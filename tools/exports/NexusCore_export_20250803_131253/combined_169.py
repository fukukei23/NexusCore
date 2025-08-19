
# === NexusCore/tools\exports\export_20250803_114325\combined_190.py ===

# === NexusCore/openenv\Lib\site-packages\PIL\IcoImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# Windows Icon support for PIL
#
# History:
#       96-05-27 fl     Created
#
# Copyright (c) Secret Labs AB 1997.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#

# This plugin is a refactored version of Win32IconImagePlugin by Bryan Davis
# <casadebender@gmail.com>.
# https://code.google.com/archive/p/casadebender/wikis/Win32IconImagePlugin.wiki
#
# Icon format references:
#   * https://en.wikipedia.org/wiki/ICO_(file_format)
#   * https://msdn.microsoft.com/en-us/library/ms997538.aspx
from __future__ import annotations

import warnings
from io import BytesIO
from math import ceil, log
from typing import IO, NamedTuple

from . import BmpImagePlugin, Image, ImageFile, PngImagePlugin
from ._binary import i16le as i16
from ._binary import i32le as i32
from ._binary import o8
from ._binary import o16le as o16
from ._binary import o32le as o32

#
# --------------------------------------------------------------------

_MAGIC = b"\0\0\1\0"


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    fp.write(_MAGIC)  # (2+2)
    bmp = im.encoderinfo.get("bitmap_format") == "bmp"
    sizes = im.encoderinfo.get(
        "sizes",
        [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    frames = []
    provided_ims = [im] + im.encoderinfo.get("append_images", [])
    width, height = im.size
    for size in sorted(set(sizes)):
        if size[0] > width or size[1] > height or size[0] > 256 or size[1] > 256:
            continue

        for provided_im in provided_ims:
            if provided_im.size != size:
                continue
            frames.append(provided_im)
            if bmp:
                bits = BmpImagePlugin.SAVE[provided_im.mode][1]
                bits_used = [bits]
                for other_im in provided_ims:
                    if other_im.size != size:
                        continue
                    bits = BmpImagePlugin.SAVE[other_im.mode][1]
                    if bits not in bits_used:
                        # Another image has been supplied for this size
                        # with a different bit depth
                        frames.append(other_im)
                        bits_used.append(bits)
            break
        else:
            # TODO: invent a more convenient method for proportional scalings
            frame = provided_im.copy()
            frame.thumbnail(size, Image.Resampling.LANCZOS, reducing_gap=None)
            frames.append(frame)
    fp.write(o16(len(frames)))  # idCount(2)
    offset = fp.tell() + len(frames) * 16
    for frame in frames:
        width, height = frame.size
        # 0 means 256
        fp.write(o8(width if width < 256 else 0))  # bWidth(1)
        fp.write(o8(height if height < 256 else 0))  # bHeight(1)

        bits, colors = BmpImagePlugin.SAVE[frame.mode][1:] if bmp else (32, 0)
        fp.write(o8(colors))  # bColorCount(1)
        fp.write(b"\0")  # bReserved(1)
        fp.write(b"\0\0")  # wPlanes(2)
        fp.write(o16(bits))  # wBitCount(2)

        image_io = BytesIO()
        if bmp:
            frame.save(image_io, "dib")

            if bits != 32:
                and_mask = Image.new("1", size)
                ImageFile._save(
                    and_mask,
                    image_io,
                    [ImageFile._Tile("raw", (0, 0) + size, 0, ("1", 0, -1))],
                )
        else:
            frame.save(image_io, "png")
        image_io.seek(0)
        image_bytes = image_io.read()
        if bmp:
            image_bytes = image_bytes[:8] + o32(height * 2) + image_bytes[12:]
        bytes_len = len(image_bytes)
        fp.write(o32(bytes_len))  # dwBytesInRes(4)
        fp.write(o32(offset))  # dwImageOffset(4)
        current = fp.tell()
        fp.seek(offset)
        fp.write(image_bytes)
        offset = offset + bytes_len
        fp.seek(current)


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(_MAGIC)


class IconHeader(NamedTuple):
    width: int
    height: int
    nb_color: int
    reserved: int
    planes: int
    bpp: int
    size: int
    offset: int
    dim: tuple[int, int]
    square: int
    color_depth: int


class IcoFile:
    def __init__(self, buf: IO[bytes]) -> None:
        """
        Parse image from file-like object containing ico file data
        """

        # check magic
        s = buf.read(6)
        if not _accept(s):
            msg = "not an ICO file"
            raise SyntaxError(msg)

        self.buf = buf
        self.entry = []

        # Number of items in file
        self.nb_items = i16(s, 4)

        # Get headers for each item
        for i in range(self.nb_items):
            s = buf.read(16)

            # See Wikipedia
            width = s[0] or 256
            height = s[1] or 256

            # No. of colors in image (0 if >=8bpp)
            nb_color = s[2]
            bpp = i16(s, 6)
            icon_header = IconHeader(
                width=width,
                height=height,
                nb_color=nb_color,
                reserved=s[3],
                planes=i16(s, 4),
                bpp=i16(s, 6),
                size=i32(s, 8),
                offset=i32(s, 12),
                dim=(width, height),
                square=width * height,
                # See Wikipedia notes about color depth.
                # We need this just to differ images with equal sizes
                color_depth=bpp or (nb_color != 0 and ceil(log(nb_color, 2))) or 256,
            )

            self.entry.append(icon_header)

        self.entry = sorted(self.entry, key=lambda x: x.color_depth)
        # ICO images are usually squares
        self.entry = sorted(self.entry, key=lambda x: x.square, reverse=True)

    def sizes(self) -> set[tuple[int, int]]:
        """
        Get a set of all available icon sizes and color depths.
        """
        return {(h.width, h.height) for h in self.entry}

    def getentryindex(self, size: tuple[int, int], bpp: int | bool = False) -> int:
        for i, h in enumerate(self.entry):
            if size == h.dim and (bpp is False or bpp == h.color_depth):
                return i
        return 0

    def getimage(self, size: tuple[int, int], bpp: int | bool = False) -> Image.Image:
        """
        Get an image from the icon
        """
        return self.frame(self.getentryindex(size, bpp))

    def frame(self, idx: int) -> Image.Image:
        """
        Get an image from frame idx
        """

        header = self.entry[idx]

        self.buf.seek(header.offset)
        data = self.buf.read(8)
        self.buf.seek(header.offset)

        im: Image.Image
        if data[:8] == PngImagePlugin._MAGIC:
            # png frame
            im = PngImagePlugin.PngImageFile(self.buf)
            Image._decompression_bomb_check(im.size)
        else:
            # XOR + AND mask bmp frame
            im = BmpImagePlugin.DibImageFile(self.buf)
            Image._decompression_bomb_check(im.size)

            # change tile dimension to only encompass XOR image
            im._size = (im.size[0], int(im.size[1] / 2))
            d, e, o, a = im.tile[0]
            im.tile[0] = ImageFile._Tile(d, (0, 0) + im.size, o, a)

            # figure out where AND mask image starts
            if header.bpp == 32:
                # 32-bit color depth icon image allows semitransparent areas
                # PIL's DIB format ignores transparency bits, recover them.
                # The DIB is packed in BGRX byte order where X is the alpha
                # channel.

                # Back up to start of bmp data
                self.buf.seek(o)
                # extract every 4th byte (eg. 3,7,11,15,...)
                alpha_bytes = self.buf.read(im.size[0] * im.size[1] * 4)[3::4]

                # convert to an 8bpp grayscale image
                try:
                    mask = Image.frombuffer(
                        "L",  # 8bpp
                        im.size,  # (w, h)
                        alpha_bytes,  # source chars
                        "raw",  # raw decoder
                        ("L", 0, -1),  # 8bpp inverted, unpadded, reversed
                    )
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        mask = None
                    else:
                        raise
            else:
                # get AND image from end of bitmap
                w = im.size[0]
                if (w % 32) > 0:
                    # bitmap row data is aligned to word boundaries
                    w += 32 - (im.size[0] % 32)

                # the total mask data is
                # padded row size * height / bits per char

                total_bytes = int((w * im.size[1]) / 8)
                and_mask_offset = header.offset + header.size - total_bytes

                self.buf.seek(and_mask_offset)
                mask_data = self.buf.read(total_bytes)

                # convert raw data to image
                try:
                    mask = Image.frombuffer(
                        "1",  # 1 bpp
                        im.size,  # (w, h)
                        mask_data,  # source chars
                        "raw",  # raw decoder
                        ("1;I", int(w / 8), -1),  # 1bpp inverted, padded, reversed
                    )
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        mask = None
                    else:
                        raise

                # now we have two images, im is XOR image and mask is AND image

            # apply mask image as alpha channel
            if mask:
                im = im.convert("RGBA")
                im.putalpha(mask)

        return im


##
# Image plugin for Windows Icon files.


class IcoImageFile(ImageFile.ImageFile):
    """
    PIL read-only image support for Microsoft Windows .ico files.

    By default the largest resolution image in the file will be loaded. This
    can be changed by altering the 'size' attribute before calling 'load'.

    The info dictionary has a key 'sizes' that is a list of the sizes available
    in the icon file.

    Handles classic, XP and Vista icon formats.

    When saving, PNG compression is used. Support for this was only added in
    Windows Vista. If you are unable to view the icon in Windows, convert the
    image to "RGBA" mode before saving.

    This plugin is a refactored version of Win32IconImagePlugin by Bryan Davis
    <casadebender@gmail.com>.
    https://code.google.com/archive/p/casadebender/wikis/Win32IconImagePlugin.wiki
    """

    format = "ICO"
    format_description = "Windows Icon"

    def _open(self) -> None:
        self.ico = IcoFile(self.fp)
        self.info["sizes"] = self.ico.sizes()
        self.size = self.ico.entry[0].dim
        self.load()

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]) -> None:
        if value not in self.info["sizes"]:
            msg = "This is not one of the allowed sizes of this image"
            raise ValueError(msg)
        self._size = value

    def load(self) -> Image.core.PixelAccess | None:
        if self._im is not None and self.im.size == self.size:
            # Already loaded
            return Image.Image.load(self)
        im = self.ico.getimage(self.size)
        # if tile is PNG, it won't really be loaded yet
        im.load()
        self.im = im.im
        self._mode = im.mode
        if im.palette:
            self.palette = im.palette
        if im.size != self.size:
            warnings.warn("Image was not the expected size")

            index = self.ico.getentryindex(self.size)
            sizes = list(self.info["sizes"])
            sizes[index] = im.size
            self.info["sizes"] = set(sizes)

            self.size = im.size
        return None

    def load_seek(self, pos: int) -> None:
        # Flag the ImageFile.Parser so that it
        # just does all the decode at the end.
        pass


#
# --------------------------------------------------------------------


Image.register_open(IcoImageFile.format, IcoImageFile, _accept)
Image.register_save(IcoImageFile.format, _save)
Image.register_extension(IcoImageFile.format, ".ico")

Image.register_mime(IcoImageFile.format, "image/x-icon")

# === NexusCore/openenv\Lib\site-packages\charset_normalizer\cli\__main__.py ===
from __future__ import annotations

import argparse
import sys
import typing
from json import dumps
from os.path import abspath, basename, dirname, join, realpath
from platform import python_version
from unicodedata import unidata_version

import charset_normalizer.md as md_module
from charset_normalizer import from_fp
from charset_normalizer.models import CliDetectionResult
from charset_normalizer.version import __version__


def query_yes_no(question: str, default: str = "yes") -> bool:
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".

    Credit goes to (c) https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


class FileType:
    """Factory for creating file object types

    Instances of FileType are typically passed as type= arguments to the
    ArgumentParser add_argument() method.

    Keyword Arguments:
        - mode -- A string indicating how the file is to be opened. Accepts the
            same values as the builtin open() function.
        - bufsize -- The file's desired buffer size. Accepts the same values as
            the builtin open() function.
        - encoding -- The file's encoding. Accepts the same values as the
            builtin open() function.
        - errors -- A string indicating how encoding and decoding errors are to
            be handled. Accepts the same value as the builtin open() function.

    Backported from CPython 3.12
    """

    def __init__(
        self,
        mode: str = "r",
        bufsize: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
    ):
        self._mode = mode
        self._bufsize = bufsize
        self._encoding = encoding
        self._errors = errors

    def __call__(self, string: str) -> typing.IO:  # type: ignore[type-arg]
        # the special argument "-" means sys.std{in,out}
        if string == "-":
            if "r" in self._mode:
                return sys.stdin.buffer if "b" in self._mode else sys.stdin
            elif any(c in self._mode for c in "wax"):
                return sys.stdout.buffer if "b" in self._mode else sys.stdout
            else:
                msg = f'argument "-" with mode {self._mode}'
                raise ValueError(msg)

        # all other arguments are used as file names
        try:
            return open(string, self._mode, self._bufsize, self._encoding, self._errors)
        except OSError as e:
            message = f"can't open '{string}': {e}"
            raise argparse.ArgumentTypeError(message)

    def __repr__(self) -> str:
        args = self._mode, self._bufsize
        kwargs = [("encoding", self._encoding), ("errors", self._errors)]
        args_str = ", ".join(
            [repr(arg) for arg in args if arg != -1]
            + [f"{kw}={arg!r}" for kw, arg in kwargs if arg is not None]
        )
        return f"{type(self).__name__}({args_str})"


def cli_detect(argv: list[str] | None = None) -> int:
    """
    CLI assistant using ARGV and ArgumentParser
    :param argv:
    :return: 0 if everything is fine, anything else equal trouble
    """
    parser = argparse.ArgumentParser(
        description="The Real First Universal Charset Detector. "
        "Discover originating encoding used on text file. "
        "Normalize text to unicode."
    )

    parser.add_argument(
        "files", type=FileType("rb"), nargs="+", help="File(s) to be analysed"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Display complementary information about file if any. "
        "Stdout will contain logs about the detection process.",
    )
    parser.add_argument(
        "-a",
        "--with-alternative",
        action="store_true",
        default=False,
        dest="alternatives",
        help="Output complementary possibilities if any. Top-level JSON WILL be a list.",
    )
    parser.add_argument(
        "-n",
        "--normalize",
        action="store_true",
        default=False,
        dest="normalize",
        help="Permit to normalize input file. If not set, program does not write anything.",
    )
    parser.add_argument(
        "-m",
        "--minimal",
        action="store_true",
        default=False,
        dest="minimal",
        help="Only output the charset detected to STDOUT. Disabling JSON output.",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        default=False,
        dest="replace",
        help="Replace file when trying to normalize it instead of creating a new one.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        dest="force",
        help="Replace file without asking if you are sure, use this flag with caution.",
    )
    parser.add_argument(
        "-i",
        "--no-preemptive",
        action="store_true",
        default=False,
        dest="no_preemptive",
        help="Disable looking at a charset declaration to hint the detector.",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        action="store",
        default=0.2,
        type=float,
        dest="threshold",
        help="Define a custom maximum amount of noise allowed in decoded content. 0. <= noise <= 1.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Charset-Normalizer {} - Python {} - Unicode {} - SpeedUp {}".format(
            __version__,
            python_version(),
            unidata_version,
            "OFF" if md_module.__file__.lower().endswith(".py") else "ON",
        ),
        help="Show version information and exit.",
    )

    args = parser.parse_args(argv)

    if args.replace is True and args.normalize is False:
        if args.files:
            for my_file in args.files:
                my_file.close()
        print("Use --replace in addition of --normalize only.", file=sys.stderr)
        return 1

    if args.force is True and args.replace is False:
        if args.files:
            for my_file in args.files:
                my_file.close()
        print("Use --force in addition of --replace only.", file=sys.stderr)
        return 1

    if args.threshold < 0.0 or args.threshold > 1.0:
        if args.files:
            for my_file in args.files:
                my_file.close()
        print("--threshold VALUE should be between 0. AND 1.", file=sys.stderr)
        return 1

    x_ = []

    for my_file in args.files:
        matches = from_fp(
            my_file,
            threshold=args.threshold,
            explain=args.verbose,
            preemptive_behaviour=args.no_preemptive is False,
        )

        best_guess = matches.best()

        if best_guess is None:
            print(
                'Unable to identify originating encoding for "{}". {}'.format(
                    my_file.name,
                    (
                        "Maybe try increasing maximum amount of chaos."
                        if args.threshold < 1.0
                        else ""
                    ),
                ),
                file=sys.stderr,
            )
            x_.append(
                CliDetectionResult(
                    abspath(my_file.name),
                    None,
                    [],
                    [],
                    "Unknown",
                    [],
                    False,
                    1.0,
                    0.0,
                    None,
                    True,
                )
            )
        else:
            x_.append(
                CliDetectionResult(
                    abspath(my_file.name),
                    best_guess.encoding,
                    best_guess.encoding_aliases,
                    [
                        cp
                        for cp in best_guess.could_be_from_charset
                        if cp != best_guess.encoding
                    ],
                    best_guess.language,
                    best_guess.alphabets,
                    best_guess.bom,
                    best_guess.percent_chaos,
                    best_guess.percent_coherence,
                    None,
                    True,
                )
            )

            if len(matches) > 1 and args.alternatives:
                for el in matches:
                    if el != best_guess:
                        x_.append(
                            CliDetectionResult(
                                abspath(my_file.name),
                                el.encoding,
                                el.encoding_aliases,
                                [
                                    cp
                                    for cp in el.could_be_from_charset
                                    if cp != el.encoding
                                ],
                                el.language,
                                el.alphabets,
                                el.bom,
                                el.percent_chaos,
                                el.percent_coherence,
                                None,
                                False,
                            )
                        )

            if args.normalize is True:
                if best_guess.encoding.startswith("utf") is True:
                    print(
                        '"{}" file does not need to be normalized, as it already came from unicode.'.format(
                            my_file.name
                        ),
                        file=sys.stderr,
                    )
                    if my_file.closed is False:
                        my_file.close()
                    continue

                dir_path = dirname(realpath(my_file.name))
                file_name = basename(realpath(my_file.name))

                o_: list[str] = file_name.split(".")

                if args.replace is False:
                    o_.insert(-1, best_guess.encoding)
                    if my_file.closed is False:
                        my_file.close()
                elif (
                    args.force is False
                    and query_yes_no(
                        'Are you sure to normalize "{}" by replacing it ?'.format(
                            my_file.name
                        ),
                        "no",
                    )
                    is False
                ):
                    if my_file.closed is False:
                        my_file.close()
                    continue

                try:
                    x_[0].unicode_path = join(dir_path, ".".join(o_))

                    with open(x_[0].unicode_path, "wb") as fp:
                        fp.write(best_guess.output())
                except OSError as e:
                    print(str(e), file=sys.stderr)
                    if my_file.closed is False:
                        my_file.close()
                    return 2

        if my_file.closed is False:
            my_file.close()

    if args.minimal is False:
        print(
            dumps(
                [el.__dict__ for el in x_] if len(x_) > 1 else x_[0].__dict__,
                ensure_ascii=True,
                indent=4,
            )
        )
    else:
        for my_file in args.files:
            print(
                ", ".join(
                    [
                        el.encoding or "undefined"
                        for el in x_
                        if el.path == abspath(my_file.name)
                    ]
                )
            )

    return 0


if __name__ == "__main__":
    cli_detect()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydev_ipython\qt_loaders.py ===
"""
This module contains factory functions that attempt
to return Qt submodules from the various python Qt bindings.

It also protects against double-importing Qt with different
bindings, which is unstable and likely to crash

This is used primarily by qt and qt_for_kernel, and shouldn't
be accessed directly from the outside
"""

import sys
from functools import partial

from pydev_ipython.version import check_version

# Available APIs.
QT_API_PYQT = "pyqt"
QT_API_PYQTv1 = "pyqtv1"
QT_API_PYQT_DEFAULT = "pyqtdefault"  # don't set SIP explicitly
QT_API_PYSIDE = "pyside"
QT_API_PYSIDE2 = "pyside2"
QT_API_PYSIDE6 = "pyside6"
QT_API_PYQT5 = "pyqt5"
QT_API_PYQT6 = "pyqt6"


class ImportDenier(object):
    """Import Hook that will guard against bad Qt imports
    once IPython commits to a specific binding
    """

    def __init__(self):
        self.__forbidden = set()

    def forbid(self, module_name):
        sys.modules.pop(module_name, None)
        self.__forbidden.add(module_name)

    def find_module(self, fullname, path=None):
        if path:
            return
        if fullname in self.__forbidden:
            return self

    def load_module(self, fullname):
        raise ImportError(
            """
    Importing %s disabled by IPython, which has
    already imported an Incompatible QT Binding: %s
    """
            % (fullname, loaded_api())
        )


ID = ImportDenier()
sys.meta_path.append(ID)


def commit_api(api):
    """Commit to a particular API, and trigger ImportErrors on subsequent
    dangerous imports"""

    if api == QT_API_PYSIDE:
        ID.forbid("PyQt4")
        ID.forbid("PyQt5")
        ID.forbid("PyQt6")
    else:
        ID.forbid("PySide")
        ID.forbid("PySide2")
        ID.forbid("PySide6")


def loaded_api():
    """Return which API is loaded, if any

    If this returns anything besides None,
    importing any other Qt binding is unsafe.

    Returns
    -------
    None, 'pyside', 'pyside2', 'pyside6', 'pyqt5', 'pyqt6', or 'pyqtv1'
    """
    if "PyQt4.QtCore" in sys.modules:
        if qtapi_version() == 2:
            return QT_API_PYQT
        else:
            return QT_API_PYQTv1
    elif "PySide.QtCore" in sys.modules:
        return QT_API_PYSIDE
    elif "PySide2.QtCore" in sys.modules:
        return QT_API_PYSIDE2
    elif "PySide6.QtCore" in sys.modules:
        return QT_API_PYSIDE6
    elif "PyQt5.QtCore" in sys.modules:
        return QT_API_PYQT5
    elif "PyQt6.QtCore" in sys.modules:
        return QT_API_PYQT6
    return None


def has_binding(api):
    """Safely check for PyQt or PySide, without importing
    submodules

    Parameters
    ----------
    api : str [ 'pyqtv1' | 'pyqt' | 'pyside' | 'pyqtdefault']
         Which module to check for

    Returns
    -------
    True if the relevant module appears to be importable
    """
    # we can't import an incomplete pyside and pyqt4
    # this will cause a crash in sip (#1431)
    # check for complete presence before importing
    module_name = {
        QT_API_PYSIDE: "PySide",
        QT_API_PYSIDE2: "PySide2",
        QT_API_PYSIDE6: "PySide6",
        QT_API_PYQT: "PyQt4",
        QT_API_PYQTv1: "PyQt4",
        QT_API_PYQT_DEFAULT: "PyQt4",
        QT_API_PYQT5: "PyQt5",
        QT_API_PYQT6: "PyQt6",
    }
    module_name = module_name[api]

    import importlib

    try:
        # importing top level PyQt4/PySide module is ok...
        mod = __import__(module_name)
        # ...importing submodules is not

        for check in ("QtCore", "QtGui", "QtSvg"):
            if importlib.util.find_spec("%s.%s" % (module_name, check)) is None:
                return False

        # we can also safely check PySide version
        if api == QT_API_PYSIDE:
            return check_version(mod.__version__, "1.0.3")
        else:
            return True

    except ModuleNotFoundError:
        try:
            from importlib import machinery

            # importing top level PyQt4/PySide module is ok...
            mod = __import__(module_name)

            # ...importing submodules is not
            loader_details = (machinery.ExtensionFileLoader, machinery.EXTENSION_SUFFIXES)
            submod_finder = machinery.FileFinder(mod.__path__[0], loader_details)
            submod_check = (
                submod_finder.find_spec("QtCore") is not None
                and submod_finder.find_spec("QtGui") is not None
                and submod_finder.find_spec("QtSvg") is not None
            )

            # we can also safely check PySide version
            if api == QT_API_PYSIDE:
                return check_version(mod.__version__, '1.0.3') and submod_check
            else:
                return submod_check
        except:
            return False
                
    except ImportError:
        return False


def qtapi_version():
    """Return which QString API has been set, if any

    Returns
    -------
    The QString API version (1 or 2), or None if not set
    """
    try:
        import sip
    except ImportError:
        return
    try:
        return sip.getapi("QString")
    except ValueError:
        return


def can_import(api):
    """Safely query whether an API is importable, without importing it"""
    if not has_binding(api):
        return False

    current = loaded_api()
    if api == QT_API_PYQT_DEFAULT:
        return current in [QT_API_PYQT, QT_API_PYQTv1, QT_API_PYQT5, QT_API_PYQT6, None]
    else:
        return current in [api, None]


def import_pyqt4(version=2):
    """
    Import PyQt4

    Parameters
    ----------
    version : 1, 2, or None
      Which QString/QVariant API to use. Set to None to use the system
      default

    ImportErrors raised within this function are non-recoverable
    """
    # The new-style string API (version=2) automatically
    # converts QStrings to Unicode Python strings. Also, automatically unpacks
    # QVariants to their underlying objects.
    import sip

    if version is not None:
        sip.setapi("QString", version)
        sip.setapi("QVariant", version)

    from PyQt4 import QtGui, QtCore, QtSvg

    if not check_version(QtCore.PYQT_VERSION_STR, "4.7"):
        raise ImportError("IPython requires PyQt4 >= 4.7, found %s" % QtCore.PYQT_VERSION_STR)

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    # query for the API version (in case version == None)
    version = sip.getapi("QString")
    api = QT_API_PYQTv1 if version == 1 else QT_API_PYQT
    return QtCore, QtGui, QtSvg, api


def import_pyqt5():
    """
    Import PyQt5

    ImportErrors raised within this function are non-recoverable
    """
    from PyQt5 import QtGui, QtCore, QtSvg

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    return QtCore, QtGui, QtSvg, QT_API_PYQT5


def import_pyqt6():
    """
    Import PyQt6

    ImportErrors raised within this function are non-recoverable
    """
    from PyQt6 import QtGui, QtCore, QtSvg

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    return QtCore, QtGui, QtSvg, QT_API_PYQT6


def import_pyside():
    """
    Import PySide

    ImportErrors raised within this function are non-recoverable
    """
    from PySide import QtGui, QtCore, QtSvg  # @UnresolvedImport

    return QtCore, QtGui, QtSvg, QT_API_PYSIDE


def import_pyside2():
    """
    Import PySide2

    ImportErrors raised within this function are non-recoverable
    """
    from PySide2 import QtGui, QtCore, QtSvg  # @UnresolvedImport

    return QtCore, QtGui, QtSvg, QT_API_PYSIDE2


def import_pyside6():
    """
    Import PySide6

    ImportErrors raised within this function are non-recoverable
    """
    from PySide6 import QtGui, QtCore, QtSvg  # @UnresolvedImport

    return QtCore, QtGui, QtSvg, QT_API_PYSIDE6


def load_qt(api_options):
    """
    Attempt to import Qt, given a preference list
    of permissible bindings

    It is safe to call this function multiple times.

    Parameters
    ----------
    api_options: List of strings
        The order of APIs to try. Valid items are 'pyside',
        'pyqt', and 'pyqtv1'

    Returns
    -------

    A tuple of QtCore, QtGui, QtSvg, QT_API
    The first three are the Qt modules. The last is the
    string indicating which module was loaded.

    Raises
    ------
    ImportError, if it isn't possible to import any requested
    bindings (either becaues they aren't installed, or because
    an incompatible library has already been installed)
    """
    loaders = {
        QT_API_PYSIDE: import_pyside,
        QT_API_PYSIDE2: import_pyside2,
        QT_API_PYSIDE6: import_pyside6,
        QT_API_PYQT: import_pyqt4,
        QT_API_PYQTv1: partial(import_pyqt4, version=1),
        QT_API_PYQT_DEFAULT: partial(import_pyqt4, version=None),
        QT_API_PYQT5: import_pyqt5,
        QT_API_PYQT6: import_pyqt6,
    }

    for api in api_options:
        if api not in loaders:
            raise RuntimeError(
                "Invalid Qt API %r, valid values are: %r, %r, %r, %r, %r, %r, %r"
                % (api, QT_API_PYSIDE, QT_API_PYSIDE2, QT_API_PYQT, QT_API_PYQTv1, QT_API_PYQT_DEFAULT, QT_API_PYQT5, QT_API_PYQT6)
            )

        if not can_import(api):
            continue

        # cannot safely recover from an ImportError during this
        result = loaders[api]()
        api = result[-1]  # changed if api = QT_API_PYQT_DEFAULT
        commit_api(api)
        return result
    else:
        raise ImportError(
            """
    Could not load requested Qt binding. Please ensure that
    PyQt4 >= 4.7 or PySide >= 1.0.3 is available,
    and only one is imported per session.

    Currently-imported Qt library:   %r
    PyQt4 installed:                 %s
    PyQt5 installed:                 %s
    PyQt6 installed:                 %s
    PySide >= 1.0.3 installed:       %s
    PySide2 installed:               %s
    PySide6 installed:               %s
    Tried to load:                   %r
    """
            % (
                loaded_api(),
                has_binding(QT_API_PYQT),
                has_binding(QT_API_PYQT5),
                has_binding(QT_API_PYQT6),
                has_binding(QT_API_PYSIDE),
                has_binding(QT_API_PYSIDE2),
                has_binding(QT_API_PYSIDE6),
                api_options,
            )
        )

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\profiles\defaults\codestral-few-shot.py ===
"""
EXPERIMENTAL
"""

print("Remember to `pip install open-interpreter[local]`.")

import subprocess

from interpreter import interpreter

interpreter.llm.model = "ollama/codestral"
interpreter.llm.max_tokens = 1000
interpreter.llm.context_window = 7000

model_name = interpreter.llm.model.replace("ollama/", "")
try:
    # List out all downloaded ollama models. Will fail if ollama isn't installed
    result = subprocess.run(
        ["ollama", "list"], capture_output=True, text=True, check=True
    )
except Exception as e:
    print(str(e))
    interpreter.display_message(
        f"> Ollama not found\n\nPlease download Ollama from [ollama.com](https://ollama.com/) to use `codestral`.\n"
    )
    exit()

lines = result.stdout.split("\n")
names = [
    line.split()[0].replace(":latest", "") for line in lines[1:] if line.strip()
]  # Extract names, trim out ":latest", skip header

if model_name not in names:
    interpreter.display_message(f"\nDownloading {model_name}...\n")
    subprocess.run(["ollama", "pull", model_name], check=True)

# Send a ping, which will actually load the model
interpreter.display_message("\n*Loading model...*\n")

old_max_tokens = interpreter.llm.max_tokens
interpreter.llm.max_tokens = 1
interpreter.computer.ai.chat("ping")
interpreter.llm.max_tokens = old_max_tokens

interpreter.display_message("> Model set to `codestral`")


# Set the system message to a minimal version for all local models.
interpreter.system_message = """
You are Open Interpreter, a world-class programmer that can execute code on the user's machine.
First, list all of the information you know related to the user's request.
Next, write a plan. **Always recap the plan between each code block** (you have extreme short-term memory loss, so you need to recap the plan between each message block to retain it).
The code you write must be able to be executed as is. Invalid syntax will cause a catastrophic failure. Do not include the language of the code in the response.
When you execute code, it will be executed **on the user's machine**. The user has given you **full and complete permission** to execute any code necessary to complete the task. Execute the code.
You can access the internet. Run **any code** to achieve the goal, and if at first you don't succeed, try again and again.
You can install new packages.
When a user refers to a filename, they're likely referring to an existing file in the directory you're currently executing code in.
Write messages to the user in Markdown.
In general, try to **make plans** with as few steps as possible. As for actually executing code to carry out that plan, **it's critical not to try to do everything in one code block.** You should try something, print information about it, then continue from there in tiny, informed steps. You will never get it on the first try, and attempting it in one go will often lead to errors you cant see.
You are capable of **any** task.
Once you have accomplished the task, ask the user if they are happy with the result and wait for their response. It is very important to get feedback from the user. 
The user will tell you the next task after you ask them.
"""

interpreter.system_message = """You are an AI assistant that writes markdown code snippets to answer the user's request. You speak very concisely and quickly, you say nothing irrelevant to the user's request. YOU NEVER USE PLACEHOLDERS, always code that should 'just work'."""
interpreter.llm.supports_functions = False
interpreter.messages = [
    {"role": "user", "type": "message", "content": "Open the chrome app."},
    {
        "role": "assistant",
        "type": "message",
        "content": "On it.\n```python\nimport webbrowser\nwebbrowser.open('https://chrome.google.com')\n```",
    },
    {
        "role": "user",
        "type": "message",
        "content": "The code you ran produced no output. Was this expected, or are we finished?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "No further action is required; the provided snippet opens Chrome.",
    },
]

# interpreter.user_message_template = "{content} Please send me some code that would be able to answer my question, in the form of ```python\n... the code ...\n``` or ```shell\n... the code ...\n```"
interpreter.code_output_template = '''I executed that code. This was the output: """\n{content}\n"""\n\nWhat does this output mean (I can't understand it, please help) / what code needs to be run next (if anything, or are we done)? I can't replace any placeholders, send me code that just works.'''
interpreter.empty_code_output_template = "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"
interpreter.code_output_sender = "user"
interpreter.max_output = 600
interpreter.llm.context_window = 8000
interpreter.loop = False
interpreter.user_message_template = "{content}. If my question must be solved by running code on my computer, send me code to run enclosed in ```python (preferred) or ```shell (less preferred). Otherwise, don't send code. Be concise, don't include anything unnecessary. Don't use placeholders, I can't edit code."
# interpreter.user_message_template = "{content}"
interpreter.llm.execution_instructions = False

# Set offline for all local models
interpreter.offline = True


# interpreter.user_message_template = "{content} Please send me some code that would be able to answer my question, in the form of ```python\n... the code ...\n``` or ```shell\n... the code ...\n```"
interpreter.code_output_template = '''I executed that code. This was the output: """{content}"""\n\nWhat does this output mean (I can't understand it, please help) / what's next (if anything, or are we done)?'''
interpreter.empty_code_output_template = "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"
interpreter.code_output_sender = "user"
interpreter.max_output = 600
interpreter.llm.context_window = 8000
interpreter.loop = False
interpreter.user_message_template = "{content}. If my question must be solved by running code on my computer, send me code to run enclosed in ```python (preferred) or ```shell (less preferred). Otherwise, don't send code. Be concise, don't include anything unnecessary. Don't use placeholders, I can't edit code."
interpreter.llm.execution_instructions = False

# Set offline for all local models
interpreter.offline = True


interpreter.system_message = """You are an AI assistant that returns code snippets that, if run, would answer the user's query. You speak very concisely and quickly, you say nothing irrelevant to the user's request. YOU NEVER USE PLACEHOLDERS, and instead always write code that 'just works' — for example, instead of a <username> placeholder, you put code that determines the user's username."""

