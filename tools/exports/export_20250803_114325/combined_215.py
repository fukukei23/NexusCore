
# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\extension.py ===
"""distutils.extension

Provides the Extension class, used to describe C/C++ extension
modules in setup scripts."""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterable

# This class is really only used by the "build_ext" command, so it might
# make sense to put it in distutils.command.build_ext.  However, that
# module is already big enough, and I want to make this class a bit more
# complex to simplify some common cases ("foo" module in "foo.c") and do
# better error-checking ("foo.c" actually exists).
#
# Also, putting this in build_ext.py means every setup script would have to
# import that large-ish module (indirectly, through distutils.core) in
# order to do anything.


class Extension:
    """Just a collection of attributes that describes an extension
    module and everything needed to build it (hopefully in a portable
    way, but there are hooks that let you be as unportable as you need).

    Instance attributes:
      name : string
        the full name of the extension, including any packages -- ie.
        *not* a filename or pathname, but Python dotted name
      sources : Iterable[string | os.PathLike]
        iterable of source filenames (except strings, which could be misinterpreted
        as a single filename), relative to the distribution root (where the setup
        script lives), in Unix form (slash-separated) for portability. Can be any
        non-string iterable (list, tuple, set, etc.) containing strings or
        PathLike objects. Source files may be C, C++, SWIG (.i), platform-specific
        resource files, or whatever else is recognized by the "build_ext" command
        as source for a Python extension.
      include_dirs : [string]
        list of directories to search for C/C++ header files (in Unix
        form for portability)
      define_macros : [(name : string, value : string|None)]
        list of macros to define; each macro is defined using a 2-tuple,
        where 'value' is either the string to define it to or None to
        define it without a particular value (equivalent of "#define
        FOO" in source or -DFOO on Unix C compiler command line)
      undef_macros : [string]
        list of macros to undefine explicitly
      library_dirs : [string]
        list of directories to search for C/C++ libraries at link time
      libraries : [string]
        list of library names (not filenames or paths) to link against
      runtime_library_dirs : [string]
        list of directories to search for C/C++ libraries at run time
        (for shared extensions, this is when the extension is loaded)
      extra_objects : [string]
        list of extra files to link with (eg. object files not implied
        by 'sources', static library that must be explicitly specified,
        binary resource files, etc.)
      extra_compile_args : [string]
        any extra platform- and compiler-specific information to use
        when compiling the source files in 'sources'.  For platforms and
        compilers where "command line" makes sense, this is typically a
        list of command-line arguments, but for other platforms it could
        be anything.
      extra_link_args : [string]
        any extra platform- and compiler-specific information to use
        when linking object files together to create the extension (or
        to create a new static Python interpreter).  Similar
        interpretation as for 'extra_compile_args'.
      export_symbols : [string]
        list of symbols to be exported from a shared extension.  Not
        used on all platforms, and not generally necessary for Python
        extensions, which typically export exactly one symbol: "init" +
        extension_name.
      swig_opts : [string]
        any extra options to pass to SWIG if a source file has the .i
        extension.
      depends : [string]
        list of files that the extension depends on
      language : string
        extension language (i.e. "c", "c++", "objc"). Will be detected
        from the source extensions if not provided.
      optional : boolean
        specifies that a build failure in the extension should not abort the
        build process, but simply not install the failing extension.
    """

    # When adding arguments to this constructor, be sure to update
    # setup_keywords in core.py.
    def __init__(
        self,
        name: str,
        sources: Iterable[str | os.PathLike[str]],
        include_dirs: list[str] | None = None,
        define_macros: list[tuple[str, str | None]] | None = None,
        undef_macros: list[str] | None = None,
        library_dirs: list[str] | None = None,
        libraries: list[str] | None = None,
        runtime_library_dirs: list[str] | None = None,
        extra_objects: list[str] | None = None,
        extra_compile_args: list[str] | None = None,
        extra_link_args: list[str] | None = None,
        export_symbols: list[str] | None = None,
        swig_opts: list[str] | None = None,
        depends: list[str] | None = None,
        language: str | None = None,
        optional: bool | None = None,
        **kw,  # To catch unknown keywords
    ):
        if not isinstance(name, str):
            raise TypeError("'name' must be a string")

        # handle the string case first; since strings are iterable, disallow them
        if isinstance(sources, str):
            raise TypeError(
                "'sources' must be an iterable of strings or PathLike objects, not a string"
            )

        # now we check if it's iterable and contains valid types
        try:
            self.sources = list(map(os.fspath, sources))
        except TypeError:
            raise TypeError(
                "'sources' must be an iterable of strings or PathLike objects"
            )

        self.name = name
        self.include_dirs = include_dirs or []
        self.define_macros = define_macros or []
        self.undef_macros = undef_macros or []
        self.library_dirs = library_dirs or []
        self.libraries = libraries or []
        self.runtime_library_dirs = runtime_library_dirs or []
        self.extra_objects = extra_objects or []
        self.extra_compile_args = extra_compile_args or []
        self.extra_link_args = extra_link_args or []
        self.export_symbols = export_symbols or []
        self.swig_opts = swig_opts or []
        self.depends = depends or []
        self.language = language
        self.optional = optional

        # If there are unknown keyword options, warn about them
        if len(kw) > 0:
            options = [repr(option) for option in kw]
            options = ', '.join(sorted(options))
            msg = f"Unknown Extension options: {options}"
            warnings.warn(msg)

    def __repr__(self):
        return f'<{self.__class__.__module__}.{self.__class__.__qualname__}({self.name!r}) at {id(self):#x}>'


def read_setup_file(filename):  # noqa: C901
    """Reads a Setup file and returns Extension instances."""
    from distutils.sysconfig import _variable_rx, expand_makefile_vars, parse_makefile
    from distutils.text_file import TextFile
    from distutils.util import split_quoted

    # First pass over the file to gather "VAR = VALUE" assignments.
    vars = parse_makefile(filename)

    # Second pass to gobble up the real content: lines of the form
    #   <module> ... [<sourcefile> ...] [<cpparg> ...] [<library> ...]
    file = TextFile(
        filename,
        strip_comments=True,
        skip_blanks=True,
        join_lines=True,
        lstrip_ws=True,
        rstrip_ws=True,
    )
    try:
        extensions = []

        while True:
            line = file.readline()
            if line is None:  # eof
                break
            if _variable_rx.match(line):  # VAR=VALUE, handled in first pass
                continue

            if line[0] == line[-1] == "*":
                file.warn(f"'{line}' lines not handled yet")
                continue

            line = expand_makefile_vars(line, vars)
            words = split_quoted(line)

            # NB. this parses a slightly different syntax than the old
            # makesetup script: here, there must be exactly one extension per
            # line, and it must be the first word of the line.  I have no idea
            # why the old syntax supported multiple extensions per line, as
            # they all wind up being the same.

            module = words[0]
            ext = Extension(module, [])
            append_next_word = None

            for word in words[1:]:
                if append_next_word is not None:
                    append_next_word.append(word)
                    append_next_word = None
                    continue

                suffix = os.path.splitext(word)[1]
                switch = word[0:2]
                value = word[2:]

                if suffix in (".c", ".cc", ".cpp", ".cxx", ".c++", ".m", ".mm"):
                    # hmm, should we do something about C vs. C++ sources?
                    # or leave it up to the CCompiler implementation to
                    # worry about?
                    ext.sources.append(word)
                elif switch == "-I":
                    ext.include_dirs.append(value)
                elif switch == "-D":
                    equals = value.find("=")
                    if equals == -1:  # bare "-DFOO" -- no value
                        ext.define_macros.append((value, None))
                    else:  # "-DFOO=blah"
                        ext.define_macros.append((value[0:equals], value[equals + 2 :]))
                elif switch == "-U":
                    ext.undef_macros.append(value)
                elif switch == "-C":  # only here 'cause makesetup has it!
                    ext.extra_compile_args.append(word)
                elif switch == "-l":
                    ext.libraries.append(value)
                elif switch == "-L":
                    ext.library_dirs.append(value)
                elif switch == "-R":
                    ext.runtime_library_dirs.append(value)
                elif word == "-rpath":
                    append_next_word = ext.runtime_library_dirs
                elif word == "-Xlinker":
                    append_next_word = ext.extra_link_args
                elif word == "-Xcompiler":
                    append_next_word = ext.extra_compile_args
                elif switch == "-u":
                    ext.extra_link_args.append(word)
                    if not value:
                        append_next_word = ext.extra_link_args
                elif suffix in (".a", ".so", ".sl", ".o", ".dylib"):
                    # NB. a really faithful emulation of makesetup would
                    # append a .o file to extra_objects only if it
                    # had a slash in it; otherwise, it would s/.o/.c/
                    # and append it to sources.  Hmmmm.
                    ext.extra_objects.append(word)
                else:
                    file.warn(f"unrecognized argument '{word}'")

            extensions.append(ext)
    finally:
        file.close()

    return extensions

# === NexusCore/openenv\Lib\site-packages\urllib3\util\request.py ===
from __future__ import annotations

import io
import typing
from base64 import b64encode
from enum import Enum

from ..exceptions import UnrewindableBodyError
from .util import to_bytes

if typing.TYPE_CHECKING:
    from typing import Final

# Pass as a value within ``headers`` to skip
# emitting some HTTP headers that are added automatically.
# The only headers that are supported are ``Accept-Encoding``,
# ``Host``, and ``User-Agent``.
SKIP_HEADER = "@@@SKIP_HEADER@@@"
SKIPPABLE_HEADERS = frozenset(["accept-encoding", "host", "user-agent"])

ACCEPT_ENCODING = "gzip,deflate"
try:
    try:
        import brotlicffi as _unused_module_brotli  # type: ignore[import-not-found] # noqa: F401
    except ImportError:
        import brotli as _unused_module_brotli  # type: ignore[import-not-found] # noqa: F401
except ImportError:
    pass
else:
    ACCEPT_ENCODING += ",br"
try:
    import zstandard as _unused_module_zstd  # noqa: F401
except ImportError:
    pass
else:
    ACCEPT_ENCODING += ",zstd"


class _TYPE_FAILEDTELL(Enum):
    token = 0


_FAILEDTELL: Final[_TYPE_FAILEDTELL] = _TYPE_FAILEDTELL.token

_TYPE_BODY_POSITION = typing.Union[int, _TYPE_FAILEDTELL]

# When sending a request with these methods we aren't expecting
# a body so don't need to set an explicit 'Content-Length: 0'
# The reason we do this in the negative instead of tracking methods
# which 'should' have a body is because unknown methods should be
# treated as if they were 'POST' which *does* expect a body.
_METHODS_NOT_EXPECTING_BODY = {"GET", "HEAD", "DELETE", "TRACE", "OPTIONS", "CONNECT"}


def make_headers(
    keep_alive: bool | None = None,
    accept_encoding: bool | list[str] | str | None = None,
    user_agent: str | None = None,
    basic_auth: str | None = None,
    proxy_basic_auth: str | None = None,
    disable_cache: bool | None = None,
) -> dict[str, str]:
    """
    Shortcuts for generating request headers.

    :param keep_alive:
        If ``True``, adds 'connection: keep-alive' header.

    :param accept_encoding:
        Can be a boolean, list, or string.
        ``True`` translates to 'gzip,deflate'.  If the dependencies for
        Brotli (either the ``brotli`` or ``brotlicffi`` package) and/or Zstandard
        (the ``zstandard`` package) algorithms are installed, then their encodings are
        included in the string ('br' and 'zstd', respectively).
        List will get joined by comma.
        String will be used as provided.

    :param user_agent:
        String representing the user-agent you want, such as
        "python-urllib3/0.6"

    :param basic_auth:
        Colon-separated username:password string for 'authorization: basic ...'
        auth header.

    :param proxy_basic_auth:
        Colon-separated username:password string for 'proxy-authorization: basic ...'
        auth header.

    :param disable_cache:
        If ``True``, adds 'cache-control: no-cache' header.

    Example:

    .. code-block:: python

        import urllib3

        print(urllib3.util.make_headers(keep_alive=True, user_agent="Batman/1.0"))
        # {'connection': 'keep-alive', 'user-agent': 'Batman/1.0'}
        print(urllib3.util.make_headers(accept_encoding=True))
        # {'accept-encoding': 'gzip,deflate'}
    """
    headers: dict[str, str] = {}
    if accept_encoding:
        if isinstance(accept_encoding, str):
            pass
        elif isinstance(accept_encoding, list):
            accept_encoding = ",".join(accept_encoding)
        else:
            accept_encoding = ACCEPT_ENCODING
        headers["accept-encoding"] = accept_encoding

    if user_agent:
        headers["user-agent"] = user_agent

    if keep_alive:
        headers["connection"] = "keep-alive"

    if basic_auth:
        headers["authorization"] = (
            f"Basic {b64encode(basic_auth.encode('latin-1')).decode()}"
        )

    if proxy_basic_auth:
        headers["proxy-authorization"] = (
            f"Basic {b64encode(proxy_basic_auth.encode('latin-1')).decode()}"
        )

    if disable_cache:
        headers["cache-control"] = "no-cache"

    return headers


def set_file_position(
    body: typing.Any, pos: _TYPE_BODY_POSITION | None
) -> _TYPE_BODY_POSITION | None:
    """
    If a position is provided, move file to that point.
    Otherwise, we'll attempt to record a position for future use.
    """
    if pos is not None:
        rewind_body(body, pos)
    elif getattr(body, "tell", None) is not None:
        try:
            pos = body.tell()
        except OSError:
            # This differentiates from None, allowing us to catch
            # a failed `tell()` later when trying to rewind the body.
            pos = _FAILEDTELL

    return pos


def rewind_body(body: typing.IO[typing.AnyStr], body_pos: _TYPE_BODY_POSITION) -> None:
    """
    Attempt to rewind body to a certain position.
    Primarily used for request redirects and retries.

    :param body:
        File-like object that supports seek.

    :param int pos:
        Position to seek to in file.
    """
    body_seek = getattr(body, "seek", None)
    if body_seek is not None and isinstance(body_pos, int):
        try:
            body_seek(body_pos)
        except OSError as e:
            raise UnrewindableBodyError(
                "An error occurred when rewinding request body for redirect/retry."
            ) from e
    elif body_pos is _FAILEDTELL:
        raise UnrewindableBodyError(
            "Unable to record file position for rewinding "
            "request body during a redirect/retry."
        )
    else:
        raise ValueError(
            f"body_pos must be of type integer, instead it was {type(body_pos)}."
        )


class ChunksAndContentLength(typing.NamedTuple):
    chunks: typing.Iterable[bytes] | None
    content_length: int | None


def body_to_chunks(
    body: typing.Any | None, method: str, blocksize: int
) -> ChunksAndContentLength:
    """Takes the HTTP request method, body, and blocksize and
    transforms them into an iterable of chunks to pass to
    socket.sendall() and an optional 'Content-Length' header.

    A 'Content-Length' of 'None' indicates the length of the body
    can't be determined so should use 'Transfer-Encoding: chunked'
    for framing instead.
    """

    chunks: typing.Iterable[bytes] | None
    content_length: int | None

    # No body, we need to make a recommendation on 'Content-Length'
    # based on whether that request method is expected to have
    # a body or not.
    if body is None:
        chunks = None
        if method.upper() not in _METHODS_NOT_EXPECTING_BODY:
            content_length = 0
        else:
            content_length = None

    # Bytes or strings become bytes
    elif isinstance(body, (str, bytes)):
        chunks = (to_bytes(body),)
        content_length = len(chunks[0])

    # File-like object, TODO: use seek() and tell() for length?
    elif hasattr(body, "read"):

        def chunk_readable() -> typing.Iterable[bytes]:
            nonlocal body, blocksize
            encode = isinstance(body, io.TextIOBase)
            while True:
                datablock = body.read(blocksize)
                if not datablock:
                    break
                if encode:
                    datablock = datablock.encode("utf-8")
                yield datablock

        chunks = chunk_readable()
        content_length = None

    # Otherwise we need to start checking via duck-typing.
    else:
        try:
            # Check if the body implements the buffer API.
            mv = memoryview(body)
        except TypeError:
            try:
                # Check if the body is an iterable
                chunks = iter(body)
                content_length = None
            except TypeError:
                raise TypeError(
                    f"'body' must be a bytes-like object, file-like "
                    f"object, or iterable. Instead was {body!r}"
                ) from None
        else:
            # Since it implements the buffer API can be passed directly to socket.sendall()
            chunks = (body,)
            content_length = mv.nbytes

    return ChunksAndContentLength(chunks=chunks, content_length=content_length)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\tree.py ===
from typing import Iterator, List, Optional, Tuple

from ._loop import loop_first, loop_last
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleStack, StyleType
from .styled import Styled

GuideType = Tuple[str, str, str, str]


class Tree(JupyterMixin):
    """A renderable for a tree structure.

    Attributes:
        ASCII_GUIDES (GuideType): Guide lines used when Console.ascii_only is True.
        TREE_GUIDES (List[GuideType, GuideType, GuideType]): Default guide lines.

    Args:
        label (RenderableType): The renderable or str for the tree label.
        style (StyleType, optional): Style of this tree. Defaults to "tree".
        guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
        expanded (bool, optional): Also display children. Defaults to True.
        highlight (bool, optional): Highlight renderable (if str). Defaults to False.
        hide_root (bool, optional): Hide the root node. Defaults to False.
    """

    ASCII_GUIDES = ("    ", "|   ", "+-- ", "`-- ")
    TREE_GUIDES = [
        ("    ", "│   ", "├── ", "└── "),
        ("    ", "┃   ", "┣━━ ", "┗━━ "),
        ("    ", "║   ", "╠══ ", "╚══ "),
    ]

    def __init__(
        self,
        label: RenderableType,
        *,
        style: StyleType = "tree",
        guide_style: StyleType = "tree.line",
        expanded: bool = True,
        highlight: bool = False,
        hide_root: bool = False,
    ) -> None:
        self.label = label
        self.style = style
        self.guide_style = guide_style
        self.children: List[Tree] = []
        self.expanded = expanded
        self.highlight = highlight
        self.hide_root = hide_root

    def add(
        self,
        label: RenderableType,
        *,
        style: Optional[StyleType] = None,
        guide_style: Optional[StyleType] = None,
        expanded: bool = True,
        highlight: Optional[bool] = False,
    ) -> "Tree":
        """Add a child tree.

        Args:
            label (RenderableType): The renderable or str for the tree label.
            style (StyleType, optional): Style of this tree. Defaults to "tree".
            guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
            expanded (bool, optional): Also display children. Defaults to True.
            highlight (Optional[bool], optional): Highlight renderable (if str). Defaults to False.

        Returns:
            Tree: A new child Tree, which may be further modified.
        """
        node = Tree(
            label,
            style=self.style if style is None else style,
            guide_style=self.guide_style if guide_style is None else guide_style,
            expanded=expanded,
            highlight=self.highlight if highlight is None else highlight,
        )
        self.children.append(node)
        return node

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        stack: List[Iterator[Tuple[bool, Tree]]] = []
        pop = stack.pop
        push = stack.append
        new_line = Segment.line()

        get_style = console.get_style
        null_style = Style.null()
        guide_style = get_style(self.guide_style, default="") or null_style
        SPACE, CONTINUE, FORK, END = range(4)

        _Segment = Segment

        def make_guide(index: int, style: Style) -> Segment:
            """Make a Segment for a level of the guide lines."""
            if options.ascii_only:
                line = self.ASCII_GUIDES[index]
            else:
                guide = 1 if style.bold else (2 if style.underline2 else 0)
                line = self.TREE_GUIDES[0 if options.legacy_windows else guide][index]
            return _Segment(line, style)

        levels: List[Segment] = [make_guide(CONTINUE, guide_style)]
        push(iter(loop_last([self])))

        guide_style_stack = StyleStack(get_style(self.guide_style))
        style_stack = StyleStack(get_style(self.style))
        remove_guide_styles = Style(bold=False, underline2=False)

        depth = 0

        while stack:
            stack_node = pop()
            try:
                last, node = next(stack_node)
            except StopIteration:
                levels.pop()
                if levels:
                    guide_style = levels[-1].style or null_style
                    levels[-1] = make_guide(FORK, guide_style)
                    guide_style_stack.pop()
                    style_stack.pop()
                continue
            push(stack_node)
            if last:
                levels[-1] = make_guide(END, levels[-1].style or null_style)

            guide_style = guide_style_stack.current + get_style(node.guide_style)
            style = style_stack.current + get_style(node.style)
            prefix = levels[(2 if self.hide_root else 1) :]
            renderable_lines = console.render_lines(
                Styled(node.label, style),
                options.update(
                    width=options.max_width
                    - sum(level.cell_length for level in prefix),
                    highlight=self.highlight,
                    height=None,
                ),
                pad=options.justify is not None,
            )

            if not (depth == 0 and self.hide_root):
                for first, line in loop_first(renderable_lines):
                    if prefix:
                        yield from _Segment.apply_style(
                            prefix,
                            style.background_style,
                            post_style=remove_guide_styles,
                        )
                    yield from line
                    yield new_line
                    if first and prefix:
                        prefix[-1] = make_guide(
                            SPACE if last else CONTINUE, prefix[-1].style or null_style
                        )

            if node.expanded and node.children:
                levels[-1] = make_guide(
                    SPACE if last else CONTINUE, levels[-1].style or null_style
                )
                levels.append(
                    make_guide(END if len(node.children) == 1 else FORK, guide_style)
                )
                style_stack.push(get_style(node.style))
                guide_style_stack.push(get_style(node.guide_style))
                push(iter(loop_last(node.children)))
                depth += 1

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        stack: List[Iterator[Tree]] = [iter([self])]
        pop = stack.pop
        push = stack.append
        minimum = 0
        maximum = 0
        measure = Measurement.get
        level = 0
        while stack:
            iter_tree = pop()
            try:
                tree = next(iter_tree)
            except StopIteration:
                level -= 1
                continue
            push(iter_tree)
            min_measure, max_measure = measure(console, options, tree.label)
            indent = level * 4
            minimum = max(min_measure + indent, minimum)
            maximum = max(max_measure + indent, maximum)
            if tree.expanded and tree.children:
                push(iter(tree.children))
                level += 1
        return Measurement(minimum, maximum)


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Group
    from pip._vendor.rich.markdown import Markdown
    from pip._vendor.rich.panel import Panel
    from pip._vendor.rich.syntax import Syntax
    from pip._vendor.rich.table import Table

    table = Table(row_styles=["", "dim"])

    table.add_column("Released", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Box Office", justify="right", style="green")

    table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
    table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
    table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
    table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

    code = """\
class Segment(NamedTuple):
    text: str = ""
    style: Optional[Style] = None
    is_control: bool = False
"""
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)

    markdown = Markdown(
        """\
### example.md
> Hello, World!
>
> Markdown _all_ the things
"""
    )

    root = Tree("🌲 [b green]Rich Tree", highlight=True, hide_root=True)

    node = root.add(":file_folder: Renderables", guide_style="red")
    simple_node = node.add(":file_folder: [bold yellow]Atomic", guide_style="uu green")
    simple_node.add(Group("📄 Syntax", syntax))
    simple_node.add(Group("📄 Markdown", Panel(markdown, border_style="green")))

    containers_node = node.add(
        ":file_folder: [bold magenta]Containers", guide_style="bold magenta"
    )
    containers_node.expanded = True
    panel = Panel.fit("Just a panel", border_style="red")
    containers_node.add(Group("📄 Panels", panel))

    containers_node.add(Group("📄 [b magenta]Table", table))

    console = Console()

    console.print(root)

# === NexusCore/openenv\Lib\site-packages\PIL\FpxImagePlugin.py ===
#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library.
# $Id$
#
# FlashPix support for PIL
#
# History:
# 97-01-25 fl   Created (reads uncompressed RGB images only)
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1997.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import olefile

from . import Image, ImageFile
from ._binary import i32le as i32

# we map from colour field tuples to (mode, rawmode) descriptors
MODES = {
    # opacity
    (0x00007FFE,): ("A", "L"),
    # monochrome
    (0x00010000,): ("L", "L"),
    (0x00018000, 0x00017FFE): ("RGBA", "LA"),
    # photo YCC
    (0x00020000, 0x00020001, 0x00020002): ("RGB", "YCC;P"),
    (0x00028000, 0x00028001, 0x00028002, 0x00027FFE): ("RGBA", "YCCA;P"),
    # standard RGB (NIFRGB)
    (0x00030000, 0x00030001, 0x00030002): ("RGB", "RGB"),
    (0x00038000, 0x00038001, 0x00038002, 0x00037FFE): ("RGBA", "RGBA"),
}


#
# --------------------------------------------------------------------


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(olefile.MAGIC)


##
# Image plugin for the FlashPix images.


class FpxImageFile(ImageFile.ImageFile):
    format = "FPX"
    format_description = "FlashPix"

    def _open(self) -> None:
        #
        # read the OLE directory and see if this is a likely
        # to be a FlashPix file

        try:
            self.ole = olefile.OleFileIO(self.fp)
        except OSError as e:
            msg = "not an FPX file; invalid OLE file"
            raise SyntaxError(msg) from e

        root = self.ole.root
        if not root or root.clsid != "56616700-C154-11CE-8553-00AA00A1F95B":
            msg = "not an FPX file; bad root CLSID"
            raise SyntaxError(msg)

        self._open_index(1)

    def _open_index(self, index: int = 1) -> None:
        #
        # get the Image Contents Property Set

        prop = self.ole.getproperties(
            [f"Data Object Store {index:06d}", "\005Image Contents"]
        )

        # size (highest resolution)

        assert isinstance(prop[0x1000002], int)
        assert isinstance(prop[0x1000003], int)
        self._size = prop[0x1000002], prop[0x1000003]

        size = max(self.size)
        i = 1
        while size > 64:
            size = size // 2
            i += 1
        self.maxid = i - 1

        # mode.  instead of using a single field for this, flashpix
        # requires you to specify the mode for each channel in each
        # resolution subimage, and leaves it to the decoder to make
        # sure that they all match.  for now, we'll cheat and assume
        # that this is always the case.

        id = self.maxid << 16

        s = prop[0x2000002 | id]

        if not isinstance(s, bytes) or (bands := i32(s, 4)) > 4:
            msg = "Invalid number of bands"
            raise OSError(msg)

        # note: for now, we ignore the "uncalibrated" flag
        colors = tuple(i32(s, 8 + i * 4) & 0x7FFFFFFF for i in range(bands))

        self._mode, self.rawmode = MODES[colors]

        # load JPEG tables, if any
        self.jpeg = {}
        for i in range(256):
            id = 0x3000001 | (i << 16)
            if id in prop:
                self.jpeg[i] = prop[id]

        self._open_subimage(1, self.maxid)

    def _open_subimage(self, index: int = 1, subimage: int = 0) -> None:
        #
        # setup tile descriptors for a given subimage

        stream = [
            f"Data Object Store {index:06d}",
            f"Resolution {subimage:04d}",
            "Subimage 0000 Header",
        ]

        fp = self.ole.openstream(stream)

        # skip prefix
        fp.read(28)

        # header stream
        s = fp.read(36)

        size = i32(s, 4), i32(s, 8)
        # tilecount = i32(s, 12)
        tilesize = i32(s, 16), i32(s, 20)
        # channels = i32(s, 24)
        offset = i32(s, 28)
        length = i32(s, 32)

        if size != self.size:
            msg = "subimage mismatch"
            raise OSError(msg)

        # get tile descriptors
        fp.seek(28 + offset)
        s = fp.read(i32(s, 12) * length)

        x = y = 0
        xsize, ysize = size
        xtile, ytile = tilesize
        self.tile = []

        for i in range(0, len(s), length):
            x1 = min(xsize, x + xtile)
            y1 = min(ysize, y + ytile)

            compression = i32(s, i + 8)

            if compression == 0:
                self.tile.append(
                    ImageFile._Tile(
                        "raw",
                        (x, y, x1, y1),
                        i32(s, i) + 28,
                        self.rawmode,
                    )
                )

            elif compression == 1:
                # FIXME: the fill decoder is not implemented
                self.tile.append(
                    ImageFile._Tile(
                        "fill",
                        (x, y, x1, y1),
                        i32(s, i) + 28,
                        (self.rawmode, s[12:16]),
                    )
                )

            elif compression == 2:
                internal_color_conversion = s[14]
                jpeg_tables = s[15]
                rawmode = self.rawmode

                if internal_color_conversion:
                    # The image is stored as usual (usually YCbCr).
                    if rawmode == "RGBA":
                        # For "RGBA", data is stored as YCbCrA based on
                        # negative RGB. The following trick works around
                        # this problem :
                        jpegmode, rawmode = "YCbCrK", "CMYK"
                    else:
                        jpegmode = None  # let the decoder decide

                else:
                    # The image is stored as defined by rawmode
                    jpegmode = rawmode

                self.tile.append(
                    ImageFile._Tile(
                        "jpeg",
                        (x, y, x1, y1),
                        i32(s, i) + 28,
                        (rawmode, jpegmode),
                    )
                )

                # FIXME: jpeg tables are tile dependent; the prefix
                # data must be placed in the tile descriptor itself!

                if jpeg_tables:
                    self.tile_prefix = self.jpeg[jpeg_tables]

            else:
                msg = "unknown/invalid compression"
                raise OSError(msg)

            x = x + xtile
            if x >= xsize:
                x, y = 0, y + ytile
                if y >= ysize:
                    break  # isn't really required

        self.stream = stream
        self._fp = self.fp
        self.fp = None

    def load(self) -> Image.core.PixelAccess | None:
        if not self.fp:
            self.fp = self.ole.openstream(self.stream[:2] + ["Subimage 0000 Data"])

        return ImageFile.ImageFile.load(self)

    def close(self) -> None:
        self.ole.close()
        super().close()

    def __exit__(self, *args: object) -> None:
        self.ole.close()
        super().__exit__()


#
# --------------------------------------------------------------------


Image.register_open(FpxImageFile.format, FpxImageFile, _accept)

Image.register_extension(FpxImageFile.format, ".fpx")

# === NexusCore/openenv\Lib\site-packages\rich\tree.py ===
from typing import Iterator, List, Optional, Tuple

from ._loop import loop_first, loop_last
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleStack, StyleType
from .styled import Styled

GuideType = Tuple[str, str, str, str]


class Tree(JupyterMixin):
    """A renderable for a tree structure.

    Attributes:
        ASCII_GUIDES (GuideType): Guide lines used when Console.ascii_only is True.
        TREE_GUIDES (List[GuideType, GuideType, GuideType]): Default guide lines.

    Args:
        label (RenderableType): The renderable or str for the tree label.
        style (StyleType, optional): Style of this tree. Defaults to "tree".
        guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
        expanded (bool, optional): Also display children. Defaults to True.
        highlight (bool, optional): Highlight renderable (if str). Defaults to False.
        hide_root (bool, optional): Hide the root node. Defaults to False.
    """

    ASCII_GUIDES = ("    ", "|   ", "+-- ", "`-- ")
    TREE_GUIDES = [
        ("    ", "│   ", "├── ", "└── "),
        ("    ", "┃   ", "┣━━ ", "┗━━ "),
        ("    ", "║   ", "╠══ ", "╚══ "),
    ]

    def __init__(
        self,
        label: RenderableType,
        *,
        style: StyleType = "tree",
        guide_style: StyleType = "tree.line",
        expanded: bool = True,
        highlight: bool = False,
        hide_root: bool = False,
    ) -> None:
        self.label = label
        self.style = style
        self.guide_style = guide_style
        self.children: List[Tree] = []
        self.expanded = expanded
        self.highlight = highlight
        self.hide_root = hide_root

    def add(
        self,
        label: RenderableType,
        *,
        style: Optional[StyleType] = None,
        guide_style: Optional[StyleType] = None,
        expanded: bool = True,
        highlight: Optional[bool] = False,
    ) -> "Tree":
        """Add a child tree.

        Args:
            label (RenderableType): The renderable or str for the tree label.
            style (StyleType, optional): Style of this tree. Defaults to "tree".
            guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
            expanded (bool, optional): Also display children. Defaults to True.
            highlight (Optional[bool], optional): Highlight renderable (if str). Defaults to False.

        Returns:
            Tree: A new child Tree, which may be further modified.
        """
        node = Tree(
            label,
            style=self.style if style is None else style,
            guide_style=self.guide_style if guide_style is None else guide_style,
            expanded=expanded,
            highlight=self.highlight if highlight is None else highlight,
        )
        self.children.append(node)
        return node

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        stack: List[Iterator[Tuple[bool, Tree]]] = []
        pop = stack.pop
        push = stack.append
        new_line = Segment.line()

        get_style = console.get_style
        null_style = Style.null()
        guide_style = get_style(self.guide_style, default="") or null_style
        SPACE, CONTINUE, FORK, END = range(4)

        _Segment = Segment

        def make_guide(index: int, style: Style) -> Segment:
            """Make a Segment for a level of the guide lines."""
            if options.ascii_only:
                line = self.ASCII_GUIDES[index]
            else:
                guide = 1 if style.bold else (2 if style.underline2 else 0)
                line = self.TREE_GUIDES[0 if options.legacy_windows else guide][index]
            return _Segment(line, style)

        levels: List[Segment] = [make_guide(CONTINUE, guide_style)]
        push(iter(loop_last([self])))

        guide_style_stack = StyleStack(get_style(self.guide_style))
        style_stack = StyleStack(get_style(self.style))
        remove_guide_styles = Style(bold=False, underline2=False)

        depth = 0

        while stack:
            stack_node = pop()
            try:
                last, node = next(stack_node)
            except StopIteration:
                levels.pop()
                if levels:
                    guide_style = levels[-1].style or null_style
                    levels[-1] = make_guide(FORK, guide_style)
                    guide_style_stack.pop()
                    style_stack.pop()
                continue
            push(stack_node)
            if last:
                levels[-1] = make_guide(END, levels[-1].style or null_style)

            guide_style = guide_style_stack.current + get_style(node.guide_style)
            style = style_stack.current + get_style(node.style)
            prefix = levels[(2 if self.hide_root else 1) :]
            renderable_lines = console.render_lines(
                Styled(node.label, style),
                options.update(
                    width=options.max_width
                    - sum(level.cell_length for level in prefix),
                    highlight=self.highlight,
                    height=None,
                ),
                pad=options.justify is not None,
            )

            if not (depth == 0 and self.hide_root):
                for first, line in loop_first(renderable_lines):
                    if prefix:
                        yield from _Segment.apply_style(
                            prefix,
                            style.background_style,
                            post_style=remove_guide_styles,
                        )
                    yield from line
                    yield new_line
                    if first and prefix:
                        prefix[-1] = make_guide(
                            SPACE if last else CONTINUE, prefix[-1].style or null_style
                        )

            if node.expanded and node.children:
                levels[-1] = make_guide(
                    SPACE if last else CONTINUE, levels[-1].style or null_style
                )
                levels.append(
                    make_guide(END if len(node.children) == 1 else FORK, guide_style)
                )
                style_stack.push(get_style(node.style))
                guide_style_stack.push(get_style(node.guide_style))
                push(iter(loop_last(node.children)))
                depth += 1

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        stack: List[Iterator[Tree]] = [iter([self])]
        pop = stack.pop
        push = stack.append
        minimum = 0
        maximum = 0
        measure = Measurement.get
        level = 0
        while stack:
            iter_tree = pop()
            try:
                tree = next(iter_tree)
            except StopIteration:
                level -= 1
                continue
            push(iter_tree)
            min_measure, max_measure = measure(console, options, tree.label)
            indent = level * 4
            minimum = max(min_measure + indent, minimum)
            maximum = max(max_measure + indent, maximum)
            if tree.expanded and tree.children:
                push(iter(tree.children))
                level += 1
        return Measurement(minimum, maximum)


