
# === NexusCore/tools\exports\export_20250803_114325\combined_204.py ===

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\appengine.py ===
"""
This module provides a pool manager that uses Google App Engine's
`URLFetch Service <https://cloud.google.com/appengine/docs/python/urlfetch>`_.

Example usage::

    from pip._vendor.urllib3 import PoolManager
    from pip._vendor.urllib3.contrib.appengine import AppEngineManager, is_appengine_sandbox

    if is_appengine_sandbox():
        # AppEngineManager uses AppEngine's URLFetch API behind the scenes
        http = AppEngineManager()
    else:
        # PoolManager uses a socket-level API behind the scenes
        http = PoolManager()

    r = http.request('GET', 'https://google.com/')

There are `limitations <https://cloud.google.com/appengine/docs/python/\
urlfetch/#Python_Quotas_and_limits>`_ to the URLFetch service and it may not be
the best choice for your application. There are three options for using
urllib3 on Google App Engine:

1. You can use :class:`AppEngineManager` with URLFetch. URLFetch is
   cost-effective in many circumstances as long as your usage is within the
   limitations.
2. You can use a normal :class:`~urllib3.PoolManager` by enabling sockets.
   Sockets also have `limitations and restrictions
   <https://cloud.google.com/appengine/docs/python/sockets/\
   #limitations-and-restrictions>`_ and have a lower free quota than URLFetch.
   To use sockets, be sure to specify the following in your ``app.yaml``::

        env_variables:
            GAE_USE_SOCKETS_HTTPLIB : 'true'

3. If you are using `App Engine Flexible
<https://cloud.google.com/appengine/docs/flexible/>`_, you can use the standard
:class:`PoolManager` without any configuration or special environment variables.
"""

from __future__ import absolute_import

import io
import logging
import warnings

from ..exceptions import (
    HTTPError,
    HTTPWarning,
    MaxRetryError,
    ProtocolError,
    SSLError,
    TimeoutError,
)
from ..packages.six.moves.urllib.parse import urljoin
from ..request import RequestMethods
from ..response import HTTPResponse
from ..util.retry import Retry
from ..util.timeout import Timeout
from . import _appengine_environ

try:
    from google.appengine.api import urlfetch
except ImportError:
    urlfetch = None


log = logging.getLogger(__name__)


class AppEnginePlatformWarning(HTTPWarning):
    pass


class AppEnginePlatformError(HTTPError):
    pass


class AppEngineManager(RequestMethods):
    """
    Connection manager for Google App Engine sandbox applications.

    This manager uses the URLFetch service directly instead of using the
    emulated httplib, and is subject to URLFetch limitations as described in
    the App Engine documentation `here
    <https://cloud.google.com/appengine/docs/python/urlfetch>`_.

    Notably it will raise an :class:`AppEnginePlatformError` if:
        * URLFetch is not available.
        * If you attempt to use this on App Engine Flexible, as full socket
          support is available.
        * If a request size is more than 10 megabytes.
        * If a response size is more than 32 megabytes.
        * If you use an unsupported request method such as OPTIONS.

    Beyond those cases, it will raise normal urllib3 errors.
    """

    def __init__(
        self,
        headers=None,
        retries=None,
        validate_certificate=True,
        urlfetch_retries=True,
    ):
        if not urlfetch:
            raise AppEnginePlatformError(
                "URLFetch is not available in this environment."
            )

        warnings.warn(
            "urllib3 is using URLFetch on Google App Engine sandbox instead "
            "of sockets. To use sockets directly instead of URLFetch see "
            "https://urllib3.readthedocs.io/en/1.26.x/reference/urllib3.contrib.html.",
            AppEnginePlatformWarning,
        )

        RequestMethods.__init__(self, headers)
        self.validate_certificate = validate_certificate
        self.urlfetch_retries = urlfetch_retries

        self.retries = retries or Retry.DEFAULT

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Return False to re-raise any potential exceptions
        return False

    def urlopen(
        self,
        method,
        url,
        body=None,
        headers=None,
        retries=None,
        redirect=True,
        timeout=Timeout.DEFAULT_TIMEOUT,
        **response_kw
    ):

        retries = self._get_retries(retries, redirect)

        try:
            follow_redirects = redirect and retries.redirect != 0 and retries.total
            response = urlfetch.fetch(
                url,
                payload=body,
                method=method,
                headers=headers or {},
                allow_truncated=False,
                follow_redirects=self.urlfetch_retries and follow_redirects,
                deadline=self._get_absolute_timeout(timeout),
                validate_certificate=self.validate_certificate,
            )
        except urlfetch.DeadlineExceededError as e:
            raise TimeoutError(self, e)

        except urlfetch.InvalidURLError as e:
            if "too large" in str(e):
                raise AppEnginePlatformError(
                    "URLFetch request too large, URLFetch only "
                    "supports requests up to 10mb in size.",
                    e,
                )
            raise ProtocolError(e)

        except urlfetch.DownloadError as e:
            if "Too many redirects" in str(e):
                raise MaxRetryError(self, url, reason=e)
            raise ProtocolError(e)

        except urlfetch.ResponseTooLargeError as e:
            raise AppEnginePlatformError(
                "URLFetch response too large, URLFetch only supports"
                "responses up to 32mb in size.",
                e,
            )

        except urlfetch.SSLCertificateError as e:
            raise SSLError(e)

        except urlfetch.InvalidMethodError as e:
            raise AppEnginePlatformError(
                "URLFetch does not support method: %s" % method, e
            )

        http_response = self._urlfetch_response_to_http_response(
            response, retries=retries, **response_kw
        )

        # Handle redirect?
        redirect_location = redirect and http_response.get_redirect_location()
        if redirect_location:
            # Check for redirect response
            if self.urlfetch_retries and retries.raise_on_redirect:
                raise MaxRetryError(self, url, "too many redirects")
            else:
                if http_response.status == 303:
                    method = "GET"

                try:
                    retries = retries.increment(
                        method, url, response=http_response, _pool=self
                    )
                except MaxRetryError:
                    if retries.raise_on_redirect:
                        raise MaxRetryError(self, url, "too many redirects")
                    return http_response

                retries.sleep_for_retry(http_response)
                log.debug("Redirecting %s -> %s", url, redirect_location)
                redirect_url = urljoin(url, redirect_location)
                return self.urlopen(
                    method,
                    redirect_url,
                    body,
                    headers,
                    retries=retries,
                    redirect=redirect,
                    timeout=timeout,
                    **response_kw
                )

        # Check if we should retry the HTTP response.
        has_retry_after = bool(http_response.headers.get("Retry-After"))
        if retries.is_retry(method, http_response.status, has_retry_after):
            retries = retries.increment(method, url, response=http_response, _pool=self)
            log.debug("Retry: %s", url)
            retries.sleep(http_response)
            return self.urlopen(
                method,
                url,
                body=body,
                headers=headers,
                retries=retries,
                redirect=redirect,
                timeout=timeout,
                **response_kw
            )

        return http_response

    def _urlfetch_response_to_http_response(self, urlfetch_resp, **response_kw):

        if is_prod_appengine():
            # Production GAE handles deflate encoding automatically, but does
            # not remove the encoding header.
            content_encoding = urlfetch_resp.headers.get("content-encoding")

            if content_encoding == "deflate":
                del urlfetch_resp.headers["content-encoding"]

        transfer_encoding = urlfetch_resp.headers.get("transfer-encoding")
        # We have a full response's content,
        # so let's make sure we don't report ourselves as chunked data.
        if transfer_encoding == "chunked":
            encodings = transfer_encoding.split(",")
            encodings.remove("chunked")
            urlfetch_resp.headers["transfer-encoding"] = ",".join(encodings)

        original_response = HTTPResponse(
            # In order for decoding to work, we must present the content as
            # a file-like object.
            body=io.BytesIO(urlfetch_resp.content),
            msg=urlfetch_resp.header_msg,
            headers=urlfetch_resp.headers,
            status=urlfetch_resp.status_code,
            **response_kw
        )

        return HTTPResponse(
            body=io.BytesIO(urlfetch_resp.content),
            headers=urlfetch_resp.headers,
            status=urlfetch_resp.status_code,
            original_response=original_response,
            **response_kw
        )

    def _get_absolute_timeout(self, timeout):
        if timeout is Timeout.DEFAULT_TIMEOUT:
            return None  # Defer to URLFetch's default.
        if isinstance(timeout, Timeout):
            if timeout._read is not None or timeout._connect is not None:
                warnings.warn(
                    "URLFetch does not support granular timeout settings, "
                    "reverting to total or default URLFetch timeout.",
                    AppEnginePlatformWarning,
                )
            return timeout.total
        return timeout

    def _get_retries(self, retries, redirect):
        if not isinstance(retries, Retry):
            retries = Retry.from_int(retries, redirect=redirect, default=self.retries)

        if retries.connect or retries.read or retries.redirect:
            warnings.warn(
                "URLFetch only supports total retries and does not "
                "recognize connect, read, or redirect retry parameters.",
                AppEnginePlatformWarning,
            )

        return retries


# Alias methods from _appengine_environ to maintain public API interface.

is_appengine = _appengine_environ.is_appengine
is_appengine_sandbox = _appengine_environ.is_appengine_sandbox
is_local_appengine = _appengine_environ.is_local_appengine
is_prod_appengine = _appengine_environ.is_prod_appengine
is_prod_appengine_mvms = _appengine_environ.is_prod_appengine_mvms

# === NexusCore/openenv\Lib\site-packages\pyparsing\exceptions.py ===
# exceptions.py
from __future__ import annotations

import copy
import re
import sys
import typing
from functools import cached_property

from .unicode import pyparsing_unicode as ppu
from .util import (
    _collapse_string_to_ranges,
    col,
    line,
    lineno,
    replaced_by_pep8,
)


class _ExceptionWordUnicodeSet(
    ppu.Latin1, ppu.LatinA, ppu.LatinB, ppu.Greek, ppu.Cyrillic
):
    pass


_extract_alphanums = _collapse_string_to_ranges(_ExceptionWordUnicodeSet.alphanums)
_exception_word_extractor = re.compile("([" + _extract_alphanums + "]{1,16})|.")


class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""

    loc: int
    msg: str
    pstr: str
    parser_element: typing.Any  # "ParserElement"
    args: tuple[str, int, typing.Optional[str]]

    __slots__ = (
        "loc",
        "msg",
        "pstr",
        "parser_element",
        "args",
    )

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__(
        self,
        pstr: str,
        loc: int = 0,
        msg: typing.Optional[str] = None,
        elem=None,
    ) -> None:
        if msg is None:
            msg, pstr = pstr, ""

        self.loc = loc
        self.msg = msg
        self.pstr = pstr
        self.parser_element = elem
        self.args = (pstr, loc, msg)

    @staticmethod
    def explain_exception(exc: Exception, depth: int = 16) -> str:
        """
        Method to take an exception and translate the Python internal traceback into a list
        of the pyparsing expressions that caused the exception to be raised.

        Parameters:

        - exc - exception raised during parsing (need not be a ParseException, in support
          of Python exceptions that might be raised in a parse action)
        - depth (default=16) - number of levels back in the stack trace to list expression
          and function names; if None, the full stack trace names will be listed; if 0, only
          the failing input line, marker, and exception string will be shown

        Returns a multi-line string listing the ParserElements and/or function names in the
        exception's stack trace.
        """
        import inspect
        from .core import ParserElement

        if depth is None:
            depth = sys.getrecursionlimit()
        ret: list[str] = []
        if isinstance(exc, ParseBaseException):
            ret.append(exc.line)
            ret.append(f"{'^':>{exc.column}}")
        ret.append(f"{type(exc).__name__}: {exc}")

        if depth <= 0 or exc.__traceback__ is None:
            return "\n".join(ret)

        callers = inspect.getinnerframes(exc.__traceback__, context=depth)
        seen: set[int] = set()
        for ff in callers[-depth:]:
            frm = ff[0]

            f_self = frm.f_locals.get("self", None)
            if isinstance(f_self, ParserElement):
                if not frm.f_code.co_name.startswith(("parseImpl", "_parseNoCache")):
                    continue
                if id(f_self) in seen:
                    continue
                seen.add(id(f_self))

                self_type = type(f_self)
                ret.append(f"{self_type.__module__}.{self_type.__name__} - {f_self}")

            elif f_self is not None:
                self_type = type(f_self)
                ret.append(f"{self_type.__module__}.{self_type.__name__}")

            else:
                code = frm.f_code
                if code.co_name in ("wrapper", "<module>"):
                    continue

                ret.append(code.co_name)

            depth -= 1
            if not depth:
                break

        return "\n".join(ret)

    @classmethod
    def _from_exception(cls, pe) -> ParseBaseException:
        """
        internal factory method to simplify creating one type of ParseException
        from another - avoids having __init__ signature conflicts among subclasses
        """
        return cls(pe.pstr, pe.loc, pe.msg, pe.parser_element)

    @cached_property
    def line(self) -> str:
        """
        Return the line of text where the exception occurred.
        """
        return line(self.loc, self.pstr)

    @cached_property
    def lineno(self) -> int:
        """
        Return the 1-based line number of text where the exception occurred.
        """
        return lineno(self.loc, self.pstr)

    @cached_property
    def col(self) -> int:
        """
        Return the 1-based column on the line of text where the exception occurred.
        """
        return col(self.loc, self.pstr)

    @cached_property
    def column(self) -> int:
        """
        Return the 1-based column on the line of text where the exception occurred.
        """
        return col(self.loc, self.pstr)

    @cached_property
    def found(self) -> str:
        if not self.pstr:
            return ""

        if self.loc >= len(self.pstr):
            return "end of text"

        # pull out next word at error location
        found_match = _exception_word_extractor.match(self.pstr, self.loc)
        if found_match is not None:
            found_text = found_match.group(0)
        else:
            found_text = self.pstr[self.loc : self.loc + 1]

        return repr(found_text).replace(r"\\", "\\")

    # pre-PEP8 compatibility
    @property
    def parserElement(self):
        return self.parser_element

    @parserElement.setter
    def parserElement(self, elem):
        self.parser_element = elem

    def copy(self):
        return copy.copy(self)

    def formatted_message(self) -> str:
        found_phrase = f", found {self.found}" if self.found else ""
        return f"{self.msg}{found_phrase}  (at char {self.loc}), (line:{self.lineno}, col:{self.column})"

    def __str__(self) -> str:
        return self.formatted_message()

    def __repr__(self):
        return str(self)

    def mark_input_line(
        self, marker_string: typing.Optional[str] = None, *, markerString: str = ">!<"
    ) -> str:
        """
        Extracts the exception line from the input string, and marks
        the location of the exception with a special symbol.
        """
        markerString = marker_string if marker_string is not None else markerString
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = f"{line_str[:line_column]}{markerString}{line_str[line_column:]}"
        return line_str.strip()

    def explain(self, depth: int = 16) -> str:
        """
        Method to translate the Python internal traceback into a list
        of the pyparsing expressions that caused the exception to be raised.

        Parameters:

        - depth (default=16) - number of levels back in the stack trace to list expression
          and function names; if None, the full stack trace names will be listed; if 0, only
          the failing input line, marker, and exception string will be shown

        Returns a multi-line string listing the ParserElements and/or function names in the
        exception's stack trace.

        Example::

            # an expression to parse 3 integers
            expr = pp.Word(pp.nums) * 3
            try:
                # a failing parse - the third integer is prefixed with "A"
                expr.parse_string("123 456 A789")
            except pp.ParseException as pe:
                print(pe.explain(depth=0))

        prints::

            123 456 A789
                    ^
            ParseException: Expected W:(0-9), found 'A'  (at char 8), (line:1, col:9)

        Note: the diagnostic output will include string representations of the expressions
        that failed to parse. These representations will be more helpful if you use `set_name` to
        give identifiable names to your expressions. Otherwise they will use the default string
        forms, which may be cryptic to read.

        Note: pyparsing's default truncation of exception tracebacks may also truncate the
        stack of expressions that are displayed in the ``explain`` output. To get the full listing
        of parser expressions, you may have to set ``ParserElement.verbose_stacktrace = True``
        """
        return self.explain_exception(self, depth)

    # Compatibility synonyms
    # fmt: off
    markInputline = replaced_by_pep8("markInputline", mark_input_line)
    # fmt: on


class ParseException(ParseBaseException):
    """
    Exception thrown when a parse expression doesn't match the input string

    Example::

        integer = Word(nums).set_name("integer")
        try:
            integer.parse_string("ABC")
        except ParseException as pe:
            print(pe, f"column: {pe.column}")

    prints::

       Expected integer, found 'ABC'  (at char 0), (line:1, col:1) column: 1

    """


class ParseFatalException(ParseBaseException):
    """
    User-throwable exception thrown when inconsistent parse content
    is found; stops all parsing immediately
    """


class ParseSyntaxException(ParseFatalException):
    """
    Just like :class:`ParseFatalException`, but thrown internally
    when an :class:`ErrorStop<And._ErrorStop>` ('-' operator) indicates
    that parsing is to stop immediately because an unbacktrackable
    syntax error has been found.
    """


class RecursiveGrammarException(Exception):
    """
    Exception thrown by :class:`ParserElement.validate` if the
    grammar could be left-recursive; parser may need to enable
    left recursion using :class:`ParserElement.enable_left_recursion<ParserElement.enable_left_recursion>`

    Deprecated: only used by deprecated method ParserElement.validate.
    """

    def __init__(self, parseElementList) -> None:
        self.parseElementTrace = parseElementList

    def __str__(self) -> str:
        return f"RecursiveGrammarException: {self.parseElementTrace}"

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\align.py ===
import sys
from itertools import chain
from typing import TYPE_CHECKING, Iterable, Optional

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover

from .constrain import Constrain
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import StyleType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult

AlignMethod = Literal["left", "center", "right"]
VerticalAlignMethod = Literal["top", "middle", "bottom"]


