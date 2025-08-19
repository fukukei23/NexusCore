
# === NexusCore/openenv\Lib\site-packages\PIL\TiffTags.py ===
#
# The Python Imaging Library.
# $Id$
#
# TIFF tags
#
# This module provides clear-text names for various well-known
# TIFF tags.  the TIFF codec works just fine without it.
#
# Copyright (c) Secret Labs AB 1999.
#
# See the README file for information on usage and redistribution.
#

##
# This module provides constants and clear-text names for various
# well-known TIFF tags.
##
from __future__ import annotations

from typing import NamedTuple


class _TagInfo(NamedTuple):
    value: int | None
    name: str
    type: int | None
    length: int | None
    enum: dict[str, int]


class TagInfo(_TagInfo):
    __slots__: list[str] = []

    def __new__(
        cls,
        value: int | None = None,
        name: str = "unknown",
        type: int | None = None,
        length: int | None = None,
        enum: dict[str, int] | None = None,
    ) -> TagInfo:
        return super().__new__(cls, value, name, type, length, enum or {})

    def cvt_enum(self, value: str) -> int | str:
        # Using get will call hash(value), which can be expensive
        # for some types (e.g. Fraction). Since self.enum is rarely
        # used, it's usually better to test it first.
        return self.enum.get(value, value) if self.enum else value


def lookup(tag: int, group: int | None = None) -> TagInfo:
    """
    :param tag: Integer tag number
    :param group: Which :py:data:`~PIL.TiffTags.TAGS_V2_GROUPS` to look in

    .. versionadded:: 8.3.0

    :returns: Taginfo namedtuple, From the ``TAGS_V2`` info if possible,
        otherwise just populating the value and name from ``TAGS``.
        If the tag is not recognized, "unknown" is returned for the name

    """

    if group is not None:
        info = TAGS_V2_GROUPS[group].get(tag) if group in TAGS_V2_GROUPS else None
    else:
        info = TAGS_V2.get(tag)
    return info or TagInfo(tag, TAGS.get(tag, "unknown"))


##
# Map tag numbers to tag info.
#
#  id: (Name, Type, Length[, enum_values])
#
# The length here differs from the length in the tiff spec.  For
# numbers, the tiff spec is for the number of fields returned. We
# agree here.  For string-like types, the tiff spec uses the length of
# field in bytes.  In Pillow, we are using the number of expected
# fields, in general 1 for string-like types.


BYTE = 1
ASCII = 2
SHORT = 3
LONG = 4
RATIONAL = 5
SIGNED_BYTE = 6
UNDEFINED = 7
SIGNED_SHORT = 8
SIGNED_LONG = 9
SIGNED_RATIONAL = 10
FLOAT = 11
DOUBLE = 12
IFD = 13
LONG8 = 16

_tags_v2: dict[int, tuple[str, int, int] | tuple[str, int, int, dict[str, int]]] = {
    254: ("NewSubfileType", LONG, 1),
    255: ("SubfileType", SHORT, 1),
    256: ("ImageWidth", LONG, 1),
    257: ("ImageLength", LONG, 1),
    258: ("BitsPerSample", SHORT, 0),
    259: (
        "Compression",
        SHORT,
        1,
        {
            "Uncompressed": 1,
            "CCITT 1d": 2,
            "Group 3 Fax": 3,
            "Group 4 Fax": 4,
            "LZW": 5,
            "JPEG": 6,
            "PackBits": 32773,
        },
    ),
    262: (
        "PhotometricInterpretation",
        SHORT,
        1,
        {
            "WhiteIsZero": 0,
            "BlackIsZero": 1,
            "RGB": 2,
            "RGB Palette": 3,
            "Transparency Mask": 4,
            "CMYK": 5,
            "YCbCr": 6,
            "CieLAB": 8,
            "CFA": 32803,  # TIFF/EP, Adobe DNG
            "LinearRaw": 32892,  # Adobe DNG
        },
    ),
    263: ("Threshholding", SHORT, 1),
    264: ("CellWidth", SHORT, 1),
    265: ("CellLength", SHORT, 1),
    266: ("FillOrder", SHORT, 1),
    269: ("DocumentName", ASCII, 1),
    270: ("ImageDescription", ASCII, 1),
    271: ("Make", ASCII, 1),
    272: ("Model", ASCII, 1),
    273: ("StripOffsets", LONG, 0),
    274: ("Orientation", SHORT, 1),
    277: ("SamplesPerPixel", SHORT, 1),
    278: ("RowsPerStrip", LONG, 1),
    279: ("StripByteCounts", LONG, 0),
    280: ("MinSampleValue", SHORT, 0),
    281: ("MaxSampleValue", SHORT, 0),
    282: ("XResolution", RATIONAL, 1),
    283: ("YResolution", RATIONAL, 1),
    284: ("PlanarConfiguration", SHORT, 1, {"Contiguous": 1, "Separate": 2}),
    285: ("PageName", ASCII, 1),
    286: ("XPosition", RATIONAL, 1),
    287: ("YPosition", RATIONAL, 1),
    288: ("FreeOffsets", LONG, 1),
    289: ("FreeByteCounts", LONG, 1),
    290: ("GrayResponseUnit", SHORT, 1),
    291: ("GrayResponseCurve", SHORT, 0),
    292: ("T4Options", LONG, 1),
    293: ("T6Options", LONG, 1),
    296: ("ResolutionUnit", SHORT, 1, {"none": 1, "inch": 2, "cm": 3}),
    297: ("PageNumber", SHORT, 2),
    301: ("TransferFunction", SHORT, 0),
    305: ("Software", ASCII, 1),
    306: ("DateTime", ASCII, 1),
    315: ("Artist", ASCII, 1),
    316: ("HostComputer", ASCII, 1),
    317: ("Predictor", SHORT, 1, {"none": 1, "Horizontal Differencing": 2}),
    318: ("WhitePoint", RATIONAL, 2),
    319: ("PrimaryChromaticities", RATIONAL, 6),
    320: ("ColorMap", SHORT, 0),
    321: ("HalftoneHints", SHORT, 2),
    322: ("TileWidth", LONG, 1),
    323: ("TileLength", LONG, 1),
    324: ("TileOffsets", LONG, 0),
    325: ("TileByteCounts", LONG, 0),
    330: ("SubIFDs", LONG, 0),
    332: ("InkSet", SHORT, 1),
    333: ("InkNames", ASCII, 1),
    334: ("NumberOfInks", SHORT, 1),
    336: ("DotRange", SHORT, 0),
    337: ("TargetPrinter", ASCII, 1),
    338: ("ExtraSamples", SHORT, 0),
    339: ("SampleFormat", SHORT, 0),
    340: ("SMinSampleValue", DOUBLE, 0),
    341: ("SMaxSampleValue", DOUBLE, 0),
    342: ("TransferRange", SHORT, 6),
    347: ("JPEGTables", UNDEFINED, 1),
    # obsolete JPEG tags
    512: ("JPEGProc", SHORT, 1),
    513: ("JPEGInterchangeFormat", LONG, 1),
    514: ("JPEGInterchangeFormatLength", LONG, 1),
    515: ("JPEGRestartInterval", SHORT, 1),
    517: ("JPEGLosslessPredictors", SHORT, 0),
    518: ("JPEGPointTransforms", SHORT, 0),
    519: ("JPEGQTables", LONG, 0),
    520: ("JPEGDCTables", LONG, 0),
    521: ("JPEGACTables", LONG, 0),
    529: ("YCbCrCoefficients", RATIONAL, 3),
    530: ("YCbCrSubSampling", SHORT, 2),
    531: ("YCbCrPositioning", SHORT, 1),
    532: ("ReferenceBlackWhite", RATIONAL, 6),
    700: ("XMP", BYTE, 0),
    33432: ("Copyright", ASCII, 1),
    33723: ("IptcNaaInfo", UNDEFINED, 1),
    34377: ("PhotoshopInfo", BYTE, 0),
    # FIXME add more tags here
    34665: ("ExifIFD", LONG, 1),
    34675: ("ICCProfile", UNDEFINED, 1),
    34853: ("GPSInfoIFD", LONG, 1),
    36864: ("ExifVersion", UNDEFINED, 1),
    37724: ("ImageSourceData", UNDEFINED, 1),
    40965: ("InteroperabilityIFD", LONG, 1),
    41730: ("CFAPattern", UNDEFINED, 1),
    # MPInfo
    45056: ("MPFVersion", UNDEFINED, 1),
    45057: ("NumberOfImages", LONG, 1),
    45058: ("MPEntry", UNDEFINED, 1),
    45059: ("ImageUIDList", UNDEFINED, 0),  # UNDONE, check
    45060: ("TotalFrames", LONG, 1),
    45313: ("MPIndividualNum", LONG, 1),
    45569: ("PanOrientation", LONG, 1),
    45570: ("PanOverlap_H", RATIONAL, 1),
    45571: ("PanOverlap_V", RATIONAL, 1),
    45572: ("BaseViewpointNum", LONG, 1),
    45573: ("ConvergenceAngle", SIGNED_RATIONAL, 1),
    45574: ("BaselineLength", RATIONAL, 1),
    45575: ("VerticalDivergence", SIGNED_RATIONAL, 1),
    45576: ("AxisDistance_X", SIGNED_RATIONAL, 1),
    45577: ("AxisDistance_Y", SIGNED_RATIONAL, 1),
    45578: ("AxisDistance_Z", SIGNED_RATIONAL, 1),
    45579: ("YawAngle", SIGNED_RATIONAL, 1),
    45580: ("PitchAngle", SIGNED_RATIONAL, 1),
    45581: ("RollAngle", SIGNED_RATIONAL, 1),
    40960: ("FlashPixVersion", UNDEFINED, 1),
    50741: ("MakerNoteSafety", SHORT, 1, {"Unsafe": 0, "Safe": 1}),
    50780: ("BestQualityScale", RATIONAL, 1),
    50838: ("ImageJMetaDataByteCounts", LONG, 0),  # Can be more than one
    50839: ("ImageJMetaData", UNDEFINED, 1),  # see Issue #2006
}
_tags_v2_groups = {
    # ExifIFD
    34665: {
        36864: ("ExifVersion", UNDEFINED, 1),
        40960: ("FlashPixVersion", UNDEFINED, 1),
        40965: ("InteroperabilityIFD", LONG, 1),
        41730: ("CFAPattern", UNDEFINED, 1),
    },
    # GPSInfoIFD
    34853: {
        0: ("GPSVersionID", BYTE, 4),
        1: ("GPSLatitudeRef", ASCII, 2),
        2: ("GPSLatitude", RATIONAL, 3),
        3: ("GPSLongitudeRef", ASCII, 2),
        4: ("GPSLongitude", RATIONAL, 3),
        5: ("GPSAltitudeRef", BYTE, 1),
        6: ("GPSAltitude", RATIONAL, 1),
        7: ("GPSTimeStamp", RATIONAL, 3),
        8: ("GPSSatellites", ASCII, 0),
        9: ("GPSStatus", ASCII, 2),
        10: ("GPSMeasureMode", ASCII, 2),
        11: ("GPSDOP", RATIONAL, 1),
        12: ("GPSSpeedRef", ASCII, 2),
        13: ("GPSSpeed", RATIONAL, 1),
        14: ("GPSTrackRef", ASCII, 2),
        15: ("GPSTrack", RATIONAL, 1),
        16: ("GPSImgDirectionRef", ASCII, 2),
        17: ("GPSImgDirection", RATIONAL, 1),
        18: ("GPSMapDatum", ASCII, 0),
        19: ("GPSDestLatitudeRef", ASCII, 2),
        20: ("GPSDestLatitude", RATIONAL, 3),
        21: ("GPSDestLongitudeRef", ASCII, 2),
        22: ("GPSDestLongitude", RATIONAL, 3),
        23: ("GPSDestBearingRef", ASCII, 2),
        24: ("GPSDestBearing", RATIONAL, 1),
        25: ("GPSDestDistanceRef", ASCII, 2),
        26: ("GPSDestDistance", RATIONAL, 1),
        27: ("GPSProcessingMethod", UNDEFINED, 0),
        28: ("GPSAreaInformation", UNDEFINED, 0),
        29: ("GPSDateStamp", ASCII, 11),
        30: ("GPSDifferential", SHORT, 1),
    },
    # InteroperabilityIFD
    40965: {1: ("InteropIndex", ASCII, 1), 2: ("InteropVersion", UNDEFINED, 1)},
}

# Legacy Tags structure
# these tags aren't included above, but were in the previous versions
TAGS: dict[int | tuple[int, int], str] = {
    347: "JPEGTables",
    700: "XMP",
    # Additional Exif Info
    32932: "Wang Annotation",
    33434: "ExposureTime",
    33437: "FNumber",
    33445: "MD FileTag",
    33446: "MD ScalePixel",
    33447: "MD ColorTable",
    33448: "MD LabName",
    33449: "MD SampleInfo",
    33450: "MD PrepDate",
    33451: "MD PrepTime",
    33452: "MD FileUnits",
    33550: "ModelPixelScaleTag",
    33723: "IptcNaaInfo",
    33918: "INGR Packet Data Tag",
    33919: "INGR Flag Registers",
    33920: "IrasB Transformation Matrix",
    33922: "ModelTiepointTag",
    34264: "ModelTransformationTag",
    34377: "PhotoshopInfo",
    34735: "GeoKeyDirectoryTag",
    34736: "GeoDoubleParamsTag",
    34737: "GeoAsciiParamsTag",
    34850: "ExposureProgram",
    34852: "SpectralSensitivity",
    34855: "ISOSpeedRatings",
    34856: "OECF",
    34864: "SensitivityType",
    34865: "StandardOutputSensitivity",
    34866: "RecommendedExposureIndex",
    34867: "ISOSpeed",
    34868: "ISOSpeedLatitudeyyy",
    34869: "ISOSpeedLatitudezzz",
    34908: "HylaFAX FaxRecvParams",
    34909: "HylaFAX FaxSubAddress",
    34910: "HylaFAX FaxRecvTime",
    36864: "ExifVersion",
    36867: "DateTimeOriginal",
    36868: "DateTimeDigitized",
    37121: "ComponentsConfiguration",
    37122: "CompressedBitsPerPixel",
    37724: "ImageSourceData",
    37377: "ShutterSpeedValue",
    37378: "ApertureValue",
    37379: "BrightnessValue",
    37380: "ExposureBiasValue",
    37381: "MaxApertureValue",
    37382: "SubjectDistance",
    37383: "MeteringMode",
    37384: "LightSource",
    37385: "Flash",
    37386: "FocalLength",
    37396: "SubjectArea",
    37500: "MakerNote",
    37510: "UserComment",
    37520: "SubSec",
    37521: "SubSecTimeOriginal",
    37522: "SubsecTimeDigitized",
    40960: "FlashPixVersion",
    40961: "ColorSpace",
    40962: "PixelXDimension",
    40963: "PixelYDimension",
    40964: "RelatedSoundFile",
    40965: "InteroperabilityIFD",
    41483: "FlashEnergy",
    41484: "SpatialFrequencyResponse",
    41486: "FocalPlaneXResolution",
    41487: "FocalPlaneYResolution",
    41488: "FocalPlaneResolutionUnit",
    41492: "SubjectLocation",
    41493: "ExposureIndex",
    41495: "SensingMethod",
    41728: "FileSource",
    41729: "SceneType",
    41730: "CFAPattern",
    41985: "CustomRendered",
    41986: "ExposureMode",
    41987: "WhiteBalance",
    41988: "DigitalZoomRatio",
    41989: "FocalLengthIn35mmFilm",
    41990: "SceneCaptureType",
    41991: "GainControl",
    41992: "Contrast",
    41993: "Saturation",
    41994: "Sharpness",
    41995: "DeviceSettingDescription",
    41996: "SubjectDistanceRange",
    42016: "ImageUniqueID",
    42032: "CameraOwnerName",
    42033: "BodySerialNumber",
    42034: "LensSpecification",
    42035: "LensMake",
    42036: "LensModel",
    42037: "LensSerialNumber",
    42112: "GDAL_METADATA",
    42113: "GDAL_NODATA",
    42240: "Gamma",
    50215: "Oce Scanjob Description",
    50216: "Oce Application Selector",
    50217: "Oce Identification Number",
    50218: "Oce ImageLogic Characteristics",
    # Adobe DNG
    50706: "DNGVersion",
    50707: "DNGBackwardVersion",
    50708: "UniqueCameraModel",
    50709: "LocalizedCameraModel",
    50710: "CFAPlaneColor",
    50711: "CFALayout",
    50712: "LinearizationTable",
    50713: "BlackLevelRepeatDim",
    50714: "BlackLevel",
    50715: "BlackLevelDeltaH",
    50716: "BlackLevelDeltaV",
    50717: "WhiteLevel",
    50718: "DefaultScale",
    50719: "DefaultCropOrigin",
    50720: "DefaultCropSize",
    50721: "ColorMatrix1",
    50722: "ColorMatrix2",
    50723: "CameraCalibration1",
    50724: "CameraCalibration2",
    50725: "ReductionMatrix1",
    50726: "ReductionMatrix2",
    50727: "AnalogBalance",
    50728: "AsShotNeutral",
    50729: "AsShotWhiteXY",
    50730: "BaselineExposure",
    50731: "BaselineNoise",
    50732: "BaselineSharpness",
    50733: "BayerGreenSplit",
    50734: "LinearResponseLimit",
    50735: "CameraSerialNumber",
    50736: "LensInfo",
    50737: "ChromaBlurRadius",
    50738: "AntiAliasStrength",
    50740: "DNGPrivateData",
    50778: "CalibrationIlluminant1",
    50779: "CalibrationIlluminant2",
    50784: "Alias Layer Metadata",
}

TAGS_V2: dict[int, TagInfo] = {}
TAGS_V2_GROUPS: dict[int, dict[int, TagInfo]] = {}


def _populate() -> None:
    for k, v in _tags_v2.items():
        # Populate legacy structure.
        TAGS[k] = v[0]
        if len(v) == 4:
            for sk, sv in v[3].items():
                TAGS[(k, sv)] = sk

        TAGS_V2[k] = TagInfo(k, *v)

    for group, tags in _tags_v2_groups.items():
        TAGS_V2_GROUPS[group] = {k: TagInfo(k, *v) for k, v in tags.items()}


_populate()
##
# Map type numbers to type names -- defined in ImageFileDirectory.

TYPES: dict[int, str] = {}

#
# These tags are handled by default in libtiff, without
# adding to the custom dictionary. From tif_dir.c, searching for
# case TIFFTAG in the _TIFFVSetField function:
# Line: item.
# 148: case TIFFTAG_SUBFILETYPE:
# 151: case TIFFTAG_IMAGEWIDTH:
# 154: case TIFFTAG_IMAGELENGTH:
# 157: case TIFFTAG_BITSPERSAMPLE:
# 181: case TIFFTAG_COMPRESSION:
# 202: case TIFFTAG_PHOTOMETRIC:
# 205: case TIFFTAG_THRESHHOLDING:
# 208: case TIFFTAG_FILLORDER:
# 214: case TIFFTAG_ORIENTATION:
# 221: case TIFFTAG_SAMPLESPERPIXEL:
# 228: case TIFFTAG_ROWSPERSTRIP:
# 238: case TIFFTAG_MINSAMPLEVALUE:
# 241: case TIFFTAG_MAXSAMPLEVALUE:
# 244: case TIFFTAG_SMINSAMPLEVALUE:
# 247: case TIFFTAG_SMAXSAMPLEVALUE:
# 250: case TIFFTAG_XRESOLUTION:
# 256: case TIFFTAG_YRESOLUTION:
# 262: case TIFFTAG_PLANARCONFIG:
# 268: case TIFFTAG_XPOSITION:
# 271: case TIFFTAG_YPOSITION:
# 274: case TIFFTAG_RESOLUTIONUNIT:
# 280: case TIFFTAG_PAGENUMBER:
# 284: case TIFFTAG_HALFTONEHINTS:
# 288: case TIFFTAG_COLORMAP:
# 294: case TIFFTAG_EXTRASAMPLES:
# 298: case TIFFTAG_MATTEING:
# 305: case TIFFTAG_TILEWIDTH:
# 316: case TIFFTAG_TILELENGTH:
# 327: case TIFFTAG_TILEDEPTH:
# 333: case TIFFTAG_DATATYPE:
# 344: case TIFFTAG_SAMPLEFORMAT:
# 361: case TIFFTAG_IMAGEDEPTH:
# 364: case TIFFTAG_SUBIFD:
# 376: case TIFFTAG_YCBCRPOSITIONING:
# 379: case TIFFTAG_YCBCRSUBSAMPLING:
# 383: case TIFFTAG_TRANSFERFUNCTION:
# 389: case TIFFTAG_REFERENCEBLACKWHITE:
# 393: case TIFFTAG_INKNAMES:

# Following pseudo-tags are also handled by default in libtiff:
# TIFFTAG_JPEGQUALITY 65537

# some of these are not in our TAGS_V2 dict and were included from tiff.h

# This list also exists in encode.c
LIBTIFF_CORE = {
    255,
    256,
    257,
    258,
    259,
    262,
    263,
    266,
    274,
    277,
    278,
    280,
    281,
    340,
    341,
    282,
    283,
    284,
    286,
    287,
    296,
    297,
    321,
    320,
    338,
    32995,
    322,
    323,
    32998,
    32996,
    339,
    32997,
    330,
    531,
    530,
    301,
    532,
    333,
    # as above
    269,  # this has been in our tests forever, and works
    65537,
}

LIBTIFF_CORE.remove(255)  # We don't have support for subfiletypes
LIBTIFF_CORE.remove(322)  # We don't have support for writing tiled images with libtiff
LIBTIFF_CORE.remove(323)  # Tiled images
LIBTIFF_CORE.remove(333)  # Ink Names either

# Note to advanced users: There may be combinations of these
# parameters and values that when added properly, will work and
# produce valid tiff images that may work in your application.
# It is safe to add and remove tags from this set from Pillow's point
# of view so long as you test against libtiff.

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\cmd_line_parser.py ===
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
"""Parses an LLM command line."""
from __future__ import annotations

import argparse
import shlex
import sys
from typing import AbstractSet, Any, Callable, MutableMapping, Sequence

from google.generativeai.notebook import argument_parser
from google.generativeai.notebook import flag_def
from google.generativeai.notebook import input_utils
from google.generativeai.notebook import model_registry
from google.generativeai.notebook import output_utils
from google.generativeai.notebook import parsed_args_lib
from google.generativeai.notebook import post_process_utils
from google.generativeai.notebook import py_utils
from google.generativeai.notebook import sheets_utils
from google.generativeai.notebook.lib import llm_function
from google.generativeai.notebook.lib import llmfn_inputs_source
from google.generativeai.notebook.lib import llmfn_outputs
from google.generativeai.notebook.lib import model as model_lib


_MIN_CANDIDATE_COUNT = 1
_MAX_CANDIDATE_COUNT = 8


def _validate_input_source_against_placeholders(
    source: llmfn_inputs_source.LLMFnInputsSource,
    placeholders: AbstractSet[str],
) -> None:
    for inputs in source.to_normalized_inputs():
        for keyword in placeholders:
            if keyword not in inputs:
                raise ValueError('Placeholder "{}" not found in input'.format(keyword))


def _get_resolve_input_from_py_var_fn(
    placeholders: AbstractSet[str] | None,
) -> Callable[[str], llmfn_inputs_source.LLMFnInputsSource]:
    def _fn(var_name: str) -> llmfn_inputs_source.LLMFnInputsSource:
        source = input_utils.get_inputs_source_from_py_var(var_name)
        if placeholders:
            _validate_input_source_against_placeholders(source, placeholders)
        return source

    return _fn


def _resolve_compare_fn_var(
    name: str,
) -> tuple[str, parsed_args_lib.TextResultCompareFn]:
    """Resolves a value passed into --compare_fn."""
    fn = py_utils.get_py_var(name)
    if not isinstance(fn, Callable):
        raise ValueError('Variable "{}" does not contain a Callable object'.format(name))

    return name, fn


def _resolve_ground_truth_var(name: str) -> Sequence[str]:
    """Resolves a value passed into --ground_truth."""
    value = py_utils.get_py_var(name)

    # "str" and "bytes" are also Sequences but we want an actual Sequence of
    # strings, like a list.
    if not isinstance(value, Sequence) or isinstance(value, str) or isinstance(value, bytes):
        raise ValueError('Variable "{}" does not contain a Sequence of strings'.format(name))
    for x in value:
        if not isinstance(x, str):
            raise ValueError('Variable "{}" does not contain a Sequence of strings'.format(name))
    return value


def _get_resolve_sheets_inputs_fn(
    placeholders: AbstractSet[str] | None,
) -> Callable[[str], llmfn_inputs_source.LLMFnInputsSource]:
    def _fn(value: str) -> llmfn_inputs_source.LLMFnInputsSource:
        sheets_id = sheets_utils.get_sheets_id_from_str(value)
        source = sheets_utils.SheetsInputs(sheets_id)
        if placeholders:
            _validate_input_source_against_placeholders(source, placeholders)
        return source

    return _fn


def _resolve_sheets_outputs(value: str) -> llmfn_outputs.LLMFnOutputsSink:
    sheets_id = sheets_utils.get_sheets_id_from_str(value)
    return sheets_utils.SheetsOutputs(sheets_id)


def _add_model_flags(
    parser: argparse.ArgumentParser,
) -> None:
    """Adds flags that are related to model selection and config."""
    flag_def.EnumFlagDef(
        name="model_type",
        short_name="mt",
        enum_type=model_registry.ModelName,
        default_value=model_registry.ModelRegistry.DEFAULT_MODEL,
        help_msg="The type of model to use.",
    ).add_argument_to_parser(parser)

    def _check_is_greater_than_or_equal_to_zero(x: float) -> float:
        if x < 0:
            raise ValueError("Value should be greater than or equal to zero, got {}".format(x))
        return x

    flag_def.SingleValueFlagDef(
        name="temperature",
        short_name="t",
        parse_type=float,
        # Use None for default value to indicate that this will use the default
        # value in Text service.
        default_value=None,
        parse_to_dest_type_fn=_check_is_greater_than_or_equal_to_zero,
        help_msg=(
            "Controls the randomness of the output. Must be positive. Typical"
            " values are in the range: [0.0, 1.0]. Higher values produce a more"
            " random and varied response. A temperature of zero will be"
            " deterministic."
        ),
    ).add_argument_to_parser(parser)

    flag_def.SingleValueFlagDef(
        name="model",
        short_name="m",
        default_value=None,
        help_msg=(
            "The name of the model to use. If not provided, a default model will" " be used."
        ),
    ).add_argument_to_parser(parser)

    def _check_candidate_count_range(x: Any) -> int:
        if x < _MIN_CANDIDATE_COUNT or x > _MAX_CANDIDATE_COUNT:
            raise ValueError(
                "Value should be in the range [{}, {}], got {}".format(
                    _MIN_CANDIDATE_COUNT, _MAX_CANDIDATE_COUNT, x
                )
            )
        return int(x)

    flag_def.SingleValueFlagDef(
        name="candidate_count",
        short_name="cc",
        parse_type=int,
        # Use None for default value to indicate that this will use the default
        # value in Text service.
        default_value=None,
        parse_to_dest_type_fn=_check_candidate_count_range,
        help_msg="The number of candidates to produce.",
    ).add_argument_to_parser(parser)

    flag_def.BooleanFlagDef(
        name="unique",
        help_msg="Whether to dedupe candidates returned by the model.",
    ).add_argument_to_parser(parser)


def _add_input_flags(
    parser: argparse.ArgumentParser,
    placeholders: AbstractSet[str] | None,
) -> None:
    """Adds flags to read inputs from a Python variable or Sheets."""
    flag_def.MultiValuesFlagDef(
        name="inputs",
        short_name="i",
        dest_type=llmfn_inputs_source.LLMFnInputsSource,
        parse_to_dest_type_fn=_get_resolve_input_from_py_var_fn(placeholders),
        help_msg=(
            "Optional names of Python variables containing inputs to use to"
            " instantiate a prompt. The variable must be either: a dictionary"
            " {'key1': ['val1', 'val2'] ...}, or an instance of LLMFnInputsSource"
            " such as SheetsInput."
        ),
    ).add_argument_to_parser(parser)

    flag_def.MultiValuesFlagDef(
        name="sheets_input_names",
        short_name="si",
        dest_type=llmfn_inputs_source.LLMFnInputsSource,
        parse_to_dest_type_fn=_get_resolve_sheets_inputs_fn(placeholders),
        help_msg=(
            "Optional names of Google Sheets to read inputs from. This is"
            " equivalent to using --inputs with the names of variables that are"
            " instances of SheetsInputs, just more convenient to use."
        ),
    ).add_argument_to_parser(parser)


def _add_output_flags(
    parser: argparse.ArgumentParser,
) -> None:
    """Adds flags to write outputs to a Python variable."""
    flag_def.MultiValuesFlagDef(
        name="outputs",
        short_name="o",
        dest_type=llmfn_outputs.LLMFnOutputsSink,
        parse_to_dest_type_fn=output_utils.get_outputs_sink_from_py_var,
        help_msg=(
            "Optional names of Python variables to output to. If the Python"
            " variable has not already been defined, it will be created. If the"
            " variable is defined and is an instance of LLMFnOutputsSink, the"
            " outputs will be written through the sink's write_outputs() method."
        ),
    ).add_argument_to_parser(parser)

    flag_def.MultiValuesFlagDef(
        name="sheets_output_names",
        short_name="so",
        dest_type=llmfn_outputs.LLMFnOutputsSink,
        parse_to_dest_type_fn=_resolve_sheets_outputs,
        help_msg=(
            "Optional names of Google Sheets to write inputs to. This is"
            " equivalent to using --outputs with the names of variables that are"
            " instances of SheetsOutputs, just more convenient to use."
        ),
    ).add_argument_to_parser(parser)


def _add_compare_flags(
    parser: argparse.ArgumentParser,
) -> None:
    flag_def.MultiValuesFlagDef(
        name="compare_fn",
        dest_type=tuple,
        parse_to_dest_type_fn=_resolve_compare_fn_var,
        help_msg=(
            "An optional function that takes two inputs: (lhs_result, rhs_result)"
            " which are the results of the left- and right-hand side functions. "
            "Multiple comparison functions can be provided."
        ),
    ).add_argument_to_parser(parser)


def _add_eval_flags(
    parser: argparse.ArgumentParser,
) -> None:
    flag_def.SingleValueFlagDef(
        name="ground_truth",
        required=True,
        dest_type=Sequence,
        parse_to_dest_type_fn=_resolve_ground_truth_var,
        help_msg=(
            "A variable containing a Sequence of strings representing the ground"
            " truth that the output of this cell will be compared against. It"
            " should have the same number of entries as inputs."
        ),
    ).add_argument_to_parser(parser)


def _create_run_parser(
    parser: argparse.ArgumentParser,
    placeholders: AbstractSet[str] | None,
) -> None:
    """Adds flags for the `run` command.

    `run` sends one or more prompts to a model.

    Args:
      parser: The parser to which flags will be added.
      placeholders: Placeholders from prompts in the cell contents.
    """
    _add_model_flags(parser)
    _add_input_flags(parser, placeholders)
    _add_output_flags(parser)


def _create_compile_parser(
    parser: argparse.ArgumentParser,
) -> None:
    """Adds flags for the compile command.

    `compile` "compiles" a prompt and model call into a callable function.

    Args:
      parser: The parser to which flags will be added.
    """

    # Add a positional argument for "compile_save_name".
    def _compile_save_name_fn(var_name: str) -> str:
        try:
            py_utils.validate_var_name(var_name)
        except ValueError as e:
            # Re-raise as ArgumentError to preserve the original error message.
            raise argparse.ArgumentError(None, "{}".format(e)) from e
        return var_name

    save_name_help = "The name of a Python variable to save the compiled function to."
    parser.add_argument("compile_save_name", help=save_name_help, type=_compile_save_name_fn)
    _add_model_flags(parser)


def _create_compare_parser(
    parser: argparse.ArgumentParser,
    placeholders: AbstractSet[str] | None,
) -> None:
    """Adds flags for the compare command.

    Args:
      parser: The parser to which flags will be added.
      placeholders: Placeholders from prompts in the compiled functions.
    """

    # Add positional arguments.
    def _resolve_llm_function_fn(
        var_name: str,
    ) -> tuple[str, llm_function.LLMFunction]:
        try:
            py_utils.validate_var_name(var_name)
        except ValueError as e:
            # Re-raise as ArgumentError to preserve the original error message.
            raise argparse.ArgumentError(None, "{}".format(e)) from e

        fn = py_utils.get_py_var(var_name)
        if not isinstance(fn, llm_function.LLMFunction):
            raise argparse.ArgumentError(
                None,
                '{} is not a function created with the "compile" command'.format(var_name),
            )
        return var_name, fn

    name_help = (
        "The name of a Python variable containing a function previously created"
        ' with the "compile" command.'
    )
    parser.add_argument("lhs_name_and_fn", help=name_help, type=_resolve_llm_function_fn)
    parser.add_argument("rhs_name_and_fn", help=name_help, type=_resolve_llm_function_fn)

    _add_input_flags(parser, placeholders)
    _add_output_flags(parser)
    _add_compare_flags(parser)


def _create_eval_parser(
    parser: argparse.ArgumentParser,
    placeholders: AbstractSet[str] | None,
) -> None:
    """Adds flags for the eval command.

    Args:
      parser: The parser to which flags will be added.
      placeholders: Placeholders from prompts in the cell contents.
    """
    _add_model_flags(parser)
    _add_input_flags(parser, placeholders)
    _add_output_flags(parser)
    _add_compare_flags(parser)
    _add_eval_flags(parser)


def _create_parser(
    placeholders: AbstractSet[str] | None,
) -> argparse.ArgumentParser:
    """Create the full parser."""
    system_name = "llm"
    description = "A system for interacting with LLMs."
    epilog = ""

    # Commands
    extra_args = {}
    if sys.version_info[0:2] >= (3, 9):
        extra_args["exit_on_error"] = False

    parser = argument_parser.ArgumentParser(
        prog=system_name,
        description=description,
        epilog=epilog,
        **extra_args,
    )
    subparsers = parser.add_subparsers(dest="cmd")
    _create_run_parser(
        subparsers.add_parser(parsed_args_lib.CommandName.RUN_CMD.value),
        placeholders,
    )
    _create_compile_parser(subparsers.add_parser(parsed_args_lib.CommandName.COMPILE_CMD.value))
    _create_compare_parser(
        subparsers.add_parser(parsed_args_lib.CommandName.COMPARE_CMD.value),
        placeholders,
    )
    _create_eval_parser(
        subparsers.add_parser(parsed_args_lib.CommandName.EVAL_CMD.value),
        placeholders,
    )
    return parser


def _validate_parsed_args(parsed_args: parsed_args_lib.ParsedArgs) -> None:
    # If candidate_count is not set (i.e. is None), assuming the default value
    # is 1.
    if parsed_args.unique and (
        parsed_args.model_args.candidate_count is None
        or parsed_args.model_args.candidate_count == 1
    ):
        print(
            '"--unique" works across candidates only: it should be used with'
            " --candidate_count set to a value greater-than one."
        )


