
# === NexusCore/tools\exports\export_20250803_114325\combined_172.py ===

# === NexusCore/openenv\Lib\site-packages\IPython\core\shellapp.py ===
# encoding: utf-8
"""
A mixin for :class:`~IPython.core.application.Application` classes that
launch InteractiveShell instances, load extensions, etc.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import glob
from itertools import chain
import os
import sys
import typing as t

from traitlets.config.application import boolean_flag
from traitlets.config.configurable import Configurable
from traitlets.config.loader import Config
from IPython.core.application import SYSTEM_CONFIG_DIRS, ENV_CONFIG_DIRS
from IPython.utils.contexts import preserve_keys
from IPython.utils.path import filefind
from traitlets import (
    Unicode,
    Instance,
    List,
    Bool,
    CaselessStrEnum,
    observe,
    DottedObjectName,
    Undefined,
)
from IPython.terminal import pt_inputhooks

# -----------------------------------------------------------------------------
# Aliases and Flags
# -----------------------------------------------------------------------------

gui_keys = tuple(sorted(pt_inputhooks.backends) + sorted(pt_inputhooks.aliases))

shell_flags = {}

addflag = lambda *args: shell_flags.update(boolean_flag(*args))
addflag(
    "autoindent",
    "InteractiveShell.autoindent",
    "Turn on autoindenting.",
    "Turn off autoindenting.",
)
addflag(
    "automagic",
    "InteractiveShell.automagic",
    """Turn on the auto calling of magic commands. Type %%magic at the
        IPython  prompt  for  more information.""",
        'Turn off the auto calling of magic commands.'
)
addflag('pdb', 'InteractiveShell.pdb',
    "Enable auto calling the pdb debugger after every exception.",
    "Disable auto calling the pdb debugger after every exception."
)
addflag('pprint', 'PlainTextFormatter.pprint',
    "Enable auto pretty printing of results.",
    "Disable auto pretty printing of results."
)
addflag('color-info', 'InteractiveShell.color_info',
    """IPython can display information about objects via a set of functions,
    and optionally can use colors for this, syntax highlighting
    source code and various other elements. This is on by default, but can cause
    problems with some pagers. If you see such problems, you can disable the
    colours.""",
    "Disable using colors for info related things."
)
addflag('ignore-cwd', 'InteractiveShellApp.ignore_cwd',
        "Exclude the current working directory from sys.path",
        "Include the current working directory in sys.path",
)
nosep_config = Config()
nosep_config.InteractiveShell.separate_in = ''
nosep_config.InteractiveShell.separate_out = ''
nosep_config.InteractiveShell.separate_out2 = ''

shell_flags['nosep']=(nosep_config, "Eliminate all spacing between prompts.")
shell_flags['pylab'] = (
    {'InteractiveShellApp' : {'pylab' : 'auto'}},
    """Pre-load matplotlib and numpy for interactive use with
    the default matplotlib backend. The exact options available
    depend on what Matplotlib provides at runtime.""",
)
shell_flags['matplotlib'] = (
    {'InteractiveShellApp' : {'matplotlib' : 'auto'}},
    """Configure matplotlib for interactive use with
    the default matplotlib backend. The exact options available
    depend on what Matplotlib provides at runtime.""",
)

# it's possible we don't want short aliases for *all* of these:
shell_aliases = dict(
    autocall="InteractiveShell.autocall",
    colors="InteractiveShell.colors",
    theme="InteractiveShell.colors",
    logfile="InteractiveShell.logfile",
    logappend="InteractiveShell.logappend",
    c="InteractiveShellApp.code_to_run",
    m="InteractiveShellApp.module_to_run",
    ext="InteractiveShellApp.extra_extensions",
    gui='InteractiveShellApp.gui',
    pylab='InteractiveShellApp.pylab',
    matplotlib='InteractiveShellApp.matplotlib',
)
shell_aliases['cache-size'] = 'InteractiveShell.cache_size'


# -----------------------------------------------------------------------------
# Traitlets
# -----------------------------------------------------------------------------


class MatplotlibBackendCaselessStrEnum(CaselessStrEnum):
    """An enum of Matplotlib backend strings where the case should be ignored.

    Prior to Matplotlib 3.9.0 the list of valid backends is hardcoded in
    pylabtools.backends. After that, Matplotlib manages backends.

    The list of valid backends is determined when it is first needed to avoid
    wasting unnecessary initialisation time.
    """

    def __init__(
        self: CaselessStrEnum[t.Any],
        default_value: t.Any = Undefined,
        **kwargs: t.Any,
    ) -> None:
        super().__init__(None, default_value=default_value, **kwargs)

    def __getattribute__(self, name):
        if name == "values" and object.__getattribute__(self, name) is None:
            from IPython.core.pylabtools import _list_matplotlib_backends_and_gui_loops

            self.values = _list_matplotlib_backends_and_gui_loops()
        return object.__getattribute__(self, name)


#-----------------------------------------------------------------------------
# Main classes and functions
#-----------------------------------------------------------------------------

class InteractiveShellApp(Configurable):
    """A Mixin for applications that start InteractiveShell instances.

    Provides configurables for loading extensions and executing files
    as part of configuring a Shell environment.

    The following methods should be called by the :meth:`initialize` method
    of the subclass:

      - :meth:`init_path`
      - :meth:`init_shell` (to be implemented by the subclass)
      - :meth:`init_gui_pylab`
      - :meth:`init_extensions`
      - :meth:`init_code`
    """
    extensions = List(Unicode(),
        help="A list of dotted module names of IPython extensions to load."
    ).tag(config=True)

    extra_extensions = List(
        DottedObjectName(),
        help="""
        Dotted module name(s) of one or more IPython extensions to load.

        For specifying extra extensions to load on the command-line.

        .. versionadded:: 7.10
        """,
    ).tag(config=True)

    reraise_ipython_extension_failures = Bool(False,
        help="Reraise exceptions encountered loading IPython extensions?",
    ).tag(config=True)

    # Extensions that are always loaded (not configurable)
    default_extensions = List(Unicode(), [u'storemagic']).tag(config=False)

    hide_initial_ns = Bool(True,
        help="""Should variables loaded at startup (by startup files, exec_lines, etc.)
        be hidden from tools like %who?"""
    ).tag(config=True)

    exec_files = List(Unicode(),
        help="""List of files to run at IPython startup."""
    ).tag(config=True)
    exec_PYTHONSTARTUP = Bool(True,
        help="""Run the file referenced by the PYTHONSTARTUP environment
        variable at IPython startup."""
    ).tag(config=True)
    file_to_run = Unicode('',
        help="""A file to be run""").tag(config=True)

    exec_lines = List(Unicode(),
        help="""lines of code to run at IPython startup."""
    ).tag(config=True)
    code_to_run = Unicode("", help="Execute the given command string.").tag(config=True)
    module_to_run = Unicode("", help="Run the module as a script.").tag(config=True)
    gui = CaselessStrEnum(
        gui_keys,
        allow_none=True,
        help="Enable GUI event loop integration with any of {0}.".format(gui_keys),
    ).tag(config=True)
    matplotlib = MatplotlibBackendCaselessStrEnum(
        allow_none=True,
        help="""Configure matplotlib for interactive use with
        the default matplotlib backend. The exact options available
        depend on what Matplotlib provides at runtime.""",
    ).tag(config=True)
    pylab = MatplotlibBackendCaselessStrEnum(
        allow_none=True,
        help="""Pre-load matplotlib and numpy for interactive use,
        selecting a particular matplotlib backend and loop integration.
        The exact options available depend on what Matplotlib provides at runtime.
        """,
    ).tag(config=True)
    pylab_import_all = Bool(
        True,
        help="""If true, IPython will populate the user namespace with numpy, pylab, etc.
        and an ``import *`` is done from numpy and pylab, when using pylab mode.

        When False, pylab mode should not import any names into the user namespace.
        """,
    ).tag(config=True)
    ignore_cwd = Bool(
        False,
        help="""If True, IPython will not add the current working directory to sys.path.
        When False, the current working directory is added to sys.path, allowing imports
        of modules defined in the current directory."""
    ).tag(config=True)
    shell = Instance('IPython.core.interactiveshell.InteractiveShellABC',
                     allow_none=True)
    # whether interact-loop should start
    interact = Bool(True)

    user_ns = Instance(dict, args=None, allow_none=True)
    @observe('user_ns')
    def _user_ns_changed(self, change):
        if self.shell is not None:
            self.shell.user_ns = change['new']
            self.shell.init_user_ns()

    def init_path(self):
        """Add current working directory, '', to sys.path

        Unlike Python's default, we insert before the first `site-packages`
        or `dist-packages` directory,
        so that it is after the standard library.

        .. versionchanged:: 7.2
            Try to insert after the standard library, instead of first.
        .. versionchanged:: 8.0
            Allow optionally not including the current directory in sys.path
        """
        if '' in sys.path or self.ignore_cwd:
            return
        for idx, path in enumerate(sys.path):
            parent, last_part = os.path.split(path)
            if last_part in {'site-packages', 'dist-packages'}:
                break
        else:
            # no site-packages or dist-packages found (?!)
            # back to original behavior of inserting at the front
            idx = 0
        sys.path.insert(idx, '')

    def init_shell(self):
        raise NotImplementedError("Override in subclasses")

    def init_gui_pylab(self):
        """Enable GUI event loop integration, taking pylab into account."""
        enable = False
        shell = self.shell
        if self.pylab:
            enable = lambda key: shell.enable_pylab(key, import_all=self.pylab_import_all)
            key = self.pylab
        elif self.matplotlib:
            enable = shell.enable_matplotlib
            key = self.matplotlib
        elif self.gui:
            enable = shell.enable_gui
            key = self.gui

        if not enable:
            return

        try:
            r = enable(key)
        except ImportError:
            self.log.warning("Eventloop or matplotlib integration failed. Is matplotlib installed?")
            self.shell.showtraceback()
            return
        except Exception:
            self.log.warning("GUI event loop or pylab initialization failed")
            self.shell.showtraceback()
            return

        if isinstance(r, tuple):
            gui, backend = r[:2]
            self.log.info("Enabling GUI event loop integration, "
                      "eventloop=%s, matplotlib=%s", gui, backend)
            if key == "auto":
                print("Using matplotlib backend: %s" % backend)
        else:
            gui = r
            self.log.info("Enabling GUI event loop integration, "
                      "eventloop=%s", gui)

    def init_extensions(self):
        """Load all IPython extensions in IPythonApp.extensions.

        This uses the :meth:`ExtensionManager.load_extensions` to load all
        the extensions listed in ``self.extensions``.
        """
        try:
            self.log.debug("Loading IPython extensions...")
            extensions = (
                self.default_extensions + self.extensions + self.extra_extensions
            )
            for ext in extensions:
                try:
                    self.log.info("Loading IPython extension: %s", ext)
                    self.shell.extension_manager.load_extension(ext)
                except:
                    if self.reraise_ipython_extension_failures:
                        raise
                    msg = ("Error in loading extension: {ext}\n"
                           "Check your config files in {location}".format(
                               ext=ext,
                               location=self.profile_dir.location
                           ))
                    self.log.warning(msg, exc_info=True)
        except:
            if self.reraise_ipython_extension_failures:
                raise
            self.log.warning("Unknown error in loading extensions:", exc_info=True)

    def init_code(self):
        """run the pre-flight code, specified via exec_lines"""
        self._run_startup_files()
        self._run_exec_lines()
        self._run_exec_files()

        # Hide variables defined here from %who etc.
        if self.hide_initial_ns:
            self.shell.user_ns_hidden.update(self.shell.user_ns)

        # command-line execution (ipython -i script.py, ipython -m module)
        # should *not* be excluded from %whos
        self._run_cmd_line_code()
        self._run_module()

        # flush output, so itwon't be attached to the first cell
        sys.stdout.flush()
        sys.stderr.flush()
        self.shell._sys_modules_keys = set(sys.modules.keys())

    def _run_exec_lines(self):
        """Run lines of code in IPythonApp.exec_lines in the user's namespace."""
        if not self.exec_lines:
            return
        try:
            self.log.debug("Running code from IPythonApp.exec_lines...")
            for line in self.exec_lines:
                try:
                    self.log.info("Running code in user namespace: %s" %
                                  line)
                    self.shell.run_cell(line, store_history=False)
                except:
                    self.log.warning("Error in executing line in user "
                                  "namespace: %s" % line)
                    self.shell.showtraceback()
        except:
            self.log.warning("Unknown error in handling IPythonApp.exec_lines:")
            self.shell.showtraceback()

    def _exec_file(self, fname, shell_futures=False):
        try:
            full_filename = filefind(fname, [u'.', self.ipython_dir])
        except IOError:
            self.log.warning("File not found: %r"%fname)
            return
        # Make sure that the running script gets a proper sys.argv as if it
        # were run from a system shell.
        save_argv = sys.argv
        sys.argv = [full_filename] + self.extra_args[1:]
        try:
            if os.path.isfile(full_filename):
                self.log.info("Running file in user namespace: %s" %
                              full_filename)
                # Ensure that __file__ is always defined to match Python
                # behavior.
                with preserve_keys(self.shell.user_ns, '__file__'):
                    self.shell.user_ns['__file__'] = fname
                    if full_filename.endswith('.ipy') or full_filename.endswith('.ipynb'):
                        self.shell.safe_execfile_ipy(full_filename,
                                                     shell_futures=shell_futures)
                    else:
                        # default to python, even without extension
                        self.shell.safe_execfile(full_filename,
                                                 self.shell.user_ns,
                                                 shell_futures=shell_futures,
                                                 raise_exceptions=True)
        finally:
            sys.argv = save_argv

    def _run_startup_files(self):
        """Run files from profile startup directory"""
        startup_dirs = [self.profile_dir.startup_dir] + [
            os.path.join(p, 'startup') for p in chain(ENV_CONFIG_DIRS, SYSTEM_CONFIG_DIRS)
        ]
        startup_files = []

        if self.exec_PYTHONSTARTUP and os.environ.get('PYTHONSTARTUP', False) and \
                not (self.file_to_run or self.code_to_run or self.module_to_run):
            python_startup = os.environ['PYTHONSTARTUP']
            self.log.debug("Running PYTHONSTARTUP file %s...", python_startup)
            try:
                self._exec_file(python_startup)
            except:
                self.log.warning("Unknown error in handling PYTHONSTARTUP file %s:", python_startup)
                self.shell.showtraceback()
        for startup_dir in startup_dirs[::-1]:
            startup_files += glob.glob(os.path.join(startup_dir, '*.py'))
            startup_files += glob.glob(os.path.join(startup_dir, '*.ipy'))
        if not startup_files:
            return

        self.log.debug("Running startup files from %s...", startup_dir)
        try:
            for fname in sorted(startup_files):
                self._exec_file(fname)
        except:
            self.log.warning("Unknown error in handling startup files:")
            self.shell.showtraceback()

    def _run_exec_files(self):
        """Run files from IPythonApp.exec_files"""
        if not self.exec_files:
            return

        self.log.debug("Running files in IPythonApp.exec_files...")
        try:
            for fname in self.exec_files:
                self._exec_file(fname)
        except:
            self.log.warning("Unknown error in handling IPythonApp.exec_files:")
            self.shell.showtraceback()

    def _run_cmd_line_code(self):
        """Run code or file specified at the command-line"""
        if self.code_to_run:
            line = self.code_to_run
            try:
                self.log.info("Running code given at command line (c=): %s" %
                              line)
                self.shell.run_cell(line, store_history=False)
            except:
                self.log.warning("Error in executing line in user namespace: %s" %
                              line)
                self.shell.showtraceback()
                if not self.interact:
                    self.exit(1)

        # Like Python itself, ignore the second if the first of these is present
        elif self.file_to_run:
            fname = self.file_to_run
            if os.path.isdir(fname):
                fname = os.path.join(fname, "__main__.py")
            if not os.path.exists(fname):
                self.log.warning("File '%s' doesn't exist", fname)
                if not self.interact:
                    self.exit(2)
            try:
                self._exec_file(fname, shell_futures=True)
            except:
                self.shell.showtraceback(tb_offset=4)
                if not self.interact:
                    self.exit(1)

    def _run_module(self):
        """Run module specified at the command-line."""
        if self.module_to_run:
            # Make sure that the module gets a proper sys.argv as if it were
            # run using `python -m`.
            save_argv = sys.argv
            sys.argv = [sys.executable] + self.extra_args
            try:
                self.shell.safe_run_module(self.module_to_run,
                                           self.shell.user_ns)
            finally:
                sys.argv = save_argv

# === NexusCore/myenv\Lib\site-packages\pip\_internal\index\collector.py ===
"""
The main purpose of this module is to expose LinkCollector.collect_sources().
"""

import collections
import email.message
import functools
import itertools
import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from optparse import Values
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)

from pip._vendor import requests
from pip._vendor.requests import Response
from pip._vendor.requests.exceptions import RetryError, SSLError

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.link import Link
from pip._internal.models.search_scope import SearchScope
from pip._internal.network.session import PipSession
from pip._internal.network.utils import raise_for_status
from pip._internal.utils.filetypes import is_archive_file
from pip._internal.utils.misc import redact_auth_from_url
from pip._internal.vcs import vcs

from .sources import CandidatesFromPage, LinkSource, build_source

logger = logging.getLogger(__name__)

ResponseHeaders = MutableMapping[str, str]


def _match_vcs_scheme(url: str) -> Optional[str]:
    """Look for VCS schemes in the URL.

    Returns the matched VCS scheme, or None if there's no match.
    """
    for scheme in vcs.schemes:
        if url.lower().startswith(scheme) and url[len(scheme)] in "+:":
            return scheme
    return None


class _NotAPIContent(Exception):
    def __init__(self, content_type: str, request_desc: str) -> None:
        super().__init__(content_type, request_desc)
        self.content_type = content_type
        self.request_desc = request_desc


def _ensure_api_header(response: Response) -> None:
    """
    Check the Content-Type header to ensure the response contains a Simple
    API Response.

    Raises `_NotAPIContent` if the content type is not a valid content-type.
    """
    content_type = response.headers.get("Content-Type", "Unknown")

    content_type_l = content_type.lower()
    if content_type_l.startswith(
        (
            "text/html",
            "application/vnd.pypi.simple.v1+html",
            "application/vnd.pypi.simple.v1+json",
        )
    ):
        return

    raise _NotAPIContent(content_type, response.request.method)


class _NotHTTP(Exception):
    pass


def _ensure_api_response(url: str, session: PipSession) -> None:
    """
    Send a HEAD request to the URL, and ensure the response contains a simple
    API Response.

    Raises `_NotHTTP` if the URL is not available for a HEAD request, or
    `_NotAPIContent` if the content type is not a valid content type.
    """
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    if scheme not in {"http", "https"}:
        raise _NotHTTP()

    resp = session.head(url, allow_redirects=True)
    raise_for_status(resp)

    _ensure_api_header(resp)


def _get_simple_response(url: str, session: PipSession) -> Response:
    """Access an Simple API response with GET, and return the response.

    This consists of three parts:

    1. If the URL looks suspiciously like an archive, send a HEAD first to
       check the Content-Type is HTML or Simple API, to avoid downloading a
       large file. Raise `_NotHTTP` if the content type cannot be determined, or
       `_NotAPIContent` if it is not HTML or a Simple API.
    2. Actually perform the request. Raise HTTP exceptions on network failures.
    3. Check the Content-Type header to make sure we got a Simple API response,
       and raise `_NotAPIContent` otherwise.
    """
    if is_archive_file(Link(url).filename):
        _ensure_api_response(url, session=session)

    logger.debug("Getting page %s", redact_auth_from_url(url))

    resp = session.get(
        url,
        headers={
            "Accept": ", ".join(
                [
                    "application/vnd.pypi.simple.v1+json",
                    "application/vnd.pypi.simple.v1+html; q=0.1",
                    "text/html; q=0.01",
                ]
            ),
            # We don't want to blindly returned cached data for
            # /simple/, because authors generally expecting that
            # twine upload && pip install will function, but if
            # they've done a pip install in the last ~10 minutes
            # it won't. Thus by setting this to zero we will not
            # blindly use any cached data, however the benefit of
            # using max-age=0 instead of no-cache, is that we will
            # still support conditional requests, so we will still
            # minimize traffic sent in cases where the page hasn't
            # changed at all, we will just always incur the round
            # trip for the conditional GET now instead of only
            # once per 10 minutes.
            # For more information, please see pypa/pip#5670.
            "Cache-Control": "max-age=0",
        },
    )
    raise_for_status(resp)

    # The check for archives above only works if the url ends with
    # something that looks like an archive. However that is not a
    # requirement of an url. Unless we issue a HEAD request on every
    # url we cannot know ahead of time for sure if something is a
    # Simple API response or not. However we can check after we've
    # downloaded it.
    _ensure_api_header(resp)

    logger.debug(
        "Fetched page %s as %s",
        redact_auth_from_url(url),
        resp.headers.get("Content-Type", "Unknown"),
    )

    return resp


def _get_encoding_from_headers(headers: ResponseHeaders) -> Optional[str]:
    """Determine if we have any encoding information in our headers."""
    if headers and "Content-Type" in headers:
        m = email.message.Message()
        m["content-type"] = headers["Content-Type"]
        charset = m.get_param("charset")
        if charset:
            return str(charset)
    return None


class CacheablePageContent:
    def __init__(self, page: "IndexContent") -> None:
        assert page.cache_link_parsing
        self.page = page

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.page.url == other.page.url

    def __hash__(self) -> int:
        return hash(self.page.url)


class ParseLinks(Protocol):
    def __call__(self, page: "IndexContent") -> Iterable[Link]: ...


def with_cached_index_content(fn: ParseLinks) -> ParseLinks:
    """
    Given a function that parses an Iterable[Link] from an IndexContent, cache the
    function's result (keyed by CacheablePageContent), unless the IndexContent
    `page` has `page.cache_link_parsing == False`.
    """

    @functools.lru_cache(maxsize=None)
    def wrapper(cacheable_page: CacheablePageContent) -> List[Link]:
        return list(fn(cacheable_page.page))

    @functools.wraps(fn)
    def wrapper_wrapper(page: "IndexContent") -> List[Link]:
        if page.cache_link_parsing:
            return wrapper(CacheablePageContent(page))
        return list(fn(page))

    return wrapper_wrapper


@with_cached_index_content
def parse_links(page: "IndexContent") -> Iterable[Link]:
    """
    Parse a Simple API's Index Content, and yield its anchor elements as Link objects.
    """

    content_type_l = page.content_type.lower()
    if content_type_l.startswith("application/vnd.pypi.simple.v1+json"):
        data = json.loads(page.content)
        for file in data.get("files", []):
            link = Link.from_json(file, page.url)
            if link is None:
                continue
            yield link
        return

    parser = HTMLLinkParser(page.url)
    encoding = page.encoding or "utf-8"
    parser.feed(page.content.decode(encoding))

    url = page.url
    base_url = parser.base_url or url
    for anchor in parser.anchors:
        link = Link.from_element(anchor, page_url=url, base_url=base_url)
        if link is None:
            continue
        yield link


@dataclass(frozen=True)
class IndexContent:
    """Represents one response (or page), along with its URL.

    :param encoding: the encoding to decode the given content.
    :param url: the URL from which the HTML was downloaded.
    :param cache_link_parsing: whether links parsed from this page's url
                               should be cached. PyPI index urls should
                               have this set to False, for example.
    """

    content: bytes
    content_type: str
    encoding: Optional[str]
    url: str
    cache_link_parsing: bool = True

    def __str__(self) -> str:
        return redact_auth_from_url(self.url)


class HTMLLinkParser(HTMLParser):
    """
    HTMLParser that keeps the first base HREF and a list of all anchor
    elements' attributes.
    """

    def __init__(self, url: str) -> None:
        super().__init__(convert_charrefs=True)

        self.url: str = url
        self.base_url: Optional[str] = None
        self.anchors: List[Dict[str, Optional[str]]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "base" and self.base_url is None:
            href = self.get_href(attrs)
            if href is not None:
                self.base_url = href
        elif tag == "a":
            self.anchors.append(dict(attrs))

    def get_href(self, attrs: List[Tuple[str, Optional[str]]]) -> Optional[str]:
        for name, value in attrs:
            if name == "href":
                return value
        return None


def _handle_get_simple_fail(
    link: Link,
    reason: Union[str, Exception],
    meth: Optional[Callable[..., None]] = None,
) -> None:
    if meth is None:
        meth = logger.debug
    meth("Could not fetch URL %s: %s - skipping", link, reason)


def _make_index_content(
    response: Response, cache_link_parsing: bool = True
) -> IndexContent:
    encoding = _get_encoding_from_headers(response.headers)
    return IndexContent(
        response.content,
        response.headers["Content-Type"],
        encoding=encoding,
        url=response.url,
        cache_link_parsing=cache_link_parsing,
    )


def _get_index_content(link: Link, *, session: PipSession) -> Optional["IndexContent"]:
    url = link.url.split("#", 1)[0]

    # Check for VCS schemes that do not support lookup as web pages.
    vcs_scheme = _match_vcs_scheme(url)
    if vcs_scheme:
        logger.warning(
            "Cannot look at %s URL %s because it does not support lookup as web pages.",
            vcs_scheme,
            link,
        )
        return None

    # Tack index.html onto file:// URLs that point to directories
    scheme, _, path, _, _, _ = urllib.parse.urlparse(url)
    if scheme == "file" and os.path.isdir(urllib.request.url2pathname(path)):
        # add trailing slash if not present so urljoin doesn't trim
        # final segment
        if not url.endswith("/"):
            url += "/"
        # TODO: In the future, it would be nice if pip supported PEP 691
        #       style responses in the file:// URLs, however there's no
        #       standard file extension for application/vnd.pypi.simple.v1+json
        #       so we'll need to come up with something on our own.
        url = urllib.parse.urljoin(url, "index.html")
        logger.debug(" file: URL is directory, getting %s", url)

    try:
        resp = _get_simple_response(url, session=session)
    except _NotHTTP:
        logger.warning(
            "Skipping page %s because it looks like an archive, and cannot "
            "be checked by a HTTP HEAD request.",
            link,
        )
    except _NotAPIContent as exc:
        logger.warning(
            "Skipping page %s because the %s request got Content-Type: %s. "
            "The only supported Content-Types are application/vnd.pypi.simple.v1+json, "
            "application/vnd.pypi.simple.v1+html, and text/html",
            link,
            exc.request_desc,
            exc.content_type,
        )
    except NetworkConnectionError as exc:
        _handle_get_simple_fail(link, exc)
    except RetryError as exc:
        _handle_get_simple_fail(link, exc)
    except SSLError as exc:
        reason = "There was a problem confirming the ssl certificate: "
        reason += str(exc)
        _handle_get_simple_fail(link, reason, meth=logger.info)
    except requests.ConnectionError as exc:
        _handle_get_simple_fail(link, f"connection error: {exc}")
    except requests.Timeout:
        _handle_get_simple_fail(link, "timed out")
    else:
        return _make_index_content(resp, cache_link_parsing=link.cache_link_parsing)
    return None


class CollectedSources(NamedTuple):
    find_links: Sequence[Optional[LinkSource]]
    index_urls: Sequence[Optional[LinkSource]]


class LinkCollector:
    """
    Responsible for collecting Link objects from all configured locations,
    making network requests as needed.

    The class's main method is its collect_sources() method.
    """

    def __init__(
        self,
        session: PipSession,
        search_scope: SearchScope,
    ) -> None:
        self.search_scope = search_scope
        self.session = session

    @classmethod
    def create(
        cls,
        session: PipSession,
        options: Values,
        suppress_no_index: bool = False,
    ) -> "LinkCollector":
        """
        :param session: The Session to use to make requests.
        :param suppress_no_index: Whether to ignore the --no-index option
            when constructing the SearchScope object.
        """
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index and not suppress_no_index:
            logger.debug(
                "Ignoring indexes: %s",
                ",".join(redact_auth_from_url(url) for url in index_urls),
            )
            index_urls = []

        # Make sure find_links is a list before passing to create().
        find_links = options.find_links or []

        search_scope = SearchScope.create(
            find_links=find_links,
            index_urls=index_urls,
            no_index=options.no_index,
        )
        link_collector = LinkCollector(
            session=session,
            search_scope=search_scope,
        )
        return link_collector

    @property
    def find_links(self) -> List[str]:
        return self.search_scope.find_links

    def fetch_response(self, location: Link) -> Optional[IndexContent]:
        """
        Fetch an HTML page containing package links.
        """
        return _get_index_content(location, session=self.session)

    def collect_sources(
        self,
        project_name: str,
        candidates_from_page: CandidatesFromPage,
    ) -> CollectedSources:
        # The OrderedDict calls deduplicate sources by URL.
        index_url_sources = collections.OrderedDict(
            build_source(
                loc,
                candidates_from_page=candidates_from_page,
                page_validator=self.session.is_secure_origin,
                expand_dir=False,
                cache_link_parsing=False,
                project_name=project_name,
            )
            for loc in self.search_scope.get_index_urls_locations(project_name)
        ).values()
        find_links_sources = collections.OrderedDict(
            build_source(
                loc,
                candidates_from_page=candidates_from_page,
                page_validator=self.session.is_secure_origin,
                expand_dir=True,
                cache_link_parsing=True,
                project_name=project_name,
            )
            for loc in self.find_links
        ).values()

        if logger.isEnabledFor(logging.DEBUG):
            lines = [
                f"* {s.link}"
                for s in itertools.chain(find_links_sources, index_url_sources)
                if s is not None and s.link is not None
            ]
            lines = [
                f"{len(lines)} location(s) to search "
                f"for versions of {project_name}:"
            ] + lines
            logger.debug("\n".join(lines))

        return CollectedSources(
            find_links=list(find_links_sources),
            index_urls=list(index_url_sources),
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\common_utils.py ===
import json
import os
from typing import Any, Callable, Dict, Optional, Union

import httpx
from openai import AsyncAzureOpenAI, AzureOpenAI

import litellm
from litellm._logging import verbose_logger
from litellm.caching.caching import DualCache
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.llms.openai.common_utils import BaseOpenAILLM
from litellm.secret_managers.get_azure_ad_token_provider import (
    get_azure_ad_token_provider,
)
from litellm.secret_managers.main import get_secret_str

azure_ad_cache = DualCache()


class AzureOpenAIError(BaseLLMException):
    def __init__(
        self,
        status_code,
        message,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
        headers: Optional[Union[httpx.Headers, dict]] = None,
        body: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status_code,
            message=message,
            request=request,
            response=response,
            headers=headers,
            body=body,
        )


def process_azure_headers(headers: Union[httpx.Headers, dict]) -> dict:
    openai_headers = {}
    if "x-ratelimit-limit-requests" in headers:
        openai_headers["x-ratelimit-limit-requests"] = headers[
            "x-ratelimit-limit-requests"
        ]
    if "x-ratelimit-remaining-requests" in headers:
        openai_headers["x-ratelimit-remaining-requests"] = headers[
            "x-ratelimit-remaining-requests"
        ]
    if "x-ratelimit-limit-tokens" in headers:
        openai_headers["x-ratelimit-limit-tokens"] = headers["x-ratelimit-limit-tokens"]
    if "x-ratelimit-remaining-tokens" in headers:
        openai_headers["x-ratelimit-remaining-tokens"] = headers[
            "x-ratelimit-remaining-tokens"
        ]
    llm_response_headers = {
        "{}-{}".format("llm_provider", k): v for k, v in headers.items()
    }

    return {**llm_response_headers, **openai_headers}


def get_azure_ad_token_from_entra_id(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    scope: str = "https://cognitiveservices.azure.com/.default",
) -> Callable[[], str]:
    """
    Get Azure AD token provider from `client_id`, `client_secret`, and `tenant_id`

    Args:
        tenant_id: str
        client_id: str
        client_secret: str
        scope: str

    Returns:
        callable that returns a bearer token.
    """
    from azure.identity import ClientSecretCredential, get_bearer_token_provider

    verbose_logger.debug("Getting Azure AD Token from Entra ID")

    if tenant_id.startswith("os.environ/"):
        _tenant_id = get_secret_str(tenant_id)
    else:
        _tenant_id = tenant_id

    if client_id.startswith("os.environ/"):
        _client_id = get_secret_str(client_id)
    else:
        _client_id = client_id

    if client_secret.startswith("os.environ/"):
        _client_secret = get_secret_str(client_secret)
    else:
        _client_secret = client_secret

    verbose_logger.debug(
        "tenant_id %s, client_id %s, client_secret %s",
        _tenant_id,
        _client_id,
        _client_secret,
    )
    if _tenant_id is None or _client_id is None or _client_secret is None:
        raise ValueError("tenant_id, client_id, and client_secret must be provided")
    credential = ClientSecretCredential(_tenant_id, _client_id, _client_secret)

    verbose_logger.debug("credential %s", credential)

    token_provider = get_bearer_token_provider(credential, scope)

    verbose_logger.debug("token_provider %s", token_provider)

    return token_provider


def get_azure_ad_token_from_username_password(
    client_id: str,
    azure_username: str,
    azure_password: str,
    scope: str = "https://cognitiveservices.azure.com/.default",
) -> Callable[[], str]:
    """
    Get Azure AD token provider from `client_id`, `azure_username`, and `azure_password`

    Args:
        client_id: str
        azure_username: str
        azure_password: str
        scope: str

    Returns:
        callable that returns a bearer token.
    """
    from azure.identity import UsernamePasswordCredential, get_bearer_token_provider

    verbose_logger.debug(
        "client_id %s, azure_username %s, azure_password %s",
        client_id,
        azure_username,
        azure_password,
    )
    credential = UsernamePasswordCredential(
        client_id=client_id,
        username=azure_username,
        password=azure_password,
    )

    verbose_logger.debug("credential %s", credential)

    token_provider = get_bearer_token_provider(credential, scope)

    verbose_logger.debug("token_provider %s", token_provider)

    return token_provider


def get_azure_ad_token_from_oidc(
    azure_ad_token: str,
    azure_client_id: Optional[str],
    azure_tenant_id: Optional[str],
    scope: Optional[str] = None,
) -> str:
    """
    Get Azure AD token from OIDC token

    Args:
        azure_ad_token: str
        azure_client_id: Optional[str]
        azure_tenant_id: Optional[str]
        scope: str

    Returns:
        `azure_ad_token_access_token` - str
    """
    if scope is None:
        scope = "https://cognitiveservices.azure.com/.default"
    azure_authority_host = os.getenv(
        "AZURE_AUTHORITY_HOST", "https://login.microsoftonline.com"
    )
    azure_client_id = azure_client_id or os.getenv("AZURE_CLIENT_ID")
    azure_tenant_id = azure_tenant_id or os.getenv("AZURE_TENANT_ID")
    if azure_client_id is None or azure_tenant_id is None:
        raise AzureOpenAIError(
            status_code=422,
            message="AZURE_CLIENT_ID and AZURE_TENANT_ID must be set",
        )

    oidc_token = get_secret_str(azure_ad_token)

    if oidc_token is None:
        raise AzureOpenAIError(
            status_code=401,
            message="OIDC token could not be retrieved from secret manager.",
        )

    azure_ad_token_cache_key = json.dumps(
        {
            "azure_client_id": azure_client_id,
            "azure_tenant_id": azure_tenant_id,
            "azure_authority_host": azure_authority_host,
            "oidc_token": oidc_token,
        }
    )

    azure_ad_token_access_token = azure_ad_cache.get_cache(azure_ad_token_cache_key)
    if azure_ad_token_access_token is not None:
        return azure_ad_token_access_token

    client = litellm.module_level_client

    req_token = client.post(
        f"{azure_authority_host}/{azure_tenant_id}/oauth2/v2.0/token",
        data={
            "client_id": azure_client_id,
            "grant_type": "client_credentials",
            "scope": scope,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": oidc_token,
        },
    )

    if req_token.status_code != 200:
        raise AzureOpenAIError(
            status_code=req_token.status_code,
            message=req_token.text,
        )

    azure_ad_token_json = req_token.json()
    azure_ad_token_access_token = azure_ad_token_json.get("access_token", None)
    azure_ad_token_expires_in = azure_ad_token_json.get("expires_in", None)

    if azure_ad_token_access_token is None:
        raise AzureOpenAIError(
            status_code=422, message="Azure AD Token access_token not returned"
        )

    if azure_ad_token_expires_in is None:
        raise AzureOpenAIError(
            status_code=422, message="Azure AD Token expires_in not returned"
        )

    azure_ad_cache.set_cache(
        key=azure_ad_token_cache_key,
        value=azure_ad_token_access_token,
        ttl=azure_ad_token_expires_in,
    )

    return azure_ad_token_access_token


def select_azure_base_url_or_endpoint(azure_client_params: dict):
    azure_endpoint = azure_client_params.get("azure_endpoint", None)
    if azure_endpoint is not None:
        # see : https://github.com/openai/openai-python/blob/3d61ed42aba652b547029095a7eb269ad4e1e957/src/openai/lib/azure.py#L192
        if "/openai/deployments" in azure_endpoint:
            # this is base_url, not an azure_endpoint
            azure_client_params["base_url"] = azure_endpoint
            azure_client_params.pop("azure_endpoint")

    return azure_client_params


class BaseAzureLLM(BaseOpenAILLM):
    def get_azure_openai_client(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str] = None,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
        _is_async: bool = False,
        model: Optional[str] = None,
    ) -> Optional[Union[AzureOpenAI, AsyncAzureOpenAI]]:
        openai_client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None
        client_initialization_params: dict = locals()
        client_initialization_params["is_async"] = _is_async
        if client is None:
            cached_client = self.get_cached_openai_client(
                client_initialization_params=client_initialization_params,
                client_type="azure",
            )
            if cached_client:
                if isinstance(cached_client, AzureOpenAI) or isinstance(
                    cached_client, AsyncAzureOpenAI
                ):
                    return cached_client

            azure_client_params = self.initialize_azure_sdk_client(
                litellm_params=litellm_params or {},
                api_key=api_key,
                api_base=api_base,
                model_name=model,
                api_version=api_version,
                is_async=_is_async,
            )
            if _is_async is True:
                openai_client = AsyncAzureOpenAI(**azure_client_params)
            else:
                openai_client = AzureOpenAI(**azure_client_params)  # type: ignore
        else:
            openai_client = client
            if api_version is not None and isinstance(
                openai_client._custom_query, dict
            ):
                # set api_version to version passed by user
                openai_client._custom_query.setdefault("api-version", api_version)

        # save client in-memory cache
        self.set_cached_openai_client(
            openai_client=openai_client,
            client_initialization_params=client_initialization_params,
            client_type="azure",
        )
        return openai_client

    def initialize_azure_sdk_client(
        self,
        litellm_params: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        model_name: Optional[str],
        api_version: Optional[str],
        is_async: bool,
    ) -> dict:
        azure_ad_token_provider = litellm_params.get("azure_ad_token_provider")
        # If we have api_key, then we have higher priority
        azure_ad_token = litellm_params.get("azure_ad_token")
        tenant_id = litellm_params.get("tenant_id", os.getenv("AZURE_TENANT_ID"))
        client_id = litellm_params.get("client_id", os.getenv("AZURE_CLIENT_ID"))
        client_secret = litellm_params.get(
            "client_secret", os.getenv("AZURE_CLIENT_SECRET")
        )
        azure_username = litellm_params.get(
            "azure_username", os.getenv("AZURE_USERNAME")
        )
        azure_password = litellm_params.get(
            "azure_password", os.getenv("AZURE_PASSWORD")
        )
        scope = litellm_params.get(
            "azure_scope",
            os.getenv("AZURE_SCOPE", "https://cognitiveservices.azure.com/.default"),
        )
        if scope is None:
            scope = "https://cognitiveservices.azure.com/.default"
        max_retries = litellm_params.get("max_retries")
        timeout = litellm_params.get("timeout")
        if (
            not api_key
            and azure_ad_token_provider is None
            and tenant_id
            and client_id
            and client_secret
        ):
            verbose_logger.debug(
                "Using Azure AD Token Provider from Entra ID for Azure Auth"
            )
            azure_ad_token_provider = get_azure_ad_token_from_entra_id(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
            )
        if (
            azure_ad_token_provider is None
            and azure_username
            and azure_password
            and client_id
        ):
            verbose_logger.debug("Using Azure Username and Password for Azure Auth")
            azure_ad_token_provider = get_azure_ad_token_from_username_password(
                azure_username=azure_username,
                azure_password=azure_password,
                client_id=client_id,
                scope=scope,
            )

        if azure_ad_token is not None and azure_ad_token.startswith("oidc/"):
            verbose_logger.debug("Using Azure OIDC Token for Azure Auth")
            azure_ad_token = get_azure_ad_token_from_oidc(
                azure_ad_token=azure_ad_token,
                azure_client_id=client_id,
                azure_tenant_id=tenant_id,
                scope=scope,
            )
        elif (
            not api_key
            and azure_ad_token_provider is None
            and litellm.enable_azure_ad_token_refresh is True
        ):
            verbose_logger.debug(
                "Using Azure AD token provider based on Service Principal with Secret workflow for Azure Auth"
            )
            try:
                azure_ad_token_provider = get_azure_ad_token_provider(azure_scope=scope)
            except ValueError:
                verbose_logger.debug("Azure AD Token Provider could not be used.")
        if api_version is None:
            api_version = os.getenv(
                "AZURE_API_VERSION", litellm.AZURE_DEFAULT_API_VERSION
            )

        _api_key = api_key
        if _api_key is not None and isinstance(_api_key, str):
            # only show first 5 chars of api_key
            _api_key = _api_key[:8] + "*" * 15
        verbose_logger.debug(
            f"Initializing Azure OpenAI Client for {model_name}, Api Base: {str(api_base)}, Api Key:{_api_key}"
        )
        azure_client_params = {
            "api_key": api_key,
            "azure_endpoint": api_base,
            "api_version": api_version,
            "azure_ad_token": azure_ad_token,
            "azure_ad_token_provider": azure_ad_token_provider,
        }
        # init http client + SSL Verification settings
        if is_async is True:
            azure_client_params["http_client"] = self._get_async_http_client()
        else:
            azure_client_params["http_client"] = self._get_sync_http_client()

        if max_retries is not None:
            azure_client_params["max_retries"] = max_retries
        if timeout is not None:
            azure_client_params["timeout"] = timeout

        if azure_ad_token_provider is not None:
            azure_client_params["azure_ad_token_provider"] = azure_ad_token_provider
        # this decides if we should set azure_endpoint or base_url on Azure OpenAI Client
        # required to support GPT-4 vision enhancements, since base_url needs to be set on Azure OpenAI Client

        azure_client_params = select_azure_base_url_or_endpoint(
            azure_client_params=azure_client_params
        )

        return azure_client_params

    def _init_azure_client_for_cloudflare_ai_gateway(
        self,
        api_base: str,
        model: str,
        api_version: str,
        max_retries: int,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        api_key: Optional[str],
        azure_ad_token: Optional[str],
        azure_ad_token_provider: Optional[Callable[[], str]],
        acompletion: bool,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
    ) -> Union[AzureOpenAI, AsyncAzureOpenAI]:
        ## build base url - assume api base includes resource name
        tenant_id = litellm_params.get("tenant_id", os.getenv("AZURE_TENANT_ID"))
        client_id = litellm_params.get("client_id", os.getenv("AZURE_CLIENT_ID"))
        scope = litellm_params.get(
            "azure_scope",
            os.getenv("AZURE_SCOPE", "https://cognitiveservices.azure.com/.default"),
        )
        if client is None:
            if not api_base.endswith("/"):
                api_base += "/"
            api_base += f"{model}"

            azure_client_params: Dict[str, Any] = {
                "api_version": api_version,
                "base_url": f"{api_base}",
                "http_client": litellm.client_session,
                "max_retries": max_retries,
                "timeout": timeout,
            }
            if api_key is not None:
                azure_client_params["api_key"] = api_key
            elif azure_ad_token is not None:
                if azure_ad_token.startswith("oidc/"):
                    azure_ad_token = get_azure_ad_token_from_oidc(
                        azure_ad_token=azure_ad_token,
                        azure_client_id=client_id,
                        azure_tenant_id=tenant_id,
                        scope=scope,
                    )

                azure_client_params["azure_ad_token"] = azure_ad_token
            if azure_ad_token_provider is not None:
                azure_client_params["azure_ad_token_provider"] = azure_ad_token_provider

            if acompletion is True:
                client = AsyncAzureOpenAI(**azure_client_params)  # type: ignore
            else:
                client = AzureOpenAI(**azure_client_params)  # type: ignore
        return client

# === NexusCore/openenv\Lib\site-packages\pip\_internal\index\collector.py ===
"""
The main purpose of this module is to expose LinkCollector.collect_sources().
"""

import collections
import email.message
import functools
import itertools
import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from optparse import Values
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    MutableMapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    Union,
)

