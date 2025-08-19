
# === NexusCore/tools\exports\export_20250803_114325\combined_154.py ===

# === NexusCore/openenv\Lib\site-packages\PIL\DdsImagePlugin.py ===
"""
A Pillow loader for .dds files (S3TC-compressed aka DXTC)
Jerome Leclanche <jerome@leclan.ch>

Documentation:
https://web.archive.org/web/20170802060935/http://oss.sgi.com/projects/ogl-sample/registry/EXT/texture_compression_s3tc.txt

The contents of this file are hereby released in the public domain (CC0)
Full text of the CC0 license:
https://creativecommons.org/publicdomain/zero/1.0/
"""

from __future__ import annotations

import io
import struct
import sys
from enum import IntEnum, IntFlag
from typing import IO

from . import Image, ImageFile, ImagePalette
from ._binary import i32le as i32
from ._binary import o8
from ._binary import o32le as o32

# Magic ("DDS ")
DDS_MAGIC = 0x20534444


# DDS flags
class DDSD(IntFlag):
    CAPS = 0x1
    HEIGHT = 0x2
    WIDTH = 0x4
    PITCH = 0x8
    PIXELFORMAT = 0x1000
    MIPMAPCOUNT = 0x20000
    LINEARSIZE = 0x80000
    DEPTH = 0x800000


# DDS caps
class DDSCAPS(IntFlag):
    COMPLEX = 0x8
    TEXTURE = 0x1000
    MIPMAP = 0x400000


class DDSCAPS2(IntFlag):
    CUBEMAP = 0x200
    CUBEMAP_POSITIVEX = 0x400
    CUBEMAP_NEGATIVEX = 0x800
    CUBEMAP_POSITIVEY = 0x1000
    CUBEMAP_NEGATIVEY = 0x2000
    CUBEMAP_POSITIVEZ = 0x4000
    CUBEMAP_NEGATIVEZ = 0x8000
    VOLUME = 0x200000


# Pixel Format
class DDPF(IntFlag):
    ALPHAPIXELS = 0x1
    ALPHA = 0x2
    FOURCC = 0x4
    PALETTEINDEXED8 = 0x20
    RGB = 0x40
    LUMINANCE = 0x20000


# dxgiformat.h
class DXGI_FORMAT(IntEnum):
    UNKNOWN = 0
    R32G32B32A32_TYPELESS = 1
    R32G32B32A32_FLOAT = 2
    R32G32B32A32_UINT = 3
    R32G32B32A32_SINT = 4
    R32G32B32_TYPELESS = 5
    R32G32B32_FLOAT = 6
    R32G32B32_UINT = 7
    R32G32B32_SINT = 8
    R16G16B16A16_TYPELESS = 9
    R16G16B16A16_FLOAT = 10
    R16G16B16A16_UNORM = 11
    R16G16B16A16_UINT = 12
    R16G16B16A16_SNORM = 13
    R16G16B16A16_SINT = 14
    R32G32_TYPELESS = 15
    R32G32_FLOAT = 16
    R32G32_UINT = 17
    R32G32_SINT = 18
    R32G8X24_TYPELESS = 19
    D32_FLOAT_S8X24_UINT = 20
    R32_FLOAT_X8X24_TYPELESS = 21
    X32_TYPELESS_G8X24_UINT = 22
    R10G10B10A2_TYPELESS = 23
    R10G10B10A2_UNORM = 24
    R10G10B10A2_UINT = 25
    R11G11B10_FLOAT = 26
    R8G8B8A8_TYPELESS = 27
    R8G8B8A8_UNORM = 28
    R8G8B8A8_UNORM_SRGB = 29
    R8G8B8A8_UINT = 30
    R8G8B8A8_SNORM = 31
    R8G8B8A8_SINT = 32
    R16G16_TYPELESS = 33
    R16G16_FLOAT = 34
    R16G16_UNORM = 35
    R16G16_UINT = 36
    R16G16_SNORM = 37
    R16G16_SINT = 38
    R32_TYPELESS = 39
    D32_FLOAT = 40
    R32_FLOAT = 41
    R32_UINT = 42
    R32_SINT = 43
    R24G8_TYPELESS = 44
    D24_UNORM_S8_UINT = 45
    R24_UNORM_X8_TYPELESS = 46
    X24_TYPELESS_G8_UINT = 47
    R8G8_TYPELESS = 48
    R8G8_UNORM = 49
    R8G8_UINT = 50
    R8G8_SNORM = 51
    R8G8_SINT = 52
    R16_TYPELESS = 53
    R16_FLOAT = 54
    D16_UNORM = 55
    R16_UNORM = 56
    R16_UINT = 57
    R16_SNORM = 58
    R16_SINT = 59
    R8_TYPELESS = 60
    R8_UNORM = 61
    R8_UINT = 62
    R8_SNORM = 63
    R8_SINT = 64
    A8_UNORM = 65
    R1_UNORM = 66
    R9G9B9E5_SHAREDEXP = 67
    R8G8_B8G8_UNORM = 68
    G8R8_G8B8_UNORM = 69
    BC1_TYPELESS = 70
    BC1_UNORM = 71
    BC1_UNORM_SRGB = 72
    BC2_TYPELESS = 73
    BC2_UNORM = 74
    BC2_UNORM_SRGB = 75
    BC3_TYPELESS = 76
    BC3_UNORM = 77
    BC3_UNORM_SRGB = 78
    BC4_TYPELESS = 79
    BC4_UNORM = 80
    BC4_SNORM = 81
    BC5_TYPELESS = 82
    BC5_UNORM = 83
    BC5_SNORM = 84
    B5G6R5_UNORM = 85
    B5G5R5A1_UNORM = 86
    B8G8R8A8_UNORM = 87
    B8G8R8X8_UNORM = 88
    R10G10B10_XR_BIAS_A2_UNORM = 89
    B8G8R8A8_TYPELESS = 90
    B8G8R8A8_UNORM_SRGB = 91
    B8G8R8X8_TYPELESS = 92
    B8G8R8X8_UNORM_SRGB = 93
    BC6H_TYPELESS = 94
    BC6H_UF16 = 95
    BC6H_SF16 = 96
    BC7_TYPELESS = 97
    BC7_UNORM = 98
    BC7_UNORM_SRGB = 99
    AYUV = 100
    Y410 = 101
    Y416 = 102
    NV12 = 103
    P010 = 104
    P016 = 105
    OPAQUE_420 = 106
    YUY2 = 107
    Y210 = 108
    Y216 = 109
    NV11 = 110
    AI44 = 111
    IA44 = 112
    P8 = 113
    A8P8 = 114
    B4G4R4A4_UNORM = 115
    P208 = 130
    V208 = 131
    V408 = 132
    SAMPLER_FEEDBACK_MIN_MIP_OPAQUE = 189
    SAMPLER_FEEDBACK_MIP_REGION_USED_OPAQUE = 190


class D3DFMT(IntEnum):
    UNKNOWN = 0
    R8G8B8 = 20
    A8R8G8B8 = 21
    X8R8G8B8 = 22
    R5G6B5 = 23
    X1R5G5B5 = 24
    A1R5G5B5 = 25
    A4R4G4B4 = 26
    R3G3B2 = 27
    A8 = 28
    A8R3G3B2 = 29
    X4R4G4B4 = 30
    A2B10G10R10 = 31
    A8B8G8R8 = 32
    X8B8G8R8 = 33
    G16R16 = 34
    A2R10G10B10 = 35
    A16B16G16R16 = 36
    A8P8 = 40
    P8 = 41
    L8 = 50
    A8L8 = 51
    A4L4 = 52
    V8U8 = 60
    L6V5U5 = 61
    X8L8V8U8 = 62
    Q8W8V8U8 = 63
    V16U16 = 64
    A2W10V10U10 = 67
    D16_LOCKABLE = 70
    D32 = 71
    D15S1 = 73
    D24S8 = 75
    D24X8 = 77
    D24X4S4 = 79
    D16 = 80
    D32F_LOCKABLE = 82
    D24FS8 = 83
    D32_LOCKABLE = 84
    S8_LOCKABLE = 85
    L16 = 81
    VERTEXDATA = 100
    INDEX16 = 101
    INDEX32 = 102
    Q16W16V16U16 = 110
    R16F = 111
    G16R16F = 112
    A16B16G16R16F = 113
    R32F = 114
    G32R32F = 115
    A32B32G32R32F = 116
    CxV8U8 = 117
    A1 = 118
    A2B10G10R10_XR_BIAS = 119
    BINARYBUFFER = 199

    UYVY = i32(b"UYVY")
    R8G8_B8G8 = i32(b"RGBG")
    YUY2 = i32(b"YUY2")
    G8R8_G8B8 = i32(b"GRGB")
    DXT1 = i32(b"DXT1")
    DXT2 = i32(b"DXT2")
    DXT3 = i32(b"DXT3")
    DXT4 = i32(b"DXT4")
    DXT5 = i32(b"DXT5")
    DX10 = i32(b"DX10")
    BC4S = i32(b"BC4S")
    BC4U = i32(b"BC4U")
    BC5S = i32(b"BC5S")
    BC5U = i32(b"BC5U")
    ATI1 = i32(b"ATI1")
    ATI2 = i32(b"ATI2")
    MULTI2_ARGB8 = i32(b"MET1")


# Backward compatibility layer
module = sys.modules[__name__]
for item in DDSD:
    assert item.name is not None
    setattr(module, f"DDSD_{item.name}", item.value)
for item1 in DDSCAPS:
    assert item1.name is not None
    setattr(module, f"DDSCAPS_{item1.name}", item1.value)
for item2 in DDSCAPS2:
    assert item2.name is not None
    setattr(module, f"DDSCAPS2_{item2.name}", item2.value)
for item3 in DDPF:
    assert item3.name is not None
    setattr(module, f"DDPF_{item3.name}", item3.value)

DDS_FOURCC = DDPF.FOURCC
DDS_RGB = DDPF.RGB
DDS_RGBA = DDPF.RGB | DDPF.ALPHAPIXELS
DDS_LUMINANCE = DDPF.LUMINANCE
DDS_LUMINANCEA = DDPF.LUMINANCE | DDPF.ALPHAPIXELS
DDS_ALPHA = DDPF.ALPHA
DDS_PAL8 = DDPF.PALETTEINDEXED8

DDS_HEADER_FLAGS_TEXTURE = DDSD.CAPS | DDSD.HEIGHT | DDSD.WIDTH | DDSD.PIXELFORMAT
DDS_HEADER_FLAGS_MIPMAP = DDSD.MIPMAPCOUNT
DDS_HEADER_FLAGS_VOLUME = DDSD.DEPTH
DDS_HEADER_FLAGS_PITCH = DDSD.PITCH
DDS_HEADER_FLAGS_LINEARSIZE = DDSD.LINEARSIZE

DDS_HEIGHT = DDSD.HEIGHT
DDS_WIDTH = DDSD.WIDTH

DDS_SURFACE_FLAGS_TEXTURE = DDSCAPS.TEXTURE
DDS_SURFACE_FLAGS_MIPMAP = DDSCAPS.COMPLEX | DDSCAPS.MIPMAP
DDS_SURFACE_FLAGS_CUBEMAP = DDSCAPS.COMPLEX

DDS_CUBEMAP_POSITIVEX = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_POSITIVEX
DDS_CUBEMAP_NEGATIVEX = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_NEGATIVEX
DDS_CUBEMAP_POSITIVEY = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_POSITIVEY
DDS_CUBEMAP_NEGATIVEY = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_NEGATIVEY
DDS_CUBEMAP_POSITIVEZ = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_POSITIVEZ
DDS_CUBEMAP_NEGATIVEZ = DDSCAPS2.CUBEMAP | DDSCAPS2.CUBEMAP_NEGATIVEZ

DXT1_FOURCC = D3DFMT.DXT1
DXT3_FOURCC = D3DFMT.DXT3
DXT5_FOURCC = D3DFMT.DXT5

DXGI_FORMAT_R8G8B8A8_TYPELESS = DXGI_FORMAT.R8G8B8A8_TYPELESS
DXGI_FORMAT_R8G8B8A8_UNORM = DXGI_FORMAT.R8G8B8A8_UNORM
DXGI_FORMAT_R8G8B8A8_UNORM_SRGB = DXGI_FORMAT.R8G8B8A8_UNORM_SRGB
DXGI_FORMAT_BC5_TYPELESS = DXGI_FORMAT.BC5_TYPELESS
DXGI_FORMAT_BC5_UNORM = DXGI_FORMAT.BC5_UNORM
DXGI_FORMAT_BC5_SNORM = DXGI_FORMAT.BC5_SNORM
DXGI_FORMAT_BC6H_UF16 = DXGI_FORMAT.BC6H_UF16
DXGI_FORMAT_BC6H_SF16 = DXGI_FORMAT.BC6H_SF16
DXGI_FORMAT_BC7_TYPELESS = DXGI_FORMAT.BC7_TYPELESS
DXGI_FORMAT_BC7_UNORM = DXGI_FORMAT.BC7_UNORM
DXGI_FORMAT_BC7_UNORM_SRGB = DXGI_FORMAT.BC7_UNORM_SRGB


class DdsImageFile(ImageFile.ImageFile):
    format = "DDS"
    format_description = "DirectDraw Surface"

    def _open(self) -> None:
        if not _accept(self.fp.read(4)):
            msg = "not a DDS file"
            raise SyntaxError(msg)
        (header_size,) = struct.unpack("<I", self.fp.read(4))
        if header_size != 124:
            msg = f"Unsupported header size {repr(header_size)}"
            raise OSError(msg)
        header_bytes = self.fp.read(header_size - 4)
        if len(header_bytes) != 120:
            msg = f"Incomplete header: {len(header_bytes)} bytes"
            raise OSError(msg)
        header = io.BytesIO(header_bytes)

        flags, height, width = struct.unpack("<3I", header.read(12))
        self._size = (width, height)
        extents = (0, 0) + self.size

        pitch, depth, mipmaps = struct.unpack("<3I", header.read(12))
        struct.unpack("<11I", header.read(44))  # reserved

        # pixel format
        pfsize, pfflags, fourcc, bitcount = struct.unpack("<4I", header.read(16))
        n = 0
        rawmode = None
        if pfflags & DDPF.RGB:
            # Texture contains uncompressed RGB data
            if pfflags & DDPF.ALPHAPIXELS:
                self._mode = "RGBA"
                mask_count = 4
            else:
                self._mode = "RGB"
                mask_count = 3

            masks = struct.unpack(f"<{mask_count}I", header.read(mask_count * 4))
            self.tile = [ImageFile._Tile("dds_rgb", extents, 0, (bitcount, masks))]
            return
        elif pfflags & DDPF.LUMINANCE:
            if bitcount == 8:
                self._mode = "L"
            elif bitcount == 16 and pfflags & DDPF.ALPHAPIXELS:
                self._mode = "LA"
            else:
                msg = f"Unsupported bitcount {bitcount} for {pfflags}"
                raise OSError(msg)
        elif pfflags & DDPF.PALETTEINDEXED8:
            self._mode = "P"
            self.palette = ImagePalette.raw("RGBA", self.fp.read(1024))
            self.palette.mode = "RGBA"
        elif pfflags & DDPF.FOURCC:
            offset = header_size + 4
            if fourcc == D3DFMT.DXT1:
                self._mode = "RGBA"
                self.pixel_format = "DXT1"
                n = 1
            elif fourcc == D3DFMT.DXT3:
                self._mode = "RGBA"
                self.pixel_format = "DXT3"
                n = 2
            elif fourcc == D3DFMT.DXT5:
                self._mode = "RGBA"
                self.pixel_format = "DXT5"
                n = 3
            elif fourcc in (D3DFMT.BC4U, D3DFMT.ATI1):
                self._mode = "L"
                self.pixel_format = "BC4"
                n = 4
            elif fourcc == D3DFMT.BC5S:
                self._mode = "RGB"
                self.pixel_format = "BC5S"
                n = 5
            elif fourcc in (D3DFMT.BC5U, D3DFMT.ATI2):
                self._mode = "RGB"
                self.pixel_format = "BC5"
                n = 5
            elif fourcc == D3DFMT.DX10:
                offset += 20
                # ignoring flags which pertain to volume textures and cubemaps
                (dxgi_format,) = struct.unpack("<I", self.fp.read(4))
                self.fp.read(16)
                if dxgi_format in (
                    DXGI_FORMAT.BC1_UNORM,
                    DXGI_FORMAT.BC1_TYPELESS,
                ):
                    self._mode = "RGBA"
                    self.pixel_format = "BC1"
                    n = 1
                elif dxgi_format in (DXGI_FORMAT.BC2_TYPELESS, DXGI_FORMAT.BC2_UNORM):
                    self._mode = "RGBA"
                    self.pixel_format = "BC2"
                    n = 2
                elif dxgi_format in (DXGI_FORMAT.BC3_TYPELESS, DXGI_FORMAT.BC3_UNORM):
                    self._mode = "RGBA"
                    self.pixel_format = "BC3"
                    n = 3
                elif dxgi_format in (DXGI_FORMAT.BC4_TYPELESS, DXGI_FORMAT.BC4_UNORM):
                    self._mode = "L"
                    self.pixel_format = "BC4"
                    n = 4
                elif dxgi_format in (DXGI_FORMAT.BC5_TYPELESS, DXGI_FORMAT.BC5_UNORM):
                    self._mode = "RGB"
                    self.pixel_format = "BC5"
                    n = 5
                elif dxgi_format == DXGI_FORMAT.BC5_SNORM:
                    self._mode = "RGB"
                    self.pixel_format = "BC5S"
                    n = 5
                elif dxgi_format == DXGI_FORMAT.BC6H_UF16:
                    self._mode = "RGB"
                    self.pixel_format = "BC6H"
                    n = 6
                elif dxgi_format == DXGI_FORMAT.BC6H_SF16:
                    self._mode = "RGB"
                    self.pixel_format = "BC6HS"
                    n = 6
                elif dxgi_format in (
                    DXGI_FORMAT.BC7_TYPELESS,
                    DXGI_FORMAT.BC7_UNORM,
                    DXGI_FORMAT.BC7_UNORM_SRGB,
                ):
                    self._mode = "RGBA"
                    self.pixel_format = "BC7"
                    n = 7
                    if dxgi_format == DXGI_FORMAT.BC7_UNORM_SRGB:
                        self.info["gamma"] = 1 / 2.2
                elif dxgi_format in (
                    DXGI_FORMAT.R8G8B8A8_TYPELESS,
                    DXGI_FORMAT.R8G8B8A8_UNORM,
                    DXGI_FORMAT.R8G8B8A8_UNORM_SRGB,
                ):
                    self._mode = "RGBA"
                    if dxgi_format == DXGI_FORMAT.R8G8B8A8_UNORM_SRGB:
                        self.info["gamma"] = 1 / 2.2
                else:
                    msg = f"Unimplemented DXGI format {dxgi_format}"
                    raise NotImplementedError(msg)
            else:
                msg = f"Unimplemented pixel format {repr(fourcc)}"
                raise NotImplementedError(msg)
        else:
            msg = f"Unknown pixel format flags {pfflags}"
            raise NotImplementedError(msg)

        if n:
            self.tile = [
                ImageFile._Tile("bcn", extents, offset, (n, self.pixel_format))
            ]
        else:
            self.tile = [ImageFile._Tile("raw", extents, 0, rawmode or self.mode)]

    def load_seek(self, pos: int) -> None:
        pass


class DdsRgbDecoder(ImageFile.PyDecoder):
    _pulls_fd = True

    def decode(self, buffer: bytes | Image.SupportsArrayInterface) -> tuple[int, int]:
        assert self.fd is not None
        bitcount, masks = self.args

        # Some masks will be padded with zeros, e.g. R 0b11 G 0b1100
        # Calculate how many zeros each mask is padded with
        mask_offsets = []
        # And the maximum value of each channel without the padding
        mask_totals = []
        for mask in masks:
            offset = 0
            if mask != 0:
                while mask >> (offset + 1) << (offset + 1) == mask:
                    offset += 1
            mask_offsets.append(offset)
            mask_totals.append(mask >> offset)

        data = bytearray()
        bytecount = bitcount // 8
        dest_length = self.state.xsize * self.state.ysize * len(masks)
        while len(data) < dest_length:
            value = int.from_bytes(self.fd.read(bytecount), "little")
            for i, mask in enumerate(masks):
                masked_value = value & mask
                # Remove the zero padding, and scale it to 8 bits
                data += o8(
                    int(((masked_value >> mask_offsets[i]) / mask_totals[i]) * 255)
                )
        self.set_as_raw(data)
        return -1, 0


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode not in ("RGB", "RGBA", "L", "LA"):
        msg = f"cannot write mode {im.mode} as DDS"
        raise OSError(msg)

    flags = DDSD.CAPS | DDSD.HEIGHT | DDSD.WIDTH | DDSD.PIXELFORMAT
    bitcount = len(im.getbands()) * 8
    pixel_format = im.encoderinfo.get("pixel_format")
    args: tuple[int] | str
    if pixel_format:
        codec_name = "bcn"
        flags |= DDSD.LINEARSIZE
        pitch = (im.width + 3) * 4
        rgba_mask = [0, 0, 0, 0]
        pixel_flags = DDPF.FOURCC
        if pixel_format == "DXT1":
            fourcc = D3DFMT.DXT1
            args = (1,)
        elif pixel_format == "DXT3":
            fourcc = D3DFMT.DXT3
            args = (2,)
        elif pixel_format == "DXT5":
            fourcc = D3DFMT.DXT5
            args = (3,)
        else:
            fourcc = D3DFMT.DX10
            if pixel_format == "BC2":
                args = (2,)
                dxgi_format = DXGI_FORMAT.BC2_TYPELESS
            elif pixel_format == "BC3":
                args = (3,)
                dxgi_format = DXGI_FORMAT.BC3_TYPELESS
            elif pixel_format == "BC5":
                args = (5,)
                dxgi_format = DXGI_FORMAT.BC5_TYPELESS
                if im.mode != "RGB":
                    msg = "only RGB mode can be written as BC5"
                    raise OSError(msg)
            else:
                msg = f"cannot write pixel format {pixel_format}"
                raise OSError(msg)
    else:
        codec_name = "raw"
        flags |= DDSD.PITCH
        pitch = (im.width * bitcount + 7) // 8

        alpha = im.mode[-1] == "A"
        if im.mode[0] == "L":
            pixel_flags = DDPF.LUMINANCE
            args = im.mode
            if alpha:
                rgba_mask = [0x000000FF, 0x000000FF, 0x000000FF]
            else:
                rgba_mask = [0xFF000000, 0xFF000000, 0xFF000000]
        else:
            pixel_flags = DDPF.RGB
            args = im.mode[::-1]
            rgba_mask = [0x00FF0000, 0x0000FF00, 0x000000FF]

            if alpha:
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (a, r, g, b))
        if alpha:
            pixel_flags |= DDPF.ALPHAPIXELS
        rgba_mask.append(0xFF000000 if alpha else 0)

        fourcc = D3DFMT.UNKNOWN
    fp.write(
        o32(DDS_MAGIC)
        + struct.pack(
            "<7I",
            124,  # header size
            flags,  # flags
            im.height,
            im.width,
            pitch,
            0,  # depth
            0,  # mipmaps
        )
        + struct.pack("11I", *((0,) * 11))  # reserved
        # pfsize, pfflags, fourcc, bitcount
        + struct.pack("<4I", 32, pixel_flags, fourcc, bitcount)
        + struct.pack("<4I", *rgba_mask)  # dwRGBABitMask
        + struct.pack("<5I", DDSCAPS.TEXTURE, 0, 0, 0, 0)
    )
    if fourcc == D3DFMT.DX10:
        fp.write(
            # dxgi_format, 2D resource, misc, array size, straight alpha
            struct.pack("<5I", dxgi_format, 3, 0, 0, 1)
        )
    ImageFile._save(im, fp, [ImageFile._Tile(codec_name, (0, 0) + im.size, 0, args)])


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(b"DDS ")


Image.register_open(DdsImageFile.format, DdsImageFile, _accept)
Image.register_decoder("dds_rgb", DdsRgbDecoder)
Image.register_save(DdsImageFile.format, _save)
Image.register_extension(DdsImageFile.format, ".dds")

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\jaraco\text\__init__.py ===
import re
import itertools
import textwrap
import functools

try:
    from importlib.resources import files  # type: ignore
except ImportError:  # pragma: nocover
    from importlib_resources import files  # type: ignore

from jaraco.functools import compose, method_cache
from jaraco.context import ExceptionTrap


def substitution(old, new):
    """
    Return a function that will perform a substitution on a string
    """
    return lambda s: s.replace(old, new)


def multi_substitution(*substitutions):
    """
    Take a sequence of pairs specifying substitutions, and create
    a function that performs those substitutions.

    >>> multi_substitution(('foo', 'bar'), ('bar', 'baz'))('foo')
    'baz'
    """
    substitutions = itertools.starmap(substitution, substitutions)
    # compose function applies last function first, so reverse the
    #  substitutions to get the expected order.
    substitutions = reversed(tuple(substitutions))
    return compose(*substitutions)


class FoldedCase(str):
    """
    A case insensitive string class; behaves just like str
    except compares equal when the only variation is case.

    >>> s = FoldedCase('hello world')

    >>> s == 'Hello World'
    True

    >>> 'Hello World' == s
    True

    >>> s != 'Hello World'
    False

    >>> s.index('O')
    4

    >>> s.split('O')
    ['hell', ' w', 'rld']

    >>> sorted(map(FoldedCase, ['GAMMA', 'alpha', 'Beta']))
    ['alpha', 'Beta', 'GAMMA']

    Sequence membership is straightforward.

    >>> "Hello World" in [s]
    True
    >>> s in ["Hello World"]
    True

    Allows testing for set inclusion, but candidate and elements
    must both be folded.

    >>> FoldedCase("Hello World") in {s}
    True
    >>> s in {FoldedCase("Hello World")}
    True

    String inclusion works as long as the FoldedCase object
    is on the right.

    >>> "hello" in FoldedCase("Hello World")
    True

    But not if the FoldedCase object is on the left:

    >>> FoldedCase('hello') in 'Hello World'
    False

    In that case, use ``in_``:

    >>> FoldedCase('hello').in_('Hello World')
    True

    >>> FoldedCase('hello') > FoldedCase('Hello')
    False

    >>> FoldedCase('ß') == FoldedCase('ss')
    True
    """

    def __lt__(self, other):
        return self.casefold() < other.casefold()

    def __gt__(self, other):
        return self.casefold() > other.casefold()

    def __eq__(self, other):
        return self.casefold() == other.casefold()

    def __ne__(self, other):
        return self.casefold() != other.casefold()

    def __hash__(self):
        return hash(self.casefold())

    def __contains__(self, other):
        return super().casefold().__contains__(other.casefold())

    def in_(self, other):
        "Does self appear in other?"
        return self in FoldedCase(other)

    # cache casefold since it's likely to be called frequently.
    @method_cache
    def casefold(self):
        return super().casefold()

    def index(self, sub):
        return self.casefold().index(sub.casefold())

    def split(self, splitter=' ', maxsplit=0):
        pattern = re.compile(re.escape(splitter), re.I)
        return pattern.split(self, maxsplit)


# Python 3.8 compatibility
_unicode_trap = ExceptionTrap(UnicodeDecodeError)


@_unicode_trap.passes
def is_decodable(value):
    r"""
    Return True if the supplied value is decodable (using the default
    encoding).

    >>> is_decodable(b'\xff')
    False
    >>> is_decodable(b'\x32')
    True
    """
    value.decode()


def is_binary(value):
    r"""
    Return True if the value appears to be binary (that is, it's a byte
    string and isn't decodable).

    >>> is_binary(b'\xff')
    True
    >>> is_binary('\xff')
    False
    """
    return isinstance(value, bytes) and not is_decodable(value)


def trim(s):
    r"""
    Trim something like a docstring to remove the whitespace that
    is common due to indentation and formatting.

    >>> trim("\n\tfoo = bar\n\t\tbar = baz\n")
    'foo = bar\n\tbar = baz'
    """
    return textwrap.dedent(s).strip()


def wrap(s):
    """
    Wrap lines of text, retaining existing newlines as
    paragraph markers.

    >>> print(wrap(lorem_ipsum))
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad
    minim veniam, quis nostrud exercitation ullamco laboris nisi ut
    aliquip ex ea commodo consequat. Duis aute irure dolor in
    reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla
    pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
    culpa qui officia deserunt mollit anim id est laborum.
    <BLANKLINE>
    Curabitur pretium tincidunt lacus. Nulla gravida orci a odio. Nullam
    varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus
    magna felis sollicitudin mauris. Integer in mauris eu nibh euismod
    gravida. Duis ac tellus et risus vulputate vehicula. Donec lobortis
    risus a elit. Etiam tempor. Ut ullamcorper, ligula eu tempor congue,
    eros est euismod turpis, id tincidunt sapien risus a quam. Maecenas
    fermentum consequat mi. Donec fermentum. Pellentesque malesuada nulla
    a mi. Duis sapien sem, aliquet nec, commodo eget, consequat quis,
    neque. Aliquam faucibus, elit ut dictum aliquet, felis nisl adipiscing
    sapien, sed malesuada diam lacus eget erat. Cras mollis scelerisque
    nunc. Nullam arcu. Aliquam consequat. Curabitur augue lorem, dapibus
    quis, laoreet et, pretium ac, nisi. Aenean magna nisl, mollis quis,
    molestie eu, feugiat in, orci. In hac habitasse platea dictumst.
    """
    paragraphs = s.splitlines()
    wrapped = ('\n'.join(textwrap.wrap(para)) for para in paragraphs)
    return '\n\n'.join(wrapped)


def unwrap(s):
    r"""
    Given a multi-line string, return an unwrapped version.

    >>> wrapped = wrap(lorem_ipsum)
    >>> wrapped.count('\n')
    20
    >>> unwrapped = unwrap(wrapped)
    >>> unwrapped.count('\n')
    1
    >>> print(unwrapped)
    Lorem ipsum dolor sit amet, consectetur adipiscing ...
    Curabitur pretium tincidunt lacus. Nulla gravida orci ...

    """
    paragraphs = re.split(r'\n\n+', s)
    cleaned = (para.replace('\n', ' ') for para in paragraphs)
    return '\n'.join(cleaned)


lorem_ipsum: str = (
    files(__name__).joinpath('Lorem ipsum.txt').read_text(encoding='utf-8')
)


class Splitter:
    """object that will split a string with the given arguments for each call

    >>> s = Splitter(',')
    >>> s('hello, world, this is your, master calling')
    ['hello', ' world', ' this is your', ' master calling']
    """

    def __init__(self, *args):
        self.args = args

    def __call__(self, s):
        return s.split(*self.args)


def indent(string, prefix=' ' * 4):
    """
    >>> indent('foo')
    '    foo'
    """
    return prefix + string


class WordSet(tuple):
    """
    Given an identifier, return the words that identifier represents,
    whether in camel case, underscore-separated, etc.

    >>> WordSet.parse("camelCase")
    ('camel', 'Case')

    >>> WordSet.parse("under_sep")
    ('under', 'sep')

    Acronyms should be retained

    >>> WordSet.parse("firstSNL")
    ('first', 'SNL')

    >>> WordSet.parse("you_and_I")
    ('you', 'and', 'I')

    >>> WordSet.parse("A simple test")
    ('A', 'simple', 'test')

    Multiple caps should not interfere with the first cap of another word.

    >>> WordSet.parse("myABCClass")
    ('my', 'ABC', 'Class')

    The result is a WordSet, providing access to other forms.

    >>> WordSet.parse("myABCClass").underscore_separated()
    'my_ABC_Class'

    >>> WordSet.parse('a-command').camel_case()
    'ACommand'

    >>> WordSet.parse('someIdentifier').lowered().space_separated()
    'some identifier'

    Slices of the result should return another WordSet.

    >>> WordSet.parse('taken-out-of-context')[1:].underscore_separated()
    'out_of_context'

    >>> WordSet.from_class_name(WordSet()).lowered().space_separated()
    'word set'

    >>> example = WordSet.parse('figured it out')
    >>> example.headless_camel_case()
    'figuredItOut'
    >>> example.dash_separated()
    'figured-it-out'

    """

    _pattern = re.compile('([A-Z]?[a-z]+)|([A-Z]+(?![a-z]))')

    def capitalized(self):
        return WordSet(word.capitalize() for word in self)

    def lowered(self):
        return WordSet(word.lower() for word in self)

    def camel_case(self):
        return ''.join(self.capitalized())

    def headless_camel_case(self):
        words = iter(self)
        first = next(words).lower()
        new_words = itertools.chain((first,), WordSet(words).camel_case())
        return ''.join(new_words)

    def underscore_separated(self):
        return '_'.join(self)

    def dash_separated(self):
        return '-'.join(self)

    def space_separated(self):
        return ' '.join(self)

    def trim_right(self, item):
        """
        Remove the item from the end of the set.

        >>> WordSet.parse('foo bar').trim_right('foo')
        ('foo', 'bar')
        >>> WordSet.parse('foo bar').trim_right('bar')
        ('foo',)
        >>> WordSet.parse('').trim_right('bar')
        ()
        """
        return self[:-1] if self and self[-1] == item else self

    def trim_left(self, item):
        """
        Remove the item from the beginning of the set.

        >>> WordSet.parse('foo bar').trim_left('foo')
        ('bar',)
        >>> WordSet.parse('foo bar').trim_left('bar')
        ('foo', 'bar')
        >>> WordSet.parse('').trim_left('bar')
        ()
        """
        return self[1:] if self and self[0] == item else self

    def trim(self, item):
        """
        >>> WordSet.parse('foo bar').trim('foo')
        ('bar',)
        """
        return self.trim_left(item).trim_right(item)

    def __getitem__(self, item):
        result = super().__getitem__(item)
        if isinstance(item, slice):
            result = WordSet(result)
        return result

    @classmethod
    def parse(cls, identifier):
        matches = cls._pattern.finditer(identifier)
        return WordSet(match.group(0) for match in matches)

    @classmethod
    def from_class_name(cls, subject):
        return cls.parse(subject.__class__.__name__)


# for backward compatibility
words = WordSet.parse


def simple_html_strip(s):
    r"""
    Remove HTML from the string `s`.

    >>> str(simple_html_strip(''))
    ''

    >>> print(simple_html_strip('A <bold>stormy</bold> day in paradise'))
    A stormy day in paradise

    >>> print(simple_html_strip('Somebody <!-- do not --> tell the truth.'))
    Somebody  tell the truth.

    >>> print(simple_html_strip('What about<br/>\nmultiple lines?'))
    What about
    multiple lines?
    """
    html_stripper = re.compile('(<!--.*?-->)|(<[^>]*>)|([^<]+)', re.DOTALL)
    texts = (match.group(3) or '' for match in html_stripper.finditer(s))
    return ''.join(texts)


class SeparatedValues(str):
    """
    A string separated by a separator. Overrides __iter__ for getting
    the values.

    >>> list(SeparatedValues('a,b,c'))
    ['a', 'b', 'c']

    Whitespace is stripped and empty values are discarded.

    >>> list(SeparatedValues(' a,   b   , c,  '))
    ['a', 'b', 'c']
    """

    separator = ','

    def __iter__(self):
        parts = self.split(self.separator)
        return filter(None, (part.strip() for part in parts))


class Stripper:
    r"""
    Given a series of lines, find the common prefix and strip it from them.

    >>> lines = [
    ...     'abcdefg\n',
    ...     'abc\n',
    ...     'abcde\n',
    ... ]
    >>> res = Stripper.strip_prefix(lines)
    >>> res.prefix
    'abc'
    >>> list(res.lines)
    ['defg\n', '\n', 'de\n']

    If no prefix is common, nothing should be stripped.

    >>> lines = [
    ...     'abcd\n',
    ...     '1234\n',
    ... ]
    >>> res = Stripper.strip_prefix(lines)
    >>> res.prefix = ''
    >>> list(res.lines)
    ['abcd\n', '1234\n']
    """

    def __init__(self, prefix, lines):
        self.prefix = prefix
        self.lines = map(self, lines)

    @classmethod
    def strip_prefix(cls, lines):
        prefix_lines, lines = itertools.tee(lines)
        prefix = functools.reduce(cls.common_prefix, prefix_lines)
        return cls(prefix, lines)

    def __call__(self, line):
        if not self.prefix:
            return line
        null, prefix, rest = line.partition(self.prefix)
        return rest

    @staticmethod
    def common_prefix(s1, s2):
        """
        Return the common prefix of two lines.
        """
        index = min(len(s1), len(s2))
        while s1[:index] != s2[:index]:
            index -= 1
        return s1[:index]


def remove_prefix(text, prefix):
    """
    Remove the prefix from the text if it exists.

    >>> remove_prefix('underwhelming performance', 'underwhelming ')
    'performance'

    >>> remove_prefix('something special', 'sample')
    'something special'
    """
    null, prefix, rest = text.rpartition(prefix)
    return rest


def remove_suffix(text, suffix):
    """
    Remove the suffix from the text if it exists.

    >>> remove_suffix('name.git', '.git')
    'name'

    >>> remove_suffix('something special', 'sample')
    'something special'
    """
    rest, suffix, null = text.partition(suffix)
    return rest


def normalize_newlines(text):
    r"""
    Replace alternate newlines with the canonical newline.

    >>> normalize_newlines('Lorem Ipsum\u2029')
    'Lorem Ipsum\n'
    >>> normalize_newlines('Lorem Ipsum\r\n')
    'Lorem Ipsum\n'
    >>> normalize_newlines('Lorem Ipsum\x85')
    'Lorem Ipsum\n'
    """
    newlines = ['\r\n', '\r', '\n', '\u0085', '\u2028', '\u2029']
    pattern = '|'.join(newlines)
    return re.sub(pattern, '\n', text)


def _nonblank(str):
    return str and not str.startswith('#')


@functools.singledispatch
def yield_lines(iterable):
    r"""
    Yield valid lines of a string or iterable.

    >>> list(yield_lines(''))
    []
    >>> list(yield_lines(['foo', 'bar']))
    ['foo', 'bar']
    >>> list(yield_lines('foo\nbar'))
    ['foo', 'bar']
    >>> list(yield_lines('\nfoo\n#bar\nbaz #comment'))
    ['foo', 'baz #comment']
    >>> list(yield_lines(['foo\nbar', 'baz', 'bing\n\n\n']))
    ['foo', 'bar', 'baz', 'bing']
    """
    return itertools.chain.from_iterable(map(yield_lines, iterable))


@yield_lines.register(str)
def _(text):
    return filter(_nonblank, map(str.strip, text.splitlines()))


def drop_comment(line):
    """
    Drop comments.

    >>> drop_comment('foo # bar')
    'foo'

    A hash without a space may be in a URL.

    >>> drop_comment('http://example.com/foo#bar')
    'http://example.com/foo#bar'
    """
    return line.partition(' #')[0]


