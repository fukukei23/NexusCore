
# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_ssl.py ===
from __future__ import annotations

import os
import socket as stdlib_socket
import ssl
import sys
import threading
from contextlib import asynccontextmanager, contextmanager, suppress
from functools import partial
from ssl import SSLContext
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
)

import pytest

from trio import StapledStream
from trio._tests.pytest_plugin import skip_if_optional_else_raise
from trio.abc import ReceiveStream, SendStream
from trio.testing import (
    Matcher,
    MemoryReceiveStream,
    MemorySendStream,
    RaisesGroup,
)

try:
    import trustme
    from OpenSSL import SSL
except ImportError as error:
    skip_if_optional_else_raise(error)

import trio

from .. import _core, socket as tsocket
from .._abc import Stream
from .._core import BrokenResourceError, ClosedResourceError
from .._core._tests.tutil import slow
from .._highlevel_generic import aclose_forcefully
from .._highlevel_open_tcp_stream import open_tcp_stream
from .._highlevel_socket import SocketListener, SocketStream
from .._ssl import NeedHandshakeError, SSLListener, SSLStream, _is_eof
from .._util import ConflictDetector
from ..testing import (
    Sequencer,
    assert_checkpoints,
    check_two_way_stream,
    lockstep_stream_pair,
    memory_stream_pair,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

    from typing_extensions import TypeAlias

    from trio._core import MockClock
    from trio._ssl import T_Stream

    from .._core._run import CancelScope

# We have two different kinds of echo server fixtures we use for testing. The
# first is a real server written using the stdlib ssl module and blocking
# sockets. It runs in a thread and we talk to it over a real socketpair(), to
# validate interoperability in a semi-realistic setting.
#
# The second is a very weird virtual echo server that lives inside a custom
# Stream class. It lives entirely inside the Python object space; there are no
# operating system calls in it at all. No threads, no I/O, nothing. It's
# 'send_all' call takes encrypted data from a client and feeds it directly into
# the server-side TLS state engine to decrypt, then takes that data, feeds it
# back through to get the encrypted response, and returns it from 'receive_some'. This
# gives us full control and reproducibility. This server is written using
# PyOpenSSL, so that we can trigger renegotiations on demand. It also allows
# us to insert random (virtual) delays, to really exercise all the weird paths
# in SSLStream's state engine.
#
# Both present a certificate for "trio-test-1.example.org".

TRIO_TEST_CA = trustme.CA()
TRIO_TEST_1_CERT = TRIO_TEST_CA.issue_server_cert("trio-test-1.example.org")

SERVER_CTX = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
if hasattr(ssl, "OP_IGNORE_UNEXPECTED_EOF"):
    SERVER_CTX.options &= ~ssl.OP_IGNORE_UNEXPECTED_EOF

TRIO_TEST_1_CERT.configure_cert(SERVER_CTX)


# TLS 1.3 has a lot of changes from previous versions. So we want to run tests
# with both TLS 1.3, and TLS 1.2.
# "tls13" means that we're willing to negotiate TLS 1.3. Usually that's
# what will happen, but the renegotiation tests explicitly force a
# downgrade on the server side. "tls12" means we refuse to negotiate TLS
# 1.3, so we'll almost certainly use TLS 1.2.
@pytest.fixture(scope="module", params=["tls13", "tls12"])
def client_ctx(request: pytest.FixtureRequest) -> ssl.SSLContext:
    ctx = ssl.create_default_context()

    if hasattr(ssl, "OP_IGNORE_UNEXPECTED_EOF"):
        ctx.options &= ~ssl.OP_IGNORE_UNEXPECTED_EOF

    TRIO_TEST_CA.configure_trust(ctx)
    if request.param in ["default", "tls13"]:
        return ctx
    elif request.param == "tls12":
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        return ctx
    else:  # pragma: no cover
        raise AssertionError()


# The blocking socket server.
def ssl_echo_serve_sync(
    sock: stdlib_socket.socket,
    *,
    expect_fail: bool = False,
) -> None:
    try:
        wrapped = SERVER_CTX.wrap_socket(
            sock,
            server_side=True,
            suppress_ragged_eofs=False,
        )
        with wrapped:
            wrapped.do_handshake()
            while True:
                data = wrapped.recv(4096)
                if not data:
                    # other side has initiated a graceful shutdown; we try to
                    # respond in kind but it's legal for them to have already
                    # gone away.
                    with suppress(BrokenPipeError, ssl.SSLZeroReturnError):
                        wrapped.unwrap()
                    return
                wrapped.sendall(data)
    # This is an obscure workaround for an openssl bug. In server mode, in
    # some versions, openssl sends some extra data at the end of do_handshake
    # that it shouldn't send. Normally this is harmless, but, if the other
    # side shuts down the connection before it reads that data, it might cause
    # the OS to report a ECONNREST or even ECONNABORTED (which is just wrong,
    # since ECONNABORTED is supposed to mean that connect() failed, but what
    # can you do). In this case the other side did nothing wrong, but there's
    # no way to recover, so we let it pass, and just cross our fingers its not
    # hiding any (other) real bugs. For more details see:
    #
    #   https://github.com/python-trio/trio/issues/1293
    #
    # Also, this happens frequently but non-deterministically, so we have to
    # 'no cover' it to avoid coverage flapping.
    except (ConnectionResetError, ConnectionAbortedError):  # pragma: no cover
        return
    except Exception as exc:
        if expect_fail:
            print("ssl_echo_serve_sync got error as expected:", exc)
        else:  # pragma: no cover
            print("ssl_echo_serve_sync got unexpected error:", exc)
            raise
    else:
        if expect_fail:  # pragma: no cover
            raise RuntimeError("failed to fail?")
    finally:
        sock.close()


# Fixture that gives a raw socket connected to a trio-test-1 echo server
# (running in a thread). Useful for testing making connections with different
# SSLContexts.
@asynccontextmanager
async def ssl_echo_server_raw(expect_fail: bool = False) -> AsyncIterator[SocketStream]:
    a, b = stdlib_socket.socketpair()
    async with trio.open_nursery() as nursery:
        # Exiting the 'with a, b' context manager closes the sockets, which
        # causes the thread to exit (possibly with an error), which allows the
        # nursery context manager to exit too.
        with a, b:
            nursery.start_soon(
                trio.to_thread.run_sync,
                partial(ssl_echo_serve_sync, b, expect_fail=expect_fail),
            )

            yield SocketStream(tsocket.from_stdlib_socket(a))


# Fixture that gives a properly set up SSLStream connected to a trio-test-1
# echo server (running in a thread)
@asynccontextmanager
async def ssl_echo_server(
    client_ctx: SSLContext,
    expect_fail: bool = False,
) -> AsyncIterator[SSLStream[Stream]]:
    async with ssl_echo_server_raw(expect_fail=expect_fail) as sock:
        yield SSLStream(sock, client_ctx, server_hostname="trio-test-1.example.org")


# The weird in-memory server ... thing.
# Doesn't inherit from Stream because I left out the methods that we don't
# actually need.
# jakkdl: it seems to implement all the abstract methods (now), so I made it inherit
#         from Stream for the sake of typechecking.
class PyOpenSSLEchoStream(Stream):
    def __init__(
        self,
        sleeper: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        # TLS 1.3 removes renegotiation support. Which is great for them, but
        # we still have to support versions before that, and that means we
        # need to test renegotiation support, which means we need to force this
        # to use a lower version where this test server can trigger
        # renegotiations.
        from cryptography.hazmat.bindings.openssl.binding import Binding

        b = Binding()
        ctx.set_options(b.lib.SSL_OP_NO_TLSv1_3)

        # Unfortunately there's currently no way to say "use 1.3 or worse", we
        # can only disable specific versions. And if the two sides start
        # negotiating 1.4 at some point in the future, it *might* mean that
        # our tests silently stop working properly. So the next line is a
        # tripwire to remind us we need to revisit this stuff in 5 years or
        # whatever when the next TLS version is released:
        assert not hasattr(SSL, "OP_NO_TLSv1_4")
        TRIO_TEST_1_CERT.configure_cert(ctx)
        self._conn = SSL.Connection(ctx, None)
        self._conn.set_accept_state()
        self._lot = _core.ParkingLot()
        self._pending_cleartext = bytearray()

        self._send_all_conflict_detector = ConflictDetector(
            "simultaneous calls to PyOpenSSLEchoStream.send_all",
        )
        self._receive_some_conflict_detector = ConflictDetector(
            "simultaneous calls to PyOpenSSLEchoStream.receive_some",
        )

        self.sleeper: Callable[[str], Awaitable[None]]
        if sleeper is None:

            async def no_op_sleeper(_: object) -> None:
                return

            self.sleeper = no_op_sleeper
        else:
            self.sleeper = sleeper

    async def aclose(self) -> None:
        self._conn.bio_shutdown()

    def renegotiate_pending(self) -> bool:
        return self._conn.renegotiate_pending()

    def renegotiate(self) -> None:
        # Returns false if a renegotiation is already in progress, meaning
        # nothing happens.
        assert self._conn.renegotiate()

    async def wait_send_all_might_not_block(self) -> None:
        with self._send_all_conflict_detector:
            await _core.checkpoint()
            await _core.checkpoint()
            await self.sleeper("wait_send_all_might_not_block")

    async def send_all(self, data: bytes) -> None:
        print("  --> transport_stream.send_all")
        with self._send_all_conflict_detector:
            await _core.checkpoint()
            await _core.checkpoint()
            await self.sleeper("send_all")
            self._conn.bio_write(data)
            while True:
                await self.sleeper("send_all")
                try:
                    data = self._conn.recv(1)
                except SSL.ZeroReturnError:
                    self._conn.shutdown()
                    print("renegotiations:", self._conn.total_renegotiations())
                    break
                except SSL.WantReadError:
                    break
                else:
                    self._pending_cleartext += data
            self._lot.unpark_all()
            await self.sleeper("send_all")
            print("  <-- transport_stream.send_all finished")

    async def receive_some(self, nbytes: int | None = None) -> bytes:
        print("  --> transport_stream.receive_some")
        if nbytes is None:
            nbytes = 65536  # arbitrary
        with self._receive_some_conflict_detector:
            try:
                await _core.checkpoint()
                await _core.checkpoint()
                while True:
                    await self.sleeper("receive_some")
                    try:
                        return self._conn.bio_read(nbytes)
                    except SSL.WantReadError:
                        # No data in our ciphertext buffer; try to generate
                        # some.
                        if self._pending_cleartext:
                            # We have some cleartext; maybe we can encrypt it
                            # and then return it.
                            print("    trying", self._pending_cleartext)
                            try:
                                # PyOpenSSL bug: doesn't accept bytearray
                                # https://github.com/pyca/pyopenssl/issues/621
                                next_byte = self._pending_cleartext[0:1]
                                self._conn.send(bytes(next_byte))
                            # Apparently this next bit never gets hit in the
                            # test suite, but it's not an interesting omission
                            # so let's pragma it.
                            except SSL.WantReadError:  # pragma: no cover
                                # We didn't manage to send the cleartext (and
                                # in particular we better leave it there to
                                # try again, due to openssl's retry
                                # semantics), but it's possible we pushed a
                                # renegotiation forward and *now* we have data
                                # to send.
                                try:
                                    return self._conn.bio_read(nbytes)
                                except SSL.WantReadError:
                                    # Nope. We're just going to have to wait
                                    # for someone to call send_all() to give
                                    # use more data.
                                    print("parking (a)")
                                    await self._lot.park()
                            else:
                                # We successfully sent that byte, so we don't
                                # have to again.
                                del self._pending_cleartext[0:1]
                        else:
                            # no pending cleartext; nothing to do but wait for
                            # someone to call send_all
                            print("parking (b)")
                            await self._lot.park()
            finally:
                await self.sleeper("receive_some")
                print("  <-- transport_stream.receive_some finished")


async def test_PyOpenSSLEchoStream_gives_resource_busy_errors() -> None:
    # Make sure that PyOpenSSLEchoStream complains if two tasks call send_all
    # at the same time, or ditto for receive_some. The tricky cases where SSLStream
    # might accidentally do this are during renegotiation, which we test using
    # PyOpenSSLEchoStream, so this makes sure that if we do have a bug then
    # PyOpenSSLEchoStream will notice and complain.

    async def do_test(
        func1: str,
        args1: tuple[object, ...],
        func2: str,
        args2: tuple[object, ...],
    ) -> None:
        s = PyOpenSSLEchoStream()
        with RaisesGroup(Matcher(_core.BusyResourceError, "simultaneous")):
            async with _core.open_nursery() as nursery:
                nursery.start_soon(getattr(s, func1), *args1)
                nursery.start_soon(getattr(s, func2), *args2)

    await do_test("send_all", (b"x",), "send_all", (b"x",))
    await do_test("send_all", (b"x",), "wait_send_all_might_not_block", ())
    await do_test(
        "wait_send_all_might_not_block",
        (),
        "wait_send_all_might_not_block",
        (),
    )
    await do_test("receive_some", (1,), "receive_some", (1,))


@contextmanager
def virtual_ssl_echo_server(
    client_ctx: SSLContext,
    sleeper: Callable[[str], Awaitable[None]] | None = None,
) -> Iterator[SSLStream[PyOpenSSLEchoStream]]:
    fakesock = PyOpenSSLEchoStream(sleeper=sleeper)
    yield SSLStream(fakesock, client_ctx, server_hostname="trio-test-1.example.org")


def ssl_wrap_pair(  # type: ignore[explicit-any]
    client_ctx: SSLContext,
    client_transport: T_Stream,
    server_transport: T_Stream,
    *,
    client_kwargs: dict[str, Any] | None = None,
    server_kwargs: dict[str, Any] | None = None,
) -> tuple[SSLStream[T_Stream], SSLStream[T_Stream]]:
    if server_kwargs is None:
        server_kwargs = {}
    if client_kwargs is None:
        client_kwargs = {}
    client_ssl = SSLStream(
        client_transport,
        client_ctx,
        server_hostname="trio-test-1.example.org",
        **client_kwargs,
    )
    server_ssl = SSLStream(
        server_transport,
        SERVER_CTX,
        server_side=True,
        **server_kwargs,
    )
    return client_ssl, server_ssl


MemoryStapledStream: TypeAlias = StapledStream[MemorySendStream, MemoryReceiveStream]


def ssl_memory_stream_pair(
    client_ctx: SSLContext,
    client_kwargs: dict[str, str | bytes | bool | None] | None = None,
    server_kwargs: dict[str, str | bytes | bool | None] | None = None,
) -> tuple[
    SSLStream[MemoryStapledStream],
    SSLStream[MemoryStapledStream],
]:
    client_transport, server_transport = memory_stream_pair()
    return ssl_wrap_pair(
        client_ctx,
        client_transport,
        server_transport,
        client_kwargs=client_kwargs,
        server_kwargs=server_kwargs,
    )


MyStapledStream: TypeAlias = StapledStream[SendStream, ReceiveStream]


def ssl_lockstep_stream_pair(
    client_ctx: SSLContext,
    client_kwargs: dict[str, str | bytes | bool | None] | None = None,
    server_kwargs: dict[str, str | bytes | bool | None] | None = None,
) -> tuple[
    SSLStream[MyStapledStream],
    SSLStream[MyStapledStream],
]:
    client_transport, server_transport = lockstep_stream_pair()
    return ssl_wrap_pair(
        client_ctx,
        client_transport,
        server_transport,
        client_kwargs=client_kwargs,
        server_kwargs=server_kwargs,
    )


# Simple smoke test for handshake/send/receive/shutdown talking to a
# synchronous server, plus make sure that we do the bare minimum of
# certificate checking (even though this is really Python's responsibility)
async def test_ssl_client_basics(client_ctx: SSLContext) -> None:
    # Everything OK
    async with ssl_echo_server(client_ctx) as s:
        assert not s.server_side
        await s.send_all(b"x")
        assert await s.receive_some(1) == b"x"
        await s.aclose()

    # Didn't configure the CA file, should fail
    async with ssl_echo_server_raw(expect_fail=True) as sock:
        bad_client_ctx = ssl.create_default_context()
        s = SSLStream(sock, bad_client_ctx, server_hostname="trio-test-1.example.org")
        assert not s.server_side
        with pytest.raises(BrokenResourceError) as excinfo:
            await s.send_all(b"x")
        assert isinstance(excinfo.value.__cause__, ssl.SSLError)

    # Trusted CA, but wrong host name
    async with ssl_echo_server_raw(expect_fail=True) as sock:
        s = SSLStream(sock, client_ctx, server_hostname="trio-test-2.example.org")
        assert not s.server_side
        with pytest.raises(BrokenResourceError) as excinfo:
            await s.send_all(b"x")
        assert isinstance(excinfo.value.__cause__, ssl.CertificateError)


async def test_ssl_server_basics(client_ctx: SSLContext) -> None:
    a, b = stdlib_socket.socketpair()
    with a, b:
        server_sock = tsocket.from_stdlib_socket(b)
        server_transport = SSLStream(
            SocketStream(server_sock),
            SERVER_CTX,
            server_side=True,
        )
        assert server_transport.server_side

        def client() -> None:
            with client_ctx.wrap_socket(
                a,
                server_hostname="trio-test-1.example.org",
            ) as client_sock:
                client_sock.sendall(b"x")
                assert client_sock.recv(1) == b"y"
                client_sock.sendall(b"z")
                client_sock.unwrap()

        t = threading.Thread(target=client)
        t.start()

        assert await server_transport.receive_some(1) == b"x"
        await server_transport.send_all(b"y")
        assert await server_transport.receive_some(1) == b"z"
        assert await server_transport.receive_some(1) == b""
        await server_transport.aclose()

        t.join()


async def test_attributes(client_ctx: SSLContext) -> None:
    async with ssl_echo_server_raw(expect_fail=True) as sock:
        good_ctx = client_ctx
        bad_ctx = ssl.create_default_context()
        s = SSLStream(sock, good_ctx, server_hostname="trio-test-1.example.org")

        assert s.transport_stream is sock

        # Forwarded attribute getting
        assert s.context is good_ctx
        assert s.server_side == False  # noqa
        assert s.server_hostname == "trio-test-1.example.org"
        with pytest.raises(AttributeError):
            s.asfdasdfsa  # noqa: B018  # "useless expression"

        # __dir__
        assert "transport_stream" in dir(s)
        assert "context" in dir(s)

        # Setting the attribute goes through to the underlying object

        # most attributes on SSLObject are read-only
        with pytest.raises(AttributeError):
            s.server_side = True
        with pytest.raises(AttributeError):
            s.server_hostname = "asdf"

        # but .context is *not*. Check that we forward attribute setting by
        # making sure that after we set the bad context our handshake indeed
        # fails:
        s.context = bad_ctx
        assert s.context is bad_ctx
        with pytest.raises(BrokenResourceError) as excinfo:
            await s.do_handshake()
        assert isinstance(excinfo.value.__cause__, ssl.SSLError)


# Note: this test fails horribly if we force TLS 1.2 and trigger a
# renegotiation at the beginning (e.g. by switching to the pyopenssl
# server). Usually the client crashes in SSLObject.write with "UNEXPECTED
# RECORD"; sometimes we get something more exotic like a SyscallError. This is
# odd because openssl isn't doing any syscalls, but so it goes. After lots of
# websearching I'm pretty sure this is due to a bug in OpenSSL, where it just
# can't reliably handle full-duplex communication combined with
# renegotiation. Nice, eh?
#
#   https://rt.openssl.org/Ticket/Display.html?id=3712
#   https://rt.openssl.org/Ticket/Display.html?id=2481
#   http://openssl.6102.n7.nabble.com/TLS-renegotiation-failure-on-receiving-application-data-during-handshake-td48127.html
#   https://stackoverflow.com/questions/18728355/ssl-renegotiation-with-full-duplex-socket-communication
#
# In some variants of this test (maybe only against the java server?) I've
# also seen cases where our send_all blocks waiting to write, and then our receive_some
# also blocks waiting to write, and they never wake up again. It looks like
# some kind of deadlock. I suspect there may be an issue where we've filled up
# the send buffers, and the remote side is trying to handle the renegotiation
# from inside a write() call, so it has a problem: there's all this application
# data clogging up the pipe, but it can't process and return it to the
# application because it's in write(), and it doesn't want to buffer infinite
# amounts of data, and... actually I guess those are the only two choices.
#
# NSS even documents that you shouldn't try to do a renegotiation except when
# the connection is idle:
#
#   https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS/SSL_functions/sslfnc.html#1061582
#
# I begin to see why HTTP/2 forbids renegotiation and TLS 1.3 removes it...


async def test_full_duplex_basics(client_ctx: SSLContext) -> None:
    CHUNKS = 30
    CHUNK_SIZE = 32768
    EXPECTED = CHUNKS * CHUNK_SIZE

    sent = bytearray()
    received = bytearray()

    async def sender(s: Stream) -> None:
        nonlocal sent
        for i in range(CHUNKS):
            print(i)
            chunk = bytes([i] * CHUNK_SIZE)
            sent += chunk
            await s.send_all(chunk)

    async def receiver(s: Stream) -> None:
        nonlocal received
        while len(received) < EXPECTED:
            chunk = await s.receive_some(CHUNK_SIZE // 2)
            received += chunk

    async with ssl_echo_server(client_ctx) as s:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sender, s)
            nursery.start_soon(receiver, s)
            # And let's have some doing handshakes too, everyone
            # simultaneously
            nursery.start_soon(s.do_handshake)
            nursery.start_soon(s.do_handshake)

        await s.aclose()

    assert len(sent) == len(received) == EXPECTED
    assert sent == received


async def test_renegotiation_simple(client_ctx: SSLContext) -> None:
    with virtual_ssl_echo_server(client_ctx) as s:
        await s.do_handshake()
        s.transport_stream.renegotiate()
        await s.send_all(b"a")
        assert await s.receive_some(1) == b"a"

        # Have to send some more data back and forth to make sure the
        # renegotiation is finished before shutting down the
        # connection... otherwise openssl raises an error. I think this is a
        # bug in openssl but what can ya do.
        await s.send_all(b"b")
        assert await s.receive_some(1) == b"b"

        await s.aclose()


@slow
async def test_renegotiation_randomized(
    mock_clock: MockClock,
    client_ctx: SSLContext,
) -> None:
    # The only blocking things in this function are our random sleeps, so 0 is
    # a good threshold.
    mock_clock.autojump_threshold = 0

    import random

    r = random.Random(0)

    async def sleeper(_: object) -> None:
        await trio.sleep(r.uniform(0, 10))

    async def clear() -> None:
        while s.transport_stream.renegotiate_pending():
            with assert_checkpoints():
                await send(b"-")
            with assert_checkpoints():
                await expect(b"-")
        print("-- clear --")

    async def send(byte: bytes) -> None:
        await s.transport_stream.sleeper("outer send")
        print("calling SSLStream.send_all", byte)
        with assert_checkpoints():
            await s.send_all(byte)

    async def expect(expected: bytes) -> None:
        await s.transport_stream.sleeper("expect")
        print("calling SSLStream.receive_some, expecting", expected)
        assert len(expected) == 1
        with assert_checkpoints():
            assert await s.receive_some(1) == expected

    with virtual_ssl_echo_server(client_ctx, sleeper=sleeper) as s:
        await s.do_handshake()

        await send(b"a")
        s.transport_stream.renegotiate()
        await expect(b"a")

        await clear()

        for i in range(100):
            b1 = bytes([i % 0xFF])
            b2 = bytes([(2 * i) % 0xFF])
            s.transport_stream.renegotiate()
            async with _core.open_nursery() as nursery:
                nursery.start_soon(send, b1)
                nursery.start_soon(expect, b1)
            async with _core.open_nursery() as nursery:
                nursery.start_soon(expect, b2)
                nursery.start_soon(send, b2)
            await clear()

        for i in range(100):
            b1 = bytes([i % 0xFF])
            b2 = bytes([(2 * i) % 0xFF])
            await send(b1)
            s.transport_stream.renegotiate()
            await expect(b1)
            async with _core.open_nursery() as nursery:
                nursery.start_soon(expect, b2)
                nursery.start_soon(send, b2)
            await clear()

    # Checking that wait_send_all_might_not_block and receive_some don't
    # conflict:

    # 1) Set up a situation where expect (receive_some) is blocked sending,
    # and wait_send_all_might_not_block comes in.

    # Our receive_some() call will get stuck when it hits send_all
    async def sleeper_with_slow_send_all(method: str) -> None:
        if method == "send_all":
            # ignore ASYNC116, not sleep_forever, trying to test a large but finite sleep
            await trio.sleep(100000)  # noqa: ASYNC116

    # And our wait_send_all_might_not_block call will give it time to get
    # stuck, and then start
    async def sleep_then_wait_writable() -> None:
        await trio.sleep(1000)
        await s.wait_send_all_might_not_block()

    with virtual_ssl_echo_server(client_ctx, sleeper=sleeper_with_slow_send_all) as s:
        await send(b"x")
        s.transport_stream.renegotiate()
        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect, b"x")
            nursery.start_soon(sleep_then_wait_writable)

        await clear()

        await s.aclose()

    # 2) Same, but now wait_send_all_might_not_block is stuck when
    # receive_some tries to send.

    async def sleeper_with_slow_wait_writable_and_expect(method: str) -> None:
        if method == "wait_send_all_might_not_block":
            # ignore ASYNC116, not sleep_forever, trying to test a large but finite sleep
            await trio.sleep(100000)  # noqa: ASYNC116
        elif method == "expect":
            await trio.sleep(1000)

    with virtual_ssl_echo_server(
        client_ctx,
        sleeper=sleeper_with_slow_wait_writable_and_expect,
    ) as s:
        await send(b"x")
        s.transport_stream.renegotiate()
        async with _core.open_nursery() as nursery:
            nursery.start_soon(expect, b"x")
            nursery.start_soon(s.wait_send_all_might_not_block)

        await clear()

        await s.aclose()


async def test_resource_busy_errors(client_ctx: SSLContext) -> None:
    S: TypeAlias = trio.SSLStream[
        trio.StapledStream[trio.abc.SendStream, trio.abc.ReceiveStream]
    ]

    async def do_send_all(s: S) -> None:
        with assert_checkpoints():
            await s.send_all(b"x")

    async def do_receive_some(s: S) -> None:
        with assert_checkpoints():
            await s.receive_some(1)

    async def do_wait_send_all_might_not_block(s: S) -> None:
        with assert_checkpoints():
            await s.wait_send_all_might_not_block()

    async def do_test(
        func1: Callable[[S], Awaitable[None]],
        func2: Callable[[S], Awaitable[None]],
    ) -> None:
        s, _ = ssl_lockstep_stream_pair(client_ctx)
        with RaisesGroup(Matcher(_core.BusyResourceError, "another task")):
            async with _core.open_nursery() as nursery:
                nursery.start_soon(func1, s)
                nursery.start_soon(func2, s)

    await do_test(do_send_all, do_send_all)
    await do_test(do_receive_some, do_receive_some)
    await do_test(do_send_all, do_wait_send_all_might_not_block)
    await do_test(do_wait_send_all_might_not_block, do_wait_send_all_might_not_block)


async def test_wait_writable_calls_underlying_wait_writable() -> None:
    record = []

    class NotAStream(Stream):
        async def wait_send_all_might_not_block(self) -> None:
            record.append("ok")

        # define methods that are abstract in Stream
        async def aclose(self) -> None:
            raise AssertionError("Should not get called")  # pragma: no cover

        async def receive_some(self, max_bytes: int | None = None) -> bytes | bytearray:
            raise AssertionError("Should not get called")  # pragma: no cover

        async def send_all(self, data: bytes | bytearray | memoryview) -> None:
            raise AssertionError("Should not get called")  # pragma: no cover

    ctx = ssl.create_default_context()
    s = SSLStream(NotAStream(), ctx, server_hostname="x")
    await s.wait_send_all_might_not_block()
    assert record == ["ok"]


@pytest.mark.skipif(
    os.name == "nt" and sys.version_info >= (3, 10),
    reason="frequently fails on Windows + Python 3.10",
)
async def test_checkpoints(client_ctx: SSLContext) -> None:
    async with ssl_echo_server(client_ctx) as s:
        with assert_checkpoints():
            await s.do_handshake()
        with assert_checkpoints():
            await s.do_handshake()
        with assert_checkpoints():
            await s.wait_send_all_might_not_block()
        with assert_checkpoints():
            await s.send_all(b"xxx")
        with assert_checkpoints():
            await s.receive_some(1)
        # These receive_some's in theory could return immediately, because the
        # "xxx" was sent in a single record and after the first
        # receive_some(1) the rest are sitting inside the SSLObject's internal
        # buffers.
        with assert_checkpoints():
            await s.receive_some(1)
        with assert_checkpoints():
            await s.receive_some(1)
        with assert_checkpoints():
            await s.unwrap()

    async with ssl_echo_server(client_ctx) as s:
        await s.do_handshake()
        with assert_checkpoints():
            await s.aclose()


async def test_send_all_empty_string(client_ctx: SSLContext) -> None:
    async with ssl_echo_server(client_ctx) as s:
        await s.do_handshake()

        # underlying SSLObject interprets writing b"" as indicating an EOF,
        # for some reason. Make sure we don't inherit this.
        with assert_checkpoints():
            await s.send_all(b"")
        with assert_checkpoints():
            await s.send_all(b"")
        await s.send_all(b"x")
        assert await s.receive_some(1) == b"x"

        await s.aclose()


@pytest.mark.parametrize("https_compatible", [False, True])
async def test_SSLStream_generic(
    client_ctx: SSLContext,
    https_compatible: bool,
) -> None:
    async def stream_maker() -> tuple[
        SSLStream[MemoryStapledStream],
        SSLStream[MemoryStapledStream],
    ]:
        return ssl_memory_stream_pair(
            client_ctx,
            client_kwargs={"https_compatible": https_compatible},
            server_kwargs={"https_compatible": https_compatible},
        )

    async def clogged_stream_maker() -> tuple[
        SSLStream[MyStapledStream],
        SSLStream[MyStapledStream],
    ]:
        client, server = ssl_lockstep_stream_pair(client_ctx)
        # If we don't do handshakes up front, then we run into a problem in
        # the following situation:
        # - server does wait_send_all_might_not_block
        # - client does receive_some to unclog it
        # Then the client's receive_some will actually send some data to start
        # the handshake, and itself get stuck.
        async with _core.open_nursery() as nursery:
            nursery.start_soon(client.do_handshake)
            nursery.start_soon(server.do_handshake)
        return client, server

    await check_two_way_stream(stream_maker, clogged_stream_maker)


async def test_unwrap(client_ctx: SSLContext) -> None:
    client_ssl, server_ssl = ssl_memory_stream_pair(client_ctx)
    client_transport = client_ssl.transport_stream
    server_transport = server_ssl.transport_stream

    seq = Sequencer()

    async def client() -> None:
        await client_ssl.do_handshake()
        await client_ssl.send_all(b"x")
        assert await client_ssl.receive_some(1) == b"y"
        await client_ssl.send_all(b"z")

        # After sending that, disable outgoing data from our end, to make
        # sure the server doesn't see our EOF until after we've sent some
        # trailing data
        async with seq(0):
            send_all_hook = client_transport.send_stream.send_all_hook
            client_transport.send_stream.send_all_hook = None

        assert await client_ssl.receive_some(1) == b""
        assert client_ssl.transport_stream is client_transport
        # We just received EOF. Unwrap the connection and send some more.
        raw, trailing = await client_ssl.unwrap()
        assert raw is client_transport
        assert trailing == b""
        assert client_ssl.transport_stream is None
        await raw.send_all(b"trailing")

        # Reconnect the streams. Now the server will receive both our shutdown
        # acknowledgement + the trailing data in a single lump.
        client_transport.send_stream.send_all_hook = send_all_hook
        await client_transport.send_stream.send_all_hook()

    async def server() -> None:
        await server_ssl.do_handshake()
        assert await server_ssl.receive_some(1) == b"x"
        await server_ssl.send_all(b"y")
        assert await server_ssl.receive_some(1) == b"z"
        # Now client is blocked waiting for us to send something, but
        # instead we close the TLS connection (with sequencer to make sure
        # that the client won't see and automatically respond before we've had
        # a chance to disable the client->server transport)
        async with seq(1):
            raw, trailing = await server_ssl.unwrap()
        assert raw is server_transport
        assert trailing == b"trailing"
        assert server_ssl.transport_stream is None

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client)
        nursery.start_soon(server)


async def test_closing_nice_case(client_ctx: SSLContext) -> None:
    # the nice case: graceful closes all around

    client_ssl, server_ssl = ssl_memory_stream_pair(client_ctx)
    client_transport = client_ssl.transport_stream

    # Both the handshake and the close require back-and-forth discussion, so
    # we need to run them concurrently
    async def client_closer() -> None:
        with assert_checkpoints():
            await client_ssl.aclose()

    async def server_closer() -> None:
        assert await server_ssl.receive_some(10) == b""
        assert await server_ssl.receive_some(10) == b""
        with assert_checkpoints():
            await server_ssl.aclose()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client_closer)
        nursery.start_soon(server_closer)

    # closing the SSLStream also closes its transport
    with pytest.raises(ClosedResourceError):
        await client_transport.send_all(b"123")

    # once closed, it's OK to close again
    with assert_checkpoints():
        await client_ssl.aclose()
    with assert_checkpoints():
        await client_ssl.aclose()

    # Trying to send more data does not work
    with pytest.raises(ClosedResourceError):
        await server_ssl.send_all(b"123")

    # And once the connection is has been closed *locally*, then instead of
    # getting empty bytestrings we get a proper error
    with pytest.raises(ClosedResourceError):
        assert await client_ssl.receive_some(10) == b""

    with pytest.raises(ClosedResourceError):
        await client_ssl.unwrap()

    with pytest.raises(ClosedResourceError):
        await client_ssl.do_handshake()

    # Check that a graceful close *before* handshaking gives a clean EOF on
    # the other side
    client_ssl, server_ssl = ssl_memory_stream_pair(client_ctx)

    async def expect_eof_server() -> None:
        with assert_checkpoints():
            assert await server_ssl.receive_some(10) == b""
        with assert_checkpoints():
            await server_ssl.aclose()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client_ssl.aclose)
        nursery.start_soon(expect_eof_server)


async def test_send_all_fails_in_the_middle(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    async def bad_hook() -> NoReturn:
        raise KeyError

    client.transport_stream.send_stream.send_all_hook = bad_hook

    with pytest.raises(KeyError):
        await client.send_all(b"x")

    with pytest.raises(BrokenResourceError):
        await client.wait_send_all_might_not_block()

    closed = 0

    def close_hook() -> None:
        nonlocal closed
        closed += 1

    client.transport_stream.send_stream.close_hook = close_hook
    client.transport_stream.receive_stream.close_hook = close_hook
    await client.aclose()

    assert closed == 2


async def test_ssl_over_ssl(client_ctx: SSLContext) -> None:
    client_0, server_0 = memory_stream_pair()

    client_1 = SSLStream(
        client_0,
        client_ctx,
        server_hostname="trio-test-1.example.org",
    )
    server_1 = SSLStream(server_0, SERVER_CTX, server_side=True)

    client_2 = SSLStream(
        client_1,
        client_ctx,
        server_hostname="trio-test-1.example.org",
    )
    server_2 = SSLStream(server_1, SERVER_CTX, server_side=True)

    async def client() -> None:
        await client_2.send_all(b"hi")
        assert await client_2.receive_some(10) == b"bye"

    async def server() -> None:
        assert await server_2.receive_some(10) == b"hi"
        await server_2.send_all(b"bye")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client)
        nursery.start_soon(server)


async def test_ssl_bad_shutdown(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    await trio.aclose_forcefully(client)
    # now the server sees a broken stream
    with pytest.raises(BrokenResourceError):
        await server.receive_some(10)
    with pytest.raises(BrokenResourceError):
        await server.send_all(b"x" * 10)

    await server.aclose()


async def test_ssl_bad_shutdown_but_its_ok(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(
        client_ctx,
        server_kwargs={"https_compatible": True},
        client_kwargs={"https_compatible": True},
    )

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    await trio.aclose_forcefully(client)
    # the server sees that as a clean shutdown
    assert await server.receive_some(10) == b""
    with pytest.raises(BrokenResourceError):
        await server.send_all(b"x" * 10)

    await server.aclose()


async def test_ssl_handshake_failure_during_aclose() -> None:
    # Weird scenario: aclose() triggers an automatic handshake, and this
    # fails. This also exercises a bit of code in aclose() that was otherwise
    # uncovered, for re-raising exceptions after calling aclose_forcefully on
    # the underlying transport.
    async with ssl_echo_server_raw(expect_fail=True) as sock:
        # Don't configure trust correctly
        client_ctx = ssl.create_default_context()
        s = SSLStream(sock, client_ctx, server_hostname="trio-test-1.example.org")
        # It's a little unclear here whether aclose should swallow the error
        # or let it escape. We *do* swallow the error if it arrives when we're
        # sending close_notify, because both sides closing the connection
        # simultaneously is allowed. But I guess when https_compatible=False
        # then it's bad if we can get through a whole connection with a peer
        # that has no valid certificate, and never raise an error.
        with pytest.raises(BrokenResourceError):
            await s.aclose()


async def test_ssl_only_closes_stream_once(client_ctx: SSLContext) -> None:
    # We used to have a bug where if transport_stream.aclose() raised an
    # error, we would call it again. This checks that that's fixed.
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    client_orig_close_hook = client.transport_stream.send_stream.close_hook
    transport_close_count = 0

    def close_hook() -> NoReturn:
        nonlocal transport_close_count
        assert client_orig_close_hook is not None
        client_orig_close_hook()
        transport_close_count += 1
        raise KeyError

    client.transport_stream.send_stream.close_hook = close_hook

    with pytest.raises(KeyError):
        await client.aclose()
    assert transport_close_count == 1


async def test_ssl_https_compatibility_disagreement(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(
        client_ctx,
        server_kwargs={"https_compatible": False},
        client_kwargs={"https_compatible": True},
    )

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    # client is in HTTPS-mode, server is not
    # so client doing graceful_shutdown causes an error on server
    async def receive_and_expect_error() -> None:
        with pytest.raises(BrokenResourceError) as excinfo:
            await server.receive_some(10)

        assert _is_eof(excinfo.value.__cause__)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.aclose)
        nursery.start_soon(receive_and_expect_error)


async def test_https_mode_eof_before_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(
        client_ctx,
        server_kwargs={"https_compatible": True},
        client_kwargs={"https_compatible": True},
    )

    async def server_expect_clean_eof() -> None:
        assert await server.receive_some(10) == b""

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.aclose)
        nursery.start_soon(server_expect_clean_eof)


async def test_send_error_during_handshake(client_ctx: SSLContext) -> None:
    client, _server = ssl_memory_stream_pair(client_ctx)

    async def bad_hook() -> NoReturn:
        raise KeyError

    client.transport_stream.send_stream.send_all_hook = bad_hook

    with pytest.raises(KeyError):
        with assert_checkpoints():
            await client.do_handshake()

    with pytest.raises(BrokenResourceError):
        with assert_checkpoints():
            await client.do_handshake()


async def test_receive_error_during_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    async def bad_hook() -> NoReturn:
        raise KeyError

    client.transport_stream.receive_stream.receive_some_hook = bad_hook

    async def client_side(cancel_scope: CancelScope) -> None:
        with pytest.raises(KeyError):
            with assert_checkpoints():
                await client.do_handshake()
        cancel_scope.cancel()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client_side, nursery.cancel_scope)
        nursery.start_soon(server.do_handshake)

    with pytest.raises(BrokenResourceError):
        with assert_checkpoints():
            await client.do_handshake()