from pip._vendor import requests
from pip._vendor.requests import Response
from pip._vendor.requests.exceptions import RetryError, SSLError

from pip._internal.exceptions import NetworkConnectionError
from pip._internal.models.link import Link
from pip._internal.models.search_scope import SearchScope
from pip._internal.network.session import PipSession
from pip._internal.network.utils import raise_for_status
from pip._internal.utils.filetypes import is_archive_file
from pip._internal.utils.misc import redact_auth_from_url
from pip._internal.vcs import vcs

from .sources import CandidatesFromPage, LinkSource, build_source

logger = logging.getLogger(__name__)

ResponseHeaders = MutableMapping[str, str]


def _match_vcs_scheme(url: str) -> Optional[str]:
    """Look for VCS schemes in the URL.

    Returns the matched VCS scheme, or None if there's no match.
    """
    for scheme in vcs.schemes:
        if url.lower().startswith(scheme) and url[len(scheme)] in "+:":
            return scheme
    return None


class _NotAPIContent(Exception):
    def __init__(self, content_type: str, request_desc: str) -> None:
        super().__init__(content_type, request_desc)
        self.content_type = content_type
        self.request_desc = request_desc


def _ensure_api_header(response: Response) -> None:
    """
    Check the Content-Type header to ensure the response contains a Simple
    API Response.

    Raises `_NotAPIContent` if the content type is not a valid content-type.
    """
    content_type = response.headers.get("Content-Type", "Unknown")

    content_type_l = content_type.lower()
    if content_type_l.startswith(
        (
            "text/html",
            "application/vnd.pypi.simple.v1+html",
            "application/vnd.pypi.simple.v1+json",
        )
    ):
        return

    raise _NotAPIContent(content_type, response.request.method)


class _NotHTTP(Exception):
    pass


def _ensure_api_response(url: str, session: PipSession) -> None:
    """
    Send a HEAD request to the URL, and ensure the response contains a simple
    API Response.

    Raises `_NotHTTP` if the URL is not available for a HEAD request, or
    `_NotAPIContent` if the content type is not a valid content type.
    """
    scheme, netloc, path, query, fragment = urllib.parse.urlsplit(url)
    if scheme not in {"http", "https"}:
        raise _NotHTTP()

    resp = session.head(url, allow_redirects=True)
    raise_for_status(resp)

    _ensure_api_header(resp)


def _get_simple_response(url: str, session: PipSession) -> Response:
    """Access an Simple API response with GET, and return the response.

    This consists of three parts:

    1. If the URL looks suspiciously like an archive, send a HEAD first to
       check the Content-Type is HTML or Simple API, to avoid downloading a
       large file. Raise `_NotHTTP` if the content type cannot be determined, or
       `_NotAPIContent` if it is not HTML or a Simple API.
    2. Actually perform the request. Raise HTTP exceptions on network failures.
    3. Check the Content-Type header to make sure we got a Simple API response,
       and raise `_NotAPIContent` otherwise.
    """
    if is_archive_file(Link(url).filename):
        _ensure_api_response(url, session=session)

    logger.debug("Getting page %s", redact_auth_from_url(url))

    resp = session.get(
        url,
        headers={
            "Accept": ", ".join(
                [
                    "application/vnd.pypi.simple.v1+json",
                    "application/vnd.pypi.simple.v1+html; q=0.1",
                    "text/html; q=0.01",
                ]
            ),
            # We don't want to blindly returned cached data for
            # /simple/, because authors generally expecting that
            # twine upload && pip install will function, but if
            # they've done a pip install in the last ~10 minutes
            # it won't. Thus by setting this to zero we will not
            # blindly use any cached data, however the benefit of
            # using max-age=0 instead of no-cache, is that we will
            # still support conditional requests, so we will still
            # minimize traffic sent in cases where the page hasn't
            # changed at all, we will just always incur the round
            # trip for the conditional GET now instead of only
            # once per 10 minutes.
            # For more information, please see pypa/pip#5670.
            "Cache-Control": "max-age=0",
        },
    )
    raise_for_status(resp)

    # The check for archives above only works if the url ends with
    # something that looks like an archive. However that is not a
    # requirement of an url. Unless we issue a HEAD request on every
    # url we cannot know ahead of time for sure if something is a
    # Simple API response or not. However we can check after we've
    # downloaded it.
    _ensure_api_header(resp)

    logger.debug(
        "Fetched page %s as %s",
        redact_auth_from_url(url),
        resp.headers.get("Content-Type", "Unknown"),
    )

    return resp


def _get_encoding_from_headers(headers: ResponseHeaders) -> Optional[str]:
    """Determine if we have any encoding information in our headers."""
    if headers and "Content-Type" in headers:
        m = email.message.Message()
        m["content-type"] = headers["Content-Type"]
        charset = m.get_param("charset")
        if charset:
            return str(charset)
    return None


class CacheablePageContent:
    def __init__(self, page: "IndexContent") -> None:
        assert page.cache_link_parsing
        self.page = page

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.page.url == other.page.url

    def __hash__(self) -> int:
        return hash(self.page.url)


class ParseLinks(Protocol):
    def __call__(self, page: "IndexContent") -> Iterable[Link]: ...


def with_cached_index_content(fn: ParseLinks) -> ParseLinks:
    """
    Given a function that parses an Iterable[Link] from an IndexContent, cache the
    function's result (keyed by CacheablePageContent), unless the IndexContent
    `page` has `page.cache_link_parsing == False`.
    """

    @functools.lru_cache(maxsize=None)
    def wrapper(cacheable_page: CacheablePageContent) -> List[Link]:
        return list(fn(cacheable_page.page))

    @functools.wraps(fn)
    def wrapper_wrapper(page: "IndexContent") -> List[Link]:
        if page.cache_link_parsing:
            return wrapper(CacheablePageContent(page))
        return list(fn(page))

    return wrapper_wrapper


@with_cached_index_content
def parse_links(page: "IndexContent") -> Iterable[Link]:
    """
    Parse a Simple API's Index Content, and yield its anchor elements as Link objects.
    """

    content_type_l = page.content_type.lower()
    if content_type_l.startswith("application/vnd.pypi.simple.v1+json"):
        data = json.loads(page.content)
        for file in data.get("files", []):
            link = Link.from_json(file, page.url)
            if link is None:
                continue
            yield link
        return

    parser = HTMLLinkParser(page.url)
    encoding = page.encoding or "utf-8"
    parser.feed(page.content.decode(encoding))

    url = page.url
    base_url = parser.base_url or url
    for anchor in parser.anchors:
        link = Link.from_element(anchor, page_url=url, base_url=base_url)
        if link is None:
            continue
        yield link


@dataclass(frozen=True)
class IndexContent:
    """Represents one response (or page), along with its URL.

    :param encoding: the encoding to decode the given content.
    :param url: the URL from which the HTML was downloaded.
    :param cache_link_parsing: whether links parsed from this page's url
                               should be cached. PyPI index urls should
                               have this set to False, for example.
    """

    content: bytes
    content_type: str
    encoding: Optional[str]
    url: str
    cache_link_parsing: bool = True

    def __str__(self) -> str:
        return redact_auth_from_url(self.url)


class HTMLLinkParser(HTMLParser):
    """
    HTMLParser that keeps the first base HREF and a list of all anchor
    elements' attributes.
    """

    def __init__(self, url: str) -> None:
        super().__init__(convert_charrefs=True)

        self.url: str = url
        self.base_url: Optional[str] = None
        self.anchors: List[Dict[str, Optional[str]]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag == "base" and self.base_url is None:
            href = self.get_href(attrs)
            if href is not None:
                self.base_url = href
        elif tag == "a":
            self.anchors.append(dict(attrs))

    def get_href(self, attrs: List[Tuple[str, Optional[str]]]) -> Optional[str]:
        for name, value in attrs:
            if name == "href":
                return value
        return None


def _handle_get_simple_fail(
    link: Link,
    reason: Union[str, Exception],
    meth: Optional[Callable[..., None]] = None,
) -> None:
    if meth is None:
        meth = logger.debug
    meth("Could not fetch URL %s: %s - skipping", link, reason)


def _make_index_content(
    response: Response, cache_link_parsing: bool = True
) -> IndexContent:
    encoding = _get_encoding_from_headers(response.headers)
    return IndexContent(
        response.content,
        response.headers["Content-Type"],
        encoding=encoding,
        url=response.url,
        cache_link_parsing=cache_link_parsing,
    )


def _get_index_content(link: Link, *, session: PipSession) -> Optional["IndexContent"]:
    url = link.url.split("#", 1)[0]

    # Check for VCS schemes that do not support lookup as web pages.
    vcs_scheme = _match_vcs_scheme(url)
    if vcs_scheme:
        logger.warning(
            "Cannot look at %s URL %s because it does not support lookup as web pages.",
            vcs_scheme,
            link,
        )
        return None

    # Tack index.html onto file:// URLs that point to directories
    scheme, _, path, _, _, _ = urllib.parse.urlparse(url)
    if scheme == "file" and os.path.isdir(urllib.request.url2pathname(path)):
        # add trailing slash if not present so urljoin doesn't trim
        # final segment
        if not url.endswith("/"):
            url += "/"
        # TODO: In the future, it would be nice if pip supported PEP 691
        #       style responses in the file:// URLs, however there's no
        #       standard file extension for application/vnd.pypi.simple.v1+json
        #       so we'll need to come up with something on our own.
        url = urllib.parse.urljoin(url, "index.html")
        logger.debug(" file: URL is directory, getting %s", url)

    try:
        resp = _get_simple_response(url, session=session)
    except _NotHTTP:
        logger.warning(
            "Skipping page %s because it looks like an archive, and cannot "
            "be checked by a HTTP HEAD request.",
            link,
        )
    except _NotAPIContent as exc:
        logger.warning(
            "Skipping page %s because the %s request got Content-Type: %s. "
            "The only supported Content-Types are application/vnd.pypi.simple.v1+json, "
            "application/vnd.pypi.simple.v1+html, and text/html",
            link,
            exc.request_desc,
            exc.content_type,
        )
    except NetworkConnectionError as exc:
        _handle_get_simple_fail(link, exc)
    except RetryError as exc:
        _handle_get_simple_fail(link, exc)
    except SSLError as exc:
        reason = "There was a problem confirming the ssl certificate: "
        reason += str(exc)
        _handle_get_simple_fail(link, reason, meth=logger.info)
    except requests.ConnectionError as exc:
        _handle_get_simple_fail(link, f"connection error: {exc}")
    except requests.Timeout:
        _handle_get_simple_fail(link, "timed out")
    else:
        return _make_index_content(resp, cache_link_parsing=link.cache_link_parsing)
    return None


class CollectedSources(NamedTuple):
    find_links: Sequence[Optional[LinkSource]]
    index_urls: Sequence[Optional[LinkSource]]


class LinkCollector:
    """
    Responsible for collecting Link objects from all configured locations,
    making network requests as needed.

    The class's main method is its collect_sources() method.
    """

    def __init__(
        self,
        session: PipSession,
        search_scope: SearchScope,
    ) -> None:
        self.search_scope = search_scope
        self.session = session

    @classmethod
    def create(
        cls,
        session: PipSession,
        options: Values,
        suppress_no_index: bool = False,
    ) -> "LinkCollector":
        """
        :param session: The Session to use to make requests.
        :param suppress_no_index: Whether to ignore the --no-index option
            when constructing the SearchScope object.
        """
        index_urls = [options.index_url] + options.extra_index_urls
        if options.no_index and not suppress_no_index:
            logger.debug(
                "Ignoring indexes: %s",
                ",".join(redact_auth_from_url(url) for url in index_urls),
            )
            index_urls = []

        # Make sure find_links is a list before passing to create().
        find_links = options.find_links or []

        search_scope = SearchScope.create(
            find_links=find_links,
            index_urls=index_urls,
            no_index=options.no_index,
        )
        link_collector = LinkCollector(
            session=session,
            search_scope=search_scope,
        )
        return link_collector

    @property
    def find_links(self) -> List[str]:
        return self.search_scope.find_links

    def fetch_response(self, location: Link) -> Optional[IndexContent]:
        """
        Fetch an HTML page containing package links.
        """
        return _get_index_content(location, session=self.session)

    def collect_sources(
        self,
        project_name: str,
        candidates_from_page: CandidatesFromPage,
    ) -> CollectedSources:
        # The OrderedDict calls deduplicate sources by URL.
        index_url_sources = collections.OrderedDict(
            build_source(
                loc,
                candidates_from_page=candidates_from_page,
                page_validator=self.session.is_secure_origin,
                expand_dir=False,
                cache_link_parsing=False,
                project_name=project_name,
            )
            for loc in self.search_scope.get_index_urls_locations(project_name)
        ).values()
        find_links_sources = collections.OrderedDict(
            build_source(
                loc,
                candidates_from_page=candidates_from_page,
                page_validator=self.session.is_secure_origin,
                expand_dir=True,
                cache_link_parsing=True,
                project_name=project_name,
            )
            for loc in self.find_links
        ).values()

        if logger.isEnabledFor(logging.DEBUG):
            lines = [
                f"* {s.link}"
                for s in itertools.chain(find_links_sources, index_url_sources)
                if s is not None and s.link is not None
            ]
            lines = [
                f"{len(lines)} location(s) to search "
                f"for versions of {project_name}:"
            ] + lines
            logger.debug("\n".join(lines))

        return CollectedSources(
            find_links=list(find_links_sources),
            index_urls=list(index_url_sources),
        )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\scrollable_pane.py ===
from __future__ import annotations

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.key_binding import KeyBindingsBase
from prompt_toolkit.mouse_events import MouseEvent

from .containers import Container, ScrollOffsets
from .dimension import AnyDimension, Dimension, sum_layout_dimensions, to_dimension
from .mouse_handlers import MouseHandler, MouseHandlers
from .screen import Char, Screen, WritePosition

__all__ = ["ScrollablePane"]

# Never go beyond this height, because performance will degrade.
MAX_AVAILABLE_HEIGHT = 10_000


class ScrollablePane(Container):
    """
    Container widget that exposes a larger virtual screen to its content and
    displays it in a vertical scrollbale region.

    Typically this is wrapped in a large `HSplit` container. Make sure in that
    case to not specify a `height` dimension of the `HSplit`, so that it will
    scale according to the content.

    .. note::

        If you want to display a completion menu for widgets in this
        `ScrollablePane`, then it's still a good practice to use a
        `FloatContainer` with a `CompletionsMenu` in a `Float` at the top-level
        of the layout hierarchy, rather then nesting a `FloatContainer` in this
        `ScrollablePane`. (Otherwise, it's possible that the completion menu
        is clipped.)

    :param content: The content container.
    :param scrolloffset: Try to keep the cursor within this distance from the
        top/bottom (left/right offset is not used).
    :param keep_cursor_visible: When `True`, automatically scroll the pane so
        that the cursor (of the focused window) is always visible.
    :param keep_focused_window_visible: When `True`, automatically scroll the
        pane so that the focused window is visible, or as much visible as
        possible if it doesn't completely fit the screen.
    :param max_available_height: Always constraint the height to this amount
        for performance reasons.
    :param width: When given, use this width instead of looking at the children.
    :param height: When given, use this height instead of looking at the children.
    :param show_scrollbar: When `True` display a scrollbar on the right.
    """

    def __init__(
        self,
        content: Container,
        scroll_offsets: ScrollOffsets | None = None,
        keep_cursor_visible: FilterOrBool = True,
        keep_focused_window_visible: FilterOrBool = True,
        max_available_height: int = MAX_AVAILABLE_HEIGHT,
        width: AnyDimension = None,
        height: AnyDimension = None,
        show_scrollbar: FilterOrBool = True,
        display_arrows: FilterOrBool = True,
        up_arrow_symbol: str = "^",
        down_arrow_symbol: str = "v",
    ) -> None:
        self.content = content
        self.scroll_offsets = scroll_offsets or ScrollOffsets(top=1, bottom=1)
        self.keep_cursor_visible = to_filter(keep_cursor_visible)
        self.keep_focused_window_visible = to_filter(keep_focused_window_visible)
        self.max_available_height = max_available_height
        self.width = width
        self.height = height
        self.show_scrollbar = to_filter(show_scrollbar)
        self.display_arrows = to_filter(display_arrows)
        self.up_arrow_symbol = up_arrow_symbol
        self.down_arrow_symbol = down_arrow_symbol

        self.vertical_scroll = 0

    def __repr__(self) -> str:
        return f"ScrollablePane({self.content!r})"

    def reset(self) -> None:
        self.content.reset()

    def preferred_width(self, max_available_width: int) -> Dimension:
        if self.width is not None:
            return to_dimension(self.width)

        # We're only scrolling vertical. So the preferred width is equal to
        # that of the content.
        content_width = self.content.preferred_width(max_available_width)

        # If a scrollbar needs to be displayed, add +1 to the content width.
        if self.show_scrollbar():
            return sum_layout_dimensions([Dimension.exact(1), content_width])

        return content_width

    def preferred_height(self, width: int, max_available_height: int) -> Dimension:
        if self.height is not None:
            return to_dimension(self.height)

        # Prefer a height large enough so that it fits all the content. If not,
        # we'll make the pane scrollable.
        if self.show_scrollbar():
            # If `show_scrollbar` is set. Always reserve space for the scrollbar.
            width -= 1

        dimension = self.content.preferred_height(width, self.max_available_height)

        # Only take 'preferred' into account. Min/max can be anything.
        return Dimension(min=0, preferred=dimension.preferred)

    def write_to_screen(
        self,
        screen: Screen,
        mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        parent_style: str,
        erase_bg: bool,
        z_index: int | None,
    ) -> None:
        """
        Render scrollable pane content.

        This works by rendering on an off-screen canvas, and copying over the
        visible region.
        """
        show_scrollbar = self.show_scrollbar()

        if show_scrollbar:
            virtual_width = write_position.width - 1
        else:
            virtual_width = write_position.width

        # Compute preferred height again.
        virtual_height = self.content.preferred_height(
            virtual_width, self.max_available_height
        ).preferred

        # Ensure virtual height is at least the available height.
        virtual_height = max(virtual_height, write_position.height)
        virtual_height = min(virtual_height, self.max_available_height)

        # First, write the content to a virtual screen, then copy over the
        # visible part to the real screen.
        temp_screen = Screen(default_char=Char(char=" ", style=parent_style))
        temp_screen.show_cursor = screen.show_cursor
        temp_write_position = WritePosition(
            xpos=0, ypos=0, width=virtual_width, height=virtual_height
        )

        temp_mouse_handlers = MouseHandlers()

        self.content.write_to_screen(
            temp_screen,
            temp_mouse_handlers,
            temp_write_position,
            parent_style,
            erase_bg,
            z_index,
        )
        temp_screen.draw_all_floats()

        # If anything in the virtual screen is focused, move vertical scroll to
        from prompt_toolkit.application import get_app

        focused_window = get_app().layout.current_window

        try:
            visible_win_write_pos = temp_screen.visible_windows_to_write_positions[
                focused_window
            ]
        except KeyError:
            pass  # No window focused here. Don't scroll.
        else:
            # Make sure this window is visible.
            self._make_window_visible(
                write_position.height,
                virtual_height,
                visible_win_write_pos,
                temp_screen.cursor_positions.get(focused_window),
            )

        # Copy over virtual screen and zero width escapes to real screen.
        self._copy_over_screen(screen, temp_screen, write_position, virtual_width)

        # Copy over mouse handlers.
        self._copy_over_mouse_handlers(
            mouse_handlers, temp_mouse_handlers, write_position, virtual_width
        )

        # Set screen.width/height.
        ypos = write_position.ypos
        xpos = write_position.xpos

        screen.width = max(screen.width, xpos + virtual_width)
        screen.height = max(screen.height, ypos + write_position.height)

        # Copy over window write positions.
        self._copy_over_write_positions(screen, temp_screen, write_position)

        if temp_screen.show_cursor:
            screen.show_cursor = True

        # Copy over cursor positions, if they are visible.
        for window, point in temp_screen.cursor_positions.items():
            if (
                0 <= point.x < write_position.width
                and self.vertical_scroll
                <= point.y
                < write_position.height + self.vertical_scroll
            ):
                screen.cursor_positions[window] = Point(
                    x=point.x + xpos, y=point.y + ypos - self.vertical_scroll
                )

        # Copy over menu positions, but clip them to the visible area.
        for window, point in temp_screen.menu_positions.items():
            screen.menu_positions[window] = self._clip_point_to_visible_area(
                Point(x=point.x + xpos, y=point.y + ypos - self.vertical_scroll),
                write_position,
            )

        # Draw scrollbar.
        if show_scrollbar:
            self._draw_scrollbar(
                write_position,
                virtual_height,
                screen,
            )

    def _clip_point_to_visible_area(
        self, point: Point, write_position: WritePosition
    ) -> Point:
        """
        Ensure that the cursor and menu positions always are always reported
        """
        if point.x < write_position.xpos:
            point = point._replace(x=write_position.xpos)
        if point.y < write_position.ypos:
            point = point._replace(y=write_position.ypos)
        if point.x >= write_position.xpos + write_position.width:
            point = point._replace(x=write_position.xpos + write_position.width - 1)
        if point.y >= write_position.ypos + write_position.height:
            point = point._replace(y=write_position.ypos + write_position.height - 1)

        return point

    def _copy_over_screen(
        self,
        screen: Screen,
        temp_screen: Screen,
        write_position: WritePosition,
        virtual_width: int,
    ) -> None:
        """
        Copy over visible screen content and "zero width escape sequences".
        """
        ypos = write_position.ypos
        xpos = write_position.xpos

        for y in range(write_position.height):
            temp_row = temp_screen.data_buffer[y + self.vertical_scroll]
            row = screen.data_buffer[y + ypos]
            temp_zero_width_escapes = temp_screen.zero_width_escapes[
                y + self.vertical_scroll
            ]
            zero_width_escapes = screen.zero_width_escapes[y + ypos]

            for x in range(virtual_width):
                row[x + xpos] = temp_row[x]

                if x in temp_zero_width_escapes:
                    zero_width_escapes[x + xpos] = temp_zero_width_escapes[x]

    def _copy_over_mouse_handlers(
        self,
        mouse_handlers: MouseHandlers,
        temp_mouse_handlers: MouseHandlers,
        write_position: WritePosition,
        virtual_width: int,
    ) -> None:
        """
        Copy over mouse handlers from virtual screen to real screen.

        Note: we take `virtual_width` because we don't want to copy over mouse
              handlers that we possibly have behind the scrollbar.
        """
        ypos = write_position.ypos
        xpos = write_position.xpos

        # Cache mouse handlers when wrapping them. Very often the same mouse
        # handler is registered for many positions.
        mouse_handler_wrappers: dict[MouseHandler, MouseHandler] = {}

        def wrap_mouse_handler(handler: MouseHandler) -> MouseHandler:
            "Wrap mouse handler. Translate coordinates in `MouseEvent`."
            if handler not in mouse_handler_wrappers:

                def new_handler(event: MouseEvent) -> None:
                    new_event = MouseEvent(
                        position=Point(
                            x=event.position.x - xpos,
                            y=event.position.y + self.vertical_scroll - ypos,
                        ),
                        event_type=event.event_type,
                        button=event.button,
                        modifiers=event.modifiers,
                    )
                    handler(new_event)

                mouse_handler_wrappers[handler] = new_handler
            return mouse_handler_wrappers[handler]

        # Copy handlers.
        mouse_handlers_dict = mouse_handlers.mouse_handlers
        temp_mouse_handlers_dict = temp_mouse_handlers.mouse_handlers

        for y in range(write_position.height):
            if y in temp_mouse_handlers_dict:
                temp_mouse_row = temp_mouse_handlers_dict[y + self.vertical_scroll]
                mouse_row = mouse_handlers_dict[y + ypos]
                for x in range(virtual_width):
                    if x in temp_mouse_row:
                        mouse_row[x + xpos] = wrap_mouse_handler(temp_mouse_row[x])

    def _copy_over_write_positions(
        self, screen: Screen, temp_screen: Screen, write_position: WritePosition
    ) -> None:
        """
        Copy over window write positions.
        """
        ypos = write_position.ypos
        xpos = write_position.xpos

        for win, write_pos in temp_screen.visible_windows_to_write_positions.items():
            screen.visible_windows_to_write_positions[win] = WritePosition(
                xpos=write_pos.xpos + xpos,
                ypos=write_pos.ypos + ypos - self.vertical_scroll,
                # TODO: if the window is only partly visible, then truncate width/height.
                #       This could be important if we have nested ScrollablePanes.
                height=write_pos.height,
                width=write_pos.width,
            )

    def is_modal(self) -> bool:
        return self.content.is_modal()

    def get_key_bindings(self) -> KeyBindingsBase | None:
        return self.content.get_key_bindings()

    def get_children(self) -> list[Container]:
        return [self.content]

    def _make_window_visible(
        self,
        visible_height: int,
        virtual_height: int,
        visible_win_write_pos: WritePosition,
        cursor_position: Point | None,
    ) -> None:
        """
        Scroll the scrollable pane, so that this window becomes visible.

        :param visible_height: Height of this `ScrollablePane` that is rendered.
        :param virtual_height: Height of the virtual, temp screen.
        :param visible_win_write_pos: `WritePosition` of the nested window on the
            temp screen.
        :param cursor_position: The location of the cursor position of this
            window on the temp screen.
        """
        # Start with maximum allowed scroll range, and then reduce according to
        # the focused window and cursor position.
        min_scroll = 0
        max_scroll = virtual_height - visible_height

        if self.keep_cursor_visible():
            # Reduce min/max scroll according to the cursor in the focused window.
            if cursor_position is not None:
                offsets = self.scroll_offsets
                cpos_min_scroll = (
                    cursor_position.y - visible_height + 1 + offsets.bottom
                )
                cpos_max_scroll = cursor_position.y - offsets.top
                min_scroll = max(min_scroll, cpos_min_scroll)
                max_scroll = max(0, min(max_scroll, cpos_max_scroll))

        if self.keep_focused_window_visible():
            # Reduce min/max scroll according to focused window position.
            # If the window is small enough, bot the top and bottom of the window
            # should be visible.
            if visible_win_write_pos.height <= visible_height:
                window_min_scroll = (
                    visible_win_write_pos.ypos
                    + visible_win_write_pos.height
                    - visible_height
                )
                window_max_scroll = visible_win_write_pos.ypos
            else:
                # Window does not fit on the screen. Make sure at least the whole
                # screen is occupied with this window, and nothing else is shown.
                window_min_scroll = visible_win_write_pos.ypos
                window_max_scroll = (
                    visible_win_write_pos.ypos
                    + visible_win_write_pos.height
                    - visible_height
                )

            min_scroll = max(min_scroll, window_min_scroll)
            max_scroll = min(max_scroll, window_max_scroll)

        if min_scroll > max_scroll:
            min_scroll = max_scroll  # Should not happen.

        # Finally, properly clip the vertical scroll.
        if self.vertical_scroll > max_scroll:
            self.vertical_scroll = max_scroll
        if self.vertical_scroll < min_scroll:
            self.vertical_scroll = min_scroll

    def _draw_scrollbar(
        self, write_position: WritePosition, content_height: int, screen: Screen
    ) -> None:
        """
        Draw the scrollbar on the screen.

        Note: There is some code duplication with the `ScrollbarMargin`
              implementation.
        """

        window_height = write_position.height
        display_arrows = self.display_arrows()

        if display_arrows:
            window_height -= 2

        try:
            fraction_visible = write_position.height / float(content_height)
            fraction_above = self.vertical_scroll / float(content_height)

            scrollbar_height = int(
                min(window_height, max(1, window_height * fraction_visible))
            )
            scrollbar_top = int(window_height * fraction_above)
        except ZeroDivisionError:
            return
        else:

            def is_scroll_button(row: int) -> bool:
                "True if we should display a button on this row."
                return scrollbar_top <= row <= scrollbar_top + scrollbar_height

            xpos = write_position.xpos + write_position.width - 1
            ypos = write_position.ypos
            data_buffer = screen.data_buffer

            # Up arrow.
            if display_arrows:
                data_buffer[ypos][xpos] = Char(
                    self.up_arrow_symbol, "class:scrollbar.arrow"
                )
                ypos += 1

            # Scrollbar body.
            scrollbar_background = "class:scrollbar.background"
            scrollbar_background_start = "class:scrollbar.background,scrollbar.start"
            scrollbar_button = "class:scrollbar.button"
            scrollbar_button_end = "class:scrollbar.button,scrollbar.end"

            for i in range(window_height):
                style = ""
                if is_scroll_button(i):
                    if not is_scroll_button(i + 1):
                        # Give the last cell a different style, because we want
                        # to underline this.
                        style = scrollbar_button_end
                    else:
                        style = scrollbar_button
                else:
                    if is_scroll_button(i + 1):
                        style = scrollbar_background_start
                    else:
                        style = scrollbar_background

                data_buffer[ypos][xpos] = Char(" ", style)
                ypos += 1

            # Down arrow
            if display_arrows:
                data_buffer[ypos][xpos] = Char(
                    self.down_arrow_symbol, "class:scrollbar.arrow"
                )

# === NexusCore/openenv\Lib\site-packages\pydantic\v1\color.py ===
"""
Color definitions are  used as per CSS3 specification:
http://www.w3.org/TR/css3-color/#svg-color

A few colors have multiple names referring to the sames colors, eg. `grey` and `gray` or `aqua` and `cyan`.

In these cases the LAST color when sorted alphabetically takes preferences,
eg. Color((0, 255, 255)).as_named() == 'cyan' because "cyan" comes after "aqua".
"""
import math
import re
from colorsys import hls_to_rgb, rgb_to_hls
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union, cast

from pydantic.v1.errors import ColorError
from pydantic.v1.utils import Representation, almost_equal_floats

if TYPE_CHECKING:
    from pydantic.v1.typing import CallableGenerator, ReprArgs

ColorTuple = Union[Tuple[int, int, int], Tuple[int, int, int, float]]
ColorType = Union[ColorTuple, str]
HslColorTuple = Union[Tuple[float, float, float], Tuple[float, float, float, float]]


class RGBA:
    """
    Internal use only as a representation of a color.
    """

    __slots__ = 'r', 'g', 'b', 'alpha', '_tuple'

    def __init__(self, r: float, g: float, b: float, alpha: Optional[float]):
        self.r = r
        self.g = g
        self.b = b
        self.alpha = alpha

        self._tuple: Tuple[float, float, float, Optional[float]] = (r, g, b, alpha)

    def __getitem__(self, item: Any) -> Any:
        return self._tuple[item]


# these are not compiled here to avoid import slowdown, they'll be compiled the first time they're used, then cached
r_hex_short = r'\s*(?:#|0x)?([0-9a-f])([0-9a-f])([0-9a-f])([0-9a-f])?\s*'
r_hex_long = r'\s*(?:#|0x)?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})?\s*'
_r_255 = r'(\d{1,3}(?:\.\d+)?)'
_r_comma = r'\s*,\s*'
r_rgb = fr'\s*rgb\(\s*{_r_255}{_r_comma}{_r_255}{_r_comma}{_r_255}\)\s*'
_r_alpha = r'(\d(?:\.\d+)?|\.\d+|\d{1,2}%)'
r_rgba = fr'\s*rgba\(\s*{_r_255}{_r_comma}{_r_255}{_r_comma}{_r_255}{_r_comma}{_r_alpha}\s*\)\s*'
_r_h = r'(-?\d+(?:\.\d+)?|-?\.\d+)(deg|rad|turn)?'
_r_sl = r'(\d{1,3}(?:\.\d+)?)%'
r_hsl = fr'\s*hsl\(\s*{_r_h}{_r_comma}{_r_sl}{_r_comma}{_r_sl}\s*\)\s*'
r_hsla = fr'\s*hsl\(\s*{_r_h}{_r_comma}{_r_sl}{_r_comma}{_r_sl}{_r_comma}{_r_alpha}\s*\)\s*'

# colors where the two hex characters are the same, if all colors match this the short version of hex colors can be used
repeat_colors = {int(c * 2, 16) for c in '0123456789abcdef'}
rads = 2 * math.pi


class Color(Representation):
    __slots__ = '_original', '_rgba'

    def __init__(self, value: ColorType) -> None:
        self._rgba: RGBA
        self._original: ColorType
        if isinstance(value, (tuple, list)):
            self._rgba = parse_tuple(value)
        elif isinstance(value, str):
            self._rgba = parse_str(value)
        elif isinstance(value, Color):
            self._rgba = value._rgba
            value = value._original
        else:
            raise ColorError(reason='value must be a tuple, list or string')

        # if we've got here value must be a valid color
        self._original = value

    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='color')

    def original(self) -> ColorType:
        """
        Original value passed to Color
        """
        return self._original

    def as_named(self, *, fallback: bool = False) -> str:
        if self._rgba.alpha is None:
            rgb = cast(Tuple[int, int, int], self.as_rgb_tuple())
            try:
                return COLORS_BY_VALUE[rgb]
            except KeyError as e:
                if fallback:
                    return self.as_hex()
                else:
                    raise ValueError('no named color found, use fallback=True, as_hex() or as_rgb()') from e
        else:
            return self.as_hex()

    def as_hex(self) -> str:
        """
        Hex string representing the color can be 3, 4, 6 or 8 characters depending on whether the string
        a "short" representation of the color is possible and whether there's an alpha channel.
        """
        values = [float_to_255(c) for c in self._rgba[:3]]
        if self._rgba.alpha is not None:
            values.append(float_to_255(self._rgba.alpha))

        as_hex = ''.join(f'{v:02x}' for v in values)
        if all(c in repeat_colors for c in values):
            as_hex = ''.join(as_hex[c] for c in range(0, len(as_hex), 2))
        return '#' + as_hex

    def as_rgb(self) -> str:
        """
        Color as an rgb(<r>, <g>, <b>) or rgba(<r>, <g>, <b>, <a>) string.
        """
        if self._rgba.alpha is None:
            return f'rgb({float_to_255(self._rgba.r)}, {float_to_255(self._rgba.g)}, {float_to_255(self._rgba.b)})'
        else:
            return (
                f'rgba({float_to_255(self._rgba.r)}, {float_to_255(self._rgba.g)}, {float_to_255(self._rgba.b)}, '
                f'{round(self._alpha_float(), 2)})'
            )

    def as_rgb_tuple(self, *, alpha: Optional[bool] = None) -> ColorTuple:
        """
        Color as an RGB or RGBA tuple; red, green and blue are in the range 0 to 255, alpha if included is
        in the range 0 to 1.

        :param alpha: whether to include the alpha channel, options are
          None - (default) include alpha only if it's set (e.g. not None)
          True - always include alpha,
          False - always omit alpha,
        """
        r, g, b = (float_to_255(c) for c in self._rgba[:3])
        if alpha is None:
            if self._rgba.alpha is None:
                return r, g, b
            else:
                return r, g, b, self._alpha_float()
        elif alpha:
            return r, g, b, self._alpha_float()
        else:
            # alpha is False
            return r, g, b

    def as_hsl(self) -> str:
        """
        Color as an hsl(<h>, <s>, <l>) or hsl(<h>, <s>, <l>, <a>) string.
        """
        if self._rgba.alpha is None:
            h, s, li = self.as_hsl_tuple(alpha=False)  # type: ignore
            return f'hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%})'
        else:
            h, s, li, a = self.as_hsl_tuple(alpha=True)  # type: ignore
            return f'hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%}, {round(a, 2)})'

    def as_hsl_tuple(self, *, alpha: Optional[bool] = None) -> HslColorTuple:
        """
        Color as an HSL or HSLA tuple, e.g. hue, saturation, lightness and optionally alpha; all elements are in
        the range 0 to 1.

        NOTE: this is HSL as used in HTML and most other places, not HLS as used in python's colorsys.

        :param alpha: whether to include the alpha channel, options are
          None - (default) include alpha only if it's set (e.g. not None)
          True - always include alpha,
          False - always omit alpha,
        """
        h, l, s = rgb_to_hls(self._rgba.r, self._rgba.g, self._rgba.b)
        if alpha is None:
            if self._rgba.alpha is None:
                return h, s, l
            else:
                return h, s, l, self._alpha_float()
        if alpha:
            return h, s, l, self._alpha_float()
        else:
            # alpha is False
            return h, s, l

    def _alpha_float(self) -> float:
        return 1 if self._rgba.alpha is None else self._rgba.alpha

    @classmethod
    def __get_validators__(cls) -> 'CallableGenerator':
        yield cls

    def __str__(self) -> str:
        return self.as_named(fallback=True)

    def __repr_args__(self) -> 'ReprArgs':
        return [(None, self.as_named(fallback=True))] + [('rgb', self.as_rgb_tuple())]  # type: ignore

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Color) and self.as_rgb_tuple() == other.as_rgb_tuple()

    def __hash__(self) -> int:
        return hash(self.as_rgb_tuple())


