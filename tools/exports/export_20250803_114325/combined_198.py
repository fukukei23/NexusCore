
# === NexusCore/openenv\Lib\site-packages\pygments\formatters\terminal256.py ===
"""
    pygments.formatters.terminal256
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for 256-color terminal output with ANSI sequences.

    RGB-to-XTERM color conversion routines adapted from xterm256-conv
    tool (http://frexx.de/xterm-256-notes/data/xterm256-conv2.tar.bz2)
    by Wolfgang Frisch.

    Formatter version 1.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# TODO:
#  - Options to map style's bold/underline/italic/border attributes
#    to some ANSI attrbutes (something like 'italic=underline')
#  - An option to output "style RGB to xterm RGB/index" conversion table
#  - An option to indicate that we are running in "reverse background"
#    xterm. This means that default colors are white-on-black, not
#    black-on-while, so colors like "white background" need to be converted
#    to "white background, black foreground", etc...

from pygments.formatter import Formatter
from pygments.console import codes
from pygments.style import ansicolors


__all__ = ['Terminal256Formatter', 'TerminalTrueColorFormatter']


class EscapeSequence:
    def __init__(self, fg=None, bg=None, bold=False, underline=False, italic=False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.underline = underline
        self.italic = italic

    def escape(self, attrs):
        if len(attrs):
            return "\x1b[" + ";".join(attrs) + "m"
        return ""

    def color_string(self):
        attrs = []
        if self.fg is not None:
            if self.fg in ansicolors:
                esc = codes[self.fg.replace('ansi','')]
                if ';01m' in esc:
                    self.bold = True
                # extract fg color code.
                attrs.append(esc[2:4])
            else:
                attrs.extend(("38", "5", "%i" % self.fg))
        if self.bg is not None:
            if self.bg in ansicolors:
                esc = codes[self.bg.replace('ansi','')]
                # extract fg color code, add 10 for bg.
                attrs.append(str(int(esc[2:4])+10))
            else:
                attrs.extend(("48", "5", "%i" % self.bg))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def true_color_string(self):
        attrs = []
        if self.fg:
            attrs.extend(("38", "2", str(self.fg[0]), str(self.fg[1]), str(self.fg[2])))
        if self.bg:
            attrs.extend(("48", "2", str(self.bg[0]), str(self.bg[1]), str(self.bg[2])))
        if self.bold:
            attrs.append("01")
        if self.underline:
            attrs.append("04")
        if self.italic:
            attrs.append("03")
        return self.escape(attrs)

    def reset_string(self):
        attrs = []
        if self.fg is not None:
            attrs.append("39")
        if self.bg is not None:
            attrs.append("49")
        if self.bold or self.underline or self.italic:
            attrs.append("00")
        return self.escape(attrs)


class Terminal256Formatter(Formatter):
    """
    Format tokens with ANSI color sequences, for output in a 256-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    The formatter takes colors from a style defined by the `style` option
    and converts them to nearest ANSI 256-color escape sequences. Bold and
    underline attributes from the style are preserved (and displayed).

    .. versionadded:: 0.9

    .. versionchanged:: 2.2
       If the used style defines foreground colors in the form ``#ansi*``, then
       `Terminal256Formatter` will map these to non extended foreground color.
       See :ref:`AnsiTerminalStyle` for more information.

    .. versionchanged:: 2.4
       The ANSI color names have been updated with names that are easier to
       understand and align with colornames of other projects and terminals.
       See :ref:`this table <new-ansi-color-names>` for more information.


    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `linenos`
        Set to ``True`` to have line numbers on the terminal output as well
        (default: ``False`` = no line numbers).
    """
    name = 'Terminal256'
    aliases = ['terminal256', 'console256', '256']
    filenames = []

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        self.xterm_colors = []
        self.best_match = {}
        self.style_string = {}

        self.usebold = 'nobold' not in options
        self.useunderline = 'nounderline' not in options
        self.useitalic = 'noitalic' not in options

        self._build_color_table()  # build an RGB-to-256 color conversion table
        self._setup_styles()  # convert selected style's colors to term. colors

        self.linenos = options.get('linenos', False)
        self._lineno = 0

    def _build_color_table(self):
        # colors 0..15: 16 basic colors

        self.xterm_colors.append((0x00, 0x00, 0x00))  # 0
        self.xterm_colors.append((0xcd, 0x00, 0x00))  # 1
        self.xterm_colors.append((0x00, 0xcd, 0x00))  # 2
        self.xterm_colors.append((0xcd, 0xcd, 0x00))  # 3
        self.xterm_colors.append((0x00, 0x00, 0xee))  # 4
        self.xterm_colors.append((0xcd, 0x00, 0xcd))  # 5
        self.xterm_colors.append((0x00, 0xcd, 0xcd))  # 6
        self.xterm_colors.append((0xe5, 0xe5, 0xe5))  # 7
        self.xterm_colors.append((0x7f, 0x7f, 0x7f))  # 8
        self.xterm_colors.append((0xff, 0x00, 0x00))  # 9
        self.xterm_colors.append((0x00, 0xff, 0x00))  # 10
        self.xterm_colors.append((0xff, 0xff, 0x00))  # 11
        self.xterm_colors.append((0x5c, 0x5c, 0xff))  # 12
        self.xterm_colors.append((0xff, 0x00, 0xff))  # 13
        self.xterm_colors.append((0x00, 0xff, 0xff))  # 14
        self.xterm_colors.append((0xff, 0xff, 0xff))  # 15

        # colors 16..232: the 6x6x6 color cube

        valuerange = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)

        for i in range(217):
            r = valuerange[(i // 36) % 6]
            g = valuerange[(i // 6) % 6]
            b = valuerange[i % 6]
            self.xterm_colors.append((r, g, b))

        # colors 233..253: grayscale

        for i in range(1, 22):
            v = 8 + i * 10
            self.xterm_colors.append((v, v, v))

    def _closest_color(self, r, g, b):
        distance = 257*257*3  # "infinity" (>distance from #000000 to #ffffff)
        match = 0

        for i in range(0, 254):
            values = self.xterm_colors[i]

            rd = r - values[0]
            gd = g - values[1]
            bd = b - values[2]
            d = rd*rd + gd*gd + bd*bd

            if d < distance:
                match = i
                distance = d
        return match

    def _color_index(self, color):
        index = self.best_match.get(color, None)
        if color in ansicolors:
            # strip the `ansi/#ansi` part and look up code
            index = color
            self.best_match[color] = index
        if index is None:
            try:
                rgb = int(str(color), 16)
            except ValueError:
                rgb = 0

            r = (rgb >> 16) & 0xff
            g = (rgb >> 8) & 0xff
            b = rgb & 0xff
            index = self._closest_color(r, g, b)
            self.best_match[color] = index
        return index

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            # get foreground from ansicolor if set
            if ndef['ansicolor']:
                escape.fg = self._color_index(ndef['ansicolor'])
            elif ndef['color']:
                escape.fg = self._color_index(ndef['color'])
            if ndef['bgansicolor']:
                escape.bg = self._color_index(ndef['bgansicolor'])
            elif ndef['bgcolor']:
                escape.bg = self._color_index(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.color_string(),
                                             escape.reset_string())

    def _write_lineno(self, outfile):
        self._lineno += 1
        outfile.write("%s%04d: " % (self._lineno != 1 and '\n' or '', self._lineno))

    def format(self, tokensource, outfile):
        return Formatter.format(self, tokensource, outfile)

    def format_unencoded(self, tokensource, outfile):
        if self.linenos:
            self._write_lineno(outfile)

        for ttype, value in tokensource:
            not_found = True
            while ttype and not_found:
                try:
                    # outfile.write( "<" + str(ttype) + ">" )
                    on, off = self.style_string[str(ttype)]

                    # Like TerminalFormatter, add "reset colors" escape sequence
                    # on newline.
                    spl = value.split('\n')
                    for line in spl[:-1]:
                        if line:
                            outfile.write(on + line + off)
                        if self.linenos:
                            self._write_lineno(outfile)
                        else:
                            outfile.write('\n')

                    if spl[-1]:
                        outfile.write(on + spl[-1] + off)

                    not_found = False
                    # outfile.write( '#' + str(ttype) + '#' )

                except KeyError:
                    # ottype = ttype
                    ttype = ttype.parent
                    # outfile.write( '!' + str(ottype) + '->' + str(ttype) + '!' )

            if not_found:
                outfile.write(value)

        if self.linenos:
            outfile.write("\n")



class TerminalTrueColorFormatter(Terminal256Formatter):
    r"""
    Format tokens with ANSI color sequences, for output in a true-color
    terminal or console.  Like in `TerminalFormatter` color sequences
    are terminated at newlines, so that paging the output works correctly.

    .. versionadded:: 2.1

    Options accepted:

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).
    """
    name = 'TerminalTrueColor'
    aliases = ['terminal16m', 'console16m', '16m']
    filenames = []

    def _build_color_table(self):
        pass

    def _color_tuple(self, color):
        try:
            rgb = int(str(color), 16)
        except ValueError:
            return None
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (r, g, b)

    def _setup_styles(self):
        for ttype, ndef in self.style:
            escape = EscapeSequence()
            if ndef['color']:
                escape.fg = self._color_tuple(ndef['color'])
            if ndef['bgcolor']:
                escape.bg = self._color_tuple(ndef['bgcolor'])
            if self.usebold and ndef['bold']:
                escape.bold = True
            if self.useunderline and ndef['underline']:
                escape.underline = True
            if self.useitalic and ndef['italic']:
                escape.italic = True
            self.style_string[str(ttype)] = (escape.true_color_string(),
                                             escape.reset_string())

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\unpacking.py ===
"""Utilities related archives.
"""

import logging
import os
import shutil
import stat
import sys
import tarfile
import zipfile
from typing import Iterable, List, Optional
from zipfile import ZipInfo

from pip._internal.exceptions import InstallationError
from pip._internal.utils.filetypes import (
    BZ2_EXTENSIONS,
    TAR_EXTENSIONS,
    XZ_EXTENSIONS,
    ZIP_EXTENSIONS,
)
from pip._internal.utils.misc import ensure_dir

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = ZIP_EXTENSIONS + TAR_EXTENSIONS

try:
    import bz2  # noqa

    SUPPORTED_EXTENSIONS += BZ2_EXTENSIONS
except ImportError:
    logger.debug("bz2 module is not available")

try:
    # Only for Python 3.3+
    import lzma  # noqa

    SUPPORTED_EXTENSIONS += XZ_EXTENSIONS
except ImportError:
    logger.debug("lzma module is not available")


def current_umask() -> int:
    """Get the current umask which involves having to set it temporarily."""
    mask = os.umask(0)
    os.umask(mask)
    return mask


def split_leading_dir(path: str) -> List[str]:
    path = path.lstrip("/").lstrip("\\")
    if "/" in path and (
        ("\\" in path and path.find("/") < path.find("\\")) or "\\" not in path
    ):
        return path.split("/", 1)
    elif "\\" in path:
        return path.split("\\", 1)
    else:
        return [path, ""]


def has_leading_dir(paths: Iterable[str]) -> bool:
    """Returns true if all the paths have the same leading path name
    (i.e., everything is in one subdirectory in an archive)"""
    common_prefix = None
    for path in paths:
        prefix, rest = split_leading_dir(path)
        if not prefix:
            return False
        elif common_prefix is None:
            common_prefix = prefix
        elif prefix != common_prefix:
            return False
    return True


def is_within_directory(directory: str, target: str) -> bool:
    """
    Return true if the absolute path of target is within the directory
    """
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])
    return prefix == abs_directory


def _get_default_mode_plus_executable() -> int:
    return 0o777 & ~current_umask() | 0o111


def set_extracted_file_to_default_mode_plus_executable(path: str) -> None:
    """
    Make file present at path have execute for user/group/world
    (chmod +x) is no-op on windows per python docs
    """
    os.chmod(path, _get_default_mode_plus_executable())


def zip_item_is_executable(info: ZipInfo) -> bool:
    mode = info.external_attr >> 16
    # if mode and regular file and any execute permissions for
    # user/group/world?
    return bool(mode and stat.S_ISREG(mode) and mode & 0o111)


def unzip_file(filename: str, location: str, flatten: bool = True) -> None:
    """
    Unzip the file (with path `filename`) to the destination `location`.  All
    files are written based on system defaults and umask (i.e. permissions are
    not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written. Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    zipfp = open(filename, "rb")
    try:
        zip = zipfile.ZipFile(zipfp, allowZip64=True)
        leading = has_leading_dir(zip.namelist()) and flatten
        for info in zip.infolist():
            name = info.filename
            fn = name
            if leading:
                fn = split_leading_dir(name)[1]
            fn = os.path.join(location, fn)
            dir = os.path.dirname(fn)
            if not is_within_directory(location, fn):
                message = (
                    "The zip file ({}) has a file ({}) trying to install "
                    "outside target directory ({})"
                )
                raise InstallationError(message.format(filename, fn, location))
            if fn.endswith("/") or fn.endswith("\\"):
                # A directory
                ensure_dir(fn)
            else:
                ensure_dir(dir)
                # Don't use read() to avoid allocating an arbitrarily large
                # chunk of memory for the file's content
                fp = zip.open(name)
                try:
                    with open(fn, "wb") as destfp:
                        shutil.copyfileobj(fp, destfp)
                finally:
                    fp.close()
                    if zip_item_is_executable(info):
                        set_extracted_file_to_default_mode_plus_executable(fn)
    finally:
        zipfp.close()


def untar_file(filename: str, location: str) -> None:
    """
    Untar the file (with path `filename`) to the destination `location`.
    All files are written based on system defaults and umask (i.e. permissions
    are not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied on top of the
    default.  Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    if filename.lower().endswith(".gz") or filename.lower().endswith(".tgz"):
        mode = "r:gz"
    elif filename.lower().endswith(BZ2_EXTENSIONS):
        mode = "r:bz2"
    elif filename.lower().endswith(XZ_EXTENSIONS):
        mode = "r:xz"
    elif filename.lower().endswith(".tar"):
        mode = "r"
    else:
        logger.warning(
            "Cannot determine compression type for file %s",
            filename,
        )
        mode = "r:*"

    tar = tarfile.open(filename, mode, encoding="utf-8")  # type: ignore
    try:
        leading = has_leading_dir([member.name for member in tar.getmembers()])

        # PEP 706 added `tarfile.data_filter`, and made some other changes to
        # Python's tarfile module (see below). The features were backported to
        # security releases.
        try:
            data_filter = tarfile.data_filter
        except AttributeError:
            _untar_without_filter(filename, location, tar, leading)
        else:
            default_mode_plus_executable = _get_default_mode_plus_executable()

            if leading:
                # Strip the leading directory from all files in the archive,
                # including hardlink targets (which are relative to the
                # unpack location).
                for member in tar.getmembers():
                    name_lead, name_rest = split_leading_dir(member.name)
                    member.name = name_rest
                    if member.islnk():
                        lnk_lead, lnk_rest = split_leading_dir(member.linkname)
                        if lnk_lead == name_lead:
                            member.linkname = lnk_rest

            def pip_filter(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo:
                orig_mode = member.mode
                try:
                    try:
                        member = data_filter(member, location)
                    except tarfile.LinkOutsideDestinationError:
                        if sys.version_info[:3] in {
                            (3, 8, 17),
                            (3, 9, 17),
                            (3, 10, 12),
                            (3, 11, 4),
                        }:
                            # The tarfile filter in specific Python versions
                            # raises LinkOutsideDestinationError on valid input
                            # (https://github.com/python/cpython/issues/107845)
                            # Ignore the error there, but do use the
                            # more lax `tar_filter`
                            member = tarfile.tar_filter(member, location)
                        else:
                            raise
                except tarfile.TarError as exc:
                    message = "Invalid member in the tar file {}: {}"
                    # Filter error messages mention the member name.
                    # No need to add it here.
                    raise InstallationError(
                        message.format(
                            filename,
                            exc,
                        )
                    )
                if member.isfile() and orig_mode & 0o111:
                    member.mode = default_mode_plus_executable
                else:
                    # See PEP 706 note above.
                    # The PEP changed this from `int` to `Optional[int]`,
                    # where None means "use the default". Mypy doesn't
                    # know this yet.
                    member.mode = None  # type: ignore [assignment]
                return member

            tar.extractall(location, filter=pip_filter)

    finally:
        tar.close()


def _untar_without_filter(
    filename: str,
    location: str,
    tar: tarfile.TarFile,
    leading: bool,
) -> None:
    """Fallback for Python without tarfile.data_filter"""
    for member in tar.getmembers():
        fn = member.name
        if leading:
            fn = split_leading_dir(fn)[1]
        path = os.path.join(location, fn)
        if not is_within_directory(location, path):
            message = (
                "The tar file ({}) has a file ({}) trying to install "
                "outside target directory ({})"
            )
            raise InstallationError(message.format(filename, path, location))
        if member.isdir():
            ensure_dir(path)
        elif member.issym():
            try:
                tar._extract_member(member, path)
            except Exception as exc:
                # Some corrupt tar files seem to produce this
                # (specifically bad symlinks)
                logger.warning(
                    "In the tar file %s the member %s is invalid: %s",
                    filename,
                    member.name,
                    exc,
                )
                continue
        else:
            try:
                fp = tar.extractfile(member)
            except (KeyError, AttributeError) as exc:
                # Some corrupt tar files seem to produce this
                # (specifically bad symlinks)
                logger.warning(
                    "In the tar file %s the member %s is invalid: %s",
                    filename,
                    member.name,
                    exc,
                )
                continue
            ensure_dir(os.path.dirname(path))
            assert fp is not None
            with open(path, "wb") as destfp:
                shutil.copyfileobj(fp, destfp)
            fp.close()
            # Update the timestamp (useful for cython compiled files)
            tar.utime(member, path)
            # member have any execute permissions for user/group/world?
            if member.mode & 0o111:
                set_extracted_file_to_default_mode_plus_executable(path)


def unpack_file(
    filename: str,
    location: str,
    content_type: Optional[str] = None,
) -> None:
    filename = os.path.realpath(filename)
    if (
        content_type == "application/zip"
        or filename.lower().endswith(ZIP_EXTENSIONS)
        or zipfile.is_zipfile(filename)
    ):
        unzip_file(filename, location, flatten=not filename.endswith(".whl"))
    elif (
        content_type == "application/x-gzip"
        or tarfile.is_tarfile(filename)
        or filename.lower().endswith(TAR_EXTENSIONS + BZ2_EXTENSIONS + XZ_EXTENSIONS)
    ):
        untar_file(filename, location)
    else:
        # FIXME: handle?
        # FIXME: magic signatures?
        logger.critical(
            "Cannot unpack file %s (downloaded from %s, content-type: %s); "
            "cannot detect archive format",
            filename,
            location,
            content_type,
        )
        raise InstallationError(f"Cannot determine archive format of {location}")

# === NexusCore/openenv\Lib\site-packages\setuptools\_core_metadata.py ===
"""
Handling of Core Metadata for Python packages (including reading and writing).

See: https://packaging.python.org/en/latest/specifications/core-metadata/
"""

from __future__ import annotations

import os
import stat
import textwrap
from email import message_from_file
from email.message import Message
from tempfile import NamedTemporaryFile

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, canonicalize_version
from packaging.version import Version

from . import _normalization, _reqs
from ._static import is_static
from .warnings import SetuptoolsDeprecationWarning

from distutils.util import rfc822_escape


def get_metadata_version(self):
    mv = getattr(self, 'metadata_version', None)
    if mv is None:
        mv = Version('2.4')
        self.metadata_version = mv
    return mv


def rfc822_unescape(content: str) -> str:
    """Reverse RFC-822 escaping by removing leading whitespaces from content."""
    lines = content.splitlines()
    if len(lines) == 1:
        return lines[0].lstrip()
    return '\n'.join((lines[0].lstrip(), textwrap.dedent('\n'.join(lines[1:]))))


def _read_field_from_msg(msg: Message, field: str) -> str | None:
    """Read Message header field."""
    value = msg[field]
    if value == 'UNKNOWN':
        return None
    return value


def _read_field_unescaped_from_msg(msg: Message, field: str) -> str | None:
    """Read Message header field and apply rfc822_unescape."""
    value = _read_field_from_msg(msg, field)
    if value is None:
        return value
    return rfc822_unescape(value)


def _read_list_from_msg(msg: Message, field: str) -> list[str] | None:
    """Read Message header field and return all results as list."""
    values = msg.get_all(field, None)
    if values == []:
        return None
    return values


def _read_payload_from_msg(msg: Message) -> str | None:
    value = str(msg.get_payload()).strip()
    if value == 'UNKNOWN' or not value:
        return None
    return value


def read_pkg_file(self, file):
    """Reads the metadata values from a file object."""
    msg = message_from_file(file)

    self.metadata_version = Version(msg['metadata-version'])
    self.name = _read_field_from_msg(msg, 'name')
    self.version = _read_field_from_msg(msg, 'version')
    self.description = _read_field_from_msg(msg, 'summary')
    # we are filling author only.
    self.author = _read_field_from_msg(msg, 'author')
    self.maintainer = None
    self.author_email = _read_field_from_msg(msg, 'author-email')
    self.maintainer_email = None
    self.url = _read_field_from_msg(msg, 'home-page')
    self.download_url = _read_field_from_msg(msg, 'download-url')
    self.license = _read_field_unescaped_from_msg(msg, 'license')
    self.license_expression = _read_field_unescaped_from_msg(msg, 'license-expression')

    self.long_description = _read_field_unescaped_from_msg(msg, 'description')
    if self.long_description is None and self.metadata_version >= Version('2.1'):
        self.long_description = _read_payload_from_msg(msg)
    self.description = _read_field_from_msg(msg, 'summary')

    if 'keywords' in msg:
        self.keywords = _read_field_from_msg(msg, 'keywords').split(',')

    self.platforms = _read_list_from_msg(msg, 'platform')
    self.classifiers = _read_list_from_msg(msg, 'classifier')

    # PEP 314 - these fields only exist in 1.1
    if self.metadata_version == Version('1.1'):
        self.requires = _read_list_from_msg(msg, 'requires')
        self.provides = _read_list_from_msg(msg, 'provides')
        self.obsoletes = _read_list_from_msg(msg, 'obsoletes')
    else:
        self.requires = None
        self.provides = None
        self.obsoletes = None

    self.license_files = _read_list_from_msg(msg, 'license-file')


def single_line(val):
    """
    Quick and dirty validation for Summary pypa/setuptools#1390.
    """
    if '\n' in val:
        # TODO: Replace with `raise ValueError("newlines not allowed")`
        # after reviewing #2893.
        msg = "newlines are not allowed in `summary` and will break in the future"
        SetuptoolsDeprecationWarning.emit("Invalid config.", msg)
        # due_date is undefined. Controversial change, there was a lot of push back.
        val = val.strip().split('\n')[0]
    return val


def write_pkg_info(self, base_dir):
    """Write the PKG-INFO file into the release tree."""
    temp = ""
    final = os.path.join(base_dir, 'PKG-INFO')
    try:
        # Use a temporary file while writing to avoid race conditions
        # (e.g. `importlib.metadata` reading `.egg-info/PKG-INFO`):
        with NamedTemporaryFile("w", encoding="utf-8", dir=base_dir, delete=False) as f:
            temp = f.name
            self.write_pkg_file(f)
        permissions = stat.S_IMODE(os.lstat(temp).st_mode)
        os.chmod(temp, permissions | stat.S_IRGRP | stat.S_IROTH)
        os.replace(temp, final)  # atomic operation.
    finally:
        if temp and os.path.exists(temp):
            os.remove(temp)


# Based on Python 3.5 version
def write_pkg_file(self, file):  # noqa: C901  # is too complex (14)  # FIXME
    """Write the PKG-INFO format data to a file object."""
    version = self.get_metadata_version()

    def write_field(key, value):
        file.write(f"{key}: {value}\n")

    write_field('Metadata-Version', str(version))
    write_field('Name', self.get_name())
    write_field('Version', self.get_version())

    summary = self.get_description()
    if summary:
        write_field('Summary', single_line(summary))

    optional_fields = (
        ('Home-page', 'url'),
        ('Download-URL', 'download_url'),
        ('Author', 'author'),
        ('Author-email', 'author_email'),
        ('Maintainer', 'maintainer'),
        ('Maintainer-email', 'maintainer_email'),
    )

    for field, attr in optional_fields:
        attr_val = getattr(self, attr, None)
        if attr_val is not None:
            write_field(field, attr_val)

    if license_expression := self.license_expression:
        write_field('License-Expression', license_expression)
    elif license := self.get_license():
        write_field('License', rfc822_escape(license))

    for label, url in self.project_urls.items():
        write_field('Project-URL', f'{label}, {url}')

    keywords = ','.join(self.get_keywords())
    if keywords:
        write_field('Keywords', keywords)

    platforms = self.get_platforms() or []
    for platform in platforms:
        write_field('Platform', platform)

    self._write_list(file, 'Classifier', self.get_classifiers())

    # PEP 314
    self._write_list(file, 'Requires', self.get_requires())
    self._write_list(file, 'Provides', self.get_provides())
    self._write_list(file, 'Obsoletes', self.get_obsoletes())

    # Setuptools specific for PEP 345
    if hasattr(self, 'python_requires'):
        write_field('Requires-Python', self.python_requires)

    # PEP 566
    if self.long_description_content_type:
        write_field('Description-Content-Type', self.long_description_content_type)

    safe_license_files = map(_safe_license_file, self.license_files or [])
    self._write_list(file, 'License-File', safe_license_files)
    _write_requirements(self, file)

    for field, attr in _POSSIBLE_DYNAMIC_FIELDS.items():
        if (val := getattr(self, attr, None)) and not is_static(val):
            write_field('Dynamic', field)

    long_description = self.get_long_description()
    if long_description:
        file.write(f"\n{long_description}")
        if not long_description.endswith("\n"):
            file.write("\n")


def _write_requirements(self, file):
    for req in _reqs.parse(self.install_requires):
        file.write(f"Requires-Dist: {req}\n")

    processed_extras = {}
    for augmented_extra, reqs in self.extras_require.items():
        # Historically, setuptools allows "augmented extras": `<extra>:<condition>`
        unsafe_extra, _, condition = augmented_extra.partition(":")
        unsafe_extra = unsafe_extra.strip()
        extra = _normalization.safe_extra(unsafe_extra)

        if extra:
            _write_provides_extra(file, processed_extras, extra, unsafe_extra)
        for req in _reqs.parse_strings(reqs):
            r = _include_extra(req, extra, condition.strip())
            file.write(f"Requires-Dist: {r}\n")

    return processed_extras


def _include_extra(req: str, extra: str, condition: str) -> Requirement:
    r = Requirement(req)  # create a fresh object that can be modified
    parts = (
        f"({r.marker})" if r.marker else None,
        f"({condition})" if condition else None,
        f"extra == {extra!r}" if extra else None,
    )
    r.marker = Marker(" and ".join(x for x in parts if x))
    return r


def _write_provides_extra(file, processed_extras, safe, unsafe):
    previous = processed_extras.get(safe)
    if previous == unsafe:
        SetuptoolsDeprecationWarning.emit(
            'Ambiguity during "extra" normalization for dependencies.',
            f"""
            {previous!r} and {unsafe!r} normalize to the same value:\n
                {safe!r}\n
            In future versions, setuptools might halt the build process.
            """,
            see_url="https://peps.python.org/pep-0685/",
        )
    else:
        processed_extras[safe] = unsafe
        file.write(f"Provides-Extra: {safe}\n")


# from pypa/distutils#244; needed only until that logic is always available
def get_fullname(self):
    return _distribution_fullname(self.get_name(), self.get_version())


def _distribution_fullname(name: str, version: str) -> str:
    """
    >>> _distribution_fullname('setup.tools', '1.0-2')
    'setup_tools-1.0.post2'
    >>> _distribution_fullname('setup-tools', '1.2post2')
    'setup_tools-1.2.post2'
    >>> _distribution_fullname('setup-tools', '1.0-r2')
    'setup_tools-1.0.post2'
    >>> _distribution_fullname('setup.tools', '1.0.post')
    'setup_tools-1.0.post0'
    >>> _distribution_fullname('setup.tools', '1.0+ubuntu-1')
    'setup_tools-1.0+ubuntu.1'
    """
    return "{}-{}".format(
        canonicalize_name(name).replace('-', '_'),
        canonicalize_version(version, strip_trailing_zero=False),
    )


def _safe_license_file(file):
    # XXX: Do we need this after the deprecation discussed in #4892, #4896??
    normalized = os.path.normpath(file).replace(os.sep, "/")
    if "../" in normalized:
        return os.path.basename(normalized)  # Temporarily restore pre PEP639 behaviour
    return normalized


_POSSIBLE_DYNAMIC_FIELDS = {
    # Core Metadata Field x related Distribution attribute
    "author": "author",
    "author-email": "author_email",
    "classifier": "classifiers",
    "description": "long_description",
    "description-content-type": "long_description_content_type",
    "download-url": "download_url",
    "home-page": "url",
    "keywords": "keywords",
    "license": "license",
    # XXX: License-File is complicated because the user gives globs that are expanded
    #      during the build. Without special handling it is likely always
    #      marked as Dynamic, which is an acceptable outcome according to:
    #      https://github.com/pypa/setuptools/issues/4629#issuecomment-2331233677
    "license-file": "license_files",
    "license-expression": "license_expression",  # PEP 639
    "maintainer": "maintainer",
    "maintainer-email": "maintainer_email",
    "obsoletes": "obsoletes",
    # "obsoletes-dist": "obsoletes_dist",  # NOT USED
    "platform": "platforms",
    "project-url": "project_urls",
    "provides": "provides",
    # "provides-dist": "provides_dist",  # NOT USED
    "provides-extra": "extras_require",
    "requires": "requires",
    "requires-dist": "install_requires",
    # "requires-external": "requires_external",  # NOT USED
    "requires-python": "python_requires",
    "summary": "description",
    # "supported-platform": "supported_platforms",  # NOT USED
}

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_g_v_a_r.py ===
from collections import deque
from functools import partial
from fontTools.misc import sstruct
from fontTools.misc.textTools import safeEval
from fontTools.misc.lazyTools import LazyDict
from fontTools.ttLib import OPTIMIZE_FONT_SPEED
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from . import DefaultTable
import array
import itertools
import logging
import struct
import sys
import fontTools.ttLib.tables.TupleVariation as tv

log = logging.getLogger(__name__)

# https://www.microsoft.com/typography/otspec/gvar.htm
# https://www.microsoft.com/typography/otspec/otvarcommonformats.htm
#
# Apple's documentation of 'gvar':
# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6gvar.html
#
# FreeType2 source code for parsing 'gvar':
# http://git.savannah.gnu.org/cgit/freetype/freetype2.git/tree/src/truetype/ttgxvar.c

GVAR_HEADER_FORMAT_HEAD = """
	> # big endian
	version:			H
	reserved:			H
	axisCount:			H
	sharedTupleCount:		H
	offsetToSharedTuples:		I
"""
# In between the HEAD and TAIL lies the glyphCount, which is
# of different size: 2 bytes for gvar, and 3 bytes for GVAR.
GVAR_HEADER_FORMAT_TAIL = """
	> # big endian
	flags:				H
	offsetToGlyphVariationData:	I
"""

GVAR_HEADER_SIZE_HEAD = sstruct.calcsize(GVAR_HEADER_FORMAT_HEAD)
GVAR_HEADER_SIZE_TAIL = sstruct.calcsize(GVAR_HEADER_FORMAT_TAIL)


class table__g_v_a_r(DefaultTable.DefaultTable):
    """Glyph Variations table

    The ``gvar`` table provides the per-glyph variation data that
    describe how glyph outlines in the ``glyf`` table change across
    the variation space that is defined for the font in the ``fvar``
    table.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/gvar
    """

    dependencies = ["fvar", "glyf"]
    gid_size = 2

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.version, self.reserved = 1, 0
        self.variations = {}

    def compile(self, ttFont):

        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        sharedTuples = tv.compileSharedTuples(
            axisTags, itertools.chain(*self.variations.values())
        )
        sharedTupleIndices = {coord: i for i, coord in enumerate(sharedTuples)}
        sharedTupleSize = sum([len(c) for c in sharedTuples])
        compiledGlyphs = self.compileGlyphs_(ttFont, axisTags, sharedTupleIndices)
        offset = 0
        offsets = []
        for glyph in compiledGlyphs:
            offsets.append(offset)
            offset += len(glyph)
        offsets.append(offset)
        compiledOffsets, tableFormat = self.compileOffsets_(offsets)

        GVAR_HEADER_SIZE = GVAR_HEADER_SIZE_HEAD + self.gid_size + GVAR_HEADER_SIZE_TAIL
        header = {}
        header["version"] = self.version
        header["reserved"] = self.reserved
        header["axisCount"] = len(axisTags)
        header["sharedTupleCount"] = len(sharedTuples)
        header["offsetToSharedTuples"] = GVAR_HEADER_SIZE + len(compiledOffsets)
        header["flags"] = tableFormat
        header["offsetToGlyphVariationData"] = (
            header["offsetToSharedTuples"] + sharedTupleSize
        )

        result = [
            sstruct.pack(GVAR_HEADER_FORMAT_HEAD, header),
            len(compiledGlyphs).to_bytes(self.gid_size, "big"),
            sstruct.pack(GVAR_HEADER_FORMAT_TAIL, header),
        ]

        result.append(compiledOffsets)
        result.extend(sharedTuples)
        result.extend(compiledGlyphs)
        return b"".join(result)

    def compileGlyphs_(self, ttFont, axisTags, sharedCoordIndices):
        optimizeSpeed = ttFont.cfg[OPTIMIZE_FONT_SPEED]
        result = []
        glyf = ttFont["glyf"]
        for glyphName in ttFont.getGlyphOrder():
            variations = self.variations.get(glyphName, [])
            if not variations:
                result.append(b"")
                continue
            pointCountUnused = 0  # pointCount is actually unused by compileGlyph
            result.append(
                compileGlyph_(
                    self.gid_size,
                    variations,
                    pointCountUnused,
                    axisTags,
                    sharedCoordIndices,
                    optimizeSize=not optimizeSpeed,
                )
            )
        return result

    def decompile(self, data, ttFont):
        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        glyphs = ttFont.getGlyphOrder()

        # Parse the header
        GVAR_HEADER_SIZE = GVAR_HEADER_SIZE_HEAD + self.gid_size + GVAR_HEADER_SIZE_TAIL
        sstruct.unpack(GVAR_HEADER_FORMAT_HEAD, data[:GVAR_HEADER_SIZE_HEAD], self)
        self.glyphCount = int.from_bytes(
            data[GVAR_HEADER_SIZE_HEAD : GVAR_HEADER_SIZE_HEAD + self.gid_size], "big"
        )
        sstruct.unpack(
            GVAR_HEADER_FORMAT_TAIL,
            data[GVAR_HEADER_SIZE_HEAD + self.gid_size : GVAR_HEADER_SIZE],
            self,
        )

        assert len(glyphs) == self.glyphCount
        assert len(axisTags) == self.axisCount
        sharedCoords = tv.decompileSharedTuples(
            axisTags, self.sharedTupleCount, data, self.offsetToSharedTuples
        )
        variations = {}
        offsetToData = self.offsetToGlyphVariationData
        glyf = ttFont["glyf"]

        def get_read_item():
            reverseGlyphMap = ttFont.getReverseGlyphMap()
            tableFormat = self.flags & 1

            def read_item(glyphName):
                gid = reverseGlyphMap[glyphName]
                offsetSize = 2 if tableFormat == 0 else 4
                startOffset = GVAR_HEADER_SIZE + offsetSize * gid
                endOffset = startOffset + offsetSize * 2
                offsets = table__g_v_a_r.decompileOffsets_(
                    data[startOffset:endOffset],
                    tableFormat=tableFormat,
                    glyphCount=1,
                )
                gvarData = data[offsetToData + offsets[0] : offsetToData + offsets[1]]
                if not gvarData:
                    return []
                glyph = glyf[glyphName]
                numPointsInGlyph = self.getNumPoints_(glyph)
                return decompileGlyph_(
                    self.gid_size, numPointsInGlyph, sharedCoords, axisTags, gvarData
                )

            return read_item

        read_item = get_read_item()
        l = LazyDict({glyphs[gid]: read_item for gid in range(self.glyphCount)})

        self.variations = l

        if ttFont.lazy is False:  # Be lazy for None and True
            self.ensureDecompiled()

    def ensureDecompiled(self, recurse=False):
        # The recurse argument is unused, but part of the signature of
        # ensureDecompiled across the library.
        # Use a zero-length deque to consume the lazy dict
        deque(self.variations.values(), maxlen=0)

    @staticmethod
    def decompileOffsets_(data, tableFormat, glyphCount):
        if tableFormat == 0:
            # Short format: array of UInt16
            offsets = array.array("H")
            offsetsSize = (glyphCount + 1) * 2
        else:
            # Long format: array of UInt32
            offsets = array.array("I")
            offsetsSize = (glyphCount + 1) * 4
        offsets.frombytes(data[0:offsetsSize])
        if sys.byteorder != "big":
            offsets.byteswap()

        # In the short format, offsets need to be multiplied by 2.
        # This is not documented in Apple's TrueType specification,
        # but can be inferred from the FreeType implementation, and
        # we could verify it with two sample GX fonts.
        if tableFormat == 0:
            offsets = [off * 2 for off in offsets]

        return offsets

    @staticmethod
    def compileOffsets_(offsets):
        """Packs a list of offsets into a 'gvar' offset table.

        Returns a pair (bytestring, tableFormat). Bytestring is the
        packed offset table. Format indicates whether the table
        uses short (tableFormat=0) or long (tableFormat=1) integers.
        The returned tableFormat should get packed into the flags field
        of the 'gvar' header.
        """
        assert len(offsets) >= 2
        for i in range(1, len(offsets)):
            assert offsets[i - 1] <= offsets[i]
        if max(offsets) <= 0xFFFF * 2:
            packed = array.array("H", [n >> 1 for n in offsets])
            tableFormat = 0
        else:
            packed = array.array("I", offsets)
            tableFormat = 1
        if sys.byteorder != "big":
            packed.byteswap()
        return (packed.tobytes(), tableFormat)

    def toXML(self, writer, ttFont):
        writer.simpletag("version", value=self.version)
        writer.newline()
        writer.simpletag("reserved", value=self.reserved)
        writer.newline()
        axisTags = [axis.axisTag for axis in ttFont["fvar"].axes]
        for glyphName in ttFont.getGlyphNames():
            variations = self.variations.get(glyphName)
            if not variations:
                continue
            writer.begintag("glyphVariations", glyph=glyphName)
            writer.newline()
            for gvar in variations:
                gvar.toXML(writer, axisTags)
            writer.endtag("glyphVariations")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = safeEval(attrs["value"])
        elif name == "reserved":
            self.reserved = safeEval(attrs["value"])
        elif name == "glyphVariations":
            if not hasattr(self, "variations"):
                self.variations = {}
            glyphName = attrs["glyph"]
            glyph = ttFont["glyf"][glyphName]
            numPointsInGlyph = self.getNumPoints_(glyph)
            glyphVariations = []
            for element in content:
                if isinstance(element, tuple):
                    name, attrs, content = element
                    if name == "tuple":
                        gvar = TupleVariation({}, [None] * numPointsInGlyph)
                        glyphVariations.append(gvar)
                        for tupleElement in content:
                            if isinstance(tupleElement, tuple):
                                tupleName, tupleAttrs, tupleContent = tupleElement
                                gvar.fromXML(tupleName, tupleAttrs, tupleContent)
            self.variations[glyphName] = glyphVariations

    @staticmethod
    def getNumPoints_(glyph):
        NUM_PHANTOM_POINTS = 4

        if glyph.isComposite():
            return len(glyph.components) + NUM_PHANTOM_POINTS
        else:
            # Empty glyphs (eg. space, nonmarkingreturn) have no "coordinates" attribute.
            return len(getattr(glyph, "coordinates", [])) + NUM_PHANTOM_POINTS


def compileGlyph_(
    dataOffsetSize,
    variations,
    pointCount,
    axisTags,
    sharedCoordIndices,
    *,
    optimizeSize=True,
):
    assert dataOffsetSize in (2, 3)
    tupleVariationCount, tuples, data = tv.compileTupleVariationStore(
        variations, pointCount, axisTags, sharedCoordIndices, optimizeSize=optimizeSize
    )
    if tupleVariationCount == 0:
        return b""

    offsetToData = 2 + dataOffsetSize + len(tuples)

    result = [
        tupleVariationCount.to_bytes(2, "big"),
        offsetToData.to_bytes(dataOffsetSize, "big"),
        tuples,
        data,
    ]
    if (offsetToData + len(data)) % 2 != 0:
        result.append(b"\0")  # padding
    return b"".join(result)


def decompileGlyph_(dataOffsetSize, pointCount, sharedTuples, axisTags, data):
    assert dataOffsetSize in (2, 3)
    if len(data) < 2 + dataOffsetSize:
        return []

    tupleVariationCount = int.from_bytes(data[:2], "big")
    offsetToData = int.from_bytes(data[2 : 2 + dataOffsetSize], "big")

    dataPos = offsetToData
    return tv.decompileTupleVariationStore(
        "gvar",
        axisTags,
        tupleVariationCount,
        pointCount,
        sharedTuples,
        data,
        2 + dataOffsetSize,
        offsetToData,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\responses\streaming_iterator.py ===
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from litellm.constants import STREAM_SSE_DONE_STRING
from litellm.litellm_core_utils.asyncify import run_async_function
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.thread_pool_executor import executor
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig
from litellm.responses.utils import ResponsesAPIRequestUtils
from litellm.types.llms.openai import (
    OutputTextDeltaEvent,
    ResponseCompletedEvent,
    ResponsesAPIResponse,
    ResponsesAPIStreamEvents,
    ResponsesAPIStreamingResponse,
)
from litellm.utils import CustomStreamWrapper


class BaseResponsesAPIStreamingIterator:
    """
    Base class for streaming iterators that process responses from the Responses API.

    This class contains shared logic for both synchronous and asynchronous iterators.
    """

    def __init__(
        self,
        response: httpx.Response,
        model: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        logging_obj: LiteLLMLoggingObj,
        litellm_metadata: Optional[Dict[str, Any]] = None,
        custom_llm_provider: Optional[str] = None,
    ):
        self.response = response
        self.model = model
        self.logging_obj = logging_obj
        self.finished = False
        self.responses_api_provider_config = responses_api_provider_config
        self.completed_response: Optional[ResponsesAPIStreamingResponse] = None
        self.start_time = datetime.now()

        # set request kwargs
        self.litellm_metadata = litellm_metadata
        self.custom_llm_provider = custom_llm_provider

    def _process_chunk(self, chunk) -> Optional[ResponsesAPIStreamingResponse]:
        """Process a single chunk of data from the stream"""
        if not chunk:
            return None

        # Handle SSE format (data: {...})
        chunk = CustomStreamWrapper._strip_sse_data_from_chunk(chunk)
        if chunk is None:
            return None

        # Handle "[DONE]" marker
        if chunk == STREAM_SSE_DONE_STRING:
            self.finished = True
            return None

        try:
            # Parse the JSON chunk
            parsed_chunk = json.loads(chunk)

            # Format as ResponsesAPIStreamingResponse
            if isinstance(parsed_chunk, dict):
                openai_responses_api_chunk = (
                    self.responses_api_provider_config.transform_streaming_response(
                        model=self.model,
                        parsed_chunk=parsed_chunk,
                        logging_obj=self.logging_obj,
                    )
                )

                # if "response" in parsed_chunk, then encode litellm specific information like custom_llm_provider
                response_object = getattr(openai_responses_api_chunk, "response", None)
                if response_object:
                    response = ResponsesAPIRequestUtils._update_responses_api_response_id_with_model_id(
                        responses_api_response=response_object,
                        litellm_metadata=self.litellm_metadata,
                        custom_llm_provider=self.custom_llm_provider,
                    )
                    setattr(openai_responses_api_chunk, "response", response)

                # Store the completed response
                if (
                    openai_responses_api_chunk
                    and openai_responses_api_chunk.type
                    == ResponsesAPIStreamEvents.RESPONSE_COMPLETED
                ):
                    self.completed_response = openai_responses_api_chunk
                    self._handle_logging_completed_response()

                return openai_responses_api_chunk

            return None
        except json.JSONDecodeError:
            # If we can't parse the chunk, continue
            return None

    def _handle_logging_completed_response(self):
        """Base implementation - should be overridden by subclasses"""
        pass


class ResponsesAPIStreamingIterator(BaseResponsesAPIStreamingIterator):
    """
    Async iterator for processing streaming responses from the Responses API.
    """

    def __init__(
        self,
        response: httpx.Response,
        model: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        logging_obj: LiteLLMLoggingObj,
        litellm_metadata: Optional[Dict[str, Any]] = None,
        custom_llm_provider: Optional[str] = None,
    ):
        super().__init__(
            response,
            model,
            responses_api_provider_config,
            logging_obj,
            litellm_metadata,
            custom_llm_provider,
        )
        self.stream_iterator = response.aiter_lines()

    def __aiter__(self):
        return self

    async def __anext__(self) -> ResponsesAPIStreamingResponse:
        try:
            while True:
                # Get the next chunk from the stream
                try:
                    chunk = await self.stream_iterator.__anext__()
                except StopAsyncIteration:
                    self.finished = True
                    raise StopAsyncIteration

                result = self._process_chunk(chunk)

                if self.finished:
                    raise StopAsyncIteration
                elif result is not None:
                    return result
                # If result is None, continue the loop to get the next chunk

        except httpx.HTTPError as e:
            # Handle HTTP errors
            self.finished = True
            raise e

    def _handle_logging_completed_response(self):
        """Handle logging for completed responses in async context"""
        asyncio.create_task(
            self.logging_obj.async_success_handler(
                result=self.completed_response,
                start_time=self.start_time,
                end_time=datetime.now(),
                cache_hit=None,
            )
        )

        executor.submit(
            self.logging_obj.success_handler,
            result=self.completed_response,
            cache_hit=None,
            start_time=self.start_time,
            end_time=datetime.now(),
        )


class SyncResponsesAPIStreamingIterator(BaseResponsesAPIStreamingIterator):
    """
    Synchronous iterator for processing streaming responses from the Responses API.
    """

    def __init__(
        self,
        response: httpx.Response,
        model: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        logging_obj: LiteLLMLoggingObj,
        litellm_metadata: Optional[Dict[str, Any]] = None,
        custom_llm_provider: Optional[str] = None,
    ):
        super().__init__(
            response,
            model,
            responses_api_provider_config,
            logging_obj,
            litellm_metadata,
            custom_llm_provider,
        )
        self.stream_iterator = response.iter_lines()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            while True:
                # Get the next chunk from the stream
                try:
                    chunk = next(self.stream_iterator)
                except StopIteration:
                    self.finished = True
                    raise StopIteration

                result = self._process_chunk(chunk)

                if self.finished:
                    raise StopIteration
                elif result is not None:
                    return result
                # If result is None, continue the loop to get the next chunk

        except httpx.HTTPError as e:
            # Handle HTTP errors
            self.finished = True
            raise e

    def _handle_logging_completed_response(self):
        """Handle logging for completed responses in sync context"""
        run_async_function(
            async_function=self.logging_obj.async_success_handler,
            result=self.completed_response,
            start_time=self.start_time,
            end_time=datetime.now(),
            cache_hit=None,
        )

        executor.submit(
            self.logging_obj.success_handler,
            result=self.completed_response,
            cache_hit=None,
            start_time=self.start_time,
            end_time=datetime.now(),
        )


class MockResponsesAPIStreamingIterator(BaseResponsesAPIStreamingIterator):
    """
    Mock iterator—fake a stream by slicing the full response text into
    5 char deltas, then emit a completed event.

    Models like o1-pro don't support streaming, so we fake it.
    """

    CHUNK_SIZE = 5

    def __init__(
        self,
        response: httpx.Response,
        model: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        logging_obj: LiteLLMLoggingObj,
        litellm_metadata: Optional[Dict[str, Any]] = None,
        custom_llm_provider: Optional[str] = None,
    ):
        super().__init__(
            response=response,
            model=model,
            responses_api_provider_config=responses_api_provider_config,
            logging_obj=logging_obj,
            litellm_metadata=litellm_metadata,
            custom_llm_provider=custom_llm_provider,
        )

        # one-time transform
        transformed = (
            self.responses_api_provider_config.transform_response_api_response(
                model=self.model,
                raw_response=response,
                logging_obj=logging_obj,
            )
        )
        full_text = self._collect_text(transformed)

        # build a list of 5‑char delta events
        deltas = [
            OutputTextDeltaEvent(
                type=ResponsesAPIStreamEvents.OUTPUT_TEXT_DELTA,
                delta=full_text[i : i + self.CHUNK_SIZE],
                item_id=transformed.id,
                output_index=0,
                content_index=0,
            )
            for i in range(0, len(full_text), self.CHUNK_SIZE)
        ]

        # append the completed event
        self._events = deltas + [
            ResponseCompletedEvent(
                type=ResponsesAPIStreamEvents.RESPONSE_COMPLETED,
                response=transformed,
            )
        ]
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self) -> ResponsesAPIStreamingResponse:
        if self._idx >= len(self._events):
            raise StopAsyncIteration
        evt = self._events[self._idx]
        self._idx += 1
        return evt

    def __iter__(self):
        return self

    def __next__(self) -> ResponsesAPIStreamingResponse:
        if self._idx >= len(self._events):
            raise StopIteration
        evt = self._events[self._idx]
        self._idx += 1
        return evt

    def _collect_text(self, resp: ResponsesAPIResponse) -> str:
        out = ""
        for out_item in resp.output:
            item_type = getattr(out_item, "type", None)
            if item_type == "message":
                for c in getattr(out_item, "content", []):
                    out += c.text
        return out

# === NexusCore/openenv\Lib\site-packages\nltk\chat\eliza.py ===
# Natural Language Toolkit: Eliza
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Steven Bird <stevenbird1@gmail.com>
#          Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# Based on an Eliza implementation by Joe Strout <joe@strout.net>,
# Jeff Epler <jepler@inetnebr.com> and Jez Higgins <mailto:jez@jezuk.co.uk>.

# a translation table used to convert things you say into things the
# computer says back, e.g. "I am" --> "you are"

from nltk.chat.util import Chat, reflections

# a table of response pairs, where each pair consists of a
# regular expression, and a list of possible responses,
# with group-macros labelled as %1, %2.

pairs = (
    (
        r"I need (.*)",
        (
            "Why do you need %1?",
            "Would it really help you to get %1?",
            "Are you sure you need %1?",
        ),
    ),
    (
        r"Why don\'t you (.*)",
        (
            "Do you really think I don't %1?",
            "Perhaps eventually I will %1.",
            "Do you really want me to %1?",
        ),
    ),
    (
        r"Why can\'t I (.*)",
        (
            "Do you think you should be able to %1?",
            "If you could %1, what would you do?",
            "I don't know -- why can't you %1?",
            "Have you really tried?",
        ),
    ),
    (
        r"I can\'t (.*)",
        (
            "How do you know you can't %1?",
            "Perhaps you could %1 if you tried.",
            "What would it take for you to %1?",
        ),
    ),
    (
        r"I am (.*)",
        (
            "Did you come to me because you are %1?",
            "How long have you been %1?",
            "How do you feel about being %1?",
        ),
    ),
    (
        r"I\'m (.*)",
        (
            "How does being %1 make you feel?",
            "Do you enjoy being %1?",
            "Why do you tell me you're %1?",
            "Why do you think you're %1?",
        ),
    ),
    (
        r"Are you (.*)",
        (
            "Why does it matter whether I am %1?",
            "Would you prefer it if I were not %1?",
            "Perhaps you believe I am %1.",
            "I may be %1 -- what do you think?",
        ),
    ),
    (
        r"What (.*)",
        (
            "Why do you ask?",
            "How would an answer to that help you?",
            "What do you think?",
        ),
    ),
    (
        r"How (.*)",
        (
            "How do you suppose?",
            "Perhaps you can answer your own question.",
            "What is it you're really asking?",
        ),
    ),
    (
        r"Because (.*)",
        (
            "Is that the real reason?",
            "What other reasons come to mind?",
            "Does that reason apply to anything else?",
            "If %1, what else must be true?",
        ),
    ),
    (
        r"(.*) sorry (.*)",
        (
            "There are many times when no apology is needed.",
            "What feelings do you have when you apologize?",
        ),
    ),
    (
        r"Hello(.*)",
        (
            "Hello... I'm glad you could drop by today.",
            "Hi there... how are you today?",
            "Hello, how are you feeling today?",
        ),
    ),
    (
        r"I think (.*)",
        ("Do you doubt %1?", "Do you really think so?", "But you're not sure %1?"),
    ),
    (
        r"(.*) friend (.*)",
        (
            "Tell me more about your friends.",
            "When you think of a friend, what comes to mind?",
            "Why don't you tell me about a childhood friend?",
        ),
    ),
    (r"Yes", ("You seem quite sure.", "OK, but can you elaborate a bit?")),
    (
        r"(.*) computer(.*)",
        (
            "Are you really talking about me?",
            "Does it seem strange to talk to a computer?",
            "How do computers make you feel?",
            "Do you feel threatened by computers?",
        ),
    ),
    (
        r"Is it (.*)",
        (
            "Do you think it is %1?",
            "Perhaps it's %1 -- what do you think?",
            "If it were %1, what would you do?",
            "It could well be that %1.",
        ),
    ),
    (
        r"It is (.*)",
        (
            "You seem very certain.",
            "If I told you that it probably isn't %1, what would you feel?",
        ),
    ),
    (
        r"Can you (.*)",
        (
            "What makes you think I can't %1?",
            "If I could %1, then what?",
            "Why do you ask if I can %1?",
        ),
    ),
    (
        r"Can I (.*)",
        (
            "Perhaps you don't want to %1.",
            "Do you want to be able to %1?",
            "If you could %1, would you?",
        ),
    ),
    (
        r"You are (.*)",
        (
            "Why do you think I am %1?",
            "Does it please you to think that I'm %1?",
            "Perhaps you would like me to be %1.",
            "Perhaps you're really talking about yourself?",
        ),
    ),
    (
        r"You\'re (.*)",
        (
            "Why do you say I am %1?",
            "Why do you think I am %1?",
            "Are we talking about you, or me?",
        ),
    ),
    (
        r"I don\'t (.*)",
        ("Don't you really %1?", "Why don't you %1?", "Do you want to %1?"),
    ),
    (
        r"I feel (.*)",
        (
            "Good, tell me more about these feelings.",
            "Do you often feel %1?",
            "When do you usually feel %1?",
            "When you feel %1, what do you do?",
        ),
    ),
    (
        r"I have (.*)",
        (
            "Why do you tell me that you've %1?",
            "Have you really %1?",
            "Now that you have %1, what will you do next?",
        ),
    ),
    (
        r"I would (.*)",
        (
            "Could you explain why you would %1?",
            "Why would you %1?",
            "Who else knows that you would %1?",
        ),
    ),
    (
        r"Is there (.*)",
        (
            "Do you think there is %1?",
            "It's likely that there is %1.",
            "Would you like there to be %1?",
        ),
    ),
    (
        r"My (.*)",
        (
            "I see, your %1.",
            "Why do you say that your %1?",
            "When your %1, how do you feel?",
        ),
    ),
    (
        r"You (.*)",
        (
            "We should be discussing you, not me.",
            "Why do you say that about me?",
            "Why do you care whether I %1?",
        ),
    ),
    (r"Why (.*)", ("Why don't you tell me the reason why %1?", "Why do you think %1?")),
    (
        r"I want (.*)",
        (
            "What would it mean to you if you got %1?",
            "Why do you want %1?",
            "What would you do if you got %1?",
            "If you got %1, then what would you do?",
        ),
    ),
    (
        r"(.*) mother(.*)",
        (
            "Tell me more about your mother.",
            "What was your relationship with your mother like?",
            "How do you feel about your mother?",
            "How does this relate to your feelings today?",
            "Good family relations are important.",
        ),
    ),
    (
        r"(.*) father(.*)",
        (
            "Tell me more about your father.",
            "How did your father make you feel?",
            "How do you feel about your father?",
            "Does your relationship with your father relate to your feelings today?",
            "Do you have trouble showing affection with your family?",
        ),
    ),
    (
        r"(.*) child(.*)",
        (
            "Did you have close friends as a child?",
            "What is your favorite childhood memory?",
            "Do you remember any dreams or nightmares from childhood?",
            "Did the other children sometimes tease you?",
            "How do you think your childhood experiences relate to your feelings today?",
        ),
    ),
    (
        r"(.*)\?",
        (
            "Why do you ask that?",
            "Please consider whether you can answer your own question.",
            "Perhaps the answer lies within yourself?",
            "Why don't you tell me?",
        ),
    ),
    (
        r"quit",
        (
            "Thank you for talking with me.",
            "Good-bye.",
            "Thank you, that will be $150.  Have a good day!",
        ),
    ),
    (
        r"(.*)",
        (
            "Please tell me more.",
            "Let's change focus a bit... Tell me about your family.",
            "Can you elaborate on that?",
            "Why do you say that %1?",
            "I see.",
            "Very interesting.",
            "%1.",
            "I see.  And what does that tell you?",
            "How does that make you feel?",
            "How do you feel when you say that?",
        ),
    ),
)

eliza_chatbot = Chat(pairs, reflections)


def eliza_chat():
    print("Therapist\n---------")
    print("Talk to the program by typing in plain English, using normal upper-")
    print('and lower-case letters and punctuation.  Enter "quit" when done.')
    print("=" * 72)
    print("Hello.  How are you feeling today?")

    eliza_chatbot.converse()


def demo():
    eliza_chat()


if __name__ == "__main__":
    eliza_chat()

# === NexusCore/openenv\Lib\site-packages\nltk\tree\transforms.py ===
# Natural Language Toolkit: Tree Transformations
#
# Copyright (C) 2005-2007 Oregon Graduate Institute
# Author: Nathan Bodenstab <bodenstab@cslu.ogi.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
A collection of methods for tree (grammar) transformations used
in parsing natural language.

Although many of these methods are technically grammar transformations
(ie. Chomsky Norm Form), when working with treebanks it is much more
natural to visualize these modifications in a tree structure.  Hence,
we will do all transformation directly to the tree itself.
Transforming the tree directly also allows us to do parent annotation.
A grammar can then be simply induced from the modified tree.

The following is a short tutorial on the available transformations.

 1. Chomsky Normal Form (binarization)

    It is well known that any grammar has a Chomsky Normal Form (CNF)
    equivalent grammar where CNF is defined by every production having
    either two non-terminals or one terminal on its right hand side.
    When we have hierarchically structured data (ie. a treebank), it is
    natural to view this in terms of productions where the root of every
    subtree is the head (left hand side) of the production and all of
    its children are the right hand side constituents.  In order to
    convert a tree into CNF, we simply need to ensure that every subtree
    has either two subtrees as children (binarization), or one leaf node
    (non-terminal).  In order to binarize a subtree with more than two
    children, we must introduce artificial nodes.

    There are two popular methods to convert a tree into CNF: left
    factoring and right factoring.  The following example demonstrates
    the difference between them.  Example::

     Original       Right-Factored     Left-Factored

          A              A                      A
        / | \          /   \                  /   \
       B  C  D   ==>  B    A|<C-D>   OR   A|<B-C>  D
                            /  \          /  \
                           C    D        B    C

 2. Parent Annotation

    In addition to binarizing the tree, there are two standard
    modifications to node labels we can do in the same traversal: parent
    annotation and Markov order-N smoothing (or sibling smoothing).

    The purpose of parent annotation is to refine the probabilities of
    productions by adding a small amount of context.  With this simple
    addition, a CYK (inside-outside, dynamic programming chart parse)
    can improve from 74% to 79% accuracy.  A natural generalization from
    parent annotation is to grandparent annotation and beyond.  The
    tradeoff becomes accuracy gain vs. computational complexity.  We
    must also keep in mind data sparcity issues.  Example::

     Original       Parent Annotation

          A                A^<?>
        / | \             /   \
       B  C  D   ==>  B^<A>    A|<C-D>^<?>     where ? is the
                                 /  \          parent of A
                             C^<A>   D^<A>


 3. Markov order-N smoothing

    Markov smoothing combats data sparcity issues as well as decreasing
    computational requirements by limiting the number of children
    included in artificial nodes.  In practice, most people use an order
    2 grammar.  Example::

      Original       No Smoothing       Markov order 1   Markov order 2   etc.

       __A__            A                      A                A
      / /|\ \         /   \                  /   \            /   \
     B C D E F  ==>  B    A|<C-D-E-F>  ==>  B   A|<C>  ==>   B  A|<C-D>
                            /   \               /   \            /   \
                           C    ...            C    ...         C    ...



    Annotation decisions can be thought about in the vertical direction
    (parent, grandparent, etc) and the horizontal direction (number of
    siblings to keep).  Parameters to the following functions specify
    these values.  For more information see:

    Dan Klein and Chris Manning (2003) "Accurate Unlexicalized
    Parsing", ACL-03.  https://www.aclweb.org/anthology/P03-1054

 4. Unary Collapsing

    Collapse unary productions (ie. subtrees with a single child) into a
    new non-terminal (Tree node).  This is useful when working with
    algorithms that do not allow unary productions, yet you do not wish
    to lose the parent information.  Example::

       A
       |
       B   ==>   A+B
      / \        / \
     C   D      C   D

"""

from nltk.tree.tree import Tree


def chomsky_normal_form(
    tree, factor="right", horzMarkov=None, vertMarkov=0, childChar="|", parentChar="^"
):
    # assume all subtrees have homogeneous children
    # assume all terminals have no siblings

    # A semi-hack to have elegant looking code below.  As a result,
    # any subtree with a branching factor greater than 999 will be incorrectly truncated.
    if horzMarkov is None:
        horzMarkov = 999

    # Traverse the tree depth-first keeping a list of ancestor nodes to the root.
    # I chose not to use the tree.treepositions() method since it requires
    # two traversals of the tree (one to get the positions, one to iterate
    # over them) and node access time is proportional to the height of the node.
    # This method is 7x faster which helps when parsing 40,000 sentences.

    nodeList = [(tree, [tree.label()])]
    while nodeList != []:
        node, parent = nodeList.pop()
        if isinstance(node, Tree):
            # parent annotation
            parentString = ""
            originalNode = node.label()
            if vertMarkov != 0 and node != tree and isinstance(node[0], Tree):
                parentString = "{}<{}>".format(parentChar, "-".join(parent))
                node.set_label(node.label() + parentString)
                parent = [originalNode] + parent[: vertMarkov - 1]

            # add children to the agenda before we mess with them
            for child in node:
                nodeList.append((child, parent))

            # chomsky normal form factorization
            if len(node) > 2:
                childNodes = [child.label() for child in node]
                nodeCopy = node.copy()
                node[0:] = []  # delete the children

                curNode = node
                numChildren = len(nodeCopy)
                for i in range(1, numChildren - 1):
                    if factor == "right":
                        newHead = "{}{}<{}>{}".format(
                            originalNode,
                            childChar,
                            "-".join(
                                childNodes[i : min([i + horzMarkov, numChildren])]
                            ),
                            parentString,
                        )  # create new head
                        newNode = Tree(newHead, [])
                        curNode[0:] = [nodeCopy.pop(0), newNode]
                    else:
                        newHead = "{}{}<{}>{}".format(
                            originalNode,
                            childChar,
                            "-".join(
                                childNodes[max([numChildren - i - horzMarkov, 0]) : -i]
                            ),
                            parentString,
                        )
                        newNode = Tree(newHead, [])
                        curNode[0:] = [newNode, nodeCopy.pop()]

                    curNode = newNode

                curNode[0:] = [child for child in nodeCopy]


def un_chomsky_normal_form(
    tree, expandUnary=True, childChar="|", parentChar="^", unaryChar="+"
):
    # Traverse the tree-depth first keeping a pointer to the parent for modification purposes.
    nodeList = [(tree, [])]
    while nodeList != []:
        node, parent = nodeList.pop()
        if isinstance(node, Tree):
            # if the node contains the 'childChar' character it means that
            # it is an artificial node and can be removed, although we still need
            # to move its children to its parent
            childIndex = node.label().find(childChar)
            if childIndex != -1:
                nodeIndex = parent.index(node)
                parent.remove(parent[nodeIndex])
                # Generated node was on the left if the nodeIndex is 0 which
                # means the grammar was left factored.  We must insert the children
                # at the beginning of the parent's children
                if nodeIndex == 0:
                    parent.insert(0, node[0])
                    parent.insert(1, node[1])
                else:
                    parent.extend([node[0], node[1]])

                # parent is now the current node so the children of parent will be added to the agenda
                node = parent
            else:
                parentIndex = node.label().find(parentChar)
                if parentIndex != -1:
                    # strip the node name of the parent annotation
                    node.set_label(node.label()[:parentIndex])

                # expand collapsed unary productions
                if expandUnary == True:
                    unaryIndex = node.label().find(unaryChar)
                    if unaryIndex != -1:
                        newNode = Tree(
                            node.label()[unaryIndex + 1 :], [i for i in node]
                        )
                        node.set_label(node.label()[:unaryIndex])
                        node[0:] = [newNode]

            for child in node:
                nodeList.append((child, node))


def collapse_unary(tree, collapsePOS=False, collapseRoot=False, joinChar="+"):
    """
    Collapse subtrees with a single child (ie. unary productions)
    into a new non-terminal (Tree node) joined by 'joinChar'.
    This is useful when working with algorithms that do not allow
    unary productions, and completely removing the unary productions
    would require loss of useful information.  The Tree is modified
    directly (since it is passed by reference) and no value is returned.

    :param tree: The Tree to be collapsed
    :type  tree: Tree
    :param collapsePOS: 'False' (default) will not collapse the parent of leaf nodes (ie.
                        Part-of-Speech tags) since they are always unary productions
    :type  collapsePOS: bool
    :param collapseRoot: 'False' (default) will not modify the root production
                         if it is unary.  For the Penn WSJ treebank corpus, this corresponds
                         to the TOP -> productions.
    :type collapseRoot: bool
    :param joinChar: A string used to connect collapsed node values (default = "+")
    :type  joinChar: str
    """

    if collapseRoot == False and isinstance(tree, Tree) and len(tree) == 1:
        nodeList = [tree[0]]
    else:
        nodeList = [tree]

    # depth-first traversal of tree
    while nodeList != []:
        node = nodeList.pop()
        if isinstance(node, Tree):
            if (
                len(node) == 1
                and isinstance(node[0], Tree)
                and (collapsePOS == True or isinstance(node[0, 0], Tree))
            ):
                node.set_label(node.label() + joinChar + node[0].label())
                node[0:] = [child for child in node[0]]
                # since we assigned the child's children to the current node,
                # evaluate the current node again
                nodeList.append(node)
            else:
                for child in node:
                    nodeList.append(child)


#################################################################
# Demonstration
#################################################################


def demo():
    """
    A demonstration showing how each tree transform can be used.
    """

    from copy import deepcopy

    from nltk.draw.tree import draw_trees
    from nltk.tree.tree import Tree

    # original tree from WSJ bracketed text
    sentence = """(TOP
  (S
    (S
      (VP
        (VBN Turned)
        (ADVP (RB loose))
        (PP
          (IN in)
          (NP
            (NP (NNP Shane) (NNP Longman) (POS 's))
            (NN trading)
            (NN room)))))
    (, ,)
    (NP (DT the) (NN yuppie) (NNS dealers))
    (VP (AUX do) (NP (NP (RB little)) (ADJP (RB right))))
    (. .)))"""
    t = Tree.fromstring(sentence, remove_empty_top_bracketing=True)

    # collapse subtrees with only one child
    collapsedTree = deepcopy(t)
    collapse_unary(collapsedTree)

    # convert the tree to CNF
    cnfTree = deepcopy(collapsedTree)
    chomsky_normal_form(cnfTree)

    # convert the tree to CNF with parent annotation (one level) and horizontal smoothing of order two
    parentTree = deepcopy(collapsedTree)
    chomsky_normal_form(parentTree, horzMarkov=2, vertMarkov=1)

    # convert the tree back to its original form (used to make CYK results comparable)
    original = deepcopy(parentTree)
    un_chomsky_normal_form(original)

    # convert tree back to bracketed text
    sentence2 = original.pprint()
    print(sentence)
    print(sentence2)
    print("Sentences the same? ", sentence == sentence2)

    draw_trees(t, collapsedTree, cnfTree, parentTree, original)


if __name__ == "__main__":
    demo()

__all__ = ["chomsky_normal_form", "un_chomsky_normal_form", "collapse_unary"]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\unpacking.py ===
"""Utilities related archives.
"""

import logging
import os
import shutil
import stat
import sys
import tarfile
import zipfile
from typing import Iterable, List, Optional
from zipfile import ZipInfo

from pip._internal.exceptions import InstallationError
from pip._internal.utils.filetypes import (
    BZ2_EXTENSIONS,
    TAR_EXTENSIONS,
    XZ_EXTENSIONS,
    ZIP_EXTENSIONS,
)
from pip._internal.utils.misc import ensure_dir

logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = ZIP_EXTENSIONS + TAR_EXTENSIONS

try:
    import bz2  # noqa

    SUPPORTED_EXTENSIONS += BZ2_EXTENSIONS
except ImportError:
    logger.debug("bz2 module is not available")

try:
    # Only for Python 3.3+
    import lzma  # noqa

    SUPPORTED_EXTENSIONS += XZ_EXTENSIONS
except ImportError:
    logger.debug("lzma module is not available")


def current_umask() -> int:
    """Get the current umask which involves having to set it temporarily."""
    mask = os.umask(0)
    os.umask(mask)
    return mask


def split_leading_dir(path: str) -> List[str]:
    path = path.lstrip("/").lstrip("\\")
    if "/" in path and (
        ("\\" in path and path.find("/") < path.find("\\")) or "\\" not in path
    ):
        return path.split("/", 1)
    elif "\\" in path:
        return path.split("\\", 1)
    else:
        return [path, ""]


def has_leading_dir(paths: Iterable[str]) -> bool:
    """Returns true if all the paths have the same leading path name
    (i.e., everything is in one subdirectory in an archive)"""
    common_prefix = None
    for path in paths:
        prefix, rest = split_leading_dir(path)
        if not prefix:
            return False
        elif common_prefix is None:
            common_prefix = prefix
        elif prefix != common_prefix:
            return False
    return True


def is_within_directory(directory: str, target: str) -> bool:
    """
    Return true if the absolute path of target is within the directory
    """
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])
    return prefix == abs_directory