def test_selected_alpn_protocol_before_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    with pytest.raises(NeedHandshakeError):
        client.selected_alpn_protocol()

    with pytest.raises(NeedHandshakeError):
        server.selected_alpn_protocol()


async def test_selected_alpn_protocol_when_not_set(client_ctx: SSLContext) -> None:
    # ALPN protocol still returns None when it's not set,
    # instead of raising an exception
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    assert client.selected_alpn_protocol() is None
    assert server.selected_alpn_protocol() is None

    assert client.selected_alpn_protocol() == server.selected_alpn_protocol()


def test_selected_npn_protocol_before_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    with pytest.raises(NeedHandshakeError):
        client.selected_npn_protocol()

    with pytest.raises(NeedHandshakeError):
        server.selected_npn_protocol()


@pytest.mark.filterwarnings(
    r"ignore: ssl module. NPN is deprecated, use ALPN instead:UserWarning",
    r"ignore:ssl NPN is deprecated, use ALPN instead:DeprecationWarning",
)
async def test_selected_npn_protocol_when_not_set(client_ctx: SSLContext) -> None:
    # NPN protocol still returns None when it's not set,
    # instead of raising an exception
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    assert client.selected_npn_protocol() is None
    assert server.selected_npn_protocol() is None

    assert client.selected_npn_protocol() == server.selected_npn_protocol()


def test_get_channel_binding_before_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    with pytest.raises(NeedHandshakeError):
        client.get_channel_binding()

    with pytest.raises(NeedHandshakeError):
        server.get_channel_binding()


async def test_get_channel_binding_after_handshake(client_ctx: SSLContext) -> None:
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    assert client.get_channel_binding() is not None
    assert server.get_channel_binding() is not None

    assert client.get_channel_binding() == server.get_channel_binding()


async def test_getpeercert(client_ctx: SSLContext) -> None:
    # Make sure we're not affected by https://bugs.python.org/issue29334
    client, server = ssl_memory_stream_pair(client_ctx)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(client.do_handshake)
        nursery.start_soon(server.do_handshake)

    assert server.getpeercert() is None
    print(client.getpeercert())
    assert ("DNS", "trio-test-1.example.org") in client.getpeercert()["subjectAltName"]


async def test_SSLListener(client_ctx: SSLContext) -> None:
    async def setup(
        https_compatible: bool = False,
    ) -> tuple[tsocket.SocketType, SSLListener[SocketStream], SSLStream[SocketStream]]:
        listen_sock = tsocket.socket()
        await listen_sock.bind(("127.0.0.1", 0))
        listen_sock.listen(1)
        socket_listener = SocketListener(listen_sock)
        ssl_listener = SSLListener(
            socket_listener,
            SERVER_CTX,
            https_compatible=https_compatible,
        )

        transport_client = await open_tcp_stream(*listen_sock.getsockname())
        ssl_client = SSLStream(
            transport_client,
            client_ctx,
            server_hostname="trio-test-1.example.org",
        )
        return listen_sock, ssl_listener, ssl_client

    listen_sock, ssl_listener, ssl_client = await setup()

    async with ssl_client:
        ssl_server = await ssl_listener.accept()

        async with ssl_server:
            assert not ssl_server._https_compatible

            # Make sure the connection works
            async with _core.open_nursery() as nursery:
                nursery.start_soon(ssl_client.do_handshake)
                nursery.start_soon(ssl_server.do_handshake)

        # Test SSLListener.aclose
        await ssl_listener.aclose()
        assert listen_sock.fileno() == -1

    ################

    # Test https_compatible
    _, ssl_listener, ssl_client = await setup(https_compatible=True)

    ssl_server = await ssl_listener.accept()

    assert ssl_server._https_compatible

    await aclose_forcefully(ssl_listener)
    await aclose_forcefully(ssl_client)
    await aclose_forcefully(ssl_server)

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\vertex\_auth.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from .._extras import google_auth

if TYPE_CHECKING:
    from google.auth.credentials import Credentials  # type: ignore[import-untyped]

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
# google libraries don't provide types :/

# Note: these functions are blocking as they make HTTP requests, the async
# client runs these functions in a separate thread to ensure they do not
# cause synchronous blocking issues.


def load_auth(*, project_id: str | None) -> tuple[Credentials, str]:
    from google.auth.transport.requests import Request  # type: ignore[import-untyped]

    credentials, loaded_project_id = google_auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials = cast(Any, credentials)
    credentials.refresh(Request())

    if not project_id:
        project_id = loaded_project_id

    if not project_id:
        raise ValueError("Could not resolve project_id")

    if not isinstance(project_id, str):
        raise TypeError(f"Expected project_id to be a str but got {type(project_id)}")

    return credentials, project_id


def refresh_auth(credentials: Credentials) -> None:
    from google.auth.transport.requests import Request  # type: ignore[import-untyped]

    credentials.refresh(Request())

# === NexusCore/openenv\Lib\site-packages\matplotlib\rcsetup.py ===
"""
The rcsetup module contains the validation code for customization using
Matplotlib's rc settings.

Each rc setting is assigned a function used to validate any attempted changes
to that setting.  The validation functions are defined in the rcsetup module,
and are used to construct the rcParams global object which stores the settings
and is referenced throughout Matplotlib.

The default values of the rc settings are set in the default matplotlibrc file.
Any additions or deletions to the parameter set listed here should also be
propagated to the :file:`lib/matplotlib/mpl-data/matplotlibrc` in Matplotlib's
root source directory.
"""

import ast
from functools import lru_cache, reduce
from numbers import Real
import operator
import os
import re

import numpy as np

from matplotlib import _api, cbook
from matplotlib.backends import BackendFilter, backend_registry
from matplotlib.cbook import ls_mapper
from matplotlib.colors import Colormap, is_color_like
from matplotlib._fontconfig_pattern import parse_fontconfig_pattern
from matplotlib._enums import JoinStyle, CapStyle

# Don't let the original cycler collide with our validating cycler
from cycler import Cycler, cycler as ccycler


@_api.caching_module_getattr
class __getattr__:
    @_api.deprecated(
        "3.9",
        alternative="``matplotlib.backends.backend_registry.list_builtin"
            "(matplotlib.backends.BackendFilter.INTERACTIVE)``")
    @property
    def interactive_bk(self):
        return backend_registry.list_builtin(BackendFilter.INTERACTIVE)

    @_api.deprecated(
        "3.9",
        alternative="``matplotlib.backends.backend_registry.list_builtin"
            "(matplotlib.backends.BackendFilter.NON_INTERACTIVE)``")
    @property
    def non_interactive_bk(self):
        return backend_registry.list_builtin(BackendFilter.NON_INTERACTIVE)

    @_api.deprecated(
        "3.9",
        alternative="``matplotlib.backends.backend_registry.list_builtin()``")
    @property
    def all_backends(self):
        return backend_registry.list_builtin()


class ValidateInStrings:
    def __init__(self, key, valid, ignorecase=False, *,
                 _deprecated_since=None):
        """*valid* is a list of legal strings."""
        self.key = key
        self.ignorecase = ignorecase
        self._deprecated_since = _deprecated_since

        def func(s):
            if ignorecase:
                return s.lower()
            else:
                return s
        self.valid = {func(k): k for k in valid}

    def __call__(self, s):
        if self._deprecated_since:
            name, = (k for k, v in globals().items() if v is self)
            _api.warn_deprecated(
                self._deprecated_since, name=name, obj_type="function")
        if self.ignorecase and isinstance(s, str):
            s = s.lower()
        if s in self.valid:
            return self.valid[s]
        msg = (f"{s!r} is not a valid value for {self.key}; supported values "
               f"are {[*self.valid.values()]}")
        if (isinstance(s, str)
                and (s.startswith('"') and s.endswith('"')
                     or s.startswith("'") and s.endswith("'"))
                and s[1:-1] in self.valid):
            msg += "; remove quotes surrounding your string"
        raise ValueError(msg)


@lru_cache
def _listify_validator(scalar_validator, allow_stringlist=False, *,
                       n=None, doc=None):
    def f(s):
        if isinstance(s, str):
            try:
                val = [scalar_validator(v.strip()) for v in s.split(',')
                       if v.strip()]
            except Exception:
                if allow_stringlist:
                    # Sometimes, a list of colors might be a single string
                    # of single-letter colornames. So give that a shot.
                    val = [scalar_validator(v.strip()) for v in s if v.strip()]
                else:
                    raise
        # Allow any ordered sequence type -- generators, np.ndarray, pd.Series
        # -- but not sets, whose iteration order is non-deterministic.
        elif np.iterable(s) and not isinstance(s, (set, frozenset)):
            # The condition on this list comprehension will preserve the
            # behavior of filtering out any empty strings (behavior was
            # from the original validate_stringlist()), while allowing
            # any non-string/text scalar values such as numbers and arrays.
            val = [scalar_validator(v) for v in s
                   if not isinstance(v, str) or v]
        else:
            raise ValueError(
                f"Expected str or other non-set iterable, but got {s}")
        if n is not None and len(val) != n:
            raise ValueError(
                f"Expected {n} values, but there are {len(val)} values in {s}")
        return val

    try:
        f.__name__ = f"{scalar_validator.__name__}list"
    except AttributeError:  # class instance.
        f.__name__ = f"{type(scalar_validator).__name__}List"
    f.__qualname__ = f.__qualname__.rsplit(".", 1)[0] + "." + f.__name__
    f.__doc__ = doc if doc is not None else scalar_validator.__doc__
    return f


def validate_any(s):
    return s
validate_anylist = _listify_validator(validate_any)


def _validate_date(s):
    try:
        np.datetime64(s)
        return s
    except ValueError:
        raise ValueError(
            f'{s!r} should be a string that can be parsed by numpy.datetime64')


def validate_bool(b):
    """Convert b to ``bool`` or raise."""
    if isinstance(b, str):
        b = b.lower()
    if b in ('t', 'y', 'yes', 'on', 'true', '1', 1, True):
        return True
    elif b in ('f', 'n', 'no', 'off', 'false', '0', 0, False):
        return False
    else:
        raise ValueError(f'Cannot convert {b!r} to bool')


def validate_axisbelow(s):
    try:
        return validate_bool(s)
    except ValueError:
        if isinstance(s, str):
            if s == 'line':
                return 'line'
    raise ValueError(f'{s!r} cannot be interpreted as'
                     ' True, False, or "line"')


def validate_dpi(s):
    """Confirm s is string 'figure' or convert s to float or raise."""
    if s == 'figure':
        return s
    try:
        return float(s)
    except ValueError as e:
        raise ValueError(f'{s!r} is not string "figure" and '
                         f'could not convert {s!r} to float') from e


def _make_type_validator(cls, *, allow_none=False):
    """
    Return a validator that converts inputs to *cls* or raises (and possibly
    allows ``None`` as well).
    """

    def validator(s):
        if (allow_none and
                (s is None or cbook._str_lower_equal(s, "none"))):
            return None
        if cls is str and not isinstance(s, str):
            raise ValueError(f'Could not convert {s!r} to str')
        try:
            return cls(s)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f'Could not convert {s!r} to {cls.__name__}') from e

    validator.__name__ = f"validate_{cls.__name__}"
    if allow_none:
        validator.__name__ += "_or_None"
    validator.__qualname__ = (
        validator.__qualname__.rsplit(".", 1)[0] + "." + validator.__name__)
    return validator


validate_string = _make_type_validator(str)
validate_string_or_None = _make_type_validator(str, allow_none=True)
validate_stringlist = _listify_validator(
    validate_string, doc='return a list of strings')
validate_int = _make_type_validator(int)
validate_int_or_None = _make_type_validator(int, allow_none=True)
validate_float = _make_type_validator(float)
validate_float_or_None = _make_type_validator(float, allow_none=True)
validate_floatlist = _listify_validator(
    validate_float, doc='return a list of floats')


def _validate_marker(s):
    try:
        return validate_int(s)
    except ValueError as e:
        try:
            return validate_string(s)
        except ValueError as e:
            raise ValueError('Supported markers are [string, int]') from e


_validate_markerlist = _listify_validator(
    _validate_marker, doc='return a list of markers')


def _validate_pathlike(s):
    if isinstance(s, (str, os.PathLike)):
        # Store value as str because savefig.directory needs to distinguish
        # between "" (cwd) and "." (cwd, but gets updated by user selections).
        return os.fsdecode(s)
    else:
        return validate_string(s)


def validate_fonttype(s):
    """
    Confirm that this is a Postscript or PDF font type that we know how to
    convert to.
    """
    fonttypes = {'type3':    3,
                 'truetype': 42}
    try:
        fonttype = validate_int(s)
    except ValueError:
        try:
            return fonttypes[s.lower()]
        except KeyError as e:
            raise ValueError('Supported Postscript/PDF font types are %s'
                             % list(fonttypes)) from e
    else:
        if fonttype not in fonttypes.values():
            raise ValueError(
                'Supported Postscript/PDF font types are %s' %
                list(fonttypes.values()))
        return fonttype


_auto_backend_sentinel = object()


def validate_backend(s):
    if s is _auto_backend_sentinel or backend_registry.is_valid_backend(s):
        return s
    else:
        msg = (f"'{s}' is not a valid value for backend; supported values are "
               f"{backend_registry.list_all()}")
        raise ValueError(msg)


def _validate_toolbar(s):
    s = ValidateInStrings(
        'toolbar', ['None', 'toolbar2', 'toolmanager'], ignorecase=True)(s)
    if s == 'toolmanager':
        _api.warn_external(
            "Treat the new Tool classes introduced in v1.5 as experimental "
            "for now; the API and rcParam may change in future versions.")
    return s


def validate_color_or_inherit(s):
    """Return a valid color arg."""
    if cbook._str_equal(s, 'inherit'):
        return s
    return validate_color(s)


def validate_color_or_auto(s):
    if cbook._str_equal(s, 'auto'):
        return s
    return validate_color(s)


def validate_color_for_prop_cycle(s):
    # N-th color cycle syntax can't go into the color cycle.
    if isinstance(s, str) and re.match("^C[0-9]$", s):
        raise ValueError(f"Cannot put cycle reference ({s!r}) in prop_cycler")
    return validate_color(s)


def _validate_color_or_linecolor(s):
    if cbook._str_equal(s, 'linecolor'):
        return s
    elif cbook._str_equal(s, 'mfc') or cbook._str_equal(s, 'markerfacecolor'):
        return 'markerfacecolor'
    elif cbook._str_equal(s, 'mec') or cbook._str_equal(s, 'markeredgecolor'):
        return 'markeredgecolor'
    elif s is None:
        return None
    elif isinstance(s, str) and len(s) == 6 or len(s) == 8:
        stmp = '#' + s
        if is_color_like(stmp):
            return stmp
        if s.lower() == 'none':
            return None
    elif is_color_like(s):
        return s

    raise ValueError(f'{s!r} does not look like a color arg')


def validate_color(s):
    """Return a valid color arg."""
    if isinstance(s, str):
        if s.lower() == 'none':
            return 'none'
        if len(s) == 6 or len(s) == 8:
            stmp = '#' + s
            if is_color_like(stmp):
                return stmp

    if is_color_like(s):
        return s

    # If it is still valid, it must be a tuple (as a string from matplotlibrc).
    try:
        color = ast.literal_eval(s)
    except (SyntaxError, ValueError):
        pass
    else:
        if is_color_like(color):
            return color

    raise ValueError(f'{s!r} does not look like a color arg')


validate_colorlist = _listify_validator(
    validate_color, allow_stringlist=True, doc='return a list of colorspecs')


def _validate_cmap(s):
    _api.check_isinstance((str, Colormap), cmap=s)
    return s


def validate_aspect(s):
    if s in ('auto', 'equal'):
        return s
    try:
        return float(s)
    except ValueError as e:
        raise ValueError('not a valid aspect specification') from e


def validate_fontsize_None(s):
    if s is None or s == 'None':
        return None
    else:
        return validate_fontsize(s)


def validate_fontsize(s):
    fontsizes = ['xx-small', 'x-small', 'small', 'medium', 'large',
                 'x-large', 'xx-large', 'smaller', 'larger']
    if isinstance(s, str):
        s = s.lower()
    if s in fontsizes:
        return s
    try:
        return float(s)
    except ValueError as e:
        raise ValueError("%s is not a valid font size. Valid font sizes "
                         "are %s." % (s, ", ".join(fontsizes))) from e


validate_fontsizelist = _listify_validator(validate_fontsize)


def validate_fontweight(s):
    weights = [
        'ultralight', 'light', 'normal', 'regular', 'book', 'medium', 'roman',
        'semibold', 'demibold', 'demi', 'bold', 'heavy', 'extra bold', 'black']
    # Note: Historically, weights have been case-sensitive in Matplotlib
    if s in weights:
        return s
    try:
        return int(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f'{s} is not a valid font weight.') from e


def validate_fontstretch(s):
    stretchvalues = [
        'ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed',
        'normal', 'semi-expanded', 'expanded', 'extra-expanded',
        'ultra-expanded']
    # Note: Historically, stretchvalues have been case-sensitive in Matplotlib
    if s in stretchvalues:
        return s
    try:
        return int(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f'{s} is not a valid font stretch.') from e


def validate_font_properties(s):
    parse_fontconfig_pattern(s)
    return s


def _validate_mathtext_fallback(s):
    _fallback_fonts = ['cm', 'stix', 'stixsans']
    if isinstance(s, str):
        s = s.lower()
    if s is None or s == 'none':
        return None
    elif s.lower() in _fallback_fonts:
        return s
    else:
        raise ValueError(
            f"{s} is not a valid fallback font name. Valid fallback font "
            f"names are {','.join(_fallback_fonts)}. Passing 'None' will turn "
            "fallback off.")


def validate_whiskers(s):
    try:
        return _listify_validator(validate_float, n=2)(s)
    except (TypeError, ValueError):
        try:
            return float(s)
        except ValueError as e:
            raise ValueError("Not a valid whisker value [float, "
                             "(float, float)]") from e


def validate_ps_distiller(s):
    if isinstance(s, str):
        s = s.lower()
    if s in ('none', None, 'false', False):
        return None
    else:
        return ValidateInStrings('ps.usedistiller', ['ghostscript', 'xpdf'])(s)


# A validator dedicated to the named line styles, based on the items in
# ls_mapper, and a list of possible strings read from Line2D.set_linestyle
_validate_named_linestyle = ValidateInStrings(
    'linestyle',
    [*ls_mapper.keys(), *ls_mapper.values(), 'None', 'none', ' ', ''],
    ignorecase=True)


def _validate_linestyle(ls):
    """
    A validator for all possible line styles, the named ones *and*
    the on-off ink sequences.
    """
    if isinstance(ls, str):
        try:  # Look first for a valid named line style, like '--' or 'solid'.
            return _validate_named_linestyle(ls)
        except ValueError:
            pass
        try:
            ls = ast.literal_eval(ls)  # Parsing matplotlibrc.
        except (SyntaxError, ValueError):
            pass  # Will error with the ValueError at the end.

    def _is_iterable_not_string_like(x):
        # Explicitly exclude bytes/bytearrays so that they are not
        # nonsensically interpreted as sequences of numbers (codepoints).
        return np.iterable(x) and not isinstance(x, (str, bytes, bytearray))

    if _is_iterable_not_string_like(ls):
        if len(ls) == 2 and _is_iterable_not_string_like(ls[1]):
            # (offset, (on, off, on, off, ...))
            offset, onoff = ls
        else:
            # For backcompat: (on, off, on, off, ...); the offset is implicit.
            offset = 0
            onoff = ls

        if (isinstance(offset, Real)
                and len(onoff) % 2 == 0
                and all(isinstance(elem, Real) for elem in onoff)):
            return (offset, onoff)

    raise ValueError(f"linestyle {ls!r} is not a valid on-off ink sequence.")


validate_fillstyle = ValidateInStrings(
    'markers.fillstyle', ['full', 'left', 'right', 'bottom', 'top', 'none'])


validate_fillstylelist = _listify_validator(validate_fillstyle)


def validate_markevery(s):
    """
    Validate the markevery property of a Line2D object.

    Parameters
    ----------
    s : None, int, (int, int), slice, float, (float, float), or list[int]

    Returns
    -------
    None, int, (int, int), slice, float, (float, float), or list[int]
    """
    # Validate s against type slice float int and None
    if isinstance(s, (slice, float, int, type(None))):
        return s
    # Validate s against type tuple
    if isinstance(s, tuple):
        if (len(s) == 2
                and (all(isinstance(e, int) for e in s)
                     or all(isinstance(e, float) for e in s))):
            return s
        else:
            raise TypeError(
                "'markevery' tuple must be pair of ints or of floats")
    # Validate s against type list
    if isinstance(s, list):
        if all(isinstance(e, int) for e in s):
            return s
        else:
            raise TypeError(
                "'markevery' list must have all elements of type int")
    raise TypeError("'markevery' is of an invalid type")


validate_markeverylist = _listify_validator(validate_markevery)


def validate_bbox(s):
    if isinstance(s, str):
        s = s.lower()
        if s == 'tight':
            return s
        if s == 'standard':
            return None
        raise ValueError("bbox should be 'tight' or 'standard'")
    elif s is not None:
        # Backwards compatibility. None is equivalent to 'standard'.
        raise ValueError("bbox should be 'tight' or 'standard'")
    return s


def validate_sketch(s):

    if isinstance(s, str):
        s = s.lower().strip()
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1]
    if s == 'none' or s is None:
        return None
    try:
        return tuple(_listify_validator(validate_float, n=3)(s))
    except ValueError as exc:
        raise ValueError("Expected a (scale, length, randomness) tuple") from exc


def _validate_greaterthan_minushalf(s):
    s = validate_float(s)
    if s > -0.5:
        return s
    else:
        raise RuntimeError(f'Value must be >-0.5; got {s}')


def _validate_greaterequal0_lessequal1(s):
    s = validate_float(s)
    if 0 <= s <= 1:
        return s
    else:
        raise RuntimeError(f'Value must be >=0 and <=1; got {s}')


def _validate_int_greaterequal0(s):
    s = validate_int(s)
    if s >= 0:
        return s
    else:
        raise RuntimeError(f'Value must be >=0; got {s}')


def validate_hatch(s):
    r"""
    Validate a hatch pattern.
    A hatch pattern string can have any sequence of the following
    characters: ``\ / | - + * . x o O``.
    """
    if not isinstance(s, str):
        raise ValueError("Hatch pattern must be a string")
    _api.check_isinstance(str, hatch_pattern=s)
    unknown = set(s) - {'\\', '/', '|', '-', '+', '*', '.', 'x', 'o', 'O'}
    if unknown:
        raise ValueError("Unknown hatch symbol(s): %s" % list(unknown))
    return s


validate_hatchlist = _listify_validator(validate_hatch)
validate_dashlist = _listify_validator(validate_floatlist)


def _validate_minor_tick_ndivs(n):
    """
    Validate ndiv parameter related to the minor ticks.
    It controls the number of minor ticks to be placed between
    two major ticks.
    """

    if cbook._str_lower_equal(n, 'auto'):
        return n
    try:
        n = _validate_int_greaterequal0(n)
        return n
    except (RuntimeError, ValueError):
        pass

    raise ValueError("'tick.minor.ndivs' must be 'auto' or non-negative int")


_prop_validators = {
        'color': _listify_validator(validate_color_for_prop_cycle,
                                    allow_stringlist=True),
        'linewidth': validate_floatlist,
        'linestyle': _listify_validator(_validate_linestyle),
        'facecolor': validate_colorlist,
        'edgecolor': validate_colorlist,
        'joinstyle': _listify_validator(JoinStyle),
        'capstyle': _listify_validator(CapStyle),
        'fillstyle': validate_fillstylelist,
        'markerfacecolor': validate_colorlist,
        'markersize': validate_floatlist,
        'markeredgewidth': validate_floatlist,
        'markeredgecolor': validate_colorlist,
        'markevery': validate_markeverylist,
        'alpha': validate_floatlist,
        'marker': _validate_markerlist,
        'hatch': validate_hatchlist,
        'dashes': validate_dashlist,
    }
_prop_aliases = {
        'c': 'color',
        'lw': 'linewidth',
        'ls': 'linestyle',
        'fc': 'facecolor',
        'ec': 'edgecolor',
        'mfc': 'markerfacecolor',
        'mec': 'markeredgecolor',
        'mew': 'markeredgewidth',
        'ms': 'markersize',
    }


def cycler(*args, **kwargs):
    """
    Create a `~cycler.Cycler` object much like :func:`cycler.cycler`,
    but includes input validation.

    Call signatures::

      cycler(cycler)
      cycler(label=values, label2=values2, ...)
      cycler(label, values)

    Form 1 copies a given `~cycler.Cycler` object.

    Form 2 creates a `~cycler.Cycler` which cycles over one or more
    properties simultaneously. If multiple properties are given, their
    value lists must have the same length.

    Form 3 creates a `~cycler.Cycler` for a single property. This form
    exists for compatibility with the original cycler. Its use is
    discouraged in favor of the kwarg form, i.e. ``cycler(label=values)``.

    Parameters
    ----------
    cycler : Cycler
        Copy constructor for Cycler.

    label : str
        The property key. Must be a valid `.Artist` property.
        For example, 'color' or 'linestyle'. Aliases are allowed,
        such as 'c' for 'color' and 'lw' for 'linewidth'.

    values : iterable
        Finite-length iterable of the property values. These values
        are validated and will raise a ValueError if invalid.

    Returns
    -------
    Cycler
        A new :class:`~cycler.Cycler` for the given properties.

    Examples
    --------
    Creating a cycler for a single property:

    >>> c = cycler(color=['red', 'green', 'blue'])

    Creating a cycler for simultaneously cycling over multiple properties
    (e.g. red circle, green plus, blue cross):

    >>> c = cycler(color=['red', 'green', 'blue'],
    ...            marker=['o', '+', 'x'])

    """
    if args and kwargs:
        raise TypeError("cycler() can only accept positional OR keyword "
                        "arguments -- not both.")
    elif not args and not kwargs:
        raise TypeError("cycler() must have positional OR keyword arguments")

    if len(args) == 1:
        if not isinstance(args[0], Cycler):
            raise TypeError("If only one positional argument given, it must "
                            "be a Cycler instance.")
        return validate_cycler(args[0])
    elif len(args) == 2:
        pairs = [(args[0], args[1])]
    elif len(args) > 2:
        raise _api.nargs_error('cycler', '0-2', len(args))
    else:
        pairs = kwargs.items()

    validated = []
    for prop, vals in pairs:
        norm_prop = _prop_aliases.get(prop, prop)
        validator = _prop_validators.get(norm_prop, None)
        if validator is None:
            raise TypeError("Unknown artist property: %s" % prop)
        vals = validator(vals)
        # We will normalize the property names as well to reduce
        # the amount of alias handling code elsewhere.
        validated.append((norm_prop, vals))

    return reduce(operator.add, (ccycler(k, v) for k, v in validated))


class _DunderChecker(ast.NodeVisitor):
    def visit_Attribute(self, node):
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise ValueError("cycler strings with dunders are forbidden")
        self.generic_visit(node)


# A validator dedicated to the named legend loc
_validate_named_legend_loc = ValidateInStrings(
    'legend.loc',
    [
        "best",
        "upper right", "upper left", "lower left", "lower right", "right",
        "center left", "center right", "lower center", "upper center",
        "center"],
    ignorecase=True)


def _validate_legend_loc(loc):
    """
    Confirm that loc is a type which rc.Params["legend.loc"] supports.

    .. versionadded:: 3.8

    Parameters
    ----------
    loc : str | int | (float, float) | str((float, float))
        The location of the legend.

    Returns
    -------
    loc : str | int | (float, float) or raise ValueError exception
        The location of the legend.
    """
    if isinstance(loc, str):
        try:
            return _validate_named_legend_loc(loc)
        except ValueError:
            pass
        try:
            loc = ast.literal_eval(loc)
        except (SyntaxError, ValueError):
            pass
    if isinstance(loc, int):
        if 0 <= loc <= 10:
            return loc
    if isinstance(loc, tuple):
        if len(loc) == 2 and all(isinstance(e, Real) for e in loc):
            return loc
    raise ValueError(f"{loc} is not a valid legend location.")


def validate_cycler(s):
    """Return a Cycler object from a string repr or the object itself."""
    if isinstance(s, str):
        # TODO: We might want to rethink this...
        # While I think I have it quite locked down, it is execution of
        # arbitrary code without sanitation.
        # Combine this with the possibility that rcparams might come from the
        # internet (future plans), this could be downright dangerous.
        # I locked it down by only having the 'cycler()' function available.
        # UPDATE: Partly plugging a security hole.
        # I really should have read this:
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        # We should replace this eval with a combo of PyParsing and
        # ast.literal_eval()
        try:
            _DunderChecker().visit(ast.parse(s))
            s = eval(s, {'cycler': cycler, '__builtins__': {}})
        except BaseException as e:
            raise ValueError(f"{s!r} is not a valid cycler construction: {e}"
                             ) from e
    # Should make sure what comes from the above eval()
    # is a Cycler object.
    if isinstance(s, Cycler):
        cycler_inst = s
    else:
        raise ValueError(f"Object is not a string or Cycler instance: {s!r}")

    unknowns = cycler_inst.keys - (set(_prop_validators) | set(_prop_aliases))
    if unknowns:
        raise ValueError("Unknown artist properties: %s" % unknowns)

    # Not a full validation, but it'll at least normalize property names
    # A fuller validation would require v0.10 of cycler.
    checker = set()
    for prop in cycler_inst.keys:
        norm_prop = _prop_aliases.get(prop, prop)
        if norm_prop != prop and norm_prop in cycler_inst.keys:
            raise ValueError(f"Cannot specify both {norm_prop!r} and alias "
                             f"{prop!r} in the same prop_cycle")
        if norm_prop in checker:
            raise ValueError(f"Another property was already aliased to "
                             f"{norm_prop!r}. Collision normalizing {prop!r}.")
        checker.update([norm_prop])

    # This is just an extra-careful check, just in case there is some
    # edge-case I haven't thought of.
    assert len(checker) == len(cycler_inst.keys)

    # Now, it should be safe to mutate this cycler
    for prop in cycler_inst.keys:
        norm_prop = _prop_aliases.get(prop, prop)
        cycler_inst.change_key(prop, norm_prop)

    for key, vals in cycler_inst.by_key().items():
        _prop_validators[key](vals)

    return cycler_inst


def validate_hist_bins(s):
    valid_strs = ["auto", "sturges", "fd", "doane", "scott", "rice", "sqrt"]
    if isinstance(s, str) and s in valid_strs:
        return s
    try:
        return int(s)
    except (TypeError, ValueError):
        pass
    try:
        return validate_floatlist(s)
    except ValueError:
        pass
    raise ValueError(f"'hist.bins' must be one of {valid_strs}, an int or"
                     " a sequence of floats")


class _ignorecase(list):
    """A marker class indicating that a list-of-str is case-insensitive."""


def _convert_validator_spec(key, conv):
    if isinstance(conv, list):
        ignorecase = isinstance(conv, _ignorecase)
        return ValidateInStrings(key, conv, ignorecase=ignorecase)
    else:
        return conv