def parse_tuple(value: Tuple[Any, ...]) -> RGBA:
    """
    Parse a tuple or list as a color.
    """
    if len(value) == 3:
        r, g, b = (parse_color_value(v) for v in value)
        return RGBA(r, g, b, None)
    elif len(value) == 4:
        r, g, b = (parse_color_value(v) for v in value[:3])
        return RGBA(r, g, b, parse_float_alpha(value[3]))
    else:
        raise ColorError(reason='tuples must have length 3 or 4')


def parse_str(value: str) -> RGBA:
    """
    Parse a string to an RGBA tuple, trying the following formats (in this order):
    * named color, see COLORS_BY_NAME below
    * hex short eg. `<prefix>fff` (prefix can be `#`, `0x` or nothing)
    * hex long eg. `<prefix>ffffff` (prefix can be `#`, `0x` or nothing)
    * `rgb(<r>, <g>, <b>) `
    * `rgba(<r>, <g>, <b>, <a>)`
    """
    value_lower = value.lower()
    try:
        r, g, b = COLORS_BY_NAME[value_lower]
    except KeyError:
        pass
    else:
        return ints_to_rgba(r, g, b, None)

    m = re.fullmatch(r_hex_short, value_lower)
    if m:
        *rgb, a = m.groups()
        r, g, b = (int(v * 2, 16) for v in rgb)
        if a:
            alpha: Optional[float] = int(a * 2, 16) / 255
        else:
            alpha = None
        return ints_to_rgba(r, g, b, alpha)

    m = re.fullmatch(r_hex_long, value_lower)
    if m:
        *rgb, a = m.groups()
        r, g, b = (int(v, 16) for v in rgb)
        if a:
            alpha = int(a, 16) / 255
        else:
            alpha = None
        return ints_to_rgba(r, g, b, alpha)

    m = re.fullmatch(r_rgb, value_lower)
    if m:
        return ints_to_rgba(*m.groups(), None)  # type: ignore

    m = re.fullmatch(r_rgba, value_lower)
    if m:
        return ints_to_rgba(*m.groups())  # type: ignore

    m = re.fullmatch(r_hsl, value_lower)
    if m:
        h, h_units, s, l_ = m.groups()
        return parse_hsl(h, h_units, s, l_)

    m = re.fullmatch(r_hsla, value_lower)
    if m:
        h, h_units, s, l_, a = m.groups()
        return parse_hsl(h, h_units, s, l_, parse_float_alpha(a))

    raise ColorError(reason='string not recognised as a valid color')


def ints_to_rgba(r: Union[int, str], g: Union[int, str], b: Union[int, str], alpha: Optional[float]) -> RGBA:
    return RGBA(parse_color_value(r), parse_color_value(g), parse_color_value(b), parse_float_alpha(alpha))


def parse_color_value(value: Union[int, str], max_val: int = 255) -> float:
    """
    Parse a value checking it's a valid int in the range 0 to max_val and divide by max_val to give a number
    in the range 0 to 1
    """
    try:
        color = float(value)
    except ValueError:
        raise ColorError(reason='color values must be a valid number')
    if 0 <= color <= max_val:
        return color / max_val
    else:
        raise ColorError(reason=f'color values must be in the range 0 to {max_val}')


def parse_float_alpha(value: Union[None, str, float, int]) -> Optional[float]:
    """
    Parse a value checking it's a valid float in the range 0 to 1
    """
    if value is None:
        return None
    try:
        if isinstance(value, str) and value.endswith('%'):
            alpha = float(value[:-1]) / 100
        else:
            alpha = float(value)
    except ValueError:
        raise ColorError(reason='alpha values must be a valid float')

    if almost_equal_floats(alpha, 1):
        return None
    elif 0 <= alpha <= 1:
        return alpha
    else:
        raise ColorError(reason='alpha values must be in the range 0 to 1')


def parse_hsl(h: str, h_units: str, sat: str, light: str, alpha: Optional[float] = None) -> RGBA:
    """
    Parse raw hue, saturation, lightness and alpha values and convert to RGBA.
    """
    s_value, l_value = parse_color_value(sat, 100), parse_color_value(light, 100)

    h_value = float(h)
    if h_units in {None, 'deg'}:
        h_value = h_value % 360 / 360
    elif h_units == 'rad':
        h_value = h_value % rads / rads
    else:
        # turns
        h_value = h_value % 1

    r, g, b = hls_to_rgb(h_value, l_value, s_value)
    return RGBA(r, g, b, alpha)


def float_to_255(c: float) -> int:
    return int(round(c * 255))


COLORS_BY_NAME = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aquamarine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burlywood': (222, 184, 135),
    'cadetblue': (95, 158, 160),
    'chartreuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkorange': (255, 140, 0),
    'darkorchid': (153, 50, 204),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deepskyblue': (0, 191, 255),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'firebrick': (178, 34, 34),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'goldenrod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'honeydew': (240, 255, 240),
    'hotpink': (255, 105, 180),
    'indianred': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lightblue': (173, 216, 230),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightsalmon': (255, 160, 122),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightyellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumpurple': (147, 112, 219),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navy': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olivedrab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orangered': (255, 69, 0),
    'orchid': (218, 112, 214),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'paleturquoise': (175, 238, 238),
    'palevioletred': (219, 112, 147),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'red': (255, 0, 0),
    'rosybrown': (188, 143, 143),
    'royalblue': (65, 105, 225),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'skyblue': (135, 206, 235),
    'slateblue': (106, 90, 205),
    'slategray': (112, 128, 144),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'springgreen': (0, 255, 127),
    'steelblue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellowgreen': (154, 205, 50),
}

COLORS_BY_VALUE = {v: k for k, v in COLORS_BY_NAME.items()}

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\tools\browser.py ===
# basic module browser.

# usage:
# >>> import browser
# >>> browser.Browse()
# or
# >>> browser.Browse(your_module)
import sys
import types

import __main__
import win32ui
from pywin.mfc import dialog

from . import hierlist

special_names = ["__doc__", "__name__", "__self__"]


#
# HierList items
class HLIPythonObject(hierlist.HierListItem):
    def __init__(self, myobject=None, name=None):
        hierlist.HierListItem.__init__(self)
        self.myobject = myobject
        self.knownExpandable = None
        if name:
            self.name = name
        else:
            try:
                self.name = myobject.__name__
            except (AttributeError, TypeError):
                try:
                    r = repr(myobject)
                    if len(r) > 20:
                        r = r[:20] + "..."
                    self.name = r
                except (AttributeError, TypeError):
                    self.name = "???"

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        try:
            type = self.GetHLIType()
        except:
            type = "Generic"
        return f"HLIPythonObject({type}) - name: {self.name} object: {self.myobject!r}"

    def GetText(self):
        try:
            return f"{self.name} ({self.GetHLIType()})"
        except AttributeError:
            return f"{self.name} = {self.myobject!r}"

    def InsertDocString(self, lst):
        ob = None
        try:
            ob = self.myobject.__doc__
        except (AttributeError, TypeError):
            pass
        # I don't quite grok descriptors enough to know how to
        # best hook them up. Eg:
        # >>> object.__getattribute__.__class__.__doc__
        # <attribute '__doc__' of 'wrapper_descriptor' objects>
        if ob and isinstance(ob, str):
            lst.insert(0, HLIDocString(ob, "Doc"))

    def GetSubList(self):
        ret = []
        try:
            for key, ob in self.myobject.__dict__.items():
                if key not in special_names:
                    ret.append(MakeHLI(ob, key))
        except (AttributeError, TypeError):
            pass
        try:
            for name in self.myobject.__methods__:
                ret.append(HLIMethod(name))  # no MakeHLI, as can't auto detect
        except (AttributeError, TypeError):
            pass
        try:
            for member in self.myobject.__members__:
                if not member in special_names:
                    ret.append(MakeHLI(getattr(self.myobject, member), member))
        except (AttributeError, TypeError):
            pass
        ret.sort()
        self.InsertDocString(ret)
        return ret

    # if the has a dict, it is expandable.
    def IsExpandable(self):
        if self.knownExpandable is None:
            self.knownExpandable = self.CalculateIsExpandable()
        return self.knownExpandable

    def CalculateIsExpandable(self):
        if hasattr(self.myobject, "__doc__"):
            return 1
        try:
            for key in self.myobject.__dict__:
                if key not in special_names:
                    return 1
        except (AttributeError, TypeError):
            pass
        try:
            self.myobject.__methods__
            return 1
        except (AttributeError, TypeError):
            pass
        try:
            for item in self.myobject.__members__:
                if item not in special_names:
                    return 1
        except (AttributeError, TypeError):
            pass
        return 0

    def GetBitmapColumn(self):
        if self.IsExpandable():
            return 0
        else:
            return 4

    def TakeDefaultAction(self):
        ShowObject(self.myobject, self.name)


class HLIDocString(HLIPythonObject):
    def GetHLIType(self):
        return "DocString"

    def GetText(self):
        return self.myobject.strip()

    def IsExpandable(self):
        return 0

    def GetBitmapColumn(self):
        return 6


class HLIModule(HLIPythonObject):
    def GetHLIType(self):
        return "Module"


class HLIFrame(HLIPythonObject):
    def GetHLIType(self):
        return "Stack Frame"


class HLITraceback(HLIPythonObject):
    def GetHLIType(self):
        return "Traceback"


class HLIClass(HLIPythonObject):
    def GetHLIType(self):
        return "Class"

    def GetSubList(self):
        ret = []
        for base in self.myobject.__bases__:
            ret.append(MakeHLI(base, "Base class: " + base.__name__))
        ret.extend(HLIPythonObject.GetSubList(self))
        return ret


class HLIMethod(HLIPythonObject):
    # myobject is just a string for methods.
    def GetHLIType(self):
        return "Method"

    def GetText(self):
        return "Method: " + self.myobject + "()"


class HLICode(HLIPythonObject):
    def GetHLIType(self):
        return "Code"

    def IsExpandable(self):
        return self.myobject

    def GetSubList(self):
        ret = []
        ret.append(MakeHLI(self.myobject.co_consts, "Constants (co_consts)"))
        ret.append(MakeHLI(self.myobject.co_names, "Names (co_names)"))
        ret.append(MakeHLI(self.myobject.co_filename, "Filename (co_filename)"))
        ret.append(MakeHLI(self.myobject.co_argcount, "Number of args (co_argcount)"))
        ret.append(MakeHLI(self.myobject.co_varnames, "Param names (co_varnames)"))

        return ret


class HLIInstance(HLIPythonObject):
    def GetHLIType(self):
        return "Instance"

    def GetText(self):
        return (
            str(self.name)
            + " (Instance of class "
            + str(self.myobject.__class__.__name__)
            + ")"
        )

    def IsExpandable(self):
        return 1

    def GetSubList(self):
        ret = []
        ret.append(MakeHLI(self.myobject.__class__))
        ret.extend(HLIPythonObject.GetSubList(self))
        return ret


class HLIBuiltinFunction(HLIPythonObject):
    def GetHLIType(self):
        return "Builtin Function"


class HLIFunction(HLIPythonObject):
    def GetHLIType(self):
        return "Function"

    def IsExpandable(self):
        return 1

    def GetSubList(self):
        ret = [
            MakeHLI(self.myobject.__code__, "Code"),
            MakeHLI(self.myobject.__globals__, "Globals"),
        ]
        self.InsertDocString(ret)
        return ret


class HLISeq(HLIPythonObject):
    def GetHLIType(self):
        return "Sequence (abstract!)"

    def IsExpandable(self):
        return len(self.myobject) > 0

    def GetSubList(self):
        ret = []
        pos = 0
        for item in self.myobject:
            ret.append(MakeHLI(item, f"[{pos}]"))
            pos += 1
        self.InsertDocString(ret)
        return ret


class HLIList(HLISeq):
    def GetHLIType(self):
        return "List"


class HLITuple(HLISeq):
    def GetHLIType(self):
        return "Tuple"


class HLIDict(HLIPythonObject):
    def GetHLIType(self):
        return "Dict"

    def IsExpandable(self):
        try:
            self.myobject.__doc__
            return 1
        except (AttributeError, TypeError):
            return len(self.myobject) > 0

    def GetSubList(self):
        ret = [MakeHLI(self.myobject[key], str(key)) for key in sorted(self.myobject)]
        self.InsertDocString(ret)
        return ret


# strings and Unicode have builtin methods, but we don't really want to see these
class HLIString(HLIPythonObject):
    def IsExpandable(self):
        return 0


TypeMap = {
    type: HLIClass,
    types.FunctionType: HLIFunction,
    tuple: HLITuple,
    dict: HLIDict,
    list: HLIList,
    types.ModuleType: HLIModule,
    types.CodeType: HLICode,
    types.BuiltinFunctionType: HLIBuiltinFunction,
    types.FrameType: HLIFrame,
    types.TracebackType: HLITraceback,
    str: HLIString,
    int: HLIPythonObject,
    bool: HLIPythonObject,
    float: HLIPythonObject,
}


def MakeHLI(ob, name=None):
    try:
        cls = TypeMap[type(ob)]
    except KeyError:
        # hrmph - this check gets more and more bogus as Python
        # improves.  It's possible we should just *always* use
        # HLIInstance?
        if hasattr(ob, "__class__"):  # 'new style' class
            cls = HLIInstance
        else:
            cls = HLIPythonObject
    return cls(ob, name)


#########################################
#
# Dialog related.


class DialogShowObject(dialog.Dialog):
    def __init__(self, object, title):
        self.object = object
        self.title = title
        dialog.Dialog.__init__(self, win32ui.IDD_LARGE_EDIT)

    def OnInitDialog(self):
        import re

        self.SetWindowText(self.title)
        self.edit = self.GetDlgItem(win32ui.IDC_EDIT1)
        try:
            strval = str(self.object)
        except:
            t, v, tb = sys.exc_info()
            strval = f"Exception getting object value\n\n{t}:{v}"
            tb = None
        strval = re.sub(r"\n", "\r\n", strval)
        self.edit.ReplaceSel(strval)


def ShowObject(object, title):
    dlg = DialogShowObject(object, title)
    dlg.DoModal()


# And some mods for a sizable dialog from Sam Rushing!
import commctrl
import win32api
import win32con


class dynamic_browser(dialog.Dialog):
    style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE
    cs = (
        win32con.WS_CHILD
        | win32con.WS_VISIBLE
        | commctrl.TVS_HASLINES
        | commctrl.TVS_LINESATROOT
        | commctrl.TVS_HASBUTTONS
    )

    dt = [
        ["Python Object Browser", (0, 0, 200, 200), style, None, (8, "MS Sans Serif")],
        ["SysTreeView32", None, win32ui.IDC_LIST1, (0, 0, 200, 200), cs],
    ]

    def __init__(self, hli_root):
        dialog.Dialog.__init__(self, self.dt)
        self.hier_list = hierlist.HierListWithItems(hli_root, win32ui.IDB_BROWSER_HIER)
        self.HookMessage(self.on_size, win32con.WM_SIZE)

    def OnInitDialog(self):
        self.hier_list.HierInit(self)
        return dialog.Dialog.OnInitDialog(self)

    def OnOK(self):
        self.hier_list.HierTerm()
        self.hier_list = None
        return self._obj_.OnOK()

    def OnCancel(self):
        self.hier_list.HierTerm()
        self.hier_list = None
        return self._obj_.OnCancel()

    def on_size(self, params):
        lparam = params[3]
        w = win32api.LOWORD(lparam)
        h = win32api.HIWORD(lparam)
        self.GetDlgItem(win32ui.IDC_LIST1).MoveWindow((0, 0, w, h))


def Browse(ob=__main__):
    "Browse the argument, or the main dictionary"
    root = MakeHLI(ob, "root")
    if not root.IsExpandable():
        raise TypeError(
            "Browse() argument must have __dict__ attribute, or be a Browser supported type"
        )

    dlg = dynamic_browser(root)
    dlg.CreateWindow()
    return dlg


#
#
# Classes for using the browser in an MDI window, rather than a dialog
#
from pywin.mfc import docview


class BrowserTemplate(docview.DocTemplate):
    def __init__(self):
        docview.DocTemplate.__init__(
            self, win32ui.IDR_PYTHONTYPE, BrowserDocument, None, BrowserView
        )

    def OpenObject(self, root):  # Use this instead of OpenDocumentFile.
        # Look for existing open document
        for doc in self.GetDocumentList():
            if doc.root == root:
                doc.GetFirstView().ActivateFrame()
                return doc
        # not found - new one.
        doc = BrowserDocument(self, root)
        frame = self.CreateNewFrame(doc)
        doc.OnNewDocument()
        self.InitialUpdateFrame(frame, doc, 1)
        return doc


class BrowserDocument(docview.Document):
    def __init__(self, template, root):
        docview.Document.__init__(self, template)
        self.root = root
        self.SetTitle("Browser: " + root.name)

    def OnOpenDocument(self, name):
        raise TypeError("This template can not open files")
        return 0


class BrowserView(docview.TreeView):
    def OnInitialUpdate(self):
        import commctrl

        rc = self._obj_.OnInitialUpdate()
        list = hierlist.HierListWithItems(
            self.GetDocument().root,
            win32ui.IDB_BROWSER_HIER,
            win32ui.AFX_IDW_PANE_FIRST,
        )
        list.HierInit(self.GetParent())
        list.SetStyle(
            commctrl.TVS_HASLINES | commctrl.TVS_LINESATROOT | commctrl.TVS_HASBUTTONS
        )
        return rc


template = None


def MakeTemplate():
    global template
    if template is None:
        template = (
            BrowserTemplate()
        )  # win32ui.IDR_PYTHONTYPE, BrowserDocument, None, BrowserView)


def BrowseMDI(ob=__main__):
    """Browse an object using an MDI window."""

    MakeTemplate()
    root = MakeHLI(ob, repr(ob))
    if not root.IsExpandable():
        raise TypeError(
            "Browse() argument must have __dict__ attribute, or be a Browser supported type"
        )

    template.OpenObject(root)

# === NexusCore/openenv\Lib\site-packages\IPython\core\application.py ===
# encoding: utf-8
"""
An application for IPython.

All top-level applications should use the classes in this module for
handling configuration and creating configurables.

The job of an :class:`Application` is to create the master configuration
object and then create the configurable objects, passing the config to them.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import atexit
from copy import deepcopy
import logging
import os
import shutil
import sys

from pathlib import Path

from traitlets.config.application import Application, catch_config_error
from traitlets.config.loader import ConfigFileNotFound, PyFileConfigLoader
from IPython.core import release, crashhandler
from IPython.core.profiledir import ProfileDir, ProfileDirError
from IPython.paths import get_ipython_dir, get_ipython_package_dir
from IPython.utils.path import ensure_dir_exists
from traitlets import (
    List, Unicode, Type, Bool, Set, Instance, Undefined,
    default, observe,
)

if os.name == "nt":
    programdata = os.environ.get("PROGRAMDATA", None)
    if programdata is not None:
        SYSTEM_CONFIG_DIRS = [str(Path(programdata) / "ipython")]
    else:  # PROGRAMDATA is not defined by default on XP.
        SYSTEM_CONFIG_DIRS = []
else:
    SYSTEM_CONFIG_DIRS = [
        "/usr/local/etc/ipython",
        "/etc/ipython",
    ]


ENV_CONFIG_DIRS = []
_env_config_dir = os.path.join(sys.prefix, 'etc', 'ipython')
if _env_config_dir not in SYSTEM_CONFIG_DIRS:
    # only add ENV_CONFIG if sys.prefix is not already included
    ENV_CONFIG_DIRS.append(_env_config_dir)


_envvar = os.environ.get('IPYTHON_SUPPRESS_CONFIG_ERRORS')
if _envvar in {None, ''}:
    IPYTHON_SUPPRESS_CONFIG_ERRORS = None
else:
    if _envvar.lower() in {'1','true'}:
        IPYTHON_SUPPRESS_CONFIG_ERRORS = True
    elif _envvar.lower() in {'0','false'} :
        IPYTHON_SUPPRESS_CONFIG_ERRORS = False
    else:
        sys.exit("Unsupported value for environment variable: 'IPYTHON_SUPPRESS_CONFIG_ERRORS' is set to '%s' which is none of  {'0', '1', 'false', 'true', ''}."% _envvar )

# aliases and flags

base_aliases = {}
if isinstance(Application.aliases, dict):
    # traitlets 5
    base_aliases.update(Application.aliases)
base_aliases.update(
    {
        "profile-dir": "ProfileDir.location",
        "profile": "BaseIPythonApplication.profile",
        "ipython-dir": "BaseIPythonApplication.ipython_dir",
        "log-level": "Application.log_level",
        "config": "BaseIPythonApplication.extra_config_file",
    }
)

base_flags = dict()
if isinstance(Application.flags, dict):
    # traitlets 5
    base_flags.update(Application.flags)
base_flags.update(
    dict(
        debug=(
            {"Application": {"log_level": logging.DEBUG}},
            "set log level to logging.DEBUG (maximize logging output)",
        ),
        quiet=(
            {"Application": {"log_level": logging.CRITICAL}},
            "set log level to logging.CRITICAL (minimize logging output)",
        ),
        init=(
            {
                "BaseIPythonApplication": {
                    "copy_config_files": True,
                    "auto_create": True,
                }
            },
            """Initialize profile with default config files.  This is equivalent
            to running `ipython profile create <profile>` prior to startup.
            """,
        ),
    )
)


class ProfileAwareConfigLoader(PyFileConfigLoader):
    """A Python file config loader that is aware of IPython profiles."""
    def load_subconfig(self, fname, path=None, profile=None):
        if profile is not None:
            try:
                profile_dir = ProfileDir.find_profile_dir_by_name(
                        get_ipython_dir(),
                        profile,
                )
            except ProfileDirError:
                return
            path = profile_dir.location
        return super(ProfileAwareConfigLoader, self).load_subconfig(fname, path=path)

class BaseIPythonApplication(Application):
    name = "ipython"
    description = "IPython: an enhanced interactive Python shell."
    version = Unicode(release.version)

    aliases = base_aliases
    flags = base_flags
    classes = List([ProfileDir])
    
    # enable `load_subconfig('cfg.py', profile='name')`
    python_config_loader_class = ProfileAwareConfigLoader

    # Track whether the config_file has changed,
    # because some logic happens only if we aren't using the default.
    config_file_specified = Set()

    config_file_name = Unicode()
    @default('config_file_name')
    def _config_file_name_default(self):
        return self.name.replace('-','_') + u'_config.py'
    @observe('config_file_name')
    def _config_file_name_changed(self, change):
        if change['new'] != change['old']:
            self.config_file_specified.add(change['new'])

    # The directory that contains IPython's builtin profiles.
    builtin_profile_dir = Unicode(
        os.path.join(get_ipython_package_dir(), u'config', u'profile', u'default')
    )
    
    config_file_paths = List(Unicode())
    @default('config_file_paths')
    def _config_file_paths_default(self):
        return []

    extra_config_file = Unicode(
    help="""Path to an extra config file to load.
    
    If specified, load this config file in addition to any other IPython config.
    """).tag(config=True)
    @observe('extra_config_file')
    def _extra_config_file_changed(self, change):
        old = change['old']
        new = change['new']
        try:
            self.config_files.remove(old)
        except ValueError:
            pass
        self.config_file_specified.add(new)
        self.config_files.append(new)

    profile = Unicode(u'default',
        help="""The IPython profile to use."""
    ).tag(config=True)
    
    @observe('profile')
    def _profile_changed(self, change):
        self.builtin_profile_dir = os.path.join(
                get_ipython_package_dir(), u'config', u'profile', change['new']
        )

    add_ipython_dir_to_sys_path = Bool(
        False,
        """Should the IPython profile directory be added to sys path ?

        This option was non-existing before IPython 8.0, and ipython_dir was added to
        sys path to allow import of extensions present there. This was historical
        baggage from when pip did not exist. This now default to false,
        but can be set to true for legacy reasons.
        """,
    ).tag(config=True)

    ipython_dir = Unicode(
        help="""
        The name of the IPython directory. This directory is used for logging
        configuration (through profiles), history storage, etc. The default
        is usually $HOME/.ipython. This option can also be specified through
        the environment variable IPYTHONDIR.
        """
    ).tag(config=True)
    @default('ipython_dir')
    def _ipython_dir_default(self):
        d = get_ipython_dir()
        self._ipython_dir_changed({
            'name': 'ipython_dir',
            'old': d,
            'new': d,
        })
        return d
    
    _in_init_profile_dir = False

    profile_dir = Instance(ProfileDir, allow_none=True)

    @default('profile_dir')
    def _profile_dir_default(self):
        # avoid recursion
        if self._in_init_profile_dir:
            return
        # profile_dir requested early, force initialization
        self.init_profile_dir()
        return self.profile_dir

    overwrite = Bool(False,
        help="""Whether to overwrite existing config files when copying"""
    ).tag(config=True)

    auto_create = Bool(False,
        help="""Whether to create profile dir if it doesn't exist"""
    ).tag(config=True)

    config_files = List(Unicode())

    @default('config_files')
    def _config_files_default(self):
        return [self.config_file_name]

    copy_config_files = Bool(False,
        help="""Whether to install the default config files into the profile dir.
        If a new profile is being created, and IPython contains config files for that
        profile, then they will be staged into the new directory.  Otherwise,
        default config files will be automatically generated.
        """).tag(config=True)
    
    verbose_crash = Bool(False,
        help="""Create a massive crash report when IPython encounters what may be an
        internal error.  The default is to append a short message to the
        usual traceback""").tag(config=True)

    # The class to use as the crash handler.
    crash_handler_class = Type(crashhandler.CrashHandler)

    @catch_config_error
    def __init__(self, **kwargs):
        super(BaseIPythonApplication, self).__init__(**kwargs)
        # ensure current working directory exists
        try:
            os.getcwd()
        except:
            # exit if cwd doesn't exist
            self.log.error("Current working directory doesn't exist.")
            self.exit(1)

    #-------------------------------------------------------------------------
    # Various stages of Application creation
    #-------------------------------------------------------------------------
    
    def init_crash_handler(self):
        """Create a crash handler, typically setting sys.excepthook to it."""
        self.crash_handler = self.crash_handler_class(self)
        sys.excepthook = self.excepthook
        def unset_crashhandler():
            sys.excepthook = sys.__excepthook__
        atexit.register(unset_crashhandler)
    
    def excepthook(self, etype, evalue, tb):
        """this is sys.excepthook after init_crashhandler

        set self.verbose_crash=True to use our full crashhandler, instead of
        a regular traceback with a short message (crash_handler_lite)
        """
        
        if self.verbose_crash:
            return self.crash_handler(etype, evalue, tb)
        else:
            return crashhandler.crash_handler_lite(etype, evalue, tb)

    @observe('ipython_dir')
    def _ipython_dir_changed(self, change):
        old = change['old']
        new = change['new']
        if old is not Undefined:
            str_old = os.path.abspath(old)
            if str_old in sys.path:
                sys.path.remove(str_old)
        if self.add_ipython_dir_to_sys_path:
            str_path = os.path.abspath(new)
            sys.path.append(str_path)
            ensure_dir_exists(new)
            readme = os.path.join(new, "README")
            readme_src = os.path.join(
                get_ipython_package_dir(), "config", "profile", "README"
            )
            if not os.path.exists(readme) and os.path.exists(readme_src):
                shutil.copy(readme_src, readme)
            for d in ("extensions", "nbextensions"):
                path = os.path.join(new, d)
                try:
                    ensure_dir_exists(path)
                except OSError as e:
                    # this will not be EEXIST
                    self.log.error("couldn't create path %s: %s", path, e)
            self.log.debug("IPYTHONDIR set to: %s", new)

    def load_config_file(self, suppress_errors=IPYTHON_SUPPRESS_CONFIG_ERRORS):
        """Load the config file.

        By default, errors in loading config are handled, and a warning
        printed on screen. For testing, the suppress_errors option is set
        to False, so errors will make tests fail.

        `suppress_errors` default value is to be `None` in which case the
        behavior default to the one of `traitlets.Application`.

        The default value can be set :
           - to `False` by setting 'IPYTHON_SUPPRESS_CONFIG_ERRORS' environment variable to '0', or 'false' (case insensitive).
           - to `True` by setting 'IPYTHON_SUPPRESS_CONFIG_ERRORS' environment variable to '1' or 'true' (case insensitive).
           - to `None` by setting 'IPYTHON_SUPPRESS_CONFIG_ERRORS' environment variable to '' (empty string) or leaving it unset.

        Any other value are invalid, and will make IPython exit with a non-zero return code.
        """


        self.log.debug("Searching path %s for config files", self.config_file_paths)
        base_config = 'ipython_config.py'
        self.log.debug("Attempting to load config file: %s" %
                       base_config)
        try:
            if suppress_errors is not None:
                old_value = Application.raise_config_file_errors
                Application.raise_config_file_errors = not suppress_errors
            Application.load_config_file(
                self,
                base_config,
                path=self.config_file_paths
            )
        except ConfigFileNotFound:
            # ignore errors loading parent
            self.log.debug("Config file %s not found", base_config)
            pass
        if suppress_errors is not None:
            Application.raise_config_file_errors = old_value
        
        for config_file_name in self.config_files:
            if not config_file_name or config_file_name == base_config:
                continue
            self.log.debug("Attempting to load config file: %s" %
                           self.config_file_name)
            try:
                Application.load_config_file(
                    self,
                    config_file_name,
                    path=self.config_file_paths
                )
            except ConfigFileNotFound:
                # Only warn if the default config file was NOT being used.
                if config_file_name in self.config_file_specified:
                    msg = self.log.warning
                else:
                    msg = self.log.debug
                msg("Config file not found, skipping: %s", config_file_name)
            except Exception:
                # For testing purposes.
                if not suppress_errors:
                    raise
                self.log.warning("Error loading config file: %s" %
                              self.config_file_name, exc_info=True)

    def init_profile_dir(self):
        """initialize the profile dir"""
        self._in_init_profile_dir = True
        if self.profile_dir is not None:
            # already ran
            return
        if 'ProfileDir.location' not in self.config:
            # location not specified, find by profile name
            try:
                p = ProfileDir.find_profile_dir_by_name(self.ipython_dir, self.profile, self.config)
            except ProfileDirError:
                # not found, maybe create it (always create default profile)
                if self.auto_create or self.profile == 'default':
                    try:
                        p = ProfileDir.create_profile_dir_by_name(self.ipython_dir, self.profile, self.config)
                    except ProfileDirError:
                        self.log.fatal("Could not create profile: %r"%self.profile)
                        self.exit(1)
                    else:
                        self.log.info("Created profile dir: %r"%p.location)
                else:
                    self.log.fatal("Profile %r not found."%self.profile)
                    self.exit(1)
            else:
                self.log.debug("Using existing profile dir: %r", p.location)
        else:
            location = self.config.ProfileDir.location
            # location is fully specified
            try:
                p = ProfileDir.find_profile_dir(location, self.config)
            except ProfileDirError:
                # not found, maybe create it
                if self.auto_create:
                    try:
                        p = ProfileDir.create_profile_dir(location, self.config)
                    except ProfileDirError:
                        self.log.fatal("Could not create profile directory: %r"%location)
                        self.exit(1)
                    else:
                        self.log.debug("Creating new profile dir: %r"%location)
                else:
                    self.log.fatal("Profile directory %r not found."%location)
                    self.exit(1)
            else:
                self.log.debug("Using existing profile dir: %r", p.location)
            # if profile_dir is specified explicitly, set profile name
            dir_name = os.path.basename(p.location)
            if dir_name.startswith('profile_'):
                self.profile = dir_name[8:]

        self.profile_dir = p
        self.config_file_paths.append(p.location)
        self._in_init_profile_dir = False

    def init_config_files(self):
        """[optionally] copy default config files into profile dir."""
        self.config_file_paths.extend(ENV_CONFIG_DIRS)
        self.config_file_paths.extend(SYSTEM_CONFIG_DIRS)
        # copy config files
        path = Path(self.builtin_profile_dir)
        if self.copy_config_files:
            src = self.profile

            cfg = self.config_file_name
            if path and (path / cfg).exists():
                self.log.warning(
                    "Staging %r from %s into %r [overwrite=%s]"
                    % (cfg, src, self.profile_dir.location, self.overwrite)
                )
                self.profile_dir.copy_config_file(cfg, path=path, overwrite=self.overwrite)
            else:
                self.stage_default_config_file()
        else:
            # Still stage *bundled* config files, but not generated ones
            # This is necessary for `ipython profile=sympy` to load the profile
            # on the first go
            files = path.glob("*.py")
            for fullpath in files:
                cfg = fullpath.name
                if self.profile_dir.copy_config_file(cfg, path=path, overwrite=False):
                    # file was copied
                    self.log.warning("Staging bundled %s from %s into %r"%(
                            cfg, self.profile, self.profile_dir.location)
                    )


    def stage_default_config_file(self):
        """auto generate default config file, and stage it into the profile."""
        s = self.generate_config_file()
        config_file = Path(self.profile_dir.location) / self.config_file_name
        if self.overwrite or not config_file.exists():
            self.log.warning("Generating default config file: %r", (config_file))
            config_file.write_text(s, encoding="utf-8")

    @catch_config_error
    def initialize(self, argv=None):
        # don't hook up crash handler before parsing command-line
        self.parse_command_line(argv)
        self.init_crash_handler()
        if self.subapp is not None:
            # stop here if subapp is taking over
            return
        # save a copy of CLI config to re-load after config files
        # so that it has highest priority
        cl_config = deepcopy(self.config)
        self.init_profile_dir()
        self.init_config_files()
        self.load_config_file()
        # enforce cl-opts override configfile opts:
        self.update_config(cl_config)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\vertex_llm_base.py ===