class CmdLineParser:
    """Implementation of Magics command line parser."""

    # Commands
    DEFAULT_CMD = parsed_args_lib.CommandName.RUN_CMD

    # Post-processing operator.
    PIPE_OP = "|"

    @classmethod
    def _split_post_processing_tokens(
        cls,
        tokens: Sequence[str],
    ) -> tuple[Sequence[str], parsed_args_lib.PostProcessingTokens]:
        """Splits inputs into the command and post processing tokens.

        The command is represented as a sequence of tokens.
        See comments on the PostProcessingTokens type alias.

        E.g. Given: "run --temperature 0.5 | add_score | to_lower_case"
        The command will be: ["run", "--temperature", "0.5"].
        The post processing tokens will be: [["add_score"], ["to_lower_case"]]

        Args:
          tokens: The command line tokens.

        Returns:
          A tuple of (command line, post processing tokens).
        """
        split_tokens = []
        start_idx: int | None = None
        for token_num, token in enumerate(tokens):
            if start_idx is None:
                start_idx = token_num
            if token == CmdLineParser.PIPE_OP:
                split_tokens.append(tokens[start_idx:token_num] if start_idx is not None else [])
                start_idx = None

        # Add the remaining tokens after the last PIPE_OP.
        split_tokens.append(tokens[start_idx:] if start_idx is not None else [])

        return split_tokens[0], split_tokens[1:]

    @classmethod
    def _tokenize_line(
        cls, line: str
    ) -> tuple[Sequence[str], parsed_args_lib.PostProcessingTokens]:
        """Parses `line` and returns command line and post processing tokens."""
        # Check to make sure there is a command at the start. If not, add the
        # default command to the list of tokens.
        tokens = shlex.split(line)
        if not tokens:
            tokens = [CmdLineParser.DEFAULT_CMD.value]
        first_token = tokens[0]
        # Add default command if the first token is not the help token.
        if not first_token[0].isalpha() and first_token not in ["-h", "--help"]:
            tokens = [CmdLineParser.DEFAULT_CMD.value] + tokens
        # Split line into tokens and post-processing
        return CmdLineParser._split_post_processing_tokens(tokens)

    @classmethod
    def _get_model_args(
        cls, parsed_results: MutableMapping[str, Any]
    ) -> tuple[MutableMapping[str, Any], model_lib.ModelArguments]:
        """Extracts fields for model args from `parsed_results`.

        Keys specific to model arguments will be removed from `parsed_results`.

        Args:
          parsed_results: A dictionary of parsed arguments (from ArgumentParser). It
            will be modified in place.

        Returns:
          A tuple of (updated parsed_results, model arguments).
        """
        model = parsed_results.pop("model", None)
        temperature = parsed_results.pop("temperature", None)
        candidate_count = parsed_results.pop("candidate_count", None)

        model_args = model_lib.ModelArguments(
            model=model,
            temperature=temperature,
            candidate_count=candidate_count,
        )
        return parsed_results, model_args

    def parse_line(
        self,
        line: str,
        placeholders: AbstractSet[str] | None = None,
    ) -> tuple[parsed_args_lib.ParsedArgs, parsed_args_lib.PostProcessingTokens]:
        """Parses the commandline and returns ParsedArgs and post-processing tokens.

        Args:
          line: The line to parse (usually contents from cell Magics).
          placeholders: Placeholders from prompts in the cell contents.

        Returns:
          A tuple of (parsed_args, post_processing_tokens).
        """
        tokens, post_processing_tokens = CmdLineParser._tokenize_line(line)

        parsed_args = self._get_parsed_args_from_cmd_line_tokens(
            tokens=tokens, placeholders=placeholders
        )

        # Special-case for "compare" command: because the prompts are compiled into
        # the left- and right-hand side functions rather than in the cell body, we
        # cannot examine the cell body to get the placeholders.
        #
        # Instead we parse the command line twice: once to get the left- and right-
        # functions, then we query the functions for their placeholders, then
        # parse the commandline again to validate the inputs.
        if parsed_args.cmd == parsed_args_lib.CommandName.COMPARE_CMD:
            assert parsed_args.lhs_name_and_fn is not None
            assert parsed_args.rhs_name_and_fn is not None
            _, lhs_fn = parsed_args.lhs_name_and_fn
            _, rhs_fn = parsed_args.rhs_name_and_fn
            parsed_args = self._get_parsed_args_from_cmd_line_tokens(
                tokens=tokens,
                placeholders=frozenset(lhs_fn.get_placeholders()).union(rhs_fn.get_placeholders()),
            )

        _validate_parsed_args(parsed_args)

        for expr in post_processing_tokens:
            post_process_utils.validate_one_post_processing_expression(expr)

        return parsed_args, post_processing_tokens

    def _get_parsed_args_from_cmd_line_tokens(
        self,
        tokens: Sequence[str],
        placeholders: AbstractSet[str] | None,
    ) -> parsed_args_lib.ParsedArgs:
        """Returns ParsedArgs from a tokenized command line."""
        # Create a new parser to avoid reusing the temporary argparse.Namespace
        # object.
        results = _create_parser(placeholders).parse_args(tokens)

        results_dict = vars(results)
        results_dict["cmd"] = parsed_args_lib.CommandName(results_dict["cmd"])

        results_dict, model_args = CmdLineParser._get_model_args(results_dict)
        results_dict["model_args"] = model_args

        return parsed_args_lib.ParsedArgs(**results_dict)

# === NexusCore/openenv\Lib\site-packages\jedi\inference\compiled\access.py ===
import inspect
import types
import traceback
import sys
import operator as op
from collections import namedtuple
import warnings
import re
import builtins
import typing
from pathlib import Path
from typing import Optional, Tuple

from jedi.inference.compiled.getattr_static import getattr_static

ALLOWED_GETITEM_TYPES = (str, list, tuple, bytes, bytearray, dict)

MethodDescriptorType = type(str.replace)
# These are not considered classes and access is granted even though they have
# a __class__ attribute.
NOT_CLASS_TYPES = (
    types.BuiltinFunctionType,
    types.CodeType,
    types.FrameType,
    types.FunctionType,
    types.GeneratorType,
    types.GetSetDescriptorType,
    types.LambdaType,
    types.MemberDescriptorType,
    types.MethodType,
    types.ModuleType,
    types.TracebackType,
    MethodDescriptorType,
    types.MappingProxyType,
    types.SimpleNamespace,
    types.DynamicClassAttribute,
)

# Those types don't exist in typing.
MethodDescriptorType = type(str.replace)
WrapperDescriptorType = type(set.__iter__)
# `object.__subclasshook__` is an already executed descriptor.
object_class_dict = type.__dict__["__dict__"].__get__(object)  # type: ignore[index]
ClassMethodDescriptorType = type(object_class_dict['__subclasshook__'])

_sentinel = object()

# Maps Python syntax to the operator module.
COMPARISON_OPERATORS = {
    '==': op.eq,
    '!=': op.ne,
    'is': op.is_,
    'is not': op.is_not,
    '<': op.lt,
    '<=': op.le,
    '>': op.gt,
    '>=': op.ge,
}

_OPERATORS = {
    '+': op.add,
    '-': op.sub,
}
_OPERATORS.update(COMPARISON_OPERATORS)

ALLOWED_DESCRIPTOR_ACCESS = (
    types.FunctionType,
    types.GetSetDescriptorType,
    types.MemberDescriptorType,
    MethodDescriptorType,
    WrapperDescriptorType,
    ClassMethodDescriptorType,
    staticmethod,
    classmethod,
)


def safe_getattr(obj, name, default=_sentinel):
    try:
        attr, is_get_descriptor = getattr_static(obj, name)
    except AttributeError:
        if default is _sentinel:
            raise
        return default
    else:
        if isinstance(attr, ALLOWED_DESCRIPTOR_ACCESS):
            # In case of descriptors that have get methods we cannot return
            # it's value, because that would mean code execution.
            # Since it's an isinstance call, code execution is still possible,
            # but this is not really a security feature, but much more of a
            # safety feature. Code execution is basically always possible when
            # a module is imported. This is here so people don't shoot
            # themselves in the foot.
            return getattr(obj, name)
    return attr


SignatureParam = namedtuple(
    'SignatureParam',
    'name has_default default default_string has_annotation annotation annotation_string kind_name'
)


def shorten_repr(func):
    def wrapper(self):
        r = func(self)
        if len(r) > 50:
            r = r[:50] + '..'
        return r
    return wrapper


def create_access(inference_state, obj):
    return inference_state.compiled_subprocess.get_or_create_access_handle(obj)


def load_module(inference_state, dotted_name, sys_path):
    temp, sys.path = sys.path, sys_path
    try:
        __import__(dotted_name)
    except ImportError:
        # If a module is "corrupt" or not really a Python module or whatever.
        warnings.warn(
            "Module %s not importable in path %s." % (dotted_name, sys_path),
            UserWarning,
            stacklevel=2,
        )
        return None
    except Exception:
        # Since __import__ pretty much makes code execution possible, just
        # catch any error here and print it.
        warnings.warn(
            "Cannot import:\n%s" % traceback.format_exc(), UserWarning, stacklevel=2
        )
        return None
    finally:
        sys.path = temp

    # Just access the cache after import, because of #59 as well as the very
    # complicated import structure of Python.
    module = sys.modules[dotted_name]
    return create_access_path(inference_state, module)


class AccessPath:
    def __init__(self, accesses):
        self.accesses = accesses


def create_access_path(inference_state, obj) -> AccessPath:
    access = create_access(inference_state, obj)
    return AccessPath(access.get_access_path_tuples())


def get_api_type(obj):
    if inspect.isclass(obj):
        return 'class'
    elif inspect.ismodule(obj):
        return 'module'
    elif inspect.isbuiltin(obj) or inspect.ismethod(obj) \
            or inspect.ismethoddescriptor(obj) or inspect.isfunction(obj):
        return 'function'
    # Everything else...
    return 'instance'


class DirectObjectAccess:
    def __init__(self, inference_state, obj):
        self._inference_state = inference_state
        self._obj = obj

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.get_repr())

    def _create_access(self, obj):
        return create_access(self._inference_state, obj)

    def _create_access_path(self, obj) -> AccessPath:
        return create_access_path(self._inference_state, obj)

    def py__bool__(self):
        return bool(self._obj)

    def py__file__(self) -> Optional[Path]:
        try:
            return Path(self._obj.__file__)
        except AttributeError:
            return None

    def py__doc__(self):
        return inspect.getdoc(self._obj) or ''

    def py__name__(self):
        if not _is_class_instance(self._obj) or \
                inspect.ismethoddescriptor(self._obj):  # slots
            cls = self._obj
        else:
            try:
                cls = self._obj.__class__
            except AttributeError:
                # happens with numpy.core.umath._UFUNC_API (you get it
                # automatically by doing `import numpy`.
                return None

        try:
            return cls.__name__
        except AttributeError:
            return None

    def py__mro__accesses(self):
        return tuple(self._create_access_path(cls) for cls in self._obj.__mro__[1:])

    def py__getitem__all_values(self):
        if isinstance(self._obj, dict):
            return [self._create_access_path(v) for v in self._obj.values()]
        if isinstance(self._obj, (list, tuple)):
            return [self._create_access_path(v) for v in self._obj]

        if self.is_instance():
            cls = DirectObjectAccess(self._inference_state, self._obj.__class__)
            return cls.py__getitem__all_values()

        try:
            getitem = self._obj.__getitem__
        except AttributeError:
            pass
        else:
            annotation = DirectObjectAccess(self._inference_state, getitem).get_return_annotation()
            if annotation is not None:
                return [annotation]
        return None

    def py__simple_getitem__(self, index, *, safe=True):
        if safe and type(self._obj) not in ALLOWED_GETITEM_TYPES:
            # Get rid of side effects, we won't call custom `__getitem__`s.
            return None

        return self._create_access_path(self._obj[index])

    def py__iter__list(self):
        try:
            iter_method = self._obj.__iter__
        except AttributeError:
            return None
        else:
            p = DirectObjectAccess(self._inference_state, iter_method).get_return_annotation()
            if p is not None:
                return [p]

        if type(self._obj) not in ALLOWED_GETITEM_TYPES:
            # Get rid of side effects, we won't call custom `__getitem__`s.
            return []

        lst = []
        for i, part in enumerate(self._obj):
            if i > 20:
                # Should not go crazy with large iterators
                break
            lst.append(self._create_access_path(part))
        return lst

    def py__class__(self):
        return self._create_access_path(self._obj.__class__)

    def py__bases__(self):
        return [self._create_access_path(base) for base in self._obj.__bases__]

    def py__path__(self):
        paths = getattr(self._obj, '__path__', None)
        # Avoid some weird hacks that would just fail, because they cannot be
        # used by pickle.
        if not isinstance(paths, list) \
                or not all(isinstance(p, str) for p in paths):
            return None
        return paths

    @shorten_repr
    def get_repr(self):
        if inspect.ismodule(self._obj):
            return repr(self._obj)
        # Try to avoid execution of the property.
        if safe_getattr(self._obj, '__module__', default='') == 'builtins':
            return repr(self._obj)

        type_ = type(self._obj)
        if type_ == type:
            return type.__repr__(self._obj)

        if safe_getattr(type_, '__module__', default='') == 'builtins':
            # Allow direct execution of repr for builtins.
            return repr(self._obj)
        return object.__repr__(self._obj)

    def is_class(self):
        return inspect.isclass(self._obj)

    def is_function(self):
        return inspect.isfunction(self._obj) or inspect.ismethod(self._obj)

    def is_module(self):
        return inspect.ismodule(self._obj)

    def is_instance(self):
        return _is_class_instance(self._obj)

    def ismethoddescriptor(self):
        return inspect.ismethoddescriptor(self._obj)

    def get_qualified_names(self):
        def try_to_get_name(obj):
            return getattr(obj, '__qualname__', getattr(obj, '__name__', None))

        if self.is_module():
            return ()
        name = try_to_get_name(self._obj)
        if name is None:
            name = try_to_get_name(type(self._obj))
            if name is None:
                return ()
        return tuple(name.split('.'))

    def dir(self):
        return dir(self._obj)

    def has_iter(self):
        try:
            iter(self._obj)
            return True
        except TypeError:
            return False

    def is_allowed_getattr(self, name, safe=True) -> Tuple[bool, bool, Optional[AccessPath]]:
        # TODO this API is ugly.
        try:
            attr, is_get_descriptor = getattr_static(self._obj, name)
        except AttributeError:
            if not safe:
                # Unsafe is mostly used to check for __getattr__/__getattribute__.
                # getattr_static works for properties, but the underscore methods
                # are just ignored (because it's safer and avoids more code
                # execution). See also GH #1378.

                # Avoid warnings, see comment in the next function.
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("always")
                    try:
                        return hasattr(self._obj, name), False, None
                    except Exception:
                        # Obviously has an attribute (probably a property) that
                        # gets executed, so just avoid all exceptions here.
                        pass
            return False, False, None
        else:
            if is_get_descriptor and type(attr) not in ALLOWED_DESCRIPTOR_ACCESS:
                if isinstance(attr, property):
                    if hasattr(attr.fget, '__annotations__'):
                        a = DirectObjectAccess(self._inference_state, attr.fget)
                        return True, True, a.get_return_annotation()
                # In case of descriptors that have get methods we cannot return
                # it's value, because that would mean code execution.
                return True, True, None
        return True, False, None

    def getattr_paths(self, name, default=_sentinel):
        try:
            # Make sure no warnings are printed here, this is autocompletion,
            # warnings should not be shown. See also GH #1383.
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                return_obj = getattr(self._obj, name)
        except Exception as e:
            if default is _sentinel:
                if isinstance(e, AttributeError):
                    # Happens e.g. in properties of
                    # PyQt4.QtGui.QStyleOptionComboBox.currentText
                    # -> just set it to None
                    raise
                # Just in case anything happens, return an AttributeError. It
                # should not crash.
                raise AttributeError
            return_obj = default
        access = self._create_access(return_obj)
        if inspect.ismodule(return_obj):
            return [access]

        try:
            module = return_obj.__module__
        except AttributeError:
            pass
        else:
            if module is not None and isinstance(module, str):
                try:
                    __import__(module)
                    # For some modules like _sqlite3, the __module__ for classes is
                    # different, in this case it's sqlite3. So we have to try to
                    # load that "original" module, because it's not loaded yet. If
                    # we don't do that, we don't really have a "parent" module and
                    # we would fall back to builtins.
                except ImportError:
                    pass

        module = inspect.getmodule(return_obj)
        if module is None:
            module = inspect.getmodule(type(return_obj))
            if module is None:
                module = builtins
        return [self._create_access(module), access]

    def get_safe_value(self):
        if type(self._obj) in (bool, bytes, float, int, str, slice) or self._obj is None:
            return self._obj
        raise ValueError("Object is type %s and not simple" % type(self._obj))

    def get_api_type(self):
        return get_api_type(self._obj)

    def get_array_type(self):
        if isinstance(self._obj, dict):
            return 'dict'
        return None

    def get_key_paths(self):
        def iter_partial_keys():
            # We could use list(keys()), but that might take a lot more memory.
            for (i, k) in enumerate(self._obj.keys()):
                # Limit key listing at some point. This is artificial, but this
                # way we don't get stalled because of slow completions
                if i > 50:
                    break
                yield k

        return [self._create_access_path(k) for k in iter_partial_keys()]

    def get_access_path_tuples(self):
        accesses = [create_access(self._inference_state, o) for o in self._get_objects_path()]
        return [(access.py__name__(), access) for access in accesses]

    def _get_objects_path(self):
        def get():
            obj = self._obj
            yield obj
            try:
                obj = obj.__objclass__
            except AttributeError:
                pass
            else:
                yield obj

            try:
                # Returns a dotted string path.
                imp_plz = obj.__module__
            except AttributeError:
                # Unfortunately in some cases like `int` there's no __module__
                if not inspect.ismodule(obj):
                    yield builtins
            else:
                if imp_plz is None:
                    # Happens for example in `(_ for _ in []).send.__module__`.
                    yield builtins
                else:
                    try:
                        yield sys.modules[imp_plz]
                    except KeyError:
                        # __module__ can be something arbitrary that doesn't exist.
                        yield builtins

        return list(reversed(list(get())))

    def execute_operation(self, other_access_handle, operator):
        other_access = other_access_handle.access
        op = _OPERATORS[operator]
        return self._create_access_path(op(self._obj, other_access._obj))

    def get_annotation_name_and_args(self):
        """
        Returns Tuple[Optional[str], Tuple[AccessPath, ...]]
        """
        name = None
        args = ()
        if safe_getattr(self._obj, '__module__', default='') == 'typing':
            m = re.match(r'typing.(\w+)\[', repr(self._obj))
            if m is not None:
                name = m.group(1)

                import typing
                if sys.version_info >= (3, 8):
                    args = typing.get_args(self._obj)
                else:
                    args = safe_getattr(self._obj, '__args__', default=None)
        return name, tuple(self._create_access_path(arg) for arg in args)

    def needs_type_completions(self):
        return inspect.isclass(self._obj) and self._obj != type

    def _annotation_to_str(self, annotation):
        return inspect.formatannotation(annotation)

    def get_signature_params(self):
        return [
            SignatureParam(
                name=p.name,
                has_default=p.default is not p.empty,
                default=self._create_access_path(p.default),
                default_string=repr(p.default),
                has_annotation=p.annotation is not p.empty,
                annotation=self._create_access_path(p.annotation),
                annotation_string=self._annotation_to_str(p.annotation),
                kind_name=str(p.kind)
            ) for p in self._get_signature().parameters.values()
        ]

    def _get_signature(self):
        obj = self._obj
        try:
            return inspect.signature(obj)
        except (RuntimeError, TypeError):
            # Reading the code of the function in Python 3.6 implies there are
            # at least these errors that might occur if something is wrong with
            # the signature. In that case we just want a simple escape for now.
            raise ValueError

    def get_return_annotation(self) -> Optional[AccessPath]:
        try:
            o = self._obj.__annotations__.get('return')
        except AttributeError:
            return None

        if o is None:
            return None

        try:
            o = typing.get_type_hints(self._obj).get('return')
        except Exception:
            pass

        return self._create_access_path(o)

    def negate(self):
        return self._create_access_path(-self._obj)

    def get_dir_infos(self):
        """
        Used to return a couple of infos that are needed when accessing the sub
        objects of an objects
        """
        tuples = dict(
            (name, self.is_allowed_getattr(name))
            for name in self.dir()
        )
        return self.needs_type_completions(), tuples


def _is_class_instance(obj):
    """Like inspect.* methods."""
    try:
        cls = obj.__class__
    except AttributeError:
        return False
    else:
        # The isinstance check for cls is just there so issubclass doesn't
        # raise an exception.
        return cls != type and isinstance(cls, type) and not issubclass(cls, NOT_CLASS_TYPES)

# === NexusCore/openenv\Lib\site-packages\nltk\twitter\twitterclient.py ===
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
NLTK Twitter client

This module offers methods for collecting and processing Tweets. Most of the
functionality depends on access to the Twitter APIs, and this is handled via
the third party Twython library.

If one of the methods below returns an integer, it is probably a `Twitter
error code <https://dev.twitter.com/overview/api/response-codes>`_. For
example, the response of '420' means that you have reached the limit of the
requests you can currently make to the Twitter API. Currently, `rate limits
for the search API <https://dev.twitter.com/rest/public/rate-limiting>`_ are
divided into 15 minute windows.
"""

import datetime
import gzip
import itertools
import json
import os
import time

import requests
from twython import Twython, TwythonStreamer
from twython.exceptions import TwythonError, TwythonRateLimitError

from nltk.twitter.api import BasicTweetHandler, TweetHandlerI
from nltk.twitter.util import credsfromfile, guess_path


class Streamer(TwythonStreamer):
    """
    Retrieve data from the Twitter Streaming API.

    The streaming API requires
    `OAuth 1.0 <https://en.wikipedia.org/wiki/OAuth>`_ authentication.
    """

    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):
        self.handler = None
        self.do_continue = True
        TwythonStreamer.__init__(
            self, app_key, app_secret, oauth_token, oauth_token_secret
        )

    def register(self, handler):
        """
        Register a method for handling Tweets.

        :param TweetHandlerI handler: method for viewing
        """
        self.handler = handler

    def on_success(self, data):
        """
        :param data: response from Twitter API
        """
        if self.do_continue:
            if self.handler is not None:
                if "text" in data:
                    self.handler.counter += 1
                    self.handler.handle(data)
                    self.do_continue = self.handler.do_continue()
            else:
                raise ValueError("No data handler has been registered.")
        else:
            self.disconnect()
            self.handler.on_finish()

    def on_error(self, status_code, data):
        """
        :param status_code: The status code returned by the Twitter API
        :param data: The response from Twitter API

        """
        print(status_code)

    def sample(self):
        """
        Wrapper for 'statuses / sample' API call
        """
        while self.do_continue:
            # Stream in an endless loop until limit is reached. See twython
            # issue 288: https://github.com/ryanmcgrath/twython/issues/288
            # colditzjb commented on 9 Dec 2014

            try:
                self.statuses.sample()
            except requests.exceptions.ChunkedEncodingError as e:
                if e is not None:
                    print(f"Error (stream will continue): {e}")
                continue

    def filter(self, track="", follow="", lang="en"):
        """
        Wrapper for 'statuses / filter' API call
        """
        while self.do_continue:
            # Stream in an endless loop until limit is reached

            try:
                if track == "" and follow == "":
                    msg = "Please supply a value for 'track', 'follow'"
                    raise ValueError(msg)
                self.statuses.filter(track=track, follow=follow, lang=lang)
            except requests.exceptions.ChunkedEncodingError as e:
                if e is not None:
                    print(f"Error (stream will continue): {e}")
                continue


class Query(Twython):
    """
    Retrieve data from the Twitter REST API.
    """

    def __init__(self, app_key, app_secret, oauth_token, oauth_token_secret):
        """
        :param app_key: (optional) Your applications key
        :param app_secret: (optional) Your applications secret key
        :param oauth_token: (optional) When using **OAuth 1**, combined with
            oauth_token_secret to make authenticated calls
        :param oauth_token_secret: (optional) When using **OAuth 1** combined
            with oauth_token to make authenticated calls
        """
        self.handler = None
        self.do_continue = True
        Twython.__init__(self, app_key, app_secret, oauth_token, oauth_token_secret)

    def register(self, handler):
        """
        Register a method for handling Tweets.

        :param TweetHandlerI handler: method for viewing or writing Tweets to a file.
        """
        self.handler = handler

    def expand_tweetids(self, ids_f, verbose=True):
        """
        Given a file object containing a list of Tweet IDs, fetch the
        corresponding full Tweets from the Twitter API.

        The API call `statuses/lookup` will fail to retrieve a Tweet if the
        user has deleted it.

        This call to the Twitter API is rate-limited. See
        <https://dev.twitter.com/rest/reference/get/statuses/lookup> for details.

        :param ids_f: input file object consisting of Tweet IDs, one to a line
        :return: iterable of Tweet objects in JSON format
        """
        ids = [line.strip() for line in ids_f if line]

        if verbose:
            print(f"Counted {len(ids)} Tweet IDs in {ids_f}.")

        # The Twitter endpoint takes lists of up to 100 ids, so we chunk the
        # ids.
        id_chunks = [ids[i : i + 100] for i in range(0, len(ids), 100)]

        chunked_tweets = (self.lookup_status(id=chunk) for chunk in id_chunks)

        return itertools.chain.from_iterable(chunked_tweets)

    def _search_tweets(self, keywords, limit=100, lang="en"):
        """
        Assumes that the handler has been informed. Fetches Tweets from
        search_tweets generator output and passses them to handler

        :param str keywords: A list of query terms to search for, written as\
        a comma-separated string.
        :param int limit: Number of Tweets to process
        :param str lang: language
        """
        while True:
            tweets = self.search_tweets(
                keywords=keywords, limit=limit, lang=lang, max_id=self.handler.max_id
            )
            for tweet in tweets:
                self.handler.handle(tweet)
            if not (self.handler.do_continue() and self.handler.repeat):
                break
        self.handler.on_finish()

    def search_tweets(
        self,
        keywords,
        limit=100,
        lang="en",
        max_id=None,
        retries_after_twython_exception=0,
    ):
        """
        Call the REST API ``'search/tweets'`` endpoint with some plausible
        defaults. See `the Twitter search documentation
        <https://dev.twitter.com/rest/public/search>`_ for more information
        about admissible search parameters.

        :param str keywords: A list of query terms to search for, written as\
        a comma-separated string
        :param int limit: Number of Tweets to process
        :param str lang: language
        :param int max_id: id of the last tweet fetched
        :param int retries_after_twython_exception: number of retries when\
        searching Tweets before raising an exception
        :rtype: python generator
        """
        if not self.handler:
            # if no handler is provided, `BasicTweetHandler` provides minimum
            # functionality for limiting the number of Tweets retrieved
            self.handler = BasicTweetHandler(limit=limit)

        count_from_query = 0
        if max_id:
            self.handler.max_id = max_id
        else:
            results = self.search(
                q=keywords, count=min(100, limit), lang=lang, result_type="recent"
            )
            count = len(results["statuses"])
            if count == 0:
                print("No Tweets available through REST API for those keywords")
                return
            count_from_query = count
            self.handler.max_id = results["statuses"][count - 1]["id"] - 1

            for result in results["statuses"]:
                yield result
                self.handler.counter += 1
                if self.handler.do_continue() == False:
                    return

        # Pagination loop: keep fetching Tweets until the desired count is
        # reached while dealing with Twitter rate limits.
        retries = 0
        while count_from_query < limit:
            try:
                mcount = min(100, limit - count_from_query)
                results = self.search(
                    q=keywords,
                    count=mcount,
                    lang=lang,
                    max_id=self.handler.max_id,
                    result_type="recent",
                )
            except TwythonRateLimitError as e:
                print(f"Waiting for 15 minutes -{e}")
                time.sleep(15 * 60)  # wait 15 minutes
                continue
            except TwythonError as e:
                print(f"Fatal error in Twython request -{e}")
                if retries_after_twython_exception == retries:
                    raise e
                retries += 1

            count = len(results["statuses"])
            if count == 0:
                print("No more Tweets available through rest api")
                return
            count_from_query += count
            # the max_id is also present in the Tweet metadata
            # results['search_metadata']['next_results'], but as part of a
            # query and difficult to fetch. This is doing the equivalent
            # (last tweet id minus one)
            self.handler.max_id = results["statuses"][count - 1]["id"] - 1

            for result in results["statuses"]:
                yield result
                self.handler.counter += 1
                if self.handler.do_continue() == False:
                    return

    def user_info_from_id(self, userids):
        """
        Convert a list of userIDs into a variety of information about the users.

        See <https://dev.twitter.com/rest/reference/get/users/show>.

        :param list userids: A list of integer strings corresponding to Twitter userIDs
        :rtype: list(json)
        """
        return [self.show_user(user_id=userid) for userid in userids]

    def user_tweets(self, screen_name, limit, include_rts="false"):
        """
        Return a collection of the most recent Tweets posted by the user

        :param str user: The user's screen name; the initial '@' symbol\
        should be omitted
        :param int limit: The number of Tweets to recover; 200 is the maximum allowed
        :param str include_rts: Whether to include statuses which have been\
        retweeted by the user; possible values are 'true' and 'false'
        """
        data = self.get_user_timeline(
            screen_name=screen_name, count=limit, include_rts=include_rts
        )
        for item in data:
            self.handler.handle(item)


class Twitter:
    """
    Wrapper class with restricted functionality and fewer options.
    """

    def __init__(self):
        self._oauth = credsfromfile()
        self.streamer = Streamer(**self._oauth)
        self.query = Query(**self._oauth)

    def tweets(
        self,
        keywords="",
        follow="",
        to_screen=True,
        stream=True,
        limit=100,
        date_limit=None,
        lang="en",
        repeat=False,
        gzip_compress=False,
    ):
        """
        Process some Tweets in a simple manner.

        :param str keywords: Keywords to use for searching or filtering
        :param list follow: UserIDs to use for filtering Tweets from the public stream
        :param bool to_screen: If `True`, display the tweet texts on the screen,\
            otherwise print to a file

        :param bool stream: If `True`, use the live public stream,\
            otherwise search past public Tweets

        :param int limit: The number of data items to process in the current\
            round of processing.

        :param tuple date_limit: The date at which to stop collecting\
            new data. This should be entered as a tuple which can serve as the\
            argument to `datetime.datetime`.\
            E.g. `date_limit=(2015, 4, 1, 12, 40)` for 12:30 pm on April 1 2015.
            Note that, in the case of streaming, this is the maximum date, i.e.\
            a date in the future; if not, it is the minimum date, i.e. a date\
            in the past

        :param str lang: language

        :param bool repeat: A flag to determine whether multiple files should\
            be written. If `True`, the length of each file will be set by the\
            value of `limit`. Use only if `to_screen` is `False`. See also
            :py:func:`handle`.

        :param gzip_compress: if `True`, output files are compressed with gzip.
        """
        if stream:
            upper_date_limit = date_limit
            lower_date_limit = None
        else:
            upper_date_limit = None
            lower_date_limit = date_limit

        if to_screen:
            handler = TweetViewer(
                limit=limit,
                upper_date_limit=upper_date_limit,
                lower_date_limit=lower_date_limit,
            )
        else:
            handler = TweetWriter(
                limit=limit,
                upper_date_limit=upper_date_limit,
                lower_date_limit=lower_date_limit,
                repeat=repeat,
                gzip_compress=gzip_compress,
            )

        if to_screen:
            handler = TweetViewer(limit=limit)
        else:
            if stream:
                upper_date_limit = date_limit
                lower_date_limit = None
            else:
                upper_date_limit = None
                lower_date_limit = date_limit

            handler = TweetWriter(
                limit=limit,
                upper_date_limit=upper_date_limit,
                lower_date_limit=lower_date_limit,
                repeat=repeat,
                gzip_compress=gzip_compress,
            )

        if stream:
            self.streamer.register(handler)
            if keywords == "" and follow == "":
                self.streamer.sample()
            else:
                self.streamer.filter(track=keywords, follow=follow, lang=lang)
        else:
            self.query.register(handler)
            if keywords == "":
                raise ValueError("Please supply at least one keyword to search for.")
            else:
                self.query._search_tweets(keywords, limit=limit, lang=lang)


class TweetViewer(TweetHandlerI):
    """
    Handle data by sending it to the terminal.
    """

    def handle(self, data):
        """
        Direct data to `sys.stdout`

        :return: return ``False`` if processing should cease, otherwise return ``True``.
        :rtype: bool
        :param data: Tweet object returned by Twitter API
        """
        text = data["text"]
        print(text)

        self.check_date_limit(data)
        if self.do_stop:
            return

    def on_finish(self):
        print(f"Written {self.counter} Tweets")


class TweetWriter(TweetHandlerI):
    """
    Handle data by writing it to a file.
    """

    def __init__(
        self,
        limit=2000,
        upper_date_limit=None,
        lower_date_limit=None,
        fprefix="tweets",
        subdir="twitter-files",
        repeat=False,
        gzip_compress=False,
    ):
        """
        The difference between the upper and lower date limits depends on
        whether Tweets are coming in an ascending date order (i.e. when
        streaming) or descending date order (i.e. when searching past Tweets).

        :param int limit: number of data items to process in the current\
        round of processing.

        :param tuple upper_date_limit: The date at which to stop collecting new\
        data. This should be entered as a tuple which can serve as the\
        argument to `datetime.datetime`. E.g. `upper_date_limit=(2015, 4, 1, 12,\
        40)` for 12:30 pm on April 1 2015.

        :param tuple lower_date_limit: The date at which to stop collecting new\
        data. See `upper_data_limit` for formatting.

        :param str fprefix: The prefix to use in creating file names for Tweet\
        collections.

        :param str subdir: The name of the directory where Tweet collection\
        files should be stored.

        :param bool repeat: flag to determine whether multiple files should be\
        written. If `True`, the length of each file will be set by the value\
        of `limit`. See also :py:func:`handle`.

        :param gzip_compress: if `True`, output files are compressed with gzip.
        """
        self.fprefix = fprefix
        self.subdir = guess_path(subdir)
        self.gzip_compress = gzip_compress
        self.fname = self.timestamped_file()
        self.repeat = repeat
        self.output = None
        TweetHandlerI.__init__(self, limit, upper_date_limit, lower_date_limit)

    def timestamped_file(self):
        """
        :return: timestamped file name
        :rtype: str
        """
        subdir = self.subdir
        fprefix = self.fprefix
        if subdir:
            if not os.path.exists(subdir):
                os.mkdir(subdir)

        fname = os.path.join(subdir, fprefix)
        fmt = "%Y%m%d-%H%M%S"
        timestamp = datetime.datetime.now().strftime(fmt)
        if self.gzip_compress:
            suffix = ".gz"
        else:
            suffix = ""
        outfile = f"{fname}.{timestamp}.json{suffix}"
        return outfile

    def handle(self, data):
        """
        Write Twitter data as line-delimited JSON into one or more files.

        :return: return `False` if processing should cease, otherwise return `True`.
        :param data: tweet object returned by Twitter API
        """
        if self.startingup:
            if self.gzip_compress:
                self.output = gzip.open(self.fname, "w")
            else:
                self.output = open(self.fname, "w")
            print(f"Writing to {self.fname}")

        json_data = json.dumps(data)
        if self.gzip_compress:
            self.output.write((json_data + "\n").encode("utf-8"))
        else:
            self.output.write(json_data + "\n")

        self.check_date_limit(data)
        if self.do_stop:
            return

        self.startingup = False

    def on_finish(self):
        print(f"Written {self.counter} Tweets")
        if self.output:
            self.output.close()

    def do_continue(self):
        if self.repeat == False:
            return TweetHandlerI.do_continue(self)

        if self.do_stop:
            # stop for a functional cause (e.g. date limit)
            return False

        if self.counter == self.limit:
            # repeat is True, thus close output file and
            # create a new one
            self._restart_file()
        return True

    def _restart_file(self):
        self.on_finish()
        self.fname = self.timestamped_file()
        self.startingup = True
        self.counter = 0

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\cookies.py ===
"""
requests.cookies
~~~~~~~~~~~~~~~~

Compatibility code to be able to use `http.cookiejar.CookieJar` with requests.

