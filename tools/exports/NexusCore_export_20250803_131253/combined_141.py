
# === NexusCore/tools\exports\export_20250803_114325\combined_126.py ===

# === NexusCore/openenv\Lib\site-packages\tornado\test\simple_httpclient_test.py ===
import collections
from contextlib import closing
import errno
import logging
import os
import re
import socket
import ssl
import sys
import typing  # noqa: F401

from tornado.escape import to_unicode, utf8
from tornado import gen, version
from tornado.httpclient import AsyncHTTPClient, HTTPResponse
from tornado.httpserver import HTTPServer
from tornado.httputil import HTTPHeaders, ResponseStartLine
from tornado.ioloop import IOLoop
from tornado.iostream import UnsatisfiableReadError
from tornado.locks import Event
from tornado.log import gen_log
from tornado.netutil import Resolver, bind_sockets
from tornado.simple_httpclient import (
    SimpleAsyncHTTPClient,
    HTTPStreamClosedError,
    HTTPTimeoutError,
)
from tornado.test.httpclient_test import (
    ChunkHandler,
    CountdownHandler,
    HelloWorldHandler,
    RedirectHandler,
    UserAgentHandler,
)
from tornado.test import httpclient_test
from tornado.testing import (
    AsyncHTTPTestCase,
    AsyncHTTPSTestCase,
    AsyncTestCase,
    ExpectLog,
    gen_test,
)
from tornado.test.util import (
    abstract_base_test,
    skipIfNoIPv6,
    refusing_port,
)
from tornado.web import RequestHandler, Application, url, stream_request_body


class SimpleHTTPClientCommonTestCase(httpclient_test.HTTPClientCommonTestCase):
    def get_http_client(self):
        client = SimpleAsyncHTTPClient(force_instance=True)
        self.assertTrue(isinstance(client, SimpleAsyncHTTPClient))
        return client


class TriggerHandler(RequestHandler):
    def initialize(self, queue, wake_callback):
        self.queue = queue
        self.wake_callback = wake_callback

    @gen.coroutine
    def get(self):
        logging.debug("queuing trigger")
        event = Event()
        self.queue.append(event.set)
        if self.get_argument("wake", "true") == "true":
            self.wake_callback()
        yield event.wait()


class ContentLengthHandler(RequestHandler):
    def get(self):
        self.stream = self.detach()
        IOLoop.current().spawn_callback(self.write_response)

    @gen.coroutine
    def write_response(self):
        yield self.stream.write(
            utf8(
                "HTTP/1.0 200 OK\r\nContent-Length: %s\r\n\r\nok"
                % self.get_argument("value")
            )
        )
        self.stream.close()


class HeadHandler(RequestHandler):
    def head(self):
        self.set_header("Content-Length", "7")


class OptionsHandler(RequestHandler):
    def options(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.write("ok")


class NoContentHandler(RequestHandler):
    def get(self):
        self.set_status(204)
        self.finish()


class SeeOtherPostHandler(RequestHandler):
    def post(self):
        redirect_code = int(self.request.body)
        assert redirect_code in (302, 303), "unexpected body %r" % self.request.body
        self.set_header("Location", "/see_other_get")
        self.set_status(redirect_code)


class SeeOtherGetHandler(RequestHandler):
    def get(self):
        if self.request.body:
            raise Exception("unexpected body %r" % self.request.body)
        self.write("ok")


class HostEchoHandler(RequestHandler):
    def get(self):
        self.write(self.request.headers["Host"])


class NoContentLengthHandler(RequestHandler):
    def get(self):
        if self.request.version.startswith("HTTP/1"):
            # Emulate the old HTTP/1.0 behavior of returning a body with no
            # content-length.  Tornado handles content-length at the framework
            # level so we have to go around it.
            stream = self.detach()
            stream.write(b"HTTP/1.0 200 OK\r\n\r\n" b"hello")
            stream.close()
        else:
            self.finish("HTTP/1 required")


class EchoPostHandler(RequestHandler):
    def post(self):
        self.write(self.request.body)


@stream_request_body
class RespondInPrepareHandler(RequestHandler):
    def prepare(self):
        self.set_status(403)
        self.finish("forbidden")


@abstract_base_test
class SimpleHTTPClientTestMixin(AsyncTestCase):
    # See comments on TestIOStreamWebMixin
    def get_http_port(self) -> int:
        raise NotImplementedError()

    def fetch(
        self, path: str, raise_error: bool = False, **kwargs: typing.Any
    ) -> HTTPResponse:
        # To be filled in by mixing in AsyncHTTPTestCase or AsyncHTTPSTestCase
        raise NotImplementedError()

    def get_url(self, path: str) -> str:
        raise NotImplementedError()

    def get_protocol(self) -> str:
        raise NotImplementedError()

    def get_http_server(self) -> HTTPServer:
        raise NotImplementedError()

    def create_client(self, **kwargs):
        raise NotImplementedError()

    def mixin_get_app(self):
        # callable objects to finish pending /trigger requests
        self.triggers = (
            collections.deque()
        )  # type: typing.Deque[typing.Callable[[], None]]
        return Application(
            [
                url(
                    "/trigger",
                    TriggerHandler,
                    dict(queue=self.triggers, wake_callback=self.stop),
                ),
                url("/chunk", ChunkHandler),
                url("/countdown/([0-9]+)", CountdownHandler, name="countdown"),
                url("/hello", HelloWorldHandler),
                url("/content_length", ContentLengthHandler),
                url("/head", HeadHandler),
                url("/options", OptionsHandler),
                url("/no_content", NoContentHandler),
                url("/see_other_post", SeeOtherPostHandler),
                url("/see_other_get", SeeOtherGetHandler),
                url("/host_echo", HostEchoHandler),
                url("/no_content_length", NoContentLengthHandler),
                url("/echo_post", EchoPostHandler),
                url("/respond_in_prepare", RespondInPrepareHandler),
                url("/redirect", RedirectHandler),
                url("/user_agent", UserAgentHandler),
            ],
            gzip=True,
        )

    def test_singleton(self):
        # Class "constructor" reuses objects on the same IOLoop
        self.assertIs(SimpleAsyncHTTPClient(), SimpleAsyncHTTPClient())
        # unless force_instance is used
        self.assertIsNot(
            SimpleAsyncHTTPClient(), SimpleAsyncHTTPClient(force_instance=True)
        )
        # different IOLoops use different objects
        with closing(IOLoop(make_current=False)) as io_loop2:

            async def make_client():
                await gen.sleep(0)
                return SimpleAsyncHTTPClient()

            client1 = self.io_loop.run_sync(make_client)
            client2 = io_loop2.run_sync(make_client)
            self.assertIsNot(client1, client2)

    def test_connection_limit(self):
        with closing(self.create_client(max_clients=2)) as client:
            self.assertEqual(client.max_clients, 2)
            seen = []
            # Send 4 requests.  Two can be sent immediately, while the others
            # will be queued
            for i in range(4):

                def cb(fut, i=i):
                    seen.append(i)
                    self.stop()

                client.fetch(self.get_url("/trigger")).add_done_callback(cb)
            self.wait(condition=lambda: len(self.triggers) == 2)
            self.assertEqual(len(client.queue), 2)

            # Finish the first two requests and let the next two through
            self.triggers.popleft()()
            self.triggers.popleft()()
            self.wait(condition=lambda: (len(self.triggers) == 2 and len(seen) == 2))
            self.assertEqual(set(seen), {0, 1})
            self.assertEqual(len(client.queue), 0)

            # Finish all the pending requests
            self.triggers.popleft()()
            self.triggers.popleft()()
            self.wait(condition=lambda: len(seen) == 4)
            self.assertEqual(set(seen), {0, 1, 2, 3})
            self.assertEqual(len(self.triggers), 0)

    @gen_test
    def test_redirect_connection_limit(self):
        # following redirects should not consume additional connections
        with closing(self.create_client(max_clients=1)) as client:
            response = yield client.fetch(self.get_url("/countdown/3"), max_redirects=3)
            response.rethrow()

    def test_max_redirects(self):
        response = self.fetch("/countdown/5", max_redirects=3)
        self.assertEqual(302, response.code)
        # We requested 5, followed three redirects for 4, 3, 2, then the last
        # unfollowed redirect is to 1.
        self.assertTrue(response.request.url.endswith("/countdown/5"))
        self.assertTrue(response.effective_url.endswith("/countdown/2"))
        self.assertTrue(response.headers["Location"].endswith("/countdown/1"))

    def test_header_reuse(self):
        # Apps may reuse a headers object if they are only passing in constant
        # headers like user-agent.  The header object should not be modified.
        headers = HTTPHeaders({"User-Agent": "Foo"})
        self.fetch("/hello", headers=headers)
        self.assertEqual(list(headers.get_all()), [("User-Agent", "Foo")])

    def test_default_user_agent(self):
        response = self.fetch("/user_agent", method="GET")
        self.assertEqual(200, response.code)
        self.assertEqual(response.body.decode(), f"Tornado/{version}")

    def test_see_other_redirect(self):
        for code in (302, 303):
            response = self.fetch("/see_other_post", method="POST", body="%d" % code)
            self.assertEqual(200, response.code)
            self.assertTrue(response.request.url.endswith("/see_other_post"))
            self.assertTrue(response.effective_url.endswith("/see_other_get"))
            # request is the original request, is a POST still
            self.assertEqual("POST", response.request.method)

    @gen_test
    def test_connect_timeout(self):
        timeout = 0.1

        cleanup_event = Event()
        test = self

        class TimeoutResolver(Resolver):
            async def resolve(self, *args, **kwargs):
                await cleanup_event.wait()
                # Return something valid so the test doesn't raise during shutdown.
                return [(socket.AF_INET, ("127.0.0.1", test.get_http_port()))]

        with closing(self.create_client(resolver=TimeoutResolver())) as client:
            with self.assertRaises(HTTPTimeoutError):
                yield client.fetch(
                    self.get_url("/hello"),
                    connect_timeout=timeout,
                    request_timeout=3600,
                    raise_error=True,
                )

        # Let the hanging coroutine clean up after itself. We need to
        # wait more than a single IOLoop iteration for the SSL case,
        # which logs errors on unexpected EOF.
        cleanup_event.set()
        yield gen.sleep(0.2)

    def test_request_timeout(self):
        timeout = 0.1
        if os.name == "nt":
            timeout = 0.5

        with self.assertRaises(HTTPTimeoutError):
            self.fetch("/trigger?wake=false", request_timeout=timeout, raise_error=True)
        # trigger the hanging request to let it clean up after itself
        self.triggers.popleft()()
        self.io_loop.run_sync(lambda: gen.sleep(0))

    @skipIfNoIPv6
    def test_ipv6(self):
        [sock] = bind_sockets(0, "::1", family=socket.AF_INET6)
        port = sock.getsockname()[1]
        self.get_http_server().add_socket(sock)
        url = "%s://[::1]:%d/hello" % (self.get_protocol(), port)

        # ipv6 is currently enabled by default but can be disabled
        with self.assertRaises(Exception):
            self.fetch(url, allow_ipv6=False, raise_error=True)

        response = self.fetch(url)
        self.assertEqual(response.body, b"Hello world!")

    def test_multiple_content_length_accepted(self):
        response = self.fetch("/content_length?value=2,2")
        self.assertEqual(response.body, b"ok")
        response = self.fetch("/content_length?value=2,%202,2")
        self.assertEqual(response.body, b"ok")

        with ExpectLog(
            gen_log, ".*Multiple unequal Content-Lengths", level=logging.INFO
        ):
            with self.assertRaises(HTTPStreamClosedError):
                self.fetch("/content_length?value=2,4", raise_error=True)
            with self.assertRaises(HTTPStreamClosedError):
                self.fetch("/content_length?value=2,%202,3", raise_error=True)

    def test_head_request(self):
        response = self.fetch("/head", method="HEAD")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["content-length"], "7")
        self.assertFalse(response.body)

    def test_options_request(self):
        response = self.fetch("/options", method="OPTIONS")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["content-length"], "2")
        self.assertEqual(response.headers["access-control-allow-origin"], "*")
        self.assertEqual(response.body, b"ok")

    def test_no_content(self):
        response = self.fetch("/no_content")
        self.assertEqual(response.code, 204)
        # 204 status shouldn't have a content-length
        #
        # Tests with a content-length header are included below
        # in HTTP204NoContentTestCase.
        self.assertNotIn("Content-Length", response.headers)

    def test_host_header(self):
        host_re = re.compile(b"^127.0.0.1:[0-9]+$")
        response = self.fetch("/host_echo")
        self.assertTrue(host_re.match(response.body))

        url = self.get_url("/host_echo").replace("http://", "http://me:secret@")
        response = self.fetch(url)
        self.assertTrue(host_re.match(response.body), response.body)

    def test_connection_refused(self):
        cleanup_func, port = refusing_port()
        self.addCleanup(cleanup_func)
        with ExpectLog(gen_log, ".*", required=False):
            with self.assertRaises(socket.error) as cm:
                self.fetch("http://127.0.0.1:%d/" % port, raise_error=True)

        if sys.platform != "cygwin":
            # cygwin returns EPERM instead of ECONNREFUSED here
            contains_errno = str(errno.ECONNREFUSED) in str(cm.exception)
            if not contains_errno and hasattr(errno, "WSAECONNREFUSED"):
                contains_errno = str(errno.WSAECONNREFUSED) in str(  # type: ignore
                    cm.exception
                )
            self.assertTrue(contains_errno, cm.exception)
            # This is usually "Connection refused".
            # On windows, strerror is broken and returns "Unknown error".
            expected_message = os.strerror(errno.ECONNREFUSED)
            self.assertTrue(expected_message in str(cm.exception), cm.exception)

    def test_queue_timeout(self):
        with closing(self.create_client(max_clients=1)) as client:
            # Wait for the trigger request to block, not complete.
            fut1 = client.fetch(self.get_url("/trigger"), request_timeout=10)
            self.wait()
            with self.assertRaises(HTTPTimeoutError) as cm:
                self.io_loop.run_sync(
                    lambda: client.fetch(
                        self.get_url("/hello"), connect_timeout=0.1, raise_error=True
                    )
                )

            self.assertEqual(str(cm.exception), "Timeout in request queue")
            self.triggers.popleft()()
            self.io_loop.run_sync(lambda: fut1)

    def test_no_content_length(self):
        response = self.fetch("/no_content_length")
        if response.body == b"HTTP/1 required":
            self.skipTest("requires HTTP/1.x")
        else:
            self.assertEqual(b"hello", response.body)

    def sync_body_producer(self, write):
        write(b"1234")
        write(b"5678")

    @gen.coroutine
    def async_body_producer(self, write):
        yield write(b"1234")
        yield gen.moment
        yield write(b"5678")

    def test_sync_body_producer_chunked(self):
        response = self.fetch(
            "/echo_post", method="POST", body_producer=self.sync_body_producer
        )
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_sync_body_producer_content_length(self):
        response = self.fetch(
            "/echo_post",
            method="POST",
            body_producer=self.sync_body_producer,
            headers={"Content-Length": "8"},
        )
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_async_body_producer_chunked(self):
        response = self.fetch(
            "/echo_post", method="POST", body_producer=self.async_body_producer
        )
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_async_body_producer_content_length(self):
        response = self.fetch(
            "/echo_post",
            method="POST",
            body_producer=self.async_body_producer,
            headers={"Content-Length": "8"},
        )
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_native_body_producer_chunked(self):
        async def body_producer(write):
            await write(b"1234")
            import asyncio

            await asyncio.sleep(0)
            await write(b"5678")

        response = self.fetch("/echo_post", method="POST", body_producer=body_producer)
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_native_body_producer_content_length(self):
        async def body_producer(write):
            await write(b"1234")
            import asyncio

            await asyncio.sleep(0)
            await write(b"5678")

        response = self.fetch(
            "/echo_post",
            method="POST",
            body_producer=body_producer,
            headers={"Content-Length": "8"},
        )
        response.rethrow()
        self.assertEqual(response.body, b"12345678")

    def test_100_continue(self):
        response = self.fetch(
            "/echo_post", method="POST", body=b"1234", expect_100_continue=True
        )
        self.assertEqual(response.body, b"1234")

    def test_100_continue_early_response(self):
        def body_producer(write):
            raise Exception("should not be called")

        response = self.fetch(
            "/respond_in_prepare",
            method="POST",
            body_producer=body_producer,
            expect_100_continue=True,
        )
        self.assertEqual(response.code, 403)

    def test_streaming_follow_redirects(self):
        # When following redirects, header and streaming callbacks
        # should only be called for the final result.
        # TODO(bdarnell): this test belongs in httpclient_test instead of
        # simple_httpclient_test, but it fails with the version of libcurl
        # available on travis-ci. Move it when that has been upgraded
        # or we have a better framework to skip tests based on curl version.
        headers = []  # type: typing.List[str]
        chunk_bytes = []  # type: typing.List[bytes]
        self.fetch(
            "/redirect?url=/hello",
            header_callback=headers.append,
            streaming_callback=chunk_bytes.append,
        )
        chunks = list(map(to_unicode, chunk_bytes))
        self.assertEqual(chunks, ["Hello world!"])
        # Make sure we only got one set of headers.
        num_start_lines = len([h for h in headers if h.startswith("HTTP/")])
        self.assertEqual(num_start_lines, 1)


class SimpleHTTPClientTestCase(AsyncHTTPTestCase, SimpleHTTPClientTestMixin):
    def setUp(self):
        super().setUp()
        self.http_client = self.create_client()

    def get_app(self):
        return self.mixin_get_app()

    def create_client(self, **kwargs):
        return SimpleAsyncHTTPClient(force_instance=True, **kwargs)


class SimpleHTTPSClientTestCase(AsyncHTTPSTestCase, SimpleHTTPClientTestMixin):
    def setUp(self):
        super().setUp()
        self.http_client = self.create_client()

    def get_app(self):
        return self.mixin_get_app()

    def create_client(self, **kwargs):
        return SimpleAsyncHTTPClient(
            force_instance=True, defaults=dict(validate_cert=False), **kwargs
        )

    def test_ssl_options(self):
        resp = self.fetch("/hello", ssl_options={"cert_reqs": ssl.CERT_NONE})
        self.assertEqual(resp.body, b"Hello world!")

    def test_ssl_context(self):
        ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        resp = self.fetch("/hello", ssl_options=ssl_ctx)
        self.assertEqual(resp.body, b"Hello world!")

    def test_ssl_options_handshake_fail(self):
        with ExpectLog(gen_log, "SSL Error|Uncaught exception", required=False):
            with self.assertRaises(ssl.SSLError):
                self.fetch(
                    "/hello",
                    ssl_options=dict(cert_reqs=ssl.CERT_REQUIRED),
                    raise_error=True,
                )

    def test_ssl_context_handshake_fail(self):
        with ExpectLog(gen_log, "SSL Error|Uncaught exception"):
            # CERT_REQUIRED is set by default.
            ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            with self.assertRaises(ssl.SSLError):
                self.fetch("/hello", ssl_options=ctx, raise_error=True)

    def test_error_logging(self):
        # No stack traces are logged for SSL errors (in this case,
        # failure to validate the testing self-signed cert).
        # The SSLError is exposed through ssl.SSLError.
        with ExpectLog(gen_log, ".*") as expect_log:
            with self.assertRaises(ssl.SSLError):
                self.fetch("/", validate_cert=True, raise_error=True)
        self.assertFalse(expect_log.logged_stack)


class CreateAsyncHTTPClientTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.saved = AsyncHTTPClient._save_configuration()

    def tearDown(self):
        AsyncHTTPClient._restore_configuration(self.saved)
        super().tearDown()

    def test_max_clients(self):
        AsyncHTTPClient.configure(SimpleAsyncHTTPClient)
        with closing(AsyncHTTPClient(force_instance=True)) as client:
            self.assertEqual(client.max_clients, 10)  # type: ignore
        with closing(AsyncHTTPClient(max_clients=11, force_instance=True)) as client:
            self.assertEqual(client.max_clients, 11)  # type: ignore

        # Now configure max_clients statically and try overriding it
        # with each way max_clients can be passed
        AsyncHTTPClient.configure(SimpleAsyncHTTPClient, max_clients=12)
        with closing(AsyncHTTPClient(force_instance=True)) as client:
            self.assertEqual(client.max_clients, 12)  # type: ignore
        with closing(AsyncHTTPClient(max_clients=13, force_instance=True)) as client:
            self.assertEqual(client.max_clients, 13)  # type: ignore
        with closing(AsyncHTTPClient(max_clients=14, force_instance=True)) as client:
            self.assertEqual(client.max_clients, 14)  # type: ignore


class HTTP100ContinueTestCase(AsyncHTTPTestCase):
    def respond_100(self, request):
        self.http1 = request.version.startswith("HTTP/1.")
        if not self.http1:
            request.connection.write_headers(
                ResponseStartLine("", 200, "OK"), HTTPHeaders()
            )
            request.connection.finish()
            return
        self.request = request
        fut = self.request.connection.stream.write(b"HTTP/1.1 100 CONTINUE\r\n\r\n")
        fut.add_done_callback(self.respond_200)

    def respond_200(self, fut):
        fut.result()
        fut = self.request.connection.stream.write(
            b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nA"
        )
        fut.add_done_callback(lambda f: self.request.connection.stream.close())

    def get_app(self):
        # Not a full Application, but works as an HTTPServer callback
        return self.respond_100

    def test_100_continue(self):
        res = self.fetch("/")
        if not self.http1:
            self.skipTest("requires HTTP/1.x")
        self.assertEqual(res.body, b"A")


class HTTP204NoContentTestCase(AsyncHTTPTestCase):
    def respond_204(self, request):
        self.http1 = request.version.startswith("HTTP/1.")
        if not self.http1:
            # Close the request cleanly in HTTP/2; it will be skipped anyway.
            request.connection.write_headers(
                ResponseStartLine("", 200, "OK"), HTTPHeaders()
            )
            request.connection.finish()
            return

        # A 204 response never has a body, even if doesn't have a content-length
        # (which would otherwise mean read-until-close).  We simulate here a
        # server that sends no content length and does not close the connection.
        #
        # Tests of a 204 response with no Content-Length header are included
        # in SimpleHTTPClientTestMixin.
        stream = request.connection.detach()
        stream.write(b"HTTP/1.1 204 No content\r\n")
        if request.arguments.get("error", [False])[-1]:
            stream.write(b"Content-Length: 5\r\n")
        else:
            stream.write(b"Content-Length: 0\r\n")
        stream.write(b"\r\n")
        stream.close()

    def get_app(self):
        return self.respond_204

    def test_204_no_content(self):
        resp = self.fetch("/")
        if not self.http1:
            self.skipTest("requires HTTP/1.x")
        self.assertEqual(resp.code, 204)
        self.assertEqual(resp.body, b"")

    def test_204_invalid_content_length(self):
        # 204 status with non-zero content length is malformed
        with ExpectLog(
            gen_log, ".*Response with code 204 should not have body", level=logging.INFO
        ):
            with self.assertRaises(HTTPStreamClosedError):
                self.fetch("/?error=1", raise_error=True)
                if not self.http1:
                    self.skipTest("requires HTTP/1.x")
                if self.http_client.configured_class != SimpleAsyncHTTPClient:
                    self.skipTest("curl client accepts invalid headers")