interpreter.messages = [
    {
        "role": "user",
        "type": "message",
        "content": "Run a directory listing in the current folder.",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Absolutely, fetching the directory listing now.",
    },
    {"role": "assistant", "type": "code", "format": "shell", "content": "ls -la"},
    {
        "role": "computer",
        "type": "console",
        "format": "output",
        "content": "total 48\ndrwxr-xr-x  12 user  staff  384 Jan 12 12:34 .\ndrwxr-xr-x   6 user  staff  192 Jan 12 12:34 ..",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Here's the directory listing:\n\ntotal 48\ndrwxr-xr-x  12 user  staff  384 Jan 12 12:34 .\ndrwxr-xr-x   6 user  staff  192 Jan 12 12:34 ..\n\nWhat's next on your agenda?",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Can you multiply 2380 by 3875 for me?",
    },
    {"role": "assistant", "type": "code", "format": "python", "content": "2380*3875"},
    {"role": "computer", "type": "console", "format": "output", "content": "9222500"},
    {
        "role": "assistant",
        "type": "message",
        "content": "The multiplication of 2380 by 3875 gives you 9222500. Do you need this data for anything else?",
    },
    {"role": "user", "type": "message", "content": "Nah. I'll talk to you in an hour!"},
    {
        "role": "assistant",
        "type": "message",
        "content": "Alright, I'll be here. Talk to you soon!",
    },
]


interpreter.messages = [
    {
        "role": "user",
        "type": "message",
        "content": "Hello! I'm trying to provide IT support to someone remotely. I can run code on their computer. Here's their first request: 'what's in my cwd?'",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Absolutely, I can help with that. To get the contents of their current working directory (CWD), we'll use the `ls` command in a shell script like this:",
    },
    {"role": "assistant", "type": "code", "format": "shell", "content": "ls -la"},
    {
        "role": "computer",
        "type": "console",
        "format": "output",
        "content": "total 48\ndrwxr-xr-x  12 user  staff  384 Jan 12 12:34 .\ndrwxr-xr-x   6 user  staff  192 Jan 12 12:34 ..",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Here's the directory listing:\n\ntotal 48\ndrwxr-xr-x  12 user  staff  384 Jan 12 12:34 .\ndrwxr-xr-x   6 user  staff  192 Jan 12 12:34 ..\n\nWhat's next on your agenda?",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Can you multiply 2380 by 3875 for me?",
    },
    {"role": "assistant", "type": "code", "format": "python", "content": "2380*3875"},
    {"role": "computer", "type": "console", "format": "output", "content": "9222500"},
    {
        "role": "assistant",
        "type": "message",
        "content": "The multiplication of 2380 by 3875 gives you 9222500.",
    },
    {
        "role": "user",
        "type": "message",
        "content": """I just imported these functions: computer.view() — which will show me an image of what's on the user's screen (but only if it's ALONE in a codeblock, like the below)

```python
computer.view()
```

and I also imported computer.vision.query(path='path/to/image', query='describe this image.') which queries any image at path in natural language. Can you use these for requests in the future?""",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Yes, I'll be sure to use the `computer.view` and `computer.vision.query` functions for any future requests you have that involve vision or viewing your screen.",
    },
]


interpreter.llm.supports_functions = False

interpreter.computer.import_computer_api = True
interpreter.computer.system_message = ""

# interpreter.user_message_template = "{content} Please send me some code that would be able to answer my question, in the form of ```python\n... the code ...\n``` or ```shell\n... the code ...\n```"
interpreter.code_output_template = '''I executed that code. This was the output: """{content}"""\n\nWhat does this output mean (I can't understand it, please help) / what code needs to be run next (if anything, or are we done)? I can't replace any placeholders— please send me code to determine usernames, paths, etc given the request. I'm lazy!'''
interpreter.empty_code_output_template = "The code above was executed on my machine. It produced no text output. what's next (if anything, or are we done?)"
interpreter.code_output_sender = "user"
interpreter.max_output = 600
interpreter.llm.context_window = 8000
interpreter.loop = False
interpreter.user_message_template = "{content}. If my question must be solved by running code on my computer, send me code to run enclosed in ```python (preferred) or ```shell (less preferred). Otherwise, don't send code. Be concise, don't include anything unnecessary. Don't use placeholders, I can't edit code. Send code that will determine any placeholders (e.g. determine my username)."
interpreter.user_message_template = "I'm trying to help someone use their computer. Here's the last thing they said: '{content}'. What is some code that might be able to answer that question / what should I say to them? DONT USE PLACEHOLDERS! It needs to just work. If it's like a simple greeting, just tell me what to say (without code)."
# interpreter.user_message_template = "{content}"
interpreter.always_apply_user_message_template = False
interpreter.llm.execution_instructions = False
interpreter.auto_run = True

# Set offline for all local models
interpreter.offline = True

import os, platform

# Get the current user's login name
username = os.getlogin()
# Determine the operating system
operating_system = platform.system()
# Find the current working directory
cwd = os.getcwd()


# OS MODE

interpreter.messages = [
    {
        "role": "user",
        "type": "message",
        "content": "I have someone remotely accessing my computer and they're asking to perform tasks. Can you help me provide support by writing some code?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Absolutely, I can help with that.",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Great, could you provide me with the code to find out the username, operating system, and current working directory on my computer?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Sure, you can use the following Python script to retrieve the username, operating system, and current working directory of your computer:",
    },
    {
        "role": "assistant",
        "type": "code",
        "format": "python",
        "content": "import os\n# Get the current user's login name\nusername = os.getlogin()\n# Determine the operating system\noperating_system = os.name\n# Find the current working directory\ncwd = os.getcwd()\n# Print all the information\nprint(f'Username: {username}, OS: {operating_system}, Current Working Directory: {cwd}')",
    },
    {
        "role": "user",
        "type": "message",
        "content": f"I've executed the script, and here's the output: 'Username: {username}, OS: {operating_system}, Current Working Directory: {cwd}'",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": f"The output indicates that the username is '{username}', the operating system is {operating_system}, and the current working directory is '{cwd}'.",
    },
    {
        "role": "user",
        "type": "message",
        "content": "I just imported these functions: computer.view() — which will show me an image of what's on the user's screen when used alone in a code block, and computer.vision.query(path='path/to/image', query='describe this image.') which queries any image at path in natural language. Can you use these for requests in the future instead of like, pyautogui?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Yes, I can use those functions for future requests.",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Okay, what's on my screen right now? I might ask this again later btw, and I'll need you to run it again if I do.",
    },
    {
        "role": "assistant",
        "type": "code",
        "format": "python",
        "content": "computer.view()",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Okay, that returned this: 'There is a code editor on the screen, several open tabs, and a debugging console at the bottom.' What does this mean?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "It looks like there's a code editor open on your screen with multiple tabs and a debugging console visible. This setup is typically used for software development or editing scripts. Can I help with anything else?",
    },
    {"role": "user", "type": "message", "content": "Nah. I'll talk to you in an hour!"},
    {
        "role": "assistant",
        "type": "message",
        "content": "Alright, I'll be here. Talk to you soon!",
    },
]

interpreter.system_message = "You are an AI assistant designed to help users with remote IT support tasks. If the user asks you to use functions, be biased towards using them if possible."


interpreter.messages = [
    {
        "role": "user",
        "type": "message",
        "content": "I have someone remotely accessing my computer and they're asking to perform tasks. Can you help me provide support by writing some code?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Absolutely, I can help with that.",
    },
    {
        "role": "user",
        "type": "message",
        "content": "Great, could you provide me with the code to find out the username, operating system, and current working directory on my computer?",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": "Sure, you can use the following Python script to retrieve the username, operating system, and current working directory of your computer:",
    },
    {
        "role": "assistant",
        "type": "code",
        "format": "python",
        "content": "import os\n# Get the current user's login name\nusername = os.getlogin()\n# Determine the operating system\noperating_system = os.name\n# Find the current working directory\ncwd = os.getcwd()\n# Print all the information\nprint(f'Username: {username}, OS: {operating_system}, Current Working Directory: {cwd}')",
    },
    {
        "role": "user",
        "type": "message",
        "content": f"I've executed the script, and here's the output: 'Username: {username}, OS: {operating_system}, Current Working Directory: {cwd}'",
    },
    {
        "role": "assistant",
        "type": "message",
        "content": f"The output indicates that the username is '{username}', the operating system is {operating_system}, and the current working directory is '{cwd}'. Can I help with anything else?",
    },
    {"role": "user", "type": "message", "content": "Nah. I'll talk to you in an hour!"},
    {
        "role": "assistant",
        "type": "message",
        "content": "Alright, I'll be here. Talk to you soon!",
    },
]

interpreter.system_message = """You are an AI assistant that writes working markdown code snippets to answer the user's request. You speak concisely and quickly. You say nothing irrelevant to the user's request. YOU NEVER USE PLACEHOLDERS, and instead always send code that 'just works' by figuring out placeholders dynamically. When you send code that fails, you identify the issue, then send new code that doesn't fail."""
interpreter.max_output = 600
interpreter.llm.context_window = 8000
interpreter.loop = False
interpreter.user_message_template = "{content}. If my question must be solved by running code on my computer, send me code to run enclosed in ```python (preferred) or ```shell (less preferred). Otherwise, don't send code. Be concise, don't include anything unnecessary. Don't use placeholders, I can't edit code. Send code that will determine any placeholders (e.g. determine my username)."
interpreter.user_message_template = "I'm trying to help someone use their computer. Here's the last thing they said: '{content}'. What is some code that might be able to answer that question / what should I say to them? DONT USE PLACEHOLDERS! It needs to just work. If it's like a simple greeting, just tell me what to say (without code)."
interpreter.always_apply_user_message_template = False
interpreter.llm.execution_instructions = False
interpreter.auto_run = False

# === NexusCore/evaluation\evaluate\utils.py ===
import os
from evalplus.sanitize import sanitize
from typing import Any, Dict, List, Optional, Tuple, Union
import itertools
import multiprocessing
import time
from multiprocessing import Array, Value
from typing import Any, Dict, List, Tuple, Union

import numpy as np
import pickle

from evalplus.data.utils import CACHE_DIR
from evalplus.eval import *
from evalplus.gen.util import trusted_exec
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS, _poly
from evalplus.eval.utils import TimeoutException
from evalplus.eval.utils import (
    create_tempdir,
    reliability_guard,
    swallow_io,
    time_limit,
)
import re
import resource
import traceback


SUCCESS = "success"
FAILED = "failed"
TIMEOUT = "timed out"

_SUCCESS = 0
_FAILED = 1
_TIMEOUT = 2
_UNKNOWN = 3

_mapping = {_SUCCESS: SUCCESS, _FAILED: FAILED, _TIMEOUT: TIMEOUT, _UNKNOWN: None}

class MyCustomException(BaseException):
    def __init__(self, message):
        self.message = message


def get_groundtruth(problems, hashcode, tasks_only_output_not_none):
    cache_file = os.path.join(CACHE_DIR, f"{hashcode}.pkl")
    if os.path.exists(cache_file):
        print(f"Load from ground-truth from {cache_file}")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    os.makedirs(CACHE_DIR, exist_ok=True)
    print("Computing expected output...")
    tbegin = time.time()
    expected_output = {}
    for task_id, problem in problems.items():
        oracle = {}
        oracle["base"], oracle["base_time"] = trusted_exec(
            problem["prompt"] + problem["canonical_solution"],
            problem["base_input"],
            problem["entry_point"],
            record_time=True,
            output_not_none=problem["entry_point"] in tasks_only_output_not_none,
        )

        oracle["plus"], oracle["plus_time"] = trusted_exec(
            problem["prompt"] + problem["canonical_solution"],
            problem["plus_input"],
            problem["entry_point"],
            record_time=True,
            output_not_none=problem["entry_point"] in tasks_only_output_not_none,
        )
        expected_output[task_id] = oracle
    print(f"Expected outputs computed in {time.time() - tbegin:.2f}s")

    with open(cache_file, "wb") as f:
        pickle.dump(expected_output, f)

    return expected_output

def remove_unindented_lines(code, protect_before, execeptions, trim_tails):
    lines = code.splitlines()
    cut_idx = []
    cut_enabled = False
    for i, line in enumerate(lines):
        if not cut_enabled and line.startswith(protect_before):
            cut_enabled = True
            continue
        if line.strip() == "":
            continue
        if any(line.startswith(e) for e in execeptions):
            continue

        lspace = len(line) - len(line.lstrip())
        if lspace == 0:
            cut_idx.append(i)

        if any(line.rstrip().startswith(t) for t in trim_tails):
            # cut off everything behind
            cut_idx.extend(list(range(i, len(lines))))
            break

    return "\n".join([line for i, line in enumerate(lines) if i not in cut_idx])


def to_four_space_indents(old_code):
    new_code = ""
    for line in old_code.splitlines():
        lspace = len(line) - len(line.lstrip())
        if lspace == 3:
            new_code += " "
        new_code += line + "\n"
    return new_code


def sanitize_solution(solution,eofs):
    task_id = solution["task_id"]
    dbg_identifier = task_id
    entry_point = solution["entry_point"]

    old_code = solution["solution"]
    old_code = old_code.strip()

    new_code = sanitize(
        code=old_code,
        entrypoint=entry_point,
    ).strip()

    # if changed, print the message
    if new_code != old_code:
        msg = "Sanitized: " + dbg_identifier
        print(msg)
    solution["solution"]=new_code
    return solution



################################eval funcs############################
# 1st item: the status
# 2nd item (optional): the detailed pass/fail boolean for each input
Result = Tuple[str, List[bool]]

def is_floats(x) -> bool:
    # check if it is float; List[float]; Tuple[float]
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)):
        return all(isinstance(i, float) for i in x)
    if isinstance(x, np.ndarray):
        return x.dtype == np.float64 or x.dtype == np.float32
    return False


def unsafe_execute(
    dataset: str,
    entry_point: str,
    code: str,
    inputs,
    expected: List,
    time_limits,
    atol,
    fast_check,
    stat: Value,
    details: Array,
    progress: Value,
    feedback: Value,
    feedback_size: int,
):
    with create_tempdir():
        # These system calls are needed when cleaning up tempdir.
        import os
        import shutil

        rmtree = shutil.rmtree
        rmdir = os.rmdir
        chdir = os.chdir
        maximum_memory_bytes = None
        reliability_guard(maximum_memory_bytes=maximum_memory_bytes)
        exec_globals = {}
        try:
            with swallow_io():
                exec(code, exec_globals)
                try:
                    fn = exec_globals[entry_point]
                except KeyError as e:
                    raise f"Please rename your function to {entry_point} as there is no function named {entry_point}."
                except BaseException as e:
                    raise MyCustomException("An error occurred.")
                for i, inp in enumerate(inputs):
                    # try:
                    with time_limit(time_limits[i]):
                        out = fn(*inp)

                    exp = expected[i]
                    exact_match = out == exp

                    # ================================================ #
                    # ============== special oracles ================= #
                    if dataset == "mbpp":
                        if (
                            "are_equivalent" == entry_point
                        ):  # Mbpp/164 special oracle
                            exact_match = exact_match or True
                        elif "sum_div" == entry_point:  # Mbpp/295 special oracle
                            exact_match = exact_match or out == 0
                        elif entry_point in MBPP_OUTPUT_NOT_NONE_TASKS:
                            if isinstance(out, bool):
                                exact_match = out == exp
                            else:
                                exact_match = exp == (out is not None)

                    if dataset == "humaneval":
                        if "find_zero" == entry_point:
                            assert _poly(*out, inp) <= atol, f"The results aren't as expected.\nInput: {inp}\nExpected Output: {exp}\nActual Output: {out}"
                    # ============== special oracles ================= #
                    if atol == 0 and is_floats(exp):
                        atol = 1e-6  # enforce atol for float comparison
                    
                    if not exact_match and atol != 0:
                        try:
                            np.testing.assert_allclose(out, exp, atol=atol)
                        except BaseException as e:
                            raise AssertionError(f"The results aren't as expected.\nInput: {inp}\nExpected Output: {exp}\nActual Output: {out}")
                    else:
                        assert exact_match, f"The results aren't as expected.\nInput: {inp}\nExpected Output: {exp}\nActual Output: {out}"

                    details[i] = True
                    progress.value += 1
            stat.value = _SUCCESS
            padding = feedback_size - len(SUCCESS)
            feedback.value = (SUCCESS + " " * padding).encode('utf-8')
        except TimeoutException as e:
            stat.value = _FAILED
            error_str="Execution timed out."
            padding = max(0, feedback_size - len(error_str))
            feedback.value = (error_str + " " * padding).encode('utf-8')
        except AssertionError as e:
            stat.value = _FAILED
            error_str=str(e)[:feedback_size]
            padding = max(0, feedback_size - len(error_str))
            feedback.value = (error_str + " " * padding).encode('utf-8')
        except MyCustomException as e:
            stat.value = _FAILED
            error_str=e.message[:feedback_size]
            padding = max(0, feedback_size - len(error_str))
            feedback.value = (error_str + " " * padding).encode('utf-8') 
        except BaseException as e:
            stat.value = _FAILED
            error_traceback = traceback.format_exc()
            match = re.search(r'(File "<string>".*)', error_traceback, re.DOTALL)
            if match:
                error_traceback = match.group(1)
            elif "assert _poly" in error_traceback:
                if "TypeError: _poly() argument after *" in error_traceback:
                    error_traceback = "TypeError: Invalid output type, output must be an iterable."
                else:
                    delimiter = r'f"Input: \{inp\}\\nExpected Output: \{exp\}\\nActual Output: \{out\}"'
                    error_traceback = re.split(delimiter, error_traceback)[-1]

            error_str=str(error_traceback)[:feedback_size]
            padding = max(0, feedback_size - len(error_str))
            feedback.value = (error_str + " " * padding).encode('utf-8')
        # Needed for cleaning up.
        shutil.rmtree = rmtree
        os.rmdir = rmdir
        os.chdir = chdir


def untrusted_check(
    dataset: str,
    code: str,
    inputs: List[Any],
    entry_point: str,
    expected,
    atol,
    ref_time: List[float],
    fast_check: bool = False,
    min_time_limit: float = 0.1,
    gt_time_limit_factor: float = 2.0,
) -> Tuple[str, np.ndarray]:

    time_limits = [max(min_time_limit, gt_time_limit_factor * t) for t in ref_time]
    timeout = sum(time_limits) + 1
    if not fast_check:
        timeout += 1  # extra time for data collection

    # shared memory objects
    progress = Value("i", 0)
    stat = Value("i", _UNKNOWN)
    details = Array("b", [False for _ in range(len(inputs))])
    feedback_size = 500
    feedback = Array('c', b'\0' * feedback_size)

    p = multiprocessing.Process(
        target=unsafe_execute,
        args=(
            dataset,
            entry_point,
            code,
            inputs,
            expected,
            time_limits,
            atol,
            fast_check,
            stat,
            details,
            progress,
            feedback,
            feedback_size,
        ),
    )
    p.start()
    p.join(timeout=timeout + 1)
    if p.is_alive():
        p.terminate()
        time.sleep(0.1)
    if p.is_alive():
        p.kill()
        time.sleep(0.1)

    stat = _mapping[stat.value]
    details = details[: progress.value]
    feedback = feedback.value.decode("utf-8").strip()
    if entry_point not in code:
        feedback = f"Please rename your function to {entry_point} as there is no function named {entry_point}."

    if not stat:
        stat = TIMEOUT

    if stat == SUCCESS:
        if len(details) != len(inputs) or not all(details):
            stat = FAILED

    return stat, details, feedback


def check_correctness(
    dataset: str,
    completion_id: int,
    problem: Dict[str, Any],
    solution: str,
    expected_output: Dict[str, List],
    version="base",
    fast_check=False,
    identifier=None,
    min_time_limit: float = 0.1,
    gt_time_limit_factor: float = 2.0,
) -> Dict[str, Union[int, Optional[Result]]]:
    ret = {
        "completion_id": completion_id,
        "task_id": problem["task_id"],
        "_identifier": identifier,
    }
    
    ret["base"] = untrusted_check(
        dataset,
        solution,
        problem["base_input"],
        problem["entry_point"],
        expected=expected_output["base"],
        atol=problem["atol"],
        ref_time=expected_output["base_time"],
        fast_check=fast_check,
        min_time_limit=min_time_limit,
        gt_time_limit_factor=gt_time_limit_factor,
    )
    if version=="plus":
        ret["plus"] = untrusted_check(
            dataset,
            solution,
            problem["plus_input"],
            problem["entry_point"],
            expected=expected_output["plus"],
            atol=problem["atol"],
            ref_time=expected_output["plus_time"],
            fast_check=fast_check,
            min_time_limit=min_time_limit,
            gt_time_limit_factor=gt_time_limit_factor,
        )
    return ret

# === NexusCore/openenv\Lib\site-packages\numpy\matlib.py ===
import warnings

# 2018-05-29, PendingDeprecationWarning added to matrix.__new__
# 2020-01-23, numpy 1.19.0 PendingDeprecatonWarning
warnings.warn("Importing from numpy.matlib is deprecated since 1.19.0. "
              "The matrix subclass is not the recommended way to represent "
              "matrices or deal with linear algebra (see "
              "https://docs.scipy.org/doc/numpy/user/numpy-for-matlab-users.html). "
              "Please adjust your code to use regular ndarray. ",
              PendingDeprecationWarning, stacklevel=2)

import numpy as np

# Matlib.py contains all functions in the numpy namespace with a few
# replacements. See doc/source/reference/routines.matlib.rst for details.
# Need * as we're copying the numpy namespace.
from numpy import *  # noqa: F403
from numpy.matrixlib.defmatrix import asmatrix, matrix

__version__ = np.__version__

__all__ = ['rand', 'randn', 'repmat']
__all__ += np.__all__

def empty(shape, dtype=None, order='C'):
    """Return a new matrix of given shape and type, without initializing entries.

    Parameters
    ----------
    shape : int or tuple of int
        Shape of the empty matrix.
    dtype : data-type, optional
        Desired output data-type.
    order : {'C', 'F'}, optional
        Whether to store multi-dimensional data in row-major
        (C-style) or column-major (Fortran-style) order in
        memory.

    See Also
    --------
    numpy.empty : Equivalent array function.
    matlib.zeros : Return a matrix of zeros.
    matlib.ones : Return a matrix of ones.

    Notes
    -----
    Unlike other matrix creation functions (e.g. `matlib.zeros`,
    `matlib.ones`), `matlib.empty` does not initialize the values of the
    matrix, and may therefore be marginally faster. However, the values
    stored in the newly allocated matrix are arbitrary. For reproducible
    behavior, be sure to set each element of the matrix before reading.

    Examples
    --------
    >>> import numpy.matlib
    >>> np.matlib.empty((2, 2))    # filled with random data
    matrix([[  6.76425276e-320,   9.79033856e-307], # random
            [  7.39337286e-309,   3.22135945e-309]])
    >>> np.matlib.empty((2, 2), dtype=int)
    matrix([[ 6600475,        0], # random
            [ 6586976, 22740995]])

    """
    return ndarray.__new__(matrix, shape, dtype, order=order)

def ones(shape, dtype=None, order='C'):
    """
    Matrix of ones.

    Return a matrix of given shape and type, filled with ones.

    Parameters
    ----------
    shape : {sequence of ints, int}
        Shape of the matrix
    dtype : data-type, optional
        The desired data-type for the matrix, default is np.float64.
    order : {'C', 'F'}, optional
        Whether to store matrix in C- or Fortran-contiguous order,
        default is 'C'.

    Returns
    -------
    out : matrix
        Matrix of ones of given shape, dtype, and order.

    See Also
    --------
    ones : Array of ones.
    matlib.zeros : Zero matrix.

    Notes
    -----
    If `shape` has length one i.e. ``(N,)``, or is a scalar ``N``,
    `out` becomes a single row matrix of shape ``(1,N)``.

    Examples
    --------
    >>> np.matlib.ones((2,3))
    matrix([[1.,  1.,  1.],
            [1.,  1.,  1.]])

    >>> np.matlib.ones(2)
    matrix([[1.,  1.]])

    """
    a = ndarray.__new__(matrix, shape, dtype, order=order)
    a.fill(1)
    return a

def zeros(shape, dtype=None, order='C'):
    """
    Return a matrix of given shape and type, filled with zeros.

    Parameters
    ----------
    shape : int or sequence of ints
        Shape of the matrix
    dtype : data-type, optional
        The desired data-type for the matrix, default is float.
    order : {'C', 'F'}, optional
        Whether to store the result in C- or Fortran-contiguous order,
        default is 'C'.

    Returns
    -------
    out : matrix
        Zero matrix of given shape, dtype, and order.

    See Also
    --------
    numpy.zeros : Equivalent array function.
    matlib.ones : Return a matrix of ones.

    Notes
    -----
    If `shape` has length one i.e. ``(N,)``, or is a scalar ``N``,
    `out` becomes a single row matrix of shape ``(1,N)``.

    Examples
    --------
    >>> import numpy.matlib
    >>> np.matlib.zeros((2, 3))
    matrix([[0.,  0.,  0.],
            [0.,  0.,  0.]])

    >>> np.matlib.zeros(2)
    matrix([[0.,  0.]])

    """
    a = ndarray.__new__(matrix, shape, dtype, order=order)
    a.fill(0)
    return a

def identity(n, dtype=None):
    """
    Returns the square identity matrix of given size.

    Parameters
    ----------
    n : int
        Size of the returned identity matrix.
    dtype : data-type, optional
        Data-type of the output. Defaults to ``float``.

    Returns
    -------
    out : matrix
        `n` x `n` matrix with its main diagonal set to one,
        and all other elements zero.

    See Also
    --------
    numpy.identity : Equivalent array function.
    matlib.eye : More general matrix identity function.

    Examples
    --------
    >>> import numpy.matlib
    >>> np.matlib.identity(3, dtype=int)
    matrix([[1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]])

    """
    a = array([1] + n * [0], dtype=dtype)
    b = empty((n, n), dtype=dtype)
    b.flat = a
    return b

def eye(n, M=None, k=0, dtype=float, order='C'):
    """
    Return a matrix with ones on the diagonal and zeros elsewhere.

    Parameters
    ----------
    n : int
        Number of rows in the output.
    M : int, optional
        Number of columns in the output, defaults to `n`.
    k : int, optional
        Index of the diagonal: 0 refers to the main diagonal,
        a positive value refers to an upper diagonal,
        and a negative value to a lower diagonal.
    dtype : dtype, optional
        Data-type of the returned matrix.
    order : {'C', 'F'}, optional
        Whether the output should be stored in row-major (C-style) or
        column-major (Fortran-style) order in memory.

    Returns
    -------
    I : matrix
        A `n` x `M` matrix where all elements are equal to zero,
        except for the `k`-th diagonal, whose values are equal to one.

    See Also
    --------
    numpy.eye : Equivalent array function.
    identity : Square identity matrix.

    Examples
    --------
    >>> import numpy.matlib
    >>> np.matlib.eye(3, k=1, dtype=float)
    matrix([[0.,  1.,  0.],
            [0.,  0.,  1.],
            [0.,  0.,  0.]])

    """
    return asmatrix(np.eye(n, M=M, k=k, dtype=dtype, order=order))

def rand(*args):
    """
    Return a matrix of random values with given shape.

    Create a matrix of the given shape and propagate it with
    random samples from a uniform distribution over ``[0, 1)``.

    Parameters
    ----------
    \\*args : Arguments
        Shape of the output.
        If given as N integers, each integer specifies the size of one
        dimension.
        If given as a tuple, this tuple gives the complete shape.

    Returns
    -------
    out : ndarray
        The matrix of random values with shape given by `\\*args`.

    See Also
    --------
    randn, numpy.random.RandomState.rand

    Examples
    --------
    >>> np.random.seed(123)
    >>> import numpy.matlib
    >>> np.matlib.rand(2, 3)
    matrix([[0.69646919, 0.28613933, 0.22685145],
            [0.55131477, 0.71946897, 0.42310646]])
    >>> np.matlib.rand((2, 3))
    matrix([[0.9807642 , 0.68482974, 0.4809319 ],
            [0.39211752, 0.34317802, 0.72904971]])

    If the first argument is a tuple, other arguments are ignored:

    >>> np.matlib.rand((2, 3), 4)
    matrix([[0.43857224, 0.0596779 , 0.39804426],
            [0.73799541, 0.18249173, 0.17545176]])

    """
    if isinstance(args[0], tuple):
        args = args[0]
    return asmatrix(np.random.rand(*args))

def randn(*args):
    """
    Return a random matrix with data from the "standard normal" distribution.

    `randn` generates a matrix filled with random floats sampled from a
    univariate "normal" (Gaussian) distribution of mean 0 and variance 1.

    Parameters
    ----------
    \\*args : Arguments
        Shape of the output.
        If given as N integers, each integer specifies the size of one
        dimension. If given as a tuple, this tuple gives the complete shape.

    Returns
    -------
    Z : matrix of floats
        A matrix of floating-point samples drawn from the standard normal
        distribution.

    See Also
    --------
    rand, numpy.random.RandomState.randn

    Notes
    -----
    For random samples from the normal distribution with mean ``mu`` and
    standard deviation ``sigma``, use::

        sigma * np.matlib.randn(...) + mu

    Examples
    --------
    >>> np.random.seed(123)
    >>> import numpy.matlib
    >>> np.matlib.randn(1)
    matrix([[-1.0856306]])
    >>> np.matlib.randn(1, 2, 3)
    matrix([[ 0.99734545,  0.2829785 , -1.50629471],
            [-0.57860025,  1.65143654, -2.42667924]])

    Two-by-four matrix of samples from the normal distribution with
    mean 3 and standard deviation 2.5:

    >>> 2.5 * np.matlib.randn((2, 4)) + 3
    matrix([[1.92771843, 6.16484065, 0.83314899, 1.30278462],
            [2.76322758, 6.72847407, 1.40274501, 1.8900451 ]])

    """
    if isinstance(args[0], tuple):
        args = args[0]
    return asmatrix(np.random.randn(*args))

def repmat(a, m, n):
    """
    Repeat a 0-D to 2-D array or matrix MxN times.

    Parameters
    ----------
    a : array_like
        The array or matrix to be repeated.
    m, n : int
        The number of times `a` is repeated along the first and second axes.

    Returns
    -------
    out : ndarray
        The result of repeating `a`.

    Examples
    --------
    >>> import numpy.matlib
    >>> a0 = np.array(1)
    >>> np.matlib.repmat(a0, 2, 3)
    array([[1, 1, 1],
           [1, 1, 1]])

    >>> a1 = np.arange(4)
    >>> np.matlib.repmat(a1, 2, 2)
    array([[0, 1, 2, 3, 0, 1, 2, 3],
           [0, 1, 2, 3, 0, 1, 2, 3]])

    >>> a2 = np.asmatrix(np.arange(6).reshape(2, 3))
    >>> np.matlib.repmat(a2, 2, 3)
    matrix([[0, 1, 2, 0, 1, 2, 0, 1, 2],
            [3, 4, 5, 3, 4, 5, 3, 4, 5],
            [0, 1, 2, 0, 1, 2, 0, 1, 2],
            [3, 4, 5, 3, 4, 5, 3, 4, 5]])

    """
    a = asanyarray(a)
    ndim = a.ndim
    if ndim == 0:
        origrows, origcols = (1, 1)
    elif ndim == 1:
        origrows, origcols = (1, a.shape[0])
    else:
        origrows, origcols = a.shape
    rows = origrows * m
    cols = origcols * n
    c = a.reshape(1, a.size).repeat(m, 0).reshape(rows, origcols).repeat(n, 0)
    return c.reshape(rows, cols)

# === NexusCore/openenv\Lib\site-packages\google\auth\external_account_authorized_user.py ===
# Copyright 2022 Google LLC
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

"""External Account Authorized User Credentials.
This module provides credentials based on OAuth 2.0 access and refresh tokens.
These credentials usually access resources on behalf of a user (resource
owner).

Specifically, these are sourced using external identities via Workforce Identity Federation.

Obtaining the initial access and refresh token can be done through the Google Cloud CLI.

Example credential:
{
  "type": "external_account_authorized_user",
  "audience": "//iam.googleapis.com/locations/global/workforcePools/$WORKFORCE_POOL_ID/providers/$PROVIDER_ID",
  "refresh_token": "refreshToken",
  "token_url": "https://sts.googleapis.com/v1/oauth/token",
  "token_info_url": "https://sts.googleapis.com/v1/instrospect",
  "client_id": "clientId",
  "client_secret": "clientSecret"
}
"""

import datetime
import io
import json

from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.oauth2 import sts
from google.oauth2 import utils

_EXTERNAL_ACCOUNT_AUTHORIZED_USER_JSON_TYPE = "external_account_authorized_user"