# Mapping of rcParams to validators.
# Converters given as lists or _ignorecase are converted to ValidateInStrings
# immediately below.
# The rcParams defaults are defined in lib/matplotlib/mpl-data/matplotlibrc, which
# gets copied to matplotlib/mpl-data/matplotlibrc by the setup script.
_validators = {
    "backend":           validate_backend,
    "backend_fallback":  validate_bool,
    "figure.hooks":      validate_stringlist,
    "toolbar":           _validate_toolbar,
    "interactive":       validate_bool,
    "timezone":          validate_string,

    "webagg.port":            validate_int,
    "webagg.address":         validate_string,
    "webagg.open_in_browser": validate_bool,
    "webagg.port_retries":    validate_int,

    # line props
    "lines.linewidth":       validate_float,  # line width in points
    "lines.linestyle":       _validate_linestyle,  # solid line
    "lines.color":           validate_color,  # first color in color cycle
    "lines.marker":          _validate_marker,  # marker name
    "lines.markerfacecolor": validate_color_or_auto,  # default color
    "lines.markeredgecolor": validate_color_or_auto,  # default color
    "lines.markeredgewidth": validate_float,
    "lines.markersize":      validate_float,  # markersize, in points
    "lines.antialiased":     validate_bool,  # antialiased (no jaggies)
    "lines.dash_joinstyle":  JoinStyle,
    "lines.solid_joinstyle": JoinStyle,
    "lines.dash_capstyle":   CapStyle,
    "lines.solid_capstyle":  CapStyle,
    "lines.dashed_pattern":  validate_floatlist,
    "lines.dashdot_pattern": validate_floatlist,
    "lines.dotted_pattern":  validate_floatlist,
    "lines.scale_dashes":    validate_bool,

    # marker props
    "markers.fillstyle": validate_fillstyle,

    ## pcolor(mesh) props:
    "pcolor.shading": ["auto", "flat", "nearest", "gouraud"],
    "pcolormesh.snap": validate_bool,

    ## patch props
    "patch.linewidth":       validate_float,  # line width in points
    "patch.edgecolor":       validate_color,
    "patch.force_edgecolor": validate_bool,
    "patch.facecolor":       validate_color,  # first color in cycle
    "patch.antialiased":     validate_bool,  # antialiased (no jaggies)

    ## hatch props
    "hatch.color":     validate_color,
    "hatch.linewidth": validate_float,

    ## Histogram properties
    "hist.bins": validate_hist_bins,

    ## Boxplot properties
    "boxplot.notch":       validate_bool,
    "boxplot.vertical":    validate_bool,
    "boxplot.whiskers":    validate_whiskers,
    "boxplot.bootstrap":   validate_int_or_None,
    "boxplot.patchartist": validate_bool,
    "boxplot.showmeans":   validate_bool,
    "boxplot.showcaps":    validate_bool,
    "boxplot.showbox":     validate_bool,
    "boxplot.showfliers":  validate_bool,
    "boxplot.meanline":    validate_bool,

    "boxplot.flierprops.color":           validate_color,
    "boxplot.flierprops.marker":          _validate_marker,
    "boxplot.flierprops.markerfacecolor": validate_color_or_auto,
    "boxplot.flierprops.markeredgecolor": validate_color,
    "boxplot.flierprops.markeredgewidth": validate_float,
    "boxplot.flierprops.markersize":      validate_float,
    "boxplot.flierprops.linestyle":       _validate_linestyle,
    "boxplot.flierprops.linewidth":       validate_float,

    "boxplot.boxprops.color":     validate_color,
    "boxplot.boxprops.linewidth": validate_float,
    "boxplot.boxprops.linestyle": _validate_linestyle,

    "boxplot.whiskerprops.color":     validate_color,
    "boxplot.whiskerprops.linewidth": validate_float,
    "boxplot.whiskerprops.linestyle": _validate_linestyle,

    "boxplot.capprops.color":     validate_color,
    "boxplot.capprops.linewidth": validate_float,
    "boxplot.capprops.linestyle": _validate_linestyle,

    "boxplot.medianprops.color":     validate_color,
    "boxplot.medianprops.linewidth": validate_float,
    "boxplot.medianprops.linestyle": _validate_linestyle,

    "boxplot.meanprops.color":           validate_color,
    "boxplot.meanprops.marker":          _validate_marker,
    "boxplot.meanprops.markerfacecolor": validate_color,
    "boxplot.meanprops.markeredgecolor": validate_color,
    "boxplot.meanprops.markersize":      validate_float,
    "boxplot.meanprops.linestyle":       _validate_linestyle,
    "boxplot.meanprops.linewidth":       validate_float,

    ## font props
    "font.family":     validate_stringlist,  # used by text object
    "font.style":      validate_string,
    "font.variant":    validate_string,
    "font.stretch":    validate_fontstretch,
    "font.weight":     validate_fontweight,
    "font.size":       validate_float,  # Base font size in points
    "font.serif":      validate_stringlist,
    "font.sans-serif": validate_stringlist,
    "font.cursive":    validate_stringlist,
    "font.fantasy":    validate_stringlist,
    "font.monospace":  validate_stringlist,

    # text props
    "text.color":          validate_color,
    "text.usetex":         validate_bool,
    "text.latex.preamble": validate_string,
    "text.hinting":        ["default", "no_autohint", "force_autohint",
                            "no_hinting", "auto", "native", "either", "none"],
    "text.hinting_factor": validate_int,
    "text.kerning_factor": validate_int,
    "text.antialiased":    validate_bool,
    "text.parse_math":     validate_bool,

    "mathtext.cal":            validate_font_properties,
    "mathtext.rm":             validate_font_properties,
    "mathtext.tt":             validate_font_properties,
    "mathtext.it":             validate_font_properties,
    "mathtext.bf":             validate_font_properties,
    "mathtext.bfit":           validate_font_properties,
    "mathtext.sf":             validate_font_properties,
    "mathtext.fontset":        ["dejavusans", "dejavuserif", "cm", "stix",
                                "stixsans", "custom"],
    "mathtext.default":        ["rm", "cal", "bfit", "it", "tt", "sf", "bf", "default",
                                "bb", "frak", "scr", "regular"],
    "mathtext.fallback":       _validate_mathtext_fallback,

    "image.aspect":              validate_aspect,  # equal, auto, a number
    "image.interpolation":       validate_string,
    "image.interpolation_stage": ["auto", "data", "rgba"],
    "image.cmap":                _validate_cmap,  # gray, jet, etc.
    "image.lut":                 validate_int,  # lookup table
    "image.origin":              ["upper", "lower"],
    "image.resample":            validate_bool,
    # Specify whether vector graphics backends will combine all images on a
    # set of Axes into a single composite image
    "image.composite_image": validate_bool,

    # contour props
    "contour.negative_linestyle": _validate_linestyle,
    "contour.corner_mask":        validate_bool,
    "contour.linewidth":          validate_float_or_None,
    "contour.algorithm":          ["mpl2005", "mpl2014", "serial", "threaded"],

    # errorbar props
    "errorbar.capsize": validate_float,

    # axis props
    # alignment of x/y axis title
    "xaxis.labellocation": ["left", "center", "right"],
    "yaxis.labellocation": ["bottom", "center", "top"],

    # Axes props
    "axes.axisbelow":        validate_axisbelow,
    "axes.facecolor":        validate_color,  # background color
    "axes.edgecolor":        validate_color,  # edge color
    "axes.linewidth":        validate_float,  # edge linewidth

    "axes.spines.left":      validate_bool,  # Set visibility of axes spines,
    "axes.spines.right":     validate_bool,  # i.e., the lines around the chart
    "axes.spines.bottom":    validate_bool,  # denoting data boundary.
    "axes.spines.top":       validate_bool,

    "axes.titlesize":     validate_fontsize,  # Axes title fontsize
    "axes.titlelocation": ["left", "center", "right"],  # Axes title alignment
    "axes.titleweight":   validate_fontweight,  # Axes title font weight
    "axes.titlecolor":    validate_color_or_auto,  # Axes title font color
    # title location, axes units, None means auto
    "axes.titley":        validate_float_or_None,
    # pad from Axes top decoration to title in points
    "axes.titlepad":      validate_float,
    "axes.grid":          validate_bool,  # display grid or not
    "axes.grid.which":    ["minor", "both", "major"],  # which grids are drawn
    "axes.grid.axis":     ["x", "y", "both"],  # grid type
    "axes.labelsize":     validate_fontsize,  # fontsize of x & y labels
    "axes.labelpad":      validate_float,  # space between label and axis
    "axes.labelweight":   validate_fontweight,  # fontsize of x & y labels
    "axes.labelcolor":    validate_color,  # color of axis label
    # use scientific notation if log10 of the axis range is smaller than the
    # first or larger than the second
    "axes.formatter.limits": _listify_validator(validate_int, n=2),
    # use current locale to format ticks
    "axes.formatter.use_locale": validate_bool,
    "axes.formatter.use_mathtext": validate_bool,
    # minimum exponent to format in scientific notation
    "axes.formatter.min_exponent": validate_int,
    "axes.formatter.useoffset": validate_bool,
    "axes.formatter.offset_threshold": validate_int,
    "axes.unicode_minus": validate_bool,
    # This entry can be either a cycler object or a string repr of a
    # cycler-object, which gets eval()'ed to create the object.
    "axes.prop_cycle": validate_cycler,
    # If "data", axes limits are set close to the data.
    # If "round_numbers" axes limits are set to the nearest round numbers.
    "axes.autolimit_mode": ["data", "round_numbers"],
    "axes.xmargin": _validate_greaterthan_minushalf,  # margin added to xaxis
    "axes.ymargin": _validate_greaterthan_minushalf,  # margin added to yaxis
    "axes.zmargin": _validate_greaterthan_minushalf,  # margin added to zaxis

    "polaraxes.grid":    validate_bool,  # display polar grid or not
    "axes3d.grid":       validate_bool,  # display 3d grid
    "axes3d.automargin": validate_bool,  # automatically add margin when
                                         # manually setting 3D axis limits

    "axes3d.xaxis.panecolor":    validate_color,  # 3d background pane
    "axes3d.yaxis.panecolor":    validate_color,  # 3d background pane
    "axes3d.zaxis.panecolor":    validate_color,  # 3d background pane

    "axes3d.mouserotationstyle": ["azel", "trackball", "sphere", "arcball"],
    "axes3d.trackballsize": validate_float,
    "axes3d.trackballborder": validate_float,

    # scatter props
    "scatter.marker":     _validate_marker,
    "scatter.edgecolors": validate_string,

    "date.epoch": _validate_date,
    "date.autoformatter.year":        validate_string,
    "date.autoformatter.month":       validate_string,
    "date.autoformatter.day":         validate_string,
    "date.autoformatter.hour":        validate_string,
    "date.autoformatter.minute":      validate_string,
    "date.autoformatter.second":      validate_string,
    "date.autoformatter.microsecond": validate_string,

    'date.converter':          ['auto', 'concise'],
    # for auto date locator, choose interval_multiples
    'date.interval_multiples': validate_bool,

    # legend properties
    "legend.fancybox": validate_bool,
    "legend.loc": _validate_legend_loc,

    # the number of points in the legend line
    "legend.numpoints":      validate_int,
    # the number of points in the legend line for scatter
    "legend.scatterpoints":  validate_int,
    "legend.fontsize":       validate_fontsize,
    "legend.title_fontsize": validate_fontsize_None,
    # color of the legend
    "legend.labelcolor":     _validate_color_or_linecolor,
    # the relative size of legend markers vs. original
    "legend.markerscale":    validate_float,
    # using dict in rcParams not yet supported, so make sure it is bool
    "legend.shadow":         validate_bool,
    # whether or not to draw a frame around legend
    "legend.frameon":        validate_bool,
    # alpha value of the legend frame
    "legend.framealpha":     validate_float_or_None,

    ## the following dimensions are in fraction of the font size
    "legend.borderpad":      validate_float,  # units are fontsize
    # the vertical space between the legend entries
    "legend.labelspacing":   validate_float,
    # the length of the legend lines
    "legend.handlelength":   validate_float,
    # the length of the legend lines
    "legend.handleheight":   validate_float,
    # the space between the legend line and legend text
    "legend.handletextpad":  validate_float,
    # the border between the Axes and legend edge
    "legend.borderaxespad":  validate_float,
    # the border between the Axes and legend edge
    "legend.columnspacing":  validate_float,
    "legend.facecolor":      validate_color_or_inherit,
    "legend.edgecolor":      validate_color_or_inherit,

    # tick properties
    "xtick.top":           validate_bool,      # draw ticks on top side
    "xtick.bottom":        validate_bool,      # draw ticks on bottom side
    "xtick.labeltop":      validate_bool,      # draw label on top
    "xtick.labelbottom":   validate_bool,      # draw label on bottom
    "xtick.major.size":    validate_float,     # major xtick size in points
    "xtick.minor.size":    validate_float,     # minor xtick size in points
    "xtick.major.width":   validate_float,     # major xtick width in points
    "xtick.minor.width":   validate_float,     # minor xtick width in points
    "xtick.major.pad":     validate_float,     # distance to label in points
    "xtick.minor.pad":     validate_float,     # distance to label in points
    "xtick.color":         validate_color,     # color of xticks
    "xtick.labelcolor":    validate_color_or_inherit,  # color of xtick labels
    "xtick.minor.visible": validate_bool,      # visibility of minor xticks
    "xtick.minor.top":     validate_bool,      # draw top minor xticks
    "xtick.minor.bottom":  validate_bool,      # draw bottom minor xticks
    "xtick.major.top":     validate_bool,      # draw top major xticks
    "xtick.major.bottom":  validate_bool,      # draw bottom major xticks
    # number of minor xticks
    "xtick.minor.ndivs":   _validate_minor_tick_ndivs,
    "xtick.labelsize":     validate_fontsize,  # fontsize of xtick labels
    "xtick.direction":     ["out", "in", "inout"],  # direction of xticks
    "xtick.alignment":     ["center", "right", "left"],

    "ytick.left":          validate_bool,      # draw ticks on left side
    "ytick.right":         validate_bool,      # draw ticks on right side
    "ytick.labelleft":     validate_bool,      # draw tick labels on left side
    "ytick.labelright":    validate_bool,      # draw tick labels on right side
    "ytick.major.size":    validate_float,     # major ytick size in points
    "ytick.minor.size":    validate_float,     # minor ytick size in points
    "ytick.major.width":   validate_float,     # major ytick width in points
    "ytick.minor.width":   validate_float,     # minor ytick width in points
    "ytick.major.pad":     validate_float,     # distance to label in points
    "ytick.minor.pad":     validate_float,     # distance to label in points
    "ytick.color":         validate_color,     # color of yticks
    "ytick.labelcolor":    validate_color_or_inherit,  # color of ytick labels
    "ytick.minor.visible": validate_bool,      # visibility of minor yticks
    "ytick.minor.left":    validate_bool,      # draw left minor yticks
    "ytick.minor.right":   validate_bool,      # draw right minor yticks
    "ytick.major.left":    validate_bool,      # draw left major yticks
    "ytick.major.right":   validate_bool,      # draw right major yticks
    # number of minor yticks
    "ytick.minor.ndivs":   _validate_minor_tick_ndivs,
    "ytick.labelsize":     validate_fontsize,  # fontsize of ytick labels
    "ytick.direction":     ["out", "in", "inout"],  # direction of yticks
    "ytick.alignment":     [
        "center", "top", "bottom", "baseline", "center_baseline"],

    "grid.color":        validate_color,  # grid color
    "grid.linestyle":    _validate_linestyle,  # solid
    "grid.linewidth":    validate_float,     # in points
    "grid.alpha":        validate_float,

    ## figure props
    # figure title
    "figure.titlesize":   validate_fontsize,
    "figure.titleweight": validate_fontweight,

    # figure labels
    "figure.labelsize":   validate_fontsize,
    "figure.labelweight": validate_fontweight,

    # figure size in inches: width by height
    "figure.figsize":          _listify_validator(validate_float, n=2),
    "figure.dpi":              validate_float,
    "figure.facecolor":        validate_color,
    "figure.edgecolor":        validate_color,
    "figure.frameon":          validate_bool,
    "figure.autolayout":       validate_bool,
    "figure.max_open_warning": validate_int,
    "figure.raise_window":     validate_bool,
    "macosx.window_mode":      ["system", "tab", "window"],

    "figure.subplot.left":   validate_float,
    "figure.subplot.right":  validate_float,
    "figure.subplot.bottom": validate_float,
    "figure.subplot.top":    validate_float,
    "figure.subplot.wspace": validate_float,
    "figure.subplot.hspace": validate_float,

    "figure.constrained_layout.use": validate_bool,  # run constrained_layout?
    # wspace and hspace are fraction of adjacent subplots to use for space.
    # Much smaller than above because we don't need room for the text.
    "figure.constrained_layout.hspace": validate_float,
    "figure.constrained_layout.wspace": validate_float,
    # buffer around the Axes, in inches.
    "figure.constrained_layout.h_pad": validate_float,
    "figure.constrained_layout.w_pad": validate_float,

    ## Saving figure's properties
    'savefig.dpi':          validate_dpi,
    'savefig.facecolor':    validate_color_or_auto,
    'savefig.edgecolor':    validate_color_or_auto,
    'savefig.orientation':  ['landscape', 'portrait'],
    "savefig.format":       validate_string,
    "savefig.bbox":         validate_bbox,  # "tight", or "standard" (= None)
    "savefig.pad_inches":   validate_float,
    # default directory in savefig dialog box
    "savefig.directory":    _validate_pathlike,
    "savefig.transparent":  validate_bool,

    "tk.window_focus": validate_bool,  # Maintain shell focus for TkAgg

    # Set the papersize/type
    "ps.papersize":       _ignorecase(
                                ["figure", "letter", "legal", "ledger",
                                 *[f"{ab}{i}" for ab in "ab" for i in range(11)]]),
    "ps.useafm":          validate_bool,
    # use ghostscript or xpdf to distill ps output
    "ps.usedistiller":    validate_ps_distiller,
    "ps.distiller.res":   validate_int,  # dpi
    "ps.fonttype":        validate_fonttype,  # 3 (Type3) or 42 (Truetype)
    "pdf.compression":    validate_int,  # 0-9 compression level; 0 to disable
    "pdf.inheritcolor":   validate_bool,  # skip color setting commands
    # use only the 14 PDF core fonts embedded in every PDF viewing application
    "pdf.use14corefonts": validate_bool,
    "pdf.fonttype":       validate_fonttype,  # 3 (Type3) or 42 (Truetype)

    "pgf.texsystem": ["xelatex", "lualatex", "pdflatex"],  # latex variant used
    "pgf.rcfonts":   validate_bool,  # use mpl's rc settings for font config
    "pgf.preamble":  validate_string,  # custom LaTeX preamble

    # write raster image data into the svg file
    "svg.image_inline": validate_bool,
    "svg.fonttype": ["none", "path"],  # save text as text ("none") or "paths"
    "svg.hashsalt": validate_string_or_None,
    "svg.id": validate_string_or_None,

    # set this when you want to generate hardcopy docstring
    "docstring.hardcopy": validate_bool,

    "path.simplify":           validate_bool,
    "path.simplify_threshold": _validate_greaterequal0_lessequal1,
    "path.snap":               validate_bool,
    "path.sketch":             validate_sketch,
    "path.effects":            validate_anylist,
    "agg.path.chunksize":      validate_int,  # 0 to disable chunking

    # key-mappings (multi-character mappings should be a list/tuple)
    "keymap.fullscreen": validate_stringlist,
    "keymap.home":       validate_stringlist,
    "keymap.back":       validate_stringlist,
    "keymap.forward":    validate_stringlist,
    "keymap.pan":        validate_stringlist,
    "keymap.zoom":       validate_stringlist,
    "keymap.save":       validate_stringlist,
    "keymap.quit":       validate_stringlist,
    "keymap.quit_all":   validate_stringlist,  # e.g.: "W", "cmd+W", "Q"
    "keymap.grid":       validate_stringlist,
    "keymap.grid_minor": validate_stringlist,
    "keymap.yscale":     validate_stringlist,
    "keymap.xscale":     validate_stringlist,
    "keymap.help":       validate_stringlist,
    "keymap.copy":       validate_stringlist,

    # Animation settings
    "animation.html":         ["html5", "jshtml", "none"],
    # Limit, in MB, of size of base64 encoded animation in HTML
    # (i.e. IPython notebook)
    "animation.embed_limit":  validate_float,
    "animation.writer":       validate_string,
    "animation.codec":        validate_string,
    "animation.bitrate":      validate_int,
    # Controls image format when frames are written to disk
    "animation.frame_format": ["png", "jpeg", "tiff", "raw", "rgba", "ppm",
                               "sgi", "bmp", "pbm", "svg"],
    # Path to ffmpeg binary. If just binary name, subprocess uses $PATH.
    "animation.ffmpeg_path":  _validate_pathlike,
    # Additional arguments for ffmpeg movie writer (using pipes)
    "animation.ffmpeg_args":  validate_stringlist,
     # Path to convert binary. If just binary name, subprocess uses $PATH.
    "animation.convert_path": _validate_pathlike,
     # Additional arguments for convert movie writer (using pipes)
    "animation.convert_args": validate_stringlist,

    # Classic (pre 2.0) compatibility mode
    # This is used for things that are hard to make backward compatible
    # with a sane rcParam alone.  This does *not* turn on classic mode
    # altogether.  For that use `matplotlib.style.use("classic")`.
    "_internal.classic_mode": validate_bool
}
_hardcoded_defaults = {  # Defaults not inferred from
    # lib/matplotlib/mpl-data/matplotlibrc...
    # ... because they are private:
    "_internal.classic_mode": False,
    # ... because they are deprecated:
    # No current deprecations.
    # backend is handled separately when constructing rcParamsDefault.
}
_validators = {k: _convert_validator_spec(k, conv)
               for k, conv in _validators.items()}

# === NexusCore/openenv\Lib\site-packages\matplotlib\legend.py ===
"""
The legend module defines the Legend class, which is responsible for
drawing legends associated with Axes and/or figures.

.. important::

    It is unlikely that you would ever create a Legend instance manually.
    Most users would normally create a legend via the `~.Axes.legend`
    function. For more details on legends there is also a :ref:`legend guide
    <legend_guide>`.

The `Legend` class is a container of legend handles and legend texts.

The legend handler map specifies how to create legend handles from artists
(lines, patches, etc.) in the Axes or figures. Default legend handlers are
defined in the :mod:`~matplotlib.legend_handler` module. While not all artist
types are covered by the default legend handlers, custom legend handlers can be
defined to support arbitrary objects.

See the :ref`<legend_guide>` for more
information.
"""

import itertools
import logging
import numbers
import time

import numpy as np

import matplotlib as mpl
from matplotlib import _api, _docstring, cbook, colors, offsetbox
from matplotlib.artist import Artist, allow_rasterization
from matplotlib.cbook import silent_list
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.patches import (Patch, Rectangle, Shadow, FancyBboxPatch,
                                StepPatch)
from matplotlib.collections import (
    Collection, CircleCollection, LineCollection, PathCollection,
    PolyCollection, RegularPolyCollection)
from matplotlib.text import Text
from matplotlib.transforms import Bbox, BboxBase, TransformedBbox
from matplotlib.transforms import BboxTransformTo, BboxTransformFrom
from matplotlib.offsetbox import (
    AnchoredOffsetbox, DraggableOffsetBox,
    HPacker, VPacker,
    DrawingArea, TextArea,
)
from matplotlib.container import ErrorbarContainer, BarContainer, StemContainer
from . import legend_handler


class DraggableLegend(DraggableOffsetBox):
    def __init__(self, legend, use_blit=False, update="loc"):
        """
        Wrapper around a `.Legend` to support mouse dragging.

        Parameters
        ----------
        legend : `.Legend`
            The `.Legend` instance to wrap.
        use_blit : bool, optional
            Use blitting for faster image composition. For details see
            :ref:`func-animation`.
        update : {'loc', 'bbox'}, optional
            If "loc", update the *loc* parameter of the legend upon finalizing.
            If "bbox", update the *bbox_to_anchor* parameter.
        """
        self.legend = legend

        _api.check_in_list(["loc", "bbox"], update=update)
        self._update = update

        super().__init__(legend, legend._legend_box, use_blit=use_blit)

    def finalize_offset(self):
        if self._update == "loc":
            self._update_loc(self.get_loc_in_canvas())
        elif self._update == "bbox":
            self._update_bbox_to_anchor(self.get_loc_in_canvas())

    def _update_loc(self, loc_in_canvas):
        bbox = self.legend.get_bbox_to_anchor()
        # if bbox has zero width or height, the transformation is
        # ill-defined. Fall back to the default bbox_to_anchor.
        if bbox.width == 0 or bbox.height == 0:
            self.legend.set_bbox_to_anchor(None)
            bbox = self.legend.get_bbox_to_anchor()
        _bbox_transform = BboxTransformFrom(bbox)
        self.legend._loc = tuple(_bbox_transform.transform(loc_in_canvas))

    def _update_bbox_to_anchor(self, loc_in_canvas):
        loc_in_bbox = self.legend.axes.transAxes.transform(loc_in_canvas)
        self.legend.set_bbox_to_anchor(loc_in_bbox)


_legend_kw_doc_base = """
bbox_to_anchor : `.BboxBase`, 2-tuple, or 4-tuple of floats
    Box that is used to position the legend in conjunction with *loc*.
    Defaults to ``axes.bbox`` (if called as a method to `.Axes.legend`) or
    ``figure.bbox`` (if ``figure.legend``).  This argument allows arbitrary
    placement of the legend.

    Bbox coordinates are interpreted in the coordinate system given by
    *bbox_transform*, with the default transform
    Axes or Figure coordinates, depending on which ``legend`` is called.

    If a 4-tuple or `.BboxBase` is given, then it specifies the bbox
    ``(x, y, width, height)`` that the legend is placed in.
    To put the legend in the best location in the bottom right
    quadrant of the Axes (or figure)::

        loc='best', bbox_to_anchor=(0.5, 0., 0.5, 0.5)

    A 2-tuple ``(x, y)`` places the corner of the legend specified by *loc* at
    x, y.  For example, to put the legend's upper right-hand corner in the
    center of the Axes (or figure) the following keywords can be used::

        loc='upper right', bbox_to_anchor=(0.5, 0.5)

ncols : int, default: 1
    The number of columns that the legend has.

    For backward compatibility, the spelling *ncol* is also supported
    but it is discouraged. If both are given, *ncols* takes precedence.

prop : None or `~matplotlib.font_manager.FontProperties` or dict
    The font properties of the legend. If None (default), the current
    :data:`matplotlib.rcParams` will be used.

fontsize : int or {'xx-small', 'x-small', 'small', 'medium', 'large', \
'x-large', 'xx-large'}
    The font size of the legend. If the value is numeric the size will be the
    absolute font size in points. String values are relative to the current
    default font size. This argument is only used if *prop* is not specified.

labelcolor : str or list, default: :rc:`legend.labelcolor`
    The color of the text in the legend. Either a valid color string
    (for example, 'red'), or a list of color strings. The labelcolor can
    also be made to match the color of the line or marker using 'linecolor',
    'markerfacecolor' (or 'mfc'), or 'markeredgecolor' (or 'mec').

    Labelcolor can be set globally using :rc:`legend.labelcolor`. If None,
    use :rc:`text.color`.

numpoints : int, default: :rc:`legend.numpoints`
    The number of marker points in the legend when creating a legend
    entry for a `.Line2D` (line).

scatterpoints : int, default: :rc:`legend.scatterpoints`
    The number of marker points in the legend when creating
    a legend entry for a `.PathCollection` (scatter plot).

scatteryoffsets : iterable of floats, default: ``[0.375, 0.5, 0.3125]``
    The vertical offset (relative to the font size) for the markers
    created for a scatter plot legend entry. 0.0 is at the base the
    legend text, and 1.0 is at the top. To draw all markers at the
    same height, set to ``[0.5]``.

markerscale : float, default: :rc:`legend.markerscale`
    The relative size of legend markers compared to the originally drawn ones.

markerfirst : bool, default: True
    If *True*, legend marker is placed to the left of the legend label.
    If *False*, legend marker is placed to the right of the legend label.

reverse : bool, default: False
    If *True*, the legend labels are displayed in reverse order from the input.
    If *False*, the legend labels are displayed in the same order as the input.

    .. versionadded:: 3.7

frameon : bool, default: :rc:`legend.frameon`
    Whether the legend should be drawn on a patch (frame).

fancybox : bool, default: :rc:`legend.fancybox`
    Whether round edges should be enabled around the `.FancyBboxPatch` which
    makes up the legend's background.

shadow : None, bool or dict, default: :rc:`legend.shadow`
    Whether to draw a shadow behind the legend.
    The shadow can be configured using `.Patch` keywords.
    Customization via :rc:`legend.shadow` is currently not supported.

framealpha : float, default: :rc:`legend.framealpha`
    The alpha transparency of the legend's background.
    If *shadow* is activated and *framealpha* is ``None``, the default value is
    ignored.

facecolor : "inherit" or color, default: :rc:`legend.facecolor`
    The legend's background color.
    If ``"inherit"``, use :rc:`axes.facecolor`.

edgecolor : "inherit" or color, default: :rc:`legend.edgecolor`
    The legend's background patch edge color.
    If ``"inherit"``, use :rc:`axes.edgecolor`.

mode : {"expand", None}
    If *mode* is set to ``"expand"`` the legend will be horizontally
    expanded to fill the Axes area (or *bbox_to_anchor* if defines
    the legend's size).

bbox_transform : None or `~matplotlib.transforms.Transform`
    The transform for the bounding box (*bbox_to_anchor*). For a value
    of ``None`` (default) the Axes'
    :data:`~matplotlib.axes.Axes.transAxes` transform will be used.

title : str or None
    The legend's title. Default is no title (``None``).

title_fontproperties : None or `~matplotlib.font_manager.FontProperties` or dict
    The font properties of the legend's title. If None (default), the
    *title_fontsize* argument will be used if present; if *title_fontsize* is
    also None, the current :rc:`legend.title_fontsize` will be used.

title_fontsize : int or {'xx-small', 'x-small', 'small', 'medium', 'large', \
'x-large', 'xx-large'}, default: :rc:`legend.title_fontsize`
    The font size of the legend's title.
    Note: This cannot be combined with *title_fontproperties*. If you want
    to set the fontsize alongside other font properties, use the *size*
    parameter in *title_fontproperties*.

alignment : {'center', 'left', 'right'}, default: 'center'
    The alignment of the legend title and the box of entries. The entries
    are aligned as a single block, so that markers always lined up.

borderpad : float, default: :rc:`legend.borderpad`
    The fractional whitespace inside the legend border, in font-size units.

labelspacing : float, default: :rc:`legend.labelspacing`
    The vertical space between the legend entries, in font-size units.

handlelength : float, default: :rc:`legend.handlelength`
    The length of the legend handles, in font-size units.

handleheight : float, default: :rc:`legend.handleheight`
    The height of the legend handles, in font-size units.

handletextpad : float, default: :rc:`legend.handletextpad`
    The pad between the legend handle and text, in font-size units.

borderaxespad : float, default: :rc:`legend.borderaxespad`
    The pad between the Axes and legend border, in font-size units.

columnspacing : float, default: :rc:`legend.columnspacing`
    The spacing between columns, in font-size units.

handler_map : dict or None
    The custom dictionary mapping instances or types to a legend
    handler. This *handler_map* updates the default handler map
    found at `matplotlib.legend.Legend.get_legend_handler_map`.

draggable : bool, default: False
    Whether the legend can be dragged with the mouse.
"""

_loc_doc_base = """
loc : str or pair of floats, default: {default}
    The location of the legend.

    The strings ``'upper left'``, ``'upper right'``, ``'lower left'``,
    ``'lower right'`` place the legend at the corresponding corner of the
    {parent}.

    The strings ``'upper center'``, ``'lower center'``, ``'center left'``,
    ``'center right'`` place the legend at the center of the corresponding edge
    of the {parent}.

    The string ``'center'`` places the legend at the center of the {parent}.
{best}
    The location can also be a 2-tuple giving the coordinates of the lower-left
    corner of the legend in {parent} coordinates (in which case *bbox_to_anchor*
    will be ignored).

    For back-compatibility, ``'center right'`` (but no other location) can also
    be spelled ``'right'``, and each "string" location can also be given as a
    numeric value:

    ==================   =============
    Location String      Location Code
    ==================   =============
    'best' (Axes only)   0
    'upper right'        1
    'upper left'         2
    'lower left'         3
    'lower right'        4
    'right'              5
    'center left'        6
    'center right'       7
    'lower center'       8
    'upper center'       9
    'center'             10
    ==================   =============
    {outside}"""

_loc_doc_best = """
    The string ``'best'`` places the legend at the location, among the nine
    locations defined so far, with the minimum overlap with other drawn
    artists.  This option can be quite slow for plots with large amounts of
    data; your plotting speed may benefit from providing a specific location.
"""

_legend_kw_axes_st = (
    _loc_doc_base.format(parent='axes', default=':rc:`legend.loc`',
                         best=_loc_doc_best, outside='') +
    _legend_kw_doc_base)
_docstring.interpd.register(_legend_kw_axes=_legend_kw_axes_st)

_outside_doc = """
    If a figure is using the constrained layout manager, the string codes
    of the *loc* keyword argument can get better layout behaviour using the
    prefix 'outside'. There is ambiguity at the corners, so 'outside
    upper right' will make space for the legend above the rest of the
    axes in the layout, and 'outside right upper' will make space on the
    right side of the layout.  In addition to the values of *loc*
    listed above, we have 'outside right upper', 'outside right lower',
    'outside left upper', and 'outside left lower'.  See
    :ref:`legend_guide` for more details.
"""

_legend_kw_figure_st = (
    _loc_doc_base.format(parent='figure', default="'upper right'",
                         best='', outside=_outside_doc) +
    _legend_kw_doc_base)
_docstring.interpd.register(_legend_kw_figure=_legend_kw_figure_st)

_legend_kw_both_st = (
    _loc_doc_base.format(parent='axes/figure',
                         default=":rc:`legend.loc` for Axes, 'upper right' for Figure",
                         best=_loc_doc_best, outside=_outside_doc) +
    _legend_kw_doc_base)
_docstring.interpd.register(_legend_kw_doc=_legend_kw_both_st)

_legend_kw_set_loc_st = (
    _loc_doc_base.format(parent='axes/figure',
                         default=":rc:`legend.loc` for Axes, 'upper right' for Figure",
                         best=_loc_doc_best, outside=_outside_doc))
_docstring.interpd.register(_legend_kw_set_loc_doc=_legend_kw_set_loc_st)