if __name__ == "__main__":  # pragma: no cover
    from rich.console import Group
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table

    table = Table(row_styles=["", "dim"])

    table.add_column("Released", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Box Office", justify="right", style="green")

    table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
    table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
    table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
    table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

    code = """\
class Segment(NamedTuple):
    text: str = ""
    style: Optional[Style] = None
    is_control: bool = False
"""
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)

    markdown = Markdown(
        """\
### example.md
> Hello, World!
>
> Markdown _all_ the things
"""
    )

    root = Tree("🌲 [b green]Rich Tree", highlight=True, hide_root=True)

    node = root.add(":file_folder: Renderables", guide_style="red")
    simple_node = node.add(":file_folder: [bold yellow]Atomic", guide_style="uu green")
    simple_node.add(Group("📄 Syntax", syntax))
    simple_node.add(Group("📄 Markdown", Panel(markdown, border_style="green")))

    containers_node = node.add(
        ":file_folder: [bold magenta]Containers", guide_style="bold magenta"
    )
    containers_node.expanded = True
    panel = Panel.fit("Just a panel", border_style="red")
    containers_node.add(Group("📄 Panels", panel))

    containers_node.add(Group("📄 [b magenta]Table", table))

    console = Console()

    console.print(root)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, operations_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta3 import gapic_version as package_version
from google.ai.generativelanguage_v1beta3.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta3.types import model, model_service
from google.ai.generativelanguage_v1beta3.types import tuned_model

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class ModelServiceTransport(abc.ABC):
    """Abstract transport class for ModelService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
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
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.get_model: gapic_v1.method.wrap_method(
                self.get_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_models: gapic_v1.method.wrap_method(
                self.list_models,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_tuned_model: gapic_v1.method.wrap_method(
                self.get_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_tuned_models: gapic_v1.method.wrap_method(
                self.list_tuned_models,
                default_timeout=None,
                client_info=client_info,
            ),
            self.create_tuned_model: gapic_v1.method.wrap_method(
                self.create_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_tuned_model: gapic_v1.method.wrap_method(
                self.update_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_tuned_model: gapic_v1.method.wrap_method(
                self.delete_tuned_model,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def operations_client(self):
        """Return the client designed to process long-running operations."""
        raise NotImplementedError()

    @property
    def get_model(
        self,
    ) -> Callable[
        [model_service.GetModelRequest], Union[model.Model, Awaitable[model.Model]]
    ]:
        raise NotImplementedError()

    @property
    def list_models(
        self,
    ) -> Callable[
        [model_service.ListModelsRequest],
        Union[
            model_service.ListModelsResponse,
            Awaitable[model_service.ListModelsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_tuned_model(
        self,
    ) -> Callable[
        [model_service.GetTunedModelRequest],
        Union[tuned_model.TunedModel, Awaitable[tuned_model.TunedModel]],
    ]:
        raise NotImplementedError()

    @property
    def list_tuned_models(
        self,
    ) -> Callable[
        [model_service.ListTunedModelsRequest],
        Union[
            model_service.ListTunedModelsResponse,
            Awaitable[model_service.ListTunedModelsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def create_tuned_model(
        self,
    ) -> Callable[
        [model_service.CreateTunedModelRequest],
        Union[operations_pb2.Operation, Awaitable[operations_pb2.Operation]],
    ]:
        raise NotImplementedError()

    @property
    def update_tuned_model(
        self,
    ) -> Callable[
        [model_service.UpdateTunedModelRequest],
        Union[gag_tuned_model.TunedModel, Awaitable[gag_tuned_model.TunedModel]],
    ]:
        raise NotImplementedError()

    @property
    def delete_tuned_model(
        self,
    ) -> Callable[
        [model_service.DeleteTunedModelRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("ModelServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_base_call.py ===
# Copyright 2019 The gRPC Authors
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
"""Abstract base classes for client-side Call objects.

Call objects represents the RPC itself, and offer methods to access / modify
its information. They also offer methods to manipulate the life-cycle of the
RPC, e.g. cancellation.
"""

from abc import ABCMeta
from abc import abstractmethod
from typing import Any, AsyncIterator, Generator, Generic, Optional, Union

import grpc

from ._metadata import Metadata
from ._typing import DoneCallbackType
from ._typing import EOFType
from ._typing import RequestType
from ._typing import ResponseType

__all__ = "RpcContext", "Call", "UnaryUnaryCall", "UnaryStreamCall"


class RpcContext(metaclass=ABCMeta):
    """Provides RPC-related information and action."""

    @abstractmethod
    def cancelled(self) -> bool:
        """Return True if the RPC is cancelled.

        The RPC is cancelled when the cancellation was requested with cancel().

        Returns:
          A bool indicates whether the RPC is cancelled or not.
        """

    @abstractmethod
    def done(self) -> bool:
        """Return True if the RPC is done.

        An RPC is done if the RPC is completed, cancelled or aborted.

        Returns:
          A bool indicates if the RPC is done.
        """

    @abstractmethod
    def time_remaining(self) -> Optional[float]:
        """Describes the length of allowed time remaining for the RPC.

        Returns:
          A nonnegative float indicating the length of allowed time in seconds
          remaining for the RPC to complete before it is considered to have
          timed out, or None if no deadline was specified for the RPC.
        """

    @abstractmethod
    def cancel(self) -> bool:
        """Cancels the RPC.

        Idempotent and has no effect if the RPC has already terminated.

        Returns:
          A bool indicates if the cancellation is performed or not.
        """

    @abstractmethod
    def add_done_callback(self, callback: DoneCallbackType) -> None:
        """Registers a callback to be called on RPC termination.

        Args:
          callback: A callable object will be called with the call object as
          its only argument.
        """


class Call(RpcContext, metaclass=ABCMeta):
    """The abstract base class of an RPC on the client-side."""

    @abstractmethod
    async def initial_metadata(self) -> Metadata:
        """Accesses the initial metadata sent by the server.

        Returns:
          The initial :term:`metadata`.
        """

    @abstractmethod
    async def trailing_metadata(self) -> Metadata:
        """Accesses the trailing metadata sent by the server.

        Returns:
          The trailing :term:`metadata`.
        """

    @abstractmethod
    async def code(self) -> grpc.StatusCode:
        """Accesses the status code sent by the server.

        Returns:
          The StatusCode value for the RPC.
        """

    @abstractmethod
    async def details(self) -> str:
        """Accesses the details sent by the server.

        Returns:
          The details string of the RPC.
        """

    @abstractmethod
    async def wait_for_connection(self) -> None:
        """Waits until connected to peer and raises aio.AioRpcError if failed.

        This is an EXPERIMENTAL method.

        This method ensures the RPC has been successfully connected. Otherwise,
        an AioRpcError will be raised to explain the reason of the connection
        failure.

        This method is recommended for building retry mechanisms.
        """


class UnaryUnaryCall(
    Generic[RequestType, ResponseType], Call, metaclass=ABCMeta
):
    """The abstract base class of a unary-unary RPC on the client-side."""

    @abstractmethod
    def __await__(self) -> Generator[Any, None, ResponseType]:
        """Await the response message to be ready.

        Returns:
          The response message of the RPC.
        """


class UnaryStreamCall(
    Generic[RequestType, ResponseType], Call, metaclass=ABCMeta
):
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[ResponseType]:
        """Returns the async iterator representation that yields messages.

        Under the hood, it is calling the "read" method.

        Returns:
          An async iterator object that yields messages.
        """

    @abstractmethod
    async def read(self) -> Union[EOFType, ResponseType]:
        """Reads one message from the stream.

        Read operations must be serialized when called from multiple
        coroutines.

        Note that the iterator and read/write APIs may not be mixed on
        a single RPC.

        Returns:
          A response message, or an `grpc.aio.EOF` to indicate the end of the
          stream.
        """


class StreamUnaryCall(
    Generic[RequestType, ResponseType], Call, metaclass=ABCMeta
):
    @abstractmethod
    async def write(self, request: RequestType) -> None:
        """Writes one message to the stream.

        Note that the iterator and read/write APIs may not be mixed on
        a single RPC.

        Raises:
          An RpcError exception if the write failed.
        """

    @abstractmethod
    async def done_writing(self) -> None:
        """Notifies server that the client is done sending messages.

        After done_writing is called, any additional invocation to the write
        function will fail. This function is idempotent.
        """

    @abstractmethod
    def __await__(self) -> Generator[Any, None, ResponseType]:
        """Await the response message to be ready.

        Returns:
          The response message of the stream.
        """


class StreamStreamCall(
    Generic[RequestType, ResponseType], Call, metaclass=ABCMeta
):
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[ResponseType]:
        """Returns the async iterator representation that yields messages.

        Under the hood, it is calling the "read" method.

        Returns:
          An async iterator object that yields messages.
        """

    @abstractmethod
    async def read(self) -> Union[EOFType, ResponseType]:
        """Reads one message from the stream.

        Read operations must be serialized when called from multiple
        coroutines.

        Note that the iterator and read/write APIs may not be mixed on
        a single RPC.

        Returns:
          A response message, or an `grpc.aio.EOF` to indicate the end of the
          stream.
        """

    @abstractmethod
    async def write(self, request: RequestType) -> None:
        """Writes one message to the stream.

        Note that the iterator and read/write APIs may not be mixed on
        a single RPC.

        Raises:
          An RpcError exception if the write failed.
        """

    @abstractmethod
    async def done_writing(self) -> None:
        """Notifies server that the client is done sending messages.

        After done_writing is called, any additional invocation to the write
        function will fail. This function is idempotent.
        """

# === NexusCore/openenv\Lib\site-packages\jedi\inference\param.py ===
from collections import defaultdict
from inspect import Parameter

from jedi import debug
from jedi.inference.utils import PushBackIterator
from jedi.inference import analysis
from jedi.inference.lazy_value import LazyKnownValue, \
    LazyTreeValue, LazyUnknownValue
from jedi.inference.value import iterable
from jedi.inference.names import ParamName


def _add_argument_issue(error_name, lazy_value, message):
    if isinstance(lazy_value, LazyTreeValue):
        node = lazy_value.data
        if node.parent.type == 'argument':
            node = node.parent
        return analysis.add(lazy_value.context, error_name, node, message)


class ExecutedParamName(ParamName):
    def __init__(self, function_value, arguments, param_node, lazy_value, is_default=False):
        super().__init__(function_value, param_node.name, arguments=arguments)
        self._lazy_value = lazy_value
        self._is_default = is_default

    def infer(self):
        return self._lazy_value.infer()

    def matches_signature(self):
        if self._is_default:
            return True
        argument_values = self.infer().py__class__()
        if self.get_kind() in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
            return True
        annotations = self.infer_annotation(execute_annotation=False)
        if not annotations:
            # If we cannot infer annotations - or there aren't any - pretend
            # that the signature matches.
            return True
        matches = any(c1.is_sub_class_of(c2)
                      for c1 in argument_values
                      for c2 in annotations.gather_annotation_classes())
        debug.dbg("param compare %s: %s <=> %s",
                  matches, argument_values, annotations, color='BLUE')
        return matches

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.string_name)


def get_executed_param_names_and_issues(function_value, arguments):
    """
    Return a tuple of:
      - a list of `ExecutedParamName`s corresponding to the arguments of the
        function execution `function_value`, containing the inferred value of
        those arguments (whether explicit or default)
      - a list of the issues encountered while building that list

    For example, given:
    ```
    def foo(a, b, c=None, d='d'): ...

    foo(42, c='c')
    ```

    Then for the execution of `foo`, this will return a tuple containing:
      - a list with entries for each parameter a, b, c & d; the entries for a,
        c, & d will have their values (42, 'c' and 'd' respectively) included.
      - a list with a single entry about the lack of a value for `b`
    """
    def too_many_args(argument):
        m = _error_argument_count(funcdef, len(unpacked_va))
        # Just report an error for the first param that is not needed (like
        # cPython).
        if arguments.get_calling_nodes():
            # There might not be a valid calling node so check for that first.
            issues.append(
                _add_argument_issue(
                    'type-error-too-many-arguments',
                    argument,
                    message=m
                )
            )
        else:
            issues.append(None)
            debug.warning('non-public warning: %s', m)

    issues = []  # List[Optional[analysis issue]]
    result_params = []
    param_dict = {}
    funcdef = function_value.tree_node
    # Default params are part of the value where the function was defined.
    # This means that they might have access on class variables that the
    # function itself doesn't have.
    default_param_context = function_value.get_default_param_context()

    for param in funcdef.get_params():
        param_dict[param.name.value] = param
    unpacked_va = list(arguments.unpack(funcdef))
    var_arg_iterator = PushBackIterator(iter(unpacked_va))

    non_matching_keys = defaultdict(lambda: [])
    keys_used = {}
    keys_only = False
    had_multiple_value_error = False
    for param in funcdef.get_params():
        # The value and key can both be null. There, the defaults apply.
        # args / kwargs will just be empty arrays / dicts, respectively.
        # Wrong value count is just ignored. If you try to test cases that are
        # not allowed in Python, Jedi will maybe not show any completions.
        is_default = False
        key, argument = next(var_arg_iterator, (None, None))
        while key is not None:
            keys_only = True
            try:
                key_param = param_dict[key]
            except KeyError:
                non_matching_keys[key] = argument
            else:
                if key in keys_used:
                    had_multiple_value_error = True
                    m = ("TypeError: %s() got multiple values for keyword argument '%s'."
                         % (funcdef.name, key))
                    for contextualized_node in arguments.get_calling_nodes():
                        issues.append(
                            analysis.add(contextualized_node.context,
                                         'type-error-multiple-values',
                                         contextualized_node.node, message=m)
                        )
                else:
                    keys_used[key] = ExecutedParamName(
                        function_value, arguments, key_param, argument)
            key, argument = next(var_arg_iterator, (None, None))

        try:
            result_params.append(keys_used[param.name.value])
            continue
        except KeyError:
            pass

        if param.star_count == 1:
            # *args param
            lazy_value_list = []
            if argument is not None:
                lazy_value_list.append(argument)
                for key, argument in var_arg_iterator:
                    # Iterate until a key argument is found.
                    if key:
                        var_arg_iterator.push_back((key, argument))
                        break
                    lazy_value_list.append(argument)
            seq = iterable.FakeTuple(function_value.inference_state, lazy_value_list)
            result_arg = LazyKnownValue(seq)
        elif param.star_count == 2:
            if argument is not None:
                too_many_args(argument)
            # **kwargs param
            dct = iterable.FakeDict(function_value.inference_state, dict(non_matching_keys))
            result_arg = LazyKnownValue(dct)
            non_matching_keys = {}
        else:
            # normal param
            if argument is None:
                # No value: Return an empty container
                if param.default is None:
                    result_arg = LazyUnknownValue()
                    if not keys_only:
                        for contextualized_node in arguments.get_calling_nodes():
                            m = _error_argument_count(funcdef, len(unpacked_va))
                            issues.append(
                                analysis.add(
                                    contextualized_node.context,
                                    'type-error-too-few-arguments',
                                    contextualized_node.node,
                                    message=m,
                                )
                            )
                else:
                    result_arg = LazyTreeValue(default_param_context, param.default)
                    is_default = True
            else:
                result_arg = argument

        result_params.append(ExecutedParamName(
            function_value, arguments, param, result_arg, is_default=is_default
        ))
        if not isinstance(result_arg, LazyUnknownValue):
            keys_used[param.name.value] = result_params[-1]

    if keys_only:
        # All arguments should be handed over to the next function. It's not
        # about the values inside, it's about the names. Jedi needs to now that
        # there's nothing to find for certain names.
        for k in set(param_dict) - set(keys_used):
            param = param_dict[k]

            if not (non_matching_keys or had_multiple_value_error
                    or param.star_count or param.default):
                # add a warning only if there's not another one.
                for contextualized_node in arguments.get_calling_nodes():
                    m = _error_argument_count(funcdef, len(unpacked_va))
                    issues.append(
                        analysis.add(contextualized_node.context,
                                     'type-error-too-few-arguments',
                                     contextualized_node.node, message=m)
                    )

    for key, lazy_value in non_matching_keys.items():
        m = "TypeError: %s() got an unexpected keyword argument '%s'." \
            % (funcdef.name, key)
        issues.append(
            _add_argument_issue(
                'type-error-keyword-argument',
                lazy_value,
                message=m
            )
        )

    remaining_arguments = list(var_arg_iterator)
    if remaining_arguments:
        first_key, lazy_value = remaining_arguments[0]
        too_many_args(lazy_value)
    return result_params, issues


def get_executed_param_names(function_value, arguments):
    """
    Return a list of `ExecutedParamName`s corresponding to the arguments of the
    function execution `function_value`, containing the inferred value of those
    arguments (whether explicit or default). Any issues building this list (for
    example required arguments which are missing in the invocation) are ignored.

    For example, given:
    ```
    def foo(a, b, c=None, d='d'): ...

    foo(42, c='c')
    ```

    Then for the execution of `foo`, this will return a list containing entries
    for each parameter a, b, c & d; the entries for a, c, & d will have their
    values (42, 'c' and 'd' respectively) included.
    """
    return get_executed_param_names_and_issues(function_value, arguments)[0]


def _error_argument_count(funcdef, actual_count):
    params = funcdef.get_params()
    default_arguments = sum(1 for p in params if p.default or p.star_count)

    if default_arguments == 0:
        before = 'exactly '
    else:
        before = 'from %s to ' % (len(params) - default_arguments)
    return ('TypeError: %s() takes %s%s arguments (%s given).'
            % (funcdef.name, before, len(params), actual_count))

# === NexusCore/openenv\Lib\site-packages\jedi\inference\compiled\subprocess\functions.py ===
import sys
import os
import inspect
import importlib
from pathlib import Path
from zipfile import ZipFile
from zipimport import zipimporter, ZipImportError
from importlib.machinery import all_suffixes

from jedi.inference.compiled import access
from jedi import debug
from jedi import parser_utils
from jedi.file_io import KnownContentFileIO, ZipFileIO


def get_sys_path():
    return sys.path


def load_module(inference_state, **kwargs):
    return access.load_module(inference_state, **kwargs)


def get_compiled_method_return(inference_state, id, attribute, *args, **kwargs):
    handle = inference_state.compiled_subprocess.get_access_handle(id)
    return getattr(handle.access, attribute)(*args, **kwargs)


def create_simple_object(inference_state, obj):
    return access.create_access_path(inference_state, obj)


def get_module_info(inference_state, sys_path=None, full_name=None, **kwargs):
    """
    Returns Tuple[Union[NamespaceInfo, FileIO, None], Optional[bool]]
    """
    if sys_path is not None:
        sys.path, temp = sys_path, sys.path
    try:
        return _find_module(full_name=full_name, **kwargs)
    except ImportError:
        return None, None
    finally:
        if sys_path is not None:
            sys.path = temp


def get_builtin_module_names(inference_state):
    return sys.builtin_module_names


def _test_raise_error(inference_state, exception_type):
    """
    Raise an error to simulate certain problems for unit tests.
    """
    raise exception_type


def _test_print(inference_state, stderr=None, stdout=None):
    """
    Force some prints in the subprocesses. This exists for unit tests.
    """
    if stderr is not None:
        print(stderr, file=sys.stderr)
        sys.stderr.flush()
    if stdout is not None:
        print(stdout)
        sys.stdout.flush()


def _get_init_path(directory_path):
    """
    The __init__ file can be searched in a directory. If found return it, else
    None.
    """
    for suffix in all_suffixes():
        path = os.path.join(directory_path, '__init__' + suffix)
        if os.path.exists(path):
            return path
    return None


def safe_literal_eval(inference_state, value):
    return parser_utils.safe_literal_eval(value)


def iter_module_names(*args, **kwargs):
    return list(_iter_module_names(*args, **kwargs))


def _iter_module_names(inference_state, paths):
    # Python modules/packages
    for path in paths:
        try:
            dir_entries = ((entry.name, entry.is_dir()) for entry in os.scandir(path))
        except OSError:
            try:
                zip_import_info = zipimporter(path)
                # Unfortunately, there is no public way to access zipimporter's
                # private _files member. We therefore have to use a
                # custom function to iterate over the files.
                dir_entries = _zip_list_subdirectory(
                    zip_import_info.archive, zip_import_info.prefix)
            except ZipImportError:
                # The file might not exist or reading it might lead to an error.
                debug.warning("Not possible to list directory: %s", path)
                continue
        for name, is_dir in dir_entries:
            # First Namespaces then modules/stubs
            if is_dir:
                # pycache is obviously not an interesting namespace. Also the
                # name must be a valid identifier.
                if name != '__pycache__' and name.isidentifier():
                    yield name
            else:
                if name.endswith('.pyi'):  # Stub files
                    modname = name[:-4]
                else:
                    modname = inspect.getmodulename(name)

                if modname and '.' not in modname:
                    if modname != '__init__':
                        yield modname


def _find_module(string, path=None, full_name=None, is_global_search=True):
    """
    Provides information about a module.

    This function isolates the differences in importing libraries introduced with
    python 3.3 on; it gets a module name and optionally a path. It will return a
    tuple containin an open file for the module (if not builtin), the filename
    or the name of the module if it is a builtin one and a boolean indicating
    if the module is contained in a package.
    """
    spec = None
    loader = None

    for finder in sys.meta_path:
        if is_global_search and finder != importlib.machinery.PathFinder:
            p = None
        else:
            p = path
        try:
            find_spec = finder.find_spec
        except AttributeError:
            # These are old-school clases that still have a different API, just
            # ignore those.
            continue

        spec = find_spec(string, p)
        if spec is not None:
            if spec.origin == "frozen":
                continue

            loader = spec.loader

            if loader is None and not spec.has_location:
                # This is a namespace package.
                full_name = string if not path else full_name
                implicit_ns_info = ImplicitNSInfo(full_name, spec.submodule_search_locations._path)
                return implicit_ns_info, True
            break

    return _find_module_py33(string, path, loader)


def _find_module_py33(string, path=None, loader=None, full_name=None, is_global_search=True):
    if not loader:
        spec = importlib.machinery.PathFinder.find_spec(string, path)
        if spec is not None:
            loader = spec.loader

    if loader is None and path is None:  # Fallback to find builtins
        try:
            spec = importlib.util.find_spec(string)
            if spec is not None:
                loader = spec.loader
        except ValueError as e:
            # See #491. Importlib might raise a ValueError, to avoid this, we
            # just raise an ImportError to fix the issue.
            raise ImportError("Originally  " + repr(e))

    if loader is None:
        raise ImportError("Couldn't find a loader for {}".format(string))

    return _from_loader(loader, string)


def _from_loader(loader, string):
    try:
        is_package_method = loader.is_package
    except AttributeError:
        is_package = False
    else:
        is_package = is_package_method(string)
    try:
        get_filename = loader.get_filename
    except AttributeError:
        return None, is_package
    else:
        module_path = get_filename(string)

    # To avoid unicode and read bytes, "overwrite" loader.get_source if
    # possible.
    try:
        f = type(loader).get_source
    except AttributeError:
        raise ImportError("get_source was not defined on loader")

    if f is not importlib.machinery.SourceFileLoader.get_source:
        # Unfortunately we are reading unicode here, not bytes.
        # It seems hard to get bytes, because the zip importer
        # logic just unpacks the zip file and returns a file descriptor
        # that we cannot as easily access. Therefore we just read it as
        # a string in the cases where get_source was overwritten.
        code = loader.get_source(string)
    else:
        code = _get_source(loader, string)

    if code is None:
        return None, is_package
    if isinstance(loader, zipimporter):
        return ZipFileIO(module_path, code, Path(loader.archive)), is_package

    return KnownContentFileIO(module_path, code), is_package


def _get_source(loader, fullname):
    """
    This method is here as a replacement for SourceLoader.get_source. That
    method returns unicode, but we prefer bytes.
    """
    path = loader.get_filename(fullname)
    try:
        return loader.get_data(path)
    except OSError:
        raise ImportError('source not available through get_data()',
                          name=fullname)


def _zip_list_subdirectory(zip_path, zip_subdir_path):
    zip_file = ZipFile(zip_path)
    zip_subdir_path = Path(zip_subdir_path)
    zip_content_file_paths = zip_file.namelist()
    for raw_file_name in zip_content_file_paths:
        file_path = Path(raw_file_name)
        if file_path.parent == zip_subdir_path:
            file_path = file_path.relative_to(zip_subdir_path)
            yield file_path.name, raw_file_name.endswith("/")


class ImplicitNSInfo:
    """Stores information returned from an implicit namespace spec"""
    def __init__(self, name, paths):
        self.name = name
        self.paths = paths

# === NexusCore/openenv\Lib\site-packages\jupyter_client\provisioning\provisioner_base.py ===
"""Kernel Provisioner Classes"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os
from abc import ABC, ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional, Union

from traitlets.config import Instance, LoggingConfigurable, Unicode

from ..connect import KernelConnectionInfo


class KernelProvisionerMeta(ABCMeta, type(LoggingConfigurable)):  # type: ignore[misc]
    pass


