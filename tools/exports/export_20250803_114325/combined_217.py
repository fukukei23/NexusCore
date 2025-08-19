
# === NexusCore/openenv\Lib\site-packages\PIL\ImageWin.py ===
#
# The Python Imaging Library.
# $Id$
#
# a Windows DIB display interface
#
# History:
# 1996-05-20 fl   Created
# 1996-09-20 fl   Fixed subregion exposure
# 1997-09-21 fl   Added draw primitive (for tzPrint)
# 2003-05-21 fl   Added experimental Window/ImageWindow classes
# 2003-09-05 fl   Added fromstring/tostring methods
#
# Copyright (c) Secret Labs AB 1997-2003.
# Copyright (c) Fredrik Lundh 1996-2003.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

from . import Image


class HDC:
    """
    Wraps an HDC integer. The resulting object can be passed to the
    :py:meth:`~PIL.ImageWin.Dib.draw` and :py:meth:`~PIL.ImageWin.Dib.expose`
    methods.
    """

    def __init__(self, dc: int) -> None:
        self.dc = dc

    def __int__(self) -> int:
        return self.dc


class HWND:
    """
    Wraps an HWND integer. The resulting object can be passed to the
    :py:meth:`~PIL.ImageWin.Dib.draw` and :py:meth:`~PIL.ImageWin.Dib.expose`
    methods, instead of a DC.
    """

    def __init__(self, wnd: int) -> None:
        self.wnd = wnd

    def __int__(self) -> int:
        return self.wnd


class Dib:
    """
    A Windows bitmap with the given mode and size.  The mode can be one of "1",
    "L", "P", or "RGB".

    If the display requires a palette, this constructor creates a suitable
    palette and associates it with the image. For an "L" image, 128 graylevels
    are allocated. For an "RGB" image, a 6x6x6 colour cube is used, together
    with 20 graylevels.

    To make sure that palettes work properly under Windows, you must call the
    ``palette`` method upon certain events from Windows.

    :param image: Either a PIL image, or a mode string. If a mode string is
                  used, a size must also be given.  The mode can be one of "1",
                  "L", "P", or "RGB".
    :param size: If the first argument is a mode string, this
                 defines the size of the image.
    """

    def __init__(
        self, image: Image.Image | str, size: tuple[int, int] | None = None
    ) -> None:
        if isinstance(image, str):
            mode = image
            image = ""
            if size is None:
                msg = "If first argument is mode, size is required"
                raise ValueError(msg)
        else:
            mode = image.mode
            size = image.size
        if mode not in ["1", "L", "P", "RGB"]:
            mode = Image.getmodebase(mode)
        self.image = Image.core.display(mode, size)
        self.mode = mode
        self.size = size
        if image:
            assert not isinstance(image, str)
            self.paste(image)

    def expose(self, handle: int | HDC | HWND) -> None:
        """
        Copy the bitmap contents to a device context.

        :param handle: Device context (HDC), cast to a Python integer, or an
                       HDC or HWND instance.  In PythonWin, you can use
                       ``CDC.GetHandleAttrib()`` to get a suitable handle.
        """
        handle_int = int(handle)
        if isinstance(handle, HWND):
            dc = self.image.getdc(handle_int)
            try:
                self.image.expose(dc)
            finally:
                self.image.releasedc(handle_int, dc)
        else:
            self.image.expose(handle_int)

    def draw(
        self,
        handle: int | HDC | HWND,
        dst: tuple[int, int, int, int],
        src: tuple[int, int, int, int] | None = None,
    ) -> None:
        """
        Same as expose, but allows you to specify where to draw the image, and
        what part of it to draw.

        The destination and source areas are given as 4-tuple rectangles. If
        the source is omitted, the entire image is copied. If the source and
        the destination have different sizes, the image is resized as
        necessary.
        """
        if src is None:
            src = (0, 0) + self.size
        handle_int = int(handle)
        if isinstance(handle, HWND):
            dc = self.image.getdc(handle_int)
            try:
                self.image.draw(dc, dst, src)
            finally:
                self.image.releasedc(handle_int, dc)
        else:
            self.image.draw(handle_int, dst, src)

    def query_palette(self, handle: int | HDC | HWND) -> int:
        """
        Installs the palette associated with the image in the given device
        context.

        This method should be called upon **QUERYNEWPALETTE** and
        **PALETTECHANGED** events from Windows. If this method returns a
        non-zero value, one or more display palette entries were changed, and
        the image should be redrawn.

        :param handle: Device context (HDC), cast to a Python integer, or an
                       HDC or HWND instance.
        :return: The number of entries that were changed (if one or more entries,
                 this indicates that the image should be redrawn).
        """
        handle_int = int(handle)
        if isinstance(handle, HWND):
            handle = self.image.getdc(handle_int)
            try:
                result = self.image.query_palette(handle)
            finally:
                self.image.releasedc(handle, handle)
        else:
            result = self.image.query_palette(handle_int)
        return result

    def paste(
        self, im: Image.Image, box: tuple[int, int, int, int] | None = None
    ) -> None:
        """
        Paste a PIL image into the bitmap image.

        :param im: A PIL image.  The size must match the target region.
                   If the mode does not match, the image is converted to the
                   mode of the bitmap image.
        :param box: A 4-tuple defining the left, upper, right, and
                    lower pixel coordinate.  See :ref:`coordinate-system`. If
                    None is given instead of a tuple, all of the image is
                    assumed.
        """
        im.load()
        if self.mode != im.mode:
            im = im.convert(self.mode)
        if box:
            self.image.paste(im.im, box)
        else:
            self.image.paste(im.im)

    def frombytes(self, buffer: bytes) -> None:
        """
        Load display memory contents from byte data.

        :param buffer: A buffer containing display data (usually
                       data returned from :py:func:`~PIL.ImageWin.Dib.tobytes`)
        """
        self.image.frombytes(buffer)

    def tobytes(self) -> bytes:
        """
        Copy display memory contents to bytes object.

        :return: A bytes object containing display data.
        """
        return self.image.tobytes()


class Window:
    """Create a Window with the given title size."""

    def __init__(
        self, title: str = "PIL", width: int | None = None, height: int | None = None
    ) -> None:
        self.hwnd = Image.core.createwindow(
            title, self.__dispatcher, width or 0, height or 0
        )

    def __dispatcher(self, action: str, *args: int) -> None:
        getattr(self, f"ui_handle_{action}")(*args)

    def ui_handle_clear(self, dc: int, x0: int, y0: int, x1: int, y1: int) -> None:
        pass

    def ui_handle_damage(self, x0: int, y0: int, x1: int, y1: int) -> None:
        pass

    def ui_handle_destroy(self) -> None:
        pass

    def ui_handle_repair(self, dc: int, x0: int, y0: int, x1: int, y1: int) -> None:
        pass

    def ui_handle_resize(self, width: int, height: int) -> None:
        pass

    def mainloop(self) -> None:
        Image.core.eventloop()


class ImageWindow(Window):
    """Create an image window which displays the given image."""

    def __init__(self, image: Image.Image | Dib, title: str = "PIL") -> None:
        if not isinstance(image, Dib):
            image = Dib(image)
        self.image = image
        width, height = image.size
        super().__init__(title, width=width, height=height)

    def ui_handle_repair(self, dc: int, x0: int, y0: int, x1: int, y1: int) -> None:
        self.image.draw(dc, (x0, y0, x1, y1))

# === NexusCore/openenv\Lib\site-packages\PIL\SgiImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# SGI image file handling
#
# See "The SGI Image File Format (Draft version 0.97)", Paul Haeberli.
# <ftp://ftp.sgi.com/graphics/SGIIMAGESPEC>
#
#
# History:
# 2017-22-07 mb   Add RLE decompression
# 2016-16-10 mb   Add save method without compression
# 1995-09-10 fl   Created
#
# Copyright (c) 2016 by Mickael Bonfill.
# Copyright (c) 2008 by Karsten Hiddemann.
# Copyright (c) 1997 by Secret Labs AB.
# Copyright (c) 1995 by Fredrik Lundh.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import os
import struct
from typing import IO

from . import Image, ImageFile
from ._binary import i16be as i16
from ._binary import o8


def _accept(prefix: bytes) -> bool:
    return len(prefix) >= 2 and i16(prefix) == 474


MODES = {
    (1, 1, 1): "L",
    (1, 2, 1): "L",
    (2, 1, 1): "L;16B",
    (2, 2, 1): "L;16B",
    (1, 3, 3): "RGB",
    (2, 3, 3): "RGB;16B",
    (1, 3, 4): "RGBA",
    (2, 3, 4): "RGBA;16B",
}


##
# Image plugin for SGI images.
class SgiImageFile(ImageFile.ImageFile):
    format = "SGI"
    format_description = "SGI Image File Format"

    def _open(self) -> None:
        # HEAD
        assert self.fp is not None

        headlen = 512
        s = self.fp.read(headlen)

        if not _accept(s):
            msg = "Not an SGI image file"
            raise ValueError(msg)

        # compression : verbatim or RLE
        compression = s[2]

        # bpc : 1 or 2 bytes (8bits or 16bits)
        bpc = s[3]

        # dimension : 1, 2 or 3 (depending on xsize, ysize and zsize)
        dimension = i16(s, 4)

        # xsize : width
        xsize = i16(s, 6)

        # ysize : height
        ysize = i16(s, 8)

        # zsize : channels count
        zsize = i16(s, 10)

        # layout
        layout = bpc, dimension, zsize

        # determine mode from bits/zsize
        rawmode = ""
        try:
            rawmode = MODES[layout]
        except KeyError:
            pass

        if rawmode == "":
            msg = "Unsupported SGI image mode"
            raise ValueError(msg)

        self._size = xsize, ysize
        self._mode = rawmode.split(";")[0]
        if self.mode == "RGB":
            self.custom_mimetype = "image/rgb"

        # orientation -1 : scanlines begins at the bottom-left corner
        orientation = -1

        # decoder info
        if compression == 0:
            pagesize = xsize * ysize * bpc
            if bpc == 2:
                self.tile = [
                    ImageFile._Tile(
                        "SGI16",
                        (0, 0) + self.size,
                        headlen,
                        (self.mode, 0, orientation),
                    )
                ]
            else:
                self.tile = []
                offset = headlen
                for layer in self.mode:
                    self.tile.append(
                        ImageFile._Tile(
                            "raw", (0, 0) + self.size, offset, (layer, 0, orientation)
                        )
                    )
                    offset += pagesize
        elif compression == 1:
            self.tile = [
                ImageFile._Tile(
                    "sgi_rle", (0, 0) + self.size, headlen, (rawmode, orientation, bpc)
                )
            ]


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode not in {"RGB", "RGBA", "L"}:
        msg = "Unsupported SGI image mode"
        raise ValueError(msg)

    # Get the keyword arguments
    info = im.encoderinfo

    # Byte-per-pixel precision, 1 = 8bits per pixel
    bpc = info.get("bpc", 1)

    if bpc not in (1, 2):
        msg = "Unsupported number of bytes per pixel"
        raise ValueError(msg)

    # Flip the image, since the origin of SGI file is the bottom-left corner
    orientation = -1
    # Define the file as SGI File Format
    magic_number = 474
    # Run-Length Encoding Compression - Unsupported at this time
    rle = 0

    # Number of dimensions (x,y,z)
    dim = 3
    # X Dimension = width / Y Dimension = height
    x, y = im.size
    if im.mode == "L" and y == 1:
        dim = 1
    elif im.mode == "L":
        dim = 2
    # Z Dimension: Number of channels
    z = len(im.mode)

    if dim in {1, 2}:
        z = 1

    # assert we've got the right number of bands.
    if len(im.getbands()) != z:
        msg = f"incorrect number of bands in SGI write: {z} vs {len(im.getbands())}"
        raise ValueError(msg)

    # Minimum Byte value
    pinmin = 0
    # Maximum Byte value (255 = 8bits per pixel)
    pinmax = 255
    # Image name (79 characters max, truncated below in write)
    img_name = os.path.splitext(os.path.basename(filename))[0]
    if isinstance(img_name, str):
        img_name = img_name.encode("ascii", "ignore")
    # Standard representation of pixel in the file
    colormap = 0
    fp.write(struct.pack(">h", magic_number))
    fp.write(o8(rle))
    fp.write(o8(bpc))
    fp.write(struct.pack(">H", dim))
    fp.write(struct.pack(">H", x))
    fp.write(struct.pack(">H", y))
    fp.write(struct.pack(">H", z))
    fp.write(struct.pack(">l", pinmin))
    fp.write(struct.pack(">l", pinmax))
    fp.write(struct.pack("4s", b""))  # dummy
    fp.write(struct.pack("79s", img_name))  # truncates to 79 chars
    fp.write(struct.pack("s", b""))  # force null byte after img_name
    fp.write(struct.pack(">l", colormap))
    fp.write(struct.pack("404s", b""))  # dummy

    rawmode = "L"
    if bpc == 2:
        rawmode = "L;16B"

    for channel in im.split():
        fp.write(channel.tobytes("raw", rawmode, 0, orientation))

    if hasattr(fp, "flush"):
        fp.flush()


class SGI16Decoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None
        assert self.im is not None

        rawmode, stride, orientation = self.args
        pagesize = self.state.xsize * self.state.ysize
        zsize = len(self.mode)
        self.fd.seek(512)

        for band in range(zsize):
            channel = Image.new("L", (self.state.xsize, self.state.ysize))
            channel.frombytes(
                self.fd.read(2 * pagesize), "raw", "L;16B", stride, orientation
            )
            self.im.putband(channel.im, band)

        return -1, 0


#
# registry


Image.register_decoder("SGI16", SGI16Decoder)
Image.register_open(SgiImageFile.format, SgiImageFile, _accept)
Image.register_save(SgiImageFile.format, _save)
Image.register_mime(SgiImageFile.format, "image/sgi")

Image.register_extensions(SgiImageFile.format, [".bw", ".rgb", ".rgba", ".sgi"])

# End of file

# === NexusCore/openenv\Lib\site-packages\pygments\sphinxext.py ===
"""
    pygments.sphinxext
    ~~~~~~~~~~~~~~~~~~

    Sphinx extension to generate automatic documentation of lexers,
    formatters and filters.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from sphinx.util.nodes import nested_parse_with_titles


MODULEDOC = '''
.. module:: %s

%s
%s
'''

LEXERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames:   %s
    :MIME types:  %s

    %s

    %s

'''

FMTERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames: %s

    %s

'''

FILTERDOC = '''
.. class:: %s

    :Name: %s

    %s

'''


class PygmentsDoc(Directive):
    """
    A directive to collect all lexers/formatters/filters and generate
    autoclass directives for them.
    """
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        self.filenames = set()
        if self.arguments[0] == 'lexers':
            out = self.document_lexers()
        elif self.arguments[0] == 'formatters':
            out = self.document_formatters()
        elif self.arguments[0] == 'filters':
            out = self.document_filters()
        elif self.arguments[0] == 'lexers_overview':
            out = self.document_lexers_overview()
        else:
            raise Exception('invalid argument for "pygmentsdoc" directive')
        node = nodes.compound()
        vl = ViewList(out.split('\n'), source='')
        nested_parse_with_titles(self.state, vl, node)
        for fn in self.filenames:
            self.state.document.settings.record_dependencies.add(fn)
        return node.children

    def document_lexers_overview(self):
        """Generate a tabular overview of all lexers.

        The columns are the lexer name, the extensions handled by this lexer
        (or "None"), the aliases and a link to the lexer class."""
        from pygments.lexers._mapping import LEXERS
        import pygments.lexers
        out = []

        table = []

        def format_link(name, url):
            if url:
                return f'`{name} <{url}>`_'
            return name

        for classname, data in sorted(LEXERS.items(), key=lambda x: x[1][1].lower()):
            lexer_cls = pygments.lexers.find_lexer_class(data[1])
            extensions = lexer_cls.filenames + lexer_cls.alias_filenames

            table.append({
                'name': format_link(data[1], lexer_cls.url),
                'extensions': ', '.join(extensions).replace('*', '\\*').replace('_', '\\') or 'None',
                'aliases': ', '.join(data[2]),
                'class': f'{data[0]}.{classname}'
            })

        column_names = ['name', 'extensions', 'aliases', 'class']
        column_lengths = [max([len(row[column]) for row in table if row[column]])
                          for column in column_names]

        def write_row(*columns):
            """Format a table row"""
            out = []
            for length, col in zip(column_lengths, columns):
                if col:
                    out.append(col.ljust(length))
                else:
                    out.append(' '*length)

            return ' '.join(out)

        def write_seperator():
            """Write a table separator row"""
            sep = ['='*c for c in column_lengths]
            return write_row(*sep)

        out.append(write_seperator())
        out.append(write_row('Name', 'Extension(s)', 'Short name(s)', 'Lexer class'))
        out.append(write_seperator())
        for row in table:
            out.append(write_row(
                row['name'],
                row['extensions'],
                row['aliases'],
                f':class:`~{row["class"]}`'))
        out.append(write_seperator())

        return '\n'.join(out)

    def document_lexers(self):
        from pygments.lexers._mapping import LEXERS
        import pygments
        import inspect
        import pathlib

        out = []
        modules = {}
        moduledocstrings = {}
        for classname, data in sorted(LEXERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            if not cls.__doc__:
                print(f"Warning: {classname} does not have a docstring.")
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')

            example_file = getattr(cls, '_example', None)
            if example_file:
                p = pathlib.Path(inspect.getabsfile(pygments)).parent.parent /\
                    'tests' / 'examplefiles' / example_file
                content = p.read_text(encoding='utf-8')
                if not content:
                    raise Exception(
                        f"Empty example file '{example_file}' for lexer "
                        f"{classname}")

                if data[2]:
                    lexer_name = data[2][0]
                    docstring += '\n\n    .. admonition:: Example\n'
                    docstring += f'\n      .. code-block:: {lexer_name}\n\n'
                    for line in content.splitlines():
                        docstring += f'          {line}\n'

            if cls.version_added:
                version_line = f'.. versionadded:: {cls.version_added}'
            else:
                version_line = ''

            modules.setdefault(module, []).append((
                classname,
                ', '.join(data[2]) or 'None',
                ', '.join(data[3]).replace('*', '\\*').replace('_', '\\') or 'None',
                ', '.join(data[4]) or 'None',
                docstring,
                version_line))
            if module not in moduledocstrings:
                moddoc = mod.__doc__
                if isinstance(moddoc, bytes):
                    moddoc = moddoc.decode('utf8')
                moduledocstrings[module] = moddoc

        for module, lexers in sorted(modules.items(), key=lambda x: x[0]):
            if moduledocstrings[module] is None:
                raise Exception(f"Missing docstring for {module}")
            heading = moduledocstrings[module].splitlines()[4].strip().rstrip('.')
            out.append(MODULEDOC % (module, heading, '-'*len(heading)))
            for data in lexers:
                out.append(LEXERDOC % data)

        return ''.join(out)

    def document_formatters(self):
        from pygments.formatters import FORMATTERS

        out = []
        for classname, data in sorted(FORMATTERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            heading = cls.__name__
            out.append(FMTERDOC % (heading, ', '.join(data[2]) or 'None',
                                   ', '.join(data[3]).replace('*', '\\*') or 'None',
                                   docstring))
        return ''.join(out)

    def document_filters(self):
        from pygments.filters import FILTERS

        out = []
        for name, cls in FILTERS.items():
            self.filenames.add(sys.modules[cls.__module__].__file__)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            out.append(FILTERDOC % (cls.__name__, name, docstring))
        return ''.join(out)


def setup(app):
    app.add_directive('pygmentsdoc', PygmentsDoc)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\__init__.py ===
#!~/.wine/drive_c/Python25/python.exe
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
Windows application debugging engine for Python.

by Mario Vilas (mvilas at gmail.com)

Project: U{http://sourceforge.net/projects/winappdbg/}

Web:     U{http://winappdbg.sourceforge.net/}

Blog:    U{http://breakingcode.wordpress.com}

@group Debugging:
    Debug, EventHandler, EventSift, DebugLog

@group Instrumentation:
    System, Process, Thread, Module, Window, Registry

@group Disassemblers:
    Disassembler,
    BeaEngine, DistormEngine, PyDasmEngine

@group Crash reporting:
    Crash, CrashDump, CrashDAO, CrashDictionary

@group Memory search:
    Search,
    Pattern,
    BytePattern,
    TextPattern,
    RegExpPattern,
    HexPattern

@group Debug events:
    Event,
    NoEvent,
    CreateProcessEvent,
    CreateThreadEvent,
    ExitProcessEvent,
    ExitThreadEvent,
    LoadDLLEvent,
    UnloadDLLEvent,
    OutputDebugStringEvent,
    RIPEvent,
    ExceptionEvent

@group Win32 API wrappers:
    win32, Handle, ProcessHandle, ThreadHandle, FileHandle

@group Helpers:
    HexInput, HexOutput, HexDump, Color, Table, Logger,
    PathOperations,
    MemoryAddresses,
    CustomAddressIterator,
    DataAddressIterator,
    ImageAddressIterator,
    MappedAddressIterator,
    ExecutableAddressIterator,
    ReadableAddressIterator,
    WriteableAddressIterator,
    ExecutableAndWriteableAddressIterator,
    DebugRegister,
    Regenerator

@group Warnings:
    MixedBitsWarning, BreakpointWarning, BreakpointCallbackWarning,
    EventCallbackWarning, DebugSymbolsWarning, CrashWarning

@group Deprecated classes:
    CrashContainer, CrashTable, CrashTableMSSQL,
    VolatileCrashContainer, DummyCrashContainer

@type version_number: float
@var  version_number: This WinAppDbg major and minor version,
    as a floating point number. Use this for compatibility checking.

@type version: str
@var  version: This WinAppDbg release version,
    as a printable string. Use this to show to the user.

@undocumented: plugins
"""

__revision__ = "$Id$"

# List of all public symbols
__all__ = [
    # Library version
    "version",
    "version_number",
    # from breakpoint import *
    ##                'Breakpoint',
    ##                'CodeBreakpoint',
    ##                'PageBreakpoint',
    ##                'HardwareBreakpoint',
    ##                'Hook',
    ##                'ApiHook',
    ##                'BufferWatch',
    "BreakpointWarning",
    "BreakpointCallbackWarning",
    # from crash import *
    "Crash",
    "CrashWarning",
    "CrashDictionary",
    "CrashContainer",
    "CrashTable",
    "CrashTableMSSQL",
    "VolatileCrashContainer",
    "DummyCrashContainer",
    # from debug import *
    "Debug",
    "MixedBitsWarning",
    # from disasm import *
    "Disassembler",
    "BeaEngine",
    "DistormEngine",
    "PyDasmEngine",
    # from event import *
    "EventHandler",
    "EventSift",
    ##                'EventFactory',
    ##                'EventDispatcher',
    "EventCallbackWarning",
    "Event",
    ##                'NoEvent',
    "CreateProcessEvent",
    "CreateThreadEvent",
    "ExitProcessEvent",
    "ExitThreadEvent",
    "LoadDLLEvent",
    "UnloadDLLEvent",
    "OutputDebugStringEvent",
    "RIPEvent",
    "ExceptionEvent",
    # from interactive import *
    ##                'ConsoleDebugger',
    # from module import *
    "Module",
    "DebugSymbolsWarning",
    # from process import *
    "Process",
    # from system import *
    "System",
    # from search import *
    "Search",
    "Pattern",
    "BytePattern",
    "TextPattern",
    "RegExpPattern",
    "HexPattern",
    # from registry import *
    "Registry",
    # from textio import *
    "HexDump",
    "HexInput",
    "HexOutput",
    "Color",
    "Table",
    "CrashDump",
    "DebugLog",
    "Logger",
    # from thread import *
    "Thread",
    # from util import *
    "PathOperations",
    "MemoryAddresses",
    "CustomAddressIterator",
    "DataAddressIterator",
    "ImageAddressIterator",
    "MappedAddressIterator",
    "ExecutableAddressIterator",
    "ReadableAddressIterator",
    "WriteableAddressIterator",
    "ExecutableAndWriteableAddressIterator",
    "DebugRegister",
    # from window import *
    "Window",
    # import win32
    "win32",
    # from win32 import Handle, ProcessHandle, ThreadHandle, FileHandle
    "Handle",
    "ProcessHandle",
    "ThreadHandle",
    "FileHandle",
]

# Import all public symbols
from winappdbg.breakpoint import *
from winappdbg.crash import *
from winappdbg.debug import *
from winappdbg.disasm import *
from winappdbg.event import *
from winappdbg.interactive import *
from winappdbg.module import *
from winappdbg.process import *
from winappdbg.registry import *
from winappdbg.system import *
from winappdbg.search import *
from winappdbg.textio import *
from winappdbg.thread import *
from winappdbg.util import *
from winappdbg.window import *

import winappdbg.win32
from winappdbg.win32 import Handle, ProcessHandle, ThreadHandle, FileHandle

try:
    from sql import *

    __all__.append("CrashDAO")
except ImportError:
    import warnings

    warnings.warn("No SQL database support present (missing dependencies?)", ImportWarning)

# Library version
version_number = 1.5
version = "Version %s" % version_number

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\lowest_tpm_rpm.py ===
#### What this does ####
#   identifies lowest tpm deployment
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Union

from litellm import token_counter
from litellm._logging import verbose_router_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import LiteLLMPydanticObjectBase
from litellm.utils import print_verbose


class RoutingArgs(LiteLLMPydanticObjectBase):
    ttl: int = 1 * 60  # 1min (RPM/TPM expire key)