class Legend(Artist):
    """
    Place a legend on the figure/axes.
    """

    # 'best' is only implemented for Axes legends
    codes = {'best': 0, **AnchoredOffsetbox.codes}
    zorder = 5

    def __str__(self):
        return "Legend"

    @_docstring.interpd
    def __init__(
        self, parent, handles, labels,
        *,
        loc=None,
        numpoints=None,      # number of points in the legend line
        markerscale=None,    # relative size of legend markers vs. original
        markerfirst=True,    # left/right ordering of legend marker and label
        reverse=False,       # reverse ordering of legend marker and label
        scatterpoints=None,  # number of scatter points
        scatteryoffsets=None,
        prop=None,           # properties for the legend texts
        fontsize=None,       # keyword to set font size directly
        labelcolor=None,     # keyword to set the text color

        # spacing & pad defined as a fraction of the font-size
        borderpad=None,      # whitespace inside the legend border
        labelspacing=None,   # vertical space between the legend entries
        handlelength=None,   # length of the legend handles
        handleheight=None,   # height of the legend handles
        handletextpad=None,  # pad between the legend handle and text
        borderaxespad=None,  # pad between the Axes and legend border
        columnspacing=None,  # spacing between columns

        ncols=1,     # number of columns
        mode=None,  # horizontal distribution of columns: None or "expand"

        fancybox=None,  # True: fancy box, False: rounded box, None: rcParam
        shadow=None,
        title=None,           # legend title
        title_fontsize=None,  # legend title font size
        framealpha=None,      # set frame alpha
        edgecolor=None,       # frame patch edgecolor
        facecolor=None,       # frame patch facecolor

        bbox_to_anchor=None,  # bbox to which the legend will be anchored
        bbox_transform=None,  # transform for the bbox
        frameon=None,         # draw frame
        handler_map=None,
        title_fontproperties=None,  # properties for the legend title
        alignment="center",       # control the alignment within the legend box
        ncol=1,  # synonym for ncols (backward compatibility)
        draggable=False  # whether the legend can be dragged with the mouse
    ):
        """
        Parameters
        ----------
        parent : `~matplotlib.axes.Axes` or `.Figure`
            The artist that contains the legend.

        handles : list of (`.Artist` or tuple of `.Artist`)
            A list of Artists (lines, patches) to be added to the legend.

        labels : list of str
            A list of labels to show next to the artists. The length of handles
            and labels should be the same. If they are not, they are truncated
            to the length of the shorter list.

        Other Parameters
        ----------------
        %(_legend_kw_doc)s

        Attributes
        ----------
        legend_handles
            List of `.Artist` objects added as legend entries.

            .. versionadded:: 3.7
        """
        # local import only to avoid circularity
        from matplotlib.axes import Axes
        from matplotlib.figure import FigureBase

        super().__init__()

        if prop is None:
            self.prop = FontProperties(size=mpl._val_or_rc(fontsize, "legend.fontsize"))
        else:
            self.prop = FontProperties._from_any(prop)
            if isinstance(prop, dict) and "size" not in prop:
                self.prop.set_size(mpl.rcParams["legend.fontsize"])

        self._fontsize = self.prop.get_size_in_points()

        self.texts = []
        self.legend_handles = []
        self._legend_title_box = None

        #: A dictionary with the extra handler mappings for this Legend
        #: instance.
        self._custom_handler_map = handler_map

        self.numpoints = mpl._val_or_rc(numpoints, 'legend.numpoints')
        self.markerscale = mpl._val_or_rc(markerscale, 'legend.markerscale')
        self.scatterpoints = mpl._val_or_rc(scatterpoints, 'legend.scatterpoints')
        self.borderpad = mpl._val_or_rc(borderpad, 'legend.borderpad')
        self.labelspacing = mpl._val_or_rc(labelspacing, 'legend.labelspacing')
        self.handlelength = mpl._val_or_rc(handlelength, 'legend.handlelength')
        self.handleheight = mpl._val_or_rc(handleheight, 'legend.handleheight')
        self.handletextpad = mpl._val_or_rc(handletextpad, 'legend.handletextpad')
        self.borderaxespad = mpl._val_or_rc(borderaxespad, 'legend.borderaxespad')
        self.columnspacing = mpl._val_or_rc(columnspacing, 'legend.columnspacing')
        self.shadow = mpl._val_or_rc(shadow, 'legend.shadow')

        if reverse:
            labels = [*reversed(labels)]
            handles = [*reversed(handles)]

        if len(handles) < 2:
            ncols = 1
        self._ncols = ncols if ncols != 1 else ncol

        if self.numpoints <= 0:
            raise ValueError("numpoints must be > 0; it was %d" % numpoints)

        # introduce y-offset for handles of the scatter plot
        if scatteryoffsets is None:
            self._scatteryoffsets = np.array([3. / 8., 4. / 8., 2.5 / 8.])
        else:
            self._scatteryoffsets = np.asarray(scatteryoffsets)
        reps = self.scatterpoints // len(self._scatteryoffsets) + 1
        self._scatteryoffsets = np.tile(self._scatteryoffsets,
                                        reps)[:self.scatterpoints]

        # _legend_box is a VPacker instance that contains all
        # legend items and will be initialized from _init_legend_box()
        # method.
        self._legend_box = None

        if isinstance(parent, Axes):
            self.isaxes = True
            self.axes = parent
            self.set_figure(parent.get_figure(root=False))
        elif isinstance(parent, FigureBase):
            self.isaxes = False
            self.set_figure(parent)
        else:
            raise TypeError(
                "Legend needs either Axes or FigureBase as parent"
            )
        self.parent = parent

        self._mode = mode
        self.set_bbox_to_anchor(bbox_to_anchor, bbox_transform)

        # Figure out if self.shadow is valid
        # If shadow was None, rcParams loads False
        # So it shouldn't be None here

        self._shadow_props = {'ox': 2, 'oy': -2}  # default location offsets
        if isinstance(self.shadow, dict):
            self._shadow_props.update(self.shadow)
            self.shadow = True
        elif self.shadow in (0, 1, True, False):
            self.shadow = bool(self.shadow)
        else:
            raise ValueError(
                'Legend shadow must be a dict or bool, not '
                f'{self.shadow!r} of type {type(self.shadow)}.'
            )

        # We use FancyBboxPatch to draw a legend frame. The location
        # and size of the box will be updated during the drawing time.

        facecolor = mpl._val_or_rc(facecolor, "legend.facecolor")
        if facecolor == 'inherit':
            facecolor = mpl.rcParams["axes.facecolor"]

        edgecolor = mpl._val_or_rc(edgecolor, "legend.edgecolor")
        if edgecolor == 'inherit':
            edgecolor = mpl.rcParams["axes.edgecolor"]

        fancybox = mpl._val_or_rc(fancybox, "legend.fancybox")

        self.legendPatch = FancyBboxPatch(
            xy=(0, 0), width=1, height=1,
            facecolor=facecolor, edgecolor=edgecolor,
            # If shadow is used, default to alpha=1 (#8943).
            alpha=(framealpha if framealpha is not None
                   else 1 if shadow
                   else mpl.rcParams["legend.framealpha"]),
            # The width and height of the legendPatch will be set (in draw())
            # to the length that includes the padding. Thus we set pad=0 here.
            boxstyle=("round,pad=0,rounding_size=0.2" if fancybox
                      else "square,pad=0"),
            mutation_scale=self._fontsize,
            snap=True,
            visible=mpl._val_or_rc(frameon, "legend.frameon")
        )
        self._set_artist_props(self.legendPatch)

        _api.check_in_list(["center", "left", "right"], alignment=alignment)
        self._alignment = alignment

        # init with null renderer
        self._init_legend_box(handles, labels, markerfirst)

        # Set legend location
        self.set_loc(loc)

        # figure out title font properties:
        if title_fontsize is not None and title_fontproperties is not None:
            raise ValueError(
                "title_fontsize and title_fontproperties can't be specified "
                "at the same time. Only use one of them. ")
        title_prop_fp = FontProperties._from_any(title_fontproperties)
        if isinstance(title_fontproperties, dict):
            if "size" not in title_fontproperties:
                title_fontsize = mpl.rcParams["legend.title_fontsize"]
                title_prop_fp.set_size(title_fontsize)
        elif title_fontsize is not None:
            title_prop_fp.set_size(title_fontsize)
        elif not isinstance(title_fontproperties, FontProperties):
            title_fontsize = mpl.rcParams["legend.title_fontsize"]
            title_prop_fp.set_size(title_fontsize)

        self.set_title(title, prop=title_prop_fp)

        self._draggable = None
        self.set_draggable(state=draggable)

        # set the text color

        color_getters = {  # getter function depends on line or patch
            'linecolor':       ['get_color',           'get_facecolor'],
            'markerfacecolor': ['get_markerfacecolor', 'get_facecolor'],
            'mfc':             ['get_markerfacecolor', 'get_facecolor'],
            'markeredgecolor': ['get_markeredgecolor', 'get_edgecolor'],
            'mec':             ['get_markeredgecolor', 'get_edgecolor'],
        }
        labelcolor = mpl._val_or_rc(labelcolor, 'legend.labelcolor')
        if labelcolor is None:
            labelcolor = mpl.rcParams['text.color']
        if isinstance(labelcolor, str) and labelcolor in color_getters:
            getter_names = color_getters[labelcolor]
            for handle, text in zip(self.legend_handles, self.texts):
                try:
                    if handle.get_array() is not None:
                        continue
                except AttributeError:
                    pass
                for getter_name in getter_names:
                    try:
                        color = getattr(handle, getter_name)()
                        if isinstance(color, np.ndarray):
                            if (
                                    color.shape[0] == 1
                                    or np.isclose(color, color[0]).all()
                            ):
                                text.set_color(color[0])
                            else:
                                pass
                        else:
                            text.set_color(color)
                        break
                    except AttributeError:
                        pass
        elif cbook._str_equal(labelcolor, 'none'):
            for text in self.texts:
                text.set_color(labelcolor)
        elif np.iterable(labelcolor):
            for text, color in zip(self.texts,
                                   itertools.cycle(
                                       colors.to_rgba_array(labelcolor))):
                text.set_color(color)
        else:
            raise ValueError(f"Invalid labelcolor: {labelcolor!r}")

    def _set_artist_props(self, a):
        """
        Set the boilerplate props for artists added to Axes.
        """
        a.set_figure(self.get_figure(root=False))
        if self.isaxes:
            a.axes = self.axes

        a.set_transform(self.get_transform())

    @_docstring.interpd
    def set_loc(self, loc=None):
        """
        Set the location of the legend.

        .. versionadded:: 3.8

        Parameters
        ----------
        %(_legend_kw_set_loc_doc)s
        """
        loc0 = loc
        self._loc_used_default = loc is None
        if loc is None:
            loc = mpl.rcParams["legend.loc"]
            if not self.isaxes and loc in [0, 'best']:
                loc = 'upper right'

        type_err_message = ("loc must be string, coordinate tuple, or"
                            f" an integer 0-10, not {loc!r}")

        # handle outside legends:
        self._outside_loc = None
        if isinstance(loc, str):
            if loc.split()[0] == 'outside':
                # strip outside:
                loc = loc.split('outside ')[1]
                # strip "center" at the beginning
                self._outside_loc = loc.replace('center ', '')
                # strip first
                self._outside_loc = self._outside_loc.split()[0]
                locs = loc.split()
                if len(locs) > 1 and locs[0] in ('right', 'left'):
                    # locs doesn't accept "left upper", etc, so swap
                    if locs[0] != 'center':
                        locs = locs[::-1]
                    loc = locs[0] + ' ' + locs[1]
            # check that loc is in acceptable strings
            loc = _api.check_getitem(self.codes, loc=loc)
        elif np.iterable(loc):
            # coerce iterable into tuple
            loc = tuple(loc)
            # validate the tuple represents Real coordinates
            if len(loc) != 2 or not all(isinstance(e, numbers.Real) for e in loc):
                raise ValueError(type_err_message)
        elif isinstance(loc, int):
            # validate the integer represents a string numeric value
            if loc < 0 or loc > 10:
                raise ValueError(type_err_message)
        else:
            # all other cases are invalid values of loc
            raise ValueError(type_err_message)

        if self.isaxes and self._outside_loc:
            raise ValueError(
                f"'outside' option for loc='{loc0}' keyword argument only "
                "works for figure legends")

        if not self.isaxes and loc == 0:
            raise ValueError(
                "Automatic legend placement (loc='best') not implemented for "
                "figure legend")

        tmp = self._loc_used_default
        self._set_loc(loc)
        self._loc_used_default = tmp  # ignore changes done by _set_loc

    def _set_loc(self, loc):
        # find_offset function will be provided to _legend_box and
        # _legend_box will draw itself at the location of the return
        # value of the find_offset.
        self._loc_used_default = False
        self._loc_real = loc
        self.stale = True
        self._legend_box.set_offset(self._findoffset)

    def set_ncols(self, ncols):
        """Set the number of columns."""
        self._ncols = ncols

    def _get_loc(self):
        return self._loc_real

    _loc = property(_get_loc, _set_loc)

    def _findoffset(self, width, height, xdescent, ydescent, renderer):
        """Helper function to locate the legend."""

        if self._loc == 0:  # "best".
            x, y = self._find_best_position(width, height, renderer)
        elif self._loc in Legend.codes.values():  # Fixed location.
            bbox = Bbox.from_bounds(0, 0, width, height)
            x, y = self._get_anchored_bbox(self._loc, bbox,
                                           self.get_bbox_to_anchor(),
                                           renderer)
        else:  # Axes or figure coordinates.
            fx, fy = self._loc
            bbox = self.get_bbox_to_anchor()
            x, y = bbox.x0 + bbox.width * fx, bbox.y0 + bbox.height * fy

        return x + xdescent, y + ydescent

    @allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible():
            return

        renderer.open_group('legend', gid=self.get_gid())

        fontsize = renderer.points_to_pixels(self._fontsize)

        # if mode == fill, set the width of the legend_box to the
        # width of the parent (minus pads)
        if self._mode in ["expand"]:
            pad = 2 * (self.borderaxespad + self.borderpad) * fontsize
            self._legend_box.set_width(self.get_bbox_to_anchor().width - pad)

        # update the location and size of the legend. This needs to
        # be done in any case to clip the figure right.
        bbox = self._legend_box.get_window_extent(renderer)
        self.legendPatch.set_bounds(bbox.bounds)
        self.legendPatch.set_mutation_scale(fontsize)

        # self.shadow is validated in __init__
        # So by here it is a bool and self._shadow_props contains any configs

        if self.shadow:
            Shadow(self.legendPatch, **self._shadow_props).draw(renderer)

        self.legendPatch.draw(renderer)
        self._legend_box.draw(renderer)

        renderer.close_group('legend')
        self.stale = False

    # _default_handler_map defines the default mapping between plot
    # elements and the legend handlers.

    _default_handler_map = {
        StemContainer: legend_handler.HandlerStem(),
        ErrorbarContainer: legend_handler.HandlerErrorbar(),
        Line2D: legend_handler.HandlerLine2D(),
        Patch: legend_handler.HandlerPatch(),
        StepPatch: legend_handler.HandlerStepPatch(),
        LineCollection: legend_handler.HandlerLineCollection(),
        RegularPolyCollection: legend_handler.HandlerRegularPolyCollection(),
        CircleCollection: legend_handler.HandlerCircleCollection(),
        BarContainer: legend_handler.HandlerPatch(
            update_func=legend_handler.update_from_first_child),
        tuple: legend_handler.HandlerTuple(),
        PathCollection: legend_handler.HandlerPathCollection(),
        PolyCollection: legend_handler.HandlerPolyCollection()
        }

    # (get|set|update)_default_handler_maps are public interfaces to
    # modify the default handler map.

    @classmethod
    def get_default_handler_map(cls):
        """Return the global default handler map, shared by all legends."""
        return cls._default_handler_map

    @classmethod
    def set_default_handler_map(cls, handler_map):
        """Set the global default handler map, shared by all legends."""
        cls._default_handler_map = handler_map

    @classmethod
    def update_default_handler_map(cls, handler_map):
        """Update the global default handler map, shared by all legends."""
        cls._default_handler_map.update(handler_map)

    def get_legend_handler_map(self):
        """Return this legend instance's handler map."""
        default_handler_map = self.get_default_handler_map()
        return ({**default_handler_map, **self._custom_handler_map}
                if self._custom_handler_map else default_handler_map)

    @staticmethod
    def get_legend_handler(legend_handler_map, orig_handle):
        """
        Return a legend handler from *legend_handler_map* that
        corresponds to *orig_handler*.

        *legend_handler_map* should be a dictionary object (that is
        returned by the get_legend_handler_map method).

        It first checks if the *orig_handle* itself is a key in the
        *legend_handler_map* and return the associated value.
        Otherwise, it checks for each of the classes in its
        method-resolution-order. If no matching key is found, it
        returns ``None``.
        """
        try:
            return legend_handler_map[orig_handle]
        except (TypeError, KeyError):  # TypeError if unhashable.
            pass
        for handle_type in type(orig_handle).mro():
            try:
                return legend_handler_map[handle_type]
            except KeyError:
                pass
        return None

    def _init_legend_box(self, handles, labels, markerfirst=True):
        """
        Initialize the legend_box. The legend_box is an instance of
        the OffsetBox, which is packed with legend handles and
        texts. Once packed, their location is calculated during the
        drawing time.
        """

        fontsize = self._fontsize

        # legend_box is a HPacker, horizontally packed with columns.
        # Each column is a VPacker, vertically packed with legend items.
        # Each legend item is a HPacker packed with:
        # - handlebox: a DrawingArea which contains the legend handle.
        # - labelbox: a TextArea which contains the legend text.

        text_list = []  # the list of text instances
        handle_list = []  # the list of handle instances
        handles_and_labels = []

        # The approximate height and descent of text. These values are
        # only used for plotting the legend handle.
        descent = 0.35 * fontsize * (self.handleheight - 0.7)  # heuristic.
        height = fontsize * self.handleheight - descent
        # each handle needs to be drawn inside a box of (x, y, w, h) =
        # (0, -descent, width, height).  And their coordinates should
        # be given in the display coordinates.

        # The transformation of each handle will be automatically set
        # to self.get_transform(). If the artist does not use its
        # default transform (e.g., Collections), you need to
        # manually set their transform to the self.get_transform().
        legend_handler_map = self.get_legend_handler_map()

        for orig_handle, label in zip(handles, labels):
            handler = self.get_legend_handler(legend_handler_map, orig_handle)
            if handler is None:
                _api.warn_external(
                             "Legend does not support handles for "
                             f"{type(orig_handle).__name__} "
                             "instances.\nA proxy artist may be used "
                             "instead.\nSee: https://matplotlib.org/"
                             "stable/users/explain/axes/legend_guide.html"
                             "#controlling-the-legend-entries")
                # No handle for this artist, so we just defer to None.
                handle_list.append(None)
            else:
                textbox = TextArea(label, multilinebaseline=True,
                                   textprops=dict(
                                       verticalalignment='baseline',
                                       horizontalalignment='left',
                                       fontproperties=self.prop))
                handlebox = DrawingArea(width=self.handlelength * fontsize,
                                        height=height,
                                        xdescent=0., ydescent=descent)

                text_list.append(textbox._text)
                # Create the artist for the legend which represents the
                # original artist/handle.
                handle_list.append(handler.legend_artist(self, orig_handle,
                                                         fontsize, handlebox))
                handles_and_labels.append((handlebox, textbox))

        columnbox = []
        # array_split splits n handles_and_labels into ncols columns, with the
        # first n%ncols columns having an extra entry.  filter(len, ...)
        # handles the case where n < ncols: the last ncols-n columns are empty
        # and get filtered out.
        for handles_and_labels_column in filter(
                len, np.array_split(handles_and_labels, self._ncols)):
            # pack handlebox and labelbox into itembox
            itemboxes = [HPacker(pad=0,
                                 sep=self.handletextpad * fontsize,
                                 children=[h, t] if markerfirst else [t, h],
                                 align="baseline")
                         for h, t in handles_and_labels_column]
            # pack columnbox
            alignment = "baseline" if markerfirst else "right"
            columnbox.append(VPacker(pad=0,
                                     sep=self.labelspacing * fontsize,
                                     align=alignment,
                                     children=itemboxes))

        mode = "expand" if self._mode == "expand" else "fixed"
        sep = self.columnspacing * fontsize
        self._legend_handle_box = HPacker(pad=0,
                                          sep=sep, align="baseline",
                                          mode=mode,
                                          children=columnbox)
        self._legend_title_box = TextArea("")
        self._legend_box = VPacker(pad=self.borderpad * fontsize,
                                   sep=self.labelspacing * fontsize,
                                   align=self._alignment,
                                   children=[self._legend_title_box,
                                             self._legend_handle_box])
        self._legend_box.set_figure(self.get_figure(root=False))
        self._legend_box.axes = self.axes
        self.texts = text_list
        self.legend_handles = handle_list

    def _auto_legend_data(self, renderer):
        """
        Return display coordinates for hit testing for "best" positioning.

        Returns
        -------
        bboxes
            List of bounding boxes of all patches.
        lines
            List of `.Path` corresponding to each line.
        offsets
            List of (x, y) offsets of all collection.
        """
        assert self.isaxes  # always holds, as this is only called internally
        bboxes = []
        lines = []
        offsets = []
        for artist in self.parent._children:
            if isinstance(artist, Line2D):
                lines.append(
                    artist.get_transform().transform_path(artist.get_path()))
            elif isinstance(artist, Rectangle):
                bboxes.append(
                    artist.get_bbox().transformed(artist.get_data_transform()))
            elif isinstance(artist, Patch):
                lines.append(
                    artist.get_transform().transform_path(artist.get_path()))
            elif isinstance(artist, PolyCollection):
                lines.extend(artist.get_transform().transform_path(path)
                             for path in artist.get_paths())
            elif isinstance(artist, Collection):
                transform, transOffset, hoffsets, _ = artist._prepare_points()
                if len(hoffsets):
                    offsets.extend(transOffset.transform(hoffsets))
            elif isinstance(artist, Text):
                bboxes.append(artist.get_window_extent(renderer))

        return bboxes, lines, offsets

    def get_children(self):
        # docstring inherited
        return [self._legend_box, self.get_frame()]

    def get_frame(self):
        """Return the `~.patches.Rectangle` used to frame the legend."""
        return self.legendPatch

    def get_lines(self):
        r"""Return the list of `~.lines.Line2D`\s in the legend."""
        return [h for h in self.legend_handles if isinstance(h, Line2D)]

    def get_patches(self):
        r"""Return the list of `~.patches.Patch`\s in the legend."""
        return silent_list('Patch',
                           [h for h in self.legend_handles
                            if isinstance(h, Patch)])

    def get_texts(self):
        r"""Return the list of `~.text.Text`\s in the legend."""
        return silent_list('Text', self.texts)

    def set_alignment(self, alignment):
        """
        Set the alignment of the legend title and the box of entries.

        The entries are aligned as a single block, so that markers always
        lined up.

        Parameters
        ----------
        alignment : {'center', 'left', 'right'}.

        """
        _api.check_in_list(["center", "left", "right"], alignment=alignment)
        self._alignment = alignment
        self._legend_box.align = alignment

    def get_alignment(self):
        """Get the alignment value of the legend box"""
        return self._legend_box.align

    def set_title(self, title, prop=None):
        """
        Set legend title and title style.

        Parameters
        ----------
        title : str
            The legend title.

        prop : `.font_manager.FontProperties` or `str` or `pathlib.Path`
            The font properties of the legend title.
            If a `str`, it is interpreted as a fontconfig pattern parsed by
            `.FontProperties`.  If a `pathlib.Path`, it is interpreted as the
            absolute path to a font file.

        """
        self._legend_title_box._text.set_text(title)
        if title:
            self._legend_title_box._text.set_visible(True)
            self._legend_title_box.set_visible(True)
        else:
            self._legend_title_box._text.set_visible(False)
            self._legend_title_box.set_visible(False)

        if prop is not None:
            self._legend_title_box._text.set_fontproperties(prop)

        self.stale = True

    def get_title(self):
        """Return the `.Text` instance for the legend title."""
        return self._legend_title_box._text

    def get_window_extent(self, renderer=None):
        # docstring inherited
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        return self._legend_box.get_window_extent(renderer=renderer)

    def get_tightbbox(self, renderer=None):
        # docstring inherited
        return self._legend_box.get_window_extent(renderer)

    def get_frame_on(self):
        """Get whether the legend box patch is drawn."""
        return self.legendPatch.get_visible()

    def set_frame_on(self, b):
        """
        Set whether the legend box patch is drawn.

        Parameters
        ----------
        b : bool
        """
        self.legendPatch.set_visible(b)
        self.stale = True

    draw_frame = set_frame_on  # Backcompat alias.

    def get_bbox_to_anchor(self):
        """Return the bbox that the legend will be anchored to."""
        if self._bbox_to_anchor is None:
            return self.parent.bbox
        else:
            return self._bbox_to_anchor

    def set_bbox_to_anchor(self, bbox, transform=None):
        """
        Set the bbox that the legend will be anchored to.

        Parameters
        ----------
        bbox : `~matplotlib.transforms.BboxBase` or tuple
            The bounding box can be specified in the following ways:

            - A `.BboxBase` instance
            - A tuple of ``(left, bottom, width, height)`` in the given
              transform (normalized axes coordinate if None)
            - A tuple of ``(left, bottom)`` where the width and height will be
              assumed to be zero.
            - *None*, to remove the bbox anchoring, and use the parent bbox.

        transform : `~matplotlib.transforms.Transform`, optional
            A transform to apply to the bounding box. If not specified, this
            will use a transform to the bounding box of the parent.
        """
        if bbox is None:
            self._bbox_to_anchor = None
            return
        elif isinstance(bbox, BboxBase):
            self._bbox_to_anchor = bbox
        else:
            try:
                l = len(bbox)
            except TypeError as err:
                raise ValueError(f"Invalid bbox: {bbox}") from err

            if l == 2:
                bbox = [bbox[0], bbox[1], 0, 0]

            self._bbox_to_anchor = Bbox.from_bounds(*bbox)

        if transform is None:
            transform = BboxTransformTo(self.parent.bbox)

        self._bbox_to_anchor = TransformedBbox(self._bbox_to_anchor,
                                               transform)
        self.stale = True

    def _get_anchored_bbox(self, loc, bbox, parentbbox, renderer):
        """
        Place the *bbox* inside the *parentbbox* according to a given
        location code. Return the (x, y) coordinate of the bbox.

        Parameters
        ----------
        loc : int
            A location code in range(1, 11). This corresponds to the possible
            values for ``self._loc``, excluding "best".
        bbox : `~matplotlib.transforms.Bbox`
            bbox to be placed, in display coordinates.
        parentbbox : `~matplotlib.transforms.Bbox`
            A parent box which will contain the bbox, in display coordinates.
        """
        return offsetbox._get_anchored_bbox(
            loc, bbox, parentbbox,
            self.borderaxespad * renderer.points_to_pixels(self._fontsize))

    def _find_best_position(self, width, height, renderer):
        """Determine the best location to place the legend."""
        assert self.isaxes  # always holds, as this is only called internally

        start_time = time.perf_counter()

        bboxes, lines, offsets = self._auto_legend_data(renderer)

        bbox = Bbox.from_bounds(0, 0, width, height)

        candidates = []
        for idx in range(1, len(self.codes)):
            l, b = self._get_anchored_bbox(idx, bbox,
                                           self.get_bbox_to_anchor(),
                                           renderer)
            legendBox = Bbox.from_bounds(l, b, width, height)
            # XXX TODO: If markers are present, it would be good to take them
            # into account when checking vertex overlaps in the next line.
            badness = (sum(legendBox.count_contains(line.vertices)
                           for line in lines)
                       + legendBox.count_contains(offsets)
                       + legendBox.count_overlaps(bboxes)
                       + sum(line.intersects_bbox(legendBox, filled=False)
                             for line in lines))
            # Include the index to favor lower codes in case of a tie.
            candidates.append((badness, idx, (l, b)))
            if badness == 0:
                break

        _, _, (l, b) = min(candidates)

        if self._loc_used_default and time.perf_counter() - start_time > 1:
            _api.warn_external(
                'Creating legend with loc="best" can be slow with large '
                'amounts of data.')

        return l, b

    def contains(self, mouseevent):
        return self.legendPatch.contains(mouseevent)

    def set_draggable(self, state, use_blit=False, update='loc'):
        """
        Enable or disable mouse dragging support of the legend.

        Parameters
        ----------
        state : bool
            Whether mouse dragging is enabled.
        use_blit : bool, optional
            Use blitting for faster image composition. For details see
            :ref:`func-animation`.
        update : {'loc', 'bbox'}, optional
            The legend parameter to be changed when dragged:

            - 'loc': update the *loc* parameter of the legend
            - 'bbox': update the *bbox_to_anchor* parameter of the legend

        Returns
        -------
        `.DraggableLegend` or *None*
            If *state* is ``True`` this returns the `.DraggableLegend` helper
            instance. Otherwise this returns *None*.
        """
        if state:
            if self._draggable is None:
                self._draggable = DraggableLegend(self,
                                                  use_blit,
                                                  update=update)
        else:
            if self._draggable is not None:
                self._draggable.disconnect()
            self._draggable = None
        return self._draggable

    def get_draggable(self):
        """Return ``True`` if the legend is draggable, ``False`` otherwise."""
        return self._draggable is not None


# Helper functions to parse legend arguments for both `figure.legend` and
# `axes.legend`:
def _get_legend_handles(axs, legend_handler_map=None):
    """Yield artists that can be used as handles in a legend."""
    handles_original = []
    for ax in axs:
        handles_original += [
            *(a for a in ax._children
              if isinstance(a, (Line2D, Patch, Collection, Text))),
            *ax.containers]
        # support parasite Axes:
        if hasattr(ax, 'parasites'):
            for axx in ax.parasites:
                handles_original += [
                    *(a for a in axx._children
                      if isinstance(a, (Line2D, Patch, Collection, Text))),
                    *axx.containers]

    handler_map = {**Legend.get_default_handler_map(),
                   **(legend_handler_map or {})}
    has_handler = Legend.get_legend_handler
    for handle in handles_original:
        label = handle.get_label()
        if label != '_nolegend_' and has_handler(handler_map, handle):
            yield handle
        elif (label and not label.startswith('_') and
                not has_handler(handler_map, handle)):
            _api.warn_external(
                             "Legend does not support handles for "
                             f"{type(handle).__name__} "
                             "instances.\nSee: https://matplotlib.org/stable/"
                             "tutorials/intermediate/legend_guide.html"
                             "#implementing-a-custom-legend-handler")
            continue


def _get_legend_handles_labels(axs, legend_handler_map=None):
    """Return handles and labels for legend."""
    handles = []
    labels = []
    for handle in _get_legend_handles(axs, legend_handler_map):
        label = handle.get_label()
        if label and not label.startswith('_'):
            handles.append(handle)
            labels.append(label)
    return handles, labels