def join_continuation(lines):
    r"""
    Join lines continued by a trailing backslash.

    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar', 'baz']))
    ['foobar', 'baz']
    >>> list(join_continuation(['foo \\', 'bar \\', 'baz']))
    ['foobarbaz']

    Not sure why, but...
    The character preceding the backslash is also elided.

    >>> list(join_continuation(['goo\\', 'dly']))
    ['godly']

    A terrible idea, but...
    If no line is available to continue, suppress the lines.

    >>> list(join_continuation(['foo', 'bar\\', 'baz\\']))
    ['foo']
    """
    lines = iter(lines)
    for item in lines:
        while item.endswith('\\'):
            try:
                item = item[:-2].strip() + next(lines)
            except StopIteration:
                return
        yield item


def read_newlines(filename, limit=1024):
    r"""
    >>> tmp_path = getfixture('tmp_path')
    >>> filename = tmp_path / 'out.txt'
    >>> _ = filename.write_text('foo\n', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    '\n'
    >>> _ = filename.write_text('foo\r\n', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    '\r\n'
    >>> _ = filename.write_text('foo\r\nbar\nbing\r', newline='', encoding='utf-8')
    >>> read_newlines(filename)
    ('\r', '\n', '\r\n')
    """
    with open(filename, encoding='utf-8') as fp:
        fp.read(limit)
    return fp.newlines

# === NexusCore/myenv\Lib\site-packages\pip\_internal\req\req_file.py ===
"""
Requirements file parsing
"""

import codecs
import locale
import logging
import optparse
import os
import re
import shlex
import sys
import urllib.parse
from dataclasses import dataclass
from optparse import Values
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    NoReturn,
    Optional,
    Tuple,
)

from pip._internal.cli import cmdoptions
from pip._internal.exceptions import InstallationError, RequirementsFileParseError
from pip._internal.models.search_scope import SearchScope

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.network.session import PipSession

__all__ = ["parse_requirements"]

ReqFileLines = Iterable[Tuple[int, str]]

LineParser = Callable[[str], Tuple[str, Values]]

SCHEME_RE = re.compile(r"^(http|https|file):", re.I)
COMMENT_RE = re.compile(r"(^|\s+)#.*$")

# Matches environment variable-style values in '${MY_VARIABLE_1}' with the
# variable name consisting of only uppercase letters, digits or the '_'
# (underscore). This follows the POSIX standard defined in IEEE Std 1003.1,
# 2013 Edition.
ENV_VAR_RE = re.compile(r"(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})")

SUPPORTED_OPTIONS: List[Callable[..., optparse.Option]] = [
    cmdoptions.index_url,
    cmdoptions.extra_index_url,
    cmdoptions.no_index,
    cmdoptions.constraints,
    cmdoptions.requirements,
    cmdoptions.editable,
    cmdoptions.find_links,
    cmdoptions.no_binary,
    cmdoptions.only_binary,
    cmdoptions.prefer_binary,
    cmdoptions.require_hashes,
    cmdoptions.pre,
    cmdoptions.trusted_host,
    cmdoptions.use_new_feature,
]

# options to be passed to requirements
SUPPORTED_OPTIONS_REQ: List[Callable[..., optparse.Option]] = [
    cmdoptions.global_options,
    cmdoptions.hash,
    cmdoptions.config_settings,
]

SUPPORTED_OPTIONS_EDITABLE_REQ: List[Callable[..., optparse.Option]] = [
    cmdoptions.config_settings,
]


# the 'dest' string values
SUPPORTED_OPTIONS_REQ_DEST = [str(o().dest) for o in SUPPORTED_OPTIONS_REQ]
SUPPORTED_OPTIONS_EDITABLE_REQ_DEST = [
    str(o().dest) for o in SUPPORTED_OPTIONS_EDITABLE_REQ
]

# order of BOMS is important: codecs.BOM_UTF16_LE is a prefix of codecs.BOM_UTF32_LE
# so data.startswith(BOM_UTF16_LE) would be true for UTF32_LE data
BOMS: List[Tuple[bytes, str]] = [
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF16, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
]

PEP263_ENCODING_RE = re.compile(rb"coding[:=]\s*([-\w.]+)")
DEFAULT_ENCODING = "utf-8"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedRequirement:
    # TODO: replace this with slots=True when dropping Python 3.9 support.
    __slots__ = (
        "requirement",
        "is_editable",
        "comes_from",
        "constraint",
        "options",
        "line_source",
    )

    requirement: str
    is_editable: bool
    comes_from: str
    constraint: bool
    options: Optional[Dict[str, Any]]
    line_source: Optional[str]


@dataclass(frozen=True)
class ParsedLine:
    __slots__ = ("filename", "lineno", "args", "opts", "constraint")

    filename: str
    lineno: int
    args: str
    opts: Values
    constraint: bool

    @property
    def is_editable(self) -> bool:
        return bool(self.opts.editables)

    @property
    def requirement(self) -> Optional[str]:
        if self.args:
            return self.args
        elif self.is_editable:
            # We don't support multiple -e on one line
            return self.opts.editables[0]
        return None


def parse_requirements(
    filename: str,
    session: "PipSession",
    finder: Optional["PackageFinder"] = None,
    options: Optional[optparse.Values] = None,
    constraint: bool = False,
) -> Generator[ParsedRequirement, None, None]:
    """Parse a requirements file and yield ParsedRequirement instances.

    :param filename:    Path or url of requirements file.
    :param session:     PipSession instance.
    :param finder:      Instance of pip.index.PackageFinder.
    :param options:     cli options.
    :param constraint:  If true, parsing a constraint file rather than
        requirements file.
    """
    line_parser = get_line_parser(finder)
    parser = RequirementsFileParser(session, line_parser)

    for parsed_line in parser.parse(filename, constraint):
        parsed_req = handle_line(
            parsed_line, options=options, finder=finder, session=session
        )
        if parsed_req is not None:
            yield parsed_req


def preprocess(content: str) -> ReqFileLines:
    """Split, filter, and join lines, and return a line iterator

    :param content: the content of the requirements file
    """
    lines_enum: ReqFileLines = enumerate(content.splitlines(), start=1)
    lines_enum = join_lines(lines_enum)
    lines_enum = ignore_comments(lines_enum)
    lines_enum = expand_env_variables(lines_enum)
    return lines_enum


def handle_requirement_line(
    line: ParsedLine,
    options: Optional[optparse.Values] = None,
) -> ParsedRequirement:
    # preserve for the nested code path
    line_comes_from = "{} {} (line {})".format(
        "-c" if line.constraint else "-r",
        line.filename,
        line.lineno,
    )

    assert line.requirement is not None

    # get the options that apply to requirements
    if line.is_editable:
        supported_dest = SUPPORTED_OPTIONS_EDITABLE_REQ_DEST
    else:
        supported_dest = SUPPORTED_OPTIONS_REQ_DEST
    req_options = {}
    for dest in supported_dest:
        if dest in line.opts.__dict__ and line.opts.__dict__[dest]:
            req_options[dest] = line.opts.__dict__[dest]

    line_source = f"line {line.lineno} of {line.filename}"
    return ParsedRequirement(
        requirement=line.requirement,
        is_editable=line.is_editable,
        comes_from=line_comes_from,
        constraint=line.constraint,
        options=req_options,
        line_source=line_source,
    )


def handle_option_line(
    opts: Values,
    filename: str,
    lineno: int,
    finder: Optional["PackageFinder"] = None,
    options: Optional[optparse.Values] = None,
    session: Optional["PipSession"] = None,
) -> None:
    if opts.hashes:
        logger.warning(
            "%s line %s has --hash but no requirement, and will be ignored.",
            filename,
            lineno,
        )

    if options:
        # percolate options upward
        if opts.require_hashes:
            options.require_hashes = opts.require_hashes
        if opts.features_enabled:
            options.features_enabled.extend(
                f for f in opts.features_enabled if f not in options.features_enabled
            )

    # set finder options
    if finder:
        find_links = finder.find_links
        index_urls = finder.index_urls
        no_index = finder.search_scope.no_index
        if opts.no_index is True:
            no_index = True
            index_urls = []
        if opts.index_url and not no_index:
            index_urls = [opts.index_url]
        if opts.extra_index_urls and not no_index:
            index_urls.extend(opts.extra_index_urls)
        if opts.find_links:
            # FIXME: it would be nice to keep track of the source
            # of the find_links: support a find-links local path
            # relative to a requirements file.
            value = opts.find_links[0]
            req_dir = os.path.dirname(os.path.abspath(filename))
            relative_to_reqs_file = os.path.join(req_dir, value)
            if os.path.exists(relative_to_reqs_file):
                value = relative_to_reqs_file
            find_links.append(value)

        if session:
            # We need to update the auth urls in session
            session.update_index_urls(index_urls)

        search_scope = SearchScope(
            find_links=find_links,
            index_urls=index_urls,
            no_index=no_index,
        )
        finder.search_scope = search_scope

        if opts.pre:
            finder.set_allow_all_prereleases()

        if opts.prefer_binary:
            finder.set_prefer_binary()

        if session:
            for host in opts.trusted_hosts or []:
                source = f"line {lineno} of {filename}"
                session.add_trusted_host(host, source=source)


def handle_line(
    line: ParsedLine,
    options: Optional[optparse.Values] = None,
    finder: Optional["PackageFinder"] = None,
    session: Optional["PipSession"] = None,
) -> Optional[ParsedRequirement]:
    """Handle a single parsed requirements line; This can result in
    creating/yielding requirements, or updating the finder.

    :param line:        The parsed line to be processed.
    :param options:     CLI options.
    :param finder:      The finder - updated by non-requirement lines.
    :param session:     The session - updated by non-requirement lines.

    Returns a ParsedRequirement object if the line is a requirement line,
    otherwise returns None.

    For lines that contain requirements, the only options that have an effect
    are from SUPPORTED_OPTIONS_REQ, and they are scoped to the
    requirement. Other options from SUPPORTED_OPTIONS may be present, but are
    ignored.

    For lines that do not contain requirements, the only options that have an
    effect are from SUPPORTED_OPTIONS. Options from SUPPORTED_OPTIONS_REQ may
    be present, but are ignored. These lines may contain multiple options
    (although our docs imply only one is supported), and all our parsed and
    affect the finder.
    """

    if line.requirement is not None:
        parsed_req = handle_requirement_line(line, options)
        return parsed_req
    else:
        handle_option_line(
            line.opts,
            line.filename,
            line.lineno,
            finder,
            options,
            session,
        )
        return None


class RequirementsFileParser:
    def __init__(
        self,
        session: "PipSession",
        line_parser: LineParser,
    ) -> None:
        self._session = session
        self._line_parser = line_parser

    def parse(
        self, filename: str, constraint: bool
    ) -> Generator[ParsedLine, None, None]:
        """Parse a given file, yielding parsed lines."""
        yield from self._parse_and_recurse(
            filename, constraint, [{os.path.abspath(filename): None}]
        )

    def _parse_and_recurse(
        self,
        filename: str,
        constraint: bool,
        parsed_files_stack: List[Dict[str, Optional[str]]],
    ) -> Generator[ParsedLine, None, None]:
        for line in self._parse_file(filename, constraint):
            if line.requirement is None and (
                line.opts.requirements or line.opts.constraints
            ):
                # parse a nested requirements file
                if line.opts.requirements:
                    req_path = line.opts.requirements[0]
                    nested_constraint = False
                else:
                    req_path = line.opts.constraints[0]
                    nested_constraint = True

                # original file is over http
                if SCHEME_RE.search(filename):
                    # do a url join so relative paths work
                    req_path = urllib.parse.urljoin(filename, req_path)
                # original file and nested file are paths
                elif not SCHEME_RE.search(req_path):
                    # do a join so relative paths work
                    # and then abspath so that we can identify recursive references
                    req_path = os.path.abspath(
                        os.path.join(
                            os.path.dirname(filename),
                            req_path,
                        )
                    )
                parsed_files = parsed_files_stack[0]
                if req_path in parsed_files:
                    initial_file = parsed_files[req_path]
                    tail = (
                        f" and again in {initial_file}"
                        if initial_file is not None
                        else ""
                    )
                    raise RequirementsFileParseError(
                        f"{req_path} recursively references itself in {filename}{tail}"
                    )
                # Keeping a track where was each file first included in
                new_parsed_files = parsed_files.copy()
                new_parsed_files[req_path] = filename
                yield from self._parse_and_recurse(
                    req_path, nested_constraint, [new_parsed_files, *parsed_files_stack]
                )
            else:
                yield line

    def _parse_file(
        self, filename: str, constraint: bool
    ) -> Generator[ParsedLine, None, None]:
        _, content = get_file_content(filename, self._session)

        lines_enum = preprocess(content)

        for line_number, line in lines_enum:
            try:
                args_str, opts = self._line_parser(line)
            except OptionParsingError as e:
                # add offending line
                msg = f"Invalid requirement: {line}\n{e.msg}"
                raise RequirementsFileParseError(msg)

            yield ParsedLine(
                filename,
                line_number,
                args_str,
                opts,
                constraint,
            )


def get_line_parser(finder: Optional["PackageFinder"]) -> LineParser:
    def parse_line(line: str) -> Tuple[str, Values]:
        # Build new parser for each line since it accumulates appendable
        # options.
        parser = build_parser()
        defaults = parser.get_default_values()
        defaults.index_url = None
        if finder:
            defaults.format_control = finder.format_control

        args_str, options_str = break_args_options(line)

        try:
            options = shlex.split(options_str)
        except ValueError as e:
            raise OptionParsingError(f"Could not split options: {options_str}") from e

        opts, _ = parser.parse_args(options, defaults)

        return args_str, opts

    return parse_line


def break_args_options(line: str) -> Tuple[str, str]:
    """Break up the line into an args and options string.  We only want to shlex
    (and then optparse) the options, not the args.  args can contain markers
    which are corrupted by shlex.
    """
    tokens = line.split(" ")
    args = []
    options = tokens[:]
    for token in tokens:
        if token.startswith("-") or token.startswith("--"):
            break
        else:
            args.append(token)
            options.pop(0)
    return " ".join(args), " ".join(options)


class OptionParsingError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg


def build_parser() -> optparse.OptionParser:
    """
    Return a parser for parsing requirement lines
    """
    parser = optparse.OptionParser(add_help_option=False)

    option_factories = SUPPORTED_OPTIONS + SUPPORTED_OPTIONS_REQ
    for option_factory in option_factories:
        option = option_factory()
        parser.add_option(option)

    # By default optparse sys.exits on parsing errors. We want to wrap
    # that in our own exception.
    def parser_exit(self: Any, msg: str) -> "NoReturn":
        raise OptionParsingError(msg)

    # NOTE: mypy disallows assigning to a method
    #       https://github.com/python/mypy/issues/2427
    parser.exit = parser_exit  # type: ignore

    return parser


def join_lines(lines_enum: ReqFileLines) -> ReqFileLines:
    """Joins a line ending in '\' with the previous line (except when following
    comments).  The joined line takes on the index of the first line.
    """
    primary_line_number = None
    new_line: List[str] = []
    for line_number, line in lines_enum:
        if not line.endswith("\\") or COMMENT_RE.match(line):
            if COMMENT_RE.match(line):
                # this ensures comments are always matched later
                line = " " + line
            if new_line:
                new_line.append(line)
                assert primary_line_number is not None
                yield primary_line_number, "".join(new_line)
                new_line = []
            else:
                yield line_number, line
        else:
            if not new_line:
                primary_line_number = line_number
            new_line.append(line.strip("\\"))

    # last line contains \
    if new_line:
        assert primary_line_number is not None
        yield primary_line_number, "".join(new_line)

    # TODO: handle space after '\'.


def ignore_comments(lines_enum: ReqFileLines) -> ReqFileLines:
    """
    Strips comments and filter empty lines.
    """
    for line_number, line in lines_enum:
        line = COMMENT_RE.sub("", line)
        line = line.strip()
        if line:
            yield line_number, line


def expand_env_variables(lines_enum: ReqFileLines) -> ReqFileLines:
    """Replace all environment variables that can be retrieved via `os.getenv`.

    The only allowed format for environment variables defined in the
    requirement file is `${MY_VARIABLE_1}` to ensure two things:

    1. Strings that contain a `$` aren't accidentally (partially) expanded.
    2. Ensure consistency across platforms for requirement files.

    These points are the result of a discussion on the `github pull
    request #3514 <https://github.com/pypa/pip/pull/3514>`_.

    Valid characters in variable names follow the `POSIX standard
    <http://pubs.opengroup.org/onlinepubs/9699919799/>`_ and are limited
    to uppercase letter, digits and the `_` (underscore).
    """
    for line_number, line in lines_enum:
        for env_var, var_name in ENV_VAR_RE.findall(line):
            value = os.getenv(var_name)
            if not value:
                continue

            line = line.replace(env_var, value)

        yield line_number, line


def get_file_content(url: str, session: "PipSession") -> Tuple[str, str]:
    """Gets the content of a file; it may be a filename, file: URL, or
    http: URL.  Returns (location, content).  Content is unicode.
    Respects # -*- coding: declarations on the retrieved files.

    :param url:         File path or url.
    :param session:     PipSession instance.
    """
    scheme = urllib.parse.urlsplit(url).scheme
    # Pip has special support for file:// URLs (LocalFSAdapter).
    if scheme in ["http", "https", "file"]:
        # Delay importing heavy network modules until absolutely necessary.
        from pip._internal.network.utils import raise_for_status

        resp = session.get(url)
        raise_for_status(resp)
        return resp.url, resp.text

    # Assume this is a bare path.
    try:
        with open(url, "rb") as f:
            raw_content = f.read()
    except OSError as exc:
        raise InstallationError(f"Could not open requirements file: {exc}")

    content = _decode_req_file(raw_content, url)

    return url, content


def _decode_req_file(data: bytes, url: str) -> str:
    for bom, encoding in BOMS:
        if data.startswith(bom):
            return data[len(bom) :].decode(encoding)

    for line in data.split(b"\n")[:2]:
        if line[0:1] == b"#":
            result = PEP263_ENCODING_RE.search(line)
            if result is not None:
                encoding = result.groups()[0].decode("ascii")
                return data.decode(encoding)

    try:
        return data.decode(DEFAULT_ENCODING)
    except UnicodeDecodeError:
        locale_encoding = locale.getpreferredencoding(False) or sys.getdefaultencoding()
        logging.warning(
            "unable to decode data from %s with default encoding %s, "
            "falling back to encoding from locale: %s. "
            "If this is intentional you should specify the encoding with a "
            "PEP-263 style comment, e.g. '# -*- coding: %s -*-'",
            url,
            DEFAULT_ENCODING,
            locale_encoding,
            locale_encoding,
        )
        return data.decode(locale_encoding)

# === NexusCore/openenv\Lib\site-packages\attr\_next_gen.py ===
# SPDX-License-Identifier: MIT

"""
These are keyword-only APIs that call `attr.s` and `attr.ib` with different
default values.
"""

from functools import partial

from . import setters
from ._funcs import asdict as _asdict
from ._funcs import astuple as _astuple
from ._make import (
    _DEFAULT_ON_SETATTR,
    NOTHING,
    _frozen_setattrs,
    attrib,
    attrs,
)
from .exceptions import UnannotatedAttributeError


def define(
    maybe_cls=None,
    *,
    these=None,
    repr=None,
    unsafe_hash=None,
    hash=None,
    init=None,
    slots=True,
    frozen=False,
    weakref_slot=True,
    str=False,
    auto_attribs=None,
    kw_only=False,
    cache_hash=False,
    auto_exc=True,
    eq=None,
    order=False,
    auto_detect=True,
    getstate_setstate=None,
    on_setattr=None,
    field_transformer=None,
    match_args=True,
):
    r"""
    A class decorator that adds :term:`dunder methods` according to
    :term:`fields <field>` specified using :doc:`type annotations <types>`,
    `field()` calls, or the *these* argument.

    Since *attrs* patches or replaces an existing class, you cannot use
    `object.__init_subclass__` with *attrs* classes, because it runs too early.
    As a replacement, you can define ``__attrs_init_subclass__`` on your class.
    It will be called by *attrs* classes that subclass it after they're
    created. See also :ref:`init-subclass`.

    Args:
        slots (bool):
            Create a :term:`slotted class <slotted classes>` that's more
            memory-efficient. Slotted classes are generally superior to the
            default dict classes, but have some gotchas you should know about,
            so we encourage you to read the :term:`glossary entry <slotted
            classes>`.

        auto_detect (bool):
            Instead of setting the *init*, *repr*, *eq*, and *hash* arguments
            explicitly, assume they are set to True **unless any** of the
            involved methods for one of the arguments is implemented in the
            *current* class (meaning, it is *not* inherited from some base
            class).

            So, for example by implementing ``__eq__`` on a class yourself,
            *attrs* will deduce ``eq=False`` and will create *neither*
            ``__eq__`` *nor* ``__ne__`` (but Python classes come with a
            sensible ``__ne__`` by default, so it *should* be enough to only
            implement ``__eq__`` in most cases).

            Passing True or False` to *init*, *repr*, *eq*, or *hash*
            overrides whatever *auto_detect* would determine.

        auto_exc (bool):
            If the class subclasses `BaseException` (which implicitly includes
            any subclass of any exception), the following happens to behave
            like a well-behaved Python exception class:

            - the values for *eq*, *order*, and *hash* are ignored and the
              instances compare and hash by the instance's ids [#]_ ,
            - all attributes that are either passed into ``__init__`` or have a
              default value are additionally available as a tuple in the
              ``args`` attribute,
            - the value of *str* is ignored leaving ``__str__`` to base
              classes.

            .. [#]
               Note that *attrs* will *not* remove existing implementations of
               ``__hash__`` or the equality methods. It just won't add own
               ones.

        on_setattr (~typing.Callable | list[~typing.Callable] | None | ~typing.Literal[attrs.setters.NO_OP]):
            A callable that is run whenever the user attempts to set an
            attribute (either by assignment like ``i.x = 42`` or by using
            `setattr` like ``setattr(i, "x", 42)``). It receives the same
            arguments as validators: the instance, the attribute that is being
            modified, and the new value.

            If no exception is raised, the attribute is set to the return value
            of the callable.

            If a list of callables is passed, they're automatically wrapped in
            an `attrs.setters.pipe`.

            If left None, the default behavior is to run converters and
            validators whenever an attribute is set.

        init (bool):
            Create a ``__init__`` method that initializes the *attrs*
            attributes. Leading underscores are stripped for the argument name,
            unless an alias is set on the attribute.

            .. seealso::
                `init` shows advanced ways to customize the generated
                ``__init__`` method, including executing code before and after.

        repr(bool):
            Create a ``__repr__`` method with a human readable representation
            of *attrs* attributes.

        str (bool):
            Create a ``__str__`` method that is identical to ``__repr__``. This
            is usually not necessary except for `Exception`\ s.

        eq (bool | None):
            If True or None (default), add ``__eq__`` and ``__ne__`` methods
            that check two instances for equality.

            .. seealso::
                `comparison` describes how to customize the comparison behavior
                going as far comparing NumPy arrays.

        order (bool | None):
            If True, add ``__lt__``, ``__le__``, ``__gt__``, and ``__ge__``
            methods that behave like *eq* above and allow instances to be
            ordered.

            They compare the instances as if they were tuples of their *attrs*
            attributes if and only if the types of both classes are
            *identical*.

            If `None` mirror value of *eq*.

            .. seealso:: `comparison`

        unsafe_hash (bool | None):
            If None (default), the ``__hash__`` method is generated according
            how *eq* and *frozen* are set.

            1. If *both* are True, *attrs* will generate a ``__hash__`` for
               you.
            2. If *eq* is True and *frozen* is False, ``__hash__`` will be set
               to None, marking it unhashable (which it is).
            3. If *eq* is False, ``__hash__`` will be left untouched meaning
               the ``__hash__`` method of the base class will be used. If the
               base class is `object`, this means it will fall back to id-based
               hashing.

            Although not recommended, you can decide for yourself and force
            *attrs* to create one (for example, if the class is immutable even
            though you didn't freeze it programmatically) by passing True or
            not.  Both of these cases are rather special and should be used
            carefully.

            .. seealso::

                - Our documentation on `hashing`,
                - Python's documentation on `object.__hash__`,
                - and the `GitHub issue that led to the default \ behavior
                  <https://github.com/python-attrs/attrs/issues/136>`_ for more
                  details.

        hash (bool | None):
            Deprecated alias for *unsafe_hash*. *unsafe_hash* takes precedence.

        cache_hash (bool):
            Ensure that the object's hash code is computed only once and stored
            on the object.  If this is set to True, hashing must be either
            explicitly or implicitly enabled for this class.  If the hash code
            is cached, avoid any reassignments of fields involved in hash code
            computation or mutations of the objects those fields point to after
            object creation.  If such changes occur, the behavior of the
            object's hash code is undefined.

        frozen (bool):
            Make instances immutable after initialization.  If someone attempts
            to modify a frozen instance, `attrs.exceptions.FrozenInstanceError`
            is raised.

            .. note::

                1. This is achieved by installing a custom ``__setattr__``
                   method on your class, so you can't implement your own.

                2. True immutability is impossible in Python.

                3. This *does* have a minor a runtime performance `impact
                   <how-frozen>` when initializing new instances.  In other
                   words: ``__init__`` is slightly slower with ``frozen=True``.

                4. If a class is frozen, you cannot modify ``self`` in
                   ``__attrs_post_init__`` or a self-written ``__init__``. You
                   can circumvent that limitation by using
                   ``object.__setattr__(self, "attribute_name", value)``.

                5. Subclasses of a frozen class are frozen too.

        kw_only (bool):
            Make all attributes keyword-only in the generated ``__init__`` (if
            *init* is False, this parameter is ignored).

        weakref_slot (bool):
            Make instances weak-referenceable.  This has no effect unless
            *slots* is True.

        field_transformer (~typing.Callable | None):
            A function that is called with the original class object and all
            fields right before *attrs* finalizes the class.  You can use this,
            for example, to automatically add converters or validators to
            fields based on their types.

            .. seealso:: `transform-fields`

        match_args (bool):
            If True (default), set ``__match_args__`` on the class to support
            :pep:`634` (*Structural Pattern Matching*). It is a tuple of all
            non-keyword-only ``__init__`` parameter names on Python 3.10 and
            later. Ignored on older Python versions.

        collect_by_mro (bool):
            If True, *attrs* collects attributes from base classes correctly
            according to the `method resolution order
            <https://docs.python.org/3/howto/mro.html>`_. If False, *attrs*
            will mimic the (wrong) behavior of `dataclasses` and :pep:`681`.

            See also `issue #428
            <https://github.com/python-attrs/attrs/issues/428>`_.

        getstate_setstate (bool | None):
            .. note::

                This is usually only interesting for slotted classes and you
                should probably just set *auto_detect* to True.

            If True, ``__getstate__`` and ``__setstate__`` are generated and
            attached to the class. This is necessary for slotted classes to be
            pickleable. If left None, it's True by default for slotted classes
            and False for dict classes.

            If *auto_detect* is True, and *getstate_setstate* is left None, and
            **either** ``__getstate__`` or ``__setstate__`` is detected
            directly on the class (meaning: not inherited), it is set to False
            (this is usually what you want).

        auto_attribs (bool | None):
            If True, look at type annotations to determine which attributes to
            use, like `dataclasses`. If False, it will only look for explicit
            :func:`field` class attributes, like classic *attrs*.

            If left None, it will guess:

            1. If any attributes are annotated and no unannotated
               `attrs.field`\ s are found, it assumes *auto_attribs=True*.
            2. Otherwise it assumes *auto_attribs=False* and tries to collect
               `attrs.field`\ s.

            If *attrs* decides to look at type annotations, **all** fields
            **must** be annotated. If *attrs* encounters a field that is set to
            a :func:`field` / `attr.ib` but lacks a type annotation, an
            `attrs.exceptions.UnannotatedAttributeError` is raised.  Use
            ``field_name: typing.Any = field(...)`` if you don't want to set a
            type.

            .. warning::

                For features that use the attribute name to create decorators
                (for example, :ref:`validators <validators>`), you still *must*
                assign :func:`field` / `attr.ib` to them. Otherwise Python will
                either not find the name or try to use the default value to
                call, for example, ``validator`` on it.

            Attributes annotated as `typing.ClassVar`, and attributes that are
            neither annotated nor set to an `field()` are **ignored**.

        these (dict[str, object]):
            A dictionary of name to the (private) return value of `field()`
            mappings. This is useful to avoid the definition of your attributes
            within the class body because you can't (for example, if you want
            to add ``__repr__`` methods to Django models) or don't want to.

            If *these* is not `None`, *attrs* will *not* search the class body
            for attributes and will *not* remove any attributes from it.

            The order is deduced from the order of the attributes inside
            *these*.

            Arguably, this is a rather obscure feature.

    .. versionadded:: 20.1.0
    .. versionchanged:: 21.3.0 Converters are also run ``on_setattr``.
    .. versionadded:: 22.2.0
       *unsafe_hash* as an alias for *hash* (for :pep:`681` compliance).
    .. versionchanged:: 24.1.0
       Instances are not compared as tuples of attributes anymore, but using a
       big ``and`` condition. This is faster and has more correct behavior for
       uncomparable values like `math.nan`.
    .. versionadded:: 24.1.0
       If a class has an *inherited* classmethod called
       ``__attrs_init_subclass__``, it is executed after the class is created.
    .. deprecated:: 24.1.0 *hash* is deprecated in favor of *unsafe_hash*.
    .. versionadded:: 24.3.0
       Unless already present, a ``__replace__`` method is automatically
       created for `copy.replace` (Python 3.13+ only).

    .. note::

        The main differences to the classic `attr.s` are:

        - Automatically detect whether or not *auto_attribs* should be `True`
          (c.f. *auto_attribs* parameter).
        - Converters and validators run when attributes are set by default --
          if *frozen* is `False`.
        - *slots=True*

          Usually, this has only upsides and few visible effects in everyday
          programming. But it *can* lead to some surprising behaviors, so
          please make sure to read :term:`slotted classes`.

        - *auto_exc=True*
        - *auto_detect=True*
        - *order=False*
        - Some options that were only relevant on Python 2 or were kept around
          for backwards-compatibility have been removed.

    """

    def do_it(cls, auto_attribs):
        return attrs(
            maybe_cls=cls,
            these=these,
            repr=repr,
            hash=hash,
            unsafe_hash=unsafe_hash,
            init=init,
            slots=slots,
            frozen=frozen,
            weakref_slot=weakref_slot,
            str=str,
            auto_attribs=auto_attribs,
            kw_only=kw_only,
            cache_hash=cache_hash,
            auto_exc=auto_exc,
            eq=eq,
            order=order,
            auto_detect=auto_detect,
            collect_by_mro=True,
            getstate_setstate=getstate_setstate,
            on_setattr=on_setattr,
            field_transformer=field_transformer,
            match_args=match_args,
        )

    def wrap(cls):
        """
        Making this a wrapper ensures this code runs during class creation.

        We also ensure that frozen-ness of classes is inherited.
        """
        nonlocal frozen, on_setattr

        had_on_setattr = on_setattr not in (None, setters.NO_OP)

        # By default, mutable classes convert & validate on setattr.
        if frozen is False and on_setattr is None:
            on_setattr = _DEFAULT_ON_SETATTR

        # However, if we subclass a frozen class, we inherit the immutability
        # and disable on_setattr.
        for base_cls in cls.__bases__:
            if base_cls.__setattr__ is _frozen_setattrs:
                if had_on_setattr:
                    msg = "Frozen classes can't use on_setattr (frozen-ness was inherited)."
                    raise ValueError(msg)

                on_setattr = setters.NO_OP
                break

        if auto_attribs is not None:
            return do_it(cls, auto_attribs)

        try:
            return do_it(cls, True)
        except UnannotatedAttributeError:
            return do_it(cls, False)

    # maybe_cls's type depends on the usage of the decorator.  It's a class
    # if it's used as `@attrs` but `None` if used as `@attrs()`.
    if maybe_cls is None:
        return wrap

    return wrap(maybe_cls)


mutable = define
frozen = partial(define, frozen=True, on_setattr=None)


def field(
    *,
    default=NOTHING,
    validator=None,
    repr=True,
    hash=None,
    init=True,
    metadata=None,
    type=None,
    converter=None,
    factory=None,
    kw_only=False,
    eq=None,
    order=None,
    on_setattr=None,
    alias=None,
):
    """
    Create a new :term:`field` / :term:`attribute` on a class.

    ..  warning::

        Does **nothing** unless the class is also decorated with
        `attrs.define` (or similar)!

    Args:
        default:
            A value that is used if an *attrs*-generated ``__init__`` is used
            and no value is passed while instantiating or the attribute is
            excluded using ``init=False``.

            If the value is an instance of `attrs.Factory`, its callable will
            be used to construct a new value (useful for mutable data types
            like lists or dicts).

            If a default is not set (or set manually to `attrs.NOTHING`), a
            value *must* be supplied when instantiating; otherwise a
            `TypeError` will be raised.

            .. seealso:: `defaults`

        factory (~typing.Callable):
            Syntactic sugar for ``default=attr.Factory(factory)``.

        validator (~typing.Callable | list[~typing.Callable]):
            Callable that is called by *attrs*-generated ``__init__`` methods
            after the instance has been initialized.  They receive the
            initialized instance, the :func:`~attrs.Attribute`, and the passed
            value.

            The return value is *not* inspected so the validator has to throw
            an exception itself.

            If a `list` is passed, its items are treated as validators and must
            all pass.

            Validators can be globally disabled and re-enabled using
            `attrs.validators.get_disabled` / `attrs.validators.set_disabled`.

            The validator can also be set using decorator notation as shown
            below.

            .. seealso:: :ref:`validators`

        repr (bool | ~typing.Callable):
            Include this attribute in the generated ``__repr__`` method. If
            True, include the attribute; if False, omit it. By default, the
            built-in ``repr()`` function is used. To override how the attribute
            value is formatted, pass a ``callable`` that takes a single value
            and returns a string. Note that the resulting string is used as-is,
            which means it will be used directly *instead* of calling
            ``repr()`` (the default).

        eq (bool | ~typing.Callable):
            If True (default), include this attribute in the generated
            ``__eq__`` and ``__ne__`` methods that check two instances for
            equality. To override how the attribute value is compared, pass a
            callable that takes a single value and returns the value to be
            compared.

            .. seealso:: `comparison`

        order (bool | ~typing.Callable):
            If True (default), include this attributes in the generated
            ``__lt__``, ``__le__``, ``__gt__`` and ``__ge__`` methods. To
            override how the attribute value is ordered, pass a callable that
            takes a single value and returns the value to be ordered.

            .. seealso:: `comparison`

        hash (bool | None):
            Include this attribute in the generated ``__hash__`` method.  If
            None (default), mirror *eq*'s value.  This is the correct behavior
            according the Python spec.  Setting this value to anything else
            than None is *discouraged*.

            .. seealso:: `hashing`

        init (bool):
            Include this attribute in the generated ``__init__`` method.

            It is possible to set this to False and set a default value. In
            that case this attributed is unconditionally initialized with the
            specified default value or factory.

            .. seealso:: `init`

        converter (typing.Callable | Converter):
            A callable that is called by *attrs*-generated ``__init__`` methods
            to convert attribute's value to the desired format.

            If a vanilla callable is passed, it is given the passed-in value as
            the only positional argument. It is possible to receive additional
            arguments by wrapping the callable in a `Converter`.

            Either way, the returned value will be used as the new value of the
            attribute.  The value is converted before being passed to the
            validator, if any.

            .. seealso:: :ref:`converters`

        metadata (dict | None):
            An arbitrary mapping, to be used by third-party code.

            .. seealso:: `extending-metadata`.

        type (type):
            The type of the attribute. Nowadays, the preferred method to
            specify the type is using a variable annotation (see :pep:`526`).
            This argument is provided for backwards-compatibility and for usage
            with `make_class`. Regardless of the approach used, the type will
            be stored on ``Attribute.type``.

            Please note that *attrs* doesn't do anything with this metadata by
            itself. You can use it as part of your own code or for `static type
            checking <types>`.

        kw_only (bool):
            Make this attribute keyword-only in the generated ``__init__`` (if
            ``init`` is False, this parameter is ignored).

        on_setattr (~typing.Callable | list[~typing.Callable] | None | ~typing.Literal[attrs.setters.NO_OP]):
            Allows to overwrite the *on_setattr* setting from `attr.s`. If left
            None, the *on_setattr* value from `attr.s` is used. Set to
            `attrs.setters.NO_OP` to run **no** `setattr` hooks for this
            attribute -- regardless of the setting in `define()`.

        alias (str | None):
            Override this attribute's parameter name in the generated
            ``__init__`` method. If left None, default to ``name`` stripped
            of leading underscores. See `private-attributes`.

    .. versionadded:: 20.1.0
    .. versionchanged:: 21.1.0
       *eq*, *order*, and *cmp* also accept a custom callable
    .. versionadded:: 22.2.0 *alias*
    .. versionadded:: 23.1.0
       The *type* parameter has been re-added; mostly for `attrs.make_class`.
       Please note that type checkers ignore this metadata.

    .. seealso::

       `attr.ib`
    """
    return attrib(
        default=default,
        validator=validator,
        repr=repr,
        hash=hash,
        init=init,
        metadata=metadata,
        type=type,
        converter=converter,
        factory=factory,
        kw_only=kw_only,
        eq=eq,
        order=order,
        on_setattr=on_setattr,
        alias=alias,
    )


def asdict(inst, *, recurse=True, filter=None, value_serializer=None):
    """
    Same as `attr.asdict`, except that collections types are always retained
    and dict is always used as *dict_factory*.

    .. versionadded:: 21.3.0
    """
    return _asdict(
        inst=inst,
        recurse=recurse,
        filter=filter,
        value_serializer=value_serializer,
        retain_collection_types=True,
    )


def astuple(inst, *, recurse=True, filter=None):
    """
    Same as `attr.astuple`, except that collections types are always retained
    and `tuple` is always used as the *tuple_factory*.

    .. versionadded:: 21.3.0
    """
    return _astuple(
        inst=inst, recurse=recurse, filter=filter, retain_collection_types=True
    )

# === NexusCore/openenv\Lib\site-packages\pip\_internal\req\req_file.py ===
"""
Requirements file parsing
"""

import codecs
import locale
import logging
import optparse
import os
import re
import shlex
import sys
import urllib.parse
from dataclasses import dataclass
from optparse import Values
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    List,
    NoReturn,
    Optional,
    Tuple,
)

from pip._internal.cli import cmdoptions
from pip._internal.exceptions import InstallationError, RequirementsFileParseError
from pip._internal.models.search_scope import SearchScope

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.network.session import PipSession

__all__ = ["parse_requirements"]

ReqFileLines = Iterable[Tuple[int, str]]

LineParser = Callable[[str], Tuple[str, Values]]