class LowestTPMLoggingHandler(CustomLogger):
    test_flag: bool = False
    logged_success: int = 0
    logged_failure: int = 0
    default_cache_time_seconds: int = 1 * 60 * 60  # 1 hour

    def __init__(
        self, router_cache: DualCache, model_list: list, routing_args: dict = {}
    ):
        self.router_cache = router_cache
        self.model_list = model_list
        self.routing_args = RoutingArgs(**routing_args)

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update TPM/RPM usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                total_tokens = response_obj["usage"]["total_tokens"]

                # ------------
                # Setup values
                # ------------
                current_minute = datetime.now().strftime("%H-%M")
                tpm_key = f"{model_group}:tpm:{current_minute}"
                rpm_key = f"{model_group}:rpm:{current_minute}"

                # ------------
                # Update usage
                # ------------

                ## TPM
                request_count_dict = self.router_cache.get_cache(key=tpm_key) or {}
                request_count_dict[id] = request_count_dict.get(id, 0) + total_tokens

                self.router_cache.set_cache(
                    key=tpm_key, value=request_count_dict, ttl=self.routing_args.ttl
                )

                ## RPM
                request_count_dict = self.router_cache.get_cache(key=rpm_key) or {}
                request_count_dict[id] = request_count_dict.get(id, 0) + 1

                self.router_cache.set_cache(
                    key=rpm_key, value=request_count_dict, ttl=self.routing_args.ttl
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_router_logger.error(
                "litellm.router_strategy.lowest_tpm_rpm.py::async_log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            verbose_router_logger.debug(traceback.format_exc())
            pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            """
            Update TPM/RPM usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                if "litellm_params" not in kwargs:
                    return
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                if "usage" not in response_obj:
                    return
                total_tokens = response_obj["usage"]["total_tokens"]

                # ------------
                # Setup values
                # ------------
                current_minute = datetime.now().strftime("%H-%M")
                tpm_key = f"{model_group}:tpm:{current_minute}"
                rpm_key = f"{model_group}:rpm:{current_minute}"

                # ------------
                # Update usage
                # ------------
                # update cache

                ## TPM
                request_count_dict = (
                    await self.router_cache.async_get_cache(key=tpm_key) or {}
                )
                request_count_dict[id] = request_count_dict.get(id, 0) + total_tokens

                await self.router_cache.async_set_cache(
                    key=tpm_key, value=request_count_dict, ttl=self.routing_args.ttl
                )

                ## RPM
                request_count_dict = (
                    await self.router_cache.async_get_cache(key=rpm_key) or {}
                )
                request_count_dict[id] = request_count_dict.get(id, 0) + 1

                await self.router_cache.async_set_cache(
                    key=rpm_key, value=request_count_dict, ttl=self.routing_args.ttl
                )

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_router_logger.exception(
                "litellm.router_strategy.lowest_tpm_rpm.py::async_log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            verbose_router_logger.debug(traceback.format_exc())
            pass

    def get_available_deployments(  # noqa: PLR0915
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
    ):
        """
        Returns a deployment with the lowest TPM/RPM usage.
        """
        # get list of potential deployments
        verbose_router_logger.debug(
            f"get_available_deployments - Usage Based. model_group: {model_group}, healthy_deployments: {healthy_deployments}"
        )
        current_minute = datetime.now().strftime("%H-%M")
        tpm_key = f"{model_group}:tpm:{current_minute}"
        rpm_key = f"{model_group}:rpm:{current_minute}"

        tpm_dict = self.router_cache.get_cache(key=tpm_key)
        rpm_dict = self.router_cache.get_cache(key=rpm_key)

        verbose_router_logger.debug(
            f"tpm_key={tpm_key}, tpm_dict: {tpm_dict}, rpm_dict: {rpm_dict}"
        )
        try:
            input_tokens = token_counter(messages=messages, text=input)
        except Exception:
            input_tokens = 0
        verbose_router_logger.debug(f"input_tokens={input_tokens}")
        # -----------------------
        # Find lowest used model
        # ----------------------
        lowest_tpm = float("inf")

        if tpm_dict is None:  # base case - none of the deployments have been used
            # initialize a tpm dict with {model_id: 0}
            tpm_dict = {}
            for deployment in healthy_deployments:
                tpm_dict[deployment["model_info"]["id"]] = 0
        else:
            for d in healthy_deployments:
                ## if healthy deployment not yet used
                if d["model_info"]["id"] not in tpm_dict:
                    tpm_dict[d["model_info"]["id"]] = 0

        all_deployments = tpm_dict

        deployment = None
        for item, item_tpm in all_deployments.items():
            ## get the item from model list
            _deployment = None
            for m in healthy_deployments:
                if item == m["model_info"]["id"]:
                    _deployment = m

            if _deployment is None:
                continue  # skip to next one

            _deployment_tpm = None
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("litellm_params", {}).get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = _deployment.get("model_info", {}).get("tpm")
            if _deployment_tpm is None:
                _deployment_tpm = float("inf")

            _deployment_rpm = None
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("litellm_params", {}).get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = _deployment.get("model_info", {}).get("rpm")
            if _deployment_rpm is None:
                _deployment_rpm = float("inf")

            if item_tpm + input_tokens > _deployment_tpm:
                continue
            elif (rpm_dict is not None and item in rpm_dict) and (
                rpm_dict[item] + 1 >= _deployment_rpm
            ):
                continue
            elif item_tpm < lowest_tpm:
                lowest_tpm = item_tpm
                deployment = _deployment
        print_verbose("returning picked lowest tpm/rpm deployment.")
        return deployment

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\_experimental\mcp_server\db.py ===
import uuid
from typing import Iterable, List, Optional, Set

from litellm.proxy._types import (
    LiteLLM_MCPServerTable,
    LiteLLM_ObjectPermissionTable,
    LiteLLM_TeamTable,
    NewMCPServerRequest,
    SpecialMCPServerName,
    UpdateMCPServerRequest,
    UserAPIKeyAuth,
)
from litellm.proxy.utils import PrismaClient


async def get_all_mcp_servers(
    prisma_client: PrismaClient,
) -> List[LiteLLM_MCPServerTable]:
    """
    Returns all of the mcp servers from the db
    """
    mcp_servers = await prisma_client.db.litellm_mcpservertable.find_many()

    return mcp_servers


async def get_mcp_server(
    prisma_client: PrismaClient, server_id: str
) -> Optional[LiteLLM_MCPServerTable]:
    """
    Returns the matching mcp server from the db iff exists
    """
    mcp_server: Optional[
        LiteLLM_MCPServerTable
    ] = await prisma_client.db.litellm_mcpservertable.find_unique(
        where={
            "server_id": server_id,
        }
    )
    return mcp_server


async def get_mcp_servers(
    prisma_client: PrismaClient, server_ids: Iterable[str]
) -> List[LiteLLM_MCPServerTable]:
    """
    Returns the matching mcp servers from the db with the server_ids
    """
    mcp_servers: List[
        LiteLLM_MCPServerTable
    ] = await prisma_client.db.litellm_mcpservertable.find_many(
        where={
            "server_id": {"in": server_ids},
        }
    )
    return mcp_servers


async def get_mcp_servers_by_verificationtoken(
    prisma_client: PrismaClient, token: str
) -> List[str]:
    """
    Returns the mcp servers from the db for the verification token
    """
    verification_token_record: LiteLLM_TeamTable = (
        await prisma_client.db.litellm_verificationtoken.find_unique(
            where={
                "token": token,
            },
            include={
                "object_permission": True,
            },
        )
    )

    mcp_servers: Optional[List[str]] = []
    if (
        verification_token_record is not None
        and verification_token_record.object_permission is not None
    ):
        mcp_servers = verification_token_record.object_permission.mcp_servers
    return mcp_servers or []


async def get_mcp_servers_by_team(
    prisma_client: PrismaClient, team_id: str
) -> List[str]:
    """
    Returns the mcp servers from the db for the team id
    """
    team_record: LiteLLM_TeamTable = (
        await prisma_client.db.litellm_teamtable.find_unique(
            where={
                "team_id": team_id,
            },
            include={
                "object_permission": True,
            },
        )
    )

    mcp_servers: Optional[List[str]] = []
    if team_record is not None and team_record.object_permission is not None:
        mcp_servers = team_record.object_permission.mcp_servers
    return mcp_servers or []


async def get_all_mcp_servers_for_user(
    prisma_client: PrismaClient,
    user: UserAPIKeyAuth,
) -> List[LiteLLM_MCPServerTable]:
    """
    Get all the mcp servers filtered by the given user has access to.

    Following Least-Privilege Principle - the requestor should only be able to see the mcp servers that they have access to.
    """

    mcp_server_ids: Set[str] = set()
    mcp_servers = []

    # Get the mcp servers for the key
    if user.api_key:
        token_mcp_servers = await get_mcp_servers_by_verificationtoken(
            prisma_client, user.api_key
        )
        mcp_server_ids.update(token_mcp_servers)

        # check for special team membership
        if (
            SpecialMCPServerName.all_team_servers in mcp_server_ids
            and user.team_id is not None
        ):
            team_mcp_servers = await get_mcp_servers_by_team(
                prisma_client, user.team_id
            )
            mcp_server_ids.update(team_mcp_servers)

    if len(mcp_server_ids) > 0:
        mcp_servers = await get_mcp_servers(prisma_client, mcp_server_ids)

    return mcp_servers


async def get_objectpermissions_for_mcp_server(
    prisma_client: PrismaClient, mcp_server_id: str
) -> List[LiteLLM_ObjectPermissionTable]:
    """
    Get all the object permissions records and the associated team and verficiationtoken records that have access to the mcp server
    """
    object_permission_records = (
        await prisma_client.db.litellm_objectpermissiontable.find_many(
            where={
                "mcp_servers": {"has": mcp_server_id},
            },
            include={
                "teams": True,
                "verification_tokens": True,
            },
        )
    )

    return object_permission_records


async def get_virtualkeys_for_mcp_server(
    prisma_client: PrismaClient, server_id: str
) -> List:
    """
    Get all the virtual keys that have access to the mcp server
    """
    virtual_keys = await prisma_client.db.litellm_verificationtoken.find_many(
        where={
            "mcp_servers": {"has": server_id},
        },
    )

    if virtual_keys is None:
        return []
    return virtual_keys


async def delete_mcp_server_from_team(prisma_client: PrismaClient, server_id: str):
    """
    Remove the mcp server from the team
    """
    pass


async def delete_mcp_server_from_virtualkey():
    """
    Remove the mcp server from the virtual key
    """
    pass


async def delete_mcp_server(
    prisma_client: PrismaClient, server_id: str
) -> Optional[LiteLLM_MCPServerTable]:
    """
    Delete the mcp server from the db by server_id

    Returns the deleted mcp server record if it exists, otherwise None
    """
    deleted_server = await prisma_client.db.litellm_mcpservertable.delete(
        where={
            "server_id": server_id,
        },
    )
    return deleted_server


async def create_mcp_server(
    prisma_client: PrismaClient, data: NewMCPServerRequest, touched_by: str
) -> LiteLLM_MCPServerTable:
    """
    Create a new mcp server record in the db
    """
    if data.server_id is None:
        data.server_id = str(uuid.uuid4())

    mcp_server_record = await prisma_client.db.litellm_mcpservertable.create(
        data={
            **data.model_dump(),
            "created_by": touched_by,
            "updated_by": touched_by,
        }
    )
    return mcp_server_record


async def update_mcp_server(
    prisma_client: PrismaClient, data: UpdateMCPServerRequest, touched_by: str
) -> LiteLLM_MCPServerTable:
    """
    Update a new mcp server record in the db
    """
    mcp_server_record = await prisma_client.db.litellm_mcpservertable.update(
        where={
            "server_id": data.server_id,
        },
        data={
            **data.model_dump(),
            "created_by": touched_by,
            "updated_by": touched_by,
        },
    )
    return mcp_server_record

# === NexusCore/openenv\Lib\site-packages\matplotlib\tri\_triangulation.py ===
import sys

import numpy as np

from matplotlib import _api


class Triangulation:
    """
    An unstructured triangular grid consisting of npoints points and
    ntri triangles.  The triangles can either be specified by the user
    or automatically generated using a Delaunay triangulation.

    Parameters
    ----------
    x, y : (npoints,) array-like
        Coordinates of grid points.
    triangles : (ntri, 3) array-like of int, optional
        For each triangle, the indices of the three points that make
        up the triangle, ordered in an anticlockwise manner.  If not
        specified, the Delaunay triangulation is calculated.
    mask : (ntri,) array-like of bool, optional
        Which triangles are masked out.

    Attributes
    ----------
    triangles : (ntri, 3) array of int
        For each triangle, the indices of the three points that make
        up the triangle, ordered in an anticlockwise manner. If you want to
        take the *mask* into account, use `get_masked_triangles` instead.
    mask : (ntri, 3) array of bool or None
        Masked out triangles.
    is_delaunay : bool
        Whether the Triangulation is a calculated Delaunay
        triangulation (where *triangles* was not specified) or not.

    Notes
    -----
    For a Triangulation to be valid it must not have duplicate points,
    triangles formed from colinear points, or overlapping triangles.
    """
    def __init__(self, x, y, triangles=None, mask=None):
        from matplotlib import _qhull

        self.x = np.asarray(x, dtype=np.float64)
        self.y = np.asarray(y, dtype=np.float64)
        if self.x.shape != self.y.shape or self.x.ndim != 1:
            raise ValueError("x and y must be equal-length 1D arrays, but "
                             f"found shapes {self.x.shape!r} and "
                             f"{self.y.shape!r}")

        self.mask = None
        self._edges = None
        self._neighbors = None
        self.is_delaunay = False

        if triangles is None:
            # No triangulation specified, so use matplotlib._qhull to obtain
            # Delaunay triangulation.
            self.triangles, self._neighbors = _qhull.delaunay(x, y, sys.flags.verbose)
            self.is_delaunay = True
        else:
            # Triangulation specified. Copy, since we may correct triangle
            # orientation.
            try:
                self.triangles = np.array(triangles, dtype=np.int32, order='C')
            except ValueError as e:
                raise ValueError('triangles must be a (N, 3) int array, not '
                                 f'{triangles!r}') from e
            if self.triangles.ndim != 2 or self.triangles.shape[1] != 3:
                raise ValueError(
                    'triangles must be a (N, 3) int array, but found shape '
                    f'{self.triangles.shape!r}')
            if self.triangles.max() >= len(self.x):
                raise ValueError(
                    'triangles are indices into the points and must be in the '
                    f'range 0 <= i < {len(self.x)} but found value '
                    f'{self.triangles.max()}')
            if self.triangles.min() < 0:
                raise ValueError(
                    'triangles are indices into the points and must be in the '
                    f'range 0 <= i < {len(self.x)} but found value '
                    f'{self.triangles.min()}')

        # Underlying C++ object is not created until first needed.
        self._cpp_triangulation = None

        # Default TriFinder not created until needed.
        self._trifinder = None

        self.set_mask(mask)

    def calculate_plane_coefficients(self, z):
        """
        Calculate plane equation coefficients for all unmasked triangles from
        the point (x, y) coordinates and specified z-array of shape (npoints).
        The returned array has shape (npoints, 3) and allows z-value at (x, y)
        position in triangle tri to be calculated using
        ``z = array[tri, 0] * x  + array[tri, 1] * y + array[tri, 2]``.
        """
        return self.get_cpp_triangulation().calculate_plane_coefficients(z)

    @property
    def edges(self):
        """
        Return integer array of shape (nedges, 2) containing all edges of
        non-masked triangles.

        Each row defines an edge by its start point index and end point
        index.  Each edge appears only once, i.e. for an edge between points
        *i*  and *j*, there will only be either *(i, j)* or *(j, i)*.
        """
        if self._edges is None:
            self._edges = self.get_cpp_triangulation().get_edges()
        return self._edges

    def get_cpp_triangulation(self):
        """
        Return the underlying C++ Triangulation object, creating it
        if necessary.
        """
        from matplotlib import _tri
        if self._cpp_triangulation is None:
            self._cpp_triangulation = _tri.Triangulation(
                # For unset arrays use empty tuple which has size of zero.
                self.x, self.y, self.triangles,
                self.mask if self.mask is not None else (),
                self._edges if self._edges is not None else (),
                self._neighbors if self._neighbors is not None else (),
                not self.is_delaunay)
        return self._cpp_triangulation

    def get_masked_triangles(self):
        """
        Return an array of triangles taking the mask into account.
        """
        if self.mask is not None:
            return self.triangles[~self.mask]
        else:
            return self.triangles

    @staticmethod
    def get_from_args_and_kwargs(*args, **kwargs):
        """
        Return a Triangulation object from the args and kwargs, and
        the remaining args and kwargs with the consumed values removed.

        There are two alternatives: either the first argument is a
        Triangulation object, in which case it is returned, or the args
        and kwargs are sufficient to create a new Triangulation to
        return.  In the latter case, see Triangulation.__init__ for
        the possible args and kwargs.
        """
        if isinstance(args[0], Triangulation):
            triangulation, *args = args
            if 'triangles' in kwargs:
                _api.warn_external(
                    "Passing the keyword 'triangles' has no effect when also "
                    "passing a Triangulation")
            if 'mask' in kwargs:
                _api.warn_external(
                    "Passing the keyword 'mask' has no effect when also "
                    "passing a Triangulation")
        else:
            x, y, triangles, mask, args, kwargs = \
                Triangulation._extract_triangulation_params(args, kwargs)
            triangulation = Triangulation(x, y, triangles, mask)
        return triangulation, args, kwargs

    @staticmethod
    def _extract_triangulation_params(args, kwargs):
        x, y, *args = args
        # Check triangles in kwargs then args.
        triangles = kwargs.pop('triangles', None)
        from_args = False
        if triangles is None and args:
            triangles = args[0]
            from_args = True
        if triangles is not None:
            try:
                triangles = np.asarray(triangles, dtype=np.int32)
            except ValueError:
                triangles = None
        if triangles is not None and (triangles.ndim != 2 or
                                      triangles.shape[1] != 3):
            triangles = None
        if triangles is not None and from_args:
            args = args[1:]  # Consumed first item in args.
        # Check for mask in kwargs.
        mask = kwargs.pop('mask', None)
        return x, y, triangles, mask, args, kwargs

    def get_trifinder(self):
        """
        Return the default `matplotlib.tri.TriFinder` of this
        triangulation, creating it if necessary.  This allows the same
        TriFinder object to be easily shared.
        """
        if self._trifinder is None:
            # Default TriFinder class.
            from matplotlib.tri._trifinder import TrapezoidMapTriFinder
            self._trifinder = TrapezoidMapTriFinder(self)
        return self._trifinder

    @property
    def neighbors(self):
        """
        Return integer array of shape (ntri, 3) containing neighbor triangles.

        For each triangle, the indices of the three triangles that
        share the same edges, or -1 if there is no such neighboring
        triangle.  ``neighbors[i, j]`` is the triangle that is the neighbor
        to the edge from point index ``triangles[i, j]`` to point index
        ``triangles[i, (j+1)%3]``.
        """
        if self._neighbors is None:
            self._neighbors = self.get_cpp_triangulation().get_neighbors()
        return self._neighbors

    def set_mask(self, mask):
        """
        Set or clear the mask array.

        Parameters
        ----------
        mask : None or bool array of length ntri
        """
        if mask is None:
            self.mask = None
        else:
            self.mask = np.asarray(mask, dtype=bool)
            if self.mask.shape != (self.triangles.shape[0],):
                raise ValueError('mask array must have same length as '
                                 'triangles array')

        # Set mask in C++ Triangulation.
        if self._cpp_triangulation is not None:
            self._cpp_triangulation.set_mask(
                self.mask if self.mask is not None else ())

        # Clear derived fields so they are recalculated when needed.
        self._edges = None
        self._neighbors = None

        # Recalculate TriFinder if it exists.
        if self._trifinder is not None:
            self._trifinder._initialize()

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\_src_pyf.py ===
import os
import re

# START OF CODE VENDORED FROM `numpy.distutils.from_template`
#############################################################
"""
process_file(filename)

  takes templated file .xxx.src and produces .xxx file where .xxx
  is .pyf .f90 or .f using the following template rules:

  '<..>' denotes a template.

  All function and subroutine blocks in a source file with names that
  contain '<..>' will be replicated according to the rules in '<..>'.

  The number of comma-separated words in '<..>' will determine the number of
  replicates.

  '<..>' may have two different forms, named and short. For example,

  named:
   <p=d,s,z,c> where anywhere inside a block '<p>' will be replaced with
   'd', 's', 'z', and 'c' for each replicate of the block.

   <_c>  is already defined: <_c=s,d,c,z>
   <_t>  is already defined: <_t=real,double precision,complex,double complex>

  short:
   <s,d,c,z>, a short form of the named, useful when no <p> appears inside
   a block.

  In general, '<..>' contains a comma separated list of arbitrary
  expressions. If these expression must contain a comma|leftarrow|rightarrow,
  then prepend the comma|leftarrow|rightarrow with a backslash.

  If an expression matches '\\<index>' then it will be replaced
  by <index>-th expression.

  Note that all '<..>' forms in a block must have the same number of
  comma-separated entries.

 Predefined named template rules:
  <prefix=s,d,c,z>
  <ftype=real,double precision,complex,double complex>
  <ftypereal=real,double precision,\\0,\\1>
  <ctype=float,double,complex_float,complex_double>
  <ctypereal=float,double,\\0,\\1>
"""

routine_start_re = re.compile(r'(\n|\A)((     (\$|\*))|)\s*(subroutine|function)\b', re.I)
routine_end_re = re.compile(r'\n\s*end\s*(subroutine|function)\b.*(\n|\Z)', re.I)
function_start_re = re.compile(r'\n     (\$|\*)\s*function\b', re.I)

def parse_structure(astr):
    """ Return a list of tuples for each function or subroutine each
    tuple is the start and end of a subroutine or function to be
    expanded.
    """

    spanlist = []
    ind = 0
    while True:
        m = routine_start_re.search(astr, ind)
        if m is None:
            break
        start = m.start()
        if function_start_re.match(astr, start, m.end()):
            while True:
                i = astr.rfind('\n', ind, start)
                if i == -1:
                    break
                start = i
                if astr[i:i + 7] != '\n     $':
                    break
        start += 1
        m = routine_end_re.search(astr, m.end())
        ind = end = (m and m.end() - 1) or len(astr)
        spanlist.append((start, end))
    return spanlist


template_re = re.compile(r"<\s*(\w[\w\d]*)\s*>")
named_re = re.compile(r"<\s*(\w[\w\d]*)\s*=\s*(.*?)\s*>")
list_re = re.compile(r"<\s*((.*?))\s*>")

def find_repl_patterns(astr):
    reps = named_re.findall(astr)
    names = {}
    for rep in reps:
        name = rep[0].strip() or unique_key(names)
        repl = rep[1].replace(r'\,', '@comma@')
        thelist = conv(repl)
        names[name] = thelist
    return names

def find_and_remove_repl_patterns(astr):
    names = find_repl_patterns(astr)
    astr = re.subn(named_re, '', astr)[0]
    return astr, names


item_re = re.compile(r"\A\\(?P<index>\d+)\Z")
def conv(astr):
    b = astr.split(',')
    l = [x.strip() for x in b]
    for i in range(len(l)):
        m = item_re.match(l[i])
        if m:
            j = int(m.group('index'))
            l[i] = l[j]
    return ','.join(l)

def unique_key(adict):
    """ Obtain a unique key given a dictionary."""
    allkeys = list(adict.keys())
    done = False
    n = 1
    while not done:
        newkey = f'__l{n}'
        if newkey in allkeys:
            n += 1
        else:
            done = True
    return newkey


template_name_re = re.compile(r'\A\s*(\w[\w\d]*)\s*\Z')
def expand_sub(substr, names):
    substr = substr.replace(r'\>', '@rightarrow@')
    substr = substr.replace(r'\<', '@leftarrow@')
    lnames = find_repl_patterns(substr)
    substr = named_re.sub(r"<\1>", substr)  # get rid of definition templates

    def listrepl(mobj):
        thelist = conv(mobj.group(1).replace(r'\,', '@comma@'))
        if template_name_re.match(thelist):
            return f"<{thelist}>"
        name = None
        for key in lnames.keys():    # see if list is already in dictionary
            if lnames[key] == thelist:
                name = key
        if name is None:      # this list is not in the dictionary yet
            name = unique_key(lnames)
            lnames[name] = thelist
        return f"<{name}>"

    # convert all lists to named templates
    # new names are constructed as needed
    substr = list_re.sub(listrepl, substr)

    numsubs = None
    base_rule = None
    rules = {}
    for r in template_re.findall(substr):
        if r not in rules:
            thelist = lnames.get(r, names.get(r, None))
            if thelist is None:
                raise ValueError(f'No replicates found for <{r}>')
            if r not in names and not thelist.startswith('_'):
                names[r] = thelist
            rule = [i.replace('@comma@', ',') for i in thelist.split(',')]
            num = len(rule)

            if numsubs is None:
                numsubs = num
                rules[r] = rule
                base_rule = r
            elif num == numsubs:
                rules[r] = rule
            else:
                rules_base_rule = ','.join(rules[base_rule])
                print("Mismatch in number of replacements "
                      f"(base <{base_rule}={rules_base_rule}>) "
                      f"for <{r}={thelist}>. Ignoring.")
    if not rules:
        return substr

    def namerepl(mobj):
        name = mobj.group(1)
        return rules.get(name, (k + 1) * [name])[k]

    newstr = ''
    for k in range(numsubs):
        newstr += template_re.sub(namerepl, substr) + '\n\n'

    newstr = newstr.replace('@rightarrow@', '>')
    newstr = newstr.replace('@leftarrow@', '<')
    return newstr

def process_str(allstr):
    newstr = allstr
    writestr = ''

    struct = parse_structure(newstr)

    oldend = 0
    names = {}
    names.update(_special_names)
    for sub in struct:
        cleanedstr, defs = find_and_remove_repl_patterns(newstr[oldend:sub[0]])
        writestr += cleanedstr
        names.update(defs)
        writestr += expand_sub(newstr[sub[0]:sub[1]], names)
        oldend = sub[1]
    writestr += newstr[oldend:]

    return writestr


include_src_re = re.compile(r"(\n|\A)\s*include\s*['\"](?P<name>[\w\d./\\]+\.src)['\"]", re.I)

def resolve_includes(source):
    d = os.path.dirname(source)
    with open(source) as fid:
        lines = []
        for line in fid:
            m = include_src_re.match(line)
            if m:
                fn = m.group('name')
                if not os.path.isabs(fn):
                    fn = os.path.join(d, fn)
                if os.path.isfile(fn):
                    lines.extend(resolve_includes(fn))
                else:
                    lines.append(line)
            else:
                lines.append(line)
    return lines

def process_file(source):
    lines = resolve_includes(source)
    return process_str(''.join(lines))


_special_names = find_repl_patterns('''
<_c=s,d,c,z>
<_t=real,double precision,complex,double complex>
<prefix=s,d,c,z>
<ftype=real,double precision,complex,double complex>
<ctype=float,double,complex_float,complex_double>
<ftypereal=real,double precision,\\0,\\1>
<ctypereal=float,double,\\0,\\1>
''')

# END OF CODE VENDORED FROM `numpy.distutils.from_template`
###########################################################

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\sphinxext.py ===
"""
    pygments.sphinxext
    ~~~~~~~~~~~~~~~~~~

    Sphinx extension to generate automatic documentation of lexers,
    formatters and filters.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys

from docutils import nodes
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from sphinx.util.nodes import nested_parse_with_titles


MODULEDOC = '''
.. module:: %s

%s
%s
'''

LEXERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames:   %s
    :MIME types:  %s

    %s

    %s

'''

FMTERDOC = '''
.. class:: %s

    :Short names: %s
    :Filenames: %s

    %s

'''

FILTERDOC = '''
.. class:: %s

    :Name: %s

    %s

'''


class PygmentsDoc(Directive):
    """
    A directive to collect all lexers/formatters/filters and generate
    autoclass directives for them.
    """
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        self.filenames = set()
        if self.arguments[0] == 'lexers':
            out = self.document_lexers()
        elif self.arguments[0] == 'formatters':
            out = self.document_formatters()
        elif self.arguments[0] == 'filters':
            out = self.document_filters()
        elif self.arguments[0] == 'lexers_overview':
            out = self.document_lexers_overview()
        else:
            raise Exception('invalid argument for "pygmentsdoc" directive')
        node = nodes.compound()
        vl = ViewList(out.split('\n'), source='')
        nested_parse_with_titles(self.state, vl, node)
        for fn in self.filenames:
            self.state.document.settings.record_dependencies.add(fn)
        return node.children

    def document_lexers_overview(self):
        """Generate a tabular overview of all lexers.

        The columns are the lexer name, the extensions handled by this lexer
        (or "None"), the aliases and a link to the lexer class."""
        from pip._vendor.pygments.lexers._mapping import LEXERS
        from pip._vendor.pygments.lexers import find_lexer_class
        out = []

        table = []

        def format_link(name, url):
            if url:
                return f'`{name} <{url}>`_'
            return name

        for classname, data in sorted(LEXERS.items(), key=lambda x: x[1][1].lower()):
            lexer_cls = find_lexer_class(data[1])
            extensions = lexer_cls.filenames + lexer_cls.alias_filenames

            table.append({
                'name': format_link(data[1], lexer_cls.url),
                'extensions': ', '.join(extensions).replace('*', '\\*').replace('_', '\\') or 'None',
                'aliases': ', '.join(data[2]),
                'class': f'{data[0]}.{classname}'
            })

        column_names = ['name', 'extensions', 'aliases', 'class']
        column_lengths = [max([len(row[column]) for row in table if row[column]])
                          for column in column_names]

        def write_row(*columns):
            """Format a table row"""
            out = []
            for length, col in zip(column_lengths, columns):
                if col:
                    out.append(col.ljust(length))
                else:
                    out.append(' '*length)

            return ' '.join(out)

        def write_seperator():
            """Write a table separator row"""
            sep = ['='*c for c in column_lengths]
            return write_row(*sep)

        out.append(write_seperator())
        out.append(write_row('Name', 'Extension(s)', 'Short name(s)', 'Lexer class'))
        out.append(write_seperator())
        for row in table:
            out.append(write_row(
                row['name'],
                row['extensions'],
                row['aliases'],
                f':class:`~{row["class"]}`'))
        out.append(write_seperator())

        return '\n'.join(out)

    def document_lexers(self):
        from pip._vendor.pygments.lexers._mapping import LEXERS
        from pip._vendor import pygments
        import inspect
        import pathlib

        out = []
        modules = {}
        moduledocstrings = {}
        for classname, data in sorted(LEXERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            if not cls.__doc__:
                print(f"Warning: {classname} does not have a docstring.")
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')

            example_file = getattr(cls, '_example', None)
            if example_file:
                p = pathlib.Path(inspect.getabsfile(pygments)).parent.parent /\
                    'tests' / 'examplefiles' / example_file
                content = p.read_text(encoding='utf-8')
                if not content:
                    raise Exception(
                        f"Empty example file '{example_file}' for lexer "
                        f"{classname}")

                if data[2]:
                    lexer_name = data[2][0]
                    docstring += '\n\n    .. admonition:: Example\n'
                    docstring += f'\n      .. code-block:: {lexer_name}\n\n'
                    for line in content.splitlines():
                        docstring += f'          {line}\n'

            if cls.version_added:
                version_line = f'.. versionadded:: {cls.version_added}'
            else:
                version_line = ''

            modules.setdefault(module, []).append((
                classname,
                ', '.join(data[2]) or 'None',
                ', '.join(data[3]).replace('*', '\\*').replace('_', '\\') or 'None',
                ', '.join(data[4]) or 'None',
                docstring,
                version_line))
            if module not in moduledocstrings:
                moddoc = mod.__doc__
                if isinstance(moddoc, bytes):
                    moddoc = moddoc.decode('utf8')
                moduledocstrings[module] = moddoc

        for module, lexers in sorted(modules.items(), key=lambda x: x[0]):
            if moduledocstrings[module] is None:
                raise Exception(f"Missing docstring for {module}")
            heading = moduledocstrings[module].splitlines()[4].strip().rstrip('.')
            out.append(MODULEDOC % (module, heading, '-'*len(heading)))
            for data in lexers:
                out.append(LEXERDOC % data)

        return ''.join(out)

    def document_formatters(self):
        from pip._vendor.pygments.formatters import FORMATTERS

        out = []
        for classname, data in sorted(FORMATTERS.items(), key=lambda x: x[0]):
            module = data[0]
            mod = __import__(module, None, None, [classname])
            self.filenames.add(mod.__file__)
            cls = getattr(mod, classname)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            heading = cls.__name__
            out.append(FMTERDOC % (heading, ', '.join(data[2]) or 'None',
                                   ', '.join(data[3]).replace('*', '\\*') or 'None',
                                   docstring))
        return ''.join(out)

    def document_filters(self):
        from pip._vendor.pygments.filters import FILTERS

        out = []
        for name, cls in FILTERS.items():
            self.filenames.add(sys.modules[cls.__module__].__file__)
            docstring = cls.__doc__
            if isinstance(docstring, bytes):
                docstring = docstring.decode('utf8')
            out.append(FILTERDOC % (cls.__name__, name, docstring))
        return ''.join(out)


def setup(app):
    app.add_directive('pygmentsdoc', PygmentsDoc)

# === NexusCore/evaluation\evaluate\multi_turn\gen_plus_solution_multiround.py ===
import argparse
import os
import torch
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from evalplus.data import (get_human_eval_plus, 
    write_jsonl,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from utils import sanitize_solution,check_correctness,get_groundtruth,SUCCESS
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from copy import deepcopy

MAX_TRY = 2

def build_humaneval_instruction(languge: str, question: str):
    return '''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given code to do completion:
```{}
{}
```
Please continue to complete the function with {} programming language. You are not allowed to modify the given code and do the completion only. 

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''.strip().format(languge.lower(), question.strip(),languge.lower(),languge.lower())

build_mbpp_instruction='''You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
Here is the given problem and test examples:
{}

Please use the {} programming language to solve this problem.
Please make sure that your code includes the functions from the test samples and that the input and output formats of these functions match the test samples.

Please return all completed codes in one code block. 
This code block should be in the following format:
```{}
# Your codes here
```

@@ Response
'''

def generate_multi_round(problem, expected_output, example, lang, tokenizer, model, name, flags):
    if flags.dataset=="humaneval":
        prompt = build_humaneval_instruction(lang, example['prompt'])
    elif flags.dataset=="mbpp":
        prompt = build_mbpp_instruction.strip().format(example['prompt'],"python","python")
    inputs = tokenizer.apply_chat_template(
        [{'role': 'user', 'content': prompt }],
        return_tensors="pt"
    ).to(model.device)
    stop_id = tokenizer.convert_tokens_to_ids("<|EOT|>")
    assert isinstance(stop_id, int), "Invalid tokenizer, EOT id not found"
    max_new_tokens=1024
    outputs = model.generate(
        inputs, 
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
        temperature=0,
    )
    output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
    solution = {k:v for k,v in example.items()}
    solution["solution"]=output
    sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)
    attempt = 1
    judge = False
    modify = False
    code = sanitized_solution["solution"]
    while attempt==1 or sanitized_solution["solution"]!="":
        args = (
            flags.dataset,
            0,
            problem,
            sanitized_solution["solution"],
            expected_output,
            flags.version,
            True,  # fast_check
            example["task_id"]+f'_{attempt}',
            flags.min_time_limit,
            flags.gt_time_limit_factor,
        )
        result = check_correctness(*args)
        if flags.version=="base" and result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        elif flags.version=="plus" and result["plus"][0]==result["base"][0]==SUCCESS:
            code = sanitized_solution["solution"]
            if attempt==2:
                modify = True
            judge = True
            break
        else:
            attempt += 1    
            if attempt > MAX_TRY:
                code = sanitized_solution["solution"]
                break
            execution_feedback=""
            if flags.version=="base":
                execution_feedback=result["base"][2]
            elif flags.version=="plus":
                if result["base"][0]!=SUCCESS:
                    execution_feedback+=result["base"][2]
                    if "The results aren't as expected." in execution_feedback:
                        if result["plus"][0]!=SUCCESS:
                            execution_feedback+="\n"+result["plus"][2]
                else:
                    execution_feedback=result["plus"][2]
            prompt +="""
{}

@@ Instruction
Execution result: 
{}
""".format(solution["solution"],execution_feedback)
            inputs = tokenizer.apply_chat_template(
                [{'role': 'user', 'content': prompt }],
                return_tensors="pt"
            ).to(model.device)

            outputs = model.generate(
                inputs, 
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                temperature=0,
            )
            output = tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)
            solution = {k:v for k,v in example.items()}
            solution["solution"]=output 
            sanitized_solution = sanitize_solution(deepcopy(solution),flags.eofs)

    return code,judge,modify


def gen_solution(args):
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    fail_list=[]
    model_path = args.model
    logging.info(f"model:{model_path}")
    model_name =model_path.replace("/", "_")
    lang = "python"
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    output_file = os.path.join(args.output_path,model_name,f"multiround_{args.dataset}_{args.version}_solutions-sanitized.jsonl")
    if os.path.exists(output_file):
        logging.info(f"Old sample jsonl file exists, remove it. {output_file}")
        os.remove(output_file)

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    logging.info("load tokenizer {} from {} over.".format(tokenizer.__class__, model_path))
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    model.eval()

    modelname=model_path.replace("/", "_")
    if args.dataset=="humaneval":
        problems = get_human_eval_plus()
        examples = problems.items()
        dataset_hash = get_human_eval_plus_hash()
        expected_outputs = get_groundtruth(problems, dataset_hash, [])
    else:
        problems = get_mbpp_plus()
        examples = problems.items()
        dataset_hash = get_mbpp_plus_hash()
        expected_outputs = get_groundtruth(
                problems,
                dataset_hash,
                MBPP_OUTPUT_NOT_NONE_TASKS,
            )
    logging.info("Read {} examples for evaluation over.".format(len(examples)))
    a,b = 0,0
    total_modify = 0
    for task_id,example in tqdm(examples, desc='Generating'):
        problem = problems[task_id]
        expected_output = expected_outputs[task_id]
        code,judge,modify = generate_multi_round(problem,expected_output,example, lang, tokenizer, model, modelname,args)
        gen_sample=[dict(task_id=task_id, solution=code)]
        write_jsonl(output_file, gen_sample ,append=True)

        if modify:
            total_modify += 1
        if judge:
            a += 1
        else:
            b += 1
            fail_list.append(task_id)
        result = a/(a+b)
        print ("pass num :",a)
        print ("total num:",a+b)
        print ('pass rate: '+str(result))
        print ("num modify: "+str(total_modify))
        print ("judge:",judge)
        print ('modify: '+str(modify))
        print ("fail list:",fail_list)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, help="model path")
    parser.add_argument('--output_path', type=str, help="output path", default="./multiround_output")
    parser.add_argument('--log_file', type=str, help="log file name", default="gen_humaneval_plus_solution_singleround.log")
    parser.add_argument("--min-time-limit", default=1, type=float)
    parser.add_argument("--gt-time-limit-factor", default=4.0, type=float)
    parser.add_argument(
        "--version", required=True, type=str, choices=["base", "plus"]
    )
    parser.add_argument(
        "--dataset", required=True, type=str, choices=["humaneval", "mbpp"]
    )

    args = parser.parse_args()
    args.eofs=None

    model_name = args.model.replace("/", "_")
    os.makedirs(os.path.join(args.output_path,model_name),exist_ok=True)
    logfile=os.path.join(args.output_path,model_name,args.log_file)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - \n%(message)s')
    file_handler.setFormatter(formatter)  
    logging.getLogger().addHandler(file_handler)

    gen_solution(args)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\embed\transformation.py ===
"""
Transformation logic from OpenAI /v1/embeddings format to Cohere's /v1/embed format.

Why separate file? Make it easy to see how transformation works

Convers
- v3 embedding models
- v2 embedding models

Docs - https://docs.cohere.com/v2/reference/embed
"""

from typing import Any, List, Optional, Union, cast

import httpx

import litellm
from litellm import COHERE_DEFAULT_EMBEDDING_INPUT_TYPE
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm import BaseEmbeddingConfig
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.llms.bedrock import (
    CohereEmbeddingRequest,
    CohereEmbeddingRequestWithModel,
)
from litellm.types.llms.openai import AllEmbeddingInputValues, AllMessageValues
from litellm.types.utils import EmbeddingResponse, PromptTokensDetailsWrapper, Usage
from litellm.utils import is_base64_encoded

from ..common_utils import CohereError