requests.utils imports from here, so be careful with imports.
"""

import calendar
import copy
import time

from ._internal_utils import to_native_string
from .compat import Morsel, MutableMapping, cookielib, urlparse, urlunparse

try:
    import threading
except ImportError:
    import dummy_threading as threading


class MockRequest:
    """Wraps a `requests.Request` to mimic a `urllib2.Request`.

    The code in `http.cookiejar.CookieJar` expects this interface in order to correctly
    manage cookie policies, i.e., determine whether a cookie can be set, given the
    domains of the request and the cookie.

    The original request object is read-only. The client is responsible for collecting
    the new headers via `get_new_headers()` and interpreting them appropriately. You
    probably want `get_cookie_header`, defined below.
    """

    def __init__(self, request):
        self._r = request
        self._new_headers = {}
        self.type = urlparse(self._r.url).scheme

    def get_type(self):
        return self.type

    def get_host(self):
        return urlparse(self._r.url).netloc

    def get_origin_req_host(self):
        return self.get_host()

    def get_full_url(self):
        # Only return the response's URL if the user hadn't set the Host
        # header
        if not self._r.headers.get("Host"):
            return self._r.url
        # If they did set it, retrieve it and reconstruct the expected domain
        host = to_native_string(self._r.headers["Host"], encoding="utf-8")
        parsed = urlparse(self._r.url)
        # Reconstruct the URL as we expect it
        return urlunparse(
            [
                parsed.scheme,
                host,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ]
        )

    def is_unverifiable(self):
        return True

    def has_header(self, name):
        return name in self._r.headers or name in self._new_headers

    def get_header(self, name, default=None):
        return self._r.headers.get(name, self._new_headers.get(name, default))

    def add_header(self, key, val):
        """cookiejar has no legitimate use for this method; add it back if you find one."""
        raise NotImplementedError(
            "Cookie headers should be added with add_unredirected_header()"
        )

    def add_unredirected_header(self, name, value):
        self._new_headers[name] = value

    def get_new_headers(self):
        return self._new_headers

    @property
    def unverifiable(self):
        return self.is_unverifiable()

    @property
    def origin_req_host(self):
        return self.get_origin_req_host()

    @property
    def host(self):
        return self.get_host()


class MockResponse:
    """Wraps a `httplib.HTTPMessage` to mimic a `urllib.addinfourl`.

    ...what? Basically, expose the parsed HTTP headers from the server response
    the way `http.cookiejar` expects to see them.
    """

    def __init__(self, headers):
        """Make a MockResponse for `cookiejar` to read.

        :param headers: a httplib.HTTPMessage or analogous carrying the headers
        """
        self._headers = headers

    def info(self):
        return self._headers

    def getheaders(self, name):
        self._headers.getheaders(name)


def extract_cookies_to_jar(jar, request, response):
    """Extract the cookies from the response into a CookieJar.

    :param jar: http.cookiejar.CookieJar (not necessarily a RequestsCookieJar)
    :param request: our own requests.Request object
    :param response: urllib3.HTTPResponse object
    """
    if not (hasattr(response, "_original_response") and response._original_response):
        return
    # the _original_response field is the wrapped httplib.HTTPResponse object,
    req = MockRequest(request)
    # pull out the HTTPMessage with the headers and put it in the mock:
    res = MockResponse(response._original_response.msg)
    jar.extract_cookies(res, req)


def get_cookie_header(jar, request):
    """
    Produce an appropriate Cookie header string to be sent with `request`, or None.

    :rtype: str
    """
    r = MockRequest(request)
    jar.add_cookie_header(r)
    return r.get_new_headers().get("Cookie")


def remove_cookie_by_name(cookiejar, name, domain=None, path=None):
    """Unsets a cookie by name, by default over all domains and paths.

    Wraps CookieJar.clear(), is O(n).
    """
    clearables = []
    for cookie in cookiejar:
        if cookie.name != name:
            continue
        if domain is not None and domain != cookie.domain:
            continue
        if path is not None and path != cookie.path:
            continue
        clearables.append((cookie.domain, cookie.path, cookie.name))

    for domain, path, name in clearables:
        cookiejar.clear(domain, path, name)


class CookieConflictError(RuntimeError):
    """There are two cookies that meet the criteria specified in the cookie jar.
    Use .get and .set and include domain and path args in order to be more specific.
    """


class RequestsCookieJar(cookielib.CookieJar, MutableMapping):
    """Compatibility class; is a http.cookiejar.CookieJar, but exposes a dict
    interface.

    This is the CookieJar we create by default for requests and sessions that
    don't specify one, since some clients may expect response.cookies and
    session.cookies to support dict operations.

    Requests does not use the dict interface internally; it's just for
    compatibility with external client code. All requests code should work
    out of the box with externally provided instances of ``CookieJar``, e.g.
    ``LWPCookieJar`` and ``FileCookieJar``.

    Unlike a regular CookieJar, this class is pickleable.

    .. warning:: dictionary operations that are normally O(1) may be O(n).
    """

    def get(self, name, default=None, domain=None, path=None):
        """Dict-like get() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.

        .. warning:: operation is O(n), not O(1).
        """
        try:
            return self._find_no_duplicates(name, domain, path)
        except KeyError:
            return default

    def set(self, name, value, **kwargs):
        """Dict-like set() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.
        """
        # support client code that unsets cookies by assignment of a None value:
        if value is None:
            remove_cookie_by_name(
                self, name, domain=kwargs.get("domain"), path=kwargs.get("path")
            )
            return

        if isinstance(value, Morsel):
            c = morsel_to_cookie(value)
        else:
            c = create_cookie(name, value, **kwargs)
        self.set_cookie(c)
        return c

    def iterkeys(self):
        """Dict-like iterkeys() that returns an iterator of names of cookies
        from the jar.

        .. seealso:: itervalues() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.name

    def keys(self):
        """Dict-like keys() that returns a list of names of cookies from the
        jar.

        .. seealso:: values() and items().
        """
        return list(self.iterkeys())

    def itervalues(self):
        """Dict-like itervalues() that returns an iterator of values of cookies
        from the jar.

        .. seealso:: iterkeys() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.value

    def values(self):
        """Dict-like values() that returns a list of values of cookies from the
        jar.

        .. seealso:: keys() and items().
        """
        return list(self.itervalues())

    def iteritems(self):
        """Dict-like iteritems() that returns an iterator of name-value tuples
        from the jar.

        .. seealso:: iterkeys() and itervalues().
        """
        for cookie in iter(self):
            yield cookie.name, cookie.value

    def items(self):
        """Dict-like items() that returns a list of name-value tuples from the
        jar. Allows client-code to call ``dict(RequestsCookieJar)`` and get a
        vanilla python dict of key value pairs.

        .. seealso:: keys() and values().
        """
        return list(self.iteritems())

    def list_domains(self):
        """Utility method to list all the domains in the jar."""
        domains = []
        for cookie in iter(self):
            if cookie.domain not in domains:
                domains.append(cookie.domain)
        return domains

    def list_paths(self):
        """Utility method to list all the paths in the jar."""
        paths = []
        for cookie in iter(self):
            if cookie.path not in paths:
                paths.append(cookie.path)
        return paths

    def multiple_domains(self):
        """Returns True if there are multiple domains in the jar.
        Returns False otherwise.

        :rtype: bool
        """
        domains = []
        for cookie in iter(self):
            if cookie.domain is not None and cookie.domain in domains:
                return True
            domains.append(cookie.domain)
        return False  # there is only one domain in jar

    def get_dict(self, domain=None, path=None):
        """Takes as an argument an optional domain and path and returns a plain
        old Python dict of name-value pairs of cookies that meet the
        requirements.

        :rtype: dict
        """
        dictionary = {}
        for cookie in iter(self):
            if (domain is None or cookie.domain == domain) and (
                path is None or cookie.path == path
            ):
                dictionary[cookie.name] = cookie.value
        return dictionary

    def __contains__(self, name):
        try:
            return super().__contains__(name)
        except CookieConflictError:
            return True

    def __getitem__(self, name):
        """Dict-like __getitem__() for compatibility with client code. Throws
        exception if there are more than one cookie with name. In that case,
        use the more explicit get() method instead.

        .. warning:: operation is O(n), not O(1).
        """
        return self._find_no_duplicates(name)

    def __setitem__(self, name, value):
        """Dict-like __setitem__ for compatibility with client code. Throws
        exception if there is already a cookie of that name in the jar. In that
        case, use the more explicit set() method instead.
        """
        self.set(name, value)

    def __delitem__(self, name):
        """Deletes a cookie given a name. Wraps ``http.cookiejar.CookieJar``'s
        ``remove_cookie_by_name()``.
        """
        remove_cookie_by_name(self, name)

    def set_cookie(self, cookie, *args, **kwargs):
        if (
            hasattr(cookie.value, "startswith")
            and cookie.value.startswith('"')
            and cookie.value.endswith('"')
        ):
            cookie.value = cookie.value.replace('\\"', "")
        return super().set_cookie(cookie, *args, **kwargs)

    def update(self, other):
        """Updates this jar with cookies from another CookieJar or dict-like"""
        if isinstance(other, cookielib.CookieJar):
            for cookie in other:
                self.set_cookie(copy.copy(cookie))
        else:
            super().update(other)

    def _find(self, name, domain=None, path=None):
        """Requests uses this method internally to get cookie values.

        If there are conflicting cookies, _find arbitrarily chooses one.
        See _find_no_duplicates if you want an exception thrown if there are
        conflicting cookies.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :return: cookie.value
        """
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        return cookie.value

        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def _find_no_duplicates(self, name, domain=None, path=None):
        """Both ``__get_item__`` and ``get`` call this function: it's never
        used elsewhere in Requests.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :raises KeyError: if cookie is not found
        :raises CookieConflictError: if there are multiple cookies
            that match name and optionally domain and path
        :return: cookie.value
        """
        toReturn = None
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        if toReturn is not None:
                            # if there are multiple cookies that meet passed in criteria
                            raise CookieConflictError(
                                f"There are multiple cookies with name, {name!r}"
                            )
                        # we will eventually return this as long as no cookie conflict
                        toReturn = cookie.value

        if toReturn:
            return toReturn
        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def __getstate__(self):
        """Unlike a normal CookieJar, this class is pickleable."""
        state = self.__dict__.copy()
        # remove the unpickleable RLock object
        state.pop("_cookies_lock")
        return state

    def __setstate__(self, state):
        """Unlike a normal CookieJar, this class is pickleable."""
        self.__dict__.update(state)
        if "_cookies_lock" not in self.__dict__:
            self._cookies_lock = threading.RLock()

    def copy(self):
        """Return a copy of this RequestsCookieJar."""
        new_cj = RequestsCookieJar()
        new_cj.set_policy(self.get_policy())
        new_cj.update(self)
        return new_cj

    def get_policy(self):
        """Return the CookiePolicy instance used."""
        return self._policy


def _copy_cookie_jar(jar):
    if jar is None:
        return None

    if hasattr(jar, "copy"):
        # We're dealing with an instance of RequestsCookieJar
        return jar.copy()
    # We're dealing with a generic CookieJar instance
    new_jar = copy.copy(jar)
    new_jar.clear()
    for cookie in jar:
        new_jar.set_cookie(copy.copy(cookie))
    return new_jar


def create_cookie(name, value, **kwargs):
    """Make a cookie from underspecified parameters.

    By default, the pair of `name` and `value` will be set for the domain ''
    and sent on every request (this is sometimes called a "supercookie").
    """
    result = {
        "version": 0,
        "name": name,
        "value": value,
        "port": None,
        "domain": "",
        "path": "/",
        "secure": False,
        "expires": None,
        "discard": True,
        "comment": None,
        "comment_url": None,
        "rest": {"HttpOnly": None},
        "rfc2109": False,
    }

    badargs = set(kwargs) - set(result)
    if badargs:
        raise TypeError(
            f"create_cookie() got unexpected keyword arguments: {list(badargs)}"
        )

    result.update(kwargs)
    result["port_specified"] = bool(result["port"])
    result["domain_specified"] = bool(result["domain"])
    result["domain_initial_dot"] = result["domain"].startswith(".")
    result["path_specified"] = bool(result["path"])

    return cookielib.Cookie(**result)


def morsel_to_cookie(morsel):
    """Convert a Morsel object into a Cookie containing the one k/v pair."""

    expires = None
    if morsel["max-age"]:
        try:
            expires = int(time.time() + int(morsel["max-age"]))
        except ValueError:
            raise TypeError(f"max-age: {morsel['max-age']} must be integer")
    elif morsel["expires"]:
        time_template = "%a, %d-%b-%Y %H:%M:%S GMT"
        expires = calendar.timegm(time.strptime(morsel["expires"], time_template))
    return create_cookie(
        comment=morsel["comment"],
        comment_url=bool(morsel["comment"]),
        discard=False,
        domain=morsel["domain"],
        expires=expires,
        name=morsel.key,
        path=morsel["path"],
        port=None,
        rest={"HttpOnly": morsel["httponly"]},
        rfc2109=False,
        secure=bool(morsel["secure"]),
        value=morsel.value,
        version=morsel["version"] or 0,
    )


def cookiejar_from_dict(cookie_dict, cookiejar=None, overwrite=True):
    """Returns a CookieJar from a key/value dictionary.

    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :param cookiejar: (optional) A cookiejar to add the cookies to.
    :param overwrite: (optional) If False, will not replace cookies
        already in the jar with new ones.
    :rtype: CookieJar
    """
    if cookiejar is None:
        cookiejar = RequestsCookieJar()

    if cookie_dict is not None:
        names_from_jar = [cookie.name for cookie in cookiejar]
        for name in cookie_dict:
            if overwrite or (name not in names_from_jar):
                cookiejar.set_cookie(create_cookie(name, cookie_dict[name]))

    return cookiejar


def merge_cookies(cookiejar, cookies):
    """Add cookies to cookiejar and returns a merged CookieJar.

    :param cookiejar: CookieJar object to add the cookies to.
    :param cookies: Dictionary or CookieJar object to be added.
    :rtype: CookieJar
    """
    if not isinstance(cookiejar, cookielib.CookieJar):
        raise ValueError("You can only merge into CookieJar")

    if isinstance(cookies, dict):
        cookiejar = cookiejar_from_dict(cookies, cookiejar=cookiejar, overwrite=False)
    elif isinstance(cookies, cookielib.CookieJar):
        try:
            cookiejar.update(cookies)
        except AttributeError:
            for cookie_in_jar in cookies:
                cookiejar.set_cookie(cookie_in_jar)

    return cookiejar

# === NexusCore/openenv\Lib\site-packages\requests\cookies.py ===
"""
requests.cookies
~~~~~~~~~~~~~~~~

Compatibility code to be able to use `http.cookiejar.CookieJar` with requests.

requests.utils imports from here, so be careful with imports.
"""

import calendar
import copy
import time

from ._internal_utils import to_native_string
from .compat import Morsel, MutableMapping, cookielib, urlparse, urlunparse

try:
    import threading
except ImportError:
    import dummy_threading as threading


class MockRequest:
    """Wraps a `requests.Request` to mimic a `urllib2.Request`.

    The code in `http.cookiejar.CookieJar` expects this interface in order to correctly
    manage cookie policies, i.e., determine whether a cookie can be set, given the
    domains of the request and the cookie.

    The original request object is read-only. The client is responsible for collecting
    the new headers via `get_new_headers()` and interpreting them appropriately. You
    probably want `get_cookie_header`, defined below.
    """

    def __init__(self, request):
        self._r = request
        self._new_headers = {}
        self.type = urlparse(self._r.url).scheme

    def get_type(self):
        return self.type

    def get_host(self):
        return urlparse(self._r.url).netloc

    def get_origin_req_host(self):
        return self.get_host()

    def get_full_url(self):
        # Only return the response's URL if the user hadn't set the Host
        # header
        if not self._r.headers.get("Host"):
            return self._r.url
        # If they did set it, retrieve it and reconstruct the expected domain
        host = to_native_string(self._r.headers["Host"], encoding="utf-8")
        parsed = urlparse(self._r.url)
        # Reconstruct the URL as we expect it
        return urlunparse(
            [
                parsed.scheme,
                host,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ]
        )

    def is_unverifiable(self):
        return True

    def has_header(self, name):
        return name in self._r.headers or name in self._new_headers

    def get_header(self, name, default=None):
        return self._r.headers.get(name, self._new_headers.get(name, default))

    def add_header(self, key, val):
        """cookiejar has no legitimate use for this method; add it back if you find one."""
        raise NotImplementedError(
            "Cookie headers should be added with add_unredirected_header()"
        )

    def add_unredirected_header(self, name, value):
        self._new_headers[name] = value

    def get_new_headers(self):
        return self._new_headers

    @property
    def unverifiable(self):
        return self.is_unverifiable()

    @property
    def origin_req_host(self):
        return self.get_origin_req_host()

    @property
    def host(self):
        return self.get_host()


class MockResponse:
    """Wraps a `httplib.HTTPMessage` to mimic a `urllib.addinfourl`.

    ...what? Basically, expose the parsed HTTP headers from the server response
    the way `http.cookiejar` expects to see them.
    """

    def __init__(self, headers):
        """Make a MockResponse for `cookiejar` to read.

        :param headers: a httplib.HTTPMessage or analogous carrying the headers
        """
        self._headers = headers

    def info(self):
        return self._headers

    def getheaders(self, name):
        self._headers.getheaders(name)


def extract_cookies_to_jar(jar, request, response):
    """Extract the cookies from the response into a CookieJar.

    :param jar: http.cookiejar.CookieJar (not necessarily a RequestsCookieJar)
    :param request: our own requests.Request object
    :param response: urllib3.HTTPResponse object
    """
    if not (hasattr(response, "_original_response") and response._original_response):
        return
    # the _original_response field is the wrapped httplib.HTTPResponse object,
    req = MockRequest(request)
    # pull out the HTTPMessage with the headers and put it in the mock:
    res = MockResponse(response._original_response.msg)
    jar.extract_cookies(res, req)


def get_cookie_header(jar, request):
    """
    Produce an appropriate Cookie header string to be sent with `request`, or None.

    :rtype: str
    """
    r = MockRequest(request)
    jar.add_cookie_header(r)
    return r.get_new_headers().get("Cookie")


def remove_cookie_by_name(cookiejar, name, domain=None, path=None):
    """Unsets a cookie by name, by default over all domains and paths.

    Wraps CookieJar.clear(), is O(n).
    """
    clearables = []
    for cookie in cookiejar:
        if cookie.name != name:
            continue
        if domain is not None and domain != cookie.domain:
            continue
        if path is not None and path != cookie.path:
            continue
        clearables.append((cookie.domain, cookie.path, cookie.name))

    for domain, path, name in clearables:
        cookiejar.clear(domain, path, name)


class CookieConflictError(RuntimeError):
    """There are two cookies that meet the criteria specified in the cookie jar.
    Use .get and .set and include domain and path args in order to be more specific.
    """


class RequestsCookieJar(cookielib.CookieJar, MutableMapping):
    """Compatibility class; is a http.cookiejar.CookieJar, but exposes a dict
    interface.

    This is the CookieJar we create by default for requests and sessions that
    don't specify one, since some clients may expect response.cookies and
    session.cookies to support dict operations.

    Requests does not use the dict interface internally; it's just for
    compatibility with external client code. All requests code should work
    out of the box with externally provided instances of ``CookieJar``, e.g.
    ``LWPCookieJar`` and ``FileCookieJar``.

    Unlike a regular CookieJar, this class is pickleable.

    .. warning:: dictionary operations that are normally O(1) may be O(n).
    """

    def get(self, name, default=None, domain=None, path=None):
        """Dict-like get() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.

        .. warning:: operation is O(n), not O(1).
        """
        try:
            return self._find_no_duplicates(name, domain, path)
        except KeyError:
            return default

    def set(self, name, value, **kwargs):
        """Dict-like set() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.
        """
        # support client code that unsets cookies by assignment of a None value:
        if value is None:
            remove_cookie_by_name(
                self, name, domain=kwargs.get("domain"), path=kwargs.get("path")
            )
            return

        if isinstance(value, Morsel):
            c = morsel_to_cookie(value)
        else:
            c = create_cookie(name, value, **kwargs)
        self.set_cookie(c)
        return c

    def iterkeys(self):
        """Dict-like iterkeys() that returns an iterator of names of cookies
        from the jar.

        .. seealso:: itervalues() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.name

    def keys(self):
        """Dict-like keys() that returns a list of names of cookies from the
        jar.

        .. seealso:: values() and items().
        """
        return list(self.iterkeys())

    def itervalues(self):
        """Dict-like itervalues() that returns an iterator of values of cookies
        from the jar.

        .. seealso:: iterkeys() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.value

    def values(self):
        """Dict-like values() that returns a list of values of cookies from the
        jar.

        .. seealso:: keys() and items().
        """
        return list(self.itervalues())

    def iteritems(self):
        """Dict-like iteritems() that returns an iterator of name-value tuples
        from the jar.

        .. seealso:: iterkeys() and itervalues().
        """
        for cookie in iter(self):
            yield cookie.name, cookie.value

    def items(self):
        """Dict-like items() that returns a list of name-value tuples from the
        jar. Allows client-code to call ``dict(RequestsCookieJar)`` and get a
        vanilla python dict of key value pairs.

        .. seealso:: keys() and values().
        """
        return list(self.iteritems())

    def list_domains(self):
        """Utility method to list all the domains in the jar."""
        domains = []
        for cookie in iter(self):
            if cookie.domain not in domains:
                domains.append(cookie.domain)
        return domains

    def list_paths(self):
        """Utility method to list all the paths in the jar."""
        paths = []
        for cookie in iter(self):
            if cookie.path not in paths:
                paths.append(cookie.path)
        return paths

    def multiple_domains(self):
        """Returns True if there are multiple domains in the jar.
        Returns False otherwise.

        :rtype: bool
        """
        domains = []
        for cookie in iter(self):
            if cookie.domain is not None and cookie.domain in domains:
                return True
            domains.append(cookie.domain)
        return False  # there is only one domain in jar

    def get_dict(self, domain=None, path=None):
        """Takes as an argument an optional domain and path and returns a plain
        old Python dict of name-value pairs of cookies that meet the
        requirements.

        :rtype: dict
        """
        dictionary = {}
        for cookie in iter(self):
            if (domain is None or cookie.domain == domain) and (
                path is None or cookie.path == path
            ):
                dictionary[cookie.name] = cookie.value
        return dictionary

    def __contains__(self, name):
        try:
            return super().__contains__(name)
        except CookieConflictError:
            return True

    def __getitem__(self, name):
        """Dict-like __getitem__() for compatibility with client code. Throws
        exception if there are more than one cookie with name. In that case,
        use the more explicit get() method instead.

        .. warning:: operation is O(n), not O(1).
        """
        return self._find_no_duplicates(name)

    def __setitem__(self, name, value):
        """Dict-like __setitem__ for compatibility with client code. Throws
        exception if there is already a cookie of that name in the jar. In that
        case, use the more explicit set() method instead.
        """
        self.set(name, value)

    def __delitem__(self, name):
        """Deletes a cookie given a name. Wraps ``http.cookiejar.CookieJar``'s
        ``remove_cookie_by_name()``.
        """
        remove_cookie_by_name(self, name)

    def set_cookie(self, cookie, *args, **kwargs):
        if (
            hasattr(cookie.value, "startswith")
            and cookie.value.startswith('"')
            and cookie.value.endswith('"')
        ):
            cookie.value = cookie.value.replace('\\"', "")
        return super().set_cookie(cookie, *args, **kwargs)

    def update(self, other):
        """Updates this jar with cookies from another CookieJar or dict-like"""
        if isinstance(other, cookielib.CookieJar):
            for cookie in other:
                self.set_cookie(copy.copy(cookie))
        else:
            super().update(other)

    def _find(self, name, domain=None, path=None):
        """Requests uses this method internally to get cookie values.

        If there are conflicting cookies, _find arbitrarily chooses one.
        See _find_no_duplicates if you want an exception thrown if there are
        conflicting cookies.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :return: cookie.value
        """
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        return cookie.value

        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def _find_no_duplicates(self, name, domain=None, path=None):
        """Both ``__get_item__`` and ``get`` call this function: it's never
        used elsewhere in Requests.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :raises KeyError: if cookie is not found
        :raises CookieConflictError: if there are multiple cookies
            that match name and optionally domain and path
        :return: cookie.value
        """
        toReturn = None
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        if toReturn is not None:
                            # if there are multiple cookies that meet passed in criteria
                            raise CookieConflictError(
                                f"There are multiple cookies with name, {name!r}"
                            )
                        # we will eventually return this as long as no cookie conflict
                        toReturn = cookie.value

        if toReturn:
            return toReturn
        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def __getstate__(self):
        """Unlike a normal CookieJar, this class is pickleable."""
        state = self.__dict__.copy()
        # remove the unpickleable RLock object
        state.pop("_cookies_lock")
        return state

    def __setstate__(self, state):
        """Unlike a normal CookieJar, this class is pickleable."""
        self.__dict__.update(state)
        if "_cookies_lock" not in self.__dict__:
            self._cookies_lock = threading.RLock()

    def copy(self):
        """Return a copy of this RequestsCookieJar."""
        new_cj = RequestsCookieJar()
        new_cj.set_policy(self.get_policy())
        new_cj.update(self)
        return new_cj

    def get_policy(self):
        """Return the CookiePolicy instance used."""
        return self._policy


def _copy_cookie_jar(jar):
    if jar is None:
        return None

    if hasattr(jar, "copy"):
        # We're dealing with an instance of RequestsCookieJar
        return jar.copy()
    # We're dealing with a generic CookieJar instance
    new_jar = copy.copy(jar)
    new_jar.clear()
    for cookie in jar:
        new_jar.set_cookie(copy.copy(cookie))
    return new_jar


def create_cookie(name, value, **kwargs):
    """Make a cookie from underspecified parameters.

    By default, the pair of `name` and `value` will be set for the domain ''
    and sent on every request (this is sometimes called a "supercookie").
    """
    result = {
        "version": 0,
        "name": name,
        "value": value,
        "port": None,
        "domain": "",
        "path": "/",
        "secure": False,
        "expires": None,
        "discard": True,
        "comment": None,
        "comment_url": None,
        "rest": {"HttpOnly": None},
        "rfc2109": False,
    }

    badargs = set(kwargs) - set(result)
    if badargs:
        raise TypeError(
            f"create_cookie() got unexpected keyword arguments: {list(badargs)}"
        )

    result.update(kwargs)
    result["port_specified"] = bool(result["port"])
    result["domain_specified"] = bool(result["domain"])
    result["domain_initial_dot"] = result["domain"].startswith(".")
    result["path_specified"] = bool(result["path"])

    return cookielib.Cookie(**result)


def morsel_to_cookie(morsel):
    """Convert a Morsel object into a Cookie containing the one k/v pair."""

    expires = None
    if morsel["max-age"]:
        try:
            expires = int(time.time() + int(morsel["max-age"]))
        except ValueError:
            raise TypeError(f"max-age: {morsel['max-age']} must be integer")
    elif morsel["expires"]:
        time_template = "%a, %d-%b-%Y %H:%M:%S GMT"
        expires = calendar.timegm(time.strptime(morsel["expires"], time_template))
    return create_cookie(
        comment=morsel["comment"],
        comment_url=bool(morsel["comment"]),
        discard=False,
        domain=morsel["domain"],
        expires=expires,
        name=morsel.key,
        path=morsel["path"],
        port=None,
        rest={"HttpOnly": morsel["httponly"]},
        rfc2109=False,
        secure=bool(morsel["secure"]),
        value=morsel.value,
        version=morsel["version"] or 0,
    )


def cookiejar_from_dict(cookie_dict, cookiejar=None, overwrite=True):
    """Returns a CookieJar from a key/value dictionary.

    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :param cookiejar: (optional) A cookiejar to add the cookies to.
    :param overwrite: (optional) If False, will not replace cookies
        already in the jar with new ones.
    :rtype: CookieJar
    """
    if cookiejar is None:
        cookiejar = RequestsCookieJar()

    if cookie_dict is not None:
        names_from_jar = [cookie.name for cookie in cookiejar]
        for name in cookie_dict:
            if overwrite or (name not in names_from_jar):
                cookiejar.set_cookie(create_cookie(name, cookie_dict[name]))

    return cookiejar


def merge_cookies(cookiejar, cookies):
    """Add cookies to cookiejar and returns a merged CookieJar.

    :param cookiejar: CookieJar object to add the cookies to.
    :param cookies: Dictionary or CookieJar object to be added.
    :rtype: CookieJar
    """
    if not isinstance(cookiejar, cookielib.CookieJar):
        raise ValueError("You can only merge into CookieJar")

    if isinstance(cookies, dict):
        cookiejar = cookiejar_from_dict(cookies, cookiejar=cookiejar, overwrite=False)
    elif isinstance(cookies, cookielib.CookieJar):
        try:
            cookiejar.update(cookies)
        except AttributeError:
            for cookie_in_jar in cookies:
                cookiejar.set_cookie(cookie_in_jar)

    return cookiejar

# === NexusCore/openenv\Lib\site-packages\nltk\inference\nonmonotonic.py ===
# Natural Language Toolkit: Nonmonotonic Reasoning
#
# Author: Daniel H. Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module to perform nonmonotonic reasoning.  The ideas and demonstrations in
this module are based on "Logical Foundations of Artificial Intelligence" by
Michael R. Genesereth and Nils J. Nilsson.
"""

from collections import defaultdict
from functools import reduce

from nltk.inference.api import Prover, ProverCommandDecorator
from nltk.inference.prover9 import Prover9, Prover9Command
from nltk.sem.logic import (
    AbstractVariableExpression,
    AllExpression,
    AndExpression,
    ApplicationExpression,
    BooleanExpression,
    EqualityExpression,
    ExistsExpression,
    Expression,
    ImpExpression,
    NegatedExpression,
    Variable,
    VariableExpression,
    operator,
    unique_variable,
)


class ProverParseError(Exception):
    pass


def get_domain(goal, assumptions):
    if goal is None:
        all_expressions = assumptions
    else:
        all_expressions = assumptions + [-goal]
    return reduce(operator.or_, (a.constants() for a in all_expressions), set())


class ClosedDomainProver(ProverCommandDecorator):
    """
    This is a prover decorator that adds domain closure assumptions before
    proving.
    """

    def assumptions(self):
        assumptions = [a for a in self._command.assumptions()]
        goal = self._command.goal()
        domain = get_domain(goal, assumptions)
        return [self.replace_quants(ex, domain) for ex in assumptions]

    def goal(self):
        goal = self._command.goal()
        domain = get_domain(goal, self._command.assumptions())
        return self.replace_quants(goal, domain)

    def replace_quants(self, ex, domain):
        """
        Apply the closed domain assumption to the expression

        - Domain = union([e.free()|e.constants() for e in all_expressions])
        - translate "exists x.P" to "(z=d1 | z=d2 | ... ) & P.replace(x,z)" OR
                    "P.replace(x, d1) | P.replace(x, d2) | ..."
        - translate "all x.P" to "P.replace(x, d1) & P.replace(x, d2) & ..."

        :param ex: ``Expression``
        :param domain: set of {Variable}s
        :return: ``Expression``
        """
        if isinstance(ex, AllExpression):
            conjuncts = [
                ex.term.replace(ex.variable, VariableExpression(d)) for d in domain
            ]
            conjuncts = [self.replace_quants(c, domain) for c in conjuncts]
            return reduce(lambda x, y: x & y, conjuncts)
        elif isinstance(ex, BooleanExpression):
            return ex.__class__(
                self.replace_quants(ex.first, domain),
                self.replace_quants(ex.second, domain),
            )
        elif isinstance(ex, NegatedExpression):
            return -self.replace_quants(ex.term, domain)
        elif isinstance(ex, ExistsExpression):
            disjuncts = [
                ex.term.replace(ex.variable, VariableExpression(d)) for d in domain
            ]
            disjuncts = [self.replace_quants(d, domain) for d in disjuncts]
            return reduce(lambda x, y: x | y, disjuncts)
        else:
            return ex


class UniqueNamesProver(ProverCommandDecorator):
    """
    This is a prover decorator that adds unique names assumptions before
    proving.
    """

    def assumptions(self):
        """
        - Domain = union([e.free()|e.constants() for e in all_expressions])
        - if "d1 = d2" cannot be proven from the premises, then add "d1 != d2"
        """
        assumptions = self._command.assumptions()

        domain = list(get_domain(self._command.goal(), assumptions))

        # build a dictionary of obvious equalities
        eq_sets = SetHolder()
        for a in assumptions:
            if isinstance(a, EqualityExpression):
                av = a.first.variable
                bv = a.second.variable
                # put 'a' and 'b' in the same set
                eq_sets[av].add(bv)

        new_assumptions = []
        for i, a in enumerate(domain):
            for b in domain[i + 1 :]:
                # if a and b are not already in the same equality set
                if b not in eq_sets[a]:
                    newEqEx = EqualityExpression(
                        VariableExpression(a), VariableExpression(b)
                    )
                    if Prover9().prove(newEqEx, assumptions):
                        # we can prove that the names are the same entity.
                        # remember that they are equal so we don't re-check.
                        eq_sets[a].add(b)
                    else:
                        # we can't prove it, so assume unique names
                        new_assumptions.append(-newEqEx)

        return assumptions + new_assumptions


class SetHolder(list):
    """
    A list of sets of Variables.
    """

    def __getitem__(self, item):
        """
        :param item: ``Variable``
        :return: the set containing 'item'
        """
        assert isinstance(item, Variable)
        for s in self:
            if item in s:
                return s
        # item is not found in any existing set.  so create a new set
        new = {item}
        self.append(new)
        return new


class ClosedWorldProver(ProverCommandDecorator):
    """
    This is a prover decorator that completes predicates before proving.

    If the assumptions contain "P(A)", then "all x.(P(x) -> (x=A))" is the completion of "P".
    If the assumptions contain "all x.(ostrich(x) -> bird(x))", then "all x.(bird(x) -> ostrich(x))" is the completion of "bird".
    If the assumptions don't contain anything that are "P", then "all x.-P(x)" is the completion of "P".

    walk(Socrates)
    Socrates != Bill
    + all x.(walk(x) -> (x=Socrates))
    ----------------
    -walk(Bill)

    see(Socrates, John)
    see(John, Mary)
    Socrates != John
    John != Mary
    + all x.all y.(see(x,y) -> ((x=Socrates & y=John) | (x=John & y=Mary)))
    ----------------
    -see(Socrates, Mary)

    all x.(ostrich(x) -> bird(x))
    bird(Tweety)
    -ostrich(Sam)
    Sam != Tweety
    + all x.(bird(x) -> (ostrich(x) | x=Tweety))
    + all x.-ostrich(x)
    -------------------
    -bird(Sam)
    """

    def assumptions(self):
        assumptions = self._command.assumptions()

        predicates = self._make_predicate_dict(assumptions)

        new_assumptions = []
        for p in predicates:
            predHolder = predicates[p]
            new_sig = self._make_unique_signature(predHolder)
            new_sig_exs = [VariableExpression(v) for v in new_sig]

            disjuncts = []

            # Turn the signatures into disjuncts
            for sig in predHolder.signatures:
                equality_exs = []
                for v1, v2 in zip(new_sig_exs, sig):
                    equality_exs.append(EqualityExpression(v1, v2))
                disjuncts.append(reduce(lambda x, y: x & y, equality_exs))

            # Turn the properties into disjuncts
            for prop in predHolder.properties:
                # replace variables from the signature with new sig variables
                bindings = {}
                for v1, v2 in zip(new_sig_exs, prop[0]):
                    bindings[v2] = v1
                disjuncts.append(prop[1].substitute_bindings(bindings))

            # make the assumption
            if disjuncts:
                # disjuncts exist, so make an implication
                antecedent = self._make_antecedent(p, new_sig)
                consequent = reduce(lambda x, y: x | y, disjuncts)
                accum = ImpExpression(antecedent, consequent)
            else:
                # nothing has property 'p'
                accum = NegatedExpression(self._make_antecedent(p, new_sig))

            # quantify the implication
            for new_sig_var in new_sig[::-1]:
                accum = AllExpression(new_sig_var, accum)
            new_assumptions.append(accum)

        return assumptions + new_assumptions

    def _make_unique_signature(self, predHolder):
        """
        This method figures out how many arguments the predicate takes and
        returns a tuple containing that number of unique variables.
        """
        return tuple(unique_variable() for i in range(predHolder.signature_len))

    def _make_antecedent(self, predicate, signature):
        """
        Return an application expression with 'predicate' as the predicate
        and 'signature' as the list of arguments.
        """
        antecedent = predicate
        for v in signature:
            antecedent = antecedent(VariableExpression(v))
        return antecedent

    def _make_predicate_dict(self, assumptions):
        """
        Create a dictionary of predicates from the assumptions.

        :param assumptions: a list of ``Expression``s
        :return: dict mapping ``AbstractVariableExpression`` to ``PredHolder``
        """
        predicates = defaultdict(PredHolder)
        for a in assumptions:
            self._map_predicates(a, predicates)
        return predicates

    def _map_predicates(self, expression, predDict):
        if isinstance(expression, ApplicationExpression):
            func, args = expression.uncurry()
            if isinstance(func, AbstractVariableExpression):
                predDict[func].append_sig(tuple(args))
        elif isinstance(expression, AndExpression):
            self._map_predicates(expression.first, predDict)
            self._map_predicates(expression.second, predDict)
        elif isinstance(expression, AllExpression):
            # collect all the universally quantified variables
            sig = [expression.variable]
            term = expression.term
            while isinstance(term, AllExpression):
                sig.append(term.variable)
                term = term.term
            if isinstance(term, ImpExpression):
                if isinstance(term.first, ApplicationExpression) and isinstance(
                    term.second, ApplicationExpression
                ):
                    func1, args1 = term.first.uncurry()
                    func2, args2 = term.second.uncurry()
                    if (
                        isinstance(func1, AbstractVariableExpression)
                        and isinstance(func2, AbstractVariableExpression)
                        and sig == [v.variable for v in args1]
                        and sig == [v.variable for v in args2]
                    ):
                        predDict[func2].append_prop((tuple(sig), term.first))
                        predDict[func1].validate_sig_len(sig)