class HostnameMappingTestCase(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.http_client = SimpleAsyncHTTPClient(
            hostname_mapping={
                "www.example.com": "127.0.0.1",
                ("foo.example.com", 8000): ("127.0.0.1", self.get_http_port()),
            }
        )

    def get_app(self):
        return Application([url("/hello", HelloWorldHandler)])

    def test_hostname_mapping(self):
        response = self.fetch("http://www.example.com:%d/hello" % self.get_http_port())
        response.rethrow()
        self.assertEqual(response.body, b"Hello world!")

    def test_port_mapping(self):
        response = self.fetch("http://foo.example.com:8000/hello")
        response.rethrow()
        self.assertEqual(response.body, b"Hello world!")


class ResolveTimeoutTestCase(AsyncHTTPTestCase):
    def setUp(self):
        self.cleanup_event = Event()
        test = self

        # Dummy Resolver subclass that never finishes.
        class BadResolver(Resolver):
            @gen.coroutine
            def resolve(self, *args, **kwargs):
                yield test.cleanup_event.wait()
                # Return something valid so the test doesn't raise during cleanup.
                return [(socket.AF_INET, ("127.0.0.1", test.get_http_port()))]

        super().setUp()
        self.http_client = SimpleAsyncHTTPClient(resolver=BadResolver())

    def get_app(self):
        return Application([url("/hello", HelloWorldHandler)])

    def test_resolve_timeout(self):
        with self.assertRaises(HTTPTimeoutError):
            self.fetch("/hello", connect_timeout=0.1, raise_error=True)

        # Let the hanging coroutine clean up after itself
        self.cleanup_event.set()
        self.io_loop.run_sync(lambda: gen.sleep(0))


class MaxHeaderSizeTest(AsyncHTTPTestCase):
    def get_app(self):
        class SmallHeaders(RequestHandler):
            def get(self):
                self.set_header("X-Filler", "a" * 100)
                self.write("ok")

        class LargeHeaders(RequestHandler):
            def get(self):
                self.set_header("X-Filler", "a" * 1000)
                self.write("ok")

        return Application([("/small", SmallHeaders), ("/large", LargeHeaders)])

    def get_http_client(self):
        return SimpleAsyncHTTPClient(max_header_size=1024)

    def test_small_headers(self):
        response = self.fetch("/small")
        response.rethrow()
        self.assertEqual(response.body, b"ok")

    def test_large_headers(self):
        with ExpectLog(gen_log, "Unsatisfiable read", level=logging.INFO):
            with self.assertRaises(UnsatisfiableReadError):
                self.fetch("/large", raise_error=True)


class MaxBodySizeTest(AsyncHTTPTestCase):
    def get_app(self):
        class SmallBody(RequestHandler):
            def get(self):
                self.write("a" * 1024 * 64)

        class LargeBody(RequestHandler):
            def get(self):
                self.write("a" * 1024 * 100)

        return Application([("/small", SmallBody), ("/large", LargeBody)])

    def get_http_client(self):
        return SimpleAsyncHTTPClient(max_body_size=1024 * 64)

    def test_small_body(self):
        response = self.fetch("/small")
        response.rethrow()
        self.assertEqual(response.body, b"a" * 1024 * 64)

    def test_large_body(self):
        with ExpectLog(
            gen_log,
            "Malformed HTTP message from None: Content-Length too long",
            level=logging.INFO,
        ):
            with self.assertRaises(HTTPStreamClosedError):
                self.fetch("/large", raise_error=True)


class MaxBufferSizeTest(AsyncHTTPTestCase):
    def get_app(self):
        class LargeBody(RequestHandler):
            def get(self):
                self.write("a" * 1024 * 100)

        return Application([("/large", LargeBody)])

    def get_http_client(self):
        # 100KB body with 64KB buffer
        return SimpleAsyncHTTPClient(
            max_body_size=1024 * 100, max_buffer_size=1024 * 64
        )

    def test_large_body(self):
        response = self.fetch("/large")
        response.rethrow()
        self.assertEqual(response.body, b"a" * 1024 * 100)


class ChunkedWithContentLengthTest(AsyncHTTPTestCase):
    def get_app(self):
        class ChunkedWithContentLength(RequestHandler):
            def get(self):
                # Add an invalid Transfer-Encoding to the response
                self.set_header("Transfer-Encoding", "chunked")
                self.write("Hello world")

        return Application([("/chunkwithcl", ChunkedWithContentLength)])

    def get_http_client(self):
        return SimpleAsyncHTTPClient()

    def test_chunked_with_content_length(self):
        # Make sure the invalid headers are detected
        with ExpectLog(
            gen_log,
            (
                "Malformed HTTP message from None: Message "
                "with both Transfer-Encoding and Content-Length"
            ),
            level=logging.INFO,
        ):
            with self.assertRaises(HTTPStreamClosedError):
                self.fetch("/chunkwithcl", raise_error=True)

# === NexusCore/openenv\Lib\site-packages\win32comext\shell\demos\servers\folder_view.py ===
# This is a port of the Vista SDK "FolderView" sample, and associated
# notes at https://web.archive.org/web/20081225011615/http://shellrevealed.com/blogs/shellblog/archive/2007/03/15/Shell-Namespace-Extension_3A00_-Creating-and-Using-the-System-Folder-View-Object.aspx
# A key difference to shell_view.py is that this version uses the default
# IShellView provided by the shell (via SHCreateShellFolderView) rather
# than our own.
# XXX - sadly, it doesn't work quite like the original sample.  Oh well,
# another day...
import os
import pickle
import random
import sys

import commctrl
import pythoncom
import win32api
import win32con
import win32gui
import winerror
from win32com.axcontrol import axcontrol  # IObjectWithSite
from win32com.propsys import propsys
from win32com.server.exception import COMException
from win32com.server.util import NewEnum as _NewEnum, wrap as _wrap
from win32com.shell import shell, shellcon

GUID = pythoncom.MakeIID

# If set, output spews to the win32traceutil collector...
debug = 0


# wrap a python object in a COM pointer
def wrap(ob, iid=None):
    return _wrap(ob, iid, useDispatcher=(debug > 0))


def NewEnum(seq, iid):
    return _NewEnum(seq, iid=iid, useDispatcher=(debug > 0))


# The sample makes heavy use of "string ids" (ie, integer IDs defined in .h
# files, loaded at runtime from a (presumably localized) DLL.  We cheat.
_sids = {}  # strings, indexed bystring_id,


def LoadString(sid):
    return _sids[sid]


# fn to create a unique string ID
_last_ids = 0


def _make_ids(s):
    global _last_ids
    _last_ids += 1
    _sids[_last_ids] = s
    return _last_ids


# These strings are what the user sees and would be localized.
# XXX - it's possible that the shell might persist these values, so
# this scheme wouldn't really be suitable in a real ap.
IDS_UNSPECIFIED = _make_ids("unspecified")
IDS_SMALL = _make_ids("small")
IDS_MEDIUM = _make_ids("medium")
IDS_LARGE = _make_ids("large")
IDS_CIRCLE = _make_ids("circle")
IDS_TRIANGLE = _make_ids("triangle")
IDS_RECTANGLE = _make_ids("rectangle")
IDS_POLYGON = _make_ids("polygon")
IDS_DISPLAY = _make_ids("Display")
IDS_DISPLAY_TT = _make_ids("Display the item.")
IDS_SETTINGS = _make_ids("Settings")
IDS_SETTING1 = _make_ids("Setting 1")
IDS_SETTING2 = _make_ids("Setting 2")
IDS_SETTING3 = _make_ids("Setting 3")
IDS_SETTINGS_TT = _make_ids("Modify settings.")
IDS_SETTING1_TT = _make_ids("Modify setting 1.")
IDS_SETTING2_TT = _make_ids("Modify setting 2.")
IDS_SETTING3_TT = _make_ids("Modify setting 3.")
IDS_LESSTHAN5 = _make_ids("Less Than 5")
IDS_5ORGREATER = _make_ids("Five or Greater")
del _make_ids, _last_ids

# Other misc resource stuff
IDI_ICON1 = 100
IDI_SETTINGS = 101

# The sample defines a number of "category ids".  Each one gets
# its own GUID.
CAT_GUID_NAME = GUID("{de094c9d-c65a-11dc-ba21-005056c00008}")
CAT_GUID_SIZE = GUID("{de094c9e-c65a-11dc-ba21-005056c00008}")
CAT_GUID_SIDES = GUID("{de094c9f-c65a-11dc-ba21-005056c00008}")
CAT_GUID_LEVEL = GUID("{de094ca0-c65a-11dc-ba21-005056c00008}")
# The next category guid is NOT based on a column (see
# ViewCategoryProvider::EnumCategories()...)
CAT_GUID_VALUE = "{de094ca1-c65a-11dc-ba21-005056c00008}"

GUID_Display = GUID("{4d6c2fdd-c689-11dc-ba21-005056c00008}")
GUID_Settings = GUID("{4d6c2fde-c689-11dc-ba21-005056c00008}")
GUID_Setting1 = GUID("{4d6c2fdf-c689-11dc-ba21-005056c00008}")
GUID_Setting2 = GUID("{4d6c2fe0-c689-11dc-ba21-005056c00008}")
GUID_Setting3 = GUID("{4d6c2fe1-c689-11dc-ba21-005056c00008}")

# Hrm - not sure what to do about the std keys.
# Probably need a simple parser for propkey.h
PKEY_ItemNameDisplay = ("{B725F130-47EF-101A-A5F1-02608C9EEBAC}", 10)
PKEY_PropList_PreviewDetails = ("{C9944A21-A406-48FE-8225-AEC7E24C211B}", 8)

# Not sure what the "3" here refers to - docs say PID_FIRST_USABLE (2) be
# used.  Presumably it is the 'propID' value in the .propdesc file!
# note that the following GUIDs are also references in the .propdesc file
PID_SOMETHING = 3
# These are our 'private' PKEYs
# Col 2, name="Sample.AreaSize"
PKEY_Sample_AreaSize = ("{d6f5e341-c65c-11dc-ba21-005056c00008}", PID_SOMETHING)
# Col 3, name="Sample.NumberOfSides"
PKEY_Sample_NumberOfSides = ("{d6f5e342-c65c-11dc-ba21-005056c00008}", PID_SOMETHING)
# Col 4, name="Sample.DirectoryLevel"
PKEY_Sample_DirectoryLevel = ("{d6f5e343-c65c-11dc-ba21-005056c00008}", PID_SOMETHING)


# We construct a PIDL from a pickle of a dict - turn it back into a
# dict (we should *never* be called with a PIDL that the last elt is not
# ours, so it is safe to assume we created it (assume->"ass" = "u" + "me" :)
def pidl_to_item(pidl):
    # Note that only the *last* elt in the PIDL is certainly ours,
    # but it contains everything we need encoded as a dict.
    return pickle.loads(pidl[-1])


# Start of msdn sample port...
# make_item_enum replaces the sample's entire EnumIDList.cpp :)
def make_item_enum(level, flags):
    pidls = []
    nums = """zero one two three four five size seven eight nine ten""".split()
    for i, name in enumerate(nums):
        size = random.randint(0, 255)
        sides = 1
        while sides in [1, 2]:
            sides = random.randint(0, 5)
        is_folder = (i % 2) != 0
        # check the flags say to include it.
        # (This seems strange; if you ask the same folder for, but appear
        skip = False
        if not (flags & shellcon.SHCONTF_STORAGE):
            if is_folder:
                skip = not (flags & shellcon.SHCONTF_FOLDERS)
            else:
                skip = not (flags & shellcon.SHCONTF_NONFOLDERS)
        if not skip:
            data = {
                "name": name,
                "size": size,
                "sides": sides,
                "level": level,
                "is_folder": is_folder,
            }
            pidls.append([pickle.dumps(data)])
    return NewEnum(pidls, shell.IID_IEnumIDList)


# start of Utils.cpp port
def DisplayItem(shell_item_array, hwnd_parent=0):
    # Get the first ShellItem and display its name
    if shell_item_array is None:
        msg = "You must select something!"
    else:
        si = shell_item_array.GetItemAt(0)
        name = si.GetDisplayName(shellcon.SIGDN_NORMALDISPLAY)
        msg = "%d items selected, first is %r" % (shell_item_array.GetCount(), name)
    win32gui.MessageBox(hwnd_parent, msg, "Hello", win32con.MB_OK)


# end of Utils.cpp port


# start of sample's FVCommands.cpp port
class Command:
    def __init__(self, guid, ids, ids_tt, idi, flags, callback, children):
        self.guid = guid
        self.ids = ids
        self.ids_tt = ids_tt
        self.idi = idi
        self.flags = flags
        self.callback = callback
        self.children = children
        assert not children or isinstance(children[0], Command)

    def tuple(self):
        return (
            self.guid,
            self.ids,
            self.ids_tt,
            self.idi,
            self.flags,
            self.callback,
            self.children,
        )


# command callbacks - called back directly by us - see ExplorerCommand.Invoke
def onDisplay(items, bindctx):
    DisplayItem(items)


def onSetting1(items, bindctx):
    win32gui.MessageBox(0, LoadString(IDS_SETTING1), "Hello", win32con.MB_OK)


def onSetting2(items, bindctx):
    win32gui.MessageBox(0, LoadString(IDS_SETTING2), "Hello", win32con.MB_OK)


def onSetting3(items, bindctx):
    win32gui.MessageBox(0, LoadString(IDS_SETTING3), "Hello", win32con.MB_OK)


taskSettings = [
    Command(
        GUID_Setting1, IDS_SETTING1, IDS_SETTING1_TT, IDI_SETTINGS, 0, onSetting1, None
    ),
    Command(
        GUID_Setting2, IDS_SETTING2, IDS_SETTING2_TT, IDI_SETTINGS, 0, onSetting2, None
    ),
    Command(
        GUID_Setting3, IDS_SETTING3, IDS_SETTING3_TT, IDI_SETTINGS, 0, onSetting3, None
    ),
]

tasks = [
    Command(GUID_Display, IDS_DISPLAY, IDS_DISPLAY_TT, IDI_ICON1, 0, onDisplay, None),
    Command(
        GUID_Settings,
        IDS_SETTINGS,
        IDS_SETTINGS_TT,
        IDI_SETTINGS,
        shellcon.ECF_HASSUBCOMMANDS,
        None,
        taskSettings,
    ),
]


class ExplorerCommandProvider:
    _com_interfaces_ = [shell.IID_IExplorerCommandProvider]
    _public_methods_ = shellcon.IExplorerCommandProvider_Methods

    def GetCommands(self, site, iid):
        items = [wrap(ExplorerCommand(t)) for t in tasks]
        return NewEnum(items, shell.IID_IEnumExplorerCommand)


class ExplorerCommand:
    _com_interfaces_ = [shell.IID_IExplorerCommand]
    _public_methods_ = shellcon.IExplorerCommand_Methods

    def __init__(self, cmd):
        self.cmd = cmd

    # The sample also appears to ignore the pidl args!?
    def GetTitle(self, pidl):
        return LoadString(self.cmd.ids)

    def GetToolTip(self, pidl):
        return LoadString(self.cmd.ids_tt)

    def GetIcon(self, pidl):
        # Return a string of the usual "dll,resource_id" format
        # todo - just return any ".ico that comes with python" + ",0" :)
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetState(self, shell_items, slow_ok):
        return shellcon.ECS_ENABLED

    def GetFlags(self):
        return self.cmd.flags

    def GetCanonicalName(self):
        return self.cmd.guid

    def Invoke(self, items, bind_ctx):
        # If no function defined - just return S_OK
        if self.cmd.callback:
            self.cmd.callback(items, bind_ctx)
        else:
            print("No callback for command ", LoadString(self.cmd.ids))

    def EnumSubCommands(self):
        if not self.cmd.children:
            return None
        items = [wrap(ExplorerCommand(c)) for c in self.cmd.children]
        return NewEnum(items, shell.IID_IEnumExplorerCommand)


# end of sample's FVCommands.cpp port


# start of sample's Category.cpp port
class FolderViewCategorizer:
    _com_interfaces_ = [shell.IID_ICategorizer]
    _public_methods_ = shellcon.ICategorizer_Methods

    description = None  # subclasses should set their own

    def __init__(self, shell_folder):
        self.sf = shell_folder

    #  Determines the relative order of two items in their item identifier lists.
    def CompareCategory(self, flags, cat1, cat2):
        return cat1 - cat2

    #  Retrieves the name of a categorizer, such as "Group By Device
    #  Type", that can be displayed in the user interface.
    def GetDescription(self, cch):
        return self.description

    # Retrieves information about a category, such as the default
    # display and the text to display in the user interface.
    def GetCategoryInfo(self, catid):
        # Note: this isn't always appropriate!  See overrides below
        return 0, str(catid)  # ????


class FolderViewCategorizer_Name(FolderViewCategorizer):
    description = "Alphabetical"

    def GetCategory(self, pidls):
        ret = []
        for pidl in pidls:
            val = self.sf.GetDetailsEx(pidl, PKEY_ItemNameDisplay)
            ret.append(val)
        return ret


class FolderViewCategorizer_Size(FolderViewCategorizer):
    description = "Group By Size"

    def GetCategory(self, pidls):
        ret = []
        for pidl in pidls:
            # Why don't we just get the size of the PIDL?
            val = self.sf.GetDetailsEx(pidl, PKEY_Sample_AreaSize)
            val = int(val)  # it probably came in a VT_BSTR variant
            if val < 255 // 3:
                cid = IDS_SMALL
            elif val < 2 * 255 // 3:
                cid = IDS_MEDIUM
            else:
                cid = IDS_LARGE
            ret.append(cid)
        return ret

    def GetCategoryInfo(self, catid):
        return 0, LoadString(catid)


class FolderViewCategorizer_Sides(FolderViewCategorizer):
    description = "Group By Sides"

    def GetCategory(self, pidls):
        ret = []
        for pidl in pidls:
            val = self.sf.GetDetailsEx(pidl, PKEY_ItemNameDisplay)
            if val == 0:
                cid = IDS_CIRCLE
            elif val == 3:
                cid = IDS_TRIANGLE
            elif val == 4:
                cid = IDS_RECTANGLE
            elif val == 5:
                cid = IDS_POLYGON
            else:
                cid = IDS_UNSPECIFIED
            ret.append(cid)
        return ret

    def GetCategoryInfo(self, catid):
        return 0, LoadString(catid)


class FolderViewCategorizer_Value(FolderViewCategorizer):
    description = "Group By Value"

    def GetCategory(self, pidls):
        ret = []
        for pidl in pidls:
            val = self.sf.GetDetailsEx(pidl, PKEY_ItemNameDisplay)
            if val in "one two three four".split():
                ret.append(IDS_LESSTHAN5)
            else:
                ret.append(IDS_5ORGREATER)
        return ret

    def GetCategoryInfo(self, catid):
        return 0, LoadString(catid)


class FolderViewCategorizer_Level(FolderViewCategorizer):
    description = "Group By Value"

    def GetCategory(self, pidls):
        return [
            self.sf.GetDetailsEx(pidl, PKEY_Sample_DirectoryLevel) for pidl in pidls
        ]


class ViewCategoryProvider:
    _com_interfaces_ = [shell.IID_ICategoryProvider]
    _public_methods_ = shellcon.ICategoryProvider_Methods

    def __init__(self, shell_folder):
        self.shell_folder = shell_folder

    def CanCategorizeOnSCID(self, pkey):
        return pkey in [
            PKEY_ItemNameDisplay,
            PKEY_Sample_AreaSize,
            PKEY_Sample_NumberOfSides,
            PKEY_Sample_DirectoryLevel,
        ]

    #  Creates a category object.
    def CreateCategory(self, guid, iid):
        if iid == shell.IID_ICategorizer:
            if guid == CAT_GUID_NAME:
                klass = FolderViewCategorizer_Name
            elif guid == CAT_GUID_SIDES:
                klass = FolderViewCategorizer_Sides
            elif guid == CAT_GUID_SIZE:
                klass = FolderViewCategorizer_Size
            elif guid == CAT_GUID_VALUE:
                klass = FolderViewCategorizer_Value
            elif guid == CAT_GUID_LEVEL:
                klass = FolderViewCategorizer_Level
            else:
                raise COMException(hresult=winerror.E_INVALIDARG)
            return wrap(klass(self.shell_folder))
        raise COMException(hresult=winerror.E_NOINTERFACE)

    #  Retrieves the enumerator for the categories.
    def EnumCategories(self):
        # These are additional categories beyond the columns
        seq = [CAT_GUID_VALUE]
        return NewEnum(seq, pythoncom.IID_IEnumGUID)

    #  Retrieves a globally unique identifier (GUID) that represents
    #  the categorizer to use for the specified Shell column.
    def GetCategoryForSCID(self, scid):
        if scid == PKEY_ItemNameDisplay:
            guid = CAT_GUID_NAME
        elif scid == PKEY_Sample_AreaSize:
            guid = CAT_GUID_SIZE
        elif scid == PKEY_Sample_NumberOfSides:
            guid = CAT_GUID_SIDES
        elif scid == PKEY_Sample_DirectoryLevel:
            guid = CAT_GUID_LEVEL
        elif scid == pythoncom.IID_NULL:
            # This can be called with a NULL
            # format ID. This will happen if you have a category,
            # not based on a column, that gets stored in the
            # property bag. When a return is made to this item,
            # it will call this function with a NULL format id.
            guid = CAT_GUID_VALUE
        else:
            raise COMException(hresult=winerror.E_INVALIDARG)
        return guid

    #  Retrieves the name of the specified category. This is where
    #  additional categories that appear under the column
    #  related categories in the UI, get their display names.
    def GetCategoryName(self, guid, cch):
        if guid == CAT_GUID_VALUE:
            return "Value"
        raise COMException(hresult=winerror.E_FAIL)

    #  Enables the folder to override the default grouping.
    def GetDefaultCategory(self):
        return CAT_GUID_LEVEL, (pythoncom.IID_NULL, 0)


# end of sample's Category.cpp port

# start of sample's ContextMenu.cpp port
MENUVERB_DISPLAY = 0

folderViewImplContextMenuIDs = [
    (
        "display",
        MENUVERB_DISPLAY,
        0,
    ),
]


class ContextMenu:
    _reg_progid_ = "Python.ShellFolderSample.ContextMenu"
    _reg_desc_ = "Python FolderView Context Menu"
    _reg_clsid_ = "{fed40039-021f-4011-87c5-6188b9979764}"
    _com_interfaces_ = [
        shell.IID_IShellExtInit,
        shell.IID_IContextMenu,
        axcontrol.IID_IObjectWithSite,
    ]
    _public_methods_ = (
        shellcon.IContextMenu_Methods
        + shellcon.IShellExtInit_Methods
        + ["GetSite", "SetSite"]
    )
    _context_menu_type_ = "PythonFolderViewSampleType"

    def __init__(self):
        self.site = None
        self.dataobj = None

    def Initialize(self, folder, dataobj, hkey):
        self.dataobj = dataobj

    def QueryContextMenu(self, hMenu, indexMenu, idCmdFirst, idCmdLast, uFlags):
        s = LoadString(IDS_DISPLAY)
        win32gui.InsertMenu(
            hMenu, indexMenu, win32con.MF_BYPOSITION, idCmdFirst + MENUVERB_DISPLAY, s
        )
        indexMenu += 1
        # other verbs could go here...

        # indicate that we added one verb.
        return 1

    def InvokeCommand(self, ci):
        mask, hwnd, verb, params, dir, nShow, hotkey, hicon = ci
        # this seems very convoluted, but it's what the sample does :)
        for verb_name, verb_id, flag in folderViewImplContextMenuIDs:
            if isinstance(verb, int):
                matches = verb == verb_id
            else:
                matches = verb == verb_name
            if matches:
                break
        else:
            raise AssertionError(ci, "failed to find our ID")
        if verb_id == MENUVERB_DISPLAY:
            sia = shell.SHCreateShellItemArrayFromDataObject(self.dataobj)
            DisplayItem(hwnd, sia)
        else:
            raise AssertionError(ci, "Got some verb we weren't expecting?")

    def GetCommandString(self, cmd, typ):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def SetSite(self, site):
        self.site = site

    def GetSite(self, iid):
        return self.site


# end of sample's ContextMenu.cpp port


# start of sample's ShellFolder.cpp port
class ShellFolder:
    _com_interfaces_ = [
        shell.IID_IBrowserFrameOptions,
        pythoncom.IID_IPersist,
        shell.IID_IPersistFolder,
        shell.IID_IPersistFolder2,
        shell.IID_IShellFolder,
        shell.IID_IShellFolder2,
    ]

    _public_methods_ = (
        shellcon.IBrowserFrame_Methods
        + shellcon.IPersistFolder2_Methods
        + shellcon.IShellFolder2_Methods
    )

    _reg_progid_ = "Python.ShellFolderSample.Folder2"
    _reg_desc_ = "Python FolderView sample"
    _reg_clsid_ = "{bb8c24ad-6aaa-4cec-ac5e-c429d5f57627}"

    max_levels = 5

    def __init__(self, level=0):
        self.current_level = level
        self.pidl = None  # set when Initialize is called

    def ParseDisplayName(self, hwnd, reserved, displayName, attr):
        # print("ParseDisplayName", displayName)
        raise COMException(hresult=winerror.E_NOTIMPL)

    def EnumObjects(self, hwndOwner, flags):
        if self.current_level >= self.max_levels:
            return None
        return make_item_enum(self.current_level + 1, flags)

    def BindToObject(self, pidl, bc, iid):
        tail = pidl_to_item(pidl)
        # assert tail['is_folder'], "BindToObject should only be called on folders?"
        # *sob*
        # No point creating object just to have QI fail.
        if iid not in ShellFolder._com_interfaces_:
            raise COMException(hresult=winerror.E_NOTIMPL)
        child = ShellFolder(self.current_level + 1)
        # hrmph - not sure what multiple PIDLs here mean?
        #        assert len(pidl)==1, pidl # expecting just relative child PIDL
        child.Initialize(self.pidl + pidl)
        return wrap(child, iid)

    def BindToStorage(self, pidl, bc, iid):
        return self.BindToObject(pidl, bc, iid)

    def CompareIDs(self, param, id1, id2):
        return 0  # XXX - todo - implement this!

    def CreateViewObject(self, hwnd, iid):
        if iid == shell.IID_IShellView:
            com_folder = wrap(self)
            return shell.SHCreateShellFolderView(com_folder)
        elif iid == shell.IID_ICategoryProvider:
            return wrap(ViewCategoryProvider(self))
        elif iid == shell.IID_IContextMenu:
            ws = wrap(self)
            dcm = (hwnd, None, self.pidl, ws, None)
            return shell.SHCreateDefaultContextMenu(dcm, iid)
        elif iid == shell.IID_IExplorerCommandProvider:
            return wrap(ExplorerCommandProvider())
        else:
            raise COMException(hresult=winerror.E_NOINTERFACE)

    def GetAttributesOf(self, pidls, attrFlags):
        assert len(pidls) == 1, "sample only expects 1 too!"
        assert len(pidls[0]) == 1, "expect relative pidls!"
        item = pidl_to_item(pidls[0])
        flags = 0
        if item["is_folder"]:
            flags |= shellcon.SFGAO_FOLDER
        if item["level"] < self.max_levels:
            flags |= shellcon.SFGAO_HASSUBFOLDER
        return flags

    #  Retrieves an OLE interface that can be used to carry out
    #  actions on the specified file objects or folders.
    def GetUIObjectOf(self, hwndOwner, pidls, iid, inout):
        assert len(pidls) == 1, "oops - aren't expecting more than one!"
        assert len(pidls[0]) == 1, "assuming relative pidls!"
        item = pidl_to_item(pidls[0])
        if iid == shell.IID_IContextMenu:
            ws = wrap(self)
            dcm = (hwndOwner, None, self.pidl, ws, pidls)
            return shell.SHCreateDefaultContextMenu(dcm, iid)
        elif iid == shell.IID_IExtractIconW:
            dxi = shell.SHCreateDefaultExtractIcon()
            # dxi is IDefaultExtractIconInit
            if item["is_folder"]:
                dxi.SetNormalIcon("shell32.dll", 4)
            else:
                dxi.SetNormalIcon("shell32.dll", 1)
            # just return the dxi - let Python QI for IID_IExtractIconW
            return dxi

        elif iid == pythoncom.IID_IDataObject:
            return shell.SHCreateDataObject(self.pidl, pidls, None, iid)

        elif iid == shell.IID_IQueryAssociations:
            elts = []
            if item["is_folder"]:
                elts.append((shellcon.ASSOCCLASS_FOLDER, None, None))
            elts.append(
                (shellcon.ASSOCCLASS_PROGID_STR, None, ContextMenu._context_menu_type_)
            )
            return shell.AssocCreateForClasses(elts, iid)

        raise COMException(hresult=winerror.E_NOINTERFACE)

    #  Retrieves the display name for the specified file object or subfolder.
    def GetDisplayNameOf(self, pidl, flags):
        item = pidl_to_item(pidl)
        if flags & shellcon.SHGDN_FORPARSING:
            if flags & shellcon.SHGDN_INFOLDER:
                return item["name"]
            else:
                if flags & shellcon.SHGDN_FORADDRESSBAR:
                    sigdn = shellcon.SIGDN_DESKTOPABSOLUTEEDITING
                else:
                    sigdn = shellcon.SIGDN_DESKTOPABSOLUTEPARSING
                parent = shell.SHGetNameFromIDList(self.pidl, sigdn)
                return parent + "\\" + item["name"]
        else:
            return item["name"]

    def SetNameOf(self, hwndOwner, pidl, new_name, flags):
        raise COMException(hresult=winerror.E_NOTIMPL)

    def GetClassID(self):
        return self._reg_clsid_

    #  IPersistFolder method
    def Initialize(self, pidl):
        self.pidl = pidl

    #  IShellFolder2 methods
    def EnumSearches(self):
        raise COMException(hresult=winerror.E_NOINTERFACE)

    #  Retrieves the default sorting and display columns.
    def GetDefaultColumn(self, dwres):
        # result is (sort, display)
        return 0, 0

    #  Retrieves the default state for a specified column.
    def GetDefaultColumnState(self, iCol):
        if iCol < 3:
            return shellcon.SHCOLSTATE_ONBYDEFAULT | shellcon.SHCOLSTATE_TYPE_STR
        raise COMException(hresult=winerror.E_INVALIDARG)

    #  Requests the GUID of the default search object for the folder.
    def GetDefaultSearchGUID(self):
        raise COMException(hresult=winerror.E_NOTIMPL)

    #  Helper function for getting the display name for a column.
    def _GetColumnDisplayName(self, pidl, pkey):
        item = pidl_to_item(pidl)
        is_folder = item["is_folder"]
        if pkey == PKEY_ItemNameDisplay:
            val = item["name"]
        elif pkey == PKEY_Sample_AreaSize and not is_folder:
            val = "%d Sq. Ft." % item["size"]
        elif pkey == PKEY_Sample_NumberOfSides and not is_folder:
            val = str(item["sides"])  # not sure why str()
        elif pkey == PKEY_Sample_DirectoryLevel:
            val = str(item["level"])
        else:
            val = ""
        return val

    #  Retrieves detailed information, identified by a
    #  property set ID (FMTID) and property ID (PID),
    #  on an item in a Shell folder.
    def GetDetailsEx(self, pidl, pkey):
        item = pidl_to_item(pidl)
        is_folder = item["is_folder"]
        if not is_folder and pkey == PKEY_PropList_PreviewDetails:
            return "prop:Sample.AreaSize;Sample.NumberOfSides;Sample.DirectoryLevel"
        return self._GetColumnDisplayName(pidl, pkey)

    #  Retrieves detailed information, identified by a
    #  column index, on an item in a Shell folder.
    def GetDetailsOf(self, pidl, iCol):
        key = self.MapColumnToSCID(iCol)
        if pidl is None:
            data = [
                (commctrl.LVCFMT_LEFT, "Name"),
                (commctrl.LVCFMT_CENTER, "Size"),
                (commctrl.LVCFMT_CENTER, "Sides"),
                (commctrl.LVCFMT_CENTER, "Level"),
            ]
            if iCol >= len(data):
                raise COMException(hresult=winerror.E_FAIL)
            fmt, val = data[iCol]
        else:
            fmt = 0  # ?
            val = self._GetColumnDisplayName(pidl, key)
        cxChar = 24
        return fmt, cxChar, val

    #  Converts a column name to the appropriate
    #  property set ID (FMTID) and property ID (PID).
    def MapColumnToSCID(self, iCol):
        data = [
            PKEY_ItemNameDisplay,
            PKEY_Sample_AreaSize,
            PKEY_Sample_NumberOfSides,
            PKEY_Sample_DirectoryLevel,
        ]
        if iCol >= len(data):
            raise COMException(hresult=winerror.E_FAIL)
        return data[iCol]

    #  IPersistFolder2 methods
    #  Retrieves the PIDLIST_ABSOLUTE for the folder object.
    def GetCurFolder(self):
        # The docs say this is OK, but I suspect it's a problem in this case :)
        # assert self.pidl, "haven't been initialized?"
        return self.pidl


# end of sample's ShellFolder.cpp port


def get_schema_fname():
    me = win32api.GetFullPathName(__file__)
    sc = os.path.splitext(me)[0] + ".propdesc"
    assert os.path.isfile(sc), sc
    return sc


def DllRegisterServer():
    import winreg

    if sys.getwindowsversion()[0] < 6:
        print("This sample only works on Vista")
        sys.exit(1)

    key = winreg.CreateKey(
        winreg.HKEY_LOCAL_MACHINE,
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
        "Explorer\\Desktop\\Namespace\\" + ShellFolder._reg_clsid_,
    )
    winreg.SetValueEx(key, None, 0, winreg.REG_SZ, ShellFolder._reg_desc_)
    # And special shell keys under our CLSID
    key = winreg.CreateKey(
        winreg.HKEY_CLASSES_ROOT, "CLSID\\" + ShellFolder._reg_clsid_ + "\\ShellFolder"
    )
    # 'Attributes' is an int stored as a binary! use struct
    attr = (
        shellcon.SFGAO_FOLDER | shellcon.SFGAO_HASSUBFOLDER | shellcon.SFGAO_BROWSABLE
    )
    import struct

    s = struct.pack("i", attr)
    winreg.SetValueEx(key, "Attributes", 0, winreg.REG_BINARY, s)
    # register the context menu handler under the FolderViewSampleType type.
    keypath = "{}\\shellex\\ContextMenuHandlers\\{}".format(
        ContextMenu._context_menu_type_,
        ContextMenu._reg_desc_,
    )
    key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, keypath)
    winreg.SetValueEx(key, None, 0, winreg.REG_SZ, ContextMenu._reg_clsid_)
    propsys.PSRegisterPropertySchema(get_schema_fname())
    print(ShellFolder._reg_desc_, "registration complete.")


def DllUnregisterServer():
    import winreg

    paths = [
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Desktop\\Namespace\\"
        + ShellFolder._reg_clsid_,
        "{}\\shellex\\ContextMenuHandlers\\{}".format(
            ContextMenu._context_menu_type_, ContextMenu._reg_desc_
        ),
    ]
    for path in paths:
        try:
            winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, path)
        except OSError as details:
            import errno

            if details.errno != errno.ENOENT:
                print(f"FAILED to remove {path}: {details}")

    propsys.PSUnregisterPropertySchema(get_schema_fname())
    print(ShellFolder._reg_desc_, "unregistration complete.")


if __name__ == "__main__":
    from win32com.server import register

    register.UseCommandLine(
        ShellFolder,
        ContextMenu,
        debug=debug,
        finalize_register=DllRegisterServer,
        finalize_unregister=DllUnregisterServer,
    )

# === NexusCore/openenv\Lib\site-packages\openai\resources\vector_stores\vector_stores.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Optional
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from .files import (
    Files,
    AsyncFiles,
    FilesWithRawResponse,
    AsyncFilesWithRawResponse,
    FilesWithStreamingResponse,
    AsyncFilesWithStreamingResponse,
)
from ...types import (
    FileChunkingStrategyParam,
    vector_store_list_params,
    vector_store_create_params,
    vector_store_search_params,
    vector_store_update_params,
)
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...pagination import SyncPage, AsyncPage, SyncCursorPage, AsyncCursorPage
from .file_batches import (
    FileBatches,
    AsyncFileBatches,
    FileBatchesWithRawResponse,
    AsyncFileBatchesWithRawResponse,
    FileBatchesWithStreamingResponse,
    AsyncFileBatchesWithStreamingResponse,
)
from ..._base_client import AsyncPaginator, make_request_options
from ...types.vector_store import VectorStore
from ...types.vector_store_deleted import VectorStoreDeleted
from ...types.shared_params.metadata import Metadata
from ...types.file_chunking_strategy_param import FileChunkingStrategyParam
from ...types.vector_store_search_response import VectorStoreSearchResponse

__all__ = ["VectorStores", "AsyncVectorStores"]