class CohereEmbeddingConfig(BaseEmbeddingConfig):
    """
    Reference: https://docs.cohere.com/v2/reference/embed
    """

    def __init__(self) -> None:
        pass

    def get_supported_openai_params(self, model: str) -> List[str]:
        return ["encoding_format", "dimensions"]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool = False,
    ) -> dict:
        for k, v in non_default_params.items():
            if k == "encoding_format":
                if isinstance(v, list):
                    optional_params["embedding_types"] = v
                else:
                    optional_params["embedding_types"] = [v]
            elif k == "dimensions":
                optional_params["output_dimension"] = v
        return optional_params

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
        default_headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"
        headers = {**default_headers, **headers}
        return headers

    def _is_v3_model(self, model: str) -> bool:
        return "3" in model

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        return api_base or "https://api.cohere.ai/v2/embed"

    def _transform_request(
        self, model: str, input: List[str], inference_params: dict
    ) -> CohereEmbeddingRequestWithModel:
        is_encoded = False
        for input_str in input:
            is_encoded = is_base64_encoded(input_str)

        if is_encoded:  # check if string is b64 encoded image or not
            transformed_request = CohereEmbeddingRequestWithModel(
                model=model,
                images=input,
                input_type="image",
            )
        else:
            transformed_request = CohereEmbeddingRequestWithModel(
                model=model,
                texts=input,
                input_type=COHERE_DEFAULT_EMBEDDING_INPUT_TYPE,
            )

        for k, v in inference_params.items():
            transformed_request[k] = v  # type: ignore

        return transformed_request

    def transform_embedding_request(
        self,
        model: str,
        input: AllEmbeddingInputValues,
        optional_params: dict,
        headers: dict,
    ) -> dict:
        if isinstance(input, list) and (
            isinstance(input[0], list) or isinstance(input[0], int)
        ):
            raise ValueError("Input must be a list of strings")
        return cast(
            dict,
            self._transform_request(
                model=model,
                input=cast(List[str], input) if isinstance(input, List) else [input],
                inference_params=optional_params,
            ),
        )

    def _calculate_usage(self, input: List[str], encoding: Any, meta: dict) -> Usage:
        input_tokens = 0

        text_tokens: Optional[int] = meta.get("billed_units", {}).get("input_tokens")

        image_tokens: Optional[int] = meta.get("billed_units", {}).get("images")

        prompt_tokens_details: Optional[PromptTokensDetailsWrapper] = None
        if image_tokens is None and text_tokens is None:
            for text in input:
                input_tokens += len(encoding.encode(text))
        else:
            prompt_tokens_details = PromptTokensDetailsWrapper(
                image_tokens=image_tokens,
                text_tokens=text_tokens,
            )
            if image_tokens:
                input_tokens += image_tokens
            if text_tokens:
                input_tokens += text_tokens

        return Usage(
            prompt_tokens=input_tokens,
            completion_tokens=0,
            total_tokens=input_tokens,
            prompt_tokens_details=prompt_tokens_details,
        )

    def _transform_response(
        self,
        response: httpx.Response,
        api_key: Optional[str],
        logging_obj: LiteLLMLoggingObj,
        data: Union[dict, CohereEmbeddingRequest],
        model_response: EmbeddingResponse,
        model: str,
        encoding: Any,
        input: list,
    ) -> EmbeddingResponse:
        response_json = response.json()
        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=response_json,
        )
        """
            response 
            {
                'object': "list",
                'data': [
                
                ]
                'model', 
                'usage'
            }
        """
        embeddings = response_json["embeddings"]
        output_data = []
        for k, embedding_list in embeddings.items():
            for idx, embedding in enumerate(embedding_list):
                output_data.append(
                    {"object": "embedding", "index": idx, "embedding": embedding}
                )
        model_response.object = "list"
        model_response.data = output_data
        model_response.model = model
        input_tokens = 0
        for text in input:
            input_tokens += len(encoding.encode(text))

        setattr(
            model_response,
            "usage",
            self._calculate_usage(input, encoding, response_json.get("meta", {})),
        )

        return model_response

    def transform_embedding_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: EmbeddingResponse,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        request_data: dict,
        optional_params: dict,
        litellm_params: dict,
    ) -> EmbeddingResponse:
        return self._transform_response(
            response=raw_response,
            api_key=api_key,
            logging_obj=logging_obj,
            data=request_data,
            model_response=model_response,
            model=model,
            encoding=litellm.encoding,
            input=logging_obj.model_call_details["input"],
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return CohereError(
            status_code=status_code,
            message=error_message,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_ribes.py ===
from nltk.translate.ribes_score import corpus_ribes, word_rank_alignment


def test_ribes_empty_worder():  # worder as in word order
    # Verifies that these two sentences have no alignment,
    # and hence have the lowest possible RIBES score.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's neat and all but the reference's different".split()

    assert word_rank_alignment(ref, hyp) == []

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes_one_worder():
    # Verifies that these two sentences have just one match,
    # and the RIBES score for this sentence with very little
    # correspondence is 0.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's nice and all but the reference's different".split()

    assert word_rank_alignment(ref, hyp) == [3]

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes_two_worder():
    # Verifies that these two sentences have two matches,
    # but still get the lowest possible RIBES score due
    # to the lack of similarity.
    hyp = "This is a nice sentence which I quite like".split()
    ref = "Okay well that's nice and all but the reference is different".split()

    assert word_rank_alignment(ref, hyp) == [9, 3]

    list_of_refs = [[ref]]
    hypotheses = [hyp]
    assert corpus_ribes(list_of_refs, hypotheses) == 0.0


def test_ribes():
    # Based on the doctest of the corpus_ribes function
    hyp1 = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "which",
        "ensures",
        "that",
        "the",
        "military",
        "always",
        "obeys",
        "the",
        "commands",
        "of",
        "the",
        "party",
    ]
    ref1a = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "that",
        "ensures",
        "that",
        "the",
        "military",
        "will",
        "forever",
        "heed",
        "Party",
        "commands",
    ]
    ref1b = [
        "It",
        "is",
        "the",
        "guiding",
        "principle",
        "which",
        "guarantees",
        "the",
        "military",
        "forces",
        "always",
        "being",
        "under",
        "the",
        "command",
        "of",
        "the",
        "Party",
    ]
    ref1c = [
        "It",
        "is",
        "the",
        "practical",
        "guide",
        "for",
        "the",
        "army",
        "always",
        "to",
        "heed",
        "the",
        "directions",
        "of",
        "the",
        "party",
    ]

    hyp2 = [
        "he",
        "read",
        "the",
        "book",
        "because",
        "he",
        "was",
        "interested",
        "in",
        "world",
        "history",
    ]
    ref2a = [
        "he",
        "was",
        "interested",
        "in",
        "world",
        "history",
        "because",
        "he",
        "read",
        "the",
        "book",
    ]

    list_of_refs = [[ref1a, ref1b, ref1c], [ref2a]]
    hypotheses = [hyp1, hyp2]

    score = corpus_ribes(list_of_refs, hypotheses)

    assert round(score, 4) == 0.3597


def test_no_zero_div():
    # Regression test for Issue 2529, assure that no ZeroDivisionError is thrown.
    hyp1 = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "which",
        "ensures",
        "that",
        "the",
        "military",
        "always",
        "obeys",
        "the",
        "commands",
        "of",
        "the",
        "party",
    ]
    ref1a = [
        "It",
        "is",
        "a",
        "guide",
        "to",
        "action",
        "that",
        "ensures",
        "that",
        "the",
        "military",
        "will",
        "forever",
        "heed",
        "Party",
        "commands",
    ]
    ref1b = [
        "It",
        "is",
        "the",
        "guiding",
        "principle",
        "which",
        "guarantees",
        "the",
        "military",
        "forces",
        "always",
        "being",
        "under",
        "the",
        "command",
        "of",
        "the",
        "Party",
    ]
    ref1c = [
        "It",
        "is",
        "the",
        "practical",
        "guide",
        "for",
        "the",
        "army",
        "always",
        "to",
        "heed",
        "the",
        "directions",
        "of",
        "the",
        "party",
    ]

    hyp2 = ["he", "read", "the"]
    ref2a = ["he", "was", "interested", "in", "world", "history", "because", "he"]

    list_of_refs = [[ref1a, ref1b, ref1c], [ref2a]]
    hypotheses = [hyp1, hyp2]

    score = corpus_ribes(list_of_refs, hypotheses)

    assert round(score, 4) == 0.1688

# === NexusCore/openenv\Lib\site-packages\nltk\test\unit\test_wordnet.py ===
"""
Unit tests for nltk.corpus.wordnet
See also nltk/test/wordnet.doctest
"""

import unittest

from nltk.corpus import wordnet as wn
from nltk.corpus import wordnet_ic as wnic

wn.ensure_loaded()
S = wn.synset
L = wn.lemma


class WordnNetDemo(unittest.TestCase):
    def test_retrieve_synset(self):
        move_synset = S("go.v.21")
        self.assertEqual(move_synset.name(), "move.v.15")
        self.assertEqual(move_synset.lemma_names(), ["move", "go"])
        self.assertEqual(
            move_synset.definition(), "have a turn; make one's move in a game"
        )
        self.assertEqual(move_synset.examples(), ["Can I go now?"])

    def test_retrieve_synsets(self):
        self.assertEqual(sorted(wn.synsets("zap", pos="n")), [S("zap.n.01")])
        self.assertEqual(
            sorted(wn.synsets("zap", pos="v")),
            [S("microwave.v.01"), S("nuke.v.01"), S("zap.v.01"), S("zap.v.02")],
        )

    def test_hyperhyponyms(self):
        # Not every synset as hypernyms()
        self.assertEqual(S("travel.v.01").hypernyms(), [])
        self.assertEqual(S("travel.v.02").hypernyms(), [S("travel.v.03")])
        self.assertEqual(S("travel.v.03").hypernyms(), [])

        # Test hyper-/hyponyms.
        self.assertEqual(S("breakfast.n.1").hypernyms(), [S("meal.n.01")])
        first_five_meal_hypo = [
            S("banquet.n.02"),
            S("bite.n.04"),
            S("breakfast.n.01"),
            S("brunch.n.01"),
            S("buffet.n.02"),
        ]
        self.assertEqual(sorted(S("meal.n.1").hyponyms())[:5], first_five_meal_hypo)
        self.assertEqual(S("Austen.n.1").instance_hypernyms(), [S("writer.n.01")])
        first_five_composer_hypo = [
            S("ambrose.n.01"),
            S("bach.n.01"),
            S("barber.n.01"),
            S("bartok.n.01"),
            S("beethoven.n.01"),
        ]
        self.assertEqual(
            sorted(S("composer.n.1").instance_hyponyms())[:5], first_five_composer_hypo
        )

        # Test root hyper-/hyponyms
        self.assertEqual(S("person.n.01").root_hypernyms(), [S("entity.n.01")])
        self.assertEqual(S("sail.v.01").root_hypernyms(), [S("travel.v.01")])
        self.assertEqual(
            sorted(S("fall.v.12").root_hypernyms()), [S("act.v.01"), S("fall.v.17")]
        )

    def test_derivationally_related_forms(self):
        # Test `derivationally_related_forms()`
        self.assertEqual(
            L("zap.v.03.nuke").derivationally_related_forms(),
            [L("atomic_warhead.n.01.nuke")],
        )
        self.assertEqual(
            L("zap.v.03.atomize").derivationally_related_forms(),
            [L("atomization.n.02.atomization")],
        )
        self.assertEqual(
            L("zap.v.03.atomise").derivationally_related_forms(),
            [L("atomization.n.02.atomisation")],
        )
        self.assertEqual(L("zap.v.03.zap").derivationally_related_forms(), [])

    def test_meronyms_holonyms(self):
        # Test meronyms, holonyms.
        self.assertEqual(
            sorted(S("dog.n.01").member_holonyms()), [S("canis.n.01"), S("pack.n.06")]
        )
        self.assertEqual(S("dog.n.01").part_meronyms(), [S("flag.n.07")])

        self.assertEqual(S("faculty.n.2").member_meronyms(), [S("professor.n.01")])
        self.assertEqual(S("copilot.n.1").member_holonyms(), [S("crew.n.01")])

        self.assertEqual(
            sorted(S("table.n.2").part_meronyms()),
            [S("leg.n.03"), S("tabletop.n.01"), S("tableware.n.01")],
        )
        self.assertEqual(S("course.n.7").part_holonyms(), [S("meal.n.01")])

        self.assertEqual(
            sorted(S("water.n.1").substance_meronyms()),
            [S("hydrogen.n.01"), S("oxygen.n.01")],
        )
        self.assertEqual(
            sorted(S("gin.n.1").substance_holonyms()),
            [
                S("gin_and_it.n.01"),
                S("gin_and_tonic.n.01"),
                S("martini.n.01"),
                S("pink_lady.n.01"),
            ],
        )

    def test_antonyms(self):
        # Test antonyms.
        self.assertEqual(
            L("leader.n.1.leader").antonyms(), [L("follower.n.01.follower")]
        )
        self.assertEqual(
            L("increase.v.1.increase").antonyms(), [L("decrease.v.01.decrease")]
        )

    def test_misc_relations(self):
        # Test misc relations.
        self.assertEqual(S("snore.v.1").entailments(), [S("sleep.v.01")])
        self.assertEqual(
            sorted(S("heavy.a.1").similar_tos()),
            [
                S("dense.s.03"),
                S("doughy.s.01"),
                S("heavier-than-air.s.01"),
                S("hefty.s.02"),
                S("massive.s.04"),
                S("non-buoyant.s.01"),
                S("ponderous.s.02"),
            ],
        )
        self.assertEqual(S("light.a.1").attributes(), [S("weight.n.01")])
        self.assertEqual(S("heavy.a.1").attributes(), [S("weight.n.01")])

        # Test pertainyms.
        self.assertEqual(
            L("English.a.1.English").pertainyms(), [L("england.n.01.England")]
        )

    def test_lch(self):
        # Test LCH.
        self.assertEqual(
            S("person.n.01").lowest_common_hypernyms(S("dog.n.01")),
            [S("organism.n.01")],
        )
        self.assertEqual(
            S("woman.n.01").lowest_common_hypernyms(S("girlfriend.n.02")),
            [S("woman.n.01")],
        )

    def test_domains(self):
        # Test domains.
        self.assertEqual(S("code.n.03").topic_domains(), [S("computer_science.n.01")])
        self.assertEqual(S("pukka.a.01").region_domains(), [S("india.n.01")])
        self.assertEqual(S("freaky.a.01").usage_domains(), [S("slang.n.02")])

    def test_in_topic_domains(self):
        # Test in domains.
        self.assertEqual(
            sorted(S("computer_science.n.01").in_topic_domains())[0], S("access.n.05")
        )
        self.assertEqual(
            sorted(S("germany.n.01").in_region_domains())[23], S("trillion.n.02")
        )
        self.assertEqual(
            sorted(S("slang.n.02").in_usage_domains())[1], S("airhead.n.01")
        )

    def test_wordnet_similarities(self):
        # Path based similarities.
        self.assertAlmostEqual(S("cat.n.01").path_similarity(S("cat.n.01")), 1.0)
        self.assertAlmostEqual(S("dog.n.01").path_similarity(S("cat.n.01")), 0.2)
        self.assertAlmostEqual(
            S("car.n.01").path_similarity(S("automobile.v.01")),
            S("automobile.v.01").path_similarity(S("car.n.01")),
        )
        self.assertAlmostEqual(
            S("big.a.01").path_similarity(S("dog.n.01")),
            S("dog.n.01").path_similarity(S("big.a.01")),
        )
        self.assertAlmostEqual(
            S("big.a.01").path_similarity(S("long.a.01")),
            S("long.a.01").path_similarity(S("big.a.01")),
        )
        self.assertAlmostEqual(
            S("dog.n.01").lch_similarity(S("cat.n.01")), 2.028, places=3
        )
        self.assertAlmostEqual(
            S("dog.n.01").wup_similarity(S("cat.n.01")), 0.8571, places=3
        )
        self.assertAlmostEqual(
            S("car.n.01").wup_similarity(S("automobile.v.01")),
            S("automobile.v.01").wup_similarity(S("car.n.01")),
        )
        self.assertAlmostEqual(
            S("big.a.01").wup_similarity(S("dog.n.01")),
            S("dog.n.01").wup_similarity(S("big.a.01")),
        )
        self.assertAlmostEqual(
            S("big.a.01").wup_similarity(S("long.a.01")),
            S("long.a.01").wup_similarity(S("big.a.01")),
        )
        self.assertAlmostEqual(
            S("big.a.01").lch_similarity(S("long.a.01")),
            S("long.a.01").lch_similarity(S("big.a.01")),
        )
        # Information Content similarities.
        brown_ic = wnic.ic("ic-brown.dat")
        self.assertAlmostEqual(
            S("dog.n.01").jcn_similarity(S("cat.n.01"), brown_ic), 0.4497, places=3
        )
        semcor_ic = wnic.ic("ic-semcor.dat")
        self.assertAlmostEqual(
            S("dog.n.01").lin_similarity(S("cat.n.01"), semcor_ic), 0.8863, places=3
        )

    def test_omw_lemma_no_trailing_underscore(self):
        expected = sorted(
            [
                "popolna_sprememba_v_mišljenju",
                "popoln_obrat",
                "preobrat",
                "preobrat_v_mišljenju",
            ]
        )
        self.assertEqual(sorted(S("about-face.n.02").lemma_names(lang="slv")), expected)

    def test_iterable_type_for_all_lemma_names(self):
        # Duck-test for iterables.
        # See https://stackoverflow.com/a/36230057/610569
        cat_lemmas = wn.all_lemma_names(lang="cat")
        eng_lemmas = wn.all_lemma_names(lang="eng")

        self.assertTrue(hasattr(eng_lemmas, "__iter__"))
        self.assertTrue(hasattr(eng_lemmas, "__next__") or hasattr(eng_lemmas, "next"))
        self.assertTrue(eng_lemmas.__iter__() is eng_lemmas)

        self.assertTrue(hasattr(cat_lemmas, "__iter__"))
        self.assertTrue(hasattr(cat_lemmas, "__next__") or hasattr(eng_lemmas, "next"))
        self.assertTrue(cat_lemmas.__iter__() is cat_lemmas)

# === NexusCore/openenv\Lib\site-packages\trio\_tests\check_type_completeness.py ===
#!/usr/bin/env python3
"""This is a file that wraps calls to `pyright --verifytypes`, achieving two things:
1. give an error if docstrings are missing.
    pyright will give a number of missing docstrings, and error messages, but not exit with a non-zero value.
2. filter out specific errors we don't care about.
    this is largely due to 1, but also because Trio does some very complex stuff and --verifytypes has few to no ways of ignoring specific errors.

If this check is giving you false alarms, you can ignore them by adding logic to `has_docstring_at_runtime`, in the main loop in `check_type`, or by updating the json file.
"""
from __future__ import annotations

# this file is not run as part of the tests, instead it's run standalone from check.sh
import argparse
import json
import subprocess
import sys
from pathlib import Path

import trio
import trio.testing

# not needed if everything is working, but if somebody does something to generate
# tons of errors, we can be nice and stop them from getting 3*tons of output
printed_diagnostics: set[str] = set()


# TODO: consider checking manually without `--ignoreexternal`, and/or
# removing it from the below call later on.
def run_pyright(platform: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "pyright",
            # Specify a platform and version to keep imported modules consistent.
            f"--pythonplatform={platform}",
            "--pythonversion=3.9",
            "--verifytypes=trio",
            "--outputjson",
            "--ignoreexternal",
        ],
        capture_output=True,
    )


def has_docstring_at_runtime(name: str) -> bool:
    """Pyright gives us an object identifier of xx.yy.zz
    This function tries to decompose that into its constituent parts, such that we
    can resolve it, in order to check whether it has a `__doc__` at runtime and
    verifytypes misses it because we're doing overly fancy stuff.
    """
    # This assert is solely for stopping isort from removing our imports of trio & trio.testing
    # It could also be done with isort:skip, but that'd also disable import sorting and the like.
    assert trio.testing is not None

    # figure out what part of the name is the module, so we can "import" it
    name_parts = name.split(".")
    assert name_parts[0] == "trio"
    if name_parts[1] == "tests":
        return True

    # traverse down the remaining identifiers with getattr
    obj = trio
    try:
        for obj_name in name_parts[1:]:
            obj = getattr(obj, obj_name)
    except AttributeError as exc:
        # asynciowrapper does funky getattr stuff
        if "AsyncIOWrapper" in str(exc) or name in (
            # Symbols not existing on all platforms, so we can't dynamically inspect them.
            # Manually confirmed to have docstrings but pyright doesn't see them due to
            # export shenanigans. TODO: actually manually confirm that.
            # In theory we could verify these at runtime, probably by running the script separately
            # on separate platforms. It might also be a decent idea to work the other way around,
            # a la test_static_tool_sees_class_members
            # darwin
            "trio.lowlevel.current_kqueue",
            "trio.lowlevel.monitor_kevent",
            "trio.lowlevel.wait_kevent",
            "trio._core._io_kqueue._KqueueStatistics",
            # windows
            "trio._socket.SocketType.share",
            "trio._core._io_windows._WindowsStatistics",
            "trio._core._windows_cffi.Handle",
            "trio.lowlevel.current_iocp",
            "trio.lowlevel.monitor_completion_key",
            "trio.lowlevel.readinto_overlapped",
            "trio.lowlevel.register_with_iocp",
            "trio.lowlevel.wait_overlapped",
            "trio.lowlevel.write_overlapped",
            "trio.lowlevel.WaitForSingleObject",
            "trio.socket.fromshare",
            # linux
            # this test will fail on linux, but I don't develop on linux. So the next
            # person to do so is very welcome to open a pull request and populate with
            # objects
            # TODO: these are erroring on all platforms, why?
            "trio._highlevel_generic.StapledStream.send_stream",
            "trio._highlevel_generic.StapledStream.receive_stream",
            "trio._ssl.SSLStream.transport_stream",
            "trio._file_io._HasFileNo",
            "trio._file_io._HasFileNo.fileno",
        ):
            return True

        else:
            print(
                f"Pyright sees {name} at runtime, but unable to getattr({obj.__name__}, {obj_name}).",
                file=sys.stderr,
            )
            return False
    return bool(obj.__doc__)


def check_type(
    platform: str,
    full_diagnostics_file: Path | None,
    expected_errors: list[object],
) -> list[object]:
    # convince isort we use the trio import
    assert trio is not None

    # run pyright, load output into json
    res = run_pyright(platform)
    current_result = json.loads(res.stdout)

    if res.stderr:
        print(res.stderr, file=sys.stderr)

    if full_diagnostics_file:
        with open(full_diagnostics_file, "a") as f:
            json.dump(current_result, f, sort_keys=True, indent=4)

    errors = []

    for symbol in current_result["typeCompleteness"]["symbols"]:
        diagnostics = symbol["diagnostics"]
        name = symbol["name"]
        for diagnostic in diagnostics:
            message = diagnostic["message"]
            if name in (
                "trio._path.PosixPath",
                "trio._path.WindowsPath",
            ) and message.startswith("Type of base class "):
                continue

            if name.startswith("trio._path.Path"):
                if message.startswith("No docstring found for"):
                    continue
                if message.startswith(
                    "Type is missing type annotation and could be inferred differently by type checkers",
                ):
                    continue

            # ignore errors about missing docstrings if they're available at runtime
            if message.startswith("No docstring found for"):
                if has_docstring_at_runtime(symbol["name"]):
                    continue
            else:
                # Missing docstring messages include the name of the object.
                # Other errors don't, so we add it.
                message = f"{name}: {message}"
            if message not in expected_errors and message not in printed_diagnostics:
                print(f"new error: {message}", file=sys.stderr)
            errors.append(message)
            printed_diagnostics.add(message)

        continue

    return errors


def main(args: argparse.Namespace) -> int:
    if args.full_diagnostics_file:
        full_diagnostics_file = Path(args.full_diagnostics_file)
        full_diagnostics_file.write_text("")
    else:
        full_diagnostics_file = None

    errors_by_platform_file = Path(__file__).parent / "_check_type_completeness.json"
    if errors_by_platform_file.exists():
        with open(errors_by_platform_file) as f:
            errors_by_platform = json.load(f)
    else:
        errors_by_platform = {"Linux": [], "Windows": [], "Darwin": [], "all": []}

    changed = False
    for platform in "Linux", "Windows", "Darwin":
        platform_errors = errors_by_platform[platform] + errors_by_platform["all"]
        print("*" * 20, f"\nChecking {platform}...")
        errors = check_type(platform, full_diagnostics_file, platform_errors)

        new_errors = [e for e in errors if e not in platform_errors]
        missing_errors = [e for e in platform_errors if e not in errors]

        if new_errors:
            print(
                f"New errors introduced in `pyright --verifytypes`. Fix them, or ignore them by modifying {errors_by_platform_file}, either manually or with '--overwrite-file'.",
                file=sys.stderr,
            )
            changed = True
        if missing_errors:
            print(
                f"Congratulations, you have resolved existing errors! Please remove them from {errors_by_platform_file}, either manually or with '--overwrite-file'.",
                file=sys.stderr,
            )
            changed = True
            print(missing_errors, file=sys.stderr)

        errors_by_platform[platform] = errors
    print("*" * 20)

    # cut down the size of the json file by a lot, and make it easier to parse for
    # humans, by moving errors that appear on all platforms to a separate category
    errors_by_platform["all"] = []
    for e in errors_by_platform["Linux"].copy():
        if e in errors_by_platform["Darwin"] and e in errors_by_platform["Windows"]:
            for platform in "Linux", "Windows", "Darwin":
                errors_by_platform[platform].remove(e)
            errors_by_platform["all"].append(e)

    if changed and args.overwrite_file:
        with open(errors_by_platform_file, "w") as f:
            json.dump(errors_by_platform, f, indent=4, sort_keys=True)
            # newline at end of file
            f.write("\n")

    # True -> 1 -> non-zero exit value -> error
    return changed


parser = argparse.ArgumentParser()
parser.add_argument(
    "--overwrite-file",
    action="store_true",
    default=False,
    help="Use this flag to overwrite the current stored results. Either in CI together with a diff check, or to avoid having to manually correct it.",
)
parser.add_argument(
    "--full-diagnostics-file",
    type=Path,
    default=None,
    help="Use this for debugging, it will dump the output of all three pyright runs by platform into this file.",
)
args = parser.parse_args()

assert __name__ == "__main__", "This script should be run standalone"
sys.exit(main(args))

# === NexusCore/openenv\Lib\site-packages\win32\Demos\desktopmanager.py ===
# Demonstrates using a taskbar icon to create and navigate between desktops

import _thread
import io
import time
import traceback

import pywintypes
import win32api
import win32con
import win32gui
import win32process
import win32service

## "Shell_TrayWnd" is class of system tray window, broadcasts "TaskbarCreated" when initialized


def desktop_name_dlgproc(hwnd, msg, wparam, lparam):
    """Handles messages from the desktop name dialog box"""
    if msg in (win32con.WM_CLOSE, win32con.WM_DESTROY):
        win32gui.DestroyWindow(hwnd)
    elif msg == win32con.WM_COMMAND:
        if wparam == win32con.IDOK:
            desktop_name = win32gui.GetDlgItemText(hwnd, 72)
            print("new desktop name: ", desktop_name)
            win32gui.DestroyWindow(hwnd)
            create_desktop(desktop_name)

        elif wparam == win32con.IDCANCEL:
            win32gui.DestroyWindow(hwnd)


def get_new_desktop_name(parent_hwnd):
    """Create a dialog box to ask the user for name of desktop to be created"""
    msgs = {
        win32con.WM_COMMAND: desktop_name_dlgproc,
        win32con.WM_CLOSE: desktop_name_dlgproc,
        win32con.WM_DESTROY: desktop_name_dlgproc,
    }
    # dlg item [type, caption, id, (x,y,cx,cy), style, ex style
    style = (
        win32con.WS_BORDER
        | win32con.WS_VISIBLE
        | win32con.WS_CAPTION
        | win32con.WS_SYSMENU
    )  ## |win32con.DS_SYSMODAL
    h = win32gui.CreateDialogIndirect(
        win32api.GetModuleHandle(None),
        [
            ["One ugly dialog box !", (100, 100, 200, 100), style, 0],
            [
                "Button",
                "Create",
                win32con.IDOK,
                (10, 10, 30, 20),
                win32con.WS_VISIBLE
                | win32con.WS_TABSTOP
                | win32con.BS_HOLLOW
                | win32con.BS_DEFPUSHBUTTON,
            ],
            [
                "Button",
                "Never mind",
                win32con.IDCANCEL,
                (45, 10, 50, 20),
                win32con.WS_VISIBLE | win32con.WS_TABSTOP | win32con.BS_HOLLOW,
            ],
            ["Static", "Desktop name:", 71, (10, 40, 70, 10), win32con.WS_VISIBLE],
            ["Edit", "", 72, (75, 40, 90, 10), win32con.WS_VISIBLE],
        ],
        parent_hwnd,
        msgs,
    )  ## parent_hwnd, msgs)

    win32gui.EnableWindow(h, True)
    hcontrol = win32gui.GetDlgItem(h, 72)
    win32gui.EnableWindow(hcontrol, True)
    win32gui.SetFocus(hcontrol)


def new_icon(hdesk, desktop_name):
    """Runs as a thread on each desktop to create a new tray icon and handle its messages"""
    global id
    id += 1
    hdesk.SetThreadDesktop()
    ## apparently the threads can't use same hinst, so each needs its own window class
    windowclassname = "PythonDesktopManager" + desktop_name
    wc = win32gui.WNDCLASS()
    wc.hInstance = win32api.GetModuleHandle(None)
    wc.lpszClassName = windowclassname
    wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW | win32con.CS_GLOBALCLASS
    wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
    wc.hbrBackground = win32con.COLOR_WINDOW
    wc.lpfnWndProc = icon_wndproc
    windowclass = win32gui.RegisterClass(wc)
    style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
    hwnd = win32gui.CreateWindow(
        windowclass,
        "dm_" + desktop_name,
        win32con.WS_SYSMENU,
        0,
        0,
        win32con.CW_USEDEFAULT,
        win32con.CW_USEDEFAULT,
        0,
        0,
        wc.hInstance,
        None,
    )
    win32gui.UpdateWindow(hwnd)
    flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
    notify_info = (
        hwnd,
        id,
        flags,
        win32con.WM_USER + 20,
        hicon,
        "Desktop Manager (%s)" % desktop_name,
    )
    window_info[hwnd] = notify_info
    ## wait for explorer to initialize system tray for new desktop
    tray_found = 0
    while not tray_found:
        try:
            tray_found = win32gui.FindWindow("Shell_TrayWnd", None)
        except win32gui.error:
            traceback.print_exc
            time.sleep(0.5)
    win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_info)
    win32gui.PumpMessages()


def create_desktop(desktop_name, start_explorer=1):
    """Creates a new desktop and spawns a thread running on it
    Will also start a new icon thread on an existing desktop
    """
    sa = pywintypes.SECURITY_ATTRIBUTES()
    sa.bInheritHandle = 1

    try:
        hdesk = win32service.CreateDesktop(
            desktop_name, 0, win32con.MAXIMUM_ALLOWED, sa
        )
    except win32service.error:
        traceback.print_exc()
        errbuf = io.StringIO()
        traceback.print_exc(None, errbuf)
        win32api.MessageBox(0, errbuf.getvalue(), "Desktop creation failed")
        return
    if start_explorer:
        s = win32process.STARTUPINFO()
        s.lpDesktop = desktop_name
        prc_info = win32process.CreateProcess(
            None,
            "Explorer.exe",
            None,
            None,
            True,
            win32con.CREATE_NEW_CONSOLE,
            None,
            "c:\\",
            s,
        )

    th = _thread.start_new_thread(new_icon, (hdesk, desktop_name))
    hdesk.SwitchDesktop()


def icon_wndproc(hwnd, msg, wp, lp):
    """Window proc for the tray icons"""
    if lp == win32con.WM_LBUTTONDOWN:
        ## popup menu won't disappear if you don't do this
        win32gui.SetForegroundWindow(hwnd)

        curr_desktop = win32service.OpenInputDesktop(0, True, win32con.MAXIMUM_ALLOWED)
        curr_desktop_name = win32service.GetUserObjectInformation(
            curr_desktop, win32con.UOI_NAME
        )
        winsta = win32service.GetProcessWindowStation()
        desktops = winsta.EnumDesktops()
        m = win32gui.CreatePopupMenu()
        desktop_cnt = len(desktops)
        ## *don't* create an item 0
        for d in range(1, desktop_cnt + 1):
            mf_flags = win32con.MF_STRING
            ## if you switch to winlogon yourself, there's nothing there and you're stuck
            if desktops[d - 1].lower() in ("winlogon", "disconnect"):
                mf_flags |= win32con.MF_GRAYED | win32con.MF_DISABLED
            if desktops[d - 1] == curr_desktop_name:
                mf_flags |= win32con.MF_CHECKED
            win32gui.AppendMenu(m, mf_flags, d, desktops[d - 1])
        win32gui.AppendMenu(m, win32con.MF_STRING, desktop_cnt + 1, "Create new ...")
        win32gui.AppendMenu(m, win32con.MF_STRING, desktop_cnt + 2, "Exit")

        x, y = win32gui.GetCursorPos()
        d = win32gui.TrackPopupMenu(
            m,
            win32con.TPM_LEFTBUTTON | win32con.TPM_RETURNCMD | win32con.TPM_NONOTIFY,
            x,
            y,
            0,
            hwnd,
            None,
        )
        win32gui.PumpWaitingMessages()
        win32gui.DestroyMenu(m)
        if d == desktop_cnt + 1:  ## Create new
            get_new_desktop_name(hwnd)
        elif d == desktop_cnt + 2:  ## Exit
            win32gui.PostQuitMessage(0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, window_info[hwnd])
            del window_info[hwnd]
            origin_desktop.SwitchDesktop()
        elif d > 0:
            hdesk = win32service.OpenDesktop(
                desktops[d - 1], 0, 0, win32con.MAXIMUM_ALLOWED
            )
            hdesk.SwitchDesktop()
        return 0
    else:
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)


window_info = {}
origin_desktop = win32service.OpenInputDesktop(0, True, win32con.MAXIMUM_ALLOWED)
origin_desktop_name = win32service.GetUserObjectInformation(
    origin_desktop, win32service.UOI_NAME
)

hinst = win32api.GetModuleHandle(None)
try:
    hicon = win32gui.LoadIcon(hinst, 1)  ## python.exe and pythonw.exe
except win32gui.error:
    hicon = win32gui.LoadIcon(hinst, 135)  ## pythonwin's icon
id = 0

create_desktop(str(origin_desktop_name), 0)

## wait for first thread to initialize its icon
while not window_info:
    time.sleep(1)

## exit when last tray icon goes away
while window_info:
    win32gui.PumpWaitingMessages()
    time.sleep(3)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\subprocess.py ===
import logging
import os
import shlex
import subprocess
from typing import Any, Callable, Iterable, List, Literal, Mapping, Optional, Union

from pip._vendor.rich.markup import escape

from pip._internal.cli.spinners import SpinnerInterface, open_spinner
from pip._internal.exceptions import InstallationSubprocessError
from pip._internal.utils.logging import VERBOSE, subprocess_logger
from pip._internal.utils.misc import HiddenText

CommandArgs = List[Union[str, HiddenText]]


def make_command(*args: Union[str, HiddenText, CommandArgs]) -> CommandArgs:
    """
    Create a CommandArgs object.
    """
    command_args: CommandArgs = []
    for arg in args:
        # Check for list instead of CommandArgs since CommandArgs is
        # only known during type-checking.
        if isinstance(arg, list):
            command_args.extend(arg)
        else:
            # Otherwise, arg is str or HiddenText.
            command_args.append(arg)

    return command_args


def format_command_args(args: Union[List[str], CommandArgs]) -> str:
    """
    Format command arguments for display.
    """
    # For HiddenText arguments, display the redacted form by calling str().
    # Also, we don't apply str() to arguments that aren't HiddenText since
    # this can trigger a UnicodeDecodeError in Python 2 if the argument
    # has type unicode and includes a non-ascii character.  (The type
    # checker doesn't ensure the annotations are correct in all cases.)
    return " ".join(
        shlex.quote(str(arg)) if isinstance(arg, HiddenText) else shlex.quote(arg)
        for arg in args
    )


def reveal_command_args(args: Union[List[str], CommandArgs]) -> List[str]:
    """
    Return the arguments in their raw, unredacted form.
    """
    return [arg.secret if isinstance(arg, HiddenText) else arg for arg in args]