"""
Base Vertex, Google AI Studio LLM Class

Handles Authentication and generating request urls for Vertex AI and Google AI Studio
"""

import json
import os
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Tuple

from litellm._logging import verbose_logger
from litellm.litellm_core_utils.asyncify import asyncify
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from litellm.types.llms.vertex_ai import VERTEX_CREDENTIALS_TYPES, VertexPartnerProvider

from .common_utils import (
    _get_gemini_url,
    _get_vertex_url,
    all_gemini_url_modes,
    is_global_only_vertex_model,
)

if TYPE_CHECKING:
    from google.auth.credentials import Credentials as GoogleCredentialsObject
else:
    GoogleCredentialsObject = Any


class VertexBase:
    def __init__(self) -> None:
        super().__init__()
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._credentials: Optional[GoogleCredentialsObject] = None
        self._credentials_project_mapping: Dict[
            Tuple[Optional[VERTEX_CREDENTIALS_TYPES], Optional[str]],
            GoogleCredentialsObject,
        ] = {}
        self.project_id: Optional[str] = None
        self.async_handler: Optional[AsyncHTTPHandler] = None

    def get_vertex_region(self, vertex_region: Optional[str], model: str) -> str:
        if is_global_only_vertex_model(model):
            return "global"
        return vertex_region or "us-central1"

    def load_auth(
        self, credentials: Optional[VERTEX_CREDENTIALS_TYPES], project_id: Optional[str]
    ) -> Tuple[Any, str]:
        if credentials is not None:
            if isinstance(credentials, str):
                verbose_logger.debug(
                    "Vertex: Loading vertex credentials from %s", credentials
                )
                verbose_logger.debug(
                    "Vertex: checking if credentials is a valid path, os.path.exists(%s)=%s, current dir %s",
                    credentials,
                    os.path.exists(credentials),
                    os.getcwd(),
                )

                try:
                    if os.path.exists(credentials):
                        json_obj = json.load(open(credentials))
                    else:
                        json_obj = json.loads(credentials)
                except Exception:
                    raise Exception(
                        "Unable to load vertex credentials from environment. Got={}".format(
                            credentials
                        )
                    )
            elif isinstance(credentials, dict):
                json_obj = credentials
            else:
                raise ValueError(
                    "Invalid credentials type: {}".format(type(credentials))
                )

            # Check if the JSON object contains Workload Identity Federation configuration
            if "type" in json_obj and json_obj["type"] == "external_account":
                # If environment_id key contains "aws" value it corresponds to an AWS config file
                if (
                    "credential_source" in json_obj
                    and "environment_id" in json_obj["credential_source"]
                    and "aws" in json_obj["credential_source"]["environment_id"]
                ):
                    creds = self._credentials_from_identity_pool_with_aws(json_obj)
                else:
                    creds = self._credentials_from_identity_pool(json_obj)
            # Check if the JSON object contains Authorized User configuration (via gcloud auth application-default login)
            elif "type" in json_obj and json_obj["type"] == "authorized_user":
                creds = self._credentials_from_authorized_user(
                    json_obj,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                if project_id is None:
                    project_id = (
                        creds.quota_project_id
                    )  # authorized user credentials don't have a project_id, only quota_project_id
            else:
                creds = self._credentials_from_service_account(
                    json_obj,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )

            if project_id is None:
                project_id = getattr(creds, "project_id", None)
        else:
            creds, creds_project_id = self._credentials_from_default_auth(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            if project_id is None:
                project_id = creds_project_id

        self.refresh_auth(creds)

        if not project_id:
            raise ValueError("Could not resolve project_id")

        if not isinstance(project_id, str):
            raise TypeError(
                f"Expected project_id to be a str but got {type(project_id)}"
            )

        return creds, project_id

    # Google Auth Helpers -- extracted for mocking purposes in tests
    def _credentials_from_identity_pool(self, json_obj):
        from google.auth import identity_pool

        return identity_pool.Credentials.from_info(json_obj)
    
    def _credentials_from_identity_pool_with_aws(self, json_obj):
        from google.auth import aws

        return aws.Credentials.from_info(json_obj)

    def _credentials_from_authorized_user(self, json_obj, scopes):
        import google.oauth2.credentials

        return google.oauth2.credentials.Credentials.from_authorized_user_info(
            json_obj, scopes=scopes
        )

    def _credentials_from_service_account(self, json_obj, scopes):
        import google.oauth2.service_account

        return google.oauth2.service_account.Credentials.from_service_account_info(
            json_obj, scopes=scopes
        )

    def _credentials_from_default_auth(self, scopes):
        import google.auth as google_auth

        return google_auth.default(scopes=scopes)

    def get_default_vertex_location(self) -> str:
        return "us-central1"

    def get_api_base(
        self, api_base: Optional[str], vertex_location: Optional[str]
    ) -> str:
        if api_base:
            return api_base
        elif vertex_location == "global":
            return "https://aiplatform.googleapis.com"
        elif vertex_location:
            return f"https://{vertex_location}-aiplatform.googleapis.com"
        else:
            return f"https://{self.get_default_vertex_location()}-aiplatform.googleapis.com"

    @staticmethod
    def create_vertex_url(
        vertex_location: str,
        vertex_project: str,
        partner: VertexPartnerProvider,
        stream: Optional[bool],
        model: str,
        api_base: Optional[str] = None,
    ) -> str:
        """Return the base url for the vertex partner models"""

        api_base = api_base or f"https://{vertex_location}-aiplatform.googleapis.com"
        if partner == VertexPartnerProvider.llama:
            return f"{api_base}/v1beta1/projects/{vertex_project}/locations/{vertex_location}/endpoints/openapi/chat/completions"
        elif partner == VertexPartnerProvider.mistralai:
            if stream:
                return f"{api_base}/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/mistralai/models/{model}:streamRawPredict"
            else:
                return f"{api_base}/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/mistralai/models/{model}:rawPredict"
        elif partner == VertexPartnerProvider.ai21:
            if stream:
                return f"{api_base}/v1beta1/projects/{vertex_project}/locations/{vertex_location}/publishers/ai21/models/{model}:streamRawPredict"
            else:
                return f"{api_base}/v1beta1/projects/{vertex_project}/locations/{vertex_location}/publishers/ai21/models/{model}:rawPredict"
        elif partner == VertexPartnerProvider.claude:
            if stream:
                return f"{api_base}/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/anthropic/models/{model}:streamRawPredict"
            else:
                return f"{api_base}/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/anthropic/models/{model}:rawPredict"

    def get_complete_vertex_url(
        self,
        custom_api_base: Optional[str],
        vertex_location: Optional[str],
        vertex_project: Optional[str],
        project_id: str,
        partner: VertexPartnerProvider,
        stream: Optional[bool],
        model: str,
    ) -> str:
        api_base = self.get_api_base(
            api_base=custom_api_base, vertex_location=vertex_location
        )
        default_api_base = VertexBase.create_vertex_url(
            vertex_location=vertex_location or "us-central1",
            vertex_project=vertex_project or project_id,
            partner=partner,
            stream=stream,
            model=model,
            api_base=api_base,
        )

        if len(default_api_base.split(":")) > 1:
            endpoint = default_api_base.split(":")[-1]
        else:
            endpoint = ""

        _, api_base = self._check_custom_proxy(
            api_base=custom_api_base,
            custom_llm_provider="vertex_ai",
            gemini_api_key=None,
            endpoint=endpoint,
            stream=stream,
            auth_header=None,
            url=default_api_base,
        )
        return api_base

    def refresh_auth(self, credentials: Any) -> None:
        from google.auth.transport.requests import (
            Request,  # type: ignore[import-untyped]
        )

        credentials.refresh(Request())

    def _ensure_access_token(
        self,
        credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        project_id: Optional[str],
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
    ) -> Tuple[str, str]:
        """
        Returns auth token and project id
        """
        if custom_llm_provider == "gemini":
            return "", ""
        else:
            return self.get_access_token(
                credentials=credentials,
                project_id=project_id,
            )

    def is_using_v1beta1_features(self, optional_params: dict) -> bool:
        """
        VertexAI only supports ContextCaching on v1beta1

        use this helper to decide if request should be sent to v1 or v1beta1

        Returns v1beta1 if context caching is enabled
        Returns v1 in all other cases
        """
        if "cached_content" in optional_params:
            return True
        if "CachedContent" in optional_params:
            return True
        return False

    def _check_custom_proxy(
        self,
        api_base: Optional[str],
        custom_llm_provider: str,
        gemini_api_key: Optional[str],
        endpoint: str,
        stream: Optional[bool],
        auth_header: Optional[str],
        url: str,
    ) -> Tuple[Optional[str], str]:
        """
        for cloudflare ai gateway - https://github.com/BerriAI/litellm/issues/4317

        ## Returns
        - (auth_header, url) - Tuple[Optional[str], str]
        """
        if api_base:
            if custom_llm_provider == "gemini":
                url = "{}:{}".format(api_base, endpoint)
                if gemini_api_key is None:
                    raise ValueError(
                        "Missing gemini_api_key, please set `GEMINI_API_KEY`"
                    )
                auth_header = (
                    gemini_api_key  # cloudflare expects api key as bearer token
                )
            else:
                url = "{}:{}".format(api_base, endpoint)

            if stream is True:
                url = url + "?alt=sse"
        return auth_header, url

    def _get_token_and_url(
        self,
        model: str,
        auth_header: Optional[str],
        gemini_api_key: Optional[str],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        stream: Optional[bool],
        custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"],
        api_base: Optional[str],
        should_use_v1beta1_features: Optional[bool] = False,
        mode: all_gemini_url_modes = "chat",
    ) -> Tuple[Optional[str], str]:
        """
        Internal function. Returns the token and url for the call.

        Handles logic if it's google ai studio vs. vertex ai.

        Returns
            token, url
        """
        if custom_llm_provider == "gemini":
            url, endpoint = _get_gemini_url(
                mode=mode,
                model=model,
                stream=stream,
                gemini_api_key=gemini_api_key,
            )
            auth_header = None  # this field is not used for gemin
        else:
            vertex_location = self.get_vertex_region(
                vertex_region=vertex_location,
                model=model,
            )

            ### SET RUNTIME ENDPOINT ###
            version: Literal["v1beta1", "v1"] = (
                "v1beta1" if should_use_v1beta1_features is True else "v1"
            )
            url, endpoint = _get_vertex_url(
                mode=mode,
                model=model,
                stream=stream,
                vertex_project=vertex_project,
                vertex_location=vertex_location,
                vertex_api_version=version,
            )

        return self._check_custom_proxy(
            api_base=api_base,
            auth_header=auth_header,
            custom_llm_provider=custom_llm_provider,
            gemini_api_key=gemini_api_key,
            endpoint=endpoint,
            stream=stream,
            url=url,
        )

    def get_access_token(
        self,
        credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        project_id: Optional[str],
    ) -> Tuple[str, str]:
        """
        Get access token and project id

        1. Check if credentials are already in self._credentials_project_mapping
        2. If not, load credentials and add to self._credentials_project_mapping
        3. Check if loaded credentials have expired
        4. If expired, refresh credentials
        5. Return access token and project id
        """

        # Convert dict credentials to string for caching
        cache_credentials = (
            json.dumps(credentials) if isinstance(credentials, dict) else credentials
        )
        credential_cache_key = (cache_credentials, project_id)
        _credentials: Optional[GoogleCredentialsObject] = None

        verbose_logger.debug(
            f"Checking cached credentials for project_id: {project_id}"
        )

        if credential_cache_key in self._credentials_project_mapping:
            verbose_logger.debug(
                f"Cached credentials found for project_id: {project_id}."
            )
            _credentials = self._credentials_project_mapping[credential_cache_key]
            verbose_logger.debug("Using cached credentials")
            credential_project_id = _credentials.quota_project_id or getattr(
                _credentials, "project_id", None
            )

        else:
            verbose_logger.debug(
                f"Credential cache key not found for project_id: {project_id}, loading new credentials"
            )

            try:
                _credentials, credential_project_id = self.load_auth(
                    credentials=credentials, project_id=project_id
                )
            except Exception as e:
                verbose_logger.exception(
                    f"Failed to load vertex credentials. Check to see if credentials containing partial/invalid information. Error: {str(e)}"
                )
                raise e

            if _credentials is None:
                raise ValueError(
                    "Could not resolve credentials - either dynamically or from environment, for project_id: {}".format(
                        project_id
                    )
                )

            self._credentials_project_mapping[credential_cache_key] = _credentials

        ## VALIDATE CREDENTIALS
        verbose_logger.debug(f"Validating credentials for project_id: {project_id}")
        if (
            project_id is None
            and credential_project_id is not None
            and isinstance(credential_project_id, str)
        ):
            project_id = credential_project_id

        if _credentials.expired:
            self.refresh_auth(_credentials)

        ## VALIDATION STEP
        if _credentials.token is None or not isinstance(_credentials.token, str):
            raise ValueError(
                "Could not resolve credentials token. Got None or non-string token - {}".format(
                    _credentials.token
                )
            )

        if project_id is None:
            raise ValueError("Could not resolve project_id")

        return _credentials.token, project_id

    async def _ensure_access_token_async(
        self,
        credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        project_id: Optional[str],
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
    ) -> Tuple[str, str]:
        """
        Async version of _ensure_access_token
        """
        if custom_llm_provider == "gemini":
            return "", ""
        else:
            try:
                return await asyncify(self.get_access_token)(
                    credentials=credentials,
                    project_id=project_id,
                )
            except Exception as e:
                raise e

    def set_headers(
        self, auth_header: Optional[str], extra_headers: Optional[dict]
    ) -> dict:
        headers = {
            "Content-Type": "application/json",
        }
        if auth_header is not None:
            headers["Authorization"] = f"Bearer {auth_header}"
        if extra_headers is not None:
            headers.update(extra_headers)

        return headers

# === NexusCore/openenv\Lib\site-packages\blessed\formatters.py ===
"""Sub-module providing sequence-formatting functions."""
# std imports
import platform

# local
from blessed._compat import TextType, StringType
from blessed.colorspace import CGA_COLORS, X11_COLORNAMES_TO_RGB

# isort: off
# curses
if platform.system() == 'Windows':
    import jinxed as curses   # pylint: disable=import-error
else:
    import curses


def _make_colors():
    """
    Return set of valid colors and their derivatives.

    :rtype: set
    :returns: Color names with prefixes
    """
    colors = set()
    # basic CGA foreground color, background, high intensity, and bold
    # background ('iCE colors' in my day).
    for cga_color in CGA_COLORS:
        colors.add(cga_color)
        colors.add('on_' + cga_color)
        colors.add('bright_' + cga_color)
        colors.add('on_bright_' + cga_color)

    # foreground and background VGA color
    for vga_color in X11_COLORNAMES_TO_RGB:
        colors.add(vga_color)
        colors.add('on_' + vga_color)
    return colors


#: Valid colors and their background (on), bright, and bright-background
#: derivatives.
COLORS = _make_colors()

#: Attributes that may be compounded with colors, by underscore, such as
#: 'reverse_indigo'.
COMPOUNDABLES = set('bold underline reverse blink italic standout'.split())


class ParameterizingString(TextType):
    r"""
    A Unicode string which can be called as a parameterizing termcap.

    For example::

        >>> from blessed import Terminal
        >>> term = Terminal()
        >>> color = ParameterizingString(term.color, term.normal, 'color')
        >>> color(9)('color #9')
        u'\x1b[91mcolor #9\x1b(B\x1b[m'
    """

    def __new__(cls, cap, normal=u'', name=u'<not specified>'):
        # pylint: disable = missing-return-doc, missing-return-type-doc
        """
        Class constructor accepting 3 positional arguments.

        :arg str cap: parameterized string suitable for curses.tparm()
        :arg str normal: terminating sequence for this capability (optional).
        :arg str name: name of this terminal capability (optional).
        """
        new = TextType.__new__(cls, cap)
        new._normal = normal
        new._name = name
        return new

    def __call__(self, *args):
        """
        Returning :class:`FormattingString` instance for given parameters.

        Return evaluated terminal capability (self), receiving arguments
        ``*args``, followed by the terminating sequence (self.normal) into
        a :class:`FormattingString` capable of being called.

        :raises TypeError: Mismatch between capability and arguments
        :raises curses.error: :func:`curses.tparm` raised an exception
        :rtype: :class:`FormattingString` or :class:`NullCallableString`
        :returns: Callable string for given parameters
        """
        try:
            # Re-encode the cap, because tparm() takes a bytestring in Python
            # 3. However, appear to be a plain Unicode string otherwise so
            # concats work.
            attr = curses.tparm(self.encode('latin1'), *args).decode('latin1')
            return FormattingString(attr, self._normal)
        except TypeError as err:
            # If the first non-int (i.e. incorrect) arg was a string, suggest
            # something intelligent:
            if args and isinstance(args[0], StringType):
                raise TypeError(
                    "Unknown terminal capability, %r, or, TypeError "
                    "for arguments %r: %s" % (self._name, args, err))
            # Somebody passed a non-string; I don't feel confident
            # guessing what they were trying to do.
            raise
        except curses.error as err:
            # ignore 'tparm() returned NULL', you won't get any styling,
            # even if does_styling is True. This happens on win32 platforms
            # with http://www.lfd.uci.edu/~gohlke/pythonlibs/#curses installed
            if "tparm() returned NULL" not in TextType(err):
                raise
            return NullCallableString()


class ParameterizingProxyString(TextType):
    r"""
    A Unicode string which can be called to proxy missing termcap entries.

    This class supports the function :func:`get_proxy_string`, and mirrors
    the behavior of :class:`ParameterizingString`, except that instead of
    a capability name, receives a format string, and callable to filter the
    given positional ``*args`` of :meth:`ParameterizingProxyString.__call__`
    into a terminal sequence.

    For example::

        >>> from blessed import Terminal
        >>> term = Terminal('screen')
        >>> hpa = ParameterizingString(term.hpa, term.normal, 'hpa')
        >>> hpa(9)
        u''
        >>> fmt = u'\x1b[{0}G'
        >>> fmt_arg = lambda *arg: (arg[0] + 1,)
        >>> hpa = ParameterizingProxyString((fmt, fmt_arg), term.normal, 'hpa')
        >>> hpa(9)
        u'\x1b[10G'
    """

    def __new__(cls, fmt_pair, normal=u'', name=u'<not specified>'):
        # pylint: disable = missing-return-doc, missing-return-type-doc
        """
        Class constructor accepting 4 positional arguments.

        :arg tuple fmt_pair: Two element tuple containing:
            - format string suitable for displaying terminal sequences
            - callable suitable for receiving  __call__ arguments for formatting string
        :arg str normal: terminating sequence for this capability (optional).
        :arg str name: name of this terminal capability (optional).
        """
        assert isinstance(fmt_pair, tuple), fmt_pair
        assert callable(fmt_pair[1]), fmt_pair[1]
        new = TextType.__new__(cls, fmt_pair[0])
        new._fmt_args = fmt_pair[1]
        new._normal = normal
        new._name = name
        return new

    def __call__(self, *args):
        """
        Returning :class:`FormattingString` instance for given parameters.

        Arguments are determined by the capability.  For example, ``hpa``
        (move_x) receives only a single integer, whereas ``cup`` (move)
        receives two integers.  See documentation in terminfo(5) for the
        given capability.

        :rtype: FormattingString
        :returns: Callable string for given parameters
        """
        return FormattingString(self.format(*self._fmt_args(*args)),
                                self._normal)


class FormattingString(TextType):
    r"""
    A Unicode string which doubles as a callable.

    This is used for terminal attributes, so that it may be used both
    directly, or as a callable.  When used directly, it simply emits
    the given terminal sequence.  When used as a callable, it wraps the
    given (string) argument with the 2nd argument used by the class
    constructor::

        >>> from blessed import Terminal
        >>> term = Terminal()
        >>> style = FormattingString(term.bright_blue, term.normal)
        >>> print(repr(style))
        u'\x1b[94m'
        >>> style('Big Blue')
        u'\x1b[94mBig Blue\x1b(B\x1b[m'
    """

    def __new__(cls, sequence, normal=u''):
        # pylint: disable = missing-return-doc, missing-return-type-doc
        """
        Class constructor accepting 2 positional arguments.

        :arg str sequence: terminal attribute sequence.
        :arg str normal: terminating sequence for this attribute (optional).
        """
        new = TextType.__new__(cls, sequence)
        new._normal = normal
        return new

    def __call__(self, *args):
        """
        Return ``text`` joined by ``sequence`` and ``normal``.

        :raises TypeError: Not a string type
        :rtype: str
        :returns: Arguments wrapped in sequence and normal
        """
        # Jim Allman brings us this convenience of allowing existing
        # unicode strings to be joined as a call parameter to a formatting
        # string result, allowing nestation:
        #
        # >>> t.red('This is ', t.bold('extremely'), ' dangerous!')
        for idx, ucs_part in enumerate(args):
            if not isinstance(ucs_part, StringType):
                raise TypeError(
                    "TypeError for FormattingString argument, %r, at position %s: expected type "
                    "%s, got %s" % (ucs_part, idx, StringType.__name__, type(ucs_part).__name__)
                )
        postfix = u''
        if self and self._normal:
            postfix = self._normal
            _refresh = self._normal + self
            args = [_refresh.join(ucs_part.split(self._normal))
                    for ucs_part in args]

        return self + u''.join(args) + postfix


class FormattingOtherString(TextType):
    r"""
    A Unicode string which doubles as a callable for another sequence when called.

    This is used for the :meth:`~.Terminal.move_up`, ``down``, ``left``, and ``right()``
    family of functions::

        >>> from blessed import Terminal
        >>> term = Terminal()
        >>> move_right = FormattingOtherString(term.cuf1, term.cuf)
        >>> print(repr(move_right))
        u'\x1b[C'
        >>> print(repr(move_right(666)))
        u'\x1b[666C'
        >>> print(repr(move_right()))
        u'\x1b[C'
    """

    def __new__(cls, direct, target):
        # pylint: disable = missing-return-doc, missing-return-type-doc
        """
        Class constructor accepting 2 positional arguments.

        :arg str direct: capability name for direct formatting, eg ``('x' + term.right)``.
        :arg str target: capability name for callable, eg ``('x' + term.right(99))``.
        """
        new = TextType.__new__(cls, direct)
        new._callable = target
        return new

    def __getnewargs__(self):
        # return arguments used for the __new__ method upon unpickling.
        return TextType.__new__(TextType, self), self._callable

    def __call__(self, *args):
        """Return ``text`` by ``target``."""
        return self._callable(*args) if args else self


class NullCallableString(TextType):
    """
    A dummy callable Unicode alternative to :class:`FormattingString`.

    This is used for colors on terminals that do not support colors, it is just a basic form of
    unicode that may also act as a callable.
    """

    def __new__(cls):
        """Class constructor."""
        return TextType.__new__(cls, u'')

    def __call__(self, *args):
        """
        Allow empty string to be callable, returning given string, if any.

        When called with an int as the first arg, return an empty Unicode. An int is a good hint
        that I am a :class:`ParameterizingString`, as there are only about half a dozen string-
        returning capabilities listed in terminfo(5) which accept non-int arguments, they are seldom
        used.

        When called with a non-int as the first arg (no no args at all), return the first arg,
        acting in place of :class:`FormattingString` without any attributes.
        """
        if not args or isinstance(args[0], int):
            # As a NullCallableString, even when provided with a parameter,
            # such as t.color(5), we must also still be callable, fe:
            #
            # >>> t.color(5)('shmoo')
            #
            # is actually simplified result of NullCallable()() on terminals
            # without color support, so turtles all the way down: we return
            # another instance.
            return NullCallableString()
        return u''.join(args)


def get_proxy_string(term, attr):
    """
    Proxy and return callable string for proxied attributes.

    :arg Terminal term: :class:`~.Terminal` instance.
    :arg str attr: terminal capability name that may be proxied.
    :rtype: None or :class:`ParameterizingProxyString`.
    :returns: :class:`ParameterizingProxyString` for some attributes
        of some terminal types that support it, where the terminfo(5)
        database would otherwise come up empty, such as ``move_x``
        attribute for ``term.kind`` of ``screen``.  Otherwise, None.
    """
    # normalize 'screen-256color', or 'ansi.sys' to its basic names
    term_kind = next(iter(_kind for _kind in ('screen', 'ansi',)
                          if term.kind.startswith(_kind)), term)
    _proxy_table = {  # pragma: no cover
        'screen': {
            # proxy move_x/move_y for 'screen' terminal type, used by tmux(1).
            'hpa': ParameterizingProxyString(
                (u'\x1b[{0}G', lambda *arg: (arg[0] + 1,)), term.normal, attr),
            'vpa': ParameterizingProxyString(
                (u'\x1b[{0}d', lambda *arg: (arg[0] + 1,)), term.normal, attr),
        },
        'ansi': {
            # proxy show/hide cursor for 'ansi' terminal type.  There is some
            # demand for a richly working ANSI terminal type for some reason.
            'civis': ParameterizingProxyString(
                (u'\x1b[?25l', lambda *arg: ()), term.normal, attr),
            'cnorm': ParameterizingProxyString(
                (u'\x1b[?25h', lambda *arg: ()), term.normal, attr),
            'hpa': ParameterizingProxyString(
                (u'\x1b[{0}G', lambda *arg: (arg[0] + 1,)), term.normal, attr),
            'vpa': ParameterizingProxyString(
                (u'\x1b[{0}d', lambda *arg: (arg[0] + 1,)), term.normal, attr),
            'sc': '\x1b[s',
            'rc': '\x1b[u',
        }
    }
    return _proxy_table.get(term_kind, {}).get(attr, None)


def split_compound(compound):
    """
    Split compound formating string into segments.

    >>> split_compound('bold_underline_bright_blue_on_red')
    ['bold', 'underline', 'bright_blue', 'on_red']

    :arg str compound: a string that may contain compounds, separated by
        underline (``_``).
    :rtype: list
    :returns: List of formating string segments
    """
    merged_segs = []
    # These occur only as prefixes, so they can always be merged:
    mergeable_prefixes = ['on', 'bright', 'on_bright']
    for segment in compound.split('_'):
        if merged_segs and merged_segs[-1] in mergeable_prefixes:
            merged_segs[-1] += '_' + segment
        else:
            merged_segs.append(segment)
    return merged_segs


def resolve_capability(term, attr):
    """
    Resolve a raw terminal capability using :func:`tigetstr`.

    :arg Terminal term: :class:`~.Terminal` instance.
    :arg str attr: terminal capability name.
    :returns: string of the given terminal capability named by ``attr``,
       which may be empty (u'') if not found or not supported by the
       given :attr:`~.Terminal.kind`.
    :rtype: str
    """
    if not term.does_styling:
        return u''
    val = curses.tigetstr(term._sugar.get(attr, attr))  # pylint: disable=protected-access
    # Decode sequences as latin1, as they are always 8-bit bytes, so when
    # b'\xff' is returned, this is decoded as u'\xff'.
    return u'' if val is None else val.decode('latin1')


def resolve_color(term, color):
    """
    Resolve a simple color name to a callable capability.

    This function supports :func:`resolve_attribute`.

    :arg Terminal term: :class:`~.Terminal` instance.
    :arg str color: any string found in set :const:`COLORS`.
    :returns: a string class instance which emits the terminal sequence
        for the given color, and may be used as a callable to wrap the
        given string with such sequence.
    :returns: :class:`NullCallableString` when
        :attr:`~.Terminal.number_of_colors` is 0,
        otherwise :class:`FormattingString`.
    :rtype: :class:`NullCallableString` or :class:`FormattingString`
    """
    # pylint: disable=protected-access
    if term.number_of_colors == 0:
        return NullCallableString()

    # fg/bg capabilities terminals that support 0-256+ colors.
    vga_color_cap = (term._background_color if 'on_' in color else
                     term._foreground_color)

    base_color = color.rsplit('_', 1)[-1]
    if base_color in CGA_COLORS:
        # curses constants go up to only 7, so add an offset to get at the
        # bright colors at 8-15:
        offset = 8 if 'bright_' in color else 0
        base_color = color.rsplit('_', 1)[-1]
        attr = 'COLOR_%s' % (base_color.upper(),)
        fmt_attr = vga_color_cap(getattr(curses, attr) + offset)
        return FormattingString(fmt_attr, term.normal)

    assert base_color in X11_COLORNAMES_TO_RGB, (
        'color not known', base_color)
    rgb = X11_COLORNAMES_TO_RGB[base_color]

    # downconvert X11 colors to CGA, EGA, or VGA color spaces
    if term.number_of_colors <= 256:
        fmt_attr = vga_color_cap(term.rgb_downconvert(*rgb))
        return FormattingString(fmt_attr, term.normal)

    # Modern 24-bit color terminals are written pretty basically.  The
    # foreground and background sequences are:
    # - ^[38;2;<r>;<g>;<b>m
    # - ^[48;2;<r>;<g>;<b>m
    fgbg_seq = ('48' if 'on_' in color else '38')
    assert term.number_of_colors == 1 << 24
    fmt_attr = u'\x1b[' + fgbg_seq + ';2;{0};{1};{2}m'
    return FormattingString(fmt_attr.format(*rgb), term.normal)


def resolve_attribute(term, attr):
    """
    Resolve a terminal attribute name into a capability class.

    :arg Terminal term: :class:`~.Terminal` instance.
    :arg str attr: Sugary, ordinary, or compound formatted terminal
        capability, such as "red_on_white", "normal", "red", or
        "bold_on_black".
    :returns: a string class instance which emits the terminal sequence
        for the given terminal capability, or may be used as a callable to
        wrap the given string with such sequence.
    :returns: :class:`NullCallableString` when
        :attr:`~.Terminal.number_of_colors` is 0,
        otherwise :class:`FormattingString`.
    :rtype: :class:`NullCallableString` or :class:`FormattingString`
    """
    if attr in COLORS:
        return resolve_color(term, attr)

    # A direct compoundable, such as `bold' or `on_red'.
    if attr in COMPOUNDABLES:
        sequence = resolve_capability(term, attr)
        return FormattingString(sequence, term.normal)

    # Given `bold_on_red', resolve to ('bold', 'on_red'), RECURSIVE
    # call for each compounding section, joined and returned as
    # a completed completed FormattingString.
    formatters = split_compound(attr)
    if all((fmt in COLORS or fmt in COMPOUNDABLES) for fmt in formatters):
        resolution = (resolve_attribute(term, fmt) for fmt in formatters)
        return FormattingString(u''.join(resolution), term.normal)

    # otherwise, this is our end-game: given a sequence such as 'csr'
    # (change scrolling region), return a ParameterizingString instance,
    # that when called, performs and returns the final string after curses
    # capability lookup is performed.
    tparm_capseq = resolve_capability(term, attr)
    if not tparm_capseq:
        # and, for special terminals, such as 'screen', provide a Proxy
        # ParameterizingString for attributes they do not claim to support,
        # but actually do! (such as 'hpa' and 'vpa').
        proxy = get_proxy_string(term,
                                 term._sugar.get(attr, attr))  # pylint: disable=protected-access
        if proxy is not None:
            return proxy

    return ParameterizingString(tparm_capseq, term.normal, attr)

# === NexusCore/openenv\Lib\site-packages\wsproto\handshake.py ===
"""
wsproto/handshake
~~~~~~~~~~~~~~~~~~

An implementation of WebSocket handshakes.
"""
from collections import deque
from typing import (
    cast,
    Deque,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Sequence,
    Union,
)

import h11

from .connection import Connection, ConnectionState, ConnectionType
from .events import AcceptConnection, Event, RejectConnection, RejectData, Request
from .extensions import Extension
from .typing import Headers
from .utilities import (
    generate_accept_token,
    generate_nonce,
    LocalProtocolError,
    normed_header_dict,
    RemoteProtocolError,
    split_comma_header,
)

# RFC6455, Section 4.2.1/6 - Reading the Client's Opening Handshake
WEBSOCKET_VERSION = b"13"


class H11Handshake:
    """A Handshake implementation for HTTP/1.1 connections."""

    def __init__(self, connection_type: ConnectionType) -> None:
        self.client = connection_type is ConnectionType.CLIENT
        self._state = ConnectionState.CONNECTING

        if self.client:
            self._h11_connection = h11.Connection(h11.CLIENT)
        else:
            self._h11_connection = h11.Connection(h11.SERVER)

        self._connection: Optional[Connection] = None
        self._events: Deque[Event] = deque()
        self._initiating_request: Optional[Request] = None
        self._nonce: Optional[bytes] = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def connection(self) -> Optional[Connection]:
        """Return the established connection.

        This will either return the connection or raise a
        LocalProtocolError if the connection has not yet been
        established.

        :rtype: h11.Connection
        """
        return self._connection

    def initiate_upgrade_connection(
        self, headers: Headers, path: Union[bytes, str]
    ) -> None:
        """Initiate an upgrade connection.

        This should be used if the request has already be received and
        parsed.

        :param list headers: HTTP headers represented as a list of 2-tuples.
        :param str path: A URL path.
        """
        if self.client:
            raise LocalProtocolError(
                "Cannot initiate an upgrade connection when acting as the client"
            )
        upgrade_request = h11.Request(method=b"GET", target=path, headers=headers)
        h11_client = h11.Connection(h11.CLIENT)
        self.receive_data(h11_client.send(upgrade_request))

    def send(self, event: Event) -> bytes:
        """Send an event to the remote.

        This will return the bytes to send based on the event or raise
        a LocalProtocolError if the event is not valid given the
        state.

        :returns: Data to send to the WebSocket peer.
        :rtype: bytes
        """
        data = b""
        if isinstance(event, Request):
            data += self._initiate_connection(event)
        elif isinstance(event, AcceptConnection):
            data += self._accept(event)
        elif isinstance(event, RejectConnection):
            data += self._reject(event)
        elif isinstance(event, RejectData):
            data += self._send_reject_data(event)
        else:
            raise LocalProtocolError(
                f"Event {event} cannot be sent during the handshake"
            )
        return data

    def receive_data(self, data: Optional[bytes]) -> None:
        """Receive data from the remote.

        A list of events that the remote peer triggered by sending
        this data can be retrieved with :meth:`events`.

        :param bytes data: Data received from the WebSocket peer.
        """
        self._h11_connection.receive_data(data or b"")
        while True:
            try:
                event = self._h11_connection.next_event()
            except h11.RemoteProtocolError:
                raise RemoteProtocolError(
                    "Bad HTTP message", event_hint=RejectConnection()
                )
            if (
                isinstance(event, h11.ConnectionClosed)
                or event is h11.NEED_DATA
                or event is h11.PAUSED
            ):
                break

            if self.client:
                if isinstance(event, h11.InformationalResponse):
                    if event.status_code == 101:
                        self._events.append(self._establish_client_connection(event))
                    else:
                        self._events.append(
                            RejectConnection(
                                headers=list(event.headers),
                                status_code=event.status_code,
                                has_body=False,
                            )
                        )
                        self._state = ConnectionState.CLOSED
                elif isinstance(event, h11.Response):
                    self._state = ConnectionState.REJECTING
                    self._events.append(
                        RejectConnection(
                            headers=list(event.headers),
                            status_code=event.status_code,
                            has_body=True,
                        )
                    )
                elif isinstance(event, h11.Data):
                    self._events.append(
                        RejectData(data=event.data, body_finished=False)
                    )
                elif isinstance(event, h11.EndOfMessage):
                    self._events.append(RejectData(data=b"", body_finished=True))
                    self._state = ConnectionState.CLOSED
            else:
                if isinstance(event, h11.Request):
                    self._events.append(self._process_connection_request(event))

    def events(self) -> Generator[Event, None, None]:
        """Return a generator that provides any events that have been generated
        by protocol activity.

        :returns: a generator that yields H11 events.
        """
        while self._events:
            yield self._events.popleft()

    # Server mode methods

    def _process_connection_request(  # noqa: MC0001
        self, event: h11.Request
    ) -> Request:
        if event.method != b"GET":
            raise RemoteProtocolError(
                "Request method must be GET", event_hint=RejectConnection()
            )
        connection_tokens = None
        extensions: List[str] = []
        host = None
        key = None
        subprotocols: List[str] = []
        upgrade = b""
        version = None
        headers: Headers = []
        for name, value in event.headers:
            name = name.lower()
            if name == b"connection":
                connection_tokens = split_comma_header(value)
            elif name == b"host":
                host = value.decode("idna")
                continue  # Skip appending to headers
            elif name == b"sec-websocket-extensions":
                extensions.extend(split_comma_header(value))
                continue  # Skip appending to headers
            elif name == b"sec-websocket-key":
                key = value
            elif name == b"sec-websocket-protocol":
                subprotocols.extend(split_comma_header(value))
                continue  # Skip appending to headers
            elif name == b"sec-websocket-version":
                version = value
            elif name == b"upgrade":
                upgrade = value
            headers.append((name, value))
        if connection_tokens is None or not any(
            token.lower() == "upgrade" for token in connection_tokens
        ):
            raise RemoteProtocolError(
                "Missing header, 'Connection: Upgrade'", event_hint=RejectConnection()
            )
        if version != WEBSOCKET_VERSION:
            raise RemoteProtocolError(
                "Missing header, 'Sec-WebSocket-Version'",
                event_hint=RejectConnection(
                    headers=[(b"Sec-WebSocket-Version", WEBSOCKET_VERSION)],
                    status_code=426 if version else 400,
                ),
            )
        if key is None:
            raise RemoteProtocolError(
                "Missing header, 'Sec-WebSocket-Key'", event_hint=RejectConnection()
            )
        if upgrade.lower() != b"websocket":
            raise RemoteProtocolError(
                "Missing header, 'Upgrade: WebSocket'", event_hint=RejectConnection()
            )
        if host is None:
            raise RemoteProtocolError(
                "Missing header, 'Host'", event_hint=RejectConnection()
            )

        self._initiating_request = Request(
            extensions=extensions,
            extra_headers=headers,
            host=host,
            subprotocols=subprotocols,
            target=event.target.decode("ascii"),
        )
        return self._initiating_request

    def _accept(self, event: AcceptConnection) -> bytes:
        # _accept is always called after _process_connection_request.
        assert self._initiating_request is not None
        request_headers = normed_header_dict(self._initiating_request.extra_headers)

        nonce = request_headers[b"sec-websocket-key"]
        accept_token = generate_accept_token(nonce)

        headers = [
            (b"Upgrade", b"WebSocket"),
            (b"Connection", b"Upgrade"),
            (b"Sec-WebSocket-Accept", accept_token),
        ]

        if event.subprotocol is not None:
            if event.subprotocol not in self._initiating_request.subprotocols:
                raise LocalProtocolError(f"unexpected subprotocol {event.subprotocol}")
            headers.append(
                (b"Sec-WebSocket-Protocol", event.subprotocol.encode("ascii"))
            )

        if event.extensions:
            accepts = server_extensions_handshake(
                cast(Sequence[str], self._initiating_request.extensions),
                event.extensions,
            )
            if accepts:
                headers.append((b"Sec-WebSocket-Extensions", accepts))

        response = h11.InformationalResponse(
            status_code=101, headers=headers + event.extra_headers
        )
        self._connection = Connection(
            ConnectionType.CLIENT if self.client else ConnectionType.SERVER,
            event.extensions,
        )
        self._state = ConnectionState.OPEN
        return self._h11_connection.send(response) or b""

    def _reject(self, event: RejectConnection) -> bytes:
        if self.state != ConnectionState.CONNECTING:
            raise LocalProtocolError(
                "Connection cannot be rejected in state %s" % self.state
            )

        headers = list(event.headers)
        if not event.has_body:
            headers.append((b"content-length", b"0"))
        response = h11.Response(status_code=event.status_code, headers=headers)
        data = self._h11_connection.send(response) or b""
        self._state = ConnectionState.REJECTING
        if not event.has_body:
            data += self._h11_connection.send(h11.EndOfMessage()) or b""
            self._state = ConnectionState.CLOSED
        return data

    def _send_reject_data(self, event: RejectData) -> bytes:
        if self.state != ConnectionState.REJECTING:
            raise LocalProtocolError(
                f"Cannot send rejection data in state {self.state}"
            )

        data = self._h11_connection.send(h11.Data(data=event.data)) or b""
        if event.body_finished:
            data += self._h11_connection.send(h11.EndOfMessage()) or b""
            self._state = ConnectionState.CLOSED
        return data

    # Client mode methods

    def _initiate_connection(self, request: Request) -> bytes:
        self._initiating_request = request
        self._nonce = generate_nonce()

        headers = [
            (b"Host", request.host.encode("idna")),
            (b"Upgrade", b"WebSocket"),
            (b"Connection", b"Upgrade"),
            (b"Sec-WebSocket-Key", self._nonce),
            (b"Sec-WebSocket-Version", WEBSOCKET_VERSION),
        ]

        if request.subprotocols:
            headers.append(
                (
                    b"Sec-WebSocket-Protocol",
                    (", ".join(request.subprotocols)).encode("ascii"),
                )
            )

        if request.extensions:
            offers: Dict[str, Union[str, bool]] = {}
            for e in request.extensions:
                assert isinstance(e, Extension)
                offers[e.name] = e.offer()
            extensions = []
            for name, params in offers.items():
                bname = name.encode("ascii")
                if isinstance(params, bool):
                    if params:
                        extensions.append(bname)
                else:
                    extensions.append(b"%s; %s" % (bname, params.encode("ascii")))
            if extensions:
                headers.append((b"Sec-WebSocket-Extensions", b", ".join(extensions)))

        upgrade = h11.Request(
            method=b"GET",
            target=request.target.encode("ascii"),
            headers=headers + request.extra_headers,
        )
        return self._h11_connection.send(upgrade) or b""

    def _establish_client_connection(
        self, event: h11.InformationalResponse
    ) -> AcceptConnection:  # noqa: MC0001
        # _establish_client_connection is always called after _initiate_connection.
        assert self._initiating_request is not None
        assert self._nonce is not None

        accept = None
        connection_tokens = None
        accepts: List[str] = []
        subprotocol = None
        upgrade = b""
        headers: Headers = []
        for name, value in event.headers:
            name = name.lower()
            if name == b"connection":
                connection_tokens = split_comma_header(value)
                continue  # Skip appending to headers
            elif name == b"sec-websocket-extensions":
                accepts = split_comma_header(value)
                continue  # Skip appending to headers
            elif name == b"sec-websocket-accept":
                accept = value
                continue  # Skip appending to headers
            elif name == b"sec-websocket-protocol":
                subprotocol = value.decode("ascii")
                continue  # Skip appending to headers
            elif name == b"upgrade":
                upgrade = value
                continue  # Skip appending to headers
            headers.append((name, value))

        if connection_tokens is None or not any(
            token.lower() == "upgrade" for token in connection_tokens
        ):
            raise RemoteProtocolError(
                "Missing header, 'Connection: Upgrade'", event_hint=RejectConnection()
            )
        if upgrade.lower() != b"websocket":
            raise RemoteProtocolError(
                "Missing header, 'Upgrade: WebSocket'", event_hint=RejectConnection()
            )
        accept_token = generate_accept_token(self._nonce)
        if accept != accept_token:
            raise RemoteProtocolError("Bad accept token", event_hint=RejectConnection())
        if subprotocol is not None:
            if subprotocol not in self._initiating_request.subprotocols:
                raise RemoteProtocolError(
                    f"unrecognized subprotocol {subprotocol}",
                    event_hint=RejectConnection(),
                )
        extensions = client_extensions_handshake(
            accepts, cast(Sequence[Extension], self._initiating_request.extensions)
        )

        self._connection = Connection(
            ConnectionType.CLIENT if self.client else ConnectionType.SERVER,
            extensions,
            self._h11_connection.trailing_data[0],
        )
        self._state = ConnectionState.OPEN
        return AcceptConnection(
            extensions=extensions, extra_headers=headers, subprotocol=subprotocol
        )

    def __repr__(self) -> str:
        return "{}(client={}, state={})".format(
            self.__class__.__name__, self.client, self.state
        )


def server_extensions_handshake(
    requested: Iterable[str], supported: List[Extension]
) -> Optional[bytes]:
    """Agree on the extensions to use returning an appropriate header value.

    This returns None if there are no agreed extensions
    """
    accepts: Dict[str, Union[bool, bytes]] = {}
    for offer in requested:
        name = offer.split(";", 1)[0].strip()
        for extension in supported:
            if extension.name == name:
                accept = extension.accept(offer)
                if isinstance(accept, bool):
                    if accept:
                        accepts[extension.name] = True
                elif accept is not None:
                    accepts[extension.name] = accept.encode("ascii")

    if accepts:
        extensions: List[bytes] = []
        for name, params in accepts.items():
            name_bytes = name.encode("ascii")
            if isinstance(params, bool):
                assert params
                extensions.append(name_bytes)
            else:
                if params == b"":
                    extensions.append(b"%s" % (name_bytes))
                else:
                    extensions.append(b"%s; %s" % (name_bytes, params))
        return b", ".join(extensions)

    return None


def client_extensions_handshake(
    accepted: Iterable[str], supported: Sequence[Extension]
) -> List[Extension]:
    # This raises RemoteProtocolError is the accepted extension is not
    # supported.
    extensions = []
    for accept in accepted:
        name = accept.split(";", 1)[0].strip()
        for extension in supported:
            if extension.name == name:
                extension.finalize(accept)
                extensions.append(extension)
                break
        else:
            raise RemoteProtocolError(
                f"unrecognized extension {name}", event_hint=RejectConnection()
            )
    return extensions

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\animation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Animation (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


@dataclass
class Animation:
    '''
    Animation instance.
    '''
    #: ``Animation``'s id.
    id_: str

    #: ``Animation``'s name.
    name: str

    #: ``Animation``'s internal paused state.
    paused_state: bool

    #: ``Animation``'s play state.
    play_state: str

    #: ``Animation``'s playback rate.
    playback_rate: float

    #: ``Animation``'s start time.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    start_time: float

    #: ``Animation``'s current time.
    current_time: float

    #: Animation type of ``Animation``.
    type_: str

    #: ``Animation``'s source animation node.
    source: typing.Optional[AnimationEffect] = None

    #: A unique ID for ``Animation`` representing the sources that triggered this CSS
    #: animation/transition.
    css_id: typing.Optional[str] = None

    #: View or scroll timeline
    view_or_scroll_timeline: typing.Optional[ViewOrScrollTimeline] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['name'] = self.name
        json['pausedState'] = self.paused_state
        json['playState'] = self.play_state
        json['playbackRate'] = self.playback_rate
        json['startTime'] = self.start_time
        json['currentTime'] = self.current_time
        json['type'] = self.type_
        if self.source is not None:
            json['source'] = self.source.to_json()
        if self.css_id is not None:
            json['cssId'] = self.css_id
        if self.view_or_scroll_timeline is not None:
            json['viewOrScrollTimeline'] = self.view_or_scroll_timeline.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            name=str(json['name']),
            paused_state=bool(json['pausedState']),
            play_state=str(json['playState']),
            playback_rate=float(json['playbackRate']),
            start_time=float(json['startTime']),
            current_time=float(json['currentTime']),
            type_=str(json['type']),
            source=AnimationEffect.from_json(json['source']) if 'source' in json else None,
            css_id=str(json['cssId']) if 'cssId' in json else None,
            view_or_scroll_timeline=ViewOrScrollTimeline.from_json(json['viewOrScrollTimeline']) if 'viewOrScrollTimeline' in json else None,
        )


@dataclass
class ViewOrScrollTimeline:
    '''
    Timeline instance
    '''
    #: Orientation of the scroll
    axis: dom.ScrollOrientation

    #: Scroll container node
    source_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Represents the starting scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    start_offset: typing.Optional[float] = None

    #: Represents the ending scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    end_offset: typing.Optional[float] = None

    #: The element whose principal box's visibility in the
    #: scrollport defined the progress of the timeline.
    #: Does not exist for animations with ScrollTimeline
    subject_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['axis'] = self.axis.to_json()
        if self.source_node_id is not None:
            json['sourceNodeId'] = self.source_node_id.to_json()
        if self.start_offset is not None:
            json['startOffset'] = self.start_offset
        if self.end_offset is not None:
            json['endOffset'] = self.end_offset
        if self.subject_node_id is not None:
            json['subjectNodeId'] = self.subject_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            axis=dom.ScrollOrientation.from_json(json['axis']),
            source_node_id=dom.BackendNodeId.from_json(json['sourceNodeId']) if 'sourceNodeId' in json else None,
            start_offset=float(json['startOffset']) if 'startOffset' in json else None,
            end_offset=float(json['endOffset']) if 'endOffset' in json else None,
            subject_node_id=dom.BackendNodeId.from_json(json['subjectNodeId']) if 'subjectNodeId' in json else None,
        )


@dataclass
class AnimationEffect:
    '''
    AnimationEffect instance
    '''
    #: ``AnimationEffect``'s delay.
    delay: float

    #: ``AnimationEffect``'s end delay.
    end_delay: float

    #: ``AnimationEffect``'s iteration start.
    iteration_start: float

    #: ``AnimationEffect``'s iterations.
    iterations: float

    #: ``AnimationEffect``'s iteration duration.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    duration: float

    #: ``AnimationEffect``'s playback direction.
    direction: str

    #: ``AnimationEffect``'s fill mode.
    fill: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    #: ``AnimationEffect``'s target node.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: ``AnimationEffect``'s keyframes.
    keyframes_rule: typing.Optional[KeyframesRule] = None

    def to_json(self):
        json = dict()
        json['delay'] = self.delay
        json['endDelay'] = self.end_delay
        json['iterationStart'] = self.iteration_start
        json['iterations'] = self.iterations
        json['duration'] = self.duration
        json['direction'] = self.direction
        json['fill'] = self.fill
        json['easing'] = self.easing
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.keyframes_rule is not None:
            json['keyframesRule'] = self.keyframes_rule.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            delay=float(json['delay']),
            end_delay=float(json['endDelay']),
            iteration_start=float(json['iterationStart']),
            iterations=float(json['iterations']),
            duration=float(json['duration']),
            direction=str(json['direction']),
            fill=str(json['fill']),
            easing=str(json['easing']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            keyframes_rule=KeyframesRule.from_json(json['keyframesRule']) if 'keyframesRule' in json else None,
        )


@dataclass
class KeyframesRule:
    '''
    Keyframes Rule
    '''
    #: List of animation keyframes.
    keyframes: typing.List[KeyframeStyle]

    #: CSS keyframed animation's name.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyframes'] = [i.to_json() for i in self.keyframes]
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            keyframes=[KeyframeStyle.from_json(i) for i in json['keyframes']],
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class KeyframeStyle:
    '''
    Keyframe Style
    '''
    #: Keyframe's time offset.
    offset: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    def to_json(self):
        json = dict()
        json['offset'] = self.offset
        json['easing'] = self.easing
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            offset=str(json['offset']),
            easing=str(json['easing']),
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.enable',
    }
    json = yield cmd_dict