def _parse_legend_args(axs, *args, handles=None, labels=None, **kwargs):
    """
    Get the handles and labels from the calls to either ``figure.legend``
    or ``axes.legend``.

    The parser is a bit involved because we support::

        legend()
        legend(labels)
        legend(handles, labels)
        legend(labels=labels)
        legend(handles=handles)
        legend(handles=handles, labels=labels)

    The behavior for a mixture of positional and keyword handles and labels
    is undefined and issues a warning; it will be an error in the future.

    Parameters
    ----------
    axs : list of `.Axes`
        If handles are not given explicitly, the artists in these Axes are
        used as handles.
    *args : tuple
        Positional parameters passed to ``legend()``.
    handles
        The value of the keyword argument ``legend(handles=...)``, or *None*
        if that keyword argument was not used.
    labels
        The value of the keyword argument ``legend(labels=...)``, or *None*
        if that keyword argument was not used.
    **kwargs
        All other keyword arguments passed to ``legend()``.

    Returns
    -------
    handles : list of (`.Artist` or tuple of `.Artist`)
        The legend handles.
    labels : list of str
        The legend labels.
    kwargs : dict
        *kwargs* with keywords handles and labels removed.

    """
    log = logging.getLogger(__name__)

    handlers = kwargs.get('handler_map')

    if (handles is not None or labels is not None) and args:
        _api.warn_deprecated("3.9", message=(
            "You have mixed positional and keyword arguments, some input may "
            "be discarded.  This is deprecated since %(since)s and will "
            "become an error in %(removal)s."))

    if (hasattr(handles, "__len__") and
            hasattr(labels, "__len__") and
            len(handles) != len(labels)):
        _api.warn_external(f"Mismatched number of handles and labels: "
                           f"len(handles) = {len(handles)} "
                           f"len(labels) = {len(labels)}")
    # if got both handles and labels as kwargs, make same length
    if handles and labels:
        handles, labels = zip(*zip(handles, labels))

    elif handles is not None and labels is None:
        labels = [handle.get_label() for handle in handles]

    elif labels is not None and handles is None:
        # Get as many handles as there are labels.
        handles = [handle for handle, label
                   in zip(_get_legend_handles(axs, handlers), labels)]

    elif len(args) == 0:  # 0 args: automatically detect labels and handles.
        handles, labels = _get_legend_handles_labels(axs, handlers)
        if not handles:
            _api.warn_external(
                "No artists with labels found to put in legend.  Note that "
                "artists whose label start with an underscore are ignored "
                "when legend() is called with no argument.")

    elif len(args) == 1:  # 1 arg: user defined labels, automatic handle detection.
        labels, = args
        if any(isinstance(l, Artist) for l in labels):
            raise TypeError("A single argument passed to legend() must be a "
                            "list of labels, but found an Artist in there.")

        # Get as many handles as there are labels.
        handles = [handle for handle, label
                   in zip(_get_legend_handles(axs, handlers), labels)]

    elif len(args) == 2:  # 2 args: user defined handles and labels.
        handles, labels = args[:2]

    else:
        raise _api.nargs_error('legend', '0-2', len(args))

    return handles, labels, kwargs

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\int_fiction.py ===
"""
    pygments.lexers.int_fiction
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for interactive fiction languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, \
    this, default, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error, Generic

__all__ = ['Inform6Lexer', 'Inform6TemplateLexer', 'Inform7Lexer',
           'Tads3Lexer']


class Inform6Lexer(RegexLexer):
    """
    For Inform 6 source code.
    """

    name = 'Inform 6'
    url = 'http://inform-fiction.org/'
    aliases = ['inform6', 'i6']
    filenames = ['*.inf']
    version_added = '2.0'

    flags = re.MULTILINE | re.DOTALL

    _name = r'[a-zA-Z_]\w*'

    # Inform 7 maps these four character classes to their ASCII
    # equivalents. To support Inform 6 inclusions within Inform 7,
    # Inform6Lexer maps them too.
    _dash = '\\-\u2010-\u2014'
    _dquote = '"\u201c\u201d'
    _squote = "'\u2018\u2019"
    _newline = '\\n\u0085\u2028\u2029'

    tokens = {
        'root': [
            (rf'\A(!%[^{_newline}]*[{_newline}])+', Comment.Preproc,
             'directive'),
            default('directive')
        ],
        '_whitespace': [
            (r'\s+', Text),
            (rf'![^{_newline}]*', Comment.Single)
        ],
        'default': [
            include('_whitespace'),
            (r'\[', Punctuation, 'many-values'),  # Array initialization
            (r':|(?=;)', Punctuation, '#pop'),
            (r'<', Punctuation),  # Second angle bracket in an action statement
            default(('expression', '_expression'))
        ],

        # Expressions
        '_expression': [
            include('_whitespace'),
            (r'(?=sp\b)', Text, '#pop'),
            (rf'(?=[{_dquote}{_squote}$0-9#a-zA-Z_])', Text,
             ('#pop', 'value')),
            (rf'\+\+|[{_dash}]{{1,2}}(?!>)|~~?', Operator),
            (rf'(?=[()\[{_dash},?@{{:;])', Text, '#pop')
        ],
        'expression': [
            include('_whitespace'),
            (r'\(', Punctuation, ('expression', '_expression')),
            (r'\)', Punctuation, '#pop'),
            (r'\[', Punctuation, ('#pop', 'statements', 'locals')),
            (rf'>(?=(\s+|(![^{_newline}]*))*[>;])', Punctuation),
            (rf'\+\+|[{_dash}]{{2}}(?!>)', Operator),
            (r',', Punctuation, '_expression'),
            (rf'&&?|\|\|?|[=~><]?=|[{_dash}]{{1,2}}>?|\.\.?[&#]?|::|[<>+*/%]',
             Operator, '_expression'),
            (r'(has|hasnt|in|notin|ofclass|or|provides)\b', Operator.Word,
             '_expression'),
            (r'sp\b', Name),
            (r'\?~?', Name.Label, 'label?'),
            (r'[@{]', Error),
            default('#pop')
        ],
        '_assembly-expression': [
            (r'\(', Punctuation, ('#push', '_expression')),
            (r'[\[\]]', Punctuation),
            (rf'[{_dash}]>', Punctuation, '_expression'),
            (r'sp\b', Keyword.Pseudo),
            (r';', Punctuation, '#pop:3'),
            include('expression')
        ],
        '_for-expression': [
            (r'\)', Punctuation, '#pop:2'),
            (r':', Punctuation, '#pop'),
            include('expression')
        ],
        '_keyword-expression': [
            (r'(from|near|to)\b', Keyword, '_expression'),
            include('expression')
        ],
        '_list-expression': [
            (r',', Punctuation, '#pop'),
            include('expression')
        ],
        '_object-expression': [
            (r'has\b', Keyword.Declaration, '#pop'),
            include('_list-expression')
        ],

        # Values
        'value': [
            include('_whitespace'),
            # Strings
            (rf'[{_squote}][^@][{_squote}]', String.Char, '#pop'),
            (rf'([{_squote}])(@\{{[0-9a-fA-F]*\}})([{_squote}])',
             bygroups(String.Char, String.Escape, String.Char), '#pop'),
            (rf'([{_squote}])(@.{{2}})([{_squote}])',
             bygroups(String.Char, String.Escape, String.Char), '#pop'),
            (rf'[{_squote}]', String.Single, ('#pop', 'dictionary-word')),
            (rf'[{_dquote}]', String.Double, ('#pop', 'string')),
            # Numbers
            (rf'\$[<>]?[+{_dash}][0-9]*\.?[0-9]*([eE][+{_dash}]?[0-9]+)?',
             Number.Float, '#pop'),
            (r'\$[0-9a-fA-F]+', Number.Hex, '#pop'),
            (r'\$\$[01]+', Number.Bin, '#pop'),
            (r'[0-9]+', Number.Integer, '#pop'),
            # Values prefixed by hashes
            (rf'(##|#a\$)({_name})', bygroups(Operator, Name), '#pop'),
            (rf'(#g\$)({_name})',
             bygroups(Operator, Name.Variable.Global), '#pop'),
            (r'#[nw]\$', Operator, ('#pop', 'obsolete-dictionary-word')),
            (rf'(#r\$)({_name})', bygroups(Operator, Name.Function), '#pop'),
            (r'#', Name.Builtin, ('#pop', 'system-constant')),
            # System functions
            (words((
                'child', 'children', 'elder', 'eldest', 'glk', 'indirect', 'metaclass',
                'parent', 'random', 'sibling', 'younger', 'youngest'), suffix=r'\b'),
             Name.Builtin, '#pop'),
            # Metaclasses
            (r'(?i)(Class|Object|Routine|String)\b', Name.Builtin, '#pop'),
            # Veneer routines
            (words((
                'Box__Routine', 'CA__Pr', 'CDefArt', 'CInDefArt', 'Cl__Ms',
                'Copy__Primitive', 'CP__Tab', 'DA__Pr', 'DB__Pr', 'DefArt', 'Dynam__String',
                'EnglishNumber', 'Glk__Wrap', 'IA__Pr', 'IB__Pr', 'InDefArt', 'Main__',
                'Meta__class', 'OB__Move', 'OB__Remove', 'OC__Cl', 'OP__Pr', 'Print__Addr',
                'Print__PName', 'PrintShortName', 'RA__Pr', 'RA__Sc', 'RL__Pr', 'R_Process',
                'RT__ChG', 'RT__ChGt', 'RT__ChLDB', 'RT__ChLDW', 'RT__ChPR', 'RT__ChPrintA',
                'RT__ChPrintC', 'RT__ChPrintO', 'RT__ChPrintS', 'RT__ChPS', 'RT__ChR',
                'RT__ChSTB', 'RT__ChSTW', 'RT__ChT', 'RT__Err', 'RT__TrPS', 'RV__Pr',
                'Symb__Tab', 'Unsigned__Compare', 'WV__Pr', 'Z__Region'),
                prefix='(?i)', suffix=r'\b'),
             Name.Builtin, '#pop'),
            # Other built-in symbols
            (words((
                'call', 'copy', 'create', 'DEBUG', 'destroy', 'DICT_CHAR_SIZE',
                'DICT_ENTRY_BYTES', 'DICT_IS_UNICODE', 'DICT_WORD_SIZE', 'DOUBLE_HI_INFINITY',
                'DOUBLE_HI_NAN', 'DOUBLE_HI_NINFINITY', 'DOUBLE_LO_INFINITY', 'DOUBLE_LO_NAN',
                'DOUBLE_LO_NINFINITY', 'false', 'FLOAT_INFINITY', 'FLOAT_NAN', 'FLOAT_NINFINITY',
                'GOBJFIELD_CHAIN', 'GOBJFIELD_CHILD', 'GOBJFIELD_NAME', 'GOBJFIELD_PARENT',
                'GOBJFIELD_PROPTAB', 'GOBJFIELD_SIBLING', 'GOBJ_EXT_START',
                'GOBJ_TOTAL_LENGTH', 'Grammar__Version', 'INDIV_PROP_START', 'INFIX',
                'infix__watching', 'MODULE_MODE', 'name', 'nothing', 'NUM_ATTR_BYTES', 'print',
                'print_to_array', 'recreate', 'remaining', 'self', 'sender', 'STRICT_MODE',
                'sw__var', 'sys__glob0', 'sys__glob1', 'sys__glob2', 'sys_statusline_flag',
                'TARGET_GLULX', 'TARGET_ZCODE', 'temp__global2', 'temp__global3',
                'temp__global4', 'temp_global', 'true', 'USE_MODULES', 'WORDSIZE'),
                prefix='(?i)', suffix=r'\b'),
             Name.Builtin, '#pop'),
            # Other values
            (_name, Name, '#pop')
        ],
        'value?': [
            include('value'),
            default('#pop')
        ],
        # Strings
        'dictionary-word': [
            (rf'[~^]+|//[^{_squote}]*', String.Escape),
            (rf'[^~^/\\@({{{_squote}]+', String.Single),
            (r'[/({]', String.Single),
            (r'@\{[0-9a-fA-F]*\}', String.Escape),
            (r'@.{2}', String.Escape),
            (rf'[{_squote}]', String.Single, '#pop')
        ],
        'string': [
            (r'[~^]+', String.Escape),
            (rf'[^~^\\@({{{_dquote}]+', String.Double),
            (r'[({]', String.Double),
            (r'\\', String.Escape),
            (rf'@(\\\s*[{_newline}]\s*)*@((\\\s*[{_newline}]\s*)*[0-9])*', String.Escape),
            (rf'@(\\\s*[{_newline}]\s*)*[({{]((\\\s*[{_newline}]\s*)*[0-9a-zA-Z_])*'
             rf'(\\\s*[{_newline}]\s*)*[)}}]',
             String.Escape),
            (rf'@(\\\s*[{_newline}]\s*)*.(\\\s*[{_newline}]\s*)*.',
             String.Escape),
            (rf'[{_dquote}]', String.Double, '#pop')
        ],
        'plain-string': [
            (rf'[^~^\\({{\[\]{_dquote}]+', String.Double),
            (r'[~^({\[\]]', String.Double),
            (r'\\', String.Escape),
            (rf'[{_dquote}]', String.Double, '#pop')
        ],
        # Names
        '_constant': [
            include('_whitespace'),
            (_name, Name.Constant, '#pop'),
            include('value')
        ],
        'constant*': [
            include('_whitespace'),
            (r',', Punctuation),
            (r'=', Punctuation, 'value?'),
            (_name, Name.Constant, 'value?'),
            default('#pop')
        ],
        '_global': [
            include('_whitespace'),
            (_name, Name.Variable.Global, '#pop'),
            include('value')
        ],
        'label?': [
            include('_whitespace'),
            (_name, Name.Label, '#pop'),
            default('#pop')
        ],
        'variable?': [
            include('_whitespace'),
            (_name, Name.Variable, '#pop'),
            default('#pop')
        ],
        # Values after hashes
        'obsolete-dictionary-word': [
            (r'\S\w*', String.Other, '#pop')
        ],
        'system-constant': [
            include('_whitespace'),
            (_name, Name.Builtin, '#pop')
        ],

        # Directives
        'directive': [
            include('_whitespace'),
            (r'#', Punctuation),
            (r';', Punctuation, '#pop'),
            (r'\[', Punctuation,
             ('default', 'statements', 'locals', 'routine-name?')),
            (words((
                'abbreviate', 'endif', 'dictionary', 'ifdef', 'iffalse', 'ifndef', 'ifnot',
                'iftrue', 'ifv3', 'ifv5', 'release', 'serial', 'switches', 'system_file',
                'version'), prefix='(?i)', suffix=r'\b'),
             Keyword, 'default'),
            (r'(?i)(array|global)\b', Keyword,
             ('default', 'directive-keyword?', '_global')),
            (r'(?i)attribute\b', Keyword, ('default', 'alias?', '_constant')),
            (r'(?i)class\b', Keyword,
             ('object-body', 'duplicates', 'class-name')),
            (r'(?i)(constant|default)\b', Keyword,
             ('default', 'constant*')),
            (r'(?i)(end\b)(.*)', bygroups(Keyword, Text)),
            (r'(?i)(extend|verb)\b', Keyword, 'grammar'),
            (r'(?i)fake_action\b', Keyword, ('default', '_constant')),
            (r'(?i)import\b', Keyword, 'manifest'),
            (r'(?i)(include|link|origsource)\b', Keyword,
             ('default', 'before-plain-string?')),
            (r'(?i)(lowstring|undef)\b', Keyword, ('default', '_constant')),
            (r'(?i)message\b', Keyword, ('default', 'diagnostic')),
            (r'(?i)(nearby|object)\b', Keyword,
             ('object-body', '_object-head')),
            (r'(?i)property\b', Keyword,
             ('default', 'alias?', '_constant', 'property-keyword*')),
            (r'(?i)replace\b', Keyword,
             ('default', 'routine-name?', 'routine-name?')),
            (r'(?i)statusline\b', Keyword, ('default', 'directive-keyword?')),
            (r'(?i)stub\b', Keyword, ('default', 'routine-name?')),
            (r'(?i)trace\b', Keyword,
             ('default', 'trace-keyword?', 'trace-keyword?')),
            (r'(?i)zcharacter\b', Keyword,
             ('default', 'directive-keyword?', 'directive-keyword?')),
            (_name, Name.Class, ('object-body', '_object-head'))
        ],
        # [, Replace, Stub
        'routine-name?': [
            include('_whitespace'),
            (_name, Name.Function, '#pop'),
            default('#pop')
        ],
        'locals': [
            include('_whitespace'),
            (r';', Punctuation, '#pop'),
            (r'\*', Punctuation),
            (r'"', String.Double, 'plain-string'),
            (_name, Name.Variable)
        ],
        # Array
        'many-values': [
            include('_whitespace'),
            (r';', Punctuation),
            (r'\]', Punctuation, '#pop'),
            (r':', Error),
            default(('expression', '_expression'))
        ],
        # Attribute, Property
        'alias?': [
            include('_whitespace'),
            (r'alias\b', Keyword, ('#pop', '_constant')),
            default('#pop')
        ],
        # Class, Object, Nearby
        'class-name': [
            include('_whitespace'),
            (r'(?=[,;]|(class|has|private|with)\b)', Text, '#pop'),
            (_name, Name.Class, '#pop')
        ],
        'duplicates': [
            include('_whitespace'),
            (r'\(', Punctuation, ('#pop', 'expression', '_expression')),
            default('#pop')
        ],
        '_object-head': [
            (rf'[{_dash}]>', Punctuation),
            (r'(class|has|private|with)\b', Keyword.Declaration, '#pop'),
            include('_global')
        ],
        'object-body': [
            include('_whitespace'),
            (r';', Punctuation, '#pop:2'),
            (r',', Punctuation),
            (r'class\b', Keyword.Declaration, 'class-segment'),
            (r'(has|private|with)\b', Keyword.Declaration),
            (r':', Error),
            default(('_object-expression', '_expression'))
        ],
        'class-segment': [
            include('_whitespace'),
            (r'(?=[,;]|(class|has|private|with)\b)', Text, '#pop'),
            (_name, Name.Class),
            default('value')
        ],
        # Extend, Verb
        'grammar': [
            include('_whitespace'),
            (r'=', Punctuation, ('#pop', 'default')),
            (r'\*', Punctuation, ('#pop', 'grammar-line')),
            default('_directive-keyword')
        ],
        'grammar-line': [
            include('_whitespace'),
            (r';', Punctuation, '#pop'),
            (r'[/*]', Punctuation),
            (rf'[{_dash}]>', Punctuation, 'value'),
            (r'(noun|scope)\b', Keyword, '=routine'),
            default('_directive-keyword')
        ],
        '=routine': [
            include('_whitespace'),
            (r'=', Punctuation, 'routine-name?'),
            default('#pop')
        ],
        # Import
        'manifest': [
            include('_whitespace'),
            (r';', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'(?i)global\b', Keyword, '_global'),
            default('_global')
        ],
        # Include, Link, Message
        'diagnostic': [
            include('_whitespace'),
            (rf'[{_dquote}]', String.Double, ('#pop', 'message-string')),
            default(('#pop', 'before-plain-string?', 'directive-keyword?'))
        ],
        'before-plain-string?': [
            include('_whitespace'),
            (rf'[{_dquote}]', String.Double, ('#pop', 'plain-string')),
            default('#pop')
        ],
        'message-string': [
            (r'[~^]+', String.Escape),
            include('plain-string')
        ],

        # Keywords used in directives
        '_directive-keyword!': [
            include('_whitespace'),
            (words((
                'additive', 'alias', 'buffer', 'class', 'creature', 'data', 'error', 'fatalerror',
                'first', 'has', 'held', 'individual', 'initial', 'initstr', 'last', 'long', 'meta',
                'multi', 'multiexcept', 'multiheld', 'multiinside', 'noun', 'number', 'only',
                'private', 'replace', 'reverse', 'scope', 'score', 'special', 'string', 'table',
                'terminating', 'time', 'topic', 'warning', 'with'), suffix=r'\b'),
             Keyword, '#pop'),
            (r'static\b', Keyword),
            (rf'[{_dash}]{{1,2}}>|[+=]', Punctuation, '#pop')
        ],
        '_directive-keyword': [
            include('_directive-keyword!'),
            include('value')
        ],
        'directive-keyword?': [
            include('_directive-keyword!'),
            default('#pop')
        ],
        'property-keyword*': [
            include('_whitespace'),
            (words(('additive', 'individual', 'long'),
                suffix=rf'\b(?=(\s*|(![^{_newline}]*[{_newline}]))*[_a-zA-Z])'),
             Keyword),
            default('#pop')
        ],
        'trace-keyword?': [
            include('_whitespace'),
            (words((
                'assembly', 'dictionary', 'expressions', 'lines', 'linker',
                'objects', 'off', 'on', 'symbols', 'tokens', 'verbs'), suffix=r'\b'),
             Keyword, '#pop'),
            default('#pop')
        ],

        # Statements
        'statements': [
            include('_whitespace'),
            (r'\]', Punctuation, '#pop'),
            (r'[;{}]', Punctuation),
            (words((
                'box', 'break', 'continue', 'default', 'give', 'inversion',
                'new_line', 'quit', 'read', 'remove', 'return', 'rfalse', 'rtrue',
                'spaces', 'string', 'until'), suffix=r'\b'),
             Keyword, 'default'),
            (r'(do|else)\b', Keyword),
            (r'(font|style)\b', Keyword,
             ('default', 'miscellaneous-keyword?')),
            (r'for\b', Keyword, ('for', '(?')),
            (r'(if|switch|while)', Keyword,
             ('expression', '_expression', '(?')),
            (r'(jump|save|restore)\b', Keyword, ('default', 'label?')),
            (r'objectloop\b', Keyword,
             ('_keyword-expression', 'variable?', '(?')),
            (rf'print(_ret)?\b|(?=[{_dquote}])', Keyword, 'print-list'),
            (r'\.', Name.Label, 'label?'),
            (r'@', Keyword, 'opcode'),
            (r'#(?![agrnw]\$|#)', Punctuation, 'directive'),
            (r'<', Punctuation, 'default'),
            (r'move\b', Keyword,
             ('default', '_keyword-expression', '_expression')),
            default(('default', '_keyword-expression', '_expression'))
        ],
        'miscellaneous-keyword?': [
            include('_whitespace'),
            (r'(bold|fixed|from|near|off|on|reverse|roman|to|underline)\b',
             Keyword, '#pop'),
            (r'(a|A|an|address|char|name|number|object|property|string|the|'
             rf'The)\b(?=(\s+|(![^{_newline}]*))*\))', Keyword.Pseudo,
             '#pop'),
            (rf'{_name}(?=(\s+|(![^{_newline}]*))*\))', Name.Function,
             '#pop'),
            default('#pop')
        ],
        '(?': [
            include('_whitespace'),
            (r'\(', Punctuation, '#pop'),
            default('#pop')
        ],
        'for': [
            include('_whitespace'),
            (r';', Punctuation, ('_for-expression', '_expression')),
            default(('_for-expression', '_expression'))
        ],
        'print-list': [
            include('_whitespace'),
            (r';', Punctuation, '#pop'),
            (r':', Error),
            default(('_list-expression', '_expression', '_list-expression', 'form'))
        ],
        'form': [
            include('_whitespace'),
            (r'\(', Punctuation, ('#pop', 'miscellaneous-keyword?')),
            default('#pop')
        ],

        # Assembly
        'opcode': [
            include('_whitespace'),
            (rf'[{_dquote}]', String.Double, ('operands', 'plain-string')),
            (rf'[{_dash}]{{1,2}}>', Punctuation, 'operands'),
            (_name, Keyword, 'operands')
        ],
        'operands': [
            (r':', Error),
            default(('_assembly-expression', '_expression'))
        ]
    }

    def get_tokens_unprocessed(self, text):
        # 'in' is either a keyword or an operator.
        # If the token two tokens after 'in' is ')', 'in' is a keyword:
        #   objectloop(a in b)
        # Otherwise, it is an operator:
        #   objectloop(a in b && true)
        objectloop_queue = []
        objectloop_token_count = -1
        previous_token = None
        for index, token, value in RegexLexer.get_tokens_unprocessed(self,
                                                                     text):
            if previous_token is Name.Variable and value == 'in':
                objectloop_queue = [[index, token, value]]
                objectloop_token_count = 2
            elif objectloop_token_count > 0:
                if token not in Comment and token not in Text:
                    objectloop_token_count -= 1
                objectloop_queue.append((index, token, value))
            else:
                if objectloop_token_count == 0:
                    if objectloop_queue[-1][2] == ')':
                        objectloop_queue[0][1] = Keyword
                    while objectloop_queue:
                        yield objectloop_queue.pop(0)
                    objectloop_token_count = -1
                yield index, token, value
            if token not in Comment and token not in Text:
                previous_token = token
        while objectloop_queue:
            yield objectloop_queue.pop(0)

    def analyse_text(text):
        """We try to find a keyword which seem relatively common, unfortunately
        there is a decent overlap with Smalltalk keywords otherwise here.."""
        result = 0
        if re.search('\borigsource\b', text, re.IGNORECASE):
            result += 0.05

        return result


class Inform7Lexer(RegexLexer):
    """
    For Inform 7 source code.
    """

    name = 'Inform 7'
    url = 'http://inform7.com/'
    aliases = ['inform7', 'i7']
    filenames = ['*.ni', '*.i7x']
    version_added = '2.0'

    flags = re.MULTILINE | re.DOTALL

    _dash = Inform6Lexer._dash
    _dquote = Inform6Lexer._dquote
    _newline = Inform6Lexer._newline
    _start = rf'\A|(?<=[{_newline}])'

    # There are three variants of Inform 7, differing in how to
    # interpret at signs and braces in I6T. In top-level inclusions, at
    # signs in the first column are inweb syntax. In phrase definitions
    # and use options, tokens in braces are treated as I7. Use options
    # also interpret "{N}".
    tokens = {}
    token_variants = ['+i6t-not-inline', '+i6t-inline', '+i6t-use-option']

    for level in token_variants:
        tokens[level] = {
            '+i6-root': list(Inform6Lexer.tokens['root']),
            '+i6t-root': [  # For Inform6TemplateLexer
                (rf'[^{Inform6Lexer._newline}]*', Comment.Preproc,
                 ('directive', '+p'))
            ],
            'root': [
                (r'(\|?\s)+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'[{_dquote}]', Generic.Heading,
                 ('+main', '+titling', '+titling-string')),
                default(('+main', '+heading?'))
            ],
            '+titling-string': [
                (rf'[^{_dquote}]+', Generic.Heading),
                (rf'[{_dquote}]', Generic.Heading, '#pop')
            ],
            '+titling': [
                (r'\[', Comment.Multiline, '+comment'),
                (rf'[^{_dquote}.;:|{_newline}]+', Generic.Heading),
                (rf'[{_dquote}]', Generic.Heading, '+titling-string'),
                (rf'[{_newline}]{{2}}|(?<=[\s{_dquote}])\|[\s{_dquote}]',
                 Text, ('#pop', '+heading?')),
                (rf'[.;:]|(?<=[\s{_dquote}])\|', Text, '#pop'),
                (rf'[|{_newline}]', Generic.Heading)
            ],
            '+main': [
                (rf'(?i)[^{_dquote}:a\[(|{_newline}]+', Text),
                (rf'[{_dquote}]', String.Double, '+text'),
                (r':', Text, '+phrase-definition'),
                (r'(?i)\bas\b', Text, '+use-option'),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'(\([{_dash}])(.*?)([{_dash}]\))',
                 bygroups(Punctuation,
                          using(this, state=('+i6-root', 'directive'),
                                i6t='+i6t-not-inline'), Punctuation)),
                (rf'({_start}|(?<=[\s;:.{_dquote}]))\|\s|[{_newline}]{{2,}}', Text, '+heading?'),
                (rf'(?i)[a(|{_newline}]', Text)
            ],
            '+phrase-definition': [
                (r'\s+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'(\([{_dash}])(.*?)([{_dash}]\))',
                 bygroups(Punctuation,
                          using(this, state=('+i6-root', 'directive',
                                             'default', 'statements'),
                                i6t='+i6t-inline'), Punctuation), '#pop'),
                default('#pop')
            ],
            '+use-option': [
                (r'\s+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'(\([{_dash}])(.*?)([{_dash}]\))',
                 bygroups(Punctuation,
                          using(this, state=('+i6-root', 'directive'),
                                i6t='+i6t-use-option'), Punctuation), '#pop'),
                default('#pop')
            ],
            '+comment': [
                (r'[^\[\]]+', Comment.Multiline),
                (r'\[', Comment.Multiline, '#push'),
                (r'\]', Comment.Multiline, '#pop')
            ],
            '+text': [
                (rf'[^\[{_dquote}]+', String.Double),
                (r'\[.*?\]', String.Interpol),
                (rf'[{_dquote}]', String.Double, '#pop')
            ],
            '+heading?': [
                (r'(\|?\s)+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'[{_dash}]{{4}}\s+', Text, '+documentation-heading'),
                (rf'[{_dash}]{{1,3}}', Text),
                (rf'(?i)(volume|book|part|chapter|section)\b[^{_newline}]*',
                 Generic.Heading, '#pop'),
                default('#pop')
            ],
            '+documentation-heading': [
                (r'\s+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (r'(?i)documentation\s+', Text, '+documentation-heading2'),
                default('#pop')
            ],
            '+documentation-heading2': [
                (r'\s+', Text),
                (r'\[', Comment.Multiline, '+comment'),
                (rf'[{_dash}]{{4}}\s', Text, '+documentation'),
                default('#pop:2')
            ],
            '+documentation': [
                (rf'(?i)({_start})\s*(chapter|example)\s*:[^{_newline}]*', Generic.Heading),
                (rf'(?i)({_start})\s*section\s*:[^{_newline}]*',
                 Generic.Subheading),
                (rf'(({_start})\t.*?[{_newline}])+',
                 using(this, state='+main')),
                (rf'[^{_newline}\[]+|[{_newline}\[]', Text),
                (r'\[', Comment.Multiline, '+comment'),
            ],
            '+i6t-not-inline': [
                (rf'({_start})@c( .*?)?([{_newline}]|\Z)',
                 Comment.Preproc),
                (rf'({_start})@([{_dash}]+|Purpose:)[^{_newline}]*',
                 Comment.Preproc),
                (rf'({_start})@p( .*?)?([{_newline}]|\Z)',
                 Generic.Heading, '+p')
            ],
            '+i6t-use-option': [
                include('+i6t-not-inline'),
                (r'(\{)(N)(\})', bygroups(Punctuation, Text, Punctuation))
            ],
            '+i6t-inline': [
                (r'(\{)(\S[^}]*)?(\})',
                 bygroups(Punctuation, using(this, state='+main'),
                          Punctuation))
            ],
            '+i6t': [
                (rf'(\{{[{_dash}])(![^}}]*)(\}}?)',
                 bygroups(Punctuation, Comment.Single, Punctuation)),
                (rf'(\{{[{_dash}])(lines)(:)([^}}]*)(\}}?)',
                 bygroups(Punctuation, Keyword, Punctuation, Text,
                          Punctuation), '+lines'),
                (rf'(\{{[{_dash}])([^:}}]*)(:?)([^}}]*)(\}}?)',
                 bygroups(Punctuation, Keyword, Punctuation, Text,
                          Punctuation)),
                (r'(\(\+)(.*?)(\+\)|\Z)',
                 bygroups(Punctuation, using(this, state='+main'),
                          Punctuation))
            ],
            '+p': [
                (r'[^@]+', Comment.Preproc),
                (rf'({_start})@c( .*?)?([{_newline}]|\Z)',
                 Comment.Preproc, '#pop'),
                (rf'({_start})@([{_dash}]|Purpose:)', Comment.Preproc),
                (rf'({_start})@p( .*?)?([{_newline}]|\Z)',
                 Generic.Heading),
                (r'@', Comment.Preproc)
            ],
            '+lines': [
                (rf'({_start})@c( .*?)?([{_newline}]|\Z)',
                 Comment.Preproc),
                (rf'({_start})@([{_dash}]|Purpose:)[^{_newline}]*',
                 Comment.Preproc),
                (rf'({_start})@p( .*?)?([{_newline}]|\Z)',
                 Generic.Heading, '+p'),
                (rf'({_start})@\w*[ {_newline}]', Keyword),
                (rf'![^{_newline}]*', Comment.Single),
                (rf'(\{{)([{_dash}]endlines)(\}})',
                 bygroups(Punctuation, Keyword, Punctuation), '#pop'),
                (rf'[^@!{{]+?([{_newline}]|\Z)|.', Text)
            ]
        }
        # Inform 7 can include snippets of Inform 6 template language,
        # so all of Inform6Lexer's states are copied here, with
        # modifications to account for template syntax. Inform7Lexer's
        # own states begin with '+' to avoid name conflicts. Some of
        # Inform6Lexer's states begin with '_': these are not modified.
        # They deal with template syntax either by including modified
        # states, or by matching r'' then pushing to modified states.
        for token in Inform6Lexer.tokens:
            if token == 'root':
                continue
            tokens[level][token] = list(Inform6Lexer.tokens[token])
            if not token.startswith('_'):
                tokens[level][token][:0] = [include('+i6t'), include(level)]

    def __init__(self, **options):
        level = options.get('i6t', '+i6t-not-inline')
        if level not in self._all_tokens:
            self._tokens = self.__class__.process_tokendef(level)
        else:
            self._tokens = self._all_tokens[level]
        RegexLexer.__init__(self, **options)


class Inform6TemplateLexer(Inform7Lexer):
    """
    For Inform 6 template code.
    """

    name = 'Inform 6 template'
    aliases = ['i6t']
    filenames = ['*.i6t']
    version_added = '2.0'

    def get_tokens_unprocessed(self, text, stack=('+i6t-root',)):
        return Inform7Lexer.get_tokens_unprocessed(self, text, stack)


class Tads3Lexer(RegexLexer):
    """
    For TADS 3 source code.
    """

    name = 'TADS 3'
    aliases = ['tads3']
    filenames = ['*.t']
    url = 'https://www.tads.org'
    version_added = ''

    flags = re.DOTALL | re.MULTILINE

    _comment_single = r'(?://(?:[^\\\n]|\\+[\w\W])*$)'
    _comment_multiline = r'(?:/\*(?:[^*]|\*(?!/))*\*/)'
    _escape = (r'(?:\\(?:[\n\\<>"\'^v bnrt]|u[\da-fA-F]{,4}|x[\da-fA-F]{,2}|'
               r'[0-3]?[0-7]{1,2}))')
    _name = r'(?:[_a-zA-Z]\w*)'
    _no_quote = r'(?=\s|\\?>)'
    _operator = (r'(?:&&|\|\||\+\+|--|\?\?|::|[.,@\[\]~]|'
                 r'(?:[=+\-*/%!&|^]|<<?|>>?>?)=?)')
    _ws = rf'(?:\\|\s|{_comment_single}|{_comment_multiline})'
    _ws_pp = rf'(?:\\\n|[^\S\n]|{_comment_single}|{_comment_multiline})'

    def _make_string_state(triple, double, verbatim=None, _escape=_escape):
        if verbatim:
            verbatim = ''.join([f'(?:{re.escape(c.lower())}|{re.escape(c.upper())})'
                                for c in verbatim])
        char = r'"' if double else r"'"
        token = String.Double if double else String.Single
        escaped_quotes = rf'+|{char}(?!{char}{{2}})' if triple else r''
        prefix = '{}{}'.format('t' if triple else '', 'd' if double else 's')
        tag_state_name = f'{prefix}qt'
        state = []
        if triple:
            state += [
                (rf'{char}{{3,}}', token, '#pop'),
                (rf'\\{char}+', String.Escape),
                (char, token)
            ]
        else:
            state.append((char, token, '#pop'))
        state += [
            include('s/verbatim'),
            (rf'[^\\<&{{}}{char}]+', token)
        ]
        if verbatim:
            # This regex can't use `(?i)` because escape sequences are
            # case-sensitive. `<\XMP>` works; `<\xmp>` doesn't.
            state.append((rf'\\?<(/|\\\\|(?!{_escape})\\){verbatim}(?=[\s=>])',
                          Name.Tag, ('#pop', f'{prefix}qs', tag_state_name)))
        else:
            state += [
                (rf'\\?<!([^><\\{char}]|<(?!<)|\\{char}{escaped_quotes}|{_escape}|\\.)*>?', Comment.Multiline),
                (r'(?i)\\?<listing(?=[\s=>]|\\>)', Name.Tag,
                 ('#pop', f'{prefix}qs/listing', tag_state_name)),
                (r'(?i)\\?<xmp(?=[\s=>]|\\>)', Name.Tag,
                 ('#pop', f'{prefix}qs/xmp', tag_state_name)),
                (rf'\\?<([^\s=><\\{char}]|<(?!<)|\\{char}{escaped_quotes}|{_escape}|\\.)*', Name.Tag,
                 tag_state_name),
                include('s/entity')
            ]
        state += [
            include('s/escape'),
            (rf'\{{([^}}<\\{char}]|<(?!<)|\\{char}{escaped_quotes}|{_escape}|\\.)*\}}', String.Interpol),
            (r'[\\&{}<]', token)
        ]
        return state

    def _make_tag_state(triple, double, _escape=_escape):
        char = r'"' if double else r"'"
        quantifier = r'{3,}' if triple else r''
        state_name = '{}{}qt'.format('t' if triple else '', 'd' if double else 's')
        token = String.Double if double else String.Single
        escaped_quotes = rf'+|{char}(?!{char}{{2}})' if triple else r''
        return [
            (rf'{char}{quantifier}', token, '#pop:2'),
            (r'(\s|\\\n)+', Text),
            (r'(=)(\\?")', bygroups(Punctuation, String.Double),
             f'dqs/{state_name}'),
            (r"(=)(\\?')", bygroups(Punctuation, String.Single),
             f'sqs/{state_name}'),
            (r'=', Punctuation, f'uqs/{state_name}'),
            (r'\\?>', Name.Tag, '#pop'),
            (rf'\{{([^}}<\\{char}]|<(?!<)|\\{char}{escaped_quotes}|{_escape}|\\.)*\}}', String.Interpol),
            (rf'([^\s=><\\{char}]|<(?!<)|\\{char}{escaped_quotes}|{_escape}|\\.)+', Name.Attribute),
            include('s/escape'),
            include('s/verbatim'),
            include('s/entity'),
            (r'[\\{}&]', Name.Attribute)
        ]

    def _make_attribute_value_state(terminator, host_triple, host_double,
                                    _escape=_escape):
        token = (String.Double if terminator == r'"' else
                 String.Single if terminator == r"'" else String.Other)
        host_char = r'"' if host_double else r"'"
        host_quantifier = r'{3,}' if host_triple else r''
        host_token = String.Double if host_double else String.Single
        escaped_quotes = (rf'+|{host_char}(?!{host_char}{{2}})'
                          if host_triple else r'')
        return [
            (rf'{host_char}{host_quantifier}', host_token, '#pop:3'),
            (r'{}{}'.format(r'' if token is String.Other else r'\\?', terminator),
             token, '#pop'),
            include('s/verbatim'),
            include('s/entity'),
            (rf'\{{([^}}<\\{host_char}]|<(?!<)|\\{host_char}{escaped_quotes}|{_escape}|\\.)*\}}', String.Interpol),
            (r'([^\s"\'<%s{}\\&])+' % (r'>' if token is String.Other else r''),
             token),
            include('s/escape'),
            (r'["\'\s&{<}\\]', token)
        ]

    tokens = {
        'root': [
            ('\ufeff', Text),
            (r'\{', Punctuation, 'object-body'),
            (r';+', Punctuation),
            (r'(?=(argcount|break|case|catch|continue|default|definingobj|'
             r'delegated|do|else|for|foreach|finally|goto|if|inherited|'
             r'invokee|local|nil|new|operator|replaced|return|self|switch|'
             r'targetobj|targetprop|throw|true|try|while)\b)', Text, 'block'),
            (rf'({_name})({_ws}*)(\()',
             bygroups(Name.Function, using(this, state='whitespace'),
                      Punctuation),
             ('block?/root', 'more/parameters', 'main/parameters')),
            include('whitespace'),
            (r'\++', Punctuation),
            (r'[^\s!"%-(*->@-_a-z{-~]+', Error),  # Averts an infinite loop
            (r'(?!\Z)', Text, 'main/root')
        ],
        'main/root': [
            include('main/basic'),
            default(('#pop', 'object-body/no-braces', 'classes', 'class'))
        ],
        'object-body/no-braces': [
            (r';', Punctuation, '#pop'),
            (r'\{', Punctuation, ('#pop', 'object-body')),
            include('object-body')
        ],
        'object-body': [
            (r';', Punctuation),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            (r':', Punctuation, ('classes', 'class')),
            (rf'({_name}?)({_ws}*)(\()',
             bygroups(Name.Function, using(this, state='whitespace'),
                      Punctuation),
             ('block?', 'more/parameters', 'main/parameters')),
            (rf'({_name})({_ws}*)(\{{)',
             bygroups(Name.Function, using(this, state='whitespace'),
                      Punctuation), 'block'),
            (rf'({_name})({_ws}*)(:)',
             bygroups(Name.Variable, using(this, state='whitespace'),
                      Punctuation),
             ('object-body/no-braces', 'classes', 'class')),
            include('whitespace'),
            (rf'->|{_operator}', Punctuation, 'main'),
            default('main/object-body')
        ],
        'main/object-body': [
            include('main/basic'),
            (rf'({_name})({_ws}*)(=?)',
             bygroups(Name.Variable, using(this, state='whitespace'),
                      Punctuation), ('#pop', 'more', 'main')),
            default('#pop:2')
        ],
        'block?/root': [
            (r'\{', Punctuation, ('#pop', 'block')),
            include('whitespace'),
            (r'(?=[\[\'"<(:])', Text,  # It might be a VerbRule macro.
             ('#pop', 'object-body/no-braces', 'grammar', 'grammar-rules')),
            # It might be a macro like DefineAction.
            default(('#pop', 'object-body/no-braces'))
        ],
        'block?': [
            (r'\{', Punctuation, ('#pop', 'block')),
            include('whitespace'),
            default('#pop')
        ],
        'block/basic': [
            (r'[;:]+', Punctuation),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            (r'default\b', Keyword.Reserved),
            (rf'({_name})({_ws}*)(:)',
             bygroups(Name.Label, using(this, state='whitespace'),
                      Punctuation)),
            include('whitespace')
        ],
        'block': [
            include('block/basic'),
            (r'(?!\Z)', Text, ('more', 'main'))
        ],
        'block/embed': [
            (r'>>', String.Interpol, '#pop'),
            include('block/basic'),
            (r'(?!\Z)', Text, ('more/embed', 'main'))
        ],
        'main/basic': [
            include('whitespace'),
            (r'\(', Punctuation, ('#pop', 'more', 'main')),
            (r'\[', Punctuation, ('#pop', 'more/list', 'main')),
            (r'\{', Punctuation, ('#pop', 'more/inner', 'main/inner',
                                  'more/parameters', 'main/parameters')),
            (r'\*|\.{3}', Punctuation, '#pop'),
            (r'(?i)0x[\da-f]+', Number.Hex, '#pop'),
            (r'(\d+\.(?!\.)\d*|\.\d+)([eE][-+]?\d+)?|\d+[eE][-+]?\d+',
             Number.Float, '#pop'),
            (r'0[0-7]+', Number.Oct, '#pop'),
            (r'\d+', Number.Integer, '#pop'),
            (r'"""', String.Double, ('#pop', 'tdqs')),
            (r"'''", String.Single, ('#pop', 'tsqs')),
            (r'"', String.Double, ('#pop', 'dqs')),
            (r"'", String.Single, ('#pop', 'sqs')),
            (r'R"""', String.Regex, ('#pop', 'tdqr')),
            (r"R'''", String.Regex, ('#pop', 'tsqr')),
            (r'R"', String.Regex, ('#pop', 'dqr')),
            (r"R'", String.Regex, ('#pop', 'sqr')),
            # Two-token keywords
            (rf'(extern)({_ws}+)(object\b)',
             bygroups(Keyword.Reserved, using(this, state='whitespace'),
                      Keyword.Reserved)),
            (rf'(function|method)({_ws}*)(\()',
             bygroups(Keyword.Reserved, using(this, state='whitespace'),
                      Punctuation),
             ('#pop', 'block?', 'more/parameters', 'main/parameters')),
            (rf'(modify)({_ws}+)(grammar\b)',
             bygroups(Keyword.Reserved, using(this, state='whitespace'),
                      Keyword.Reserved),
             ('#pop', 'object-body/no-braces', ':', 'grammar')),
            (rf'(new)({_ws}+(?=(?:function|method)\b))',
             bygroups(Keyword.Reserved, using(this, state='whitespace'))),
            (rf'(object)({_ws}+)(template\b)',
             bygroups(Keyword.Reserved, using(this, state='whitespace'),
                      Keyword.Reserved), ('#pop', 'template')),
            (rf'(string)({_ws}+)(template\b)',
             bygroups(Keyword, using(this, state='whitespace'),
                      Keyword.Reserved), ('#pop', 'function-name')),
            # Keywords
            (r'(argcount|definingobj|invokee|replaced|targetobj|targetprop)\b',
             Name.Builtin, '#pop'),
            (r'(break|continue|goto)\b', Keyword.Reserved, ('#pop', 'label')),
            (r'(case|extern|if|intrinsic|return|static|while)\b',
             Keyword.Reserved),
            (r'catch\b', Keyword.Reserved, ('#pop', 'catch')),
            (r'class\b', Keyword.Reserved,
             ('#pop', 'object-body/no-braces', 'class')),
            (r'(default|do|else|finally|try)\b', Keyword.Reserved, '#pop'),
            (r'(dictionary|property)\b', Keyword.Reserved,
             ('#pop', 'constants')),
            (r'enum\b', Keyword.Reserved, ('#pop', 'enum')),
            (r'export\b', Keyword.Reserved, ('#pop', 'main')),
            (r'(for|foreach)\b', Keyword.Reserved,
             ('#pop', 'more/inner', 'main/inner')),
            (r'(function|method)\b', Keyword.Reserved,
             ('#pop', 'block?', 'function-name')),
            (r'grammar\b', Keyword.Reserved,
             ('#pop', 'object-body/no-braces', 'grammar')),
            (r'inherited\b', Keyword.Reserved, ('#pop', 'inherited')),
            (r'local\b', Keyword.Reserved,
             ('#pop', 'more/local', 'main/local')),
            (r'(modify|replace|switch|throw|transient)\b', Keyword.Reserved,
             '#pop'),
            (r'new\b', Keyword.Reserved, ('#pop', 'class')),
            (r'(nil|true)\b', Keyword.Constant, '#pop'),
            (r'object\b', Keyword.Reserved, ('#pop', 'object-body/no-braces')),
            (r'operator\b', Keyword.Reserved, ('#pop', 'operator')),
            (r'propertyset\b', Keyword.Reserved,
             ('#pop', 'propertyset', 'main')),
            (r'self\b', Name.Builtin.Pseudo, '#pop'),
            (r'template\b', Keyword.Reserved, ('#pop', 'template')),
            # Operators
            (rf'(__objref|defined)({_ws}*)(\()',
             bygroups(Operator.Word, using(this, state='whitespace'),
                      Operator), ('#pop', 'more/__objref', 'main')),
            (r'delegated\b', Operator.Word),
            # Compiler-defined macros and built-in properties
            (r'(__DATE__|__DEBUG|__LINE__|__FILE__|'
             r'__TADS_MACRO_FORMAT_VERSION|__TADS_SYS_\w*|__TADS_SYSTEM_NAME|'
             r'__TADS_VERSION_MAJOR|__TADS_VERSION_MINOR|__TADS3|__TIME__|'
             r'construct|finalize|grammarInfo|grammarTag|lexicalParent|'
             r'miscVocab|sourceTextGroup|sourceTextGroupName|'
             r'sourceTextGroupOrder|sourceTextOrder)\b', Name.Builtin, '#pop')
        ],
        'main': [
            include('main/basic'),
            (_name, Name, '#pop'),
            default('#pop')
        ],
        'more/basic': [
            (r'\(', Punctuation, ('more/list', 'main')),
            (r'\[', Punctuation, ('more', 'main')),
            (r'\.{3}', Punctuation),
            (r'->|\.\.', Punctuation, 'main'),
            (r'(?=;)|[:)\]]', Punctuation, '#pop'),
            include('whitespace'),
            (_operator, Operator, 'main'),
            (r'\?', Operator, ('main', 'more/conditional', 'main')),
            (rf'(is|not)({_ws}+)(in\b)',
             bygroups(Operator.Word, using(this, state='whitespace'),
                      Operator.Word)),
            (r'[^\s!"%-_a-z{-~]+', Error)  # Averts an infinite loop
        ],
        'more': [
            include('more/basic'),
            default('#pop')
        ],
        # Then expression (conditional operator)
        'more/conditional': [
            (r':(?!:)', Operator, '#pop'),
            include('more')
        ],
        # Embedded expressions
        'more/embed': [
            (r'>>', String.Interpol, '#pop:2'),
            include('more')
        ],
        # For/foreach loop initializer or short-form anonymous function
        'main/inner': [
            (r'\(', Punctuation, ('#pop', 'more/inner', 'main/inner')),
            (r'local\b', Keyword.Reserved, ('#pop', 'main/local')),
            include('main')
        ],
        'more/inner': [
            (r'\}', Punctuation, '#pop'),
            (r',', Punctuation, 'main/inner'),
            (r'(in|step)\b', Keyword, 'main/inner'),
            include('more')
        ],
        # Local
        'main/local': [
            (_name, Name.Variable, '#pop'),
            include('whitespace')
        ],
        'more/local': [
            (r',', Punctuation, 'main/local'),
            include('more')
        ],
        # List
        'more/list': [
            (r'[,:]', Punctuation, 'main'),
            include('more')
        ],
        # Parameter list
        'main/parameters': [
            (rf'({_name})({_ws}*)(?=:)',
             bygroups(Name.Variable, using(this, state='whitespace')), '#pop'),
            (rf'({_name})({_ws}+)({_name})',
             bygroups(Name.Class, using(this, state='whitespace'),
                      Name.Variable), '#pop'),
            (r'\[+', Punctuation),
            include('main/basic'),
            (_name, Name.Variable, '#pop'),
            default('#pop')
        ],
        'more/parameters': [
            (rf'(:)({_ws}*(?=[?=,:)]))',
             bygroups(Punctuation, using(this, state='whitespace'))),
            (r'[?\]]+', Punctuation),
            (r'[:)]', Punctuation, ('#pop', 'multimethod?')),
            (r',', Punctuation, 'main/parameters'),
            (r'=', Punctuation, ('more/parameter', 'main')),
            include('more')
        ],
        'more/parameter': [
            (r'(?=[,)])', Text, '#pop'),
            include('more')
        ],
        'multimethod?': [
            (r'multimethod\b', Keyword, '#pop'),
            include('whitespace'),
            default('#pop')
        ],

        # Statements and expressions
        'more/__objref': [
            (r',', Punctuation, 'mode'),
            (r'\)', Operator, '#pop'),
            include('more')
        ],
        'mode': [
            (r'(error|warn)\b', Keyword, '#pop'),
            include('whitespace')
        ],
        'catch': [
            (r'\(+', Punctuation),
            (_name, Name.Exception, ('#pop', 'variables')),
            include('whitespace')
        ],
        'enum': [
            include('whitespace'),
            (r'token\b', Keyword, ('#pop', 'constants')),
            default(('#pop', 'constants'))
        ],
        'grammar': [
            (r'\)+', Punctuation),
            (r'\(', Punctuation, 'grammar-tag'),
            (r':', Punctuation, 'grammar-rules'),
            (_name, Name.Class),
            include('whitespace')
        ],
        'grammar-tag': [
            include('whitespace'),
            (r'"""([^\\"<]|""?(?!")|\\"+|\\.|<(?!<))+("{3,}|<<)|'
             r'R"""([^\\"]|""?(?!")|\\"+|\\.)+"{3,}|'
             r"'''([^\\'<]|''?(?!')|\\'+|\\.|<(?!<))+('{3,}|<<)|"
             r"R'''([^\\']|''?(?!')|\\'+|\\.)+'{3,}|"
             r'"([^\\"<]|\\.|<(?!<))+("|<<)|R"([^\\"]|\\.)+"|'
             r"'([^\\'<]|\\.|<(?!<))+('|<<)|R'([^\\']|\\.)+'|"
             r"([^)\s\\/]|/(?![/*]))+|\)", String.Other, '#pop')
        ],
        'grammar-rules': [
            include('string'),
            include('whitespace'),
            (rf'(\[)({_ws}*)(badness)',
             bygroups(Punctuation, using(this, state='whitespace'), Keyword),
             'main'),
            (rf'->|{_operator}|[()]', Punctuation),
            (_name, Name.Constant),
            default('#pop:2')
        ],
        ':': [
            (r':', Punctuation, '#pop')
        ],
        'function-name': [
            (r'(<<([^>]|>>>|>(?!>))*>>)+', String.Interpol),
            (rf'(?={_name}?{_ws}*[({{])', Text, '#pop'),
            (_name, Name.Function, '#pop'),
            include('whitespace')
        ],
        'inherited': [
            (r'<', Punctuation, ('#pop', 'classes', 'class')),
            include('whitespace'),
            (_name, Name.Class, '#pop'),
            default('#pop')
        ],
        'operator': [
            (r'negate\b', Operator.Word, '#pop'),
            include('whitespace'),
            (_operator, Operator),
            default('#pop')
        ],
        'propertyset': [
            (r'\(', Punctuation, ('more/parameters', 'main/parameters')),
            (r'\{', Punctuation, ('#pop', 'object-body')),
            include('whitespace')
        ],
        'template': [
            (r'(?=;)', Text, '#pop'),
            include('string'),
            (r'inherited\b', Keyword.Reserved),
            include('whitespace'),
            (rf'->|\?|{_operator}', Punctuation),
            (_name, Name.Variable)
        ],

        # Identifiers
        'class': [
            (r'\*|\.{3}', Punctuation, '#pop'),
            (r'object\b', Keyword.Reserved, '#pop'),
            (r'transient\b', Keyword.Reserved),
            (_name, Name.Class, '#pop'),
            include('whitespace'),
            default('#pop')
        ],
        'classes': [
            (r'[:,]', Punctuation, 'class'),
            include('whitespace'),
            (r'>', Punctuation, '#pop'),
            default('#pop')
        ],
        'constants': [
            (r',+', Punctuation),
            (r';', Punctuation, '#pop'),
            (r'property\b', Keyword.Reserved),
            (_name, Name.Constant),
            include('whitespace')
        ],
        'label': [
            (_name, Name.Label, '#pop'),
            include('whitespace'),
            default('#pop')
        ],
        'variables': [
            (r',+', Punctuation),
            (r'\)', Punctuation, '#pop'),
            include('whitespace'),
            (_name, Name.Variable)
        ],

        # Whitespace and comments
        'whitespace': [
            (rf'^{_ws_pp}*#({_comment_multiline}|[^\n]|(?<=\\)\n)*\n?',
             Comment.Preproc),
            (_comment_single, Comment.Single),
            (_comment_multiline, Comment.Multiline),
            (rf'\\+\n+{_ws_pp}*#?|\n+|([^\S\n]|\\)+', Text)
        ],

        # Strings
        'string': [
            (r'"""', String.Double, 'tdqs'),
            (r"'''", String.Single, 'tsqs'),
            (r'"', String.Double, 'dqs'),
            (r"'", String.Single, 'sqs')
        ],
        's/escape': [
            (rf'\{{\{{|\}}\}}|{_escape}', String.Escape)
        ],
        's/verbatim': [
            (r'<<\s*(as\s+decreasingly\s+likely\s+outcomes|cycling|else|end|'
             r'first\s+time|one\s+of|only|or|otherwise|'
             r'(sticky|(then\s+)?(purely\s+)?at)\s+random|stopping|'
             r'(then\s+)?(half\s+)?shuffled|\|\|)\s*>>', String.Interpol),
            (rf'<<(%(_({_escape}|\\?.)|[\-+ ,#]|\[\d*\]?)*\d*\.?\d*({_escape}|\\?.)|'
             r'\s*((else|otherwise)\s+)?(if|unless)\b)?',
             String.Interpol, ('block/embed', 'more/embed', 'main'))
        ],
        's/entity': [
            (r'(?i)&(#(x[\da-f]+|\d+)|[a-z][\da-z]*);?', Name.Entity)
        ],
        'tdqs': _make_string_state(True, True),
        'tsqs': _make_string_state(True, False),
        'dqs': _make_string_state(False, True),
        'sqs': _make_string_state(False, False),
        'tdqs/listing': _make_string_state(True, True, 'listing'),
        'tsqs/listing': _make_string_state(True, False, 'listing'),
        'dqs/listing': _make_string_state(False, True, 'listing'),
        'sqs/listing': _make_string_state(False, False, 'listing'),
        'tdqs/xmp': _make_string_state(True, True, 'xmp'),
        'tsqs/xmp': _make_string_state(True, False, 'xmp'),
        'dqs/xmp': _make_string_state(False, True, 'xmp'),
        'sqs/xmp': _make_string_state(False, False, 'xmp'),

        # Tags
        'tdqt': _make_tag_state(True, True),
        'tsqt': _make_tag_state(True, False),
        'dqt': _make_tag_state(False, True),
        'sqt': _make_tag_state(False, False),
        'dqs/tdqt': _make_attribute_value_state(r'"', True, True),
        'dqs/tsqt': _make_attribute_value_state(r'"', True, False),
        'dqs/dqt': _make_attribute_value_state(r'"', False, True),
        'dqs/sqt': _make_attribute_value_state(r'"', False, False),
        'sqs/tdqt': _make_attribute_value_state(r"'", True, True),
        'sqs/tsqt': _make_attribute_value_state(r"'", True, False),
        'sqs/dqt': _make_attribute_value_state(r"'", False, True),
        'sqs/sqt': _make_attribute_value_state(r"'", False, False),
        'uqs/tdqt': _make_attribute_value_state(_no_quote, True, True),
        'uqs/tsqt': _make_attribute_value_state(_no_quote, True, False),
        'uqs/dqt': _make_attribute_value_state(_no_quote, False, True),
        'uqs/sqt': _make_attribute_value_state(_no_quote, False, False),

        # Regular expressions
        'tdqr': [
            (r'[^\\"]+', String.Regex),
            (r'\\"*', String.Regex),
            (r'"{3,}', String.Regex, '#pop'),
            (r'"', String.Regex)
        ],
        'tsqr': [
            (r"[^\\']+", String.Regex),
            (r"\\'*", String.Regex),
            (r"'{3,}", String.Regex, '#pop'),
            (r"'", String.Regex)
        ],
        'dqr': [
            (r'[^\\"]+', String.Regex),
            (r'\\"?', String.Regex),
            (r'"', String.Regex, '#pop')
        ],
        'sqr': [
            (r"[^\\']+", String.Regex),
            (r"\\'?", String.Regex),
            (r"'", String.Regex, '#pop')
        ]
    }

    def get_tokens_unprocessed(self, text, **kwargs):
        pp = rf'^{self._ws_pp}*#{self._ws_pp}*'
        if_false_level = 0
        for index, token, value in (
            RegexLexer.get_tokens_unprocessed(self, text, **kwargs)):
            if if_false_level == 0:  # Not in a false #if
                if (token is Comment.Preproc and
                    re.match(rf'{pp}if{self._ws_pp}+(0|nil){self._ws_pp}*$\n?', value)):
                    if_false_level = 1
            else:  # In a false #if
                if token is Comment.Preproc:
                    if (if_false_level == 1 and
                          re.match(rf'{pp}el(if|se)\b', value)):
                        if_false_level = 0
                    elif re.match(rf'{pp}if', value):
                        if_false_level += 1
                    elif re.match(rf'{pp}endif\b', value):
                        if_false_level -= 1
                else:
                    token = Comment
            yield index, token, value

    def analyse_text(text):
        """This is a rather generic descriptive language without strong
        identifiers. It looks like a 'GameMainDef' has to be present,
        and/or a 'versionInfo' with an 'IFID' field."""
        result = 0
        if '__TADS' in text or 'GameMainDef' in text:
            result += 0.2

        # This is a fairly unique keyword which is likely used in source as well
        if 'versionInfo' in text and 'IFID' in text:
            result += 0.1

        return result

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\text.py ===
import re
from functools import partial, reduce
from math import gcd
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from ._loop import loop_last
from ._pick import pick_bool
from ._wrap import divide_line
from .align import AlignMethod
from .cells import cell_len, set_cell_size
from .containers import Lines
from .control import strip_control_codes
from .emoji import EmojiVariant
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