class Align(JupyterMixin):
    """Align a renderable by adding spaces if necessary.

    Args:
        renderable (RenderableType): A console renderable.
        align (AlignMethod): One of "left", "center", or "right""
        style (StyleType, optional): An optional style to apply to the background.
        vertical (Optional[VerticalAlignMethod], optional): Optional vertical align, one of "top", "middle", or "bottom". Defaults to None.
        pad (bool, optional): Pad the right with spaces. Defaults to True.
        width (int, optional): Restrict contents to given width, or None to use default width. Defaults to None.
        height (int, optional): Set height of align renderable, or None to fit to contents. Defaults to None.

    Raises:
        ValueError: if ``align`` is not one of the expected values.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        align: AlignMethod = "left",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        if align not in ("left", "center", "right"):
            raise ValueError(
                f'invalid value for align, expected "left", "center", or "right" (not {align!r})'
            )
        if vertical is not None and vertical not in ("top", "middle", "bottom"):
            raise ValueError(
                f'invalid value for vertical, expected "top", "middle", or "bottom" (not {vertical!r})'
            )
        self.renderable = renderable
        self.align = align
        self.style = style
        self.vertical = vertical
        self.pad = pad
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Align({self.renderable!r}, {self.align!r})"

    @classmethod
    def left(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the left."""
        return cls(
            renderable,
            "left",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def center(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the center."""
        return cls(
            renderable,
            "center",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def right(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the right."""
        return cls(
            renderable,
            "right",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        align = self.align
        width = console.measure(self.renderable, options=options).maximum
        rendered = console.render(
            Constrain(
                self.renderable, width if self.width is None else min(width, self.width)
            ),
            options.update(height=None),
        )
        lines = list(Segment.split_lines(rendered))
        width, height = Segment.get_shape(lines)
        lines = Segment.set_shape(lines, width, height)
        new_line = Segment.line()
        excess_space = options.max_width - width
        style = console.get_style(self.style) if self.style is not None else None

        def generate_segments() -> Iterable[Segment]:
            if excess_space <= 0:
                # Exact fit
                for line in lines:
                    yield from line
                    yield new_line

            elif align == "left":
                # Pad on the right
                pad = Segment(" " * excess_space, style) if self.pad else None
                for line in lines:
                    yield from line
                    if pad:
                        yield pad
                    yield new_line

            elif align == "center":
                # Pad left and right
                left = excess_space // 2
                pad = Segment(" " * left, style)
                pad_right = (
                    Segment(" " * (excess_space - left), style) if self.pad else None
                )
                for line in lines:
                    if left:
                        yield pad
                    yield from line
                    if pad_right:
                        yield pad_right
                    yield new_line

            elif align == "right":
                # Padding on left
                pad = Segment(" " * excess_space, style)
                for line in lines:
                    yield pad
                    yield from line
                    yield new_line

        blank_line = (
            Segment(f"{' ' * (self.width or options.max_width)}\n", style)
            if self.pad
            else Segment("\n")
        )

        def blank_lines(count: int) -> Iterable[Segment]:
            if count > 0:
                for _ in range(count):
                    yield blank_line

        vertical_height = self.height or options.height
        iter_segments: Iterable[Segment]
        if self.vertical and vertical_height is not None:
            if self.vertical == "top":
                bottom_space = vertical_height - height
                iter_segments = chain(generate_segments(), blank_lines(bottom_space))
            elif self.vertical == "middle":
                top_space = (vertical_height - height) // 2
                bottom_space = vertical_height - top_space - height
                iter_segments = chain(
                    blank_lines(top_space),
                    generate_segments(),
                    blank_lines(bottom_space),
                )
            else:  #  self.vertical == "bottom":
                top_space = vertical_height - height
                iter_segments = chain(blank_lines(top_space), generate_segments())
        else:
            iter_segments = generate_segments()
        if self.style:
            style = console.get_style(self.style)
            iter_segments = Segment.apply_style(iter_segments, style)
        yield from iter_segments

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


class VerticalCenter(JupyterMixin):
    """Vertically aligns a renderable.

    Warn:
        This class is deprecated and may be removed in a future version. Use Align class with
        `vertical="middle"`.

    Args:
        renderable (RenderableType): A renderable object.
        style (StyleType, optional): An optional style to apply to the background. Defaults to None.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
    ) -> None:
        self.renderable = renderable
        self.style = style

    def __repr__(self) -> str:
        return f"VerticalCenter({self.renderable!r})"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style) if self.style is not None else None
        lines = console.render_lines(
            self.renderable, options.update(height=None), pad=False
        )
        width, _height = Segment.get_shape(lines)
        new_line = Segment.line()
        height = options.height or options.size.height
        top_space = (height - len(lines)) // 2
        bottom_space = height - top_space - len(lines)
        blank_line = Segment(f"{' ' * width}", style)

        def blank_lines(count: int) -> Iterable[Segment]:
            for _ in range(count):
                yield blank_line
                yield new_line

        if top_space > 0:
            yield from blank_lines(top_space)
        for line in lines:
            yield from line
            yield new_line
        if bottom_space > 0:
            yield from blank_lines(bottom_space)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console, Group
    from pip._vendor.rich.highlighter import ReprHighlighter
    from pip._vendor.rich.panel import Panel

    highlighter = ReprHighlighter()
    console = Console()

    panel = Panel(
        Group(
            Align.left(highlighter("align='left'")),
            Align.center(highlighter("align='center'")),
            Align.right(highlighter("align='right'")),
        ),
        width=60,
        style="on dark_blue",
        title="Align",
    )

    console.print(
        Align.center(panel, vertical="middle", style="on red", height=console.height)
    )

# === NexusCore/openenv\Lib\site-packages\litellm\_service_logger.py ===
import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional, Union

import litellm
from litellm._logging import verbose_logger
from litellm.proxy._types import UserAPIKeyAuth

from .integrations.custom_logger import CustomLogger
from .integrations.datadog.datadog import DataDogLogger
from .integrations.opentelemetry import OpenTelemetry
from .integrations.prometheus_services import PrometheusServicesLogger
from .types.services import ServiceLoggerPayload, ServiceTypes

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
    OTELClass = OpenTelemetry
else:
    Span = Any
    OTELClass = Any


class ServiceLogging(CustomLogger):
    """
    Separate class used for monitoring health of litellm-adjacent services (redis/postgres).
    """

    def __init__(self, mock_testing: bool = False) -> None:
        self.mock_testing = mock_testing
        self.mock_testing_sync_success_hook = 0
        self.mock_testing_async_success_hook = 0
        self.mock_testing_sync_failure_hook = 0
        self.mock_testing_async_failure_hook = 0
        if "prometheus_system" in litellm.service_callback:
            self.prometheusServicesLogger = PrometheusServicesLogger()

    def service_success_hook(
        self,
        service: ServiceTypes,
        duration: float,
        call_type: str,
        parent_otel_span: Optional[Span] = None,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[float, datetime]] = None,
    ):
        """
        Handles both sync and async monitoring by checking for existing event loop.
        """

        if self.mock_testing:
            self.mock_testing_sync_success_hook += 1

        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            # Check if the loop is running
            if loop.is_running():
                # If we're in a running loop, create a task
                loop.create_task(
                    self.async_service_success_hook(
                        service=service,
                        duration=duration,
                        call_type=call_type,
                        parent_otel_span=parent_otel_span,
                        start_time=start_time,
                        end_time=end_time,
                    )
                )
            else:
                # Loop exists but not running, we can use run_until_complete
                loop.run_until_complete(
                    self.async_service_success_hook(
                        service=service,
                        duration=duration,
                        call_type=call_type,
                        parent_otel_span=parent_otel_span,
                        start_time=start_time,
                        end_time=end_time,
                    )
                )
        except RuntimeError:
            # No event loop exists, create a new one and run
            asyncio.run(
                self.async_service_success_hook(
                    service=service,
                    duration=duration,
                    call_type=call_type,
                    parent_otel_span=parent_otel_span,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

    def service_failure_hook(
        self, service: ServiceTypes, duration: float, error: Exception, call_type: str
    ):
        """
        [TODO] Not implemented for sync calls yet. V0 is focused on async monitoring (used by proxy).
        """
        if self.mock_testing:
            self.mock_testing_sync_failure_hook += 1

    async def async_service_success_hook(
        self,
        service: ServiceTypes,
        call_type: str,
        duration: float,
        parent_otel_span: Optional[Span] = None,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[datetime, float]] = None,
        event_metadata: Optional[dict] = None,
    ):
        """
        - For counting if the redis, postgres call is successful
        """
        if self.mock_testing:
            self.mock_testing_async_success_hook += 1

        payload = ServiceLoggerPayload(
            is_error=False,
            error=None,
            service=service,
            duration=duration,
            call_type=call_type,
            event_metadata=event_metadata,
        )

        for callback in litellm.service_callback:
            if callback == "prometheus_system":
                await self.init_prometheus_services_logger_if_none()
                await self.prometheusServicesLogger.async_service_success_hook(
                    payload=payload
                )
            elif callback == "datadog" or isinstance(callback, DataDogLogger):
                await self.init_datadog_logger_if_none()
                await self.dd_logger.async_service_success_hook(
                    payload=payload,
                    parent_otel_span=parent_otel_span,
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata=event_metadata,
                )
            elif callback == "otel" or isinstance(callback, OpenTelemetry):
                from litellm.proxy.proxy_server import open_telemetry_logger

                await self.init_otel_logger_if_none()

                if (
                    parent_otel_span is not None
                    and open_telemetry_logger is not None
                    and isinstance(open_telemetry_logger, OpenTelemetry)
                ):
                    await self.otel_logger.async_service_success_hook(
                        payload=payload,
                        parent_otel_span=parent_otel_span,
                        start_time=start_time,
                        end_time=end_time,
                        event_metadata=event_metadata,
                    )

    async def init_prometheus_services_logger_if_none(self):
        """
        initializes prometheusServicesLogger if it is None or no attribute exists on ServiceLogging Object

        """
        if not hasattr(self, "prometheusServicesLogger"):
            self.prometheusServicesLogger = PrometheusServicesLogger()
        elif self.prometheusServicesLogger is None:
            self.prometheusServicesLogger = self.prometheusServicesLogger()
        return

    async def init_datadog_logger_if_none(self):
        """
        initializes dd_logger if it is None or no attribute exists on ServiceLogging Object

        """
        from litellm.integrations.datadog.datadog import DataDogLogger

        if not hasattr(self, "dd_logger"):
            self.dd_logger: DataDogLogger = DataDogLogger()

        return

    async def init_otel_logger_if_none(self):
        """
        initializes otel_logger if it is None or no attribute exists on ServiceLogging Object

        """
        from litellm.proxy.proxy_server import open_telemetry_logger

        if not hasattr(self, "otel_logger"):
            if open_telemetry_logger is not None and isinstance(
                open_telemetry_logger, OpenTelemetry
            ):
                self.otel_logger: OpenTelemetry = open_telemetry_logger
            else:
                verbose_logger.warning(
                    "ServiceLogger: open_telemetry_logger is None or not an instance of OpenTelemetry"
                )
        return

    async def async_service_failure_hook(
        self,
        service: ServiceTypes,
        duration: float,
        error: Union[str, Exception],
        call_type: str,
        parent_otel_span: Optional[Span] = None,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[float, datetime]] = None,
        event_metadata: Optional[dict] = None,
    ):
        """
        - For counting if the redis, postgres call is unsuccessful
        """
        if self.mock_testing:
            self.mock_testing_async_failure_hook += 1

        error_message = ""
        if isinstance(error, Exception):
            error_message = str(error)
        elif isinstance(error, str):
            error_message = error

        payload = ServiceLoggerPayload(
            is_error=True,
            error=error_message,
            service=service,
            duration=duration,
            call_type=call_type,
            event_metadata=event_metadata,
        )

        for callback in litellm.service_callback:
            if callback == "prometheus_system":
                await self.init_prometheus_services_logger_if_none()
                await self.prometheusServicesLogger.async_service_failure_hook(
                    payload=payload,
                    error=error,
                )
            elif callback == "datadog" or isinstance(callback, DataDogLogger):
                await self.init_datadog_logger_if_none()
                await self.dd_logger.async_service_failure_hook(
                    payload=payload,
                    error=error_message,
                    parent_otel_span=parent_otel_span,
                    start_time=start_time,
                    end_time=end_time,
                    event_metadata=event_metadata,
                )
            elif callback == "otel" or isinstance(callback, OpenTelemetry):
                from litellm.proxy.proxy_server import open_telemetry_logger

                await self.init_otel_logger_if_none()

                if not isinstance(error, str):
                    error = str(error)

                if (
                    parent_otel_span is not None
                    and open_telemetry_logger is not None
                    and isinstance(open_telemetry_logger, OpenTelemetry)
                ):
                    await self.otel_logger.async_service_success_hook(
                        payload=payload,
                        parent_otel_span=parent_otel_span,
                        start_time=start_time,
                        end_time=end_time,
                        event_metadata=event_metadata,
                    )

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        """
        Hook to track failed litellm-service calls
        """
        return await super().async_post_call_failure_hook(
            request_data,
            original_exception,
            user_api_key_dict,
        )

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """
        Hook to track latency for litellm proxy llm api calls
        """
        try:
            _duration = end_time - start_time
            if isinstance(_duration, timedelta):
                _duration = _duration.total_seconds()
            elif isinstance(_duration, float):
                pass
            else:
                raise Exception(
                    "Duration={} is not a float or timedelta object. type={}".format(
                        _duration, type(_duration)
                    )
                )  # invalid _duration value
            await self.async_service_success_hook(
                service=ServiceTypes.LITELLM,
                duration=_duration,
                call_type=kwargs["call_type"],
            )
        except Exception as e:
            raise e

# === NexusCore/openenv\Lib\site-packages\rich\align.py ===
import sys
from itertools import chain
from typing import TYPE_CHECKING, Iterable, Optional

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover

from .constrain import Constrain
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import StyleType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult

AlignMethod = Literal["left", "center", "right"]
VerticalAlignMethod = Literal["top", "middle", "bottom"]


class Align(JupyterMixin):
    """Align a renderable by adding spaces if necessary.

    Args:
        renderable (RenderableType): A console renderable.
        align (AlignMethod): One of "left", "center", or "right""
        style (StyleType, optional): An optional style to apply to the background.
        vertical (Optional[VerticalAlignMethod], optional): Optional vertical align, one of "top", "middle", or "bottom". Defaults to None.
        pad (bool, optional): Pad the right with spaces. Defaults to True.
        width (int, optional): Restrict contents to given width, or None to use default width. Defaults to None.
        height (int, optional): Set height of align renderable, or None to fit to contents. Defaults to None.

    Raises:
        ValueError: if ``align`` is not one of the expected values.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        align: AlignMethod = "left",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        if align not in ("left", "center", "right"):
            raise ValueError(
                f'invalid value for align, expected "left", "center", or "right" (not {align!r})'
            )
        if vertical is not None and vertical not in ("top", "middle", "bottom"):
            raise ValueError(
                f'invalid value for vertical, expected "top", "middle", or "bottom" (not {vertical!r})'
            )
        self.renderable = renderable
        self.align = align
        self.style = style
        self.vertical = vertical
        self.pad = pad
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Align({self.renderable!r}, {self.align!r})"

    @classmethod
    def left(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the left."""
        return cls(
            renderable,
            "left",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def center(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the center."""
        return cls(
            renderable,
            "center",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def right(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the right."""
        return cls(
            renderable,
            "right",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        align = self.align
        width = console.measure(self.renderable, options=options).maximum
        rendered = console.render(
            Constrain(
                self.renderable, width if self.width is None else min(width, self.width)
            ),
            options.update(height=None),
        )
        lines = list(Segment.split_lines(rendered))
        width, height = Segment.get_shape(lines)
        lines = Segment.set_shape(lines, width, height)
        new_line = Segment.line()
        excess_space = options.max_width - width
        style = console.get_style(self.style) if self.style is not None else None

        def generate_segments() -> Iterable[Segment]:
            if excess_space <= 0:
                # Exact fit
                for line in lines:
                    yield from line
                    yield new_line

            elif align == "left":
                # Pad on the right
                pad = Segment(" " * excess_space, style) if self.pad else None
                for line in lines:
                    yield from line
                    if pad:
                        yield pad
                    yield new_line

            elif align == "center":
                # Pad left and right
                left = excess_space // 2
                pad = Segment(" " * left, style)
                pad_right = (
                    Segment(" " * (excess_space - left), style) if self.pad else None
                )
                for line in lines:
                    if left:
                        yield pad
                    yield from line
                    if pad_right:
                        yield pad_right
                    yield new_line

            elif align == "right":
                # Padding on left
                pad = Segment(" " * excess_space, style)
                for line in lines:
                    yield pad
                    yield from line
                    yield new_line

        blank_line = (
            Segment(f"{' ' * (self.width or options.max_width)}\n", style)
            if self.pad
            else Segment("\n")
        )

        def blank_lines(count: int) -> Iterable[Segment]:
            if count > 0:
                for _ in range(count):
                    yield blank_line

        vertical_height = self.height or options.height
        iter_segments: Iterable[Segment]
        if self.vertical and vertical_height is not None:
            if self.vertical == "top":
                bottom_space = vertical_height - height
                iter_segments = chain(generate_segments(), blank_lines(bottom_space))
            elif self.vertical == "middle":
                top_space = (vertical_height - height) // 2
                bottom_space = vertical_height - top_space - height
                iter_segments = chain(
                    blank_lines(top_space),
                    generate_segments(),
                    blank_lines(bottom_space),
                )
            else:  #  self.vertical == "bottom":
                top_space = vertical_height - height
                iter_segments = chain(blank_lines(top_space), generate_segments())
        else:
            iter_segments = generate_segments()
        if self.style:
            style = console.get_style(self.style)
            iter_segments = Segment.apply_style(iter_segments, style)
        yield from iter_segments

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


class VerticalCenter(JupyterMixin):
    """Vertically aligns a renderable.

    Warn:
        This class is deprecated and may be removed in a future version. Use Align class with
        `vertical="middle"`.

    Args:
        renderable (RenderableType): A renderable object.
        style (StyleType, optional): An optional style to apply to the background. Defaults to None.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
    ) -> None:
        self.renderable = renderable
        self.style = style

    def __repr__(self) -> str:
        return f"VerticalCenter({self.renderable!r})"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style) if self.style is not None else None
        lines = console.render_lines(
            self.renderable, options.update(height=None), pad=False
        )
        width, _height = Segment.get_shape(lines)
        new_line = Segment.line()
        height = options.height or options.size.height
        top_space = (height - len(lines)) // 2
        bottom_space = height - top_space - len(lines)
        blank_line = Segment(f"{' ' * width}", style)

        def blank_lines(count: int) -> Iterable[Segment]:
            for _ in range(count):
                yield blank_line
                yield new_line

        if top_space > 0:
            yield from blank_lines(top_space)
        for line in lines:
            yield from line
            yield new_line
        if bottom_space > 0:
            yield from blank_lines(bottom_space)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


if __name__ == "__main__":  # pragma: no cover
    from rich.console import Console, Group
    from rich.highlighter import ReprHighlighter
    from rich.panel import Panel

    highlighter = ReprHighlighter()
    console = Console()

    panel = Panel(
        Group(
            Align.left(highlighter("align='left'")),
            Align.center(highlighter("align='center'")),
            Align.right(highlighter("align='right'")),
        ),
        width=60,
        style="on dark_blue",
        title="Align",
    )

    console.print(
        Align.center(panel, vertical="middle", style="on red", height=console.height)
    )

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\statisticsPen.py ===
"""Pen calculating area, center of mass, variance and standard-deviation,
covariance and correlation, and slant, of glyph shapes."""

from math import sqrt, degrees, atan
from fontTools.pens.basePen import BasePen, OpenContourError
from fontTools.pens.momentsPen import MomentsPen

__all__ = ["StatisticsPen", "StatisticsControlPen"]


class StatisticsBase:
    def __init__(self):
        self._zero()

    def _zero(self):
        self.area = 0
        self.meanX = 0
        self.meanY = 0
        self.varianceX = 0
        self.varianceY = 0
        self.stddevX = 0
        self.stddevY = 0
        self.covariance = 0
        self.correlation = 0
        self.slant = 0

    def _update(self):
        # XXX The variance formulas should never produce a negative value,
        # but due to reasons I don't understand, both of our pens do.
        # So we take the absolute value here.
        self.varianceX = abs(self.varianceX)
        self.varianceY = abs(self.varianceY)

        self.stddevX = stddevX = sqrt(self.varianceX)
        self.stddevY = stddevY = sqrt(self.varianceY)

        # Correlation(X,Y) = Covariance(X,Y) / ( stddev(X) * stddev(Y) )
        # https://en.wikipedia.org/wiki/Pearson_product-moment_correlation_coefficient
        if stddevX * stddevY == 0:
            correlation = float("NaN")
        else:
            # XXX The above formula should never produce a value outside
            # the range [-1, 1], but due to reasons I don't understand,
            # (probably the same issue as above), it does. So we clamp.
            correlation = self.covariance / (stddevX * stddevY)
            correlation = max(-1, min(1, correlation))
        self.correlation = correlation if abs(correlation) > 1e-3 else 0

        slant = (
            self.covariance / self.varianceY if self.varianceY != 0 else float("NaN")
        )
        self.slant = slant if abs(slant) > 1e-3 else 0


class StatisticsPen(StatisticsBase, MomentsPen):
    """Pen calculating area, center of mass, variance and
    standard-deviation, covariance and correlation, and slant,
    of glyph shapes.

    Note that if the glyph shape is self-intersecting, the values
    are not correct (but well-defined). Moreover, area will be
    negative if contour directions are clockwise."""

    def __init__(self, glyphset=None):
        MomentsPen.__init__(self, glyphset=glyphset)
        StatisticsBase.__init__(self)

    def _closePath(self):
        MomentsPen._closePath(self)
        self._update()

    def _update(self):
        area = self.area
        if not area:
            self._zero()
            return

        # Center of mass
        # https://en.wikipedia.org/wiki/Center_of_mass#A_continuous_volume
        self.meanX = meanX = self.momentX / area
        self.meanY = meanY = self.momentY / area

        # Var(X) = E[X^2] - E[X]^2
        self.varianceX = self.momentXX / area - meanX * meanX
        self.varianceY = self.momentYY / area - meanY * meanY

        # Covariance(X,Y) = (E[X.Y] - E[X]E[Y])
        self.covariance = self.momentXY / area - meanX * meanY

        StatisticsBase._update(self)


class StatisticsControlPen(StatisticsBase, BasePen):
    """Pen calculating area, center of mass, variance and
    standard-deviation, covariance and correlation, and slant,
    of glyph shapes, using the control polygon only.

    Note that if the glyph shape is self-intersecting, the values
    are not correct (but well-defined). Moreover, area will be
    negative if contour directions are clockwise."""

    def __init__(self, glyphset=None):
        BasePen.__init__(self, glyphset)
        StatisticsBase.__init__(self)
        self._nodes = []

    def _moveTo(self, pt):
        self._nodes.append(complex(*pt))
        self._startPoint = pt

    def _lineTo(self, pt):
        self._nodes.append(complex(*pt))

    def _qCurveToOne(self, pt1, pt2):
        for pt in (pt1, pt2):
            self._nodes.append(complex(*pt))

    def _curveToOne(self, pt1, pt2, pt3):
        for pt in (pt1, pt2, pt3):
            self._nodes.append(complex(*pt))

    def _closePath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            self._lineTo(self._startPoint)
        self._update()

    def _endPath(self):
        p0 = self._getCurrentPoint()
        if p0 != self._startPoint:
            raise OpenContourError("Glyph statistics not defined on open contours.")
        self._update()

    def _update(self):
        nodes = self._nodes
        n = len(nodes)

        # Triangle formula
        self.area = (
            sum(
                (p0.real * p1.imag - p1.real * p0.imag)
                for p0, p1 in zip(nodes, nodes[1:] + nodes[:1])
            )
            / 2
        )

        # Center of mass
        # https://en.wikipedia.org/wiki/Center_of_mass#A_system_of_particles
        sumNodes = sum(nodes)
        self.meanX = meanX = sumNodes.real / n
        self.meanY = meanY = sumNodes.imag / n

        if n > 1:
            # Var(X) = (sum[X^2] - sum[X]^2 / n) / (n - 1)
            # https://www.statisticshowto.com/probability-and-statistics/descriptive-statistics/sample-variance/
            self.varianceX = varianceX = (
                sum(p.real * p.real for p in nodes)
                - (sumNodes.real * sumNodes.real) / n
            ) / (n - 1)
            self.varianceY = varianceY = (
                sum(p.imag * p.imag for p in nodes)
                - (sumNodes.imag * sumNodes.imag) / n
            ) / (n - 1)

            # Covariance(X,Y) = (sum[X.Y] - sum[X].sum[Y] / n) / (n - 1)
            self.covariance = covariance = (
                sum(p.real * p.imag for p in nodes)
                - (sumNodes.real * sumNodes.imag) / n
            ) / (n - 1)
        else:
            self.varianceX = varianceX = 0
            self.varianceY = varianceY = 0
            self.covariance = covariance = 0

        StatisticsBase._update(self)


def _test(glyphset, upem, glyphs, quiet=False, *, control=False):
    from fontTools.pens.transformPen import TransformPen
    from fontTools.misc.transform import Scale

    wght_sum = 0
    wght_sum_perceptual = 0
    wdth_sum = 0
    slnt_sum = 0
    slnt_sum_perceptual = 0
    for glyph_name in glyphs:
        glyph = glyphset[glyph_name]
        if control:
            pen = StatisticsControlPen(glyphset=glyphset)
        else:
            pen = StatisticsPen(glyphset=glyphset)
        transformer = TransformPen(pen, Scale(1.0 / upem))
        glyph.draw(transformer)

        area = abs(pen.area)
        width = glyph.width
        wght_sum += area
        wght_sum_perceptual += pen.area * width
        wdth_sum += width
        slnt_sum += pen.slant
        slnt_sum_perceptual += pen.slant * width

        if quiet:
            continue

        print()
        print("glyph:", glyph_name)

        for item in [
            "area",
            "momentX",
            "momentY",
            "momentXX",
            "momentYY",
            "momentXY",
            "meanX",
            "meanY",
            "varianceX",
            "varianceY",
            "stddevX",
            "stddevY",
            "covariance",
            "correlation",
            "slant",
        ]:
            print("%s: %g" % (item, getattr(pen, item)))

    if not quiet:
        print()
        print("font:")

    print("weight: %g" % (wght_sum * upem / wdth_sum))
    print("weight (perceptual): %g" % (wght_sum_perceptual / wdth_sum))
    print("width:  %g" % (wdth_sum / upem / len(glyphs)))
    slant = slnt_sum / len(glyphs)
    print("slant:  %g" % slant)
    print("slant angle:  %g" % -degrees(atan(slant)))
    slant_perceptual = slnt_sum_perceptual / wdth_sum
    print("slant (perceptual):  %g" % slant_perceptual)
    print("slant (perceptual) angle:  %g" % -degrees(atan(slant_perceptual)))


def main(args):
    """Report font glyph shape geometricsl statistics"""

    if args is None:
        import sys

        args = sys.argv[1:]

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools pens.statisticsPen",
        description="Report font glyph shape geometricsl statistics",
    )
    parser.add_argument("font", metavar="font.ttf", help="Font file.")
    parser.add_argument("glyphs", metavar="glyph-name", help="Glyph names.", nargs="*")
    parser.add_argument(
        "-y",
        metavar="<number>",
        help="Face index into a collection to open. Zero based.",
    )
    parser.add_argument(
        "-c",
        "--control",
        action="store_true",
        help="Use the control-box pen instead of the Green therem.",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Only report font-wide statistics."
    )
    parser.add_argument(
        "--variations",
        metavar="AXIS=LOC",
        default="",
        help="List of space separated locations. A location consist in "
        "the name of a variation axis, followed by '=' and a number. E.g.: "
        "wght=700 wdth=80. The default is the location of the base master.",
    )

    options = parser.parse_args(args)

    glyphs = options.glyphs
    fontNumber = int(options.y) if options.y is not None else 0

    location = {}
    for tag_v in options.variations.split():
        fields = tag_v.split("=")
        tag = fields[0].strip()
        v = int(fields[1])
        location[tag] = v

    from fontTools.ttLib import TTFont

    font = TTFont(options.font, fontNumber=fontNumber)
    if not glyphs:
        glyphs = font.getGlyphOrder()
    _test(
        font.getGlyphSet(location=location),
        font["head"].unitsPerEm,
        glyphs,
        quiet=options.quiet,
        control=options.control,
    )


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\memory.py ===
from __future__ import annotations

import logging
from datetime import datetime, timezone
from errno import ENOTEMPTY
from io import BytesIO
from pathlib import PurePath, PureWindowsPath
from typing import Any, ClassVar

from fsspec import AbstractFileSystem
from fsspec.implementations.local import LocalFileSystem
from fsspec.utils import stringify_path

logger = logging.getLogger("fsspec.memoryfs")


class MemoryFileSystem(AbstractFileSystem):
    """A filesystem based on a dict of BytesIO objects

    This is a global filesystem so instances of this class all point to the same
    in memory filesystem.
    """

    store: ClassVar[dict[str, Any]] = {}  # global, do not overwrite!
    pseudo_dirs = [""]  # global, do not overwrite!
    protocol = "memory"
    root_marker = "/"

    @classmethod
    def _strip_protocol(cls, path):
        if isinstance(path, PurePath):
            if isinstance(path, PureWindowsPath):
                return LocalFileSystem._strip_protocol(path)
            else:
                path = stringify_path(path)

        if path.startswith("memory://"):
            path = path[len("memory://") :]
        if "::" in path or "://" in path:
            return path.rstrip("/")
        path = path.lstrip("/").rstrip("/")
        return "/" + path if path else ""

    def ls(self, path, detail=True, **kwargs):
        path = self._strip_protocol(path)
        if path in self.store:
            # there is a key with this exact name
            if not detail:
                return [path]
            return [
                {
                    "name": path,
                    "size": self.store[path].size,
                    "type": "file",
                    "created": self.store[path].created.timestamp(),
                }
            ]
        paths = set()
        starter = path + "/"
        out = []
        for p2 in tuple(self.store):
            if p2.startswith(starter):
                if "/" not in p2[len(starter) :]:
                    # exact child
                    out.append(
                        {
                            "name": p2,
                            "size": self.store[p2].size,
                            "type": "file",
                            "created": self.store[p2].created.timestamp(),
                        }
                    )
                elif len(p2) > len(starter):
                    # implied child directory
                    ppath = starter + p2[len(starter) :].split("/", 1)[0]
                    if ppath not in paths:
                        out = out or []
                        out.append(
                            {
                                "name": ppath,
                                "size": 0,
                                "type": "directory",
                            }
                        )
                        paths.add(ppath)
        for p2 in self.pseudo_dirs:
            if p2.startswith(starter):
                if "/" not in p2[len(starter) :]:
                    # exact child pdir
                    if p2 not in paths:
                        out.append({"name": p2, "size": 0, "type": "directory"})
                        paths.add(p2)
                else:
                    # directory implied by deeper pdir
                    ppath = starter + p2[len(starter) :].split("/", 1)[0]
                    if ppath not in paths:
                        out.append({"name": ppath, "size": 0, "type": "directory"})
                        paths.add(ppath)
        if not out:
            if path in self.pseudo_dirs:
                # empty dir
                return []
            raise FileNotFoundError(path)
        if detail:
            return out
        return sorted([f["name"] for f in out])

    def mkdir(self, path, create_parents=True, **kwargs):
        path = self._strip_protocol(path)
        if path in self.store or path in self.pseudo_dirs:
            raise FileExistsError(path)
        if self._parent(path).strip("/") and self.isfile(self._parent(path)):
            raise NotADirectoryError(self._parent(path))
        if create_parents and self._parent(path).strip("/"):
            try:
                self.mkdir(self._parent(path), create_parents, **kwargs)
            except FileExistsError:
                pass
        if path and path not in self.pseudo_dirs:
            self.pseudo_dirs.append(path)

    def makedirs(self, path, exist_ok=False):
        try:
            self.mkdir(path, create_parents=True)
        except FileExistsError:
            if not exist_ok:
                raise

    def pipe_file(self, path, value, mode="overwrite", **kwargs):
        """Set the bytes of given file

        Avoids copies of the data if possible
        """
        mode = "xb" if mode == "create" else "wb"
        self.open(path, mode=mode, data=value)

    def rmdir(self, path):
        path = self._strip_protocol(path)
        if path == "":
            # silently avoid deleting FS root
            return
        if path in self.pseudo_dirs:
            if not self.ls(path):
                self.pseudo_dirs.remove(path)
            else:
                raise OSError(ENOTEMPTY, "Directory not empty", path)
        else:
            raise FileNotFoundError(path)

    def info(self, path, **kwargs):
        logger.debug("info: %s", path)
        path = self._strip_protocol(path)
        if path in self.pseudo_dirs or any(
            p.startswith(path + "/") for p in list(self.store) + self.pseudo_dirs
        ):
            return {
                "name": path,
                "size": 0,
                "type": "directory",
            }
        elif path in self.store:
            filelike = self.store[path]
            return {
                "name": path,
                "size": filelike.size,
                "type": "file",
                "created": getattr(filelike, "created", None),
            }
        else:
            raise FileNotFoundError(path)

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        autocommit=True,
        cache_options=None,
        **kwargs,
    ):
        path = self._strip_protocol(path)
        if "x" in mode and self.exists(path):
            raise FileExistsError
        if path in self.pseudo_dirs:
            raise IsADirectoryError(path)
        parent = path
        while len(parent) > 1:
            parent = self._parent(parent)
            if self.isfile(parent):
                raise FileExistsError(parent)
        if mode in ["rb", "ab", "r+b"]:
            if path in self.store:
                f = self.store[path]
                if mode == "ab":
                    # position at the end of file
                    f.seek(0, 2)
                else:
                    # position at the beginning of file
                    f.seek(0)
                return f
            else:
                raise FileNotFoundError(path)
        elif mode in {"wb", "xb"}:
            if mode == "xb" and self.exists(path):
                raise FileExistsError
            m = MemoryFile(self, path, kwargs.get("data"))
            if not self._intrans:
                m.commit()
            return m
        else:
            name = self.__class__.__name__
            raise ValueError(f"unsupported file mode for {name}: {mode!r}")

    def cp_file(self, path1, path2, **kwargs):
        path1 = self._strip_protocol(path1)
        path2 = self._strip_protocol(path2)
        if self.isfile(path1):
            self.store[path2] = MemoryFile(
                self, path2, self.store[path1].getvalue()
            )  # implicit copy
        elif self.isdir(path1):
            if path2 not in self.pseudo_dirs:
                self.pseudo_dirs.append(path2)
        else:
            raise FileNotFoundError(path1)

    def cat_file(self, path, start=None, end=None, **kwargs):
        logger.debug("cat: %s", path)
        path = self._strip_protocol(path)
        try:
            return bytes(self.store[path].getbuffer()[start:end])
        except KeyError as e:
            raise FileNotFoundError(path) from e

    def _rm(self, path):
        path = self._strip_protocol(path)
        try:
            del self.store[path]
        except KeyError as e:
            raise FileNotFoundError(path) from e

    def modified(self, path):
        path = self._strip_protocol(path)
        try:
            return self.store[path].modified
        except KeyError as e:
            raise FileNotFoundError(path) from e

    def created(self, path):
        path = self._strip_protocol(path)
        try:
            return self.store[path].created
        except KeyError as e:
            raise FileNotFoundError(path) from e

    def isfile(self, path):
        path = self._strip_protocol(path)
        return path in self.store

    def rm(self, path, recursive=False, maxdepth=None):
        if isinstance(path, str):
            path = self._strip_protocol(path)
        else:
            path = [self._strip_protocol(p) for p in path]
        paths = self.expand_path(path, recursive=recursive, maxdepth=maxdepth)
        for p in reversed(paths):
            if self.isfile(p):
                self.rm_file(p)
            # If the expanded path doesn't exist, it is only because the expanded
            # path was a directory that does not exist in self.pseudo_dirs. This
            # is possible if you directly create files without making the
            # directories first.
            elif not self.exists(p):
                continue
            else:
                self.rmdir(p)


class MemoryFile(BytesIO):
    """A BytesIO which can't close and works as a context manager

    Can initialise with data. Each path should only be active once at any moment.

    No need to provide fs, path if auto-committing (default)
    """

    def __init__(self, fs=None, path=None, data=None):
        logger.debug("open file %s", path)
        self.fs = fs
        self.path = path
        self.created = datetime.now(tz=timezone.utc)
        self.modified = datetime.now(tz=timezone.utc)
        if data:
            super().__init__(data)
            self.seek(0)

    @property
    def size(self):
        return self.getbuffer().nbytes

    def __enter__(self):
        return self

    def close(self):
        pass

    def discard(self):
        pass

    def commit(self):
        self.fs.store[self.path] = self
        self.modified = datetime.now(tz=timezone.utc)

# === NexusCore/openenv\Lib\site-packages\google\generativeai\embedding.py ===
# -*- coding: utf-8 -*-
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
from __future__ import annotations

import itertools
from typing import Any, Iterable, overload, TypeVar, Union, Mapping

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.generativeai.client import get_default_generative_client
from google.generativeai.client import get_default_generative_async_client

from google.generativeai.types import helper_types
from google.generativeai.types import text_types
from google.generativeai.types import model_types
from google.generativeai.types import content_types

DEFAULT_EMB_MODEL = "models/embedding-001"
EMBEDDING_MAX_BATCH_SIZE = 100

EmbeddingTaskType = protos.TaskType

EmbeddingTaskTypeOptions = Union[int, str, EmbeddingTaskType]

_EMBEDDING_TASK_TYPE: dict[EmbeddingTaskTypeOptions, EmbeddingTaskType] = {
    EmbeddingTaskType.TASK_TYPE_UNSPECIFIED: EmbeddingTaskType.TASK_TYPE_UNSPECIFIED,
    0: EmbeddingTaskType.TASK_TYPE_UNSPECIFIED,
    "task_type_unspecified": EmbeddingTaskType.TASK_TYPE_UNSPECIFIED,
    "unspecified": EmbeddingTaskType.TASK_TYPE_UNSPECIFIED,
    EmbeddingTaskType.RETRIEVAL_QUERY: EmbeddingTaskType.RETRIEVAL_QUERY,
    1: EmbeddingTaskType.RETRIEVAL_QUERY,
    "retrieval_query": EmbeddingTaskType.RETRIEVAL_QUERY,
    "query": EmbeddingTaskType.RETRIEVAL_QUERY,
    EmbeddingTaskType.RETRIEVAL_DOCUMENT: EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    2: EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    "retrieval_document": EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    "document": EmbeddingTaskType.RETRIEVAL_DOCUMENT,
    EmbeddingTaskType.SEMANTIC_SIMILARITY: EmbeddingTaskType.SEMANTIC_SIMILARITY,
    3: EmbeddingTaskType.SEMANTIC_SIMILARITY,
    "semantic_similarity": EmbeddingTaskType.SEMANTIC_SIMILARITY,
    "similarity": EmbeddingTaskType.SEMANTIC_SIMILARITY,
    EmbeddingTaskType.CLASSIFICATION: EmbeddingTaskType.CLASSIFICATION,
    4: EmbeddingTaskType.CLASSIFICATION,
    "classification": EmbeddingTaskType.CLASSIFICATION,
    EmbeddingTaskType.CLUSTERING: EmbeddingTaskType.CLUSTERING,
    5: EmbeddingTaskType.CLUSTERING,
    "clustering": EmbeddingTaskType.CLUSTERING,
    6: EmbeddingTaskType.QUESTION_ANSWERING,
    "question_answering": EmbeddingTaskType.QUESTION_ANSWERING,
    "qa": EmbeddingTaskType.QUESTION_ANSWERING,
    EmbeddingTaskType.QUESTION_ANSWERING: EmbeddingTaskType.QUESTION_ANSWERING,
    7: EmbeddingTaskType.FACT_VERIFICATION,
    "fact_verification": EmbeddingTaskType.FACT_VERIFICATION,
    "verification": EmbeddingTaskType.FACT_VERIFICATION,
    EmbeddingTaskType.FACT_VERIFICATION: EmbeddingTaskType.FACT_VERIFICATION,
}


def to_task_type(x: EmbeddingTaskTypeOptions) -> EmbeddingTaskType:
    if isinstance(x, str):
        x = x.lower()
    return _EMBEDDING_TASK_TYPE[x]


try:
    # python 3.12+
    _batched = itertools.batched  # type: ignore
except AttributeError:
    T = TypeVar("T")

    def _batched(iterable: Iterable[T], n: int) -> Iterable[list[T]]:
        if n < 1:
            raise ValueError(
                f"Invalid input: The batch size 'n' must be a positive integer. You entered: {n}. Please enter a number greater than 0."
            )
        batch = []
        for item in iterable:
            batch.append(item)
            if len(batch) == n:
                yield batch
                batch = []

        if batch:
            yield batch


@overload
def embed_content(
    model: model_types.BaseModelNameOptions,
    content: content_types.ContentType,
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict: ...


@overload
def embed_content(
    model: model_types.BaseModelNameOptions,
    content: Iterable[content_types.ContentType],
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.BatchEmbeddingDict: ...


def embed_content(
    model: model_types.BaseModelNameOptions,
    content: content_types.ContentType | Iterable[content_types.ContentType],
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict | text_types.BatchEmbeddingDict:
    """Calls the API to create embeddings for content passed in.

    Args:
        model:
            Which [model](https://ai.google.dev/models/gemini#embedding) to
            call, as a string or a `types.Model`.

        content:
            Content to embed.

        task_type:
            Optional task type for which the embeddings will be used. Can only
            be set for `models/embedding-001`.

        title:
            An optional title for the text. Only applicable when task_type is
            `RETRIEVAL_DOCUMENT`.

        output_dimensionality:
            Optional reduced dimensionality for the output embeddings. If set,
            excessive values from the output embeddings will be truncated from
            the end.

        request_options:
            Options for the request.

    Return:
        Dictionary containing the embedding (list of float values) for the
        input content.
    """
    model = model_types.make_model_name(model)

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_generative_client()

    if title and to_task_type(task_type) is not EmbeddingTaskType.RETRIEVAL_DOCUMENT:
        raise ValueError(
            f"Invalid task type: When a title is specified, the task must be of a 'retrieval document' type. Received task type: {task_type} and title: {title}."
        )

    if output_dimensionality and output_dimensionality < 0:
        raise ValueError(
            f"Invalid value: `output_dimensionality` must be a non-negative integer. Received: {output_dimensionality}."
        )

    if task_type:
        task_type = to_task_type(task_type)

    if isinstance(content, Iterable) and not isinstance(content, (str, Mapping)):
        result = {"embedding": []}
        requests = (
            protos.EmbedContentRequest(
                model=model,
                content=content_types.to_content(c),
                task_type=task_type,
                title=title,
                output_dimensionality=output_dimensionality,
            )
            for c in content
        )
        for batch in _batched(requests, EMBEDDING_MAX_BATCH_SIZE):
            embedding_request = protos.BatchEmbedContentsRequest(model=model, requests=batch)
            embedding_response = client.batch_embed_contents(
                embedding_request,
                **request_options,
            )
            embedding_dict = type(embedding_response).to_dict(embedding_response)
            result["embedding"].extend(e["values"] for e in embedding_dict["embeddings"])
        return result
    else:
        embedding_request = protos.EmbedContentRequest(
            model=model,
            content=content_types.to_content(content),
            task_type=task_type,
            title=title,
            output_dimensionality=output_dimensionality,
        )
        embedding_response = client.embed_content(
            embedding_request,
            **request_options,
        )
        embedding_dict = type(embedding_response).to_dict(embedding_response)
        embedding_dict["embedding"] = embedding_dict["embedding"]["values"]
        return embedding_dict


@overload
async def embed_content_async(
    model: model_types.BaseModelNameOptions,
    content: content_types.ContentType,
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict: ...


@overload
async def embed_content_async(
    model: model_types.BaseModelNameOptions,
    content: Iterable[content_types.ContentType],
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.BatchEmbeddingDict: ...


async def embed_content_async(
    model: model_types.BaseModelNameOptions,
    content: content_types.ContentType | Iterable[content_types.ContentType],
    task_type: EmbeddingTaskTypeOptions | None = None,
    title: str | None = None,
    output_dimensionality: int | None = None,
    client: glm.GenerativeServiceAsyncClient = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> text_types.EmbeddingDict | text_types.BatchEmbeddingDict:
    """Calls the API to create async embeddings for content passed in."""

    model = model_types.make_model_name(model)

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_generative_async_client()

    if title and to_task_type(task_type) is not EmbeddingTaskType.RETRIEVAL_DOCUMENT:
        raise ValueError(
            f"Invalid task type: When a title is specified, the task must be of a 'retrieval document' type. Received task type: {task_type} and title: {title}."
        )
    if output_dimensionality and output_dimensionality < 0:
        raise ValueError(
            f"Invalid value: `output_dimensionality` must be a non-negative integer. Received: {output_dimensionality}."
        )

    if task_type:
        task_type = to_task_type(task_type)

    if isinstance(content, Iterable) and not isinstance(content, (str, Mapping)):
        result = {"embedding": []}
        requests = (
            protos.EmbedContentRequest(
                model=model,
                content=content_types.to_content(c),
                task_type=task_type,
                title=title,
                output_dimensionality=output_dimensionality,
            )
            for c in content
        )
        for batch in _batched(requests, EMBEDDING_MAX_BATCH_SIZE):
            embedding_request = protos.BatchEmbedContentsRequest(model=model, requests=batch)
            embedding_response = await client.batch_embed_contents(
                embedding_request,
                **request_options,
            )
            embedding_dict = type(embedding_response).to_dict(embedding_response)
            result["embedding"].extend(e["values"] for e in embedding_dict["embeddings"])
        return result
    else:
        embedding_request = protos.EmbedContentRequest(
            model=model,
            content=content_types.to_content(content),
            task_type=task_type,
            title=title,
            output_dimensionality=output_dimensionality,
        )
        embedding_response = await client.embed_content(
            embedding_request,
            **request_options,
        )
        embedding_dict = type(embedding_response).to_dict(embedding_response)
        embedding_dict["embedding"] = embedding_dict["embedding"]["values"]
        return embedding_dict

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\tools\edit.py ===
from collections import defaultdict
from pathlib import Path
from typing import Literal, get_args

from anthropic.types.beta import BetaToolTextEditor20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .run import maybe_truncate, run

Command = Literal[
    "view",
    "create",
    "str_replace",
    "insert",
    "undo_edit",
]
SNIPPET_LINES: int = 4


class EditTool(BaseAnthropicTool):
    """
    An filesystem editor tool that allows the agent to view, create, and edit files.
    The tool parameters are defined by Anthropic and are not editable.
    """

    api_type: Literal["text_editor_20241022"] = "text_editor_20241022"
    name: Literal["str_replace_editor"] = "str_replace_editor"

    _file_history: dict[Path, list[str]]

    def __init__(self):
        self._file_history = defaultdict(list)
        super().__init__()

    def to_params(self) -> BetaToolTextEditor20241022Param:
        return {
            "name": self.name,
            "type": self.api_type,
        }

    async def __call__(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ):
        # Ask for user permission before executing the command
        print(f"Do you want to execute the following command?")
        print(f"Command: {command}")
        print(f"Path: {path}")
        if file_text:
            print(f"File text: {file_text}")
        if view_range:
            print(f"View range: {view_range}")
        if old_str:
            print(f"Old string: {old_str}")
        if new_str:
            print(f"New string: {new_str}")
        if insert_line is not None:
            print(f"Insert line: {insert_line}")

        user_input = input("Enter 'yes' to proceed, anything else to cancel: ")

        if user_input.lower() != "yes":
            return ToolResult(
                system="Command execution cancelled by user",
                error="User did not provide permission to execute the command.",
            )
        _path = Path(path)
        self.validate_path(command, _path)
        if command == "view":
            return await self.view(_path, view_range)
        elif command == "create":
            if not file_text:
                raise ToolError("Parameter `file_text` is required for command: create")
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)
            return ToolResult(output=f"File created successfully at: {_path}")
        elif command == "str_replace":
            if not old_str:
                raise ToolError(
                    "Parameter `old_str` is required for command: str_replace"
                )
            return self.str_replace(_path, old_str, new_str)
        elif command == "insert":
            if insert_line is None:
                raise ToolError(
                    "Parameter `insert_line` is required for command: insert"
                )
            if not new_str:
                raise ToolError("Parameter `new_str` is required for command: insert")
            return self.insert(_path, insert_line, new_str)
        elif command == "undo_edit":
            return self.undo_edit(_path)
        raise ToolError(
            f'Unrecognized command {command}. The allowed commands for the {self.name} tool are: {", ".join(get_args(Command))}'
        )

    def validate_path(self, command: str, path: Path):
        """
        Check that the path/command combination is valid.
        """
        # Check if its an absolute path
        if not path.is_absolute():
            suggested_path = Path("") / path
            raise ToolError(
                f"The path {path} is not an absolute path, it should start with `/`. Maybe you meant {suggested_path}?"
            )
        # Check if path exists
        if not path.exists() and command != "create":
            raise ToolError(
                f"The path {path} does not exist. Please provide a valid path."
            )
        if path.exists() and command == "create":
            raise ToolError(
                f"File already exists at: {path}. Cannot overwrite files using command `create`."
            )
        # Check if the path points to a directory
        if path.is_dir():
            if command != "view":
                raise ToolError(
                    f"The path {path} is a directory and only the `view` command can be used on directories"
                )

    async def view(self, path: Path, view_range: list[int] | None = None):
        """Implement the view command"""
        if path.is_dir():
            if view_range:
                raise ToolError(
                    "The `view_range` parameter is not allowed when `path` points to a directory."
                )

            _, stdout, stderr = await run(
                rf"find {path} -maxdepth 2 -not -path '*/\.*'"
            )
            if not stderr:
                stdout = f"Here's the files and directories up to 2 levels deep in {path}, excluding hidden items:\n{stdout}\n"
            return CLIResult(output=stdout, error=stderr)

        file_content = self.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "Invalid `view_range`. It should be a list of two integers."
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. It's first element `{init_line}` should be within the range of lines of the file: {[1, n_lines_file]}"
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. It's second element `{final_line}` should be smaller than the number of lines in the file: `{n_lines_file}`"
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"Invalid `view_range`: {view_range}. It's second element `{final_line}` should be larger or equal than its first `{init_line}`"
                )

            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        return CLIResult(
            output=self._make_output(file_content, str(path), init_line=init_line)
        )

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """Implement the str_replace command, which replaces old_str with new_str in the file content"""
        # Read the file content
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""

        # Check if old_str is unique in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f"No replacement was performed, old_str `{old_str}` did not appear verbatim in {path}."
            )
        elif occurrences > 1:
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"No replacement was performed. Multiple occurrences of old_str `{old_str}` in lines {lines}. Please ensure it is unique"
            )

        # Replace old_str with new_str
        new_file_content = file_content.replace(old_str, new_str)

        # Write the new content to the file
        self.write_file(path, new_file_content)

        # Save the content to history
        self._file_history[path].append(file_content)

        # Create a snippet of the edited section
        replacement_line = file_content.split(old_str)[0].count("\n")
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
        snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])

        # Prepare the success message
        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet, f"a snippet of {path}", start_line + 1
        )
        success_msg += "Review the changes and make sure they are as expected. Edit the file again if necessary."

        return CLIResult(output=success_msg)

    def insert(self, path: Path, insert_line: int, new_str: str):
        """Implement the insert command, which inserts new_str at the specified line in the file content."""
        file_text = self.read_file(path).expandtabs()
        new_str = new_str.expandtabs()
        file_text_lines = file_text.split("\n")
        n_lines_file = len(file_text_lines)

        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f"Invalid `insert_line` parameter: {insert_line}. It should be within the range of lines of the file: {[0, n_lines_file]}"
            )

        new_str_lines = new_str.split("\n")
        new_file_text_lines = (
            file_text_lines[:insert_line]
            + new_str_lines
            + file_text_lines[insert_line:]
        )
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + new_str_lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]
        )

        new_file_text = "\n".join(new_file_text_lines)
        snippet = "\n".join(snippet_lines)

        self.write_file(path, new_file_text)
        self._file_history[path].append(file_text)

        success_msg = f"The file {path} has been edited. "
        success_msg += self._make_output(
            snippet,
            "a snippet of the edited file",
            max(1, insert_line - SNIPPET_LINES + 1),
        )
        success_msg += "Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."
        return CLIResult(output=success_msg)

    def undo_edit(self, path: Path):
        """Implement the undo_edit command."""
        if not self._file_history[path]:
            raise ToolError(f"No edit history found for {path}.")

        old_text = self._file_history[path].pop()
        self.write_file(path, old_text)

        return CLIResult(
            output=f"Last edit to {path} undone successfully. {self._make_output(old_text, str(path))}"
        )

    def read_file(self, path: Path):
        """Read the content of a file from a given path; raise a ToolError if an error occurs."""
        try:
            return path.read_text()
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to read {path}") from None

    def write_file(self, path: Path, file: str):
        """Write the content of a file to a given path; raise a ToolError if an error occurs."""
        try:
            path.write_text(file)
        except Exception as e:
            raise ToolError(f"Ran into {e} while trying to write to {path}") from None

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
    ):
        """Generate output for the CLI based on the content of a file."""
        file_content = maybe_truncate(file_content)
        if expand_tabs:
            file_content = file_content.expandtabs()
        file_content = "\n".join(
            [
                f"{i + init_line:6}\t{line}"
                for i, line in enumerate(file_content.split("\n"))
            ]
        )
        return (
            f"Here's the result of running `cat -n` on {file_descriptor}:\n"
            + file_content
            + "\n"
        )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\align.py ===