class PredHolder:
    """
    This class will be used by a dictionary that will store information
    about predicates to be used by the ``ClosedWorldProver``.

    The 'signatures' property is a list of tuples defining signatures for
    which the predicate is true.  For instance, 'see(john, mary)' would be
    result in the signature '(john,mary)' for 'see'.

    The second element of the pair is a list of pairs such that the first
    element of the pair is a tuple of variables and the second element is an
    expression of those variables that makes the predicate true.  For instance,
    'all x.all y.(see(x,y) -> know(x,y))' would result in "((x,y),('see(x,y)'))"
    for 'know'.
    """

    def __init__(self):
        self.signatures = []
        self.properties = []
        self.signature_len = None

    def append_sig(self, new_sig):
        self.validate_sig_len(new_sig)
        self.signatures.append(new_sig)

    def append_prop(self, new_prop):
        self.validate_sig_len(new_prop[0])
        self.properties.append(new_prop)

    def validate_sig_len(self, new_sig):
        if self.signature_len is None:
            self.signature_len = len(new_sig)
        elif self.signature_len != len(new_sig):
            raise Exception("Signature lengths do not match")

    def __str__(self):
        return f"({self.signatures},{self.properties},{self.signature_len})"

    def __repr__(self):
        return "%s" % self


def closed_domain_demo():
    lexpr = Expression.fromstring

    p1 = lexpr(r"exists x.walk(x)")
    p2 = lexpr(r"man(Socrates)")
    c = lexpr(r"walk(Socrates)")
    prover = Prover9Command(c, [p1, p2])
    print(prover.prove())
    cdp = ClosedDomainProver(prover)
    print("assumptions:")
    for a in cdp.assumptions():
        print("   ", a)
    print("goal:", cdp.goal())
    print(cdp.prove())

    p1 = lexpr(r"exists x.walk(x)")
    p2 = lexpr(r"man(Socrates)")
    p3 = lexpr(r"-walk(Bill)")
    c = lexpr(r"walk(Socrates)")
    prover = Prover9Command(c, [p1, p2, p3])
    print(prover.prove())
    cdp = ClosedDomainProver(prover)
    print("assumptions:")
    for a in cdp.assumptions():
        print("   ", a)
    print("goal:", cdp.goal())
    print(cdp.prove())

    p1 = lexpr(r"exists x.walk(x)")
    p2 = lexpr(r"man(Socrates)")
    p3 = lexpr(r"-walk(Bill)")
    c = lexpr(r"walk(Socrates)")
    prover = Prover9Command(c, [p1, p2, p3])
    print(prover.prove())
    cdp = ClosedDomainProver(prover)
    print("assumptions:")
    for a in cdp.assumptions():
        print("   ", a)
    print("goal:", cdp.goal())
    print(cdp.prove())

    p1 = lexpr(r"walk(Socrates)")
    p2 = lexpr(r"walk(Bill)")
    c = lexpr(r"all x.walk(x)")
    prover = Prover9Command(c, [p1, p2])
    print(prover.prove())
    cdp = ClosedDomainProver(prover)
    print("assumptions:")
    for a in cdp.assumptions():
        print("   ", a)
    print("goal:", cdp.goal())
    print(cdp.prove())

    p1 = lexpr(r"girl(mary)")
    p2 = lexpr(r"dog(rover)")
    p3 = lexpr(r"all x.(girl(x) -> -dog(x))")
    p4 = lexpr(r"all x.(dog(x) -> -girl(x))")
    p5 = lexpr(r"chase(mary, rover)")
    c = lexpr(r"exists y.(dog(y) & all x.(girl(x) -> chase(x,y)))")
    prover = Prover9Command(c, [p1, p2, p3, p4, p5])
    print(prover.prove())
    cdp = ClosedDomainProver(prover)
    print("assumptions:")
    for a in cdp.assumptions():
        print("   ", a)
    print("goal:", cdp.goal())
    print(cdp.prove())


def unique_names_demo():
    lexpr = Expression.fromstring

    p1 = lexpr(r"man(Socrates)")
    p2 = lexpr(r"man(Bill)")
    c = lexpr(r"exists x.exists y.(x != y)")
    prover = Prover9Command(c, [p1, p2])
    print(prover.prove())
    unp = UniqueNamesProver(prover)
    print("assumptions:")
    for a in unp.assumptions():
        print("   ", a)
    print("goal:", unp.goal())
    print(unp.prove())

    p1 = lexpr(r"all x.(walk(x) -> (x = Socrates))")
    p2 = lexpr(r"Bill = William")
    p3 = lexpr(r"Bill = Billy")
    c = lexpr(r"-walk(William)")
    prover = Prover9Command(c, [p1, p2, p3])
    print(prover.prove())
    unp = UniqueNamesProver(prover)
    print("assumptions:")
    for a in unp.assumptions():
        print("   ", a)
    print("goal:", unp.goal())
    print(unp.prove())


def closed_world_demo():
    lexpr = Expression.fromstring

    p1 = lexpr(r"walk(Socrates)")
    p2 = lexpr(r"(Socrates != Bill)")
    c = lexpr(r"-walk(Bill)")
    prover = Prover9Command(c, [p1, p2])
    print(prover.prove())
    cwp = ClosedWorldProver(prover)
    print("assumptions:")
    for a in cwp.assumptions():
        print("   ", a)
    print("goal:", cwp.goal())
    print(cwp.prove())

    p1 = lexpr(r"see(Socrates, John)")
    p2 = lexpr(r"see(John, Mary)")
    p3 = lexpr(r"(Socrates != John)")
    p4 = lexpr(r"(John != Mary)")
    c = lexpr(r"-see(Socrates, Mary)")
    prover = Prover9Command(c, [p1, p2, p3, p4])
    print(prover.prove())
    cwp = ClosedWorldProver(prover)
    print("assumptions:")
    for a in cwp.assumptions():
        print("   ", a)
    print("goal:", cwp.goal())
    print(cwp.prove())

    p1 = lexpr(r"all x.(ostrich(x) -> bird(x))")
    p2 = lexpr(r"bird(Tweety)")
    p3 = lexpr(r"-ostrich(Sam)")
    p4 = lexpr(r"Sam != Tweety")
    c = lexpr(r"-bird(Sam)")
    prover = Prover9Command(c, [p1, p2, p3, p4])
    print(prover.prove())
    cwp = ClosedWorldProver(prover)
    print("assumptions:")
    for a in cwp.assumptions():
        print("   ", a)
    print("goal:", cwp.goal())
    print(cwp.prove())


def combination_prover_demo():
    lexpr = Expression.fromstring

    p1 = lexpr(r"see(Socrates, John)")
    p2 = lexpr(r"see(John, Mary)")
    c = lexpr(r"-see(Socrates, Mary)")
    prover = Prover9Command(c, [p1, p2])
    print(prover.prove())
    command = ClosedDomainProver(UniqueNamesProver(ClosedWorldProver(prover)))
    for a in command.assumptions():
        print(a)
    print(command.prove())


def default_reasoning_demo():
    lexpr = Expression.fromstring

    premises = []

    # define taxonomy
    premises.append(lexpr(r"all x.(elephant(x)        -> animal(x))"))
    premises.append(lexpr(r"all x.(bird(x)            -> animal(x))"))
    premises.append(lexpr(r"all x.(dove(x)            -> bird(x))"))
    premises.append(lexpr(r"all x.(ostrich(x)         -> bird(x))"))
    premises.append(lexpr(r"all x.(flying_ostrich(x)  -> ostrich(x))"))

    # default properties
    premises.append(
        lexpr(r"all x.((animal(x)  & -Ab1(x)) -> -fly(x))")
    )  # normal animals don't fly
    premises.append(
        lexpr(r"all x.((bird(x)    & -Ab2(x)) -> fly(x))")
    )  # normal birds fly
    premises.append(
        lexpr(r"all x.((ostrich(x) & -Ab3(x)) -> -fly(x))")
    )  # normal ostriches don't fly

    # specify abnormal entities
    premises.append(lexpr(r"all x.(bird(x)           -> Ab1(x))"))  # flight
    premises.append(lexpr(r"all x.(ostrich(x)        -> Ab2(x))"))  # non-flying bird
    premises.append(lexpr(r"all x.(flying_ostrich(x) -> Ab3(x))"))  # flying ostrich

    # define entities
    premises.append(lexpr(r"elephant(E)"))
    premises.append(lexpr(r"dove(D)"))
    premises.append(lexpr(r"ostrich(O)"))

    # print the assumptions
    prover = Prover9Command(None, premises)
    command = UniqueNamesProver(ClosedWorldProver(prover))
    for a in command.assumptions():
        print(a)

    print_proof("-fly(E)", premises)
    print_proof("fly(D)", premises)
    print_proof("-fly(O)", premises)


def print_proof(goal, premises):
    lexpr = Expression.fromstring
    prover = Prover9Command(lexpr(goal), premises)
    command = UniqueNamesProver(ClosedWorldProver(prover))
    print(goal, prover.prove(), command.prove())


def demo():
    closed_domain_demo()
    unique_names_demo()
    closed_world_demo()
    combination_prover_demo()
    default_reasoning_demo()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\cookies.py ===
"""
requests.cookies
~~~~~~~~~~~~~~~~

Compatibility code to be able to use `http.cookiejar.CookieJar` with requests.

requests.utils imports from here, so be careful with imports.
"""

import calendar
import copy
import time

from ._internal_utils import to_native_string
from .compat import Morsel, MutableMapping, cookielib, urlparse, urlunparse

try:
    import threading
except ImportError:
    import dummy_threading as threading


class MockRequest:
    """Wraps a `requests.Request` to mimic a `urllib2.Request`.

    The code in `http.cookiejar.CookieJar` expects this interface in order to correctly
    manage cookie policies, i.e., determine whether a cookie can be set, given the
    domains of the request and the cookie.

    The original request object is read-only. The client is responsible for collecting
    the new headers via `get_new_headers()` and interpreting them appropriately. You
    probably want `get_cookie_header`, defined below.
    """

    def __init__(self, request):
        self._r = request
        self._new_headers = {}
        self.type = urlparse(self._r.url).scheme

    def get_type(self):
        return self.type

    def get_host(self):
        return urlparse(self._r.url).netloc

    def get_origin_req_host(self):
        return self.get_host()

    def get_full_url(self):
        # Only return the response's URL if the user hadn't set the Host
        # header
        if not self._r.headers.get("Host"):
            return self._r.url
        # If they did set it, retrieve it and reconstruct the expected domain
        host = to_native_string(self._r.headers["Host"], encoding="utf-8")
        parsed = urlparse(self._r.url)
        # Reconstruct the URL as we expect it
        return urlunparse(
            [
                parsed.scheme,
                host,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            ]
        )

    def is_unverifiable(self):
        return True

    def has_header(self, name):
        return name in self._r.headers or name in self._new_headers

    def get_header(self, name, default=None):
        return self._r.headers.get(name, self._new_headers.get(name, default))

    def add_header(self, key, val):
        """cookiejar has no legitimate use for this method; add it back if you find one."""
        raise NotImplementedError(
            "Cookie headers should be added with add_unredirected_header()"
        )

    def add_unredirected_header(self, name, value):
        self._new_headers[name] = value

    def get_new_headers(self):
        return self._new_headers

    @property
    def unverifiable(self):
        return self.is_unverifiable()

    @property
    def origin_req_host(self):
        return self.get_origin_req_host()

    @property
    def host(self):
        return self.get_host()


class MockResponse:
    """Wraps a `httplib.HTTPMessage` to mimic a `urllib.addinfourl`.

    ...what? Basically, expose the parsed HTTP headers from the server response
    the way `http.cookiejar` expects to see them.
    """

    def __init__(self, headers):
        """Make a MockResponse for `cookiejar` to read.

        :param headers: a httplib.HTTPMessage or analogous carrying the headers
        """
        self._headers = headers

    def info(self):
        return self._headers

    def getheaders(self, name):
        self._headers.getheaders(name)


def extract_cookies_to_jar(jar, request, response):
    """Extract the cookies from the response into a CookieJar.

    :param jar: http.cookiejar.CookieJar (not necessarily a RequestsCookieJar)
    :param request: our own requests.Request object
    :param response: urllib3.HTTPResponse object
    """
    if not (hasattr(response, "_original_response") and response._original_response):
        return
    # the _original_response field is the wrapped httplib.HTTPResponse object,
    req = MockRequest(request)
    # pull out the HTTPMessage with the headers and put it in the mock:
    res = MockResponse(response._original_response.msg)
    jar.extract_cookies(res, req)


def get_cookie_header(jar, request):
    """
    Produce an appropriate Cookie header string to be sent with `request`, or None.

    :rtype: str
    """
    r = MockRequest(request)
    jar.add_cookie_header(r)
    return r.get_new_headers().get("Cookie")


def remove_cookie_by_name(cookiejar, name, domain=None, path=None):
    """Unsets a cookie by name, by default over all domains and paths.

    Wraps CookieJar.clear(), is O(n).
    """
    clearables = []
    for cookie in cookiejar:
        if cookie.name != name:
            continue
        if domain is not None and domain != cookie.domain:
            continue
        if path is not None and path != cookie.path:
            continue
        clearables.append((cookie.domain, cookie.path, cookie.name))

    for domain, path, name in clearables:
        cookiejar.clear(domain, path, name)


class CookieConflictError(RuntimeError):
    """There are two cookies that meet the criteria specified in the cookie jar.
    Use .get and .set and include domain and path args in order to be more specific.
    """


class RequestsCookieJar(cookielib.CookieJar, MutableMapping):
    """Compatibility class; is a http.cookiejar.CookieJar, but exposes a dict
    interface.

    This is the CookieJar we create by default for requests and sessions that
    don't specify one, since some clients may expect response.cookies and
    session.cookies to support dict operations.

    Requests does not use the dict interface internally; it's just for
    compatibility with external client code. All requests code should work
    out of the box with externally provided instances of ``CookieJar``, e.g.
    ``LWPCookieJar`` and ``FileCookieJar``.

    Unlike a regular CookieJar, this class is pickleable.

    .. warning:: dictionary operations that are normally O(1) may be O(n).
    """

    def get(self, name, default=None, domain=None, path=None):
        """Dict-like get() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.

        .. warning:: operation is O(n), not O(1).
        """
        try:
            return self._find_no_duplicates(name, domain, path)
        except KeyError:
            return default

    def set(self, name, value, **kwargs):
        """Dict-like set() that also supports optional domain and path args in
        order to resolve naming collisions from using one cookie jar over
        multiple domains.
        """
        # support client code that unsets cookies by assignment of a None value:
        if value is None:
            remove_cookie_by_name(
                self, name, domain=kwargs.get("domain"), path=kwargs.get("path")
            )
            return

        if isinstance(value, Morsel):
            c = morsel_to_cookie(value)
        else:
            c = create_cookie(name, value, **kwargs)
        self.set_cookie(c)
        return c

    def iterkeys(self):
        """Dict-like iterkeys() that returns an iterator of names of cookies
        from the jar.

        .. seealso:: itervalues() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.name

    def keys(self):
        """Dict-like keys() that returns a list of names of cookies from the
        jar.

        .. seealso:: values() and items().
        """
        return list(self.iterkeys())

    def itervalues(self):
        """Dict-like itervalues() that returns an iterator of values of cookies
        from the jar.

        .. seealso:: iterkeys() and iteritems().
        """
        for cookie in iter(self):
            yield cookie.value

    def values(self):
        """Dict-like values() that returns a list of values of cookies from the
        jar.

        .. seealso:: keys() and items().
        """
        return list(self.itervalues())

    def iteritems(self):
        """Dict-like iteritems() that returns an iterator of name-value tuples
        from the jar.

        .. seealso:: iterkeys() and itervalues().
        """
        for cookie in iter(self):
            yield cookie.name, cookie.value

    def items(self):
        """Dict-like items() that returns a list of name-value tuples from the
        jar. Allows client-code to call ``dict(RequestsCookieJar)`` and get a
        vanilla python dict of key value pairs.

        .. seealso:: keys() and values().
        """
        return list(self.iteritems())

    def list_domains(self):
        """Utility method to list all the domains in the jar."""
        domains = []
        for cookie in iter(self):
            if cookie.domain not in domains:
                domains.append(cookie.domain)
        return domains

    def list_paths(self):
        """Utility method to list all the paths in the jar."""
        paths = []
        for cookie in iter(self):
            if cookie.path not in paths:
                paths.append(cookie.path)
        return paths

    def multiple_domains(self):
        """Returns True if there are multiple domains in the jar.
        Returns False otherwise.

        :rtype: bool
        """
        domains = []
        for cookie in iter(self):
            if cookie.domain is not None and cookie.domain in domains:
                return True
            domains.append(cookie.domain)
        return False  # there is only one domain in jar

    def get_dict(self, domain=None, path=None):
        """Takes as an argument an optional domain and path and returns a plain
        old Python dict of name-value pairs of cookies that meet the
        requirements.

        :rtype: dict
        """
        dictionary = {}
        for cookie in iter(self):
            if (domain is None or cookie.domain == domain) and (
                path is None or cookie.path == path
            ):
                dictionary[cookie.name] = cookie.value
        return dictionary

    def __contains__(self, name):
        try:
            return super().__contains__(name)
        except CookieConflictError:
            return True

    def __getitem__(self, name):
        """Dict-like __getitem__() for compatibility with client code. Throws
        exception if there are more than one cookie with name. In that case,
        use the more explicit get() method instead.

        .. warning:: operation is O(n), not O(1).
        """
        return self._find_no_duplicates(name)

    def __setitem__(self, name, value):
        """Dict-like __setitem__ for compatibility with client code. Throws
        exception if there is already a cookie of that name in the jar. In that
        case, use the more explicit set() method instead.
        """
        self.set(name, value)

    def __delitem__(self, name):
        """Deletes a cookie given a name. Wraps ``http.cookiejar.CookieJar``'s
        ``remove_cookie_by_name()``.
        """
        remove_cookie_by_name(self, name)

    def set_cookie(self, cookie, *args, **kwargs):
        if (
            hasattr(cookie.value, "startswith")
            and cookie.value.startswith('"')
            and cookie.value.endswith('"')
        ):
            cookie.value = cookie.value.replace('\\"', "")
        return super().set_cookie(cookie, *args, **kwargs)

    def update(self, other):
        """Updates this jar with cookies from another CookieJar or dict-like"""
        if isinstance(other, cookielib.CookieJar):
            for cookie in other:
                self.set_cookie(copy.copy(cookie))
        else:
            super().update(other)

    def _find(self, name, domain=None, path=None):
        """Requests uses this method internally to get cookie values.

        If there are conflicting cookies, _find arbitrarily chooses one.
        See _find_no_duplicates if you want an exception thrown if there are
        conflicting cookies.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :return: cookie.value
        """
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        return cookie.value

        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def _find_no_duplicates(self, name, domain=None, path=None):
        """Both ``__get_item__`` and ``get`` call this function: it's never
        used elsewhere in Requests.

        :param name: a string containing name of cookie
        :param domain: (optional) string containing domain of cookie
        :param path: (optional) string containing path of cookie
        :raises KeyError: if cookie is not found
        :raises CookieConflictError: if there are multiple cookies
            that match name and optionally domain and path
        :return: cookie.value
        """
        toReturn = None
        for cookie in iter(self):
            if cookie.name == name:
                if domain is None or cookie.domain == domain:
                    if path is None or cookie.path == path:
                        if toReturn is not None:
                            # if there are multiple cookies that meet passed in criteria
                            raise CookieConflictError(
                                f"There are multiple cookies with name, {name!r}"
                            )
                        # we will eventually return this as long as no cookie conflict
                        toReturn = cookie.value

        if toReturn:
            return toReturn
        raise KeyError(f"name={name!r}, domain={domain!r}, path={path!r}")

    def __getstate__(self):
        """Unlike a normal CookieJar, this class is pickleable."""
        state = self.__dict__.copy()
        # remove the unpickleable RLock object
        state.pop("_cookies_lock")
        return state

    def __setstate__(self, state):
        """Unlike a normal CookieJar, this class is pickleable."""
        self.__dict__.update(state)
        if "_cookies_lock" not in self.__dict__:
            self._cookies_lock = threading.RLock()

    def copy(self):
        """Return a copy of this RequestsCookieJar."""
        new_cj = RequestsCookieJar()
        new_cj.set_policy(self.get_policy())
        new_cj.update(self)
        return new_cj

    def get_policy(self):
        """Return the CookiePolicy instance used."""
        return self._policy


def _copy_cookie_jar(jar):
    if jar is None:
        return None

    if hasattr(jar, "copy"):
        # We're dealing with an instance of RequestsCookieJar
        return jar.copy()
    # We're dealing with a generic CookieJar instance
    new_jar = copy.copy(jar)
    new_jar.clear()
    for cookie in jar:
        new_jar.set_cookie(copy.copy(cookie))
    return new_jar


def create_cookie(name, value, **kwargs):
    """Make a cookie from underspecified parameters.

    By default, the pair of `name` and `value` will be set for the domain ''
    and sent on every request (this is sometimes called a "supercookie").
    """
    result = {
        "version": 0,
        "name": name,
        "value": value,
        "port": None,
        "domain": "",
        "path": "/",
        "secure": False,
        "expires": None,
        "discard": True,
        "comment": None,
        "comment_url": None,
        "rest": {"HttpOnly": None},
        "rfc2109": False,
    }

    badargs = set(kwargs) - set(result)
    if badargs:
        raise TypeError(
            f"create_cookie() got unexpected keyword arguments: {list(badargs)}"
        )

    result.update(kwargs)
    result["port_specified"] = bool(result["port"])
    result["domain_specified"] = bool(result["domain"])
    result["domain_initial_dot"] = result["domain"].startswith(".")
    result["path_specified"] = bool(result["path"])

    return cookielib.Cookie(**result)


def morsel_to_cookie(morsel):
    """Convert a Morsel object into a Cookie containing the one k/v pair."""

    expires = None
    if morsel["max-age"]:
        try:
            expires = int(time.time() + int(morsel["max-age"]))
        except ValueError:
            raise TypeError(f"max-age: {morsel['max-age']} must be integer")
    elif morsel["expires"]:
        time_template = "%a, %d-%b-%Y %H:%M:%S GMT"
        expires = calendar.timegm(time.strptime(morsel["expires"], time_template))
    return create_cookie(
        comment=morsel["comment"],
        comment_url=bool(morsel["comment"]),
        discard=False,
        domain=morsel["domain"],
        expires=expires,
        name=morsel.key,
        path=morsel["path"],
        port=None,
        rest={"HttpOnly": morsel["httponly"]},
        rfc2109=False,
        secure=bool(morsel["secure"]),
        value=morsel.value,
        version=morsel["version"] or 0,
    )


def cookiejar_from_dict(cookie_dict, cookiejar=None, overwrite=True):
    """Returns a CookieJar from a key/value dictionary.

    :param cookie_dict: Dict of key/values to insert into CookieJar.
    :param cookiejar: (optional) A cookiejar to add the cookies to.
    :param overwrite: (optional) If False, will not replace cookies
        already in the jar with new ones.
    :rtype: CookieJar
    """
    if cookiejar is None:
        cookiejar = RequestsCookieJar()

    if cookie_dict is not None:
        names_from_jar = [cookie.name for cookie in cookiejar]
        for name in cookie_dict:
            if overwrite or (name not in names_from_jar):
                cookiejar.set_cookie(create_cookie(name, cookie_dict[name]))

    return cookiejar


def merge_cookies(cookiejar, cookies):
    """Add cookies to cookiejar and returns a merged CookieJar.

    :param cookiejar: CookieJar object to add the cookies to.
    :param cookies: Dictionary or CookieJar object to be added.
    :rtype: CookieJar
    """
    if not isinstance(cookiejar, cookielib.CookieJar):
        raise ValueError("You can only merge into CookieJar")

    if isinstance(cookies, dict):
        cookiejar = cookiejar_from_dict(cookies, cookiejar=cookiejar, overwrite=False)
    elif isinstance(cookies, cookielib.CookieJar):
        try:
            cookiejar.update(cookies)
        except AttributeError:
            for cookie_in_jar in cookies:
                cookiejar.set_cookie(cookie_in_jar)

    return cookiejar

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\version.py ===
# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.
"""
.. testsetup::

    from packaging.version import parse, Version
"""

import itertools
import re
from typing import Any, Callable, NamedTuple, Optional, SupportsInt, Tuple, Union

from ._structures import Infinity, InfinityType, NegativeInfinity, NegativeInfinityType

__all__ = ["VERSION_PATTERN", "parse", "Version", "InvalidVersion"]

LocalType = Tuple[Union[int, str], ...]

CmpPrePostDevType = Union[InfinityType, NegativeInfinityType, Tuple[str, int]]
CmpLocalType = Union[
    NegativeInfinityType,
    Tuple[Union[Tuple[int, str], Tuple[NegativeInfinityType, Union[int, str]]], ...],
]
CmpKey = Tuple[
    int,
    Tuple[int, ...],
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpPrePostDevType,
    CmpLocalType,
]
VersionComparisonMethod = Callable[[CmpKey, CmpKey], bool]


class _Version(NamedTuple):
    epoch: int
    release: Tuple[int, ...]
    dev: Optional[Tuple[str, int]]
    pre: Optional[Tuple[str, int]]
    post: Optional[Tuple[str, int]]
    local: Optional[LocalType]


def parse(version: str) -> "Version":
    """Parse the given version string.

    >>> parse('1.0.dev1')
    <Version('1.0.dev1')>

    :param version: The version string to parse.
    :raises InvalidVersion: When the version string is not a valid version.
    """
    return Version(version)


class InvalidVersion(ValueError):
    """Raised when a version string is not a valid version.

    >>> Version("invalid")
    Traceback (most recent call last):
        ...
    packaging.version.InvalidVersion: Invalid version: 'invalid'
    """


class _BaseVersion:
    _key: Tuple[Any, ...]

    def __hash__(self) -> int:
        return hash(self._key)

    # Please keep the duplicated `isinstance` check
    # in the six comparisons hereunder
    # unless you find a way to avoid adding overhead function calls.
    def __lt__(self, other: "_BaseVersion") -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key < other._key

    def __le__(self, other: "_BaseVersion") -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key <= other._key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key == other._key

    def __ge__(self, other: "_BaseVersion") -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key >= other._key

    def __gt__(self, other: "_BaseVersion") -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key > other._key

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, _BaseVersion):
            return NotImplemented

        return self._key != other._key


# Deliberately not anchored to the start and end of the string, to make it
# easier for 3rd party code to reuse
_VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_PATTERN = _VERSION_PATTERN
"""
A string containing the regular expression used to match a valid version.

The pattern is not anchored at either end, and is intended for embedding in larger
expressions (for example, matching a version number as part of a file name). The
regular expression should be compiled with the ``re.VERBOSE`` and ``re.IGNORECASE``
flags set.

:meta hide-value:
"""


class Version(_BaseVersion):
    """This class abstracts handling of a project's versions.

    A :class:`Version` instance is comparison aware and can be compared and
    sorted using the standard Python interfaces.

    >>> v1 = Version("1.0a5")
    >>> v2 = Version("1.0")
    >>> v1
    <Version('1.0a5')>
    >>> v2
    <Version('1.0')>
    >>> v1 < v2
    True
    >>> v1 == v2
    False
    >>> v1 > v2
    False
    >>> v1 >= v2
    False
    >>> v1 <= v2
    True
    """

    _regex = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)
    _key: CmpKey

    def __init__(self, version: str) -> None:
        """Initialize a Version object.

        :param version:
            The string representation of a version which will be parsed and normalized
            before use.
        :raises InvalidVersion:
            If the ``version`` does not conform to PEP 440 in any way then this
            exception will be raised.
        """

        # Validate the version and parse it into pieces
        match = self._regex.search(version)
        if not match:
            raise InvalidVersion(f"Invalid version: '{version}'")

        # Store the parsed out pieces of the version
        self._version = _Version(
            epoch=int(match.group("epoch")) if match.group("epoch") else 0,
            release=tuple(int(i) for i in match.group("release").split(".")),
            pre=_parse_letter_version(match.group("pre_l"), match.group("pre_n")),
            post=_parse_letter_version(
                match.group("post_l"), match.group("post_n1") or match.group("post_n2")
            ),
            dev=_parse_letter_version(match.group("dev_l"), match.group("dev_n")),
            local=_parse_local_version(match.group("local")),
        )

        # Generate a key which will be used for sorting
        self._key = _cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __repr__(self) -> str:
        """A representation of the Version that shows all internal state.

        >>> Version('1.0.0')
        <Version('1.0.0')>
        """
        return f"<Version('{self}')>"

    def __str__(self) -> str:
        """A string representation of the version that can be rounded-tripped.

        >>> str(Version("1.0a5"))
        '1.0a5'
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            parts.append(f".post{self.post}")

        # Development release
        if self.dev is not None:
            parts.append(f".dev{self.dev}")

        # Local version segment
        if self.local is not None:
            parts.append(f"+{self.local}")

        return "".join(parts)

    @property
    def epoch(self) -> int:
        """The epoch of the version.

        >>> Version("2.0.0").epoch
        0
        >>> Version("1!2.0.0").epoch
        1
        """
        return self._version.epoch

    @property
    def release(self) -> Tuple[int, ...]:
        """The components of the "release" segment of the version.

        >>> Version("1.2.3").release
        (1, 2, 3)
        >>> Version("2.0.0").release
        (2, 0, 0)
        >>> Version("1!2.0.0.post0").release
        (2, 0, 0)

        Includes trailing zeroes but not the epoch or any pre-release / development /
        post-release suffixes.
        """
        return self._version.release

    @property
    def pre(self) -> Optional[Tuple[str, int]]:
        """The pre-release segment of the version.

        >>> print(Version("1.2.3").pre)
        None
        >>> Version("1.2.3a1").pre
        ('a', 1)
        >>> Version("1.2.3b1").pre
        ('b', 1)
        >>> Version("1.2.3rc1").pre
        ('rc', 1)
        """
        return self._version.pre

    @property
    def post(self) -> Optional[int]:
        """The post-release number of the version.

        >>> print(Version("1.2.3").post)
        None
        >>> Version("1.2.3.post1").post
        1
        """
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self) -> Optional[int]:
        """The development number of the version.

        >>> print(Version("1.2.3").dev)
        None
        >>> Version("1.2.3.dev1").dev
        1
        """
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self) -> Optional[str]:
        """The local version segment of the version.

        >>> print(Version("1.2.3").local)
        None
        >>> Version("1.2.3+abc").local
        'abc'
        """
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        else:
            return None

    @property
    def public(self) -> str:
        """The public portion of the version.

        >>> Version("1.2.3").public
        '1.2.3'
        >>> Version("1.2.3+abc").public
        '1.2.3'
        >>> Version("1.2.3+abc.dev1").public
        '1.2.3'
        """
        return str(self).split("+", 1)[0]

    @property
    def base_version(self) -> str:
        """The "base version" of the version.

        >>> Version("1.2.3").base_version
        '1.2.3'
        >>> Version("1.2.3+abc").base_version
        '1.2.3'
        >>> Version("1!1.2.3+abc.dev1").base_version
        '1!1.2.3'

        The "base version" is the public version of the project without any pre or post
        release markers.
        """
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append(f"{self.epoch}!")

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        return "".join(parts)

    @property
    def is_prerelease(self) -> bool:
        """Whether this version is a pre-release.

        >>> Version("1.2.3").is_prerelease
        False
        >>> Version("1.2.3a1").is_prerelease
        True
        >>> Version("1.2.3b1").is_prerelease
        True
        >>> Version("1.2.3rc1").is_prerelease
        True
        >>> Version("1.2.3dev1").is_prerelease
        True
        """
        return self.dev is not None or self.pre is not None

    @property
    def is_postrelease(self) -> bool:
        """Whether this version is a post-release.

        >>> Version("1.2.3").is_postrelease
        False
        >>> Version("1.2.3.post1").is_postrelease
        True
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """Whether this version is a development release.

        >>> Version("1.2.3").is_devrelease
        False
        >>> Version("1.2.3.dev1").is_devrelease
        True
        """
        return self.dev is not None

    @property
    def major(self) -> int:
        """The first item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").major
        1
        """
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self) -> int:
        """The second item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").minor
        2
        >>> Version("1").minor
        0
        """
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self) -> int:
        """The third item of :attr:`release` or ``0`` if unavailable.

        >>> Version("1.2.3").micro
        3
        >>> Version("1").micro
        0
        """
        return self.release[2] if len(self.release) >= 3 else 0


def _parse_letter_version(
    letter: Optional[str], number: Union[str, bytes, SupportsInt, None]
) -> Optional[Tuple[str, int]]:
    if letter:
        # We consider there to be an implicit 0 in a pre-release if there is
        # not a numeral associated with it.
        if number is None:
            number = 0

        # We normalize any letters to their lower case form
        letter = letter.lower()

        # We consider some words to be alternate spellings of other words and
        # in those cases we want to normalize the spellings to our preferred
        # spelling.
        if letter == "alpha":
            letter = "a"
        elif letter == "beta":
            letter = "b"
        elif letter in ["c", "pre", "preview"]:
            letter = "rc"
        elif letter in ["rev", "r"]:
            letter = "post"

        return letter, int(number)
    if not letter and number:
        # We assume if we are given a number, but we are not given a letter
        # then this is using the implicit post release syntax (e.g. 1.0-1)
        letter = "post"

        return letter, int(number)

    return None


_local_version_separators = re.compile(r"[\._-]")


def _parse_local_version(local: Optional[str]) -> Optional[LocalType]:
    """
    Takes a string like abc.1.twelve and turns it into ("abc", 1, "twelve").
    """
    if local is not None:
        return tuple(
            part.lower() if not part.isdigit() else int(part)
            for part in _local_version_separators.split(local)
        )
    return None


def _cmpkey(
    epoch: int,
    release: Tuple[int, ...],
    pre: Optional[Tuple[str, int]],
    post: Optional[Tuple[str, int]],
    dev: Optional[Tuple[str, int]],
    local: Optional[LocalType],
) -> CmpKey:
    # When we compare a release version, we want to compare it with all of the
    # trailing zeros removed. So we'll use a reverse the list, drop all the now
    # leading zeros until we come to something non zero, then take the rest
    # re-reverse it back into the correct order and make it a tuple and use
    # that for our sorting key.
    _release = tuple(
        reversed(list(itertools.dropwhile(lambda x: x == 0, reversed(release))))
    )

    # We need to "trick" the sorting algorithm to put 1.0.dev0 before 1.0a0.
    # We'll do this by abusing the pre segment, but we _only_ want to do this
    # if there is not a pre or a post segment. If we have one of those then
    # the normal sorting rules will handle this case correctly.
    if pre is None and post is None and dev is not None:
        _pre: CmpPrePostDevType = NegativeInfinity
    # Versions without a pre-release (except as noted above) should sort after
    # those with one.
    elif pre is None:
        _pre = Infinity
    else:
        _pre = pre

    # Versions without a post segment should sort before those with one.
    if post is None:
        _post: CmpPrePostDevType = NegativeInfinity

    else:
        _post = post

    # Versions without a development segment should sort after those with one.
    if dev is None:
        _dev: CmpPrePostDevType = Infinity

    else:
        _dev = dev

    if local is None:
        # Versions without a local segment should sort before those with one.
        _local: CmpLocalType = NegativeInfinity
    else:
        # Versions with a local segment need that segment parsed to implement
        # the sorting rules in PEP440.
        # - Alpha numeric segments sort before numeric segments
        # - Alpha numeric segments sort lexicographically
        # - Numeric segments sort numerically
        # - Shorter versions sort before longer versions when the prefixes
        #   match exactly
        _local = tuple(
            (i, "") if isinstance(i, int) else (NegativeInfinity, i) for i in local
        )

    return epoch, _release, _pre, _post, _dev, _local

# === NexusCore/myenv\Lib\site-packages\pip\_internal\req\constructors.py ===
"""Backing implementation for InstallRequirement's various constructors