def call_subprocess(
    cmd: Union[List[str], CommandArgs],
    show_stdout: bool = False,
    cwd: Optional[str] = None,
    on_returncode: 'Literal["raise", "warn", "ignore"]' = "raise",
    extra_ok_returncodes: Optional[Iterable[int]] = None,
    extra_environ: Optional[Mapping[str, Any]] = None,
    unset_environ: Optional[Iterable[str]] = None,
    spinner: Optional[SpinnerInterface] = None,
    log_failed_cmd: Optional[bool] = True,
    stdout_only: Optional[bool] = False,
    *,
    command_desc: str,
) -> str:
    """
    Args:
      show_stdout: if true, use INFO to log the subprocess's stderr and
        stdout streams.  Otherwise, use DEBUG.  Defaults to False.
      extra_ok_returncodes: an iterable of integer return codes that are
        acceptable, in addition to 0. Defaults to None, which means [].
      unset_environ: an iterable of environment variable names to unset
        prior to calling subprocess.Popen().
      log_failed_cmd: if false, failed commands are not logged, only raised.
      stdout_only: if true, return only stdout, else return both. When true,
        logging of both stdout and stderr occurs when the subprocess has
        terminated, else logging occurs as subprocess output is produced.
    """
    if extra_ok_returncodes is None:
        extra_ok_returncodes = []
    if unset_environ is None:
        unset_environ = []
    # Most places in pip use show_stdout=False. What this means is--
    #
    # - We connect the child's output (combined stderr and stdout) to a
    #   single pipe, which we read.
    # - We log this output to stderr at DEBUG level as it is received.
    # - If DEBUG logging isn't enabled (e.g. if --verbose logging wasn't
    #   requested), then we show a spinner so the user can still see the
    #   subprocess is in progress.
    # - If the subprocess exits with an error, we log the output to stderr
    #   at ERROR level if it hasn't already been displayed to the console
    #   (e.g. if --verbose logging wasn't enabled).  This way we don't log
    #   the output to the console twice.
    #
    # If show_stdout=True, then the above is still done, but with DEBUG
    # replaced by INFO.
    if show_stdout:
        # Then log the subprocess output at INFO level.
        log_subprocess: Callable[..., None] = subprocess_logger.info
        used_level = logging.INFO
    else:
        # Then log the subprocess output using VERBOSE.  This also ensures
        # it will be logged to the log file (aka user_log), if enabled.
        log_subprocess = subprocess_logger.verbose
        used_level = VERBOSE

    # Whether the subprocess will be visible in the console.
    showing_subprocess = subprocess_logger.getEffectiveLevel() <= used_level

    # Only use the spinner if we're not showing the subprocess output
    # and we have a spinner.
    use_spinner = not showing_subprocess and spinner is not None

    log_subprocess("Running command %s", command_desc)
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)
    for name in unset_environ:
        env.pop(name, None)
    try:
        proc = subprocess.Popen(
            # Convert HiddenText objects to the underlying str.
            reveal_command_args(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if not stdout_only else subprocess.PIPE,
            cwd=cwd,
            env=env,
            errors="backslashreplace",
        )
    except Exception as exc:
        if log_failed_cmd:
            subprocess_logger.critical(
                "Error %s while executing command %s",
                exc,
                command_desc,
            )
        raise
    all_output = []
    if not stdout_only:
        assert proc.stdout
        assert proc.stdin
        proc.stdin.close()
        # In this mode, stdout and stderr are in the same pipe.
        while True:
            line: str = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            all_output.append(line + "\n")

            # Show the line immediately.
            log_subprocess(line)
            # Update the spinner.
            if use_spinner:
                assert spinner
                spinner.spin()
        try:
            proc.wait()
        finally:
            if proc.stdout:
                proc.stdout.close()
        output = "".join(all_output)
    else:
        # In this mode, stdout and stderr are in different pipes.
        # We must use communicate() which is the only safe way to read both.
        out, err = proc.communicate()
        # log line by line to preserve pip log indenting
        for out_line in out.splitlines():
            log_subprocess(out_line)
        all_output.append(out)
        for err_line in err.splitlines():
            log_subprocess(err_line)
        all_output.append(err)
        output = out

    proc_had_error = proc.returncode and proc.returncode not in extra_ok_returncodes
    if use_spinner:
        assert spinner
        if proc_had_error:
            spinner.finish("error")
        else:
            spinner.finish("done")
    if proc_had_error:
        if on_returncode == "raise":
            error = InstallationSubprocessError(
                command_description=command_desc,
                exit_code=proc.returncode,
                output_lines=all_output if not showing_subprocess else None,
            )
            if log_failed_cmd:
                subprocess_logger.error("%s", error, extra={"rich": True})
                subprocess_logger.verbose(
                    "[bold magenta]full command[/]: [blue]%s[/]",
                    escape(format_command_args(cmd)),
                    extra={"markup": True},
                )
                subprocess_logger.verbose(
                    "[bold magenta]cwd[/]: %s",
                    escape(cwd or "[inherit]"),
                    extra={"markup": True},
                )

            raise error
        elif on_returncode == "warn":
            subprocess_logger.warning(
                'Command "%s" had error code %s in %s',
                command_desc,
                proc.returncode,
                cwd,
            )
        elif on_returncode == "ignore":
            pass
        else:
            raise ValueError(f"Invalid value: on_returncode={on_returncode!r}")
    return output


def runner_with_spinner_message(message: str) -> Callable[..., None]:
    """Provide a subprocess_runner that shows a spinner message.

    Intended for use with for BuildBackendHookCaller. Thus, the runner has
    an API that matches what's expected by BuildBackendHookCaller.subprocess_runner.
    """

    def runner(
        cmd: List[str],
        cwd: Optional[str] = None,
        extra_environ: Optional[Mapping[str, Any]] = None,
    ) -> None:
        with open_spinner(message) as spinner:
            call_subprocess(
                cmd,
                command_desc=message,
                cwd=cwd,
                extra_environ=extra_environ,
                spinner=spinner,
            )

    return runner

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\requirements.py ===
from typing import Any, Optional

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.req.constructors import install_req_drop_extras
from pip._internal.req.req_install import InstallRequirement

from .base import Candidate, CandidateLookup, Requirement, format_name


class ExplicitRequirement(Requirement):
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate

    def __str__(self) -> str:
        return str(self.candidate)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.candidate!r})"

    def __hash__(self) -> int:
        return hash(self.candidate)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ExplicitRequirement):
            return False
        return self.candidate == other.candidate

    @property
    def project_name(self) -> NormalizedName:
        # No need to canonicalize - the candidate did this
        return self.candidate.project_name

    @property
    def name(self) -> str:
        # No need to canonicalize - the candidate did this
        return self.candidate.name

    def format_for_error(self) -> str:
        return self.candidate.format_for_error()

    def get_candidate_lookup(self) -> CandidateLookup:
        return self.candidate, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return candidate == self.candidate


class SpecifierRequirement(Requirement):
    def __init__(self, ireq: InstallRequirement) -> None:
        assert ireq.link is None, "This is a link, not a specifier"
        self._ireq = ireq
        self._equal_cache: Optional[str] = None
        self._hash: Optional[int] = None
        self._extras = frozenset(canonicalize_name(e) for e in self._ireq.extras)

    @property
    def _equal(self) -> str:
        if self._equal_cache is not None:
            return self._equal_cache

        self._equal_cache = str(self._ireq)
        return self._equal_cache

    def __str__(self) -> str:
        return str(self._ireq.req)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self._ireq.req)!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecifierRequirement):
            return NotImplemented
        return self._equal == other._equal

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash(self._equal)
        return self._hash

    @property
    def project_name(self) -> NormalizedName:
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        return canonicalize_name(self._ireq.req.name)

    @property
    def name(self) -> str:
        return format_name(self.project_name, self._extras)

    def format_for_error(self) -> str:
        # Convert comma-separated specifiers into "A, B, ..., F and G"
        # This makes the specifier a bit more "human readable", without
        # risking a change in meaning. (Hopefully! Not all edge cases have
        # been checked)
        parts = [s.strip() for s in str(self).split(",")]
        if len(parts) == 0:
            return ""
        elif len(parts) == 1:
            return parts[0]

        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, self._ireq

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self.name, (
            f"Internal issue: Candidate is not for this requirement "
            f"{candidate.name} vs {self.name}"
        )
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        spec = self._ireq.req.specifier
        return spec.contains(candidate.version, prereleases=True)


class SpecifierWithoutExtrasRequirement(SpecifierRequirement):
    """
    Requirement backed by an install requirement on a base package.
    Trims extras from its install requirement if there are any.
    """

    def __init__(self, ireq: InstallRequirement) -> None:
        assert ireq.link is None, "This is a link, not a specifier"
        self._ireq = install_req_drop_extras(ireq)
        self._equal_cache: Optional[str] = None
        self._hash: Optional[int] = None
        self._extras = frozenset(canonicalize_name(e) for e in self._ireq.extras)

    @property
    def _equal(self) -> str:
        if self._equal_cache is not None:
            return self._equal_cache

        self._equal_cache = str(self._ireq)
        return self._equal_cache

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecifierWithoutExtrasRequirement):
            return NotImplemented
        return self._equal == other._equal

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash(self._equal)
        return self._hash


class RequiresPythonRequirement(Requirement):
    """A requirement representing Requires-Python metadata."""

    def __init__(self, specifier: SpecifierSet, match: Candidate) -> None:
        self.specifier = specifier
        self._specifier_string = str(specifier)  # for faster __eq__
        self._hash: Optional[int] = None
        self._candidate = match

    def __str__(self) -> str:
        return f"Python {self.specifier}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self.specifier)!r})"

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash((self._specifier_string, self._candidate))
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RequiresPythonRequirement):
            return False
        return (
            self._specifier_string == other._specifier_string
            and self._candidate == other._candidate
        )

    @property
    def project_name(self) -> NormalizedName:
        return self._candidate.project_name

    @property
    def name(self) -> str:
        return self._candidate.name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        if self.specifier.contains(self._candidate.version, prereleases=True):
            return self._candidate, None
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self._candidate.name, "Not Python candidate"
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class UnsatisfiableRequirement(Requirement):
    """A requirement that cannot be satisfied."""

    def __init__(self, name: NormalizedName) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"{self._name} (unavailable)"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self._name)!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnsatisfiableRequirement):
            return NotImplemented
        return self._name == other._name

    def __hash__(self) -> int:
        return hash(self._name)

    @property
    def project_name(self) -> NormalizedName:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return False

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\filenames.py ===
"""
This module implements the algorithm for converting between a "user name" -
something that a user can choose arbitrarily inside a font editor - and a file
name suitable for use in a wide range of operating systems and filesystems.

The `UFO 3 specification <http://unifiedfontobject.org/versions/ufo3/conventions/>`_
provides an example of an algorithm for such conversion, which avoids illegal
characters, reserved file names, ambiguity between upper- and lower-case
characters, and clashes with existing files.

This code was originally copied from
`ufoLib <https://github.com/unified-font-object/ufoLib/blob/8747da7/Lib/ufoLib/filenames.py>`_
by Tal Leming and is copyright (c) 2005-2016, The RoboFab Developers:

-	Erik van Blokland
-	Tal Leming
-	Just van Rossum
"""

illegalCharacters = r"\" * + / : < > ? [ \ ] | \0".split(" ")
illegalCharacters += [chr(i) for i in range(1, 32)]
illegalCharacters += [chr(0x7F)]
reservedFileNames = "CON PRN AUX CLOCK$ NUL A:-Z: COM1".lower().split(" ")
reservedFileNames += "LPT1 LPT2 LPT3 COM2 COM3 COM4".lower().split(" ")
maxFileNameLength = 255


class NameTranslationError(Exception):
    pass


def userNameToFileName(userName, existing=[], prefix="", suffix=""):
    """Converts from a user name to a file name.

    Takes care to avoid illegal characters, reserved file names, ambiguity between
    upper- and lower-case characters, and clashes with existing files.

    Args:
            userName (str): The input file name.
            existing: A case-insensitive list of all existing file names.
            prefix: Prefix to be prepended to the file name.
            suffix: Suffix to be appended to the file name.

    Returns:
            A suitable filename.

    Raises:
            NameTranslationError: If no suitable name could be generated.

    Examples::

            >>> userNameToFileName("a") == "a"
            True
            >>> userNameToFileName("A") == "A_"
            True
            >>> userNameToFileName("AE") == "A_E_"
            True
            >>> userNameToFileName("Ae") == "A_e"
            True
            >>> userNameToFileName("ae") == "ae"
            True
            >>> userNameToFileName("aE") == "aE_"
            True
            >>> userNameToFileName("a.alt") == "a.alt"
            True
            >>> userNameToFileName("A.alt") == "A_.alt"
            True
            >>> userNameToFileName("A.Alt") == "A_.A_lt"
            True
            >>> userNameToFileName("A.aLt") == "A_.aL_t"
            True
            >>> userNameToFileName(u"A.alT") == "A_.alT_"
            True
            >>> userNameToFileName("T_H") == "T__H_"
            True
            >>> userNameToFileName("T_h") == "T__h"
            True
            >>> userNameToFileName("t_h") == "t_h"
            True
            >>> userNameToFileName("F_F_I") == "F__F__I_"
            True
            >>> userNameToFileName("f_f_i") == "f_f_i"
            True
            >>> userNameToFileName("Aacute_V.swash") == "A_acute_V_.swash"
            True
            >>> userNameToFileName(".notdef") == "_notdef"
            True
            >>> userNameToFileName("con") == "_con"
            True
            >>> userNameToFileName("CON") == "C_O_N_"
            True
            >>> userNameToFileName("con.alt") == "_con.alt"
            True
            >>> userNameToFileName("alt.con") == "alt._con"
            True
    """
    # the incoming name must be a str
    if not isinstance(userName, str):
        raise ValueError("The value for userName must be a string.")
    # establish the prefix and suffix lengths
    prefixLength = len(prefix)
    suffixLength = len(suffix)
    # replace an initial period with an _
    # if no prefix is to be added
    if not prefix and userName[0] == ".":
        userName = "_" + userName[1:]
    # filter the user name
    filteredUserName = []
    for character in userName:
        # replace illegal characters with _
        if character in illegalCharacters:
            character = "_"
        # add _ to all non-lower characters
        elif character != character.lower():
            character += "_"
        filteredUserName.append(character)
    userName = "".join(filteredUserName)
    # clip to 255
    sliceLength = maxFileNameLength - prefixLength - suffixLength
    userName = userName[:sliceLength]
    # test for illegal files names
    parts = []
    for part in userName.split("."):
        if part.lower() in reservedFileNames:
            part = "_" + part
        parts.append(part)
    userName = ".".join(parts)
    # test for clash
    fullName = prefix + userName + suffix
    if fullName.lower() in existing:
        fullName = handleClash1(userName, existing, prefix, suffix)
    # finished
    return fullName


def handleClash1(userName, existing=[], prefix="", suffix=""):
    """
    existing should be a case-insensitive list
    of all existing file names.

    >>> prefix = ("0" * 5) + "."
    >>> suffix = "." + ("0" * 10)
    >>> existing = ["a" * 5]

    >>> e = list(existing)
    >>> handleClash1(userName="A" * 5, existing=e,
    ...		prefix=prefix, suffix=suffix) == (
    ... 	'00000.AAAAA000000000000001.0000000000')
    True

    >>> e = list(existing)
    >>> e.append(prefix + "aaaaa" + "1".zfill(15) + suffix)
    >>> handleClash1(userName="A" * 5, existing=e,
    ...		prefix=prefix, suffix=suffix) == (
    ... 	'00000.AAAAA000000000000002.0000000000')
    True

    >>> e = list(existing)
    >>> e.append(prefix + "AAAAA" + "2".zfill(15) + suffix)
    >>> handleClash1(userName="A" * 5, existing=e,
    ...		prefix=prefix, suffix=suffix) == (
    ... 	'00000.AAAAA000000000000001.0000000000')
    True
    """
    # if the prefix length + user name length + suffix length + 15 is at
    # or past the maximum length, silce 15 characters off of the user name
    prefixLength = len(prefix)
    suffixLength = len(suffix)
    if prefixLength + len(userName) + suffixLength + 15 > maxFileNameLength:
        l = prefixLength + len(userName) + suffixLength + 15
        sliceLength = maxFileNameLength - l
        userName = userName[:sliceLength]
    finalName = None
    # try to add numbers to create a unique name
    counter = 1
    while finalName is None:
        name = userName + str(counter).zfill(15)
        fullName = prefix + name + suffix
        if fullName.lower() not in existing:
            finalName = fullName
            break
        else:
            counter += 1
        if counter >= 999999999999999:
            break
    # if there is a clash, go to the next fallback
    if finalName is None:
        finalName = handleClash2(existing, prefix, suffix)
    # finished
    return finalName


def handleClash2(existing=[], prefix="", suffix=""):
    """
    existing should be a case-insensitive list
    of all existing file names.

    >>> prefix = ("0" * 5) + "."
    >>> suffix = "." + ("0" * 10)
    >>> existing = [prefix + str(i) + suffix for i in range(100)]

    >>> e = list(existing)
    >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
    ... 	'00000.100.0000000000')
    True

    >>> e = list(existing)
    >>> e.remove(prefix + "1" + suffix)
    >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
    ... 	'00000.1.0000000000')
    True

    >>> e = list(existing)
    >>> e.remove(prefix + "2" + suffix)
    >>> handleClash2(existing=e, prefix=prefix, suffix=suffix) == (
    ... 	'00000.2.0000000000')
    True
    """
    # calculate the longest possible string
    maxLength = maxFileNameLength - len(prefix) - len(suffix)
    maxValue = int("9" * maxLength)
    # try to find a number
    finalName = None
    counter = 1
    while finalName is None:
        fullName = prefix + str(counter) + suffix
        if fullName.lower() not in existing:
            finalName = fullName
            break
        else:
            counter += 1
        if counter >= maxValue:
            break
    # raise an error if nothing has been found
    if finalName is None:
        raise NameTranslationError("No unique name could be found.")
    # finished
    return finalName


if __name__ == "__main__":
    import doctest
    import sys

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\wire_format.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Constants and static functions to support protocol buffer wire format."""

__author__ = 'robinson@google.com (Will Robinson)'

import struct
from google.protobuf import descriptor
from google.protobuf import message


TAG_TYPE_BITS = 3  # Number of bits used to hold type info in a proto tag.
TAG_TYPE_MASK = (1 << TAG_TYPE_BITS) - 1  # 0x7

# These numbers identify the wire type of a protocol buffer value.
# We use the least-significant TAG_TYPE_BITS bits of the varint-encoded
# tag-and-type to store one of these WIRETYPE_* constants.
# These values must match WireType enum in //google/protobuf/wire_format.h.
WIRETYPE_VARINT = 0
WIRETYPE_FIXED64 = 1
WIRETYPE_LENGTH_DELIMITED = 2
WIRETYPE_START_GROUP = 3
WIRETYPE_END_GROUP = 4
WIRETYPE_FIXED32 = 5
_WIRETYPE_MAX = 5


# Bounds for various integer types.
INT32_MAX = int((1 << 31) - 1)
INT32_MIN = int(-(1 << 31))
UINT32_MAX = (1 << 32) - 1

INT64_MAX = (1 << 63) - 1
INT64_MIN = -(1 << 63)
UINT64_MAX = (1 << 64) - 1

# "struct" format strings that will encode/decode the specified formats.
FORMAT_UINT32_LITTLE_ENDIAN = '<I'
FORMAT_UINT64_LITTLE_ENDIAN = '<Q'
FORMAT_FLOAT_LITTLE_ENDIAN = '<f'
FORMAT_DOUBLE_LITTLE_ENDIAN = '<d'


# We'll have to provide alternate implementations of AppendLittleEndian*() on
# any architectures where these checks fail.
if struct.calcsize(FORMAT_UINT32_LITTLE_ENDIAN) != 4:
  raise AssertionError('Format "I" is not a 32-bit number.')
if struct.calcsize(FORMAT_UINT64_LITTLE_ENDIAN) != 8:
  raise AssertionError('Format "Q" is not a 64-bit number.')


def PackTag(field_number, wire_type):
  """Returns an unsigned 32-bit integer that encodes the field number and
  wire type information in standard protocol message wire format.

  Args:
    field_number: Expected to be an integer in the range [1, 1 << 29)
    wire_type: One of the WIRETYPE_* constants.
  """
  if not 0 <= wire_type <= _WIRETYPE_MAX:
    raise message.EncodeError('Unknown wire type: %d' % wire_type)
  return (field_number << TAG_TYPE_BITS) | wire_type


def UnpackTag(tag):
  """The inverse of PackTag().  Given an unsigned 32-bit number,
  returns a (field_number, wire_type) tuple.
  """
  return (tag >> TAG_TYPE_BITS), (tag & TAG_TYPE_MASK)


def ZigZagEncode(value):
  """ZigZag Transform:  Encodes signed integers so that they can be
  effectively used with varint encoding.  See wire_format.h for
  more details.
  """
  if value >= 0:
    return value << 1
  return (value << 1) ^ (~0)


def ZigZagDecode(value):
  """Inverse of ZigZagEncode()."""
  if not value & 0x1:
    return value >> 1
  return (value >> 1) ^ (~0)



# The *ByteSize() functions below return the number of bytes required to
# serialize "field number + type" information and then serialize the value.


def Int32ByteSize(field_number, int32):
  return Int64ByteSize(field_number, int32)


def Int32ByteSizeNoTag(int32):
  return _VarUInt64ByteSizeNoTag(0xffffffffffffffff & int32)


def Int64ByteSize(field_number, int64):
  # Have to convert to uint before calling UInt64ByteSize().
  return UInt64ByteSize(field_number, 0xffffffffffffffff & int64)


def UInt32ByteSize(field_number, uint32):
  return UInt64ByteSize(field_number, uint32)


def UInt64ByteSize(field_number, uint64):
  return TagByteSize(field_number) + _VarUInt64ByteSizeNoTag(uint64)


def SInt32ByteSize(field_number, int32):
  return UInt32ByteSize(field_number, ZigZagEncode(int32))


def SInt64ByteSize(field_number, int64):
  return UInt64ByteSize(field_number, ZigZagEncode(int64))


def Fixed32ByteSize(field_number, fixed32):
  return TagByteSize(field_number) + 4


def Fixed64ByteSize(field_number, fixed64):
  return TagByteSize(field_number) + 8


def SFixed32ByteSize(field_number, sfixed32):
  return TagByteSize(field_number) + 4


def SFixed64ByteSize(field_number, sfixed64):
  return TagByteSize(field_number) + 8


def FloatByteSize(field_number, flt):
  return TagByteSize(field_number) + 4


def DoubleByteSize(field_number, double):
  return TagByteSize(field_number) + 8


def BoolByteSize(field_number, b):
  return TagByteSize(field_number) + 1


def EnumByteSize(field_number, enum):
  return UInt32ByteSize(field_number, enum)


def StringByteSize(field_number, string):
  return BytesByteSize(field_number, string.encode('utf-8'))


def BytesByteSize(field_number, b):
  return (TagByteSize(field_number)
          + _VarUInt64ByteSizeNoTag(len(b))
          + len(b))


def GroupByteSize(field_number, message):
  return (2 * TagByteSize(field_number)  # START and END group.
          + message.ByteSize())


def MessageByteSize(field_number, message):
  return (TagByteSize(field_number)
          + _VarUInt64ByteSizeNoTag(message.ByteSize())
          + message.ByteSize())


def MessageSetItemByteSize(field_number, msg):
  # First compute the sizes of the tags.
  # There are 2 tags for the beginning and ending of the repeated group, that
  # is field number 1, one with field number 2 (type_id) and one with field
  # number 3 (message).
  total_size = (2 * TagByteSize(1) + TagByteSize(2) + TagByteSize(3))

  # Add the number of bytes for type_id.
  total_size += _VarUInt64ByteSizeNoTag(field_number)

  message_size = msg.ByteSize()

  # The number of bytes for encoding the length of the message.
  total_size += _VarUInt64ByteSizeNoTag(message_size)

  # The size of the message.
  total_size += message_size
  return total_size


def TagByteSize(field_number):
  """Returns the bytes required to serialize a tag with this field number."""
  # Just pass in type 0, since the type won't affect the tag+type size.
  return _VarUInt64ByteSizeNoTag(PackTag(field_number, 0))


# Private helper function for the *ByteSize() functions above.

def _VarUInt64ByteSizeNoTag(uint64):
  """Returns the number of bytes required to serialize a single varint
  using boundary value comparisons. (unrolled loop optimization -WPierce)
  uint64 must be unsigned.
  """
  if uint64 <= 0x7f: return 1
  if uint64 <= 0x3fff: return 2
  if uint64 <= 0x1fffff: return 3
  if uint64 <= 0xfffffff: return 4
  if uint64 <= 0x7ffffffff: return 5
  if uint64 <= 0x3ffffffffff: return 6
  if uint64 <= 0x1ffffffffffff: return 7
  if uint64 <= 0xffffffffffffff: return 8
  if uint64 <= 0x7fffffffffffffff: return 9
  if uint64 > UINT64_MAX:
    raise message.EncodeError('Value out of range: %d' % uint64)
  return 10


NON_PACKABLE_TYPES = (
  descriptor.FieldDescriptor.TYPE_STRING,
  descriptor.FieldDescriptor.TYPE_GROUP,
  descriptor.FieldDescriptor.TYPE_MESSAGE,
  descriptor.FieldDescriptor.TYPE_BYTES
)


def IsTypePackable(field_type):
  """Return true iff packable = true is valid for fields of this type.

  Args:
    field_type: a FieldDescriptor::Type value.

  Returns:
    True iff fields of this type are packable.
  """
  return field_type not in NON_PACKABLE_TYPES

# === NexusCore/openenv\Lib\site-packages\grpc\framework\interfaces\face\utilities.py ===
# Copyright 2015 gRPC authors.
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
"""Utilities for RPC Framework's Face interface."""

import collections

# stream is referenced from specification in this module.
from grpc.framework.common import cardinality
from grpc.framework.common import style
from grpc.framework.foundation import stream  # pylint: disable=unused-import
from grpc.framework.interfaces.face import face


class _MethodImplementation(
    face.MethodImplementation,
    collections.namedtuple(
        "_MethodImplementation",
        [
            "cardinality",
            "style",
            "unary_unary_inline",
            "unary_stream_inline",
            "stream_unary_inline",
            "stream_stream_inline",
            "unary_unary_event",
            "unary_stream_event",
            "stream_unary_event",
            "stream_stream_event",
        ],
    ),
):
    pass