SCHEME_RE = re.compile(r"^(http|https|file):", re.I)
COMMENT_RE = re.compile(r"(^|\s+)#.*$")

# Matches environment variable-style values in '${MY_VARIABLE_1}' with the
# variable name consisting of only uppercase letters, digits or the '_'
# (underscore). This follows the POSIX standard defined in IEEE Std 1003.1,
# 2013 Edition.
ENV_VAR_RE = re.compile(r"(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})")

SUPPORTED_OPTIONS: List[Callable[..., optparse.Option]] = [
    cmdoptions.index_url,
    cmdoptions.extra_index_url,
    cmdoptions.no_index,
    cmdoptions.constraints,
    cmdoptions.requirements,
    cmdoptions.editable,
    cmdoptions.find_links,
    cmdoptions.no_binary,
    cmdoptions.only_binary,
    cmdoptions.prefer_binary,
    cmdoptions.require_hashes,
    cmdoptions.pre,
    cmdoptions.trusted_host,
    cmdoptions.use_new_feature,
]

# options to be passed to requirements
SUPPORTED_OPTIONS_REQ: List[Callable[..., optparse.Option]] = [
    cmdoptions.global_options,
    cmdoptions.hash,
    cmdoptions.config_settings,
]

SUPPORTED_OPTIONS_EDITABLE_REQ: List[Callable[..., optparse.Option]] = [
    cmdoptions.config_settings,
]


# the 'dest' string values
SUPPORTED_OPTIONS_REQ_DEST = [str(o().dest) for o in SUPPORTED_OPTIONS_REQ]
SUPPORTED_OPTIONS_EDITABLE_REQ_DEST = [
    str(o().dest) for o in SUPPORTED_OPTIONS_EDITABLE_REQ
]

# order of BOMS is important: codecs.BOM_UTF16_LE is a prefix of codecs.BOM_UTF32_LE
# so data.startswith(BOM_UTF16_LE) would be true for UTF32_LE data
BOMS: List[Tuple[bytes, str]] = [
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF16, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
]

PEP263_ENCODING_RE = re.compile(rb"coding[:=]\s*([-\w.]+)")
DEFAULT_ENCODING = "utf-8"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedRequirement:
    # TODO: replace this with slots=True when dropping Python 3.9 support.
    __slots__ = (
        "requirement",
        "is_editable",
        "comes_from",
        "constraint",
        "options",
        "line_source",
    )

    requirement: str
    is_editable: bool
    comes_from: str
    constraint: bool
    options: Optional[Dict[str, Any]]
    line_source: Optional[str]


@dataclass(frozen=True)
class ParsedLine:
    __slots__ = ("filename", "lineno", "args", "opts", "constraint")

    filename: str
    lineno: int
    args: str
    opts: Values
    constraint: bool

    @property
    def is_editable(self) -> bool:
        return bool(self.opts.editables)

    @property
    def requirement(self) -> Optional[str]:
        if self.args:
            return self.args
        elif self.is_editable:
            # We don't support multiple -e on one line
            return self.opts.editables[0]
        return None


def parse_requirements(
    filename: str,
    session: "PipSession",
    finder: Optional["PackageFinder"] = None,
    options: Optional[optparse.Values] = None,
    constraint: bool = False,
) -> Generator[ParsedRequirement, None, None]:
    """Parse a requirements file and yield ParsedRequirement instances.

    :param filename:    Path or url of requirements file.
    :param session:     PipSession instance.
    :param finder:      Instance of pip.index.PackageFinder.
    :param options:     cli options.
    :param constraint:  If true, parsing a constraint file rather than
        requirements file.
    """
    line_parser = get_line_parser(finder)
    parser = RequirementsFileParser(session, line_parser)

    for parsed_line in parser.parse(filename, constraint):
        parsed_req = handle_line(
            parsed_line, options=options, finder=finder, session=session
        )
        if parsed_req is not None:
            yield parsed_req


def preprocess(content: str) -> ReqFileLines:
    """Split, filter, and join lines, and return a line iterator

    :param content: the content of the requirements file
    """
    lines_enum: ReqFileLines = enumerate(content.splitlines(), start=1)
    lines_enum = join_lines(lines_enum)
    lines_enum = ignore_comments(lines_enum)
    lines_enum = expand_env_variables(lines_enum)
    return lines_enum


def handle_requirement_line(
    line: ParsedLine,
    options: Optional[optparse.Values] = None,
) -> ParsedRequirement:
    # preserve for the nested code path
    line_comes_from = "{} {} (line {})".format(
        "-c" if line.constraint else "-r",
        line.filename,
        line.lineno,
    )

    assert line.requirement is not None

    # get the options that apply to requirements
    if line.is_editable:
        supported_dest = SUPPORTED_OPTIONS_EDITABLE_REQ_DEST
    else:
        supported_dest = SUPPORTED_OPTIONS_REQ_DEST
    req_options = {}
    for dest in supported_dest:
        if dest in line.opts.__dict__ and line.opts.__dict__[dest]:
            req_options[dest] = line.opts.__dict__[dest]

    line_source = f"line {line.lineno} of {line.filename}"
    return ParsedRequirement(
        requirement=line.requirement,
        is_editable=line.is_editable,
        comes_from=line_comes_from,
        constraint=line.constraint,
        options=req_options,
        line_source=line_source,
    )


def handle_option_line(
    opts: Values,
    filename: str,
    lineno: int,
    finder: Optional["PackageFinder"] = None,
    options: Optional[optparse.Values] = None,
    session: Optional["PipSession"] = None,
) -> None:
    if opts.hashes:
        logger.warning(
            "%s line %s has --hash but no requirement, and will be ignored.",
            filename,
            lineno,
        )

    if options:
        # percolate options upward
        if opts.require_hashes:
            options.require_hashes = opts.require_hashes
        if opts.features_enabled:
            options.features_enabled.extend(
                f for f in opts.features_enabled if f not in options.features_enabled
            )

    # set finder options
    if finder:
        find_links = finder.find_links
        index_urls = finder.index_urls
        no_index = finder.search_scope.no_index
        if opts.no_index is True:
            no_index = True
            index_urls = []
        if opts.index_url and not no_index:
            index_urls = [opts.index_url]
        if opts.extra_index_urls and not no_index:
            index_urls.extend(opts.extra_index_urls)
        if opts.find_links:
            # FIXME: it would be nice to keep track of the source
            # of the find_links: support a find-links local path
            # relative to a requirements file.
            value = opts.find_links[0]
            req_dir = os.path.dirname(os.path.abspath(filename))
            relative_to_reqs_file = os.path.join(req_dir, value)
            if os.path.exists(relative_to_reqs_file):
                value = relative_to_reqs_file
            find_links.append(value)

        if session:
            # We need to update the auth urls in session
            session.update_index_urls(index_urls)

        search_scope = SearchScope(
            find_links=find_links,
            index_urls=index_urls,
            no_index=no_index,
        )
        finder.search_scope = search_scope

        if opts.pre:
            finder.set_allow_all_prereleases()

        if opts.prefer_binary:
            finder.set_prefer_binary()

        if session:
            for host in opts.trusted_hosts or []:
                source = f"line {lineno} of {filename}"
                session.add_trusted_host(host, source=source)


def handle_line(
    line: ParsedLine,
    options: Optional[optparse.Values] = None,
    finder: Optional["PackageFinder"] = None,
    session: Optional["PipSession"] = None,
) -> Optional[ParsedRequirement]:
    """Handle a single parsed requirements line; This can result in
    creating/yielding requirements, or updating the finder.

    :param line:        The parsed line to be processed.
    :param options:     CLI options.
    :param finder:      The finder - updated by non-requirement lines.
    :param session:     The session - updated by non-requirement lines.

    Returns a ParsedRequirement object if the line is a requirement line,
    otherwise returns None.

    For lines that contain requirements, the only options that have an effect
    are from SUPPORTED_OPTIONS_REQ, and they are scoped to the
    requirement. Other options from SUPPORTED_OPTIONS may be present, but are
    ignored.

    For lines that do not contain requirements, the only options that have an
    effect are from SUPPORTED_OPTIONS. Options from SUPPORTED_OPTIONS_REQ may
    be present, but are ignored. These lines may contain multiple options
    (although our docs imply only one is supported), and all our parsed and
    affect the finder.
    """

    if line.requirement is not None:
        parsed_req = handle_requirement_line(line, options)
        return parsed_req
    else:
        handle_option_line(
            line.opts,
            line.filename,
            line.lineno,
            finder,
            options,
            session,
        )
        return None


class RequirementsFileParser:
    def __init__(
        self,
        session: "PipSession",
        line_parser: LineParser,
    ) -> None:
        self._session = session
        self._line_parser = line_parser

    def parse(
        self, filename: str, constraint: bool
    ) -> Generator[ParsedLine, None, None]:
        """Parse a given file, yielding parsed lines."""
        yield from self._parse_and_recurse(
            filename, constraint, [{os.path.abspath(filename): None}]
        )

    def _parse_and_recurse(
        self,
        filename: str,
        constraint: bool,
        parsed_files_stack: List[Dict[str, Optional[str]]],
    ) -> Generator[ParsedLine, None, None]:
        for line in self._parse_file(filename, constraint):
            if line.requirement is None and (
                line.opts.requirements or line.opts.constraints
            ):
                # parse a nested requirements file
                if line.opts.requirements:
                    req_path = line.opts.requirements[0]
                    nested_constraint = False
                else:
                    req_path = line.opts.constraints[0]
                    nested_constraint = True

                # original file is over http
                if SCHEME_RE.search(filename):
                    # do a url join so relative paths work
                    req_path = urllib.parse.urljoin(filename, req_path)
                # original file and nested file are paths
                elif not SCHEME_RE.search(req_path):
                    # do a join so relative paths work
                    # and then abspath so that we can identify recursive references
                    req_path = os.path.abspath(
                        os.path.join(
                            os.path.dirname(filename),
                            req_path,
                        )
                    )
                parsed_files = parsed_files_stack[0]
                if req_path in parsed_files:
                    initial_file = parsed_files[req_path]
                    tail = (
                        f" and again in {initial_file}"
                        if initial_file is not None
                        else ""
                    )
                    raise RequirementsFileParseError(
                        f"{req_path} recursively references itself in {filename}{tail}"
                    )
                # Keeping a track where was each file first included in
                new_parsed_files = parsed_files.copy()
                new_parsed_files[req_path] = filename
                yield from self._parse_and_recurse(
                    req_path, nested_constraint, [new_parsed_files, *parsed_files_stack]
                )
            else:
                yield line

    def _parse_file(
        self, filename: str, constraint: bool
    ) -> Generator[ParsedLine, None, None]:
        _, content = get_file_content(filename, self._session)

        lines_enum = preprocess(content)

        for line_number, line in lines_enum:
            try:
                args_str, opts = self._line_parser(line)
            except OptionParsingError as e:
                # add offending line
                msg = f"Invalid requirement: {line}\n{e.msg}"
                raise RequirementsFileParseError(msg)

            yield ParsedLine(
                filename,
                line_number,
                args_str,
                opts,
                constraint,
            )


def get_line_parser(finder: Optional["PackageFinder"]) -> LineParser:
    def parse_line(line: str) -> Tuple[str, Values]:
        # Build new parser for each line since it accumulates appendable
        # options.
        parser = build_parser()
        defaults = parser.get_default_values()
        defaults.index_url = None
        if finder:
            defaults.format_control = finder.format_control

        args_str, options_str = break_args_options(line)

        try:
            options = shlex.split(options_str)
        except ValueError as e:
            raise OptionParsingError(f"Could not split options: {options_str}") from e

        opts, _ = parser.parse_args(options, defaults)

        return args_str, opts

    return parse_line


def break_args_options(line: str) -> Tuple[str, str]:
    """Break up the line into an args and options string.  We only want to shlex
    (and then optparse) the options, not the args.  args can contain markers
    which are corrupted by shlex.
    """
    tokens = line.split(" ")
    args = []
    options = tokens[:]
    for token in tokens:
        if token.startswith("-") or token.startswith("--"):
            break
        else:
            args.append(token)
            options.pop(0)
    return " ".join(args), " ".join(options)


class OptionParsingError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg


def build_parser() -> optparse.OptionParser:
    """
    Return a parser for parsing requirement lines
    """
    parser = optparse.OptionParser(add_help_option=False)

    option_factories = SUPPORTED_OPTIONS + SUPPORTED_OPTIONS_REQ
    for option_factory in option_factories:
        option = option_factory()
        parser.add_option(option)

    # By default optparse sys.exits on parsing errors. We want to wrap
    # that in our own exception.
    def parser_exit(self: Any, msg: str) -> "NoReturn":
        raise OptionParsingError(msg)

    # NOTE: mypy disallows assigning to a method
    #       https://github.com/python/mypy/issues/2427
    parser.exit = parser_exit  # type: ignore

    return parser


def join_lines(lines_enum: ReqFileLines) -> ReqFileLines:
    """Joins a line ending in '\' with the previous line (except when following
    comments).  The joined line takes on the index of the first line.
    """
    primary_line_number = None
    new_line: List[str] = []
    for line_number, line in lines_enum:
        if not line.endswith("\\") or COMMENT_RE.match(line):
            if COMMENT_RE.match(line):
                # this ensures comments are always matched later
                line = " " + line
            if new_line:
                new_line.append(line)
                assert primary_line_number is not None
                yield primary_line_number, "".join(new_line)
                new_line = []
            else:
                yield line_number, line
        else:
            if not new_line:
                primary_line_number = line_number
            new_line.append(line.strip("\\"))

    # last line contains \
    if new_line:
        assert primary_line_number is not None
        yield primary_line_number, "".join(new_line)

    # TODO: handle space after '\'.


def ignore_comments(lines_enum: ReqFileLines) -> ReqFileLines:
    """
    Strips comments and filter empty lines.
    """
    for line_number, line in lines_enum:
        line = COMMENT_RE.sub("", line)
        line = line.strip()
        if line:
            yield line_number, line


def expand_env_variables(lines_enum: ReqFileLines) -> ReqFileLines:
    """Replace all environment variables that can be retrieved via `os.getenv`.

    The only allowed format for environment variables defined in the
    requirement file is `${MY_VARIABLE_1}` to ensure two things:

    1. Strings that contain a `$` aren't accidentally (partially) expanded.
    2. Ensure consistency across platforms for requirement files.

    These points are the result of a discussion on the `github pull
    request #3514 <https://github.com/pypa/pip/pull/3514>`_.

    Valid characters in variable names follow the `POSIX standard
    <http://pubs.opengroup.org/onlinepubs/9699919799/>`_ and are limited
    to uppercase letter, digits and the `_` (underscore).
    """
    for line_number, line in lines_enum:
        for env_var, var_name in ENV_VAR_RE.findall(line):
            value = os.getenv(var_name)
            if not value:
                continue

            line = line.replace(env_var, value)

        yield line_number, line


def get_file_content(url: str, session: "PipSession") -> Tuple[str, str]:
    """Gets the content of a file; it may be a filename, file: URL, or
    http: URL.  Returns (location, content).  Content is unicode.
    Respects # -*- coding: declarations on the retrieved files.

    :param url:         File path or url.
    :param session:     PipSession instance.
    """
    scheme = urllib.parse.urlsplit(url).scheme
    # Pip has special support for file:// URLs (LocalFSAdapter).
    if scheme in ["http", "https", "file"]:
        # Delay importing heavy network modules until absolutely necessary.
        from pip._internal.network.utils import raise_for_status

        resp = session.get(url)
        raise_for_status(resp)
        return resp.url, resp.text

    # Assume this is a bare path.
    try:
        with open(url, "rb") as f:
            raw_content = f.read()
    except OSError as exc:
        raise InstallationError(f"Could not open requirements file: {exc}")

    content = _decode_req_file(raw_content, url)

    return url, content


def _decode_req_file(data: bytes, url: str) -> str:
    for bom, encoding in BOMS:
        if data.startswith(bom):
            return data[len(bom) :].decode(encoding)

    for line in data.split(b"\n")[:2]:
        if line[0:1] == b"#":
            result = PEP263_ENCODING_RE.search(line)
            if result is not None:
                encoding = result.groups()[0].decode("ascii")
                return data.decode(encoding)

    try:
        return data.decode(DEFAULT_ENCODING)
    except UnicodeDecodeError:
        locale_encoding = locale.getpreferredencoding(False) or sys.getdefaultencoding()
        logging.warning(
            "unable to decode data from %s with default encoding %s, "
            "falling back to encoding from locale: %s. "
            "If this is intentional you should specify the encoding with a "
            "PEP-263 style comment, e.g. '# -*- coding: %s -*-'",
            url,
            DEFAULT_ENCODING,
            locale_encoding,
            locale_encoding,
        )
        return data.decode(locale_encoding)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\util\retry.py ===
from __future__ import absolute_import

import email
import logging
import re
import time
import warnings
from collections import namedtuple
from itertools import takewhile

from ..exceptions import (
    ConnectTimeoutError,
    InvalidHeader,
    MaxRetryError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    ResponseError,
)
from ..packages import six

log = logging.getLogger(__name__)


# Data structure for representing the metadata of requests that result in a retry.
RequestHistory = namedtuple(
    "RequestHistory", ["method", "url", "error", "status", "redirect_location"]
)


# TODO: In v2 we can remove this sentinel and metaclass with deprecated options.
_Default = object()