class KernelProvisionerBase(  # type:ignore[misc]
    ABC, LoggingConfigurable, metaclass=KernelProvisionerMeta
):
    """
    Abstract base class defining methods for KernelProvisioner classes.

    A majority of methods are abstract (requiring implementations via a subclass) while
    some are optional and others provide implementations common to all instances.
    Subclasses should be aware of which methods require a call to the superclass.

    Many of these methods model those of :class:`subprocess.Popen` for parity with
    previous versions where the kernel process was managed directly.
    """

    # The kernel specification associated with this provisioner
    kernel_spec: Any = Instance("jupyter_client.kernelspec.KernelSpec", allow_none=True)
    kernel_id: Union[str, Unicode] = Unicode(None, allow_none=True)
    connection_info: KernelConnectionInfo = {}

    @property
    @abstractmethod
    def has_process(self) -> bool:
        """
        Returns true if this provisioner is currently managing a process.

        This property is asserted to be True immediately following a call to
        the provisioner's :meth:`launch_kernel` method.
        """
        pass

    @abstractmethod
    async def poll(self) -> Optional[int]:
        """
        Checks if kernel process is still running.

        If running, None is returned, otherwise the process's integer-valued exit code is returned.
        This method is called from :meth:`KernelManager.is_alive`.
        """
        pass

    @abstractmethod
    async def wait(self) -> Optional[int]:
        """
        Waits for kernel process to terminate.

        This method is called from `KernelManager.finish_shutdown()` and
        `KernelManager.kill_kernel()` when terminating a kernel gracefully or
        immediately, respectively.
        """
        pass

    @abstractmethod
    async def send_signal(self, signum: int) -> None:
        """
        Sends signal identified by signum to the kernel process.

        This method is called from `KernelManager.signal_kernel()` to send the
        kernel process a signal.
        """
        pass

    @abstractmethod
    async def kill(self, restart: bool = False) -> None:
        """
        Kill the kernel process.

        This is typically accomplished via a SIGKILL signal, which cannot be caught.
        This method is called from `KernelManager.kill_kernel()` when terminating
        a kernel immediately.

        restart is True if this operation will precede a subsequent launch_kernel request.
        """
        pass

    @abstractmethod
    async def terminate(self, restart: bool = False) -> None:
        """
        Terminates the kernel process.

        This is typically accomplished via a SIGTERM signal, which can be caught, allowing
        the kernel provisioner to perform possible cleanup of resources.  This method is
        called indirectly from `KernelManager.finish_shutdown()` during a kernel's
        graceful termination.

        restart is True if this operation precedes a start launch_kernel request.
        """
        pass

    @abstractmethod
    async def launch_kernel(self, cmd: List[str], **kwargs: Any) -> KernelConnectionInfo:
        """
        Launch the kernel process and return its connection information.

        This method is called from `KernelManager.launch_kernel()` during the
        kernel manager's start kernel sequence.
        """
        pass

    @abstractmethod
    async def cleanup(self, restart: bool = False) -> None:
        """
        Cleanup any resources allocated on behalf of the kernel provisioner.

        This method is called from `KernelManager.cleanup_resources()` as part of
        its shutdown kernel sequence.

        restart is True if this operation precedes a start launch_kernel request.
        """
        pass

    async def shutdown_requested(self, restart: bool = False) -> None:
        """
        Allows the provisioner to determine if the kernel's shutdown has been requested.

        This method is called from `KernelManager.request_shutdown()` as part of
        its shutdown sequence.

        This method is optional and is primarily used in scenarios where the provisioner
        may need to perform other operations in preparation for a kernel's shutdown.
        """
        pass

    async def pre_launch(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Perform any steps in preparation for kernel process launch.

        This includes applying additional substitutions to the kernel launch command
        and environment. It also includes preparation of launch parameters.

        NOTE: Subclass implementations are advised to call this method as it applies
        environment variable substitutions from the local environment and calls the
        provisioner's :meth:`_finalize_env()` method to allow each provisioner the
        ability to cleanup the environment variables that will be used by the kernel.

        This method is called from `KernelManager.pre_start_kernel()` as part of its
        start kernel sequence.

        Returns the (potentially updated) keyword arguments that are passed to
        :meth:`launch_kernel()`.
        """
        env = kwargs.pop("env", os.environ).copy()
        env.update(self.__apply_env_substitutions(env))
        self._finalize_env(env)
        kwargs["env"] = env

        return kwargs

    async def post_launch(self, **kwargs: Any) -> None:
        """
        Perform any steps following the kernel process launch.

        This method is called from `KernelManager.post_start_kernel()` as part of its
        start kernel sequence.
        """
        pass

    async def get_provisioner_info(self) -> Dict[str, Any]:
        """
        Captures the base information necessary for persistence relative to this instance.

        This enables applications that subclass `KernelManager` to persist a kernel provisioner's
        relevant information to accomplish functionality like disaster recovery or high availability
        by calling this method via the kernel manager's `provisioner` attribute.

        NOTE: The superclass method must always be called first to ensure proper serialization.
        """
        provisioner_info: Dict[str, Any] = {}
        provisioner_info["kernel_id"] = self.kernel_id
        provisioner_info["connection_info"] = self.connection_info
        return provisioner_info

    async def load_provisioner_info(self, provisioner_info: Dict) -> None:
        """
        Loads the base information necessary for persistence relative to this instance.

        The inverse of `get_provisioner_info()`, this enables applications that subclass
        `KernelManager` to re-establish communication with a provisioner that is managing
        a (presumably) remote kernel from an entirely different process that the original
        provisioner.

        NOTE: The superclass method must always be called first to ensure proper deserialization.
        """
        self.kernel_id = provisioner_info["kernel_id"]
        self.connection_info = provisioner_info["connection_info"]

    def get_shutdown_wait_time(self, recommended: float = 5.0) -> float:
        """
        Returns the time allowed for a complete shutdown. This may vary by provisioner.

        This method is called from `KernelManager.finish_shutdown()` during the graceful
        phase of its kernel shutdown sequence.

        The recommended value will typically be what is configured in the kernel manager.
        """
        return recommended

    def get_stable_start_time(self, recommended: float = 10.0) -> float:
        """
        Returns the expected upper bound for a kernel (re-)start to complete.
        This may vary by provisioner.

        The recommended value will typically be what is configured in the kernel restarter.
        """
        return recommended

    def _finalize_env(self, env: Dict[str, str]) -> None:
        """
        Ensures env is appropriate prior to launch.

        This method is called from `KernelProvisionerBase.pre_launch()` during the kernel's
        start sequence.

        NOTE: Subclasses should be sure to call super()._finalize_env(env)
        """
        if self.kernel_spec.language and self.kernel_spec.language.lower().startswith("python"):
            # Don't allow PYTHONEXECUTABLE to be passed to kernel process.
            # If set, it can bork all the things.
            env.pop("PYTHONEXECUTABLE", None)

    def __apply_env_substitutions(self, substitution_values: Dict[str, str]) -> Dict[str, str]:
        """
        Walks entries in the kernelspec's env stanza and applies substitutions from current env.

        This method is called from `KernelProvisionerBase.pre_launch()` during the kernel's
        start sequence.

        Returns the substituted list of env entries.

        NOTE: This method is private and is not intended to be overridden by provisioners.
        """
        substituted_env = {}
        if self.kernel_spec:
            from string import Template

            # For each templated env entry, fill any templated references
            # matching names of env variables with those values and build
            # new dict with substitutions.
            templated_env = self.kernel_spec.env
            for k, v in templated_env.items():
                substituted_env.update({k: Template(v).safe_substitute(substitution_values)})
        return substituted_env

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\caching_routes.py ===
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import RedisCache
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.litellm_core_utils.sensitive_data_masker import SensitiveDataMasker
from litellm.proxy._types import ProxyErrorTypes, ProxyException
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.types.caching import CachePingResponse, HealthCheckCacheParams

masker = SensitiveDataMasker()

router = APIRouter(
    prefix="/cache",
    tags=["caching"],
)


def _extract_cache_params() -> Dict[str, Any]:
    """
    Safely extracts and cleans cache parameters.

    The health check UI needs to display specific cache parameters, to show users how they set up their cache.

    eg.
        {
            "host": "localhost",
            "port": 6379,
            "redis_kwargs": {"db": 0},
            "namespace": "test",
        }

    Returns:
        Dict containing cleaned and masked cache parameters
    """
    if litellm.cache is None:
        return {}
    try:
        cache_params = vars(litellm.cache.cache)
        cleaned_params = (
            HealthCheckCacheParams(**cache_params).model_dump() if cache_params else {}
        )
        return masker.mask_dict(cleaned_params)
    except (AttributeError, TypeError) as e:
        verbose_proxy_logger.debug(f"Error extracting cache params: {str(e)}")
        return {}


@router.get(
    "/ping",
    response_model=CachePingResponse,
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_ping():
    """
    Endpoint for checking if cache can be pinged
    """
    litellm_cache_params: Dict[str, Any] = {}
    cleaned_cache_params: Dict[str, Any] = {}
    try:
        if litellm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. litellm.cache is None"
            )
        litellm_cache_params = masker.mask_dict(vars(litellm.cache))
        # remove field that might reference itself
        litellm_cache_params.pop("cache", None)
        cleaned_cache_params = _extract_cache_params()

        if litellm.cache.type == "redis":
            ping_response = await litellm.cache.ping()
            verbose_proxy_logger.debug(
                "/cache/ping: ping_response: " + str(ping_response)
            )
            # add cache does not return anything
            await litellm.cache.async_add_cache(
                result="test_key",
                model="test-model",
                messages=[{"role": "user", "content": "test from litellm"}],
            )
            verbose_proxy_logger.debug("/cache/ping: done with set_cache()")

            return CachePingResponse(
                status="healthy",
                cache_type=str(litellm.cache.type),
                ping_response=True,
                set_cache_response="success",
                litellm_cache_params=safe_dumps(litellm_cache_params),
                health_check_cache_params=cleaned_cache_params,
            )
        else:
            return CachePingResponse(
                status="healthy",
                cache_type=str(litellm.cache.type),
                litellm_cache_params=safe_dumps(litellm_cache_params),
            )
    except Exception as e:
        import traceback

        error_message = {
            "message": f"Service Unhealthy ({str(e)})",
            "litellm_cache_params": safe_dumps(litellm_cache_params),
            "health_check_cache_params": safe_dumps(cleaned_cache_params),
            "traceback": traceback.format_exc(),
        }
        raise ProxyException(
            message=safe_dumps(error_message),
            type=ProxyErrorTypes.cache_ping_error,
            param="cache_ping",
            code=503,
        )


@router.post(
    "/delete",
    tags=["caching"],
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_delete(request: Request):
    """
    Endpoint for deleting a key from the cache. All responses from litellm proxy have `x-litellm-cache-key` in the headers

    Parameters:
    - **keys**: *Optional[List[str]]* - A list of keys to delete from the cache. Example {"keys": ["key1", "key2"]}

    ```shell
    curl -X POST "http://0.0.0.0:4000/cache/delete" \
    -H "Authorization: Bearer sk-1234" \
    -d '{"keys": ["key1", "key2"]}'
    ```

    """
    try:
        if litellm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. litellm.cache is None"
            )

        request_data = await request.json()
        keys = request_data.get("keys", None)

        if litellm.cache.type == "redis":
            await litellm.cache.delete_cache_keys(keys=keys)
            return {
                "status": "success",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {litellm.cache.type} does not support deleting a key. only `redis` is supported",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache Delete Failed({str(e)})",
        )


def _get_redis_client_info(cache_instance) -> Tuple[List, int]:
    """
    Helper function to safely get Redis client list information.

    Returns:
        tuple: (client_list, num_clients) where num_clients is -1 if CLIENT LIST is unavailable
    """
    try:
        client_list = cache_instance.client_list()
        return client_list, len(client_list)
    except Exception as e:
        verbose_proxy_logger.warning(
            f"CLIENT LIST command failed (likely restricted on managed Redis): {str(e)}"
        )
        return ["CLIENT LIST command not available on this Redis instance"], -1


@router.get(
    "/redis/info",
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_redis_info():
    """
    Endpoint for getting /redis/info
    """
    try:
        if litellm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. litellm.cache is None"
            )

        if not (
            litellm.cache.type == "redis"
            and isinstance(litellm.cache.cache, RedisCache)
        ):
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {litellm.cache.type} does not support redis info",
            )

        # Get client information (handles CLIENT LIST restrictions gracefully)
        client_list, num_clients = _get_redis_client_info(litellm.cache.cache)

        # Get Redis server information
        redis_info = litellm.cache.cache.info()

        return {
            "num_clients": num_clients,
            "clients": client_list,
            "info": redis_info,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service Unhealthy ({str(e)})",
        )


@router.post(
    "/flushall",
    tags=["caching"],
    dependencies=[Depends(user_api_key_auth)],
)
async def cache_flushall():
    """
    A function to flush all items from the cache. (All items will be deleted from the cache with this)
    Raises HTTPException if the cache is not initialized or if the cache type does not support flushing.
    Returns a dictionary with the status of the operation.

    Usage:
    ```
    curl -X POST http://0.0.0.0:4000/cache/flushall -H "Authorization: Bearer sk-1234"
    ```
    """
    try:
        if litellm.cache is None:
            raise HTTPException(
                status_code=503, detail="Cache not initialized. litellm.cache is None"
            )
        if litellm.cache.type == "redis" and isinstance(
            litellm.cache.cache, RedisCache
        ):
            litellm.cache.cache.flushall()
            return {
                "status": "success",
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Cache type {litellm.cache.type} does not support flushing",
            )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service Unhealthy ({str(e)})",
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\common_utils.py ===
"""
This file contains common utils for anthropic calls.
"""

from typing import Dict, List, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    get_file_ids_from_messages,
)
from litellm.llms.base_llm.base_utils import BaseLLMModelInfo
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.llms.anthropic import AllAnthropicToolsValues, AnthropicMcpServerTool
from litellm.types.llms.openai import AllMessageValues


class AnthropicError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message,
        headers: Optional[httpx.Headers] = None,
    ):
        super().__init__(status_code=status_code, message=message, headers=headers)


class AnthropicModelInfo(BaseLLMModelInfo):
    def is_cache_control_set(self, messages: List[AllMessageValues]) -> bool:
        """
        Return if {"cache_control": ..} in message content block

        Used to check if anthropic prompt caching headers need to be set.
        """
        for message in messages:
            if message.get("cache_control", None) is not None:
                return True
            _message_content = message.get("content")
            if _message_content is not None and isinstance(_message_content, list):
                for content in _message_content:
                    if "cache_control" in content:
                        return True

        return False

    def is_file_id_used(self, messages: List[AllMessageValues]) -> bool:
        """
        Return if {"source": {"type": "file", "file_id": ..}} in message content block
        """
        file_ids = get_file_ids_from_messages(messages)
        return len(file_ids) > 0

    def is_mcp_server_used(
        self, mcp_servers: Optional[List[AnthropicMcpServerTool]]
    ) -> bool:
        if mcp_servers is None:
            return False
        if mcp_servers:
            return True
        return False

    def is_computer_tool_used(
        self, tools: Optional[List[AllAnthropicToolsValues]]
    ) -> bool:
        if tools is None:
            return False
        for tool in tools:
            if "type" in tool and tool["type"].startswith("computer_"):
                return True
        return False

    def is_pdf_used(self, messages: List[AllMessageValues]) -> bool:
        """
        Set to true if media passed into messages.

        """
        for message in messages:
            if (
                "content" in message
                and message["content"] is not None
                and isinstance(message["content"], list)
            ):
                for content in message["content"]:
                    if "type" in content and content["type"] != "text":
                        return True
        return False

    def _get_user_anthropic_beta_headers(
        self, anthropic_beta_header: Optional[str]
    ) -> Optional[List[str]]:
        if anthropic_beta_header is None:
            return None
        return anthropic_beta_header.split(",")

    def get_anthropic_headers(
        self,
        api_key: str,
        anthropic_version: Optional[str] = None,
        computer_tool_used: bool = False,
        prompt_caching_set: bool = False,
        pdf_used: bool = False,
        file_id_used: bool = False,
        mcp_server_used: bool = False,
        is_vertex_request: bool = False,
        user_anthropic_beta_headers: Optional[List[str]] = None,
    ) -> dict:
        betas = set()
        if prompt_caching_set:
            betas.add("prompt-caching-2024-07-31")
        if computer_tool_used:
            betas.add("computer-use-2024-10-22")
        # if pdf_used:
        #     betas.add("pdfs-2024-09-25")
        if file_id_used:
            betas.add("files-api-2025-04-14")
            betas.add("code-execution-2025-05-22")
        if mcp_server_used:
            betas.add("mcp-client-2025-04-04")

        headers = {
            "anthropic-version": anthropic_version or "2023-06-01",
            "x-api-key": api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

        if user_anthropic_beta_headers is not None:
            betas.update(user_anthropic_beta_headers)

        # Don't send any beta headers to Vertex, Vertex has failed requests when they are sent
        if is_vertex_request is True:
            pass
        elif len(betas) > 0:
            headers["anthropic-beta"] = ",".join(betas)

        return headers

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Dict:
        if api_key is None:
            raise litellm.AuthenticationError(
                message="Missing Anthropic API Key - A call is being made to anthropic but no key is set either in the environment variables or via params. Please set `ANTHROPIC_API_KEY` in your environment vars",
                llm_provider="anthropic",
                model=model,
            )

        tools = optional_params.get("tools")
        prompt_caching_set = self.is_cache_control_set(messages=messages)
        computer_tool_used = self.is_computer_tool_used(tools=tools)
        mcp_server_used = self.is_mcp_server_used(
            mcp_servers=optional_params.get("mcp_servers")
        )
        pdf_used = self.is_pdf_used(messages=messages)
        file_id_used = self.is_file_id_used(messages=messages)
        user_anthropic_beta_headers = self._get_user_anthropic_beta_headers(
            anthropic_beta_header=headers.get("anthropic-beta")
        )
        anthropic_headers = self.get_anthropic_headers(
            computer_tool_used=computer_tool_used,
            prompt_caching_set=prompt_caching_set,
            pdf_used=pdf_used,
            api_key=api_key,
            file_id_used=file_id_used,
            is_vertex_request=optional_params.get("is_vertex_request", False),
            user_anthropic_beta_headers=user_anthropic_beta_headers,
            mcp_server_used=mcp_server_used,
        )

        headers = {**headers, **anthropic_headers}

        return headers

    @staticmethod
    def get_api_base(api_base: Optional[str] = None) -> Optional[str]:
        from litellm.secret_managers.main import get_secret_str

        return (
            api_base
            or get_secret_str("ANTHROPIC_API_BASE")
            or "https://api.anthropic.com"
        )

    @staticmethod
    def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
        from litellm.secret_managers.main import get_secret_str

        return api_key or get_secret_str("ANTHROPIC_API_KEY")

    @staticmethod
    def get_base_model(model: Optional[str] = None) -> Optional[str]:
        return model.replace("anthropic/", "") if model else None

    def get_models(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None
    ) -> List[str]:
        api_base = AnthropicModelInfo.get_api_base(api_base)
        api_key = AnthropicModelInfo.get_api_key(api_key)
        if api_base is None or api_key is None:
            raise ValueError(
                "ANTHROPIC_API_BASE or ANTHROPIC_API_KEY is not set. Please set the environment variable, to query Anthropic's `/models` endpoint."
            )
        response = litellm.module_level_client.get(
            url=f"{api_base}/v1/models",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            raise Exception(
                f"Failed to fetch models from Anthropic. Status code: {response.status_code}, Response: {response.text}"
            )

        models = response.json()["data"]

        litellm_model_names = []
        for model in models:
            stripped_model_name = model["id"]
            litellm_model_name = "anthropic/" + stripped_model_name
            litellm_model_names.append(litellm_model_name)
        return litellm_model_names


def process_anthropic_headers(headers: Union[httpx.Headers, dict]) -> dict:
    openai_headers = {}
    if "anthropic-ratelimit-requests-limit" in headers:
        openai_headers["x-ratelimit-limit-requests"] = headers[
            "anthropic-ratelimit-requests-limit"
        ]
    if "anthropic-ratelimit-requests-remaining" in headers:
        openai_headers["x-ratelimit-remaining-requests"] = headers[
            "anthropic-ratelimit-requests-remaining"
        ]
    if "anthropic-ratelimit-tokens-limit" in headers:
        openai_headers["x-ratelimit-limit-tokens"] = headers[
            "anthropic-ratelimit-tokens-limit"
        ]
    if "anthropic-ratelimit-tokens-remaining" in headers:
        openai_headers["x-ratelimit-remaining-tokens"] = headers[
            "anthropic-ratelimit-tokens-remaining"
        ]

    llm_response_headers = {
        "{}-{}".format("llm_provider", k): v for k, v in headers.items()
    }

    additional_headers = {**llm_response_headers, **openai_headers}
    return additional_headers

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\parasite_axes.py ===
from matplotlib import _api, cbook
import matplotlib.artist as martist
import matplotlib.transforms as mtransforms
from matplotlib.transforms import Bbox
from .mpl_axes import Axes


class ParasiteAxesBase:

    def __init__(self, parent_axes, aux_transform=None,
                 *, viewlim_mode=None, **kwargs):
        self._parent_axes = parent_axes
        self.transAux = aux_transform
        self.set_viewlim_mode(viewlim_mode)
        kwargs["frameon"] = False
        super().__init__(parent_axes.get_figure(root=False),
                         parent_axes._position, **kwargs)

    def clear(self):
        super().clear()
        martist.setp(self.get_children(), visible=False)
        self._get_lines = self._parent_axes._get_lines
        self._parent_axes.callbacks._connect_picklable(
            "xlim_changed", self._sync_lims)
        self._parent_axes.callbacks._connect_picklable(
            "ylim_changed", self._sync_lims)

    def pick(self, mouseevent):
        # This most likely goes to Artist.pick (depending on axes_class given
        # to the factory), which only handles pick events registered on the
        # axes associated with each child:
        super().pick(mouseevent)
        # But parasite axes are additionally given pick events from their host
        # axes (cf. HostAxesBase.pick), which we handle here:
        for a in self.get_children():
            if (hasattr(mouseevent.inaxes, "parasites")
                    and self in mouseevent.inaxes.parasites):
                a.pick(mouseevent)

    # aux_transform support

    def _set_lim_and_transforms(self):
        if self.transAux is not None:
            self.transAxes = self._parent_axes.transAxes
            self.transData = self.transAux + self._parent_axes.transData
            self._xaxis_transform = mtransforms.blended_transform_factory(
                self.transData, self.transAxes)
            self._yaxis_transform = mtransforms.blended_transform_factory(
                self.transAxes, self.transData)
        else:
            super()._set_lim_and_transforms()

    def set_viewlim_mode(self, mode):
        _api.check_in_list([None, "equal", "transform"], mode=mode)
        self._viewlim_mode = mode

    def get_viewlim_mode(self):
        return self._viewlim_mode

    def _sync_lims(self, parent):
        viewlim = parent.viewLim.frozen()
        mode = self.get_viewlim_mode()
        if mode is None:
            pass
        elif mode == "equal":
            self.viewLim.set(viewlim)
        elif mode == "transform":
            self.viewLim.set(viewlim.transformed(self.transAux.inverted()))
        else:
            _api.check_in_list([None, "equal", "transform"], mode=mode)

    # end of aux_transform support


parasite_axes_class_factory = cbook._make_class_factory(
    ParasiteAxesBase, "{}Parasite")
ParasiteAxes = parasite_axes_class_factory(Axes)


class HostAxesBase:
    def __init__(self, *args, **kwargs):
        self.parasites = []
        super().__init__(*args, **kwargs)

    def get_aux_axes(
            self, tr=None, viewlim_mode="equal", axes_class=None, **kwargs):
        """
        Add a parasite axes to this host.

        Despite this method's name, this should actually be thought of as an
        ``add_parasite_axes`` method.

        .. versionchanged:: 3.7
           Defaults to same base axes class as host axes.

        Parameters
        ----------
        tr : `~matplotlib.transforms.Transform` or None, default: None
            If a `.Transform`, the following relation will hold:
            ``parasite.transData = tr + host.transData``.
            If None, the parasite's and the host's ``transData`` are unrelated.
        viewlim_mode : {"equal", "transform", None}, default: "equal"
            How the parasite's view limits are set: directly equal to the
            parent axes ("equal"), equal after application of *tr*
            ("transform"), or independently (None).
        axes_class : subclass type of `~matplotlib.axes.Axes`, optional
            The `~.axes.Axes` subclass that is instantiated.  If None, the base
            class of the host axes is used.
        **kwargs
            Other parameters are forwarded to the parasite axes constructor.
        """
        if axes_class is None:
            axes_class = self._base_axes_class
        parasite_axes_class = parasite_axes_class_factory(axes_class)
        ax2 = parasite_axes_class(
            self, tr, viewlim_mode=viewlim_mode, **kwargs)
        # note that ax2.transData == tr + ax1.transData
        # Anything you draw in ax2 will match the ticks and grids of ax1.
        self.parasites.append(ax2)
        ax2._remove_method = self.parasites.remove
        return ax2

    def draw(self, renderer):
        orig_children_len = len(self._children)

        locator = self.get_axes_locator()
        if locator:
            pos = locator(self, renderer)
            self.set_position(pos, which="active")
            self.apply_aspect(pos)
        else:
            self.apply_aspect()

        rect = self.get_position()
        for ax in self.parasites:
            ax.apply_aspect(rect)
            self._children.extend(ax.get_children())

        super().draw(renderer)
        del self._children[orig_children_len:]

    def clear(self):
        super().clear()
        for ax in self.parasites:
            ax.clear()

    def pick(self, mouseevent):
        super().pick(mouseevent)
        # Also pass pick events on to parasite axes and, in turn, their
        # children (cf. ParasiteAxesBase.pick)
        for a in self.parasites:
            a.pick(mouseevent)

    def twinx(self, axes_class=None):
        """
        Create a twin of Axes with a shared x-axis but independent y-axis.

        The y-axis of self will have ticks on the left and the returned axes
        will have ticks on the right.
        """
        ax = self._add_twin_axes(axes_class, sharex=self)
        self.axis["right"].set_visible(False)
        ax.axis["right"].set_visible(True)
        ax.axis["left", "top", "bottom"].set_visible(False)
        return ax

    def twiny(self, axes_class=None):
        """
        Create a twin of Axes with a shared y-axis but independent x-axis.

        The x-axis of self will have ticks on the bottom and the returned axes
        will have ticks on the top.
        """
        ax = self._add_twin_axes(axes_class, sharey=self)
        self.axis["top"].set_visible(False)
        ax.axis["top"].set_visible(True)
        ax.axis["left", "right", "bottom"].set_visible(False)
        return ax

    def twin(self, aux_trans=None, axes_class=None):
        """
        Create a twin of Axes with no shared axis.

        While self will have ticks on the left and bottom axis, the returned
        axes will have ticks on the top and right axis.
        """
        if aux_trans is None:
            aux_trans = mtransforms.IdentityTransform()
        ax = self._add_twin_axes(
            axes_class, aux_transform=aux_trans, viewlim_mode="transform")
        self.axis["top", "right"].set_visible(False)
        ax.axis["top", "right"].set_visible(True)
        ax.axis["left", "bottom"].set_visible(False)
        return ax

    def _add_twin_axes(self, axes_class, **kwargs):
        """
        Helper for `.twinx`/`.twiny`/`.twin`.

        *kwargs* are forwarded to the parasite axes constructor.
        """
        if axes_class is None:
            axes_class = self._base_axes_class
        ax = parasite_axes_class_factory(axes_class)(self, **kwargs)
        self.parasites.append(ax)
        ax._remove_method = self._remove_any_twin
        return ax

    def _remove_any_twin(self, ax):
        self.parasites.remove(ax)
        restore = ["top", "right"]
        if ax._sharex:
            restore.remove("top")
        if ax._sharey:
            restore.remove("right")
        self.axis[tuple(restore)].set_visible(True)
        self.axis[tuple(restore)].toggle(ticklabels=False, label=False)

    def get_tightbbox(self, renderer=None, *, call_axes_locator=True,
                      bbox_extra_artists=None):
        bbs = [
            *[ax.get_tightbbox(renderer, call_axes_locator=call_axes_locator)
              for ax in self.parasites],
            super().get_tightbbox(renderer,
                                  call_axes_locator=call_axes_locator,
                                  bbox_extra_artists=bbox_extra_artists)]
        return Bbox.union([b for b in bbs if b.width != 0 or b.height != 0])


host_axes_class_factory = host_subplot_class_factory = \
    cbook._make_class_factory(HostAxesBase, "{}HostAxes", "_base_axes_class")
HostAxes = SubplotHost = host_axes_class_factory(Axes)


def host_axes(*args, axes_class=Axes, figure=None, **kwargs):
    """
    Create axes that can act as a hosts to parasitic axes.

    Parameters
    ----------
    figure : `~matplotlib.figure.Figure`
        Figure to which the axes will be added. Defaults to the current figure
        `.pyplot.gcf()`.

    *args, **kwargs
        Will be passed on to the underlying `~.axes.Axes` object creation.
    """
    import matplotlib.pyplot as plt
    host_axes_class = host_axes_class_factory(axes_class)
    if figure is None:
        figure = plt.gcf()
    ax = host_axes_class(figure, *args, **kwargs)
    figure.add_axes(ax)
    return ax


host_subplot = host_axes

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\tree.py ===
from typing import Iterator, List, Optional, Tuple

from ._loop import loop_first, loop_last
from .console import Console, ConsoleOptions, RenderableType, RenderResult
from .jupyter import JupyterMixin
from .measure import Measurement
from .segment import Segment
from .style import Style, StyleStack, StyleType
from .styled import Styled

GuideType = Tuple[str, str, str, str]


class Tree(JupyterMixin):
    """A renderable for a tree structure.

    Attributes:
        ASCII_GUIDES (GuideType): Guide lines used when Console.ascii_only is True.
        TREE_GUIDES (List[GuideType, GuideType, GuideType]): Default guide lines.

    Args:
        label (RenderableType): The renderable or str for the tree label.
        style (StyleType, optional): Style of this tree. Defaults to "tree".
        guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
        expanded (bool, optional): Also display children. Defaults to True.
        highlight (bool, optional): Highlight renderable (if str). Defaults to False.
        hide_root (bool, optional): Hide the root node. Defaults to False.
    """

    ASCII_GUIDES = ("    ", "|   ", "+-- ", "`-- ")
    TREE_GUIDES = [
        ("    ", "│   ", "├── ", "└── "),
        ("    ", "┃   ", "┣━━ ", "┗━━ "),
        ("    ", "║   ", "╠══ ", "╚══ "),
    ]

    def __init__(
        self,
        label: RenderableType,
        *,
        style: StyleType = "tree",
        guide_style: StyleType = "tree.line",
        expanded: bool = True,
        highlight: bool = False,
        hide_root: bool = False,
    ) -> None:
        self.label = label
        self.style = style
        self.guide_style = guide_style
        self.children: List[Tree] = []
        self.expanded = expanded
        self.highlight = highlight
        self.hide_root = hide_root

    def add(
        self,
        label: RenderableType,
        *,
        style: Optional[StyleType] = None,
        guide_style: Optional[StyleType] = None,
        expanded: bool = True,
        highlight: Optional[bool] = False,
    ) -> "Tree":
        """Add a child tree.

        Args:
            label (RenderableType): The renderable or str for the tree label.
            style (StyleType, optional): Style of this tree. Defaults to "tree".
            guide_style (StyleType, optional): Style of the guide lines. Defaults to "tree.line".
            expanded (bool, optional): Also display children. Defaults to True.
            highlight (Optional[bool], optional): Highlight renderable (if str). Defaults to False.

        Returns:
            Tree: A new child Tree, which may be further modified.
        """
        node = Tree(
            label,
            style=self.style if style is None else style,
            guide_style=self.guide_style if guide_style is None else guide_style,
            expanded=expanded,
            highlight=self.highlight if highlight is None else highlight,
        )
        self.children.append(node)
        return node

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        stack: List[Iterator[Tuple[bool, Tree]]] = []
        pop = stack.pop
        push = stack.append
        new_line = Segment.line()

        get_style = console.get_style
        null_style = Style.null()
        guide_style = get_style(self.guide_style, default="") or null_style
        SPACE, CONTINUE, FORK, END = range(4)

        _Segment = Segment

        def make_guide(index: int, style: Style) -> Segment:
            """Make a Segment for a level of the guide lines."""
            if options.ascii_only:
                line = self.ASCII_GUIDES[index]
            else:
                guide = 1 if style.bold else (2 if style.underline2 else 0)
                line = self.TREE_GUIDES[0 if options.legacy_windows else guide][index]
            return _Segment(line, style)

        levels: List[Segment] = [make_guide(CONTINUE, guide_style)]
        push(iter(loop_last([self])))

        guide_style_stack = StyleStack(get_style(self.guide_style))
        style_stack = StyleStack(get_style(self.style))
        remove_guide_styles = Style(bold=False, underline2=False)

        depth = 0

        while stack:
            stack_node = pop()
            try:
                last, node = next(stack_node)
            except StopIteration:
                levels.pop()
                if levels:
                    guide_style = levels[-1].style or null_style
                    levels[-1] = make_guide(FORK, guide_style)
                    guide_style_stack.pop()
                    style_stack.pop()
                continue
            push(stack_node)
            if last:
                levels[-1] = make_guide(END, levels[-1].style or null_style)

            guide_style = guide_style_stack.current + get_style(node.guide_style)
            style = style_stack.current + get_style(node.style)
            prefix = levels[(2 if self.hide_root else 1) :]
            renderable_lines = console.render_lines(
                Styled(node.label, style),
                options.update(
                    width=options.max_width
                    - sum(level.cell_length for level in prefix),
                    highlight=self.highlight,
                    height=None,
                ),
                pad=options.justify is not None,
            )

            if not (depth == 0 and self.hide_root):
                for first, line in loop_first(renderable_lines):
                    if prefix:
                        yield from _Segment.apply_style(
                            prefix,
                            style.background_style,
                            post_style=remove_guide_styles,
                        )
                    yield from line
                    yield new_line
                    if first and prefix:
                        prefix[-1] = make_guide(
                            SPACE if last else CONTINUE, prefix[-1].style or null_style
                        )

            if node.expanded and node.children:
                levels[-1] = make_guide(
                    SPACE if last else CONTINUE, levels[-1].style or null_style
                )
                levels.append(
                    make_guide(END if len(node.children) == 1 else FORK, guide_style)
                )
                style_stack.push(get_style(node.style))
                guide_style_stack.push(get_style(node.guide_style))
                push(iter(loop_last(node.children)))
                depth += 1

    def __rich_measure__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "Measurement":
        stack: List[Iterator[Tree]] = [iter([self])]
        pop = stack.pop
        push = stack.append
        minimum = 0
        maximum = 0
        measure = Measurement.get
        level = 0
        while stack:
            iter_tree = pop()
            try:
                tree = next(iter_tree)
            except StopIteration:
                level -= 1
                continue
            push(iter_tree)
            min_measure, max_measure = measure(console, options, tree.label)
            indent = level * 4
            minimum = max(min_measure + indent, minimum)
            maximum = max(max_measure + indent, maximum)
            if tree.expanded and tree.children:
                push(iter(tree.children))
                level += 1
        return Measurement(minimum, maximum)


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Group
    from pip._vendor.rich.markdown import Markdown
    from pip._vendor.rich.panel import Panel
    from pip._vendor.rich.syntax import Syntax
    from pip._vendor.rich.table import Table

    table = Table(row_styles=["", "dim"])

    table.add_column("Released", style="cyan", no_wrap=True)
    table.add_column("Title", style="magenta")
    table.add_column("Box Office", justify="right", style="green")

    table.add_row("Dec 20, 2019", "Star Wars: The Rise of Skywalker", "$952,110,690")
    table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
    table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
    table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

    code = """\
class Segment(NamedTuple):
    text: str = ""
    style: Optional[Style] = None
    is_control: bool = False
"""
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)

    markdown = Markdown(
        """\
### example.md
> Hello, World!
>
> Markdown _all_ the things
"""
    )

    root = Tree("🌲 [b green]Rich Tree", highlight=True, hide_root=True)

    node = root.add(":file_folder: Renderables", guide_style="red")
    simple_node = node.add(":file_folder: [bold yellow]Atomic", guide_style="uu green")
    simple_node.add(Group("📄 Syntax", syntax))
    simple_node.add(Group("📄 Markdown", Panel(markdown, border_style="green")))

    containers_node = node.add(
        ":file_folder: [bold magenta]Containers", guide_style="bold magenta"
    )
    containers_node.expanded = True
    panel = Panel.fit("Just a panel", border_style="red")
    containers_node.add(Group("📄 Panels", panel))

    containers_node.add(Group("📄 [b magenta]Table", table))

    console = Console()

    console.print(root)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\bindings\basic.py ===
# pylint: disable=function-redefined
from __future__ import annotations

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import (
    Condition,
    emacs_insert_mode,
    has_selection,
    in_paste_mode,
    is_multiline,
    vi_insert_mode,
)
from prompt_toolkit.key_binding.key_processor import KeyPress, KeyPressEvent
from prompt_toolkit.keys import Keys

from ..key_bindings import KeyBindings
from .named_commands import get_by_name

__all__ = [
    "load_basic_bindings",
]

E = KeyPressEvent


def if_no_repeat(event: E) -> bool:
    """Callable that returns True when the previous event was delivered to
    another handler."""
    return not event.is_repeat


@Condition
def has_text_before_cursor() -> bool:
    return bool(get_app().current_buffer.text)


@Condition
def in_quoted_insert() -> bool:
    return get_app().quoted_insert


def load_basic_bindings() -> KeyBindings:
    key_bindings = KeyBindings()
    insert_mode = vi_insert_mode | emacs_insert_mode
    handle = key_bindings.add

    @handle("c-a")
    @handle("c-b")
    @handle("c-c")
    @handle("c-d")
    @handle("c-e")
    @handle("c-f")
    @handle("c-g")
    @handle("c-h")
    @handle("c-i")
    @handle("c-j")
    @handle("c-k")
    @handle("c-l")
    @handle("c-m")
    @handle("c-n")
    @handle("c-o")
    @handle("c-p")
    @handle("c-q")
    @handle("c-r")
    @handle("c-s")
    @handle("c-t")
    @handle("c-u")
    @handle("c-v")
    @handle("c-w")
    @handle("c-x")
    @handle("c-y")
    @handle("c-z")
    @handle("f1")
    @handle("f2")
    @handle("f3")
    @handle("f4")
    @handle("f5")
    @handle("f6")
    @handle("f7")
    @handle("f8")
    @handle("f9")
    @handle("f10")
    @handle("f11")
    @handle("f12")
    @handle("f13")
    @handle("f14")
    @handle("f15")
    @handle("f16")
    @handle("f17")
    @handle("f18")
    @handle("f19")
    @handle("f20")
    @handle("f21")
    @handle("f22")
    @handle("f23")
    @handle("f24")
    @handle("c-@")  # Also c-space.
    @handle("c-\\")
    @handle("c-]")
    @handle("c-^")
    @handle("c-_")
    @handle("backspace")
    @handle("up")
    @handle("down")
    @handle("right")
    @handle("left")
    @handle("s-up")
    @handle("s-down")
    @handle("s-right")
    @handle("s-left")
    @handle("home")
    @handle("end")
    @handle("s-home")
    @handle("s-end")
    @handle("delete")
    @handle("s-delete")
    @handle("c-delete")
    @handle("pageup")
    @handle("pagedown")
    @handle("s-tab")
    @handle("tab")
    @handle("c-s-left")
    @handle("c-s-right")
    @handle("c-s-home")
    @handle("c-s-end")
    @handle("c-left")
    @handle("c-right")
    @handle("c-up")
    @handle("c-down")
    @handle("c-home")
    @handle("c-end")
    @handle("insert")
    @handle("s-insert")
    @handle("c-insert")
    @handle("<sigint>")
    @handle(Keys.Ignore)
    def _ignore(event: E) -> None:
        """
        First, for any of these keys, Don't do anything by default. Also don't
        catch them in the 'Any' handler which will insert them as data.

        If people want to insert these characters as a literal, they can always
        do by doing a quoted insert. (ControlQ in emacs mode, ControlV in Vi
        mode.)
        """
        pass

    # Readline-style bindings.
    handle("home")(get_by_name("beginning-of-line"))
    handle("end")(get_by_name("end-of-line"))
    handle("left")(get_by_name("backward-char"))
    handle("right")(get_by_name("forward-char"))
    handle("c-up")(get_by_name("previous-history"))
    handle("c-down")(get_by_name("next-history"))
    handle("c-l")(get_by_name("clear-screen"))

    handle("c-k", filter=insert_mode)(get_by_name("kill-line"))
    handle("c-u", filter=insert_mode)(get_by_name("unix-line-discard"))
    handle("backspace", filter=insert_mode, save_before=if_no_repeat)(
        get_by_name("backward-delete-char")
    )
    handle("delete", filter=insert_mode, save_before=if_no_repeat)(
        get_by_name("delete-char")
    )
    handle("c-delete", filter=insert_mode, save_before=if_no_repeat)(
        get_by_name("delete-char")
    )
    handle(Keys.Any, filter=insert_mode, save_before=if_no_repeat)(
        get_by_name("self-insert")
    )
    handle("c-t", filter=insert_mode)(get_by_name("transpose-chars"))
    handle("c-i", filter=insert_mode)(get_by_name("menu-complete"))
    handle("s-tab", filter=insert_mode)(get_by_name("menu-complete-backward"))

    # Control-W should delete, using whitespace as separator, while M-Del
    # should delete using [^a-zA-Z0-9] as a boundary.
    handle("c-w", filter=insert_mode)(get_by_name("unix-word-rubout"))

    handle("pageup", filter=~has_selection)(get_by_name("previous-history"))
    handle("pagedown", filter=~has_selection)(get_by_name("next-history"))

    # CTRL keys.

    handle("c-d", filter=has_text_before_cursor & insert_mode)(
        get_by_name("delete-char")
    )

    @handle("enter", filter=insert_mode & is_multiline)
    def _newline(event: E) -> None:
        """
        Newline (in case of multiline input.
        """
        event.current_buffer.newline(copy_margin=not in_paste_mode())

    @handle("c-j")
    def _newline2(event: E) -> None:
        r"""
        By default, handle \n as if it were a \r (enter).
        (It appears that some terminals send \n instead of \r when pressing
        enter. - at least the Linux subsystem for Windows.)
        """
        event.key_processor.feed(KeyPress(Keys.ControlM, "\r"), first=True)

    # Delete the word before the cursor.

    @handle("up")
    def _go_up(event: E) -> None:
        event.current_buffer.auto_up(count=event.arg)

    @handle("down")
    def _go_down(event: E) -> None:
        event.current_buffer.auto_down(count=event.arg)

    @handle("delete", filter=has_selection)
    def _cut(event: E) -> None:
        data = event.current_buffer.cut_selection()
        event.app.clipboard.set_data(data)

    # Global bindings.

    @handle("c-z")
    def _insert_ctrl_z(event: E) -> None:
        """
        By default, control-Z should literally insert Ctrl-Z.
        (Ansi Ctrl-Z, code 26 in MSDOS means End-Of-File.
        In a Python REPL for instance, it's possible to type
        Control-Z followed by enter to quit.)

        When the system bindings are loaded and suspend-to-background is
        supported, that will override this binding.
        """
        event.current_buffer.insert_text(event.data)

    @handle(Keys.BracketedPaste)
    def _paste(event: E) -> None:
        """
        Pasting from clipboard.
        """
        data = event.data

        # Be sure to use \n as line ending.
        # Some terminals (Like iTerm2) seem to paste \r\n line endings in a
        # bracketed paste. See: https://github.com/ipython/ipython/issues/9737
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")

        event.current_buffer.insert_text(data)

    @handle(Keys.Any, filter=in_quoted_insert, eager=True)
    def _insert_text(event: E) -> None:
        """
        Handle quoted insert.
        """
        event.current_buffer.insert_text(event.data, overwrite=False)
        event.app.quoted_insert = False

    return key_bindings

# === NexusCore/archive\app.py ===
# --- FILE: src/app.py ---
# メインアプリケーション: FlaskサーバーとGradio UI

import os
import threading
from pathlib import Path

import gradio as gr
from flask import Flask, jsonify, request

from dotenv import load_dotenv

# --- ローカルモジュールのインポート ---
from .git_manager import GitManager, get_file_diff
from .ai_assistant import AIAssistant
from .agents.guardian_agent import GuardianAgent

# --- 初期化 ---
load_dotenv()

# ディレクトリ構造の定義
ROOT = Path(__file__).parent.parent.resolve()
SANDBOX_REPO_PATH = ROOT / "sandbox_repo"

# モジュールのインスタンス化
if not SANDBOX_REPO_PATH.exists():
    SANDBOX_REPO_PATH.mkdir()

if not (SANDBOX_REPO_PATH / ".git").exists():
    print("⚠️ Gitリポジトリが初期化されていません。")
    git_manager = GitManager.initialize_repo(SANDBOX_REPO_PATH)
    print(f"✅ '{SANDBOX_REPO_PATH}' にGitリポジトリを初期化しました。")
else:
    git_manager = GitManager(repo_path=SANDBOX_REPO_PATH)

ai_assistant = AIAssistant(api_key=os.getenv("OPENAI_API_KEY"))

# --- Flaskアプリケーション ---
flask_app = Flask(__name__)

@flask_app.route("/api/status", methods=['GET'])
def get_status():
    """リポジトリの現在の状態を返すAPI"""
    history = git_manager.get_history(limit=10)
    return jsonify({
        "repo_path": str(git_manager.repo_path),
        "current_branch": git_manager.get_current_branch(),
        "recent_history": history
    })

# --- Gradio UIのためのバックエンド関数 ---

def get_history_and_files():
    """UI表示用に履歴とファイルリストを取得"""
    history = git_manager.get_history_for_ui()
    
    if history.empty:
        print("🚀 初回起動シーケンスを開始します。")
        app_dir = SANDBOX_REPO_PATH / "app"
        tests_dir = SANDBOX_REPO_PATH / "tests"
        app_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "__init__.py").touch()
        (SANDBOX_REPO_PATH / "pyproject.toml").write_text("""[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "--cov"
[tool.coverage.run]
source = ["app"]
omit = ["*/__init__.py"]
[tool.coverage.report]
fail_under = 90
""", encoding='utf-8')
        git_manager.write_file_and_commit("app/main.py", "# Add your main code here", "feat: Initial commit with app/main.py")
        git_manager.write_file_and_commit("tests/test_main.py", "# Add tests for main.py here", "feat: Initial commit with tests/test_main.py")
        history = git_manager.get_history_for_ui()
        
    files = git_manager.get_tracked_files()
    return history, files

def run_tests_on_current_code():
    """現在の作業ディレクトリのコードに対してテストを実行"""
    return git_manager.run_pytest(project_path=str(SANDBOX_REPO_PATH))

def propose_ai_fix(target_file, user_instruction, history_df):
    """AIにコードの修正案を提案させる"""
    latest_commit_hash = history_df.iloc[0]['commit'] if not history_df.empty else 'HEAD'
    
    current_code = git_manager.read_file(target_file, commit_hash=latest_commit_hash)
    test_file_path = "tests/test_" + os.path.basename(target_file)
    test_code = git_manager.read_file(test_file_path, commit_hash=latest_commit_hash)
    test_results = git_manager.run_pytest(project_path=str(SANDBOX_REPO_PATH))

    ai_response = ai_assistant.generate_fix(
        target_file=target_file,
        current_code=current_code,
        test_code=test_code,
        test_results=test_results,
        user_instruction=user_instruction
    )
    
    suggested_code = ai_response.get("code", "")
    summary = ai_response.get("summary", "要約の生成に失敗しました。")
    diff_html = get_file_diff(current_code, suggested_code, target_file)
    
    return summary, suggested_code, diff_html, gr.update(interactive=True)

def accept_ai_suggestion(target_file, suggested_code, summary):
    """AIの提案を受け入れ、コミットする前にガーディアンAIのレビューを実行する"""
    if not suggested_code:
        return "提案されたコードが空のため、コミットできませんでした。", gr.update()

    current_code = git_manager.read_file(target_file)
    git_manager.write_file(target_file, suggested_code)

    constitution = {
        'min_pylint_score': 7.0,
        'min_coverage_percent': 90.0,
    }
    
    test_file_path = "tests/test_" + os.path.basename(target_file)

    guardian = GuardianAgent(constitution=constitution)
    
    # ✅ 修正点: 不要な 'project_path' 引数を削除
    approved, report = guardian.review_changes(
        code_file_path=target_file,
        test_file_path=test_file_path
    )
    
    if approved:
        commit_message = f"AI提案の適用 (Guardian承認済): {summary}"
        git_manager.commit(commit_message)
        return f"✅ ガーディアンAIが承認。新バージョンをコミットしました。\n\n{report}", git_manager.get_history_for_ui()
    else:
        git_manager.write_file(target_file, current_code)
        return f"❌ ガーディアンAIが却下。コミットは行われませんでした。\n\n{report}", gr.update()

def revert_to_version(commit_hash):
    """指定されたバージョンにロールバックする"""
    if not commit_hash or len(commit_hash) < 7:
        return "コミットハッシュが選択されていません。", gr.update()
    
    try:
        full_hash = git_manager.repo.git.rev_parse(commit_hash)
        git_manager.checkout(full_hash)
        files = git_manager.get_tracked_files()
        return f"✅ バージョン {commit_hash[:7]} にロールバックしました。", gr.update(choices=files)
    except Exception as e:
        return f"❌ ロールバック中にエラーが発生しました: {e}", gr.update()

# --- Gradio UIの構築 ---
def create_gradio_app():
    with gr.Blocks(theme=gr.themes.Soft(), css="""
        .diff-container { padding: 10px; border-radius: 5px; background-color: #f0f0f0; font-family: monospace; white-space: pre-wrap; }
        .diff-add { background-color: #e6ffed; }
        .diff-remove { background-color: #ffebe9; }
    """) as app:
        gr.Markdown("# 🚀 究極のAIアシスト型バージョン管理システム")
        
        ai_suggestion_code = gr.State("")
        ai_suggestion_summary = gr.State("")
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 📜 バージョン履歴")
                history_table = gr.DataFrame(headers=["commit", "author", "date", "message"], interactive=False, datatype=["str", "str", "str", "str"])
                
                with gr.Accordion("🔁 ロールバック", open=False):
                    selected_commit = gr.Dropdown(label="戻したいバージョンを選択", choices=[])
                    rollback_btn = gr.Button("このバージョンに戻す")

            with gr.Column(scale=3):
                gr.Markdown("### 🤖 AIによるコード修正")
                target_file_dropdown = gr.Dropdown(label="修正対象ファイル", interactive=True)
                user_instruction_textbox = gr.Textbox(label="追加の指示・修正したい内容", lines=3, placeholder="例: バグを修正して、パフォーマンスを改善してください。")
                propose_fix_btn = gr.Button("🤖 AIに修正案を提案させる", variant="primary")
                
                with gr.Accordion("🔍 AIの提案内容", open=True):
                    ai_summary_output = gr.Markdown(label="AIによる修正の要約")
                    diff_output = gr.HTML(label="差分プレビュー (緑: 追加, 赤: 削除)")

                with gr.Row():
                    accept_btn = gr.Button("✅ この修正を承認する", variant="primary", interactive=False)

            with gr.Column(scale=2):
                gr.Markdown("### 🧪 テスト実行")
                run_test_btn = gr.Button("現在のコードでテストを実行")
                test_result_output = gr.Textbox(label="📊 テスト結果", lines=10, interactive=False)
                
                with gr.Accordion("📄 ファイル内容の確認", open=False):
                    file_content_display = gr.Code(label="ファイル内容", language="python", interactive=False)

        def initial_load():
            history, files = get_history_and_files()
            commit_choices = history['commit'].tolist() if not history.empty else []
            return history, gr.update(choices=files, value=files[0] if files else None), gr.update(choices=commit_choices)
        
        app.load(initial_load, outputs=[history_table, target_file_dropdown, selected_commit])

        propose_fix_btn.click(
            fn=propose_ai_fix,
            inputs=[target_file_dropdown, user_instruction_textbox, history_table],
            outputs=[ai_summary_output, ai_suggestion_code, diff_output, accept_btn],
            show_progress="full"
        ).then(
            fn=lambda summary, code: (summary, code),
            inputs=[ai_summary_output, ai_suggestion_code],
            outputs=[ai_suggestion_summary, ai_suggestion_code]
        )

        accept_btn.click(
            fn=accept_ai_suggestion,
            inputs=[target_file_dropdown, ai_suggestion_code, ai_suggestion_summary],
            outputs=[test_result_output, history_table],
            show_progress="full"
        ).then(
            lambda: ("", "", "", gr.update(interactive=False)),
            outputs=[ai_summary_output, diff_output, ai_suggestion_code, accept_btn]
        )

        run_test_btn.click(fn=run_tests_on_current_code, outputs=test_result_output)
        
        rollback_btn.click(
            fn=revert_to_version,
            inputs=[selected_commit],
            outputs=[test_result_output, target_file_dropdown]
        ).then(
            fn=initial_load, 
            outputs=[history_table, target_file_dropdown, selected_commit]
        )
        
        def show_file_content(filepath):
            if not filepath: return ""
            return git_manager.read_file(filepath, "HEAD")

        target_file_dropdown.change(
            fn=show_file_content,
            inputs=[target_file_dropdown],
            outputs=file_content_display
        )

    return app

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    gradio_app = create_gradio_app()
    
    threading.Thread(
        target=lambda: gradio_app.launch(server_name="0.0.0.0", server_port=7860, quiet=True),
        daemon=True
    ).start()
    print("✅ Gradio UIが http://127.0.0.1:7860 で起動しました。")

    print("✅ Flask APIサーバーが http://127.0.0.1:5000 で起動しました。")
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\operations\freeze.py ===
import collections
import logging
import os
from dataclasses import dataclass, field
from typing import Container, Dict, Generator, Iterable, List, NamedTuple, Optional, Set

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import InvalidVersion

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.metadata import BaseDistribution, get_environment
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._internal.req.req_file import COMMENT_RE
from pip._internal.utils.direct_url_helpers import direct_url_as_pep440_direct_reference

logger = logging.getLogger(__name__)


class _EditableInfo(NamedTuple):
    requirement: str
    comments: List[str]


def freeze(
    requirement: Optional[List[str]] = None,
    local_only: bool = False,
    user_only: bool = False,
    paths: Optional[List[str]] = None,
    isolated: bool = False,
    exclude_editable: bool = False,
    skip: Container[str] = (),
) -> Generator[str, None, None]:
    installations: Dict[str, FrozenRequirement] = {}

    dists = get_environment(paths).iter_installed_distributions(
        local_only=local_only,
        skip=(),
        user_only=user_only,
    )
    for dist in dists:
        req = FrozenRequirement.from_dist(dist)
        if exclude_editable and req.editable:
            continue
        installations[req.canonical_name] = req

    if requirement:
        # the options that don't get turned into an InstallRequirement
        # should only be emitted once, even if the same option is in multiple
        # requirements files, so we need to keep track of what has been emitted
        # so that we don't emit it again if it's seen again
        emitted_options: Set[str] = set()
        # keep track of which files a requirement is in so that we can
        # give an accurate warning if a requirement appears multiple times.
        req_files: Dict[str, List[str]] = collections.defaultdict(list)
        for req_file_path in requirement:
            with open(req_file_path) as req_file:
                for line in req_file:
                    if (
                        not line.strip()
                        or line.strip().startswith("#")
                        or line.startswith(
                            (
                                "-r",
                                "--requirement",
                                "-f",
                                "--find-links",
                                "-i",
                                "--index-url",
                                "--pre",
                                "--trusted-host",
                                "--process-dependency-links",
                                "--extra-index-url",
                                "--use-feature",
                            )
                        )
                    ):
                        line = line.rstrip()
                        if line not in emitted_options:
                            emitted_options.add(line)
                            yield line
                        continue

                    if line.startswith("-e") or line.startswith("--editable"):
                        if line.startswith("-e"):
                            line = line[2:].strip()
                        else:
                            line = line[len("--editable") :].strip().lstrip("=")
                        line_req = install_req_from_editable(
                            line,
                            isolated=isolated,
                        )
                    else:
                        line_req = install_req_from_line(
                            COMMENT_RE.sub("", line).strip(),
                            isolated=isolated,
                        )

                    if not line_req.name:
                        logger.info(
                            "Skipping line in requirement file [%s] because "
                            "it's not clear what it would install: %s",
                            req_file_path,
                            line.strip(),
                        )
                        logger.info(
                            "  (add #egg=PackageName to the URL to avoid"
                            " this warning)"
                        )
                    else:
                        line_req_canonical_name = canonicalize_name(line_req.name)
                        if line_req_canonical_name not in installations:
                            # either it's not installed, or it is installed
                            # but has been processed already
                            if not req_files[line_req.name]:
                                logger.warning(
                                    "Requirement file [%s] contains %s, but "
                                    "package %r is not installed",
                                    req_file_path,
                                    COMMENT_RE.sub("", line).strip(),
                                    line_req.name,
                                )
                            else:
                                req_files[line_req.name].append(req_file_path)
                        else:
                            yield str(installations[line_req_canonical_name]).rstrip()
                            del installations[line_req_canonical_name]
                            req_files[line_req.name].append(req_file_path)

        # Warn about requirements that were included multiple times (in a
        # single requirements file or in different requirements files).
        for name, files in req_files.items():
            if len(files) > 1:
                logger.warning(
                    "Requirement %s included multiple times [%s]",
                    name,
                    ", ".join(sorted(set(files))),
                )

        yield ("## The following requirements were added by pip freeze:")
    for installation in sorted(installations.values(), key=lambda x: x.name.lower()):
        if installation.canonical_name not in skip:
            yield str(installation).rstrip()


def _format_as_name_version(dist: BaseDistribution) -> str:
    try:
        dist_version = dist.version
    except InvalidVersion:
        # legacy version
        return f"{dist.raw_name}==={dist.raw_version}"
    else:
        return f"{dist.raw_name}=={dist_version}"


def _get_editable_info(dist: BaseDistribution) -> _EditableInfo:
    """
    Compute and return values (req, comments) for use in
    FrozenRequirement.from_dist().
    """
    editable_project_location = dist.editable_project_location
    assert editable_project_location
    location = os.path.normcase(os.path.abspath(editable_project_location))

    from pip._internal.vcs import RemoteNotFoundError, RemoteNotValidError, vcs

    vcs_backend = vcs.get_backend_for_dir(location)

    if vcs_backend is None:
        display = _format_as_name_version(dist)
        logger.debug(
            'No VCS found for editable requirement "%s" in: %r',
            display,
            location,
        )
        return _EditableInfo(
            requirement=location,
            comments=[f"# Editable install with no version control ({display})"],
        )

    vcs_name = type(vcs_backend).__name__

    try:
        req = vcs_backend.get_src_requirement(location, dist.raw_name)
    except RemoteNotFoundError:
        display = _format_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[f"# Editable {vcs_name} install with no remote ({display})"],
        )
    except RemoteNotValidError as ex:
        display = _format_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[
                f"# Editable {vcs_name} install ({display}) with either a deleted "
                f"local remote or invalid URI:",
                f"# '{ex.url}'",
            ],
        )
    except BadCommand:
        logger.warning(
            "cannot determine version of editable source in %s "
            "(%s command not found in path)",
            location,
            vcs_backend.name,
        )
        return _EditableInfo(requirement=location, comments=[])
    except InstallationError as exc:
        logger.warning("Error when trying to get requirement for VCS system %s", exc)
    else:
        return _EditableInfo(requirement=req, comments=[])

    logger.warning("Could not determine repository location of %s", location)

    return _EditableInfo(
        requirement=location,
        comments=["## !! Could not determine repository location"],
    )


@dataclass(frozen=True)
class FrozenRequirement:
    name: str
    req: str
    editable: bool
    comments: Iterable[str] = field(default_factory=tuple)

    @property
    def canonical_name(self) -> NormalizedName:
        return canonicalize_name(self.name)

    @classmethod
    def from_dist(cls, dist: BaseDistribution) -> "FrozenRequirement":
        editable = dist.editable
        if editable:
            req, comments = _get_editable_info(dist)
        else:
            comments = []
            direct_url = dist.direct_url
            if direct_url:
                # if PEP 610 metadata is present, use it
                req = direct_url_as_pep440_direct_reference(direct_url, dist.raw_name)
            else:
                # name==version requirement
                req = _format_as_name_version(dist)

        return cls(dist.raw_name, req, editable, comments=comments)

    def __str__(self) -> str:
        req = self.req
        if self.editable:
            req = f"-e {req}"
        return "\n".join(list(self.comments) + [str(req)]) + "\n"

# === NexusCore/openenv\Lib\site-packages\jinja2\tests.py ===
"""Built-in template tests used with the ``is`` operator."""

import operator
import typing as t
from collections import abc
from numbers import Number

from .runtime import Undefined
from .utils import pass_environment

if t.TYPE_CHECKING:
    from .environment import Environment


def test_odd(value: int) -> bool:
    """Return true if the variable is odd."""
    return value % 2 == 1


def test_even(value: int) -> bool:
    """Return true if the variable is even."""
    return value % 2 == 0


def test_divisibleby(value: int, num: int) -> bool:
    """Check if a variable is divisible by a number."""
    return value % num == 0


def test_defined(value: t.Any) -> bool:
    """Return true if the variable is defined:

    .. sourcecode:: jinja

        {% if variable is defined %}
            value of variable: {{ variable }}
        {% else %}
            variable is not defined
        {% endif %}

    See the :func:`default` filter for a simple way to set undefined
    variables.
    """
    return not isinstance(value, Undefined)


def test_undefined(value: t.Any) -> bool:
    """Like :func:`defined` but the other way round."""
    return isinstance(value, Undefined)


@pass_environment
def test_filter(env: "Environment", value: str) -> bool:
    """Check if a filter exists by name. Useful if a filter may be
    optionally available.

    .. code-block:: jinja

        {% if 'markdown' is filter %}
            {{ value | markdown }}
        {% else %}
            {{ value }}
        {% endif %}

    .. versionadded:: 3.0
    """
    return value in env.filters


@pass_environment
def test_test(env: "Environment", value: str) -> bool:
    """Check if a test exists by name. Useful if a test may be
    optionally available.

    .. code-block:: jinja

        {% if 'loud' is test %}
            {% if value is loud %}
                {{ value|upper }}
            {% else %}
                {{ value|lower }}
            {% endif %}
        {% else %}
            {{ value }}
        {% endif %}

    .. versionadded:: 3.0
    """
    return value in env.tests


def test_none(value: t.Any) -> bool:
    """Return true if the variable is none."""
    return value is None


def test_boolean(value: t.Any) -> bool:
    """Return true if the object is a boolean value.

    .. versionadded:: 2.11
    """
    return value is True or value is False


def test_false(value: t.Any) -> bool:
    """Return true if the object is False.

    .. versionadded:: 2.11
    """
    return value is False


def test_true(value: t.Any) -> bool:
    """Return true if the object is True.

    .. versionadded:: 2.11
    """
    return value is True


# NOTE: The existing 'number' test matches booleans and floats
def test_integer(value: t.Any) -> bool:
    """Return true if the object is an integer.

    .. versionadded:: 2.11
    """
    return isinstance(value, int) and value is not True and value is not False


# NOTE: The existing 'number' test matches booleans and integers
def test_float(value: t.Any) -> bool:
    """Return true if the object is a float.

    .. versionadded:: 2.11
    """
    return isinstance(value, float)


def test_lower(value: str) -> bool:
    """Return true if the variable is lowercased."""
    return str(value).islower()


def test_upper(value: str) -> bool:
    """Return true if the variable is uppercased."""
    return str(value).isupper()


def test_string(value: t.Any) -> bool:
    """Return true if the object is a string."""
    return isinstance(value, str)


def test_mapping(value: t.Any) -> bool:
    """Return true if the object is a mapping (dict etc.).

    .. versionadded:: 2.6
    """
    return isinstance(value, abc.Mapping)


def test_number(value: t.Any) -> bool:
    """Return true if the variable is a number."""
    return isinstance(value, Number)


def test_sequence(value: t.Any) -> bool:
    """Return true if the variable is a sequence. Sequences are variables
    that are iterable.
    """
    try:
        len(value)
        value.__getitem__  # noqa B018
    except Exception:
        return False

    return True


def test_sameas(value: t.Any, other: t.Any) -> bool:
    """Check if an object points to the same memory address than another
    object:

    .. sourcecode:: jinja

        {% if foo.attribute is sameas false %}
            the foo attribute really is the `False` singleton
        {% endif %}
    """
    return value is other


def test_iterable(value: t.Any) -> bool:
    """Check if it's possible to iterate over an object."""
    try:
        iter(value)
    except TypeError:
        return False

    return True


def test_escaped(value: t.Any) -> bool:
    """Check if the value is escaped."""
    return hasattr(value, "__html__")


def test_in(value: t.Any, seq: t.Container[t.Any]) -> bool:
    """Check if value is in seq.

    .. versionadded:: 2.10
    """
    return value in seq


TESTS = {
    "odd": test_odd,
    "even": test_even,
    "divisibleby": test_divisibleby,
    "defined": test_defined,
    "undefined": test_undefined,
    "filter": test_filter,
    "test": test_test,
    "none": test_none,
    "boolean": test_boolean,
    "false": test_false,
    "true": test_true,
    "integer": test_integer,
    "float": test_float,
    "lower": test_lower,
    "upper": test_upper,
    "string": test_string,
    "mapping": test_mapping,
    "number": test_number,
    "sequence": test_sequence,
    "iterable": test_iterable,
    "callable": callable,
    "sameas": test_sameas,
    "escaped": test_escaped,
    "in": test_in,
    "==": operator.eq,
    "eq": operator.eq,
    "equalto": operator.eq,
    "!=": operator.ne,
    "ne": operator.ne,
    ">": operator.gt,
    "gt": operator.gt,
    "greaterthan": operator.gt,
    "ge": operator.ge,
    ">=": operator.ge,
    "<": operator.lt,
    "lt": operator.lt,
    "lessthan": operator.lt,
    "<=": operator.le,
    "le": operator.le,
}

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_io.py ===
from _pydevd_bundle.pydevd_constants import ForkSafeLock, get_global_debugger
import os
import sys
from contextlib import contextmanager


class IORedirector:
    """
    This class works to wrap a stream (stdout/stderr) with an additional redirect.
    """

    def __init__(self, original, new_redirect, wrap_buffer=False):
        """
        :param stream original:
            The stream to be wrapped (usually stdout/stderr, but could be None).

        :param stream new_redirect:
            Usually IOBuf (below).

        :param bool wrap_buffer:
            Whether to create a buffer attribute (needed to mimick python 3 s
            tdout/stderr which has a buffer to write binary data).
        """
        self._lock = ForkSafeLock(rlock=True)
        self._writing = False
        self._redirect_to = (original, new_redirect)
        if wrap_buffer and hasattr(original, "buffer"):
            self.buffer = IORedirector(original.buffer, new_redirect.buffer, False)

    def write(self, s):
        # Note that writing to the original stream may fail for some reasons
        # (such as trying to write something that's not a string or having it closed).
        with self._lock:
            if self._writing:
                return
            self._writing = True
            try:
                for r in self._redirect_to:
                    if hasattr(r, "write"):
                        r.write(s)
            finally:
                self._writing = False

    def isatty(self):
        for r in self._redirect_to:
            if hasattr(r, "isatty"):
                return r.isatty()
        return False

    def flush(self):
        for r in self._redirect_to:
            if hasattr(r, "flush"):
                r.flush()

    def __getattr__(self, name):
        for r in self._redirect_to:
            if hasattr(r, name):
                return getattr(r, name)
        raise AttributeError(name)


class RedirectToPyDBIoMessages(object):
    def __init__(self, out_ctx, wrap_stream, wrap_buffer, on_write=None):
        """
        :param out_ctx:
            1=stdout and 2=stderr

        :param wrap_stream:
            Either sys.stdout or sys.stderr.

        :param bool wrap_buffer:
            If True the buffer attribute (which wraps writing bytes) should be
            wrapped.

        :param callable(str) on_write:
            May be a custom callable to be called when to write something.
            If not passed the default implementation will create an io message
            and send it through the debugger.
        """
        encoding = getattr(wrap_stream, "encoding", None)
        if not encoding:
            encoding = os.environ.get("PYTHONIOENCODING", "utf-8")
        self.encoding = encoding
        self._out_ctx = out_ctx
        if wrap_buffer:
            self.buffer = RedirectToPyDBIoMessages(out_ctx, wrap_stream, wrap_buffer=False, on_write=on_write)
        self._on_write = on_write

    def get_pydb(self):
        # Note: separate method for mocking on tests.
        return get_global_debugger()

    def flush(self):
        pass  # no-op here

    def write(self, s):
        if self._on_write is not None:
            self._on_write(s)
            return

        if s:
            # Need s in str
            if isinstance(s, bytes):
                s = s.decode(self.encoding, errors="replace")

            py_db = self.get_pydb()
            if py_db is not None:
                # Note that the actual message contents will be a xml with utf-8, although
                # the entry is str on py3 and bytes on py2.
                cmd = py_db.cmd_factory.make_io_message(s, self._out_ctx)
                if py_db.writer is not None:
                    py_db.writer.add_command(cmd)


class IOBuf:
    """This class works as a replacement for stdio and stderr.
    It is a buffer and when its contents are requested, it will erase what
    it has so far so that the next return will not return the same contents again.
    """

    def __init__(self):
        self.buflist = []
        import os

        self.encoding = os.environ.get("PYTHONIOENCODING", "utf-8")

    def getvalue(self):
        b = self.buflist
        self.buflist = []  # clear it
        return "".join(b)  # bytes on py2, str on py3.

    def write(self, s):
        if isinstance(s, bytes):
            s = s.decode(self.encoding, errors="replace")
        self.buflist.append(s)

    def isatty(self):
        return False

    def flush(self):
        pass

    def empty(self):
        return len(self.buflist) == 0


class _RedirectInfo(object):
    def __init__(self, original, redirect_to):
        self.original = original
        self.redirect_to = redirect_to


class _RedirectionsHolder:
    _lock = ForkSafeLock(rlock=True)
    _stack_stdout = []
    _stack_stderr = []

    _pydevd_stdout_redirect_ = None
    _pydevd_stderr_redirect_ = None


def start_redirect(keep_original_redirection=False, std="stdout", redirect_to=None):
    """
    @param std: 'stdout', 'stderr', or 'both'
    """
    with _RedirectionsHolder._lock:
        if redirect_to is None:
            redirect_to = IOBuf()

        if std == "both":
            config_stds = ["stdout", "stderr"]
        else:
            config_stds = [std]

        for std in config_stds:
            original = getattr(sys, std)
            stack = getattr(_RedirectionsHolder, "_stack_%s" % std)

            if keep_original_redirection:
                wrap_buffer = True if hasattr(redirect_to, "buffer") else False
                new_std_instance = IORedirector(getattr(sys, std), redirect_to, wrap_buffer=wrap_buffer)
                setattr(sys, std, new_std_instance)
            else:
                new_std_instance = redirect_to
                setattr(sys, std, redirect_to)

            stack.append(_RedirectInfo(original, new_std_instance))

        return redirect_to


def end_redirect(std="stdout"):
    with _RedirectionsHolder._lock:
        if std == "both":
            config_stds = ["stdout", "stderr"]
        else:
            config_stds = [std]
        for std in config_stds:
            stack = getattr(_RedirectionsHolder, "_stack_%s" % std)
            redirect_info = stack.pop()
            setattr(sys, std, redirect_info.original)


def redirect_stream_to_pydb_io_messages(std):
    """
    :param std:
        'stdout' or 'stderr'
    """
    with _RedirectionsHolder._lock:
        redirect_to_name = "_pydevd_%s_redirect_" % (std,)
        if getattr(_RedirectionsHolder, redirect_to_name) is None:
            wrap_buffer = True
            original = getattr(sys, std)

            redirect_to = RedirectToPyDBIoMessages(1 if std == "stdout" else 2, original, wrap_buffer)
            start_redirect(keep_original_redirection=True, std=std, redirect_to=redirect_to)

            stack = getattr(_RedirectionsHolder, "_stack_%s" % std)
            setattr(_RedirectionsHolder, redirect_to_name, stack[-1])
            return True

        return False


def stop_redirect_stream_to_pydb_io_messages(std):
    """
    :param std:
        'stdout' or 'stderr'
    """
    with _RedirectionsHolder._lock:
        redirect_to_name = "_pydevd_%s_redirect_" % (std,)
        redirect_info = getattr(_RedirectionsHolder, redirect_to_name)
        if redirect_info is not None:  # :type redirect_info: _RedirectInfo
            setattr(_RedirectionsHolder, redirect_to_name, None)

            stack = getattr(_RedirectionsHolder, "_stack_%s" % std)
            prev_info = stack.pop()

            curr = getattr(sys, std)
            if curr is redirect_info.redirect_to:
                setattr(sys, std, redirect_info.original)


@contextmanager
def redirect_stream_to_pydb_io_messages_context():
    with _RedirectionsHolder._lock:
        redirecting = []
        for std in ("stdout", "stderr"):
            if redirect_stream_to_pydb_io_messages(std):
                redirecting.append(std)

        try:
            yield
        finally:
            for std in redirecting:
                stop_redirect_stream_to_pydb_io_messages(std)

# === NexusCore/openenv\Lib\site-packages\interpreter\core\archived_server_2.py ===
# This is a websocket interpreter, TTS and STT disabled.
# It makes a websocket on a port that sends/receives LMC messages in *streaming* format.

### You MUST send a start and end flag with each message! For example: ###

"""
{"role": "user", "type": "message", "start": True})
{"role": "user", "type": "message", "content": "hi"})
{"role": "user", "type": "message", "end": True})
"""

import asyncio
import json

###
# from RealtimeTTS import TextToAudioStream, OpenAIEngine, CoquiEngine
# from RealtimeSTT import AudioToTextRecorder
# from beeper import Beeper
import time
import traceback
from typing import Any, Dict, List

from fastapi import FastAPI, Header, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uvicorn import Config, Server


class Settings(BaseModel):
    auto_run: bool
    custom_instructions: str
    model: str


class AsyncInterpreter:
    def __init__(self, interpreter):
        self.interpreter = interpreter

        # STT
        # self.stt = AudioToTextRecorder(use_microphone=False)
        # self.stt.stop() # It needs this for some reason

        # TTS
        # if self.interpreter.tts == "coqui":
        #     engine = CoquiEngine()
        # elif self.interpreter.tts == "openai":
        #     engine = OpenAIEngine()
        # self.tts = TextToAudioStream(engine)

        # Clock
        # clock()

        # self.beeper = Beeper()

        # Startup sounds
        # self.beeper.beep("Blow")
        # self.tts.feed("Hi, how can I help you?")
        # self.tts.play_async(on_audio_chunk=self.on_tts_chunk, muted=True)

        self._input_queue = asyncio.Queue()  # Queue that .input will shove things into
        self._output_queue = asyncio.Queue()  # Queue to put output chunks into
        self._last_lmc_start_flag = None  # Unix time of last LMC start flag received
        self._in_keyboard_write_block = (
            False  # Tracks whether interpreter is trying to use the keyboard
        )

        # self.loop = asyncio.get_event_loop()

    async def _add_to_queue(self, queue, item):
        await queue.put(item)

    async def clear_queue(self, queue):
        while not queue.empty():
            await queue.get()

    async def clear_input_queue(self):
        await self.clear_queue(self._input_queue)

    async def clear_output_queue(self):
        await self.clear_queue(self._output_queue)

    async def input(self, chunk):
        """
        Expects a chunk in streaming LMC format.
        """
        if isinstance(chunk, bytes):
            # It's probably a chunk of audio
            # self.stt.feed_audio(chunk)
            pass
        else:
            try:
                chunk = json.loads(chunk)
            except:
                pass

            if "start" in chunk:
                # self.stt.start()
                self._last_lmc_start_flag = time.time()
                self.interpreter.computer.terminate()
                # Stop any code execution... maybe we should make interpreter.stop()?
            elif "end" in chunk:
                asyncio.create_task(self.run())
            else:
                await self._add_to_queue(self._input_queue, chunk)

    def add_to_output_queue_sync(self, chunk):
        """
        Synchronous function to add a chunk to the output queue.
        """
        asyncio.create_task(self._add_to_queue(self._output_queue, chunk))

    async def run(self):
        """
        Runs OI on the audio bytes submitted to the input. Will add streaming LMC chunks to the _output_queue.
        """
        # self.beeper.start()

        # self.stt.stop()
        # message = self.stt.text()
        # print("THE MESSAGE:", message)

        input_queue = list(self._input_queue._queue)
        message = [i for i in input_queue if i["type"] == "message"][0]["content"]

        def generate(message):
            last_lmc_start_flag = self._last_lmc_start_flag
            # interpreter.messages = self.active_chat_messages
            # print("🍀🍀🍀🍀GENERATING, using these messages: ", self.interpreter.messages)
            print("passing this in:", message)
            for chunk in self.interpreter.chat(message, display=False, stream=True):
                if self._last_lmc_start_flag != last_lmc_start_flag:
                    # self.beeper.stop()
                    break

                # self.add_to_output_queue_sync(chunk) # To send text, not just audio

                content = chunk.get("content")

                # Handle message blocks
                if chunk.get("type") == "message":
                    self.add_to_output_queue_sync(
                        chunk.copy()
                    )  # To send text, not just audio
                    # ^^^^^^^ MUST be a copy, otherwise the first chunk will get modified by OI >>while<< it's in the queue. Insane
                    if content:
                        # self.beeper.stop()

                        # Experimental: The AI voice sounds better with replacements like these, but it should happen at the TTS layer
                        # content = content.replace(". ", ". ... ").replace(", ", ", ... ").replace("!", "! ... ").replace("?", "? ... ")

                        yield content

                # Handle code blocks
                elif chunk.get("type") == "code":
                    pass
                    # if "start" in chunk:
                    # self.beeper.start()

                    # Experimental: If the AI wants to type, we should type immediately
                    # if (
                    #     self.interpreter.messages[-1]
                    #     .get("content", "")
                    #     .startswith("computer.keyboard.write(")
                    # ):
                    #     keyboard.controller.type(content)
                    #     self._in_keyboard_write_block = True
                    # if "end" in chunk and self._in_keyboard_write_block:
                    #     self._in_keyboard_write_block = False
                    #     # (This will make it so it doesn't type twice when the block executes)
                    #     if self.interpreter.messages[-1]["content"].startswith(
                    #         "computer.keyboard.write("
                    #     ):
                    #         self.interpreter.messages[-1]["content"] = (
                    #             "dummy_variable = ("
                    #             + self.interpreter.messages[-1]["content"][
                    #                 len("computer.keyboard.write(") :
                    #             ]
                    #         )

            # Send a completion signal
            self.add_to_output_queue_sync(
                {"role": "server", "type": "completion", "content": "DONE"}
            )

        # Feed generate to RealtimeTTS
        # self.tts.feed(generate(message))
        for _ in generate(message):
            pass
        # self.tts.play_async(on_audio_chunk=self.on_tts_chunk, muted=True)

    async def output(self):
        return await self._output_queue.get()


def server(interpreter, port=8000):  # Default port is 8000 if not specified
    async_interpreter = AsyncInterpreter(interpreter)

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
        allow_headers=["*"],  # Allow all headers
    )

    @app.post("/settings")
    async def settings(payload: Dict[str, Any]):
        for key, value in payload.items():
            print("Updating interpreter settings with the following:")
            print(key, value)
            if key == "llm" and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    setattr(async_interpreter.interpreter, sub_key, sub_value)
            else:
                setattr(async_interpreter.interpreter, key, value)

        return {"status": "success"}

    @app.websocket("/")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        try:

            async def receive_input():
                while True:
                    data = await websocket.receive()
                    print(data)
                    if isinstance(data, bytes):
                        await async_interpreter.input(data)
                    elif "text" in data:
                        await async_interpreter.input(data["text"])
                    elif data == {"type": "websocket.disconnect", "code": 1000}:
                        print("Websocket disconnected with code 1000.")
                        break

            async def send_output():
                while True:
                    output = await async_interpreter.output()
                    if isinstance(output, bytes):
                        # await websocket.send_bytes(output)
                        # we don't send out bytes rn, no TTS
                        pass
                    elif isinstance(output, dict):
                        await websocket.send_text(json.dumps(output))

            await asyncio.gather(receive_input(), send_output())
        except Exception as e:
            print(f"WebSocket connection closed with exception: {e}")
            traceback.print_exc()
        finally:
            await websocket.close()

    config = Config(app, host="0.0.0.0", port=port)
    interpreter.uvicorn_server = Server(config)
    interpreter.uvicorn_server.run()

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\proxy_track_cost_callback.py ===
import asyncio
import traceback
from datetime import datetime
from typing import Any, Optional, Union, cast

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.core_helpers import (
    _get_parent_otel_span_from_kwargs,
    get_litellm_metadata_from_kwargs,
)
from litellm.litellm_core_utils.litellm_logging import StandardLoggingPayloadSetup
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.auth.auth_checks import log_db_metrics
from litellm.proxy.auth.route_checks import RouteChecks
from litellm.proxy.utils import ProxyUpdateSpend
from litellm.types.utils import (
    StandardLoggingPayload,
    StandardLoggingUserAPIKeyMetadata,
)
from litellm.utils import get_end_user_id_for_cost_tracking


class _ProxyDBLogger(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        await self._PROXY_track_cost_callback(
            kwargs, response_obj, start_time, end_time
        )

    async def async_post_call_failure_hook(
        self,
        request_data: dict,
        original_exception: Exception,
        user_api_key_dict: UserAPIKeyAuth,
        traceback_str: Optional[str] = None,
    ):
        request_route = user_api_key_dict.request_route
        if _ProxyDBLogger._should_track_errors_in_db() is False:
            return
        elif request_route is not None and not RouteChecks.is_llm_api_route(
            route=request_route
        ):
            return

        from litellm.proxy.proxy_server import proxy_logging_obj

        _metadata = dict(
            StandardLoggingUserAPIKeyMetadata(
                user_api_key_hash=user_api_key_dict.api_key,
                user_api_key_alias=user_api_key_dict.key_alias,
                user_api_key_user_email=user_api_key_dict.user_email,
                user_api_key_user_id=user_api_key_dict.user_id,
                user_api_key_team_id=user_api_key_dict.team_id,
                user_api_key_org_id=user_api_key_dict.org_id,
                user_api_key_team_alias=user_api_key_dict.team_alias,
                user_api_key_end_user_id=user_api_key_dict.end_user_id,
                user_api_key_request_route=user_api_key_dict.request_route,
            )
        )
        _metadata["user_api_key"] = user_api_key_dict.api_key
        _metadata["status"] = "failure"
        _metadata[
            "error_information"
        ] = StandardLoggingPayloadSetup.get_error_information(
            original_exception=original_exception,
            traceback_str=traceback_str,
        )

        existing_metadata: dict = request_data.get("metadata", None) or {}
        existing_metadata.update(_metadata)

        if "litellm_params" not in request_data:
            request_data["litellm_params"] = {}
        request_data["litellm_params"]["proxy_server_request"] = (
            request_data.get("proxy_server_request") or {}
        )
        request_data["litellm_params"]["metadata"] = existing_metadata
        await proxy_logging_obj.db_spend_update_writer.update_database(
            token=user_api_key_dict.api_key,
            response_cost=0.0,
            user_id=user_api_key_dict.user_id,
            end_user_id=user_api_key_dict.end_user_id,
            team_id=user_api_key_dict.team_id,
            kwargs=request_data,
            completion_response=original_exception,
            start_time=datetime.now(),
            end_time=datetime.now(),
            org_id=user_api_key_dict.org_id,
        )

    @log_db_metrics
    async def _PROXY_track_cost_callback(
        self,
        kwargs,  # kwargs to completion
        completion_response: Optional[
            Union[litellm.ModelResponse, Any]
        ],  # response from completion
        start_time=None,
        end_time=None,  # start/end time for completion
    ):
        from litellm.proxy.proxy_server import proxy_logging_obj, update_cache

        verbose_proxy_logger.debug("INSIDE _PROXY_track_cost_callback")
        try:
            verbose_proxy_logger.debug(
                f"kwargs stream: {kwargs.get('stream', None)} + complete streaming response: {kwargs.get('complete_streaming_response', None)}"
            )
            parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs=kwargs)
            litellm_params = kwargs.get("litellm_params", {}) or {}
            end_user_id = get_end_user_id_for_cost_tracking(litellm_params)
            metadata = get_litellm_metadata_from_kwargs(kwargs=kwargs)
            user_id = cast(Optional[str], metadata.get("user_api_key_user_id", None))
            team_id = cast(Optional[str], metadata.get("user_api_key_team_id", None))
            org_id = cast(Optional[str], metadata.get("user_api_key_org_id", None))
            key_alias = cast(Optional[str], metadata.get("user_api_key_alias", None))
            end_user_max_budget = metadata.get("user_api_end_user_max_budget", None)
            sl_object: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )
            response_cost = (
                sl_object.get("response_cost", None)
                if sl_object is not None
                else kwargs.get("response_cost", None)
            )

            if response_cost is not None:
                user_api_key = metadata.get("user_api_key", None)
                if kwargs.get("cache_hit", False) is True:
                    response_cost = 0.0
                    verbose_proxy_logger.info(
                        f"Cache Hit: response_cost {response_cost}, for user_id {user_id}"
                    )

                verbose_proxy_logger.debug(
                    f"user_api_key {user_api_key}, user_id {user_id}, team_id {team_id}, end_user_id {end_user_id}"
                )
                if _should_track_cost_callback(
                    user_api_key=user_api_key,
                    user_id=user_id,
                    team_id=team_id,
                    end_user_id=end_user_id,
                ):
                    ## UPDATE DATABASE
                    await proxy_logging_obj.db_spend_update_writer.update_database(
                        token=user_api_key,
                        response_cost=response_cost,
                        user_id=user_id,
                        end_user_id=end_user_id,
                        team_id=team_id,
                        kwargs=kwargs,
                        completion_response=completion_response,
                        start_time=start_time,
                        end_time=end_time,
                        org_id=org_id,
                    )

                    # update cache
                    asyncio.create_task(
                        update_cache(
                            token=user_api_key,
                            user_id=user_id,
                            end_user_id=end_user_id,
                            response_cost=response_cost,
                            team_id=team_id,
                            parent_otel_span=parent_otel_span,
                        )
                    )

                    await proxy_logging_obj.slack_alerting_instance.customer_spend_alert(
                        token=user_api_key,
                        key_alias=key_alias,
                        end_user_id=end_user_id,
                        response_cost=response_cost,
                        max_budget=end_user_max_budget,
                    )
                else:
                    raise Exception(
                        "User API key and team id and user id missing from custom callback."
                    )
            else:
                if kwargs["stream"] is not True or (
                    kwargs["stream"] is True and "complete_streaming_response" in kwargs
                ):
                    if sl_object is not None:
                        cost_tracking_failure_debug_info: Union[dict, str] = (
                            sl_object["response_cost_failure_debug_info"]  # type: ignore
                            or "response_cost_failure_debug_info is None in standard_logging_object"
                        )
                    else:
                        cost_tracking_failure_debug_info = (
                            "standard_logging_object not found"
                        )
                    model = kwargs.get("model")
                    raise Exception(
                        f"Cost tracking failed for model={model}.\nDebug info - {cost_tracking_failure_debug_info}\nAdd custom pricing - https://docs.litellm.ai/docs/proxy/custom_pricing"
                    )
        except Exception as e:
            error_msg = f"Error in tracking cost callback - {str(e)}\n Traceback:{traceback.format_exc()}"
            model = kwargs.get("model", "")
            metadata = get_litellm_metadata_from_kwargs(kwargs=kwargs)
            litellm_metadata = kwargs.get("litellm_params", {}).get(
                "litellm_metadata", {}
            )
            old_metadata = kwargs.get("litellm_params", {}).get("metadata", {})
            call_type = kwargs.get("call_type", "")
            error_msg += f"\n Args to _PROXY_track_cost_callback\n model: {model}\n chosen_metadata: {metadata}\n litellm_metadata: {litellm_metadata}\n old_metadata: {old_metadata}\n call_type: {call_type}\n"
            asyncio.create_task(
                proxy_logging_obj.failed_tracking_alert(
                    error_message=error_msg,
                    failing_model=model,
                )
            )

            verbose_proxy_logger.exception(
                "Error in tracking cost callback - %s", str(e)
            )

    @staticmethod
    def _should_track_errors_in_db():
        """
        Returns True if errors should be tracked in the database

        By default, errors are tracked in the database

        If users want to disable error tracking, they can set the disable_error_logs flag in the general_settings
        """
        from litellm.proxy.proxy_server import general_settings

        if general_settings.get("disable_error_logs") is True:
            return False
        return


def _should_track_cost_callback(
    user_api_key: Optional[str],
    user_id: Optional[str],
    team_id: Optional[str],
    end_user_id: Optional[str],
) -> bool:
    """
    Determine if the cost callback should be tracked based on the kwargs
    """

    # don't run track cost callback if user opted into disabling spend
    if ProxyUpdateSpend.disable_spend_updates() is True:
        return False

    if (
        user_api_key is not None
        or user_id is not None
        or team_id is not None
        or end_user_id is not None
    ):
        return True
    return False

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\ycoe.py ===
# Natural Language Toolkit: York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE)
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Selina Dennis <selina@tranzfusion.net>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the York-Toronto-Helsinki Parsed Corpus of Old
English Prose (YCOE), a 1.5 million word syntactically-annotated
corpus of Old English prose texts. The corpus is distributed by the
Oxford Text Archive: http://www.ota.ahds.ac.uk/ It is not included
with NLTK.

The YCOE corpus is divided into 100 files, each representing
an Old English prose text. Tags used within each text complies
to the YCOE standard: https://www-users.york.ac.uk/~lang22/YCOE/YcoeHome.htm
"""

import os
import re

from nltk.corpus.reader.api import *
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
from nltk.corpus.reader.tagged import TaggedCorpusReader
from nltk.corpus.reader.util import *
from nltk.tokenize import RegexpTokenizer


class YCOECorpusReader(CorpusReader):
    """
    Corpus reader for the York-Toronto-Helsinki Parsed Corpus of Old
    English Prose (YCOE), a 1.5 million word syntactically-annotated
    corpus of Old English prose texts.
    """

    def __init__(self, root, encoding="utf8"):
        CorpusReader.__init__(self, root, [], encoding)

        self._psd_reader = YCOEParseCorpusReader(
            self.root.join("psd"), ".*", ".psd", encoding=encoding
        )
        self._pos_reader = YCOETaggedCorpusReader(self.root.join("pos"), ".*", ".pos")

        # Make sure we have a consistent set of items:
        documents = {f[:-4] for f in self._psd_reader.fileids()}
        if {f[:-4] for f in self._pos_reader.fileids()} != documents:
            raise ValueError('Items in "psd" and "pos" ' "subdirectories do not match.")

        fileids = sorted(
            ["%s.psd" % doc for doc in documents]
            + ["%s.pos" % doc for doc in documents]
        )
        CorpusReader.__init__(self, root, fileids, encoding)
        self._documents = sorted(documents)

    def documents(self, fileids=None):
        """
        Return a list of document identifiers for all documents in
        this corpus, or for the documents with the given file(s) if
        specified.
        """
        if fileids is None:
            return self._documents
        if isinstance(fileids, str):
            fileids = [fileids]
        for f in fileids:
            if f not in self._fileids:
                raise KeyError("File id %s not found" % fileids)
        # Strip off the '.pos' and '.psd' extensions.
        return sorted({f[:-4] for f in fileids})

    def fileids(self, documents=None):
        """
        Return a list of file identifiers for the files that make up
        this corpus, or that store the given document(s) if specified.
        """
        if documents is None:
            return self._fileids
        elif isinstance(documents, str):
            documents = [documents]
        return sorted(
            set(
                ["%s.pos" % doc for doc in documents]
                + ["%s.psd" % doc for doc in documents]
            )
        )

    def _getfileids(self, documents, subcorpus):
        """
        Helper that selects the appropriate fileids for a given set of
        documents from a given subcorpus (pos or psd).
        """
        if documents is None:
            documents = self._documents
        else:
            if isinstance(documents, str):
                documents = [documents]
            for document in documents:
                if document not in self._documents:
                    if document[-4:] in (".pos", ".psd"):
                        raise ValueError(
                            "Expected a document identifier, not a file "
                            "identifier.  (Use corpus.documents() to get "
                            "a list of document identifiers."
                        )
                    else:
                        raise ValueError("Document identifier %s not found" % document)
        return [f"{d}.{subcorpus}" for d in documents]

    # Delegate to one of our two sub-readers:
    def words(self, documents=None):
        return self._pos_reader.words(self._getfileids(documents, "pos"))

    def sents(self, documents=None):
        return self._pos_reader.sents(self._getfileids(documents, "pos"))

    def paras(self, documents=None):
        return self._pos_reader.paras(self._getfileids(documents, "pos"))

    def tagged_words(self, documents=None):
        return self._pos_reader.tagged_words(self._getfileids(documents, "pos"))

    def tagged_sents(self, documents=None):
        return self._pos_reader.tagged_sents(self._getfileids(documents, "pos"))

    def tagged_paras(self, documents=None):
        return self._pos_reader.tagged_paras(self._getfileids(documents, "pos"))

    def parsed_sents(self, documents=None):
        return self._psd_reader.parsed_sents(self._getfileids(documents, "psd"))


class YCOEParseCorpusReader(BracketParseCorpusReader):
    """Specialized version of the standard bracket parse corpus reader
    that strips out (CODE ...) and (ID ...) nodes."""

    def _parse(self, t):
        t = re.sub(r"(?u)\((CODE|ID)[^\)]*\)", "", t)
        if re.match(r"\s*\(\s*\)\s*$", t):
            return None
        return BracketParseCorpusReader._parse(self, t)


class YCOETaggedCorpusReader(TaggedCorpusReader):
    def __init__(self, root, items, encoding="utf8"):
        gaps_re = r"(?u)(?<=/\.)\s+|\s*\S*_CODE\s*|\s*\S*_ID\s*"
        sent_tokenizer = RegexpTokenizer(gaps_re, gaps=True)
        TaggedCorpusReader.__init__(
            self, root, items, sep="_", sent_tokenizer=sent_tokenizer
        )


#: A list of all documents and their titles in ycoe.
documents = {
    "coadrian.o34": "Adrian and Ritheus",
    "coaelhom.o3": "Ælfric, Supplemental Homilies",
    "coaelive.o3": "Ælfric's Lives of Saints",
    "coalcuin": "Alcuin De virtutibus et vitiis",
    "coalex.o23": "Alexander's Letter to Aristotle",
    "coapollo.o3": "Apollonius of Tyre",
    "coaugust": "Augustine",
    "cobede.o2": "Bede's History of the English Church",
    "cobenrul.o3": "Benedictine Rule",
    "coblick.o23": "Blickling Homilies",
    "coboeth.o2": "Boethius' Consolation of Philosophy",
    "cobyrhtf.o3": "Byrhtferth's Manual",
    "cocanedgD": "Canons of Edgar (D)",
    "cocanedgX": "Canons of Edgar (X)",
    "cocathom1.o3": "Ælfric's Catholic Homilies I",
    "cocathom2.o3": "Ælfric's Catholic Homilies II",
    "cochad.o24": "Saint Chad",
    "cochdrul": "Chrodegang of Metz, Rule",
    "cochristoph": "Saint Christopher",
    "cochronA.o23": "Anglo-Saxon Chronicle A",
    "cochronC": "Anglo-Saxon Chronicle C",
    "cochronD": "Anglo-Saxon Chronicle D",
    "cochronE.o34": "Anglo-Saxon Chronicle E",
    "cocura.o2": "Cura Pastoralis",
    "cocuraC": "Cura Pastoralis (Cotton)",
    "codicts.o34": "Dicts of Cato",
    "codocu1.o1": "Documents 1 (O1)",
    "codocu2.o12": "Documents 2 (O1/O2)",
    "codocu2.o2": "Documents 2 (O2)",
    "codocu3.o23": "Documents 3 (O2/O3)",
    "codocu3.o3": "Documents 3 (O3)",
    "codocu4.o24": "Documents 4 (O2/O4)",
    "coeluc1": "Honorius of Autun, Elucidarium 1",
    "coeluc2": "Honorius of Autun, Elucidarium 1",
    "coepigen.o3": "Ælfric's Epilogue to Genesis",
    "coeuphr": "Saint Euphrosyne",
    "coeust": "Saint Eustace and his companions",
    "coexodusP": "Exodus (P)",
    "cogenesiC": "Genesis (C)",
    "cogregdC.o24": "Gregory's Dialogues (C)",
    "cogregdH.o23": "Gregory's Dialogues (H)",
    "coherbar": "Pseudo-Apuleius, Herbarium",
    "coinspolD.o34": "Wulfstan's Institute of Polity (D)",
    "coinspolX": "Wulfstan's Institute of Polity (X)",
    "cojames": "Saint James",
    "colacnu.o23": "Lacnunga",
    "colaece.o2": "Leechdoms",
    "colaw1cn.o3": "Laws, Cnut I",
    "colaw2cn.o3": "Laws, Cnut II",
    "colaw5atr.o3": "Laws, Æthelred V",
    "colaw6atr.o3": "Laws, Æthelred VI",
    "colawaf.o2": "Laws, Alfred",
    "colawafint.o2": "Alfred's Introduction to Laws",
    "colawger.o34": "Laws, Gerefa",
    "colawine.ox2": "Laws, Ine",
    "colawnorthu.o3": "Northumbra Preosta Lagu",
    "colawwllad.o4": "Laws, William I, Lad",
    "coleofri.o4": "Leofric",
    "colsigef.o3": "Ælfric's Letter to Sigefyrth",
    "colsigewB": "Ælfric's Letter to Sigeweard (B)",
    "colsigewZ.o34": "Ælfric's Letter to Sigeweard (Z)",
    "colwgeat": "Ælfric's Letter to Wulfgeat",
    "colwsigeT": "Ælfric's Letter to Wulfsige (T)",
    "colwsigeXa.o34": "Ælfric's Letter to Wulfsige (Xa)",
    "colwstan1.o3": "Ælfric's Letter to Wulfstan I",
    "colwstan2.o3": "Ælfric's Letter to Wulfstan II",
    "comargaC.o34": "Saint Margaret (C)",
    "comargaT": "Saint Margaret (T)",
    "comart1": "Martyrology, I",
    "comart2": "Martyrology, II",
    "comart3.o23": "Martyrology, III",
    "comarvel.o23": "Marvels of the East",
    "comary": "Mary of Egypt",
    "coneot": "Saint Neot",
    "conicodA": "Gospel of Nicodemus (A)",
    "conicodC": "Gospel of Nicodemus (C)",
    "conicodD": "Gospel of Nicodemus (D)",
    "conicodE": "Gospel of Nicodemus (E)",
    "coorosiu.o2": "Orosius",
    "cootest.o3": "Heptateuch",
    "coprefcath1.o3": "Ælfric's Preface to Catholic Homilies I",
    "coprefcath2.o3": "Ælfric's Preface to Catholic Homilies II",
    "coprefcura.o2": "Preface to the Cura Pastoralis",
    "coprefgen.o3": "Ælfric's Preface to Genesis",
    "copreflives.o3": "Ælfric's Preface to Lives of Saints",
    "coprefsolilo": "Preface to Augustine's Soliloquies",
    "coquadru.o23": "Pseudo-Apuleius, Medicina de quadrupedibus",
    "corood": "History of the Holy Rood-Tree",
    "cosevensl": "Seven Sleepers",
    "cosolilo": "St. Augustine's Soliloquies",
    "cosolsat1.o4": "Solomon and Saturn I",
    "cosolsat2": "Solomon and Saturn II",
    "cotempo.o3": "Ælfric's De Temporibus Anni",
    "coverhom": "Vercelli Homilies",
    "coverhomE": "Vercelli Homilies (E)",
    "coverhomL": "Vercelli Homilies (L)",
    "covinceB": "Saint Vincent (Bodley 343)",
    "covinsal": "Vindicta Salvatoris",
    "cowsgosp.o3": "West-Saxon Gospels",
    "cowulf.o34": "Wulfstan's Homilies",
}

# === NexusCore/openenv\Lib\site-packages\pip\_internal\operations\freeze.py ===
import collections
import logging
import os
from dataclasses import dataclass, field
from typing import Container, Dict, Generator, Iterable, List, NamedTuple, Optional, Set

from pip._vendor.packaging.utils import NormalizedName, canonicalize_name
from pip._vendor.packaging.version import InvalidVersion

from pip._internal.exceptions import BadCommand, InstallationError
from pip._internal.metadata import BaseDistribution, get_environment
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._internal.req.req_file import COMMENT_RE
from pip._internal.utils.direct_url_helpers import direct_url_as_pep440_direct_reference

logger = logging.getLogger(__name__)


class _EditableInfo(NamedTuple):
    requirement: str
    comments: List[str]


def freeze(
    requirement: Optional[List[str]] = None,
    local_only: bool = False,
    user_only: bool = False,
    paths: Optional[List[str]] = None,
    isolated: bool = False,
    exclude_editable: bool = False,
    skip: Container[str] = (),
) -> Generator[str, None, None]:
    installations: Dict[str, FrozenRequirement] = {}

    dists = get_environment(paths).iter_installed_distributions(
        local_only=local_only,
        skip=(),
        user_only=user_only,
    )
    for dist in dists:
        req = FrozenRequirement.from_dist(dist)
        if exclude_editable and req.editable:
            continue
        installations[req.canonical_name] = req

    if requirement:
        # the options that don't get turned into an InstallRequirement
        # should only be emitted once, even if the same option is in multiple
        # requirements files, so we need to keep track of what has been emitted
        # so that we don't emit it again if it's seen again
        emitted_options: Set[str] = set()
        # keep track of which files a requirement is in so that we can
        # give an accurate warning if a requirement appears multiple times.
        req_files: Dict[str, List[str]] = collections.defaultdict(list)
        for req_file_path in requirement:
            with open(req_file_path) as req_file:
                for line in req_file:
                    if (
                        not line.strip()
                        or line.strip().startswith("#")
                        or line.startswith(
                            (
                                "-r",
                                "--requirement",
                                "-f",
                                "--find-links",
                                "-i",
                                "--index-url",
                                "--pre",
                                "--trusted-host",
                                "--process-dependency-links",
                                "--extra-index-url",
                                "--use-feature",
                            )
                        )
                    ):
                        line = line.rstrip()
                        if line not in emitted_options:
                            emitted_options.add(line)
                            yield line
                        continue

                    if line.startswith("-e") or line.startswith("--editable"):
                        if line.startswith("-e"):
                            line = line[2:].strip()
                        else:
                            line = line[len("--editable") :].strip().lstrip("=")
                        line_req = install_req_from_editable(
                            line,
                            isolated=isolated,
                        )
                    else:
                        line_req = install_req_from_line(
                            COMMENT_RE.sub("", line).strip(),
                            isolated=isolated,
                        )

                    if not line_req.name:
                        logger.info(
                            "Skipping line in requirement file [%s] because "
                            "it's not clear what it would install: %s",
                            req_file_path,
                            line.strip(),
                        )
                        logger.info(
                            "  (add #egg=PackageName to the URL to avoid"
                            " this warning)"
                        )
                    else:
                        line_req_canonical_name = canonicalize_name(line_req.name)
                        if line_req_canonical_name not in installations:
                            # either it's not installed, or it is installed
                            # but has been processed already
                            if not req_files[line_req.name]:
                                logger.warning(
                                    "Requirement file [%s] contains %s, but "
                                    "package %r is not installed",
                                    req_file_path,
                                    COMMENT_RE.sub("", line).strip(),
                                    line_req.name,
                                )
                            else:
                                req_files[line_req.name].append(req_file_path)
                        else:
                            yield str(installations[line_req_canonical_name]).rstrip()
                            del installations[line_req_canonical_name]
                            req_files[line_req.name].append(req_file_path)

        # Warn about requirements that were included multiple times (in a
        # single requirements file or in different requirements files).
        for name, files in req_files.items():
            if len(files) > 1:
                logger.warning(
                    "Requirement %s included multiple times [%s]",
                    name,
                    ", ".join(sorted(set(files))),
                )

        yield ("## The following requirements were added by pip freeze:")
    for installation in sorted(installations.values(), key=lambda x: x.name.lower()):
        if installation.canonical_name not in skip:
            yield str(installation).rstrip()


def _format_as_name_version(dist: BaseDistribution) -> str:
    try:
        dist_version = dist.version
    except InvalidVersion:
        # legacy version
        return f"{dist.raw_name}==={dist.raw_version}"
    else:
        return f"{dist.raw_name}=={dist_version}"


def _get_editable_info(dist: BaseDistribution) -> _EditableInfo:
    """
    Compute and return values (req, comments) for use in
    FrozenRequirement.from_dist().
    """
    editable_project_location = dist.editable_project_location
    assert editable_project_location
    location = os.path.normcase(os.path.abspath(editable_project_location))

    from pip._internal.vcs import RemoteNotFoundError, RemoteNotValidError, vcs

    vcs_backend = vcs.get_backend_for_dir(location)

    if vcs_backend is None:
        display = _format_as_name_version(dist)
        logger.debug(
            'No VCS found for editable requirement "%s" in: %r',
            display,
            location,
        )
        return _EditableInfo(
            requirement=location,
            comments=[f"# Editable install with no version control ({display})"],
        )

    vcs_name = type(vcs_backend).__name__

    try:
        req = vcs_backend.get_src_requirement(location, dist.raw_name)
    except RemoteNotFoundError:
        display = _format_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[f"# Editable {vcs_name} install with no remote ({display})"],
        )
    except RemoteNotValidError as ex:
        display = _format_as_name_version(dist)
        return _EditableInfo(
            requirement=location,
            comments=[
                f"# Editable {vcs_name} install ({display}) with either a deleted "
                f"local remote or invalid URI:",
                f"# '{ex.url}'",
            ],
        )
    except BadCommand:
        logger.warning(
            "cannot determine version of editable source in %s "
            "(%s command not found in path)",
            location,
            vcs_backend.name,
        )
        return _EditableInfo(requirement=location, comments=[])
    except InstallationError as exc:
        logger.warning("Error when trying to get requirement for VCS system %s", exc)
    else:
        return _EditableInfo(requirement=req, comments=[])

    logger.warning("Could not determine repository location of %s", location)

    return _EditableInfo(
        requirement=location,
        comments=["## !! Could not determine repository location"],
    )


@dataclass(frozen=True)
class FrozenRequirement:
    name: str
    req: str
    editable: bool
    comments: Iterable[str] = field(default_factory=tuple)

    @property
    def canonical_name(self) -> NormalizedName:
        return canonicalize_name(self.name)

    @classmethod
    def from_dist(cls, dist: BaseDistribution) -> "FrozenRequirement":
        editable = dist.editable
        if editable:
            req, comments = _get_editable_info(dist)
        else:
            comments = []
            direct_url = dist.direct_url
            if direct_url:
                # if PEP 610 metadata is present, use it
                req = direct_url_as_pep440_direct_reference(direct_url, dist.raw_name)
            else:
                # name==version requirement
                req = _format_as_name_version(dist)

        return cls(dist.raw_name, req, editable, comments=comments)

    def __str__(self) -> str:
        req = self.req
        if self.editable:
            req = f"-e {req}"
        return "\n".join(list(self.comments) + [str(req)]) + "\n"

# === NexusCore/openenv\Lib\site-packages\pydantic\deprecated\class_validators.py ===
"""Old `@validator` and `@root_validator` function validators from V1."""

from __future__ import annotations as _annotations

from functools import partial, partialmethod
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar, Union, overload
from warnings import warn

from typing_extensions import Protocol, TypeAlias, deprecated

from .._internal import _decorators, _decorators_v1
from ..errors import PydanticUserError
from ..warnings import PydanticDeprecatedSince20

_ALLOW_REUSE_WARNING_MESSAGE = '`allow_reuse` is deprecated and will be ignored; it should no longer be necessary'


if TYPE_CHECKING:

    class _OnlyValueValidatorClsMethod(Protocol):
        def __call__(self, __cls: Any, __value: Any) -> Any: ...

    class _V1ValidatorWithValuesClsMethod(Protocol):
        def __call__(self, __cls: Any, __value: Any, values: dict[str, Any]) -> Any: ...

    class _V1ValidatorWithValuesKwOnlyClsMethod(Protocol):
        def __call__(self, __cls: Any, __value: Any, *, values: dict[str, Any]) -> Any: ...

    class _V1ValidatorWithKwargsClsMethod(Protocol):
        def __call__(self, __cls: Any, **kwargs: Any) -> Any: ...

    class _V1ValidatorWithValuesAndKwargsClsMethod(Protocol):
        def __call__(self, __cls: Any, values: dict[str, Any], **kwargs: Any) -> Any: ...

    class _V1RootValidatorClsMethod(Protocol):
        def __call__(
            self, __cls: Any, __values: _decorators_v1.RootValidatorValues
        ) -> _decorators_v1.RootValidatorValues: ...

    V1Validator = Union[
        _OnlyValueValidatorClsMethod,
        _V1ValidatorWithValuesClsMethod,
        _V1ValidatorWithValuesKwOnlyClsMethod,
        _V1ValidatorWithKwargsClsMethod,
        _V1ValidatorWithValuesAndKwargsClsMethod,
        _decorators_v1.V1ValidatorWithValues,
        _decorators_v1.V1ValidatorWithValuesKwOnly,
        _decorators_v1.V1ValidatorWithKwargs,
        _decorators_v1.V1ValidatorWithValuesAndKwargs,
    ]

    V1RootValidator = Union[
        _V1RootValidatorClsMethod,
        _decorators_v1.V1RootValidatorFunction,
    ]

    _PartialClsOrStaticMethod: TypeAlias = Union[classmethod[Any, Any, Any], staticmethod[Any, Any], partialmethod[Any]]

    # Allow both a V1 (assumed pre=False) or V2 (assumed mode='after') validator
    # We lie to type checkers and say we return the same thing we get
    # but in reality we return a proxy object that _mostly_ behaves like the wrapped thing
    _V1ValidatorType = TypeVar('_V1ValidatorType', V1Validator, _PartialClsOrStaticMethod)
    _V1RootValidatorFunctionType = TypeVar(
        '_V1RootValidatorFunctionType',
        _decorators_v1.V1RootValidatorFunction,
        _V1RootValidatorClsMethod,
        _PartialClsOrStaticMethod,
    )
else:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20


@deprecated(
    'Pydantic V1 style `@validator` validators are deprecated.'
    ' You should migrate to Pydantic V2 style `@field_validator` validators,'
    ' see the migration guide for more details',
    category=None,
)
def validator(
    __field: str,
    *fields: str,
    pre: bool = False,
    each_item: bool = False,
    always: bool = False,
    check_fields: bool | None = None,
    allow_reuse: bool = False,
) -> Callable[[_V1ValidatorType], _V1ValidatorType]:
    """Decorate methods on the class indicating that they should be used to validate fields.

    Args:
        __field (str): The first field the validator should be called on; this is separate
            from `fields` to ensure an error is raised if you don't pass at least one.
        *fields (str): Additional field(s) the validator should be called on.
        pre (bool, optional): Whether this validator should be called before the standard
            validators (else after). Defaults to False.
        each_item (bool, optional): For complex objects (sets, lists etc.) whether to validate
            individual elements rather than the whole object. Defaults to False.
        always (bool, optional): Whether this method and other validators should be called even if
            the value is missing. Defaults to False.
        check_fields (bool | None, optional): Whether to check that the fields actually exist on the model.
            Defaults to None.
        allow_reuse (bool, optional): Whether to track and raise an error if another validator refers to
            the decorated function. Defaults to False.

    Returns:
        Callable: A decorator that can be used to decorate a
            function to be used as a validator.
    """
    warn(
        'Pydantic V1 style `@validator` validators are deprecated.'
        ' You should migrate to Pydantic V2 style `@field_validator` validators,'
        ' see the migration guide for more details',
        DeprecationWarning,
        stacklevel=2,
    )

    if allow_reuse is True:  # pragma: no cover
        warn(_ALLOW_REUSE_WARNING_MESSAGE, DeprecationWarning)
    fields = __field, *fields
    if isinstance(fields[0], FunctionType):
        raise PydanticUserError(
            '`@validator` should be used with fields and keyword arguments, not bare. '
            "E.g. usage should be `@validator('<field_name>', ...)`",
            code='validator-no-fields',
        )
    elif not all(isinstance(field, str) for field in fields):
        raise PydanticUserError(
            '`@validator` fields should be passed as separate string args. '
            "E.g. usage should be `@validator('<field_name_1>', '<field_name_2>', ...)`",
            code='validator-invalid-fields',
        )

    mode: Literal['before', 'after'] = 'before' if pre is True else 'after'

    def dec(f: Any) -> _decorators.PydanticDescriptorProxy[Any]:
        if _decorators.is_instance_method_from_sig(f):
            raise PydanticUserError(
                '`@validator` cannot be applied to instance methods', code='validator-instance-method'
            )
        # auto apply the @classmethod decorator
        f = _decorators.ensure_classmethod_based_on_signature(f)
        wrap = _decorators_v1.make_generic_v1_field_validator
        validator_wrapper_info = _decorators.ValidatorDecoratorInfo(
            fields=fields,
            mode=mode,
            each_item=each_item,
            always=always,
            check_fields=check_fields,
        )
        return _decorators.PydanticDescriptorProxy(f, validator_wrapper_info, shim=wrap)

    return dec  # type: ignore[return-value]


@overload
def root_validator(
    *,
    # if you don't specify `pre` the default is `pre=False`
    # which means you need to specify `skip_on_failure=True`
    skip_on_failure: Literal[True],
    allow_reuse: bool = ...,
) -> Callable[
    [_V1RootValidatorFunctionType],
    _V1RootValidatorFunctionType,
]: ...


@overload
def root_validator(
    *,
    # if you specify `pre=True` then you don't need to specify
    # `skip_on_failure`, in fact it is not allowed as an argument!
    pre: Literal[True],
    allow_reuse: bool = ...,
) -> Callable[
    [_V1RootValidatorFunctionType],
    _V1RootValidatorFunctionType,
]: ...


@overload
def root_validator(
    *,
    # if you explicitly specify `pre=False` then you
    # MUST specify `skip_on_failure=True`
    pre: Literal[False],
    skip_on_failure: Literal[True],
    allow_reuse: bool = ...,
) -> Callable[
    [_V1RootValidatorFunctionType],
    _V1RootValidatorFunctionType,
]: ...


@deprecated(
    'Pydantic V1 style `@root_validator` validators are deprecated.'
    ' You should migrate to Pydantic V2 style `@model_validator` validators,'
    ' see the migration guide for more details',
    category=None,
)
def root_validator(
    *__args,
    pre: bool = False,
    skip_on_failure: bool = False,
    allow_reuse: bool = False,
) -> Any:
    """Decorate methods on a model indicating that they should be used to validate (and perhaps
    modify) data either before or after standard model parsing/validation is performed.

    Args:
        pre (bool, optional): Whether this validator should be called before the standard
            validators (else after). Defaults to False.
        skip_on_failure (bool, optional): Whether to stop validation and return as soon as a
            failure is encountered. Defaults to False.
        allow_reuse (bool, optional): Whether to track and raise an error if another validator
            refers to the decorated function. Defaults to False.

    Returns:
        Any: A decorator that can be used to decorate a function to be used as a root_validator.
    """
    warn(
        'Pydantic V1 style `@root_validator` validators are deprecated.'
        ' You should migrate to Pydantic V2 style `@model_validator` validators,'
        ' see the migration guide for more details',
        DeprecationWarning,
        stacklevel=2,
    )

    if __args:
        # Ensure a nice error is raised if someone attempts to use the bare decorator
        return root_validator()(*__args)  # type: ignore

    if allow_reuse is True:  # pragma: no cover
        warn(_ALLOW_REUSE_WARNING_MESSAGE, DeprecationWarning)
    mode: Literal['before', 'after'] = 'before' if pre is True else 'after'
    if pre is False and skip_on_failure is not True:
        raise PydanticUserError(
            'If you use `@root_validator` with pre=False (the default) you MUST specify `skip_on_failure=True`.'
            ' Note that `@root_validator` is deprecated and should be replaced with `@model_validator`.',
            code='root-validator-pre-skip',
        )

    wrap = partial(_decorators_v1.make_v1_generic_root_validator, pre=pre)

    def dec(f: Callable[..., Any] | classmethod[Any, Any, Any] | staticmethod[Any, Any]) -> Any:
        if _decorators.is_instance_method_from_sig(f):
            raise TypeError('`@root_validator` cannot be applied to instance methods')
        # auto apply the @classmethod decorator
        res = _decorators.ensure_classmethod_based_on_signature(f)
        dec_info = _decorators.RootValidatorDecoratorInfo(mode=mode)
        return _decorators.PydanticDescriptorProxy(res, dec_info, shim=wrap)

    return dec

# === NexusCore/openenv\Lib\site-packages\aiohttp\worker.py ===
"""Async gunicorn worker for aiohttp.web"""

import asyncio
import inspect
import os
import re
import signal
import sys
from types import FrameType
from typing import TYPE_CHECKING, Any, Optional

from gunicorn.config import AccessLogFormat as GunicornAccessLogFormat
from gunicorn.workers import base

from aiohttp import web

from .helpers import set_result
from .web_app import Application
from .web_log import AccessLogger

if TYPE_CHECKING:
    import ssl

    SSLContext = ssl.SSLContext
else:
    try:
        import ssl

        SSLContext = ssl.SSLContext
    except ImportError:  # pragma: no cover
        ssl = None  # type: ignore[assignment]
        SSLContext = object  # type: ignore[misc,assignment]


__all__ = ("GunicornWebWorker", "GunicornUVLoopWebWorker")


class GunicornWebWorker(base.Worker):  # type: ignore[misc,no-any-unimported]

    DEFAULT_AIOHTTP_LOG_FORMAT = AccessLogger.LOG_FORMAT
    DEFAULT_GUNICORN_LOG_FORMAT = GunicornAccessLogFormat.default

    def __init__(self, *args: Any, **kw: Any) -> None:  # pragma: no cover
        super().__init__(*args, **kw)

        self._task: Optional[asyncio.Task[None]] = None
        self.exit_code = 0
        self._notify_waiter: Optional[asyncio.Future[bool]] = None

    def init_process(self) -> None:
        # create new event_loop after fork
        asyncio.get_event_loop().close()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        super().init_process()

    def run(self) -> None:
        self._task = self.loop.create_task(self._run())

        try:  # ignore all finalization problems
            self.loop.run_until_complete(self._task)
        except Exception:
            self.log.exception("Exception in gunicorn worker")
        self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        self.loop.close()

        sys.exit(self.exit_code)

    async def _run(self) -> None:
        runner = None
        if isinstance(self.wsgi, Application):
            app = self.wsgi
        elif inspect.iscoroutinefunction(self.wsgi) or (
            sys.version_info < (3, 14) and asyncio.iscoroutinefunction(self.wsgi)
        ):
            wsgi = await self.wsgi()
            if isinstance(wsgi, web.AppRunner):
                runner = wsgi
                app = runner.app
            else:
                app = wsgi
        else:
            raise RuntimeError(
                "wsgi app should be either Application or "
                "async function returning Application, got {}".format(self.wsgi)
            )

        if runner is None:
            access_log = self.log.access_log if self.cfg.accesslog else None
            runner = web.AppRunner(
                app,
                logger=self.log,
                keepalive_timeout=self.cfg.keepalive,
                access_log=access_log,
                access_log_format=self._get_valid_log_format(
                    self.cfg.access_log_format
                ),
                shutdown_timeout=self.cfg.graceful_timeout / 100 * 95,
            )
        await runner.setup()

        ctx = self._create_ssl_context(self.cfg) if self.cfg.is_ssl else None

        runner = runner
        assert runner is not None
        server = runner.server
        assert server is not None
        for sock in self.sockets:
            site = web.SockSite(
                runner,
                sock,
                ssl_context=ctx,
            )
            await site.start()

        # If our parent changed then we shut down.
        pid = os.getpid()
        try:
            while self.alive:  # type: ignore[has-type]
                self.notify()

                cnt = server.requests_count
                if self.max_requests and cnt > self.max_requests:
                    self.alive = False
                    self.log.info("Max requests, shutting down: %s", self)

                elif pid == os.getpid() and self.ppid != os.getppid():
                    self.alive = False
                    self.log.info("Parent changed, shutting down: %s", self)
                else:
                    await self._wait_next_notify()
        except BaseException:
            pass

        await runner.cleanup()

    def _wait_next_notify(self) -> "asyncio.Future[bool]":
        self._notify_waiter_done()

        loop = self.loop
        assert loop is not None
        self._notify_waiter = waiter = loop.create_future()
        self.loop.call_later(1.0, self._notify_waiter_done, waiter)

        return waiter

    def _notify_waiter_done(
        self, waiter: Optional["asyncio.Future[bool]"] = None
    ) -> None:
        if waiter is None:
            waiter = self._notify_waiter
        if waiter is not None:
            set_result(waiter, True)

        if waiter is self._notify_waiter:
            self._notify_waiter = None

    def init_signals(self) -> None:
        # Set up signals through the event loop API.

        self.loop.add_signal_handler(
            signal.SIGQUIT, self.handle_quit, signal.SIGQUIT, None
        )

        self.loop.add_signal_handler(
            signal.SIGTERM, self.handle_exit, signal.SIGTERM, None
        )

        self.loop.add_signal_handler(
            signal.SIGINT, self.handle_quit, signal.SIGINT, None
        )

        self.loop.add_signal_handler(
            signal.SIGWINCH, self.handle_winch, signal.SIGWINCH, None
        )

        self.loop.add_signal_handler(
            signal.SIGUSR1, self.handle_usr1, signal.SIGUSR1, None
        )

        self.loop.add_signal_handler(
            signal.SIGABRT, self.handle_abort, signal.SIGABRT, None
        )

        # Don't let SIGTERM and SIGUSR1 disturb active requests
        # by interrupting system calls
        signal.siginterrupt(signal.SIGTERM, False)
        signal.siginterrupt(signal.SIGUSR1, False)
        # Reset signals so Gunicorn doesn't swallow subprocess return codes
        # See: https://github.com/aio-libs/aiohttp/issues/6130

    def handle_quit(self, sig: int, frame: Optional[FrameType]) -> None:
        self.alive = False

        # worker_int callback
        self.cfg.worker_int(self)

        # wakeup closing process
        self._notify_waiter_done()

    def handle_abort(self, sig: int, frame: Optional[FrameType]) -> None:
        self.alive = False
        self.exit_code = 1
        self.cfg.worker_abort(self)
        sys.exit(1)

    @staticmethod
    def _create_ssl_context(cfg: Any) -> "SSLContext":
        """Creates SSLContext instance for usage in asyncio.create_server.

        See ssl.SSLSocket.__init__ for more details.
        """
        if ssl is None:  # pragma: no cover
            raise RuntimeError("SSL is not supported.")

        ctx = ssl.SSLContext(cfg.ssl_version)
        ctx.load_cert_chain(cfg.certfile, cfg.keyfile)
        ctx.verify_mode = cfg.cert_reqs
        if cfg.ca_certs:
            ctx.load_verify_locations(cfg.ca_certs)
        if cfg.ciphers:
            ctx.set_ciphers(cfg.ciphers)
        return ctx

    def _get_valid_log_format(self, source_format: str) -> str:
        if source_format == self.DEFAULT_GUNICORN_LOG_FORMAT:
            return self.DEFAULT_AIOHTTP_LOG_FORMAT
        elif re.search(r"%\([^\)]+\)", source_format):
            raise ValueError(
                "Gunicorn's style options in form of `%(name)s` are not "
                "supported for the log formatting. Please use aiohttp's "
                "format specification to configure access log formatting: "
                "http://docs.aiohttp.org/en/stable/logging.html"
                "#format-specification"
            )
        else:
            return source_format


class GunicornUVLoopWebWorker(GunicornWebWorker):
    def init_process(self) -> None:
        import uvloop

        # Close any existing event loop before setting a
        # new policy.
        asyncio.get_event_loop().close()

        # Setup uvloop policy, so that every
        # asyncio.get_event_loop() will create an instance
        # of uvloop event loop.
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        super().init_process()

# === NexusCore/openenv\Lib\site-packages\google\generativeai\retriever.py ===
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


from typing import AsyncIterable, Iterable, Optional

import google.ai.generativelanguage as glm
from google.generativeai import protos

from google.generativeai.client import get_default_retriever_client
from google.generativeai.client import get_default_retriever_async_client
from google.generativeai.types import helper_types
from google.generativeai.types.model_types import idecode_time
from google.generativeai.types import retriever_types


def create_corpus(
    name: str | None = None,
    display_name: str | None = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:
    """Calls the API to create a new `Corpus` by specifying either a corpus resource name as an ID or a display name, and returns the created `Corpus`.

    Args:
        name: The corpus resource name (ID). The name must be alphanumeric and fewer
            than 40 characters.
        display_name: The human readable display name. The display name must be fewer
            than 128 characters. All characters, including alphanumeric, spaces, and
            dashes are supported.
        request_options: Options for the request.

    Return:
        `retriever_types.Corpus` object with specified name or display name.

    Raises:
        ValueError: When the name is not specified or formatted incorrectly.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if name is None:
        corpus = protos.Corpus(display_name=display_name)
    elif retriever_types.valid_name(name):
        corpus = protos.Corpus(name=f"corpora/{name}", display_name=display_name)
    else:
        raise ValueError(retriever_types.NAME_ERROR_MSG.format(length=len(name), name=name))

    request = protos.CreateCorpusRequest(corpus=corpus)
    response = client.create_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


async def create_corpus_async(
    name: str | None = None,
    display_name: str | None = None,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:
    """This is the async version of `retriever.create_corpus`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if name is None:
        corpus = protos.Corpus(display_name=display_name)
    elif retriever_types.valid_name(name):
        corpus = protos.Corpus(name=f"corpora/{name}", display_name=display_name)
    else:
        raise ValueError(retriever_types.NAME_ERROR_MSG.format(length=len(name), name=name))

    request = protos.CreateCorpusRequest(corpus=corpus)
    response = await client.create_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


def get_corpus(
    name: str,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:  # fmt: skip
    """Calls the API to fetch a `Corpus` by name and returns the `Corpus`.

    Args:
        name: The `Corpus` name.
        request_options: Options for the request.

    Return:
        a `retriever_types.Corpus` of interest.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.GetCorpusRequest(name=name)
    response = client.get_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


async def get_corpus_async(
    name: str,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> retriever_types.Corpus:  # fmt: skip
    """This is the async version of `retriever.get_corpus`."""

    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.GetCorpusRequest(name=name)
    response = await client.get_corpus(request, **request_options)
    response = type(response).to_dict(response)
    idecode_time(response, "create_time")
    idecode_time(response, "update_time")
    response = retriever_types.Corpus(**response)
    return response


def delete_corpus(
    name: str,
    force: bool = False,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):  # fmt: skip
    """Calls the API to remove a `Corpus` from the service, optionally deleting associated `Document`s and objects if the `force` parameter is set to true.

    Args:
        name: The `Corpus` name.
        force: If set to true, any `Document`s and objects related to this `Corpus` will also be deleted.
        request_options: Options for the request.

    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.DeleteCorpusRequest(name=name, force=force)
    client.delete_corpus(request, **request_options)


async def delete_corpus_async(
    name: str,
    force: bool = False,
    client: glm.RetrieverServiceAsyncClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
):  # fmt: skip
    """This is the async version of `retriever.delete_corpus`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    if "/" not in name:
        name = "corpora/" + name

    request = protos.DeleteCorpusRequest(name=name, force=force)
    await client.delete_corpus(request, **request_options)


def list_corpora(
    *,
    page_size: Optional[int] = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> Iterable[retriever_types.Corpus]:
    """Calls the API to list all `Corpora` in the service and returns a list of paginated `Corpora`.

    Args:
        page_size: Maximum number of `Corpora` to request.
        page_token: A page token, received from a previous ListCorpora call.
        request_options: Options for the request.

    Return:
        Paginated list of `Corpora`.
    """
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_client()

    request = protos.ListCorporaRequest(page_size=page_size)
    for corpus in client.list_corpora(request, **request_options):
        corpus = type(corpus).to_dict(corpus)
        idecode_time(corpus, "create_time")
        idecode_time(corpus, "update_time")
        yield retriever_types.Corpus(**corpus)


async def list_corpora_async(
    *,
    page_size: Optional[int] = None,
    client: glm.RetrieverServiceClient | None = None,
    request_options: helper_types.RequestOptionsType | None = None,
) -> AsyncIterable[retriever_types.Corpus]:
    """This is the async version of `retriever.list_corpora`."""
    if request_options is None:
        request_options = {}

    if client is None:
        client = get_default_retriever_async_client()

    request = protos.ListCorporaRequest(page_size=page_size)
    async for corpus in await client.list_corpora(request, **request_options):
        corpus = type(corpus).to_dict(corpus)
        idecode_time(corpus, "create_time")
        idecode_time(corpus, "update_time")
        yield retriever_types.Corpus(**corpus)

# === NexusCore/openenv\Lib\site-packages\nltk\sentiment\sentiment_analyzer.py ===
#
# Natural Language Toolkit: Sentiment Analyzer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A SentimentAnalyzer is a tool to implement and facilitate Sentiment Analysis tasks
using NLTK features and classifiers, especially for teaching and demonstrative
purposes.
"""

import sys
from collections import defaultdict

from nltk.classify.util import accuracy as eval_accuracy
from nltk.classify.util import apply_features
from nltk.collocations import BigramCollocationFinder
from nltk.metrics import BigramAssocMeasures
from nltk.metrics import f_measure as eval_f_measure
from nltk.metrics import precision as eval_precision
from nltk.metrics import recall as eval_recall
from nltk.probability import FreqDist


class SentimentAnalyzer:
    """
    A Sentiment Analysis tool based on machine learning approaches.
    """

    def __init__(self, classifier=None):
        self.feat_extractors = defaultdict(list)
        self.classifier = classifier

    def all_words(self, documents, labeled=None):
        """
        Return all words/tokens from the documents (with duplicates).

        :param documents: a list of (words, label) tuples.
        :param labeled: if `True`, assume that each document is represented by a
            (words, label) tuple: (list(str), str). If `False`, each document is
            considered as being a simple list of strings: list(str).
        :rtype: list(str)
        :return: A list of all words/tokens in `documents`.
        """
        all_words = []
        if labeled is None:
            labeled = documents and isinstance(documents[0], tuple)
        if labeled:
            for words, _sentiment in documents:
                all_words.extend(words)
        elif not labeled:
            for words in documents:
                all_words.extend(words)
        return all_words

    def apply_features(self, documents, labeled=None):
        """
        Apply all feature extractor functions to the documents. This is a wrapper
        around `nltk.classify.util.apply_features`.

        If `labeled=False`, return featuresets as:
            [feature_func(doc) for doc in documents]
        If `labeled=True`, return featuresets as:
            [(feature_func(tok), label) for (tok, label) in toks]

        :param documents: a list of documents. `If labeled=True`, the method expects
            a list of (words, label) tuples.
        :rtype: LazyMap
        """
        return apply_features(self.extract_features, documents, labeled)

    def unigram_word_feats(self, words, top_n=None, min_freq=0):
        """
        Return most common top_n word features.

        :param words: a list of words/tokens.
        :param top_n: number of best words/tokens to use, sorted by frequency.
        :rtype: list(str)
        :return: A list of `top_n` words/tokens (with no duplicates) sorted by
            frequency.
        """
        # Stopwords are not removed
        unigram_feats_freqs = FreqDist(word for word in words)
        return [
            w
            for w, f in unigram_feats_freqs.most_common(top_n)
            if unigram_feats_freqs[w] > min_freq
        ]

    def bigram_collocation_feats(
        self, documents, top_n=None, min_freq=3, assoc_measure=BigramAssocMeasures.pmi
    ):
        """
        Return `top_n` bigram features (using `assoc_measure`).
        Note that this method is based on bigram collocations measures, and not
        on simple bigram frequency.

        :param documents: a list (or iterable) of tokens.
        :param top_n: number of best words/tokens to use, sorted by association
            measure.
        :param assoc_measure: bigram association measure to use as score function.
        :param min_freq: the minimum number of occurrencies of bigrams to take
            into consideration.

        :return: `top_n` ngrams scored by the given association measure.
        """
        finder = BigramCollocationFinder.from_documents(documents)
        finder.apply_freq_filter(min_freq)
        return finder.nbest(assoc_measure, top_n)

    def classify(self, instance):
        """
        Classify a single instance applying the features that have already been
        stored in the SentimentAnalyzer.

        :param instance: a list (or iterable) of tokens.
        :return: the classification result given by applying the classifier.
        """
        instance_feats = self.apply_features([instance], labeled=False)
        return self.classifier.classify(instance_feats[0])

    def add_feat_extractor(self, function, **kwargs):
        """
        Add a new function to extract features from a document. This function will
        be used in extract_features().
        Important: in this step our kwargs are only representing additional parameters,
        and NOT the document we have to parse. The document will always be the first
        parameter in the parameter list, and it will be added in the extract_features()
        function.

        :param function: the extractor function to add to the list of feature extractors.
        :param kwargs: additional parameters required by the `function` function.
        """
        self.feat_extractors[function].append(kwargs)

    def extract_features(self, document):
        """
        Apply extractor functions (and their parameters) to the present document.
        We pass `document` as the first parameter of the extractor functions.
        If we want to use the same extractor function multiple times, we have to
        add it to the extractors with `add_feat_extractor` using multiple sets of
        parameters (one for each call of the extractor function).

        :param document: the document that will be passed as argument to the
            feature extractor functions.
        :return: A dictionary of populated features extracted from the document.
        :rtype: dict
        """
        all_features = {}
        for extractor in self.feat_extractors:
            for param_set in self.feat_extractors[extractor]:
                feats = extractor(document, **param_set)
            all_features.update(feats)
        return all_features

    def train(self, trainer, training_set, save_classifier=None, **kwargs):
        """
        Train classifier on the training set, optionally saving the output in the
        file specified by `save_classifier`.
        Additional arguments depend on the specific trainer used. For example,
        a MaxentClassifier can use `max_iter` parameter to specify the number
        of iterations, while a NaiveBayesClassifier cannot.

        :param trainer: `train` method of a classifier.
            E.g.: NaiveBayesClassifier.train
        :param training_set: the training set to be passed as argument to the
            classifier `train` method.
        :param save_classifier: the filename of the file where the classifier
            will be stored (optional).
        :param kwargs: additional parameters that will be passed as arguments to
            the classifier `train` function.
        :return: A classifier instance trained on the training set.
        :rtype:
        """
        print("Training classifier")
        self.classifier = trainer(training_set, **kwargs)
        if save_classifier:
            self.save_file(self.classifier, save_classifier)

        return self.classifier

    def save_file(self, content, filename):
        """
        Store `content` in `filename`. Can be used to store a SentimentAnalyzer.
        """
        print("Saving", filename, file=sys.stderr)
        with open(filename, "wb") as storage_file:
            import pickle

            # The protocol=2 parameter is for python2 compatibility
            pickle.dump(content, storage_file, protocol=2)

    def evaluate(
        self,
        test_set,
        classifier=None,
        accuracy=True,
        f_measure=True,
        precision=True,
        recall=True,
        verbose=False,
    ):
        """
        Evaluate and print classifier performance on the test set.

        :param test_set: A list of (tokens, label) tuples to use as gold set.
        :param classifier: a classifier instance (previously trained).
        :param accuracy: if `True`, evaluate classifier accuracy.
        :param f_measure: if `True`, evaluate classifier f_measure.
        :param precision: if `True`, evaluate classifier precision.
        :param recall: if `True`, evaluate classifier recall.
        :return: evaluation results.
        :rtype: dict(str): float
        """
        if classifier is None:
            classifier = self.classifier
        print(f"Evaluating {type(classifier).__name__} results...")
        metrics_results = {}
        if accuracy:
            accuracy_score = eval_accuracy(classifier, test_set)
            metrics_results["Accuracy"] = accuracy_score

        gold_results = defaultdict(set)
        test_results = defaultdict(set)
        labels = set()
        for i, (feats, label) in enumerate(test_set):
            labels.add(label)
            gold_results[label].add(i)
            observed = classifier.classify(feats)
            test_results[observed].add(i)

        for label in labels:
            if precision:
                precision_score = eval_precision(
                    gold_results[label], test_results[label]
                )
                metrics_results[f"Precision [{label}]"] = precision_score
            if recall:
                recall_score = eval_recall(gold_results[label], test_results[label])
                metrics_results[f"Recall [{label}]"] = recall_score
            if f_measure:
                f_measure_score = eval_f_measure(
                    gold_results[label], test_results[label]
                )
                metrics_results[f"F-measure [{label}]"] = f_measure_score

        # Print evaluation results (in alphabetical order)
        if verbose:
            for result in sorted(metrics_results):
                print(f"{result}: {metrics_results[result]}")

        return metrics_results

# === NexusCore/openenv\Lib\site-packages\numpy\lib\array_utils.py ===
from ._array_utils_impl import (  # noqa: F401
    __all__,
    __doc__,
    byte_bounds,
    normalize_axis_index,
    normalize_axis_tuple,
)

# === NexusCore/openenv\Lib\site-packages\numpy\_core\_methods.py ===
"""
Array methods which are called by both the C-code for the method
and the Python code for the NumPy-namespace function

"""
import os
import pickle
import warnings
from contextlib import nullcontext

import numpy as np
from numpy._core import multiarray as mu
from numpy._core import numerictypes as nt
from numpy._core import umath as um
from numpy._core.multiarray import asanyarray
from numpy._globals import _NoValue

# save those O(100) nanoseconds!
bool_dt = mu.dtype("bool")
umr_maximum = um.maximum.reduce
umr_minimum = um.minimum.reduce
umr_sum = um.add.reduce
umr_prod = um.multiply.reduce
umr_bitwise_count = um.bitwise_count
umr_any = um.logical_or.reduce
umr_all = um.logical_and.reduce

# Complex types to -> (2,)float view for fast-path computation in _var()
_complex_to_float = {
    nt.dtype(nt.csingle): nt.dtype(nt.single),
    nt.dtype(nt.cdouble): nt.dtype(nt.double),
}
# Special case for windows: ensure double takes precedence
if nt.dtype(nt.longdouble) != nt.dtype(nt.double):
    _complex_to_float.update({
        nt.dtype(nt.clongdouble): nt.dtype(nt.longdouble),
    })

# avoid keyword arguments to speed up parsing, saves about 15%-20% for very
# small reductions
def _amax(a, axis=None, out=None, keepdims=False,
          initial=_NoValue, where=True):
    return umr_maximum(a, axis, None, out, keepdims, initial, where)

def _amin(a, axis=None, out=None, keepdims=False,
          initial=_NoValue, where=True):
    return umr_minimum(a, axis, None, out, keepdims, initial, where)

def _sum(a, axis=None, dtype=None, out=None, keepdims=False,
         initial=_NoValue, where=True):
    return umr_sum(a, axis, dtype, out, keepdims, initial, where)

def _prod(a, axis=None, dtype=None, out=None, keepdims=False,
          initial=_NoValue, where=True):
    return umr_prod(a, axis, dtype, out, keepdims, initial, where)

def _any(a, axis=None, dtype=None, out=None, keepdims=False, *, where=True):
    # By default, return a boolean for any and all
    if dtype is None:
        dtype = bool_dt
    # Parsing keyword arguments is currently fairly slow, so avoid it for now
    if where is True:
        return umr_any(a, axis, dtype, out, keepdims)
    return umr_any(a, axis, dtype, out, keepdims, where=where)

def _all(a, axis=None, dtype=None, out=None, keepdims=False, *, where=True):
    # By default, return a boolean for any and all
    if dtype is None:
        dtype = bool_dt
    # Parsing keyword arguments is currently fairly slow, so avoid it for now
    if where is True:
        return umr_all(a, axis, dtype, out, keepdims)
    return umr_all(a, axis, dtype, out, keepdims, where=where)

def _count_reduce_items(arr, axis, keepdims=False, where=True):
    # fast-path for the default case
    if where is True:
        # no boolean mask given, calculate items according to axis
        if axis is None:
            axis = tuple(range(arr.ndim))
        elif not isinstance(axis, tuple):
            axis = (axis,)
        items = 1
        for ax in axis:
            items *= arr.shape[mu.normalize_axis_index(ax, arr.ndim)]
        items = nt.intp(items)
    else:
        # TODO: Optimize case when `where` is broadcast along a non-reduction
        # axis and full sum is more excessive than needed.

        # guarded to protect circular imports
        from numpy.lib._stride_tricks_impl import broadcast_to
        # count True values in (potentially broadcasted) boolean mask
        items = umr_sum(broadcast_to(where, arr.shape), axis, nt.intp, None,
                        keepdims)
    return items

def _clip(a, min=None, max=None, out=None, **kwargs):
    if a.dtype.kind in "iu":
        # If min/max is a Python integer, deal with out-of-bound values here.
        # (This enforces NEP 50 rules as no value based promotion is done.)
        if type(min) is int and min <= np.iinfo(a.dtype).min:
            min = None
        if type(max) is int and max >= np.iinfo(a.dtype).max:
            max = None

    if min is None and max is None:
        # return identity
        return um.positive(a, out=out, **kwargs)
    elif min is None:
        return um.minimum(a, max, out=out, **kwargs)
    elif max is None:
        return um.maximum(a, min, out=out, **kwargs)
    else:
        return um.clip(a, min, max, out=out, **kwargs)

def _mean(a, axis=None, dtype=None, out=None, keepdims=False, *, where=True):
    arr = asanyarray(a)

    is_float16_result = False

    rcount = _count_reduce_items(arr, axis, keepdims=keepdims, where=where)
    if rcount == 0 if where is True else umr_any(rcount == 0, axis=None):
        warnings.warn("Mean of empty slice.", RuntimeWarning, stacklevel=2)

    # Cast bool, unsigned int, and int to float64 by default
    if dtype is None:
        if issubclass(arr.dtype.type, (nt.integer, nt.bool)):
            dtype = mu.dtype('f8')
        elif issubclass(arr.dtype.type, nt.float16):
            dtype = mu.dtype('f4')
            is_float16_result = True

    ret = umr_sum(arr, axis, dtype, out, keepdims, where=where)
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(
                ret, rcount, out=ret, casting='unsafe', subok=False)
        if is_float16_result and out is None:
            ret = arr.dtype.type(ret)
    elif hasattr(ret, 'dtype'):
        if is_float16_result:
            ret = arr.dtype.type(ret / rcount)
        else:
            ret = ret.dtype.type(ret / rcount)
    else:
        ret = ret / rcount

    return ret

def _var(a, axis=None, dtype=None, out=None, ddof=0, keepdims=False, *,
         where=True, mean=None):
    arr = asanyarray(a)

    rcount = _count_reduce_items(arr, axis, keepdims=keepdims, where=where)
    # Make this warning show up on top.
    if ddof >= rcount if where is True else umr_any(ddof >= rcount, axis=None):
        warnings.warn("Degrees of freedom <= 0 for slice", RuntimeWarning,
                      stacklevel=2)

    # Cast bool, unsigned int, and int to float64 by default
    if dtype is None and issubclass(arr.dtype.type, (nt.integer, nt.bool)):
        dtype = mu.dtype('f8')

    if mean is not None:
        arrmean = mean
    else:
        # Compute the mean.
        # Note that if dtype is not of inexact type then arraymean will
        # not be either.
        arrmean = umr_sum(arr, axis, dtype, keepdims=True, where=where)
        # The shape of rcount has to match arrmean to not change the shape of
        # out in broadcasting. Otherwise, it cannot be stored back to arrmean.
        if rcount.ndim == 0:
            # fast-path for default case when where is True
            div = rcount
        else:
            # matching rcount to arrmean when where is specified as array
            div = rcount.reshape(arrmean.shape)
        if isinstance(arrmean, mu.ndarray):
            arrmean = um.true_divide(arrmean, div, out=arrmean,
                                     casting='unsafe', subok=False)
        elif hasattr(arrmean, "dtype"):
            arrmean = arrmean.dtype.type(arrmean / rcount)
        else:
            arrmean = arrmean / rcount

    # Compute sum of squared deviations from mean
    # Note that x may not be inexact and that we need it to be an array,
    # not a scalar.
    x = asanyarray(arr - arrmean)

    if issubclass(arr.dtype.type, (nt.floating, nt.integer)):
        x = um.multiply(x, x, out=x)
    # Fast-paths for built-in complex types
    elif x.dtype in _complex_to_float:
        xv = x.view(dtype=(_complex_to_float[x.dtype], (2,)))
        um.multiply(xv, xv, out=xv)
        x = um.add(xv[..., 0], xv[..., 1], out=x.real).real
    # Most general case; includes handling object arrays containing imaginary
    # numbers and complex types with non-native byteorder
    else:
        x = um.multiply(x, um.conjugate(x), out=x).real

    ret = umr_sum(x, axis, dtype, out, keepdims=keepdims, where=where)

    # Compute degrees of freedom and make sure it is not negative.
    rcount = um.maximum(rcount - ddof, 0)

    # divide by degrees of freedom
    if isinstance(ret, mu.ndarray):
        ret = um.true_divide(
                ret, rcount, out=ret, casting='unsafe', subok=False)
    elif hasattr(ret, 'dtype'):
        ret = ret.dtype.type(ret / rcount)
    else:
        ret = ret / rcount

    return ret

def _std(a, axis=None, dtype=None, out=None, ddof=0, keepdims=False, *,
         where=True, mean=None):
    ret = _var(a, axis=axis, dtype=dtype, out=out, ddof=ddof,
               keepdims=keepdims, where=where, mean=mean)

    if isinstance(ret, mu.ndarray):
        ret = um.sqrt(ret, out=ret)
    elif hasattr(ret, 'dtype'):
        ret = ret.dtype.type(um.sqrt(ret))
    else:
        ret = um.sqrt(ret)

    return ret

def _ptp(a, axis=None, out=None, keepdims=False):
    return um.subtract(
        umr_maximum(a, axis, None, out, keepdims),
        umr_minimum(a, axis, None, None, keepdims),
        out
    )

def _dump(self, file, protocol=2):
    if hasattr(file, 'write'):
        ctx = nullcontext(file)
    else:
        ctx = open(os.fspath(file), "wb")
    with ctx as f:
        pickle.dump(self, f, protocol=protocol)

def _dumps(self, protocol=2):
    return pickle.dumps(self, protocol=protocol)

def _bitwise_count(a, out=None, *, where=True, casting='same_kind',
          order='K', dtype=None, subok=True):
    return umr_bitwise_count(a, out, where=where, casting=casting,
            order=order, dtype=dtype, subok=subok)

# === NexusCore/openenv\Lib\site-packages\urllib3\contrib\emscripten\connection.py ===
from __future__ import annotations

import os
import typing

# use http.client.HTTPException for consistency with non-emscripten
from http.client import HTTPException as HTTPException  # noqa: F401
from http.client import ResponseNotReady

from ..._base_connection import _TYPE_BODY
from ...connection import HTTPConnection, ProxyConfig, port_by_scheme
from ...exceptions import TimeoutError
from ...response import BaseHTTPResponse
from ...util.connection import _TYPE_SOCKET_OPTIONS
from ...util.timeout import _DEFAULT_TIMEOUT, _TYPE_TIMEOUT
from ...util.url import Url
from .fetch import _RequestError, _TimeoutError, send_request, send_streaming_request
from .request import EmscriptenRequest
from .response import EmscriptenHttpResponseWrapper, EmscriptenResponse

if typing.TYPE_CHECKING:
    from ..._base_connection import BaseHTTPConnection, BaseHTTPSConnection


class EmscriptenHTTPConnection:
    default_port: typing.ClassVar[int] = port_by_scheme["http"]
    default_socket_options: typing.ClassVar[_TYPE_SOCKET_OPTIONS]

    timeout: None | (float)

    host: str
    port: int
    blocksize: int
    source_address: tuple[str, int] | None
    socket_options: _TYPE_SOCKET_OPTIONS | None

    proxy: Url | None
    proxy_config: ProxyConfig | None

    is_verified: bool = False
    proxy_is_verified: bool | None = None

    _response: EmscriptenResponse | None

    def __init__(
        self,
        host: str,
        port: int = 0,
        *,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 8192,
        socket_options: _TYPE_SOCKET_OPTIONS | None = None,
        proxy: Url | None = None,
        proxy_config: ProxyConfig | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout if isinstance(timeout, float) else 0.0
        self.scheme = "http"
        self._closed = True
        self._response = None
        # ignore these things because we don't
        # have control over that stuff
        self.proxy = None
        self.proxy_config = None
        self.blocksize = blocksize
        self.source_address = None
        self.socket_options = None
        self.is_verified = False

    def set_tunnel(
        self,
        host: str,
        port: int | None = 0,
        headers: typing.Mapping[str, str] | None = None,
        scheme: str = "http",
    ) -> None:
        pass

    def connect(self) -> None:
        pass

    def request(
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        # We know *at least* botocore is depending on the order of the
        # first 3 parameters so to be safe we only mark the later ones
        # as keyword-only to ensure we have space to extend.
        *,
        chunked: bool = False,
        preload_content: bool = True,
        decode_content: bool = True,
        enforce_content_length: bool = True,
    ) -> None:
        self._closed = False
        if url.startswith("/"):
            # no scheme / host / port included, make a full url
            url = f"{self.scheme}://{self.host}:{self.port}" + url
        request = EmscriptenRequest(
            url=url,
            method=method,
            timeout=self.timeout if self.timeout else 0,
            decode_content=decode_content,
        )
        request.set_body(body)
        if headers:
            for k, v in headers.items():
                request.set_header(k, v)
        self._response = None
        try:
            if not preload_content:
                self._response = send_streaming_request(request)
            if self._response is None:
                self._response = send_request(request)
        except _TimeoutError as e:
            raise TimeoutError(e.message) from e
        except _RequestError as e:
            raise HTTPException(e.message) from e

    def getresponse(self) -> BaseHTTPResponse:
        if self._response is not None:
            return EmscriptenHttpResponseWrapper(
                internal_response=self._response,
                url=self._response.request.url,
                connection=self,
            )
        else:
            raise ResponseNotReady()

    def close(self) -> None:
        self._closed = True
        self._response = None

    @property
    def is_closed(self) -> bool:
        """Whether the connection either is brand new or has been previously closed.
        If this property is True then both ``is_connected`` and ``has_connected_to_proxy``
        properties must be False.
        """
        return self._closed

    @property
    def is_connected(self) -> bool:
        """Whether the connection is actively connected to any origin (proxy or target)"""
        return True

    @property
    def has_connected_to_proxy(self) -> bool:
        """Whether the connection has successfully connected to its proxy.
        This returns False if no proxy is in use. Used to determine whether
        errors are coming from the proxy layer or from tunnelling to the target origin.
        """
        return False


class EmscriptenHTTPSConnection(EmscriptenHTTPConnection):
    default_port = port_by_scheme["https"]
    # all this is basically ignored, as browser handles https
    cert_reqs: int | str | None = None
    ca_certs: str | None = None
    ca_cert_dir: str | None = None
    ca_cert_data: None | str | bytes = None
    cert_file: str | None
    key_file: str | None
    key_password: str | None
    ssl_context: typing.Any | None
    ssl_version: int | str | None = None
    ssl_minimum_version: int | None = None
    ssl_maximum_version: int | None = None
    assert_hostname: None | str | typing.Literal[False]
    assert_fingerprint: str | None = None

    def __init__(
        self,
        host: str,
        port: int = 0,
        *,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 16384,
        socket_options: (
            None | _TYPE_SOCKET_OPTIONS
        ) = HTTPConnection.default_socket_options,
        proxy: Url | None = None,
        proxy_config: ProxyConfig | None = None,
        cert_reqs: int | str | None = None,
        assert_hostname: None | str | typing.Literal[False] = None,
        assert_fingerprint: str | None = None,
        server_hostname: str | None = None,
        ssl_context: typing.Any | None = None,
        ca_certs: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: None | str | bytes = None,
        ssl_minimum_version: int | None = None,
        ssl_maximum_version: int | None = None,
        ssl_version: int | str | None = None,  # Deprecated
        cert_file: str | None = None,
        key_file: str | None = None,
        key_password: str | None = None,
    ) -> None:
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            source_address=source_address,
            blocksize=blocksize,
            socket_options=socket_options,
            proxy=proxy,
            proxy_config=proxy_config,
        )
        self.scheme = "https"

        self.key_file = key_file
        self.cert_file = cert_file
        self.key_password = key_password
        self.ssl_context = ssl_context
        self.server_hostname = server_hostname
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint
        self.ssl_version = ssl_version
        self.ssl_minimum_version = ssl_minimum_version
        self.ssl_maximum_version = ssl_maximum_version
        self.ca_certs = ca_certs and os.path.expanduser(ca_certs)
        self.ca_cert_dir = ca_cert_dir and os.path.expanduser(ca_cert_dir)
        self.ca_cert_data = ca_cert_data

        self.cert_reqs = None

        # The browser will automatically verify all requests.
        # We have no control over that setting.
        self.is_verified = True

    def set_cert(
        self,
        key_file: str | None = None,
        cert_file: str | None = None,
        cert_reqs: int | str | None = None,
        key_password: str | None = None,
        ca_certs: str | None = None,
        assert_hostname: None | str | typing.Literal[False] = None,
        assert_fingerprint: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: None | str | bytes = None,
    ) -> None:
        pass


# verify that this class implements BaseHTTP(s) connection correctly
if typing.TYPE_CHECKING:
    _supports_http_protocol: BaseHTTPConnection = EmscriptenHTTPConnection("", 0)
    _supports_https_protocol: BaseHTTPSConnection = EmscriptenHTTPSConnection("", 0)

# === NexusCore/openenv\Lib\site-packages\PIL\PcfFontFile.py ===
#
# THIS IS WORK IN PROGRESS
#
# The Python Imaging Library
# $Id$
#
# portable compiled font file parser
#
# history:
# 1997-08-19 fl   created
# 2003-09-13 fl   fixed loading of unicode fonts
#
# Copyright (c) 1997-2003 by Secret Labs AB.
# Copyright (c) 1997-2003 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
from typing import BinaryIO, Callable

from . import FontFile, Image
from ._binary import i8
from ._binary import i16be as b16
from ._binary import i16le as l16
from ._binary import i32be as b32
from ._binary import i32le as l32

# --------------------------------------------------------------------
# declarations

PCF_MAGIC = 0x70636601  # "\x01fcp"

PCF_PROPERTIES = 1 << 0
PCF_ACCELERATORS = 1 << 1
PCF_METRICS = 1 << 2
PCF_BITMAPS = 1 << 3
PCF_INK_METRICS = 1 << 4
PCF_BDF_ENCODINGS = 1 << 5
PCF_SWIDTHS = 1 << 6
PCF_GLYPH_NAMES = 1 << 7
PCF_BDF_ACCELERATORS = 1 << 8

BYTES_PER_ROW: list[Callable[[int], int]] = [
    lambda bits: ((bits + 7) >> 3),
    lambda bits: ((bits + 15) >> 3) & ~1,
    lambda bits: ((bits + 31) >> 3) & ~3,
    lambda bits: ((bits + 63) >> 3) & ~7,
]


def sz(s: bytes, o: int) -> bytes:
    return s[o : s.index(b"\0", o)]


class PcfFontFile(FontFile.FontFile):
    """Font file plugin for the X11 PCF format."""

    name = "name"

    def __init__(self, fp: BinaryIO, charset_encoding: str = "iso8859-1"):
        self.charset_encoding = charset_encoding

        magic = l32(fp.read(4))
        if magic != PCF_MAGIC:
            msg = "not a PCF file"
            raise SyntaxError(msg)

        super().__init__()

        count = l32(fp.read(4))
        self.toc = {}
        for i in range(count):
            type = l32(fp.read(4))
            self.toc[type] = l32(fp.read(4)), l32(fp.read(4)), l32(fp.read(4))

        self.fp = fp

        self.info = self._load_properties()

        metrics = self._load_metrics()
        bitmaps = self._load_bitmaps(metrics)
        encoding = self._load_encoding()

        #
        # create glyph structure

        for ch, ix in enumerate(encoding):
            if ix is not None:
                (
                    xsize,
                    ysize,
                    left,
                    right,
                    width,
                    ascent,
                    descent,
                    attributes,
                ) = metrics[ix]
                self.glyph[ch] = (
                    (width, 0),
                    (left, descent - ysize, xsize + left, descent),
                    (0, 0, xsize, ysize),
                    bitmaps[ix],
                )

    def _getformat(
        self, tag: int
    ) -> tuple[BinaryIO, int, Callable[[bytes], int], Callable[[bytes], int]]:
        format, size, offset = self.toc[tag]

        fp = self.fp
        fp.seek(offset)

        format = l32(fp.read(4))

        if format & 4:
            i16, i32 = b16, b32
        else:
            i16, i32 = l16, l32

        return fp, format, i16, i32

    def _load_properties(self) -> dict[bytes, bytes | int]:
        #
        # font properties

        properties = {}

        fp, format, i16, i32 = self._getformat(PCF_PROPERTIES)

        nprops = i32(fp.read(4))

        # read property description
        p = [(i32(fp.read(4)), i8(fp.read(1)), i32(fp.read(4))) for _ in range(nprops)]

        if nprops & 3:
            fp.seek(4 - (nprops & 3), io.SEEK_CUR)  # pad

        data = fp.read(i32(fp.read(4)))

        for k, s, v in p:
            property_value: bytes | int = sz(data, v) if s else v
            properties[sz(data, k)] = property_value

        return properties

    def _load_metrics(self) -> list[tuple[int, int, int, int, int, int, int, int]]:
        #
        # font metrics

        metrics: list[tuple[int, int, int, int, int, int, int, int]] = []

        fp, format, i16, i32 = self._getformat(PCF_METRICS)

        append = metrics.append

        if (format & 0xFF00) == 0x100:
            # "compressed" metrics
            for i in range(i16(fp.read(2))):
                left = i8(fp.read(1)) - 128
                right = i8(fp.read(1)) - 128
                width = i8(fp.read(1)) - 128
                ascent = i8(fp.read(1)) - 128
                descent = i8(fp.read(1)) - 128
                xsize = right - left
                ysize = ascent + descent
                append((xsize, ysize, left, right, width, ascent, descent, 0))

        else:
            # "jumbo" metrics
            for i in range(i32(fp.read(4))):
                left = i16(fp.read(2))
                right = i16(fp.read(2))
                width = i16(fp.read(2))
                ascent = i16(fp.read(2))
                descent = i16(fp.read(2))
                attributes = i16(fp.read(2))
                xsize = right - left
                ysize = ascent + descent
                append((xsize, ysize, left, right, width, ascent, descent, attributes))

        return metrics

    def _load_bitmaps(
        self, metrics: list[tuple[int, int, int, int, int, int, int, int]]
    ) -> list[Image.Image]:
        #
        # bitmap data

        fp, format, i16, i32 = self._getformat(PCF_BITMAPS)

        nbitmaps = i32(fp.read(4))

        if nbitmaps != len(metrics):
            msg = "Wrong number of bitmaps"
            raise OSError(msg)

        offsets = [i32(fp.read(4)) for _ in range(nbitmaps)]

        bitmap_sizes = [i32(fp.read(4)) for _ in range(4)]

        # byteorder = format & 4  # non-zero => MSB
        bitorder = format & 8  # non-zero => MSB
        padindex = format & 3

        bitmapsize = bitmap_sizes[padindex]
        offsets.append(bitmapsize)

        data = fp.read(bitmapsize)

        pad = BYTES_PER_ROW[padindex]
        mode = "1;R"
        if bitorder:
            mode = "1"

        bitmaps = []
        for i in range(nbitmaps):
            xsize, ysize = metrics[i][:2]
            b, e = offsets[i : i + 2]
            bitmaps.append(
                Image.frombytes("1", (xsize, ysize), data[b:e], "raw", mode, pad(xsize))
            )

        return bitmaps

    def _load_encoding(self) -> list[int | None]:
        fp, format, i16, i32 = self._getformat(PCF_BDF_ENCODINGS)

        first_col, last_col = i16(fp.read(2)), i16(fp.read(2))
        first_row, last_row = i16(fp.read(2)), i16(fp.read(2))

        i16(fp.read(2))  # default

        nencoding = (last_col - first_col + 1) * (last_row - first_row + 1)

        # map character code to bitmap index
        encoding: list[int | None] = [None] * min(256, nencoding)

        encoding_offsets = [i16(fp.read(2)) for _ in range(nencoding)]

        for i in range(first_col, len(encoding)):
            try:
                encoding_offset = encoding_offsets[
                    ord(bytearray([i]).decode(self.charset_encoding))
                ]
                if encoding_offset != 0xFFFF:
                    encoding[i] = encoding_offset
            except UnicodeDecodeError:
                # character is not supported in selected encoding
                pass

        return encoding

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\fixedTools.py ===
"""
The `OpenType specification <https://docs.microsoft.com/en-us/typography/opentype/spec/otff#data-types>`_
defines two fixed-point data types:

``Fixed``
	A 32-bit signed fixed-point number with a 16 bit twos-complement
	magnitude component and 16 fractional bits.
``F2DOT14``
	A 16-bit signed fixed-point number with a 2 bit twos-complement
	magnitude component and 14 fractional bits.

To support reading and writing data with these data types, this module provides
functions for converting between fixed-point, float and string representations.

.. data:: MAX_F2DOT14

	The maximum value that can still fit in an F2Dot14. (1.99993896484375)
"""

from .roundTools import otRound, nearestMultipleShortestRepr
import logging

log = logging.getLogger(__name__)

__all__ = [
    "MAX_F2DOT14",
    "fixedToFloat",
    "floatToFixed",
    "floatToFixedToFloat",
    "floatToFixedToStr",
    "fixedToStr",
    "strToFixed",
    "strToFixedToFloat",
    "ensureVersionIsLong",
    "versionToFixed",
]


MAX_F2DOT14 = 0x7FFF / (1 << 14)


def fixedToFloat(value, precisionBits):
    """Converts a fixed-point number to a float given the number of
    precision bits.

    Args:
            value (int): Number in fixed-point format.
            precisionBits (int): Number of precision bits.

    Returns:
            Floating point value.

    Examples::

            >>> import math
            >>> f = fixedToFloat(-10139, precisionBits=14)
            >>> math.isclose(f, -0.61883544921875)
            True
    """
    return value / (1 << precisionBits)


def floatToFixed(value, precisionBits):
    """Converts a float to a fixed-point number given the number of
    precision bits.

    Args:
            value (float): Floating point value.
            precisionBits (int): Number of precision bits.

    Returns:
            int: Fixed-point representation.

    Examples::

            >>> floatToFixed(-0.61883544921875, precisionBits=14)
            -10139
            >>> floatToFixed(-0.61884, precisionBits=14)
            -10139
    """
    return otRound(value * (1 << precisionBits))


def floatToFixedToFloat(value, precisionBits):
    """Converts a float to a fixed-point number and back again.

    By converting the float to fixed, rounding it, and converting it back
    to float again, this returns a floating point values which is exactly
    representable in fixed-point format.

    Note: this **is** equivalent to ``fixedToFloat(floatToFixed(value))``.

    Args:
            value (float): The input floating point value.
            precisionBits (int): Number of precision bits.

    Returns:
            float: The transformed and rounded value.

    Examples::
            >>> import math
            >>> f1 = -0.61884
            >>> f2 = floatToFixedToFloat(-0.61884, precisionBits=14)
            >>> f1 != f2
            True
            >>> math.isclose(f2, -0.61883544921875)
            True
    """
    scale = 1 << precisionBits
    return otRound(value * scale) / scale


def fixedToStr(value, precisionBits):
    """Converts a fixed-point number to a string representing a decimal float.

    This chooses the float that has the shortest decimal representation (the least
    number of fractional decimal digits).

    For example, to convert a fixed-point number in a 2.14 format, use
    ``precisionBits=14``::

            >>> fixedToStr(-10139, precisionBits=14)
            '-0.61884'

    This is pretty slow compared to the simple division used in ``fixedToFloat``.
    Use sporadically when you need to serialize or print the fixed-point number in
    a human-readable form.
    It uses nearestMultipleShortestRepr under the hood.

    Args:
            value (int): The fixed-point value to convert.
            precisionBits (int): Number of precision bits, *up to a maximum of 16*.

    Returns:
            str: A string representation of the value.
    """
    scale = 1 << precisionBits
    return nearestMultipleShortestRepr(value / scale, factor=1.0 / scale)


def strToFixed(string, precisionBits):
    """Converts a string representing a decimal float to a fixed-point number.

    Args:
            string (str): A string representing a decimal float.
            precisionBits (int): Number of precision bits, *up to a maximum of 16*.

    Returns:
            int: Fixed-point representation.

    Examples::

            >>> ## to convert a float string to a 2.14 fixed-point number:
            >>> strToFixed('-0.61884', precisionBits=14)
            -10139
    """
    value = float(string)
    return otRound(value * (1 << precisionBits))


def strToFixedToFloat(string, precisionBits):
    """Convert a string to a decimal float with fixed-point rounding.

    This first converts string to a float, then turns it into a fixed-point
    number with ``precisionBits`` fractional binary digits, then back to a
    float again.

    This is simply a shorthand for fixedToFloat(floatToFixed(float(s))).

    Args:
            string (str): A string representing a decimal float.
            precisionBits (int): Number of precision bits.

    Returns:
            float: The transformed and rounded value.

    Examples::

            >>> import math
            >>> s = '-0.61884'
            >>> bits = 14
            >>> f = strToFixedToFloat(s, precisionBits=bits)
            >>> math.isclose(f, -0.61883544921875)
            True
            >>> f == fixedToFloat(floatToFixed(float(s), precisionBits=bits), precisionBits=bits)
            True
    """
    value = float(string)
    scale = 1 << precisionBits
    return otRound(value * scale) / scale


def floatToFixedToStr(value, precisionBits):
    """Convert float to string with fixed-point rounding.

    This uses the shortest decimal representation (ie. the least
    number of fractional decimal digits) to represent the equivalent
    fixed-point number with ``precisionBits`` fractional binary digits.
    It uses nearestMultipleShortestRepr under the hood.

    >>> floatToFixedToStr(-0.61883544921875, precisionBits=14)
    '-0.61884'

    Args:
            value (float): The float value to convert.
            precisionBits (int): Number of precision bits, *up to a maximum of 16*.

    Returns:
            str: A string representation of the value.

    """
    scale = 1 << precisionBits
    return nearestMultipleShortestRepr(value, factor=1.0 / scale)


def ensureVersionIsLong(value):
    """Ensure a table version is an unsigned long.

    OpenType table version numbers are expressed as a single unsigned long
    comprising of an unsigned short major version and unsigned short minor
    version. This function detects if the value to be used as a version number
    looks too small (i.e. is less than ``0x10000``), and converts it to
    fixed-point using :func:`floatToFixed` if so.

    Args:
            value (Number): a candidate table version number.

    Returns:
            int: A table version number, possibly corrected to fixed-point.
    """
    if value < 0x10000:
        newValue = floatToFixed(value, 16)
        log.warning(
            "Table version value is a float: %.4f; " "fix to use hex instead: 0x%08x",
            value,
            newValue,
        )
        value = newValue
    return value


def versionToFixed(value):
    """Ensure a table version number is fixed-point.

    Args:
            value (str): a candidate table version number.

    Returns:
            int: A table version number, possibly corrected to fixed-point.
    """
    value = int(value, 0) if value.startswith("0") else float(value)
    value = ensureVersionIsLong(value)
    return value

# === NexusCore/openenv\Lib\site-packages\fontTools\subset\svg.py ===
from __future__ import annotations

import re
from functools import lru_cache
from itertools import chain, count
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

try:
    from lxml import etree
except ImportError:
    # lxml is required for subsetting SVG, but we prefer to delay the import error
    # until subset_glyphs() is called (i.e. if font to subset has an 'SVG ' table)
    etree = None

from fontTools import ttLib
from fontTools.subset.util import _add_method
from fontTools.ttLib.tables.S_V_G_ import SVGDocument


__all__ = ["subset_glyphs"]


GID_RE = re.compile(r"^glyph(\d+)$")

NAMESPACES = {
    "svg": "http://www.w3.org/2000/svg",
    "xlink": "http://www.w3.org/1999/xlink",
}
XLINK_HREF = f'{{{NAMESPACES["xlink"]}}}href'


# TODO(antrotype): Replace with functools.cache once we are 3.9+
@lru_cache(maxsize=None)
def xpath(path):
    # compile XPath upfront, caching result to reuse on multiple elements
    return etree.XPath(path, namespaces=NAMESPACES)


def group_elements_by_id(tree: etree.Element) -> Dict[str, etree.Element]:
    # select all svg elements with 'id' attribute no matter where they are
    # including the root element itself:
    # https://github.com/fonttools/fonttools/issues/2548
    return {el.attrib["id"]: el for el in xpath("//svg:*[@id]")(tree)}


def parse_css_declarations(style_attr: str) -> Dict[str, str]:
    # https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/style
    # https://developer.mozilla.org/en-US/docs/Web/CSS/Syntax#css_declarations
    result = {}
    for declaration in style_attr.split(";"):
        if declaration.count(":") == 1:
            property_name, value = declaration.split(":")
            property_name = property_name.strip()
            result[property_name] = value.strip()
        elif declaration.strip():
            raise ValueError(f"Invalid CSS declaration syntax: {declaration}")
    return result


def iter_referenced_ids(tree: etree.Element) -> Iterator[str]:
    # Yield all the ids that can be reached via references from this element tree.
    # We currently support xlink:href (as used by <use> and gradient templates),
    # and local url(#...) links found in fill or clip-path attributes
    # TODO(anthrotype): Check we aren't missing other supported kinds of reference
    find_svg_elements_with_references = xpath(
        ".//svg:*[ "
        "starts-with(@xlink:href, '#') "
        "or starts-with(@fill, 'url(#') "
        "or starts-with(@clip-path, 'url(#') "
        "or contains(@style, ':url(#') "
        "]",
    )
    for el in chain([tree], find_svg_elements_with_references(tree)):
        ref_id = href_local_target(el)
        if ref_id is not None:
            yield ref_id

        attrs = el.attrib
        if "style" in attrs:
            attrs = {**dict(attrs), **parse_css_declarations(el.attrib["style"])}
        for attr in ("fill", "clip-path"):
            if attr in attrs:
                value = attrs[attr]
                if value.startswith("url(#") and value.endswith(")"):
                    ref_id = value[5:-1]
                    assert ref_id
                    yield ref_id


def closure_element_ids(
    elements: Dict[str, etree.Element], element_ids: Set[str]
) -> None:
    # Expand the initial subset of element ids to include ids that can be reached
    # via references from the initial set.
    unvisited = element_ids
    while unvisited:
        referenced: Set[str] = set()
        for el_id in unvisited:
            if el_id not in elements:
                # ignore dangling reference; not our job to validate svg
                continue
            referenced.update(iter_referenced_ids(elements[el_id]))
        referenced -= element_ids
        element_ids.update(referenced)
        unvisited = referenced


def subset_elements(el: etree.Element, retained_ids: Set[str]) -> bool:
    # Keep elements if their id is in the subset, or any of their children's id is.
    # Drop elements whose id is not in the subset, and either have no children,
    # or all their children are being dropped.
    if el.attrib.get("id") in retained_ids:
        # if id is in the set, don't recurse; keep whole subtree
        return True
    # recursively subset all the children; we use a list comprehension instead
    # of a parentheses-less generator expression because we don't want any() to
    # short-circuit, as our function has a side effect of dropping empty elements.
    if any([subset_elements(e, retained_ids) for e in el]):
        return True
    assert len(el) == 0
    parent = el.getparent()
    if parent is not None:
        parent.remove(el)
    return False


def remap_glyph_ids(
    svg: etree.Element, glyph_index_map: Dict[int, int]
) -> Dict[str, str]:
    # Given {old_gid: new_gid} map, rename all elements containing id="glyph{gid}"
    # special attributes
    elements = group_elements_by_id(svg)
    id_map = {}
    for el_id, el in elements.items():
        m = GID_RE.match(el_id)
        if not m:
            continue
        old_index = int(m.group(1))
        new_index = glyph_index_map.get(old_index)
        if new_index is not None:
            if old_index == new_index:
                continue
            new_id = f"glyph{new_index}"
        else:
            # If the old index is missing, the element correspond to a glyph that was
            # excluded from the font's subset.
            # We rename it to avoid clashes with the new GIDs or other element ids.
            new_id = f".{el_id}"
            n = count(1)
            while new_id in elements:
                new_id = f"{new_id}.{next(n)}"

        id_map[el_id] = new_id
        el.attrib["id"] = new_id

    return id_map


def href_local_target(el: etree.Element) -> Optional[str]:
    if XLINK_HREF in el.attrib:
        href = el.attrib[XLINK_HREF]
        if href.startswith("#") and len(href) > 1:
            return href[1:]  # drop the leading #
    return None


def update_glyph_href_links(svg: etree.Element, id_map: Dict[str, str]) -> None:
    # update all xlink:href="#glyph..." attributes to point to the new glyph ids
    for el in xpath(".//svg:*[starts-with(@xlink:href, '#glyph')]")(svg):
        old_id = href_local_target(el)
        assert old_id is not None
        if old_id in id_map:
            new_id = id_map[old_id]
            el.attrib[XLINK_HREF] = f"#{new_id}"


def ranges(ints: Iterable[int]) -> Iterator[Tuple[int, int]]:
    # Yield sorted, non-overlapping (min, max) ranges of consecutive integers
    sorted_ints = iter(sorted(set(ints)))
    try:
        start = end = next(sorted_ints)
    except StopIteration:
        return
    for v in sorted_ints:
        if v - 1 == end:
            end = v
        else:
            yield (start, end)
            start = end = v
    yield (start, end)


@_add_method(ttLib.getTableClass("SVG "))
def subset_glyphs(self, s) -> bool:
    if etree is None:
        raise ImportError("No module named 'lxml', required to subset SVG")

    # glyph names (before subsetting)
    glyph_order: List[str] = s.orig_glyph_order
    # map from glyph names to original glyph indices
    rev_orig_glyph_map: Dict[str, int] = s.reverseOrigGlyphMap
    # map from original to new glyph indices (after subsetting)
    glyph_index_map: Dict[int, int] = s.glyph_index_map

    new_docs: List[SVGDocument] = []
    for doc in self.docList:
        glyphs = {
            glyph_order[i] for i in range(doc.startGlyphID, doc.endGlyphID + 1)
        }.intersection(s.glyphs)
        if not glyphs:
            # no intersection: we can drop the whole record
            continue

        svg = etree.fromstring(
            # encode because fromstring dislikes xml encoding decl if input is str.
            # SVG xml encoding must be utf-8 as per OT spec.
            doc.data.encode("utf-8"),
            parser=etree.XMLParser(
                # Disable libxml2 security restrictions to support very deep trees.
                # Without this we would get an error like this:
                # `lxml.etree.XMLSyntaxError: internal error: Huge input lookup`
                # when parsing big fonts e.g. noto-emoji-picosvg.ttf.
                huge_tree=True,
                # ignore blank text as it's not meaningful in OT-SVG; it also prevents
                # dangling tail text after removing an element when pretty_print=True
                remove_blank_text=True,
                # don't replace entities; we don't expect any in OT-SVG and they may
                # be abused for XXE attacks
                resolve_entities=False,
            ),
        )

        elements = group_elements_by_id(svg)
        gids = {rev_orig_glyph_map[g] for g in glyphs}
        element_ids = {f"glyph{i}" for i in gids}
        closure_element_ids(elements, element_ids)

        if not subset_elements(svg, element_ids):
            continue

        if not s.options.retain_gids:
            id_map = remap_glyph_ids(svg, glyph_index_map)
            update_glyph_href_links(svg, id_map)

        new_doc = etree.tostring(svg, pretty_print=s.options.pretty_svg).decode("utf-8")

        new_gids = (glyph_index_map[i] for i in gids)
        for start, end in ranges(new_gids):
            new_docs.append(SVGDocument(new_doc, start, end, doc.compressed))

    self.docList = new_docs

    return bool(self.docList)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\multiVarStore.py ===
from fontTools.misc.roundTools import noRound, otRound
from fontTools.misc.intTools import bit_count
from fontTools.misc.vector import Vector
from fontTools.ttLib.tables import otTables as ot
from fontTools.varLib.models import supportScalar
import fontTools.varLib.varStore  # For monkey-patching
from fontTools.varLib.builder import (
    buildVarRegionList,
    buildSparseVarRegionList,
    buildSparseVarRegion,
    buildMultiVarStore,
    buildMultiVarData,
)
from fontTools.misc.iterTools import batched
from functools import partial
from collections import defaultdict
from heapq import heappush, heappop


NO_VARIATION_INDEX = ot.NO_VARIATION_INDEX
ot.MultiVarStore.NO_VARIATION_INDEX = NO_VARIATION_INDEX


def _getLocationKey(loc):
    return tuple(sorted(loc.items(), key=lambda kv: kv[0]))


class OnlineMultiVarStoreBuilder(object):
    def __init__(self, axisTags):
        self._axisTags = axisTags
        self._regionMap = {}
        self._regionList = buildSparseVarRegionList([], axisTags)
        self._store = buildMultiVarStore(self._regionList, [])
        self._data = None
        self._model = None
        self._supports = None
        self._varDataIndices = {}
        self._varDataCaches = {}
        self._cache = None

    def setModel(self, model):
        self.setSupports(model.supports)
        self._model = model

    def setSupports(self, supports):
        self._model = None
        self._supports = list(supports)
        if not self._supports[0]:
            del self._supports[0]  # Drop base master support
        self._cache = None
        self._data = None

    def finish(self):
        self._regionList.RegionCount = len(self._regionList.Region)
        self._store.MultiVarDataCount = len(self._store.MultiVarData)
        return self._store

    def _add_MultiVarData(self):
        regionMap = self._regionMap
        regionList = self._regionList

        regions = self._supports
        regionIndices = []
        for region in regions:
            key = _getLocationKey(region)
            idx = regionMap.get(key)
            if idx is None:
                varRegion = buildSparseVarRegion(region, self._axisTags)
                idx = regionMap[key] = len(regionList.Region)
                regionList.Region.append(varRegion)
            regionIndices.append(idx)

        # Check if we have one already...
        key = tuple(regionIndices)
        varDataIdx = self._varDataIndices.get(key)
        if varDataIdx is not None:
            self._outer = varDataIdx
            self._data = self._store.MultiVarData[varDataIdx]
            self._cache = self._varDataCaches[key]
            if len(self._data.Item) == 0xFFFF:
                # This is full.  Need new one.
                varDataIdx = None

        if varDataIdx is None:
            self._data = buildMultiVarData(regionIndices, [])
            self._outer = len(self._store.MultiVarData)
            self._store.MultiVarData.append(self._data)
            self._varDataIndices[key] = self._outer
            if key not in self._varDataCaches:
                self._varDataCaches[key] = {}
            self._cache = self._varDataCaches[key]

    def storeMasters(self, master_values, *, round=round):
        deltas = self._model.getDeltas(master_values, round=round)
        base = deltas.pop(0)
        return base, self.storeDeltas(deltas, round=noRound)

    def storeDeltas(self, deltas, *, round=round):
        deltas = tuple(round(d) for d in deltas)

        if not any(deltas):
            return NO_VARIATION_INDEX

        deltas_tuple = tuple(tuple(d) for d in deltas)

        if not self._data:
            self._add_MultiVarData()

        varIdx = self._cache.get(deltas_tuple)
        if varIdx is not None:
            return varIdx

        inner = len(self._data.Item)
        if inner == 0xFFFF:
            # Full array. Start new one.
            self._add_MultiVarData()
            return self.storeDeltas(deltas, round=noRound)
        self._data.addItem(deltas, round=noRound)

        varIdx = (self._outer << 16) + inner
        self._cache[deltas_tuple] = varIdx
        return varIdx


def MultiVarData_addItem(self, deltas, *, round=round):
    deltas = tuple(round(d) for d in deltas)

    assert len(deltas) == self.VarRegionCount

    values = []
    for d in deltas:
        values.extend(d)

    self.Item.append(values)
    self.ItemCount = len(self.Item)


ot.MultiVarData.addItem = MultiVarData_addItem


def SparseVarRegion_get_support(self, fvar_axes):
    return {
        fvar_axes[reg.AxisIndex].axisTag: (reg.StartCoord, reg.PeakCoord, reg.EndCoord)
        for reg in self.SparseVarRegionAxis
    }


ot.SparseVarRegion.get_support = SparseVarRegion_get_support


def MultiVarStore___bool__(self):
    return bool(self.MultiVarData)


ot.MultiVarStore.__bool__ = MultiVarStore___bool__


class MultiVarStoreInstancer(object):
    def __init__(self, multivarstore, fvar_axes, location={}):
        self.fvar_axes = fvar_axes
        assert multivarstore is None or multivarstore.Format == 1
        self._varData = multivarstore.MultiVarData if multivarstore else []
        self._regions = (
            multivarstore.SparseVarRegionList.Region if multivarstore else []
        )
        self.setLocation(location)

    def setLocation(self, location):
        self.location = dict(location)
        self._clearCaches()

    def _clearCaches(self):
        self._scalars = {}

    def _getScalar(self, regionIdx):
        scalar = self._scalars.get(regionIdx)
        if scalar is None:
            support = self._regions[regionIdx].get_support(self.fvar_axes)
            scalar = supportScalar(self.location, support)
            self._scalars[regionIdx] = scalar
        return scalar

    @staticmethod
    def interpolateFromDeltasAndScalars(deltas, scalars):
        if not deltas:
            return Vector([])
        assert len(deltas) % len(scalars) == 0, (len(deltas), len(scalars))
        m = len(deltas) // len(scalars)
        delta = Vector([0] * m)
        for d, s in zip(batched(deltas, m), scalars):
            if not s:
                continue
            delta += Vector(d) * s
        return delta

    def __getitem__(self, varidx):
        major, minor = varidx >> 16, varidx & 0xFFFF
        if varidx == NO_VARIATION_INDEX:
            return Vector([])
        varData = self._varData
        scalars = [self._getScalar(ri) for ri in varData[major].VarRegionIndex]
        deltas = varData[major].Item[minor]
        return self.interpolateFromDeltasAndScalars(deltas, scalars)

    def interpolateFromDeltas(self, varDataIndex, deltas):
        varData = self._varData
        scalars = [self._getScalar(ri) for ri in varData[varDataIndex].VarRegionIndex]
        return self.interpolateFromDeltasAndScalars(deltas, scalars)


def MultiVarStore_subset_varidxes(self, varIdxes):
    return ot.VarStore.subset_varidxes(self, varIdxes, VarData="MultiVarData")


def MultiVarStore_prune_regions(self):
    return ot.VarStore.prune_regions(
        self, VarData="MultiVarData", VarRegionList="SparseVarRegionList"
    )


ot.MultiVarStore.prune_regions = MultiVarStore_prune_regions
ot.MultiVarStore.subset_varidxes = MultiVarStore_subset_varidxes


def MultiVarStore_get_supports(self, major, fvarAxes):
    supports = []
    varData = self.MultiVarData[major]
    for regionIdx in varData.VarRegionIndex:
        region = self.SparseVarRegionList.Region[regionIdx]
        support = region.get_support(fvarAxes)
        supports.append(support)
    return supports


ot.MultiVarStore.get_supports = MultiVarStore_get_supports


def VARC_collect_varidxes(self, varidxes):
    for glyph in self.VarCompositeGlyphs.VarCompositeGlyph:
        for component in glyph.components:
            varidxes.add(component.axisValuesVarIndex)
            varidxes.add(component.transformVarIndex)


def VARC_remap_varidxes(self, varidxes_map):
    for glyph in self.VarCompositeGlyphs.VarCompositeGlyph:
        for component in glyph.components:
            component.axisValuesVarIndex = varidxes_map[component.axisValuesVarIndex]
            component.transformVarIndex = varidxes_map[component.transformVarIndex]


ot.VARC.collect_varidxes = VARC_collect_varidxes
ot.VARC.remap_varidxes = VARC_remap_varidxes

# === NexusCore/openenv\Lib\site-packages\google\api_core\gapic_v1\method.py ===
# Copyright 2017 Google LLC
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

"""Helpers for wrapping low-level gRPC methods with common functionality.

This is used by gapic clients to provide common error mapping, retry, timeout,
compression, pagination, and long-running operations to gRPC methods.
"""

import enum
import functools

from google.api_core import grpc_helpers
from google.api_core.gapic_v1 import client_info
from google.api_core.timeout import TimeToDeadlineTimeout

USE_DEFAULT_METADATA = object()


class _MethodDefault(enum.Enum):
    # Uses enum so that pytype/mypy knows that this is the only possible value.
    # https://stackoverflow.com/a/60605919/101923
    #
    # Literal[_DEFAULT_VALUE] is an alternative, but only added in Python 3.8.
    # https://docs.python.org/3/library/typing.html#typing.Literal
    _DEFAULT_VALUE = object()


DEFAULT = _MethodDefault._DEFAULT_VALUE
"""Sentinel value indicating that a retry, timeout, or compression argument was unspecified,
so the default should be used."""


def _is_not_none_or_false(value):
    return value is not None and value is not False


def _apply_decorators(func, decorators):
    """Apply a list of decorators to a given function.

    ``decorators`` may contain items that are ``None`` or ``False`` which will
    be ignored.
    """
    filtered_decorators = filter(_is_not_none_or_false, reversed(decorators))

    for decorator in filtered_decorators:
        func = decorator(func)

    return func


class _GapicCallable(object):
    """Callable that applies retry, timeout, and metadata logic.

    Args:
        target (Callable): The low-level RPC method.
        retry (google.api_core.retry.Retry): The default retry for the
            callable. If ``None``, this callable will not retry by default
        timeout (google.api_core.timeout.Timeout): The default timeout for the
            callable (i.e. duration of time within which an RPC must terminate
            after its start, not to be confused with deadline). If ``None``,
            this callable will not specify a timeout argument to the low-level
            RPC method.
        compression (grpc.Compression): The default compression for the callable.
            If ``None``, this callable will not specify a compression argument
            to the low-level RPC method.
        metadata (Sequence[Tuple[str, str]]): Additional metadata that is
            provided to the RPC method on every invocation. This is merged with
            any metadata specified during invocation. If ``None``, no
            additional metadata will be passed to the RPC method.
    """

    def __init__(
        self,
        target,
        retry,
        timeout,
        compression,
        metadata=None,
    ):
        self._target = target
        self._retry = retry
        self._timeout = timeout
        self._compression = compression
        self._metadata = metadata

    def __call__(
        self, *args, timeout=DEFAULT, retry=DEFAULT, compression=DEFAULT, **kwargs
    ):
        """Invoke the low-level RPC with retry, timeout, compression, and metadata."""

        if retry is DEFAULT:
            retry = self._retry

        if timeout is DEFAULT:
            timeout = self._timeout

        if compression is DEFAULT:
            compression = self._compression

        if isinstance(timeout, (int, float)):
            timeout = TimeToDeadlineTimeout(timeout=timeout)

        # Apply all applicable decorators.
        wrapped_func = _apply_decorators(self._target, [retry, timeout])

        # Add the user agent metadata to the call.
        if self._metadata is not None:
            metadata = kwargs.get("metadata", [])
            # Due to the nature of invocation, None should be treated the same
            # as not specified.
            if metadata is None:
                metadata = []
            metadata = list(metadata)
            metadata.extend(self._metadata)
            kwargs["metadata"] = metadata
        if self._compression is not None:
            kwargs["compression"] = compression

        return wrapped_func(*args, **kwargs)


def wrap_method(
    func,
    default_retry=None,
    default_timeout=None,
    default_compression=None,
    client_info=client_info.DEFAULT_CLIENT_INFO,
    *,
    with_call=False,
):
    """Wrap an RPC method with common behavior.

    This applies common error wrapping, retry, timeout, and compression behavior to a function.
    The wrapped function will take optional ``retry``, ``timeout``, and ``compression``
    arguments.

    For example::

        import google.api_core.gapic_v1.method
        from google.api_core import retry
        from google.api_core import timeout
        from grpc import Compression

        # The original RPC method.
        def get_topic(name, timeout=None):
            request = publisher_v2.GetTopicRequest(name=name)
            return publisher_stub.GetTopic(request, timeout=timeout)

        default_retry = retry.Retry(deadline=60)
        default_timeout = timeout.Timeout(deadline=60)
        default_compression = Compression.NoCompression
        wrapped_get_topic = google.api_core.gapic_v1.method.wrap_method(
            get_topic, default_retry)

        # Execute get_topic with default retry and timeout:
        response = wrapped_get_topic()

        # Execute get_topic without doing any retying but with the default
        # timeout:
        response = wrapped_get_topic(retry=None)

        # Execute get_topic but only retry on 5xx errors:
        my_retry = retry.Retry(retry.if_exception_type(
            exceptions.InternalServerError))
        response = wrapped_get_topic(retry=my_retry)

    The way this works is by late-wrapping the given function with the retry
    and timeout decorators. Essentially, when ``wrapped_get_topic()`` is
    called:

    * ``get_topic()`` is first wrapped with the ``timeout`` into
      ``get_topic_with_timeout``.
    * ``get_topic_with_timeout`` is wrapped with the ``retry`` into
      ``get_topic_with_timeout_and_retry()``.
    * The final ``get_topic_with_timeout_and_retry`` is called passing through
      the ``args``  and ``kwargs``.

    The callstack is therefore::

        method.__call__() ->
            Retry.__call__() ->
                Timeout.__call__() ->
                    wrap_errors() ->
                        get_topic()

    Note that if ``timeout`` or ``retry`` is ``None``, then they are not
    applied to the function. For example,
    ``wrapped_get_topic(timeout=None, retry=None)`` is more or less
    equivalent to just calling ``get_topic`` but with error re-mapping.

    Args:
        func (Callable[Any]): The function to wrap. It should accept an
            optional ``timeout`` argument. If ``metadata`` is not ``None``, it
            should accept a ``metadata`` argument.
        default_retry (Optional[google.api_core.Retry]): The default retry
            strategy. If ``None``, the method will not retry by default.
        default_timeout (Optional[google.api_core.Timeout]): The default
            timeout strategy. Can also be specified as an int or float. If
            ``None``, the method will not have timeout specified by default.
        default_compression (Optional[grpc.Compression]): The default
            grpc.Compression. If ``None``, the method will not have
            compression specified by default.
        client_info
            (Optional[google.api_core.gapic_v1.client_info.ClientInfo]):
                Client information used to create a user-agent string that's
                passed as gRPC metadata to the method. If unspecified, then
                a sane default will be used. If ``None``, then no user agent
                metadata will be provided to the RPC method.
        with_call (bool): If True, wrapped grpc.UnaryUnaryMulticallables will
            return a tuple of (response, grpc.Call) instead of just the response.
            This is useful for extracting trailing metadata from unary calls.
            Defaults to False.

    Returns:
        Callable: A new callable that takes optional ``retry``, ``timeout``,
            and ``compression``
            arguments and applies the common error mapping, retry, timeout, compression,
            and metadata behavior to the low-level RPC method.
    """
    if with_call:
        try:
            func = func.with_call
        except AttributeError as exc:
            raise ValueError(
                "with_call=True is only supported for unary calls."
            ) from exc
    func = grpc_helpers.wrap_errors(func)
    if client_info is not None:
        user_agent_metadata = [client_info.to_grpc_metadata()]
    else:
        user_agent_metadata = None

    return functools.wraps(func)(
        _GapicCallable(
            func,
            default_retry,
            default_timeout,
            default_compression,
            metadata=user_agent_metadata,
        )
    )

# === NexusCore/openenv\Lib\site-packages\litellm\batch_completion\main.py ===
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import List, Optional

import litellm
from litellm._logging import print_verbose
from litellm.utils import get_optional_params

from ..llms.vllm.completion import handler as vllm_handler


def batch_completion(
    model: str,
    # Optional OpenAI params: see https://platform.openai.com/docs/api-reference/chat/create
    messages: List = [],
    functions: Optional[List] = None,
    function_call: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    n: Optional[int] = None,
    stream: Optional[bool] = None,
    stop=None,
    max_tokens: Optional[int] = None,
    presence_penalty: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    logit_bias: Optional[dict] = None,
    user: Optional[str] = None,
    deployment_id=None,
    request_timeout: Optional[int] = None,
    timeout: Optional[int] = 600,
    max_workers: Optional[int] = 100,
    # Optional liteLLM function params
    **kwargs,
):
    """
    Batch litellm.completion function for a given model.

    Args:
        model (str): The model to use for generating completions.
        messages (List, optional): List of messages to use as input for generating completions. Defaults to [].
        functions (List, optional): List of functions to use as input for generating completions. Defaults to [].
        function_call (str, optional): The function call to use as input for generating completions. Defaults to "".
        temperature (float, optional): The temperature parameter for generating completions. Defaults to None.
        top_p (float, optional): The top-p parameter for generating completions. Defaults to None.
        n (int, optional): The number of completions to generate. Defaults to None.
        stream (bool, optional): Whether to stream completions or not. Defaults to None.
        stop (optional): The stop parameter for generating completions. Defaults to None.
        max_tokens (float, optional): The maximum number of tokens to generate. Defaults to None.
        presence_penalty (float, optional): The presence penalty for generating completions. Defaults to None.
        frequency_penalty (float, optional): The frequency penalty for generating completions. Defaults to None.
        logit_bias (dict, optional): The logit bias for generating completions. Defaults to {}.
        user (str, optional): The user string for generating completions. Defaults to "".
        deployment_id (optional): The deployment ID for generating completions. Defaults to None.
        request_timeout (int, optional): The request timeout for generating completions. Defaults to None.
        max_workers (int,optional): The maximum number of threads to use for parallel processing.

    Returns:
        list: A list of completion results.
    """
    args = locals()

    batch_messages = messages
    completions = []
    model = model
    custom_llm_provider = None
    if model.split("/", 1)[0] in litellm.provider_list:
        custom_llm_provider = model.split("/", 1)[0]
        model = model.split("/", 1)[1]
    if custom_llm_provider == "vllm":
        optional_params = get_optional_params(
            functions=functions,
            function_call=function_call,
            temperature=temperature,
            top_p=top_p,
            n=n,
            stream=stream or False,
            stop=stop,
            max_tokens=max_tokens,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            logit_bias=logit_bias,
            user=user,
            # params to identify the model
            model=model,
            custom_llm_provider=custom_llm_provider,
        )
        results = vllm_handler.batch_completions(
            model=model,
            messages=batch_messages,
            custom_prompt_dict=litellm.custom_prompt_dict,
            optional_params=optional_params,
        )
    # all non VLLM models for batch completion models
    else:

        def chunks(lst, n):
            """Yield successive n-sized chunks from lst."""
            for i in range(0, len(lst), n):
                yield lst[i : i + n]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for sub_batch in chunks(batch_messages, 100):
                for message_list in sub_batch:
                    kwargs_modified = args.copy()
                    kwargs_modified.pop("max_workers")
                    kwargs_modified["messages"] = message_list
                    original_kwargs = {}
                    if "kwargs" in kwargs_modified:
                        original_kwargs = kwargs_modified.pop("kwargs")
                    future = executor.submit(
                        litellm.completion, **kwargs_modified, **original_kwargs
                    )
                    completions.append(future)

        # Retrieve the results from the futures
        # results = [future.result() for future in completions]
        # return exceptions if any
        results = []
        for future in completions:
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(exc)

    return results


# send one request to multiple models
# return as soon as one of the llms responds
def batch_completion_models(*args, **kwargs):
    """
    Send a request to multiple language models concurrently and return the response
    as soon as one of the models responds.

    Args:
        *args: Variable-length positional arguments passed to the completion function.
        **kwargs: Additional keyword arguments:
            - models (str or list of str): The language models to send requests to.
            - Other keyword arguments to be passed to the completion function.

    Returns:
        str or None: The response from one of the language models, or None if no response is received.

    Note:
        This function utilizes a ThreadPoolExecutor to parallelize requests to multiple models.
        It sends requests concurrently and returns the response from the first model that responds.
    """

    if "model" in kwargs:
        kwargs.pop("model")
    if "models" in kwargs:
        models = kwargs["models"]
        kwargs.pop("models")
        futures = {}
        with ThreadPoolExecutor(max_workers=len(models)) as executor:
            for model in models:
                futures[model] = executor.submit(
                    litellm.completion, *args, model=model, **kwargs
                )

            for model, future in sorted(
                futures.items(), key=lambda x: models.index(x[0])
            ):
                if future.result() is not None:
                    return future.result()
    elif "deployments" in kwargs:
        deployments = kwargs["deployments"]
        kwargs.pop("deployments")
        kwargs.pop("model_list")
        nested_kwargs = kwargs.pop("kwargs", {})
        futures = {}
        with ThreadPoolExecutor(max_workers=len(deployments)) as executor:
            for deployment in deployments:
                for key in kwargs.keys():
                    if (
                        key not in deployment
                    ):  # don't override deployment values e.g. model name, api base, etc.
                        deployment[key] = kwargs[key]
                kwargs = {**deployment, **nested_kwargs}
                futures[deployment["model"]] = executor.submit(
                    litellm.completion, **kwargs
                )

            while futures:
                # wait for the first returned future
                print_verbose("\n\n waiting for next result\n\n")
                done, _ = wait(futures.values(), return_when=FIRST_COMPLETED)
                print_verbose(f"done list\n{done}")
                for future in done:
                    try:
                        result = future.result()
                        return result
                    except Exception:
                        # if model 1 fails, continue with response from model 2, model3
                        print_verbose(
                            "\n\ngot an exception, ignoring, removing from futures"
                        )
                        print_verbose(futures)
                        new_futures = {}
                        for key, value in futures.items():
                            if future == value:
                                print_verbose(f"removing key{key}")
                                continue
                            else:
                                new_futures[key] = value
                        futures = new_futures
                        print_verbose(f"new futures{futures}")
                        continue

                print_verbose("\n\ndone looping through futures\n\n")
                print_verbose(futures)

    return None  # If no response is received from any model


def batch_completion_models_all_responses(*args, **kwargs):
    """
    Send a request to multiple language models concurrently and return a list of responses
    from all models that respond.

    Args:
        *args: Variable-length positional arguments passed to the completion function.
        **kwargs: Additional keyword arguments:
            - models (str or list of str): The language models to send requests to.
            - Other keyword arguments to be passed to the completion function.

    Returns:
        list: A list of responses from the language models that responded.

    Note:
        This function utilizes a ThreadPoolExecutor to parallelize requests to multiple models.
        It sends requests concurrently and collects responses from all models that respond.
    """
    import concurrent.futures

    # ANSI escape codes for colored output

    if "model" in kwargs:
        kwargs.pop("model")
    if "models" in kwargs:
        models = kwargs["models"]
        kwargs.pop("models")
    else:
        raise Exception("'models' param not in kwargs")

    responses = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
        for idx, model in enumerate(models):
            future = executor.submit(litellm.completion, *args, model=model, **kwargs)
            if future.result() is not None:
                responses.append(future.result())

    return responses

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\image_generation\image_generation_handler.py ===
import json
from typing import Any, Dict, List, Optional

import httpx
from openai.types.image import Image

import litellm
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from litellm.types.llms.vertex_ai import VERTEX_CREDENTIALS_TYPES
from litellm.types.utils import ImageResponse


class VertexImageGeneration(VertexLLM):
    def process_image_generation_response(
        self,
        json_response: Dict[str, Any],
        model_response: ImageResponse,
        model: Optional[str] = None,
    ) -> ImageResponse:
        if "predictions" not in json_response:
            raise litellm.InternalServerError(
                message=f"image generation response does not contain 'predictions', got {json_response}",
                llm_provider="vertex_ai",
                model=model,
            )

        predictions = json_response["predictions"]
        response_data: List[Image] = []

        for prediction in predictions:
            bytes_base64_encoded = prediction["bytesBase64Encoded"]
            image_object = Image(b64_json=bytes_base64_encoded)
            response_data.append(image_object)

        model_response.data = response_data
        return model_response

    def image_generation(
        self,
        prompt: str,
        api_base: Optional[str],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        model_response: ImageResponse,
        logging_obj: Any,
        model: str = "imagegeneration",  # vertex ai uses imagegeneration as the default model
        client: Optional[Any] = None,
        optional_params: Optional[dict] = None,
        timeout: Optional[int] = None,
        aimg_generation=False,
        extra_headers: Optional[dict] = None,
    ) -> ImageResponse:
        if aimg_generation is True:
            return self.aimage_generation(  # type: ignore
                prompt=prompt,
                api_base=api_base,
                vertex_project=vertex_project,
                vertex_location=vertex_location,
                vertex_credentials=vertex_credentials,
                model=model,
                client=client,
                optional_params=optional_params,
                timeout=timeout,
                logging_obj=logging_obj,
                model_response=model_response,
            )

        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            sync_handler: HTTPHandler = HTTPHandler(**_params)  # type: ignore
        else:
            sync_handler = client  # type: ignore

        # url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:predict"

        auth_header: Optional[str] = None
        auth_header, _ = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai",
        )
        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=None,
            auth_header=auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=False,
            custom_llm_provider="vertex_ai",
            api_base=api_base,
            should_use_v1beta1_features=False,
            mode="image_generation",
        )
        optional_params = optional_params or {
            "sampleCount": 1
        }  # default optional params

        request_data = {
            "instances": [{"prompt": prompt}],
            "parameters": optional_params,
        }

        headers = self.set_headers(auth_header=auth_header, extra_headers=extra_headers)

        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": optional_params,
                "api_base": api_base,
                "headers": headers,
            },
        )

        response = sync_handler.post(
            url=api_base,
            headers=headers,
            data=json.dumps(request_data),
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        json_response = response.json()
        return self.process_image_generation_response(
            json_response, model_response, model
        )

    async def aimage_generation(
        self,
        prompt: str,
        api_base: Optional[str],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        model_response: litellm.ImageResponse,
        logging_obj: Any,
        model: str = "imagegeneration",  # vertex ai uses imagegeneration as the default model
        client: Optional[AsyncHTTPHandler] = None,
        optional_params: Optional[dict] = None,
        timeout: Optional[int] = None,
        extra_headers: Optional[dict] = None,
    ):
        response = None
        if client is None:
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    _httpx_timeout = httpx.Timeout(timeout)
                    _params["timeout"] = _httpx_timeout
            else:
                _params["timeout"] = httpx.Timeout(timeout=600.0, connect=5.0)

            self.async_handler = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.VERTEX_AI,
                params={"timeout": timeout},
            )
        else:
            self.async_handler = client  # type: ignore

        # make POST request to
        # https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/imagegeneration:predict

        """
        Docs link: https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/imagegeneration?project=adroit-crow-413218
        curl -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d {
            "instances": [
                {
                    "prompt": "a cat"
                }
            ],
            "parameters": {
                "sampleCount": 1
            }
        } \
        "https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/imagegeneration:predict"
        """
        auth_header: Optional[str] = None
        auth_header, _ = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai",
        )
        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=None,
            auth_header=auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=False,
            custom_llm_provider="vertex_ai",
            api_base=api_base,
            should_use_v1beta1_features=False,
            mode="image_generation",
        )
        optional_params = optional_params or {
            "sampleCount": 1
        }  # default optional params

        request_data = {
            "instances": [{"prompt": prompt}],
            "parameters": optional_params,
        }

        headers = self.set_headers(auth_header=auth_header, extra_headers=extra_headers)

        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": optional_params,
                "api_base": api_base,
                "headers": headers,
            },
        )

        response = await self.async_handler.post(
            url=api_base,
            headers=headers,
            data=json.dumps(request_data),
        )

        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} {response.text}")

        json_response = response.json()
        return self.process_image_generation_response(
            json_response, model_response, model
        )

    def is_image_generation_response(self, json_response: Dict[str, Any]) -> bool:
        if "predictions" in json_response:
            if "bytesBase64Encoded" in json_response["predictions"][0]:
                return True
        return False

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\client\keys.py ===
import requests
from typing import Dict, Any, Optional, Union, List
from .exceptions import UnauthorizedError


class KeysManagementClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """
        Initialize the KeysManagementClient.

        Args:
            base_url (str): The base URL of the LiteLLM proxy server (e.g., "http://localhost:8000")
            api_key (Optional[str]): API key for authentication. If provided, it will be sent as a Bearer token.
        """
        self._base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self._api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers for API requests, including authorization if api_key is set.

        Returns:
            Dict[str, str]: Headers to use for API requests
        """
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def list(
        self,
        page: Optional[int] = None,
        size: Optional[int] = None,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        key_hash: Optional[str] = None,
        key_alias: Optional[str] = None,
        return_full_object: Optional[bool] = None,
        include_team_keys: Optional[bool] = None,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        List all API keys with optional filtering and pagination.

        Args:
            page (Optional[int]): Page number for pagination
            size (Optional[int]): Number of items per page
            user_id (Optional[str]): Filter keys by user ID
            team_id (Optional[str]): Filter keys by team ID
            organization_id (Optional[str]): Filter keys by organization ID
            key_hash (Optional[str]): Filter by specific key hash
            key_alias (Optional[str]): Filter by key alias
            return_full_object (Optional[bool]): Whether to return the full key object
            include_team_keys (Optional[bool]): Whether to include team keys in the response
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True. The response contains a list
            of API keys with their configurations.

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/key/list"
        params: Dict[str, Any] = {}

        # Add optional query parameters
        if page is not None:
            params["page"] = page
        if size is not None:
            params["size"] = size
        if user_id is not None:
            params["user_id"] = user_id
        if team_id is not None:
            params["team_id"] = team_id
        if organization_id is not None:
            params["organization_id"] = organization_id
        if key_hash is not None:
            params["key_hash"] = key_hash
        if key_alias is not None:
            params["key_alias"] = key_alias
        if return_full_object is not None:
            params["return_full_object"] = str(return_full_object).lower()
        if include_team_keys is not None:
            params["include_team_keys"] = str(include_team_keys).lower()

        request = requests.Request("GET", url, headers=self._get_headers(), params=params)

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def generate(
        self,
        models: Optional[List[str]] = None,
        aliases: Optional[Dict[str, str]] = None,
        spend: Optional[float] = None,
        duration: Optional[str] = None,
        key_alias: Optional[str] = None,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        budget_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Generate an API key based on the provided data.

        Docs: https://docs.litellm.ai/docs/proxy/virtual_keys

        Args:
            models (Optional[List[str]]): List of allowed models for this key
            aliases (Optional[Dict[str, str]]): Model alias mappings
            spend (Optional[float]): Maximum spend limit for this key
            duration (Optional[str]): Duration for which the key is valid (e.g. "24h", "7d")
            key_alias (Optional[str]): Alias/name for the key for easier identification
            team_id (Optional[str]): Team ID to associate the key with
            user_id (Optional[str]): User ID to associate the key with
            budget_id (Optional[str]): Budget ID to associate the key with
            config (Optional[Dict[str, Any]]): Additional configuration parameters
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/key/generate"

        data: Dict[str, Any] = {}
        if models is not None:
            data["models"] = models
        if aliases is not None:
            data["aliases"] = aliases
        if spend is not None:
            data["spend"] = spend
        if duration is not None:
            data["duration"] = duration
        if key_alias is not None:
            data["key_alias"] = key_alias
        if team_id is not None:
            data["team_id"] = team_id
        if user_id is not None:
            data["user_id"] = user_id
        if budget_id is not None:
            data["budget_id"] = budget_id
        if config is not None:
            data["config"] = config

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def delete(
        self,
        keys: Optional[List[str]] = None,
        key_aliases: Optional[List[str]] = None,
        return_request: bool = False,
    ) -> Union[Dict[str, Any], requests.Request]:
        """
        Delete existing keys

        Args:
            keys (List[str]): List of API keys to delete
            key_aliases (List[str]): List of key aliases to delete
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or
            a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/key/delete"

        data = {
            "keys": keys,
            "key_aliases": key_aliases,
        }

        request = requests.Request("POST", url, headers=self._get_headers(), json=data)

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

    def info(self, key: str, return_request: bool = False) -> Union[Dict[str, Any], requests.Request]:
        """
        Get information about API keys.

        Args:
            key (str): The key hash to get information about
            return_request (bool): If True, returns the prepared request object instead of executing it

        Returns:
            Union[Dict[str, Any], requests.Request]: Either the response from the server or a prepared request object if return_request is True

        Raises:
            UnauthorizedError: If the request fails with a 401 status code
            requests.exceptions.RequestException: If the request fails with any other error
        """
        url = f"{self._base_url}/keys/info?key={key}"
        request = requests.Request("GET", url, headers=self._get_headers())

        if return_request:
            return request

        session = requests.Session()
        try:
            response = session.send(request.prepare())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise UnauthorizedError(e)
            raise

# === NexusCore/openenv\Lib\site-packages\pyreadline3\console\ansi.py ===
# -*- coding: ISO-8859-1 -*-


import os
import re
import sys

terminal_escape = re.compile("(\001?\033\\[[0-9;]*m\002?)")
escape_parts = re.compile("\001?\033\\[([0-9;]*)m\002?")


class AnsiState(object):
    def __init__(
        self,
        bold=False,
        inverse=False,
        color="white",
        background="black",
        backgroundbold=False,
    ):
        self.bold = bold
        self.inverse = inverse
        self.color = color
        self.background = background
        self.backgroundbold = backgroundbold

    trtable = {
        "black": 0,
        "red": 4,
        "green": 2,
        "yellow": 6,
        "blue": 1,
        "magenta": 5,
        "cyan": 3,
        "white": 7,
    }
    revtable = dict(zip(trtable.values(), trtable.keys()))

    def get_winattr(self):
        attr = 0
        if self.bold:
            attr |= 0x0008
        if self.backgroundbold:
            attr |= 0x0080
        if self.inverse:
            attr |= 0x4000
        attr |= self.trtable[self.color]
        attr |= self.trtable[self.background] << 4
        return attr

    def set_winattr(self, attr):
        self.bold = bool(attr & 0x0008)
        self.backgroundbold = bool(attr & 0x0080)
        self.inverse = bool(attr & 0x4000)
        self.color = self.revtable[attr & 0x0007]
        self.background = self.revtable[(attr & 0x0070) >> 4]

    winattr = property(get_winattr, set_winattr)

    def __repr__(self):
        return (
            "AnsiState(bold=%s,inverse=%s,color=%9s,"
            "background=%9s,backgroundbold=%s)# 0x%x"
            % (
                self.bold,
                self.inverse,
                '"%s"' % self.color,
                '"%s"' % self.background,
                self.backgroundbold,
                self.winattr,
            )
        )

    def copy(self):
        x = AnsiState()
        x.bold = self.bold
        x.inverse = self.inverse
        x.color = self.color
        x.background = self.background
        x.backgroundbold = self.backgroundbold
        return x


defaultstate = AnsiState(False, False, "white")

trtable = {
    0: "black",
    1: "red",
    2: "green",
    3: "yellow",
    4: "blue",
    5: "magenta",
    6: "cyan",
    7: "white",
}


class AnsiWriter(object):
    def __init__(self, default=defaultstate):
        if isinstance(defaultstate, AnsiState):
            self.defaultstate = default
        else:
            self.defaultstate = AnsiState()
            self.defaultstate.winattr = defaultstate

    def write_color(self, text, attr=None):
        """write text at current cursor position and interpret color escapes.

        return the number of characters written.
        """
        if isinstance(attr, AnsiState):
            defaultstate = attr
        elif attr is None:  # use attribute form initial console
            attr = self.defaultstate.copy()
        else:
            defaultstate = AnsiState()
            defaultstate.winattr = attr
            attr = defaultstate
        chunks = terminal_escape.split(text)
        n = 0  # count the characters we actually write, omitting the escapes
        res = []
        for chunk in chunks:
            m = escape_parts.match(chunk)
            if m:
                parts = m.group(1).split(";")
                if len(parts) == 1 and parts[0] == "0":
                    attr = self.defaultstate.copy()
                    continue
                for part in parts:
                    if part == "0":  # No text attribute
                        attr = self.defaultstate.copy()
                        attr.bold = False
                    elif part == "7":  # switch on reverse
                        attr.inverse = True
                    # switch on bold (i.e. intensify foreground color)
                    elif part == "1":
                        attr.bold = True
                    elif len(part) == 2:
                        if part == "22":  # Normal foreground color
                            attr.bold = False
                        elif "30" <= part <= "37":  # set foreground color
                            attr.color = trtable[int(part) - 30]
                        elif part == "39":  # Default foreground color
                            attr.color = self.defaultstate.color
                        elif "40" <= part <= "47":  # set background color
                            attr.background = trtable[int(part) - 40]
                        elif part == "49":  # Default background color
                            attr.background = self.defaultstate.background
                continue
            n += len(chunk)

            res.append((attr.copy(), chunk))

        return n, res

    def parse_color(self, text, attr=None):
        n, res = self.write_color(text, attr)
        return n, [attr.winattr for attr, text in res]


def write_color(text, attr=None):
    a = AnsiWriter(defaultstate)
    return a.write_color(text, attr)


def write_color_old(text, attr=None):
    """write text at current cursor position and interpret color escapes.

    return the number of characters written.
    """
    res = []
    chunks = terminal_escape.split(text)
    n = 0  # count the characters we actually write, omitting the escapes
    if attr is None:  # use attribute from initial console
        attr = 15
    for chunk in chunks:
        m = escape_parts.match(chunk)
        if m:
            for part in m.group(1).split(";"):
                if part == "0":  # No text attribute
                    attr = 0
                elif part == "7":  # switch on reverse
                    attr |= 0x4000
                # switch on bold (i.e. intensify foreground color)
                if part == "1":
                    attr |= 0x08
                elif len(part) == 2 and "30" <= part <= "37":  # set foreground color
                    part = int(part) - 30
                    # we have to mirror bits
                    attr = (
                        (attr & ~0x07)
                        | ((part & 0x1) << 2)
                        | (part & 0x2)
                        | ((part & 0x4) >> 2)
                    )
                elif len(part) == 2 and "40" <= part <= "47":  # set background color
                    part = int(part) - 40
                    # we have to mirror bits
                    attr = (
                        (attr & ~0x70)
                        | ((part & 0x1) << 6)
                        | ((part & 0x2) << 4)
                        | ((part & 0x4) << 2)
                    )
                # ignore blink, underline and anything we don't understand
            continue
        n += len(chunk)
        if chunk:
            res.append(("0x%x" % attr, chunk))
    return res


# trtable={0:"black",1:"red",2:"green",3:"yellow",4:"blue",5:"magenta",6:"cyan",7:"white"}

if __name__ == "__main__x":
    import pprint

    pprint = pprint.pprint

    s = "\033[0;31mred\033[0;32mgreen\033[0;33myellow\033[0;34mblue\033[0;35mmagenta\033[0;36mcyan\033[0;37mwhite\033[0m"
    pprint(write_color(s))
    pprint(write_color_old(s))
    s = "\033[1;31mred\033[1;32mgreen\033[1;33myellow\033[1;34mblue\033[1;35mmagenta\033[1;36mcyan\033[1;37mwhite\033[0m"
    pprint(write_color(s))
    pprint(write_color_old(s))

    s = "\033[0;7;31mred\033[0;7;32mgreen\033[0;7;33myellow\033[0;7;34mblue\033[0;7;35mmagenta\033[0;7;36mcyan\033[0;7;37mwhite\033[0m"
    pprint(write_color(s))
    pprint(write_color_old(s))
    s = "\033[1;7;31mred\033[1;7;32mgreen\033[1;7;33myellow\033[1;7;34mblue\033[1;7;35mmagenta\033[1;7;36mcyan\033[1;7;37mwhite\033[0m"
    pprint(write_color(s))
    pprint(write_color_old(s))


if __name__ == "__main__":
    import pprint

    import console

    pprint = pprint.pprint

    c = console.Console()
    c.write_color("dhsjdhs")
    c.write_color("\033[0;32mIn [\033[1;32m1\033[0;32m]:")
    print
    pprint(write_color("\033[0;32mIn [\033[1;32m1\033[0;32m]:"))

if __name__ == "__main__x":
    import pprint

    pprint = pprint.pprint
    s = "\033[0;31mred\033[0;32mgreen\033[0;33myellow\033[0;34mblue\033[0;35mmagenta\033[0;36mcyan\033[0;37mwhite\033[0m"
    pprint(write_color(s))

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\markers.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

import operator
import os
import platform
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ._parser import (
    MarkerAtom,
    MarkerList,
    Op,
    Value,
    Variable,
)
from ._parser import (
    parse_marker as _parse_marker,
)
from ._tokenizer import ParserSyntaxError
from .specifiers import InvalidSpecifier, Specifier
from .utils import canonicalize_name

__all__ = [
    "InvalidMarker",
    "UndefinedComparison",
    "UndefinedEnvironmentName",
    "Marker",
    "default_environment",
]

Operator = Callable[[str, str], bool]


class InvalidMarker(ValueError):
    """
    An invalid marker was found, users should refer to PEP 508.
    """


class UndefinedComparison(ValueError):
    """
    An invalid operation was attempted on a value that doesn't support it.
    """


class UndefinedEnvironmentName(ValueError):
    """
    A name was attempted to be used that does not exist inside of the
    environment.
    """


def _normalize_extra_values(results: Any) -> Any:
    """
    Normalize extra values.
    """
    if isinstance(results[0], tuple):
        lhs, op, rhs = results[0]
        if isinstance(lhs, Variable) and lhs.value == "extra":
            normalized_extra = canonicalize_name(rhs.value)
            rhs = Value(normalized_extra)
        elif isinstance(rhs, Variable) and rhs.value == "extra":
            normalized_extra = canonicalize_name(lhs.value)
            lhs = Value(normalized_extra)
        results[0] = lhs, op, rhs
    return results


def _format_marker(
    marker: Union[List[str], MarkerAtom, str], first: Optional[bool] = True
) -> str:
    assert isinstance(marker, (list, tuple, str))

    # Sometimes we have a structure like [[...]] which is a single item list
    # where the single item is itself it's own list. In that case we want skip
    # the rest of this function so that we don't get extraneous () on the
    # outside.
    if (
        isinstance(marker, list)
        and len(marker) == 1
        and isinstance(marker[0], (list, tuple))
    ):
        return _format_marker(marker[0])

    if isinstance(marker, list):
        inner = (_format_marker(m, first=False) for m in marker)
        if first:
            return " ".join(inner)
        else:
            return "(" + " ".join(inner) + ")"
    elif isinstance(marker, tuple):
        return " ".join([m.serialize() for m in marker])
    else:
        return marker


_operators: Dict[str, Operator] = {
    "in": lambda lhs, rhs: lhs in rhs,
    "not in": lambda lhs, rhs: lhs not in rhs,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    ">=": operator.ge,
    ">": operator.gt,
}


def _eval_op(lhs: str, op: Op, rhs: str) -> bool:
    try:
        spec = Specifier("".join([op.serialize(), rhs]))
    except InvalidSpecifier:
        pass
    else:
        return spec.contains(lhs, prereleases=True)

    oper: Optional[Operator] = _operators.get(op.serialize())
    if oper is None:
        raise UndefinedComparison(f"Undefined {op!r} on {lhs!r} and {rhs!r}.")

    return oper(lhs, rhs)


def _normalize(*values: str, key: str) -> Tuple[str, ...]:
    # PEP 685 – Comparison of extra names for optional distribution dependencies
    # https://peps.python.org/pep-0685/
    # > When comparing extra names, tools MUST normalize the names being
    # > compared using the semantics outlined in PEP 503 for names
    if key == "extra":
        return tuple(canonicalize_name(v) for v in values)

    # other environment markers don't have such standards
    return values


def _evaluate_markers(markers: MarkerList, environment: Dict[str, str]) -> bool:
    groups: List[List[bool]] = [[]]

    for marker in markers:
        assert isinstance(marker, (list, tuple, str))

        if isinstance(marker, list):
            groups[-1].append(_evaluate_markers(marker, environment))
        elif isinstance(marker, tuple):
            lhs, op, rhs = marker

            if isinstance(lhs, Variable):
                environment_key = lhs.value
                lhs_value = environment[environment_key]
                rhs_value = rhs.value
            else:
                lhs_value = lhs.value
                environment_key = rhs.value
                rhs_value = environment[environment_key]

            lhs_value, rhs_value = _normalize(lhs_value, rhs_value, key=environment_key)
            groups[-1].append(_eval_op(lhs_value, op, rhs_value))
        else:
            assert marker in ["and", "or"]
            if marker == "or":
                groups.append([])

    return any(all(item) for item in groups)


def format_full_version(info: "sys._version_info") -> str:
    version = "{0.major}.{0.minor}.{0.micro}".format(info)
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> Dict[str, str]:
    iver = format_full_version(sys.implementation.version)
    implementation_name = sys.implementation.name
    return {
        "implementation_name": implementation_name,
        "implementation_version": iver,
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "platform_python_implementation": platform.python_implementation(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


class Marker:
    def __init__(self, marker: str) -> None:
        # Note: We create a Marker object without calling this constructor in
        #       packaging.requirements.Requirement. If any additional logic is
        #       added here, make sure to mirror/adapt Requirement.
        try:
            self._markers = _normalize_extra_values(_parse_marker(marker))
            # The attribute `_markers` can be described in terms of a recursive type:
            # MarkerList = List[Union[Tuple[Node, ...], str, MarkerList]]
            #
            # For example, the following expression:
            # python_version > "3.6" or (python_version == "3.6" and os_name == "unix")
            #
            # is parsed into:
            # [
            #     (<Variable('python_version')>, <Op('>')>, <Value('3.6')>),
            #     'and',
            #     [
            #         (<Variable('python_version')>, <Op('==')>, <Value('3.6')>),
            #         'or',
            #         (<Variable('os_name')>, <Op('==')>, <Value('unix')>)
            #     ]
            # ]
        except ParserSyntaxError as e:
            raise InvalidMarker(str(e)) from e

    def __str__(self) -> str:
        return _format_marker(self._markers)

    def __repr__(self) -> str:
        return f"<Marker('{self}')>"

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, str(self)))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Marker):
            return NotImplemented

        return str(self) == str(other)

    def evaluate(self, environment: Optional[Dict[str, str]] = None) -> bool:
        """Evaluate a marker.

        Return the boolean from evaluating the given marker against the
        environment. environment is an optional argument to override all or
        part of the determined environment.

        The environment is determined from the current Python process.
        """
        current_environment = default_environment()
        current_environment["extra"] = ""
        if environment is not None:
            current_environment.update(environment)
            # The API used to allow setting extra to None. We need to handle this
            # case for backwards compatibility.
            if current_environment["extra"] is None:
                current_environment["extra"] = ""

        return _evaluate_markers(self._markers, current_environment)