def unary_unary_inline(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a unary-unary RPC method as a callable value
        that takes a request value and an face.ServicerContext object and
        returns a response value.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.UNARY_UNARY,
        style.Service.INLINE,
        behavior,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def unary_stream_inline(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a unary-stream RPC method as a callable
        value that takes a request value and an face.ServicerContext object and
        returns an iterator of response values.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.UNARY_STREAM,
        style.Service.INLINE,
        None,
        behavior,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def stream_unary_inline(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a stream-unary RPC method as a callable
        value that takes an iterator of request values and an
        face.ServicerContext object and returns a response value.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.STREAM_UNARY,
        style.Service.INLINE,
        None,
        None,
        behavior,
        None,
        None,
        None,
        None,
        None,
    )


def stream_stream_inline(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a stream-stream RPC method as a callable
        value that takes an iterator of request values and an
        face.ServicerContext object and returns an iterator of response values.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.STREAM_STREAM,
        style.Service.INLINE,
        None,
        None,
        None,
        behavior,
        None,
        None,
        None,
        None,
    )


def unary_unary_event(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a unary-unary RPC method as a callable
        value that takes a request value, a response callback to which to pass
        the response value of the RPC, and an face.ServicerContext.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.UNARY_UNARY,
        style.Service.EVENT,
        None,
        None,
        None,
        None,
        behavior,
        None,
        None,
        None,
    )


def unary_stream_event(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a unary-stream RPC method as a callable
        value that takes a request value, a stream.Consumer to which to pass the
        response values of the RPC, and an face.ServicerContext.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.UNARY_STREAM,
        style.Service.EVENT,
        None,
        None,
        None,
        None,
        None,
        behavior,
        None,
        None,
    )


def stream_unary_event(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a stream-unary RPC method as a callable
        value that takes a response callback to which to pass the response value
        of the RPC and an face.ServicerContext and returns a stream.Consumer to
        which the request values of the RPC should be passed.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.STREAM_UNARY,
        style.Service.EVENT,
        None,
        None,
        None,
        None,
        None,
        None,
        behavior,
        None,
    )


def stream_stream_event(behavior):
    """Creates an face.MethodImplementation for the given behavior.

    Args:
      behavior: The implementation of a stream-stream RPC method as a callable
        value that takes a stream.Consumer to which to pass the response values
        of the RPC and an face.ServicerContext and returns a stream.Consumer to
        which the request values of the RPC should be passed.

    Returns:
      An face.MethodImplementation derived from the given behavior.
    """
    return _MethodImplementation(
        cardinality.Cardinality.STREAM_STREAM,
        style.Service.EVENT,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        behavior,
    )

# === NexusCore/openenv\Lib\site-packages\openai\resources\audio\speech.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Union
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import (
    StreamedBinaryAPIResponse,
    AsyncStreamedBinaryAPIResponse,
    to_custom_streamed_response_wrapper,
    async_to_custom_streamed_response_wrapper,
)
from ...types.audio import speech_create_params
from ..._base_client import make_request_options
from ...types.audio.speech_model import SpeechModel

__all__ = ["Speech", "AsyncSpeech"]


class Speech(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> SpeechWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return SpeechWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> SpeechWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return SpeechWithStreamingResponse(self)

    def create(
        self,
        *,
        input: str,
        model: Union[str, SpeechModel],
        voice: Union[
            str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
        ],
        instructions: str | NotGiven = NOT_GIVEN,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] | NotGiven = NOT_GIVEN,
        speed: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Generates audio from the input text.

        Args:
          input: The text to generate audio for. The maximum length is 4096 characters.

          model:
              One of the available [TTS models](https://platform.openai.com/docs/models#tts):
              `tts-1`, `tts-1-hd` or `gpt-4o-mini-tts`.

          voice: The voice to use when generating the audio. Supported voices are `alloy`, `ash`,
              `ballad`, `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and
              `verse`. Previews of the voices are available in the
              [Text to speech guide](https://platform.openai.com/docs/guides/text-to-speech#voice-options).

          instructions: Control the voice of your generated audio with additional instructions. Does not
              work with `tts-1` or `tts-1-hd`.

          response_format: The format to audio in. Supported formats are `mp3`, `opus`, `aac`, `flac`,
              `wav`, and `pcm`.

          speed: The speed of the generated audio. Select a value from `0.25` to `4.0`. `1.0` is
              the default. Does not work with `gpt-4o-mini-tts`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "application/octet-stream", **(extra_headers or {})}
        return self._post(
            "/audio/speech",
            body=maybe_transform(
                {
                    "input": input,
                    "model": model,
                    "voice": voice,
                    "instructions": instructions,
                    "response_format": response_format,
                    "speed": speed,
                },
                speech_create_params.SpeechCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )


class AsyncSpeech(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncSpeechWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncSpeechWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncSpeechWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncSpeechWithStreamingResponse(self)

    async def create(
        self,
        *,
        input: str,
        model: Union[str, SpeechModel],
        voice: Union[
            str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
        ],
        instructions: str | NotGiven = NOT_GIVEN,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] | NotGiven = NOT_GIVEN,
        speed: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> _legacy_response.HttpxBinaryResponseContent:
        """
        Generates audio from the input text.

        Args:
          input: The text to generate audio for. The maximum length is 4096 characters.

          model:
              One of the available [TTS models](https://platform.openai.com/docs/models#tts):
              `tts-1`, `tts-1-hd` or `gpt-4o-mini-tts`.

          voice: The voice to use when generating the audio. Supported voices are `alloy`, `ash`,
              `ballad`, `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and
              `verse`. Previews of the voices are available in the
              [Text to speech guide](https://platform.openai.com/docs/guides/text-to-speech#voice-options).

          instructions: Control the voice of your generated audio with additional instructions. Does not
              work with `tts-1` or `tts-1-hd`.

          response_format: The format to audio in. Supported formats are `mp3`, `opus`, `aac`, `flac`,
              `wav`, and `pcm`.

          speed: The speed of the generated audio. Select a value from `0.25` to `4.0`. `1.0` is
              the default. Does not work with `gpt-4o-mini-tts`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"Accept": "application/octet-stream", **(extra_headers or {})}
        return await self._post(
            "/audio/speech",
            body=await async_maybe_transform(
                {
                    "input": input,
                    "model": model,
                    "voice": voice,
                    "instructions": instructions,
                    "response_format": response_format,
                    "speed": speed,
                },
                speech_create_params.SpeechCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=_legacy_response.HttpxBinaryResponseContent,
        )


class SpeechWithRawResponse:
    def __init__(self, speech: Speech) -> None:
        self._speech = speech

        self.create = _legacy_response.to_raw_response_wrapper(
            speech.create,
        )


class AsyncSpeechWithRawResponse:
    def __init__(self, speech: AsyncSpeech) -> None:
        self._speech = speech

        self.create = _legacy_response.async_to_raw_response_wrapper(
            speech.create,
        )


class SpeechWithStreamingResponse:
    def __init__(self, speech: Speech) -> None:
        self._speech = speech

        self.create = to_custom_streamed_response_wrapper(
            speech.create,
            StreamedBinaryAPIResponse,
        )


class AsyncSpeechWithStreamingResponse:
    def __init__(self, speech: AsyncSpeech) -> None:
        self._speech = speech

        self.create = async_to_custom_streamed_response_wrapper(
            speech.create,
            AsyncStreamedBinaryAPIResponse,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\threads\run.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Optional
from typing_extensions import Literal

from ...._models import BaseModel
from .run_status import RunStatus
from ..assistant_tool import AssistantTool
from ...shared.metadata import Metadata
from ..assistant_tool_choice_option import AssistantToolChoiceOption
from ..assistant_response_format_option import AssistantResponseFormatOption
from .required_action_function_tool_call import RequiredActionFunctionToolCall

__all__ = [
    "Run",
    "IncompleteDetails",
    "LastError",
    "RequiredAction",
    "RequiredActionSubmitToolOutputs",
    "TruncationStrategy",
    "Usage",
]


class IncompleteDetails(BaseModel):
    reason: Optional[Literal["max_completion_tokens", "max_prompt_tokens"]] = None
    """The reason why the run is incomplete.

    This will point to which specific token limit was reached over the course of the
    run.
    """


class LastError(BaseModel):
    code: Literal["server_error", "rate_limit_exceeded", "invalid_prompt"]
    """One of `server_error`, `rate_limit_exceeded`, or `invalid_prompt`."""

    message: str
    """A human-readable description of the error."""


class RequiredActionSubmitToolOutputs(BaseModel):
    tool_calls: List[RequiredActionFunctionToolCall]
    """A list of the relevant tool calls."""


class RequiredAction(BaseModel):
    submit_tool_outputs: RequiredActionSubmitToolOutputs
    """Details on the tool outputs needed for this run to continue."""

    type: Literal["submit_tool_outputs"]
    """For now, this is always `submit_tool_outputs`."""


class TruncationStrategy(BaseModel):
    type: Literal["auto", "last_messages"]
    """The truncation strategy to use for the thread.

    The default is `auto`. If set to `last_messages`, the thread will be truncated
    to the n most recent messages in the thread. When set to `auto`, messages in the
    middle of the thread will be dropped to fit the context length of the model,
    `max_prompt_tokens`.
    """

    last_messages: Optional[int] = None
    """
    The number of most recent messages from the thread when constructing the context
    for the run.
    """


class Usage(BaseModel):
    completion_tokens: int
    """Number of completion tokens used over the course of the run."""

    prompt_tokens: int
    """Number of prompt tokens used over the course of the run."""

    total_tokens: int
    """Total number of tokens used (prompt + completion)."""


class Run(BaseModel):
    id: str
    """The identifier, which can be referenced in API endpoints."""

    assistant_id: str
    """
    The ID of the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) used for
    execution of this run.
    """

    cancelled_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the run was cancelled."""

    completed_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the run was completed."""

    created_at: int
    """The Unix timestamp (in seconds) for when the run was created."""

    expires_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the run will expire."""

    failed_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the run failed."""

    incomplete_details: Optional[IncompleteDetails] = None
    """Details on why the run is incomplete.

    Will be `null` if the run is not incomplete.
    """

    instructions: str
    """
    The instructions that the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) used for
    this run.
    """

    last_error: Optional[LastError] = None
    """The last error associated with this run. Will be `null` if there are no errors."""

    max_completion_tokens: Optional[int] = None
    """
    The maximum number of completion tokens specified to have been used over the
    course of the run.
    """

    max_prompt_tokens: Optional[int] = None
    """
    The maximum number of prompt tokens specified to have been used over the course
    of the run.
    """

    metadata: Optional[Metadata] = None
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: str
    """
    The model that the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) used for
    this run.
    """

    object: Literal["thread.run"]
    """The object type, which is always `thread.run`."""

    parallel_tool_calls: bool
    """
    Whether to enable
    [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
    during tool use.
    """

    required_action: Optional[RequiredAction] = None
    """Details on the action required to continue the run.

    Will be `null` if no action is required.
    """

    response_format: Optional[AssistantResponseFormatOption] = None
    """Specifies the format that the model must output.

    Compatible with [GPT-4o](https://platform.openai.com/docs/models#gpt-4o),
    [GPT-4 Turbo](https://platform.openai.com/docs/models#gpt-4-turbo-and-gpt-4),
    and all GPT-3.5 Turbo models since `gpt-3.5-turbo-1106`.

    Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
    Outputs which ensures the model will match your supplied JSON schema. Learn more
    in the
    [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

    Setting to `{ "type": "json_object" }` enables JSON mode, which ensures the
    message the model generates is valid JSON.

    **Important:** when using JSON mode, you **must** also instruct the model to
    produce JSON yourself via a system or user message. Without this, the model may
    generate an unending stream of whitespace until the generation reaches the token
    limit, resulting in a long-running and seemingly "stuck" request. Also note that
    the message content may be partially cut off if `finish_reason="length"`, which
    indicates the generation exceeded `max_tokens` or the conversation exceeded the
    max context length.
    """

    started_at: Optional[int] = None
    """The Unix timestamp (in seconds) for when the run was started."""

    status: RunStatus
    """
    The status of the run, which can be either `queued`, `in_progress`,
    `requires_action`, `cancelling`, `cancelled`, `failed`, `completed`,
    `incomplete`, or `expired`.
    """

    thread_id: str
    """
    The ID of the [thread](https://platform.openai.com/docs/api-reference/threads)
    that was executed on as a part of this run.
    """

    tool_choice: Optional[AssistantToolChoiceOption] = None
    """
    Controls which (if any) tool is called by the model. `none` means the model will
    not call any tools and instead generates a message. `auto` is the default value
    and means the model can pick between generating a message or calling one or more
    tools. `required` means the model must call one or more tools before responding
    to the user. Specifying a particular tool like `{"type": "file_search"}` or
    `{"type": "function", "function": {"name": "my_function"}}` forces the model to
    call that tool.
    """

    tools: List[AssistantTool]
    """
    The list of tools that the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) used for
    this run.
    """

    truncation_strategy: Optional[TruncationStrategy] = None
    """Controls for how a thread will be truncated prior to the run.

    Use this to control the intial context window of the run.
    """

    usage: Optional[Usage] = None
    """Usage statistics related to the run.

    This value will be `null` if the run is not in a terminal state (i.e.
    `in_progress`, `queued`, etc.).
    """

    temperature: Optional[float] = None
    """The sampling temperature used for this run. If not set, defaults to 1."""

    top_p: Optional[float] = None
    """The nucleus sampling value used for this run. If not set, defaults to 1."""

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\subprocess.py ===
import logging
import os
import shlex
import subprocess
from typing import Any, Callable, Iterable, List, Literal, Mapping, Optional, Union

from pip._vendor.rich.markup import escape

from pip._internal.cli.spinners import SpinnerInterface, open_spinner
from pip._internal.exceptions import InstallationSubprocessError
from pip._internal.utils.logging import VERBOSE, subprocess_logger
from pip._internal.utils.misc import HiddenText

CommandArgs = List[Union[str, HiddenText]]


def make_command(*args: Union[str, HiddenText, CommandArgs]) -> CommandArgs:
    """
    Create a CommandArgs object.
    """
    command_args: CommandArgs = []
    for arg in args:
        # Check for list instead of CommandArgs since CommandArgs is
        # only known during type-checking.
        if isinstance(arg, list):
            command_args.extend(arg)
        else:
            # Otherwise, arg is str or HiddenText.
            command_args.append(arg)

    return command_args


def format_command_args(args: Union[List[str], CommandArgs]) -> str:
    """
    Format command arguments for display.
    """
    # For HiddenText arguments, display the redacted form by calling str().
    # Also, we don't apply str() to arguments that aren't HiddenText since
    # this can trigger a UnicodeDecodeError in Python 2 if the argument
    # has type unicode and includes a non-ascii character.  (The type
    # checker doesn't ensure the annotations are correct in all cases.)
    return " ".join(
        shlex.quote(str(arg)) if isinstance(arg, HiddenText) else shlex.quote(arg)
        for arg in args
    )


def reveal_command_args(args: Union[List[str], CommandArgs]) -> List[str]:
    """
    Return the arguments in their raw, unredacted form.
    """
    return [arg.secret if isinstance(arg, HiddenText) else arg for arg in args]


def call_subprocess(
    cmd: Union[List[str], CommandArgs],
    show_stdout: bool = False,
    cwd: Optional[str] = None,
    on_returncode: 'Literal["raise", "warn", "ignore"]' = "raise",
    extra_ok_returncodes: Optional[Iterable[int]] = None,
    extra_environ: Optional[Mapping[str, Any]] = None,
    unset_environ: Optional[Iterable[str]] = None,
    spinner: Optional[SpinnerInterface] = None,
    log_failed_cmd: Optional[bool] = True,
    stdout_only: Optional[bool] = False,
    *,
    command_desc: str,
) -> str:
    """
    Args:
      show_stdout: if true, use INFO to log the subprocess's stderr and
        stdout streams.  Otherwise, use DEBUG.  Defaults to False.
      extra_ok_returncodes: an iterable of integer return codes that are
        acceptable, in addition to 0. Defaults to None, which means [].
      unset_environ: an iterable of environment variable names to unset
        prior to calling subprocess.Popen().
      log_failed_cmd: if false, failed commands are not logged, only raised.
      stdout_only: if true, return only stdout, else return both. When true,
        logging of both stdout and stderr occurs when the subprocess has
        terminated, else logging occurs as subprocess output is produced.
    """
    if extra_ok_returncodes is None:
        extra_ok_returncodes = []
    if unset_environ is None:
        unset_environ = []
    # Most places in pip use show_stdout=False. What this means is--
    #
    # - We connect the child's output (combined stderr and stdout) to a
    #   single pipe, which we read.
    # - We log this output to stderr at DEBUG level as it is received.
    # - If DEBUG logging isn't enabled (e.g. if --verbose logging wasn't
    #   requested), then we show a spinner so the user can still see the
    #   subprocess is in progress.
    # - If the subprocess exits with an error, we log the output to stderr
    #   at ERROR level if it hasn't already been displayed to the console
    #   (e.g. if --verbose logging wasn't enabled).  This way we don't log
    #   the output to the console twice.
    #
    # If show_stdout=True, then the above is still done, but with DEBUG
    # replaced by INFO.
    if show_stdout:
        # Then log the subprocess output at INFO level.
        log_subprocess: Callable[..., None] = subprocess_logger.info
        used_level = logging.INFO
    else:
        # Then log the subprocess output using VERBOSE.  This also ensures
        # it will be logged to the log file (aka user_log), if enabled.
        log_subprocess = subprocess_logger.verbose
        used_level = VERBOSE

    # Whether the subprocess will be visible in the console.
    showing_subprocess = subprocess_logger.getEffectiveLevel() <= used_level

    # Only use the spinner if we're not showing the subprocess output
    # and we have a spinner.
    use_spinner = not showing_subprocess and spinner is not None

    log_subprocess("Running command %s", command_desc)
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)
    for name in unset_environ:
        env.pop(name, None)
    try:
        proc = subprocess.Popen(
            # Convert HiddenText objects to the underlying str.
            reveal_command_args(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT if not stdout_only else subprocess.PIPE,
            cwd=cwd,
            env=env,
            errors="backslashreplace",
        )
    except Exception as exc:
        if log_failed_cmd:
            subprocess_logger.critical(
                "Error %s while executing command %s",
                exc,
                command_desc,
            )
        raise
    all_output = []
    if not stdout_only:
        assert proc.stdout
        assert proc.stdin
        proc.stdin.close()
        # In this mode, stdout and stderr are in the same pipe.
        while True:
            line: str = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            all_output.append(line + "\n")

            # Show the line immediately.
            log_subprocess(line)
            # Update the spinner.
            if use_spinner:
                assert spinner
                spinner.spin()
        try:
            proc.wait()
        finally:
            if proc.stdout:
                proc.stdout.close()
        output = "".join(all_output)
    else:
        # In this mode, stdout and stderr are in different pipes.
        # We must use communicate() which is the only safe way to read both.
        out, err = proc.communicate()
        # log line by line to preserve pip log indenting
        for out_line in out.splitlines():
            log_subprocess(out_line)
        all_output.append(out)
        for err_line in err.splitlines():
            log_subprocess(err_line)
        all_output.append(err)
        output = out

    proc_had_error = proc.returncode and proc.returncode not in extra_ok_returncodes
    if use_spinner:
        assert spinner
        if proc_had_error:
            spinner.finish("error")
        else:
            spinner.finish("done")
    if proc_had_error:
        if on_returncode == "raise":
            error = InstallationSubprocessError(
                command_description=command_desc,
                exit_code=proc.returncode,
                output_lines=all_output if not showing_subprocess else None,
            )
            if log_failed_cmd:
                subprocess_logger.error("%s", error, extra={"rich": True})
                subprocess_logger.verbose(
                    "[bold magenta]full command[/]: [blue]%s[/]",
                    escape(format_command_args(cmd)),
                    extra={"markup": True},
                )
                subprocess_logger.verbose(
                    "[bold magenta]cwd[/]: %s",
                    escape(cwd or "[inherit]"),
                    extra={"markup": True},
                )

            raise error
        elif on_returncode == "warn":
            subprocess_logger.warning(
                'Command "%s" had error code %s in %s',
                command_desc,
                proc.returncode,
                cwd,
            )
        elif on_returncode == "ignore":
            pass
        else:
            raise ValueError(f"Invalid value: on_returncode={on_returncode!r}")
    return output


def runner_with_spinner_message(message: str) -> Callable[..., None]:
    """Provide a subprocess_runner that shows a spinner message.

    Intended for use with for BuildBackendHookCaller. Thus, the runner has
    an API that matches what's expected by BuildBackendHookCaller.subprocess_runner.
    """

    def runner(
        cmd: List[str],
        cwd: Optional[str] = None,
        extra_environ: Optional[Mapping[str, Any]] = None,
    ) -> None:
        with open_spinner(message) as spinner:
            call_subprocess(
                cmd,
                command_desc=message,
                cwd=cwd,
                extra_environ=extra_environ,
                spinner=spinner,
            )

    return runner

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\requirements.py ===
from typing import Any, Optional

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import NormalizedName, canonicalize_name

from pip._internal.req.constructors import install_req_drop_extras
from pip._internal.req.req_install import InstallRequirement

from .base import Candidate, CandidateLookup, Requirement, format_name


class ExplicitRequirement(Requirement):
    def __init__(self, candidate: Candidate) -> None:
        self.candidate = candidate

    def __str__(self) -> str:
        return str(self.candidate)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.candidate!r})"

    def __hash__(self) -> int:
        return hash(self.candidate)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ExplicitRequirement):
            return False
        return self.candidate == other.candidate

    @property
    def project_name(self) -> NormalizedName:
        # No need to canonicalize - the candidate did this
        return self.candidate.project_name

    @property
    def name(self) -> str:
        # No need to canonicalize - the candidate did this
        return self.candidate.name

    def format_for_error(self) -> str:
        return self.candidate.format_for_error()

    def get_candidate_lookup(self) -> CandidateLookup:
        return self.candidate, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return candidate == self.candidate


class SpecifierRequirement(Requirement):
    def __init__(self, ireq: InstallRequirement) -> None:
        assert ireq.link is None, "This is a link, not a specifier"
        self._ireq = ireq
        self._equal_cache: Optional[str] = None
        self._hash: Optional[int] = None
        self._extras = frozenset(canonicalize_name(e) for e in self._ireq.extras)

    @property
    def _equal(self) -> str:
        if self._equal_cache is not None:
            return self._equal_cache

        self._equal_cache = str(self._ireq)
        return self._equal_cache

    def __str__(self) -> str:
        return str(self._ireq.req)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self._ireq.req)!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecifierRequirement):
            return NotImplemented
        return self._equal == other._equal

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash(self._equal)
        return self._hash

    @property
    def project_name(self) -> NormalizedName:
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        return canonicalize_name(self._ireq.req.name)

    @property
    def name(self) -> str:
        return format_name(self.project_name, self._extras)

    def format_for_error(self) -> str:
        # Convert comma-separated specifiers into "A, B, ..., F and G"
        # This makes the specifier a bit more "human readable", without
        # risking a change in meaning. (Hopefully! Not all edge cases have
        # been checked)
        parts = [s.strip() for s in str(self).split(",")]
        if len(parts) == 0:
            return ""
        elif len(parts) == 1:
            return parts[0]

        return ", ".join(parts[:-1]) + " and " + parts[-1]

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, self._ireq

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self.name, (
            f"Internal issue: Candidate is not for this requirement "
            f"{candidate.name} vs {self.name}"
        )
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        assert self._ireq.req, "Specifier-backed ireq is always PEP 508"
        spec = self._ireq.req.specifier
        return spec.contains(candidate.version, prereleases=True)


class SpecifierWithoutExtrasRequirement(SpecifierRequirement):
    """
    Requirement backed by an install requirement on a base package.
    Trims extras from its install requirement if there are any.
    """

    def __init__(self, ireq: InstallRequirement) -> None:
        assert ireq.link is None, "This is a link, not a specifier"
        self._ireq = install_req_drop_extras(ireq)
        self._equal_cache: Optional[str] = None
        self._hash: Optional[int] = None
        self._extras = frozenset(canonicalize_name(e) for e in self._ireq.extras)

    @property
    def _equal(self) -> str:
        if self._equal_cache is not None:
            return self._equal_cache

        self._equal_cache = str(self._ireq)
        return self._equal_cache

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecifierWithoutExtrasRequirement):
            return NotImplemented
        return self._equal == other._equal

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash(self._equal)
        return self._hash


class RequiresPythonRequirement(Requirement):
    """A requirement representing Requires-Python metadata."""

    def __init__(self, specifier: SpecifierSet, match: Candidate) -> None:
        self.specifier = specifier
        self._specifier_string = str(specifier)  # for faster __eq__
        self._hash: Optional[int] = None
        self._candidate = match

    def __str__(self) -> str:
        return f"Python {self.specifier}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self.specifier)!r})"

    def __hash__(self) -> int:
        if self._hash is not None:
            return self._hash

        self._hash = hash((self._specifier_string, self._candidate))
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, RequiresPythonRequirement):
            return False
        return (
            self._specifier_string == other._specifier_string
            and self._candidate == other._candidate
        )

    @property
    def project_name(self) -> NormalizedName:
        return self._candidate.project_name

    @property
    def name(self) -> str:
        return self._candidate.name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        if self.specifier.contains(self._candidate.version, prereleases=True):
            return self._candidate, None
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        assert candidate.name == self._candidate.name, "Not Python candidate"
        # We can safely always allow prereleases here since PackageFinder
        # already implements the prerelease logic, and would have filtered out
        # prerelease candidates if the user does not expect them.
        return self.specifier.contains(candidate.version, prereleases=True)


class UnsatisfiableRequirement(Requirement):
    """A requirement that cannot be satisfied."""

    def __init__(self, name: NormalizedName) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"{self._name} (unavailable)"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self._name)!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UnsatisfiableRequirement):
            return NotImplemented
        return self._name == other._name

    def __hash__(self) -> int:
        return hash(self._name)

    @property
    def project_name(self) -> NormalizedName:
        return self._name

    @property
    def name(self) -> str:
        return self._name

    def format_for_error(self) -> str:
        return str(self)

    def get_candidate_lookup(self) -> CandidateLookup:
        return None, None

    def is_satisfied_by(self, candidate: Candidate) -> bool:
        return False

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\service.py ===
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
import errno
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from io import IOBase
from platform import system
from subprocess import PIPE
from time import sleep
from typing import IO, Any, List, Mapping, Optional, Union, cast
from urllib import request
from urllib.error import URLError

from selenium.common.exceptions import WebDriverException
from selenium.types import SubprocessStdAlias
from selenium.webdriver.common import utils

logger = logging.getLogger(__name__)