import sys
from itertools import chain
from typing import TYPE_CHECKING, Iterable, Optional

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from pip._vendor.typing_extensions import Literal  # pragma: no cover

from .constrain import Constrain
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import StyleType

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderableType, RenderResult

AlignMethod = Literal["left", "center", "right"]
VerticalAlignMethod = Literal["top", "middle", "bottom"]


class Align(JupyterMixin):
    """Align a renderable by adding spaces if necessary.

    Args:
        renderable (RenderableType): A console renderable.
        align (AlignMethod): One of "left", "center", or "right""
        style (StyleType, optional): An optional style to apply to the background.
        vertical (Optional[VerticalAlignMethod], optional): Optional vertical align, one of "top", "middle", or "bottom". Defaults to None.
        pad (bool, optional): Pad the right with spaces. Defaults to True.
        width (int, optional): Restrict contents to given width, or None to use default width. Defaults to None.
        height (int, optional): Set height of align renderable, or None to fit to contents. Defaults to None.

    Raises:
        ValueError: if ``align`` is not one of the expected values.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        align: AlignMethod = "left",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        if align not in ("left", "center", "right"):
            raise ValueError(
                f'invalid value for align, expected "left", "center", or "right" (not {align!r})'
            )
        if vertical is not None and vertical not in ("top", "middle", "bottom"):
            raise ValueError(
                f'invalid value for vertical, expected "top", "middle", or "bottom" (not {vertical!r})'
            )
        self.renderable = renderable
        self.align = align
        self.style = style
        self.vertical = vertical
        self.pad = pad
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return f"Align({self.renderable!r}, {self.align!r})"

    @classmethod
    def left(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the left."""
        return cls(
            renderable,
            "left",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def center(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the center."""
        return cls(
            renderable,
            "center",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    @classmethod
    def right(
        cls,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
        *,
        vertical: Optional[VerticalAlignMethod] = None,
        pad: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> "Align":
        """Align a renderable to the right."""
        return cls(
            renderable,
            "right",
            style=style,
            vertical=vertical,
            pad=pad,
            width=width,
            height=height,
        )

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        align = self.align
        width = console.measure(self.renderable, options=options).maximum
        rendered = console.render(
            Constrain(
                self.renderable, width if self.width is None else min(width, self.width)
            ),
            options.update(height=None),
        )
        lines = list(Segment.split_lines(rendered))
        width, height = Segment.get_shape(lines)
        lines = Segment.set_shape(lines, width, height)
        new_line = Segment.line()
        excess_space = options.max_width - width
        style = console.get_style(self.style) if self.style is not None else None

        def generate_segments() -> Iterable[Segment]:
            if excess_space <= 0:
                # Exact fit
                for line in lines:
                    yield from line
                    yield new_line

            elif align == "left":
                # Pad on the right
                pad = Segment(" " * excess_space, style) if self.pad else None
                for line in lines:
                    yield from line
                    if pad:
                        yield pad
                    yield new_line

            elif align == "center":
                # Pad left and right
                left = excess_space // 2
                pad = Segment(" " * left, style)
                pad_right = (
                    Segment(" " * (excess_space - left), style) if self.pad else None
                )
                for line in lines:
                    if left:
                        yield pad
                    yield from line
                    if pad_right:
                        yield pad_right
                    yield new_line

            elif align == "right":
                # Padding on left
                pad = Segment(" " * excess_space, style)
                for line in lines:
                    yield pad
                    yield from line
                    yield new_line

        blank_line = (
            Segment(f"{' ' * (self.width or options.max_width)}\n", style)
            if self.pad
            else Segment("\n")
        )

        def blank_lines(count: int) -> Iterable[Segment]:
            if count > 0:
                for _ in range(count):
                    yield blank_line

        vertical_height = self.height or options.height
        iter_segments: Iterable[Segment]
        if self.vertical and vertical_height is not None:
            if self.vertical == "top":
                bottom_space = vertical_height - height
                iter_segments = chain(generate_segments(), blank_lines(bottom_space))
            elif self.vertical == "middle":
                top_space = (vertical_height - height) // 2
                bottom_space = vertical_height - top_space - height
                iter_segments = chain(
                    blank_lines(top_space),
                    generate_segments(),
                    blank_lines(bottom_space),
                )
            else:  #  self.vertical == "bottom":
                top_space = vertical_height - height
                iter_segments = chain(blank_lines(top_space), generate_segments())
        else:
            iter_segments = generate_segments()
        if self.style:
            style = console.get_style(self.style)
            iter_segments = Segment.apply_style(iter_segments, style)
        yield from iter_segments

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


class VerticalCenter(JupyterMixin):
    """Vertically aligns a renderable.

    Warn:
        This class is deprecated and may be removed in a future version. Use Align class with
        `vertical="middle"`.

    Args:
        renderable (RenderableType): A renderable object.
        style (StyleType, optional): An optional style to apply to the background. Defaults to None.
    """

    def __init__(
        self,
        renderable: "RenderableType",
        style: Optional[StyleType] = None,
    ) -> None:
        self.renderable = renderable
        self.style = style

    def __repr__(self) -> str:
        return f"VerticalCenter({self.renderable!r})"

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        style = console.get_style(self.style) if self.style is not None else None
        lines = console.render_lines(
            self.renderable, options.update(height=None), pad=False
        )
        width, _height = Segment.get_shape(lines)
        new_line = Segment.line()
        height = options.height or options.size.height
        top_space = (height - len(lines)) // 2
        bottom_space = height - top_space - len(lines)
        blank_line = Segment(f"{' ' * width}", style)

        def blank_lines(count: int) -> Iterable[Segment]:
            for _ in range(count):
                yield blank_line
                yield new_line

        if top_space > 0:
            yield from blank_lines(top_space)
        for line in lines:
            yield from line
            yield new_line
        if bottom_space > 0:
            yield from blank_lines(bottom_space)

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> Measurement:
        measurement = Measurement.get(console, options, self.renderable)
        return measurement


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console, Group
    from pip._vendor.rich.highlighter import ReprHighlighter
    from pip._vendor.rich.panel import Panel

    highlighter = ReprHighlighter()
    console = Console()

    panel = Panel(
        Group(
            Align.left(highlighter("align='left'")),
            Align.center(highlighter("align='center'")),
            Align.right(highlighter("align='right'")),
        ),
        width=60,
        style="on dark_blue",
        title="Align",
    )

    console.print(
        Align.center(panel, vertical="middle", style="on red", height=console.height)
    )

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\document.py ===
import codecs
import re
import string

import win32con
import win32ui
from pywin import default_scintilla_encoding
from pywin.mfc import docview

from . import scintillacon

crlf_bytes = b"\r\n"
lf_bytes = b"\n"

# re from pep263 - but we use it both on bytes and strings.
re_encoding_bytes = re.compile(rb"coding[:=]\s*([-\w.]+)")
re_encoding_text = re.compile(r"coding[:=]\s*([-\w.]+)")

ParentScintillaDocument = docview.Document


class CScintillaDocument(ParentScintillaDocument):
    "A SyntEdit document."

    def __init__(self, *args):
        self.bom = None  # the BOM, if any, read from the file.
        # the encoding we detected from the source.  Might have
        # detected via the BOM or an encoding decl.  Note that in
        # the latter case (ie, while self.bom is None), it can't be
        # trusted - the user may have edited the encoding decl between
        # open and save.
        self.source_encoding = None
        ParentScintillaDocument.__init__(self, *args)

    def DeleteContents(self):
        pass

    def OnOpenDocument(self, filename):
        # init data members
        # print("Opening", filename)
        self.SetPathName(filename)  # Must set this early!
        try:
            # load the text as binary we can get smart
            # about detecting any existing EOL conventions.
            f = open(filename, "rb")
            try:
                self._LoadTextFromFile(f)
            finally:
                f.close()
        except OSError:
            rc = win32ui.MessageBox(
                "Could not load the file from %s\n\nDo you want to create a new file?"
                % filename,
                "Pythonwin",
                win32con.MB_YESNO | win32con.MB_ICONWARNING,
            )
            if rc == win32con.IDNO:
                return 0
            assert rc == win32con.IDYES, rc
            try:
                f = open(filename, "wb+")
                try:
                    self._LoadTextFromFile(f)
                finally:
                    f.close()
            except OSError as e:
                rc = win32ui.MessageBox("Cannot create the file %s" % filename)
        return 1

    def SaveFile(self, fileName, encoding=None):
        view = self.GetFirstView()
        ok = view.SaveTextFile(fileName, encoding=encoding)
        if ok:
            view.SCISetSavePoint()
        return ok

    def ApplyFormattingStyles(self):
        self._ApplyOptionalToViews("ApplyFormattingStyles")

    # #####################
    # File related functions
    # Helper to transfer text from the MFC document to the control.
    def _LoadTextFromFile(self, f):
        # detect EOL mode - we don't support \r only - so find the
        # first '\n' and guess based on the char before.
        l = f.readline()
        l2 = f.readline()
        # If line ends with \r\n or has no line ending, use CRLF.
        if l.endswith(crlf_bytes) or not l.endswith(lf_bytes):
            eol_mode = scintillacon.SC_EOL_CRLF
        else:
            eol_mode = scintillacon.SC_EOL_LF

        # Detect the encoding - first look for a BOM, and if not found,
        # look for a pep263 encoding declaration.
        for bom, encoding in (
            (codecs.BOM_UTF8, "utf8"),
            (codecs.BOM_UTF16_LE, "utf_16_le"),
            (codecs.BOM_UTF16_BE, "utf_16_be"),
        ):
            if l.startswith(bom):
                self.bom = bom
                self.source_encoding = encoding
                l = l[len(bom) :]  # remove it.
                break
        else:
            # no bom detected - look for pep263 encoding decl.
            for look in (l, l2):
                # Note we are looking at raw bytes here: so
                # both the re itself uses bytes and the result
                # is bytes - but we need the result as a string.
                match = re_encoding_bytes.search(look)
                if match is not None:
                    self.source_encoding = match.group(1).decode("ascii")
                    break

        # reading by lines would be too slow?  Maybe we can use the
        # incremental encoders? For now just stick with loading the
        # entire file in memory.
        text = l + l2 + f.read()

        # Translate from source encoding to UTF-8 bytes for Scintilla
        source_encoding = self.source_encoding
        # If we don't know an encoding, try utf-8 - if that fails we will
        # fallback to latin-1 to treat it as bytes...
        if source_encoding is None:
            source_encoding = "utf-8"
        # we could optimize this by avoiding utf8 to-ing and from-ing,
        # but then we would lose the ability to handle invalid utf8
        # (and even then, the use of encoding aliases makes this tricky)
        # To create an invalid utf8 file:
        # >>> open(filename, "wb").write(codecs.BOM_UTF8+"bad \xa9har\r\n")
        try:
            dec = text.decode(source_encoding)
        except UnicodeError:
            print(
                "WARNING: Failed to decode bytes from '%s' encoding - treating as latin1"
                % source_encoding
            )
            dec = text.decode("latin1")
        except LookupError:
            print(
                "WARNING: Invalid encoding '%s' specified - treating as latin1"
                % source_encoding
            )
            dec = text.decode("latin1")
        # and put it back as utf8 - this shouldn't fail.
        text = dec.encode(default_scintilla_encoding)

        view = self.GetFirstView()
        if view.IsWindow():
            # Turn off undo collection while loading
            view.SendScintilla(scintillacon.SCI_SETUNDOCOLLECTION, 0, 0)
            # Make sure the control isn't read-only
            view.SetReadOnly(0)
            view.SendScintilla(scintillacon.SCI_CLEARALL)
            view.SendMessage(scintillacon.SCI_ADDTEXT, text)
            view.SendScintilla(scintillacon.SCI_SETUNDOCOLLECTION, 1, 0)
            view.SendScintilla(win32con.EM_EMPTYUNDOBUFFER, 0, 0)
            # set EOL mode
            view.SendScintilla(scintillacon.SCI_SETEOLMODE, eol_mode)

    def _SaveTextToFile(self, view, filename, encoding=None):
        s = view.GetTextRange()  # already decoded from scintilla's encoding
        source_encoding = encoding
        if source_encoding is None:
            if self.bom:
                source_encoding = self.source_encoding
            else:
                # no BOM - look for an encoding.
                bits = re.split(r"[\r\n]+", s, 3)
                for look in bits[:-1]:
                    match = re_encoding_text.search(look)
                    if match is not None:
                        source_encoding = match.group(1)
                        self.source_encoding = source_encoding
                        break

            if source_encoding is None:
                source_encoding = "utf-8"

        ## encode data before opening file so script is not lost if encoding fails
        file_contents = s.encode(source_encoding)
        # Open in binary mode as scintilla itself ensures the
        # line endings are already appropriate
        f = open(filename, "wb")
        try:
            if self.bom:
                f.write(self.bom)
            f.write(file_contents)
        finally:
            f.close()
        self.SetModifiedFlag(0)

    def FinalizeViewCreation(self, view):
        pass

    def HookViewNotifications(self, view):
        parent = view.GetParentFrame()
        parent.HookNotify(
            ViewNotifyDelegate(self, "OnBraceMatch"), scintillacon.SCN_UPDATEUI
        )
        parent.HookNotify(
            ViewNotifyDelegate(self, "OnMarginClick"), scintillacon.SCN_MARGINCLICK
        )
        parent.HookNotify(
            ViewNotifyDelegate(self, "OnNeedShown"), scintillacon.SCN_NEEDSHOWN
        )

        parent.HookNotify(
            DocumentNotifyDelegate(self, "OnSavePointReached"),
            scintillacon.SCN_SAVEPOINTREACHED,
        )
        parent.HookNotify(
            DocumentNotifyDelegate(self, "OnSavePointLeft"),
            scintillacon.SCN_SAVEPOINTLEFT,
        )
        parent.HookNotify(
            DocumentNotifyDelegate(self, "OnModifyAttemptRO"),
            scintillacon.SCN_MODIFYATTEMPTRO,
        )
        # Tell scintilla what characters should abort auto-complete.
        view.SCIAutoCStops(string.whitespace + "()[]:;+-/*=\\?'!#@$%^&,<>\"'|")

        if view != self.GetFirstView():
            view.SCISetDocPointer(self.GetFirstView().SCIGetDocPointer())

    def OnSavePointReached(self, std, extra):
        self.SetModifiedFlag(0)

    def OnSavePointLeft(self, std, extra):
        self.SetModifiedFlag(1)

    def OnModifyAttemptRO(self, std, extra):
        self.MakeDocumentWritable()

    # All Marker functions are 1 based.
    def MarkerAdd(self, lineNo, marker):
        self.GetEditorView().SCIMarkerAdd(lineNo - 1, marker)

    def MarkerCheck(self, lineNo, marker):
        v = self.GetEditorView()
        lineNo -= 1  # Make 0 based
        markerState = v.SCIMarkerGet(lineNo)
        return markerState & (1 << marker) != 0

    def MarkerToggle(self, lineNo, marker):
        v = self.GetEditorView()
        if self.MarkerCheck(lineNo, marker):
            v.SCIMarkerDelete(lineNo - 1, marker)
        else:
            v.SCIMarkerAdd(lineNo - 1, marker)

    def MarkerDelete(self, lineNo, marker):
        self.GetEditorView().SCIMarkerDelete(lineNo - 1, marker)

    def MarkerDeleteAll(self, marker):
        self.GetEditorView().SCIMarkerDeleteAll(marker)

    def MarkerGetNext(self, lineNo, marker):
        return self.GetEditorView().SCIMarkerNext(lineNo - 1, 1 << marker) + 1

    def MarkerAtLine(self, lineNo, marker):
        markerState = self.GetEditorView().SCIMarkerGet(lineNo - 1)
        return markerState & (1 << marker)

    # Helper for reflecting functions to views.
    def _ApplyToViews(self, funcName, *args):
        for view in self.GetAllViews():
            func = getattr(view, funcName)
            func(*args)

    def _ApplyOptionalToViews(self, funcName, *args):
        for view in self.GetAllViews():
            func = getattr(view, funcName, None)
            if func is not None:
                func(*args)

    def GetEditorView(self):
        # Find the first frame with a view,
        # then ask it to give the editor view
        # as it knows which one is "active"
        try:
            frame_gev = self.GetFirstView().GetParentFrame().GetEditorView
        except AttributeError:
            return self.GetFirstView()
        return frame_gev()


# Delegate to the correct view, based on the control that sent it.
class ViewNotifyDelegate:
    def __init__(self, doc, name):
        self.doc = doc
        self.name = name

    def __call__(self, std, extra):
        (hwndFrom, idFrom, code) = std
        for v in self.doc.GetAllViews():
            if v.GetSafeHwnd() == hwndFrom:
                return getattr(v, self.name)(*(std, extra))


# Delegate to the document, but only from a single view (as each view sends it seperately)
class DocumentNotifyDelegate:
    def __init__(self, doc, name):
        self.doc = doc
        self.delegate = getattr(doc, name)

    def __call__(self, std, extra):
        (hwndFrom, idFrom, code) = std
        if hwndFrom == self.doc.GetEditorView().GetSafeHwnd():
            self.delegate(*(std, extra))

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\dom_debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMDebugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


class DOMBreakpointType(enum.Enum):
    '''
    DOM breakpoint type.
    '''
    SUBTREE_MODIFIED = "subtree-modified"
    ATTRIBUTE_MODIFIED = "attribute-modified"
    NODE_REMOVED = "node-removed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CSPViolationType(enum.Enum):
    '''
    CSP Violation type.
    '''
    TRUSTEDTYPE_SINK_VIOLATION = "trustedtype-sink-violation"
    TRUSTEDTYPE_POLICY_VIOLATION = "trustedtype-policy-violation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventListener:
    '''
    Object event listener.
    '''
    #: ``EventListener``'s type.
    type_: str

    #: ``EventListener``'s useCapture.
    use_capture: bool

    #: ``EventListener``'s passive flag.
    passive: bool

    #: ``EventListener``'s once flag.
    once: bool

    #: Script id of the handler code.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: int

    #: Event handler function value.
    handler: typing.Optional[runtime.RemoteObject] = None

    #: Event original handler function value.
    original_handler: typing.Optional[runtime.RemoteObject] = None

    #: Node the listener is added to (if any).
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['useCapture'] = self.use_capture
        json['passive'] = self.passive
        json['once'] = self.once
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.handler is not None:
            json['handler'] = self.handler.to_json()
        if self.original_handler is not None:
            json['originalHandler'] = self.original_handler.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            use_capture=bool(json['useCapture']),
            passive=bool(json['passive']),
            once=bool(json['once']),
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            handler=runtime.RemoteObject.from_json(json['handler']) if 'handler' in json else None,
            original_handler=runtime.RemoteObject.from_json(json['originalHandler']) if 'originalHandler' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
        )


def get_event_listeners(
        object_id: runtime.RemoteObjectId,
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[EventListener]]:
    '''
    Returns event listeners of the given object.

    :param object_id: Identifier of the object to return listeners for.
    :param depth: *(Optional)* The maximum depth at which Node children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false). Reports listeners for all contexts if pierce is enabled.
    :returns: Array of relevant listeners.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.getEventListeners',
        'params': params,
    }
    json = yield cmd_dict
    return [EventListener.from_json(i) for i in json['listeners']]


def remove_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes DOM breakpoint that was set using ``setDOMBreakpoint``.

    :param node_id: Identifier of the node to remove breakpoint from.
    :param type_: Type of the breakpoint to remove.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular DOM event.

    :param event_name: Event name.
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint from XMLHttpRequest.

    :param url: Resource URL substring.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_break_on_csp_violation(
        violation_types: typing.List[CSPViolationType]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular CSP violations.

    **EXPERIMENTAL**

    :param violation_types: CSP Violations to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['violationTypes'] = [i.to_json() for i in violation_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setBreakOnCSPViolation',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular operation with DOM.

    :param node_id: Identifier of the node to set breakpoint on.
    :param type_: Type of the operation to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular DOM event.

    :param event_name: DOM Event name to stop on (any DOM event will do).
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name to stop on. If equal to ```"*"``` or not provided, will stop on any EventTarget.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on XMLHttpRequest.

    :param url: Resource URL substring. All XHRs having this substring in the URL will get stopped upon.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\dom_debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMDebugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


class DOMBreakpointType(enum.Enum):
    '''
    DOM breakpoint type.
    '''
    SUBTREE_MODIFIED = "subtree-modified"
    ATTRIBUTE_MODIFIED = "attribute-modified"
    NODE_REMOVED = "node-removed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CSPViolationType(enum.Enum):
    '''
    CSP Violation type.
    '''
    TRUSTEDTYPE_SINK_VIOLATION = "trustedtype-sink-violation"
    TRUSTEDTYPE_POLICY_VIOLATION = "trustedtype-policy-violation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventListener:
    '''
    Object event listener.
    '''
    #: ``EventListener``'s type.
    type_: str

    #: ``EventListener``'s useCapture.
    use_capture: bool

    #: ``EventListener``'s passive flag.
    passive: bool

    #: ``EventListener``'s once flag.
    once: bool

    #: Script id of the handler code.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: int

    #: Event handler function value.
    handler: typing.Optional[runtime.RemoteObject] = None

    #: Event original handler function value.
    original_handler: typing.Optional[runtime.RemoteObject] = None

    #: Node the listener is added to (if any).
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['useCapture'] = self.use_capture
        json['passive'] = self.passive
        json['once'] = self.once
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.handler is not None:
            json['handler'] = self.handler.to_json()
        if self.original_handler is not None:
            json['originalHandler'] = self.original_handler.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            use_capture=bool(json['useCapture']),
            passive=bool(json['passive']),
            once=bool(json['once']),
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            handler=runtime.RemoteObject.from_json(json['handler']) if 'handler' in json else None,
            original_handler=runtime.RemoteObject.from_json(json['originalHandler']) if 'originalHandler' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
        )


def get_event_listeners(
        object_id: runtime.RemoteObjectId,
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[EventListener]]:
    '''
    Returns event listeners of the given object.

    :param object_id: Identifier of the object to return listeners for.
    :param depth: *(Optional)* The maximum depth at which Node children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false). Reports listeners for all contexts if pierce is enabled.
    :returns: Array of relevant listeners.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.getEventListeners',
        'params': params,
    }
    json = yield cmd_dict
    return [EventListener.from_json(i) for i in json['listeners']]


def remove_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes DOM breakpoint that was set using ``setDOMBreakpoint``.

    :param node_id: Identifier of the node to remove breakpoint from.
    :param type_: Type of the breakpoint to remove.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular DOM event.

    :param event_name: Event name.
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint from XMLHttpRequest.

    :param url: Resource URL substring.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_break_on_csp_violation(
        violation_types: typing.List[CSPViolationType]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular CSP violations.

    **EXPERIMENTAL**

    :param violation_types: CSP Violations to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['violationTypes'] = [i.to_json() for i in violation_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setBreakOnCSPViolation',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular operation with DOM.

    :param node_id: Identifier of the node to set breakpoint on.
    :param type_: Type of the operation to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular DOM event.

    :param event_name: DOM Event name to stop on (any DOM event will do).
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name to stop on. If equal to ```"*"``` or not provided, will stop on any EventTarget.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on XMLHttpRequest.

    :param url: Resource URL substring. All XHRs having this substring in the URL will get stopped upon.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\dom_debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMDebugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


class DOMBreakpointType(enum.Enum):
    '''
    DOM breakpoint type.
    '''
    SUBTREE_MODIFIED = "subtree-modified"
    ATTRIBUTE_MODIFIED = "attribute-modified"
    NODE_REMOVED = "node-removed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class CSPViolationType(enum.Enum):
    '''
    CSP Violation type.
    '''
    TRUSTEDTYPE_SINK_VIOLATION = "trustedtype-sink-violation"
    TRUSTEDTYPE_POLICY_VIOLATION = "trustedtype-policy-violation"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class EventListener:
    '''
    Object event listener.
    '''
    #: ``EventListener``'s type.
    type_: str

    #: ``EventListener``'s useCapture.
    use_capture: bool

    #: ``EventListener``'s passive flag.
    passive: bool

    #: ``EventListener``'s once flag.
    once: bool

    #: Script id of the handler code.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: int

    #: Event handler function value.
    handler: typing.Optional[runtime.RemoteObject] = None

    #: Event original handler function value.
    original_handler: typing.Optional[runtime.RemoteObject] = None

    #: Node the listener is added to (if any).
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['useCapture'] = self.use_capture
        json['passive'] = self.passive
        json['once'] = self.once
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        if self.handler is not None:
            json['handler'] = self.handler.to_json()
        if self.original_handler is not None:
            json['originalHandler'] = self.original_handler.to_json()
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            use_capture=bool(json['useCapture']),
            passive=bool(json['passive']),
            once=bool(json['once']),
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
            handler=runtime.RemoteObject.from_json(json['handler']) if 'handler' in json else None,
            original_handler=runtime.RemoteObject.from_json(json['originalHandler']) if 'originalHandler' in json else None,
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
        )


def get_event_listeners(
        object_id: runtime.RemoteObjectId,
        depth: typing.Optional[int] = None,
        pierce: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[EventListener]]:
    '''
    Returns event listeners of the given object.

    :param object_id: Identifier of the object to return listeners for.
    :param depth: *(Optional)* The maximum depth at which Node children should be retrieved, defaults to 1. Use -1 for the entire subtree or provide an integer larger than 0.
    :param pierce: *(Optional)* Whether or not iframes and shadow roots should be traversed when returning the subtree (default is false). Reports listeners for all contexts if pierce is enabled.
    :returns: Array of relevant listeners.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if depth is not None:
        params['depth'] = depth
    if pierce is not None:
        params['pierce'] = pierce
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.getEventListeners',
        'params': params,
    }
    json = yield cmd_dict
    return [EventListener.from_json(i) for i in json['listeners']]


def remove_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes DOM breakpoint that was set using ``setDOMBreakpoint``.

    :param node_id: Identifier of the node to remove breakpoint from.
    :param type_: Type of the breakpoint to remove.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular DOM event.

    :param event_name: Event name.
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def remove_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes breakpoint from XMLHttpRequest.

    :param url: Resource URL substring.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.removeXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_break_on_csp_violation(
        violation_types: typing.List[CSPViolationType]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular CSP violations.

    **EXPERIMENTAL**

    :param violation_types: CSP Violations to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['violationTypes'] = [i.to_json() for i in violation_types]
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setBreakOnCSPViolation',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_breakpoint(
        node_id: dom.NodeId,
        type_: DOMBreakpointType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular operation with DOM.

    :param node_id: Identifier of the node to set breakpoint on.
    :param type_: Type of the operation to stop upon.
    '''
    params: T_JSON_DICT = dict()
    params['nodeId'] = node_id.to_json()
    params['type'] = type_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setDOMBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_event_listener_breakpoint(
        event_name: str,
        target_name: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular DOM event.

    :param event_name: DOM Event name to stop on (any DOM event will do).
    :param target_name: **(EXPERIMENTAL)** *(Optional)* EventTarget interface name to stop on. If equal to ```"*"``` or not provided, will stop on any EventTarget.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    if target_name is not None:
        params['targetName'] = target_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setEventListenerBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_instrumentation_breakpoint(
        event_name: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on particular native event.

    **EXPERIMENTAL**

    :param event_name: Instrumentation name to stop on.
    '''
    params: T_JSON_DICT = dict()
    params['eventName'] = event_name
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def set_xhr_breakpoint(
        url: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets breakpoint on XMLHttpRequest.

    :param url: Resource URL substring. All XHRs having this substring in the URL will get stopped upon.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMDebugger.setXHRBreakpoint',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\matplotlib_inline\backend_inline.py ===
"""A matplotlib backend for publishing figures via display_data"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the BSD 3-Clause License.

import matplotlib
from matplotlib import colors
from matplotlib.backends import backend_agg
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib._pylab_helpers import Gcf
from matplotlib.figure import Figure

from IPython.core.interactiveshell import InteractiveShell
from IPython.core.getipython import get_ipython
from IPython.core.pylabtools import select_figure_formats
from IPython.display import display

from .config import InlineBackend


def new_figure_manager(num, *args, FigureClass=Figure, **kwargs):
    """
    Return a new figure manager for a new figure instance.

    This function is part of the API expected by Matplotlib backends.
    """
    return new_figure_manager_given_figure(num, FigureClass(*args, **kwargs))


def new_figure_manager_given_figure(num, figure):
    """
    Return a new figure manager for a given figure instance.

    This function is part of the API expected by Matplotlib backends.
    """
    manager = backend_agg.new_figure_manager_given_figure(num, figure)

    # Hack: matplotlib FigureManager objects in interacive backends (at least
    # in some of them) monkeypatch the figure object and add a .show() method
    # to it.  This applies the same monkeypatch in order to support user code
    # that might expect `.show()` to be part of the official API of figure
    # objects.  For further reference:
    # https://github.com/ipython/ipython/issues/1612
    # https://github.com/matplotlib/matplotlib/issues/835

    if not hasattr(figure, 'show'):
        # Queue up `figure` for display
        figure.show = lambda *a: display(
            figure, metadata=_fetch_figure_metadata(figure))

    # If matplotlib was manually set to non-interactive mode, this function
    # should be a no-op (otherwise we'll generate duplicate plots, since a user
    # who set ioff() manually expects to make separate draw/show calls).
    if not matplotlib.is_interactive():
        return manager

    # ensure current figure will be drawn, and each subsequent call
    # of draw_if_interactive() moves the active figure to ensure it is
    # drawn last
    try:
        show._to_draw.remove(figure)
    except ValueError:
        # ensure it only appears in the draw list once
        pass
    # Queue up the figure for drawing in next show() call
    show._to_draw.append(figure)
    show._draw_called = True

    return manager


def show(close=None, block=None):
    """Show all figures as SVG/PNG payloads sent to the IPython clients.

    Parameters
    ----------
    close : bool, optional
        If true, a ``plt.close('all')`` call is automatically issued after
        sending all the figures. If this is set, the figures will entirely
        removed from the internal list of figures.
    block : Not used.
        The `block` parameter is a Matplotlib experimental parameter.
        We accept it in the function signature for compatibility with other
        backends.
    """
    if close is None:
        close = InlineBackend.instance().close_figures
    try:
        for figure_manager in Gcf.get_all_fig_managers():
            display(
                figure_manager.canvas.figure,
                metadata=_fetch_figure_metadata(figure_manager.canvas.figure)
            )
    finally:
        show._to_draw = []
        # only call close('all') if any to close
        # close triggers gc.collect, which can be slow
        if close and Gcf.get_all_fig_managers():
            matplotlib.pyplot.close('all')


# This flag will be reset by draw_if_interactive when called
show._draw_called = False
# list of figures to draw when flush_figures is called
show._to_draw = []


def flush_figures():
    """Send all figures that changed

    This is meant to be called automatically and will call show() if, during
    prior code execution, there had been any calls to draw_if_interactive.

    This function is meant to be used as a post_execute callback in IPython,
    so user-caused errors are handled with showtraceback() instead of being
    allowed to raise.  If this function is not called from within IPython,
    then these exceptions will raise.
    """
    if not show._draw_called:
        return

    try:
        if InlineBackend.instance().close_figures:
            # ignore the tracking, just draw and close all figures
            try:
                return show(True)
            except Exception as e:
                # safely show traceback if in IPython, else raise
                ip = get_ipython()
                if ip is None:
                    raise e
                else:
                    ip.showtraceback()
                    return

        # exclude any figures that were closed:
        active = set([fm.canvas.figure for fm in Gcf.get_all_fig_managers()])
        for fig in [fig for fig in show._to_draw if fig in active]:
            try:
                display(fig, metadata=_fetch_figure_metadata(fig))
            except Exception as e:
                # safely show traceback if in IPython, else raise
                ip = get_ipython()
                if ip is None:
                    raise e
                else:
                    ip.showtraceback()
                    return
    finally:
        # clear flags for next round
        show._to_draw = []
        show._draw_called = False


# Changes to matplotlib in version 1.2 requires a mpl backend to supply a default
# figurecanvas. This is set here to a Agg canvas
# See https://github.com/matplotlib/matplotlib/pull/1125
FigureCanvas = FigureCanvasAgg


def configure_inline_support(shell, backend):
    """Configure an IPython shell object for matplotlib use.

    Parameters
    ----------
    shell : InteractiveShell instance

    backend : matplotlib backend
    """
    # If using our svg payload backend, register the post-execution
    # function that will pick up the results for display.  This can only be
    # done with access to the real shell object.

    cfg = InlineBackend.instance(parent=shell)
    cfg.shell = shell
    if cfg not in shell.configurables:
        shell.configurables.append(cfg)

    if backend in ('inline', 'module://matplotlib_inline.backend_inline'):
        shell.events.register('post_execute', flush_figures)

        # Save rcParams that will be overwrittern
        shell._saved_rcParams = {}
        for k in cfg.rc:
            shell._saved_rcParams[k] = matplotlib.rcParams[k]
        # load inline_rc
        matplotlib.rcParams.update(cfg.rc)
        new_backend_name = "inline"
    else:
        try:
            shell.events.unregister('post_execute', flush_figures)
        except ValueError:
            pass
        if hasattr(shell, '_saved_rcParams'):
            matplotlib.rcParams.update(shell._saved_rcParams)
            del shell._saved_rcParams
        new_backend_name = "other"

    # only enable the formats once -> don't change the enabled formats (which the user may
    # has changed) when getting another "%matplotlib inline" call.
    # See https://github.com/ipython/ipykernel/issues/29
    cur_backend = getattr(configure_inline_support, "current_backend", "unset")
    if new_backend_name != cur_backend:
        # Setup the default figure format
        select_figure_formats(shell, cfg.figure_formats, **cfg.print_figure_kwargs)
        configure_inline_support.current_backend = new_backend_name


def _enable_matplotlib_integration():
    """Enable extra IPython matplotlib integration when we are loaded as the matplotlib backend."""
    from matplotlib import get_backend
    ip = get_ipython()
    backend = get_backend()
    if ip and backend in ('inline', 'module://matplotlib_inline.backend_inline'):
        from IPython.core.pylabtools import activate_matplotlib
        try:
            activate_matplotlib(backend)
            configure_inline_support(ip, backend)
        except (ImportError, AttributeError):
            # bugs may cause a circular import on Python 2
            def configure_once(*args):
                activate_matplotlib(backend)
                configure_inline_support(ip, backend)
                ip.events.unregister('post_run_cell', configure_once)
            ip.events.register('post_run_cell', configure_once)


_enable_matplotlib_integration()


def _fetch_figure_metadata(fig):
    """Get some metadata to help with displaying a figure."""
    # determine if a background is needed for legibility
    if _is_transparent(fig.get_facecolor()):
        # the background is transparent
        ticksLight = _is_light([label.get_color()
                                for axes in fig.axes
                                for axis in (axes.xaxis, axes.yaxis)
                                for label in axis.get_ticklabels()])
        if ticksLight.size and (ticksLight == ticksLight[0]).all():
            # there are one or more tick labels, all with the same lightness
            return {'needs_background': 'dark' if ticksLight[0] else 'light'}

    return None


def _is_light(color):
    """Determines if a color (or each of a sequence of colors) is light (as
    opposed to dark). Based on ITU BT.601 luminance formula (see
    https://stackoverflow.com/a/596241)."""
    rgbaArr = colors.to_rgba_array(color)
    return rgbaArr[:, :3].dot((.299, .587, .114)) > .5


def _is_transparent(color):
    """Determine transparency from alpha."""
    rgba = colors.to_rgba(color)
    return rgba[3] < .5


def set_matplotlib_formats(*formats, **kwargs):
    """Select figure formats for the inline backend. Optionally pass quality for JPEG.

    For example, this enables PNG and JPEG output with a JPEG quality of 90%::

        In [1]: set_matplotlib_formats('png', 'jpeg', quality=90)

    To set this in your config files use the following::

        c.InlineBackend.figure_formats = {'png', 'jpeg'}
        c.InlineBackend.print_figure_kwargs.update({'quality' : 90})

    Parameters
    ----------
    *formats : strs
        One or more figure formats to enable: 'png', 'retina', 'jpeg', 'svg', 'pdf'.
    **kwargs
        Keyword args will be relayed to ``figure.canvas.print_figure``.
    """
    # build kwargs, starting with InlineBackend config
    cfg = InlineBackend.instance()
    kw = {}
    kw.update(cfg.print_figure_kwargs)
    kw.update(**kwargs)
    shell = InteractiveShell.instance()
    select_figure_formats(shell, formats, **kw)


def set_matplotlib_close(close=True):
    """Set whether the inline backend closes all figures automatically or not.

    By default, the inline backend used in the IPython Notebook will close all
    matplotlib figures automatically after each cell is run. This means that
    plots in different cells won't interfere. Sometimes, you may want to make
    a plot in one cell and then refine it in later cells. This can be accomplished
    by::

        In [1]: set_matplotlib_close(False)

    To set this in your config files use the following::

        c.InlineBackend.close_figures = False

    Parameters
    ----------
    close : bool
        Should all matplotlib figures be automatically closed after each cell is
        run?
    """
    cfg = InlineBackend.instance()
    cfg.close_figures = close

# === NexusCore/openenv\Lib\site-packages\PIL\ImageChops.py ===
#
# The Python Imaging Library.
# $Id$
#
# standard channel operations
#
# History:
# 1996-03-24 fl   Created
# 1996-08-13 fl   Added logical operations (for "1" images)
# 2000-10-12 fl   Added offset method (from Image.py)
#
# Copyright (c) 1997-2000 by Secret Labs AB
# Copyright (c) 1996-2000 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#

from __future__ import annotations

from . import Image


def constant(image: Image.Image, value: int) -> Image.Image:
    """Fill a channel with a given gray level.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.new("L", image.size, value)


def duplicate(image: Image.Image) -> Image.Image:
    """Copy a channel. Alias for :py:meth:`PIL.Image.Image.copy`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return image.copy()


def invert(image: Image.Image) -> Image.Image:
    """
    Invert an image (channel). ::

        out = MAX - image

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image.load()
    return image._new(image.im.chop_invert())


def lighter(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Compares the two images, pixel by pixel, and returns a new image containing
    the lighter values. ::

        out = max(image1, image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_lighter(image2.im))


def darker(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Compares the two images, pixel by pixel, and returns a new image containing
    the darker values. ::

        out = min(image1, image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_darker(image2.im))


def difference(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Returns the absolute value of the pixel-by-pixel difference between the two
    images. ::

        out = abs(image1 - image2)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_difference(image2.im))


def multiply(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Superimposes two images on top of each other.

    If you multiply an image with a solid black image, the result is black. If
    you multiply with a solid white image, the image is unaffected. ::

        out = image1 * image2 / MAX

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_multiply(image2.im))


def screen(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Superimposes two inverted images on top of each other. ::

        out = MAX - ((MAX - image1) * (MAX - image2) / MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_screen(image2.im))


def soft_light(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Superimposes two images on top of each other using the Soft Light algorithm

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_soft_light(image2.im))


def hard_light(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Superimposes two images on top of each other using the Hard Light algorithm

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_hard_light(image2.im))


def overlay(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """
    Superimposes two images on top of each other using the Overlay algorithm

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_overlay(image2.im))


def add(
    image1: Image.Image, image2: Image.Image, scale: float = 1.0, offset: float = 0
) -> Image.Image:
    """
    Adds two images, dividing the result by scale and adding the
    offset. If omitted, scale defaults to 1.0, and offset to 0.0. ::

        out = ((image1 + image2) / scale + offset)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_add(image2.im, scale, offset))


def subtract(
    image1: Image.Image, image2: Image.Image, scale: float = 1.0, offset: float = 0
) -> Image.Image:
    """
    Subtracts two images, dividing the result by scale and adding the offset.
    If omitted, scale defaults to 1.0, and offset to 0.0. ::

        out = ((image1 - image2) / scale + offset)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_subtract(image2.im, scale, offset))