class _RetryMeta(type):
    @property
    def DEFAULT_METHOD_WHITELIST(cls):
        warnings.warn(
            "Using 'Retry.DEFAULT_METHOD_WHITELIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_ALLOWED_METHODS' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_ALLOWED_METHODS

    @DEFAULT_METHOD_WHITELIST.setter
    def DEFAULT_METHOD_WHITELIST(cls, value):
        warnings.warn(
            "Using 'Retry.DEFAULT_METHOD_WHITELIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_ALLOWED_METHODS' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_ALLOWED_METHODS = value

    @property
    def DEFAULT_REDIRECT_HEADERS_BLACKLIST(cls):
        warnings.warn(
            "Using 'Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_REMOVE_HEADERS_ON_REDIRECT' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_REMOVE_HEADERS_ON_REDIRECT

    @DEFAULT_REDIRECT_HEADERS_BLACKLIST.setter
    def DEFAULT_REDIRECT_HEADERS_BLACKLIST(cls, value):
        warnings.warn(
            "Using 'Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_REMOVE_HEADERS_ON_REDIRECT' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_REMOVE_HEADERS_ON_REDIRECT = value

    @property
    def BACKOFF_MAX(cls):
        warnings.warn(
            "Using 'Retry.BACKOFF_MAX' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_BACKOFF_MAX' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_BACKOFF_MAX

    @BACKOFF_MAX.setter
    def BACKOFF_MAX(cls, value):
        warnings.warn(
            "Using 'Retry.BACKOFF_MAX' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_BACKOFF_MAX' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_BACKOFF_MAX = value


@six.add_metaclass(_RetryMeta)
class Retry(object):
    """Retry configuration.

    Each retry attempt will create a new Retry object with updated values, so
    they can be safely reused.

    Retries can be defined as a default for a pool::

        retries = Retry(connect=5, read=2, redirect=5)
        http = PoolManager(retries=retries)
        response = http.request('GET', 'http://example.com/')

    Or per-request (which overrides the default for the pool)::

        response = http.request('GET', 'http://example.com/', retries=Retry(10))

    Retries can be disabled by passing ``False``::

        response = http.request('GET', 'http://example.com/', retries=False)

    Errors will be wrapped in :class:`~urllib3.exceptions.MaxRetryError` unless
    retries are disabled, in which case the causing exception will be raised.

    :param int total:
        Total number of retries to allow. Takes precedence over other counts.

        Set to ``None`` to remove this constraint and fall back on other
        counts.

        Set to ``0`` to fail on the first retry.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int connect:
        How many connection-related errors to retry on.

        These are errors raised before the request is sent to the remote server,
        which we assume has not triggered the server to process the request.

        Set to ``0`` to fail on the first retry of this type.

    :param int read:
        How many times to retry on read errors.

        These errors are raised after the request was sent to the server, so the
        request may have side-effects.

        Set to ``0`` to fail on the first retry of this type.

    :param int redirect:
        How many redirects to perform. Limit this to avoid infinite redirect
        loops.

        A redirect is a HTTP response with a status code 301, 302, 303, 307 or
        308.

        Set to ``0`` to fail on the first retry of this type.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int status:
        How many times to retry on bad status codes.

        These are retries made on responses, where status code matches
        ``status_forcelist``.

        Set to ``0`` to fail on the first retry of this type.

    :param int other:
        How many times to retry on other errors.

        Other errors are errors that are not connect, read, redirect or status errors.
        These errors might be raised after the request was sent to the server, so the
        request might have side-effects.

        Set to ``0`` to fail on the first retry of this type.

        If ``total`` is not set, it's a good idea to set this to 0 to account
        for unexpected edge cases and avoid infinite retry loops.

    :param iterable allowed_methods:
        Set of uppercased HTTP method verbs that we should retry on.

        By default, we only retry on methods which are considered to be
        idempotent (multiple requests with the same parameters end with the
        same state). See :attr:`Retry.DEFAULT_ALLOWED_METHODS`.

        Set to a ``False`` value to retry on any verb.

        .. warning::

            Previously this parameter was named ``method_whitelist``, that
            usage is deprecated in v1.26.0 and will be removed in v2.0.

    :param iterable status_forcelist:
        A set of integer HTTP status codes that we should force a retry on.
        A retry is initiated if the request method is in ``allowed_methods``
        and the response status code is in ``status_forcelist``.

        By default, this is disabled with ``None``.

    :param float backoff_factor:
        A backoff factor to apply between attempts after the second try
        (most errors are resolved immediately by a second try without a
        delay). urllib3 will sleep for::

            {backoff factor} * (2 ** ({number of total retries} - 1))

        seconds. If the backoff_factor is 0.1, then :func:`.sleep` will sleep
        for [0.0s, 0.2s, 0.4s, ...] between retries. It will never be longer
        than :attr:`Retry.DEFAULT_BACKOFF_MAX`.

        By default, backoff is disabled (set to 0).

    :param bool raise_on_redirect: Whether, if the number of redirects is
        exhausted, to raise a MaxRetryError, or to return a response with a
        response code in the 3xx range.

    :param bool raise_on_status: Similar meaning to ``raise_on_redirect``:
        whether we should raise an exception, or return a response,
        if status falls in ``status_forcelist`` range and retries have
        been exhausted.

    :param tuple history: The history of the request encountered during
        each call to :meth:`~Retry.increment`. The list is in the order
        the requests occurred. Each list item is of class :class:`RequestHistory`.

    :param bool respect_retry_after_header:
        Whether to respect Retry-After header on status codes defined as
        :attr:`Retry.RETRY_AFTER_STATUS_CODES` or not.

    :param iterable remove_headers_on_redirect:
        Sequence of headers to remove from the request when a response
        indicating a redirect is returned before firing off the redirected
        request.
    """

    #: Default methods to be used for ``allowed_methods``
    DEFAULT_ALLOWED_METHODS = frozenset(
        ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )

    #: Default status codes to be used for ``status_forcelist``
    RETRY_AFTER_STATUS_CODES = frozenset([413, 429, 503])

    #: Default headers to be used for ``remove_headers_on_redirect``
    DEFAULT_REMOVE_HEADERS_ON_REDIRECT = frozenset(
        ["Cookie", "Authorization", "Proxy-Authorization"]
    )

    #: Maximum backoff time.
    DEFAULT_BACKOFF_MAX = 120

    def __init__(
        self,
        total=10,
        connect=None,
        read=None,
        redirect=None,
        status=None,
        other=None,
        allowed_methods=_Default,
        status_forcelist=None,
        backoff_factor=0,
        raise_on_redirect=True,
        raise_on_status=True,
        history=None,
        respect_retry_after_header=True,
        remove_headers_on_redirect=_Default,
        # TODO: Deprecated, remove in v2.0
        method_whitelist=_Default,
    ):

        if method_whitelist is not _Default:
            if allowed_methods is not _Default:
                raise ValueError(
                    "Using both 'allowed_methods' and "
                    "'method_whitelist' together is not allowed. "
                    "Instead only use 'allowed_methods'"
                )
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
                stacklevel=2,
            )
            allowed_methods = method_whitelist
        if allowed_methods is _Default:
            allowed_methods = self.DEFAULT_ALLOWED_METHODS
        if remove_headers_on_redirect is _Default:
            remove_headers_on_redirect = self.DEFAULT_REMOVE_HEADERS_ON_REDIRECT

        self.total = total
        self.connect = connect
        self.read = read
        self.status = status
        self.other = other

        if redirect is False or total is False:
            redirect = 0
            raise_on_redirect = False

        self.redirect = redirect
        self.status_forcelist = status_forcelist or set()
        self.allowed_methods = allowed_methods
        self.backoff_factor = backoff_factor
        self.raise_on_redirect = raise_on_redirect
        self.raise_on_status = raise_on_status
        self.history = history or tuple()
        self.respect_retry_after_header = respect_retry_after_header
        self.remove_headers_on_redirect = frozenset(
            [h.lower() for h in remove_headers_on_redirect]
        )

    def new(self, **kw):
        params = dict(
            total=self.total,
            connect=self.connect,
            read=self.read,
            redirect=self.redirect,
            status=self.status,
            other=self.other,
            status_forcelist=self.status_forcelist,
            backoff_factor=self.backoff_factor,
            raise_on_redirect=self.raise_on_redirect,
            raise_on_status=self.raise_on_status,
            history=self.history,
            remove_headers_on_redirect=self.remove_headers_on_redirect,
            respect_retry_after_header=self.respect_retry_after_header,
        )

        # TODO: If already given in **kw we use what's given to us
        # If not given we need to figure out what to pass. We decide
        # based on whether our class has the 'method_whitelist' property
        # and if so we pass the deprecated 'method_whitelist' otherwise
        # we use 'allowed_methods'. Remove in v2.0
        if "method_whitelist" not in kw and "allowed_methods" not in kw:
            if "method_whitelist" in self.__dict__:
                warnings.warn(
                    "Using 'method_whitelist' with Retry is deprecated and "
                    "will be removed in v2.0. Use 'allowed_methods' instead",
                    DeprecationWarning,
                )
                params["method_whitelist"] = self.allowed_methods
            else:
                params["allowed_methods"] = self.allowed_methods

        params.update(kw)
        return type(self)(**params)

    @classmethod
    def from_int(cls, retries, redirect=True, default=None):
        """Backwards-compatibility for the old retries format."""
        if retries is None:
            retries = default if default is not None else cls.DEFAULT

        if isinstance(retries, Retry):
            return retries

        redirect = bool(redirect) and None
        new_retries = cls(retries, redirect=redirect)
        log.debug("Converted retries value: %r -> %r", retries, new_retries)
        return new_retries

    def get_backoff_time(self):
        """Formula for computing the current backoff

        :rtype: float
        """
        # We want to consider only the last consecutive errors sequence (Ignore redirects).
        consecutive_errors_len = len(
            list(
                takewhile(lambda x: x.redirect_location is None, reversed(self.history))
            )
        )
        if consecutive_errors_len <= 1:
            return 0

        backoff_value = self.backoff_factor * (2 ** (consecutive_errors_len - 1))
        return min(self.DEFAULT_BACKOFF_MAX, backoff_value)

    def parse_retry_after(self, retry_after):
        # Whitespace: https://tools.ietf.org/html/rfc7230#section-3.2.4
        if re.match(r"^\s*[0-9]+\s*$", retry_after):
            seconds = int(retry_after)
        else:
            retry_date_tuple = email.utils.parsedate_tz(retry_after)
            if retry_date_tuple is None:
                raise InvalidHeader("Invalid Retry-After header: %s" % retry_after)
            if retry_date_tuple[9] is None:  # Python 2
                # Assume UTC if no timezone was specified
                # On Python2.7, parsedate_tz returns None for a timezone offset
                # instead of 0 if no timezone is given, where mktime_tz treats
                # a None timezone offset as local time.
                retry_date_tuple = retry_date_tuple[:9] + (0,) + retry_date_tuple[10:]

            retry_date = email.utils.mktime_tz(retry_date_tuple)
            seconds = retry_date - time.time()

        if seconds < 0:
            seconds = 0

        return seconds

    def get_retry_after(self, response):
        """Get the value of Retry-After in seconds."""

        retry_after = response.headers.get("Retry-After")

        if retry_after is None:
            return None

        return self.parse_retry_after(retry_after)

    def sleep_for_retry(self, response=None):
        retry_after = self.get_retry_after(response)
        if retry_after:
            time.sleep(retry_after)
            return True

        return False

    def _sleep_backoff(self):
        backoff = self.get_backoff_time()
        if backoff <= 0:
            return
        time.sleep(backoff)

    def sleep(self, response=None):
        """Sleep between retry attempts.

        This method will respect a server's ``Retry-After`` response header
        and sleep the duration of the time requested. If that is not present, it
        will use an exponential backoff. By default, the backoff factor is 0 and
        this method will return immediately.
        """

        if self.respect_retry_after_header and response:
            slept = self.sleep_for_retry(response)
            if slept:
                return

        self._sleep_backoff()

    def _is_connection_error(self, err):
        """Errors when we're fairly sure that the server did not receive the
        request, so it should be safe to retry.
        """
        if isinstance(err, ProxyError):
            err = err.original_error
        return isinstance(err, ConnectTimeoutError)

    def _is_read_error(self, err):
        """Errors that occur after the request has been started, so we should
        assume that the server began processing it.
        """
        return isinstance(err, (ReadTimeoutError, ProtocolError))

    def _is_method_retryable(self, method):
        """Checks if a given HTTP method should be retried upon, depending if
        it is included in the allowed_methods
        """
        # TODO: For now favor if the Retry implementation sets its own method_whitelist
        # property outside of our constructor to avoid breaking custom implementations.
        if "method_whitelist" in self.__dict__:
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
            )
            allowed_methods = self.method_whitelist
        else:
            allowed_methods = self.allowed_methods

        if allowed_methods and method.upper() not in allowed_methods:
            return False
        return True

    def is_retry(self, method, status_code, has_retry_after=False):
        """Is this method/status code retryable? (Based on allowlists and control
        variables such as the number of total retries to allow, whether to
        respect the Retry-After header, whether this header is present, and
        whether the returned status code is on the list of status codes to
        be retried upon on the presence of the aforementioned header)
        """
        if not self._is_method_retryable(method):
            return False

        if self.status_forcelist and status_code in self.status_forcelist:
            return True

        return (
            self.total
            and self.respect_retry_after_header
            and has_retry_after
            and (status_code in self.RETRY_AFTER_STATUS_CODES)
        )

    def is_exhausted(self):
        """Are we out of retries?"""
        retry_counts = (
            self.total,
            self.connect,
            self.read,
            self.redirect,
            self.status,
            self.other,
        )
        retry_counts = list(filter(None, retry_counts))
        if not retry_counts:
            return False

        return min(retry_counts) < 0

    def increment(
        self,
        method=None,
        url=None,
        response=None,
        error=None,
        _pool=None,
        _stacktrace=None,
    ):
        """Return a new Retry object with incremented retry counters.

        :param response: A response object, or None, if the server did not
            return a response.
        :type response: :class:`~urllib3.response.HTTPResponse`
        :param Exception error: An error encountered during the request, or
            None if the response was received successfully.

        :return: A new ``Retry`` object.
        """
        if self.total is False and error:
            # Disabled, indicate to re-raise the error.
            raise six.reraise(type(error), error, _stacktrace)

        total = self.total
        if total is not None:
            total -= 1

        connect = self.connect
        read = self.read
        redirect = self.redirect
        status_count = self.status
        other = self.other
        cause = "unknown"
        status = None
        redirect_location = None

        if error and self._is_connection_error(error):
            # Connect retry?
            if connect is False:
                raise six.reraise(type(error), error, _stacktrace)
            elif connect is not None:
                connect -= 1

        elif error and self._is_read_error(error):
            # Read retry?
            if read is False or not self._is_method_retryable(method):
                raise six.reraise(type(error), error, _stacktrace)
            elif read is not None:
                read -= 1

        elif error:
            # Other retry?
            if other is not None:
                other -= 1

        elif response and response.get_redirect_location():
            # Redirect retry?
            if redirect is not None:
                redirect -= 1
            cause = "too many redirects"
            redirect_location = response.get_redirect_location()
            status = response.status

        else:
            # Incrementing because of a server error like a 500 in
            # status_forcelist and the given method is in the allowed_methods
            cause = ResponseError.GENERIC_ERROR
            if response and response.status:
                if status_count is not None:
                    status_count -= 1
                cause = ResponseError.SPECIFIC_ERROR.format(status_code=response.status)
                status = response.status

        history = self.history + (
            RequestHistory(method, url, error, status, redirect_location),
        )

        new_retry = self.new(
            total=total,
            connect=connect,
            read=read,
            redirect=redirect,
            status=status_count,
            other=other,
            history=history,
        )

        if new_retry.is_exhausted():
            raise MaxRetryError(_pool, url, error or ResponseError(cause))

        log.debug("Incremented Retry for (url='%s'): %r", url, new_retry)

        return new_retry

    def __repr__(self):
        return (
            "{cls.__name__}(total={self.total}, connect={self.connect}, "
            "read={self.read}, redirect={self.redirect}, status={self.status})"
        ).format(cls=type(self), self=self)

    def __getattr__(self, item):
        if item == "method_whitelist":
            # TODO: Remove this deprecated alias in v2.0
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
            )
            return self.allowed_methods
        try:
            return getattr(super(Retry, self), item)
        except AttributeError:
            return getattr(Retry, item)


# For backwards compatibility (equivalent to pre-v1.9):
Retry.DEFAULT = Retry(3)

# === NexusCore/openenv\Lib\site-packages\click\_compat.py ===
from __future__ import annotations

import codecs
import collections.abc as cabc
import io
import os
import re
import sys
import typing as t
from types import TracebackType
from weakref import WeakKeyDictionary

CYGWIN = sys.platform.startswith("cygwin")
WIN = sys.platform.startswith("win")
auto_wrap_for_ansi: t.Callable[[t.TextIO], t.TextIO] | None = None
_ansi_re = re.compile(r"\033\[[;?0-9]*[a-zA-Z]")


def _make_text_stream(
    stream: t.BinaryIO,
    encoding: str | None,
    errors: str | None,
    force_readable: bool = False,
    force_writable: bool = False,
) -> t.TextIO:
    if encoding is None:
        encoding = get_best_encoding(stream)
    if errors is None:
        errors = "replace"
    return _NonClosingTextIOWrapper(
        stream,
        encoding,
        errors,
        line_buffering=True,
        force_readable=force_readable,
        force_writable=force_writable,
    )


def is_ascii_encoding(encoding: str) -> bool:
    """Checks if a given encoding is ascii."""
    try:
        return codecs.lookup(encoding).name == "ascii"
    except LookupError:
        return False


def get_best_encoding(stream: t.IO[t.Any]) -> str:
    """Returns the default stream encoding if not found."""
    rv = getattr(stream, "encoding", None) or sys.getdefaultencoding()
    if is_ascii_encoding(rv):
        return "utf-8"
    return rv


class _NonClosingTextIOWrapper(io.TextIOWrapper):
    def __init__(
        self,
        stream: t.BinaryIO,
        encoding: str | None,
        errors: str | None,
        force_readable: bool = False,
        force_writable: bool = False,
        **extra: t.Any,
    ) -> None:
        self._stream = stream = t.cast(
            t.BinaryIO, _FixupStream(stream, force_readable, force_writable)
        )
        super().__init__(stream, encoding, errors, **extra)

    def __del__(self) -> None:
        try:
            self.detach()
        except Exception:
            pass

    def isatty(self) -> bool:
        # https://bitbucket.org/pypy/pypy/issue/1803
        return self._stream.isatty()


class _FixupStream:
    """The new io interface needs more from streams than streams
    traditionally implement.  As such, this fix-up code is necessary in
    some circumstances.

    The forcing of readable and writable flags are there because some tools
    put badly patched objects on sys (one such offender are certain version
    of jupyter notebook).
    """

    def __init__(
        self,
        stream: t.BinaryIO,
        force_readable: bool = False,
        force_writable: bool = False,
    ):
        self._stream = stream
        self._force_readable = force_readable
        self._force_writable = force_writable

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._stream, name)

    def read1(self, size: int) -> bytes:
        f = getattr(self._stream, "read1", None)

        if f is not None:
            return t.cast(bytes, f(size))

        return self._stream.read(size)

    def readable(self) -> bool:
        if self._force_readable:
            return True
        x = getattr(self._stream, "readable", None)
        if x is not None:
            return t.cast(bool, x())
        try:
            self._stream.read(0)
        except Exception:
            return False
        return True

    def writable(self) -> bool:
        if self._force_writable:
            return True
        x = getattr(self._stream, "writable", None)
        if x is not None:
            return t.cast(bool, x())
        try:
            self._stream.write(b"")
        except Exception:
            try:
                self._stream.write(b"")
            except Exception:
                return False
        return True

    def seekable(self) -> bool:
        x = getattr(self._stream, "seekable", None)
        if x is not None:
            return t.cast(bool, x())
        try:
            self._stream.seek(self._stream.tell())
        except Exception:
            return False
        return True


def _is_binary_reader(stream: t.IO[t.Any], default: bool = False) -> bool:
    try:
        return isinstance(stream.read(0), bytes)
    except Exception:
        return default
        # This happens in some cases where the stream was already
        # closed.  In this case, we assume the default.


def _is_binary_writer(stream: t.IO[t.Any], default: bool = False) -> bool:
    try:
        stream.write(b"")
    except Exception:
        try:
            stream.write("")
            return False
        except Exception:
            pass
        return default
    return True


def _find_binary_reader(stream: t.IO[t.Any]) -> t.BinaryIO | None:
    # We need to figure out if the given stream is already binary.
    # This can happen because the official docs recommend detaching
    # the streams to get binary streams.  Some code might do this, so
    # we need to deal with this case explicitly.
    if _is_binary_reader(stream, False):
        return t.cast(t.BinaryIO, stream)

    buf = getattr(stream, "buffer", None)

    # Same situation here; this time we assume that the buffer is
    # actually binary in case it's closed.
    if buf is not None and _is_binary_reader(buf, True):
        return t.cast(t.BinaryIO, buf)

    return None


def _find_binary_writer(stream: t.IO[t.Any]) -> t.BinaryIO | None:
    # We need to figure out if the given stream is already binary.
    # This can happen because the official docs recommend detaching
    # the streams to get binary streams.  Some code might do this, so
    # we need to deal with this case explicitly.
    if _is_binary_writer(stream, False):
        return t.cast(t.BinaryIO, stream)

    buf = getattr(stream, "buffer", None)

    # Same situation here; this time we assume that the buffer is
    # actually binary in case it's closed.
    if buf is not None and _is_binary_writer(buf, True):
        return t.cast(t.BinaryIO, buf)

    return None


def _stream_is_misconfigured(stream: t.TextIO) -> bool:
    """A stream is misconfigured if its encoding is ASCII."""
    # If the stream does not have an encoding set, we assume it's set
    # to ASCII.  This appears to happen in certain unittest
    # environments.  It's not quite clear what the correct behavior is
    # but this at least will force Click to recover somehow.
    return is_ascii_encoding(getattr(stream, "encoding", None) or "ascii")


def _is_compat_stream_attr(stream: t.TextIO, attr: str, value: str | None) -> bool:
    """A stream attribute is compatible if it is equal to the
    desired value or the desired value is unset and the attribute
    has a value.
    """
    stream_value = getattr(stream, attr, None)
    return stream_value == value or (value is None and stream_value is not None)


def _is_compatible_text_stream(
    stream: t.TextIO, encoding: str | None, errors: str | None
) -> bool:
    """Check if a stream's encoding and errors attributes are
    compatible with the desired values.
    """
    return _is_compat_stream_attr(
        stream, "encoding", encoding
    ) and _is_compat_stream_attr(stream, "errors", errors)


def _force_correct_text_stream(
    text_stream: t.IO[t.Any],
    encoding: str | None,
    errors: str | None,
    is_binary: t.Callable[[t.IO[t.Any], bool], bool],
    find_binary: t.Callable[[t.IO[t.Any]], t.BinaryIO | None],
    force_readable: bool = False,
    force_writable: bool = False,
) -> t.TextIO:
    if is_binary(text_stream, False):
        binary_reader = t.cast(t.BinaryIO, text_stream)
    else:
        text_stream = t.cast(t.TextIO, text_stream)
        # If the stream looks compatible, and won't default to a
        # misconfigured ascii encoding, return it as-is.
        if _is_compatible_text_stream(text_stream, encoding, errors) and not (
            encoding is None and _stream_is_misconfigured(text_stream)
        ):
            return text_stream

        # Otherwise, get the underlying binary reader.
        possible_binary_reader = find_binary(text_stream)

        # If that's not possible, silently use the original reader
        # and get mojibake instead of exceptions.
        if possible_binary_reader is None:
            return text_stream

        binary_reader = possible_binary_reader

    # Default errors to replace instead of strict in order to get
    # something that works.
    if errors is None:
        errors = "replace"

    # Wrap the binary stream in a text stream with the correct
    # encoding parameters.
    return _make_text_stream(
        binary_reader,
        encoding,
        errors,
        force_readable=force_readable,
        force_writable=force_writable,
    )


def _force_correct_text_reader(
    text_reader: t.IO[t.Any],
    encoding: str | None,
    errors: str | None,
    force_readable: bool = False,
) -> t.TextIO:
    return _force_correct_text_stream(
        text_reader,
        encoding,
        errors,
        _is_binary_reader,
        _find_binary_reader,
        force_readable=force_readable,
    )


def _force_correct_text_writer(
    text_writer: t.IO[t.Any],
    encoding: str | None,
    errors: str | None,
    force_writable: bool = False,
) -> t.TextIO:
    return _force_correct_text_stream(
        text_writer,
        encoding,
        errors,
        _is_binary_writer,
        _find_binary_writer,
        force_writable=force_writable,
    )


def get_binary_stdin() -> t.BinaryIO:
    reader = _find_binary_reader(sys.stdin)
    if reader is None:
        raise RuntimeError("Was not able to determine binary stream for sys.stdin.")
    return reader


def get_binary_stdout() -> t.BinaryIO:
    writer = _find_binary_writer(sys.stdout)
    if writer is None:
        raise RuntimeError("Was not able to determine binary stream for sys.stdout.")
    return writer


def get_binary_stderr() -> t.BinaryIO:
    writer = _find_binary_writer(sys.stderr)
    if writer is None:
        raise RuntimeError("Was not able to determine binary stream for sys.stderr.")
    return writer


def get_text_stdin(encoding: str | None = None, errors: str | None = None) -> t.TextIO:
    rv = _get_windows_console_stream(sys.stdin, encoding, errors)
    if rv is not None:
        return rv
    return _force_correct_text_reader(sys.stdin, encoding, errors, force_readable=True)


def get_text_stdout(encoding: str | None = None, errors: str | None = None) -> t.TextIO:
    rv = _get_windows_console_stream(sys.stdout, encoding, errors)
    if rv is not None:
        return rv
    return _force_correct_text_writer(sys.stdout, encoding, errors, force_writable=True)


def get_text_stderr(encoding: str | None = None, errors: str | None = None) -> t.TextIO:
    rv = _get_windows_console_stream(sys.stderr, encoding, errors)
    if rv is not None:
        return rv
    return _force_correct_text_writer(sys.stderr, encoding, errors, force_writable=True)


def _wrap_io_open(
    file: str | os.PathLike[str] | int,
    mode: str,
    encoding: str | None,
    errors: str | None,
) -> t.IO[t.Any]:
    """Handles not passing ``encoding`` and ``errors`` in binary mode."""
    if "b" in mode:
        return open(file, mode)

    return open(file, mode, encoding=encoding, errors=errors)


def open_stream(
    filename: str | os.PathLike[str],
    mode: str = "r",
    encoding: str | None = None,
    errors: str | None = "strict",
    atomic: bool = False,
) -> tuple[t.IO[t.Any], bool]:
    binary = "b" in mode
    filename = os.fspath(filename)

    # Standard streams first. These are simple because they ignore the
    # atomic flag. Use fsdecode to handle Path("-").
    if os.fsdecode(filename) == "-":
        if any(m in mode for m in ["w", "a", "x"]):
            if binary:
                return get_binary_stdout(), False
            return get_text_stdout(encoding=encoding, errors=errors), False
        if binary:
            return get_binary_stdin(), False
        return get_text_stdin(encoding=encoding, errors=errors), False

    # Non-atomic writes directly go out through the regular open functions.
    if not atomic:
        return _wrap_io_open(filename, mode, encoding, errors), True

    # Some usability stuff for atomic writes
    if "a" in mode:
        raise ValueError(
            "Appending to an existing file is not supported, because that"
            " would involve an expensive `copy`-operation to a temporary"
            " file. Open the file in normal `w`-mode and copy explicitly"
            " if that's what you're after."
        )
    if "x" in mode:
        raise ValueError("Use the `overwrite`-parameter instead.")
    if "w" not in mode:
        raise ValueError("Atomic writes only make sense with `w`-mode.")

    # Atomic writes are more complicated.  They work by opening a file
    # as a proxy in the same folder and then using the fdopen
    # functionality to wrap it in a Python file.  Then we wrap it in an
    # atomic file that moves the file over on close.
    import errno
    import random

    try:
        perm: int | None = os.stat(filename).st_mode
    except OSError:
        perm = None

    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL

    if binary:
        flags |= getattr(os, "O_BINARY", 0)

    while True:
        tmp_filename = os.path.join(
            os.path.dirname(filename),
            f".__atomic-write{random.randrange(1 << 32):08x}",
        )
        try:
            fd = os.open(tmp_filename, flags, 0o666 if perm is None else perm)
            break
        except OSError as e:
            if e.errno == errno.EEXIST or (
                os.name == "nt"
                and e.errno == errno.EACCES
                and os.path.isdir(e.filename)
                and os.access(e.filename, os.W_OK)
            ):
                continue
            raise

    if perm is not None:
        os.chmod(tmp_filename, perm)  # in case perm includes bits in umask

    f = _wrap_io_open(fd, mode, encoding, errors)
    af = _AtomicFile(f, tmp_filename, os.path.realpath(filename))
    return t.cast(t.IO[t.Any], af), True


class _AtomicFile:
    def __init__(self, f: t.IO[t.Any], tmp_filename: str, real_filename: str) -> None:
        self._f = f
        self._tmp_filename = tmp_filename
        self._real_filename = real_filename
        self.closed = False

    @property
    def name(self) -> str:
        return self._real_filename

    def close(self, delete: bool = False) -> None:
        if self.closed:
            return
        self._f.close()
        os.replace(self._tmp_filename, self._real_filename)
        self.closed = True

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._f, name)

    def __enter__(self) -> _AtomicFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close(delete=exc_type is not None)

    def __repr__(self) -> str:
        return repr(self._f)


def strip_ansi(value: str) -> str:
    return _ansi_re.sub("", value)


def _is_jupyter_kernel_output(stream: t.IO[t.Any]) -> bool:
    while isinstance(stream, (_FixupStream, _NonClosingTextIOWrapper)):
        stream = stream._stream

    return stream.__class__.__module__.startswith("ipykernel.")


def should_strip_ansi(
    stream: t.IO[t.Any] | None = None, color: bool | None = None
) -> bool:
    if color is None:
        if stream is None:
            stream = sys.stdin
        return not isatty(stream) and not _is_jupyter_kernel_output(stream)
    return not color


# On Windows, wrap the output streams with colorama to support ANSI
# color codes.
# NOTE: double check is needed so mypy does not analyze this on Linux
if sys.platform.startswith("win") and WIN:
    from ._winconsole import _get_windows_console_stream

    def _get_argv_encoding() -> str:
        import locale

        return locale.getpreferredencoding()

    _ansi_stream_wrappers: cabc.MutableMapping[t.TextIO, t.TextIO] = WeakKeyDictionary()

    def auto_wrap_for_ansi(stream: t.TextIO, color: bool | None = None) -> t.TextIO:
        """Support ANSI color and style codes on Windows by wrapping a
        stream with colorama.
        """
        try:
            cached = _ansi_stream_wrappers.get(stream)
        except Exception:
            cached = None

        if cached is not None:
            return cached

        import colorama

        strip = should_strip_ansi(stream, color)
        ansi_wrapper = colorama.AnsiToWin32(stream, strip=strip)
        rv = t.cast(t.TextIO, ansi_wrapper.stream)
        _write = rv.write

        def _safe_write(s: str) -> int:
            try:
                return _write(s)
            except BaseException:
                ansi_wrapper.reset_all()
                raise

        rv.write = _safe_write  # type: ignore[method-assign]

        try:
            _ansi_stream_wrappers[stream] = rv
        except Exception:
            pass

        return rv

else:

    def _get_argv_encoding() -> str:
        return getattr(sys.stdin, "encoding", None) or sys.getfilesystemencoding()

    def _get_windows_console_stream(
        f: t.TextIO, encoding: str | None, errors: str | None
    ) -> t.TextIO | None:
        return None


def term_len(x: str) -> int:
    return len(strip_ansi(x))


def isatty(stream: t.IO[t.Any]) -> bool:
    try:
        return stream.isatty()
    except Exception:
        return False


def _make_cached_stream_func(
    src_func: t.Callable[[], t.TextIO | None],
    wrapper_func: t.Callable[[], t.TextIO],
) -> t.Callable[[], t.TextIO | None]:
    cache: cabc.MutableMapping[t.TextIO, t.TextIO] = WeakKeyDictionary()

    def func() -> t.TextIO | None:
        stream = src_func()

        if stream is None:
            return None

        try:
            rv = cache.get(stream)
        except Exception:
            rv = None
        if rv is not None:
            return rv
        rv = wrapper_func()
        try:
            cache[stream] = rv
        except Exception:
            pass
        return rv

    return func


_default_text_stdin = _make_cached_stream_func(lambda: sys.stdin, get_text_stdin)
_default_text_stdout = _make_cached_stream_func(lambda: sys.stdout, get_text_stdout)
_default_text_stderr = _make_cached_stream_func(lambda: sys.stderr, get_text_stderr)


binary_streams: cabc.Mapping[str, t.Callable[[], t.BinaryIO]] = {
    "stdin": get_binary_stdin,
    "stdout": get_binary_stdout,
    "stderr": get_binary_stderr,
}

text_streams: cabc.Mapping[str, t.Callable[[str | None, str | None], t.TextIO]] = {
    "stdin": get_text_stdin,
    "stdout": get_text_stdout,
    "stderr": get_text_stderr,
}

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\retry.py ===
from __future__ import absolute_import

import email
import logging
import re
import time
import warnings
from collections import namedtuple
from itertools import takewhile

from ..exceptions import (
    ConnectTimeoutError,
    InvalidHeader,
    MaxRetryError,
    ProtocolError,
    ProxyError,
    ReadTimeoutError,
    ResponseError,
)
from ..packages import six

log = logging.getLogger(__name__)


# Data structure for representing the metadata of requests that result in a retry.
RequestHistory = namedtuple(
    "RequestHistory", ["method", "url", "error", "status", "redirect_location"]
)


# TODO: In v2 we can remove this sentinel and metaclass with deprecated options.
_Default = object()


class _RetryMeta(type):
    @property
    def DEFAULT_METHOD_WHITELIST(cls):
        warnings.warn(
            "Using 'Retry.DEFAULT_METHOD_WHITELIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_ALLOWED_METHODS' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_ALLOWED_METHODS

    @DEFAULT_METHOD_WHITELIST.setter
    def DEFAULT_METHOD_WHITELIST(cls, value):
        warnings.warn(
            "Using 'Retry.DEFAULT_METHOD_WHITELIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_ALLOWED_METHODS' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_ALLOWED_METHODS = value

    @property
    def DEFAULT_REDIRECT_HEADERS_BLACKLIST(cls):
        warnings.warn(
            "Using 'Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_REMOVE_HEADERS_ON_REDIRECT' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_REMOVE_HEADERS_ON_REDIRECT

    @DEFAULT_REDIRECT_HEADERS_BLACKLIST.setter
    def DEFAULT_REDIRECT_HEADERS_BLACKLIST(cls, value):
        warnings.warn(
            "Using 'Retry.DEFAULT_REDIRECT_HEADERS_BLACKLIST' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_REMOVE_HEADERS_ON_REDIRECT' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_REMOVE_HEADERS_ON_REDIRECT = value

    @property
    def BACKOFF_MAX(cls):
        warnings.warn(
            "Using 'Retry.BACKOFF_MAX' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_BACKOFF_MAX' instead",
            DeprecationWarning,
        )
        return cls.DEFAULT_BACKOFF_MAX

    @BACKOFF_MAX.setter
    def BACKOFF_MAX(cls, value):
        warnings.warn(
            "Using 'Retry.BACKOFF_MAX' is deprecated and "
            "will be removed in v2.0. Use 'Retry.DEFAULT_BACKOFF_MAX' instead",
            DeprecationWarning,
        )
        cls.DEFAULT_BACKOFF_MAX = value


@six.add_metaclass(_RetryMeta)
class Retry(object):
    """Retry configuration.

    Each retry attempt will create a new Retry object with updated values, so
    they can be safely reused.

    Retries can be defined as a default for a pool::

        retries = Retry(connect=5, read=2, redirect=5)
        http = PoolManager(retries=retries)
        response = http.request('GET', 'http://example.com/')

    Or per-request (which overrides the default for the pool)::

        response = http.request('GET', 'http://example.com/', retries=Retry(10))

    Retries can be disabled by passing ``False``::

        response = http.request('GET', 'http://example.com/', retries=False)

    Errors will be wrapped in :class:`~urllib3.exceptions.MaxRetryError` unless
    retries are disabled, in which case the causing exception will be raised.

    :param int total:
        Total number of retries to allow. Takes precedence over other counts.

        Set to ``None`` to remove this constraint and fall back on other
        counts.

        Set to ``0`` to fail on the first retry.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int connect:
        How many connection-related errors to retry on.

        These are errors raised before the request is sent to the remote server,
        which we assume has not triggered the server to process the request.

        Set to ``0`` to fail on the first retry of this type.

    :param int read:
        How many times to retry on read errors.

        These errors are raised after the request was sent to the server, so the
        request may have side-effects.

        Set to ``0`` to fail on the first retry of this type.

    :param int redirect:
        How many redirects to perform. Limit this to avoid infinite redirect
        loops.

        A redirect is a HTTP response with a status code 301, 302, 303, 307 or
        308.

        Set to ``0`` to fail on the first retry of this type.

        Set to ``False`` to disable and imply ``raise_on_redirect=False``.

    :param int status:
        How many times to retry on bad status codes.

        These are retries made on responses, where status code matches
        ``status_forcelist``.

        Set to ``0`` to fail on the first retry of this type.

    :param int other:
        How many times to retry on other errors.

        Other errors are errors that are not connect, read, redirect or status errors.
        These errors might be raised after the request was sent to the server, so the
        request might have side-effects.

        Set to ``0`` to fail on the first retry of this type.

        If ``total`` is not set, it's a good idea to set this to 0 to account
        for unexpected edge cases and avoid infinite retry loops.

    :param iterable allowed_methods:
        Set of uppercased HTTP method verbs that we should retry on.

        By default, we only retry on methods which are considered to be
        idempotent (multiple requests with the same parameters end with the
        same state). See :attr:`Retry.DEFAULT_ALLOWED_METHODS`.

        Set to a ``False`` value to retry on any verb.

        .. warning::

            Previously this parameter was named ``method_whitelist``, that
            usage is deprecated in v1.26.0 and will be removed in v2.0.

    :param iterable status_forcelist:
        A set of integer HTTP status codes that we should force a retry on.
        A retry is initiated if the request method is in ``allowed_methods``
        and the response status code is in ``status_forcelist``.

        By default, this is disabled with ``None``.

    :param float backoff_factor:
        A backoff factor to apply between attempts after the second try
        (most errors are resolved immediately by a second try without a
        delay). urllib3 will sleep for::

            {backoff factor} * (2 ** ({number of total retries} - 1))

        seconds. If the backoff_factor is 0.1, then :func:`.sleep` will sleep
        for [0.0s, 0.2s, 0.4s, ...] between retries. It will never be longer
        than :attr:`Retry.DEFAULT_BACKOFF_MAX`.

        By default, backoff is disabled (set to 0).

    :param bool raise_on_redirect: Whether, if the number of redirects is
        exhausted, to raise a MaxRetryError, or to return a response with a
        response code in the 3xx range.

    :param bool raise_on_status: Similar meaning to ``raise_on_redirect``:
        whether we should raise an exception, or return a response,
        if status falls in ``status_forcelist`` range and retries have
        been exhausted.

    :param tuple history: The history of the request encountered during
        each call to :meth:`~Retry.increment`. The list is in the order
        the requests occurred. Each list item is of class :class:`RequestHistory`.

    :param bool respect_retry_after_header:
        Whether to respect Retry-After header on status codes defined as
        :attr:`Retry.RETRY_AFTER_STATUS_CODES` or not.

    :param iterable remove_headers_on_redirect:
        Sequence of headers to remove from the request when a response
        indicating a redirect is returned before firing off the redirected
        request.
    """

    #: Default methods to be used for ``allowed_methods``
    DEFAULT_ALLOWED_METHODS = frozenset(
        ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )

    #: Default status codes to be used for ``status_forcelist``
    RETRY_AFTER_STATUS_CODES = frozenset([413, 429, 503])

    #: Default headers to be used for ``remove_headers_on_redirect``
    DEFAULT_REMOVE_HEADERS_ON_REDIRECT = frozenset(
        ["Cookie", "Authorization", "Proxy-Authorization"]
    )

    #: Maximum backoff time.
    DEFAULT_BACKOFF_MAX = 120

    def __init__(
        self,
        total=10,
        connect=None,
        read=None,
        redirect=None,
        status=None,
        other=None,
        allowed_methods=_Default,
        status_forcelist=None,
        backoff_factor=0,
        raise_on_redirect=True,
        raise_on_status=True,
        history=None,
        respect_retry_after_header=True,
        remove_headers_on_redirect=_Default,
        # TODO: Deprecated, remove in v2.0
        method_whitelist=_Default,
    ):

        if method_whitelist is not _Default:
            if allowed_methods is not _Default:
                raise ValueError(
                    "Using both 'allowed_methods' and "
                    "'method_whitelist' together is not allowed. "
                    "Instead only use 'allowed_methods'"
                )
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
                stacklevel=2,
            )
            allowed_methods = method_whitelist
        if allowed_methods is _Default:
            allowed_methods = self.DEFAULT_ALLOWED_METHODS
        if remove_headers_on_redirect is _Default:
            remove_headers_on_redirect = self.DEFAULT_REMOVE_HEADERS_ON_REDIRECT

        self.total = total
        self.connect = connect
        self.read = read
        self.status = status
        self.other = other

        if redirect is False or total is False:
            redirect = 0
            raise_on_redirect = False

        self.redirect = redirect
        self.status_forcelist = status_forcelist or set()
        self.allowed_methods = allowed_methods
        self.backoff_factor = backoff_factor
        self.raise_on_redirect = raise_on_redirect
        self.raise_on_status = raise_on_status
        self.history = history or tuple()
        self.respect_retry_after_header = respect_retry_after_header
        self.remove_headers_on_redirect = frozenset(
            [h.lower() for h in remove_headers_on_redirect]
        )

    def new(self, **kw):
        params = dict(
            total=self.total,
            connect=self.connect,
            read=self.read,
            redirect=self.redirect,
            status=self.status,
            other=self.other,
            status_forcelist=self.status_forcelist,
            backoff_factor=self.backoff_factor,
            raise_on_redirect=self.raise_on_redirect,
            raise_on_status=self.raise_on_status,
            history=self.history,
            remove_headers_on_redirect=self.remove_headers_on_redirect,
            respect_retry_after_header=self.respect_retry_after_header,
        )

        # TODO: If already given in **kw we use what's given to us
        # If not given we need to figure out what to pass. We decide
        # based on whether our class has the 'method_whitelist' property
        # and if so we pass the deprecated 'method_whitelist' otherwise
        # we use 'allowed_methods'. Remove in v2.0
        if "method_whitelist" not in kw and "allowed_methods" not in kw:
            if "method_whitelist" in self.__dict__:
                warnings.warn(
                    "Using 'method_whitelist' with Retry is deprecated and "
                    "will be removed in v2.0. Use 'allowed_methods' instead",
                    DeprecationWarning,
                )
                params["method_whitelist"] = self.allowed_methods
            else:
                params["allowed_methods"] = self.allowed_methods

        params.update(kw)
        return type(self)(**params)

    @classmethod
    def from_int(cls, retries, redirect=True, default=None):
        """Backwards-compatibility for the old retries format."""
        if retries is None:
            retries = default if default is not None else cls.DEFAULT

        if isinstance(retries, Retry):
            return retries

        redirect = bool(redirect) and None
        new_retries = cls(retries, redirect=redirect)
        log.debug("Converted retries value: %r -> %r", retries, new_retries)
        return new_retries

    def get_backoff_time(self):
        """Formula for computing the current backoff

        :rtype: float
        """
        # We want to consider only the last consecutive errors sequence (Ignore redirects).
        consecutive_errors_len = len(
            list(
                takewhile(lambda x: x.redirect_location is None, reversed(self.history))
            )
        )
        if consecutive_errors_len <= 1:
            return 0

        backoff_value = self.backoff_factor * (2 ** (consecutive_errors_len - 1))
        return min(self.DEFAULT_BACKOFF_MAX, backoff_value)

    def parse_retry_after(self, retry_after):
        # Whitespace: https://tools.ietf.org/html/rfc7230#section-3.2.4
        if re.match(r"^\s*[0-9]+\s*$", retry_after):
            seconds = int(retry_after)
        else:
            retry_date_tuple = email.utils.parsedate_tz(retry_after)
            if retry_date_tuple is None:
                raise InvalidHeader("Invalid Retry-After header: %s" % retry_after)
            if retry_date_tuple[9] is None:  # Python 2
                # Assume UTC if no timezone was specified
                # On Python2.7, parsedate_tz returns None for a timezone offset
                # instead of 0 if no timezone is given, where mktime_tz treats
                # a None timezone offset as local time.
                retry_date_tuple = retry_date_tuple[:9] + (0,) + retry_date_tuple[10:]

            retry_date = email.utils.mktime_tz(retry_date_tuple)
            seconds = retry_date - time.time()

        if seconds < 0:
            seconds = 0

        return seconds

    def get_retry_after(self, response):
        """Get the value of Retry-After in seconds."""

        retry_after = response.headers.get("Retry-After")

        if retry_after is None:
            return None

        return self.parse_retry_after(retry_after)

    def sleep_for_retry(self, response=None):
        retry_after = self.get_retry_after(response)
        if retry_after:
            time.sleep(retry_after)
            return True

        return False

    def _sleep_backoff(self):
        backoff = self.get_backoff_time()
        if backoff <= 0:
            return
        time.sleep(backoff)

    def sleep(self, response=None):
        """Sleep between retry attempts.

        This method will respect a server's ``Retry-After`` response header
        and sleep the duration of the time requested. If that is not present, it
        will use an exponential backoff. By default, the backoff factor is 0 and
        this method will return immediately.
        """

        if self.respect_retry_after_header and response:
            slept = self.sleep_for_retry(response)
            if slept:
                return

        self._sleep_backoff()

    def _is_connection_error(self, err):
        """Errors when we're fairly sure that the server did not receive the
        request, so it should be safe to retry.
        """
        if isinstance(err, ProxyError):
            err = err.original_error
        return isinstance(err, ConnectTimeoutError)

    def _is_read_error(self, err):
        """Errors that occur after the request has been started, so we should
        assume that the server began processing it.
        """
        return isinstance(err, (ReadTimeoutError, ProtocolError))

    def _is_method_retryable(self, method):
        """Checks if a given HTTP method should be retried upon, depending if
        it is included in the allowed_methods
        """
        # TODO: For now favor if the Retry implementation sets its own method_whitelist
        # property outside of our constructor to avoid breaking custom implementations.
        if "method_whitelist" in self.__dict__:
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
            )
            allowed_methods = self.method_whitelist
        else:
            allowed_methods = self.allowed_methods

        if allowed_methods and method.upper() not in allowed_methods:
            return False
        return True

    def is_retry(self, method, status_code, has_retry_after=False):
        """Is this method/status code retryable? (Based on allowlists and control
        variables such as the number of total retries to allow, whether to
        respect the Retry-After header, whether this header is present, and
        whether the returned status code is on the list of status codes to
        be retried upon on the presence of the aforementioned header)
        """
        if not self._is_method_retryable(method):
            return False

        if self.status_forcelist and status_code in self.status_forcelist:
            return True

        return (
            self.total
            and self.respect_retry_after_header
            and has_retry_after
            and (status_code in self.RETRY_AFTER_STATUS_CODES)
        )

    def is_exhausted(self):
        """Are we out of retries?"""
        retry_counts = (
            self.total,
            self.connect,
            self.read,
            self.redirect,
            self.status,
            self.other,
        )
        retry_counts = list(filter(None, retry_counts))
        if not retry_counts:
            return False

        return min(retry_counts) < 0

    def increment(
        self,
        method=None,
        url=None,
        response=None,
        error=None,
        _pool=None,
        _stacktrace=None,
    ):
        """Return a new Retry object with incremented retry counters.

        :param response: A response object, or None, if the server did not
            return a response.
        :type response: :class:`~urllib3.response.HTTPResponse`
        :param Exception error: An error encountered during the request, or
            None if the response was received successfully.

        :return: A new ``Retry`` object.
        """
        if self.total is False and error:
            # Disabled, indicate to re-raise the error.
            raise six.reraise(type(error), error, _stacktrace)

        total = self.total
        if total is not None:
            total -= 1

        connect = self.connect
        read = self.read
        redirect = self.redirect
        status_count = self.status
        other = self.other
        cause = "unknown"
        status = None
        redirect_location = None

        if error and self._is_connection_error(error):
            # Connect retry?
            if connect is False:
                raise six.reraise(type(error), error, _stacktrace)
            elif connect is not None:
                connect -= 1

        elif error and self._is_read_error(error):
            # Read retry?
            if read is False or not self._is_method_retryable(method):
                raise six.reraise(type(error), error, _stacktrace)
            elif read is not None:
                read -= 1

        elif error:
            # Other retry?
            if other is not None:
                other -= 1

        elif response and response.get_redirect_location():
            # Redirect retry?
            if redirect is not None:
                redirect -= 1
            cause = "too many redirects"
            redirect_location = response.get_redirect_location()
            status = response.status

        else:
            # Incrementing because of a server error like a 500 in
            # status_forcelist and the given method is in the allowed_methods
            cause = ResponseError.GENERIC_ERROR
            if response and response.status:
                if status_count is not None:
                    status_count -= 1
                cause = ResponseError.SPECIFIC_ERROR.format(status_code=response.status)
                status = response.status

        history = self.history + (
            RequestHistory(method, url, error, status, redirect_location),
        )

        new_retry = self.new(
            total=total,
            connect=connect,
            read=read,
            redirect=redirect,
            status=status_count,
            other=other,
            history=history,
        )

        if new_retry.is_exhausted():
            raise MaxRetryError(_pool, url, error or ResponseError(cause))

        log.debug("Incremented Retry for (url='%s'): %r", url, new_retry)

        return new_retry

    def __repr__(self):
        return (
            "{cls.__name__}(total={self.total}, connect={self.connect}, "
            "read={self.read}, redirect={self.redirect}, status={self.status})"
        ).format(cls=type(self), self=self)

    def __getattr__(self, item):
        if item == "method_whitelist":
            # TODO: Remove this deprecated alias in v2.0
            warnings.warn(
                "Using 'method_whitelist' with Retry is deprecated and "
                "will be removed in v2.0. Use 'allowed_methods' instead",
                DeprecationWarning,
            )
            return self.allowed_methods
        try:
            return getattr(super(Retry, self), item)
        except AttributeError:
            return getattr(Retry, item)


# For backwards compatibility (equivalent to pre-v1.9):
Retry.DEFAULT = Retry(3)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_connection.py ===
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
import collections.abc
import contextvars
import datetime
import inspect
import sys
import traceback
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    TypedDict,
    Union,
    cast,
)

from pyee import EventEmitter
from pyee.asyncio import AsyncIOEventEmitter

import playwright
import playwright._impl._impl_to_api_mapping
from playwright._impl._errors import TargetClosedError, rewrite_error
from playwright._impl._greenlets import EventGreenlet
from playwright._impl._helper import Error, ParsedMessagePayload, parse_error
from playwright._impl._transport import Transport

if TYPE_CHECKING:
    from playwright._impl._local_utils import LocalUtils
    from playwright._impl._playwright import Playwright


class Channel(AsyncIOEventEmitter):
    def __init__(self, connection: "Connection", object: "ChannelOwner") -> None:
        super().__init__()
        self._connection = connection
        self._guid = object._guid
        self._object = object
        self.on("error", lambda exc: self._connection._on_event_listener_error(exc))
        self._is_internal_type = False

    async def send(self, method: str, params: Dict = None) -> Any:
        return await self._connection.wrap_api_call(
            lambda: self._inner_send(method, params, False),
            self._is_internal_type,
        )

    async def send_return_as_dict(self, method: str, params: Dict = None) -> Any:
        return await self._connection.wrap_api_call(
            lambda: self._inner_send(method, params, True),
            self._is_internal_type,
        )

    def send_no_reply(self, method: str, params: Dict = None) -> None:
        # No reply messages are used to e.g. waitForEventInfo(after).
        self._connection.wrap_api_call_sync(
            lambda: self._connection._send_message_to_server(
                self._object, method, {} if params is None else params, True
            )
        )

    async def _inner_send(
        self, method: str, params: Optional[Dict], return_as_dict: bool
    ) -> Any:
        if params is None:
            params = {}
        if self._connection._error:
            error = self._connection._error
            self._connection._error = None
            raise error
        callback = self._connection._send_message_to_server(
            self._object, method, _filter_none(params)
        )
        done, _ = await asyncio.wait(
            {
                self._connection._transport.on_error_future,
                callback.future,
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not callback.future.done():
            callback.future.cancel()
        result = next(iter(done)).result()
        # Protocol now has named return values, assume result is one level deeper unless
        # there is explicit ambiguity.
        if not result:
            return None
        assert isinstance(result, dict)
        if return_as_dict:
            return result
        if len(result) == 0:
            return None
        assert len(result) == 1
        key = next(iter(result))
        return result[key]

    def mark_as_internal_type(self) -> None:
        self._is_internal_type = True


class ChannelOwner(AsyncIOEventEmitter):
    def __init__(
        self,
        parent: Union["ChannelOwner", "Connection"],
        type: str,
        guid: str,
        initializer: Dict,
    ) -> None:
        super().__init__(loop=parent._loop)
        self._loop: asyncio.AbstractEventLoop = parent._loop
        self._dispatcher_fiber: Any = parent._dispatcher_fiber
        self._type = type
        self._guid: str = guid
        self._connection: Connection = (
            parent._connection if isinstance(parent, ChannelOwner) else parent
        )
        self._parent: Optional[ChannelOwner] = (
            parent if isinstance(parent, ChannelOwner) else None
        )
        self._objects: Dict[str, "ChannelOwner"] = {}
        self._channel: Channel = Channel(self._connection, self)
        self._initializer = initializer
        self._was_collected = False

        self._connection._objects[guid] = self
        if self._parent:
            self._parent._objects[guid] = self

        self._event_to_subscription_mapping: Dict[str, str] = {}

    def _dispose(self, reason: Optional[str]) -> None:
        # Clean up from parent and connection.
        if self._parent:
            del self._parent._objects[self._guid]
        del self._connection._objects[self._guid]
        self._was_collected = reason == "gc"

        # Dispose all children.
        for object in list(self._objects.values()):
            object._dispose(reason)
        self._objects.clear()

    def _adopt(self, child: "ChannelOwner") -> None:
        del cast("ChannelOwner", child._parent)._objects[child._guid]
        self._objects[child._guid] = child
        child._parent = self

    def _set_event_to_subscription_mapping(self, mapping: Dict[str, str]) -> None:
        self._event_to_subscription_mapping = mapping

    def _update_subscription(self, event: str, enabled: bool) -> None:
        protocol_event = self._event_to_subscription_mapping.get(event)
        if protocol_event:
            self._connection.wrap_api_call_sync(
                lambda: self._channel.send_no_reply(
                    "updateSubscription", {"event": protocol_event, "enabled": enabled}
                ),
                True,
            )

    def _add_event_handler(self, event: str, k: Any, v: Any) -> None:
        if not self.listeners(event):
            self._update_subscription(event, True)
        super()._add_event_handler(event, k, v)

    def remove_listener(self, event: str, f: Any) -> None:
        super().remove_listener(event, f)
        if not self.listeners(event):
            self._update_subscription(event, False)


class ProtocolCallback:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.stack_trace: traceback.StackSummary
        self.no_reply: bool
        self.future = loop.create_future()
        # The outer task can get cancelled by the user, this forwards the cancellation to the inner task.
        current_task = asyncio.current_task()

        def cb(task: asyncio.Task) -> None:
            if current_task:
                current_task.remove_done_callback(cb)
            if task.cancelled():
                self.future.cancel()

        if current_task:
            current_task.add_done_callback(cb)
            self.future.add_done_callback(
                lambda _: (
                    current_task.remove_done_callback(cb) if current_task else None
                )
            )


class RootChannelOwner(ChannelOwner):
    def __init__(self, connection: "Connection") -> None:
        super().__init__(connection, "Root", "", {})

    async def initialize(self) -> "Playwright":
        return from_channel(
            await self._channel.send(
                "initialize",
                {
                    "sdkLanguage": "python",
                },
            )
        )


class Connection(EventEmitter):
    def __init__(
        self,
        dispatcher_fiber: Any,
        object_factory: Callable[[ChannelOwner, str, str, Dict], ChannelOwner],
        transport: Transport,
        loop: asyncio.AbstractEventLoop,
        local_utils: Optional["LocalUtils"] = None,
    ) -> None:
        super().__init__()
        self._dispatcher_fiber = dispatcher_fiber
        self._transport = transport
        self._transport.on_message = lambda msg: self.dispatch(msg)
        self._waiting_for_object: Dict[str, Callable[[ChannelOwner], None]] = {}
        self._last_id = 0
        self._objects: Dict[str, ChannelOwner] = {}
        self._callbacks: Dict[int, ProtocolCallback] = {}
        self._object_factory = object_factory
        self._is_sync = False
        self._child_ws_connections: List["Connection"] = []
        self._loop = loop
        self.playwright_future: asyncio.Future["Playwright"] = loop.create_future()
        self._error: Optional[BaseException] = None
        self.is_remote = False
        self._init_task: Optional[asyncio.Task] = None
        self._api_zone: contextvars.ContextVar[Optional[ParsedStackTrace]] = (
            contextvars.ContextVar("ApiZone", default=None)
        )
        self._local_utils: Optional["LocalUtils"] = local_utils
        self._tracing_count = 0
        self._closed_error: Optional[Exception] = None

    @property
    def local_utils(self) -> "LocalUtils":
        assert self._local_utils
        return self._local_utils

    def mark_as_remote(self) -> None:
        self.is_remote = True

    async def run_as_sync(self) -> None:
        self._is_sync = True
        await self.run()

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._root_object = RootChannelOwner(self)

        async def init() -> None:
            self.playwright_future.set_result(await self._root_object.initialize())

        await self._transport.connect()
        self._init_task = self._loop.create_task(init())
        await self._transport.run()

    def stop_sync(self) -> None:
        self._transport.request_stop()
        self._dispatcher_fiber.switch()
        self._loop.run_until_complete(self._transport.wait_until_stopped())
        self.cleanup()

    async def stop_async(self) -> None:
        self._transport.request_stop()
        await self._transport.wait_until_stopped()
        self.cleanup()

    def cleanup(self, cause: str = None) -> None:
        self._closed_error = TargetClosedError(cause) if cause else TargetClosedError()
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
        for ws_connection in self._child_ws_connections:
            ws_connection._transport.dispose()
        for callback in self._callbacks.values():
            # To prevent 'Future exception was never retrieved' we ignore all callbacks that are no_reply.
            if callback.no_reply:
                continue
            if callback.future.cancelled():
                continue
            callback.future.set_exception(self._closed_error)
        self._callbacks.clear()
        self.emit("close")

    def call_on_object_with_known_name(
        self, guid: str, callback: Callable[[ChannelOwner], None]
    ) -> None:
        self._waiting_for_object[guid] = callback

    def set_is_tracing(self, is_tracing: bool) -> None:
        if is_tracing:
            self._tracing_count += 1
        else:
            self._tracing_count -= 1

    def _send_message_to_server(
        self, object: ChannelOwner, method: str, params: Dict, no_reply: bool = False
    ) -> ProtocolCallback:
        if self._closed_error:
            raise self._closed_error
        if object._was_collected:
            raise Error(
                "The object has been collected to prevent unbounded heap growth."
            )
        self._last_id += 1
        id = self._last_id
        callback = ProtocolCallback(self._loop)
        task = asyncio.current_task(self._loop)
        callback.stack_trace = cast(
            traceback.StackSummary,
            getattr(task, "__pw_stack_trace__", traceback.extract_stack()),
        )
        callback.no_reply = no_reply
        self._callbacks[id] = callback
        stack_trace_information = cast(ParsedStackTrace, self._api_zone.get())
        frames = stack_trace_information.get("frames", [])
        location = (
            {
                "file": frames[0]["file"],
                "line": frames[0]["line"],
                "column": frames[0]["column"],
            }
            if frames
            else None
        )
        metadata = {
            "wallTime": int(datetime.datetime.now().timestamp() * 1000),
            "apiName": stack_trace_information["apiName"],
            "internal": not stack_trace_information["apiName"],
        }
        if location:
            metadata["location"] = location  # type: ignore
        message = {
            "id": id,
            "guid": object._guid,
            "method": method,
            "params": self._replace_channels_with_guids(params),
            "metadata": metadata,
        }
        if (
            self._tracing_count > 0
            and frames
            and frames
            and object._guid != "localUtils"
        ):
            self.local_utils.add_stack_to_tracing_no_reply(id, frames)

        self._transport.send(message)
        self._callbacks[id] = callback

        return callback

    def dispatch(self, msg: ParsedMessagePayload) -> None:
        if self._closed_error:
            return
        id = msg.get("id")
        if id:
            callback = self._callbacks.pop(id)
            if callback.future.cancelled():
                return
            # No reply messages are used to e.g. waitForEventInfo(after) which returns exceptions on page close.
            # To prevent 'Future exception was never retrieved' we just ignore such messages.
            if callback.no_reply:
                return
            error = msg.get("error")
            if error and not msg.get("result"):
                parsed_error = parse_error(
                    error["error"], format_call_log(msg.get("log"))  # type: ignore
                )
                parsed_error._stack = "".join(
                    traceback.format_list(callback.stack_trace)[-10:]
                )
                callback.future.set_exception(parsed_error)
            else:
                result = self._replace_guids_with_channels(msg.get("result"))
                callback.future.set_result(result)
            return

        guid = msg["guid"]
        method = msg["method"]
        params = msg.get("params")
        if method == "__create__":
            assert params
            parent = self._objects[guid]
            self._create_remote_object(
                parent, params["type"], params["guid"], params["initializer"]
            )
            return

        object = self._objects.get(guid)
        if not object:
            raise Exception(f'Cannot find object to "{method}": {guid}')

        if method == "__adopt__":
            child_guid = cast(Dict[str, str], params)["guid"]
            child = self._objects.get(child_guid)
            if not child:
                raise Exception(f"Unknown new child: {child_guid}")
            object._adopt(child)
            return

        if method == "__dispose__":
            assert isinstance(params, dict)
            self._objects[guid]._dispose(cast(Optional[str], params.get("reason")))
            return
        object = self._objects[guid]
        should_replace_guids_with_channels = "jsonPipe@" not in guid
        try:
            if self._is_sync:
                for listener in object._channel.listeners(method):
                    # Event handlers like route/locatorHandlerTriggered require us to perform async work.
                    # In order to report their potential errors to the user, we need to catch it and store it in the connection
                    def _done_callback(future: asyncio.Future) -> None:
                        exc = future.exception()
                        if exc:
                            self._on_event_listener_error(exc)

                    def _listener_with_error_handler_attached(params: Any) -> None:
                        potential_future = listener(params)
                        if asyncio.isfuture(potential_future):
                            potential_future.add_done_callback(_done_callback)

                    # Each event handler is a potentilly blocking context, create a fiber for each
                    # and switch to them in order, until they block inside and pass control to each
                    # other and then eventually back to dispatcher as listener functions return.
                    g = EventGreenlet(_listener_with_error_handler_attached)
                    if should_replace_guids_with_channels:
                        g.switch(self._replace_guids_with_channels(params))
                    else:
                        g.switch(params)
            else:
                if should_replace_guids_with_channels:
                    object._channel.emit(
                        method, self._replace_guids_with_channels(params)
                    )
                else:
                    object._channel.emit(method, params)
        except BaseException as exc:
            self._on_event_listener_error(exc)

    def _on_event_listener_error(self, exc: BaseException) -> None:
        print("Error occurred in event listener", file=sys.stderr)
        traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)
        # Save the error to throw at the next API call. This "replicates" unhandled rejection in Node.js.
        self._error = exc

    def _create_remote_object(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> ChannelOwner:
        initializer = self._replace_guids_with_channels(initializer)
        result = self._object_factory(parent, type, guid, initializer)
        if guid in self._waiting_for_object:
            self._waiting_for_object.pop(guid)(result)
        return result

    def _replace_channels_with_guids(
        self,
        payload: Any,
    ) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, Path):
            return str(payload)
        if isinstance(payload, collections.abc.Sequence) and not isinstance(
            payload, str
        ):
            return list(map(self._replace_channels_with_guids, payload))
        if isinstance(payload, Channel):
            return dict(guid=payload._guid)
        if isinstance(payload, dict):
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_channels_with_guids(value)
            return result
        return payload

    def _replace_guids_with_channels(self, payload: Any) -> Any:
        if payload is None:
            return payload
        if isinstance(payload, list):
            return list(map(self._replace_guids_with_channels, payload))
        if isinstance(payload, dict):
            if payload.get("guid") in self._objects:
                return self._objects[payload["guid"]]._channel
            result = {}
            for key, value in payload.items():
                result[key] = self._replace_guids_with_channels(value)
            return result
        return payload

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(task, "__pw_stack__", inspect.stack())
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
            raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
        finally:
            self._api_zone.set(None)

    def wrap_api_call_sync(
        self, cb: Callable[[], Any], is_internal: bool = False
    ) -> Any:
        if self._api_zone.get():
            return cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(task, "__pw_stack__", inspect.stack())
        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal)
        self._api_zone.set(parsed_st)
        try:
            return cb()
        except Exception as error:
            raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
        finally:
            self._api_zone.set(None)


def from_channel(channel: Channel) -> Any:
    return channel._object


def from_nullable_channel(channel: Optional[Channel]) -> Optional[Any]:
    return channel._object if channel else None


class StackFrame(TypedDict):
    file: str
    line: int
    column: int
    function: Optional[str]


class ParsedStackTrace(TypedDict):
    frames: List[StackFrame]
    apiName: Optional[str]


def _extract_stack_trace_information_from_stack(
    st: List[inspect.FrameInfo], is_internal: bool
) -> ParsedStackTrace:
    playwright_module_path = str(Path(playwright.__file__).parents[0])
    last_internal_api_name = ""
    api_name = ""
    parsed_frames: List[StackFrame] = []
    for frame in st:
        # Sync and Async implementations can have event handlers. When these are sync, they
        # get evaluated in the context of the event loop, so they contain the stack trace of when
        # the message was received. _impl_to_api_mapping is glue between the user-code and internal
        # code to translate impl classes to api classes. We want to ignore these frames.
        if playwright._impl._impl_to_api_mapping.__file__ == frame.filename:
            continue
        is_playwright_internal = frame.filename.startswith(playwright_module_path)

        method_name = ""
        if "self" in frame[0].f_locals:
            method_name = frame[0].f_locals["self"].__class__.__name__ + "."
        method_name += frame[0].f_code.co_name

        if not is_playwright_internal:
            parsed_frames.append(
                {
                    "file": frame.filename,
                    "line": frame.lineno,
                    "column": 0,
                    "function": method_name,
                }
            )
        if is_playwright_internal:
            last_internal_api_name = method_name
        elif last_internal_api_name:
            api_name = last_internal_api_name
            last_internal_api_name = ""
    if not api_name:
        api_name = last_internal_api_name

    return {
        "frames": parsed_frames,
        "apiName": "" if is_internal else api_name,
    }


def _filter_none(d: Mapping) -> Dict:
    return {k: v for k, v in d.items() if v is not None}


def format_call_log(log: Optional[List[str]]) -> str:
    if not log:
        return ""
    if len(list(filter(lambda x: x.strip(), log))) == 0:
        return ""
    return "\nCall log:\n" + "\n".join(log) + "\n"

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\color.py ===
import re
import sys
from colorsys import rgb_to_hls
from enum import IntEnum
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple, Optional, Tuple

from ._palettes import EIGHT_BIT_PALETTE, STANDARD_PALETTE, WINDOWS_PALETTE
from .color_triplet import ColorTriplet
from .repr import Result, rich_repr
from .terminal_theme import DEFAULT_TERMINAL_THEME

if TYPE_CHECKING:  # pragma: no cover
    from .terminal_theme import TerminalTheme
    from .text import Text


WINDOWS = sys.platform == "win32"


class ColorSystem(IntEnum):
    """One of the 3 color system supported by terminals."""

    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorSystem.{self.name}"

    def __str__(self) -> str:
        return repr(self)


class ColorType(IntEnum):
    """Type of color stored in Color class."""

    DEFAULT = 0
    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorType.{self.name}"


ANSI_COLOR_NAMES = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "bright_black": 8,
    "bright_red": 9,
    "bright_green": 10,
    "bright_yellow": 11,
    "bright_blue": 12,
    "bright_magenta": 13,
    "bright_cyan": 14,
    "bright_white": 15,
    "grey0": 16,
    "gray0": 16,
    "navy_blue": 17,
    "dark_blue": 18,
    "blue3": 20,
    "blue1": 21,
    "dark_green": 22,
    "deep_sky_blue4": 25,
    "dodger_blue3": 26,
    "dodger_blue2": 27,
    "green4": 28,
    "spring_green4": 29,
    "turquoise4": 30,
    "deep_sky_blue3": 32,
    "dodger_blue1": 33,
    "green3": 40,
    "spring_green3": 41,
    "dark_cyan": 36,
    "light_sea_green": 37,
    "deep_sky_blue2": 38,
    "deep_sky_blue1": 39,
    "spring_green2": 47,
    "cyan3": 43,
    "dark_turquoise": 44,
    "turquoise2": 45,
    "green1": 46,
    "spring_green1": 48,
    "medium_spring_green": 49,
    "cyan2": 50,
    "cyan1": 51,
    "dark_red": 88,
    "deep_pink4": 125,
    "purple4": 55,
    "purple3": 56,
    "blue_violet": 57,
    "orange4": 94,
    "grey37": 59,
    "gray37": 59,
    "medium_purple4": 60,
    "slate_blue3": 62,
    "royal_blue1": 63,
    "chartreuse4": 64,
    "dark_sea_green4": 71,
    "pale_turquoise4": 66,
    "steel_blue": 67,
    "steel_blue3": 68,
    "cornflower_blue": 69,
    "chartreuse3": 76,
    "cadet_blue": 73,
    "sky_blue3": 74,
    "steel_blue1": 81,
    "pale_green3": 114,
    "sea_green3": 78,
    "aquamarine3": 79,
    "medium_turquoise": 80,
    "chartreuse2": 112,
    "sea_green2": 83,
    "sea_green1": 85,
    "aquamarine1": 122,
    "dark_slate_gray2": 87,
    "dark_magenta": 91,
    "dark_violet": 128,
    "purple": 129,
    "light_pink4": 95,
    "plum4": 96,
    "medium_purple3": 98,
    "slate_blue1": 99,
    "yellow4": 106,
    "wheat4": 101,
    "grey53": 102,
    "gray53": 102,
    "light_slate_grey": 103,
    "light_slate_gray": 103,
    "medium_purple": 104,
    "light_slate_blue": 105,
    "dark_olive_green3": 149,
    "dark_sea_green": 108,
    "light_sky_blue3": 110,
    "sky_blue2": 111,
    "dark_sea_green3": 150,
    "dark_slate_gray3": 116,
    "sky_blue1": 117,
    "chartreuse1": 118,
    "light_green": 120,
    "pale_green1": 156,
    "dark_slate_gray1": 123,
    "red3": 160,
    "medium_violet_red": 126,
    "magenta3": 164,
    "dark_orange3": 166,
    "indian_red": 167,
    "hot_pink3": 168,
    "medium_orchid3": 133,
    "medium_orchid": 134,
    "medium_purple2": 140,
    "dark_goldenrod": 136,
    "light_salmon3": 173,
    "rosy_brown": 138,
    "grey63": 139,
    "gray63": 139,
    "medium_purple1": 141,
    "gold3": 178,
    "dark_khaki": 143,
    "navajo_white3": 144,
    "grey69": 145,
    "gray69": 145,
    "light_steel_blue3": 146,
    "light_steel_blue": 147,
    "yellow3": 184,
    "dark_sea_green2": 157,
    "light_cyan3": 152,
    "light_sky_blue1": 153,
    "green_yellow": 154,
    "dark_olive_green2": 155,
    "dark_sea_green1": 193,
    "pale_turquoise1": 159,
    "deep_pink3": 162,
    "magenta2": 200,
    "hot_pink2": 169,
    "orchid": 170,
    "medium_orchid1": 207,
    "orange3": 172,
    "light_pink3": 174,
    "pink3": 175,
    "plum3": 176,
    "violet": 177,
    "light_goldenrod3": 179,
    "tan": 180,
    "misty_rose3": 181,
    "thistle3": 182,
    "plum2": 183,
    "khaki3": 185,
    "light_goldenrod2": 222,
    "light_yellow3": 187,
    "grey84": 188,
    "gray84": 188,
    "light_steel_blue1": 189,
    "yellow2": 190,
    "dark_olive_green1": 192,
    "honeydew2": 194,
    "light_cyan1": 195,
    "red1": 196,
    "deep_pink2": 197,
    "deep_pink1": 199,
    "magenta1": 201,
    "orange_red1": 202,
    "indian_red1": 204,
    "hot_pink": 206,
    "dark_orange": 208,
    "salmon1": 209,
    "light_coral": 210,
    "pale_violet_red1": 211,
    "orchid2": 212,
    "orchid1": 213,
    "orange1": 214,
    "sandy_brown": 215,
    "light_salmon1": 216,
    "light_pink1": 217,
    "pink1": 218,
    "plum1": 219,
    "gold1": 220,
    "navajo_white1": 223,
    "misty_rose1": 224,
    "thistle1": 225,
    "yellow1": 226,
    "light_goldenrod1": 227,
    "khaki1": 228,
    "wheat1": 229,
    "cornsilk1": 230,
    "grey100": 231,
    "gray100": 231,
    "grey3": 232,
    "gray3": 232,
    "grey7": 233,
    "gray7": 233,
    "grey11": 234,
    "gray11": 234,
    "grey15": 235,
    "gray15": 235,
    "grey19": 236,
    "gray19": 236,
    "grey23": 237,
    "gray23": 237,
    "grey27": 238,
    "gray27": 238,
    "grey30": 239,
    "gray30": 239,
    "grey35": 240,
    "gray35": 240,
    "grey39": 241,
    "gray39": 241,
    "grey42": 242,
    "gray42": 242,
    "grey46": 243,
    "gray46": 243,
    "grey50": 244,
    "gray50": 244,
    "grey54": 245,
    "gray54": 245,
    "grey58": 246,
    "gray58": 246,
    "grey62": 247,
    "gray62": 247,
    "grey66": 248,
    "gray66": 248,
    "grey70": 249,
    "gray70": 249,
    "grey74": 250,
    "gray74": 250,
    "grey78": 251,
    "gray78": 251,
    "grey82": 252,
    "gray82": 252,
    "grey85": 253,
    "gray85": 253,
    "grey89": 254,
    "gray89": 254,
    "grey93": 255,
    "gray93": 255,
}


class ColorParseError(Exception):
    """The color could not be parsed."""


RE_COLOR = re.compile(
    r"""^
\#([0-9a-f]{6})$|
color\(([0-9]{1,3})\)$|
rgb\(([\d\s,]+)\)$
""",
    re.VERBOSE,
)


@rich_repr
class Color(NamedTuple):
    """Terminal color definition."""

    name: str
    """The name of the color (typically the input to Color.parse)."""
    type: ColorType
    """The type of the color."""
    number: Optional[int] = None
    """The color number, if a standard color, or None."""
    triplet: Optional[ColorTriplet] = None
    """A triplet of color components, if an RGB color."""

    def __rich__(self) -> "Text":
        """Displays the actual color if Rich printed."""
        from .style import Style
        from .text import Text

        return Text.assemble(
            f"<color {self.name!r} ({self.type.name.lower()})",
            ("⬤", Style(color=self)),
            " >",
        )

    def __rich_repr__(self) -> Result:
        yield self.name
        yield self.type
        yield "number", self.number, None
        yield "triplet", self.triplet, None

    @property
    def system(self) -> ColorSystem:
        """Get the native color system for this color."""
        if self.type == ColorType.DEFAULT:
            return ColorSystem.STANDARD
        return ColorSystem(int(self.type))

    @property
    def is_system_defined(self) -> bool:
        """Check if the color is ultimately defined by the system."""
        return self.system not in (ColorSystem.EIGHT_BIT, ColorSystem.TRUECOLOR)

    @property
    def is_default(self) -> bool:
        """Check if the color is a default color."""
        return self.type == ColorType.DEFAULT

    def get_truecolor(
        self, theme: Optional["TerminalTheme"] = None, foreground: bool = True
    ) -> ColorTriplet:
        """Get an equivalent color triplet for this color.

        Args:
            theme (TerminalTheme, optional): Optional terminal theme, or None to use default. Defaults to None.
            foreground (bool, optional): True for a foreground color, or False for background. Defaults to True.

        Returns:
            ColorTriplet: A color triplet containing RGB components.
        """

        if theme is None:
            theme = DEFAULT_TERMINAL_THEME
        if self.type == ColorType.TRUECOLOR:
            assert self.triplet is not None
            return self.triplet
        elif self.type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return EIGHT_BIT_PALETTE[self.number]
        elif self.type == ColorType.STANDARD:
            assert self.number is not None
            return theme.ansi_colors[self.number]
        elif self.type == ColorType.WINDOWS:
            assert self.number is not None
            return WINDOWS_PALETTE[self.number]
        else:  # self.type == ColorType.DEFAULT:
            assert self.number is None
            return theme.foreground_color if foreground else theme.background_color

    @classmethod
    def from_ansi(cls, number: int) -> "Color":
        """Create a Color number from it's 8-bit ansi number.

        Args:
            number (int): A number between 0-255 inclusive.

        Returns:
            Color: A new Color instance.
        """
        return cls(
            name=f"color({number})",
            type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
            number=number,
        )

    @classmethod
    def from_triplet(cls, triplet: "ColorTriplet") -> "Color":
        """Create a truecolor RGB color from a triplet of values.

        Args:
            triplet (ColorTriplet): A color triplet containing red, green and blue components.

        Returns:
            Color: A new color object.
        """
        return cls(name=triplet.hex, type=ColorType.TRUECOLOR, triplet=triplet)

    @classmethod
    def from_rgb(cls, red: float, green: float, blue: float) -> "Color":
        """Create a truecolor from three color components in the range(0->255).

        Args:
            red (float): Red component in range 0-255.
            green (float): Green component in range 0-255.
            blue (float): Blue component in range 0-255.

        Returns:
            Color: A new color object.
        """
        return cls.from_triplet(ColorTriplet(int(red), int(green), int(blue)))

    @classmethod
    def default(cls) -> "Color":
        """Get a Color instance representing the default color.

        Returns:
            Color: Default color.
        """
        return cls(name="default", type=ColorType.DEFAULT)

    @classmethod
    @lru_cache(maxsize=1024)
    def parse(cls, color: str) -> "Color":
        """Parse a color definition."""
        original_color = color
        color = color.lower().strip()

        if color == "default":
            return cls(color, type=ColorType.DEFAULT)

        color_number = ANSI_COLOR_NAMES.get(color)
        if color_number is not None:
            return cls(
                color,
                type=(ColorType.STANDARD if color_number < 16 else ColorType.EIGHT_BIT),
                number=color_number,
            )

        color_match = RE_COLOR.match(color)
        if color_match is None:
            raise ColorParseError(f"{original_color!r} is not a valid color")

        color_24, color_8, color_rgb = color_match.groups()
        if color_24:
            triplet = ColorTriplet(
                int(color_24[0:2], 16), int(color_24[2:4], 16), int(color_24[4:6], 16)
            )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

        elif color_8:
            number = int(color_8)
            if number > 255:
                raise ColorParseError(f"color number must be <= 255 in {color!r}")
            return cls(
                color,
                type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
                number=number,
            )

        else:  #  color_rgb:
            components = color_rgb.split(",")
            if len(components) != 3:
                raise ColorParseError(
                    f"expected three components in {original_color!r}"
                )
            red, green, blue = components
            triplet = ColorTriplet(int(red), int(green), int(blue))
            if not all(component <= 255 for component in triplet):
                raise ColorParseError(
                    f"color components must be <= 255 in {original_color!r}"
                )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

    @lru_cache(maxsize=1024)
    def get_ansi_codes(self, foreground: bool = True) -> Tuple[str, ...]:
        """Get the ANSI escape codes for this color."""
        _type = self.type
        if _type == ColorType.DEFAULT:
            return ("39" if foreground else "49",)

        elif _type == ColorType.WINDOWS:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.STANDARD:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return ("38" if foreground else "48", "5", str(self.number))

        else:  # self.standard == ColorStandard.TRUECOLOR:
            assert self.triplet is not None
            red, green, blue = self.triplet
            return ("38" if foreground else "48", "2", str(red), str(green), str(blue))

    @lru_cache(maxsize=1024)
    def downgrade(self, system: ColorSystem) -> "Color":
        """Downgrade a color system to a system with fewer colors."""

        if self.type in (ColorType.DEFAULT, system):
            return self
        # Convert to 8-bit color from truecolor color
        if system == ColorSystem.EIGHT_BIT and self.system == ColorSystem.TRUECOLOR:
            assert self.triplet is not None
            _h, l, s = rgb_to_hls(*self.triplet.normalized)
            # If saturation is under 15% assume it is grayscale
            if s < 0.15:
                gray = round(l * 25.0)
                if gray == 0:
                    color_number = 16
                elif gray == 25:
                    color_number = 231
                else:
                    color_number = 231 + gray
                return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

            red, green, blue = self.triplet
            six_red = red / 95 if red < 95 else 1 + (red - 95) / 40
            six_green = green / 95 if green < 95 else 1 + (green - 95) / 40
            six_blue = blue / 95 if blue < 95 else 1 + (blue - 95) / 40

            color_number = (
                16 + 36 * round(six_red) + 6 * round(six_green) + round(six_blue)
            )
            return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

        # Convert to standard from truecolor or 8-bit
        elif system == ColorSystem.STANDARD:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = STANDARD_PALETTE.match(triplet)
            return Color(self.name, ColorType.STANDARD, number=color_number)

        elif system == ColorSystem.WINDOWS:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                if self.number < 16:
                    return Color(self.name, ColorType.WINDOWS, number=self.number)
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = WINDOWS_PALETTE.match(triplet)
            return Color(self.name, ColorType.WINDOWS, number=color_number)

        return self


def parse_rgb_hex(hex_color: str) -> ColorTriplet:
    """Parse six hex characters in to RGB triplet."""
    assert len(hex_color) == 6, "must be 6 characters"
    color = ColorTriplet(
        int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    )
    return color


def blend_rgb(
    color1: ColorTriplet, color2: ColorTriplet, cross_fade: float = 0.5
) -> ColorTriplet:
    """Blend one RGB color in to another."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    new_color = ColorTriplet(
        int(r1 + (r2 - r1) * cross_fade),
        int(g1 + (g2 - g1) * cross_fade),
        int(b1 + (b2 - b1) * cross_fade),
    )
    return new_color


if __name__ == "__main__":  # pragma: no cover
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console()

    table = Table(show_footer=False, show_edge=True)
    table.add_column("Color", width=10, overflow="ellipsis")
    table.add_column("Number", justify="right", style="yellow")
    table.add_column("Name", style="green")
    table.add_column("Hex", style="blue")
    table.add_column("RGB", style="magenta")

    colors = sorted((v, k) for k, v in ANSI_COLOR_NAMES.items())
    for color_number, name in colors:
        if "grey" in name:
            continue
        color_cell = Text(" " * 10, style=f"on {name}")
        if color_number < 16:
            table.add_row(color_cell, f"{color_number}", Text(f'"{name}"'))
        else:
            color = EIGHT_BIT_PALETTE[color_number]  # type: ignore[has-type]
            table.add_row(
                color_cell, str(color_number), Text(f'"{name}"'), color.hex, color.rgb
            )

    console.print(table)

# === NexusCore/openenv\Lib\site-packages\contourpy\convert.py ===
from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, cast

import numpy as np

from contourpy._contourpy import FillType, LineType
import contourpy.array as arr
from contourpy.enum_util import as_fill_type, as_line_type
from contourpy.typecheck import check_filled, check_lines
from contourpy.types import MOVETO, offset_dtype

if TYPE_CHECKING:
    import contourpy._contourpy as cpy


def _convert_filled_from_OuterCode(
    filled: cpy.FillReturn_OuterCode,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.OuterCode:
        return filled
    elif fill_type_to == FillType.OuterOffset:
        return (filled[0], [arr.offsets_from_codes(codes) for codes in filled[1]])

    if len(filled[0]) > 0:
        points = arr.concat_points(filled[0])
        codes = arr.concat_codes(filled[1])
    else:
        points = None
        codes = None

    if fill_type_to == FillType.ChunkCombinedCode:
        return ([points], [codes])
    elif fill_type_to == FillType.ChunkCombinedOffset:
        return ([points], [None if codes is None else arr.offsets_from_codes(codes)])
    elif fill_type_to == FillType.ChunkCombinedCodeOffset:
        outer_offsets = None if points is None else arr.offsets_from_lengths(filled[0])
        ret1: cpy.FillReturn_ChunkCombinedCodeOffset = ([points], [codes], [outer_offsets])
        return ret1
    elif fill_type_to == FillType.ChunkCombinedOffsetOffset:
        if codes is None:
            ret2: cpy.FillReturn_ChunkCombinedOffsetOffset = ([None], [None], [None])
        else:
            offsets = arr.offsets_from_codes(codes)
            outer_offsets = arr.outer_offsets_from_list_of_codes(filled[1])
            ret2 = ([points], [offsets], [outer_offsets])
        return ret2
    else:
        raise ValueError(f"Invalid FillType {fill_type_to}")


def _convert_filled_from_OuterOffset(
    filled: cpy.FillReturn_OuterOffset,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.OuterCode:
        separate_codes = [arr.codes_from_offsets(offsets) for offsets in filled[1]]
        return (filled[0], separate_codes)
    elif fill_type_to == FillType.OuterOffset:
        return filled

    if len(filled[0]) > 0:
        points = arr.concat_points(filled[0])
        offsets = arr.concat_offsets(filled[1])
    else:
        points = None
        offsets = None

    if fill_type_to == FillType.ChunkCombinedCode:
        return ([points], [None if offsets is None else arr.codes_from_offsets(offsets)])
    elif fill_type_to == FillType.ChunkCombinedOffset:
        return ([points], [offsets])
    elif fill_type_to == FillType.ChunkCombinedCodeOffset:
        if offsets is None:
            ret1: cpy.FillReturn_ChunkCombinedCodeOffset = ([None], [None], [None])
        else:
            codes = arr.codes_from_offsets(offsets)
            outer_offsets = arr.offsets_from_lengths(filled[0])
            ret1 = ([points], [codes], [outer_offsets])
        return ret1
    elif fill_type_to == FillType.ChunkCombinedOffsetOffset:
        if points is None:
            ret2: cpy.FillReturn_ChunkCombinedOffsetOffset = ([None], [None], [None])
        else:
            outer_offsets = arr.outer_offsets_from_list_of_offsets(filled[1])
            ret2 = ([points], [offsets], [outer_offsets])
        return ret2
    else:
        raise ValueError(f"Invalid FillType {fill_type_to}")


def _convert_filled_from_ChunkCombinedCode(
    filled: cpy.FillReturn_ChunkCombinedCode,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.ChunkCombinedCode:
        return filled
    elif fill_type_to == FillType.ChunkCombinedOffset:
        codes = [None if codes is None else arr.offsets_from_codes(codes) for codes in filled[1]]
        return (filled[0], codes)
    else:
        raise ValueError(
            f"Conversion from {FillType.ChunkCombinedCode} to {fill_type_to} not supported")


def _convert_filled_from_ChunkCombinedOffset(
    filled: cpy.FillReturn_ChunkCombinedOffset,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.ChunkCombinedCode:
        chunk_codes: list[cpy.CodeArray | None] = []
        for points, offsets in zip(*filled):
            if points is None:
                chunk_codes.append(None)
            else:
                if TYPE_CHECKING:
                    assert offsets is not None
                chunk_codes.append(arr.codes_from_offsets_and_points(offsets, points))
        return (filled[0], chunk_codes)
    elif fill_type_to == FillType.ChunkCombinedOffset:
        return filled
    else:
        raise ValueError(
            f"Conversion from {FillType.ChunkCombinedOffset} to {fill_type_to} not supported")


def _convert_filled_from_ChunkCombinedCodeOffset(
    filled: cpy.FillReturn_ChunkCombinedCodeOffset,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.OuterCode:
        separate_points = []
        separate_codes = []
        for points, codes, outer_offsets in zip(*filled):
            if points is not None:
                if TYPE_CHECKING:
                    assert codes is not None
                    assert outer_offsets is not None
                separate_points += arr.split_points_by_offsets(points, outer_offsets)
                separate_codes += arr.split_codes_by_offsets(codes, outer_offsets)
        return (separate_points, separate_codes)
    elif fill_type_to == FillType.OuterOffset:
        separate_points = []
        separate_offsets = []
        for points, codes, outer_offsets in zip(*filled):
            if points is not None:
                if TYPE_CHECKING:
                    assert codes is not None
                    assert outer_offsets is not None
                separate_points += arr.split_points_by_offsets(points, outer_offsets)
                separate_codes = arr.split_codes_by_offsets(codes, outer_offsets)
                separate_offsets += [arr.offsets_from_codes(codes) for codes in separate_codes]
        return (separate_points, separate_offsets)
    elif fill_type_to == FillType.ChunkCombinedCode:
        ret1: cpy.FillReturn_ChunkCombinedCode = (filled[0], filled[1])
        return ret1
    elif fill_type_to == FillType.ChunkCombinedOffset:
        all_offsets = [None if codes is None else arr.offsets_from_codes(codes)
                       for codes in filled[1]]
        ret2: cpy.FillReturn_ChunkCombinedOffset = (filled[0], all_offsets)
        return ret2
    elif fill_type_to == FillType.ChunkCombinedCodeOffset:
        return filled
    elif fill_type_to == FillType.ChunkCombinedOffsetOffset:
        chunk_offsets: list[cpy.OffsetArray | None] = []
        chunk_outer_offsets: list[cpy.OffsetArray | None] = []
        for codes, outer_offsets in zip(*filled[1:]):
            if codes is None:
                chunk_offsets.append(None)
                chunk_outer_offsets.append(None)
            else:
                if TYPE_CHECKING:
                    assert outer_offsets is not None
                offsets = arr.offsets_from_codes(codes)
                outer_offsets = np.array([np.nonzero(offsets == oo)[0][0] for oo in outer_offsets],
                                         dtype=offset_dtype)
                chunk_offsets.append(offsets)
                chunk_outer_offsets.append(outer_offsets)
        ret3: cpy.FillReturn_ChunkCombinedOffsetOffset = (
            filled[0], chunk_offsets, chunk_outer_offsets,
        )
        return ret3
    else:
        raise ValueError(f"Invalid FillType {fill_type_to}")


def _convert_filled_from_ChunkCombinedOffsetOffset(
    filled: cpy.FillReturn_ChunkCombinedOffsetOffset,
    fill_type_to: FillType,
) -> cpy.FillReturn:
    if fill_type_to == FillType.OuterCode:
        separate_points = []
        separate_codes = []
        for points, offsets, outer_offsets in zip(*filled):
            if points is not None:
                if TYPE_CHECKING:
                    assert offsets is not None
                    assert outer_offsets is not None
                codes = arr.codes_from_offsets_and_points(offsets, points)
                outer_offsets = offsets[outer_offsets]
                separate_points += arr.split_points_by_offsets(points, outer_offsets)
                separate_codes += arr.split_codes_by_offsets(codes, outer_offsets)
        return (separate_points, separate_codes)
    elif fill_type_to == FillType.OuterOffset:
        separate_points = []
        separate_offsets = []
        for points, offsets, outer_offsets in zip(*filled):
            if points is not None:
                if TYPE_CHECKING:
                    assert offsets is not None
                    assert outer_offsets is not None
                if len(outer_offsets) > 2:
                    separate_offsets += [offsets[s:e+1] - offsets[s] for s, e in
                                         pairwise(outer_offsets)]
                else:
                    separate_offsets.append(offsets)
                separate_points += arr.split_points_by_offsets(points, offsets[outer_offsets])
        return (separate_points, separate_offsets)
    elif fill_type_to == FillType.ChunkCombinedCode:
        chunk_codes: list[cpy.CodeArray | None] = []
        for points, offsets, outer_offsets in zip(*filled):
            if points is None:
                chunk_codes.append(None)
            else:
                if TYPE_CHECKING:
                    assert offsets is not None
                    assert outer_offsets is not None
                chunk_codes.append(arr.codes_from_offsets_and_points(offsets, points))
        ret1: cpy.FillReturn_ChunkCombinedCode = (filled[0], chunk_codes)
        return ret1
    elif fill_type_to == FillType.ChunkCombinedOffset:
        return (filled[0], filled[1])
    elif fill_type_to == FillType.ChunkCombinedCodeOffset:
        chunk_codes = []
        chunk_outer_offsets: list[cpy.OffsetArray | None] = []
        for points, offsets, outer_offsets in zip(*filled):
            if points is None:
                chunk_codes.append(None)
                chunk_outer_offsets.append(None)
            else:
                if TYPE_CHECKING:
                    assert offsets is not None
                    assert outer_offsets is not None
                chunk_codes.append(arr.codes_from_offsets_and_points(offsets, points))
                chunk_outer_offsets.append(offsets[outer_offsets])
        ret2: cpy.FillReturn_ChunkCombinedCodeOffset = (filled[0], chunk_codes, chunk_outer_offsets)
        return ret2
    elif fill_type_to == FillType.ChunkCombinedOffsetOffset:
        return filled
    else:
        raise ValueError(f"Invalid FillType {fill_type_to}")


def convert_filled(
    filled: cpy.FillReturn,
    fill_type_from: FillType | str,
    fill_type_to:  FillType | str,
) -> cpy.FillReturn:
    """Convert filled contours from one :class:`~.FillType` to another.

    Args:
        filled (sequence of arrays): Filled contour polygons to convert, such as those returned by
            :meth:`.ContourGenerator.filled`.
        fill_type_from (FillType or str): :class:`~.FillType` to convert from as enum or
            string equivalent.
        fill_type_to (FillType or str): :class:`~.FillType` to convert to as enum or string
            equivalent.

    Return:
        Converted filled contour polygons.

    When converting non-chunked fill types (``FillType.OuterCode`` or ``FillType.OuterOffset``) to
    chunked ones, all polygons are placed in the first chunk. When converting in the other
    direction, all chunk information is discarded. Converting a fill type that is not aware of the
    relationship between outer boundaries and contained holes (``FillType.ChunkCombinedCode`` or
    ``FillType.ChunkCombinedOffset``) to one that is will raise a ``ValueError``.

    .. versionadded:: 1.2.0
    """
    fill_type_from = as_fill_type(fill_type_from)
    fill_type_to = as_fill_type(fill_type_to)

    check_filled(filled, fill_type_from)

    if fill_type_from == FillType.OuterCode:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_OuterCode, filled)
        return _convert_filled_from_OuterCode(filled, fill_type_to)
    elif fill_type_from == FillType.OuterOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_OuterOffset, filled)
        return _convert_filled_from_OuterOffset(filled, fill_type_to)
    elif fill_type_from == FillType.ChunkCombinedCode:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCode, filled)
        return _convert_filled_from_ChunkCombinedCode(filled, fill_type_to)
    elif fill_type_from == FillType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffset, filled)
        return _convert_filled_from_ChunkCombinedOffset(filled, fill_type_to)
    elif fill_type_from == FillType.ChunkCombinedCodeOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedCodeOffset, filled)
        return _convert_filled_from_ChunkCombinedCodeOffset(filled, fill_type_to)
    elif fill_type_from == FillType.ChunkCombinedOffsetOffset:
        if TYPE_CHECKING:
            filled = cast(cpy.FillReturn_ChunkCombinedOffsetOffset, filled)
        return _convert_filled_from_ChunkCombinedOffsetOffset(filled, fill_type_to)
    else:
        raise ValueError(f"Invalid FillType {fill_type_from}")


def _convert_lines_from_Separate(
    lines: cpy.LineReturn_Separate,
    line_type_to: LineType,
) -> cpy.LineReturn:
    if line_type_to == LineType.Separate:
        return lines
    elif line_type_to == LineType.SeparateCode:
        separate_codes = [arr.codes_from_points(line) for line in lines]
        return (lines, separate_codes)
    elif line_type_to == LineType.ChunkCombinedCode:
        if not lines:
            ret1: cpy.LineReturn_ChunkCombinedCode = ([None], [None])
        else:
            points = arr.concat_points(lines)
            offsets = arr.offsets_from_lengths(lines)
            codes = arr.codes_from_offsets_and_points(offsets, points)
            ret1 = ([points], [codes])
        return ret1
    elif line_type_to == LineType.ChunkCombinedOffset:
        if not lines:
            ret2: cpy.LineReturn_ChunkCombinedOffset = ([None], [None])
        else:
            ret2 = ([arr.concat_points(lines)], [arr.offsets_from_lengths(lines)])
        return ret2
    elif line_type_to == LineType.ChunkCombinedNan:
        if not lines:
            ret3: cpy.LineReturn_ChunkCombinedNan = ([None],)
        else:
            ret3 = ([arr.concat_points_with_nan(lines)],)
        return ret3
    else:
        raise ValueError(f"Invalid LineType {line_type_to}")


def _convert_lines_from_SeparateCode(
    lines: cpy.LineReturn_SeparateCode,
    line_type_to: LineType,
) -> cpy.LineReturn:
    if line_type_to == LineType.Separate:
        # Drop codes.
        return lines[0]
    elif line_type_to == LineType.SeparateCode:
        return lines
    elif line_type_to == LineType.ChunkCombinedCode:
        if not lines[0]:
            ret1: cpy.LineReturn_ChunkCombinedCode = ([None], [None])
        else:
            ret1 = ([arr.concat_points(lines[0])], [arr.concat_codes(lines[1])])
        return ret1
    elif line_type_to == LineType.ChunkCombinedOffset:
        if not lines[0]:
            ret2: cpy.LineReturn_ChunkCombinedOffset = ([None], [None])
        else:
            ret2 = ([arr.concat_points(lines[0])], [arr.offsets_from_lengths(lines[0])])
        return ret2
    elif line_type_to == LineType.ChunkCombinedNan:
        if not lines[0]:
            ret3: cpy.LineReturn_ChunkCombinedNan = ([None],)
        else:
            ret3 = ([arr.concat_points_with_nan(lines[0])],)
        return ret3
    else:
        raise ValueError(f"Invalid LineType {line_type_to}")


def _convert_lines_from_ChunkCombinedCode(
    lines: cpy.LineReturn_ChunkCombinedCode,
    line_type_to: LineType,
) -> cpy.LineReturn:
    if line_type_to in (LineType.Separate, LineType.SeparateCode):
        separate_lines = []
        for points, codes in zip(*lines):
            if points is not None:
                if TYPE_CHECKING:
                    assert codes is not None
                split_at = np.nonzero(codes == MOVETO)[0]
                if len(split_at) > 1:
                    separate_lines += np.split(points, split_at[1:])
                else:
                    separate_lines.append(points)
        if line_type_to == LineType.Separate:
            return separate_lines
        else:
            separate_codes = [arr.codes_from_points(line) for line in separate_lines]
            return (separate_lines, separate_codes)
    elif line_type_to == LineType.ChunkCombinedCode:
        return lines
    elif line_type_to == LineType.ChunkCombinedOffset:
        chunk_offsets = [None if codes is None else arr.offsets_from_codes(codes)
                         for codes in lines[1]]
        return (lines[0], chunk_offsets)
    elif line_type_to == LineType.ChunkCombinedNan:
        points_nan: list[cpy.PointArray | None] = []
        for points, codes in zip(*lines):
            if points is None:
                points_nan.append(None)
            else:
                if TYPE_CHECKING:
                    assert codes is not None
                offsets = arr.offsets_from_codes(codes)
                points_nan.append(arr.insert_nan_at_offsets(points, offsets))
        return (points_nan,)
    else:
        raise ValueError(f"Invalid LineType {line_type_to}")


def _convert_lines_from_ChunkCombinedOffset(
    lines: cpy.LineReturn_ChunkCombinedOffset,
    line_type_to: LineType,
) -> cpy.LineReturn:
    if line_type_to in (LineType.Separate, LineType.SeparateCode):
        separate_lines = []
        for points, offsets in zip(*lines):
            if points is not None:
                if TYPE_CHECKING:
                    assert offsets is not None
                separate_lines += arr.split_points_by_offsets(points, offsets)
        if line_type_to == LineType.Separate:
            return separate_lines
        else:
            separate_codes = [arr.codes_from_points(line) for line in separate_lines]
            return (separate_lines, separate_codes)
    elif line_type_to == LineType.ChunkCombinedCode:
        chunk_codes: list[cpy.CodeArray | None] = []
        for points, offsets in zip(*lines):
            if points is None:
                chunk_codes.append(None)
            else:
                if TYPE_CHECKING:
                    assert offsets is not None
                chunk_codes.append(arr.codes_from_offsets_and_points(offsets, points))
        return (lines[0], chunk_codes)
    elif line_type_to == LineType.ChunkCombinedOffset:
        return lines
    elif line_type_to == LineType.ChunkCombinedNan:
        points_nan: list[cpy.PointArray | None] = []
        for points, offsets in zip(*lines):
            if points is None:
                points_nan.append(None)
            else:
                if TYPE_CHECKING:
                    assert offsets is not None
                points_nan.append(arr.insert_nan_at_offsets(points, offsets))
        return (points_nan,)
    else:
        raise ValueError(f"Invalid LineType {line_type_to}")


def _convert_lines_from_ChunkCombinedNan(
    lines: cpy.LineReturn_ChunkCombinedNan,
    line_type_to: LineType,
) -> cpy.LineReturn:
    if line_type_to in (LineType.Separate, LineType.SeparateCode):
        separate_lines = []
        for points in lines[0]:
            if points is not None:
                separate_lines += arr.split_points_at_nan(points)
        if line_type_to == LineType.Separate:
            return separate_lines
        else:
            separate_codes = [arr.codes_from_points(points) for points in separate_lines]
            return (separate_lines, separate_codes)
    elif line_type_to == LineType.ChunkCombinedCode:
        chunk_points: list[cpy.PointArray | None] = []
        chunk_codes: list[cpy.CodeArray | None] = []
        for points in lines[0]:
            if points is None:
                chunk_points.append(None)
                chunk_codes.append(None)
            else:
                points, offsets = arr.remove_nan(points)
                chunk_points.append(points)
                chunk_codes.append(arr.codes_from_offsets_and_points(offsets, points))
        return (chunk_points, chunk_codes)
    elif line_type_to == LineType.ChunkCombinedOffset:
        chunk_points = []
        chunk_offsets: list[cpy.OffsetArray | None] = []
        for points in lines[0]:
            if points is None:
                chunk_points.append(None)
                chunk_offsets.append(None)
            else:
                points, offsets = arr.remove_nan(points)
                chunk_points.append(points)
                chunk_offsets.append(offsets)
        return (chunk_points, chunk_offsets)
    elif line_type_to == LineType.ChunkCombinedNan:
        return lines
    else:
        raise ValueError(f"Invalid LineType {line_type_to}")


def convert_lines(
    lines: cpy.LineReturn,
    line_type_from: LineType | str,
    line_type_to:  LineType | str,
) -> cpy.LineReturn:
    """Convert contour lines from one :class:`~.LineType` to another.

    Args:
        lines (sequence of arrays): Contour lines to convert, such as those returned by
            :meth:`.ContourGenerator.lines`.
        line_type_from (LineType or str): :class:`~.LineType` to convert from as enum or
            string equivalent.
        line_type_to (LineType or str): :class:`~.LineType` to convert to as enum or string
            equivalent.

    Return:
        Converted contour lines.

    When converting non-chunked line types (``LineType.Separate`` or ``LineType.SeparateCode``) to
    chunked ones (``LineType.ChunkCombinedCode``, ``LineType.ChunkCombinedOffset`` or
    ``LineType.ChunkCombinedNan``), all lines are placed in the first chunk. When converting in the
    other direction, all chunk information is discarded.

    .. versionadded:: 1.2.0
    """
    line_type_from = as_line_type(line_type_from)
    line_type_to = as_line_type(line_type_to)

    check_lines(lines, line_type_from)

    if line_type_from == LineType.Separate:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_Separate, lines)
        return _convert_lines_from_Separate(lines, line_type_to)
    elif line_type_from == LineType.SeparateCode:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_SeparateCode, lines)
        return _convert_lines_from_SeparateCode(lines, line_type_to)
    elif line_type_from == LineType.ChunkCombinedCode:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedCode, lines)
        return _convert_lines_from_ChunkCombinedCode(lines, line_type_to)
    elif line_type_from == LineType.ChunkCombinedOffset:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedOffset, lines)
        return _convert_lines_from_ChunkCombinedOffset(lines, line_type_to)
    elif line_type_from == LineType.ChunkCombinedNan:
        if TYPE_CHECKING:
            lines = cast(cpy.LineReturn_ChunkCombinedNan, lines)
        return _convert_lines_from_ChunkCombinedNan(lines, line_type_to)
    else:
        raise ValueError(f"Invalid LineType {line_type_from}")


def convert_multi_filled(
    multi_filled: list[cpy.FillReturn],
    fill_type_from: FillType | str,
    fill_type_to:  FillType | str,
) -> list[cpy.FillReturn]:
    """Convert multiple sets of filled contours from one :class:`~.FillType` to another.

    Args:
        multi_filled (nested sequence of arrays): Filled contour polygons to convert, such as those
            returned by :meth:`.ContourGenerator.multi_filled`.
        fill_type_from (FillType or str): :class:`~.FillType` to convert from as enum or
            string equivalent.
        fill_type_to (FillType or str): :class:`~.FillType` to convert to as enum or string
            equivalent.

    Return:
        Converted sets filled contour polygons.

    When converting non-chunked fill types (``FillType.OuterCode`` or ``FillType.OuterOffset``) to
    chunked ones, all polygons are placed in the first chunk. When converting in the other
    direction, all chunk information is discarded. Converting a fill type that is not aware of the
    relationship between outer boundaries and contained holes (``FillType.ChunkCombinedCode`` or
    ``FillType.ChunkCombinedOffset``) to one that is will raise a ``ValueError``.

    .. versionadded:: 1.3.0
    """
    fill_type_from = as_fill_type(fill_type_from)
    fill_type_to = as_fill_type(fill_type_to)

    return [convert_filled(filled, fill_type_from, fill_type_to) for filled in multi_filled]


def convert_multi_lines(
    multi_lines: list[cpy.LineReturn],
    line_type_from: LineType | str,
    line_type_to:  LineType | str,
) -> list[cpy.LineReturn]:
    """Convert multiple sets of contour lines from one :class:`~.LineType` to another.

    Args:
        multi_lines (nested sequence of arrays): Contour lines to convert, such as those returned by
            :meth:`.ContourGenerator.multi_lines`.
        line_type_from (LineType or str): :class:`~.LineType` to convert from as enum or
            string equivalent.
        line_type_to (LineType or str): :class:`~.LineType` to convert to as enum or string
            equivalent.

    Return:
        Converted set of contour lines.

    When converting non-chunked line types (``LineType.Separate`` or ``LineType.SeparateCode``) to
    chunked ones (``LineType.ChunkCombinedCode``, ``LineType.ChunkCombinedOffset`` or
    ``LineType.ChunkCombinedNan``), all lines are placed in the first chunk. When converting in the
    other direction, all chunk information is discarded.

    .. versionadded:: 1.3.0
    """
    line_type_from = as_line_type(line_type_from)
    line_type_to = as_line_type(line_type_to)

    return [convert_lines(lines, line_type_from, line_type_to) for lines in multi_lines]

# === NexusCore/openenv\Lib\site-packages\rich\color.py ===
import re
import sys
from colorsys import rgb_to_hls
from enum import IntEnum
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple, Optional, Tuple

from ._palettes import EIGHT_BIT_PALETTE, STANDARD_PALETTE, WINDOWS_PALETTE
from .color_triplet import ColorTriplet
from .repr import Result, rich_repr
from .terminal_theme import DEFAULT_TERMINAL_THEME

if TYPE_CHECKING:  # pragma: no cover
    from .terminal_theme import TerminalTheme
    from .text import Text


WINDOWS = sys.platform == "win32"


class ColorSystem(IntEnum):
    """One of the 3 color system supported by terminals."""

    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorSystem.{self.name}"

    def __str__(self) -> str:
        return repr(self)


class ColorType(IntEnum):
    """Type of color stored in Color class."""

    DEFAULT = 0
    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorType.{self.name}"


ANSI_COLOR_NAMES = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "bright_black": 8,
    "bright_red": 9,
    "bright_green": 10,
    "bright_yellow": 11,
    "bright_blue": 12,
    "bright_magenta": 13,
    "bright_cyan": 14,
    "bright_white": 15,
    "grey0": 16,
    "gray0": 16,
    "navy_blue": 17,
    "dark_blue": 18,
    "blue3": 20,
    "blue1": 21,
    "dark_green": 22,
    "deep_sky_blue4": 25,
    "dodger_blue3": 26,
    "dodger_blue2": 27,
    "green4": 28,
    "spring_green4": 29,
    "turquoise4": 30,
    "deep_sky_blue3": 32,
    "dodger_blue1": 33,
    "green3": 40,
    "spring_green3": 41,
    "dark_cyan": 36,
    "light_sea_green": 37,
    "deep_sky_blue2": 38,
    "deep_sky_blue1": 39,
    "spring_green2": 47,
    "cyan3": 43,
    "dark_turquoise": 44,
    "turquoise2": 45,
    "green1": 46,
    "spring_green1": 48,
    "medium_spring_green": 49,
    "cyan2": 50,
    "cyan1": 51,
    "dark_red": 88,
    "deep_pink4": 125,
    "purple4": 55,
    "purple3": 56,
    "blue_violet": 57,
    "orange4": 94,
    "grey37": 59,
    "gray37": 59,
    "medium_purple4": 60,
    "slate_blue3": 62,
    "royal_blue1": 63,
    "chartreuse4": 64,
    "dark_sea_green4": 71,
    "pale_turquoise4": 66,
    "steel_blue": 67,
    "steel_blue3": 68,
    "cornflower_blue": 69,
    "chartreuse3": 76,
    "cadet_blue": 73,
    "sky_blue3": 74,
    "steel_blue1": 81,
    "pale_green3": 114,
    "sea_green3": 78,
    "aquamarine3": 79,
    "medium_turquoise": 80,
    "chartreuse2": 112,
    "sea_green2": 83,
    "sea_green1": 85,
    "aquamarine1": 122,
    "dark_slate_gray2": 87,
    "dark_magenta": 91,
    "dark_violet": 128,
    "purple": 129,
    "light_pink4": 95,
    "plum4": 96,
    "medium_purple3": 98,
    "slate_blue1": 99,
    "yellow4": 106,
    "wheat4": 101,
    "grey53": 102,
    "gray53": 102,
    "light_slate_grey": 103,
    "light_slate_gray": 103,
    "medium_purple": 104,
    "light_slate_blue": 105,
    "dark_olive_green3": 149,
    "dark_sea_green": 108,
    "light_sky_blue3": 110,
    "sky_blue2": 111,
    "dark_sea_green3": 150,
    "dark_slate_gray3": 116,
    "sky_blue1": 117,
    "chartreuse1": 118,
    "light_green": 120,
    "pale_green1": 156,
    "dark_slate_gray1": 123,
    "red3": 160,
    "medium_violet_red": 126,
    "magenta3": 164,
    "dark_orange3": 166,
    "indian_red": 167,
    "hot_pink3": 168,
    "medium_orchid3": 133,
    "medium_orchid": 134,
    "medium_purple2": 140,
    "dark_goldenrod": 136,
    "light_salmon3": 173,
    "rosy_brown": 138,
    "grey63": 139,
    "gray63": 139,
    "medium_purple1": 141,
    "gold3": 178,
    "dark_khaki": 143,
    "navajo_white3": 144,
    "grey69": 145,
    "gray69": 145,
    "light_steel_blue3": 146,
    "light_steel_blue": 147,
    "yellow3": 184,
    "dark_sea_green2": 157,
    "light_cyan3": 152,
    "light_sky_blue1": 153,
    "green_yellow": 154,
    "dark_olive_green2": 155,
    "dark_sea_green1": 193,
    "pale_turquoise1": 159,
    "deep_pink3": 162,
    "magenta2": 200,
    "hot_pink2": 169,
    "orchid": 170,
    "medium_orchid1": 207,
    "orange3": 172,
    "light_pink3": 174,
    "pink3": 175,
    "plum3": 176,
    "violet": 177,
    "light_goldenrod3": 179,
    "tan": 180,
    "misty_rose3": 181,
    "thistle3": 182,
    "plum2": 183,
    "khaki3": 185,
    "light_goldenrod2": 222,
    "light_yellow3": 187,
    "grey84": 188,
    "gray84": 188,
    "light_steel_blue1": 189,
    "yellow2": 190,
    "dark_olive_green1": 192,
    "honeydew2": 194,
    "light_cyan1": 195,
    "red1": 196,
    "deep_pink2": 197,
    "deep_pink1": 199,
    "magenta1": 201,
    "orange_red1": 202,
    "indian_red1": 204,
    "hot_pink": 206,
    "dark_orange": 208,
    "salmon1": 209,
    "light_coral": 210,
    "pale_violet_red1": 211,
    "orchid2": 212,
    "orchid1": 213,
    "orange1": 214,
    "sandy_brown": 215,
    "light_salmon1": 216,
    "light_pink1": 217,
    "pink1": 218,
    "plum1": 219,
    "gold1": 220,
    "navajo_white1": 223,
    "misty_rose1": 224,
    "thistle1": 225,
    "yellow1": 226,
    "light_goldenrod1": 227,
    "khaki1": 228,
    "wheat1": 229,
    "cornsilk1": 230,
    "grey100": 231,
    "gray100": 231,
    "grey3": 232,
    "gray3": 232,
    "grey7": 233,
    "gray7": 233,
    "grey11": 234,
    "gray11": 234,
    "grey15": 235,
    "gray15": 235,
    "grey19": 236,
    "gray19": 236,
    "grey23": 237,
    "gray23": 237,
    "grey27": 238,
    "gray27": 238,
    "grey30": 239,
    "gray30": 239,
    "grey35": 240,
    "gray35": 240,
    "grey39": 241,
    "gray39": 241,
    "grey42": 242,
    "gray42": 242,
    "grey46": 243,
    "gray46": 243,
    "grey50": 244,
    "gray50": 244,
    "grey54": 245,
    "gray54": 245,
    "grey58": 246,
    "gray58": 246,
    "grey62": 247,
    "gray62": 247,
    "grey66": 248,
    "gray66": 248,
    "grey70": 249,
    "gray70": 249,
    "grey74": 250,
    "gray74": 250,
    "grey78": 251,
    "gray78": 251,
    "grey82": 252,
    "gray82": 252,
    "grey85": 253,
    "gray85": 253,
    "grey89": 254,
    "gray89": 254,
    "grey93": 255,
    "gray93": 255,
}


class ColorParseError(Exception):
    """The color could not be parsed."""


RE_COLOR = re.compile(
    r"""^
\#([0-9a-f]{6})$|
color\(([0-9]{1,3})\)$|
rgb\(([\d\s,]+)\)$
""",
    re.VERBOSE,
)


@rich_repr
class Color(NamedTuple):
    """Terminal color definition."""

    name: str
    """The name of the color (typically the input to Color.parse)."""
    type: ColorType
    """The type of the color."""
    number: Optional[int] = None
    """The color number, if a standard color, or None."""
    triplet: Optional[ColorTriplet] = None
    """A triplet of color components, if an RGB color."""

    def __rich__(self) -> "Text":
        """Displays the actual color if Rich printed."""
        from .style import Style
        from .text import Text

        return Text.assemble(
            f"<color {self.name!r} ({self.type.name.lower()})",
            ("⬤", Style(color=self)),
            " >",
        )

    def __rich_repr__(self) -> Result:
        yield self.name
        yield self.type
        yield "number", self.number, None
        yield "triplet", self.triplet, None

    @property
    def system(self) -> ColorSystem:
        """Get the native color system for this color."""
        if self.type == ColorType.DEFAULT:
            return ColorSystem.STANDARD
        return ColorSystem(int(self.type))

    @property
    def is_system_defined(self) -> bool:
        """Check if the color is ultimately defined by the system."""
        return self.system not in (ColorSystem.EIGHT_BIT, ColorSystem.TRUECOLOR)

    @property
    def is_default(self) -> bool:
        """Check if the color is a default color."""
        return self.type == ColorType.DEFAULT

    def get_truecolor(
        self, theme: Optional["TerminalTheme"] = None, foreground: bool = True
    ) -> ColorTriplet:
        """Get an equivalent color triplet for this color.

        Args:
            theme (TerminalTheme, optional): Optional terminal theme, or None to use default. Defaults to None.
            foreground (bool, optional): True for a foreground color, or False for background. Defaults to True.

        Returns:
            ColorTriplet: A color triplet containing RGB components.
        """

        if theme is None:
            theme = DEFAULT_TERMINAL_THEME
        if self.type == ColorType.TRUECOLOR:
            assert self.triplet is not None
            return self.triplet
        elif self.type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return EIGHT_BIT_PALETTE[self.number]
        elif self.type == ColorType.STANDARD:
            assert self.number is not None
            return theme.ansi_colors[self.number]
        elif self.type == ColorType.WINDOWS:
            assert self.number is not None
            return WINDOWS_PALETTE[self.number]
        else:  # self.type == ColorType.DEFAULT:
            assert self.number is None
            return theme.foreground_color if foreground else theme.background_color

    @classmethod
    def from_ansi(cls, number: int) -> "Color":
        """Create a Color number from it's 8-bit ansi number.

        Args:
            number (int): A number between 0-255 inclusive.

        Returns:
            Color: A new Color instance.
        """
        return cls(
            name=f"color({number})",
            type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
            number=number,
        )

    @classmethod
    def from_triplet(cls, triplet: "ColorTriplet") -> "Color":
        """Create a truecolor RGB color from a triplet of values.

        Args:
            triplet (ColorTriplet): A color triplet containing red, green and blue components.

        Returns:
            Color: A new color object.
        """
        return cls(name=triplet.hex, type=ColorType.TRUECOLOR, triplet=triplet)

    @classmethod
    def from_rgb(cls, red: float, green: float, blue: float) -> "Color":
        """Create a truecolor from three color components in the range(0->255).

        Args:
            red (float): Red component in range 0-255.
            green (float): Green component in range 0-255.
            blue (float): Blue component in range 0-255.

        Returns:
            Color: A new color object.
        """
        return cls.from_triplet(ColorTriplet(int(red), int(green), int(blue)))

    @classmethod
    def default(cls) -> "Color":
        """Get a Color instance representing the default color.

        Returns:
            Color: Default color.
        """
        return cls(name="default", type=ColorType.DEFAULT)

    @classmethod
    @lru_cache(maxsize=1024)
    def parse(cls, color: str) -> "Color":
        """Parse a color definition."""
        original_color = color
        color = color.lower().strip()

        if color == "default":
            return cls(color, type=ColorType.DEFAULT)

        color_number = ANSI_COLOR_NAMES.get(color)
        if color_number is not None:
            return cls(
                color,
                type=(ColorType.STANDARD if color_number < 16 else ColorType.EIGHT_BIT),
                number=color_number,
            )

        color_match = RE_COLOR.match(color)
        if color_match is None:
            raise ColorParseError(f"{original_color!r} is not a valid color")

        color_24, color_8, color_rgb = color_match.groups()
        if color_24:
            triplet = ColorTriplet(
                int(color_24[0:2], 16), int(color_24[2:4], 16), int(color_24[4:6], 16)
            )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

        elif color_8:
            number = int(color_8)
            if number > 255:
                raise ColorParseError(f"color number must be <= 255 in {color!r}")
            return cls(
                color,
                type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
                number=number,
            )

        else:  #  color_rgb:
            components = color_rgb.split(",")
            if len(components) != 3:
                raise ColorParseError(
                    f"expected three components in {original_color!r}"
                )
            red, green, blue = components
            triplet = ColorTriplet(int(red), int(green), int(blue))
            if not all(component <= 255 for component in triplet):
                raise ColorParseError(
                    f"color components must be <= 255 in {original_color!r}"
                )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

    @lru_cache(maxsize=1024)
    def get_ansi_codes(self, foreground: bool = True) -> Tuple[str, ...]:
        """Get the ANSI escape codes for this color."""
        _type = self.type
        if _type == ColorType.DEFAULT:
            return ("39" if foreground else "49",)

        elif _type == ColorType.WINDOWS:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.STANDARD:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return ("38" if foreground else "48", "5", str(self.number))

        else:  # self.standard == ColorStandard.TRUECOLOR:
            assert self.triplet is not None
            red, green, blue = self.triplet
            return ("38" if foreground else "48", "2", str(red), str(green), str(blue))

    @lru_cache(maxsize=1024)
    def downgrade(self, system: ColorSystem) -> "Color":
        """Downgrade a color system to a system with fewer colors."""

        if self.type in (ColorType.DEFAULT, system):
            return self
        # Convert to 8-bit color from truecolor color
        if system == ColorSystem.EIGHT_BIT and self.system == ColorSystem.TRUECOLOR:
            assert self.triplet is not None
            _h, l, s = rgb_to_hls(*self.triplet.normalized)
            # If saturation is under 15% assume it is grayscale
            if s < 0.15:
                gray = round(l * 25.0)
                if gray == 0:
                    color_number = 16
                elif gray == 25:
                    color_number = 231
                else:
                    color_number = 231 + gray
                return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

            red, green, blue = self.triplet
            six_red = red / 95 if red < 95 else 1 + (red - 95) / 40
            six_green = green / 95 if green < 95 else 1 + (green - 95) / 40
            six_blue = blue / 95 if blue < 95 else 1 + (blue - 95) / 40

            color_number = (
                16 + 36 * round(six_red) + 6 * round(six_green) + round(six_blue)
            )
            return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

        # Convert to standard from truecolor or 8-bit
        elif system == ColorSystem.STANDARD:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = STANDARD_PALETTE.match(triplet)
            return Color(self.name, ColorType.STANDARD, number=color_number)

        elif system == ColorSystem.WINDOWS:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                if self.number < 16:
                    return Color(self.name, ColorType.WINDOWS, number=self.number)
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = WINDOWS_PALETTE.match(triplet)
            return Color(self.name, ColorType.WINDOWS, number=color_number)

        return self


def parse_rgb_hex(hex_color: str) -> ColorTriplet:
    """Parse six hex characters in to RGB triplet."""
    assert len(hex_color) == 6, "must be 6 characters"
    color = ColorTriplet(
        int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    )
    return color


def blend_rgb(
    color1: ColorTriplet, color2: ColorTriplet, cross_fade: float = 0.5
) -> ColorTriplet:
    """Blend one RGB color in to another."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    new_color = ColorTriplet(
        int(r1 + (r2 - r1) * cross_fade),
        int(g1 + (g2 - g1) * cross_fade),
        int(b1 + (b2 - b1) * cross_fade),
    )
    return new_color