def get_current_time(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Returns the current time of the an animation.

    :param id_: Id of animation.
    :returns: Current time of the page.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getCurrentTime',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['currentTime'])


def get_playback_rate() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Gets the playback rate of the document timeline.

    :returns: Playback rate for animations on page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getPlaybackRate',
    }
    json = yield cmd_dict
    return float(json['playbackRate'])


def release_animations(
        animations: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases a set of animations to no longer be manipulated.

    :param animations: List of animation ids to seek.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.releaseAnimations',
        'params': params,
    }
    json = yield cmd_dict


def resolve_animation(
        animation_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    Gets the remote object of the Animation.

    :param animation_id: Animation id.
    :returns: Corresponding remote object.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.resolveAnimation',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['remoteObject'])


def seek_animations(
        animations: typing.List[str],
        current_time: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Seek a set of animations to a particular time within each animation.

    :param animations: List of animation ids to seek.
    :param current_time: Set the current time of each animation.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['currentTime'] = current_time
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.seekAnimations',
        'params': params,
    }
    json = yield cmd_dict


def set_paused(
        animations: typing.List[str],
        paused: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the paused state of a set of animations.

    :param animations: Animations to set the pause state of.
    :param paused: Paused state to set to.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['paused'] = paused
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPaused',
        'params': params,
    }
    json = yield cmd_dict


def set_playback_rate(
        playback_rate: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the playback rate of the document timeline.

    :param playback_rate: Playback rate for animations on page
    '''
    params: T_JSON_DICT = dict()
    params['playbackRate'] = playback_rate
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPlaybackRate',
        'params': params,
    }
    json = yield cmd_dict


def set_timing(
        animation_id: str,
        duration: float,
        delay: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the timing of an animation node.

    :param animation_id: Animation id.
    :param duration: Duration of the animation.
    :param delay: Delay of the animation.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    params['duration'] = duration
    params['delay'] = delay
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setTiming',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Animation.animationCanceled')
@dataclass
class AnimationCanceled:
    '''
    Event for when an animation has been cancelled.
    '''
    #: Id of the animation that was cancelled.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCanceled:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationCreated')
@dataclass
class AnimationCreated:
    '''
    Event for each animation that has been created.
    '''
    #: Id of the animation that was created.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCreated:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationStarted')
@dataclass
class AnimationStarted:
    '''
    Event for animation that has been started.
    '''
    #: Animation that was started.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationStarted:
        return cls(
            animation=Animation.from_json(json['animation'])
        )


@event_class('Animation.animationUpdated')
@dataclass
class AnimationUpdated:
    '''
    Event for animation that has been updated.
    '''
    #: Animation that was updated.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationUpdated:
        return cls(
            animation=Animation.from_json(json['animation'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\animation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Animation (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


@dataclass
class Animation:
    '''
    Animation instance.
    '''
    #: ``Animation``'s id.
    id_: str

    #: ``Animation``'s name.
    name: str

    #: ``Animation``'s internal paused state.
    paused_state: bool

    #: ``Animation``'s play state.
    play_state: str

    #: ``Animation``'s playback rate.
    playback_rate: float

    #: ``Animation``'s start time.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    start_time: float

    #: ``Animation``'s current time.
    current_time: float

    #: Animation type of ``Animation``.
    type_: str

    #: ``Animation``'s source animation node.
    source: typing.Optional[AnimationEffect] = None

    #: A unique ID for ``Animation`` representing the sources that triggered this CSS
    #: animation/transition.
    css_id: typing.Optional[str] = None

    #: View or scroll timeline
    view_or_scroll_timeline: typing.Optional[ViewOrScrollTimeline] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['name'] = self.name
        json['pausedState'] = self.paused_state
        json['playState'] = self.play_state
        json['playbackRate'] = self.playback_rate
        json['startTime'] = self.start_time
        json['currentTime'] = self.current_time
        json['type'] = self.type_
        if self.source is not None:
            json['source'] = self.source.to_json()
        if self.css_id is not None:
            json['cssId'] = self.css_id
        if self.view_or_scroll_timeline is not None:
            json['viewOrScrollTimeline'] = self.view_or_scroll_timeline.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            name=str(json['name']),
            paused_state=bool(json['pausedState']),
            play_state=str(json['playState']),
            playback_rate=float(json['playbackRate']),
            start_time=float(json['startTime']),
            current_time=float(json['currentTime']),
            type_=str(json['type']),
            source=AnimationEffect.from_json(json['source']) if 'source' in json else None,
            css_id=str(json['cssId']) if 'cssId' in json else None,
            view_or_scroll_timeline=ViewOrScrollTimeline.from_json(json['viewOrScrollTimeline']) if 'viewOrScrollTimeline' in json else None,
        )


@dataclass
class ViewOrScrollTimeline:
    '''
    Timeline instance
    '''
    #: Orientation of the scroll
    axis: dom.ScrollOrientation

    #: Scroll container node
    source_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Represents the starting scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    start_offset: typing.Optional[float] = None

    #: Represents the ending scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    end_offset: typing.Optional[float] = None

    #: The element whose principal box's visibility in the
    #: scrollport defined the progress of the timeline.
    #: Does not exist for animations with ScrollTimeline
    subject_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['axis'] = self.axis.to_json()
        if self.source_node_id is not None:
            json['sourceNodeId'] = self.source_node_id.to_json()
        if self.start_offset is not None:
            json['startOffset'] = self.start_offset
        if self.end_offset is not None:
            json['endOffset'] = self.end_offset
        if self.subject_node_id is not None:
            json['subjectNodeId'] = self.subject_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            axis=dom.ScrollOrientation.from_json(json['axis']),
            source_node_id=dom.BackendNodeId.from_json(json['sourceNodeId']) if 'sourceNodeId' in json else None,
            start_offset=float(json['startOffset']) if 'startOffset' in json else None,
            end_offset=float(json['endOffset']) if 'endOffset' in json else None,
            subject_node_id=dom.BackendNodeId.from_json(json['subjectNodeId']) if 'subjectNodeId' in json else None,
        )


@dataclass
class AnimationEffect:
    '''
    AnimationEffect instance
    '''
    #: ``AnimationEffect``'s delay.
    delay: float

    #: ``AnimationEffect``'s end delay.
    end_delay: float

    #: ``AnimationEffect``'s iteration start.
    iteration_start: float

    #: ``AnimationEffect``'s iterations.
    iterations: float

    #: ``AnimationEffect``'s iteration duration.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    duration: float

    #: ``AnimationEffect``'s playback direction.
    direction: str

    #: ``AnimationEffect``'s fill mode.
    fill: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    #: ``AnimationEffect``'s target node.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: ``AnimationEffect``'s keyframes.
    keyframes_rule: typing.Optional[KeyframesRule] = None

    def to_json(self):
        json = dict()
        json['delay'] = self.delay
        json['endDelay'] = self.end_delay
        json['iterationStart'] = self.iteration_start
        json['iterations'] = self.iterations
        json['duration'] = self.duration
        json['direction'] = self.direction
        json['fill'] = self.fill
        json['easing'] = self.easing
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.keyframes_rule is not None:
            json['keyframesRule'] = self.keyframes_rule.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            delay=float(json['delay']),
            end_delay=float(json['endDelay']),
            iteration_start=float(json['iterationStart']),
            iterations=float(json['iterations']),
            duration=float(json['duration']),
            direction=str(json['direction']),
            fill=str(json['fill']),
            easing=str(json['easing']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            keyframes_rule=KeyframesRule.from_json(json['keyframesRule']) if 'keyframesRule' in json else None,
        )


@dataclass
class KeyframesRule:
    '''
    Keyframes Rule
    '''
    #: List of animation keyframes.
    keyframes: typing.List[KeyframeStyle]

    #: CSS keyframed animation's name.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyframes'] = [i.to_json() for i in self.keyframes]
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            keyframes=[KeyframeStyle.from_json(i) for i in json['keyframes']],
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class KeyframeStyle:
    '''
    Keyframe Style
    '''
    #: Keyframe's time offset.
    offset: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    def to_json(self):
        json = dict()
        json['offset'] = self.offset
        json['easing'] = self.easing
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            offset=str(json['offset']),
            easing=str(json['easing']),
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.enable',
    }
    json = yield cmd_dict


def get_current_time(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Returns the current time of the an animation.

    :param id_: Id of animation.
    :returns: Current time of the page.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getCurrentTime',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['currentTime'])


def get_playback_rate() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Gets the playback rate of the document timeline.

    :returns: Playback rate for animations on page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getPlaybackRate',
    }
    json = yield cmd_dict
    return float(json['playbackRate'])


def release_animations(
        animations: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases a set of animations to no longer be manipulated.

    :param animations: List of animation ids to seek.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.releaseAnimations',
        'params': params,
    }
    json = yield cmd_dict


def resolve_animation(
        animation_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    Gets the remote object of the Animation.

    :param animation_id: Animation id.
    :returns: Corresponding remote object.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.resolveAnimation',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['remoteObject'])


def seek_animations(
        animations: typing.List[str],
        current_time: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Seek a set of animations to a particular time within each animation.

    :param animations: List of animation ids to seek.
    :param current_time: Set the current time of each animation.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['currentTime'] = current_time
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.seekAnimations',
        'params': params,
    }
    json = yield cmd_dict


def set_paused(
        animations: typing.List[str],
        paused: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the paused state of a set of animations.

    :param animations: Animations to set the pause state of.
    :param paused: Paused state to set to.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['paused'] = paused
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPaused',
        'params': params,
    }
    json = yield cmd_dict


def set_playback_rate(
        playback_rate: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the playback rate of the document timeline.

    :param playback_rate: Playback rate for animations on page
    '''
    params: T_JSON_DICT = dict()
    params['playbackRate'] = playback_rate
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPlaybackRate',
        'params': params,
    }
    json = yield cmd_dict


def set_timing(
        animation_id: str,
        duration: float,
        delay: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the timing of an animation node.

    :param animation_id: Animation id.
    :param duration: Duration of the animation.
    :param delay: Delay of the animation.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    params['duration'] = duration
    params['delay'] = delay
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setTiming',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Animation.animationCanceled')
@dataclass
class AnimationCanceled:
    '''
    Event for when an animation has been cancelled.
    '''
    #: Id of the animation that was cancelled.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCanceled:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationCreated')
@dataclass
class AnimationCreated:
    '''
    Event for each animation that has been created.
    '''
    #: Id of the animation that was created.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCreated:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationStarted')
@dataclass
class AnimationStarted:
    '''
    Event for animation that has been started.
    '''
    #: Animation that was started.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationStarted:
        return cls(
            animation=Animation.from_json(json['animation'])
        )


@event_class('Animation.animationUpdated')
@dataclass
class AnimationUpdated:
    '''
    Event for animation that has been updated.
    '''
    #: Animation that was updated.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationUpdated:
        return cls(
            animation=Animation.from_json(json['animation'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\animation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Animation (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import runtime


@dataclass
class Animation:
    '''
    Animation instance.
    '''
    #: ``Animation``'s id.
    id_: str

    #: ``Animation``'s name.
    name: str

    #: ``Animation``'s internal paused state.
    paused_state: bool

    #: ``Animation``'s play state.
    play_state: str

    #: ``Animation``'s playback rate.
    playback_rate: float

    #: ``Animation``'s start time.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    start_time: float

    #: ``Animation``'s current time.
    current_time: float

    #: Animation type of ``Animation``.
    type_: str

    #: ``Animation``'s source animation node.
    source: typing.Optional[AnimationEffect] = None

    #: A unique ID for ``Animation`` representing the sources that triggered this CSS
    #: animation/transition.
    css_id: typing.Optional[str] = None

    #: View or scroll timeline
    view_or_scroll_timeline: typing.Optional[ViewOrScrollTimeline] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_
        json['name'] = self.name
        json['pausedState'] = self.paused_state
        json['playState'] = self.play_state
        json['playbackRate'] = self.playback_rate
        json['startTime'] = self.start_time
        json['currentTime'] = self.current_time
        json['type'] = self.type_
        if self.source is not None:
            json['source'] = self.source.to_json()
        if self.css_id is not None:
            json['cssId'] = self.css_id
        if self.view_or_scroll_timeline is not None:
            json['viewOrScrollTimeline'] = self.view_or_scroll_timeline.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=str(json['id']),
            name=str(json['name']),
            paused_state=bool(json['pausedState']),
            play_state=str(json['playState']),
            playback_rate=float(json['playbackRate']),
            start_time=float(json['startTime']),
            current_time=float(json['currentTime']),
            type_=str(json['type']),
            source=AnimationEffect.from_json(json['source']) if 'source' in json else None,
            css_id=str(json['cssId']) if 'cssId' in json else None,
            view_or_scroll_timeline=ViewOrScrollTimeline.from_json(json['viewOrScrollTimeline']) if 'viewOrScrollTimeline' in json else None,
        )


@dataclass
class ViewOrScrollTimeline:
    '''
    Timeline instance
    '''
    #: Orientation of the scroll
    axis: dom.ScrollOrientation

    #: Scroll container node
    source_node_id: typing.Optional[dom.BackendNodeId] = None

    #: Represents the starting scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    start_offset: typing.Optional[float] = None

    #: Represents the ending scroll position of the timeline
    #: as a length offset in pixels from scroll origin.
    end_offset: typing.Optional[float] = None

    #: The element whose principal box's visibility in the
    #: scrollport defined the progress of the timeline.
    #: Does not exist for animations with ScrollTimeline
    subject_node_id: typing.Optional[dom.BackendNodeId] = None

    def to_json(self):
        json = dict()
        json['axis'] = self.axis.to_json()
        if self.source_node_id is not None:
            json['sourceNodeId'] = self.source_node_id.to_json()
        if self.start_offset is not None:
            json['startOffset'] = self.start_offset
        if self.end_offset is not None:
            json['endOffset'] = self.end_offset
        if self.subject_node_id is not None:
            json['subjectNodeId'] = self.subject_node_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            axis=dom.ScrollOrientation.from_json(json['axis']),
            source_node_id=dom.BackendNodeId.from_json(json['sourceNodeId']) if 'sourceNodeId' in json else None,
            start_offset=float(json['startOffset']) if 'startOffset' in json else None,
            end_offset=float(json['endOffset']) if 'endOffset' in json else None,
            subject_node_id=dom.BackendNodeId.from_json(json['subjectNodeId']) if 'subjectNodeId' in json else None,
        )


@dataclass
class AnimationEffect:
    '''
    AnimationEffect instance
    '''
    #: ``AnimationEffect``'s delay.
    delay: float

    #: ``AnimationEffect``'s end delay.
    end_delay: float

    #: ``AnimationEffect``'s iteration start.
    iteration_start: float

    #: ``AnimationEffect``'s iterations.
    iterations: float

    #: ``AnimationEffect``'s iteration duration.
    #: Milliseconds for time based animations and
    #: percentage [0 - 100] for scroll driven animations
    #: (i.e. when viewOrScrollTimeline exists).
    duration: float

    #: ``AnimationEffect``'s playback direction.
    direction: str

    #: ``AnimationEffect``'s fill mode.
    fill: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    #: ``AnimationEffect``'s target node.
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    #: ``AnimationEffect``'s keyframes.
    keyframes_rule: typing.Optional[KeyframesRule] = None

    def to_json(self):
        json = dict()
        json['delay'] = self.delay
        json['endDelay'] = self.end_delay
        json['iterationStart'] = self.iteration_start
        json['iterations'] = self.iterations
        json['duration'] = self.duration
        json['direction'] = self.direction
        json['fill'] = self.fill
        json['easing'] = self.easing
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.keyframes_rule is not None:
            json['keyframesRule'] = self.keyframes_rule.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            delay=float(json['delay']),
            end_delay=float(json['endDelay']),
            iteration_start=float(json['iterationStart']),
            iterations=float(json['iterations']),
            duration=float(json['duration']),
            direction=str(json['direction']),
            fill=str(json['fill']),
            easing=str(json['easing']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            keyframes_rule=KeyframesRule.from_json(json['keyframesRule']) if 'keyframesRule' in json else None,
        )


@dataclass
class KeyframesRule:
    '''
    Keyframes Rule
    '''
    #: List of animation keyframes.
    keyframes: typing.List[KeyframeStyle]

    #: CSS keyframed animation's name.
    name: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['keyframes'] = [i.to_json() for i in self.keyframes]
        if self.name is not None:
            json['name'] = self.name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            keyframes=[KeyframeStyle.from_json(i) for i in json['keyframes']],
            name=str(json['name']) if 'name' in json else None,
        )


@dataclass
class KeyframeStyle:
    '''
    Keyframe Style
    '''
    #: Keyframe's time offset.
    offset: str

    #: ``AnimationEffect``'s timing function.
    easing: str

    def to_json(self):
        json = dict()
        json['offset'] = self.offset
        json['easing'] = self.easing
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            offset=str(json['offset']),
            easing=str(json['easing']),
        )


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables animation domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.enable',
    }
    json = yield cmd_dict


def get_current_time(
        id_: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Returns the current time of the an animation.

    :param id_: Id of animation.
    :returns: Current time of the page.
    '''
    params: T_JSON_DICT = dict()
    params['id'] = id_
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getCurrentTime',
        'params': params,
    }
    json = yield cmd_dict
    return float(json['currentTime'])


def get_playback_rate() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,float]:
    '''
    Gets the playback rate of the document timeline.

    :returns: Playback rate for animations on page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.getPlaybackRate',
    }
    json = yield cmd_dict
    return float(json['playbackRate'])


def release_animations(
        animations: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Releases a set of animations to no longer be manipulated.

    :param animations: List of animation ids to seek.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.releaseAnimations',
        'params': params,
    }
    json = yield cmd_dict


def resolve_animation(
        animation_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.RemoteObject]:
    '''
    Gets the remote object of the Animation.

    :param animation_id: Animation id.
    :returns: Corresponding remote object.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.resolveAnimation',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.RemoteObject.from_json(json['remoteObject'])


def seek_animations(
        animations: typing.List[str],
        current_time: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Seek a set of animations to a particular time within each animation.

    :param animations: List of animation ids to seek.
    :param current_time: Set the current time of each animation.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['currentTime'] = current_time
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.seekAnimations',
        'params': params,
    }
    json = yield cmd_dict


def set_paused(
        animations: typing.List[str],
        paused: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the paused state of a set of animations.

    :param animations: Animations to set the pause state of.
    :param paused: Paused state to set to.
    '''
    params: T_JSON_DICT = dict()
    params['animations'] = [i for i in animations]
    params['paused'] = paused
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPaused',
        'params': params,
    }
    json = yield cmd_dict