def add_modulo(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """Add two images, without clipping the result. ::

        out = ((image1 + image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_add_modulo(image2.im))


def subtract_modulo(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """Subtract two images, without clipping the result. ::

        out = ((image1 - image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_subtract_modulo(image2.im))


def logical_and(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """Logical AND between two images.

    Both of the images must have mode "1". If you would like to perform a
    logical AND on an image with a mode other than "1", try
    :py:meth:`~PIL.ImageChops.multiply` instead, using a black-and-white mask
    as the second image. ::

        out = ((image1 and image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_and(image2.im))


def logical_or(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """Logical OR between two images.

    Both of the images must have mode "1". ::

        out = ((image1 or image2) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_or(image2.im))


def logical_xor(image1: Image.Image, image2: Image.Image) -> Image.Image:
    """Logical XOR between two images.

    Both of the images must have mode "1". ::

        out = ((bool(image1) != bool(image2)) % MAX)

    :rtype: :py:class:`~PIL.Image.Image`
    """

    image1.load()
    image2.load()
    return image1._new(image1.im.chop_xor(image2.im))


def blend(image1: Image.Image, image2: Image.Image, alpha: float) -> Image.Image:
    """Blend images using constant transparency weight. Alias for
    :py:func:`PIL.Image.blend`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.blend(image1, image2, alpha)


def composite(
    image1: Image.Image, image2: Image.Image, mask: Image.Image
) -> Image.Image:
    """Create composite using transparency mask. Alias for
    :py:func:`PIL.Image.composite`.

    :rtype: :py:class:`~PIL.Image.Image`
    """

    return Image.composite(image1, image2, mask)


def offset(image: Image.Image, xoffset: int, yoffset: int | None = None) -> Image.Image:
    """Returns a copy of the image where data has been offset by the given
    distances. Data wraps around the edges. If ``yoffset`` is omitted, it
    is assumed to be equal to ``xoffset``.

    :param image: Input image.
    :param xoffset: The horizontal distance.
    :param yoffset: The vertical distance.  If omitted, both
        distances are set to the same value.
    :rtype: :py:class:`~PIL.Image.Image`
    """

    if yoffset is None:
        yoffset = xoffset
    image.load()
    return image._new(image.im.offset(xoffset, yoffset))

# === NexusCore/openenv\Lib\site-packages\PIL\PdfImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# PDF (Acrobat) file handling
#
# History:
# 1996-07-16 fl   Created
# 1997-01-18 fl   Fixed header
# 2004-02-21 fl   Fixes for 1/L/CMYK images, etc.
# 2004-02-24 fl   Fixes for 1 and P images.
#
# Copyright (c) 1997-2004 by Secret Labs AB.  All rights reserved.
# Copyright (c) 1996-1997 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#

##
# Image plugin for PDF images (output only).
##
from __future__ import annotations

import io
import math
import os
import time
from typing import IO, Any

from . import Image, ImageFile, ImageSequence, PdfParser, __version__, features

#
# --------------------------------------------------------------------

# object ids:
#  1. catalogue
#  2. pages
#  3. image
#  4. page
#  5. page contents


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, save_all=True)


##
# (Internal) Image save plugin for the PDF format.


def _write_image(
    im: Image.Image,
    filename: str | bytes,
    existing_pdf: PdfParser.PdfParser,
    image_refs: list[PdfParser.IndirectReference],
) -> tuple[PdfParser.IndirectReference, str]:
    # FIXME: Should replace ASCIIHexDecode with RunLengthDecode
    # (packbits) or LZWDecode (tiff/lzw compression).  Note that
    # PDF 1.2 also supports Flatedecode (zip compression).

    params = None
    decode = None

    #
    # Get image characteristics

    width, height = im.size

    dict_obj: dict[str, Any] = {"BitsPerComponent": 8}
    if im.mode == "1":
        if features.check("libtiff"):
            decode_filter = "CCITTFaxDecode"
            dict_obj["BitsPerComponent"] = 1
            params = PdfParser.PdfArray(
                [
                    PdfParser.PdfDict(
                        {
                            "K": -1,
                            "BlackIs1": True,
                            "Columns": width,
                            "Rows": height,
                        }
                    )
                ]
            )
        else:
            decode_filter = "DCTDecode"
        dict_obj["ColorSpace"] = PdfParser.PdfName("DeviceGray")
        procset = "ImageB"  # grayscale
    elif im.mode == "L":
        decode_filter = "DCTDecode"
        # params = f"<< /Predictor 15 /Columns {width-2} >>"
        dict_obj["ColorSpace"] = PdfParser.PdfName("DeviceGray")
        procset = "ImageB"  # grayscale
    elif im.mode == "LA":
        decode_filter = "JPXDecode"
        # params = f"<< /Predictor 15 /Columns {width-2} >>"
        procset = "ImageB"  # grayscale
        dict_obj["SMaskInData"] = 1
    elif im.mode == "P":
        decode_filter = "ASCIIHexDecode"
        palette = im.getpalette()
        assert palette is not None
        dict_obj["ColorSpace"] = [
            PdfParser.PdfName("Indexed"),
            PdfParser.PdfName("DeviceRGB"),
            len(palette) // 3 - 1,
            PdfParser.PdfBinary(palette),
        ]
        procset = "ImageI"  # indexed color

        if "transparency" in im.info:
            smask = im.convert("LA").getchannel("A")
            smask.encoderinfo = {}

            image_ref = _write_image(smask, filename, existing_pdf, image_refs)[0]
            dict_obj["SMask"] = image_ref
    elif im.mode == "RGB":
        decode_filter = "DCTDecode"
        dict_obj["ColorSpace"] = PdfParser.PdfName("DeviceRGB")
        procset = "ImageC"  # color images
    elif im.mode == "RGBA":
        decode_filter = "JPXDecode"
        procset = "ImageC"  # color images
        dict_obj["SMaskInData"] = 1
    elif im.mode == "CMYK":
        decode_filter = "DCTDecode"
        dict_obj["ColorSpace"] = PdfParser.PdfName("DeviceCMYK")
        procset = "ImageC"  # color images
        decode = [1, 0, 1, 0, 1, 0, 1, 0]
    else:
        msg = f"cannot save mode {im.mode}"
        raise ValueError(msg)

    #
    # image

    op = io.BytesIO()

    if decode_filter == "ASCIIHexDecode":
        ImageFile._save(im, op, [ImageFile._Tile("hex", (0, 0) + im.size, 0, im.mode)])
    elif decode_filter == "CCITTFaxDecode":
        im.save(
            op,
            "TIFF",
            compression="group4",
            # use a single strip
            strip_size=math.ceil(width / 8) * height,
        )
    elif decode_filter == "DCTDecode":
        Image.SAVE["JPEG"](im, op, filename)
    elif decode_filter == "JPXDecode":
        del dict_obj["BitsPerComponent"]
        Image.SAVE["JPEG2000"](im, op, filename)
    else:
        msg = f"unsupported PDF filter ({decode_filter})"
        raise ValueError(msg)

    stream = op.getvalue()
    filter: PdfParser.PdfArray | PdfParser.PdfName
    if decode_filter == "CCITTFaxDecode":
        stream = stream[8:]
        filter = PdfParser.PdfArray([PdfParser.PdfName(decode_filter)])
    else:
        filter = PdfParser.PdfName(decode_filter)

    image_ref = image_refs.pop(0)
    existing_pdf.write_obj(
        image_ref,
        stream=stream,
        Type=PdfParser.PdfName("XObject"),
        Subtype=PdfParser.PdfName("Image"),
        Width=width,  # * 72.0 / x_resolution,
        Height=height,  # * 72.0 / y_resolution,
        Filter=filter,
        Decode=decode,
        DecodeParms=params,
        **dict_obj,
    )

    return image_ref, procset


def _save(
    im: Image.Image, fp: IO[bytes], filename: str | bytes, save_all: bool = False
) -> None:
    is_appending = im.encoderinfo.get("append", False)
    filename_str = filename.decode() if isinstance(filename, bytes) else filename
    if is_appending:
        existing_pdf = PdfParser.PdfParser(f=fp, filename=filename_str, mode="r+b")
    else:
        existing_pdf = PdfParser.PdfParser(f=fp, filename=filename_str, mode="w+b")

    dpi = im.encoderinfo.get("dpi")
    if dpi:
        x_resolution = dpi[0]
        y_resolution = dpi[1]
    else:
        x_resolution = y_resolution = im.encoderinfo.get("resolution", 72.0)

    info = {
        "title": (
            None if is_appending else os.path.splitext(os.path.basename(filename))[0]
        ),
        "author": None,
        "subject": None,
        "keywords": None,
        "creator": None,
        "producer": None,
        "creationDate": None if is_appending else time.gmtime(),
        "modDate": None if is_appending else time.gmtime(),
    }
    for k, default in info.items():
        v = im.encoderinfo.get(k) if k in im.encoderinfo else default
        if v:
            existing_pdf.info[k[0].upper() + k[1:]] = v

    #
    # make sure image data is available
    im.load()

    existing_pdf.start_writing()
    existing_pdf.write_header()
    existing_pdf.write_comment(f"created by Pillow {__version__} PDF driver")

    #
    # pages
    ims = [im]
    if save_all:
        append_images = im.encoderinfo.get("append_images", [])
        for append_im in append_images:
            append_im.encoderinfo = im.encoderinfo.copy()
            ims.append(append_im)
    number_of_pages = 0
    image_refs = []
    page_refs = []
    contents_refs = []
    for im in ims:
        im_number_of_pages = 1
        if save_all:
            im_number_of_pages = getattr(im, "n_frames", 1)
        number_of_pages += im_number_of_pages
        for i in range(im_number_of_pages):
            image_refs.append(existing_pdf.next_object_id(0))
            if im.mode == "P" and "transparency" in im.info:
                image_refs.append(existing_pdf.next_object_id(0))

            page_refs.append(existing_pdf.next_object_id(0))
            contents_refs.append(existing_pdf.next_object_id(0))
            existing_pdf.pages.append(page_refs[-1])

    #
    # catalog and list of pages
    existing_pdf.write_catalog()

    page_number = 0
    for im_sequence in ims:
        im_pages: ImageSequence.Iterator | list[Image.Image] = (
            ImageSequence.Iterator(im_sequence) if save_all else [im_sequence]
        )
        for im in im_pages:
            image_ref, procset = _write_image(im, filename, existing_pdf, image_refs)

            #
            # page

            existing_pdf.write_page(
                page_refs[page_number],
                Resources=PdfParser.PdfDict(
                    ProcSet=[PdfParser.PdfName("PDF"), PdfParser.PdfName(procset)],
                    XObject=PdfParser.PdfDict(image=image_ref),
                ),
                MediaBox=[
                    0,
                    0,
                    im.width * 72.0 / x_resolution,
                    im.height * 72.0 / y_resolution,
                ],
                Contents=contents_refs[page_number],
            )

            #
            # page contents

            page_contents = b"q %f 0 0 %f 0 0 cm /image Do Q\n" % (
                im.width * 72.0 / x_resolution,
                im.height * 72.0 / y_resolution,
            )

            existing_pdf.write_obj(contents_refs[page_number], stream=page_contents)

            page_number += 1

    #
    # trailer
    existing_pdf.write_xref_and_trailer()
    if hasattr(fp, "flush"):
        fp.flush()
    existing_pdf.close()


#
# --------------------------------------------------------------------


Image.register_save("PDF", _save)
Image.register_save_all("PDF", _save_all)

Image.register_extension("PDF", ".pdf")

Image.register_mime("PDF", "application/pdf")

# === NexusCore/openenv\Lib\site-packages\matplotlib\cm.py ===
"""
Builtin colormaps, colormap handling utilities, and the `ScalarMappable` mixin.

.. seealso::

  :doc:`/gallery/color/colormap_reference` for a list of builtin colormaps.

  :ref:`colormap-manipulation` for examples of how to make
  colormaps.

  :ref:`colormaps` an in-depth discussion of choosing
  colormaps.

  :ref:`colormapnorms` for more details about data normalization.
"""

from collections.abc import Mapping

import matplotlib as mpl
from matplotlib import _api, colors
# TODO make this warn on access
from matplotlib.colorizer import _ScalarMappable as ScalarMappable  # noqa
from matplotlib._cm import datad
from matplotlib._cm_listed import cmaps as cmaps_listed
from matplotlib._cm_multivar import cmap_families as multivar_cmaps
from matplotlib._cm_bivar import cmaps as bivar_cmaps


_LUTSIZE = mpl.rcParams['image.lut']


def _gen_cmap_registry():
    """
    Generate a dict mapping standard colormap names to standard colormaps, as
    well as the reversed colormaps.
    """
    cmap_d = {**cmaps_listed}
    for name, spec in datad.items():
        cmap_d[name] = (  # Precache the cmaps at a fixed lutsize..
            colors.LinearSegmentedColormap(name, spec, _LUTSIZE)
            if 'red' in spec else
            colors.ListedColormap(spec['listed'], name)
            if 'listed' in spec else
            colors.LinearSegmentedColormap.from_list(name, spec, _LUTSIZE))

    # Register colormap aliases for gray and grey.
    aliases = {
        # alias -> original name
        'grey': 'gray',
        'gist_grey': 'gist_gray',
        'gist_yerg': 'gist_yarg',
        'Grays': 'Greys',
    }
    for alias, original_name in aliases.items():
        cmap = cmap_d[original_name].copy()
        cmap.name = alias
        cmap_d[alias] = cmap

    # Generate reversed cmaps.
    for cmap in list(cmap_d.values()):
        rmap = cmap.reversed()
        cmap_d[rmap.name] = rmap
    return cmap_d


class ColormapRegistry(Mapping):
    r"""
    Container for colormaps that are known to Matplotlib by name.

    The universal registry instance is `matplotlib.colormaps`. There should be
    no need for users to instantiate `.ColormapRegistry` themselves.

    Read access uses a dict-like interface mapping names to `.Colormap`\s::

        import matplotlib as mpl
        cmap = mpl.colormaps['viridis']

    Returned `.Colormap`\s are copies, so that their modification does not
    change the global definition of the colormap.

    Additional colormaps can be added via `.ColormapRegistry.register`::

        mpl.colormaps.register(my_colormap)

    To get a list of all registered colormaps, you can do::

        from matplotlib import colormaps
        list(colormaps)
    """
    def __init__(self, cmaps):
        self._cmaps = cmaps
        self._builtin_cmaps = tuple(cmaps)

    def __getitem__(self, item):
        try:
            return self._cmaps[item].copy()
        except KeyError:
            raise KeyError(f"{item!r} is not a known colormap name") from None

    def __iter__(self):
        return iter(self._cmaps)

    def __len__(self):
        return len(self._cmaps)

    def __str__(self):
        return ('ColormapRegistry; available colormaps:\n' +
                ', '.join(f"'{name}'" for name in self))

    def __call__(self):
        """
        Return a list of the registered colormap names.

        This exists only for backward-compatibility in `.pyplot` which had a
        ``plt.colormaps()`` method. The recommended way to get this list is
        now ``list(colormaps)``.
        """
        return list(self)

    def register(self, cmap, *, name=None, force=False):
        """
        Register a new colormap.

        The colormap name can then be used as a string argument to any ``cmap``
        parameter in Matplotlib. It is also available in ``pyplot.get_cmap``.

        The colormap registry stores a copy of the given colormap, so that
        future changes to the original colormap instance do not affect the
        registered colormap. Think of this as the registry taking a snapshot
        of the colormap at registration.

        Parameters
        ----------
        cmap : matplotlib.colors.Colormap
            The colormap to register.

        name : str, optional
            The name for the colormap. If not given, ``cmap.name`` is used.

        force : bool, default: False
            If False, a ValueError is raised if trying to overwrite an already
            registered name. True supports overwriting registered colormaps
            other than the builtin colormaps.
        """
        _api.check_isinstance(colors.Colormap, cmap=cmap)

        name = name or cmap.name
        if name in self:
            if not force:
                # don't allow registering an already existing cmap
                # unless explicitly asked to
                raise ValueError(
                    f'A colormap named "{name}" is already registered.')
            elif name in self._builtin_cmaps:
                # We don't allow overriding a builtin.
                raise ValueError("Re-registering the builtin cmap "
                                 f"{name!r} is not allowed.")

            # Warn that we are updating an already existing colormap
            _api.warn_external(f"Overwriting the cmap {name!r} "
                               "that was already in the registry.")

        self._cmaps[name] = cmap.copy()
        # Someone may set the extremes of a builtin colormap and want to register it
        # with a different name for future lookups. The object would still have the
        # builtin name, so we should update it to the registered name
        if self._cmaps[name].name != name:
            self._cmaps[name].name = name

    def unregister(self, name):
        """
        Remove a colormap from the registry.

        You cannot remove built-in colormaps.

        If the named colormap is not registered, returns with no error, raises
        if you try to de-register a default colormap.

        .. warning::

            Colormap names are currently a shared namespace that may be used
            by multiple packages. Use `unregister` only if you know you
            have registered that name before. In particular, do not
            unregister just in case to clean the name before registering a
            new colormap.

        Parameters
        ----------
        name : str
            The name of the colormap to be removed.

        Raises
        ------
        ValueError
            If you try to remove a default built-in colormap.
        """
        if name in self._builtin_cmaps:
            raise ValueError(f"cannot unregister {name!r} which is a builtin "
                             "colormap.")
        self._cmaps.pop(name, None)

    def get_cmap(self, cmap):
        """
        Return a color map specified through *cmap*.

        Parameters
        ----------
        cmap : str or `~matplotlib.colors.Colormap` or None

            - if a `.Colormap`, return it
            - if a string, look it up in ``mpl.colormaps``
            - if None, return the Colormap defined in :rc:`image.cmap`

        Returns
        -------
        Colormap
        """
        # get the default color map
        if cmap is None:
            return self[mpl.rcParams["image.cmap"]]

        # if the user passed in a Colormap, simply return it
        if isinstance(cmap, colors.Colormap):
            return cmap
        if isinstance(cmap, str):
            _api.check_in_list(sorted(_colormaps), cmap=cmap)
            # otherwise, it must be a string so look it up
            return self[cmap]
        raise TypeError(
            'get_cmap expects None or an instance of a str or Colormap . ' +
            f'you passed {cmap!r} of type {type(cmap)}'
        )


# public access to the colormaps should be via `matplotlib.colormaps`. For now,
# we still create the registry here, but that should stay an implementation
# detail.
_colormaps = ColormapRegistry(_gen_cmap_registry())
globals().update(_colormaps)

_multivar_colormaps = ColormapRegistry(multivar_cmaps)

_bivar_colormaps = ColormapRegistry(bivar_cmaps)


# This is an exact copy of pyplot.get_cmap(). It was removed in 3.9, but apparently
# caused more user trouble than expected. Re-added for 3.9.1 and extended the
# deprecation period for two additional minor releases.
@_api.deprecated(
    '3.7',
    removal='3.11',
    alternative="``matplotlib.colormaps[name]`` or ``matplotlib.colormaps.get_cmap()``"
                " or ``pyplot.get_cmap()``"
    )
def get_cmap(name=None, lut=None):
    """
    Get a colormap instance, defaulting to rc values if *name* is None.

    Parameters
    ----------
    name : `~matplotlib.colors.Colormap` or str or None, default: None
        If a `.Colormap` instance, it will be returned. Otherwise, the name of
        a colormap known to Matplotlib, which will be resampled by *lut*. The
        default, None, means :rc:`image.cmap`.
    lut : int or None, default: None
        If *name* is not already a Colormap instance and *lut* is not None, the
        colormap will be resampled to have *lut* entries in the lookup table.

    Returns
    -------
    Colormap
    """
    if name is None:
        name = mpl.rcParams['image.cmap']
    if isinstance(name, colors.Colormap):
        return name
    _api.check_in_list(sorted(_colormaps), name=name)
    if lut is None:
        return _colormaps[name]
    else:
        return _colormaps[name].resampled(lut)


def _ensure_cmap(cmap):
    """
    Ensure that we have a `.Colormap` object.

    For internal use to preserve type stability of errors.

    Parameters
    ----------
    cmap : None, str, Colormap

        - if a `Colormap`, return it
        - if a string, look it up in mpl.colormaps
        - if None, look up the default color map in mpl.colormaps

    Returns
    -------
    Colormap

    """
    if isinstance(cmap, colors.Colormap):
        return cmap
    cmap_name = cmap if cmap is not None else mpl.rcParams["image.cmap"]
    # use check_in_list to ensure type stability of the exception raised by
    # the internal usage of this (ValueError vs KeyError)
    if cmap_name not in _colormaps:
        _api.check_in_list(sorted(_colormaps), cmap=cmap_name)
    return mpl.colormaps[cmap_name]

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\svgPathPen.py ===
from typing import Callable
from fontTools.pens.basePen import BasePen


def pointToString(pt, ntos=str):
    return " ".join(ntos(i) for i in pt)


class SVGPathPen(BasePen):
    """Pen to draw SVG path d commands.

    Args:
        glyphSet: a dictionary of drawable glyph objects keyed by name
            used to resolve component references in composite glyphs.
        ntos: a callable that takes a number and returns a string, to
            customize how numbers are formatted (default: str).

    :Example:
        .. code-block::

            >>> pen = SVGPathPen(None)
            >>> pen.moveTo((0, 0))
            >>> pen.lineTo((1, 1))
            >>> pen.curveTo((2, 2), (3, 3), (4, 4))
            >>> pen.closePath()
            >>> pen.getCommands()
            'M0 0 1 1C2 2 3 3 4 4Z'

    Note:
        Fonts have a coordinate system where Y grows up, whereas in SVG,
        Y grows down.  As such, rendering path data from this pen in
        SVG typically results in upside-down glyphs.  You can fix this
        by wrapping the data from this pen in an SVG group element with
        transform, or wrap this pen in a transform pen.  For example:
        .. code-block:: python

            spen = svgPathPen.SVGPathPen(glyphset)
            pen= TransformPen(spen , (1, 0, 0, -1, 0, 0))
            glyphset[glyphname].draw(pen)
            print(tpen.getCommands())
    """

    def __init__(self, glyphSet, ntos: Callable[[float], str] = str):
        BasePen.__init__(self, glyphSet)
        self._commands = []
        self._lastCommand = None
        self._lastX = None
        self._lastY = None
        self._ntos = ntos

    def _handleAnchor(self):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((0, 0))
        >>> pen.moveTo((10, 10))
        >>> pen._commands
        ['M10 10']
        """
        if self._lastCommand == "M":
            self._commands.pop(-1)

    def _moveTo(self, pt):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((0, 0))
        >>> pen._commands
        ['M0 0']

        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((10, 0))
        >>> pen._commands
        ['M10 0']

        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((0, 10))
        >>> pen._commands
        ['M0 10']
        """
        self._handleAnchor()
        t = "M%s" % (pointToString(pt, self._ntos))
        self._commands.append(t)
        self._lastCommand = "M"
        self._lastX, self._lastY = pt

    def _lineTo(self, pt):
        """
        # duplicate point
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((10, 10))
        >>> pen.lineTo((10, 10))
        >>> pen._commands
        ['M10 10']

        # vertical line
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((10, 10))
        >>> pen.lineTo((10, 0))
        >>> pen._commands
        ['M10 10', 'V0']

        # horizontal line
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((10, 10))
        >>> pen.lineTo((0, 10))
        >>> pen._commands
        ['M10 10', 'H0']

        # basic
        >>> pen = SVGPathPen(None)
        >>> pen.lineTo((70, 80))
        >>> pen._commands
        ['L70 80']

        # basic following a moveto
        >>> pen = SVGPathPen(None)
        >>> pen.moveTo((0, 0))
        >>> pen.lineTo((10, 10))
        >>> pen._commands
        ['M0 0', ' 10 10']
        """
        x, y = pt
        # duplicate point
        if x == self._lastX and y == self._lastY:
            return
        # vertical line
        elif x == self._lastX:
            cmd = "V"
            pts = self._ntos(y)
        # horizontal line
        elif y == self._lastY:
            cmd = "H"
            pts = self._ntos(x)
        # previous was a moveto
        elif self._lastCommand == "M":
            cmd = None
            pts = " " + pointToString(pt, self._ntos)
        # basic
        else:
            cmd = "L"
            pts = pointToString(pt, self._ntos)
        # write the string
        t = ""
        if cmd:
            t += cmd
            self._lastCommand = cmd
        t += pts
        self._commands.append(t)
        # store for future reference
        self._lastX, self._lastY = pt

    def _curveToOne(self, pt1, pt2, pt3):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.curveTo((10, 20), (30, 40), (50, 60))
        >>> pen._commands
        ['C10 20 30 40 50 60']
        """
        t = "C"
        t += pointToString(pt1, self._ntos) + " "
        t += pointToString(pt2, self._ntos) + " "
        t += pointToString(pt3, self._ntos)
        self._commands.append(t)
        self._lastCommand = "C"
        self._lastX, self._lastY = pt3

    def _qCurveToOne(self, pt1, pt2):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.qCurveTo((10, 20), (30, 40))
        >>> pen._commands
        ['Q10 20 30 40']
        >>> from fontTools.misc.roundTools import otRound
        >>> pen = SVGPathPen(None, ntos=lambda v: str(otRound(v)))
        >>> pen.qCurveTo((3, 3), (7, 5), (11, 4))
        >>> pen._commands
        ['Q3 3 5 4', 'Q7 5 11 4']
        """
        assert pt2 is not None
        t = "Q"
        t += pointToString(pt1, self._ntos) + " "
        t += pointToString(pt2, self._ntos)
        self._commands.append(t)
        self._lastCommand = "Q"
        self._lastX, self._lastY = pt2

    def _closePath(self):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.closePath()
        >>> pen._commands
        ['Z']
        """
        self._commands.append("Z")
        self._lastCommand = "Z"
        self._lastX = self._lastY = None

    def _endPath(self):
        """
        >>> pen = SVGPathPen(None)
        >>> pen.endPath()
        >>> pen._commands
        []
        """
        self._lastCommand = None
        self._lastX = self._lastY = None

    def getCommands(self):
        return "".join(self._commands)


def main(args=None):
    """Generate per-character SVG from font and text"""

    if args is None:
        import sys

        args = sys.argv[1:]

    from fontTools.ttLib import TTFont
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools pens.svgPathPen", description="Generate SVG from text"
    )
    parser.add_argument("font", metavar="font.ttf", help="Font file.")
    parser.add_argument("text", metavar="text", nargs="?", help="Text string.")
    parser.add_argument(
        "-y",
        metavar="<number>",
        help="Face index into a collection to open. Zero based.",
    )
    parser.add_argument(
        "--glyphs",
        metavar="whitespace-separated list of glyph names",
        type=str,
        help="Glyphs to show. Exclusive with text option",
    )
    parser.add_argument(
        "--variations",
        metavar="AXIS=LOC",
        default="",
        help="List of space separated locations. A location consist in "
        "the name of a variation axis, followed by '=' and a number. E.g.: "
        "wght=700 wdth=80. The default is the location of the base master.",
    )

    options = parser.parse_args(args)

    fontNumber = int(options.y) if options.y is not None else 0

    font = TTFont(options.font, fontNumber=fontNumber)
    text = options.text
    glyphs = options.glyphs

    location = {}
    for tag_v in options.variations.split():
        fields = tag_v.split("=")
        tag = fields[0].strip()
        v = float(fields[1])
        location[tag] = v

    hhea = font["hhea"]
    ascent, descent = hhea.ascent, hhea.descent

    glyphset = font.getGlyphSet(location=location)
    cmap = font["cmap"].getBestCmap()

    if glyphs is not None and text is not None:
        raise ValueError("Options --glyphs and --text are exclusive")

    if glyphs is None:
        glyphs = " ".join(cmap[ord(u)] for u in text)

    glyphs = glyphs.split()

    s = ""
    width = 0
    for g in glyphs:
        glyph = glyphset[g]

        pen = SVGPathPen(glyphset)
        glyph.draw(pen)
        commands = pen.getCommands()

        s += '<g transform="translate(%d %d) scale(1 -1)"><path d="%s"/></g>\n' % (
            width,
            ascent,
            commands,
        )

        width += glyph.width

    print('<?xml version="1.0" encoding="UTF-8"?>')
    print(
        '<svg width="%d" height="%d" xmlns="http://www.w3.org/2000/svg">'
        % (width, ascent - descent)
    )
    print(s, end="")
    print("</svg>")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        import doctest

        sys.exit(doctest.testmod().failed)

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\field_mask.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains FieldMask class."""

from google.protobuf.descriptor import FieldDescriptor


class FieldMask(object):
  """Class for FieldMask message type."""

  __slots__ = ()

  def ToJsonString(self):
    """Converts FieldMask to string according to proto3 JSON spec."""
    camelcase_paths = []
    for path in self.paths:
      camelcase_paths.append(_SnakeCaseToCamelCase(path))
    return ','.join(camelcase_paths)

  def FromJsonString(self, value):
    """Converts string to FieldMask according to proto3 JSON spec."""
    if not isinstance(value, str):
      raise ValueError('FieldMask JSON value not a string: {!r}'.format(value))
    self.Clear()
    if value:
      for path in value.split(','):
        self.paths.append(_CamelCaseToSnakeCase(path))

  def IsValidForDescriptor(self, message_descriptor):
    """Checks whether the FieldMask is valid for Message Descriptor."""
    for path in self.paths:
      if not _IsValidPath(message_descriptor, path):
        return False
    return True

  def AllFieldsFromDescriptor(self, message_descriptor):
    """Gets all direct fields of Message Descriptor to FieldMask."""
    self.Clear()
    for field in message_descriptor.fields:
      self.paths.append(field.name)

  def CanonicalFormFromMask(self, mask):
    """Converts a FieldMask to the canonical form.

    Removes paths that are covered by another path. For example,
    "foo.bar" is covered by "foo" and will be removed if "foo"
    is also in the FieldMask. Then sorts all paths in alphabetical order.

    Args:
      mask: The original FieldMask to be converted.
    """
    tree = _FieldMaskTree(mask)
    tree.ToFieldMask(self)

  def Union(self, mask1, mask2):
    """Merges mask1 and mask2 into this FieldMask."""
    _CheckFieldMaskMessage(mask1)
    _CheckFieldMaskMessage(mask2)
    tree = _FieldMaskTree(mask1)
    tree.MergeFromFieldMask(mask2)
    tree.ToFieldMask(self)

  def Intersect(self, mask1, mask2):
    """Intersects mask1 and mask2 into this FieldMask."""
    _CheckFieldMaskMessage(mask1)
    _CheckFieldMaskMessage(mask2)
    tree = _FieldMaskTree(mask1)
    intersection = _FieldMaskTree()
    for path in mask2.paths:
      tree.IntersectPath(path, intersection)
    intersection.ToFieldMask(self)

  def MergeMessage(
      self, source, destination,
      replace_message_field=False, replace_repeated_field=False):
    """Merges fields specified in FieldMask from source to destination.

    Args:
      source: Source message.
      destination: The destination message to be merged into.
      replace_message_field: Replace message field if True. Merge message
          field if False.
      replace_repeated_field: Replace repeated field if True. Append
          elements of repeated field if False.
    """
    tree = _FieldMaskTree(self)
    tree.MergeMessage(
        source, destination, replace_message_field, replace_repeated_field)


def _IsValidPath(message_descriptor, path):
  """Checks whether the path is valid for Message Descriptor."""
  parts = path.split('.')
  last = parts.pop()
  for name in parts:
    field = message_descriptor.fields_by_name.get(name)
    if (field is None or
        field.label == FieldDescriptor.LABEL_REPEATED or
        field.type != FieldDescriptor.TYPE_MESSAGE):
      return False
    message_descriptor = field.message_type
  return last in message_descriptor.fields_by_name


def _CheckFieldMaskMessage(message):
  """Raises ValueError if message is not a FieldMask."""
  message_descriptor = message.DESCRIPTOR
  if (message_descriptor.name != 'FieldMask' or
      message_descriptor.file.name != 'google/protobuf/field_mask.proto'):
    raise ValueError('Message {0} is not a FieldMask.'.format(
        message_descriptor.full_name))


def _SnakeCaseToCamelCase(path_name):
  """Converts a path name from snake_case to camelCase."""
  result = []
  after_underscore = False
  for c in path_name:
    if c.isupper():
      raise ValueError(
          'Fail to print FieldMask to Json string: Path name '
          '{0} must not contain uppercase letters.'.format(path_name))
    if after_underscore:
      if c.islower():
        result.append(c.upper())
        after_underscore = False
      else:
        raise ValueError(
            'Fail to print FieldMask to Json string: The '
            'character after a "_" must be a lowercase letter '
            'in path name {0}.'.format(path_name))
    elif c == '_':
      after_underscore = True
    else:
      result += c

  if after_underscore:
    raise ValueError('Fail to print FieldMask to Json string: Trailing "_" '
                     'in path name {0}.'.format(path_name))
  return ''.join(result)


def _CamelCaseToSnakeCase(path_name):
  """Converts a field name from camelCase to snake_case."""
  result = []
  for c in path_name:
    if c == '_':
      raise ValueError('Fail to parse FieldMask: Path name '
                       '{0} must not contain "_"s.'.format(path_name))
    if c.isupper():
      result += '_'
      result += c.lower()
    else:
      result += c
  return ''.join(result)


class _FieldMaskTree(object):
  """Represents a FieldMask in a tree structure.

  For example, given a FieldMask "foo.bar,foo.baz,bar.baz",
  the FieldMaskTree will be:
      [_root] -+- foo -+- bar
            |       |
            |       +- baz
            |
            +- bar --- baz
  In the tree, each leaf node represents a field path.
  """

  __slots__ = ('_root',)

  def __init__(self, field_mask=None):
    """Initializes the tree by FieldMask."""
    self._root = {}
    if field_mask:
      self.MergeFromFieldMask(field_mask)

  def MergeFromFieldMask(self, field_mask):
    """Merges a FieldMask to the tree."""
    for path in field_mask.paths:
      self.AddPath(path)

  def AddPath(self, path):
    """Adds a field path into the tree.

    If the field path to add is a sub-path of an existing field path
    in the tree (i.e., a leaf node), it means the tree already matches
    the given path so nothing will be added to the tree. If the path
    matches an existing non-leaf node in the tree, that non-leaf node
    will be turned into a leaf node with all its children removed because
    the path matches all the node's children. Otherwise, a new path will
    be added.

    Args:
      path: The field path to add.
    """
    node = self._root
    for name in path.split('.'):
      if name not in node:
        node[name] = {}
      elif not node[name]:
        # Pre-existing empty node implies we already have this entire tree.
        return
      node = node[name]
    # Remove any sub-trees we might have had.
    node.clear()

  def ToFieldMask(self, field_mask):
    """Converts the tree to a FieldMask."""
    field_mask.Clear()
    _AddFieldPaths(self._root, '', field_mask)

  def IntersectPath(self, path, intersection):
    """Calculates the intersection part of a field path with this tree.

    Args:
      path: The field path to calculates.
      intersection: The out tree to record the intersection part.
    """
    node = self._root
    for name in path.split('.'):
      if name not in node:
        return
      elif not node[name]:
        intersection.AddPath(path)
        return
      node = node[name]
    intersection.AddLeafNodes(path, node)

  def AddLeafNodes(self, prefix, node):
    """Adds leaf nodes begin with prefix to this tree."""
    if not node:
      self.AddPath(prefix)
    for name in node:
      child_path = prefix + '.' + name
      self.AddLeafNodes(child_path, node[name])

  def MergeMessage(
      self, source, destination,
      replace_message, replace_repeated):
    """Merge all fields specified by this tree from source to destination."""
    _MergeMessage(
        self._root, source, destination, replace_message, replace_repeated)


def _StrConvert(value):
  """Converts value to str if it is not."""
  # This file is imported by c extension and some methods like ClearField
  # requires string for the field name. py2/py3 has different text
  # type and may use unicode.
  if not isinstance(value, str):
    return value.encode('utf-8')
  return value


def _MergeMessage(
    node, source, destination, replace_message, replace_repeated):
  """Merge all fields specified by a sub-tree from source to destination."""
  source_descriptor = source.DESCRIPTOR
  for name in node:
    child = node[name]
    field = source_descriptor.fields_by_name[name]
    if field is None:
      raise ValueError('Error: Can\'t find field {0} in message {1}.'.format(
          name, source_descriptor.full_name))
    if child:
      # Sub-paths are only allowed for singular message fields.
      if (field.label == FieldDescriptor.LABEL_REPEATED or
          field.cpp_type != FieldDescriptor.CPPTYPE_MESSAGE):
        raise ValueError('Error: Field {0} in message {1} is not a singular '
                         'message field and cannot have sub-fields.'.format(
                             name, source_descriptor.full_name))
      if source.HasField(name):
        _MergeMessage(
            child, getattr(source, name), getattr(destination, name),
            replace_message, replace_repeated)
      continue
    if field.label == FieldDescriptor.LABEL_REPEATED:
      if replace_repeated:
        destination.ClearField(_StrConvert(name))
      repeated_source = getattr(source, name)
      repeated_destination = getattr(destination, name)
      repeated_destination.MergeFrom(repeated_source)
    else:
      if field.cpp_type == FieldDescriptor.CPPTYPE_MESSAGE:
        if replace_message:
          destination.ClearField(_StrConvert(name))
        if source.HasField(name):
          getattr(destination, name).MergeFrom(getattr(source, name))
      else:
        setattr(destination, name, getattr(source, name))


def _AddFieldPaths(node, prefix, field_mask):
  """Adds the field paths descended from node to field_mask."""
  if not node and prefix:
    field_mask.paths.append(prefix)
    return
  for name in sorted(node):
    if prefix:
      child_path = prefix + '.' + name
    else:
      child_path = name
    _AddFieldPaths(node[name], child_path, field_mask)

# === NexusCore/openenv\Lib\site-packages\IPython\core\magic_arguments.py ===
'''A decorator-based method of constructing IPython magics with `argparse`
option handling.

New magic functions can be defined like so::

    from IPython.core.magic_arguments import (argument, magic_arguments,
        parse_argstring)

    @magic_arguments()
    @argument('-o', '--option', help='An optional argument.')
    @argument('arg', type=int, help='An integer positional argument.')
    def magic_cool(self, arg):
        """ A really cool magic command.

    """
        args = parse_argstring(magic_cool, arg)
        ...

The `@magic_arguments` decorator marks the function as having argparse arguments.
The `@argument` decorator adds an argument using the same syntax as argparse's
`add_argument()` method. More sophisticated uses may also require the
`@argument_group` or `@kwds` decorator to customize the formatting and the
parsing.

Help text for the magic is automatically generated from the docstring and the
arguments::

    In[1]: %cool?
        %cool [-o OPTION] arg

        A really cool magic command.

        positional arguments:
          arg                   An integer positional argument.

        optional arguments:
          -o OPTION, --option OPTION
                                An optional argument.

Here is an elaborated example that uses default parameters in `argument` and calls the `args` in the cell magic::

    from IPython.core.magic import register_cell_magic
    from IPython.core.magic_arguments import (argument, magic_arguments,
                                            parse_argstring)


    @magic_arguments()
    @argument(
        "--option",
        "-o",
        help=("Add an option here"),
    )
    @argument(
        "--style",
        "-s",
        default="foo",
        help=("Add some style arguments"),
    )
    @register_cell_magic
    def my_cell_magic(line, cell):
        args = parse_argstring(my_cell_magic, line)
        print(f"{args.option=}")
        print(f"{args.style=}")
        print(f"{cell=}")

In a jupyter notebook, this cell magic can be executed like this::

    %%my_cell_magic -o Hello
    print("bar")
    i = 42

Inheritance diagram:

.. inheritance-diagram:: IPython.core.magic_arguments
   :parts: 3

'''
#-----------------------------------------------------------------------------
# Copyright (C) 2010-2011, IPython Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------
import argparse
import re

# Our own imports
from IPython.core.error import UsageError
from IPython.utils.decorators import undoc
from IPython.utils.process import arg_split
from IPython.utils.text import dedent

NAME_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*$")

@undoc
class MagicHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """A HelpFormatter with a couple of changes to meet our needs.
    """
    # Modified to dedent text.
    def _fill_text(self, text, width, indent):
        return argparse.RawDescriptionHelpFormatter._fill_text(self, dedent(text), width, indent)

    # Modified to wrap argument placeholders in <> where necessary.
    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar

        else:
            parts = []

            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                # IPYTHON MODIFICATION: If args_string is not a plain name, wrap
                # it in <> so it's valid RST.
                if not NAME_RE.match(args_string):
                    args_string = "<%s>" % args_string
                for option_string in action.option_strings:
                    parts.append('%s %s' % (option_string, args_string))

            return ', '.join(parts)

    # Override the default prefix ('usage') to our % magic escape,
    # in a code block.
    def add_usage(self, usage, actions, groups, prefix="::\n\n  %"):
        super(MagicHelpFormatter, self).add_usage(usage, actions, groups, prefix)

class MagicArgumentParser(argparse.ArgumentParser):
    """ An ArgumentParser tweaked for use by IPython magics.
    """
    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 parents=None,
                 formatter_class=MagicHelpFormatter,
                 prefix_chars='-',
                 argument_default=None,
                 conflict_handler='error',
                 add_help=False):
        if parents is None:
            parents = []
        super(MagicArgumentParser, self).__init__(prog=prog, usage=usage,
            description=description, epilog=epilog,
            parents=parents, formatter_class=formatter_class,
            prefix_chars=prefix_chars, argument_default=argument_default,
            conflict_handler=conflict_handler, add_help=add_help)

    def error(self, message):
        """ Raise a catchable error instead of exiting.
        """
        raise UsageError(message)

    def parse_argstring(self, argstring):
        """ Split a string into an argument list and parse that argument list.
        """
        argv = arg_split(argstring)
        return self.parse_args(argv)


def construct_parser(magic_func):
    """ Construct an argument parser using the function decorations.
    """
    kwds = getattr(magic_func, 'argcmd_kwds', {})
    if 'description' not in kwds:
        kwds['description'] = getattr(magic_func, '__doc__', None)
    arg_name = real_name(magic_func)
    parser = MagicArgumentParser(arg_name, **kwds)
    # Reverse the list of decorators in order to apply them in the
    # order in which they appear in the source.
    group = None
    for deco in magic_func.decorators[::-1]:
        result = deco.add_to_parser(parser, group)
        if result is not None:
            group = result

    # Replace the magic function's docstring with the full help text.
    magic_func.__doc__ = parser.format_help()

    return parser


def parse_argstring(magic_func, argstring):
    """ Parse the string of arguments for the given magic function.
    """
    return magic_func.parser.parse_argstring(argstring)


def real_name(magic_func):
    """ Find the real name of the magic.
    """
    magic_name = magic_func.__name__
    if magic_name.startswith('magic_'):
        magic_name = magic_name[len('magic_'):]
    return getattr(magic_func, 'argcmd_name', magic_name)


class ArgDecorator:
    """ Base class for decorators to add ArgumentParser information to a method.
    """

    def __call__(self, func):
        if not getattr(func, 'has_arguments', False):
            func.has_arguments = True
            func.decorators = []
        func.decorators.append(self)
        return func

    def add_to_parser(self, parser, group):
        """ Add this object's information to the parser, if necessary.
        """
        pass


class magic_arguments(ArgDecorator):
    """ Mark the magic as having argparse arguments and possibly adjust the
    name.
    """

    def __init__(self, name=None):
        self.name = name

    def __call__(self, func):
        if not getattr(func, 'has_arguments', False):
            func.has_arguments = True
            func.decorators = []
        if self.name is not None:
            func.argcmd_name = self.name
        # This should be the first decorator in the list of decorators, thus the
        # last to execute. Build the parser.
        func.parser = construct_parser(func)
        return func


class ArgMethodWrapper(ArgDecorator):

    """
    Base class to define a wrapper for ArgumentParser method.

    Child class must define either `_method_name` or `add_to_parser`.

    """

    _method_name: str

    def __init__(self, *args, **kwds):
        self.args = args
        self.kwds = kwds

    def add_to_parser(self, parser, group):
        """ Add this object's information to the parser.
        """
        if group is not None:
            parser = group
        getattr(parser, self._method_name)(*self.args, **self.kwds)
        return None


class argument(ArgMethodWrapper):
    """ Store arguments and keywords to pass to add_argument().

    Instances also serve to decorate command methods.
    """
    _method_name = 'add_argument'


class defaults(ArgMethodWrapper):
    """ Store arguments and keywords to pass to set_defaults().

    Instances also serve to decorate command methods.
    """
    _method_name = 'set_defaults'


class argument_group(ArgMethodWrapper):
    """ Store arguments and keywords to pass to add_argument_group().

    Instances also serve to decorate command methods.
    """

    def add_to_parser(self, parser, group):
        """ Add this object's information to the parser.
        """
        return parser.add_argument_group(*self.args, **self.kwds)


class kwds(ArgDecorator):
    """ Provide other keywords to the sub-parser constructor.
    """
    def __init__(self, **kwds):
        self.kwds = kwds

    def __call__(self, func):
        func = super(kwds, self).__call__(func)
        func.argcmd_kwds = self.kwds
        return func


__all__ = ['magic_arguments', 'argument', 'argument_group', 'kwds',
    'parse_argstring']

# === NexusCore/openenv\Lib\site-packages\jedi\inference\gradual\typeshed.py ===
import os
import re
from functools import wraps
from collections import namedtuple
from typing import Dict, Mapping, Tuple
from pathlib import Path

from jedi import settings
from jedi.file_io import FileIO
from jedi.parser_utils import get_cached_code_lines
from jedi.inference.base_value import ValueSet, NO_VALUES
from jedi.inference.gradual.stub_value import TypingModuleWrapper, StubModuleValue
from jedi.inference.value import ModuleValue

_jedi_path = Path(__file__).parent.parent.parent
TYPESHED_PATH = _jedi_path.joinpath('third_party', 'typeshed')
DJANGO_INIT_PATH = _jedi_path.joinpath('third_party', 'django-stubs',
                                       'django-stubs', '__init__.pyi')

_IMPORT_MAP = dict(
    _collections='collections',
    _socket='socket',
)

PathInfo = namedtuple('PathInfo', 'path is_third_party')


def _merge_create_stub_map(path_infos):
    map_ = {}
    for directory_path_info in path_infos:
        map_.update(_create_stub_map(directory_path_info))
    return map_


def _create_stub_map(directory_path_info):
    """
    Create a mapping of an importable name in Python to a stub file.
    """
    def generate():
        try:
            listed = os.listdir(directory_path_info.path)
        except (FileNotFoundError, NotADirectoryError):
            return

        for entry in listed:
            path = os.path.join(directory_path_info.path, entry)
            if os.path.isdir(path):
                init = os.path.join(path, '__init__.pyi')
                if os.path.isfile(init):
                    yield entry, PathInfo(init, directory_path_info.is_third_party)
            elif entry.endswith('.pyi') and os.path.isfile(path):
                name = entry[:-4]
                if name != '__init__':
                    yield name, PathInfo(path, directory_path_info.is_third_party)

    # Create a dictionary from the tuple generator.
    return dict(generate())


def _get_typeshed_directories(version_info):
    check_version_list = ['2and3', '3']
    for base in ['stdlib', 'third_party']:
        base_path = TYPESHED_PATH.joinpath(base)
        base_list = os.listdir(base_path)
        for base_list_entry in base_list:
            match = re.match(r'(\d+)\.(\d+)$', base_list_entry)
            if match is not None:
                if match.group(1) == '3' and int(match.group(2)) <= version_info.minor:
                    check_version_list.append(base_list_entry)

        for check_version in check_version_list:
            is_third_party = base != 'stdlib'
            yield PathInfo(str(base_path.joinpath(check_version)), is_third_party)


_version_cache: Dict[Tuple[int, int], Mapping[str, PathInfo]] = {}


def _cache_stub_file_map(version_info):
    """
    Returns a map of an importable name in Python to a stub file.
    """
    # TODO this caches the stub files indefinitely, maybe use a time cache
    # for that?
    version = version_info[:2]
    try:
        return _version_cache[version]
    except KeyError:
        pass

    _version_cache[version] = file_set = \
        _merge_create_stub_map(_get_typeshed_directories(version_info))
    return file_set


def import_module_decorator(func):
    @wraps(func)
    def wrapper(inference_state, import_names, parent_module_value, sys_path, prefer_stubs):
        python_value_set = inference_state.module_cache.get(import_names)
        if python_value_set is None:
            if parent_module_value is not None and parent_module_value.is_stub():
                parent_module_values = parent_module_value.non_stub_value_set
            else:
                parent_module_values = [parent_module_value]
            if import_names == ('os', 'path'):
                # This is a huge exception, we follow a nested import
                # ``os.path``, because it's a very important one in Python
                # that is being achieved by messing with ``sys.modules`` in
                # ``os``.
                python_value_set = ValueSet.from_sets(
                    func(inference_state, (n,), None, sys_path,)
                    for n in ['posixpath', 'ntpath', 'macpath', 'os2emxpath']
                )
            else:
                python_value_set = ValueSet.from_sets(
                    func(inference_state, import_names, p, sys_path,)
                    for p in parent_module_values
                )
            inference_state.module_cache.add(import_names, python_value_set)

        if not prefer_stubs or import_names[0] in settings.auto_import_modules:
            return python_value_set

        stub = try_to_load_stub_cached(inference_state, import_names, python_value_set,
                                       parent_module_value, sys_path)
        if stub is not None:
            return ValueSet([stub])
        return python_value_set

    return wrapper


def try_to_load_stub_cached(inference_state, import_names, *args, **kwargs):
    if import_names is None:
        return None

    try:
        return inference_state.stub_module_cache[import_names]
    except KeyError:
        pass

    # TODO is this needed? where are the exceptions coming from that make this
    # necessary? Just remove this line.
    inference_state.stub_module_cache[import_names] = None
    inference_state.stub_module_cache[import_names] = result = \
        _try_to_load_stub(inference_state, import_names, *args, **kwargs)
    return result


def _try_to_load_stub(inference_state, import_names, python_value_set,
                      parent_module_value, sys_path):
    """
    Trying to load a stub for a set of import_names.

    This is modelled to work like "PEP 561 -- Distributing and Packaging Type
    Information", see https://www.python.org/dev/peps/pep-0561.
    """
    if parent_module_value is None and len(import_names) > 1:
        try:
            parent_module_value = try_to_load_stub_cached(
                inference_state, import_names[:-1], NO_VALUES,
                parent_module_value=None, sys_path=sys_path)
        except KeyError:
            pass

    # 1. Try to load foo-stubs folders on path for import name foo.
    if len(import_names) == 1:
        # foo-stubs
        for p in sys_path:
            init = os.path.join(p, *import_names) + '-stubs' + os.path.sep + '__init__.pyi'
            m = _try_to_load_stub_from_file(
                inference_state,
                python_value_set,
                file_io=FileIO(init),
                import_names=import_names,
            )
            if m is not None:
                return m
        if import_names[0] == 'django' and python_value_set:
            return _try_to_load_stub_from_file(
                inference_state,
                python_value_set,
                file_io=FileIO(str(DJANGO_INIT_PATH)),
                import_names=import_names,
            )

    # 2. Try to load pyi files next to py files.
    for c in python_value_set:
        try:
            method = c.py__file__
        except AttributeError:
            pass
        else:
            file_path = method()
            file_paths = []
            if c.is_namespace():
                file_paths = [os.path.join(p, '__init__.pyi') for p in c.py__path__()]
            elif file_path is not None and file_path.suffix == '.py':
                file_paths = [str(file_path) + 'i']

            for file_path in file_paths:
                m = _try_to_load_stub_from_file(
                    inference_state,
                    python_value_set,
                    # The file path should end with .pyi
                    file_io=FileIO(file_path),
                    import_names=import_names,
                )
                if m is not None:
                    return m

    # 3. Try to load typeshed
    m = _load_from_typeshed(inference_state, python_value_set, parent_module_value, import_names)
    if m is not None:
        return m

    # 4. Try to load pyi file somewhere if python_value_set was not defined.
    if not python_value_set:
        if parent_module_value is not None:
            check_path = parent_module_value.py__path__() or []
            # In case import_names
            names_for_path = (import_names[-1],)
        else:
            check_path = sys_path
            names_for_path = import_names

        for p in check_path:
            m = _try_to_load_stub_from_file(
                inference_state,
                python_value_set,
                file_io=FileIO(os.path.join(p, *names_for_path) + '.pyi'),
                import_names=import_names,
            )
            if m is not None:
                return m

    # If no stub is found, that's fine, the calling function has to deal with
    # it.
    return None


def _load_from_typeshed(inference_state, python_value_set, parent_module_value, import_names):
    import_name = import_names[-1]
    map_ = None
    if len(import_names) == 1:
        map_ = _cache_stub_file_map(inference_state.grammar.version_info)
        import_name = _IMPORT_MAP.get(import_name, import_name)
    elif isinstance(parent_module_value, ModuleValue):
        if not parent_module_value.is_package():
            # Only if it's a package (= a folder) something can be
            # imported.
            return None
        paths = parent_module_value.py__path__()
        # Once the initial package has been loaded, the sub packages will
        # always be loaded, regardless if they are there or not. This makes
        # sense, IMO, because stubs take preference, even if the original
        # library doesn't provide a module (it could be dynamic). ~dave
        map_ = _merge_create_stub_map([PathInfo(p, is_third_party=False) for p in paths])

    if map_ is not None:
        path_info = map_.get(import_name)
        if path_info is not None and (not path_info.is_third_party or python_value_set):
            return _try_to_load_stub_from_file(
                inference_state,
                python_value_set,
                file_io=FileIO(path_info.path),
                import_names=import_names,
            )


def _try_to_load_stub_from_file(inference_state, python_value_set, file_io, import_names):
    try:
        stub_module_node = parse_stub_module(inference_state, file_io)
    except OSError:
        # The file that you're looking for doesn't exist (anymore).
        return None
    else:
        return create_stub_module(
            inference_state, inference_state.latest_grammar, python_value_set,
            stub_module_node, file_io, import_names
        )


def parse_stub_module(inference_state, file_io):
    return inference_state.parse(
        file_io=file_io,
        cache=True,
        diff_cache=settings.fast_parser,
        cache_path=settings.cache_directory,
        use_latest_grammar=True
    )


def create_stub_module(inference_state, grammar, python_value_set,
                       stub_module_node, file_io, import_names):
    if import_names == ('typing',):
        module_cls = TypingModuleWrapper
    else:
        module_cls = StubModuleValue
    file_name = os.path.basename(file_io.path)
    stub_module_value = module_cls(
        python_value_set, inference_state, stub_module_node,
        file_io=file_io,
        string_names=import_names,
        # The code was loaded with latest_grammar, so use
        # that.
        code_lines=get_cached_code_lines(grammar, file_io.path),
        is_package=file_name == '__init__.pyi',
    )
    return stub_module_value

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\completion\transformation.py ===
"""
Translation logic for anthropic's `/v1/complete` endpoint

Litellm provider slug: `anthropic_text/<model_name>`
"""

import json
import time
from typing import AsyncIterator, Dict, Iterator, List, Optional, Union

import httpx

import litellm
from litellm.constants import DEFAULT_MAX_TOKENS
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.chat.transformation import (
    BaseConfig,
    BaseLLMException,
    LiteLLMLoggingObj,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    GenericStreamingChunk,
    ModelResponse,
    Usage,
)


class AnthropicTextError(BaseLLMException):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url="https://api.anthropic.com/v1/complete"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            request=self.request,
            response=self.response,
        )  # Call the base class constructor with the parameters it needs


class AnthropicTextConfig(BaseConfig):
    """
    Reference: https://docs.anthropic.com/claude/reference/complete_post

    to pass metadata to anthropic, it's {"user_id": "any-relevant-information"}
    """

    max_tokens_to_sample: Optional[
        int
    ] = litellm.max_tokens  # anthropic requires a default
    stop_sequences: Optional[list] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    top_k: Optional[int] = None
    metadata: Optional[dict] = None

    def __init__(
        self,
        max_tokens_to_sample: Optional[
            int
        ] = DEFAULT_MAX_TOKENS,  # anthropic requires a default
        stop_sequences: Optional[list] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        top_k: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    # makes headers for API call
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
        if api_key is None:
            raise ValueError(
                "Missing Anthropic API Key - A call is being made to anthropic but no key is set either in the environment variables or via params"
            )
        _headers = {
            "accept": "application/json",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-api-key": api_key,
        }
        headers.update(_headers)
        return headers

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        prompt = self._get_anthropic_text_prompt_from_messages(
            messages=messages, model=model
        )
        ## Load Config
        config = litellm.AnthropicTextConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        data = {
            "model": model,
            "prompt": prompt,
            **optional_params,
        }

        return data

    def get_supported_openai_params(self, model: str):
        """
        Anthropic /complete API Ref: https://docs.anthropic.com/en/api/complete
        """
        return [
            "stream",
            "max_tokens",
            "max_completion_tokens",
            "stop",
            "temperature",
            "top_p",
            "extra_headers",
            "user",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        Follows the same logic as the AnthropicConfig.map_openai_params method (which is the Anthropic /messages API)

        Note: the only difference is in the get supported openai params method between the AnthropicConfig and AnthropicTextConfig
        API Ref: https://docs.anthropic.com/en/api/complete
        """
        for param, value in non_default_params.items():
            if param == "max_tokens":
                optional_params["max_tokens_to_sample"] = value
            if param == "max_completion_tokens":
                optional_params["max_tokens_to_sample"] = value
            if param == "stream" and value is True:
                optional_params["stream"] = value
            if param == "stop" and (isinstance(value, str) or isinstance(value, list)):
                _value = litellm.AnthropicConfig()._map_stop_sequences(value)
                if _value is not None:
                    optional_params["stop_sequences"] = _value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "user":
                optional_params["metadata"] = {"user_id": value}

        return optional_params

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            completion_response = raw_response.json()
        except Exception:
            raise AnthropicTextError(
                message=raw_response.text, status_code=raw_response.status_code
            )
        prompt = self._get_anthropic_text_prompt_from_messages(
            messages=messages, model=model
        )
        if "error" in completion_response:
            raise AnthropicTextError(
                message=str(completion_response["error"]),
                status_code=raw_response.status_code,
            )
        else:
            if len(completion_response["completion"]) > 0:
                model_response.choices[0].message.content = completion_response[  # type: ignore
                    "completion"
                ]
            model_response.choices[0].finish_reason = completion_response["stop_reason"]

        ## CALCULATING USAGE
        prompt_tokens = len(
            encoding.encode(prompt)
        )  ##[TODO] use the anthropic tokenizer here
        completion_tokens = len(
            encoding.encode(model_response["choices"][0]["message"].get("content", ""))
        )  ##[TODO] use the anthropic tokenizer here

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        setattr(model_response, "usage", usage)
        return model_response

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, httpx.Headers]
    ) -> BaseLLMException:
        return AnthropicTextError(
            status_code=status_code,
            message=error_message,
        )

    @staticmethod
    def _is_anthropic_text_model(model: str) -> bool:
        return model == "claude-2" or model == "claude-instant-1"

    def _get_anthropic_text_prompt_from_messages(
        self, messages: List[AllMessageValues], model: str
    ) -> str:
        custom_prompt_dict = litellm.custom_prompt_dict
        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details["roles"],
                initial_prompt_value=model_prompt_details["initial_prompt_value"],
                final_prompt_value=model_prompt_details["final_prompt_value"],
                messages=messages,
            )
        else:
            prompt = prompt_factory(
                model=model, messages=messages, custom_llm_provider="anthropic"
            )

        return str(prompt)

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return AnthropicTextCompletionResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class AnthropicTextCompletionResponseIterator(BaseModelResponseIterator):
    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None
            provider_specific_fields = None
            index = int(chunk.get("index", 0))
            _chunk_text = chunk.get("completion", None)
            if _chunk_text is not None and isinstance(_chunk_text, str):
                text = _chunk_text
            finish_reason = chunk.get("stop_reason", None)
            if finish_reason is not None:
                is_finished = True
            returned_chunk = GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=index,
                provider_specific_fields=provider_specific_fields,
            )

            return returned_chunk

        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\session_update_event_param.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypeAlias, TypedDict