def _get_default_mode_plus_executable() -> int:
    return 0o777 & ~current_umask() | 0o111


def set_extracted_file_to_default_mode_plus_executable(path: str) -> None:
    """
    Make file present at path have execute for user/group/world
    (chmod +x) is no-op on windows per python docs
    """
    os.chmod(path, _get_default_mode_plus_executable())


def zip_item_is_executable(info: ZipInfo) -> bool:
    mode = info.external_attr >> 16
    # if mode and regular file and any execute permissions for
    # user/group/world?
    return bool(mode and stat.S_ISREG(mode) and mode & 0o111)


def unzip_file(filename: str, location: str, flatten: bool = True) -> None:
    """
    Unzip the file (with path `filename`) to the destination `location`.  All
    files are written based on system defaults and umask (i.e. permissions are
    not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written. Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    zipfp = open(filename, "rb")
    try:
        zip = zipfile.ZipFile(zipfp, allowZip64=True)
        leading = has_leading_dir(zip.namelist()) and flatten
        for info in zip.infolist():
            name = info.filename
            fn = name
            if leading:
                fn = split_leading_dir(name)[1]
            fn = os.path.join(location, fn)
            dir = os.path.dirname(fn)
            if not is_within_directory(location, fn):
                message = (
                    "The zip file ({}) has a file ({}) trying to install "
                    "outside target directory ({})"
                )
                raise InstallationError(message.format(filename, fn, location))
            if fn.endswith("/") or fn.endswith("\\"):
                # A directory
                ensure_dir(fn)
            else:
                ensure_dir(dir)
                # Don't use read() to avoid allocating an arbitrarily large
                # chunk of memory for the file's content
                fp = zip.open(name)
                try:
                    with open(fn, "wb") as destfp:
                        shutil.copyfileobj(fp, destfp)
                finally:
                    fp.close()
                    if zip_item_is_executable(info):
                        set_extracted_file_to_default_mode_plus_executable(fn)
    finally:
        zipfp.close()


def untar_file(filename: str, location: str) -> None:
    """
    Untar the file (with path `filename`) to the destination `location`.
    All files are written based on system defaults and umask (i.e. permissions
    are not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied on top of the
    default.  Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    if filename.lower().endswith(".gz") or filename.lower().endswith(".tgz"):
        mode = "r:gz"
    elif filename.lower().endswith(BZ2_EXTENSIONS):
        mode = "r:bz2"
    elif filename.lower().endswith(XZ_EXTENSIONS):
        mode = "r:xz"
    elif filename.lower().endswith(".tar"):
        mode = "r"
    else:
        logger.warning(
            "Cannot determine compression type for file %s",
            filename,
        )
        mode = "r:*"

    tar = tarfile.open(filename, mode, encoding="utf-8")  # type: ignore
    try:
        leading = has_leading_dir([member.name for member in tar.getmembers()])

        # PEP 706 added `tarfile.data_filter`, and made some other changes to
        # Python's tarfile module (see below). The features were backported to
        # security releases.
        try:
            data_filter = tarfile.data_filter
        except AttributeError:
            _untar_without_filter(filename, location, tar, leading)
        else:
            default_mode_plus_executable = _get_default_mode_plus_executable()

            if leading:
                # Strip the leading directory from all files in the archive,
                # including hardlink targets (which are relative to the
                # unpack location).
                for member in tar.getmembers():
                    name_lead, name_rest = split_leading_dir(member.name)
                    member.name = name_rest
                    if member.islnk():
                        lnk_lead, lnk_rest = split_leading_dir(member.linkname)
                        if lnk_lead == name_lead:
                            member.linkname = lnk_rest

            def pip_filter(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo:
                orig_mode = member.mode
                try:
                    try:
                        member = data_filter(member, location)
                    except tarfile.LinkOutsideDestinationError:
                        if sys.version_info[:3] in {
                            (3, 8, 17),
                            (3, 9, 17),
                            (3, 10, 12),
                            (3, 11, 4),
                        }:
                            # The tarfile filter in specific Python versions
                            # raises LinkOutsideDestinationError on valid input
                            # (https://github.com/python/cpython/issues/107845)
                            # Ignore the error there, but do use the
                            # more lax `tar_filter`
                            member = tarfile.tar_filter(member, location)
                        else:
                            raise
                except tarfile.TarError as exc:
                    message = "Invalid member in the tar file {}: {}"
                    # Filter error messages mention the member name.
                    # No need to add it here.
                    raise InstallationError(
                        message.format(
                            filename,
                            exc,
                        )
                    )
                if member.isfile() and orig_mode & 0o111:
                    member.mode = default_mode_plus_executable
                else:
                    # See PEP 706 note above.
                    # The PEP changed this from `int` to `Optional[int]`,
                    # where None means "use the default". Mypy doesn't
                    # know this yet.
                    member.mode = None  # type: ignore [assignment]
                return member

            tar.extractall(location, filter=pip_filter)

    finally:
        tar.close()


def _untar_without_filter(
    filename: str,
    location: str,
    tar: tarfile.TarFile,
    leading: bool,
) -> None:
    """Fallback for Python without tarfile.data_filter"""
    for member in tar.getmembers():
        fn = member.name
        if leading:
            fn = split_leading_dir(fn)[1]
        path = os.path.join(location, fn)
        if not is_within_directory(location, path):
            message = (
                "The tar file ({}) has a file ({}) trying to install "
                "outside target directory ({})"
            )
            raise InstallationError(message.format(filename, path, location))
        if member.isdir():
            ensure_dir(path)
        elif member.issym():
            try:
                tar._extract_member(member, path)
            except Exception as exc:
                # Some corrupt tar files seem to produce this
                # (specifically bad symlinks)
                logger.warning(
                    "In the tar file %s the member %s is invalid: %s",
                    filename,
                    member.name,
                    exc,
                )
                continue
        else:
            try:
                fp = tar.extractfile(member)
            except (KeyError, AttributeError) as exc:
                # Some corrupt tar files seem to produce this
                # (specifically bad symlinks)
                logger.warning(
                    "In the tar file %s the member %s is invalid: %s",
                    filename,
                    member.name,
                    exc,
                )
                continue
            ensure_dir(os.path.dirname(path))
            assert fp is not None
            with open(path, "wb") as destfp:
                shutil.copyfileobj(fp, destfp)
            fp.close()
            # Update the timestamp (useful for cython compiled files)
            tar.utime(member, path)
            # member have any execute permissions for user/group/world?
            if member.mode & 0o111:
                set_extracted_file_to_default_mode_plus_executable(path)


def unpack_file(
    filename: str,
    location: str,
    content_type: Optional[str] = None,
) -> None:
    filename = os.path.realpath(filename)
    if (
        content_type == "application/zip"
        or filename.lower().endswith(ZIP_EXTENSIONS)
        or zipfile.is_zipfile(filename)
    ):
        unzip_file(filename, location, flatten=not filename.endswith(".whl"))
    elif (
        content_type == "application/x-gzip"
        or tarfile.is_tarfile(filename)
        or filename.lower().endswith(TAR_EXTENSIONS + BZ2_EXTENSIONS + XZ_EXTENSIONS)
    ):
        untar_file(filename, location)
    else:
        # FIXME: handle?
        # FIXME: magic signatures?
        logger.critical(
            "Cannot unpack file %s (downloaded from %s, content-type: %s); "
            "cannot detect archive format",
            filename,
            location,
            content_type,
        )
        raise InstallationError(f"Cannot determine archive format of {location}")

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_asyncgen.py ===
from __future__ import annotations

import contextlib
import sys
import weakref
from math import inf
from types import AsyncGeneratorType
from typing import TYPE_CHECKING, NoReturn

import pytest

from ... import _core
from .tutil import gc_collect_harder, restore_unraisablehook

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def test_asyncgen_basics() -> None:
    collected = []

    async def example(cause: str) -> AsyncGenerator[int, None]:
        try:
            with contextlib.suppress(GeneratorExit):
                yield 42
            await _core.checkpoint()
        except _core.Cancelled:
            assert "exhausted" not in cause
            task_name = _core.current_task().name
            assert cause in task_name or task_name == "<init>"
            assert _core.current_effective_deadline() == -inf
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            collected.append(cause)
        else:
            assert "async_main" in _core.current_task().name
            assert "exhausted" in cause
            assert _core.current_effective_deadline() == inf
            await _core.checkpoint()
            collected.append(cause)

    saved = []

    async def async_main() -> None:
        # GC'ed before exhausted
        with pytest.warns(  # noqa: PT031
            ResourceWarning,
            match="Async generator.*collected before.*exhausted",
        ):
            assert await example("abandoned").asend(None) == 42
            gc_collect_harder()
        await _core.wait_all_tasks_blocked()
        assert collected.pop() == "abandoned"

        aiter_ = example("exhausted 1")
        try:
            assert await aiter_.asend(None) == 42
        finally:
            await aiter_.aclose()
        assert collected.pop() == "exhausted 1"

        # Also fine if you exhaust it at point of use
        async for val in example("exhausted 2"):
            assert val == 42
        assert collected.pop() == "exhausted 2"

        gc_collect_harder()

        # No problems saving the geniter when using either of these patterns
        aiter_ = example("exhausted 3")
        try:
            saved.append(aiter_)
            assert await aiter_.asend(None) == 42
        finally:
            await aiter_.aclose()
        assert collected.pop() == "exhausted 3"

        # Also fine if you exhaust it at point of use
        saved.append(example("exhausted 4"))
        async for val in saved[-1]:
            assert val == 42
        assert collected.pop() == "exhausted 4"

        # Leave one referenced-but-unexhausted and make sure it gets cleaned up
        saved.append(example("outlived run"))
        assert await saved[-1].asend(None) == 42
        assert collected == []

    _core.run(async_main)
    assert collected.pop() == "outlived run"
    for agen in saved:
        assert isinstance(agen, AsyncGeneratorType)
        assert agen.ag_frame is None  # all should now be exhausted


async def test_asyncgen_throws_during_finalization(
    caplog: pytest.LogCaptureFixture,
) -> None:
    record = []

    async def agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            await _core.cancel_shielded_checkpoint()
            record.append("crashing")
            raise ValueError("oops")

    with restore_unraisablehook():
        await agen().asend(None)
        gc_collect_harder()
    await _core.wait_all_tasks_blocked()
    assert record == ["crashing"]
    # Following type ignore is because typing for LogCaptureFixture is wrong
    exc_type, exc_value, _exc_traceback = caplog.records[0].exc_info  # type: ignore[misc]
    assert exc_type is ValueError
    assert str(exc_value) == "oops"
    assert "during finalization of async generator" in caplog.records[0].message


def test_firstiter_after_closing() -> None:
    saved = []
    record = []

    async def funky_agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except GeneratorExit:
            record.append("cleanup 1")
            raise
        try:
            yield 2
        finally:
            record.append("cleanup 2")
            await funky_agen().asend(None)

    async def async_main() -> None:
        aiter_ = funky_agen()
        saved.append(aiter_)
        assert await aiter_.asend(None) == 1
        assert await aiter_.asend(None) == 2

    _core.run(async_main)
    assert record == ["cleanup 2", "cleanup 1"]


def test_interdependent_asyncgen_cleanup_order() -> None:
    saved: list[AsyncGenerator[int, None]] = []
    record: list[int | str] = []

    async def innermost() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            await _core.cancel_shielded_checkpoint()
            record.append("innermost")

    async def agen(
        label: int,
        inner: AsyncGenerator[int, None],
    ) -> AsyncGenerator[int, None]:
        try:
            yield await inner.asend(None)
        finally:
            # Either `inner` has already been cleaned up, or
            # we're about to exhaust it. Either way, we wind
            # up with `record` containing the labels in
            # innermost-to-outermost order.
            with pytest.raises(StopAsyncIteration):
                await inner.asend(None)
            record.append(label)

    async def async_main() -> None:
        # This makes a chain of 101 interdependent asyncgens:
        # agen(99)'s cleanup will iterate agen(98)'s will iterate
        # ... agen(0)'s will iterate innermost()'s
        ag_chain = innermost()
        for idx in range(100):
            ag_chain = agen(idx, ag_chain)
        saved.append(ag_chain)
        assert await ag_chain.asend(None) == 1
        assert record == []

    _core.run(async_main)
    assert record == ["innermost", *range(100)]


@restore_unraisablehook()
def test_last_minute_gc_edge_case() -> None:
    saved: list[AsyncGenerator[int, None]] = []
    record = []
    needs_retry = True

    async def agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            record.append("cleaned up")

    def collect_at_opportune_moment(token: _core._entry_queue.TrioToken) -> None:
        runner = _core._run.GLOBAL_RUN_CONTEXT.runner
        assert runner.system_nursery is not None
        if runner.system_nursery._closed and isinstance(
            runner.asyncgens.alive,
            weakref.WeakSet,
        ):
            saved.clear()
            record.append("final collection")
            gc_collect_harder()
            record.append("done")
        else:
            try:
                token.run_sync_soon(collect_at_opportune_moment, token)
            except _core.RunFinishedError:  # pragma: no cover
                nonlocal needs_retry
                needs_retry = True

    async def async_main() -> None:
        token = _core.current_trio_token()
        token.run_sync_soon(collect_at_opportune_moment, token)
        saved.append(agen())
        await saved[-1].asend(None)

    # Actually running into the edge case requires that the run_sync_soon task
    # execute in between the system nursery's closure and the strong-ification
    # of runner.asyncgens. There's about a 25% chance that it doesn't
    # (if the run_sync_soon task runs before init on one tick and after init
    # on the next tick); if we try enough times, we can make the chance of
    # failure as small as we want.
    for _attempt in range(50):
        needs_retry = False
        record.clear()
        saved.clear()
        _core.run(async_main)
        if needs_retry:  # pragma: no cover
            assert record == ["cleaned up"]
        else:
            assert record == ["final collection", "done", "cleaned up"]
            break
    else:  # pragma: no cover
        pytest.fail(
            "Didn't manage to hit the trailing_finalizer_asyncgens case "
            f"despite trying {_attempt} times",
        )


async def step_outside_async_context(aiter_: AsyncGenerator[int, None]) -> None:
    # abort_fns run outside of task context, at least if they're
    # triggered by a deadline expiry rather than a direct
    # cancellation.  Thus, an asyncgen first iterated inside one
    # will appear non-Trio, and since no other hooks were installed,
    # will use the last-ditch fallback handling (that tries to mimic
    # CPython's behavior with no hooks).
    #
    # NB: the strangeness with aiter being an attribute of abort_fn is
    # to make it as easy as possible to ensure we don't hang onto a
    # reference to aiter inside the guts of the run loop.
    def abort_fn(_: _core.RaiseCancelT) -> _core.Abort:
        with pytest.raises(StopIteration, match="42"):
            abort_fn.aiter.asend(None).send(None)  # type: ignore[attr-defined]  # Callables don't have attribute "aiter"
        del abort_fn.aiter  # type: ignore[attr-defined]
        return _core.Abort.SUCCEEDED

    abort_fn.aiter = aiter_  # type: ignore[attr-defined]

    async with _core.open_nursery() as nursery:
        nursery.start_soon(_core.wait_task_rescheduled, abort_fn)
        await _core.wait_all_tasks_blocked()
        nursery.cancel_scope.deadline = _core.current_time()


async def test_fallback_when_no_hook_claims_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def well_behaved() -> AsyncGenerator[int, None]:
        yield 42

    async def yields_after_yield() -> AsyncGenerator[int, None]:
        with pytest.raises(GeneratorExit):
            yield 42
        yield 100

    async def awaits_after_yield() -> AsyncGenerator[int, None]:
        with pytest.raises(GeneratorExit):
            yield 42
        await _core.cancel_shielded_checkpoint()

    with restore_unraisablehook():
        await step_outside_async_context(well_behaved())
        gc_collect_harder()
        assert capsys.readouterr().err == ""

        await step_outside_async_context(yields_after_yield())
        gc_collect_harder()
        assert "ignored GeneratorExit" in capsys.readouterr().err

        await step_outside_async_context(awaits_after_yield())
        gc_collect_harder()
        assert "awaited something during finalization" in capsys.readouterr().err


def test_delegation_to_existing_hooks() -> None:
    record = []

    def my_firstiter(agen: AsyncGenerator[object, NoReturn]) -> None:
        assert isinstance(agen, AsyncGeneratorType)
        record.append("firstiter " + agen.ag_frame.f_locals["arg"])

    def my_finalizer(agen: AsyncGenerator[object, NoReturn]) -> None:
        assert isinstance(agen, AsyncGeneratorType)
        record.append("finalizer " + agen.ag_frame.f_locals["arg"])

    async def example(arg: str) -> AsyncGenerator[int, None]:
        try:
            yield 42
        finally:
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            record.append("trio collected " + arg)

    async def async_main() -> None:
        await step_outside_async_context(example("theirs"))
        assert await example("ours").asend(None) == 42
        gc_collect_harder()
        assert record == ["firstiter theirs", "finalizer theirs"]
        record[:] = []
        await _core.wait_all_tasks_blocked()
        assert record == ["trio collected ours"]

    with restore_unraisablehook():
        old_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(my_firstiter, my_finalizer)
        try:
            _core.run(async_main)
        finally:
            assert sys.get_asyncgen_hooks() == (my_firstiter, my_finalizer)
            sys.set_asyncgen_hooks(*old_hooks)

# === NexusCore/openenv\Lib\site-packages\markdown_it\renderer.py ===
"""
class Renderer

Generates HTML from parsed token stream. Each instance has independent
copy of rules. Those can be rewritten with ease. Also, you can add new
rules if you create plugin and adds new token types.
"""
from __future__ import annotations

from collections.abc import Sequence
import inspect
from typing import Any, ClassVar, Protocol

from .common.utils import escapeHtml, unescapeAll
from .token import Token
from .utils import EnvType, OptionsDict


class RendererProtocol(Protocol):
    __output__: ClassVar[str]

    def render(
        self, tokens: Sequence[Token], options: OptionsDict, env: EnvType
    ) -> Any:
        ...


class RendererHTML(RendererProtocol):
    """Contains render rules for tokens. Can be updated and extended.

    Example:

    Each rule is called as independent static function with fixed signature:

    ::

        class Renderer:
            def token_type_name(self, tokens, idx, options, env) {
                # ...
                return renderedHTML

    ::

        class CustomRenderer(RendererHTML):
            def strong_open(self, tokens, idx, options, env):
                return '<b>'
            def strong_close(self, tokens, idx, options, env):
                return '</b>'

        md = MarkdownIt(renderer_cls=CustomRenderer)

        result = md.render(...)

    See https://github.com/markdown-it/markdown-it/blob/master/lib/renderer.js
    for more details and examples.
    """

    __output__ = "html"

    def __init__(self, parser: Any = None):
        self.rules = {
            k: v
            for k, v in inspect.getmembers(self, predicate=inspect.ismethod)
            if not (k.startswith("render") or k.startswith("_"))
        }

    def render(
        self, tokens: Sequence[Token], options: OptionsDict, env: EnvType
    ) -> str:
        """Takes token stream and generates HTML.

        :param tokens: list on block tokens to render
        :param options: params of parser instance
        :param env: additional data from parsed input

        """
        result = ""

        for i, token in enumerate(tokens):
            if token.type == "inline":
                if token.children:
                    result += self.renderInline(token.children, options, env)
            elif token.type in self.rules:
                result += self.rules[token.type](tokens, i, options, env)
            else:
                result += self.renderToken(tokens, i, options, env)

        return result

    def renderInline(
        self, tokens: Sequence[Token], options: OptionsDict, env: EnvType
    ) -> str:
        """The same as ``render``, but for single token of `inline` type.

        :param tokens: list on block tokens to render
        :param options: params of parser instance
        :param env: additional data from parsed input (references, for example)
        """
        result = ""

        for i, token in enumerate(tokens):
            if token.type in self.rules:
                result += self.rules[token.type](tokens, i, options, env)
            else:
                result += self.renderToken(tokens, i, options, env)

        return result

    def renderToken(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        """Default token renderer.

        Can be overridden by custom function

        :param idx: token index to render
        :param options: params of parser instance
        """
        result = ""
        needLf = False
        token = tokens[idx]

        # Tight list paragraphs
        if token.hidden:
            return ""

        # Insert a newline between hidden paragraph and subsequent opening
        # block-level tag.
        #
        # For example, here we should insert a newline before blockquote:
        #  - a
        #    >
        #
        if token.block and token.nesting != -1 and idx and tokens[idx - 1].hidden:
            result += "\n"

        # Add token name, e.g. `<img`
        result += ("</" if token.nesting == -1 else "<") + token.tag

        # Encode attributes, e.g. `<img src="foo"`
        result += self.renderAttrs(token)

        # Add a slash for self-closing tags, e.g. `<img src="foo" /`
        if token.nesting == 0 and options["xhtmlOut"]:
            result += " /"

        # Check if we need to add a newline after this tag
        if token.block:
            needLf = True

            if token.nesting == 1 and (idx + 1 < len(tokens)):
                nextToken = tokens[idx + 1]

                if nextToken.type == "inline" or nextToken.hidden:  # noqa: SIM114
                    # Block-level tag containing an inline tag.
                    #
                    needLf = False

                elif nextToken.nesting == -1 and nextToken.tag == token.tag:
                    # Opening tag + closing tag of the same type. E.g. `<li></li>`.
                    #
                    needLf = False

        result += ">\n" if needLf else ">"

        return result

    @staticmethod
    def renderAttrs(token: Token) -> str:
        """Render token attributes to string."""
        result = ""

        for key, value in token.attrItems():
            result += " " + escapeHtml(key) + '="' + escapeHtml(str(value)) + '"'

        return result

    def renderInlineAsText(
        self,
        tokens: Sequence[Token] | None,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        """Special kludge for image `alt` attributes to conform CommonMark spec.

        Don't try to use it! Spec requires to show `alt` content with stripped markup,
        instead of simple escaping.

        :param tokens: list on block tokens to render
        :param options: params of parser instance
        :param env: additional data from parsed input
        """
        result = ""

        for token in tokens or []:
            if token.type == "text":
                result += token.content
            elif token.type == "image":
                if token.children:
                    result += self.renderInlineAsText(token.children, options, env)
            elif token.type == "softbreak":
                result += "\n"

        return result

    ###################################################

    def code_inline(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        token = tokens[idx]
        return (
            "<code"
            + self.renderAttrs(token)
            + ">"
            + escapeHtml(tokens[idx].content)
            + "</code>"
        )

    def code_block(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        token = tokens[idx]

        return (
            "<pre"
            + self.renderAttrs(token)
            + "><code>"
            + escapeHtml(tokens[idx].content)
            + "</code></pre>\n"
        )

    def fence(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        token = tokens[idx]
        info = unescapeAll(token.info).strip() if token.info else ""
        langName = ""
        langAttrs = ""

        if info:
            arr = info.split(maxsplit=1)
            langName = arr[0]
            if len(arr) == 2:
                langAttrs = arr[1]

        if options.highlight:
            highlighted = options.highlight(
                token.content, langName, langAttrs
            ) or escapeHtml(token.content)
        else:
            highlighted = escapeHtml(token.content)

        if highlighted.startswith("<pre"):
            return highlighted + "\n"

        # If language exists, inject class gently, without modifying original token.
        # May be, one day we will add .deepClone() for token and simplify this part, but
        # now we prefer to keep things local.
        if info:
            # Fake token just to render attributes
            tmpToken = Token(type="", tag="", nesting=0, attrs=token.attrs.copy())
            tmpToken.attrJoin("class", options.langPrefix + langName)

            return (
                "<pre><code"
                + self.renderAttrs(tmpToken)
                + ">"
                + highlighted
                + "</code></pre>\n"
            )

        return (
            "<pre><code"
            + self.renderAttrs(token)
            + ">"
            + highlighted
            + "</code></pre>\n"
        )

    def image(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        token = tokens[idx]

        # "alt" attr MUST be set, even if empty. Because it's mandatory and
        # should be placed on proper position for tests.
        if token.children:
            token.attrSet("alt", self.renderInlineAsText(token.children, options, env))
        else:
            token.attrSet("alt", "")

        return self.renderToken(tokens, idx, options, env)

    def hardbreak(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return "<br />\n" if options.xhtmlOut else "<br>\n"

    def softbreak(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return (
            ("<br />\n" if options.xhtmlOut else "<br>\n") if options.breaks else "\n"
        )

    def text(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return escapeHtml(tokens[idx].content)

    def html_block(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return tokens[idx].content

    def html_inline(
        self, tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType
    ) -> str:
        return tokens[idx].content

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2634.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
# Modified by Russ Housley to add a map for use with opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Enhanced Security Services for S/MIME
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc2634.txt
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedval
from pyasn1.type import namedtype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5280

MAX = float('inf')

ContentType = rfc5652.ContentType

IssuerAndSerialNumber = rfc5652.IssuerAndSerialNumber

SubjectKeyIdentifier = rfc5652.SubjectKeyIdentifier

PolicyInformation = rfc5280.PolicyInformation

GeneralNames = rfc5280.GeneralNames

CertificateSerialNumber = rfc5280.CertificateSerialNumber


# Signing Certificate Attribute
# Warning: It is better to use SigningCertificateV2 from RFC 5035

id_aa_signingCertificate = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.12')

class Hash(univ.OctetString):
    pass  # SHA-1 hash of entire certificate; RFC 5035 supports other hash algorithms


class IssuerSerial(univ.Sequence):
    pass

IssuerSerial.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuer', GeneralNames()),
    namedtype.NamedType('serialNumber', CertificateSerialNumber())
)


class ESSCertID(univ.Sequence):
    pass

ESSCertID.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certHash', Hash()),
    namedtype.OptionalNamedType('issuerSerial', IssuerSerial())
)


class SigningCertificate(univ.Sequence):
    pass

SigningCertificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('certs', univ.SequenceOf(
        componentType=ESSCertID())),
    namedtype.OptionalNamedType('policies', univ.SequenceOf(
        componentType=PolicyInformation()))
)


# Mail List Expansion History Attribute

id_aa_mlExpandHistory = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.3')

ub_ml_expansion_history = univ.Integer(64)


class EntityIdentifier(univ.Choice):
    pass

EntityIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerAndSerialNumber', IssuerAndSerialNumber()),
    namedtype.NamedType('subjectKeyIdentifier', SubjectKeyIdentifier())
)


class MLReceiptPolicy(univ.Choice):
    pass

MLReceiptPolicy.componentType = namedtype.NamedTypes(
    namedtype.NamedType('none', univ.Null().subtype(implicitTag=tag.Tag(
        tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('insteadOf', univ.SequenceOf(
        componentType=GeneralNames()).subtype(
        sizeSpec=constraint.ValueSizeConstraint(1, MAX)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('inAdditionTo', univ.SequenceOf(
        componentType=GeneralNames()).subtype(
        sizeSpec=constraint.ValueSizeConstraint(1, MAX)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)


class MLData(univ.Sequence):
    pass

MLData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('mailListIdentifier', EntityIdentifier()),
    namedtype.NamedType('expansionTime', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('mlReceiptPolicy', MLReceiptPolicy())
)

class MLExpansionHistory(univ.SequenceOf):
    pass

MLExpansionHistory.componentType = MLData()
MLExpansionHistory.sizeSpec = constraint.ValueSizeConstraint(1, ub_ml_expansion_history)


# ESS Security Label Attribute

id_aa_securityLabel = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.2')

ub_privacy_mark_length = univ.Integer(128)

ub_security_categories = univ.Integer(64)

ub_integer_options = univ.Integer(256)


class ESSPrivacyMark(univ.Choice):
    pass

ESSPrivacyMark.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_privacy_mark_length))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
)


class SecurityClassification(univ.Integer):
    pass

SecurityClassification.subtypeSpec=constraint.ValueRangeConstraint(0, ub_integer_options)

SecurityClassification.namedValues = namedval.NamedValues(
    ('unmarked', 0),
    ('unclassified', 1),
    ('restricted', 2),
    ('confidential', 3),
    ('secret', 4),
    ('top-secret', 5)
)


class SecurityPolicyIdentifier(univ.ObjectIdentifier):
    pass


class SecurityCategory(univ.Sequence):
    pass

SecurityCategory.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('value', univ.Any().subtype(implicitTag=tag.Tag(
        tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class SecurityCategories(univ.SetOf):
    pass

SecurityCategories.componentType = SecurityCategory()
SecurityCategories.sizeSpec = constraint.ValueSizeConstraint(1, ub_security_categories)


class ESSSecurityLabel(univ.Set):
    pass

ESSSecurityLabel.componentType = namedtype.NamedTypes(
    namedtype.NamedType('security-policy-identifier', SecurityPolicyIdentifier()),
    namedtype.OptionalNamedType('security-classification', SecurityClassification()),
    namedtype.OptionalNamedType('privacy-mark', ESSPrivacyMark()),
    namedtype.OptionalNamedType('security-categories', SecurityCategories())
)


# Equivalent Labels Attribute

id_aa_equivalentLabels = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.9')

class EquivalentLabels(univ.SequenceOf):
    pass

EquivalentLabels.componentType = ESSSecurityLabel()


# Content Identifier Attribute

id_aa_contentIdentifier = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.7')

class ContentIdentifier(univ.OctetString):
    pass


# Content Reference Attribute

id_aa_contentReference = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.10')

class ContentReference(univ.Sequence):
    pass

ContentReference.componentType = namedtype.NamedTypes(
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('signedContentIdentifier', ContentIdentifier()),
    namedtype.NamedType('originatorSignatureValue', univ.OctetString())
)


# Message Signature Digest Attribute

id_aa_msgSigDigest = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.5')

class MsgSigDigest(univ.OctetString):
    pass


# Content Hints Attribute

id_aa_contentHint = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.4')

class ContentHints(univ.Sequence):
    pass

ContentHints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('contentDescription', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('contentType', ContentType())
)


# Receipt Request Attribute

class AllOrFirstTier(univ.Integer):
    pass

AllOrFirstTier.namedValues = namedval.NamedValues(
    ('allReceipts', 0),
    ('firstTierRecipients', 1)
)


class ReceiptsFrom(univ.Choice):
    pass

ReceiptsFrom.componentType = namedtype.NamedTypes(
    namedtype.NamedType('allOrFirstTier', AllOrFirstTier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('receiptList', univ.SequenceOf(
        componentType=GeneralNames()).subtype(implicitTag=tag.Tag(
        tag.tagClassContext, tag.tagFormatSimple, 1)))
)


id_aa_receiptRequest = univ.ObjectIdentifier('1.2.840.113549.1.9.16.2.1')

ub_receiptsTo = univ.Integer(16)

class ReceiptRequest(univ.Sequence):
    pass

ReceiptRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('signedContentIdentifier', ContentIdentifier()),
    namedtype.NamedType('receiptsFrom', ReceiptsFrom()),
    namedtype.NamedType('receiptsTo', univ.SequenceOf(componentType=GeneralNames()).subtype(sizeSpec=constraint.ValueSizeConstraint(1, ub_receiptsTo)))
)

# Receipt Content Type

class ESSVersion(univ.Integer):
    pass

ESSVersion.namedValues = namedval.NamedValues(
    ('v1', 1)
)


id_ct_receipt = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.1')

class Receipt(univ.Sequence):
    pass

Receipt.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version', ESSVersion()),
    namedtype.NamedType('contentType', ContentType()),
    namedtype.NamedType('signedContentIdentifier', ContentIdentifier()),
    namedtype.NamedType('originatorSignatureValue', univ.OctetString())
)


# Map of Attribute Type to the Attribute structure is added to the
# ones that are in rfc5652.py

_cmsAttributesMapUpdate = {
    id_aa_signingCertificate: SigningCertificate(),
    id_aa_mlExpandHistory: MLExpansionHistory(),
    id_aa_securityLabel: ESSSecurityLabel(),
    id_aa_equivalentLabels: EquivalentLabels(),
    id_aa_contentIdentifier: ContentIdentifier(),
    id_aa_contentReference: ContentReference(),
    id_aa_msgSigDigest: MsgSigDigest(),
    id_aa_contentHint: ContentHints(),
    id_aa_receiptRequest: ReceiptRequest(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)


# Map of Content Type OIDs to Content Types is added to the
# ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_ct_receipt: Receipt(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pycparser\_ast_gen.py ===
#-----------------------------------------------------------------
# _ast_gen.py
#
# Generates the AST Node classes from a specification given in
# a configuration file
#
# The design of this module was inspired by astgen.py from the
# Python 2.5 code-base.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------
from string import Template


class ASTCodeGenerator(object):
    def __init__(self, cfg_filename='_c_ast.cfg'):
        """ Initialize the code generator from a configuration
            file.
        """
        self.cfg_filename = cfg_filename
        self.node_cfg = [NodeCfg(name, contents)
            for (name, contents) in self.parse_cfgfile(cfg_filename)]

    def generate(self, file=None):
        """ Generates the code into file, an open file buffer.
        """
        src = Template(_PROLOGUE_COMMENT).substitute(
            cfg_filename=self.cfg_filename)

        src += _PROLOGUE_CODE
        for node_cfg in self.node_cfg:
            src += node_cfg.generate_source() + '\n\n'

        file.write(src)

    def parse_cfgfile(self, filename):
        """ Parse the configuration file and yield pairs of
            (name, contents) for each node.
        """
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                colon_i = line.find(':')
                lbracket_i = line.find('[')
                rbracket_i = line.find(']')
                if colon_i < 1 or lbracket_i <= colon_i or rbracket_i <= lbracket_i:
                    raise RuntimeError("Invalid line in %s:\n%s\n" % (filename, line))

                name = line[:colon_i]
                val = line[lbracket_i + 1:rbracket_i]
                vallist = [v.strip() for v in val.split(',')] if val else []
                yield name, vallist


class NodeCfg(object):
    """ Node configuration.

        name: node name
        contents: a list of contents - attributes and child nodes
        See comment at the top of the configuration file for details.
    """

    def __init__(self, name, contents):
        self.name = name
        self.all_entries = []
        self.attr = []
        self.child = []
        self.seq_child = []

        for entry in contents:
            clean_entry = entry.rstrip('*')
            self.all_entries.append(clean_entry)

            if entry.endswith('**'):
                self.seq_child.append(clean_entry)
            elif entry.endswith('*'):
                self.child.append(clean_entry)
            else:
                self.attr.append(entry)

    def generate_source(self):
        src = self._gen_init()
        src += '\n' + self._gen_children()
        src += '\n' + self._gen_iter()
        src += '\n' + self._gen_attr_names()
        return src

    def _gen_init(self):
        src = "class %s(Node):\n" % self.name

        if self.all_entries:
            args = ', '.join(self.all_entries)
            slots = ', '.join("'{0}'".format(e) for e in self.all_entries)
            slots += ", 'coord', '__weakref__'"
            arglist = '(self, %s, coord=None)' % args
        else:
            slots = "'coord', '__weakref__'"
            arglist = '(self, coord=None)'

        src += "    __slots__ = (%s)\n" % slots
        src += "    def __init__%s:\n" % arglist

        for name in self.all_entries + ['coord']:
            src += "        self.%s = %s\n" % (name, name)

        return src

    def _gen_children(self):
        src = '    def children(self):\n'

        if self.all_entries:
            src += '        nodelist = []\n'

            for child in self.child:
                src += (
                    '        if self.%(child)s is not None:' +
                    ' nodelist.append(("%(child)s", self.%(child)s))\n') % (
                        dict(child=child))

            for seq_child in self.seq_child:
                src += (
                    '        for i, child in enumerate(self.%(child)s or []):\n'
                    '            nodelist.append(("%(child)s[%%d]" %% i, child))\n') % (
                        dict(child=seq_child))

            src += '        return tuple(nodelist)\n'
        else:
            src += '        return ()\n'

        return src

    def _gen_iter(self):
        src = '    def __iter__(self):\n'

        if self.all_entries:
            for child in self.child:
                src += (
                    '        if self.%(child)s is not None:\n' +
                    '            yield self.%(child)s\n') % (dict(child=child))

            for seq_child in self.seq_child:
                src += (
                    '        for child in (self.%(child)s or []):\n'
                    '            yield child\n') % (dict(child=seq_child))

            if not (self.child or self.seq_child):
                # Empty generator
                src += (
                    '        return\n' +
                    '        yield\n')
        else:
            # Empty generator
            src += (
                '        return\n' +
                '        yield\n')

        return src

    def _gen_attr_names(self):
        src = "    attr_names = (" + ''.join("%r, " % nm for nm in self.attr) + ')'
        return src


_PROLOGUE_COMMENT = \
r'''#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# $cfg_filename
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# pycparser: c_ast.py
#
# AST Node classes.
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#-----------------------------------------------------------------

'''

_PROLOGUE_CODE = r'''
import sys

def _repr(obj):
    """
    Get the representation of an object, with dedicated pprint-like format for lists.
    """
    if isinstance(obj, list):
        return '[' + (',\n '.join((_repr(e).replace('\n', '\n ') for e in obj))) + '\n]'
    else:
        return repr(obj)

class Node(object):
    __slots__ = ()
    """ Abstract base class for AST nodes.
    """
    def __repr__(self):
        """ Generates a python representation of the current node
        """
        result = self.__class__.__name__ + '('

        indent = ''
        separator = ''
        for name in self.__slots__[:-2]:
            result += separator
            result += indent
            result += name + '=' + (_repr(getattr(self, name)).replace('\n', '\n  ' + (' ' * (len(name) + len(self.__class__.__name__)))))

            separator = ','
            indent = '\n ' + (' ' * len(self.__class__.__name__))

        result += indent + ')'

        return result

    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(self, buf=sys.stdout, offset=0, attrnames=False, nodenames=False, showcoord=False, _my_node_name=None):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.

            buf:
                Open IO buffer into which the Node is printed.

            offset:
                Initial offset (amount of leading spaces)

            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.

            nodenames:
                True if you want to see the actual node names
                within their parents.

            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__+ ' <' + _my_node_name + '>: ')
        else:
            buf.write(lead + self.__class__.__name__+ ': ')

        if self.attr_names:
            if attrnames:
                nvlist = [(n, getattr(self,n)) for n in self.attr_names]
                attrstr = ', '.join('%s=%s' % nv for nv in nvlist)
            else:
                vlist = [getattr(self, n) for n in self.attr_names]
                attrstr = ', '.join('%s' % v for v in vlist)
            buf.write(attrstr)

        if showcoord:
            buf.write(' (at %s)' % self.coord)
        buf.write('\n')

        for (child_name, child) in self.children():
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor(object):
    """ A base NodeVisitor class for visiting c_ast nodes.
        Subclass it and define your own visit_XXX methods, where
        XXX is the class name you want to visit with these
        methods.

        For example:

        class ConstantVisitor(NodeVisitor):
            def __init__(self):
                self.values = []

            def visit_Constant(self, node):
                self.values.append(node.value)

        Creates a list of values of all the constant nodes
        encountered below the given node. To use it:

        cv = ConstantVisitor()
        cv.visit(node)

        Notes:

        *   generic_visit() will be called for AST nodes for which
            no visit_XXX method was defined.
        *   The children of nodes for which a visit_XXX was
            defined will not be visited - if you need this, call
            generic_visit() on the node.
            You can use:
                NodeVisitor.generic_visit(self, node)
        *   Modeled after Python's own AST visiting facilities
            (the ast module of Python 3.0)
    """

    _method_cache = None

    def visit(self, node):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node)

    def generic_visit(self, node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """
        for c in node:
            self.visit(c)

'''

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\guardrails\guardrail_hooks\aim.py ===
# +-------------------------------------------------------------+
#
#           Use Aim Security Guardrails for your LLM calls
#                   https://www.aim.security/
#
# +-------------------------------------------------------------+
import asyncio
import json
import os
from typing import Any, AsyncGenerator, Literal, Optional, Union

from fastapi import HTTPException
from pydantic import BaseModel
from websockets.asyncio.client import ClientConnection, connect

from litellm import DualCache
from litellm._logging import verbose_proxy_logger
from litellm._version import version as litellm_version
from litellm.integrations.custom_guardrail import CustomGuardrail
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.proxy._types import UserAPIKeyAuth
from litellm.proxy.proxy_server import StreamingCallbackError
from litellm.types.utils import (
    Choices,
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    ModelResponseStream,
)


class AimGuardrailMissingSecrets(Exception):
    pass


class AimGuardrail(CustomGuardrail):
    def __init__(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None, **kwargs
    ):
        self.async_handler = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.GuardrailCallback
        )
        self.api_key = api_key or os.environ.get("AIM_API_KEY")
        if not self.api_key:
            msg = (
                "Couldn't get Aim api key, either set the `AIM_API_KEY` in the environment or "
                "pass it as a parameter to the guardrail in the config file"
            )
            raise AimGuardrailMissingSecrets(msg)
        self.api_base = (
            api_base or os.environ.get("AIM_API_BASE") or "https://api.aim.security"
        )
        self.ws_api_base = self.api_base.replace("http://", "ws://").replace(
            "https://", "wss://"
        )
        self.dlp_entities: list[dict] = []
        self._max_dlp_entities = 100
        super().__init__(**kwargs)

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank",
        ],
    ) -> Union[Exception, str, dict, None]:
        verbose_proxy_logger.debug("Inside AIM Pre-Call Hook")

        return await self.call_aim_guardrail(
            data, hook="pre_call", key_alias=user_api_key_dict.key_alias
        )

    async def async_moderation_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "responses",
        ],
    ) -> Union[Exception, str, dict, None]:
        verbose_proxy_logger.debug("Inside AIM Moderation Hook")

        await self.call_aim_guardrail(
            data, hook="moderation", key_alias=user_api_key_dict.key_alias
        )
        return data

    async def call_aim_guardrail(
        self, data: dict, hook: str, key_alias: Optional[str]
    ) -> dict:
        user_email = data.get("metadata", {}).get("headers", {}).get("x-aim-user-email")
        call_id = data.get("litellm_call_id")
        headers = self._build_aim_headers(
            hook=hook,
            key_alias=key_alias,
            user_email=user_email,
            litellm_call_id=call_id,
        )
        response = await self.async_handler.post(
            f"{self.api_base}/detect/openai/v2",
            headers=headers,
            json={"messages": data.get("messages", [])},
        )
        response.raise_for_status()
        res = response.json()
        required_action = res.get("required_action")
        action_type = required_action and required_action.get("action_type", None)
        if action_type is None:
            verbose_proxy_logger.debug("Aim: No required action specified")
            return data
        if action_type == "monitor_action":
            verbose_proxy_logger.info("Aim: monitor action")
        elif action_type == "block_action":
            self._handle_block_action(res["analysis_result"], required_action)
        elif action_type == "anonymize_action":
            return self._anonymize_request(
                res["analysis_result"], required_action, data
            )
        else:
            verbose_proxy_logger.error(f"Aim: {action_type} action")
        return data

    def _handle_block_action(self, analysis_result: Any, required_action: Any) -> None:
        detection_message = required_action.get("detection_message", None)
        verbose_proxy_logger.info(
            "Aim: Violation detected enabled policies: {policies}".format(
                policies=list(analysis_result["policy_drill_down"].keys()),
            ),
        )
        raise HTTPException(status_code=400, detail=detection_message)

    def _anonymize_request(
        self, analysis_result: Any, required_action: Any, data: dict
    ) -> dict:
        verbose_proxy_logger.info("Aim: anonymize action")
        redaction_result = required_action and required_action.get(
            "chat_redaction_result"
        )
        if not redaction_result:
            return data
        if analysis_result and analysis_result.get("session_entities"):
            self._set_dlp_entities(analysis_result.get("session_entities"))
        data["messages"] = [
            {
                "role": redaction_result["redacted_new_message"]["role"],
                "content": redaction_result["redacted_new_message"]["content"],
            }
        ] + [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in redaction_result["all_redacted_messages"]
        ]
        return data

    async def call_aim_guardrail_on_output(
        self, request_data: dict, output: str, hook: str, key_alias: Optional[str]
    ) -> Optional[dict]:
        user_email = (
            request_data.get("metadata", {}).get("headers", {}).get("x-aim-user-email")
        )
        call_id = request_data.get("litellm_call_id")
        response = await self.async_handler.post(
            f"{self.api_base}/detect/output/v2",
            headers=self._build_aim_headers(
                hook=hook,
                key_alias=key_alias,
                user_email=user_email,
                litellm_call_id=call_id,
            ),
            json={"output": output, "messages": request_data.get("messages", [])},
        )
        response.raise_for_status()
        res = response.json()
        required_action = res.get("required_action")
        action_type = required_action and required_action.get("action_type", None)
        if action_type and action_type == "block_action":
            return self._handle_block_action_on_output(
                res["analysis_result"], required_action
            )
        return self._deanonymize_output(output)

    def _handle_block_action_on_output(
        self, analysis_result: Any, required_action: Any
    ) -> dict | None:
        detection_message = required_action.get("detection_message", None)
        verbose_proxy_logger.info(
            "Aim: detected: {detected}, enabled policies: {policies}".format(
                detected=True,
                policies=list(analysis_result["policy_drill_down"].keys()),
            ),
        )
        return {"detection_message": detection_message}

    def _deanonymize_output(self, output: str) -> dict | None:
        try:
            for entity in self.dlp_entities:
                output = output.replace(f"[{entity['name']}]", entity["content"])
            return {"redacted_output": output}
        except Exception as e:
            verbose_proxy_logger.error(f"Aim: Error while redacting output: {e}")
            return None

    def _build_aim_headers(
        self,
        *,
        hook: str,
        key_alias: Optional[str],
        user_email: Optional[str],
        litellm_call_id: Optional[str],
    ):
        """
        A helper function to build the http headers that are required by AIM guardrails.
        """
        return (
            {
                "Authorization": f"Bearer {self.api_key}",
                # Used by Aim to apply only the guardrails that should be applied in a specific request phase.
                "x-aim-litellm-hook": hook,
                # Used by Aim to track LiteLLM version and provide backward compatibility.
                "x-aim-litellm-version": litellm_version,
            }
            # Used by Aim to track together single call input and output
            | ({"x-aim-litellm-call-id": litellm_call_id} if litellm_call_id else {})
            # Used by Aim to track guardrails violations by user.
            | ({"x-aim-user-email": user_email} if user_email else {})
            | (
                {
                    # Used by Aim apply only the guardrails that are associated with the key alias.
                    "x-aim-litellm-key-alias": key_alias,
                }
                if key_alias
                else {}
            )
        )

    async def async_post_call_success_hook(
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        response: Union[Any, ModelResponse, EmbeddingResponse, ImageResponse],
    ) -> Any:
        if (
            isinstance(response, ModelResponse)
            and response.choices
            and isinstance(response.choices[0], Choices)
        ):
            content = response.choices[0].message.content or ""
            aim_output_guardrail_result = await self.call_aim_guardrail_on_output(
                data, content, hook="output", key_alias=user_api_key_dict.key_alias
            )
            if aim_output_guardrail_result and aim_output_guardrail_result.get(
                "detection_message"
            ):
                raise HTTPException(
                    status_code=400,
                    detail=aim_output_guardrail_result.get("detection_message"),
                )
            if aim_output_guardrail_result and aim_output_guardrail_result.get(
                "redacted_output"
            ):
                response.choices[0].message.content = aim_output_guardrail_result.get(
                    "redacted_output"
                )
        return response

    async def async_post_call_streaming_iterator_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        response,
        request_data: dict,
    ) -> AsyncGenerator[ModelResponseStream, None]:
        user_email = (
            request_data.get("metadata", {}).get("headers", {}).get("x-aim-user-email")
        )
        call_id = request_data.get("litellm_call_id")
        async with connect(
            f"{self.ws_api_base}/detect/output/ws",
            additional_headers=self._build_aim_headers(
                hook="output",
                key_alias=user_api_key_dict.key_alias,
                user_email=user_email,
                litellm_call_id=call_id,
            ),
        ) as websocket:
            sender = asyncio.create_task(
                self.forward_the_stream_to_aim(websocket, response)
            )
            while True:
                result = json.loads(await websocket.recv())
                if verified_chunk := result.get("verified_chunk"):
                    yield ModelResponseStream.model_validate(verified_chunk)
                else:
                    sender.cancel()
                    if result.get("done"):
                        return
                    if blocking_message := result.get("blocking_message"):
                        raise StreamingCallbackError(blocking_message)
                    verbose_proxy_logger.error(
                        f"Unknown message received from AIM: {result}"
                    )
                    return

    async def forward_the_stream_to_aim(
        self,
        websocket: ClientConnection,
        response_iter,
    ) -> None:
        async for chunk in response_iter:
            if isinstance(chunk, BaseModel):
                chunk = chunk.model_dump_json()
            if isinstance(chunk, dict):
                chunk = json.dumps(chunk)
            await websocket.send(chunk)
        await websocket.send(json.dumps({"done": True}))

    def _set_dlp_entities(self, entities: list[dict]) -> None:
        self.dlp_entities = entities[: self._max_dlp_entities]

# === NexusCore/openenv\Lib\site-packages\setuptools\config\_validate_pyproject\error_reporting.py ===
import io
import json
import logging
import os
import re
import typing
from contextlib import contextmanager
from textwrap import indent, wrap
from typing import Any, Dict, Generator, Iterator, List, Optional, Sequence, Union

from .fastjsonschema_exceptions import JsonSchemaValueException

if typing.TYPE_CHECKING:
    import sys

    if sys.version_info < (3, 11):
        from typing_extensions import Self
    else:
        from typing import Self

_logger = logging.getLogger(__name__)

_MESSAGE_REPLACEMENTS = {
    "must be named by propertyName definition": "keys must be named by",
    "one of contains definition": "at least one item that matches",
    " same as const definition:": "",
    "only specified items": "only items matching the definition",
}

_SKIP_DETAILS = (
    "must not be empty",
    "is always invalid",
    "must not be there",
)

_NEED_DETAILS = {"anyOf", "oneOf", "allOf", "contains", "propertyNames", "not", "items"}

_CAMEL_CASE_SPLITTER = re.compile(r"\W+|([A-Z][^A-Z\W]*)")
_IDENTIFIER = re.compile(r"^[\w_]+$", re.I)

_TOML_JARGON = {
    "object": "table",
    "property": "key",
    "properties": "keys",
    "property names": "keys",
}

_FORMATS_HELP = """
For more details about `format` see
https://validate-pyproject.readthedocs.io/en/latest/api/validate_pyproject.formats.html
"""


class ValidationError(JsonSchemaValueException):
    """Report violations of a given JSON schema.

    This class extends :exc:`~fastjsonschema.JsonSchemaValueException`
    by adding the following properties:

    - ``summary``: an improved version of the ``JsonSchemaValueException`` error message
      with only the necessary information)

    - ``details``: more contextual information about the error like the failing schema
      itself and the value that violates the schema.

    Depending on the level of the verbosity of the ``logging`` configuration
    the exception message will be only ``summary`` (default) or a combination of
    ``summary`` and ``details`` (when the logging level is set to :obj:`logging.DEBUG`).
    """

    summary = ""
    details = ""
    _original_message = ""

    @classmethod
    def _from_jsonschema(cls, ex: JsonSchemaValueException) -> "Self":
        formatter = _ErrorFormatting(ex)
        obj = cls(str(formatter), ex.value, formatter.name, ex.definition, ex.rule)
        debug_code = os.getenv("JSONSCHEMA_DEBUG_CODE_GENERATION", "false").lower()
        if debug_code != "false":  # pragma: no cover
            obj.__cause__, obj.__traceback__ = ex.__cause__, ex.__traceback__
        obj._original_message = ex.message
        obj.summary = formatter.summary
        obj.details = formatter.details
        return obj


@contextmanager
def detailed_errors() -> Generator[None, None, None]:
    try:
        yield
    except JsonSchemaValueException as ex:
        raise ValidationError._from_jsonschema(ex) from None


class _ErrorFormatting:
    def __init__(self, ex: JsonSchemaValueException):
        self.ex = ex
        self.name = f"`{self._simplify_name(ex.name)}`"
        self._original_message: str = self.ex.message.replace(ex.name, self.name)
        self._summary = ""
        self._details = ""

    def __str__(self) -> str:
        if _logger.getEffectiveLevel() <= logging.DEBUG and self.details:
            return f"{self.summary}\n\n{self.details}"

        return self.summary

    @property
    def summary(self) -> str:
        if not self._summary:
            self._summary = self._expand_summary()

        return self._summary

    @property
    def details(self) -> str:
        if not self._details:
            self._details = self._expand_details()

        return self._details

    @staticmethod
    def _simplify_name(name: str) -> str:
        x = len("data.")
        return name[x:] if name.startswith("data.") else name

    def _expand_summary(self) -> str:
        msg = self._original_message

        for bad, repl in _MESSAGE_REPLACEMENTS.items():
            msg = msg.replace(bad, repl)

        if any(substring in msg for substring in _SKIP_DETAILS):
            return msg

        schema = self.ex.rule_definition
        if self.ex.rule in _NEED_DETAILS and schema:
            summary = _SummaryWriter(_TOML_JARGON)
            return f"{msg}:\n\n{indent(summary(schema), '    ')}"

        return msg

    def _expand_details(self) -> str:
        optional = []
        definition = self.ex.definition or {}
        desc_lines = definition.pop("$$description", [])
        desc = definition.pop("description", None) or " ".join(desc_lines)
        if desc:
            description = "\n".join(
                wrap(
                    desc,
                    width=80,
                    initial_indent="    ",
                    subsequent_indent="    ",
                    break_long_words=False,
                )
            )
            optional.append(f"DESCRIPTION:\n{description}")
        schema = json.dumps(definition, indent=4)
        value = json.dumps(self.ex.value, indent=4)
        defaults = [
            f"GIVEN VALUE:\n{indent(value, '    ')}",
            f"OFFENDING RULE: {self.ex.rule!r}",
            f"DEFINITION:\n{indent(schema, '    ')}",
        ]
        msg = "\n\n".join(optional + defaults)
        epilog = f"\n{_FORMATS_HELP}" if "format" in msg.lower() else ""
        return msg + epilog


class _SummaryWriter:
    _IGNORE = frozenset(("description", "default", "title", "examples"))

    def __init__(self, jargon: Optional[Dict[str, str]] = None):
        self.jargon: Dict[str, str] = jargon or {}
        # Clarify confusing terms
        self._terms = {
            "anyOf": "at least one of the following",
            "oneOf": "exactly one of the following",
            "allOf": "all of the following",
            "not": "(*NOT* the following)",
            "prefixItems": f"{self._jargon('items')} (in order)",
            "items": "items",
            "contains": "contains at least one of",
            "propertyNames": (
                f"non-predefined acceptable {self._jargon('property names')}"
            ),
            "patternProperties": f"{self._jargon('properties')} named via pattern",
            "const": "predefined value",
            "enum": "one of",
        }
        # Attributes that indicate that the definition is easy and can be done
        # inline (e.g. string and number)
        self._guess_inline_defs = [
            "enum",
            "const",
            "maxLength",
            "minLength",
            "pattern",
            "format",
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "multipleOf",
        ]

    def _jargon(self, term: Union[str, List[str]]) -> Union[str, List[str]]:
        if isinstance(term, list):
            return [self.jargon.get(t, t) for t in term]
        return self.jargon.get(term, term)

    def __call__(
        self,
        schema: Union[dict, List[dict]],
        prefix: str = "",
        *,
        _path: Sequence[str] = (),
    ) -> str:
        if isinstance(schema, list):
            return self._handle_list(schema, prefix, _path)

        filtered = self._filter_unecessary(schema, _path)
        simple = self._handle_simple_dict(filtered, _path)
        if simple:
            return f"{prefix}{simple}"

        child_prefix = self._child_prefix(prefix, "  ")
        item_prefix = self._child_prefix(prefix, "- ")
        indent = len(prefix) * " "
        with io.StringIO() as buffer:
            for i, (key, value) in enumerate(filtered.items()):
                child_path = [*_path, key]
                line_prefix = prefix if i == 0 else indent
                buffer.write(f"{line_prefix}{self._label(child_path)}:")
                # ^  just the first item should receive the complete prefix
                if isinstance(value, dict):
                    filtered = self._filter_unecessary(value, child_path)
                    simple = self._handle_simple_dict(filtered, child_path)
                    buffer.write(
                        f" {simple}"
                        if simple
                        else f"\n{self(value, child_prefix, _path=child_path)}"
                    )
                elif isinstance(value, list) and (
                    key != "type" or self._is_property(child_path)
                ):
                    children = self._handle_list(value, item_prefix, child_path)
                    sep = " " if children.startswith("[") else "\n"
                    buffer.write(f"{sep}{children}")
                else:
                    buffer.write(f" {self._value(value, child_path)}\n")
            return buffer.getvalue()

    def _is_unecessary(self, path: Sequence[str]) -> bool:
        if self._is_property(path) or not path:  # empty path => instruction @ root
            return False
        key = path[-1]
        return any(key.startswith(k) for k in "$_") or key in self._IGNORE

    def _filter_unecessary(
        self, schema: Dict[str, Any], path: Sequence[str]
    ) -> Dict[str, Any]:
        return {
            key: value
            for key, value in schema.items()
            if not self._is_unecessary([*path, key])
        }

    def _handle_simple_dict(self, value: dict, path: Sequence[str]) -> Optional[str]:
        inline = any(p in value for p in self._guess_inline_defs)
        simple = not any(isinstance(v, (list, dict)) for v in value.values())
        if inline or simple:
            return f"{{{', '.join(self._inline_attrs(value, path))}}}\n"
        return None

    def _handle_list(
        self, schemas: list, prefix: str = "", path: Sequence[str] = ()
    ) -> str:
        if self._is_unecessary(path):
            return ""

        repr_ = repr(schemas)
        if all(not isinstance(e, (dict, list)) for e in schemas) and len(repr_) < 60:
            return f"{repr_}\n"

        item_prefix = self._child_prefix(prefix, "- ")
        return "".join(
            self(v, item_prefix, _path=[*path, f"[{i}]"]) for i, v in enumerate(schemas)
        )

    def _is_property(self, path: Sequence[str]) -> bool:
        """Check if the given path can correspond to an arbitrarily named property"""
        counter = 0
        for key in path[-2::-1]:
            if key not in {"properties", "patternProperties"}:
                break
            counter += 1

        # If the counter if even, the path correspond to a JSON Schema keyword
        # otherwise it can be any arbitrary string naming a property
        return counter % 2 == 1

    def _label(self, path: Sequence[str]) -> str:
        *parents, key = path
        if not self._is_property(path):
            norm_key = _separate_terms(key)
            return self._terms.get(key) or " ".join(self._jargon(norm_key))

        if parents[-1] == "patternProperties":
            return f"(regex {key!r})"
        return repr(key)  # property name

    def _value(self, value: Any, path: Sequence[str]) -> str:
        if path[-1] == "type" and not self._is_property(path):
            type_ = self._jargon(value)
            return f"[{', '.join(type_)}]" if isinstance(type_, list) else type_
        return repr(value)

    def _inline_attrs(self, schema: dict, path: Sequence[str]) -> Iterator[str]:
        for key, value in schema.items():
            child_path = [*path, key]
            yield f"{self._label(child_path)}: {self._value(value, child_path)}"

    def _child_prefix(self, parent_prefix: str, child_prefix: str) -> str:
        return len(parent_prefix) * " " + child_prefix


def _separate_terms(word: str) -> List[str]:
    """
    >>> _separate_terms("FooBar-foo")
    ['foo', 'bar', 'foo']
    """
    return [w.lower() for w in _CAMEL_CASE_SPLITTER.split(word) if w]

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_highlevel_socket.py ===
from __future__ import annotations

import errno
import socket as stdlib_socket
import sys
from typing import TYPE_CHECKING

import pytest

from .. import _core, socket as tsocket
from .._highlevel_socket import *
from ..testing import (
    assert_checkpoints,
    check_half_closeable_stream,
    wait_all_tasks_blocked,
)
from .test_socket import setsockopt_tests

if TYPE_CHECKING:
    from collections.abc import Sequence


async def test_SocketStream_basics() -> None:
    # stdlib socket bad (even if connected)
    stdlib_a, stdlib_b = stdlib_socket.socketpair()
    with stdlib_a, stdlib_b:
        with pytest.raises(TypeError):
            SocketStream(stdlib_a)  # type: ignore[arg-type]

    # DGRAM socket bad
    with tsocket.socket(type=tsocket.SOCK_DGRAM) as sock:
        with pytest.raises(
            ValueError,
            match=r"^SocketStream requires a SOCK_STREAM socket$",
        ):
            # TODO: does not raise an error?
            SocketStream(sock)

    a, b = tsocket.socketpair()
    with a, b:
        s = SocketStream(a)
        assert s.socket is a

    # Use a real, connected socket to test socket options, because
    # socketpair() might give us a unix socket that doesn't support any of
    # these options
    with tsocket.socket() as listen_sock:
        await listen_sock.bind(("127.0.0.1", 0))
        listen_sock.listen(1)
        with tsocket.socket() as client_sock:
            await client_sock.connect(listen_sock.getsockname())

            s = SocketStream(client_sock)

            # TCP_NODELAY enabled by default
            assert s.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)
            # We can disable it though
            s.setsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, False)
            assert not s.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY)

            res = s.getsockopt(tsocket.IPPROTO_TCP, tsocket.TCP_NODELAY, 1)
            assert isinstance(res, bytes)

            setsockopt_tests(s)


async def test_SocketStream_send_all() -> None:
    BIG = 10000000

    a_sock, b_sock = tsocket.socketpair()
    with a_sock, b_sock:
        a = SocketStream(a_sock)
        b = SocketStream(b_sock)

        # Check a send_all that has to be split into multiple parts (on most
        # platforms... on Windows every send() either succeeds or fails as a
        # whole)
        async def sender() -> None:
            data = bytearray(BIG)
            await a.send_all(data)
            # send_all uses memoryviews internally, which temporarily "lock"
            # the object they view. If it doesn't clean them up properly, then
            # some bytearray operations might raise an error afterwards, which
            # would be a pretty weird and annoying side-effect to spring on
            # users. So test that this doesn't happen, by forcing the
            # bytearray's underlying buffer to be realloc'ed:
            data += bytes(BIG)
            # (Note: the above line of code doesn't do a very good job at
            # testing anything, because:
            # - on CPython, the refcount GC generally cleans up memoryviews
            #   for us even if we're sloppy.
            # - on PyPy3, at least as of 5.7.0, the memoryview code and the
            #   bytearray code conspire so that resizing never fails – if
            #   resizing forces the bytearray's internal buffer to move, then
            #   all memoryview references are automagically updated (!!).
            #   See:
            #   https://gist.github.com/njsmith/0ffd38ec05ad8e34004f34a7dc492227
            # But I'm leaving the test here in hopes that if this ever changes
            # and we break our implementation of send_all, then we'll get some
            # early warning...)

        async def receiver() -> None:
            # Make sure the sender fills up the kernel buffers and blocks
            await wait_all_tasks_blocked()
            nbytes = 0
            while nbytes < BIG:
                nbytes += len(await b.receive_some(BIG))
            assert nbytes == BIG

        async with _core.open_nursery() as nursery:
            nursery.start_soon(sender)
            nursery.start_soon(receiver)

        # We know that we received BIG bytes of NULs so far. Make sure that
        # was all the data in there.
        await a.send_all(b"e")
        assert await b.receive_some(10) == b"e"
        await a.send_eof()
        assert await b.receive_some(10) == b""


async def fill_stream(s: SocketStream) -> None:
    async def sender() -> None:
        while True:
            await s.send_all(b"x" * 10000)

    async def waiter(nursery: _core.Nursery) -> None:
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(sender)
        nursery.start_soon(waiter, nursery)


async def test_SocketStream_generic() -> None:
    async def stream_maker() -> tuple[
        SocketStream,
        SocketStream,
    ]:
        left, right = tsocket.socketpair()
        return SocketStream(left), SocketStream(right)

    async def clogged_stream_maker() -> tuple[SocketStream, SocketStream]:
        left, right = await stream_maker()
        await fill_stream(left)
        await fill_stream(right)
        return left, right

    await check_half_closeable_stream(stream_maker, clogged_stream_maker)


async def test_SocketListener() -> None:
    # Not a Trio socket
    with stdlib_socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(10)
        with pytest.raises(TypeError):
            SocketListener(s)  # type: ignore[arg-type]

    # Not a SOCK_STREAM
    with tsocket.socket(type=tsocket.SOCK_DGRAM) as s:
        await s.bind(("127.0.0.1", 0))
        with pytest.raises(
            ValueError,
            match=r"^SocketListener requires a SOCK_STREAM socket$",
        ) as excinfo:
            SocketListener(s)
        excinfo.match(r".*SOCK_STREAM")

    # Didn't call .listen()
    # macOS has no way to check for this, so skip testing it there.
    if sys.platform != "darwin":
        with tsocket.socket() as s:
            await s.bind(("127.0.0.1", 0))
            with pytest.raises(
                ValueError,
                match=r"^SocketListener requires a listening socket$",
            ) as excinfo:
                SocketListener(s)
            excinfo.match(r".*listen")

    listen_sock = tsocket.socket()
    await listen_sock.bind(("127.0.0.1", 0))
    listen_sock.listen(10)
    listener = SocketListener(listen_sock)

    assert listener.socket is listen_sock

    client_sock = tsocket.socket()
    await client_sock.connect(listen_sock.getsockname())
    with assert_checkpoints():
        server_stream = await listener.accept()
    assert isinstance(server_stream, SocketStream)
    assert server_stream.socket.getsockname() == listen_sock.getsockname()
    assert server_stream.socket.getpeername() == client_sock.getsockname()

    with assert_checkpoints():
        await listener.aclose()

    with assert_checkpoints():
        await listener.aclose()

    with assert_checkpoints():
        with pytest.raises(_core.ClosedResourceError):
            await listener.accept()

    client_sock.close()
    await server_stream.aclose()


async def test_SocketListener_socket_closed_underfoot() -> None:
    listen_sock = tsocket.socket()
    await listen_sock.bind(("127.0.0.1", 0))
    listen_sock.listen(10)
    listener = SocketListener(listen_sock)

    # Close the socket, not the listener
    listen_sock.close()

    # SocketListener gives correct error
    with assert_checkpoints():
        with pytest.raises(_core.ClosedResourceError):
            await listener.accept()


async def test_SocketListener_accept_errors() -> None:
    class FakeSocket(tsocket.SocketType):
        def __init__(self, events: Sequence[SocketType | BaseException]) -> None:
            self._events = iter(events)

        type = tsocket.SOCK_STREAM

        # Fool the check for SO_ACCEPTCONN in SocketListener.__init__
        @overload
        def getsockopt(self, /, level: int, optname: int) -> int: ...

        @overload
        def getsockopt(  # noqa: F811
            self,
            /,
            level: int,
            optname: int,
            buflen: int,
        ) -> bytes: ...

        def getsockopt(  # noqa: F811
            self,
            /,
            level: int,
            optname: int,
            buflen: int | None = None,
        ) -> int | bytes:
            return True

        @overload
        def setsockopt(
            self,
            /,
            level: int,
            optname: int,
            value: int | Buffer,
        ) -> None: ...

        @overload
        def setsockopt(  # noqa: F811
            self,
            /,
            level: int,
            optname: int,
            value: None,
            optlen: int,
        ) -> None: ...

        def setsockopt(  # noqa: F811
            self,
            /,
            level: int,
            optname: int,
            value: int | Buffer | None,
            optlen: int | None = None,
        ) -> None:
            pass

        async def accept(self) -> tuple[SocketType, object]:
            await _core.checkpoint()
            event = next(self._events)
            if isinstance(event, BaseException):
                raise event
            else:
                return event, None

    fake_server_sock = FakeSocket([])

    fake_listen_sock = FakeSocket(
        [
            OSError(errno.ECONNABORTED, "Connection aborted"),
            OSError(errno.EPERM, "Permission denied"),
            OSError(errno.EPROTO, "Bad protocol"),
            fake_server_sock,
            OSError(errno.EMFILE, "Out of file descriptors"),
            OSError(errno.EFAULT, "attempt to write to read-only memory"),
            OSError(errno.ENOBUFS, "out of buffers"),
            fake_server_sock,
        ],
    )

    listener = SocketListener(fake_listen_sock)

    with assert_checkpoints():
        stream = await listener.accept()
        assert stream.socket is fake_server_sock

    for code, match in {
        errno.EMFILE: r"\[\w+ \d+\] Out of file descriptors$",
        errno.EFAULT: r"\[\w+ \d+\] attempt to write to read-only memory$",
        errno.ENOBUFS: r"\[\w+ \d+\] out of buffers$",
    }.items():
        with assert_checkpoints():
            with pytest.raises(OSError, match=match) as excinfo:
                await listener.accept()
            assert excinfo.value.errno == code

    with assert_checkpoints():
        stream = await listener.accept()
        assert stream.socket is fake_server_sock


async def test_socket_stream_works_when_peer_has_already_closed() -> None:
    sock_a, sock_b = tsocket.socketpair()
    with sock_a, sock_b:
        await sock_b.send(b"x")
        sock_b.close()
        stream = SocketStream(sock_a)
        assert await stream.receive_some(1) == b"x"
        assert await stream.receive_some(1) == b""

# === NexusCore/openenv\Lib\site-packages\win32\Demos\security\security_enums.py ===
import ntsecuritycon
import win32security
import winnt


class Enum:
    def __init__(self, *const_names):
        """Accepts variable number of constant names that can be found in either
        win32security, ntsecuritycon, or winnt."""
        for const_name in const_names:
            try:
                const_val = getattr(win32security, const_name)
            except AttributeError:
                try:
                    const_val = getattr(ntsecuritycon, const_name)
                except AttributeError:
                    try:
                        const_val = getattr(winnt, const_name)
                    except AttributeError:
                        raise AttributeError(
                            'Constant "%s" not found in win32security, ntsecuritycon, or winnt.'
                            % const_name
                        )
            setattr(self, const_name, const_val)

    def lookup_name(self, const_val):
        """Looks up the name of a particular value."""
        for k, v in self.__dict__.items():
            if v == const_val:
                return k
        raise AttributeError("Value %s not found in enum" % const_val)

    def lookup_flags(self, flags):
        """Returns the names of all recognized flags in input, and any flags not found in the enum."""
        flag_names = []
        unknown_flags = flags
        for k, v in self.__dict__.items():
            if flags & v == v:
                flag_names.append(k)
                unknown_flags &= ~v
        return flag_names, unknown_flags


TOKEN_INFORMATION_CLASS = Enum(
    "TokenUser",
    "TokenGroups",
    "TokenPrivileges",
    "TokenOwner",
    "TokenPrimaryGroup",
    "TokenDefaultDacl",
    "TokenSource",
    "TokenType",
    "TokenImpersonationLevel",
    "TokenStatistics",
    "TokenRestrictedSids",
    "TokenSessionId",
    "TokenGroupsAndPrivileges",
    "TokenSessionReference",
    "TokenSandBoxInert",
    "TokenAuditPolicy",
    "TokenOrigin",
    "TokenElevationType",
    "TokenLinkedToken",
    "TokenElevation",
    "TokenHasRestrictions",
    "TokenAccessInformation",
    "TokenVirtualizationAllowed",
    "TokenVirtualizationEnabled",
    "TokenIntegrityLevel",
    "TokenUIAccess",
    "TokenMandatoryPolicy",
    "TokenLogonSid",
)

TOKEN_TYPE = Enum("TokenPrimary", "TokenImpersonation")

TOKEN_ELEVATION_TYPE = Enum(
    "TokenElevationTypeDefault", "TokenElevationTypeFull", "TokenElevationTypeLimited"
)

POLICY_AUDIT_EVENT_TYPE = Enum(
    "AuditCategorySystem",
    "AuditCategoryLogon",
    "AuditCategoryObjectAccess",
    "AuditCategoryPrivilegeUse",
    "AuditCategoryDetailedTracking",
    "AuditCategoryPolicyChange",
    "AuditCategoryAccountManagement",
    "AuditCategoryDirectoryServiceAccess",
    "AuditCategoryAccountLogon",
)

POLICY_INFORMATION_CLASS = Enum(
    "PolicyAuditLogInformation",
    "PolicyAuditEventsInformation",
    "PolicyPrimaryDomainInformation",
    "PolicyPdAccountInformation",
    "PolicyAccountDomainInformation",
    "PolicyLsaServerRoleInformation",
    "PolicyReplicaSourceInformation",
    "PolicyDefaultQuotaInformation",
    "PolicyModificationInformation",
    "PolicyAuditFullSetInformation",
    "PolicyAuditFullQueryInformation",
    "PolicyDnsDomainInformation",
)

POLICY_LSA_SERVER_ROLE = Enum("PolicyServerRoleBackup", "PolicyServerRolePrimary")

## access modes for opening a policy handle - this is not a real enum
POLICY_ACCESS_MODES = Enum(
    "POLICY_VIEW_LOCAL_INFORMATION",
    "POLICY_VIEW_AUDIT_INFORMATION",
    "POLICY_GET_PRIVATE_INFORMATION",
    "POLICY_TRUST_ADMIN",
    "POLICY_CREATE_ACCOUNT",
    "POLICY_CREATE_SECRET",
    "POLICY_CREATE_PRIVILEGE",
    "POLICY_SET_DEFAULT_QUOTA_LIMITS",
    "POLICY_SET_AUDIT_REQUIREMENTS",
    "POLICY_AUDIT_LOG_ADMIN",
    "POLICY_SERVER_ADMIN",
    "POLICY_LOOKUP_NAMES",
    "POLICY_NOTIFICATION",
    "POLICY_ALL_ACCESS",
    "POLICY_READ",
    "POLICY_WRITE",
    "POLICY_EXECUTE",
)

## EventAuditingOptions flags - not a real enum
POLICY_AUDIT_EVENT_OPTIONS_FLAGS = Enum(
    "POLICY_AUDIT_EVENT_UNCHANGED",
    "POLICY_AUDIT_EVENT_SUCCESS",
    "POLICY_AUDIT_EVENT_FAILURE",
    "POLICY_AUDIT_EVENT_NONE",
)

# AceType in ACE_HEADER - not a real enum
ACE_TYPE = Enum(
    "ACCESS_MIN_MS_ACE_TYPE",
    "ACCESS_ALLOWED_ACE_TYPE",
    "ACCESS_DENIED_ACE_TYPE",
    "SYSTEM_AUDIT_ACE_TYPE",
    "SYSTEM_ALARM_ACE_TYPE",
    "ACCESS_MAX_MS_V2_ACE_TYPE",
    "ACCESS_ALLOWED_COMPOUND_ACE_TYPE",
    "ACCESS_MAX_MS_V3_ACE_TYPE",
    "ACCESS_MIN_MS_OBJECT_ACE_TYPE",
    "ACCESS_ALLOWED_OBJECT_ACE_TYPE",
    "ACCESS_DENIED_OBJECT_ACE_TYPE",
    "SYSTEM_AUDIT_OBJECT_ACE_TYPE",
    "SYSTEM_ALARM_OBJECT_ACE_TYPE",
    "ACCESS_MAX_MS_OBJECT_ACE_TYPE",
    "ACCESS_MAX_MS_V4_ACE_TYPE",
    "ACCESS_MAX_MS_ACE_TYPE",
    "ACCESS_ALLOWED_CALLBACK_ACE_TYPE",
    "ACCESS_DENIED_CALLBACK_ACE_TYPE",
    "ACCESS_ALLOWED_CALLBACK_OBJECT_ACE_TYPE",
    "ACCESS_DENIED_CALLBACK_OBJECT_ACE_TYPE",
    "SYSTEM_AUDIT_CALLBACK_ACE_TYPE",
    "SYSTEM_ALARM_CALLBACK_ACE_TYPE",
    "SYSTEM_AUDIT_CALLBACK_OBJECT_ACE_TYPE",
    "SYSTEM_ALARM_CALLBACK_OBJECT_ACE_TYPE",
    "SYSTEM_MANDATORY_LABEL_ACE_TYPE",
    "ACCESS_MAX_MS_V5_ACE_TYPE",
)

# bit flags for AceFlags - not a real enum
ACE_FLAGS = Enum(
    "CONTAINER_INHERIT_ACE",
    "FAILED_ACCESS_ACE_FLAG",
    "INHERIT_ONLY_ACE",
    "INHERITED_ACE",
    "NO_PROPAGATE_INHERIT_ACE",
    "OBJECT_INHERIT_ACE",
    "SUCCESSFUL_ACCESS_ACE_FLAG",
    "NO_INHERITANCE",
    "SUB_CONTAINERS_AND_OBJECTS_INHERIT",
    "SUB_CONTAINERS_ONLY_INHERIT",
    "SUB_OBJECTS_ONLY_INHERIT",
)

# used in SetEntriesInAcl - very similar to ACE_TYPE
ACCESS_MODE = Enum(
    "NOT_USED_ACCESS",
    "GRANT_ACCESS",
    "SET_ACCESS",
    "DENY_ACCESS",
    "REVOKE_ACCESS",
    "SET_AUDIT_SUCCESS",
    "SET_AUDIT_FAILURE",
)

# Bit flags in PSECURITY_DESCRIPTOR->Control - not a real enum
SECURITY_DESCRIPTOR_CONTROL_FLAGS = Enum(
    "SE_DACL_AUTO_INHERITED",  ## win2k and up
    "SE_SACL_AUTO_INHERITED",  ## win2k and up
    "SE_DACL_PROTECTED",  ## win2k and up
    "SE_SACL_PROTECTED",  ## win2k and up
    "SE_DACL_DEFAULTED",
    "SE_DACL_PRESENT",
    "SE_GROUP_DEFAULTED",
    "SE_OWNER_DEFAULTED",
    "SE_SACL_PRESENT",
    "SE_SELF_RELATIVE",
    "SE_SACL_DEFAULTED",
)

# types of SID
SID_NAME_USE = Enum(
    "SidTypeUser",
    "SidTypeGroup",
    "SidTypeDomain",
    "SidTypeAlias",
    "SidTypeWellKnownGroup",
    "SidTypeDeletedAccount",
    "SidTypeInvalid",
    "SidTypeUnknown",
    "SidTypeComputer",
    "SidTypeLabel",
)

## bit flags, not a real enum
TOKEN_ACCESS_PRIVILEGES = Enum(
    "TOKEN_ADJUST_DEFAULT",
    "TOKEN_ADJUST_GROUPS",
    "TOKEN_ADJUST_PRIVILEGES",
    "TOKEN_ALL_ACCESS",
    "TOKEN_ASSIGN_PRIMARY",
    "TOKEN_DUPLICATE",
    "TOKEN_EXECUTE",
    "TOKEN_IMPERSONATE",
    "TOKEN_QUERY",
    "TOKEN_QUERY_SOURCE",
    "TOKEN_READ",
    "TOKEN_WRITE",
)

SECURITY_IMPERSONATION_LEVEL = Enum(
    "SecurityAnonymous",
    "SecurityIdentification",
    "SecurityImpersonation",
    "SecurityDelegation",
)

POLICY_SERVER_ENABLE_STATE = Enum("PolicyServerEnabled", "PolicyServerDisabled")

POLICY_NOTIFICATION_INFORMATION_CLASS = Enum(
    "PolicyNotifyAuditEventsInformation",
    "PolicyNotifyAccountDomainInformation",
    "PolicyNotifyServerRoleInformation",
    "PolicyNotifyDnsDomainInformation",
    "PolicyNotifyDomainEfsInformation",
    "PolicyNotifyDomainKerberosTicketInformation",
    "PolicyNotifyMachineAccountPasswordInformation",
)

TRUSTED_INFORMATION_CLASS = Enum(
    "TrustedDomainNameInformation",
    "TrustedControllersInformation",
    "TrustedPosixOffsetInformation",
    "TrustedPasswordInformation",
    "TrustedDomainInformationBasic",
    "TrustedDomainInformationEx",
    "TrustedDomainAuthInformation",
    "TrustedDomainFullInformation",
    "TrustedDomainAuthInformationInternal",
    "TrustedDomainFullInformationInternal",
    "TrustedDomainInformationEx2Internal",
    "TrustedDomainFullInformation2Internal",
)

TRUSTEE_FORM = Enum(
    "TRUSTEE_IS_SID",
    "TRUSTEE_IS_NAME",
    "TRUSTEE_BAD_FORM",
    "TRUSTEE_IS_OBJECTS_AND_SID",
    "TRUSTEE_IS_OBJECTS_AND_NAME",
)

TRUSTEE_TYPE = Enum(
    "TRUSTEE_IS_UNKNOWN",
    "TRUSTEE_IS_USER",
    "TRUSTEE_IS_GROUP",
    "TRUSTEE_IS_DOMAIN",
    "TRUSTEE_IS_ALIAS",
    "TRUSTEE_IS_WELL_KNOWN_GROUP",
    "TRUSTEE_IS_DELETED",
    "TRUSTEE_IS_INVALID",
    "TRUSTEE_IS_COMPUTER",
)

## SE_OBJECT_TYPE - securable objects
SE_OBJECT_TYPE = Enum(
    "SE_UNKNOWN_OBJECT_TYPE",
    "SE_FILE_OBJECT",
    "SE_SERVICE",
    "SE_PRINTER",
    "SE_REGISTRY_KEY",
    "SE_LMSHARE",
    "SE_KERNEL_OBJECT",
    "SE_WINDOW_OBJECT",
    "SE_DS_OBJECT",
    "SE_DS_OBJECT_ALL",
    "SE_PROVIDER_DEFINED_OBJECT",
    "SE_WMIGUID_OBJECT",
    "SE_REGISTRY_WOW64_32KEY",
)

PRIVILEGE_FLAGS = Enum(
    "SE_PRIVILEGE_ENABLED_BY_DEFAULT",
    "SE_PRIVILEGE_ENABLED",
    "SE_PRIVILEGE_USED_FOR_ACCESS",
)

# Group flags used with TokenGroups
TOKEN_GROUP_ATTRIBUTES = Enum(
    "SE_GROUP_MANDATORY",
    "SE_GROUP_ENABLED_BY_DEFAULT",
    "SE_GROUP_ENABLED",
    "SE_GROUP_OWNER",
    "SE_GROUP_USE_FOR_DENY_ONLY",
    "SE_GROUP_INTEGRITY",
    "SE_GROUP_INTEGRITY_ENABLED",
    "SE_GROUP_LOGON_ID",
    "SE_GROUP_RESOURCE",
)

# Privilege flags returned by TokenPrivileges
TOKEN_PRIVILEGE_ATTRIBUTES = Enum(
    "SE_PRIVILEGE_ENABLED_BY_DEFAULT",
    "SE_PRIVILEGE_ENABLED",
    "SE_PRIVILEGE_REMOVED",
    "SE_PRIVILEGE_USED_FOR_ACCESS",
)

# === NexusCore/openenv\Lib\site-packages\urllib3\exceptions.py ===
from __future__ import annotations

import socket
import typing
import warnings
from email.errors import MessageDefect
from http.client import IncompleteRead as httplib_IncompleteRead

if typing.TYPE_CHECKING:
    from .connection import HTTPConnection
    from .connectionpool import ConnectionPool
    from .response import HTTPResponse
    from .util.retry import Retry

# Base Exceptions


class HTTPError(Exception):
    """Base exception used by this module."""


class HTTPWarning(Warning):
    """Base warning used by this module."""


_TYPE_REDUCE_RESULT = tuple[typing.Callable[..., object], tuple[object, ...]]


class PoolError(HTTPError):
    """Base exception for errors caused within a pool."""

    def __init__(self, pool: ConnectionPool, message: str) -> None:
        self.pool = pool
        self._message = message
        super().__init__(f"{pool}: {message}")

    def __reduce__(self) -> _TYPE_REDUCE_RESULT:
        # For pickling purposes.
        return self.__class__, (None, self._message)


class RequestError(PoolError):
    """Base exception for PoolErrors that have associated URLs."""

    def __init__(self, pool: ConnectionPool, url: str, message: str) -> None:
        self.url = url
        super().__init__(pool, message)

    def __reduce__(self) -> _TYPE_REDUCE_RESULT:
        # For pickling purposes.
        return self.__class__, (None, self.url, self._message)


class SSLError(HTTPError):
    """Raised when SSL certificate fails in an HTTPS connection."""


class ProxyError(HTTPError):
    """Raised when the connection to a proxy fails."""

    # The original error is also available as __cause__.
    original_error: Exception

    def __init__(self, message: str, error: Exception) -> None:
        super().__init__(message, error)
        self.original_error = error


class DecodeError(HTTPError):
    """Raised when automatic decoding based on Content-Type fails."""


class ProtocolError(HTTPError):
    """Raised when something unexpected happens mid-request/response."""


#: Renamed to ProtocolError but aliased for backwards compatibility.
ConnectionError = ProtocolError


# Leaf Exceptions


class MaxRetryError(RequestError):
    """Raised when the maximum number of retries is exceeded.

    :param pool: The connection pool
    :type pool: :class:`~urllib3.connectionpool.HTTPConnectionPool`
    :param str url: The requested Url
    :param reason: The underlying error
    :type reason: :class:`Exception`

    """

    def __init__(
        self, pool: ConnectionPool, url: str, reason: Exception | None = None
    ) -> None:
        self.reason = reason

        message = f"Max retries exceeded with url: {url} (Caused by {reason!r})"

        super().__init__(pool, url, message)

    def __reduce__(self) -> _TYPE_REDUCE_RESULT:
        # For pickling purposes.
        return self.__class__, (None, self.url, self.reason)


class HostChangedError(RequestError):
    """Raised when an existing pool gets a request for a foreign host."""

    def __init__(
        self, pool: ConnectionPool, url: str, retries: Retry | int = 3
    ) -> None:
        message = f"Tried to open a foreign host with url: {url}"
        super().__init__(pool, url, message)
        self.retries = retries


class TimeoutStateError(HTTPError):
    """Raised when passing an invalid state to a timeout"""


class TimeoutError(HTTPError):
    """Raised when a socket timeout error occurs.

    Catching this error will catch both :exc:`ReadTimeoutErrors
    <ReadTimeoutError>` and :exc:`ConnectTimeoutErrors <ConnectTimeoutError>`.
    """


class ReadTimeoutError(TimeoutError, RequestError):
    """Raised when a socket timeout occurs while receiving data from a server"""


# This timeout error does not have a URL attached and needs to inherit from the
# base HTTPError
class ConnectTimeoutError(TimeoutError):
    """Raised when a socket timeout occurs while connecting to a server"""


class NewConnectionError(ConnectTimeoutError, HTTPError):
    """Raised when we fail to establish a new connection. Usually ECONNREFUSED."""

    def __init__(self, conn: HTTPConnection, message: str) -> None:
        self.conn = conn
        self._message = message
        super().__init__(f"{conn}: {message}")

    def __reduce__(self) -> _TYPE_REDUCE_RESULT:
        # For pickling purposes.
        return self.__class__, (None, self._message)

    @property
    def pool(self) -> HTTPConnection:
        warnings.warn(
            "The 'pool' property is deprecated and will be removed "
            "in urllib3 v2.1.0. Use 'conn' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        return self.conn


class NameResolutionError(NewConnectionError):
    """Raised when host name resolution fails."""

    def __init__(self, host: str, conn: HTTPConnection, reason: socket.gaierror):
        message = f"Failed to resolve '{host}' ({reason})"
        self._host = host
        self._reason = reason
        super().__init__(conn, message)

    def __reduce__(self) -> _TYPE_REDUCE_RESULT:
        # For pickling purposes.
        return self.__class__, (self._host, None, self._reason)


class EmptyPoolError(PoolError):
    """Raised when a pool runs out of connections and no more are allowed."""


class FullPoolError(PoolError):
    """Raised when we try to add a connection to a full pool in blocking mode."""


class ClosedPoolError(PoolError):
    """Raised when a request enters a pool after the pool has been closed."""


class LocationValueError(ValueError, HTTPError):
    """Raised when there is something wrong with a given URL input."""


class LocationParseError(LocationValueError):
    """Raised when get_host or similar fails to parse the URL input."""

    def __init__(self, location: str) -> None:
        message = f"Failed to parse: {location}"
        super().__init__(message)

        self.location = location


class URLSchemeUnknown(LocationValueError):
    """Raised when a URL input has an unsupported scheme."""

    def __init__(self, scheme: str):
        message = f"Not supported URL scheme {scheme}"
        super().__init__(message)

        self.scheme = scheme


class ResponseError(HTTPError):
    """Used as a container for an error reason supplied in a MaxRetryError."""

    GENERIC_ERROR = "too many error responses"
    SPECIFIC_ERROR = "too many {status_code} error responses"


class SecurityWarning(HTTPWarning):
    """Warned when performing security reducing actions"""


class InsecureRequestWarning(SecurityWarning):
    """Warned when making an unverified HTTPS request."""


class NotOpenSSLWarning(SecurityWarning):
    """Warned when using unsupported SSL library"""


class SystemTimeWarning(SecurityWarning):
    """Warned when system time is suspected to be wrong"""


class InsecurePlatformWarning(SecurityWarning):
    """Warned when certain TLS/SSL configuration is not available on a platform."""


class DependencyWarning(HTTPWarning):
    """
    Warned when an attempt is made to import a module with missing optional
    dependencies.
    """


class ResponseNotChunked(ProtocolError, ValueError):
    """Response needs to be chunked in order to read it as chunks."""


class BodyNotHttplibCompatible(HTTPError):
    """
    Body should be :class:`http.client.HTTPResponse` like
    (have an fp attribute which returns raw chunks) for read_chunked().
    """


class IncompleteRead(HTTPError, httplib_IncompleteRead):
    """
    Response length doesn't match expected Content-Length

    Subclass of :class:`http.client.IncompleteRead` to allow int value
    for ``partial`` to avoid creating large objects on streamed reads.
    """

    partial: int  # type: ignore[assignment]
    expected: int

    def __init__(self, partial: int, expected: int) -> None:
        self.partial = partial
        self.expected = expected

    def __repr__(self) -> str:
        return "IncompleteRead(%i bytes read, %i more expected)" % (
            self.partial,
            self.expected,
        )


class InvalidChunkLength(HTTPError, httplib_IncompleteRead):
    """Invalid chunk length in a chunked response."""

    def __init__(self, response: HTTPResponse, length: bytes) -> None:
        self.partial: int = response.tell()  # type: ignore[assignment]
        self.expected: int | None = response.length_remaining
        self.response = response
        self.length = length

    def __repr__(self) -> str:
        return "InvalidChunkLength(got length %r, %i bytes read)" % (
            self.length,
            self.partial,
        )


class InvalidHeader(HTTPError):
    """The header provided was somehow invalid."""


class ProxySchemeUnknown(AssertionError, URLSchemeUnknown):
    """ProxyManager does not support the supplied scheme"""

    # TODO(t-8ch): Stop inheriting from AssertionError in v2.0.

    def __init__(self, scheme: str | None) -> None:
        # 'localhost' is here because our URL parser parses
        # localhost:8080 -> scheme=localhost, remove if we fix this.
        if scheme == "localhost":
            scheme = None
        if scheme is None:
            message = "Proxy URL had no scheme, should start with http:// or https://"
        else:
            message = f"Proxy URL had unsupported scheme {scheme}, should use http:// or https://"
        super().__init__(message)


class ProxySchemeUnsupported(ValueError):
    """Fetching HTTPS resources through HTTPS proxies is unsupported"""


class HeaderParsingError(HTTPError):
    """Raised by assert_header_parsing, but we convert it to a log.warning statement."""

    def __init__(
        self, defects: list[MessageDefect], unparsed_data: bytes | str | None
    ) -> None:
        message = f"{defects or 'Unknown'}, unparsed data: {unparsed_data!r}"
        super().__init__(message)


class UnrewindableBodyError(HTTPError):
    """urllib3 encountered an error when trying to rewind a body"""

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\recordingPen.py ===
"""Pen recording operations that can be accessed or replayed."""

from fontTools.pens.basePen import AbstractPen, DecomposingPen
from fontTools.pens.pointPen import AbstractPointPen, DecomposingPointPen


__all__ = [
    "replayRecording",
    "RecordingPen",
    "DecomposingRecordingPen",
    "DecomposingRecordingPointPen",
    "RecordingPointPen",
    "lerpRecordings",
]


def replayRecording(recording, pen):
    """Replay a recording, as produced by RecordingPen or DecomposingRecordingPen,
    to a pen.

    Note that recording does not have to be produced by those pens.
    It can be any iterable of tuples of method name and tuple-of-arguments.
    Likewise, pen can be any objects receiving those method calls.
    """
    for operator, operands in recording:
        getattr(pen, operator)(*operands)


class RecordingPen(AbstractPen):
    """Pen recording operations that can be accessed or replayed.

    The recording can be accessed as pen.value; or replayed using
    pen.replay(otherPen).

    :Example:
        .. code-block::

            from fontTools.ttLib import TTFont
            from fontTools.pens.recordingPen import RecordingPen

            glyph_name = 'dollar'
            font_path = 'MyFont.otf'

            font = TTFont(font_path)
            glyphset = font.getGlyphSet()
            glyph = glyphset[glyph_name]

            pen = RecordingPen()
            glyph.draw(pen)
            print(pen.value)
    """

    def __init__(self):
        self.value = []

    def moveTo(self, p0):
        self.value.append(("moveTo", (p0,)))

    def lineTo(self, p1):
        self.value.append(("lineTo", (p1,)))

    def qCurveTo(self, *points):
        self.value.append(("qCurveTo", points))

    def curveTo(self, *points):
        self.value.append(("curveTo", points))

    def closePath(self):
        self.value.append(("closePath", ()))

    def endPath(self):
        self.value.append(("endPath", ()))

    def addComponent(self, glyphName, transformation):
        self.value.append(("addComponent", (glyphName, transformation)))

    def addVarComponent(self, glyphName, transformation, location):
        self.value.append(("addVarComponent", (glyphName, transformation, location)))

    def replay(self, pen):
        replayRecording(self.value, pen)

    draw = replay


class DecomposingRecordingPen(DecomposingPen, RecordingPen):
    """Same as RecordingPen, except that it doesn't keep components
    as references, but draws them decomposed as regular contours.

    The constructor takes a required 'glyphSet' positional argument,
    a dictionary of glyph objects (i.e. with a 'draw' method) keyed
    by thir name; other arguments are forwarded to the DecomposingPen's
    constructor::

        >>> class SimpleGlyph(object):
        ...     def draw(self, pen):
        ...         pen.moveTo((0, 0))
        ...         pen.curveTo((1, 1), (2, 2), (3, 3))
        ...         pen.closePath()
        >>> class CompositeGlyph(object):
        ...     def draw(self, pen):
        ...         pen.addComponent('a', (1, 0, 0, 1, -1, 1))
        >>> class MissingComponent(object):
        ...     def draw(self, pen):
        ...         pen.addComponent('foobar', (1, 0, 0, 1, 0, 0))
        >>> class FlippedComponent(object):
        ...     def draw(self, pen):
        ...         pen.addComponent('a', (-1, 0, 0, 1, 0, 0))
        >>> glyphSet = {
        ...    'a': SimpleGlyph(),
        ...    'b': CompositeGlyph(),
        ...    'c': MissingComponent(),
        ...    'd': FlippedComponent(),
        ... }
        >>> for name, glyph in sorted(glyphSet.items()):
        ...     pen = DecomposingRecordingPen(glyphSet)
        ...     try:
        ...         glyph.draw(pen)
        ...     except pen.MissingComponentError:
        ...         pass
        ...     print("{}: {}".format(name, pen.value))
        a: [('moveTo', ((0, 0),)), ('curveTo', ((1, 1), (2, 2), (3, 3))), ('closePath', ())]
        b: [('moveTo', ((-1, 1),)), ('curveTo', ((0, 2), (1, 3), (2, 4))), ('closePath', ())]
        c: []
        d: [('moveTo', ((0, 0),)), ('curveTo', ((-1, 1), (-2, 2), (-3, 3))), ('closePath', ())]

        >>> for name, glyph in sorted(glyphSet.items()):
        ...     pen = DecomposingRecordingPen(
        ...         glyphSet, skipMissingComponents=True, reverseFlipped=True,
        ...     )
        ...     glyph.draw(pen)
        ...     print("{}: {}".format(name, pen.value))
        a: [('moveTo', ((0, 0),)), ('curveTo', ((1, 1), (2, 2), (3, 3))), ('closePath', ())]
        b: [('moveTo', ((-1, 1),)), ('curveTo', ((0, 2), (1, 3), (2, 4))), ('closePath', ())]
        c: []
        d: [('moveTo', ((0, 0),)), ('lineTo', ((-3, 3),)), ('curveTo', ((-2, 2), (-1, 1), (0, 0))), ('closePath', ())]
    """

    # raises MissingComponentError(KeyError) if base glyph is not found in glyphSet
    skipMissingComponents = False


class RecordingPointPen(AbstractPointPen):
    """PointPen recording operations that can be accessed or replayed.

    The recording can be accessed as pen.value; or replayed using
    pointPen.replay(otherPointPen).

    :Example:
        .. code-block::

            from defcon import Font
            from fontTools.pens.recordingPen import RecordingPointPen

            glyph_name = 'a'
            font_path = 'MyFont.ufo'

            font = Font(font_path)
            glyph = font[glyph_name]

            pen = RecordingPointPen()
            glyph.drawPoints(pen)
            print(pen.value)

            new_glyph = font.newGlyph('b')
            pen.replay(new_glyph.getPointPen())
    """

    def __init__(self):
        self.value = []

    def beginPath(self, identifier=None, **kwargs):
        if identifier is not None:
            kwargs["identifier"] = identifier
        self.value.append(("beginPath", (), kwargs))

    def endPath(self):
        self.value.append(("endPath", (), {}))

    def addPoint(
        self, pt, segmentType=None, smooth=False, name=None, identifier=None, **kwargs
    ):
        if identifier is not None:
            kwargs["identifier"] = identifier
        self.value.append(("addPoint", (pt, segmentType, smooth, name), kwargs))

    def addComponent(self, baseGlyphName, transformation, identifier=None, **kwargs):
        if identifier is not None:
            kwargs["identifier"] = identifier
        self.value.append(("addComponent", (baseGlyphName, transformation), kwargs))

    def addVarComponent(
        self, baseGlyphName, transformation, location, identifier=None, **kwargs
    ):
        if identifier is not None:
            kwargs["identifier"] = identifier
        self.value.append(
            ("addVarComponent", (baseGlyphName, transformation, location), kwargs)
        )

    def replay(self, pointPen):
        for operator, args, kwargs in self.value:
            getattr(pointPen, operator)(*args, **kwargs)

    drawPoints = replay


class DecomposingRecordingPointPen(DecomposingPointPen, RecordingPointPen):
    """Same as RecordingPointPen, except that it doesn't keep components
    as references, but draws them decomposed as regular contours.

    The constructor takes a required 'glyphSet' positional argument,
    a dictionary of pointPen-drawable glyph objects (i.e. with a 'drawPoints' method)
    keyed by thir name; other arguments are forwarded to the DecomposingPointPen's
    constructor::

        >>> from pprint import pprint
        >>> class SimpleGlyph(object):
        ...     def drawPoints(self, pen):
        ...         pen.beginPath()
        ...         pen.addPoint((0, 0), "line")
        ...         pen.addPoint((1, 1))
        ...         pen.addPoint((2, 2))
        ...         pen.addPoint((3, 3), "curve")
        ...         pen.endPath()
        >>> class CompositeGlyph(object):
        ...     def drawPoints(self, pen):
        ...         pen.addComponent('a', (1, 0, 0, 1, -1, 1))
        >>> class MissingComponent(object):
        ...     def drawPoints(self, pen):
        ...         pen.addComponent('foobar', (1, 0, 0, 1, 0, 0))
        >>> class FlippedComponent(object):
        ...     def drawPoints(self, pen):
        ...         pen.addComponent('a', (-1, 0, 0, 1, 0, 0))
        >>> glyphSet = {
        ...    'a': SimpleGlyph(),
        ...    'b': CompositeGlyph(),
        ...    'c': MissingComponent(),
        ...    'd': FlippedComponent(),
        ... }
        >>> for name, glyph in sorted(glyphSet.items()):
        ...     pen = DecomposingRecordingPointPen(glyphSet)
        ...     try:
        ...         glyph.drawPoints(pen)
        ...     except pen.MissingComponentError:
        ...         pass
        ...     pprint({name: pen.value})
        {'a': [('beginPath', (), {}),
               ('addPoint', ((0, 0), 'line', False, None), {}),
               ('addPoint', ((1, 1), None, False, None), {}),
               ('addPoint', ((2, 2), None, False, None), {}),
               ('addPoint', ((3, 3), 'curve', False, None), {}),
               ('endPath', (), {})]}
        {'b': [('beginPath', (), {}),
               ('addPoint', ((-1, 1), 'line', False, None), {}),
               ('addPoint', ((0, 2), None, False, None), {}),
               ('addPoint', ((1, 3), None, False, None), {}),
               ('addPoint', ((2, 4), 'curve', False, None), {}),
               ('endPath', (), {})]}
        {'c': []}
        {'d': [('beginPath', (), {}),
               ('addPoint', ((0, 0), 'line', False, None), {}),
               ('addPoint', ((-1, 1), None, False, None), {}),
               ('addPoint', ((-2, 2), None, False, None), {}),
               ('addPoint', ((-3, 3), 'curve', False, None), {}),
               ('endPath', (), {})]}

        >>> for name, glyph in sorted(glyphSet.items()):
        ...     pen = DecomposingRecordingPointPen(
        ...         glyphSet, skipMissingComponents=True, reverseFlipped=True,
        ...     )
        ...     glyph.drawPoints(pen)
        ...     pprint({name: pen.value})
        {'a': [('beginPath', (), {}),
               ('addPoint', ((0, 0), 'line', False, None), {}),
               ('addPoint', ((1, 1), None, False, None), {}),
               ('addPoint', ((2, 2), None, False, None), {}),
               ('addPoint', ((3, 3), 'curve', False, None), {}),
               ('endPath', (), {})]}
        {'b': [('beginPath', (), {}),
               ('addPoint', ((-1, 1), 'line', False, None), {}),
               ('addPoint', ((0, 2), None, False, None), {}),
               ('addPoint', ((1, 3), None, False, None), {}),
               ('addPoint', ((2, 4), 'curve', False, None), {}),
               ('endPath', (), {})]}
        {'c': []}
        {'d': [('beginPath', (), {}),
               ('addPoint', ((0, 0), 'curve', False, None), {}),
               ('addPoint', ((-3, 3), 'line', False, None), {}),
               ('addPoint', ((-2, 2), None, False, None), {}),
               ('addPoint', ((-1, 1), None, False, None), {}),
               ('endPath', (), {})]}
    """

    # raises MissingComponentError(KeyError) if base glyph is not found in glyphSet
    skipMissingComponents = False


def lerpRecordings(recording1, recording2, factor=0.5):
    """Linearly interpolate between two recordings. The recordings
    must be decomposed, i.e. they must not contain any components.

    Factor is typically between 0 and 1. 0 means the first recording,
    1 means the second recording, and 0.5 means the average of the
    two recordings. Other values are possible, and can be useful to
    extrapolate. Defaults to 0.5.

    Returns a generator with the new recording.
    """
    if len(recording1) != len(recording2):
        raise ValueError(
            "Mismatched lengths: %d and %d" % (len(recording1), len(recording2))
        )
    for (op1, args1), (op2, args2) in zip(recording1, recording2):
        if op1 != op2:
            raise ValueError("Mismatched operations: %s, %s" % (op1, op2))
        if op1 == "addComponent":
            raise ValueError("Cannot interpolate components")
        else:
            mid_args = [
                (x1 + (x2 - x1) * factor, y1 + (y2 - y1) * factor)
                for (x1, y1), (x2, y2) in zip(args1, args2)
            ]
        yield (op1, mid_args)


if __name__ == "__main__":
    pen = RecordingPen()
    pen.moveTo((0, 0))
    pen.lineTo((0, 100))
    pen.curveTo((50, 75), (60, 50), (50, 25))
    pen.closePath()
    from pprint import pprint

    pprint(pen.value)

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\ttGlyphPen.py ===
from array import array
from typing import Any, Callable, Dict, Optional, Tuple
from fontTools.misc.fixedTools import MAX_F2DOT14, floatToFixedToFloat
from fontTools.misc.loggingTools import LogMixin
from fontTools.pens.pointPen import AbstractPointPen
from fontTools.misc.roundTools import otRound
from fontTools.pens.basePen import LoggingPen, PenError
from fontTools.pens.transformPen import TransformPen, TransformPointPen
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import flagOnCurve, flagCubic
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables._g_l_y_f import GlyphComponent
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables._g_l_y_f import dropImpliedOnCurvePoints
import math


__all__ = ["TTGlyphPen", "TTGlyphPointPen"]


class _TTGlyphBasePen:
    def __init__(
        self,
        glyphSet: Optional[Dict[str, Any]],
        handleOverflowingTransforms: bool = True,
    ) -> None:
        """
        Construct a new pen.

        Args:
            glyphSet (Dict[str, Any]): A glyphset object, used to resolve components.
            handleOverflowingTransforms (bool): See below.

        If ``handleOverflowingTransforms`` is True, the components' transform values
        are checked that they don't overflow the limits of a F2Dot14 number:
        -2.0 <= v < +2.0. If any transform value exceeds these, the composite
        glyph is decomposed.

        An exception to this rule is done for values that are very close to +2.0
        (both for consistency with the -2.0 case, and for the relative frequency
        these occur in real fonts). When almost +2.0 values occur (and all other
        values are within the range -2.0 <= x <= +2.0), they are clamped to the
        maximum positive value that can still be encoded as an F2Dot14: i.e.
        1.99993896484375.

        If False, no check is done and all components are translated unmodified
        into the glyf table, followed by an inevitable ``struct.error`` once an
        attempt is made to compile them.

        If both contours and components are present in a glyph, the components
        are decomposed.
        """
        self.glyphSet = glyphSet
        self.handleOverflowingTransforms = handleOverflowingTransforms
        self.init()

    def _decompose(
        self,
        glyphName: str,
        transformation: Tuple[float, float, float, float, float, float],
    ):
        tpen = self.transformPen(self, transformation)
        getattr(self.glyphSet[glyphName], self.drawMethod)(tpen)

    def _isClosed(self):
        """
        Check if the current path is closed.
        """
        raise NotImplementedError

    def init(self) -> None:
        self.points = []
        self.endPts = []
        self.types = []
        self.components = []

    def addComponent(
        self,
        baseGlyphName: str,
        transformation: Tuple[float, float, float, float, float, float],
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a sub glyph.
        """
        self.components.append((baseGlyphName, transformation))

    def _buildComponents(self, componentFlags):
        if self.handleOverflowingTransforms:
            # we can't encode transform values > 2 or < -2 in F2Dot14,
            # so we must decompose the glyph if any transform exceeds these
            overflowing = any(
                s > 2 or s < -2
                for (glyphName, transformation) in self.components
                for s in transformation[:4]
            )
        components = []
        for glyphName, transformation in self.components:
            if glyphName not in self.glyphSet:
                self.log.warning(f"skipped non-existing component '{glyphName}'")
                continue
            if self.points or (self.handleOverflowingTransforms and overflowing):
                # can't have both coordinates and components, so decompose
                self._decompose(glyphName, transformation)
                continue

            component = GlyphComponent()
            component.glyphName = glyphName
            component.x, component.y = (otRound(v) for v in transformation[4:])
            # quantize floats to F2Dot14 so we get same values as when decompiled
            # from a binary glyf table
            transformation = tuple(
                floatToFixedToFloat(v, 14) for v in transformation[:4]
            )
            if transformation != (1, 0, 0, 1):
                if self.handleOverflowingTransforms and any(
                    MAX_F2DOT14 < s <= 2 for s in transformation
                ):
                    # clamp values ~= +2.0 so we can keep the component
                    transformation = tuple(
                        MAX_F2DOT14 if MAX_F2DOT14 < s <= 2 else s
                        for s in transformation
                    )
                component.transform = (transformation[:2], transformation[2:])
            component.flags = componentFlags
            components.append(component)
        return components

    def glyph(
        self,
        componentFlags: int = 0x04,
        dropImpliedOnCurves: bool = False,
        *,
        round: Callable[[float], int] = otRound,
    ) -> Glyph:
        """
        Returns a :py:class:`~._g_l_y_f.Glyph` object representing the glyph.

        Args:
            componentFlags: Flags to use for component glyphs. (default: 0x04)

            dropImpliedOnCurves: Whether to remove implied-oncurve points. (default: False)
        """
        if not self._isClosed():
            raise PenError("Didn't close last contour.")
        components = self._buildComponents(componentFlags)

        glyph = Glyph()
        glyph.coordinates = GlyphCoordinates(self.points)
        glyph.endPtsOfContours = self.endPts
        glyph.flags = array("B", self.types)
        self.init()

        if components:
            # If both components and contours were present, they have by now
            # been decomposed by _buildComponents.
            glyph.components = components
            glyph.numberOfContours = -1
        else:
            glyph.numberOfContours = len(glyph.endPtsOfContours)
            glyph.program = ttProgram.Program()
            glyph.program.fromBytecode(b"")
            if dropImpliedOnCurves:
                dropImpliedOnCurvePoints(glyph)
            glyph.coordinates.toInt(round=round)

        return glyph


class TTGlyphPen(_TTGlyphBasePen, LoggingPen):
    """
    Pen used for drawing to a TrueType glyph.

    This pen can be used to construct or modify glyphs in a TrueType format
    font. After using the pen to draw, use the ``.glyph()`` method to retrieve
    a :py:class:`~._g_l_y_f.Glyph` object representing the glyph.
    """

    drawMethod = "draw"
    transformPen = TransformPen

    def __init__(
        self,
        glyphSet: Optional[Dict[str, Any]] = None,
        handleOverflowingTransforms: bool = True,
        outputImpliedClosingLine: bool = False,
    ) -> None:
        super().__init__(glyphSet, handleOverflowingTransforms)
        self.outputImpliedClosingLine = outputImpliedClosingLine

    def _addPoint(self, pt: Tuple[float, float], tp: int) -> None:
        self.points.append(pt)
        self.types.append(tp)

    def _popPoint(self) -> None:
        self.points.pop()
        self.types.pop()

    def _isClosed(self) -> bool:
        return (not self.points) or (
            self.endPts and self.endPts[-1] == len(self.points) - 1
        )

    def lineTo(self, pt: Tuple[float, float]) -> None:
        self._addPoint(pt, flagOnCurve)

    def moveTo(self, pt: Tuple[float, float]) -> None:
        if not self._isClosed():
            raise PenError('"move"-type point must begin a new contour.')
        self._addPoint(pt, flagOnCurve)

    def curveTo(self, *points) -> None:
        assert len(points) % 2 == 1
        for pt in points[:-1]:
            self._addPoint(pt, flagCubic)

        # last point is None if there are no on-curve points
        if points[-1] is not None:
            self._addPoint(points[-1], 1)

    def qCurveTo(self, *points) -> None:
        assert len(points) >= 1
        for pt in points[:-1]:
            self._addPoint(pt, 0)

        # last point is None if there are no on-curve points
        if points[-1] is not None:
            self._addPoint(points[-1], 1)

    def closePath(self) -> None:
        endPt = len(self.points) - 1

        # ignore anchors (one-point paths)
        if endPt == 0 or (self.endPts and endPt == self.endPts[-1] + 1):
            self._popPoint()
            return

        if not self.outputImpliedClosingLine:
            # if first and last point on this path are the same, remove last
            startPt = 0
            if self.endPts:
                startPt = self.endPts[-1] + 1
            if self.points[startPt] == self.points[endPt]:
                self._popPoint()
                endPt -= 1

        self.endPts.append(endPt)

    def endPath(self) -> None:
        # TrueType contours are always "closed"
        self.closePath()


class TTGlyphPointPen(_TTGlyphBasePen, LogMixin, AbstractPointPen):
    """
    Point pen used for drawing to a TrueType glyph.

    This pen can be used to construct or modify glyphs in a TrueType format
    font. After using the pen to draw, use the ``.glyph()`` method to retrieve
    a :py:class:`~._g_l_y_f.Glyph` object representing the glyph.
    """

    drawMethod = "drawPoints"
    transformPen = TransformPointPen

    def init(self) -> None:
        super().init()
        self._currentContourStartIndex = None

    def _isClosed(self) -> bool:
        return self._currentContourStartIndex is None

    def beginPath(self, identifier: Optional[str] = None, **kwargs: Any) -> None:
        """
        Start a new sub path.
        """
        if not self._isClosed():
            raise PenError("Didn't close previous contour.")
        self._currentContourStartIndex = len(self.points)

    def endPath(self) -> None:
        """
        End the current sub path.
        """
        # TrueType contours are always "closed"
        if self._isClosed():
            raise PenError("Contour is already closed.")
        if self._currentContourStartIndex == len(self.points):
            # ignore empty contours
            self._currentContourStartIndex = None
            return

        contourStart = self.endPts[-1] + 1 if self.endPts else 0
        self.endPts.append(len(self.points) - 1)
        self._currentContourStartIndex = None

        # Resolve types for any cubic segments
        flags = self.types
        for i in range(contourStart, len(flags)):
            if flags[i] == "curve":
                j = i - 1
                if j < contourStart:
                    j = len(flags) - 1
                while flags[j] == 0:
                    flags[j] = flagCubic
                    j -= 1
                flags[i] = flagOnCurve

    def addPoint(
        self,
        pt: Tuple[float, float],
        segmentType: Optional[str] = None,
        smooth: bool = False,
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Add a point to the current sub path.
        """
        if self._isClosed():
            raise PenError("Can't add a point to a closed contour.")
        if segmentType is None:
            self.types.append(0)
        elif segmentType in ("line", "move"):
            self.types.append(flagOnCurve)
        elif segmentType == "qcurve":
            self.types.append(flagOnCurve)
        elif segmentType == "curve":
            self.types.append("curve")
        else:
            raise AssertionError(segmentType)

        self.points.append(pt)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\arguments.py ===
import re
from itertools import zip_longest

from parso.python import tree

from jedi import debug
from jedi.inference.utils import PushBackIterator
from jedi.inference import analysis
from jedi.inference.lazy_value import LazyKnownValue, LazyKnownValues, \
    LazyTreeValue, get_merged_lazy_value
from jedi.inference.names import ParamName, TreeNameDefinition, AnonymousParamName
from jedi.inference.base_value import NO_VALUES, ValueSet, ContextualizedNode
from jedi.inference.value import iterable
from jedi.inference.cache import inference_state_as_method_param_cache


def try_iter_content(types, depth=0):
    """Helper method for static analysis."""
    if depth > 10:
        # It's possible that a loop has references on itself (especially with
        # CompiledValue). Therefore don't loop infinitely.
        return

    for typ in types:
        try:
            f = typ.py__iter__
        except AttributeError:
            pass
        else:
            for lazy_value in f():
                try_iter_content(lazy_value.infer(), depth + 1)


class ParamIssue(Exception):
    pass


def repack_with_argument_clinic(clinic_string):
    """
    Transforms a function or method with arguments to the signature that is
    given as an argument clinic notation.

    Argument clinic is part of CPython and used for all the functions that are
    implemented in C (Python 3.7):

        str.split.__text_signature__
        # Results in: '($self, /, sep=None, maxsplit=-1)'
    """
    def decorator(func):
        def wrapper(value, arguments):
            try:
                args = tuple(iterate_argument_clinic(
                    value.inference_state,
                    arguments,
                    clinic_string,
                ))
            except ParamIssue:
                return NO_VALUES
            else:
                return func(value, *args)

        return wrapper
    return decorator


def iterate_argument_clinic(inference_state, arguments, clinic_string):
    """Uses a list with argument clinic information (see PEP 436)."""
    clinic_args = list(_parse_argument_clinic(clinic_string))

    iterator = PushBackIterator(arguments.unpack())
    for i, (name, optional, allow_kwargs, stars) in enumerate(clinic_args):
        if stars == 1:
            lazy_values = []
            for key, argument in iterator:
                if key is not None:
                    iterator.push_back((key, argument))
                    break

                lazy_values.append(argument)
            yield ValueSet([iterable.FakeTuple(inference_state, lazy_values)])
            lazy_values
            continue
        elif stars == 2:
            raise NotImplementedError()
        key, argument = next(iterator, (None, None))
        if key is not None:
            debug.warning('Keyword arguments in argument clinic are currently not supported.')
            raise ParamIssue
        if argument is None and not optional:
            debug.warning('TypeError: %s expected at least %s arguments, got %s',
                          name, len(clinic_args), i)
            raise ParamIssue

        value_set = NO_VALUES if argument is None else argument.infer()

        if not value_set and not optional:
            # For the stdlib we always want values. If we don't get them,
            # that's ok, maybe something is too hard to resolve, however,
            # we will not proceed with the type inference of that function.
            debug.warning('argument_clinic "%s" not resolvable.', name)
            raise ParamIssue
        yield value_set


def _parse_argument_clinic(string):
    allow_kwargs = False
    optional = False
    while string:
        # Optional arguments have to begin with a bracket. And should always be
        # at the end of the arguments. This is therefore not a proper argument
        # clinic implementation. `range()` for exmple allows an optional start
        # value at the beginning.
        match = re.match(r'(?:(?:(\[),? ?|, ?|)(\**\w+)|, ?/)\]*', string)
        string = string[len(match.group(0)):]
        if not match.group(2):  # A slash -> allow named arguments
            allow_kwargs = True
            continue
        optional = optional or bool(match.group(1))
        word = match.group(2)
        stars = word.count('*')
        word = word[stars:]
        yield (word, optional, allow_kwargs, stars)
        if stars:
            allow_kwargs = True


class _AbstractArgumentsMixin:
    def unpack(self, funcdef=None):
        raise NotImplementedError

    def get_calling_nodes(self):
        return []


class AbstractArguments(_AbstractArgumentsMixin):
    context = None
    argument_node = None
    trailer = None


def unpack_arglist(arglist):
    if arglist is None:
        return

    if arglist.type != 'arglist' and not (
            arglist.type == 'argument' and arglist.children[0] in ('*', '**')):
        yield 0, arglist
        return

    iterator = iter(arglist.children)
    for child in iterator:
        if child == ',':
            continue
        elif child in ('*', '**'):
            c = next(iterator, None)
            assert c is not None
            yield len(child.value), c
        elif child.type == 'argument' and \
                child.children[0] in ('*', '**'):
            assert len(child.children) == 2
            yield len(child.children[0].value), child.children[1]
        else:
            yield 0, child


class TreeArguments(AbstractArguments):
    def __init__(self, inference_state, context, argument_node, trailer=None):
        """
        :param argument_node: May be an argument_node or a list of nodes.
        """
        self.argument_node = argument_node
        self.context = context
        self._inference_state = inference_state
        self.trailer = trailer  # Can be None, e.g. in a class definition.

    @classmethod
    @inference_state_as_method_param_cache()
    def create_cached(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    def unpack(self, funcdef=None):
        named_args = []
        for star_count, el in unpack_arglist(self.argument_node):
            if star_count == 1:
                arrays = self.context.infer_node(el)
                iterators = [_iterate_star_args(self.context, a, el, funcdef)
                             for a in arrays]
                for values in list(zip_longest(*iterators)):
                    yield None, get_merged_lazy_value(
                        [v for v in values if v is not None]
                    )
            elif star_count == 2:
                arrays = self.context.infer_node(el)
                for dct in arrays:
                    yield from _star_star_dict(self.context, dct, el, funcdef)
            else:
                if el.type == 'argument':
                    c = el.children
                    if len(c) == 3:  # Keyword argument.
                        named_args.append((c[0].value, LazyTreeValue(self.context, c[2]),))
                    else:  # Generator comprehension.
                        # Include the brackets with the parent.
                        sync_comp_for = el.children[1]
                        if sync_comp_for.type == 'comp_for':
                            sync_comp_for = sync_comp_for.children[1]
                        comp = iterable.GeneratorComprehension(
                            self._inference_state,
                            defining_context=self.context,
                            sync_comp_for_node=sync_comp_for,
                            entry_node=el.children[0],
                        )
                        yield None, LazyKnownValue(comp)
                else:
                    yield None, LazyTreeValue(self.context, el)

        # Reordering arguments is necessary, because star args sometimes appear
        # after named argument, but in the actual order it's prepended.
        yield from named_args

    def _as_tree_tuple_objects(self):
        for star_count, argument in unpack_arglist(self.argument_node):
            default = None
            if argument.type == 'argument':
                if len(argument.children) == 3:  # Keyword argument.
                    argument, default = argument.children[::2]
            yield argument, default, star_count

    def iter_calling_names_with_star(self):
        for name, default, star_count in self._as_tree_tuple_objects():
            # TODO this function is a bit strange. probably refactor?
            if not star_count or not isinstance(name, tree.Name):
                continue

            yield TreeNameDefinition(self.context, name)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.argument_node)

    def get_calling_nodes(self):
        old_arguments_list = []
        arguments = self

        while arguments not in old_arguments_list:
            if not isinstance(arguments, TreeArguments):
                break

            old_arguments_list.append(arguments)
            for calling_name in reversed(list(arguments.iter_calling_names_with_star())):
                names = calling_name.goto()
                if len(names) != 1:
                    break
                if isinstance(names[0], AnonymousParamName):
                    # Dynamic parameters should not have calling nodes, because
                    # they are dynamic and extremely random.
                    return []
                if not isinstance(names[0], ParamName):
                    break
                executed_param_name = names[0].get_executed_param_name()
                arguments = executed_param_name.arguments
                break

        if arguments.argument_node is not None:
            return [ContextualizedNode(arguments.context, arguments.argument_node)]
        if arguments.trailer is not None:
            return [ContextualizedNode(arguments.context, arguments.trailer)]
        return []


class ValuesArguments(AbstractArguments):
    def __init__(self, values_list):
        self._values_list = values_list

    def unpack(self, funcdef=None):
        for values in self._values_list:
            yield None, LazyKnownValues(values)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._values_list)


class TreeArgumentsWrapper(_AbstractArgumentsMixin):
    def __init__(self, arguments):
        self._wrapped_arguments = arguments

    @property
    def context(self):
        return self._wrapped_arguments.context

    @property
    def argument_node(self):
        return self._wrapped_arguments.argument_node

    @property
    def trailer(self):
        return self._wrapped_arguments.trailer

    def unpack(self, func=None):
        raise NotImplementedError

    def get_calling_nodes(self):
        return self._wrapped_arguments.get_calling_nodes()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._wrapped_arguments)


def _iterate_star_args(context, array, input_node, funcdef=None):
    if not array.py__getattribute__('__iter__'):
        if funcdef is not None:
            # TODO this funcdef should not be needed.
            m = "TypeError: %s() argument after * must be a sequence, not %s" \
                % (funcdef.name.value, array)
            analysis.add(context, 'type-error-star', input_node, message=m)
    try:
        iter_ = array.py__iter__
    except AttributeError:
        pass
    else:
        yield from iter_()


def _star_star_dict(context, array, input_node, funcdef):
    from jedi.inference.value.instance import CompiledInstance
    if isinstance(array, CompiledInstance) and array.name.string_name == 'dict':
        # For now ignore this case. In the future add proper iterators and just
        # make one call without crazy isinstance checks.
        return {}
    elif isinstance(array, iterable.Sequence) and array.array_type == 'dict':
        return array.exact_key_items()
    else:
        if funcdef is not None:
            m = "TypeError: %s argument after ** must be a mapping, not %s" \
                % (funcdef.name.value, array)
            analysis.add(context, 'type-error-star-star', input_node, message=m)
        return {}

# === NexusCore/openenv\Lib\site-packages\nltk\translate\api.py ===
# Natural Language Toolkit: API for alignment and translation objects
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Will Zhang <wilzzha@gmail.com>
#         Guan Gui <ggui@student.unimelb.edu.au>
#         Steven Bird <stevenbird1@gmail.com>
#         Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import subprocess
from collections import namedtuple


class AlignedSent:
    """
    Return an aligned sentence object, which encapsulates two sentences
    along with an ``Alignment`` between them.

    Typically used in machine translation to represent a sentence and
    its translation.

        >>> from nltk.translate import AlignedSent, Alignment
        >>> algnsent = AlignedSent(['klein', 'ist', 'das', 'Haus'],
        ...     ['the', 'house', 'is', 'small'], Alignment.fromstring('0-3 1-2 2-0 3-1'))
        >>> algnsent.words
        ['klein', 'ist', 'das', 'Haus']
        >>> algnsent.mots
        ['the', 'house', 'is', 'small']
        >>> algnsent.alignment
        Alignment([(0, 3), (1, 2), (2, 0), (3, 1)])
        >>> from nltk.corpus import comtrans
        >>> print(comtrans.aligned_sents()[54])
        <AlignedSent: 'Weshalb also sollten...' -> 'So why should EU arm...'>
        >>> print(comtrans.aligned_sents()[54].alignment)
        0-0 0-1 1-0 2-2 3-4 3-5 4-7 5-8 6-3 7-9 8-9 9-10 9-11 10-12 11-6 12-6 13-13

    :param words: Words in the target language sentence
    :type words: list(str)
    :param mots: Words in the source language sentence
    :type mots: list(str)
    :param alignment: Word-level alignments between ``words`` and ``mots``.
        Each alignment is represented as a 2-tuple (words_index, mots_index).
    :type alignment: Alignment
    """

    def __init__(self, words, mots, alignment=None):
        self._words = words
        self._mots = mots
        if alignment is None:
            self.alignment = Alignment([])
        else:
            assert type(alignment) is Alignment
            self.alignment = alignment

    @property
    def words(self):
        return self._words

    @property
    def mots(self):
        return self._mots

    def _get_alignment(self):
        return self._alignment

    def _set_alignment(self, alignment):
        _check_alignment(len(self.words), len(self.mots), alignment)
        self._alignment = alignment

    alignment = property(_get_alignment, _set_alignment)

    def __repr__(self):
        """
        Return a string representation for this ``AlignedSent``.

        :rtype: str
        """
        words = "[%s]" % (", ".join("'%s'" % w for w in self._words))
        mots = "[%s]" % (", ".join("'%s'" % w for w in self._mots))

        return f"AlignedSent({words}, {mots}, {self._alignment!r})"

    def _to_dot(self):
        """
        Dot representation of the aligned sentence
        """
        s = "graph align {\n"
        s += "node[shape=plaintext]\n"

        # Declare node
        s += "".join([f'"{w}_source" [label="{w}"] \n' for w in self._words])
        s += "".join([f'"{w}_target" [label="{w}"] \n' for w in self._mots])

        # Alignment
        s += "".join(
            [
                f'"{self._words[u]}_source" -- "{self._mots[v]}_target" \n'
                for u, v in self._alignment
            ]
        )

        # Connect the source words
        for i in range(len(self._words) - 1):
            s += '"{}_source" -- "{}_source" [style=invis]\n'.format(
                self._words[i],
                self._words[i + 1],
            )

        # Connect the target words
        for i in range(len(self._mots) - 1):
            s += '"{}_target" -- "{}_target" [style=invis]\n'.format(
                self._mots[i],
                self._mots[i + 1],
            )

        # Put it in the same rank
        s += "{rank = same; %s}\n" % (" ".join('"%s_source"' % w for w in self._words))
        s += "{rank = same; %s}\n" % (" ".join('"%s_target"' % w for w in self._mots))

        s += "}"

        return s

    def _repr_svg_(self):
        """
        Ipython magic : show SVG representation of this ``AlignedSent``.
        """
        dot_string = self._to_dot().encode("utf8")
        output_format = "svg"
        try:
            process = subprocess.Popen(
                ["dot", "-T%s" % output_format],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as e:
            raise Exception("Cannot find the dot binary from Graphviz package") from e
        out, err = process.communicate(dot_string)

        return out.decode("utf8")

    def __str__(self):
        """
        Return a human-readable string representation for this ``AlignedSent``.

        :rtype: str
        """
        source = " ".join(self._words)[:20] + "..."
        target = " ".join(self._mots)[:20] + "..."
        return f"<AlignedSent: '{source}' -> '{target}'>"

    def invert(self):
        """
        Return the aligned sentence pair, reversing the directionality

        :rtype: AlignedSent
        """
        return AlignedSent(self._mots, self._words, self._alignment.invert())


class Alignment(frozenset):
    """
    A storage class for representing alignment between two sequences, s1, s2.
    In general, an alignment is a set of tuples of the form (i, j, ...)
    representing an alignment between the i-th element of s1 and the
    j-th element of s2.  Tuples are extensible (they might contain
    additional data, such as a boolean to indicate sure vs possible alignments).

        >>> from nltk.translate import Alignment
        >>> a = Alignment([(0, 0), (0, 1), (1, 2), (2, 2)])
        >>> a.invert()
        Alignment([(0, 0), (1, 0), (2, 1), (2, 2)])
        >>> print(a.invert())
        0-0 1-0 2-1 2-2
        >>> a[0]
        [(0, 1), (0, 0)]
        >>> a.invert()[2]
        [(2, 1), (2, 2)]
        >>> b = Alignment([(0, 0), (0, 1)])
        >>> b.issubset(a)
        True
        >>> c = Alignment.fromstring('0-0 0-1')
        >>> b == c
        True
    """

    def __new__(cls, pairs):
        self = frozenset.__new__(cls, pairs)
        self._len = max(p[0] for p in self) if self != frozenset([]) else 0
        self._index = None
        return self

    @classmethod
    def fromstring(cls, s):
        """
        Read a giza-formatted string and return an Alignment object.

            >>> Alignment.fromstring('0-0 2-1 9-2 21-3 10-4 7-5')
            Alignment([(0, 0), (2, 1), (7, 5), (9, 2), (10, 4), (21, 3)])

        :type s: str
        :param s: the positional alignments in giza format
        :rtype: Alignment
        :return: An Alignment object corresponding to the string representation ``s``.
        """

        return Alignment([_giza2pair(a) for a in s.split()])

    def __getitem__(self, key):
        """
        Look up the alignments that map from a given index or slice.
        """
        if not self._index:
            self._build_index()
        return self._index.__getitem__(key)

    def invert(self):
        """
        Return an Alignment object, being the inverted mapping.
        """
        return Alignment(((p[1], p[0]) + p[2:]) for p in self)

    def range(self, positions=None):
        """
        Work out the range of the mapping from the given positions.
        If no positions are specified, compute the range of the entire mapping.
        """
        image = set()
        if not self._index:
            self._build_index()
        if not positions:
            positions = list(range(len(self._index)))
        for p in positions:
            image.update(f for _, f in self._index[p])
        return sorted(image)

    def __repr__(self):
        """
        Produce a Giza-formatted string representing the alignment.
        """
        return "Alignment(%r)" % sorted(self)

    def __str__(self):
        """
        Produce a Giza-formatted string representing the alignment.
        """
        return " ".join("%d-%d" % p[:2] for p in sorted(self))

    def _build_index(self):
        """
        Build a list self._index such that self._index[i] is a list
        of the alignments originating from word i.
        """
        self._index = [[] for _ in range(self._len + 1)]
        for p in self:
            self._index[p[0]].append(p)


def _giza2pair(pair_string):
    i, j = pair_string.split("-")
    return int(i), int(j)


def _naacl2pair(pair_string):
    i, j, p = pair_string.split("-")
    return int(i), int(j)


def _check_alignment(num_words, num_mots, alignment):
    """
    Check whether the alignments are legal.

    :param num_words: the number of source language words
    :type num_words: int
    :param num_mots: the number of target language words
    :type num_mots: int
    :param alignment: alignment to be checked
    :type alignment: Alignment
    :raise IndexError: if alignment falls outside the sentence
    """

    assert type(alignment) is Alignment

    if not all(0 <= pair[0] < num_words for pair in alignment):
        raise IndexError("Alignment is outside boundary of words")
    if not all(pair[1] is None or 0 <= pair[1] < num_mots for pair in alignment):
        raise IndexError("Alignment is outside boundary of mots")


PhraseTableEntry = namedtuple("PhraseTableEntry", ["trg_phrase", "log_prob"])


class PhraseTable:
    """
    In-memory store of translations for a given phrase, and the log
    probability of the those translations
    """

    def __init__(self):
        self.src_phrases = dict()

    def translations_for(self, src_phrase):
        """
        Get the translations for a source language phrase

        :param src_phrase: Source language phrase of interest
        :type src_phrase: tuple(str)

        :return: A list of target language phrases that are translations
            of ``src_phrase``, ordered in decreasing order of
            likelihood. Each list element is a tuple of the target
            phrase and its log probability.
        :rtype: list(PhraseTableEntry)
        """
        return self.src_phrases[src_phrase]

    def add(self, src_phrase, trg_phrase, log_prob):
        """
        :type src_phrase: tuple(str)
        :type trg_phrase: tuple(str)

        :param log_prob: Log probability that given ``src_phrase``,
            ``trg_phrase`` is its translation
        :type log_prob: float
        """
        entry = PhraseTableEntry(trg_phrase=trg_phrase, log_prob=log_prob)
        if src_phrase not in self.src_phrases:
            self.src_phrases[src_phrase] = []
        self.src_phrases[src_phrase].append(entry)
        self.src_phrases[src_phrase].sort(key=lambda e: e.log_prob, reverse=True)

    def __contains__(self, src_phrase):
        return src_phrase in self.src_phrases

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\tag.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
from pyasn1 import error

__all__ = ['tagClassUniversal', 'tagClassApplication', 'tagClassContext',
           'tagClassPrivate', 'tagFormatSimple', 'tagFormatConstructed',
           'tagCategoryImplicit', 'tagCategoryExplicit',
           'tagCategoryUntagged', 'Tag', 'TagSet']

#: Identifier for ASN.1 class UNIVERSAL
tagClassUniversal = 0x00

#: Identifier for ASN.1 class APPLICATION
tagClassApplication = 0x40

#: Identifier for ASN.1 class context-specific
tagClassContext = 0x80

#: Identifier for ASN.1 class private
tagClassPrivate = 0xC0

#: Identifier for "simple" ASN.1 structure (e.g. scalar)
tagFormatSimple = 0x00

#: Identifier for "constructed" ASN.1 structure (e.g. may have inner components)
tagFormatConstructed = 0x20

tagCategoryImplicit = 0x01
tagCategoryExplicit = 0x02
tagCategoryUntagged = 0x04


class Tag(object):
    """Create ASN.1 tag

    Represents ASN.1 tag that can be attached to a ASN.1 type to make
    types distinguishable from each other.

    *Tag* objects are immutable and duck-type Python :class:`tuple` objects
    holding three integer components of a tag.

    Parameters
    ----------
    tagClass: :py:class:`int`
        Tag *class* value

    tagFormat: :py:class:`int`
        Tag *format* value

    tagId: :py:class:`int`
        Tag ID value
    """
    def __init__(self, tagClass, tagFormat, tagId):
        if tagId < 0:
            raise error.PyAsn1Error('Negative tag ID (%s) not allowed' % tagId)
        self.__tagClass = tagClass
        self.__tagFormat = tagFormat
        self.__tagId = tagId
        self.__tagClassId = tagClass, tagId
        self.__hash = hash(self.__tagClassId)

    def __repr__(self):
        representation = '[%s:%s:%s]' % (
            self.__tagClass, self.__tagFormat, self.__tagId)
        return '<%s object, tag %s>' % (
            self.__class__.__name__, representation)

    def __eq__(self, other):
        return self.__tagClassId == other

    def __ne__(self, other):
        return self.__tagClassId != other

    def __lt__(self, other):
        return self.__tagClassId < other

    def __le__(self, other):
        return self.__tagClassId <= other

    def __gt__(self, other):
        return self.__tagClassId > other

    def __ge__(self, other):
        return self.__tagClassId >= other

    def __hash__(self):
        return self.__hash

    def __getitem__(self, idx):
        if idx == 0:
            return self.__tagClass
        elif idx == 1:
            return self.__tagFormat
        elif idx == 2:
            return self.__tagId
        else:
            raise IndexError

    def __iter__(self):
        yield self.__tagClass
        yield self.__tagFormat
        yield self.__tagId

    def __and__(self, otherTag):
        return self.__class__(self.__tagClass & otherTag.tagClass,
                              self.__tagFormat & otherTag.tagFormat,
                              self.__tagId & otherTag.tagId)

    def __or__(self, otherTag):
        return self.__class__(self.__tagClass | otherTag.tagClass,
                              self.__tagFormat | otherTag.tagFormat,
                              self.__tagId | otherTag.tagId)

    @property
    def tagClass(self):
        """ASN.1 tag class

        Returns
        -------
        : :py:class:`int`
            Tag class
        """
        return self.__tagClass

    @property
    def tagFormat(self):
        """ASN.1 tag format

        Returns
        -------
        : :py:class:`int`
            Tag format
        """
        return self.__tagFormat

    @property
    def tagId(self):
        """ASN.1 tag ID

        Returns
        -------
        : :py:class:`int`
            Tag ID
        """
        return self.__tagId


class TagSet(object):
    """Create a collection of ASN.1 tags

    Represents a combination of :class:`~pyasn1.type.tag.Tag` objects
    that can be attached to a ASN.1 type to make types distinguishable
    from each other.

    *TagSet* objects are immutable and duck-type Python :class:`tuple` objects
    holding arbitrary number of :class:`~pyasn1.type.tag.Tag` objects.

    Parameters
    ----------
    baseTag: :class:`~pyasn1.type.tag.Tag`
        Base *Tag* object. This tag survives IMPLICIT tagging.

    *superTags: :class:`~pyasn1.type.tag.Tag`
        Additional *Tag* objects taking part in subtyping.

    Examples
    --------
    .. code-block:: python

        class OrderNumber(NumericString):
            '''
            ASN.1 specification

            Order-number ::=
                [APPLICATION 5] IMPLICIT NumericString
            '''
            tagSet = NumericString.tagSet.tagImplicitly(
                Tag(tagClassApplication, tagFormatSimple, 5)
            )

        orderNumber = OrderNumber('1234')
    """
    def __init__(self, baseTag=(), *superTags):
        self.__baseTag = baseTag
        self.__superTags = superTags
        self.__superTagsClassId = tuple(
            [(superTag.tagClass, superTag.tagId) for superTag in superTags]
        )
        self.__lenOfSuperTags = len(superTags)
        self.__hash = hash(self.__superTagsClassId)

    def __repr__(self):
        representation = '-'.join(['%s:%s:%s' % (x.tagClass, x.tagFormat, x.tagId)
                                   for x in self.__superTags])
        if representation:
            representation = 'tags ' + representation
        else:
            representation = 'untagged'

        return '<%s object, %s>' % (self.__class__.__name__, representation)

    def __add__(self, superTag):
        return self.__class__(self.__baseTag, *self.__superTags + (superTag,))

    def __radd__(self, superTag):
        return self.__class__(self.__baseTag, *(superTag,) + self.__superTags)

    def __getitem__(self, i):
        if i.__class__ is slice:
            return self.__class__(self.__baseTag, *self.__superTags[i])
        else:
            return self.__superTags[i]

    def __eq__(self, other):
        return self.__superTagsClassId == other

    def __ne__(self, other):
        return self.__superTagsClassId != other

    def __lt__(self, other):
        return self.__superTagsClassId < other

    def __le__(self, other):
        return self.__superTagsClassId <= other

    def __gt__(self, other):
        return self.__superTagsClassId > other

    def __ge__(self, other):
        return self.__superTagsClassId >= other

    def __hash__(self):
        return self.__hash

    def __len__(self):
        return self.__lenOfSuperTags

    @property
    def baseTag(self):
        """Return base ASN.1 tag

        Returns
        -------
        : :class:`~pyasn1.type.tag.Tag`
            Base tag of this *TagSet*
        """
        return self.__baseTag

    @property
    def superTags(self):
        """Return ASN.1 tags

        Returns
        -------
        : :py:class:`tuple`
            Tuple of :class:`~pyasn1.type.tag.Tag` objects that this *TagSet* contains
        """
        return self.__superTags

    def tagExplicitly(self, superTag):
        """Return explicitly tagged *TagSet*

        Create a new *TagSet* representing callee *TagSet* explicitly tagged
        with passed tag(s). With explicit tagging mode, new tags are appended
        to existing tag(s).

        Parameters
        ----------
        superTag: :class:`~pyasn1.type.tag.Tag`
            *Tag* object to tag this *TagSet*

        Returns
        -------
        : :class:`~pyasn1.type.tag.TagSet`
            New *TagSet* object
        """
        if superTag.tagClass == tagClassUniversal:
            raise error.PyAsn1Error("Can't tag with UNIVERSAL class tag")
        if superTag.tagFormat != tagFormatConstructed:
            superTag = Tag(superTag.tagClass, tagFormatConstructed, superTag.tagId)
        return self + superTag

    def tagImplicitly(self, superTag):
        """Return implicitly tagged *TagSet*

        Create a new *TagSet* representing callee *TagSet* implicitly tagged
        with passed tag(s). With implicit tagging mode, new tag(s) replace the
        last existing tag.

        Parameters
        ----------
        superTag: :class:`~pyasn1.type.tag.Tag`
            *Tag* object to tag this *TagSet*

        Returns
        -------
        : :class:`~pyasn1.type.tag.TagSet`
            New *TagSet* object
        """
        if self.__superTags:
            superTag = Tag(superTag.tagClass, self.__superTags[-1].tagFormat, superTag.tagId)
        return self[:-1] + superTag

    def isSuperTagSetOf(self, tagSet):
        """Test type relationship against given *TagSet*

        The callee is considered to be a supertype of given *TagSet*
        tag-wise if all tags in *TagSet* are present in the callee and
        they are in the same order.

        Parameters
        ----------
        tagSet: :class:`~pyasn1.type.tag.TagSet`
            *TagSet* object to evaluate against the callee

        Returns
        -------
        : :py:class:`bool`
            :obj:`True` if callee is a supertype of *tagSet*
        """
        if len(tagSet) < self.__lenOfSuperTags:
            return False
        return self.__superTags == tagSet[:self.__lenOfSuperTags]

    # Backward compatibility

    def getBaseTag(self):
        return self.__baseTag

def initTagSet(tag):
    return TagSet(tag, tag)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\gcs_bucket\gcs_bucket_base.py ===
import json
import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from litellm._logging import verbose_logger
from litellm.integrations.custom_batch_logger import CustomBatchLogger
from litellm.llms.custom_httpx.http_handler import (
    get_async_httpx_client,
    httpxSpecialProvider,
)
from litellm.types.integrations.gcs_bucket import *
from litellm.types.utils import StandardCallbackDynamicParams, StandardLoggingPayload

if TYPE_CHECKING:
    from litellm.llms.vertex_ai.vertex_llm_base import VertexBase
else:
    VertexBase = Any
IAM_AUTH_KEY = "IAM_AUTH"


class GCSBucketBase(CustomBatchLogger):
    def __init__(self, bucket_name: Optional[str] = None, **kwargs) -> None:
        self.async_httpx_client = get_async_httpx_client(
            llm_provider=httpxSpecialProvider.LoggingCallback
        )
        _path_service_account = os.getenv("GCS_PATH_SERVICE_ACCOUNT")
        _bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
        self.path_service_account_json: Optional[str] = _path_service_account
        self.BUCKET_NAME: Optional[str] = _bucket_name
        self.vertex_instances: Dict[str, VertexBase] = {}
        super().__init__(**kwargs)

    async def construct_request_headers(
        self,
        service_account_json: Optional[str],
        vertex_instance: Optional[VertexBase] = None,
    ) -> Dict[str, str]:
        from litellm import vertex_chat_completion

        if vertex_instance is None:
            vertex_instance = vertex_chat_completion

        _auth_header, vertex_project = await vertex_instance._ensure_access_token_async(
            credentials=service_account_json,
            project_id=None,
            custom_llm_provider="vertex_ai",
        )

        auth_header, _ = vertex_instance._get_token_and_url(
            model="gcs-bucket",
            auth_header=_auth_header,
            vertex_credentials=service_account_json,
            vertex_project=vertex_project,
            vertex_location=None,
            gemini_api_key=None,
            stream=None,
            custom_llm_provider="vertex_ai",
            api_base=None,
        )
        verbose_logger.debug("constructed auth_header %s", auth_header)
        headers = {
            "Authorization": f"Bearer {auth_header}",  # auth_header
            "Content-Type": "application/json",
        }

        return headers

    def sync_construct_request_headers(self) -> Dict[str, str]:
        """
        Construct request headers for GCS API calls
        """
        from litellm import vertex_chat_completion

        # Get project_id from environment if available, otherwise None
        # This helps support use of this library to auth to pull secrets 
        # from Secret Manager.
        project_id = os.getenv("GOOGLE_SECRET_MANAGER_PROJECT_ID")
        
        _auth_header, vertex_project = vertex_chat_completion._ensure_access_token(
            credentials=self.path_service_account_json,
            project_id=project_id,
            custom_llm_provider="vertex_ai",
        )

        auth_header, _ = vertex_chat_completion._get_token_and_url(
            model="gcs-bucket",
            auth_header=_auth_header,
            vertex_credentials=self.path_service_account_json,
            vertex_project=vertex_project,
            vertex_location=None,
            gemini_api_key=None,
            stream=None,
            custom_llm_provider="vertex_ai",
            api_base=None,
        )
        verbose_logger.debug("constructed auth_header %s", auth_header)
        headers = {
            "Authorization": f"Bearer {auth_header}",  # auth_header
            "Content-Type": "application/json",
        }

        return headers

    def _handle_folders_in_bucket_name(
        self,
        bucket_name: str,
        object_name: str,
    ) -> Tuple[str, str]:
        """
        Handles when the user passes a bucket name with a folder postfix


        Example:
            - Bucket name: "my-bucket/my-folder/dev"
            - Object name: "my-object"
            - Returns: bucket_name="my-bucket", object_name="my-folder/dev/my-object"

        """
        if "/" in bucket_name:
            bucket_name, prefix = bucket_name.split("/", 1)
            object_name = f"{prefix}/{object_name}"
            return bucket_name, object_name
        return bucket_name, object_name

    async def get_gcs_logging_config(
        self, kwargs: Optional[Dict[str, Any]] = {}
    ) -> GCSLoggingConfig:
        """
        This function is used to get the GCS logging config for the GCS Bucket Logger.
        It checks if the dynamic parameters are provided in the kwargs and uses them to get the GCS logging config.
        If no dynamic parameters are provided, it uses the default values.
        """
        if kwargs is None:
            kwargs = {}

        standard_callback_dynamic_params: Optional[
            StandardCallbackDynamicParams
        ] = kwargs.get("standard_callback_dynamic_params", None)

        bucket_name: str
        path_service_account: Optional[str]
        if standard_callback_dynamic_params is not None:
            verbose_logger.debug("Using dynamic GCS logging")
            verbose_logger.debug(
                "standard_callback_dynamic_params: %s", standard_callback_dynamic_params
            )

            _bucket_name: Optional[str] = (
                standard_callback_dynamic_params.get("gcs_bucket_name", None)
                or self.BUCKET_NAME
            )
            _path_service_account: Optional[str] = (
                standard_callback_dynamic_params.get("gcs_path_service_account", None)
                or self.path_service_account_json
            )

            if _bucket_name is None:
                raise ValueError(
                    "GCS_BUCKET_NAME is not set in the environment, but GCS Bucket is being used as a logging callback. Please set 'GCS_BUCKET_NAME' in the environment."
                )
            bucket_name = _bucket_name
            path_service_account = _path_service_account
            vertex_instance = await self.get_or_create_vertex_instance(
                credentials=path_service_account
            )
        else:
            # If no dynamic parameters, use the default instance
            if self.BUCKET_NAME is None:
                raise ValueError(
                    "GCS_BUCKET_NAME is not set in the environment, but GCS Bucket is being used as a logging callback. Please set 'GCS_BUCKET_NAME' in the environment."
                )
            bucket_name = self.BUCKET_NAME
            path_service_account = self.path_service_account_json
            vertex_instance = await self.get_or_create_vertex_instance(
                credentials=path_service_account
            )

        return GCSLoggingConfig(
            bucket_name=bucket_name,
            vertex_instance=vertex_instance,
            path_service_account=path_service_account,
        )

    async def get_or_create_vertex_instance(
        self, credentials: Optional[str]
    ) -> VertexBase:
        """
        This function is used to get the Vertex instance for the GCS Bucket Logger.
        It checks if the Vertex instance is already created and cached, if not it creates a new instance and caches it.
        """
        from litellm.llms.vertex_ai.vertex_llm_base import VertexBase

        _in_memory_key = self._get_in_memory_key_for_vertex_instance(credentials)
        if _in_memory_key not in self.vertex_instances:
            vertex_instance = VertexBase()
            await vertex_instance._ensure_access_token_async(
                credentials=credentials,
                project_id=None,
                custom_llm_provider="vertex_ai",
            )
            self.vertex_instances[_in_memory_key] = vertex_instance
        return self.vertex_instances[_in_memory_key]

    def _get_in_memory_key_for_vertex_instance(self, credentials: Optional[str]) -> str:
        """
        Returns key to use for caching the Vertex instance in-memory.

        When using Vertex with Key based logging, we need to cache the Vertex instance in-memory.

        - If a credentials string is provided, it is used as the key.
        - If no credentials string is provided, "IAM_AUTH" is used as the key.
        """
        return credentials or IAM_AUTH_KEY

    async def download_gcs_object(self, object_name: str, **kwargs):
        """
        Download an object from GCS.

        https://cloud.google.com/storage/docs/downloading-objects#download-object-json
        """
        try:
            gcs_logging_config: GCSLoggingConfig = await self.get_gcs_logging_config(
                kwargs=kwargs
            )
            headers = await self.construct_request_headers(
                vertex_instance=gcs_logging_config["vertex_instance"],
                service_account_json=gcs_logging_config["path_service_account"],
            )
            bucket_name = gcs_logging_config["bucket_name"]
            bucket_name, object_name = self._handle_folders_in_bucket_name(
                bucket_name=bucket_name,
                object_name=object_name,
            )

            url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{object_name}?alt=media"

            # Send the GET request to download the object
            response = await self.async_httpx_client.get(url=url, headers=headers)

            if response.status_code != 200:
                verbose_logger.error(
                    "GCS object download error: %s", str(response.text)
                )
                return None

            verbose_logger.debug(
                "GCS object download response status code: %s", response.status_code
            )

            # Return the content of the downloaded object
            return response.content

        except Exception as e:
            verbose_logger.error("GCS object download error: %s", str(e))
            return None

    async def delete_gcs_object(self, object_name: str, **kwargs):
        """
        Delete an object from GCS.
        """
        try:
            gcs_logging_config: GCSLoggingConfig = await self.get_gcs_logging_config(
                kwargs=kwargs
            )
            headers = await self.construct_request_headers(
                vertex_instance=gcs_logging_config["vertex_instance"],
                service_account_json=gcs_logging_config["path_service_account"],
            )
            bucket_name = gcs_logging_config["bucket_name"]
            bucket_name, object_name = self._handle_folders_in_bucket_name(
                bucket_name=bucket_name,
                object_name=object_name,
            )

            url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{object_name}"

            # Send the DELETE request to delete the object
            response = await self.async_httpx_client.delete(url=url, headers=headers)

            if (response.status_code != 200) or (response.status_code != 204):
                verbose_logger.error(
                    "GCS object delete error: %s, status code: %s",
                    str(response.text),
                    response.status_code,
                )
                return None

            verbose_logger.debug(
                "GCS object delete response status code: %s, response: %s",
                response.status_code,
                response.text,
            )

            # Return the content of the downloaded object
            return response.text

        except Exception as e:
            verbose_logger.error("GCS object download error: %s", str(e))
            return None

    async def _log_json_data_on_gcs(
        self,
        headers: Dict[str, str],
        bucket_name: str,
        object_name: str,
        logging_payload: Union[StandardLoggingPayload, str],
    ):
        """
        Helper function to make POST request to GCS Bucket in the specified bucket.
        """
        if isinstance(logging_payload, str):
            json_logged_payload = logging_payload
        else:
            json_logged_payload = json.dumps(logging_payload, default=str)

        bucket_name, object_name = self._handle_folders_in_bucket_name(
            bucket_name=bucket_name,
            object_name=object_name,
        )

        response = await self.async_httpx_client.post(
            headers=headers,
            url=f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={object_name}",
            data=json_logged_payload,
        )

        if response.status_code != 200:
            verbose_logger.error("GCS Bucket logging error: %s", str(response.text))

        verbose_logger.debug("GCS Bucket response %s", response)
        verbose_logger.debug("GCS Bucket status code %s", response.status_code)
        verbose_logger.debug("GCS Bucket response.text %s", response.text)

        return response.json()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\php.py ===
"""
    pygments.lexers.php
    ~~~~~~~~~~~~~~~~~~~

    Lexers for PHP and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, include, bygroups, default, \
    using, this, words, do_insertions, line_re
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Other, Generic
from pygments.util import get_bool_opt, get_list_opt, shebang_matches

__all__ = ['ZephirLexer', 'PsyshConsoleLexer', 'PhpLexer']


class ZephirLexer(RegexLexer):
    """
    For Zephir language source code.

    Zephir is a compiled high level language aimed
    to the creation of C-extensions for PHP.
    """

    name = 'Zephir'
    url = 'http://zephir-lang.com/'
    aliases = ['zephir']
    filenames = ['*.zep']
    version_added = '2.0'

    zephir_keywords = ['fetch', 'echo', 'isset', 'empty']
    zephir_type = ['bit', 'bits', 'string']

    flags = re.DOTALL | re.MULTILINE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'/', Operator, '#pop'),
            default('#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|->|[-<>+*%&|^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|loop|'
             r'require|inline|throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'namespace|use|extends|this|fetch|isset|unset|echo|fetch|likely|unlikely|'
             r'empty)\b', Keyword, 'slashstartsregex'),
            (r'(var|let|with|function)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|bool|char|class|const|double|enum|export|extends|final|'
             r'native|goto|implements|import|int|string|interface|long|ulong|char|uchar|'
             r'float|unsigned|private|protected|public|short|static|self|throws|reverse|'
             r'transient|volatile|readonly)\b', Keyword.Reserved),
            (r'(true|false|null|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|_REQUEST|_COOKIE|_SESSION|'
             r'_GET|_POST|_SERVER|this|stdClass|range|count|iterator|'
             r'window)\b', Name.Builtin),
            (r'[$a-zA-Z_][\w\\]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ]
    }


class PsyshConsoleLexer(Lexer):
    """
    For PsySH console output, such as:

    .. sourcecode:: psysh

        >>> $greeting = function($name): string {
        ...     return "Hello, {$name}";
        ... };
        => Closure($name): string {#2371 …3}
        >>> $greeting('World')
        => "Hello, World"
    """
    name = 'PsySH console session for PHP'
    url = 'https://psysh.org/'
    aliases = ['psysh']
    version_added = '2.7'

    def __init__(self, **options):
        options['startinline'] = True
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        phplexer = PhpLexer(**self.options)
        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            if line.startswith('>>> ') or line.startswith('... '):
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:4])]))
                curcode += line[4:]
            elif line.rstrip() == '...':
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, '...')]))
                curcode += line[3:]
            else:
                if curcode:
                    yield from do_insertions(
                        insertions, phplexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            yield from do_insertions(insertions,
                                     phplexer.get_tokens_unprocessed(curcode))


class PhpLexer(RegexLexer):
    """
    For PHP source code.
    For PHP embedded in HTML, use the `HtmlPhpLexer`.

    Additional options accepted:

    `startinline`
        If given and ``True`` the lexer starts highlighting with
        php code (i.e.: no starting ``<?php`` required).  The default
        is ``False``.
    `funcnamehighlighting`
        If given and ``True``, highlight builtin function names
        (default: ``True``).
    `disabledmodules`
        If given, must be a list of module names whose function names
        should not be highlighted. By default all modules are highlighted
        except the special ``'unknown'`` module that includes functions
        that are known to php but are undocumented.

        To get a list of allowed modules have a look into the
        `_php_builtins` module:

        .. sourcecode:: pycon

            >>> from pygments.lexers._php_builtins import MODULES
            >>> MODULES.keys()
            ['PHP Options/Info', 'Zip', 'dba', ...]

        In fact the names of those modules match the module names from
        the php documentation.
    """

    name = 'PHP'
    url = 'https://www.php.net/'
    aliases = ['php', 'php3', 'php4', 'php5']
    filenames = ['*.php', '*.php[345]', '*.inc']
    mimetypes = ['text/x-php']
    version_added = ''

    # Note that a backslash is included, PHP uses a backslash as a namespace
    # separator.
    _ident_inner = r'(?:[\\_a-z]|[^\x00-\x7f])(?:[\\\w]|[^\x00-\x7f])*'
    # But not inside strings.
    _ident_nons = r'(?:[_a-z]|[^\x00-\x7f])(?:\w|[^\x00-\x7f])*'

    flags = re.IGNORECASE | re.DOTALL | re.MULTILINE
    tokens = {
        'root': [
            (r'<\?(php)?', Comment.Preproc, 'php'),
            (r'[^<]+', Other),
            (r'<', Other)
        ],
        'php': [
            (r'\?>', Comment.Preproc, '#pop'),
            (r'(<<<)([\'"]?)(' + _ident_nons + r')(\2\n.*?\n\s*)(\3)(;?)(\n)',
             bygroups(String, String, String.Delimiter, String, String.Delimiter,
                      Punctuation, Text)),
            (r'\s+', Text),
            (r'#\[', Punctuation, 'attribute'),
            (r'#.*?\n', Comment.Single),
            (r'//.*?\n', Comment.Single),
            # put the empty comment here, it is otherwise seen as
            # the start of a docstring
            (r'/\*\*/', Comment.Multiline),
            (r'/\*\*.*?\*/', String.Doc),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'(->|::)(\s*)(' + _ident_nons + ')',
             bygroups(Operator, Text, Name.Attribute)),
            (r'[~!%^&*+=|:.<>/@-]+', Operator),
            (r'\?', Operator),  # don't add to the charclass above!
            (r'[\[\]{}();,]+', Punctuation),
            (r'(new)(\s+)(class)\b', bygroups(Keyword, Text, Keyword)),
            (r'(class)(\s+)', bygroups(Keyword, Text), 'classname'),
            (r'(function)(\s*)(?=\()', bygroups(Keyword, Text)),
            (r'(function)(\s+)(&?)(\s*)',
             bygroups(Keyword, Text, Operator, Text), 'functionname'),
            (r'(const)(\s+)(' + _ident_inner + ')',
             bygroups(Keyword, Text, Name.Constant)),
            (r'(and|E_PARSE|old_function|E_ERROR|or|as|E_WARNING|parent|'
             r'eval|PHP_OS|break|exit|case|extends|PHP_VERSION|cfunction|'
             r'FALSE|print|for|require|continue|foreach|require_once|'
             r'declare|return|default|static|do|switch|die|stdClass|'
             r'echo|else|TRUE|elseif|var|empty|if|xor|enddeclare|include|'
             r'virtual|endfor|include_once|while|endforeach|global|'
             r'endif|list|endswitch|new|endwhile|not|'
             r'array|E_ALL|NULL|final|php_user_filter|interface|'
             r'implements|public|private|protected|abstract|clone|try|'
             r'catch|throw|this|use|namespace|trait|yield|'
             r'finally|match)\b', Keyword),
            (r'(true|false|null)\b', Keyword.Constant),
            include('magicconstants'),
            (r'\$\{', Name.Variable, 'variablevariable'),
            (r'\$+' + _ident_inner, Name.Variable),
            (_ident_inner, Name.Other),
            (r'(\d+\.\d*|\d*\.\d+)(e[+-]?[0-9]+)?', Number.Float),
            (r'\d+e[+-]?[0-9]+', Number.Float),
            (r'0[0-7]+', Number.Oct),
            (r'0x[a-f0-9]+', Number.Hex),
            (r'\d+', Number.Integer),
            (r'0b[01]+', Number.Bin),
            (r"'([^'\\]*(?:\\.[^'\\]*)*)'", String.Single),
            (r'`([^`\\]*(?:\\.[^`\\]*)*)`', String.Backtick),
            (r'"', String.Double, 'string'),
        ],
        'variablevariable': [
            (r'\}', Name.Variable, '#pop'),
            include('php')
        ],
        'magicfuncs': [
            # source: http://php.net/manual/en/language.oop5.magic.php
            (words((
                '__construct', '__destruct', '__call', '__callStatic', '__get', '__set',
                '__isset', '__unset', '__sleep', '__wakeup', '__toString', '__invoke',
                '__set_state', '__clone', '__debugInfo',), suffix=r'\b'),
             Name.Function.Magic),
        ],
        'magicconstants': [
            # source: http://php.net/manual/en/language.constants.predefined.php
            (words((
                '__LINE__', '__FILE__', '__DIR__', '__FUNCTION__', '__CLASS__',
                '__TRAIT__', '__METHOD__', '__NAMESPACE__',),
                suffix=r'\b'),
             Name.Constant),
        ],
        'classname': [
            (_ident_inner, Name.Class, '#pop')
        ],
        'functionname': [
            include('magicfuncs'),
            (_ident_inner, Name.Function, '#pop'),
            default('#pop')
        ],
        'string': [
            (r'"', String.Double, '#pop'),
            (r'[^{$"\\]+', String.Double),
            (r'\\([nrt"$\\]|[0-7]{1,3}|x[0-9a-f]{1,2})', String.Escape),
            (r'\$' + _ident_nons + r'(\[\S+?\]|->' + _ident_nons + ')?',
             String.Interpol),
            (r'(\{\$\{)(.*?)(\}\})',
             bygroups(String.Interpol, using(this, _startinline=True),
                      String.Interpol)),
            (r'(\{)(\$.*?)(\})',
             bygroups(String.Interpol, using(this, _startinline=True),
                      String.Interpol)),
            (r'(\$\{)(\S+)(\})',
             bygroups(String.Interpol, Name.Variable, String.Interpol)),
            (r'[${\\]', String.Double)
        ],
        'attribute': [
            (r'\]', Punctuation, '#pop'),
            (r'\(', Punctuation, 'attributeparams'),
            (_ident_inner, Name.Decorator),
            include('php')
        ],
        'attributeparams': [
            (r'\)', Punctuation, '#pop'),
            include('php')
        ],
    }

    def __init__(self, **options):
        self.funcnamehighlighting = get_bool_opt(
            options, 'funcnamehighlighting', True)
        self.disabledmodules = get_list_opt(
            options, 'disabledmodules', ['unknown'])
        self.startinline = get_bool_opt(options, 'startinline', False)

        # private option argument for the lexer itself
        if '_startinline' in options:
            self.startinline = options.pop('_startinline')

        # collect activated functions in a set
        self._functions = set()
        if self.funcnamehighlighting:
            from pygments.lexers._php_builtins import MODULES
            for key, value in MODULES.items():
                if key not in self.disabledmodules:
                    self._functions.update(value)
        RegexLexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        stack = ['root']
        if self.startinline:
            stack.append('php')
        for index, token, value in \
                RegexLexer.get_tokens_unprocessed(self, text, stack):
            if token is Name.Other:
                if value in self._functions:
                    yield index, Name.Builtin, value
                    continue
            yield index, token, value

    def analyse_text(text):
        if shebang_matches(text, r'php'):
            return True
        rv = 0.0
        if re.search(r'<\?(?!xml)', text):
            rv += 0.3
        return rv

# === NexusCore/openenv\Lib\site-packages\zmq\green\core.py ===
# -----------------------------------------------------------------------------
#  Copyright (C) 2011-2012 Travis Cline
#
#  This file is part of pyzmq
#  It is adapted from upstream project zeromq_gevent under the New BSD License
#
#  Distributed under the terms of the New BSD License.  The full license is in
#  the file LICENSE.BSD, distributed as part of this software.
# -----------------------------------------------------------------------------

"""This module wraps the :class:`Socket` and :class:`Context` found in :mod:`pyzmq <zmq>` to be non blocking"""

from __future__ import annotations

import sys
import time
import warnings

import gevent
from gevent.event import AsyncResult
from gevent.hub import get_hub

import zmq
from zmq import Context as _original_Context
from zmq import Socket as _original_Socket

from .poll import _Poller

if hasattr(zmq, 'RCVTIMEO'):
    TIMEOS: tuple = (zmq.RCVTIMEO, zmq.SNDTIMEO)
else:
    TIMEOS = ()


def _stop(evt):
    """simple wrapper for stopping an Event, allowing for method rename in gevent 1.0"""
    try:
        evt.stop()
    except AttributeError:
        # gevent<1.0 compat
        evt.cancel()


class _Socket(_original_Socket):
    """Green version of :class:`zmq.Socket`

    The following methods are overridden:

        * send
        * recv

    To ensure that the ``zmq.NOBLOCK`` flag is set and that sending or receiving
    is deferred to the hub if a ``zmq.EAGAIN`` (retry) error is raised.

    The `__state_changed` method is triggered when the zmq.FD for the socket is
    marked as readable and triggers the necessary read and write events (which
    are waited for in the recv and send methods).

    Some double underscore prefixes are used to minimize pollution of
    :class:`zmq.Socket`'s namespace.
    """

    __in_send_multipart = False
    __in_recv_multipart = False
    __writable = None
    __readable = None
    _state_event = None
    _gevent_bug_timeout = 11.6  # timeout for not trusting gevent
    _debug_gevent = False  # turn on if you think gevent is missing events
    _poller_class = _Poller
    _repr_cls = "zmq.green.Socket"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.__in_send_multipart = False
        self.__in_recv_multipart = False
        self.__setup_events()

    def __del__(self):
        self.close()

    def close(self, linger=None):
        super().close(linger)
        self.__cleanup_events()

    def __cleanup_events(self):
        # close the _state_event event, keeps the number of active file descriptors down
        if getattr(self, '_state_event', None):
            _stop(self._state_event)
            self._state_event = None
        # if the socket has entered a close state resume any waiting greenlets
        self.__writable.set()
        self.__readable.set()

    def __setup_events(self):
        self.__readable = AsyncResult()
        self.__writable = AsyncResult()
        self.__readable.set()
        self.__writable.set()

        try:
            self._state_event = get_hub().loop.io(
                self.getsockopt(zmq.FD), 1
            )  # read state watcher
            self._state_event.start(self.__state_changed)
        except AttributeError:
            # for gevent<1.0 compatibility
            from gevent.core import read_event

            self._state_event = read_event(
                self.getsockopt(zmq.FD), self.__state_changed, persist=True
            )

    def __state_changed(self, event=None, _evtype=None):
        if self.closed:
            self.__cleanup_events()
            return
        try:
            # avoid triggering __state_changed from inside __state_changed
            events = super().getsockopt(zmq.EVENTS)
        except zmq.ZMQError as exc:
            self.__writable.set_exception(exc)
            self.__readable.set_exception(exc)
        else:
            if events & zmq.POLLOUT:
                self.__writable.set()
            if events & zmq.POLLIN:
                self.__readable.set()

    def _wait_write(self):
        assert self.__writable.ready(), "Only one greenlet can be waiting on this event"
        self.__writable = AsyncResult()
        # timeout is because libzmq cannot be trusted to properly signal a new send event:
        # this is effectively a maximum poll interval of 1s
        tic = time.time()
        dt = self._gevent_bug_timeout
        if dt:
            timeout = gevent.Timeout(seconds=dt)
        else:
            timeout = None
        try:
            if timeout:
                timeout.start()
            self.__writable.get(block=True)
        except gevent.Timeout as t:
            if t is not timeout:
                raise
            toc = time.time()
            # gevent bug: get can raise timeout even on clean return
            # don't display zmq bug warning for gevent bug (this is getting ridiculous)
            if (
                self._debug_gevent
                and timeout
                and toc - tic > dt
                and self.getsockopt(zmq.EVENTS) & zmq.POLLOUT
            ):
                print(
                    f"BUG: gevent may have missed a libzmq send event on {self.FD}!",
                    file=sys.stderr,
                )
        finally:
            if timeout:
                timeout.close()
            self.__writable.set()

    def _wait_read(self):
        assert self.__readable.ready(), "Only one greenlet can be waiting on this event"
        self.__readable = AsyncResult()
        # timeout is because libzmq cannot always be trusted to play nice with libevent.
        # I can only confirm that this actually happens for send, but lets be symmetrical
        # with our dirty hacks.
        # this is effectively a maximum poll interval of 1s
        tic = time.time()
        dt = self._gevent_bug_timeout
        if dt:
            timeout = gevent.Timeout(seconds=dt)
        else:
            timeout = None
        try:
            if timeout:
                timeout.start()
            self.__readable.get(block=True)
        except gevent.Timeout as t:
            if t is not timeout:
                raise
            toc = time.time()
            # gevent bug: get can raise timeout even on clean return
            # don't display zmq bug warning for gevent bug (this is getting ridiculous)
            if (
                self._debug_gevent
                and timeout
                and toc - tic > dt
                and self.getsockopt(zmq.EVENTS) & zmq.POLLIN
            ):
                print(
                    f"BUG: gevent may have missed a libzmq recv event on {self.FD}!",
                    file=sys.stderr,
                )
        finally:
            if timeout:
                timeout.close()
            self.__readable.set()

    def send(self, data, flags=0, copy=True, track=False, **kwargs):
        """send, which will only block current greenlet

        state_changed always fires exactly once (success or fail) at the
        end of this method.
        """

        # if we're given the NOBLOCK flag act as normal and let the EAGAIN get raised
        if flags & zmq.NOBLOCK:
            try:
                msg = super().send(data, flags, copy, track, **kwargs)
            finally:
                if not self.__in_send_multipart:
                    self.__state_changed()
            return msg
        # ensure the zmq.NOBLOCK flag is part of flags
        flags |= zmq.NOBLOCK
        while True:  # Attempt to complete this operation indefinitely, blocking the current greenlet
            try:
                # attempt the actual call
                msg = super().send(data, flags, copy, track)
            except zmq.ZMQError as e:
                # if the raised ZMQError is not EAGAIN, reraise
                if e.errno != zmq.EAGAIN:
                    if not self.__in_send_multipart:
                        self.__state_changed()
                    raise
            else:
                if not self.__in_send_multipart:
                    self.__state_changed()
                return msg
            # defer to the event loop until we're notified the socket is writable
            self._wait_write()

    def recv(self, flags=0, copy=True, track=False):
        """recv, which will only block current greenlet

        state_changed always fires exactly once (success or fail) at the
        end of this method.
        """
        if flags & zmq.NOBLOCK:
            try:
                msg = super().recv(flags, copy, track)
            finally:
                if not self.__in_recv_multipart:
                    self.__state_changed()
            return msg

        flags |= zmq.NOBLOCK
        while True:
            try:
                msg = super().recv(flags, copy, track)
            except zmq.ZMQError as e:
                if e.errno != zmq.EAGAIN:
                    if not self.__in_recv_multipart:
                        self.__state_changed()
                    raise
            else:
                if not self.__in_recv_multipart:
                    self.__state_changed()
                return msg
            self._wait_read()

    def recv_into(self, buffer, /, *, nbytes=0, flags=0):
        """recv_into, which will only block current greenlet"""
        if flags & zmq.DONTWAIT:
            return super().recv_into(buffer, nbytes=nbytes, flags=flags)
        flags |= zmq.DONTWAIT
        while True:
            try:
                recvd = super().recv_into(buffer, nbytes=nbytes, flags=flags)
            except zmq.ZMQError as e:
                if e.errno != zmq.EAGAIN:
                    self.__state_changed()
                    raise
            else:
                self.__state_changed()
                return recvd
            self._wait_read()

    def send_multipart(self, *args, **kwargs):
        """wrap send_multipart to prevent state_changed on each partial send"""
        self.__in_send_multipart = True
        try:
            msg = super().send_multipart(*args, **kwargs)
        finally:
            self.__in_send_multipart = False
            self.__state_changed()
        return msg

    def recv_multipart(self, *args, **kwargs):
        """wrap recv_multipart to prevent state_changed on each partial recv"""
        self.__in_recv_multipart = True
        try:
            msg = super().recv_multipart(*args, **kwargs)
        finally:
            self.__in_recv_multipart = False
            self.__state_changed()
        return msg

    def get(self, opt):
        """trigger state_changed on getsockopt(EVENTS)"""
        if opt in TIMEOS:
            warnings.warn(
                "TIMEO socket options have no effect in zmq.green", UserWarning
            )
        optval = super().get(opt)
        if opt == zmq.EVENTS:
            self.__state_changed()
        return optval

    def set(self, opt, val):
        """set socket option"""
        if opt in TIMEOS:
            warnings.warn(
                "TIMEO socket options have no effect in zmq.green", UserWarning
            )
        return super().set(opt, val)


class _Context(_original_Context[_Socket]):
    """Replacement for :class:`zmq.Context`

    Ensures that the greened Socket above is used in calls to `socket`.
    """

    _socket_class = _Socket
    _repr_cls = "zmq.green.Context"

    # avoid sharing instance with base Context class
    _instance = None

# === NexusCore/openenv\Lib\site-packages\jupyter_client\localinterfaces.py ===
"""Utilities for identifying local IP addresses."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import os
import re
import socket
import subprocess
from subprocess import PIPE, Popen
from typing import Any, Callable, Iterable, Sequence
from warnings import warn

LOCAL_IPS: list = []
PUBLIC_IPS: list = []

LOCALHOST: str = ""


def _uniq_stable(elems: Iterable) -> list:
    """uniq_stable(elems) -> list

    Return from an iterable, a list of all the unique elements in the input,
    maintaining the order in which they first appear.
    """
    seen = set()
    value = []
    for x in elems:
        if x not in seen:
            value.append(x)
            seen.add(x)
    return value


def _get_output(cmd: str | Sequence[str]) -> str:
    """Get output of a command, raising IOError if it fails"""
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()  # type:ignore[attr-defined]
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type:ignore[attr-defined]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo)  # noqa
    stdout, stderr = p.communicate()
    if p.returncode:
        msg = "Failed to run {}: {}".format(cmd, stderr.decode("utf8", "replace"))
        raise OSError(msg)
    return stdout.decode("utf8", "replace")


def _only_once(f: Callable) -> Callable:
    """decorator to only run a function once"""
    f.called = False  # type:ignore[attr-defined]

    def wrapped(**kwargs: Any) -> Any:
        if f.called:  # type:ignore[attr-defined]
            return
        ret = f(**kwargs)
        f.called = True  # type:ignore[attr-defined]
        return ret

    return wrapped


def _requires_ips(f: Callable) -> Callable:
    """decorator to ensure load_ips has been run before f"""

    def ips_loaded(*args: Any, **kwargs: Any) -> Any:
        _load_ips()
        return f(*args, **kwargs)

    return ips_loaded


# subprocess-parsing ip finders
class NoIPAddresses(Exception):  # noqa
    pass


def _populate_from_list(addrs: Sequence[str] | None) -> None:
    """populate local and public IPs from flat list of all IPs"""
    if not addrs:
        raise NoIPAddresses

    global LOCALHOST
    public_ips = []
    local_ips = []

    for ip in addrs:
        local_ips.append(ip)
        if not ip.startswith("127."):
            public_ips.append(ip)
        elif not LOCALHOST:
            LOCALHOST = ip

    if not LOCALHOST or LOCALHOST == "127.0.0.1":
        LOCALHOST = "127.0.0.1"
        local_ips.insert(0, LOCALHOST)

    local_ips.extend(["0.0.0.0", ""])  # noqa

    LOCAL_IPS[:] = _uniq_stable(local_ips)
    PUBLIC_IPS[:] = _uniq_stable(public_ips)


_ifconfig_ipv4_pat = re.compile(r"inet\b.*?(\d+\.\d+\.\d+\.\d+)", re.IGNORECASE)


def _load_ips_ifconfig() -> None:
    """load ip addresses from `ifconfig` output (posix)"""

    try:
        out = _get_output("ifconfig")
    except OSError:
        # no ifconfig, it's usually in /sbin and /sbin is not on everyone's PATH
        out = _get_output("/sbin/ifconfig")

    lines = out.splitlines()
    addrs = []
    for line in lines:
        m = _ifconfig_ipv4_pat.match(line.strip())
        if m:
            addrs.append(m.group(1))
    _populate_from_list(addrs)


def _load_ips_ip() -> None:
    """load ip addresses from `ip addr` output (Linux)"""
    out = _get_output(["ip", "-f", "inet", "addr"])

    lines = out.splitlines()
    addrs = []
    for line in lines:
        blocks = line.lower().split()
        if (len(blocks) >= 2) and (blocks[0] == "inet"):
            addrs.append(blocks[1].split("/")[0])
    _populate_from_list(addrs)


_ipconfig_ipv4_pat = re.compile(r"ipv4.*?(\d+\.\d+\.\d+\.\d+)$", re.IGNORECASE)


def _load_ips_ipconfig() -> None:
    """load ip addresses from `ipconfig` output (Windows)"""
    out = _get_output("ipconfig")

    lines = out.splitlines()
    addrs = []
    for line in lines:
        m = _ipconfig_ipv4_pat.match(line.strip())
        if m:
            addrs.append(m.group(1))
    _populate_from_list(addrs)


def _load_ips_psutil() -> None:
    """load ip addresses with netifaces"""
    import psutil

    global LOCALHOST
    local_ips = []
    public_ips = []

    # dict of iface_name: address_list, eg
    # {"lo": [snicaddr(family=<AddressFamily.AF_INET>, address="127.0.0.1",
    #   ...), snicaddr(family=<AddressFamily.AF_INET6>, ...)]}
    for iface, ifaddresses in psutil.net_if_addrs().items():
        for address_data in ifaddresses:
            if address_data.family == socket.AF_INET:
                addr = address_data.address
                if not (iface.startswith("lo") or addr.startswith("127.")):
                    public_ips.append(addr)
                elif not LOCALHOST:
                    LOCALHOST = addr
                local_ips.append(addr)
    if not LOCALHOST:
        # we never found a loopback interface (can this ever happen?), assume common default
        LOCALHOST = "127.0.0.1"
        local_ips.insert(0, LOCALHOST)
    local_ips.extend(["0.0.0.0", ""])  # noqa
    LOCAL_IPS[:] = _uniq_stable(local_ips)
    PUBLIC_IPS[:] = _uniq_stable(public_ips)


def _load_ips_netifaces() -> None:
    """load ip addresses with netifaces"""
    import netifaces  # type: ignore[import-not-found]

    global LOCALHOST
    local_ips = []
    public_ips = []

    # list of iface names, 'lo0', 'eth0', etc.
    for iface in netifaces.interfaces():
        # list of ipv4 addrinfo dicts
        ipv4s = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
        for entry in ipv4s:
            addr = entry.get("addr")
            if not addr:
                continue
            if not (iface.startswith("lo") or addr.startswith("127.")):
                public_ips.append(addr)
            elif not LOCALHOST:
                LOCALHOST = addr
            local_ips.append(addr)
    if not LOCALHOST:
        # we never found a loopback interface (can this ever happen?), assume common default
        LOCALHOST = "127.0.0.1"
        local_ips.insert(0, LOCALHOST)
    local_ips.extend(["0.0.0.0", ""])  # noqa
    LOCAL_IPS[:] = _uniq_stable(local_ips)
    PUBLIC_IPS[:] = _uniq_stable(public_ips)


def _load_ips_gethostbyname() -> None:
    """load ip addresses with socket.gethostbyname_ex

    This can be slow.
    """
    global LOCALHOST
    try:
        LOCAL_IPS[:] = socket.gethostbyname_ex("localhost")[2]
    except OSError:
        # assume common default
        LOCAL_IPS[:] = ["127.0.0.1"]

    try:
        hostname = socket.gethostname()
        PUBLIC_IPS[:] = socket.gethostbyname_ex(hostname)[2]
        # try hostname.local, in case hostname has been short-circuited to loopback
        if not hostname.endswith(".local") and all(ip.startswith("127") for ip in PUBLIC_IPS):
            PUBLIC_IPS[:] = socket.gethostbyname_ex(socket.gethostname() + ".local")[2]
    except OSError:
        pass
    finally:
        PUBLIC_IPS[:] = _uniq_stable(PUBLIC_IPS)
        LOCAL_IPS.extend(PUBLIC_IPS)

    # include all-interface aliases: 0.0.0.0 and ''
    LOCAL_IPS.extend(["0.0.0.0", ""])  # noqa

    LOCAL_IPS[:] = _uniq_stable(LOCAL_IPS)

    LOCALHOST = LOCAL_IPS[0]


def _load_ips_dumb() -> None:
    """Fallback in case of unexpected failure"""
    global LOCALHOST
    LOCALHOST = "127.0.0.1"
    LOCAL_IPS[:] = [LOCALHOST, "0.0.0.0", ""]  # noqa
    PUBLIC_IPS[:] = []


@_only_once
def _load_ips(suppress_exceptions: bool = True) -> None:
    """load the IPs that point to this machine

    This function will only ever be called once.

    If will use psutil to do it quickly if available.
    If not, it will use netifaces to do it quickly if available.
    Then it will fallback on parsing the output of ifconfig / ip addr / ipconfig, as appropriate.
    Finally, it will fallback on socket.gethostbyname_ex, which can be slow.
    """

    try:
        # first priority, use psutil
        try:
            return _load_ips_psutil()
        except ImportError:
            pass

        # second priority, use netifaces
        try:
            return _load_ips_netifaces()
        except ImportError:
            pass

        # second priority, parse subprocess output (how reliable is this?)

        if os.name == "nt":
            try:
                return _load_ips_ipconfig()
            except (OSError, NoIPAddresses):
                pass
        else:
            try:
                return _load_ips_ip()
            except (OSError, NoIPAddresses):
                pass
            try:
                return _load_ips_ifconfig()
            except (OSError, NoIPAddresses):
                pass

        # lowest priority, use gethostbyname

        return _load_ips_gethostbyname()
    except Exception as e:
        if not suppress_exceptions:
            raise
        # unexpected error shouldn't crash, load dumb default values instead.
        warn("Unexpected error discovering local network interfaces: %s" % e, stacklevel=2)
    _load_ips_dumb()


@_requires_ips
def local_ips() -> list[str]:
    """return the IP addresses that point to this machine"""
    return LOCAL_IPS


@_requires_ips
def public_ips() -> list[str]:
    """return the IP addresses for this machine that are visible to other machines"""
    return PUBLIC_IPS


@_requires_ips
def localhost() -> str:
    """return ip for localhost (almost always 127.0.0.1)"""
    return LOCALHOST


@_requires_ips
def is_local_ip(ip: str) -> bool:
    """does `ip` point to this machine?"""
    return ip in LOCAL_IPS


@_requires_ips
def is_public_ip(ip: str) -> bool:
    """is `ip` a publicly visible address?"""
    return ip in PUBLIC_IPS

# === NexusCore/openenv\Lib\site-packages\litellm\_redis.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import inspect
import json

# s/o [@Frank Colson](https://www.linkedin.com/in/frank-colson-422b9b183/) for this redis implementation
import os
from typing import List, Optional, Union

import redis  # type: ignore
import redis.asyncio as async_redis  # type: ignore

from litellm import get_secret, get_secret_str
from litellm.constants import REDIS_CONNECTION_POOL_TIMEOUT, REDIS_SOCKET_TIMEOUT

from ._logging import verbose_logger


def _get_redis_kwargs():
    arg_spec = inspect.getfullargspec(redis.Redis)

    # Only allow primitive arguments
    exclude_args = {
        "self",
        "connection_pool",
        "retry",
    }

    include_args = ["url"]

    available_args = [x for x in arg_spec.args if x not in exclude_args] + include_args

    return available_args


def _get_redis_url_kwargs(client=None):
    if client is None:
        client = redis.Redis.from_url
    arg_spec = inspect.getfullargspec(redis.Redis.from_url)

    # Only allow primitive arguments
    exclude_args = {
        "self",
        "connection_pool",
        "retry",
    }

    include_args = ["url"]

    available_args = [x for x in arg_spec.args if x not in exclude_args] + include_args

    return available_args


def _get_redis_cluster_kwargs(client=None):
    if client is None:
        client = redis.Redis.from_url
    arg_spec = inspect.getfullargspec(redis.RedisCluster)

    # Only allow primitive arguments
    exclude_args = {"self", "connection_pool", "retry", "host", "port", "startup_nodes"}

    available_args = [x for x in arg_spec.args if x not in exclude_args]
    available_args.append("password")
    available_args.append("username")
    available_args.append("ssl")

    return available_args


def _get_redis_env_kwarg_mapping():
    PREFIX = "REDIS_"

    return {f"{PREFIX}{x.upper()}": x for x in _get_redis_kwargs()}


def _redis_kwargs_from_environment():
    mapping = _get_redis_env_kwarg_mapping()

    return_dict = {}
    for k, v in mapping.items():
        value = get_secret(k, default_value=None)  # type: ignore
        if value is not None:
            return_dict[v] = value
    return return_dict


def get_redis_url_from_environment():
    if "REDIS_URL" in os.environ:
        return os.environ["REDIS_URL"]

    if "REDIS_HOST" not in os.environ or "REDIS_PORT" not in os.environ:
        raise ValueError(
            "Either 'REDIS_URL' or both 'REDIS_HOST' and 'REDIS_PORT' must be specified for Redis."
        )

    if "REDIS_PASSWORD" in os.environ:
        redis_password = f":{os.environ['REDIS_PASSWORD']}@"
    else:
        redis_password = ""

    return (
        f"redis://{redis_password}{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}"
    )


def _get_redis_client_logic(**env_overrides):
    """
    Common functionality across sync + async redis client implementations
    """
    ### check if "os.environ/<key-name>" passed in
    for k, v in env_overrides.items():
        if isinstance(v, str) and v.startswith("os.environ/"):
            v = v.replace("os.environ/", "")
            value = get_secret(v)  # type: ignore
            env_overrides[k] = value

    redis_kwargs = {
        **_redis_kwargs_from_environment(),
        **env_overrides,
    }

    _startup_nodes: Optional[Union[str, list]] = redis_kwargs.get("startup_nodes", None) or get_secret(  # type: ignore
        "REDIS_CLUSTER_NODES"
    )

    if _startup_nodes is not None and isinstance(_startup_nodes, str):
        redis_kwargs["startup_nodes"] = json.loads(_startup_nodes)

    _sentinel_nodes: Optional[Union[str, list]] = redis_kwargs.get("sentinel_nodes", None) or get_secret(  # type: ignore
        "REDIS_SENTINEL_NODES"
    )

    if _sentinel_nodes is not None and isinstance(_sentinel_nodes, str):
        redis_kwargs["sentinel_nodes"] = json.loads(_sentinel_nodes)

    _sentinel_password: Optional[str] = redis_kwargs.get(
        "sentinel_password", None
    ) or get_secret_str("REDIS_SENTINEL_PASSWORD")

    if _sentinel_password is not None:
        redis_kwargs["sentinel_password"] = _sentinel_password

    _service_name: Optional[str] = redis_kwargs.get("service_name", None) or get_secret(  # type: ignore
        "REDIS_SERVICE_NAME"
    )

    if _service_name is not None:
        redis_kwargs["service_name"] = _service_name

    if "url" in redis_kwargs and redis_kwargs["url"] is not None:
        redis_kwargs.pop("host", None)
        redis_kwargs.pop("port", None)
        redis_kwargs.pop("db", None)
        redis_kwargs.pop("password", None)
    elif "startup_nodes" in redis_kwargs and redis_kwargs["startup_nodes"] is not None:
        pass
    elif (
        "sentinel_nodes" in redis_kwargs and redis_kwargs["sentinel_nodes"] is not None
    ):
        pass
    elif "host" not in redis_kwargs or redis_kwargs["host"] is None:
        raise ValueError("Either 'host' or 'url' must be specified for redis.")

    # litellm.print_verbose(f"redis_kwargs: {redis_kwargs}")
    return redis_kwargs


def init_redis_cluster(redis_kwargs) -> redis.RedisCluster:
    _redis_cluster_nodes_in_env: Optional[str] = get_secret("REDIS_CLUSTER_NODES")  # type: ignore
    if _redis_cluster_nodes_in_env is not None:
        try:
            redis_kwargs["startup_nodes"] = json.loads(_redis_cluster_nodes_in_env)
        except json.JSONDecodeError:
            raise ValueError(
                "REDIS_CLUSTER_NODES environment variable is not valid JSON. Please ensure it's properly formatted."
            )

    verbose_logger.debug("init_redis_cluster: startup nodes are being initialized.")
    from redis.cluster import ClusterNode

    args = _get_redis_cluster_kwargs()
    cluster_kwargs = {}
    for arg in redis_kwargs:
        if arg in args:
            cluster_kwargs[arg] = redis_kwargs[arg]

    new_startup_nodes: List[ClusterNode] = []

    for item in redis_kwargs["startup_nodes"]:
        new_startup_nodes.append(ClusterNode(**item))

    redis_kwargs.pop("startup_nodes")
    return redis.RedisCluster(startup_nodes=new_startup_nodes, **cluster_kwargs)  # type: ignore


def _init_redis_sentinel(redis_kwargs) -> redis.Redis:
    sentinel_nodes = redis_kwargs.get("sentinel_nodes")
    sentinel_password = redis_kwargs.get("sentinel_password")
    service_name = redis_kwargs.get("service_name")

    if not sentinel_nodes or not service_name:
        raise ValueError(
            "Both 'sentinel_nodes' and 'service_name' are required for Redis Sentinel."
        )

    verbose_logger.debug("init_redis_sentinel: sentinel nodes are being initialized.")

    # Set up the Sentinel client
    sentinel = redis.Sentinel(
        sentinel_nodes,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        password=sentinel_password,
    )

    # Return the master instance for the given service

    return sentinel.master_for(service_name)


def _init_async_redis_sentinel(redis_kwargs) -> async_redis.Redis:
    sentinel_nodes = redis_kwargs.get("sentinel_nodes")
    sentinel_password = redis_kwargs.get("sentinel_password")
    service_name = redis_kwargs.get("service_name")

    if not sentinel_nodes or not service_name:
        raise ValueError(
            "Both 'sentinel_nodes' and 'service_name' are required for Redis Sentinel."
        )

    verbose_logger.debug("init_redis_sentinel: sentinel nodes are being initialized.")

    # Set up the Sentinel client
    sentinel = async_redis.Sentinel(
        sentinel_nodes,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        password=sentinel_password,
    )

    # Return the master instance for the given service

    return sentinel.master_for(service_name)


def get_redis_client(**env_overrides):
    redis_kwargs = _get_redis_client_logic(**env_overrides)
    if "url" in redis_kwargs and redis_kwargs["url"] is not None:
        args = _get_redis_url_kwargs()
        url_kwargs = {}
        for arg in redis_kwargs:
            if arg in args:
                url_kwargs[arg] = redis_kwargs[arg]

        return redis.Redis.from_url(**url_kwargs)

    if "startup_nodes" in redis_kwargs or get_secret("REDIS_CLUSTER_NODES") is not None:  # type: ignore
        return init_redis_cluster(redis_kwargs)

    # Check for Redis Sentinel
    if "sentinel_nodes" in redis_kwargs and "service_name" in redis_kwargs:
        return _init_redis_sentinel(redis_kwargs)

    return redis.Redis(**redis_kwargs)


def get_redis_async_client(
    **env_overrides,
) -> async_redis.Redis:
    redis_kwargs = _get_redis_client_logic(**env_overrides)
    if "url" in redis_kwargs and redis_kwargs["url"] is not None:
        args = _get_redis_url_kwargs(client=async_redis.Redis.from_url)
        url_kwargs = {}
        for arg in redis_kwargs:
            if arg in args:
                url_kwargs[arg] = redis_kwargs[arg]
            else:
                verbose_logger.debug(
                    "REDIS: ignoring argument: {}. Not an allowed async_redis.Redis.from_url arg.".format(
                        arg
                    )
                )
        return async_redis.Redis.from_url(**url_kwargs)

    if "startup_nodes" in redis_kwargs:
        from redis.cluster import ClusterNode

        args = _get_redis_cluster_kwargs()
        cluster_kwargs = {}
        for arg in redis_kwargs:
            if arg in args:
                cluster_kwargs[arg] = redis_kwargs[arg]

        new_startup_nodes: List[ClusterNode] = []

        for item in redis_kwargs["startup_nodes"]:
            new_startup_nodes.append(ClusterNode(**item))
        redis_kwargs.pop("startup_nodes")
        return async_redis.RedisCluster(
            startup_nodes=new_startup_nodes, **cluster_kwargs  # type: ignore
        )

    # Check for Redis Sentinel
    if "sentinel_nodes" in redis_kwargs and "service_name" in redis_kwargs:
        return _init_async_redis_sentinel(redis_kwargs)

    return async_redis.Redis(
        **redis_kwargs,
    )


def get_redis_connection_pool(**env_overrides):
    redis_kwargs = _get_redis_client_logic(**env_overrides)
    verbose_logger.debug("get_redis_connection_pool: redis_kwargs", redis_kwargs)
    if "url" in redis_kwargs and redis_kwargs["url"] is not None:
        return async_redis.BlockingConnectionPool.from_url(
            timeout=REDIS_CONNECTION_POOL_TIMEOUT, url=redis_kwargs["url"]
        )
    connection_class = async_redis.Connection
    if "ssl" in redis_kwargs:
        connection_class = async_redis.SSLConnection
        redis_kwargs.pop("ssl", None)
        redis_kwargs["connection_class"] = connection_class
    redis_kwargs.pop("startup_nodes", None)
    return async_redis.BlockingConnectionPool(
        timeout=REDIS_CONNECTION_POOL_TIMEOUT, **redis_kwargs
    )

# === NexusCore/openenv\Lib\site-packages\PIL\PsdImagePlugin.py ===
#
# The Python Imaging Library
# $Id$
#
# Adobe PSD 2.5/3.0 file handling
#
# History:
# 1995-09-01 fl   Created
# 1997-01-03 fl   Read most PSD images
# 1997-01-18 fl   Fixed P and CMYK support
# 2001-10-21 fl   Added seek/tell support (for layers)
#
# Copyright (c) 1997-2001 by Secret Labs AB.
# Copyright (c) 1995-2001 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import io
from functools import cached_property
from typing import IO

from . import Image, ImageFile, ImagePalette
from ._binary import i8
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import si16be as si16
from ._binary import si32be as si32
from ._util import DeferredError

MODES = {
    # (photoshop mode, bits) -> (pil mode, required channels)
    (0, 1): ("1", 1),
    (0, 8): ("L", 1),
    (1, 8): ("L", 1),
    (2, 8): ("P", 1),
    (3, 8): ("RGB", 3),
    (4, 8): ("CMYK", 4),
    (7, 8): ("L", 1),  # FIXME: multilayer
    (8, 8): ("L", 1),  # duotone
    (9, 8): ("LAB", 3),
}


# --------------------------------------------------------------------.
# read PSD images


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(b"8BPS")


##
# Image plugin for Photoshop images.


class PsdImageFile(ImageFile.ImageFile):
    format = "PSD"
    format_description = "Adobe Photoshop"
    _close_exclusive_fp_after_loading = False

    def _open(self) -> None:
        read = self.fp.read

        #
        # header

        s = read(26)
        if not _accept(s) or i16(s, 4) != 1:
            msg = "not a PSD file"
            raise SyntaxError(msg)

        psd_bits = i16(s, 22)
        psd_channels = i16(s, 12)
        psd_mode = i16(s, 24)

        mode, channels = MODES[(psd_mode, psd_bits)]

        if channels > psd_channels:
            msg = "not enough channels"
            raise OSError(msg)
        if mode == "RGB" and psd_channels == 4:
            mode = "RGBA"
            channels = 4

        self._mode = mode
        self._size = i32(s, 18), i32(s, 14)

        #
        # color mode data

        size = i32(read(4))
        if size:
            data = read(size)
            if mode == "P" and size == 768:
                self.palette = ImagePalette.raw("RGB;L", data)

        #
        # image resources

        self.resources = []

        size = i32(read(4))
        if size:
            # load resources
            end = self.fp.tell() + size
            while self.fp.tell() < end:
                read(4)  # signature
                id = i16(read(2))
                name = read(i8(read(1)))
                if not (len(name) & 1):
                    read(1)  # padding
                data = read(i32(read(4)))
                if len(data) & 1:
                    read(1)  # padding
                self.resources.append((id, name, data))
                if id == 1039:  # ICC profile
                    self.info["icc_profile"] = data

        #
        # layer and mask information

        self._layers_position = None

        size = i32(read(4))
        if size:
            end = self.fp.tell() + size
            size = i32(read(4))
            if size:
                self._layers_position = self.fp.tell()
                self._layers_size = size
            self.fp.seek(end)
        self._n_frames: int | None = None

        #
        # image descriptor

        self.tile = _maketile(self.fp, mode, (0, 0) + self.size, channels)

        # keep the file open
        self._fp = self.fp
        self.frame = 1
        self._min_frame = 1

    @cached_property
    def layers(
        self,
    ) -> list[tuple[str, str, tuple[int, int, int, int], list[ImageFile._Tile]]]:
        layers = []
        if self._layers_position is not None:
            if isinstance(self._fp, DeferredError):
                raise self._fp.ex
            self._fp.seek(self._layers_position)
            _layer_data = io.BytesIO(ImageFile._safe_read(self._fp, self._layers_size))
            layers = _layerinfo(_layer_data, self._layers_size)
        self._n_frames = len(layers)
        return layers

    @property
    def n_frames(self) -> int:
        if self._n_frames is None:
            self._n_frames = len(self.layers)
        return self._n_frames

    @property
    def is_animated(self) -> bool:
        return len(self.layers) > 1

    def seek(self, layer: int) -> None:
        if not self._seek_check(layer):
            return
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex

        # seek to given layer (1..max)
        _, mode, _, tile = self.layers[layer - 1]
        self._mode = mode
        self.tile = tile
        self.frame = layer
        self.fp = self._fp

    def tell(self) -> int:
        # return layer number (0=image, 1..max=layers)
        return self.frame


def _layerinfo(
    fp: IO[bytes], ct_bytes: int
) -> list[tuple[str, str, tuple[int, int, int, int], list[ImageFile._Tile]]]:
    # read layerinfo block
    layers = []

    def read(size: int) -> bytes:
        return ImageFile._safe_read(fp, size)

    ct = si16(read(2))

    # sanity check
    if ct_bytes < (abs(ct) * 20):
        msg = "Layer block too short for number of layers requested"
        raise SyntaxError(msg)

    for _ in range(abs(ct)):
        # bounding box
        y0 = si32(read(4))
        x0 = si32(read(4))
        y1 = si32(read(4))
        x1 = si32(read(4))

        # image info
        bands = []
        ct_types = i16(read(2))
        if ct_types > 4:
            fp.seek(ct_types * 6 + 12, io.SEEK_CUR)
            size = i32(read(4))
            fp.seek(size, io.SEEK_CUR)
            continue

        for _ in range(ct_types):
            type = i16(read(2))

            if type == 65535:
                b = "A"
            else:
                b = "RGBA"[type]

            bands.append(b)
            read(4)  # size

        # figure out the image mode
        bands.sort()
        if bands == ["R"]:
            mode = "L"
        elif bands == ["B", "G", "R"]:
            mode = "RGB"
        elif bands == ["A", "B", "G", "R"]:
            mode = "RGBA"
        else:
            mode = ""  # unknown

        # skip over blend flags and extra information
        read(12)  # filler
        name = ""
        size = i32(read(4))  # length of the extra data field
        if size:
            data_end = fp.tell() + size

            length = i32(read(4))
            if length:
                fp.seek(length - 16, io.SEEK_CUR)

            length = i32(read(4))
            if length:
                fp.seek(length, io.SEEK_CUR)

            length = i8(read(1))
            if length:
                # Don't know the proper encoding,
                # Latin-1 should be a good guess
                name = read(length).decode("latin-1", "replace")

            fp.seek(data_end)
        layers.append((name, mode, (x0, y0, x1, y1)))

    # get tiles
    layerinfo = []
    for i, (name, mode, bbox) in enumerate(layers):
        tile = []
        for m in mode:
            t = _maketile(fp, m, bbox, 1)
            if t:
                tile.extend(t)
        layerinfo.append((name, mode, bbox, tile))

    return layerinfo


def _maketile(
    file: IO[bytes], mode: str, bbox: tuple[int, int, int, int], channels: int
) -> list[ImageFile._Tile]:
    tiles = []
    read = file.read

    compression = i16(read(2))

    xsize = bbox[2] - bbox[0]
    ysize = bbox[3] - bbox[1]

    offset = file.tell()

    if compression == 0:
        #
        # raw compression
        for channel in range(channels):
            layer = mode[channel]
            if mode == "CMYK":
                layer += ";I"
            tiles.append(ImageFile._Tile("raw", bbox, offset, layer))
            offset = offset + xsize * ysize

    elif compression == 1:
        #
        # packbits compression
        i = 0
        bytecount = read(channels * ysize * 2)
        offset = file.tell()
        for channel in range(channels):
            layer = mode[channel]
            if mode == "CMYK":
                layer += ";I"
            tiles.append(ImageFile._Tile("packbits", bbox, offset, layer))
            for y in range(ysize):
                offset = offset + i16(bytecount, i)
                i += 2

    file.seek(offset)

    if offset & 1:
        read(1)  # padding

    return tiles


# --------------------------------------------------------------------
# registry


Image.register_open(PsdImageFile.format, PsdImageFile, _accept)

Image.register_extension(PsdImageFile.format, ".psd")

Image.register_mime(PsdImageFile.format, "image/vnd.adobe.photoshop")

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\github.py ===
import base64
import re

import requests

from ..spec import AbstractFileSystem
from ..utils import infer_storage_options
from .memory import MemoryFile


class GithubFileSystem(AbstractFileSystem):
    """Interface to files in github

    An instance of this class provides the files residing within a remote github
    repository. You may specify a point in the repos history, by SHA, branch
    or tag (default is current master).

    For files less than 1 MB in size, file content is returned directly in a
    MemoryFile. For larger files, or for files tracked by git-lfs, file content
    is returned as an HTTPFile wrapping the ``download_url`` provided by the
    GitHub API.

    When using fsspec.open, allows URIs of the form:

    - "github://path/file", in which case you must specify org, repo and
      may specify sha in the extra args
    - 'github://org:repo@/precip/catalog.yml', where the org and repo are
      part of the URI
    - 'github://org:repo@sha/precip/catalog.yml', where the sha is also included

    ``sha`` can be the full or abbreviated hex of the commit you want to fetch
    from, or a branch or tag name (so long as it doesn't contain special characters
    like "/", "?", which would have to be HTTP-encoded).

    For authorised access, you must provide username and token, which can be made
    at https://github.com/settings/tokens
    """

    url = "https://api.github.com/repos/{org}/{repo}/git/trees/{sha}"
    content_url = "https://api.github.com/repos/{org}/{repo}/contents/{path}?ref={sha}"
    protocol = "github"
    timeout = (60, 60)  # connect, read timeouts

    def __init__(
        self, org, repo, sha=None, username=None, token=None, timeout=None, **kwargs
    ):
        super().__init__(**kwargs)
        self.org = org
        self.repo = repo
        if (username is None) ^ (token is None):
            raise ValueError("Auth required both username and token")
        self.username = username
        self.token = token
        if timeout is not None:
            self.timeout = timeout
        if sha is None:
            # look up default branch (not necessarily "master")
            u = "https://api.github.com/repos/{org}/{repo}"
            r = requests.get(
                u.format(org=org, repo=repo), timeout=self.timeout, **self.kw
            )
            r.raise_for_status()
            sha = r.json()["default_branch"]

        self.root = sha
        self.ls("")
        try:
            from .http import HTTPFileSystem

            self.http_fs = HTTPFileSystem(**kwargs)
        except ImportError:
            self.http_fs = None

    @property
    def kw(self):
        if self.username:
            return {"auth": (self.username, self.token)}
        return {}

    @classmethod
    def repos(cls, org_or_user, is_org=True):
        """List repo names for given org or user

        This may become the top level of the FS

        Parameters
        ----------
        org_or_user: str
            Name of the github org or user to query
        is_org: bool (default True)
            Whether the name is an organisation (True) or user (False)

        Returns
        -------
        List of string
        """
        r = requests.get(
            f"https://api.github.com/{['users', 'orgs'][is_org]}/{org_or_user}/repos",
            timeout=cls.timeout,
        )
        r.raise_for_status()
        return [repo["name"] for repo in r.json()]

    @property
    def tags(self):
        """Names of tags in the repo"""
        r = requests.get(
            f"https://api.github.com/repos/{self.org}/{self.repo}/tags",
            timeout=self.timeout,
            **self.kw,
        )
        r.raise_for_status()
        return [t["name"] for t in r.json()]

    @property
    def branches(self):
        """Names of branches in the repo"""
        r = requests.get(
            f"https://api.github.com/repos/{self.org}/{self.repo}/branches",
            timeout=self.timeout,
            **self.kw,
        )
        r.raise_for_status()
        return [t["name"] for t in r.json()]

    @property
    def refs(self):
        """Named references, tags and branches"""
        return {"tags": self.tags, "branches": self.branches}

    def ls(self, path, detail=False, sha=None, _sha=None, **kwargs):
        """List files at given path

        Parameters
        ----------
        path: str
            Location to list, relative to repo root
        detail: bool
            If True, returns list of dicts, one per file; if False, returns
            list of full filenames only
        sha: str (optional)
            List at the given point in the repo history, branch or tag name or commit
            SHA
        _sha: str (optional)
            List this specific tree object (used internally to descend into trees)
        """
        path = self._strip_protocol(path)
        if path == "":
            _sha = sha or self.root
        if _sha is None:
            parts = path.rstrip("/").split("/")
            so_far = ""
            _sha = sha or self.root
            for part in parts:
                out = self.ls(so_far, True, sha=sha, _sha=_sha)
                so_far += "/" + part if so_far else part
                out = [o for o in out if o["name"] == so_far]
                if not out:
                    raise FileNotFoundError(path)
                out = out[0]
                if out["type"] == "file":
                    if detail:
                        return [out]
                    else:
                        return path
                _sha = out["sha"]
        if path not in self.dircache or sha not in [self.root, None]:
            r = requests.get(
                self.url.format(org=self.org, repo=self.repo, sha=_sha),
                timeout=self.timeout,
                **self.kw,
            )
            if r.status_code == 404:
                raise FileNotFoundError(path)
            r.raise_for_status()
            types = {"blob": "file", "tree": "directory"}
            out = [
                {
                    "name": path + "/" + f["path"] if path else f["path"],
                    "mode": f["mode"],
                    "type": types[f["type"]],
                    "size": f.get("size", 0),
                    "sha": f["sha"],
                }
                for f in r.json()["tree"]
                if f["type"] in types
            ]
            if sha in [self.root, None]:
                self.dircache[path] = out
        else:
            out = self.dircache[path]
        if detail:
            return out
        else:
            return sorted([f["name"] for f in out])

    def invalidate_cache(self, path=None):
        self.dircache.clear()

    @classmethod
    def _strip_protocol(cls, path):
        opts = infer_storage_options(path)
        if "username" not in opts:
            return super()._strip_protocol(path)
        return opts["path"].lstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(path):
        opts = infer_storage_options(path)
        if "username" not in opts:
            return {}
        out = {"org": opts["username"], "repo": opts["password"]}
        if opts["host"]:
            out["sha"] = opts["host"]
        return out

    def _open(
        self,
        path,
        mode="rb",
        block_size=None,
        cache_options=None,
        sha=None,
        **kwargs,
    ):
        if mode != "rb":
            raise NotImplementedError

        # construct a url to hit the GitHub API's repo contents API
        url = self.content_url.format(
            org=self.org, repo=self.repo, path=path, sha=sha or self.root
        )

        # make a request to this API, and parse the response as JSON
        r = requests.get(url, timeout=self.timeout, **self.kw)
        if r.status_code == 404:
            raise FileNotFoundError(path)
        r.raise_for_status()
        content_json = r.json()

        # if the response's content key is not empty, try to parse it as base64
        if content_json["content"]:
            content = base64.b64decode(content_json["content"])

            # as long as the content does not start with the string
            # "version https://git-lfs.github.com/"
            # then it is probably not a git-lfs pointer and we can just return
            # the content directly
            if not content.startswith(b"version https://git-lfs.github.com/"):
                return MemoryFile(None, None, content)

        # we land here if the content was not present in the first response
        # (regular file over 1MB or git-lfs tracked file)
        # in this case, we get let the HTTPFileSystem handle the download
        if self.http_fs is None:
            raise ImportError(
                "Please install fsspec[http] to access github files >1 MB "
                "or git-lfs tracked files."
            )
        return self.http_fs.open(
            content_json["download_url"],
            mode=mode,
            block_size=block_size,
            cache_options=cache_options,
            **kwargs,
        )

    def rm(self, path, recursive=False, maxdepth=None, message=None):
        path = self.expand_path(path, recursive=recursive, maxdepth=maxdepth)
        for p in reversed(path):
            self.rm_file(p, message=message)

    def rm_file(self, path, message=None, **kwargs):
        """
        Remove a file from a specified branch using a given commit message.

        Since Github DELETE operation requires a branch name, and we can't reliably
        determine whether the provided SHA refers to a branch, tag, or commit, we
        assume it's a branch. If it's not, the user will encounter an error when
        attempting to retrieve the file SHA or delete the file.

        Parameters
        ----------
        path: str
            The file's location relative to the repository root.
        message: str, optional
            The commit message for the deletion.
        """

        if not self.username:
            raise ValueError("Authentication required")

        path = self._strip_protocol(path)

        # Attempt to get SHA from cache or Github API
        sha = self._get_sha_from_cache(path)
        if not sha:
            url = self.content_url.format(
                org=self.org, repo=self.repo, path=path.lstrip("/"), sha=self.root
            )
            r = requests.get(url, timeout=self.timeout, **self.kw)
            if r.status_code == 404:
                raise FileNotFoundError(path)
            r.raise_for_status()
            sha = r.json()["sha"]

        # Delete the file
        delete_url = self.content_url.format(
            org=self.org, repo=self.repo, path=path, sha=self.root
        )
        branch = self.root
        data = {
            "message": message or f"Delete {path}",
            "sha": sha,
            **({"branch": branch} if branch else {}),
        }

        r = requests.delete(delete_url, json=data, timeout=self.timeout, **self.kw)
        error_message = r.json().get("message", "")
        if re.search(r"Branch .+ not found", error_message):
            error = "Remove only works when the filesystem is initialised from a branch or default (None)"
            raise ValueError(error)
        r.raise_for_status()

        self.invalidate_cache(path)

    def _get_sha_from_cache(self, path):
        for entries in self.dircache.values():
            for entry in entries:
                entry_path = entry.get("name")
                if entry_path and entry_path == path and "sha" in entry:
                    return entry["sha"]
        return None

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\model_service.py ===
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

from google.ai.generativelanguage_v1beta.types import tuned_model as gag_tuned_model
from google.ai.generativelanguage_v1beta.types import model

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
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
        models (MutableSequence[google.ai.generativelanguage_v1beta.types.Model]):
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
        filter (str):
            Optional. A filter is a full text search over
            the tuned model's description and display name.
            By default, results will not include tuned
            models shared with everyone.

            Additional operators:

              - owner:me
              - writers:me
              - readers:me
              - readers:everyone

            Examples:

              "owner:me" returns all tuned models to which
            caller has owner role   "readers:me" returns all
            tuned models to which caller has reader role
            "readers:everyone" returns all tuned models that
            are shared with everyone
    """

    page_size: int = proto.Field(
        proto.INT32,
        number=1,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )
    filter: str = proto.Field(
        proto.STRING,
        number=3,
    )


class ListTunedModelsResponse(proto.Message):
    r"""Response from ``ListTunedModels`` containing a paginated list of
    Models.

    Attributes:
        tuned_models (MutableSequence[google.ai.generativelanguage_v1beta.types.TunedModel]):
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
        tuned_model (google.ai.generativelanguage_v1beta.types.TunedModel):
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
        snapshots (MutableSequence[google.ai.generativelanguage_v1beta.types.TuningSnapshot]):
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
        tuned_model (google.ai.generativelanguage_v1beta.types.TunedModel):
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