def set_playback_rate(
        playback_rate: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the playback rate of the document timeline.

    :param playback_rate: Playback rate for animations on page
    '''
    params: T_JSON_DICT = dict()
    params['playbackRate'] = playback_rate
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setPlaybackRate',
        'params': params,
    }
    json = yield cmd_dict


def set_timing(
        animation_id: str,
        duration: float,
        delay: float
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sets the timing of an animation node.

    :param animation_id: Animation id.
    :param duration: Duration of the animation.
    :param delay: Delay of the animation.
    '''
    params: T_JSON_DICT = dict()
    params['animationId'] = animation_id
    params['duration'] = duration
    params['delay'] = delay
    cmd_dict: T_JSON_DICT = {
        'method': 'Animation.setTiming',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Animation.animationCanceled')
@dataclass
class AnimationCanceled:
    '''
    Event for when an animation has been cancelled.
    '''
    #: Id of the animation that was cancelled.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCanceled:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationCreated')
@dataclass
class AnimationCreated:
    '''
    Event for each animation that has been created.
    '''
    #: Id of the animation that was created.
    id_: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationCreated:
        return cls(
            id_=str(json['id'])
        )


@event_class('Animation.animationStarted')
@dataclass
class AnimationStarted:
    '''
    Event for animation that has been started.
    '''
    #: Animation that was started.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationStarted:
        return cls(
            animation=Animation.from_json(json['animation'])
        )


@event_class('Animation.animationUpdated')
@dataclass
class AnimationUpdated:
    '''
    Event for animation that has been updated.
    '''
    #: Animation that was updated.
    animation: Animation

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AnimationUpdated:
        return cls(
            animation=Animation.from_json(json['animation'])
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\transforms.py ===
from fontTools.misc.psCharStrings import (
    SimpleT2Decompiler,
    T2WidthExtractor,
    calcSubrBias,
)


def _uniq_sort(l):
    return sorted(set(l))


class StopHintCountEvent(Exception):
    pass


class _DesubroutinizingT2Decompiler(SimpleT2Decompiler):
    stop_hintcount_ops = (
        "op_hintmask",
        "op_cntrmask",
        "op_rmoveto",
        "op_hmoveto",
        "op_vmoveto",
    )

    def __init__(self, localSubrs, globalSubrs, private=None):
        SimpleT2Decompiler.__init__(self, localSubrs, globalSubrs, private)

    def execute(self, charString):
        self.need_hintcount = True  # until proven otherwise
        for op_name in self.stop_hintcount_ops:
            setattr(self, op_name, self.stop_hint_count)

        if hasattr(charString, "_desubroutinized"):
            # If a charstring has already been desubroutinized, we will still
            # need to execute it if we need to count hints in order to
            # compute the byte length for mask arguments, and haven't finished
            # counting hints pairs.
            if self.need_hintcount and self.callingStack:
                try:
                    SimpleT2Decompiler.execute(self, charString)
                except StopHintCountEvent:
                    del self.callingStack[-1]
            return

        charString._patches = []
        SimpleT2Decompiler.execute(self, charString)
        desubroutinized = charString.program[:]
        for idx, expansion in reversed(charString._patches):
            assert idx >= 2
            assert desubroutinized[idx - 1] in [
                "callsubr",
                "callgsubr",
            ], desubroutinized[idx - 1]
            assert type(desubroutinized[idx - 2]) == int
            if expansion[-1] == "return":
                expansion = expansion[:-1]
            desubroutinized[idx - 2 : idx] = expansion
        if not self.private.in_cff2:
            if "endchar" in desubroutinized:
                # Cut off after first endchar
                desubroutinized = desubroutinized[
                    : desubroutinized.index("endchar") + 1
                ]

        charString._desubroutinized = desubroutinized
        del charString._patches

    def op_callsubr(self, index):
        subr = self.localSubrs[self.operandStack[-1] + self.localBias]
        SimpleT2Decompiler.op_callsubr(self, index)
        self.processSubr(index, subr)

    def op_callgsubr(self, index):
        subr = self.globalSubrs[self.operandStack[-1] + self.globalBias]
        SimpleT2Decompiler.op_callgsubr(self, index)
        self.processSubr(index, subr)

    def stop_hint_count(self, *args):
        self.need_hintcount = False
        for op_name in self.stop_hintcount_ops:
            setattr(self, op_name, None)
        cs = self.callingStack[-1]
        if hasattr(cs, "_desubroutinized"):
            raise StopHintCountEvent()

    def op_hintmask(self, index):
        SimpleT2Decompiler.op_hintmask(self, index)
        if self.need_hintcount:
            self.stop_hint_count()

    def processSubr(self, index, subr):
        cs = self.callingStack[-1]
        if not hasattr(cs, "_desubroutinized"):
            cs._patches.append((index, subr._desubroutinized))


def desubroutinize(cff):
    for fontName in cff.fontNames:
        font = cff[fontName]
        cs = font.CharStrings
        for c in cs.values():
            c.decompile()
            subrs = getattr(c.private, "Subrs", [])
            decompiler = _DesubroutinizingT2Decompiler(subrs, c.globalSubrs, c.private)
            decompiler.execute(c)
            c.program = c._desubroutinized
            del c._desubroutinized
        # Delete all the local subrs
        if hasattr(font, "FDArray"):
            for fd in font.FDArray:
                pd = fd.Private
                if hasattr(pd, "Subrs"):
                    del pd.Subrs
                if "Subrs" in pd.rawDict:
                    del pd.rawDict["Subrs"]
        else:
            pd = font.Private
            if hasattr(pd, "Subrs"):
                del pd.Subrs
            if "Subrs" in pd.rawDict:
                del pd.rawDict["Subrs"]
    # as well as the global subrs
    cff.GlobalSubrs.clear()


class _MarkingT2Decompiler(SimpleT2Decompiler):
    def __init__(self, localSubrs, globalSubrs, private):
        SimpleT2Decompiler.__init__(self, localSubrs, globalSubrs, private)
        for subrs in [localSubrs, globalSubrs]:
            if subrs and not hasattr(subrs, "_used"):
                subrs._used = set()

    def op_callsubr(self, index):
        self.localSubrs._used.add(self.operandStack[-1] + self.localBias)
        SimpleT2Decompiler.op_callsubr(self, index)

    def op_callgsubr(self, index):
        self.globalSubrs._used.add(self.operandStack[-1] + self.globalBias)
        SimpleT2Decompiler.op_callgsubr(self, index)


class _DehintingT2Decompiler(T2WidthExtractor):
    class Hints(object):
        def __init__(self):
            # Whether calling this charstring produces any hint stems
            # Note that if a charstring starts with hintmask, it will
            # have has_hint set to True, because it *might* produce an
            # implicit vstem if called under certain conditions.
            self.has_hint = False
            # Index to start at to drop all hints
            self.last_hint = 0
            # Index up to which we know more hints are possible.
            # Only relevant if status is 0 or 1.
            self.last_checked = 0
            # The status means:
            # 0: after dropping hints, this charstring is empty
            # 1: after dropping hints, there may be more hints
            # 	continuing after this, or there might be
            # 	other things.  Not clear yet.
            # 2: no more hints possible after this charstring
            self.status = 0
            # Has hintmask instructions; not recursive
            self.has_hintmask = False
            # List of indices of calls to empty subroutines to remove.
            self.deletions = []

        pass

    def __init__(
        self, css, localSubrs, globalSubrs, nominalWidthX, defaultWidthX, private=None
    ):
        self._css = css
        T2WidthExtractor.__init__(
            self, localSubrs, globalSubrs, nominalWidthX, defaultWidthX
        )
        self.private = private

    def execute(self, charString):
        old_hints = charString._hints if hasattr(charString, "_hints") else None
        charString._hints = self.Hints()

        T2WidthExtractor.execute(self, charString)

        hints = charString._hints

        if hints.has_hint or hints.has_hintmask:
            self._css.add(charString)

        if hints.status != 2:
            # Check from last_check, make sure we didn't have any operators.
            for i in range(hints.last_checked, len(charString.program) - 1):
                if isinstance(charString.program[i], str):
                    hints.status = 2
                    break
                else:
                    hints.status = 1  # There's *something* here
            hints.last_checked = len(charString.program)

        if old_hints:
            assert hints.__dict__ == old_hints.__dict__

    def op_callsubr(self, index):
        subr = self.localSubrs[self.operandStack[-1] + self.localBias]
        T2WidthExtractor.op_callsubr(self, index)
        self.processSubr(index, subr)

    def op_callgsubr(self, index):
        subr = self.globalSubrs[self.operandStack[-1] + self.globalBias]
        T2WidthExtractor.op_callgsubr(self, index)
        self.processSubr(index, subr)

    def op_hstem(self, index):
        T2WidthExtractor.op_hstem(self, index)
        self.processHint(index)

    def op_vstem(self, index):
        T2WidthExtractor.op_vstem(self, index)
        self.processHint(index)

    def op_hstemhm(self, index):
        T2WidthExtractor.op_hstemhm(self, index)
        self.processHint(index)

    def op_vstemhm(self, index):
        T2WidthExtractor.op_vstemhm(self, index)
        self.processHint(index)

    def op_hintmask(self, index):
        rv = T2WidthExtractor.op_hintmask(self, index)
        self.processHintmask(index)
        return rv

    def op_cntrmask(self, index):
        rv = T2WidthExtractor.op_cntrmask(self, index)
        self.processHintmask(index)
        return rv

    def processHintmask(self, index):
        cs = self.callingStack[-1]
        hints = cs._hints
        hints.has_hintmask = True
        if hints.status != 2:
            # Check from last_check, see if we may be an implicit vstem
            for i in range(hints.last_checked, index - 1):
                if isinstance(cs.program[i], str):
                    hints.status = 2
                    break
            else:
                # We are an implicit vstem
                hints.has_hint = True
                hints.last_hint = index + 1
                hints.status = 0
        hints.last_checked = index + 1

    def processHint(self, index):
        cs = self.callingStack[-1]
        hints = cs._hints
        hints.has_hint = True
        hints.last_hint = index
        hints.last_checked = index

    def processSubr(self, index, subr):
        cs = self.callingStack[-1]
        hints = cs._hints
        subr_hints = subr._hints

        # Check from last_check, make sure we didn't have
        # any operators.
        if hints.status != 2:
            for i in range(hints.last_checked, index - 1):
                if isinstance(cs.program[i], str):
                    hints.status = 2
                    break
            hints.last_checked = index

        if hints.status != 2:
            if subr_hints.has_hint:
                hints.has_hint = True

                # Decide where to chop off from
                if subr_hints.status == 0:
                    hints.last_hint = index
                else:
                    hints.last_hint = index - 2  # Leave the subr call in

        elif subr_hints.status == 0:
            hints.deletions.append(index)

        hints.status = max(hints.status, subr_hints.status)


def _cs_subset_subroutines(charstring, subrs, gsubrs):
    p = charstring.program
    for i in range(1, len(p)):
        if p[i] == "callsubr":
            assert isinstance(p[i - 1], int)
            p[i - 1] = subrs._used.index(p[i - 1] + subrs._old_bias) - subrs._new_bias
        elif p[i] == "callgsubr":
            assert isinstance(p[i - 1], int)
            p[i - 1] = (
                gsubrs._used.index(p[i - 1] + gsubrs._old_bias) - gsubrs._new_bias
            )


def _cs_drop_hints(charstring):
    hints = charstring._hints

    if hints.deletions:
        p = charstring.program
        for idx in reversed(hints.deletions):
            del p[idx - 2 : idx]

    if hints.has_hint:
        assert not hints.deletions or hints.last_hint <= hints.deletions[0]
        charstring.program = charstring.program[hints.last_hint :]
        if not charstring.program:
            # TODO CFF2 no need for endchar.
            charstring.program.append("endchar")
        if hasattr(charstring, "width"):
            # Insert width back if needed
            if charstring.width != charstring.private.defaultWidthX:
                # For CFF2 charstrings, this should never happen
                assert (
                    charstring.private.defaultWidthX is not None
                ), "CFF2 CharStrings must not have an initial width value"
                charstring.program.insert(
                    0, charstring.width - charstring.private.nominalWidthX
                )

    if hints.has_hintmask:
        i = 0
        p = charstring.program
        while i < len(p):
            if p[i] in ["hintmask", "cntrmask"]:
                assert i + 1 <= len(p)
                del p[i : i + 2]
                continue
            i += 1

    assert len(charstring.program)

    del charstring._hints


def remove_hints(cff, *, removeUnusedSubrs: bool = True):
    for fontname in cff.keys():
        font = cff[fontname]
        cs = font.CharStrings
        # This can be tricky, but doesn't have to. What we do is:
        #
        # - Run all used glyph charstrings and recurse into subroutines,
        # - For each charstring (including subroutines), if it has any
        #   of the hint stem operators, we mark it as such.
        #   Upon returning, for each charstring we note all the
        #   subroutine calls it makes that (recursively) contain a stem,
        # - Dropping hinting then consists of the following two ops:
        #   * Drop the piece of the program in each charstring before the
        #     last call to a stem op or a stem-calling subroutine,
        #   * Drop all hintmask operations.
        # - It's trickier... A hintmask right after hints and a few numbers
        #    will act as an implicit vstemhm. As such, we track whether
        #    we have seen any non-hint operators so far and do the right
        #    thing, recursively... Good luck understanding that :(
        css = set()
        for c in cs.values():
            c.decompile()
            subrs = getattr(c.private, "Subrs", [])
            decompiler = _DehintingT2Decompiler(
                css,
                subrs,
                c.globalSubrs,
                c.private.nominalWidthX,
                c.private.defaultWidthX,
                c.private,
            )
            decompiler.execute(c)
            c.width = decompiler.width
        for charstring in css:
            _cs_drop_hints(charstring)
        del css

        # Drop font-wide hinting values
        all_privs = []
        if hasattr(font, "FDArray"):
            all_privs.extend(fd.Private for fd in font.FDArray)
        else:
            all_privs.append(font.Private)
        for priv in all_privs:
            for k in [
                "BlueValues",
                "OtherBlues",
                "FamilyBlues",
                "FamilyOtherBlues",
                "BlueScale",
                "BlueShift",
                "BlueFuzz",
                "StemSnapH",
                "StemSnapV",
                "StdHW",
                "StdVW",
                "ForceBold",
                "LanguageGroup",
                "ExpansionFactor",
            ]:
                if hasattr(priv, k):
                    setattr(priv, k, None)
    if removeUnusedSubrs:
        remove_unused_subroutines(cff)


def _pd_delete_empty_subrs(private_dict):
    if hasattr(private_dict, "Subrs") and not private_dict.Subrs:
        if "Subrs" in private_dict.rawDict:
            del private_dict.rawDict["Subrs"]
        del private_dict.Subrs


def remove_unused_subroutines(cff):
    for fontname in cff.keys():
        font = cff[fontname]
        cs = font.CharStrings
        # Renumber subroutines to remove unused ones

        # Mark all used subroutines
        for c in cs.values():
            subrs = getattr(c.private, "Subrs", [])
            decompiler = _MarkingT2Decompiler(subrs, c.globalSubrs, c.private)
            decompiler.execute(c)

        all_subrs = [font.GlobalSubrs]
        if hasattr(font, "FDArray"):
            all_subrs.extend(
                fd.Private.Subrs
                for fd in font.FDArray
                if hasattr(fd.Private, "Subrs") and fd.Private.Subrs
            )
        elif hasattr(font.Private, "Subrs") and font.Private.Subrs:
            all_subrs.append(font.Private.Subrs)

        subrs = set(subrs)  # Remove duplicates

        # Prepare
        for subrs in all_subrs:
            if not hasattr(subrs, "_used"):
                subrs._used = set()
            subrs._used = _uniq_sort(subrs._used)
            subrs._old_bias = calcSubrBias(subrs)
            subrs._new_bias = calcSubrBias(subrs._used)

        # Renumber glyph charstrings
        for c in cs.values():
            subrs = getattr(c.private, "Subrs", None)
            _cs_subset_subroutines(c, subrs, font.GlobalSubrs)

        # Renumber subroutines themselves
        for subrs in all_subrs:
            if subrs == font.GlobalSubrs:
                if not hasattr(font, "FDArray") and hasattr(font.Private, "Subrs"):
                    local_subrs = font.Private.Subrs
                elif (
                    hasattr(font, "FDArray")
                    and len(font.FDArray) == 1
                    and hasattr(font.FDArray[0].Private, "Subrs")
                ):
                    # Technically we shouldn't do this. But I've run into fonts that do it.
                    local_subrs = font.FDArray[0].Private.Subrs
                else:
                    local_subrs = None
            else:
                local_subrs = subrs

            subrs.items = [subrs.items[i] for i in subrs._used]
            if hasattr(subrs, "file"):
                del subrs.file
            if hasattr(subrs, "offsets"):
                del subrs.offsets

            for subr in subrs.items:
                _cs_subset_subroutines(subr, local_subrs, font.GlobalSubrs)

        # Delete local SubrsIndex if empty
        if hasattr(font, "FDArray"):
            for fd in font.FDArray:
                _pd_delete_empty_subrs(fd.Private)
        else:
            _pd_delete_empty_subrs(font.Private)

        # Cleanup
        for subrs in all_subrs:
            del subrs._used, subrs._old_bias, subrs._new_bias

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\ttGlyphSet.py ===
"""GlyphSets returned by a TTFont."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextlib import contextmanager
from copy import copy, deepcopy
from types import SimpleNamespace
from fontTools.misc.vector import Vector
from fontTools.misc.fixedTools import otRound, fixedToFloat as fi2fl
from fontTools.misc.loggingTools import deprecateFunction
from fontTools.misc.transform import Transform, DecomposedTransform
from fontTools.pens.transformPen import TransformPen, TransformPointPen
from fontTools.pens.recordingPen import (
    DecomposingRecordingPen,
    lerpRecordings,
    replayRecording,
)


class _TTGlyphSet(Mapping):
    """Generic dict-like GlyphSet class that pulls metrics from hmtx and
    glyph shape from TrueType or CFF.
    """

    def __init__(self, font, location, glyphsMapping, *, recalcBounds=True):
        self.recalcBounds = recalcBounds
        self.font = font
        self.defaultLocationNormalized = (
            {axis.axisTag: 0 for axis in self.font["fvar"].axes}
            if "fvar" in self.font
            else {}
        )
        self.location = location if location is not None else {}
        self.rawLocation = {}  # VarComponent-only location
        self.originalLocation = location if location is not None else {}
        self.depth = 0
        self.locationStack = []
        self.rawLocationStack = []
        self.glyphsMapping = glyphsMapping
        self.hMetrics = font["hmtx"].metrics
        self.vMetrics = getattr(font.get("vmtx"), "metrics", None)
        self.hvarTable = None
        if location:
            from fontTools.varLib.varStore import VarStoreInstancer

            self.hvarTable = getattr(font.get("HVAR"), "table", None)
            if self.hvarTable is not None:
                self.hvarInstancer = VarStoreInstancer(
                    self.hvarTable.VarStore, font["fvar"].axes, location
                )
            # TODO VVAR, VORG

    @contextmanager
    def pushLocation(self, location, reset: bool):
        self.locationStack.append(self.location)
        self.rawLocationStack.append(self.rawLocation)
        if reset:
            self.location = self.originalLocation.copy()
            self.rawLocation = self.defaultLocationNormalized.copy()
        else:
            self.location = self.location.copy()
            self.rawLocation = {}
        self.location.update(location)
        self.rawLocation.update(location)

        try:
            yield None
        finally:
            self.location = self.locationStack.pop()
            self.rawLocation = self.rawLocationStack.pop()

    @contextmanager
    def pushDepth(self):
        try:
            depth = self.depth
            self.depth += 1
            yield depth
        finally:
            self.depth -= 1

    def __contains__(self, glyphName):
        return glyphName in self.glyphsMapping

    def __iter__(self):
        return iter(self.glyphsMapping.keys())

    def __len__(self):
        return len(self.glyphsMapping)

    @deprecateFunction(
        "use 'glyphName in glyphSet' instead", category=DeprecationWarning
    )
    def has_key(self, glyphName):
        return glyphName in self.glyphsMapping


class _TTGlyphSetGlyf(_TTGlyphSet):
    def __init__(self, font, location, recalcBounds=True):
        self.glyfTable = font["glyf"]
        super().__init__(font, location, self.glyfTable, recalcBounds=recalcBounds)
        self.gvarTable = font.get("gvar")

    def __getitem__(self, glyphName):
        return _TTGlyphGlyf(self, glyphName, recalcBounds=self.recalcBounds)


class _TTGlyphSetCFF(_TTGlyphSet):
    def __init__(self, font, location):
        tableTag = "CFF2" if "CFF2" in font else "CFF "
        self.charStrings = list(font[tableTag].cff.values())[0].CharStrings
        super().__init__(font, location, self.charStrings)
        self.setLocation(location)

    def __getitem__(self, glyphName):
        return _TTGlyphCFF(self, glyphName)

    def setLocation(self, location):
        self.blender = None
        if location:
            # TODO Optimize by using instancer.setLocation()

            from fontTools.varLib.varStore import VarStoreInstancer

            varStore = getattr(self.charStrings, "varStore", None)
            if varStore is not None:
                instancer = VarStoreInstancer(
                    varStore.otVarStore, self.font["fvar"].axes, location
                )
                self.blender = instancer.interpolateFromDeltas
        else:
            self.blender = None

    @contextmanager
    def pushLocation(self, location, reset: bool):
        self.setLocation(location)
        with _TTGlyphSet.pushLocation(self, location, reset) as value:
            try:
                yield value
            finally:
                self.setLocation(self.location)


class _TTGlyphSetVARC(_TTGlyphSet):
    def __init__(self, font, location, glyphSet):
        self.glyphSet = glyphSet
        super().__init__(font, location, glyphSet)
        self.varcTable = font["VARC"].table

    def __getitem__(self, glyphName):
        varc = self.varcTable
        if glyphName not in varc.Coverage.glyphs:
            return self.glyphSet[glyphName]
        return _TTGlyphVARC(self, glyphName)


class _TTGlyph(ABC):
    """Glyph object that supports the Pen protocol, meaning that it has
    .draw() and .drawPoints() methods that take a pen object as their only
    argument. Additionally there are 'width' and 'lsb' attributes, read from
    the 'hmtx' table.

    If the font contains a 'vmtx' table, there will also be 'height' and 'tsb'
    attributes.
    """

    def __init__(self, glyphSet, glyphName, *, recalcBounds=True):
        self.glyphSet = glyphSet
        self.name = glyphName
        self.recalcBounds = recalcBounds
        self.width, self.lsb = glyphSet.hMetrics[glyphName]
        if glyphSet.vMetrics is not None:
            self.height, self.tsb = glyphSet.vMetrics[glyphName]
        else:
            self.height, self.tsb = None, None
        if glyphSet.location and glyphSet.hvarTable is not None:
            varidx = (
                glyphSet.font.getGlyphID(glyphName)
                if glyphSet.hvarTable.AdvWidthMap is None
                else glyphSet.hvarTable.AdvWidthMap.mapping[glyphName]
            )
            self.width += glyphSet.hvarInstancer[varidx]
        # TODO: VVAR/VORG

    @abstractmethod
    def draw(self, pen):
        """Draw the glyph onto ``pen``. See fontTools.pens.basePen for details
        how that works.
        """
        raise NotImplementedError

    def drawPoints(self, pen):
        """Draw the glyph onto ``pen``. See fontTools.pens.pointPen for details
        how that works.
        """
        from fontTools.pens.pointPen import SegmentToPointPen

        self.draw(SegmentToPointPen(pen))


class _TTGlyphGlyf(_TTGlyph):
    def draw(self, pen):
        """Draw the glyph onto ``pen``. See fontTools.pens.basePen for details
        how that works.
        """
        glyph, offset = self._getGlyphAndOffset()

        with self.glyphSet.pushDepth() as depth:
            if depth:
                offset = 0  # Offset should only apply at top-level

            glyph.draw(pen, self.glyphSet.glyfTable, offset)

    def drawPoints(self, pen):
        """Draw the glyph onto ``pen``. See fontTools.pens.pointPen for details
        how that works.
        """
        glyph, offset = self._getGlyphAndOffset()

        with self.glyphSet.pushDepth() as depth:
            if depth:
                offset = 0  # Offset should only apply at top-level

            glyph.drawPoints(pen, self.glyphSet.glyfTable, offset)

    def _getGlyphAndOffset(self):
        if self.glyphSet.location and self.glyphSet.gvarTable is not None:
            glyph = self._getGlyphInstance()
        else:
            glyph = self.glyphSet.glyfTable[self.name]

        offset = self.lsb - glyph.xMin if hasattr(glyph, "xMin") else 0
        return glyph, offset

    def _getGlyphInstance(self):
        from fontTools.varLib.iup import iup_delta
        from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
        from fontTools.varLib.models import supportScalar

        glyphSet = self.glyphSet
        glyfTable = glyphSet.glyfTable
        variations = glyphSet.gvarTable.variations[self.name]
        hMetrics = glyphSet.hMetrics
        vMetrics = glyphSet.vMetrics
        coordinates, _ = glyfTable._getCoordinatesAndControls(
            self.name, hMetrics, vMetrics
        )
        origCoords, endPts = None, None
        for var in variations:
            scalar = supportScalar(glyphSet.location, var.axes)
            if not scalar:
                continue
            delta = var.coordinates
            if None in delta:
                if origCoords is None:
                    origCoords, control = glyfTable._getCoordinatesAndControls(
                        self.name, hMetrics, vMetrics
                    )
                    endPts = (
                        control[1] if control[0] >= 1 else list(range(len(control[1])))
                    )
                delta = iup_delta(delta, origCoords, endPts)
            coordinates += GlyphCoordinates(delta) * scalar

        glyph = copy(glyfTable[self.name])  # Shallow copy
        width, lsb, height, tsb = _setCoordinates(
            glyph, coordinates, glyfTable, recalcBounds=self.recalcBounds
        )
        self.lsb = lsb
        self.tsb = tsb
        if glyphSet.hvarTable is None:
            # no HVAR: let's set metrics from the phantom points
            self.width = width
            self.height = height
        return glyph


class _TTGlyphCFF(_TTGlyph):
    def draw(self, pen):
        """Draw the glyph onto ``pen``. See fontTools.pens.basePen for details
        how that works.
        """
        self.glyphSet.charStrings[self.name].draw(pen, self.glyphSet.blender)


def _evaluateCondition(condition, fvarAxes, location, instancer):
    if condition.Format == 1:
        # ConditionAxisRange
        axisIndex = condition.AxisIndex
        axisTag = fvarAxes[axisIndex].axisTag
        axisValue = location.get(axisTag, 0)
        minValue = condition.FilterRangeMinValue
        maxValue = condition.FilterRangeMaxValue
        return minValue <= axisValue <= maxValue
    elif condition.Format == 2:
        # ConditionValue
        value = condition.DefaultValue
        value += instancer[condition.VarIdx][0]
        return value > 0
    elif condition.Format == 3:
        # ConditionAnd
        for subcondition in condition.ConditionTable:
            if not _evaluateCondition(subcondition, fvarAxes, location, instancer):
                return False
        return True
    elif condition.Format == 4:
        # ConditionOr
        for subcondition in condition.ConditionTable:
            if _evaluateCondition(subcondition, fvarAxes, location, instancer):
                return True
        return False
    elif condition.Format == 5:
        # ConditionNegate
        return not _evaluateCondition(
            condition.conditionTable, fvarAxes, location, instancer
        )
    else:
        return False  # Unkonwn condition format


class _TTGlyphVARC(_TTGlyph):
    def _draw(self, pen, isPointPen):
        """Draw the glyph onto ``pen``. See fontTools.pens.basePen for details
        how that works.
        """
        from fontTools.ttLib.tables.otTables import (
            VarComponentFlags,
            NO_VARIATION_INDEX,
        )

        glyphSet = self.glyphSet
        varc = glyphSet.varcTable
        idx = varc.Coverage.glyphs.index(self.name)
        glyph = varc.VarCompositeGlyphs.VarCompositeGlyph[idx]

        from fontTools.varLib.multiVarStore import MultiVarStoreInstancer
        from fontTools.varLib.varStore import VarStoreInstancer

        fvarAxes = glyphSet.font["fvar"].axes
        instancer = MultiVarStoreInstancer(
            varc.MultiVarStore, fvarAxes, self.glyphSet.location
        )

        for comp in glyph.components:
            if comp.flags & VarComponentFlags.HAVE_CONDITION:
                condition = varc.ConditionList.ConditionTable[comp.conditionIndex]
                if not _evaluateCondition(
                    condition, fvarAxes, self.glyphSet.location, instancer
                ):
                    continue

            location = {}
            if comp.axisIndicesIndex is not None:
                axisIndices = varc.AxisIndicesList.Item[comp.axisIndicesIndex]
                axisValues = Vector(comp.axisValues)
                if comp.axisValuesVarIndex != NO_VARIATION_INDEX:
                    axisValues += fi2fl(instancer[comp.axisValuesVarIndex], 14)
                assert len(axisIndices) == len(axisValues), (
                    len(axisIndices),
                    len(axisValues),
                )
                location = {
                    fvarAxes[i].axisTag: v for i, v in zip(axisIndices, axisValues)
                }

            if comp.transformVarIndex != NO_VARIATION_INDEX:
                deltas = instancer[comp.transformVarIndex]
                comp = deepcopy(comp)
                comp.applyTransformDeltas(deltas)
            transform = comp.transform

            reset = comp.flags & VarComponentFlags.RESET_UNSPECIFIED_AXES
            with self.glyphSet.glyphSet.pushLocation(location, reset):
                with self.glyphSet.pushLocation(location, reset):
                    shouldDecompose = self.name == comp.glyphName

                    if not shouldDecompose:
                        try:
                            pen.addVarComponent(
                                comp.glyphName, transform, self.glyphSet.rawLocation
                            )
                        except AttributeError:
                            shouldDecompose = True

                    if shouldDecompose:
                        t = transform.toTransform()
                        compGlyphSet = (
                            self.glyphSet
                            if comp.glyphName != self.name
                            else glyphSet.glyphSet
                        )
                        g = compGlyphSet[comp.glyphName]
                        if isPointPen:
                            tPen = TransformPointPen(pen, t)
                            g.drawPoints(tPen)
                        else:
                            tPen = TransformPen(pen, t)
                            g.draw(tPen)

    def draw(self, pen):
        self._draw(pen, False)

    def drawPoints(self, pen):
        self._draw(pen, True)


def _setCoordinates(glyph, coord, glyfTable, *, recalcBounds=True):
    # Handle phantom points for (left, right, top, bottom) positions.
    assert len(coord) >= 4
    leftSideX = coord[-4][0]
    rightSideX = coord[-3][0]
    topSideY = coord[-2][1]
    bottomSideY = coord[-1][1]

    for _ in range(4):
        del coord[-1]

    if glyph.isComposite():
        assert len(coord) == len(glyph.components)
        glyph.components = [copy(comp) for comp in glyph.components]  # Shallow copy
        for p, comp in zip(coord, glyph.components):
            if hasattr(comp, "x"):
                comp.x, comp.y = p
    elif glyph.numberOfContours == 0:
        assert len(coord) == 0
    else:
        assert len(coord) == len(glyph.coordinates)
        glyph.coordinates = coord

    if recalcBounds:
        glyph.recalcBounds(glyfTable)

    horizontalAdvanceWidth = otRound(rightSideX - leftSideX)
    verticalAdvanceWidth = otRound(topSideY - bottomSideY)
    leftSideBearing = otRound(glyph.xMin - leftSideX)
    topSideBearing = otRound(topSideY - glyph.yMax)
    return (
        horizontalAdvanceWidth,
        leftSideBearing,
        verticalAdvanceWidth,
        topSideBearing,
    )


class LerpGlyphSet(Mapping):
    """A glyphset that interpolates between two other glyphsets.

    Factor is typically between 0 and 1. 0 means the first glyphset,
    1 means the second glyphset, and 0.5 means the average of the
    two glyphsets. Other values are possible, and can be useful to
    extrapolate. Defaults to 0.5.
    """

    def __init__(self, glyphset1, glyphset2, factor=0.5):
        self.glyphset1 = glyphset1
        self.glyphset2 = glyphset2
        self.factor = factor

    def __getitem__(self, glyphname):
        if glyphname in self.glyphset1 and glyphname in self.glyphset2:
            return LerpGlyph(glyphname, self)
        raise KeyError(glyphname)

    def __contains__(self, glyphname):
        return glyphname in self.glyphset1 and glyphname in self.glyphset2

    def __iter__(self):
        set1 = set(self.glyphset1)
        set2 = set(self.glyphset2)
        return iter(set1.intersection(set2))

    def __len__(self):
        set1 = set(self.glyphset1)
        set2 = set(self.glyphset2)
        return len(set1.intersection(set2))


class LerpGlyph:
    def __init__(self, glyphname, glyphset):
        self.glyphset = glyphset
        self.glyphname = glyphname

    def draw(self, pen):
        recording1 = DecomposingRecordingPen(self.glyphset.glyphset1)
        self.glyphset.glyphset1[self.glyphname].draw(recording1)
        recording2 = DecomposingRecordingPen(self.glyphset.glyphset2)
        self.glyphset.glyphset2[self.glyphname].draw(recording2)

        factor = self.glyphset.factor

        replayRecording(lerpRecordings(recording1.value, recording2.value, factor), pen)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\iup.py ===
try:
    import cython
except (AttributeError, ImportError):
    # if cython not installed, use mock module with no-op decorators and types
    from fontTools.misc import cython
COMPILED = cython.compiled

from typing import (
    Sequence,
    Tuple,
    Union,
)
from numbers import Integral, Real


_Point = Tuple[Real, Real]
_Delta = Tuple[Real, Real]
_PointSegment = Sequence[_Point]
_DeltaSegment = Sequence[_Delta]
_DeltaOrNone = Union[_Delta, None]
_DeltaOrNoneSegment = Sequence[_DeltaOrNone]
_Endpoints = Sequence[Integral]


MAX_LOOKBACK = 8


@cython.cfunc
@cython.locals(
    j=cython.int,
    n=cython.int,
    x1=cython.double,
    x2=cython.double,
    d1=cython.double,
    d2=cython.double,
    scale=cython.double,
    x=cython.double,
    d=cython.double,
)
def iup_segment(
    coords: _PointSegment, rc1: _Point, rd1: _Delta, rc2: _Point, rd2: _Delta
):  # -> _DeltaSegment:
    """Given two reference coordinates `rc1` & `rc2` and their respective
    delta vectors `rd1` & `rd2`, returns interpolated deltas for the set of
    coordinates `coords`."""

    # rc1 = reference coord 1
    # rd1 = reference delta 1
    out_arrays = [None, None]
    for j in 0, 1:
        out_arrays[j] = out = []
        x1, x2, d1, d2 = rc1[j], rc2[j], rd1[j], rd2[j]

        if x1 == x2:
            n = len(coords)
            if d1 == d2:
                out.extend([d1] * n)
            else:
                out.extend([0] * n)
            continue

        if x1 > x2:
            x1, x2 = x2, x1
            d1, d2 = d2, d1

        # x1 < x2
        scale = (d2 - d1) / (x2 - x1)
        for pair in coords:
            x = pair[j]

            if x <= x1:
                d = d1
            elif x >= x2:
                d = d2
            else:
                # Interpolate
                #
                # NOTE: we assign an explicit intermediate variable here in
                # order to disable a fused mul-add optimization. See:
                #
                # - https://godbolt.org/z/YsP4T3TqK,
                # - https://github.com/fonttools/fonttools/issues/3703
                nudge = (x - x1) * scale
                d = d1 + nudge

            out.append(d)

    return zip(*out_arrays)


def iup_contour(deltas: _DeltaOrNoneSegment, coords: _PointSegment) -> _DeltaSegment:
    """For the contour given in `coords`, interpolate any missing
    delta values in delta vector `deltas`.

    Returns fully filled-out delta vector."""

    assert len(deltas) == len(coords)
    if None not in deltas:
        return deltas

    n = len(deltas)
    # indices of points with explicit deltas
    indices = [i for i, v in enumerate(deltas) if v is not None]
    if not indices:
        # All deltas are None.  Return 0,0 for all.
        return [(0, 0)] * n

    out = []
    it = iter(indices)
    start = next(it)
    if start != 0:
        # Initial segment that wraps around
        i1, i2, ri1, ri2 = 0, start, start, indices[-1]
        out.extend(
            iup_segment(
                coords[i1:i2], coords[ri1], deltas[ri1], coords[ri2], deltas[ri2]
            )
        )
    out.append(deltas[start])
    for end in it:
        if end - start > 1:
            i1, i2, ri1, ri2 = start + 1, end, start, end
            out.extend(
                iup_segment(
                    coords[i1:i2], coords[ri1], deltas[ri1], coords[ri2], deltas[ri2]
                )
            )
        out.append(deltas[end])
        start = end
    if start != n - 1:
        # Final segment that wraps around
        i1, i2, ri1, ri2 = start + 1, n, start, indices[0]
        out.extend(
            iup_segment(
                coords[i1:i2], coords[ri1], deltas[ri1], coords[ri2], deltas[ri2]
            )
        )

    assert len(deltas) == len(out), (len(deltas), len(out))
    return out


def iup_delta(
    deltas: _DeltaOrNoneSegment, coords: _PointSegment, ends: _Endpoints
) -> _DeltaSegment:
    """For the outline given in `coords`, with contour endpoints given
    in sorted increasing order in `ends`, interpolate any missing
    delta values in delta vector `deltas`.

    Returns fully filled-out delta vector."""

    assert sorted(ends) == ends and len(coords) == (ends[-1] + 1 if ends else 0) + 4
    n = len(coords)
    ends = ends + [n - 4, n - 3, n - 2, n - 1]
    out = []
    start = 0
    for end in ends:
        end += 1
        contour = iup_contour(deltas[start:end], coords[start:end])
        out.extend(contour)
        start = end

    return out


# Optimizer


@cython.cfunc
@cython.inline
@cython.locals(
    i=cython.int,
    j=cython.int,
    # tolerance=cython.double, # https://github.com/fonttools/fonttools/issues/3282
    x=cython.double,
    y=cython.double,
    p=cython.double,
    q=cython.double,
)
@cython.returns(int)
def can_iup_in_between(
    deltas: _DeltaSegment,
    coords: _PointSegment,
    i: Integral,
    j: Integral,
    tolerance: Real,
):  # -> bool:
    """Return true if the deltas for points at `i` and `j` (`i < j`) can be
    successfully used to interpolate deltas for points in between them within
    provided error tolerance."""

    assert j - i >= 2
    interp = iup_segment(coords[i + 1 : j], coords[i], deltas[i], coords[j], deltas[j])
    deltas = deltas[i + 1 : j]

    return all(
        abs(complex(x - p, y - q)) <= tolerance
        for (x, y), (p, q) in zip(deltas, interp)
    )


@cython.locals(
    cj=cython.double,
    dj=cython.double,
    lcj=cython.double,
    ldj=cython.double,
    ncj=cython.double,
    ndj=cython.double,
    force=cython.int,
    forced=set,
)
def _iup_contour_bound_forced_set(
    deltas: _DeltaSegment, coords: _PointSegment, tolerance: Real = 0
) -> set:
    """The forced set is a conservative set of points on the contour that must be encoded
    explicitly (ie. cannot be interpolated).  Calculating this set allows for significantly
    speeding up the dynamic-programming, as well as resolve circularity in DP.

    The set is precise; that is, if an index is in the returned set, then there is no way
    that IUP can generate delta for that point, given `coords` and `deltas`.
    """
    assert len(deltas) == len(coords)

    n = len(deltas)
    forced = set()
    # Track "last" and "next" points on the contour as we sweep.
    for i in range(len(deltas) - 1, -1, -1):
        ld, lc = deltas[i - 1], coords[i - 1]
        d, c = deltas[i], coords[i]
        nd, nc = deltas[i - n + 1], coords[i - n + 1]

        for j in (0, 1):  # For X and for Y
            cj = c[j]
            dj = d[j]
            lcj = lc[j]
            ldj = ld[j]
            ncj = nc[j]
            ndj = nd[j]

            if lcj <= ncj:
                c1, c2 = lcj, ncj
                d1, d2 = ldj, ndj
            else:
                c1, c2 = ncj, lcj
                d1, d2 = ndj, ldj

            force = False

            # If the two coordinates are the same, then the interpolation
            # algorithm produces the same delta if both deltas are equal,
            # and zero if they differ.
            #
            # This test has to be before the next one.
            if c1 == c2:
                if abs(d1 - d2) > tolerance and abs(dj) > tolerance:
                    force = True

            # If coordinate for current point is between coordinate of adjacent
            # points on the two sides, but the delta for current point is NOT
            # between delta for those adjacent points (considering tolerance
            # allowance), then there is no way that current point can be IUP-ed.
            # Mark it forced.
            elif c1 <= cj <= c2:  # and c1 != c2
                if not (min(d1, d2) - tolerance <= dj <= max(d1, d2) + tolerance):
                    force = True

            # Otherwise, the delta should either match the closest, or have the
            # same sign as the interpolation of the two deltas.
            else:  # cj < c1 or c2 < cj
                if d1 != d2:
                    if cj < c1:
                        if (
                            abs(dj) > tolerance
                            and abs(dj - d1) > tolerance
                            and ((dj - tolerance < d1) != (d1 < d2))
                        ):
                            force = True
                    else:  # c2 < cj
                        if (
                            abs(dj) > tolerance
                            and abs(dj - d2) > tolerance
                            and ((d2 < dj + tolerance) != (d1 < d2))
                        ):
                            force = True

            if force:
                forced.add(i)
                break

    return forced


@cython.locals(
    i=cython.int,
    j=cython.int,
    best_cost=cython.double,
    best_j=cython.int,
    cost=cython.double,
    forced=set,
    tolerance=cython.double,
)
def _iup_contour_optimize_dp(
    deltas: _DeltaSegment,
    coords: _PointSegment,
    forced=set(),
    tolerance: Real = 0,
    lookback: Integral = None,
):
    """Straightforward Dynamic-Programming.  For each index i, find least-costly encoding of
    points 0 to i where i is explicitly encoded.  We find this by considering all previous
    explicit points j and check whether interpolation can fill points between j and i.

    Note that solution always encodes last point explicitly.  Higher-level is responsible
    for removing that restriction.

    As major speedup, we stop looking further whenever we see a "forced" point."""

    n = len(deltas)
    if lookback is None:
        lookback = n
    lookback = min(lookback, MAX_LOOKBACK)
    costs = {-1: 0}
    chain = {-1: None}
    for i in range(0, n):
        best_cost = costs[i - 1] + 1

        costs[i] = best_cost
        chain[i] = i - 1

        if i - 1 in forced:
            continue

        for j in range(i - 2, max(i - lookback, -2), -1):
            cost = costs[j] + 1

            if cost < best_cost and can_iup_in_between(deltas, coords, j, i, tolerance):
                costs[i] = best_cost = cost
                chain[i] = j

            if j in forced:
                break

    return chain, costs


def _rot_list(l: list, k: int):
    """Rotate list by k items forward.  Ie. item at position 0 will be
    at position k in returned list.  Negative k is allowed."""
    n = len(l)
    k %= n
    if not k:
        return l
    return l[n - k :] + l[: n - k]


def _rot_set(s: set, k: int, n: int):
    k %= n
    if not k:
        return s
    return {(v + k) % n for v in s}


def iup_contour_optimize(
    deltas: _DeltaSegment, coords: _PointSegment, tolerance: Real = 0.0
) -> _DeltaOrNoneSegment:
    """For contour with coordinates `coords`, optimize a set of delta
    values `deltas` within error `tolerance`.

    Returns delta vector that has most number of None items instead of
    the input delta.
    """

    n = len(deltas)

    # Get the easy cases out of the way:

    # If all are within tolerance distance of 0, encode nothing:
    if all(abs(complex(*p)) <= tolerance for p in deltas):
        return [None] * n

    # If there's exactly one point, return it:
    if n == 1:
        return deltas

    # If all deltas are exactly the same, return just one (the first one):
    d0 = deltas[0]
    if all(d0 == d for d in deltas):
        return [d0] + [None] * (n - 1)

    # Else, solve the general problem using Dynamic Programming.

    forced = _iup_contour_bound_forced_set(deltas, coords, tolerance)
    # The _iup_contour_optimize_dp() routine returns the optimal encoding
    # solution given the constraint that the last point is always encoded.
    # To remove this constraint, we use two different methods, depending on
    # whether forced set is non-empty or not:

    # Debugging: Make the next if always take the second branch and observe
    # if the font size changes (reduced); that would mean the forced-set
    # has members it should not have.
    if forced:
        # Forced set is non-empty: rotate the contour start point
        # such that the last point in the list is a forced point.
        k = (n - 1) - max(forced)
        assert k >= 0

        deltas = _rot_list(deltas, k)
        coords = _rot_list(coords, k)
        forced = _rot_set(forced, k, n)

        # Debugging: Pass a set() instead of forced variable to the next call
        # to exercise forced-set computation for under-counting.
        chain, costs = _iup_contour_optimize_dp(deltas, coords, forced, tolerance)

        # Assemble solution.
        solution = set()
        i = n - 1
        while i is not None:
            solution.add(i)
            i = chain[i]
        solution.remove(-1)

        # if not forced <= solution:
        # 	print("coord", coords)
        # 	print("deltas", deltas)
        # 	print("len", len(deltas))
        assert forced <= solution, (forced, solution)

        deltas = [deltas[i] if i in solution else None for i in range(n)]

        deltas = _rot_list(deltas, -k)
    else:
        # Repeat the contour an extra time, solve the new case, then look for solutions of the
        # circular n-length problem in the solution for new linear case.  I cannot prove that
        # this always produces the optimal solution...
        chain, costs = _iup_contour_optimize_dp(
            deltas + deltas, coords + coords, forced, tolerance, n
        )
        best_sol, best_cost = None, n + 1

        for start in range(n - 1, len(costs) - 1):
            # Assemble solution.
            solution = set()
            i = start
            while i > start - n:
                solution.add(i % n)
                i = chain[i]
            if i == start - n:
                cost = costs[start] - costs[start - n]
                if cost <= best_cost:
                    best_sol, best_cost = solution, cost

        # if not forced <= best_sol:
        # 	print("coord", coords)
        # 	print("deltas", deltas)
        # 	print("len", len(deltas))
        assert forced <= best_sol, (forced, best_sol)

        deltas = [deltas[i] if i in best_sol else None for i in range(n)]

    return deltas


def iup_delta_optimize(
    deltas: _DeltaSegment,
    coords: _PointSegment,
    ends: _Endpoints,
    tolerance: Real = 0.0,
) -> _DeltaOrNoneSegment:
    """For the outline given in `coords`, with contour endpoints given
    in sorted increasing order in `ends`, optimize a set of delta
    values `deltas` within error `tolerance`.

    Returns delta vector that has most number of None items instead of
    the input delta.
    """
    assert sorted(ends) == ends and len(coords) == (ends[-1] + 1 if ends else 0) + 4
    n = len(coords)
    ends = ends + [n - 4, n - 3, n - 2, n - 1]
    out = []
    start = 0
    for end in ends:
        contour = iup_contour_optimize(
            deltas[start : end + 1], coords[start : end + 1], tolerance
        )
        assert len(contour) == end - start + 1
        out.extend(contour)
        start = end + 1

    return out

# === NexusCore/openenv\Lib\site-packages\nltk\translate\ibm4.py ===
# Natural Language Toolkit: IBM Model 4
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Translation model that reorders output words based on their type and
distance from other related words in the output sentence.

IBM Model 4 improves the distortion model of Model 3, motivated by the
observation that certain words tend to be re-ordered in a predictable
way relative to one another. For example, <adjective><noun> in English
usually has its order flipped as <noun><adjective> in French.

Model 4 requires words in the source and target vocabularies to be
categorized into classes. This can be linguistically driven, like parts
of speech (adjective, nouns, prepositions, etc). Word classes can also
be obtained by statistical methods. The original IBM Model 4 uses an
information theoretic approach to group words into 50 classes for each
vocabulary.

Terminology
-----------

:Cept:
    A source word with non-zero fertility i.e. aligned to one or more
    target words.
:Tablet:
    The set of target word(s) aligned to a cept.
:Head of cept:
    The first word of the tablet of that cept.
:Center of cept:
    The average position of the words in that cept's tablet. If the
    value is not an integer, the ceiling is taken.
    For example, for a tablet with words in positions 2, 5, 6 in the
    target sentence, the center of the corresponding cept is
    ceil((2 + 5 + 6) / 3) = 5
:Displacement:
    For a head word, defined as (position of head word - position of
    previous cept's center). Can be positive or negative.
    For a non-head word, defined as (position of non-head word -
    position of previous word in the same tablet). Always positive,
    because successive words in a tablet are assumed to appear to the
    right of the previous word.

In contrast to Model 3 which reorders words in a tablet independently of
other words, Model 4 distinguishes between three cases.

1. Words generated by NULL are distributed uniformly.
2. For a head word t, its position is modeled by the probability
   d_head(displacement | word_class_s(s),word_class_t(t)),
   where s is the previous cept, and word_class_s and word_class_t maps
   s and t to a source and target language word class respectively.
3. For a non-head word t, its position is modeled by the probability
   d_non_head(displacement | word_class_t(t))

The EM algorithm used in Model 4 is:

:E step: In the training data, collect counts, weighted by prior
         probabilities.

         - (a) count how many times a source language word is translated
               into a target language word
         - (b) for a particular word class, count how many times a head
               word is located at a particular displacement from the
               previous cept's center
         - (c) for a particular word class, count how many times a
               non-head word is located at a particular displacement from
               the previous target word
         - (d) count how many times a source word is aligned to phi number
               of target words
         - (e) count how many times NULL is aligned to a target word

:M step: Estimate new probabilities based on the counts from the E step

Like Model 3, there are too many possible alignments to consider. Thus,
a hill climbing approach is used to sample good candidates.

Notations
---------

:i: Position in the source sentence
     Valid values are 0 (for NULL), 1, 2, ..., length of source sentence
:j: Position in the target sentence
     Valid values are 1, 2, ..., length of target sentence
:l: Number of words in the source sentence, excluding NULL
:m: Number of words in the target sentence
:s: A word in the source language
:t: A word in the target language
:phi: Fertility, the number of target words produced by a source word
:p1: Probability that a target word produced by a source word is
     accompanied by another target word that is aligned to NULL
:p0: 1 - p1
:dj: Displacement, Δj

References
----------

Philipp Koehn. 2010. Statistical Machine Translation.
Cambridge University Press, New York.

Peter E Brown, Stephen A. Della Pietra, Vincent J. Della Pietra, and
Robert L. Mercer. 1993. The Mathematics of Statistical Machine
Translation: Parameter Estimation. Computational Linguistics, 19 (2),
263-311.
"""

import warnings
from collections import defaultdict
from math import factorial

from nltk.translate import AlignedSent, Alignment, IBMModel, IBMModel3
from nltk.translate.ibm_model import Counts, longest_target_sentence_length


class IBMModel4(IBMModel):
    """
    Translation model that reorders output words based on their type and
    their distance from other related words in the output sentence

    >>> bitext = []
    >>> bitext.append(AlignedSent(['klein', 'ist', 'das', 'haus'], ['the', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus', 'war', 'ja', 'groß'], ['the', 'house', 'was', 'big']))
    >>> bitext.append(AlignedSent(['das', 'buch', 'ist', 'ja', 'klein'], ['the', 'book', 'is', 'small']))
    >>> bitext.append(AlignedSent(['ein', 'haus', 'ist', 'klein'], ['a', 'house', 'is', 'small']))
    >>> bitext.append(AlignedSent(['das', 'haus'], ['the', 'house']))
    >>> bitext.append(AlignedSent(['das', 'buch'], ['the', 'book']))
    >>> bitext.append(AlignedSent(['ein', 'buch'], ['a', 'book']))
    >>> bitext.append(AlignedSent(['ich', 'fasse', 'das', 'buch', 'zusammen'], ['i', 'summarize', 'the', 'book']))
    >>> bitext.append(AlignedSent(['fasse', 'zusammen'], ['summarize']))
    >>> src_classes = {'the': 0, 'a': 0, 'small': 1, 'big': 1, 'house': 2, 'book': 2, 'is': 3, 'was': 3, 'i': 4, 'summarize': 5 }
    >>> trg_classes = {'das': 0, 'ein': 0, 'haus': 1, 'buch': 1, 'klein': 2, 'groß': 2, 'ist': 3, 'war': 3, 'ja': 4, 'ich': 5, 'fasse': 6, 'zusammen': 6 }

    >>> ibm4 = IBMModel4(bitext, 5, src_classes, trg_classes)

    >>> print(round(ibm4.translation_table['buch']['book'], 3))
    1.0
    >>> print(round(ibm4.translation_table['das']['book'], 3))
    0.0
    >>> print(round(ibm4.translation_table['ja'][None], 3))
    1.0

    >>> print(round(ibm4.head_distortion_table[1][0][1], 3))
    1.0
    >>> print(round(ibm4.head_distortion_table[2][0][1], 3))
    0.0
    >>> print(round(ibm4.non_head_distortion_table[3][6], 3))
    0.5

    >>> print(round(ibm4.fertility_table[2]['summarize'], 3))
    1.0
    >>> print(round(ibm4.fertility_table[1]['book'], 3))
    1.0

    >>> print(round(ibm4.p1, 3))
    0.033

    >>> test_sentence = bitext[2]
    >>> test_sentence.words
    ['das', 'buch', 'ist', 'ja', 'klein']
    >>> test_sentence.mots
    ['the', 'book', 'is', 'small']
    >>> test_sentence.alignment
    Alignment([(0, 0), (1, 1), (2, 2), (3, None), (4, 3)])

    """

    def __init__(
        self,
        sentence_aligned_corpus,
        iterations,
        source_word_classes,
        target_word_classes,
        probability_tables=None,
    ):
        """
        Train on ``sentence_aligned_corpus`` and create a lexical
        translation model, distortion models, a fertility model, and a
        model for generating NULL-aligned words.

        Translation direction is from ``AlignedSent.mots`` to
        ``AlignedSent.words``.

        :param sentence_aligned_corpus: Sentence-aligned parallel corpus
        :type sentence_aligned_corpus: list(AlignedSent)

        :param iterations: Number of iterations to run training algorithm
        :type iterations: int

        :param source_word_classes: Lookup table that maps a source word
            to its word class, the latter represented by an integer id
        :type source_word_classes: dict[str]: int

        :param target_word_classes: Lookup table that maps a target word
            to its word class, the latter represented by an integer id
        :type target_word_classes: dict[str]: int

        :param probability_tables: Optional. Use this to pass in custom
            probability values. If not specified, probabilities will be
            set to a uniform distribution, or some other sensible value.
            If specified, all the following entries must be present:
            ``translation_table``, ``alignment_table``,
            ``fertility_table``, ``p1``, ``head_distortion_table``,
            ``non_head_distortion_table``. See ``IBMModel`` and
            ``IBMModel4`` for the type and purpose of these tables.
        :type probability_tables: dict[str]: object
        """
        super().__init__(sentence_aligned_corpus)
        self.reset_probabilities()
        self.src_classes = source_word_classes
        self.trg_classes = target_word_classes

        if probability_tables is None:
            # Get probabilities from IBM model 3
            ibm3 = IBMModel3(sentence_aligned_corpus, iterations)
            self.translation_table = ibm3.translation_table
            self.alignment_table = ibm3.alignment_table
            self.fertility_table = ibm3.fertility_table
            self.p1 = ibm3.p1
            self.set_uniform_probabilities(sentence_aligned_corpus)
        else:
            # Set user-defined probabilities
            self.translation_table = probability_tables["translation_table"]
            self.alignment_table = probability_tables["alignment_table"]
            self.fertility_table = probability_tables["fertility_table"]
            self.p1 = probability_tables["p1"]
            self.head_distortion_table = probability_tables["head_distortion_table"]
            self.non_head_distortion_table = probability_tables[
                "non_head_distortion_table"
            ]

        for n in range(0, iterations):
            self.train(sentence_aligned_corpus)

    def reset_probabilities(self):
        super().reset_probabilities()
        self.head_distortion_table = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: self.MIN_PROB))
        )
        """
        dict[int][int][int]: float. Probability(displacement of head
        word | word class of previous cept,target word class).
        Values accessed as ``distortion_table[dj][src_class][trg_class]``.
        """

        self.non_head_distortion_table = defaultdict(
            lambda: defaultdict(lambda: self.MIN_PROB)
        )
        """
        dict[int][int]: float. Probability(displacement of non-head
        word | target word class).
        Values accessed as ``distortion_table[dj][trg_class]``.
        """

    def set_uniform_probabilities(self, sentence_aligned_corpus):
        """
        Set distortion probabilities uniformly to
        1 / cardinality of displacement values
        """
        max_m = longest_target_sentence_length(sentence_aligned_corpus)

        # The maximum displacement is m-1, when a word is in the last
        # position m of the target sentence and the previously placed
        # word is in the first position.
        # Conversely, the minimum displacement is -(m-1).
        # Thus, the displacement range is (m-1) - (-(m-1)). Note that
        # displacement cannot be zero and is not included in the range.
        if max_m <= 1:
            initial_prob = IBMModel.MIN_PROB
        else:
            initial_prob = 1 / (2 * (max_m - 1))
        if initial_prob < IBMModel.MIN_PROB:
            warnings.warn(
                "A target sentence is too long ("
                + str(max_m)
                + " words). Results may be less accurate."
            )

        for dj in range(1, max_m):
            self.head_distortion_table[dj] = defaultdict(
                lambda: defaultdict(lambda: initial_prob)
            )
            self.head_distortion_table[-dj] = defaultdict(
                lambda: defaultdict(lambda: initial_prob)
            )
            self.non_head_distortion_table[dj] = defaultdict(lambda: initial_prob)
            self.non_head_distortion_table[-dj] = defaultdict(lambda: initial_prob)

    def train(self, parallel_corpus):
        counts = Model4Counts()
        for aligned_sentence in parallel_corpus:
            m = len(aligned_sentence.words)

            # Sample the alignment space
            sampled_alignments, best_alignment = self.sample(aligned_sentence)
            # Record the most probable alignment
            aligned_sentence.alignment = Alignment(
                best_alignment.zero_indexed_alignment()
            )

            # E step (a): Compute normalization factors to weigh counts
            total_count = self.prob_of_alignments(sampled_alignments)

            # E step (b): Collect counts
            for alignment_info in sampled_alignments:
                count = self.prob_t_a_given_s(alignment_info)
                normalized_count = count / total_count

                for j in range(1, m + 1):
                    counts.update_lexical_translation(
                        normalized_count, alignment_info, j
                    )
                    counts.update_distortion(
                        normalized_count,
                        alignment_info,
                        j,
                        self.src_classes,
                        self.trg_classes,
                    )

                counts.update_null_generation(normalized_count, alignment_info)
                counts.update_fertility(normalized_count, alignment_info)

        # M step: Update probabilities with maximum likelihood estimates
        # If any probability is less than MIN_PROB, clamp it to MIN_PROB
        existing_alignment_table = self.alignment_table
        self.reset_probabilities()
        self.alignment_table = existing_alignment_table  # don't retrain

        self.maximize_lexical_translation_probabilities(counts)
        self.maximize_distortion_probabilities(counts)
        self.maximize_fertility_probabilities(counts)
        self.maximize_null_generation_probabilities(counts)

    def maximize_distortion_probabilities(self, counts):
        head_d_table = self.head_distortion_table
        for dj, src_classes in counts.head_distortion.items():
            for s_cls, trg_classes in src_classes.items():
                for t_cls in trg_classes:
                    estimate = (
                        counts.head_distortion[dj][s_cls][t_cls]
                        / counts.head_distortion_for_any_dj[s_cls][t_cls]
                    )
                    head_d_table[dj][s_cls][t_cls] = max(estimate, IBMModel.MIN_PROB)

        non_head_d_table = self.non_head_distortion_table
        for dj, trg_classes in counts.non_head_distortion.items():
            for t_cls in trg_classes:
                estimate = (
                    counts.non_head_distortion[dj][t_cls]
                    / counts.non_head_distortion_for_any_dj[t_cls]
                )
                non_head_d_table[dj][t_cls] = max(estimate, IBMModel.MIN_PROB)

    def prob_t_a_given_s(self, alignment_info):
        """
        Probability of target sentence and an alignment given the
        source sentence
        """
        return IBMModel4.model4_prob_t_a_given_s(alignment_info, self)

    @staticmethod  # exposed for Model 5 to use
    def model4_prob_t_a_given_s(alignment_info, ibm_model):
        probability = 1.0
        MIN_PROB = IBMModel.MIN_PROB

        def null_generation_term():
            # Binomial distribution: B(m - null_fertility, p1)
            value = 1.0
            p1 = ibm_model.p1
            p0 = 1 - p1
            null_fertility = alignment_info.fertility_of_i(0)
            m = len(alignment_info.trg_sentence) - 1
            value *= pow(p1, null_fertility) * pow(p0, m - 2 * null_fertility)
            if value < MIN_PROB:
                return MIN_PROB

            # Combination: (m - null_fertility) choose null_fertility
            for i in range(1, null_fertility + 1):
                value *= (m - null_fertility - i + 1) / i
            return value

        def fertility_term():
            value = 1.0
            src_sentence = alignment_info.src_sentence
            for i in range(1, len(src_sentence)):
                fertility = alignment_info.fertility_of_i(i)
                value *= (
                    factorial(fertility)
                    * ibm_model.fertility_table[fertility][src_sentence[i]]
                )
                if value < MIN_PROB:
                    return MIN_PROB
            return value

        def lexical_translation_term(j):
            t = alignment_info.trg_sentence[j]
            i = alignment_info.alignment[j]
            s = alignment_info.src_sentence[i]
            return ibm_model.translation_table[t][s]

        def distortion_term(j):
            t = alignment_info.trg_sentence[j]
            i = alignment_info.alignment[j]
            if i == 0:
                # case 1: t is aligned to NULL
                return 1.0
            if alignment_info.is_head_word(j):
                # case 2: t is the first word of a tablet
                previous_cept = alignment_info.previous_cept(j)
                src_class = None
                if previous_cept is not None:
                    previous_s = alignment_info.src_sentence[previous_cept]
                    src_class = ibm_model.src_classes[previous_s]
                trg_class = ibm_model.trg_classes[t]
                dj = j - alignment_info.center_of_cept(previous_cept)
                return ibm_model.head_distortion_table[dj][src_class][trg_class]

            # case 3: t is a subsequent word of a tablet
            previous_position = alignment_info.previous_in_tablet(j)
            trg_class = ibm_model.trg_classes[t]
            dj = j - previous_position
            return ibm_model.non_head_distortion_table[dj][trg_class]

        # end nested functions

        # Abort computation whenever probability falls below MIN_PROB at
        # any point, since MIN_PROB can be considered as zero
        probability *= null_generation_term()
        if probability < MIN_PROB:
            return MIN_PROB

        probability *= fertility_term()
        if probability < MIN_PROB:
            return MIN_PROB

        for j in range(1, len(alignment_info.trg_sentence)):
            probability *= lexical_translation_term(j)
            if probability < MIN_PROB:
                return MIN_PROB

            probability *= distortion_term(j)
            if probability < MIN_PROB:
                return MIN_PROB

        return probability