if __name__ == "__main__":  # pragma: no cover
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console()

    table = Table(show_footer=False, show_edge=True)
    table.add_column("Color", width=10, overflow="ellipsis")
    table.add_column("Number", justify="right", style="yellow")
    table.add_column("Name", style="green")
    table.add_column("Hex", style="blue")
    table.add_column("RGB", style="magenta")

    colors = sorted((v, k) for k, v in ANSI_COLOR_NAMES.items())
    for color_number, name in colors:
        if "grey" in name:
            continue
        color_cell = Text(" " * 10, style=f"on {name}")
        if color_number < 16:
            table.add_row(color_cell, f"{color_number}", Text(f'"{name}"'))
        else:
            color = EIGHT_BIT_PALETTE[color_number]  # type: ignore[has-type]
            table.add_row(
                color_cell, str(color_number), Text(f'"{name}"'), color.hex, color.rgb
            )

    console.print(table)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\color.py ===
import re
import sys
from colorsys import rgb_to_hls
from enum import IntEnum
from functools import lru_cache
from typing import TYPE_CHECKING, NamedTuple, Optional, Tuple

from ._palettes import EIGHT_BIT_PALETTE, STANDARD_PALETTE, WINDOWS_PALETTE
from .color_triplet import ColorTriplet
from .repr import Result, rich_repr
from .terminal_theme import DEFAULT_TERMINAL_THEME