class Credentials(
    credentials.CredentialsWithQuotaProject,
    credentials.ReadOnlyScoped,
    credentials.CredentialsWithTokenUri,
):
    """Credentials for External Account Authorized Users.

    This is used to instantiate Credentials for exchanging refresh tokens from
    authorized users for Google access token and authorizing requests to Google
    APIs.

    The credentials are considered immutable. If you want to modify the
    quota project, use `with_quota_project` and if you want to modify the token
    uri, use `with_token_uri`.
    """

    def __init__(
        self,
        token=None,
        expiry=None,
        refresh_token=None,
        audience=None,
        client_id=None,
        client_secret=None,
        token_url=None,
        token_info_url=None,
        revoke_url=None,
        scopes=None,
        quota_project_id=None,
        universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
    ):
        """Instantiates a external account authorized user credentials object.

        Args:
        token (str): The OAuth 2.0 access token. Can be None if refresh information
            is provided.
        expiry (datetime.datetime): The optional expiration datetime of the OAuth 2.0 access
            token.
        refresh_token (str): The optional OAuth 2.0 refresh token. If specified,
            credentials can be refreshed.
        audience (str): The optional STS audience which contains the resource name for the workforce
            pool and the provider identifier in that pool.
        client_id (str): The OAuth 2.0 client ID. Must be specified for refresh, can be left as
            None if the token can not be refreshed.
        client_secret (str): The OAuth 2.0 client secret. Must be specified for refresh, can be
            left as None if the token can not be refreshed.
        token_url (str): The optional STS token exchange endpoint for refresh. Must be specified for
            refresh, can be left as None if the token can not be refreshed.
        token_info_url (str): The optional STS endpoint URL for token introspection.
        revoke_url (str): The optional STS endpoint URL for revoking tokens.
        quota_project_id (str): The optional project ID used for quota and billing.
            This project may be different from the project used to
            create the credentials.
        universe_domain (Optional[str]): The universe domain. The default value
            is googleapis.com.

        Returns:
            google.auth.external_account_authorized_user.Credentials: The
                constructed credentials.
        """
        super(Credentials, self).__init__()

        self.token = token
        self.expiry = expiry
        self._audience = audience
        self._refresh_token = refresh_token
        self._token_url = token_url
        self._token_info_url = token_info_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._revoke_url = revoke_url
        self._quota_project_id = quota_project_id
        self._scopes = scopes
        self._universe_domain = universe_domain or credentials.DEFAULT_UNIVERSE_DOMAIN
        self._cred_file_path = None

        if not self.valid and not self.can_refresh:
            raise exceptions.InvalidOperation(
                "Token should be created with fields to make it valid (`token` and "
                "`expiry`), or fields to allow it to refresh (`refresh_token`, "
                "`token_url`, `client_id`, `client_secret`)."
            )

        self._client_auth = None
        if self._client_id:
            self._client_auth = utils.ClientAuthentication(
                utils.ClientAuthType.basic, self._client_id, self._client_secret
            )
        self._sts_client = sts.Client(self._token_url, self._client_auth)

    @property
    def info(self):
        """Generates the serializable dictionary representation of the current
        credentials.

        Returns:
            Mapping: The dictionary representation of the credentials. This is the
                reverse of the "from_info" method defined in this class. It is
                useful for serializing the current credentials so it can deserialized
                later.
        """
        config_info = self.constructor_args()
        config_info.update(type=_EXTERNAL_ACCOUNT_AUTHORIZED_USER_JSON_TYPE)
        if config_info["expiry"]:
            config_info["expiry"] = config_info["expiry"].isoformat() + "Z"

        return {key: value for key, value in config_info.items() if value is not None}

    def constructor_args(self):
        return {
            "audience": self._audience,
            "refresh_token": self._refresh_token,
            "token_url": self._token_url,
            "token_info_url": self._token_info_url,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "token": self.token,
            "expiry": self.expiry,
            "revoke_url": self._revoke_url,
            "scopes": self._scopes,
            "quota_project_id": self._quota_project_id,
            "universe_domain": self._universe_domain,
        }

    @property
    def scopes(self):
        """Optional[str]: The OAuth 2.0 permission scopes."""
        return self._scopes

    @property
    def requires_scopes(self):
        """ False: OAuth 2.0 credentials have their scopes set when
        the initial token is requested and can not be changed."""
        return False

    @property
    def client_id(self):
        """Optional[str]: The OAuth 2.0 client ID."""
        return self._client_id

    @property
    def client_secret(self):
        """Optional[str]: The OAuth 2.0 client secret."""
        return self._client_secret

    @property
    def audience(self):
        """Optional[str]: The STS audience which contains the resource name for the
            workforce pool and the provider identifier in that pool."""
        return self._audience

    @property
    def refresh_token(self):
        """Optional[str]: The OAuth 2.0 refresh token."""
        return self._refresh_token

    @property
    def token_url(self):
        """Optional[str]: The STS token exchange endpoint for refresh."""
        return self._token_url

    @property
    def token_info_url(self):
        """Optional[str]: The STS endpoint for token info."""
        return self._token_info_url

    @property
    def revoke_url(self):
        """Optional[str]: The STS endpoint for token revocation."""
        return self._revoke_url

    @property
    def is_user(self):
        """ True: This credential always represents a user."""
        return True

    @property
    def can_refresh(self):
        return all(
            (self._refresh_token, self._token_url, self._client_id, self._client_secret)
        )

    def get_project_id(self, request=None):
        """Retrieves the project ID corresponding to the workload identity or workforce pool.
        For workforce pool credentials, it returns the project ID corresponding to
        the workforce_pool_user_project.

        When not determinable, None is returned.

        Args:
            request (google.auth.transport.requests.Request): Request object.
                Unused here, but passed from _default.default().

        Return:
          str: project ID is not determinable for this credential type so it returns None
        """

        return None

    def to_json(self, strip=None):
        """Utility function that creates a JSON representation of this
        credential.
        Args:
            strip (Sequence[str]): Optional list of members to exclude from the
                                   generated JSON.
        Returns:
            str: A JSON representation of this instance. When converted into
            a dictionary, it can be passed to from_info()
            to create a new instance.
        """
        strip = strip if strip else []
        return json.dumps({k: v for (k, v) in self.info.items() if k not in strip})

    def refresh(self, request):
        """Refreshes the access token.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If the credentials could
                not be refreshed.
        """
        if not self.can_refresh:
            raise exceptions.RefreshError(
                "The credentials do not contain the necessary fields need to "
                "refresh the access token. You must specify refresh_token, "
                "token_url, client_id, and client_secret."
            )

        now = _helpers.utcnow()
        response_data = self._make_sts_request(request)

        self.token = response_data.get("access_token")

        lifetime = datetime.timedelta(seconds=response_data.get("expires_in"))
        self.expiry = now + lifetime

        if "refresh_token" in response_data:
            self._refresh_token = response_data["refresh_token"]

    def _make_sts_request(self, request):
        return self._sts_client.refresh_token(request, self._refresh_token)

    @_helpers.copy_docstring(credentials.Credentials)
    def get_cred_info(self):
        if self._cred_file_path:
            return {
                "credential_source": self._cred_file_path,
                "credential_type": "external account authorized user credentials",
            }
        return None

    def _make_copy(self):
        kwargs = self.constructor_args()
        cred = self.__class__(**kwargs)
        cred._cred_file_path = self._cred_file_path
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        cred = self._make_copy()
        cred._quota_project_id = quota_project_id
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithTokenUri)
    def with_token_uri(self, token_uri):
        cred = self._make_copy()
        cred._token_url = token_uri
        return cred

    @_helpers.copy_docstring(credentials.CredentialsWithUniverseDomain)
    def with_universe_domain(self, universe_domain):
        cred = self._make_copy()
        cred._universe_domain = universe_domain
        return cred

    @classmethod
    def from_info(cls, info, **kwargs):
        """Creates a Credentials instance from parsed external account info.

        Args:
            info (Mapping[str, str]): The external account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.external_account_authorized_user.Credentials: The
                constructed credentials.

        Raises:
            ValueError: For invalid parameters.
        """
        expiry = info.get("expiry")
        if expiry:
            expiry = datetime.datetime.strptime(
                expiry.rstrip("Z").split(".")[0], "%Y-%m-%dT%H:%M:%S"
            )
        return cls(
            audience=info.get("audience"),
            refresh_token=info.get("refresh_token"),
            token_url=info.get("token_url"),
            token_info_url=info.get("token_info_url"),
            client_id=info.get("client_id"),
            client_secret=info.get("client_secret"),
            token=info.get("token"),
            expiry=expiry,
            revoke_url=info.get("revoke_url"),
            quota_project_id=info.get("quota_project_id"),
            scopes=info.get("scopes"),
            universe_domain=info.get(
                "universe_domain", credentials.DEFAULT_UNIVERSE_DOMAIN
            ),
            **kwargs
        )

    @classmethod
    def from_file(cls, filename, **kwargs):
        """Creates a Credentials instance from an external account json file.

        Args:
            filename (str): The path to the external account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.external_account_authorized_user.Credentials: The
                constructed credentials.
        """
        with io.open(filename, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            return cls.from_info(data, **kwargs)

# === NexusCore/openenv\Lib\site-packages\httpx\_exceptions.py ===
"""
Our exception hierarchy:

* HTTPError
  x RequestError
    + TransportError
      - TimeoutException
        · ConnectTimeout
        · ReadTimeout
        · WriteTimeout
        · PoolTimeout
      - NetworkError
        · ConnectError
        · ReadError
        · WriteError
        · CloseError
      - ProtocolError
        · LocalProtocolError
        · RemoteProtocolError
      - ProxyError
      - UnsupportedProtocol
    + DecodingError
    + TooManyRedirects
  x HTTPStatusError
* InvalidURL
* CookieConflict
* StreamError
  x StreamConsumed
  x StreamClosed
  x ResponseNotRead
  x RequestNotRead
"""

from __future__ import annotations

import contextlib
import typing

if typing.TYPE_CHECKING:
    from ._models import Request, Response  # pragma: no cover

__all__ = [
    "CloseError",
    "ConnectError",
    "ConnectTimeout",
    "CookieConflict",
    "DecodingError",
    "HTTPError",
    "HTTPStatusError",
    "InvalidURL",
    "LocalProtocolError",
    "NetworkError",
    "PoolTimeout",
    "ProtocolError",
    "ProxyError",
    "ReadError",
    "ReadTimeout",
    "RemoteProtocolError",
    "RequestError",
    "RequestNotRead",
    "ResponseNotRead",
    "StreamClosed",
    "StreamConsumed",
    "StreamError",
    "TimeoutException",
    "TooManyRedirects",
    "TransportError",
    "UnsupportedProtocol",
    "WriteError",
    "WriteTimeout",
]


class HTTPError(Exception):
    """
    Base class for `RequestError` and `HTTPStatusError`.

    Useful for `try...except` blocks when issuing a request,
    and then calling `.raise_for_status()`.

    For example:

    ```
    try:
        response = httpx.get("https://www.example.com")
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"HTTP Exception for {exc.request.url} - {exc}")
    ```
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self._request: Request | None = None

    @property
    def request(self) -> Request:
        if self._request is None:
            raise RuntimeError("The .request property has not been set.")
        return self._request

    @request.setter
    def request(self, request: Request) -> None:
        self._request = request


class RequestError(HTTPError):
    """
    Base class for all exceptions that may occur when issuing a `.request()`.
    """

    def __init__(self, message: str, *, request: Request | None = None) -> None:
        super().__init__(message)
        # At the point an exception is raised we won't typically have a request
        # instance to associate it with.
        #
        # The 'request_context' context manager is used within the Client and
        # Response methods in order to ensure that any raised exceptions
        # have a `.request` property set on them.
        self._request = request


class TransportError(RequestError):
    """
    Base class for all exceptions that occur at the level of the Transport API.
    """


# Timeout exceptions...


class TimeoutException(TransportError):
    """
    The base class for timeout errors.

    An operation has timed out.
    """


class ConnectTimeout(TimeoutException):
    """
    Timed out while connecting to the host.
    """


class ReadTimeout(TimeoutException):
    """
    Timed out while receiving data from the host.
    """


class WriteTimeout(TimeoutException):
    """
    Timed out while sending data to the host.
    """


class PoolTimeout(TimeoutException):
    """
    Timed out waiting to acquire a connection from the pool.
    """


# Core networking exceptions...


class NetworkError(TransportError):
    """
    The base class for network-related errors.

    An error occurred while interacting with the network.
    """


class ReadError(NetworkError):
    """
    Failed to receive data from the network.
    """


class WriteError(NetworkError):
    """
    Failed to send data through the network.
    """


class ConnectError(NetworkError):
    """
    Failed to establish a connection.
    """


class CloseError(NetworkError):
    """
    Failed to close a connection.
    """


# Other transport exceptions...


class ProxyError(TransportError):
    """
    An error occurred while establishing a proxy connection.
    """


class UnsupportedProtocol(TransportError):
    """
    Attempted to make a request to an unsupported protocol.

    For example issuing a request to `ftp://www.example.com`.
    """


class ProtocolError(TransportError):
    """
    The protocol was violated.
    """


class LocalProtocolError(ProtocolError):
    """
    A protocol was violated by the client.

    For example if the user instantiated a `Request` instance explicitly,
    failed to include the mandatory `Host:` header, and then issued it directly
    using `client.send()`.
    """


class RemoteProtocolError(ProtocolError):
    """
    The protocol was violated by the server.

    For example, returning malformed HTTP.
    """


# Other request exceptions...


class DecodingError(RequestError):
    """
    Decoding of the response failed, due to a malformed encoding.
    """


class TooManyRedirects(RequestError):
    """
    Too many redirects.
    """


# Client errors


class HTTPStatusError(HTTPError):
    """
    The response had an error HTTP status of 4xx or 5xx.

    May be raised when calling `response.raise_for_status()`
    """

    def __init__(self, message: str, *, request: Request, response: Response) -> None:
        super().__init__(message)
        self.request = request
        self.response = response


class InvalidURL(Exception):
    """
    URL is improperly formed or cannot be parsed.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CookieConflict(Exception):
    """
    Attempted to lookup a cookie by name, but multiple cookies existed.

    Can occur when calling `response.cookies.get(...)`.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# Stream exceptions...

# These may occur as the result of a programming error, by accessing
# the request/response stream in an invalid manner.


class StreamError(RuntimeError):
    """
    The base class for stream exceptions.

    The developer made an error in accessing the request stream in
    an invalid way.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class StreamConsumed(StreamError):
    """
    Attempted to read or stream content, but the content has already
    been streamed.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream some content, but the content has "
            "already been streamed. For requests, this could be due to passing "
            "a generator as request content, and then receiving a redirect "
            "response or a secondary request as part of an authentication flow."
            "For responses, this could be due to attempting to stream the response "
            "content more than once."
        )
        super().__init__(message)


class StreamClosed(StreamError):
    """
    Attempted to read or stream response content, but the request has been
    closed.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to read or stream content, but the stream has " "been closed."
        )
        super().__init__(message)


class ResponseNotRead(StreamError):
    """
    Attempted to access streaming response content, without having called `read()`.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to access streaming response content,"
            " without having called `read()`."
        )
        super().__init__(message)


class RequestNotRead(StreamError):
    """
    Attempted to access streaming request content, without having called `read()`.
    """

    def __init__(self) -> None:
        message = (
            "Attempted to access streaming request content,"
            " without having called `read()`."
        )
        super().__init__(message)


@contextlib.contextmanager
def request_context(
    request: Request | None = None,
) -> typing.Iterator[None]:
    """
    A context manager that can be used to attach the given request context
    to any `RequestError` exceptions that are raised within the block.
    """
    try:
        yield
    except RequestError as exc:
        if request is not None:
            exc.request = request
        raise exc

# === NexusCore/openenv\Lib\site-packages\joblib\func_inspect.py ===
"""
My own variation on function-specific inspect-like features.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import collections
import inspect
import os
import re
import warnings
from itertools import islice
from tokenize import open as open_py_source

from .logger import pformat

full_argspec_fields = (
    "args varargs varkw defaults kwonlyargs kwonlydefaults annotations"
)
full_argspec_type = collections.namedtuple("FullArgSpec", full_argspec_fields)


def get_func_code(func):
    """Attempts to retrieve a reliable function code hash.

    The reason we don't use inspect.getsource is that it caches the
    source, whereas we want this to be modified on the fly when the
    function is modified.

    Returns
    -------
    func_code: string
        The function code
    source_file: string
        The path to the file in which the function is defined.
    first_line: int
        The first line of the code in the source file.

    Notes
    ------
    This function does a bit more magic than inspect, and is thus
    more robust.
    """
    source_file = None
    try:
        code = func.__code__
        source_file = code.co_filename
        if not os.path.exists(source_file):
            # Use inspect for lambda functions and functions defined in an
            # interactive shell, or in doctests
            source_code = "".join(inspect.getsourcelines(func)[0])
            line_no = 1
            if source_file.startswith("<doctest "):
                source_file, line_no = re.match(
                    r"\<doctest (.*\.rst)\[(.*)\]\>", source_file
                ).groups()
                line_no = int(line_no)
                source_file = "<doctest %s>" % source_file
            return source_code, source_file, line_no
        # Try to retrieve the source code.
        with open_py_source(source_file) as source_file_obj:
            first_line = code.co_firstlineno
            # All the lines after the function definition:
            source_lines = list(islice(source_file_obj, first_line - 1, None))
        return "".join(inspect.getblock(source_lines)), source_file, first_line
    except:  # noqa: E722
        # If the source code fails, we use the hash. This is fragile and
        # might change from one session to another.
        if hasattr(func, "__code__"):
            # Python 3.X
            return str(func.__code__.__hash__()), source_file, -1
        else:
            # Weird objects like numpy ufunc don't have __code__
            # This is fragile, as quite often the id of the object is
            # in the repr, so it might not persist across sessions,
            # however it will work for ufuncs.
            return repr(func), source_file, -1


def _clean_win_chars(string):
    """Windows cannot encode some characters in filename."""
    import urllib

    if hasattr(urllib, "quote"):
        quote = urllib.quote
    else:
        # In Python 3, quote is elsewhere
        import urllib.parse

        quote = urllib.parse.quote
    for char in ("<", ">", "!", ":", "\\"):
        string = string.replace(char, quote(char))
    return string


def get_func_name(func, resolv_alias=True, win_characters=True):
    """Return the function import path (as a list of module names), and
    a name for the function.

    Parameters
    ----------
    func: callable
        The func to inspect
    resolv_alias: boolean, optional
        If true, possible local aliases are indicated.
    win_characters: boolean, optional
        If true, substitute special characters using urllib.quote
        This is useful in Windows, as it cannot encode some filenames
    """
    if hasattr(func, "__module__"):
        module = func.__module__
    else:
        try:
            module = inspect.getmodule(func)
        except TypeError:
            if hasattr(func, "__class__"):
                module = func.__class__.__module__
            else:
                module = "unknown"
    if module is None:
        # Happens in doctests, eg
        module = ""
    if module == "__main__":
        try:
            filename = os.path.abspath(inspect.getsourcefile(func))
        except:  # noqa: E722
            filename = None
        if filename is not None:
            # mangling of full path to filename
            parts = filename.split(os.sep)
            if parts[-1].startswith("<ipython-input"):
                # We're in a IPython (or notebook) session. parts[-1] comes
                # from func.__code__.co_filename and is of the form
                # <ipython-input-N-XYZ>, where:
                # - N is the cell number where the function was defined
                # - XYZ is a hash representing the function's code (and name).
                #   It will be consistent across sessions and kernel restarts,
                #   and will change if the function's code/name changes
                # We remove N so that cache is properly hit if the cell where
                # the func is defined is re-exectuted.
                # The XYZ hash should avoid collisions between functions with
                # the same name, both within the same notebook but also across
                # notebooks
                split = parts[-1].split("-")
                parts[-1] = "-".join(split[:2] + split[3:])
            elif len(parts) > 2 and parts[-2].startswith("ipykernel_"):
                # In a notebook session (ipykernel). Filename seems to be 'xyz'
                # of above. parts[-2] has the structure ipykernel_XXXXXX where
                # XXXXXX is a six-digit number identifying the current run (?).
                # If we split it off, the function again has the same
                # identifier across runs.
                parts[-2] = "ipykernel"
            filename = "-".join(parts)
            if filename.endswith(".py"):
                filename = filename[:-3]
            module = module + "-" + filename
    module = module.split(".")
    if hasattr(func, "func_name"):
        name = func.func_name
    elif hasattr(func, "__name__"):
        name = func.__name__
    else:
        name = "unknown"
    # Hack to detect functions not defined at the module-level
    if resolv_alias:
        # TODO: Maybe add a warning here?
        if hasattr(func, "func_globals") and name in func.func_globals:
            if func.func_globals[name] is not func:
                name = "%s-alias" % name
    if hasattr(func, "__qualname__") and func.__qualname__ != name:
        # Extend the module name in case of nested functions to avoid
        # (module, name) collisions
        module.extend(func.__qualname__.split(".")[:-1])
    if inspect.ismethod(func):
        # We need to add the name of the class
        if hasattr(func, "im_class"):
            klass = func.im_class
            module.append(klass.__name__)
    if os.name == "nt" and win_characters:
        # Windows can't encode certain characters in filenames
        name = _clean_win_chars(name)
        module = [_clean_win_chars(s) for s in module]
    return module, name


def _signature_str(function_name, arg_sig):
    """Helper function to output a function signature"""
    return "{}{}".format(function_name, arg_sig)


def _function_called_str(function_name, args, kwargs):
    """Helper function to output a function call"""
    template_str = "{0}({1}, {2})"

    args_str = repr(args)[1:-1]
    kwargs_str = ", ".join("%s=%s" % (k, v) for k, v in kwargs.items())
    return template_str.format(function_name, args_str, kwargs_str)


def filter_args(func, ignore_lst, args=(), kwargs=dict()):
    """Filters the given args and kwargs using a list of arguments to
    ignore, and a function specification.

    Parameters
    ----------
    func: callable
        Function giving the argument specification
    ignore_lst: list of strings
        List of arguments to ignore (either a name of an argument
        in the function spec, or '*', or '**')
    *args: list
        Positional arguments passed to the function.
    **kwargs: dict
        Keyword arguments passed to the function

    Returns
    -------
    filtered_args: list
        List of filtered positional and keyword arguments.
    """
    args = list(args)
    if isinstance(ignore_lst, str):
        # Catch a common mistake
        raise ValueError(
            "ignore_lst must be a list of parameters to ignore "
            "%s (type %s) was given" % (ignore_lst, type(ignore_lst))
        )
    # Special case for functools.partial objects
    if not inspect.ismethod(func) and not inspect.isfunction(func):
        if ignore_lst:
            warnings.warn(
                "Cannot inspect object %s, ignore list will not work." % func,
                stacklevel=2,
            )
        return {"*": args, "**": kwargs}
    arg_sig = inspect.signature(func)
    arg_names = []
    arg_defaults = []
    arg_kwonlyargs = []
    arg_varargs = None
    arg_varkw = None
    for param in arg_sig.parameters.values():
        if param.kind is param.POSITIONAL_OR_KEYWORD:
            arg_names.append(param.name)
        elif param.kind is param.KEYWORD_ONLY:
            arg_names.append(param.name)
            arg_kwonlyargs.append(param.name)
        elif param.kind is param.VAR_POSITIONAL:
            arg_varargs = param.name
        elif param.kind is param.VAR_KEYWORD:
            arg_varkw = param.name
        if param.default is not param.empty:
            arg_defaults.append(param.default)
    if inspect.ismethod(func):
        # First argument is 'self', it has been removed by Python
        # we need to add it back:
        args = [
            func.__self__,
        ] + args
        # func is an instance method, inspect.signature(func) does not
        # include self, we need to fetch it from the class method, i.e
        # func.__func__
        class_method_sig = inspect.signature(func.__func__)
        self_name = next(iter(class_method_sig.parameters))
        arg_names = [self_name] + arg_names
    # XXX: Maybe I need an inspect.isbuiltin to detect C-level methods, such
    # as on ndarrays.

    _, name = get_func_name(func, resolv_alias=False)
    arg_dict = dict()
    arg_position = -1
    for arg_position, arg_name in enumerate(arg_names):
        if arg_position < len(args):
            # Positional argument or keyword argument given as positional
            if arg_name not in arg_kwonlyargs:
                arg_dict[arg_name] = args[arg_position]
            else:
                raise ValueError(
                    "Keyword-only parameter '%s' was passed as "
                    "positional parameter for %s:\n"
                    "     %s was called."
                    % (
                        arg_name,
                        _signature_str(name, arg_sig),
                        _function_called_str(name, args, kwargs),
                    )
                )

        else:
            position = arg_position - len(arg_names)
            if arg_name in kwargs:
                arg_dict[arg_name] = kwargs[arg_name]
            else:
                try:
                    arg_dict[arg_name] = arg_defaults[position]
                except (IndexError, KeyError) as e:
                    # Missing argument
                    raise ValueError(
                        "Wrong number of arguments for %s:\n"
                        "     %s was called."
                        % (
                            _signature_str(name, arg_sig),
                            _function_called_str(name, args, kwargs),
                        )
                    ) from e

    varkwargs = dict()
    for arg_name, arg_value in sorted(kwargs.items()):
        if arg_name in arg_dict:
            arg_dict[arg_name] = arg_value
        elif arg_varkw is not None:
            varkwargs[arg_name] = arg_value
        else:
            raise TypeError(
                "Ignore list for %s() contains an unexpected "
                "keyword argument '%s'" % (name, arg_name)
            )

    if arg_varkw is not None:
        arg_dict["**"] = varkwargs
    if arg_varargs is not None:
        varargs = args[arg_position + 1 :]
        arg_dict["*"] = varargs

    # Now remove the arguments to be ignored
    for item in ignore_lst:
        if item in arg_dict:
            arg_dict.pop(item)
        else:
            raise ValueError(
                "Ignore list: argument '%s' is not defined for "
                "function %s" % (item, _signature_str(name, arg_sig))
            )
    # XXX: Return a sorted list of pairs?
    return arg_dict


def _format_arg(arg):
    formatted_arg = pformat(arg, indent=2)
    if len(formatted_arg) > 1500:
        formatted_arg = "%s..." % formatted_arg[:700]
    return formatted_arg


def format_signature(func, *args, **kwargs):
    # XXX: Should this use inspect.formatargvalues/formatargspec?
    module, name = get_func_name(func)
    module = [m for m in module if m]
    if module:
        module.append(name)
        module_path = ".".join(module)
    else:
        module_path = name
    arg_str = list()
    previous_length = 0
    for arg in args:
        formatted_arg = _format_arg(arg)
        if previous_length > 80:
            formatted_arg = "\n%s" % formatted_arg
        previous_length = len(formatted_arg)
        arg_str.append(formatted_arg)
    arg_str.extend(["%s=%s" % (v, _format_arg(i)) for v, i in kwargs.items()])
    arg_str = ", ".join(arg_str)

    signature = "%s(%s)" % (name, arg_str)
    return module_path, signature


def format_call(func, args, kwargs, object_name="Memory"):
    """Returns a nicely formatted statement displaying the function
    call with the given arguments.
    """
    path, signature = format_signature(func, *args, **kwargs)
    msg = "%s\n[%s] Calling %s...\n%s" % (80 * "_", object_name, path, signature)
    return msg
    # XXX: Not using logging framework
    # self.debug(msg)

# === NexusCore/openenv\Lib\site-packages\google\auth\compute_engine\_metadata.py ===
# Copyright 2016 Google LLC
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

"""Provides helper methods for talking to the Compute Engine metadata server.

See https://cloud.google.com/compute/docs/metadata for more details.
"""

import datetime
import http.client as http_client
import json
import logging
import os
from urllib.parse import urljoin

from google.auth import _helpers
from google.auth import environment_vars
from google.auth import exceptions
from google.auth import metrics
from google.auth import transport
from google.auth._exponential_backoff import ExponentialBackoff

_LOGGER = logging.getLogger(__name__)

# Environment variable GCE_METADATA_HOST is originally named
# GCE_METADATA_ROOT. For compatibility reasons, here it checks
# the new variable first; if not set, the system falls back
# to the old variable.
_GCE_METADATA_HOST = os.getenv(environment_vars.GCE_METADATA_HOST, None)
if not _GCE_METADATA_HOST:
    _GCE_METADATA_HOST = os.getenv(
        environment_vars.GCE_METADATA_ROOT, "metadata.google.internal"
    )
_METADATA_ROOT = "http://{}/computeMetadata/v1/".format(_GCE_METADATA_HOST)

# This is used to ping the metadata server, it avoids the cost of a DNS
# lookup.
_METADATA_IP_ROOT = "http://{}".format(
    os.getenv(environment_vars.GCE_METADATA_IP, "169.254.169.254")
)
_METADATA_FLAVOR_HEADER = "metadata-flavor"
_METADATA_FLAVOR_VALUE = "Google"
_METADATA_HEADERS = {_METADATA_FLAVOR_HEADER: _METADATA_FLAVOR_VALUE}

# Timeout in seconds to wait for the GCE metadata server when detecting the
# GCE environment.
try:
    _METADATA_DEFAULT_TIMEOUT = int(os.getenv("GCE_METADATA_TIMEOUT", 3))
except ValueError:  # pragma: NO COVER
    _METADATA_DEFAULT_TIMEOUT = 3

# Detect GCE Residency
_GOOGLE = "Google"
_GCE_PRODUCT_NAME_FILE = "/sys/class/dmi/id/product_name"


def is_on_gce(request):
    """Checks to see if the code runs on Google Compute Engine

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.

    Returns:
        bool: True if the code runs on Google Compute Engine, False otherwise.
    """
    if ping(request):
        return True

    if os.name == "nt":
        # TODO: implement GCE residency detection on Windows
        return False

    # Detect GCE residency on Linux
    return detect_gce_residency_linux()


def detect_gce_residency_linux():
    """Detect Google Compute Engine residency by smbios check on Linux

    Returns:
        bool: True if the GCE product name file is detected, False otherwise.
    """
    try:
        with open(_GCE_PRODUCT_NAME_FILE, "r") as file_obj:
            content = file_obj.read().strip()

    except Exception:
        return False

    return content.startswith(_GOOGLE)


def ping(request, timeout=_METADATA_DEFAULT_TIMEOUT, retry_count=3):
    """Checks to see if the metadata server is available.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        timeout (int): How long to wait for the metadata server to respond.
        retry_count (int): How many times to attempt connecting to metadata
            server using above timeout.

    Returns:
        bool: True if the metadata server is reachable, False otherwise.
    """
    # NOTE: The explicit ``timeout`` is a workaround. The underlying
    #       issue is that resolving an unknown host on some networks will take
    #       20-30 seconds; making this timeout short fixes the issue, but
    #       could lead to false negatives in the event that we are on GCE, but
    #       the metadata resolution was particularly slow. The latter case is
    #       "unlikely".
    headers = _METADATA_HEADERS.copy()
    headers[metrics.API_CLIENT_HEADER] = metrics.mds_ping()

    backoff = ExponentialBackoff(total_attempts=retry_count)

    for attempt in backoff:
        try:
            response = request(
                url=_METADATA_IP_ROOT, method="GET", headers=headers, timeout=timeout
            )

            metadata_flavor = response.headers.get(_METADATA_FLAVOR_HEADER)
            return (
                response.status == http_client.OK
                and metadata_flavor == _METADATA_FLAVOR_VALUE
            )

        except exceptions.TransportError as e:
            _LOGGER.warning(
                "Compute Engine Metadata server unavailable on "
                "attempt %s of %s. Reason: %s",
                attempt,
                retry_count,
                e,
            )

    return False


def get(
    request,
    path,
    root=_METADATA_ROOT,
    params=None,
    recursive=False,
    retry_count=5,
    headers=None,
    return_none_for_not_found_error=False,
    timeout=_METADATA_DEFAULT_TIMEOUT,
):
    """Fetch a resource from the metadata server.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        path (str): The resource to retrieve. For example,
            ``'instance/service-accounts/default'``.
        root (str): The full path to the metadata server root.
        params (Optional[Mapping[str, str]]): A mapping of query parameter
            keys to values.
        recursive (bool): Whether to do a recursive query of metadata. See
            https://cloud.google.com/compute/docs/metadata#aggcontents for more
            details.
        retry_count (int): How many times to attempt connecting to metadata
            server using above timeout.
        headers (Optional[Mapping[str, str]]): Headers for the request.
        return_none_for_not_found_error (Optional[bool]): If True, returns None
            for 404 error instead of throwing an exception.
        timeout (int): How long to wait, in seconds for the metadata server to respond.

    Returns:
        Union[Mapping, str]: If the metadata server returns JSON, a mapping of
            the decoded JSON is returned. Otherwise, the response content is
            returned as a string.

    Raises:
        google.auth.exceptions.TransportError: if an error occurred while
            retrieving metadata.
    """
    base_url = urljoin(root, path)
    query_params = {} if params is None else params

    headers_to_use = _METADATA_HEADERS.copy()
    if headers:
        headers_to_use.update(headers)

    if recursive:
        query_params["recursive"] = "true"

    url = _helpers.update_query(base_url, query_params)

    backoff = ExponentialBackoff(total_attempts=retry_count)
    failure_reason = None
    for attempt in backoff:
        try:
            response = request(
                url=url, method="GET", headers=headers_to_use, timeout=timeout
            )
            if response.status in transport.DEFAULT_RETRYABLE_STATUS_CODES:
                _LOGGER.warning(
                    "Compute Engine Metadata server unavailable on "
                    "attempt %s of %s. Response status: %s",
                    attempt,
                    retry_count,
                    response.status,
                )
                failure_reason = (
                    response.data.decode("utf-8")
                    if hasattr(response.data, "decode")
                    else response.data
                )
                continue
            else:
                break

        except exceptions.TransportError as e:
            _LOGGER.warning(
                "Compute Engine Metadata server unavailable on "
                "attempt %s of %s. Reason: %s",
                attempt,
                retry_count,
                e,
            )
            failure_reason = e
    else:
        raise exceptions.TransportError(
            "Failed to retrieve {} from the Google Compute Engine "
            "metadata service. Compute Engine Metadata server unavailable due to {}".format(
                url, failure_reason
            )
        )

    content = _helpers.from_bytes(response.data)

    if response.status == http_client.NOT_FOUND and return_none_for_not_found_error:
        return None

    if response.status == http_client.OK:
        if (
            _helpers.parse_content_type(response.headers["content-type"])
            == "application/json"
        ):
            try:
                return json.loads(content)
            except ValueError as caught_exc:
                new_exc = exceptions.TransportError(
                    "Received invalid JSON from the Google Compute Engine "
                    "metadata service: {:.20}".format(content)
                )
                raise new_exc from caught_exc
        else:
            return content

    raise exceptions.TransportError(
        "Failed to retrieve {} from the Google Compute Engine "
        "metadata service. Status: {} Response:\n{}".format(
            url, response.status, response.data
        ),
        response,
    )


def get_project_id(request):
    """Get the Google Cloud Project ID from the metadata server.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.

    Returns:
        str: The project ID

    Raises:
        google.auth.exceptions.TransportError: if an error occurred while
            retrieving metadata.
    """
    return get(request, "project/project-id")


def get_universe_domain(request):
    """Get the universe domain value from the metadata server.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.

    Returns:
        str: The universe domain value. If the universe domain endpoint is not
        not found, return the default value, which is googleapis.com

    Raises:
        google.auth.exceptions.TransportError: if an error other than
            404 occurs while retrieving metadata.
    """
    universe_domain = get(
        request, "universe/universe-domain", return_none_for_not_found_error=True
    )
    if not universe_domain:
        return "googleapis.com"
    return universe_domain


def get_service_account_info(request, service_account="default"):
    """Get information about a service account from the metadata server.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        service_account (str): The string 'default' or a service account email
            address. The determines which service account for which to acquire
            information.

    Returns:
        Mapping: The service account's information, for example::

            {
                'email': '...',
                'scopes': ['scope', ...],
                'aliases': ['default', '...']
            }

    Raises:
        google.auth.exceptions.TransportError: if an error occurred while
            retrieving metadata.
    """
    path = "instance/service-accounts/{0}/".format(service_account)
    # See https://cloud.google.com/compute/docs/metadata#aggcontents
    # for more on the use of 'recursive'.
    return get(request, path, params={"recursive": "true"})


def get_service_account_token(request, service_account="default", scopes=None):
    """Get the OAuth 2.0 access token for a service account.

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        service_account (str): The string 'default' or a service account email
            address. The determines which service account for which to acquire
            an access token.
        scopes (Optional[Union[str, List[str]]]): Optional string or list of
            strings with auth scopes.
    Returns:
        Tuple[str, datetime]: The access token and its expiration.

    Raises:
        google.auth.exceptions.TransportError: if an error occurred while
            retrieving metadata.
    """
    if scopes:
        if not isinstance(scopes, str):
            scopes = ",".join(scopes)
        params = {"scopes": scopes}
    else:
        params = None

    metrics_header = {
        metrics.API_CLIENT_HEADER: metrics.token_request_access_token_mds()
    }

    path = "instance/service-accounts/{0}/token".format(service_account)
    token_json = get(request, path, params=params, headers=metrics_header)
    token_expiry = _helpers.utcnow() + datetime.timedelta(
        seconds=token_json["expires_in"]
    )
    return token_json["access_token"], token_expiry

# === NexusCore/openenv\Lib\site-packages\httpcore\_async\http11.py ===
from __future__ import annotations

import enum
import logging
import ssl
import time
import types
import typing

import h11

from .._backends.base import AsyncNetworkStream
from .._exceptions import (
    ConnectionNotAvailable,
    LocalProtocolError,
    RemoteProtocolError,
    WriteError,
    map_exceptions,
)
from .._models import Origin, Request, Response
from .._synchronization import AsyncLock, AsyncShieldCancellation
from .._trace import Trace
from .interfaces import AsyncConnectionInterface

logger = logging.getLogger("httpcore.http11")