class Model4Counts(Counts):
    """
    Data object to store counts of various parameters during training.
    Includes counts for distortion.
    """

    def __init__(self):
        super().__init__()
        self.head_distortion = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        self.head_distortion_for_any_dj = defaultdict(lambda: defaultdict(float))
        self.non_head_distortion = defaultdict(lambda: defaultdict(float))
        self.non_head_distortion_for_any_dj = defaultdict(float)

    def update_distortion(self, count, alignment_info, j, src_classes, trg_classes):
        i = alignment_info.alignment[j]
        t = alignment_info.trg_sentence[j]
        if i == 0:
            # case 1: t is aligned to NULL
            pass
        elif alignment_info.is_head_word(j):
            # case 2: t is the first word of a tablet
            previous_cept = alignment_info.previous_cept(j)
            if previous_cept is not None:
                previous_src_word = alignment_info.src_sentence[previous_cept]
                src_class = src_classes[previous_src_word]
            else:
                src_class = None
            trg_class = trg_classes[t]
            dj = j - alignment_info.center_of_cept(previous_cept)
            self.head_distortion[dj][src_class][trg_class] += count
            self.head_distortion_for_any_dj[src_class][trg_class] += count
        else:
            # case 3: t is a subsequent word of a tablet
            previous_j = alignment_info.previous_in_tablet(j)
            trg_class = trg_classes[t]
            dj = j - previous_j
            self.non_head_distortion[dj][trg_class] += count
            self.non_head_distortion_for_any_dj[trg_class] += count

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_ufunc_config.py ===
"""
Functions for changing global ufunc configuration

This provides helpers which wrap `_get_extobj_dict` and `_make_extobj`, and
`_extobj_contextvar` from umath.
"""
import functools

from numpy._utils import set_module

from .umath import _extobj_contextvar, _get_extobj_dict, _make_extobj

__all__ = [
    "seterr", "geterr", "setbufsize", "getbufsize", "seterrcall", "geterrcall",
    "errstate"
]


@set_module('numpy')
def seterr(all=None, divide=None, over=None, under=None, invalid=None):
    """
    Set how floating-point errors are handled.

    Note that operations on integer scalar types (such as `int16`) are
    handled like floating point, and are affected by these settings.

    Parameters
    ----------
    all : {'ignore', 'warn', 'raise', 'call', 'print', 'log'}, optional
        Set treatment for all types of floating-point errors at once:

        - ignore: Take no action when the exception occurs.
        - warn: Print a :exc:`RuntimeWarning` (via the Python `warnings`
          module).
        - raise: Raise a :exc:`FloatingPointError`.
        - call: Call a function specified using the `seterrcall` function.
        - print: Print a warning directly to ``stdout``.
        - log: Record error in a Log object specified by `seterrcall`.

        The default is not to change the current behavior.
    divide : {'ignore', 'warn', 'raise', 'call', 'print', 'log'}, optional
        Treatment for division by zero.
    over : {'ignore', 'warn', 'raise', 'call', 'print', 'log'}, optional
        Treatment for floating-point overflow.
    under : {'ignore', 'warn', 'raise', 'call', 'print', 'log'}, optional
        Treatment for floating-point underflow.
    invalid : {'ignore', 'warn', 'raise', 'call', 'print', 'log'}, optional
        Treatment for invalid floating-point operation.

    Returns
    -------
    old_settings : dict
        Dictionary containing the old settings.

    See also
    --------
    seterrcall : Set a callback function for the 'call' mode.
    geterr, geterrcall, errstate

    Notes
    -----
    The floating-point exceptions are defined in the IEEE 754 standard [1]_:

    - Division by zero: infinite result obtained from finite numbers.
    - Overflow: result too large to be expressed.
    - Underflow: result so close to zero that some precision
      was lost.
    - Invalid operation: result is not an expressible number, typically
      indicates that a NaN was produced.

    .. [1] https://en.wikipedia.org/wiki/IEEE_754

    Examples
    --------
    >>> import numpy as np
    >>> orig_settings = np.seterr(all='ignore')  # seterr to known value
    >>> np.int16(32000) * np.int16(3)
    np.int16(30464)
    >>> np.seterr(over='raise')
    {'divide': 'ignore', 'over': 'ignore', 'under': 'ignore', 'invalid': 'ignore'}
    >>> old_settings = np.seterr(all='warn', over='raise')
    >>> np.int16(32000) * np.int16(3)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    FloatingPointError: overflow encountered in scalar multiply

    >>> old_settings = np.seterr(all='print')
    >>> np.geterr()
    {'divide': 'print', 'over': 'print', 'under': 'print', 'invalid': 'print'}
    >>> np.int16(32000) * np.int16(3)
    np.int16(30464)
    >>> np.seterr(**orig_settings)  # restore original
    {'divide': 'print', 'over': 'print', 'under': 'print', 'invalid': 'print'}

    """

    old = _get_extobj_dict()
    # The errstate doesn't include call and bufsize, so pop them:
    old.pop("call", None)
    old.pop("bufsize", None)

    extobj = _make_extobj(
            all=all, divide=divide, over=over, under=under, invalid=invalid)
    _extobj_contextvar.set(extobj)
    return old


@set_module('numpy')
def geterr():
    """
    Get the current way of handling floating-point errors.

    Returns
    -------
    res : dict
        A dictionary with keys "divide", "over", "under", and "invalid",
        whose values are from the strings "ignore", "print", "log", "warn",
        "raise", and "call". The keys represent possible floating-point
        exceptions, and the values define how these exceptions are handled.

    See Also
    --------
    geterrcall, seterr, seterrcall

    Notes
    -----
    For complete documentation of the types of floating-point exceptions and
    treatment options, see `seterr`.

    Examples
    --------
    >>> import numpy as np
    >>> np.geterr()
    {'divide': 'warn', 'over': 'warn', 'under': 'ignore', 'invalid': 'warn'}
    >>> np.arange(3.) / np.arange(3.)  # doctest: +SKIP
    array([nan,  1.,  1.])
    RuntimeWarning: invalid value encountered in divide

    >>> oldsettings = np.seterr(all='warn', invalid='raise')
    >>> np.geterr()
    {'divide': 'warn', 'over': 'warn', 'under': 'warn', 'invalid': 'raise'}
    >>> np.arange(3.) / np.arange(3.)
    Traceback (most recent call last):
      ...
    FloatingPointError: invalid value encountered in divide
    >>> oldsettings = np.seterr(**oldsettings)  # restore original

    """
    res = _get_extobj_dict()
    # The "geterr" doesn't include call and bufsize,:
    res.pop("call", None)
    res.pop("bufsize", None)
    return res


@set_module('numpy')
def setbufsize(size):
    """
    Set the size of the buffer used in ufuncs.

    .. versionchanged:: 2.0
        The scope of setting the buffer is tied to the `numpy.errstate`
        context.  Exiting a ``with errstate():`` will also restore the bufsize.

    Parameters
    ----------
    size : int
        Size of buffer.

    Returns
    -------
    bufsize : int
        Previous size of ufunc buffer in bytes.

    Examples
    --------
    When exiting a `numpy.errstate` context manager the bufsize is restored:

    >>> import numpy as np
    >>> with np.errstate():
    ...     np.setbufsize(4096)
    ...     print(np.getbufsize())
    ...
    8192
    4096
    >>> np.getbufsize()
    8192

    """
    old = _get_extobj_dict()["bufsize"]
    extobj = _make_extobj(bufsize=size)
    _extobj_contextvar.set(extobj)
    return old


@set_module('numpy')
def getbufsize():
    """
    Return the size of the buffer used in ufuncs.

    Returns
    -------
    getbufsize : int
        Size of ufunc buffer in bytes.

    Examples
    --------
    >>> import numpy as np
    >>> np.getbufsize()
    8192

    """
    return _get_extobj_dict()["bufsize"]


@set_module('numpy')
def seterrcall(func):
    """
    Set the floating-point error callback function or log object.

    There are two ways to capture floating-point error messages.  The first
    is to set the error-handler to 'call', using `seterr`.  Then, set
    the function to call using this function.

    The second is to set the error-handler to 'log', using `seterr`.
    Floating-point errors then trigger a call to the 'write' method of
    the provided object.

    Parameters
    ----------
    func : callable f(err, flag) or object with write method
        Function to call upon floating-point errors ('call'-mode) or
        object whose 'write' method is used to log such message ('log'-mode).

        The call function takes two arguments. The first is a string describing
        the type of error (such as "divide by zero", "overflow", "underflow",
        or "invalid value"), and the second is the status flag.  The flag is a
        byte, whose four least-significant bits indicate the type of error, one
        of "divide", "over", "under", "invalid"::

          [0 0 0 0 divide over under invalid]

        In other words, ``flags = divide + 2*over + 4*under + 8*invalid``.

        If an object is provided, its write method should take one argument,
        a string.

    Returns
    -------
    h : callable, log instance or None
        The old error handler.

    See Also
    --------
    seterr, geterr, geterrcall

    Examples
    --------
    Callback upon error:

    >>> def err_handler(type, flag):
    ...     print("Floating point error (%s), with flag %s" % (type, flag))
    ...

    >>> import numpy as np

    >>> orig_handler = np.seterrcall(err_handler)
    >>> orig_err = np.seterr(all='call')

    >>> np.array([1, 2, 3]) / 0.0
    Floating point error (divide by zero), with flag 1
    array([inf, inf, inf])

    >>> np.seterrcall(orig_handler)
    <function err_handler at 0x...>
    >>> np.seterr(**orig_err)
    {'divide': 'call', 'over': 'call', 'under': 'call', 'invalid': 'call'}

    Log error message:

    >>> class Log:
    ...     def write(self, msg):
    ...         print("LOG: %s" % msg)
    ...

    >>> log = Log()
    >>> saved_handler = np.seterrcall(log)
    >>> save_err = np.seterr(all='log')

    >>> np.array([1, 2, 3]) / 0.0
    LOG: Warning: divide by zero encountered in divide
    array([inf, inf, inf])

    >>> np.seterrcall(orig_handler)
    <numpy.Log object at 0x...>
    >>> np.seterr(**orig_err)
    {'divide': 'log', 'over': 'log', 'under': 'log', 'invalid': 'log'}

    """
    old = _get_extobj_dict()["call"]
    extobj = _make_extobj(call=func)
    _extobj_contextvar.set(extobj)
    return old


@set_module('numpy')
def geterrcall():
    """
    Return the current callback function used on floating-point errors.

    When the error handling for a floating-point error (one of "divide",
    "over", "under", or "invalid") is set to 'call' or 'log', the function
    that is called or the log instance that is written to is returned by
    `geterrcall`. This function or log instance has been set with
    `seterrcall`.

    Returns
    -------
    errobj : callable, log instance or None
        The current error handler. If no handler was set through `seterrcall`,
        ``None`` is returned.

    See Also
    --------
    seterrcall, seterr, geterr

    Notes
    -----
    For complete documentation of the types of floating-point exceptions and
    treatment options, see `seterr`.

    Examples
    --------
    >>> import numpy as np
    >>> np.geterrcall()  # we did not yet set a handler, returns None

    >>> orig_settings = np.seterr(all='call')
    >>> def err_handler(type, flag):
    ...     print("Floating point error (%s), with flag %s" % (type, flag))
    >>> old_handler = np.seterrcall(err_handler)
    >>> np.array([1, 2, 3]) / 0.0
    Floating point error (divide by zero), with flag 1
    array([inf, inf, inf])

    >>> cur_handler = np.geterrcall()
    >>> cur_handler is err_handler
    True
    >>> old_settings = np.seterr(**orig_settings)  # restore original
    >>> old_handler = np.seterrcall(None)  # restore original

    """
    return _get_extobj_dict()["call"]


class _unspecified:
    pass


_Unspecified = _unspecified()