if TYPE_CHECKING:  # pragma: no cover
    from .terminal_theme import TerminalTheme
    from .text import Text


WINDOWS = sys.platform == "win32"


class ColorSystem(IntEnum):
    """One of the 3 color system supported by terminals."""

    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorSystem.{self.name}"

    def __str__(self) -> str:
        return repr(self)


class ColorType(IntEnum):
    """Type of color stored in Color class."""

    DEFAULT = 0
    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorType.{self.name}"


ANSI_COLOR_NAMES = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "bright_black": 8,
    "bright_red": 9,
    "bright_green": 10,
    "bright_yellow": 11,
    "bright_blue": 12,
    "bright_magenta": 13,
    "bright_cyan": 14,
    "bright_white": 15,
    "grey0": 16,
    "gray0": 16,
    "navy_blue": 17,
    "dark_blue": 18,
    "blue3": 20,
    "blue1": 21,
    "dark_green": 22,
    "deep_sky_blue4": 25,
    "dodger_blue3": 26,
    "dodger_blue2": 27,
    "green4": 28,
    "spring_green4": 29,
    "turquoise4": 30,
    "deep_sky_blue3": 32,
    "dodger_blue1": 33,
    "green3": 40,
    "spring_green3": 41,
    "dark_cyan": 36,
    "light_sea_green": 37,
    "deep_sky_blue2": 38,
    "deep_sky_blue1": 39,
    "spring_green2": 47,
    "cyan3": 43,
    "dark_turquoise": 44,
    "turquoise2": 45,
    "green1": 46,
    "spring_green1": 48,
    "medium_spring_green": 49,
    "cyan2": 50,
    "cyan1": 51,
    "dark_red": 88,
    "deep_pink4": 125,
    "purple4": 55,
    "purple3": 56,
    "blue_violet": 57,
    "orange4": 94,
    "grey37": 59,
    "gray37": 59,
    "medium_purple4": 60,
    "slate_blue3": 62,
    "royal_blue1": 63,
    "chartreuse4": 64,
    "dark_sea_green4": 71,
    "pale_turquoise4": 66,
    "steel_blue": 67,
    "steel_blue3": 68,
    "cornflower_blue": 69,
    "chartreuse3": 76,
    "cadet_blue": 73,
    "sky_blue3": 74,
    "steel_blue1": 81,
    "pale_green3": 114,
    "sea_green3": 78,
    "aquamarine3": 79,
    "medium_turquoise": 80,
    "chartreuse2": 112,
    "sea_green2": 83,
    "sea_green1": 85,
    "aquamarine1": 122,
    "dark_slate_gray2": 87,
    "dark_magenta": 91,
    "dark_violet": 128,
    "purple": 129,
    "light_pink4": 95,
    "plum4": 96,
    "medium_purple3": 98,
    "slate_blue1": 99,
    "yellow4": 106,
    "wheat4": 101,
    "grey53": 102,
    "gray53": 102,
    "light_slate_grey": 103,
    "light_slate_gray": 103,
    "medium_purple": 104,
    "light_slate_blue": 105,
    "dark_olive_green3": 149,
    "dark_sea_green": 108,
    "light_sky_blue3": 110,
    "sky_blue2": 111,
    "dark_sea_green3": 150,
    "dark_slate_gray3": 116,
    "sky_blue1": 117,
    "chartreuse1": 118,
    "light_green": 120,
    "pale_green1": 156,
    "dark_slate_gray1": 123,
    "red3": 160,
    "medium_violet_red": 126,
    "magenta3": 164,
    "dark_orange3": 166,
    "indian_red": 167,
    "hot_pink3": 168,
    "medium_orchid3": 133,
    "medium_orchid": 134,
    "medium_purple2": 140,
    "dark_goldenrod": 136,
    "light_salmon3": 173,
    "rosy_brown": 138,
    "grey63": 139,
    "gray63": 139,
    "medium_purple1": 141,
    "gold3": 178,
    "dark_khaki": 143,
    "navajo_white3": 144,
    "grey69": 145,
    "gray69": 145,
    "light_steel_blue3": 146,
    "light_steel_blue": 147,
    "yellow3": 184,
    "dark_sea_green2": 157,
    "light_cyan3": 152,
    "light_sky_blue1": 153,
    "green_yellow": 154,
    "dark_olive_green2": 155,
    "dark_sea_green1": 193,
    "pale_turquoise1": 159,
    "deep_pink3": 162,
    "magenta2": 200,
    "hot_pink2": 169,
    "orchid": 170,
    "medium_orchid1": 207,
    "orange3": 172,
    "light_pink3": 174,
    "pink3": 175,
    "plum3": 176,
    "violet": 177,
    "light_goldenrod3": 179,
    "tan": 180,
    "misty_rose3": 181,
    "thistle3": 182,
    "plum2": 183,
    "khaki3": 185,
    "light_goldenrod2": 222,
    "light_yellow3": 187,
    "grey84": 188,
    "gray84": 188,
    "light_steel_blue1": 189,
    "yellow2": 190,
    "dark_olive_green1": 192,
    "honeydew2": 194,
    "light_cyan1": 195,
    "red1": 196,
    "deep_pink2": 197,
    "deep_pink1": 199,
    "magenta1": 201,
    "orange_red1": 202,
    "indian_red1": 204,
    "hot_pink": 206,
    "dark_orange": 208,
    "salmon1": 209,
    "light_coral": 210,
    "pale_violet_red1": 211,
    "orchid2": 212,
    "orchid1": 213,
    "orange1": 214,
    "sandy_brown": 215,
    "light_salmon1": 216,
    "light_pink1": 217,
    "pink1": 218,
    "plum1": 219,
    "gold1": 220,
    "navajo_white1": 223,
    "misty_rose1": 224,
    "thistle1": 225,
    "yellow1": 226,
    "light_goldenrod1": 227,
    "khaki1": 228,
    "wheat1": 229,
    "cornsilk1": 230,
    "grey100": 231,
    "gray100": 231,
    "grey3": 232,
    "gray3": 232,
    "grey7": 233,
    "gray7": 233,
    "grey11": 234,
    "gray11": 234,
    "grey15": 235,
    "gray15": 235,
    "grey19": 236,
    "gray19": 236,
    "grey23": 237,
    "gray23": 237,
    "grey27": 238,
    "gray27": 238,
    "grey30": 239,
    "gray30": 239,
    "grey35": 240,
    "gray35": 240,
    "grey39": 241,
    "gray39": 241,
    "grey42": 242,
    "gray42": 242,
    "grey46": 243,
    "gray46": 243,
    "grey50": 244,
    "gray50": 244,
    "grey54": 245,
    "gray54": 245,
    "grey58": 246,
    "gray58": 246,
    "grey62": 247,
    "gray62": 247,
    "grey66": 248,
    "gray66": 248,
    "grey70": 249,
    "gray70": 249,
    "grey74": 250,
    "gray74": 250,
    "grey78": 251,
    "gray78": 251,
    "grey82": 252,
    "gray82": 252,
    "grey85": 253,
    "gray85": 253,
    "grey89": 254,
    "gray89": 254,
    "grey93": 255,
    "gray93": 255,
}


class ColorParseError(Exception):
    """The color could not be parsed."""


RE_COLOR = re.compile(
    r"""^
\#([0-9a-f]{6})$|
color\(([0-9]{1,3})\)$|
rgb\(([\d\s,]+)\)$
""",
    re.VERBOSE,
)


@rich_repr
class Color(NamedTuple):
    """Terminal color definition."""

    name: str
    """The name of the color (typically the input to Color.parse)."""
    type: ColorType
    """The type of the color."""
    number: Optional[int] = None
    """The color number, if a standard color, or None."""
    triplet: Optional[ColorTriplet] = None
    """A triplet of color components, if an RGB color."""

    def __rich__(self) -> "Text":
        """Displays the actual color if Rich printed."""
        from .style import Style
        from .text import Text

        return Text.assemble(
            f"<color {self.name!r} ({self.type.name.lower()})",
            ("⬤", Style(color=self)),
            " >",
        )

    def __rich_repr__(self) -> Result:
        yield self.name
        yield self.type
        yield "number", self.number, None
        yield "triplet", self.triplet, None

    @property
    def system(self) -> ColorSystem:
        """Get the native color system for this color."""
        if self.type == ColorType.DEFAULT:
            return ColorSystem.STANDARD
        return ColorSystem(int(self.type))

    @property
    def is_system_defined(self) -> bool:
        """Check if the color is ultimately defined by the system."""
        return self.system not in (ColorSystem.EIGHT_BIT, ColorSystem.TRUECOLOR)

    @property
    def is_default(self) -> bool:
        """Check if the color is a default color."""
        return self.type == ColorType.DEFAULT

    def get_truecolor(
        self, theme: Optional["TerminalTheme"] = None, foreground: bool = True
    ) -> ColorTriplet:
        """Get an equivalent color triplet for this color.

        Args:
            theme (TerminalTheme, optional): Optional terminal theme, or None to use default. Defaults to None.
            foreground (bool, optional): True for a foreground color, or False for background. Defaults to True.

        Returns:
            ColorTriplet: A color triplet containing RGB components.
        """

        if theme is None:
            theme = DEFAULT_TERMINAL_THEME
        if self.type == ColorType.TRUECOLOR:
            assert self.triplet is not None
            return self.triplet
        elif self.type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return EIGHT_BIT_PALETTE[self.number]
        elif self.type == ColorType.STANDARD:
            assert self.number is not None
            return theme.ansi_colors[self.number]
        elif self.type == ColorType.WINDOWS:
            assert self.number is not None
            return WINDOWS_PALETTE[self.number]
        else:  # self.type == ColorType.DEFAULT:
            assert self.number is None
            return theme.foreground_color if foreground else theme.background_color

    @classmethod
    def from_ansi(cls, number: int) -> "Color":
        """Create a Color number from it's 8-bit ansi number.

        Args:
            number (int): A number between 0-255 inclusive.

        Returns:
            Color: A new Color instance.
        """
        return cls(
            name=f"color({number})",
            type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
            number=number,
        )

    @classmethod
    def from_triplet(cls, triplet: "ColorTriplet") -> "Color":
        """Create a truecolor RGB color from a triplet of values.

        Args:
            triplet (ColorTriplet): A color triplet containing red, green and blue components.

        Returns:
            Color: A new color object.
        """
        return cls(name=triplet.hex, type=ColorType.TRUECOLOR, triplet=triplet)

    @classmethod
    def from_rgb(cls, red: float, green: float, blue: float) -> "Color":
        """Create a truecolor from three color components in the range(0->255).

        Args:
            red (float): Red component in range 0-255.
            green (float): Green component in range 0-255.
            blue (float): Blue component in range 0-255.

        Returns:
            Color: A new color object.
        """
        return cls.from_triplet(ColorTriplet(int(red), int(green), int(blue)))

    @classmethod
    def default(cls) -> "Color":
        """Get a Color instance representing the default color.

        Returns:
            Color: Default color.
        """
        return cls(name="default", type=ColorType.DEFAULT)

    @classmethod
    @lru_cache(maxsize=1024)
    def parse(cls, color: str) -> "Color":
        """Parse a color definition."""
        original_color = color
        color = color.lower().strip()

        if color == "default":
            return cls(color, type=ColorType.DEFAULT)

        color_number = ANSI_COLOR_NAMES.get(color)
        if color_number is not None:
            return cls(
                color,
                type=(ColorType.STANDARD if color_number < 16 else ColorType.EIGHT_BIT),
                number=color_number,
            )

        color_match = RE_COLOR.match(color)
        if color_match is None:
            raise ColorParseError(f"{original_color!r} is not a valid color")

        color_24, color_8, color_rgb = color_match.groups()
        if color_24:
            triplet = ColorTriplet(
                int(color_24[0:2], 16), int(color_24[2:4], 16), int(color_24[4:6], 16)
            )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

        elif color_8:
            number = int(color_8)
            if number > 255:
                raise ColorParseError(f"color number must be <= 255 in {color!r}")
            return cls(
                color,
                type=(ColorType.STANDARD if number < 16 else ColorType.EIGHT_BIT),
                number=number,
            )

        else:  #  color_rgb:
            components = color_rgb.split(",")
            if len(components) != 3:
                raise ColorParseError(
                    f"expected three components in {original_color!r}"
                )
            red, green, blue = components
            triplet = ColorTriplet(int(red), int(green), int(blue))
            if not all(component <= 255 for component in triplet):
                raise ColorParseError(
                    f"color components must be <= 255 in {original_color!r}"
                )
            return cls(color, ColorType.TRUECOLOR, triplet=triplet)

    @lru_cache(maxsize=1024)
    def get_ansi_codes(self, foreground: bool = True) -> Tuple[str, ...]:
        """Get the ANSI escape codes for this color."""
        _type = self.type
        if _type == ColorType.DEFAULT:
            return ("39" if foreground else "49",)

        elif _type == ColorType.WINDOWS:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.STANDARD:
            number = self.number
            assert number is not None
            fore, back = (30, 40) if number < 8 else (82, 92)
            return (str(fore + number if foreground else back + number),)

        elif _type == ColorType.EIGHT_BIT:
            assert self.number is not None
            return ("38" if foreground else "48", "5", str(self.number))

        else:  # self.standard == ColorStandard.TRUECOLOR:
            assert self.triplet is not None
            red, green, blue = self.triplet
            return ("38" if foreground else "48", "2", str(red), str(green), str(blue))

    @lru_cache(maxsize=1024)
    def downgrade(self, system: ColorSystem) -> "Color":
        """Downgrade a color system to a system with fewer colors."""

        if self.type in (ColorType.DEFAULT, system):
            return self
        # Convert to 8-bit color from truecolor color
        if system == ColorSystem.EIGHT_BIT and self.system == ColorSystem.TRUECOLOR:
            assert self.triplet is not None
            _h, l, s = rgb_to_hls(*self.triplet.normalized)
            # If saturation is under 15% assume it is grayscale
            if s < 0.15:
                gray = round(l * 25.0)
                if gray == 0:
                    color_number = 16
                elif gray == 25:
                    color_number = 231
                else:
                    color_number = 231 + gray
                return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

            red, green, blue = self.triplet
            six_red = red / 95 if red < 95 else 1 + (red - 95) / 40
            six_green = green / 95 if green < 95 else 1 + (green - 95) / 40
            six_blue = blue / 95 if blue < 95 else 1 + (blue - 95) / 40

            color_number = (
                16 + 36 * round(six_red) + 6 * round(six_green) + round(six_blue)
            )
            return Color(self.name, ColorType.EIGHT_BIT, number=color_number)

        # Convert to standard from truecolor or 8-bit
        elif system == ColorSystem.STANDARD:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = STANDARD_PALETTE.match(triplet)
            return Color(self.name, ColorType.STANDARD, number=color_number)

        elif system == ColorSystem.WINDOWS:
            if self.system == ColorSystem.TRUECOLOR:
                assert self.triplet is not None
                triplet = self.triplet
            else:  # self.system == ColorSystem.EIGHT_BIT
                assert self.number is not None
                if self.number < 16:
                    return Color(self.name, ColorType.WINDOWS, number=self.number)
                triplet = ColorTriplet(*EIGHT_BIT_PALETTE[self.number])

            color_number = WINDOWS_PALETTE.match(triplet)
            return Color(self.name, ColorType.WINDOWS, number=color_number)

        return self