# A subset of `h11.Event` types supported by `_send_event`
H11SendEvent = typing.Union[
    h11.Request,
    h11.Data,
    h11.EndOfMessage,
]


class HTTPConnectionState(enum.IntEnum):
    NEW = 0
    ACTIVE = 1
    IDLE = 2
    CLOSED = 3


class AsyncHTTP11Connection(AsyncConnectionInterface):
    READ_NUM_BYTES = 64 * 1024
    MAX_INCOMPLETE_EVENT_SIZE = 100 * 1024

    def __init__(
        self,
        origin: Origin,
        stream: AsyncNetworkStream,
        keepalive_expiry: float | None = None,
    ) -> None:
        self._origin = origin
        self._network_stream = stream
        self._keepalive_expiry: float | None = keepalive_expiry
        self._expire_at: float | None = None
        self._state = HTTPConnectionState.NEW
        self._state_lock = AsyncLock()
        self._request_count = 0
        self._h11_state = h11.Connection(
            our_role=h11.CLIENT,
            max_incomplete_event_size=self.MAX_INCOMPLETE_EVENT_SIZE,
        )

    async def handle_async_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection "
                f"to {self._origin}"
            )

        async with self._state_lock:
            if self._state in (HTTPConnectionState.NEW, HTTPConnectionState.IDLE):
                self._request_count += 1
                self._state = HTTPConnectionState.ACTIVE
                self._expire_at = None
            else:
                raise ConnectionNotAvailable()

        try:
            kwargs = {"request": request}
            try:
                async with Trace(
                    "send_request_headers", logger, request, kwargs
                ) as trace:
                    await self._send_request_headers(**kwargs)
                async with Trace("send_request_body", logger, request, kwargs) as trace:
                    await self._send_request_body(**kwargs)
            except WriteError:
                # If we get a write error while we're writing the request,
                # then we supress this error and move on to attempting to
                # read the response. Servers can sometimes close the request
                # pre-emptively and then respond with a well formed HTTP
                # error response.
                pass

            async with Trace(
                "receive_response_headers", logger, request, kwargs
            ) as trace:
                (
                    http_version,
                    status,
                    reason_phrase,
                    headers,
                    trailing_data,
                ) = await self._receive_response_headers(**kwargs)
                trace.return_value = (
                    http_version,
                    status,
                    reason_phrase,
                    headers,
                )

            network_stream = self._network_stream

            # CONNECT or Upgrade request
            if (status == 101) or (
                (request.method == b"CONNECT") and (200 <= status < 300)
            ):
                network_stream = AsyncHTTP11UpgradeStream(network_stream, trailing_data)

            return Response(
                status=status,
                headers=headers,
                content=HTTP11ConnectionByteStream(self, request),
                extensions={
                    "http_version": http_version,
                    "reason_phrase": reason_phrase,
                    "network_stream": network_stream,
                },
            )
        except BaseException as exc:
            with AsyncShieldCancellation():
                async with Trace("response_closed", logger, request) as trace:
                    await self._response_closed()
            raise exc

    # Sending the request...

    async def _send_request_headers(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        with map_exceptions({h11.LocalProtocolError: LocalProtocolError}):
            event = h11.Request(
                method=request.method,
                target=request.url.target,
                headers=request.headers,
            )
        await self._send_event(event, timeout=timeout)

    async def _send_request_body(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        assert isinstance(request.stream, typing.AsyncIterable)
        async for chunk in request.stream:
            event = h11.Data(data=chunk)
            await self._send_event(event, timeout=timeout)

        await self._send_event(h11.EndOfMessage(), timeout=timeout)

    async def _send_event(self, event: h11.Event, timeout: float | None = None) -> None:
        bytes_to_send = self._h11_state.send(event)
        if bytes_to_send is not None:
            await self._network_stream.write(bytes_to_send, timeout=timeout)

    # Receiving the response...

    async def _receive_response_headers(
        self, request: Request
    ) -> tuple[bytes, int, bytes, list[tuple[bytes, bytes]], bytes]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        while True:
            event = await self._receive_event(timeout=timeout)
            if isinstance(event, h11.Response):
                break
            if (
                isinstance(event, h11.InformationalResponse)
                and event.status_code == 101
            ):
                break

        http_version = b"HTTP/" + event.http_version

        # h11 version 0.11+ supports a `raw_items` interface to get the
        # raw header casing, rather than the enforced lowercase headers.
        headers = event.headers.raw_items()

        trailing_data, _ = self._h11_state.trailing_data

        return http_version, event.status_code, event.reason, headers, trailing_data

    async def _receive_response_body(
        self, request: Request
    ) -> typing.AsyncIterator[bytes]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        while True:
            event = await self._receive_event(timeout=timeout)
            if isinstance(event, h11.Data):
                yield bytes(event.data)
            elif isinstance(event, (h11.EndOfMessage, h11.PAUSED)):
                break

    async def _receive_event(
        self, timeout: float | None = None
    ) -> h11.Event | type[h11.PAUSED]:
        while True:
            with map_exceptions({h11.RemoteProtocolError: RemoteProtocolError}):
                event = self._h11_state.next_event()

            if event is h11.NEED_DATA:
                data = await self._network_stream.read(
                    self.READ_NUM_BYTES, timeout=timeout
                )

                # If we feed this case through h11 we'll raise an exception like:
                #
                #     httpcore.RemoteProtocolError: can't handle event type
                #     ConnectionClosed when role=SERVER and state=SEND_RESPONSE
                #
                # Which is accurate, but not very informative from an end-user
                # perspective. Instead we handle this case distinctly and treat
                # it as a ConnectError.
                if data == b"" and self._h11_state.their_state == h11.SEND_RESPONSE:
                    msg = "Server disconnected without sending a response."
                    raise RemoteProtocolError(msg)

                self._h11_state.receive_data(data)
            else:
                # mypy fails to narrow the type in the above if statement above
                return event  # type: ignore[return-value]

    async def _response_closed(self) -> None:
        async with self._state_lock:
            if (
                self._h11_state.our_state is h11.DONE
                and self._h11_state.their_state is h11.DONE
            ):
                self._state = HTTPConnectionState.IDLE
                self._h11_state.start_next_cycle()
                if self._keepalive_expiry is not None:
                    now = time.monotonic()
                    self._expire_at = now + self._keepalive_expiry
            else:
                await self.aclose()

    # Once the connection is no longer required...

    async def aclose(self) -> None:
        # Note that this method unilaterally closes the connection, and does
        # not have any kind of locking in place around it.
        self._state = HTTPConnectionState.CLOSED
        await self._network_stream.aclose()

    # The AsyncConnectionInterface methods provide information about the state of
    # the connection, allowing for a connection pooling implementation to
    # determine when to reuse and when to close the connection...

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    def is_available(self) -> bool:
        # Note that HTTP/1.1 connections in the "NEW" state are not treated as
        # being "available". The control flow which created the connection will
        # be able to send an outgoing request, but the connection will not be
        # acquired from the connection pool for any other request.
        return self._state == HTTPConnectionState.IDLE

    def has_expired(self) -> bool:
        now = time.monotonic()
        keepalive_expired = self._expire_at is not None and now > self._expire_at

        # If the HTTP connection is idle but the socket is readable, then the
        # only valid state is that the socket is about to return b"", indicating
        # a server-initiated disconnect.
        server_disconnected = (
            self._state == HTTPConnectionState.IDLE
            and self._network_stream.get_extra_info("is_readable")
        )

        return keepalive_expired or server_disconnected

    def is_idle(self) -> bool:
        return self._state == HTTPConnectionState.IDLE

    def is_closed(self) -> bool:
        return self._state == HTTPConnectionState.CLOSED

    def info(self) -> str:
        origin = str(self._origin)
        return (
            f"{origin!r}, HTTP/1.1, {self._state.name}, "
            f"Request Count: {self._request_count}"
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        origin = str(self._origin)
        return (
            f"<{class_name} [{origin!r}, {self._state.name}, "
            f"Request Count: {self._request_count}]>"
        )

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    async def __aenter__(self) -> AsyncHTTP11Connection:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        await self.aclose()


class HTTP11ConnectionByteStream:
    def __init__(self, connection: AsyncHTTP11Connection, request: Request) -> None:
        self._connection = connection
        self._request = request
        self._closed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        kwargs = {"request": self._request}
        try:
            async with Trace("receive_response_body", logger, self._request, kwargs):
                async for chunk in self._connection._receive_response_body(**kwargs):
                    yield chunk
        except BaseException as exc:
            # If we get an exception while streaming the response,
            # we want to close the response (and possibly the connection)
            # before raising that exception.
            with AsyncShieldCancellation():
                await self.aclose()
            raise exc

    async def aclose(self) -> None:
        if not self._closed:
            self._closed = True
            async with Trace("response_closed", logger, self._request):
                await self._connection._response_closed()


class AsyncHTTP11UpgradeStream(AsyncNetworkStream):
    def __init__(self, stream: AsyncNetworkStream, leading_data: bytes) -> None:
        self._stream = stream
        self._leading_data = leading_data

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self._leading_data:
            buffer = self._leading_data[:max_bytes]
            self._leading_data = self._leading_data[max_bytes:]
            return buffer
        else:
            return await self._stream.read(max_bytes, timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        await self._stream.write(buffer, timeout)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> AsyncNetworkStream:
        return await self._stream.start_tls(ssl_context, server_hostname, timeout)

    def get_extra_info(self, info: str) -> typing.Any:
        return self._stream.get_extra_info(info)

# === NexusCore/openenv\Lib\site-packages\httpcore\_sync\http11.py ===
from __future__ import annotations

import enum
import logging
import ssl
import time
import types
import typing

import h11

from .._backends.base import NetworkStream
from .._exceptions import (
    ConnectionNotAvailable,
    LocalProtocolError,
    RemoteProtocolError,
    WriteError,
    map_exceptions,
)
from .._models import Origin, Request, Response
from .._synchronization import Lock, ShieldCancellation
from .._trace import Trace
from .interfaces import ConnectionInterface

logger = logging.getLogger("httpcore.http11")


# A subset of `h11.Event` types supported by `_send_event`
H11SendEvent = typing.Union[
    h11.Request,
    h11.Data,
    h11.EndOfMessage,
]


class HTTPConnectionState(enum.IntEnum):
    NEW = 0
    ACTIVE = 1
    IDLE = 2
    CLOSED = 3


class HTTP11Connection(ConnectionInterface):
    READ_NUM_BYTES = 64 * 1024
    MAX_INCOMPLETE_EVENT_SIZE = 100 * 1024

    def __init__(
        self,
        origin: Origin,
        stream: NetworkStream,
        keepalive_expiry: float | None = None,
    ) -> None:
        self._origin = origin
        self._network_stream = stream
        self._keepalive_expiry: float | None = keepalive_expiry
        self._expire_at: float | None = None
        self._state = HTTPConnectionState.NEW
        self._state_lock = Lock()
        self._request_count = 0
        self._h11_state = h11.Connection(
            our_role=h11.CLIENT,
            max_incomplete_event_size=self.MAX_INCOMPLETE_EVENT_SIZE,
        )

    def handle_request(self, request: Request) -> Response:
        if not self.can_handle_request(request.url.origin):
            raise RuntimeError(
                f"Attempted to send request to {request.url.origin} on connection "
                f"to {self._origin}"
            )

        with self._state_lock:
            if self._state in (HTTPConnectionState.NEW, HTTPConnectionState.IDLE):
                self._request_count += 1
                self._state = HTTPConnectionState.ACTIVE
                self._expire_at = None
            else:
                raise ConnectionNotAvailable()

        try:
            kwargs = {"request": request}
            try:
                with Trace(
                    "send_request_headers", logger, request, kwargs
                ) as trace:
                    self._send_request_headers(**kwargs)
                with Trace("send_request_body", logger, request, kwargs) as trace:
                    self._send_request_body(**kwargs)
            except WriteError:
                # If we get a write error while we're writing the request,
                # then we supress this error and move on to attempting to
                # read the response. Servers can sometimes close the request
                # pre-emptively and then respond with a well formed HTTP
                # error response.
                pass

            with Trace(
                "receive_response_headers", logger, request, kwargs
            ) as trace:
                (
                    http_version,
                    status,
                    reason_phrase,
                    headers,
                    trailing_data,
                ) = self._receive_response_headers(**kwargs)
                trace.return_value = (
                    http_version,
                    status,
                    reason_phrase,
                    headers,
                )

            network_stream = self._network_stream

            # CONNECT or Upgrade request
            if (status == 101) or (
                (request.method == b"CONNECT") and (200 <= status < 300)
            ):
                network_stream = HTTP11UpgradeStream(network_stream, trailing_data)

            return Response(
                status=status,
                headers=headers,
                content=HTTP11ConnectionByteStream(self, request),
                extensions={
                    "http_version": http_version,
                    "reason_phrase": reason_phrase,
                    "network_stream": network_stream,
                },
            )
        except BaseException as exc:
            with ShieldCancellation():
                with Trace("response_closed", logger, request) as trace:
                    self._response_closed()
            raise exc

    # Sending the request...

    def _send_request_headers(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        with map_exceptions({h11.LocalProtocolError: LocalProtocolError}):
            event = h11.Request(
                method=request.method,
                target=request.url.target,
                headers=request.headers,
            )
        self._send_event(event, timeout=timeout)

    def _send_request_body(self, request: Request) -> None:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("write", None)

        assert isinstance(request.stream, typing.Iterable)
        for chunk in request.stream:
            event = h11.Data(data=chunk)
            self._send_event(event, timeout=timeout)

        self._send_event(h11.EndOfMessage(), timeout=timeout)

    def _send_event(self, event: h11.Event, timeout: float | None = None) -> None:
        bytes_to_send = self._h11_state.send(event)
        if bytes_to_send is not None:
            self._network_stream.write(bytes_to_send, timeout=timeout)

    # Receiving the response...

    def _receive_response_headers(
        self, request: Request
    ) -> tuple[bytes, int, bytes, list[tuple[bytes, bytes]], bytes]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        while True:
            event = self._receive_event(timeout=timeout)
            if isinstance(event, h11.Response):
                break
            if (
                isinstance(event, h11.InformationalResponse)
                and event.status_code == 101
            ):
                break

        http_version = b"HTTP/" + event.http_version

        # h11 version 0.11+ supports a `raw_items` interface to get the
        # raw header casing, rather than the enforced lowercase headers.
        headers = event.headers.raw_items()

        trailing_data, _ = self._h11_state.trailing_data

        return http_version, event.status_code, event.reason, headers, trailing_data

    def _receive_response_body(
        self, request: Request
    ) -> typing.Iterator[bytes]:
        timeouts = request.extensions.get("timeout", {})
        timeout = timeouts.get("read", None)

        while True:
            event = self._receive_event(timeout=timeout)
            if isinstance(event, h11.Data):
                yield bytes(event.data)
            elif isinstance(event, (h11.EndOfMessage, h11.PAUSED)):
                break

    def _receive_event(
        self, timeout: float | None = None
    ) -> h11.Event | type[h11.PAUSED]:
        while True:
            with map_exceptions({h11.RemoteProtocolError: RemoteProtocolError}):
                event = self._h11_state.next_event()

            if event is h11.NEED_DATA:
                data = self._network_stream.read(
                    self.READ_NUM_BYTES, timeout=timeout
                )

                # If we feed this case through h11 we'll raise an exception like:
                #
                #     httpcore.RemoteProtocolError: can't handle event type
                #     ConnectionClosed when role=SERVER and state=SEND_RESPONSE
                #
                # Which is accurate, but not very informative from an end-user
                # perspective. Instead we handle this case distinctly and treat
                # it as a ConnectError.
                if data == b"" and self._h11_state.their_state == h11.SEND_RESPONSE:
                    msg = "Server disconnected without sending a response."
                    raise RemoteProtocolError(msg)

                self._h11_state.receive_data(data)
            else:
                # mypy fails to narrow the type in the above if statement above
                return event  # type: ignore[return-value]

    def _response_closed(self) -> None:
        with self._state_lock:
            if (
                self._h11_state.our_state is h11.DONE
                and self._h11_state.their_state is h11.DONE
            ):
                self._state = HTTPConnectionState.IDLE
                self._h11_state.start_next_cycle()
                if self._keepalive_expiry is not None:
                    now = time.monotonic()
                    self._expire_at = now + self._keepalive_expiry
            else:
                self.close()

    # Once the connection is no longer required...

    def close(self) -> None:
        # Note that this method unilaterally closes the connection, and does
        # not have any kind of locking in place around it.
        self._state = HTTPConnectionState.CLOSED
        self._network_stream.close()

    # The ConnectionInterface methods provide information about the state of
    # the connection, allowing for a connection pooling implementation to
    # determine when to reuse and when to close the connection...

    def can_handle_request(self, origin: Origin) -> bool:
        return origin == self._origin

    def is_available(self) -> bool:
        # Note that HTTP/1.1 connections in the "NEW" state are not treated as
        # being "available". The control flow which created the connection will
        # be able to send an outgoing request, but the connection will not be
        # acquired from the connection pool for any other request.
        return self._state == HTTPConnectionState.IDLE

    def has_expired(self) -> bool:
        now = time.monotonic()
        keepalive_expired = self._expire_at is not None and now > self._expire_at

        # If the HTTP connection is idle but the socket is readable, then the
        # only valid state is that the socket is about to return b"", indicating
        # a server-initiated disconnect.
        server_disconnected = (
            self._state == HTTPConnectionState.IDLE
            and self._network_stream.get_extra_info("is_readable")
        )

        return keepalive_expired or server_disconnected

    def is_idle(self) -> bool:
        return self._state == HTTPConnectionState.IDLE

    def is_closed(self) -> bool:
        return self._state == HTTPConnectionState.CLOSED

    def info(self) -> str:
        origin = str(self._origin)
        return (
            f"{origin!r}, HTTP/1.1, {self._state.name}, "
            f"Request Count: {self._request_count}"
        )

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        origin = str(self._origin)
        return (
            f"<{class_name} [{origin!r}, {self._state.name}, "
            f"Request Count: {self._request_count}]>"
        )

    # These context managers are not used in the standard flow, but are
    # useful for testing or working with connection instances directly.

    def __enter__(self) -> HTTP11Connection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: types.TracebackType | None = None,
    ) -> None:
        self.close()


class HTTP11ConnectionByteStream:
    def __init__(self, connection: HTTP11Connection, request: Request) -> None:
        self._connection = connection
        self._request = request
        self._closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        kwargs = {"request": self._request}
        try:
            with Trace("receive_response_body", logger, self._request, kwargs):
                for chunk in self._connection._receive_response_body(**kwargs):
                    yield chunk
        except BaseException as exc:
            # If we get an exception while streaming the response,
            # we want to close the response (and possibly the connection)
            # before raising that exception.
            with ShieldCancellation():
                self.close()
            raise exc

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            with Trace("response_closed", logger, self._request):
                self._connection._response_closed()


class HTTP11UpgradeStream(NetworkStream):
    def __init__(self, stream: NetworkStream, leading_data: bytes) -> None:
        self._stream = stream
        self._leading_data = leading_data

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self._leading_data:
            buffer = self._leading_data[:max_bytes]
            self._leading_data = self._leading_data[max_bytes:]
            return buffer
        else:
            return self._stream.read(max_bytes, timeout)

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        self._stream.write(buffer, timeout)

    def close(self) -> None:
        self._stream.close()

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> NetworkStream:
        return self._stream.start_tls(ssl_context, server_hostname, timeout)

    def get_extra_info(self, info: str) -> typing.Any:
        return self._stream.get_extra_info(info)

# === NexusCore/openenv\Lib\site-packages\IPython\utils\ipstruct.py ===
# encoding: utf-8
"""A dict subclass that supports attribute style access.

Authors:

* Fernando Perez (original)
* Brian Granger (refactoring to a dict subclass)
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

__all__ = ['Struct']

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------


class Struct(dict):
    """A dict subclass with attribute style access.

    This dict subclass has a a few extra features:

    * Attribute style access.
    * Protection of class members (like keys, items) when using attribute
      style access.
    * The ability to restrict assignment to only existing keys.
    * Intelligent merging.
    * Overloaded operators.
    """
    _allownew = True
    def __init__(self, *args, **kw):
        """Initialize with a dictionary, another Struct, or data.

        Parameters
        ----------
        *args : dict, Struct
            Initialize with one dict or Struct
        **kw : dict
            Initialize with key, value pairs.

        Examples
        --------
        >>> s = Struct(a=10,b=30)
        >>> s.a
        10
        >>> s.b
        30
        >>> s2 = Struct(s,c=30)
        >>> sorted(s2.keys())
        ['a', 'b', 'c']
        """
        object.__setattr__(self, '_allownew', True)
        dict.__init__(self, *args, **kw)

    def __setitem__(self, key, value):
        """Set an item with check for allownew.

        Examples
        --------
        >>> s = Struct()
        >>> s['a'] = 10
        >>> s.allow_new_attr(False)
        >>> s['a'] = 10
        >>> s['a']
        10
        >>> try:
        ...     s['b'] = 20
        ... except KeyError:
        ...     print('this is not allowed')
        ...
        this is not allowed
        """
        if not self._allownew and key not in self:
            raise KeyError(
                "can't create new attribute %s when allow_new_attr(False)" % key)
        dict.__setitem__(self, key, value)

    def __setattr__(self, key, value):
        """Set an attr with protection of class members.

        This calls :meth:`self.__setitem__` but convert :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------
        >>> s = Struct()
        >>> s.a = 10
        >>> s.a
        10
        >>> try:
        ...     s.get = 10
        ... except AttributeError:
        ...     print("you can't set a class member")
        ...
        you can't set a class member
        """
        # If key is an str it might be a class member or instance var
        if isinstance(key, str):
            # I can't simply call hasattr here because it calls getattr, which
            # calls self.__getattr__, which returns True for keys in
            # self._data.  But I only want keys in the class and in
            # self.__dict__
            if key in self.__dict__ or hasattr(Struct, key):
                raise AttributeError(
                    'attr %s is a protected member of class Struct.' % key
                )
        try:
            self.__setitem__(key, value)
        except KeyError as e:
            raise AttributeError(e) from e

    def __getattr__(self, key):
        """Get an attr by calling :meth:`dict.__getitem__`.

        Like :meth:`__setattr__`, this method converts :exc:`KeyError` to
        :exc:`AttributeError`.

        Examples
        --------
        >>> s = Struct(a=10)
        >>> s.a
        10
        >>> type(s.get)
        <...method'>
        >>> try:
        ...     s.b
        ... except AttributeError:
        ...     print("I don't have that key")
        ...
        I don't have that key
        """
        try:
            result = self[key]
        except KeyError as e:
            raise AttributeError(key) from e
        else:
            return result

    def __iadd__(self, other):
        """s += s2 is a shorthand for s.merge(s2).

        Examples
        --------
        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s += s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        self.merge(other)
        return self

    def __add__(self,other):
        """s + s2 -> New Struct made from s.merge(s2).

        Examples
        --------
        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s = s1 + s2
        >>> sorted(s.keys())
        ['a', 'b', 'c']
        """
        sout = self.copy()
        sout.merge(other)
        return sout

    def __sub__(self,other):
        """s1 - s2 -> remove keys in s2 from s1.

        Examples
        --------
        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s = s1 - s2
        >>> s
        {'b': 30}
        """
        sout = self.copy()
        sout -= other
        return sout

    def __isub__(self,other):
        """Inplace remove keys from self that are in other.

        Examples
        --------
        >>> s1 = Struct(a=10,b=30)
        >>> s2 = Struct(a=40)
        >>> s1 -= s2
        >>> s1
        {'b': 30}
        """
        for k in other.keys():
            if k in self:
                del self[k]
        return self

    def __dict_invert(self, data):
        """Helper function for merge.

        Takes a dictionary whose values are lists and returns a dict with
        the elements of each list as keys and the original keys as values.
        """
        outdict = {}
        for k,lst in data.items():
            if isinstance(lst, str):
                lst = lst.split()
            for entry in lst:
                outdict[entry] = k
        return outdict

    def dict(self):
        return self

    def copy(self):
        """Return a copy as a Struct.

        Examples
        --------
        >>> s = Struct(a=10,b=30)
        >>> s2 = s.copy()
        >>> type(s2) is Struct
        True
        """
        return Struct(dict.copy(self))

    def hasattr(self, key):
        """hasattr function available as a method.

        Implemented like has_key.

        Examples
        --------
        >>> s = Struct(a=10)
        >>> s.hasattr('a')
        True
        >>> s.hasattr('b')
        False
        >>> s.hasattr('get')
        False
        """
        return key in self

    def allow_new_attr(self, allow = True):
        """Set whether new attributes can be created in this Struct.

        This can be used to catch typos by verifying that the attribute user
        tries to change already exists in this Struct.
        """
        object.__setattr__(self, '_allownew', allow)

    def merge(self, __loc_data__=None, __conflict_solve=None, **kw):
        """Merge two Structs with customizable conflict resolution.

        This is similar to :meth:`update`, but much more flexible. First, a
        dict is made from data+key=value pairs. When merging this dict with
        the Struct S, the optional dictionary 'conflict' is used to decide
        what to do.

        If conflict is not given, the default behavior is to preserve any keys
        with their current value (the opposite of the :meth:`update` method's
        behavior).

        Parameters
        ----------
        __loc_data__ : dict, Struct
            The data to merge into self
        __conflict_solve : dict
            The conflict policy dict.  The keys are binary functions used to
            resolve the conflict and the values are lists of strings naming
            the keys the conflict resolution function applies to.  Instead of
            a list of strings a space separated string can be used, like
            'a b c'.
        **kw : dict
            Additional key, value pairs to merge in

        Notes
        -----
        The `__conflict_solve` dict is a dictionary of binary functions which will be used to
        solve key conflicts.  Here is an example::

            __conflict_solve = dict(
                func1=['a','b','c'],
                func2=['d','e']
            )

        In this case, the function :func:`func1` will be used to resolve
        keys 'a', 'b' and 'c' and the function :func:`func2` will be used for
        keys 'd' and 'e'.  This could also be written as::

            __conflict_solve = dict(func1='a b c',func2='d e')

        These functions will be called for each key they apply to with the
        form::

            func1(self['a'], other['a'])

        The return value is used as the final merged value.

        As a convenience, merge() provides five (the most commonly needed)
        pre-defined policies: preserve, update, add, add_flip and add_s. The
        easiest explanation is their implementation::

            preserve = lambda old,new: old
            update   = lambda old,new: new
            add      = lambda old,new: old + new
            add_flip = lambda old,new: new + old  # note change of order!
            add_s    = lambda old,new: old + ' ' + new  # only for str!

        You can use those four words (as strings) as keys instead
        of defining them as functions, and the merge method will substitute
        the appropriate functions for you.

        For more complicated conflict resolution policies, you still need to
        construct your own functions.

        Examples
        --------
        This show the default policy:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,c=40)
        >>> s.merge(s2)
        >>> sorted(s.items())
        [('a', 10), ('b', 30), ('c', 40)]

        Now, show how to specify a conflict dict:

        >>> s = Struct(a=10,b=30)
        >>> s2 = Struct(a=20,b=40)
        >>> conflict = {'update':'a','add':'b'}
        >>> s.merge(s2,conflict)
        >>> sorted(s.items())
        [('a', 20), ('b', 70)]
        """

        data_dict = dict(__loc_data__,**kw)

        # policies for conflict resolution: two argument functions which return
        # the value that will go in the new struct
        preserve = lambda old,new: old
        update   = lambda old,new: new
        add      = lambda old,new: old + new
        add_flip = lambda old,new: new + old  # note change of order!
        add_s    = lambda old,new: old + ' ' + new

        # default policy is to keep current keys when there's a conflict
        conflict_solve = dict.fromkeys(self, preserve)

        # the conflict_solve dictionary is given by the user 'inverted': we
        # need a name-function mapping, it comes as a function -> names
        # dict. Make a local copy (b/c we'll make changes), replace user
        # strings for the three builtin policies and invert it.
        if __conflict_solve:
            inv_conflict_solve_user = __conflict_solve.copy()
            for name, func in [('preserve',preserve), ('update',update),
                               ('add',add), ('add_flip',add_flip),
                               ('add_s',add_s)]:
                if name in inv_conflict_solve_user.keys():
                    inv_conflict_solve_user[func] = inv_conflict_solve_user[name]
                    del inv_conflict_solve_user[name]
            conflict_solve.update(self.__dict_invert(inv_conflict_solve_user))
        for key in data_dict:
            if key not in self:
                self[key] = data_dict[key]
            else:
                self[key] = conflict_solve[key](self[key],data_dict[key])


# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\completion\handler.py ===
from typing import Any, Callable, Optional

from openai import AsyncAzureOpenAI, AzureOpenAI

from litellm.litellm_core_utils.prompt_templates.factory import prompt_factory
from litellm.utils import CustomStreamWrapper, ModelResponse, TextCompletionResponse

from ...openai.completion.transformation import OpenAITextCompletionConfig
from ..common_utils import AzureOpenAIError, BaseAzureLLM

openai_text_completion_config = OpenAITextCompletionConfig()


class AzureTextCompletion(BaseAzureLLM):
    def __init__(self) -> None:
        super().__init__()

    def validate_environment(self, api_key, azure_ad_token):
        headers = {
            "content-type": "application/json",
        }
        if api_key is not None:
            headers["api-key"] = api_key
        elif azure_ad_token is not None:
            headers["Authorization"] = f"Bearer {azure_ad_token}"
        return headers

    def completion(  # noqa: PLR0915
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        api_key: str,
        api_base: str,
        api_version: str,
        api_type: str,
        azure_ad_token: str,
        azure_ad_token_provider: Optional[Callable],
        print_verbose: Callable,
        timeout,
        logging_obj,
        optional_params,
        litellm_params,
        logger_fn,
        acompletion: bool = False,
        headers: Optional[dict] = None,
        client=None,
    ):
        try:
            if model is None or messages is None:
                raise AzureOpenAIError(
                    status_code=422, message="Missing model or messages"
                )

            max_retries = optional_params.pop("max_retries", 2)
            prompt = prompt_factory(
                messages=messages, model=model, custom_llm_provider="azure_text"
            )

            ### CHECK IF CLOUDFLARE AI GATEWAY ###
            ### if so - set the model as part of the base url
            if "gateway.ai.cloudflare.com" in api_base:
                ## build base url - assume api base includes resource name
                client = self._init_azure_client_for_cloudflare_ai_gateway(
                    api_key=api_key,
                    api_version=api_version,
                    api_base=api_base,
                    model=model,
                    client=client,
                    max_retries=max_retries,
                    timeout=timeout,
                    azure_ad_token=azure_ad_token,
                    azure_ad_token_provider=azure_ad_token_provider,
                    acompletion=acompletion,
                    litellm_params=litellm_params,
                )

                data = {"model": None, "prompt": prompt, **optional_params}
            else:
                data = {
                    "model": model,  # type: ignore
                    "prompt": prompt,
                    **optional_params,
                }

            if acompletion is True:
                if optional_params.get("stream", False):
                    return self.async_streaming(
                        logging_obj=logging_obj,
                        api_base=api_base,
                        data=data,
                        model=model,
                        api_key=api_key,
                        api_version=api_version,
                        azure_ad_token=azure_ad_token,
                        timeout=timeout,
                        client=client,
                        litellm_params=litellm_params,
                    )
                else:
                    return self.acompletion(
                        api_base=api_base,
                        data=data,
                        model_response=model_response,
                        api_key=api_key,
                        api_version=api_version,
                        model=model,
                        azure_ad_token=azure_ad_token,
                        timeout=timeout,
                        client=client,
                        logging_obj=logging_obj,
                        max_retries=max_retries,
                        litellm_params=litellm_params,
                    )
            elif "stream" in optional_params and optional_params["stream"] is True:
                return self.streaming(
                    logging_obj=logging_obj,
                    api_base=api_base,
                    data=data,
                    model=model,
                    api_key=api_key,
                    api_version=api_version,
                    azure_ad_token=azure_ad_token,
                    timeout=timeout,
                    client=client,
                )
            else:
                ## LOGGING
                logging_obj.pre_call(
                    input=prompt,
                    api_key=api_key,
                    additional_args={
                        "headers": {
                            "api_key": api_key,
                            "azure_ad_token": azure_ad_token,
                        },
                        "api_version": api_version,
                        "api_base": api_base,
                        "complete_input_dict": data,
                    },
                )
                if not isinstance(max_retries, int):
                    raise AzureOpenAIError(
                        status_code=422, message="max retries must be an int"
                    )
                # init AzureOpenAI Client
                azure_client = self.get_azure_openai_client(
                    api_key=api_key,
                    api_base=api_base,
                    api_version=api_version,
                    client=client,
                    litellm_params=litellm_params,
                    _is_async=False,
                    model=model,
                )

                if not isinstance(azure_client, AzureOpenAI):
                    raise AzureOpenAIError(
                        status_code=500,
                        message="azure_client is not an instance of AzureOpenAI",
                    )

                raw_response = azure_client.completions.with_raw_response.create(
                    **data, timeout=timeout
                )
                response = raw_response.parse()
                stringified_response = response.model_dump()
                ## LOGGING
                logging_obj.post_call(
                    input=prompt,
                    api_key=api_key,
                    original_response=stringified_response,
                    additional_args={
                        "headers": headers,
                        "api_version": api_version,
                        "api_base": api_base,
                    },
                )
                return (
                    openai_text_completion_config.convert_to_chat_model_response_object(
                        response_object=TextCompletionResponse(**stringified_response),
                        model_response_object=model_response,
                    )
                )
        except AzureOpenAIError as e:
            raise e
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise AzureOpenAIError(
                status_code=status_code, message=str(e), headers=error_headers
            )

    async def acompletion(
        self,
        api_key: str,
        api_version: str,
        model: str,
        api_base: str,
        data: dict,
        timeout: Any,
        model_response: ModelResponse,
        logging_obj: Any,
        max_retries: int,
        azure_ad_token: Optional[str] = None,
        client=None,  # this is the AsyncAzureOpenAI
        litellm_params: dict = {},
    ):
        response = None
        try:
            # init AzureOpenAI Client
            # setting Azure client
            azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                _is_async=True,
                client=client,
                litellm_params=litellm_params,
            )
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise AzureOpenAIError(
                    status_code=500,
                    message="azure_client is not an instance of AsyncAzureOpenAI",
                )

            ## LOGGING
            logging_obj.pre_call(
                input=data["prompt"],
                api_key=azure_client.api_key,
                additional_args={
                    "headers": {"Authorization": f"Bearer {azure_client.api_key}"},
                    "api_base": azure_client._base_url._uri_reference,
                    "acompletion": True,
                    "complete_input_dict": data,
                },
            )
            raw_response = await azure_client.completions.with_raw_response.create(
                **data, timeout=timeout
            )
            response = raw_response.parse()
            return openai_text_completion_config.convert_to_chat_model_response_object(
                response_object=response.model_dump(),
                model_response_object=model_response,
            )
        except AzureOpenAIError as e:
            raise e
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise AzureOpenAIError(
                status_code=status_code, message=str(e), headers=error_headers
            )

    def streaming(
        self,
        logging_obj,
        api_base: str,
        api_key: str,
        api_version: str,
        data: dict,
        model: str,
        timeout: Any,
        azure_ad_token: Optional[str] = None,
        client=None,
        litellm_params: dict = {},
    ):
        max_retries = data.pop("max_retries", 2)
        if not isinstance(max_retries, int):
            raise AzureOpenAIError(
                status_code=422, message="max retries must be an int"
            )
        # init AzureOpenAI Client
        azure_client = self.get_azure_openai_client(
            api_version=api_version,
            api_base=api_base,
            api_key=api_key,
            model=model,
            _is_async=False,
            client=client,
            litellm_params=litellm_params,
        )
        if not isinstance(azure_client, AzureOpenAI):
            raise AzureOpenAIError(
                status_code=500,
                message="azure_client is not an instance of AzureOpenAI",
            )

        ## LOGGING
        logging_obj.pre_call(
            input=data["prompt"],
            api_key=azure_client.api_key,
            additional_args={
                "headers": {"Authorization": f"Bearer {azure_client.api_key}"},
                "api_base": azure_client._base_url._uri_reference,
                "acompletion": True,
                "complete_input_dict": data,
            },
        )
        raw_response = azure_client.completions.with_raw_response.create(
            **data, timeout=timeout
        )
        response = raw_response.parse()
        streamwrapper = CustomStreamWrapper(
            completion_stream=response,
            model=model,
            custom_llm_provider="azure_text",
            logging_obj=logging_obj,
        )
        return streamwrapper

    async def async_streaming(
        self,
        logging_obj,
        api_base: str,
        api_key: str,
        api_version: str,
        data: dict,
        model: str,
        timeout: Any,
        azure_ad_token: Optional[str] = None,
        client=None,
        litellm_params: dict = {},
    ):
        try:
            # init AzureOpenAI Client
            azure_client = self.get_azure_openai_client(
                api_version=api_version,
                api_base=api_base,
                api_key=api_key,
                model=model,
                _is_async=True,
                client=client,
                litellm_params=litellm_params,
            )
            if not isinstance(azure_client, AsyncAzureOpenAI):
                raise AzureOpenAIError(
                    status_code=500,
                    message="azure_client is not an instance of AsyncAzureOpenAI",
                )
            ## LOGGING
            logging_obj.pre_call(
                input=data["prompt"],
                api_key=azure_client.api_key,
                additional_args={
                    "headers": {"Authorization": f"Bearer {azure_client.api_key}"},
                    "api_base": azure_client._base_url._uri_reference,
                    "acompletion": True,
                    "complete_input_dict": data,
                },
            )
            raw_response = await azure_client.completions.with_raw_response.create(
                **data, timeout=timeout
            )
            response = raw_response.parse()
            # return response
            streamwrapper = CustomStreamWrapper(
                completion_stream=response,
                model=model,
                custom_llm_provider="azure_text",
                logging_obj=logging_obj,
            )
            return streamwrapper  ## DO NOT make this into an async for ... loop, it will yield an async generator, which won't raise errors if the response fails
        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_headers = getattr(e, "headers", None)
            error_response = getattr(e, "response", None)
            if error_headers is None and error_response:
                error_headers = getattr(error_response, "headers", None)
            raise AzureOpenAIError(
                status_code=status_code, message=str(e), headers=error_headers
            )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\automation.py ===
"""
    pygments.lexers.automation
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for automation scripting languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, bygroups, combined
from pygments.token import Text, Comment, Operator, Name, String, \
    Number, Punctuation, Generic

__all__ = ['AutohotkeyLexer', 'AutoItLexer']


class AutohotkeyLexer(RegexLexer):
    """
    For autohotkey source code.
    """
    name = 'autohotkey'
    url = 'http://www.autohotkey.com/'
    aliases = ['autohotkey', 'ahk']
    filenames = ['*.ahk', '*.ahkl']
    mimetypes = ['text/x-autohotkey']
    version_added = '1.4'

    tokens = {
        'root': [
            (r'^(\s*)(/\*)', bygroups(Text, Comment.Multiline), 'incomment'),
            (r'^(\s*)(\()', bygroups(Text, Generic), 'incontinuation'),
            (r'\s+;.*?$', Comment.Single),
            (r'^;.*?$', Comment.Single),
            (r'[]{}(),;[]', Punctuation),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'\%[a-zA-Z_#@$][\w#@$]*\%', Name.Variable),
            (r'!=|==|:=|\.=|<<|>>|[-~+/*%=<>&^|?:!.]', Operator),
            include('commands'),
            include('labels'),
            include('builtInFunctions'),
            include('builtInVariables'),
            (r'"', String, combined('stringescape', 'dqs')),
            include('numbers'),
            (r'[a-zA-Z_#@$][\w#@$]*', Name),
            (r'\\|\'', Text),
            (r'\`([,%`abfnrtv\-+;])', String.Escape),
            include('garbage'),
        ],
        'incomment': [
            (r'^\s*\*/', Comment.Multiline, '#pop'),
            (r'[^*]+', Comment.Multiline),
            (r'\*', Comment.Multiline)
        ],
        'incontinuation': [
            (r'^\s*\)', Generic, '#pop'),
            (r'[^)]', Generic),
            (r'[)]', Generic),
        ],
        'commands': [
            (r'(?i)^(\s*)(global|local|static|'
             r'#AllowSameLineComments|#ClipboardTimeout|#CommentFlag|'
             r'#ErrorStdOut|#EscapeChar|#HotkeyInterval|#HotkeyModifierTimeout|'
             r'#Hotstring|#IfWinActive|#IfWinExist|#IfWinNotActive|'
             r'#IfWinNotExist|#IncludeAgain|#Include|#InstallKeybdHook|'
             r'#InstallMouseHook|#KeyHistory|#LTrim|#MaxHotkeysPerInterval|'
             r'#MaxMem|#MaxThreads|#MaxThreadsBuffer|#MaxThreadsPerHotkey|'
             r'#NoEnv|#NoTrayIcon|#Persistent|#SingleInstance|#UseHook|'
             r'#WinActivateForce|AutoTrim|BlockInput|Break|Click|ClipWait|'
             r'Continue|Control|ControlClick|ControlFocus|ControlGetFocus|'
             r'ControlGetPos|ControlGetText|ControlGet|ControlMove|ControlSend|'
             r'ControlSendRaw|ControlSetText|CoordMode|Critical|'
             r'DetectHiddenText|DetectHiddenWindows|Drive|DriveGet|'
             r'DriveSpaceFree|Edit|Else|EnvAdd|EnvDiv|EnvGet|EnvMult|EnvSet|'
             r'EnvSub|EnvUpdate|Exit|ExitApp|FileAppend|'
             r'FileCopy|FileCopyDir|FileCreateDir|FileCreateShortcut|'
             r'FileDelete|FileGetAttrib|FileGetShortcut|FileGetSize|'
             r'FileGetTime|FileGetVersion|FileInstall|FileMove|FileMoveDir|'
             r'FileRead|FileReadLine|FileRecycle|FileRecycleEmpty|'
             r'FileRemoveDir|FileSelectFile|FileSelectFolder|FileSetAttrib|'
             r'FileSetTime|FormatTime|GetKeyState|Gosub|Goto|GroupActivate|'
             r'GroupAdd|GroupClose|GroupDeactivate|Gui|GuiControl|'
             r'GuiControlGet|Hotkey|IfEqual|IfExist|IfGreaterOrEqual|IfGreater|'
             r'IfInString|IfLess|IfLessOrEqual|IfMsgBox|IfNotEqual|IfNotExist|'
             r'IfNotInString|IfWinActive|IfWinExist|IfWinNotActive|'
             r'IfWinNotExist|If |ImageSearch|IniDelete|IniRead|IniWrite|'
             r'InputBox|Input|KeyHistory|KeyWait|ListHotkeys|ListLines|'
             r'ListVars|Loop|Menu|MouseClickDrag|MouseClick|MouseGetPos|'
             r'MouseMove|MsgBox|OnExit|OutputDebug|Pause|PixelGetColor|'
             r'PixelSearch|PostMessage|Process|Progress|Random|RegDelete|'
             r'RegRead|RegWrite|Reload|Repeat|Return|RunAs|RunWait|Run|'
             r'SendEvent|SendInput|SendMessage|SendMode|SendPlay|SendRaw|Send|'
             r'SetBatchLines|SetCapslockState|SetControlDelay|'
             r'SetDefaultMouseSpeed|SetEnv|SetFormat|SetKeyDelay|'
             r'SetMouseDelay|SetNumlockState|SetScrollLockState|'
             r'SetStoreCapslockMode|SetTimer|SetTitleMatchMode|'
             r'SetWinDelay|SetWorkingDir|Shutdown|Sleep|Sort|SoundBeep|'
             r'SoundGet|SoundGetWaveVolume|SoundPlay|SoundSet|'
             r'SoundSetWaveVolume|SplashImage|SplashTextOff|SplashTextOn|'
             r'SplitPath|StatusBarGetText|StatusBarWait|StringCaseSense|'
             r'StringGetPos|StringLeft|StringLen|StringLower|StringMid|'
             r'StringReplace|StringRight|StringSplit|StringTrimLeft|'
             r'StringTrimRight|StringUpper|Suspend|SysGet|Thread|ToolTip|'
             r'Transform|TrayTip|URLDownloadToFile|While|WinActivate|'
             r'WinActivateBottom|WinClose|WinGetActiveStats|WinGetActiveTitle|'
             r'WinGetClass|WinGetPos|WinGetText|WinGetTitle|WinGet|WinHide|'
             r'WinKill|WinMaximize|WinMenuSelectItem|WinMinimizeAllUndo|'
             r'WinMinimizeAll|WinMinimize|WinMove|WinRestore|WinSetTitle|'
             r'WinSet|WinShow|WinWaitActive|WinWaitClose|WinWaitNotActive|'
             r'WinWait)\b', bygroups(Text, Name.Builtin)),
        ],
        'builtInFunctions': [
            (r'(?i)(Abs|ACos|Asc|ASin|ATan|Ceil|Chr|Cos|DllCall|Exp|FileExist|'
             r'Floor|GetKeyState|IL_Add|IL_Create|IL_Destroy|InStr|IsFunc|'
             r'IsLabel|Ln|Log|LV_Add|LV_Delete|LV_DeleteCol|LV_GetCount|'
             r'LV_GetNext|LV_GetText|LV_Insert|LV_InsertCol|LV_Modify|'
             r'LV_ModifyCol|LV_SetImageList|Mod|NumGet|NumPut|OnMessage|'
             r'RegExMatch|RegExReplace|RegisterCallback|Round|SB_SetIcon|'
             r'SB_SetParts|SB_SetText|Sin|Sqrt|StrLen|SubStr|Tan|TV_Add|'
             r'TV_Delete|TV_GetChild|TV_GetCount|TV_GetNext|TV_Get|'
             r'TV_GetParent|TV_GetPrev|TV_GetSelection|TV_GetText|TV_Modify|'
             r'VarSetCapacity|WinActive|WinExist|Object|ComObjActive|'
             r'ComObjArray|ComObjEnwrap|ComObjUnwrap|ComObjParameter|'
             r'ComObjType|ComObjConnect|ComObjCreate|ComObjGet|ComObjError|'
             r'ComObjValue|Insert|MinIndex|MaxIndex|Remove|SetCapacity|'
             r'GetCapacity|GetAddress|_NewEnum|FileOpen|Read|Write|ReadLine|'
             r'WriteLine|ReadNumType|WriteNumType|RawRead|RawWrite|Seek|Tell|'
             r'Close|Next|IsObject|StrPut|StrGet|Trim|LTrim|RTrim)\b',
             Name.Function),
        ],
        'builtInVariables': [
            (r'(?i)(A_AhkPath|A_AhkVersion|A_AppData|A_AppDataCommon|'
             r'A_AutoTrim|A_BatchLines|A_CaretX|A_CaretY|A_ComputerName|'
             r'A_ControlDelay|A_Cursor|A_DDDD|A_DDD|A_DD|A_DefaultMouseSpeed|'
             r'A_Desktop|A_DesktopCommon|A_DetectHiddenText|'
             r'A_DetectHiddenWindows|A_EndChar|A_EventInfo|A_ExitReason|'
             r'A_FormatFloat|A_FormatInteger|A_Gui|A_GuiEvent|A_GuiControl|'
             r'A_GuiControlEvent|A_GuiHeight|A_GuiWidth|A_GuiX|A_GuiY|A_Hour|'
             r'A_IconFile|A_IconHidden|A_IconNumber|A_IconTip|A_Index|'
             r'A_IPAddress1|A_IPAddress2|A_IPAddress3|A_IPAddress4|A_ISAdmin|'
             r'A_IsCompiled|A_IsCritical|A_IsPaused|A_IsSuspended|A_KeyDelay|'
             r'A_Language|A_LastError|A_LineFile|A_LineNumber|A_LoopField|'
             r'A_LoopFileAttrib|A_LoopFileDir|A_LoopFileExt|A_LoopFileFullPath|'
             r'A_LoopFileLongPath|A_LoopFileName|A_LoopFileShortName|'
             r'A_LoopFileShortPath|A_LoopFileSize|A_LoopFileSizeKB|'
             r'A_LoopFileSizeMB|A_LoopFileTimeAccessed|A_LoopFileTimeCreated|'
             r'A_LoopFileTimeModified|A_LoopReadLine|A_LoopRegKey|'
             r'A_LoopRegName|A_LoopRegSubkey|A_LoopRegTimeModified|'
             r'A_LoopRegType|A_MDAY|A_Min|A_MM|A_MMM|A_MMMM|A_Mon|A_MouseDelay|'
             r'A_MSec|A_MyDocuments|A_Now|A_NowUTC|A_NumBatchLines|A_OSType|'
             r'A_OSVersion|A_PriorHotkey|A_ProgramFiles|A_Programs|'
             r'A_ProgramsCommon|A_ScreenHeight|A_ScreenWidth|A_ScriptDir|'
             r'A_ScriptFullPath|A_ScriptName|A_Sec|A_Space|A_StartMenu|'
             r'A_StartMenuCommon|A_Startup|A_StartupCommon|A_StringCaseSense|'
             r'A_Tab|A_Temp|A_ThisFunc|A_ThisHotkey|A_ThisLabel|A_ThisMenu|'
             r'A_ThisMenuItem|A_ThisMenuItemPos|A_TickCount|A_TimeIdle|'
             r'A_TimeIdlePhysical|A_TimeSincePriorHotkey|A_TimeSinceThisHotkey|'
             r'A_TitleMatchMode|A_TitleMatchModeSpeed|A_UserName|A_WDay|'
             r'A_WinDelay|A_WinDir|A_WorkingDir|A_YDay|A_YEAR|A_YWeek|A_YYYY|'
             r'Clipboard|ClipboardAll|ComSpec|ErrorLevel|ProgramFiles|True|'
             r'False|A_IsUnicode|A_FileEncoding|A_OSVersion|A_PtrSize)\b',
             Name.Variable),
        ],
        'labels': [
            # hotkeys and labels
            # technically, hotkey names are limited to named keys and buttons
            (r'(^\s*)([^:\s("]+?:{1,2})', bygroups(Text, Name.Label)),
            (r'(^\s*)(::[^:\s]+?::)', bygroups(Text, Name.Label)),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+', Number.Float),
            (r'0\d+', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+', Number.Integer)
        ],
        'stringescape': [
            (r'\"\"|\`([,%`abfnrtv])', String.Escape),
        ],
        'strings': [
            (r'[^"\n]+', String),
        ],
        'dqs': [
            (r'"', String, '#pop'),
            include('strings')
        ],
        'garbage': [
            (r'[^\S\n]', Text),
            # (r'.', Text),      # no cheating
        ],
    }


class AutoItLexer(RegexLexer):
    """
    For AutoIt files.

    AutoIt is a freeware BASIC-like scripting language
    designed for automating the Windows GUI and general scripting
    """
    name = 'AutoIt'
    url = 'http://www.autoitscript.com/site/autoit/'
    aliases = ['autoit']
    filenames = ['*.au3']
    mimetypes = ['text/x-autoit']
    version_added = '1.6'

    # Keywords, functions, macros from au3.keywords.properties
    # which can be found in AutoIt installed directory, e.g.
    # c:\Program Files (x86)\AutoIt3\SciTE\au3.keywords.properties

    keywords = """\
    #include-once #include #endregion #forcedef #forceref #region
    and byref case continueloop dim do else elseif endfunc endif
    endselect exit exitloop for func global
    if local next not or return select step
    then to until wend while exit""".split()

    functions = """\
    abs acos adlibregister adlibunregister asc ascw asin assign atan
    autoitsetoption autoitwingettitle autoitwinsettitle beep binary binarylen
    binarymid binarytostring bitand bitnot bitor bitrotate bitshift bitxor
    blockinput break call cdtray ceiling chr chrw clipget clipput consoleread
    consolewrite consolewriteerror controlclick controlcommand controldisable
    controlenable controlfocus controlgetfocus controlgethandle controlgetpos
    controlgettext controlhide controllistview controlmove controlsend
    controlsettext controlshow controltreeview cos dec dircopy dircreate
    dirgetsize dirmove dirremove dllcall dllcalladdress dllcallbackfree
    dllcallbackgetptr dllcallbackregister dllclose dllopen dllstructcreate
    dllstructgetdata dllstructgetptr dllstructgetsize dllstructsetdata
    drivegetdrive drivegetfilesystem drivegetlabel drivegetserial drivegettype
    drivemapadd drivemapdel drivemapget drivesetlabel drivespacefree
    drivespacetotal drivestatus envget envset envupdate eval execute exp
    filechangedir fileclose filecopy filecreatentfslink filecreateshortcut
    filedelete fileexists filefindfirstfile filefindnextfile fileflush
    filegetattrib filegetencoding filegetlongname filegetpos filegetshortcut
    filegetshortname filegetsize filegettime filegetversion fileinstall filemove
    fileopen fileopendialog fileread filereadline filerecycle filerecycleempty
    filesavedialog fileselectfolder filesetattrib filesetpos filesettime
    filewrite filewriteline floor ftpsetproxy guicreate guictrlcreateavi
    guictrlcreatebutton guictrlcreatecheckbox guictrlcreatecombo
    guictrlcreatecontextmenu guictrlcreatedate guictrlcreatedummy
    guictrlcreateedit guictrlcreategraphic guictrlcreategroup guictrlcreateicon
    guictrlcreateinput guictrlcreatelabel guictrlcreatelist
    guictrlcreatelistview guictrlcreatelistviewitem guictrlcreatemenu
    guictrlcreatemenuitem guictrlcreatemonthcal guictrlcreateobj
    guictrlcreatepic guictrlcreateprogress guictrlcreateradio
    guictrlcreateslider guictrlcreatetab guictrlcreatetabitem
    guictrlcreatetreeview guictrlcreatetreeviewitem guictrlcreateupdown
    guictrldelete guictrlgethandle guictrlgetstate guictrlread guictrlrecvmsg
    guictrlregisterlistviewsort guictrlsendmsg guictrlsendtodummy
    guictrlsetbkcolor guictrlsetcolor guictrlsetcursor guictrlsetdata
    guictrlsetdefbkcolor guictrlsetdefcolor guictrlsetfont guictrlsetgraphic
    guictrlsetimage guictrlsetlimit guictrlsetonevent guictrlsetpos
    guictrlsetresizing guictrlsetstate guictrlsetstyle guictrlsettip guidelete
    guigetcursorinfo guigetmsg guigetstyle guiregistermsg guisetaccelerators
    guisetbkcolor guisetcoord guisetcursor guisetfont guisethelp guiseticon
    guisetonevent guisetstate guisetstyle guistartgroup guiswitch hex hotkeyset
    httpsetproxy httpsetuseragent hwnd inetclose inetget inetgetinfo inetgetsize
    inetread inidelete iniread inireadsection inireadsectionnames
    inirenamesection iniwrite iniwritesection inputbox int isadmin isarray
    isbinary isbool isdeclared isdllstruct isfloat ishwnd isint iskeyword
    isnumber isobj isptr isstring log memgetstats mod mouseclick mouseclickdrag
    mousedown mousegetcursor mousegetpos mousemove mouseup mousewheel msgbox
    number objcreate objcreateinterface objevent objevent objget objname
    onautoitexitregister onautoitexitunregister opt ping pixelchecksum
    pixelgetcolor pixelsearch pluginclose pluginopen processclose processexists
    processgetstats processlist processsetpriority processwait processwaitclose
    progressoff progresson progressset ptr random regdelete regenumkey
    regenumval regread regwrite round run runas runaswait runwait send
    sendkeepactive seterror setextended shellexecute shellexecutewait shutdown
    sin sleep soundplay soundsetwavevolume splashimageon splashoff splashtexton
    sqrt srandom statusbargettext stderrread stdinwrite stdioclose stdoutread
    string stringaddcr stringcompare stringformat stringfromasciiarray
    stringinstr stringisalnum stringisalpha stringisascii stringisdigit
    stringisfloat stringisint stringislower stringisspace stringisupper
    stringisxdigit stringleft stringlen stringlower stringmid stringregexp
    stringregexpreplace stringreplace stringright stringsplit stringstripcr
    stringstripws stringtoasciiarray stringtobinary stringtrimleft
    stringtrimright stringupper tan tcpaccept tcpclosesocket tcpconnect
    tcplisten tcpnametoip tcprecv tcpsend tcpshutdown tcpstartup timerdiff
    timerinit tooltip traycreateitem traycreatemenu traygetmsg trayitemdelete
    trayitemgethandle trayitemgetstate trayitemgettext trayitemsetonevent
    trayitemsetstate trayitemsettext traysetclick trayseticon traysetonevent
    traysetpauseicon traysetstate traysettooltip traytip ubound udpbind
    udpclosesocket udpopen udprecv udpsend udpshutdown udpstartup vargettype
    winactivate winactive winclose winexists winflash wingetcaretpos
    wingetclasslist wingetclientsize wingethandle wingetpos wingetprocess
    wingetstate wingettext wingettitle winkill winlist winmenuselectitem
    winminimizeall winminimizeallundo winmove winsetontop winsetstate
    winsettitle winsettrans winwait winwaitactive winwaitclose
    winwaitnotactive""".split()

    macros = """\
    @appdatacommondir @appdatadir @autoitexe @autoitpid @autoitversion
    @autoitx64 @com_eventobj @commonfilesdir @compiled @computername @comspec
    @cpuarch @cr @crlf @desktopcommondir @desktopdepth @desktopdir
    @desktopheight @desktoprefresh @desktopwidth @documentscommondir @error
    @exitcode @exitmethod @extended @favoritescommondir @favoritesdir
    @gui_ctrlhandle @gui_ctrlid @gui_dragfile @gui_dragid @gui_dropid
    @gui_winhandle @homedrive @homepath @homeshare @hotkeypressed @hour
    @ipaddress1 @ipaddress2 @ipaddress3 @ipaddress4 @kblayout @lf
    @logondnsdomain @logondomain @logonserver @mday @min @mon @msec @muilang
    @mydocumentsdir @numparams @osarch @osbuild @oslang @osservicepack @ostype
    @osversion @programfilesdir @programscommondir @programsdir @scriptdir
    @scriptfullpath @scriptlinenumber @scriptname @sec @startmenucommondir
    @startmenudir @startupcommondir @startupdir @sw_disable @sw_enable @sw_hide
    @sw_lock @sw_maximize @sw_minimize @sw_restore @sw_show @sw_showdefault
    @sw_showmaximized @sw_showminimized @sw_showminnoactive @sw_showna
    @sw_shownoactivate @sw_shownormal @sw_unlock @systemdir @tab @tempdir
    @tray_id @trayiconflashing @trayiconvisible @username @userprofiledir @wday
    @windowsdir @workingdir @yday @year""".split()

    tokens = {
        'root': [
            (r';.*\n', Comment.Single),
            (r'(#comments-start|#cs)(.|\n)*?(#comments-end|#ce)',
             Comment.Multiline),
            (r'[\[\]{}(),;]', Punctuation),
            (r'(and|or|not)\b', Operator.Word),
            (r'[$|@][a-zA-Z_]\w*', Name.Variable),
            (r'!=|==|:=|\.=|<<|>>|[-~+/*%=<>&^|?:!.]', Operator),
            include('commands'),
            include('labels'),
            include('builtInFunctions'),
            include('builtInMarcros'),
            (r'"', String, combined('stringescape', 'dqs')),
            (r"'", String, 'sqs'),
            include('numbers'),
            (r'[a-zA-Z_#@$][\w#@$]*', Name),
            (r'\\|\'', Text),
            (r'\`([,%`abfnrtv\-+;])', String.Escape),
            (r'_\n', Text),  # Line continuation
            include('garbage'),
        ],
        'commands': [
            (r'(?i)(\s*)({})\b'.format('|'.join(keywords)),
             bygroups(Text, Name.Builtin)),
        ],
        'builtInFunctions': [
            (r'(?i)({})\b'.format('|'.join(functions)),
             Name.Function),
        ],
        'builtInMarcros': [
            (r'(?i)({})\b'.format('|'.join(macros)),
             Name.Variable.Global),
        ],
        'labels': [
            # sendkeys
            (r'(^\s*)(\{\S+?\})', bygroups(Text, Name.Label)),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+', Number.Float),
            (r'0\d+', Number.Oct),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+', Number.Integer)
        ],
        'stringescape': [
            (r'\"\"|\`([,%`abfnrtv])', String.Escape),
        ],
        'strings': [
            (r'[^"\n]+', String),
        ],
        'dqs': [
            (r'"', String, '#pop'),
            include('strings')
        ],
        'sqs': [
            (r'\'\'|\`([,%`abfnrtv])', String.Escape),
            (r"'", String, '#pop'),
            (r"[^'\n]+", String)
        ],
        'garbage': [
            (r'[^\S\n]', Text),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\document.py ===
# We no longer support the old, non-colour editor!

import os
import shutil
import traceback

import win32api
import win32con
import win32ui
from pywin.framework.editor import GetEditorOption

BAK_NONE = 0
BAK_DOT_BAK = 1
BAK_DOT_BAK_TEMP_DIR = 2
BAK_DOT_BAK_BAK_DIR = 3

MSG_CHECK_EXTERNAL_FILE = (
    win32con.WM_USER + 1999
)  ## WARNING: Duplicated in editor.py and coloreditor.py

import pywin.scintilla.document

ParentEditorDocument = pywin.scintilla.document.CScintillaDocument


class EditorDocumentBase(ParentEditorDocument):
    def __init__(self, template):
        self.bAutoReload = GetEditorOption("Auto Reload", 1)
        self.bDeclinedReload = 0  # Has the user declined to reload.
        self.fileStat = None
        self.bReportedFileNotFound = 0

        # what sort of bak file should I create.
        # default to write to %temp%/bak/filename.ext
        self.bakFileType = GetEditorOption("Backup Type", BAK_DOT_BAK_BAK_DIR)

        self.watcherThread = FileWatchingThread(self)
        self.watcherThread.CreateThread()
        # Should I try and use VSS integration?
        self.scModuleName = GetEditorOption("Source Control Module", "")
        self.scModule = None  # Loaded when first used.
        ParentEditorDocument.__init__(self, template, template.CreateWin32uiDocument())

    def OnCloseDocument(self):
        self.watcherThread.SignalStop()
        return self._obj_.OnCloseDocument()

    # 	def OnOpenDocument(self, name):
    # 		rc = ParentEditorDocument.OnOpenDocument(self, name)
    # 		self.GetFirstView()._SetLoadedText(self.text)
    # 		self._DocumentStateChanged()
    # 		return rc

    def OnSaveDocument(self, fileName):
        win32ui.SetStatusText("Saving file...", 1)
        # rename to bak if required.
        dir, basename = os.path.split(fileName)
        if self.bakFileType == BAK_DOT_BAK:
            bakFileName = dir + "\\" + os.path.splitext(basename)[0] + ".bak"
        elif self.bakFileType == BAK_DOT_BAK_TEMP_DIR:
            bakFileName = (
                win32api.GetTempPath() + "\\" + os.path.splitext(basename)[0] + ".bak"
            )
        elif self.bakFileType == BAK_DOT_BAK_BAK_DIR:
            tempPath = os.path.join(win32api.GetTempPath(), "bak")
            try:
                os.mkdir(tempPath, 0)
            except OSError:
                pass
            bakFileName = os.path.join(tempPath, basename)
        try:
            os.unlink(bakFileName)  # raise NameError if no bakups wanted.
        except (OSError, NameError):
            pass
        try:
            # Do a copy as it might be on different volumes,
            # and the file may be a hard-link, causing the link
            # to follow the backup.
            shutil.copy2(fileName, bakFileName)
        except (OSError, NameError):
            pass
        try:
            self.SaveFile(fileName)
        except OSError as details:
            win32ui.MessageBox("Error - could not save file\r\n\r\n%s" % details)
            return 0
        except (UnicodeEncodeError, LookupError) as details:
            rc = win32ui.MessageBox(
                "Encoding failed: \r\n%s" % details
                + "\r\nPlease add desired source encoding as first line of file, eg \r\n"
                + "# -*- coding: mbcs -*-\r\n\r\n"
                + "If you continue, the file will be saved as binary and will\r\n"
                + "not be valid in the declared encoding.\r\n\r\n"
                + "Save the file as binary with an invalid encoding?",
                "File save failed",
                win32con.MB_YESNO | win32con.MB_DEFBUTTON2,
            )
            if rc == win32con.IDYES:
                try:
                    self.SaveFile(fileName, encoding="latin-1")
                except OSError as details:
                    win32ui.MessageBox(
                        "Error - could not save file\r\n\r\n%s" % details
                    )
                    return 0
            else:
                return 0
        self.SetModifiedFlag(0)  # No longer dirty
        self.bDeclinedReload = 0  # They probably want to know if it changes again!
        win32ui.AddToRecentFileList(fileName)
        self.SetPathName(fileName)
        win32ui.SetStatusText("Ready")
        self._DocumentStateChanged()
        return 1

    def FinalizeViewCreation(self, view):
        ParentEditorDocument.FinalizeViewCreation(self, view)
        if view == self.GetFirstView():
            self._DocumentStateChanged()
            if view.bFolding and GetEditorOption("Fold On Open", 0):
                view.FoldTopLevelEvent()

    def HookViewNotifications(self, view):
        ParentEditorDocument.HookViewNotifications(self, view)

    # Support for reloading the document from disk - presumably after some
    # external application has modified it (or possibly source control has
    # checked it out.
    def ReloadDocument(self):
        """Reloads the document from disk.  Assumes the file has
        been saved and user has been asked if necessary - it just does it!
        """
        win32ui.SetStatusText("Reloading document.  Please wait...", 1)
        self.SetModifiedFlag(0)
        # Loop over all views, saving their state, then reload the document
        views = self.GetAllViews()
        states = []
        for view in views:
            try:
                info = view._PrepareUserStateChange()
            except AttributeError:  # Not our editor view?
                info = None
            states.append(info)
        self.OnOpenDocument(self.GetPathName())
        for view, info in zip(views, states):
            if info is not None:
                view._EndUserStateChange(info)
        self._DocumentStateChanged()
        win32ui.SetStatusText("Document reloaded.")

    # Reloading the file
    def CheckExternalDocumentUpdated(self):
        if self.bDeclinedReload or not self.GetPathName():
            return
        try:
            newstat = os.stat(self.GetPathName())
        except OSError as exc:
            if not self.bReportedFileNotFound:
                print(
                    "The file '{}' is open for editing, but\nchecking it for changes caused the error: {}".format(
                        self.GetPathName(), exc.strerror
                    )
                )
                self.bReportedFileNotFound = 1
            return
        if self.bReportedFileNotFound:
            print(
                "The file '{}' has re-appeared - continuing to watch for changes...".format(
                    self.GetPathName()
                )
            )
            self.bReportedFileNotFound = (
                0  # Once found again we want to start complaining.
            )
        changed = (
            (self.fileStat is None)
            or self.fileStat[0] != newstat[0]
            or self.fileStat[6] != newstat[6]
            or self.fileStat[8] != newstat[8]
            or self.fileStat[9] != newstat[9]
        )
        if changed:
            question = None
            if self.IsModified():
                question = (
                    "%s\r\n\r\nThis file has been modified outside of the source editor.\r\nDo you want to reload it and LOSE THE CHANGES in the source editor?"
                    % self.GetPathName()
                )
                mbStyle = win32con.MB_YESNO | win32con.MB_DEFBUTTON2  # Default to "No"
            else:
                if not self.bAutoReload:
                    question = (
                        "%s\r\n\r\nThis file has been modified outside of the source editor.\r\nDo you want to reload it?"
                        % self.GetPathName()
                    )
                    mbStyle = win32con.MB_YESNO  # Default to "Yes"
            if question:
                rc = win32ui.MessageBox(question, None, mbStyle)
                if rc != win32con.IDYES:
                    self.bDeclinedReload = 1
                    return
            self.ReloadDocument()

    def _DocumentStateChanged(self):
        """Called whenever the documents state (on disk etc) has been changed
        by the editor (eg, as the result of a save operation)
        """
        if self.GetPathName():
            try:
                self.fileStat = os.stat(self.GetPathName())
            except OSError:
                self.fileStat = None
        else:
            self.fileStat = None
        self.watcherThread._DocumentStateChanged()
        self._UpdateUIForState()
        self._ApplyOptionalToViews("_UpdateUIForState")
        self._ApplyOptionalToViews("SetReadOnly", self._IsReadOnly())
        self._ApplyOptionalToViews("SCISetSavePoint")
        # Allow the debugger to reset us too.
        import pywin.debugger

        if pywin.debugger.currentDebugger is not None:
            pywin.debugger.currentDebugger.UpdateDocumentLineStates(self)

    # Read-only document support - make it obvious to the user
    # that the file is read-only.
    def _IsReadOnly(self):
        return self.fileStat is not None and (self.fileStat[0] & 128) == 0

    def _UpdateUIForState(self):
        """Change the title to reflect the state of the document -
        eg ReadOnly, Dirty, etc
        """
        filename = self.GetPathName()
        if not filename:
            return  # New file - nothing to do
        try:
            # This seems necessary so the internal state of the window becomes
            # "visible".  without it, it is still shown, but certain functions
            # (such as updating the title) don't immediately work?
            self.GetFirstView().ShowWindow(win32con.SW_SHOW)
            title = win32ui.GetFileTitle(filename)
        except win32ui.error:
            title = filename
        if self._IsReadOnly():
            title += " (read-only)"
        self.SetTitle(title)

    def MakeDocumentWritable(self):
        pretend_ss = 0  # Set to 1 to test this without source safe :-)
        if not self.scModuleName and not pretend_ss:  # No Source Control support.
            win32ui.SetStatusText(
                "Document is read-only, and no source-control system is configured"
            )
            win32api.MessageBeep()
            return 0

        # We have source control support - check if the user wants to use it.
        msg = "Would you like to check this file out?"
        defButton = win32con.MB_YESNO
        if self.IsModified():
            msg += "\r\n\r\nALL CHANGES IN THE EDITOR WILL BE LOST"
            defButton = win32con.MB_YESNO
        if win32ui.MessageBox(msg, None, defButton) != win32con.IDYES:
            return 0

        if pretend_ss:
            print("We are only pretending to check it out!")
            win32api.SetFileAttributes(
                self.GetPathName(), win32con.FILE_ATTRIBUTE_NORMAL
            )
            self.ReloadDocument()
            return 1

        # Now call on the module to do it.
        if self.scModule is None:
            try:
                self.scModule = __import__(self.scModuleName)
                for part in self.scModuleName.split(".")[1:]:
                    self.scModule = getattr(self.scModule, part)
            except:
                traceback.print_exc()
                print("Error loading source control module.")
                return 0

        if self.scModule.CheckoutFile(self.GetPathName()):
            self.ReloadDocument()
            return 1
        return 0

    def CheckMakeDocumentWritable(self):
        if self._IsReadOnly():
            return self.MakeDocumentWritable()
        return 1

    def SaveModified(self):
        # Called as the document is closed.  If we are about
        # to prompt for a save, bring the document to the foreground.
        if self.IsModified():
            frame = self.GetFirstView().GetParentFrame()
            try:
                frame.MDIActivate()
                frame.AutoRestore()
            except:
                print("Could not bring document to foreground")
        return self._obj_.SaveModified()


# NOTE - I DONT use the standard threading module,
# as this waits for all threads to terminate at shutdown.
# When using the debugger, it is possible shutdown will
# occur without Pythonwin getting a complete shutdown,
# so we deadlock at the end - threading is waiting for
import pywin.mfc.thread
import win32event


class FileWatchingThread(pywin.mfc.thread.WinThread):
    def __init__(self, doc):
        self.doc = doc
        self.adminEvent = win32event.CreateEvent(None, 0, 0, None)
        self.stopEvent = win32event.CreateEvent(None, 0, 0, None)
        self.watchEvent = None
        pywin.mfc.thread.WinThread.__init__(self)

    def _DocumentStateChanged(self):
        win32event.SetEvent(self.adminEvent)

    def RefreshEvent(self):
        self.hwnd = self.doc.GetFirstView().GetSafeHwnd()
        if self.watchEvent is not None:
            win32api.FindCloseChangeNotification(self.watchEvent)
            self.watchEvent = None
        path = self.doc.GetPathName()
        if path:
            path = os.path.dirname(path)
        if path:
            filter = (
                win32con.FILE_NOTIFY_CHANGE_FILE_NAME
                | win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES
                | win32con.FILE_NOTIFY_CHANGE_LAST_WRITE
            )
            try:
                self.watchEvent = win32api.FindFirstChangeNotification(path, 0, filter)
            except win32api.error as exc:
                print("Can not watch file", path, "for changes -", exc.strerror)

    def SignalStop(self):
        win32event.SetEvent(self.stopEvent)

    def Run(self):
        while 1:
            handles = [self.stopEvent, self.adminEvent]
            if self.watchEvent is not None:
                handles.append(self.watchEvent)
            rc = win32event.WaitForMultipleObjects(handles, 0, win32event.INFINITE)
            if rc == win32event.WAIT_OBJECT_0:
                break
            elif rc == win32event.WAIT_OBJECT_0 + 1:
                self.RefreshEvent()
            else:
                win32api.PostMessage(self.hwnd, MSG_CHECK_EXTERNAL_FILE, 0, 0)
                try:
                    # If the directory has been removed underneath us, we get this error.
                    win32api.FindNextChangeNotification(self.watchEvent)
                except win32api.error as exc:
                    print(
                        "Can not watch file",
                        self.doc.GetPathName(),
                        "for changes -",
                        exc.strerror,
                    )
                    break

        # close a circular reference
        self.doc = None
        if self.watchEvent:
            win32api.FindCloseChangeNotification(self.watchEvent)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\action_chains.py ===
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
"""The ActionChains implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

from selenium.webdriver.remote.webelement import WebElement

from .actions.action_builder import ActionBuilder
from .actions.key_input import KeyInput
from .actions.pointer_input import PointerInput
from .actions.wheel_input import ScrollOrigin, WheelInput
from .utils import keys_to_typing

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

AnyDevice = Union[PointerInput, KeyInput, WheelInput]


class ActionChains:
    """ActionChains are a way to automate low level interactions such as mouse
    movements, mouse button actions, key press, and context menu interactions.
    This is useful for doing more complex actions like hover over and drag and
    drop.

    Generate user actions.
       When you call methods for actions on the ActionChains object,
       the actions are stored in a queue in the ActionChains object.
       When you call perform(), the events are fired in the order they
       are queued up.

    ActionChains can be used in a chain pattern::

        menu = driver.find_element(By.CSS_SELECTOR, ".nav")
        hidden_submenu = driver.find_element(By.CSS_SELECTOR, ".nav #submenu1")

        ActionChains(driver).move_to_element(menu).click(hidden_submenu).perform()

    Or actions can be queued up one by one, then performed.::

        menu = driver.find_element(By.CSS_SELECTOR, ".nav")
        hidden_submenu = driver.find_element(By.CSS_SELECTOR, ".nav #submenu1")

        actions = ActionChains(driver)
        actions.move_to_element(menu)
        actions.click(hidden_submenu)
        actions.perform()

    Either way, the actions are performed in the order they are called, one after
    another.
    """

    def __init__(self, driver: WebDriver, duration: int = 250, devices: list[AnyDevice] | None = None) -> None:
        """Creates a new ActionChains.

        :Args:
         - driver: The WebDriver instance which performs user actions.
         - duration: override the default 250 msecs of DEFAULT_MOVE_DURATION in PointerInput
        """
        self._driver = driver
        mouse = None
        keyboard = None
        wheel = None
        if devices is not None and isinstance(devices, list):
            for device in devices:
                if isinstance(device, PointerInput):
                    mouse = device
                if isinstance(device, KeyInput):
                    keyboard = device
                if isinstance(device, WheelInput):
                    wheel = device
        self.w3c_actions = ActionBuilder(driver, mouse=mouse, keyboard=keyboard, wheel=wheel, duration=duration)

    def perform(self) -> None:
        """Performs all stored actions."""
        self.w3c_actions.perform()

    def reset_actions(self) -> None:
        """Clears actions that are already stored locally and on the remote
        end."""
        self.w3c_actions.clear_actions()
        for device in self.w3c_actions.devices:
            device.clear_actions()

    def click(self, on_element: WebElement | None = None) -> ActionChains:
        """Clicks an element.

        :Args:
         - on_element: The element to click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.click()
        self.w3c_actions.key_action.pause()
        self.w3c_actions.key_action.pause()

        return self

    def click_and_hold(self, on_element: WebElement | None = None) -> ActionChains:
        """Holds down the left mouse button on an element.

        :Args:
         - on_element: The element to mouse down.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.click_and_hold()
        self.w3c_actions.key_action.pause()

        return self

    def context_click(self, on_element: WebElement | None = None) -> ActionChains:
        """Performs a context-click (right click) on an element.

        :Args:
         - on_element: The element to context-click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.context_click()
        self.w3c_actions.key_action.pause()
        self.w3c_actions.key_action.pause()

        return self

    def double_click(self, on_element: WebElement | None = None) -> ActionChains:
        """Double-clicks an element.

        :Args:
         - on_element: The element to double-click.
           If None, clicks on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.double_click()
        for _ in range(4):
            self.w3c_actions.key_action.pause()

        return self

    def drag_and_drop(self, source: WebElement, target: WebElement) -> ActionChains:
        """Holds down the left mouse button on the source element, then moves
        to the target element and releases the mouse button.

        :Args:
         - source: The element to mouse down.
         - target: The element to mouse up.
        """
        self.click_and_hold(source)
        self.release(target)
        return self

    def drag_and_drop_by_offset(self, source: WebElement, xoffset: int, yoffset: int) -> ActionChains:
        """Holds down the left mouse button on the source element, then moves
        to the target offset and releases the mouse button.

        :Args:
         - source: The element to mouse down.
         - xoffset: X offset to move to.
         - yoffset: Y offset to move to.
        """
        self.click_and_hold(source)
        self.move_by_offset(xoffset, yoffset)
        self.release()
        return self

    def key_down(self, value: str, element: WebElement | None = None) -> ActionChains:
        """Sends a key press only, without releasing it. Should only be used
        with modifier keys (Control, Alt and Shift).

        :Args:
         - value: The modifier key to send. Values are defined in `Keys` class.
         - element: The element to send keys.
           If None, sends a key to current focused element.

        Example, pressing ctrl+c::

            ActionChains(driver).key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()
        """
        if element:
            self.click(element)

        self.w3c_actions.key_action.key_down(value)
        self.w3c_actions.pointer_action.pause()

        return self

    def key_up(self, value: str, element: WebElement | None = None) -> ActionChains:
        """Releases a modifier key.

        :Args:
         - value: The modifier key to send. Values are defined in Keys class.
         - element: The element to send keys.
           If None, sends a key to current focused element.

        Example, pressing ctrl+c::

            ActionChains(driver).key_down(Keys.CONTROL).send_keys("c").key_up(Keys.CONTROL).perform()
        """
        if element:
            self.click(element)

        self.w3c_actions.key_action.key_up(value)
        self.w3c_actions.pointer_action.pause()

        return self

    def move_by_offset(self, xoffset: int, yoffset: int) -> ActionChains:
        """Moving the mouse to an offset from current mouse position.

        :Args:
         - xoffset: X offset to move to, as a positive or negative integer.
         - yoffset: Y offset to move to, as a positive or negative integer.
        """

        self.w3c_actions.pointer_action.move_by(xoffset, yoffset)
        self.w3c_actions.key_action.pause()

        return self

    def move_to_element(self, to_element: WebElement) -> ActionChains:
        """Moving the mouse to the middle of an element.

        :Args:
         - to_element: The WebElement to move to.
        """

        self.w3c_actions.pointer_action.move_to(to_element)
        self.w3c_actions.key_action.pause()

        return self

    def move_to_element_with_offset(self, to_element: WebElement, xoffset: int, yoffset: int) -> ActionChains:
        """Move the mouse by an offset of the specified element. Offsets are
        relative to the in-view center point of the element.

        :Args:
         - to_element: The WebElement to move to.
         - xoffset: X offset to move to, as a positive or negative integer.
         - yoffset: Y offset to move to, as a positive or negative integer.
        """

        self.w3c_actions.pointer_action.move_to(to_element, int(xoffset), int(yoffset))
        self.w3c_actions.key_action.pause()

        return self

    def pause(self, seconds: float | int) -> ActionChains:
        """Pause all inputs for the specified duration in seconds."""

        self.w3c_actions.pointer_action.pause(seconds)
        self.w3c_actions.key_action.pause(seconds)

        return self

    def release(self, on_element: WebElement | None = None) -> ActionChains:
        """Releasing a held mouse button on an element.

        :Args:
         - on_element: The element to mouse up.
           If None, releases on current mouse position.
        """
        if on_element:
            self.move_to_element(on_element)

        self.w3c_actions.pointer_action.release()
        self.w3c_actions.key_action.pause()

        return self

    def send_keys(self, *keys_to_send: str) -> ActionChains:
        """Sends keys to current focused element.

        :Args:
         - keys_to_send: The keys to send.  Modifier keys constants can be found in the
           'Keys' class.
        """
        typing = keys_to_typing(keys_to_send)

        for key in typing:
            self.key_down(key)
            self.key_up(key)

        return self

    def send_keys_to_element(self, element: WebElement, *keys_to_send: str) -> ActionChains:
        """Sends keys to an element.

        :Args:
         - element: The element to send keys.
         - keys_to_send: The keys to send.  Modifier keys constants can be found in the
           'Keys' class.
        """
        self.click(element)
        self.send_keys(*keys_to_send)
        return self

    def scroll_to_element(self, element: WebElement) -> ActionChains:
        """If the element is outside the viewport, scrolls the bottom of the
        element to the bottom of the viewport.

        :Args:
         - element: Which element to scroll into the viewport.
        """

        self.w3c_actions.wheel_action.scroll(origin=element)
        return self

    def scroll_by_amount(self, delta_x: int, delta_y: int) -> ActionChains:
        """Scrolls by provided amounts with the origin in the top left corner
        of the viewport.

        :Args:
         - delta_x: Distance along X axis to scroll using the wheel. A negative value scrolls left.
         - delta_y: Distance along Y axis to scroll using the wheel. A negative value scrolls up.
        """

        self.w3c_actions.wheel_action.scroll(delta_x=delta_x, delta_y=delta_y)
        return self

    def scroll_from_origin(self, scroll_origin: ScrollOrigin, delta_x: int, delta_y: int) -> ActionChains:
        """Scrolls by provided amount based on a provided origin. The scroll
        origin is either the center of an element or the upper left of the
        viewport plus any offsets. If the origin is an element, and the element
        is not in the viewport, the bottom of the element will first be
        scrolled to the bottom of the viewport.

        :Args:
         - origin: Where scroll originates (viewport or element center) plus provided offsets.
         - delta_x: Distance along X axis to scroll using the wheel. A negative value scrolls left.
         - delta_y: Distance along Y axis to scroll using the wheel. A negative value scrolls up.

         :Raises: If the origin with offset is outside the viewport.
          - MoveTargetOutOfBoundsException - If the origin with offset is outside the viewport.
        """

        if not isinstance(scroll_origin, ScrollOrigin):
            raise TypeError(f"Expected object of type ScrollOrigin, got: {type(scroll_origin)}")

        self.w3c_actions.wheel_action.scroll(
            origin=scroll_origin.origin,
            x=scroll_origin.x_offset,
            y=scroll_origin.y_offset,
            delta_x=delta_x,
            delta_y=delta_y,
        )
        return self

    # Context manager so ActionChains can be used in a 'with .. as' statements.

    def __enter__(self) -> ActionChains:
        return self  # Return created instance of self.

    def __exit__(self, _type, _value, _traceback) -> None:
        pass  # Do nothing, does not require additional cleanup.

# === NexusCore/openenv\Lib\site-packages\aiohttp\http_writer.py ===
"""Http related parsers and protocol."""

import asyncio
import sys
from typing import (  # noqa
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Union,
)

from multidict import CIMultiDict

from .abc import AbstractStreamWriter
from .base_protocol import BaseProtocol
from .client_exceptions import ClientConnectionResetError
from .compression_utils import ZLibCompressor
from .helpers import NO_EXTENSIONS

__all__ = ("StreamWriter", "HttpVersion", "HttpVersion10", "HttpVersion11")


MIN_PAYLOAD_FOR_WRITELINES = 2048
IS_PY313_BEFORE_313_2 = (3, 13, 0) <= sys.version_info < (3, 13, 2)
IS_PY_BEFORE_312_9 = sys.version_info < (3, 12, 9)
SKIP_WRITELINES = IS_PY313_BEFORE_313_2 or IS_PY_BEFORE_312_9
# writelines is not safe for use
# on Python 3.12+ until 3.12.9
# on Python 3.13+ until 3.13.2
# and on older versions it not any faster than write
# CVE-2024-12254: https://github.com/python/cpython/pull/127656


class HttpVersion(NamedTuple):
    major: int
    minor: int


HttpVersion10 = HttpVersion(1, 0)
HttpVersion11 = HttpVersion(1, 1)


_T_OnChunkSent = Optional[Callable[[bytes], Awaitable[None]]]
_T_OnHeadersSent = Optional[Callable[["CIMultiDict[str]"], Awaitable[None]]]


class StreamWriter(AbstractStreamWriter):

    length: Optional[int] = None
    chunked: bool = False
    _eof: bool = False
    _compress: Optional[ZLibCompressor] = None

    def __init__(
        self,
        protocol: BaseProtocol,
        loop: asyncio.AbstractEventLoop,
        on_chunk_sent: _T_OnChunkSent = None,
        on_headers_sent: _T_OnHeadersSent = None,
    ) -> None:
        self._protocol = protocol
        self.loop = loop
        self._on_chunk_sent: _T_OnChunkSent = on_chunk_sent
        self._on_headers_sent: _T_OnHeadersSent = on_headers_sent
        self._headers_buf: Optional[bytes] = None
        self._headers_written: bool = False

    @property
    def transport(self) -> Optional[asyncio.Transport]:
        return self._protocol.transport

    @property
    def protocol(self) -> BaseProtocol:
        return self._protocol

    def enable_chunking(self) -> None:
        self.chunked = True

    def enable_compression(
        self, encoding: str = "deflate", strategy: Optional[int] = None
    ) -> None:
        self._compress = ZLibCompressor(encoding=encoding, strategy=strategy)

    def _write(self, chunk: Union[bytes, bytearray, memoryview]) -> None:
        size = len(chunk)
        self.buffer_size += size
        self.output_size += size
        transport = self._protocol.transport
        if transport is None or transport.is_closing():
            raise ClientConnectionResetError("Cannot write to closing transport")
        transport.write(chunk)

    def _writelines(self, chunks: Iterable[bytes]) -> None:
        size = 0
        for chunk in chunks:
            size += len(chunk)
        self.buffer_size += size
        self.output_size += size
        transport = self._protocol.transport
        if transport is None or transport.is_closing():
            raise ClientConnectionResetError("Cannot write to closing transport")
        if SKIP_WRITELINES or size < MIN_PAYLOAD_FOR_WRITELINES:
            transport.write(b"".join(chunks))
        else:
            transport.writelines(chunks)

    def _write_chunked_payload(
        self, chunk: Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"]
    ) -> None:
        """Write a chunk with proper chunked encoding."""
        chunk_len_pre = f"{len(chunk):x}\r\n".encode("ascii")
        self._writelines((chunk_len_pre, chunk, b"\r\n"))

    def _send_headers_with_payload(
        self,
        chunk: Union[bytes, bytearray, "memoryview[int]", "memoryview[bytes]"],
        is_eof: bool,
    ) -> None:
        """Send buffered headers with payload, coalescing into single write."""
        # Mark headers as written
        self._headers_written = True
        headers_buf = self._headers_buf
        self._headers_buf = None

        if TYPE_CHECKING:
            # Safe because callers (write() and write_eof()) only invoke this method
            # after checking that self._headers_buf is truthy
            assert headers_buf is not None

        if not self.chunked:
            # Non-chunked: coalesce headers with body
            if chunk:
                self._writelines((headers_buf, chunk))
            else:
                self._write(headers_buf)
            return

        # Coalesce headers with chunked data
        if chunk:
            chunk_len_pre = f"{len(chunk):x}\r\n".encode("ascii")
            if is_eof:
                self._writelines((headers_buf, chunk_len_pre, chunk, b"\r\n0\r\n\r\n"))
            else:
                self._writelines((headers_buf, chunk_len_pre, chunk, b"\r\n"))
        elif is_eof:
            self._writelines((headers_buf, b"0\r\n\r\n"))
        else:
            self._write(headers_buf)

    async def write(
        self,
        chunk: Union[bytes, bytearray, memoryview],
        *,
        drain: bool = True,
        LIMIT: int = 0x10000,
    ) -> None:
        """
        Writes chunk of data to a stream.

        write_eof() indicates end of stream.
        writer can't be used after write_eof() method being called.
        write() return drain future.
        """
        if self._on_chunk_sent is not None:
            await self._on_chunk_sent(chunk)

        if isinstance(chunk, memoryview):
            if chunk.nbytes != len(chunk):
                # just reshape it
                chunk = chunk.cast("c")

        if self._compress is not None:
            chunk = await self._compress.compress(chunk)
            if not chunk:
                return

        if self.length is not None:
            chunk_len = len(chunk)
            if self.length >= chunk_len:
                self.length = self.length - chunk_len
            else:
                chunk = chunk[: self.length]
                self.length = 0
                if not chunk:
                    return

        # Handle buffered headers for small payload optimization
        if self._headers_buf and not self._headers_written:
            self._send_headers_with_payload(chunk, False)
            if drain and self.buffer_size > LIMIT:
                self.buffer_size = 0
                await self.drain()
            return

        if chunk:
            if self.chunked:
                self._write_chunked_payload(chunk)
            else:
                self._write(chunk)

            if drain and self.buffer_size > LIMIT:
                self.buffer_size = 0
                await self.drain()

    async def write_headers(
        self, status_line: str, headers: "CIMultiDict[str]"
    ) -> None:
        """Write headers to the stream."""
        if self._on_headers_sent is not None:
            await self._on_headers_sent(headers)
        # status + headers
        buf = _serialize_headers(status_line, headers)
        self._headers_written = False
        self._headers_buf = buf

    def send_headers(self) -> None:
        """Force sending buffered headers if not already sent."""
        if not self._headers_buf or self._headers_written:
            return

        self._headers_written = True
        headers_buf = self._headers_buf
        self._headers_buf = None

        if TYPE_CHECKING:
            # Safe because we only enter this block when self._headers_buf is truthy
            assert headers_buf is not None

        self._write(headers_buf)

    def set_eof(self) -> None:
        """Indicate that the message is complete."""
        if self._eof:
            return

        # If headers haven't been sent yet, send them now
        # This handles the case where there's no body at all
        if self._headers_buf and not self._headers_written:
            self._headers_written = True
            headers_buf = self._headers_buf
            self._headers_buf = None

            if TYPE_CHECKING:
                # Safe because we only enter this block when self._headers_buf is truthy
                assert headers_buf is not None

            # Combine headers and chunked EOF marker in a single write
            if self.chunked:
                self._writelines((headers_buf, b"0\r\n\r\n"))
            else:
                self._write(headers_buf)
        elif self.chunked and self._headers_written:
            # Headers already sent, just send the final chunk marker
            self._write(b"0\r\n\r\n")

        self._eof = True

    async def write_eof(self, chunk: bytes = b"") -> None:
        if self._eof:
            return

        if chunk and self._on_chunk_sent is not None:
            await self._on_chunk_sent(chunk)

        # Handle body/compression
        if self._compress:
            chunks: List[bytes] = []
            chunks_len = 0
            if chunk and (compressed_chunk := await self._compress.compress(chunk)):
                chunks_len = len(compressed_chunk)
                chunks.append(compressed_chunk)

            flush_chunk = self._compress.flush()
            chunks_len += len(flush_chunk)
            chunks.append(flush_chunk)
            assert chunks_len

            # Send buffered headers with compressed data if not yet sent
            if self._headers_buf and not self._headers_written:
                self._headers_written = True
                headers_buf = self._headers_buf
                self._headers_buf = None

                if self.chunked:
                    # Coalesce headers with compressed chunked data
                    chunk_len_pre = f"{chunks_len:x}\r\n".encode("ascii")
                    self._writelines(
                        (headers_buf, chunk_len_pre, *chunks, b"\r\n0\r\n\r\n")
                    )
                else:
                    # Coalesce headers with compressed data
                    self._writelines((headers_buf, *chunks))
                await self.drain()
                self._eof = True
                return

            # Headers already sent, just write compressed data
            if self.chunked:
                chunk_len_pre = f"{chunks_len:x}\r\n".encode("ascii")
                self._writelines((chunk_len_pre, *chunks, b"\r\n0\r\n\r\n"))
            elif len(chunks) > 1:
                self._writelines(chunks)
            else:
                self._write(chunks[0])
            await self.drain()
            self._eof = True
            return

        # No compression - send buffered headers if not yet sent
        if self._headers_buf and not self._headers_written:
            # Use helper to send headers with payload
            self._send_headers_with_payload(chunk, True)
            await self.drain()
            self._eof = True
            return

        # Handle remaining body
        if self.chunked:
            if chunk:
                # Write final chunk with EOF marker
                self._writelines(
                    (f"{len(chunk):x}\r\n".encode("ascii"), chunk, b"\r\n0\r\n\r\n")
                )
            else:
                self._write(b"0\r\n\r\n")
            await self.drain()
            self._eof = True
            return

        if chunk:
            self._write(chunk)
            await self.drain()

        self._eof = True

    async def drain(self) -> None:
        """Flush the write buffer.

        The intended use is to write

          await w.write(data)
          await w.drain()
        """
        protocol = self._protocol
        if protocol.transport is not None and protocol._paused:
            await protocol._drain_helper()


def _safe_header(string: str) -> str:
    if "\r" in string or "\n" in string:
        raise ValueError(
            "Newline or carriage return detected in headers. "
            "Potential header injection attack."
        )
    return string


def _py_serialize_headers(status_line: str, headers: "CIMultiDict[str]") -> bytes:
    headers_gen = (_safe_header(k) + ": " + _safe_header(v) for k, v in headers.items())
    line = status_line + "\r\n" + "\r\n".join(headers_gen) + "\r\n\r\n"
    return line.encode("utf-8")


_serialize_headers = _py_serialize_headers

try:
    import aiohttp._http_writer as _http_writer  # type: ignore[import-not-found]

    _c_serialize_headers = _http_writer._serialize_headers
    if not NO_EXTENSIONS:
        _serialize_headers = _c_serialize_headers
except ImportError:
    pass

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import file, file_service

from .base import DEFAULT_CLIENT_INFO, FileServiceTransport
from .grpc import FileServiceGrpcTransport


class FileServiceGrpcAsyncIOTransport(FileServiceTransport):
    """gRPC AsyncIO backend transport for FileService.

    An API for uploading and managing files.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def create_file(
        self,
    ) -> Callable[
        [file_service.CreateFileRequest], Awaitable[file_service.CreateFileResponse]
    ]:
        r"""Return a callable for the create file method over gRPC.

        Creates a ``File``.

        Returns:
            Callable[[~.CreateFileRequest],
                    Awaitable[~.CreateFileResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_file" not in self._stubs:
            self._stubs["create_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/CreateFile",
                request_serializer=file_service.CreateFileRequest.serialize,
                response_deserializer=file_service.CreateFileResponse.deserialize,
            )
        return self._stubs["create_file"]

    @property
    def list_files(
        self,
    ) -> Callable[
        [file_service.ListFilesRequest], Awaitable[file_service.ListFilesResponse]
    ]:
        r"""Return a callable for the list files method over gRPC.

        Lists the metadata for ``File``\ s owned by the requesting
        project.

        Returns:
            Callable[[~.ListFilesRequest],
                    Awaitable[~.ListFilesResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_files" not in self._stubs:
            self._stubs["list_files"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/ListFiles",
                request_serializer=file_service.ListFilesRequest.serialize,
                response_deserializer=file_service.ListFilesResponse.deserialize,
            )
        return self._stubs["list_files"]

    @property
    def get_file(self) -> Callable[[file_service.GetFileRequest], Awaitable[file.File]]:
        r"""Return a callable for the get file method over gRPC.

        Gets the metadata for the given ``File``.

        Returns:
            Callable[[~.GetFileRequest],
                    Awaitable[~.File]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_file" not in self._stubs:
            self._stubs["get_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/GetFile",
                request_serializer=file_service.GetFileRequest.serialize,
                response_deserializer=file.File.deserialize,
            )
        return self._stubs["get_file"]

    @property
    def delete_file(
        self,
    ) -> Callable[[file_service.DeleteFileRequest], Awaitable[empty_pb2.Empty]]:
        r"""Return a callable for the delete file method over gRPC.

        Deletes the ``File``.

        Returns:
            Callable[[~.DeleteFileRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_file" not in self._stubs:
            self._stubs["delete_file"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.FileService/DeleteFile",
                request_serializer=file_service.DeleteFileRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_file"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.create_file: gapic_v1.method_async.wrap_method(
                self.create_file,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_files: gapic_v1.method_async.wrap_method(
                self.list_files,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_file: gapic_v1.method_async.wrap_method(
                self.get_file,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_file: gapic_v1.method_async.wrap_method(
                self.delete_file,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("FileServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\operations_client.py ===
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

"""A client for the google.longrunning.operations meta-API.

This is a client that deals with long-running operations that follow the
pattern outlined by the `Google API Style Guide`_.

When an API method normally takes long time to complete, it can be designed to
return ``Operation`` to the client, and the client can use this interface to
receive the real response asynchronously by polling the operation resource to
receive the response.

It is not a separate service, but rather an interface implemented by a larger
service. The protocol-level definition is available at
`google/longrunning/operations.proto`_. Typically, this will be constructed
automatically by another client class to deal with operations.

.. _Google API Style Guide:
    https://cloud.google.com/apis/design/design_pattern
    s#long_running_operations
.. _google/longrunning/operations.proto:
    https://github.com/googleapis/googleapis/blob/master/google/longrunning
    /operations.proto
"""

import functools

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import page_iterator
from google.api_core import retry as retries
from google.api_core import timeout as timeouts
from google.longrunning import operations_pb2
from grpc import Compression


class OperationsClient(object):
    """Client for interacting with long-running operations within a service.

    Args:
        channel (grpc.Channel): The gRPC channel associated with the service
            that implements the ``google.longrunning.operations`` interface.
        client_config (dict):
            A dictionary of call options for each method. If not specified
            the default configuration is used.
    """

    def __init__(self, channel, client_config=None):
        # Create the gRPC client stub.
        self.operations_stub = operations_pb2.OperationsStub(channel)

        default_retry = retries.Retry(
            initial=0.1,  # seconds
            maximum=60.0,  # seconds
            multiplier=1.3,
            predicate=retries.if_exception_type(
                core_exceptions.DeadlineExceeded,
                core_exceptions.ServiceUnavailable,
            ),
            timeout=600.0,  # seconds
        )
        default_timeout = timeouts.TimeToDeadlineTimeout(timeout=600.0)

        default_compression = Compression.NoCompression

        self._get_operation = gapic_v1.method.wrap_method(
            self.operations_stub.GetOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._list_operations = gapic_v1.method.wrap_method(
            self.operations_stub.ListOperations,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._cancel_operation = gapic_v1.method.wrap_method(
            self.operations_stub.CancelOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

        self._delete_operation = gapic_v1.method.wrap_method(
            self.operations_stub.DeleteOperation,
            default_retry=default_retry,
            default_timeout=default_timeout,
            default_compression=default_compression,
        )

    # Service calls
    def get_operation(
        self,
        name,
        retry=gapic_v1.method.DEFAULT,
        timeout=gapic_v1.method.DEFAULT,
        compression=gapic_v1.method.DEFAULT,
        metadata=None,
    ):
        """Gets the latest state of a long-running operation.

        Clients can use this method to poll the operation result at intervals
        as recommended by the API service.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> response = api.get_operation(name)

        Args:
            name (str): The name of the operation resource.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]):
                Additional gRPC metadata.

        Returns:
            google.longrunning.operations_pb2.Operation: The state of the
                operation.

        Raises:
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        request = operations_pb2.GetOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        return self._get_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

    def list_operations(
        self,
        name,
        filter_,
        retry=gapic_v1.method.DEFAULT,
        timeout=gapic_v1.method.DEFAULT,
        compression=gapic_v1.method.DEFAULT,
        metadata=None,
    ):
        """
        Lists operations that match the specified filter in the request.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>>
            >>> # Iterate over all results
            >>> for operation in api.list_operations(name):
            >>>   # process operation
            >>>   pass
            >>>
            >>> # Or iterate over results one page at a time
            >>> iter = api.list_operations(name)
            >>> for page in iter.pages:
            >>>   for operation in page:
            >>>     # process operation
            >>>     pass

        Args:
            name (str): The name of the operation collection.
            filter_ (str): The standard list filter.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.

        Returns:
            google.api_core.page_iterator.Iterator: An iterator that yields
                :class:`google.longrunning.operations_pb2.Operation` instances.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        # Create the request object.
        request = operations_pb2.ListOperationsRequest(name=name, filter=filter_)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        # Create the method used to fetch pages
        method = functools.partial(
            self._list_operations,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

        iterator = page_iterator.GRPCIterator(
            client=None,
            method=method,
            request=request,
            items_field="operations",
            request_token_field="page_token",
            response_token_field="next_page_token",
        )

        return iterator

    def cancel_operation(
        self,
        name,
        retry=gapic_v1.method.DEFAULT,
        timeout=gapic_v1.method.DEFAULT,
        compression=gapic_v1.method.DEFAULT,
        metadata=None,
    ):
        """Starts asynchronous cancellation on a long-running operation.

        The server makes a best effort to cancel the operation, but success is
        not guaranteed. Clients can use :meth:`get_operation` or service-
        specific methods to check whether the cancellation succeeded or whether
        the operation completed despite cancellation. On successful
        cancellation, the operation is not deleted; instead, it becomes an
        operation with an ``Operation.error`` value with a
        ``google.rpc.Status.code`` of ``1``, corresponding to
        ``Code.CANCELLED``.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> api.cancel_operation(name)

        Args:
            name (str): The name of the operation resource to be cancelled.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        # Create the request object.
        request = operations_pb2.CancelOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        self._cancel_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

    def delete_operation(
        self,
        name,
        retry=gapic_v1.method.DEFAULT,
        timeout=gapic_v1.method.DEFAULT,
        compression=gapic_v1.method.DEFAULT,
        metadata=None,
    ):
        """Deletes a long-running operation.

        This method indicates that the client is no longer interested in the
        operation result. It does not cancel the operation.

        Example:
            >>> from google.api_core import operations_v1
            >>> api = operations_v1.OperationsClient()
            >>> name = ''
            >>> api.delete_operation(name)

        Args:
            name (str): The name of the operation resource to be deleted.
            retry (google.api_core.retry.Retry): The retry strategy to use
                when invoking the RPC. If unspecified, the default retry from
                the client configuration will be used. If ``None``, then this
                method will not retry the RPC at all.
            timeout (float): The amount of time in seconds to wait for the RPC
                to complete. Note that if ``retry`` is used, this timeout
                applies to each individual attempt and the overall time it
                takes for this method to complete may be longer. If
                unspecified, the the default timeout in the client
                configuration is used. If ``None``, then the RPC method will
                not time out.
            compression (grpc.Compression): An element of grpc.compression
                e.g. grpc.compression.Gzip.
            metadata (Optional[List[Tuple[str, str]]]): Additional gRPC
                metadata.

        Raises:
            google.api_core.exceptions.MethodNotImplemented: If the server
                does not support this method. Services are not required to
                implement this method.
            google.api_core.exceptions.GoogleAPICallError: If an error occurred
                while invoking the RPC, the appropriate ``GoogleAPICallError``
                subclass will be raised.
        """
        # Create the request object.
        request = operations_pb2.DeleteOperationRequest(name=name)

        # Add routing header
        metadata = metadata or []
        metadata.append(gapic_v1.routing_header.to_grpc_metadata({"name": name}))

        self._delete_operation(
            request,
            retry=retry,
            timeout=timeout,
            compression=compression,
            metadata=metadata,
        )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\errors.py ===
"""Contains all custom errors."""

from pathlib import Path
from typing import Optional, Union

from requests import HTTPError, Response


# CACHE ERRORS


class CacheNotFound(Exception):
    """Exception thrown when the Huggingface cache is not found."""

    cache_dir: Union[str, Path]

    def __init__(self, msg: str, cache_dir: Union[str, Path], *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
        self.cache_dir = cache_dir


class CorruptedCacheException(Exception):
    """Exception for any unexpected structure in the Huggingface cache-system."""


# HEADERS ERRORS


class LocalTokenNotFoundError(EnvironmentError):
    """Raised if local token is required but not found."""


# HTTP ERRORS


class OfflineModeIsEnabled(ConnectionError):
    """Raised when a request is made but `HF_HUB_OFFLINE=1` is set as environment variable."""


class HfHubHTTPError(HTTPError):
    """
    HTTPError to inherit from for any custom HTTP Error raised in HF Hub.

    Any HTTPError is converted at least into a `HfHubHTTPError`. If some information is
    sent back by the server, it will be added to the error message.

    Added details:
    - Request id from "X-Request-Id" header if exists. If not, fallback to "X-Amzn-Trace-Id" header if exists.
    - Server error message from the header "X-Error-Message".
    - Server error message if we can found one in the response body.

    Example:
    ```py
        import requests
        from huggingface_hub.utils import get_session, hf_raise_for_status, HfHubHTTPError

        response = get_session().post(...)
        try:
            hf_raise_for_status(response)
        except HfHubHTTPError as e:
            print(str(e)) # formatted message
            e.request_id, e.server_message # details returned by server

            # Complete the error message with additional information once it's raised
            e.append_to_message("\n`create_commit` expects the repository to exist.")
            raise
    ```
    """

    def __init__(self, message: str, response: Optional[Response] = None, *, server_message: Optional[str] = None):
        self.request_id = (
            response.headers.get("x-request-id") or response.headers.get("X-Amzn-Trace-Id")
            if response is not None
            else None
        )
        self.server_message = server_message

        super().__init__(
            message,
            response=response,  # type: ignore [arg-type]
            request=response.request if response is not None else None,  # type: ignore [arg-type]
        )

    def append_to_message(self, additional_message: str) -> None:
        """Append additional information to the `HfHubHTTPError` initial message."""
        self.args = (self.args[0] + additional_message,) + self.args[1:]


# INFERENCE CLIENT ERRORS


class InferenceTimeoutError(HTTPError, TimeoutError):
    """Error raised when a model is unavailable or the request times out."""


# INFERENCE ENDPOINT ERRORS


class InferenceEndpointError(Exception):
    """Generic exception when dealing with Inference Endpoints."""


class InferenceEndpointTimeoutError(InferenceEndpointError, TimeoutError):
    """Exception for timeouts while waiting for Inference Endpoint."""


# SAFETENSORS ERRORS


class SafetensorsParsingError(Exception):
    """Raised when failing to parse a safetensors file metadata.

    This can be the case if the file is not a safetensors file or does not respect the specification.
    """


class NotASafetensorsRepoError(Exception):
    """Raised when a repo is not a Safetensors repo i.e. doesn't have either a `model.safetensors` or a
    `model.safetensors.index.json` file.
    """


# TEXT GENERATION ERRORS


class TextGenerationError(HTTPError):
    """Generic error raised if text-generation went wrong."""


# Text Generation Inference Errors
class ValidationError(TextGenerationError):
    """Server-side validation error."""


class GenerationError(TextGenerationError):
    pass


class OverloadedError(TextGenerationError):
    pass


class IncompleteGenerationError(TextGenerationError):
    pass


class UnknownError(TextGenerationError):
    pass


# VALIDATION ERRORS


class HFValidationError(ValueError):
    """Generic exception thrown by `huggingface_hub` validators.

    Inherits from [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError).
    """


# FILE METADATA ERRORS


class FileMetadataError(OSError):
    """Error triggered when the metadata of a file on the Hub cannot be retrieved (missing ETag or commit_hash).

    Inherits from `OSError` for backward compatibility.
    """


# REPOSITORY ERRORS


class RepositoryNotFoundError(HfHubHTTPError):
    """
    Raised when trying to access a hf.co URL with an invalid repository name, or
    with a private repo name the user does not have access to.

    Example:

    ```py
    >>> from huggingface_hub import model_info
    >>> model_info("<non_existent_repository>")
    (...)
    huggingface_hub.utils._errors.RepositoryNotFoundError: 401 Client Error. (Request ID: PvMw_VjBMjVdMz53WKIzP)

    Repository Not Found for url: https://huggingface.co/api/models/%3Cnon_existent_repository%3E.
    Please make sure you specified the correct `repo_id` and `repo_type`.
    If the repo is private, make sure you are authenticated.
    Invalid username or password.
    ```
    """


class GatedRepoError(RepositoryNotFoundError):
    """
    Raised when trying to access a gated repository for which the user is not on the
    authorized list.

    Note: derives from `RepositoryNotFoundError` to ensure backward compatibility.

    Example:

    ```py
    >>> from huggingface_hub import model_info
    >>> model_info("<gated_repository>")
    (...)
    huggingface_hub.utils._errors.GatedRepoError: 403 Client Error. (Request ID: ViT1Bf7O_026LGSQuVqfa)

    Cannot access gated repo for url https://huggingface.co/api/models/ardent-figment/gated-model.
    Access to model ardent-figment/gated-model is restricted and you are not in the authorized list.
    Visit https://huggingface.co/ardent-figment/gated-model to ask for access.
    ```
    """


class DisabledRepoError(HfHubHTTPError):
    """
    Raised when trying to access a repository that has been disabled by its author.

    Example:

    ```py
    >>> from huggingface_hub import dataset_info
    >>> dataset_info("laion/laion-art")
    (...)
    huggingface_hub.utils._errors.DisabledRepoError: 403 Client Error. (Request ID: Root=1-659fc3fa-3031673e0f92c71a2260dbe2;bc6f4dfb-b30a-4862-af0a-5cfe827610d8)

    Cannot access repository for url https://huggingface.co/api/datasets/laion/laion-art.
    Access to this resource is disabled.
    ```
    """


# REVISION ERROR


class RevisionNotFoundError(HfHubHTTPError):
    """
    Raised when trying to access a hf.co URL with a valid repository but an invalid
    revision.

    Example:

    ```py
    >>> from huggingface_hub import hf_hub_download
    >>> hf_hub_download('bert-base-cased', 'config.json', revision='<non-existent-revision>')
    (...)
    huggingface_hub.utils._errors.RevisionNotFoundError: 404 Client Error. (Request ID: Mwhe_c3Kt650GcdKEFomX)

    Revision Not Found for url: https://huggingface.co/bert-base-cased/resolve/%3Cnon-existent-revision%3E/config.json.
    ```
    """


# ENTRY ERRORS
class EntryNotFoundError(HfHubHTTPError):
    """
    Raised when trying to access a hf.co URL with a valid repository and revision
    but an invalid filename.

    Example:

    ```py
    >>> from huggingface_hub import hf_hub_download
    >>> hf_hub_download('bert-base-cased', '<non-existent-file>')
    (...)
    huggingface_hub.utils._errors.EntryNotFoundError: 404 Client Error. (Request ID: 53pNl6M0MxsnG5Sw8JA6x)

    Entry Not Found for url: https://huggingface.co/bert-base-cased/resolve/main/%3Cnon-existent-file%3E.
    ```
    """


class LocalEntryNotFoundError(EntryNotFoundError, FileNotFoundError, ValueError):
    """
    Raised when trying to access a file or snapshot that is not on the disk when network is
    disabled or unavailable (connection issue). The entry may exist on the Hub.

    Note: `ValueError` type is to ensure backward compatibility.
    Note: `LocalEntryNotFoundError` derives from `HTTPError` because of `EntryNotFoundError`
          even when it is not a network issue.

    Example:

    ```py
    >>> from huggingface_hub import hf_hub_download
    >>> hf_hub_download('bert-base-cased', '<non-cached-file>',  local_files_only=True)
    (...)
    huggingface_hub.utils._errors.LocalEntryNotFoundError: Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable hf.co look-ups and downloads online, set 'local_files_only' to False.
    ```
    """

    def __init__(self, message: str):
        super().__init__(message, response=None)


# REQUEST ERROR
class BadRequestError(HfHubHTTPError, ValueError):
    """
    Raised by `hf_raise_for_status` when the server returns a HTTP 400 error.

    Example:

    ```py
    >>> resp = requests.post("hf.co/api/check", ...)
    >>> hf_raise_for_status(resp, endpoint_name="check")
    huggingface_hub.utils._errors.BadRequestError: Bad request for check endpoint: {details} (Request ID: XXX)
    ```
    """


# DDUF file format ERROR


class DDUFError(Exception):
    """Base exception for errors related to the DDUF format."""


class DDUFCorruptedFileError(DDUFError):
    """Exception thrown when the DDUF file is corrupted."""


class DDUFExportError(DDUFError):
    """Base exception for errors during DDUF export."""


class DDUFInvalidEntryNameError(DDUFExportError):
    """Exception thrown when the entry name is invalid."""


# STRICT DATACLASSES ERRORS


class StrictDataclassError(Exception):
    """Base exception for strict dataclasses."""


class StrictDataclassDefinitionError(StrictDataclassError):
    """Exception thrown when a strict dataclass is defined incorrectly."""


class StrictDataclassFieldValidationError(StrictDataclassError):
    """Exception thrown when a strict dataclass fails validation for a given field."""

    def __init__(self, field: str, cause: Exception):
        error_message = f"Validation error for field '{field}':"
        error_message += f"\n    {cause.__class__.__name__}: {cause}"
        super().__init__(error_message)


class StrictDataclassClassValidationError(StrictDataclassError):
    """Exception thrown when a strict dataclass fails validation on a class validator."""

    def __init__(self, validator: str, cause: Exception):
        error_message = f"Class validation error for validator '{validator}':"
        error_message += f"\n    {cause.__class__.__name__}: {cause}"
        super().__init__(error_message)


# XET ERRORS


class XetError(Exception):
    """Base exception for errors related to Xet Storage."""


class XetAuthorizationError(XetError):
    """Exception thrown when the user does not have the right authorization to use Xet Storage."""


class XetRefreshTokenError(XetError):
    """Exception thrown when the refresh token is invalid."""


class XetDownloadError(Exception):
    """Exception thrown when the download from Xet Storage fails."""

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\key_management_event_hooks.py ===
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import (
    CommonProxyErrors,
    GenerateKeyRequest,
    GenerateKeyResponse,
    KeyRequest,
    LiteLLM_AuditLogs,
    Litellm_EntityType,
    LiteLLM_VerificationToken,
    LitellmTableNames,
    RegenerateKeyRequest,
    UpdateKeyRequest,
    UserAPIKeyAuth,
)

# NOTE: This is the prefix for all virtual keys stored in AWS Secrets Manager
LITELLM_PREFIX_STORED_VIRTUAL_KEYS = "litellm/"


class KeyManagementEventHooks:
    @staticmethod
    async def async_key_generated_hook(
        data: GenerateKeyRequest,
        response: GenerateKeyResponse,
        user_api_key_dict: UserAPIKeyAuth,
        litellm_changed_by: Optional[str] = None,
    ):
        """
        Hook that runs after a successful /key/generate request

        Handles the following:
        - Sending Email with Key Details
        - Storing Audit Logs for key generation
        - Storing Generated Key in DB
        """
        from litellm.proxy.management_helpers.audit_logs import (
            create_audit_log_for_update,
        )
        from litellm.proxy.proxy_server import litellm_proxy_admin_name

        if data.send_invite_email is True:
            await KeyManagementEventHooks._send_key_created_email(
                response.model_dump(exclude_none=True)
            )

        # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
        if litellm.store_audit_logs is True:
            _updated_values = response.model_dump_json(exclude_none=True)
            asyncio.create_task(
                create_audit_log_for_update(
                    request_data=LiteLLM_AuditLogs(
                        id=str(uuid.uuid4()),
                        updated_at=datetime.now(timezone.utc),
                        changed_by=litellm_changed_by
                        or user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                        changed_by_api_key=user_api_key_dict.api_key,
                        table_name=LitellmTableNames.KEY_TABLE_NAME,
                        object_id=response.token_id or "",
                        action="created",
                        updated_values=_updated_values,
                        before_value=None,
                    )
                )
            )
        # store the generated key in the secret manager
        await KeyManagementEventHooks._store_virtual_key_in_secret_manager(
            secret_name=data.key_alias or f"virtual-key-{response.token_id}",
            secret_token=response.key,
        )

    @staticmethod
    async def async_key_updated_hook(
        data: UpdateKeyRequest,
        existing_key_row: Any,
        response: Any,
        user_api_key_dict: UserAPIKeyAuth,
        litellm_changed_by: Optional[str] = None,
    ):
        """
        Post /key/update processing hook

        Handles the following:
        - Storing Audit Logs for key update
        """
        from litellm.proxy.management_helpers.audit_logs import (
            create_audit_log_for_update,
        )
        from litellm.proxy.proxy_server import litellm_proxy_admin_name

        # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
        if litellm.store_audit_logs is True:
            _updated_values = json.dumps(data.json(exclude_none=True), default=str)

            _before_value = existing_key_row.json(exclude_none=True)
            _before_value = json.dumps(_before_value, default=str)

            asyncio.create_task(
                create_audit_log_for_update(
                    request_data=LiteLLM_AuditLogs(
                        id=str(uuid.uuid4()),
                        updated_at=datetime.now(timezone.utc),
                        changed_by=litellm_changed_by
                        or user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                        changed_by_api_key=user_api_key_dict.api_key,
                        table_name=LitellmTableNames.KEY_TABLE_NAME,
                        object_id=data.key,
                        action="updated",
                        updated_values=_updated_values,
                        before_value=_before_value,
                    )
                )
            )

    @staticmethod
    async def async_key_rotated_hook(
        data: Optional[RegenerateKeyRequest],
        existing_key_row: LiteLLM_VerificationToken,
        response: GenerateKeyResponse,
        user_api_key_dict: UserAPIKeyAuth,
        litellm_changed_by: Optional[str] = None,
    ):
        from litellm.proxy.management_helpers.audit_logs import (
            create_audit_log_for_update,
        )
        from litellm.proxy.proxy_server import litellm_proxy_admin_name

        # store the generated key in the secret manager
        if data is not None and response.token_id is not None:
            initial_secret_name = (
                existing_key_row.key_alias or f"virtual-key-{existing_key_row.token}"
            )
            await KeyManagementEventHooks._rotate_virtual_key_in_secret_manager(
                current_secret_name=initial_secret_name,
                new_secret_name=data.key_alias or f"virtual-key-{response.token_id}",
                new_secret_value=response.key,
            )

        # store the audit log
        if litellm.store_audit_logs is True and existing_key_row.token is not None:
            asyncio.create_task(
                create_audit_log_for_update(
                    request_data=LiteLLM_AuditLogs(
                        id=str(uuid.uuid4()),
                        updated_at=datetime.now(timezone.utc),
                        changed_by=litellm_changed_by
                        or user_api_key_dict.user_id
                        or litellm_proxy_admin_name,
                        changed_by_api_key=user_api_key_dict.token,
                        table_name=LitellmTableNames.KEY_TABLE_NAME,
                        object_id=existing_key_row.token,
                        action="rotated",
                        updated_values=response.model_dump_json(exclude_none=True),
                        before_value=existing_key_row.model_dump_json(
                            exclude_none=True
                        ),
                    )
                )
            )

    @staticmethod
    async def async_key_deleted_hook(
        data: KeyRequest,
        keys_being_deleted: List[LiteLLM_VerificationToken],
        response: dict,
        user_api_key_dict: UserAPIKeyAuth,
        litellm_changed_by: Optional[str] = None,
    ):
        """
        Post /key/delete processing hook

        Handles the following:
        - Storing Audit Logs for key deletion
        """
        from litellm.proxy.management_helpers.audit_logs import (
            create_audit_log_for_update,
        )
        from litellm.proxy.proxy_server import litellm_proxy_admin_name

        # Enterprise Feature - Audit Logging. Enable with litellm.store_audit_logs = True
        # we do this after the first for loop, since first for loop is for validation. we only want this inserted after validation passes
        if litellm.store_audit_logs is True and data.keys is not None:
            # make an audit log for each key deleted
            for key in keys_being_deleted:
                if key.token is None:
                    continue
                _key_row = key.model_dump_json(exclude_none=True)

                asyncio.create_task(
                    create_audit_log_for_update(
                        request_data=LiteLLM_AuditLogs(
                            id=str(uuid.uuid4()),
                            updated_at=datetime.now(timezone.utc),
                            changed_by=litellm_changed_by
                            or user_api_key_dict.user_id
                            or litellm_proxy_admin_name,
                            changed_by_api_key=user_api_key_dict.token,
                            table_name=LitellmTableNames.KEY_TABLE_NAME,
                            object_id=key.token,
                            action="deleted",
                            updated_values="{}",
                            before_value=_key_row,
                        )
                    )
                )
        # delete the keys from the secret manager
        await KeyManagementEventHooks._delete_virtual_keys_from_secret_manager(
            keys_being_deleted=keys_being_deleted
        )
        pass

    @staticmethod
    async def _store_virtual_key_in_secret_manager(secret_name: str, secret_token: str):
        """
        Store a virtual key in the secret manager

        Args:
            secret_name: Name of the virtual key
            secret_token: Value of the virtual key (example: sk-1234)
        """
        if litellm._key_management_settings is not None:
            if litellm._key_management_settings.store_virtual_keys is True:
                from litellm.secret_managers.base_secret_manager import (
                    BaseSecretManager,
                )

                # store the key in the secret manager
                if isinstance(litellm.secret_manager_client, BaseSecretManager):
                    await litellm.secret_manager_client.async_write_secret(
                        secret_name=KeyManagementEventHooks._get_secret_name(
                            secret_name
                        ),
                        secret_value=secret_token,
                    )

    @staticmethod
    async def _rotate_virtual_key_in_secret_manager(
        current_secret_name: str, new_secret_name: str, new_secret_value: str
    ):
        """
        Update a virtual key in the secret manager

        Args:
            secret_name: Name of the virtual key
            secret_token: Value of the virtual key (example: sk-1234)
        """
        if litellm._key_management_settings is not None:
            if litellm._key_management_settings.store_virtual_keys is True:
                from litellm.secret_managers.base_secret_manager import (
                    BaseSecretManager,
                )

                # store the key in the secret manager
                if isinstance(litellm.secret_manager_client, BaseSecretManager):
                    await litellm.secret_manager_client.async_rotate_secret(
                        current_secret_name=KeyManagementEventHooks._get_secret_name(
                            current_secret_name
                        ),
                        new_secret_name=KeyManagementEventHooks._get_secret_name(
                            new_secret_name
                        ),
                        new_secret_value=new_secret_value,
                    )

    @staticmethod
    def _get_secret_name(secret_name: str) -> str:
        if litellm._key_management_settings.prefix_for_stored_virtual_keys.endswith(
            "/"
        ):
            return f"{litellm._key_management_settings.prefix_for_stored_virtual_keys}{secret_name}"
        else:
            return f"{litellm._key_management_settings.prefix_for_stored_virtual_keys}/{secret_name}"

    @staticmethod
    async def _delete_virtual_keys_from_secret_manager(
        keys_being_deleted: List[LiteLLM_VerificationToken],
    ):
        """
        Deletes virtual keys from the secret manager

        Args:
            keys_being_deleted: List of keys being deleted, this is passed down from the /key/delete operation
        """
        if litellm._key_management_settings is not None:
            if litellm._key_management_settings.store_virtual_keys is True:
                from litellm.secret_managers.base_secret_manager import (
                    BaseSecretManager,
                )

                if isinstance(litellm.secret_manager_client, BaseSecretManager):
                    for key in keys_being_deleted:
                        if key.key_alias is not None:
                            await litellm.secret_manager_client.async_delete_secret(
                                secret_name=KeyManagementEventHooks._get_secret_name(
                                    key.key_alias
                                )
                            )
                        else:
                            verbose_proxy_logger.warning(
                                f"KeyManagementEventHooks._delete_virtual_key_from_secret_manager: Key alias not found for key {key.token}. Skipping deletion from secret manager."
                            )

    @staticmethod
    async def _send_key_created_email(response: dict):
        try:
            from litellm_enterprise.enterprise_callbacks.send_emails.base_email import (
                BaseEmailLogger,
            )
        except ImportError:
            raise Exception(
                "Trying to use Email Hooks"
                + CommonProxyErrors.missing_enterprise_package.value
            )

        from litellm.proxy.proxy_server import general_settings, proxy_logging_obj

        try:
            from litellm_enterprise.types.enterprise_callbacks.send_emails import (
                SendKeyCreatedEmailEvent,
            )
        except ImportError:
            raise Exception(
                "Trying to use Email Hooks"
                + CommonProxyErrors.missing_enterprise_package.value
            )

        event = SendKeyCreatedEmailEvent(
            virtual_key=response.get("key", ""),
            event="key_created",
            event_group=Litellm_EntityType.KEY,
            event_message="API Key Created",
            token=response.get("token", ""),
            spend=response.get("spend", 0.0),
            max_budget=response.get("max_budget", 0.0),
            user_id=response.get("user_id", None),
            team_id=response.get("team_id", "Default Team"),
            key_alias=response.get("key_alias", None),
        )

        ##########################
        # v2 integration for emails
        ##########################
        initialized_email_loggers = (
            litellm.logging_callback_manager.get_custom_loggers_for_type(
                callback_type=BaseEmailLogger
            )
        )
        if len(initialized_email_loggers) > 0:
            for email_logger in initialized_email_loggers:
                if isinstance(email_logger, BaseEmailLogger):
                    await email_logger.send_key_created_email(
                        send_key_created_email_event=event,
                    )

        ##########################
        # v0 integration for emails
        ##########################
        else:
            if "email" not in general_settings.get("alerting", []):
                raise ValueError(
                    "Email alerting not setup on config.yaml. Please set `alerting=['email']. \nDocs: https://docs.litellm.ai/docs/proxy/email`"
                )

            # If user configured email alerting - send an Email letting their end-user know the key was created
            asyncio.create_task(
                proxy_logging_obj.slack_alerting_instance.send_key_created_or_user_invited_email(
                    webhook_event=event,
                )
            )

# === NexusCore/openenv\Lib\site-packages\nltk\classify\weka.py ===
# Natural Language Toolkit: Interface to Weka Classsifiers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classifiers that make use of the external 'Weka' package.
"""

import os
import re
import subprocess
import tempfile
import time
import zipfile
from sys import stdin

from nltk.classify.api import ClassifierI
from nltk.internals import config_java, java
from nltk.probability import DictionaryProbDist

_weka_classpath = None
_weka_search = [
    ".",
    "/usr/share/weka",
    "/usr/local/share/weka",
    "/usr/lib/weka",
    "/usr/local/lib/weka",
]


def config_weka(classpath=None):
    global _weka_classpath

    # Make sure java's configured first.
    config_java()

    if classpath is not None:
        _weka_classpath = classpath

    if _weka_classpath is None:
        searchpath = _weka_search
        if "WEKAHOME" in os.environ:
            searchpath.insert(0, os.environ["WEKAHOME"])

        for path in searchpath:
            if os.path.exists(os.path.join(path, "weka.jar")):
                _weka_classpath = os.path.join(path, "weka.jar")
                version = _check_weka_version(_weka_classpath)
                if version:
                    print(f"[Found Weka: {_weka_classpath} (version {version})]")
                else:
                    print("[Found Weka: %s]" % _weka_classpath)
                _check_weka_version(_weka_classpath)

    if _weka_classpath is None:
        raise LookupError(
            "Unable to find weka.jar!  Use config_weka() "
            "or set the WEKAHOME environment variable. "
            "For more information about Weka, please see "
            "https://www.cs.waikato.ac.nz/ml/weka/"
        )


def _check_weka_version(jar):
    try:
        zf = zipfile.ZipFile(jar)
    except (SystemExit, KeyboardInterrupt):
        raise
    except:
        return None
    try:
        try:
            return zf.read("weka/core/version.txt")
        except KeyError:
            return None
    finally:
        zf.close()


class WekaClassifier(ClassifierI):
    def __init__(self, formatter, model_filename):
        self._formatter = formatter
        self._model = model_filename

    def prob_classify_many(self, featuresets):
        return self._classify_many(featuresets, ["-p", "0", "-distribution"])

    def classify_many(self, featuresets):
        return self._classify_many(featuresets, ["-p", "0"])

    def _classify_many(self, featuresets, options):
        # Make sure we can find java & weka.
        config_weka()

        temp_dir = tempfile.mkdtemp()
        try:
            # Write the test data file.
            test_filename = os.path.join(temp_dir, "test.arff")
            self._formatter.write(test_filename, featuresets)

            # Call weka to classify the data.
            cmd = [
                "weka.classifiers.bayes.NaiveBayes",
                "-l",
                self._model,
                "-T",
                test_filename,
            ] + options
            (stdout, stderr) = java(
                cmd,
                classpath=_weka_classpath,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Check if something went wrong:
            if stderr and not stdout:
                if "Illegal options: -distribution" in stderr:
                    raise ValueError(
                        "The installed version of weka does "
                        "not support probability distribution "
                        "output."
                    )
                else:
                    raise ValueError("Weka failed to generate output:\n%s" % stderr)

            # Parse weka's output.
            return self.parse_weka_output(stdout.decode(stdin.encoding).split("\n"))

        finally:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

    def parse_weka_distribution(self, s):
        probs = [float(v) for v in re.split("[*,]+", s) if v.strip()]
        probs = dict(zip(self._formatter.labels(), probs))
        return DictionaryProbDist(probs)

    def parse_weka_output(self, lines):
        # Strip unwanted text from stdout
        for i, line in enumerate(lines):
            if line.strip().startswith("inst#"):
                lines = lines[i:]
                break

        if lines[0].split() == ["inst#", "actual", "predicted", "error", "prediction"]:
            return [line.split()[2].split(":")[1] for line in lines[1:] if line.strip()]
        elif lines[0].split() == [
            "inst#",
            "actual",
            "predicted",
            "error",
            "distribution",
        ]:
            return [
                self.parse_weka_distribution(line.split()[-1])
                for line in lines[1:]
                if line.strip()
            ]

        # is this safe:?
        elif re.match(r"^0 \w+ [01]\.[0-9]* \?\s*$", lines[0]):
            return [line.split()[1] for line in lines if line.strip()]

        else:
            for line in lines[:10]:
                print(line)
            raise ValueError(
                "Unhandled output format -- your version "
                "of weka may not be supported.\n"
                "  Header: %s" % lines[0]
            )

    # [xx] full list of classifiers (some may be abstract?):
    # ADTree, AODE, BayesNet, ComplementNaiveBayes, ConjunctiveRule,
    # DecisionStump, DecisionTable, HyperPipes, IB1, IBk, Id3, J48,
    # JRip, KStar, LBR, LeastMedSq, LinearRegression, LMT, Logistic,
    # LogisticBase, M5Base, MultilayerPerceptron,
    # MultipleClassifiersCombiner, NaiveBayes, NaiveBayesMultinomial,
    # NaiveBayesSimple, NBTree, NNge, OneR, PaceRegression, PART,
    # PreConstructedLinearModel, Prism, RandomForest,
    # RandomizableClassifier, RandomTree, RBFNetwork, REPTree, Ridor,
    # RuleNode, SimpleLinearRegression, SimpleLogistic,
    # SingleClassifierEnhancer, SMO, SMOreg, UserClassifier, VFI,
    # VotedPerceptron, Winnow, ZeroR

    _CLASSIFIER_CLASS = {
        "naivebayes": "weka.classifiers.bayes.NaiveBayes",
        "C4.5": "weka.classifiers.trees.J48",
        "log_regression": "weka.classifiers.functions.Logistic",
        "svm": "weka.classifiers.functions.SMO",
        "kstar": "weka.classifiers.lazy.KStar",
        "ripper": "weka.classifiers.rules.JRip",
    }

    @classmethod
    def train(
        cls,
        model_filename,
        featuresets,
        classifier="naivebayes",
        options=[],
        quiet=True,
    ):
        # Make sure we can find java & weka.
        config_weka()

        # Build an ARFF formatter.
        formatter = ARFF_Formatter.from_train(featuresets)

        temp_dir = tempfile.mkdtemp()
        try:
            # Write the training data file.
            train_filename = os.path.join(temp_dir, "train.arff")
            formatter.write(train_filename, featuresets)

            if classifier in cls._CLASSIFIER_CLASS:
                javaclass = cls._CLASSIFIER_CLASS[classifier]
            elif classifier in cls._CLASSIFIER_CLASS.values():
                javaclass = classifier
            else:
                raise ValueError("Unknown classifier %s" % classifier)

            # Train the weka model.
            cmd = [javaclass, "-d", model_filename, "-t", train_filename]
            cmd += list(options)
            if quiet:
                stdout = subprocess.PIPE
            else:
                stdout = None
            java(cmd, classpath=_weka_classpath, stdout=stdout)

            # Return the new classifier.
            return WekaClassifier(formatter, model_filename)

        finally:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)


class ARFF_Formatter:
    """
    Converts featuresets and labeled featuresets to ARFF-formatted
    strings, appropriate for input into Weka.

    Features and classes can be specified manually in the constructor, or may
    be determined from data using ``from_train``.
    """

    def __init__(self, labels, features):
        """
        :param labels: A list of all class labels that can be generated.
        :param features: A list of feature specifications, where
            each feature specification is a tuple (fname, ftype);
            and ftype is an ARFF type string such as NUMERIC or
            STRING.
        """
        self._labels = labels
        self._features = features

    def format(self, tokens):
        """Returns a string representation of ARFF output for the given data."""
        return self.header_section() + self.data_section(tokens)

    def labels(self):
        """Returns the list of classes."""
        return list(self._labels)

    def write(self, outfile, tokens):
        """Writes ARFF data to a file for the given data."""
        if not hasattr(outfile, "write"):
            outfile = open(outfile, "w")
        outfile.write(self.format(tokens))
        outfile.close()

    @staticmethod
    def from_train(tokens):
        """
        Constructs an ARFF_Formatter instance with class labels and feature
        types determined from the given data. Handles boolean, numeric and
        string (note: not nominal) types.
        """
        # Find the set of all attested labels.
        labels = {label for (tok, label) in tokens}

        # Determine the types of all features.
        features = {}
        for tok, label in tokens:
            for fname, fval in tok.items():
                if issubclass(type(fval), bool):
                    ftype = "{True, False}"
                elif issubclass(type(fval), (int, float, bool)):
                    ftype = "NUMERIC"
                elif issubclass(type(fval), str):
                    ftype = "STRING"
                elif fval is None:
                    continue  # can't tell the type.
                else:
                    raise ValueError("Unsupported value type %r" % ftype)

                if features.get(fname, ftype) != ftype:
                    raise ValueError("Inconsistent type for %s" % fname)
                features[fname] = ftype
        features = sorted(features.items())

        return ARFF_Formatter(labels, features)

    def header_section(self):
        """Returns an ARFF header as a string."""
        # Header comment.
        s = (
            "% Weka ARFF file\n"
            + "% Generated automatically by NLTK\n"
            + "%% %s\n\n" % time.ctime()
        )

        # Relation name
        s += "@RELATION rel\n\n"

        # Input attribute specifications
        for fname, ftype in self._features:
            s += "@ATTRIBUTE %-30r %s\n" % (fname, ftype)

        # Label attribute specification
        s += "@ATTRIBUTE %-30r {%s}\n" % ("-label-", ",".join(self._labels))

        return s

    def data_section(self, tokens, labeled=None):
        """
        Returns the ARFF data section for the given data.

        :param tokens: a list of featuresets (dicts) or labelled featuresets
            which are tuples (featureset, label).
        :param labeled: Indicates whether the given tokens are labeled
            or not.  If None, then the tokens will be assumed to be
            labeled if the first token's value is a tuple or list.
        """
        # Check if the tokens are labeled or unlabeled.  If unlabeled,
        # then use 'None'
        if labeled is None:
            labeled = tokens and isinstance(tokens[0], (tuple, list))
        if not labeled:
            tokens = [(tok, None) for tok in tokens]

        # Data section
        s = "\n@DATA\n"
        for tok, label in tokens:
            for fname, ftype in self._features:
                s += "%s," % self._fmt_arff_val(tok.get(fname))
            s += "%s\n" % self._fmt_arff_val(label)

        return s

    def _fmt_arff_val(self, fval):
        if fval is None:
            return "?"
        elif isinstance(fval, (bool, int)):
            return "%s" % fval
        elif isinstance(fval, float):
            return "%r" % fval
        else:
            return "%r" % fval


if __name__ == "__main__":
    from nltk.classify.util import binary_names_demo_features, names_demo

    def make_classifier(featuresets):
        return WekaClassifier.train("/tmp/name.model", featuresets, "C4.5")

    classifier = names_demo(make_classifier, binary_names_demo_features)

# === NexusCore/openenv\Lib\site-packages\anyio\abc\_eventloop.py ===
from __future__ import annotations

import math
import sys
from abc import ABCMeta, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import AbstractContextManager
from os import PathLike
from signal import Signals
from socket import AddressFamily, SocketKind, socket
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
    overload,
)

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from _typeshed import HasFileno

    from .._core._synchronization import CapacityLimiter, Event, Lock, Semaphore
    from .._core._tasks import CancelScope
    from .._core._testing import TaskInfo
    from ..from_thread import BlockingPortal
    from ._sockets import (
        ConnectedUDPSocket,
        ConnectedUNIXDatagramSocket,
        IPSockAddrType,
        SocketListener,
        SocketStream,
        UDPSocket,
        UNIXDatagramSocket,
        UNIXSocketStream,
    )
    from ._subprocesses import Process
    from ._tasks import TaskGroup
    from ._testing import TestRunner

T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")
StrOrBytesPath: TypeAlias = Union[str, bytes, "PathLike[str]", "PathLike[bytes]"]


class AsyncBackend(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def run(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        kwargs: dict[str, Any],
        options: dict[str, Any],
    ) -> T_Retval:
        """
        Run the given coroutine function in an asynchronous event loop.

        The current thread must not be already running an event loop.

        :param func: a coroutine function
        :param args: positional arguments to ``func``
        :param kwargs: positional arguments to ``func``
        :param options: keyword arguments to call the backend ``run()`` implementation
            with
        :return: the return value of the coroutine function
        """

    @classmethod
    @abstractmethod
    def current_token(cls) -> object:
        """

        :return:
        """

    @classmethod
    @abstractmethod
    def current_time(cls) -> float:
        """
        Return the current value of the event loop's internal clock.

        :return: the clock value (seconds)
        """

    @classmethod
    @abstractmethod
    def cancelled_exception_class(cls) -> type[BaseException]:
        """Return the exception class that is raised in a task if it's cancelled."""

    @classmethod
    @abstractmethod
    async def checkpoint(cls) -> None:
        """
        Check if the task has been cancelled, and allow rescheduling of other tasks.

        This is effectively the same as running :meth:`checkpoint_if_cancelled` and then
        :meth:`cancel_shielded_checkpoint`.
        """

    @classmethod
    async def checkpoint_if_cancelled(cls) -> None:
        """
        Check if the current task group has been cancelled.

        This will check if the task has been cancelled, but will not allow other tasks
        to be scheduled if not.

        """
        if cls.current_effective_deadline() == -math.inf:
            await cls.checkpoint()

    @classmethod
    async def cancel_shielded_checkpoint(cls) -> None:
        """
        Allow the rescheduling of other tasks.

        This will give other tasks the opportunity to run, but without checking if the
        current task group has been cancelled, unlike with :meth:`checkpoint`.

        """
        with cls.create_cancel_scope(shield=True):
            await cls.sleep(0)

    @classmethod
    @abstractmethod
    async def sleep(cls, delay: float) -> None:
        """
        Pause the current task for the specified duration.

        :param delay: the duration, in seconds
        """

    @classmethod
    @abstractmethod
    def create_cancel_scope(
        cls, *, deadline: float = math.inf, shield: bool = False
    ) -> CancelScope:
        pass

    @classmethod
    @abstractmethod
    def current_effective_deadline(cls) -> float:
        """
        Return the nearest deadline among all the cancel scopes effective for the
        current task.

        :return:
            - a clock value from the event loop's internal clock
            - ``inf`` if there is no deadline in effect
            - ``-inf`` if the current scope has been cancelled
        :rtype: float
        """

    @classmethod
    @abstractmethod
    def create_task_group(cls) -> TaskGroup:
        pass

    @classmethod
    @abstractmethod
    def create_event(cls) -> Event:
        pass

    @classmethod
    @abstractmethod
    def create_lock(cls, *, fast_acquire: bool) -> Lock:
        pass

    @classmethod
    @abstractmethod
    def create_semaphore(
        cls,
        initial_value: int,
        *,
        max_value: int | None = None,
        fast_acquire: bool = False,
    ) -> Semaphore:
        pass

    @classmethod
    @abstractmethod
    def create_capacity_limiter(cls, total_tokens: float) -> CapacityLimiter:
        pass

    @classmethod
    @abstractmethod
    async def run_sync_in_worker_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        abandon_on_cancel: bool = False,
        limiter: CapacityLimiter | None = None,
    ) -> T_Retval:
        pass

    @classmethod
    @abstractmethod
    def check_cancelled(cls) -> None:
        pass

    @classmethod
    @abstractmethod
    def run_async_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], Awaitable[T_Retval]],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        pass

    @classmethod
    @abstractmethod
    def run_sync_from_thread(
        cls,
        func: Callable[[Unpack[PosArgsT]], T_Retval],
        args: tuple[Unpack[PosArgsT]],
        token: object,
    ) -> T_Retval:
        pass

    @classmethod
    @abstractmethod
    def create_blocking_portal(cls) -> BlockingPortal:
        pass

    @classmethod
    @abstractmethod
    async def open_process(
        cls,
        command: StrOrBytesPath | Sequence[StrOrBytesPath],
        *,
        stdin: int | IO[Any] | None,
        stdout: int | IO[Any] | None,
        stderr: int | IO[Any] | None,
        **kwargs: Any,
    ) -> Process:
        pass

    @classmethod
    @abstractmethod
    def setup_process_pool_exit_at_shutdown(cls, workers: set[Process]) -> None:
        pass

    @classmethod
    @abstractmethod
    async def connect_tcp(
        cls, host: str, port: int, local_address: IPSockAddrType | None = None
    ) -> SocketStream:
        pass

    @classmethod
    @abstractmethod
    async def connect_unix(cls, path: str | bytes) -> UNIXSocketStream:
        pass

    @classmethod
    @abstractmethod
    def create_tcp_listener(cls, sock: socket) -> SocketListener:
        pass

    @classmethod
    @abstractmethod
    def create_unix_listener(cls, sock: socket) -> SocketListener:
        pass

    @classmethod
    @abstractmethod
    async def create_udp_socket(
        cls,
        family: AddressFamily,
        local_address: IPSockAddrType | None,
        remote_address: IPSockAddrType | None,
        reuse_port: bool,
    ) -> UDPSocket | ConnectedUDPSocket:
        pass

    @classmethod
    @overload
    async def create_unix_datagram_socket(
        cls, raw_socket: socket, remote_path: None
    ) -> UNIXDatagramSocket: ...

    @classmethod
    @overload
    async def create_unix_datagram_socket(
        cls, raw_socket: socket, remote_path: str | bytes
    ) -> ConnectedUNIXDatagramSocket: ...

    @classmethod
    @abstractmethod
    async def create_unix_datagram_socket(
        cls, raw_socket: socket, remote_path: str | bytes | None
    ) -> UNIXDatagramSocket | ConnectedUNIXDatagramSocket:
        pass

    @classmethod
    @abstractmethod
    async def getaddrinfo(
        cls,
        host: bytes | str | None,
        port: str | int | None,
        *,
        family: int | AddressFamily = 0,
        type: int | SocketKind = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> Sequence[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        pass

    @classmethod
    @abstractmethod
    async def getnameinfo(
        cls, sockaddr: IPSockAddrType, flags: int = 0
    ) -> tuple[str, str]:
        pass

    @classmethod
    @abstractmethod
    async def wait_readable(cls, obj: HasFileno | int) -> None:
        pass

    @classmethod
    @abstractmethod
    async def wait_writable(cls, obj: HasFileno | int) -> None:
        pass

    @classmethod
    @abstractmethod
    def current_default_thread_limiter(cls) -> CapacityLimiter:
        pass

    @classmethod
    @abstractmethod
    def open_signal_receiver(
        cls, *signals: Signals
    ) -> AbstractContextManager[AsyncIterator[Signals]]:
        pass

    @classmethod
    @abstractmethod
    def get_current_task(cls) -> TaskInfo:
        pass

    @classmethod
    @abstractmethod
    def get_running_tasks(cls) -> Sequence[TaskInfo]:
        pass

    @classmethod
    @abstractmethod
    async def wait_all_tasks_blocked(cls) -> None:
        pass

    @classmethod
    @abstractmethod
    def create_test_runner(cls, options: dict[str, Any]) -> TestRunner:
        pass

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\list.py ===
import json
import logging
from optparse import Values
from typing import TYPE_CHECKING, Generator, List, Optional, Sequence, Tuple, cast

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.cli import cmdoptions
from pip._internal.cli.index_command import IndexGroupCommand
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.metadata import BaseDistribution, get_environment
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.utils.compat import stdlib_pkgs
from pip._internal.utils.misc import tabulate, write_output

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.network.session import PipSession

    class _DistWithLatestInfo(BaseDistribution):
        """Give the distribution object a couple of extra fields.

        These will be populated during ``get_outdated()``. This is dirty but
        makes the rest of the code much cleaner.
        """

        latest_version: Version
        latest_filetype: str

    _ProcessedDists = Sequence[_DistWithLatestInfo]


logger = logging.getLogger(__name__)


class ListCommand(IndexGroupCommand):
    """
    List installed packages, including editables.

    Packages are listed in a case-insensitive sorted order.
    """

    ignore_require_venv = True
    usage = """
      %prog [options]"""

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-o",
            "--outdated",
            action="store_true",
            default=False,
            help="List outdated packages",
        )
        self.cmd_opts.add_option(
            "-u",
            "--uptodate",
            action="store_true",
            default=False,
            help="List uptodate packages",
        )
        self.cmd_opts.add_option(
            "-e",
            "--editable",
            action="store_true",
            default=False,
            help="List editable projects.",
        )
        self.cmd_opts.add_option(
            "-l",
            "--local",
            action="store_true",
            default=False,
            help=(
                "If in a virtualenv that has global access, do not list "
                "globally-installed packages."
            ),
        )
        self.cmd_opts.add_option(
            "--user",
            dest="user",
            action="store_true",
            default=False,
            help="Only output packages installed in user-site.",
        )
        self.cmd_opts.add_option(cmdoptions.list_path())
        self.cmd_opts.add_option(
            "--pre",
            action="store_true",
            default=False,
            help=(
                "Include pre-release and development versions. By default, "
                "pip only finds stable versions."
            ),
        )

        self.cmd_opts.add_option(
            "--format",
            action="store",
            dest="list_format",
            default="columns",
            choices=("columns", "freeze", "json"),
            help=(
                "Select the output format among: columns (default), freeze, or json. "
                "The 'freeze' format cannot be used with the --outdated option."
            ),
        )

        self.cmd_opts.add_option(
            "--not-required",
            action="store_true",
            dest="not_required",
            help="List packages that are not dependencies of installed packages.",
        )

        self.cmd_opts.add_option(
            "--exclude-editable",
            action="store_false",
            dest="include_editable",
            help="Exclude editable package from output.",
        )
        self.cmd_opts.add_option(
            "--include-editable",
            action="store_true",
            dest="include_editable",
            help="Include editable package from output.",
            default=True,
        )
        self.cmd_opts.add_option(cmdoptions.list_exclude())
        index_opts = cmdoptions.make_option_group(cmdoptions.index_group, self.parser)

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    def handle_pip_version_check(self, options: Values) -> None:
        if options.outdated or options.uptodate:
            super().handle_pip_version_check(options)

    def _build_package_finder(
        self, options: Values, session: "PipSession"
    ) -> "PackageFinder":
        """
        Create a package finder appropriate to this list command.
        """
        # Lazy import the heavy index modules as most list invocations won't need 'em.
        from pip._internal.index.collector import LinkCollector
        from pip._internal.index.package_finder import PackageFinder

        link_collector = LinkCollector.create(session, options=options)

        # Pass allow_yanked=False to ignore yanked versions.
        selection_prefs = SelectionPreferences(
            allow_yanked=False,
            allow_all_prereleases=options.pre,
        )

        return PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )

    def run(self, options: Values, args: List[str]) -> int:
        if options.outdated and options.uptodate:
            raise CommandError("Options --outdated and --uptodate cannot be combined.")

        if options.outdated and options.list_format == "freeze":
            raise CommandError(
                "List format 'freeze' cannot be used with the --outdated option."
            )

        cmdoptions.check_list_path_option(options)

        skip = set(stdlib_pkgs)
        if options.excludes:
            skip.update(canonicalize_name(n) for n in options.excludes)

        packages: _ProcessedDists = [
            cast("_DistWithLatestInfo", d)
            for d in get_environment(options.path).iter_installed_distributions(
                local_only=options.local,
                user_only=options.user,
                editables_only=options.editable,
                include_editables=options.include_editable,
                skip=skip,
            )
        ]

        # get_not_required must be called firstly in order to find and
        # filter out all dependencies correctly. Otherwise a package
        # can't be identified as requirement because some parent packages
        # could be filtered out before.
        if options.not_required:
            packages = self.get_not_required(packages, options)

        if options.outdated:
            packages = self.get_outdated(packages, options)
        elif options.uptodate:
            packages = self.get_uptodate(packages, options)

        self.output_package_listing(packages, options)
        return SUCCESS

    def get_outdated(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        return [
            dist
            for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version > dist.version
        ]

    def get_uptodate(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        return [
            dist
            for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version == dist.version
        ]

    def get_not_required(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        dep_keys = {
            canonicalize_name(dep.name)
            for dist in packages
            for dep in (dist.iter_dependencies() or ())
        }

        # Create a set to remove duplicate packages, and cast it to a list
        # to keep the return type consistent with get_outdated and
        # get_uptodate
        return list({pkg for pkg in packages if pkg.canonical_name not in dep_keys})

    def iter_packages_latest_infos(
        self, packages: "_ProcessedDists", options: Values
    ) -> Generator["_DistWithLatestInfo", None, None]:
        with self._build_session(options) as session:
            finder = self._build_package_finder(options, session)

            def latest_info(
                dist: "_DistWithLatestInfo",
            ) -> Optional["_DistWithLatestInfo"]:
                all_candidates = finder.find_all_candidates(dist.canonical_name)
                if not options.pre:
                    # Remove prereleases
                    all_candidates = [
                        candidate
                        for candidate in all_candidates
                        if not candidate.version.is_prerelease
                    ]

                evaluator = finder.make_candidate_evaluator(
                    project_name=dist.canonical_name,
                )
                best_candidate = evaluator.sort_best_candidate(all_candidates)
                if best_candidate is None:
                    return None

                remote_version = best_candidate.version
                if best_candidate.link.is_wheel:
                    typ = "wheel"
                else:
                    typ = "sdist"
                dist.latest_version = remote_version
                dist.latest_filetype = typ
                return dist

            for dist in map(latest_info, packages):
                if dist is not None:
                    yield dist

    def output_package_listing(
        self, packages: "_ProcessedDists", options: Values
    ) -> None:
        packages = sorted(
            packages,
            key=lambda dist: dist.canonical_name,
        )
        if options.list_format == "columns" and packages:
            data, header = format_for_columns(packages, options)
            self.output_package_listing_columns(data, header)
        elif options.list_format == "freeze":
            for dist in packages:
                if options.verbose >= 1:
                    write_output(
                        "%s==%s (%s)", dist.raw_name, dist.version, dist.location
                    )
                else:
                    write_output("%s==%s", dist.raw_name, dist.version)
        elif options.list_format == "json":
            write_output(format_for_json(packages, options))

    def output_package_listing_columns(
        self, data: List[List[str]], header: List[str]
    ) -> None:
        # insert the header first: we need to know the size of column names
        if len(data) > 0:
            data.insert(0, header)

        pkg_strings, sizes = tabulate(data)

        # Create and add a separator.
        if len(data) > 0:
            pkg_strings.insert(1, " ".join("-" * x for x in sizes))

        for val in pkg_strings:
            write_output(val)


def format_for_columns(
    pkgs: "_ProcessedDists", options: Values
) -> Tuple[List[List[str]], List[str]]:
    """
    Convert the package data into something usable
    by output_package_listing_columns.
    """
    header = ["Package", "Version"]

    running_outdated = options.outdated
    if running_outdated:
        header.extend(["Latest", "Type"])

    has_editables = any(x.editable for x in pkgs)
    if has_editables:
        header.append("Editable project location")

    if options.verbose >= 1:
        header.append("Location")
    if options.verbose >= 1:
        header.append("Installer")

    data = []
    for proj in pkgs:
        # if we're working on the 'outdated' list, separate out the
        # latest_version and type
        row = [proj.raw_name, proj.raw_version]

        if running_outdated:
            row.append(str(proj.latest_version))
            row.append(proj.latest_filetype)

        if has_editables:
            row.append(proj.editable_project_location or "")

        if options.verbose >= 1:
            row.append(proj.location or "")
        if options.verbose >= 1:
            row.append(proj.installer)

        data.append(row)

    return data, header


def format_for_json(packages: "_ProcessedDists", options: Values) -> str:
    data = []
    for dist in packages:
        info = {
            "name": dist.raw_name,
            "version": str(dist.version),
        }
        if options.verbose >= 1:
            info["location"] = dist.location or ""
            info["installer"] = dist.installer
        if options.outdated:
            info["latest_version"] = str(dist.latest_version)
            info["latest_filetype"] = dist.latest_filetype
        editable_project_location = dist.editable_project_location
        if editable_project_location:
            info["editable_project_location"] = editable_project_location
        data.append(info)
    return json.dumps(data)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\live.py ===
import sys
from threading import Event, RLock, Thread
from types import TracebackType
from typing import IO, Any, Callable, List, Optional, TextIO, Type, cast

from . import get_console
from .console import Console, ConsoleRenderable, RenderableType, RenderHook
from .control import Control
from .file_proxy import FileProxy
from .jupyter import JupyterMixin
from .live_render import LiveRender, VerticalOverflowMethod
from .screen import Screen
from .text import Text


class _RefreshThread(Thread):
    """A thread that calls refresh() at regular intervals."""

    def __init__(self, live: "Live", refresh_per_second: float) -> None:
        self.live = live
        self.refresh_per_second = refresh_per_second
        self.done = Event()
        super().__init__(daemon=True)

    def stop(self) -> None:
        self.done.set()

    def run(self) -> None:
        while not self.done.wait(1 / self.refresh_per_second):
            with self.live._lock:
                if not self.done.is_set():
                    self.live.refresh()


class Live(JupyterMixin, RenderHook):
    """Renders an auto-updating live display of any given renderable.

    Args:
        renderable (RenderableType, optional): The renderable to live display. Defaults to displaying nothing.
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        screen (bool, optional): Enable alternate screen mode. Defaults to False.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()` or `update()` with refresh flag. Defaults to True
        refresh_per_second (float, optional): Number of times per second to refresh the live display. Defaults to 4.
        transient (bool, optional): Clear the renderable on exit (has no effect when screen=True). Defaults to False.
        redirect_stdout (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr (bool, optional): Enable redirection of stderr. Defaults to True.
        vertical_overflow (VerticalOverflowMethod, optional): How to handle renderable when it is too tall for the console. Defaults to "ellipsis".
        get_renderable (Callable[[], RenderableType], optional): Optional callable to get renderable. Defaults to None.
    """

    def __init__(
        self,
        renderable: Optional[RenderableType] = None,
        *,
        console: Optional[Console] = None,
        screen: bool = False,
        auto_refresh: bool = True,
        refresh_per_second: float = 4,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        vertical_overflow: VerticalOverflowMethod = "ellipsis",
        get_renderable: Optional[Callable[[], RenderableType]] = None,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._renderable = renderable
        self.console = console if console is not None else get_console()
        self._screen = screen
        self._alt_screen = False

        self._redirect_stdout = redirect_stdout
        self._redirect_stderr = redirect_stderr
        self._restore_stdout: Optional[IO[str]] = None
        self._restore_stderr: Optional[IO[str]] = None

        self._lock = RLock()
        self.ipy_widget: Optional[Any] = None
        self.auto_refresh = auto_refresh
        self._started: bool = False
        self.transient = True if screen else transient

        self._refresh_thread: Optional[_RefreshThread] = None
        self.refresh_per_second = refresh_per_second

        self.vertical_overflow = vertical_overflow
        self._get_renderable = get_renderable
        self._live_render = LiveRender(
            self.get_renderable(), vertical_overflow=vertical_overflow
        )

    @property
    def is_started(self) -> bool:
        """Check if live display has been started."""
        return self._started

    def get_renderable(self) -> RenderableType:
        renderable = (
            self._get_renderable()
            if self._get_renderable is not None
            else self._renderable
        )
        return renderable or ""

    def start(self, refresh: bool = False) -> None:
        """Start live rendering display.

        Args:
            refresh (bool, optional): Also refresh. Defaults to False.
        """
        with self._lock:
            if self._started:
                return
            self.console.set_live(self)
            self._started = True
            if self._screen:
                self._alt_screen = self.console.set_alt_screen(True)
            self.console.show_cursor(False)
            self._enable_redirect_io()
            self.console.push_render_hook(self)
            if refresh:
                try:
                    self.refresh()
                except Exception:
                    # If refresh fails, we want to stop the redirection of sys.stderr,
                    # so the error stacktrace is properly displayed in the terminal.
                    # (or, if the code that calls Rich captures the exception and wants to display something,
                    # let this be displayed in the terminal).
                    self.stop()
                    raise
            if self.auto_refresh:
                self._refresh_thread = _RefreshThread(self, self.refresh_per_second)
                self._refresh_thread.start()

    def stop(self) -> None:
        """Stop live rendering display."""
        with self._lock:
            if not self._started:
                return
            self.console.clear_live()
            self._started = False

            if self.auto_refresh and self._refresh_thread is not None:
                self._refresh_thread.stop()
                self._refresh_thread = None
            # allow it to fully render on the last even if overflow
            self.vertical_overflow = "visible"
            with self.console:
                try:
                    if not self._alt_screen and not self.console.is_jupyter:
                        self.refresh()
                finally:
                    self._disable_redirect_io()
                    self.console.pop_render_hook()
                    if not self._alt_screen and self.console.is_terminal:
                        self.console.line()
                    self.console.show_cursor(True)
                    if self._alt_screen:
                        self.console.set_alt_screen(False)

                    if self.transient and not self._alt_screen:
                        self.console.control(self._live_render.restore_cursor())
                    if self.ipy_widget is not None and self.transient:
                        self.ipy_widget.close()  # pragma: no cover

    def __enter__(self) -> "Live":
        self.start(refresh=self._renderable is not None)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def _enable_redirect_io(self) -> None:
        """Enable redirecting of stdout / stderr."""
        if self.console.is_terminal or self.console.is_jupyter:
            if self._redirect_stdout and not isinstance(sys.stdout, FileProxy):
                self._restore_stdout = sys.stdout
                sys.stdout = cast("TextIO", FileProxy(self.console, sys.stdout))
            if self._redirect_stderr and not isinstance(sys.stderr, FileProxy):
                self._restore_stderr = sys.stderr
                sys.stderr = cast("TextIO", FileProxy(self.console, sys.stderr))

    def _disable_redirect_io(self) -> None:
        """Disable redirecting of stdout / stderr."""
        if self._restore_stdout:
            sys.stdout = cast("TextIO", self._restore_stdout)
            self._restore_stdout = None
        if self._restore_stderr:
            sys.stderr = cast("TextIO", self._restore_stderr)
            self._restore_stderr = None

    @property
    def renderable(self) -> RenderableType:
        """Get the renderable that is being displayed

        Returns:
            RenderableType: Displayed renderable.
        """
        renderable = self.get_renderable()
        return Screen(renderable) if self._alt_screen else renderable

    def update(self, renderable: RenderableType, *, refresh: bool = False) -> None:
        """Update the renderable that is being displayed

        Args:
            renderable (RenderableType): New renderable to use.
            refresh (bool, optional): Refresh the display. Defaults to False.
        """
        if isinstance(renderable, str):
            renderable = self.console.render_str(renderable)
        with self._lock:
            self._renderable = renderable
            if refresh:
                self.refresh()

    def refresh(self) -> None:
        """Update the display of the Live Render."""
        with self._lock:
            self._live_render.set_renderable(self.renderable)
            if self.console.is_jupyter:  # pragma: no cover
                try:
                    from IPython.display import display
                    from ipywidgets import Output
                except ImportError:
                    import warnings

                    warnings.warn('install "ipywidgets" for Jupyter support')
                else:
                    if self.ipy_widget is None:
                        self.ipy_widget = Output()
                        display(self.ipy_widget)

                    with self.ipy_widget:
                        self.ipy_widget.clear_output(wait=True)
                        self.console.print(self._live_render.renderable)
            elif self.console.is_terminal and not self.console.is_dumb_terminal:
                with self.console:
                    self.console.print(Control())
            elif (
                not self._started and not self.transient
            ):  # if it is finished allow files or dumb-terminals to see final result
                with self.console:
                    self.console.print(Control())

    def process_renderables(
        self, renderables: List[ConsoleRenderable]
    ) -> List[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        self._live_render.vertical_overflow = self.vertical_overflow
        if self.console.is_interactive:
            # lock needs acquiring as user can modify live_render renderable at any time unlike in Progress.
            with self._lock:
                reset = (
                    Control.home()
                    if self._alt_screen
                    else self._live_render.position_cursor()
                )
                renderables = [reset, *renderables, self._live_render]
        elif (
            not self._started and not self.transient
        ):  # if it is finished render the final output for files or dumb_terminals
            renderables = [*renderables, self._live_render]

        return renderables


if __name__ == "__main__":  # pragma: no cover
    import random
    import time
    from itertools import cycle
    from typing import Dict, List, Tuple

    from .align import Align
    from .console import Console
    from .live import Live as Live
    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    console = Console()

    syntax = Syntax(
        '''def loop_last(values: Iterable[T]) -> Iterable[Tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    for value in iter_values:
        yield False, previous_value
        previous_value = value
    yield True, previous_value''',
        "python",
        line_numbers=True,
    )

    table = Table("foo", "bar", "baz")
    table.add_row("1", "2", "3")

    progress_renderables = [
        "You can make the terminal shorter and taller to see the live table hide"
        "Text may be printed while the progress bars are rendering.",
        Panel("In fact, [i]any[/i] renderable will work"),
        "Such as [magenta]tables[/]...",
        table,
        "Pretty printed structures...",
        {"type": "example", "text": "Pretty printed"},
        "Syntax...",
        syntax,
        Rule("Give it a try!"),
    ]

    examples = cycle(progress_renderables)

    exchanges = [
        "SGD",
        "MYR",
        "EUR",
        "USD",
        "AUD",
        "JPY",
        "CNH",
        "HKD",
        "CAD",
        "INR",
        "DKK",
        "GBP",
        "RUB",
        "NZD",
        "MXN",
        "IDR",
        "TWD",
        "THB",
        "VND",
    ]
    with Live(console=console) as live_table:
        exchange_rate_dict: Dict[Tuple[str, str], float] = {}

        for index in range(100):
            select_exchange = exchanges[index % len(exchanges)]

            for exchange in exchanges:
                if exchange == select_exchange:
                    continue
                time.sleep(0.4)
                if random.randint(0, 10) < 1:
                    console.log(next(examples))
                exchange_rate_dict[(select_exchange, exchange)] = 200 / (
                    (random.random() * 320) + 1
                )
                if len(exchange_rate_dict) > len(exchanges) - 1:
                    exchange_rate_dict.pop(list(exchange_rate_dict.keys())[0])
                table = Table(title="Exchange Rates")

                table.add_column("Source Currency")
                table.add_column("Destination Currency")
                table.add_column("Exchange Rate")

                for (source, dest), exchange_rate in exchange_rate_dict.items():
                    table.add_row(
                        source,
                        dest,
                        Text(
                            f"{exchange_rate:.4f}",
                            style="red" if exchange_rate < 1.0 else "green",
                        ),
                    )

                live_table.update(Align.center(table))

# === NexusCore/openenv\Lib\site-packages\PIL\PpmImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# PPM support for PIL
#
# History:
#       96-03-24 fl     Created
#       98-03-06 fl     Write RGBA images (as RGB, that is)
#
# Copyright (c) Secret Labs AB 1997-98.
# Copyright (c) Fredrik Lundh 1996.
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import math
from typing import IO

from . import Image, ImageFile
from ._binary import i16be as i16
from ._binary import o8
from ._binary import o32le as o32

#
# --------------------------------------------------------------------

b_whitespace = b"\x20\x09\x0a\x0b\x0c\x0d"

MODES = {
    # standard
    b"P1": "1",
    b"P2": "L",
    b"P3": "RGB",
    b"P4": "1",
    b"P5": "L",
    b"P6": "RGB",
    # extensions
    b"P0CMYK": "CMYK",
    b"Pf": "F",
    # PIL extensions (for test purposes only)
    b"PyP": "P",
    b"PyRGBA": "RGBA",
    b"PyCMYK": "CMYK",
}


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(b"P") and prefix[1] in b"0123456fy"


##
# Image plugin for PBM, PGM, and PPM images.


class PpmImageFile(ImageFile.ImageFile):
    format = "PPM"
    format_description = "Pbmplus image"

    def _read_magic(self) -> bytes:
        assert self.fp is not None

        magic = b""
        # read until whitespace or longest available magic number
        for _ in range(6):
            c = self.fp.read(1)
            if not c or c in b_whitespace:
                break
            magic += c
        return magic

    def _read_token(self) -> bytes:
        assert self.fp is not None

        token = b""
        while len(token) <= 10:  # read until next whitespace or limit of 10 characters
            c = self.fp.read(1)
            if not c:
                break
            elif c in b_whitespace:  # token ended
                if not token:
                    # skip whitespace at start
                    continue
                break
            elif c == b"#":
                # ignores rest of the line; stops at CR, LF or EOF
                while self.fp.read(1) not in b"\r\n":
                    pass
                continue
            token += c
        if not token:
            # Token was not even 1 byte
            msg = "Reached EOF while reading header"
            raise ValueError(msg)
        elif len(token) > 10:
            msg = f"Token too long in file header: {token.decode()}"
            raise ValueError(msg)
        return token

    def _open(self) -> None:
        assert self.fp is not None

        magic_number = self._read_magic()
        try:
            mode = MODES[magic_number]
        except KeyError:
            msg = "not a PPM file"
            raise SyntaxError(msg)
        self._mode = mode

        if magic_number in (b"P1", b"P4"):
            self.custom_mimetype = "image/x-portable-bitmap"
        elif magic_number in (b"P2", b"P5"):
            self.custom_mimetype = "image/x-portable-graymap"
        elif magic_number in (b"P3", b"P6"):
            self.custom_mimetype = "image/x-portable-pixmap"

        self._size = int(self._read_token()), int(self._read_token())

        decoder_name = "raw"
        if magic_number in (b"P1", b"P2", b"P3"):
            decoder_name = "ppm_plain"

        args: str | tuple[str | int, ...]
        if mode == "1":
            args = "1;I"
        elif mode == "F":
            scale = float(self._read_token())
            if scale == 0.0 or not math.isfinite(scale):
                msg = "scale must be finite and non-zero"
                raise ValueError(msg)
            self.info["scale"] = abs(scale)

            rawmode = "F;32F" if scale < 0 else "F;32BF"
            args = (rawmode, 0, -1)
        else:
            maxval = int(self._read_token())
            if not 0 < maxval < 65536:
                msg = "maxval must be greater than 0 and less than 65536"
                raise ValueError(msg)
            if maxval > 255 and mode == "L":
                self._mode = "I"

            rawmode = mode
            if decoder_name != "ppm_plain":
                # If maxval matches a bit depth, use the raw decoder directly
                if maxval == 65535 and mode == "L":
                    rawmode = "I;16B"
                elif maxval != 255:
                    decoder_name = "ppm"

            args = rawmode if decoder_name == "raw" else (rawmode, maxval)
        self.tile = [
            ImageFile._Tile(decoder_name, (0, 0) + self.size, self.fp.tell(), args)
        ]


#
# --------------------------------------------------------------------


class PpmPlainDecoder(ImageFile.PyDecoder):
    _pulls_fd = True
    _comment_spans: bool

    def _read_block(self) -> bytes:
        assert self.fd is not None

        return self.fd.read(ImageFile.SAFEBLOCK)

    def _find_comment_end(self, block: bytes, start: int = 0) -> int:
        a = block.find(b"\n", start)
        b = block.find(b"\r", start)
        return min(a, b) if a * b > 0 else max(a, b)  # lowest nonnegative index (or -1)

    def _ignore_comments(self, block: bytes) -> bytes:
        if self._comment_spans:
            # Finish current comment
            while block:
                comment_end = self._find_comment_end(block)
                if comment_end != -1:
                    # Comment ends in this block
                    # Delete tail of comment
                    block = block[comment_end + 1 :]
                    break
                else:
                    # Comment spans whole block
                    # So read the next block, looking for the end
                    block = self._read_block()

        # Search for any further comments
        self._comment_spans = False
        while True:
            comment_start = block.find(b"#")
            if comment_start == -1:
                # No comment found
                break
            comment_end = self._find_comment_end(block, comment_start)
            if comment_end != -1:
                # Comment ends in this block
                # Delete comment
                block = block[:comment_start] + block[comment_end + 1 :]
            else:
                # Comment continues to next block(s)
                block = block[:comment_start]
                self._comment_spans = True
                break
        return block

    def _decode_bitonal(self) -> bytearray:
        """
        This is a separate method because in the plain PBM format, all data tokens are
        exactly one byte, so the inter-token whitespace is optional.
        """
        data = bytearray()
        total_bytes = self.state.xsize * self.state.ysize

        while len(data) != total_bytes:
            block = self._read_block()  # read next block
            if not block:
                # eof
                break

            block = self._ignore_comments(block)

            tokens = b"".join(block.split())
            for token in tokens:
                if token not in (48, 49):
                    msg = b"Invalid token for this mode: %s" % bytes([token])
                    raise ValueError(msg)
            data = (data + tokens)[:total_bytes]
        invert = bytes.maketrans(b"01", b"\xff\x00")
        return data.translate(invert)

    def _decode_blocks(self, maxval: int) -> bytearray:
        data = bytearray()
        max_len = 10
        out_byte_count = 4 if self.mode == "I" else 1
        out_max = 65535 if self.mode == "I" else 255
        bands = Image.getmodebands(self.mode)
        total_bytes = self.state.xsize * self.state.ysize * bands * out_byte_count

        half_token = b""
        while len(data) != total_bytes:
            block = self._read_block()  # read next block
            if not block:
                if half_token:
                    block = bytearray(b" ")  # flush half_token
                else:
                    # eof
                    break

            block = self._ignore_comments(block)

            if half_token:
                block = half_token + block  # stitch half_token to new block
                half_token = b""

            tokens = block.split()

            if block and not block[-1:].isspace():  # block might split token
                half_token = tokens.pop()  # save half token for later
                if len(half_token) > max_len:  # prevent buildup of half_token
                    msg = (
                        b"Token too long found in data: %s" % half_token[: max_len + 1]
                    )
                    raise ValueError(msg)

            for token in tokens:
                if len(token) > max_len:
                    msg = b"Token too long found in data: %s" % token[: max_len + 1]
                    raise ValueError(msg)
                value = int(token)
                if value < 0:
                    msg_str = f"Channel value is negative: {value}"
                    raise ValueError(msg_str)
                if value > maxval:
                    msg_str = f"Channel value too large for this mode: {value}"
                    raise ValueError(msg_str)
                value = round(value / maxval * out_max)
                data += o32(value) if self.mode == "I" else o8(value)
                if len(data) == total_bytes:  # finished!
                    break
        return data

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        self._comment_spans = False
        if self.mode == "1":
            data = self._decode_bitonal()
            rawmode = "1;8"
        else:
            maxval = self.args[-1]
            data = self._decode_blocks(maxval)
            rawmode = "I;32" if self.mode == "I" else self.mode
        self.set_as_raw(bytes(data), rawmode)
        return -1, 0


class PpmDecoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None

        data = bytearray()
        maxval = self.args[-1]
        in_byte_count = 1 if maxval < 256 else 2
        out_byte_count = 4 if self.mode == "I" else 1
        out_max = 65535 if self.mode == "I" else 255
        bands = Image.getmodebands(self.mode)
        dest_length = self.state.xsize * self.state.ysize * bands * out_byte_count
        while len(data) < dest_length:
            pixels = self.fd.read(in_byte_count * bands)
            if len(pixels) < in_byte_count * bands:
                # eof
                break
            for b in range(bands):
                value = (
                    pixels[b] if in_byte_count == 1 else i16(pixels, b * in_byte_count)
                )
                value = min(out_max, round(value / maxval * out_max))
                data += o32(value) if self.mode == "I" else o8(value)
        rawmode = "I;32" if self.mode == "I" else self.mode
        self.set_as_raw(bytes(data), rawmode)
        return -1, 0


#
# --------------------------------------------------------------------


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode == "1":
        rawmode, head = "1;I", b"P4"
    elif im.mode == "L":
        rawmode, head = "L", b"P5"
    elif im.mode in ("I", "I;16"):
        rawmode, head = "I;16B", b"P5"
    elif im.mode in ("RGB", "RGBA"):
        rawmode, head = "RGB", b"P6"
    elif im.mode == "F":
        rawmode, head = "F;32F", b"Pf"
    else:
        msg = f"cannot write mode {im.mode} as PPM"
        raise OSError(msg)
    fp.write(head + b"\n%d %d\n" % im.size)
    if head == b"P6":
        fp.write(b"255\n")
    elif head == b"P5":
        if rawmode == "L":
            fp.write(b"255\n")
        else:
            fp.write(b"65535\n")
    elif head == b"Pf":
        fp.write(b"-1.0\n")
    row_order = -1 if im.mode == "F" else 1
    ImageFile._save(
        im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 0, (rawmode, 0, row_order))]
    )


#
# --------------------------------------------------------------------


Image.register_open(PpmImageFile.format, PpmImageFile, _accept)
Image.register_save(PpmImageFile.format, _save)

Image.register_decoder("ppm", PpmDecoder)
Image.register_decoder("ppm_plain", PpmPlainDecoder)

Image.register_extensions(PpmImageFile.format, [".pbm", ".pgm", ".ppm", ".pnm", ".pfm"])

Image.register_mime(PpmImageFile.format, "image/x-portable-anymap")