class Service(ABC):
    """The abstract base class for all service objects.  Services typically
    launch a child program in a new process as an interim process to
    communicate with a browser.

    :param executable: install path of the executable.
    :param port: Port for the service to run on, defaults to 0 where the operating system will decide.
    :param log_output: (Optional) int representation of STDOUT/DEVNULL, any IO instance or String path to file.
    :param env: (Optional) Mapping of environment variables for the new process, defaults to `os.environ`.
    :param driver_path_env_key: (Optional) Environment variable to use to get the path to the driver executable.
    """

    def __init__(
        self,
        executable_path: Optional[str] = None,
        port: int = 0,
        log_output: Optional[SubprocessStdAlias] = None,
        env: Optional[Mapping[Any, Any]] = None,
        driver_path_env_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        if isinstance(log_output, str):
            self.log_output = cast(IOBase, open(log_output, "a+", encoding="utf-8"))
        elif log_output == subprocess.STDOUT:
            self.log_output = cast(Optional[Union[int, IOBase]], None)
        elif log_output is None or log_output == subprocess.DEVNULL:
            self.log_output = cast(Optional[Union[int, IOBase]], subprocess.DEVNULL)
        else:
            self.log_output = log_output

        self.port = port or utils.free_port()
        # Default value for every python subprocess: subprocess.Popen(..., creationflags=0)
        self.popen_kw = kwargs.pop("popen_kw", {})
        self.creation_flags = self.popen_kw.pop("creation_flags", 0)
        self.env = env or os.environ
        self.DRIVER_PATH_ENV_KEY = driver_path_env_key
        self._path = self.env_path() or executable_path

    @property
    def service_url(self) -> str:
        """Gets the url of the Service."""
        return f"http://{utils.join_host_port('localhost', self.port)}"

    @abstractmethod
    def command_line_args(self) -> List[str]:
        """A List of program arguments (excluding the executable)."""
        raise NotImplementedError("This method needs to be implemented in a sub class")

    @property
    def path(self) -> str:
        return self._path or ""

    @path.setter
    def path(self, value: str) -> None:
        self._path = str(value)

    def start(self) -> None:
        """Starts the Service.

        :Exceptions:
         - WebDriverException : Raised either when it can't start the service
           or when it can't connect to the service
        """
        if self._path is None:
            raise WebDriverException("Service path cannot be None.")
        self._start_process(self._path)

        count = 0
        while True:
            self.assert_process_still_running()
            if self.is_connectable():
                break
            # sleep increasing: 0.01, 0.06, 0.11, 0.16, 0.21, 0.26, 0.31, 0.36, 0.41, 0.46, 0.5
            sleep(min(0.01 + 0.05 * count, 0.5))
            count += 1
            if count == 70:
                raise WebDriverException(f"Can not connect to the Service {self._path}")

    def assert_process_still_running(self) -> None:
        """Check if the underlying process is still running."""
        return_code = self.process.poll()
        if return_code:
            raise WebDriverException(f"Service {self._path} unexpectedly exited. Status code was: {return_code}")

    def is_connectable(self) -> bool:
        """Establishes a socket connection to determine if the service running
        on the port is accessible."""
        return utils.is_connectable(self.port)

    def send_remote_shutdown_command(self) -> None:
        """Dispatch an HTTP request to the shutdown endpoint for the service in
        an attempt to stop it."""
        try:
            request.urlopen(f"{self.service_url}/shutdown")
        except URLError:
            return

        for _ in range(30):
            if not self.is_connectable():
                break
            sleep(1)

    def stop(self) -> None:
        """Stops the service."""

        if self.log_output not in {PIPE, subprocess.DEVNULL}:
            if isinstance(self.log_output, IOBase):
                self.log_output.close()
            elif isinstance(self.log_output, int):
                os.close(self.log_output)

        if self.process is not None and self.process.poll() is None:
            try:
                self.send_remote_shutdown_command()
            except TypeError:
                pass
            finally:
                self._terminate_process()

    def _terminate_process(self) -> None:
        """Terminate the child process.

        On POSIX this attempts a graceful SIGTERM followed by a SIGKILL,
        on a Windows OS kill is an alias to terminate.  Terminating does
        not raise itself if something has gone wrong but (currently)
        silently ignores errors here.
        """
        try:
            stdin, stdout, stderr = (
                self.process.stdin,
                self.process.stdout,
                self.process.stderr,
            )
            for stream in stdin, stdout, stderr:
                try:
                    stream.close()  # type: ignore
                except AttributeError:
                    pass
            self.process.terminate()
            try:
                self.process.wait(60)
            except subprocess.TimeoutExpired:
                logger.error(
                    "Service process refused to terminate gracefully with SIGTERM, escalating to SIGKILL.",
                    exc_info=True,
                )
                self.process.kill()
        except OSError:
            logger.error("Error terminating service process.", exc_info=True)

    def __del__(self) -> None:
        # `subprocess.Popen` doesn't send signal on `__del__`;
        # so we attempt to close the launched process when `__del__`
        # is triggered.
        # do not use globals here; interpreter shutdown may have already cleaned them up
        # and they would be `None`. This goes for anything this method is referencing internally.
        try:
            self.stop()
        except Exception:
            pass

    def _start_process(self, path: str) -> None:
        """Creates a subprocess by executing the command provided.

        :param cmd: full command to execute
        """
        cmd = [path]
        cmd.extend(self.command_line_args())
        close_file_descriptors = self.popen_kw.pop("close_fds", system() != "Windows")
        try:
            start_info = None
            if system() == "Windows":
                start_info = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
                start_info.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
                start_info.wShowWindow = subprocess.SW_HIDE  # type: ignore[attr-defined]

            self.process = subprocess.Popen(
                cmd,
                env=self.env,
                close_fds=close_file_descriptors,
                stdout=cast(Optional[Union[int, IO[Any]]], self.log_output),
                stderr=cast(Optional[Union[int, IO[Any]]], self.log_output),
                stdin=PIPE,
                creationflags=self.creation_flags,
                startupinfo=start_info,
                **self.popen_kw,
            )
            logger.debug(
                "Started executable: `%s` in a child process with pid: %s using %s to output %s",
                self._path,
                self.process.pid,
                self.creation_flags,
                self.log_output,
            )
        except TypeError:
            raise
        except OSError as err:
            if err.errno == errno.EACCES:
                if self._path is None:
                    raise WebDriverException("Service path cannot be None.")
                raise WebDriverException(
                    f"'{os.path.basename(self._path)}' executable may have wrong permissions."
                ) from err
            raise

    def env_path(self) -> Optional[str]:
        if self.DRIVER_PATH_ENV_KEY:
            return os.getenv(self.DRIVER_PATH_ENV_KEY, None)
        return None

# === NexusCore/openenv\Lib\site-packages\blessed\color.py ===
# -*- coding: utf-8 -*-
"""
Sub-module providing color functions.

References,

- https://en.wikipedia.org/wiki/Color_difference
- http://www.easyrgb.com/en/math.php
- Measuring Colour by R.W.G. Hunt and M.R. Pointer
"""

# std imports
from math import cos, exp, sin, sqrt, atan2

# isort: off
try:
    from functools import lru_cache
except ImportError:
    # lru_cache was added in Python 3.2
    from backports.functools_lru_cache import lru_cache


def rgb_to_xyz(red, green, blue):
    """
    Convert standard RGB color to XYZ color.

    D65/2° standard illuminant.

    :arg int red: RGB value of Red.
    :arg int green: RGB value of Green.
    :arg int blue: RGB value of Blue.
    :returns: Tuple (X, Y, Z) representing XYZ color
    :rtype: tuple
    """
    rgb = []
    for val in red, green, blue:
        val /= 255.0
        if val > 0.04045:
            val = pow((val + 0.055) / 1.055, 2.4)
        else:
            val /= 12.92
        val *= 100
        rgb.append(val)

    red, green, blue = rgb  # pylint: disable=unbalanced-tuple-unpacking
    x_val = red * 0.4124 + green * 0.3576 + blue * 0.1805
    y_val = red * 0.2126 + green * 0.7152 + blue * 0.0722
    z_val = red * 0.0193 + green * 0.1192 + blue * 0.9505

    return x_val, y_val, z_val


def xyz_to_lab(x_val, y_val, z_val):
    """
    Convert XYZ color to CIE-Lab color.

    :arg float x_val: XYZ value of X.
    :arg float y_val: XYZ value of Y.
    :arg float z_val: XYZ value of Z.
    :returns: Tuple (L, a, b) representing CIE-Lab color
    :rtype: tuple  D65/2° standard illuminant
    """
    xyz = []
    for val, ref in (x_val, 95.047), (y_val, 100.0), (z_val, 108.883):
        val /= ref
        val = pow(val, 1 / 3.0) if val > 0.008856 else 7.787 * val + 16 / 116.0
        xyz.append(val)

    x_val, y_val, z_val = xyz  # pylint: disable=unbalanced-tuple-unpacking
    cie_l = 116 * y_val - 16
    cie_a = 500 * (x_val - y_val)
    cie_b = 200 * (y_val - z_val)

    return cie_l, cie_a, cie_b


@lru_cache(maxsize=256)
def rgb_to_lab(red, green, blue):
    """
    Convert RGB color to CIE-Lab color.

    :arg int red: RGB value of Red.
    :arg int green: RGB value of Green.
    :arg int blue: RGB value of Blue.
    :returns: Tuple (L, a, b) representing CIE-Lab color
    :rtype: tuple  D65/2° standard illuminant
    """
    return xyz_to_lab(*rgb_to_xyz(red, green, blue))


def dist_rgb(rgb1, rgb2):
    """
    Determine distance between two rgb colors.

    :arg tuple rgb1: RGB color definition
    :arg tuple rgb2: RGB color definition
    :returns: Square of the distance between provided colors
    :rtype: float

    This works by treating RGB colors as coordinates in three dimensional
    space and finding the closest point within the configured color range
    using the formula::

        d^2 = (r2 - r1)^2 + (g2 - g1)^2 + (b2 - b1)^2

    For efficiency, the square of the distance is returned
    which is sufficient for comparisons
    """
    return sum(pow(rgb1[idx] - rgb2[idx], 2) for idx in (0, 1, 2))


def dist_rgb_weighted(rgb1, rgb2):
    """
    Determine the weighted distance between two rgb colors.

    :arg tuple rgb1: RGB color definition
    :arg tuple rgb2: RGB color definition
    :returns: Square of the distance between provided colors
    :rtype: float Similar to a standard distance formula, the values are weighted to approximate
        human perception of color differences For efficiency, the square of the distance is returned
        which is sufficient for comparisons
    """
    red_mean = (rgb1[0] + rgb2[0]) / 2.0

    return ((2 + red_mean / 256) * pow(rgb1[0] - rgb2[0], 2) +
            4 * pow(rgb1[1] - rgb2[1], 2) +
            (2 + (255 - red_mean) / 256) * pow(rgb1[2] - rgb2[2], 2))


def dist_cie76(rgb1, rgb2):
    """
    Determine distance between two rgb colors using the CIE76 algorithm.

    :arg tuple rgb1: RGB color definition
    :arg tuple rgb2: RGB color definition
    :returns: Square of the distance between provided colors
    :rtype: float For efficiency, the square of the distance is returned which is sufficient for
        comparisons
    """
    l_1, a_1, b_1 = rgb_to_lab(*rgb1)
    l_2, a_2, b_2 = rgb_to_lab(*rgb2)
    return pow(l_1 - l_2, 2) + pow(a_1 - a_2, 2) + pow(b_1 - b_2, 2)


def dist_cie94(rgb1, rgb2):
    # pylint: disable=too-many-locals
    """
    Determine distance between two rgb colors using the CIE94 algorithm.

    :arg tuple rgb1: RGB color definition
    :arg tuple rgb2: RGB color definition
    :returns: Square of the distance between provided colors
    :rtype: float For efficiency, the square of the distance is returned which is sufficient for
        comparisons
    """
    l_1, a_1, b_1 = rgb_to_lab(*rgb1)
    l_2, a_2, b_2 = rgb_to_lab(*rgb2)

    s_l = k_l = k_c = k_h = 1
    k_1 = 0.045
    k_2 = 0.015

    delta_l = l_1 - l_2
    delta_a = a_1 - a_2
    delta_b = b_1 - b_2
    c_1 = sqrt(a_1 ** 2 + b_1 ** 2)
    c_2 = sqrt(a_2 ** 2 + b_2 ** 2)
    delta_c = c_1 - c_2
    delta_h = sqrt(delta_a ** 2 + delta_b ** 2 + delta_c ** 2)
    s_c = 1 + k_1 * c_1
    s_h = 1 + k_2 * c_1

    return ((delta_l / (k_l * s_l)) ** 2 +  # pylint: disable=superfluous-parens
            (delta_c / (k_c * s_c)) ** 2 +
            (delta_h / (k_h * s_h)) ** 2)


def dist_cie2000(rgb1, rgb2):
    # pylint: disable=too-many-locals
    """
    Determine distance between two rgb colors using the CIE2000 algorithm.

    :arg tuple rgb1: RGB color definition
    :arg tuple rgb2: RGB color definition
    :returns: Square of the distance between provided colors
    :rtype: float For efficiency, the square of the distance is returned which is sufficient for
        comparisons
    """
    s_l = k_l = k_c = k_h = 1

    l_1, a_1, b_1 = rgb_to_lab(*rgb1)
    l_2, a_2, b_2 = rgb_to_lab(*rgb2)

    delta_l = l_2 - l_1
    l_mean = (l_1 + l_2) / 2

    c_1 = sqrt(a_1 ** 2 + b_1 ** 2)
    c_2 = sqrt(a_2 ** 2 + b_2 ** 2)
    c_mean = (c_1 + c_2) / 2
    delta_c = c_1 - c_2

    g_x = sqrt(c_mean ** 7 / (c_mean ** 7 + 25 ** 7))
    h_1 = atan2(b_1, a_1 + (a_1 / 2) * (1 - g_x)) % 360
    h_2 = atan2(b_2, a_2 + (a_2 / 2) * (1 - g_x)) % 360

    if 0 in (c_1, c_2):
        delta_h_prime = 0
        h_mean = h_1 + h_2
    else:
        delta_h_prime = h_2 - h_1
        if abs(delta_h_prime) <= 180:
            h_mean = (h_1 + h_2) / 2
        else:
            if h_2 <= h_1:
                delta_h_prime += 360
            else:
                delta_h_prime -= 360
            h_mean = (h_1 + h_2 + 360) / 2 if h_1 + h_2 < 360 else (h_1 + h_2 - 360) / 2

    delta_h = 2 * sqrt(c_1 * c_2) * sin(delta_h_prime / 2)

    t_x = (1 -
           0.17 * cos(h_mean - 30) +
           0.24 * cos(2 * h_mean) +
           0.32 * cos(3 * h_mean + 6) -
           0.20 * cos(4 * h_mean - 63))

    s_l = 1 + (0.015 * (l_mean - 50) ** 2) / sqrt(20 + (l_mean - 50) ** 2)
    s_c = 1 + 0.045 * c_mean
    s_h = 1 + 0.015 * c_mean * t_x
    r_t = -2 * g_x * sin(abs(60 * exp(-1 * abs((delta_h - 275) / 25) ** 2)))

    delta_l = delta_l / (k_l * s_l)
    delta_c = delta_c / (k_c * s_c)
    delta_h = delta_h / (k_h * s_h)

    return delta_l ** 2 + delta_c ** 2 + delta_h ** 2 + r_t * delta_c * delta_h


COLOR_DISTANCE_ALGORITHMS = {'rgb': dist_rgb,
                             'rgb-weighted': dist_rgb_weighted,
                             'cie76': dist_cie76,
                             'cie94': dist_cie94,
                             'cie2000': dist_cie2000}

# === NexusCore/openenv\Lib\site-packages\websocket\_wsdump.py ===
#!/usr/bin/env python3

"""
wsdump.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import code
import gzip
import ssl
import sys
import threading
import time
import zlib
from urllib.parse import urlparse

import websocket

try:
    import readline
except ImportError:
    pass


def get_encoding() -> str:
    encoding = getattr(sys.stdin, "encoding", "")
    if not encoding:
        return "utf-8"
    else:
        return encoding.lower()


OPCODE_DATA = (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY)
ENCODING = get_encoding()


class VAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.Namespace,
        args: tuple,
        values: str,
        option_string: str = None,
    ) -> None:
        if values is None:
            values = "1"
        try:
            values = int(values)
        except ValueError:
            values = values.count("v") + 1
        setattr(args, self.dest, values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WebSocket Simple Dump Tool")
    parser.add_argument(
        "url", metavar="ws_url", help="websocket url. ex. ws://echo.websocket.events/"
    )
    parser.add_argument("-p", "--proxy", help="proxy url. ex. http://127.0.0.1:8080")
    parser.add_argument(
        "-v",
        "--verbose",
        default=0,
        nargs="?",
        action=VAction,
        dest="verbose",
        help="set verbose mode. If set to 1, show opcode. "
        "If set to 2, enable to trace  websocket module",
    )
    parser.add_argument(
        "-n", "--nocert", action="store_true", help="Ignore invalid SSL cert"
    )
    parser.add_argument("-r", "--raw", action="store_true", help="raw output")
    parser.add_argument("-s", "--subprotocols", nargs="*", help="Set subprotocols")
    parser.add_argument("-o", "--origin", help="Set origin")
    parser.add_argument(
        "--eof-wait",
        default=0,
        type=int,
        help="wait time(second) after 'EOF' received.",
    )
    parser.add_argument("-t", "--text", help="Send initial text")
    parser.add_argument(
        "--timings", action="store_true", help="Print timings in seconds"
    )
    parser.add_argument("--headers", help="Set custom headers. Use ',' as separator")

    return parser.parse_args()


class RawInput:
    def raw_input(self, prompt: str = "") -> str:
        line = input(prompt)

        if ENCODING and ENCODING != "utf-8" and not isinstance(line, str):
            line = line.decode(ENCODING).encode("utf-8")
        elif isinstance(line, str):
            line = line.encode("utf-8")

        return line


class InteractiveConsole(RawInput, code.InteractiveConsole):
    def write(self, data: str) -> None:
        sys.stdout.write("\033[2K\033[E")
        # sys.stdout.write("\n")
        sys.stdout.write("\033[34m< " + data + "\033[39m")
        sys.stdout.write("\n> ")
        sys.stdout.flush()

    def read(self) -> str:
        return self.raw_input("> ")


class NonInteractive(RawInput):
    def write(self, data: str) -> None:
        sys.stdout.write(data)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def read(self) -> str:
        return self.raw_input("")


def main() -> None:
    start_time = time.time()
    args = parse_args()
    if args.verbose > 1:
        websocket.enableTrace(True)
    options = {}
    if args.proxy:
        p = urlparse(args.proxy)
        options["http_proxy_host"] = p.hostname
        options["http_proxy_port"] = p.port
    if args.origin:
        options["origin"] = args.origin
    if args.subprotocols:
        options["subprotocols"] = args.subprotocols
    opts = {}
    if args.nocert:
        opts = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}
    if args.headers:
        options["header"] = list(map(str.strip, args.headers.split(",")))
    ws = websocket.create_connection(args.url, sslopt=opts, **options)
    if args.raw:
        console = NonInteractive()
    else:
        console = InteractiveConsole()
        print("Press Ctrl+C to quit")

    def recv() -> tuple:
        try:
            frame = ws.recv_frame()
        except websocket.WebSocketException:
            return websocket.ABNF.OPCODE_CLOSE, ""
        if not frame:
            raise websocket.WebSocketException(f"Not a valid frame {frame}")
        elif frame.opcode in OPCODE_DATA:
            return frame.opcode, frame.data
        elif frame.opcode == websocket.ABNF.OPCODE_CLOSE:
            ws.send_close()
            return frame.opcode, ""
        elif frame.opcode == websocket.ABNF.OPCODE_PING:
            ws.pong(frame.data)
            return frame.opcode, frame.data

        return frame.opcode, frame.data

    def recv_ws() -> None:
        while True:
            opcode, data = recv()
            msg = None
            if opcode == websocket.ABNF.OPCODE_TEXT and isinstance(data, bytes):
                data = str(data, "utf-8")
            if (
                isinstance(data, bytes) and len(data) > 2 and data[:2] == b"\037\213"
            ):  # gzip magick
                try:
                    data = "[gzip] " + str(gzip.decompress(data), "utf-8")
                except:
                    pass
            elif isinstance(data, bytes):
                try:
                    data = "[zlib] " + str(
                        zlib.decompress(data, -zlib.MAX_WBITS), "utf-8"
                    )
                except:
                    pass

            if isinstance(data, bytes):
                data = repr(data)

            if args.verbose:
                msg = f"{websocket.ABNF.OPCODE_MAP.get(opcode)}: {data}"
            else:
                msg = data

            if msg is not None:
                if args.timings:
                    console.write(f"{time.time() - start_time}: {msg}")
                else:
                    console.write(msg)

            if opcode == websocket.ABNF.OPCODE_CLOSE:
                break

    thread = threading.Thread(target=recv_ws)
    thread.daemon = True
    thread.start()

    if args.text:
        ws.send(args.text)

    while True:
        try:
            message = console.read()
            ws.send(message)
        except KeyboardInterrupt:
            return
        except EOFError:
            time.sleep(args.eof_wait)
            return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)

# === NexusCore/openenv\Lib\site-packages\IPython\core\crashhandler.py ===
"""sys.excepthook for IPython itself, leaves a detailed report on disk.

Authors:

* Fernando Perez
* Brian E. Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2001-2007 Fernando Perez. <fperez@colorado.edu>
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import traceback
from pprint import pformat
from pathlib import Path

import builtins as builtin_mod

from IPython.core import ultratb
from IPython.core.application import Application
from IPython.core.release import author_email
from IPython.utils.sysinfo import sys_info

from IPython.core.release import __version__ as version

from typing import Optional, Dict
import types

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------

# Template for the user message.
_default_message_template = """\
Oops, {app_name} crashed. We do our best to make it stable, but...

A crash report was automatically generated with the following information:
  - A verbatim copy of the crash traceback.
  - A copy of your input history during this session.
  - Data on your current {app_name} configuration.

It was left in the file named:
\t'{crash_report_fname}'
If you can email this file to the developers, the information in it will help
them in understanding and correcting the problem.

You can mail it to: {contact_name} at {contact_email}
with the subject '{app_name} Crash Report'.

If you want to do it now, the following command will work (under Unix):
mail -s '{app_name} Crash Report' {contact_email} < {crash_report_fname}

In your email, please also include information about:
- The operating system under which the crash happened: Linux, macOS, Windows,
  other, and which exact version (for example: Ubuntu 16.04.3, macOS 10.13.2,
  Windows 10 Pro), and whether it is 32-bit or 64-bit;
- How {app_name} was installed: using pip or conda, from GitHub, as part of
  a Docker container, or other, providing more detail if possible;
- How to reproduce the crash: what exact sequence of instructions can one
  input to get the same crash? Ideally, find a minimal yet complete sequence
  of instructions that yields the crash.

To ensure accurate tracking of this issue, please file a report about it at:
{bug_tracker}
"""

_lite_message_template = """
If you suspect this is an IPython {version} bug, please report it at:
    https://github.com/ipython/ipython/issues
or send an email to the mailing list at {email}

You can print a more detailed traceback right now with "%tb", or use "%debug"
to interactively debug it.

Extra-detailed tracebacks for bug-reporting purposes can be enabled via:
    {config}Application.verbose_crash=True
"""


class CrashHandler:
    """Customizable crash handlers for IPython applications.

    Instances of this class provide a :meth:`__call__` method which can be
    used as a ``sys.excepthook``.  The :meth:`__call__` signature is::

        def __call__(self, etype, evalue, etb)
    """

    message_template = _default_message_template
    section_sep = '\n\n'+'*'*75+'\n\n'
    info: Dict[str, Optional[str]]

    def __init__(
        self,
        app: Application,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        bug_tracker: Optional[str] = None,
        show_crash_traceback: bool = True,
        call_pdb: bool = False,
    ):
        """Create a new crash handler

        Parameters
        ----------
        app : Application
            A running :class:`Application` instance, which will be queried at
            crash time for internal information.
        contact_name : str
            A string with the name of the person to contact.
        contact_email : str
            A string with the email address of the contact.
        bug_tracker : str
            A string with the URL for your project's bug tracker.
        show_crash_traceback : bool
            If false, don't print the crash traceback on stderr, only generate
            the on-disk report
        call_pdb
            Whether to call pdb on crash

        Attributes
        ----------
        These instances contain some non-argument attributes which allow for
        further customization of the crash handler's behavior. Please see the
        source for further details.

        """
        self.crash_report_fname = "Crash_report_%s.txt" % app.name
        self.app = app
        self.call_pdb = call_pdb
        #self.call_pdb = True # dbg
        self.show_crash_traceback = show_crash_traceback
        self.info = dict(app_name = app.name,
                    contact_name = contact_name,
                    contact_email = contact_email,
                    bug_tracker = bug_tracker,
                    crash_report_fname = self.crash_report_fname)

    def __call__(
        self,
        etype: type[BaseException],
        evalue: BaseException,
        etb: types.TracebackType,
    ) -> None:
        """Handle an exception, call for compatible with sys.excepthook"""

        # do not allow the crash handler to be called twice without reinstalling it
        # this prevents unlikely errors in the crash handling from entering an
        # infinite loop.
        sys.excepthook = sys.__excepthook__
        

        # Use this ONLY for developer debugging (keep commented out for release)
        ipython_dir = getattr(self.app, "ipython_dir", None)
        if ipython_dir is not None:
            assert isinstance(ipython_dir, str)
            rptdir = Path(ipython_dir)
        else:
            rptdir = Path.cwd()
        if not rptdir.is_dir():
            rptdir = Path.cwd()
        report_name = rptdir / self.crash_report_fname
        # write the report filename into the instance dict so it can get
        # properly expanded out in the user message template
        self.crash_report_fname = str(report_name)
        self.info["crash_report_fname"] = str(report_name)
        TBhandler = ultratb.VerboseTB(
            theme_name="nocolor",
            long_header=True,
            call_pdb=self.call_pdb,
        )
        if self.call_pdb:
            TBhandler(etype,evalue,etb)
            return
        else:
            traceback = TBhandler.text(etype,evalue,etb,context=31)

        # print traceback to screen
        if self.show_crash_traceback:
            print(traceback, file=sys.stderr)

        # and generate a complete report on disk
        try:
            report = open(report_name, "w", encoding="utf-8")
        except:
            print('Could not create crash report on disk.', file=sys.stderr)
            return

        with report:
            # Inform user on stderr of what happened
            print('\n'+'*'*70+'\n', file=sys.stderr)
            print(self.message_template.format(**self.info), file=sys.stderr)

            # Construct report on disk
            report.write(self.make_report(str(traceback)))

        builtin_mod.input("Hit <Enter> to quit (your terminal may close):")

    def make_report(self, traceback: str) -> str:
        """Return a string containing a crash report."""

        sec_sep = self.section_sep

        report = ['*'*75+'\n\n'+'IPython post-mortem report\n\n']
        rpt_add = report.append
        rpt_add(sys_info())

        try:
            config = pformat(self.app.config)
            rpt_add(sec_sep)
            rpt_add("Application name: %s\n\n" % self.app.name)
            rpt_add("Current user configuration structure:\n\n")
            rpt_add(config)
        except:
            pass
        rpt_add(sec_sep+'Crash traceback:\n\n' + traceback)

        return ''.join(report)


def crash_handler_lite(
    etype: type[BaseException], evalue: BaseException, tb: types.TracebackType
) -> None:
    """a light excepthook, adding a small message to the usual traceback"""
    traceback.print_exception(etype, evalue, tb)
    
    from IPython.core.interactiveshell import InteractiveShell
    if InteractiveShell.initialized():
        # we are in a Shell environment, give %magic example
        config = "%config "
    else:
        # we are not in a shell, show generic config
        config = "c."
    print(_lite_message_template.format(email=author_email, config=config, version=version), file=sys.stderr)


# === NexusCore/openenv\Lib\site-packages\IPython\core\profiledir.py ===
# encoding: utf-8
"""An object for managing IPython profile directories."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import os
import shutil
import errno
from pathlib import Path

from traitlets.config.configurable import LoggingConfigurable
from ..paths import get_ipython_package_dir
from ..utils.path import expand_path, ensure_dir_exists
from traitlets import Unicode, Bool, observe

from typing import Optional

#-----------------------------------------------------------------------------
# Module errors
#-----------------------------------------------------------------------------

class ProfileDirError(Exception):
    pass


#-----------------------------------------------------------------------------
# Class for managing profile directories
#-----------------------------------------------------------------------------

class ProfileDir(LoggingConfigurable):
    """An object to manage the profile directory and its resources.

    The profile directory is used by all IPython applications, to manage
    configuration, logging and security.

    This object knows how to find, create and manage these directories. This
    should be used by any code that wants to handle profiles.
    """

    security_dir_name = Unicode('security')
    log_dir_name = Unicode('log')
    startup_dir_name = Unicode('startup')
    pid_dir_name = Unicode('pid')
    static_dir_name = Unicode('static')
    security_dir = Unicode(u'')
    log_dir = Unicode(u'')
    startup_dir = Unicode(u'')
    pid_dir = Unicode(u'')
    static_dir = Unicode(u'')

    location = Unicode(u'',
        help="""Set the profile location directly. This overrides the logic used by the
        `profile` option.""",
        ).tag(config=True)

    _location_isset = Bool(False) # flag for detecting multiply set location
    @observe('location')
    def _location_changed(self, change):
        if self._location_isset:
            raise RuntimeError("Cannot set profile location more than once.")
        self._location_isset = True
        new = change['new']
        ensure_dir_exists(new)

        # ensure config files exist:
        self.security_dir = os.path.join(new, self.security_dir_name)
        self.log_dir = os.path.join(new, self.log_dir_name)
        self.startup_dir = os.path.join(new, self.startup_dir_name)
        self.pid_dir = os.path.join(new, self.pid_dir_name)
        self.static_dir = os.path.join(new, self.static_dir_name)
        self.check_dirs()

    def _mkdir(self, path: str, mode: Optional[int] = None) -> bool:
        """ensure a directory exists at a given path

        This is a version of os.mkdir, with the following differences:

        - returns whether the directory has been created or not.
        - ignores EEXIST, protecting against race conditions where
          the dir may have been created in between the check and
          the creation
        - sets permissions if requested and the dir already exists

        Parameters
        ----------
        path: str
            path of the dir to create
        mode: int
            see `mode` of `os.mkdir`

        Returns
        -------
        bool:
            returns True if it created the directory, False otherwise
        """

        if os.path.exists(path):
            if mode and os.stat(path).st_mode != mode:
                try:
                    os.chmod(path, mode)
                except OSError:
                    self.log.warning(
                        "Could not set permissions on %s",
                        path
                    )
            return False
        try:
            if mode:
                os.mkdir(path, mode)
            else:
                os.mkdir(path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                return False
            else:
                raise

        return True
    
    @observe('log_dir')
    def check_log_dir(self, change=None):
        self._mkdir(self.log_dir)
    
    @observe('startup_dir')
    def check_startup_dir(self, change=None):
        if self._mkdir(self.startup_dir):
            readme = os.path.join(self.startup_dir, "README")
            src = os.path.join(
                get_ipython_package_dir(), "core", "profile", "README_STARTUP"
            )

            if os.path.exists(src):
                if not os.path.exists(readme):
                    shutil.copy(src, readme)
            else:
                self.log.warning(
                    "Could not copy README_STARTUP to startup dir. Source file %s does not exist.",
                    src,
                )

    @observe('security_dir')
    def check_security_dir(self, change=None):
        self._mkdir(self.security_dir, 0o40700)

    @observe('pid_dir')
    def check_pid_dir(self, change=None):
        self._mkdir(self.pid_dir, 0o40700)

    def check_dirs(self):
        self.check_security_dir()
        self.check_log_dir()
        self.check_pid_dir()
        self.check_startup_dir()

    def copy_config_file(self, config_file: str, path: Path, overwrite=False) -> bool:
        """Copy a default config file into the active profile directory.

        Default configuration files are kept in :mod:`IPython.core.profile`.
        This function moves these from that location to the working profile
        directory.
        """
        dst = Path(os.path.join(self.location, config_file))
        if dst.exists() and not overwrite:
            return False
        if path is None:
            path = os.path.join(get_ipython_package_dir(), u'core', u'profile', u'default')
        assert isinstance(path, Path)
        src = path / config_file
        shutil.copy(src, dst)
        return True

    @classmethod
    def create_profile_dir(cls, profile_dir, config=None):
        """Create a new profile directory given a full path.

        Parameters
        ----------
        profile_dir : str
            The full path to the profile directory.  If it does exist, it will
            be used.  If not, it will be created.
        """
        return cls(location=profile_dir, config=config)

    @classmethod
    def create_profile_dir_by_name(cls, path, name=u'default', config=None):
        """Create a profile dir by profile name and path.

        Parameters
        ----------
        path : unicode
            The path (directory) to put the profile directory in.
        name : unicode
            The name of the profile.  The name of the profile directory will
            be "profile_<profile>".
        """
        if not os.path.isdir(path):
            raise ProfileDirError('Directory not found: %s' % path)
        profile_dir = os.path.join(path, u'profile_' + name)
        return cls(location=profile_dir, config=config)

    @classmethod
    def find_profile_dir_by_name(cls, ipython_dir, name=u'default', config=None):
        """Find an existing profile dir by profile name, return its ProfileDir.

        This searches through a sequence of paths for a profile dir.  If it
        is not found, a :class:`ProfileDirError` exception will be raised.

        The search path algorithm is:
        1. ``os.getcwd()`` # removed for security reason.
        2. ``ipython_dir``

        Parameters
        ----------
        ipython_dir : unicode or str
            The IPython directory to use.
        name : unicode or str
            The name of the profile.  The name of the profile directory
            will be "profile_<profile>".
        """
        dirname = u'profile_' + name
        paths = [ipython_dir]
        for p in paths:
            profile_dir = os.path.join(p, dirname)
            if os.path.isdir(profile_dir):
                return cls(location=profile_dir, config=config)
        else:
            raise ProfileDirError('Profile directory not found in paths: %s' % dirname)

    @classmethod
    def find_profile_dir(cls, profile_dir, config=None):
        """Find/create a profile dir and return its ProfileDir.

        This will create the profile directory if it doesn't exist.

        Parameters
        ----------
        profile_dir : unicode or str
            The path of the profile directory.
        """
        profile_dir = expand_path(profile_dir)
        if not os.path.isdir(profile_dir):
            raise ProfileDirError('Profile directory not found: %s' % profile_dir)
        return cls(location=profile_dir, config=config)

# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\spawn.py ===
###############################################################################
# Prepares and processes the data to setup the new process environment
#
# author: Thomas Moreau and Olivier Grisel
#
# adapted from multiprocessing/spawn.py (17/02/2017)
#  * Improve logging data
#
import os
import sys
import runpy
import textwrap
import types
from multiprocessing import process, util


if sys.platform != "win32":
    WINEXE = False
    WINSERVICE = False
else:
    import msvcrt
    from multiprocessing.reduction import duplicate

    WINEXE = sys.platform == "win32" and getattr(sys, "frozen", False)
    WINSERVICE = sys.executable.lower().endswith("pythonservice.exe")

if WINSERVICE:
    _python_exe = os.path.join(sys.exec_prefix, "python.exe")
else:
    _python_exe = sys.executable


def get_executable():
    return _python_exe


def _check_not_importing_main():
    if getattr(process.current_process(), "_inheriting", False):
        raise RuntimeError(
            textwrap.dedent(
                """\
            An attempt has been made to start a new process before the
            current process has finished its bootstrapping phase.

            This probably means that you are not using fork to start your
            child processes and you have forgotten to use the proper idiom
            in the main module:

                if __name__ == '__main__':
                    freeze_support()
                    ...

            The "freeze_support()" line can be omitted if the program
            is not going to be frozen to produce an executable."""
            )
        )


def get_preparation_data(name, init_main_module=True):
    """Return info about parent needed by child to unpickle process object."""
    _check_not_importing_main()
    d = dict(
        log_to_stderr=util._log_to_stderr,
        authkey=bytes(process.current_process().authkey),
        name=name,
        sys_argv=sys.argv,
        orig_dir=process.ORIGINAL_DIR,
        dir=os.getcwd(),
    )

    # Send sys_path and make sure the current directory will not be changed
    d["sys_path"] = [p if p != "" else process.ORIGINAL_DIR for p in sys.path]

    # Make sure to pass the information if the multiprocessing logger is active
    if util._logger is not None:
        d["log_level"] = util._logger.getEffectiveLevel()
        if util._logger.handlers:
            h = util._logger.handlers[0]
            d["log_fmt"] = h.formatter._fmt

    # Tell the child how to communicate with the resource_tracker
    from .resource_tracker import _resource_tracker

    _resource_tracker.ensure_running()
    if sys.platform == "win32":
        d["tracker_fd"] = msvcrt.get_osfhandle(_resource_tracker._fd)
    else:
        d["tracker_fd"] = _resource_tracker._fd

    if os.name == "posix":
        # joblib/loky#242: allow loky processes to retrieve the resource
        # tracker of their parent in case the child processes depickles
        # shared_memory objects, that are still tracked by multiprocessing's
        # resource_tracker by default.
        # XXX: this is a workaround that may be error prone: in the future, it
        # would be better to have loky subclass multiprocessing's shared_memory
        # to force registration of shared_memory segments via loky's
        # resource_tracker.
        from multiprocessing.resource_tracker import (
            _resource_tracker as mp_resource_tracker,
        )

        # multiprocessing's resource_tracker must be running before loky
        # process is created (othewise the child won't be able to use it if it
        # is created later on)
        mp_resource_tracker.ensure_running()
        d["mp_tracker_fd"] = mp_resource_tracker._fd

    # Figure out whether to initialise main in the subprocess as a module
    # or through direct execution (or to leave it alone entirely)
    if init_main_module:
        main_module = sys.modules["__main__"]
        try:
            main_mod_name = getattr(main_module.__spec__, "name", None)
        except BaseException:
            main_mod_name = None
        if main_mod_name is not None:
            d["init_main_from_name"] = main_mod_name
        elif sys.platform != "win32" or (not WINEXE and not WINSERVICE):
            main_path = getattr(main_module, "__file__", None)
            if main_path is not None:
                if (
                    not os.path.isabs(main_path)
                    and process.ORIGINAL_DIR is not None
                ):
                    main_path = os.path.join(process.ORIGINAL_DIR, main_path)
                d["init_main_from_path"] = os.path.normpath(main_path)

    return d


#
# Prepare current process
#
old_main_modules = []


def prepare(data, parent_sentinel=None):
    """Try to get current process ready to unpickle process object."""
    if "name" in data:
        process.current_process().name = data["name"]

    if "authkey" in data:
        process.current_process().authkey = data["authkey"]

    if "log_to_stderr" in data and data["log_to_stderr"]:
        util.log_to_stderr()

    if "log_level" in data:
        util.get_logger().setLevel(data["log_level"])

    if "log_fmt" in data:
        import logging

        util.get_logger().handlers[0].setFormatter(
            logging.Formatter(data["log_fmt"])
        )

    if "sys_path" in data:
        sys.path = data["sys_path"]

    if "sys_argv" in data:
        sys.argv = data["sys_argv"]

    if "dir" in data:
        os.chdir(data["dir"])

    if "orig_dir" in data:
        process.ORIGINAL_DIR = data["orig_dir"]

    if "mp_tracker_fd" in data:
        from multiprocessing.resource_tracker import (
            _resource_tracker as mp_resource_tracker,
        )

        mp_resource_tracker._fd = data["mp_tracker_fd"]
    if "tracker_fd" in data:
        from .resource_tracker import _resource_tracker

        if sys.platform == "win32":
            handle = data["tracker_fd"]
            handle = duplicate(handle, source_process=parent_sentinel)
            _resource_tracker._fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        else:
            _resource_tracker._fd = data["tracker_fd"]

    if "init_main_from_name" in data:
        _fixup_main_from_name(data["init_main_from_name"])
    elif "init_main_from_path" in data:
        _fixup_main_from_path(data["init_main_from_path"])


# Multiprocessing module helpers to fix up the main module in
# spawned subprocesses
def _fixup_main_from_name(mod_name):
    # __main__.py files for packages, directories, zip archives, etc, run
    # their "main only" code unconditionally, so we don't even try to
    # populate anything in __main__, nor do we make any changes to
    # __main__ attributes
    current_main = sys.modules["__main__"]
    if mod_name == "__main__" or mod_name.endswith(".__main__"):
        return

    # If this process was forked, __main__ may already be populated
    if getattr(current_main.__spec__, "name", None) == mod_name:
        return

    # Otherwise, __main__ may contain some non-main code where we need to
    # support unpickling it properly. We rerun it as __mp_main__ and make
    # the normal __main__ an alias to that
    old_main_modules.append(current_main)
    main_module = types.ModuleType("__mp_main__")
    main_content = runpy.run_module(
        mod_name, run_name="__mp_main__", alter_sys=True
    )
    main_module.__dict__.update(main_content)
    sys.modules["__main__"] = sys.modules["__mp_main__"] = main_module


def _fixup_main_from_path(main_path):
    # If this process was forked, __main__ may already be populated
    current_main = sys.modules["__main__"]

    # Unfortunately, the main ipython launch script historically had no
    # "if __name__ == '__main__'" guard, so we work around that
    # by treating it like a __main__.py file
    # See https://github.com/ipython/ipython/issues/4698
    main_name = os.path.splitext(os.path.basename(main_path))[0]
    if main_name == "ipython":
        return

    # Otherwise, if __file__ already has the setting we expect,
    # there's nothing more to do
    if getattr(current_main, "__file__", None) == main_path:
        return

    # If the parent process has sent a path through rather than a module
    # name we assume it is an executable script that may contain
    # non-main code that needs to be executed
    old_main_modules.append(current_main)
    main_module = types.ModuleType("__mp_main__")
    main_content = runpy.run_path(main_path, run_name="__mp_main__")
    main_module.__dict__.update(main_content)
    sys.modules["__main__"] = sys.modules["__mp_main__"] = main_module

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\image_variations\handler.py ===
"""
OpenAI Image Variations Handler
"""

from typing import Callable, Optional

import httpx
from openai import AsyncOpenAI, OpenAI

import litellm
from litellm.types.utils import FileTypes, ImageResponse, LlmProviders
from litellm.utils import ProviderConfigManager

from ...base_llm.image_variations.transformation import BaseImageVariationConfig
from ...custom_httpx.llm_http_handler import LiteLLMLoggingObj
from ..common_utils import OpenAIError


class OpenAIImageVariationsHandler:
    def get_sync_client(
        self,
        client: Optional[OpenAI],
        init_client_params: dict,
    ):
        if client is None:
            openai_client = OpenAI(
                **init_client_params,
            )
        else:
            openai_client = client
        return openai_client

    def get_async_client(
        self, client: Optional[AsyncOpenAI], init_client_params: dict
    ) -> AsyncOpenAI:
        if client is None:
            openai_client = AsyncOpenAI(
                **init_client_params,
            )
        else:
            openai_client = client
        return openai_client

    async def async_image_variations(
        self,
        api_key: str,
        api_base: str,
        organization: Optional[str],
        client: Optional[AsyncOpenAI],
        data: dict,
        headers: dict,
        model: Optional[str],
        timeout: Optional[float],
        max_retries: int,
        logging_obj: LiteLLMLoggingObj,
        model_response: ImageResponse,
        optional_params: dict,
        litellm_params: dict,
        image: FileTypes,
        provider_config: BaseImageVariationConfig,
    ) -> ImageResponse:
        try:
            init_client_params = {
                "api_key": api_key,
                "base_url": api_base,
                "http_client": litellm.client_session,
                "timeout": timeout,
                "max_retries": max_retries,  # type: ignore
                "organization": organization,
            }

            client = self.get_async_client(
                client=client, init_client_params=init_client_params
            )

            raw_response = await client.images.with_raw_response.create_variation(**data)  # type: ignore
            response = raw_response.parse()
            response_json = response.model_dump()

            ## LOGGING
            logging_obj.post_call(
                api_key=api_key,
                original_response=response_json,
                additional_args={
                    "headers": headers,
                    "api_base": api_base,
                },
            )

            ## RESPONSE OBJECT
            return provider_config.transform_response_image_variation(
                model=model,
                model_response=ImageResponse(**response_json),
                raw_response=httpx.Response(
                    status_code=200,
                    request=httpx.Request(
                        method="GET", url="https://litellm.ai"
                    ),  # mock request object
                ),
                logging_obj=logging_obj,
                request_data=data,
                image=image,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=None,
                api_key=api_key,
            )
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

    def image_variations(
        self,
        model_response: ImageResponse,
        api_key: str,
        api_base: str,
        model: Optional[str],
        image: FileTypes,
        timeout: Optional[float],
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        litellm_params: dict,
        print_verbose: Optional[Callable] = None,
        logger_fn=None,
        client=None,
        organization: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> ImageResponse:
        try:
            provider_config = ProviderConfigManager.get_provider_image_variation_config(
                model=model or "",  # openai defaults to dall-e-2
                provider=LlmProviders.OPENAI,
            )

            if provider_config is None:
                raise ValueError(
                    f"image variation provider not found: {custom_llm_provider}."
                )

            max_retries = optional_params.pop("max_retries", 2)

            data = provider_config.transform_request_image_variation(
                model=model,
                image=image,
                optional_params=optional_params,
                headers=headers or {},
            )
            json_data = data.get("data")
            if not json_data:
                raise ValueError(
                    f"data field is required, for openai image variations. Got={data}"
                )
            ## LOGGING
            logging_obj.pre_call(
                input="",
                api_key=api_key,
                additional_args={
                    "headers": headers,
                    "api_base": api_base,
                    "complete_input_dict": data,
                },
            )
            if litellm_params.get("async_call", False):
                return self.async_image_variations(
                    api_base=api_base,
                    data=json_data,
                    headers=headers or {},
                    model_response=model_response,
                    api_key=api_key,
                    logging_obj=logging_obj,
                    model=model,
                    timeout=timeout,
                    max_retries=max_retries,
                    organization=organization,
                    client=client,
                    provider_config=provider_config,
                    image=image,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                )  # type: ignore

            init_client_params = {
                "api_key": api_key,
                "base_url": api_base,
                "http_client": litellm.client_session,
                "timeout": timeout,
                "max_retries": max_retries,  # type: ignore
                "organization": organization,
            }

            client = self.get_sync_client(
                client=client, init_client_params=init_client_params
            )

            raw_response = client.images.with_raw_response.create_variation(**json_data)  # type: ignore
            response = raw_response.parse()
            response_json = response.model_dump()

            ## LOGGING
            logging_obj.post_call(
                api_key=api_key,
                original_response=response_json,
                additional_args={
                    "headers": headers,
                    "api_base": api_base,
                },
            )

            ## RESPONSE OBJECT
            return provider_config.transform_response_image_variation(
                model=model,
                model_response=ImageResponse(**response_json),
                raw_response=httpx.Response(
                    status_code=200,
                    request=httpx.Request(
                        method="GET", url="https://litellm.ai"
                    ),  # mock request object
                ),
                logging_obj=logging_obj,
                request_data=json_data,
                image=image,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=None,
                api_key=api_key,
            )
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_text = getattr(e, "text", str(e))
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise OpenAIError(
                status_code=status_code, message=error_text, headers=error_headers
            )

# === NexusCore/openenv\Lib\site-packages\openai\types\responses\response_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .tool_param import ToolParam
from .response_includable import ResponseIncludable
from .tool_choice_options import ToolChoiceOptions
from .response_input_param import ResponseInputParam
from .response_prompt_param import ResponsePromptParam
from ..shared_params.metadata import Metadata
from .tool_choice_types_param import ToolChoiceTypesParam
from ..shared_params.reasoning import Reasoning
from .response_text_config_param import ResponseTextConfigParam
from .tool_choice_function_param import ToolChoiceFunctionParam
from ..shared_params.responses_model import ResponsesModel

__all__ = [
    "ResponseCreateParamsBase",
    "ToolChoice",
    "ResponseCreateParamsNonStreaming",
    "ResponseCreateParamsStreaming",
]


class ResponseCreateParamsBase(TypedDict, total=False):
    background: Optional[bool]
    """Whether to run the model response in the background.

    [Learn more](https://platform.openai.com/docs/guides/background).
    """

    include: Optional[List[ResponseIncludable]]
    """Specify additional output data to include in the model response.

    Currently supported values are:

    - `file_search_call.results`: Include the search results of the file search tool
      call.
    - `message.input_image.image_url`: Include image urls from the input message.
    - `computer_call_output.output.image_url`: Include image urls from the computer
      call output.
    - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
      tokens in reasoning item outputs. This enables reasoning items to be used in
      multi-turn conversations when using the Responses API statelessly (like when
      the `store` parameter is set to `false`, or when an organization is enrolled
      in the zero data retention program).
    - `code_interpreter_call.outputs`: Includes the outputs of python code execution
      in code interpreter tool call items.
    """

    input: Union[str, ResponseInputParam]
    """Text, image, or file inputs to the model, used to generate a response.

    Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Image inputs](https://platform.openai.com/docs/guides/images)
    - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
    - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
    - [Function calling](https://platform.openai.com/docs/guides/function-calling)
    """

    instructions: Optional[str]
    """A system (or developer) message inserted into the model's context.

    When using along with `previous_response_id`, the instructions from a previous
    response will not be carried over to the next response. This makes it simple to
    swap out system (or developer) messages in new responses.
    """

    max_output_tokens: Optional[int]
    """
    An upper bound for the number of tokens that can be generated for a response,
    including visible output tokens and
    [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: ResponsesModel
    """Model ID used to generate the response, like `gpt-4o` or `o3`.

    OpenAI offers a wide range of models with different capabilities, performance
    characteristics, and price points. Refer to the
    [model guide](https://platform.openai.com/docs/models) to browse and compare
    available models.
    """

    parallel_tool_calls: Optional[bool]
    """Whether to allow the model to run tool calls in parallel."""

    previous_response_id: Optional[str]
    """The unique ID of the previous response to the model.

    Use this to create multi-turn conversations. Learn more about
    [conversation state](https://platform.openai.com/docs/guides/conversation-state).
    """

    prompt: Optional[ResponsePromptParam]
    """Reference to a prompt template and its variables.

    [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).
    """

    reasoning: Optional[Reasoning]
    """**o-series models only**

    Configuration options for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning).
    """

    service_tier: Optional[Literal["auto", "default", "flex", "scale"]]
    """Specifies the latency tier to use for processing the request.

    This parameter is relevant for customers subscribed to the scale tier service:

    - If set to 'auto', and the Project is Scale tier enabled, the system will
      utilize scale tier credits until they are exhausted.
    - If set to 'auto', and the Project is not Scale tier enabled, the request will
      be processed using the default service tier with a lower uptime SLA and no
      latency guarantee.
    - If set to 'default', the request will be processed using the default service
      tier with a lower uptime SLA and no latency guarantee.
    - If set to 'flex', the request will be processed with the Flex Processing
      service tier.
      [Learn more](https://platform.openai.com/docs/guides/flex-processing).
    - When not set, the default behavior is 'auto'.

    When this parameter is set, the response body will include the `service_tier`
    utilized.
    """

    store: Optional[bool]
    """Whether to store the generated model response for later retrieval via API."""

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic. We generally recommend altering
    this or `top_p` but not both.
    """

    text: ResponseTextConfigParam
    """Configuration options for a text response from the model.

    Can be plain text or structured JSON data. Learn more:

    - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
    - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
    """

    tool_choice: ToolChoice
    """
    How the model should select which tool (or tools) to use when generating a
    response. See the `tools` parameter to see how to specify which tools the model
    can call.
    """

    tools: Iterable[ToolParam]
    """An array of tools the model may call while generating a response.

    You can specify which tool to use by setting the `tool_choice` parameter.

    The two categories of tools you can provide the model are:

    - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
      capabilities, like
      [web search](https://platform.openai.com/docs/guides/tools-web-search) or
      [file search](https://platform.openai.com/docs/guides/tools-file-search).
      Learn more about
      [built-in tools](https://platform.openai.com/docs/guides/tools).
    - **Function calls (custom tools)**: Functions that are defined by you, enabling
      the model to call your own code. Learn more about
      [function calling](https://platform.openai.com/docs/guides/function-calling).
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or `temperature` but not both.
    """

    truncation: Optional[Literal["auto", "disabled"]]
    """The truncation strategy to use for the model response.

    - `auto`: If the context of this response and previous ones exceeds the model's
      context window size, the model will truncate the response to fit the context
      window by dropping input items in the middle of the conversation.
    - `disabled` (default): If a model response will exceed the context window size
      for a model, the request will fail with a 400 error.
    """

    user: str
    """A stable identifier for your end-users.

    Used to boost cache hit rates by better bucketing similar requests and to help
    OpenAI detect and prevent abuse.
    [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).
    """


ToolChoice: TypeAlias = Union[ToolChoiceOptions, ToolChoiceTypesParam, ToolChoiceFunctionParam]


class ResponseCreateParamsNonStreaming(ResponseCreateParamsBase, total=False):
    stream: Optional[Literal[False]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
    for more information.
    """


class ResponseCreateParamsStreaming(ResponseCreateParamsBase):
    stream: Required[Literal[True]]
    """
    If set to true, the model response data will be streamed to the client as it is
    generated using
    [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
    See the
    [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
    for more information.
    """


ResponseCreateParams = Union[ResponseCreateParamsNonStreaming, ResponseCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\native\decoder.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import warnings

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['decode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_DECODER)


class AbstractScalarPayloadDecoder(object):
    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        return asn1Spec.clone(pyObject)


class BitStringPayloadDecoder(AbstractScalarPayloadDecoder):
    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        return asn1Spec.clone(univ.BitString.fromBinaryString(pyObject))


class SequenceOrSetPayloadDecoder(object):
    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Spec.componentType

        for field in asn1Value:
            if field in pyObject:
                asn1Value[field] = decodeFun(pyObject[field], componentsTypes[field].asn1Object, **options)

        return asn1Value


class SequenceOfOrSetOfPayloadDecoder(object):
    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        asn1Value = asn1Spec.clone()

        for pyValue in pyObject:
            asn1Value.append(decodeFun(pyValue, asn1Spec.componentType), **options)

        return asn1Value


class ChoicePayloadDecoder(object):
    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Spec.componentType

        for field in pyObject:
            if field in componentsTypes:
                asn1Value[field] = decodeFun(pyObject[field], componentsTypes[field].asn1Object, **options)
                break

        return asn1Value


TAG_MAP = {
    univ.Integer.tagSet: AbstractScalarPayloadDecoder(),
    univ.Boolean.tagSet: AbstractScalarPayloadDecoder(),
    univ.BitString.tagSet: BitStringPayloadDecoder(),
    univ.OctetString.tagSet: AbstractScalarPayloadDecoder(),
    univ.Null.tagSet: AbstractScalarPayloadDecoder(),
    univ.ObjectIdentifier.tagSet: AbstractScalarPayloadDecoder(),
    univ.RelativeOID.tagSet: AbstractScalarPayloadDecoder(),
    univ.Enumerated.tagSet: AbstractScalarPayloadDecoder(),
    univ.Real.tagSet: AbstractScalarPayloadDecoder(),
    univ.Sequence.tagSet: SequenceOrSetPayloadDecoder(),  # conflicts with SequenceOf
    univ.Set.tagSet: SequenceOrSetPayloadDecoder(),  # conflicts with SetOf
    univ.Choice.tagSet: ChoicePayloadDecoder(),  # conflicts with Any
    # character string types
    char.UTF8String.tagSet: AbstractScalarPayloadDecoder(),
    char.NumericString.tagSet: AbstractScalarPayloadDecoder(),
    char.PrintableString.tagSet: AbstractScalarPayloadDecoder(),
    char.TeletexString.tagSet: AbstractScalarPayloadDecoder(),
    char.VideotexString.tagSet: AbstractScalarPayloadDecoder(),
    char.IA5String.tagSet: AbstractScalarPayloadDecoder(),
    char.GraphicString.tagSet: AbstractScalarPayloadDecoder(),
    char.VisibleString.tagSet: AbstractScalarPayloadDecoder(),
    char.GeneralString.tagSet: AbstractScalarPayloadDecoder(),
    char.UniversalString.tagSet: AbstractScalarPayloadDecoder(),
    char.BMPString.tagSet: AbstractScalarPayloadDecoder(),
    # useful types
    useful.ObjectDescriptor.tagSet: AbstractScalarPayloadDecoder(),
    useful.GeneralizedTime.tagSet: AbstractScalarPayloadDecoder(),
    useful.UTCTime.tagSet: AbstractScalarPayloadDecoder()
}

# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Integer.typeId: AbstractScalarPayloadDecoder(),
    univ.Boolean.typeId: AbstractScalarPayloadDecoder(),
    univ.BitString.typeId: BitStringPayloadDecoder(),
    univ.OctetString.typeId: AbstractScalarPayloadDecoder(),
    univ.Null.typeId: AbstractScalarPayloadDecoder(),
    univ.ObjectIdentifier.typeId: AbstractScalarPayloadDecoder(),
    univ.RelativeOID.typeId: AbstractScalarPayloadDecoder(),
    univ.Enumerated.typeId: AbstractScalarPayloadDecoder(),
    univ.Real.typeId: AbstractScalarPayloadDecoder(),
    # ambiguous base types
    univ.Set.typeId: SequenceOrSetPayloadDecoder(),
    univ.SetOf.typeId: SequenceOfOrSetOfPayloadDecoder(),
    univ.Sequence.typeId: SequenceOrSetPayloadDecoder(),
    univ.SequenceOf.typeId: SequenceOfOrSetOfPayloadDecoder(),
    univ.Choice.typeId: ChoicePayloadDecoder(),
    univ.Any.typeId: AbstractScalarPayloadDecoder(),
    # character string types
    char.UTF8String.typeId: AbstractScalarPayloadDecoder(),
    char.NumericString.typeId: AbstractScalarPayloadDecoder(),
    char.PrintableString.typeId: AbstractScalarPayloadDecoder(),
    char.TeletexString.typeId: AbstractScalarPayloadDecoder(),
    char.VideotexString.typeId: AbstractScalarPayloadDecoder(),
    char.IA5String.typeId: AbstractScalarPayloadDecoder(),
    char.GraphicString.typeId: AbstractScalarPayloadDecoder(),
    char.VisibleString.typeId: AbstractScalarPayloadDecoder(),
    char.GeneralString.typeId: AbstractScalarPayloadDecoder(),
    char.UniversalString.typeId: AbstractScalarPayloadDecoder(),
    char.BMPString.typeId: AbstractScalarPayloadDecoder(),
    # useful types
    useful.ObjectDescriptor.typeId: AbstractScalarPayloadDecoder(),
    useful.GeneralizedTime.typeId: AbstractScalarPayloadDecoder(),
    useful.UTCTime.typeId: AbstractScalarPayloadDecoder()
}


class SingleItemDecoder(object):

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    def __call__(self, pyObject, asn1Spec, **options):

        if LOG:
            debug.scope.push(type(pyObject).__name__)
            LOG('decoder called at scope %s, working with '
                'type %s' % (debug.scope, type(pyObject).__name__))

        if asn1Spec is None or not isinstance(asn1Spec, base.Asn1Item):
            raise error.PyAsn1Error(
                'asn1Spec is not valid (should be an instance of an ASN.1 '
                'Item, not %s)' % asn1Spec.__class__.__name__)

        try:
            valueDecoder = self._typeMap[asn1Spec.typeId]

        except KeyError:
            # use base type for codec lookup to recover untagged types
            baseTagSet = tag.TagSet(asn1Spec.tagSet.baseTag, asn1Spec.tagSet.baseTag)

            try:
                valueDecoder = self._tagMap[baseTagSet]

            except KeyError:
                raise error.PyAsn1Error('Unknown ASN.1 tag %s' % asn1Spec.tagSet)

        if LOG:
            LOG('calling decoder %s on Python type %s '
                '<%s>' % (type(valueDecoder).__name__,
                          type(pyObject).__name__, repr(pyObject)))

        value = valueDecoder(pyObject, asn1Spec, self, **options)

        if LOG:
            LOG('decoder %s produced ASN.1 type %s '
                '<%s>' % (type(valueDecoder).__name__,
                          type(value).__name__, repr(value)))
            debug.scope.pop()

        return value


class Decoder(object):
    SINGLE_ITEM_DECODER = SingleItemDecoder

    def __init__(self, **options):
        self._singleItemDecoder = self.SINGLE_ITEM_DECODER(**options)

    def __call__(self, pyObject, asn1Spec=None, **kwargs):
        return self._singleItemDecoder(pyObject, asn1Spec=asn1Spec, **kwargs)


#: Turns Python objects of built-in types into ASN.1 objects.
#:
#: Takes Python objects of built-in types and turns them into a tree of
#: ASN.1 objects (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative) which
#: may be a scalar or an arbitrary nested structure.
#:
#: Parameters
#: ----------
#: pyObject: :py:class:`object`
#:     A scalar or nested Python objects
#:
#: Keyword Args
#: ------------
#: asn1Spec: any pyasn1 type object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A pyasn1 type object to act as a template guiding the decoder. It is required
#:     for successful interpretation of Python objects mapping into their ASN.1
#:     representations.
#:
#: Returns
#: -------
#: : :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A scalar or constructed pyasn1 object
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On decoding errors
#:
#: Examples
#: --------
#: Decode native Python object into ASN.1 objects with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> s, _ = decode([1, 2, 3], asn1Spec=seq)
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
decode = Decoder()

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning)
        return globals()[newAttr]
    raise AttributeError(attr)

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\dir_util.py ===
"""distutils.dir_util

Utility functions for manipulating directories and directory trees."""

import functools
import itertools
import os
import pathlib

from . import file_util
from ._log import log
from .errors import DistutilsFileError, DistutilsInternalError


class SkipRepeatAbsolutePaths(set):
    """
    Cache for mkpath.

    In addition to cheapening redundant calls, eliminates redundant
    "creating /foo/bar/baz" messages in dry-run mode.
    """

    def __init__(self):
        SkipRepeatAbsolutePaths.instance = self

    @classmethod
    def clear(cls):
        super(cls, cls.instance).clear()

    def wrap(self, func):
        @functools.wraps(func)
        def wrapper(path, *args, **kwargs):
            if path.absolute() in self:
                return
            result = func(path, *args, **kwargs)
            self.add(path.absolute())
            return result

        return wrapper


# Python 3.8 compatibility
wrapper = SkipRepeatAbsolutePaths().wrap


@functools.singledispatch
@wrapper
def mkpath(name: pathlib.Path, mode=0o777, verbose=True, dry_run=False) -> None:
    """Create a directory and any missing ancestor directories.

    If the directory already exists (or if 'name' is the empty string, which
    means the current directory, which of course exists), then do nothing.
    Raise DistutilsFileError if unable to create some directory along the way
    (eg. some sub-path exists, but is a file rather than a directory).
    If 'verbose' is true, log the directory created.
    """
    if verbose and not name.is_dir():
        log.info("creating %s", name)

    try:
        dry_run or name.mkdir(mode=mode, parents=True, exist_ok=True)
    except OSError as exc:
        raise DistutilsFileError(f"could not create '{name}': {exc.args[-1]}")


@mkpath.register
def _(name: str, *args, **kwargs):
    return mkpath(pathlib.Path(name), *args, **kwargs)


@mkpath.register
def _(name: None, *args, **kwargs):
    """
    Detect a common bug -- name is None.
    """
    raise DistutilsInternalError(f"mkpath: 'name' must be a string (got {name!r})")


def create_tree(base_dir, files, mode=0o777, verbose=True, dry_run=False):
    """Create all the empty directories under 'base_dir' needed to put 'files'
    there.

    'base_dir' is just the name of a directory which doesn't necessarily
    exist yet; 'files' is a list of filenames to be interpreted relative to
    'base_dir'.  'base_dir' + the directory portion of every file in 'files'
    will be created if it doesn't already exist.  'mode', 'verbose' and
    'dry_run' flags are as for 'mkpath()'.
    """
    # First get the list of directories to create
    need_dir = set(os.path.join(base_dir, os.path.dirname(file)) for file in files)

    # Now create them
    for dir in sorted(need_dir):
        mkpath(dir, mode, verbose=verbose, dry_run=dry_run)


def copy_tree(
    src,
    dst,
    preserve_mode=True,
    preserve_times=True,
    preserve_symlinks=False,
    update=False,
    verbose=True,
    dry_run=False,
):
    """Copy an entire directory tree 'src' to a new location 'dst'.

    Both 'src' and 'dst' must be directory names.  If 'src' is not a
    directory, raise DistutilsFileError.  If 'dst' does not exist, it is
    created with 'mkpath()'.  The end result of the copy is that every
    file in 'src' is copied to 'dst', and directories under 'src' are
    recursively copied to 'dst'.  Return the list of files that were
    copied or might have been copied, using their output name.  The
    return value is unaffected by 'update' or 'dry_run': it is simply
    the list of all files under 'src', with the names changed to be
    under 'dst'.

    'preserve_mode' and 'preserve_times' are the same as for
    'copy_file'; note that they only apply to regular files, not to
    directories.  If 'preserve_symlinks' is true, symlinks will be
    copied as symlinks (on platforms that support them!); otherwise
    (the default), the destination of the symlink will be copied.
    'update' and 'verbose' are the same as for 'copy_file'.
    """
    if not dry_run and not os.path.isdir(src):
        raise DistutilsFileError(f"cannot copy tree '{src}': not a directory")
    try:
        names = os.listdir(src)
    except OSError as e:
        if dry_run:
            names = []
        else:
            raise DistutilsFileError(f"error listing files in '{src}': {e.strerror}")

    if not dry_run:
        mkpath(dst, verbose=verbose)

    copy_one = functools.partial(
        _copy_one,
        src=src,
        dst=dst,
        preserve_symlinks=preserve_symlinks,
        verbose=verbose,
        dry_run=dry_run,
        preserve_mode=preserve_mode,
        preserve_times=preserve_times,
        update=update,
    )
    return list(itertools.chain.from_iterable(map(copy_one, names)))


def _copy_one(
    name,
    *,
    src,
    dst,
    preserve_symlinks,
    verbose,
    dry_run,
    preserve_mode,
    preserve_times,
    update,
):
    src_name = os.path.join(src, name)
    dst_name = os.path.join(dst, name)

    if name.startswith('.nfs'):
        # skip NFS rename files
        return

    if preserve_symlinks and os.path.islink(src_name):
        link_dest = os.readlink(src_name)
        if verbose >= 1:
            log.info("linking %s -> %s", dst_name, link_dest)
        if not dry_run:
            os.symlink(link_dest, dst_name)
        yield dst_name

    elif os.path.isdir(src_name):
        yield from copy_tree(
            src_name,
            dst_name,
            preserve_mode,
            preserve_times,
            preserve_symlinks,
            update,
            verbose=verbose,
            dry_run=dry_run,
        )
    else:
        file_util.copy_file(
            src_name,
            dst_name,
            preserve_mode,
            preserve_times,
            update,
            verbose=verbose,
            dry_run=dry_run,
        )
        yield dst_name


def _build_cmdtuple(path, cmdtuples):
    """Helper for remove_tree()."""
    for f in os.listdir(path):
        real_f = os.path.join(path, f)
        if os.path.isdir(real_f) and not os.path.islink(real_f):
            _build_cmdtuple(real_f, cmdtuples)
        else:
            cmdtuples.append((os.remove, real_f))
    cmdtuples.append((os.rmdir, path))


def remove_tree(directory, verbose=True, dry_run=False):
    """Recursively remove an entire directory tree.

    Any errors are ignored (apart from being reported to stdout if 'verbose'
    is true).
    """
    if verbose >= 1:
        log.info("removing '%s' (and everything under it)", directory)
    if dry_run:
        return
    cmdtuples = []
    _build_cmdtuple(directory, cmdtuples)
    for cmd in cmdtuples:
        try:
            cmd[0](cmd[1])
            # Clear the cache
            SkipRepeatAbsolutePaths.clear()
        except OSError as exc:
            log.warning("error removing %s: %s", directory, exc)


def ensure_relative(path):
    """Take the full path 'path', and make it a relative path.

    This is useful to make 'path' the second argument to os.path.join().
    """
    drive, path = os.path.splitdrive(path)
    if path[0:1] == os.sep:
        path = drive + path[1:]
    return path

# === NexusCore/openenv\Lib\site-packages\PIL\ImageDraw2.py ===
#
# The Python Imaging Library
# $Id$
#
# WCK-style drawing interface operations
#
# History:
# 2003-12-07 fl   created
# 2005-05-15 fl   updated; added to PIL as ImageDraw2
# 2005-05-15 fl   added text support
# 2005-05-20 fl   added arc/chord/pieslice support
#
# Copyright (c) 2003-2005 by Secret Labs AB
# Copyright (c) 2003-2005 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#


"""
(Experimental) WCK-style drawing interface operations

.. seealso:: :py:mod:`PIL.ImageDraw`
"""
from __future__ import annotations

from typing import Any, AnyStr, BinaryIO

from . import Image, ImageColor, ImageDraw, ImageFont, ImagePath
from ._typing import Coords, StrOrBytesPath


class Pen:
    """Stores an outline color and width."""

    def __init__(self, color: str, width: int = 1, opacity: int = 255) -> None:
        self.color = ImageColor.getrgb(color)
        self.width = width


class Brush:
    """Stores a fill color"""

    def __init__(self, color: str, opacity: int = 255) -> None:
        self.color = ImageColor.getrgb(color)


class Font:
    """Stores a TrueType font and color"""

    def __init__(
        self, color: str, file: StrOrBytesPath | BinaryIO, size: float = 12
    ) -> None:
        # FIXME: add support for bitmap fonts
        self.color = ImageColor.getrgb(color)
        self.font = ImageFont.truetype(file, size)


class Draw:
    """
    (Experimental) WCK-style drawing interface
    """

    def __init__(
        self,
        image: Image.Image | str,
        size: tuple[int, int] | list[int] | None = None,
        color: float | tuple[float, ...] | str | None = None,
    ) -> None:
        if isinstance(image, str):
            if size is None:
                msg = "If image argument is mode string, size must be a list or tuple"
                raise ValueError(msg)
            image = Image.new(image, size, color)
        self.draw = ImageDraw.Draw(image)
        self.image = image
        self.transform: tuple[float, float, float, float, float, float] | None = None

    def flush(self) -> Image.Image:
        return self.image

    def render(
        self,
        op: str,
        xy: Coords,
        pen: Pen | Brush | None,
        brush: Brush | Pen | None = None,
        **kwargs: Any,
    ) -> None:
        # handle color arguments
        outline = fill = None
        width = 1
        if isinstance(pen, Pen):
            outline = pen.color
            width = pen.width
        elif isinstance(brush, Pen):
            outline = brush.color
            width = brush.width
        if isinstance(brush, Brush):
            fill = brush.color
        elif isinstance(pen, Brush):
            fill = pen.color
        # handle transformation
        if self.transform:
            path = ImagePath.Path(xy)
            path.transform(self.transform)
            xy = path
        # render the item
        if op in ("arc", "line"):
            kwargs.setdefault("fill", outline)
        else:
            kwargs.setdefault("fill", fill)
            kwargs.setdefault("outline", outline)
        if op == "line":
            kwargs.setdefault("width", width)
        getattr(self.draw, op)(xy, **kwargs)

    def settransform(self, offset: tuple[float, float]) -> None:
        """Sets a transformation offset."""
        (xoffset, yoffset) = offset
        self.transform = (1, 0, xoffset, 0, 1, yoffset)

    def arc(
        self,
        xy: Coords,
        pen: Pen | Brush | None,
        start: float,
        end: float,
        *options: Any,
    ) -> None:
        """
        Draws an arc (a portion of a circle outline) between the start and end
        angles, inside the given bounding box.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.arc`
        """
        self.render("arc", xy, pen, *options, start=start, end=end)

    def chord(
        self,
        xy: Coords,
        pen: Pen | Brush | None,
        start: float,
        end: float,
        *options: Any,
    ) -> None:
        """
        Same as :py:meth:`~PIL.ImageDraw2.Draw.arc`, but connects the end points
        with a straight line.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.chord`
        """
        self.render("chord", xy, pen, *options, start=start, end=end)

    def ellipse(self, xy: Coords, pen: Pen | Brush | None, *options: Any) -> None:
        """
        Draws an ellipse inside the given bounding box.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.ellipse`
        """
        self.render("ellipse", xy, pen, *options)

    def line(self, xy: Coords, pen: Pen | Brush | None, *options: Any) -> None:
        """
        Draws a line between the coordinates in the ``xy`` list.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.line`
        """
        self.render("line", xy, pen, *options)

    def pieslice(
        self,
        xy: Coords,
        pen: Pen | Brush | None,
        start: float,
        end: float,
        *options: Any,
    ) -> None:
        """
        Same as arc, but also draws straight lines between the end points and the
        center of the bounding box.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.pieslice`
        """
        self.render("pieslice", xy, pen, *options, start=start, end=end)

    def polygon(self, xy: Coords, pen: Pen | Brush | None, *options: Any) -> None:
        """
        Draws a polygon.

        The polygon outline consists of straight lines between the given
        coordinates, plus a straight line between the last and the first
        coordinate.


        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.polygon`
        """
        self.render("polygon", xy, pen, *options)

    def rectangle(self, xy: Coords, pen: Pen | Brush | None, *options: Any) -> None:
        """
        Draws a rectangle.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.rectangle`
        """
        self.render("rectangle", xy, pen, *options)

    def text(self, xy: tuple[float, float], text: AnyStr, font: Font) -> None:
        """
        Draws the string at the given position.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.text`
        """
        if self.transform:
            path = ImagePath.Path(xy)
            path.transform(self.transform)
            xy = path
        self.draw.text(xy, text, font=font.font, fill=font.color)

    def textbbox(
        self, xy: tuple[float, float], text: AnyStr, font: Font
    ) -> tuple[float, float, float, float]:
        """
        Returns bounding box (in pixels) of given text.

        :return: ``(left, top, right, bottom)`` bounding box

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.textbbox`
        """
        if self.transform:
            path = ImagePath.Path(xy)
            path.transform(self.transform)
            xy = path
        return self.draw.textbbox(xy, text, font=font.font)

    def textlength(self, text: AnyStr, font: Font) -> float:
        """
        Returns length (in pixels) of given text.
        This is the amount by which following text should be offset.

        .. seealso:: :py:meth:`PIL.ImageDraw.ImageDraw.textlength`
        """
        return self.draw.textlength(text, font=font.font)

# === NexusCore/openenv\Lib\site-packages\psutil\_psposix.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Routines common to all posix systems."""

import glob
import os
import signal
import sys
import time

from ._common import MACOS
from ._common import TimeoutExpired
from ._common import memoize
from ._common import sdiskusage
from ._common import usage_percent
from ._compat import PY3
from ._compat import ChildProcessError
from ._compat import FileNotFoundError
from ._compat import InterruptedError
from ._compat import PermissionError
from ._compat import ProcessLookupError
from ._compat import unicode


if MACOS:
    from . import _psutil_osx


if PY3:
    import enum
else:
    enum = None


__all__ = ['pid_exists', 'wait_pid', 'disk_usage', 'get_terminal_map']


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if pid == 0:
        # According to "man 2 kill" PID 0 has a special meaning:
        # it refers to <<every process in the process group of the
        # calling process>> so we don't want to go any further.
        # If we get here it means this UNIX platform *does* have
        # a process with id 0.
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # EPERM clearly means there's a process to deny access to
        return True
    # According to "man 2 kill" possible error values are
    # (EINVAL, EPERM, ESRCH)
    else:
        return True


# Python 3.5 signals enum (contributed by me ^^):
# https://bugs.python.org/issue21076
if enum is not None and hasattr(signal, "Signals"):
    Negsignal = enum.IntEnum(
        'Negsignal', dict([(x.name, -x.value) for x in signal.Signals])
    )

    def negsig_to_enum(num):
        """Convert a negative signal value to an enum."""
        try:
            return Negsignal(num)
        except ValueError:
            return num

else:  # pragma: no cover

    def negsig_to_enum(num):
        return num


def wait_pid(
    pid,
    timeout=None,
    proc_name=None,
    _waitpid=os.waitpid,
    _timer=getattr(time, 'monotonic', time.time),  # noqa: B008
    _min=min,
    _sleep=time.sleep,
    _pid_exists=pid_exists,
):
    """Wait for a process PID to terminate.

    If the process terminated normally by calling exit(3) or _exit(2),
    or by returning from main(), the return value is the positive integer
    passed to *exit().

    If it was terminated by a signal it returns the negated value of the
    signal which caused the termination (e.g. -SIGTERM).

    If PID is not a children of os.getpid() (current process) just
    wait until the process disappears and return None.

    If PID does not exist at all return None immediately.

    If *timeout* != None and process is still alive raise TimeoutExpired.
    timeout=0 is also possible (either return immediately or raise).
    """
    if pid <= 0:
        # see "man waitpid"
        msg = "can't wait for PID 0"
        raise ValueError(msg)
    interval = 0.0001
    flags = 0
    if timeout is not None:
        flags |= os.WNOHANG
        stop_at = _timer() + timeout

    def sleep(interval):
        # Sleep for some time and return a new increased interval.
        if timeout is not None:
            if _timer() >= stop_at:
                raise TimeoutExpired(timeout, pid=pid, name=proc_name)
        _sleep(interval)
        return _min(interval * 2, 0.04)

    # See: https://linux.die.net/man/2/waitpid
    while True:
        try:
            retpid, status = os.waitpid(pid, flags)
        except InterruptedError:
            interval = sleep(interval)
        except ChildProcessError:
            # This has two meanings:
            # - PID is not a child of os.getpid() in which case
            #   we keep polling until it's gone
            # - PID never existed in the first place
            # In both cases we'll eventually return None as we
            # can't determine its exit status code.
            while _pid_exists(pid):
                interval = sleep(interval)
            return
        else:
            if retpid == 0:
                # WNOHANG flag was used and PID is still running.
                interval = sleep(interval)
                continue

            if os.WIFEXITED(status):
                # Process terminated normally by calling exit(3) or _exit(2),
                # or by returning from main(). The return value is the
                # positive integer passed to *exit().
                return os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                # Process exited due to a signal. Return the negative value
                # of that signal.
                return negsig_to_enum(-os.WTERMSIG(status))
            # elif os.WIFSTOPPED(status):
            #     # Process was stopped via SIGSTOP or is being traced, and
            #     # waitpid() was called with WUNTRACED flag. PID is still
            #     # alive. From now on waitpid() will keep returning (0, 0)
            #     # until the process state doesn't change.
            #     # It may make sense to catch/enable this since stopped PIDs
            #     # ignore SIGTERM.
            #     interval = sleep(interval)
            #     continue
            # elif os.WIFCONTINUED(status):
            #     # Process was resumed via SIGCONT and waitpid() was called
            #     # with WCONTINUED flag.
            #     interval = sleep(interval)
            #     continue
            else:
                # Should never happen.
                raise ValueError("unknown process exit status %r" % status)


def disk_usage(path):
    """Return disk usage associated with path.
    Note: UNIX usually reserves 5% disk space which is not accessible
    by user. In this function "total" and "used" values reflect the
    total and used disk space whereas "free" and "percent" represent
    the "free" and "used percent" user disk space.
    """
    if PY3:
        st = os.statvfs(path)
    else:  # pragma: no cover
        # os.statvfs() does not support unicode on Python 2:
        # - https://github.com/giampaolo/psutil/issues/416
        # - http://bugs.python.org/issue18695
        try:
            st = os.statvfs(path)
        except UnicodeEncodeError:
            if isinstance(path, unicode):
                try:
                    path = path.encode(sys.getfilesystemencoding())
                except UnicodeEncodeError:
                    pass
                st = os.statvfs(path)
            else:
                raise

    # Total space which is only available to root (unless changed
    # at system level).
    total = st.f_blocks * st.f_frsize
    # Remaining free space usable by root.
    avail_to_root = st.f_bfree * st.f_frsize
    # Remaining free space usable by user.
    avail_to_user = st.f_bavail * st.f_frsize
    # Total space being used in general.
    used = total - avail_to_root
    if MACOS:
        # see: https://github.com/giampaolo/psutil/pull/2152
        used = _psutil_osx.disk_usage_used(path, used)
    # Total space which is available to user (same as 'total' but
    # for the user).
    total_user = used + avail_to_user
    # User usage percent compared to the total amount of space
    # the user can use. This number would be higher if compared
    # to root's because the user has less space (usually -5%).
    usage_percent_user = usage_percent(used, total_user, round_=1)

    # NB: the percentage is -5% than what shown by df due to
    # reserved blocks that we are currently not considering:
    # https://github.com/giampaolo/psutil/issues/829#issuecomment-223750462
    return sdiskusage(
        total=total, used=used, free=avail_to_user, percent=usage_percent_user
    )


@memoize
def get_terminal_map():
    """Get a map of device-id -> path as a dict.
    Used by Process.terminal().
    """
    ret = {}
    ls = glob.glob('/dev/tty*') + glob.glob('/dev/pts/*')
    for name in ls:
        assert name not in ret, name
        try:
            ret[os.stat(name).st_rdev] = name
        except FileNotFoundError:
            pass
    return ret

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\text_to_speech\text_to_speech_handler.py ===
from typing import Optional, TypedDict, Union

import httpx

import litellm
from litellm.llms.custom_httpx.http_handler import (
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.llms.openai.openai import HttpxBinaryResponseContent
from litellm.llms.vertex_ai.gemini.vertex_and_google_ai_studio_gemini import VertexLLM
from litellm.types.llms.vertex_ai import VERTEX_CREDENTIALS_TYPES


class VertexInput(TypedDict, total=False):
    text: Optional[str]
    ssml: Optional[str]


class VertexVoice(TypedDict, total=False):
    languageCode: str
    name: str


class VertexAudioConfig(TypedDict, total=False):
    audioEncoding: str
    speakingRate: str


class VertexTextToSpeechRequest(TypedDict, total=False):
    input: VertexInput
    voice: VertexVoice
    audioConfig: Optional[VertexAudioConfig]


class VertexTextToSpeechAPI(VertexLLM):
    """
    Vertex methods to support for batches
    """

    def __init__(self) -> None:
        super().__init__()

    def audio_speech(
        self,
        logging_obj,
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        api_base: Optional[str],
        timeout: Union[float, httpx.Timeout],
        model: str,
        input: str,
        voice: Optional[dict] = None,
        _is_async: Optional[bool] = False,
        optional_params: Optional[dict] = None,
        kwargs: Optional[dict] = None,
    ) -> HttpxBinaryResponseContent:
        import base64

        ####### Authenticate with Vertex AI ########
        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai_beta",
        )

        auth_header, _ = self._get_token_and_url(
            model="",
            auth_header=_auth_header,
            gemini_api_key=None,
            vertex_credentials=vertex_credentials,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            stream=False,
            custom_llm_provider="vertex_ai_beta",
            api_base=api_base,
        )

        headers = {
            "Authorization": f"Bearer {auth_header}",
            "x-goog-user-project": vertex_project,
            "Content-Type": "application/json",
            "charset": "UTF-8",
        }

        ######### End of Authentication ###########

        ####### Build the request ################
        # API Ref: https://cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize
        kwargs = kwargs or {}
        optional_params = optional_params or {}

        vertex_input = VertexInput(text=input)
        validate_vertex_input(vertex_input, kwargs, optional_params)

        # required param
        if voice is not None:
            vertex_voice = VertexVoice(**voice)
        elif "voice" in kwargs:
            vertex_voice = VertexVoice(**kwargs["voice"])
        else:
            # use defaults to not fail the request
            vertex_voice = VertexVoice(
                languageCode="en-US",
                name="en-US-Studio-O",
            )

        if "audioConfig" in kwargs:
            vertex_audio_config = VertexAudioConfig(**kwargs["audioConfig"])
        else:
            # use defaults to not fail the request
            vertex_audio_config = VertexAudioConfig(
                audioEncoding="LINEAR16",
                speakingRate="1",
            )

        request = VertexTextToSpeechRequest(
            input=vertex_input,
            voice=vertex_voice,
            audioConfig=vertex_audio_config,
        )

        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        ########## End of building request ############

        ########## Log the request for debugging / logging ############
        logging_obj.pre_call(
            input=[],
            api_key="",
            additional_args={
                "complete_input_dict": request,
                "api_base": url,
                "headers": headers,
            },
        )

        ########## End of logging ############
        ####### Send the request ###################
        if _is_async is True:
            return self.async_audio_speech(  # type:ignore
                logging_obj=logging_obj, url=url, headers=headers, request=request
            )
        sync_handler = _get_httpx_client()

        response = sync_handler.post(
            url=url,
            headers=headers,
            json=request,  # type: ignore
        )
        if response.status_code != 200:
            raise Exception(
                f"Request failed with status code {response.status_code}, {response.text}"
            )
        ############ Process the response ############
        _json_response = response.json()

        response_content = _json_response["audioContent"]

        # Decode base64 to get binary content
        binary_data = base64.b64decode(response_content)

        # Create an httpx.Response object
        response = httpx.Response(
            status_code=200,
            content=binary_data,
        )

        # Initialize the HttpxBinaryResponseContent instance
        http_binary_response = HttpxBinaryResponseContent(response)
        return http_binary_response

    async def async_audio_speech(
        self,
        logging_obj,
        url: str,
        headers: dict,
        request: VertexTextToSpeechRequest,
    ) -> HttpxBinaryResponseContent:
        import base64

        async_handler = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.VERTEX_AI
        )

        response = await async_handler.post(
            url=url,
            headers=headers,
            json=request,  # type: ignore
        )

        if response.status_code != 200:
            raise Exception(
                f"Request did not return a 200 status code: {response.status_code}, {response.text}"
            )

        _json_response = response.json()

        response_content = _json_response["audioContent"]

        # Decode base64 to get binary content
        binary_data = base64.b64decode(response_content)

        # Create an httpx.Response object
        response = httpx.Response(
            status_code=200,
            content=binary_data,
        )

        # Initialize the HttpxBinaryResponseContent instance
        http_binary_response = HttpxBinaryResponseContent(response)
        return http_binary_response


def validate_vertex_input(
    input_data: VertexInput, kwargs: dict, optional_params: dict
) -> None:
    # Remove None values
    if input_data.get("text") is None:
        input_data.pop("text", None)
    if input_data.get("ssml") is None:
        input_data.pop("ssml", None)

    # Check if use_ssml is set
    use_ssml = kwargs.get("use_ssml", optional_params.get("use_ssml", False))

    if use_ssml:
        if "text" in input_data:
            input_data["ssml"] = input_data.pop("text")
        elif "ssml" not in input_data:
            raise ValueError("SSML input is required when use_ssml is True.")
    else:
        # LiteLLM will auto-detect if text is in ssml format
        # check if "text" is an ssml - in this case we should pass it as ssml instead of text
        if input_data:
            _text = input_data.get("text", None) or ""
            if "<speak>" in _text:
                input_data["ssml"] = input_data.pop("text")

    if not input_data:
        raise ValueError("Either 'text' or 'ssml' must be provided.")
    if "text" in input_data and "ssml" in input_data:
        raise ValueError("Only one of 'text' or 'ssml' should be provided, not both.")

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_nbagg.py ===
"""Interactive figures in the IPython notebook."""
# Note: There is a notebook in
# lib/matplotlib/backends/web_backend/nbagg_uat.ipynb to help verify
# that changes made maintain expected behaviour.

from base64 import b64encode
import io
import json
import pathlib
import uuid

from ipykernel.comm import Comm
from IPython.display import display, Javascript, HTML

from matplotlib import is_interactive
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import _Backend, CloseEvent, NavigationToolbar2
from .backend_webagg_core import (
    FigureCanvasWebAggCore, FigureManagerWebAgg, NavigationToolbar2WebAgg)
from .backend_webagg_core import (  # noqa: F401 # pylint: disable=W0611
    TimerTornado, TimerAsyncio)


def connection_info():
    """
    Return a string showing the figure and connection status for the backend.

    This is intended as a diagnostic tool, and not for general use.
    """
    result = [
        '{fig} - {socket}'.format(
            fig=(manager.canvas.figure.get_label()
                 or f"Figure {manager.num}"),
            socket=manager.web_sockets)
        for manager in Gcf.get_all_fig_managers()
    ]
    if not is_interactive():
        result.append(f'Figures pending show: {len(Gcf.figs)}')
    return '\n'.join(result)


_FONT_AWESOME_CLASSES = {  # font-awesome 4 names
    'home': 'fa fa-home',
    'back': 'fa fa-arrow-left',
    'forward': 'fa fa-arrow-right',
    'zoom_to_rect': 'fa fa-square-o',
    'move': 'fa fa-arrows',
    'download': 'fa fa-floppy-o',
    None: None
}


class NavigationIPy(NavigationToolbar2WebAgg):

    # Use the standard toolbar items + download button
    toolitems = [(text, tooltip_text,
                  _FONT_AWESOME_CLASSES[image_file], name_of_method)
                 for text, tooltip_text, image_file, name_of_method
                 in (NavigationToolbar2.toolitems +
                     (('Download', 'Download plot', 'download', 'download'),))
                 if image_file in _FONT_AWESOME_CLASSES]


class FigureManagerNbAgg(FigureManagerWebAgg):
    _toolbar2_class = ToolbarCls = NavigationIPy

    def __init__(self, canvas, num):
        self._shown = False
        super().__init__(canvas, num)

    @classmethod
    def create_with_canvas(cls, canvas_class, figure, num):
        canvas = canvas_class(figure)
        manager = cls(canvas, num)
        if is_interactive():
            manager.show()
            canvas.draw_idle()

        def destroy(event):
            canvas.mpl_disconnect(cid)
            Gcf.destroy(manager)

        cid = canvas.mpl_connect('close_event', destroy)
        return manager

    def display_js(self):
        # XXX How to do this just once? It has to deal with multiple
        # browser instances using the same kernel (require.js - but the
        # file isn't static?).
        display(Javascript(FigureManagerNbAgg.get_javascript()))

    def show(self):
        if not self._shown:
            self.display_js()
            self._create_comm()
        else:
            self.canvas.draw_idle()
        self._shown = True
        # plt.figure adds an event which makes the figure in focus the active
        # one. Disable this behaviour, as it results in figures being put as
        # the active figure after they have been shown, even in non-interactive
        # mode.
        if hasattr(self, '_cidgcf'):
            self.canvas.mpl_disconnect(self._cidgcf)
        if not is_interactive():
            from matplotlib._pylab_helpers import Gcf
            Gcf.figs.pop(self.num, None)

    def reshow(self):
        """
        A special method to re-show the figure in the notebook.

        """
        self._shown = False
        self.show()

    @property
    def connected(self):
        return bool(self.web_sockets)

    @classmethod
    def get_javascript(cls, stream=None):
        if stream is None:
            output = io.StringIO()
        else:
            output = stream
        super().get_javascript(stream=output)
        output.write((pathlib.Path(__file__).parent
                      / "web_backend/js/nbagg_mpl.js")
                     .read_text(encoding="utf-8"))
        if stream is None:
            return output.getvalue()

    def _create_comm(self):
        comm = CommSocket(self)
        self.add_web_socket(comm)
        return comm

    def destroy(self):
        self._send_event('close')
        # need to copy comms as callbacks will modify this list
        for comm in list(self.web_sockets):
            comm.on_close()
        self.clearup_closed()

    def clearup_closed(self):
        """Clear up any closed Comms."""
        self.web_sockets = {socket for socket in self.web_sockets
                            if socket.is_open()}

        if len(self.web_sockets) == 0:
            CloseEvent("close_event", self.canvas)._process()

    def remove_comm(self, comm_id):
        self.web_sockets = {socket for socket in self.web_sockets
                            if socket.comm.comm_id != comm_id}


class FigureCanvasNbAgg(FigureCanvasWebAggCore):
    manager_class = FigureManagerNbAgg


class CommSocket:
    """
    Manages the Comm connection between IPython and the browser (client).

    Comms are 2 way, with the CommSocket being able to publish a message
    via the send_json method, and handle a message with on_message. On the
    JS side figure.send_message and figure.ws.onmessage do the sending and
    receiving respectively.

    """
    def __init__(self, manager):
        self.supports_binary = None
        self.manager = manager
        self.uuid = str(uuid.uuid4())
        # Publish an output area with a unique ID. The javascript can then
        # hook into this area.
        display(HTML("<div id=%r></div>" % self.uuid))
        try:
            self.comm = Comm('matplotlib', data={'id': self.uuid})
        except AttributeError as err:
            raise RuntimeError('Unable to create an IPython notebook Comm '
                               'instance. Are you in the IPython '
                               'notebook?') from err
        self.comm.on_msg(self.on_message)

        manager = self.manager
        self._ext_close = False

        def _on_close(close_message):
            self._ext_close = True
            manager.remove_comm(close_message['content']['comm_id'])
            manager.clearup_closed()

        self.comm.on_close(_on_close)

    def is_open(self):
        return not (self._ext_close or self.comm._closed)

    def on_close(self):
        # When the socket is closed, deregister the websocket with
        # the FigureManager.
        if self.is_open():
            try:
                self.comm.close()
            except KeyError:
                # apparently already cleaned it up?
                pass

    def send_json(self, content):
        self.comm.send({'data': json.dumps(content)})

    def send_binary(self, blob):
        if self.supports_binary:
            self.comm.send({'blob': 'image/png'}, buffers=[blob])
        else:
            # The comm is ASCII, so we send the image in base64 encoded data
            # URL form.
            data = b64encode(blob).decode('ascii')
            data_uri = f"data:image/png;base64,{data}"
            self.comm.send({'data': data_uri})

    def on_message(self, message):
        # The 'supports_binary' message is relevant to the
        # websocket itself.  The other messages get passed along
        # to matplotlib as-is.

        # Every message has a "type" and a "figure_id".
        message = json.loads(message['content']['data'])
        if message['type'] == 'closing':
            self.on_close()
            self.manager.clearup_closed()
        elif message['type'] == 'supports_binary':
            self.supports_binary = message['value']
        else:
            self.manager.handle_json(message)


@_Backend.export
class _BackendNbAgg(_Backend):
    FigureCanvas = FigureCanvasNbAgg
    FigureManager = FigureManagerNbAgg

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\actionscript.py ===
"""
    pygments.lexers.actionscript
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for ActionScript and MXML.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, using, this, words, default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['ActionScriptLexer', 'ActionScript3Lexer', 'MxmlLexer']


class ActionScriptLexer(RegexLexer):
    """
    For ActionScript source code.
    """

    name = 'ActionScript'
    aliases = ['actionscript', 'as']
    filenames = ['*.as']
    mimetypes = ['application/x-actionscript', 'text/x-actionscript',
                 'text/actionscript']
    url = 'https://en.wikipedia.org/wiki/ActionScript'
    version_added = '0.9'

    flags = re.DOTALL
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/(\\\\|\\[^\\]|[^/\\\n])*/[gim]*', String.Regex),
            (r'[~^*!%&<>|+=:;,/?\\-]+', Operator),
            (r'[{}\[\]();.]+', Punctuation),
            (words((
                'case', 'default', 'for', 'each', 'in', 'while', 'do', 'break',
                'return', 'continue', 'if', 'else', 'throw', 'try', 'catch',
                'var', 'with', 'new', 'typeof', 'arguments', 'instanceof', 'this',
                'switch'), suffix=r'\b'),
             Keyword),
            (words((
                'class', 'public', 'final', 'internal', 'native', 'override', 'private',
                'protected', 'static', 'import', 'extends', 'implements', 'interface',
                'intrinsic', 'return', 'super', 'dynamic', 'function', 'const', 'get',
                'namespace', 'package', 'set'), suffix=r'\b'),
             Keyword.Declaration),
            (r'(true|false|null|NaN|Infinity|-Infinity|undefined|Void)\b',
             Keyword.Constant),
            (words((
                'Accessibility', 'AccessibilityProperties', 'ActionScriptVersion',
                'ActivityEvent', 'AntiAliasType', 'ApplicationDomain', 'AsBroadcaster', 'Array',
                'AsyncErrorEvent', 'AVM1Movie', 'BevelFilter', 'Bitmap', 'BitmapData',
                'BitmapDataChannel', 'BitmapFilter', 'BitmapFilterQuality', 'BitmapFilterType',
                'BlendMode', 'BlurFilter', 'Boolean', 'ByteArray', 'Camera', 'Capabilities', 'CapsStyle',
                'Class', 'Color', 'ColorMatrixFilter', 'ColorTransform', 'ContextMenu',
                'ContextMenuBuiltInItems', 'ContextMenuEvent', 'ContextMenuItem',
                'ConvultionFilter', 'CSMSettings', 'DataEvent', 'Date', 'DefinitionError',
                'DeleteObjectSample', 'Dictionary', 'DisplacmentMapFilter', 'DisplayObject',
                'DisplacmentMapFilterMode', 'DisplayObjectContainer', 'DropShadowFilter',
                'Endian', 'EOFError', 'Error', 'ErrorEvent', 'EvalError', 'Event', 'EventDispatcher',
                'EventPhase', 'ExternalInterface', 'FileFilter', 'FileReference',
                'FileReferenceList', 'FocusDirection', 'FocusEvent', 'Font', 'FontStyle', 'FontType',
                'FrameLabel', 'FullScreenEvent', 'Function', 'GlowFilter', 'GradientBevelFilter',
                'GradientGlowFilter', 'GradientType', 'Graphics', 'GridFitType', 'HTTPStatusEvent',
                'IBitmapDrawable', 'ID3Info', 'IDataInput', 'IDataOutput', 'IDynamicPropertyOutput'
                'IDynamicPropertyWriter', 'IEventDispatcher', 'IExternalizable',
                'IllegalOperationError', 'IME', 'IMEConversionMode', 'IMEEvent', 'int',
                'InteractiveObject', 'InterpolationMethod', 'InvalidSWFError', 'InvokeEvent',
                'IOError', 'IOErrorEvent', 'JointStyle', 'Key', 'Keyboard', 'KeyboardEvent', 'KeyLocation',
                'LineScaleMode', 'Loader', 'LoaderContext', 'LoaderInfo', 'LoadVars', 'LocalConnection',
                'Locale', 'Math', 'Matrix', 'MemoryError', 'Microphone', 'MorphShape', 'Mouse', 'MouseEvent',
                'MovieClip', 'MovieClipLoader', 'Namespace', 'NetConnection', 'NetStatusEvent',
                'NetStream', 'NewObjectSample', 'Number', 'Object', 'ObjectEncoding', 'PixelSnapping',
                'Point', 'PrintJob', 'PrintJobOptions', 'PrintJobOrientation', 'ProgressEvent', 'Proxy',
                'QName', 'RangeError', 'Rectangle', 'ReferenceError', 'RegExp', 'Responder', 'Sample',
                'Scene', 'ScriptTimeoutError', 'Security', 'SecurityDomain', 'SecurityError',
                'SecurityErrorEvent', 'SecurityPanel', 'Selection', 'Shape', 'SharedObject',
                'SharedObjectFlushStatus', 'SimpleButton', 'Socket', 'Sound', 'SoundChannel',
                'SoundLoaderContext', 'SoundMixer', 'SoundTransform', 'SpreadMethod', 'Sprite',
                'StackFrame', 'StackOverflowError', 'Stage', 'StageAlign', 'StageDisplayState',
                'StageQuality', 'StageScaleMode', 'StaticText', 'StatusEvent', 'String', 'StyleSheet',
                'SWFVersion', 'SyncEvent', 'SyntaxError', 'System', 'TextColorType', 'TextField',
                'TextFieldAutoSize', 'TextFieldType', 'TextFormat', 'TextFormatAlign',
                'TextLineMetrics', 'TextRenderer', 'TextSnapshot', 'Timer', 'TimerEvent', 'Transform',
                'TypeError', 'uint', 'URIError', 'URLLoader', 'URLLoaderDataFormat', 'URLRequest',
                'URLRequestHeader', 'URLRequestMethod', 'URLStream', 'URLVariabeles', 'VerifyError',
                'Video', 'XML', 'XMLDocument', 'XMLList', 'XMLNode', 'XMLNodeType', 'XMLSocket',
                'XMLUI'), suffix=r'\b'),
             Name.Builtin),
            (words((
                'decodeURI', 'decodeURIComponent', 'encodeURI', 'escape', 'eval', 'isFinite', 'isNaN',
                'isXMLName', 'clearInterval', 'fscommand', 'getTimer', 'getURL', 'getVersion',
                'parseFloat', 'parseInt', 'setInterval', 'trace', 'updateAfterEvent',
                'unescape'), suffix=r'\b'),
             Name.Function),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
        ]
    }

    def analyse_text(text):
        """This is only used to disambiguate between ActionScript and
        ActionScript3. We return 0 here; the ActionScript3 lexer will match
        AS3 variable definitions and that will hopefully suffice."""
        return 0

class ActionScript3Lexer(RegexLexer):
    """
    For ActionScript 3 source code.
    """

    name = 'ActionScript 3'
    url = 'https://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/index.html'
    aliases = ['actionscript3', 'as3']
    filenames = ['*.as']
    mimetypes = ['application/x-actionscript3', 'text/x-actionscript3',
                 'text/actionscript3']
    version_added = '0.11'

    identifier = r'[$a-zA-Z_]\w*'
    typeidentifier = identifier + r'(?:\.<\w+>)?'

    flags = re.DOTALL | re.MULTILINE
    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(function\s+)(' + identifier + r')(\s*)(\()',
             bygroups(Keyword.Declaration, Name.Function, Text, Operator),
             'funcparams'),
            (r'(var|const)(\s+)(' + identifier + r')(\s*)(:)(\s*)(' +
             typeidentifier + r')',
             bygroups(Keyword.Declaration, Whitespace, Name, Whitespace, Punctuation, Whitespace,
                      Keyword.Type)),
            (r'(import|package)(\s+)((?:' + identifier + r'|\.)+)(\s*)',
             bygroups(Keyword, Whitespace, Name.Namespace, Whitespace)),
            (r'(new)(\s+)(' + typeidentifier + r')(\s*)(\()',
             bygroups(Keyword, Whitespace, Keyword.Type, Whitespace, Operator)),
            (r'//.*?\n', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/(\\\\|\\[^\\]|[^\\\n])*/[gisx]*', String.Regex),
            (r'(\.)(' + identifier + r')', bygroups(Operator, Name.Attribute)),
            (r'(case|default|for|each|in|while|do|break|return|continue|if|else|'
             r'throw|try|catch|with|new|typeof|arguments|instanceof|this|'
             r'switch|import|include|as|is)\b',
             Keyword),
            (r'(class|public|final|internal|native|override|private|protected|'
             r'static|import|extends|implements|interface|intrinsic|return|super|'
             r'dynamic|function|const|get|namespace|package|set)\b',
             Keyword.Declaration),
            (r'(true|false|null|NaN|Infinity|-Infinity|undefined|void)\b',
             Keyword.Constant),
            (r'(decodeURI|decodeURIComponent|encodeURI|escape|eval|isFinite|isNaN|'
             r'isXMLName|clearInterval|fscommand|getTimer|getURL|getVersion|'
             r'isFinite|parseFloat|parseInt|setInterval|trace|updateAfterEvent|'
             r'unescape)\b', Name.Function),
            (identifier, Name),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-f]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'[~^*!%&<>|+=:;,/?\\{}\[\]().-]+', Operator),
        ],
        'funcparams': [
            (r'\s+', Whitespace),
            (r'(\s*)(\.\.\.)?(' + identifier + r')(\s*)(:)(\s*)(' +
             typeidentifier + r'|\*)(\s*)',
             bygroups(Whitespace, Punctuation, Name, Whitespace, Operator, Whitespace,
                      Keyword.Type, Whitespace), 'defval'),
            (r'\)', Operator, 'type')
        ],
        'type': [
            (r'(\s*)(:)(\s*)(' + typeidentifier + r'|\*)',
             bygroups(Whitespace, Operator, Whitespace, Keyword.Type), '#pop:2'),
            (r'\s+', Text, '#pop:2'),
            default('#pop:2')
        ],
        'defval': [
            (r'(=)(\s*)([^(),]+)(\s*)(,?)',
             bygroups(Operator, Whitespace, using(this), Whitespace, Operator), '#pop'),
            (r',', Operator, '#pop'),
            default('#pop')
        ]
    }

    def analyse_text(text):
        if re.match(r'\w+\s*:\s*\w', text):
            return 0.3
        return 0


class MxmlLexer(RegexLexer):
    """
    For MXML markup.
    Nested AS3 in <script> tags is highlighted by the appropriate lexer.
    """
    flags = re.MULTILINE | re.DOTALL
    name = 'MXML'
    aliases = ['mxml']
    filenames = ['*.mxml']
    url = 'https://en.wikipedia.org/wiki/MXML'
    version_added = '1.1'

    tokens = {
        'root': [
            ('[^<&]+', Text),
            (r'&\S*?;', Name.Entity),
            (r'(\<\!\[CDATA\[)(.*?)(\]\]\>)',
             bygroups(String, using(ActionScript3Lexer), String)),
            ('<!--', Comment, 'comment'),
            (r'<\?.*?\?>', Comment.Preproc),
            ('<![^>]*>', Comment.Preproc),
            (r'<\s*[\w:.-]+', Name.Tag, 'tag'),
            (r'<\s*/\s*[\w:.-]+\s*>', Name.Tag),
        ],
        'comment': [
            ('[^-]+', Comment),
            ('-->', Comment, '#pop'),
            ('-', Comment),
        ],
        'tag': [
            (r'\s+', Whitespace),
            (r'[\w.:-]+\s*=', Name.Attribute, 'attr'),
            (r'/?\s*>', Name.Tag, '#pop'),
        ],
        'attr': [
            (r'\s+', Whitespace),
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\ocx\ocxtest.py ===
# OCX Tester for Pythonwin
#
# This file _is_ ready to run.  All that is required is that the OCXs being tested
# are installed on your machine.
#
# The .py files behind the OCXs will be automatically generated and imported.

import glob
import os

import win32api
import win32con
import win32ui
from pywin.mfc import activex, dialog, window
from win32com.client import gencache


def MakeDlgTemplate():
    style = (
        win32con.DS_MODALFRAME
        | win32con.WS_POPUP
        | win32con.WS_VISIBLE
        | win32con.WS_CAPTION
        | win32con.WS_SYSMENU
        | win32con.DS_SETFONT
    )
    cs = win32con.WS_CHILD | win32con.WS_VISIBLE
    dlg = [
        ["OCX Demos", (0, 0, 350, 350), style, None, (8, "MS Sans Serif")],
    ]
    s = win32con.WS_TABSTOP | cs
    # 	dlg.append([131, None, 130, (5, 40, 110, 48),
    # 		s | win32con.LBS_NOTIFY | win32con.LBS_SORT | win32con.LBS_NOINTEGRALHEIGHT | win32con.WS_VSCROLL | win32con.WS_BORDER])
    # 	dlg.append(["{8E27C92B-1264-101C-8A2F-040224009C02}", None, 131, (5, 40, 110, 48),win32con.WS_TABSTOP])

    dlg.append(
        [128, "About", win32con.IDOK, (124, 5, 50, 14), s | win32con.BS_DEFPUSHBUTTON]
    )
    s = win32con.BS_PUSHBUTTON | s
    dlg.append([128, "Close", win32con.IDCANCEL, (124, 22, 50, 14), s])

    return dlg


####################################
#
# Calendar test code
#


def GetTestCalendarClass():
    global calendarParentModule
    win32ui.DoWaitCursor(1)
    calendarParentModule = gencache.EnsureModule(
        "{8E27C92E-1264-101C-8A2F-040224009C02}", 0, 7, 0
    )
    win32ui.DoWaitCursor(0)
    if calendarParentModule is None:
        return None

    class TestCalDialog(dialog.Dialog):
        def OnInitDialog(self):
            class MyCal(activex.Control, calendarParentModule.Calendar):
                def OnAfterUpdate(self):
                    print("OnAfterUpdate")

                def OnClick(self):
                    print("OnClick")

                def OnDblClick(self):
                    print("OnDblClick")

                def OnKeyDown(self, KeyCode, Shift):
                    print("OnKeyDown", KeyCode, Shift)

                def OnKeyPress(self, KeyAscii):
                    print("OnKeyPress", KeyAscii)

                def OnKeyUp(self, KeyCode, Shift):
                    print("OnKeyUp", KeyCode, Shift)

                def OnBeforeUpdate(self, Cancel):
                    print("OnBeforeUpdate", Cancel)

                def OnNewMonth(self):
                    print("OnNewMonth")

                def OnNewYear(self):
                    print("OnNewYear")

            rc = dialog.Dialog.OnInitDialog(self)
            self.olectl = MyCal()
            try:
                self.olectl.CreateControl(
                    "OCX",
                    win32con.WS_TABSTOP | win32con.WS_VISIBLE,
                    (7, 43, 500, 300),
                    self._obj_,
                    131,
                )
            except win32ui.error:
                self.MessageBox("The Calendar Control could not be created")
                self.olectl = None
                self.EndDialog(win32con.IDCANCEL)

            return rc

        def OnOK(self):
            self.olectl.AboutBox()

    return TestCalDialog


####################################
#
# Video Control
#
def GetTestVideoModule():
    global videoControlModule, videoControlFileName
    win32ui.DoWaitCursor(1)
    videoControlModule = gencache.EnsureModule(
        "{05589FA0-C356-11CE-BF01-00AA0055595A}", 0, 2, 0
    )
    win32ui.DoWaitCursor(0)
    if videoControlModule is None:
        return None
    fnames = glob.glob(os.path.join(win32api.GetWindowsDirectory(), "*.avi"))
    if not fnames:
        print("No AVI files available in system directory")
        return None
    videoControlFileName = fnames[0]
    return videoControlModule


def GetTestVideoDialogClass():
    if GetTestVideoModule() is None:
        return None

    class TestVideoDialog(dialog.Dialog):
        def OnInitDialog(self):
            rc = dialog.Dialog.OnInitDialog(self)
            try:
                self.olectl = activex.MakeControlInstance(
                    videoControlModule.ActiveMovie
                )
                self.olectl.CreateControl(
                    "",
                    win32con.WS_TABSTOP | win32con.WS_VISIBLE,
                    (7, 43, 500, 300),
                    self._obj_,
                    131,
                )
            except win32ui.error:
                self.MessageBox("The Video Control could not be created")
                self.olectl = None
                self.EndDialog(win32con.IDCANCEL)
                return

            self.olectl.FileName = videoControlFileName
            # 			self.olectl.Run()
            return rc

        def OnOK(self):
            self.olectl.AboutBox()

    return TestVideoDialog


###############
#
# An OCX in an MDI Frame
#
class OCXFrame(window.MDIChildWnd):
    def __init__(self):
        pass  # Don't call base class doc/view version...

    def Create(self, controlClass, title, rect=None, parent=None):
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
        self._obj_ = win32ui.CreateMDIChild()
        self._obj_.AttachObject(self)
        self._obj_.CreateWindow(None, title, style, rect, parent)

        rect = self.GetClientRect()
        rect = (0, 0, rect[2] - rect[0], rect[3] - rect[1])
        self.ocx = controlClass()
        self.ocx.CreateControl(
            "", win32con.WS_VISIBLE | win32con.WS_CHILD, rect, self, 1000
        )


def MDITest():
    calendarParentModule = gencache.EnsureModule(
        "{8E27C92E-1264-101C-8A2F-040224009C02}", 0, 7, 0
    )

    class MyCal(activex.Control, calendarParentModule.Calendar):
        def OnAfterUpdate(self):
            print("OnAfterUpdate")

        def OnClick(self):
            print("OnClick")

    f = OCXFrame()
    f.Create(MyCal, "Calendar Test")


def test1():
    klass = GetTestCalendarClass()
    if klass is None:
        print(
            "Can not test the MSAccess Calendar control - it does not appear to be installed"
        )
        return

    d = klass(MakeDlgTemplate())
    d.DoModal()


def test2():
    klass = GetTestVideoDialogClass()
    if klass is None:
        print("Can not test the Video OCX - it does not appear to be installed,")
        print("or no AVI files can be found.")
        return
    d = klass(MakeDlgTemplate())
    d.DoModal()
    d = None


def testall():
    test1()
    test2()


def demo():
    testall()


if __name__ == "__main__":
    import demoutils

    if demoutils.NeedGoodGUI():
        testall()

# === NexusCore/openenv\Lib\site-packages\win32com\test\errorSemantics.py ===
# errorSemantics.py

# Test the Python error handling semantics.  Specifically:
#
# * When a Python COM object is called via IDispatch, the nominated
#   scode is placed in the exception tuple, and the HRESULT is
#   DISP_E_EXCEPTION
# * When the same interface is called via IWhatever, the
#   nominated  scode is returned directly (with the scode also
#   reflected in the exception tuple)
# * In all cases, the description etc end up in the exception tuple
# * "Normal" Python exceptions resolve to an E_FAIL "internal error"

import pythoncom
import winerror
from win32com.client import Dispatch
from win32com.server.exception import COMException
from win32com.server.util import wrap
from win32com.test.util import CaptureWriter


# Our COM server.
class TestServer:
    _public_methods_ = ["Clone", "Commit", "LockRegion", "Read"]
    _com_interfaces_ = [pythoncom.IID_IStream]

    def Clone(self):
        raise COMException("Not today", scode=winerror.E_UNEXPECTED)

    def Commit(self, flags):
        # Testing unicode: 1F600   '😀'; GRINNING FACE
        # Use the 'name' just for fun!
        if flags == 0:
            # A non com-specific exception.
            raise Exception("\N{GRINNING FACE}")
        # An explicit com_error, which is a bit of an edge-case, but might happen if
        # a COM server itself calls another COM object and it fails.
        excepinfo = (
            winerror.E_UNEXPECTED,
            "source",
            "\N{GRINNING FACE}",
            "helpfile",
            1,
            winerror.E_FAIL,
        )
        raise pythoncom.com_error(winerror.E_UNEXPECTED, "desc", excepinfo, None)


def test():
    # Call via a native interface.
    com_server = wrap(TestServer(), pythoncom.IID_IStream)
    try:
        com_server.Clone()
        raise AssertionError("Expecting this call to fail!")
    except pythoncom.com_error as com_exc:
        assert com_exc.hresult == winerror.E_UNEXPECTED, (
            "Calling the object natively did not yield the correct scode",
            str(com_exc),
        )
        exc = com_exc.excepinfo
        assert exc and exc[-1] == winerror.E_UNEXPECTED, (
            "The scode element of the exception tuple did not yield the correct scode",
            str(com_exc),
        )
        assert exc[2] == "Not today", (
            "The description in the exception tuple did not yield the correct string",
            str(com_exc),
        )
    cap = CaptureWriter()
    try:
        cap.capture()
        try:
            com_server.Commit(0)
        finally:
            cap.release()
        raise AssertionError("Expecting this call to fail!")
    except pythoncom.com_error as com_exc:
        assert com_exc.hresult == winerror.E_FAIL, (
            "The hresult was not E_FAIL for an internal error",
            str(com_exc),
        )
        assert com_exc.excepinfo[1] == "Python COM Server Internal Error", (
            "The description in the exception tuple did not yield the correct string",
            str(com_exc),
        )
    # Check we saw a traceback in stderr
    assert (
        cap.get_captured().find("Traceback") >= 0
    ), f"Could not find a traceback in stderr: {cap.get_captured()!r}"

    # Now do it all again, but using IDispatch
    com_server = Dispatch(wrap(TestServer()))
    try:
        com_server.Clone()
        raise AssertionError("Expecting this call to fail!")
    except pythoncom.com_error as com_exc:
        assert com_exc.hresult == winerror.DISP_E_EXCEPTION, (
            "Calling the object via IDispatch did not yield the correct scode",
            str(com_exc),
        )
        exc = com_exc.excepinfo
        assert exc and exc[-1] == winerror.E_UNEXPECTED, (
            "The scode element of the exception tuple did not yield the correct scode",
            str(com_exc),
        )
        assert exc[2] == "Not today", (
            "The description in the exception tuple did not yield the correct string",
            str(com_exc),
        )

    cap.clear()
    try:
        cap.capture()
        try:
            com_server.Commit(0)
        finally:
            cap.release()
        raise AssertionError("Expecting this call to fail!")
    except pythoncom.com_error as com_exc:
        assert com_exc.hresult == winerror.DISP_E_EXCEPTION, (
            "Calling the object via IDispatch did not yield the correct scode",
            str(com_exc),
        )
        exc = com_exc.excepinfo
        assert exc and exc[-1] == winerror.E_FAIL, (
            "The scode element of the exception tuple did not yield the correct scode",
            str(com_exc),
        )
        assert exc[1] == "Python COM Server Internal Error", (
            "The description in the exception tuple did not yield the correct string",
            str(com_exc),
        )
    # Check we saw a traceback in stderr
    assert (
        cap.get_captured().find("Traceback") >= 0
    ), f"Could not find a traceback in stderr: {cap.get_captured()!r}"

    # And an explicit com_error
    cap.clear()
    try:
        cap.capture()
        try:
            com_server.Commit(1)
        finally:
            cap.release()
        raise AssertionError("Expecting this call to fail!")
    except pythoncom.com_error as com_exc:
        assert com_exc.hresult == winerror.DISP_E_EXCEPTION, (
            "Calling the object via IDispatch did not yield the correct scode",
            str(com_exc),
        )
        exc = com_exc.excepinfo
        assert exc and exc[-1] == winerror.E_FAIL, (
            "The scode element of the exception tuple did not yield the correct scode",
            str(com_exc),
        )
        assert exc[1] == "source", (
            "The source in the exception tuple did not yield the correct string",
            str(com_exc),
        )
        assert exc[2] == "\U0001f600", (
            "The description in the exception tuple did not yield the correct string",
            str(com_exc),
        )
        assert exc[3] == "helpfile", (
            "The helpfile in the exception tuple did not yield the correct string",
            str(com_exc),
        )
        assert exc[4] == 1, (
            "The help context in the exception tuple did not yield the correct string",
            str(com_exc),
        )


try:
    import logging
except ImportError:
    logging = None
if logging is not None:
    import win32com

    class TestLogHandler(logging.Handler):
        def __init__(self):
            self.reset()
            logging.Handler.__init__(self)

        def reset(self):
            self.num_emits = 0
            self.last_record = None

        def emit(self, record):
            self.num_emits += 1
            self.last_record = self.format(record)
            return
            print("--- record start")
            print(self.last_record)
            print("--- record end")

    def testLogger():
        assert not hasattr(win32com, "logger")
        handler = TestLogHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        log = logging.getLogger("win32com_test")
        log.addHandler(handler)
        win32com.logger = log
        # Now throw some exceptions!
        # Native interfaces
        com_server = wrap(TestServer(), pythoncom.IID_IStream)
        try:
            com_server.Commit(0)
            raise AssertionError("should have failed")
        except pythoncom.error as exc:
            # `excepinfo` is a tuple with elt 2 being the traceback we captured.
            message = exc.excepinfo[2]
            assert message.endswith("Exception: \U0001f600\n")
        assert handler.num_emits == 1, handler.num_emits
        assert handler.last_record.startswith(
            "pythoncom error: Unexpected exception in gateway method 'Commit'"
        )
        handler.reset()

        # IDispatch
        com_server = Dispatch(wrap(TestServer()))
        try:
            com_server.Commit(0)
            raise AssertionError("should have failed")
        except pythoncom.error as exc:
            # `excepinfo` is a tuple with elt 2 being the traceback we captured.
            message = exc.excepinfo[2]
            assert message.endswith("Exception: \U0001f600\n")
        assert handler.num_emits == 1, handler.num_emits
        handler.reset()


if __name__ == "__main__":
    test()
    if logging is not None:
        testLogger()
    from win32com.test.util import CheckClean

    CheckClean()
    print("error semantic tests worked")