if TYPE_CHECKING:  # pragma: no cover
    from .console import Console, ConsoleOptions, JustifyMethod, OverflowMethod

DEFAULT_JUSTIFY: "JustifyMethod" = "default"
DEFAULT_OVERFLOW: "OverflowMethod" = "fold"


_re_whitespace = re.compile(r"\s+$")

TextType = Union[str, "Text"]
"""A plain string or a :class:`Text` instance."""

GetStyleCallable = Callable[[str], Optional[StyleType]]


class Span(NamedTuple):
    """A marked up region in some text."""

    start: int
    """Span start index."""
    end: int
    """Span end index."""
    style: Union[str, Style]
    """Style associated with the span."""

    def __repr__(self) -> str:
        return f"Span({self.start}, {self.end}, {self.style!r})"

    def __bool__(self) -> bool:
        return self.end > self.start

    def split(self, offset: int) -> Tuple["Span", Optional["Span"]]:
        """Split a span in to 2 from a given offset."""

        if offset < self.start:
            return self, None
        if offset >= self.end:
            return self, None

        start, end, style = self
        span1 = Span(start, min(end, offset), style)
        span2 = Span(span1.end, end, style)
        return span1, span2

    def move(self, offset: int) -> "Span":
        """Move start and end by a given offset.

        Args:
            offset (int): Number of characters to add to start and end.

        Returns:
            TextSpan: A new TextSpan with adjusted position.
        """
        start, end, style = self
        return Span(start + offset, end + offset, style)

    def right_crop(self, offset: int) -> "Span":
        """Crop the span at the given offset.

        Args:
            offset (int): A value between start and end.

        Returns:
            Span: A new (possibly smaller) span.
        """
        start, end, style = self
        if offset >= end:
            return self
        return Span(start, min(offset, end), style)

    def extend(self, cells: int) -> "Span":
        """Extend the span by the given number of cells.

        Args:
            cells (int): Additional space to add to end of span.

        Returns:
            Span: A span.
        """
        if cells:
            start, end, style = self
            return Span(start, end + cells, style)
        else:
            return self