__all__ = [
    "SessionUpdateEventParam",
    "Session",
    "SessionClientSecret",
    "SessionClientSecretExpiresAt",
    "SessionInputAudioNoiseReduction",
    "SessionInputAudioTranscription",
    "SessionTool",
    "SessionTracing",
    "SessionTracingTracingConfiguration",
    "SessionTurnDetection",
]


class SessionClientSecretExpiresAt(TypedDict, total=False):
    anchor: Literal["created_at"]
    """The anchor point for the ephemeral token expiration.

    Only `created_at` is currently supported.
    """

    seconds: int
    """The number of seconds from the anchor point to the expiration.

    Select a value between `10` and `7200`.
    """


class SessionClientSecret(TypedDict, total=False):
    expires_at: SessionClientSecretExpiresAt
    """Configuration for the ephemeral token expiration."""


class SessionInputAudioNoiseReduction(TypedDict, total=False):
    type: Literal["near_field", "far_field"]
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class SessionInputAudioTranscription(TypedDict, total=False):
    language: str
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: str
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: str
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class SessionTool(TypedDict, total=False):
    description: str
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: str
    """The name of the function."""

    parameters: object
    """Parameters of the function in JSON Schema."""

    type: Literal["function"]
    """The type of the tool, i.e. `function`."""