The idea here is that these formed a major chunk of InstallRequirement's size
so, moving them and support code dedicated to them outside of that class
helps creates for better understandability for the rest of the code.

These are meant to be used elsewhere within pip to create instances of
InstallRequirement.
"""

import copy
import logging
import os
import re
from dataclasses import dataclass
from typing import Collection, Dict, List, Optional, Set, Tuple, Union

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
from pip._vendor.packaging.specifiers import Specifier

from pip._internal.exceptions import InstallationError
from pip._internal.models.index import PyPI, TestPyPI
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.req.req_file import ParsedRequirement
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.filetypes import is_archive_file
from pip._internal.utils.misc import is_installable_dir
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import is_url, vcs

__all__ = [
    "install_req_from_editable",
    "install_req_from_line",
    "parse_editable",
]

logger = logging.getLogger(__name__)
operators = Specifier._operators.keys()


def _strip_extras(path: str) -> Tuple[str, Optional[str]]:
    m = re.match(r"^(.+)(\[[^\]]+\])$", path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


def convert_extras(extras: Optional[str]) -> Set[str]:
    if not extras:
        return set()
    return get_requirement("placeholder" + extras.lower()).extras


def _set_requirement_extras(req: Requirement, new_extras: Set[str]) -> Requirement:
    """
    Returns a new requirement based on the given one, with the supplied extras. If the
    given requirement already has extras those are replaced (or dropped if no new extras
    are given).
    """
    match: Optional[re.Match[str]] = re.fullmatch(
        # see https://peps.python.org/pep-0508/#complete-grammar
        r"([\w\t .-]+)(\[[^\]]*\])?(.*)",
        str(req),
        flags=re.ASCII,
    )
    # ireq.req is a valid requirement so the regex should always match
    assert (
        match is not None
    ), f"regex match on requirement {req} failed, this should never happen"
    pre: Optional[str] = match.group(1)
    post: Optional[str] = match.group(3)
    assert (
        pre is not None and post is not None
    ), f"regex group selection for requirement {req} failed, this should never happen"
    extras: str = "[{}]".format(",".join(sorted(new_extras)) if new_extras else "")
    return get_requirement(f"{pre}{extras}{post}")


def parse_editable(editable_req: str) -> Tuple[Optional[str], str, Set[str]]:
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """

    url = editable_req

    # If a file path is specified with extras, strip off the extras.
    url_no_extras, extras = _strip_extras(url)

    if os.path.isdir(url_no_extras):
        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith("file:"):
        package_name = Link(url_no_extras).egg_fragment
        if extras:
            return (
                package_name,
                url_no_extras,
                get_requirement("placeholder" + extras.lower()).extras,
            )
        else:
            return package_name, url_no_extras, set()

    for version_control in vcs:
        if url.lower().startswith(f"{version_control}:"):
            url = f"{version_control}+{url}"
            break

    link = Link(url)

    if not link.is_vcs:
        backends = ", ".join(vcs.all_schemes)
        raise InstallationError(
            f"{editable_req} is not a valid editable requirement. "
            f"It should either be a path to a local project or a VCS URL "
            f"(beginning with {backends})."
        )

    package_name = link.egg_fragment
    if not package_name:
        raise InstallationError(
            f"Could not detect requirement name for '{editable_req}', "
            "please specify one with #egg=your_package_name"
        )
    return package_name, url, set()


def check_first_requirement_in_file(filename: str) -> None:
    """Check if file is parsable as a requirements file.

    This is heavily based on ``pkg_resources.parse_requirements``, but
    simplified to just check the first meaningful line.

    :raises InvalidRequirement: If the first meaningful line cannot be parsed
        as an requirement.
    """
    with open(filename, encoding="utf-8", errors="ignore") as f:
        # Create a steppable iterator, so we can handle \-continuations.
        lines = (
            line
            for line in (line.strip() for line in f)
            if line and not line.startswith("#")  # Skip blank lines/comments.
        )

        for line in lines:
            # Drop comments -- a hash without a space may be in a URL.
            if " #" in line:
                line = line[: line.find(" #")]
            # If there is a line continuation, drop it, and append the next line.
            if line.endswith("\\"):
                line = line[:-2].strip() + next(lines, "")
            get_requirement(line)
            return


def deduce_helpful_msg(req: str) -> str:
    """Returns helpful msg in case requirements file does not exist,
    or cannot be parsed.

    :params req: Requirements file path
    """
    if not os.path.exists(req):
        return f" File '{req}' does not exist."
    msg = " The path does exist. "
    # Try to parse and check if it is a requirements file.
    try:
        check_first_requirement_in_file(req)
    except InvalidRequirement:
        logger.debug("Cannot parse '%s' as requirements file", req)
    else:
        msg += (
            f"The argument you provided "
            f"({req}) appears to be a"
            f" requirements file. If that is the"
            f" case, use the '-r' flag to install"
            f" the packages specified within it."
        )
    return msg


@dataclass(frozen=True)
class RequirementParts:
    requirement: Optional[Requirement]
    link: Optional[Link]
    markers: Optional[Marker]
    extras: Set[str]


def parse_req_from_editable(editable_req: str) -> RequirementParts:
    name, url, extras_override = parse_editable(editable_req)

    if name is not None:
        try:
            req: Optional[Requirement] = get_requirement(name)
        except InvalidRequirement as exc:
            raise InstallationError(f"Invalid requirement: {name!r}: {exc}")
    else:
        req = None

    link = Link(url)

    return RequirementParts(req, link, None, extras_override)


# ---- The actual constructors follow ----