class Text(JupyterMixin):
    """Text with color / style.

    Args:
        text (str, optional): Default unstyled text. Defaults to "".
        style (Union[str, Style], optional): Base style for text. Defaults to "".
        justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
        overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
        no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
        end (str, optional): Character to end text with. Defaults to "\\\\n".
        tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        spans (List[Span], optional). A list of predefined style spans. Defaults to None.
    """

    __slots__ = [
        "_text",
        "style",
        "justify",
        "overflow",
        "no_wrap",
        "end",
        "tab_size",
        "_spans",
        "_length",
    ]

    def __init__(
        self,
        text: str = "",
        style: Union[str, Style] = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = None,
        spans: Optional[List[Span]] = None,
    ) -> None:
        sanitized_text = strip_control_codes(text)
        self._text = [sanitized_text]
        self.style = style
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.end = end
        self.tab_size = tab_size
        self._spans: List[Span] = spans or []
        self._length: int = len(sanitized_text)

    def __len__(self) -> int:
        return self._length

    def __bool__(self) -> bool:
        return bool(self._length)

    def __str__(self) -> str:
        return self.plain

    def __repr__(self) -> str:
        return f"<text {self.plain!r} {self._spans!r} {self.style!r}>"

    def __add__(self, other: Any) -> "Text":
        if isinstance(other, (str, Text)):
            result = self.copy()
            result.append(other)
            return result
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Text):
            return NotImplemented
        return self.plain == other.plain and self._spans == other._spans

    def __contains__(self, other: object) -> bool:
        if isinstance(other, str):
            return other in self.plain
        elif isinstance(other, Text):
            return other.plain in self.plain
        return False

    def __getitem__(self, slice: Union[int, slice]) -> "Text":
        def get_text_at(offset: int) -> "Text":
            _Span = Span
            text = Text(
                self.plain[offset],
                spans=[
                    _Span(0, 1, style)
                    for start, end, style in self._spans
                    if end > offset >= start
                ],
                end="",
            )
            return text

        if isinstance(slice, int):
            return get_text_at(slice)
        else:
            start, stop, step = slice.indices(len(self.plain))
            if step == 1:
                lines = self.divide([start, stop])
                return lines[1]
            else:
                # This would be a bit of work to implement efficiently
                # For now, its not required
                raise TypeError("slices with step!=1 are not supported")

    @property
    def cell_len(self) -> int:
        """Get the number of cells required to render this text."""
        return cell_len(self.plain)

    @property
    def markup(self) -> str:
        """Get console markup to render this Text.

        Returns:
            str: A string potentially creating markup tags.
        """
        from .markup import escape

        output: List[str] = []

        plain = self.plain
        markup_spans = [
            (0, False, self.style),
            *((span.start, False, span.style) for span in self._spans),
            *((span.end, True, span.style) for span in self._spans),
            (len(plain), True, self.style),
        ]
        markup_spans.sort(key=itemgetter(0, 1))
        position = 0
        append = output.append
        for offset, closing, style in markup_spans:
            if offset > position:
                append(escape(plain[position:offset]))
                position = offset
            if style:
                append(f"[/{style}]" if closing else f"[{style}]")
        markup = "".join(output)
        return markup

    @classmethod
    def from_markup(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        emoji: bool = True,
        emoji_variant: Optional[EmojiVariant] = None,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        end: str = "\n",
    ) -> "Text":
        """Create Text instance from markup.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            emoji (bool, optional): Also render emoji code. Defaults to True.
            emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".

        Returns:
            Text: A Text instance with markup rendered.
        """
        from .markup import render

        rendered_text = render(text, style, emoji=emoji, emoji_variant=emoji_variant)
        rendered_text.justify = justify
        rendered_text.overflow = overflow
        rendered_text.end = end
        return rendered_text

    @classmethod
    def from_ansi(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = 8,
    ) -> "Text":
        """Create a Text object from a string containing ANSI escape codes.

        Args:
            text (str): A string containing escape codes.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        """
        from .ansi import AnsiDecoder

        joiner = Text(
            "\n",
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
            style=style,
        )
        decoder = AnsiDecoder()
        result = joiner.join(line for line in decoder.decode(text))
        return result

    @classmethod
    def styled(
        cls,
        text: str,
        style: StyleType = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
    ) -> "Text":
        """Construct a Text instance with a pre-applied styled. A style applied in this way won't be used
        to pad the text when it is justified.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style]): Style to apply to the text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.

        Returns:
            Text: A text instance with a style applied to the entire string.
        """
        styled_text = cls(text, justify=justify, overflow=overflow)
        styled_text.stylize(style)
        return styled_text

    @classmethod
    def assemble(
        cls,
        *parts: Union[str, "Text", Tuple[str, StyleType]],
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: int = 8,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Text":
        """Construct a text instance by combining a sequence of strings with optional styles.
        The positional arguments should be either strings, or a tuple of string + style.

        Args:
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
            meta (Dict[str, Any], optional). Meta data to apply to text, or None for no meta data. Default to None

        Returns:
            Text: A new text instance.
        """
        text = cls(
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
        )
        append = text.append
        _Text = Text
        for part in parts:
            if isinstance(part, (_Text, str)):
                append(part)
            else:
                append(*part)
        if meta:
            text.apply_meta(meta)
        return text

    @property
    def plain(self) -> str:
        """Get the text as a single string."""
        if len(self._text) != 1:
            self._text[:] = ["".join(self._text)]
        return self._text[0]

    @plain.setter
    def plain(self, new_text: str) -> None:
        """Set the text to a new value."""
        if new_text != self.plain:
            sanitized_text = strip_control_codes(new_text)
            self._text[:] = [sanitized_text]
            old_length = self._length
            self._length = len(sanitized_text)
            if old_length > self._length:
                self._trim_spans()

    @property
    def spans(self) -> List[Span]:
        """Get a reference to the internal list of spans."""
        return self._spans

    @spans.setter
    def spans(self, spans: List[Span]) -> None:
        """Set spans."""
        self._spans = spans[:]

    def blank_copy(self, plain: str = "") -> "Text":
        """Return a new Text instance with copied metadata (but not the string or spans)."""
        copy_self = Text(
            plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        return copy_self

    def copy(self) -> "Text":
        """Return a copy of this instance."""
        copy_self = Text(
            self.plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        copy_self._spans[:] = self._spans
        return copy_self

    def stylize(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.append(Span(start, min(length, end), style))

    def stylize_before(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text. Styles will be applied before other styles already present.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.insert(0, Span(start, min(length, end), style))

    def apply_meta(
        self, meta: Dict[str, Any], start: int = 0, end: Optional[int] = None
    ) -> None:
        """Apply metadata to the text, or a portion of the text.

        Args:
            meta (Dict[str, Any]): A dict of meta information.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.

        """
        style = Style.from_meta(meta)
        self.stylize(style, start=start, end=end)

    def on(self, meta: Optional[Dict[str, Any]] = None, **handlers: Any) -> "Text":
        """Apply event handlers (used by Textual project).

        Example:
            >>> from rich.text import Text
            >>> text = Text("hello world")
            >>> text.on(click="view.toggle('world')")

        Args:
            meta (Dict[str, Any]): Mapping of meta information.
            **handlers: Keyword args are prefixed with "@" to defined handlers.

        Returns:
            Text: Self is returned to method may be chained.
        """
        meta = {} if meta is None else meta
        meta.update({f"@{key}": value for key, value in handlers.items()})
        self.stylize(Style.from_meta(meta))
        return self

    def remove_suffix(self, suffix: str) -> None:
        """Remove a suffix if it exists.

        Args:
            suffix (str): Suffix to remove.
        """
        if self.plain.endswith(suffix):
            self.right_crop(len(suffix))

    def get_style_at_offset(self, console: "Console", offset: int) -> Style:
        """Get the style of a character at give offset.

        Args:
            console (~Console): Console where text will be rendered.
            offset (int): Offset in to text (negative indexing supported)

        Returns:
            Style: A Style instance.
        """
        # TODO: This is a little inefficient, it is only used by full justify
        if offset < 0:
            offset = len(self) + offset
        get_style = console.get_style
        style = get_style(self.style).copy()
        for start, end, span_style in self._spans:
            if end > offset >= start:
                style += get_style(span_style, default="")
        return style

    def extend_style(self, spaces: int) -> None:
        """Extend the Text given number of spaces where the spaces have the same style as the last character.

        Args:
            spaces (int): Number of spaces to add to the Text.
        """
        if spaces <= 0:
            return
        spans = self.spans
        new_spaces = " " * spaces
        if spans:
            end_offset = len(self)
            self._spans[:] = [
                span.extend(spaces) if span.end >= end_offset else span
                for span in spans
            ]
            self._text.append(new_spaces)
            self._length += spaces
        else:
            self.plain += new_spaces

    def highlight_regex(
        self,
        re_highlight: Union[Pattern[str], str],
        style: Optional[Union[GetStyleCallable, StyleType]] = None,
        *,
        style_prefix: str = "",
    ) -> int:
        """Highlight text with a regular expression, where group names are
        translated to styles.

        Args:
            re_highlight (Union[re.Pattern, str]): A regular expression object or string.
            style (Union[GetStyleCallable, StyleType]): Optional style to apply to whole match, or a callable
                which accepts the matched text and returns a style. Defaults to None.
            style_prefix (str, optional): Optional prefix to add to style group names.

        Returns:
            int: Number of regex matches
        """
        count = 0
        append_span = self._spans.append
        _Span = Span
        plain = self.plain
        if isinstance(re_highlight, str):
            re_highlight = re.compile(re_highlight)
        for match in re_highlight.finditer(plain):
            get_span = match.span
            if style:
                start, end = get_span()
                match_style = style(plain[start:end]) if callable(style) else style
                if match_style is not None and end > start:
                    append_span(_Span(start, end, match_style))

            count += 1
            for name in match.groupdict().keys():
                start, end = get_span(name)
                if start != -1 and end > start:
                    append_span(_Span(start, end, f"{style_prefix}{name}"))
        return count

    def highlight_words(
        self,
        words: Iterable[str],
        style: Union[str, Style],
        *,
        case_sensitive: bool = True,
    ) -> int:
        """Highlight words with a style.

        Args:
            words (Iterable[str]): Words to highlight.
            style (Union[str, Style]): Style to apply.
            case_sensitive (bool, optional): Enable case sensitive matching. Defaults to True.

        Returns:
            int: Number of words highlighted.
        """
        re_words = "|".join(re.escape(word) for word in words)
        add_span = self._spans.append
        count = 0
        _Span = Span
        for match in re.finditer(
            re_words, self.plain, flags=0 if case_sensitive else re.IGNORECASE
        ):
            start, end = match.span(0)
            add_span(_Span(start, end, style))
            count += 1
        return count

    def rstrip(self) -> None:
        """Strip whitespace from end of text."""
        self.plain = self.plain.rstrip()

    def rstrip_end(self, size: int) -> None:
        """Remove whitespace beyond a certain width at the end of the text.

        Args:
            size (int): The desired size of the text.
        """
        text_length = len(self)
        if text_length > size:
            excess = text_length - size
            whitespace_match = _re_whitespace.search(self.plain)
            if whitespace_match is not None:
                whitespace_count = len(whitespace_match.group(0))
                self.right_crop(min(whitespace_count, excess))

    def set_length(self, new_length: int) -> None:
        """Set new length of the text, clipping or padding is required."""
        length = len(self)
        if length != new_length:
            if length < new_length:
                self.pad_right(new_length - length)
            else:
                self.right_crop(length - new_length)

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Iterable[Segment]:
        tab_size: int = console.tab_size if self.tab_size is None else self.tab_size
        justify = self.justify or options.justify or DEFAULT_JUSTIFY

        overflow = self.overflow or options.overflow or DEFAULT_OVERFLOW

        lines = self.wrap(
            console,
            options.max_width,
            justify=justify,
            overflow=overflow,
            tab_size=tab_size or 8,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap, False),
        )
        all_lines = Text("\n").join(lines)
        yield from all_lines.render(console, end=self.end)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        text = self.plain
        lines = text.splitlines()
        max_text_width = max(cell_len(line) for line in lines) if lines else 0
        words = text.split()
        min_text_width = (
            max(cell_len(word) for word in words) if words else max_text_width
        )
        return Measurement(min_text_width, max_text_width)

    def render(self, console: "Console", end: str = "") -> Iterable["Segment"]:
        """Render the text as Segments.

        Args:
            console (Console): Console instance.
            end (Optional[str], optional): Optional end character.

        Returns:
            Iterable[Segment]: Result of render that may be written to the console.
        """
        _Segment = Segment
        text = self.plain
        if not self._spans:
            yield Segment(text)
            if end:
                yield _Segment(end)
            return
        get_style = partial(console.get_style, default=Style.null())

        enumerated_spans = list(enumerate(self._spans, 1))
        style_map = {index: get_style(span.style) for index, span in enumerated_spans}
        style_map[0] = get_style(self.style)

        spans = [
            (0, False, 0),
            *((span.start, False, index) for index, span in enumerated_spans),
            *((span.end, True, index) for index, span in enumerated_spans),
            (len(text), True, 0),
        ]
        spans.sort(key=itemgetter(0, 1))

        stack: List[int] = []
        stack_append = stack.append
        stack_pop = stack.remove

        style_cache: Dict[Tuple[Style, ...], Style] = {}
        style_cache_get = style_cache.get
        combine = Style.combine

        def get_current_style() -> Style:
            """Construct current style from stack."""
            styles = tuple(style_map[_style_id] for _style_id in sorted(stack))
            cached_style = style_cache_get(styles)
            if cached_style is not None:
                return cached_style
            current_style = combine(styles)
            style_cache[styles] = current_style
            return current_style

        for (offset, leaving, style_id), (next_offset, _, _) in zip(spans, spans[1:]):
            if leaving:
                stack_pop(style_id)
            else:
                stack_append(style_id)
            if next_offset > offset:
                yield _Segment(text[offset:next_offset], get_current_style())
        if end:
            yield _Segment(end)

    def join(self, lines: Iterable["Text"]) -> "Text":
        """Join text together with this instance as the separator.

        Args:
            lines (Iterable[Text]): An iterable of Text instances to join.

        Returns:
            Text: A new text instance containing join text.
        """

        new_text = self.blank_copy()

        def iter_text() -> Iterable["Text"]:
            if self.plain:
                for last, line in loop_last(lines):
                    yield line
                    if not last:
                        yield self
            else:
                yield from lines

        extend_text = new_text._text.extend
        append_span = new_text._spans.append
        extend_spans = new_text._spans.extend
        offset = 0
        _Span = Span

        for text in iter_text():
            extend_text(text._text)
            if text.style:
                append_span(_Span(offset, offset + len(text), text.style))
            extend_spans(
                _Span(offset + start, offset + end, style)
                for start, end, style in text._spans
            )
            offset += len(text)
        new_text._length = offset
        return new_text

    def expand_tabs(self, tab_size: Optional[int] = None) -> None:
        """Converts tabs to spaces.

        Args:
            tab_size (int, optional): Size of tabs. Defaults to 8.

        """
        if "\t" not in self.plain:
            return
        if tab_size is None:
            tab_size = self.tab_size
        if tab_size is None:
            tab_size = 8

        new_text: List[Text] = []
        append = new_text.append

        for line in self.split("\n", include_separator=True):
            if "\t" not in line.plain:
                append(line)
            else:
                cell_position = 0
                parts = line.split("\t", include_separator=True)
                for part in parts:
                    if part.plain.endswith("\t"):
                        part._text[-1] = part._text[-1][:-1] + " "
                        cell_position += part.cell_len
                        tab_remainder = cell_position % tab_size
                        if tab_remainder:
                            spaces = tab_size - tab_remainder
                            part.extend_style(spaces)
                            cell_position += spaces
                    else:
                        cell_position += part.cell_len
                    append(part)

        result = Text("").join(new_text)

        self._text = [result.plain]
        self._length = len(self.plain)
        self._spans[:] = result._spans

    def truncate(
        self,
        max_width: int,
        *,
        overflow: Optional["OverflowMethod"] = None,
        pad: bool = False,
    ) -> None:
        """Truncate text if it is longer that a given width.

        Args:
            max_width (int): Maximum number of characters in text.
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None, to use self.overflow.
            pad (bool, optional): Pad with spaces if the length is less than max_width. Defaults to False.
        """
        _overflow = overflow or self.overflow or DEFAULT_OVERFLOW
        if _overflow != "ignore":
            length = cell_len(self.plain)
            if length > max_width:
                if _overflow == "ellipsis":
                    self.plain = set_cell_size(self.plain, max_width - 1) + "…"
                else:
                    self.plain = set_cell_size(self.plain, max_width)
            if pad and length < max_width:
                spaces = max_width - length
                self._text = [f"{self.plain}{' ' * spaces}"]
                self._length = len(self.plain)

    def _trim_spans(self) -> None:
        """Remove or modify any spans that are over the end of the text."""
        max_offset = len(self.plain)
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]

    def pad(self, count: int, character: str = " ") -> None:
        """Pad left and right with a given number of characters.

        Args:
            count (int): Width of padding.
            character (str): The character to pad with. Must be a string of length 1.
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            pad_characters = character * count
            self.plain = f"{pad_characters}{self.plain}{pad_characters}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_left(self, count: int, character: str = " ") -> None:
        """Pad the left with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{character * count}{self.plain}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_right(self, count: int, character: str = " ") -> None:
        """Pad the right with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{self.plain}{character * count}"

    def align(self, align: AlignMethod, width: int, character: str = " ") -> None:
        """Align text to a given width.

        Args:
            align (AlignMethod): One of "left", "center", or "right".
            width (int): Desired width.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        self.truncate(width)
        excess_space = width - cell_len(self.plain)
        if excess_space:
            if align == "left":
                self.pad_right(excess_space, character)
            elif align == "center":
                left = excess_space // 2
                self.pad_left(left, character)
                self.pad_right(excess_space - left, character)
            else:
                self.pad_left(excess_space, character)

    def append(
        self, text: Union["Text", str], style: Optional[Union[str, "Style"]] = None
    ) -> "Text":
        """Add text with an optional style.

        Args:
            text (Union[Text, str]): A str or Text to append.
            style (str, optional): A style name. Defaults to None.

        Returns:
            Text: Returns self for chaining.
        """

        if not isinstance(text, (str, Text)):
            raise TypeError("Only str or Text can be appended to Text")

        if len(text):
            if isinstance(text, str):
                sanitized_text = strip_control_codes(text)
                self._text.append(sanitized_text)
                offset = len(self)
                text_length = len(sanitized_text)
                if style:
                    self._spans.append(Span(offset, offset + text_length, style))
                self._length += text_length
            elif isinstance(text, Text):
                _Span = Span
                if style is not None:
                    raise ValueError(
                        "style must not be set when appending Text instance"
                    )
                text_length = self._length
                if text.style:
                    self._spans.append(
                        _Span(text_length, text_length + len(text), text.style)
                    )
                self._text.append(text.plain)
                self._spans.extend(
                    _Span(start + text_length, end + text_length, style)
                    for start, end, style in text._spans.copy()
                )
                self._length += len(text)
        return self

    def append_text(self, text: "Text") -> "Text":
        """Append another Text instance. This method is more performant that Text.append, but
        only works for Text.

        Args:
            text (Text): The Text instance to append to this instance.

        Returns:
            Text: Returns self for chaining.
        """
        _Span = Span
        text_length = self._length
        if text.style:
            self._spans.append(_Span(text_length, text_length + len(text), text.style))
        self._text.append(text.plain)
        self._spans.extend(
            _Span(start + text_length, end + text_length, style)
            for start, end, style in text._spans.copy()
        )
        self._length += len(text)
        return self

    def append_tokens(
        self, tokens: Iterable[Tuple[str, Optional[StyleType]]]
    ) -> "Text":
        """Append iterable of str and style. Style may be a Style instance or a str style definition.

        Args:
            tokens (Iterable[Tuple[str, Optional[StyleType]]]): An iterable of tuples containing str content and style.

        Returns:
            Text: Returns self for chaining.
        """
        append_text = self._text.append
        append_span = self._spans.append
        _Span = Span
        offset = len(self)
        for content, style in tokens:
            content = strip_control_codes(content)
            append_text(content)
            if style:
                append_span(_Span(offset, offset + len(content), style))
            offset += len(content)
        self._length = offset
        return self

    def copy_styles(self, text: "Text") -> None:
        """Copy styles from another Text instance.

        Args:
            text (Text): A Text instance to copy styles from, must be the same length.
        """
        self._spans.extend(text._spans)

    def split(
        self,
        separator: str = "\n",
        *,
        include_separator: bool = False,
        allow_blank: bool = False,
    ) -> Lines:
        """Split rich text in to lines, preserving styles.

        Args:
            separator (str, optional): String to split on. Defaults to "\\\\n".
            include_separator (bool, optional): Include the separator in the lines. Defaults to False.
            allow_blank (bool, optional): Return a blank line if the text ends with a separator. Defaults to False.

        Returns:
            List[RichText]: A list of rich text, one per line of the original.
        """
        assert separator, "separator must not be empty"

        text = self.plain
        if separator not in text:
            return Lines([self.copy()])

        if include_separator:
            lines = self.divide(
                match.end() for match in re.finditer(re.escape(separator), text)
            )
        else:

            def flatten_spans() -> Iterable[int]:
                for match in re.finditer(re.escape(separator), text):
                    start, end = match.span()
                    yield start
                    yield end

            lines = Lines(
                line for line in self.divide(flatten_spans()) if line.plain != separator
            )

        if not allow_blank and text.endswith(separator):
            lines.pop()

        return lines

    def divide(self, offsets: Iterable[int]) -> Lines:
        """Divide text in to a number of lines at given offsets.

        Args:
            offsets (Iterable[int]): Offsets used to divide text.

        Returns:
            Lines: New RichText instances between offsets.
        """
        _offsets = list(offsets)

        if not _offsets:
            return Lines([self.copy()])

        text = self.plain
        text_length = len(text)
        divide_offsets = [0, *_offsets, text_length]
        line_ranges = list(zip(divide_offsets, divide_offsets[1:]))

        style = self.style
        justify = self.justify
        overflow = self.overflow
        _Text = Text
        new_lines = Lines(
            _Text(
                text[start:end],
                style=style,
                justify=justify,
                overflow=overflow,
            )
            for start, end in line_ranges
        )
        if not self._spans:
            return new_lines

        _line_appends = [line._spans.append for line in new_lines._lines]
        line_count = len(line_ranges)
        _Span = Span

        for span_start, span_end, style in self._spans:
            lower_bound = 0
            upper_bound = line_count
            start_line_no = (lower_bound + upper_bound) // 2

            while True:
                line_start, line_end = line_ranges[start_line_no]
                if span_start < line_start:
                    upper_bound = start_line_no - 1
                elif span_start > line_end:
                    lower_bound = start_line_no + 1
                else:
                    break
                start_line_no = (lower_bound + upper_bound) // 2

            if span_end < line_end:
                end_line_no = start_line_no
            else:
                end_line_no = lower_bound = start_line_no
                upper_bound = line_count

                while True:
                    line_start, line_end = line_ranges[end_line_no]
                    if span_end < line_start:
                        upper_bound = end_line_no - 1
                    elif span_end > line_end:
                        lower_bound = end_line_no + 1
                    else:
                        break
                    end_line_no = (lower_bound + upper_bound) // 2

            for line_no in range(start_line_no, end_line_no + 1):
                line_start, line_end = line_ranges[line_no]
                new_start = max(0, span_start - line_start)
                new_end = min(span_end - line_start, line_end - line_start)
                if new_end > new_start:
                    _line_appends[line_no](_Span(new_start, new_end, style))

        return new_lines

    def right_crop(self, amount: int = 1) -> None:
        """Remove a number of characters from the end of the text."""
        max_offset = len(self.plain) - amount
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]
        self._text = [self.plain[:-amount]]
        self._length -= amount

    def wrap(
        self,
        console: "Console",
        width: int,
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        tab_size: int = 8,
        no_wrap: Optional[bool] = None,
    ) -> Lines:
        """Word wrap the text.

        Args:
            console (Console): Console instance.
            width (int): Number of cells available per line.
            justify (str, optional): Justify method: "default", "left", "center", "full", "right". Defaults to "default".
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None.
            tab_size (int, optional): Default tab size. Defaults to 8.
            no_wrap (bool, optional): Disable wrapping, Defaults to False.

        Returns:
            Lines: Number of lines.
        """
        wrap_justify = justify or self.justify or DEFAULT_JUSTIFY
        wrap_overflow = overflow or self.overflow or DEFAULT_OVERFLOW

        no_wrap = pick_bool(no_wrap, self.no_wrap, False) or overflow == "ignore"

        lines = Lines()
        for line in self.split(allow_blank=True):
            if "\t" in line:
                line.expand_tabs(tab_size)
            if no_wrap:
                new_lines = Lines([line])
            else:
                offsets = divide_line(str(line), width, fold=wrap_overflow == "fold")
                new_lines = line.divide(offsets)
            for line in new_lines:
                line.rstrip_end(width)
            if wrap_justify:
                new_lines.justify(
                    console, width, justify=wrap_justify, overflow=wrap_overflow
                )
            for line in new_lines:
                line.truncate(width, overflow=wrap_overflow)
            lines.extend(new_lines)
        return lines

    def fit(self, width: int) -> Lines:
        """Fit the text in to given width by chopping in to lines.

        Args:
            width (int): Maximum characters in a line.

        Returns:
            Lines: Lines container.
        """
        lines: Lines = Lines()
        append = lines.append
        for line in self.split():
            line.set_length(width)
            append(line)
        return lines

    def detect_indentation(self) -> int:
        """Auto-detect indentation of code.

        Returns:
            int: Number of spaces used to indent code.
        """

        _indentations = {
            len(match.group(1))
            for match in re.finditer(r"^( *)(.*)$", self.plain, flags=re.MULTILINE)
        }

        try:
            indentation = (
                reduce(gcd, [indent for indent in _indentations if not indent % 2]) or 1
            )
        except TypeError:
            indentation = 1

        return indentation

    def with_indent_guides(
        self,
        indent_size: Optional[int] = None,
        *,
        character: str = "│",
        style: StyleType = "dim green",
    ) -> "Text":
        """Adds indent guide lines to text.

        Args:
            indent_size (Optional[int]): Size of indentation, or None to auto detect. Defaults to None.
            character (str, optional): Character to use for indentation. Defaults to "│".
            style (Union[Style, str], optional): Style of indent guides.

        Returns:
            Text: New text with indentation guides.
        """

        _indent_size = self.detect_indentation() if indent_size is None else indent_size

        text = self.copy()
        text.expand_tabs()
        indent_line = f"{character}{' ' * (_indent_size - 1)}"

        re_indent = re.compile(r"^( *)(.*)$")
        new_lines: List[Text] = []
        add_line = new_lines.append
        blank_lines = 0
        for line in text.split(allow_blank=True):
            match = re_indent.match(line.plain)
            if not match or not match.group(2):
                blank_lines += 1
                continue
            indent = match.group(1)
            full_indents, remaining_space = divmod(len(indent), _indent_size)
            new_indent = f"{indent_line * full_indents}{' ' * remaining_space}"
            line.plain = new_indent + line.plain[len(new_indent) :]
            line.stylize(style, 0, len(new_indent))
            if blank_lines:
                new_lines.extend([Text(new_indent, style=style)] * blank_lines)
                blank_lines = 0
            add_line(line)
        if blank_lines:
            new_lines.extend([Text("", style=style)] * blank_lines)

        new_text = text.blank_copy("\n").join(new_lines)
        return new_text


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console

    text = Text(
        """\nLorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n"""
    )
    text.highlight_words(["Lorem"], "bold")
    text.highlight_words(["ipsum"], "italic")

    console = Console()

    console.rule("justify='left'")
    console.print(text, style="red")
    console.print()

    console.rule("justify='center'")
    console.print(text, style="green", justify="center")
    console.print()

    console.rule("justify='right'")
    console.print(text, style="blue", justify="right")
    console.print()

    console.rule("justify='full'")
    console.print(text, style="magenta", justify="full")
    console.print()

# === NexusCore/openenv\Lib\site-packages\rich\text.py ===
import re
from functools import partial, reduce
from math import gcd
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from ._loop import loop_last
from ._pick import pick_bool
from ._wrap import divide_line
from .align import AlignMethod
from .cells import cell_len, set_cell_size
from .containers import Lines
from .control import strip_control_codes
from .emoji import EmojiVariant
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

if TYPE_CHECKING:  # pragma: no cover
    from .console import Console, ConsoleOptions, JustifyMethod, OverflowMethod

DEFAULT_JUSTIFY: "JustifyMethod" = "default"
DEFAULT_OVERFLOW: "OverflowMethod" = "fold"


_re_whitespace = re.compile(r"\s+$")

TextType = Union[str, "Text"]
"""A plain string or a :class:`Text` instance."""

GetStyleCallable = Callable[[str], Optional[StyleType]]


class Span(NamedTuple):
    """A marked up region in some text."""

    start: int
    """Span start index."""
    end: int
    """Span end index."""
    style: Union[str, Style]
    """Style associated with the span."""

    def __repr__(self) -> str:
        return f"Span({self.start}, {self.end}, {self.style!r})"

    def __bool__(self) -> bool:
        return self.end > self.start

    def split(self, offset: int) -> Tuple["Span", Optional["Span"]]:
        """Split a span in to 2 from a given offset."""

        if offset < self.start:
            return self, None
        if offset >= self.end:
            return self, None

        start, end, style = self
        span1 = Span(start, min(end, offset), style)
        span2 = Span(span1.end, end, style)
        return span1, span2

    def move(self, offset: int) -> "Span":
        """Move start and end by a given offset.

        Args:
            offset (int): Number of characters to add to start and end.

        Returns:
            TextSpan: A new TextSpan with adjusted position.
        """
        start, end, style = self
        return Span(start + offset, end + offset, style)

    def right_crop(self, offset: int) -> "Span":
        """Crop the span at the given offset.

        Args:
            offset (int): A value between start and end.

        Returns:
            Span: A new (possibly smaller) span.
        """
        start, end, style = self
        if offset >= end:
            return self
        return Span(start, min(offset, end), style)

    def extend(self, cells: int) -> "Span":
        """Extend the span by the given number of cells.

        Args:
            cells (int): Additional space to add to end of span.

        Returns:
            Span: A span.
        """
        if cells:
            start, end, style = self
            return Span(start, end + cells, style)
        else:
            return self


class Text(JupyterMixin):
    """Text with color / style.

    Args:
        text (str, optional): Default unstyled text. Defaults to "".
        style (Union[str, Style], optional): Base style for text. Defaults to "".
        justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
        overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
        no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
        end (str, optional): Character to end text with. Defaults to "\\\\n".
        tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        spans (List[Span], optional). A list of predefined style spans. Defaults to None.
    """

    __slots__ = [
        "_text",
        "style",
        "justify",
        "overflow",
        "no_wrap",
        "end",
        "tab_size",
        "_spans",
        "_length",
    ]

    def __init__(
        self,
        text: str = "",
        style: Union[str, Style] = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = None,
        spans: Optional[List[Span]] = None,
    ) -> None:
        sanitized_text = strip_control_codes(text)
        self._text = [sanitized_text]
        self.style = style
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.end = end
        self.tab_size = tab_size
        self._spans: List[Span] = spans or []
        self._length: int = len(sanitized_text)

    def __len__(self) -> int:
        return self._length

    def __bool__(self) -> bool:
        return bool(self._length)

    def __str__(self) -> str:
        return self.plain

    def __repr__(self) -> str:
        return f"<text {self.plain!r} {self._spans!r} {self.style!r}>"

    def __add__(self, other: Any) -> "Text":
        if isinstance(other, (str, Text)):
            result = self.copy()
            result.append(other)
            return result
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Text):
            return NotImplemented
        return self.plain == other.plain and self._spans == other._spans

    def __contains__(self, other: object) -> bool:
        if isinstance(other, str):
            return other in self.plain
        elif isinstance(other, Text):
            return other.plain in self.plain
        return False

    def __getitem__(self, slice: Union[int, slice]) -> "Text":
        def get_text_at(offset: int) -> "Text":
            _Span = Span
            text = Text(
                self.plain[offset],
                spans=[
                    _Span(0, 1, style)
                    for start, end, style in self._spans
                    if end > offset >= start
                ],
                end="",
            )
            return text

        if isinstance(slice, int):
            return get_text_at(slice)
        else:
            start, stop, step = slice.indices(len(self.plain))
            if step == 1:
                lines = self.divide([start, stop])
                return lines[1]
            else:
                # This would be a bit of work to implement efficiently
                # For now, its not required
                raise TypeError("slices with step!=1 are not supported")

    @property
    def cell_len(self) -> int:
        """Get the number of cells required to render this text."""
        return cell_len(self.plain)

    @property
    def markup(self) -> str:
        """Get console markup to render this Text.

        Returns:
            str: A string potentially creating markup tags.
        """
        from .markup import escape

        output: List[str] = []

        plain = self.plain
        markup_spans = [
            (0, False, self.style),
            *((span.start, False, span.style) for span in self._spans),
            *((span.end, True, span.style) for span in self._spans),
            (len(plain), True, self.style),
        ]
        markup_spans.sort(key=itemgetter(0, 1))
        position = 0
        append = output.append
        for offset, closing, style in markup_spans:
            if offset > position:
                append(escape(plain[position:offset]))
                position = offset
            if style:
                append(f"[/{style}]" if closing else f"[{style}]")
        markup = "".join(output)
        return markup

    @classmethod
    def from_markup(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        emoji: bool = True,
        emoji_variant: Optional[EmojiVariant] = None,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        end: str = "\n",
    ) -> "Text":
        """Create Text instance from markup.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            emoji (bool, optional): Also render emoji code. Defaults to True.
            emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".

        Returns:
            Text: A Text instance with markup rendered.
        """
        from .markup import render

        rendered_text = render(text, style, emoji=emoji, emoji_variant=emoji_variant)
        rendered_text.justify = justify
        rendered_text.overflow = overflow
        rendered_text.end = end
        return rendered_text

    @classmethod
    def from_ansi(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = 8,
    ) -> "Text":
        """Create a Text object from a string containing ANSI escape codes.

        Args:
            text (str): A string containing escape codes.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        """
        from .ansi import AnsiDecoder

        joiner = Text(
            "\n",
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
            style=style,
        )
        decoder = AnsiDecoder()
        result = joiner.join(line for line in decoder.decode(text))
        return result

    @classmethod
    def styled(
        cls,
        text: str,
        style: StyleType = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
    ) -> "Text":
        """Construct a Text instance with a pre-applied styled. A style applied in this way won't be used
        to pad the text when it is justified.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style]): Style to apply to the text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.

        Returns:
            Text: A text instance with a style applied to the entire string.
        """
        styled_text = cls(text, justify=justify, overflow=overflow)
        styled_text.stylize(style)
        return styled_text

    @classmethod
    def assemble(
        cls,
        *parts: Union[str, "Text", Tuple[str, StyleType]],
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: int = 8,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Text":
        """Construct a text instance by combining a sequence of strings with optional styles.
        The positional arguments should be either strings, or a tuple of string + style.

        Args:
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
            meta (Dict[str, Any], optional). Meta data to apply to text, or None for no meta data. Default to None

        Returns:
            Text: A new text instance.
        """
        text = cls(
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
        )
        append = text.append
        _Text = Text
        for part in parts:
            if isinstance(part, (_Text, str)):
                append(part)
            else:
                append(*part)
        if meta:
            text.apply_meta(meta)
        return text

    @property
    def plain(self) -> str:
        """Get the text as a single string."""
        if len(self._text) != 1:
            self._text[:] = ["".join(self._text)]
        return self._text[0]

    @plain.setter
    def plain(self, new_text: str) -> None:
        """Set the text to a new value."""
        if new_text != self.plain:
            sanitized_text = strip_control_codes(new_text)
            self._text[:] = [sanitized_text]
            old_length = self._length
            self._length = len(sanitized_text)
            if old_length > self._length:
                self._trim_spans()

    @property
    def spans(self) -> List[Span]:
        """Get a reference to the internal list of spans."""
        return self._spans

    @spans.setter
    def spans(self, spans: List[Span]) -> None:
        """Set spans."""
        self._spans = spans[:]

    def blank_copy(self, plain: str = "") -> "Text":
        """Return a new Text instance with copied metadata (but not the string or spans)."""
        copy_self = Text(
            plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        return copy_self

    def copy(self) -> "Text":
        """Return a copy of this instance."""
        copy_self = Text(
            self.plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        copy_self._spans[:] = self._spans
        return copy_self

    def stylize(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.append(Span(start, min(length, end), style))

    def stylize_before(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text. Styles will be applied before other styles already present.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.insert(0, Span(start, min(length, end), style))

    def apply_meta(
        self, meta: Dict[str, Any], start: int = 0, end: Optional[int] = None
    ) -> None:
        """Apply metadata to the text, or a portion of the text.

        Args:
            meta (Dict[str, Any]): A dict of meta information.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.

        """
        style = Style.from_meta(meta)
        self.stylize(style, start=start, end=end)

    def on(self, meta: Optional[Dict[str, Any]] = None, **handlers: Any) -> "Text":
        """Apply event handlers (used by Textual project).

        Example:
            >>> from rich.text import Text
            >>> text = Text("hello world")
            >>> text.on(click="view.toggle('world')")

        Args:
            meta (Dict[str, Any]): Mapping of meta information.
            **handlers: Keyword args are prefixed with "@" to defined handlers.

        Returns:
            Text: Self is returned to method may be chained.
        """
        meta = {} if meta is None else meta
        meta.update({f"@{key}": value for key, value in handlers.items()})
        self.stylize(Style.from_meta(meta))
        return self

    def remove_suffix(self, suffix: str) -> None:
        """Remove a suffix if it exists.

        Args:
            suffix (str): Suffix to remove.
        """
        if self.plain.endswith(suffix):
            self.right_crop(len(suffix))

    def get_style_at_offset(self, console: "Console", offset: int) -> Style:
        """Get the style of a character at give offset.

        Args:
            console (~Console): Console where text will be rendered.
            offset (int): Offset in to text (negative indexing supported)

        Returns:
            Style: A Style instance.
        """
        # TODO: This is a little inefficient, it is only used by full justify
        if offset < 0:
            offset = len(self) + offset
        get_style = console.get_style
        style = get_style(self.style).copy()
        for start, end, span_style in self._spans:
            if end > offset >= start:
                style += get_style(span_style, default="")
        return style

    def extend_style(self, spaces: int) -> None:
        """Extend the Text given number of spaces where the spaces have the same style as the last character.

        Args:
            spaces (int): Number of spaces to add to the Text.
        """
        if spaces <= 0:
            return
        spans = self.spans
        new_spaces = " " * spaces
        if spans:
            end_offset = len(self)
            self._spans[:] = [
                span.extend(spaces) if span.end >= end_offset else span
                for span in spans
            ]
            self._text.append(new_spaces)
            self._length += spaces
        else:
            self.plain += new_spaces

    def highlight_regex(
        self,
        re_highlight: Union[Pattern[str], str],
        style: Optional[Union[GetStyleCallable, StyleType]] = None,
        *,
        style_prefix: str = "",
    ) -> int:
        """Highlight text with a regular expression, where group names are
        translated to styles.

        Args:
            re_highlight (Union[re.Pattern, str]): A regular expression object or string.
            style (Union[GetStyleCallable, StyleType]): Optional style to apply to whole match, or a callable
                which accepts the matched text and returns a style. Defaults to None.
            style_prefix (str, optional): Optional prefix to add to style group names.

        Returns:
            int: Number of regex matches
        """
        count = 0
        append_span = self._spans.append
        _Span = Span
        plain = self.plain
        if isinstance(re_highlight, str):
            re_highlight = re.compile(re_highlight)
        for match in re_highlight.finditer(plain):
            get_span = match.span
            if style:
                start, end = get_span()
                match_style = style(plain[start:end]) if callable(style) else style
                if match_style is not None and end > start:
                    append_span(_Span(start, end, match_style))

            count += 1
            for name in match.groupdict().keys():
                start, end = get_span(name)
                if start != -1 and end > start:
                    append_span(_Span(start, end, f"{style_prefix}{name}"))
        return count

    def highlight_words(
        self,
        words: Iterable[str],
        style: Union[str, Style],
        *,
        case_sensitive: bool = True,
    ) -> int:
        """Highlight words with a style.

        Args:
            words (Iterable[str]): Words to highlight.
            style (Union[str, Style]): Style to apply.
            case_sensitive (bool, optional): Enable case sensitive matching. Defaults to True.

        Returns:
            int: Number of words highlighted.
        """
        re_words = "|".join(re.escape(word) for word in words)
        add_span = self._spans.append
        count = 0
        _Span = Span
        for match in re.finditer(
            re_words, self.plain, flags=0 if case_sensitive else re.IGNORECASE
        ):
            start, end = match.span(0)
            add_span(_Span(start, end, style))
            count += 1
        return count

    def rstrip(self) -> None:
        """Strip whitespace from end of text."""
        self.plain = self.plain.rstrip()

    def rstrip_end(self, size: int) -> None:
        """Remove whitespace beyond a certain width at the end of the text.

        Args:
            size (int): The desired size of the text.
        """
        text_length = len(self)
        if text_length > size:
            excess = text_length - size
            whitespace_match = _re_whitespace.search(self.plain)
            if whitespace_match is not None:
                whitespace_count = len(whitespace_match.group(0))
                self.right_crop(min(whitespace_count, excess))

    def set_length(self, new_length: int) -> None:
        """Set new length of the text, clipping or padding is required."""
        length = len(self)
        if length != new_length:
            if length < new_length:
                self.pad_right(new_length - length)
            else:
                self.right_crop(length - new_length)

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Iterable[Segment]:
        tab_size: int = console.tab_size if self.tab_size is None else self.tab_size
        justify = self.justify or options.justify or DEFAULT_JUSTIFY

        overflow = self.overflow or options.overflow or DEFAULT_OVERFLOW

        lines = self.wrap(
            console,
            options.max_width,
            justify=justify,
            overflow=overflow,
            tab_size=tab_size or 8,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap, False),
        )
        all_lines = Text("\n").join(lines)
        yield from all_lines.render(console, end=self.end)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        text = self.plain
        lines = text.splitlines()
        max_text_width = max(cell_len(line) for line in lines) if lines else 0
        words = text.split()
        min_text_width = (
            max(cell_len(word) for word in words) if words else max_text_width
        )
        return Measurement(min_text_width, max_text_width)

    def render(self, console: "Console", end: str = "") -> Iterable["Segment"]:
        """Render the text as Segments.

        Args:
            console (Console): Console instance.
            end (Optional[str], optional): Optional end character.

        Returns:
            Iterable[Segment]: Result of render that may be written to the console.
        """
        _Segment = Segment
        text = self.plain
        if not self._spans:
            yield Segment(text)
            if end:
                yield _Segment(end)
            return
        get_style = partial(console.get_style, default=Style.null())

        enumerated_spans = list(enumerate(self._spans, 1))
        style_map = {index: get_style(span.style) for index, span in enumerated_spans}
        style_map[0] = get_style(self.style)

        spans = [
            (0, False, 0),
            *((span.start, False, index) for index, span in enumerated_spans),
            *((span.end, True, index) for index, span in enumerated_spans),
            (len(text), True, 0),
        ]
        spans.sort(key=itemgetter(0, 1))

        stack: List[int] = []
        stack_append = stack.append
        stack_pop = stack.remove

        style_cache: Dict[Tuple[Style, ...], Style] = {}
        style_cache_get = style_cache.get
        combine = Style.combine

        def get_current_style() -> Style:
            """Construct current style from stack."""
            styles = tuple(style_map[_style_id] for _style_id in sorted(stack))
            cached_style = style_cache_get(styles)
            if cached_style is not None:
                return cached_style
            current_style = combine(styles)
            style_cache[styles] = current_style
            return current_style

        for (offset, leaving, style_id), (next_offset, _, _) in zip(spans, spans[1:]):
            if leaving:
                stack_pop(style_id)
            else:
                stack_append(style_id)
            if next_offset > offset:
                yield _Segment(text[offset:next_offset], get_current_style())
        if end:
            yield _Segment(end)

    def join(self, lines: Iterable["Text"]) -> "Text":
        """Join text together with this instance as the separator.

        Args:
            lines (Iterable[Text]): An iterable of Text instances to join.

        Returns:
            Text: A new text instance containing join text.
        """

        new_text = self.blank_copy()

        def iter_text() -> Iterable["Text"]:
            if self.plain:
                for last, line in loop_last(lines):
                    yield line
                    if not last:
                        yield self
            else:
                yield from lines

        extend_text = new_text._text.extend
        append_span = new_text._spans.append
        extend_spans = new_text._spans.extend
        offset = 0
        _Span = Span

        for text in iter_text():
            extend_text(text._text)
            if text.style:
                append_span(_Span(offset, offset + len(text), text.style))
            extend_spans(
                _Span(offset + start, offset + end, style)
                for start, end, style in text._spans
            )
            offset += len(text)
        new_text._length = offset
        return new_text

    def expand_tabs(self, tab_size: Optional[int] = None) -> None:
        """Converts tabs to spaces.

        Args:
            tab_size (int, optional): Size of tabs. Defaults to 8.

        """
        if "\t" not in self.plain:
            return
        if tab_size is None:
            tab_size = self.tab_size
        if tab_size is None:
            tab_size = 8

        new_text: List[Text] = []
        append = new_text.append

        for line in self.split("\n", include_separator=True):
            if "\t" not in line.plain:
                append(line)
            else:
                cell_position = 0
                parts = line.split("\t", include_separator=True)
                for part in parts:
                    if part.plain.endswith("\t"):
                        part._text[-1] = part._text[-1][:-1] + " "
                        cell_position += part.cell_len
                        tab_remainder = cell_position % tab_size
                        if tab_remainder:
                            spaces = tab_size - tab_remainder
                            part.extend_style(spaces)
                            cell_position += spaces
                    else:
                        cell_position += part.cell_len
                    append(part)

        result = Text("").join(new_text)

        self._text = [result.plain]
        self._length = len(self.plain)
        self._spans[:] = result._spans

    def truncate(
        self,
        max_width: int,
        *,
        overflow: Optional["OverflowMethod"] = None,
        pad: bool = False,
    ) -> None:
        """Truncate text if it is longer that a given width.

        Args:
            max_width (int): Maximum number of characters in text.
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None, to use self.overflow.
            pad (bool, optional): Pad with spaces if the length is less than max_width. Defaults to False.
        """
        _overflow = overflow or self.overflow or DEFAULT_OVERFLOW
        if _overflow != "ignore":
            length = cell_len(self.plain)
            if length > max_width:
                if _overflow == "ellipsis":
                    self.plain = set_cell_size(self.plain, max_width - 1) + "…"
                else:
                    self.plain = set_cell_size(self.plain, max_width)
            if pad and length < max_width:
                spaces = max_width - length
                self._text = [f"{self.plain}{' ' * spaces}"]
                self._length = len(self.plain)

    def _trim_spans(self) -> None:
        """Remove or modify any spans that are over the end of the text."""
        max_offset = len(self.plain)
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]

    def pad(self, count: int, character: str = " ") -> None:
        """Pad left and right with a given number of characters.

        Args:
            count (int): Width of padding.
            character (str): The character to pad with. Must be a string of length 1.
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            pad_characters = character * count
            self.plain = f"{pad_characters}{self.plain}{pad_characters}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_left(self, count: int, character: str = " ") -> None:
        """Pad the left with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{character * count}{self.plain}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_right(self, count: int, character: str = " ") -> None:
        """Pad the right with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{self.plain}{character * count}"

    def align(self, align: AlignMethod, width: int, character: str = " ") -> None:
        """Align text to a given width.

        Args:
            align (AlignMethod): One of "left", "center", or "right".
            width (int): Desired width.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        self.truncate(width)
        excess_space = width - cell_len(self.plain)
        if excess_space:
            if align == "left":
                self.pad_right(excess_space, character)
            elif align == "center":
                left = excess_space // 2
                self.pad_left(left, character)
                self.pad_right(excess_space - left, character)
            else:
                self.pad_left(excess_space, character)

    def append(
        self, text: Union["Text", str], style: Optional[Union[str, "Style"]] = None
    ) -> "Text":
        """Add text with an optional style.

        Args:
            text (Union[Text, str]): A str or Text to append.
            style (str, optional): A style name. Defaults to None.

        Returns:
            Text: Returns self for chaining.
        """

        if not isinstance(text, (str, Text)):
            raise TypeError("Only str or Text can be appended to Text")

        if len(text):
            if isinstance(text, str):
                sanitized_text = strip_control_codes(text)
                self._text.append(sanitized_text)
                offset = len(self)
                text_length = len(sanitized_text)
                if style:
                    self._spans.append(Span(offset, offset + text_length, style))
                self._length += text_length
            elif isinstance(text, Text):
                _Span = Span
                if style is not None:
                    raise ValueError(
                        "style must not be set when appending Text instance"
                    )
                text_length = self._length
                if text.style:
                    self._spans.append(
                        _Span(text_length, text_length + len(text), text.style)
                    )
                self._text.append(text.plain)
                self._spans.extend(
                    _Span(start + text_length, end + text_length, style)
                    for start, end, style in text._spans.copy()
                )
                self._length += len(text)
        return self

    def append_text(self, text: "Text") -> "Text":
        """Append another Text instance. This method is more performant that Text.append, but
        only works for Text.

        Args:
            text (Text): The Text instance to append to this instance.

        Returns:
            Text: Returns self for chaining.
        """
        _Span = Span
        text_length = self._length
        if text.style:
            self._spans.append(_Span(text_length, text_length + len(text), text.style))
        self._text.append(text.plain)
        self._spans.extend(
            _Span(start + text_length, end + text_length, style)
            for start, end, style in text._spans.copy()
        )
        self._length += len(text)
        return self

    def append_tokens(
        self, tokens: Iterable[Tuple[str, Optional[StyleType]]]
    ) -> "Text":
        """Append iterable of str and style. Style may be a Style instance or a str style definition.

        Args:
            tokens (Iterable[Tuple[str, Optional[StyleType]]]): An iterable of tuples containing str content and style.

        Returns:
            Text: Returns self for chaining.
        """
        append_text = self._text.append
        append_span = self._spans.append
        _Span = Span
        offset = len(self)
        for content, style in tokens:
            content = strip_control_codes(content)
            append_text(content)
            if style:
                append_span(_Span(offset, offset + len(content), style))
            offset += len(content)
        self._length = offset
        return self

    def copy_styles(self, text: "Text") -> None:
        """Copy styles from another Text instance.

        Args:
            text (Text): A Text instance to copy styles from, must be the same length.
        """
        self._spans.extend(text._spans)

    def split(
        self,
        separator: str = "\n",
        *,
        include_separator: bool = False,
        allow_blank: bool = False,
    ) -> Lines:
        """Split rich text in to lines, preserving styles.

        Args:
            separator (str, optional): String to split on. Defaults to "\\\\n".
            include_separator (bool, optional): Include the separator in the lines. Defaults to False.
            allow_blank (bool, optional): Return a blank line if the text ends with a separator. Defaults to False.

        Returns:
            List[RichText]: A list of rich text, one per line of the original.
        """
        assert separator, "separator must not be empty"

        text = self.plain
        if separator not in text:
            return Lines([self.copy()])

        if include_separator:
            lines = self.divide(
                match.end() for match in re.finditer(re.escape(separator), text)
            )
        else:

            def flatten_spans() -> Iterable[int]:
                for match in re.finditer(re.escape(separator), text):
                    start, end = match.span()
                    yield start
                    yield end

            lines = Lines(
                line for line in self.divide(flatten_spans()) if line.plain != separator
            )

        if not allow_blank and text.endswith(separator):
            lines.pop()

        return lines

    def divide(self, offsets: Iterable[int]) -> Lines:
        """Divide text in to a number of lines at given offsets.

        Args:
            offsets (Iterable[int]): Offsets used to divide text.

        Returns:
            Lines: New RichText instances between offsets.
        """
        _offsets = list(offsets)

        if not _offsets:
            return Lines([self.copy()])

        text = self.plain
        text_length = len(text)
        divide_offsets = [0, *_offsets, text_length]
        line_ranges = list(zip(divide_offsets, divide_offsets[1:]))

        style = self.style
        justify = self.justify
        overflow = self.overflow
        _Text = Text
        new_lines = Lines(
            _Text(
                text[start:end],
                style=style,
                justify=justify,
                overflow=overflow,
            )
            for start, end in line_ranges
        )
        if not self._spans:
            return new_lines

        _line_appends = [line._spans.append for line in new_lines._lines]
        line_count = len(line_ranges)
        _Span = Span

        for span_start, span_end, style in self._spans:
            lower_bound = 0
            upper_bound = line_count
            start_line_no = (lower_bound + upper_bound) // 2

            while True:
                line_start, line_end = line_ranges[start_line_no]
                if span_start < line_start:
                    upper_bound = start_line_no - 1
                elif span_start > line_end:
                    lower_bound = start_line_no + 1
                else:
                    break
                start_line_no = (lower_bound + upper_bound) // 2

            if span_end < line_end:
                end_line_no = start_line_no
            else:
                end_line_no = lower_bound = start_line_no
                upper_bound = line_count

                while True:
                    line_start, line_end = line_ranges[end_line_no]
                    if span_end < line_start:
                        upper_bound = end_line_no - 1
                    elif span_end > line_end:
                        lower_bound = end_line_no + 1
                    else:
                        break
                    end_line_no = (lower_bound + upper_bound) // 2

            for line_no in range(start_line_no, end_line_no + 1):
                line_start, line_end = line_ranges[line_no]
                new_start = max(0, span_start - line_start)
                new_end = min(span_end - line_start, line_end - line_start)
                if new_end > new_start:
                    _line_appends[line_no](_Span(new_start, new_end, style))

        return new_lines

    def right_crop(self, amount: int = 1) -> None:
        """Remove a number of characters from the end of the text."""
        max_offset = len(self.plain) - amount
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]
        self._text = [self.plain[:-amount]]
        self._length -= amount

    def wrap(
        self,
        console: "Console",
        width: int,
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        tab_size: int = 8,
        no_wrap: Optional[bool] = None,
    ) -> Lines:
        """Word wrap the text.

        Args:
            console (Console): Console instance.
            width (int): Number of cells available per line.
            justify (str, optional): Justify method: "default", "left", "center", "full", "right". Defaults to "default".
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None.
            tab_size (int, optional): Default tab size. Defaults to 8.
            no_wrap (bool, optional): Disable wrapping, Defaults to False.

        Returns:
            Lines: Number of lines.
        """
        wrap_justify = justify or self.justify or DEFAULT_JUSTIFY
        wrap_overflow = overflow or self.overflow or DEFAULT_OVERFLOW

        no_wrap = pick_bool(no_wrap, self.no_wrap, False) or overflow == "ignore"

        lines = Lines()
        for line in self.split(allow_blank=True):
            if "\t" in line:
                line.expand_tabs(tab_size)
            if no_wrap:
                new_lines = Lines([line])
            else:
                offsets = divide_line(str(line), width, fold=wrap_overflow == "fold")
                new_lines = line.divide(offsets)
            for line in new_lines:
                line.rstrip_end(width)
            if wrap_justify:
                new_lines.justify(
                    console, width, justify=wrap_justify, overflow=wrap_overflow
                )
            for line in new_lines:
                line.truncate(width, overflow=wrap_overflow)
            lines.extend(new_lines)
        return lines

    def fit(self, width: int) -> Lines:
        """Fit the text in to given width by chopping in to lines.

        Args:
            width (int): Maximum characters in a line.

        Returns:
            Lines: Lines container.
        """
        lines: Lines = Lines()
        append = lines.append
        for line in self.split():
            line.set_length(width)
            append(line)
        return lines

    def detect_indentation(self) -> int:
        """Auto-detect indentation of code.

        Returns:
            int: Number of spaces used to indent code.
        """

        _indentations = {
            len(match.group(1))
            for match in re.finditer(r"^( *)(.*)$", self.plain, flags=re.MULTILINE)
        }

        try:
            indentation = (
                reduce(gcd, [indent for indent in _indentations if not indent % 2]) or 1
            )
        except TypeError:
            indentation = 1

        return indentation

    def with_indent_guides(
        self,
        indent_size: Optional[int] = None,
        *,
        character: str = "│",
        style: StyleType = "dim green",
    ) -> "Text":
        """Adds indent guide lines to text.

        Args:
            indent_size (Optional[int]): Size of indentation, or None to auto detect. Defaults to None.
            character (str, optional): Character to use for indentation. Defaults to "│".
            style (Union[Style, str], optional): Style of indent guides.

        Returns:
            Text: New text with indentation guides.
        """

        _indent_size = self.detect_indentation() if indent_size is None else indent_size

        text = self.copy()
        text.expand_tabs()
        indent_line = f"{character}{' ' * (_indent_size - 1)}"

        re_indent = re.compile(r"^( *)(.*)$")
        new_lines: List[Text] = []
        add_line = new_lines.append
        blank_lines = 0
        for line in text.split(allow_blank=True):
            match = re_indent.match(line.plain)
            if not match or not match.group(2):
                blank_lines += 1
                continue
            indent = match.group(1)
            full_indents, remaining_space = divmod(len(indent), _indent_size)
            new_indent = f"{indent_line * full_indents}{' ' * remaining_space}"
            line.plain = new_indent + line.plain[len(new_indent) :]
            line.stylize(style, 0, len(new_indent))
            if blank_lines:
                new_lines.extend([Text(new_indent, style=style)] * blank_lines)
                blank_lines = 0
            add_line(line)
        if blank_lines:
            new_lines.extend([Text("", style=style)] * blank_lines)

        new_text = text.blank_copy("\n").join(new_lines)
        return new_text


if __name__ == "__main__":  # pragma: no cover
    from rich.console import Console

    text = Text(
        """\nLorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n"""
    )
    text.highlight_words(["Lorem"], "bold")
    text.highlight_words(["ipsum"], "italic")

    console = Console()

    console.rule("justify='left'")
    console.print(text, style="red")
    console.print()

    console.rule("justify='center'")
    console.print(text, style="green", justify="center")
    console.print()

    console.rule("justify='right'")
    console.print(text, style="blue", justify="right")
    console.print()

    console.rule("justify='full'")
    console.print(text, style="magenta", justify="full")
    console.print()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\text.py ===
import re
from functools import partial, reduce
from math import gcd
from operator import itemgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Pattern,
    Tuple,
    Union,
)

from ._loop import loop_last
from ._pick import pick_bool
from ._wrap import divide_line
from .align import AlignMethod
from .cells import cell_len, set_cell_size
from .containers import Lines
from .control import strip_control_codes
from .emoji import EmojiVariant
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleType

if TYPE_CHECKING:  # pragma: no cover
    from .console import Console, ConsoleOptions, JustifyMethod, OverflowMethod

DEFAULT_JUSTIFY: "JustifyMethod" = "default"
DEFAULT_OVERFLOW: "OverflowMethod" = "fold"


_re_whitespace = re.compile(r"\s+$")

TextType = Union[str, "Text"]
"""A plain string or a :class:`Text` instance."""

GetStyleCallable = Callable[[str], Optional[StyleType]]


class Span(NamedTuple):
    """A marked up region in some text."""

    start: int
    """Span start index."""
    end: int
    """Span end index."""
    style: Union[str, Style]
    """Style associated with the span."""

    def __repr__(self) -> str:
        return f"Span({self.start}, {self.end}, {self.style!r})"

    def __bool__(self) -> bool:
        return self.end > self.start

    def split(self, offset: int) -> Tuple["Span", Optional["Span"]]:
        """Split a span in to 2 from a given offset."""

        if offset < self.start:
            return self, None
        if offset >= self.end:
            return self, None

        start, end, style = self
        span1 = Span(start, min(end, offset), style)
        span2 = Span(span1.end, end, style)
        return span1, span2

    def move(self, offset: int) -> "Span":
        """Move start and end by a given offset.

        Args:
            offset (int): Number of characters to add to start and end.

        Returns:
            TextSpan: A new TextSpan with adjusted position.
        """
        start, end, style = self
        return Span(start + offset, end + offset, style)

    def right_crop(self, offset: int) -> "Span":
        """Crop the span at the given offset.

        Args:
            offset (int): A value between start and end.

        Returns:
            Span: A new (possibly smaller) span.
        """
        start, end, style = self
        if offset >= end:
            return self
        return Span(start, min(offset, end), style)

    def extend(self, cells: int) -> "Span":
        """Extend the span by the given number of cells.

        Args:
            cells (int): Additional space to add to end of span.

        Returns:
            Span: A span.
        """
        if cells:
            start, end, style = self
            return Span(start, end + cells, style)
        else:
            return self


class Text(JupyterMixin):
    """Text with color / style.

    Args:
        text (str, optional): Default unstyled text. Defaults to "".
        style (Union[str, Style], optional): Base style for text. Defaults to "".
        justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
        overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
        no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
        end (str, optional): Character to end text with. Defaults to "\\\\n".
        tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        spans (List[Span], optional). A list of predefined style spans. Defaults to None.
    """

    __slots__ = [
        "_text",
        "style",
        "justify",
        "overflow",
        "no_wrap",
        "end",
        "tab_size",
        "_spans",
        "_length",
    ]

    def __init__(
        self,
        text: str = "",
        style: Union[str, Style] = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = None,
        spans: Optional[List[Span]] = None,
    ) -> None:
        sanitized_text = strip_control_codes(text)
        self._text = [sanitized_text]
        self.style = style
        self.justify: Optional["JustifyMethod"] = justify
        self.overflow: Optional["OverflowMethod"] = overflow
        self.no_wrap = no_wrap
        self.end = end
        self.tab_size = tab_size
        self._spans: List[Span] = spans or []
        self._length: int = len(sanitized_text)

    def __len__(self) -> int:
        return self._length

    def __bool__(self) -> bool:
        return bool(self._length)

    def __str__(self) -> str:
        return self.plain

    def __repr__(self) -> str:
        return f"<text {self.plain!r} {self._spans!r} {self.style!r}>"

    def __add__(self, other: Any) -> "Text":
        if isinstance(other, (str, Text)):
            result = self.copy()
            result.append(other)
            return result
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Text):
            return NotImplemented
        return self.plain == other.plain and self._spans == other._spans

    def __contains__(self, other: object) -> bool:
        if isinstance(other, str):
            return other in self.plain
        elif isinstance(other, Text):
            return other.plain in self.plain
        return False

    def __getitem__(self, slice: Union[int, slice]) -> "Text":
        def get_text_at(offset: int) -> "Text":
            _Span = Span
            text = Text(
                self.plain[offset],
                spans=[
                    _Span(0, 1, style)
                    for start, end, style in self._spans
                    if end > offset >= start
                ],
                end="",
            )
            return text

        if isinstance(slice, int):
            return get_text_at(slice)
        else:
            start, stop, step = slice.indices(len(self.plain))
            if step == 1:
                lines = self.divide([start, stop])
                return lines[1]
            else:
                # This would be a bit of work to implement efficiently
                # For now, its not required
                raise TypeError("slices with step!=1 are not supported")

    @property
    def cell_len(self) -> int:
        """Get the number of cells required to render this text."""
        return cell_len(self.plain)

    @property
    def markup(self) -> str:
        """Get console markup to render this Text.

        Returns:
            str: A string potentially creating markup tags.
        """
        from .markup import escape

        output: List[str] = []

        plain = self.plain
        markup_spans = [
            (0, False, self.style),
            *((span.start, False, span.style) for span in self._spans),
            *((span.end, True, span.style) for span in self._spans),
            (len(plain), True, self.style),
        ]
        markup_spans.sort(key=itemgetter(0, 1))
        position = 0
        append = output.append
        for offset, closing, style in markup_spans:
            if offset > position:
                append(escape(plain[position:offset]))
                position = offset
            if style:
                append(f"[/{style}]" if closing else f"[{style}]")
        markup = "".join(output)
        return markup

    @classmethod
    def from_markup(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        emoji: bool = True,
        emoji_variant: Optional[EmojiVariant] = None,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        end: str = "\n",
    ) -> "Text":
        """Create Text instance from markup.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            emoji (bool, optional): Also render emoji code. Defaults to True.
            emoji_variant (str, optional): Optional emoji variant, either "text" or "emoji". Defaults to None.
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".

        Returns:
            Text: A Text instance with markup rendered.
        """
        from .markup import render

        rendered_text = render(text, style, emoji=emoji, emoji_variant=emoji_variant)
        rendered_text.justify = justify
        rendered_text.overflow = overflow
        rendered_text.end = end
        return rendered_text

    @classmethod
    def from_ansi(
        cls,
        text: str,
        *,
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: Optional[int] = 8,
    ) -> "Text":
        """Create a Text object from a string containing ANSI escape codes.

        Args:
            text (str): A string containing escape codes.
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
        """
        from .ansi import AnsiDecoder

        joiner = Text(
            "\n",
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
            style=style,
        )
        decoder = AnsiDecoder()
        result = joiner.join(line for line in decoder.decode(text))
        return result

    @classmethod
    def styled(
        cls,
        text: str,
        style: StyleType = "",
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
    ) -> "Text":
        """Construct a Text instance with a pre-applied styled. A style applied in this way won't be used
        to pad the text when it is justified.

        Args:
            text (str): A string containing console markup.
            style (Union[str, Style]): Style to apply to the text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.

        Returns:
            Text: A text instance with a style applied to the entire string.
        """
        styled_text = cls(text, justify=justify, overflow=overflow)
        styled_text.stylize(style)
        return styled_text

    @classmethod
    def assemble(
        cls,
        *parts: Union[str, "Text", Tuple[str, StyleType]],
        style: Union[str, Style] = "",
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        no_wrap: Optional[bool] = None,
        end: str = "\n",
        tab_size: int = 8,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "Text":
        """Construct a text instance by combining a sequence of strings with optional styles.
        The positional arguments should be either strings, or a tuple of string + style.

        Args:
            style (Union[str, Style], optional): Base style for text. Defaults to "".
            justify (str, optional): Justify method: "left", "center", "full", "right". Defaults to None.
            overflow (str, optional): Overflow method: "crop", "fold", "ellipsis". Defaults to None.
            no_wrap (bool, optional): Disable text wrapping, or None for default. Defaults to None.
            end (str, optional): Character to end text with. Defaults to "\\\\n".
            tab_size (int): Number of spaces per tab, or ``None`` to use ``console.tab_size``. Defaults to None.
            meta (Dict[str, Any], optional). Meta data to apply to text, or None for no meta data. Default to None

        Returns:
            Text: A new text instance.
        """
        text = cls(
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            end=end,
            tab_size=tab_size,
        )
        append = text.append
        _Text = Text
        for part in parts:
            if isinstance(part, (_Text, str)):
                append(part)
            else:
                append(*part)
        if meta:
            text.apply_meta(meta)
        return text

    @property
    def plain(self) -> str:
        """Get the text as a single string."""
        if len(self._text) != 1:
            self._text[:] = ["".join(self._text)]
        return self._text[0]

    @plain.setter
    def plain(self, new_text: str) -> None:
        """Set the text to a new value."""
        if new_text != self.plain:
            sanitized_text = strip_control_codes(new_text)
            self._text[:] = [sanitized_text]
            old_length = self._length
            self._length = len(sanitized_text)
            if old_length > self._length:
                self._trim_spans()

    @property
    def spans(self) -> List[Span]:
        """Get a reference to the internal list of spans."""
        return self._spans

    @spans.setter
    def spans(self, spans: List[Span]) -> None:
        """Set spans."""
        self._spans = spans[:]

    def blank_copy(self, plain: str = "") -> "Text":
        """Return a new Text instance with copied metadata (but not the string or spans)."""
        copy_self = Text(
            plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        return copy_self

    def copy(self) -> "Text":
        """Return a copy of this instance."""
        copy_self = Text(
            self.plain,
            style=self.style,
            justify=self.justify,
            overflow=self.overflow,
            no_wrap=self.no_wrap,
            end=self.end,
            tab_size=self.tab_size,
        )
        copy_self._spans[:] = self._spans
        return copy_self

    def stylize(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.append(Span(start, min(length, end), style))

    def stylize_before(
        self,
        style: Union[str, Style],
        start: int = 0,
        end: Optional[int] = None,
    ) -> None:
        """Apply a style to the text, or a portion of the text. Styles will be applied before other styles already present.

        Args:
            style (Union[str, Style]): Style instance or style definition to apply.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.
        """
        if style:
            length = len(self)
            if start < 0:
                start = length + start
            if end is None:
                end = length
            if end < 0:
                end = length + end
            if start >= length or end <= start:
                # Span not in text or not valid
                return
            self._spans.insert(0, Span(start, min(length, end), style))

    def apply_meta(
        self, meta: Dict[str, Any], start: int = 0, end: Optional[int] = None
    ) -> None:
        """Apply metadata to the text, or a portion of the text.

        Args:
            meta (Dict[str, Any]): A dict of meta information.
            start (int): Start offset (negative indexing is supported). Defaults to 0.
            end (Optional[int], optional): End offset (negative indexing is supported), or None for end of text. Defaults to None.

        """
        style = Style.from_meta(meta)
        self.stylize(style, start=start, end=end)

    def on(self, meta: Optional[Dict[str, Any]] = None, **handlers: Any) -> "Text":
        """Apply event handlers (used by Textual project).

        Example:
            >>> from rich.text import Text
            >>> text = Text("hello world")
            >>> text.on(click="view.toggle('world')")

        Args:
            meta (Dict[str, Any]): Mapping of meta information.
            **handlers: Keyword args are prefixed with "@" to defined handlers.

        Returns:
            Text: Self is returned to method may be chained.
        """
        meta = {} if meta is None else meta
        meta.update({f"@{key}": value for key, value in handlers.items()})
        self.stylize(Style.from_meta(meta))
        return self

    def remove_suffix(self, suffix: str) -> None:
        """Remove a suffix if it exists.

        Args:
            suffix (str): Suffix to remove.
        """
        if self.plain.endswith(suffix):
            self.right_crop(len(suffix))

    def get_style_at_offset(self, console: "Console", offset: int) -> Style:
        """Get the style of a character at give offset.

        Args:
            console (~Console): Console where text will be rendered.
            offset (int): Offset in to text (negative indexing supported)

        Returns:
            Style: A Style instance.
        """
        # TODO: This is a little inefficient, it is only used by full justify
        if offset < 0:
            offset = len(self) + offset
        get_style = console.get_style
        style = get_style(self.style).copy()
        for start, end, span_style in self._spans:
            if end > offset >= start:
                style += get_style(span_style, default="")
        return style

    def extend_style(self, spaces: int) -> None:
        """Extend the Text given number of spaces where the spaces have the same style as the last character.

        Args:
            spaces (int): Number of spaces to add to the Text.
        """
        if spaces <= 0:
            return
        spans = self.spans
        new_spaces = " " * spaces
        if spans:
            end_offset = len(self)
            self._spans[:] = [
                span.extend(spaces) if span.end >= end_offset else span
                for span in spans
            ]
            self._text.append(new_spaces)
            self._length += spaces
        else:
            self.plain += new_spaces

    def highlight_regex(
        self,
        re_highlight: Union[Pattern[str], str],
        style: Optional[Union[GetStyleCallable, StyleType]] = None,
        *,
        style_prefix: str = "",
    ) -> int:
        """Highlight text with a regular expression, where group names are
        translated to styles.

        Args:
            re_highlight (Union[re.Pattern, str]): A regular expression object or string.
            style (Union[GetStyleCallable, StyleType]): Optional style to apply to whole match, or a callable
                which accepts the matched text and returns a style. Defaults to None.
            style_prefix (str, optional): Optional prefix to add to style group names.

        Returns:
            int: Number of regex matches
        """
        count = 0
        append_span = self._spans.append
        _Span = Span
        plain = self.plain
        if isinstance(re_highlight, str):
            re_highlight = re.compile(re_highlight)
        for match in re_highlight.finditer(plain):
            get_span = match.span
            if style:
                start, end = get_span()
                match_style = style(plain[start:end]) if callable(style) else style
                if match_style is not None and end > start:
                    append_span(_Span(start, end, match_style))

            count += 1
            for name in match.groupdict().keys():
                start, end = get_span(name)
                if start != -1 and end > start:
                    append_span(_Span(start, end, f"{style_prefix}{name}"))
        return count

    def highlight_words(
        self,
        words: Iterable[str],
        style: Union[str, Style],
        *,
        case_sensitive: bool = True,
    ) -> int:
        """Highlight words with a style.

        Args:
            words (Iterable[str]): Words to highlight.
            style (Union[str, Style]): Style to apply.
            case_sensitive (bool, optional): Enable case sensitive matching. Defaults to True.

        Returns:
            int: Number of words highlighted.
        """
        re_words = "|".join(re.escape(word) for word in words)
        add_span = self._spans.append
        count = 0
        _Span = Span
        for match in re.finditer(
            re_words, self.plain, flags=0 if case_sensitive else re.IGNORECASE
        ):
            start, end = match.span(0)
            add_span(_Span(start, end, style))
            count += 1
        return count

    def rstrip(self) -> None:
        """Strip whitespace from end of text."""
        self.plain = self.plain.rstrip()

    def rstrip_end(self, size: int) -> None:
        """Remove whitespace beyond a certain width at the end of the text.

        Args:
            size (int): The desired size of the text.
        """
        text_length = len(self)
        if text_length > size:
            excess = text_length - size
            whitespace_match = _re_whitespace.search(self.plain)
            if whitespace_match is not None:
                whitespace_count = len(whitespace_match.group(0))
                self.right_crop(min(whitespace_count, excess))

    def set_length(self, new_length: int) -> None:
        """Set new length of the text, clipping or padding is required."""
        length = len(self)
        if length != new_length:
            if length < new_length:
                self.pad_right(new_length - length)
            else:
                self.right_crop(length - new_length)

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Iterable[Segment]:
        tab_size: int = console.tab_size if self.tab_size is None else self.tab_size
        justify = self.justify or options.justify or DEFAULT_JUSTIFY

        overflow = self.overflow or options.overflow or DEFAULT_OVERFLOW

        lines = self.wrap(
            console,
            options.max_width,
            justify=justify,
            overflow=overflow,
            tab_size=tab_size or 8,
            no_wrap=pick_bool(self.no_wrap, options.no_wrap, False),
        )
        all_lines = Text("\n").join(lines)
        yield from all_lines.render(console, end=self.end)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        text = self.plain
        lines = text.splitlines()
        max_text_width = max(cell_len(line) for line in lines) if lines else 0
        words = text.split()
        min_text_width = (
            max(cell_len(word) for word in words) if words else max_text_width
        )
        return Measurement(min_text_width, max_text_width)

    def render(self, console: "Console", end: str = "") -> Iterable["Segment"]:
        """Render the text as Segments.

        Args:
            console (Console): Console instance.
            end (Optional[str], optional): Optional end character.

        Returns:
            Iterable[Segment]: Result of render that may be written to the console.
        """
        _Segment = Segment
        text = self.plain
        if not self._spans:
            yield Segment(text)
            if end:
                yield _Segment(end)
            return
        get_style = partial(console.get_style, default=Style.null())

        enumerated_spans = list(enumerate(self._spans, 1))
        style_map = {index: get_style(span.style) for index, span in enumerated_spans}
        style_map[0] = get_style(self.style)

        spans = [
            (0, False, 0),
            *((span.start, False, index) for index, span in enumerated_spans),
            *((span.end, True, index) for index, span in enumerated_spans),
            (len(text), True, 0),
        ]
        spans.sort(key=itemgetter(0, 1))

        stack: List[int] = []
        stack_append = stack.append
        stack_pop = stack.remove

        style_cache: Dict[Tuple[Style, ...], Style] = {}
        style_cache_get = style_cache.get
        combine = Style.combine

        def get_current_style() -> Style:
            """Construct current style from stack."""
            styles = tuple(style_map[_style_id] for _style_id in sorted(stack))
            cached_style = style_cache_get(styles)
            if cached_style is not None:
                return cached_style
            current_style = combine(styles)
            style_cache[styles] = current_style
            return current_style

        for (offset, leaving, style_id), (next_offset, _, _) in zip(spans, spans[1:]):
            if leaving:
                stack_pop(style_id)
            else:
                stack_append(style_id)
            if next_offset > offset:
                yield _Segment(text[offset:next_offset], get_current_style())
        if end:
            yield _Segment(end)

    def join(self, lines: Iterable["Text"]) -> "Text":
        """Join text together with this instance as the separator.

        Args:
            lines (Iterable[Text]): An iterable of Text instances to join.

        Returns:
            Text: A new text instance containing join text.
        """

        new_text = self.blank_copy()

        def iter_text() -> Iterable["Text"]:
            if self.plain:
                for last, line in loop_last(lines):
                    yield line
                    if not last:
                        yield self
            else:
                yield from lines

        extend_text = new_text._text.extend
        append_span = new_text._spans.append
        extend_spans = new_text._spans.extend
        offset = 0
        _Span = Span

        for text in iter_text():
            extend_text(text._text)
            if text.style:
                append_span(_Span(offset, offset + len(text), text.style))
            extend_spans(
                _Span(offset + start, offset + end, style)
                for start, end, style in text._spans
            )
            offset += len(text)
        new_text._length = offset
        return new_text

    def expand_tabs(self, tab_size: Optional[int] = None) -> None:
        """Converts tabs to spaces.

        Args:
            tab_size (int, optional): Size of tabs. Defaults to 8.

        """
        if "\t" not in self.plain:
            return
        if tab_size is None:
            tab_size = self.tab_size
        if tab_size is None:
            tab_size = 8

        new_text: List[Text] = []
        append = new_text.append

        for line in self.split("\n", include_separator=True):
            if "\t" not in line.plain:
                append(line)
            else:
                cell_position = 0
                parts = line.split("\t", include_separator=True)
                for part in parts:
                    if part.plain.endswith("\t"):
                        part._text[-1] = part._text[-1][:-1] + " "
                        cell_position += part.cell_len
                        tab_remainder = cell_position % tab_size
                        if tab_remainder:
                            spaces = tab_size - tab_remainder
                            part.extend_style(spaces)
                            cell_position += spaces
                    else:
                        cell_position += part.cell_len
                    append(part)

        result = Text("").join(new_text)

        self._text = [result.plain]
        self._length = len(self.plain)
        self._spans[:] = result._spans

    def truncate(
        self,
        max_width: int,
        *,
        overflow: Optional["OverflowMethod"] = None,
        pad: bool = False,
    ) -> None:
        """Truncate text if it is longer that a given width.

        Args:
            max_width (int): Maximum number of characters in text.
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None, to use self.overflow.
            pad (bool, optional): Pad with spaces if the length is less than max_width. Defaults to False.
        """
        _overflow = overflow or self.overflow or DEFAULT_OVERFLOW
        if _overflow != "ignore":
            length = cell_len(self.plain)
            if length > max_width:
                if _overflow == "ellipsis":
                    self.plain = set_cell_size(self.plain, max_width - 1) + "…"
                else:
                    self.plain = set_cell_size(self.plain, max_width)
            if pad and length < max_width:
                spaces = max_width - length
                self._text = [f"{self.plain}{' ' * spaces}"]
                self._length = len(self.plain)

    def _trim_spans(self) -> None:
        """Remove or modify any spans that are over the end of the text."""
        max_offset = len(self.plain)
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]

    def pad(self, count: int, character: str = " ") -> None:
        """Pad left and right with a given number of characters.

        Args:
            count (int): Width of padding.
            character (str): The character to pad with. Must be a string of length 1.
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            pad_characters = character * count
            self.plain = f"{pad_characters}{self.plain}{pad_characters}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_left(self, count: int, character: str = " ") -> None:
        """Pad the left with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{character * count}{self.plain}"
            _Span = Span
            self._spans[:] = [
                _Span(start + count, end + count, style)
                for start, end, style in self._spans
            ]

    def pad_right(self, count: int, character: str = " ") -> None:
        """Pad the right with a given character.

        Args:
            count (int): Number of characters to pad.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        assert len(character) == 1, "Character must be a string of length 1"
        if count:
            self.plain = f"{self.plain}{character * count}"

    def align(self, align: AlignMethod, width: int, character: str = " ") -> None:
        """Align text to a given width.

        Args:
            align (AlignMethod): One of "left", "center", or "right".
            width (int): Desired width.
            character (str, optional): Character to pad with. Defaults to " ".
        """
        self.truncate(width)
        excess_space = width - cell_len(self.plain)
        if excess_space:
            if align == "left":
                self.pad_right(excess_space, character)
            elif align == "center":
                left = excess_space // 2
                self.pad_left(left, character)
                self.pad_right(excess_space - left, character)
            else:
                self.pad_left(excess_space, character)

    def append(
        self, text: Union["Text", str], style: Optional[Union[str, "Style"]] = None
    ) -> "Text":
        """Add text with an optional style.

        Args:
            text (Union[Text, str]): A str or Text to append.
            style (str, optional): A style name. Defaults to None.

        Returns:
            Text: Returns self for chaining.
        """

        if not isinstance(text, (str, Text)):
            raise TypeError("Only str or Text can be appended to Text")

        if len(text):
            if isinstance(text, str):
                sanitized_text = strip_control_codes(text)
                self._text.append(sanitized_text)
                offset = len(self)
                text_length = len(sanitized_text)
                if style:
                    self._spans.append(Span(offset, offset + text_length, style))
                self._length += text_length
            elif isinstance(text, Text):
                _Span = Span
                if style is not None:
                    raise ValueError(
                        "style must not be set when appending Text instance"
                    )
                text_length = self._length
                if text.style:
                    self._spans.append(
                        _Span(text_length, text_length + len(text), text.style)
                    )
                self._text.append(text.plain)
                self._spans.extend(
                    _Span(start + text_length, end + text_length, style)
                    for start, end, style in text._spans.copy()
                )
                self._length += len(text)
        return self

    def append_text(self, text: "Text") -> "Text":
        """Append another Text instance. This method is more performant that Text.append, but
        only works for Text.

        Args:
            text (Text): The Text instance to append to this instance.

        Returns:
            Text: Returns self for chaining.
        """
        _Span = Span
        text_length = self._length
        if text.style:
            self._spans.append(_Span(text_length, text_length + len(text), text.style))
        self._text.append(text.plain)
        self._spans.extend(
            _Span(start + text_length, end + text_length, style)
            for start, end, style in text._spans.copy()
        )
        self._length += len(text)
        return self

    def append_tokens(
        self, tokens: Iterable[Tuple[str, Optional[StyleType]]]
    ) -> "Text":
        """Append iterable of str and style. Style may be a Style instance or a str style definition.

        Args:
            tokens (Iterable[Tuple[str, Optional[StyleType]]]): An iterable of tuples containing str content and style.

        Returns:
            Text: Returns self for chaining.
        """
        append_text = self._text.append
        append_span = self._spans.append
        _Span = Span
        offset = len(self)
        for content, style in tokens:
            content = strip_control_codes(content)
            append_text(content)
            if style:
                append_span(_Span(offset, offset + len(content), style))
            offset += len(content)
        self._length = offset
        return self

    def copy_styles(self, text: "Text") -> None:
        """Copy styles from another Text instance.

        Args:
            text (Text): A Text instance to copy styles from, must be the same length.
        """
        self._spans.extend(text._spans)

    def split(
        self,
        separator: str = "\n",
        *,
        include_separator: bool = False,
        allow_blank: bool = False,
    ) -> Lines:
        """Split rich text in to lines, preserving styles.

        Args:
            separator (str, optional): String to split on. Defaults to "\\\\n".
            include_separator (bool, optional): Include the separator in the lines. Defaults to False.
            allow_blank (bool, optional): Return a blank line if the text ends with a separator. Defaults to False.

        Returns:
            List[RichText]: A list of rich text, one per line of the original.
        """
        assert separator, "separator must not be empty"

        text = self.plain
        if separator not in text:
            return Lines([self.copy()])

        if include_separator:
            lines = self.divide(
                match.end() for match in re.finditer(re.escape(separator), text)
            )
        else:

            def flatten_spans() -> Iterable[int]:
                for match in re.finditer(re.escape(separator), text):
                    start, end = match.span()
                    yield start
                    yield end

            lines = Lines(
                line for line in self.divide(flatten_spans()) if line.plain != separator
            )

        if not allow_blank and text.endswith(separator):
            lines.pop()

        return lines

    def divide(self, offsets: Iterable[int]) -> Lines:
        """Divide text in to a number of lines at given offsets.

        Args:
            offsets (Iterable[int]): Offsets used to divide text.

        Returns:
            Lines: New RichText instances between offsets.
        """
        _offsets = list(offsets)

        if not _offsets:
            return Lines([self.copy()])

        text = self.plain
        text_length = len(text)
        divide_offsets = [0, *_offsets, text_length]
        line_ranges = list(zip(divide_offsets, divide_offsets[1:]))

        style = self.style
        justify = self.justify
        overflow = self.overflow
        _Text = Text
        new_lines = Lines(
            _Text(
                text[start:end],
                style=style,
                justify=justify,
                overflow=overflow,
            )
            for start, end in line_ranges
        )
        if not self._spans:
            return new_lines

        _line_appends = [line._spans.append for line in new_lines._lines]
        line_count = len(line_ranges)
        _Span = Span

        for span_start, span_end, style in self._spans:
            lower_bound = 0
            upper_bound = line_count
            start_line_no = (lower_bound + upper_bound) // 2

            while True:
                line_start, line_end = line_ranges[start_line_no]
                if span_start < line_start:
                    upper_bound = start_line_no - 1
                elif span_start > line_end:
                    lower_bound = start_line_no + 1
                else:
                    break
                start_line_no = (lower_bound + upper_bound) // 2

            if span_end < line_end:
                end_line_no = start_line_no
            else:
                end_line_no = lower_bound = start_line_no
                upper_bound = line_count

                while True:
                    line_start, line_end = line_ranges[end_line_no]
                    if span_end < line_start:
                        upper_bound = end_line_no - 1
                    elif span_end > line_end:
                        lower_bound = end_line_no + 1
                    else:
                        break
                    end_line_no = (lower_bound + upper_bound) // 2

            for line_no in range(start_line_no, end_line_no + 1):
                line_start, line_end = line_ranges[line_no]
                new_start = max(0, span_start - line_start)
                new_end = min(span_end - line_start, line_end - line_start)
                if new_end > new_start:
                    _line_appends[line_no](_Span(new_start, new_end, style))

        return new_lines

    def right_crop(self, amount: int = 1) -> None:
        """Remove a number of characters from the end of the text."""
        max_offset = len(self.plain) - amount
        _Span = Span
        self._spans[:] = [
            (
                span
                if span.end < max_offset
                else _Span(span.start, min(max_offset, span.end), span.style)
            )
            for span in self._spans
            if span.start < max_offset
        ]
        self._text = [self.plain[:-amount]]
        self._length -= amount

    def wrap(
        self,
        console: "Console",
        width: int,
        *,
        justify: Optional["JustifyMethod"] = None,
        overflow: Optional["OverflowMethod"] = None,
        tab_size: int = 8,
        no_wrap: Optional[bool] = None,
    ) -> Lines:
        """Word wrap the text.

        Args:
            console (Console): Console instance.
            width (int): Number of cells available per line.
            justify (str, optional): Justify method: "default", "left", "center", "full", "right". Defaults to "default".
            overflow (str, optional): Overflow method: "crop", "fold", or "ellipsis". Defaults to None.
            tab_size (int, optional): Default tab size. Defaults to 8.
            no_wrap (bool, optional): Disable wrapping, Defaults to False.

        Returns:
            Lines: Number of lines.
        """
        wrap_justify = justify or self.justify or DEFAULT_JUSTIFY
        wrap_overflow = overflow or self.overflow or DEFAULT_OVERFLOW

        no_wrap = pick_bool(no_wrap, self.no_wrap, False) or overflow == "ignore"

        lines = Lines()
        for line in self.split(allow_blank=True):
            if "\t" in line:
                line.expand_tabs(tab_size)
            if no_wrap:
                new_lines = Lines([line])
            else:
                offsets = divide_line(str(line), width, fold=wrap_overflow == "fold")
                new_lines = line.divide(offsets)
            for line in new_lines:
                line.rstrip_end(width)
            if wrap_justify:
                new_lines.justify(
                    console, width, justify=wrap_justify, overflow=wrap_overflow
                )
            for line in new_lines:
                line.truncate(width, overflow=wrap_overflow)
            lines.extend(new_lines)
        return lines

    def fit(self, width: int) -> Lines:
        """Fit the text in to given width by chopping in to lines.

        Args:
            width (int): Maximum characters in a line.

        Returns:
            Lines: Lines container.
        """
        lines: Lines = Lines()
        append = lines.append
        for line in self.split():
            line.set_length(width)
            append(line)
        return lines

    def detect_indentation(self) -> int:
        """Auto-detect indentation of code.

        Returns:
            int: Number of spaces used to indent code.
        """

        _indentations = {
            len(match.group(1))
            for match in re.finditer(r"^( *)(.*)$", self.plain, flags=re.MULTILINE)
        }

        try:
            indentation = (
                reduce(gcd, [indent for indent in _indentations if not indent % 2]) or 1
            )
        except TypeError:
            indentation = 1

        return indentation

    def with_indent_guides(
        self,
        indent_size: Optional[int] = None,
        *,
        character: str = "│",
        style: StyleType = "dim green",
    ) -> "Text":
        """Adds indent guide lines to text.

        Args:
            indent_size (Optional[int]): Size of indentation, or None to auto detect. Defaults to None.
            character (str, optional): Character to use for indentation. Defaults to "│".
            style (Union[Style, str], optional): Style of indent guides.

        Returns:
            Text: New text with indentation guides.
        """

        _indent_size = self.detect_indentation() if indent_size is None else indent_size

        text = self.copy()
        text.expand_tabs()
        indent_line = f"{character}{' ' * (_indent_size - 1)}"

        re_indent = re.compile(r"^( *)(.*)$")
        new_lines: List[Text] = []
        add_line = new_lines.append
        blank_lines = 0
        for line in text.split(allow_blank=True):
            match = re_indent.match(line.plain)
            if not match or not match.group(2):
                blank_lines += 1
                continue
            indent = match.group(1)
            full_indents, remaining_space = divmod(len(indent), _indent_size)
            new_indent = f"{indent_line * full_indents}{' ' * remaining_space}"
            line.plain = new_indent + line.plain[len(new_indent) :]
            line.stylize(style, 0, len(new_indent))
            if blank_lines:
                new_lines.extend([Text(new_indent, style=style)] * blank_lines)
                blank_lines = 0
            add_line(line)
        if blank_lines:
            new_lines.extend([Text("", style=style)] * blank_lines)

        new_text = text.blank_copy("\n").join(new_lines)
        return new_text


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console

    text = Text(
        """\nLorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.\n"""
    )
    text.highlight_words(["Lorem"], "bold")
    text.highlight_words(["ipsum"], "italic")

    console = Console()

    console.rule("justify='left'")
    console.print(text, style="red")
    console.print()

    console.rule("justify='center'")
    console.print(text, style="green", justify="center")
    console.print()

    console.rule("justify='right'")
    console.print(text, style="blue", justify="right")
    console.print()

    console.rule("justify='full'")
    console.print(text, style="magenta", justify="full")
    console.print()

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\aline.py ===
# Natural Language Toolkit: ALINE
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Greg Kondrak <gkondrak@ualberta.ca>
#         Geoff Bacon <bacon@berkeley.edu> (Python port)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
ALINE
https://webdocs.cs.ualberta.ca/~kondrak/
Copyright 2002 by Grzegorz Kondrak.

ALINE is an algorithm for aligning phonetic sequences, described in [1].
This module is a port of Kondrak's (2002) ALINE. It provides functions for
phonetic sequence alignment and similarity analysis. These are useful in
historical linguistics, sociolinguistics and synchronic phonology.

ALINE has parameters that can be tuned for desired output. These parameters are:
- C_skip, C_sub, C_exp, C_vwl
- Salience weights
- Segmental features

In this implementation, some parameters have been changed from their default
values as described in [1], in order to replicate published results. All changes
are noted in comments.

Example usage
-------------

# Get optimal alignment of two phonetic sequences

>>> align('θin', 'tenwis') # doctest: +SKIP
[[('θ', 't'), ('i', 'e'), ('n', 'n'), ('-', 'w'), ('-', 'i'), ('-', 's')]]

[1] G. Kondrak. Algorithms for Language Reconstruction. PhD dissertation,
University of Toronto.
"""

try:
    import numpy as np
except ImportError:
    np = None

# === Constants ===

inf = float("inf")

# Default values for maximum similarity scores (Kondrak 2002: 54)
C_skip = -10  # Indels
C_sub = 35  # Substitutions
C_exp = 45  # Expansions/compressions
C_vwl = 5  # Vowel/consonant relative weight (decreased from 10)

consonants = [
    "B",
    "N",
    "R",
    "b",
    "c",
    "d",
    "f",
    "g",
    "h",
    "j",
    "k",
    "l",
    "m",
    "n",
    "p",
    "q",
    "r",
    "s",
    "t",
    "v",
    "x",
    "z",
    "ç",
    "ð",
    "ħ",
    "ŋ",
    "ɖ",
    "ɟ",
    "ɢ",
    "ɣ",
    "ɦ",
    "ɬ",
    "ɮ",
    "ɰ",
    "ɱ",
    "ɲ",
    "ɳ",
    "ɴ",
    "ɸ",
    "ɹ",
    "ɻ",
    "ɽ",
    "ɾ",
    "ʀ",
    "ʁ",
    "ʂ",
    "ʃ",
    "ʈ",
    "ʋ",
    "ʐ ",
    "ʒ",
    "ʔ",
    "ʕ",
    "ʙ",
    "ʝ",
    "β",
    "θ",
    "χ",
    "ʐ",
    "w",
]

# Relevant features for comparing consonants and vowels
R_c = [
    "aspirated",
    "lateral",
    "manner",
    "nasal",
    "place",
    "retroflex",
    "syllabic",
    "voice",
]
# 'high' taken out of R_v because same as manner
R_v = [
    "back",
    "lateral",
    "long",
    "manner",
    "nasal",
    "place",
    "retroflex",
    "round",
    "syllabic",
    "voice",
]

# Flattened feature matrix (Kondrak 2002: 56)
similarity_matrix = {
    # place
    "bilabial": 1.0,
    "labiodental": 0.95,
    "dental": 0.9,
    "alveolar": 0.85,
    "retroflex": 0.8,
    "palato-alveolar": 0.75,
    "palatal": 0.7,
    "velar": 0.6,
    "uvular": 0.5,
    "pharyngeal": 0.3,
    "glottal": 0.1,
    "labiovelar": 1.0,
    "vowel": -1.0,  # added 'vowel'
    # manner
    "stop": 1.0,
    "affricate": 0.9,
    "fricative": 0.85,  # increased fricative from 0.8
    "trill": 0.7,
    "tap": 0.65,
    "approximant": 0.6,
    "high vowel": 0.4,
    "mid vowel": 0.2,
    "low vowel": 0.0,
    "vowel2": 0.5,  # added vowel
    # high
    "high": 1.0,
    "mid": 0.5,
    "low": 0.0,
    # back
    "front": 1.0,
    "central": 0.5,
    "back": 0.0,
    # binary features
    "plus": 1.0,
    "minus": 0.0,
}

# Relative weights of phonetic features (Kondrak 2002: 55)
salience = {
    "syllabic": 5,
    "place": 40,
    "manner": 50,
    "voice": 5,  # decreased from 10
    "nasal": 20,  # increased from 10
    "retroflex": 10,
    "lateral": 10,
    "aspirated": 5,
    "long": 0,  # decreased from 1
    "high": 3,  # decreased from 5
    "back": 2,  # decreased from 5
    "round": 2,  # decreased from 5
}

# (Kondrak 2002: 59-60)
feature_matrix = {
    # Consonants
    "p": {
        "place": "bilabial",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "b": {
        "place": "bilabial",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "t": {
        "place": "alveolar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "d": {
        "place": "alveolar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʈ": {
        "place": "retroflex",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɖ": {
        "place": "retroflex",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "c": {
        "place": "palatal",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɟ": {
        "place": "palatal",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "k": {
        "place": "velar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "g": {
        "place": "velar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "q": {
        "place": "uvular",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɢ": {
        "place": "uvular",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʔ": {
        "place": "glottal",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "m": {
        "place": "bilabial",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɱ": {
        "place": "labiodental",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "n": {
        "place": "alveolar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɳ": {
        "place": "retroflex",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɲ": {
        "place": "palatal",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ŋ": {
        "place": "velar",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɴ": {
        "place": "uvular",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "N": {
        "place": "uvular",
        "manner": "stop",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "plus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʙ": {
        "place": "bilabial",
        "manner": "trill",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "B": {
        "place": "bilabial",
        "manner": "trill",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "r": {
        "place": "alveolar",
        "manner": "trill",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʀ": {
        "place": "uvular",
        "manner": "trill",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "R": {
        "place": "uvular",
        "manner": "trill",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɾ": {
        "place": "alveolar",
        "manner": "tap",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɽ": {
        "place": "retroflex",
        "manner": "tap",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɸ": {
        "place": "bilabial",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "β": {
        "place": "bilabial",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "f": {
        "place": "labiodental",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "v": {
        "place": "labiodental",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "θ": {
        "place": "dental",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ð": {
        "place": "dental",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "s": {
        "place": "alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "z": {
        "place": "alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʃ": {
        "place": "palato-alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʒ": {
        "place": "palato-alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʂ": {
        "place": "retroflex",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʐ": {
        "place": "retroflex",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ç": {
        "place": "palatal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʝ": {
        "place": "palatal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "x": {
        "place": "velar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɣ": {
        "place": "velar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "χ": {
        "place": "uvular",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʁ": {
        "place": "uvular",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ħ": {
        "place": "pharyngeal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ʕ": {
        "place": "pharyngeal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "h": {
        "place": "glottal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɦ": {
        "place": "glottal",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɬ": {
        "place": "alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "minus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "plus",
        "aspirated": "minus",
    },
    "ɮ": {
        "place": "alveolar",
        "manner": "fricative",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "plus",
        "aspirated": "minus",
    },
    "ʋ": {
        "place": "labiodental",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɹ": {
        "place": "alveolar",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɻ": {
        "place": "retroflex",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "plus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "j": {
        "place": "palatal",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "ɰ": {
        "place": "velar",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    "l": {
        "place": "alveolar",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "plus",
        "aspirated": "minus",
    },
    "w": {
        "place": "labiovelar",
        "manner": "approximant",
        "syllabic": "minus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "aspirated": "minus",
    },
    # Vowels
    "i": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "front",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "y": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "front",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "e": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "front",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "E": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "front",
        "round": "minus",
        "long": "plus",
        "aspirated": "minus",
    },
    "ø": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "front",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "ɛ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "front",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "œ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "front",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "æ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "low",
        "back": "front",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "a": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "low",
        "back": "front",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "A": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "low",
        "back": "front",
        "round": "minus",
        "long": "plus",
        "aspirated": "minus",
    },
    "ɨ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "central",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "ʉ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "central",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "ə": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "central",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "u": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "back",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "U": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "back",
        "round": "plus",
        "long": "plus",
        "aspirated": "minus",
    },
    "o": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "back",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "O": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "back",
        "round": "plus",
        "long": "plus",
        "aspirated": "minus",
    },
    "ɔ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "mid",
        "back": "back",
        "round": "plus",
        "long": "minus",
        "aspirated": "minus",
    },
    "ɒ": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "low",
        "back": "back",
        "round": "minus",
        "long": "minus",
        "aspirated": "minus",
    },
    "I": {
        "place": "vowel",
        "manner": "vowel2",
        "syllabic": "plus",
        "voice": "plus",
        "nasal": "minus",
        "retroflex": "minus",
        "lateral": "minus",
        "high": "high",
        "back": "front",
        "round": "minus",
        "long": "plus",
        "aspirated": "minus",
    },
}

# === Algorithm ===


def align(str1, str2, epsilon=0):
    """
    Compute the alignment of two phonetic strings.

    :param str str1: First string to be aligned
    :param str str2: Second string to be aligned

    :type epsilon: float (0.0 to 1.0)
    :param epsilon: Adjusts threshold similarity score for near-optimal alignments

    :rtype: list(list(tuple(str, str)))
    :return: Alignment(s) of str1 and str2

    (Kondrak 2002: 51)
    """
    if np is None:
        raise ImportError("You need numpy in order to use the align function")

    assert 0.0 <= epsilon <= 1.0, "Epsilon must be between 0.0 and 1.0."
    m = len(str1)
    n = len(str2)
    # This includes Kondrak's initialization of row 0 and column 0 to all 0s.
    S = np.zeros((m + 1, n + 1), dtype=float)

    # If i <= 1 or j <= 1, don't allow expansions as it doesn't make sense,
    # and breaks array and string indices. Make sure they never get chosen
    # by setting them to -inf.
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            edit1 = S[i - 1, j] + sigma_skip(str1[i - 1])
            edit2 = S[i, j - 1] + sigma_skip(str2[j - 1])
            edit3 = S[i - 1, j - 1] + sigma_sub(str1[i - 1], str2[j - 1])
            if i > 1:
                edit4 = S[i - 2, j - 1] + sigma_exp(str2[j - 1], str1[i - 2 : i])
            else:
                edit4 = -inf
            if j > 1:
                edit5 = S[i - 1, j - 2] + sigma_exp(str1[i - 1], str2[j - 2 : j])
            else:
                edit5 = -inf
            S[i, j] = max(edit1, edit2, edit3, edit4, edit5, 0)

    T = (1 - epsilon) * np.amax(S)  # Threshold score for near-optimal alignments

    alignments = []
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if S[i, j] >= T:
                alignments.append(_retrieve(i, j, 0, S, T, str1, str2, []))
    return alignments


def _retrieve(i, j, s, S, T, str1, str2, out):
    """
    Retrieve the path through the similarity matrix S starting at (i, j).

    :rtype: list(tuple(str, str))
    :return: Alignment of str1 and str2
    """
    if S[i, j] == 0:
        return out
    else:
        if j > 1 and S[i - 1, j - 2] + sigma_exp(str1[i - 1], str2[j - 2 : j]) + s >= T:
            out.insert(0, (str1[i - 1], str2[j - 2 : j]))
            _retrieve(
                i - 1,
                j - 2,
                s + sigma_exp(str1[i - 1], str2[j - 2 : j]),
                S,
                T,
                str1,
                str2,
                out,
            )
        elif (
            i > 1 and S[i - 2, j - 1] + sigma_exp(str2[j - 1], str1[i - 2 : i]) + s >= T
        ):
            out.insert(0, (str1[i - 2 : i], str2[j - 1]))
            _retrieve(
                i - 2,
                j - 1,
                s + sigma_exp(str2[j - 1], str1[i - 2 : i]),
                S,
                T,
                str1,
                str2,
                out,
            )
        elif S[i, j - 1] + sigma_skip(str2[j - 1]) + s >= T:
            out.insert(0, ("-", str2[j - 1]))
            _retrieve(i, j - 1, s + sigma_skip(str2[j - 1]), S, T, str1, str2, out)
        elif S[i - 1, j] + sigma_skip(str1[i - 1]) + s >= T:
            out.insert(0, (str1[i - 1], "-"))
            _retrieve(i - 1, j, s + sigma_skip(str1[i - 1]), S, T, str1, str2, out)
        elif S[i - 1, j - 1] + sigma_sub(str1[i - 1], str2[j - 1]) + s >= T:
            out.insert(0, (str1[i - 1], str2[j - 1]))
            _retrieve(
                i - 1,
                j - 1,
                s + sigma_sub(str1[i - 1], str2[j - 1]),
                S,
                T,
                str1,
                str2,
                out,
            )
    return out


def sigma_skip(p):
    """
    Returns score of an indel of P.

    (Kondrak 2002: 54)
    """
    return C_skip


def sigma_sub(p, q):
    """
    Returns score of a substitution of P with Q.

    (Kondrak 2002: 54)
    """
    return C_sub - delta(p, q) - V(p) - V(q)


def sigma_exp(p, q):
    """
    Returns score of an expansion/compression.

    (Kondrak 2002: 54)
    """
    q1 = q[0]
    q2 = q[1]
    return C_exp - delta(p, q1) - delta(p, q2) - V(p) - max(V(q1), V(q2))


def delta(p, q):
    """
    Return weighted sum of difference between P and Q.

    (Kondrak 2002: 54)
    """
    features = R(p, q)
    total = 0
    if np is not None:
        return np.dot(
            [diff(p, q, f) for f in features], [salience[f] for f in features]
        )
    for f in features:
        total += diff(p, q, f) * salience[f]
    return total


def diff(p, q, f):
    """
    Returns difference between phonetic segments P and Q for feature F.

    (Kondrak 2002: 52, 54)
    """
    p_features, q_features = feature_matrix[p], feature_matrix[q]
    return abs(similarity_matrix[p_features[f]] - similarity_matrix[q_features[f]])


def R(p, q):
    """
    Return relevant features for segment comparison.

    (Kondrak 2002: 54)
    """
    if p in consonants or q in consonants:
        return R_c
    return R_v


def V(p):
    """
    Return vowel weight if P is vowel.

    (Kondrak 2002: 54)
    """
    if p in consonants:
        return 0
    return C_vwl


# === Test ===


def demo():
    """
    A demonstration of the result of aligning phonetic sequences
    used in Kondrak's (2002) dissertation.
    """
    data = [pair.split(",") for pair in cognate_data.split("\n")]
    for pair in data:
        alignment = align(pair[0], pair[1])[0]
        alignment = [f"({a[0]}, {a[1]})" for a in alignment]
        alignment = " ".join(alignment)
        print(f"{pair[0]} ~ {pair[1]} : {alignment}")


cognate_data = """jo,ʒə
tu,ty
nosotros,nu
kjen,ki
ke,kwa
todos,tu
una,ən
dos,dø
tres,trwa
ombre,om
arbol,arbrə
pluma,plym
kabeθa,kap
boka,buʃ
pje,pje
koraθon,kœr
ber,vwar
benir,vənir
deθir,dir
pobre,povrə
ðis,dIzes
ðæt,das
wat,vas
nat,nixt
loŋ,laŋ
mæn,man
fleʃ,flajʃ
bləd,blyt
feðər,fEdər
hær,hAr
ir,Or
aj,awgə
nowz,nAzə
mawθ,munt
təŋ,tsuŋə
fut,fys
nij,knI
hænd,hant
hart,herts
livər,lEbər
ænd,ante
æt,ad
blow,flAre
ir,awris
ijt,edere
fiʃ,piʃkis
flow,fluere
staɾ,stella
ful,plenus
græs,gramen
hart,kordis
horn,korny
aj,ego
nij,genU
məðər,mAter
mawntən,mons
nejm,nomen
njuw,nowus
wən,unus
rawnd,rotundus
sow,suere
sit,sedere
θrij,tres
tuwθ,dentis
θin,tenwis
kinwawa,kenuaʔ
nina,nenah
napewa,napɛw
wapimini,wapemen
namesa,namɛʔs
okimawa,okemaw
ʃiʃipa,seʔsep
ahkohkwa,ahkɛh
pematesiweni,pematesewen
asenja,aʔsɛn"""


if __name__ == "__main__":
    demo()