class SessionTracingTracingConfiguration(TypedDict, total=False):
    group_id: str
    """
    The group id to attach to this trace to enable filtering and grouping in the
    traces dashboard.
    """

    metadata: object
    """
    The arbitrary metadata to attach to this trace to enable filtering in the traces
    dashboard.
    """

    workflow_name: str
    """The name of the workflow to attach to this trace.

    This is used to name the trace in the traces dashboard.
    """


SessionTracing: TypeAlias = Union[Literal["auto"], SessionTracingTracingConfiguration]


class SessionTurnDetection(TypedDict, total=False):
    create_response: bool
    """
    Whether or not to automatically generate a response when a VAD stop event
    occurs.
    """

    eagerness: Literal["low", "medium", "high", "auto"]
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: bool
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs.
    """

    prefix_padding_ms: int
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: int
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: float
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Literal["server_vad", "semantic_vad"]
    """Type of turn detection."""


class Session(TypedDict, total=False):
    client_secret: SessionClientSecret
    """Configuration options for the generated client secret."""

    input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: SessionInputAudioNoiseReduction
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: SessionInputAudioTranscription
    """
    Configuration for input audio transcription, defaults to off and can be set to
    `null` to turn off once on. Input audio transcription is not native to the
    model, since the model consumes audio directly. Transcription runs
    asynchronously through
    [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
    and should be treated as guidance of input audio content rather than precisely
    what the model heard. The client can optionally set the language and prompt for
    transcription, these offer additional guidance to the transcription service.
    """

    instructions: str
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"]]
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    modalities: List[Literal["text", "audio"]]
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    model: Literal[
        "gpt-4o-realtime-preview",
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview-2025-06-03",
        "gpt-4o-mini-realtime-preview",
        "gpt-4o-mini-realtime-preview-2024-12-17",
    ]
    """The Realtime model used for this session."""

    output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"]
    """The format of output audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, output audio is
    sampled at a rate of 24kHz.
    """

    speed: float
    """The speed of the model's spoken response.

    1.0 is the default speed. 0.25 is the minimum speed. 1.5 is the maximum speed.
    This value can only be changed in between model turns, not while a response is
    in progress.
    """

    temperature: float
    """Sampling temperature for the model, limited to [0.6, 1.2].

    For audio models a temperature of 0.8 is highly recommended for best
    performance.
    """

    tool_choice: str
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function.
    """

    tools: Iterable[SessionTool]
    """Tools (functions) available to the model."""

    tracing: SessionTracing
    """Configuration options for tracing.

    Set to null to disable tracing. Once tracing is enabled for a session, the
    configuration cannot be modified.

    `auto` will create a trace for the session with default values for the workflow
    name, group id, and metadata.
    """

    turn_detection: SessionTurnDetection
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """

    voice: Union[
        str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
    ]
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and `verse`.
    """


class SessionUpdateEventParam(TypedDict, total=False):
    session: Required[Session]
    """Realtime session object configuration."""

    type: Required[Literal["session.update"]]
    """The event type, must be `session.update`."""

    event_id: str
    """Optional client-generated ID used to identify this event."""

# === NexusCore/openenv\Lib\site-packages\trio\_core\_traps.py ===
"""These are the only functions that ever yield back to the task runner."""

from __future__ import annotations

import enum
import types

# Jedi gets mad in test_static_tool_sees_class_members if we use collections Callable
from typing import TYPE_CHECKING, Any, Callable, NoReturn, Union, cast

import attrs
import outcome

from . import _run

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator

    from typing_extensions import TypeAlias

    from ._run import Task

RaiseCancelT: TypeAlias = Callable[[], NoReturn]


# This class object is used as a singleton.
# Not exported in the trio._core namespace, but imported directly by _run.
class CancelShieldedCheckpoint:
    __slots__ = ()


# Not exported in the trio._core namespace, but imported directly by _run.
@attrs.frozen(slots=False)
class WaitTaskRescheduled:
    abort_func: Callable[[RaiseCancelT], Abort]


# Not exported in the trio._core namespace, but imported directly by _run.
@attrs.frozen(slots=False)
class PermanentlyDetachCoroutineObject:
    final_outcome: outcome.Outcome[object]


MessageType: TypeAlias = Union[
    type[CancelShieldedCheckpoint],
    WaitTaskRescheduled,
    PermanentlyDetachCoroutineObject,
    object,
]


# Helper for the bottommost 'yield'. You can't use 'yield' inside an async
# function, but you can inside a generator, and if you decorate your generator
# with @types.coroutine, then it's even awaitable. However, it's still not a
# real async function: in particular, it isn't recognized by
# inspect.iscoroutinefunction, and it doesn't trigger the unawaited coroutine
# tracking machinery. Since our traps are public APIs, we make them real async
# functions, and then this helper takes care of the actual yield:
@types.coroutine
def _real_async_yield(
    obj: MessageType,
) -> Generator[MessageType, None, None]:
    return (yield obj)


# Real yield value is from trio's main loop, but type checkers can't
# understand that, so we cast it to make type checkers understand.
_async_yield = cast(
    "Callable[[MessageType], Awaitable[outcome.Outcome[object]]]",
    _real_async_yield,
)


async def cancel_shielded_checkpoint() -> None:
    """Introduce a schedule point, but not a cancel point.

    This is *not* a :ref:`checkpoint <checkpoints>`, but it is half of a
    checkpoint, and when combined with :func:`checkpoint_if_cancelled` it can
    make a full checkpoint.

    Equivalent to (but potentially more efficient than)::

        with trio.CancelScope(shield=True):
            await trio.lowlevel.checkpoint()

    """
    (await _async_yield(CancelShieldedCheckpoint)).unwrap()


# Return values for abort functions
class Abort(enum.Enum):
    """:class:`enum.Enum` used as the return value from abort functions.

    See :func:`wait_task_rescheduled` for details.

    .. data:: SUCCEEDED
              FAILED

    """

    SUCCEEDED = 1
    FAILED = 2


# Should always return the type a Task "expects", unless you willfully reschedule it
# with a bad value.
async def wait_task_rescheduled(  # type: ignore[explicit-any]
    abort_func: Callable[[RaiseCancelT], Abort],
) -> Any:
    """Put the current task to sleep, with cancellation support.

    This is the lowest-level API for blocking in Trio. Every time a
    :class:`~trio.lowlevel.Task` blocks, it does so by calling this function
    (usually indirectly via some higher-level API).

    This is a tricky interface with no guard rails. If you can use
    :class:`ParkingLot` or the built-in I/O wait functions instead, then you
    should.

    Generally the way it works is that before calling this function, you make
    arrangements for "someone" to call :func:`reschedule` on the current task
    at some later point.

    Then you call :func:`wait_task_rescheduled`, passing in ``abort_func``, an
    "abort callback".

    (Terminology: in Trio, "aborting" is the process of attempting to
    interrupt a blocked task to deliver a cancellation.)

    There are two possibilities for what happens next:

    1. "Someone" calls :func:`reschedule` on the current task, and
       :func:`wait_task_rescheduled` returns or raises whatever value or error
       was passed to :func:`reschedule`.

    2. The call's context transitions to a cancelled state (e.g. due to a
       timeout expiring). When this happens, the ``abort_func`` is called. Its
       interface looks like::

           def abort_func(raise_cancel):
               ...
               return trio.lowlevel.Abort.SUCCEEDED  # or FAILED

       It should attempt to clean up any state associated with this call, and
       in particular, arrange that :func:`reschedule` will *not* be called
       later. If (and only if!) it is successful, then it should return
       :data:`Abort.SUCCEEDED`, in which case the task will automatically be
       rescheduled with an appropriate :exc:`~trio.Cancelled` error.

       Otherwise, it should return :data:`Abort.FAILED`. This means that the
       task can't be cancelled at this time, and still has to make sure that
       "someone" eventually calls :func:`reschedule`.

       At that point there are again two possibilities. You can simply ignore
       the cancellation altogether: wait for the operation to complete and
       then reschedule and continue as normal. (For example, this is what
       :func:`trio.to_thread.run_sync` does if cancellation is disabled.)
       The other possibility is that the ``abort_func`` does succeed in
       cancelling the operation, but for some reason isn't able to report that
       right away. (Example: on Windows, it's possible to request that an
       async ("overlapped") I/O operation be cancelled, but this request is
       *also* asynchronous – you don't find out until later whether the
       operation was actually cancelled or not.)  To report a delayed
       cancellation, then you should reschedule the task yourself, and call
       the ``raise_cancel`` callback passed to ``abort_func`` to raise a
       :exc:`~trio.Cancelled` (or possibly :exc:`KeyboardInterrupt`) exception
       into this task. Either of the approaches sketched below can work::

          # Option 1:
          # Catch the exception from raise_cancel and inject it into the task.
          # (This is what Trio does automatically for you if you return
          # Abort.SUCCEEDED.)
          trio.lowlevel.reschedule(task, outcome.capture(raise_cancel))

          # Option 2:
          # wait to be woken by "someone", and then decide whether to raise
          # the error from inside the task.
          outer_raise_cancel = None
          def abort(inner_raise_cancel):
              nonlocal outer_raise_cancel
              outer_raise_cancel = inner_raise_cancel
              TRY_TO_CANCEL_OPERATION()
              return trio.lowlevel.Abort.FAILED
          await wait_task_rescheduled(abort)
          if OPERATION_WAS_SUCCESSFULLY_CANCELLED:
              # raises the error
              outer_raise_cancel()

       In any case it's guaranteed that we only call the ``abort_func`` at most
       once per call to :func:`wait_task_rescheduled`.

    Sometimes, it's useful to be able to share some mutable sleep-related data
    between the sleeping task, the abort function, and the waking task. You
    can use the sleeping task's :data:`~Task.custom_sleep_data` attribute to
    store this data, and Trio won't touch it, except to make sure that it gets
    cleared when the task is rescheduled.

    .. warning::

       If your ``abort_func`` raises an error, or returns any value other than
       :data:`Abort.SUCCEEDED` or :data:`Abort.FAILED`, then Trio will crash
       violently. Be careful! Similarly, it is entirely possible to deadlock a
       Trio program by failing to reschedule a blocked task, or cause havoc by
       calling :func:`reschedule` too many times. Remember what we said up
       above about how you should use a higher-level API if at all possible?

    """
    return (await _async_yield(WaitTaskRescheduled(abort_func))).unwrap()


async def permanently_detach_coroutine_object(
    final_outcome: outcome.Outcome[object],
) -> object:
    """Permanently detach the current task from the Trio scheduler.

    Normally, a Trio task doesn't exit until its coroutine object exits. When
    you call this function, Trio acts like the coroutine object just exited
    and the task terminates with the given outcome. This is useful if you want
    to permanently switch the coroutine object over to a different coroutine
    runner.

    When the calling coroutine enters this function it's running under Trio,
    and when the function returns it's running under the foreign coroutine
    runner.

    You should make sure that the coroutine object has released any
    Trio-specific resources it has acquired (e.g. nurseries).

    Args:
      final_outcome (outcome.Outcome): Trio acts as if the current task exited
          with the given return value or exception.

    Returns or raises whatever value or exception the new coroutine runner
    uses to resume the coroutine.

    """
    if _run.current_task().child_nurseries:
        raise RuntimeError(
            "can't permanently detach a coroutine object with open nurseries",
        )
    return await _async_yield(PermanentlyDetachCoroutineObject(final_outcome))


async def temporarily_detach_coroutine_object(
    abort_func: Callable[[RaiseCancelT], Abort],
) -> object:
    """Temporarily detach the current coroutine object from the Trio
    scheduler.

    When the calling coroutine enters this function it's running under Trio,
    and when the function returns it's running under the foreign coroutine
    runner.

    The Trio :class:`Task` will continue to exist, but will be suspended until
    you use :func:`reattach_detached_coroutine_object` to resume it. In the
    mean time, you can use another coroutine runner to schedule the coroutine
    object. In fact, you have to – the function doesn't return until the
    coroutine is advanced from outside.

    Note that you'll need to save the current :class:`Task` object to later
    resume; you can retrieve it with :func:`current_task`. You can also use
    this :class:`Task` object to retrieve the coroutine object – see
    :data:`Task.coro`.

    Args:
      abort_func: Same as for :func:`wait_task_rescheduled`, except that it
          must return :data:`Abort.FAILED`. (If it returned
          :data:`Abort.SUCCEEDED`, then Trio would attempt to reschedule the
          detached task directly without going through
          :func:`reattach_detached_coroutine_object`, which would be bad.)
          Your ``abort_func`` should still arrange for whatever the coroutine
          object is doing to be cancelled, and then reattach to Trio and call
          the ``raise_cancel`` callback, if possible.

    Returns or raises whatever value or exception the new coroutine runner
    uses to resume the coroutine.

    """
    return await _async_yield(WaitTaskRescheduled(abort_func))


async def reattach_detached_coroutine_object(task: Task, yield_value: object) -> None:
    """Reattach a coroutine object that was detached using
    :func:`temporarily_detach_coroutine_object`.

    When the calling coroutine enters this function it's running under the
    foreign coroutine runner, and when the function returns it's running under
    Trio.

    This must be called from inside the coroutine being resumed, and yields
    whatever value you pass in. (Presumably you'll pass a value that will
    cause the current coroutine runner to stop scheduling this task.) Then the
    coroutine is resumed by the Trio scheduler at the next opportunity.

    Args:
      task (Task): The Trio task object that the current coroutine was
          detached from.
      yield_value (object): The object to yield to the current coroutine
          runner.

    """
    # This is a kind of crude check – in particular, it can fail if the
    # passed-in task is where the coroutine *runner* is running. But this is
    # an experts-only interface, and there's no easy way to do a more accurate
    # check, so I guess that's OK.
    if not task.coro.cr_running:
        raise RuntimeError("given task does not match calling coroutine")
    _run.reschedule(task, outcome.Value("reattaching"))
    value = await _async_yield(yield_value)
    assert value == outcome.Value("reattaching")

# === NexusCore/openenv\Lib\site-packages\zmq\devices\basedevice.py ===
"""Classes for running 0MQ Devices in the background."""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

import time
from multiprocessing import Process
from threading import Thread
from typing import Any, Callable, List, Optional, Tuple

import zmq
from zmq import ENOTSOCK, ETERM, PUSH, QUEUE, Context, ZMQBindError, ZMQError, proxy


class Device:
    """A 0MQ Device to be run in the background.

    You do not pass Socket instances to this, but rather Socket types::

        Device(device_type, in_socket_type, out_socket_type)

    For instance::

        dev = Device(zmq.QUEUE, zmq.DEALER, zmq.ROUTER)

    Similar to zmq.device, but socket types instead of sockets themselves are
    passed, and the sockets are created in the work thread, to avoid issues
    with thread safety. As a result, additional bind_{in|out} and
    connect_{in|out} methods and setsockopt_{in|out} allow users to specify
    connections for the sockets.

    Parameters
    ----------
    device_type : int
        The 0MQ Device type
    {in|out}_type : int
        zmq socket types, to be passed later to context.socket(). e.g.
        zmq.PUB, zmq.SUB, zmq.REQ. If out_type is < 0, then in_socket is used
        for both in_socket and out_socket.

    Methods
    -------
    bind_{in_out}(iface)
        passthrough for ``{in|out}_socket.bind(iface)``, to be called in the thread
    connect_{in_out}(iface)
        passthrough for ``{in|out}_socket.connect(iface)``, to be called in the
        thread
    setsockopt_{in_out}(opt,value)
        passthrough for ``{in|out}_socket.setsockopt(opt, value)``, to be called in
        the thread

    Attributes
    ----------
    daemon : bool
        sets whether the thread should be run as a daemon
        Default is true, because if it is false, the thread will not
        exit unless it is killed
    context_factory : callable
        This is a class attribute.
        Function for creating the Context. This will be Context.instance
        in ThreadDevices, and Context in ProcessDevices.  The only reason
        it is not instance() in ProcessDevices is that there may be a stale
        Context instance already initialized, and the forked environment
        should *never* try to use it.
    """

    context_factory: Callable[[], zmq.Context] = Context.instance
    """Callable that returns a context. Typically either Context.instance or Context,
    depending on whether the device should share the global instance or not.
    """

    daemon: bool
    device_type: int
    in_type: int
    out_type: int

    _in_binds: List[str]
    _in_connects: List[str]
    _in_sockopts: List[Tuple[int, Any]]
    _out_binds: List[str]
    _out_connects: List[str]
    _out_sockopts: List[Tuple[int, Any]]
    _random_addrs: List[str]
    _sockets: List[zmq.Socket]

    def __init__(
        self,
        device_type: int = QUEUE,
        in_type: Optional[int] = None,
        out_type: Optional[int] = None,
    ) -> None:
        self.device_type = device_type
        if in_type is None:
            raise TypeError("in_type must be specified")
        if out_type is None:
            raise TypeError("out_type must be specified")
        self.in_type = in_type
        self.out_type = out_type
        self._in_binds = []
        self._in_connects = []
        self._in_sockopts = []
        self._out_binds = []
        self._out_connects = []
        self._out_sockopts = []
        self._random_addrs = []
        self.daemon = True
        self.done = False
        self._sockets = []

    def bind_in(self, addr: str) -> None:
        """Enqueue ZMQ address for binding on in_socket.

        See zmq.Socket.bind for details.
        """
        self._in_binds.append(addr)

    def bind_in_to_random_port(self, addr: str, *args, **kwargs) -> int:
        """Enqueue a random port on the given interface for binding on
        in_socket.

        See zmq.Socket.bind_to_random_port for details.

        .. versionadded:: 18.0
        """
        port = self._reserve_random_port(addr, *args, **kwargs)

        self.bind_in(f'{addr}:{port}')

        return port

    def connect_in(self, addr: str) -> None:
        """Enqueue ZMQ address for connecting on in_socket.

        See zmq.Socket.connect for details.
        """
        self._in_connects.append(addr)

    def setsockopt_in(self, opt: int, value: Any) -> None:
        """Enqueue setsockopt(opt, value) for in_socket

        See zmq.Socket.setsockopt for details.
        """
        self._in_sockopts.append((opt, value))

    def bind_out(self, addr: str) -> None:
        """Enqueue ZMQ address for binding on out_socket.

        See zmq.Socket.bind for details.
        """
        self._out_binds.append(addr)

    def bind_out_to_random_port(self, addr: str, *args, **kwargs) -> int:
        """Enqueue a random port on the given interface for binding on
        out_socket.

        See zmq.Socket.bind_to_random_port for details.

        .. versionadded:: 18.0
        """
        port = self._reserve_random_port(addr, *args, **kwargs)

        self.bind_out(f'{addr}:{port}')

        return port

    def connect_out(self, addr: str):
        """Enqueue ZMQ address for connecting on out_socket.

        See zmq.Socket.connect for details.
        """
        self._out_connects.append(addr)

    def setsockopt_out(self, opt: int, value: Any):
        """Enqueue setsockopt(opt, value) for out_socket

        See zmq.Socket.setsockopt for details.
        """
        self._out_sockopts.append((opt, value))

    def _reserve_random_port(self, addr: str, *args, **kwargs) -> int:
        with Context() as ctx:
            with ctx.socket(PUSH) as binder:
                for i in range(5):
                    port = binder.bind_to_random_port(addr, *args, **kwargs)

                    new_addr = f'{addr}:{port}'

                    if new_addr in self._random_addrs:
                        continue
                    else:
                        break
                else:
                    raise ZMQBindError("Could not reserve random port.")

                self._random_addrs.append(new_addr)

        return port

    def _setup_sockets(self) -> Tuple[zmq.Socket, zmq.Socket]:
        ctx: zmq.Context[zmq.Socket] = self.context_factory()  # type: ignore
        self._context = ctx

        # create the sockets
        ins = ctx.socket(self.in_type)
        self._sockets.append(ins)
        if self.out_type < 0:
            outs = ins
        else:
            outs = ctx.socket(self.out_type)
            self._sockets.append(outs)

        # set sockopts (must be done first, in case of zmq.IDENTITY)
        for opt, value in self._in_sockopts:
            ins.setsockopt(opt, value)
        for opt, value in self._out_sockopts:
            outs.setsockopt(opt, value)

        for iface in self._in_binds:
            ins.bind(iface)
        for iface in self._out_binds:
            outs.bind(iface)

        for iface in self._in_connects:
            ins.connect(iface)
        for iface in self._out_connects:
            outs.connect(iface)

        return ins, outs

    def run_device(self) -> None:
        """The runner method.

        Do not call me directly, instead call ``self.start()``, just like a Thread.
        """
        ins, outs = self._setup_sockets()
        proxy(ins, outs)

    def _close_sockets(self):
        """Cleanup sockets we created"""
        for s in self._sockets:
            if s and not s.closed:
                s.close()

    def run(self) -> None:
        """wrap run_device in try/catch ETERM"""
        try:
            self.run_device()
        except ZMQError as e:
            if e.errno in {ETERM, ENOTSOCK}:
                # silence TERM, ENOTSOCK errors, because this should be a clean shutdown
                pass
            else:
                raise
        finally:
            self.done = True
            self._close_sockets()

    def start(self) -> None:
        """Start the device. Override me in subclass for other launchers."""
        return self.run()

    def join(self, timeout: Optional[float] = None) -> None:
        """wait for me to finish, like Thread.join.

        Reimplemented appropriately by subclasses."""
        tic = time.monotonic()
        toc = tic
        while not self.done and not (timeout is not None and toc - tic > timeout):
            time.sleep(0.001)
            toc = time.monotonic()


class BackgroundDevice(Device):
    """Base class for launching Devices in background processes and threads."""

    launcher: Any = None
    _launch_class: Any = None

    def start(self) -> None:
        self.launcher = self._launch_class(target=self.run)
        self.launcher.daemon = self.daemon
        return self.launcher.start()

    def join(self, timeout: Optional[float] = None) -> None:
        return self.launcher.join(timeout=timeout)


class ThreadDevice(BackgroundDevice):
    """A Device that will be run in a background Thread.

    See Device for details.
    """

    _launch_class = Thread


class ProcessDevice(BackgroundDevice):
    """A Device that will be run in a background Process.

    See Device for details.
    """

    _launch_class = Process
    context_factory = Context
    """Callable that returns a context. Typically either Context.instance or Context,
    depending on whether the device should share the global instance or not.
    """


__all__ = ['Device', 'ThreadDevice', 'ProcessDevice']

# === NexusCore/tools\code_export_gui.py ===
"""code_export_gui.py — importance‑aware export (ルール + 静的メタ解析)
Fully expanded script – 2025‑07‑23 rev‑6  (multi‑root + combine fix)
────────────────────────────────────────────────────────
* Layer‑① ルールベース（拡張子・パス・サイズ）
* Layer‑② 静的メタ解析（import 結合度 + LOC）
* **複数フォルダ選択** OK
* **combine_py バグ修正** ← ファイルが異なる root に属するとき `relative_to()` で ValueError が出ていた問題を解消
* exports/ 除外／Windows Path Limit 対策／99 MB 上限／Cancel／Progress はそのまま
"""
from __future__ import annotations
import ast
import datetime
import fnmatch
import os
import traceback
import zipfile
from collections import defaultdict
from math import log2
from pathlib import Path
from threading import Event
from typing import List, Tuple, Dict, Set

import gradio as gr

try:
    import networkx as nx  # optional – centrality calc
except ImportError:
    nx = None

# === CONFIG ===
FILE_TYPES: Tuple[str, ...] = (
    ".py", ".ipynb", ".md", ".txt", "package.json", ".json", ".yml", ".yaml", ".toml",
)
DEFAULT_IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build", ".idea", ".vscode",
}
MAX_LINES_PER_FILE = 10_000
TOTAL_SIZE_CAP_MB = 99
WIN_PATH_CAP = 250  # safe margin under MAX_PATH 260
EXPORT_ROOT = Path("./exports").resolve()
EXPORT_ROOT.mkdir(exist_ok=True)
DEFAULT_IGNORED_DIRS.add(EXPORT_ROOT.name)

