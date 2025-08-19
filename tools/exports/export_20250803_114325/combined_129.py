
# === NexusCore/openenv\Lib\site-packages\requests\sessions.py ===
"""
requests.sessions
~~~~~~~~~~~~~~~~~

This module provides a Session object to manage and persist settings across
requests (cookies, auth, proxies).
"""
import os
import sys
import time
from collections import OrderedDict
from datetime import timedelta

from ._internal_utils import to_native_string
from .adapters import HTTPAdapter
from .auth import _basic_auth_str
from .compat import Mapping, cookielib, urljoin, urlparse
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    extract_cookies_to_jar,
    merge_cookies,
)
from .exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    InvalidSchema,
    TooManyRedirects,
)
from .hooks import default_hooks, dispatch_hook

# formerly defined here, reexposed here for backward compatibility
from .models import (  # noqa: F401
    DEFAULT_REDIRECT_LIMIT,
    REDIRECT_STATI,
    PreparedRequest,
    Request,
)
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (  # noqa: F401
    DEFAULT_PORTS,
    default_headers,
    get_auth_from_url,
    get_environ_proxies,
    get_netrc_auth,
    requote_uri,
    resolve_proxies,
    rewind_body,
    should_bypass_proxies,
    to_key_val_list,
)

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time


def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
    """Determines appropriate setting for a given request, taking into account
    the explicit setting on that request, and the setting in the session. If a
    setting is a dictionary, they will be merged together using `dict_class`
    """

    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting

    # Bypass if not a dictionary (e.g. verify)
    if not (
        isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)
    ):
        return request_setting

    merged_setting = dict_class(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]

    return merged_setting


def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks

    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks

    return merge_setting(request_hooks, session_hooks, dict_class)


class SessionRedirectMixin:
    def get_redirect_target(self, resp):
        """Receives a Response. Returns a redirect URI or ``None``"""
        # Due to the nature of how requests processes redirects this method will
        # be called at least once upon the original response and at least twice
        # on each subsequent redirect response (if any).
        # If a custom mixin is used to handle this logic, it may be advantageous
        # to cache the redirect location onto the response object as a private
        # attribute.
        if resp.is_redirect:
            location = resp.headers["location"]
            # Currently the underlying http module on py3 decode headers
            # in latin1, but empirical evidence suggests that latin1 is very
            # rarely used with non-ASCII characters in HTTP headers.
            # It is more likely to get UTF8 header rather than latin1.
            # This causes incorrect handling of UTF8 encoded location headers.
            # To solve this, we re-encode the location in latin1.
            location = location.encode("latin1")
            return to_native_string(location, "utf8")
        return None

    def should_strip_auth(self, old_url, new_url):
        """Decide whether Authorization header should be removed when redirecting"""
        old_parsed = urlparse(old_url)
        new_parsed = urlparse(new_url)
        if old_parsed.hostname != new_parsed.hostname:
            return True
        # Special case: allow http -> https redirect when using the standard
        # ports. This isn't specified by RFC 7235, but is kept to avoid
        # breaking backwards compatibility with older versions of requests
        # that allowed any redirects on the same host.
        if (
            old_parsed.scheme == "http"
            and old_parsed.port in (80, None)
            and new_parsed.scheme == "https"
            and new_parsed.port in (443, None)
        ):
            return False

        # Handle default port usage corresponding to scheme.
        changed_port = old_parsed.port != new_parsed.port
        changed_scheme = old_parsed.scheme != new_parsed.scheme
        default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
        if (
            not changed_scheme
            and old_parsed.port in default_port
            and new_parsed.port in default_port
        ):
            return False

        # Standard case: root URI must match
        return changed_port or changed_scheme

    def resolve_redirects(
        self,
        resp,
        req,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
        yield_requests=False,
        **adapter_kwargs,
    ):
        """Receives a Response. Returns a generator of Responses or Requests."""

        hist = []  # keep track of history

        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()

            # Update history and keep track of redirects.
            # resp.history must ignore the original request in this loop
            hist.append(resp)
            resp.history = hist[1:]

            try:
                resp.content  # Consume socket so it can be released
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                resp.raw.read(decode_content=False)

            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(
                    f"Exceeded {self.max_redirects} redirects.", response=resp
                )

            # Release the connection back into the pool.
            resp.close()

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith("//"):
                parsed_rurl = urlparse(resp.url)
                url = ":".join([to_native_string(parsed_rurl.scheme), url])

            # Normalize url case and attach previous fragment if needed (RFC 7231 7.1.2)
            parsed = urlparse(url)
            if parsed.fragment == "" and previous_fragment:
                parsed = parsed._replace(fragment=previous_fragment)
            elif parsed.fragment:
                previous_fragment = parsed.fragment
            url = parsed.geturl()

            # Facilitate relative 'location' headers, as allowed by RFC 7231.
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            # Compliant with RFC3986, we percent encode the url.
            if not parsed.netloc:
                url = urljoin(resp.url, requote_uri(url))
            else:
                url = requote_uri(url)

            prepared_request.url = to_native_string(url)

            self.rebuild_method(prepared_request, resp)

            # https://github.com/psf/requests/issues/1084
            if resp.status_code not in (
                codes.temporary_redirect,
                codes.permanent_redirect,
            ):
                # https://github.com/psf/requests/issues/3490
                purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
                for header in purged_headers:
                    prepared_request.headers.pop(header, None)
                prepared_request.body = None

            headers = prepared_request.headers
            headers.pop("Cookie", None)

            # Extract any cookies sent on the response to the cookiejar
            # in the new request. Because we've mutated our copied prepared
            # request, use the old one that we haven't yet touched.
            extract_cookies_to_jar(prepared_request._cookies, req, resp.raw)
            merge_cookies(prepared_request._cookies, self.cookies)
            prepared_request.prepare_cookies(prepared_request._cookies)

            # Rebuild auth and proxy information.
            proxies = self.rebuild_proxies(prepared_request, proxies)
            self.rebuild_auth(prepared_request, resp)

            # A failed tell() sets `_body_position` to `object()`. This non-None
            # value ensures `rewindable` will be True, allowing us to raise an
            # UnrewindableBodyError, instead of hanging the connection.
            rewindable = prepared_request._body_position is not None and (
                "Content-Length" in headers or "Transfer-Encoding" in headers
            )

            # Attempt to rewind consumed file-like object.
            if rewindable:
                rewind_body(prepared_request)

            # Override the original request.
            req = prepared_request

            if yield_requests:
                yield req
            else:
                resp = self.send(
                    req,
                    stream=stream,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies,
                    allow_redirects=False,
                    **adapter_kwargs,
                )

                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

                # extract redirect url, if any, for the next loop
                url = self.get_redirect_target(resp)
                yield resp

    def rebuild_auth(self, prepared_request, response):
        """When being redirected we may want to strip authentication from the
        request to avoid leaking credentials. This method intelligently removes
        and reapplies authentication where possible to avoid credential loss.
        """
        headers = prepared_request.headers
        url = prepared_request.url

        if "Authorization" in headers and self.should_strip_auth(
            response.request.url, url
        ):
            # If we get redirected to a new host, we should strip out any
            # authentication headers.
            del headers["Authorization"]

        # .netrc might have more auth for us on our new host.
        new_auth = get_netrc_auth(url) if self.trust_env else None
        if new_auth is not None:
            prepared_request.prepare_auth(new_auth)

    def rebuild_proxies(self, prepared_request, proxies):
        """This method re-evaluates the proxy configuration by considering the
        environment variables. If we are redirected to a URL covered by
        NO_PROXY, we strip the proxy configuration. Otherwise, we set missing
        proxy keys for this URL (in case they were stripped by a previous
        redirect).

        This method also replaces the Proxy-Authorization header where
        necessary.

        :rtype: dict
        """
        headers = prepared_request.headers
        scheme = urlparse(prepared_request.url).scheme
        new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)

        if "Proxy-Authorization" in headers:
            del headers["Proxy-Authorization"]

        try:
            username, password = get_auth_from_url(new_proxies[scheme])
        except KeyError:
            username, password = None, None

        # urllib3 handles proxy authorization for us in the standard adapter.
        # Avoid appending this to TLS tunneled requests where it may be leaked.
        if not scheme.startswith("https") and username and password:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return new_proxies

    def rebuild_method(self, prepared_request, response):
        """When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = prepared_request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.see_other and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # First, turn 302s into GETs.
        if response.status_code == codes.found and method != "HEAD":
            method = "GET"

        # Second, if a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in Issue 1704.
        if response.status_code == codes.moved and method == "POST":
            method = "GET"

        prepared_request.method = method


class Session(SessionRedirectMixin):
    """A Requests session.

    Provides cookie persistence, connection-pooling, and configuration.

    Basic Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> s.get('https://httpbin.org/get')
      <Response [200]>

    Or as a context manager::

      >>> with requests.Session() as s:
      ...     s.get('https://httpbin.org/get')
      <Response [200]>
    """

    __attrs__ = [
        "headers",
        "cookies",
        "auth",
        "proxies",
        "hooks",
        "params",
        "verify",
        "cert",
        "adapters",
        "stream",
        "trust_env",
        "max_redirects",
    ]

    def __init__(self):
        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol or protocol and host to the URL of the proxy
        #: (e.g. {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}) to
        #: be used on each :class:`Request <Request>`.
        self.proxies = {}

        #: Event-handling hooks.
        self.hooks = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params = {}

        #: Stream response content default.
        self.stream = False

        #: SSL Verification default.
        #: Defaults to `True`, requiring requests to verify the TLS certificate at the
        #: remote end.
        #: If verify is set to `False`, requests will accept any TLS certificate
        #: presented by the server, and will ignore hostname mismatches and/or
        #: expired certificates, which will make your application vulnerable to
        #: man-in-the-middle (MitM) attacks.
        #: Only set this to `False` for testing.
        self.verify = True

        #: SSL client certificate default, if String, path to ssl client
        #: cert file (.pem). If Tuple, ('cert', 'key') pair.
        self.cert = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        #: This defaults to requests.models.DEFAULT_REDIRECT_LIMIT, which is
        #: 30.
        self.max_redirects = DEFAULT_REDIRECT_LIMIT

        #: Trust environment settings for proxy configuration, default
        #: authentication and similar.
        self.trust_env = True

        #: A CookieJar containing all currently outstanding cookies set on this
        #: session. By default it is a
        #: :class:`RequestsCookieJar <requests.cookies.RequestsCookieJar>`, but
        #: may be any other ``cookielib.CookieJar`` compatible object.
        self.cookies = cookiejar_from_dict({})

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount("https://", HTTPAdapter())
        self.mount("http://", HTTPAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def prepare_request(self, request):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for
        transmission and returns it. The :class:`PreparedRequest` has settings
        merged from the :class:`Request <Request>` instance and those of the
        :class:`Session`.

        :param request: :class:`Request` instance to prepare with this
            session's settings.
        :rtype: requests.PreparedRequest
        """
        cookies = request.cookies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = merge_cookies(
            merge_cookies(RequestsCookieJar(), self.cookies), cookies
        )

        # Set environment's basic authentication if not explicitly set.
        auth = request.auth
        if self.trust_env and not auth and not self.auth:
            auth = get_netrc_auth(request.url)

        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(),
            url=request.url,
            files=request.files,
            data=request.data,
            json=request.json,
            headers=merge_setting(
                request.headers, self.headers, dict_class=CaseInsensitiveDict
            ),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(
        self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :rtype: requests.Response
        """
        # Create the Request.
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)

        return resp

    def get(self, url, **kwargs):
        r"""Sends a GET request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, **kwargs)

    def options(self, url, **kwargs):
        r"""Sends a OPTIONS request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url, **kwargs):
        r"""Sends a HEAD request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", False)
        return self.request("HEAD", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        r"""Sends a POST request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        r"""Sends a PUT request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PUT", url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        r"""Sends a PATCH request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PATCH", url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        r"""Sends a DELETE request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("DELETE", url, **kwargs)

    def send(self, request, **kwargs):
        """Send a given PreparedRequest.

        :rtype: requests.Response
        """
        # Set defaults that the hooks can utilize to ensure they always have
        # the correct parameters to reproduce the previous request.
        kwargs.setdefault("stream", self.stream)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("cert", self.cert)
        if "proxies" not in kwargs:
            kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)

        # It's possible that users might accidentally send a Request object.
        # Guard against that specific failure case.
        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")

        # Set up variables needed for resolve_redirects and dispatching of hooks
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks

        # Get the appropriate adapter to use
        adapter = self.get_adapter(url=request.url)

        # Start time (approximately) of the request
        start = preferred_clock()

        # Send the request
        r = adapter.send(request, **kwargs)

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)

        # Response manipulation hooks
        r = dispatch_hook("response", hooks, r, **kwargs)

        # Persist cookies
        if r.history:
            # If the hooks create history then we want those cookies too
            for resp in r.history:
                extract_cookies_to_jar(self.cookies, resp.request, resp.raw)

        extract_cookies_to_jar(self.cookies, request, r.raw)

        # Resolve redirects if allowed.
        if allow_redirects:
            # Redirect resolving generator.
            gen = self.resolve_redirects(r, request, **kwargs)
            history = [resp for resp in gen]
        else:
            history = []

        # Shuffle things around if there's history.
        if history:
            # Insert the first (original) request at the start
            history.insert(0, r)
            # Get the last request made
            r = history.pop()
            r.history = history

        # If redirects aren't being followed, store the response on the Request for Response.next().
        if not allow_redirects:
            try:
                r._next = next(
                    self.resolve_redirects(r, request, yield_requests=True, **kwargs)
                )
            except StopIteration:
                pass

        if not stream:
            r.content

        return r

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        """
        Check the environment and merge it with some settings.

        :rtype: dict
        """
        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            no_proxy = proxies.get("no_proxy") if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            for k, v in env_proxies.items():
                proxies.setdefault(k, v)

            # Look for requests environment configuration
            # and be compatible with cURL.
            if verify is True or verify is None:
                verify = (
                    os.environ.get("REQUESTS_CA_BUNDLE")
                    or os.environ.get("CURL_CA_BUNDLE")
                    or verify
                )

        # Merge all the kwargs.
        proxies = merge_setting(proxies, self.proxies)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        return {"proxies": proxies, "stream": stream, "verify": verify, "cert": cert}

    def get_adapter(self, url):
        """
        Returns the appropriate connection adapter for the given URL.

        :rtype: requests.adapters.BaseAdapter
        """
        for prefix, adapter in self.adapters.items():
            if url.lower().startswith(prefix.lower()):
                return adapter

        # Nothing matches :-/
        raise InvalidSchema(f"No connection adapters were found for {url!r}")

    def close(self):
        """Closes all adapters and as such the session"""
        for v in self.adapters.values():
            v.close()

    def mount(self, prefix, adapter):
        """Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by prefix length.
        """
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]

        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)

    def __getstate__(self):
        state = {attr: getattr(self, attr, None) for attr in self.__attrs__}
        return state

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)


def session():
    """
    Returns a :class:`Session` for context-management.

    .. deprecated:: 1.0.0

        This method has been deprecated since version 1.0.0 and is only kept for
        backwards compatibility. New code should use :class:`~requests.sessions.Session`
        to create a session. This may be removed at a future date.

    :rtype: Session
    """
    return Session()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\sessions.py ===
"""
requests.sessions
~~~~~~~~~~~~~~~~~

This module provides a Session object to manage and persist settings across
requests (cookies, auth, proxies).
"""
import os
import sys
import time
from collections import OrderedDict
from datetime import timedelta

from ._internal_utils import to_native_string
from .adapters import HTTPAdapter
from .auth import _basic_auth_str
from .compat import Mapping, cookielib, urljoin, urlparse
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    extract_cookies_to_jar,
    merge_cookies,
)
from .exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    InvalidSchema,
    TooManyRedirects,
)
from .hooks import default_hooks, dispatch_hook

# formerly defined here, reexposed here for backward compatibility
from .models import (  # noqa: F401
    DEFAULT_REDIRECT_LIMIT,
    REDIRECT_STATI,
    PreparedRequest,
    Request,
)
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (  # noqa: F401
    DEFAULT_PORTS,
    default_headers,
    get_auth_from_url,
    get_environ_proxies,
    get_netrc_auth,
    requote_uri,
    resolve_proxies,
    rewind_body,
    should_bypass_proxies,
    to_key_val_list,
)

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time


def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
    """Determines appropriate setting for a given request, taking into account
    the explicit setting on that request, and the setting in the session. If a
    setting is a dictionary, they will be merged together using `dict_class`
    """

    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting

    # Bypass if not a dictionary (e.g. verify)
    if not (
        isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)
    ):
        return request_setting

    merged_setting = dict_class(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]

    return merged_setting


def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks

    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks

    return merge_setting(request_hooks, session_hooks, dict_class)


class SessionRedirectMixin:
    def get_redirect_target(self, resp):
        """Receives a Response. Returns a redirect URI or ``None``"""
        # Due to the nature of how requests processes redirects this method will
        # be called at least once upon the original response and at least twice
        # on each subsequent redirect response (if any).
        # If a custom mixin is used to handle this logic, it may be advantageous
        # to cache the redirect location onto the response object as a private
        # attribute.
        if resp.is_redirect:
            location = resp.headers["location"]
            # Currently the underlying http module on py3 decode headers
            # in latin1, but empirical evidence suggests that latin1 is very
            # rarely used with non-ASCII characters in HTTP headers.
            # It is more likely to get UTF8 header rather than latin1.
            # This causes incorrect handling of UTF8 encoded location headers.
            # To solve this, we re-encode the location in latin1.
            location = location.encode("latin1")
            return to_native_string(location, "utf8")
        return None

    def should_strip_auth(self, old_url, new_url):
        """Decide whether Authorization header should be removed when redirecting"""
        old_parsed = urlparse(old_url)
        new_parsed = urlparse(new_url)
        if old_parsed.hostname != new_parsed.hostname:
            return True
        # Special case: allow http -> https redirect when using the standard
        # ports. This isn't specified by RFC 7235, but is kept to avoid
        # breaking backwards compatibility with older versions of requests
        # that allowed any redirects on the same host.
        if (
            old_parsed.scheme == "http"
            and old_parsed.port in (80, None)
            and new_parsed.scheme == "https"
            and new_parsed.port in (443, None)
        ):
            return False

        # Handle default port usage corresponding to scheme.
        changed_port = old_parsed.port != new_parsed.port
        changed_scheme = old_parsed.scheme != new_parsed.scheme
        default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
        if (
            not changed_scheme
            and old_parsed.port in default_port
            and new_parsed.port in default_port
        ):
            return False

        # Standard case: root URI must match
        return changed_port or changed_scheme

    def resolve_redirects(
        self,
        resp,
        req,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
        yield_requests=False,
        **adapter_kwargs,
    ):
        """Receives a Response. Returns a generator of Responses or Requests."""

        hist = []  # keep track of history

        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()

            # Update history and keep track of redirects.
            # resp.history must ignore the original request in this loop
            hist.append(resp)
            resp.history = hist[1:]

            try:
                resp.content  # Consume socket so it can be released
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                resp.raw.read(decode_content=False)

            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(
                    f"Exceeded {self.max_redirects} redirects.", response=resp
                )

            # Release the connection back into the pool.
            resp.close()

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith("//"):
                parsed_rurl = urlparse(resp.url)
                url = ":".join([to_native_string(parsed_rurl.scheme), url])

            # Normalize url case and attach previous fragment if needed (RFC 7231 7.1.2)
            parsed = urlparse(url)
            if parsed.fragment == "" and previous_fragment:
                parsed = parsed._replace(fragment=previous_fragment)
            elif parsed.fragment:
                previous_fragment = parsed.fragment
            url = parsed.geturl()

            # Facilitate relative 'location' headers, as allowed by RFC 7231.
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            # Compliant with RFC3986, we percent encode the url.
            if not parsed.netloc:
                url = urljoin(resp.url, requote_uri(url))
            else:
                url = requote_uri(url)

            prepared_request.url = to_native_string(url)

            self.rebuild_method(prepared_request, resp)

            # https://github.com/psf/requests/issues/1084
            if resp.status_code not in (
                codes.temporary_redirect,
                codes.permanent_redirect,
            ):
                # https://github.com/psf/requests/issues/3490
                purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
                for header in purged_headers:
                    prepared_request.headers.pop(header, None)
                prepared_request.body = None

            headers = prepared_request.headers
            headers.pop("Cookie", None)

            # Extract any cookies sent on the response to the cookiejar
            # in the new request. Because we've mutated our copied prepared
            # request, use the old one that we haven't yet touched.
            extract_cookies_to_jar(prepared_request._cookies, req, resp.raw)
            merge_cookies(prepared_request._cookies, self.cookies)
            prepared_request.prepare_cookies(prepared_request._cookies)

            # Rebuild auth and proxy information.
            proxies = self.rebuild_proxies(prepared_request, proxies)
            self.rebuild_auth(prepared_request, resp)

            # A failed tell() sets `_body_position` to `object()`. This non-None
            # value ensures `rewindable` will be True, allowing us to raise an
            # UnrewindableBodyError, instead of hanging the connection.
            rewindable = prepared_request._body_position is not None and (
                "Content-Length" in headers or "Transfer-Encoding" in headers
            )

            # Attempt to rewind consumed file-like object.
            if rewindable:
                rewind_body(prepared_request)

            # Override the original request.
            req = prepared_request

            if yield_requests:
                yield req
            else:
                resp = self.send(
                    req,
                    stream=stream,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies,
                    allow_redirects=False,
                    **adapter_kwargs,
                )

                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

                # extract redirect url, if any, for the next loop
                url = self.get_redirect_target(resp)
                yield resp

    def rebuild_auth(self, prepared_request, response):
        """When being redirected we may want to strip authentication from the
        request to avoid leaking credentials. This method intelligently removes
        and reapplies authentication where possible to avoid credential loss.
        """
        headers = prepared_request.headers
        url = prepared_request.url

        if "Authorization" in headers and self.should_strip_auth(
            response.request.url, url
        ):
            # If we get redirected to a new host, we should strip out any
            # authentication headers.
            del headers["Authorization"]

        # .netrc might have more auth for us on our new host.
        new_auth = get_netrc_auth(url) if self.trust_env else None
        if new_auth is not None:
            prepared_request.prepare_auth(new_auth)

    def rebuild_proxies(self, prepared_request, proxies):
        """This method re-evaluates the proxy configuration by considering the
        environment variables. If we are redirected to a URL covered by
        NO_PROXY, we strip the proxy configuration. Otherwise, we set missing
        proxy keys for this URL (in case they were stripped by a previous
        redirect).

        This method also replaces the Proxy-Authorization header where
        necessary.

        :rtype: dict
        """
        headers = prepared_request.headers
        scheme = urlparse(prepared_request.url).scheme
        new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)

        if "Proxy-Authorization" in headers:
            del headers["Proxy-Authorization"]

        try:
            username, password = get_auth_from_url(new_proxies[scheme])
        except KeyError:
            username, password = None, None

        # urllib3 handles proxy authorization for us in the standard adapter.
        # Avoid appending this to TLS tunneled requests where it may be leaked.
        if not scheme.startswith("https") and username and password:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return new_proxies

    def rebuild_method(self, prepared_request, response):
        """When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = prepared_request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.see_other and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # First, turn 302s into GETs.
        if response.status_code == codes.found and method != "HEAD":
            method = "GET"

        # Second, if a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in Issue 1704.
        if response.status_code == codes.moved and method == "POST":
            method = "GET"

        prepared_request.method = method


class Session(SessionRedirectMixin):
    """A Requests session.

    Provides cookie persistence, connection-pooling, and configuration.

    Basic Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> s.get('https://httpbin.org/get')
      <Response [200]>

    Or as a context manager::

      >>> with requests.Session() as s:
      ...     s.get('https://httpbin.org/get')
      <Response [200]>
    """

    __attrs__ = [
        "headers",
        "cookies",
        "auth",
        "proxies",
        "hooks",
        "params",
        "verify",
        "cert",
        "adapters",
        "stream",
        "trust_env",
        "max_redirects",
    ]

    def __init__(self):
        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol or protocol and host to the URL of the proxy
        #: (e.g. {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}) to
        #: be used on each :class:`Request <Request>`.
        self.proxies = {}

        #: Event-handling hooks.
        self.hooks = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params = {}

        #: Stream response content default.
        self.stream = False

        #: SSL Verification default.
        #: Defaults to `True`, requiring requests to verify the TLS certificate at the
        #: remote end.
        #: If verify is set to `False`, requests will accept any TLS certificate
        #: presented by the server, and will ignore hostname mismatches and/or
        #: expired certificates, which will make your application vulnerable to
        #: man-in-the-middle (MitM) attacks.
        #: Only set this to `False` for testing.
        self.verify = True

        #: SSL client certificate default, if String, path to ssl client
        #: cert file (.pem). If Tuple, ('cert', 'key') pair.
        self.cert = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        #: This defaults to requests.models.DEFAULT_REDIRECT_LIMIT, which is
        #: 30.
        self.max_redirects = DEFAULT_REDIRECT_LIMIT

        #: Trust environment settings for proxy configuration, default
        #: authentication and similar.
        self.trust_env = True

        #: A CookieJar containing all currently outstanding cookies set on this
        #: session. By default it is a
        #: :class:`RequestsCookieJar <requests.cookies.RequestsCookieJar>`, but
        #: may be any other ``cookielib.CookieJar`` compatible object.
        self.cookies = cookiejar_from_dict({})

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount("https://", HTTPAdapter())
        self.mount("http://", HTTPAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def prepare_request(self, request):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for
        transmission and returns it. The :class:`PreparedRequest` has settings
        merged from the :class:`Request <Request>` instance and those of the
        :class:`Session`.

        :param request: :class:`Request` instance to prepare with this
            session's settings.
        :rtype: requests.PreparedRequest
        """
        cookies = request.cookies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = merge_cookies(
            merge_cookies(RequestsCookieJar(), self.cookies), cookies
        )

        # Set environment's basic authentication if not explicitly set.
        auth = request.auth
        if self.trust_env and not auth and not self.auth:
            auth = get_netrc_auth(request.url)

        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(),
            url=request.url,
            files=request.files,
            data=request.data,
            json=request.json,
            headers=merge_setting(
                request.headers, self.headers, dict_class=CaseInsensitiveDict
            ),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(
        self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :rtype: requests.Response
        """
        # Create the Request.
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)

        return resp

    def get(self, url, **kwargs):
        r"""Sends a GET request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, **kwargs)

    def options(self, url, **kwargs):
        r"""Sends a OPTIONS request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url, **kwargs):
        r"""Sends a HEAD request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", False)
        return self.request("HEAD", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        r"""Sends a POST request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        r"""Sends a PUT request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PUT", url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        r"""Sends a PATCH request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PATCH", url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        r"""Sends a DELETE request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("DELETE", url, **kwargs)

    def send(self, request, **kwargs):
        """Send a given PreparedRequest.

        :rtype: requests.Response
        """
        # Set defaults that the hooks can utilize to ensure they always have
        # the correct parameters to reproduce the previous request.
        kwargs.setdefault("stream", self.stream)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("cert", self.cert)
        if "proxies" not in kwargs:
            kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)

        # It's possible that users might accidentally send a Request object.
        # Guard against that specific failure case.
        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")

        # Set up variables needed for resolve_redirects and dispatching of hooks
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks

        # Get the appropriate adapter to use
        adapter = self.get_adapter(url=request.url)

        # Start time (approximately) of the request
        start = preferred_clock()

        # Send the request
        r = adapter.send(request, **kwargs)

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)

        # Response manipulation hooks
        r = dispatch_hook("response", hooks, r, **kwargs)

        # Persist cookies
        if r.history:
            # If the hooks create history then we want those cookies too
            for resp in r.history:
                extract_cookies_to_jar(self.cookies, resp.request, resp.raw)

        extract_cookies_to_jar(self.cookies, request, r.raw)

        # Resolve redirects if allowed.
        if allow_redirects:
            # Redirect resolving generator.
            gen = self.resolve_redirects(r, request, **kwargs)
            history = [resp for resp in gen]
        else:
            history = []

        # Shuffle things around if there's history.
        if history:
            # Insert the first (original) request at the start
            history.insert(0, r)
            # Get the last request made
            r = history.pop()
            r.history = history

        # If redirects aren't being followed, store the response on the Request for Response.next().
        if not allow_redirects:
            try:
                r._next = next(
                    self.resolve_redirects(r, request, yield_requests=True, **kwargs)
                )
            except StopIteration:
                pass

        if not stream:
            r.content

        return r

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        """
        Check the environment and merge it with some settings.

        :rtype: dict
        """
        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            no_proxy = proxies.get("no_proxy") if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            for k, v in env_proxies.items():
                proxies.setdefault(k, v)

            # Look for requests environment configuration
            # and be compatible with cURL.
            if verify is True or verify is None:
                verify = (
                    os.environ.get("REQUESTS_CA_BUNDLE")
                    or os.environ.get("CURL_CA_BUNDLE")
                    or verify
                )

        # Merge all the kwargs.
        proxies = merge_setting(proxies, self.proxies)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        return {"proxies": proxies, "stream": stream, "verify": verify, "cert": cert}

    def get_adapter(self, url):
        """
        Returns the appropriate connection adapter for the given URL.

        :rtype: requests.adapters.BaseAdapter
        """
        for prefix, adapter in self.adapters.items():
            if url.lower().startswith(prefix.lower()):
                return adapter

        # Nothing matches :-/
        raise InvalidSchema(f"No connection adapters were found for {url!r}")

    def close(self):
        """Closes all adapters and as such the session"""
        for v in self.adapters.values():
            v.close()

    def mount(self, prefix, adapter):
        """Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by prefix length.
        """
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]

        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)

    def __getstate__(self):
        state = {attr: getattr(self, attr, None) for attr in self.__attrs__}
        return state

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)


def session():
    """
    Returns a :class:`Session` for context-management.

    .. deprecated:: 1.0.0

        This method has been deprecated since version 1.0.0 and is only kept for
        backwards compatibility. New code should use :class:`~requests.sessions.Session`
        to create a session. This may be removed at a future date.

    :rtype: Session
    """
    return Session()

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\repocard.py ===
import os
import re
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Type, Union

import requests
import yaml

from huggingface_hub.file_download import hf_hub_download
from huggingface_hub.hf_api import upload_file
from huggingface_hub.repocard_data import (
    CardData,
    DatasetCardData,
    EvalResult,
    ModelCardData,
    SpaceCardData,
    eval_results_to_model_index,
    model_index_to_eval_results,
)
from huggingface_hub.utils import get_session, is_jinja_available, yaml_dump

from . import constants
from .errors import EntryNotFoundError
from .utils import SoftTemporaryDirectory, logging, validate_hf_hub_args


logger = logging.get_logger(__name__)


TEMPLATE_MODELCARD_PATH = Path(__file__).parent / "templates" / "modelcard_template.md"
TEMPLATE_DATASETCARD_PATH = Path(__file__).parent / "templates" / "datasetcard_template.md"

# exact same regex as in the Hub server. Please keep in sync.
# See https://github.com/huggingface/moon-landing/blob/main/server/lib/ViewMarkdown.ts#L18
REGEX_YAML_BLOCK = re.compile(r"^(\s*---[\r\n]+)([\S\s]*?)([\r\n]+---(\r\n|\n|$))")