@set_module('numpy')
class errstate:
    """
    errstate(**kwargs)

    Context manager for floating-point error handling.

    Using an instance of `errstate` as a context manager allows statements in
    that context to execute with a known error handling behavior. Upon entering
    the context the error handling is set with `seterr` and `seterrcall`, and
    upon exiting it is reset to what it was before.

    ..  versionchanged:: 1.17.0
        `errstate` is also usable as a function decorator, saving
        a level of indentation if an entire function is wrapped.

    .. versionchanged:: 2.0
        `errstate` is now fully thread and asyncio safe, but may not be
        entered more than once.
        It is not safe to decorate async functions using ``errstate``.

    Parameters
    ----------
    kwargs : {divide, over, under, invalid}
        Keyword arguments. The valid keywords are the possible floating-point
        exceptions. Each keyword should have a string value that defines the
        treatment for the particular error. Possible values are
        {'ignore', 'warn', 'raise', 'call', 'print', 'log'}.

    See Also
    --------
    seterr, geterr, seterrcall, geterrcall

    Notes
    -----
    For complete documentation of the types of floating-point exceptions and
    treatment options, see `seterr`.

    Examples
    --------
    >>> import numpy as np
    >>> olderr = np.seterr(all='ignore')  # Set error handling to known state.

    >>> np.arange(3) / 0.
    array([nan, inf, inf])
    >>> with np.errstate(divide='ignore'):
    ...     np.arange(3) / 0.
    array([nan, inf, inf])

    >>> np.sqrt(-1)
    np.float64(nan)
    >>> with np.errstate(invalid='raise'):
    ...     np.sqrt(-1)
    Traceback (most recent call last):
      File "<stdin>", line 2, in <module>
    FloatingPointError: invalid value encountered in sqrt

    Outside the context the error handling behavior has not changed:

    >>> np.geterr()
    {'divide': 'ignore', 'over': 'ignore', 'under': 'ignore', 'invalid': 'ignore'}
    >>> olderr = np.seterr(**olderr)  # restore original state

    """
    __slots__ = (
        "_all",
        "_call",
        "_divide",
        "_invalid",
        "_over",
        "_token",
        "_under",
    )

    def __init__(self, *, call=_Unspecified,
                 all=None, divide=None, over=None, under=None, invalid=None):
        self._token = None
        self._call = call
        self._all = all
        self._divide = divide
        self._over = over
        self._under = under
        self._invalid = invalid

    def __enter__(self):
        # Note that __call__ duplicates much of this logic
        if self._token is not None:
            raise TypeError("Cannot enter `np.errstate` twice.")
        if self._call is _Unspecified:
            extobj = _make_extobj(
                    all=self._all, divide=self._divide, over=self._over,
                    under=self._under, invalid=self._invalid)
        else:
            extobj = _make_extobj(
                    call=self._call,
                    all=self._all, divide=self._divide, over=self._over,
                    under=self._under, invalid=self._invalid)

        self._token = _extobj_contextvar.set(extobj)

    def __exit__(self, *exc_info):
        _extobj_contextvar.reset(self._token)

    def __call__(self, func):
        # We need to customize `__call__` compared to `ContextDecorator`
        # because we must store the token per-thread so cannot store it on
        # the instance (we could create a new instance for this).
        # This duplicates the code from `__enter__`.
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if self._call is _Unspecified:
                extobj = _make_extobj(
                        all=self._all, divide=self._divide, over=self._over,
                        under=self._under, invalid=self._invalid)
            else:
                extobj = _make_extobj(
                        call=self._call,
                        all=self._all, divide=self._divide, over=self._over,
                        under=self._under, invalid=self._invalid)

            _token = _extobj_contextvar.set(extobj)
            try:
                # Call the original, decorated, function:
                return func(*args, **kwargs)
            finally:
                _extobj_contextvar.reset(_token)

        return inner

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\remote_connection.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
import platform
import string
import warnings
from base64 import b64encode
from typing import Optional
from urllib import parse
from urllib.parse import urlparse

import urllib3

from selenium import __version__

from . import utils
from .client_config import ClientConfig
from .command import Command
from .errorhandler import ErrorCode

LOGGER = logging.getLogger(__name__)

remote_commands = {
    Command.NEW_SESSION: ("POST", "/session"),
    Command.QUIT: ("DELETE", "/session/$sessionId"),
    Command.W3C_GET_CURRENT_WINDOW_HANDLE: ("GET", "/session/$sessionId/window"),
    Command.W3C_GET_WINDOW_HANDLES: ("GET", "/session/$sessionId/window/handles"),
    Command.GET: ("POST", "/session/$sessionId/url"),
    Command.GO_FORWARD: ("POST", "/session/$sessionId/forward"),
    Command.GO_BACK: ("POST", "/session/$sessionId/back"),
    Command.REFRESH: ("POST", "/session/$sessionId/refresh"),
    Command.W3C_EXECUTE_SCRIPT: ("POST", "/session/$sessionId/execute/sync"),
    Command.W3C_EXECUTE_SCRIPT_ASYNC: ("POST", "/session/$sessionId/execute/async"),
    Command.GET_CURRENT_URL: ("GET", "/session/$sessionId/url"),
    Command.GET_TITLE: ("GET", "/session/$sessionId/title"),
    Command.GET_PAGE_SOURCE: ("GET", "/session/$sessionId/source"),
    Command.SCREENSHOT: ("GET", "/session/$sessionId/screenshot"),
    Command.ELEMENT_SCREENSHOT: ("GET", "/session/$sessionId/element/$id/screenshot"),
    Command.FIND_ELEMENT: ("POST", "/session/$sessionId/element"),
    Command.FIND_ELEMENTS: ("POST", "/session/$sessionId/elements"),
    Command.W3C_GET_ACTIVE_ELEMENT: ("GET", "/session/$sessionId/element/active"),
    Command.FIND_CHILD_ELEMENT: ("POST", "/session/$sessionId/element/$id/element"),
    Command.FIND_CHILD_ELEMENTS: ("POST", "/session/$sessionId/element/$id/elements"),
    Command.CLICK_ELEMENT: ("POST", "/session/$sessionId/element/$id/click"),
    Command.CLEAR_ELEMENT: ("POST", "/session/$sessionId/element/$id/clear"),
    Command.GET_ELEMENT_TEXT: ("GET", "/session/$sessionId/element/$id/text"),
    Command.SEND_KEYS_TO_ELEMENT: ("POST", "/session/$sessionId/element/$id/value"),
    Command.GET_ELEMENT_TAG_NAME: ("GET", "/session/$sessionId/element/$id/name"),
    Command.IS_ELEMENT_SELECTED: ("GET", "/session/$sessionId/element/$id/selected"),
    Command.IS_ELEMENT_ENABLED: ("GET", "/session/$sessionId/element/$id/enabled"),
    Command.GET_ELEMENT_RECT: ("GET", "/session/$sessionId/element/$id/rect"),
    Command.GET_ELEMENT_ATTRIBUTE: ("GET", "/session/$sessionId/element/$id/attribute/$name"),
    Command.GET_ELEMENT_PROPERTY: ("GET", "/session/$sessionId/element/$id/property/$name"),
    Command.GET_ELEMENT_ARIA_ROLE: ("GET", "/session/$sessionId/element/$id/computedrole"),
    Command.GET_ELEMENT_ARIA_LABEL: ("GET", "/session/$sessionId/element/$id/computedlabel"),
    Command.GET_SHADOW_ROOT: ("GET", "/session/$sessionId/element/$id/shadow"),
    Command.FIND_ELEMENT_FROM_SHADOW_ROOT: ("POST", "/session/$sessionId/shadow/$shadowId/element"),
    Command.FIND_ELEMENTS_FROM_SHADOW_ROOT: ("POST", "/session/$sessionId/shadow/$shadowId/elements"),
    Command.GET_ALL_COOKIES: ("GET", "/session/$sessionId/cookie"),
    Command.ADD_COOKIE: ("POST", "/session/$sessionId/cookie"),
    Command.GET_COOKIE: ("GET", "/session/$sessionId/cookie/$name"),
    Command.DELETE_ALL_COOKIES: ("DELETE", "/session/$sessionId/cookie"),
    Command.DELETE_COOKIE: ("DELETE", "/session/$sessionId/cookie/$name"),
    Command.SWITCH_TO_FRAME: ("POST", "/session/$sessionId/frame"),
    Command.SWITCH_TO_PARENT_FRAME: ("POST", "/session/$sessionId/frame/parent"),
    Command.SWITCH_TO_WINDOW: ("POST", "/session/$sessionId/window"),
    Command.NEW_WINDOW: ("POST", "/session/$sessionId/window/new"),
    Command.CLOSE: ("DELETE", "/session/$sessionId/window"),
    Command.GET_ELEMENT_VALUE_OF_CSS_PROPERTY: ("GET", "/session/$sessionId/element/$id/css/$propertyName"),
    Command.EXECUTE_ASYNC_SCRIPT: ("POST", "/session/$sessionId/execute_async"),
    Command.SET_TIMEOUTS: ("POST", "/session/$sessionId/timeouts"),
    Command.GET_TIMEOUTS: ("GET", "/session/$sessionId/timeouts"),
    Command.W3C_DISMISS_ALERT: ("POST", "/session/$sessionId/alert/dismiss"),
    Command.W3C_ACCEPT_ALERT: ("POST", "/session/$sessionId/alert/accept"),
    Command.W3C_SET_ALERT_VALUE: ("POST", "/session/$sessionId/alert/text"),
    Command.W3C_GET_ALERT_TEXT: ("GET", "/session/$sessionId/alert/text"),
    Command.W3C_ACTIONS: ("POST", "/session/$sessionId/actions"),
    Command.W3C_CLEAR_ACTIONS: ("DELETE", "/session/$sessionId/actions"),
    Command.SET_WINDOW_RECT: ("POST", "/session/$sessionId/window/rect"),
    Command.GET_WINDOW_RECT: ("GET", "/session/$sessionId/window/rect"),
    Command.W3C_MAXIMIZE_WINDOW: ("POST", "/session/$sessionId/window/maximize"),
    Command.SET_SCREEN_ORIENTATION: ("POST", "/session/$sessionId/orientation"),
    Command.GET_SCREEN_ORIENTATION: ("GET", "/session/$sessionId/orientation"),
    Command.GET_NETWORK_CONNECTION: ("GET", "/session/$sessionId/network_connection"),
    Command.SET_NETWORK_CONNECTION: ("POST", "/session/$sessionId/network_connection"),
    Command.GET_LOG: ("POST", "/session/$sessionId/se/log"),
    Command.GET_AVAILABLE_LOG_TYPES: ("GET", "/session/$sessionId/se/log/types"),
    Command.CURRENT_CONTEXT_HANDLE: ("GET", "/session/$sessionId/context"),
    Command.CONTEXT_HANDLES: ("GET", "/session/$sessionId/contexts"),
    Command.SWITCH_TO_CONTEXT: ("POST", "/session/$sessionId/context"),
    Command.FULLSCREEN_WINDOW: ("POST", "/session/$sessionId/window/fullscreen"),
    Command.MINIMIZE_WINDOW: ("POST", "/session/$sessionId/window/minimize"),
    Command.PRINT_PAGE: ("POST", "/session/$sessionId/print"),
    Command.ADD_VIRTUAL_AUTHENTICATOR: ("POST", "/session/$sessionId/webauthn/authenticator"),
    Command.REMOVE_VIRTUAL_AUTHENTICATOR: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId",
    ),
    Command.ADD_CREDENTIAL: ("POST", "/session/$sessionId/webauthn/authenticator/$authenticatorId/credential"),
    Command.GET_CREDENTIALS: ("GET", "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials"),
    Command.REMOVE_CREDENTIAL: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials/$credentialId",
    ),
    Command.REMOVE_ALL_CREDENTIALS: (
        "DELETE",
        "/session/$sessionId/webauthn/authenticator/$authenticatorId/credentials",
    ),
    Command.SET_USER_VERIFIED: ("POST", "/session/$sessionId/webauthn/authenticator/$authenticatorId/uv"),
    Command.UPLOAD_FILE: ("POST", "/session/$sessionId/se/file"),
    Command.GET_DOWNLOADABLE_FILES: ("GET", "/session/$sessionId/se/files"),
    Command.DOWNLOAD_FILE: ("POST", "/session/$sessionId/se/files"),
    Command.DELETE_DOWNLOADABLE_FILES: ("DELETE", "/session/$sessionId/se/files"),
    # Federated Credential Management (FedCM)
    Command.GET_FEDCM_TITLE: ("GET", "/session/$sessionId/fedcm/gettitle"),
    Command.GET_FEDCM_DIALOG_TYPE: ("GET", "/session/$sessionId/fedcm/getdialogtype"),
    Command.GET_FEDCM_ACCOUNT_LIST: ("GET", "/session/$sessionId/fedcm/accountlist"),
    Command.CLICK_FEDCM_DIALOG_BUTTON: ("POST", "/session/$sessionId/fedcm/clickdialogbutton"),
    Command.CANCEL_FEDCM_DIALOG: ("POST", "/session/$sessionId/fedcm/canceldialog"),
    Command.SELECT_FEDCM_ACCOUNT: ("POST", "/session/$sessionId/fedcm/selectaccount"),
    Command.SET_FEDCM_DELAY: ("POST", "/session/$sessionId/fedcm/setdelayenabled"),
    Command.RESET_FEDCM_COOLDOWN: ("POST", "/session/$sessionId/fedcm/resetcooldown"),
}


class RemoteConnection:
    """A connection with the Remote WebDriver server.

    Communicates with the server using the WebDriver wire protocol:
    https://github.com/SeleniumHQ/selenium/wiki/JsonWireProtocol
    """

    browser_name = None
    # Keep backward compatibility for AppiumConnection - https://github.com/SeleniumHQ/selenium/issues/14694
    import os
    import socket

    import certifi

    _timeout = socket.getdefaulttimeout()
    _ca_certs = os.getenv("REQUESTS_CA_BUNDLE") if "REQUESTS_CA_BUNDLE" in os.environ else certifi.where()
    _client_config: Optional[ClientConfig] = None

    system = platform.system().lower()
    if system == "darwin":
        system = "mac"

    # Class variables for headers
    extra_headers = None
    user_agent = f"selenium/{__version__} (python {system})"

    @property
    def client_config(self):
        return self._client_config

    @classmethod
    def get_timeout(cls):
        """:Returns:

        Timeout value in seconds for all http requests made to the
        Remote Connection
        """
        warnings.warn(
            "get_timeout() in RemoteConnection is deprecated, get timeout from client_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls._client_config.timeout

    @classmethod
    def set_timeout(cls, timeout):
        """Override the default timeout.

        :Args:
            - timeout - timeout value for http requests in seconds
        """
        warnings.warn(
            "set_timeout() in RemoteConnection is deprecated, set timeout in client_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        cls._client_config.timeout = timeout

    @classmethod
    def reset_timeout(cls):
        """Reset the http request timeout to socket._GLOBAL_DEFAULT_TIMEOUT."""
        warnings.warn(
            "reset_timeout() in RemoteConnection is deprecated, use reset_timeout() in client_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        cls._client_config.reset_timeout()

    @classmethod
    def get_certificate_bundle_path(cls):
        """:Returns:

        Paths of the .pem encoded certificate to verify connection to
        command executor. Defaults to certifi.where() or
        REQUESTS_CA_BUNDLE env variable if set.
        """
        warnings.warn(
            "get_certificate_bundle_path() in RemoteConnection is deprecated, get ca_certs from client_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls._client_config.ca_certs

    @classmethod
    def set_certificate_bundle_path(cls, path):
        """Set the path to the certificate bundle to verify connection to
        command executor. Can also be set to None to disable certificate
        validation.

        :Args:
            - path - path of a .pem encoded certificate chain.
        """
        warnings.warn(
            "set_certificate_bundle_path() in RemoteConnection is deprecated, set ca_certs in client_config instead",
            DeprecationWarning,
            stacklevel=2,
        )
        cls._client_config.ca_certs = path

    @classmethod
    def get_remote_connection_headers(cls, parsed_url, keep_alive=False):
        """Get headers for remote request.

        :Args:
         - parsed_url - The parsed url
         - keep_alive (Boolean) - Is this a keep-alive connection (default: False)
        """

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": cls.user_agent,
        }

        if parsed_url.username:
            warnings.warn(
                "Embedding username and password in URL could be insecure, use ClientConfig instead", stacklevel=2
            )
            base64string = b64encode(f"{parsed_url.username}:{parsed_url.password}".encode())
            headers.update({"Authorization": f"Basic {base64string.decode()}"})

        if keep_alive:
            headers.update({"Connection": "keep-alive"})

        if cls.extra_headers:
            headers.update(cls.extra_headers)

        return headers

    def _identify_http_proxy_auth(self):
        parsed_url = urlparse(self._proxy_url)
        if parsed_url.username and parsed_url.password:
            return True

    def _separate_http_proxy_auth(self):
        parsed_url = urlparse(self._proxy_url)
        proxy_without_auth = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
        auth = f"{parsed_url.username}:{parsed_url.password}"
        return proxy_without_auth, auth

    def _get_connection_manager(self):
        pool_manager_init_args = {"timeout": self._client_config.timeout}
        pool_manager_init_args.update(
            self._client_config.init_args_for_pool_manager.get("init_args_for_pool_manager", {})
        )

        if self._client_config.ignore_certificates:
            pool_manager_init_args["cert_reqs"] = "CERT_NONE"
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        elif self._client_config.ca_certs:
            pool_manager_init_args["cert_reqs"] = "CERT_REQUIRED"
            pool_manager_init_args["ca_certs"] = self._client_config.ca_certs

        if self._proxy_url:
            if self._proxy_url.lower().startswith("sock"):
                from urllib3.contrib.socks import SOCKSProxyManager

                return SOCKSProxyManager(self._proxy_url, **pool_manager_init_args)
            if self._identify_http_proxy_auth():
                self._proxy_url, self._basic_proxy_auth = self._separate_http_proxy_auth()
                pool_manager_init_args["proxy_headers"] = urllib3.make_headers(proxy_basic_auth=self._basic_proxy_auth)
            return urllib3.ProxyManager(self._proxy_url, **pool_manager_init_args)

        return urllib3.PoolManager(**pool_manager_init_args)

    def __init__(
        self,
        remote_server_addr: Optional[str] = None,
        keep_alive: Optional[bool] = True,
        ignore_proxy: Optional[bool] = False,
        ignore_certificates: Optional[bool] = False,
        init_args_for_pool_manager: Optional[dict] = None,
        client_config: Optional[ClientConfig] = None,
    ):
        self._client_config = client_config or ClientConfig(
            remote_server_addr=remote_server_addr,
            keep_alive=keep_alive,
            ignore_certificates=ignore_certificates,
            init_args_for_pool_manager=init_args_for_pool_manager,
        )

        # Keep backward compatibility for AppiumConnection - https://github.com/SeleniumHQ/selenium/issues/14694
        RemoteConnection._timeout = self._client_config.timeout
        RemoteConnection._ca_certs = self._client_config.ca_certs
        RemoteConnection._client_config = self._client_config
        RemoteConnection.extra_headers = self._client_config.extra_headers or RemoteConnection.extra_headers
        RemoteConnection.user_agent = self._client_config.user_agent or RemoteConnection.user_agent

        if remote_server_addr:
            warnings.warn(
                "setting remote_server_addr in RemoteConnection() is deprecated, set in client_config instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if not keep_alive:
            warnings.warn(
                "setting keep_alive in RemoteConnection() is deprecated, set in client_config instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if ignore_certificates:
            warnings.warn(
                "setting ignore_certificates in RemoteConnection() is deprecated, set in client_config instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if init_args_for_pool_manager:
            warnings.warn(
                "setting init_args_for_pool_manager in RemoteConnection() is deprecated, set in client_config instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if ignore_proxy:
            warnings.warn(
                "setting ignore_proxy in RemoteConnection() is deprecated, set in client_config instead",
                DeprecationWarning,
                stacklevel=2,
            )
            self._proxy_url = None
        else:
            self._proxy_url = self._client_config.get_proxy_url()

        if self._client_config.keep_alive:
            self._conn = self._get_connection_manager()
        self._commands = remote_commands

    extra_commands = {}

    def add_command(self, name, method, url):
        """Register a new command."""
        self._commands[name] = (method, url)

    def get_command(self, name: str):
        """Retrieve a command if it exists."""
        return self._commands.get(name)

    def execute(self, command, params):
        """Send a command to the remote server.

        Any path substitutions required for the URL mapped to the command should be
        included in the command parameters.

        :Args:
         - command - A string specifying the command to execute.
         - params - A dictionary of named parameters to send with the command as
           its JSON payload.
        """
        command_info = self._commands.get(command) or self.extra_commands.get(command)
        assert command_info is not None, f"Unrecognised command {command}"
        path_string = command_info[1]
        path = string.Template(path_string).substitute(params)
        substitute_params = {word[1:] for word in path_string.split("/") if word.startswith("$")}  # remove dollar sign
        if isinstance(params, dict) and substitute_params:
            for word in substitute_params:
                del params[word]
        data = utils.dump_json(params)
        url = f"{self._client_config.remote_server_addr}{path}"
        trimmed = self._trim_large_entries(params)
        LOGGER.debug("%s %s %s", command_info[0], url, str(trimmed))
        return self._request(command_info[0], url, body=data)

    def _request(self, method, url, body=None):
        """Send an HTTP request to the remote server.

        :Args:
         - method - A string for the HTTP method to send the request with.
         - url - A string for the URL to send the request to.
         - body - A string for request body. Ignored unless method is POST or PUT.

        :Returns:
          A dictionary with the server's parsed JSON response.
        """
        parsed_url = parse.urlparse(url)
        headers = self.get_remote_connection_headers(parsed_url, self._client_config.keep_alive)
        auth_header = self._client_config.get_auth_header()

        if auth_header:
            headers.update(auth_header)

        if body and method not in ("POST", "PUT"):
            body = None

        if self._client_config.keep_alive:
            response = self._conn.request(method, url, body=body, headers=headers, timeout=self._client_config.timeout)
            statuscode = response.status
        else:
            conn = self._get_connection_manager()
            with conn as http:
                response = http.request(method, url, body=body, headers=headers, timeout=self._client_config.timeout)
            statuscode = response.status
        data = response.data.decode("UTF-8")
        LOGGER.debug("Remote response: status=%s | data=%s | headers=%s", response.status, data, response.headers)
        try:
            if 300 <= statuscode < 304:
                return self._request("GET", response.headers.get("location", None))
            if 399 < statuscode <= 500:
                if statuscode == 401:
                    return {"status": statuscode, "value": "Authorization Required"}
                return {"status": statuscode, "value": str(statuscode) if not data else data.strip()}
            content_type = []
            if response.headers.get("Content-Type", None):
                content_type = response.headers.get("Content-Type", None).split(";")
            if not any([x.startswith("image/png") for x in content_type]):
                try:
                    data = utils.load_json(data.strip())
                except ValueError:
                    if 199 < statuscode < 300:
                        status = ErrorCode.SUCCESS
                    else:
                        status = ErrorCode.UNKNOWN_ERROR
                    return {"status": status, "value": data.strip()}

                # Some drivers incorrectly return a response
                # with no 'value' field when they should return null.
                if "value" not in data:
                    data["value"] = None
                return data
            data = {"status": 0, "value": data}
            return data
        finally:
            LOGGER.debug("Finished Request")
            response.close()

    def close(self):
        """Clean up resources when finished with the remote_connection."""
        if hasattr(self, "_conn"):
            self._conn.clear()

    def _trim_large_entries(self, input_dict, max_length=100):
        """Truncate string values in a dictionary if they exceed max_length.

        :param dict: Dictionary with potentially large values
        :param max_length: Maximum allowed length of string values
        :return: Dictionary with truncated string values
        """
        output_dictionary = {}
        for key, value in input_dict.items():
            if isinstance(value, dict):
                output_dictionary[key] = self._trim_large_entries(value, max_length)
            elif isinstance(value, str) and len(value) > max_length:
                output_dictionary[key] = value[:max_length] + "..."
            else:
                output_dictionary[key] = value

        return output_dictionary

# === NexusCore/openenv\Lib\site-packages\joblib\_store_backends.py ===
"""Storage providers backends for Memory caching."""

import collections
import datetime
import json
import operator
import os
import os.path
import re
import shutil
import threading
import time
import warnings
from abc import ABCMeta, abstractmethod
from pickle import PicklingError

from . import numpy_pickle
from .backports import concurrency_safe_rename
from .disk import memstr_to_bytes, mkdirp, rm_subdirs
from .logger import format_time

CacheItemInfo = collections.namedtuple("CacheItemInfo", "path size last_access")


class CacheWarning(Warning):
    """Warning to capture dump failures except for PicklingError."""

    pass


def concurrency_safe_write(object_to_write, filename, write_func):
    """Writes an object into a unique file in a concurrency-safe way."""
    thread_id = id(threading.current_thread())
    temporary_filename = "{}.thread-{}-pid-{}".format(filename, thread_id, os.getpid())
    write_func(object_to_write, temporary_filename)

    return temporary_filename


class StoreBackendBase(metaclass=ABCMeta):
    """Helper Abstract Base Class which defines all methods that
    a StorageBackend must implement."""

    location = None

    @abstractmethod
    def _open_item(self, f, mode):
        """Opens an item on the store and return a file-like object.

        This method is private and only used by the StoreBackendMixin object.

        Parameters
        ----------
        f: a file-like object
            The file-like object where an item is stored and retrieved
        mode: string, optional
            the mode in which the file-like object is opened allowed valued are
            'rb', 'wb'

        Returns
        -------
        a file-like object
        """

    @abstractmethod
    def _item_exists(self, location):
        """Checks if an item location exists in the store.

        This method is private and only used by the StoreBackendMixin object.

        Parameters
        ----------
        location: string
            The location of an item. On a filesystem, this corresponds to the
            absolute path, including the filename, of a file.

        Returns
        -------
        True if the item exists, False otherwise
        """

    @abstractmethod
    def _move_item(self, src, dst):
        """Moves an item from src to dst in the store.

        This method is private and only used by the StoreBackendMixin object.

        Parameters
        ----------
        src: string
            The source location of an item
        dst: string
            The destination location of an item
        """

    @abstractmethod
    def create_location(self, location):
        """Creates a location on the store.

        Parameters
        ----------
        location: string
            The location in the store. On a filesystem, this corresponds to a
            directory.
        """

    @abstractmethod
    def clear_location(self, location):
        """Clears a location on the store.

        Parameters
        ----------
        location: string
            The location in the store. On a filesystem, this corresponds to a
            directory or a filename absolute path
        """

    @abstractmethod
    def get_items(self):
        """Returns the whole list of items available in the store.

        Returns
        -------
        The list of items identified by their ids (e.g filename in a
        filesystem).
        """

    @abstractmethod
    def configure(self, location, verbose=0, backend_options=dict()):
        """Configures the store.

        Parameters
        ----------
        location: string
            The base location used by the store. On a filesystem, this
            corresponds to a directory.
        verbose: int
            The level of verbosity of the store
        backend_options: dict
            Contains a dictionary of named parameters used to configure the
            store backend.
        """


class StoreBackendMixin(object):
    """Class providing all logic for managing the store in a generic way.

    The StoreBackend subclass has to implement 3 methods: create_location,
    clear_location and configure. The StoreBackend also has to provide
    a private _open_item, _item_exists and _move_item methods. The _open_item
    method has to have the same signature as the builtin open and return a
    file-like object.
    """

    def load_item(self, call_id, verbose=1, timestamp=None, metadata=None):
        """Load an item from the store given its id as a list of str."""
        full_path = os.path.join(self.location, *call_id)

        if verbose > 1:
            ts_string = (
                "{: <16}".format(format_time(time.time() - timestamp))
                if timestamp is not None
                else ""
            )
            signature = os.path.basename(call_id[0])
            if metadata is not None and "input_args" in metadata:
                kwargs = ", ".join(
                    "{}={}".format(*item) for item in metadata["input_args"].items()
                )
                signature += "({})".format(kwargs)
            msg = "[Memory]{}: Loading {}".format(ts_string, signature)
            if verbose < 10:
                print("{0}...".format(msg))
            else:
                print("{0} from {1}".format(msg, full_path))

        mmap_mode = None if not hasattr(self, "mmap_mode") else self.mmap_mode

        filename = os.path.join(full_path, "output.pkl")
        if not self._item_exists(filename):
            raise KeyError(
                "Non-existing item (may have been "
                "cleared).\nFile %s does not exist" % filename
            )

        # file-like object cannot be used when mmap_mode is set
        if mmap_mode is None:
            with self._open_item(filename, "rb") as f:
                item = numpy_pickle.load(f)
        else:
            item = numpy_pickle.load(filename, mmap_mode=mmap_mode)
        return item

    def dump_item(self, call_id, item, verbose=1):
        """Dump an item in the store at the id given as a list of str."""
        try:
            item_path = os.path.join(self.location, *call_id)
            if not self._item_exists(item_path):
                self.create_location(item_path)
            filename = os.path.join(item_path, "output.pkl")
            if verbose > 10:
                print("Persisting in %s" % item_path)

            def write_func(to_write, dest_filename):
                with self._open_item(dest_filename, "wb") as f:
                    try:
                        numpy_pickle.dump(to_write, f, compress=self.compress)
                    except PicklingError as e:
                        # TODO(1.5) turn into error
                        warnings.warn(
                            "Unable to cache to disk: failed to pickle "
                            "output. In version 1.5 this will raise an "
                            f"exception. Exception: {e}.",
                            FutureWarning,
                        )

            self._concurrency_safe_write(item, filename, write_func)
        except Exception as e:  # noqa: E722
            warnings.warn(
                "Unable to cache to disk. Possibly a race condition in the "
                f"creation of the directory. Exception: {e}.",
                CacheWarning,
            )

    def clear_item(self, call_id):
        """Clear the item at the id, given as a list of str."""
        item_path = os.path.join(self.location, *call_id)
        if self._item_exists(item_path):
            self.clear_location(item_path)

    def contains_item(self, call_id):
        """Check if there is an item at the id, given as a list of str."""
        item_path = os.path.join(self.location, *call_id)
        filename = os.path.join(item_path, "output.pkl")

        return self._item_exists(filename)

    def get_item_info(self, call_id):
        """Return information about item."""
        return {"location": os.path.join(self.location, *call_id)}

    def get_metadata(self, call_id):
        """Return actual metadata of an item."""
        try:
            item_path = os.path.join(self.location, *call_id)
            filename = os.path.join(item_path, "metadata.json")
            with self._open_item(filename, "rb") as f:
                return json.loads(f.read().decode("utf-8"))
        except:  # noqa: E722
            return {}

    def store_metadata(self, call_id, metadata):
        """Store metadata of a computation."""
        try:
            item_path = os.path.join(self.location, *call_id)
            self.create_location(item_path)
            filename = os.path.join(item_path, "metadata.json")

            def write_func(to_write, dest_filename):
                with self._open_item(dest_filename, "wb") as f:
                    f.write(json.dumps(to_write).encode("utf-8"))

            self._concurrency_safe_write(metadata, filename, write_func)
        except:  # noqa: E722
            pass

    def contains_path(self, call_id):
        """Check cached function is available in store."""
        func_path = os.path.join(self.location, *call_id)
        return self.object_exists(func_path)

    def clear_path(self, call_id):
        """Clear all items with a common path in the store."""
        func_path = os.path.join(self.location, *call_id)
        if self._item_exists(func_path):
            self.clear_location(func_path)

    def store_cached_func_code(self, call_id, func_code=None):
        """Store the code of the cached function."""
        func_path = os.path.join(self.location, *call_id)
        if not self._item_exists(func_path):
            self.create_location(func_path)

        if func_code is not None:
            filename = os.path.join(func_path, "func_code.py")
            with self._open_item(filename, "wb") as f:
                f.write(func_code.encode("utf-8"))

    def get_cached_func_code(self, call_id):
        """Store the code of the cached function."""
        filename = os.path.join(self.location, *call_id, "func_code.py")
        try:
            with self._open_item(filename, "rb") as f:
                return f.read().decode("utf-8")
        except:  # noqa: E722
            raise

    def get_cached_func_info(self, call_id):
        """Return information related to the cached function if it exists."""
        return {"location": os.path.join(self.location, *call_id)}

    def clear(self):
        """Clear the whole store content."""
        self.clear_location(self.location)

    def enforce_store_limits(self, bytes_limit, items_limit=None, age_limit=None):
        """
        Remove the store's oldest files to enforce item, byte, and age limits.
        """
        items_to_delete = self._get_items_to_delete(bytes_limit, items_limit, age_limit)

        for item in items_to_delete:
            if self.verbose > 10:
                print("Deleting item {0}".format(item))
            try:
                self.clear_location(item.path)
            except OSError:
                # Even with ignore_errors=True shutil.rmtree can raise OSError
                # with:
                # [Errno 116] Stale file handle if another process has deleted
                # the folder already.
                pass

    def _get_items_to_delete(self, bytes_limit, items_limit=None, age_limit=None):
        """
        Get items to delete to keep the store under size, file, & age limits.
        """
        if isinstance(bytes_limit, str):
            bytes_limit = memstr_to_bytes(bytes_limit)

        items = self.get_items()
        if not items:
            return []

        size = sum(item.size for item in items)

        if bytes_limit is not None:
            to_delete_size = size - bytes_limit
        else:
            to_delete_size = 0

        if items_limit is not None:
            to_delete_items = len(items) - items_limit
        else:
            to_delete_items = 0

        if age_limit is not None:
            older_item = min(item.last_access for item in items)
            if age_limit.total_seconds() < 0:
                raise ValueError("age_limit has to be a positive timedelta")
            deadline = datetime.datetime.now() - age_limit
        else:
            deadline = None

        if (
            to_delete_size <= 0
            and to_delete_items <= 0
            and (deadline is None or older_item > deadline)
        ):
            return []

        # We want to delete first the cache items that were accessed a
        # long time ago
        items.sort(key=operator.attrgetter("last_access"))

        items_to_delete = []
        size_so_far = 0
        items_so_far = 0

        for item in items:
            if (
                (size_so_far >= to_delete_size)
                and items_so_far >= to_delete_items
                and (deadline is None or deadline < item.last_access)
            ):
                break

            items_to_delete.append(item)
            size_so_far += item.size
            items_so_far += 1

        return items_to_delete

    def _concurrency_safe_write(self, to_write, filename, write_func):
        """Writes an object into a file in a concurrency-safe way."""
        temporary_filename = concurrency_safe_write(to_write, filename, write_func)
        self._move_item(temporary_filename, filename)

    def __repr__(self):
        """Printable representation of the store location."""
        return '{class_name}(location="{location}")'.format(
            class_name=self.__class__.__name__, location=self.location
        )


class FileSystemStoreBackend(StoreBackendBase, StoreBackendMixin):
    """A StoreBackend used with local or network file systems."""

    _open_item = staticmethod(open)
    _item_exists = staticmethod(os.path.exists)
    _move_item = staticmethod(concurrency_safe_rename)

    def clear_location(self, location):
        """Delete location on store."""
        if location == self.location:
            rm_subdirs(location)
        else:
            shutil.rmtree(location, ignore_errors=True)

    def create_location(self, location):
        """Create object location on store"""
        mkdirp(location)

    def get_items(self):
        """Returns the whole list of items available in the store."""
        items = []

        for dirpath, _, filenames in os.walk(self.location):
            is_cache_hash_dir = re.match("[a-f0-9]{32}", os.path.basename(dirpath))

            if is_cache_hash_dir:
                output_filename = os.path.join(dirpath, "output.pkl")
                try:
                    last_access = os.path.getatime(output_filename)
                except OSError:
                    try:
                        last_access = os.path.getatime(dirpath)
                    except OSError:
                        # The directory has already been deleted
                        continue

                last_access = datetime.datetime.fromtimestamp(last_access)
                try:
                    full_filenames = [os.path.join(dirpath, fn) for fn in filenames]
                    dirsize = sum(os.path.getsize(fn) for fn in full_filenames)
                except OSError:
                    # Either output_filename or one of the files in
                    # dirpath does not exist any more. We assume this
                    # directory is being cleaned by another process already
                    continue

                items.append(CacheItemInfo(dirpath, dirsize, last_access))

        return items

    def configure(self, location, verbose=1, backend_options=None):
        """Configure the store backend.

        For this backend, valid store options are 'compress' and 'mmap_mode'
        """
        if backend_options is None:
            backend_options = {}

        # setup location directory
        self.location = location
        if not os.path.exists(self.location):
            mkdirp(self.location)

        # Automatically add `.gitignore` file to the cache folder.
        # XXX: the condition is necessary because in `Memory.__init__`, the user
        # passed `location` param is modified to be either `{location}` or
        # `{location}/joblib` depending on input type (`pathlib.Path` vs `str`).
        # The proper resolution of this inconsistency is tracked in:
        # https://github.com/joblib/joblib/issues/1684
        cache_directory = (
            os.path.dirname(location)
            if os.path.dirname(location) and os.path.basename(location) == "joblib"
            else location
        )
        with open(os.path.join(cache_directory, ".gitignore"), "w") as file:
            file.write("# Created by joblib automatically.\n")
            file.write("*\n")

        # item can be stored compressed for faster I/O
        self.compress = backend_options.get("compress", False)

        # FileSystemStoreBackend can be used with mmap_mode options under
        # certain conditions.
        mmap_mode = backend_options.get("mmap_mode")
        if self.compress and mmap_mode is not None:
            warnings.warn(
                "Compressed items cannot be memmapped in a "
                "filesystem store. Option will be ignored.",
                stacklevel=2,
            )

        self.mmap_mode = mmap_mode
        self.verbose = verbose