def parse_rgb_hex(hex_color: str) -> ColorTriplet:
    """Parse six hex characters in to RGB triplet."""
    assert len(hex_color) == 6, "must be 6 characters"
    color = ColorTriplet(
        int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    )
    return color


def blend_rgb(
    color1: ColorTriplet, color2: ColorTriplet, cross_fade: float = 0.5
) -> ColorTriplet:
    """Blend one RGB color in to another."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    new_color = ColorTriplet(
        int(r1 + (r2 - r1) * cross_fade),
        int(g1 + (g2 - g1) * cross_fade),
        int(b1 + (b2 - b1) * cross_fade),
    )
    return new_color


if __name__ == "__main__":  # pragma: no cover
    from .console import Console
    from .table import Table
    from .text import Text

    console = Console()

    table = Table(show_footer=False, show_edge=True)
    table.add_column("Color", width=10, overflow="ellipsis")
    table.add_column("Number", justify="right", style="yellow")
    table.add_column("Name", style="green")
    table.add_column("Hex", style="blue")
    table.add_column("RGB", style="magenta")

    colors = sorted((v, k) for k, v in ANSI_COLOR_NAMES.items())
    for color_number, name in colors:
        if "grey" in name:
            continue
        color_cell = Text(" " * 10, style=f"on {name}")
        if color_number < 16:
            table.add_row(color_cell, f"{color_number}", Text(f'"{name}"'))
        else:
            color = EIGHT_BIT_PALETTE[color_number]  # type: ignore[has-type]
            table.add_row(
                color_cell, str(color_number), Text(f'"{name}"'), color.hex, color.rgb
            )

    console.print(table)

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_app.py ===
import asyncio
import logging
import warnings
from functools import lru_cache, partial, update_wrapper
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from aiosignal import Signal
from frozenlist import FrozenList

from . import hdrs
from .abc import (
    AbstractAccessLogger,
    AbstractMatchInfo,
    AbstractRouter,
    AbstractStreamWriter,
)
from .helpers import DEBUG, AppKey
from .http_parser import RawRequestMessage
from .log import web_logger
from .streams import StreamReader
from .typedefs import Handler, Middleware
from .web_exceptions import NotAppKeyWarning
from .web_log import AccessLogger
from .web_middlewares import _fix_request_current_app
from .web_protocol import RequestHandler
from .web_request import Request
from .web_response import StreamResponse
from .web_routedef import AbstractRouteDef
from .web_server import Server
from .web_urldispatcher import (
    AbstractResource,
    AbstractRoute,
    Domain,
    MaskDomain,
    MatchedSubAppResource,
    PrefixedSubAppResource,
    SystemRoute,
    UrlDispatcher,
)

__all__ = ("Application", "CleanupError")


if TYPE_CHECKING:
    _AppSignal = Signal[Callable[["Application"], Awaitable[None]]]
    _RespPrepareSignal = Signal[Callable[[Request, StreamResponse], Awaitable[None]]]
    _Middlewares = FrozenList[Middleware]
    _MiddlewaresHandlers = Optional[Sequence[Tuple[Middleware, bool]]]
    _Subapps = List["Application"]
else:
    # No type checker mode, skip types
    _AppSignal = Signal
    _RespPrepareSignal = Signal
    _Middlewares = FrozenList
    _MiddlewaresHandlers = Optional[Sequence]
    _Subapps = List

_T = TypeVar("_T")
_U = TypeVar("_U")
_Resource = TypeVar("_Resource", bound=AbstractResource)


def _build_middlewares(
    handler: Handler, apps: Tuple["Application", ...]
) -> Callable[[Request], Awaitable[StreamResponse]]:
    """Apply middlewares to handler."""
    for app in apps[::-1]:
        for m, _ in app._middlewares_handlers:  # type: ignore[union-attr]
            handler = update_wrapper(partial(m, handler=handler), handler)
    return handler


_cached_build_middleware = lru_cache(maxsize=1024)(_build_middlewares)


class Application(MutableMapping[Union[str, AppKey[Any]], Any]):
    ATTRS = frozenset(
        [
            "logger",
            "_debug",
            "_router",
            "_loop",
            "_handler_args",
            "_middlewares",
            "_middlewares_handlers",
            "_has_legacy_middlewares",
            "_run_middlewares",
            "_state",
            "_frozen",
            "_pre_frozen",
            "_subapps",
            "_on_response_prepare",
            "_on_startup",
            "_on_shutdown",
            "_on_cleanup",
            "_client_max_size",
            "_cleanup_ctx",
        ]
    )

    def __init__(
        self,
        *,
        logger: logging.Logger = web_logger,
        router: Optional[UrlDispatcher] = None,
        middlewares: Iterable[Middleware] = (),
        handler_args: Optional[Mapping[str, Any]] = None,
        client_max_size: int = 1024**2,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        debug: Any = ...,  # mypy doesn't support ellipsis
    ) -> None:
        if router is None:
            router = UrlDispatcher()
        else:
            warnings.warn(
                "router argument is deprecated", DeprecationWarning, stacklevel=2
            )
        assert isinstance(router, AbstractRouter), router

        if loop is not None:
            warnings.warn(
                "loop argument is deprecated", DeprecationWarning, stacklevel=2
            )

        if debug is not ...:
            warnings.warn(
                "debug argument is deprecated", DeprecationWarning, stacklevel=2
            )
        self._debug = debug
        self._router: UrlDispatcher = router
        self._loop = loop
        self._handler_args = handler_args
        self.logger = logger

        self._middlewares: _Middlewares = FrozenList(middlewares)

        # initialized on freezing
        self._middlewares_handlers: _MiddlewaresHandlers = None
        # initialized on freezing
        self._run_middlewares: Optional[bool] = None
        self._has_legacy_middlewares: bool = True

        self._state: Dict[Union[AppKey[Any], str], object] = {}
        self._frozen = False
        self._pre_frozen = False
        self._subapps: _Subapps = []

        self._on_response_prepare: _RespPrepareSignal = Signal(self)
        self._on_startup: _AppSignal = Signal(self)
        self._on_shutdown: _AppSignal = Signal(self)
        self._on_cleanup: _AppSignal = Signal(self)
        self._cleanup_ctx = CleanupContext()
        self._on_startup.append(self._cleanup_ctx._on_startup)
        self._on_cleanup.append(self._cleanup_ctx._on_cleanup)
        self._client_max_size = client_max_size

    def __init_subclass__(cls: Type["Application"]) -> None:
        warnings.warn(
            "Inheritance class {} from web.Application "
            "is discouraged".format(cls.__name__),
            DeprecationWarning,
            stacklevel=3,
        )

    if DEBUG:  # pragma: no cover

        def __setattr__(self, name: str, val: Any) -> None:
            if name not in self.ATTRS:
                warnings.warn(
                    "Setting custom web.Application.{} attribute "
                    "is discouraged".format(name),
                    DeprecationWarning,
                    stacklevel=2,
                )
            super().__setattr__(name, val)

    # MutableMapping API

    def __eq__(self, other: object) -> bool:
        return self is other

    @overload  # type: ignore[override]
    def __getitem__(self, key: AppKey[_T]) -> _T: ...

    @overload
    def __getitem__(self, key: str) -> Any: ...

    def __getitem__(self, key: Union[str, AppKey[_T]]) -> Any:
        return self._state[key]

    def _check_frozen(self) -> None:
        if self._frozen:
            warnings.warn(
                "Changing state of started or joined application is deprecated",
                DeprecationWarning,
                stacklevel=3,
            )

    @overload  # type: ignore[override]
    def __setitem__(self, key: AppKey[_T], value: _T) -> None: ...

    @overload
    def __setitem__(self, key: str, value: Any) -> None: ...

    def __setitem__(self, key: Union[str, AppKey[_T]], value: Any) -> None:
        self._check_frozen()
        if not isinstance(key, AppKey):
            warnings.warn(
                "It is recommended to use web.AppKey instances for keys.\n"
                + "https://docs.aiohttp.org/en/stable/web_advanced.html"
                + "#application-s-config",
                category=NotAppKeyWarning,
                stacklevel=2,
            )
        self._state[key] = value

    def __delitem__(self, key: Union[str, AppKey[_T]]) -> None:
        self._check_frozen()
        del self._state[key]

    def __len__(self) -> int:
        return len(self._state)

    def __iter__(self) -> Iterator[Union[str, AppKey[Any]]]:
        return iter(self._state)

    def __hash__(self) -> int:
        return id(self)

    @overload  # type: ignore[override]
    def get(self, key: AppKey[_T], default: None = ...) -> Optional[_T]: ...

    @overload
    def get(self, key: AppKey[_T], default: _U) -> Union[_T, _U]: ...

    @overload
    def get(self, key: str, default: Any = ...) -> Any: ...

    def get(self, key: Union[str, AppKey[_T]], default: Any = None) -> Any:
        return self._state.get(key, default)

    ########
    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        # Technically the loop can be None
        # but we mask it by explicit type cast
        # to provide more convenient type annotation
        warnings.warn("loop property is deprecated", DeprecationWarning, stacklevel=2)
        return cast(asyncio.AbstractEventLoop, self._loop)

    def _set_loop(self, loop: Optional[asyncio.AbstractEventLoop]) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError(
                "web.Application instance initialized with different loop"
            )

        self._loop = loop

        # set loop debug
        if self._debug is ...:
            self._debug = loop.get_debug()

        # set loop to sub applications
        for subapp in self._subapps:
            subapp._set_loop(loop)

    @property
    def pre_frozen(self) -> bool:
        return self._pre_frozen

    def pre_freeze(self) -> None:
        if self._pre_frozen:
            return

        self._pre_frozen = True
        self._middlewares.freeze()
        self._router.freeze()
        self._on_response_prepare.freeze()
        self._cleanup_ctx.freeze()
        self._on_startup.freeze()
        self._on_shutdown.freeze()
        self._on_cleanup.freeze()
        self._middlewares_handlers = tuple(self._prepare_middleware())
        self._has_legacy_middlewares = any(
            not new_style for _, new_style in self._middlewares_handlers
        )

        # If current app and any subapp do not have middlewares avoid run all
        # of the code footprint that it implies, which have a middleware
        # hardcoded per app that sets up the current_app attribute. If no
        # middlewares are configured the handler will receive the proper
        # current_app without needing all of this code.
        self._run_middlewares = True if self.middlewares else False

        for subapp in self._subapps:
            subapp.pre_freeze()
            self._run_middlewares = self._run_middlewares or subapp._run_middlewares

    @property
    def frozen(self) -> bool:
        return self._frozen

    def freeze(self) -> None:
        if self._frozen:
            return

        self.pre_freeze()
        self._frozen = True
        for subapp in self._subapps:
            subapp.freeze()

    @property
    def debug(self) -> bool:
        warnings.warn("debug property is deprecated", DeprecationWarning, stacklevel=2)
        return self._debug  # type: ignore[no-any-return]

    def _reg_subapp_signals(self, subapp: "Application") -> None:
        def reg_handler(signame: str) -> None:
            subsig = getattr(subapp, signame)

            async def handler(app: "Application") -> None:
                await subsig.send(subapp)

            appsig = getattr(self, signame)
            appsig.append(handler)

        reg_handler("on_startup")
        reg_handler("on_shutdown")
        reg_handler("on_cleanup")

    def add_subapp(self, prefix: str, subapp: "Application") -> PrefixedSubAppResource:
        if not isinstance(prefix, str):
            raise TypeError("Prefix must be str")
        prefix = prefix.rstrip("/")
        if not prefix:
            raise ValueError("Prefix cannot be empty")
        factory = partial(PrefixedSubAppResource, prefix, subapp)
        return self._add_subapp(factory, subapp)

    def _add_subapp(
        self, resource_factory: Callable[[], _Resource], subapp: "Application"
    ) -> _Resource:
        if self.frozen:
            raise RuntimeError("Cannot add sub application to frozen application")
        if subapp.frozen:
            raise RuntimeError("Cannot add frozen application")
        resource = resource_factory()
        self.router.register_resource(resource)
        self._reg_subapp_signals(subapp)
        self._subapps.append(subapp)
        subapp.pre_freeze()
        if self._loop is not None:
            subapp._set_loop(self._loop)
        return resource

    def add_domain(self, domain: str, subapp: "Application") -> MatchedSubAppResource:
        if not isinstance(domain, str):
            raise TypeError("Domain must be str")
        elif "*" in domain:
            rule: Domain = MaskDomain(domain)
        else:
            rule = Domain(domain)
        factory = partial(MatchedSubAppResource, rule, subapp)
        return self._add_subapp(factory, subapp)

    def add_routes(self, routes: Iterable[AbstractRouteDef]) -> List[AbstractRoute]:
        return self.router.add_routes(routes)

    @property
    def on_response_prepare(self) -> _RespPrepareSignal:
        return self._on_response_prepare

    @property
    def on_startup(self) -> _AppSignal:
        return self._on_startup

    @property
    def on_shutdown(self) -> _AppSignal:
        return self._on_shutdown

    @property
    def on_cleanup(self) -> _AppSignal:
        return self._on_cleanup

    @property
    def cleanup_ctx(self) -> "CleanupContext":
        return self._cleanup_ctx

    @property
    def router(self) -> UrlDispatcher:
        return self._router

    @property
    def middlewares(self) -> _Middlewares:
        return self._middlewares

    def _make_handler(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        access_log_class: Type[AbstractAccessLogger] = AccessLogger,
        **kwargs: Any,
    ) -> Server:

        if not issubclass(access_log_class, AbstractAccessLogger):
            raise TypeError(
                "access_log_class must be subclass of "
                "aiohttp.abc.AbstractAccessLogger, got {}".format(access_log_class)
            )

        self._set_loop(loop)
        self.freeze()

        kwargs["debug"] = self._debug
        kwargs["access_log_class"] = access_log_class
        if self._handler_args:
            for k, v in self._handler_args.items():
                kwargs[k] = v

        return Server(
            self._handle,  # type: ignore[arg-type]
            request_factory=self._make_request,
            loop=self._loop,
            **kwargs,
        )

    def make_handler(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        access_log_class: Type[AbstractAccessLogger] = AccessLogger,
        **kwargs: Any,
    ) -> Server:

        warnings.warn(
            "Application.make_handler(...) is deprecated, use AppRunner API instead",
            DeprecationWarning,
            stacklevel=2,
        )

        return self._make_handler(
            loop=loop, access_log_class=access_log_class, **kwargs
        )

    async def startup(self) -> None:
        """Causes on_startup signal

        Should be called in the event loop along with the request handler.
        """
        await self.on_startup.send(self)

    async def shutdown(self) -> None:
        """Causes on_shutdown signal

        Should be called before cleanup()
        """
        await self.on_shutdown.send(self)

    async def cleanup(self) -> None:
        """Causes on_cleanup signal

        Should be called after shutdown()
        """
        if self.on_cleanup.frozen:
            await self.on_cleanup.send(self)
        else:
            # If an exception occurs in startup, ensure cleanup contexts are completed.
            await self._cleanup_ctx._on_cleanup(self)

    def _make_request(
        self,
        message: RawRequestMessage,
        payload: StreamReader,
        protocol: RequestHandler,
        writer: AbstractStreamWriter,
        task: "asyncio.Task[None]",
        _cls: Type[Request] = Request,
    ) -> Request:
        if TYPE_CHECKING:
            assert self._loop is not None
        return _cls(
            message,
            payload,
            protocol,
            writer,
            task,
            self._loop,
            client_max_size=self._client_max_size,
        )

    def _prepare_middleware(self) -> Iterator[Tuple[Middleware, bool]]:
        for m in reversed(self._middlewares):
            if getattr(m, "__middleware_version__", None) == 1:
                yield m, True
            else:
                warnings.warn(
                    f'old-style middleware "{m!r}" deprecated, see #2252',
                    DeprecationWarning,
                    stacklevel=2,
                )
                yield m, False

        yield _fix_request_current_app(self), True

    async def _handle(self, request: Request) -> StreamResponse:
        loop = asyncio.get_event_loop()
        debug = loop.get_debug()
        match_info = await self._router.resolve(request)
        if debug:  # pragma: no cover
            if not isinstance(match_info, AbstractMatchInfo):
                raise TypeError(
                    "match_info should be AbstractMatchInfo "
                    "instance, not {!r}".format(match_info)
                )
        match_info.add_app(self)

        match_info.freeze()

        request._match_info = match_info

        if request.headers.get(hdrs.EXPECT):
            resp = await match_info.expect_handler(request)
            await request.writer.drain()
            if resp is not None:
                return resp

        handler = match_info.handler

        if self._run_middlewares:
            # If its a SystemRoute, don't cache building the middlewares since
            # they are constructed for every MatchInfoError as a new handler
            # is made each time.
            if not self._has_legacy_middlewares and not isinstance(
                match_info.route, SystemRoute
            ):
                handler = _cached_build_middleware(handler, match_info.apps)
            else:
                for app in match_info.apps[::-1]:
                    for m, new_style in app._middlewares_handlers:  # type: ignore[union-attr]
                        if new_style:
                            handler = update_wrapper(
                                partial(m, handler=handler), handler
                            )
                        else:
                            handler = await m(app, handler)  # type: ignore[arg-type,assignment]

        return await handler(request)

    def __call__(self) -> "Application":
        """gunicorn compatibility"""
        return self

    def __repr__(self) -> str:
        return f"<Application 0x{id(self):x}>"

    def __bool__(self) -> bool:
        return True


class CleanupError(RuntimeError):
    @property
    def exceptions(self) -> List[BaseException]:
        return cast(List[BaseException], self.args[1])


if TYPE_CHECKING:
    _CleanupContextBase = FrozenList[Callable[[Application], AsyncIterator[None]]]
else:
    _CleanupContextBase = FrozenList


class CleanupContext(_CleanupContextBase):
    def __init__(self) -> None:
        super().__init__()
        self._exits: List[AsyncIterator[None]] = []

    async def _on_startup(self, app: Application) -> None:
        for cb in self:
            it = cb(app).__aiter__()
            await it.__anext__()
            self._exits.append(it)

    async def _on_cleanup(self, app: Application) -> None:
        errors = []
        for it in reversed(self._exits):
            try:
                await it.__anext__()
            except StopAsyncIteration:
                pass
            except (Exception, asyncio.CancelledError) as exc:
                errors.append(exc)
            else:
                errors.append(RuntimeError(f"{it!r} has more than one 'yield'"))
        if errors:
            if len(errors) == 1:
                raise errors[0]
            else:
                raise CleanupError("Multiple errors on cleanup stage", errors)

# === NexusCore/openenv\Lib\site-packages\debugpy\adapter\servers.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

import debugpy
from debugpy import adapter
from debugpy.common import json, log, messaging, sockets
from debugpy.adapter import components, sessions
import traceback
import io

access_token = None
"""Access token used to authenticate with the servers."""

listener = None
"""Listener socket that accepts server connections."""

_lock = threading.RLock()

_connections = []
"""All servers that are connected to this adapter, in order in which they connected.
"""

_connections_changed = threading.Event()


class Connection(object):
    """A debug server that is connected to the adapter.

    Servers that are not participating in a debug session are managed directly by the
    corresponding Connection instance.

    Servers that are participating in a debug session are managed by that sessions's
    Server component instance, but Connection object remains, and takes over again
    once the session ends.
    """

    disconnected: bool

    process_replaced: bool
    """Whether this is a connection to a process that is being replaced in situ
    by another process, e.g. via exec().
    """

    server: Server | None
    """The Server component, if this debug server belongs to Session.
    """

    pid: int | None

    ppid: int | None

    channel: messaging.JsonMessageChannel

    def __init__(self, sock):
        from debugpy.adapter import sessions

        self.disconnected = False

        self.process_replaced = False

        self.server = None

        self.pid = None

        stream = messaging.JsonIOStream.from_socket(sock, str(self))
        self.channel = messaging.JsonMessageChannel(stream, self)
        self.channel.start()

        try:
            self.authenticate()
            info = self.channel.request("pydevdSystemInfo")
            process_info = info("process", json.object())
            self.pid = process_info("pid", int)
            self.ppid = process_info("ppid", int, optional=True)
            if self.ppid == ():
                self.ppid = None
            self.channel.name = stream.name = str(self)

            with _lock:
                # The server can disconnect concurrently before we get here, e.g. if
                # it was force-killed. If the disconnect() handler has already run,
                # don't register this server or report it, since there's nothing to
                # deregister it.
                if self.disconnected:
                    return

                # An existing connection with the same PID and process_replaced == True
                # corresponds to the process that replaced itself with this one, so it's
                # not an error.
                if any(
                    conn.pid == self.pid and not conn.process_replaced
                    for conn in _connections
                ):
                    raise KeyError(f"{self} is already connected to this adapter")

                is_first_server = len(_connections) == 0
                _connections.append(self)
                _connections_changed.set()

        except Exception:
            log.swallow_exception("Failed to accept incoming server connection:")
            self.channel.close()

            # If this was the first server to connect, and the main thread is inside
            # wait_until_disconnected(), we want to unblock it and allow it to exit.
            dont_wait_for_first_connection()

            # If we couldn't retrieve all the necessary info from the debug server,
            # or there's a PID clash, we don't want to track this debuggee anymore,
            # but we want to continue accepting connections.
            return

        parent_session = sessions.get(self.ppid)
        if parent_session is None:
            parent_session = sessions.get(self.pid)
        if parent_session is None:
            log.info("No active debug session for parent process of {0}.", self)
        else:
            if self.pid == parent_session.pid:
                parent_server = parent_session.server
                if not (parent_server and parent_server.connection.process_replaced):
                    log.error("{0} is not expecting replacement.", parent_session)
                    self.channel.close()
                    return
            try:
                parent_session.client.notify_of_subprocess(self)
                return
            except Exception:
                # This might fail if the client concurrently disconnects from the parent
                # session. We still want to keep the connection around, in case the
                # client reconnects later. If the parent session was "launch", it'll take
                # care of closing the remaining server connections.
                log.swallow_exception(
                    "Failed to notify parent session about {0}:", self
                )

        # If we got to this point, the subprocess notification was either not sent,
        # or not delivered successfully. For the first server, this is expected, since
        # it corresponds to the root process, and there is no other debug session to
        # notify. But subsequent server connections represent subprocesses, and those
        # will not start running user code until the client tells them to. Since there
        # isn't going to be a client without the notification, such subprocesses have
        # to be unblocked.
        if is_first_server:
            return
        log.info("No clients to wait for - unblocking {0}.", self)
        try:
            self.channel.request("initialize", {"adapterID": "debugpy"})
            self.channel.request("attach", {"subProcessId": self.pid})
            self.channel.request("configurationDone")
            self.channel.request("disconnect")
        except Exception:
            log.swallow_exception("Failed to unblock orphaned subprocess:")
            self.channel.close()

    def __str__(self):
        return "Server" + ("[?]" if self.pid is None else f"[pid={self.pid}]")

    def authenticate(self):
        if access_token is None and adapter.access_token is None:
            return
        auth = self.channel.request(
            "pydevdAuthorize", {"debugServerAccessToken": access_token}
        )
        if auth["clientAccessToken"] != adapter.access_token:
            self.channel.close()
            raise RuntimeError('Mismatched "clientAccessToken"; server not authorized.')

    def request(self, request):
        raise request.isnt_valid(
            "Requests from the debug server to the client are not allowed."
        )

    def event(self, event):
        pass

    def terminated_event(self, event):
        self.channel.close()

    def disconnect(self):
        with _lock:
            self.disconnected = True
            if self.server is not None:
                # If the disconnect happened while Server was being instantiated,
                # we need to tell it, so that it can clean up via Session.finalize().
                # It will also take care of deregistering the connection in that case.
                self.server.disconnect()
            elif self in _connections:
                _connections.remove(self)
                _connections_changed.set()

    def attach_to_session(self, session):
        """Attaches this server to the specified Session as a Server component.

        Raises ValueError if the server already belongs to some session.
        """

        with _lock:
            if self.server is not None:
                raise ValueError
            log.info("Attaching {0} to {1}", self, session)
            self.server = Server(session, self)


class Server(components.Component):
    """Handles the debug server side of a debug session."""

    message_handler = components.Component.message_handler

    connection: Connection

    class Capabilities(components.Capabilities):
        PROPERTIES = {
            "supportsCompletionsRequest": False,
            "supportsConditionalBreakpoints": False,
            "supportsConfigurationDoneRequest": False,
            "supportsDataBreakpoints": False,
            "supportsDelayedStackTraceLoading": False,
            "supportsDisassembleRequest": False,
            "supportsEvaluateForHovers": False,
            "supportsExceptionInfoRequest": False,
            "supportsExceptionOptions": False,
            "supportsFunctionBreakpoints": False,
            "supportsGotoTargetsRequest": False,
            "supportsHitConditionalBreakpoints": False,
            "supportsLoadedSourcesRequest": False,
            "supportsLogPoints": False,
            "supportsModulesRequest": False,
            "supportsReadMemoryRequest": False,
            "supportsRestartFrame": False,
            "supportsRestartRequest": False,
            "supportsSetExpression": False,
            "supportsSetVariable": False,
            "supportsStepBack": False,
            "supportsStepInTargetsRequest": False,
            "supportsTerminateRequest": True,
            "supportsTerminateThreadsRequest": False,
            "supportsValueFormattingOptions": False,
            "exceptionBreakpointFilters": [],
            "additionalModuleColumns": [],
            "supportedChecksumAlgorithms": [],
        }

    def __init__(self, session, connection):
        assert connection.server is None
        with session:
            assert not session.server
            super().__init__(session, channel=connection.channel)

            self.connection = connection

            assert self.session.pid is None
            if self.session.launcher and self.session.launcher.pid != self.pid:
                log.info(
                    "Launcher reported PID={0}, but server reported PID={1}",
                    self.session.launcher.pid,
                    self.pid,
                )
            self.session.pid = self.pid

            session.server = self

    @property
    def pid(self):
        """Process ID of the debuggee process, as reported by the server."""
        return self.connection.pid

    @property
    def ppid(self):
        """Parent process ID of the debuggee process, as reported by the server."""
        return self.connection.ppid

    def initialize(self, request):
        assert request.is_request("initialize")
        self.connection.authenticate()
        request = self.channel.propagate(request)
        request.wait_for_response()
        self.capabilities = self.Capabilities(self, request.response)

    # Generic request handler, used if there's no specific handler below.
    @message_handler
    def request(self, request):
        # Do not delegate requests from the server by default. There is a security
        # boundary between the server and the adapter, and we cannot trust arbitrary
        # requests sent over that boundary, since they may contain arbitrary code
        # that the client will execute - e.g. "runInTerminal". The adapter must only
        # propagate requests that it knows are safe.
        raise request.isnt_valid(
            "Requests from the debug server to the client are not allowed."
        )

    # Generic event handler, used if there's no specific handler below.
    @message_handler
    def event(self, event):
        self.client.propagate_after_start(event)

    @message_handler
    def initialized_event(self, event):
        # pydevd doesn't send it, but the adapter will send its own in any case.
        pass

    @message_handler
    def process_event(self, event):
        # If there is a launcher, it's handling the process event.
        if not self.launcher:
            self.client.propagate_after_start(event)

    @message_handler
    def continued_event(self, event):
        # https://github.com/microsoft/ptvsd/issues/1530
        #
        # DAP specification says that a step request implies that only the thread on
        # which that step occurred is resumed for the duration of the step. However,
        # for VS compatibility, pydevd can operate in a mode that resumes all threads
        # instead. This is set according to the value of "steppingResumesAllThreads"
        # in "launch" or "attach" request, which defaults to true. If explicitly set
        # to false, pydevd will only resume the thread that was stepping.
        #
        # To ensure that the client is aware that other threads are getting resumed in
        # that mode, pydevd sends a "continued" event with "allThreadsResumed": true.
        # when responding to a step request. This ensures correct behavior in VSCode
        # and other DAP-conformant clients.
        #
        # On the other hand, VS does not follow the DAP specification in this regard.
        # When it requests a step, it assumes that all threads will be resumed, and
        # does not expect to see "continued" events explicitly reflecting that fact.
        # If such events are sent regardless, VS behaves erratically. Thus, we have
        # to suppress them specifically for VS.
        if self.client.client_id not in ("visualstudio", "vsformac"):
            self.client.propagate_after_start(event)

    @message_handler
    def exited_event(self, event: messaging.Event):
        if event("pydevdReason", str, optional=True) == "processReplaced":
            # The parent process used some API like exec() that replaced it with another
            # process in situ. The connection will shut down immediately afterwards, but
            # we need to keep the corresponding session alive long enough to report the
            # subprocess to it.
            self.connection.process_replaced = True
        else:
            # If there is a launcher, it's handling the exit code.
            if not self.launcher:
                self.client.propagate_after_start(event)

    @message_handler
    def terminated_event(self, event):
        # Do not propagate this, since we'll report our own.
        self.channel.close()

    def detach_from_session(self):
        with _lock:
            self.is_connected = False
            self.channel.handlers = self.connection
            self.channel.name = self.channel.stream.name = str(self.connection)
            self.connection.server = None

    def disconnect(self):
        if self.connection.process_replaced:
            # Wait for the replacement server to connect to the adapter, and to report
            # itself to the client for this session if there is one.
            log.info("{0} is waiting for replacement subprocess.", self)
            session = self.session
            if not session.client or not session.client.is_connected:
                wait_for_connection(
                    session, lambda conn: conn.pid == self.pid, timeout=60
                )
            else:
                self.wait_for(
                    lambda: (
                        not session.client
                        or not session.client.is_connected
                        or any(
                            conn.pid == self.pid
                            for conn in session.client.known_subprocesses
                        )
                    ),
                    timeout=60,
                )
        with _lock:
            _connections.remove(self.connection)
            _connections_changed.set()
        super().disconnect()


def serve(host="127.0.0.1", port=0):
    global listener
    listener = sockets.serve("Server", Connection, host, port)
    sessions.report_sockets()
    return listener.getsockname()


def is_serving():
    return listener is not None


def stop_serving():
    global listener
    try:
        if listener is not None:
            listener.close()
            listener = None
    except Exception:
        log.swallow_exception(level="warning")
    sessions.report_sockets()


def connections():
    with _lock:
        return list(_connections)


def wait_for_connection(session, predicate, timeout=None):
    """Waits until there is a server matching the specified predicate connected to
    this adapter, and returns the corresponding Connection.

    If there is more than one server connection already available, returns the oldest
    one.
    """

    def wait_for_timeout():
        time.sleep(timeout)
        wait_for_timeout.timed_out = True
        with _lock:
            _connections_changed.set()

    wait_for_timeout.timed_out = timeout == 0
    if timeout:
        thread = threading.Thread(
            target=wait_for_timeout, name="servers.wait_for_connection() timeout"
        )
        thread.daemon = True
        thread.start()

    if timeout != 0:
        log.info("{0} waiting for connection from debug server...", session)
    while True:
        with _lock:
            _connections_changed.clear()
            conns = (conn for conn in _connections if predicate(conn))
            conn = next(conns, None)
            if conn is not None or wait_for_timeout.timed_out:
                return conn
        _connections_changed.wait()


def wait_until_disconnected():
    """Blocks until all debug servers disconnect from the adapter.

    If there are no server connections, waits until at least one is established first,
    before waiting for it to disconnect.
    """
    while True:
        _connections_changed.wait()
        with _lock:
            _connections_changed.clear()
            if not len(_connections):
                return


def dont_wait_for_first_connection():
    """Unblocks any pending wait_until_disconnected() call that is waiting on the
    first server to connect.
    """
    with _lock:
        _connections_changed.set()


def inject(pid, debugpy_args, on_output):
    host, port = listener.getsockname()

    cmdline = [
        sys.executable,
        os.path.dirname(debugpy.__file__),
        "--connect",
        host + ":" + str(port),
    ]
    if adapter.access_token is not None:
        cmdline += ["--adapter-access-token", adapter.access_token]
    cmdline += debugpy_args
    cmdline += ["--pid", str(pid)]

    log.info("Spawning attach-to-PID debugger injector: {0!r}", cmdline)
    try:
        injector = subprocess.Popen(
            cmdline,
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        log.swallow_exception(
            "Failed to inject debug server into process with PID={0}", pid
        )
        raise messaging.MessageHandlingError(
            "Failed to inject debug server into process with PID={0}: {1}".format(
                pid, exc
            )
        )

    # We need to capture the output of the injector - needed so that it doesn't 
    # get blocked on a write() syscall (besides showing it to the user if it
    # is taking longer than expected).

    output_collected = []
    output_collected.append("--- Starting attach to pid: {0} ---\n".format(pid))

    def capture(stream):
        nonlocal output_collected
        try:
            while True:
                line = stream.readline()
                if not line:
                    break
                line = line.decode("utf-8", "replace")
                output_collected.append(line)
                log.info("Injector[PID={0}] output: {1}", pid, line.rstrip())
            log.info("Injector[PID={0}] exited.", pid)
        except Exception:
            s = io.StringIO()
            traceback.print_exc(file=s)
            on_output("stderr", s.getvalue())

    threading.Thread(
        target=capture,
        name=f"Injector[PID={pid}] stdout",
        args=(injector.stdout,),
        daemon=True,
    ).start()

    def info_on_timeout():
        nonlocal output_collected
        taking_longer_than_expected = False
        initial_time = time.time()
        while True:
            time.sleep(1)
            returncode = injector.poll()
            if returncode is not None:
                if returncode != 0:
                    # Something didn't work out. Let's print more info to the user.
                    on_output(
                        "stderr",
                        "Attach to PID failed.\n\n",
                    )
                    
                    old = output_collected
                    output_collected = []
                    contents = "".join(old)
                    on_output("stderr", "".join(contents))
                break

            elapsed = time.time() - initial_time
            on_output(
                "stdout", "Attaching to PID: %s (elapsed: %.2fs).\n" % (pid, elapsed)
            )

            if not taking_longer_than_expected:
                if elapsed > 10:
                    taking_longer_than_expected = True
                    if sys.platform in ("linux", "linux2"):
                        on_output(
                            "stdout",
                            "\nThe attach to PID is taking longer than expected.\n",
                        )
                        on_output(
                            "stdout",
                            "On Linux it's possible to customize the value of\n",
                        )
                        on_output(
                            "stdout",
                            "`PYDEVD_GDB_SCAN_SHARED_LIBRARIES` so that fewer libraries.\n",
                        )
                        on_output(
                            "stdout",
                            "are scanned when searching for the needed symbols.\n\n",
                        )
                        on_output(
                            "stdout",
                            "i.e.: set in your environment variables (and restart your editor/client\n",
                        )
                        on_output(
                            "stdout",
                            "so that it picks up the updated environment variable value):\n\n",
                        )
                        on_output(
                            "stdout",
                            "PYDEVD_GDB_SCAN_SHARED_LIBRARIES=libdl, libltdl, libc, libfreebl3\n\n",
                        )
                        on_output(
                            "stdout",
                            "-- the actual library may be different (the gdb output typically\n",
                        )
                        on_output(
                            "stdout",
                            "-- writes the libraries that will be used, so, it should be possible\n",
                        )
                        on_output(
                            "stdout",
                            "-- to test other libraries if the above doesn't work).\n\n",
                        )
            if taking_longer_than_expected:
                # If taking longer than expected, start showing the actual output to the user.
                old = output_collected
                output_collected = []
                contents = "".join(old)
                if contents:
                    on_output("stderr", contents)                

    threading.Thread(
        target=info_on_timeout, name=f"Injector[PID={pid}] info on timeout", daemon=True
    ).start()

# === NexusCore/openenv\Lib\site-packages\cffi\model.py ===
import types
import weakref

from .lock import allocate_lock
from .error import CDefError, VerificationError, VerificationMissing

# type qualifiers
Q_CONST    = 0x01
Q_RESTRICT = 0x02
Q_VOLATILE = 0x04

def qualify(quals, replace_with):
    if quals & Q_CONST:
        replace_with = ' const ' + replace_with.lstrip()
    if quals & Q_VOLATILE:
        replace_with = ' volatile ' + replace_with.lstrip()
    if quals & Q_RESTRICT:
        # It seems that __restrict is supported by gcc and msvc.
        # If you hit some different compiler, add a #define in
        # _cffi_include.h for it (and in its copies, documented there)
        replace_with = ' __restrict ' + replace_with.lstrip()
    return replace_with


class BaseTypeByIdentity(object):
    is_array_type = False
    is_raw_function = False

    def get_c_name(self, replace_with='', context='a C file', quals=0):
        result = self.c_name_with_marker
        assert result.count('&') == 1
        # some logic duplication with ffi.getctype()... :-(
        replace_with = replace_with.strip()
        if replace_with:
            if replace_with.startswith('*') and '&[' in result:
                replace_with = '(%s)' % replace_with
            elif not replace_with[0] in '[(':
                replace_with = ' ' + replace_with
        replace_with = qualify(quals, replace_with)
        result = result.replace('&', replace_with)
        if '$' in result:
            raise VerificationError(
                "cannot generate '%s' in %s: unknown type name"
                % (self._get_c_name(), context))
        return result

    def _get_c_name(self):
        return self.c_name_with_marker.replace('&', '')

    def has_c_name(self):
        return '$' not in self._get_c_name()

    def is_integer_type(self):
        return False

    def get_cached_btype(self, ffi, finishlist, can_delay=False):
        try:
            BType = ffi._cached_btypes[self]
        except KeyError:
            BType = self.build_backend_type(ffi, finishlist)
            BType2 = ffi._cached_btypes.setdefault(self, BType)
            assert BType2 is BType
        return BType

    def __repr__(self):
        return '<%s>' % (self._get_c_name(),)

    def _get_items(self):
        return [(name, getattr(self, name)) for name in self._attrs_]


class BaseType(BaseTypeByIdentity):

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self._get_items() == other._get_items())

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.__class__, tuple(self._get_items())))


class VoidType(BaseType):
    _attrs_ = ()

    def __init__(self):
        self.c_name_with_marker = 'void&'

    def build_backend_type(self, ffi, finishlist):
        return global_cache(self, ffi, 'new_void_type')

void_type = VoidType()


class BasePrimitiveType(BaseType):
    def is_complex_type(self):
        return False


class PrimitiveType(BasePrimitiveType):
    _attrs_ = ('name',)

    ALL_PRIMITIVE_TYPES = {
        'char':               'c',
        'short':              'i',
        'int':                'i',
        'long':               'i',
        'long long':          'i',
        'signed char':        'i',
        'unsigned char':      'i',
        'unsigned short':     'i',
        'unsigned int':       'i',
        'unsigned long':      'i',
        'unsigned long long': 'i',
        'float':              'f',
        'double':             'f',
        'long double':        'f',
        '_cffi_float_complex_t': 'j',
        '_cffi_double_complex_t': 'j',
        '_Bool':              'i',
        # the following types are not primitive in the C sense
        'wchar_t':            'c',
        'char16_t':           'c',
        'char32_t':           'c',
        'int8_t':             'i',
        'uint8_t':            'i',
        'int16_t':            'i',
        'uint16_t':           'i',
        'int32_t':            'i',
        'uint32_t':           'i',
        'int64_t':            'i',
        'uint64_t':           'i',
        'int_least8_t':       'i',
        'uint_least8_t':      'i',
        'int_least16_t':      'i',
        'uint_least16_t':     'i',
        'int_least32_t':      'i',
        'uint_least32_t':     'i',
        'int_least64_t':      'i',
        'uint_least64_t':     'i',
        'int_fast8_t':        'i',
        'uint_fast8_t':       'i',
        'int_fast16_t':       'i',
        'uint_fast16_t':      'i',
        'int_fast32_t':       'i',
        'uint_fast32_t':      'i',
        'int_fast64_t':       'i',
        'uint_fast64_t':      'i',
        'intptr_t':           'i',
        'uintptr_t':          'i',
        'intmax_t':           'i',
        'uintmax_t':          'i',
        'ptrdiff_t':          'i',
        'size_t':             'i',
        'ssize_t':            'i',
        }

    def __init__(self, name):
        assert name in self.ALL_PRIMITIVE_TYPES
        self.name = name
        self.c_name_with_marker = name + '&'

    def is_char_type(self):
        return self.ALL_PRIMITIVE_TYPES[self.name] == 'c'
    def is_integer_type(self):
        return self.ALL_PRIMITIVE_TYPES[self.name] == 'i'
    def is_float_type(self):
        return self.ALL_PRIMITIVE_TYPES[self.name] == 'f'
    def is_complex_type(self):
        return self.ALL_PRIMITIVE_TYPES[self.name] == 'j'

    def build_backend_type(self, ffi, finishlist):
        return global_cache(self, ffi, 'new_primitive_type', self.name)


class UnknownIntegerType(BasePrimitiveType):
    _attrs_ = ('name',)

    def __init__(self, name):
        self.name = name
        self.c_name_with_marker = name + '&'

    def is_integer_type(self):
        return True

    def build_backend_type(self, ffi, finishlist):
        raise NotImplementedError("integer type '%s' can only be used after "
                                  "compilation" % self.name)

class UnknownFloatType(BasePrimitiveType):
    _attrs_ = ('name', )

    def __init__(self, name):
        self.name = name
        self.c_name_with_marker = name + '&'

    def build_backend_type(self, ffi, finishlist):
        raise NotImplementedError("float type '%s' can only be used after "
                                  "compilation" % self.name)


class BaseFunctionType(BaseType):
    _attrs_ = ('args', 'result', 'ellipsis', 'abi')

    def __init__(self, args, result, ellipsis, abi=None):
        self.args = args
        self.result = result
        self.ellipsis = ellipsis
        self.abi = abi
        #
        reprargs = [arg._get_c_name() for arg in self.args]
        if self.ellipsis:
            reprargs.append('...')
        reprargs = reprargs or ['void']
        replace_with = self._base_pattern % (', '.join(reprargs),)
        if abi is not None:
            replace_with = replace_with[:1] + abi + ' ' + replace_with[1:]
        self.c_name_with_marker = (
            self.result.c_name_with_marker.replace('&', replace_with))


class RawFunctionType(BaseFunctionType):
    # Corresponds to a C type like 'int(int)', which is the C type of
    # a function, but not a pointer-to-function.  The backend has no
    # notion of such a type; it's used temporarily by parsing.
    _base_pattern = '(&)(%s)'
    is_raw_function = True

    def build_backend_type(self, ffi, finishlist):
        raise CDefError("cannot render the type %r: it is a function "
                        "type, not a pointer-to-function type" % (self,))

    def as_function_pointer(self):
        return FunctionPtrType(self.args, self.result, self.ellipsis, self.abi)


class FunctionPtrType(BaseFunctionType):
    _base_pattern = '(*&)(%s)'

    def build_backend_type(self, ffi, finishlist):
        result = self.result.get_cached_btype(ffi, finishlist)
        args = []
        for tp in self.args:
            args.append(tp.get_cached_btype(ffi, finishlist))
        abi_args = ()
        if self.abi == "__stdcall":
            if not self.ellipsis:    # __stdcall ignored for variadic funcs
                try:
                    abi_args = (ffi._backend.FFI_STDCALL,)
                except AttributeError:
                    pass
        return global_cache(self, ffi, 'new_function_type',
                            tuple(args), result, self.ellipsis, *abi_args)

    def as_raw_function(self):
        return RawFunctionType(self.args, self.result, self.ellipsis, self.abi)


class PointerType(BaseType):
    _attrs_ = ('totype', 'quals')

    def __init__(self, totype, quals=0):
        self.totype = totype
        self.quals = quals
        extra = " *&"
        if totype.is_array_type:
            extra = "(%s)" % (extra.lstrip(),)
        extra = qualify(quals, extra)
        self.c_name_with_marker = totype.c_name_with_marker.replace('&', extra)

    def build_backend_type(self, ffi, finishlist):
        BItem = self.totype.get_cached_btype(ffi, finishlist, can_delay=True)
        return global_cache(self, ffi, 'new_pointer_type', BItem)

voidp_type = PointerType(void_type)

def ConstPointerType(totype):
    return PointerType(totype, Q_CONST)

const_voidp_type = ConstPointerType(void_type)


class NamedPointerType(PointerType):
    _attrs_ = ('totype', 'name')

    def __init__(self, totype, name, quals=0):
        PointerType.__init__(self, totype, quals)
        self.name = name
        self.c_name_with_marker = name + '&'


class ArrayType(BaseType):
    _attrs_ = ('item', 'length')
    is_array_type = True

    def __init__(self, item, length):
        self.item = item
        self.length = length
        #
        if length is None:
            brackets = '&[]'
        elif length == '...':
            brackets = '&[/*...*/]'
        else:
            brackets = '&[%s]' % length
        self.c_name_with_marker = (
            self.item.c_name_with_marker.replace('&', brackets))

    def length_is_unknown(self):
        return isinstance(self.length, str)

    def resolve_length(self, newlength):
        return ArrayType(self.item, newlength)

    def build_backend_type(self, ffi, finishlist):
        if self.length_is_unknown():
            raise CDefError("cannot render the type %r: unknown length" %
                            (self,))
        self.item.get_cached_btype(ffi, finishlist)   # force the item BType
        BPtrItem = PointerType(self.item).get_cached_btype(ffi, finishlist)
        return global_cache(self, ffi, 'new_array_type', BPtrItem, self.length)

char_array_type = ArrayType(PrimitiveType('char'), None)


class StructOrUnionOrEnum(BaseTypeByIdentity):
    _attrs_ = ('name',)
    forcename = None

    def build_c_name_with_marker(self):
        name = self.forcename or '%s %s' % (self.kind, self.name)
        self.c_name_with_marker = name + '&'

    def force_the_name(self, forcename):
        self.forcename = forcename
        self.build_c_name_with_marker()

    def get_official_name(self):
        assert self.c_name_with_marker.endswith('&')
        return self.c_name_with_marker[:-1]


class StructOrUnion(StructOrUnionOrEnum):
    fixedlayout = None
    completed = 0
    partial = False
    packed = 0

    def __init__(self, name, fldnames, fldtypes, fldbitsize, fldquals=None):
        self.name = name
        self.fldnames = fldnames
        self.fldtypes = fldtypes
        self.fldbitsize = fldbitsize
        self.fldquals = fldquals
        self.build_c_name_with_marker()

    def anonymous_struct_fields(self):
        if self.fldtypes is not None:
            for name, type in zip(self.fldnames, self.fldtypes):
                if name == '' and isinstance(type, StructOrUnion):
                    yield type

    def enumfields(self, expand_anonymous_struct_union=True):
        fldquals = self.fldquals
        if fldquals is None:
            fldquals = (0,) * len(self.fldnames)
        for name, type, bitsize, quals in zip(self.fldnames, self.fldtypes,
                                              self.fldbitsize, fldquals):
            if (name == '' and isinstance(type, StructOrUnion)
                    and expand_anonymous_struct_union):
                # nested anonymous struct/union
                for result in type.enumfields():
                    yield result
            else:
                yield (name, type, bitsize, quals)

    def force_flatten(self):
        # force the struct or union to have a declaration that lists
        # directly all fields returned by enumfields(), flattening
        # nested anonymous structs/unions.
        names = []
        types = []
        bitsizes = []
        fldquals = []
        for name, type, bitsize, quals in self.enumfields():
            names.append(name)
            types.append(type)
            bitsizes.append(bitsize)
            fldquals.append(quals)
        self.fldnames = tuple(names)
        self.fldtypes = tuple(types)
        self.fldbitsize = tuple(bitsizes)
        self.fldquals = tuple(fldquals)

    def get_cached_btype(self, ffi, finishlist, can_delay=False):
        BType = StructOrUnionOrEnum.get_cached_btype(self, ffi, finishlist,
                                                     can_delay)
        if not can_delay:
            self.finish_backend_type(ffi, finishlist)
        return BType

    def finish_backend_type(self, ffi, finishlist):
        if self.completed:
            if self.completed != 2:
                raise NotImplementedError("recursive structure declaration "
                                          "for '%s'" % (self.name,))
            return
        BType = ffi._cached_btypes[self]
        #
        self.completed = 1
        #
        if self.fldtypes is None:
            pass    # not completing it: it's an opaque struct
            #
        elif self.fixedlayout is None:
            fldtypes = [tp.get_cached_btype(ffi, finishlist)
                        for tp in self.fldtypes]
            lst = list(zip(self.fldnames, fldtypes, self.fldbitsize))
            extra_flags = ()
            if self.packed:
                if self.packed == 1:
                    extra_flags = (8,)    # SF_PACKED
                else:
                    extra_flags = (0, self.packed)
            ffi._backend.complete_struct_or_union(BType, lst, self,
                                                  -1, -1, *extra_flags)
            #
        else:
            fldtypes = []
            fieldofs, fieldsize, totalsize, totalalignment = self.fixedlayout
            for i in range(len(self.fldnames)):
                fsize = fieldsize[i]
                ftype = self.fldtypes[i]
                #
                if isinstance(ftype, ArrayType) and ftype.length_is_unknown():
                    # fix the length to match the total size
                    BItemType = ftype.item.get_cached_btype(ffi, finishlist)
                    nlen, nrest = divmod(fsize, ffi.sizeof(BItemType))
                    if nrest != 0:
                        self._verification_error(
                            "field '%s.%s' has a bogus size?" % (
                            self.name, self.fldnames[i] or '{}'))
                    ftype = ftype.resolve_length(nlen)
                    self.fldtypes = (self.fldtypes[:i] + (ftype,) +
                                     self.fldtypes[i+1:])
                #
                BFieldType = ftype.get_cached_btype(ffi, finishlist)
                if isinstance(ftype, ArrayType) and ftype.length is None:
                    assert fsize == 0
                else:
                    bitemsize = ffi.sizeof(BFieldType)
                    if bitemsize != fsize:
                        self._verification_error(
                            "field '%s.%s' is declared as %d bytes, but is "
                            "really %d bytes" % (self.name,
                                                 self.fldnames[i] or '{}',
                                                 bitemsize, fsize))
                fldtypes.append(BFieldType)
            #
            lst = list(zip(self.fldnames, fldtypes, self.fldbitsize, fieldofs))
            ffi._backend.complete_struct_or_union(BType, lst, self,
                                                  totalsize, totalalignment)
        self.completed = 2

    def _verification_error(self, msg):
        raise VerificationError(msg)

    def check_not_partial(self):
        if self.partial and self.fixedlayout is None:
            raise VerificationMissing(self._get_c_name())

    def build_backend_type(self, ffi, finishlist):
        self.check_not_partial()
        finishlist.append(self)
        #
        return global_cache(self, ffi, 'new_%s_type' % self.kind,
                            self.get_official_name(), key=self)


class StructType(StructOrUnion):
    kind = 'struct'


class UnionType(StructOrUnion):
    kind = 'union'


class EnumType(StructOrUnionOrEnum):
    kind = 'enum'
    partial = False
    partial_resolved = False

    def __init__(self, name, enumerators, enumvalues, baseinttype=None):
        self.name = name
        self.enumerators = enumerators
        self.enumvalues = enumvalues
        self.baseinttype = baseinttype
        self.build_c_name_with_marker()

    def force_the_name(self, forcename):
        StructOrUnionOrEnum.force_the_name(self, forcename)
        if self.forcename is None:
            name = self.get_official_name()
            self.forcename = '$' + name.replace(' ', '_')

    def check_not_partial(self):
        if self.partial and not self.partial_resolved:
            raise VerificationMissing(self._get_c_name())

    def build_backend_type(self, ffi, finishlist):
        self.check_not_partial()
        base_btype = self.build_baseinttype(ffi, finishlist)
        return global_cache(self, ffi, 'new_enum_type',
                            self.get_official_name(),
                            self.enumerators, self.enumvalues,
                            base_btype, key=self)

    def build_baseinttype(self, ffi, finishlist):
        if self.baseinttype is not None:
            return self.baseinttype.get_cached_btype(ffi, finishlist)
        #
        if self.enumvalues:
            smallest_value = min(self.enumvalues)
            largest_value = max(self.enumvalues)
        else:
            import warnings
            try:
                # XXX!  The goal is to ensure that the warnings.warn()
                # will not suppress the warning.  We want to get it
                # several times if we reach this point several times.
                __warningregistry__.clear()
            except NameError:
                pass
            warnings.warn("%r has no values explicitly defined; "
                          "guessing that it is equivalent to 'unsigned int'"
                          % self._get_c_name())
            smallest_value = largest_value = 0
        if smallest_value < 0:   # needs a signed type
            sign = 1
            candidate1 = PrimitiveType("int")
            candidate2 = PrimitiveType("long")
        else:
            sign = 0
            candidate1 = PrimitiveType("unsigned int")
            candidate2 = PrimitiveType("unsigned long")
        btype1 = candidate1.get_cached_btype(ffi, finishlist)
        btype2 = candidate2.get_cached_btype(ffi, finishlist)
        size1 = ffi.sizeof(btype1)
        size2 = ffi.sizeof(btype2)
        if (smallest_value >= ((-1) << (8*size1-1)) and
            largest_value < (1 << (8*size1-sign))):
            return btype1
        if (smallest_value >= ((-1) << (8*size2-1)) and
            largest_value < (1 << (8*size2-sign))):
            return btype2
        raise CDefError("%s values don't all fit into either 'long' "
                        "or 'unsigned long'" % self._get_c_name())

def unknown_type(name, structname=None):
    if structname is None:
        structname = '$%s' % name
    tp = StructType(structname, None, None, None)
    tp.force_the_name(name)
    tp.origin = "unknown_type"
    return tp

def unknown_ptr_type(name, structname=None):
    if structname is None:
        structname = '$$%s' % name
    tp = StructType(structname, None, None, None)
    return NamedPointerType(tp, name)


global_lock = allocate_lock()
_typecache_cffi_backend = weakref.WeakValueDictionary()

def get_typecache(backend):
    # returns _typecache_cffi_backend if backend is the _cffi_backend
    # module, or type(backend).__typecache if backend is an instance of
    # CTypesBackend (or some FakeBackend class during tests)
    if isinstance(backend, types.ModuleType):
        return _typecache_cffi_backend
    with global_lock:
        if not hasattr(type(backend), '__typecache'):
            type(backend).__typecache = weakref.WeakValueDictionary()
        return type(backend).__typecache

def global_cache(srctype, ffi, funcname, *args, **kwds):
    key = kwds.pop('key', (funcname, args))
    assert not kwds
    try:
        return ffi._typecache[key]
    except KeyError:
        pass
    try:
        res = getattr(ffi._backend, funcname)(*args)
    except NotImplementedError as e:
        raise NotImplementedError("%s: %r: %s" % (funcname, srctype, e))
    # note that setdefault() on WeakValueDictionary is not atomic
    # and contains a rare bug (http://bugs.python.org/issue19542);
    # we have to use a lock and do it ourselves
    cache = ffi._typecache
    with global_lock:
        res1 = cache.get(key)
        if res1 is None:
            cache[key] = res
            return res
        else:
            return res1

def pointer_cache(ffi, BType):
    return global_cache('?', ffi, 'new_pointer_type', BType)

def attach_exception_info(e, name):
    if e.args and type(e.args[0]) is str:
        e.args = ('%s: %s' % (name, e.args[0]),) + e.args[1:]

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\axes_divider.py ===
"""
Helper classes to adjust the positions of multiple axes at drawing time.
"""

import functools

import numpy as np

import matplotlib as mpl
from matplotlib import _api
from matplotlib.gridspec import SubplotSpec
import matplotlib.transforms as mtransforms
from . import axes_size as Size


class Divider:
    """
    An Axes positioning class.

    The divider is initialized with lists of horizontal and vertical sizes
    (:mod:`mpl_toolkits.axes_grid1.axes_size`) based on which a given
    rectangular area will be divided.

    The `new_locator` method then creates a callable object
    that can be used as the *axes_locator* of the axes.
    """

    def __init__(self, fig, pos, horizontal, vertical,
                 aspect=None, anchor="C"):
        """
        Parameters
        ----------
        fig : Figure
        pos : tuple of 4 floats
            Position of the rectangle that will be divided.
        horizontal : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`
            Sizes for horizontal division.
        vertical : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`
            Sizes for vertical division.
        aspect : bool, optional
            Whether overall rectangular area is reduced so that the relative
            part of the horizontal and vertical scales have the same scale.
        anchor : (float, float) or {'C', 'SW', 'S', 'SE', 'E', 'NE', 'N', \
'NW', 'W'}, default: 'C'
            Placement of the reduced rectangle, when *aspect* is True.
        """

        self._fig = fig
        self._pos = pos
        self._horizontal = horizontal
        self._vertical = vertical
        self._anchor = anchor
        self.set_anchor(anchor)
        self._aspect = aspect
        self._xrefindex = 0
        self._yrefindex = 0
        self._locator = None

    def get_horizontal_sizes(self, renderer):
        return np.array([s.get_size(renderer) for s in self.get_horizontal()])

    def get_vertical_sizes(self, renderer):
        return np.array([s.get_size(renderer) for s in self.get_vertical()])

    def set_position(self, pos):
        """
        Set the position of the rectangle.

        Parameters
        ----------
        pos : tuple of 4 floats
            position of the rectangle that will be divided
        """
        self._pos = pos

    def get_position(self):
        """Return the position of the rectangle."""
        return self._pos

    def set_anchor(self, anchor):
        """
        Parameters
        ----------
        anchor : (float, float) or {'C', 'SW', 'S', 'SE', 'E', 'NE', 'N', \
'NW', 'W'}
            Either an (*x*, *y*) pair of relative coordinates (0 is left or
            bottom, 1 is right or top), 'C' (center), or a cardinal direction
            ('SW', southwest, is bottom left, etc.).

        See Also
        --------
        .Axes.set_anchor
        """
        if isinstance(anchor, str):
            _api.check_in_list(mtransforms.Bbox.coefs, anchor=anchor)
        elif not isinstance(anchor, (tuple, list)) or len(anchor) != 2:
            raise TypeError("anchor must be str or 2-tuple")
        self._anchor = anchor

    def get_anchor(self):
        """Return the anchor."""
        return self._anchor

    def get_subplotspec(self):
        return None

    def set_horizontal(self, h):
        """
        Parameters
        ----------
        h : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`
            sizes for horizontal division
        """
        self._horizontal = h

    def get_horizontal(self):
        """Return horizontal sizes."""
        return self._horizontal

    def set_vertical(self, v):
        """
        Parameters
        ----------
        v : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`
            sizes for vertical division
        """
        self._vertical = v

    def get_vertical(self):
        """Return vertical sizes."""
        return self._vertical

    def set_aspect(self, aspect=False):
        """
        Parameters
        ----------
        aspect : bool
        """
        self._aspect = aspect

    def get_aspect(self):
        """Return aspect."""
        return self._aspect

    def set_locator(self, _locator):
        self._locator = _locator

    def get_locator(self):
        return self._locator

    def get_position_runtime(self, ax, renderer):
        if self._locator is None:
            return self.get_position()
        else:
            return self._locator(ax, renderer).bounds

    @staticmethod
    def _calc_k(sizes, total):
        # sizes is a (n, 2) array of (rel_size, abs_size); this method finds
        # the k factor such that sum(rel_size * k + abs_size) == total.
        rel_sum, abs_sum = sizes.sum(0)
        return (total - abs_sum) / rel_sum if rel_sum else 0

    @staticmethod
    def _calc_offsets(sizes, k):
        # Apply k factors to (n, 2) sizes array of (rel_size, abs_size); return
        # the resulting cumulative offset positions.
        return np.cumsum([0, *(sizes @ [k, 1])])

    def new_locator(self, nx, ny, nx1=None, ny1=None):
        """
        Return an axes locator callable for the specified cell.

        Parameters
        ----------
        nx, nx1 : int
            Integers specifying the column-position of the
            cell. When *nx1* is None, a single *nx*-th column is
            specified. Otherwise, location of columns spanning between *nx*
            to *nx1* (but excluding *nx1*-th column) is specified.
        ny, ny1 : int
            Same as *nx* and *nx1*, but for row positions.
        """
        if nx1 is None:
            nx1 = nx + 1
        if ny1 is None:
            ny1 = ny + 1
        # append_size("left") adds a new size at the beginning of the
        # horizontal size lists; this shift transforms e.g.
        # new_locator(nx=2, ...) into effectively new_locator(nx=3, ...).  To
        # take that into account, instead of recording nx, we record
        # nx-self._xrefindex, where _xrefindex is shifted by 1 by each
        # append_size("left"), and re-add self._xrefindex back to nx in
        # _locate, when the actual axes position is computed.  Ditto for y.
        xref = self._xrefindex
        yref = self._yrefindex
        locator = functools.partial(
            self._locate, nx - xref, ny - yref, nx1 - xref, ny1 - yref)
        locator.get_subplotspec = self.get_subplotspec
        return locator

    def _locate(self, nx, ny, nx1, ny1, axes, renderer):
        """
        Implementation of ``divider.new_locator().__call__``.

        The axes locator callable returned by ``new_locator()`` is created as
        a `functools.partial` of this method with *nx*, *ny*, *nx1*, and *ny1*
        specifying the requested cell.
        """
        nx += self._xrefindex
        nx1 += self._xrefindex
        ny += self._yrefindex
        ny1 += self._yrefindex

        fig_w, fig_h = self._fig.bbox.size / self._fig.dpi
        x, y, w, h = self.get_position_runtime(axes, renderer)

        hsizes = self.get_horizontal_sizes(renderer)
        vsizes = self.get_vertical_sizes(renderer)
        k_h = self._calc_k(hsizes, fig_w * w)
        k_v = self._calc_k(vsizes, fig_h * h)

        if self.get_aspect():
            k = min(k_h, k_v)
            ox = self._calc_offsets(hsizes, k)
            oy = self._calc_offsets(vsizes, k)

            ww = (ox[-1] - ox[0]) / fig_w
            hh = (oy[-1] - oy[0]) / fig_h
            pb = mtransforms.Bbox.from_bounds(x, y, w, h)
            pb1 = mtransforms.Bbox.from_bounds(x, y, ww, hh)
            x0, y0 = pb1.anchored(self.get_anchor(), pb).p0

        else:
            ox = self._calc_offsets(hsizes, k_h)
            oy = self._calc_offsets(vsizes, k_v)
            x0, y0 = x, y

        if nx1 is None:
            nx1 = -1
        if ny1 is None:
            ny1 = -1

        x1, w1 = x0 + ox[nx] / fig_w, (ox[nx1] - ox[nx]) / fig_w
        y1, h1 = y0 + oy[ny] / fig_h, (oy[ny1] - oy[ny]) / fig_h

        return mtransforms.Bbox.from_bounds(x1, y1, w1, h1)

    def append_size(self, position, size):
        _api.check_in_list(["left", "right", "bottom", "top"],
                           position=position)
        if position == "left":
            self._horizontal.insert(0, size)
            self._xrefindex += 1
        elif position == "right":
            self._horizontal.append(size)
        elif position == "bottom":
            self._vertical.insert(0, size)
            self._yrefindex += 1
        else:  # 'top'
            self._vertical.append(size)

    def add_auto_adjustable_area(self, use_axes, pad=0.1, adjust_dirs=None):
        """
        Add auto-adjustable padding around *use_axes* to take their decorations
        (title, labels, ticks, ticklabels) into account during layout.

        Parameters
        ----------
        use_axes : `~matplotlib.axes.Axes` or list of `~matplotlib.axes.Axes`
            The Axes whose decorations are taken into account.
        pad : float, default: 0.1
            Additional padding in inches.
        adjust_dirs : list of {"left", "right", "bottom", "top"}, optional
            The sides where padding is added; defaults to all four sides.
        """
        if adjust_dirs is None:
            adjust_dirs = ["left", "right", "bottom", "top"]
        for d in adjust_dirs:
            self.append_size(d, Size._AxesDecorationsSize(use_axes, d) + pad)


class SubplotDivider(Divider):
    """
    The Divider class whose rectangle area is specified as a subplot geometry.
    """

    def __init__(self, fig, *args, horizontal=None, vertical=None,
                 aspect=None, anchor='C'):
        """
        Parameters
        ----------
        fig : `~matplotlib.figure.Figure`

        *args : tuple (*nrows*, *ncols*, *index*) or int
            The array of subplots in the figure has dimensions ``(nrows,
            ncols)``, and *index* is the index of the subplot being created.
            *index* starts at 1 in the upper left corner and increases to the
            right.

            If *nrows*, *ncols*, and *index* are all single digit numbers, then
            *args* can be passed as a single 3-digit number (e.g. 234 for
            (2, 3, 4)).
        horizontal : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`, optional
            Sizes for horizontal division.
        vertical : list of :mod:`~mpl_toolkits.axes_grid1.axes_size`, optional
            Sizes for vertical division.
        aspect : bool, optional
            Whether overall rectangular area is reduced so that the relative
            part of the horizontal and vertical scales have the same scale.
        anchor : (float, float) or {'C', 'SW', 'S', 'SE', 'E', 'NE', 'N', \
'NW', 'W'}, default: 'C'
            Placement of the reduced rectangle, when *aspect* is True.
        """
        self.figure = fig
        super().__init__(fig, [0, 0, 1, 1],
                         horizontal=horizontal or [], vertical=vertical or [],
                         aspect=aspect, anchor=anchor)
        self.set_subplotspec(SubplotSpec._from_subplot_args(fig, args))

    def get_position(self):
        """Return the bounds of the subplot box."""
        return self.get_subplotspec().get_position(self.figure).bounds

    def get_subplotspec(self):
        """Get the SubplotSpec instance."""
        return self._subplotspec

    def set_subplotspec(self, subplotspec):
        """Set the SubplotSpec instance."""
        self._subplotspec = subplotspec
        self.set_position(subplotspec.get_position(self.figure))


class AxesDivider(Divider):
    """
    Divider based on the preexisting axes.
    """

    def __init__(self, axes, xref=None, yref=None):
        """
        Parameters
        ----------
        axes : :class:`~matplotlib.axes.Axes`
        xref
        yref
        """
        self._axes = axes
        if xref is None:
            self._xref = Size.AxesX(axes)
        else:
            self._xref = xref
        if yref is None:
            self._yref = Size.AxesY(axes)
        else:
            self._yref = yref

        super().__init__(fig=axes.get_figure(), pos=None,
                         horizontal=[self._xref], vertical=[self._yref],
                         aspect=None, anchor="C")

    def _get_new_axes(self, *, axes_class=None, **kwargs):
        axes = self._axes
        if axes_class is None:
            axes_class = type(axes)
        return axes_class(axes.get_figure(), axes.get_position(original=True),
                          **kwargs)

    def new_horizontal(self, size, pad=None, pack_start=False, **kwargs):
        """
        Helper method for ``append_axes("left")`` and ``append_axes("right")``.

        See the documentation of `append_axes` for more details.

        :meta private:
        """
        if pad is None:
            pad = mpl.rcParams["figure.subplot.wspace"] * self._xref
        pos = "left" if pack_start else "right"
        if pad:
            if not isinstance(pad, Size._Base):
                pad = Size.from_any(pad, fraction_ref=self._xref)
            self.append_size(pos, pad)
        if not isinstance(size, Size._Base):
            size = Size.from_any(size, fraction_ref=self._xref)
        self.append_size(pos, size)
        locator = self.new_locator(
            nx=0 if pack_start else len(self._horizontal) - 1,
            ny=self._yrefindex)
        ax = self._get_new_axes(**kwargs)
        ax.set_axes_locator(locator)
        return ax

    def new_vertical(self, size, pad=None, pack_start=False, **kwargs):
        """
        Helper method for ``append_axes("top")`` and ``append_axes("bottom")``.

        See the documentation of `append_axes` for more details.

        :meta private:
        """
        if pad is None:
            pad = mpl.rcParams["figure.subplot.hspace"] * self._yref
        pos = "bottom" if pack_start else "top"
        if pad:
            if not isinstance(pad, Size._Base):
                pad = Size.from_any(pad, fraction_ref=self._yref)
            self.append_size(pos, pad)
        if not isinstance(size, Size._Base):
            size = Size.from_any(size, fraction_ref=self._yref)
        self.append_size(pos, size)
        locator = self.new_locator(
            nx=self._xrefindex,
            ny=0 if pack_start else len(self._vertical) - 1)
        ax = self._get_new_axes(**kwargs)
        ax.set_axes_locator(locator)
        return ax

    def append_axes(self, position, size, pad=None, *, axes_class=None,
                    **kwargs):
        """
        Add a new axes on a given side of the main axes.

        Parameters
        ----------
        position : {"left", "right", "bottom", "top"}
            Where the new axes is positioned relative to the main axes.
        size : :mod:`~mpl_toolkits.axes_grid1.axes_size` or float or str
            The axes width or height.  float or str arguments are interpreted
            as ``axes_size.from_any(size, AxesX(<main_axes>))`` for left or
            right axes, and likewise with ``AxesY`` for bottom or top axes.
        pad : :mod:`~mpl_toolkits.axes_grid1.axes_size` or float or str
            Padding between the axes.  float or str arguments are interpreted
            as for *size*.  Defaults to :rc:`figure.subplot.wspace` times the
            main Axes width (left or right axes) or :rc:`figure.subplot.hspace`
            times the main Axes height (bottom or top axes).
        axes_class : subclass type of `~.axes.Axes`, optional
            The type of the new axes.  Defaults to the type of the main axes.
        **kwargs
            All extra keywords arguments are passed to the created axes.
        """
        create_axes, pack_start = _api.check_getitem({
            "left": (self.new_horizontal, True),
            "right": (self.new_horizontal, False),
            "bottom": (self.new_vertical, True),
            "top": (self.new_vertical, False),
        }, position=position)
        ax = create_axes(
            size, pad, pack_start=pack_start, axes_class=axes_class, **kwargs)
        self._fig.add_axes(ax)
        return ax

    def get_aspect(self):
        if self._aspect is None:
            aspect = self._axes.get_aspect()
            if aspect == "auto":
                return False
            else:
                return True
        else:
            return self._aspect

    def get_position(self):
        if self._pos is None:
            bbox = self._axes.get_position(original=True)
            return bbox.bounds
        else:
            return self._pos

    def get_anchor(self):
        if self._anchor is None:
            return self._axes.get_anchor()
        else:
            return self._anchor

    def get_subplotspec(self):
        return self._axes.get_subplotspec()


# Helper for HBoxDivider/VBoxDivider.
# The variable names are written for a horizontal layout, but the calculations
# work identically for vertical layouts.
def _locate(x, y, w, h, summed_widths, equal_heights, fig_w, fig_h, anchor):

    total_width = fig_w * w
    max_height = fig_h * h

    # Determine the k factors.
    n = len(equal_heights)
    eq_rels, eq_abss = equal_heights.T
    sm_rels, sm_abss = summed_widths.T
    A = np.diag([*eq_rels, 0])
    A[:n, -1] = -1
    A[-1, :-1] = sm_rels
    B = [*(-eq_abss), total_width - sm_abss.sum()]
    # A @ K = B: This finds factors {k_0, ..., k_{N-1}, H} so that
    #   eq_rel_i * k_i + eq_abs_i = H for all i: all axes have the same height
    #   sum(sm_rel_i * k_i + sm_abs_i) = total_width: fixed total width
    # (foo_rel_i * k_i + foo_abs_i will end up being the size of foo.)
    *karray, height = np.linalg.solve(A, B)
    if height > max_height:  # Additionally, upper-bound the height.
        karray = (max_height - eq_abss) / eq_rels

    # Compute the offsets corresponding to these factors.
    ox = np.cumsum([0, *(sm_rels * karray + sm_abss)])
    ww = (ox[-1] - ox[0]) / fig_w
    h0_rel, h0_abs = equal_heights[0]
    hh = (karray[0]*h0_rel + h0_abs) / fig_h
    pb = mtransforms.Bbox.from_bounds(x, y, w, h)
    pb1 = mtransforms.Bbox.from_bounds(x, y, ww, hh)
    x0, y0 = pb1.anchored(anchor, pb).p0

    return x0, y0, ox, hh


class HBoxDivider(SubplotDivider):
    """
    A `.SubplotDivider` for laying out axes horizontally, while ensuring that
    they have equal heights.

    Examples
    --------
    .. plot:: gallery/axes_grid1/demo_axes_hbox_divider.py
    """

    def new_locator(self, nx, nx1=None):
        """
        Create an axes locator callable for the specified cell.

        Parameters
        ----------
        nx, nx1 : int
            Integers specifying the column-position of the
            cell. When *nx1* is None, a single *nx*-th column is
            specified. Otherwise, location of columns spanning between *nx*
            to *nx1* (but excluding *nx1*-th column) is specified.
        """
        return super().new_locator(nx, 0, nx1, 0)

    def _locate(self, nx, ny, nx1, ny1, axes, renderer):
        # docstring inherited
        nx += self._xrefindex
        nx1 += self._xrefindex
        fig_w, fig_h = self._fig.bbox.size / self._fig.dpi
        x, y, w, h = self.get_position_runtime(axes, renderer)
        summed_ws = self.get_horizontal_sizes(renderer)
        equal_hs = self.get_vertical_sizes(renderer)
        x0, y0, ox, hh = _locate(
            x, y, w, h, summed_ws, equal_hs, fig_w, fig_h, self.get_anchor())
        if nx1 is None:
            nx1 = -1
        x1, w1 = x0 + ox[nx] / fig_w, (ox[nx1] - ox[nx]) / fig_w
        y1, h1 = y0, hh
        return mtransforms.Bbox.from_bounds(x1, y1, w1, h1)


class VBoxDivider(SubplotDivider):
    """
    A `.SubplotDivider` for laying out axes vertically, while ensuring that
    they have equal widths.
    """

    def new_locator(self, ny, ny1=None):
        """
        Create an axes locator callable for the specified cell.

        Parameters
        ----------
        ny, ny1 : int
            Integers specifying the row-position of the
            cell. When *ny1* is None, a single *ny*-th row is
            specified. Otherwise, location of rows spanning between *ny*
            to *ny1* (but excluding *ny1*-th row) is specified.
        """
        return super().new_locator(0, ny, 0, ny1)

    def _locate(self, nx, ny, nx1, ny1, axes, renderer):
        # docstring inherited
        ny += self._yrefindex
        ny1 += self._yrefindex
        fig_w, fig_h = self._fig.bbox.size / self._fig.dpi
        x, y, w, h = self.get_position_runtime(axes, renderer)
        summed_hs = self.get_vertical_sizes(renderer)
        equal_ws = self.get_horizontal_sizes(renderer)
        y0, x0, oy, ww = _locate(
            y, x, h, w, summed_hs, equal_ws, fig_h, fig_w, self.get_anchor())
        if ny1 is None:
            ny1 = -1
        x1, w1 = x0, ww
        y1, h1 = y0 + oy[ny] / fig_h, (oy[ny1] - oy[ny]) / fig_h
        return mtransforms.Bbox.from_bounds(x1, y1, w1, h1)


def make_axes_locatable(axes):
    divider = AxesDivider(axes)
    locator = divider.new_locator(nx=0, ny=0)
    axes.set_axes_locator(locator)

    return divider


def make_axes_area_auto_adjustable(
        ax, use_axes=None, pad=0.1, adjust_dirs=None):
    """
    Add auto-adjustable padding around *ax* to take its decorations (title,
    labels, ticks, ticklabels) into account during layout, using
    `.Divider.add_auto_adjustable_area`.

    By default, padding is determined from the decorations of *ax*.
    Pass *use_axes* to consider the decorations of other Axes instead.
    """
    if adjust_dirs is None:
        adjust_dirs = ["left", "right", "bottom", "top"]
    divider = make_axes_locatable(ax)
    if use_axes is None:
        use_axes = ax
    divider.add_auto_adjustable_area(use_axes=use_axes, pad=pad,
                                     adjust_dirs=adjust_dirs)