class RepoCard:
    card_data_class = CardData
    default_template_path = TEMPLATE_MODELCARD_PATH
    repo_type = "model"

    def __init__(self, content: str, ignore_metadata_errors: bool = False):
        """Initialize a RepoCard from string content. The content should be a
        Markdown file with a YAML block at the beginning and a Markdown body.

        Args:
            content (`str`): The content of the Markdown file.

        Example:
            ```python
            >>> from huggingface_hub.repocard import RepoCard
            >>> text = '''
            ... ---
            ... language: en
            ... license: mit
            ... ---
            ...
            ... # My repo
            ... '''
            >>> card = RepoCard(text)
            >>> card.data.to_dict()
            {'language': 'en', 'license': 'mit'}
            >>> card.text
            '\\n# My repo\\n'

            ```
        <Tip>
        Raises the following error:

            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              when the content of the repo card metadata is not a dictionary.

        </Tip>
        """

        # Set the content of the RepoCard, as well as underlying .data and .text attributes.
        # See the `content` property setter for more details.
        self.ignore_metadata_errors = ignore_metadata_errors
        self.content = content

    @property
    def content(self):
        """The content of the RepoCard, including the YAML block and the Markdown body."""
        line_break = _detect_line_ending(self._content) or "\n"
        return f"---{line_break}{self.data.to_yaml(line_break=line_break, original_order=self._original_order)}{line_break}---{line_break}{self.text}"

    @content.setter
    def content(self, content: str):
        """Set the content of the RepoCard."""
        self._content = content

        match = REGEX_YAML_BLOCK.search(content)
        if match:
            # Metadata found in the YAML block
            yaml_block = match.group(2)
            self.text = content[match.end() :]
            data_dict = yaml.safe_load(yaml_block)

            if data_dict is None:
                data_dict = {}

            # The YAML block's data should be a dictionary
            if not isinstance(data_dict, dict):
                raise ValueError("repo card metadata block should be a dict")
        else:
            # Model card without metadata... create empty metadata
            logger.warning("Repo card metadata block was not found. Setting CardData to empty.")
            data_dict = {}
            self.text = content

        self.data = self.card_data_class(**data_dict, ignore_metadata_errors=self.ignore_metadata_errors)
        self._original_order = list(data_dict.keys())

    def __str__(self):
        return self.content

    def save(self, filepath: Union[Path, str]):
        r"""Save a RepoCard to a file.

        Args:
            filepath (`Union[Path, str]`): Filepath to the markdown file to save.

        Example:
            ```python
            >>> from huggingface_hub.repocard import RepoCard
            >>> card = RepoCard("---\nlanguage: en\n---\n# This is a test repo card")
            >>> card.save("/tmp/test.md")

            ```
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Preserve newlines as in the existing file.
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            f.write(str(self))

    @classmethod
    def load(
        cls,
        repo_id_or_path: Union[str, Path],
        repo_type: Optional[str] = None,
        token: Optional[str] = None,
        ignore_metadata_errors: bool = False,
    ):
        """Initialize a RepoCard from a Hugging Face Hub repo's README.md or a local filepath.

        Args:
            repo_id_or_path (`Union[str, Path]`):
                The repo ID associated with a Hugging Face Hub repo or a local filepath.
            repo_type (`str`, *optional*):
                The type of Hugging Face repo to push to. Defaults to None, which will use use "model". Other options
                are "dataset" and "space". Not used when loading from a local filepath. If this is called from a child
                class, the default value will be the child class's `repo_type`.
            token (`str`, *optional*):
                Authentication token, obtained with `huggingface_hub.HfApi.login` method. Will default to the stored token.
            ignore_metadata_errors (`str`):
                If True, errors while parsing the metadata section will be ignored. Some information might be lost during
                the process. Use it at your own risk.

        Returns:
            [`huggingface_hub.repocard.RepoCard`]: The RepoCard (or subclass) initialized from the repo's
                README.md file or filepath.

        Example:
            ```python
            >>> from huggingface_hub.repocard import RepoCard
            >>> card = RepoCard.load("nateraw/food")
            >>> assert card.data.tags == ["generated_from_trainer", "image-classification", "pytorch"]

            ```
        """

        if Path(repo_id_or_path).is_file():
            card_path = Path(repo_id_or_path)
        elif isinstance(repo_id_or_path, str):
            card_path = Path(
                hf_hub_download(
                    repo_id_or_path,
                    constants.REPOCARD_NAME,
                    repo_type=repo_type or cls.repo_type,
                    token=token,
                )
            )
        else:
            raise ValueError(f"Cannot load RepoCard: path not found on disk ({repo_id_or_path}).")

        # Preserve newlines in the existing file.
        with card_path.open(mode="r", newline="", encoding="utf-8") as f:
            return cls(f.read(), ignore_metadata_errors=ignore_metadata_errors)

    def validate(self, repo_type: Optional[str] = None):
        """Validates card against Hugging Face Hub's card validation logic.
        Using this function requires access to the internet, so it is only called
        internally by [`huggingface_hub.repocard.RepoCard.push_to_hub`].

        Args:
            repo_type (`str`, *optional*, defaults to "model"):
                The type of Hugging Face repo to push to. Options are "model", "dataset", and "space".
                If this function is called from a child class, the default will be the child class's `repo_type`.

        <Tip>
        Raises the following errors:

            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if the card fails validation checks.
            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the request to the Hub API fails for any other reason.

        </Tip>
        """

        # If repo type is provided, otherwise, use the repo type of the card.
        repo_type = repo_type or self.repo_type

        body = {
            "repoType": repo_type,
            "content": str(self),
        }
        headers = {"Accept": "text/plain"}

        try:
            r = get_session().post("https://huggingface.co/api/validate-yaml", body, headers=headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if r.status_code == 400:
                raise ValueError(r.text)
            else:
                raise exc

    def push_to_hub(
        self,
        repo_id: str,
        token: Optional[str] = None,
        repo_type: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
    ):
        """Push a RepoCard to a Hugging Face Hub repo.

        Args:
            repo_id (`str`):
                The repo ID of the Hugging Face Hub repo to push to. Example: "nateraw/food".
            token (`str`, *optional*):
                Authentication token, obtained with `huggingface_hub.HfApi.login` method. Will default to
                the stored token.
            repo_type (`str`, *optional*, defaults to "model"):
                The type of Hugging Face repo to push to. Options are "model", "dataset", and "space". If this
                function is called by a child class, it will default to the child class's `repo_type`.
            commit_message (`str`, *optional*):
                The summary / title / first line of the generated commit.
            commit_description (`str`, *optional*)
                The description of the generated commit.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            create_pr (`bool`, *optional*):
                Whether or not to create a Pull Request with this commit. Defaults to `False`.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.
        Returns:
            `str`: URL of the commit which updated the card metadata.
        """

        # If repo type is provided, otherwise, use the repo type of the card.
        repo_type = repo_type or self.repo_type

        # Validate card before pushing to hub
        self.validate(repo_type=repo_type)

        with SoftTemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / constants.REPOCARD_NAME
            tmp_path.write_text(str(self))
            url = upload_file(
                path_or_fileobj=str(tmp_path),
                path_in_repo=constants.REPOCARD_NAME,
                repo_id=repo_id,
                token=token,
                repo_type=repo_type,
                commit_message=commit_message,
                commit_description=commit_description,
                create_pr=create_pr,
                revision=revision,
                parent_commit=parent_commit,
            )
        return url

    @classmethod
    def from_template(
        cls,
        card_data: CardData,
        template_path: Optional[str] = None,
        template_str: Optional[str] = None,
        **template_kwargs,
    ):
        """Initialize a RepoCard from a template. By default, it uses the default template.

        Templates are Jinja2 templates that can be customized by passing keyword arguments.

        Args:
            card_data (`huggingface_hub.CardData`):
                A huggingface_hub.CardData instance containing the metadata you want to include in the YAML
                header of the repo card on the Hugging Face Hub.
            template_path (`str`, *optional*):
                A path to a markdown file with optional Jinja template variables that can be filled
                in with `template_kwargs`. Defaults to the default template.

        Returns:
            [`huggingface_hub.repocard.RepoCard`]: A RepoCard instance with the specified card data and content from the
            template.
        """
        if is_jinja_available():
            import jinja2
        else:
            raise ImportError(
                "Using RepoCard.from_template requires Jinja2 to be installed. Please"
                " install it with `pip install Jinja2`."
            )

        kwargs = card_data.to_dict().copy()
        kwargs.update(template_kwargs)  # Template_kwargs have priority

        if template_path is not None:
            template_str = Path(template_path).read_text()
        if template_str is None:
            template_str = Path(cls.default_template_path).read_text()
        template = jinja2.Template(template_str)
        content = template.render(card_data=card_data.to_yaml(), **kwargs)
        return cls(content)


class ModelCard(RepoCard):
    card_data_class = ModelCardData
    default_template_path = TEMPLATE_MODELCARD_PATH
    repo_type = "model"

    @classmethod
    def from_template(  # type: ignore # violates Liskov property but easier to use
        cls,
        card_data: ModelCardData,
        template_path: Optional[str] = None,
        template_str: Optional[str] = None,
        **template_kwargs,
    ):
        """Initialize a ModelCard from a template. By default, it uses the default template, which can be found here:
        https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/templates/modelcard_template.md

        Templates are Jinja2 templates that can be customized by passing keyword arguments.

        Args:
            card_data (`huggingface_hub.ModelCardData`):
                A huggingface_hub.ModelCardData instance containing the metadata you want to include in the YAML
                header of the model card on the Hugging Face Hub.
            template_path (`str`, *optional*):
                A path to a markdown file with optional Jinja template variables that can be filled
                in with `template_kwargs`. Defaults to the default template.

        Returns:
            [`huggingface_hub.ModelCard`]: A ModelCard instance with the specified card data and content from the
            template.

        Example:
            ```python
            >>> from huggingface_hub import ModelCard, ModelCardData, EvalResult

            >>> # Using the Default Template
            >>> card_data = ModelCardData(
            ...     language='en',
            ...     license='mit',
            ...     library_name='timm',
            ...     tags=['image-classification', 'resnet'],
            ...     datasets=['beans'],
            ...     metrics=['accuracy'],
            ... )
            >>> card = ModelCard.from_template(
            ...     card_data,
            ...     model_description='This model does x + y...'
            ... )

            >>> # Including Evaluation Results
            >>> card_data = ModelCardData(
            ...     language='en',
            ...     tags=['image-classification', 'resnet'],
            ...     eval_results=[
            ...         EvalResult(
            ...             task_type='image-classification',
            ...             dataset_type='beans',
            ...             dataset_name='Beans',
            ...             metric_type='accuracy',
            ...             metric_value=0.9,
            ...         ),
            ...     ],
            ...     model_name='my-cool-model',
            ... )
            >>> card = ModelCard.from_template(card_data)

            >>> # Using a Custom Template
            >>> card_data = ModelCardData(
            ...     language='en',
            ...     tags=['image-classification', 'resnet']
            ... )
            >>> card = ModelCard.from_template(
            ...     card_data=card_data,
            ...     template_path='./src/huggingface_hub/templates/modelcard_template.md',
            ...     custom_template_var='custom value',  # will be replaced in template if it exists
            ... )

            ```
        """
        return super().from_template(card_data, template_path, template_str, **template_kwargs)


class DatasetCard(RepoCard):
    card_data_class = DatasetCardData
    default_template_path = TEMPLATE_DATASETCARD_PATH
    repo_type = "dataset"

    @classmethod
    def from_template(  # type: ignore # violates Liskov property but easier to use
        cls,
        card_data: DatasetCardData,
        template_path: Optional[str] = None,
        template_str: Optional[str] = None,
        **template_kwargs,
    ):
        """Initialize a DatasetCard from a template. By default, it uses the default template, which can be found here:
        https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/templates/datasetcard_template.md

        Templates are Jinja2 templates that can be customized by passing keyword arguments.

        Args:
            card_data (`huggingface_hub.DatasetCardData`):
                A huggingface_hub.DatasetCardData instance containing the metadata you want to include in the YAML
                header of the dataset card on the Hugging Face Hub.
            template_path (`str`, *optional*):
                A path to a markdown file with optional Jinja template variables that can be filled
                in with `template_kwargs`. Defaults to the default template.

        Returns:
            [`huggingface_hub.DatasetCard`]: A DatasetCard instance with the specified card data and content from the
            template.

        Example:
            ```python
            >>> from huggingface_hub import DatasetCard, DatasetCardData

            >>> # Using the Default Template
            >>> card_data = DatasetCardData(
            ...     language='en',
            ...     license='mit',
            ...     annotations_creators='crowdsourced',
            ...     task_categories=['text-classification'],
            ...     task_ids=['sentiment-classification', 'text-scoring'],
            ...     multilinguality='monolingual',
            ...     pretty_name='My Text Classification Dataset',
            ... )
            >>> card = DatasetCard.from_template(
            ...     card_data,
            ...     pretty_name=card_data.pretty_name,
            ... )

            >>> # Using a Custom Template
            >>> card_data = DatasetCardData(
            ...     language='en',
            ...     license='mit',
            ... )
            >>> card = DatasetCard.from_template(
            ...     card_data=card_data,
            ...     template_path='./src/huggingface_hub/templates/datasetcard_template.md',
            ...     custom_template_var='custom value',  # will be replaced in template if it exists
            ... )

            ```
        """
        return super().from_template(card_data, template_path, template_str, **template_kwargs)


class SpaceCard(RepoCard):
    card_data_class = SpaceCardData
    default_template_path = TEMPLATE_MODELCARD_PATH
    repo_type = "space"


def _detect_line_ending(content: str) -> Literal["\r", "\n", "\r\n", None]:  # noqa: F722
    """Detect the line ending of a string. Used by RepoCard to avoid making huge diff on newlines.

    Uses same implementation as in Hub server, keep it in sync.

    Returns:
        str: The detected line ending of the string.
    """
    cr = content.count("\r")
    lf = content.count("\n")
    crlf = content.count("\r\n")
    if cr + lf == 0:
        return None
    if crlf == cr and crlf == lf:
        return "\r\n"
    if cr > lf:
        return "\r"
    else:
        return "\n"


def metadata_load(local_path: Union[str, Path]) -> Optional[Dict]:
    content = Path(local_path).read_text()
    match = REGEX_YAML_BLOCK.search(content)
    if match:
        yaml_block = match.group(2)
        data = yaml.safe_load(yaml_block)
        if data is None or isinstance(data, dict):
            return data
        raise ValueError("repo card metadata block should be a dict")
    else:
        return None


def metadata_save(local_path: Union[str, Path], data: Dict) -> None:
    """
    Save the metadata dict in the upper YAML part Trying to preserve newlines as
    in the existing file. Docs about open() with newline="" parameter:
    https://docs.python.org/3/library/functions.html?highlight=open#open Does
    not work with "^M" linebreaks, which are replaced by \n
    """
    line_break = "\n"
    content = ""
    # try to detect existing newline character
    if os.path.exists(local_path):
        with open(local_path, "r", newline="", encoding="utf8") as readme:
            content = readme.read()
            if isinstance(readme.newlines, tuple):
                line_break = readme.newlines[0]
            elif isinstance(readme.newlines, str):
                line_break = readme.newlines

    # creates a new file if it not
    with open(local_path, "w", newline="", encoding="utf8") as readme:
        data_yaml = yaml_dump(data, sort_keys=False, line_break=line_break)
        # sort_keys: keep dict order
        match = REGEX_YAML_BLOCK.search(content)
        if match:
            output = content[: match.start()] + f"---{line_break}{data_yaml}---{line_break}" + content[match.end() :]
        else:
            output = f"---{line_break}{data_yaml}---{line_break}{content}"

        readme.write(output)
        readme.close()


def metadata_eval_result(
    *,
    model_pretty_name: str,
    task_pretty_name: str,
    task_id: str,
    metrics_pretty_name: str,
    metrics_id: str,
    metrics_value: Any,
    dataset_pretty_name: str,
    dataset_id: str,
    metrics_config: Optional[str] = None,
    metrics_verified: bool = False,
    dataset_config: Optional[str] = None,
    dataset_split: Optional[str] = None,
    dataset_revision: Optional[str] = None,
    metrics_verification_token: Optional[str] = None,
) -> Dict:
    """
    Creates a metadata dict with the result from a model evaluated on a dataset.

    Args:
        model_pretty_name (`str`):
            The name of the model in natural language.
        task_pretty_name (`str`):
            The name of a task in natural language.
        task_id (`str`):
            Example: automatic-speech-recognition. A task id.
        metrics_pretty_name (`str`):
            A name for the metric in natural language. Example: Test WER.
        metrics_id (`str`):
            Example: wer. A metric id from https://hf.co/metrics.
        metrics_value (`Any`):
            The value from the metric. Example: 20.0 or "20.0 ± 1.2".
        dataset_pretty_name (`str`):
            The name of the dataset in natural language.
        dataset_id (`str`):
            Example: common_voice. A dataset id from https://hf.co/datasets.
        metrics_config (`str`, *optional*):
            The name of the metric configuration used in `load_metric()`.
            Example: bleurt-large-512 in `load_metric("bleurt", "bleurt-large-512")`.
        metrics_verified (`bool`, *optional*, defaults to `False`):
            Indicates whether the metrics originate from Hugging Face's [evaluation service](https://huggingface.co/spaces/autoevaluate/model-evaluator) or not. Automatically computed by Hugging Face, do not set.
        dataset_config (`str`, *optional*):
            Example: fr. The name of the dataset configuration used in `load_dataset()`.
        dataset_split (`str`, *optional*):
            Example: test. The name of the dataset split used in `load_dataset()`.
        dataset_revision (`str`, *optional*):
            Example: 5503434ddd753f426f4b38109466949a1217c2bb. The name of the dataset dataset revision
            used in `load_dataset()`.
        metrics_verification_token (`bool`, *optional*):
            A JSON Web Token that is used to verify whether the metrics originate from Hugging Face's [evaluation service](https://huggingface.co/spaces/autoevaluate/model-evaluator) or not.

    Returns:
        `dict`: a metadata dict with the result from a model evaluated on a dataset.

    Example:
        ```python
        >>> from huggingface_hub import metadata_eval_result
        >>> results = metadata_eval_result(
        ...         model_pretty_name="RoBERTa fine-tuned on ReactionGIF",
        ...         task_pretty_name="Text Classification",
        ...         task_id="text-classification",
        ...         metrics_pretty_name="Accuracy",
        ...         metrics_id="accuracy",
        ...         metrics_value=0.2662102282047272,
        ...         dataset_pretty_name="ReactionJPEG",
        ...         dataset_id="julien-c/reactionjpeg",
        ...         dataset_config="default",
        ...         dataset_split="test",
        ... )
        >>> results == {
        ...     'model-index': [
        ...         {
        ...             'name': 'RoBERTa fine-tuned on ReactionGIF',
        ...             'results': [
        ...                 {
        ...                     'task': {
        ...                         'type': 'text-classification',
        ...                         'name': 'Text Classification'
        ...                     },
        ...                     'dataset': {
        ...                         'name': 'ReactionJPEG',
        ...                         'type': 'julien-c/reactionjpeg',
        ...                         'config': 'default',
        ...                         'split': 'test'
        ...                     },
        ...                     'metrics': [
        ...                         {
        ...                             'type': 'accuracy',
        ...                             'value': 0.2662102282047272,
        ...                             'name': 'Accuracy',
        ...                             'verified': False
        ...                         }
        ...                     ]
        ...                 }
        ...             ]
        ...         }
        ...     ]
        ... }
        True

        ```
    """

    return {
        "model-index": eval_results_to_model_index(
            model_name=model_pretty_name,
            eval_results=[
                EvalResult(
                    task_name=task_pretty_name,
                    task_type=task_id,
                    metric_name=metrics_pretty_name,
                    metric_type=metrics_id,
                    metric_value=metrics_value,
                    dataset_name=dataset_pretty_name,
                    dataset_type=dataset_id,
                    metric_config=metrics_config,
                    verified=metrics_verified,
                    verify_token=metrics_verification_token,
                    dataset_config=dataset_config,
                    dataset_split=dataset_split,
                    dataset_revision=dataset_revision,
                )
            ],
        )
    }


@validate_hf_hub_args
def metadata_update(
    repo_id: str,
    metadata: Dict,
    *,
    repo_type: Optional[str] = None,
    overwrite: bool = False,
    token: Optional[str] = None,
    commit_message: Optional[str] = None,
    commit_description: Optional[str] = None,
    revision: Optional[str] = None,
    create_pr: bool = False,
    parent_commit: Optional[str] = None,
) -> str:
    """
    Updates the metadata in the README.md of a repository on the Hugging Face Hub.
    If the README.md file doesn't exist yet, a new one is created with metadata and an
    the default ModelCard or DatasetCard template. For `space` repo, an error is thrown
    as a Space cannot exist without a `README.md` file.

    Args:
        repo_id (`str`):
            The name of the repository.
        metadata (`dict`):
            A dictionary containing the metadata to be updated.
        repo_type (`str`, *optional*):
            Set to `"dataset"` or `"space"` if updating to a dataset or space,
            `None` or `"model"` if updating to a model. Default is `None`.
        overwrite (`bool`, *optional*, defaults to `False`):
            If set to `True` an existing field can be overwritten, otherwise
            attempting to overwrite an existing field will cause an error.
        token (`str`, *optional*):
            The Hugging Face authentication token.
        commit_message (`str`, *optional*):
            The summary / title / first line of the generated commit. Defaults to
            `f"Update metadata with huggingface_hub"`
        commit_description (`str` *optional*)
            The description of the generated commit
        revision (`str`, *optional*):
            The git revision to commit from. Defaults to the head of the
            `"main"` branch.
        create_pr (`boolean`, *optional*):
            Whether or not to create a Pull Request from `revision` with that commit.
            Defaults to `False`.
        parent_commit (`str`, *optional*):
            The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
            If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
            If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
            Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
            especially useful if the repo is updated / committed to concurrently.
    Returns:
        `str`: URL of the commit which updated the card metadata.

    Example:
        ```python
        >>> from huggingface_hub import metadata_update
        >>> metadata = {'model-index': [{'name': 'RoBERTa fine-tuned on ReactionGIF',
        ...             'results': [{'dataset': {'name': 'ReactionGIF',
        ...                                      'type': 'julien-c/reactiongif'},
        ...                           'metrics': [{'name': 'Recall',
        ...                                        'type': 'recall',
        ...                                        'value': 0.7762102282047272}],
        ...                          'task': {'name': 'Text Classification',
        ...                                   'type': 'text-classification'}}]}]}
        >>> url = metadata_update("hf-internal-testing/reactiongif-roberta-card", metadata)

        ```
    """
    commit_message = commit_message if commit_message is not None else "Update metadata with huggingface_hub"

    # Card class given repo_type
    card_class: Type[RepoCard]
    if repo_type is None or repo_type == "model":
        card_class = ModelCard
    elif repo_type == "dataset":
        card_class = DatasetCard
    elif repo_type == "space":
        card_class = RepoCard
    else:
        raise ValueError(f"Unknown repo_type: {repo_type}")

    # Either load repo_card from the Hub or create an empty one.
    # NOTE: Will not create the repo if it doesn't exist.
    try:
        card = card_class.load(repo_id, token=token, repo_type=repo_type)
    except EntryNotFoundError:
        if repo_type == "space":
            raise ValueError("Cannot update metadata on a Space that doesn't contain a `README.md` file.")

        # Initialize a ModelCard or DatasetCard from default template and no data.
        card = card_class.from_template(CardData())

    for key, value in metadata.items():
        if key == "model-index":
            # if the new metadata doesn't include a name, either use existing one or repo name
            if "name" not in value[0]:
                value[0]["name"] = getattr(card, "model_name", repo_id)
            model_name, new_results = model_index_to_eval_results(value)
            if card.data.eval_results is None:
                card.data.eval_results = new_results
                card.data.model_name = model_name
            else:
                existing_results = card.data.eval_results

                # Iterate over new results
                #   Iterate over existing results
                #       If both results describe the same metric but value is different:
                #           If overwrite=True: overwrite the metric value
                #           Else: raise ValueError
                #       Else: append new result to existing ones.
                for new_result in new_results:
                    result_found = False
                    for existing_result in existing_results:
                        if new_result.is_equal_except_value(existing_result):
                            if new_result != existing_result and not overwrite:
                                raise ValueError(
                                    "You passed a new value for the existing metric"
                                    f" 'name: {new_result.metric_name}, type: "
                                    f"{new_result.metric_type}'. Set `overwrite=True`"
                                    " to overwrite existing metrics."
                                )
                            result_found = True
                            existing_result.metric_value = new_result.metric_value
                            if existing_result.verified is True:
                                existing_result.verify_token = new_result.verify_token
                    if not result_found:
                        card.data.eval_results.append(new_result)
        else:
            # Any metadata that is not a result metric
            if card.data.get(key) is not None and not overwrite and card.data.get(key) != value:
                raise ValueError(
                    f"You passed a new value for the existing meta data field '{key}'."
                    " Set `overwrite=True` to overwrite existing metadata."
                )
            else:
                card.data[key] = value

    return card.push_to_hub(
        repo_id,
        token=token,
        repo_type=repo_type,
        commit_message=commit_message,
        commit_description=commit_description,
        create_pr=create_pr,
        revision=revision,
        parent_commit=parent_commit,
    )

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_resolver.py ===
from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_utils import hasattr_checked, DAPGrouper, Timer
from io import StringIO
import traceback
from os.path import basename

from functools import partial
from _pydevd_bundle.pydevd_constants import (
    IS_PY36_OR_GREATER,
    MethodWrapperType,
    RETURN_VALUES_DICT,
    DebugInfoHolder,
    IS_PYPY,
    GENERATED_LEN_ATTR_NAME,
)
from _pydevd_bundle.pydevd_safe_repr import SafeRepr
from _pydevd_bundle import pydevd_constants

TOO_LARGE_MSG = "Maximum number of items (%s) reached. To show more items customize the value of the PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS environment variable."
TOO_LARGE_ATTR = "Unable to handle:"


# =======================================================================================================================
# UnableToResolveVariableException
# =======================================================================================================================
class UnableToResolveVariableException(Exception):
    pass


try:
    from collections import OrderedDict
except:
    OrderedDict = dict

try:
    import java.lang  # @UnresolvedImport
except:
    pass

# =======================================================================================================================
# See: pydevd_extension_api module for resolver interface
# =======================================================================================================================


def sorted_attributes_key(attr_name):
    if attr_name.startswith("__"):
        if attr_name.endswith("__"):
            # __ double under before and after __
            return (3, attr_name)
        else:
            # __ double under before
            return (2, attr_name)
    elif attr_name.startswith("_"):
        # _ single under
        return (1, attr_name)
    else:
        # Regular (Before anything)
        return (0, attr_name)


# =======================================================================================================================
# DefaultResolver
# =======================================================================================================================
class DefaultResolver:
    """
    DefaultResolver is the class that'll actually resolve how to show some variable.
    """

    def resolve(self, var, attribute):
        return getattr(var, attribute)

    def get_contents_debug_adapter_protocol(self, obj, fmt=None):
        if MethodWrapperType:
            dct, used___dict__ = self._get_py_dictionary(obj)
        else:
            dct = self._get_jy_dictionary(obj)[0]

        lst = sorted(dct.items(), key=lambda tup: sorted_attributes_key(tup[0]))
        if used___dict__:
            eval_name = ".__dict__[%s]"
        else:
            eval_name = ".%s"

        ret = []
        for attr_name, attr_value in lst:
            entry = (attr_name, attr_value, eval_name % attr_name)
            ret.append(entry)

        return ret

    def get_dictionary(self, var, names=None, used___dict__=False):
        if MethodWrapperType:
            return self._get_py_dictionary(var, names, used___dict__=used___dict__)[0]
        else:
            return self._get_jy_dictionary(var)[0]

    def _get_jy_dictionary(self, obj):
        ret = {}
        found = java.util.HashMap()

        original = obj
        if hasattr_checked(obj, "__class__") and obj.__class__ == java.lang.Class:
            # get info about superclasses
            classes = []
            classes.append(obj)
            c = obj.getSuperclass()
            while c != None:
                classes.append(c)
                c = c.getSuperclass()

            # get info about interfaces
            interfs = []
            for obj in classes:
                interfs.extend(obj.getInterfaces())
            classes.extend(interfs)

            # now is the time when we actually get info on the declared methods and fields
            for obj in classes:
                declaredMethods = obj.getDeclaredMethods()
                declaredFields = obj.getDeclaredFields()
                for i in range(len(declaredMethods)):
                    name = declaredMethods[i].getName()
                    ret[name] = declaredMethods[i].toString()
                    found.put(name, 1)

                for i in range(len(declaredFields)):
                    name = declaredFields[i].getName()
                    found.put(name, 1)
                    # if declaredFields[i].isAccessible():
                    declaredFields[i].setAccessible(True)
                    # ret[name] = declaredFields[i].get( declaredFields[i] )
                    try:
                        ret[name] = declaredFields[i].get(original)
                    except:
                        ret[name] = declaredFields[i].toString()

        # this simple dir does not always get all the info, that's why we have the part before
        # (e.g.: if we do a dir on String, some methods that are from other interfaces such as
        # charAt don't appear)
        try:
            d = dir(original)
            for name in d:
                if found.get(name) != 1:
                    ret[name] = getattr(original, name)
        except:
            # sometimes we're unable to do a dir
            pass

        return ret

    def get_names(self, var):
        used___dict__ = False
        try:
            names = dir(var)
        except Exception:
            names = []
        if not names:
            if hasattr_checked(var, "__dict__"):
                names = list(var.__dict__)
                used___dict__ = True
        return names, used___dict__

    def _get_py_dictionary(self, var, names=None, used___dict__=False):
        """
        :return tuple(names, used___dict__), where used___dict__ means we have to access
        using obj.__dict__[name] instead of getattr(obj, name)
        """

        # On PyPy we never show functions. This is because of a corner case where PyPy becomes
        # absurdly slow -- it takes almost half a second to introspect a single numpy function (so,
        # the related test, "test_case_16_resolve_numpy_array", times out... this probably isn't
        # specific to numpy, but to any library where the CPython bridge is used, but as we
        # can't be sure in the debugger, we play it safe and don't show it at all).
        filter_function = IS_PYPY

        if not names:
            names, used___dict__ = self.get_names(var)
        d = {}

        # Be aware that the order in which the filters are applied attempts to
        # optimize the operation by removing as many items as possible in the
        # first filters, leaving fewer items for later filters

        timer = Timer()
        cls = type(var)
        for name in names:
            try:
                name_as_str = name
                if name_as_str.__class__ != str:
                    name_as_str = "%r" % (name_as_str,)

                if not used___dict__:
                    attr = getattr(var, name)
                else:
                    attr = var.__dict__[name]

                # filter functions?
                if filter_function:
                    if inspect.isroutine(attr) or isinstance(attr, MethodWrapperType):
                        continue
            except:
                # if some error occurs getting it, let's put it to the user.
                strIO = StringIO()
                traceback.print_exc(file=strIO)
                attr = strIO.getvalue()

            finally:
                timer.report_if_getting_attr_slow(cls, name_as_str)

            d[name_as_str] = attr

        return d, used___dict__


class DAPGrouperResolver:
    def get_contents_debug_adapter_protocol(self, obj, fmt=None):
        return obj.get_contents_debug_adapter_protocol()


_basic_immutable_types = (int, float, complex, str, bytes, type(None), bool, frozenset)


def _does_obj_repr_evaluate_to_obj(obj):
    """
    If obj is an object where evaluating its representation leads to
    the same object, return True, otherwise, return False.
    """
    try:
        if isinstance(obj, tuple):
            for o in obj:
                if not _does_obj_repr_evaluate_to_obj(o):
                    return False
            return True
        else:
            return isinstance(obj, _basic_immutable_types)
    except:
        return False


# =======================================================================================================================
# DictResolver
# =======================================================================================================================
class DictResolver:
    sort_keys = not IS_PY36_OR_GREATER

    def resolve(self, dct, key):
        if key in (GENERATED_LEN_ATTR_NAME, TOO_LARGE_ATTR):
            return None

        if "(" not in key:
            # we have to treat that because the dict resolver is also used to directly resolve the global and local
            # scopes (which already have the items directly)
            try:
                return dct[key]
            except:
                return getattr(dct, key)

        # ok, we have to iterate over the items to find the one that matches the id, because that's the only way
        # to actually find the reference from the string we have before.
        expected_id = int(key.split("(")[-1][:-1])
        for key, val in dct.items():
            if id(key) == expected_id:
                return val

        raise UnableToResolveVariableException()

    def key_to_str(self, key, fmt=None):
        if fmt is not None:
            if fmt.get("hex", False):
                safe_repr = SafeRepr()
                safe_repr.convert_to_hex = True
                return safe_repr(key)
        return "%r" % (key,)

    def init_dict(self):
        return {}

    def get_contents_debug_adapter_protocol(self, dct, fmt=None):
        """
        This method is to be used in the case where the variables are all saved by its id (and as
        such don't need to have the `resolve` method called later on, so, keys don't need to
        embed the reference in the key).

        Note that the return should be ordered.

        :return list(tuple(name:str, value:object, evaluateName:str))
        """
        ret = []

        i = 0

        found_representations = set()

        for key, val in dct.items():
            i += 1
            key_as_str = self.key_to_str(key, fmt)

            if key_as_str not in found_representations:
                found_representations.add(key_as_str)
            else:
                # If the key would be a duplicate, add the key id (otherwise
                # VSCode won't show all keys correctly).
                # See: https://github.com/microsoft/debugpy/issues/148
                key_as_str = "%s (id: %s)" % (key_as_str, id(key))
                found_representations.add(key_as_str)

            if _does_obj_repr_evaluate_to_obj(key):
                s = self.key_to_str(key)  # do not format the key
                eval_key_str = "[%s]" % (s,)
            else:
                eval_key_str = None
            ret.append((key_as_str, val, eval_key_str))
            if i >= pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS:
                ret.append((TOO_LARGE_ATTR, TOO_LARGE_MSG % (pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS,), None))
                break

        # in case the class extends built-in type and has some additional fields
        from_default_resolver = defaultResolver.get_contents_debug_adapter_protocol(dct, fmt)

        if from_default_resolver:
            ret = from_default_resolver + ret

        if self.sort_keys:
            ret = sorted(ret, key=lambda tup: sorted_attributes_key(tup[0]))

        ret.append((GENERATED_LEN_ATTR_NAME, len(dct), partial(_apply_evaluate_name, evaluate_name="len(%s)")))
        return ret

    def get_dictionary(self, dct):
        ret = self.init_dict()

        i = 0
        for key, val in dct.items():
            i += 1
            # we need to add the id because otherwise we cannot find the real object to get its contents later on.
            key = "%s (%s)" % (self.key_to_str(key), id(key))
            ret[key] = val
            if i >= pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS:
                ret[TOO_LARGE_ATTR] = TOO_LARGE_MSG % (pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS,)
                break

        # in case if the class extends built-in type and has some additional fields
        additional_fields = defaultResolver.get_dictionary(dct)
        ret.update(additional_fields)
        ret[GENERATED_LEN_ATTR_NAME] = len(dct)
        return ret


def _apply_evaluate_name(parent_name, evaluate_name):
    return evaluate_name % (parent_name,)


class MoreItemsRange:
    def __init__(self, value, from_i, to_i):
        self.value = value
        self.from_i = from_i
        self.to_i = to_i

    def get_contents_debug_adapter_protocol(self, _self, fmt=None):
        l = len(self.value)
        ret = []

        format_str = "%0" + str(int(len(str(l - 1)))) + "d"
        if fmt is not None and fmt.get("hex", False):
            format_str = "0x%0" + str(int(len(hex(l).lstrip("0x")))) + "x"

        for i, item in enumerate(self.value[self.from_i : self.to_i]):
            i += self.from_i
            ret.append((format_str % i, item, "[%s]" % i))
        return ret

    def get_dictionary(self, _self, fmt=None):
        dct = {}
        for key, obj, _ in self.get_contents_debug_adapter_protocol(self, fmt):
            dct[key] = obj
        return dct

    def resolve(self, attribute):
        """
        :param var: that's the original object we're dealing with.
        :param attribute: that's the key to resolve
            -- either the dict key in get_dictionary or the name in the dap protocol.
        """
        return self.value[int(attribute)]

    def __eq__(self, o):
        return isinstance(o, MoreItemsRange) and self.value is o.value and self.from_i == o.from_i and self.to_i == o.to_i

    def __str__(self):
        return "[%s:%s]" % (self.from_i, self.to_i)

    __repr__ = __str__


class MoreItems:
    def __init__(self, value, handled_items):
        self.value = value
        self.handled_items = handled_items

    def get_contents_debug_adapter_protocol(self, _self, fmt=None):
        total_items = len(self.value)
        remaining = total_items - self.handled_items
        bucket_size = pydevd_constants.PYDEVD_CONTAINER_BUCKET_SIZE

        from_i = self.handled_items
        to_i = from_i + min(bucket_size, remaining)

        ret = []
        while remaining > 0:
            remaining -= bucket_size
            more_items_range = MoreItemsRange(self.value, from_i, to_i)
            ret.append((str(more_items_range), more_items_range, None))

            from_i = to_i
            to_i = from_i + min(bucket_size, remaining)

        return ret

    def get_dictionary(self, _self, fmt=None):
        dct = {}
        for key, obj, _ in self.get_contents_debug_adapter_protocol(self, fmt):
            dct[key] = obj
        return dct

    def resolve(self, attribute):
        from_i, to_i = attribute[1:-1].split(":")
        from_i = int(from_i)
        to_i = int(to_i)
        return MoreItemsRange(self.value, from_i, to_i)

    def __eq__(self, o):
        return isinstance(o, MoreItems) and self.value is o.value

    def __str__(self):
        return "..."

    __repr__ = __str__


class ForwardInternalResolverToObject:
    """
    To be used when we provide some internal object that'll actually do the resolution.
    """

    def get_contents_debug_adapter_protocol(self, obj, fmt=None):
        return obj.get_contents_debug_adapter_protocol(fmt)

    def get_dictionary(self, var, fmt={}):
        return var.get_dictionary(var, fmt)

    def resolve(self, var, attribute):
        return var.resolve(attribute)


class TupleResolver:  # to enumerate tuples and lists
    def resolve(self, var, attribute):
        """
        :param var: that's the original object we're dealing with.
        :param attribute: that's the key to resolve
            -- either the dict key in get_dictionary or the name in the dap protocol.
        """
        if attribute in (GENERATED_LEN_ATTR_NAME, TOO_LARGE_ATTR):
            return None
        try:
            return var[int(attribute)]
        except:
            if attribute == "more":
                return MoreItems(var, pydevd_constants.PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS)

            return getattr(var, attribute)

    def get_contents_debug_adapter_protocol(self, lst, fmt=None):
        """
        This method is to be used in the case where the variables are all saved by its id (and as
        such don't need to have the `resolve` method called later on, so, keys don't need to
        embed the reference in the key).

        Note that the return should be ordered.

        :return list(tuple(name:str, value:object, evaluateName:str))
        """
        lst_len = len(lst)
        ret = []

        format_str = "%0" + str(int(len(str(lst_len - 1)))) + "d"
        if fmt is not None and fmt.get("hex", False):
            format_str = "0x%0" + str(int(len(hex(lst_len).lstrip("0x")))) + "x"

        initial_expanded = pydevd_constants.PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS
        for i, item in enumerate(lst):
            ret.append((format_str % i, item, "[%s]" % i))

            if i >= initial_expanded - 1:
                if (lst_len - initial_expanded) < pydevd_constants.PYDEVD_CONTAINER_BUCKET_SIZE:
                    # Special case: if we have just 1 more bucket just put it inline.
                    item = MoreItemsRange(lst, initial_expanded, lst_len)

                else:
                    # Multiple buckets
                    item = MoreItems(lst, initial_expanded)
                ret.append(("more", item, None))
                break

        # Needed in case the class extends the built-in type and has some additional fields.
        from_default_resolver = defaultResolver.get_contents_debug_adapter_protocol(lst, fmt=fmt)
        if from_default_resolver:
            ret = from_default_resolver + ret

        ret.append((GENERATED_LEN_ATTR_NAME, len(lst), partial(_apply_evaluate_name, evaluate_name="len(%s)")))
        return ret

    def get_dictionary(self, var, fmt={}):
        l = len(var)
        d = {}

        format_str = "%0" + str(int(len(str(l - 1)))) + "d"
        if fmt is not None and fmt.get("hex", False):
            format_str = "0x%0" + str(int(len(hex(l).lstrip("0x")))) + "x"

        initial_expanded = pydevd_constants.PYDEVD_CONTAINER_INITIAL_EXPANDED_ITEMS
        for i, item in enumerate(var):
            d[format_str % i] = item

            if i >= initial_expanded - 1:
                item = MoreItems(var, initial_expanded)
                d["more"] = item
                break

        # in case if the class extends built-in type and has some additional fields
        additional_fields = defaultResolver.get_dictionary(var)
        d.update(additional_fields)
        d[GENERATED_LEN_ATTR_NAME] = len(var)
        return d


# =======================================================================================================================
# SetResolver
# =======================================================================================================================
class SetResolver:
    """
    Resolves a set as dict id(object)->object
    """

    def get_contents_debug_adapter_protocol(self, obj, fmt=None):
        ret = []

        for i, item in enumerate(obj):
            ret.append((str(id(item)), item, None))

            if i >= pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS:
                ret.append((TOO_LARGE_ATTR, TOO_LARGE_MSG % (pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS,), None))
                break

        # Needed in case the class extends the built-in type and has some additional fields.
        from_default_resolver = defaultResolver.get_contents_debug_adapter_protocol(obj, fmt=fmt)
        if from_default_resolver:
            ret = from_default_resolver + ret
        ret.append((GENERATED_LEN_ATTR_NAME, len(obj), partial(_apply_evaluate_name, evaluate_name="len(%s)")))
        return ret

    def resolve(self, var, attribute):
        if attribute in (GENERATED_LEN_ATTR_NAME, TOO_LARGE_ATTR):
            return None

        try:
            attribute = int(attribute)
        except:
            return getattr(var, attribute)

        for v in var:
            if id(v) == attribute:
                return v

        raise UnableToResolveVariableException("Unable to resolve %s in %s" % (attribute, var))

    def get_dictionary(self, var):
        d = {}
        for i, item in enumerate(var):
            d[str(id(item))] = item

            if i >= pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS:
                d[TOO_LARGE_ATTR] = TOO_LARGE_MSG % (pydevd_constants.PYDEVD_CONTAINER_RANDOM_ACCESS_MAX_ITEMS,)
                break

        # in case if the class extends built-in type and has some additional fields
        additional_fields = defaultResolver.get_dictionary(var)
        d.update(additional_fields)
        d[GENERATED_LEN_ATTR_NAME] = len(var)
        return d

    def change_var_from_name(self, container, name, new_value):
        # The name given in this case must be the id(item), so, we can actually
        # iterate in the set and see which item matches the given id.

        try:
            # Check that the new value can actually be added to a set (i.e.: it's hashable/comparable).
            set().add(new_value)
        except:
            return None

        for item in container:
            if str(id(item)) == name:
                container.remove(item)
                container.add(new_value)
                return str(id(new_value))

        return None


# =======================================================================================================================
# InstanceResolver
# =======================================================================================================================
class InstanceResolver:
    def resolve(self, var, attribute):
        field = var.__class__.getDeclaredField(attribute)
        field.setAccessible(True)
        return field.get(var)

    def get_dictionary(self, obj):
        ret = {}

        declaredFields = obj.__class__.getDeclaredFields()
        for i in range(len(declaredFields)):
            name = declaredFields[i].getName()
            try:
                declaredFields[i].setAccessible(True)
                ret[name] = declaredFields[i].get(obj)
            except:
                pydev_log.exception()

        return ret


# =======================================================================================================================
# JyArrayResolver
# =======================================================================================================================
class JyArrayResolver:
    """
    This resolves a regular Object[] array from java
    """

    def resolve(self, var, attribute):
        if attribute == GENERATED_LEN_ATTR_NAME:
            return None
        return var[int(attribute)]

    def get_dictionary(self, obj):
        ret = {}

        for i in range(len(obj)):
            ret[i] = obj[i]

        ret[GENERATED_LEN_ATTR_NAME] = len(obj)
        return ret


# =======================================================================================================================
# MultiValueDictResolver
# =======================================================================================================================
class MultiValueDictResolver(DictResolver):
    def resolve(self, dct, key):
        if key in (GENERATED_LEN_ATTR_NAME, TOO_LARGE_ATTR):
            return None

        # ok, we have to iterate over the items to find the one that matches the id, because that's the only way
        # to actually find the reference from the string we have before.
        expected_id = int(key.split("(")[-1][:-1])
        for key in list(dct.keys()):
            val = dct.getlist(key)
            if id(key) == expected_id:
                return val

        raise UnableToResolveVariableException()


# =======================================================================================================================
# DjangoFormResolver
# =======================================================================================================================
class DjangoFormResolver(DefaultResolver):
    def get_dictionary(self, var, names=None):
        # Do not call self.errors because it is a property and has side effects.
        names, used___dict__ = self.get_names(var)

        has_errors_attr = False
        if "errors" in names:
            has_errors_attr = True
            names.remove("errors")

        d = defaultResolver.get_dictionary(var, names=names, used___dict__=used___dict__)
        if has_errors_attr:
            try:
                errors_attr = getattr(var, "_errors")
            except:
                errors_attr = None
            d["errors"] = errors_attr
        return d


# =======================================================================================================================
# DequeResolver
# =======================================================================================================================
class DequeResolver(TupleResolver):
    def get_dictionary(self, var):
        d = TupleResolver.get_dictionary(self, var)
        d["maxlen"] = getattr(var, "maxlen", None)
        return d


# =======================================================================================================================
# OrderedDictResolver
# =======================================================================================================================
class OrderedDictResolver(DictResolver):
    sort_keys = False

    def init_dict(self):
        return OrderedDict()


# =======================================================================================================================
# FrameResolver
# =======================================================================================================================
class FrameResolver:
    """
    This resolves a frame.
    """

    def resolve(self, obj, attribute):
        if attribute == "__internals__":
            return defaultResolver.get_dictionary(obj)

        if attribute == "stack":
            return self.get_frame_stack(obj)

        if attribute == "f_locals":
            return obj.f_locals

        return None

    def get_dictionary(self, obj):
        ret = {}
        ret["__internals__"] = defaultResolver.get_dictionary(obj)
        ret["stack"] = self.get_frame_stack(obj)
        ret["f_locals"] = obj.f_locals
        return ret

    def get_frame_stack(self, frame):
        ret = []
        if frame is not None:
            ret.append(self.get_frame_name(frame))

            while frame.f_back:
                frame = frame.f_back
                ret.append(self.get_frame_name(frame))

        return ret

    def get_frame_name(self, frame):
        if frame is None:
            return "None"
        try:
            name = basename(frame.f_code.co_filename)
            return "frame: %s [%s:%s]  id:%s" % (frame.f_code.co_name, name, frame.f_lineno, id(frame))
        except:
            return "frame object"


defaultResolver = DefaultResolver()
dictResolver = DictResolver()
tupleResolver = TupleResolver()
instanceResolver = InstanceResolver()
jyArrayResolver = JyArrayResolver()
setResolver = SetResolver()
multiValueDictResolver = MultiValueDictResolver()
djangoFormResolver = DjangoFormResolver()
dequeResolver = DequeResolver()
orderedDictResolver = OrderedDictResolver()
frameResolver = FrameResolver()
dapGrouperResolver = DAPGrouperResolver()
forwardInternalResolverToObject = ForwardInternalResolverToObject()


class InspectStub:
    def isbuiltin(self, _args):
        return False

    def isroutine(self, object):
        return False


try:
    import inspect
except:
    inspect = InspectStub()


def get_var_scope(attr_name, attr_value, evaluate_name, handle_return_values):
    if attr_name.startswith("'"):
        if attr_name.endswith("'"):
            # i.e.: strings denote that it is a regular value in some container.
            return ""
        else:
            i = attr_name.find("__' (")
            if i >= 0:
                # Handle attr_name such as: >>'__name__' (1732494379184)<<
                attr_name = attr_name[1 : i + 2]

    if handle_return_values and attr_name == RETURN_VALUES_DICT:
        return ""

    elif attr_name == GENERATED_LEN_ATTR_NAME:
        return ""

    if attr_name.startswith("__") and attr_name.endswith("__"):
        return DAPGrouper.SCOPE_SPECIAL_VARS

    if attr_name.startswith("_") or attr_name.endswith("__"):
        return DAPGrouper.SCOPE_PROTECTED_VARS

    try:
        if inspect.isroutine(attr_value) or isinstance(attr_value, MethodWrapperType):
            return DAPGrouper.SCOPE_FUNCTION_VARS

        elif inspect.isclass(attr_value):
            return DAPGrouper.SCOPE_CLASS_VARS
    except:
        # It's possible that isinstance throws an exception when dealing with user-code.
        if DebugInfoHolder.DEBUG_TRACE_LEVEL > 0:
            pydev_log.exception()

    return ""

# === NexusCore/openenv\Lib\site-packages\nltk\sem\evaluate.py ===
# Natural Language Toolkit: Models for first-order languages with lambda
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

# TODO:
# - fix tracing
# - fix iterator-based approach to existentials

"""
This module provides data structures for representing first-order
models.
"""

import inspect
import re
import sys
import textwrap
from pprint import pformat

from nltk.decorators import decorator  # this used in code that is commented out
from nltk.sem.logic import (
    AbstractVariableExpression,
    AllExpression,
    AndExpression,
    ApplicationExpression,
    EqualityExpression,
    ExistsExpression,
    Expression,
    IffExpression,
    ImpExpression,
    IndividualVariableExpression,
    IotaExpression,
    LambdaExpression,
    NegatedExpression,
    OrExpression,
    Variable,
    is_indvar,
)


class Error(Exception):
    pass


class Undefined(Error):
    pass


def trace(f, *args, **kw):
    argspec = inspect.getfullargspec(f)
    d = dict(zip(argspec[0], args))
    if d.pop("trace", None):
        print()
        for item in d.items():
            print("%s => %s" % item)
    return f(*args, **kw)


def is_rel(s):
    """
    Check whether a set represents a relation (of any arity).

    :param s: a set containing tuples of str elements
    :type s: set
    :rtype: bool
    """
    # we have the empty relation, i.e. set()
    if len(s) == 0:
        return True
    # all the elements are tuples of the same length
    elif all(isinstance(el, tuple) for el in s) and len(max(s)) == len(min(s)):
        return True
    else:
        raise ValueError("Set %r contains sequences of different lengths" % s)


def set2rel(s):
    """
    Convert a set containing individuals (strings or numbers) into a set of
    unary tuples. Any tuples of strings already in the set are passed through
    unchanged.

    For example:
      - set(['a', 'b']) => set([('a',), ('b',)])
      - set([3, 27]) => set([('3',), ('27',)])

    :type s: set
    :rtype: set of tuple of str
    """
    new = set()
    for elem in s:
        if isinstance(elem, str):
            new.add((elem,))
        elif isinstance(elem, int):
            new.add(str(elem))
        else:
            new.add(elem)
    return new


def arity(rel):
    """
    Check the arity of a relation.
    :type rel: set of tuples
    :rtype: int of tuple of str
    """
    if len(rel) == 0:
        return 0
    return len(list(rel)[0])


class Valuation(dict):
    """
    A dictionary which represents a model-theoretic Valuation of non-logical constants.
    Keys are strings representing the constants to be interpreted, and values correspond
    to individuals (represented as strings) and n-ary relations (represented as sets of tuples
    of strings).

    An instance of ``Valuation`` will raise a KeyError exception (i.e.,
    just behave like a standard  dictionary) if indexed with an expression that
    is not in its list of symbols.
    """

    def __init__(self, xs):
        """
        :param xs: a list of (symbol, value) pairs.
        """
        super().__init__()
        for sym, val in xs:
            if isinstance(val, str) or isinstance(val, bool):
                self[sym] = val
            elif isinstance(val, set):
                self[sym] = set2rel(val)
            else:
                msg = textwrap.fill(
                    "Error in initializing Valuation. "
                    "Unrecognized value for symbol '%s':\n%s" % (sym, val),
                    width=66,
                )

                raise ValueError(msg)

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined("Unknown expression: '%s'" % key)

    def __str__(self):
        return pformat(self)

    @property
    def domain(self):
        """Set-theoretic domain of the value-space of a Valuation."""
        dom = []
        for val in self.values():
            if isinstance(val, str):
                dom.append(val)
            elif not isinstance(val, bool):
                dom.extend(
                    [elem for tuple_ in val for elem in tuple_ if elem is not None]
                )
        return set(dom)

    @property
    def symbols(self):
        """The non-logical constants which the Valuation recognizes."""
        return sorted(self.keys())

    @classmethod
    def fromstring(cls, s):
        return read_valuation(s)


##########################################
# REs used by the _read_valuation function
##########################################
_VAL_SPLIT_RE = re.compile(r"\s*=+>\s*")
_ELEMENT_SPLIT_RE = re.compile(r"\s*,\s*")
_TUPLES_RE = re.compile(
    r"""\s*
                                (\([^)]+\))  # tuple-expression
                                \s*""",
    re.VERBOSE,
)


def _read_valuation_line(s):
    """
    Read a line in a valuation file.

    Lines are expected to be of the form::

      noosa => n
      girl => {g1, g2}
      chase => {(b1, g1), (b2, g1), (g1, d1), (g2, d2)}

    :param s: input line
    :type s: str
    :return: a pair (symbol, value)
    :rtype: tuple
    """
    pieces = _VAL_SPLIT_RE.split(s)
    symbol = pieces[0]
    value = pieces[1]
    # check whether the value is meant to be a set
    if value.startswith("{"):
        value = value[1:-1]
        tuple_strings = _TUPLES_RE.findall(value)
        # are the set elements tuples?
        if tuple_strings:
            set_elements = []
            for ts in tuple_strings:
                ts = ts[1:-1]
                element = tuple(_ELEMENT_SPLIT_RE.split(ts))
                set_elements.append(element)
        else:
            set_elements = _ELEMENT_SPLIT_RE.split(value)
        value = set(set_elements)
    return symbol, value


def read_valuation(s, encoding=None):
    """
    Convert a valuation string into a valuation.

    :param s: a valuation string
    :type s: str
    :param encoding: the encoding of the input string, if it is binary
    :type encoding: str
    :return: a ``nltk.sem`` valuation
    :rtype: Valuation
    """
    if encoding is not None:
        s = s.decode(encoding)
    statements = []
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        try:
            statements.append(_read_valuation_line(line))
        except ValueError as e:
            raise ValueError(f"Unable to parse line {linenum}: {line}") from e
    return Valuation(statements)


class Assignment(dict):
    r"""
    A dictionary which represents an assignment of values to variables.

    An assignment can only assign values from its domain.

    If an unknown expression *a* is passed to a model *M*\ 's
    interpretation function *i*, *i* will first check whether *M*\ 's
    valuation assigns an interpretation to *a* as a constant, and if
    this fails, *i* will delegate the interpretation of *a* to
    *g*. *g* only assigns values to individual variables (i.e.,
    members of the class ``IndividualVariableExpression`` in the ``logic``
    module. If a variable is not assigned a value by *g*, it will raise
    an ``Undefined`` exception.

    A variable *Assignment* is a mapping from individual variables to
    entities in the domain. Individual variables are usually indicated
    with the letters ``'x'``, ``'y'``, ``'w'`` and ``'z'``, optionally
    followed by an integer (e.g., ``'x0'``, ``'y332'``).  Assignments are
    created using the ``Assignment`` constructor, which also takes the
    domain as a parameter.

        >>> from nltk.sem.evaluate import Assignment
        >>> dom = set(['u1', 'u2', 'u3', 'u4'])
        >>> g3 = Assignment(dom, [('x', 'u1'), ('y', 'u2')])
        >>> g3 == {'x': 'u1', 'y': 'u2'}
        True

    There is also a ``print`` format for assignments which uses a notation
    closer to that in logic textbooks:

        >>> print(g3)
        g[u1/x][u2/y]

    It is also possible to update an assignment using the ``add`` method:

        >>> dom = set(['u1', 'u2', 'u3', 'u4'])
        >>> g4 = Assignment(dom)
        >>> g4.add('x', 'u1')
        {'x': 'u1'}

    With no arguments, ``purge()`` is equivalent to ``clear()`` on a dictionary:

        >>> g4.purge()
        >>> g4
        {}

    :param domain: the domain of discourse
    :type domain: set
    :param assign: a list of (varname, value) associations
    :type assign: list
    """

    def __init__(self, domain, assign=None):
        super().__init__()
        self.domain = domain
        if assign:
            for var, val in assign:
                assert val in self.domain, "'{}' is not in the domain: {}".format(
                    val,
                    self.domain,
                )
                assert is_indvar(var), (
                    "Wrong format for an Individual Variable: '%s'" % var
                )
                self[var] = val
        self.variant = None
        self._addvariant()

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            raise Undefined("Not recognized as a variable: '%s'" % key)

    def copy(self):
        new = Assignment(self.domain)
        new.update(self)
        return new

    def purge(self, var=None):
        """
        Remove one or all keys (i.e. logic variables) from an
        assignment, and update ``self.variant``.

        :param var: a Variable acting as a key for the assignment.
        """
        if var:
            del self[var]
        else:
            self.clear()
        self._addvariant()
        return None

    def __str__(self):
        """
        Pretty printing for assignments. {'x', 'u'} appears as 'g[u/x]'
        """
        gstring = "g"
        # Deterministic output for unit testing.
        variant = sorted(self.variant)
        for val, var in variant:
            gstring += f"[{val}/{var}]"
        return gstring

    def _addvariant(self):
        """
        Create a more pretty-printable version of the assignment.
        """
        list_ = []
        for item in self.items():
            pair = (item[1], item[0])
            list_.append(pair)
        self.variant = list_
        return None

    def add(self, var, val):
        """
        Add a new variable-value pair to the assignment, and update
        ``self.variant``.

        """
        assert val in self.domain, f"{val} is not in the domain {self.domain}"
        assert is_indvar(var), "Wrong format for an Individual Variable: '%s'" % var
        self[var] = val
        self._addvariant()
        return self


class Model:
    """
    A first order model is a domain *D* of discourse and a valuation *V*.

    A domain *D* is a set, and a valuation *V* is a map that associates
    expressions with values in the model.
    The domain of *V* should be a subset of *D*.

    Construct a new ``Model``.

    :type domain: set
    :param domain: A set of entities representing the domain of discourse of the model.
    :type valuation: Valuation
    :param valuation: the valuation of the model.
    :param prop: If this is set, then we are building a propositional\
    model and don't require the domain of *V* to be subset of *D*.
    """

    def __init__(self, domain, valuation):
        assert isinstance(domain, set)
        self.domain = domain
        self.valuation = valuation
        if not domain.issuperset(valuation.domain):
            raise Error(
                "The valuation domain, %s, must be a subset of the model's domain, %s"
                % (valuation.domain, domain)
            )

    def __repr__(self):
        return f"({self.domain!r}, {self.valuation!r})"

    def __str__(self):
        return f"Domain = {self.domain},\nValuation = \n{self.valuation}"

    def evaluate(self, expr, g, trace=None):
        """
        Read input expressions, and provide a handler for ``satisfy``
        that blocks further propagation of the ``Undefined`` error.
        :param expr: An ``Expression`` of ``logic``.
        :type g: Assignment
        :param g: an assignment to individual variables.
        :rtype: bool or 'Undefined'
        """
        try:
            parsed = Expression.fromstring(expr)
            value = self.satisfy(parsed, g, trace=trace)
            if trace:
                print()
                print(f"'{expr}' evaluates to {value} under M, {g}")
            return value
        except Undefined:
            if trace:
                print()
                print(f"'{expr}' is undefined under M, {g}")
            return "Undefined"

    def satisfy(self, parsed, g, trace=None):
        """
        Recursive interpretation function for a formula of first-order logic.

        Raises an ``Undefined`` error when ``parsed`` is an atomic string
        but is not a symbol or an individual variable.

        :return: Returns a truth value or ``Undefined`` if ``parsed`` is\
        complex, and calls the interpretation function ``i`` if ``parsed``\
        is atomic.

        :param parsed: An expression of ``logic``.
        :type g: Assignment
        :param g: an assignment to individual variables.
        """

        if isinstance(parsed, ApplicationExpression):
            function, arguments = parsed.uncurry()
            if isinstance(function, AbstractVariableExpression):
                # It's a predicate expression ("P(x,y)"), so used uncurried arguments
                funval = self.satisfy(function, g)
                argvals = tuple(self.satisfy(arg, g) for arg in arguments)
                return argvals in funval
            else:
                # It must be a lambda expression, so use curried form
                funval = self.satisfy(parsed.function, g)
                argval = self.satisfy(parsed.argument, g)
                return funval[argval]
        elif isinstance(parsed, NegatedExpression):
            return not self.satisfy(parsed.term, g)
        elif isinstance(parsed, AndExpression):
            return self.satisfy(parsed.first, g) and self.satisfy(parsed.second, g)
        elif isinstance(parsed, OrExpression):
            return self.satisfy(parsed.first, g) or self.satisfy(parsed.second, g)
        elif isinstance(parsed, ImpExpression):
            return (not self.satisfy(parsed.first, g)) or self.satisfy(parsed.second, g)
        elif isinstance(parsed, IffExpression):
            return self.satisfy(parsed.first, g) == self.satisfy(parsed.second, g)
        elif isinstance(parsed, EqualityExpression):
            return self.satisfy(parsed.first, g) == self.satisfy(parsed.second, g)
        elif isinstance(parsed, AllExpression):
            new_g = g.copy()
            for u in self.domain:
                new_g.add(parsed.variable.name, u)
                if not self.satisfy(parsed.term, new_g):
                    return False
            return True
        elif isinstance(parsed, ExistsExpression):
            new_g = g.copy()
            for u in self.domain:
                new_g.add(parsed.variable.name, u)
                if self.satisfy(parsed.term, new_g):
                    return True
            return False
        elif isinstance(parsed, IotaExpression):
            new_g = g.copy()
            for u in self.domain:
                new_g.add(parsed.variable.name, u)
                if self.satisfy(parsed.term, new_g):
                    return True
            return False
        elif isinstance(parsed, LambdaExpression):
            cf = {}
            var = parsed.variable.name
            for u in self.domain:
                val = self.satisfy(parsed.term, g.add(var, u))
                # NB the dict would be a lot smaller if we do this:
                # if val: cf[u] = val
                # But then need to deal with cases where f(a) should yield
                # a function rather than just False.
                cf[u] = val
            return cf
        else:
            return self.i(parsed, g, trace)

    # @decorator(trace_eval)
    def i(self, parsed, g, trace=False):
        """
        An interpretation function.

        Assuming that ``parsed`` is atomic:

        - if ``parsed`` is a non-logical constant, calls the valuation *V*
        - else if ``parsed`` is an individual variable, calls assignment *g*
        - else returns ``Undefined``.

        :param parsed: an ``Expression`` of ``logic``.
        :type g: Assignment
        :param g: an assignment to individual variables.
        :return: a semantic value
        """
        # If parsed is a propositional letter 'p', 'q', etc, it could be in valuation.symbols
        # and also be an IndividualVariableExpression. We want to catch this first case.
        # So there is a procedural consequence to the ordering of clauses here:
        if parsed.variable.name in self.valuation.symbols:
            return self.valuation[parsed.variable.name]
        elif isinstance(parsed, IndividualVariableExpression):
            return g[parsed.variable.name]

        else:
            raise Undefined("Can't find a value for %s" % parsed)

    def satisfiers(self, parsed, varex, g, trace=None, nesting=0):
        """
        Generate the entities from the model's domain that satisfy an open formula.

        :param parsed: an open formula
        :type parsed: Expression
        :param varex: the relevant free individual variable in ``parsed``.
        :type varex: VariableExpression or str
        :param g: a variable assignment
        :type g:  Assignment
        :return: a set of the entities that satisfy ``parsed``.
        """

        spacer = "   "
        indent = spacer + (spacer * nesting)
        candidates = []

        if isinstance(varex, str):
            var = Variable(varex)
        else:
            var = varex

        if var in parsed.free():
            if trace:
                print()
                print(
                    (spacer * nesting)
                    + f"Open formula is '{parsed}' with assignment {g}"
                )
            for u in self.domain:
                new_g = g.copy()
                new_g.add(var.name, u)
                if trace and trace > 1:
                    lowtrace = trace - 1
                else:
                    lowtrace = 0
                value = self.satisfy(parsed, new_g, lowtrace)

                if trace:
                    print(indent + "(trying assignment %s)" % new_g)

                # parsed == False under g[u/var]?
                if value == False:
                    if trace:
                        print(indent + f"value of '{parsed}' under {new_g} is False")

                # so g[u/var] is a satisfying assignment
                else:
                    candidates.append(u)
                    if trace:
                        print(indent + f"value of '{parsed}' under {new_g} is {value}")

            result = {c for c in candidates}
        # var isn't free in parsed
        else:
            raise Undefined(f"{var.name} is not free in {parsed}")

        return result


# //////////////////////////////////////////////////////////////////////
# Demo..
# //////////////////////////////////////////////////////////////////////
# number of spacer chars
mult = 30


# Demo 1: Propositional Logic
#################
def propdemo(trace=None):
    """Example of a propositional model."""

    global val1, dom1, m1, g1
    val1 = Valuation([("P", True), ("Q", True), ("R", False)])
    dom1 = set()
    m1 = Model(dom1, val1)
    g1 = Assignment(dom1)

    print()
    print("*" * mult)
    print("Propositional Formulas Demo")
    print("*" * mult)
    print("(Propositional constants treated as nullary predicates)")
    print()
    print("Model m1:\n", m1)
    print("*" * mult)
    sentences = [
        "(P & Q)",
        "(P & R)",
        "- P",
        "- R",
        "- - P",
        "- (P & R)",
        "(P | R)",
        "(R | P)",
        "(R | R)",
        "(- P | R)",
        "(P | - P)",
        "(P -> Q)",
        "(P -> R)",
        "(R -> P)",
        "(P <-> P)",
        "(R <-> R)",
        "(P <-> R)",
    ]

    for sent in sentences:
        if trace:
            print()
            m1.evaluate(sent, g1, trace)
        else:
            print(f"The value of '{sent}' is: {m1.evaluate(sent, g1)}")


# Demo 2: FOL Model
#############


def folmodel(quiet=False, trace=None):
    """Example of a first-order model."""

    global val2, v2, dom2, m2, g2

    v2 = [
        ("adam", "b1"),
        ("betty", "g1"),
        ("fido", "d1"),
        ("girl", {"g1", "g2"}),
        ("boy", {"b1", "b2"}),
        ("dog", {"d1"}),
        ("love", {("b1", "g1"), ("b2", "g2"), ("g1", "b1"), ("g2", "b1")}),
    ]
    val2 = Valuation(v2)
    dom2 = val2.domain
    m2 = Model(dom2, val2)
    g2 = Assignment(dom2, [("x", "b1"), ("y", "g2")])

    if not quiet:
        print()
        print("*" * mult)
        print("Models Demo")
        print("*" * mult)
        print("Model m2:\n", "-" * 14, "\n", m2)
        print("Variable assignment = ", g2)

        exprs = ["adam", "boy", "love", "walks", "x", "y", "z"]
        parsed_exprs = [Expression.fromstring(e) for e in exprs]

        print()
        for parsed in parsed_exprs:
            try:
                print(
                    "The interpretation of '%s' in m2 is %s"
                    % (parsed, m2.i(parsed, g2))
                )
            except Undefined:
                print("The interpretation of '%s' in m2 is Undefined" % parsed)

        applications = [
            ("boy", ("adam")),
            ("walks", ("adam",)),
            ("love", ("adam", "y")),
            ("love", ("y", "adam")),
        ]

        for fun, args in applications:
            try:
                funval = m2.i(Expression.fromstring(fun), g2)
                argsval = tuple(m2.i(Expression.fromstring(arg), g2) for arg in args)
                print(f"{fun}({args}) evaluates to {argsval in funval}")
            except Undefined:
                print(f"{fun}({args}) evaluates to Undefined")


# Demo 3: FOL
#########


def foldemo(trace=None):
    """
    Interpretation of closed expressions in a first-order model.
    """
    folmodel(quiet=True)

    print()
    print("*" * mult)
    print("FOL Formulas Demo")
    print("*" * mult)

    formulas = [
        "love (adam, betty)",
        "(adam = mia)",
        "\\x. (boy(x) | girl(x))",
        "\\x. boy(x)(adam)",
        "\\x y. love(x, y)",
        "\\x y. love(x, y)(adam)(betty)",
        "\\x y. love(x, y)(adam, betty)",
        "\\x y. (boy(x) & love(x, y))",
        "\\x. exists y. (boy(x) & love(x, y))",
        "exists z1. boy(z1)",
        "exists x. (boy(x) &  -(x = adam))",
        "exists x. (boy(x) & all y. love(y, x))",
        "all x. (boy(x) | girl(x))",
        "all x. (girl(x) -> exists y. boy(y) & love(x, y))",  # Every girl loves exists boy.
        "exists x. (boy(x) & all y. (girl(y) -> love(y, x)))",  # There is exists boy that every girl loves.
        "exists x. (boy(x) & all y. (girl(y) -> love(x, y)))",  # exists boy loves every girl.
        "all x. (dog(x) -> - girl(x))",
        "exists x. exists y. (love(x, y) & love(x, y))",
    ]

    for fmla in formulas:
        g2.purge()
        if trace:
            m2.evaluate(fmla, g2, trace)
        else:
            print(f"The value of '{fmla}' is: {m2.evaluate(fmla, g2)}")


# Demo 3: Satisfaction
#############


def satdemo(trace=None):
    """Satisfiers of an open formula in a first order model."""

    print()
    print("*" * mult)
    print("Satisfiers Demo")
    print("*" * mult)

    folmodel(quiet=True)

    formulas = [
        "boy(x)",
        "(x = x)",
        "(boy(x) | girl(x))",
        "(boy(x) & girl(x))",
        "love(adam, x)",
        "love(x, adam)",
        "-(x = adam)",
        "exists z22. love(x, z22)",
        "exists y. love(y, x)",
        "all y. (girl(y) -> love(x, y))",
        "all y. (girl(y) -> love(y, x))",
        "all y. (girl(y) -> (boy(x) & love(y, x)))",
        "(boy(x) & all y. (girl(y) -> love(x, y)))",
        "(boy(x) & all y. (girl(y) -> love(y, x)))",
        "(boy(x) & exists y. (girl(y) & love(y, x)))",
        "(girl(x) -> dog(x))",
        "all y. (dog(y) -> (x = y))",
        "exists y. love(y, x)",
        "exists y. (love(adam, y) & love(y, x))",
    ]

    if trace:
        print(m2)

    for fmla in formulas:
        print(fmla)
        Expression.fromstring(fmla)

    parsed = [Expression.fromstring(fmla) for fmla in formulas]

    for p in parsed:
        g2.purge()
        print(
            "The satisfiers of '{}' are: {}".format(p, m2.satisfiers(p, "x", g2, trace))
        )


def demo(num=0, trace=None):
    """
    Run exists demos.

     - num = 1: propositional logic demo
     - num = 2: first order model demo (only if trace is set)
     - num = 3: first order sentences demo
     - num = 4: satisfaction of open formulas demo
     - any other value: run all the demos

    :param trace: trace = 1, or trace = 2 for more verbose tracing
    """
    demos = {1: propdemo, 2: folmodel, 3: foldemo, 4: satdemo}

    try:
        demos[num](trace=trace)
    except KeyError:
        for num in demos:
            demos[num](trace=trace)


if __name__ == "__main__":
    demo(2, trace=0)

# === NexusCore/openenv\Lib\site-packages\pydantic\functional_validators.py ===
"""This module contains related classes and functions for validation."""

from __future__ import annotations as _annotations

import dataclasses
import sys
from functools import partialmethod
from types import FunctionType
from typing import TYPE_CHECKING, Annotated, Any, Callable, Literal, TypeVar, Union, cast, overload

from pydantic_core import PydanticUndefined, core_schema
from pydantic_core import core_schema as _core_schema
from typing_extensions import Self, TypeAlias

from ._internal import _decorators, _generics, _internal_dataclass
from .annotated_handlers import GetCoreSchemaHandler
from .errors import PydanticUserError

if sys.version_info < (3, 11):
    from typing_extensions import Protocol
else:
    from typing import Protocol

_inspect_validator = _decorators.inspect_validator


@dataclasses.dataclass(frozen=True, **_internal_dataclass.slots_true)
class AfterValidator:
    """!!! abstract "Usage Documentation"
        [field *after* validators](../concepts/validators.md#field-after-validator)

    A metadata class that indicates that a validation should be applied **after** the inner validation logic.

    Attributes:
        func: The validator function.

    Example:
        ```python
        from typing import Annotated

        from pydantic import AfterValidator, BaseModel, ValidationError

        MyInt = Annotated[int, AfterValidator(lambda v: v + 1)]

        class Model(BaseModel):
            a: MyInt

        print(Model(a=1).a)
        #> 2

        try:
            Model(a='a')
        except ValidationError as e:
            print(e.json(indent=2))
            '''
            [
              {
                "type": "int_parsing",
                "loc": [
                  "a"
                ],
                "msg": "Input should be a valid integer, unable to parse string as an integer",
                "input": "a",
                "url": "https://errors.pydantic.dev/2/v/int_parsing"
              }
            ]
            '''
        ```
    """

    func: core_schema.NoInfoValidatorFunction | core_schema.WithInfoValidatorFunction

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source_type)
        info_arg = _inspect_validator(self.func, 'after')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_after_validator_function(func, schema=schema, field_name=handler.field_name)
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_after_validator_function(func, schema=schema)

    @classmethod
    def _from_decorator(cls, decorator: _decorators.Decorator[_decorators.FieldValidatorDecoratorInfo]) -> Self:
        return cls(func=decorator.func)


@dataclasses.dataclass(frozen=True, **_internal_dataclass.slots_true)
class BeforeValidator:
    """!!! abstract "Usage Documentation"
        [field *before* validators](../concepts/validators.md#field-before-validator)

    A metadata class that indicates that a validation should be applied **before** the inner validation logic.

    Attributes:
        func: The validator function.
        json_schema_input_type: The input type of the function. This is only used to generate the appropriate
            JSON Schema (in validation mode).

    Example:
        ```python
        from typing import Annotated

        from pydantic import BaseModel, BeforeValidator

        MyInt = Annotated[int, BeforeValidator(lambda v: v + 1)]

        class Model(BaseModel):
            a: MyInt

        print(Model(a=1).a)
        #> 2

        try:
            Model(a='a')
        except TypeError as e:
            print(e)
            #> can only concatenate str (not "int") to str
        ```
    """

    func: core_schema.NoInfoValidatorFunction | core_schema.WithInfoValidatorFunction
    json_schema_input_type: Any = PydanticUndefined

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source_type)
        input_schema = (
            None
            if self.json_schema_input_type is PydanticUndefined
            else handler.generate_schema(self.json_schema_input_type)
        )

        info_arg = _inspect_validator(self.func, 'before')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_before_validator_function(
                func,
                schema=schema,
                field_name=handler.field_name,
                json_schema_input_schema=input_schema,
            )
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_before_validator_function(
                func, schema=schema, json_schema_input_schema=input_schema
            )

    @classmethod
    def _from_decorator(cls, decorator: _decorators.Decorator[_decorators.FieldValidatorDecoratorInfo]) -> Self:
        return cls(
            func=decorator.func,
            json_schema_input_type=decorator.info.json_schema_input_type,
        )


@dataclasses.dataclass(frozen=True, **_internal_dataclass.slots_true)
class PlainValidator:
    """!!! abstract "Usage Documentation"
        [field *plain* validators](../concepts/validators.md#field-plain-validator)

    A metadata class that indicates that a validation should be applied **instead** of the inner validation logic.

    !!! note
        Before v2.9, `PlainValidator` wasn't always compatible with JSON Schema generation for `mode='validation'`.
        You can now use the `json_schema_input_type` argument to specify the input type of the function
        to be used in the JSON schema when `mode='validation'` (the default). See the example below for more details.

    Attributes:
        func: The validator function.
        json_schema_input_type: The input type of the function. This is only used to generate the appropriate
            JSON Schema (in validation mode). If not provided, will default to `Any`.

    Example:
        ```python
        from typing import Annotated, Union

        from pydantic import BaseModel, PlainValidator

        MyInt = Annotated[
            int,
            PlainValidator(
                lambda v: int(v) + 1, json_schema_input_type=Union[str, int]  # (1)!
            ),
        ]

        class Model(BaseModel):
            a: MyInt

        print(Model(a='1').a)
        #> 2

        print(Model(a=1).a)
        #> 2
        ```

        1. In this example, we've specified the `json_schema_input_type` as `Union[str, int]` which indicates to the JSON schema
        generator that in validation mode, the input type for the `a` field can be either a `str` or an `int`.
    """

    func: core_schema.NoInfoValidatorFunction | core_schema.WithInfoValidatorFunction
    json_schema_input_type: Any = Any

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Note that for some valid uses of PlainValidator, it is not possible to generate a core schema for the
        # source_type, so calling `handler(source_type)` will error, which prevents us from generating a proper
        # serialization schema. To work around this for use cases that will not involve serialization, we simply
        # catch any PydanticSchemaGenerationError that may be raised while attempting to build the serialization schema
        # and abort any attempts to handle special serialization.
        from pydantic import PydanticSchemaGenerationError

        try:
            schema = handler(source_type)
            # TODO if `schema['serialization']` is one of `'include-exclude-dict/sequence',
            # schema validation will fail. That's why we use 'type ignore' comments below.
            serialization = schema.get(
                'serialization',
                core_schema.wrap_serializer_function_ser_schema(
                    function=lambda v, h: h(v),
                    schema=schema,
                    return_schema=handler.generate_schema(source_type),
                ),
            )
        except PydanticSchemaGenerationError:
            serialization = None

        input_schema = handler.generate_schema(self.json_schema_input_type)

        info_arg = _inspect_validator(self.func, 'plain')
        if info_arg:
            func = cast(core_schema.WithInfoValidatorFunction, self.func)
            return core_schema.with_info_plain_validator_function(
                func,
                field_name=handler.field_name,
                serialization=serialization,  # pyright: ignore[reportArgumentType]
                json_schema_input_schema=input_schema,
            )
        else:
            func = cast(core_schema.NoInfoValidatorFunction, self.func)
            return core_schema.no_info_plain_validator_function(
                func,
                serialization=serialization,  # pyright: ignore[reportArgumentType]
                json_schema_input_schema=input_schema,
            )

    @classmethod
    def _from_decorator(cls, decorator: _decorators.Decorator[_decorators.FieldValidatorDecoratorInfo]) -> Self:
        return cls(
            func=decorator.func,
            json_schema_input_type=decorator.info.json_schema_input_type,
        )


@dataclasses.dataclass(frozen=True, **_internal_dataclass.slots_true)
class WrapValidator:
    """!!! abstract "Usage Documentation"
        [field *wrap* validators](../concepts/validators.md#field-wrap-validator)

    A metadata class that indicates that a validation should be applied **around** the inner validation logic.

    Attributes:
        func: The validator function.
        json_schema_input_type: The input type of the function. This is only used to generate the appropriate
            JSON Schema (in validation mode).

    ```python
    from datetime import datetime
    from typing import Annotated

    from pydantic import BaseModel, ValidationError, WrapValidator

    def validate_timestamp(v, handler):
        if v == 'now':
            # we don't want to bother with further validation, just return the new value
            return datetime.now()
        try:
            return handler(v)
        except ValidationError:
            # validation failed, in this case we want to return a default value
            return datetime(2000, 1, 1)

    MyTimestamp = Annotated[datetime, WrapValidator(validate_timestamp)]

    class Model(BaseModel):
        a: MyTimestamp

    print(Model(a='now').a)
    #> 2032-01-02 03:04:05.000006
    print(Model(a='invalid').a)
    #> 2000-01-01 00:00:00
    ```
    """

    func: core_schema.NoInfoWrapValidatorFunction | core_schema.WithInfoWrapValidatorFunction
    json_schema_input_type: Any = PydanticUndefined

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source_type)
        input_schema = (
            None
            if self.json_schema_input_type is PydanticUndefined
            else handler.generate_schema(self.json_schema_input_type)
        )

        info_arg = _inspect_validator(self.func, 'wrap')
        if info_arg:
            func = cast(core_schema.WithInfoWrapValidatorFunction, self.func)
            return core_schema.with_info_wrap_validator_function(
                func,
                schema=schema,
                field_name=handler.field_name,
                json_schema_input_schema=input_schema,
            )
        else:
            func = cast(core_schema.NoInfoWrapValidatorFunction, self.func)
            return core_schema.no_info_wrap_validator_function(
                func,
                schema=schema,
                json_schema_input_schema=input_schema,
            )

    @classmethod
    def _from_decorator(cls, decorator: _decorators.Decorator[_decorators.FieldValidatorDecoratorInfo]) -> Self:
        return cls(
            func=decorator.func,
            json_schema_input_type=decorator.info.json_schema_input_type,
        )


if TYPE_CHECKING:

    class _OnlyValueValidatorClsMethod(Protocol):
        def __call__(self, cls: Any, value: Any, /) -> Any: ...

    class _V2ValidatorClsMethod(Protocol):
        def __call__(self, cls: Any, value: Any, info: _core_schema.ValidationInfo, /) -> Any: ...

    class _OnlyValueWrapValidatorClsMethod(Protocol):
        def __call__(self, cls: Any, value: Any, handler: _core_schema.ValidatorFunctionWrapHandler, /) -> Any: ...

    class _V2WrapValidatorClsMethod(Protocol):
        def __call__(
            self,
            cls: Any,
            value: Any,
            handler: _core_schema.ValidatorFunctionWrapHandler,
            info: _core_schema.ValidationInfo,
            /,
        ) -> Any: ...

    _V2Validator = Union[
        _V2ValidatorClsMethod,
        _core_schema.WithInfoValidatorFunction,
        _OnlyValueValidatorClsMethod,
        _core_schema.NoInfoValidatorFunction,
    ]

    _V2WrapValidator = Union[
        _V2WrapValidatorClsMethod,
        _core_schema.WithInfoWrapValidatorFunction,
        _OnlyValueWrapValidatorClsMethod,
        _core_schema.NoInfoWrapValidatorFunction,
    ]

    _PartialClsOrStaticMethod: TypeAlias = Union[classmethod[Any, Any, Any], staticmethod[Any, Any], partialmethod[Any]]

    _V2BeforeAfterOrPlainValidatorType = TypeVar(
        '_V2BeforeAfterOrPlainValidatorType',
        bound=Union[_V2Validator, _PartialClsOrStaticMethod],
    )
    _V2WrapValidatorType = TypeVar('_V2WrapValidatorType', bound=Union[_V2WrapValidator, _PartialClsOrStaticMethod])

FieldValidatorModes: TypeAlias = Literal['before', 'after', 'wrap', 'plain']


@overload
def field_validator(
    field: str,
    /,
    *fields: str,
    mode: Literal['wrap'],
    check_fields: bool | None = ...,
    json_schema_input_type: Any = ...,
) -> Callable[[_V2WrapValidatorType], _V2WrapValidatorType]: ...


@overload
def field_validator(
    field: str,
    /,
    *fields: str,
    mode: Literal['before', 'plain'],
    check_fields: bool | None = ...,
    json_schema_input_type: Any = ...,
) -> Callable[[_V2BeforeAfterOrPlainValidatorType], _V2BeforeAfterOrPlainValidatorType]: ...


@overload
def field_validator(
    field: str,
    /,
    *fields: str,
    mode: Literal['after'] = ...,
    check_fields: bool | None = ...,
) -> Callable[[_V2BeforeAfterOrPlainValidatorType], _V2BeforeAfterOrPlainValidatorType]: ...


def field_validator(
    field: str,
    /,
    *fields: str,
    mode: FieldValidatorModes = 'after',
    check_fields: bool | None = None,
    json_schema_input_type: Any = PydanticUndefined,
) -> Callable[[Any], Any]:
    """!!! abstract "Usage Documentation"
        [field validators](../concepts/validators.md#field-validators)

    Decorate methods on the class indicating that they should be used to validate fields.

    Example usage:
    ```python
    from typing import Any

    from pydantic import (
        BaseModel,
        ValidationError,
        field_validator,
    )

    class Model(BaseModel):
        a: str

        @field_validator('a')
        @classmethod
        def ensure_foobar(cls, v: Any):
            if 'foobar' not in v:
                raise ValueError('"foobar" not found in a')
            return v

    print(repr(Model(a='this is foobar good')))
    #> Model(a='this is foobar good')

    try:
        Model(a='snap')
    except ValidationError as exc_info:
        print(exc_info)
        '''
        1 validation error for Model
        a
          Value error, "foobar" not found in a [type=value_error, input_value='snap', input_type=str]
        '''
    ```

    For more in depth examples, see [Field Validators](../concepts/validators.md#field-validators).

    Args:
        field: The first field the `field_validator` should be called on; this is separate
            from `fields` to ensure an error is raised if you don't pass at least one.
        *fields: Additional field(s) the `field_validator` should be called on.
        mode: Specifies whether to validate the fields before or after validation.
        check_fields: Whether to check that the fields actually exist on the model.
        json_schema_input_type: The input type of the function. This is only used to generate
            the appropriate JSON Schema (in validation mode) and can only specified
            when `mode` is either `'before'`, `'plain'` or `'wrap'`.

    Returns:
        A decorator that can be used to decorate a function to be used as a field_validator.

    Raises:
        PydanticUserError:
            - If `@field_validator` is used bare (with no fields).
            - If the args passed to `@field_validator` as fields are not strings.
            - If `@field_validator` applied to instance methods.
    """
    if isinstance(field, FunctionType):
        raise PydanticUserError(
            '`@field_validator` should be used with fields and keyword arguments, not bare. '
            "E.g. usage should be `@validator('<field_name>', ...)`",
            code='validator-no-fields',
        )

    if mode not in ('before', 'plain', 'wrap') and json_schema_input_type is not PydanticUndefined:
        raise PydanticUserError(
            f"`json_schema_input_type` can't be used when mode is set to {mode!r}",
            code='validator-input-type',
        )

    if json_schema_input_type is PydanticUndefined and mode == 'plain':
        json_schema_input_type = Any

    fields = field, *fields
    if not all(isinstance(field, str) for field in fields):
        raise PydanticUserError(
            '`@field_validator` fields should be passed as separate string args. '
            "E.g. usage should be `@validator('<field_name_1>', '<field_name_2>', ...)`",
            code='validator-invalid-fields',
        )

    def dec(
        f: Callable[..., Any] | staticmethod[Any, Any] | classmethod[Any, Any, Any],
    ) -> _decorators.PydanticDescriptorProxy[Any]:
        if _decorators.is_instance_method_from_sig(f):
            raise PydanticUserError(
                '`@field_validator` cannot be applied to instance methods', code='validator-instance-method'
            )

        # auto apply the @classmethod decorator
        f = _decorators.ensure_classmethod_based_on_signature(f)

        dec_info = _decorators.FieldValidatorDecoratorInfo(
            fields=fields, mode=mode, check_fields=check_fields, json_schema_input_type=json_schema_input_type
        )
        return _decorators.PydanticDescriptorProxy(f, dec_info)

    return dec


_ModelType = TypeVar('_ModelType')
_ModelTypeCo = TypeVar('_ModelTypeCo', covariant=True)


class ModelWrapValidatorHandler(_core_schema.ValidatorFunctionWrapHandler, Protocol[_ModelTypeCo]):
    """`@model_validator` decorated function handler argument type. This is used when `mode='wrap'`."""

    def __call__(  # noqa: D102
        self,
        value: Any,
        outer_location: str | int | None = None,
        /,
    ) -> _ModelTypeCo:  # pragma: no cover
        ...


class ModelWrapValidatorWithoutInfo(Protocol[_ModelType]):
    """A `@model_validator` decorated function signature.
    This is used when `mode='wrap'` and the function does not have info argument.
    """

    def __call__(  # noqa: D102
        self,
        cls: type[_ModelType],
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        handler: ModelWrapValidatorHandler[_ModelType],
        /,
    ) -> _ModelType: ...


class ModelWrapValidator(Protocol[_ModelType]):
    """A `@model_validator` decorated function signature. This is used when `mode='wrap'`."""

    def __call__(  # noqa: D102
        self,
        cls: type[_ModelType],
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        handler: ModelWrapValidatorHandler[_ModelType],
        info: _core_schema.ValidationInfo,
        /,
    ) -> _ModelType: ...


class FreeModelBeforeValidatorWithoutInfo(Protocol):
    """A `@model_validator` decorated function signature.
    This is used when `mode='before'` and the function does not have info argument.
    """

    def __call__(  # noqa: D102
        self,
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        /,
    ) -> Any: ...


class ModelBeforeValidatorWithoutInfo(Protocol):
    """A `@model_validator` decorated function signature.
    This is used when `mode='before'` and the function does not have info argument.
    """

    def __call__(  # noqa: D102
        self,
        cls: Any,
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        /,
    ) -> Any: ...


class FreeModelBeforeValidator(Protocol):
    """A `@model_validator` decorated function signature. This is used when `mode='before'`."""

    def __call__(  # noqa: D102
        self,
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        info: _core_schema.ValidationInfo,
        /,
    ) -> Any: ...


class ModelBeforeValidator(Protocol):
    """A `@model_validator` decorated function signature. This is used when `mode='before'`."""

    def __call__(  # noqa: D102
        self,
        cls: Any,
        # this can be a dict, a model instance
        # or anything else that gets passed to validate_python
        # thus validators _must_ handle all cases
        value: Any,
        info: _core_schema.ValidationInfo,
        /,
    ) -> Any: ...


ModelAfterValidatorWithoutInfo = Callable[[_ModelType], _ModelType]
"""A `@model_validator` decorated function signature. This is used when `mode='after'` and the function does not
have info argument.
"""

ModelAfterValidator = Callable[[_ModelType, _core_schema.ValidationInfo], _ModelType]
"""A `@model_validator` decorated function signature. This is used when `mode='after'`."""

_AnyModelWrapValidator = Union[ModelWrapValidator[_ModelType], ModelWrapValidatorWithoutInfo[_ModelType]]
_AnyModelBeforeValidator = Union[
    FreeModelBeforeValidator, ModelBeforeValidator, FreeModelBeforeValidatorWithoutInfo, ModelBeforeValidatorWithoutInfo
]
_AnyModelAfterValidator = Union[ModelAfterValidator[_ModelType], ModelAfterValidatorWithoutInfo[_ModelType]]


@overload
def model_validator(
    *,
    mode: Literal['wrap'],
) -> Callable[
    [_AnyModelWrapValidator[_ModelType]], _decorators.PydanticDescriptorProxy[_decorators.ModelValidatorDecoratorInfo]
]: ...


@overload
def model_validator(
    *,
    mode: Literal['before'],
) -> Callable[
    [_AnyModelBeforeValidator], _decorators.PydanticDescriptorProxy[_decorators.ModelValidatorDecoratorInfo]
]: ...


@overload
def model_validator(
    *,
    mode: Literal['after'],
) -> Callable[
    [_AnyModelAfterValidator[_ModelType]], _decorators.PydanticDescriptorProxy[_decorators.ModelValidatorDecoratorInfo]
]: ...


def model_validator(
    *,
    mode: Literal['wrap', 'before', 'after'],
) -> Any:
    """!!! abstract "Usage Documentation"
        [Model Validators](../concepts/validators.md#model-validators)

    Decorate model methods for validation purposes.

    Example usage:
    ```python
    from typing_extensions import Self

    from pydantic import BaseModel, ValidationError, model_validator

    class Square(BaseModel):
        width: float
        height: float

        @model_validator(mode='after')
        def verify_square(self) -> Self:
            if self.width != self.height:
                raise ValueError('width and height do not match')
            return self

    s = Square(width=1, height=1)
    print(repr(s))
    #> Square(width=1.0, height=1.0)

    try:
        Square(width=1, height=2)
    except ValidationError as e:
        print(e)
        '''
        1 validation error for Square
          Value error, width and height do not match [type=value_error, input_value={'width': 1, 'height': 2}, input_type=dict]
        '''
    ```

    For more in depth examples, see [Model Validators](../concepts/validators.md#model-validators).

    Args:
        mode: A required string literal that specifies the validation mode.
            It can be one of the following: 'wrap', 'before', or 'after'.

    Returns:
        A decorator that can be used to decorate a function to be used as a model validator.
    """

    def dec(f: Any) -> _decorators.PydanticDescriptorProxy[Any]:
        # auto apply the @classmethod decorator
        f = _decorators.ensure_classmethod_based_on_signature(f)
        dec_info = _decorators.ModelValidatorDecoratorInfo(mode=mode)
        return _decorators.PydanticDescriptorProxy(f, dec_info)

    return dec


AnyType = TypeVar('AnyType')


if TYPE_CHECKING:
    # If we add configurable attributes to IsInstance, we'd probably need to stop hiding it from type checkers like this
    InstanceOf = Annotated[AnyType, ...]  # `IsInstance[Sequence]` will be recognized by type checkers as `Sequence`

else:

    @dataclasses.dataclass(**_internal_dataclass.slots_true)
    class InstanceOf:
        '''Generic type for annotating a type that is an instance of a given class.

        Example:
            ```python
            from pydantic import BaseModel, InstanceOf

            class Foo:
                ...

            class Bar(BaseModel):
                foo: InstanceOf[Foo]

            Bar(foo=Foo())
            try:
                Bar(foo=42)
            except ValidationError as e:
                print(e)
                """
                [
                │   {
                │   │   'type': 'is_instance_of',
                │   │   'loc': ('foo',),
                │   │   'msg': 'Input should be an instance of Foo',
                │   │   'input': 42,
                │   │   'ctx': {'class': 'Foo'},
                │   │   'url': 'https://errors.pydantic.dev/0.38.0/v/is_instance_of'
                │   }
                ]
                """
            ```
        '''

        @classmethod
        def __class_getitem__(cls, item: AnyType) -> AnyType:
            return Annotated[item, cls()]

        @classmethod
        def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
            from pydantic import PydanticSchemaGenerationError

            # use the generic _origin_ as the second argument to isinstance when appropriate
            instance_of_schema = core_schema.is_instance_schema(_generics.get_origin(source) or source)

            try:
                # Try to generate the "standard" schema, which will be used when loading from JSON
                original_schema = handler(source)
            except PydanticSchemaGenerationError:
                # If that fails, just produce a schema that can validate from python
                return instance_of_schema
            else:
                # Use the "original" approach to serialization
                instance_of_schema['serialization'] = core_schema.wrap_serializer_function_ser_schema(
                    function=lambda v, h: h(v), schema=original_schema
                )
                return core_schema.json_or_python_schema(python_schema=instance_of_schema, json_schema=original_schema)

        __hash__ = object.__hash__


if TYPE_CHECKING:
    SkipValidation = Annotated[AnyType, ...]  # SkipValidation[list[str]] will be treated by type checkers as list[str]
else:

    @dataclasses.dataclass(**_internal_dataclass.slots_true)
    class SkipValidation:
        """If this is applied as an annotation (e.g., via `x: Annotated[int, SkipValidation]`), validation will be
            skipped. You can also use `SkipValidation[int]` as a shorthand for `Annotated[int, SkipValidation]`.

        This can be useful if you want to use a type annotation for documentation/IDE/type-checking purposes,
        and know that it is safe to skip validation for one or more of the fields.

        Because this converts the validation schema to `any_schema`, subsequent annotation-applied transformations
        may not have the expected effects. Therefore, when used, this annotation should generally be the final
        annotation applied to a type.
        """

        def __class_getitem__(cls, item: Any) -> Any:
            return Annotated[item, SkipValidation()]

        @classmethod
        def __get_pydantic_core_schema__(cls, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
            original_schema = handler(source)
            metadata = {'pydantic_js_annotation_functions': [lambda _c, h: h(original_schema)]}
            return core_schema.any_schema(
                metadata=metadata,
                serialization=core_schema.wrap_serializer_function_ser_schema(
                    function=lambda v, h: h(v), schema=original_schema
                ),
            )

        __hash__ = object.__hash__

# === NexusCore/openenv\Lib\site-packages\jupyter_client\client.py ===
"""Base class to manage the interaction with a running kernel"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import inspect
import sys
import time
import typing as t
from functools import partial
from getpass import getpass
from queue import Empty

import zmq.asyncio
from jupyter_core.utils import ensure_async
from traitlets import Any, Bool, Instance, Type

from .channels import major_protocol_version
from .channelsabc import ChannelABC, HBChannelABC
from .clientabc import KernelClientABC
from .connect import ConnectionFileMixin
from .session import Session

# some utilities to validate message structure, these might get moved elsewhere
# if they prove to have more generic utility


def validate_string_dict(dct: t.Dict[str, str]) -> None:
    """Validate that the input is a dict with string keys and values.

    Raises ValueError if not."""
    for k, v in dct.items():
        if not isinstance(k, str):
            raise ValueError("key %r in dict must be a string" % k)
        if not isinstance(v, str):
            raise ValueError("value %r in dict must be a string" % v)


def reqrep(wrapped: t.Callable, meth: t.Callable, channel: str = "shell") -> t.Callable:
    wrapped = wrapped(meth, channel)
    if not meth.__doc__:
        # python -OO removes docstrings,
        # so don't bother building the wrapped docstring
        return wrapped

    basedoc, _ = meth.__doc__.split("Returns\n", 1)
    parts = [basedoc.strip()]
    if "Parameters" not in basedoc:
        parts.append(
            """
        Parameters
        ----------
        """
        )
    parts.append(
        """
        reply: bool (default: False)
            Whether to wait for and return reply
        timeout: float or None (default: None)
            Timeout to use when waiting for a reply

        Returns
        -------
        msg_id: str
            The msg_id of the request sent, if reply=False (default)
        reply: dict
            The reply message for this request, if reply=True
    """
    )
    wrapped.__doc__ = "\n".join(parts)
    return wrapped


class KernelClient(ConnectionFileMixin):
    """Communicates with a single kernel on any host via zmq channels.

    There are five channels associated with each kernel:

    * shell: for request/reply calls to the kernel.
    * iopub: for the kernel to publish results to frontends.
    * hb: for monitoring the kernel's heartbeat.
    * stdin: for frontends to reply to raw_input calls in the kernel.
    * control: for kernel management calls to the kernel.

    The messages that can be sent on these channels are exposed as methods of the
    client (KernelClient.execute, complete, history, etc.). These methods only
    send the message, they don't wait for a reply. To get results, use e.g.
    :meth:`get_shell_msg` to fetch messages from the shell channel.
    """

    # The PyZMQ Context to use for communication with the kernel.
    context = Instance(zmq.Context)

    _created_context = Bool(False)

    def _context_default(self) -> zmq.Context:
        self._created_context = True
        return zmq.Context()

    # The classes to use for the various channels
    shell_channel_class = Type(ChannelABC)
    iopub_channel_class = Type(ChannelABC)
    stdin_channel_class = Type(ChannelABC)
    hb_channel_class = Type(HBChannelABC)
    control_channel_class = Type(ChannelABC)

    # Protected traits
    _shell_channel = Any()
    _iopub_channel = Any()
    _stdin_channel = Any()
    _hb_channel = Any()
    _control_channel = Any()

    # flag for whether execute requests should be allowed to call raw_input:
    allow_stdin: bool = True

    def __del__(self) -> None:
        """Handle garbage collection.  Destroy context if applicable."""
        if (
            self._created_context
            and self.context is not None  # type:ignore[redundant-expr]
            and not self.context.closed
        ):
            if self.channels_running:
                if self.log:
                    self.log.warning("Could not destroy zmq context for %s", self)
            else:
                if self.log:
                    self.log.debug("Destroying zmq context for %s", self)
                self.context.destroy()
        try:
            super_del = super().__del__  # type:ignore[misc]
        except AttributeError:
            pass
        else:
            super_del()

    # --------------------------------------------------------------------------
    # Channel proxy methods
    # --------------------------------------------------------------------------

    async def _async_get_shell_msg(self, *args: t.Any, **kwargs: t.Any) -> t.Dict[str, t.Any]:
        """Get a message from the shell channel"""
        return await ensure_async(self.shell_channel.get_msg(*args, **kwargs))

    async def _async_get_iopub_msg(self, *args: t.Any, **kwargs: t.Any) -> t.Dict[str, t.Any]:
        """Get a message from the iopub channel"""
        return await ensure_async(self.iopub_channel.get_msg(*args, **kwargs))

    async def _async_get_stdin_msg(self, *args: t.Any, **kwargs: t.Any) -> t.Dict[str, t.Any]:
        """Get a message from the stdin channel"""
        return await ensure_async(self.stdin_channel.get_msg(*args, **kwargs))

    async def _async_get_control_msg(self, *args: t.Any, **kwargs: t.Any) -> t.Dict[str, t.Any]:
        """Get a message from the control channel"""
        return await ensure_async(self.control_channel.get_msg(*args, **kwargs))

    async def _async_wait_for_ready(self, timeout: t.Optional[float] = None) -> None:
        """Waits for a response when a client is blocked

        - Sets future time for timeout
        - Blocks on shell channel until a message is received
        - Exit if the kernel has died
        - If client times out before receiving a message from the kernel, send RuntimeError
        - Flush the IOPub channel
        """
        if timeout is None:
            timeout = float("inf")
        abs_timeout = time.time() + timeout

        from .manager import KernelManager

        if not isinstance(self.parent, KernelManager):
            # This Client was not created by a KernelManager,
            # so wait for kernel to become responsive to heartbeats
            # before checking for kernel_info reply
            while not await self._async_is_alive():
                if time.time() > abs_timeout:
                    raise RuntimeError(
                        "Kernel didn't respond to heartbeats in %d seconds and timed out" % timeout
                    )
                await asyncio.sleep(0.2)

        # Wait for kernel info reply on shell channel
        while True:
            self.kernel_info()
            try:
                msg = await ensure_async(self.shell_channel.get_msg(timeout=1))
            except Empty:
                pass
            else:
                if msg["msg_type"] == "kernel_info_reply":
                    # Checking that IOPub is connected. If it is not connected, start over.
                    try:
                        await ensure_async(self.iopub_channel.get_msg(timeout=0.2))
                    except Empty:
                        pass
                    else:
                        self._handle_kernel_info_reply(msg)
                        break

            if not await self._async_is_alive():
                msg = "Kernel died before replying to kernel_info"
                raise RuntimeError(msg)

            # Check if current time is ready check time plus timeout
            if time.time() > abs_timeout:
                raise RuntimeError("Kernel didn't respond in %d seconds" % timeout)

        # Flush IOPub channel
        while True:
            try:
                msg = await ensure_async(self.iopub_channel.get_msg(timeout=0.2))
            except Empty:
                break

    async def _async_recv_reply(
        self, msg_id: str, timeout: t.Optional[float] = None, channel: str = "shell"
    ) -> t.Dict[str, t.Any]:
        """Receive and return the reply for a given request"""
        if timeout is not None:
            deadline = time.monotonic() + timeout
        while True:
            if timeout is not None:
                timeout = max(0, deadline - time.monotonic())
            try:
                if channel == "control":
                    reply = await self._async_get_control_msg(timeout=timeout)
                else:
                    reply = await self._async_get_shell_msg(timeout=timeout)
            except Empty as e:
                msg = "Timeout waiting for reply"
                raise TimeoutError(msg) from e
            if reply["parent_header"].get("msg_id") != msg_id:
                # not my reply, someone may have forgotten to retrieve theirs
                continue
            return reply

    async def _stdin_hook_default(self, msg: t.Dict[str, t.Any]) -> None:
        """Handle an input request"""
        content = msg["content"]
        prompt = getpass if content.get("password", False) else input

        try:
            raw_data = prompt(content["prompt"])  # type:ignore[operator]
        except EOFError:
            # turn EOFError into EOF character
            raw_data = "\x04"
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            return

        # only send stdin reply if there *was not* another request
        # or execution finished while we were reading.
        if not (await self.stdin_channel.msg_ready() or await self.shell_channel.msg_ready()):
            self.input(raw_data)

    def _output_hook_default(self, msg: t.Dict[str, t.Any]) -> None:
        """Default hook for redisplaying plain-text output"""
        msg_type = msg["header"]["msg_type"]
        content = msg["content"]
        if msg_type == "stream":
            stream = getattr(sys, content["name"])
            stream.write(content["text"])
        elif msg_type in ("display_data", "execute_result"):
            sys.stdout.write(content["data"].get("text/plain", ""))
        elif msg_type == "error":
            sys.stderr.write("\n".join(content["traceback"]))

    def _output_hook_kernel(
        self,
        session: Session,
        socket: zmq.sugar.socket.Socket,
        parent_header: t.Any,
        msg: t.Dict[str, t.Any],
    ) -> None:
        """Output hook when running inside an IPython kernel

        adds rich output support.
        """
        msg_type = msg["header"]["msg_type"]
        if msg_type in ("display_data", "execute_result", "error"):
            session.send(socket, msg_type, msg["content"], parent=parent_header)
        else:
            self._output_hook_default(msg)

    # --------------------------------------------------------------------------
    # Channel management methods
    # --------------------------------------------------------------------------

    def start_channels(
        self,
        shell: bool = True,
        iopub: bool = True,
        stdin: bool = True,
        hb: bool = True,
        control: bool = True,
    ) -> None:
        """Starts the channels for this kernel.

        This will create the channels if they do not exist and then start
        them (their activity runs in a thread). If port numbers of 0 are
        being used (random ports) then you must first call
        :meth:`start_kernel`. If the channels have been stopped and you
        call this, :class:`RuntimeError` will be raised.
        """
        if iopub:
            self.iopub_channel.start()
        if shell:
            self.shell_channel.start()
        if stdin:
            self.stdin_channel.start()
            self.allow_stdin = True
        else:
            self.allow_stdin = False
        if hb:
            self.hb_channel.start()
        if control:
            self.control_channel.start()

    def stop_channels(self) -> None:
        """Stops all the running channels for this kernel.

        This stops their event loops and joins their threads.
        """
        if self.shell_channel.is_alive():
            self.shell_channel.stop()
        if self.iopub_channel.is_alive():
            self.iopub_channel.stop()
        if self.stdin_channel.is_alive():
            self.stdin_channel.stop()
        if self.hb_channel.is_alive():
            self.hb_channel.stop()
        if self.control_channel.is_alive():
            self.control_channel.stop()

    @property
    def channels_running(self) -> bool:
        """Are any of the channels created and running?"""
        return (
            (self._shell_channel and self.shell_channel.is_alive())
            or (self._iopub_channel and self.iopub_channel.is_alive())
            or (self._stdin_channel and self.stdin_channel.is_alive())
            or (self._hb_channel and self.hb_channel.is_alive())
            or (self._control_channel and self.control_channel.is_alive())
        )

    ioloop = None  # Overridden in subclasses that use pyzmq event loop

    @property
    def shell_channel(self) -> t.Any:
        """Get the shell channel object for this kernel."""
        if self._shell_channel is None:
            url = self._make_url("shell")
            self.log.debug("connecting shell channel to %s", url)
            socket = self.connect_shell(identity=self.session.bsession)
            self._shell_channel = self.shell_channel_class(  # type:ignore[call-arg,abstract]
                socket, self.session, self.ioloop
            )
        return self._shell_channel

    @property
    def iopub_channel(self) -> t.Any:
        """Get the iopub channel object for this kernel."""
        if self._iopub_channel is None:
            url = self._make_url("iopub")
            self.log.debug("connecting iopub channel to %s", url)
            socket = self.connect_iopub()
            self._iopub_channel = self.iopub_channel_class(  # type:ignore[call-arg,abstract]
                socket, self.session, self.ioloop
            )
        return self._iopub_channel

    @property
    def stdin_channel(self) -> t.Any:
        """Get the stdin channel object for this kernel."""
        if self._stdin_channel is None:
            url = self._make_url("stdin")
            self.log.debug("connecting stdin channel to %s", url)
            socket = self.connect_stdin(identity=self.session.bsession)
            self._stdin_channel = self.stdin_channel_class(  # type:ignore[call-arg,abstract]
                socket, self.session, self.ioloop
            )
        return self._stdin_channel

    @property
    def hb_channel(self) -> t.Any:
        """Get the hb channel object for this kernel."""
        if self._hb_channel is None:
            url = self._make_url("hb")
            self.log.debug("connecting heartbeat channel to %s", url)
            self._hb_channel = self.hb_channel_class(  # type:ignore[call-arg,abstract]
                self.context, self.session, url
            )
        return self._hb_channel

    @property
    def control_channel(self) -> t.Any:
        """Get the control channel object for this kernel."""
        if self._control_channel is None:
            url = self._make_url("control")
            self.log.debug("connecting control channel to %s", url)
            socket = self.connect_control(identity=self.session.bsession)
            self._control_channel = self.control_channel_class(  # type:ignore[call-arg,abstract]
                socket, self.session, self.ioloop
            )
        return self._control_channel

    async def _async_is_alive(self) -> bool:
        """Is the kernel process still running?"""
        from .manager import KernelManager

        if isinstance(self.parent, KernelManager):
            # This KernelClient was created by a KernelManager,
            # we can ask the parent KernelManager:
            return await self.parent._async_is_alive()
        if self._hb_channel is not None:
            # We don't have access to the KernelManager,
            # so we use the heartbeat.
            return self._hb_channel.is_beating()
        # no heartbeat and not local, we can't tell if it's running,
        # so naively return True
        return True

    async def _async_execute_interactive(
        self,
        code: str,
        silent: bool = False,
        store_history: bool = True,
        user_expressions: t.Optional[t.Dict[str, t.Any]] = None,
        allow_stdin: t.Optional[bool] = None,
        stop_on_error: bool = True,
        timeout: t.Optional[float] = None,
        output_hook: t.Optional[t.Callable] = None,
        stdin_hook: t.Optional[t.Callable] = None,
    ) -> t.Dict[str, t.Any]:
        """Execute code in the kernel interactively

        Output will be redisplayed, and stdin prompts will be relayed as well.
        If an IPython kernel is detected, rich output will be displayed.

        You can pass a custom output_hook callable that will be called
        with every IOPub message that is produced instead of the default redisplay.

        .. versionadded:: 5.0

        Parameters
        ----------
        code : str
            A string of code in the kernel's language.

        silent : bool, optional (default False)
            If set, the kernel will execute the code as quietly possible, and
            will force store_history to be False.

        store_history : bool, optional (default True)
            If set, the kernel will store command history.  This is forced
            to be False if silent is True.

        user_expressions : dict, optional
            A dict mapping names to expressions to be evaluated in the user's
            dict. The expression values are returned as strings formatted using
            :func:`repr`.

        allow_stdin : bool, optional (default self.allow_stdin)
            Flag for whether the kernel can send stdin requests to frontends.

            Some frontends (e.g. the Notebook) do not support stdin requests.
            If raw_input is called from code executed from such a frontend, a
            StdinNotImplementedError will be raised.

        stop_on_error: bool, optional (default True)
            Flag whether to abort the execution queue, if an exception is encountered.

        timeout: float or None (default: None)
            Timeout to use when waiting for a reply

        output_hook: callable(msg)
            Function to be called with output messages.
            If not specified, output will be redisplayed.

        stdin_hook: callable(msg)
            Function or awaitable to be called with stdin_request messages.
            If not specified, input/getpass will be called.

        Returns
        -------
        reply: dict
            The reply message for this request
        """
        if not self.iopub_channel.is_alive():
            emsg = "IOPub channel must be running to receive output"
            raise RuntimeError(emsg)
        if allow_stdin is None:
            allow_stdin = self.allow_stdin
        if allow_stdin and not self.stdin_channel.is_alive():
            emsg = "stdin channel must be running to allow input"
            raise RuntimeError(emsg)
        msg_id = await ensure_async(
            self.execute(
                code,
                silent=silent,
                store_history=store_history,
                user_expressions=user_expressions,
                allow_stdin=allow_stdin,
                stop_on_error=stop_on_error,
            )
        )
        if stdin_hook is None:
            stdin_hook = self._stdin_hook_default
        # detect IPython kernel
        if output_hook is None and "IPython" in sys.modules:
            from IPython import get_ipython

            ip = get_ipython()  # type:ignore[no-untyped-call]
            in_kernel = getattr(ip, "kernel", False)
            if in_kernel:
                output_hook = partial(
                    self._output_hook_kernel,
                    ip.display_pub.session,
                    ip.display_pub.pub_socket,
                    ip.display_pub.parent_header,
                )
        if output_hook is None:
            # default: redisplay plain-text outputs
            output_hook = self._output_hook_default

        # set deadline based on timeout
        if timeout is not None:
            deadline = time.monotonic() + timeout
        else:
            timeout_ms = None

        poller = zmq.asyncio.Poller()
        iopub_socket = self.iopub_channel.socket
        poller.register(iopub_socket, zmq.POLLIN)
        if allow_stdin:
            stdin_socket = self.stdin_channel.socket
            poller.register(stdin_socket, zmq.POLLIN)
        else:
            stdin_socket = None

        # wait for output and redisplay it
        while True:
            if timeout is not None:
                timeout = max(0, deadline - time.monotonic())
                timeout_ms = int(1000 * timeout)
            events = dict(await poller.poll(timeout_ms))
            if not events:
                emsg = "Timeout waiting for output"
                raise TimeoutError(emsg)
            if stdin_socket in events:
                req = await ensure_async(self.stdin_channel.get_msg(timeout=0))
                res = stdin_hook(req)
                if inspect.isawaitable(res):
                    await res
                continue
            if iopub_socket not in events:
                continue

            msg = await ensure_async(self.iopub_channel.get_msg(timeout=0))

            if msg["parent_header"].get("msg_id") != msg_id:
                # not from my request
                continue
            output_hook(msg)

            # stop on idle
            if (
                msg["header"]["msg_type"] == "status"
                and msg["content"]["execution_state"] == "idle"
            ):
                break

        # output is done, get the reply
        if timeout is not None:
            timeout = max(0, deadline - time.monotonic())
        return await self._async_recv_reply(msg_id, timeout=timeout)

    # Methods to send specific messages on channels
    def execute(
        self,
        code: str,
        silent: bool = False,
        store_history: bool = True,
        user_expressions: t.Optional[t.Dict[str, t.Any]] = None,
        allow_stdin: t.Optional[bool] = None,
        stop_on_error: bool = True,
    ) -> str:
        """Execute code in the kernel.

        Parameters
        ----------
        code : str
            A string of code in the kernel's language.

        silent : bool, optional (default False)
            If set, the kernel will execute the code as quietly possible, and
            will force store_history to be False.

        store_history : bool, optional (default True)
            If set, the kernel will store command history.  This is forced
            to be False if silent is True.

        user_expressions : dict, optional
            A dict mapping names to expressions to be evaluated in the user's
            dict. The expression values are returned as strings formatted using
            :func:`repr`.

        allow_stdin : bool, optional (default self.allow_stdin)
            Flag for whether the kernel can send stdin requests to frontends.

            Some frontends (e.g. the Notebook) do not support stdin requests.
            If raw_input is called from code executed from such a frontend, a
            StdinNotImplementedError will be raised.

        stop_on_error: bool, optional (default True)
            Flag whether to abort the execution queue, if an exception is encountered.

        Returns
        -------
        The msg_id of the message sent.
        """
        if user_expressions is None:
            user_expressions = {}
        if allow_stdin is None:
            allow_stdin = self.allow_stdin

        # Don't waste network traffic if inputs are invalid
        if not isinstance(code, str):
            raise ValueError("code %r must be a string" % code)
        validate_string_dict(user_expressions)

        # Create class for content/msg creation. Related to, but possibly
        # not in Session.
        content = {
            "code": code,
            "silent": silent,
            "store_history": store_history,
            "user_expressions": user_expressions,
            "allow_stdin": allow_stdin,
            "stop_on_error": stop_on_error,
        }
        msg = self.session.msg("execute_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def complete(self, code: str, cursor_pos: t.Optional[int] = None) -> str:
        """Tab complete text in the kernel's namespace.

        Parameters
        ----------
        code : str
            The context in which completion is requested.
            Can be anything between a variable name and an entire cell.
        cursor_pos : int, optional
            The position of the cursor in the block of code where the completion was requested.
            Default: ``len(code)``

        Returns
        -------
        The msg_id of the message sent.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        content = {"code": code, "cursor_pos": cursor_pos}
        msg = self.session.msg("complete_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def inspect(self, code: str, cursor_pos: t.Optional[int] = None, detail_level: int = 0) -> str:
        """Get metadata information about an object in the kernel's namespace.

        It is up to the kernel to determine the appropriate object to inspect.

        Parameters
        ----------
        code : str
            The context in which info is requested.
            Can be anything between a variable name and an entire cell.
        cursor_pos : int, optional
            The position of the cursor in the block of code where the info was requested.
            Default: ``len(code)``
        detail_level : int, optional
            The level of detail for the introspection (0-2)

        Returns
        -------
        The msg_id of the message sent.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        content = {
            "code": code,
            "cursor_pos": cursor_pos,
            "detail_level": detail_level,
        }
        msg = self.session.msg("inspect_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def history(
        self,
        raw: bool = True,
        output: bool = False,
        hist_access_type: str = "range",
        **kwargs: t.Any,
    ) -> str:
        """Get entries from the kernel's history list.

        Parameters
        ----------
        raw : bool
            If True, return the raw input.
        output : bool
            If True, then return the output as well.
        hist_access_type : str
            'range' (fill in session, start and stop params), 'tail' (fill in n)
             or 'search' (fill in pattern param).

        session : int
            For a range request, the session from which to get lines. Session
            numbers are positive integers; negative ones count back from the
            current session.
        start : int
            The first line number of a history range.
        stop : int
            The final (excluded) line number of a history range.

        n : int
            The number of lines of history to get for a tail request.

        pattern : str
            The glob-syntax pattern for a search request.

        Returns
        -------
        The ID of the message sent.
        """
        if hist_access_type == "range":
            kwargs.setdefault("session", 0)
            kwargs.setdefault("start", 0)
        content = dict(raw=raw, output=output, hist_access_type=hist_access_type, **kwargs)
        msg = self.session.msg("history_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def kernel_info(self) -> str:
        """Request kernel info

        Returns
        -------
        The msg_id of the message sent
        """
        msg = self.session.msg("kernel_info_request")
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def comm_info(self, target_name: t.Optional[str] = None) -> str:
        """Request comm info

        Returns
        -------
        The msg_id of the message sent
        """
        content = {} if target_name is None else {"target_name": target_name}
        msg = self.session.msg("comm_info_request", content)
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def _handle_kernel_info_reply(self, msg: t.Dict[str, t.Any]) -> None:
        """handle kernel info reply

        sets protocol adaptation version. This might
        be run from a separate thread.
        """
        adapt_version = int(msg["content"]["protocol_version"].split(".")[0])
        if adapt_version != major_protocol_version:
            self.session.adapt_version = adapt_version

    def is_complete(self, code: str) -> str:
        """Ask the kernel whether some code is complete and ready to execute.

        Returns
        -------
        The ID of the message sent.
        """
        msg = self.session.msg("is_complete_request", {"code": code})
        self.shell_channel.send(msg)
        return msg["header"]["msg_id"]

    def input(self, string: str) -> None:
        """Send a string of raw input to the kernel.

        This should only be called in response to the kernel sending an
        ``input_request`` message on the stdin channel.

        Returns
        -------
        The ID of the message sent.
        """
        content = {"value": string}
        msg = self.session.msg("input_reply", content)
        self.stdin_channel.send(msg)

    def shutdown(self, restart: bool = False) -> str:
        """Request an immediate kernel shutdown on the control channel.

        Upon receipt of the (empty) reply, client code can safely assume that
        the kernel has shut down and it's safe to forcefully terminate it if
        it's still alive.

        The kernel will send the reply via a function registered with Python's
        atexit module, ensuring it's truly done as the kernel is done with all
        normal operation.

        Returns
        -------
        The msg_id of the message sent
        """
        # Send quit message to kernel. Once we implement kernel-side setattr,
        # this should probably be done that way, but for now this will do.
        msg = self.session.msg("shutdown_request", {"restart": restart})
        self.control_channel.send(msg)
        return msg["header"]["msg_id"]


KernelClientABC.register(KernelClient)

# === NexusCore/openenv\Lib\site-packages\fontTools\unicodedata\ScriptExtensions.py ===
# -*- coding: utf-8 -*-
#
# NOTE: This file was auto-generated with MetaTools/buildUCD.py.
# Source: https://unicode.org/Public/UNIDATA/ScriptExtensions.txt
# License: http://unicode.org/copyright.html#License
#
# ScriptExtensions-16.0.0.txt
# Date: 2024-07-30, 19:38:00 GMT
# © 2024 Unicode®, Inc.
# Unicode and the Unicode Logo are registered trademarks of Unicode, Inc. in the U.S. and other countries.
# For terms of use and license, see https://www.unicode.org/terms_of_use.html
#
# Unicode Character Database
#   For documentation, see https://www.unicode.org/reports/tr44/
#
# The Script_Extensions property indicates which characters are commonly used
# with more than one script, but with a limited number of scripts.
# For each code point, there is one or more property values.  Each such value is a Script property value.
# For more information, see:
#   UAX #24, Unicode Script Property: https://www.unicode.org/reports/tr24/
#     Especially the sections:
#       https://www.unicode.org/reports/tr24/#Assignment_Script_Values
#       https://www.unicode.org/reports/tr24/#Assignment_ScriptX_Values
#
# Each Script_Extensions value in this file consists of a set
# of one or more abbreviated Script property values. The ordering of the
# values in that set is not material, but for stability in presentation
# it is given here as alphabetical.
#
# All code points not explicitly listed for Script_Extensions
# have as their value the corresponding Script property value.
#
# @missing: 0000..10FFFF; <script>

RANGES = [
    0x0000,  # .. 0x00B6 ; None
    0x00B7,  # .. 0x00B7 ; {'Avst', 'Cari', 'Copt', 'Dupl', 'Elba', 'Geor', 'Glag', 'Gong', 'Goth', 'Grek', 'Hani', 'Latn', 'Lydi', 'Mahj', 'Perm', 'Shaw'}
    0x00B8,  # .. 0x02BB ; None
    0x02BC,  # .. 0x02BC ; {'Beng', 'Cyrl', 'Deva', 'Latn', 'Lisu', 'Thai', 'Toto'}
    0x02BD,  # .. 0x02C6 ; None
    0x02C7,  # .. 0x02C7 ; {'Bopo', 'Latn'}
    0x02C8,  # .. 0x02C8 ; None
    0x02C9,  # .. 0x02CB ; {'Bopo', 'Latn'}
    0x02CC,  # .. 0x02CC ; None
    0x02CD,  # .. 0x02CD ; {'Latn', 'Lisu'}
    0x02CE,  # .. 0x02D6 ; None
    0x02D7,  # .. 0x02D7 ; {'Latn', 'Thai'}
    0x02D8,  # .. 0x02D8 ; None
    0x02D9,  # .. 0x02D9 ; {'Bopo', 'Latn'}
    0x02DA,  # .. 0x02FF ; None
    0x0300,  # .. 0x0300 ; {'Cher', 'Copt', 'Cyrl', 'Grek', 'Latn', 'Perm', 'Sunu', 'Tale'}
    0x0301,  # .. 0x0301 ; {'Cher', 'Cyrl', 'Grek', 'Latn', 'Osge', 'Sunu', 'Tale', 'Todr'}
    0x0302,  # .. 0x0302 ; {'Cher', 'Cyrl', 'Latn', 'Tfng'}
    0x0303,  # .. 0x0303 ; {'Glag', 'Latn', 'Sunu', 'Syrc', 'Thai'}
    0x0304,  # .. 0x0304 ; {'Aghb', 'Cher', 'Copt', 'Cyrl', 'Goth', 'Grek', 'Latn', 'Osge', 'Syrc', 'Tfng', 'Todr'}
    0x0305,  # .. 0x0305 ; {'Copt', 'Elba', 'Glag', 'Goth', 'Kana', 'Latn'}
    0x0306,  # .. 0x0306 ; {'Cyrl', 'Grek', 'Latn', 'Perm'}
    0x0307,  # .. 0x0307 ; {'Copt', 'Dupl', 'Hebr', 'Latn', 'Perm', 'Syrc', 'Tale', 'Tfng', 'Todr'}
    0x0308,  # .. 0x0308 ; {'Armn', 'Cyrl', 'Dupl', 'Goth', 'Grek', 'Hebr', 'Latn', 'Perm', 'Syrc', 'Tale'}
    0x0309,  # .. 0x0309 ; {'Latn', 'Tfng'}
    0x030A,  # .. 0x030A ; {'Dupl', 'Latn', 'Syrc'}
    0x030B,  # .. 0x030B ; {'Cher', 'Cyrl', 'Latn', 'Osge'}
    0x030C,  # .. 0x030C ; {'Cher', 'Latn', 'Tale'}
    0x030D,  # .. 0x030D ; {'Latn', 'Sunu'}
    0x030E,  # .. 0x030E ; {'Ethi', 'Latn'}
    0x030F,  # .. 0x030F ; None
    0x0310,  # .. 0x0310 ; {'Latn', 'Sunu'}
    0x0311,  # .. 0x0311 ; {'Cyrl', 'Latn', 'Todr'}
    0x0312,  # .. 0x0312 ; None
    0x0313,  # .. 0x0313 ; {'Grek', 'Latn', 'Perm', 'Todr'}
    0x0314,  # .. 0x031F ; None
    0x0320,  # .. 0x0320 ; {'Latn', 'Syrc'}
    0x0321,  # .. 0x0322 ; None
    0x0323,  # .. 0x0323 ; {'Cher', 'Dupl', 'Kana', 'Latn', 'Syrc'}
    0x0324,  # .. 0x0324 ; {'Cher', 'Dupl', 'Latn', 'Syrc'}
    0x0325,  # .. 0x0325 ; {'Latn', 'Syrc'}
    0x0326,  # .. 0x032C ; None
    0x032D,  # .. 0x032D ; {'Latn', 'Sunu', 'Syrc'}
    0x032E,  # .. 0x032E ; {'Latn', 'Syrc'}
    0x032F,  # .. 0x032F ; None
    0x0330,  # .. 0x0330 ; {'Cher', 'Latn', 'Syrc'}
    0x0331,  # .. 0x0331 ; {'Aghb', 'Cher', 'Goth', 'Latn', 'Sunu', 'Thai'}
    0x0332,  # .. 0x0341 ; None
    0x0342,  # .. 0x0342 ; {'Grek'}
    0x0343,  # .. 0x0344 ; None
    0x0345,  # .. 0x0345 ; {'Grek'}
    0x0346,  # .. 0x0357 ; None
    0x0358,  # .. 0x0358 ; {'Latn', 'Osge'}
    0x0359,  # .. 0x035D ; None
    0x035E,  # .. 0x035E ; {'Aghb', 'Latn', 'Todr'}
    0x035F,  # .. 0x0362 ; None
    0x0363,  # .. 0x036F ; {'Latn'}
    0x0370,  # .. 0x0373 ; None
    0x0374,  # .. 0x0375 ; {'Copt', 'Grek'}
    0x0376,  # .. 0x0482 ; None
    0x0483,  # .. 0x0483 ; {'Cyrl', 'Perm'}
    0x0484,  # .. 0x0484 ; {'Cyrl', 'Glag'}
    0x0485,  # .. 0x0486 ; {'Cyrl', 'Latn'}
    0x0487,  # .. 0x0487 ; {'Cyrl', 'Glag'}
    0x0488,  # .. 0x0588 ; None
    0x0589,  # .. 0x0589 ; {'Armn', 'Geor', 'Glag'}
    0x058A,  # .. 0x060B ; None
    0x060C,  # .. 0x060C ; {'Arab', 'Gara', 'Nkoo', 'Rohg', 'Syrc', 'Thaa', 'Yezi'}
    0x060D,  # .. 0x061A ; None
    0x061B,  # .. 0x061B ; {'Arab', 'Gara', 'Nkoo', 'Rohg', 'Syrc', 'Thaa', 'Yezi'}
    0x061C,  # .. 0x061C ; {'Arab', 'Syrc', 'Thaa'}
    0x061D,  # .. 0x061E ; None
    0x061F,  # .. 0x061F ; {'Adlm', 'Arab', 'Gara', 'Nkoo', 'Rohg', 'Syrc', 'Thaa', 'Yezi'}
    0x0620,  # .. 0x063F ; None
    0x0640,  # .. 0x0640 ; {'Adlm', 'Arab', 'Mand', 'Mani', 'Ougr', 'Phlp', 'Rohg', 'Sogd', 'Syrc'}
    0x0641,  # .. 0x064A ; None
    0x064B,  # .. 0x0655 ; {'Arab', 'Syrc'}
    0x0656,  # .. 0x065F ; None
    0x0660,  # .. 0x0669 ; {'Arab', 'Thaa', 'Yezi'}
    0x066A,  # .. 0x066F ; None
    0x0670,  # .. 0x0670 ; {'Arab', 'Syrc'}
    0x0671,  # .. 0x06D3 ; None
    0x06D4,  # .. 0x06D4 ; {'Arab', 'Rohg'}
    0x06D5,  # .. 0x0950 ; None
    0x0951,  # .. 0x0951 ; {'Beng', 'Deva', 'Gran', 'Gujr', 'Guru', 'Knda', 'Latn', 'Mlym', 'Orya', 'Shrd', 'Taml', 'Telu', 'Tirh'}
    0x0952,  # .. 0x0952 ; {'Beng', 'Deva', 'Gran', 'Gujr', 'Guru', 'Knda', 'Latn', 'Mlym', 'Orya', 'Taml', 'Telu', 'Tirh'}
    0x0953,  # .. 0x0963 ; None
    0x0964,  # .. 0x0964 ; {'Beng', 'Deva', 'Dogr', 'Gong', 'Gonm', 'Gran', 'Gujr', 'Guru', 'Knda', 'Mahj', 'Mlym', 'Nand', 'Onao', 'Orya', 'Sind', 'Sinh', 'Sylo', 'Takr', 'Taml', 'Telu', 'Tirh'}
    0x0965,  # .. 0x0965 ; {'Beng', 'Deva', 'Dogr', 'Gong', 'Gonm', 'Gran', 'Gujr', 'Gukh', 'Guru', 'Knda', 'Limb', 'Mahj', 'Mlym', 'Nand', 'Onao', 'Orya', 'Sind', 'Sinh', 'Sylo', 'Takr', 'Taml', 'Telu', 'Tirh'}
    0x0966,  # .. 0x096F ; {'Deva', 'Dogr', 'Kthi', 'Mahj'}
    0x0970,  # .. 0x09E5 ; None
    0x09E6,  # .. 0x09EF ; {'Beng', 'Cakm', 'Sylo'}
    0x09F0,  # .. 0x0A65 ; None
    0x0A66,  # .. 0x0A6F ; {'Guru', 'Mult'}
    0x0A70,  # .. 0x0AE5 ; None
    0x0AE6,  # .. 0x0AEF ; {'Gujr', 'Khoj'}
    0x0AF0,  # .. 0x0BE5 ; None
    0x0BE6,  # .. 0x0BF3 ; {'Gran', 'Taml'}
    0x0BF4,  # .. 0x0CE5 ; None
    0x0CE6,  # .. 0x0CEF ; {'Knda', 'Nand', 'Tutg'}
    0x0CF0,  # .. 0x103F ; None
    0x1040,  # .. 0x1049 ; {'Cakm', 'Mymr', 'Tale'}
    0x104A,  # .. 0x10FA ; None
    0x10FB,  # .. 0x10FB ; {'Geor', 'Glag', 'Latn'}
    0x10FC,  # .. 0x16EA ; None
    0x16EB,  # .. 0x16ED ; {'Runr'}
    0x16EE,  # .. 0x1734 ; None
    0x1735,  # .. 0x1736 ; {'Buhd', 'Hano', 'Tagb', 'Tglg'}
    0x1737,  # .. 0x1801 ; None
    0x1802,  # .. 0x1803 ; {'Mong', 'Phag'}
    0x1804,  # .. 0x1804 ; None
    0x1805,  # .. 0x1805 ; {'Mong', 'Phag'}
    0x1806,  # .. 0x1CCF ; None
    0x1CD0,  # .. 0x1CD0 ; {'Beng', 'Deva', 'Gran', 'Knda'}
    0x1CD1,  # .. 0x1CD1 ; {'Deva'}
    0x1CD2,  # .. 0x1CD2 ; {'Beng', 'Deva', 'Gran', 'Knda'}
    0x1CD3,  # .. 0x1CD3 ; {'Deva', 'Gran', 'Knda'}
    0x1CD4,  # .. 0x1CD4 ; {'Deva'}
    0x1CD5,  # .. 0x1CD6 ; {'Beng', 'Deva'}
    0x1CD7,  # .. 0x1CD7 ; {'Deva', 'Shrd'}
    0x1CD8,  # .. 0x1CD8 ; {'Beng', 'Deva'}
    0x1CD9,  # .. 0x1CD9 ; {'Deva', 'Shrd'}
    0x1CDA,  # .. 0x1CDA ; {'Deva', 'Knda', 'Mlym', 'Orya', 'Taml', 'Telu'}
    0x1CDB,  # .. 0x1CDB ; {'Deva'}
    0x1CDC,  # .. 0x1CDD ; {'Deva', 'Shrd'}
    0x1CDE,  # .. 0x1CDF ; {'Deva'}
    0x1CE0,  # .. 0x1CE0 ; {'Deva', 'Shrd'}
    0x1CE1,  # .. 0x1CE1 ; {'Beng', 'Deva'}
    0x1CE2,  # .. 0x1CE8 ; {'Deva'}
    0x1CE9,  # .. 0x1CE9 ; {'Deva', 'Nand'}
    0x1CEA,  # .. 0x1CEA ; {'Beng', 'Deva'}
    0x1CEB,  # .. 0x1CEC ; {'Deva'}
    0x1CED,  # .. 0x1CED ; {'Beng', 'Deva'}
    0x1CEE,  # .. 0x1CF1 ; {'Deva'}
    0x1CF2,  # .. 0x1CF2 ; {'Beng', 'Deva', 'Gran', 'Knda', 'Mlym', 'Nand', 'Orya', 'Sinh', 'Telu', 'Tirh', 'Tutg'}
    0x1CF3,  # .. 0x1CF3 ; {'Deva', 'Gran'}
    0x1CF4,  # .. 0x1CF4 ; {'Deva', 'Gran', 'Knda', 'Tutg'}
    0x1CF5,  # .. 0x1CF6 ; {'Beng', 'Deva'}
    0x1CF7,  # .. 0x1CF7 ; {'Beng'}
    0x1CF8,  # .. 0x1CF9 ; {'Deva', 'Gran'}
    0x1CFA,  # .. 0x1CFA ; {'Nand'}
    0x1CFB,  # .. 0x1DBF ; None
    0x1DC0,  # .. 0x1DC1 ; {'Grek'}
    0x1DC2,  # .. 0x1DF7 ; None
    0x1DF8,  # .. 0x1DF8 ; {'Cyrl', 'Latn', 'Syrc'}
    0x1DF9,  # .. 0x1DF9 ; None
    0x1DFA,  # .. 0x1DFA ; {'Syrc'}
    0x1DFB,  # .. 0x202E ; None
    0x202F,  # .. 0x202F ; {'Latn', 'Mong', 'Phag'}
    0x2030,  # .. 0x204E ; None
    0x204F,  # .. 0x204F ; {'Adlm', 'Arab'}
    0x2050,  # .. 0x2059 ; None
    0x205A,  # .. 0x205A ; {'Cari', 'Geor', 'Glag', 'Hung', 'Lyci', 'Orkh'}
    0x205B,  # .. 0x205C ; None
    0x205D,  # .. 0x205D ; {'Cari', 'Grek', 'Hung', 'Mero'}
    0x205E,  # .. 0x20EF ; None
    0x20F0,  # .. 0x20F0 ; {'Deva', 'Gran', 'Latn'}
    0x20F1,  # .. 0x2E16 ; None
    0x2E17,  # .. 0x2E17 ; {'Copt', 'Latn'}
    0x2E18,  # .. 0x2E2F ; None
    0x2E30,  # .. 0x2E30 ; {'Avst', 'Orkh'}
    0x2E31,  # .. 0x2E31 ; {'Avst', 'Cari', 'Geor', 'Hung', 'Kthi', 'Lydi', 'Samr'}
    0x2E32,  # .. 0x2E3B ; None
    0x2E3C,  # .. 0x2E3C ; {'Dupl'}
    0x2E3D,  # .. 0x2E40 ; None
    0x2E41,  # .. 0x2E41 ; {'Adlm', 'Arab', 'Hung'}
    0x2E42,  # .. 0x2E42 ; None
    0x2E43,  # .. 0x2E43 ; {'Cyrl', 'Glag'}
    0x2E44,  # .. 0x2FEF ; None
    0x2FF0,  # .. 0x2FFF ; {'Hani', 'Tang'}
    0x3000,  # .. 0x3000 ; None
    0x3001,  # .. 0x3001 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Mong', 'Yiii'}
    0x3002,  # .. 0x3002 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Mong', 'Phag', 'Yiii'}
    0x3003,  # .. 0x3003 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0x3004,  # .. 0x3005 ; None
    0x3006,  # .. 0x3006 ; {'Hani'}
    0x3007,  # .. 0x3007 ; None
    0x3008,  # .. 0x3009 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Mong', 'Tibt', 'Yiii'}
    0x300A,  # .. 0x300B ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Lisu', 'Mong', 'Tibt', 'Yiii'}
    0x300C,  # .. 0x3011 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Yiii'}
    0x3012,  # .. 0x3012 ; None
    0x3013,  # .. 0x3013 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0x3014,  # .. 0x301B ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Yiii'}
    0x301C,  # .. 0x301F ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0x3020,  # .. 0x3029 ; None
    0x302A,  # .. 0x302D ; {'Bopo', 'Hani'}
    0x302E,  # .. 0x302F ; None
    0x3030,  # .. 0x3030 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0x3031,  # .. 0x3035 ; {'Hira', 'Kana'}
    0x3036,  # .. 0x3036 ; None
    0x3037,  # .. 0x3037 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0x3038,  # .. 0x303B ; None
    0x303C,  # .. 0x303D ; {'Hani', 'Hira', 'Kana'}
    0x303E,  # .. 0x303F ; {'Hani'}
    0x3040,  # .. 0x3098 ; None
    0x3099,  # .. 0x309C ; {'Hira', 'Kana'}
    0x309D,  # .. 0x309F ; None
    0x30A0,  # .. 0x30A0 ; {'Hira', 'Kana'}
    0x30A1,  # .. 0x30FA ; None
    0x30FB,  # .. 0x30FB ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Yiii'}
    0x30FC,  # .. 0x30FC ; {'Hira', 'Kana'}
    0x30FD,  # .. 0x318F ; None
    0x3190,  # .. 0x319F ; {'Hani'}
    0x31A0,  # .. 0x31BF ; None
    0x31C0,  # .. 0x31E5 ; {'Hani'}
    0x31E6,  # .. 0x31EE ; None
    0x31EF,  # .. 0x31EF ; {'Hani', 'Tang'}
    0x31F0,  # .. 0x321F ; None
    0x3220,  # .. 0x3247 ; {'Hani'}
    0x3248,  # .. 0x327F ; None
    0x3280,  # .. 0x32B0 ; {'Hani'}
    0x32B1,  # .. 0x32BF ; None
    0x32C0,  # .. 0x32CB ; {'Hani'}
    0x32CC,  # .. 0x32FE ; None
    0x32FF,  # .. 0x32FF ; {'Hani'}
    0x3300,  # .. 0x3357 ; None
    0x3358,  # .. 0x3370 ; {'Hani'}
    0x3371,  # .. 0x337A ; None
    0x337B,  # .. 0x337F ; {'Hani'}
    0x3380,  # .. 0x33DF ; None
    0x33E0,  # .. 0x33FE ; {'Hani'}
    0x33FF,  # .. 0xA66E ; None
    0xA66F,  # .. 0xA66F ; {'Cyrl', 'Glag'}
    0xA670,  # .. 0xA6FF ; None
    0xA700,  # .. 0xA707 ; {'Hani', 'Latn'}
    0xA708,  # .. 0xA82F ; None
    0xA830,  # .. 0xA832 ; {'Deva', 'Dogr', 'Gujr', 'Guru', 'Khoj', 'Knda', 'Kthi', 'Mahj', 'Mlym', 'Modi', 'Nand', 'Shrd', 'Sind', 'Takr', 'Tirh', 'Tutg'}
    0xA833,  # .. 0xA835 ; {'Deva', 'Dogr', 'Gujr', 'Guru', 'Khoj', 'Knda', 'Kthi', 'Mahj', 'Modi', 'Nand', 'Shrd', 'Sind', 'Takr', 'Tirh', 'Tutg'}
    0xA836,  # .. 0xA837 ; {'Deva', 'Dogr', 'Gujr', 'Guru', 'Khoj', 'Kthi', 'Mahj', 'Modi', 'Sind', 'Takr', 'Tirh'}
    0xA838,  # .. 0xA838 ; {'Deva', 'Dogr', 'Gujr', 'Guru', 'Khoj', 'Kthi', 'Mahj', 'Modi', 'Shrd', 'Sind', 'Takr', 'Tirh'}
    0xA839,  # .. 0xA839 ; {'Deva', 'Dogr', 'Gujr', 'Guru', 'Khoj', 'Kthi', 'Mahj', 'Modi', 'Sind', 'Takr', 'Tirh'}
    0xA83A,  # .. 0xA8F0 ; None
    0xA8F1,  # .. 0xA8F1 ; {'Beng', 'Deva', 'Tutg'}
    0xA8F2,  # .. 0xA8F2 ; None
    0xA8F3,  # .. 0xA8F3 ; {'Deva', 'Taml'}
    0xA8F4,  # .. 0xA92D ; None
    0xA92E,  # .. 0xA92E ; {'Kali', 'Latn', 'Mymr'}
    0xA92F,  # .. 0xA9CE ; None
    0xA9CF,  # .. 0xA9CF ; {'Bugi', 'Java'}
    0xA9D0,  # .. 0xFD3D ; None
    0xFD3E,  # .. 0xFD3F ; {'Arab', 'Nkoo'}
    0xFD40,  # .. 0xFDF1 ; None
    0xFDF2,  # .. 0xFDF2 ; {'Arab', 'Thaa'}
    0xFDF3,  # .. 0xFDFC ; None
    0xFDFD,  # .. 0xFDFD ; {'Arab', 'Thaa'}
    0xFDFE,  # .. 0xFE44 ; None
    0xFE45,  # .. 0xFE46 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana'}
    0xFE47,  # .. 0xFF60 ; None
    0xFF61,  # .. 0xFF65 ; {'Bopo', 'Hang', 'Hani', 'Hira', 'Kana', 'Yiii'}
    0xFF66,  # .. 0xFF6F ; None
    0xFF70,  # .. 0xFF70 ; {'Hira', 'Kana'}
    0xFF71,  # .. 0xFF9D ; None
    0xFF9E,  # .. 0xFF9F ; {'Hira', 'Kana'}
    0xFFA0,  # .. 0x100FF ; None
    0x10100,  # .. 0x10101 ; {'Cpmn', 'Cprt', 'Linb'}
    0x10102,  # .. 0x10102 ; {'Cprt', 'Linb'}
    0x10103,  # .. 0x10106 ; None
    0x10107,  # .. 0x10133 ; {'Cprt', 'Lina', 'Linb'}
    0x10134,  # .. 0x10136 ; None
    0x10137,  # .. 0x1013F ; {'Cprt', 'Linb'}
    0x10140,  # .. 0x102DF ; None
    0x102E0,  # .. 0x102FB ; {'Arab', 'Copt'}
    0x102FC,  # .. 0x10AF1 ; None
    0x10AF2,  # .. 0x10AF2 ; {'Mani', 'Ougr'}
    0x10AF3,  # .. 0x11300 ; None
    0x11301,  # .. 0x11301 ; {'Gran', 'Taml'}
    0x11302,  # .. 0x11302 ; None
    0x11303,  # .. 0x11303 ; {'Gran', 'Taml'}
    0x11304,  # .. 0x1133A ; None
    0x1133B,  # .. 0x1133C ; {'Gran', 'Taml'}
    0x1133D,  # .. 0x11FCF ; None
    0x11FD0,  # .. 0x11FD1 ; {'Gran', 'Taml'}
    0x11FD2,  # .. 0x11FD2 ; None
    0x11FD3,  # .. 0x11FD3 ; {'Gran', 'Taml'}
    0x11FD4,  # .. 0x1BC9F ; None
    0x1BCA0,  # .. 0x1BCA3 ; {'Dupl'}
    0x1BCA4,  # .. 0x1D35F ; None
    0x1D360,  # .. 0x1D371 ; {'Hani'}
    0x1D372,  # .. 0x1F24F ; None
    0x1F250,  # .. 0x1F251 ; {'Hani'}
    0x1F252,  # .. 0x10FFFF ; None
]

VALUES = [
    None,  # 0000..00B6
    {
        "Avst",
        "Cari",
        "Copt",
        "Dupl",
        "Elba",
        "Geor",
        "Glag",
        "Gong",
        "Goth",
        "Grek",
        "Hani",
        "Latn",
        "Lydi",
        "Mahj",
        "Perm",
        "Shaw",
    },  # 00B7..00B7
    None,  # 00B8..02BB
    {"Beng", "Cyrl", "Deva", "Latn", "Lisu", "Thai", "Toto"},  # 02BC..02BC
    None,  # 02BD..02C6
    {"Bopo", "Latn"},  # 02C7..02C7
    None,  # 02C8..02C8
    {"Bopo", "Latn"},  # 02C9..02CB
    None,  # 02CC..02CC
    {"Latn", "Lisu"},  # 02CD..02CD
    None,  # 02CE..02D6
    {"Latn", "Thai"},  # 02D7..02D7
    None,  # 02D8..02D8
    {"Bopo", "Latn"},  # 02D9..02D9
    None,  # 02DA..02FF
    {"Cher", "Copt", "Cyrl", "Grek", "Latn", "Perm", "Sunu", "Tale"},  # 0300..0300
    {"Cher", "Cyrl", "Grek", "Latn", "Osge", "Sunu", "Tale", "Todr"},  # 0301..0301
    {"Cher", "Cyrl", "Latn", "Tfng"},  # 0302..0302
    {"Glag", "Latn", "Sunu", "Syrc", "Thai"},  # 0303..0303
    {
        "Aghb",
        "Cher",
        "Copt",
        "Cyrl",
        "Goth",
        "Grek",
        "Latn",
        "Osge",
        "Syrc",
        "Tfng",
        "Todr",
    },  # 0304..0304
    {"Copt", "Elba", "Glag", "Goth", "Kana", "Latn"},  # 0305..0305
    {"Cyrl", "Grek", "Latn", "Perm"},  # 0306..0306
    {
        "Copt",
        "Dupl",
        "Hebr",
        "Latn",
        "Perm",
        "Syrc",
        "Tale",
        "Tfng",
        "Todr",
    },  # 0307..0307
    {
        "Armn",
        "Cyrl",
        "Dupl",
        "Goth",
        "Grek",
        "Hebr",
        "Latn",
        "Perm",
        "Syrc",
        "Tale",
    },  # 0308..0308
    {"Latn", "Tfng"},  # 0309..0309
    {"Dupl", "Latn", "Syrc"},  # 030A..030A
    {"Cher", "Cyrl", "Latn", "Osge"},  # 030B..030B
    {"Cher", "Latn", "Tale"},  # 030C..030C
    {"Latn", "Sunu"},  # 030D..030D
    {"Ethi", "Latn"},  # 030E..030E
    None,  # 030F..030F
    {"Latn", "Sunu"},  # 0310..0310
    {"Cyrl", "Latn", "Todr"},  # 0311..0311
    None,  # 0312..0312
    {"Grek", "Latn", "Perm", "Todr"},  # 0313..0313
    None,  # 0314..031F
    {"Latn", "Syrc"},  # 0320..0320
    None,  # 0321..0322
    {"Cher", "Dupl", "Kana", "Latn", "Syrc"},  # 0323..0323
    {"Cher", "Dupl", "Latn", "Syrc"},  # 0324..0324
    {"Latn", "Syrc"},  # 0325..0325
    None,  # 0326..032C
    {"Latn", "Sunu", "Syrc"},  # 032D..032D
    {"Latn", "Syrc"},  # 032E..032E
    None,  # 032F..032F
    {"Cher", "Latn", "Syrc"},  # 0330..0330
    {"Aghb", "Cher", "Goth", "Latn", "Sunu", "Thai"},  # 0331..0331
    None,  # 0332..0341
    {"Grek"},  # 0342..0342
    None,  # 0343..0344
    {"Grek"},  # 0345..0345
    None,  # 0346..0357
    {"Latn", "Osge"},  # 0358..0358
    None,  # 0359..035D
    {"Aghb", "Latn", "Todr"},  # 035E..035E
    None,  # 035F..0362
    {"Latn"},  # 0363..036F
    None,  # 0370..0373
    {"Copt", "Grek"},  # 0374..0375
    None,  # 0376..0482
    {"Cyrl", "Perm"},  # 0483..0483
    {"Cyrl", "Glag"},  # 0484..0484
    {"Cyrl", "Latn"},  # 0485..0486
    {"Cyrl", "Glag"},  # 0487..0487
    None,  # 0488..0588
    {"Armn", "Geor", "Glag"},  # 0589..0589
    None,  # 058A..060B
    {"Arab", "Gara", "Nkoo", "Rohg", "Syrc", "Thaa", "Yezi"},  # 060C..060C
    None,  # 060D..061A
    {"Arab", "Gara", "Nkoo", "Rohg", "Syrc", "Thaa", "Yezi"},  # 061B..061B
    {"Arab", "Syrc", "Thaa"},  # 061C..061C
    None,  # 061D..061E
    {"Adlm", "Arab", "Gara", "Nkoo", "Rohg", "Syrc", "Thaa", "Yezi"},  # 061F..061F
    None,  # 0620..063F
    {
        "Adlm",
        "Arab",
        "Mand",
        "Mani",
        "Ougr",
        "Phlp",
        "Rohg",
        "Sogd",
        "Syrc",
    },  # 0640..0640
    None,  # 0641..064A
    {"Arab", "Syrc"},  # 064B..0655
    None,  # 0656..065F
    {"Arab", "Thaa", "Yezi"},  # 0660..0669
    None,  # 066A..066F
    {"Arab", "Syrc"},  # 0670..0670
    None,  # 0671..06D3
    {"Arab", "Rohg"},  # 06D4..06D4
    None,  # 06D5..0950
    {
        "Beng",
        "Deva",
        "Gran",
        "Gujr",
        "Guru",
        "Knda",
        "Latn",
        "Mlym",
        "Orya",
        "Shrd",
        "Taml",
        "Telu",
        "Tirh",
    },  # 0951..0951
    {
        "Beng",
        "Deva",
        "Gran",
        "Gujr",
        "Guru",
        "Knda",
        "Latn",
        "Mlym",
        "Orya",
        "Taml",
        "Telu",
        "Tirh",
    },  # 0952..0952
    None,  # 0953..0963
    {
        "Beng",
        "Deva",
        "Dogr",
        "Gong",
        "Gonm",
        "Gran",
        "Gujr",
        "Guru",
        "Knda",
        "Mahj",
        "Mlym",
        "Nand",
        "Onao",
        "Orya",
        "Sind",
        "Sinh",
        "Sylo",
        "Takr",
        "Taml",
        "Telu",
        "Tirh",
    },  # 0964..0964
    {
        "Beng",
        "Deva",
        "Dogr",
        "Gong",
        "Gonm",
        "Gran",
        "Gujr",
        "Gukh",
        "Guru",
        "Knda",
        "Limb",
        "Mahj",
        "Mlym",
        "Nand",
        "Onao",
        "Orya",
        "Sind",
        "Sinh",
        "Sylo",
        "Takr",
        "Taml",
        "Telu",
        "Tirh",
    },  # 0965..0965
    {"Deva", "Dogr", "Kthi", "Mahj"},  # 0966..096F
    None,  # 0970..09E5
    {"Beng", "Cakm", "Sylo"},  # 09E6..09EF
    None,  # 09F0..0A65
    {"Guru", "Mult"},  # 0A66..0A6F
    None,  # 0A70..0AE5
    {"Gujr", "Khoj"},  # 0AE6..0AEF
    None,  # 0AF0..0BE5
    {"Gran", "Taml"},  # 0BE6..0BF3
    None,  # 0BF4..0CE5
    {"Knda", "Nand", "Tutg"},  # 0CE6..0CEF
    None,  # 0CF0..103F
    {"Cakm", "Mymr", "Tale"},  # 1040..1049
    None,  # 104A..10FA
    {"Geor", "Glag", "Latn"},  # 10FB..10FB
    None,  # 10FC..16EA
    {"Runr"},  # 16EB..16ED
    None,  # 16EE..1734
    {"Buhd", "Hano", "Tagb", "Tglg"},  # 1735..1736
    None,  # 1737..1801
    {"Mong", "Phag"},  # 1802..1803
    None,  # 1804..1804
    {"Mong", "Phag"},  # 1805..1805
    None,  # 1806..1CCF
    {"Beng", "Deva", "Gran", "Knda"},  # 1CD0..1CD0
    {"Deva"},  # 1CD1..1CD1
    {"Beng", "Deva", "Gran", "Knda"},  # 1CD2..1CD2
    {"Deva", "Gran", "Knda"},  # 1CD3..1CD3
    {"Deva"},  # 1CD4..1CD4
    {"Beng", "Deva"},  # 1CD5..1CD6
    {"Deva", "Shrd"},  # 1CD7..1CD7
    {"Beng", "Deva"},  # 1CD8..1CD8
    {"Deva", "Shrd"},  # 1CD9..1CD9
    {"Deva", "Knda", "Mlym", "Orya", "Taml", "Telu"},  # 1CDA..1CDA
    {"Deva"},  # 1CDB..1CDB
    {"Deva", "Shrd"},  # 1CDC..1CDD
    {"Deva"},  # 1CDE..1CDF
    {"Deva", "Shrd"},  # 1CE0..1CE0
    {"Beng", "Deva"},  # 1CE1..1CE1
    {"Deva"},  # 1CE2..1CE8
    {"Deva", "Nand"},  # 1CE9..1CE9
    {"Beng", "Deva"},  # 1CEA..1CEA
    {"Deva"},  # 1CEB..1CEC
    {"Beng", "Deva"},  # 1CED..1CED
    {"Deva"},  # 1CEE..1CF1
    {
        "Beng",
        "Deva",
        "Gran",
        "Knda",
        "Mlym",
        "Nand",
        "Orya",
        "Sinh",
        "Telu",
        "Tirh",
        "Tutg",
    },  # 1CF2..1CF2
    {"Deva", "Gran"},  # 1CF3..1CF3
    {"Deva", "Gran", "Knda", "Tutg"},  # 1CF4..1CF4
    {"Beng", "Deva"},  # 1CF5..1CF6
    {"Beng"},  # 1CF7..1CF7
    {"Deva", "Gran"},  # 1CF8..1CF9
    {"Nand"},  # 1CFA..1CFA
    None,  # 1CFB..1DBF
    {"Grek"},  # 1DC0..1DC1
    None,  # 1DC2..1DF7
    {"Cyrl", "Latn", "Syrc"},  # 1DF8..1DF8
    None,  # 1DF9..1DF9
    {"Syrc"},  # 1DFA..1DFA
    None,  # 1DFB..202E
    {"Latn", "Mong", "Phag"},  # 202F..202F
    None,  # 2030..204E
    {"Adlm", "Arab"},  # 204F..204F
    None,  # 2050..2059
    {"Cari", "Geor", "Glag", "Hung", "Lyci", "Orkh"},  # 205A..205A
    None,  # 205B..205C
    {"Cari", "Grek", "Hung", "Mero"},  # 205D..205D
    None,  # 205E..20EF
    {"Deva", "Gran", "Latn"},  # 20F0..20F0
    None,  # 20F1..2E16
    {"Copt", "Latn"},  # 2E17..2E17
    None,  # 2E18..2E2F
    {"Avst", "Orkh"},  # 2E30..2E30
    {"Avst", "Cari", "Geor", "Hung", "Kthi", "Lydi", "Samr"},  # 2E31..2E31
    None,  # 2E32..2E3B
    {"Dupl"},  # 2E3C..2E3C
    None,  # 2E3D..2E40
    {"Adlm", "Arab", "Hung"},  # 2E41..2E41
    None,  # 2E42..2E42
    {"Cyrl", "Glag"},  # 2E43..2E43
    None,  # 2E44..2FEF
    {"Hani", "Tang"},  # 2FF0..2FFF
    None,  # 3000..3000
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Mong", "Yiii"},  # 3001..3001
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Mong", "Phag", "Yiii"},  # 3002..3002
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # 3003..3003
    None,  # 3004..3005
    {"Hani"},  # 3006..3006
    None,  # 3007..3007
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Mong", "Tibt", "Yiii"},  # 3008..3009
    {
        "Bopo",
        "Hang",
        "Hani",
        "Hira",
        "Kana",
        "Lisu",
        "Mong",
        "Tibt",
        "Yiii",
    },  # 300A..300B
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Yiii"},  # 300C..3011
    None,  # 3012..3012
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # 3013..3013
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Yiii"},  # 3014..301B
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # 301C..301F
    None,  # 3020..3029
    {"Bopo", "Hani"},  # 302A..302D
    None,  # 302E..302F
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # 3030..3030
    {"Hira", "Kana"},  # 3031..3035
    None,  # 3036..3036
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # 3037..3037
    None,  # 3038..303B
    {"Hani", "Hira", "Kana"},  # 303C..303D
    {"Hani"},  # 303E..303F
    None,  # 3040..3098
    {"Hira", "Kana"},  # 3099..309C
    None,  # 309D..309F
    {"Hira", "Kana"},  # 30A0..30A0
    None,  # 30A1..30FA
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Yiii"},  # 30FB..30FB
    {"Hira", "Kana"},  # 30FC..30FC
    None,  # 30FD..318F
    {"Hani"},  # 3190..319F
    None,  # 31A0..31BF
    {"Hani"},  # 31C0..31E5
    None,  # 31E6..31EE
    {"Hani", "Tang"},  # 31EF..31EF
    None,  # 31F0..321F
    {"Hani"},  # 3220..3247
    None,  # 3248..327F
    {"Hani"},  # 3280..32B0
    None,  # 32B1..32BF
    {"Hani"},  # 32C0..32CB
    None,  # 32CC..32FE
    {"Hani"},  # 32FF..32FF
    None,  # 3300..3357
    {"Hani"},  # 3358..3370
    None,  # 3371..337A
    {"Hani"},  # 337B..337F
    None,  # 3380..33DF
    {"Hani"},  # 33E0..33FE
    None,  # 33FF..A66E
    {"Cyrl", "Glag"},  # A66F..A66F
    None,  # A670..A6FF
    {"Hani", "Latn"},  # A700..A707
    None,  # A708..A82F
    {
        "Deva",
        "Dogr",
        "Gujr",
        "Guru",
        "Khoj",
        "Knda",
        "Kthi",
        "Mahj",
        "Mlym",
        "Modi",
        "Nand",
        "Shrd",
        "Sind",
        "Takr",
        "Tirh",
        "Tutg",
    },  # A830..A832
    {
        "Deva",
        "Dogr",
        "Gujr",
        "Guru",
        "Khoj",
        "Knda",
        "Kthi",
        "Mahj",
        "Modi",
        "Nand",
        "Shrd",
        "Sind",
        "Takr",
        "Tirh",
        "Tutg",
    },  # A833..A835
    {
        "Deva",
        "Dogr",
        "Gujr",
        "Guru",
        "Khoj",
        "Kthi",
        "Mahj",
        "Modi",
        "Sind",
        "Takr",
        "Tirh",
    },  # A836..A837
    {
        "Deva",
        "Dogr",
        "Gujr",
        "Guru",
        "Khoj",
        "Kthi",
        "Mahj",
        "Modi",
        "Shrd",
        "Sind",
        "Takr",
        "Tirh",
    },  # A838..A838
    {
        "Deva",
        "Dogr",
        "Gujr",
        "Guru",
        "Khoj",
        "Kthi",
        "Mahj",
        "Modi",
        "Sind",
        "Takr",
        "Tirh",
    },  # A839..A839
    None,  # A83A..A8F0
    {"Beng", "Deva", "Tutg"},  # A8F1..A8F1
    None,  # A8F2..A8F2
    {"Deva", "Taml"},  # A8F3..A8F3
    None,  # A8F4..A92D
    {"Kali", "Latn", "Mymr"},  # A92E..A92E
    None,  # A92F..A9CE
    {"Bugi", "Java"},  # A9CF..A9CF
    None,  # A9D0..FD3D
    {"Arab", "Nkoo"},  # FD3E..FD3F
    None,  # FD40..FDF1
    {"Arab", "Thaa"},  # FDF2..FDF2
    None,  # FDF3..FDFC
    {"Arab", "Thaa"},  # FDFD..FDFD
    None,  # FDFE..FE44
    {"Bopo", "Hang", "Hani", "Hira", "Kana"},  # FE45..FE46
    None,  # FE47..FF60
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Yiii"},  # FF61..FF65
    None,  # FF66..FF6F
    {"Hira", "Kana"},  # FF70..FF70
    None,  # FF71..FF9D
    {"Hira", "Kana"},  # FF9E..FF9F
    None,  # FFA0..100FF
    {"Cpmn", "Cprt", "Linb"},  # 10100..10101
    {"Cprt", "Linb"},  # 10102..10102
    None,  # 10103..10106
    {"Cprt", "Lina", "Linb"},  # 10107..10133
    None,  # 10134..10136
    {"Cprt", "Linb"},  # 10137..1013F
    None,  # 10140..102DF
    {"Arab", "Copt"},  # 102E0..102FB
    None,  # 102FC..10AF1
    {"Mani", "Ougr"},  # 10AF2..10AF2
    None,  # 10AF3..11300
    {"Gran", "Taml"},  # 11301..11301
    None,  # 11302..11302
    {"Gran", "Taml"},  # 11303..11303
    None,  # 11304..1133A
    {"Gran", "Taml"},  # 1133B..1133C
    None,  # 1133D..11FCF
    {"Gran", "Taml"},  # 11FD0..11FD1
    None,  # 11FD2..11FD2
    {"Gran", "Taml"},  # 11FD3..11FD3
    None,  # 11FD4..1BC9F
    {"Dupl"},  # 1BCA0..1BCA3
    None,  # 1BCA4..1D35F
    {"Hani"},  # 1D360..1D371
    None,  # 1D372..1F24F
    {"Hani"},  # 1F250..1F251
    None,  # 1F252..10FFFF
]

# === NexusCore/openenv\Lib\site-packages\win32com\client\gencache.py ===
"""Manages the cache of generated Python code.

Description
  This file manages the cache of generated Python code.  When run from the
  command line, it also provides a number of options for managing that cache.

Implementation
  Each typelib is generated into a filename of format "{guid}x{lcid}x{major}x{minor}.py"

  An external persistant dictionary maps from all known IIDs in all known type libraries
  to the type library itself.

  Thus, whenever Python code knows the IID of an object, it can find the IID, LCID and version of
  the type library which supports it.  Given this information, it can find the Python module
  with the support.

  If necessary, this support can be generated on the fly.

Hacks, to do, etc
  Currently just uses a pickled dictionary, but should used some sort of indexed file.
  Maybe an OLE2 compound file, or a bsddb file?
"""

from __future__ import annotations

import contextlib
import glob
import os
import sys
from importlib import reload
from types import ModuleType
from typing import Any

import pythoncom
import pywintypes
import win32com
import win32com.client
import win32event

from . import CLSIDToClass

bForDemandDefault = 0  # Default value of bForDemand - toggle this to change the world - see also makepy.py

# The global dictionary
clsidToTypelib: dict[str, tuple[str, int, int, int]] = {}

# If we have a different version of the typelib generated, this
# maps the "requested version" to the "generated version".
versionRedirectMap: dict[tuple[str, int, int, int], ModuleType | None] = {}

# There is no reason we *must* be readonly in a .zip, but we are now,
# Rather than check for ".zip" or other tricks, PEP302 defines
# a "__loader__" attribute, so we use that.
# (Later, it may become necessary to check if the __loader__ can update files,
# as a .zip loader potentially could - but punt all that until a need arises)
is_readonly = is_zip = hasattr(win32com, "__loader__") and hasattr(
    win32com.__loader__, "archive"
)

# A dictionary of ITypeLibrary objects for demand generation explicitly handed to us
# Keyed by usual clsid, lcid, major, minor
# Typing as Any because PyITypeLib is not exposed
demandGeneratedTypeLibraries: dict[tuple[str, int, int, int], Any] = {}

import pickle


def __init__():
    # Initialize the module.  Called once explicitly at module import below.
    try:
        _LoadDicts()
    except OSError:
        Rebuild()


pickleVersion = 1


def _SaveDicts():
    if is_readonly:
        raise RuntimeError(
            "Trying to write to a readonly gencache ('%s')!" % win32com.__gen_path__
        )
    f = open(os.path.join(GetGeneratePath(), "dicts.dat"), "wb")
    try:
        p = pickle.Pickler(f)
        p.dump(pickleVersion)
        p.dump(clsidToTypelib)
    finally:
        f.close()


def _LoadDicts():
    # Load the dictionary from a .zip file if that is where we live.
    if is_zip:
        import io

        loader = win32com.__loader__
        arc_path = loader.archive
        dicts_path = os.path.join(win32com.__gen_path__, "dicts.dat")
        if dicts_path.startswith(arc_path):
            dicts_path = dicts_path[len(arc_path) + 1 :]
        else:
            # Hm. See below.
            return
        try:
            data = loader.get_data(dicts_path)
        except AttributeError:
            # The __loader__ has no get_data method.  See below.
            return
        except OSError:
            # Our gencache is in a .zip file (and almost certainly readonly)
            # but no dicts file.  That actually needn't be fatal for a frozen
            # application.  Assuming they call "EnsureModule" with the same
            # typelib IDs they have been frozen with, that EnsureModule will
            # correctly re-build the dicts on the fly.  However, objects that
            # rely on the gencache but have not done an EnsureModule will
            # fail (but their apps are likely to fail running from source
            # with a clean gencache anyway, as then they would be getting
            # Dynamic objects until the cache is built - so the best answer
            # for these apps is to call EnsureModule, rather than freezing
            # the dict)
            return
        f = io.BytesIO(data)
    else:
        # NOTE: OSError on file open must be caught by caller.
        f = open(os.path.join(win32com.__gen_path__, "dicts.dat"), "rb")
    try:
        p = pickle.Unpickler(f)
        version = p.load()
        global clsidToTypelib
        clsidToTypelib = p.load()
        versionRedirectMap.clear()
    finally:
        f.close()


@contextlib.contextmanager
def ModuleMutex(module_name):
    """Given the output of GetGeneratedFilename, acquire a named mutex for that module

    This is required so that writes (generation) don't interfere with each other and with reads (import)
    """
    mutex = win32event.CreateMutex(None, False, module_name)
    with contextlib.closing(mutex):
        # acquire mutex
        win32event.WaitForSingleObject(mutex, win32event.INFINITE)
        try:
            yield
        finally:
            win32event.ReleaseMutex(mutex)


def GetGeneratedFileName(clsid, lcid, major, minor):
    """Given the clsid, lcid, major and  minor for a type lib, return
    the file name (no extension) providing this support.
    """
    return str(clsid).upper()[1:-1] + f"x{lcid}x{major}x{minor}"


def SplitGeneratedFileName(fname):
    """Reverse of GetGeneratedFileName()"""
    return tuple(fname.split("x", 4))


def GetGeneratePath():
    """Returns the name of the path to generate to.
    Checks the directory is OK.
    """
    assert not is_readonly, "Why do you want the genpath for a readonly store?"
    try:
        os.makedirs(win32com.__gen_path__)
        # os.mkdir(win32com.__gen_path__)
    except OSError:
        pass
    try:
        fname = os.path.join(win32com.__gen_path__, "__init__.py")
        os.stat(fname)
    except OSError:
        f = open(fname, "w")
        f.write(
            "# Generated file - this directory may be deleted to reset the COM cache...\n"
        )
        f.write("import win32com\n")
        f.write(
            "if __path__[:-1] != win32com.__gen_path__: __path__.append(win32com.__gen_path__)\n"
        )
        f.close()

    return win32com.__gen_path__


#
# The helpers for win32com.client.Dispatch and OCX clients.
#
def GetClassForProgID(progid):
    """Get a Python class for a Program ID

    Given a Program ID, return a Python class which wraps the COM object

    Returns the Python class, or None if no module is available.

    Params
    progid -- A COM ProgramID or IID (eg, "Word.Application")
    """
    clsid = pywintypes.IID(progid)  # This auto-converts named to IDs.
    return GetClassForCLSID(clsid)


def GetClassForCLSID(clsid):
    """Get a Python class for a CLSID

    Given a CLSID, return a Python class which wraps the COM object

    Returns the Python class, or None if no module is available.

    Params
    clsid -- A COM CLSID (or string repr of one)
    """
    # first, take a short-cut - we may already have generated support ready-to-roll.
    clsid = str(clsid)
    if CLSIDToClass.HasClass(clsid):
        return CLSIDToClass.GetClass(clsid)
    mod = GetModuleForCLSID(clsid)
    if mod is None:
        return None
    try:
        return CLSIDToClass.GetClass(clsid)
    except KeyError:
        return None


def GetModuleForProgID(progid):
    """Get a Python module for a Program ID

    Given a Program ID, return a Python module which contains the
    class which wraps the COM object.

    Returns the Python module, or None if no module is available.

    Params
    progid -- A COM ProgramID or IID (eg, "Word.Application")
    """
    try:
        iid = pywintypes.IID(progid)
    except pywintypes.com_error:
        return None
    return GetModuleForCLSID(iid)


def GetModuleForCLSID(clsid):
    """Get a Python module for a CLSID

    Given a CLSID, return a Python module which contains the
    class which wraps the COM object.

    Returns the Python module, or None if no module is available.

    Params
    progid -- A COM CLSID (ie, not the description)
    """
    clsid_str = str(clsid)
    try:
        typelibCLSID, lcid, major, minor = clsidToTypelib[clsid_str]
    except KeyError:
        return None

    try:
        mod = GetModuleForTypelib(typelibCLSID, lcid, major, minor)
    except ImportError:
        mod = None
    if mod is not None:
        sub_mod = mod.CLSIDToPackageMap.get(clsid_str)
        if sub_mod is None:
            sub_mod = mod.VTablesToPackageMap.get(clsid_str)
        if sub_mod is not None:
            sub_mod_name = mod.__name__ + "." + sub_mod
            try:
                with ModuleMutex(mod.__name__.split(".")[-1]):
                    __import__(sub_mod_name)
            except ImportError:
                info = typelibCLSID, lcid, major, minor
                # Force the generation.  If this typelibrary has explicitly been added,
                # use it (it may not be registered, causing a lookup by clsid to fail)
                if info in demandGeneratedTypeLibraries:
                    info = demandGeneratedTypeLibraries[info]
                from . import makepy

                makepy.GenerateChildFromTypeLibSpec(sub_mod, info)
                # Generate does an import...
            mod = sys.modules[sub_mod_name]
    return mod


def GetModuleForTypelib(typelibCLSID, lcid, major, minor):
    """Get a Python module for a type library ID

    Given the CLSID of a typelibrary, return an imported Python module,
    else None

    Params
    typelibCLSID -- IID of the type library.
    major -- Integer major version.
    minor -- Integer minor version
    lcid -- Integer LCID for the library.
    """
    modName = GetGeneratedFileName(typelibCLSID, lcid, major, minor)
    mod = _GetModule(modName)
    # If the import worked, it doesn't mean we have actually added this
    # module to our cache though - check that here.
    if "_in_gencache_" not in mod.__dict__:
        AddModuleToCache(typelibCLSID, lcid, major, minor)
        assert "_in_gencache_" in mod.__dict__
    return mod


def MakeModuleForTypelib(
    typelibCLSID,
    lcid,
    major,
    minor,
    progressInstance=None,
    bForDemand=bForDemandDefault,
    bBuildHidden=1,
):
    """Generate support for a type library.

    Given the IID, LCID and version information for a type library, generate
    and import the necessary support files.

    Returns the Python module.  No exceptions are caught.

    Params
    typelibCLSID -- IID of the type library.
    major -- Integer major version.
    minor -- Integer minor version.
    lcid -- Integer LCID for the library.
    progressInstance -- Instance to use as progress indicator, or None to
                        use the GUI progress bar.
    """
    from . import makepy

    makepy.GenerateFromTypeLibSpec(
        (typelibCLSID, lcid, major, minor),
        progressInstance=progressInstance,
        bForDemand=bForDemand,
        bBuildHidden=bBuildHidden,
    )
    return GetModuleForTypelib(typelibCLSID, lcid, major, minor)


def MakeModuleForTypelibInterface(
    typelib_ob, progressInstance=None, bForDemand=bForDemandDefault, bBuildHidden=1
):
    """Generate support for a type library.

    Given a PyITypeLib interface generate and import the necessary support files.  This is useful
    for getting makepy support for a typelibrary that is not registered - the caller can locate
    and load the type library itself, rather than relying on COM to find it.

    Returns the Python module.

    Params
    typelib_ob -- The type library itself
    progressInstance -- Instance to use as progress indicator, or None to
                        use the GUI progress bar.
    """
    from . import makepy

    try:
        makepy.GenerateFromTypeLibSpec(
            typelib_ob,
            progressInstance=progressInstance,
            bForDemand=bForDemandDefault,
            bBuildHidden=bBuildHidden,
        )
    except pywintypes.com_error:
        return None
    tla = typelib_ob.GetLibAttr()
    guid = tla[0]
    lcid = tla[1]
    major = tla[3]
    minor = tla[4]
    return GetModuleForTypelib(guid, lcid, major, minor)


def EnsureModuleForTypelibInterface(
    typelib_ob, progressInstance=None, bForDemand=bForDemandDefault, bBuildHidden=1
):
    """Check we have support for a type library, generating if not.

    Given a PyITypeLib interface generate and import the necessary
    support files if necessary. This is useful for getting makepy support
    for a typelibrary that is not registered - the caller can locate and
    load the type library itself, rather than relying on COM to find it.

    Returns the Python module.

    Params
    typelib_ob -- The type library itself
    progressInstance -- Instance to use as progress indicator, or None to
                        use the GUI progress bar.
    """
    tla = typelib_ob.GetLibAttr()
    guid = tla[0]
    lcid = tla[1]
    major = tla[3]
    minor = tla[4]

    # If demand generated, save the typelib interface away for later use
    if bForDemand:
        demandGeneratedTypeLibraries[(str(guid), lcid, major, minor)] = typelib_ob

    try:
        return GetModuleForTypelib(guid, lcid, major, minor)
    except ImportError:
        pass
    # Generate it.
    return MakeModuleForTypelibInterface(
        typelib_ob, progressInstance, bForDemand, bBuildHidden
    )


def ForgetAboutTypelibInterface(typelib_ob):
    """Drop any references to a typelib previously added with EnsureModuleForTypelibInterface and forDemand"""
    tla = typelib_ob.GetLibAttr()
    guid = tla[0]
    lcid = tla[1]
    major = tla[3]
    minor = tla[4]
    info = str(guid), lcid, major, minor
    try:
        del demandGeneratedTypeLibraries[info]
    except KeyError:
        # Not worth raising an exception - maybe they don't know we only remember for demand generated, etc.
        print(
            "ForgetAboutTypelibInterface:: Warning - type library with info {} is not being remembered!".format(
                info
            )
        )
    # and drop any version redirects to it
    for key, val in versionRedirectMap.items():
        if val == info:
            del versionRedirectMap[key]


def EnsureModule(
    typelibCLSID,
    lcid,
    major,
    minor,
    progressInstance=None,
    bValidateFile=not is_readonly,
    bForDemand=bForDemandDefault,
    bBuildHidden=1,
):
    """Ensure Python support is loaded for a type library, generating if necessary.

    Given the IID, LCID and version information for a type library, check and if
    necessary (re)generate, then import the necessary support files. If we regenerate the file, there
    is no way to totally snuff out all instances of the old module in Python, and thus we will regenerate the file more than necessary,
    unless makepy/genpy is modified accordingly.


    Returns the Python module.  No exceptions are caught during the generate process.

    Params
    typelibCLSID -- IID of the type library.
    major -- Integer major version.
    minor -- Integer minor version
    lcid -- Integer LCID for the library.
    progressInstance -- Instance to use as progress indicator, or None to
                        use the GUI progress bar.
    bValidateFile -- Whether or not to perform cache validation or not
    bForDemand -- Should a complete generation happen now, or on demand?
    bBuildHidden -- Should hidden members/attributes etc be generated?
    """
    bReloadNeeded = 0
    try:
        try:
            module = GetModuleForTypelib(typelibCLSID, lcid, major, minor)
        except ImportError:
            # If we get an ImportError
            # We may still find a valid cache file under a different MinorVersion #
            # (which windows will search out for us)
            # print("Loading reg typelib", typelibCLSID, major, minor, lcid)
            module = None
            try:
                tlbAttr = pythoncom.LoadRegTypeLib(
                    typelibCLSID, major, minor, lcid
                ).GetLibAttr()
                # if the above line doesn't throw a pythoncom.com_error, check if
                # it is actually a different lib than we requested, and if so, suck it in
                if tlbAttr[1] != lcid or tlbAttr[4] != minor:
                    # print("Trying 2nd minor #", tlbAttr[1], tlbAttr[3], tlbAttr[4])
                    try:
                        module = GetModuleForTypelib(
                            typelibCLSID, tlbAttr[1], tlbAttr[3], tlbAttr[4]
                        )
                    except ImportError:
                        # We don't have a module, but we do have a better minor
                        # version - remember that.
                        minor = tlbAttr[4]
                # else module remains None
            except pythoncom.com_error:
                # couldn't load any typelib - mod remains None
                pass
        if module is not None and bValidateFile:
            assert not is_readonly, "Can't validate in a read-only gencache"
            try:
                typLibPath = pythoncom.QueryPathOfRegTypeLib(
                    typelibCLSID, major, minor, lcid
                )
                # windows seems to add an extra \0 (via the underlying BSTR)
                # The mainwin toolkit does not add this erroneous \0
                if typLibPath[-1] == "\0":
                    typLibPath = typLibPath[:-1]
                suf = getattr(os.path, "supports_unicode_filenames", 0)
                if not suf:
                    # can't pass unicode filenames directly - convert
                    try:
                        typLibPath = typLibPath.encode(sys.getfilesystemencoding())
                    except AttributeError:  # no sys.getfilesystemencoding
                        typLibPath = str(typLibPath)
                tlbAttributes = pythoncom.LoadRegTypeLib(
                    typelibCLSID, major, minor, lcid
                ).GetLibAttr()
            except pythoncom.com_error:
                # We have a module, but no type lib - we should still
                # run with what we have though - the typelib may not be
                # deployed here.
                bValidateFile = 0
        if module is not None and bValidateFile:
            assert not is_readonly, "Can't validate in a read-only gencache"
            filePathPrefix = "{}\\{}".format(
                GetGeneratePath(),
                GetGeneratedFileName(typelibCLSID, lcid, major, minor),
            )
            filePath = filePathPrefix + ".py"
            filePathPyc = filePathPrefix + ".py"
            if __debug__:
                filePathPyc += "c"
            else:
                filePathPyc += "o"
            # Verify that type library is up to date.
            # If we have a differing MinorVersion or genpy has bumped versions, update the file
            from . import genpy

            if (
                module.MinorVersion != tlbAttributes[4]
                or genpy.makepy_version != module.makepy_version
            ):
                # print(f"Version skew: {module.MinorVersion}, {tlbAttributes[4]}")
                # try to erase the bad file from the cache
                try:
                    os.unlink(filePath)
                except OSError:
                    pass
                try:
                    os.unlink(filePathPyc)
                except OSError:
                    pass
                if os.path.isdir(filePathPrefix):
                    import shutil

                    shutil.rmtree(filePathPrefix)
                minor = tlbAttributes[4]
                module = None
                bReloadNeeded = 1
            else:
                minor = module.MinorVersion
                filePathPrefix = "{}\\{}".format(
                    GetGeneratePath(),
                    GetGeneratedFileName(typelibCLSID, lcid, major, minor),
                )
                filePath = filePathPrefix + ".py"
                filePathPyc = filePathPrefix + ".pyc"
                # print("Trying py stat: ", filePath)
                fModTimeSet = 0
                try:
                    pyModTime = os.stat(filePath)[8]
                    fModTimeSet = 1
                except OSError as e:
                    # If .py file fails, try .pyc file
                    # print("Trying pyc stat", filePathPyc)
                    try:
                        pyModTime = os.stat(filePathPyc)[8]
                        fModTimeSet = 1
                    except OSError as e:
                        pass
                # print("Trying stat typelib", pyModTime)
                # print(typLibPath)
                typLibModTime = os.stat(typLibPath)[8]
                if fModTimeSet and (typLibModTime > pyModTime):
                    bReloadNeeded = 1
                    module = None
    except (ImportError, OSError):
        module = None
    if module is None:
        # We need to build an item.  If we are in a read-only cache, we
        # can't/don't want to do this - so before giving up, check for
        # a different minor version in our cache - according to COM, this is OK
        if is_readonly:
            key = str(typelibCLSID), lcid, major, minor
            # If we have been asked before, get last result.
            try:
                return versionRedirectMap[key]
            except KeyError:
                pass
            # Find other candidates.
            items = []
            for desc in GetGeneratedInfos():
                if key[0] == desc[0] and key[1] == desc[1] and key[2] == desc[2]:
                    items.append(desc)
            if items:
                # Items are all identical, except for last tuple element
                # We want the latest minor version we have - so just sort and grab last
                items.sort()
                new_minor = items[-1][3]
                ret = GetModuleForTypelib(typelibCLSID, lcid, major, new_minor)
            else:
                ret = None
            # remember and return
            versionRedirectMap[key] = ret
            return ret
        # print("Rebuilding: ", major, minor)
        module = MakeModuleForTypelib(
            typelibCLSID,
            lcid,
            major,
            minor,
            progressInstance,
            bForDemand=bForDemand,
            bBuildHidden=bBuildHidden,
        )
        # If we replaced something, reload it
        if bReloadNeeded:
            module = reload(module)
            AddModuleToCache(typelibCLSID, lcid, major, minor)
    return module


def EnsureDispatch(
    prog_id, bForDemand=1
):  # New fn, so we default the new demand feature to on!
    """Given a COM prog_id, return an object that is using makepy support, building if necessary"""
    disp = win32com.client.Dispatch(prog_id)
    if not hasattr(disp, "CLSID"):  # Eeek - no makepy support - try and build it.
        try:
            ti = disp._oleobj_.GetTypeInfo()
            disp_clsid = ti.GetTypeAttr()[0]
            tlb, index = ti.GetContainingTypeLib()
            tla = tlb.GetLibAttr()
            mod = EnsureModule(tla[0], tla[1], tla[3], tla[4], bForDemand=bForDemand)
            GetModuleForCLSID(disp_clsid)
            # Get the class from the module.
            from . import CLSIDToClass

            disp_class = CLSIDToClass.GetClass(str(disp_clsid))
            disp = disp_class(disp._oleobj_)
        except pythoncom.com_error:
            raise TypeError(
                "This COM object can not automate the makepy process - please run makepy manually for this object"
            )
    return disp


def AddModuleToCache(
    typelibclsid, lcid, major, minor, verbose=1, bFlushNow=not is_readonly
):
    """Add a newly generated file to the cache dictionary."""
    fname = GetGeneratedFileName(typelibclsid, lcid, major, minor)
    mod = _GetModule(fname)
    # if mod._in_gencache_ is already true, then we are reloading this
    # module - this doesn't mean anything special though!
    mod._in_gencache_ = 1
    info = str(typelibclsid), lcid, major, minor
    dict_modified = False

    def SetTypelibForAllClsids(dict):
        nonlocal dict_modified
        for clsid in dict:
            if clsidToTypelib.get(clsid) != info:
                clsidToTypelib[clsid] = info
                dict_modified = True

    SetTypelibForAllClsids(mod.CLSIDToClassMap)
    SetTypelibForAllClsids(mod.CLSIDToPackageMap)
    SetTypelibForAllClsids(mod.VTablesToClassMap)
    SetTypelibForAllClsids(mod.VTablesToPackageMap)

    # If this lib was previously redirected, drop it
    if info in versionRedirectMap:
        del versionRedirectMap[info]
    if bFlushNow and dict_modified:
        _SaveDicts()


def GetGeneratedInfos():
    zip_pos = win32com.__gen_path__.find(".zip\\")
    if zip_pos >= 0:
        import zipfile

        zip_file = win32com.__gen_path__[: zip_pos + 4]
        zip_path = win32com.__gen_path__[zip_pos + 5 :].replace("\\", "/")
        zf = zipfile.ZipFile(zip_file)
        infos = set()
        for n in zf.namelist():
            if not n.startswith(zip_path):
                continue
            base = n[len(zip_path) + 1 :].split("/")[0]
            try:
                iid, lcid, major, minor = base.split("x")
                lcid = int(lcid)
                major = int(major)
                minor = int(minor)
                iid = pywintypes.IID("{" + iid + "}")
            except ValueError:
                continue
            except pywintypes.com_error:
                # invalid IID
                continue
            infos.add((iid, lcid, major, minor))
        zf.close()
        return list(infos)
    else:
        # on the file system
        files = glob.glob(win32com.__gen_path__ + "\\*")
        ret = []
        for file in files:
            if not os.path.isdir(file) and not os.path.splitext(file)[1] == ".py":
                continue
            name = os.path.splitext(os.path.split(file)[1])[0]
            try:
                iid, lcid, major, minor = name.split("x")
                iid = pywintypes.IID("{" + iid + "}")
                lcid = int(lcid)
                major = int(major)
                minor = int(minor)
            except ValueError:
                continue
            except pywintypes.com_error:
                # invalid IID
                continue
            ret.append((iid, lcid, major, minor))
        return ret


def _GetModule(fname):
    """Given the name of a module in the gen_py directory, import and return it."""
    mod_name = "win32com.gen_py.%s" % fname
    with ModuleMutex(fname):
        __import__(mod_name)
    return sys.modules[mod_name]


def Rebuild(verbose=1):
    """Rebuild the cache indexes from the file system."""
    clsidToTypelib.clear()
    infos = GetGeneratedInfos()
    if verbose and len(infos):  # Don't bother reporting this when directory is empty!
        print("Rebuilding cache of generated files for COM support...")
    for info in infos:
        iid, lcid, major, minor = info
        if verbose:
            print("Checking", GetGeneratedFileName(*info))
        try:
            AddModuleToCache(iid, lcid, major, minor, verbose, 0)
        except:
            print(
                "Could not add module {} - {}: {}".format(
                    info, sys.exc_info()[0], sys.exc_info()[1]
                )
            )
    if verbose and len(infos):  # Don't bother reporting this when directory is empty!
        print("Done.")
    _SaveDicts()


def _Dump():
    print("Cache is in directory", win32com.__gen_path__)
    # Build a unique dir
    d = set(clsidToTypelib.values())
    for typelibCLSID, lcid, major, minor in d:
        mod = GetModuleForTypelib(typelibCLSID, lcid, major, minor)
        print(f"{mod.__doc__} - {typelibCLSID}")


# Boot up
__init__()


def usage():
    usageString = """\
      Usage: gencache [-q] [-d] [-r]

             -q         - Quiet
             -d         - Dump the cache (typelibrary description and filename).
             -r         - Rebuild the cache dictionary from the existing .py files
    """
    print(usageString)
    sys.exit(1)


if __name__ == "__main__":
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "qrd")
    except getopt.error as message:
        print(message)
        usage()

    # we only have options - complain about real args, or none at all!
    if len(sys.argv) == 1 or args:
        print(usage())

    verbose = 1
    for opt, val in opts:
        if opt == "-d":  # Dump
            _Dump()
        if opt == "-r":
            Rebuild(verbose)
        if opt == "-q":
            verbose = 0

# === NexusCore/openenv\Lib\site-packages\ipykernel\ipkernel.py ===
"""The IPython kernel implementation"""

import asyncio
import builtins
import gc
import getpass
import os
import signal
import sys
import threading
import typing as t
from contextlib import contextmanager
from functools import partial

import comm
from IPython.core import release
from IPython.utils.tokenutil import line_at_cursor, token_at_cursor
from jupyter_client.session import extract_header
from traitlets import Any, Bool, HasTraits, Instance, List, Type, observe, observe_compat
from zmq.eventloop.zmqstream import ZMQStream

from .comm.comm import BaseComm
from .comm.manager import CommManager
from .compiler import XCachingCompiler
from .eventloops import _use_appnope
from .iostream import OutStream
from .kernelbase import Kernel as KernelBase
from .kernelbase import _accepts_parameters
from .zmqshell import ZMQInteractiveShell

try:
    from IPython.core.interactiveshell import _asyncio_runner  # type:ignore[attr-defined]
except ImportError:
    _asyncio_runner = None  # type:ignore[assignment]

try:
    from IPython.core.completer import provisionalcompleter as _provisionalcompleter
    from IPython.core.completer import rectify_completions as _rectify_completions

    _use_experimental_60_completion = True
except ImportError:
    _use_experimental_60_completion = False


_EXPERIMENTAL_KEY_NAME = "_jupyter_types_experimental"


def _create_comm(*args, **kwargs):
    """Create a new Comm."""
    return BaseComm(*args, **kwargs)


# there can only be one comm manager in a ipykernel process
_comm_lock = threading.Lock()
_comm_manager: t.Optional[CommManager] = None


def _get_comm_manager(*args, **kwargs):
    """Create a new CommManager."""
    global _comm_manager  # noqa: PLW0603
    if _comm_manager is None:
        with _comm_lock:
            if _comm_manager is None:
                _comm_manager = CommManager(*args, **kwargs)
    return _comm_manager


comm.create_comm = _create_comm
comm.get_comm_manager = _get_comm_manager


class IPythonKernel(KernelBase):
    """The IPython Kernel class."""

    shell = Instance("IPython.core.interactiveshell.InteractiveShellABC", allow_none=True)
    shell_class = Type(ZMQInteractiveShell)

    use_experimental_completions = Bool(
        True,
        help="Set this flag to False to deactivate the use of experimental IPython completion APIs.",
    ).tag(config=True)

    debugpy_stream = Instance(ZMQStream, allow_none=True)

    user_module = Any()

    @observe("user_module")
    @observe_compat
    def _user_module_changed(self, change):
        if self.shell is not None:
            self.shell.user_module = change["new"]

    user_ns = Instance(dict, args=None, allow_none=True)

    @observe("user_ns")
    @observe_compat
    def _user_ns_changed(self, change):
        if self.shell is not None:
            self.shell.user_ns = change["new"]
            self.shell.init_user_ns()

    # A reference to the Python builtin 'raw_input' function.
    # (i.e., __builtin__.raw_input for Python 2.7, builtins.input for Python 3)
    _sys_raw_input = Any()
    _sys_eval_input = Any()

    def __init__(self, **kwargs):
        """Initialize the kernel."""
        super().__init__(**kwargs)

        from .debugger import Debugger, _is_debugpy_available

        # Initialize the Debugger
        if _is_debugpy_available:
            self.debugger = Debugger(
                self.log,
                self.debugpy_stream,
                self._publish_debug_event,
                self.debug_shell_socket,
                self.session,
                self.debug_just_my_code,
            )

        # Initialize the InteractiveShell subclass
        self.shell = self.shell_class.instance(
            parent=self,
            profile_dir=self.profile_dir,
            user_module=self.user_module,
            user_ns=self.user_ns,
            kernel=self,
            compiler_class=XCachingCompiler,
        )
        self.shell.displayhook.session = self.session  # type:ignore[attr-defined]

        jupyter_session_name = os.environ.get("JPY_SESSION_NAME")
        if jupyter_session_name:
            self.shell.user_ns["__session__"] = jupyter_session_name

        self.shell.displayhook.pub_socket = self.iopub_socket  # type:ignore[attr-defined]
        self.shell.displayhook.topic = self._topic("execute_result")  # type:ignore[attr-defined]
        self.shell.display_pub.session = self.session  # type:ignore[attr-defined]
        self.shell.display_pub.pub_socket = self.iopub_socket  # type:ignore[attr-defined]

        self.comm_manager = comm.get_comm_manager()

        assert isinstance(self.comm_manager, HasTraits)
        self.shell.configurables.append(self.comm_manager)  # type:ignore[arg-type]
        comm_msg_types = ["comm_open", "comm_msg", "comm_close"]
        for msg_type in comm_msg_types:
            self.shell_handlers[msg_type] = getattr(self.comm_manager, msg_type)

        if _use_appnope() and self._darwin_app_nap:
            # Disable app-nap as the kernel is not a gui but can have guis
            import appnope  # type:ignore[import-untyped]

            appnope.nope()

        self._new_threads_parent_header = {}
        self._initialize_thread_hooks()

        if hasattr(gc, "callbacks"):
            # while `gc.callbacks` exists since Python 3.3, pypy does not
            # implement it even as of 3.9.
            gc.callbacks.append(self._clean_thread_parent_frames)

    help_links = List(
        [
            {
                "text": "Python Reference",
                "url": "https://docs.python.org/%i.%i" % sys.version_info[:2],
            },
            {
                "text": "IPython Reference",
                "url": "https://ipython.org/documentation.html",
            },
            {
                "text": "NumPy Reference",
                "url": "https://docs.scipy.org/doc/numpy/reference/",
            },
            {
                "text": "SciPy Reference",
                "url": "https://docs.scipy.org/doc/scipy/reference/",
            },
            {
                "text": "Matplotlib Reference",
                "url": "https://matplotlib.org/contents.html",
            },
            {
                "text": "SymPy Reference",
                "url": "http://docs.sympy.org/latest/index.html",
            },
            {
                "text": "pandas Reference",
                "url": "https://pandas.pydata.org/pandas-docs/stable/",
            },
        ]
    ).tag(config=True)

    # Kernel info fields
    implementation = "ipython"
    implementation_version = release.version
    language_info = {
        "name": "python",
        "version": sys.version.split()[0],
        "mimetype": "text/x-python",
        "codemirror_mode": {"name": "ipython", "version": sys.version_info[0]},
        "pygments_lexer": "ipython%d" % 3,
        "nbconvert_exporter": "python",
        "file_extension": ".py",
    }

    def dispatch_debugpy(self, msg):
        from .debugger import _is_debugpy_available

        if _is_debugpy_available:
            # The first frame is the socket id, we can drop it
            frame = msg[1].bytes.decode("utf-8")
            self.log.debug("Debugpy received: %s", frame)
            self.debugger.tcp_client.receive_dap_frame(frame)

    @property
    def banner(self):
        if self.shell:
            return self.shell.banner
        return None

    async def poll_stopped_queue(self):
        """Poll the stopped queue."""
        while True:
            await self.debugger.handle_stopped_event()

    def start(self):
        """Start the kernel."""
        if self.shell:
            self.shell.exit_now = False
        if self.debugpy_stream is None:
            self.log.warning("debugpy_stream undefined, debugging will not be enabled")
        else:
            self.debugpy_stream.on_recv(self.dispatch_debugpy, copy=False)
        super().start()
        if self.debugpy_stream:
            asyncio.run_coroutine_threadsafe(
                self.poll_stopped_queue(), self.control_thread.io_loop.asyncio_loop
            )

    def set_parent(self, ident, parent, channel="shell"):
        """Overridden from parent to tell the display hook and output streams
        about the parent message.
        """
        super().set_parent(ident, parent, channel)
        if channel == "shell" and self.shell:
            self.shell.set_parent(parent)

    def init_metadata(self, parent):
        """Initialize metadata.

        Run at the beginning of each execution request.
        """
        md = super().init_metadata(parent)
        # FIXME: remove deprecated ipyparallel-specific code
        # This is required for ipyparallel < 5.0
        md.update(
            {
                "dependencies_met": True,
                "engine": self.ident,
            }
        )
        return md

    def finish_metadata(self, parent, metadata, reply_content):
        """Finish populating metadata.

        Run after completing an execution request.
        """
        # FIXME: remove deprecated ipyparallel-specific code
        # This is required by ipyparallel < 5.0
        metadata["status"] = reply_content["status"]
        if reply_content["status"] == "error" and reply_content["ename"] == "UnmetDependency":
            metadata["dependencies_met"] = False

        return metadata

    def _forward_input(self, allow_stdin=False):
        """Forward raw_input and getpass to the current frontend.

        via input_request
        """
        self._allow_stdin = allow_stdin

        self._sys_raw_input = builtins.input
        builtins.input = self.raw_input

        self._save_getpass = getpass.getpass
        getpass.getpass = self.getpass

    def _restore_input(self):
        """Restore raw_input, getpass"""
        builtins.input = self._sys_raw_input

        getpass.getpass = self._save_getpass

    @property
    def execution_count(self):
        if self.shell:
            return self.shell.execution_count
        return None

    @execution_count.setter
    def execution_count(self, value):
        # Ignore the incrementing done by KernelBase, in favour of our shell's
        # execution counter.
        pass

    @contextmanager
    def _cancel_on_sigint(self, future):
        """ContextManager for capturing SIGINT and cancelling a future

        SIGINT raises in the event loop when running async code,
        but we want it to halt a coroutine.

        Ideally, it would raise KeyboardInterrupt,
        but this turns it into a CancelledError.
        At least it gets a decent traceback to the user.
        """
        sigint_future: asyncio.Future[int] = asyncio.Future()

        # whichever future finishes first,
        # cancel the other one
        def cancel_unless_done(f, _ignored):
            if f.cancelled() or f.done():
                return
            f.cancel()

        # when sigint finishes,
        # abort the coroutine with CancelledError
        sigint_future.add_done_callback(partial(cancel_unless_done, future))
        # when the main future finishes,
        # stop watching for SIGINT events
        future.add_done_callback(partial(cancel_unless_done, sigint_future))

        def handle_sigint(*args):
            def set_sigint_result():
                if sigint_future.cancelled() or sigint_future.done():
                    return
                sigint_future.set_result(1)

            # use add_callback for thread safety
            self.io_loop.add_callback(set_sigint_result)

        # set the custom sigint handler during this context
        save_sigint = signal.signal(signal.SIGINT, handle_sigint)
        try:
            yield
        finally:
            # restore the previous sigint handler
            signal.signal(signal.SIGINT, save_sigint)

    async def execute_request(self, stream, ident, parent):
        """Override for cell output - cell reconciliation."""
        parent_header = extract_header(parent)
        self._associate_new_top_level_threads_with(parent_header)
        await super().execute_request(stream, ident, parent)

    async def do_execute(
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
        """Handle code execution."""
        shell = self.shell  # we'll need this a lot here
        assert shell is not None

        self._forward_input(allow_stdin)

        reply_content: t.Dict[str, t.Any] = {}
        if hasattr(shell, "run_cell_async") and hasattr(shell, "should_run_async"):
            run_cell = shell.run_cell_async
            should_run_async = shell.should_run_async
            accepts_params = _accepts_parameters(run_cell, ["cell_id"])
        else:
            should_run_async = lambda cell: False  # noqa: ARG005, E731
            # older IPython,
            # use blocking run_cell and wrap it in coroutine

            async def run_cell(*args, **kwargs):
                return shell.run_cell(*args, **kwargs)

            accepts_params = _accepts_parameters(shell.run_cell, ["cell_id"])
        try:
            # default case: runner is asyncio and asyncio is already running
            # TODO: this should check every case for "are we inside the runner",
            # not just asyncio
            preprocessing_exc_tuple = None
            try:
                transformed_cell = shell.transform_cell(code)
            except Exception:
                transformed_cell = code
                preprocessing_exc_tuple = sys.exc_info()

            if (
                _asyncio_runner  # type:ignore[truthy-bool]
                and shell.loop_runner is _asyncio_runner
                and asyncio.get_event_loop().is_running()
                and should_run_async(
                    code,
                    transformed_cell=transformed_cell,
                    preprocessing_exc_tuple=preprocessing_exc_tuple,
                )
            ):
                if accepts_params["cell_id"]:
                    coro = run_cell(
                        code,
                        store_history=store_history,
                        silent=silent,
                        transformed_cell=transformed_cell,
                        preprocessing_exc_tuple=preprocessing_exc_tuple,
                        cell_id=cell_id,
                    )
                else:
                    coro = run_cell(
                        code,
                        store_history=store_history,
                        silent=silent,
                        transformed_cell=transformed_cell,
                        preprocessing_exc_tuple=preprocessing_exc_tuple,
                    )

                coro_future = asyncio.ensure_future(coro)

                with self._cancel_on_sigint(coro_future):
                    res = None
                    try:
                        res = await coro_future
                    finally:
                        shell.events.trigger("post_execute")
                        if not silent:
                            shell.events.trigger("post_run_cell", res)
            else:
                # runner isn't already running,
                # make synchronous call,
                # letting shell dispatch to loop runners
                if accepts_params["cell_id"]:
                    res = shell.run_cell(
                        code,
                        store_history=store_history,
                        silent=silent,
                        cell_id=cell_id,
                    )
                else:
                    res = shell.run_cell(code, store_history=store_history, silent=silent)
        finally:
            self._restore_input()

        err = res.error_before_exec if res.error_before_exec is not None else res.error_in_exec

        if res.success:
            reply_content["status"] = "ok"
        else:
            reply_content["status"] = "error"

            reply_content.update(
                {
                    "traceback": shell._last_traceback or [],
                    "ename": str(type(err).__name__),
                    "evalue": str(err),
                }
            )

            # FIXME: deprecated piece for ipyparallel (remove in 5.0):
            e_info = dict(engine_uuid=self.ident, engine_id=self.int_id, method="execute")
            reply_content["engine_info"] = e_info

        # Return the execution counter so clients can display prompts
        reply_content["execution_count"] = shell.execution_count - 1

        if "traceback" in reply_content:
            self.log.info(
                "Exception in execute request:\n%s",
                "\n".join(reply_content["traceback"]),
            )

        # At this point, we can tell whether the main code execution succeeded
        # or not.  If it did, we proceed to evaluate user_expressions
        if reply_content["status"] == "ok":
            reply_content["user_expressions"] = shell.user_expressions(user_expressions or {})
        else:
            # If there was an error, don't even try to compute expressions
            reply_content["user_expressions"] = {}

        # Payloads should be retrieved regardless of outcome, so we can both
        # recover partial output (that could have been generated early in a
        # block, before an error) and always clear the payload system.
        reply_content["payload"] = shell.payload_manager.read_payload()
        # Be aggressive about clearing the payload because we don't want
        # it to sit in memory until the next execute_request comes in.
        shell.payload_manager.clear_payload()

        return reply_content

    def do_complete(self, code, cursor_pos):
        """Handle code completion."""
        if _use_experimental_60_completion and self.use_experimental_completions:
            return self._experimental_do_complete(code, cursor_pos)

        # FIXME: IPython completers currently assume single line,
        # but completion messages give multi-line context
        # For now, extract line from cell, based on cursor_pos:
        if cursor_pos is None:
            cursor_pos = len(code)
        line, offset = line_at_cursor(code, cursor_pos)
        line_cursor = cursor_pos - offset
        assert self.shell is not None
        txt, matches = self.shell.complete("", line, line_cursor)
        return {
            "matches": matches,
            "cursor_end": cursor_pos,
            "cursor_start": cursor_pos - len(txt),
            "metadata": {},
            "status": "ok",
        }

    async def do_debug_request(self, msg):
        """Handle a debug request."""
        from .debugger import _is_debugpy_available

        if _is_debugpy_available:
            return await self.debugger.process_request(msg)
        return None

    def _experimental_do_complete(self, code, cursor_pos):
        """
        Experimental completions from IPython, using Jedi.
        """
        if cursor_pos is None:
            cursor_pos = len(code)
        with _provisionalcompleter():
            assert self.shell is not None
            raw_completions = self.shell.Completer.completions(code, cursor_pos)
            completions = list(_rectify_completions(code, raw_completions))

            comps = []
            for comp in completions:
                comps.append(
                    dict(
                        start=comp.start,
                        end=comp.end,
                        text=comp.text,
                        type=comp.type,
                        signature=comp.signature,
                    )
                )

        if completions:
            s = completions[0].start
            e = completions[0].end
            matches = [c.text for c in completions]
        else:
            s = cursor_pos
            e = cursor_pos
            matches = []

        return {
            "matches": matches,
            "cursor_end": e,
            "cursor_start": s,
            "metadata": {_EXPERIMENTAL_KEY_NAME: comps},
            "status": "ok",
        }

    def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=()):
        """Handle code inspection."""
        name = token_at_cursor(code, cursor_pos)

        reply_content: t.Dict[str, t.Any] = {"status": "ok"}
        reply_content["data"] = {}
        reply_content["metadata"] = {}
        assert self.shell is not None
        try:
            if release.version_info >= (8,):
                # `omit_sections` keyword will be available in IPython 8, see
                # https://github.com/ipython/ipython/pull/13343
                bundle = self.shell.object_inspect_mime(
                    name,
                    detail_level=detail_level,
                    omit_sections=omit_sections,
                )
            else:
                bundle = self.shell.object_inspect_mime(name, detail_level=detail_level)
            reply_content["data"].update(bundle)
            if not self.shell.enable_html_pager:
                reply_content["data"].pop("text/html")
            reply_content["found"] = True
        except KeyError:
            reply_content["found"] = False

        return reply_content

    def do_history(
        self,
        hist_access_type,
        output,
        raw,
        session=0,
        start=0,
        stop=None,
        n=None,
        pattern=None,
        unique=False,
    ):
        """Handle code history."""
        assert self.shell is not None
        if hist_access_type == "tail":
            hist = self.shell.history_manager.get_tail(
                n, raw=raw, output=output, include_latest=True
            )

        elif hist_access_type == "range":
            hist = self.shell.history_manager.get_range(
                session, start, stop, raw=raw, output=output
            )

        elif hist_access_type == "search":
            hist = self.shell.history_manager.search(
                pattern, raw=raw, output=output, n=n, unique=unique
            )
        else:
            hist = []

        return {
            "status": "ok",
            "history": list(hist),
        }

    def do_shutdown(self, restart):
        """Handle kernel shutdown."""
        if self.shell:
            self.shell.exit_now = True
        return dict(status="ok", restart=restart)

    def do_is_complete(self, code):
        """Handle an is_complete request."""
        transformer_manager = getattr(self.shell, "input_transformer_manager", None)
        if transformer_manager is None:
            # input_splitter attribute is deprecated
            assert self.shell is not None
            transformer_manager = self.shell.input_splitter
        status, indent_spaces = transformer_manager.check_complete(code)
        r = {"status": status}
        if status == "incomplete":
            r["indent"] = " " * indent_spaces
        return r

    def do_apply(self, content, bufs, msg_id, reply_metadata):
        """Handle an apply request."""
        try:
            from ipyparallel.serialize import serialize_object, unpack_apply_message
        except ImportError:
            from .serialize import serialize_object, unpack_apply_message

        shell = self.shell
        assert shell is not None
        try:
            working = shell.user_ns

            prefix = "_" + str(msg_id).replace("-", "") + "_"
            f, args, kwargs = unpack_apply_message(bufs, working, copy=False)

            fname = getattr(f, "__name__", "f")

            fname = prefix + "f"
            argname = prefix + "args"
            kwargname = prefix + "kwargs"
            resultname = prefix + "result"

            ns = {fname: f, argname: args, kwargname: kwargs, resultname: None}
            # print ns
            working.update(ns)
            code = f"{resultname} = {fname}(*{argname},**{kwargname})"
            try:
                exec(code, shell.user_global_ns, shell.user_ns)
                result = working.get(resultname)
            finally:
                for key in ns:
                    working.pop(key)

            assert self.session is not None
            result_buf = serialize_object(
                result,
                buffer_threshold=self.session.buffer_threshold,
                item_threshold=self.session.item_threshold,
            )

        except BaseException as e:
            # invoke IPython traceback formatting
            shell.showtraceback()
            reply_content = {
                "traceback": shell._last_traceback or [],
                "ename": str(type(e).__name__),
                "evalue": str(e),
            }
            # FIXME: deprecated piece for ipyparallel (remove in 5.0):
            e_info = dict(engine_uuid=self.ident, engine_id=self.int_id, method="apply")
            reply_content["engine_info"] = e_info

            self.send_response(
                self.iopub_socket,
                "error",
                reply_content,
                ident=self._topic("error"),
            )
            self.log.info("Exception in apply request:\n%s", "\n".join(reply_content["traceback"]))
            result_buf = []
            reply_content["status"] = "error"
        else:
            reply_content = {"status": "ok"}

        return reply_content, result_buf

    def do_clear(self):
        """Clear the kernel."""
        if self.shell:
            self.shell.reset(False)
        return dict(status="ok")

    def _associate_new_top_level_threads_with(self, parent_header):
        """Store the parent header to associate it with new top-level threads"""
        self._new_threads_parent_header = parent_header

    def _initialize_thread_hooks(self):
        """Store thread hierarchy and thread-parent_header associations."""
        stdout = self._stdout
        stderr = self._stderr
        kernel_thread_ident = threading.get_ident()
        kernel = self
        _threading_Thread_run = threading.Thread.run
        _threading_Thread__init__ = threading.Thread.__init__

        def run_closure(self: threading.Thread):
            """Wrap the `threading.Thread.start` to intercept thread identity.

            This is needed because there is no "start" hook yet, but there
            might be one in the future: https://bugs.python.org/issue14073

            This is a no-op if the `self._stdout` and `self._stderr` are not
            sub-classes of `OutStream`.
            """

            try:
                parent = self._ipykernel_parent_thread_ident  # type:ignore[attr-defined]
            except AttributeError:
                return
            for stream in [stdout, stderr]:
                if isinstance(stream, OutStream):
                    if parent == kernel_thread_ident:
                        stream._thread_to_parent_header[
                            self.ident
                        ] = kernel._new_threads_parent_header
                    else:
                        stream._thread_to_parent[self.ident] = parent
            _threading_Thread_run(self)

        def init_closure(self: threading.Thread, *args, **kwargs):
            _threading_Thread__init__(self, *args, **kwargs)
            self._ipykernel_parent_thread_ident = threading.get_ident()  # type:ignore[attr-defined]

        threading.Thread.__init__ = init_closure  # type:ignore[method-assign]
        threading.Thread.run = run_closure  # type:ignore[method-assign]

    def _clean_thread_parent_frames(
        self, phase: t.Literal["start", "stop"], info: t.Dict[str, t.Any]
    ):
        """Clean parent frames of threads which are no longer running.
        This is meant to be invoked by garbage collector callback hook.

        The implementation enumerates the threads because there is no "exit" hook yet,
        but there might be one in the future: https://bugs.python.org/issue14073

        This is a no-op if the `self._stdout` and `self._stderr` are not
        sub-classes of `OutStream`.
        """
        # Only run before the garbage collector starts
        if phase != "start":
            return
        active_threads = {thread.ident for thread in threading.enumerate()}
        for stream in [self._stdout, self._stderr]:
            if isinstance(stream, OutStream):
                thread_to_parent_header = stream._thread_to_parent_header
                for identity in list(thread_to_parent_header.keys()):
                    if identity not in active_threads:
                        try:
                            del thread_to_parent_header[identity]
                        except KeyError:
                            pass
                thread_to_parent = stream._thread_to_parent
                for identity in list(thread_to_parent.keys()):
                    if identity not in active_threads:
                        try:
                            del thread_to_parent[identity]
                        except KeyError:
                            pass


# This exists only for backwards compatibility - use IPythonKernel instead


class Kernel(IPythonKernel):
    """DEPRECATED.  An alias for the IPython kernel class."""

    def __init__(self, *args, **kwargs):  # pragma: no cover
        """DEPRECATED."""
        import warnings

        warnings.warn(
            "Kernel is a deprecated alias of ipykernel.ipkernel.IPythonKernel",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\factory.py ===
import contextlib
import functools
import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    cast,
)

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import InvalidVersion, Version
from pip._vendor.resolvelib import ResolutionImpossible

from pip._internal.cache import CacheEntry, WheelCache
from pip._internal.exceptions import (
    DistributionNotFound,
    InstallationError,
    InvalidInstalledPackage,
    MetadataInconsistent,
    MetadataInvalid,
    UnsupportedPythonVersion,
    UnsupportedWheel,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution, get_default_environment
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import (
    install_req_drop_extras,
    install_req_from_link_and_ireq,
)
from pip._internal.req.req_install import (
    InstallRequirement,
    check_invalid_constraint_type,
)
from pip._internal.resolution.base import InstallRequirementProvider
from pip._internal.utils.compatibility_tags import get_supported
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import Candidate, Constraint, Requirement
from .candidates import (
    AlreadyInstalledCandidate,
    BaseCandidate,
    EditableCandidate,
    ExtrasCandidate,
    LinkCandidate,
    RequiresPythonCandidate,
    as_base_candidate,
)
from .found_candidates import FoundCandidates, IndexCandidateInfo
from .requirements import (
    ExplicitRequirement,
    RequiresPythonRequirement,
    SpecifierRequirement,
    SpecifierWithoutExtrasRequirement,
    UnsatisfiableRequirement,
)

if TYPE_CHECKING:

    class ConflictCause(Protocol):
        requirement: RequiresPythonRequirement
        parent: Candidate


logger = logging.getLogger(__name__)

C = TypeVar("C")
Cache = Dict[Link, C]


class CollectedRootRequirements(NamedTuple):
    requirements: List[Requirement]
    constraints: Dict[str, Constraint]
    user_requested: Dict[str, int]


class Factory:
    def __init__(
        self,
        finder: PackageFinder,
        preparer: RequirementPreparer,
        make_install_req: InstallRequirementProvider,
        wheel_cache: Optional[WheelCache],
        use_user_site: bool,
        force_reinstall: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self._finder = finder
        self.preparer = preparer
        self._wheel_cache = wheel_cache
        self._python_candidate = RequiresPythonCandidate(py_version_info)
        self._make_install_req_from_spec = make_install_req
        self._use_user_site = use_user_site
        self._force_reinstall = force_reinstall
        self._ignore_requires_python = ignore_requires_python

        self._build_failures: Cache[InstallationError] = {}
        self._link_candidate_cache: Cache[LinkCandidate] = {}
        self._editable_candidate_cache: Cache[EditableCandidate] = {}
        self._installed_candidate_cache: Dict[str, AlreadyInstalledCandidate] = {}
        self._extras_candidate_cache: Dict[
            Tuple[int, FrozenSet[NormalizedName]], ExtrasCandidate
        ] = {}
        self._supported_tags_cache = get_supported()

        if not ignore_installed:
            env = get_default_environment()
            self._installed_dists = {
                dist.canonical_name: dist
                for dist in env.iter_installed_distributions(local_only=False)
            }
        else:
            self._installed_dists = {}

    @property
    def force_reinstall(self) -> bool:
        return self._force_reinstall

    def _fail_if_link_is_unsupported_wheel(self, link: Link) -> None:
        if not link.is_wheel:
            return
        wheel = Wheel(link.filename)
        if wheel.supported(self._finder.target_python.get_unsorted_tags()):
            return
        msg = f"{link.filename} is not a supported wheel on this platform."
        raise UnsupportedWheel(msg)

    def _make_extras_candidate(
        self,
        base: BaseCandidate,
        extras: FrozenSet[str],
        *,
        comes_from: Optional[InstallRequirement] = None,
    ) -> ExtrasCandidate:
        cache_key = (id(base), frozenset(canonicalize_name(e) for e in extras))
        try:
            candidate = self._extras_candidate_cache[cache_key]
        except KeyError:
            candidate = ExtrasCandidate(base, extras, comes_from=comes_from)
            self._extras_candidate_cache[cache_key] = candidate
        return candidate

    def _make_candidate_from_dist(
        self,
        dist: BaseDistribution,
        extras: FrozenSet[str],
        template: InstallRequirement,
    ) -> Candidate:
        try:
            base = self._installed_candidate_cache[dist.canonical_name]
        except KeyError:
            base = AlreadyInstalledCandidate(dist, template, factory=self)
            self._installed_candidate_cache[dist.canonical_name] = base
        if not extras:
            return base
        return self._make_extras_candidate(base, extras, comes_from=template)

    def _make_candidate_from_link(
        self,
        link: Link,
        extras: FrozenSet[str],
        template: InstallRequirement,
        name: Optional[NormalizedName],
        version: Optional[Version],
    ) -> Optional[Candidate]:
        base: Optional[BaseCandidate] = self._make_base_candidate_from_link(
            link, template, name, version
        )
        if not extras or base is None:
            return base
        return self._make_extras_candidate(base, extras, comes_from=template)

    def _make_base_candidate_from_link(
        self,
        link: Link,
        template: InstallRequirement,
        name: Optional[NormalizedName],
        version: Optional[Version],
    ) -> Optional[BaseCandidate]:
        # TODO: Check already installed candidate, and use it if the link and
        # editable flag match.

        if link in self._build_failures:
            # We already tried this candidate before, and it does not build.
            # Don't bother trying again.
            return None

        if template.editable:
            if link not in self._editable_candidate_cache:
                try:
                    self._editable_candidate_cache[link] = EditableCandidate(
                        link,
                        template,
                        factory=self,
                        name=name,
                        version=version,
                    )
                except (MetadataInconsistent, MetadataInvalid) as e:
                    logger.info(
                        "Discarding [blue underline]%s[/]: [yellow]%s[reset]",
                        link,
                        e,
                        extra={"markup": True},
                    )
                    self._build_failures[link] = e
                    return None

            return self._editable_candidate_cache[link]
        else:
            if link not in self._link_candidate_cache:
                try:
                    self._link_candidate_cache[link] = LinkCandidate(
                        link,
                        template,
                        factory=self,
                        name=name,
                        version=version,
                    )
                except MetadataInconsistent as e:
                    logger.info(
                        "Discarding [blue underline]%s[/]: [yellow]%s[reset]",
                        link,
                        e,
                        extra={"markup": True},
                    )
                    self._build_failures[link] = e
                    return None
            return self._link_candidate_cache[link]

    def _iter_found_candidates(
        self,
        ireqs: Sequence[InstallRequirement],
        specifier: SpecifierSet,
        hashes: Hashes,
        prefers_installed: bool,
        incompatible_ids: Set[int],
    ) -> Iterable[Candidate]:
        if not ireqs:
            return ()

        # The InstallRequirement implementation requires us to give it a
        # "template". Here we just choose the first requirement to represent
        # all of them.
        # Hopefully the Project model can correct this mismatch in the future.
        template = ireqs[0]
        assert template.req, "Candidates found on index must be PEP 508"
        name = canonicalize_name(template.req.name)

        extras: FrozenSet[str] = frozenset()
        for ireq in ireqs:
            assert ireq.req, "Candidates found on index must be PEP 508"
            specifier &= ireq.req.specifier
            hashes &= ireq.hashes(trust_internet=False)
            extras |= frozenset(ireq.extras)

        def _get_installed_candidate() -> Optional[Candidate]:
            """Get the candidate for the currently-installed version."""
            # If --force-reinstall is set, we want the version from the index
            # instead, so we "pretend" there is nothing installed.
            if self._force_reinstall:
                return None
            try:
                installed_dist = self._installed_dists[name]
            except KeyError:
                return None

            try:
                # Don't use the installed distribution if its version
                # does not fit the current dependency graph.
                if not specifier.contains(installed_dist.version, prereleases=True):
                    return None
            except InvalidVersion as e:
                raise InvalidInstalledPackage(dist=installed_dist, invalid_exc=e)

            candidate = self._make_candidate_from_dist(
                dist=installed_dist,
                extras=extras,
                template=template,
            )
            # The candidate is a known incompatibility. Don't use it.
            if id(candidate) in incompatible_ids:
                return None
            return candidate

        def iter_index_candidate_infos() -> Iterator[IndexCandidateInfo]:
            result = self._finder.find_best_candidate(
                project_name=name,
                specifier=specifier,
                hashes=hashes,
            )
            icans = result.applicable_candidates

            # PEP 592: Yanked releases are ignored unless the specifier
            # explicitly pins a version (via '==' or '===') that can be
            # solely satisfied by a yanked release.
            all_yanked = all(ican.link.is_yanked for ican in icans)

            def is_pinned(specifier: SpecifierSet) -> bool:
                for sp in specifier:
                    if sp.operator == "===":
                        return True
                    if sp.operator != "==":
                        continue
                    if sp.version.endswith(".*"):
                        continue
                    return True
                return False

            pinned = is_pinned(specifier)

            # PackageFinder returns earlier versions first, so we reverse.
            for ican in reversed(icans):
                if not (all_yanked and pinned) and ican.link.is_yanked:
                    continue
                func = functools.partial(
                    self._make_candidate_from_link,
                    link=ican.link,
                    extras=extras,
                    template=template,
                    name=name,
                    version=ican.version,
                )
                yield ican.version, func

        return FoundCandidates(
            iter_index_candidate_infos,
            _get_installed_candidate(),
            prefers_installed,
            incompatible_ids,
        )

    def _iter_explicit_candidates_from_base(
        self,
        base_requirements: Iterable[Requirement],
        extras: FrozenSet[str],
    ) -> Iterator[Candidate]:
        """Produce explicit candidates from the base given an extra-ed package.

        :param base_requirements: Requirements known to the resolver. The
            requirements are guaranteed to not have extras.
        :param extras: The extras to inject into the explicit requirements'
            candidates.
        """
        for req in base_requirements:
            lookup_cand, _ = req.get_candidate_lookup()
            if lookup_cand is None:  # Not explicit.
                continue
            # We've stripped extras from the identifier, and should always
            # get a BaseCandidate here, unless there's a bug elsewhere.
            base_cand = as_base_candidate(lookup_cand)
            assert base_cand is not None, "no extras here"
            yield self._make_extras_candidate(base_cand, extras)

    def _iter_candidates_from_constraints(
        self,
        identifier: str,
        constraint: Constraint,
        template: InstallRequirement,
    ) -> Iterator[Candidate]:
        """Produce explicit candidates from constraints.

        This creates "fake" InstallRequirement objects that are basically clones
        of what "should" be the template, but with original_link set to link.
        """
        for link in constraint.links:
            self._fail_if_link_is_unsupported_wheel(link)
            candidate = self._make_base_candidate_from_link(
                link,
                template=install_req_from_link_and_ireq(link, template),
                name=canonicalize_name(identifier),
                version=None,
            )
            if candidate:
                yield candidate

    def find_candidates(
        self,
        identifier: str,
        requirements: Mapping[str, Iterable[Requirement]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
        constraint: Constraint,
        prefers_installed: bool,
        is_satisfied_by: Callable[[Requirement, Candidate], bool],
    ) -> Iterable[Candidate]:
        # Collect basic lookup information from the requirements.
        explicit_candidates: Set[Candidate] = set()
        ireqs: List[InstallRequirement] = []
        for req in requirements[identifier]:
            cand, ireq = req.get_candidate_lookup()
            if cand is not None:
                explicit_candidates.add(cand)
            if ireq is not None:
                ireqs.append(ireq)

        # If the current identifier contains extras, add requires and explicit
        # candidates from entries from extra-less identifier.
        with contextlib.suppress(InvalidRequirement):
            parsed_requirement = get_requirement(identifier)
            if parsed_requirement.name != identifier:
                explicit_candidates.update(
                    self._iter_explicit_candidates_from_base(
                        requirements.get(parsed_requirement.name, ()),
                        frozenset(parsed_requirement.extras),
                    ),
                )
                for req in requirements.get(parsed_requirement.name, []):
                    _, ireq = req.get_candidate_lookup()
                    if ireq is not None:
                        ireqs.append(ireq)

        # Add explicit candidates from constraints. We only do this if there are
        # known ireqs, which represent requirements not already explicit. If
        # there are no ireqs, we're constraining already-explicit requirements,
        # which is handled later when we return the explicit candidates.
        if ireqs:
            try:
                explicit_candidates.update(
                    self._iter_candidates_from_constraints(
                        identifier,
                        constraint,
                        template=ireqs[0],
                    ),
                )
            except UnsupportedWheel:
                # If we're constrained to install a wheel incompatible with the
                # target architecture, no candidates will ever be valid.
                return ()

        # Since we cache all the candidates, incompatibility identification
        # can be made quicker by comparing only the id() values.
        incompat_ids = {id(c) for c in incompatibilities.get(identifier, ())}

        # If none of the requirements want an explicit candidate, we can ask
        # the finder for candidates.
        if not explicit_candidates:
            return self._iter_found_candidates(
                ireqs,
                constraint.specifier,
                constraint.hashes,
                prefers_installed,
                incompat_ids,
            )

        return (
            c
            for c in explicit_candidates
            if id(c) not in incompat_ids
            and constraint.is_satisfied_by(c)
            and all(is_satisfied_by(req, c) for req in requirements[identifier])
        )

    def _make_requirements_from_install_req(
        self, ireq: InstallRequirement, requested_extras: Iterable[str]
    ) -> Iterator[Requirement]:
        """
        Returns requirement objects associated with the given InstallRequirement. In
        most cases this will be a single object but the following special cases exist:
            - the InstallRequirement has markers that do not apply -> result is empty
            - the InstallRequirement has both a constraint (or link) and extras
                -> result is split in two requirement objects: one with the constraint
                (or link) and one with the extra. This allows centralized constraint
                handling for the base, resulting in fewer candidate rejections.
        """
        if not ireq.match_markers(requested_extras):
            logger.info(
                "Ignoring %s: markers '%s' don't match your environment",
                ireq.name,
                ireq.markers,
            )
        elif not ireq.link:
            if ireq.extras and ireq.req is not None and ireq.req.specifier:
                yield SpecifierWithoutExtrasRequirement(ireq)
            yield SpecifierRequirement(ireq)
        else:
            self._fail_if_link_is_unsupported_wheel(ireq.link)
            # Always make the link candidate for the base requirement to make it
            # available to `find_candidates` for explicit candidate lookup for any
            # set of extras.
            # The extras are required separately via a second requirement.
            cand = self._make_base_candidate_from_link(
                ireq.link,
                template=install_req_drop_extras(ireq) if ireq.extras else ireq,
                name=canonicalize_name(ireq.name) if ireq.name else None,
                version=None,
            )
            if cand is None:
                # There's no way we can satisfy a URL requirement if the underlying
                # candidate fails to build. An unnamed URL must be user-supplied, so
                # we fail eagerly. If the URL is named, an unsatisfiable requirement
                # can make the resolver do the right thing, either backtrack (and
                # maybe find some other requirement that's buildable) or raise a
                # ResolutionImpossible eventually.
                if not ireq.name:
                    raise self._build_failures[ireq.link]
                yield UnsatisfiableRequirement(canonicalize_name(ireq.name))
            else:
                # require the base from the link
                yield self.make_requirement_from_candidate(cand)
                if ireq.extras:
                    # require the extras on top of the base candidate
                    yield self.make_requirement_from_candidate(
                        self._make_extras_candidate(cand, frozenset(ireq.extras))
                    )

    def collect_root_requirements(
        self, root_ireqs: List[InstallRequirement]
    ) -> CollectedRootRequirements:
        collected = CollectedRootRequirements([], {}, {})
        for i, ireq in enumerate(root_ireqs):
            if ireq.constraint:
                # Ensure we only accept valid constraints
                problem = check_invalid_constraint_type(ireq)
                if problem:
                    raise InstallationError(problem)
                if not ireq.match_markers():
                    continue
                assert ireq.name, "Constraint must be named"
                name = canonicalize_name(ireq.name)
                if name in collected.constraints:
                    collected.constraints[name] &= ireq
                else:
                    collected.constraints[name] = Constraint.from_ireq(ireq)
            else:
                reqs = list(
                    self._make_requirements_from_install_req(
                        ireq,
                        requested_extras=(),
                    )
                )
                if not reqs:
                    continue
                template = reqs[0]
                if ireq.user_supplied and template.name not in collected.user_requested:
                    collected.user_requested[template.name] = i
                collected.requirements.extend(reqs)
        # Put requirements with extras at the end of the root requires. This does not
        # affect resolvelib's picking preference but it does affect its initial criteria
        # population: by putting extras at the end we enable the candidate finder to
        # present resolvelib with a smaller set of candidates to resolvelib, already
        # taking into account any non-transient constraints on the associated base. This
        # means resolvelib will have fewer candidates to visit and reject.
        # Python's list sort is stable, meaning relative order is kept for objects with
        # the same key.
        collected.requirements.sort(key=lambda r: r.name != r.project_name)
        return collected

    def make_requirement_from_candidate(
        self, candidate: Candidate
    ) -> ExplicitRequirement:
        return ExplicitRequirement(candidate)

    def make_requirements_from_spec(
        self,
        specifier: str,
        comes_from: Optional[InstallRequirement],
        requested_extras: Iterable[str] = (),
    ) -> Iterator[Requirement]:
        """
        Returns requirement objects associated with the given specifier. In most cases
        this will be a single object but the following special cases exist:
            - the specifier has markers that do not apply -> result is empty
            - the specifier has both a constraint and extras -> result is split
                in two requirement objects: one with the constraint and one with the
                extra. This allows centralized constraint handling for the base,
                resulting in fewer candidate rejections.
        """
        ireq = self._make_install_req_from_spec(specifier, comes_from)
        return self._make_requirements_from_install_req(ireq, requested_extras)

    def make_requires_python_requirement(
        self,
        specifier: SpecifierSet,
    ) -> Optional[Requirement]:
        if self._ignore_requires_python:
            return None
        # Don't bother creating a dependency for an empty Requires-Python.
        if not str(specifier):
            return None
        return RequiresPythonRequirement(specifier, self._python_candidate)

    def get_wheel_cache_entry(
        self, link: Link, name: Optional[str]
    ) -> Optional[CacheEntry]:
        """Look up the link in the wheel cache.

        If ``preparer.require_hashes`` is True, don't use the wheel cache,
        because cached wheels, always built locally, have different hashes
        than the files downloaded from the index server and thus throw false
        hash mismatches. Furthermore, cached wheels at present have
        nondeterministic contents due to file modification times.
        """
        if self._wheel_cache is None:
            return None
        return self._wheel_cache.get_cache_entry(
            link=link,
            package_name=name,
            supported_tags=self._supported_tags_cache,
        )

    def get_dist_to_uninstall(self, candidate: Candidate) -> Optional[BaseDistribution]:
        # TODO: Are there more cases this needs to return True? Editable?
        dist = self._installed_dists.get(candidate.project_name)
        if dist is None:  # Not installed, no uninstallation required.
            return None

        # We're installing into global site. The current installation must
        # be uninstalled, no matter it's in global or user site, because the
        # user site installation has precedence over global.
        if not self._use_user_site:
            return dist

        # We're installing into user site. Remove the user site installation.
        if dist.in_usersite:
            return dist

        # We're installing into user site, but the installed incompatible
        # package is in global site. We can't uninstall that, and would let
        # the new user installation to "shadow" it. But shadowing won't work
        # in virtual environments, so we error out.
        if running_under_virtualenv() and dist.in_site_packages:
            message = (
                f"Will not install to the user site because it will lack "
                f"sys.path precedence to {dist.raw_name} in {dist.location}"
            )
            raise InstallationError(message)
        return None

    def _report_requires_python_error(
        self, causes: Sequence["ConflictCause"]
    ) -> UnsupportedPythonVersion:
        assert causes, "Requires-Python error reported with no cause"

        version = self._python_candidate.version

        if len(causes) == 1:
            specifier = str(causes[0].requirement.specifier)
            message = (
                f"Package {causes[0].parent.name!r} requires a different "
                f"Python: {version} not in {specifier!r}"
            )
            return UnsupportedPythonVersion(message)

        message = f"Packages require a different Python. {version} not in:"
        for cause in causes:
            package = cause.parent.format_for_error()
            specifier = str(cause.requirement.specifier)
            message += f"\n{specifier!r} (required by {package})"
        return UnsupportedPythonVersion(message)

    def _report_single_requirement_conflict(
        self, req: Requirement, parent: Optional[Candidate]
    ) -> DistributionNotFound:
        if parent is None:
            req_disp = str(req)
        else:
            req_disp = f"{req} (from {parent.name})"

        cands = self._finder.find_all_candidates(req.project_name)
        skipped_by_requires_python = self._finder.requires_python_skipped_reasons()

        versions_set: Set[Version] = set()
        yanked_versions_set: Set[Version] = set()
        for c in cands:
            is_yanked = c.link.is_yanked if c.link else False
            if is_yanked:
                yanked_versions_set.add(c.version)
            else:
                versions_set.add(c.version)

        versions = [str(v) for v in sorted(versions_set)]
        yanked_versions = [str(v) for v in sorted(yanked_versions_set)]

        if yanked_versions:
            # Saying "version X is yanked" isn't entirely accurate.
            # https://github.com/pypa/pip/issues/11745#issuecomment-1402805842
            logger.critical(
                "Ignored the following yanked versions: %s",
                ", ".join(yanked_versions) or "none",
            )
        if skipped_by_requires_python:
            logger.critical(
                "Ignored the following versions that require a different python "
                "version: %s",
                "; ".join(skipped_by_requires_python) or "none",
            )
        logger.critical(
            "Could not find a version that satisfies the requirement %s "
            "(from versions: %s)",
            req_disp,
            ", ".join(versions) or "none",
        )
        if str(req) == "requirements.txt":
            logger.info(
                "HINT: You are attempting to install a package literally "
                'named "requirements.txt" (which cannot exist). Consider '
                "using the '-r' flag to install the packages listed in "
                "requirements.txt"
            )

        return DistributionNotFound(f"No matching distribution found for {req}")

    def get_installation_error(
        self,
        e: "ResolutionImpossible[Requirement, Candidate]",
        constraints: Dict[str, Constraint],
    ) -> InstallationError:
        assert e.causes, "Installation error reported with no cause"

        # If one of the things we can't solve is "we need Python X.Y",
        # that is what we report.
        requires_python_causes = [
            cause
            for cause in e.causes
            if isinstance(cause.requirement, RequiresPythonRequirement)
            and not cause.requirement.is_satisfied_by(self._python_candidate)
        ]
        if requires_python_causes:
            # The comprehension above makes sure all Requirement instances are
            # RequiresPythonRequirement, so let's cast for convenience.
            return self._report_requires_python_error(
                cast("Sequence[ConflictCause]", requires_python_causes),
            )

        # Otherwise, we have a set of causes which can't all be satisfied
        # at once.

        # The simplest case is when we have *one* cause that can't be
        # satisfied. We just report that case.
        if len(e.causes) == 1:
            req, parent = e.causes[0]
            if req.name not in constraints:
                return self._report_single_requirement_conflict(req, parent)

        # OK, we now have a list of requirements that can't all be
        # satisfied at once.

        # A couple of formatting helpers
        def text_join(parts: List[str]) -> str:
            if len(parts) == 1:
                return parts[0]

            return ", ".join(parts[:-1]) + " and " + parts[-1]

        def describe_trigger(parent: Candidate) -> str:
            ireq = parent.get_install_requirement()
            if not ireq or not ireq.comes_from:
                return f"{parent.name}=={parent.version}"
            if isinstance(ireq.comes_from, InstallRequirement):
                return str(ireq.comes_from.name)
            return str(ireq.comes_from)

        triggers = set()
        for req, parent in e.causes:
            if parent is None:
                # This is a root requirement, so we can report it directly
                trigger = req.format_for_error()
            else:
                trigger = describe_trigger(parent)
            triggers.add(trigger)

        if triggers:
            info = text_join(sorted(triggers))
        else:
            info = "the requested packages"

        msg = (
            f"Cannot install {info} because these package versions "
            "have conflicting dependencies."
        )
        logger.critical(msg)
        msg = "\nThe conflict is caused by:"

        relevant_constraints = set()
        for req, parent in e.causes:
            if req.name in constraints:
                relevant_constraints.add(req.name)
            msg = msg + "\n    "
            if parent:
                msg = msg + f"{parent.name} {parent.version} depends on "
            else:
                msg = msg + "The user requested "
            msg = msg + req.format_for_error()
        for key in relevant_constraints:
            spec = constraints[key].specifier
            msg += f"\n    The user requested (constraint) {key}{spec}"

        msg = (
            msg
            + "\n\n"
            + "To fix this you could try to:\n"
            + "1. loosen the range of package versions you've specified\n"
            + "2. remove package versions to allow pip to attempt to solve "
            + "the dependency conflict\n"
        )

        logger.info(msg)

        return DistributionNotFound(
            "ResolutionImpossible: for help visit "
            "https://pip.pypa.io/en/latest/topics/dependency-resolution/"
            "#dealing-with-dependency-conflicts"
        )

# === NexusCore/openenv\Lib\site-packages\anthropic\resources\completions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal, overload

import httpx

from .. import _legacy_response
from ..types import completion_create_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._utils import (
    is_given,
    required_args,
    maybe_transform,
    async_maybe_transform,
)
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .._constants import DEFAULT_TIMEOUT
from .._streaming import Stream, AsyncStream
from .._base_client import make_request_options
from ..types.completion import Completion
from ..types.model_param import ModelParam
from ..types.metadata_param import MetadataParam

__all__ = ["Completions", "AsyncCompletions"]


class Completions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> CompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return CompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> CompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return CompletionsWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[Completion]:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | Stream[Completion]:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens_to_sample", "model", "prompt"], ["max_tokens_to_sample", "model", "prompt", "stream"])
    def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | Stream[Completion]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        return self._post(
            "/v1/complete",
            body=maybe_transform(
                {
                    "max_tokens_to_sample": max_tokens_to_sample,
                    "model": model,
                    "prompt": prompt,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Completion,
            stream=stream or False,
            stream_cls=Stream[Completion],
        )


class AsyncCompletions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncCompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncCompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncCompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncCompletionsWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[Completion]:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | AsyncStream[Completion]:
        """[Legacy] Create a Text Completion.

        The Text Completions API is a legacy API.

        We recommend using the
        [Messages API](https://docs.anthropic.com/en/api/messages) going forward.

        Future models and features will not be compatible with Text Completions. See our
        [migration guide](https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages)
        for guidance in migrating from Text Completions to Messages.

        Args:
          max_tokens_to_sample: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          prompt: The prompt that you want Claude to complete.

              For proper response generation you will need to format your prompt using
              alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:

              ```
              "\n\nHuman: {userQuestion}\n\nAssistant:"
              ```

              See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and
              our guide to
              [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more
              details.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/streaming) for details.

          metadata: An object describing metadata about the request.

          stop_sequences: Sequences that will cause the model to stop generating.

              Our models stop on `"\n\nHuman:"`, and may include additional built-in stop
              sequences in the future. By providing the stop_sequences parameter, you may
              include additional strings that will cause the model to stop generating.

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens_to_sample", "model", "prompt"], ["max_tokens_to_sample", "model", "prompt", "stream"])
    async def create(
        self,
        *,
        max_tokens_to_sample: int,
        model: ModelParam,
        prompt: str,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Completion | AsyncStream[Completion]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        return await self._post(
            "/v1/complete",
            body=await async_maybe_transform(
                {
                    "max_tokens_to_sample": max_tokens_to_sample,
                    "model": model,
                    "prompt": prompt,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "temperature": temperature,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                completion_create_params.CompletionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Completion,
            stream=stream or False,
            stream_cls=AsyncStream[Completion],
        )


class CompletionsWithRawResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = _legacy_response.to_raw_response_wrapper(
            completions.create,
        )


class AsyncCompletionsWithRawResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            completions.create,
        )


class CompletionsWithStreamingResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = to_streamed_response_wrapper(
            completions.create,
        )


class AsyncCompletionsWithStreamingResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = async_to_streamed_response_wrapper(
            completions.create,
        )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\factory.py ===
import contextlib
import functools
import logging
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    cast,
)

from pip._vendor.packaging.requirements import InvalidRequirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import InvalidVersion, Version
from pip._vendor.resolvelib import ResolutionImpossible

from pip._internal.cache import CacheEntry, WheelCache
from pip._internal.exceptions import (
    DistributionNotFound,
    InstallationError,
    InvalidInstalledPackage,
    MetadataInconsistent,
    MetadataInvalid,
    UnsupportedPythonVersion,
    UnsupportedWheel,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution, get_default_environment
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req.constructors import (
    install_req_drop_extras,
    install_req_from_link_and_ireq,
)
from pip._internal.req.req_install import (
    InstallRequirement,
    check_invalid_constraint_type,
)
from pip._internal.resolution.base import InstallRequirementProvider
from pip._internal.utils.compatibility_tags import get_supported
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.virtualenv import running_under_virtualenv

from .base import Candidate, Constraint, Requirement
from .candidates import (
    AlreadyInstalledCandidate,
    BaseCandidate,
    EditableCandidate,
    ExtrasCandidate,
    LinkCandidate,
    RequiresPythonCandidate,
    as_base_candidate,
)
from .found_candidates import FoundCandidates, IndexCandidateInfo
from .requirements import (
    ExplicitRequirement,
    RequiresPythonRequirement,
    SpecifierRequirement,
    SpecifierWithoutExtrasRequirement,
    UnsatisfiableRequirement,
)

if TYPE_CHECKING:

    class ConflictCause(Protocol):
        requirement: RequiresPythonRequirement
        parent: Candidate


logger = logging.getLogger(__name__)

C = TypeVar("C")
Cache = Dict[Link, C]


class CollectedRootRequirements(NamedTuple):
    requirements: List[Requirement]
    constraints: Dict[str, Constraint]
    user_requested: Dict[str, int]


class Factory:
    def __init__(
        self,
        finder: PackageFinder,
        preparer: RequirementPreparer,
        make_install_req: InstallRequirementProvider,
        wheel_cache: Optional[WheelCache],
        use_user_site: bool,
        force_reinstall: bool,
        ignore_installed: bool,
        ignore_requires_python: bool,
        py_version_info: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self._finder = finder
        self.preparer = preparer
        self._wheel_cache = wheel_cache
        self._python_candidate = RequiresPythonCandidate(py_version_info)
        self._make_install_req_from_spec = make_install_req
        self._use_user_site = use_user_site
        self._force_reinstall = force_reinstall
        self._ignore_requires_python = ignore_requires_python

        self._build_failures: Cache[InstallationError] = {}
        self._link_candidate_cache: Cache[LinkCandidate] = {}
        self._editable_candidate_cache: Cache[EditableCandidate] = {}
        self._installed_candidate_cache: Dict[str, AlreadyInstalledCandidate] = {}
        self._extras_candidate_cache: Dict[
            Tuple[int, FrozenSet[NormalizedName]], ExtrasCandidate
        ] = {}
        self._supported_tags_cache = get_supported()

        if not ignore_installed:
            env = get_default_environment()
            self._installed_dists = {
                dist.canonical_name: dist
                for dist in env.iter_installed_distributions(local_only=False)
            }
        else:
            self._installed_dists = {}

    @property
    def force_reinstall(self) -> bool:
        return self._force_reinstall

    def _fail_if_link_is_unsupported_wheel(self, link: Link) -> None:
        if not link.is_wheel:
            return
        wheel = Wheel(link.filename)
        if wheel.supported(self._finder.target_python.get_unsorted_tags()):
            return
        msg = f"{link.filename} is not a supported wheel on this platform."
        raise UnsupportedWheel(msg)

    def _make_extras_candidate(
        self,
        base: BaseCandidate,
        extras: FrozenSet[str],
        *,
        comes_from: Optional[InstallRequirement] = None,
    ) -> ExtrasCandidate:
        cache_key = (id(base), frozenset(canonicalize_name(e) for e in extras))
        try:
            candidate = self._extras_candidate_cache[cache_key]
        except KeyError:
            candidate = ExtrasCandidate(base, extras, comes_from=comes_from)
            self._extras_candidate_cache[cache_key] = candidate
        return candidate

    def _make_candidate_from_dist(
        self,
        dist: BaseDistribution,
        extras: FrozenSet[str],
        template: InstallRequirement,
    ) -> Candidate:
        try:
            base = self._installed_candidate_cache[dist.canonical_name]
        except KeyError:
            base = AlreadyInstalledCandidate(dist, template, factory=self)
            self._installed_candidate_cache[dist.canonical_name] = base
        if not extras:
            return base
        return self._make_extras_candidate(base, extras, comes_from=template)

    def _make_candidate_from_link(
        self,
        link: Link,
        extras: FrozenSet[str],
        template: InstallRequirement,
        name: Optional[NormalizedName],
        version: Optional[Version],
    ) -> Optional[Candidate]:
        base: Optional[BaseCandidate] = self._make_base_candidate_from_link(
            link, template, name, version
        )
        if not extras or base is None:
            return base
        return self._make_extras_candidate(base, extras, comes_from=template)

    def _make_base_candidate_from_link(
        self,
        link: Link,
        template: InstallRequirement,
        name: Optional[NormalizedName],
        version: Optional[Version],
    ) -> Optional[BaseCandidate]:
        # TODO: Check already installed candidate, and use it if the link and
        # editable flag match.

        if link in self._build_failures:
            # We already tried this candidate before, and it does not build.
            # Don't bother trying again.
            return None

        if template.editable:
            if link not in self._editable_candidate_cache:
                try:
                    self._editable_candidate_cache[link] = EditableCandidate(
                        link,
                        template,
                        factory=self,
                        name=name,
                        version=version,
                    )
                except (MetadataInconsistent, MetadataInvalid) as e:
                    logger.info(
                        "Discarding [blue underline]%s[/]: [yellow]%s[reset]",
                        link,
                        e,
                        extra={"markup": True},
                    )
                    self._build_failures[link] = e
                    return None

            return self._editable_candidate_cache[link]
        else:
            if link not in self._link_candidate_cache:
                try:
                    self._link_candidate_cache[link] = LinkCandidate(
                        link,
                        template,
                        factory=self,
                        name=name,
                        version=version,
                    )
                except MetadataInconsistent as e:
                    logger.info(
                        "Discarding [blue underline]%s[/]: [yellow]%s[reset]",
                        link,
                        e,
                        extra={"markup": True},
                    )
                    self._build_failures[link] = e
                    return None
            return self._link_candidate_cache[link]

    def _iter_found_candidates(
        self,
        ireqs: Sequence[InstallRequirement],
        specifier: SpecifierSet,
        hashes: Hashes,
        prefers_installed: bool,
        incompatible_ids: Set[int],
    ) -> Iterable[Candidate]:
        if not ireqs:
            return ()

        # The InstallRequirement implementation requires us to give it a
        # "template". Here we just choose the first requirement to represent
        # all of them.
        # Hopefully the Project model can correct this mismatch in the future.
        template = ireqs[0]
        assert template.req, "Candidates found on index must be PEP 508"
        name = canonicalize_name(template.req.name)

        extras: FrozenSet[str] = frozenset()
        for ireq in ireqs:
            assert ireq.req, "Candidates found on index must be PEP 508"
            specifier &= ireq.req.specifier
            hashes &= ireq.hashes(trust_internet=False)
            extras |= frozenset(ireq.extras)

        def _get_installed_candidate() -> Optional[Candidate]:
            """Get the candidate for the currently-installed version."""
            # If --force-reinstall is set, we want the version from the index
            # instead, so we "pretend" there is nothing installed.
            if self._force_reinstall:
                return None
            try:
                installed_dist = self._installed_dists[name]
            except KeyError:
                return None

            try:
                # Don't use the installed distribution if its version
                # does not fit the current dependency graph.
                if not specifier.contains(installed_dist.version, prereleases=True):
                    return None
            except InvalidVersion as e:
                raise InvalidInstalledPackage(dist=installed_dist, invalid_exc=e)

            candidate = self._make_candidate_from_dist(
                dist=installed_dist,
                extras=extras,
                template=template,
            )
            # The candidate is a known incompatibility. Don't use it.
            if id(candidate) in incompatible_ids:
                return None
            return candidate

        def iter_index_candidate_infos() -> Iterator[IndexCandidateInfo]:
            result = self._finder.find_best_candidate(
                project_name=name,
                specifier=specifier,
                hashes=hashes,
            )
            icans = result.applicable_candidates

            # PEP 592: Yanked releases are ignored unless the specifier
            # explicitly pins a version (via '==' or '===') that can be
            # solely satisfied by a yanked release.
            all_yanked = all(ican.link.is_yanked for ican in icans)

            def is_pinned(specifier: SpecifierSet) -> bool:
                for sp in specifier:
                    if sp.operator == "===":
                        return True
                    if sp.operator != "==":
                        continue
                    if sp.version.endswith(".*"):
                        continue
                    return True
                return False

            pinned = is_pinned(specifier)

            # PackageFinder returns earlier versions first, so we reverse.
            for ican in reversed(icans):
                if not (all_yanked and pinned) and ican.link.is_yanked:
                    continue
                func = functools.partial(
                    self._make_candidate_from_link,
                    link=ican.link,
                    extras=extras,
                    template=template,
                    name=name,
                    version=ican.version,
                )
                yield ican.version, func

        return FoundCandidates(
            iter_index_candidate_infos,
            _get_installed_candidate(),
            prefers_installed,
            incompatible_ids,
        )

    def _iter_explicit_candidates_from_base(
        self,
        base_requirements: Iterable[Requirement],
        extras: FrozenSet[str],
    ) -> Iterator[Candidate]:
        """Produce explicit candidates from the base given an extra-ed package.

        :param base_requirements: Requirements known to the resolver. The
            requirements are guaranteed to not have extras.
        :param extras: The extras to inject into the explicit requirements'
            candidates.
        """
        for req in base_requirements:
            lookup_cand, _ = req.get_candidate_lookup()
            if lookup_cand is None:  # Not explicit.
                continue
            # We've stripped extras from the identifier, and should always
            # get a BaseCandidate here, unless there's a bug elsewhere.
            base_cand = as_base_candidate(lookup_cand)
            assert base_cand is not None, "no extras here"
            yield self._make_extras_candidate(base_cand, extras)

    def _iter_candidates_from_constraints(
        self,
        identifier: str,
        constraint: Constraint,
        template: InstallRequirement,
    ) -> Iterator[Candidate]:
        """Produce explicit candidates from constraints.

        This creates "fake" InstallRequirement objects that are basically clones
        of what "should" be the template, but with original_link set to link.
        """
        for link in constraint.links:
            self._fail_if_link_is_unsupported_wheel(link)
            candidate = self._make_base_candidate_from_link(
                link,
                template=install_req_from_link_and_ireq(link, template),
                name=canonicalize_name(identifier),
                version=None,
            )
            if candidate:
                yield candidate

    def find_candidates(
        self,
        identifier: str,
        requirements: Mapping[str, Iterable[Requirement]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
        constraint: Constraint,
        prefers_installed: bool,
        is_satisfied_by: Callable[[Requirement, Candidate], bool],
    ) -> Iterable[Candidate]:
        # Collect basic lookup information from the requirements.
        explicit_candidates: Set[Candidate] = set()
        ireqs: List[InstallRequirement] = []
        for req in requirements[identifier]:
            cand, ireq = req.get_candidate_lookup()
            if cand is not None:
                explicit_candidates.add(cand)
            if ireq is not None:
                ireqs.append(ireq)

        # If the current identifier contains extras, add requires and explicit
        # candidates from entries from extra-less identifier.
        with contextlib.suppress(InvalidRequirement):
            parsed_requirement = get_requirement(identifier)
            if parsed_requirement.name != identifier:
                explicit_candidates.update(
                    self._iter_explicit_candidates_from_base(
                        requirements.get(parsed_requirement.name, ()),
                        frozenset(parsed_requirement.extras),
                    ),
                )
                for req in requirements.get(parsed_requirement.name, []):
                    _, ireq = req.get_candidate_lookup()
                    if ireq is not None:
                        ireqs.append(ireq)

        # Add explicit candidates from constraints. We only do this if there are
        # known ireqs, which represent requirements not already explicit. If
        # there are no ireqs, we're constraining already-explicit requirements,
        # which is handled later when we return the explicit candidates.
        if ireqs:
            try:
                explicit_candidates.update(
                    self._iter_candidates_from_constraints(
                        identifier,
                        constraint,
                        template=ireqs[0],
                    ),
                )
            except UnsupportedWheel:
                # If we're constrained to install a wheel incompatible with the
                # target architecture, no candidates will ever be valid.
                return ()

        # Since we cache all the candidates, incompatibility identification
        # can be made quicker by comparing only the id() values.
        incompat_ids = {id(c) for c in incompatibilities.get(identifier, ())}

        # If none of the requirements want an explicit candidate, we can ask
        # the finder for candidates.
        if not explicit_candidates:
            return self._iter_found_candidates(
                ireqs,
                constraint.specifier,
                constraint.hashes,
                prefers_installed,
                incompat_ids,
            )

        return (
            c
            for c in explicit_candidates
            if id(c) not in incompat_ids
            and constraint.is_satisfied_by(c)
            and all(is_satisfied_by(req, c) for req in requirements[identifier])
        )

    def _make_requirements_from_install_req(
        self, ireq: InstallRequirement, requested_extras: Iterable[str]
    ) -> Iterator[Requirement]:
        """
        Returns requirement objects associated with the given InstallRequirement. In
        most cases this will be a single object but the following special cases exist:
            - the InstallRequirement has markers that do not apply -> result is empty
            - the InstallRequirement has both a constraint (or link) and extras
                -> result is split in two requirement objects: one with the constraint
                (or link) and one with the extra. This allows centralized constraint
                handling for the base, resulting in fewer candidate rejections.
        """
        if not ireq.match_markers(requested_extras):
            logger.info(
                "Ignoring %s: markers '%s' don't match your environment",
                ireq.name,
                ireq.markers,
            )
        elif not ireq.link:
            if ireq.extras and ireq.req is not None and ireq.req.specifier:
                yield SpecifierWithoutExtrasRequirement(ireq)
            yield SpecifierRequirement(ireq)
        else:
            self._fail_if_link_is_unsupported_wheel(ireq.link)
            # Always make the link candidate for the base requirement to make it
            # available to `find_candidates` for explicit candidate lookup for any
            # set of extras.
            # The extras are required separately via a second requirement.
            cand = self._make_base_candidate_from_link(
                ireq.link,
                template=install_req_drop_extras(ireq) if ireq.extras else ireq,
                name=canonicalize_name(ireq.name) if ireq.name else None,
                version=None,
            )
            if cand is None:
                # There's no way we can satisfy a URL requirement if the underlying
                # candidate fails to build. An unnamed URL must be user-supplied, so
                # we fail eagerly. If the URL is named, an unsatisfiable requirement
                # can make the resolver do the right thing, either backtrack (and
                # maybe find some other requirement that's buildable) or raise a
                # ResolutionImpossible eventually.
                if not ireq.name:
                    raise self._build_failures[ireq.link]
                yield UnsatisfiableRequirement(canonicalize_name(ireq.name))
            else:
                # require the base from the link
                yield self.make_requirement_from_candidate(cand)
                if ireq.extras:
                    # require the extras on top of the base candidate
                    yield self.make_requirement_from_candidate(
                        self._make_extras_candidate(cand, frozenset(ireq.extras))
                    )

    def collect_root_requirements(
        self, root_ireqs: List[InstallRequirement]
    ) -> CollectedRootRequirements:
        collected = CollectedRootRequirements([], {}, {})
        for i, ireq in enumerate(root_ireqs):
            if ireq.constraint:
                # Ensure we only accept valid constraints
                problem = check_invalid_constraint_type(ireq)
                if problem:
                    raise InstallationError(problem)
                if not ireq.match_markers():
                    continue
                assert ireq.name, "Constraint must be named"
                name = canonicalize_name(ireq.name)
                if name in collected.constraints:
                    collected.constraints[name] &= ireq
                else:
                    collected.constraints[name] = Constraint.from_ireq(ireq)
            else:
                reqs = list(
                    self._make_requirements_from_install_req(
                        ireq,
                        requested_extras=(),
                    )
                )
                if not reqs:
                    continue
                template = reqs[0]
                if ireq.user_supplied and template.name not in collected.user_requested:
                    collected.user_requested[template.name] = i
                collected.requirements.extend(reqs)
        # Put requirements with extras at the end of the root requires. This does not
        # affect resolvelib's picking preference but it does affect its initial criteria
        # population: by putting extras at the end we enable the candidate finder to
        # present resolvelib with a smaller set of candidates to resolvelib, already
        # taking into account any non-transient constraints on the associated base. This
        # means resolvelib will have fewer candidates to visit and reject.
        # Python's list sort is stable, meaning relative order is kept for objects with
        # the same key.
        collected.requirements.sort(key=lambda r: r.name != r.project_name)
        return collected

    def make_requirement_from_candidate(
        self, candidate: Candidate
    ) -> ExplicitRequirement:
        return ExplicitRequirement(candidate)

    def make_requirements_from_spec(
        self,
        specifier: str,
        comes_from: Optional[InstallRequirement],
        requested_extras: Iterable[str] = (),
    ) -> Iterator[Requirement]:
        """
        Returns requirement objects associated with the given specifier. In most cases
        this will be a single object but the following special cases exist:
            - the specifier has markers that do not apply -> result is empty
            - the specifier has both a constraint and extras -> result is split
                in two requirement objects: one with the constraint and one with the
                extra. This allows centralized constraint handling for the base,
                resulting in fewer candidate rejections.
        """
        ireq = self._make_install_req_from_spec(specifier, comes_from)
        return self._make_requirements_from_install_req(ireq, requested_extras)

    def make_requires_python_requirement(
        self,
        specifier: SpecifierSet,
    ) -> Optional[Requirement]:
        if self._ignore_requires_python:
            return None
        # Don't bother creating a dependency for an empty Requires-Python.
        if not str(specifier):
            return None
        return RequiresPythonRequirement(specifier, self._python_candidate)

    def get_wheel_cache_entry(
        self, link: Link, name: Optional[str]
    ) -> Optional[CacheEntry]:
        """Look up the link in the wheel cache.

        If ``preparer.require_hashes`` is True, don't use the wheel cache,
        because cached wheels, always built locally, have different hashes
        than the files downloaded from the index server and thus throw false
        hash mismatches. Furthermore, cached wheels at present have
        nondeterministic contents due to file modification times.
        """
        if self._wheel_cache is None:
            return None
        return self._wheel_cache.get_cache_entry(
            link=link,
            package_name=name,
            supported_tags=self._supported_tags_cache,
        )

    def get_dist_to_uninstall(self, candidate: Candidate) -> Optional[BaseDistribution]:
        # TODO: Are there more cases this needs to return True? Editable?
        dist = self._installed_dists.get(candidate.project_name)
        if dist is None:  # Not installed, no uninstallation required.
            return None

        # We're installing into global site. The current installation must
        # be uninstalled, no matter it's in global or user site, because the
        # user site installation has precedence over global.
        if not self._use_user_site:
            return dist

        # We're installing into user site. Remove the user site installation.
        if dist.in_usersite:
            return dist

        # We're installing into user site, but the installed incompatible
        # package is in global site. We can't uninstall that, and would let
        # the new user installation to "shadow" it. But shadowing won't work
        # in virtual environments, so we error out.
        if running_under_virtualenv() and dist.in_site_packages:
            message = (
                f"Will not install to the user site because it will lack "
                f"sys.path precedence to {dist.raw_name} in {dist.location}"
            )
            raise InstallationError(message)
        return None

    def _report_requires_python_error(
        self, causes: Sequence["ConflictCause"]
    ) -> UnsupportedPythonVersion:
        assert causes, "Requires-Python error reported with no cause"

        version = self._python_candidate.version

        if len(causes) == 1:
            specifier = str(causes[0].requirement.specifier)
            message = (
                f"Package {causes[0].parent.name!r} requires a different "
                f"Python: {version} not in {specifier!r}"
            )
            return UnsupportedPythonVersion(message)

        message = f"Packages require a different Python. {version} not in:"
        for cause in causes:
            package = cause.parent.format_for_error()
            specifier = str(cause.requirement.specifier)
            message += f"\n{specifier!r} (required by {package})"
        return UnsupportedPythonVersion(message)

    def _report_single_requirement_conflict(
        self, req: Requirement, parent: Optional[Candidate]
    ) -> DistributionNotFound:
        if parent is None:
            req_disp = str(req)
        else:
            req_disp = f"{req} (from {parent.name})"

        cands = self._finder.find_all_candidates(req.project_name)
        skipped_by_requires_python = self._finder.requires_python_skipped_reasons()

        versions_set: Set[Version] = set()
        yanked_versions_set: Set[Version] = set()
        for c in cands:
            is_yanked = c.link.is_yanked if c.link else False
            if is_yanked:
                yanked_versions_set.add(c.version)
            else:
                versions_set.add(c.version)

        versions = [str(v) for v in sorted(versions_set)]
        yanked_versions = [str(v) for v in sorted(yanked_versions_set)]

        if yanked_versions:
            # Saying "version X is yanked" isn't entirely accurate.
            # https://github.com/pypa/pip/issues/11745#issuecomment-1402805842
            logger.critical(
                "Ignored the following yanked versions: %s",
                ", ".join(yanked_versions) or "none",
            )
        if skipped_by_requires_python:
            logger.critical(
                "Ignored the following versions that require a different python "
                "version: %s",
                "; ".join(skipped_by_requires_python) or "none",
            )
        logger.critical(
            "Could not find a version that satisfies the requirement %s "
            "(from versions: %s)",
            req_disp,
            ", ".join(versions) or "none",
        )
        if str(req) == "requirements.txt":
            logger.info(
                "HINT: You are attempting to install a package literally "
                'named "requirements.txt" (which cannot exist). Consider '
                "using the '-r' flag to install the packages listed in "
                "requirements.txt"
            )

        return DistributionNotFound(f"No matching distribution found for {req}")

    def get_installation_error(
        self,
        e: "ResolutionImpossible[Requirement, Candidate]",
        constraints: Dict[str, Constraint],
    ) -> InstallationError:
        assert e.causes, "Installation error reported with no cause"

        # If one of the things we can't solve is "we need Python X.Y",
        # that is what we report.
        requires_python_causes = [
            cause
            for cause in e.causes
            if isinstance(cause.requirement, RequiresPythonRequirement)
            and not cause.requirement.is_satisfied_by(self._python_candidate)
        ]
        if requires_python_causes:
            # The comprehension above makes sure all Requirement instances are
            # RequiresPythonRequirement, so let's cast for convenience.
            return self._report_requires_python_error(
                cast("Sequence[ConflictCause]", requires_python_causes),
            )

        # Otherwise, we have a set of causes which can't all be satisfied
        # at once.

        # The simplest case is when we have *one* cause that can't be
        # satisfied. We just report that case.
        if len(e.causes) == 1:
            req, parent = e.causes[0]
            if req.name not in constraints:
                return self._report_single_requirement_conflict(req, parent)

        # OK, we now have a list of requirements that can't all be
        # satisfied at once.

        # A couple of formatting helpers
        def text_join(parts: List[str]) -> str:
            if len(parts) == 1:
                return parts[0]

            return ", ".join(parts[:-1]) + " and " + parts[-1]

        def describe_trigger(parent: Candidate) -> str:
            ireq = parent.get_install_requirement()
            if not ireq or not ireq.comes_from:
                return f"{parent.name}=={parent.version}"
            if isinstance(ireq.comes_from, InstallRequirement):
                return str(ireq.comes_from.name)
            return str(ireq.comes_from)

        triggers = set()
        for req, parent in e.causes:
            if parent is None:
                # This is a root requirement, so we can report it directly
                trigger = req.format_for_error()
            else:
                trigger = describe_trigger(parent)
            triggers.add(trigger)

        if triggers:
            info = text_join(sorted(triggers))
        else:
            info = "the requested packages"

        msg = (
            f"Cannot install {info} because these package versions "
            "have conflicting dependencies."
        )
        logger.critical(msg)
        msg = "\nThe conflict is caused by:"

        relevant_constraints = set()
        for req, parent in e.causes:
            if req.name in constraints:
                relevant_constraints.add(req.name)
            msg = msg + "\n    "
            if parent:
                msg = msg + f"{parent.name} {parent.version} depends on "
            else:
                msg = msg + "The user requested "
            msg = msg + req.format_for_error()
        for key in relevant_constraints:
            spec = constraints[key].specifier
            msg += f"\n    The user requested (constraint) {key}{spec}"

        msg = (
            msg
            + "\n\n"
            + "To fix this you could try to:\n"
            + "1. loosen the range of package versions you've specified\n"
            + "2. remove package versions to allow pip to attempt to solve "
            + "the dependency conflict\n"
        )

        logger.info(msg)

        return DistributionNotFound(
            "ResolutionImpossible: for help visit "
            "https://pip.pypa.io/en/latest/topics/dependency-resolution/"
            "#dealing-with-dependency-conflicts"
        )