EXT_WEIGHT = {".py": 3, ".ipynb": 2, ".md": 1}
PATH_WEIGHT = {"src": 2, "app": 2, "lib": 1, "tests": -1, "docs": -1}

stop_event = Event()

# ───────────────────────────────────────── gitignore

def load_gitignore(root: Path) -> Set[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return set()
    return {
        line.strip()
        for line in gi.read_text("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

def path_is_ignored(path: Path, root: Path, patterns: Set[str]) -> bool:
    rel = path.relative_to(root)
    for pat in patterns:
        if pat.endswith("/") and fnmatch.fnmatch(f"{rel}/", pat):
            return True
        if fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(path.name, pat):
            return True
    return False

# ───────────────────────────────────────── static analysis

def build_import_map(root: Path, py_files: List[Path]) -> Dict[Path, Set[Path]]:
    module_of = {".".join(p.relative_to(root).with_suffix("").parts): p for p in py_files}
    mapping: Dict[Path, Set[Path]] = defaultdict(set)
    for pf in py_files:
        try:
            tree = ast.parse(pf.read_text("utf-8", "ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    tgt = module_of.get(a.name.split(".")[0])
                    if tgt:
                        mapping[pf].add(tgt)
            elif isinstance(node, ast.ImportFrom) and node.module:
                tgt = module_of.get(node.module.split(".")[0])
                if tgt:
                    mapping[pf].add(tgt)
    return mapping

def degree_centrality(mapping: Dict[Path, Set[Path]]) -> Dict[Path, float]:
    if not nx:
        return {k: len(v) for k, v in mapping.items()}
    g = nx.DiGraph()
    for s, tgts in mapping.items():
        for t in tgts:
            g.add_edge(s, t)
    return nx.degree_centrality(g)

# ───────────────────────────────────────── scoring helpers

def loc_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
    except Exception:
        return 0

def file_score(path: Path, root: Path, cent: Dict[Path, float]) -> float:
    score = EXT_WEIGHT.get(path.suffix.lower(), 0)
    score += next((PATH_WEIGHT[p] for p in path.parts if p in PATH_WEIGHT), 0)
    score += cent.get(path, 0) * 5
    lines = loc_count(path)
    if lines:
        score += min(log2(lines + 1) / 5, 3)
    return score

# ───────────────────────────────────────── file collection

def collect_files(root: Path, max_single_mb: int, progress: gr.Progress) -> List[Path]:
    patterns = load_gitignore(root)
    cap_total = TOTAL_SIZE_CAP_MB * 1024 * 1024
    cap_single = max_single_mb * 1024 * 1024

    cand: List[Path] = []
    entries = list(root.rglob("*"))
    for p in entries:
        if stop_event.is_set():
            break
        if any(p.is_relative_to(root / ig) for ig in DEFAULT_IGNORED_DIRS):
            continue
        if path_is_ignored(p, root, patterns):
            continue
        if p.is_file() and p.suffix.lower() in FILE_TYPES and p.stat().st_size <= cap_single:
            if os.name == "nt" and len(str(EXPORT_ROOT / p.relative_to(root))) > WIN_PATH_CAP:
                continue
            cand.append(p)

    py = [p for p in cand if p.suffix == ".py"]
    cent = degree_centrality(build_import_map(root, py))
    cand.sort(key=lambda p: file_score(p, root, cent), reverse=True)

    sel: List[Path] = []
    total = 0
    for i, p in enumerate(cand, 1):
        if stop_event.is_set():
            break
        progress(0.3 * i / len(cand))
        size = p.stat().st_size
        if total + size > cap_total:
            continue
        sel.append(p)
        total += size
    return sel

# ───────────────────────────────────────── helpers for export

def make_tree(root: Path, files: List[Path]) -> str:
    tree_dict: Dict[str, Dict] = {}
    for f in files:
        node = tree_dict
        for part in f.relative_to(root).parts:
            node = node.setdefault(part, {})
    lines = [f"./ ({root})"]
    def dfs(d: Dict[str, Dict], pref: str = ""):
        for i, k in enumerate(sorted(d)):
            conn = "└── " if i == len(d) - 1 else "├── "
            lines.append(f"{pref}{conn}{k}")
            if d[k]:
                dfs(d[k], pref + ("    " if i == len(d) - 1 else "│   "))
    dfs(tree_dict)
    return "\n".join(lines)

def def_class_only(path: Path) -> List[str]:
    return [
        f"{path.name}: {ln.strip()}"
        for ln in path.read_text("utf-8", "ignore").splitlines()
        if ln.lstrip().startswith(("def ", "class "))
    ]

# >>> FIXED: combine_py now handles files from multiple roots safely <<<

def combine_py(py_files: List[Tuple[Path, Path]], out_dir: Path):
    """py_files: list of (root, file)"""
    buf: List[str] = []
    idx = 1
    for rt, pf in py_files:
        try:
            rel = pf.relative_to(rt)
        except ValueError:
            rel = pf.name  # fallback
        buf.append(f"\n# === {rt.name}/{rel} ===")
        buf.extend(pf.read_text("utf-8", "ignore").splitlines())
        if len(buf) >= MAX_LINES_PER_FILE:
            (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8")
            buf, idx = [], idx + 1
    if buf:
        (out_dir / f"combined_{idx}.py").write_text("\n".join(buf), "utf-8")

# ───────────────────────────────────────── project export (multi‑root)

def export_multi(roots: List[Path], max_single_mb: int, progress: gr.Progress) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session = EXPORT_ROOT / f"export_{ts}"
    session.mkdir(parents=True, exist_ok=True)

    all_files: List[Tuple[Path, Path]] = []  # (root, file)
    for idx, rt in enumerate(roots, 1):
        sub_prog = gr.Progress(track_tqdm=False)
        sub_files = collect_files(rt, max_single_mb, sub_prog)
        all_files.extend([(rt, f) for f in sub_files])
        progress(0.2 * idx / len(roots))

    if stop_event.is_set() or not all_files:
        raise RuntimeError("Cancelled or no files selected")

    tree_sections: List[str] = []
    summary_lines: List[str] = []
    py_files: List[Tuple[Path, Path]] = []

    for rt, f in all_files:
        dst = session / "source_code" / rt.name / f.relative_to(rt)
        if os.name == "nt" and len(str(dst)) > WIN_PATH_CAP:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            dst.write_bytes(f.read_bytes())
        except OSError:
            continue
        if f.suffix == ".py":
            summary_lines.extend(def_class_only(f))
            py_files.append((rt, f))

    # structure texts
    for rt in roots:
        tree_sections.append(make_tree(rt, [f for r, f in all_files if r == rt]))
        tree_sections.append("")
    (session / "project_structure.txt").write_text("\n".join(tree_sections), "utf-8")
    (session / "summary_def_class.txt").write_text("\n".join(summary_lines), "utf-8")
    combine_py(py_files, session)

    zip_path = EXPORT_ROOT / f"source_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in session.rglob("*"):
            zf.write(f, arcname=f.relative_to(session))
    progress(1)
    return zip_path

# ───────────────────────────────────────── gradio callbacks

def run_export(roots_str: str, max_mb: int, cancelling: bool, progress=gr.Progress(track_tqdm=False)):
    if cancelling:
        return None, "⚠️ cancelling…", True
    stop_event.clear()
    roots = [Path(p.strip()).expanduser().resolve() for p in roots_str.splitlines() if p.strip()]
    if not roots:
        return None, "⚠️ select at least one folder", False
    try:
        zp = export_multi(roots, max_mb, progress)
        mb = zp.stat().st_size / (1024 * 1024)
        return str(zp), f"✅ Done: {mb:.1f} MB", False
    except Exception:
        return None, f"❌ {traceback.format_exc(limit=5)}", False

def cancel_export(_: bool):
    stop_event.set()
    return "⏹️ cancel signal", True


def browse_and_append(existing: str):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askdirectory(title="Select folder")
        root.destroy()
        if path:
            paths = existing.splitlines()
            if path not in paths:
                paths.append(path)
            return "\n".join(paths)
    except Exception:
        pass
    return existing

# ───────────────────────────────────────── UI
with gr.Blocks(title="Code Export (multi‑root)", css=".gr-button{min-width:6rem}") as demo:
    gr.Markdown("## 📦 Importance‑Aware Code Export (≤99 MB, multi‑root)")

    dirs_tb = gr.Textbox(label="Selected root directories (one per line)")
    browse_btn = gr.Button("📂 Browse & add")

    max_slider = gr.Slider(1, 50, value=10, step=1, label="Max single file size (MB)")

    with gr.Row():
        exp_btn = gr.Button("🚀 Export", variant="primary")
        cancel_btn = gr.Button("🛑 Cancel")

    zip_out = gr.File(label="ZIP")
    status = gr.Textbox(label="Status", lines=4)
    cancelling_state = gr.State(False)

    browse_btn.click(browse_and_append, inputs=[dirs_tb], outputs=[dirs_tb])
    exp_btn.click(run_export, inputs=[dirs_tb, max_slider, cancelling_state], outputs=[zip_out, status, cancelling_state])
    cancel_btn.click(cancel_export, inputs=[cancelling_state], outputs=[status, cancelling_state])

if __name__ == "__main__":
    demo.launch(inbrowser=True, allowed_paths=[str(EXPORT_ROOT)])

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\_palettes.py ===
from .palette import Palette


# Taken from https://en.wikipedia.org/wiki/ANSI_escape_code (Windows 10 column)
WINDOWS_PALETTE = Palette(
    [
        (12, 12, 12),
        (197, 15, 31),
        (19, 161, 14),
        (193, 156, 0),
        (0, 55, 218),
        (136, 23, 152),
        (58, 150, 221),
        (204, 204, 204),
        (118, 118, 118),
        (231, 72, 86),
        (22, 198, 12),
        (249, 241, 165),
        (59, 120, 255),
        (180, 0, 158),
        (97, 214, 214),
        (242, 242, 242),
    ]
)

# # The standard ansi colors (including bright variants)
STANDARD_PALETTE = Palette(
    [
        (0, 0, 0),
        (170, 0, 0),
        (0, 170, 0),
        (170, 85, 0),
        (0, 0, 170),
        (170, 0, 170),
        (0, 170, 170),
        (170, 170, 170),
        (85, 85, 85),
        (255, 85, 85),
        (85, 255, 85),
        (255, 255, 85),
        (85, 85, 255),
        (255, 85, 255),
        (85, 255, 255),
        (255, 255, 255),
    ]
)


# The 256 color palette
EIGHT_BIT_PALETTE = Palette(
    [
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
        (0, 0, 0),
        (0, 0, 95),
        (0, 0, 135),
        (0, 0, 175),
        (0, 0, 215),
        (0, 0, 255),
        (0, 95, 0),
        (0, 95, 95),
        (0, 95, 135),
        (0, 95, 175),
        (0, 95, 215),
        (0, 95, 255),
        (0, 135, 0),
        (0, 135, 95),
        (0, 135, 135),
        (0, 135, 175),
        (0, 135, 215),
        (0, 135, 255),
        (0, 175, 0),
        (0, 175, 95),
        (0, 175, 135),
        (0, 175, 175),
        (0, 175, 215),
        (0, 175, 255),
        (0, 215, 0),
        (0, 215, 95),
        (0, 215, 135),
        (0, 215, 175),
        (0, 215, 215),
        (0, 215, 255),
        (0, 255, 0),
        (0, 255, 95),
        (0, 255, 135),
        (0, 255, 175),
        (0, 255, 215),
        (0, 255, 255),
        (95, 0, 0),
        (95, 0, 95),
        (95, 0, 135),
        (95, 0, 175),
        (95, 0, 215),
        (95, 0, 255),
        (95, 95, 0),
        (95, 95, 95),
        (95, 95, 135),
        (95, 95, 175),
        (95, 95, 215),
        (95, 95, 255),
        (95, 135, 0),
        (95, 135, 95),
        (95, 135, 135),
        (95, 135, 175),
        (95, 135, 215),
        (95, 135, 255),
        (95, 175, 0),
        (95, 175, 95),
        (95, 175, 135),
        (95, 175, 175),
        (95, 175, 215),
        (95, 175, 255),
        (95, 215, 0),
        (95, 215, 95),
        (95, 215, 135),
        (95, 215, 175),
        (95, 215, 215),
        (95, 215, 255),
        (95, 255, 0),
        (95, 255, 95),
        (95, 255, 135),
        (95, 255, 175),
        (95, 255, 215),
        (95, 255, 255),
        (135, 0, 0),
        (135, 0, 95),
        (135, 0, 135),
        (135, 0, 175),
        (135, 0, 215),
        (135, 0, 255),
        (135, 95, 0),
        (135, 95, 95),
        (135, 95, 135),
        (135, 95, 175),
        (135, 95, 215),
        (135, 95, 255),
        (135, 135, 0),
        (135, 135, 95),
        (135, 135, 135),
        (135, 135, 175),
        (135, 135, 215),
        (135, 135, 255),
        (135, 175, 0),
        (135, 175, 95),
        (135, 175, 135),
        (135, 175, 175),
        (135, 175, 215),
        (135, 175, 255),
        (135, 215, 0),
        (135, 215, 95),
        (135, 215, 135),
        (135, 215, 175),
        (135, 215, 215),
        (135, 215, 255),
        (135, 255, 0),
        (135, 255, 95),
        (135, 255, 135),
        (135, 255, 175),
        (135, 255, 215),
        (135, 255, 255),
        (175, 0, 0),
        (175, 0, 95),
        (175, 0, 135),
        (175, 0, 175),
        (175, 0, 215),
        (175, 0, 255),
        (175, 95, 0),
        (175, 95, 95),
        (175, 95, 135),
        (175, 95, 175),
        (175, 95, 215),
        (175, 95, 255),
        (175, 135, 0),
        (175, 135, 95),
        (175, 135, 135),
        (175, 135, 175),
        (175, 135, 215),
        (175, 135, 255),
        (175, 175, 0),
        (175, 175, 95),
        (175, 175, 135),
        (175, 175, 175),
        (175, 175, 215),
        (175, 175, 255),
        (175, 215, 0),
        (175, 215, 95),
        (175, 215, 135),
        (175, 215, 175),
        (175, 215, 215),
        (175, 215, 255),
        (175, 255, 0),
        (175, 255, 95),
        (175, 255, 135),
        (175, 255, 175),
        (175, 255, 215),
        (175, 255, 255),
        (215, 0, 0),
        (215, 0, 95),
        (215, 0, 135),
        (215, 0, 175),
        (215, 0, 215),
        (215, 0, 255),
        (215, 95, 0),
        (215, 95, 95),
        (215, 95, 135),
        (215, 95, 175),
        (215, 95, 215),
        (215, 95, 255),
        (215, 135, 0),
        (215, 135, 95),
        (215, 135, 135),
        (215, 135, 175),
        (215, 135, 215),
        (215, 135, 255),
        (215, 175, 0),
        (215, 175, 95),
        (215, 175, 135),
        (215, 175, 175),
        (215, 175, 215),
        (215, 175, 255),
        (215, 215, 0),
        (215, 215, 95),
        (215, 215, 135),
        (215, 215, 175),
        (215, 215, 215),
        (215, 215, 255),
        (215, 255, 0),
        (215, 255, 95),
        (215, 255, 135),
        (215, 255, 175),
        (215, 255, 215),
        (215, 255, 255),
        (255, 0, 0),
        (255, 0, 95),
        (255, 0, 135),
        (255, 0, 175),
        (255, 0, 215),
        (255, 0, 255),
        (255, 95, 0),
        (255, 95, 95),
        (255, 95, 135),
        (255, 95, 175),
        (255, 95, 215),
        (255, 95, 255),
        (255, 135, 0),
        (255, 135, 95),
        (255, 135, 135),
        (255, 135, 175),
        (255, 135, 215),
        (255, 135, 255),
        (255, 175, 0),
        (255, 175, 95),
        (255, 175, 135),
        (255, 175, 175),
        (255, 175, 215),
        (255, 175, 255),
        (255, 215, 0),
        (255, 215, 95),
        (255, 215, 135),
        (255, 215, 175),
        (255, 215, 215),
        (255, 215, 255),
        (255, 255, 0),
        (255, 255, 95),
        (255, 255, 135),
        (255, 255, 175),
        (255, 255, 215),
        (255, 255, 255),
        (8, 8, 8),
        (18, 18, 18),
        (28, 28, 28),
        (38, 38, 38),
        (48, 48, 48),
        (58, 58, 58),
        (68, 68, 68),
        (78, 78, 78),
        (88, 88, 88),
        (98, 98, 98),
        (108, 108, 108),
        (118, 118, 118),
        (128, 128, 128),
        (138, 138, 138),
        (148, 148, 148),
        (158, 158, 158),
        (168, 168, 168),
        (178, 178, 178),
        (188, 188, 188),
        (198, 198, 198),
        (208, 208, 208),
        (218, 218, 218),
        (228, 228, 228),
        (238, 238, 238),
    ]
)

# === NexusCore/openenv\Lib\site-packages\aiohttp\_cookie_helpers.py ===
"""
Internal cookie handling helpers.

This module contains internal utilities for cookie parsing and manipulation.
These are not part of the public API and may change without notice.
"""

import re
import sys
from http.cookies import Morsel
from typing import List, Optional, Sequence, Tuple, cast

from .log import internal_logger

__all__ = (
    "parse_set_cookie_headers",
    "parse_cookie_header",
    "preserve_morsel_with_coded_value",
)

# Cookie parsing constants
# Allow more characters in cookie names to handle real-world cookies
# that don't strictly follow RFC standards (fixes #2683)
# RFC 6265 defines cookie-name token as per RFC 2616 Section 2.2,
# but many servers send cookies with characters like {} [] () etc.
# This makes the cookie parser more tolerant of real-world cookies
# while still providing some validation to catch obviously malformed names.
_COOKIE_NAME_RE = re.compile(r"^[!#$%&\'()*+\-./0-9:<=>?@A-Z\[\]^_`a-z{|}~]+$")
_COOKIE_KNOWN_ATTRS = frozenset(  # AKA Morsel._reserved
    (
        "path",
        "domain",
        "max-age",
        "expires",
        "secure",
        "httponly",
        "samesite",
        "partitioned",
        "version",
        "comment",
    )
)
_COOKIE_BOOL_ATTRS = frozenset(  # AKA Morsel._flags
    ("secure", "httponly", "partitioned")
)

# SimpleCookie's pattern for parsing cookies with relaxed validation
# Based on http.cookies pattern but extended to allow more characters in cookie names
# to handle real-world cookies (fixes #2683)
_COOKIE_PATTERN = re.compile(
    r"""
    \s*                            # Optional whitespace at start of cookie
    (?P<key>                       # Start of group 'key'
    # aiohttp has extended to include [] for compatibility with real-world cookies
    [\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\=\[\]]+?   # Any word of at least one letter
    )                              # End of group 'key'
    (                              # Optional group: there may not be a value.
    \s*=\s*                          # Equal Sign
    (?P<val>                         # Start of group 'val'
    "(?:[^\\"]|\\.)*"                  # Any double-quoted string (properly closed)
    |                                  # or
    "[^";]*                            # Unmatched opening quote (differs from SimpleCookie - issue #7993)
    |                                  # or
    # Special case for "expires" attr - RFC 822, RFC 850, RFC 1036, RFC 1123
    (\w{3,6}day|\w{3}),\s              # Day of the week or abbreviated day (with comma)
    [\w\d\s-]{9,11}\s[\d:]{8}\s        # Date and time in specific format
    (GMT|[+-]\d{4})                     # Timezone: GMT or RFC 2822 offset like -0000, +0100
                                        # NOTE: RFC 2822 timezone support is an aiohttp extension
                                        # for issue #4493 - SimpleCookie does NOT support this
    |                                  # or
    # ANSI C asctime() format: "Wed Jun  9 10:18:14 2021"
    # NOTE: This is an aiohttp extension for issue #4327 - SimpleCookie does NOT support this format
    \w{3}\s+\w{3}\s+[\s\d]\d\s+\d{2}:\d{2}:\d{2}\s+\d{4}
    |                                  # or
    [\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\=\[\]]*      # Any word or empty string
    )                                # End of group 'val'
    )?                             # End of optional value group
    \s*                            # Any number of spaces.
    (\s+|;|$)                      # Ending either at space, semicolon, or EOS.
    """,
    re.VERBOSE | re.ASCII,
)


def preserve_morsel_with_coded_value(cookie: Morsel[str]) -> Morsel[str]:
    """
    Preserve a Morsel's coded_value exactly as received from the server.

    This function ensures that cookie encoding is preserved exactly as sent by
    the server, which is critical for compatibility with old servers that have
    strict requirements about cookie formats.

    This addresses the issue described in https://github.com/aio-libs/aiohttp/pull/1453
    where Python's SimpleCookie would re-encode cookies, breaking authentication
    with certain servers.

    Args:
        cookie: A Morsel object from SimpleCookie

    Returns:
        A Morsel object with preserved coded_value

    """
    mrsl_val = cast("Morsel[str]", cookie.get(cookie.key, Morsel()))
    # We use __setstate__ instead of the public set() API because it allows us to
    # bypass validation and set already validated state. This is more stable than
    # setting protected attributes directly and unlikely to change since it would
    # break pickling.
    mrsl_val.__setstate__(  # type: ignore[attr-defined]
        {"key": cookie.key, "value": cookie.value, "coded_value": cookie.coded_value}
    )
    return mrsl_val


_unquote_sub = re.compile(r"\\(?:([0-3][0-7][0-7])|(.))").sub


def _unquote_replace(m: re.Match[str]) -> str:
    """
    Replace function for _unquote_sub regex substitution.

    Handles escaped characters in cookie values:
    - Octal sequences are converted to their character representation
    - Other escaped characters are unescaped by removing the backslash
    """
    if m[1]:
        return chr(int(m[1], 8))
    return m[2]


def _unquote(value: str) -> str:
    """
    Unquote a cookie value.

    Vendored from http.cookies._unquote to ensure compatibility.

    Note: The original implementation checked for None, but we've removed
    that check since all callers already ensure the value is not None.
    """
    # If there aren't any doublequotes,
    # then there can't be any special characters.  See RFC 2109.
    if len(value) < 2:
        return value
    if value[0] != '"' or value[-1] != '"':
        return value

    # We have to assume that we must decode this string.
    # Down to work.

    # Remove the "s
    value = value[1:-1]

    # Check for special sequences.  Examples:
    #    \012 --> \n
    #    \"   --> "
    #
    return _unquote_sub(_unquote_replace, value)


def parse_cookie_header(header: str) -> List[Tuple[str, Morsel[str]]]:
    """
    Parse a Cookie header according to RFC 6265 Section 5.4.

    Cookie headers contain only name-value pairs separated by semicolons.
    There are no attributes in Cookie headers - even names that match
    attribute names (like 'path' or 'secure') should be treated as cookies.

    This parser uses the same regex-based approach as parse_set_cookie_headers
    to properly handle quoted values that may contain semicolons.

    Args:
        header: The Cookie header value to parse

    Returns:
        List of (name, Morsel) tuples for compatibility with SimpleCookie.update()
    """
    if not header:
        return []

    cookies: List[Tuple[str, Morsel[str]]] = []
    i = 0
    n = len(header)

    while i < n:
        # Use the same pattern as parse_set_cookie_headers to find cookies
        match = _COOKIE_PATTERN.match(header, i)
        if not match:
            break

        key = match.group("key")
        value = match.group("val") or ""
        i = match.end(0)

        # Validate the name
        if not key or not _COOKIE_NAME_RE.match(key):
            internal_logger.warning("Can not load cookie: Illegal cookie name %r", key)
            continue

        # Create new morsel
        morsel: Morsel[str] = Morsel()
        # Preserve the original value as coded_value (with quotes if present)
        # We use __setstate__ instead of the public set() API because it allows us to
        # bypass validation and set already validated state. This is more stable than
        # setting protected attributes directly and unlikely to change since it would
        # break pickling.
        morsel.__setstate__(  # type: ignore[attr-defined]
            {"key": key, "value": _unquote(value), "coded_value": value}
        )

        cookies.append((key, morsel))

    return cookies


def parse_set_cookie_headers(headers: Sequence[str]) -> List[Tuple[str, Morsel[str]]]:
    """
    Parse cookie headers using a vendored version of SimpleCookie parsing.

    This implementation is based on SimpleCookie.__parse_string to ensure
    compatibility with how SimpleCookie parses cookies, including handling
    of malformed cookies with missing semicolons.

    This function is used for both Cookie and Set-Cookie headers in order to be
    forgiving. Ideally we would have followed RFC 6265 Section 5.2 (for Cookie
    headers) and RFC 6265 Section 4.2.1 (for Set-Cookie headers), but the
    real world data makes it impossible since we need to be a bit more forgiving.

    NOTE: This implementation differs from SimpleCookie in handling unmatched quotes.
    SimpleCookie will stop parsing when it encounters a cookie value with an unmatched
    quote (e.g., 'cookie="value'), causing subsequent cookies to be silently dropped.
    This implementation handles unmatched quotes more gracefully to prevent cookie loss.
    See https://github.com/aio-libs/aiohttp/issues/7993
    """
    parsed_cookies: List[Tuple[str, Morsel[str]]] = []

    for header in headers:
        if not header:
            continue

        # Parse cookie string using SimpleCookie's algorithm
        i = 0
        n = len(header)
        current_morsel: Optional[Morsel[str]] = None
        morsel_seen = False

        while 0 <= i < n:
            # Start looking for a cookie
            match = _COOKIE_PATTERN.match(header, i)
            if not match:
                # No more cookies
                break

            key, value = match.group("key"), match.group("val")
            i = match.end(0)
            lower_key = key.lower()

            if key[0] == "$":
                if not morsel_seen:
                    # We ignore attributes which pertain to the cookie
                    # mechanism as a whole, such as "$Version".
                    continue
                # Process as attribute
                if current_morsel is not None:
                    attr_lower_key = lower_key[1:]
                    if attr_lower_key in _COOKIE_KNOWN_ATTRS:
                        current_morsel[attr_lower_key] = value or ""
            elif lower_key in _COOKIE_KNOWN_ATTRS:
                if not morsel_seen:
                    # Invalid cookie string - attribute before cookie
                    break
                if lower_key in _COOKIE_BOOL_ATTRS:
                    # Boolean attribute with any value should be True
                    if current_morsel is not None:
                        if lower_key == "partitioned" and sys.version_info < (3, 14):
                            dict.__setitem__(current_morsel, lower_key, True)
                        else:
                            current_morsel[lower_key] = True
                elif value is None:
                    # Invalid cookie string - non-boolean attribute without value
                    break
                elif current_morsel is not None:
                    # Regular attribute with value
                    current_morsel[lower_key] = _unquote(value)
            elif value is not None:
                # This is a cookie name=value pair
                # Validate the name
                if key in _COOKIE_KNOWN_ATTRS or not _COOKIE_NAME_RE.match(key):
                    internal_logger.warning(
                        "Can not load cookies: Illegal cookie name %r", key
                    )
                    current_morsel = None
                else:
                    # Create new morsel
                    current_morsel = Morsel()
                    # Preserve the original value as coded_value (with quotes if present)
                    # We use __setstate__ instead of the public set() API because it allows us to
                    # bypass validation and set already validated state. This is more stable than
                    # setting protected attributes directly and unlikely to change since it would
                    # break pickling.
                    current_morsel.__setstate__(  # type: ignore[attr-defined]
                        {"key": key, "value": _unquote(value), "coded_value": value}
                    )
                    parsed_cookies.append((key, current_morsel))
                    morsel_seen = True
            else:
                # Invalid cookie string - no value for non-attribute
                break

    return parsed_cookies

# === NexusCore/openenv\Lib\site-packages\matplotlib\layout_engine.py ===
"""
Classes to layout elements in a `.Figure`.

Figures have a ``layout_engine`` property that holds a subclass of
`~.LayoutEngine` defined here (or *None* for no layout).  At draw time
``figure.get_layout_engine().execute()`` is called, the goal of which is
usually to rearrange Axes on the figure to produce a pleasing layout. This is
like a ``draw`` callback but with two differences.  First, when printing we
disable the layout engine for the final draw. Second, it is useful to know the
layout engine while the figure is being created.  In particular, colorbars are
made differently with different layout engines (for historical reasons).

Matplotlib has two built-in layout engines:

- `.TightLayoutEngine` was the first layout engine added to Matplotlib.
  See also :ref:`tight_layout_guide`.
- `.ConstrainedLayoutEngine` is more modern and generally gives better results.
  See also :ref:`constrainedlayout_guide`.

Third parties can create their own layout engine by subclassing `.LayoutEngine`.
"""

from contextlib import nullcontext

import matplotlib as mpl

from matplotlib._constrained_layout import do_constrained_layout
from matplotlib._tight_layout import (get_subplotspec_list,
                                      get_tight_layout_figure)


class LayoutEngine:
    """
    Base class for Matplotlib layout engines.

    A layout engine can be passed to a figure at instantiation or at any time
    with `~.figure.Figure.set_layout_engine`.  Once attached to a figure, the
    layout engine ``execute`` function is called at draw time by
    `~.figure.Figure.draw`, providing a special draw-time hook.

    .. note::

       However, note that layout engines affect the creation of colorbars, so
       `~.figure.Figure.set_layout_engine` should be called before any
       colorbars are created.

    Currently, there are two properties of `LayoutEngine` classes that are
    consulted while manipulating the figure:

    - ``engine.colorbar_gridspec`` tells `.Figure.colorbar` whether to make the
       axes using the gridspec method (see `.colorbar.make_axes_gridspec`) or
       not (see `.colorbar.make_axes`);
    - ``engine.adjust_compatible`` stops `.Figure.subplots_adjust` from being
        run if it is not compatible with the layout engine.

    To implement a custom `LayoutEngine`:

    1. override ``_adjust_compatible`` and ``_colorbar_gridspec``
    2. override `LayoutEngine.set` to update *self._params*
    3. override `LayoutEngine.execute` with your implementation

    """
    # override these in subclass
    _adjust_compatible = None
    _colorbar_gridspec = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._params = {}

    def set(self, **kwargs):
        """
        Set the parameters for the layout engine.
        """
        raise NotImplementedError

    @property
    def colorbar_gridspec(self):
        """
        Return a boolean if the layout engine creates colorbars using a
        gridspec.
        """
        if self._colorbar_gridspec is None:
            raise NotImplementedError
        return self._colorbar_gridspec

    @property
    def adjust_compatible(self):
        """
        Return a boolean if the layout engine is compatible with
        `~.Figure.subplots_adjust`.
        """
        if self._adjust_compatible is None:
            raise NotImplementedError
        return self._adjust_compatible

    def get(self):
        """
        Return copy of the parameters for the layout engine.
        """
        return dict(self._params)

    def execute(self, fig):
        """
        Execute the layout on the figure given by *fig*.
        """
        # subclasses must implement this.
        raise NotImplementedError


class PlaceHolderLayoutEngine(LayoutEngine):
    """
    This layout engine does not adjust the figure layout at all.

    The purpose of this `.LayoutEngine` is to act as a placeholder when the user removes
    a layout engine to ensure an incompatible `.LayoutEngine` cannot be set later.

    Parameters
    ----------
    adjust_compatible, colorbar_gridspec : bool
        Allow the PlaceHolderLayoutEngine to mirror the behavior of whatever
        layout engine it is replacing.

    """
    def __init__(self, adjust_compatible, colorbar_gridspec, **kwargs):
        self._adjust_compatible = adjust_compatible
        self._colorbar_gridspec = colorbar_gridspec
        super().__init__(**kwargs)

    def execute(self, fig):
        """
        Do nothing.
        """
        return


class TightLayoutEngine(LayoutEngine):
    """
    Implements the ``tight_layout`` geometry management.  See
    :ref:`tight_layout_guide` for details.
    """
    _adjust_compatible = True
    _colorbar_gridspec = True

    def __init__(self, *, pad=1.08, h_pad=None, w_pad=None,
                 rect=(0, 0, 1, 1), **kwargs):
        """
        Initialize tight_layout engine.

        Parameters
        ----------
        pad : float, default: 1.08
            Padding between the figure edge and the edges of subplots, as a
            fraction of the font size.
        h_pad, w_pad : float
            Padding (height/width) between edges of adjacent subplots.
            Defaults to *pad*.
        rect : tuple (left, bottom, right, top), default: (0, 0, 1, 1).
            rectangle in normalized figure coordinates that the subplots
            (including labels) will fit into.
        """
        super().__init__(**kwargs)
        for td in ['pad', 'h_pad', 'w_pad', 'rect']:
            # initialize these in case None is passed in above:
            self._params[td] = None
        self.set(pad=pad, h_pad=h_pad, w_pad=w_pad, rect=rect)

    def execute(self, fig):
        """
        Execute tight_layout.

        This decides the subplot parameters given the padding that
        will allow the Axes labels to not be covered by other labels
        and Axes.

        Parameters
        ----------
        fig : `.Figure` to perform layout on.

        See Also
        --------
        .figure.Figure.tight_layout
        .pyplot.tight_layout
        """
        info = self._params
        renderer = fig._get_renderer()
        with getattr(renderer, "_draw_disabled", nullcontext)():
            kwargs = get_tight_layout_figure(
                fig, fig.axes, get_subplotspec_list(fig.axes), renderer,
                pad=info['pad'], h_pad=info['h_pad'], w_pad=info['w_pad'],
                rect=info['rect'])
        if kwargs:
            fig.subplots_adjust(**kwargs)

    def set(self, *, pad=None, w_pad=None, h_pad=None, rect=None):
        """
        Set the pads for tight_layout.

        Parameters
        ----------
        pad : float
            Padding between the figure edge and the edges of subplots, as a
            fraction of the font size.
        w_pad, h_pad : float
            Padding (width/height) between edges of adjacent subplots.
            Defaults to *pad*.
        rect : tuple (left, bottom, right, top)
            rectangle in normalized figure coordinates that the subplots
            (including labels) will fit into.
        """
        for td in self.set.__kwdefaults__:
            if locals()[td] is not None:
                self._params[td] = locals()[td]


class ConstrainedLayoutEngine(LayoutEngine):
    """
    Implements the ``constrained_layout`` geometry management.  See
    :ref:`constrainedlayout_guide` for details.
    """

    _adjust_compatible = False
    _colorbar_gridspec = False

    def __init__(self, *, h_pad=None, w_pad=None,
                 hspace=None, wspace=None, rect=(0, 0, 1, 1),
                 compress=False, **kwargs):
        """
        Initialize ``constrained_layout`` settings.

        Parameters
        ----------
        h_pad, w_pad : float
            Padding around the Axes elements in inches.
            Default to :rc:`figure.constrained_layout.h_pad` and
            :rc:`figure.constrained_layout.w_pad`.
        hspace, wspace : float
            Fraction of the figure to dedicate to space between the
            axes.  These are evenly spread between the gaps between the Axes.
            A value of 0.2 for a three-column layout would have a space
            of 0.1 of the figure width between each column.
            If h/wspace < h/w_pad, then the pads are used instead.
            Default to :rc:`figure.constrained_layout.hspace` and
            :rc:`figure.constrained_layout.wspace`.
        rect : tuple of 4 floats
            Rectangle in figure coordinates to perform constrained layout in
            (left, bottom, width, height), each from 0-1.
        compress : bool
            Whether to shift Axes so that white space in between them is
            removed. This is useful for simple grids of fixed-aspect Axes (e.g.
            a grid of images).  See :ref:`compressed_layout`.
        """
        super().__init__(**kwargs)
        # set the defaults:
        self.set(w_pad=mpl.rcParams['figure.constrained_layout.w_pad'],
                 h_pad=mpl.rcParams['figure.constrained_layout.h_pad'],
                 wspace=mpl.rcParams['figure.constrained_layout.wspace'],
                 hspace=mpl.rcParams['figure.constrained_layout.hspace'],
                 rect=(0, 0, 1, 1))
        # set anything that was passed in (None will be ignored):
        self.set(w_pad=w_pad, h_pad=h_pad, wspace=wspace, hspace=hspace,
                 rect=rect)
        self._compress = compress

    def execute(self, fig):
        """
        Perform constrained_layout and move and resize Axes accordingly.

        Parameters
        ----------
        fig : `.Figure` to perform layout on.
        """
        width, height = fig.get_size_inches()
        # pads are relative to the current state of the figure...
        w_pad = self._params['w_pad'] / width
        h_pad = self._params['h_pad'] / height

        return do_constrained_layout(fig, w_pad=w_pad, h_pad=h_pad,
                                     wspace=self._params['wspace'],
                                     hspace=self._params['hspace'],
                                     rect=self._params['rect'],
                                     compress=self._compress)

    def set(self, *, h_pad=None, w_pad=None,
            hspace=None, wspace=None, rect=None):
        """
        Set the pads for constrained_layout.

        Parameters
        ----------
        h_pad, w_pad : float
            Padding around the Axes elements in inches.
            Default to :rc:`figure.constrained_layout.h_pad` and
            :rc:`figure.constrained_layout.w_pad`.
        hspace, wspace : float
            Fraction of the figure to dedicate to space between the
            axes.  These are evenly spread between the gaps between the Axes.
            A value of 0.2 for a three-column layout would have a space
            of 0.1 of the figure width between each column.
            If h/wspace < h/w_pad, then the pads are used instead.
            Default to :rc:`figure.constrained_layout.hspace` and
            :rc:`figure.constrained_layout.wspace`.
        rect : tuple of 4 floats
            Rectangle in figure coordinates to perform constrained layout in
            (left, bottom, width, height), each from 0-1.
        """
        for td in self.set.__kwdefaults__:
            if locals()[td] is not None:
                self._params[td] = locals()[td]

# === NexusCore/openenv\Lib\site-packages\rich\_palettes.py ===
from .palette import Palette


# Taken from https://en.wikipedia.org/wiki/ANSI_escape_code (Windows 10 column)
WINDOWS_PALETTE = Palette(
    [
        (12, 12, 12),
        (197, 15, 31),
        (19, 161, 14),
        (193, 156, 0),
        (0, 55, 218),
        (136, 23, 152),
        (58, 150, 221),
        (204, 204, 204),
        (118, 118, 118),
        (231, 72, 86),
        (22, 198, 12),
        (249, 241, 165),
        (59, 120, 255),
        (180, 0, 158),
        (97, 214, 214),
        (242, 242, 242),
    ]
)

# # The standard ansi colors (including bright variants)
STANDARD_PALETTE = Palette(
    [
        (0, 0, 0),
        (170, 0, 0),
        (0, 170, 0),
        (170, 85, 0),
        (0, 0, 170),
        (170, 0, 170),
        (0, 170, 170),
        (170, 170, 170),
        (85, 85, 85),
        (255, 85, 85),
        (85, 255, 85),
        (255, 255, 85),
        (85, 85, 255),
        (255, 85, 255),
        (85, 255, 255),
        (255, 255, 255),
    ]
)


# The 256 color palette
EIGHT_BIT_PALETTE = Palette(
    [
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
        (0, 0, 0),
        (0, 0, 95),
        (0, 0, 135),
        (0, 0, 175),
        (0, 0, 215),
        (0, 0, 255),
        (0, 95, 0),
        (0, 95, 95),
        (0, 95, 135),
        (0, 95, 175),
        (0, 95, 215),
        (0, 95, 255),
        (0, 135, 0),
        (0, 135, 95),
        (0, 135, 135),
        (0, 135, 175),
        (0, 135, 215),
        (0, 135, 255),
        (0, 175, 0),
        (0, 175, 95),
        (0, 175, 135),
        (0, 175, 175),
        (0, 175, 215),
        (0, 175, 255),
        (0, 215, 0),
        (0, 215, 95),
        (0, 215, 135),
        (0, 215, 175),
        (0, 215, 215),
        (0, 215, 255),
        (0, 255, 0),
        (0, 255, 95),
        (0, 255, 135),
        (0, 255, 175),
        (0, 255, 215),
        (0, 255, 255),
        (95, 0, 0),
        (95, 0, 95),
        (95, 0, 135),
        (95, 0, 175),
        (95, 0, 215),
        (95, 0, 255),
        (95, 95, 0),
        (95, 95, 95),
        (95, 95, 135),
        (95, 95, 175),
        (95, 95, 215),
        (95, 95, 255),
        (95, 135, 0),
        (95, 135, 95),
        (95, 135, 135),
        (95, 135, 175),
        (95, 135, 215),
        (95, 135, 255),
        (95, 175, 0),
        (95, 175, 95),
        (95, 175, 135),
        (95, 175, 175),
        (95, 175, 215),
        (95, 175, 255),
        (95, 215, 0),
        (95, 215, 95),
        (95, 215, 135),
        (95, 215, 175),
        (95, 215, 215),
        (95, 215, 255),
        (95, 255, 0),
        (95, 255, 95),
        (95, 255, 135),
        (95, 255, 175),
        (95, 255, 215),
        (95, 255, 255),
        (135, 0, 0),
        (135, 0, 95),
        (135, 0, 135),
        (135, 0, 175),
        (135, 0, 215),
        (135, 0, 255),
        (135, 95, 0),
        (135, 95, 95),
        (135, 95, 135),
        (135, 95, 175),
        (135, 95, 215),
        (135, 95, 255),
        (135, 135, 0),
        (135, 135, 95),
        (135, 135, 135),
        (135, 135, 175),
        (135, 135, 215),
        (135, 135, 255),
        (135, 175, 0),
        (135, 175, 95),
        (135, 175, 135),
        (135, 175, 175),
        (135, 175, 215),
        (135, 175, 255),
        (135, 215, 0),
        (135, 215, 95),
        (135, 215, 135),
        (135, 215, 175),
        (135, 215, 215),
        (135, 215, 255),
        (135, 255, 0),
        (135, 255, 95),
        (135, 255, 135),
        (135, 255, 175),
        (135, 255, 215),
        (135, 255, 255),
        (175, 0, 0),
        (175, 0, 95),
        (175, 0, 135),
        (175, 0, 175),
        (175, 0, 215),
        (175, 0, 255),
        (175, 95, 0),
        (175, 95, 95),
        (175, 95, 135),
        (175, 95, 175),
        (175, 95, 215),
        (175, 95, 255),
        (175, 135, 0),
        (175, 135, 95),
        (175, 135, 135),
        (175, 135, 175),
        (175, 135, 215),
        (175, 135, 255),
        (175, 175, 0),
        (175, 175, 95),
        (175, 175, 135),
        (175, 175, 175),
        (175, 175, 215),
        (175, 175, 255),
        (175, 215, 0),
        (175, 215, 95),
        (175, 215, 135),
        (175, 215, 175),
        (175, 215, 215),
        (175, 215, 255),
        (175, 255, 0),
        (175, 255, 95),
        (175, 255, 135),
        (175, 255, 175),
        (175, 255, 215),
        (175, 255, 255),
        (215, 0, 0),
        (215, 0, 95),
        (215, 0, 135),
        (215, 0, 175),
        (215, 0, 215),
        (215, 0, 255),
        (215, 95, 0),
        (215, 95, 95),
        (215, 95, 135),
        (215, 95, 175),
        (215, 95, 215),
        (215, 95, 255),
        (215, 135, 0),
        (215, 135, 95),
        (215, 135, 135),
        (215, 135, 175),
        (215, 135, 215),
        (215, 135, 255),
        (215, 175, 0),
        (215, 175, 95),
        (215, 175, 135),
        (215, 175, 175),
        (215, 175, 215),
        (215, 175, 255),
        (215, 215, 0),
        (215, 215, 95),
        (215, 215, 135),
        (215, 215, 175),
        (215, 215, 215),
        (215, 215, 255),
        (215, 255, 0),
        (215, 255, 95),
        (215, 255, 135),
        (215, 255, 175),
        (215, 255, 215),
        (215, 255, 255),
        (255, 0, 0),
        (255, 0, 95),
        (255, 0, 135),
        (255, 0, 175),
        (255, 0, 215),
        (255, 0, 255),
        (255, 95, 0),
        (255, 95, 95),
        (255, 95, 135),
        (255, 95, 175),
        (255, 95, 215),
        (255, 95, 255),
        (255, 135, 0),
        (255, 135, 95),
        (255, 135, 135),
        (255, 135, 175),
        (255, 135, 215),
        (255, 135, 255),
        (255, 175, 0),
        (255, 175, 95),
        (255, 175, 135),
        (255, 175, 175),
        (255, 175, 215),
        (255, 175, 255),
        (255, 215, 0),
        (255, 215, 95),
        (255, 215, 135),
        (255, 215, 175),
        (255, 215, 215),
        (255, 215, 255),
        (255, 255, 0),
        (255, 255, 95),
        (255, 255, 135),
        (255, 255, 175),
        (255, 255, 215),
        (255, 255, 255),
        (8, 8, 8),
        (18, 18, 18),
        (28, 28, 28),
        (38, 38, 38),
        (48, 48, 48),
        (58, 58, 58),
        (68, 68, 68),
        (78, 78, 78),
        (88, 88, 88),
        (98, 98, 98),
        (108, 108, 108),
        (118, 118, 118),
        (128, 128, 128),
        (138, 138, 138),
        (148, 148, 148),
        (158, 158, 158),
        (168, 168, 168),
        (178, 178, 178),
        (188, 188, 188),
        (198, 198, 198),
        (208, 208, 208),
        (218, 218, 218),
        (228, 228, 228),
        (238, 238, 238),
    ]
)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\instancer\solver.py ===
from fontTools.varLib.models import supportScalar
from fontTools.misc.fixedTools import MAX_F2DOT14
from functools import lru_cache

__all__ = ["rebaseTent"]

EPSILON = 1 / (1 << 14)


def _reverse_negate(v):
    return (-v[2], -v[1], -v[0])


def _solve(tent, axisLimit, negative=False):
    axisMin, axisDef, axisMax, _distanceNegative, _distancePositive = axisLimit
    lower, peak, upper = tent

    # Mirror the problem such that axisDef <= peak
    if axisDef > peak:
        return [
            (scalar, _reverse_negate(t) if t is not None else None)
            for scalar, t in _solve(
                _reverse_negate(tent),
                axisLimit.reverse_negate(),
                not negative,
            )
        ]
    # axisDef <= peak

    # case 1: The whole deltaset falls outside the new limit; we can drop it
    #
    #                                          peak
    #  1.........................................o..........
    #                                           / \
    #                                          /   \
    #                                         /     \
    #                                        /       \
    #  0---|-----------|----------|-------- o         o----1
    #    axisMin     axisDef    axisMax   lower     upper
    #
    if axisMax <= lower and axisMax < peak:
        return []  # No overlap

    # case 2: Only the peak and outermost bound fall outside the new limit;
    # we keep the deltaset, update peak and outermost bound and and scale deltas
    # by the scalar value for the restricted axis at the new limit, and solve
    # recursively.
    #
    #                                  |peak
    #  1...............................|.o..........
    #                                  |/ \
    #                                  /   \
    #                                 /|    \
    #                                / |     \
    #  0--------------------------- o  |      o----1
    #                           lower  |      upper
    #                                  |
    #                                axisMax
    #
    # Convert to:
    #
    #  1............................................
    #                                  |
    #                                  o peak
    #                                 /|
    #                                /x|
    #  0--------------------------- o  o upper ----1
    #                           lower  |
    #                                  |
    #                                axisMax
    if axisMax < peak:
        mult = supportScalar({"tag": axisMax}, {"tag": tent})
        tent = (lower, axisMax, axisMax)
        return [(scalar * mult, t) for scalar, t in _solve(tent, axisLimit)]

    # lower <= axisDef <= peak <= axisMax

    gain = supportScalar({"tag": axisDef}, {"tag": tent})
    out = [(gain, None)]

    # First, the positive side

    # outGain is the scalar of axisMax at the tent.
    outGain = supportScalar({"tag": axisMax}, {"tag": tent})

    # Case 3a: Gain is more than outGain. The tent down-slope crosses
    # the axis into negative. We have to split it into multiples.
    #
    #                      | peak  |
    #  1...................|.o.....|..............
    #                      |/x\_   |
    #  gain................+....+_.|..............
    #                     /|    |y\|
    #  ................../.|....|..+_......outGain
    #                   /  |    |  | \
    #  0---|-----------o   |    |  |  o----------1
    #    axisMin    lower  |    |  |   upper
    #                      |    |  |
    #                axisDef    |  axisMax
    #                           |
    #                      crossing
    if gain >= outGain:
        # Note that this is the branch taken if both gain and outGain are 0.

        # Crossing point on the axis.
        crossing = peak + (1 - gain) * (upper - peak)

        loc = (max(lower, axisDef), peak, crossing)
        scalar = 1

        # The part before the crossing point.
        out.append((scalar - gain, loc))

        # The part after the crossing point may use one or two tents,
        # depending on whether upper is before axisMax or not, in one
        # case we need to keep it down to eternity.

        # Case 3a1, similar to case 1neg; just one tent needed, as in
        # the drawing above.
        if upper >= axisMax:
            loc = (crossing, axisMax, axisMax)
            scalar = outGain

            out.append((scalar - gain, loc))

        # Case 3a2: Similar to case 2neg; two tents needed, to keep
        # down to eternity.
        #
        #                      | peak             |
        #  1...................|.o................|...
        #                      |/ \_              |
        #  gain................+....+_............|...
        #                     /|    | \xxxxxxxxxxy|
        #                    / |    |  \_xxxxxyyyy|
        #                   /  |    |    \xxyyyyyy|
        #  0---|-----------o   |    |     o-------|--1
        #    axisMin    lower  |    |      upper  |
        #                      |    |             |
        #                axisDef    |             axisMax
        #                           |
        #                      crossing
        else:
            # A tent's peak cannot fall on axis default. Nudge it.
            if upper == axisDef:
                upper += EPSILON

            # Downslope.
            loc1 = (crossing, upper, axisMax)
            scalar1 = 0

            # Eternity justify.
            loc2 = (upper, axisMax, axisMax)
            scalar2 = 0

            out.append((scalar1 - gain, loc1))
            out.append((scalar2 - gain, loc2))

    else:
        # Special-case if peak is at axisMax.
        if axisMax == peak:
            upper = peak

        # Case 3:
        # We keep delta as is and only scale the axis upper to achieve
        # the desired new tent if feasible.
        #
        #                        peak
        #  1.....................o....................
        #                       / \_|
        #  ..................../....+_.........outGain
        #                     /     | \
        #  gain..............+......|..+_.............
        #                   /|      |  | \
        #  0---|-----------o |      |  |  o----------1
        #    axisMin    lower|      |  |   upper
        #                    |      |  newUpper
        #              axisDef      axisMax
        #
        newUpper = peak + (1 - gain) * (upper - peak)
        assert axisMax <= newUpper  # Because outGain > gain
        # Disabled because ots doesn't like us:
        # https://github.com/fonttools/fonttools/issues/3350
        if False and newUpper <= axisDef + (axisMax - axisDef) * 2:
            upper = newUpper
            if not negative and axisDef + (axisMax - axisDef) * MAX_F2DOT14 < upper:
                # we clamp +2.0 to the max F2Dot14 (~1.99994) for convenience
                upper = axisDef + (axisMax - axisDef) * MAX_F2DOT14
                assert peak < upper

            loc = (max(axisDef, lower), peak, upper)
            scalar = 1

            out.append((scalar - gain, loc))

        # Case 4: New limit doesn't fit; we need to chop into two tents,
        # because the shape of a triangle with part of one side cut off
        # cannot be represented as a triangle itself.
        #
        #            |   peak |
        #  1.........|......o.|....................
        #  ..........|...../x\|.............outGain
        #            |    |xxy|\_
        #            |   /xxxy|  \_
        #            |  |xxxxy|    \_
        #            |  /xxxxy|      \_
        #  0---|-----|-oxxxxxx|        o----------1
        #    axisMin | lower  |        upper
        #            |        |
        #          axisDef  axisMax
        #
        else:
            loc1 = (max(axisDef, lower), peak, axisMax)
            scalar1 = 1

            loc2 = (peak, axisMax, axisMax)
            scalar2 = outGain

            out.append((scalar1 - gain, loc1))
            # Don't add a dirac delta!
            if peak < axisMax:
                out.append((scalar2 - gain, loc2))

    # Now, the negative side

    # Case 1neg: Lower extends beyond axisMin: we chop. Simple.
    #
    #                     |   |peak
    #  1..................|...|.o.................
    #                     |   |/ \
    #  gain...............|...+...\...............
    #                     |x_/|    \
    #                     |/  |     \
    #                   _/|   |      \
    #  0---------------o  |   |       o----------1
    #              lower  |   |       upper
    #                     |   |
    #               axisMin   axisDef
    #
    if lower <= axisMin:
        loc = (axisMin, axisMin, axisDef)
        scalar = supportScalar({"tag": axisMin}, {"tag": tent})

        out.append((scalar - gain, loc))

    # Case 2neg: Lower is betwen axisMin and axisDef: we add two
    # tents to keep it down all the way to eternity.
    #
    #      |               |peak
    #  1...|...............|.o.................
    #      |               |/ \
    #  gain|...............+...\...............
    #      |yxxxxxxxxxxxxx/|    \
    #      |yyyyyyxxxxxxx/ |     \
    #      |yyyyyyyyyyyx/  |      \
    #  0---|-----------o   |       o----------1
    #    axisMin    lower  |       upper
    #                      |
    #                    axisDef
    #
    else:
        # A tent's peak cannot fall on axis default. Nudge it.
        if lower == axisDef:
            lower -= EPSILON

        # Downslope.
        loc1 = (axisMin, lower, axisDef)
        scalar1 = 0

        # Eternity justify.
        loc2 = (axisMin, axisMin, lower)
        scalar2 = 0

        out.append((scalar1 - gain, loc1))
        out.append((scalar2 - gain, loc2))

    return out


@lru_cache(128)
def rebaseTent(tent, axisLimit):
    """Given a tuple (lower,peak,upper) "tent" and new axis limits
    (axisMin,axisDefault,axisMax), solves how to represent the tent
    under the new axis configuration.  All values are in normalized
    -1,0,+1 coordinate system. Tent values can be outside this range.

    Return value is a list of tuples. Each tuple is of the form
    (scalar,tent), where scalar is a multipler to multiply any
    delta-sets by, and tent is a new tent for that output delta-set.
    If tent value is None, that is a special deltaset that should
    be always-enabled (called "gain")."""

    axisMin, axisDef, axisMax, _distanceNegative, _distancePositive = axisLimit
    assert -1 <= axisMin <= axisDef <= axisMax <= +1

    lower, peak, upper = tent
    assert -2 <= lower <= peak <= upper <= +2

    assert peak != 0

    sols = _solve(tent, axisLimit)

    n = lambda v: axisLimit.renormalizeValue(v)
    sols = [
        (scalar, (n(v[0]), n(v[1]), n(v[2])) if v is not None else None)
        for scalar, v in sols
        if scalar
    ]

    return sols

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\model_service.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

from google.protobuf import field_mask_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "GetModelRequest",
        "ListModelsRequest",
        "ListModelsResponse",
        "GetTunedModelRequest",
        "ListTunedModelsRequest",
        "ListTunedModelsResponse",
        "CreateTunedModelRequest",
        "CreateTunedModelMetadata",
        "UpdateTunedModelRequest",
        "DeleteTunedModelRequest",
    },
)


class GetModelRequest(proto.Message):
    r"""Request for getting information about a specific Model.

    Attributes:
        name (str):
            Required. The resource name of the model.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class ListModelsRequest(proto.Message):
    r"""Request for listing all Models.

    Attributes:
        page_size (int):
            The maximum number of ``Models`` to return (per page).

            The service may return fewer models. If unspecified, at most
            50 models will be returned per page. This method returns at
            most 1000 models per page, even if you pass a larger
            page_size.
        page_token (str):
            A page token, received from a previous ``ListModels`` call.

            Provide the ``page_token`` returned by one request as an
            argument to the next request to retrieve the next page.

            When paginating, all other parameters provided to
            ``ListModels`` must match the call that provided the page
            token.
    """

    page_size: int = proto.Field(
        proto.INT32,
        number=2,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=3,
    )


class ListModelsResponse(proto.Message):
    r"""Response from ``ListModel`` containing a paginated list of Models.

    Attributes:
        models (MutableSequence[google.ai.generativelanguage_v1beta3.types.Model]):
            The returned Models.
        next_page_token (str):
            A token, which can be sent as ``page_token`` to retrieve the
            next page.

            If this field is omitted, there are no more pages.
    """

    @property
    def raw_page(self):
        return self

    models: MutableSequence[model.Model] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=model.Model,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class GetTunedModelRequest(proto.Message):
    r"""Request for getting information about a specific Model.

    Attributes:
        name (str):
            Required. The resource name of the model.

            Format: ``tunedModels/my-model-id``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class ListTunedModelsRequest(proto.Message):
    r"""Request for listing TunedModels.

    Attributes:
        page_size (int):
            Optional. The maximum number of ``TunedModels`` to return
            (per page). The service may return fewer tuned models.

            If unspecified, at most 10 tuned models will be returned.
            This method returns at most 1000 models per page, even if
            you pass a larger page_size.
        page_token (str):
            Optional. A page token, received from a previous
            ``ListTunedModels`` call.

            Provide the ``page_token`` returned by one request as an
            argument to the next request to retrieve the next page.

            When paginating, all other parameters provided to
            ``ListTunedModels`` must match the call that provided the
            page token.
    """

    page_size: int = proto.Field(
        proto.INT32,
        number=1,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class ListTunedModelsResponse(proto.Message):
    r"""Response from ``ListTunedModels`` containing a paginated list of
    Models.

    Attributes:
        tuned_models (MutableSequence[google.ai.generativelanguage_v1beta3.types.TunedModel]):
            The returned Models.
        next_page_token (str):
            A token, which can be sent as ``page_token`` to retrieve the
            next page.

            If this field is omitted, there are no more pages.
    """

    @property
    def raw_page(self):
        return self

    tuned_models: MutableSequence[gag_tuned_model.TunedModel] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=gag_tuned_model.TunedModel,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class CreateTunedModelRequest(proto.Message):
    r"""Request to create a TunedModel.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        tuned_model_id (str):
            Optional. The unique id for the tuned model if specified.
            This value should be up to 40 characters, the first
            character must be a letter, the last could be a letter or a
            number. The id must match the regular expression:
            `a-z <[a-z0-9-]{0,38}[a-z0-9]>`__?.

            This field is a member of `oneof`_ ``_tuned_model_id``.
        tuned_model (google.ai.generativelanguage_v1beta3.types.TunedModel):
            Required. The tuned model to create.
    """

    tuned_model_id: str = proto.Field(
        proto.STRING,
        number=1,
        optional=True,
    )
    tuned_model: gag_tuned_model.TunedModel = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_tuned_model.TunedModel,
    )


class CreateTunedModelMetadata(proto.Message):
    r"""Metadata about the state and progress of creating a tuned
    model returned from the long-running operation

    Attributes:
        tuned_model (str):
            Name of the tuned model associated with the
            tuning operation.
        total_steps (int):
            The total number of tuning steps.
        completed_steps (int):
            The number of steps completed.
        completed_percent (float):
            The completed percentage for the tuning
            operation.
        snapshots (MutableSequence[google.ai.generativelanguage_v1beta3.types.TuningSnapshot]):
            Metrics collected during tuning.
    """

    tuned_model: str = proto.Field(
        proto.STRING,
        number=5,
    )
    total_steps: int = proto.Field(
        proto.INT32,
        number=1,
    )
    completed_steps: int = proto.Field(
        proto.INT32,
        number=2,
    )
    completed_percent: float = proto.Field(
        proto.FLOAT,
        number=3,
    )
    snapshots: MutableSequence[gag_tuned_model.TuningSnapshot] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=gag_tuned_model.TuningSnapshot,
    )


class UpdateTunedModelRequest(proto.Message):
    r"""Request to update a TunedModel.

    Attributes:
        tuned_model (google.ai.generativelanguage_v1beta3.types.TunedModel):
            Required. The tuned model to update.
        update_mask (google.protobuf.field_mask_pb2.FieldMask):
            Required. The list of fields to update.
    """

    tuned_model: gag_tuned_model.TunedModel = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_tuned_model.TunedModel,
    )
    update_mask: field_mask_pb2.FieldMask = proto.Field(
        proto.MESSAGE,
        number=2,
        message=field_mask_pb2.FieldMask,
    )


class DeleteTunedModelRequest(proto.Message):
    r"""Request to delete a TunedModel.

    Attributes:
        name (str):
            Required. The resource name of the model. Format:
            ``tunedModels/my-model-id``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))