class VectorStores(SyncAPIResource):
    @cached_property
    def files(self) -> Files:
        return Files(self._client)

    @cached_property
    def file_batches(self) -> FileBatches:
        return FileBatches(self._client)

    @cached_property
    def with_raw_response(self) -> VectorStoresWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return VectorStoresWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> VectorStoresWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return VectorStoresWithStreamingResponse(self)

    def create(
        self,
        *,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
        expires_after: vector_store_create_params.ExpiresAfter | NotGiven = NOT_GIVEN,
        file_ids: List[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Create a vector store.

        Args:
          chunking_strategy: The chunking strategy used to chunk the file(s). If not set, will use the `auto`
              strategy. Only applicable if `file_ids` is non-empty.

          expires_after: The expiration policy for a vector store.

          file_ids: A list of [File](https://platform.openai.com/docs/api-reference/files) IDs that
              the vector store should use. Useful for tools like `file_search` that can access
              files.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the vector store.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/vector_stores",
            body=maybe_transform(
                {
                    "chunking_strategy": chunking_strategy,
                    "expires_after": expires_after,
                    "file_ids": file_ids,
                    "metadata": metadata,
                    "name": name,
                },
                vector_store_create_params.VectorStoreCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    def retrieve(
        self,
        vector_store_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Retrieves a vector store.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/vector_stores/{vector_store_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    def update(
        self,
        vector_store_id: str,
        *,
        expires_after: Optional[vector_store_update_params.ExpiresAfter] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Modifies a vector store.

        Args:
          expires_after: The expiration policy for a vector store.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the vector store.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/vector_stores/{vector_store_id}",
            body=maybe_transform(
                {
                    "expires_after": expires_after,
                    "metadata": metadata,
                    "name": name,
                },
                vector_store_update_params.VectorStoreUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[VectorStore]:
        """Returns a list of vector stores.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            "/vector_stores",
            page=SyncCursorPage[VectorStore],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    vector_store_list_params.VectorStoreListParams,
                ),
            ),
            model=VectorStore,
        )

    def delete(
        self,
        vector_store_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreDeleted:
        """
        Delete a vector store.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._delete(
            f"/vector_stores/{vector_store_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreDeleted,
        )

    def search(
        self,
        vector_store_id: str,
        *,
        query: Union[str, List[str]],
        filters: vector_store_search_params.Filters | NotGiven = NOT_GIVEN,
        max_num_results: int | NotGiven = NOT_GIVEN,
        ranking_options: vector_store_search_params.RankingOptions | NotGiven = NOT_GIVEN,
        rewrite_query: bool | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncPage[VectorStoreSearchResponse]:
        """
        Search a vector store for relevant chunks based on a query and file attributes
        filter.

        Args:
          query: A query string for a search

          filters: A filter to apply based on file attributes.

          max_num_results: The maximum number of results to return. This number should be between 1 and 50
              inclusive.

          ranking_options: Ranking options for search.

          rewrite_query: Whether to rewrite the natural language query for vector search.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/search",
            page=SyncPage[VectorStoreSearchResponse],
            body=maybe_transform(
                {
                    "query": query,
                    "filters": filters,
                    "max_num_results": max_num_results,
                    "ranking_options": ranking_options,
                    "rewrite_query": rewrite_query,
                },
                vector_store_search_params.VectorStoreSearchParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=VectorStoreSearchResponse,
            method="post",
        )


class AsyncVectorStores(AsyncAPIResource):
    @cached_property
    def files(self) -> AsyncFiles:
        return AsyncFiles(self._client)

    @cached_property
    def file_batches(self) -> AsyncFileBatches:
        return AsyncFileBatches(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncVectorStoresWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncVectorStoresWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncVectorStoresWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncVectorStoresWithStreamingResponse(self)

    async def create(
        self,
        *,
        chunking_strategy: FileChunkingStrategyParam | NotGiven = NOT_GIVEN,
        expires_after: vector_store_create_params.ExpiresAfter | NotGiven = NOT_GIVEN,
        file_ids: List[str] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Create a vector store.

        Args:
          chunking_strategy: The chunking strategy used to chunk the file(s). If not set, will use the `auto`
              strategy. Only applicable if `file_ids` is non-empty.

          expires_after: The expiration policy for a vector store.

          file_ids: A list of [File](https://platform.openai.com/docs/api-reference/files) IDs that
              the vector store should use. Useful for tools like `file_search` that can access
              files.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the vector store.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/vector_stores",
            body=await async_maybe_transform(
                {
                    "chunking_strategy": chunking_strategy,
                    "expires_after": expires_after,
                    "file_ids": file_ids,
                    "metadata": metadata,
                    "name": name,
                },
                vector_store_create_params.VectorStoreCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    async def retrieve(
        self,
        vector_store_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Retrieves a vector store.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/vector_stores/{vector_store_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    async def update(
        self,
        vector_store_id: str,
        *,
        expires_after: Optional[vector_store_update_params.ExpiresAfter] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        name: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStore:
        """
        Modifies a vector store.

        Args:
          expires_after: The expiration policy for a vector store.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          name: The name of the vector store.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/vector_stores/{vector_store_id}",
            body=await async_maybe_transform(
                {
                    "expires_after": expires_after,
                    "metadata": metadata,
                    "name": name,
                },
                vector_store_update_params.VectorStoreUpdateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStore,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[VectorStore, AsyncCursorPage[VectorStore]]:
        """Returns a list of vector stores.

        Args:
          after: A cursor for use in pagination.

        `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            "/vector_stores",
            page=AsyncCursorPage[VectorStore],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                    },
                    vector_store_list_params.VectorStoreListParams,
                ),
            ),
            model=VectorStore,
        )

    async def delete(
        self,
        vector_store_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VectorStoreDeleted:
        """
        Delete a vector store.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._delete(
            f"/vector_stores/{vector_store_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=VectorStoreDeleted,
        )

    def search(
        self,
        vector_store_id: str,
        *,
        query: Union[str, List[str]],
        filters: vector_store_search_params.Filters | NotGiven = NOT_GIVEN,
        max_num_results: int | NotGiven = NOT_GIVEN,
        ranking_options: vector_store_search_params.RankingOptions | NotGiven = NOT_GIVEN,
        rewrite_query: bool | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[VectorStoreSearchResponse, AsyncPage[VectorStoreSearchResponse]]:
        """
        Search a vector store for relevant chunks based on a query and file attributes
        filter.

        Args:
          query: A query string for a search

          filters: A filter to apply based on file attributes.

          max_num_results: The maximum number of results to return. This number should be between 1 and 50
              inclusive.

          ranking_options: Ranking options for search.

          rewrite_query: Whether to rewrite the natural language query for vector search.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not vector_store_id:
            raise ValueError(f"Expected a non-empty value for `vector_store_id` but received {vector_store_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/vector_stores/{vector_store_id}/search",
            page=AsyncPage[VectorStoreSearchResponse],
            body=maybe_transform(
                {
                    "query": query,
                    "filters": filters,
                    "max_num_results": max_num_results,
                    "ranking_options": ranking_options,
                    "rewrite_query": rewrite_query,
                },
                vector_store_search_params.VectorStoreSearchParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=VectorStoreSearchResponse,
            method="post",
        )


class VectorStoresWithRawResponse:
    def __init__(self, vector_stores: VectorStores) -> None:
        self._vector_stores = vector_stores

        self.create = _legacy_response.to_raw_response_wrapper(
            vector_stores.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            vector_stores.retrieve,
        )
        self.update = _legacy_response.to_raw_response_wrapper(
            vector_stores.update,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            vector_stores.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            vector_stores.delete,
        )
        self.search = _legacy_response.to_raw_response_wrapper(
            vector_stores.search,
        )

    @cached_property
    def files(self) -> FilesWithRawResponse:
        return FilesWithRawResponse(self._vector_stores.files)

    @cached_property
    def file_batches(self) -> FileBatchesWithRawResponse:
        return FileBatchesWithRawResponse(self._vector_stores.file_batches)


class AsyncVectorStoresWithRawResponse:
    def __init__(self, vector_stores: AsyncVectorStores) -> None:
        self._vector_stores = vector_stores

        self.create = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.retrieve,
        )
        self.update = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.update,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.delete,
        )
        self.search = _legacy_response.async_to_raw_response_wrapper(
            vector_stores.search,
        )

    @cached_property
    def files(self) -> AsyncFilesWithRawResponse:
        return AsyncFilesWithRawResponse(self._vector_stores.files)

    @cached_property
    def file_batches(self) -> AsyncFileBatchesWithRawResponse:
        return AsyncFileBatchesWithRawResponse(self._vector_stores.file_batches)


class VectorStoresWithStreamingResponse:
    def __init__(self, vector_stores: VectorStores) -> None:
        self._vector_stores = vector_stores

        self.create = to_streamed_response_wrapper(
            vector_stores.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            vector_stores.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            vector_stores.update,
        )
        self.list = to_streamed_response_wrapper(
            vector_stores.list,
        )
        self.delete = to_streamed_response_wrapper(
            vector_stores.delete,
        )
        self.search = to_streamed_response_wrapper(
            vector_stores.search,
        )

    @cached_property
    def files(self) -> FilesWithStreamingResponse:
        return FilesWithStreamingResponse(self._vector_stores.files)

    @cached_property
    def file_batches(self) -> FileBatchesWithStreamingResponse:
        return FileBatchesWithStreamingResponse(self._vector_stores.file_batches)


class AsyncVectorStoresWithStreamingResponse:
    def __init__(self, vector_stores: AsyncVectorStores) -> None:
        self._vector_stores = vector_stores

        self.create = async_to_streamed_response_wrapper(
            vector_stores.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            vector_stores.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            vector_stores.update,
        )
        self.list = async_to_streamed_response_wrapper(
            vector_stores.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            vector_stores.delete,
        )
        self.search = async_to_streamed_response_wrapper(
            vector_stores.search,
        )

    @cached_property
    def files(self) -> AsyncFilesWithStreamingResponse:
        return AsyncFilesWithStreamingResponse(self._vector_stores.files)

    @cached_property
    def file_batches(self) -> AsyncFileBatchesWithStreamingResponse:
        return AsyncFileBatchesWithStreamingResponse(self._vector_stores.file_batches)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\metadata.py ===
from __future__ import annotations

import email.feedparser
import email.header
import email.message
import email.parser
import email.policy
import pathlib
import sys
import typing
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    TypedDict,
    cast,
)

from . import licenses, requirements, specifiers, utils
from . import version as version_module
from .licenses import NormalizedLicenseExpression

T = typing.TypeVar("T")


if sys.version_info >= (3, 11):  # pragma: no cover
    ExceptionGroup = ExceptionGroup
else:  # pragma: no cover

    class ExceptionGroup(Exception):
        """A minimal implementation of :external:exc:`ExceptionGroup` from Python 3.11.

        If :external:exc:`ExceptionGroup` is already defined by Python itself,
        that version is used instead.
        """

        message: str
        exceptions: list[Exception]

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            self.message = message
            self.exceptions = exceptions

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.message!r}, {self.exceptions!r})"


class InvalidMetadata(ValueError):
    """A metadata field contains invalid data."""

    field: str
    """The name of the field that contains invalid data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


# The RawMetadata class attempts to make as few assumptions about the underlying
# serialization formats as possible. The idea is that as long as a serialization
# formats offer some very basic primitives in *some* way then we can support
# serializing to and from that format.
class RawMetadata(TypedDict, total=False):
    """A dictionary of raw core metadata.

    Each field in core metadata maps to a key of this dictionary (when data is
    provided). The key is lower-case and underscores are used instead of dashes
    compared to the equivalent core metadata field. Any core metadata field that
    can be specified multiple times or can hold multiple values in a single
    field have a key with a plural name. See :class:`Metadata` whose attributes
    match the keys of this dictionary.

    Core metadata fields that can be specified multiple times are stored as a
    list or dict depending on which is appropriate for the field. Any fields
    which hold multiple values in a single field are stored as a list.

    """

    # Metadata 1.0 - PEP 241
    metadata_version: str
    name: str
    version: str
    platforms: list[str]
    summary: str
    description: str
    keywords: list[str]
    home_page: str
    author: str
    author_email: str
    license: str

    # Metadata 1.1 - PEP 314
    supported_platforms: list[str]
    download_url: str
    classifiers: list[str]
    requires: list[str]
    provides: list[str]
    obsoletes: list[str]

    # Metadata 1.2 - PEP 345
    maintainer: str
    maintainer_email: str
    requires_dist: list[str]
    provides_dist: list[str]
    obsoletes_dist: list[str]
    requires_python: str
    requires_external: list[str]
    project_urls: dict[str, str]

    # Metadata 2.0
    # PEP 426 attempted to completely revamp the metadata format
    # but got stuck without ever being able to build consensus on
    # it and ultimately ended up withdrawn.
    #
    # However, a number of tools had started emitting METADATA with
    # `2.0` Metadata-Version, so for historical reasons, this version
    # was skipped.

    # Metadata 2.1 - PEP 566
    description_content_type: str
    provides_extra: list[str]

    # Metadata 2.2 - PEP 643
    dynamic: list[str]

    # Metadata 2.3 - PEP 685
    # No new fields were added in PEP 685, just some edge case were
    # tightened up to provide better interoptability.

    # Metadata 2.4 - PEP 639
    license_expression: str
    license_files: list[str]


_STRING_FIELDS = {
    "author",
    "author_email",
    "description",
    "description_content_type",
    "download_url",
    "home_page",
    "license",
    "license_expression",
    "maintainer",
    "maintainer_email",
    "metadata_version",
    "name",
    "requires_python",
    "summary",
    "version",
}

_LIST_FIELDS = {
    "classifiers",
    "dynamic",
    "license_files",
    "obsoletes",
    "obsoletes_dist",
    "platforms",
    "provides",
    "provides_dist",
    "provides_extra",
    "requires",
    "requires_dist",
    "requires_external",
    "supported_platforms",
}

_DICT_FIELDS = {
    "project_urls",
}


def _parse_keywords(data: str) -> list[str]:
    """Split a string of comma-separated keywords into a list of keywords."""
    return [k.strip() for k in data.split(",")]


def _parse_project_urls(data: list[str]) -> dict[str, str]:
    """Parse a list of label/URL string pairings separated by a comma."""
    urls = {}
    for pair in data:
        # Our logic is slightly tricky here as we want to try and do
        # *something* reasonable with malformed data.
        #
        # The main thing that we have to worry about, is data that does
        # not have a ',' at all to split the label from the Value. There
        # isn't a singular right answer here, and we will fail validation
        # later on (if the caller is validating) so it doesn't *really*
        # matter, but since the missing value has to be an empty str
        # and our return value is dict[str, str], if we let the key
        # be the missing value, then they'd have multiple '' values that
        # overwrite each other in a accumulating dict.
        #
        # The other potentional issue is that it's possible to have the
        # same label multiple times in the metadata, with no solid "right"
        # answer with what to do in that case. As such, we'll do the only
        # thing we can, which is treat the field as unparseable and add it
        # to our list of unparsed fields.
        parts = [p.strip() for p in pair.split(",", 1)]
        parts.extend([""] * (max(0, 2 - len(parts))))  # Ensure 2 items

        # TODO: The spec doesn't say anything about if the keys should be
        #       considered case sensitive or not... logically they should
        #       be case-preserving and case-insensitive, but doing that
        #       would open up more cases where we might have duplicate
        #       entries.
        label, url = parts
        if label in urls:
            # The label already exists in our set of urls, so this field
            # is unparseable, and we can just add the whole thing to our
            # unparseable data and stop processing it.
            raise KeyError("duplicate labels in project urls")
        urls[label] = url

    return urls


def _get_payload(msg: email.message.Message, source: bytes | str) -> str:
    """Get the body of the message."""
    # If our source is a str, then our caller has managed encodings for us,
    # and we don't need to deal with it.
    if isinstance(source, str):
        payload = msg.get_payload()
        assert isinstance(payload, str)
        return payload
    # If our source is a bytes, then we're managing the encoding and we need
    # to deal with it.
    else:
        bpayload = msg.get_payload(decode=True)
        assert isinstance(bpayload, bytes)
        try:
            return bpayload.decode("utf8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("payload in an invalid encoding") from exc


# The various parse_FORMAT functions here are intended to be as lenient as
# possible in their parsing, while still returning a correctly typed
# RawMetadata.
#
# To aid in this, we also generally want to do as little touching of the
# data as possible, except where there are possibly some historic holdovers
# that make valid data awkward to work with.
#
# While this is a lower level, intermediate format than our ``Metadata``
# class, some light touch ups can make a massive difference in usability.

# Map METADATA fields to RawMetadata.
_EMAIL_TO_RAW_MAPPING = {
    "author": "author",
    "author-email": "author_email",
    "classifier": "classifiers",
    "description": "description",
    "description-content-type": "description_content_type",
    "download-url": "download_url",
    "dynamic": "dynamic",
    "home-page": "home_page",
    "keywords": "keywords",
    "license": "license",
    "license-expression": "license_expression",
    "license-file": "license_files",
    "maintainer": "maintainer",
    "maintainer-email": "maintainer_email",
    "metadata-version": "metadata_version",
    "name": "name",
    "obsoletes": "obsoletes",
    "obsoletes-dist": "obsoletes_dist",
    "platform": "platforms",
    "project-url": "project_urls",
    "provides": "provides",
    "provides-dist": "provides_dist",
    "provides-extra": "provides_extra",
    "requires": "requires",
    "requires-dist": "requires_dist",
    "requires-external": "requires_external",
    "requires-python": "requires_python",
    "summary": "summary",
    "supported-platform": "supported_platforms",
    "version": "version",
}
_RAW_TO_EMAIL_MAPPING = {raw: email for email, raw in _EMAIL_TO_RAW_MAPPING.items()}


def parse_email(data: bytes | str) -> tuple[RawMetadata, dict[str, list[str]]]:
    """Parse a distribution's metadata stored as email headers (e.g. from ``METADATA``).

    This function returns a two-item tuple of dicts. The first dict is of
    recognized fields from the core metadata specification. Fields that can be
    parsed and translated into Python's built-in types are converted
    appropriately. All other fields are left as-is. Fields that are allowed to
    appear multiple times are stored as lists.

    The second dict contains all other fields from the metadata. This includes
    any unrecognized fields. It also includes any fields which are expected to
    be parsed into a built-in type but were not formatted appropriately. Finally,
    any fields that are expected to appear only once but are repeated are
    included in this dict.

    """
    raw: dict[str, str | list[str] | dict[str, str]] = {}
    unparsed: dict[str, list[str]] = {}

    if isinstance(data, str):
        parsed = email.parser.Parser(policy=email.policy.compat32).parsestr(data)
    else:
        parsed = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(data)

    # We have to wrap parsed.keys() in a set, because in the case of multiple
    # values for a key (a list), the key will appear multiple times in the
    # list of keys, but we're avoiding that by using get_all().
    for name in frozenset(parsed.keys()):
        # Header names in RFC are case insensitive, so we'll normalize to all
        # lower case to make comparisons easier.
        name = name.lower()

        # We use get_all() here, even for fields that aren't multiple use,
        # because otherwise someone could have e.g. two Name fields, and we
        # would just silently ignore it rather than doing something about it.
        headers = parsed.get_all(name) or []

        # The way the email module works when parsing bytes is that it
        # unconditionally decodes the bytes as ascii using the surrogateescape
        # handler. When you pull that data back out (such as with get_all() ),
        # it looks to see if the str has any surrogate escapes, and if it does
        # it wraps it in a Header object instead of returning the string.
        #
        # As such, we'll look for those Header objects, and fix up the encoding.
        value = []
        # Flag if we have run into any issues processing the headers, thus
        # signalling that the data belongs in 'unparsed'.
        valid_encoding = True
        for h in headers:
            # It's unclear if this can return more types than just a Header or
            # a str, so we'll just assert here to make sure.
            assert isinstance(h, (email.header.Header, str))

            # If it's a header object, we need to do our little dance to get
            # the real data out of it. In cases where there is invalid data
            # we're going to end up with mojibake, but there's no obvious, good
            # way around that without reimplementing parts of the Header object
            # ourselves.
            #
            # That should be fine since, if mojibacked happens, this key is
            # going into the unparsed dict anyways.
            if isinstance(h, email.header.Header):
                # The Header object stores it's data as chunks, and each chunk
                # can be independently encoded, so we'll need to check each
                # of them.
                chunks: list[tuple[bytes, str | None]] = []
                for bin, encoding in email.header.decode_header(h):
                    try:
                        bin.decode("utf8", "strict")
                    except UnicodeDecodeError:
                        # Enable mojibake.
                        encoding = "latin1"
                        valid_encoding = False
                    else:
                        encoding = "utf8"
                    chunks.append((bin, encoding))

                # Turn our chunks back into a Header object, then let that
                # Header object do the right thing to turn them into a
                # string for us.
                value.append(str(email.header.make_header(chunks)))
            # This is already a string, so just add it.
            else:
                value.append(h)

        # We've processed all of our values to get them into a list of str,
        # but we may have mojibake data, in which case this is an unparsed
        # field.
        if not valid_encoding:
            unparsed[name] = value
            continue

        raw_name = _EMAIL_TO_RAW_MAPPING.get(name)
        if raw_name is None:
            # This is a bit of a weird situation, we've encountered a key that
            # we don't know what it means, so we don't know whether it's meant
            # to be a list or not.
            #
            # Since we can't really tell one way or another, we'll just leave it
            # as a list, even though it may be a single item list, because that's
            # what makes the most sense for email headers.
            unparsed[name] = value
            continue

        # If this is one of our string fields, then we'll check to see if our
        # value is a list of a single item. If it is then we'll assume that
        # it was emitted as a single string, and unwrap the str from inside
        # the list.
        #
        # If it's any other kind of data, then we haven't the faintest clue
        # what we should parse it as, and we have to just add it to our list
        # of unparsed stuff.
        if raw_name in _STRING_FIELDS and len(value) == 1:
            raw[raw_name] = value[0]
        # If this is one of our list of string fields, then we can just assign
        # the value, since email *only* has strings, and our get_all() call
        # above ensures that this is a list.
        elif raw_name in _LIST_FIELDS:
            raw[raw_name] = value
        # Special Case: Keywords
        # The keywords field is implemented in the metadata spec as a str,
        # but it conceptually is a list of strings, and is serialized using
        # ", ".join(keywords), so we'll do some light data massaging to turn
        # this into what it logically is.
        elif raw_name == "keywords" and len(value) == 1:
            raw[raw_name] = _parse_keywords(value[0])
        # Special Case: Project-URL
        # The project urls is implemented in the metadata spec as a list of
        # specially-formatted strings that represent a key and a value, which
        # is fundamentally a mapping, however the email format doesn't support
        # mappings in a sane way, so it was crammed into a list of strings
        # instead.
        #
        # We will do a little light data massaging to turn this into a map as
        # it logically should be.
        elif raw_name == "project_urls":
            try:
                raw[raw_name] = _parse_project_urls(value)
            except KeyError:
                unparsed[name] = value
        # Nothing that we've done has managed to parse this, so it'll just
        # throw it in our unparseable data and move on.
        else:
            unparsed[name] = value

    # We need to support getting the Description from the message payload in
    # addition to getting it from the the headers. This does mean, though, there
    # is the possibility of it being set both ways, in which case we put both
    # in 'unparsed' since we don't know which is right.
    try:
        payload = _get_payload(parsed, data)
    except ValueError:
        unparsed.setdefault("description", []).append(
            parsed.get_payload(decode=isinstance(data, bytes))  # type: ignore[call-overload]
        )
    else:
        if payload:
            # Check to see if we've already got a description, if so then both
            # it, and this body move to unparseable.
            if "description" in raw:
                description_header = cast(str, raw.pop("description"))
                unparsed.setdefault("description", []).extend(
                    [description_header, payload]
                )
            elif "description" in unparsed:
                unparsed["description"].append(payload)
            else:
                raw["description"] = payload

    # We need to cast our `raw` to a metadata, because a TypedDict only support
    # literal key names, but we're computing our key names on purpose, but the
    # way this function is implemented, our `TypedDict` can only have valid key
    # names.
    return cast(RawMetadata, raw), unparsed


_NOT_FOUND = object()


# Keep the two values in sync.
_VALID_METADATA_VERSIONS = ["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]
_MetadataVersion = Literal["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]

_REQUIRED_ATTRS = frozenset(["metadata_version", "name", "version"])


class _Validator(Generic[T]):
    """Validate a metadata field.

    All _process_*() methods correspond to a core metadata field. The method is
    called with the field's raw value. If the raw value is valid it is returned
    in its "enriched" form (e.g. ``version.Version`` for the ``Version`` field).
    If the raw value is invalid, :exc:`InvalidMetadata` is raised (with a cause
    as appropriate).
    """

    name: str
    raw_name: str
    added: _MetadataVersion

    def __init__(
        self,
        *,
        added: _MetadataVersion = "1.0",
    ) -> None:
        self.added = added

    def __set_name__(self, _owner: Metadata, name: str) -> None:
        self.name = name
        self.raw_name = _RAW_TO_EMAIL_MAPPING[name]

    def __get__(self, instance: Metadata, _owner: type[Metadata]) -> T:
        # With Python 3.8, the caching can be replaced with functools.cached_property().
        # No need to check the cache as attribute lookup will resolve into the
        # instance's __dict__ before __get__ is called.
        cache = instance.__dict__
        value = instance._raw.get(self.name)

        # To make the _process_* methods easier, we'll check if the value is None
        # and if this field is NOT a required attribute, and if both of those
        # things are true, we'll skip the the converter. This will mean that the
        # converters never have to deal with the None union.
        if self.name in _REQUIRED_ATTRS or value is not None:
            try:
                converter: Callable[[Any], T] = getattr(self, f"_process_{self.name}")
            except AttributeError:
                pass
            else:
                value = converter(value)

        cache[self.name] = value
        try:
            del instance._raw[self.name]  # type: ignore[misc]
        except KeyError:
            pass

        return cast(T, value)

    def _invalid_metadata(
        self, msg: str, cause: Exception | None = None
    ) -> InvalidMetadata:
        exc = InvalidMetadata(
            self.raw_name, msg.format_map({"field": repr(self.raw_name)})
        )
        exc.__cause__ = cause
        return exc

    def _process_metadata_version(self, value: str) -> _MetadataVersion:
        # Implicitly makes Metadata-Version required.
        if value not in _VALID_METADATA_VERSIONS:
            raise self._invalid_metadata(f"{value!r} is not a valid metadata version")
        return cast(_MetadataVersion, value)

    def _process_name(self, value: str) -> str:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        # Validate the name as a side-effect.
        try:
            utils.canonicalize_name(value, validate=True)
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return value

    def _process_version(self, value: str) -> version_module.Version:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        try:
            return version_module.parse(value)
        except version_module.InvalidVersion as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_summary(self, value: str) -> str:
        """Check the field contains no newlines."""
        if "\n" in value:
            raise self._invalid_metadata("{field} must be a single line")
        return value

    def _process_description_content_type(self, value: str) -> str:
        content_types = {"text/plain", "text/x-rst", "text/markdown"}
        message = email.message.EmailMessage()
        message["content-type"] = value

        content_type, parameters = (
            # Defaults to `text/plain` if parsing failed.
            message.get_content_type().lower(),
            message["content-type"].params,
        )
        # Check if content-type is valid or defaulted to `text/plain` and thus was
        # not parseable.
        if content_type not in content_types or content_type not in value.lower():
            raise self._invalid_metadata(
                f"{{field}} must be one of {list(content_types)}, not {value!r}"
            )

        charset = parameters.get("charset", "UTF-8")
        if charset != "UTF-8":
            raise self._invalid_metadata(
                f"{{field}} can only specify the UTF-8 charset, not {list(charset)}"
            )

        markdown_variants = {"GFM", "CommonMark"}
        variant = parameters.get("variant", "GFM")  # Use an acceptable default.
        if content_type == "text/markdown" and variant not in markdown_variants:
            raise self._invalid_metadata(
                f"valid Markdown variants for {{field}} are {list(markdown_variants)}, "
                f"not {variant!r}",
            )
        return value

    def _process_dynamic(self, value: list[str]) -> list[str]:
        for dynamic_field in map(str.lower, value):
            if dynamic_field in {"name", "version", "metadata-version"}:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not allowed as a dynamic field"
                )
            elif dynamic_field not in _EMAIL_TO_RAW_MAPPING:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not a valid dynamic field"
                )
        return list(map(str.lower, value))

    def _process_provides_extra(
        self,
        value: list[str],
    ) -> list[utils.NormalizedName]:
        normalized_names = []
        try:
            for name in value:
                normalized_names.append(utils.canonicalize_name(name, validate=True))
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{name!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return normalized_names

    def _process_requires_python(self, value: str) -> specifiers.SpecifierSet:
        try:
            return specifiers.SpecifierSet(value)
        except specifiers.InvalidSpecifier as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_requires_dist(
        self,
        value: list[str],
    ) -> list[requirements.Requirement]:
        reqs = []
        try:
            for req in value:
                reqs.append(requirements.Requirement(req))
        except requirements.InvalidRequirement as exc:
            raise self._invalid_metadata(
                f"{req!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return reqs

    def _process_license_expression(
        self, value: str
    ) -> NormalizedLicenseExpression | None:
        try:
            return licenses.canonicalize_license_expression(value)
        except ValueError as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_license_files(self, value: list[str]) -> list[str]:
        paths = []
        for path in value:
            if ".." in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "parent directory indicators are not allowed"
                )
            if "*" in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be resolved"
                )
            if (
                pathlib.PurePosixPath(path).is_absolute()
                or pathlib.PureWindowsPath(path).is_absolute()
            ):
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be relative"
                )
            if pathlib.PureWindowsPath(path).as_posix() != path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "paths must use '/' delimiter"
                )
            paths.append(path)
        return paths


class Metadata:
    """Representation of distribution metadata.

    Compared to :class:`RawMetadata`, this class provides objects representing
    metadata fields instead of only using built-in types. Any invalid metadata
    will cause :exc:`InvalidMetadata` to be raised (with a
    :py:attr:`~BaseException.__cause__` attribute as appropriate).
    """

    _raw: RawMetadata

    @classmethod
    def from_raw(cls, data: RawMetadata, *, validate: bool = True) -> Metadata:
        """Create an instance from :class:`RawMetadata`.

        If *validate* is true, all metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        ins = cls()
        ins._raw = data.copy()  # Mutations occur due to caching enriched values.

        if validate:
            exceptions: list[Exception] = []
            try:
                metadata_version = ins.metadata_version
                metadata_age = _VALID_METADATA_VERSIONS.index(metadata_version)
            except InvalidMetadata as metadata_version_exc:
                exceptions.append(metadata_version_exc)
                metadata_version = None

            # Make sure to check for the fields that are present, the required
            # fields (so their absence can be reported).
            fields_to_check = frozenset(ins._raw) | _REQUIRED_ATTRS
            # Remove fields that have already been checked.
            fields_to_check -= {"metadata_version"}

            for key in fields_to_check:
                try:
                    if metadata_version:
                        # Can't use getattr() as that triggers descriptor protocol which
                        # will fail due to no value for the instance argument.
                        try:
                            field_metadata_version = cls.__dict__[key].added
                        except KeyError:
                            exc = InvalidMetadata(key, f"unrecognized field: {key!r}")
                            exceptions.append(exc)
                            continue
                        field_age = _VALID_METADATA_VERSIONS.index(
                            field_metadata_version
                        )
                        if field_age > metadata_age:
                            field = _RAW_TO_EMAIL_MAPPING[key]
                            exc = InvalidMetadata(
                                field,
                                f"{field} introduced in metadata version "
                                f"{field_metadata_version}, not {metadata_version}",
                            )
                            exceptions.append(exc)
                            continue
                    getattr(ins, key)
                except InvalidMetadata as exc:
                    exceptions.append(exc)

            if exceptions:
                raise ExceptionGroup("invalid metadata", exceptions)

        return ins

    @classmethod
    def from_email(cls, data: bytes | str, *, validate: bool = True) -> Metadata:
        """Parse metadata from email headers.

        If *validate* is true, the metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        raw, unparsed = parse_email(data)

        if validate:
            exceptions: list[Exception] = []
            for unparsed_key in unparsed:
                if unparsed_key in _EMAIL_TO_RAW_MAPPING:
                    message = f"{unparsed_key!r} has invalid data"
                else:
                    message = f"unrecognized field: {unparsed_key!r}"
                exceptions.append(InvalidMetadata(unparsed_key, message))

            if exceptions:
                raise ExceptionGroup("unparsed", exceptions)

        try:
            return cls.from_raw(raw, validate=validate)
        except ExceptionGroup as exc_group:
            raise ExceptionGroup(
                "invalid or unparsed metadata", exc_group.exceptions
            ) from None

    metadata_version: _Validator[_MetadataVersion] = _Validator()
    """:external:ref:`core-metadata-metadata-version`
    (required; validated to be a valid metadata version)"""
    # `name` is not normalized/typed to NormalizedName so as to provide access to
    # the original/raw name.
    name: _Validator[str] = _Validator()
    """:external:ref:`core-metadata-name`
    (required; validated using :func:`~packaging.utils.canonicalize_name` and its
    *validate* parameter)"""
    version: _Validator[version_module.Version] = _Validator()
    """:external:ref:`core-metadata-version` (required)"""
    dynamic: _Validator[list[str] | None] = _Validator(
        added="2.2",
    )
    """:external:ref:`core-metadata-dynamic`
    (validated against core metadata field names and lowercased)"""
    platforms: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-platform`"""
    supported_platforms: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-supported-platform`"""
    summary: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-summary` (validated to contain no newlines)"""
    description: _Validator[str | None] = _Validator()  # TODO 2.1: can be in body
    """:external:ref:`core-metadata-description`"""
    description_content_type: _Validator[str | None] = _Validator(added="2.1")
    """:external:ref:`core-metadata-description-content-type` (validated)"""
    keywords: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-keywords`"""
    home_page: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-home-page`"""
    download_url: _Validator[str | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-download-url`"""
    author: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author`"""
    author_email: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author-email`"""
    maintainer: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer`"""
    maintainer_email: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer-email`"""
    license: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-license`"""
    license_expression: _Validator[NormalizedLicenseExpression | None] = _Validator(
        added="2.4"
    )
    """:external:ref:`core-metadata-license-expression`"""
    license_files: _Validator[list[str] | None] = _Validator(added="2.4")
    """:external:ref:`core-metadata-license-file`"""
    classifiers: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-classifier`"""
    requires_dist: _Validator[list[requirements.Requirement] | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-dist`"""
    requires_python: _Validator[specifiers.SpecifierSet | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-python`"""
    # Because `Requires-External` allows for non-PEP 440 version specifiers, we
    # don't do any processing on the values.
    requires_external: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-requires-external`"""
    project_urls: _Validator[dict[str, str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-project-url`"""
    # PEP 685 lets us raise an error if an extra doesn't pass `Name` validation
    # regardless of metadata version.
    provides_extra: _Validator[list[utils.NormalizedName] | None] = _Validator(
        added="2.1",
    )
    """:external:ref:`core-metadata-provides-extra`"""
    provides_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-provides-dist`"""
    obsoletes_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-obsoletes-dist`"""
    requires: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Requires`` (deprecated)"""
    provides: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Provides`` (deprecated)"""
    obsoletes: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Obsoletes`` (deprecated)"""

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\metadata.py ===
from __future__ import annotations

import email.feedparser
import email.header
import email.message
import email.parser
import email.policy
import pathlib
import sys
import typing
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    TypedDict,
    cast,
)

from . import licenses, requirements, specifiers, utils
from . import version as version_module
from .licenses import NormalizedLicenseExpression

T = typing.TypeVar("T")


if sys.version_info >= (3, 11):  # pragma: no cover
    ExceptionGroup = ExceptionGroup
else:  # pragma: no cover

    class ExceptionGroup(Exception):
        """A minimal implementation of :external:exc:`ExceptionGroup` from Python 3.11.

        If :external:exc:`ExceptionGroup` is already defined by Python itself,
        that version is used instead.
        """

        message: str
        exceptions: list[Exception]

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            self.message = message
            self.exceptions = exceptions

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.message!r}, {self.exceptions!r})"


class InvalidMetadata(ValueError):
    """A metadata field contains invalid data."""

    field: str
    """The name of the field that contains invalid data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


# The RawMetadata class attempts to make as few assumptions about the underlying
# serialization formats as possible. The idea is that as long as a serialization
# formats offer some very basic primitives in *some* way then we can support
# serializing to and from that format.
class RawMetadata(TypedDict, total=False):
    """A dictionary of raw core metadata.

    Each field in core metadata maps to a key of this dictionary (when data is
    provided). The key is lower-case and underscores are used instead of dashes
    compared to the equivalent core metadata field. Any core metadata field that
    can be specified multiple times or can hold multiple values in a single
    field have a key with a plural name. See :class:`Metadata` whose attributes
    match the keys of this dictionary.

    Core metadata fields that can be specified multiple times are stored as a
    list or dict depending on which is appropriate for the field. Any fields
    which hold multiple values in a single field are stored as a list.

    """

    # Metadata 1.0 - PEP 241
    metadata_version: str
    name: str
    version: str
    platforms: list[str]
    summary: str
    description: str
    keywords: list[str]
    home_page: str
    author: str
    author_email: str
    license: str

    # Metadata 1.1 - PEP 314
    supported_platforms: list[str]
    download_url: str
    classifiers: list[str]
    requires: list[str]
    provides: list[str]
    obsoletes: list[str]

    # Metadata 1.2 - PEP 345
    maintainer: str
    maintainer_email: str
    requires_dist: list[str]
    provides_dist: list[str]
    obsoletes_dist: list[str]
    requires_python: str
    requires_external: list[str]
    project_urls: dict[str, str]

    # Metadata 2.0
    # PEP 426 attempted to completely revamp the metadata format
    # but got stuck without ever being able to build consensus on
    # it and ultimately ended up withdrawn.
    #
    # However, a number of tools had started emitting METADATA with
    # `2.0` Metadata-Version, so for historical reasons, this version
    # was skipped.

    # Metadata 2.1 - PEP 566
    description_content_type: str
    provides_extra: list[str]

    # Metadata 2.2 - PEP 643
    dynamic: list[str]

    # Metadata 2.3 - PEP 685
    # No new fields were added in PEP 685, just some edge case were
    # tightened up to provide better interoptability.

    # Metadata 2.4 - PEP 639
    license_expression: str
    license_files: list[str]


_STRING_FIELDS = {
    "author",
    "author_email",
    "description",
    "description_content_type",
    "download_url",
    "home_page",
    "license",
    "license_expression",
    "maintainer",
    "maintainer_email",
    "metadata_version",
    "name",
    "requires_python",
    "summary",
    "version",
}

_LIST_FIELDS = {
    "classifiers",
    "dynamic",
    "license_files",
    "obsoletes",
    "obsoletes_dist",
    "platforms",
    "provides",
    "provides_dist",
    "provides_extra",
    "requires",
    "requires_dist",
    "requires_external",
    "supported_platforms",
}

_DICT_FIELDS = {
    "project_urls",
}


def _parse_keywords(data: str) -> list[str]:
    """Split a string of comma-separated keywords into a list of keywords."""
    return [k.strip() for k in data.split(",")]


def _parse_project_urls(data: list[str]) -> dict[str, str]:
    """Parse a list of label/URL string pairings separated by a comma."""
    urls = {}
    for pair in data:
        # Our logic is slightly tricky here as we want to try and do
        # *something* reasonable with malformed data.
        #
        # The main thing that we have to worry about, is data that does
        # not have a ',' at all to split the label from the Value. There
        # isn't a singular right answer here, and we will fail validation
        # later on (if the caller is validating) so it doesn't *really*
        # matter, but since the missing value has to be an empty str
        # and our return value is dict[str, str], if we let the key
        # be the missing value, then they'd have multiple '' values that
        # overwrite each other in a accumulating dict.
        #
        # The other potentional issue is that it's possible to have the
        # same label multiple times in the metadata, with no solid "right"
        # answer with what to do in that case. As such, we'll do the only
        # thing we can, which is treat the field as unparseable and add it
        # to our list of unparsed fields.
        parts = [p.strip() for p in pair.split(",", 1)]
        parts.extend([""] * (max(0, 2 - len(parts))))  # Ensure 2 items

        # TODO: The spec doesn't say anything about if the keys should be
        #       considered case sensitive or not... logically they should
        #       be case-preserving and case-insensitive, but doing that
        #       would open up more cases where we might have duplicate
        #       entries.
        label, url = parts
        if label in urls:
            # The label already exists in our set of urls, so this field
            # is unparseable, and we can just add the whole thing to our
            # unparseable data and stop processing it.
            raise KeyError("duplicate labels in project urls")
        urls[label] = url

    return urls


def _get_payload(msg: email.message.Message, source: bytes | str) -> str:
    """Get the body of the message."""
    # If our source is a str, then our caller has managed encodings for us,
    # and we don't need to deal with it.
    if isinstance(source, str):
        payload = msg.get_payload()
        assert isinstance(payload, str)
        return payload
    # If our source is a bytes, then we're managing the encoding and we need
    # to deal with it.
    else:
        bpayload = msg.get_payload(decode=True)
        assert isinstance(bpayload, bytes)
        try:
            return bpayload.decode("utf8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("payload in an invalid encoding") from exc


# The various parse_FORMAT functions here are intended to be as lenient as
# possible in their parsing, while still returning a correctly typed
# RawMetadata.
#
# To aid in this, we also generally want to do as little touching of the
# data as possible, except where there are possibly some historic holdovers
# that make valid data awkward to work with.
#
# While this is a lower level, intermediate format than our ``Metadata``
# class, some light touch ups can make a massive difference in usability.

# Map METADATA fields to RawMetadata.
_EMAIL_TO_RAW_MAPPING = {
    "author": "author",
    "author-email": "author_email",
    "classifier": "classifiers",
    "description": "description",
    "description-content-type": "description_content_type",
    "download-url": "download_url",
    "dynamic": "dynamic",
    "home-page": "home_page",
    "keywords": "keywords",
    "license": "license",
    "license-expression": "license_expression",
    "license-file": "license_files",
    "maintainer": "maintainer",
    "maintainer-email": "maintainer_email",
    "metadata-version": "metadata_version",
    "name": "name",
    "obsoletes": "obsoletes",
    "obsoletes-dist": "obsoletes_dist",
    "platform": "platforms",
    "project-url": "project_urls",
    "provides": "provides",
    "provides-dist": "provides_dist",
    "provides-extra": "provides_extra",
    "requires": "requires",
    "requires-dist": "requires_dist",
    "requires-external": "requires_external",
    "requires-python": "requires_python",
    "summary": "summary",
    "supported-platform": "supported_platforms",
    "version": "version",
}
_RAW_TO_EMAIL_MAPPING = {raw: email for email, raw in _EMAIL_TO_RAW_MAPPING.items()}


def parse_email(data: bytes | str) -> tuple[RawMetadata, dict[str, list[str]]]:
    """Parse a distribution's metadata stored as email headers (e.g. from ``METADATA``).

    This function returns a two-item tuple of dicts. The first dict is of
    recognized fields from the core metadata specification. Fields that can be
    parsed and translated into Python's built-in types are converted
    appropriately. All other fields are left as-is. Fields that are allowed to
    appear multiple times are stored as lists.

    The second dict contains all other fields from the metadata. This includes
    any unrecognized fields. It also includes any fields which are expected to
    be parsed into a built-in type but were not formatted appropriately. Finally,
    any fields that are expected to appear only once but are repeated are
    included in this dict.

    """
    raw: dict[str, str | list[str] | dict[str, str]] = {}
    unparsed: dict[str, list[str]] = {}

    if isinstance(data, str):
        parsed = email.parser.Parser(policy=email.policy.compat32).parsestr(data)
    else:
        parsed = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(data)

    # We have to wrap parsed.keys() in a set, because in the case of multiple
    # values for a key (a list), the key will appear multiple times in the
    # list of keys, but we're avoiding that by using get_all().
    for name in frozenset(parsed.keys()):
        # Header names in RFC are case insensitive, so we'll normalize to all
        # lower case to make comparisons easier.
        name = name.lower()

        # We use get_all() here, even for fields that aren't multiple use,
        # because otherwise someone could have e.g. two Name fields, and we
        # would just silently ignore it rather than doing something about it.
        headers = parsed.get_all(name) or []

        # The way the email module works when parsing bytes is that it
        # unconditionally decodes the bytes as ascii using the surrogateescape
        # handler. When you pull that data back out (such as with get_all() ),
        # it looks to see if the str has any surrogate escapes, and if it does
        # it wraps it in a Header object instead of returning the string.
        #
        # As such, we'll look for those Header objects, and fix up the encoding.
        value = []
        # Flag if we have run into any issues processing the headers, thus
        # signalling that the data belongs in 'unparsed'.
        valid_encoding = True
        for h in headers:
            # It's unclear if this can return more types than just a Header or
            # a str, so we'll just assert here to make sure.
            assert isinstance(h, (email.header.Header, str))

            # If it's a header object, we need to do our little dance to get
            # the real data out of it. In cases where there is invalid data
            # we're going to end up with mojibake, but there's no obvious, good
            # way around that without reimplementing parts of the Header object
            # ourselves.
            #
            # That should be fine since, if mojibacked happens, this key is
            # going into the unparsed dict anyways.
            if isinstance(h, email.header.Header):
                # The Header object stores it's data as chunks, and each chunk
                # can be independently encoded, so we'll need to check each
                # of them.
                chunks: list[tuple[bytes, str | None]] = []
                for bin, encoding in email.header.decode_header(h):
                    try:
                        bin.decode("utf8", "strict")
                    except UnicodeDecodeError:
                        # Enable mojibake.
                        encoding = "latin1"
                        valid_encoding = False
                    else:
                        encoding = "utf8"
                    chunks.append((bin, encoding))

                # Turn our chunks back into a Header object, then let that
                # Header object do the right thing to turn them into a
                # string for us.
                value.append(str(email.header.make_header(chunks)))
            # This is already a string, so just add it.
            else:
                value.append(h)

        # We've processed all of our values to get them into a list of str,
        # but we may have mojibake data, in which case this is an unparsed
        # field.
        if not valid_encoding:
            unparsed[name] = value
            continue

        raw_name = _EMAIL_TO_RAW_MAPPING.get(name)
        if raw_name is None:
            # This is a bit of a weird situation, we've encountered a key that
            # we don't know what it means, so we don't know whether it's meant
            # to be a list or not.
            #
            # Since we can't really tell one way or another, we'll just leave it
            # as a list, even though it may be a single item list, because that's
            # what makes the most sense for email headers.
            unparsed[name] = value
            continue

        # If this is one of our string fields, then we'll check to see if our
        # value is a list of a single item. If it is then we'll assume that
        # it was emitted as a single string, and unwrap the str from inside
        # the list.
        #
        # If it's any other kind of data, then we haven't the faintest clue
        # what we should parse it as, and we have to just add it to our list
        # of unparsed stuff.
        if raw_name in _STRING_FIELDS and len(value) == 1:
            raw[raw_name] = value[0]
        # If this is one of our list of string fields, then we can just assign
        # the value, since email *only* has strings, and our get_all() call
        # above ensures that this is a list.
        elif raw_name in _LIST_FIELDS:
            raw[raw_name] = value
        # Special Case: Keywords
        # The keywords field is implemented in the metadata spec as a str,
        # but it conceptually is a list of strings, and is serialized using
        # ", ".join(keywords), so we'll do some light data massaging to turn
        # this into what it logically is.
        elif raw_name == "keywords" and len(value) == 1:
            raw[raw_name] = _parse_keywords(value[0])
        # Special Case: Project-URL
        # The project urls is implemented in the metadata spec as a list of
        # specially-formatted strings that represent a key and a value, which
        # is fundamentally a mapping, however the email format doesn't support
        # mappings in a sane way, so it was crammed into a list of strings
        # instead.
        #
        # We will do a little light data massaging to turn this into a map as
        # it logically should be.
        elif raw_name == "project_urls":
            try:
                raw[raw_name] = _parse_project_urls(value)
            except KeyError:
                unparsed[name] = value
        # Nothing that we've done has managed to parse this, so it'll just
        # throw it in our unparseable data and move on.
        else:
            unparsed[name] = value

    # We need to support getting the Description from the message payload in
    # addition to getting it from the the headers. This does mean, though, there
    # is the possibility of it being set both ways, in which case we put both
    # in 'unparsed' since we don't know which is right.
    try:
        payload = _get_payload(parsed, data)
    except ValueError:
        unparsed.setdefault("description", []).append(
            parsed.get_payload(decode=isinstance(data, bytes))  # type: ignore[call-overload]
        )
    else:
        if payload:
            # Check to see if we've already got a description, if so then both
            # it, and this body move to unparseable.
            if "description" in raw:
                description_header = cast(str, raw.pop("description"))
                unparsed.setdefault("description", []).extend(
                    [description_header, payload]
                )
            elif "description" in unparsed:
                unparsed["description"].append(payload)
            else:
                raw["description"] = payload

    # We need to cast our `raw` to a metadata, because a TypedDict only support
    # literal key names, but we're computing our key names on purpose, but the
    # way this function is implemented, our `TypedDict` can only have valid key
    # names.
    return cast(RawMetadata, raw), unparsed


_NOT_FOUND = object()


# Keep the two values in sync.
_VALID_METADATA_VERSIONS = ["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]
_MetadataVersion = Literal["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]

_REQUIRED_ATTRS = frozenset(["metadata_version", "name", "version"])


class _Validator(Generic[T]):
    """Validate a metadata field.

    All _process_*() methods correspond to a core metadata field. The method is
    called with the field's raw value. If the raw value is valid it is returned
    in its "enriched" form (e.g. ``version.Version`` for the ``Version`` field).
    If the raw value is invalid, :exc:`InvalidMetadata` is raised (with a cause
    as appropriate).
    """

    name: str
    raw_name: str
    added: _MetadataVersion

    def __init__(
        self,
        *,
        added: _MetadataVersion = "1.0",
    ) -> None:
        self.added = added

    def __set_name__(self, _owner: Metadata, name: str) -> None:
        self.name = name
        self.raw_name = _RAW_TO_EMAIL_MAPPING[name]

    def __get__(self, instance: Metadata, _owner: type[Metadata]) -> T:
        # With Python 3.8, the caching can be replaced with functools.cached_property().
        # No need to check the cache as attribute lookup will resolve into the
        # instance's __dict__ before __get__ is called.
        cache = instance.__dict__
        value = instance._raw.get(self.name)

        # To make the _process_* methods easier, we'll check if the value is None
        # and if this field is NOT a required attribute, and if both of those
        # things are true, we'll skip the the converter. This will mean that the
        # converters never have to deal with the None union.
        if self.name in _REQUIRED_ATTRS or value is not None:
            try:
                converter: Callable[[Any], T] = getattr(self, f"_process_{self.name}")
            except AttributeError:
                pass
            else:
                value = converter(value)

        cache[self.name] = value
        try:
            del instance._raw[self.name]  # type: ignore[misc]
        except KeyError:
            pass

        return cast(T, value)

    def _invalid_metadata(
        self, msg: str, cause: Exception | None = None
    ) -> InvalidMetadata:
        exc = InvalidMetadata(
            self.raw_name, msg.format_map({"field": repr(self.raw_name)})
        )
        exc.__cause__ = cause
        return exc

    def _process_metadata_version(self, value: str) -> _MetadataVersion:
        # Implicitly makes Metadata-Version required.
        if value not in _VALID_METADATA_VERSIONS:
            raise self._invalid_metadata(f"{value!r} is not a valid metadata version")
        return cast(_MetadataVersion, value)

    def _process_name(self, value: str) -> str:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        # Validate the name as a side-effect.
        try:
            utils.canonicalize_name(value, validate=True)
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return value

    def _process_version(self, value: str) -> version_module.Version:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        try:
            return version_module.parse(value)
        except version_module.InvalidVersion as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_summary(self, value: str) -> str:
        """Check the field contains no newlines."""
        if "\n" in value:
            raise self._invalid_metadata("{field} must be a single line")
        return value

    def _process_description_content_type(self, value: str) -> str:
        content_types = {"text/plain", "text/x-rst", "text/markdown"}
        message = email.message.EmailMessage()
        message["content-type"] = value

        content_type, parameters = (
            # Defaults to `text/plain` if parsing failed.
            message.get_content_type().lower(),
            message["content-type"].params,
        )
        # Check if content-type is valid or defaulted to `text/plain` and thus was
        # not parseable.
        if content_type not in content_types or content_type not in value.lower():
            raise self._invalid_metadata(
                f"{{field}} must be one of {list(content_types)}, not {value!r}"
            )

        charset = parameters.get("charset", "UTF-8")
        if charset != "UTF-8":
            raise self._invalid_metadata(
                f"{{field}} can only specify the UTF-8 charset, not {list(charset)}"
            )

        markdown_variants = {"GFM", "CommonMark"}
        variant = parameters.get("variant", "GFM")  # Use an acceptable default.
        if content_type == "text/markdown" and variant not in markdown_variants:
            raise self._invalid_metadata(
                f"valid Markdown variants for {{field}} are {list(markdown_variants)}, "
                f"not {variant!r}",
            )
        return value

    def _process_dynamic(self, value: list[str]) -> list[str]:
        for dynamic_field in map(str.lower, value):
            if dynamic_field in {"name", "version", "metadata-version"}:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not allowed as a dynamic field"
                )
            elif dynamic_field not in _EMAIL_TO_RAW_MAPPING:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not a valid dynamic field"
                )
        return list(map(str.lower, value))

    def _process_provides_extra(
        self,
        value: list[str],
    ) -> list[utils.NormalizedName]:
        normalized_names = []
        try:
            for name in value:
                normalized_names.append(utils.canonicalize_name(name, validate=True))
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{name!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return normalized_names

    def _process_requires_python(self, value: str) -> specifiers.SpecifierSet:
        try:
            return specifiers.SpecifierSet(value)
        except specifiers.InvalidSpecifier as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_requires_dist(
        self,
        value: list[str],
    ) -> list[requirements.Requirement]:
        reqs = []
        try:
            for req in value:
                reqs.append(requirements.Requirement(req))
        except requirements.InvalidRequirement as exc:
            raise self._invalid_metadata(
                f"{req!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return reqs

    def _process_license_expression(
        self, value: str
    ) -> NormalizedLicenseExpression | None:
        try:
            return licenses.canonicalize_license_expression(value)
        except ValueError as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_license_files(self, value: list[str]) -> list[str]:
        paths = []
        for path in value:
            if ".." in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "parent directory indicators are not allowed"
                )
            if "*" in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be resolved"
                )
            if (
                pathlib.PurePosixPath(path).is_absolute()
                or pathlib.PureWindowsPath(path).is_absolute()
            ):
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be relative"
                )
            if pathlib.PureWindowsPath(path).as_posix() != path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "paths must use '/' delimiter"
                )
            paths.append(path)
        return paths


class Metadata:
    """Representation of distribution metadata.

    Compared to :class:`RawMetadata`, this class provides objects representing
    metadata fields instead of only using built-in types. Any invalid metadata
    will cause :exc:`InvalidMetadata` to be raised (with a
    :py:attr:`~BaseException.__cause__` attribute as appropriate).
    """

    _raw: RawMetadata

    @classmethod
    def from_raw(cls, data: RawMetadata, *, validate: bool = True) -> Metadata:
        """Create an instance from :class:`RawMetadata`.

        If *validate* is true, all metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        ins = cls()
        ins._raw = data.copy()  # Mutations occur due to caching enriched values.

        if validate:
            exceptions: list[Exception] = []
            try:
                metadata_version = ins.metadata_version
                metadata_age = _VALID_METADATA_VERSIONS.index(metadata_version)
            except InvalidMetadata as metadata_version_exc:
                exceptions.append(metadata_version_exc)
                metadata_version = None

            # Make sure to check for the fields that are present, the required
            # fields (so their absence can be reported).
            fields_to_check = frozenset(ins._raw) | _REQUIRED_ATTRS
            # Remove fields that have already been checked.
            fields_to_check -= {"metadata_version"}

            for key in fields_to_check:
                try:
                    if metadata_version:
                        # Can't use getattr() as that triggers descriptor protocol which
                        # will fail due to no value for the instance argument.
                        try:
                            field_metadata_version = cls.__dict__[key].added
                        except KeyError:
                            exc = InvalidMetadata(key, f"unrecognized field: {key!r}")
                            exceptions.append(exc)
                            continue
                        field_age = _VALID_METADATA_VERSIONS.index(
                            field_metadata_version
                        )
                        if field_age > metadata_age:
                            field = _RAW_TO_EMAIL_MAPPING[key]
                            exc = InvalidMetadata(
                                field,
                                f"{field} introduced in metadata version "
                                f"{field_metadata_version}, not {metadata_version}",
                            )
                            exceptions.append(exc)
                            continue
                    getattr(ins, key)
                except InvalidMetadata as exc:
                    exceptions.append(exc)

            if exceptions:
                raise ExceptionGroup("invalid metadata", exceptions)

        return ins

    @classmethod
    def from_email(cls, data: bytes | str, *, validate: bool = True) -> Metadata:
        """Parse metadata from email headers.

        If *validate* is true, the metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        raw, unparsed = parse_email(data)

        if validate:
            exceptions: list[Exception] = []
            for unparsed_key in unparsed:
                if unparsed_key in _EMAIL_TO_RAW_MAPPING:
                    message = f"{unparsed_key!r} has invalid data"
                else:
                    message = f"unrecognized field: {unparsed_key!r}"
                exceptions.append(InvalidMetadata(unparsed_key, message))

            if exceptions:
                raise ExceptionGroup("unparsed", exceptions)

        try:
            return cls.from_raw(raw, validate=validate)
        except ExceptionGroup as exc_group:
            raise ExceptionGroup(
                "invalid or unparsed metadata", exc_group.exceptions
            ) from None

    metadata_version: _Validator[_MetadataVersion] = _Validator()
    """:external:ref:`core-metadata-metadata-version`
    (required; validated to be a valid metadata version)"""
    # `name` is not normalized/typed to NormalizedName so as to provide access to
    # the original/raw name.
    name: _Validator[str] = _Validator()
    """:external:ref:`core-metadata-name`
    (required; validated using :func:`~packaging.utils.canonicalize_name` and its
    *validate* parameter)"""
    version: _Validator[version_module.Version] = _Validator()
    """:external:ref:`core-metadata-version` (required)"""
    dynamic: _Validator[list[str] | None] = _Validator(
        added="2.2",
    )
    """:external:ref:`core-metadata-dynamic`
    (validated against core metadata field names and lowercased)"""
    platforms: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-platform`"""
    supported_platforms: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-supported-platform`"""
    summary: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-summary` (validated to contain no newlines)"""
    description: _Validator[str | None] = _Validator()  # TODO 2.1: can be in body
    """:external:ref:`core-metadata-description`"""
    description_content_type: _Validator[str | None] = _Validator(added="2.1")
    """:external:ref:`core-metadata-description-content-type` (validated)"""
    keywords: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-keywords`"""
    home_page: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-home-page`"""
    download_url: _Validator[str | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-download-url`"""
    author: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author`"""
    author_email: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author-email`"""
    maintainer: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer`"""
    maintainer_email: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer-email`"""
    license: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-license`"""
    license_expression: _Validator[NormalizedLicenseExpression | None] = _Validator(
        added="2.4"
    )
    """:external:ref:`core-metadata-license-expression`"""
    license_files: _Validator[list[str] | None] = _Validator(added="2.4")
    """:external:ref:`core-metadata-license-file`"""
    classifiers: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-classifier`"""
    requires_dist: _Validator[list[requirements.Requirement] | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-dist`"""
    requires_python: _Validator[specifiers.SpecifierSet | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-python`"""
    # Because `Requires-External` allows for non-PEP 440 version specifiers, we
    # don't do any processing on the values.
    requires_external: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-requires-external`"""
    project_urls: _Validator[dict[str, str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-project-url`"""
    # PEP 685 lets us raise an error if an extra doesn't pass `Name` validation
    # regardless of metadata version.
    provides_extra: _Validator[list[utils.NormalizedName] | None] = _Validator(
        added="2.1",
    )
    """:external:ref:`core-metadata-provides-extra`"""
    provides_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-provides-dist`"""
    obsoletes_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-obsoletes-dist`"""
    requires: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Requires`` (deprecated)"""
    provides: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Provides`` (deprecated)"""
    obsoletes: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Obsoletes`` (deprecated)"""

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\metadata.py ===
from __future__ import annotations

import email.feedparser
import email.header
import email.message
import email.parser
import email.policy
import pathlib
import sys
import typing
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    TypedDict,
    cast,
)

from . import licenses, requirements, specifiers, utils
from . import version as version_module
from .licenses import NormalizedLicenseExpression

T = typing.TypeVar("T")


if sys.version_info >= (3, 11):  # pragma: no cover
    ExceptionGroup = ExceptionGroup
else:  # pragma: no cover

    class ExceptionGroup(Exception):
        """A minimal implementation of :external:exc:`ExceptionGroup` from Python 3.11.

        If :external:exc:`ExceptionGroup` is already defined by Python itself,
        that version is used instead.
        """

        message: str
        exceptions: list[Exception]

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            self.message = message
            self.exceptions = exceptions

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.message!r}, {self.exceptions!r})"


class InvalidMetadata(ValueError):
    """A metadata field contains invalid data."""

    field: str
    """The name of the field that contains invalid data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


# The RawMetadata class attempts to make as few assumptions about the underlying
# serialization formats as possible. The idea is that as long as a serialization
# formats offer some very basic primitives in *some* way then we can support
# serializing to and from that format.
class RawMetadata(TypedDict, total=False):
    """A dictionary of raw core metadata.

    Each field in core metadata maps to a key of this dictionary (when data is
    provided). The key is lower-case and underscores are used instead of dashes
    compared to the equivalent core metadata field. Any core metadata field that
    can be specified multiple times or can hold multiple values in a single
    field have a key with a plural name. See :class:`Metadata` whose attributes
    match the keys of this dictionary.

    Core metadata fields that can be specified multiple times are stored as a
    list or dict depending on which is appropriate for the field. Any fields
    which hold multiple values in a single field are stored as a list.

    """

    # Metadata 1.0 - PEP 241
    metadata_version: str
    name: str
    version: str
    platforms: list[str]
    summary: str
    description: str
    keywords: list[str]
    home_page: str
    author: str
    author_email: str
    license: str

    # Metadata 1.1 - PEP 314
    supported_platforms: list[str]
    download_url: str
    classifiers: list[str]
    requires: list[str]
    provides: list[str]
    obsoletes: list[str]

    # Metadata 1.2 - PEP 345
    maintainer: str
    maintainer_email: str
    requires_dist: list[str]
    provides_dist: list[str]
    obsoletes_dist: list[str]
    requires_python: str
    requires_external: list[str]
    project_urls: dict[str, str]

    # Metadata 2.0
    # PEP 426 attempted to completely revamp the metadata format
    # but got stuck without ever being able to build consensus on
    # it and ultimately ended up withdrawn.
    #
    # However, a number of tools had started emitting METADATA with
    # `2.0` Metadata-Version, so for historical reasons, this version
    # was skipped.

    # Metadata 2.1 - PEP 566
    description_content_type: str
    provides_extra: list[str]

    # Metadata 2.2 - PEP 643
    dynamic: list[str]

    # Metadata 2.3 - PEP 685
    # No new fields were added in PEP 685, just some edge case were
    # tightened up to provide better interoptability.

    # Metadata 2.4 - PEP 639
    license_expression: str
    license_files: list[str]


_STRING_FIELDS = {
    "author",
    "author_email",
    "description",
    "description_content_type",
    "download_url",
    "home_page",
    "license",
    "license_expression",
    "maintainer",
    "maintainer_email",
    "metadata_version",
    "name",
    "requires_python",
    "summary",
    "version",
}

_LIST_FIELDS = {
    "classifiers",
    "dynamic",
    "license_files",
    "obsoletes",
    "obsoletes_dist",
    "platforms",
    "provides",
    "provides_dist",
    "provides_extra",
    "requires",
    "requires_dist",
    "requires_external",
    "supported_platforms",
}

_DICT_FIELDS = {
    "project_urls",
}


def _parse_keywords(data: str) -> list[str]:
    """Split a string of comma-separated keywords into a list of keywords."""
    return [k.strip() for k in data.split(",")]


def _parse_project_urls(data: list[str]) -> dict[str, str]:
    """Parse a list of label/URL string pairings separated by a comma."""
    urls = {}
    for pair in data:
        # Our logic is slightly tricky here as we want to try and do
        # *something* reasonable with malformed data.
        #
        # The main thing that we have to worry about, is data that does
        # not have a ',' at all to split the label from the Value. There
        # isn't a singular right answer here, and we will fail validation
        # later on (if the caller is validating) so it doesn't *really*
        # matter, but since the missing value has to be an empty str
        # and our return value is dict[str, str], if we let the key
        # be the missing value, then they'd have multiple '' values that
        # overwrite each other in a accumulating dict.
        #
        # The other potentional issue is that it's possible to have the
        # same label multiple times in the metadata, with no solid "right"
        # answer with what to do in that case. As such, we'll do the only
        # thing we can, which is treat the field as unparseable and add it
        # to our list of unparsed fields.
        parts = [p.strip() for p in pair.split(",", 1)]
        parts.extend([""] * (max(0, 2 - len(parts))))  # Ensure 2 items

        # TODO: The spec doesn't say anything about if the keys should be
        #       considered case sensitive or not... logically they should
        #       be case-preserving and case-insensitive, but doing that
        #       would open up more cases where we might have duplicate
        #       entries.
        label, url = parts
        if label in urls:
            # The label already exists in our set of urls, so this field
            # is unparseable, and we can just add the whole thing to our
            # unparseable data and stop processing it.
            raise KeyError("duplicate labels in project urls")
        urls[label] = url

    return urls


def _get_payload(msg: email.message.Message, source: bytes | str) -> str:
    """Get the body of the message."""
    # If our source is a str, then our caller has managed encodings for us,
    # and we don't need to deal with it.
    if isinstance(source, str):
        payload = msg.get_payload()
        assert isinstance(payload, str)
        return payload
    # If our source is a bytes, then we're managing the encoding and we need
    # to deal with it.
    else:
        bpayload = msg.get_payload(decode=True)
        assert isinstance(bpayload, bytes)
        try:
            return bpayload.decode("utf8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("payload in an invalid encoding") from exc


# The various parse_FORMAT functions here are intended to be as lenient as
# possible in their parsing, while still returning a correctly typed
# RawMetadata.
#
# To aid in this, we also generally want to do as little touching of the
# data as possible, except where there are possibly some historic holdovers
# that make valid data awkward to work with.
#
# While this is a lower level, intermediate format than our ``Metadata``
# class, some light touch ups can make a massive difference in usability.

# Map METADATA fields to RawMetadata.
_EMAIL_TO_RAW_MAPPING = {
    "author": "author",
    "author-email": "author_email",
    "classifier": "classifiers",
    "description": "description",
    "description-content-type": "description_content_type",
    "download-url": "download_url",
    "dynamic": "dynamic",
    "home-page": "home_page",
    "keywords": "keywords",
    "license": "license",
    "license-expression": "license_expression",
    "license-file": "license_files",
    "maintainer": "maintainer",
    "maintainer-email": "maintainer_email",
    "metadata-version": "metadata_version",
    "name": "name",
    "obsoletes": "obsoletes",
    "obsoletes-dist": "obsoletes_dist",
    "platform": "platforms",
    "project-url": "project_urls",
    "provides": "provides",
    "provides-dist": "provides_dist",
    "provides-extra": "provides_extra",
    "requires": "requires",
    "requires-dist": "requires_dist",
    "requires-external": "requires_external",
    "requires-python": "requires_python",
    "summary": "summary",
    "supported-platform": "supported_platforms",
    "version": "version",
}
_RAW_TO_EMAIL_MAPPING = {raw: email for email, raw in _EMAIL_TO_RAW_MAPPING.items()}


def parse_email(data: bytes | str) -> tuple[RawMetadata, dict[str, list[str]]]:
    """Parse a distribution's metadata stored as email headers (e.g. from ``METADATA``).

    This function returns a two-item tuple of dicts. The first dict is of
    recognized fields from the core metadata specification. Fields that can be
    parsed and translated into Python's built-in types are converted
    appropriately. All other fields are left as-is. Fields that are allowed to
    appear multiple times are stored as lists.

    The second dict contains all other fields from the metadata. This includes
    any unrecognized fields. It also includes any fields which are expected to
    be parsed into a built-in type but were not formatted appropriately. Finally,
    any fields that are expected to appear only once but are repeated are
    included in this dict.

    """
    raw: dict[str, str | list[str] | dict[str, str]] = {}
    unparsed: dict[str, list[str]] = {}

    if isinstance(data, str):
        parsed = email.parser.Parser(policy=email.policy.compat32).parsestr(data)
    else:
        parsed = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(data)

    # We have to wrap parsed.keys() in a set, because in the case of multiple
    # values for a key (a list), the key will appear multiple times in the
    # list of keys, but we're avoiding that by using get_all().
    for name in frozenset(parsed.keys()):
        # Header names in RFC are case insensitive, so we'll normalize to all
        # lower case to make comparisons easier.
        name = name.lower()

        # We use get_all() here, even for fields that aren't multiple use,
        # because otherwise someone could have e.g. two Name fields, and we
        # would just silently ignore it rather than doing something about it.
        headers = parsed.get_all(name) or []

        # The way the email module works when parsing bytes is that it
        # unconditionally decodes the bytes as ascii using the surrogateescape
        # handler. When you pull that data back out (such as with get_all() ),
        # it looks to see if the str has any surrogate escapes, and if it does
        # it wraps it in a Header object instead of returning the string.
        #
        # As such, we'll look for those Header objects, and fix up the encoding.
        value = []
        # Flag if we have run into any issues processing the headers, thus
        # signalling that the data belongs in 'unparsed'.
        valid_encoding = True
        for h in headers:
            # It's unclear if this can return more types than just a Header or
            # a str, so we'll just assert here to make sure.
            assert isinstance(h, (email.header.Header, str))

            # If it's a header object, we need to do our little dance to get
            # the real data out of it. In cases where there is invalid data
            # we're going to end up with mojibake, but there's no obvious, good
            # way around that without reimplementing parts of the Header object
            # ourselves.
            #
            # That should be fine since, if mojibacked happens, this key is
            # going into the unparsed dict anyways.
            if isinstance(h, email.header.Header):
                # The Header object stores it's data as chunks, and each chunk
                # can be independently encoded, so we'll need to check each
                # of them.
                chunks: list[tuple[bytes, str | None]] = []
                for bin, encoding in email.header.decode_header(h):
                    try:
                        bin.decode("utf8", "strict")
                    except UnicodeDecodeError:
                        # Enable mojibake.
                        encoding = "latin1"
                        valid_encoding = False
                    else:
                        encoding = "utf8"
                    chunks.append((bin, encoding))

                # Turn our chunks back into a Header object, then let that
                # Header object do the right thing to turn them into a
                # string for us.
                value.append(str(email.header.make_header(chunks)))
            # This is already a string, so just add it.
            else:
                value.append(h)

        # We've processed all of our values to get them into a list of str,
        # but we may have mojibake data, in which case this is an unparsed
        # field.
        if not valid_encoding:
            unparsed[name] = value
            continue

        raw_name = _EMAIL_TO_RAW_MAPPING.get(name)
        if raw_name is None:
            # This is a bit of a weird situation, we've encountered a key that
            # we don't know what it means, so we don't know whether it's meant
            # to be a list or not.
            #
            # Since we can't really tell one way or another, we'll just leave it
            # as a list, even though it may be a single item list, because that's
            # what makes the most sense for email headers.
            unparsed[name] = value
            continue

        # If this is one of our string fields, then we'll check to see if our
        # value is a list of a single item. If it is then we'll assume that
        # it was emitted as a single string, and unwrap the str from inside
        # the list.
        #
        # If it's any other kind of data, then we haven't the faintest clue
        # what we should parse it as, and we have to just add it to our list
        # of unparsed stuff.
        if raw_name in _STRING_FIELDS and len(value) == 1:
            raw[raw_name] = value[0]
        # If this is one of our list of string fields, then we can just assign
        # the value, since email *only* has strings, and our get_all() call
        # above ensures that this is a list.
        elif raw_name in _LIST_FIELDS:
            raw[raw_name] = value
        # Special Case: Keywords
        # The keywords field is implemented in the metadata spec as a str,
        # but it conceptually is a list of strings, and is serialized using
        # ", ".join(keywords), so we'll do some light data massaging to turn
        # this into what it logically is.
        elif raw_name == "keywords" and len(value) == 1:
            raw[raw_name] = _parse_keywords(value[0])
        # Special Case: Project-URL
        # The project urls is implemented in the metadata spec as a list of
        # specially-formatted strings that represent a key and a value, which
        # is fundamentally a mapping, however the email format doesn't support
        # mappings in a sane way, so it was crammed into a list of strings
        # instead.
        #
        # We will do a little light data massaging to turn this into a map as
        # it logically should be.
        elif raw_name == "project_urls":
            try:
                raw[raw_name] = _parse_project_urls(value)
            except KeyError:
                unparsed[name] = value
        # Nothing that we've done has managed to parse this, so it'll just
        # throw it in our unparseable data and move on.
        else:
            unparsed[name] = value

    # We need to support getting the Description from the message payload in
    # addition to getting it from the the headers. This does mean, though, there
    # is the possibility of it being set both ways, in which case we put both
    # in 'unparsed' since we don't know which is right.
    try:
        payload = _get_payload(parsed, data)
    except ValueError:
        unparsed.setdefault("description", []).append(
            parsed.get_payload(decode=isinstance(data, bytes))  # type: ignore[call-overload]
        )
    else:
        if payload:
            # Check to see if we've already got a description, if so then both
            # it, and this body move to unparseable.
            if "description" in raw:
                description_header = cast(str, raw.pop("description"))
                unparsed.setdefault("description", []).extend(
                    [description_header, payload]
                )
            elif "description" in unparsed:
                unparsed["description"].append(payload)
            else:
                raw["description"] = payload

    # We need to cast our `raw` to a metadata, because a TypedDict only support
    # literal key names, but we're computing our key names on purpose, but the
    # way this function is implemented, our `TypedDict` can only have valid key
    # names.
    return cast(RawMetadata, raw), unparsed


_NOT_FOUND = object()


# Keep the two values in sync.
_VALID_METADATA_VERSIONS = ["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]
_MetadataVersion = Literal["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]

_REQUIRED_ATTRS = frozenset(["metadata_version", "name", "version"])


class _Validator(Generic[T]):
    """Validate a metadata field.

    All _process_*() methods correspond to a core metadata field. The method is
    called with the field's raw value. If the raw value is valid it is returned
    in its "enriched" form (e.g. ``version.Version`` for the ``Version`` field).
    If the raw value is invalid, :exc:`InvalidMetadata` is raised (with a cause
    as appropriate).
    """

    name: str
    raw_name: str
    added: _MetadataVersion

    def __init__(
        self,
        *,
        added: _MetadataVersion = "1.0",
    ) -> None:
        self.added = added

    def __set_name__(self, _owner: Metadata, name: str) -> None:
        self.name = name
        self.raw_name = _RAW_TO_EMAIL_MAPPING[name]

    def __get__(self, instance: Metadata, _owner: type[Metadata]) -> T:
        # With Python 3.8, the caching can be replaced with functools.cached_property().
        # No need to check the cache as attribute lookup will resolve into the
        # instance's __dict__ before __get__ is called.
        cache = instance.__dict__
        value = instance._raw.get(self.name)

        # To make the _process_* methods easier, we'll check if the value is None
        # and if this field is NOT a required attribute, and if both of those
        # things are true, we'll skip the the converter. This will mean that the
        # converters never have to deal with the None union.
        if self.name in _REQUIRED_ATTRS or value is not None:
            try:
                converter: Callable[[Any], T] = getattr(self, f"_process_{self.name}")
            except AttributeError:
                pass
            else:
                value = converter(value)

        cache[self.name] = value
        try:
            del instance._raw[self.name]  # type: ignore[misc]
        except KeyError:
            pass

        return cast(T, value)

    def _invalid_metadata(
        self, msg: str, cause: Exception | None = None
    ) -> InvalidMetadata:
        exc = InvalidMetadata(
            self.raw_name, msg.format_map({"field": repr(self.raw_name)})
        )
        exc.__cause__ = cause
        return exc

    def _process_metadata_version(self, value: str) -> _MetadataVersion:
        # Implicitly makes Metadata-Version required.
        if value not in _VALID_METADATA_VERSIONS:
            raise self._invalid_metadata(f"{value!r} is not a valid metadata version")
        return cast(_MetadataVersion, value)

    def _process_name(self, value: str) -> str:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        # Validate the name as a side-effect.
        try:
            utils.canonicalize_name(value, validate=True)
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return value

    def _process_version(self, value: str) -> version_module.Version:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        try:
            return version_module.parse(value)
        except version_module.InvalidVersion as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_summary(self, value: str) -> str:
        """Check the field contains no newlines."""
        if "\n" in value:
            raise self._invalid_metadata("{field} must be a single line")
        return value

    def _process_description_content_type(self, value: str) -> str:
        content_types = {"text/plain", "text/x-rst", "text/markdown"}
        message = email.message.EmailMessage()
        message["content-type"] = value

        content_type, parameters = (
            # Defaults to `text/plain` if parsing failed.
            message.get_content_type().lower(),
            message["content-type"].params,
        )
        # Check if content-type is valid or defaulted to `text/plain` and thus was
        # not parseable.
        if content_type not in content_types or content_type not in value.lower():
            raise self._invalid_metadata(
                f"{{field}} must be one of {list(content_types)}, not {value!r}"
            )

        charset = parameters.get("charset", "UTF-8")
        if charset != "UTF-8":
            raise self._invalid_metadata(
                f"{{field}} can only specify the UTF-8 charset, not {list(charset)}"
            )

        markdown_variants = {"GFM", "CommonMark"}
        variant = parameters.get("variant", "GFM")  # Use an acceptable default.
        if content_type == "text/markdown" and variant not in markdown_variants:
            raise self._invalid_metadata(
                f"valid Markdown variants for {{field}} are {list(markdown_variants)}, "
                f"not {variant!r}",
            )
        return value

    def _process_dynamic(self, value: list[str]) -> list[str]:
        for dynamic_field in map(str.lower, value):
            if dynamic_field in {"name", "version", "metadata-version"}:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not allowed as a dynamic field"
                )
            elif dynamic_field not in _EMAIL_TO_RAW_MAPPING:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not a valid dynamic field"
                )
        return list(map(str.lower, value))

    def _process_provides_extra(
        self,
        value: list[str],
    ) -> list[utils.NormalizedName]:
        normalized_names = []
        try:
            for name in value:
                normalized_names.append(utils.canonicalize_name(name, validate=True))
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{name!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return normalized_names

    def _process_requires_python(self, value: str) -> specifiers.SpecifierSet:
        try:
            return specifiers.SpecifierSet(value)
        except specifiers.InvalidSpecifier as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_requires_dist(
        self,
        value: list[str],
    ) -> list[requirements.Requirement]:
        reqs = []
        try:
            for req in value:
                reqs.append(requirements.Requirement(req))
        except requirements.InvalidRequirement as exc:
            raise self._invalid_metadata(
                f"{req!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return reqs

    def _process_license_expression(
        self, value: str
    ) -> NormalizedLicenseExpression | None:
        try:
            return licenses.canonicalize_license_expression(value)
        except ValueError as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_license_files(self, value: list[str]) -> list[str]:
        paths = []
        for path in value:
            if ".." in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "parent directory indicators are not allowed"
                )
            if "*" in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be resolved"
                )
            if (
                pathlib.PurePosixPath(path).is_absolute()
                or pathlib.PureWindowsPath(path).is_absolute()
            ):
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be relative"
                )
            if pathlib.PureWindowsPath(path).as_posix() != path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "paths must use '/' delimiter"
                )
            paths.append(path)
        return paths


class Metadata:
    """Representation of distribution metadata.

    Compared to :class:`RawMetadata`, this class provides objects representing
    metadata fields instead of only using built-in types. Any invalid metadata
    will cause :exc:`InvalidMetadata` to be raised (with a
    :py:attr:`~BaseException.__cause__` attribute as appropriate).
    """

    _raw: RawMetadata

    @classmethod
    def from_raw(cls, data: RawMetadata, *, validate: bool = True) -> Metadata:
        """Create an instance from :class:`RawMetadata`.

        If *validate* is true, all metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        ins = cls()
        ins._raw = data.copy()  # Mutations occur due to caching enriched values.

        if validate:
            exceptions: list[Exception] = []
            try:
                metadata_version = ins.metadata_version
                metadata_age = _VALID_METADATA_VERSIONS.index(metadata_version)
            except InvalidMetadata as metadata_version_exc:
                exceptions.append(metadata_version_exc)
                metadata_version = None

            # Make sure to check for the fields that are present, the required
            # fields (so their absence can be reported).
            fields_to_check = frozenset(ins._raw) | _REQUIRED_ATTRS
            # Remove fields that have already been checked.
            fields_to_check -= {"metadata_version"}

            for key in fields_to_check:
                try:
                    if metadata_version:
                        # Can't use getattr() as that triggers descriptor protocol which
                        # will fail due to no value for the instance argument.
                        try:
                            field_metadata_version = cls.__dict__[key].added
                        except KeyError:
                            exc = InvalidMetadata(key, f"unrecognized field: {key!r}")
                            exceptions.append(exc)
                            continue
                        field_age = _VALID_METADATA_VERSIONS.index(
                            field_metadata_version
                        )
                        if field_age > metadata_age:
                            field = _RAW_TO_EMAIL_MAPPING[key]
                            exc = InvalidMetadata(
                                field,
                                f"{field} introduced in metadata version "
                                f"{field_metadata_version}, not {metadata_version}",
                            )
                            exceptions.append(exc)
                            continue
                    getattr(ins, key)
                except InvalidMetadata as exc:
                    exceptions.append(exc)

            if exceptions:
                raise ExceptionGroup("invalid metadata", exceptions)

        return ins

    @classmethod
    def from_email(cls, data: bytes | str, *, validate: bool = True) -> Metadata:
        """Parse metadata from email headers.

        If *validate* is true, the metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        raw, unparsed = parse_email(data)

        if validate:
            exceptions: list[Exception] = []
            for unparsed_key in unparsed:
                if unparsed_key in _EMAIL_TO_RAW_MAPPING:
                    message = f"{unparsed_key!r} has invalid data"
                else:
                    message = f"unrecognized field: {unparsed_key!r}"
                exceptions.append(InvalidMetadata(unparsed_key, message))

            if exceptions:
                raise ExceptionGroup("unparsed", exceptions)

        try:
            return cls.from_raw(raw, validate=validate)
        except ExceptionGroup as exc_group:
            raise ExceptionGroup(
                "invalid or unparsed metadata", exc_group.exceptions
            ) from None

    metadata_version: _Validator[_MetadataVersion] = _Validator()
    """:external:ref:`core-metadata-metadata-version`
    (required; validated to be a valid metadata version)"""
    # `name` is not normalized/typed to NormalizedName so as to provide access to
    # the original/raw name.
    name: _Validator[str] = _Validator()
    """:external:ref:`core-metadata-name`
    (required; validated using :func:`~packaging.utils.canonicalize_name` and its
    *validate* parameter)"""
    version: _Validator[version_module.Version] = _Validator()
    """:external:ref:`core-metadata-version` (required)"""
    dynamic: _Validator[list[str] | None] = _Validator(
        added="2.2",
    )
    """:external:ref:`core-metadata-dynamic`
    (validated against core metadata field names and lowercased)"""
    platforms: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-platform`"""
    supported_platforms: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-supported-platform`"""
    summary: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-summary` (validated to contain no newlines)"""
    description: _Validator[str | None] = _Validator()  # TODO 2.1: can be in body
    """:external:ref:`core-metadata-description`"""
    description_content_type: _Validator[str | None] = _Validator(added="2.1")
    """:external:ref:`core-metadata-description-content-type` (validated)"""
    keywords: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-keywords`"""
    home_page: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-home-page`"""
    download_url: _Validator[str | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-download-url`"""
    author: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author`"""
    author_email: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author-email`"""
    maintainer: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer`"""
    maintainer_email: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer-email`"""
    license: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-license`"""
    license_expression: _Validator[NormalizedLicenseExpression | None] = _Validator(
        added="2.4"
    )
    """:external:ref:`core-metadata-license-expression`"""
    license_files: _Validator[list[str] | None] = _Validator(added="2.4")
    """:external:ref:`core-metadata-license-file`"""
    classifiers: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-classifier`"""
    requires_dist: _Validator[list[requirements.Requirement] | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-dist`"""
    requires_python: _Validator[specifiers.SpecifierSet | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-python`"""
    # Because `Requires-External` allows for non-PEP 440 version specifiers, we
    # don't do any processing on the values.
    requires_external: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-requires-external`"""
    project_urls: _Validator[dict[str, str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-project-url`"""
    # PEP 685 lets us raise an error if an extra doesn't pass `Name` validation
    # regardless of metadata version.
    provides_extra: _Validator[list[utils.NormalizedName] | None] = _Validator(
        added="2.1",
    )
    """:external:ref:`core-metadata-provides-extra`"""
    provides_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-provides-dist`"""
    obsoletes_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-obsoletes-dist`"""
    requires: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Requires`` (deprecated)"""
    provides: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Provides`` (deprecated)"""
    obsoletes: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Obsoletes`` (deprecated)"""

# === NexusCore/openenv\Lib\site-packages\packaging\metadata.py ===
from __future__ import annotations

import email.feedparser
import email.header
import email.message
import email.parser
import email.policy
import pathlib
import sys
import typing
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    TypedDict,
    cast,
)

from . import licenses, requirements, specifiers, utils
from . import version as version_module
from .licenses import NormalizedLicenseExpression

T = typing.TypeVar("T")


if sys.version_info >= (3, 11):  # pragma: no cover
    ExceptionGroup = ExceptionGroup
else:  # pragma: no cover

    class ExceptionGroup(Exception):
        """A minimal implementation of :external:exc:`ExceptionGroup` from Python 3.11.

        If :external:exc:`ExceptionGroup` is already defined by Python itself,
        that version is used instead.
        """

        message: str
        exceptions: list[Exception]

        def __init__(self, message: str, exceptions: list[Exception]) -> None:
            self.message = message
            self.exceptions = exceptions

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}({self.message!r}, {self.exceptions!r})"


class InvalidMetadata(ValueError):
    """A metadata field contains invalid data."""

    field: str
    """The name of the field that contains invalid data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


# The RawMetadata class attempts to make as few assumptions about the underlying
# serialization formats as possible. The idea is that as long as a serialization
# formats offer some very basic primitives in *some* way then we can support
# serializing to and from that format.
class RawMetadata(TypedDict, total=False):
    """A dictionary of raw core metadata.

    Each field in core metadata maps to a key of this dictionary (when data is
    provided). The key is lower-case and underscores are used instead of dashes
    compared to the equivalent core metadata field. Any core metadata field that
    can be specified multiple times or can hold multiple values in a single
    field have a key with a plural name. See :class:`Metadata` whose attributes
    match the keys of this dictionary.

    Core metadata fields that can be specified multiple times are stored as a
    list or dict depending on which is appropriate for the field. Any fields
    which hold multiple values in a single field are stored as a list.

    """

    # Metadata 1.0 - PEP 241
    metadata_version: str
    name: str
    version: str
    platforms: list[str]
    summary: str
    description: str
    keywords: list[str]
    home_page: str
    author: str
    author_email: str
    license: str

    # Metadata 1.1 - PEP 314
    supported_platforms: list[str]
    download_url: str
    classifiers: list[str]
    requires: list[str]
    provides: list[str]
    obsoletes: list[str]

    # Metadata 1.2 - PEP 345
    maintainer: str
    maintainer_email: str
    requires_dist: list[str]
    provides_dist: list[str]
    obsoletes_dist: list[str]
    requires_python: str
    requires_external: list[str]
    project_urls: dict[str, str]

    # Metadata 2.0
    # PEP 426 attempted to completely revamp the metadata format
    # but got stuck without ever being able to build consensus on
    # it and ultimately ended up withdrawn.
    #
    # However, a number of tools had started emitting METADATA with
    # `2.0` Metadata-Version, so for historical reasons, this version
    # was skipped.

    # Metadata 2.1 - PEP 566
    description_content_type: str
    provides_extra: list[str]

    # Metadata 2.2 - PEP 643
    dynamic: list[str]

    # Metadata 2.3 - PEP 685
    # No new fields were added in PEP 685, just some edge case were
    # tightened up to provide better interoptability.

    # Metadata 2.4 - PEP 639
    license_expression: str
    license_files: list[str]


_STRING_FIELDS = {
    "author",
    "author_email",
    "description",
    "description_content_type",
    "download_url",
    "home_page",
    "license",
    "license_expression",
    "maintainer",
    "maintainer_email",
    "metadata_version",
    "name",
    "requires_python",
    "summary",
    "version",
}

_LIST_FIELDS = {
    "classifiers",
    "dynamic",
    "license_files",
    "obsoletes",
    "obsoletes_dist",
    "platforms",
    "provides",
    "provides_dist",
    "provides_extra",
    "requires",
    "requires_dist",
    "requires_external",
    "supported_platforms",
}

_DICT_FIELDS = {
    "project_urls",
}


def _parse_keywords(data: str) -> list[str]:
    """Split a string of comma-separated keywords into a list of keywords."""
    return [k.strip() for k in data.split(",")]


def _parse_project_urls(data: list[str]) -> dict[str, str]:
    """Parse a list of label/URL string pairings separated by a comma."""
    urls = {}
    for pair in data:
        # Our logic is slightly tricky here as we want to try and do
        # *something* reasonable with malformed data.
        #
        # The main thing that we have to worry about, is data that does
        # not have a ',' at all to split the label from the Value. There
        # isn't a singular right answer here, and we will fail validation
        # later on (if the caller is validating) so it doesn't *really*
        # matter, but since the missing value has to be an empty str
        # and our return value is dict[str, str], if we let the key
        # be the missing value, then they'd have multiple '' values that
        # overwrite each other in a accumulating dict.
        #
        # The other potentional issue is that it's possible to have the
        # same label multiple times in the metadata, with no solid "right"
        # answer with what to do in that case. As such, we'll do the only
        # thing we can, which is treat the field as unparseable and add it
        # to our list of unparsed fields.
        parts = [p.strip() for p in pair.split(",", 1)]
        parts.extend([""] * (max(0, 2 - len(parts))))  # Ensure 2 items

        # TODO: The spec doesn't say anything about if the keys should be
        #       considered case sensitive or not... logically they should
        #       be case-preserving and case-insensitive, but doing that
        #       would open up more cases where we might have duplicate
        #       entries.
        label, url = parts
        if label in urls:
            # The label already exists in our set of urls, so this field
            # is unparseable, and we can just add the whole thing to our
            # unparseable data and stop processing it.
            raise KeyError("duplicate labels in project urls")
        urls[label] = url

    return urls


def _get_payload(msg: email.message.Message, source: bytes | str) -> str:
    """Get the body of the message."""
    # If our source is a str, then our caller has managed encodings for us,
    # and we don't need to deal with it.
    if isinstance(source, str):
        payload = msg.get_payload()
        assert isinstance(payload, str)
        return payload
    # If our source is a bytes, then we're managing the encoding and we need
    # to deal with it.
    else:
        bpayload = msg.get_payload(decode=True)
        assert isinstance(bpayload, bytes)
        try:
            return bpayload.decode("utf8", "strict")
        except UnicodeDecodeError as exc:
            raise ValueError("payload in an invalid encoding") from exc


# The various parse_FORMAT functions here are intended to be as lenient as
# possible in their parsing, while still returning a correctly typed
# RawMetadata.
#
# To aid in this, we also generally want to do as little touching of the
# data as possible, except where there are possibly some historic holdovers
# that make valid data awkward to work with.
#
# While this is a lower level, intermediate format than our ``Metadata``
# class, some light touch ups can make a massive difference in usability.

# Map METADATA fields to RawMetadata.
_EMAIL_TO_RAW_MAPPING = {
    "author": "author",
    "author-email": "author_email",
    "classifier": "classifiers",
    "description": "description",
    "description-content-type": "description_content_type",
    "download-url": "download_url",
    "dynamic": "dynamic",
    "home-page": "home_page",
    "keywords": "keywords",
    "license": "license",
    "license-expression": "license_expression",
    "license-file": "license_files",
    "maintainer": "maintainer",
    "maintainer-email": "maintainer_email",
    "metadata-version": "metadata_version",
    "name": "name",
    "obsoletes": "obsoletes",
    "obsoletes-dist": "obsoletes_dist",
    "platform": "platforms",
    "project-url": "project_urls",
    "provides": "provides",
    "provides-dist": "provides_dist",
    "provides-extra": "provides_extra",
    "requires": "requires",
    "requires-dist": "requires_dist",
    "requires-external": "requires_external",
    "requires-python": "requires_python",
    "summary": "summary",
    "supported-platform": "supported_platforms",
    "version": "version",
}
_RAW_TO_EMAIL_MAPPING = {raw: email for email, raw in _EMAIL_TO_RAW_MAPPING.items()}


def parse_email(data: bytes | str) -> tuple[RawMetadata, dict[str, list[str]]]:
    """Parse a distribution's metadata stored as email headers (e.g. from ``METADATA``).

    This function returns a two-item tuple of dicts. The first dict is of
    recognized fields from the core metadata specification. Fields that can be
    parsed and translated into Python's built-in types are converted
    appropriately. All other fields are left as-is. Fields that are allowed to
    appear multiple times are stored as lists.

    The second dict contains all other fields from the metadata. This includes
    any unrecognized fields. It also includes any fields which are expected to
    be parsed into a built-in type but were not formatted appropriately. Finally,
    any fields that are expected to appear only once but are repeated are
    included in this dict.

    """
    raw: dict[str, str | list[str] | dict[str, str]] = {}
    unparsed: dict[str, list[str]] = {}

    if isinstance(data, str):
        parsed = email.parser.Parser(policy=email.policy.compat32).parsestr(data)
    else:
        parsed = email.parser.BytesParser(policy=email.policy.compat32).parsebytes(data)

    # We have to wrap parsed.keys() in a set, because in the case of multiple
    # values for a key (a list), the key will appear multiple times in the
    # list of keys, but we're avoiding that by using get_all().
    for name in frozenset(parsed.keys()):
        # Header names in RFC are case insensitive, so we'll normalize to all
        # lower case to make comparisons easier.
        name = name.lower()

        # We use get_all() here, even for fields that aren't multiple use,
        # because otherwise someone could have e.g. two Name fields, and we
        # would just silently ignore it rather than doing something about it.
        headers = parsed.get_all(name) or []

        # The way the email module works when parsing bytes is that it
        # unconditionally decodes the bytes as ascii using the surrogateescape
        # handler. When you pull that data back out (such as with get_all() ),
        # it looks to see if the str has any surrogate escapes, and if it does
        # it wraps it in a Header object instead of returning the string.
        #
        # As such, we'll look for those Header objects, and fix up the encoding.
        value = []
        # Flag if we have run into any issues processing the headers, thus
        # signalling that the data belongs in 'unparsed'.
        valid_encoding = True
        for h in headers:
            # It's unclear if this can return more types than just a Header or
            # a str, so we'll just assert here to make sure.
            assert isinstance(h, (email.header.Header, str))

            # If it's a header object, we need to do our little dance to get
            # the real data out of it. In cases where there is invalid data
            # we're going to end up with mojibake, but there's no obvious, good
            # way around that without reimplementing parts of the Header object
            # ourselves.
            #
            # That should be fine since, if mojibacked happens, this key is
            # going into the unparsed dict anyways.
            if isinstance(h, email.header.Header):
                # The Header object stores it's data as chunks, and each chunk
                # can be independently encoded, so we'll need to check each
                # of them.
                chunks: list[tuple[bytes, str | None]] = []
                for bin, encoding in email.header.decode_header(h):
                    try:
                        bin.decode("utf8", "strict")
                    except UnicodeDecodeError:
                        # Enable mojibake.
                        encoding = "latin1"
                        valid_encoding = False
                    else:
                        encoding = "utf8"
                    chunks.append((bin, encoding))

                # Turn our chunks back into a Header object, then let that
                # Header object do the right thing to turn them into a
                # string for us.
                value.append(str(email.header.make_header(chunks)))
            # This is already a string, so just add it.
            else:
                value.append(h)

        # We've processed all of our values to get them into a list of str,
        # but we may have mojibake data, in which case this is an unparsed
        # field.
        if not valid_encoding:
            unparsed[name] = value
            continue

        raw_name = _EMAIL_TO_RAW_MAPPING.get(name)
        if raw_name is None:
            # This is a bit of a weird situation, we've encountered a key that
            # we don't know what it means, so we don't know whether it's meant
            # to be a list or not.
            #
            # Since we can't really tell one way or another, we'll just leave it
            # as a list, even though it may be a single item list, because that's
            # what makes the most sense for email headers.
            unparsed[name] = value
            continue

        # If this is one of our string fields, then we'll check to see if our
        # value is a list of a single item. If it is then we'll assume that
        # it was emitted as a single string, and unwrap the str from inside
        # the list.
        #
        # If it's any other kind of data, then we haven't the faintest clue
        # what we should parse it as, and we have to just add it to our list
        # of unparsed stuff.
        if raw_name in _STRING_FIELDS and len(value) == 1:
            raw[raw_name] = value[0]
        # If this is one of our list of string fields, then we can just assign
        # the value, since email *only* has strings, and our get_all() call
        # above ensures that this is a list.
        elif raw_name in _LIST_FIELDS:
            raw[raw_name] = value
        # Special Case: Keywords
        # The keywords field is implemented in the metadata spec as a str,
        # but it conceptually is a list of strings, and is serialized using
        # ", ".join(keywords), so we'll do some light data massaging to turn
        # this into what it logically is.
        elif raw_name == "keywords" and len(value) == 1:
            raw[raw_name] = _parse_keywords(value[0])
        # Special Case: Project-URL
        # The project urls is implemented in the metadata spec as a list of
        # specially-formatted strings that represent a key and a value, which
        # is fundamentally a mapping, however the email format doesn't support
        # mappings in a sane way, so it was crammed into a list of strings
        # instead.
        #
        # We will do a little light data massaging to turn this into a map as
        # it logically should be.
        elif raw_name == "project_urls":
            try:
                raw[raw_name] = _parse_project_urls(value)
            except KeyError:
                unparsed[name] = value
        # Nothing that we've done has managed to parse this, so it'll just
        # throw it in our unparseable data and move on.
        else:
            unparsed[name] = value

    # We need to support getting the Description from the message payload in
    # addition to getting it from the the headers. This does mean, though, there
    # is the possibility of it being set both ways, in which case we put both
    # in 'unparsed' since we don't know which is right.
    try:
        payload = _get_payload(parsed, data)
    except ValueError:
        unparsed.setdefault("description", []).append(
            parsed.get_payload(decode=isinstance(data, bytes))  # type: ignore[call-overload]
        )
    else:
        if payload:
            # Check to see if we've already got a description, if so then both
            # it, and this body move to unparseable.
            if "description" in raw:
                description_header = cast(str, raw.pop("description"))
                unparsed.setdefault("description", []).extend(
                    [description_header, payload]
                )
            elif "description" in unparsed:
                unparsed["description"].append(payload)
            else:
                raw["description"] = payload

    # We need to cast our `raw` to a metadata, because a TypedDict only support
    # literal key names, but we're computing our key names on purpose, but the
    # way this function is implemented, our `TypedDict` can only have valid key
    # names.
    return cast(RawMetadata, raw), unparsed


_NOT_FOUND = object()


# Keep the two values in sync.
_VALID_METADATA_VERSIONS = ["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]
_MetadataVersion = Literal["1.0", "1.1", "1.2", "2.1", "2.2", "2.3", "2.4"]

_REQUIRED_ATTRS = frozenset(["metadata_version", "name", "version"])


class _Validator(Generic[T]):
    """Validate a metadata field.

    All _process_*() methods correspond to a core metadata field. The method is
    called with the field's raw value. If the raw value is valid it is returned
    in its "enriched" form (e.g. ``version.Version`` for the ``Version`` field).
    If the raw value is invalid, :exc:`InvalidMetadata` is raised (with a cause
    as appropriate).
    """

    name: str
    raw_name: str
    added: _MetadataVersion

    def __init__(
        self,
        *,
        added: _MetadataVersion = "1.0",
    ) -> None:
        self.added = added

    def __set_name__(self, _owner: Metadata, name: str) -> None:
        self.name = name
        self.raw_name = _RAW_TO_EMAIL_MAPPING[name]

    def __get__(self, instance: Metadata, _owner: type[Metadata]) -> T:
        # With Python 3.8, the caching can be replaced with functools.cached_property().
        # No need to check the cache as attribute lookup will resolve into the
        # instance's __dict__ before __get__ is called.
        cache = instance.__dict__
        value = instance._raw.get(self.name)

        # To make the _process_* methods easier, we'll check if the value is None
        # and if this field is NOT a required attribute, and if both of those
        # things are true, we'll skip the the converter. This will mean that the
        # converters never have to deal with the None union.
        if self.name in _REQUIRED_ATTRS or value is not None:
            try:
                converter: Callable[[Any], T] = getattr(self, f"_process_{self.name}")
            except AttributeError:
                pass
            else:
                value = converter(value)

        cache[self.name] = value
        try:
            del instance._raw[self.name]  # type: ignore[misc]
        except KeyError:
            pass

        return cast(T, value)

    def _invalid_metadata(
        self, msg: str, cause: Exception | None = None
    ) -> InvalidMetadata:
        exc = InvalidMetadata(
            self.raw_name, msg.format_map({"field": repr(self.raw_name)})
        )
        exc.__cause__ = cause
        return exc

    def _process_metadata_version(self, value: str) -> _MetadataVersion:
        # Implicitly makes Metadata-Version required.
        if value not in _VALID_METADATA_VERSIONS:
            raise self._invalid_metadata(f"{value!r} is not a valid metadata version")
        return cast(_MetadataVersion, value)

    def _process_name(self, value: str) -> str:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        # Validate the name as a side-effect.
        try:
            utils.canonicalize_name(value, validate=True)
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return value

    def _process_version(self, value: str) -> version_module.Version:
        if not value:
            raise self._invalid_metadata("{field} is a required field")
        try:
            return version_module.parse(value)
        except version_module.InvalidVersion as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_summary(self, value: str) -> str:
        """Check the field contains no newlines."""
        if "\n" in value:
            raise self._invalid_metadata("{field} must be a single line")
        return value

    def _process_description_content_type(self, value: str) -> str:
        content_types = {"text/plain", "text/x-rst", "text/markdown"}
        message = email.message.EmailMessage()
        message["content-type"] = value

        content_type, parameters = (
            # Defaults to `text/plain` if parsing failed.
            message.get_content_type().lower(),
            message["content-type"].params,
        )
        # Check if content-type is valid or defaulted to `text/plain` and thus was
        # not parseable.
        if content_type not in content_types or content_type not in value.lower():
            raise self._invalid_metadata(
                f"{{field}} must be one of {list(content_types)}, not {value!r}"
            )

        charset = parameters.get("charset", "UTF-8")
        if charset != "UTF-8":
            raise self._invalid_metadata(
                f"{{field}} can only specify the UTF-8 charset, not {list(charset)}"
            )

        markdown_variants = {"GFM", "CommonMark"}
        variant = parameters.get("variant", "GFM")  # Use an acceptable default.
        if content_type == "text/markdown" and variant not in markdown_variants:
            raise self._invalid_metadata(
                f"valid Markdown variants for {{field}} are {list(markdown_variants)}, "
                f"not {variant!r}",
            )
        return value

    def _process_dynamic(self, value: list[str]) -> list[str]:
        for dynamic_field in map(str.lower, value):
            if dynamic_field in {"name", "version", "metadata-version"}:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not allowed as a dynamic field"
                )
            elif dynamic_field not in _EMAIL_TO_RAW_MAPPING:
                raise self._invalid_metadata(
                    f"{dynamic_field!r} is not a valid dynamic field"
                )
        return list(map(str.lower, value))

    def _process_provides_extra(
        self,
        value: list[str],
    ) -> list[utils.NormalizedName]:
        normalized_names = []
        try:
            for name in value:
                normalized_names.append(utils.canonicalize_name(name, validate=True))
        except utils.InvalidName as exc:
            raise self._invalid_metadata(
                f"{name!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return normalized_names

    def _process_requires_python(self, value: str) -> specifiers.SpecifierSet:
        try:
            return specifiers.SpecifierSet(value)
        except specifiers.InvalidSpecifier as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_requires_dist(
        self,
        value: list[str],
    ) -> list[requirements.Requirement]:
        reqs = []
        try:
            for req in value:
                reqs.append(requirements.Requirement(req))
        except requirements.InvalidRequirement as exc:
            raise self._invalid_metadata(
                f"{req!r} is invalid for {{field}}", cause=exc
            ) from exc
        else:
            return reqs

    def _process_license_expression(
        self, value: str
    ) -> NormalizedLicenseExpression | None:
        try:
            return licenses.canonicalize_license_expression(value)
        except ValueError as exc:
            raise self._invalid_metadata(
                f"{value!r} is invalid for {{field}}", cause=exc
            ) from exc

    def _process_license_files(self, value: list[str]) -> list[str]:
        paths = []
        for path in value:
            if ".." in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, "
                    "parent directory indicators are not allowed"
                )
            if "*" in path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be resolved"
                )
            if (
                pathlib.PurePosixPath(path).is_absolute()
                or pathlib.PureWindowsPath(path).is_absolute()
            ):
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must be relative"
                )
            if pathlib.PureWindowsPath(path).as_posix() != path:
                raise self._invalid_metadata(
                    f"{path!r} is invalid for {{field}}, paths must use '/' delimiter"
                )
            paths.append(path)
        return paths


class Metadata:
    """Representation of distribution metadata.

    Compared to :class:`RawMetadata`, this class provides objects representing
    metadata fields instead of only using built-in types. Any invalid metadata
    will cause :exc:`InvalidMetadata` to be raised (with a
    :py:attr:`~BaseException.__cause__` attribute as appropriate).
    """

    _raw: RawMetadata

    @classmethod
    def from_raw(cls, data: RawMetadata, *, validate: bool = True) -> Metadata:
        """Create an instance from :class:`RawMetadata`.

        If *validate* is true, all metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        ins = cls()
        ins._raw = data.copy()  # Mutations occur due to caching enriched values.

        if validate:
            exceptions: list[Exception] = []
            try:
                metadata_version = ins.metadata_version
                metadata_age = _VALID_METADATA_VERSIONS.index(metadata_version)
            except InvalidMetadata as metadata_version_exc:
                exceptions.append(metadata_version_exc)
                metadata_version = None

            # Make sure to check for the fields that are present, the required
            # fields (so their absence can be reported).
            fields_to_check = frozenset(ins._raw) | _REQUIRED_ATTRS
            # Remove fields that have already been checked.
            fields_to_check -= {"metadata_version"}

            for key in fields_to_check:
                try:
                    if metadata_version:
                        # Can't use getattr() as that triggers descriptor protocol which
                        # will fail due to no value for the instance argument.
                        try:
                            field_metadata_version = cls.__dict__[key].added
                        except KeyError:
                            exc = InvalidMetadata(key, f"unrecognized field: {key!r}")
                            exceptions.append(exc)
                            continue
                        field_age = _VALID_METADATA_VERSIONS.index(
                            field_metadata_version
                        )
                        if field_age > metadata_age:
                            field = _RAW_TO_EMAIL_MAPPING[key]
                            exc = InvalidMetadata(
                                field,
                                f"{field} introduced in metadata version "
                                f"{field_metadata_version}, not {metadata_version}",
                            )
                            exceptions.append(exc)
                            continue
                    getattr(ins, key)
                except InvalidMetadata as exc:
                    exceptions.append(exc)

            if exceptions:
                raise ExceptionGroup("invalid metadata", exceptions)

        return ins

    @classmethod
    def from_email(cls, data: bytes | str, *, validate: bool = True) -> Metadata:
        """Parse metadata from email headers.

        If *validate* is true, the metadata will be validated. All exceptions
        related to validation will be gathered and raised as an :class:`ExceptionGroup`.
        """
        raw, unparsed = parse_email(data)

        if validate:
            exceptions: list[Exception] = []
            for unparsed_key in unparsed:
                if unparsed_key in _EMAIL_TO_RAW_MAPPING:
                    message = f"{unparsed_key!r} has invalid data"
                else:
                    message = f"unrecognized field: {unparsed_key!r}"
                exceptions.append(InvalidMetadata(unparsed_key, message))

            if exceptions:
                raise ExceptionGroup("unparsed", exceptions)

        try:
            return cls.from_raw(raw, validate=validate)
        except ExceptionGroup as exc_group:
            raise ExceptionGroup(
                "invalid or unparsed metadata", exc_group.exceptions
            ) from None

    metadata_version: _Validator[_MetadataVersion] = _Validator()
    """:external:ref:`core-metadata-metadata-version`
    (required; validated to be a valid metadata version)"""
    # `name` is not normalized/typed to NormalizedName so as to provide access to
    # the original/raw name.
    name: _Validator[str] = _Validator()
    """:external:ref:`core-metadata-name`
    (required; validated using :func:`~packaging.utils.canonicalize_name` and its
    *validate* parameter)"""
    version: _Validator[version_module.Version] = _Validator()
    """:external:ref:`core-metadata-version` (required)"""
    dynamic: _Validator[list[str] | None] = _Validator(
        added="2.2",
    )
    """:external:ref:`core-metadata-dynamic`
    (validated against core metadata field names and lowercased)"""
    platforms: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-platform`"""
    supported_platforms: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-supported-platform`"""
    summary: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-summary` (validated to contain no newlines)"""
    description: _Validator[str | None] = _Validator()  # TODO 2.1: can be in body
    """:external:ref:`core-metadata-description`"""
    description_content_type: _Validator[str | None] = _Validator(added="2.1")
    """:external:ref:`core-metadata-description-content-type` (validated)"""
    keywords: _Validator[list[str] | None] = _Validator()
    """:external:ref:`core-metadata-keywords`"""
    home_page: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-home-page`"""
    download_url: _Validator[str | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-download-url`"""
    author: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author`"""
    author_email: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-author-email`"""
    maintainer: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer`"""
    maintainer_email: _Validator[str | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-maintainer-email`"""
    license: _Validator[str | None] = _Validator()
    """:external:ref:`core-metadata-license`"""
    license_expression: _Validator[NormalizedLicenseExpression | None] = _Validator(
        added="2.4"
    )
    """:external:ref:`core-metadata-license-expression`"""
    license_files: _Validator[list[str] | None] = _Validator(added="2.4")
    """:external:ref:`core-metadata-license-file`"""
    classifiers: _Validator[list[str] | None] = _Validator(added="1.1")
    """:external:ref:`core-metadata-classifier`"""
    requires_dist: _Validator[list[requirements.Requirement] | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-dist`"""
    requires_python: _Validator[specifiers.SpecifierSet | None] = _Validator(
        added="1.2"
    )
    """:external:ref:`core-metadata-requires-python`"""
    # Because `Requires-External` allows for non-PEP 440 version specifiers, we
    # don't do any processing on the values.
    requires_external: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-requires-external`"""
    project_urls: _Validator[dict[str, str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-project-url`"""
    # PEP 685 lets us raise an error if an extra doesn't pass `Name` validation
    # regardless of metadata version.
    provides_extra: _Validator[list[utils.NormalizedName] | None] = _Validator(
        added="2.1",
    )
    """:external:ref:`core-metadata-provides-extra`"""
    provides_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-provides-dist`"""
    obsoletes_dist: _Validator[list[str] | None] = _Validator(added="1.2")
    """:external:ref:`core-metadata-obsoletes-dist`"""
    requires: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Requires`` (deprecated)"""
    provides: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Provides`` (deprecated)"""
    obsoletes: _Validator[list[str] | None] = _Validator(added="1.1")
    """``Obsoletes`` (deprecated)"""

# === NexusCore/openenv\Lib\site-packages\google\auth\aws.py ===
# Copyright 2020 Google LLC
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

"""AWS Credentials and AWS Signature V4 Request Signer.

This module provides credentials to access Google Cloud resources from Amazon
Web Services (AWS) workloads. These credentials are recommended over the
use of service account credentials in AWS as they do not involve the management
of long-live service account private keys.

AWS Credentials are initialized using external_account arguments which are
typically loaded from the external credentials JSON file.

This module also provides a definition for an abstract AWS security credentials supplier.
This supplier can be implemented to return valid AWS security credentials and an AWS region
and used to create AWS credentials. The credentials will then call the
supplier instead of using pre-defined methods such as calling the EC2 metadata endpoints.

This module also provides a basic implementation of the
`AWS Signature Version 4`_ request signing algorithm.

AWS Credentials use serialized signed requests to the
`AWS STS GetCallerIdentity`_ API that can be exchanged for Google access tokens
via the GCP STS endpoint.

.. _AWS Signature Version 4: https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
.. _AWS STS GetCallerIdentity: https://docs.aws.amazon.com/STS/latest/APIReference/API_GetCallerIdentity.html
"""

import abc
from dataclasses import dataclass
import hashlib
import hmac
import http.client as http_client
import json
import os
import posixpath
import re
from typing import Optional
import urllib
from urllib.parse import urljoin

from google.auth import _helpers
from google.auth import environment_vars
from google.auth import exceptions
from google.auth import external_account

# AWS Signature Version 4 signing algorithm identifier.
_AWS_ALGORITHM = "AWS4-HMAC-SHA256"
# The termination string for the AWS credential scope value as defined in
# https://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html
_AWS_REQUEST_TYPE = "aws4_request"
# The AWS authorization header name for the security session token if available.
_AWS_SECURITY_TOKEN_HEADER = "x-amz-security-token"
# The AWS authorization header name for the auto-generated date.
_AWS_DATE_HEADER = "x-amz-date"
# The default AWS regional credential verification URL.
_DEFAULT_AWS_REGIONAL_CREDENTIAL_VERIFICATION_URL = (
    "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15"
)
# IMDSV2 session token lifetime. This is set to a low value because the session token is used immediately.
_IMDSV2_SESSION_TOKEN_TTL_SECONDS = "300"


class RequestSigner(object):
    """Implements an AWS request signer based on the AWS Signature Version 4 signing
    process.
    https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html
    """

    def __init__(self, region_name):
        """Instantiates an AWS request signer used to compute authenticated signed
        requests to AWS APIs based on the AWS Signature Version 4 signing process.

        Args:
            region_name (str): The AWS region to use.
        """

        self._region_name = region_name

    def get_request_options(
        self,
        aws_security_credentials,
        url,
        method,
        request_payload="",
        additional_headers={},
    ):
        """Generates the signed request for the provided HTTP request for calling
        an AWS API. This follows the steps described at:
        https://docs.aws.amazon.com/general/latest/gr/sigv4_signing.html

        Args:
            aws_security_credentials (AWSSecurityCredentials): The AWS security credentials.
            url (str): The AWS service URL containing the canonical URI and
                query string.
            method (str): The HTTP method used to call this API.
            request_payload (Optional[str]): The optional request payload if
                available.
            additional_headers (Optional[Mapping[str, str]]): The optional
                additional headers needed for the requested AWS API.

        Returns:
            Mapping[str, str]: The AWS signed request dictionary object.
        """

        additional_headers = additional_headers or {}

        uri = urllib.parse.urlparse(url)
        # Normalize the URL path. This is needed for the canonical_uri.
        # os.path.normpath can't be used since it normalizes "/" paths
        # to "\\" in Windows OS.
        normalized_uri = urllib.parse.urlparse(
            urljoin(url, posixpath.normpath(uri.path))
        )
        # Validate provided URL.
        if not uri.hostname or uri.scheme != "https":
            raise exceptions.InvalidResource("Invalid AWS service URL")

        header_map = _generate_authentication_header_map(
            host=uri.hostname,
            canonical_uri=normalized_uri.path or "/",
            canonical_querystring=_get_canonical_querystring(uri.query),
            method=method,
            region=self._region_name,
            aws_security_credentials=aws_security_credentials,
            request_payload=request_payload,
            additional_headers=additional_headers,
        )
        headers = {
            "Authorization": header_map.get("authorization_header"),
            "host": uri.hostname,
        }
        # Add x-amz-date if available.
        if "amz_date" in header_map:
            headers[_AWS_DATE_HEADER] = header_map.get("amz_date")
        # Append additional optional headers, eg. X-Amz-Target, Content-Type, etc.
        for key in additional_headers:
            headers[key] = additional_headers[key]

        # Add session token if available.
        if aws_security_credentials.session_token is not None:
            headers[_AWS_SECURITY_TOKEN_HEADER] = aws_security_credentials.session_token

        signed_request = {"url": url, "method": method, "headers": headers}
        if request_payload:
            signed_request["data"] = request_payload
        return signed_request


def _get_canonical_querystring(query):
    """Generates the canonical query string given a raw query string.
    Logic is based on
    https://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html

    Args:
        query (str): The raw query string.

    Returns:
        str: The canonical query string.
    """
    # Parse raw query string.
    querystring = urllib.parse.parse_qs(query)
    querystring_encoded_map = {}
    for key in querystring:
        quote_key = urllib.parse.quote(key, safe="-_.~")
        # URI encode key.
        querystring_encoded_map[quote_key] = []
        for item in querystring[key]:
            # For each key, URI encode all values for that key.
            querystring_encoded_map[quote_key].append(
                urllib.parse.quote(item, safe="-_.~")
            )
        # Sort values for each key.
        querystring_encoded_map[quote_key].sort()
    # Sort keys.
    sorted_keys = list(querystring_encoded_map.keys())
    sorted_keys.sort()
    # Reconstruct the query string. Preserve keys with multiple values.
    querystring_encoded_pairs = []
    for key in sorted_keys:
        for item in querystring_encoded_map[key]:
            querystring_encoded_pairs.append("{}={}".format(key, item))
    return "&".join(querystring_encoded_pairs)


def _sign(key, msg):
    """Creates the HMAC-SHA256 hash of the provided message using the provided
    key.

    Args:
        key (str): The HMAC-SHA256 key to use.
        msg (str): The message to hash.

    Returns:
        str: The computed hash bytes.
    """
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signing_key(key, date_stamp, region_name, service_name):
    """Calculates the signing key used to calculate the signature for
    AWS Signature Version 4 based on:
    https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html

    Args:
        key (str): The AWS secret access key.
        date_stamp (str): The '%Y%m%d' date format.
        region_name (str): The AWS region.
        service_name (str): The AWS service name, eg. sts.

    Returns:
        str: The signing key bytes.
    """
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


def _generate_authentication_header_map(
    host,
    canonical_uri,
    canonical_querystring,
    method,
    region,
    aws_security_credentials,
    request_payload="",
    additional_headers={},
):
    """Generates the authentication header map needed for generating the AWS
    Signature Version 4 signed request.

    Args:
        host (str): The AWS service URL hostname.
        canonical_uri (str): The AWS service URL path name.
        canonical_querystring (str): The AWS service URL query string.
        method (str): The HTTP method used to call this API.
        region (str): The AWS region.
        aws_security_credentials (AWSSecurityCredentials): The AWS security credentials.
        request_payload (Optional[str]): The optional request payload if
            available.
        additional_headers (Optional[Mapping[str, str]]): The optional
            additional headers needed for the requested AWS API.

    Returns:
        Mapping[str, str]: The AWS authentication header dictionary object.
            This contains the x-amz-date and authorization header information.
    """
    # iam.amazonaws.com host => iam service.
    # sts.us-east-2.amazonaws.com host => sts service.
    service_name = host.split(".")[0]

    current_time = _helpers.utcnow()
    amz_date = current_time.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = current_time.strftime("%Y%m%d")

    # Change all additional headers to be lower case.
    full_headers = {}
    for key in additional_headers:
        full_headers[key.lower()] = additional_headers[key]
    # Add AWS session token if available.
    if aws_security_credentials.session_token is not None:
        full_headers[
            _AWS_SECURITY_TOKEN_HEADER
        ] = aws_security_credentials.session_token

    # Required headers
    full_headers["host"] = host
    # Do not use generated x-amz-date if the date header is provided.
    # Previously the date was not fixed with x-amz- and could be provided
    # manually.
    # https://github.com/boto/botocore/blob/879f8440a4e9ace5d3cf145ce8b3d5e5ffb892ef/tests/unit/auth/aws4_testsuite/get-header-value-trim.req
    if "date" not in full_headers:
        full_headers[_AWS_DATE_HEADER] = amz_date

    # Header keys need to be sorted alphabetically.
    canonical_headers = ""
    header_keys = list(full_headers.keys())
    header_keys.sort()
    for key in header_keys:
        canonical_headers = "{}{}:{}\n".format(
            canonical_headers, key, full_headers[key]
        )
    signed_headers = ";".join(header_keys)

    payload_hash = hashlib.sha256((request_payload or "").encode("utf-8")).hexdigest()

    # https://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
    canonical_request = "{}\n{}\n{}\n{}\n{}\n{}".format(
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash,
    )

    credential_scope = "{}/{}/{}/{}".format(
        date_stamp, region, service_name, _AWS_REQUEST_TYPE
    )

    # https://docs.aws.amazon.com/general/latest/gr/sigv4-create-string-to-sign.html
    string_to_sign = "{}\n{}\n{}\n{}".format(
        _AWS_ALGORITHM,
        amz_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    )

    # https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
    signing_key = _get_signing_key(
        aws_security_credentials.secret_access_key, date_stamp, region, service_name
    )
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # https://docs.aws.amazon.com/general/latest/gr/sigv4-add-signature-to-request.html
    authorization_header = "{} Credential={}/{}, SignedHeaders={}, Signature={}".format(
        _AWS_ALGORITHM,
        aws_security_credentials.access_key_id,
        credential_scope,
        signed_headers,
        signature,
    )

    authentication_header = {"authorization_header": authorization_header}
    # Do not use generated x-amz-date if the date header is provided.
    if "date" not in full_headers:
        authentication_header["amz_date"] = amz_date
    return authentication_header


@dataclass
class AwsSecurityCredentials:
    """A class that models AWS security credentials with an optional session token.

        Attributes:
            access_key_id (str): The AWS security credentials access key id.
            secret_access_key (str): The AWS security credentials secret access key.
            session_token (Optional[str]): The optional AWS security credentials session token. This should be set when using temporary credentials.
    """

    access_key_id: str
    secret_access_key: str
    session_token: Optional[str] = None


class AwsSecurityCredentialsSupplier(metaclass=abc.ABCMeta):
    """Base class for AWS security credential suppliers. This can be implemented with custom logic to retrieve
    AWS security credentials to exchange for a Google Cloud access token. The AWS external account credential does
    not cache the AWS security credentials, so caching logic should be added in the implementation.
    """

    @abc.abstractmethod
    def get_aws_security_credentials(self, context, request):
        """Returns the AWS security credentials for the requested context.

        .. warning: This is not cached by the calling Google credential, so caching logic should be implemented in the supplier.

        Args:
            context (google.auth.externalaccount.SupplierContext): The context object
                containing information about the requested audience and subject token type.
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                security credential retrieval logic.

        Returns:
            AwsSecurityCredentials: The requested AWS security credentials.
        """
        raise NotImplementedError("")

    @abc.abstractmethod
    def get_aws_region(self, context, request):
        """Returns the AWS region for the requested context.

        Args:
            context (google.auth.externalaccount.SupplierContext): The context object
                containing information about the requested audience and subject token type.
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                region retrieval logic.

        Returns:
            str: The AWS region.
        """
        raise NotImplementedError("")


class _DefaultAwsSecurityCredentialsSupplier(AwsSecurityCredentialsSupplier):
    """Default implementation of AWS security credentials supplier. Supports retrieving
    credentials and region via EC2 metadata endpoints and environment variables.
    """

    def __init__(self, credential_source):
        self._region_url = credential_source.get("region_url")
        self._security_credentials_url = credential_source.get("url")
        self._imdsv2_session_token_url = credential_source.get(
            "imdsv2_session_token_url"
        )

    @_helpers.copy_docstring(AwsSecurityCredentialsSupplier)
    def get_aws_security_credentials(self, context, request):

        # Check environment variables for permanent credentials first.
        # https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html
        env_aws_access_key_id = os.environ.get(environment_vars.AWS_ACCESS_KEY_ID)
        env_aws_secret_access_key = os.environ.get(
            environment_vars.AWS_SECRET_ACCESS_KEY
        )
        # This is normally not available for permanent credentials.
        env_aws_session_token = os.environ.get(environment_vars.AWS_SESSION_TOKEN)
        if env_aws_access_key_id and env_aws_secret_access_key:
            return AwsSecurityCredentials(
                env_aws_access_key_id, env_aws_secret_access_key, env_aws_session_token
            )

        imdsv2_session_token = self._get_imdsv2_session_token(request)
        role_name = self._get_metadata_role_name(request, imdsv2_session_token)

        # Get security credentials.
        credentials = self._get_metadata_security_credentials(
            request, role_name, imdsv2_session_token
        )

        return AwsSecurityCredentials(
            credentials.get("AccessKeyId"),
            credentials.get("SecretAccessKey"),
            credentials.get("Token"),
        )

    @_helpers.copy_docstring(AwsSecurityCredentialsSupplier)
    def get_aws_region(self, context, request):
        # The AWS metadata server is not available in some AWS environments
        # such as AWS lambda. Instead, it is available via environment
        # variable.
        env_aws_region = os.environ.get(environment_vars.AWS_REGION)
        if env_aws_region is not None:
            return env_aws_region

        env_aws_region = os.environ.get(environment_vars.AWS_DEFAULT_REGION)
        if env_aws_region is not None:
            return env_aws_region

        if not self._region_url:
            raise exceptions.RefreshError("Unable to determine AWS region")

        headers = None
        imdsv2_session_token = self._get_imdsv2_session_token(request)
        if imdsv2_session_token is not None:
            headers = {"X-aws-ec2-metadata-token": imdsv2_session_token}

        response = request(url=self._region_url, method="GET", headers=headers)

        # Support both string and bytes type response.data.
        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        if response.status != http_client.OK:
            raise exceptions.RefreshError(
                "Unable to retrieve AWS region: {}".format(response_body)
            )

        # This endpoint will return the region in format: us-east-2b.
        # Only the us-east-2 part should be used.
        return response_body[:-1]

    def _get_imdsv2_session_token(self, request):
        if request is not None and self._imdsv2_session_token_url is not None:
            headers = {
                "X-aws-ec2-metadata-token-ttl-seconds": _IMDSV2_SESSION_TOKEN_TTL_SECONDS
            }

            imdsv2_session_token_response = request(
                url=self._imdsv2_session_token_url, method="PUT", headers=headers
            )

            if imdsv2_session_token_response.status != http_client.OK:
                raise exceptions.RefreshError(
                    "Unable to retrieve AWS Session Token: {}".format(
                        imdsv2_session_token_response.data
                    )
                )

            return imdsv2_session_token_response.data
        else:
            return None

    def _get_metadata_security_credentials(
        self, request, role_name, imdsv2_session_token
    ):
        """Retrieves the AWS security credentials required for signing AWS
        requests from the AWS metadata server.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
            role_name (str): The AWS role name required by the AWS metadata
                server security_credentials endpoint in order to return the
                credentials.
            imdsv2_session_token (str): The AWS IMDSv2 session token to be added as a
                header in the requests to AWS metadata endpoint.

        Returns:
            Mapping[str, str]: The AWS metadata server security credentials
                response.

        Raises:
            google.auth.exceptions.RefreshError: If an error occurs while
                retrieving the AWS security credentials.
        """
        headers = {"Content-Type": "application/json"}
        if imdsv2_session_token is not None:
            headers["X-aws-ec2-metadata-token"] = imdsv2_session_token

        response = request(
            url="{}/{}".format(self._security_credentials_url, role_name),
            method="GET",
            headers=headers,
        )

        # support both string and bytes type response.data
        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        if response.status != http_client.OK:
            raise exceptions.RefreshError(
                "Unable to retrieve AWS security credentials: {}".format(response_body)
            )

        credentials_response = json.loads(response_body)

        return credentials_response

    def _get_metadata_role_name(self, request, imdsv2_session_token):
        """Retrieves the AWS role currently attached to the current AWS
        workload by querying the AWS metadata server. This is needed for the
        AWS metadata server security credentials endpoint in order to retrieve
        the AWS security credentials needed to sign requests to AWS APIs.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
            imdsv2_session_token (str): The AWS IMDSv2 session token to be added as a
                header in the requests to AWS metadata endpoint.

        Returns:
            str: The AWS role name.

        Raises:
            google.auth.exceptions.RefreshError: If an error occurs while
                retrieving the AWS role name.
        """
        if self._security_credentials_url is None:
            raise exceptions.RefreshError(
                "Unable to determine the AWS metadata server security credentials endpoint"
            )

        headers = None
        if imdsv2_session_token is not None:
            headers = {"X-aws-ec2-metadata-token": imdsv2_session_token}

        response = request(
            url=self._security_credentials_url, method="GET", headers=headers
        )

        # support both string and bytes type response.data
        response_body = (
            response.data.decode("utf-8")
            if hasattr(response.data, "decode")
            else response.data
        )

        if response.status != http_client.OK:
            raise exceptions.RefreshError(
                "Unable to retrieve AWS role name {}".format(response_body)
            )

        return response_body


class Credentials(external_account.Credentials):
    """AWS external account credentials.
    This is used to exchange serialized AWS signature v4 signed requests to
    AWS STS GetCallerIdentity service for Google access tokens.
    """

    def __init__(
        self,
        audience,
        subject_token_type,
        token_url=external_account._DEFAULT_TOKEN_URL,
        credential_source=None,
        aws_security_credentials_supplier=None,
        *args,
        **kwargs
    ):
        """Instantiates an AWS workload external account credentials object.

        Args:
            audience (str): The STS audience field.
            subject_token_type (str): The subject token type based on the Oauth2.0 token exchange spec.
                Expected values include::

                    “urn:ietf:params:aws:token-type:aws4_request”

            token_url (Optional [str]): The STS endpoint URL. If not provided, will default to "https://sts.googleapis.com/v1/token".
            credential_source (Optional [Mapping]): The credential source dictionary used
                to provide instructions on how to retrieve external credential to be exchanged for Google access tokens.
                Either a credential source or an AWS security credentials supplier must be provided.

                Example credential_source for AWS credential::

                    {
                        "environment_id": "aws1",
                        "regional_cred_verification_url": "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15",
                        "region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
                        "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
                        imdsv2_session_token_url": "http://169.254.169.254/latest/api/token"
                    }

            aws_security_credentials_supplier (Optional [AwsSecurityCredentialsSupplier]): Optional AWS security credentials supplier.
                This will be called to supply valid AWS security credentails which will then
                be exchanged for Google access tokens. Either an AWS security credentials supplier
                or a credential source must be provided.
            args (List): Optional positional arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.
            kwargs (Mapping): Optional keyword arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                access token retrieval logic.
            ValueError: For invalid parameters.

        .. note:: Typically one of the helper constructors
            :meth:`from_file` or
            :meth:`from_info` are used instead of calling the constructor directly.
        """
        super(Credentials, self).__init__(
            audience=audience,
            subject_token_type=subject_token_type,
            token_url=token_url,
            credential_source=credential_source,
            *args,
            **kwargs
        )
        if credential_source is None and aws_security_credentials_supplier is None:
            raise exceptions.InvalidValue(
                "A valid credential source or AWS security credentials supplier must be provided."
            )
        if (
            credential_source is not None
            and aws_security_credentials_supplier is not None
        ):
            raise exceptions.InvalidValue(
                "AWS credential cannot have both a credential source and an AWS security credentials supplier."
            )

        if aws_security_credentials_supplier:
            self._aws_security_credentials_supplier = aws_security_credentials_supplier
            # The regional cred verification URL would normally be provided through the credential source. So set it to the default one here.
            self._cred_verification_url = (
                _DEFAULT_AWS_REGIONAL_CREDENTIAL_VERIFICATION_URL
            )
        else:
            environment_id = credential_source.get("environment_id") or ""
            self._aws_security_credentials_supplier = _DefaultAwsSecurityCredentialsSupplier(
                credential_source
            )
            self._cred_verification_url = credential_source.get(
                "regional_cred_verification_url"
            )

            # Get the environment ID, i.e. "aws1". Currently, only one version supported (1).
            matches = re.match(r"^(aws)([\d]+)$", environment_id)
            if matches:
                env_id, env_version = matches.groups()
            else:
                env_id, env_version = (None, None)

            if env_id != "aws" or self._cred_verification_url is None:
                raise exceptions.InvalidResource(
                    "No valid AWS 'credential_source' provided"
                )
            elif env_version is None or int(env_version) != 1:
                raise exceptions.InvalidValue(
                    "aws version '{}' is not supported in the current build.".format(
                        env_version
                    )
                )

        self._target_resource = audience
        self._request_signer = None

    def retrieve_subject_token(self, request):
        """Retrieves the subject token using the credential_source object.
        The subject token is a serialized `AWS GetCallerIdentity signed request`_.

        The logic is summarized as:

        Retrieve the AWS region from the AWS_REGION or AWS_DEFAULT_REGION
        environment variable or from the AWS metadata server availability-zone
        if not found in the environment variable.

        Check AWS credentials in environment variables. If not found, retrieve
        from the AWS metadata server security-credentials endpoint.

        When retrieving AWS credentials from the metadata server
        security-credentials endpoint, the AWS role needs to be determined by
        calling the security-credentials endpoint without any argument. Then the
        credentials can be retrieved via: security-credentials/role_name

        Generate the signed request to AWS STS GetCallerIdentity action.

        Inject x-goog-cloud-target-resource into header and serialize the
        signed request. This will be the subject-token to pass to GCP STS.

        .. _AWS GetCallerIdentity signed request:
            https://cloud.google.com/iam/docs/access-resources-aws#exchange-token

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
        Returns:
            str: The retrieved subject token.
        """

        # Initialize the request signer if not yet initialized after determining
        # the current AWS region.
        if self._request_signer is None:
            self._region = self._aws_security_credentials_supplier.get_aws_region(
                self._supplier_context, request
            )
            self._request_signer = RequestSigner(self._region)

        # Retrieve the AWS security credentials needed to generate the signed
        # request.
        aws_security_credentials = self._aws_security_credentials_supplier.get_aws_security_credentials(
            self._supplier_context, request
        )
        # Generate the signed request to AWS STS GetCallerIdentity API.
        # Use the required regional endpoint. Otherwise, the request will fail.
        request_options = self._request_signer.get_request_options(
            aws_security_credentials,
            self._cred_verification_url.replace("{region}", self._region),
            "POST",
        )
        # The GCP STS endpoint expects the headers to be formatted as:
        # [
        #   {key: 'x-amz-date', value: '...'},
        #   {key: 'Authorization', value: '...'},
        #   ...
        # ]
        # And then serialized as:
        # quote(json.dumps({
        #   url: '...',
        #   method: 'POST',
        #   headers: [{key: 'x-amz-date', value: '...'}, ...]
        # }))
        request_headers = request_options.get("headers")
        # The full, canonical resource name of the workload identity pool
        # provider, with or without the HTTPS prefix.
        # Including this header as part of the signature is recommended to
        # ensure data integrity.
        request_headers["x-goog-cloud-target-resource"] = self._target_resource

        # Serialize AWS signed request.
        aws_signed_req = {}
        aws_signed_req["url"] = request_options.get("url")
        aws_signed_req["method"] = request_options.get("method")
        aws_signed_req["headers"] = []
        # Reformat header to GCP STS expected format.
        for key in request_headers.keys():
            aws_signed_req["headers"].append(
                {"key": key, "value": request_headers[key]}
            )

        return urllib.parse.quote(
            json.dumps(aws_signed_req, separators=(",", ":"), sort_keys=True)
        )

    def _create_default_metrics_options(self):
        metrics_options = super(Credentials, self)._create_default_metrics_options()
        metrics_options["source"] = "aws"
        if self._has_custom_supplier():
            metrics_options["source"] = "programmatic"
        return metrics_options

    def _has_custom_supplier(self):
        return self._credential_source is None

    def _constructor_args(self):
        args = super(Credentials, self)._constructor_args()
        # If a custom supplier was used, append it to the args dict.
        if self._has_custom_supplier():
            args.update(
                {
                    "aws_security_credentials_supplier": self._aws_security_credentials_supplier
                }
            )
        return args

    @classmethod
    def from_info(cls, info, **kwargs):
        """Creates an AWS Credentials instance from parsed external account info.

        Args:
            info (Mapping[str, str]): The AWS external account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.aws.Credentials: The constructed credentials.

        Raises:
            ValueError: For invalid parameters.
        """
        aws_security_credentials_supplier = info.get(
            "aws_security_credentials_supplier"
        )
        kwargs.update(
            {"aws_security_credentials_supplier": aws_security_credentials_supplier}
        )
        return super(Credentials, cls).from_info(info, **kwargs)

    @classmethod
    def from_file(cls, filename, **kwargs):
        """Creates an AWS Credentials instance from an external account json file.

        Args:
            filename (str): The path to the AWS external account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.aws.Credentials: The constructed credentials.
        """
        return super(Credentials, cls).from_file(filename, **kwargs)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_vars.py ===
""" pydevd_vars deals with variables:
    resolution/conversion to XML.
"""
import pickle
from _pydevd_bundle.pydevd_constants import get_frame, get_current_thread_id, iter_chars, silence_warnings_decorator, get_global_debugger

from _pydevd_bundle.pydevd_xml import ExceptionOnEvaluate, get_type, var_to_xml
from _pydev_bundle import pydev_log
import functools
from _pydevd_bundle.pydevd_thread_lifecycle import resume_threads, mark_thread_suspended, suspend_all_threads
from _pydevd_bundle.pydevd_comm_constants import CMD_SET_BREAK

import sys  # @Reimport

from _pydev_bundle._pydev_saved_modules import threading
from _pydevd_bundle import pydevd_save_locals, pydevd_timeout, pydevd_constants
from _pydev_bundle.pydev_imports import Exec, execfile
from _pydevd_bundle.pydevd_utils import to_string, ScopeRequest
import inspect
from _pydevd_bundle.pydevd_daemon_thread import PyDBDaemonThread
from _pydevd_bundle.pydevd_save_locals import update_globals_and_locals
from functools import lru_cache
from typing import Optional

SENTINEL_VALUE = []


class VariableError(RuntimeError):
    pass


def iter_frames(frame):
    while frame is not None:
        yield frame
        frame = frame.f_back
    frame = None


def dump_frames(thread_id):
    sys.stdout.write("dumping frames\n")
    if thread_id != get_current_thread_id(threading.current_thread()):
        raise VariableError("find_frame: must execute on same thread")

    frame = get_frame()
    for frame in iter_frames(frame):
        sys.stdout.write("%s\n" % pickle.dumps(frame))


@silence_warnings_decorator
def getVariable(dbg, thread_id, frame_id, scope, locator):
    """
    returns the value of a variable

    :scope: can be BY_ID, EXPRESSION, GLOBAL, LOCAL, FRAME

    BY_ID means we'll traverse the list of all objects alive to get the object.

    :locator: after reaching the proper scope, we have to get the attributes until we find
            the proper location (i.e.: obj\tattr1\tattr2)

    :note: when BY_ID is used, the frame_id is considered the id of the object to find and
           not the frame (as we don't care about the frame in this case).
    """
    if scope == "BY_ID":
        if thread_id != get_current_thread_id(threading.current_thread()):
            raise VariableError("getVariable: must execute on same thread")

        try:
            import gc

            objects = gc.get_objects()
        except:
            pass  # Not all python variants have it.
        else:
            frame_id = int(frame_id)
            for var in objects:
                if id(var) == frame_id:
                    if locator is not None:
                        locator_parts = locator.split("\t")
                        for k in locator_parts:
                            _type, _type_name, resolver = get_type(var)
                            var = resolver.resolve(var, k)

                    return var

        # If it didn't return previously, we coudn't find it by id (i.e.: already garbage collected).
        sys.stderr.write("Unable to find object with id: %s\n" % (frame_id,))
        return None

    frame = dbg.find_frame(thread_id, frame_id)
    if frame is None:
        return {}

    if locator is not None:
        locator_parts = locator.split("\t")
    else:
        locator_parts = []

    for attr in locator_parts:
        attr.replace("@_@TAB_CHAR@_@", "\t")

    if scope == "EXPRESSION":
        for count in range(len(locator_parts)):
            if count == 0:
                # An Expression can be in any scope (globals/locals), therefore it needs to evaluated as an expression
                var = evaluate_expression(dbg, frame, locator_parts[count], False)
            else:
                _type, _type_name, resolver = get_type(var)
                var = resolver.resolve(var, locator_parts[count])
    else:
        if scope == "GLOBAL":
            var = frame.f_globals
            del locator_parts[0]  # globals are special, and they get a single dummy unused attribute
        else:
            # in a frame access both locals and globals as Python does
            var = {}
            var.update(frame.f_globals)
            var.update(frame.f_locals)

        for k in locator_parts:
            _type, _type_name, resolver = get_type(var)
            var = resolver.resolve(var, k)

    return var


def resolve_compound_variable_fields(dbg, thread_id, frame_id, scope, attrs):
    """
    Resolve compound variable in debugger scopes by its name and attributes

    :param thread_id: id of the variable's thread
    :param frame_id: id of the variable's frame
    :param scope: can be BY_ID, EXPRESSION, GLOBAL, LOCAL, FRAME
    :param attrs: after reaching the proper scope, we have to get the attributes until we find
            the proper location (i.e.: obj\tattr1\tattr2)
    :return: a dictionary of variables's fields
    """

    var = getVariable(dbg, thread_id, frame_id, scope, attrs)

    try:
        _type, type_name, resolver = get_type(var)
        return type_name, resolver.get_dictionary(var)
    except:
        pydev_log.exception("Error evaluating: thread_id: %s\nframe_id: %s\nscope: %s\nattrs: %s.", thread_id, frame_id, scope, attrs)


def resolve_var_object(var, attrs):
    """
    Resolve variable's attribute

    :param var: an object of variable
    :param attrs: a sequence of variable's attributes separated by \t (i.e.: obj\tattr1\tattr2)
    :return: a value of resolved variable's attribute
    """
    if attrs is not None:
        attr_list = attrs.split("\t")
    else:
        attr_list = []
    for k in attr_list:
        type, _type_name, resolver = get_type(var)
        var = resolver.resolve(var, k)
    return var


def resolve_compound_var_object_fields(var, attrs):
    """
    Resolve compound variable by its object and attributes

    :param var: an object of variable
    :param attrs: a sequence of variable's attributes separated by \t (i.e.: obj\tattr1\tattr2)
    :return: a dictionary of variables's fields
    """
    attr_list = attrs.split("\t")

    for k in attr_list:
        type, _type_name, resolver = get_type(var)
        var = resolver.resolve(var, k)

    try:
        type, _type_name, resolver = get_type(var)
        return resolver.get_dictionary(var)
    except:
        pydev_log.exception()


def custom_operation(dbg, thread_id, frame_id, scope, attrs, style, code_or_file, operation_fn_name):
    """
    We'll execute the code_or_file and then search in the namespace the operation_fn_name to execute with the given var.

    code_or_file: either some code (i.e.: from pprint import pprint) or a file to be executed.
    operation_fn_name: the name of the operation to execute after the exec (i.e.: pprint)
    """
    expressionValue = getVariable(dbg, thread_id, frame_id, scope, attrs)

    try:
        namespace = {"__name__": "<custom_operation>"}
        if style == "EXECFILE":
            namespace["__file__"] = code_or_file
            execfile(code_or_file, namespace, namespace)
        else:  # style == EXEC
            namespace["__file__"] = "<customOperationCode>"
            Exec(code_or_file, namespace, namespace)

        return str(namespace[operation_fn_name](expressionValue))
    except:
        pydev_log.exception()


@lru_cache(3)
def _expression_to_evaluate(expression):
    keepends = True
    lines = expression.splitlines(keepends)
    # find first non-empty line
    chars_to_strip = 0
    for line in lines:
        if line.strip():  # i.e.: check first non-empty line
            for c in iter_chars(line):
                if c.isspace():
                    chars_to_strip += 1
                else:
                    break
            break

    if chars_to_strip:
        # I.e.: check that the chars we'll remove are really only whitespaces.
        proceed = True
        new_lines = []
        for line in lines:
            if not proceed:
                break
            for c in iter_chars(line[:chars_to_strip]):
                if not c.isspace():
                    proceed = False
                    break

            new_lines.append(line[chars_to_strip:])

        if proceed:
            if isinstance(expression, bytes):
                expression = b"".join(new_lines)
            else:
                expression = "".join(new_lines)

    return expression


def eval_in_context(expression, global_vars, local_vars, py_db=None):
    result = None
    try:
        compiled = compile_as_eval(expression)
        is_async = inspect.CO_COROUTINE & compiled.co_flags == inspect.CO_COROUTINE

        if is_async:
            if py_db is None:
                py_db = get_global_debugger()
                if py_db is None:
                    raise RuntimeError("Cannot evaluate async without py_db.")
            t = _EvalAwaitInNewEventLoop(py_db, compiled, global_vars, local_vars)
            t.start()
            t.join()

            if t.exc:
                raise t.exc[1].with_traceback(t.exc[2])
            else:
                result = t.evaluated_value
        else:
            result = eval(compiled, global_vars, local_vars)
    except (Exception, KeyboardInterrupt):
        etype, result, tb = sys.exc_info()
        result = ExceptionOnEvaluate(result, etype, tb)

        # Ok, we have the initial error message, but let's see if we're dealing with a name mangling error...
        try:
            if ".__" in expression:
                # Try to handle '__' name mangling (for simple cases such as self.__variable.__another_var).
                split = expression.split(".")
                entry = split[0]

                if local_vars is None:
                    local_vars = global_vars
                curr = local_vars[entry]  # Note: we want the KeyError if it's not there.
                for entry in split[1:]:
                    if entry.startswith("__") and not hasattr(curr, entry):
                        entry = "_%s%s" % (curr.__class__.__name__, entry)
                    curr = getattr(curr, entry)

                result = curr
        except:
            pass
    return result


def _run_with_interrupt_thread(original_func, py_db, curr_thread, frame, expression, is_exec):
    on_interrupt_threads = None
    timeout_tracker = py_db.timeout_tracker  # : :type timeout_tracker: TimeoutTracker

    interrupt_thread_timeout = pydevd_constants.PYDEVD_INTERRUPT_THREAD_TIMEOUT

    if interrupt_thread_timeout > 0:
        on_interrupt_threads = pydevd_timeout.create_interrupt_this_thread_callback()
        pydev_log.info("Doing evaluate with interrupt threads timeout: %s.", interrupt_thread_timeout)

    if on_interrupt_threads is None:
        return original_func(py_db, frame, expression, is_exec)
    else:
        with timeout_tracker.call_on_timeout(interrupt_thread_timeout, on_interrupt_threads):
            return original_func(py_db, frame, expression, is_exec)


def _run_with_unblock_threads(original_func, py_db, curr_thread, frame, expression, is_exec):
    on_timeout_unblock_threads = None
    timeout_tracker = py_db.timeout_tracker  # : :type timeout_tracker: TimeoutTracker

    if py_db.multi_threads_single_notification:
        unblock_threads_timeout = pydevd_constants.PYDEVD_UNBLOCK_THREADS_TIMEOUT
    else:
        unblock_threads_timeout = -1  # Don't use this if threads are managed individually.

    if unblock_threads_timeout >= 0:
        pydev_log.info("Doing evaluate with unblock threads timeout: %s.", unblock_threads_timeout)
        tid = get_current_thread_id(curr_thread)

        def on_timeout_unblock_threads():
            on_timeout_unblock_threads.called = True
            pydev_log.info("Resuming threads after evaluate timeout.")
            resume_threads("*", except_thread=curr_thread)
            py_db.threads_suspended_single_notification.on_thread_resume(tid, curr_thread)

        on_timeout_unblock_threads.called = False

    try:
        if on_timeout_unblock_threads is None:
            return _run_with_interrupt_thread(original_func, py_db, curr_thread, frame, expression, is_exec)
        else:
            with timeout_tracker.call_on_timeout(unblock_threads_timeout, on_timeout_unblock_threads):
                return _run_with_interrupt_thread(original_func, py_db, curr_thread, frame, expression, is_exec)

    finally:
        if on_timeout_unblock_threads is not None and on_timeout_unblock_threads.called:
            mark_thread_suspended(curr_thread, CMD_SET_BREAK)
            py_db.threads_suspended_single_notification.increment_suspend_time()
            suspend_all_threads(py_db, except_thread=curr_thread)
            py_db.threads_suspended_single_notification.on_thread_suspend(tid, curr_thread, CMD_SET_BREAK)


def _evaluate_with_timeouts(original_func):
    """
    Provides a decorator that wraps the original evaluate to deal with slow evaluates.

    If some evaluation is too slow, we may show a message, resume threads or interrupt them
    as needed (based on the related configurations).
    """

    @functools.wraps(original_func)
    def new_func(py_db, frame, expression, is_exec):
        if py_db is None:
            # Only for testing...
            pydev_log.critical("_evaluate_with_timeouts called without py_db!")
            return original_func(py_db, frame, expression, is_exec)
        warn_evaluation_timeout = pydevd_constants.PYDEVD_WARN_EVALUATION_TIMEOUT
        curr_thread = threading.current_thread()

        def on_warn_evaluation_timeout():
            py_db.writer.add_command(py_db.cmd_factory.make_evaluation_timeout_msg(py_db, expression, curr_thread))

        timeout_tracker = py_db.timeout_tracker  # : :type timeout_tracker: TimeoutTracker
        with timeout_tracker.call_on_timeout(warn_evaluation_timeout, on_warn_evaluation_timeout):
            return _run_with_unblock_threads(original_func, py_db, curr_thread, frame, expression, is_exec)

    return new_func


_ASYNC_COMPILE_FLAGS = None
try:
    from ast import PyCF_ALLOW_TOP_LEVEL_AWAIT

    _ASYNC_COMPILE_FLAGS = PyCF_ALLOW_TOP_LEVEL_AWAIT
except:
    pass


def compile_as_eval(expression):
    """

    :param expression:
        The expression to be _compiled.

    :return: code object

    :raises Exception if the expression cannot be evaluated.
    """
    expression_to_evaluate = _expression_to_evaluate(expression)
    if _ASYNC_COMPILE_FLAGS is not None:
        return compile(expression_to_evaluate, "<string>", "eval", _ASYNC_COMPILE_FLAGS)
    else:
        return compile(expression_to_evaluate, "<string>", "eval")


def _compile_as_exec(expression):
    """

    :param expression:
        The expression to be _compiled.

    :return: code object

    :raises Exception if the expression cannot be evaluated.
    """
    expression_to_evaluate = _expression_to_evaluate(expression)
    if _ASYNC_COMPILE_FLAGS is not None:
        return compile(expression_to_evaluate, "<string>", "exec", _ASYNC_COMPILE_FLAGS)
    else:
        return compile(expression_to_evaluate, "<string>", "exec")


class _EvalAwaitInNewEventLoop(PyDBDaemonThread):
    def __init__(self, py_db, compiled, updated_globals, updated_locals):
        PyDBDaemonThread.__init__(self, py_db)
        self._compiled = compiled
        self._updated_globals = updated_globals
        self._updated_locals = updated_locals

        # Output
        self.evaluated_value = None
        self.exc = None

    async def _async_func(self):
        return await eval(self._compiled, self._updated_locals, self._updated_globals)

    def _on_run(self):
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.evaluated_value = asyncio.run(self._async_func())
        except:
            self.exc = sys.exc_info()


@_evaluate_with_timeouts
def evaluate_expression(py_db, frame, expression, is_exec):
    """
    :param str expression:
        The expression to be evaluated.

        Note that if the expression is indented it's automatically dedented (based on the indentation
        found on the first non-empty line).

        i.e.: something as:

        `
            def method():
                a = 1
        `

        becomes:

        `
        def method():
            a = 1
        `

        Also, it's possible to evaluate calls with a top-level await (currently this is done by
        creating a new event loop in a new thread and making the evaluate at that thread -- note
        that this is still done synchronously so the evaluation has to finish before this
        function returns).

    :param is_exec: determines if we should do an exec or an eval.
        There are some changes in this function depending on whether it's an exec or an eval.

        When it's an exec (i.e.: is_exec==True):
            This function returns None.
            Any exception that happens during the evaluation is reraised.
            If the expression could actually be evaluated, the variable is printed to the console if not None.

        When it's an eval (i.e.: is_exec==False):
            This function returns the result from the evaluation.
            If some exception happens in this case, the exception is caught and a ExceptionOnEvaluate is returned.
            Also, in this case we try to resolve name-mangling (i.e.: to be able to add a self.__my_var watch).

    :param py_db:
        The debugger. Only needed if some top-level await is detected (for creating a
        PyDBDaemonThread).
    """
    if frame is None:
        return

    # This is very tricky. Some statements can change locals and use them in the same
    # call (see https://github.com/microsoft/debugpy/issues/815), also, if locals and globals are
    # passed separately, it's possible that one gets updated but apparently Python will still
    # try to load from the other, so, what's done is that we merge all in a single dict and
    # then go on and update the frame with the results afterwards.

    # -- see tests in test_evaluate_expression.py

    # This doesn't work because the variables aren't updated in the locals in case the
    # evaluation tries to set a variable and use it in the same expression.
    # updated_globals = frame.f_globals
    # updated_locals = frame.f_locals

    # This doesn't work because the variables aren't updated in the locals in case the
    # evaluation tries to set a variable and use it in the same expression.
    # updated_globals = {}
    # updated_globals.update(frame.f_globals)
    # updated_globals.update(frame.f_locals)
    #
    # updated_locals = frame.f_locals

    # This doesn't work either in the case where the evaluation tries to set a variable and use
    # it in the same expression (I really don't know why as it seems like this *should* work
    # in theory but doesn't in practice).
    # updated_globals = {}
    # updated_globals.update(frame.f_globals)
    #
    # updated_locals = {}
    # updated_globals.update(frame.f_locals)

    # This is the only case that worked consistently to run the tests in test_evaluate_expression.py
    # It's a bit unfortunate because although the exec works in this case, we have to manually
    # put the updates in the frame locals afterwards.
    updated_globals = {}
    updated_globals.update(frame.f_globals)
    updated_globals.update(frame.f_locals)
    if "globals" not in updated_globals:
        # If the user explicitly uses 'globals()' then we provide the
        # frame globals (unless he has shadowed it already).
        updated_globals["globals"] = lambda: frame.f_globals

    initial_globals = updated_globals.copy()

    updated_locals = None

    try:
        expression = expression.replace("@LINE@", "\n")

        if is_exec:
            try:
                # Try to make it an eval (if it is an eval we can print it, otherwise we'll exec it and
                # it will have whatever the user actually did)
                compiled = compile_as_eval(expression)
            except Exception:
                compiled = None

            if compiled is None:
                try:
                    compiled = _compile_as_exec(expression)
                    is_async = inspect.CO_COROUTINE & compiled.co_flags == inspect.CO_COROUTINE
                    if is_async:
                        t = _EvalAwaitInNewEventLoop(py_db, compiled, updated_globals, updated_locals)
                        t.start()
                        t.join()

                        if t.exc:
                            raise t.exc[1].with_traceback(t.exc[2])
                    else:
                        Exec(compiled, updated_globals, updated_locals)
                finally:
                    # Update the globals even if it errored as it may have partially worked.
                    update_globals_and_locals(updated_globals, initial_globals, frame)
            else:
                is_async = inspect.CO_COROUTINE & compiled.co_flags == inspect.CO_COROUTINE
                if is_async:
                    t = _EvalAwaitInNewEventLoop(py_db, compiled, updated_globals, updated_locals)
                    t.start()
                    t.join()

                    if t.exc:
                        raise t.exc[1].with_traceback(t.exc[2])
                    else:
                        result = t.evaluated_value
                else:
                    result = eval(compiled, updated_globals, updated_locals)
                if result is not None:  # Only print if it's not None (as python does)
                    sys.stdout.write("%s\n" % (result,))
            return

        else:
            ret = eval_in_context(expression, updated_globals, updated_locals, py_db)
            try:
                is_exception_returned = ret.__class__ == ExceptionOnEvaluate
            except:
                pass
            else:
                if not is_exception_returned:
                    # i.e.: by using a walrus assignment (:=), expressions can change the locals,
                    # so, make sure that we save the locals back to the frame.
                    update_globals_and_locals(updated_globals, initial_globals, frame)
            return ret
    finally:
        # Should not be kept alive if an exception happens and this frame is kept in the stack.
        del updated_globals
        del updated_locals
        del initial_globals
        del frame


def change_attr_expression(frame, attr, expression, dbg, value=SENTINEL_VALUE, /, scope: Optional[ScopeRequest]=None):
    """Changes some attribute in a given frame."""
    if frame is None:
        return

    if scope is not None:
        assert isinstance(scope, ScopeRequest)
        scope = scope.scope

    try:
        expression = expression.replace("@LINE@", "\n")

        if dbg.plugin and value is SENTINEL_VALUE:
            result = dbg.plugin.change_variable(frame, attr, expression)
            if result is not dbg.plugin.EMPTY_SENTINEL:
                return result

        if attr[:7] == "Globals" or scope == "globals":
            attr = attr[8:] if attr.startswith("Globals") else attr
            if attr in frame.f_globals:
                if value is SENTINEL_VALUE:
                    value = eval(expression, frame.f_globals, frame.f_locals)
                frame.f_globals[attr] = value
                return frame.f_globals[attr]
            else:
                raise VariableError("Attribute %s not found in globals" % attr)
        else:
            if "." not in attr:  # i.e.: if we have a '.', we're changing some attribute of a local var.
                if pydevd_save_locals.is_save_locals_available():
                    if value is SENTINEL_VALUE:
                        value = eval(expression, frame.f_globals, frame.f_locals)
                    frame.f_locals[attr] = value
                    pydevd_save_locals.save_locals(frame)
                    return frame.f_locals[attr]

            # i.e.: case with '.' or save locals not available (just exec the assignment in the frame).
            if value is SENTINEL_VALUE:
                value = eval(expression, frame.f_globals, frame.f_locals)
            result = value
            Exec("%s=%s" % (attr, expression), frame.f_globals, frame.f_locals)
            return result

    except Exception as e:
        pydev_log.exception(e)
    


MAXIMUM_ARRAY_SIZE = 100
MAX_SLICE_SIZE = 1000


def table_like_struct_to_xml(array, name, roffset, coffset, rows, cols, format):
    _, type_name, _ = get_type(array)
    if type_name == "ndarray":
        array, metaxml, r, c, f = array_to_meta_xml(array, name, format)
        xml = metaxml
        format = "%" + f
        if rows == -1 and cols == -1:
            rows = r
            cols = c
        xml += array_to_xml(array, roffset, coffset, rows, cols, format)
    elif type_name == "DataFrame":
        xml = dataframe_to_xml(array, name, roffset, coffset, rows, cols, format)
    else:
        raise VariableError("Do not know how to convert type %s to table" % (type_name))

    return "<xml>%s</xml>" % xml


def array_to_xml(array, roffset, coffset, rows, cols, format):
    xml = ""
    rows = min(rows, MAXIMUM_ARRAY_SIZE)
    cols = min(cols, MAXIMUM_ARRAY_SIZE)

    # there is no obvious rule for slicing (at least 5 choices)
    if len(array) == 1 and (rows > 1 or cols > 1):
        array = array[0]
    if array.size > len(array):
        array = array[roffset:, coffset:]
        rows = min(rows, len(array))
        cols = min(cols, len(array[0]))
        if len(array) == 1:
            array = array[0]
    elif array.size == len(array):
        if roffset == 0 and rows == 1:
            array = array[coffset:]
            cols = min(cols, len(array))
        elif coffset == 0 and cols == 1:
            array = array[roffset:]
            rows = min(rows, len(array))

    xml += '<arraydata rows="%s" cols="%s"/>' % (rows, cols)
    for row in range(rows):
        xml += '<row index="%s"/>' % to_string(row)
        for col in range(cols):
            value = array
            if rows == 1 or cols == 1:
                if rows == 1 and cols == 1:
                    value = array[0]
                else:
                    if rows == 1:
                        dim = col
                    else:
                        dim = row
                    value = array[dim]
                    if "ndarray" in str(type(value)):
                        value = value[0]
            else:
                value = array[row][col]
            value = format % value
            xml += var_to_xml(value, "")
    return xml


def array_to_meta_xml(array, name, format):
    type = array.dtype.kind
    slice = name
    l = len(array.shape)

    # initial load, compute slice
    if format == "%":
        if l > 2:
            slice += "[0]" * (l - 2)
            for r in range(l - 2):
                array = array[0]
        if type == "f":
            format = ".5f"
        elif type == "i" or type == "u":
            format = "d"
        else:
            format = "s"
    else:
        format = format.replace("%", "")

    l = len(array.shape)
    reslice = ""
    if l > 2:
        raise Exception("%s has more than 2 dimensions." % slice)
    elif l == 1:
        # special case with 1D arrays arr[i, :] - row, but arr[:, i] - column with equal shape and ndim
        # http://stackoverflow.com/questions/16837946/numpy-a-2-rows-1-column-file-loadtxt-returns-1row-2-columns
        # explanation: http://stackoverflow.com/questions/15165170/how-do-i-maintain-row-column-orientation-of-vectors-in-numpy?rq=1
        # we use kind of a hack - get information about memory from C_CONTIGUOUS
        is_row = array.flags["C_CONTIGUOUS"]

        if is_row:
            rows = 1
            cols = min(len(array), MAX_SLICE_SIZE)
            if cols < len(array):
                reslice = "[0:%s]" % (cols)
            array = array[0:cols]
        else:
            cols = 1
            rows = min(len(array), MAX_SLICE_SIZE)
            if rows < len(array):
                reslice = "[0:%s]" % (rows)
            array = array[0:rows]
    elif l == 2:
        rows = min(array.shape[-2], MAX_SLICE_SIZE)
        cols = min(array.shape[-1], MAX_SLICE_SIZE)
        if cols < array.shape[-1] or rows < array.shape[-2]:
            reslice = "[0:%s, 0:%s]" % (rows, cols)
        array = array[0:rows, 0:cols]

    # avoid slice duplication
    if not slice.endswith(reslice):
        slice += reslice

    bounds = (0, 0)
    if type in "biufc":
        bounds = (array.min(), array.max())
    xml = '<array slice="%s" rows="%s" cols="%s" format="%s" type="%s" max="%s" min="%s"/>' % (
        slice,
        rows,
        cols,
        format,
        type,
        bounds[1],
        bounds[0],
    )
    return array, xml, rows, cols, format


def dataframe_to_xml(df, name, roffset, coffset, rows, cols, format):
    """
    :type df: pandas.core.frame.DataFrame
    :type name: str
    :type coffset: int
    :type roffset: int
    :type rows: int
    :type cols: int
    :type format: str


    """
    num_rows = min(df.shape[0], MAX_SLICE_SIZE)
    num_cols = min(df.shape[1], MAX_SLICE_SIZE)
    if (num_rows, num_cols) != df.shape:
        df = df.iloc[0:num_rows, 0:num_cols]
        slice = ".iloc[0:%s, 0:%s]" % (num_rows, num_cols)
    else:
        slice = ""
    slice = name + slice
    xml = '<array slice="%s" rows="%s" cols="%s" format="" type="" max="0" min="0"/>\n' % (slice, num_rows, num_cols)

    if (rows, cols) == (-1, -1):
        rows, cols = num_rows, num_cols

    rows = min(rows, MAXIMUM_ARRAY_SIZE)
    cols = min(min(cols, MAXIMUM_ARRAY_SIZE), num_cols)
    # need to precompute column bounds here before slicing!
    col_bounds = [None] * cols
    for col in range(cols):
        dtype = df.dtypes.iloc[coffset + col].kind
        if dtype in "biufc":
            cvalues = df.iloc[:, coffset + col]
            bounds = (cvalues.min(), cvalues.max())
        else:
            bounds = (0, 0)
        col_bounds[col] = bounds

    df = df.iloc[roffset : roffset + rows, coffset : coffset + cols]
    rows, cols = df.shape

    xml += '<headerdata rows="%s" cols="%s">\n' % (rows, cols)
    format = format.replace("%", "")
    col_formats = []

    get_label = lambda label: str(label) if not isinstance(label, tuple) else "/".join(map(str, label))

    for col in range(cols):
        dtype = df.dtypes.iloc[col].kind
        if dtype == "f" and format:
            fmt = format
        elif dtype == "f":
            fmt = ".5f"
        elif dtype == "i" or dtype == "u":
            fmt = "d"
        else:
            fmt = "s"
        col_formats.append("%" + fmt)
        bounds = col_bounds[col]

        xml += '<colheader index="%s" label="%s" type="%s" format="%s" max="%s" min="%s" />\n' % (
            str(col),
            get_label(df.axes[1].values[col]),
            dtype,
            fmt,
            bounds[1],
            bounds[0],
        )
    for row, label in enumerate(iter(df.axes[0])):
        xml += '<rowheader index="%s" label = "%s"/>\n' % (str(row), get_label(label))
    xml += "</headerdata>\n"
    xml += '<arraydata rows="%s" cols="%s"/>\n' % (rows, cols)
    for row in range(rows):
        xml += '<row index="%s"/>\n' % str(row)
        for col in range(cols):
            value = df.iat[row, col]
            value = col_formats[col] % value
            xml += var_to_xml(value, "")
    return xml

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\text_service\async_client.py ===
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
import functools
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
)

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry_async as retries
from google.api_core.client_options import ClientOptions
from google.auth import credentials as ga_credentials  # type: ignore
from google.oauth2 import service_account  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version

try:
    OptionalRetry = Union[retries.AsyncRetry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.AsyncRetry, object, None]  # type: ignore

from google.longrunning import operations_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3.types import safety, text_service

from .client import TextServiceClient
from .transports.base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .transports.grpc_asyncio import TextServiceGrpcAsyncIOTransport


class TextServiceAsyncClient:
    """API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.
    """

    _client: TextServiceClient

    # Copy defaults from the synchronous client for use here.
    # Note: DEFAULT_ENDPOINT is deprecated. Use _DEFAULT_ENDPOINT_TEMPLATE instead.
    DEFAULT_ENDPOINT = TextServiceClient.DEFAULT_ENDPOINT
    DEFAULT_MTLS_ENDPOINT = TextServiceClient.DEFAULT_MTLS_ENDPOINT
    _DEFAULT_ENDPOINT_TEMPLATE = TextServiceClient._DEFAULT_ENDPOINT_TEMPLATE
    _DEFAULT_UNIVERSE = TextServiceClient._DEFAULT_UNIVERSE

    model_path = staticmethod(TextServiceClient.model_path)
    parse_model_path = staticmethod(TextServiceClient.parse_model_path)
    common_billing_account_path = staticmethod(
        TextServiceClient.common_billing_account_path
    )
    parse_common_billing_account_path = staticmethod(
        TextServiceClient.parse_common_billing_account_path
    )
    common_folder_path = staticmethod(TextServiceClient.common_folder_path)
    parse_common_folder_path = staticmethod(TextServiceClient.parse_common_folder_path)
    common_organization_path = staticmethod(TextServiceClient.common_organization_path)
    parse_common_organization_path = staticmethod(
        TextServiceClient.parse_common_organization_path
    )
    common_project_path = staticmethod(TextServiceClient.common_project_path)
    parse_common_project_path = staticmethod(
        TextServiceClient.parse_common_project_path
    )
    common_location_path = staticmethod(TextServiceClient.common_location_path)
    parse_common_location_path = staticmethod(
        TextServiceClient.parse_common_location_path
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """Creates an instance of this client using the provided credentials
            info.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            TextServiceAsyncClient: The constructed client.
        """
        return TextServiceClient.from_service_account_info.__func__(TextServiceAsyncClient, info, *args, **kwargs)  # type: ignore

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
            TextServiceAsyncClient: The constructed client.
        """
        return TextServiceClient.from_service_account_file.__func__(TextServiceAsyncClient, filename, *args, **kwargs)  # type: ignore

    from_service_account_json = from_service_account_file

    @classmethod
    def get_mtls_endpoint_and_cert_source(
        cls, client_options: Optional[ClientOptions] = None
    ):
        """Return the API endpoint and client cert source for mutual TLS.

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
        return TextServiceClient.get_mtls_endpoint_and_cert_source(client_options)  # type: ignore

    @property
    def transport(self) -> TextServiceTransport:
        """Returns the transport used by the client instance.

        Returns:
            TextServiceTransport: The transport used by the client instance.
        """
        return self._client.transport

    @property
    def api_endpoint(self):
        """Return the API endpoint used by the client instance.

        Returns:
            str: The API endpoint used by the client instance.
        """
        return self._client._api_endpoint

    @property
    def universe_domain(self) -> str:
        """Return the universe domain used by the client instance.

        Returns:
            str: The universe domain used
                by the client instance.
        """
        return self._client._universe_domain

    get_transport_class = functools.partial(
        type(TextServiceClient).get_transport_class, type(TextServiceClient)
    )

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Optional[
            Union[str, TextServiceTransport, Callable[..., TextServiceTransport]]
        ] = "grpc_asyncio",
        client_options: Optional[ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the text service async client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Optional[Union[str,TextServiceTransport,Callable[..., TextServiceTransport]]]):
                The transport to use, or a Callable that constructs and returns a new transport to use.
                If a Callable is given, it will be called with the same set of initialization
                arguments as used in the TextServiceTransport constructor.
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
                default "googleapis.com" universe. Note that ``api_endpoint``
                property still takes precedence; and ``universe_domain`` is
                currently not supported for mTLS.

            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        self._client = TextServiceClient(
            credentials=credentials,
            transport=transport,
            client_options=client_options,
            client_info=client_info,
        )

    async def generate_text(
        self,
        request: Optional[Union[text_service.GenerateTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        temperature: Optional[float] = None,
        candidate_count: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.GenerateTextResponse:
        r"""Generates a response from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_generate_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta3.GenerateTextRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.generate_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.GenerateTextRequest, dict]]):
                The request object. Request to generate a text completion
                response from the model.
            model (:class:`str`):
                Required. The name of the ``Model`` or ``TunedModel`` to
                use for generating the completion. Examples:
                models/text-bison-001
                tunedModels/sentence-translator-u3b7m

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta3.types.TextPrompt`):
                Required. The free-form input text
                given to the model as a prompt.
                Given a prompt, the model will generate
                a TextCompletion response it predicts as
                the completion of the input text.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            temperature (:class:`float`):
                Optional. Controls the randomness of the output. Note:
                The default value varies by model, see the
                ``Model.temperature`` attribute of the ``Model``
                returned the ``getModel`` function.

                Values can range from [0.0,1.0], inclusive. A value
                closer to 1.0 will produce responses that are more
                varied and creative, while a value closer to 0.0 will
                typically result in more straightforward responses from
                the model.

                This corresponds to the ``temperature`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            candidate_count (:class:`int`):
                Optional. Number of generated responses to return.

                This value must be between [1, 8], inclusive. If unset,
                this will default to 1.

                This corresponds to the ``candidate_count`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            max_output_tokens (:class:`int`):
                Optional. The maximum number of tokens to include in a
                candidate.

                If unset, this will default to output_token_limit
                specified in the ``Model`` specification.

                This corresponds to the ``max_output_tokens`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_p (:class:`float`):
                Optional. The maximum cumulative probability of tokens
                to consider when sampling.

                The model uses combined Top-k and nucleus sampling.

                Tokens are sorted based on their assigned probabilities
                so that only the most likely tokens are considered.
                Top-k sampling directly limits the maximum number of
                tokens to consider, while Nucleus sampling limits number
                of tokens based on the cumulative probability.

                Note: The default value varies by model, see the
                ``Model.top_p`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_p`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            top_k (:class:`int`):
                Optional. The maximum number of tokens to consider when
                sampling.

                The model uses combined Top-k and nucleus sampling.

                Top-k sampling considers the set of ``top_k`` most
                probable tokens. Defaults to 40.

                Note: The default value varies by model, see the
                ``Model.top_k`` attribute of the ``Model`` returned the
                ``getModel`` function.

                This corresponds to the ``top_k`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.GenerateTextResponse:
                The response from the model,
                including candidate completions.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any(
            [
                model,
                prompt,
                temperature,
                candidate_count,
                max_output_tokens,
                top_p,
                top_k,
            ]
        )
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.GenerateTextRequest):
            request = text_service.GenerateTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt
        if temperature is not None:
            request.temperature = temperature
        if candidate_count is not None:
            request.candidate_count = candidate_count
        if max_output_tokens is not None:
            request.max_output_tokens = max_output_tokens
        if top_p is not None:
            request.top_p = top_p
        if top_k is not None:
            request.top_k = top_k

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.generate_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def embed_text(
        self,
        request: Optional[Union[text_service.EmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        text: Optional[str] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.EmbedTextResponse:
        r"""Generates an embedding from the model given an input
        message.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_embed_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.EmbedTextRequest(
                    model="model_value",
                    text="text_value",
                )

                # Make the request
                response = await client.embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.EmbedTextRequest, dict]]):
                The request object. Request to get a text embedding from
                the model.
            model (:class:`str`):
                Required. The model name to use with
                the format model=models/{model}.

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            text (:class:`str`):
                Required. The free-form input text
                that the model will turn into an
                embedding.

                This corresponds to the ``text`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.EmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, text])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.EmbedTextRequest):
            request = text_service.EmbedTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if text is not None:
            request.text = text

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.embed_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def batch_embed_text(
        self,
        request: Optional[Union[text_service.BatchEmbedTextRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        texts: Optional[MutableSequence[str]] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.BatchEmbedTextResponse:
        r"""Generates multiple embeddings from the model given
        input text in a synchronous call.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_batch_embed_text():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceAsyncClient()

                # Initialize request argument(s)
                request = generativelanguage_v1beta3.BatchEmbedTextRequest(
                    model="model_value",
                    texts=['texts_value1', 'texts_value2'],
                )

                # Make the request
                response = await client.batch_embed_text(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.BatchEmbedTextRequest, dict]]):
                The request object. Batch request to get a text embedding
                from the model.
            model (:class:`str`):
                Required. The name of the ``Model`` to use for
                generating the embedding. Examples:
                models/embedding-gecko-001

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            texts (:class:`MutableSequence[str]`):
                Required. The free-form input texts
                that the model will turn into an
                embedding.  The current limit is 100
                texts, over which an error will be
                thrown.

                This corresponds to the ``texts`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.BatchEmbedTextResponse:
                The response to a EmbedTextRequest.
        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, texts])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.BatchEmbedTextRequest):
            request = text_service.BatchEmbedTextRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if texts:
            request.texts.extend(texts)

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.batch_embed_text
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def count_text_tokens(
        self,
        request: Optional[Union[text_service.CountTextTokensRequest, dict]] = None,
        *,
        model: Optional[str] = None,
        prompt: Optional[text_service.TextPrompt] = None,
        retry: OptionalRetry = gapic_v1.method.DEFAULT,
        timeout: Union[float, object] = gapic_v1.method.DEFAULT,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> text_service.CountTextTokensResponse:
        r"""Runs a model's tokenizer on a text and returns the
        token count.

        .. code-block:: python

            # This snippet has been automatically generated and should be regarded as a
            # code template only.
            # It will require modifications to work:
            # - It may require correct/in-range values for request initialization.
            # - It may require specifying regional endpoints when creating the service
            #   client as shown in:
            #   https://googleapis.dev/python/google-api-core/latest/client_options.html
            from google.ai import generativelanguage_v1beta3

            async def sample_count_text_tokens():
                # Create a client
                client = generativelanguage_v1beta3.TextServiceAsyncClient()

                # Initialize request argument(s)
                prompt = generativelanguage_v1beta3.TextPrompt()
                prompt.text = "text_value"

                request = generativelanguage_v1beta3.CountTextTokensRequest(
                    model="model_value",
                    prompt=prompt,
                )

                # Make the request
                response = await client.count_text_tokens(request=request)

                # Handle the response
                print(response)

        Args:
            request (Optional[Union[google.ai.generativelanguage_v1beta3.types.CountTextTokensRequest, dict]]):
                The request object. Counts the number of tokens in the ``prompt`` sent to a
                model.

                Models may tokenize text differently, so each model may
                return a different ``token_count``.
            model (:class:`str`):
                Required. The model's resource name. This serves as an
                ID for the Model to use.

                This name should match a model name returned by the
                ``ListModels`` method.

                Format: ``models/{model}``

                This corresponds to the ``model`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            prompt (:class:`google.ai.generativelanguage_v1beta3.types.TextPrompt`):
                Required. The free-form input text
                given to the model as a prompt.

                This corresponds to the ``prompt`` field
                on the ``request`` instance; if ``request`` is provided, this
                should not be set.
            retry (google.api_core.retry_async.AsyncRetry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            google.ai.generativelanguage_v1beta3.types.CountTextTokensResponse:
                A response from CountTextTokens.

                   It returns the model's token_count for the prompt.

        """
        # Create or coerce a protobuf request object.
        # - Quick check: If we got a request object, we should *not* have
        #   gotten any keyword arguments that map to the request.
        has_flattened_params = any([model, prompt])
        if request is not None and has_flattened_params:
            raise ValueError(
                "If the `request` argument is set, then none of "
                "the individual field arguments should be set."
            )

        # - Use the request object if provided (there's no risk of modifying the input as
        #   there are no flattened fields), or create one.
        if not isinstance(request, text_service.CountTextTokensRequest):
            request = text_service.CountTextTokensRequest(request)

        # If we have keyword arguments corresponding to fields on the
        # request, apply these.
        if model is not None:
            request.model = model
        if prompt is not None:
            request.prompt = prompt

        # Wrap the RPC method; this adds retry and timeout information,
        # and friendly error handling.
        rpc = self._client._transport._wrapped_methods[
            self._client._transport.count_text_tokens
        ]

        # Certain fields should be provided within the metadata header;
        # add these here.
        metadata = tuple(metadata) + (
            gapic_v1.routing_header.to_grpc_metadata((("model", request.model),)),
        )

        # Validate the universe domain.
        self._client._validate_universe_domain()

        # Send the request.
        response = await rpc(
            request,
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        # Done; return the response.
        return response

    async def __aenter__(self) -> "TextServiceAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.transport.close()


DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


__all__ = ("TextServiceAsyncClient",)

# === NexusCore/openenv\Lib\site-packages\nltk\draw\cfg.py ===
# Natural Language Toolkit: CFG visualization
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Visualization tools for CFGs.
"""

# Idea for a nice demo:
#   - 3 panes: grammar, treelet, working area
#     - grammar is a list of productions
#     - when you select a production, the treelet that it licenses appears
#       in the treelet area
#     - the working area has the text on the bottom, and S at top.  When
#       you select a production, it shows (ghosted) the locations where
#       that production's treelet could be attached to either the text
#       or the tree rooted at S.
#     - the user can drag the treelet onto one of those (or click on them?)
#     - the user can delete pieces of the tree from the working area
#       (right click?)
#     - connecting top to bottom? drag one NP onto another?
#
# +-------------------------------------------------------------+
# | S -> NP VP   |                 S                            |
# |[NP -> Det N ]|                / \                           |
# |     ...      |              NP  VP                          |
# | N -> 'dog'   |                                              |
# | N -> 'cat'   |                                              |
# |     ...      |                                              |
# +--------------+                                              |
# |      NP      |                      Det     N               |
# |     /  \     |                       |      |               |
# |   Det   N    |  the    cat    saw   the    dog              |
# |              |                                              |
# +--------------+----------------------------------------------+
#
# Operations:
#   - connect a new treelet -- drag or click shadow
#   - delete a treelet -- right click
#     - if only connected to top, delete everything below
#     - if only connected to bottom, delete everything above
#   - connect top & bottom -- drag a leaf to a root or a root to a leaf
#   - disconnect top & bottom -- right click
#     - if connected to top & bottom, then disconnect

import re
from tkinter import (
    Button,
    Canvas,
    Entry,
    Frame,
    IntVar,
    Label,
    Scrollbar,
    Text,
    Tk,
    Toplevel,
)

from nltk.draw.tree import TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import (
    CanvasFrame,
    ColorizedList,
    ShowText,
    SymbolWidget,
    TextWidget,
)
from nltk.grammar import CFG, Nonterminal, _read_cfg_production, nonterminals
from nltk.tree import Tree

######################################################################
# Production List
######################################################################


class ProductionList(ColorizedList):
    ARROW = SymbolWidget.SYMBOLS["rightarrow"]

    def _init_colortags(self, textwidget, options):
        textwidget.tag_config("terminal", foreground="#006000")
        textwidget.tag_config("arrow", font="symbol", underline="0")
        textwidget.tag_config(
            "nonterminal", foreground="blue", font=("helvetica", -12, "bold")
        )

    def _item_repr(self, item):
        contents = []
        contents.append(("%s\t" % item.lhs(), "nonterminal"))
        contents.append((self.ARROW, "arrow"))
        for elt in item.rhs():
            if isinstance(elt, Nonterminal):
                contents.append((" %s" % elt.symbol(), "nonterminal"))
            else:
                contents.append((" %r" % elt, "terminal"))
        return contents


######################################################################
# CFG Editor
######################################################################

_CFGEditor_HELP = """

The CFG Editor can be used to create or modify context free grammars.
A context free grammar consists of a start symbol and a list of
productions.  The start symbol is specified by the text entry field in
the upper right hand corner of the editor; and the list of productions
are specified in the main text editing box.

Every non-blank line specifies a single production.  Each production
has the form "LHS -> RHS," where LHS is a single nonterminal, and RHS
is a list of nonterminals and terminals.

Nonterminals must be a single word, such as S or NP or NP_subj.
Currently, nonterminals must consists of alphanumeric characters and
underscores (_).  Nonterminals are colored blue.  If you place the
mouse over any nonterminal, then all occurrences of that nonterminal
will be highlighted.

Terminals must be surrounded by single quotes (') or double
quotes(\").  For example, "dog" and "New York" are terminals.
Currently, the string within the quotes must consist of alphanumeric
characters, underscores, and spaces.

To enter a new production, go to a blank line, and type a nonterminal,
followed by an arrow (->), followed by a sequence of terminals and
nonterminals.  Note that "->" (dash + greater-than) is automatically
converted to an arrow symbol.  When you move your cursor to a
different line, your production will automatically be colorized.  If
there are any errors, they will be highlighted in red.

Note that the order of the productions is significant for some
algorithms.  To re-order the productions, use cut and paste to move
them.

Use the buttons at the bottom of the window when you are done editing
the CFG:
  - Ok: apply the new CFG, and exit the editor.
  - Apply: apply the new CFG, and do not exit the editor.
  - Reset: revert to the original CFG, and do not exit the editor.
  - Cancel: revert to the original CFG, and exit the editor.

"""


class CFGEditor:
    """
    A dialog window for creating and editing context free grammars.
    ``CFGEditor`` imposes the following restrictions:

    - All nonterminals must be strings consisting of word
      characters.
    - All terminals must be strings consisting of word characters
      and space characters.
    """

    # Regular expressions used by _analyze_line.  Precompile them, so
    # we can process the text faster.
    ARROW = SymbolWidget.SYMBOLS["rightarrow"]
    _LHS_RE = re.compile(r"(^\s*\w+\s*)(->|(" + ARROW + "))")
    _ARROW_RE = re.compile(r"\s*(->|(" + ARROW + r"))\s*")
    _PRODUCTION_RE = re.compile(
        r"(^\s*\w+\s*)"
        + "(->|("  # LHS
        + ARROW
        + r"))\s*"
        + r"((\w+|'[\w ]*'|\"[\w ]*\"|\|)\s*)*$"  # arrow
    )  # RHS
    _TOKEN_RE = re.compile("\\w+|->|'[\\w ]+'|\"[\\w ]+\"|(" + ARROW + ")")
    _BOLD = ("helvetica", -12, "bold")

    def __init__(self, parent, cfg=None, set_cfg_callback=None):
        self._parent = parent
        if cfg is not None:
            self._cfg = cfg
        else:
            self._cfg = CFG(Nonterminal("S"), [])
        self._set_cfg_callback = set_cfg_callback

        self._highlight_matching_nonterminals = 1

        # Create the top-level window.
        self._top = Toplevel(parent)
        self._init_bindings()

        self._init_startframe()
        self._startframe.pack(side="top", fill="x", expand=0)
        self._init_prodframe()
        self._prodframe.pack(side="top", fill="both", expand=1)
        self._init_buttons()
        self._buttonframe.pack(side="bottom", fill="x", expand=0)

        self._textwidget.focus()

    def _init_startframe(self):
        frame = self._startframe = Frame(self._top)
        self._start = Entry(frame)
        self._start.pack(side="right")
        Label(frame, text="Start Symbol:").pack(side="right")
        Label(frame, text="Productions:").pack(side="left")
        self._start.insert(0, self._cfg.start().symbol())

    def _init_buttons(self):
        frame = self._buttonframe = Frame(self._top)
        Button(frame, text="Ok", command=self._ok, underline=0, takefocus=0).pack(
            side="left"
        )
        Button(frame, text="Apply", command=self._apply, underline=0, takefocus=0).pack(
            side="left"
        )
        Button(frame, text="Reset", command=self._reset, underline=0, takefocus=0).pack(
            side="left"
        )
        Button(
            frame, text="Cancel", command=self._cancel, underline=0, takefocus=0
        ).pack(side="left")
        Button(frame, text="Help", command=self._help, underline=0, takefocus=0).pack(
            side="right"
        )

    def _init_bindings(self):
        self._top.title("CFG Editor")
        self._top.bind("<Control-q>", self._cancel)
        self._top.bind("<Alt-q>", self._cancel)
        self._top.bind("<Control-d>", self._cancel)
        # self._top.bind('<Control-x>', self._cancel)
        self._top.bind("<Alt-x>", self._cancel)
        self._top.bind("<Escape>", self._cancel)
        # self._top.bind('<Control-c>', self._cancel)
        self._top.bind("<Alt-c>", self._cancel)

        self._top.bind("<Control-o>", self._ok)
        self._top.bind("<Alt-o>", self._ok)
        self._top.bind("<Control-a>", self._apply)
        self._top.bind("<Alt-a>", self._apply)
        self._top.bind("<Control-r>", self._reset)
        self._top.bind("<Alt-r>", self._reset)
        self._top.bind("<Control-h>", self._help)
        self._top.bind("<Alt-h>", self._help)
        self._top.bind("<F1>", self._help)

    def _init_prodframe(self):
        self._prodframe = Frame(self._top)

        # Create the basic Text widget & scrollbar.
        self._textwidget = Text(
            self._prodframe, background="#e0e0e0", exportselection=1
        )
        self._textscroll = Scrollbar(self._prodframe, takefocus=0, orient="vertical")
        self._textwidget.config(yscrollcommand=self._textscroll.set)
        self._textscroll.config(command=self._textwidget.yview)
        self._textscroll.pack(side="right", fill="y")
        self._textwidget.pack(expand=1, fill="both", side="left")

        # Initialize the colorization tags.  Each nonterminal gets its
        # own tag, so they aren't listed here.
        self._textwidget.tag_config("terminal", foreground="#006000")
        self._textwidget.tag_config("arrow", font="symbol")
        self._textwidget.tag_config("error", background="red")

        # Keep track of what line they're on.  We use that to remember
        # to re-analyze a line whenever they leave it.
        self._linenum = 0

        # Expand "->" to an arrow.
        self._top.bind(">", self._replace_arrows)

        # Re-colorize lines when appropriate.
        self._top.bind("<<Paste>>", self._analyze)
        self._top.bind("<KeyPress>", self._check_analyze)
        self._top.bind("<ButtonPress>", self._check_analyze)

        # Tab cycles focus. (why doesn't this work??)
        def cycle(e, textwidget=self._textwidget):
            textwidget.tk_focusNext().focus()

        self._textwidget.bind("<Tab>", cycle)

        prod_tuples = [(p.lhs(), [p.rhs()]) for p in self._cfg.productions()]
        for i in range(len(prod_tuples) - 1, 0, -1):
            if prod_tuples[i][0] == prod_tuples[i - 1][0]:
                if () in prod_tuples[i][1]:
                    continue
                if () in prod_tuples[i - 1][1]:
                    continue
                print(prod_tuples[i - 1][1])
                print(prod_tuples[i][1])
                prod_tuples[i - 1][1].extend(prod_tuples[i][1])
                del prod_tuples[i]

        for lhs, rhss in prod_tuples:
            print(lhs, rhss)
            s = "%s ->" % lhs
            for rhs in rhss:
                for elt in rhs:
                    if isinstance(elt, Nonterminal):
                        s += " %s" % elt
                    else:
                        s += " %r" % elt
                s += " |"
            s = s[:-2] + "\n"
            self._textwidget.insert("end", s)

        self._analyze()

    #         # Add the producitons to the text widget, and colorize them.
    #         prod_by_lhs = {}
    #         for prod in self._cfg.productions():
    #             if len(prod.rhs()) > 0:
    #                 prod_by_lhs.setdefault(prod.lhs(),[]).append(prod)
    #         for (lhs, prods) in prod_by_lhs.items():
    #             self._textwidget.insert('end', '%s ->' % lhs)
    #             self._textwidget.insert('end', self._rhs(prods[0]))
    #             for prod in prods[1:]:
    #                 print '\t|'+self._rhs(prod),
    #                 self._textwidget.insert('end', '\t|'+self._rhs(prod))
    #             print
    #             self._textwidget.insert('end', '\n')
    #         for prod in self._cfg.productions():
    #             if len(prod.rhs()) == 0:
    #                 self._textwidget.insert('end', '%s' % prod)
    #         self._analyze()

    #     def _rhs(self, prod):
    #         s = ''
    #         for elt in prod.rhs():
    #             if isinstance(elt, Nonterminal): s += ' %s' % elt.symbol()
    #             else: s += ' %r' % elt
    #         return s

    def _clear_tags(self, linenum):
        """
        Remove all tags (except ``arrow`` and ``sel``) from the given
        line of the text widget used for editing the productions.
        """
        start = "%d.0" % linenum
        end = "%d.end" % linenum
        for tag in self._textwidget.tag_names():
            if tag not in ("arrow", "sel"):
                self._textwidget.tag_remove(tag, start, end)

    def _check_analyze(self, *e):
        """
        Check if we've moved to a new line.  If we have, then remove
        all colorization from the line we moved to, and re-colorize
        the line that we moved from.
        """
        linenum = int(self._textwidget.index("insert").split(".")[0])
        if linenum != self._linenum:
            self._clear_tags(linenum)
            self._analyze_line(self._linenum)
            self._linenum = linenum

    def _replace_arrows(self, *e):
        """
        Replace any ``'->'`` text strings with arrows (char \\256, in
        symbol font).  This searches the whole buffer, but is fast
        enough to be done anytime they press '>'.
        """
        arrow = "1.0"
        while True:
            arrow = self._textwidget.search("->", arrow, "end+1char")
            if arrow == "":
                break
            self._textwidget.delete(arrow, arrow + "+2char")
            self._textwidget.insert(arrow, self.ARROW, "arrow")
            self._textwidget.insert(arrow, "\t")

        arrow = "1.0"
        while True:
            arrow = self._textwidget.search(self.ARROW, arrow + "+1char", "end+1char")
            if arrow == "":
                break
            self._textwidget.tag_add("arrow", arrow, arrow + "+1char")

    def _analyze_token(self, match, linenum):
        """
        Given a line number and a regexp match for a token on that
        line, colorize the token.  Note that the regexp match gives us
        the token's text, start index (on the line), and end index (on
        the line).
        """
        # What type of token is it?
        if match.group()[0] in "'\"":
            tag = "terminal"
        elif match.group() in ("->", self.ARROW):
            tag = "arrow"
        else:
            # If it's a nonterminal, then set up new bindings, so we
            # can highlight all instances of that nonterminal when we
            # put the mouse over it.
            tag = "nonterminal_" + match.group()
            if tag not in self._textwidget.tag_names():
                self._init_nonterminal_tag(tag)

        start = "%d.%d" % (linenum, match.start())
        end = "%d.%d" % (linenum, match.end())
        self._textwidget.tag_add(tag, start, end)

    def _init_nonterminal_tag(self, tag, foreground="blue"):
        self._textwidget.tag_config(tag, foreground=foreground, font=CFGEditor._BOLD)
        if not self._highlight_matching_nonterminals:
            return

        def enter(e, textwidget=self._textwidget, tag=tag):
            textwidget.tag_config(tag, background="#80ff80")

        def leave(e, textwidget=self._textwidget, tag=tag):
            textwidget.tag_config(tag, background="")

        self._textwidget.tag_bind(tag, "<Enter>", enter)
        self._textwidget.tag_bind(tag, "<Leave>", leave)

    def _analyze_line(self, linenum):
        """
        Colorize a given line.
        """
        # Get rid of any tags that were previously on the line.
        self._clear_tags(linenum)

        # Get the line line's text string.
        line = self._textwidget.get(repr(linenum) + ".0", repr(linenum) + ".end")

        # If it's a valid production, then colorize each token.
        if CFGEditor._PRODUCTION_RE.match(line):
            # It's valid; Use _TOKEN_RE to tokenize the production,
            # and call analyze_token on each token.
            def analyze_token(match, self=self, linenum=linenum):
                self._analyze_token(match, linenum)
                return ""

            CFGEditor._TOKEN_RE.sub(analyze_token, line)
        elif line.strip() != "":
            # It's invalid; show the user where the error is.
            self._mark_error(linenum, line)

    def _mark_error(self, linenum, line):
        """
        Mark the location of an error in a line.
        """
        arrowmatch = CFGEditor._ARROW_RE.search(line)
        if not arrowmatch:
            # If there's no arrow at all, highlight the whole line.
            start = "%d.0" % linenum
            end = "%d.end" % linenum
        elif not CFGEditor._LHS_RE.match(line):
            # Otherwise, if the LHS is bad, highlight it.
            start = "%d.0" % linenum
            end = "%d.%d" % (linenum, arrowmatch.start())
        else:
            # Otherwise, highlight the RHS.
            start = "%d.%d" % (linenum, arrowmatch.end())
            end = "%d.end" % linenum

        # If we're highlighting 0 chars, highlight the whole line.
        if self._textwidget.compare(start, "==", end):
            start = "%d.0" % linenum
            end = "%d.end" % linenum
        self._textwidget.tag_add("error", start, end)

    def _analyze(self, *e):
        """
        Replace ``->`` with arrows, and colorize the entire buffer.
        """
        self._replace_arrows()
        numlines = int(self._textwidget.index("end").split(".")[0])
        for linenum in range(1, numlines + 1):  # line numbers start at 1.
            self._analyze_line(linenum)

    def _parse_productions(self):
        """
        Parse the current contents of the textwidget buffer, to create
        a list of productions.
        """
        productions = []

        # Get the text, normalize it, and split it into lines.
        text = self._textwidget.get("1.0", "end")
        text = re.sub(self.ARROW, "->", text)
        text = re.sub("\t", " ", text)
        lines = text.split("\n")

        # Convert each line to a CFG production
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            productions += _read_cfg_production(line)
            # if line.strip() == '': continue
            # if not CFGEditor._PRODUCTION_RE.match(line):
            #    raise ValueError('Bad production string %r' % line)
            #
            # (lhs_str, rhs_str) = line.split('->')
            # lhs = Nonterminal(lhs_str.strip())
            # rhs = []
            # def parse_token(match, rhs=rhs):
            #    token = match.group()
            #    if token[0] in "'\"": rhs.append(token[1:-1])
            #    else: rhs.append(Nonterminal(token))
            #    return ''
            # CFGEditor._TOKEN_RE.sub(parse_token, rhs_str)
            #
            # productions.append(Production(lhs, *rhs))

        return productions

    def _destroy(self, *e):
        if self._top is None:
            return
        self._top.destroy()
        self._top = None

    def _ok(self, *e):
        self._apply()
        self._destroy()

    def _apply(self, *e):
        productions = self._parse_productions()
        start = Nonterminal(self._start.get())
        cfg = CFG(start, productions)
        if self._set_cfg_callback is not None:
            self._set_cfg_callback(cfg)

    def _reset(self, *e):
        self._textwidget.delete("1.0", "end")
        for production in self._cfg.productions():
            self._textwidget.insert("end", "%s\n" % production)
        self._analyze()
        if self._set_cfg_callback is not None:
            self._set_cfg_callback(self._cfg)

    def _cancel(self, *e):
        try:
            self._reset()
        except:
            pass
        self._destroy()

    def _help(self, *e):
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._parent,
                "Help: Chart Parser Demo",
                (_CFGEditor_HELP).strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._parent,
                "Help: Chart Parser Demo",
                (_CFGEditor_HELP).strip(),
                width=75,
            )


######################################################################
# New Demo (built tree based on cfg)
######################################################################


class CFGDemo:
    def __init__(self, grammar, text):
        self._grammar = grammar
        self._text = text

        # Set up the main window.
        self._top = Tk()
        self._top.title("Context Free Grammar Demo")

        # Base font size
        self._size = IntVar(self._top)
        self._size.set(12)  # = medium

        # Set up the key bindings
        self._init_bindings(self._top)

        # Create the basic frames
        frame1 = Frame(self._top)
        frame1.pack(side="left", fill="y", expand=0)
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_grammar(frame1)
        self._init_treelet(frame1)
        self._init_workspace(self._top)

    # //////////////////////////////////////////////////
    # Initialization
    # //////////////////////////////////////////////////

    def _init_bindings(self, top):
        top.bind("<Control-q>", self.destroy)

    def _init_menubar(self, parent):
        pass

    def _init_buttons(self, parent):
        pass

    def _init_grammar(self, parent):
        self._prodlist = ProductionList(parent, self._grammar, width=20)
        self._prodlist.pack(side="top", fill="both", expand=1)
        self._prodlist.focus()
        self._prodlist.add_callback("select", self._selectprod_cb)
        self._prodlist.add_callback("move", self._selectprod_cb)

    def _init_treelet(self, parent):
        self._treelet_canvas = Canvas(parent, background="white")
        self._treelet_canvas.pack(side="bottom", fill="x")
        self._treelet = None

    def _init_workspace(self, parent):
        self._workspace = CanvasFrame(parent, background="white")
        self._workspace.pack(side="right", fill="both", expand=1)
        self._tree = None
        self.reset_workspace()

    # //////////////////////////////////////////////////
    # Workspace
    # //////////////////////////////////////////////////

    def reset_workspace(self):
        c = self._workspace.canvas()
        fontsize = int(self._size.get())
        node_font = ("helvetica", -(fontsize + 4), "bold")
        leaf_font = ("helvetica", -(fontsize + 2))

        # Remove the old tree
        if self._tree is not None:
            self._workspace.remove_widget(self._tree)

        # The root of the tree.
        start = self._grammar.start().symbol()
        rootnode = TextWidget(c, start, font=node_font, draggable=1)

        # The leaves of the tree.
        leaves = []
        for word in self._text:
            leaves.append(TextWidget(c, word, font=leaf_font, draggable=1))

        # Put it all together into one tree
        self._tree = TreeSegmentWidget(c, rootnode, leaves, color="white")

        # Add it to the workspace.
        self._workspace.add_widget(self._tree)

        # Move the leaves to the bottom of the workspace.
        for leaf in leaves:
            leaf.move(0, 100)

        # self._nodes = {start:1}
        # self._leaves = dict([(l,1) for l in leaves])

    def workspace_markprod(self, production):
        pass

    def _markproduction(self, prod, tree=None):
        if tree is None:
            tree = self._tree
        for i in range(len(tree.subtrees()) - len(prod.rhs())):
            if tree["color", i] == "white":
                self._markproduction  # FIXME: Is this necessary at all?

            for j, node in enumerate(prod.rhs()):
                widget = tree.subtrees()[i + j]
                if (
                    isinstance(node, Nonterminal)
                    and isinstance(widget, TreeSegmentWidget)
                    and node.symbol == widget.label().text()
                ):
                    pass  # matching nonterminal
                elif (
                    isinstance(node, str)
                    and isinstance(widget, TextWidget)
                    and node == widget.text()
                ):
                    pass  # matching nonterminal
                else:
                    break
            else:
                # Everything matched!
                print("MATCH AT", i)

    # //////////////////////////////////////////////////
    # Grammar
    # //////////////////////////////////////////////////

    def _selectprod_cb(self, production):
        canvas = self._treelet_canvas

        self._prodlist.highlight(production)
        if self._treelet is not None:
            self._treelet.destroy()

        # Convert the production to a tree.
        rhs = production.rhs()
        for i, elt in enumerate(rhs):
            if isinstance(elt, Nonterminal):
                elt = Tree(elt)
        tree = Tree(production.lhs().symbol(), *rhs)

        # Draw the tree in the treelet area.
        fontsize = int(self._size.get())
        node_font = ("helvetica", -(fontsize + 4), "bold")
        leaf_font = ("helvetica", -(fontsize + 2))
        self._treelet = tree_to_treesegment(
            canvas, tree, node_font=node_font, leaf_font=leaf_font
        )
        self._treelet["draggable"] = 1

        # Center the treelet.
        (x1, y1, x2, y2) = self._treelet.bbox()
        w, h = int(canvas["width"]), int(canvas["height"])
        self._treelet.move((w - x1 - x2) / 2, (h - y1 - y2) / 2)

        # Mark the places where we can add it to the workspace.
        self._markproduction(production)

    def destroy(self, *args):
        self._top.destroy()

    def mainloop(self, *args, **kwargs):
        self._top.mainloop(*args, **kwargs)


def demo2():
    from nltk import CFG, Nonterminal, Production

    nonterminals = "S VP NP PP P N Name V Det"
    (S, VP, NP, PP, P, N, Name, V, Det) = (Nonterminal(s) for s in nonterminals.split())
    productions = (
        # Syntactic Productions
        Production(S, [NP, VP]),
        Production(NP, [Det, N]),
        Production(NP, [NP, PP]),
        Production(VP, [VP, PP]),
        Production(VP, [V, NP, PP]),
        Production(VP, [V, NP]),
        Production(PP, [P, NP]),
        Production(PP, []),
        Production(PP, ["up", "over", NP]),
        # Lexical Productions
        Production(NP, ["I"]),
        Production(Det, ["the"]),
        Production(Det, ["a"]),
        Production(N, ["man"]),
        Production(V, ["saw"]),
        Production(P, ["in"]),
        Production(P, ["with"]),
        Production(N, ["park"]),
        Production(N, ["dog"]),
        Production(N, ["statue"]),
        Production(Det, ["my"]),
    )
    grammar = CFG(S, productions)

    text = "I saw a man in the park".split()
    d = CFGDemo(grammar, text)
    d.mainloop()


######################################################################
# Old Demo
######################################################################


def demo():
    from nltk import CFG, Nonterminal

    nonterminals = "S VP NP PP P N Name V Det"
    (S, VP, NP, PP, P, N, Name, V, Det) = (Nonterminal(s) for s in nonterminals.split())

    grammar = CFG.fromstring(
        """
    S -> NP VP
    PP -> P NP
    NP -> Det N
    NP -> NP PP
    VP -> V NP
    VP -> VP PP
    Det -> 'a'
    Det -> 'the'
    Det -> 'my'
    NP -> 'I'
    N -> 'dog'
    N -> 'man'
    N -> 'park'
    N -> 'statue'
    V -> 'saw'
    P -> 'in'
    P -> 'up'
    P -> 'over'
    P -> 'with'
    """
    )

    def cb(grammar):
        print(grammar)

    top = Tk()
    editor = CFGEditor(top, grammar, cb)
    Label(top, text="\nTesting CFG Editor\n").pack()
    Button(top, text="Quit", command=top.destroy).pack()
    top.mainloop()


def demo3():
    from nltk import Production

    (S, VP, NP, PP, P, N, Name, V, Det) = nonterminals(
        "S, VP, NP, PP, P, N, Name, V, Det"
    )

    productions = (
        # Syntactic Productions
        Production(S, [NP, VP]),
        Production(NP, [Det, N]),
        Production(NP, [NP, PP]),
        Production(VP, [VP, PP]),
        Production(VP, [V, NP, PP]),
        Production(VP, [V, NP]),
        Production(PP, [P, NP]),
        Production(PP, []),
        Production(PP, ["up", "over", NP]),
        # Lexical Productions
        Production(NP, ["I"]),
        Production(Det, ["the"]),
        Production(Det, ["a"]),
        Production(N, ["man"]),
        Production(V, ["saw"]),
        Production(P, ["in"]),
        Production(P, ["with"]),
        Production(N, ["park"]),
        Production(N, ["dog"]),
        Production(N, ["statue"]),
        Production(Det, ["my"]),
    )

    t = Tk()

    def destroy(e, t=t):
        t.destroy()

    t.bind("q", destroy)
    p = ProductionList(t, productions)
    p.pack(expand=1, fill="both")
    p.add_callback("select", p.markonly)
    p.add_callback("move", p.markonly)
    p.focus()
    p.mark(productions[2])
    p.mark(productions[8])


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\rsa\key.py ===
#  Copyright 2011 Sybren A. Stüvel <sybren@stuvel.eu>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""RSA key generation code.

Create new keys with the newkeys() function. It will give you a PublicKey and a
PrivateKey object.

Loading and saving keys requires the pyasn1 module. This module is imported as
late as possible, such that other functionality will remain working in absence
of pyasn1.

.. note::

    Storing public and private keys via the `pickle` module is possible.
    However, it is insecure to load a key from an untrusted source.
    The pickle module is not secure against erroneous or maliciously
    constructed data. Never unpickle data received from an untrusted
    or unauthenticated source.

"""

import threading
import typing
import warnings

import rsa.prime
import rsa.pem
import rsa.common
import rsa.randnum
import rsa.core


DEFAULT_EXPONENT = 65537


T = typing.TypeVar("T", bound="AbstractKey")


class AbstractKey:
    """Abstract superclass for private and public keys."""

    __slots__ = ("n", "e", "blindfac", "blindfac_inverse", "mutex")

    def __init__(self, n: int, e: int) -> None:
        self.n = n
        self.e = e

        # These will be computed properly on the first call to blind().
        self.blindfac = self.blindfac_inverse = -1

        # Used to protect updates to the blinding factor in multi-threaded
        # environments.
        self.mutex = threading.Lock()

    @classmethod
    def _load_pkcs1_pem(cls: typing.Type[T], keyfile: bytes) -> T:
        """Loads a key in PKCS#1 PEM format, implement in a subclass.

        :param keyfile: contents of a PEM-encoded file that contains
            the public key.
        :type keyfile: bytes

        :return: the loaded key
        :rtype: AbstractKey
        """

    @classmethod
    def _load_pkcs1_der(cls: typing.Type[T], keyfile: bytes) -> T:
        """Loads a key in PKCS#1 PEM format, implement in a subclass.

        :param keyfile: contents of a DER-encoded file that contains
            the public key.
        :type keyfile: bytes

        :return: the loaded key
        :rtype: AbstractKey
        """

    def _save_pkcs1_pem(self) -> bytes:
        """Saves the key in PKCS#1 PEM format, implement in a subclass.

        :returns: the PEM-encoded key.
        :rtype: bytes
        """

    def _save_pkcs1_der(self) -> bytes:
        """Saves the key in PKCS#1 DER format, implement in a subclass.

        :returns: the DER-encoded key.
        :rtype: bytes
        """

    @classmethod
    def load_pkcs1(cls: typing.Type[T], keyfile: bytes, format: str = "PEM") -> T:
        """Loads a key in PKCS#1 DER or PEM format.

        :param keyfile: contents of a DER- or PEM-encoded file that contains
            the key.
        :type keyfile: bytes
        :param format: the format of the file to load; 'PEM' or 'DER'
        :type format: str

        :return: the loaded key
        :rtype: AbstractKey
        """

        methods = {
            "PEM": cls._load_pkcs1_pem,
            "DER": cls._load_pkcs1_der,
        }

        method = cls._assert_format_exists(format, methods)
        return method(keyfile)

    @staticmethod
    def _assert_format_exists(
        file_format: str, methods: typing.Mapping[str, typing.Callable]
    ) -> typing.Callable:
        """Checks whether the given file format exists in 'methods'."""

        try:
            return methods[file_format]
        except KeyError as ex:
            formats = ", ".join(sorted(methods.keys()))
            raise ValueError(
                "Unsupported format: %r, try one of %s" % (file_format, formats)
            ) from ex

    def save_pkcs1(self, format: str = "PEM") -> bytes:
        """Saves the key in PKCS#1 DER or PEM format.

        :param format: the format to save; 'PEM' or 'DER'
        :type format: str
        :returns: the DER- or PEM-encoded key.
        :rtype: bytes
        """

        methods = {
            "PEM": self._save_pkcs1_pem,
            "DER": self._save_pkcs1_der,
        }

        method = self._assert_format_exists(format, methods)
        return method()

    def blind(self, message: int) -> typing.Tuple[int, int]:
        """Performs blinding on the message.

        :param message: the message, as integer, to blind.
        :param r: the random number to blind with.
        :return: tuple (the blinded message, the inverse of the used blinding factor)

        The blinding is such that message = unblind(decrypt(blind(encrypt(message))).

        See https://en.wikipedia.org/wiki/Blinding_%28cryptography%29
        """
        blindfac, blindfac_inverse = self._update_blinding_factor()
        blinded = (message * pow(blindfac, self.e, self.n)) % self.n
        return blinded, blindfac_inverse

    def unblind(self, blinded: int, blindfac_inverse: int) -> int:
        """Performs blinding on the message using random number 'blindfac_inverse'.

        :param blinded: the blinded message, as integer, to unblind.
        :param blindfac: the factor to unblind with.
        :return: the original message.

        The blinding is such that message = unblind(decrypt(blind(encrypt(message))).

        See https://en.wikipedia.org/wiki/Blinding_%28cryptography%29
        """
        return (blindfac_inverse * blinded) % self.n

    def _initial_blinding_factor(self) -> int:
        for _ in range(1000):
            blind_r = rsa.randnum.randint(self.n - 1)
            if rsa.prime.are_relatively_prime(self.n, blind_r):
                return blind_r
        raise RuntimeError("unable to find blinding factor")

    def _update_blinding_factor(self) -> typing.Tuple[int, int]:
        """Update blinding factors.

        Computing a blinding factor is expensive, so instead this function
        does this once, then updates the blinding factor as per section 9
        of 'A Timing Attack against RSA with the Chinese Remainder Theorem'
        by Werner Schindler.
        See https://tls.mbed.org/public/WSchindler-RSA_Timing_Attack.pdf

        :return: the new blinding factor and its inverse.
        """

        with self.mutex:
            if self.blindfac < 0:
                # Compute initial blinding factor, which is rather slow to do.
                self.blindfac = self._initial_blinding_factor()
                self.blindfac_inverse = rsa.common.inverse(self.blindfac, self.n)
            else:
                # Reuse previous blinding factor.
                self.blindfac = pow(self.blindfac, 2, self.n)
                self.blindfac_inverse = pow(self.blindfac_inverse, 2, self.n)

            return self.blindfac, self.blindfac_inverse


class PublicKey(AbstractKey):
    """Represents a public RSA key.

    This key is also known as the 'encryption key'. It contains the 'n' and 'e'
    values.

    Supports attributes as well as dictionary-like access. Attribute access is
    faster, though.

    >>> PublicKey(5, 3)
    PublicKey(5, 3)

    >>> key = PublicKey(5, 3)
    >>> key.n
    5
    >>> key['n']
    5
    >>> key.e
    3
    >>> key['e']
    3

    """

    __slots__ = ()

    def __getitem__(self, key: str) -> int:
        return getattr(self, key)

    def __repr__(self) -> str:
        return "PublicKey(%i, %i)" % (self.n, self.e)

    def __getstate__(self) -> typing.Tuple[int, int]:
        """Returns the key as tuple for pickling."""
        return self.n, self.e

    def __setstate__(self, state: typing.Tuple[int, int]) -> None:
        """Sets the key from tuple."""
        self.n, self.e = state
        AbstractKey.__init__(self, self.n, self.e)

    def __eq__(self, other: typing.Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, PublicKey):
            return False

        return self.n == other.n and self.e == other.e

    def __ne__(self, other: typing.Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self.n, self.e))

    @classmethod
    def _load_pkcs1_der(cls, keyfile: bytes) -> "PublicKey":
        """Loads a key in PKCS#1 DER format.

        :param keyfile: contents of a DER-encoded file that contains the public
            key.
        :return: a PublicKey object

        First let's construct a DER encoded key:

        >>> import base64
        >>> b64der = 'MAwCBQCNGmYtAgMBAAE='
        >>> der = base64.standard_b64decode(b64der)

        This loads the file:

        >>> PublicKey._load_pkcs1_der(der)
        PublicKey(2367317549, 65537)

        """

        from pyasn1.codec.der import decoder
        from rsa.asn1 import AsnPubKey

        (priv, _) = decoder.decode(keyfile, asn1Spec=AsnPubKey())
        return cls(n=int(priv["modulus"]), e=int(priv["publicExponent"]))

    def _save_pkcs1_der(self) -> bytes:
        """Saves the public key in PKCS#1 DER format.

        :returns: the DER-encoded public key.
        :rtype: bytes
        """

        from pyasn1.codec.der import encoder
        from rsa.asn1 import AsnPubKey

        # Create the ASN object
        asn_key = AsnPubKey()
        asn_key.setComponentByName("modulus", self.n)
        asn_key.setComponentByName("publicExponent", self.e)

        return encoder.encode(asn_key)

    @classmethod
    def _load_pkcs1_pem(cls, keyfile: bytes) -> "PublicKey":
        """Loads a PKCS#1 PEM-encoded public key file.

        The contents of the file before the "-----BEGIN RSA PUBLIC KEY-----" and
        after the "-----END RSA PUBLIC KEY-----" lines is ignored.

        :param keyfile: contents of a PEM-encoded file that contains the public
            key.
        :return: a PublicKey object
        """

        der = rsa.pem.load_pem(keyfile, "RSA PUBLIC KEY")
        return cls._load_pkcs1_der(der)

    def _save_pkcs1_pem(self) -> bytes:
        """Saves a PKCS#1 PEM-encoded public key file.

        :return: contents of a PEM-encoded file that contains the public key.
        :rtype: bytes
        """

        der = self._save_pkcs1_der()
        return rsa.pem.save_pem(der, "RSA PUBLIC KEY")

    @classmethod
    def load_pkcs1_openssl_pem(cls, keyfile: bytes) -> "PublicKey":
        """Loads a PKCS#1.5 PEM-encoded public key file from OpenSSL.

        These files can be recognised in that they start with BEGIN PUBLIC KEY
        rather than BEGIN RSA PUBLIC KEY.

        The contents of the file before the "-----BEGIN PUBLIC KEY-----" and
        after the "-----END PUBLIC KEY-----" lines is ignored.

        :param keyfile: contents of a PEM-encoded file that contains the public
            key, from OpenSSL.
        :type keyfile: bytes
        :return: a PublicKey object
        """

        der = rsa.pem.load_pem(keyfile, "PUBLIC KEY")
        return cls.load_pkcs1_openssl_der(der)

    @classmethod
    def load_pkcs1_openssl_der(cls, keyfile: bytes) -> "PublicKey":
        """Loads a PKCS#1 DER-encoded public key file from OpenSSL.

        :param keyfile: contents of a DER-encoded file that contains the public
            key, from OpenSSL.
        :return: a PublicKey object
        """

        from rsa.asn1 import OpenSSLPubKey
        from pyasn1.codec.der import decoder
        from pyasn1.type import univ

        (keyinfo, _) = decoder.decode(keyfile, asn1Spec=OpenSSLPubKey())

        if keyinfo["header"]["oid"] != univ.ObjectIdentifier("1.2.840.113549.1.1.1"):
            raise TypeError("This is not a DER-encoded OpenSSL-compatible public key")

        return cls._load_pkcs1_der(keyinfo["key"][1:])


class PrivateKey(AbstractKey):
    """Represents a private RSA key.

    This key is also known as the 'decryption key'. It contains the 'n', 'e',
    'd', 'p', 'q' and other values.

    Supports attributes as well as dictionary-like access. Attribute access is
    faster, though.

    >>> PrivateKey(3247, 65537, 833, 191, 17)
    PrivateKey(3247, 65537, 833, 191, 17)

    exp1, exp2 and coef will be calculated:

    >>> pk = PrivateKey(3727264081, 65537, 3349121513, 65063, 57287)
    >>> pk.exp1
    55063
    >>> pk.exp2
    10095
    >>> pk.coef
    50797

    """

    __slots__ = ("d", "p", "q", "exp1", "exp2", "coef")

    def __init__(self, n: int, e: int, d: int, p: int, q: int) -> None:
        AbstractKey.__init__(self, n, e)
        self.d = d
        self.p = p
        self.q = q

        # Calculate exponents and coefficient.
        self.exp1 = int(d % (p - 1))
        self.exp2 = int(d % (q - 1))
        self.coef = rsa.common.inverse(q, p)

    def __getitem__(self, key: str) -> int:
        return getattr(self, key)

    def __repr__(self) -> str:
        return "PrivateKey(%i, %i, %i, %i, %i)" % (
            self.n,
            self.e,
            self.d,
            self.p,
            self.q,
        )

    def __getstate__(self) -> typing.Tuple[int, int, int, int, int, int, int, int]:
        """Returns the key as tuple for pickling."""
        return self.n, self.e, self.d, self.p, self.q, self.exp1, self.exp2, self.coef

    def __setstate__(self, state: typing.Tuple[int, int, int, int, int, int, int, int]) -> None:
        """Sets the key from tuple."""
        self.n, self.e, self.d, self.p, self.q, self.exp1, self.exp2, self.coef = state
        AbstractKey.__init__(self, self.n, self.e)

    def __eq__(self, other: typing.Any) -> bool:
        if other is None:
            return False

        if not isinstance(other, PrivateKey):
            return False

        return (
            self.n == other.n
            and self.e == other.e
            and self.d == other.d
            and self.p == other.p
            and self.q == other.q
            and self.exp1 == other.exp1
            and self.exp2 == other.exp2
            and self.coef == other.coef
        )

    def __ne__(self, other: typing.Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((self.n, self.e, self.d, self.p, self.q, self.exp1, self.exp2, self.coef))

    def blinded_decrypt(self, encrypted: int) -> int:
        """Decrypts the message using blinding to prevent side-channel attacks.

        :param encrypted: the encrypted message
        :type encrypted: int

        :returns: the decrypted message
        :rtype: int
        """

        # Blinding and un-blinding should be using the same factor
        blinded, blindfac_inverse = self.blind(encrypted)

        # Instead of using the core functionality, use the Chinese Remainder
        # Theorem and be 2-4x faster. This the same as:
        #
        # decrypted = rsa.core.decrypt_int(blinded, self.d, self.n)
        s1 = pow(blinded, self.exp1, self.p)
        s2 = pow(blinded, self.exp2, self.q)
        h = ((s1 - s2) * self.coef) % self.p
        decrypted = s2 + self.q * h

        return self.unblind(decrypted, blindfac_inverse)

    def blinded_encrypt(self, message: int) -> int:
        """Encrypts the message using blinding to prevent side-channel attacks.

        :param message: the message to encrypt
        :type message: int

        :returns: the encrypted message
        :rtype: int
        """

        blinded, blindfac_inverse = self.blind(message)
        encrypted = rsa.core.encrypt_int(blinded, self.d, self.n)
        return self.unblind(encrypted, blindfac_inverse)

    @classmethod
    def _load_pkcs1_der(cls, keyfile: bytes) -> "PrivateKey":
        """Loads a key in PKCS#1 DER format.

        :param keyfile: contents of a DER-encoded file that contains the private
            key.
        :type keyfile: bytes
        :return: a PrivateKey object

        First let's construct a DER encoded key:

        >>> import base64
        >>> b64der = 'MC4CAQACBQDeKYlRAgMBAAECBQDHn4npAgMA/icCAwDfxwIDANcXAgInbwIDAMZt'
        >>> der = base64.standard_b64decode(b64der)

        This loads the file:

        >>> PrivateKey._load_pkcs1_der(der)
        PrivateKey(3727264081, 65537, 3349121513, 65063, 57287)

        """

        from pyasn1.codec.der import decoder

        (priv, _) = decoder.decode(keyfile)

        # ASN.1 contents of DER encoded private key:
        #
        # RSAPrivateKey ::= SEQUENCE {
        #     version           Version,
        #     modulus           INTEGER,  -- n
        #     publicExponent    INTEGER,  -- e
        #     privateExponent   INTEGER,  -- d
        #     prime1            INTEGER,  -- p
        #     prime2            INTEGER,  -- q
        #     exponent1         INTEGER,  -- d mod (p-1)
        #     exponent2         INTEGER,  -- d mod (q-1)
        #     coefficient       INTEGER,  -- (inverse of q) mod p
        #     otherPrimeInfos   OtherPrimeInfos OPTIONAL
        # }

        if priv[0] != 0:
            raise ValueError("Unable to read this file, version %s != 0" % priv[0])

        as_ints = map(int, priv[1:6])
        key = cls(*as_ints)

        exp1, exp2, coef = map(int, priv[6:9])

        if (key.exp1, key.exp2, key.coef) != (exp1, exp2, coef):
            warnings.warn(
                "You have provided a malformed keyfile. Either the exponents "
                "or the coefficient are incorrect. Using the correct values "
                "instead.",
                UserWarning,
            )

        return key

    def _save_pkcs1_der(self) -> bytes:
        """Saves the private key in PKCS#1 DER format.

        :returns: the DER-encoded private key.
        :rtype: bytes
        """

        from pyasn1.type import univ, namedtype
        from pyasn1.codec.der import encoder

        class AsnPrivKey(univ.Sequence):
            componentType = namedtype.NamedTypes(
                namedtype.NamedType("version", univ.Integer()),
                namedtype.NamedType("modulus", univ.Integer()),
                namedtype.NamedType("publicExponent", univ.Integer()),
                namedtype.NamedType("privateExponent", univ.Integer()),
                namedtype.NamedType("prime1", univ.Integer()),
                namedtype.NamedType("prime2", univ.Integer()),
                namedtype.NamedType("exponent1", univ.Integer()),
                namedtype.NamedType("exponent2", univ.Integer()),
                namedtype.NamedType("coefficient", univ.Integer()),
            )

        # Create the ASN object
        asn_key = AsnPrivKey()
        asn_key.setComponentByName("version", 0)
        asn_key.setComponentByName("modulus", self.n)
        asn_key.setComponentByName("publicExponent", self.e)
        asn_key.setComponentByName("privateExponent", self.d)
        asn_key.setComponentByName("prime1", self.p)
        asn_key.setComponentByName("prime2", self.q)
        asn_key.setComponentByName("exponent1", self.exp1)
        asn_key.setComponentByName("exponent2", self.exp2)
        asn_key.setComponentByName("coefficient", self.coef)

        return encoder.encode(asn_key)

    @classmethod
    def _load_pkcs1_pem(cls, keyfile: bytes) -> "PrivateKey":
        """Loads a PKCS#1 PEM-encoded private key file.

        The contents of the file before the "-----BEGIN RSA PRIVATE KEY-----" and
        after the "-----END RSA PRIVATE KEY-----" lines is ignored.

        :param keyfile: contents of a PEM-encoded file that contains the private
            key.
        :type keyfile: bytes
        :return: a PrivateKey object
        """

        der = rsa.pem.load_pem(keyfile, b"RSA PRIVATE KEY")
        return cls._load_pkcs1_der(der)

    def _save_pkcs1_pem(self) -> bytes:
        """Saves a PKCS#1 PEM-encoded private key file.

        :return: contents of a PEM-encoded file that contains the private key.
        :rtype: bytes
        """

        der = self._save_pkcs1_der()
        return rsa.pem.save_pem(der, b"RSA PRIVATE KEY")


def find_p_q(
    nbits: int,
    getprime_func: typing.Callable[[int], int] = rsa.prime.getprime,
    accurate: bool = True,
) -> typing.Tuple[int, int]:
    """Returns a tuple of two different primes of nbits bits each.

    The resulting p * q has exactly 2 * nbits bits, and the returned p and q
    will not be equal.

    :param nbits: the number of bits in each of p and q.
    :param getprime_func: the getprime function, defaults to
        :py:func:`rsa.prime.getprime`.

        *Introduced in Python-RSA 3.1*

    :param accurate: whether to enable accurate mode or not.
    :returns: (p, q), where p > q

    >>> (p, q) = find_p_q(128)
    >>> from rsa import common
    >>> common.bit_size(p * q)
    256

    When not in accurate mode, the number of bits can be slightly less

    >>> (p, q) = find_p_q(128, accurate=False)
    >>> from rsa import common
    >>> common.bit_size(p * q) <= 256
    True
    >>> common.bit_size(p * q) > 240
    True

    """

    total_bits = nbits * 2

    # Make sure that p and q aren't too close or the factoring programs can
    # factor n.
    shift = nbits // 16
    pbits = nbits + shift
    qbits = nbits - shift

    # Choose the two initial primes
    p = getprime_func(pbits)
    q = getprime_func(qbits)

    def is_acceptable(p: int, q: int) -> bool:
        """Returns True iff p and q are acceptable:

        - p and q differ
        - (p * q) has the right nr of bits (when accurate=True)
        """

        if p == q:
            return False

        if not accurate:
            return True

        # Make sure we have just the right amount of bits
        found_size = rsa.common.bit_size(p * q)
        return total_bits == found_size

    # Keep choosing other primes until they match our requirements.
    change_p = False
    while not is_acceptable(p, q):
        # Change p on one iteration and q on the other
        if change_p:
            p = getprime_func(pbits)
        else:
            q = getprime_func(qbits)

        change_p = not change_p

    # We want p > q as described on
    # http://www.di-mgt.com.au/rsa_alg.html#crt
    return max(p, q), min(p, q)


def calculate_keys_custom_exponent(p: int, q: int, exponent: int) -> typing.Tuple[int, int]:
    """Calculates an encryption and a decryption key given p, q and an exponent,
    and returns them as a tuple (e, d)

    :param p: the first large prime
    :param q: the second large prime
    :param exponent: the exponent for the key; only change this if you know
        what you're doing, as the exponent influences how difficult your
        private key can be cracked. A very common choice for e is 65537.
    :type exponent: int

    """

    phi_n = (p - 1) * (q - 1)

    try:
        d = rsa.common.inverse(exponent, phi_n)
    except rsa.common.NotRelativePrimeError as ex:
        raise rsa.common.NotRelativePrimeError(
            exponent,
            phi_n,
            ex.d,
            msg="e (%d) and phi_n (%d) are not relatively prime (divider=%i)"
            % (exponent, phi_n, ex.d),
        ) from ex

    if (exponent * d) % phi_n != 1:
        raise ValueError(
            "e (%d) and d (%d) are not mult. inv. modulo " "phi_n (%d)" % (exponent, d, phi_n)
        )

    return exponent, d


def calculate_keys(p: int, q: int) -> typing.Tuple[int, int]:
    """Calculates an encryption and a decryption key given p and q, and
    returns them as a tuple (e, d)

    :param p: the first large prime
    :param q: the second large prime

    :return: tuple (e, d) with the encryption and decryption exponents.
    """

    return calculate_keys_custom_exponent(p, q, DEFAULT_EXPONENT)


def gen_keys(
    nbits: int,
    getprime_func: typing.Callable[[int], int],
    accurate: bool = True,
    exponent: int = DEFAULT_EXPONENT,
) -> typing.Tuple[int, int, int, int]:
    """Generate RSA keys of nbits bits. Returns (p, q, e, d).

    Note: this can take a long time, depending on the key size.

    :param nbits: the total number of bits in ``p`` and ``q``. Both ``p`` and
        ``q`` will use ``nbits/2`` bits.
    :param getprime_func: either :py:func:`rsa.prime.getprime` or a function
        with similar signature.
    :param exponent: the exponent for the key; only change this if you know
        what you're doing, as the exponent influences how difficult your
        private key can be cracked. A very common choice for e is 65537.
    :type exponent: int
    """

    # Regenerate p and q values, until calculate_keys doesn't raise a
    # ValueError.
    while True:
        (p, q) = find_p_q(nbits // 2, getprime_func, accurate)
        try:
            (e, d) = calculate_keys_custom_exponent(p, q, exponent=exponent)
            break
        except ValueError:
            pass

    return p, q, e, d


def newkeys(
    nbits: int,
    accurate: bool = True,
    poolsize: int = 1,
    exponent: int = DEFAULT_EXPONENT,
) -> typing.Tuple[PublicKey, PrivateKey]:
    """Generates public and private keys, and returns them as (pub, priv).

    The public key is also known as the 'encryption key', and is a
    :py:class:`rsa.PublicKey` object. The private key is also known as the
    'decryption key' and is a :py:class:`rsa.PrivateKey` object.

    :param nbits: the number of bits required to store ``n = p*q``.
    :param accurate: when True, ``n`` will have exactly the number of bits you
        asked for. However, this makes key generation much slower. When False,
        `n`` may have slightly less bits.
    :param poolsize: the number of processes to use to generate the prime
        numbers. If set to a number > 1, a parallel algorithm will be used.
        This requires Python 2.6 or newer.
    :param exponent: the exponent for the key; only change this if you know
        what you're doing, as the exponent influences how difficult your
        private key can be cracked. A very common choice for e is 65537.
    :type exponent: int

    :returns: a tuple (:py:class:`rsa.PublicKey`, :py:class:`rsa.PrivateKey`)

    The ``poolsize`` parameter was added in *Python-RSA 3.1* and requires
    Python 2.6 or newer.

    """

    if nbits < 16:
        raise ValueError("Key too small")

    if poolsize < 1:
        raise ValueError("Pool size (%i) should be >= 1" % poolsize)

    # Determine which getprime function to use
    if poolsize > 1:
        from rsa import parallel

        def getprime_func(nbits: int) -> int:
            return parallel.getprime(nbits, poolsize=poolsize)

    else:
        getprime_func = rsa.prime.getprime

    # Generate the key components
    (p, q, e, d) = gen_keys(nbits, getprime_func, accurate=accurate, exponent=exponent)

    # Create the key objects
    n = p * q

    return (PublicKey(n, e), PrivateKey(n, e, d, p, q))


__all__ = ["PublicKey", "PrivateKey", "newkeys"]

if __name__ == "__main__":
    import doctest

    try:
        for count in range(100):
            (failures, tests) = doctest.testmod()
            if failures:
                break

            if (count % 10 == 0 and count) or count == 1:
                print("%i times" % count)
    except KeyboardInterrupt:
        print("Aborted")
    else:
        print("Doctests done")