def install_req_from_editable(
    editable_req: str,
    comes_from: Optional[Union[InstallRequirement, str]] = None,
    *,
    use_pep517: Optional[bool] = None,
    isolated: bool = False,
    global_options: Optional[List[str]] = None,
    hash_options: Optional[Dict[str, List[str]]] = None,
    constraint: bool = False,
    user_supplied: bool = False,
    permit_editable_wheels: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    parts = parse_req_from_editable(editable_req)

    return InstallRequirement(
        parts.requirement,
        comes_from=comes_from,
        user_supplied=user_supplied,
        editable=True,
        permit_editable_wheels=permit_editable_wheels,
        link=parts.link,
        constraint=constraint,
        use_pep517=use_pep517,
        isolated=isolated,
        global_options=global_options,
        hash_options=hash_options,
        config_settings=config_settings,
        extras=parts.extras,
    )


def _looks_like_path(name: str) -> bool:
    """Checks whether the string "looks like" a path on the filesystem.

    This does not check whether the target actually exists, only judge from the
    appearance.

    Returns true if any of the following conditions is true:
    * a path separator is found (either os.path.sep or os.path.altsep);
    * a dot is found (which represents the current directory).
    """
    if os.path.sep in name:
        return True
    if os.path.altsep is not None and os.path.altsep in name:
        return True
    if name.startswith("."):
        return True
    return False


def _get_url_from_path(path: str, name: str) -> Optional[str]:
    """
    First, it checks whether a provided path is an installable directory. If it
    is, returns the path.

    If false, check if the path is an archive file (such as a .whl).
    The function checks if the path is a file. If false, if the path has
    an @, it will treat it as a PEP 440 URL requirement and return the path.
    """
    if _looks_like_path(name) and os.path.isdir(path):
        if is_installable_dir(path):
            return path_to_url(path)
        # TODO: The is_installable_dir test here might not be necessary
        #       now that it is done in load_pyproject_toml too.
        raise InstallationError(
            f"Directory {name!r} is not installable. Neither 'setup.py' "
            "nor 'pyproject.toml' found."
        )
    if not is_archive_file(path):
        return None
    if os.path.isfile(path):
        return path_to_url(path)
    urlreq_parts = name.split("@", 1)
    if len(urlreq_parts) >= 2 and not _looks_like_path(urlreq_parts[0]):
        # If the path contains '@' and the part before it does not look
        # like a path, try to treat it as a PEP 440 URL req instead.
        return None
    logger.warning(
        "Requirement %r looks like a filename, but the file does not exist",
        name,
    )
    return path_to_url(path)


def parse_req_from_line(name: str, line_source: Optional[str]) -> RequirementParts:
    if is_url(name):
        marker_sep = "; "
    else:
        marker_sep = ";"
    if marker_sep in name:
        name, markers_as_string = name.split(marker_sep, 1)
        markers_as_string = markers_as_string.strip()
        if not markers_as_string:
            markers = None
        else:
            markers = Marker(markers_as_string)
    else:
        markers = None
    name = name.strip()
    req_as_string = None
    path = os.path.normpath(os.path.abspath(name))
    link = None
    extras_as_string = None

    if is_url(name):
        link = Link(name)
    else:
        p, extras_as_string = _strip_extras(path)
        url = _get_url_from_path(p, name)
        if url is not None:
            link = Link(url)

    # it's a local file, dir, or url
    if link:
        # Handle relative file URLs
        if link.scheme == "file" and re.search(r"\.\./", link.url):
            link = Link(path_to_url(os.path.normpath(os.path.abspath(link.path))))
        # wheel file
        if link.is_wheel:
            wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
            req_as_string = f"{wheel.name}=={wheel.version}"
        else:
            # set the req to the egg fragment.  when it's not there, this
            # will become an 'unnamed' requirement
            req_as_string = link.egg_fragment

    # a requirement specifier
    else:
        req_as_string = name

    extras = convert_extras(extras_as_string)

    def with_source(text: str) -> str:
        if not line_source:
            return text
        return f"{text} (from {line_source})"

    def _parse_req_string(req_as_string: str) -> Requirement:
        try:
            return get_requirement(req_as_string)
        except InvalidRequirement as exc:
            if os.path.sep in req_as_string:
                add_msg = "It looks like a path."
                add_msg += deduce_helpful_msg(req_as_string)
            elif "=" in req_as_string and not any(
                op in req_as_string for op in operators
            ):
                add_msg = "= is not a valid operator. Did you mean == ?"
            else:
                add_msg = ""
            msg = with_source(f"Invalid requirement: {req_as_string!r}: {exc}")
            if add_msg:
                msg += f"\nHint: {add_msg}"
            raise InstallationError(msg)

    if req_as_string is not None:
        req: Optional[Requirement] = _parse_req_string(req_as_string)
    else:
        req = None

    return RequirementParts(req, link, markers, extras)


def install_req_from_line(
    name: str,
    comes_from: Optional[Union[str, InstallRequirement]] = None,
    *,
    use_pep517: Optional[bool] = None,
    isolated: bool = False,
    global_options: Optional[List[str]] = None,
    hash_options: Optional[Dict[str, List[str]]] = None,
    constraint: bool = False,
    line_source: Optional[str] = None,
    user_supplied: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    """Creates an InstallRequirement from a name, which might be a
    requirement, directory containing 'setup.py', filename, or URL.

    :param line_source: An optional string describing where the line is from,
        for logging purposes in case of an error.
    """
    parts = parse_req_from_line(name, line_source)

    return InstallRequirement(
        parts.requirement,
        comes_from,
        link=parts.link,
        markers=parts.markers,
        use_pep517=use_pep517,
        isolated=isolated,
        global_options=global_options,
        hash_options=hash_options,
        config_settings=config_settings,
        constraint=constraint,
        extras=parts.extras,
        user_supplied=user_supplied,
    )


def install_req_from_req_string(
    req_string: str,
    comes_from: Optional[InstallRequirement] = None,
    isolated: bool = False,
    use_pep517: Optional[bool] = None,
    user_supplied: bool = False,
) -> InstallRequirement:
    try:
        req = get_requirement(req_string)
    except InvalidRequirement as exc:
        raise InstallationError(f"Invalid requirement: {req_string!r}: {exc}")

    domains_not_allowed = [
        PyPI.file_storage_domain,
        TestPyPI.file_storage_domain,
    ]
    if (
        req.url
        and comes_from
        and comes_from.link
        and comes_from.link.netloc in domains_not_allowed
    ):
        # Explicitly disallow pypi packages that depend on external urls
        raise InstallationError(
            "Packages installed from PyPI cannot depend on packages "
            "which are not also hosted on PyPI.\n"
            f"{comes_from.name} depends on {req} "
        )

    return InstallRequirement(
        req,
        comes_from,
        isolated=isolated,
        use_pep517=use_pep517,
        user_supplied=user_supplied,
    )


def install_req_from_parsed_requirement(
    parsed_req: ParsedRequirement,
    isolated: bool = False,
    use_pep517: Optional[bool] = None,
    user_supplied: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    if parsed_req.is_editable:
        req = install_req_from_editable(
            parsed_req.requirement,
            comes_from=parsed_req.comes_from,
            use_pep517=use_pep517,
            constraint=parsed_req.constraint,
            isolated=isolated,
            user_supplied=user_supplied,
            config_settings=config_settings,
        )

    else:
        req = install_req_from_line(
            parsed_req.requirement,
            comes_from=parsed_req.comes_from,
            use_pep517=use_pep517,
            isolated=isolated,
            global_options=(
                parsed_req.options.get("global_options", [])
                if parsed_req.options
                else []
            ),
            hash_options=(
                parsed_req.options.get("hashes", {}) if parsed_req.options else {}
            ),
            constraint=parsed_req.constraint,
            line_source=parsed_req.line_source,
            user_supplied=user_supplied,
            config_settings=config_settings,
        )
    return req


def install_req_from_link_and_ireq(
    link: Link, ireq: InstallRequirement
) -> InstallRequirement:
    return InstallRequirement(
        req=ireq.req,
        comes_from=ireq.comes_from,
        editable=ireq.editable,
        link=link,
        markers=ireq.markers,
        use_pep517=ireq.use_pep517,
        isolated=ireq.isolated,
        global_options=ireq.global_options,
        hash_options=ireq.hash_options,
        config_settings=ireq.config_settings,
        user_supplied=ireq.user_supplied,
    )


def install_req_drop_extras(ireq: InstallRequirement) -> InstallRequirement:
    """
    Creates a new InstallationRequirement using the given template but without
    any extras. Sets the original requirement as the new one's parent
    (comes_from).
    """
    return InstallRequirement(
        req=(
            _set_requirement_extras(ireq.req, set()) if ireq.req is not None else None
        ),
        comes_from=ireq,
        editable=ireq.editable,
        link=ireq.link,
        markers=ireq.markers,
        use_pep517=ireq.use_pep517,
        isolated=ireq.isolated,
        global_options=ireq.global_options,
        hash_options=ireq.hash_options,
        constraint=ireq.constraint,
        extras=[],
        config_settings=ireq.config_settings,
        user_supplied=ireq.user_supplied,
        permit_editable_wheels=ireq.permit_editable_wheels,
    )


def install_req_extend_extras(
    ireq: InstallRequirement,
    extras: Collection[str],
) -> InstallRequirement:
    """
    Returns a copy of an installation requirement with some additional extras.
    Makes a shallow copy of the ireq object.
    """
    result = copy.copy(ireq)
    result.extras = {*ireq.extras, *extras}
    result.req = (
        _set_requirement_extras(ireq.req, result.extras)
        if ireq.req is not None
        else None
    )
    return result

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\transports\rest_asyncio.py ===
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

import json
from typing import Any, Callable, Coroutine, Dict, Optional, Sequence, Tuple

from google.auth import __version__ as auth_version

try:
    from google.auth.aio.transport.sessions import AsyncAuthorizedSession  # type: ignore
except ImportError as e:  # pragma: NO COVER
    raise ImportError(
        "The `async_rest` extra of `google-api-core` is required to use long-running operations.  Install it by running "
        "`pip install google-api-core[async_rest]`."
    ) from e

from google.api_core import exceptions as core_exceptions  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core import path_template  # type: ignore
from google.api_core import rest_helpers  # type: ignore
from google.api_core import retry_async as retries_async  # type: ignore
from google.auth.aio import credentials as ga_credentials_async  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
from google.protobuf import json_format  # type: ignore

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO, OperationsTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=f"google-auth@{auth_version}",
)


class AsyncOperationsRestTransport(OperationsTransport):
    """Asynchronous REST backend transport for Operations.

    Manages async long-running operations with an API service.

    When an API method normally takes long time to complete, it can be
    designed to return [Operation][google.api_core.operations_v1.Operation] to the
    client, and the client can use this interface to receive the real
    response asynchronously by polling the operation resource, or pass
    the operation resource to another API (such as Google Cloud Pub/Sub
    API) to receive the response. Any API service that returns
    long-running operations should implement the ``Operations``
    interface so developers can have a consistent client experience.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1
    """

    def __init__(
        self,
        *,
        host: str = "longrunning.googleapis.com",
        credentials: Optional[ga_credentials_async.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        http_options: Optional[Dict] = None,
        path_prefix: str = "v1",
        # TODO(https://github.com/googleapis/python-api-core/issues/715): Add docstring for `credentials_file` to async REST transport.
        # TODO(https://github.com/googleapis/python-api-core/issues/716): Add docstring for `scopes` to async REST transport.
        # TODO(https://github.com/googleapis/python-api-core/issues/717): Add docstring for `quota_project_id` to async REST transport.
        # TODO(https://github.com/googleapis/python-api-core/issues/718): Add docstring for `client_cert_source` to async REST transport.
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to.
            credentials (Optional[google.auth.aio.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
            http_options: a dictionary of http_options for transcoding, to override
                the defaults from operations.proto.  Each method has an entry
                with the corresponding http rules as value.
            path_prefix: path prefix (usually represents API version). Set to
                "v1" by default.

        """
        unsupported_params = {
            # TODO(https://github.com/googleapis/python-api-core/issues/715): Add support for `credentials_file` to async REST transport.
            "google.api_core.client_options.ClientOptions.credentials_file": credentials_file,
            # TODO(https://github.com/googleapis/python-api-core/issues/716): Add support for `scopes` to async REST transport.
            "google.api_core.client_options.ClientOptions.scopes": scopes,
            # TODO(https://github.com/googleapis/python-api-core/issues/717): Add support for `quota_project_id` to async REST transport.
            "google.api_core.client_options.ClientOptions.quota_project_id": quota_project_id,
            # TODO(https://github.com/googleapis/python-api-core/issues/718): Add support for `client_cert_source` to async REST transport.
            "google.api_core.client_options.ClientOptions.client_cert_source": client_cert_source_for_mtls,
            # TODO(https://github.com/googleapis/python-api-core/issues/718): Add support for `client_cert_source` to async REST transport.
            "google.api_core.client_options.ClientOptions.client_cert_source": client_cert_source_for_mtls,
        }
        provided_unsupported_params = [
            name for name, value in unsupported_params.items() if value is not None
        ]
        if provided_unsupported_params:
            raise core_exceptions.AsyncRestUnsupportedParameterError(
                f"The following provided parameters are not supported for `transport=rest_asyncio`: {', '.join(provided_unsupported_params)}"
            )

        super().__init__(
            host=host,
            # TODO(https://github.com/googleapis/python-api-core/issues/709): Remove `type: ignore` when the linked issue is resolved.
            credentials=credentials,  # type: ignore
            client_info=client_info,
            # TODO(https://github.com/googleapis/python-api-core/issues/725): Set always_use_jwt_access token when supported.
            always_use_jwt_access=False,
        )
        # TODO(https://github.com/googleapis/python-api-core/issues/708): add support for
        # `default_host` in AsyncAuthorizedSession for feature parity with the synchronous
        # code.
        # TODO(https://github.com/googleapis/python-api-core/issues/709): Remove `type: ignore` when the linked issue is resolved.
        self._session = AsyncAuthorizedSession(self._credentials)  # type: ignore
        # TODO(https://github.com/googleapis/python-api-core/issues/720): Add wrap logic directly to the property methods for callables.
        self._prep_wrapped_messages(client_info)
        self._http_options = http_options or {}
        self._path_prefix = path_prefix

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.list_operations: gapic_v1.method_async.wrap_method(
                self.list_operations,
                default_retry=retries_async.AsyncRetry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries_async.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                client_info=client_info,
                kind="rest_asyncio",
            ),
            self.get_operation: gapic_v1.method_async.wrap_method(
                self.get_operation,
                default_retry=retries_async.AsyncRetry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries_async.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                client_info=client_info,
                kind="rest_asyncio",
            ),
            self.delete_operation: gapic_v1.method_async.wrap_method(
                self.delete_operation,
                default_retry=retries_async.AsyncRetry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries_async.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                client_info=client_info,
                kind="rest_asyncio",
            ),
            self.cancel_operation: gapic_v1.method_async.wrap_method(
                self.cancel_operation,
                default_retry=retries_async.AsyncRetry(
                    initial=0.5,
                    maximum=10.0,
                    multiplier=2.0,
                    predicate=retries_async.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=10.0,
                ),
                default_timeout=10.0,
                client_info=client_info,
                kind="rest_asyncio",
            ),
        }

    async def _list_operations(
        self,
        request: operations_pb2.ListOperationsRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.ListOperationsResponse:
        r"""Asynchronously call the list operations method over HTTP.

        Args:
            request (~.operations_pb2.ListOperationsRequest):
                The request object. The request message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            ~.operations_pb2.ListOperationsResponse:
                The response message for
                [Operations.ListOperations][google.api_core.operations_v1.Operations.ListOperations].

        """

        http_options = [
            {
                "method": "get",
                "uri": "/{}/{{name=**}}/operations".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.ListOperations" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.ListOperations"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.ListOperationsRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = await getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )
        content = await response.read()

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            payload = json.loads(content.decode("utf-8"))
            request_url = "{host}{uri}".format(host=self._host, uri=uri)
            raise core_exceptions.format_http_response_error(response, method, request_url, payload)  # type: ignore

        # Return the response
        api_response = operations_pb2.ListOperationsResponse()
        json_format.Parse(content, api_response, ignore_unknown_fields=False)
        return api_response

    async def _get_operation(
        self,
        request: operations_pb2.GetOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> operations_pb2.Operation:
        r"""Asynchronously call the get operation method over HTTP.

        Args:
            request (~.operations_pb2.GetOperationRequest):
                The request object. The request message for
                [Operations.GetOperation][google.api_core.operations_v1.Operations.GetOperation].
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.

        Returns:
            ~.operations_pb2.Operation:
                This resource represents a long-
                running operation that is the result of a
                network API call.

        """

        http_options = [
            {
                "method": "get",
                "uri": "/{}/{{name=**/operations/*}}".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.GetOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.GetOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.GetOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = await getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )
        content = await response.read()

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            payload = json.loads(content.decode("utf-8"))
            request_url = "{host}{uri}".format(host=self._host, uri=uri)
            raise core_exceptions.format_http_response_error(response, method, request_url, payload)  # type: ignore

        # Return the response
        api_response = operations_pb2.Operation()
        json_format.Parse(content, api_response, ignore_unknown_fields=False)
        return api_response

    async def _delete_operation(
        self,
        request: operations_pb2.DeleteOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
    ) -> empty_pb2.Empty:
        r"""Asynchronously call the delete operation method over HTTP.

        Args:
            request (~.operations_pb2.DeleteOperationRequest):
                The request object. The request message for
                [Operations.DeleteOperation][google.api_core.operations_v1.Operations.DeleteOperation].

            retry (google.api_core.retry.Retry): Designation of what errors, if any,
                should be retried.
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """

        http_options = [
            {
                "method": "delete",
                "uri": "/{}/{{name=**/operations/*}}".format(self._path_prefix),
            },
        ]
        if "google.longrunning.Operations.DeleteOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.DeleteOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.DeleteOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = await getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            content = await response.read()
            payload = json.loads(content.decode("utf-8"))
            request_url = "{host}{uri}".format(host=self._host, uri=uri)
            raise core_exceptions.format_http_response_error(response, method, request_url, payload)  # type: ignore

        return empty_pb2.Empty()

    async def _cancel_operation(
        self,
        request: operations_pb2.CancelOperationRequest,
        *,
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Leverage `retry`
        # to allow configuring retryable error codes.
        retry=gapic_v1.method_async.DEFAULT,
        timeout: Optional[float] = None,
        metadata: Sequence[Tuple[str, str]] = (),
        # TODO(https://github.com/googleapis/python-api-core/issues/722): Add `retry` parameter
        # to allow configuring retryable error codes.
    ) -> empty_pb2.Empty:
        r"""Asynchronously call the cancel operation method over HTTP.

        Args:
            request (~.operations_pb2.CancelOperationRequest):
                The request object. The request message for
                [Operations.CancelOperation][google.api_core.operations_v1.Operations.CancelOperation].
            timeout (float): The timeout for this request.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """

        http_options = [
            {
                "method": "post",
                "uri": "/{}/{{name=**/operations/*}}:cancel".format(self._path_prefix),
                "body": "*",
            },
        ]
        if "google.longrunning.Operations.CancelOperation" in self._http_options:
            http_options = self._http_options[
                "google.longrunning.Operations.CancelOperation"
            ]

        request_kwargs = self._convert_protobuf_message_to_dict(request)
        transcoded_request = path_template.transcode(http_options, **request_kwargs)

        # Jsonify the request body
        body_request = operations_pb2.CancelOperationRequest()
        json_format.ParseDict(transcoded_request["body"], body_request)
        body = json_format.MessageToDict(
            body_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )
        uri = transcoded_request["uri"]
        method = transcoded_request["method"]

        # Jsonify the query params
        query_params_request = operations_pb2.CancelOperationRequest()
        json_format.ParseDict(transcoded_request["query_params"], query_params_request)
        query_params = json_format.MessageToDict(
            query_params_request,
            preserving_proto_field_name=False,
            use_integers_for_enums=False,
        )

        # Send the request
        headers = dict(metadata)
        headers["Content-Type"] = "application/json"
        # TODO(https://github.com/googleapis/python-api-core/issues/721): Update incorrect use of `uri`` variable name.
        response = await getattr(self._session, method)(
            "{host}{uri}".format(host=self._host, uri=uri),
            timeout=timeout,
            headers=headers,
            params=rest_helpers.flatten_query_params(query_params),
            data=body,
        )

        # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
        # subclass.
        if response.status_code >= 400:
            content = await response.read()
            payload = json.loads(content.decode("utf-8"))
            request_url = "{host}{uri}".format(host=self._host, uri=uri)
            raise core_exceptions.format_http_response_error(response, method, request_url, payload)  # type: ignore

        return empty_pb2.Empty()

    @property
    def list_operations(
        self,
    ) -> Callable[
        [operations_pb2.ListOperationsRequest],
        Coroutine[Any, Any, operations_pb2.ListOperationsResponse],
    ]:
        return self._list_operations

    @property
    def get_operation(
        self,
    ) -> Callable[
        [operations_pb2.GetOperationRequest],
        Coroutine[Any, Any, operations_pb2.Operation],
    ]:
        return self._get_operation

    @property
    def delete_operation(
        self,
    ) -> Callable[
        [operations_pb2.DeleteOperationRequest], Coroutine[Any, Any, empty_pb2.Empty]
    ]:
        return self._delete_operation

    @property
    def cancel_operation(
        self,
    ) -> Callable[
        [operations_pb2.CancelOperationRequest], Coroutine[Any, Any, empty_pb2.Empty]
    ]:
        return self._cancel_operation


__all__ = ("AsyncOperationsRestTransport",)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\req\constructors.py ===
"""Backing implementation for InstallRequirement's various constructors

The idea here is that these formed a major chunk of InstallRequirement's size
so, moving them and support code dedicated to them outside of that class
helps creates for better understandability for the rest of the code.

These are meant to be used elsewhere within pip to create instances of
InstallRequirement.
"""

import copy
import logging
import os
import re
from dataclasses import dataclass
from typing import Collection, Dict, List, Optional, Set, Tuple, Union

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
from pip._vendor.packaging.specifiers import Specifier

from pip._internal.exceptions import InstallationError
from pip._internal.models.index import PyPI, TestPyPI
from pip._internal.models.link import Link
from pip._internal.models.wheel import Wheel
from pip._internal.req.req_file import ParsedRequirement
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.filetypes import is_archive_file
from pip._internal.utils.misc import is_installable_dir
from pip._internal.utils.packaging import get_requirement
from pip._internal.utils.urls import path_to_url
from pip._internal.vcs import is_url, vcs

__all__ = [
    "install_req_from_editable",
    "install_req_from_line",
    "parse_editable",
]

logger = logging.getLogger(__name__)
operators = Specifier._operators.keys()


def _strip_extras(path: str) -> Tuple[str, Optional[str]]:
    m = re.match(r"^(.+)(\[[^\]]+\])$", path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


def convert_extras(extras: Optional[str]) -> Set[str]:
    if not extras:
        return set()
    return get_requirement("placeholder" + extras.lower()).extras


def _set_requirement_extras(req: Requirement, new_extras: Set[str]) -> Requirement:
    """
    Returns a new requirement based on the given one, with the supplied extras. If the
    given requirement already has extras those are replaced (or dropped if no new extras
    are given).
    """
    match: Optional[re.Match[str]] = re.fullmatch(
        # see https://peps.python.org/pep-0508/#complete-grammar
        r"([\w\t .-]+)(\[[^\]]*\])?(.*)",
        str(req),
        flags=re.ASCII,
    )
    # ireq.req is a valid requirement so the regex should always match
    assert (
        match is not None
    ), f"regex match on requirement {req} failed, this should never happen"
    pre: Optional[str] = match.group(1)
    post: Optional[str] = match.group(3)
    assert (
        pre is not None and post is not None
    ), f"regex group selection for requirement {req} failed, this should never happen"
    extras: str = "[{}]".format(",".join(sorted(new_extras)) if new_extras else "")
    return get_requirement(f"{pre}{extras}{post}")


def parse_editable(editable_req: str) -> Tuple[Optional[str], str, Set[str]]:
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """

    url = editable_req

    # If a file path is specified with extras, strip off the extras.
    url_no_extras, extras = _strip_extras(url)

    if os.path.isdir(url_no_extras):
        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith("file:"):
        package_name = Link(url_no_extras).egg_fragment
        if extras:
            return (
                package_name,
                url_no_extras,
                get_requirement("placeholder" + extras.lower()).extras,
            )
        else:
            return package_name, url_no_extras, set()

    for version_control in vcs:
        if url.lower().startswith(f"{version_control}:"):
            url = f"{version_control}+{url}"
            break

    link = Link(url)

    if not link.is_vcs:
        backends = ", ".join(vcs.all_schemes)
        raise InstallationError(
            f"{editable_req} is not a valid editable requirement. "
            f"It should either be a path to a local project or a VCS URL "
            f"(beginning with {backends})."
        )

    package_name = link.egg_fragment
    if not package_name:
        raise InstallationError(
            f"Could not detect requirement name for '{editable_req}', "
            "please specify one with #egg=your_package_name"
        )
    return package_name, url, set()


def check_first_requirement_in_file(filename: str) -> None:
    """Check if file is parsable as a requirements file.

    This is heavily based on ``pkg_resources.parse_requirements``, but
    simplified to just check the first meaningful line.

    :raises InvalidRequirement: If the first meaningful line cannot be parsed
        as an requirement.
    """
    with open(filename, encoding="utf-8", errors="ignore") as f:
        # Create a steppable iterator, so we can handle \-continuations.
        lines = (
            line
            for line in (line.strip() for line in f)
            if line and not line.startswith("#")  # Skip blank lines/comments.
        )

        for line in lines:
            # Drop comments -- a hash without a space may be in a URL.
            if " #" in line:
                line = line[: line.find(" #")]
            # If there is a line continuation, drop it, and append the next line.
            if line.endswith("\\"):
                line = line[:-2].strip() + next(lines, "")
            get_requirement(line)
            return


def deduce_helpful_msg(req: str) -> str:
    """Returns helpful msg in case requirements file does not exist,
    or cannot be parsed.

    :params req: Requirements file path
    """
    if not os.path.exists(req):
        return f" File '{req}' does not exist."
    msg = " The path does exist. "
    # Try to parse and check if it is a requirements file.
    try:
        check_first_requirement_in_file(req)
    except InvalidRequirement:
        logger.debug("Cannot parse '%s' as requirements file", req)
    else:
        msg += (
            f"The argument you provided "
            f"({req}) appears to be a"
            f" requirements file. If that is the"
            f" case, use the '-r' flag to install"
            f" the packages specified within it."
        )
    return msg


@dataclass(frozen=True)
class RequirementParts:
    requirement: Optional[Requirement]
    link: Optional[Link]
    markers: Optional[Marker]
    extras: Set[str]


def parse_req_from_editable(editable_req: str) -> RequirementParts:
    name, url, extras_override = parse_editable(editable_req)

    if name is not None:
        try:
            req: Optional[Requirement] = get_requirement(name)
        except InvalidRequirement as exc:
            raise InstallationError(f"Invalid requirement: {name!r}: {exc}")
    else:
        req = None

    link = Link(url)

    return RequirementParts(req, link, None, extras_override)


# ---- The actual constructors follow ----


def install_req_from_editable(
    editable_req: str,
    comes_from: Optional[Union[InstallRequirement, str]] = None,
    *,
    use_pep517: Optional[bool] = None,
    isolated: bool = False,
    global_options: Optional[List[str]] = None,
    hash_options: Optional[Dict[str, List[str]]] = None,
    constraint: bool = False,
    user_supplied: bool = False,
    permit_editable_wheels: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    parts = parse_req_from_editable(editable_req)

    return InstallRequirement(
        parts.requirement,
        comes_from=comes_from,
        user_supplied=user_supplied,
        editable=True,
        permit_editable_wheels=permit_editable_wheels,
        link=parts.link,
        constraint=constraint,
        use_pep517=use_pep517,
        isolated=isolated,
        global_options=global_options,
        hash_options=hash_options,
        config_settings=config_settings,
        extras=parts.extras,
    )


def _looks_like_path(name: str) -> bool:
    """Checks whether the string "looks like" a path on the filesystem.

    This does not check whether the target actually exists, only judge from the
    appearance.

    Returns true if any of the following conditions is true:
    * a path separator is found (either os.path.sep or os.path.altsep);
    * a dot is found (which represents the current directory).
    """
    if os.path.sep in name:
        return True
    if os.path.altsep is not None and os.path.altsep in name:
        return True
    if name.startswith("."):
        return True
    return False


def _get_url_from_path(path: str, name: str) -> Optional[str]:
    """
    First, it checks whether a provided path is an installable directory. If it
    is, returns the path.

    If false, check if the path is an archive file (such as a .whl).
    The function checks if the path is a file. If false, if the path has
    an @, it will treat it as a PEP 440 URL requirement and return the path.
    """
    if _looks_like_path(name) and os.path.isdir(path):
        if is_installable_dir(path):
            return path_to_url(path)
        # TODO: The is_installable_dir test here might not be necessary
        #       now that it is done in load_pyproject_toml too.
        raise InstallationError(
            f"Directory {name!r} is not installable. Neither 'setup.py' "
            "nor 'pyproject.toml' found."
        )
    if not is_archive_file(path):
        return None
    if os.path.isfile(path):
        return path_to_url(path)
    urlreq_parts = name.split("@", 1)
    if len(urlreq_parts) >= 2 and not _looks_like_path(urlreq_parts[0]):
        # If the path contains '@' and the part before it does not look
        # like a path, try to treat it as a PEP 440 URL req instead.
        return None
    logger.warning(
        "Requirement %r looks like a filename, but the file does not exist",
        name,
    )
    return path_to_url(path)


def parse_req_from_line(name: str, line_source: Optional[str]) -> RequirementParts:
    if is_url(name):
        marker_sep = "; "
    else:
        marker_sep = ";"
    if marker_sep in name:
        name, markers_as_string = name.split(marker_sep, 1)
        markers_as_string = markers_as_string.strip()
        if not markers_as_string:
            markers = None
        else:
            markers = Marker(markers_as_string)
    else:
        markers = None
    name = name.strip()
    req_as_string = None
    path = os.path.normpath(os.path.abspath(name))
    link = None
    extras_as_string = None

    if is_url(name):
        link = Link(name)
    else:
        p, extras_as_string = _strip_extras(path)
        url = _get_url_from_path(p, name)
        if url is not None:
            link = Link(url)

    # it's a local file, dir, or url
    if link:
        # Handle relative file URLs
        if link.scheme == "file" and re.search(r"\.\./", link.url):
            link = Link(path_to_url(os.path.normpath(os.path.abspath(link.path))))
        # wheel file
        if link.is_wheel:
            wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
            req_as_string = f"{wheel.name}=={wheel.version}"
        else:
            # set the req to the egg fragment.  when it's not there, this
            # will become an 'unnamed' requirement
            req_as_string = link.egg_fragment

    # a requirement specifier
    else:
        req_as_string = name

    extras = convert_extras(extras_as_string)

    def with_source(text: str) -> str:
        if not line_source:
            return text
        return f"{text} (from {line_source})"

    def _parse_req_string(req_as_string: str) -> Requirement:
        try:
            return get_requirement(req_as_string)
        except InvalidRequirement as exc:
            if os.path.sep in req_as_string:
                add_msg = "It looks like a path."
                add_msg += deduce_helpful_msg(req_as_string)
            elif "=" in req_as_string and not any(
                op in req_as_string for op in operators
            ):
                add_msg = "= is not a valid operator. Did you mean == ?"
            else:
                add_msg = ""
            msg = with_source(f"Invalid requirement: {req_as_string!r}: {exc}")
            if add_msg:
                msg += f"\nHint: {add_msg}"
            raise InstallationError(msg)

    if req_as_string is not None:
        req: Optional[Requirement] = _parse_req_string(req_as_string)
    else:
        req = None

    return RequirementParts(req, link, markers, extras)


def install_req_from_line(
    name: str,
    comes_from: Optional[Union[str, InstallRequirement]] = None,
    *,
    use_pep517: Optional[bool] = None,
    isolated: bool = False,
    global_options: Optional[List[str]] = None,
    hash_options: Optional[Dict[str, List[str]]] = None,
    constraint: bool = False,
    line_source: Optional[str] = None,
    user_supplied: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    """Creates an InstallRequirement from a name, which might be a
    requirement, directory containing 'setup.py', filename, or URL.

    :param line_source: An optional string describing where the line is from,
        for logging purposes in case of an error.
    """
    parts = parse_req_from_line(name, line_source)

    return InstallRequirement(
        parts.requirement,
        comes_from,
        link=parts.link,
        markers=parts.markers,
        use_pep517=use_pep517,
        isolated=isolated,
        global_options=global_options,
        hash_options=hash_options,
        config_settings=config_settings,
        constraint=constraint,
        extras=parts.extras,
        user_supplied=user_supplied,
    )


def install_req_from_req_string(
    req_string: str,
    comes_from: Optional[InstallRequirement] = None,
    isolated: bool = False,
    use_pep517: Optional[bool] = None,
    user_supplied: bool = False,
) -> InstallRequirement:
    try:
        req = get_requirement(req_string)
    except InvalidRequirement as exc:
        raise InstallationError(f"Invalid requirement: {req_string!r}: {exc}")

    domains_not_allowed = [
        PyPI.file_storage_domain,
        TestPyPI.file_storage_domain,
    ]
    if (
        req.url
        and comes_from
        and comes_from.link
        and comes_from.link.netloc in domains_not_allowed
    ):
        # Explicitly disallow pypi packages that depend on external urls
        raise InstallationError(
            "Packages installed from PyPI cannot depend on packages "
            "which are not also hosted on PyPI.\n"
            f"{comes_from.name} depends on {req} "
        )

    return InstallRequirement(
        req,
        comes_from,
        isolated=isolated,
        use_pep517=use_pep517,
        user_supplied=user_supplied,
    )


def install_req_from_parsed_requirement(
    parsed_req: ParsedRequirement,
    isolated: bool = False,
    use_pep517: Optional[bool] = None,
    user_supplied: bool = False,
    config_settings: Optional[Dict[str, Union[str, List[str]]]] = None,
) -> InstallRequirement:
    if parsed_req.is_editable:
        req = install_req_from_editable(
            parsed_req.requirement,
            comes_from=parsed_req.comes_from,
            use_pep517=use_pep517,
            constraint=parsed_req.constraint,
            isolated=isolated,
            user_supplied=user_supplied,
            config_settings=config_settings,
        )

    else:
        req = install_req_from_line(
            parsed_req.requirement,
            comes_from=parsed_req.comes_from,
            use_pep517=use_pep517,
            isolated=isolated,
            global_options=(
                parsed_req.options.get("global_options", [])
                if parsed_req.options
                else []
            ),
            hash_options=(
                parsed_req.options.get("hashes", {}) if parsed_req.options else {}
            ),
            constraint=parsed_req.constraint,
            line_source=parsed_req.line_source,
            user_supplied=user_supplied,
            config_settings=config_settings,
        )
    return req


def install_req_from_link_and_ireq(
    link: Link, ireq: InstallRequirement
) -> InstallRequirement:
    return InstallRequirement(
        req=ireq.req,
        comes_from=ireq.comes_from,
        editable=ireq.editable,
        link=link,
        markers=ireq.markers,
        use_pep517=ireq.use_pep517,
        isolated=ireq.isolated,
        global_options=ireq.global_options,
        hash_options=ireq.hash_options,
        config_settings=ireq.config_settings,
        user_supplied=ireq.user_supplied,
    )


def install_req_drop_extras(ireq: InstallRequirement) -> InstallRequirement:
    """
    Creates a new InstallationRequirement using the given template but without
    any extras. Sets the original requirement as the new one's parent
    (comes_from).
    """
    return InstallRequirement(
        req=(
            _set_requirement_extras(ireq.req, set()) if ireq.req is not None else None
        ),
        comes_from=ireq,
        editable=ireq.editable,
        link=ireq.link,
        markers=ireq.markers,
        use_pep517=ireq.use_pep517,
        isolated=ireq.isolated,
        global_options=ireq.global_options,
        hash_options=ireq.hash_options,
        constraint=ireq.constraint,
        extras=[],
        config_settings=ireq.config_settings,
        user_supplied=ireq.user_supplied,
        permit_editable_wheels=ireq.permit_editable_wheels,
    )


def install_req_extend_extras(
    ireq: InstallRequirement,
    extras: Collection[str],
) -> InstallRequirement:
    """
    Returns a copy of an installation requirement with some additional extras.
    Makes a shallow copy of the ireq object.
    """
    result = copy.copy(ireq)
    result.extras = {*ireq.extras, *extras}
    result.req = (
        _set_requirement_extras(ireq.req, result.extras)
        if ireq.req is not None
        else None
    )
    return result

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_net_command_factory_xml.py ===
import json

from _pydev_bundle.pydev_is_thread_alive import is_thread_alive
from _pydev_bundle._pydev_saved_modules import thread
from _pydevd_bundle import pydevd_xml, pydevd_frame_utils, pydevd_constants, pydevd_utils
from _pydevd_bundle.pydevd_comm_constants import (
    CMD_THREAD_CREATE,
    CMD_THREAD_KILL,
    CMD_THREAD_SUSPEND,
    CMD_THREAD_RUN,
    CMD_GET_VARIABLE,
    CMD_EVALUATE_EXPRESSION,
    CMD_GET_FRAME,
    CMD_WRITE_TO_CONSOLE,
    CMD_GET_COMPLETIONS,
    CMD_LOAD_SOURCE,
    CMD_SET_NEXT_STATEMENT,
    CMD_EXIT,
    CMD_GET_FILE_CONTENTS,
    CMD_EVALUATE_CONSOLE_EXPRESSION,
    CMD_RUN_CUSTOM_OPERATION,
    CMD_GET_BREAKPOINT_EXCEPTION,
    CMD_SEND_CURR_EXCEPTION_TRACE,
    CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED,
    CMD_SHOW_CONSOLE,
    CMD_GET_ARRAY,
    CMD_INPUT_REQUESTED,
    CMD_GET_DESCRIPTION,
    CMD_PROCESS_CREATED,
    CMD_SHOW_CYTHON_WARNING,
    CMD_LOAD_FULL_VALUE,
    CMD_GET_THREAD_STACK,
    CMD_GET_EXCEPTION_DETAILS,
    CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION,
    CMD_THREAD_RESUME_SINGLE_NOTIFICATION,
    CMD_GET_NEXT_STATEMENT_TARGETS,
    CMD_VERSION,
    CMD_RETURN,
    CMD_SET_PROTOCOL,
    CMD_ERROR,
    MAX_IO_MSG_SIZE,
    VERSION_STRING,
    CMD_RELOAD_CODE,
    CMD_LOAD_SOURCE_FROM_FRAME_ID,
)
from _pydevd_bundle.pydevd_constants import (
    DebugInfoHolder,
    get_thread_id,
    get_global_debugger,
    GetGlobalDebugger,
    set_global_debugger,
)  # Keep for backward compatibility @UnusedImport
from _pydevd_bundle.pydevd_net_command import NetCommand, NULL_NET_COMMAND, NULL_EXIT_COMMAND
from _pydevd_bundle.pydevd_utils import quote_smart as quote, get_non_pydevd_threads
from pydevd_file_utils import get_abs_path_real_path_and_base_from_frame
import pydevd_file_utils
from pydevd_tracing import get_exception_traceback_str
from _pydev_bundle._pydev_completer import completions_to_xml
from _pydev_bundle import pydev_log
from _pydevd_bundle.pydevd_frame_utils import FramesList
from io import StringIO


# =======================================================================================================================
# NetCommandFactory
# =======================================================================================================================
class NetCommandFactory(object):
    def __init__(self):
        self._additional_thread_id_to_thread_name = {}

    def _thread_to_xml(self, thread):
        """thread information as XML"""
        name = pydevd_xml.make_valid_xml_value(thread.name)
        cmd_text = '<thread name="%s" id="%s" />' % (quote(name), get_thread_id(thread))
        return cmd_text

    def make_error_message(self, seq, text):
        cmd = NetCommand(CMD_ERROR, seq, text)
        if DebugInfoHolder.DEBUG_TRACE_LEVEL > 2:
            pydev_log.error("Error: %s" % (text,))
        return cmd

    def make_protocol_set_message(self, seq):
        return NetCommand(CMD_SET_PROTOCOL, seq, "")

    def make_thread_created_message(self, thread):
        cmdText = "<xml>" + self._thread_to_xml(thread) + "</xml>"
        return NetCommand(CMD_THREAD_CREATE, 0, cmdText)

    def make_process_created_message(self):
        cmdText = "<process/>"
        return NetCommand(CMD_PROCESS_CREATED, 0, cmdText)

    def make_process_about_to_be_replaced_message(self):
        return NULL_NET_COMMAND

    def make_show_cython_warning_message(self):
        try:
            return NetCommand(CMD_SHOW_CYTHON_WARNING, 0, "")
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_custom_frame_created_message(self, frame_id, frame_description):
        self._additional_thread_id_to_thread_name[frame_id] = frame_description
        frame_description = pydevd_xml.make_valid_xml_value(frame_description)
        return NetCommand(CMD_THREAD_CREATE, 0, '<xml><thread name="%s" id="%s"/></xml>' % (frame_description, frame_id))

    def make_list_threads_message(self, py_db, seq):
        """returns thread listing as XML"""
        try:
            threads = get_non_pydevd_threads()
            cmd_text = ["<xml>"]
            append = cmd_text.append
            for thread in threads:
                if is_thread_alive(thread):
                    append(self._thread_to_xml(thread))

            for thread_id, thread_name in list(self._additional_thread_id_to_thread_name.items()):
                name = pydevd_xml.make_valid_xml_value(thread_name)
                append('<thread name="%s" id="%s" />' % (quote(name), thread_id))

            append("</xml>")
            return NetCommand(CMD_RETURN, seq, "".join(cmd_text))
        except:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_thread_stack_message(self, py_db, seq, thread_id, topmost_frame, fmt, must_be_suspended=False, start_frame=0, levels=0):
        """
        Returns thread stack as XML.

        :param must_be_suspended: If True and the thread is not suspended, returns None.
        """
        try:
            # If frame is None, the return is an empty frame list.
            cmd_text = ['<xml><thread id="%s">' % (thread_id,)]

            if topmost_frame is not None:
                try:
                    # : :type suspended_frames_manager: SuspendedFramesManager
                    suspended_frames_manager = py_db.suspended_frames_manager
                    frames_list = suspended_frames_manager.get_frames_list(thread_id)
                    if frames_list is None:
                        # Could not find stack of suspended frame...
                        if must_be_suspended:
                            return None
                        else:
                            frames_list = pydevd_frame_utils.create_frames_list_from_frame(topmost_frame)

                    cmd_text.append(self.make_thread_stack_str(py_db, frames_list))
                finally:
                    topmost_frame = None
            cmd_text.append("</thread></xml>")
            return NetCommand(CMD_GET_THREAD_STACK, seq, "".join(cmd_text))
        except:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_variable_changed_message(self, seq, payload):
        # notify debugger that value was changed successfully
        return NetCommand(CMD_RETURN, seq, payload)

    def make_warning_message(self, msg):
        return self.make_io_message(msg, 2)

    def make_console_message(self, msg):
        return self.make_io_message(msg, 2)

    def make_io_message(self, msg, ctx):
        """
        @param msg: the message to pass to the debug server
        @param ctx: 1 for stdio 2 for stderr
        """
        try:
            msg = pydevd_constants.as_str(msg)

            if len(msg) > MAX_IO_MSG_SIZE:
                msg = msg[0:MAX_IO_MSG_SIZE]
                msg += "..."

            msg = pydevd_xml.make_valid_xml_value(quote(msg, "/>_= "))
            return NetCommand(str(CMD_WRITE_TO_CONSOLE), 0, '<xml><io s="%s" ctx="%s"/></xml>' % (msg, ctx))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_version_message(self, seq):
        try:
            return NetCommand(CMD_VERSION, seq, VERSION_STRING)
        except:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_thread_killed_message(self, tid):
        self._additional_thread_id_to_thread_name.pop(tid, None)
        try:
            return NetCommand(CMD_THREAD_KILL, 0, str(tid))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def _iter_visible_frames_info(self, py_db, frames_list, flatten_chained=False):
        assert frames_list.__class__ == FramesList
        is_chained = False
        while True:
            for frame in frames_list:
                show_as_current_frame = frame is frames_list.current_frame
                if frame.f_code is None:
                    pydev_log.info("Frame without f_code: %s", frame)
                    continue  # IronPython sometimes does not have it!

                method_name = frame.f_code.co_name  # method name (if in method) or ? if global
                if method_name is None:
                    pydev_log.info("Frame without co_name: %s", frame)
                    continue  # IronPython sometimes does not have it!

                if is_chained:
                    method_name = "[Chained Exc: %s] %s" % (frames_list.exc_desc, method_name)

                abs_path_real_path_and_base = get_abs_path_real_path_and_base_from_frame(frame)
                if py_db.get_file_type(frame, abs_path_real_path_and_base) == py_db.PYDEV_FILE:
                    # Skip pydevd files.
                    frame = frame.f_back
                    continue

                frame_id = id(frame)
                lineno = frames_list.frame_id_to_lineno.get(frame_id, frame.f_lineno)
                line_col_info = frames_list.frame_id_to_line_col_info.get(frame_id)

                filename_in_utf8, lineno, changed = py_db.source_mapping.map_to_client(abs_path_real_path_and_base[0], lineno)
                new_filename_in_utf8, applied_mapping = pydevd_file_utils.map_file_to_client(filename_in_utf8)
                applied_mapping = applied_mapping or changed

                yield (
                    frame_id,
                    frame,
                    method_name,
                    abs_path_real_path_and_base[0],
                    new_filename_in_utf8,
                    lineno,
                    applied_mapping,
                    show_as_current_frame,
                    line_col_info,
                )

            if not flatten_chained:
                break

            frames_list = frames_list.chained_frames_list
            if frames_list is None or len(frames_list) == 0:
                break
            is_chained = True

    def make_thread_stack_str(self, py_db, frames_list):
        assert frames_list.__class__ == FramesList
        make_valid_xml_value = pydevd_xml.make_valid_xml_value
        cmd_text_list = []
        append = cmd_text_list.append

        try:
            for (
                frame_id,
                frame,
                method_name,
                _original_filename,
                filename_in_utf8,
                lineno,
                _applied_mapping,
                _show_as_current_frame,
                line_col_info,
            ) in self._iter_visible_frames_info(py_db, frames_list, flatten_chained=True):
                # print("file is ", filename_in_utf8)
                # print("line is ", lineno)

                # Note: variables are all gotten 'on-demand'.
                append('<frame id="%s" name="%s" ' % (frame_id, make_valid_xml_value(method_name)))
                append('file="%s" line="%s">' % (quote(make_valid_xml_value(filename_in_utf8), "/>_= \t"), lineno))
                append("</frame>")
        except:
            pydev_log.exception()

        return "".join(cmd_text_list)

    def make_thread_suspend_str(
        self,
        py_db,
        thread_id,
        frames_list,
        stop_reason=None,
        message=None,
        trace_suspend_type="trace",
    ):
        """
        :return tuple(str,str):
            Returns tuple(thread_suspended_str, thread_stack_str).

            i.e.:
            (
                '''
                    <xml>
                        <thread id="id" stop_reason="reason">
                            <frame id="id" name="functionName " file="file" line="line">
                            </frame>
                        </thread>
                    </xml>
                '''
                ,
                '''
                <frame id="id" name="functionName " file="file" line="line">
                </frame>
                '''
            )
        """
        assert frames_list.__class__ == FramesList
        make_valid_xml_value = pydevd_xml.make_valid_xml_value
        cmd_text_list = []
        append = cmd_text_list.append

        cmd_text_list.append("<xml>")
        if message:
            message = make_valid_xml_value(message)

        append('<thread id="%s"' % (thread_id,))
        if stop_reason is not None:
            append(' stop_reason="%s"' % (stop_reason,))
        if message is not None:
            append(' message="%s"' % (message,))
        if trace_suspend_type is not None:
            append(' suspend_type="%s"' % (trace_suspend_type,))
        append(">")
        thread_stack_str = self.make_thread_stack_str(py_db, frames_list)
        append(thread_stack_str)
        append("</thread></xml>")

        return "".join(cmd_text_list), thread_stack_str

    def make_thread_suspend_message(self, py_db, thread_id, frames_list, stop_reason, message, trace_suspend_type, thread, additional_info):
        try:
            thread_suspend_str, thread_stack_str = self.make_thread_suspend_str(
                py_db, thread_id, frames_list, stop_reason, message, trace_suspend_type
            )
            cmd = NetCommand(CMD_THREAD_SUSPEND, 0, thread_suspend_str)
            cmd.thread_stack_str = thread_stack_str
            cmd.thread_suspend_str = thread_suspend_str
            return cmd
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_thread_suspend_single_notification(self, py_db, thread_id, thread, stop_reason):
        try:
            return NetCommand(CMD_THREAD_SUSPEND_SINGLE_NOTIFICATION, 0, json.dumps({"thread_id": thread_id, "stop_reason": stop_reason}))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_thread_resume_single_notification(self, thread_id):
        try:
            return NetCommand(CMD_THREAD_RESUME_SINGLE_NOTIFICATION, 0, json.dumps({"thread_id": thread_id}))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_thread_run_message(self, py_db, thread_id, reason):
        try:
            return NetCommand(CMD_THREAD_RUN, 0, "%s\t%s" % (thread_id, reason))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_get_variable_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_VARIABLE, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_array_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_ARRAY, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_description_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_DESCRIPTION, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_frame_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_FRAME, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_evaluate_expression_message(self, seq, payload):
        try:
            return NetCommand(CMD_EVALUATE_EXPRESSION, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_completions_message(self, seq, completions, qualifier, start):
        try:
            payload = completions_to_xml(completions)
            return NetCommand(CMD_GET_COMPLETIONS, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_file_contents(self, seq, payload):
        try:
            return NetCommand(CMD_GET_FILE_CONTENTS, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_reloaded_code_message(self, seq, reloaded_ok):
        try:
            return NetCommand(CMD_RELOAD_CODE, seq, '<xml><reloaded ok="%s"></reloaded></xml>' % reloaded_ok)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_send_breakpoint_exception_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_BREAKPOINT_EXCEPTION, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def _make_send_curr_exception_trace_str(self, py_db, thread_id, exc_type, exc_desc, trace_obj):
        frames_list = pydevd_frame_utils.create_frames_list_from_traceback(trace_obj, None, exc_type, exc_desc)

        exc_type = pydevd_xml.make_valid_xml_value(str(exc_type)).replace("\t", "  ") or "exception: type unknown"
        exc_desc = pydevd_xml.make_valid_xml_value(str(exc_desc)).replace("\t", "  ") or "exception: no description"

        thread_suspend_str, thread_stack_str = self.make_thread_suspend_str(
            py_db, thread_id, frames_list, CMD_SEND_CURR_EXCEPTION_TRACE, ""
        )
        return exc_type, exc_desc, thread_suspend_str, thread_stack_str

    def make_send_curr_exception_trace_message(self, py_db, seq, thread_id, curr_frame_id, exc_type, exc_desc, trace_obj):
        try:
            exc_type, exc_desc, thread_suspend_str, _thread_stack_str = self._make_send_curr_exception_trace_str(
                py_db, thread_id, exc_type, exc_desc, trace_obj
            )
            payload = str(curr_frame_id) + "\t" + exc_type + "\t" + exc_desc + "\t" + thread_suspend_str
            return NetCommand(CMD_SEND_CURR_EXCEPTION_TRACE, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_exception_details_message(self, py_db, seq, thread_id, topmost_frame):
        """Returns exception details as XML"""
        try:
            # If the debugger is not suspended, just return the thread and its id.
            cmd_text = ['<xml><thread id="%s" ' % (thread_id,)]

            if topmost_frame is not None:
                try:
                    frame = topmost_frame
                    topmost_frame = None
                    while frame is not None:
                        if frame.f_code.co_name == "do_wait_suspend" and frame.f_code.co_filename.endswith("pydevd.py"):
                            arg = frame.f_locals.get("arg", None)
                            if arg is not None:
                                exc_type, exc_desc, _thread_suspend_str, thread_stack_str = self._make_send_curr_exception_trace_str(
                                    py_db, thread_id, *arg
                                )
                                cmd_text.append('exc_type="%s" ' % (exc_type,))
                                cmd_text.append('exc_desc="%s" ' % (exc_desc,))
                                cmd_text.append(">")
                                cmd_text.append(thread_stack_str)
                                break
                        frame = frame.f_back
                    else:
                        cmd_text.append(">")
                finally:
                    frame = None
            cmd_text.append("</thread></xml>")
            return NetCommand(CMD_GET_EXCEPTION_DETAILS, seq, "".join(cmd_text))
        except:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_send_curr_exception_trace_proceeded_message(self, seq, thread_id):
        try:
            return NetCommand(CMD_SEND_CURR_EXCEPTION_TRACE_PROCEEDED, 0, str(thread_id))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_send_console_message(self, seq, payload):
        try:
            return NetCommand(CMD_EVALUATE_CONSOLE_EXPRESSION, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_custom_operation_message(self, seq, payload):
        try:
            return NetCommand(CMD_RUN_CUSTOM_OPERATION, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_load_source_message(self, seq, source):
        return NetCommand(CMD_LOAD_SOURCE, seq, source)

    def make_load_source_from_frame_id_message(self, seq, source):
        return NetCommand(CMD_LOAD_SOURCE_FROM_FRAME_ID, seq, source)

    def make_show_console_message(self, py_db, thread_id, frame):
        try:
            frames_list = pydevd_frame_utils.create_frames_list_from_frame(frame)
            thread_suspended_str, _thread_stack_str = self.make_thread_suspend_str(py_db, thread_id, frames_list, CMD_SHOW_CONSOLE, "")
            return NetCommand(CMD_SHOW_CONSOLE, 0, thread_suspended_str)
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_input_requested_message(self, started):
        try:
            return NetCommand(CMD_INPUT_REQUESTED, 0, str(started))
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_set_next_stmnt_status_message(self, seq, is_success, exception_msg):
        try:
            message = str(is_success) + "\t" + exception_msg
            return NetCommand(CMD_SET_NEXT_STATEMENT, int(seq), message)
        except:
            return self.make_error_message(0, get_exception_traceback_str())

    def make_load_full_value_message(self, seq, payload):
        try:
            return NetCommand(CMD_LOAD_FULL_VALUE, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_get_next_statement_targets_message(self, seq, payload):
        try:
            return NetCommand(CMD_GET_NEXT_STATEMENT_TARGETS, seq, payload)
        except Exception:
            return self.make_error_message(seq, get_exception_traceback_str())

    def make_skipped_step_in_because_of_filters(self, py_db, frame):
        return NULL_NET_COMMAND  # Not a part of the xml protocol

    def make_evaluation_timeout_msg(self, py_db, expression, thread):
        msg = """pydevd: Evaluating: %s did not finish after %.2f seconds.
This may mean a number of things:
- This evaluation is really slow and this is expected.
    In this case it's possible to silence this error by raising the timeout, setting the
    PYDEVD_WARN_EVALUATION_TIMEOUT environment variable to a bigger value.

- The evaluation may need other threads running while it's running:
    In this case, you may need to manually let other paused threads continue.

    Alternatively, it's also possible to skip breaking on a particular thread by setting a
    `pydev_do_not_trace = True` attribute in the related threading.Thread instance
    (if some thread should always be running and no breakpoints are expected to be hit in it).

- The evaluation is deadlocked:
    In this case you may set the PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT
    environment variable to true so that a thread dump is shown along with this message and
    optionally, set the PYDEVD_INTERRUPT_THREAD_TIMEOUT to some value so that the debugger
    tries to interrupt the evaluation (if possible) when this happens.
""" % (expression, pydevd_constants.PYDEVD_WARN_EVALUATION_TIMEOUT)

        if pydevd_constants.PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT:
            stream = StringIO()
            pydevd_utils.dump_threads(stream, show_pydevd_threads=False)
            msg += "\n\n%s\n" % stream.getvalue()
        return self.make_warning_message(msg)

    def make_exit_command(self, py_db):
        return NULL_EXIT_COMMAND

# === NexusCore/openenv\Lib\site-packages\jedi\inference\base_value.py ===
"""
Values are the "values" that Python would return. However Values are at the
same time also the "values" that a user is currently sitting in.

A ValueSet is typically used to specify the return of a function or any other
static analysis operation. In jedi there are always multiple returns and not
just one.
"""
from functools import reduce
from operator import add
from itertools import zip_longest

from parso.python.tree import Name

from jedi import debug
from jedi.parser_utils import clean_scope_docstring
from jedi.inference.helpers import SimpleGetItemNotFound
from jedi.inference.utils import safe_property
from jedi.inference.cache import inference_state_as_method_param_cache
from jedi.cache import memoize_method

sentinel = object()


class HasNoContext(Exception):
    pass


class HelperValueMixin:
    def get_root_context(self):
        value = self
        if value.parent_context is None:
            return value.as_context()

        while True:
            if value.parent_context is None:
                return value
            value = value.parent_context

    def execute(self, arguments):
        return self.inference_state.execute(self, arguments=arguments)

    def execute_with_values(self, *value_list):
        from jedi.inference.arguments import ValuesArguments
        arguments = ValuesArguments([ValueSet([value]) for value in value_list])
        return self.inference_state.execute(self, arguments)

    def execute_annotation(self):
        return self.execute_with_values()

    def gather_annotation_classes(self):
        return ValueSet([self])

    def merge_types_of_iterate(self, contextualized_node=None, is_async=False):
        return ValueSet.from_sets(
            lazy_value.infer()
            for lazy_value in self.iterate(contextualized_node, is_async)
        )

    def _get_value_filters(self, name_or_str):
        origin_scope = name_or_str if isinstance(name_or_str, Name) else None
        yield from self.get_filters(origin_scope=origin_scope)
        # This covers the case where a stub files are incomplete.
        if self.is_stub():
            from jedi.inference.gradual.conversion import convert_values
            for c in convert_values(ValueSet({self})):
                yield from c.get_filters()

    def goto(self, name_or_str, name_context=None, analysis_errors=True):
        from jedi.inference import finder
        filters = self._get_value_filters(name_or_str)
        names = finder.filter_name(filters, name_or_str)
        debug.dbg('context.goto %s in (%s): %s', name_or_str, self, names)
        return names

    def py__getattribute__(self, name_or_str, name_context=None, position=None,
                           analysis_errors=True):
        """
        :param position: Position of the last statement -> tuple of line, column
        """
        if name_context is None:
            name_context = self
        names = self.goto(name_or_str, name_context, analysis_errors)
        values = ValueSet.from_sets(name.infer() for name in names)
        if not values:
            n = name_or_str.value if isinstance(name_or_str, Name) else name_or_str
            values = self.py__getattribute__alternatives(n)

        if not names and not values and analysis_errors:
            if isinstance(name_or_str, Name):
                from jedi.inference import analysis
                analysis.add_attribute_error(
                    name_context, self, name_or_str)
        debug.dbg('context.names_to_types: %s -> %s', names, values)
        return values

    def py__await__(self):
        await_value_set = self.py__getattribute__("__await__")
        if not await_value_set:
            debug.warning('Tried to run __await__ on value %s', self)
        return await_value_set.execute_with_values()

    def py__name__(self):
        return self.name.string_name

    def iterate(self, contextualized_node=None, is_async=False):
        debug.dbg('iterate %s', self)
        if is_async:
            from jedi.inference.lazy_value import LazyKnownValues
            # TODO if no __aiter__ values are there, error should be:
            # TypeError: 'async for' requires an object with __aiter__ method, got int
            return iter([
                LazyKnownValues(
                    self.py__getattribute__('__aiter__').execute_with_values()
                        .py__getattribute__('__anext__').execute_with_values()
                        .py__getattribute__('__await__').execute_with_values()
                        .py__stop_iteration_returns()
                )  # noqa: E124
            ])
        return self.py__iter__(contextualized_node)

    def is_sub_class_of(self, class_value):
        with debug.increase_indent_cm('subclass matching of %s <=> %s' % (self, class_value),
                                      color='BLUE'):
            for cls in self.py__mro__():
                if cls.is_same_class(class_value):
                    debug.dbg('matched subclass True', color='BLUE')
                    return True
            debug.dbg('matched subclass False', color='BLUE')
            return False

    def is_same_class(self, class2):
        # Class matching should prefer comparisons that are not this function.
        if type(class2).is_same_class != HelperValueMixin.is_same_class:
            return class2.is_same_class(self)
        return self == class2

    @memoize_method
    def as_context(self, *args, **kwargs):
        return self._as_context(*args, **kwargs)


class Value(HelperValueMixin):
    """
    To be implemented by subclasses.
    """
    tree_node = None
    # Possible values: None, tuple, list, dict and set. Here to deal with these
    # very important containers.
    array_type = None
    api_type = 'not_defined_please_report_bug'

    def __init__(self, inference_state, parent_context=None):
        self.inference_state = inference_state
        self.parent_context = parent_context

    def py__getitem__(self, index_value_set, contextualized_node):
        from jedi.inference import analysis
        # TODO this value is probably not right.
        analysis.add(
            contextualized_node.context,
            'type-error-not-subscriptable',
            contextualized_node.node,
            message="TypeError: '%s' object is not subscriptable" % self
        )
        return NO_VALUES

    def py__simple_getitem__(self, index):
        raise SimpleGetItemNotFound

    def py__iter__(self, contextualized_node=None):
        if contextualized_node is not None:
            from jedi.inference import analysis
            analysis.add(
                contextualized_node.context,
                'type-error-not-iterable',
                contextualized_node.node,
                message="TypeError: '%s' object is not iterable" % self)
        return iter([])

    def py__next__(self, contextualized_node=None):
        return self.py__iter__(contextualized_node)

    def get_signatures(self):
        return []

    def is_class(self):
        return False

    def is_class_mixin(self):
        return False

    def is_instance(self):
        return False

    def is_function(self):
        return False

    def is_module(self):
        return False

    def is_namespace(self):
        return False

    def is_compiled(self):
        return False

    def is_bound_method(self):
        return False

    def is_builtins_module(self):
        return False

    def py__bool__(self):
        """
        Since Wrapper is a super class for classes, functions and modules,
        the return value will always be true.
        """
        return True

    def py__doc__(self):
        try:
            self.tree_node.get_doc_node
        except AttributeError:
            return ''
        else:
            return clean_scope_docstring(self.tree_node)

    def get_safe_value(self, default=sentinel):
        if default is sentinel:
            raise ValueError("There exists no safe value for value %s" % self)
        return default

    def execute_operation(self, other, operator):
        debug.warning("%s not possible between %s and %s", operator, self, other)
        return NO_VALUES

    def py__call__(self, arguments):
        debug.warning("no execution possible %s", self)
        return NO_VALUES

    def py__stop_iteration_returns(self):
        debug.warning("Not possible to return the stop iterations of %s", self)
        return NO_VALUES

    def py__getattribute__alternatives(self, name_or_str):
        """
        For now a way to add values in cases like __getattr__.
        """
        return NO_VALUES

    def py__get__(self, instance, class_value):
        debug.warning("No __get__ defined on %s", self)
        return ValueSet([self])

    def py__get__on_class(self, calling_instance, instance, class_value):
        return NotImplemented

    def get_qualified_names(self):
        # Returns Optional[Tuple[str, ...]]
        return None

    def is_stub(self):
        # The root value knows if it's a stub or not.
        return self.parent_context.is_stub()

    def _as_context(self):
        raise HasNoContext

    @property
    def name(self):
        raise NotImplementedError

    def get_type_hint(self, add_class_info=True):
        return None

    def infer_type_vars(self, value_set):
        """
        When the current instance represents a type annotation, this method
        tries to find information about undefined type vars and returns a dict
        from type var name to value set.

        This is for example important to understand what `iter([1])` returns.
        According to typeshed, `iter` returns an `Iterator[_T]`:

            def iter(iterable: Iterable[_T]) -> Iterator[_T]: ...

        This functions would generate `int` for `_T` in this case, because it
        unpacks the `Iterable`.

        Parameters
        ----------

        `self`: represents the annotation of the current parameter to infer the
            value for. In the above example, this would initially be the
            `Iterable[_T]` of the `iterable` parameter and then, when recursing,
            just the `_T` generic parameter.

        `value_set`: represents the actual argument passed to the parameter
            we're inferred for, or (for recursive calls) their types. In the
            above example this would first be the representation of the list
            `[1]` and then, when recursing, just of `1`.
        """
        return {}


def iterate_values(values, contextualized_node=None, is_async=False):
    """
    Calls `iterate`, on all values but ignores the ordering and just returns
    all values that the iterate functions yield.
    """
    return ValueSet.from_sets(
        lazy_value.infer()
        for lazy_value in values.iterate(contextualized_node, is_async=is_async)
    )


class _ValueWrapperBase(HelperValueMixin):
    @safe_property
    def name(self):
        from jedi.inference.names import ValueName
        wrapped_name = self._wrapped_value.name
        if wrapped_name.tree_name is not None:
            return ValueName(self, wrapped_name.tree_name)
        else:
            from jedi.inference.compiled import CompiledValueName
            return CompiledValueName(self, wrapped_name.string_name)

    @classmethod
    @inference_state_as_method_param_cache()
    def create_cached(cls, inference_state, *args, **kwargs):
        return cls(*args, **kwargs)

    def __getattr__(self, name):
        assert name != '_wrapped_value', 'Problem with _get_wrapped_value'
        return getattr(self._wrapped_value, name)


class LazyValueWrapper(_ValueWrapperBase):
    @safe_property
    @memoize_method
    def _wrapped_value(self):
        with debug.increase_indent_cm('Resolve lazy value wrapper'):
            return self._get_wrapped_value()

    def __repr__(self):
        return '<%s>' % (self.__class__.__name__)

    def _get_wrapped_value(self):
        raise NotImplementedError


class ValueWrapper(_ValueWrapperBase):
    def __init__(self, wrapped_value):
        self._wrapped_value = wrapped_value

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._wrapped_value)


class TreeValue(Value):
    def __init__(self, inference_state, parent_context, tree_node):
        super().__init__(inference_state, parent_context)
        self.tree_node = tree_node

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.tree_node)


class ContextualizedNode:
    def __init__(self, context, node):
        self.context = context
        self.node = node

    def get_root_context(self):
        return self.context.get_root_context()

    def infer(self):
        return self.context.infer_node(self.node)

    def __repr__(self):
        return '<%s: %s in %s>' % (self.__class__.__name__, self.node, self.context)


def _getitem(value, index_values, contextualized_node):
    # The actual getitem call.
    result = NO_VALUES
    unused_values = set()
    for index_value in index_values:
        index = index_value.get_safe_value(default=None)
        if type(index) in (float, int, str, slice, bytes):
            try:
                result |= value.py__simple_getitem__(index)
                continue
            except SimpleGetItemNotFound:
                pass

        unused_values.add(index_value)

    # The index was somehow not good enough or simply a wrong type.
    # Therefore we now iterate through all the values and just take
    # all results.
    if unused_values or not index_values:
        result |= value.py__getitem__(
            ValueSet(unused_values),
            contextualized_node
        )
    debug.dbg('py__getitem__ result: %s', result)
    return result


class ValueSet:
    def __init__(self, iterable):
        self._set = frozenset(iterable)
        for value in iterable:
            assert not isinstance(value, ValueSet)

    @classmethod
    def _from_frozen_set(cls, frozenset_):
        self = cls.__new__(cls)
        self._set = frozenset_
        return self

    @classmethod
    def from_sets(cls, sets):
        """
        Used to work with an iterable of set.
        """
        aggregated = set()
        for set_ in sets:
            if isinstance(set_, ValueSet):
                aggregated |= set_._set
            else:
                aggregated |= frozenset(set_)
        return cls._from_frozen_set(frozenset(aggregated))

    def __or__(self, other):
        return self._from_frozen_set(self._set | other._set)

    def __and__(self, other):
        return self._from_frozen_set(self._set & other._set)

    def __iter__(self):
        return iter(self._set)

    def __bool__(self):
        return bool(self._set)

    def __len__(self):
        return len(self._set)

    def __repr__(self):
        return 'S{%s}' % (', '.join(str(s) for s in self._set))

    def filter(self, filter_func):
        return self.__class__(filter(filter_func, self._set))

    def __getattr__(self, name):
        def mapper(*args, **kwargs):
            return self.from_sets(
                getattr(value, name)(*args, **kwargs)
                for value in self._set
            )
        return mapper

    def __eq__(self, other):
        return self._set == other._set

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._set)

    def py__class__(self):
        return ValueSet(c.py__class__() for c in self._set)

    def iterate(self, contextualized_node=None, is_async=False):
        from jedi.inference.lazy_value import get_merged_lazy_value
        type_iters = [c.iterate(contextualized_node, is_async=is_async) for c in self._set]
        for lazy_values in zip_longest(*type_iters):
            yield get_merged_lazy_value(
                [l for l in lazy_values if l is not None]
            )

    def execute(self, arguments):
        return ValueSet.from_sets(c.inference_state.execute(c, arguments) for c in self._set)

    def execute_with_values(self, *args, **kwargs):
        return ValueSet.from_sets(c.execute_with_values(*args, **kwargs) for c in self._set)

    def goto(self, *args, **kwargs):
        return reduce(add, [c.goto(*args, **kwargs) for c in self._set], [])

    def py__getattribute__(self, *args, **kwargs):
        return ValueSet.from_sets(c.py__getattribute__(*args, **kwargs) for c in self._set)

    def get_item(self, *args, **kwargs):
        return ValueSet.from_sets(_getitem(c, *args, **kwargs) for c in self._set)

    def try_merge(self, function_name):
        value_set = self.__class__([])
        for c in self._set:
            try:
                method = getattr(c, function_name)
            except AttributeError:
                pass
            else:
                value_set |= method()
        return value_set

    def gather_annotation_classes(self):
        return ValueSet.from_sets([c.gather_annotation_classes() for c in self._set])

    def get_signatures(self):
        return [sig for c in self._set for sig in c.get_signatures()]

    def get_type_hint(self, add_class_info=True):
        t = [v.get_type_hint(add_class_info=add_class_info) for v in self._set]
        type_hints = sorted(filter(None, t))
        if len(type_hints) == 1:
            return type_hints[0]

        optional = 'None' in type_hints
        if optional:
            type_hints.remove('None')

        if len(type_hints) == 0:
            return None
        elif len(type_hints) == 1:
            s = type_hints[0]
        else:
            s = 'Union[%s]' % ', '.join(type_hints)
        if optional:
            s = 'Optional[%s]' % s
        return s

    def infer_type_vars(self, value_set):
        # Circular
        from jedi.inference.gradual.annotation import merge_type_var_dicts

        type_var_dict = {}
        for value in self._set:
            merge_type_var_dicts(
                type_var_dict,
                value.infer_type_vars(value_set),
            )
        return type_var_dict


NO_VALUES = ValueSet([])


def iterator_to_value_set(func):
    def wrapper(*args, **kwargs):
        return ValueSet(func(*args, **kwargs))

    return wrapper

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_css_builtins.py ===
"""
    pygments.lexers._css_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file is autogenerated by scripts/get_css_properties.py

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

_css_properties = (
    '-webkit-line-clamp',
    'accent-color',
    'align-content',
    'align-items',
    'align-self',
    'alignment-baseline',
    'all',
    'animation',
    'animation-delay',
    'animation-direction',
    'animation-duration',
    'animation-fill-mode',
    'animation-iteration-count',
    'animation-name',
    'animation-play-state',
    'animation-timing-function',
    'appearance',
    'aspect-ratio',
    'azimuth',
    'backface-visibility',
    'background',
    'background-attachment',
    'background-blend-mode',
    'background-clip',
    'background-color',
    'background-image',
    'background-origin',
    'background-position',
    'background-repeat',
    'background-size',
    'baseline-shift',
    'baseline-source',
    'block-ellipsis',
    'block-size',
    'block-step',
    'block-step-align',
    'block-step-insert',
    'block-step-round',
    'block-step-size',
    'bookmark-label',
    'bookmark-level',
    'bookmark-state',
    'border',
    'border-block',
    'border-block-color',
    'border-block-end',
    'border-block-end-color',
    'border-block-end-style',
    'border-block-end-width',
    'border-block-start',
    'border-block-start-color',
    'border-block-start-style',
    'border-block-start-width',
    'border-block-style',
    'border-block-width',
    'border-bottom',
    'border-bottom-color',
    'border-bottom-left-radius',
    'border-bottom-right-radius',
    'border-bottom-style',
    'border-bottom-width',
    'border-boundary',
    'border-collapse',
    'border-color',
    'border-end-end-radius',
    'border-end-start-radius',
    'border-image',
    'border-image-outset',
    'border-image-repeat',
    'border-image-slice',
    'border-image-source',
    'border-image-width',
    'border-inline',
    'border-inline-color',
    'border-inline-end',
    'border-inline-end-color',
    'border-inline-end-style',
    'border-inline-end-width',
    'border-inline-start',
    'border-inline-start-color',
    'border-inline-start-style',
    'border-inline-start-width',
    'border-inline-style',
    'border-inline-width',
    'border-left',
    'border-left-color',
    'border-left-style',
    'border-left-width',
    'border-radius',
    'border-right',
    'border-right-color',
    'border-right-style',
    'border-right-width',
    'border-spacing',
    'border-start-end-radius',
    'border-start-start-radius',
    'border-style',
    'border-top',
    'border-top-color',
    'border-top-left-radius',
    'border-top-right-radius',
    'border-top-style',
    'border-top-width',
    'border-width',
    'bottom',
    'box-decoration-break',
    'box-shadow',
    'box-sizing',
    'box-snap',
    'break-after',
    'break-before',
    'break-inside',
    'caption-side',
    'caret',
    'caret-color',
    'caret-shape',
    'chains',
    'clear',
    'clip',
    'clip-path',
    'clip-rule',
    'color',
    'color-adjust',
    'color-interpolation-filters',
    'color-scheme',
    'column-count',
    'column-fill',
    'column-gap',
    'column-rule',
    'column-rule-color',
    'column-rule-style',
    'column-rule-width',
    'column-span',
    'column-width',
    'columns',
    'contain',
    'contain-intrinsic-block-size',
    'contain-intrinsic-height',
    'contain-intrinsic-inline-size',
    'contain-intrinsic-size',
    'contain-intrinsic-width',
    'container',
    'container-name',
    'container-type',
    'content',
    'content-visibility',
    'continue',
    'counter-increment',
    'counter-reset',
    'counter-set',
    'cue',
    'cue-after',
    'cue-before',
    'cursor',
    'direction',
    'display',
    'dominant-baseline',
    'elevation',
    'empty-cells',
    'fill',
    'fill-break',
    'fill-color',
    'fill-image',
    'fill-opacity',
    'fill-origin',
    'fill-position',
    'fill-repeat',
    'fill-rule',
    'fill-size',
    'filter',
    'flex',
    'flex-basis',
    'flex-direction',
    'flex-flow',
    'flex-grow',
    'flex-shrink',
    'flex-wrap',
    'float',
    'float-defer',
    'float-offset',
    'float-reference',
    'flood-color',
    'flood-opacity',
    'flow',
    'flow-from',
    'flow-into',
    'font',
    'font-family',
    'font-feature-settings',
    'font-kerning',
    'font-language-override',
    'font-optical-sizing',
    'font-palette',
    'font-size',
    'font-size-adjust',
    'font-stretch',
    'font-style',
    'font-synthesis',
    'font-synthesis-small-caps',
    'font-synthesis-style',
    'font-synthesis-weight',
    'font-variant',
    'font-variant-alternates',
    'font-variant-caps',
    'font-variant-east-asian',
    'font-variant-emoji',
    'font-variant-ligatures',
    'font-variant-numeric',
    'font-variant-position',
    'font-variation-settings',
    'font-weight',
    'footnote-display',
    'footnote-policy',
    'forced-color-adjust',
    'gap',
    'glyph-orientation-vertical',
    'grid',
    'grid-area',
    'grid-auto-columns',
    'grid-auto-flow',
    'grid-auto-rows',
    'grid-column',
    'grid-column-end',
    'grid-column-start',
    'grid-row',
    'grid-row-end',
    'grid-row-start',
    'grid-template',
    'grid-template-areas',
    'grid-template-columns',
    'grid-template-rows',
    'hanging-punctuation',
    'height',
    'hyphenate-character',
    'hyphenate-limit-chars',
    'hyphenate-limit-last',
    'hyphenate-limit-lines',
    'hyphenate-limit-zone',
    'hyphens',
    'image-orientation',
    'image-rendering',
    'image-resolution',
    'initial-letter',
    'initial-letter-align',
    'initial-letter-wrap',
    'inline-size',
    'inline-sizing',
    'input-security',
    'inset',
    'inset-block',
    'inset-block-end',
    'inset-block-start',
    'inset-inline',
    'inset-inline-end',
    'inset-inline-start',
    'isolation',
    'justify-content',
    'justify-items',
    'justify-self',
    'leading-trim',
    'left',
    'letter-spacing',
    'lighting-color',
    'line-break',
    'line-clamp',
    'line-grid',
    'line-height',
    'line-height-step',
    'line-padding',
    'line-snap',
    'list-style',
    'list-style-image',
    'list-style-position',
    'list-style-type',
    'margin',
    'margin-block',
    'margin-block-end',
    'margin-block-start',
    'margin-bottom',
    'margin-break',
    'margin-inline',
    'margin-inline-end',
    'margin-inline-start',
    'margin-left',
    'margin-right',
    'margin-top',
    'margin-trim',
    'marker',
    'marker-end',
    'marker-knockout-left',
    'marker-knockout-right',
    'marker-mid',
    'marker-pattern',
    'marker-segment',
    'marker-side',
    'marker-start',
    'mask',
    'mask-border',
    'mask-border-mode',
    'mask-border-outset',
    'mask-border-repeat',
    'mask-border-slice',
    'mask-border-source',
    'mask-border-width',
    'mask-clip',
    'mask-composite',
    'mask-image',
    'mask-mode',
    'mask-origin',
    'mask-position',
    'mask-repeat',
    'mask-size',
    'mask-type',
    'max-block-size',
    'max-height',
    'max-inline-size',
    'max-lines',
    'max-width',
    'min-block-size',
    'min-height',
    'min-inline-size',
    'min-intrinsic-sizing',
    'min-width',
    'mix-blend-mode',
    'nav-down',
    'nav-left',
    'nav-right',
    'nav-up',
    'object-fit',
    'object-overflow',
    'object-position',
    'object-view-box',
    'offset',
    'offset-anchor',
    'offset-distance',
    'offset-path',
    'offset-position',
    'offset-rotate',
    'opacity',
    'order',
    'orphans',
    'outline',
    'outline-color',
    'outline-offset',
    'outline-style',
    'outline-width',
    'overflow',
    'overflow-anchor',
    'overflow-block',
    'overflow-clip-margin',
    'overflow-inline',
    'overflow-wrap',
    'overflow-x',
    'overflow-y',
    'overscroll-behavior',
    'overscroll-behavior-block',
    'overscroll-behavior-inline',
    'overscroll-behavior-x',
    'overscroll-behavior-y',
    'padding',
    'padding-block',
    'padding-block-end',
    'padding-block-start',
    'padding-bottom',
    'padding-inline',
    'padding-inline-end',
    'padding-inline-start',
    'padding-left',
    'padding-right',
    'padding-top',
    'page',
    'page-break-after',
    'page-break-before',
    'page-break-inside',
    'pause',
    'pause-after',
    'pause-before',
    'perspective',
    'perspective-origin',
    'pitch',
    'pitch-range',
    'place-content',
    'place-items',
    'place-self',
    'play-during',
    'pointer-events',
    'position',
    'print-color-adjust',
    'property-name',
    'quotes',
    'region-fragment',
    'resize',
    'rest',
    'rest-after',
    'rest-before',
    'richness',
    'right',
    'rotate',
    'row-gap',
    'ruby-align',
    'ruby-merge',
    'ruby-overhang',
    'ruby-position',
    'running',
    'scale',
    'scroll-behavior',
    'scroll-margin',
    'scroll-margin-block',
    'scroll-margin-block-end',
    'scroll-margin-block-start',
    'scroll-margin-bottom',
    'scroll-margin-inline',
    'scroll-margin-inline-end',
    'scroll-margin-inline-start',
    'scroll-margin-left',
    'scroll-margin-right',
    'scroll-margin-top',
    'scroll-padding',
    'scroll-padding-block',
    'scroll-padding-block-end',
    'scroll-padding-block-start',
    'scroll-padding-bottom',
    'scroll-padding-inline',
    'scroll-padding-inline-end',
    'scroll-padding-inline-start',
    'scroll-padding-left',
    'scroll-padding-right',
    'scroll-padding-top',
    'scroll-snap-align',
    'scroll-snap-stop',
    'scroll-snap-type',
    'scrollbar-color',
    'scrollbar-gutter',
    'scrollbar-width',
    'shape-image-threshold',
    'shape-inside',
    'shape-margin',
    'shape-outside',
    'spatial-navigation-action',
    'spatial-navigation-contain',
    'spatial-navigation-function',
    'speak',
    'speak-as',
    'speak-header',
    'speak-numeral',
    'speak-punctuation',
    'speech-rate',
    'stress',
    'string-set',
    'stroke',
    'stroke-align',
    'stroke-alignment',
    'stroke-break',
    'stroke-color',
    'stroke-dash-corner',
    'stroke-dash-justify',
    'stroke-dashadjust',
    'stroke-dasharray',
    'stroke-dashcorner',
    'stroke-dashoffset',
    'stroke-image',
    'stroke-linecap',
    'stroke-linejoin',
    'stroke-miterlimit',
    'stroke-opacity',
    'stroke-origin',
    'stroke-position',
    'stroke-repeat',
    'stroke-size',
    'stroke-width',
    'tab-size',
    'table-layout',
    'text-align',
    'text-align-all',
    'text-align-last',
    'text-combine-upright',
    'text-decoration',
    'text-decoration-color',
    'text-decoration-line',
    'text-decoration-skip',
    'text-decoration-skip-box',
    'text-decoration-skip-ink',
    'text-decoration-skip-inset',
    'text-decoration-skip-self',
    'text-decoration-skip-spaces',
    'text-decoration-style',
    'text-decoration-thickness',
    'text-edge',
    'text-emphasis',
    'text-emphasis-color',
    'text-emphasis-position',
    'text-emphasis-skip',
    'text-emphasis-style',
    'text-group-align',
    'text-indent',
    'text-justify',
    'text-orientation',
    'text-overflow',
    'text-shadow',
    'text-space-collapse',
    'text-space-trim',
    'text-spacing',
    'text-transform',
    'text-underline-offset',
    'text-underline-position',
    'text-wrap',
    'top',
    'transform',
    'transform-box',
    'transform-origin',
    'transform-style',
    'transition',
    'transition-delay',
    'transition-duration',
    'transition-property',
    'transition-timing-function',
    'translate',
    'unicode-bidi',
    'user-select',
    'vertical-align',
    'visibility',
    'voice-balance',
    'voice-duration',
    'voice-family',
    'voice-pitch',
    'voice-range',
    'voice-rate',
    'voice-stress',
    'voice-volume',
    'volume',
    'white-space',
    'widows',
    'width',
    'will-change',
    'word-boundary-detection',
    'word-boundary-expansion',
    'word-break',
    'word-spacing',
    'word-wrap',
    'wrap-after',
    'wrap-before',
    'wrap-flow',
    'wrap-inside',
    'wrap-through',
    'writing-mode',
    'z-index',
)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\preload.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Preload (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


class RuleSetId(str):
    '''
    Unique id
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RuleSetId:
        return cls(json)

    def __repr__(self):
        return 'RuleSetId({})'.format(super().__repr__())


@dataclass
class RuleSet:
    '''
    Corresponds to SpeculationRuleSet
    '''
    id_: RuleSetId

    #: Identifies a document which the rule set is associated with.
    loader_id: network.LoaderId

    #: Source text of JSON representing the rule set. If it comes from
    #: ``script`` tag, it is the textContent of the node. Note that it is
    #: a JSON for valid case.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html
    #: - https://github.com/WICG/nav-speculation/blob/main/triggers.md
    source_text: str

    #: A speculation rule set is either added through an inline
    #: ``script`` tag or through an external resource via the
    #: 'Speculation-Rules' HTTP header. For the first case, we include
    #: the BackendNodeId of the relevant ``script`` tag. For the second
    #: case, we include the external URL where the rule set was loaded
    #: from, and also RequestId if Network domain is enabled.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-script
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-header
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    url: typing.Optional[str] = None

    request_id: typing.Optional[network.RequestId] = None

    #: Error information
    #: ``errorMessage`` is null iff ``errorType`` is null.
    error_type: typing.Optional[RuleSetErrorType] = None

    #: TODO(https://crbug.com/1425354): Replace this property with structured error.
    error_message: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['loaderId'] = self.loader_id.to_json()
        json['sourceText'] = self.source_text
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        if self.error_type is not None:
            json['errorType'] = self.error_type.to_json()
        if self.error_message is not None:
            json['errorMessage'] = self.error_message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=RuleSetId.from_json(json['id']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            source_text=str(json['sourceText']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
            error_type=RuleSetErrorType.from_json(json['errorType']) if 'errorType' in json else None,
            error_message=str(json['errorMessage']) if 'errorMessage' in json else None,
        )


class RuleSetErrorType(enum.Enum):
    SOURCE_IS_NOT_JSON_OBJECT = "SourceIsNotJsonObject"
    INVALID_RULES_SKIPPED = "InvalidRulesSkipped"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationAction(enum.Enum):
    '''
    The type of preloading attempted. It corresponds to
    mojom::SpeculationAction (although PrefetchWithSubresources is omitted as it
    isn't being used by clients).
    '''
    PREFETCH = "Prefetch"
    PRERENDER = "Prerender"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationTargetHint(enum.Enum):
    '''
    Corresponds to mojom::SpeculationTargetHint.
    See https://github.com/WICG/nav-speculation/blob/main/triggers.md#window-name-targeting-hints
    '''
    BLANK = "Blank"
    SELF = "Self"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PreloadingAttemptKey:
    '''
    A key that identifies a preloading attempt.

    The url used is the url specified by the trigger (i.e. the initial URL), and
    not the final url that is navigated to. For example, prerendering allows
    same-origin main frame navigations during the attempt, but the attempt is
    still keyed with the initial URL.
    '''
    loader_id: network.LoaderId

    action: SpeculationAction

    url: str

    target_hint: typing.Optional[SpeculationTargetHint] = None

    def to_json(self):
        json = dict()
        json['loaderId'] = self.loader_id.to_json()
        json['action'] = self.action.to_json()
        json['url'] = self.url
        if self.target_hint is not None:
            json['targetHint'] = self.target_hint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            action=SpeculationAction.from_json(json['action']),
            url=str(json['url']),
            target_hint=SpeculationTargetHint.from_json(json['targetHint']) if 'targetHint' in json else None,
        )


@dataclass
class PreloadingAttemptSource:
    '''
    Lists sources for a preloading attempt, specifically the ids of rule sets
    that had a speculation rule that triggered the attempt, and the
    BackendNodeIds of <a href> or <area href> elements that triggered the
    attempt (in the case of attempts triggered by a document rule). It is
    possible for multiple rule sets and links to trigger a single attempt.
    '''
    key: PreloadingAttemptKey

    rule_set_ids: typing.List[RuleSetId]

    node_ids: typing.List[dom.BackendNodeId]

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['ruleSetIds'] = [i.to_json() for i in self.rule_set_ids]
        json['nodeIds'] = [i.to_json() for i in self.node_ids]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            rule_set_ids=[RuleSetId.from_json(i) for i in json['ruleSetIds']],
            node_ids=[dom.BackendNodeId.from_json(i) for i in json['nodeIds']],
        )


class PreloadPipelineId(str):
    '''
    Chrome manages different types of preloads together using a
    concept of preloading pipeline. For example, if a site uses a
    SpeculationRules for prerender, Chrome first starts a prefetch and
    then upgrades it to prerender.

    CDP events for them are emitted separately but they share
    ``PreloadPipelineId``.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PreloadPipelineId:
        return cls(json)

    def __repr__(self):
        return 'PreloadPipelineId({})'.format(super().__repr__())


class PrerenderFinalStatus(enum.Enum):
    '''
    List of FinalStatus reasons for Prerender2.
    '''
    ACTIVATED = "Activated"
    DESTROYED = "Destroyed"
    LOW_END_DEVICE = "LowEndDevice"
    INVALID_SCHEME_REDIRECT = "InvalidSchemeRedirect"
    INVALID_SCHEME_NAVIGATION = "InvalidSchemeNavigation"
    NAVIGATION_REQUEST_BLOCKED_BY_CSP = "NavigationRequestBlockedByCsp"
    MAIN_FRAME_NAVIGATION = "MainFrameNavigation"
    MOJO_BINDER_POLICY = "MojoBinderPolicy"
    RENDERER_PROCESS_CRASHED = "RendererProcessCrashed"
    RENDERER_PROCESS_KILLED = "RendererProcessKilled"
    DOWNLOAD = "Download"
    TRIGGER_DESTROYED = "TriggerDestroyed"
    NAVIGATION_NOT_COMMITTED = "NavigationNotCommitted"
    NAVIGATION_BAD_HTTP_STATUS = "NavigationBadHttpStatus"
    CLIENT_CERT_REQUESTED = "ClientCertRequested"
    NAVIGATION_REQUEST_NETWORK_ERROR = "NavigationRequestNetworkError"
    CANCEL_ALL_HOSTS_FOR_TESTING = "CancelAllHostsForTesting"
    DID_FAIL_LOAD = "DidFailLoad"
    STOP = "Stop"
    SSL_CERTIFICATE_ERROR = "SslCertificateError"
    LOGIN_AUTH_REQUESTED = "LoginAuthRequested"
    UA_CHANGE_REQUIRES_RELOAD = "UaChangeRequiresReload"
    BLOCKED_BY_CLIENT = "BlockedByClient"
    AUDIO_OUTPUT_DEVICE_REQUESTED = "AudioOutputDeviceRequested"
    MIXED_CONTENT = "MixedContent"
    TRIGGER_BACKGROUNDED = "TriggerBackgrounded"
    MEMORY_LIMIT_EXCEEDED = "MemoryLimitExceeded"
    DATA_SAVER_ENABLED = "DataSaverEnabled"
    TRIGGER_URL_HAS_EFFECTIVE_URL = "TriggerUrlHasEffectiveUrl"
    ACTIVATED_BEFORE_STARTED = "ActivatedBeforeStarted"
    INACTIVE_PAGE_RESTRICTION = "InactivePageRestriction"
    START_FAILED = "StartFailed"
    TIMEOUT_BACKGROUNDED = "TimeoutBackgrounded"
    CROSS_SITE_REDIRECT_IN_INITIAL_NAVIGATION = "CrossSiteRedirectInInitialNavigation"
    CROSS_SITE_NAVIGATION_IN_INITIAL_NAVIGATION = "CrossSiteNavigationInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInInitialNavigation"
    ACTIVATION_NAVIGATION_PARAMETER_MISMATCH = "ActivationNavigationParameterMismatch"
    ACTIVATED_IN_BACKGROUND = "ActivatedInBackground"
    EMBEDDER_HOST_DISALLOWED = "EmbedderHostDisallowed"
    ACTIVATION_NAVIGATION_DESTROYED_BEFORE_SUCCESS = "ActivationNavigationDestroyedBeforeSuccess"
    TAB_CLOSED_BY_USER_GESTURE = "TabClosedByUserGesture"
    TAB_CLOSED_WITHOUT_USER_GESTURE = "TabClosedWithoutUserGesture"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_CRASHED = "PrimaryMainFrameRendererProcessCrashed"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_KILLED = "PrimaryMainFrameRendererProcessKilled"
    ACTIVATION_FRAME_POLICY_NOT_COMPATIBLE = "ActivationFramePolicyNotCompatible"
    PRELOADING_DISABLED = "PreloadingDisabled"
    BATTERY_SAVER_ENABLED = "BatterySaverEnabled"
    ACTIVATED_DURING_MAIN_FRAME_NAVIGATION = "ActivatedDuringMainFrameNavigation"
    PRELOADING_UNSUPPORTED_BY_WEB_CONTENTS = "PreloadingUnsupportedByWebContents"
    CROSS_SITE_REDIRECT_IN_MAIN_FRAME_NAVIGATION = "CrossSiteRedirectInMainFrameNavigation"
    CROSS_SITE_NAVIGATION_IN_MAIN_FRAME_NAVIGATION = "CrossSiteNavigationInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInMainFrameNavigation"
    MEMORY_PRESSURE_ON_TRIGGER = "MemoryPressureOnTrigger"
    MEMORY_PRESSURE_AFTER_TRIGGERED = "MemoryPressureAfterTriggered"
    PRERENDERING_DISABLED_BY_DEV_TOOLS = "PrerenderingDisabledByDevTools"
    SPECULATION_RULE_REMOVED = "SpeculationRuleRemoved"
    ACTIVATED_WITH_AUXILIARY_BROWSING_CONTEXTS = "ActivatedWithAuxiliaryBrowsingContexts"
    MAX_NUM_OF_RUNNING_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_NON_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningNonEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_EMBEDDER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEmbedderPrerendersExceeded"
    PRERENDERING_URL_HAS_EFFECTIVE_URL = "PrerenderingUrlHasEffectiveUrl"
    REDIRECTED_PRERENDERING_URL_HAS_EFFECTIVE_URL = "RedirectedPrerenderingUrlHasEffectiveUrl"
    ACTIVATION_URL_HAS_EFFECTIVE_URL = "ActivationUrlHasEffectiveUrl"
    JAVA_SCRIPT_INTERFACE_ADDED = "JavaScriptInterfaceAdded"
    JAVA_SCRIPT_INTERFACE_REMOVED = "JavaScriptInterfaceRemoved"
    ALL_PRERENDERING_CANCELED = "AllPrerenderingCanceled"
    WINDOW_CLOSED = "WindowClosed"
    SLOW_NETWORK = "SlowNetwork"
    OTHER_PRERENDERED_PAGE_ACTIVATED = "OtherPrerenderedPageActivated"
    V8_OPTIMIZER_DISABLED = "V8OptimizerDisabled"
    PRERENDER_FAILED_DURING_PREFETCH = "PrerenderFailedDuringPrefetch"
    BROWSING_DATA_REMOVED = "BrowsingDataRemoved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PreloadingStatus(enum.Enum):
    '''
    Preloading status values, see also PreloadingTriggeringOutcome. This
    status is shared by prefetchStatusUpdated and prerenderStatusUpdated.
    '''
    PENDING = "Pending"
    RUNNING = "Running"
    READY = "Ready"
    SUCCESS = "Success"
    FAILURE = "Failure"
    NOT_SUPPORTED = "NotSupported"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PrefetchStatus(enum.Enum):
    '''
    TODO(https://crbug.com/1384419): revisit the list of PrefetchStatus and
    filter out the ones that aren't necessary to the developers.
    '''
    PREFETCH_ALLOWED = "PrefetchAllowed"
    PREFETCH_FAILED_INELIGIBLE_REDIRECT = "PrefetchFailedIneligibleRedirect"
    PREFETCH_FAILED_INVALID_REDIRECT = "PrefetchFailedInvalidRedirect"
    PREFETCH_FAILED_MIME_NOT_SUPPORTED = "PrefetchFailedMIMENotSupported"
    PREFETCH_FAILED_NET_ERROR = "PrefetchFailedNetError"
    PREFETCH_FAILED_NON2_XX = "PrefetchFailedNon2XX"
    PREFETCH_EVICTED_AFTER_BROWSING_DATA_REMOVED = "PrefetchEvictedAfterBrowsingDataRemoved"
    PREFETCH_EVICTED_AFTER_CANDIDATE_REMOVED = "PrefetchEvictedAfterCandidateRemoved"
    PREFETCH_EVICTED_FOR_NEWER_PREFETCH = "PrefetchEvictedForNewerPrefetch"
    PREFETCH_HELDBACK = "PrefetchHeldback"
    PREFETCH_INELIGIBLE_RETRY_AFTER = "PrefetchIneligibleRetryAfter"
    PREFETCH_IS_PRIVACY_DECOY = "PrefetchIsPrivacyDecoy"
    PREFETCH_IS_STALE = "PrefetchIsStale"
    PREFETCH_NOT_ELIGIBLE_BROWSER_CONTEXT_OFF_THE_RECORD = "PrefetchNotEligibleBrowserContextOffTheRecord"
    PREFETCH_NOT_ELIGIBLE_DATA_SAVER_ENABLED = "PrefetchNotEligibleDataSaverEnabled"
    PREFETCH_NOT_ELIGIBLE_EXISTING_PROXY = "PrefetchNotEligibleExistingProxy"
    PREFETCH_NOT_ELIGIBLE_HOST_IS_NON_UNIQUE = "PrefetchNotEligibleHostIsNonUnique"
    PREFETCH_NOT_ELIGIBLE_NON_DEFAULT_STORAGE_PARTITION = "PrefetchNotEligibleNonDefaultStoragePartition"
    PREFETCH_NOT_ELIGIBLE_SAME_SITE_CROSS_ORIGIN_PREFETCH_REQUIRED_PROXY = "PrefetchNotEligibleSameSiteCrossOriginPrefetchRequiredProxy"
    PREFETCH_NOT_ELIGIBLE_SCHEME_IS_NOT_HTTPS = "PrefetchNotEligibleSchemeIsNotHttps"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_COOKIES = "PrefetchNotEligibleUserHasCookies"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_SERVICE_WORKER = "PrefetchNotEligibleUserHasServiceWorker"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_SERVICE_WORKER_NO_FETCH_HANDLER = "PrefetchNotEligibleUserHasServiceWorkerNoFetchHandler"
    PREFETCH_NOT_ELIGIBLE_REDIRECT_FROM_SERVICE_WORKER = "PrefetchNotEligibleRedirectFromServiceWorker"
    PREFETCH_NOT_ELIGIBLE_REDIRECT_TO_SERVICE_WORKER = "PrefetchNotEligibleRedirectToServiceWorker"
    PREFETCH_NOT_ELIGIBLE_BATTERY_SAVER_ENABLED = "PrefetchNotEligibleBatterySaverEnabled"
    PREFETCH_NOT_ELIGIBLE_PRELOADING_DISABLED = "PrefetchNotEligiblePreloadingDisabled"
    PREFETCH_NOT_FINISHED_IN_TIME = "PrefetchNotFinishedInTime"
    PREFETCH_NOT_STARTED = "PrefetchNotStarted"
    PREFETCH_NOT_USED_COOKIES_CHANGED = "PrefetchNotUsedCookiesChanged"
    PREFETCH_PROXY_NOT_AVAILABLE = "PrefetchProxyNotAvailable"
    PREFETCH_RESPONSE_USED = "PrefetchResponseUsed"
    PREFETCH_SUCCESSFUL_BUT_NOT_USED = "PrefetchSuccessfulButNotUsed"
    PREFETCH_NOT_USED_PROBE_FAILED = "PrefetchNotUsedProbeFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PrerenderMismatchedHeaders:
    '''
    Information of headers to be displayed when the header mismatch occurred.
    '''
    header_name: str

    initial_value: typing.Optional[str] = None

    activation_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['headerName'] = self.header_name
        if self.initial_value is not None:
            json['initialValue'] = self.initial_value
        if self.activation_value is not None:
            json['activationValue'] = self.activation_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header_name=str(json['headerName']),
            initial_value=str(json['initialValue']) if 'initialValue' in json else None,
            activation_value=str(json['activationValue']) if 'activationValue' in json else None,
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.disable',
    }
    json = yield cmd_dict


@event_class('Preload.ruleSetUpdated')
@dataclass
class RuleSetUpdated:
    '''
    Upsert. Currently, it is only emitted when a rule set added.
    '''
    rule_set: RuleSet

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetUpdated:
        return cls(
            rule_set=RuleSet.from_json(json['ruleSet'])
        )


@event_class('Preload.ruleSetRemoved')
@dataclass
class RuleSetRemoved:
    id_: RuleSetId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetRemoved:
        return cls(
            id_=RuleSetId.from_json(json['id'])
        )


@event_class('Preload.preloadEnabledStateUpdated')
@dataclass
class PreloadEnabledStateUpdated:
    '''
    Fired when a preload enabled state is updated.
    '''
    disabled_by_preference: bool
    disabled_by_data_saver: bool
    disabled_by_battery_saver: bool
    disabled_by_holdback_prefetch_speculation_rules: bool
    disabled_by_holdback_prerender_speculation_rules: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadEnabledStateUpdated:
        return cls(
            disabled_by_preference=bool(json['disabledByPreference']),
            disabled_by_data_saver=bool(json['disabledByDataSaver']),
            disabled_by_battery_saver=bool(json['disabledByBatterySaver']),
            disabled_by_holdback_prefetch_speculation_rules=bool(json['disabledByHoldbackPrefetchSpeculationRules']),
            disabled_by_holdback_prerender_speculation_rules=bool(json['disabledByHoldbackPrerenderSpeculationRules'])
        )


@event_class('Preload.prefetchStatusUpdated')
@dataclass
class PrefetchStatusUpdated:
    '''
    Fired when a prefetch attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    #: The frame id of the frame initiating prefetch.
    initiating_frame_id: page.FrameId
    prefetch_url: str
    status: PreloadingStatus
    prefetch_status: PrefetchStatus
    request_id: network.RequestId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrefetchStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            initiating_frame_id=page.FrameId.from_json(json['initiatingFrameId']),
            prefetch_url=str(json['prefetchUrl']),
            status=PreloadingStatus.from_json(json['status']),
            prefetch_status=PrefetchStatus.from_json(json['prefetchStatus']),
            request_id=network.RequestId.from_json(json['requestId'])
        )


@event_class('Preload.prerenderStatusUpdated')
@dataclass
class PrerenderStatusUpdated:
    '''
    Fired when a prerender attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    status: PreloadingStatus
    prerender_status: typing.Optional[PrerenderFinalStatus]
    #: This is used to give users more information about the name of Mojo interface
    #: that is incompatible with prerender and has caused the cancellation of the attempt.
    disallowed_mojo_interface: typing.Optional[str]
    mismatched_headers: typing.Optional[typing.List[PrerenderMismatchedHeaders]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrerenderStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            status=PreloadingStatus.from_json(json['status']),
            prerender_status=PrerenderFinalStatus.from_json(json['prerenderStatus']) if 'prerenderStatus' in json else None,
            disallowed_mojo_interface=str(json['disallowedMojoInterface']) if 'disallowedMojoInterface' in json else None,
            mismatched_headers=[PrerenderMismatchedHeaders.from_json(i) for i in json['mismatchedHeaders']] if 'mismatchedHeaders' in json else None
        )


@event_class('Preload.preloadingAttemptSourcesUpdated')
@dataclass
class PreloadingAttemptSourcesUpdated:
    '''
    Send a list of sources for all preloading attempts in a document.
    '''
    loader_id: network.LoaderId
    preloading_attempt_sources: typing.List[PreloadingAttemptSource]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadingAttemptSourcesUpdated:
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            preloading_attempt_sources=[PreloadingAttemptSource.from_json(i) for i in json['preloadingAttemptSources']]
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\preload.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Preload (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import network
from . import page


class RuleSetId(str):
    '''
    Unique id
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> RuleSetId:
        return cls(json)

    def __repr__(self):
        return 'RuleSetId({})'.format(super().__repr__())


@dataclass
class RuleSet:
    '''
    Corresponds to SpeculationRuleSet
    '''
    id_: RuleSetId

    #: Identifies a document which the rule set is associated with.
    loader_id: network.LoaderId

    #: Source text of JSON representing the rule set. If it comes from
    #: ``script`` tag, it is the textContent of the node. Note that it is
    #: a JSON for valid case.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html
    #: - https://github.com/WICG/nav-speculation/blob/main/triggers.md
    source_text: str

    #: A speculation rule set is either added through an inline
    #: ``script`` tag or through an external resource via the
    #: 'Speculation-Rules' HTTP header. For the first case, we include
    #: the BackendNodeId of the relevant ``script`` tag. For the second
    #: case, we include the external URL where the rule set was loaded
    #: from, and also RequestId if Network domain is enabled.
    #: 
    #: See also:
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-script
    #: - https://wicg.github.io/nav-speculation/speculation-rules.html#speculation-rules-header
    backend_node_id: typing.Optional[dom.BackendNodeId] = None

    url: typing.Optional[str] = None

    request_id: typing.Optional[network.RequestId] = None

    #: Error information
    #: ``errorMessage`` is null iff ``errorType`` is null.
    error_type: typing.Optional[RuleSetErrorType] = None

    #: TODO(https://crbug.com/1425354): Replace this property with structured error.
    error_message: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['id'] = self.id_.to_json()
        json['loaderId'] = self.loader_id.to_json()
        json['sourceText'] = self.source_text
        if self.backend_node_id is not None:
            json['backendNodeId'] = self.backend_node_id.to_json()
        if self.url is not None:
            json['url'] = self.url
        if self.request_id is not None:
            json['requestId'] = self.request_id.to_json()
        if self.error_type is not None:
            json['errorType'] = self.error_type.to_json()
        if self.error_message is not None:
            json['errorMessage'] = self.error_message
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            id_=RuleSetId.from_json(json['id']),
            loader_id=network.LoaderId.from_json(json['loaderId']),
            source_text=str(json['sourceText']),
            backend_node_id=dom.BackendNodeId.from_json(json['backendNodeId']) if 'backendNodeId' in json else None,
            url=str(json['url']) if 'url' in json else None,
            request_id=network.RequestId.from_json(json['requestId']) if 'requestId' in json else None,
            error_type=RuleSetErrorType.from_json(json['errorType']) if 'errorType' in json else None,
            error_message=str(json['errorMessage']) if 'errorMessage' in json else None,
        )


class RuleSetErrorType(enum.Enum):
    SOURCE_IS_NOT_JSON_OBJECT = "SourceIsNotJsonObject"
    INVALID_RULES_SKIPPED = "InvalidRulesSkipped"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationAction(enum.Enum):
    '''
    The type of preloading attempted. It corresponds to
    mojom::SpeculationAction (although PrefetchWithSubresources is omitted as it
    isn't being used by clients).
    '''
    PREFETCH = "Prefetch"
    PRERENDER = "Prerender"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class SpeculationTargetHint(enum.Enum):
    '''
    Corresponds to mojom::SpeculationTargetHint.
    See https://github.com/WICG/nav-speculation/blob/main/triggers.md#window-name-targeting-hints
    '''
    BLANK = "Blank"
    SELF = "Self"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PreloadingAttemptKey:
    '''
    A key that identifies a preloading attempt.

    The url used is the url specified by the trigger (i.e. the initial URL), and
    not the final url that is navigated to. For example, prerendering allows
    same-origin main frame navigations during the attempt, but the attempt is
    still keyed with the initial URL.
    '''
    loader_id: network.LoaderId

    action: SpeculationAction

    url: str

    target_hint: typing.Optional[SpeculationTargetHint] = None

    def to_json(self):
        json = dict()
        json['loaderId'] = self.loader_id.to_json()
        json['action'] = self.action.to_json()
        json['url'] = self.url
        if self.target_hint is not None:
            json['targetHint'] = self.target_hint.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            action=SpeculationAction.from_json(json['action']),
            url=str(json['url']),
            target_hint=SpeculationTargetHint.from_json(json['targetHint']) if 'targetHint' in json else None,
        )


@dataclass
class PreloadingAttemptSource:
    '''
    Lists sources for a preloading attempt, specifically the ids of rule sets
    that had a speculation rule that triggered the attempt, and the
    BackendNodeIds of <a href> or <area href> elements that triggered the
    attempt (in the case of attempts triggered by a document rule). It is
    possible for multiple rule sets and links to trigger a single attempt.
    '''
    key: PreloadingAttemptKey

    rule_set_ids: typing.List[RuleSetId]

    node_ids: typing.List[dom.BackendNodeId]

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['ruleSetIds'] = [i.to_json() for i in self.rule_set_ids]
        json['nodeIds'] = [i.to_json() for i in self.node_ids]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            rule_set_ids=[RuleSetId.from_json(i) for i in json['ruleSetIds']],
            node_ids=[dom.BackendNodeId.from_json(i) for i in json['nodeIds']],
        )


class PreloadPipelineId(str):
    '''
    Chrome manages different types of preloads together using a
    concept of preloading pipeline. For example, if a site uses a
    SpeculationRules for prerender, Chrome first starts a prefetch and
    then upgrades it to prerender.

    CDP events for them are emitted separately but they share
    ``PreloadPipelineId``.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> PreloadPipelineId:
        return cls(json)

    def __repr__(self):
        return 'PreloadPipelineId({})'.format(super().__repr__())


class PrerenderFinalStatus(enum.Enum):
    '''
    List of FinalStatus reasons for Prerender2.
    '''
    ACTIVATED = "Activated"
    DESTROYED = "Destroyed"
    LOW_END_DEVICE = "LowEndDevice"
    INVALID_SCHEME_REDIRECT = "InvalidSchemeRedirect"
    INVALID_SCHEME_NAVIGATION = "InvalidSchemeNavigation"
    NAVIGATION_REQUEST_BLOCKED_BY_CSP = "NavigationRequestBlockedByCsp"
    MAIN_FRAME_NAVIGATION = "MainFrameNavigation"
    MOJO_BINDER_POLICY = "MojoBinderPolicy"
    RENDERER_PROCESS_CRASHED = "RendererProcessCrashed"
    RENDERER_PROCESS_KILLED = "RendererProcessKilled"
    DOWNLOAD = "Download"
    TRIGGER_DESTROYED = "TriggerDestroyed"
    NAVIGATION_NOT_COMMITTED = "NavigationNotCommitted"
    NAVIGATION_BAD_HTTP_STATUS = "NavigationBadHttpStatus"
    CLIENT_CERT_REQUESTED = "ClientCertRequested"
    NAVIGATION_REQUEST_NETWORK_ERROR = "NavigationRequestNetworkError"
    CANCEL_ALL_HOSTS_FOR_TESTING = "CancelAllHostsForTesting"
    DID_FAIL_LOAD = "DidFailLoad"
    STOP = "Stop"
    SSL_CERTIFICATE_ERROR = "SslCertificateError"
    LOGIN_AUTH_REQUESTED = "LoginAuthRequested"
    UA_CHANGE_REQUIRES_RELOAD = "UaChangeRequiresReload"
    BLOCKED_BY_CLIENT = "BlockedByClient"
    AUDIO_OUTPUT_DEVICE_REQUESTED = "AudioOutputDeviceRequested"
    MIXED_CONTENT = "MixedContent"
    TRIGGER_BACKGROUNDED = "TriggerBackgrounded"
    MEMORY_LIMIT_EXCEEDED = "MemoryLimitExceeded"
    DATA_SAVER_ENABLED = "DataSaverEnabled"
    TRIGGER_URL_HAS_EFFECTIVE_URL = "TriggerUrlHasEffectiveUrl"
    ACTIVATED_BEFORE_STARTED = "ActivatedBeforeStarted"
    INACTIVE_PAGE_RESTRICTION = "InactivePageRestriction"
    START_FAILED = "StartFailed"
    TIMEOUT_BACKGROUNDED = "TimeoutBackgrounded"
    CROSS_SITE_REDIRECT_IN_INITIAL_NAVIGATION = "CrossSiteRedirectInInitialNavigation"
    CROSS_SITE_NAVIGATION_IN_INITIAL_NAVIGATION = "CrossSiteNavigationInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInInitialNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_INITIAL_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInInitialNavigation"
    ACTIVATION_NAVIGATION_PARAMETER_MISMATCH = "ActivationNavigationParameterMismatch"
    ACTIVATED_IN_BACKGROUND = "ActivatedInBackground"
    EMBEDDER_HOST_DISALLOWED = "EmbedderHostDisallowed"
    ACTIVATION_NAVIGATION_DESTROYED_BEFORE_SUCCESS = "ActivationNavigationDestroyedBeforeSuccess"
    TAB_CLOSED_BY_USER_GESTURE = "TabClosedByUserGesture"
    TAB_CLOSED_WITHOUT_USER_GESTURE = "TabClosedWithoutUserGesture"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_CRASHED = "PrimaryMainFrameRendererProcessCrashed"
    PRIMARY_MAIN_FRAME_RENDERER_PROCESS_KILLED = "PrimaryMainFrameRendererProcessKilled"
    ACTIVATION_FRAME_POLICY_NOT_COMPATIBLE = "ActivationFramePolicyNotCompatible"
    PRELOADING_DISABLED = "PreloadingDisabled"
    BATTERY_SAVER_ENABLED = "BatterySaverEnabled"
    ACTIVATED_DURING_MAIN_FRAME_NAVIGATION = "ActivatedDuringMainFrameNavigation"
    PRELOADING_UNSUPPORTED_BY_WEB_CONTENTS = "PreloadingUnsupportedByWebContents"
    CROSS_SITE_REDIRECT_IN_MAIN_FRAME_NAVIGATION = "CrossSiteRedirectInMainFrameNavigation"
    CROSS_SITE_NAVIGATION_IN_MAIN_FRAME_NAVIGATION = "CrossSiteNavigationInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_REDIRECT_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginRedirectNotOptInInMainFrameNavigation"
    SAME_SITE_CROSS_ORIGIN_NAVIGATION_NOT_OPT_IN_IN_MAIN_FRAME_NAVIGATION = "SameSiteCrossOriginNavigationNotOptInInMainFrameNavigation"
    MEMORY_PRESSURE_ON_TRIGGER = "MemoryPressureOnTrigger"
    MEMORY_PRESSURE_AFTER_TRIGGERED = "MemoryPressureAfterTriggered"
    PRERENDERING_DISABLED_BY_DEV_TOOLS = "PrerenderingDisabledByDevTools"
    SPECULATION_RULE_REMOVED = "SpeculationRuleRemoved"
    ACTIVATED_WITH_AUXILIARY_BROWSING_CONTEXTS = "ActivatedWithAuxiliaryBrowsingContexts"
    MAX_NUM_OF_RUNNING_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_NON_EAGER_PRERENDERS_EXCEEDED = "MaxNumOfRunningNonEagerPrerendersExceeded"
    MAX_NUM_OF_RUNNING_EMBEDDER_PRERENDERS_EXCEEDED = "MaxNumOfRunningEmbedderPrerendersExceeded"
    PRERENDERING_URL_HAS_EFFECTIVE_URL = "PrerenderingUrlHasEffectiveUrl"
    REDIRECTED_PRERENDERING_URL_HAS_EFFECTIVE_URL = "RedirectedPrerenderingUrlHasEffectiveUrl"
    ACTIVATION_URL_HAS_EFFECTIVE_URL = "ActivationUrlHasEffectiveUrl"
    JAVA_SCRIPT_INTERFACE_ADDED = "JavaScriptInterfaceAdded"
    JAVA_SCRIPT_INTERFACE_REMOVED = "JavaScriptInterfaceRemoved"
    ALL_PRERENDERING_CANCELED = "AllPrerenderingCanceled"
    WINDOW_CLOSED = "WindowClosed"
    SLOW_NETWORK = "SlowNetwork"
    OTHER_PRERENDERED_PAGE_ACTIVATED = "OtherPrerenderedPageActivated"
    V8_OPTIMIZER_DISABLED = "V8OptimizerDisabled"
    PRERENDER_FAILED_DURING_PREFETCH = "PrerenderFailedDuringPrefetch"
    BROWSING_DATA_REMOVED = "BrowsingDataRemoved"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PreloadingStatus(enum.Enum):
    '''
    Preloading status values, see also PreloadingTriggeringOutcome. This
    status is shared by prefetchStatusUpdated and prerenderStatusUpdated.
    '''
    PENDING = "Pending"
    RUNNING = "Running"
    READY = "Ready"
    SUCCESS = "Success"
    FAILURE = "Failure"
    NOT_SUPPORTED = "NotSupported"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class PrefetchStatus(enum.Enum):
    '''
    TODO(https://crbug.com/1384419): revisit the list of PrefetchStatus and
    filter out the ones that aren't necessary to the developers.
    '''
    PREFETCH_ALLOWED = "PrefetchAllowed"
    PREFETCH_FAILED_INELIGIBLE_REDIRECT = "PrefetchFailedIneligibleRedirect"
    PREFETCH_FAILED_INVALID_REDIRECT = "PrefetchFailedInvalidRedirect"
    PREFETCH_FAILED_MIME_NOT_SUPPORTED = "PrefetchFailedMIMENotSupported"
    PREFETCH_FAILED_NET_ERROR = "PrefetchFailedNetError"
    PREFETCH_FAILED_NON2_XX = "PrefetchFailedNon2XX"
    PREFETCH_EVICTED_AFTER_BROWSING_DATA_REMOVED = "PrefetchEvictedAfterBrowsingDataRemoved"
    PREFETCH_EVICTED_AFTER_CANDIDATE_REMOVED = "PrefetchEvictedAfterCandidateRemoved"
    PREFETCH_EVICTED_FOR_NEWER_PREFETCH = "PrefetchEvictedForNewerPrefetch"
    PREFETCH_HELDBACK = "PrefetchHeldback"
    PREFETCH_INELIGIBLE_RETRY_AFTER = "PrefetchIneligibleRetryAfter"
    PREFETCH_IS_PRIVACY_DECOY = "PrefetchIsPrivacyDecoy"
    PREFETCH_IS_STALE = "PrefetchIsStale"
    PREFETCH_NOT_ELIGIBLE_BROWSER_CONTEXT_OFF_THE_RECORD = "PrefetchNotEligibleBrowserContextOffTheRecord"
    PREFETCH_NOT_ELIGIBLE_DATA_SAVER_ENABLED = "PrefetchNotEligibleDataSaverEnabled"
    PREFETCH_NOT_ELIGIBLE_EXISTING_PROXY = "PrefetchNotEligibleExistingProxy"
    PREFETCH_NOT_ELIGIBLE_HOST_IS_NON_UNIQUE = "PrefetchNotEligibleHostIsNonUnique"
    PREFETCH_NOT_ELIGIBLE_NON_DEFAULT_STORAGE_PARTITION = "PrefetchNotEligibleNonDefaultStoragePartition"
    PREFETCH_NOT_ELIGIBLE_SAME_SITE_CROSS_ORIGIN_PREFETCH_REQUIRED_PROXY = "PrefetchNotEligibleSameSiteCrossOriginPrefetchRequiredProxy"
    PREFETCH_NOT_ELIGIBLE_SCHEME_IS_NOT_HTTPS = "PrefetchNotEligibleSchemeIsNotHttps"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_COOKIES = "PrefetchNotEligibleUserHasCookies"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_SERVICE_WORKER = "PrefetchNotEligibleUserHasServiceWorker"
    PREFETCH_NOT_ELIGIBLE_USER_HAS_SERVICE_WORKER_NO_FETCH_HANDLER = "PrefetchNotEligibleUserHasServiceWorkerNoFetchHandler"
    PREFETCH_NOT_ELIGIBLE_REDIRECT_FROM_SERVICE_WORKER = "PrefetchNotEligibleRedirectFromServiceWorker"
    PREFETCH_NOT_ELIGIBLE_REDIRECT_TO_SERVICE_WORKER = "PrefetchNotEligibleRedirectToServiceWorker"
    PREFETCH_NOT_ELIGIBLE_BATTERY_SAVER_ENABLED = "PrefetchNotEligibleBatterySaverEnabled"
    PREFETCH_NOT_ELIGIBLE_PRELOADING_DISABLED = "PrefetchNotEligiblePreloadingDisabled"
    PREFETCH_NOT_FINISHED_IN_TIME = "PrefetchNotFinishedInTime"
    PREFETCH_NOT_STARTED = "PrefetchNotStarted"
    PREFETCH_NOT_USED_COOKIES_CHANGED = "PrefetchNotUsedCookiesChanged"
    PREFETCH_PROXY_NOT_AVAILABLE = "PrefetchProxyNotAvailable"
    PREFETCH_RESPONSE_USED = "PrefetchResponseUsed"
    PREFETCH_SUCCESSFUL_BUT_NOT_USED = "PrefetchSuccessfulButNotUsed"
    PREFETCH_NOT_USED_PROBE_FAILED = "PrefetchNotUsedProbeFailed"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class PrerenderMismatchedHeaders:
    '''
    Information of headers to be displayed when the header mismatch occurred.
    '''
    header_name: str

    initial_value: typing.Optional[str] = None

    activation_value: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['headerName'] = self.header_name
        if self.initial_value is not None:
            json['initialValue'] = self.initial_value
        if self.activation_value is not None:
            json['activationValue'] = self.activation_value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            header_name=str(json['headerName']),
            initial_value=str(json['initialValue']) if 'initialValue' in json else None,
            activation_value=str(json['activationValue']) if 'activationValue' in json else None,
        )


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.enable',
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'Preload.disable',
    }
    json = yield cmd_dict


@event_class('Preload.ruleSetUpdated')
@dataclass
class RuleSetUpdated:
    '''
    Upsert. Currently, it is only emitted when a rule set added.
    '''
    rule_set: RuleSet

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetUpdated:
        return cls(
            rule_set=RuleSet.from_json(json['ruleSet'])
        )


@event_class('Preload.ruleSetRemoved')
@dataclass
class RuleSetRemoved:
    id_: RuleSetId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> RuleSetRemoved:
        return cls(
            id_=RuleSetId.from_json(json['id'])
        )


@event_class('Preload.preloadEnabledStateUpdated')
@dataclass
class PreloadEnabledStateUpdated:
    '''
    Fired when a preload enabled state is updated.
    '''
    disabled_by_preference: bool
    disabled_by_data_saver: bool
    disabled_by_battery_saver: bool
    disabled_by_holdback_prefetch_speculation_rules: bool
    disabled_by_holdback_prerender_speculation_rules: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadEnabledStateUpdated:
        return cls(
            disabled_by_preference=bool(json['disabledByPreference']),
            disabled_by_data_saver=bool(json['disabledByDataSaver']),
            disabled_by_battery_saver=bool(json['disabledByBatterySaver']),
            disabled_by_holdback_prefetch_speculation_rules=bool(json['disabledByHoldbackPrefetchSpeculationRules']),
            disabled_by_holdback_prerender_speculation_rules=bool(json['disabledByHoldbackPrerenderSpeculationRules'])
        )


@event_class('Preload.prefetchStatusUpdated')
@dataclass
class PrefetchStatusUpdated:
    '''
    Fired when a prefetch attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    #: The frame id of the frame initiating prefetch.
    initiating_frame_id: page.FrameId
    prefetch_url: str
    status: PreloadingStatus
    prefetch_status: PrefetchStatus
    request_id: network.RequestId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrefetchStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            initiating_frame_id=page.FrameId.from_json(json['initiatingFrameId']),
            prefetch_url=str(json['prefetchUrl']),
            status=PreloadingStatus.from_json(json['status']),
            prefetch_status=PrefetchStatus.from_json(json['prefetchStatus']),
            request_id=network.RequestId.from_json(json['requestId'])
        )


@event_class('Preload.prerenderStatusUpdated')
@dataclass
class PrerenderStatusUpdated:
    '''
    Fired when a prerender attempt is updated.
    '''
    key: PreloadingAttemptKey
    pipeline_id: PreloadPipelineId
    status: PreloadingStatus
    prerender_status: typing.Optional[PrerenderFinalStatus]
    #: This is used to give users more information about the name of Mojo interface
    #: that is incompatible with prerender and has caused the cancellation of the attempt.
    disallowed_mojo_interface: typing.Optional[str]
    mismatched_headers: typing.Optional[typing.List[PrerenderMismatchedHeaders]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PrerenderStatusUpdated:
        return cls(
            key=PreloadingAttemptKey.from_json(json['key']),
            pipeline_id=PreloadPipelineId.from_json(json['pipelineId']),
            status=PreloadingStatus.from_json(json['status']),
            prerender_status=PrerenderFinalStatus.from_json(json['prerenderStatus']) if 'prerenderStatus' in json else None,
            disallowed_mojo_interface=str(json['disallowedMojoInterface']) if 'disallowedMojoInterface' in json else None,
            mismatched_headers=[PrerenderMismatchedHeaders.from_json(i) for i in json['mismatchedHeaders']] if 'mismatchedHeaders' in json else None
        )


@event_class('Preload.preloadingAttemptSourcesUpdated')
@dataclass
class PreloadingAttemptSourcesUpdated:
    '''
    Send a list of sources for all preloading attempts in a document.
    '''
    loader_id: network.LoaderId
    preloading_attempt_sources: typing.List[PreloadingAttemptSource]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> PreloadingAttemptSourcesUpdated:
        return cls(
            loader_id=network.LoaderId.from_json(json['loaderId']),
            preloading_attempt_sources=[PreloadingAttemptSource.from_json(i) for i in json['preloadingAttemptSources']]
        )

# === NexusCore/openenv\Lib\site-packages\psutil\_psosx.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""macOS platform implementation."""

import errno
import functools
import os
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_osx as cext
from . import _psutil_posix as cext_posix
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import ZombieProcess
from ._common import conn_tmap
from ._common import conn_to_ntuple
from ._common import isfile_strict
from ._common import memoize_when_activated
from ._common import parse_environ_block
from ._common import usage_percent
from ._compat import PermissionError
from ._compat import ProcessLookupError


__extra__all__ = []


# =====================================================================
# --- globals
# =====================================================================


PAGESIZE = cext_posix.getpagesize()
AF_LINK = cext_posix.AF_LINK

TCP_STATUSES = {
    cext.TCPS_ESTABLISHED: _common.CONN_ESTABLISHED,
    cext.TCPS_SYN_SENT: _common.CONN_SYN_SENT,
    cext.TCPS_SYN_RECEIVED: _common.CONN_SYN_RECV,
    cext.TCPS_FIN_WAIT_1: _common.CONN_FIN_WAIT1,
    cext.TCPS_FIN_WAIT_2: _common.CONN_FIN_WAIT2,
    cext.TCPS_TIME_WAIT: _common.CONN_TIME_WAIT,
    cext.TCPS_CLOSED: _common.CONN_CLOSE,
    cext.TCPS_CLOSE_WAIT: _common.CONN_CLOSE_WAIT,
    cext.TCPS_LAST_ACK: _common.CONN_LAST_ACK,
    cext.TCPS_LISTEN: _common.CONN_LISTEN,
    cext.TCPS_CLOSING: _common.CONN_CLOSING,
    cext.PSUTIL_CONN_NONE: _common.CONN_NONE,
}

PROC_STATUSES = {
    cext.SIDL: _common.STATUS_IDLE,
    cext.SRUN: _common.STATUS_RUNNING,
    cext.SSLEEP: _common.STATUS_SLEEPING,
    cext.SSTOP: _common.STATUS_STOPPED,
    cext.SZOMB: _common.STATUS_ZOMBIE,
}

kinfo_proc_map = dict(
    ppid=0,
    ruid=1,
    euid=2,
    suid=3,
    rgid=4,
    egid=5,
    sgid=6,
    ttynr=7,
    ctime=8,
    status=9,
    name=10,
)

pidtaskinfo_map = dict(
    cpuutime=0,
    cpustime=1,
    rss=2,
    vms=3,
    pfaults=4,
    pageins=5,
    numthreads=6,
    volctxsw=7,
)


# =====================================================================
# --- named tuples
# =====================================================================


# fmt: off
# psutil.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'nice', 'system', 'idle'])
# psutil.virtual_memory()
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'wired'])
# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms', 'pfaults', 'pageins'])
# psutil.Process.memory_full_info()
pfullmem = namedtuple('pfullmem', pmem._fields + ('uss', ))
# fmt: on


# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    """System virtual memory as a namedtuple."""
    total, active, inactive, wired, free, speculative = cext.virtual_mem()
    # This is how Zabbix calculate avail and used mem:
    # https://github.com/zabbix/zabbix/blob/trunk/src/libs/zbxsysinfo/
    #     osx/memory.c
    # Also see: https://github.com/giampaolo/psutil/issues/1277
    avail = inactive + free
    used = active + wired
    # This is NOT how Zabbix calculates free mem but it matches "free"
    # cmdline utility.
    free -= speculative
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, avail, percent, used, free, active, inactive, wired)


def swap_memory():
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, used, free, sin, sout = cext.swap_mem()
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = cext.cpu_times()
    return scputimes(user, nice, system, idle)


def per_cpu_times():
    """Return system CPU times as a named tuple."""
    ret = []
    for cpu_t in cext.per_cpu_times():
        user, nice, system, idle = cpu_t
        item = scputimes(user, nice, system, idle)
        ret.append(item)
    return ret


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    return cext.cpu_count_logical()


def cpu_count_cores():
    """Return the number of CPU cores in the system."""
    return cext.cpu_count_cores()


def cpu_stats():
    ctx_switches, interrupts, soft_interrupts, syscalls, traps = (
        cext.cpu_stats()
    )
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls
    )


def cpu_freq():
    """Return CPU frequency.
    On macOS per-cpu frequency is not supported.
    Also, the returned frequency never changes, see:
    https://arstechnica.com/civis/viewtopic.php?f=19&t=465002.
    """
    curr, min_, max_ = cext.cpu_freq()
    return [_common.scpufreq(curr, min_, max_)]


# =====================================================================
# --- disks
# =====================================================================


disk_usage = _psposix.disk_usage
disk_io_counters = cext.disk_io_counters


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples."""
    retlist = []
    partitions = cext.disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) or not os.path.exists(device):
                continue
        maxfile = maxpath = None  # set later
        ntuple = _common.sdiskpart(
            device, mountpoint, fstype, opts, maxfile, maxpath
        )
        retlist.append(ntuple)
    return retlist


# =====================================================================
# --- sensors
# =====================================================================


def sensors_battery():
    """Return battery information."""
    try:
        percent, minsleft, power_plugged = cext.sensors_battery()
    except NotImplementedError:
        # no power source - return None according to interface
        return None
    power_plugged = power_plugged == 1
    if power_plugged:
        secsleft = _common.POWER_TIME_UNLIMITED
    elif minsleft == -1:
        secsleft = _common.POWER_TIME_UNKNOWN
    else:
        secsleft = minsleft * 60
    return _common.sbattery(percent, secsleft, power_plugged)


# =====================================================================
# --- network
# =====================================================================


net_io_counters = cext.net_io_counters
net_if_addrs = cext_posix.net_if_addrs


def net_connections(kind='inet'):
    """System-wide network connections."""
    # Note: on macOS this will fail with AccessDenied unless
    # the process is owned by root.
    ret = []
    for pid in pids():
        try:
            cons = Process(pid).connections(kind)
        except NoSuchProcess:
            continue
        else:
            if cons:
                for c in cons:
                    c = list(c) + [pid]
                    ret.append(_common.sconn(*c))
    return ret


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        try:
            mtu = cext_posix.net_if_mtu(name)
            flags = cext_posix.net_if_flags(name)
            duplex, speed = cext_posix.net_if_duplex_speed(name)
        except OSError as err:
            # https://github.com/giampaolo/psutil/issues/1279
            if err.errno != errno.ENODEV:
                raise
        else:
            if hasattr(_common, 'NicDuplex'):
                duplex = _common.NicDuplex(duplex)
            output_flags = ','.join(flags)
            isup = 'running' in flags
            ret[name] = _common.snicstats(
                isup, duplex, speed, mtu, output_flags
            )
    return ret


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    """The system boot time expressed in seconds since the epoch."""
    return cext.boot_time()


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp, pid = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = _common.suser(user, tty or None, hostname or None, tstamp, pid)
        retlist.append(nt)
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    ls = cext.pids()
    if 0 not in ls:
        # On certain macOS versions pids() C doesn't return PID 0 but
        # "ps" does and the process is querable via sysctl():
        # https://travis-ci.org/giampaolo/psutil/jobs/309619941
        try:
            Process(0).create_time()
            ls.insert(0, 0)
        except NoSuchProcess:
            pass
        except AccessDenied:
            ls.insert(0, 0)
    return ls


pid_exists = _psposix.pid_exists


def is_zombie(pid):
    try:
        st = cext.proc_kinfo_oneshot(pid)[kinfo_proc_map['status']]
        return st == cext.SZOMB
    except OSError:
        return False


def wrap_exceptions(fun):
    """Decorator which translates bare OSError exceptions into
    NoSuchProcess and AccessDenied.
    """

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except ProcessLookupError:
            if is_zombie(self.pid):
                raise ZombieProcess(self.pid, self._name, self._ppid)
            else:
                raise NoSuchProcess(self.pid, self._name)
        except PermissionError:
            raise AccessDenied(self.pid, self._name)

    return wrapper


class Process:
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    @wrap_exceptions
    @memoize_when_activated
    def _get_kinfo_proc(self):
        # Note: should work with all PIDs without permission issues.
        ret = cext.proc_kinfo_oneshot(self.pid)
        assert len(ret) == len(kinfo_proc_map)
        return ret

    @wrap_exceptions
    @memoize_when_activated
    def _get_pidtaskinfo(self):
        # Note: should work for PIDs owned by user only.
        ret = cext.proc_pidtaskinfo_oneshot(self.pid)
        assert len(ret) == len(pidtaskinfo_map)
        return ret

    def oneshot_enter(self):
        self._get_kinfo_proc.cache_activate(self)
        self._get_pidtaskinfo.cache_activate(self)

    def oneshot_exit(self):
        self._get_kinfo_proc.cache_deactivate(self)
        self._get_pidtaskinfo.cache_deactivate(self)

    @wrap_exceptions
    def name(self):
        name = self._get_kinfo_proc()[kinfo_proc_map['name']]
        return name if name is not None else cext.proc_name(self.pid)

    @wrap_exceptions
    def exe(self):
        return cext.proc_exe(self.pid)

    @wrap_exceptions
    def cmdline(self):
        return cext.proc_cmdline(self.pid)

    @wrap_exceptions
    def environ(self):
        return parse_environ_block(cext.proc_environ(self.pid))

    @wrap_exceptions
    def ppid(self):
        self._ppid = self._get_kinfo_proc()[kinfo_proc_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def cwd(self):
        return cext.proc_cwd(self.pid)

    @wrap_exceptions
    def uids(self):
        rawtuple = self._get_kinfo_proc()
        return _common.puids(
            rawtuple[kinfo_proc_map['ruid']],
            rawtuple[kinfo_proc_map['euid']],
            rawtuple[kinfo_proc_map['suid']],
        )

    @wrap_exceptions
    def gids(self):
        rawtuple = self._get_kinfo_proc()
        return _common.puids(
            rawtuple[kinfo_proc_map['rgid']],
            rawtuple[kinfo_proc_map['egid']],
            rawtuple[kinfo_proc_map['sgid']],
        )

    @wrap_exceptions
    def terminal(self):
        tty_nr = self._get_kinfo_proc()[kinfo_proc_map['ttynr']]
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def memory_info(self):
        rawtuple = self._get_pidtaskinfo()
        return pmem(
            rawtuple[pidtaskinfo_map['rss']],
            rawtuple[pidtaskinfo_map['vms']],
            rawtuple[pidtaskinfo_map['pfaults']],
            rawtuple[pidtaskinfo_map['pageins']],
        )

    @wrap_exceptions
    def memory_full_info(self):
        basic_mem = self.memory_info()
        uss = cext.proc_memory_uss(self.pid)
        return pfullmem(*basic_mem + (uss,))

    @wrap_exceptions
    def cpu_times(self):
        rawtuple = self._get_pidtaskinfo()
        return _common.pcputimes(
            rawtuple[pidtaskinfo_map['cpuutime']],
            rawtuple[pidtaskinfo_map['cpustime']],
            # children user / system times are not retrievable (set to 0)
            0.0,
            0.0,
        )

    @wrap_exceptions
    def create_time(self):
        return self._get_kinfo_proc()[kinfo_proc_map['ctime']]

    @wrap_exceptions
    def num_ctx_switches(self):
        # Unvoluntary value seems not to be available;
        # getrusage() numbers seems to confirm this theory.
        # We set it to 0.
        vol = self._get_pidtaskinfo()[pidtaskinfo_map['volctxsw']]
        return _common.pctxsw(vol, 0)

    @wrap_exceptions
    def num_threads(self):
        return self._get_pidtaskinfo()[pidtaskinfo_map['numthreads']]

    @wrap_exceptions
    def open_files(self):
        if self.pid == 0:
            return []
        files = []
        rawlist = cext.proc_open_files(self.pid)
        for path, fd in rawlist:
            if isfile_strict(path):
                ntuple = _common.popenfile(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def connections(self, kind='inet'):
        if kind not in conn_tmap:
            raise ValueError(
                "invalid %r kind argument; choose between %s"
                % (kind, ', '.join([repr(x) for x in conn_tmap]))
            )
        families, types = conn_tmap[kind]
        rawlist = cext.proc_connections(self.pid, families, types)
        ret = []
        for item in rawlist:
            fd, fam, type, laddr, raddr, status = item
            nt = conn_to_ntuple(
                fd, fam, type, laddr, raddr, status, TCP_STATUSES
            )
            ret.append(nt)
        return ret

    @wrap_exceptions
    def num_fds(self):
        if self.pid == 0:
            return 0
        return cext.proc_num_fds(self.pid)

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def nice_get(self):
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def status(self):
        code = self._get_kinfo_proc()[kinfo_proc_map['status']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    @wrap_exceptions
    def threads(self):
        rawlist = cext.proc_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = _common.pthread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist