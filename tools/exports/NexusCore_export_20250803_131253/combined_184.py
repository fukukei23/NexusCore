
# === NexusCore/tools\exports\export_20250803_114325\combined_214.py ===

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\client\error.py ===
"""Exception and error handling.

This contains the core exceptions that the implementations should raise
as well as the IActiveScriptError interface code.
"""

from __future__ import annotations

import re
import traceback
import warnings
from types import TracebackType
from typing import TYPE_CHECKING

import pythoncom
import win32com.server.util
import winerror
from win32com.axscript import axscript
from win32com.server.exception import COMException

if TYPE_CHECKING:
    from win32comext.axscript.client.debug import DebugManager
    from win32comext.axscript.client.framework import AXScriptCodeBlock, COMScript
    from win32comext.axscript.server.axsite import AXSite

debugging = 0


def FormatForAX(text: str):
    """Format a string suitable for an AX Host"""
    # Replace all " with ', so it works OK in HTML (ie, ASP)
    return ExpandTabs(AddCR(text))


def ExpandTabs(text: str):
    return re.sub(r"\t", "    ", text)


def AddCR(text: str):
    return re.sub(r"\n", "\r\n", text)


class IActiveScriptError:
    """An implementation of IActiveScriptError

    The ActiveX Scripting host calls this client whenever we report
    an exception to it.  This interface provides the exception details
    for the host to report to the user.
    """

    _com_interfaces_ = [axscript.IID_IActiveScriptError]
    _public_methods_ = ["GetSourceLineText", "GetSourcePosition", "GetExceptionInfo"]

    def _query_interface_(self, iid):
        print("IActiveScriptError QI - unknown IID", iid)
        return 0

    def _SetExceptionInfo(self, exc: AXScriptException):
        self.exception = exc

    def GetSourceLineText(self):
        return self.exception.linetext

    def GetSourcePosition(self):
        ctx = self.exception.sourceContext
        # Zero based in the debugger (but our columns are too!)
        return (
            ctx,
            self.exception.lineno + self.exception.startLineNo - 1,
            self.exception.colno,
        )

    def GetExceptionInfo(self):
        return self.exception


class AXScriptException(COMException):
    """A class used as a COM exception.

    Note this has attributes which conform to the standard attributes
    for COM exceptions, plus a few others specific to our IActiveScriptError
    object.
    """

    def __init__(
        self,
        site: COMScript,
        codeBlock: AXScriptCodeBlock | None,
        exc_type: None = None,
        exc_value: BaseException | None = None,
        exc_traceback: None = None,
    ):
        # set properties base class shares via base ctor...
        super().__init__(
            description="Unknown Exception",
            scode=winerror.DISP_E_EXCEPTION,
            source="Python ActiveX Scripting Engine",
        )

        if exc_type is not None or exc_traceback is not None:
            warnings.warn(
                "`exc_type` and `exc_traceback` were redundant and are now unused.",
                category=DeprecationWarning,
            )

        # And my other values...
        if codeBlock is None:
            self.sourceContext = 0
            self.startLineNo = 0
        else:
            self.sourceContext = codeBlock.sourceContextCookie
            self.startLineNo = codeBlock.startLineNumber
        self.linetext = ""

        self.__BuildFromException(site, exc_value)

    def __BuildFromException(self, site: COMScript, value: BaseException | None):
        if debugging:
            import linecache

            linecache.clearcache()
        try:
            if isinstance(value, SyntaxError):
                self._BuildFromSyntaxError(value)
            else:
                self._BuildFromOther(site, value)
        except:  # Error extracting traceback info!!!
            traceback.print_exc()
            # re-raise.
            raise

    def _BuildFromSyntaxError(self, exc: SyntaxError):
        # Some of these may be None, which upsets us!
        msg = exc.msg or "Unknown Error"
        offset = exc.offset or 0
        line = exc.text or ""
        lineno = exc.lineno or 0

        self.description = FormatForAX(msg)
        self.lineno = lineno
        self.colno = offset - 1
        self.linetext = ExpandTabs(line.rstrip())

    def _BuildFromOther(self, site: COMScript, value: BaseException | None):
        tb = value.__traceback__ if value else None
        exc_type = type(value) if value else None
        self.colno = -1
        self.lineno = 0
        if debugging:  # Full traceback if debugging.
            list = traceback.format_exception(exc_type, value, tb)
            self.description = ExpandTabs("".join(list))
            return
        # Run down the traceback list, looking for the first "<Script..>"
        # Hide traceback above this.  In addition, keep going down
        # looking for a "_*_" attribute, and below hide these also.
        hide_names = [
            "r_import",
            "r_reload",
            "r_open",
        ]  # hide from these functions down in the traceback.
        tb_top = tb
        while tb_top:
            filename, lineno, name, line = self.ExtractTracebackInfo(tb_top, site)
            if filename[:7] == "<Script":
                break
            tb_top = tb_top.tb_next
        format_items = []
        if tb_top:  # found one.
            tb_look: TracebackType | None = tb_top
            # Look down for our bottom
            while tb_look:
                filename, lineno, name, line = self.ExtractTracebackInfo(tb_look, site)
                if name in hide_names:
                    break
                # We can report a line-number, but not a filename.  Therefore,
                # we return the last line-number we find in one of our script
                # blocks.
                if filename.startswith("<Script"):
                    self.lineno = lineno
                    self.linetext = line
                format_items.append((filename, lineno, name, line))
                tb_look = tb_look.tb_next
        else:
            tb_top = tb

        bits = ["Traceback (most recent call last):\n"]
        bits.extend(traceback.format_list(format_items))
        if isinstance(value, pythoncom.com_error):
            desc = f"{value.strerror} (0x{value.hresult:x})"
            if (
                value.hresult == winerror.DISP_E_EXCEPTION
                and value.excepinfo
                and value.excepinfo[2]
            ):
                desc = value.excepinfo[2]
            bits.append("COM Error: " + desc)
        else:
            bits.extend(traceback.format_exception_only(exc_type, value))

        self.description = ExpandTabs("".join(bits))

    def ExtractTracebackInfo(self, tb: TracebackType, site: COMScript):
        import linecache

        lineno = tb.tb_lineno
        co = tb.tb_frame.f_code
        filename = co.co_filename
        name = co.co_name
        line: str | None = linecache.getline(filename, lineno)
        if not line:
            codeBlock = site.scriptCodeBlocks.get(filename)
            if codeBlock:
                # Note: 'line' will now be unicode.
                line = codeBlock.GetLineNo(lineno)
        if line:
            line = line.strip()
        else:
            line = None
        return filename, lineno, name, line

    def __repr__(self):
        return "AXScriptException Object with description:" + self.description


def ProcessAXScriptException(
    scriptingSite: AXSite,
    debugManager: DebugManager,
    exceptionInstance: AXScriptException,
):
    """General function to handle any exception in AX code

    This function creates an instance of our IActiveScriptError interface, and
    gives it to the host, along with out exception class.  The host will
    likely call back on the IActiveScriptError interface to get the source text
    and other information not normally in COM exceptions.
    """
    # traceback.print_exc()
    instance = IActiveScriptError()
    instance._SetExceptionInfo(exceptionInstance)
    gateway = win32com.server.util.wrap(instance, axscript.IID_IActiveScriptError)
    if debugManager:
        fCallOnError = debugManager.HandleRuntimeError()
        if not fCallOnError:
            return None

    try:
        result = scriptingSite.OnScriptError(gateway)
    except pythoncom.com_error as details:
        print("**OnScriptError failed:", details)
        print(f"Exception description: '{exceptionInstance.description!r}'")
        print(f"Exception text: '{exceptionInstance.linetext!r}'")
        result = winerror.S_FALSE

    if result == winerror.S_OK:
        # If the above  returns NOERROR, it is assumed the error has been
        # correctly registered and the value SCRIPT_E_REPORTED is returned.
        ret = COMException(scode=axscript.SCRIPT_E_REPORTED)
        return ret
    else:
        # The error is taken to be unreported and is propagated up the call stack
        # via the IDispatch::Invoke's EXCEPINFO parameter (hr returned is DISP_E_EXCEPTION.
        return exceptionInstance

# === NexusCore/openenv\Lib\site-packages\contourpy\array.py ===
from __future__ import annotations

from itertools import chain, pairwise
from typing import TYPE_CHECKING

import numpy as np

from contourpy.typecheck import check_code_array, check_offset_array, check_point_array
from contourpy.types import CLOSEPOLY, LINETO, MOVETO, code_dtype, offset_dtype, point_dtype

if TYPE_CHECKING:
    import contourpy._contourpy as cpy


def codes_from_offsets(offsets: cpy.OffsetArray) -> cpy.CodeArray:
    """Determine codes from offsets, assuming they all correspond to closed polygons.
    """
    check_offset_array(offsets)

    n = offsets[-1]
    codes = np.full(n, LINETO, dtype=code_dtype)
    codes[offsets[:-1]] = MOVETO
    codes[offsets[1:] - 1] = CLOSEPOLY
    return codes


def codes_from_offsets_and_points(
    offsets: cpy.OffsetArray,
    points: cpy.PointArray,
) -> cpy.CodeArray:
    """Determine codes from offsets and points, using the equality of the start and end points of
    each line to determine if lines are closed or not.
    """
    check_offset_array(offsets)
    check_point_array(points)

    codes = np.full(len(points), LINETO, dtype=code_dtype)
    codes[offsets[:-1]] = MOVETO

    end_offsets = offsets[1:] - 1
    closed = np.all(points[offsets[:-1]] == points[end_offsets], axis=1)
    codes[end_offsets[closed]] = CLOSEPOLY

    return codes


def codes_from_points(points: cpy.PointArray) -> cpy.CodeArray:
    """Determine codes for a single line, using the equality of the start and end points to
    determine if the line is closed or not.
    """
    check_point_array(points)

    n = len(points)
    codes = np.full(n, LINETO, dtype=code_dtype)
    codes[0] = MOVETO
    if np.all(points[0] == points[-1]):
        codes[-1] = CLOSEPOLY
    return codes


def concat_codes(list_of_codes: list[cpy.CodeArray]) -> cpy.CodeArray:
    """Concatenate a list of codes arrays into a single code array.
    """
    if not list_of_codes:
        raise ValueError("Empty list passed to concat_codes")

    return np.concatenate(list_of_codes, dtype=code_dtype)


def concat_codes_or_none(list_of_codes_or_none: list[cpy.CodeArray | None]) -> cpy.CodeArray | None:
    """Concatenate a list of codes arrays or None into a single code array or None.
    """
    list_of_codes = [codes for codes in list_of_codes_or_none if codes is not None]
    if list_of_codes:
        return concat_codes(list_of_codes)
    else:
        return None


def concat_offsets(list_of_offsets: list[cpy.OffsetArray]) -> cpy.OffsetArray:
    """Concatenate a list of offsets arrays into a single offset array.
    """
    if not list_of_offsets:
        raise ValueError("Empty list passed to concat_offsets")

    n = len(list_of_offsets)
    cumulative = np.cumsum([offsets[-1] for offsets in list_of_offsets], dtype=offset_dtype)
    ret: cpy.OffsetArray = np.concatenate(
        (list_of_offsets[0], *(list_of_offsets[i+1][1:] + cumulative[i] for i in range(n-1))),
        dtype=offset_dtype,
    )
    return ret


def concat_offsets_or_none(
    list_of_offsets_or_none: list[cpy.OffsetArray | None],
) -> cpy.OffsetArray | None:
    """Concatenate a list of offsets arrays or None into a single offset array or None.
    """
    list_of_offsets = [offsets for offsets in list_of_offsets_or_none if offsets is not None]
    if list_of_offsets:
        return concat_offsets(list_of_offsets)
    else:
        return None


def concat_points(list_of_points: list[cpy.PointArray]) -> cpy.PointArray:
    """Concatenate a list of point arrays into a single point array.
    """
    if not list_of_points:
        raise ValueError("Empty list passed to concat_points")

    return np.concatenate(list_of_points, dtype=point_dtype)


def concat_points_or_none(
    list_of_points_or_none: list[cpy.PointArray | None],
) -> cpy.PointArray | None:
    """Concatenate a list of point arrays or None into a single point array or None.
    """
    list_of_points = [points for points in list_of_points_or_none if points is not None]
    if list_of_points:
        return concat_points(list_of_points)
    else:
        return None


def concat_points_or_none_with_nan(
    list_of_points_or_none: list[cpy.PointArray | None],
) -> cpy.PointArray | None:
    """Concatenate a list of points or None into a single point array or None, with NaNs used to
    separate each line.
    """
    list_of_points = [points for points in list_of_points_or_none if points is not None]
    if list_of_points:
        return concat_points_with_nan(list_of_points)
    else:
        return None


def concat_points_with_nan(list_of_points: list[cpy.PointArray]) -> cpy.PointArray:
    """Concatenate a list of points into a single point array with NaNs used to separate each line.
    """
    if not list_of_points:
        raise ValueError("Empty list passed to concat_points_with_nan")

    if len(list_of_points) == 1:
        return list_of_points[0]
    else:
        nan_spacer = np.full((1, 2), np.nan, dtype=point_dtype)
        list_of_points = [list_of_points[0],
                          *list(chain(*((nan_spacer, x) for x in list_of_points[1:])))]
        return concat_points(list_of_points)


def insert_nan_at_offsets(points: cpy.PointArray, offsets: cpy.OffsetArray) -> cpy.PointArray:
    """Insert NaNs into a point array at locations specified by an offset array.
    """
    check_point_array(points)
    check_offset_array(offsets)

    if len(offsets) <= 2:
        return points
    else:
        nan_spacer = np.array([np.nan, np.nan], dtype=point_dtype)
        # Convert offsets to int64 to avoid numpy error when mixing signed and unsigned ints.
        return np.insert(points, offsets[1:-1].astype(np.int64), nan_spacer, axis=0)


def offsets_from_codes(codes: cpy.CodeArray) -> cpy.OffsetArray:
    """Determine offsets from codes using locations of MOVETO codes.
    """
    check_code_array(codes)

    return np.append(np.nonzero(codes == MOVETO)[0], len(codes)).astype(offset_dtype)


def offsets_from_lengths(list_of_points: list[cpy.PointArray]) -> cpy.OffsetArray:
    """Determine offsets from lengths of point arrays.
    """
    if not list_of_points:
        raise ValueError("Empty list passed to offsets_from_lengths")

    return np.cumsum([0] + [len(line) for line in list_of_points], dtype=offset_dtype)


def outer_offsets_from_list_of_codes(list_of_codes: list[cpy.CodeArray]) -> cpy.OffsetArray:
    """Determine outer offsets from codes using locations of MOVETO codes.
    """
    if not list_of_codes:
        raise ValueError("Empty list passed to outer_offsets_from_list_of_codes")

    return np.cumsum([0] + [np.count_nonzero(codes == MOVETO) for codes in list_of_codes],
                     dtype=offset_dtype)


def outer_offsets_from_list_of_offsets(list_of_offsets: list[cpy.OffsetArray]) -> cpy.OffsetArray:
    """Determine outer offsets from a list of offsets.
    """
    if not list_of_offsets:
        raise ValueError("Empty list passed to outer_offsets_from_list_of_offsets")

    return np.cumsum([0] + [len(offsets)-1 for offsets in list_of_offsets], dtype=offset_dtype)


def remove_nan(points: cpy.PointArray) -> tuple[cpy.PointArray, cpy.OffsetArray]:
    """Remove NaN from a points array, also return the offsets corresponding to the NaN removed.
    """
    check_point_array(points)

    nan_offsets = np.nonzero(np.isnan(points[:, 0]))[0]
    if len(nan_offsets) == 0:
        return points, np.array([0, len(points)], dtype=offset_dtype)
    else:
        points = np.delete(points, nan_offsets, axis=0)
        nan_offsets -= np.arange(len(nan_offsets))
        offsets: cpy.OffsetArray = np.empty(len(nan_offsets)+2, dtype=offset_dtype)
        offsets[0] = 0
        offsets[1:-1] = nan_offsets
        offsets[-1] = len(points)
        return points, offsets


def split_codes_by_offsets(codes: cpy.CodeArray, offsets: cpy.OffsetArray) -> list[cpy.CodeArray]:
    """Split a code array at locations specified by an offset array into a list of code arrays.
    """
    check_code_array(codes)
    check_offset_array(offsets)

    if len(offsets) > 2:
        return np.split(codes, offsets[1:-1])
    else:
        return [codes]


def split_points_by_offsets(
    points: cpy.PointArray,
    offsets: cpy.OffsetArray,
) -> list[cpy.PointArray]:
    """Split a point array at locations specified by an offset array into a list of point arrays.
    """
    check_point_array(points)
    check_offset_array(offsets)

    if len(offsets) > 2:
        return np.split(points, offsets[1:-1])
    else:
        return [points]


def split_points_at_nan(points: cpy.PointArray) -> list[cpy.PointArray]:
    """Split a points array at NaNs into a list of point arrays.
    """
    check_point_array(points)

    nan_offsets = np.nonzero(np.isnan(points[:, 0]))[0]
    if len(nan_offsets) == 0:
        return [points]
    else:
        nan_offsets = np.concatenate(([-1], nan_offsets, [len(points)]))
        return [points[s+1:e] for s, e in pairwise(nan_offsets)]

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc7191.py ===
# This file is being contributed to of pyasn1-modules software.
#
# Created by Russ Housley without assistance from the asn1ate tool.
# Modified by Russ Housley to add support for opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# CMS Key Package Receipt and Error Content Types
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc7191.txt

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652

MAX = float('inf')

DistinguishedName = rfc5280.DistinguishedName


# SingleAttribute is the same as Attribute in RFC 5652, except that the
# attrValues SET must have one and only one member

class AttributeValue(univ.Any):
    pass


class AttributeValues(univ.SetOf):
    pass

AttributeValues.componentType = AttributeValue()
AttributeValues.sizeSpec = univ.Set.sizeSpec + constraint.ValueSizeConstraint(1, 1)


class SingleAttribute(univ.Sequence):
    pass

SingleAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', univ.ObjectIdentifier()),
    namedtype.NamedType('attrValues', AttributeValues(),
        openType=opentype.OpenType('attrType', rfc5652.cmsAttributesMap)
    )
)


# SIR Entity Name

class SIREntityNameType(univ.ObjectIdentifier):
    pass


class SIREntityNameValue(univ.Any):
    pass


class SIREntityName(univ.Sequence):
    pass

SIREntityName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('sirenType', SIREntityNameType()),
    namedtype.NamedType('sirenValue', univ.OctetString())
    # CONTAINING the DER-encoded SIREntityNameValue
)


class SIREntityNames(univ.SequenceOf):
    pass

SIREntityNames.componentType = SIREntityName()
SIREntityNames.sizeSpec=constraint.ValueSizeConstraint(1, MAX)


id_dn = univ.ObjectIdentifier('2.16.840.1.101.2.1.16.0')


class siren_dn(SIREntityName):
    def __init__(self):
        SIREntityName.__init__(self)
        self['sirenType'] = id_dn


# Key Package Error CMS Content Type

class EnumeratedErrorCode(univ.Enumerated):
    pass

# Error codes with values <= 33 are aligned with RFC 5934
EnumeratedErrorCode.namedValues = namedval.NamedValues(
    ('decodeFailure', 1),
    ('badContentInfo', 2),
    ('badSignedData', 3),
    ('badEncapContent', 4),
    ('badCertificate', 5),
    ('badSignerInfo', 6),
    ('badSignedAttrs', 7),
    ('badUnsignedAttrs', 8),
    ('missingContent', 9),
    ('noTrustAnchor', 10),
    ('notAuthorized', 11),
    ('badDigestAlgorithm', 12),
    ('badSignatureAlgorithm', 13),
    ('unsupportedKeySize', 14),
    ('unsupportedParameters', 15),
    ('signatureFailure', 16),
    ('insufficientMemory', 17),
    ('incorrectTarget', 23),
    ('missingSignature', 29),
    ('resourcesBusy', 30),
    ('versionNumberMismatch', 31),
    ('revokedCertificate', 33),
    ('ambiguousDecrypt', 60),
    ('noDecryptKey', 61),
    ('badEncryptedData', 62),
    ('badEnvelopedData', 63),
    ('badAuthenticatedData', 64),
    ('badAuthEnvelopedData', 65),
    ('badKeyAgreeRecipientInfo', 66),
    ('badKEKRecipientInfo', 67),
    ('badEncryptContent', 68),
    ('badEncryptAlgorithm', 69),
    ('missingCiphertext', 70),
    ('decryptFailure', 71),
    ('badMACAlgorithm', 72),
    ('badAuthAttrs', 73),
    ('badUnauthAttrs', 74),
    ('invalidMAC', 75),
    ('mismatchedDigestAlg', 76),
    ('missingCertificate', 77),
    ('tooManySigners', 78),
    ('missingSignedAttributes', 79),
    ('derEncodingNotUsed', 80),
    ('missingContentHints', 81),
    ('invalidAttributeLocation', 82),
    ('badMessageDigest', 83),
    ('badKeyPackage', 84),
    ('badAttributes', 85),
    ('attributeComparisonFailure', 86),
    ('unsupportedSymmetricKeyPackage', 87),
    ('unsupportedAsymmetricKeyPackage', 88),
    ('constraintViolation', 89),
    ('ambiguousDefaultValue', 90),
    ('noMatchingRecipientInfo', 91),
    ('unsupportedKeyWrapAlgorithm', 92),
    ('badKeyTransRecipientInfo', 93),
    ('other', 127)
)


class ErrorCodeChoice(univ.Choice):
    pass

ErrorCodeChoice.componentType = namedtype.NamedTypes(
    namedtype.NamedType('enum', EnumeratedErrorCode()),
    namedtype.NamedType('oid', univ.ObjectIdentifier())
)


class KeyPkgID(univ.OctetString):
    pass


class KeyPkgIdentifier(univ.Choice):
    pass

KeyPkgIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pkgID', KeyPkgID()),
    namedtype.NamedType('attribute', SingleAttribute())
)


class KeyPkgVersion(univ.Integer):
    pass


KeyPkgVersion.namedValues = namedval.NamedValues(
    ('v1', 1),
    ('v2', 2)
)

KeyPkgVersion.subtypeSpec = constraint.ValueRangeConstraint(1, 65535)


id_ct_KP_keyPackageError = univ.ObjectIdentifier('2.16.840.1.101.2.1.2.78.6')

class KeyPackageError(univ.Sequence):
    pass

KeyPackageError.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', KeyPkgVersion().subtype(value='v2')),
    namedtype.OptionalNamedType('errorOf', KeyPkgIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('errorBy', SIREntityName()),
    namedtype.NamedType('errorCode', ErrorCodeChoice())
)


# Key Package Receipt CMS Content Type

id_ct_KP_keyPackageReceipt = univ.ObjectIdentifier('2.16.840.1.101.2.1.2.78.3')

class KeyPackageReceipt(univ.Sequence):
    pass

KeyPackageReceipt.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', KeyPkgVersion().subtype(value='v2')),
    namedtype.NamedType('receiptOf', KeyPkgIdentifier()),
    namedtype.NamedType('receivedBy', SIREntityName())
)


# Key Package Receipt Request Attribute

class KeyPkgReceiptReq(univ.Sequence):
    pass

KeyPkgReceiptReq.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('encryptReceipt', univ.Boolean().subtype(value=0)),
    namedtype.OptionalNamedType('receiptsFrom', SIREntityNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('receiptsTo', SIREntityNames())
)


id_aa_KP_keyPkgIdAndReceiptReq = univ.ObjectIdentifier('2.16.840.1.101.2.1.5.65')

class KeyPkgIdentifierAndReceiptReq(univ.Sequence):
    pass

KeyPkgIdentifierAndReceiptReq.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pkgID', KeyPkgID()),
    namedtype.OptionalNamedType('receiptReq', KeyPkgReceiptReq())
)


# Map of Attribute Type OIDs to Attributes are added to
# the ones that are in rfc5652.py

_cmsAttributesMapUpdate = {
    id_aa_KP_keyPkgIdAndReceiptReq: KeyPkgIdentifierAndReceiptReq(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)


# Map of CMC Content Type OIDs to CMC Content Types are added to
# the ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_ct_KP_keyPackageError: KeyPackageError(),
    id_ct_KP_keyPackageReceipt: KeyPackageReceipt(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\setuptools\wheel.py ===
"""Wheels support."""

import contextlib
import email
import functools
import itertools
import os
import posixpath
import re
import zipfile

from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name
from packaging.version import Version as parse_version

import setuptools
from setuptools.archive_util import _unpack_zipfile_obj
from setuptools.command.egg_info import _egg_basename, write_requirements

from ._discovery import extras_from_deps
from ._importlib import metadata
from .unicode_utils import _read_utf8_with_fallback

from distutils.util import get_platform

WHEEL_NAME = re.compile(
    r"""^(?P<project_name>.+?)-(?P<version>\d.*?)
    ((-(?P<build>\d.*?))?-(?P<py_version>.+?)-(?P<abi>.+?)-(?P<platform>.+?)
    )\.whl$""",
    re.VERBOSE,
).match

NAMESPACE_PACKAGE_INIT = "__import__('pkg_resources').declare_namespace(__name__)\n"


@functools.cache
def _get_supported_tags():
    # We calculate the supported tags only once, otherwise calling
    # this method on thousands of wheels takes seconds instead of
    # milliseconds.
    return {(t.interpreter, t.abi, t.platform) for t in sys_tags()}


def unpack(src_dir, dst_dir) -> None:
    """Move everything under `src_dir` to `dst_dir`, and delete the former."""
    for dirpath, dirnames, filenames in os.walk(src_dir):
        subdir = os.path.relpath(dirpath, src_dir)
        for f in filenames:
            src = os.path.join(dirpath, f)
            dst = os.path.join(dst_dir, subdir, f)
            os.renames(src, dst)
        for n, d in reversed(list(enumerate(dirnames))):
            src = os.path.join(dirpath, d)
            dst = os.path.join(dst_dir, subdir, d)
            if not os.path.exists(dst):
                # Directory does not exist in destination,
                # rename it and prune it from os.walk list.
                os.renames(src, dst)
                del dirnames[n]
    # Cleanup.
    for dirpath, dirnames, filenames in os.walk(src_dir, topdown=True):
        assert not filenames
        os.rmdir(dirpath)


@contextlib.contextmanager
def disable_info_traces():
    """
    Temporarily disable info traces.
    """
    from distutils import log

    saved = log.set_threshold(log.WARN)
    try:
        yield
    finally:
        log.set_threshold(saved)


class Wheel:
    def __init__(self, filename) -> None:
        match = WHEEL_NAME(os.path.basename(filename))
        if match is None:
            raise ValueError(f'invalid wheel name: {filename!r}')
        self.filename = filename
        for k, v in match.groupdict().items():
            setattr(self, k, v)

    def tags(self):
        """List tags (py_version, abi, platform) supported by this wheel."""
        return itertools.product(
            self.py_version.split('.'),
            self.abi.split('.'),
            self.platform.split('.'),
        )

    def is_compatible(self):
        """Is the wheel compatible with the current platform?"""
        return next((True for t in self.tags() if t in _get_supported_tags()), False)

    def egg_name(self):
        return (
            _egg_basename(
                self.project_name,
                self.version,
                platform=(None if self.platform == 'any' else get_platform()),
            )
            + ".egg"
        )

    def get_dist_info(self, zf):
        # find the correct name of the .dist-info dir in the wheel file
        for member in zf.namelist():
            dirname = posixpath.dirname(member)
            if dirname.endswith('.dist-info') and canonicalize_name(dirname).startswith(
                canonicalize_name(self.project_name)
            ):
                return dirname
        raise ValueError("unsupported wheel format. .dist-info not found")

    def install_as_egg(self, destination_eggdir) -> None:
        """Install wheel as an egg directory."""
        with zipfile.ZipFile(self.filename) as zf:
            self._install_as_egg(destination_eggdir, zf)

    def _install_as_egg(self, destination_eggdir, zf):
        dist_basename = f'{self.project_name}-{self.version}'
        dist_info = self.get_dist_info(zf)
        dist_data = f'{dist_basename}.data'
        egg_info = os.path.join(destination_eggdir, 'EGG-INFO')

        self._convert_metadata(zf, destination_eggdir, dist_info, egg_info)
        self._move_data_entries(destination_eggdir, dist_data)
        self._fix_namespace_packages(egg_info, destination_eggdir)

    @staticmethod
    def _convert_metadata(zf, destination_eggdir, dist_info, egg_info):
        def get_metadata(name):
            with zf.open(posixpath.join(dist_info, name)) as fp:
                value = fp.read().decode('utf-8')
                return email.parser.Parser().parsestr(value)

        wheel_metadata = get_metadata('WHEEL')
        # Check wheel format version is supported.
        wheel_version = parse_version(wheel_metadata.get('Wheel-Version'))
        wheel_v1 = parse_version('1.0') <= wheel_version < parse_version('2.0dev0')
        if not wheel_v1:
            raise ValueError(f'unsupported wheel format version: {wheel_version}')
        # Extract to target directory.
        _unpack_zipfile_obj(zf, destination_eggdir)
        dist_info = os.path.join(destination_eggdir, dist_info)
        install_requires, extras_require = Wheel._convert_requires(
            destination_eggdir, dist_info
        )
        os.rename(dist_info, egg_info)
        os.rename(
            os.path.join(egg_info, 'METADATA'),
            os.path.join(egg_info, 'PKG-INFO'),
        )
        setup_dist = setuptools.Distribution(
            attrs=dict(
                install_requires=install_requires,
                extras_require=extras_require,
            ),
        )
        with disable_info_traces():
            write_requirements(
                setup_dist.get_command_obj('egg_info'),
                None,
                os.path.join(egg_info, 'requires.txt'),
            )

    @staticmethod
    def _convert_requires(destination_eggdir, dist_info):
        md = metadata.Distribution.at(dist_info).metadata
        deps = md.get_all('Requires-Dist') or []
        reqs = list(map(Requirement, deps))

        extras = extras_from_deps(deps)

        # Note: Evaluate and strip markers now,
        # as it's difficult to convert back from the syntax:
        # foobar; "linux" in sys_platform and extra == 'test'
        def raw_req(req):
            req = Requirement(str(req))
            req.marker = None
            return str(req)

        def eval(req, **env):
            return not req.marker or req.marker.evaluate(env)

        def for_extra(req):
            try:
                markers = req.marker._markers
            except AttributeError:
                markers = ()
            return set(
                marker[2].value
                for marker in markers
                if isinstance(marker, tuple) and marker[0].value == 'extra'
            )

        install_requires = list(
            map(raw_req, filter(eval, itertools.filterfalse(for_extra, reqs)))
        )
        extras_require = {
            extra: list(
                map(
                    raw_req,
                    (req for req in reqs if for_extra(req) and eval(req, extra=extra)),
                )
            )
            for extra in extras
        }
        return install_requires, extras_require

    @staticmethod
    def _move_data_entries(destination_eggdir, dist_data):
        """Move data entries to their correct location."""
        dist_data = os.path.join(destination_eggdir, dist_data)
        dist_data_scripts = os.path.join(dist_data, 'scripts')
        if os.path.exists(dist_data_scripts):
            egg_info_scripts = os.path.join(destination_eggdir, 'EGG-INFO', 'scripts')
            os.mkdir(egg_info_scripts)
            for entry in os.listdir(dist_data_scripts):
                # Remove bytecode, as it's not properly handled
                # during easy_install scripts install phase.
                if entry.endswith('.pyc'):
                    os.unlink(os.path.join(dist_data_scripts, entry))
                else:
                    os.rename(
                        os.path.join(dist_data_scripts, entry),
                        os.path.join(egg_info_scripts, entry),
                    )
            os.rmdir(dist_data_scripts)
        for subdir in filter(
            os.path.exists,
            (
                os.path.join(dist_data, d)
                for d in ('data', 'headers', 'purelib', 'platlib')
            ),
        ):
            unpack(subdir, destination_eggdir)
        if os.path.exists(dist_data):
            os.rmdir(dist_data)

    @staticmethod
    def _fix_namespace_packages(egg_info, destination_eggdir):
        namespace_packages = os.path.join(egg_info, 'namespace_packages.txt')
        if os.path.exists(namespace_packages):
            namespace_packages = _read_utf8_with_fallback(namespace_packages).split()

            for mod in namespace_packages:
                mod_dir = os.path.join(destination_eggdir, *mod.split('.'))
                mod_init = os.path.join(mod_dir, '__init__.py')
                if not os.path.exists(mod_dir):
                    os.mkdir(mod_dir)
                if not os.path.exists(mod_init):
                    with open(mod_init, 'w', encoding="utf-8") as fp:
                        fp.write(NAMESPACE_PACKAGE_INIT)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\macRes.py ===
from io import BytesIO
import struct
from fontTools.misc import sstruct
from fontTools.misc.textTools import bytesjoin, tostr
from collections import OrderedDict
from collections.abc import MutableMapping


class ResourceError(Exception):
    pass


class ResourceReader(MutableMapping):
    """Reader for Mac OS resource forks.

    Parses a resource fork and returns resources according to their type.
    If run on OS X, this will open the resource fork in the filesystem.
    Otherwise, it will open the file itself and attempt to read it as
    though it were a resource fork.

    The returned object can be indexed by type and iterated over,
    returning in each case a list of py:class:`Resource` objects
    representing all the resources of a certain type.

    """

    def __init__(self, fileOrPath):
        """Open a file

        Args:
                fileOrPath: Either an object supporting a ``read`` method, an
                        ``os.PathLike`` object, or a string.
        """
        self._resources = OrderedDict()
        if hasattr(fileOrPath, "read"):
            self.file = fileOrPath
        else:
            try:
                # try reading from the resource fork (only works on OS X)
                self.file = self.openResourceFork(fileOrPath)
                self._readFile()
                return
            except (ResourceError, IOError):
                # if it fails, use the data fork
                self.file = self.openDataFork(fileOrPath)
        self._readFile()

    @staticmethod
    def openResourceFork(path):
        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()
        with open(path + "/..namedfork/rsrc", "rb") as resfork:
            data = resfork.read()
        infile = BytesIO(data)
        infile.name = path
        return infile

    @staticmethod
    def openDataFork(path):
        with open(path, "rb") as datafork:
            data = datafork.read()
        infile = BytesIO(data)
        infile.name = path
        return infile

    def _readFile(self):
        self._readHeaderAndMap()
        self._readTypeList()

    def _read(self, numBytes, offset=None):
        if offset is not None:
            try:
                self.file.seek(offset)
            except OverflowError:
                raise ResourceError("Failed to seek offset ('offset' is too large)")
            if self.file.tell() != offset:
                raise ResourceError("Failed to seek offset (reached EOF)")
        try:
            data = self.file.read(numBytes)
        except OverflowError:
            raise ResourceError("Cannot read resource ('numBytes' is too large)")
        if len(data) != numBytes:
            raise ResourceError("Cannot read resource (not enough data)")
        return data

    def _readHeaderAndMap(self):
        self.file.seek(0)
        headerData = self._read(ResourceForkHeaderSize)
        sstruct.unpack(ResourceForkHeader, headerData, self)
        # seek to resource map, skip reserved
        mapOffset = self.mapOffset + 22
        resourceMapData = self._read(ResourceMapHeaderSize, mapOffset)
        sstruct.unpack(ResourceMapHeader, resourceMapData, self)
        self.absTypeListOffset = self.mapOffset + self.typeListOffset
        self.absNameListOffset = self.mapOffset + self.nameListOffset

    def _readTypeList(self):
        absTypeListOffset = self.absTypeListOffset
        numTypesData = self._read(2, absTypeListOffset)
        (self.numTypes,) = struct.unpack(">H", numTypesData)
        absTypeListOffset2 = absTypeListOffset + 2
        for i in range(self.numTypes + 1):
            resTypeItemOffset = absTypeListOffset2 + ResourceTypeItemSize * i
            resTypeItemData = self._read(ResourceTypeItemSize, resTypeItemOffset)
            item = sstruct.unpack(ResourceTypeItem, resTypeItemData)
            resType = tostr(item["type"], encoding="mac-roman")
            refListOffset = absTypeListOffset + item["refListOffset"]
            numRes = item["numRes"] + 1
            resources = self._readReferenceList(resType, refListOffset, numRes)
            self._resources[resType] = resources

    def _readReferenceList(self, resType, refListOffset, numRes):
        resources = []
        for i in range(numRes):
            refOffset = refListOffset + ResourceRefItemSize * i
            refData = self._read(ResourceRefItemSize, refOffset)
            res = Resource(resType)
            res.decompile(refData, self)
            resources.append(res)
        return resources

    def __getitem__(self, resType):
        return self._resources[resType]

    def __delitem__(self, resType):
        del self._resources[resType]

    def __setitem__(self, resType, resources):
        self._resources[resType] = resources

    def __len__(self):
        return len(self._resources)

    def __iter__(self):
        return iter(self._resources)

    def keys(self):
        return self._resources.keys()

    @property
    def types(self):
        """A list of the types of resources in the resource fork."""
        return list(self._resources.keys())

    def countResources(self, resType):
        """Return the number of resources of a given type."""
        try:
            return len(self[resType])
        except KeyError:
            return 0

    def getIndices(self, resType):
        """Returns a list of indices of resources of a given type."""
        numRes = self.countResources(resType)
        if numRes:
            return list(range(1, numRes + 1))
        else:
            return []

    def getNames(self, resType):
        """Return list of names of all resources of a given type."""
        return [res.name for res in self.get(resType, []) if res.name is not None]

    def getIndResource(self, resType, index):
        """Return resource of given type located at an index ranging from 1
        to the number of resources for that type, or None if not found.
        """
        if index < 1:
            return None
        try:
            res = self[resType][index - 1]
        except (KeyError, IndexError):
            return None
        return res

    def getNamedResource(self, resType, name):
        """Return the named resource of given type, else return None."""
        name = tostr(name, encoding="mac-roman")
        for res in self.get(resType, []):
            if res.name == name:
                return res
        return None

    def close(self):
        if not self.file.closed:
            self.file.close()


class Resource(object):
    """Represents a resource stored within a resource fork.

    Attributes:
            type: resource type.
            data: resource data.
            id: ID.
            name: resource name.
            attr: attributes.
    """

    def __init__(
        self, resType=None, resData=None, resID=None, resName=None, resAttr=None
    ):
        self.type = resType
        self.data = resData
        self.id = resID
        self.name = resName
        self.attr = resAttr

    def decompile(self, refData, reader):
        sstruct.unpack(ResourceRefItem, refData, self)
        # interpret 3-byte dataOffset as (padded) ULONG to unpack it with struct
        (self.dataOffset,) = struct.unpack(">L", bytesjoin([b"\0", self.dataOffset]))
        absDataOffset = reader.dataOffset + self.dataOffset
        (dataLength,) = struct.unpack(">L", reader._read(4, absDataOffset))
        self.data = reader._read(dataLength)
        if self.nameOffset == -1:
            return
        absNameOffset = reader.absNameListOffset + self.nameOffset
        (nameLength,) = struct.unpack("B", reader._read(1, absNameOffset))
        (name,) = struct.unpack(">%ss" % nameLength, reader._read(nameLength))
        self.name = tostr(name, encoding="mac-roman")


ResourceForkHeader = """
		> # big endian
		dataOffset:     L
		mapOffset:      L
		dataLen:        L
		mapLen:         L
"""

ResourceForkHeaderSize = sstruct.calcsize(ResourceForkHeader)

ResourceMapHeader = """
		> # big endian
		attr:              H
		typeListOffset:    H
		nameListOffset:    H
"""

ResourceMapHeaderSize = sstruct.calcsize(ResourceMapHeader)

ResourceTypeItem = """
		> # big endian
		type:              4s
		numRes:            H
		refListOffset:     H
"""

ResourceTypeItemSize = sstruct.calcsize(ResourceTypeItem)

ResourceRefItem = """
		> # big endian
		id:                h
		nameOffset:        h
		attr:              B
		dataOffset:        3s
		reserved:          L
"""

ResourceRefItemSize = sstruct.calcsize(ResourceRefItem)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_f_v_a_r.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
)
from fontTools.misc.textTools import Tag, bytesjoin, safeEval
from fontTools.ttLib import TTLibError
from . import DefaultTable
import struct


# Apple's documentation of 'fvar':
# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6fvar.html

FVAR_HEADER_FORMAT = """
    > # big endian
    version:        L
    offsetToData:   H
    countSizePairs: H
    axisCount:      H
    axisSize:       H
    instanceCount:  H
    instanceSize:   H
"""

FVAR_AXIS_FORMAT = """
    > # big endian
    axisTag:        4s
    minValue:       16.16F
    defaultValue:   16.16F
    maxValue:       16.16F
    flags:          H
    axisNameID:         H
"""

FVAR_INSTANCE_FORMAT = """
    > # big endian
    subfamilyNameID:     H
    flags:      H
"""


class table__f_v_a_r(DefaultTable.DefaultTable):
    """FonT Variations table

    The ``fvar`` table contains records of the variation axes and of the
    named instances in a variable font.

    See also https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6fvar.html
    """

    dependencies = ["name"]

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.axes = []
        self.instances = []

    def compile(self, ttFont):
        instanceSize = sstruct.calcsize(FVAR_INSTANCE_FORMAT) + (len(self.axes) * 4)
        includePostScriptNames = any(
            instance.postscriptNameID != 0xFFFF for instance in self.instances
        )
        if includePostScriptNames:
            instanceSize += 2
        header = {
            "version": 0x00010000,
            "offsetToData": sstruct.calcsize(FVAR_HEADER_FORMAT),
            "countSizePairs": 2,
            "axisCount": len(self.axes),
            "axisSize": sstruct.calcsize(FVAR_AXIS_FORMAT),
            "instanceCount": len(self.instances),
            "instanceSize": instanceSize,
        }
        result = [sstruct.pack(FVAR_HEADER_FORMAT, header)]
        result.extend([axis.compile() for axis in self.axes])
        axisTags = [axis.axisTag for axis in self.axes]
        for instance in self.instances:
            result.append(instance.compile(axisTags, includePostScriptNames))
        return bytesjoin(result)

    def decompile(self, data, ttFont):
        header = {}
        headerSize = sstruct.calcsize(FVAR_HEADER_FORMAT)
        header = sstruct.unpack(FVAR_HEADER_FORMAT, data[0:headerSize])
        if header["version"] != 0x00010000:
            raise TTLibError("unsupported 'fvar' version %04x" % header["version"])
        pos = header["offsetToData"]
        axisSize = header["axisSize"]
        for _ in range(header["axisCount"]):
            axis = Axis()
            axis.decompile(data[pos : pos + axisSize])
            self.axes.append(axis)
            pos += axisSize
        instanceSize = header["instanceSize"]
        axisTags = [axis.axisTag for axis in self.axes]
        for _ in range(header["instanceCount"]):
            instance = NamedInstance()
            instance.decompile(data[pos : pos + instanceSize], axisTags)
            self.instances.append(instance)
            pos += instanceSize

    def toXML(self, writer, ttFont):
        for axis in self.axes:
            axis.toXML(writer, ttFont)
        for instance in self.instances:
            instance.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "Axis":
            axis = Axis()
            axis.fromXML(name, attrs, content, ttFont)
            self.axes.append(axis)
        elif name == "NamedInstance":
            instance = NamedInstance()
            instance.fromXML(name, attrs, content, ttFont)
            self.instances.append(instance)

    def getAxes(self):
        return {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in self.axes}


class Axis(object):
    def __init__(self):
        self.axisTag = None
        self.axisNameID = 0
        self.flags = 0
        self.minValue = -1.0
        self.defaultValue = 0.0
        self.maxValue = 1.0

    def compile(self):
        return sstruct.pack(FVAR_AXIS_FORMAT, self)

    def decompile(self, data):
        sstruct.unpack2(FVAR_AXIS_FORMAT, data, self)

    def toXML(self, writer, ttFont):
        name = (
            ttFont["name"].getDebugName(self.axisNameID) if "name" in ttFont else None
        )
        if name is not None:
            writer.newline()
            writer.comment(name)
            writer.newline()
        writer.begintag("Axis")
        writer.newline()
        for tag, value in [
            ("AxisTag", self.axisTag),
            ("Flags", "0x%X" % self.flags),
            ("MinValue", fl2str(self.minValue, 16)),
            ("DefaultValue", fl2str(self.defaultValue, 16)),
            ("MaxValue", fl2str(self.maxValue, 16)),
            ("AxisNameID", str(self.axisNameID)),
        ]:
            writer.begintag(tag)
            writer.write(value)
            writer.endtag(tag)
            writer.newline()
        writer.endtag("Axis")
        writer.newline()

    def fromXML(self, name, _attrs, content, ttFont):
        assert name == "Axis"
        for tag, _, value in filter(lambda t: type(t) is tuple, content):
            value = "".join(value)
            if tag == "AxisTag":
                self.axisTag = Tag(value)
            elif tag in {"Flags", "MinValue", "DefaultValue", "MaxValue", "AxisNameID"}:
                setattr(
                    self,
                    tag[0].lower() + tag[1:],
                    str2fl(value, 16) if tag.endswith("Value") else safeEval(value),
                )


class NamedInstance(object):
    def __init__(self):
        self.subfamilyNameID = 0
        self.postscriptNameID = 0xFFFF
        self.flags = 0
        self.coordinates = {}

    def compile(self, axisTags, includePostScriptName):
        result = [sstruct.pack(FVAR_INSTANCE_FORMAT, self)]
        for axis in axisTags:
            fixedCoord = fl2fi(self.coordinates[axis], 16)
            result.append(struct.pack(">l", fixedCoord))
        if includePostScriptName:
            result.append(struct.pack(">H", self.postscriptNameID))
        return bytesjoin(result)

    def decompile(self, data, axisTags):
        sstruct.unpack2(FVAR_INSTANCE_FORMAT, data, self)
        pos = sstruct.calcsize(FVAR_INSTANCE_FORMAT)
        for axis in axisTags:
            value = struct.unpack(">l", data[pos : pos + 4])[0]
            self.coordinates[axis] = fi2fl(value, 16)
            pos += 4
        if pos + 2 <= len(data):
            self.postscriptNameID = struct.unpack(">H", data[pos : pos + 2])[0]
        else:
            self.postscriptNameID = 0xFFFF

    def toXML(self, writer, ttFont):
        name = (
            ttFont["name"].getDebugName(self.subfamilyNameID)
            if "name" in ttFont
            else None
        )
        if name is not None:
            writer.newline()
            writer.comment(name)
            writer.newline()
        psname = (
            ttFont["name"].getDebugName(self.postscriptNameID)
            if "name" in ttFont
            else None
        )
        if psname is not None:
            writer.comment("PostScript: " + psname)
            writer.newline()
        if self.postscriptNameID == 0xFFFF:
            writer.begintag(
                "NamedInstance",
                flags=("0x%X" % self.flags),
                subfamilyNameID=self.subfamilyNameID,
            )
        else:
            writer.begintag(
                "NamedInstance",
                flags=("0x%X" % self.flags),
                subfamilyNameID=self.subfamilyNameID,
                postscriptNameID=self.postscriptNameID,
            )
        writer.newline()
        for axis in ttFont["fvar"].axes:
            writer.simpletag(
                "coord",
                axis=axis.axisTag,
                value=fl2str(self.coordinates[axis.axisTag], 16),
            )
            writer.newline()
        writer.endtag("NamedInstance")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        assert name == "NamedInstance"
        self.subfamilyNameID = safeEval(attrs["subfamilyNameID"])
        self.flags = safeEval(attrs.get("flags", "0"))
        if "postscriptNameID" in attrs:
            self.postscriptNameID = safeEval(attrs["postscriptNameID"])
        else:
            self.postscriptNameID = 0xFFFF

        for tag, elementAttrs, _ in filter(lambda t: type(t) is tuple, content):
            if tag == "coord":
                value = str2fl(elementAttrs["value"], 16)
                self.coordinates[elementAttrs["axis"]] = value

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\base_routing_strategy.py ===
"""
Base class across routing strategies to abstract commmon functions like batch incrementing redis
"""

import asyncio
from abc import ABC
from typing import Dict, List, Optional, Set, Tuple, Union

from litellm._logging import verbose_router_logger
from litellm.caching.caching import DualCache
from litellm.caching.redis_cache import RedisPipelineIncrementOperation
from litellm.constants import DEFAULT_REDIS_SYNC_INTERVAL


class BaseRoutingStrategy(ABC):
    def __init__(
        self,
        dual_cache: DualCache,
        should_batch_redis_writes: bool,
        default_sync_interval: Optional[Union[int, float]],
    ):
        self.dual_cache = dual_cache
        self.redis_increment_operation_queue: List[RedisPipelineIncrementOperation] = []
        self._sync_task: Optional[asyncio.Task[None]] = None
        if should_batch_redis_writes:
            self.setup_sync_task(default_sync_interval)

        self.in_memory_keys_to_update: set[
            str
        ] = set()  # Set with max size of 1000 keys

    def setup_sync_task(self, default_sync_interval: Optional[Union[int, float]]):
        """Setup the sync task in a way that's compatible with FastAPI"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._sync_task = loop.create_task(
            self.periodic_sync_in_memory_spend_with_redis(
                default_sync_interval=default_sync_interval
            )
        )

    async def cleanup(self):
        """Cleanup method to be called when shutting down"""
        if self._sync_task is not None:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

    async def _increment_value_list_in_current_window(
        self, increment_list: List[Tuple[str, int]], ttl: int
    ) -> List[float]:
        """
        Increment a list of values in the current window
        """
        results = []
        for key, value in increment_list:
            result = await self._increment_value_in_current_window(
                key=key, value=value, ttl=ttl
            )
            results.append(result)
        return results

    async def _increment_value_in_current_window(
        self, key: str, value: Union[int, float], ttl: int
    ):
        """
        Increment spend within existing budget window

        Runs once the budget start time exists in Redis Cache (on the 2nd and subsequent requests to the same provider)

        - Increments the spend in memory cache (so spend instantly updated in memory)
        - Queues the increment operation to Redis Pipeline (using batched pipeline to optimize performance. Using Redis for multi instance environment of LiteLLM)
        """
        result = await self.dual_cache.in_memory_cache.async_increment(
            key=key,
            value=value,
            ttl=ttl,
        )
        increment_op = RedisPipelineIncrementOperation(
            key=key,
            increment_value=value,
            ttl=ttl,
        )

        self.redis_increment_operation_queue.append(increment_op)
        self.add_to_in_memory_keys_to_update(key=key)
        return result

    async def periodic_sync_in_memory_spend_with_redis(
        self, default_sync_interval: Optional[Union[int, float]]
    ):
        """
        Handler that triggers sync_in_memory_spend_with_redis every DEFAULT_REDIS_SYNC_INTERVAL seconds

        Required for multi-instance environment usage of provider budgets
        """
        default_sync_interval = default_sync_interval or DEFAULT_REDIS_SYNC_INTERVAL
        while True:
            try:
                await self._sync_in_memory_spend_with_redis()
                await asyncio.sleep(
                    default_sync_interval
                )  # Wait for DEFAULT_REDIS_SYNC_INTERVAL seconds before next sync
            except Exception as e:
                verbose_router_logger.error(f"Error in periodic sync task: {str(e)}")
                await asyncio.sleep(
                    default_sync_interval
                )  # Still wait DEFAULT_REDIS_SYNC_INTERVAL seconds on error before retrying

    async def _push_in_memory_increments_to_redis(self):
        """
        How this works:
        - async_log_success_event collects all provider spend increments in `redis_increment_operation_queue`
        - This function compresses multiple increments for the same key into a single operation
        - Then pushes all increments to Redis in a batched pipeline to optimize performance

        Only runs if Redis is initialized
        """
        try:
            if not self.dual_cache.redis_cache:
                return  # Redis is not initialized

            if len(self.redis_increment_operation_queue) > 0:
                # Compress operations for the same key
                compressed_ops: Dict[str, RedisPipelineIncrementOperation] = {}
                ops_to_remove = []
                for idx, op in enumerate(self.redis_increment_operation_queue):
                    if op["key"] in compressed_ops:
                        # Add to existing increment
                        compressed_ops[op["key"]]["increment_value"] += op[
                            "increment_value"
                        ]
                    else:
                        compressed_ops[op["key"]] = op

                    ops_to_remove.append(idx)

                # Convert back to list
                compressed_queue = list(compressed_ops.values())

                increment_result = (
                    await self.dual_cache.redis_cache.async_increment_pipeline(
                        increment_list=compressed_queue,
                    )
                )

                self.redis_increment_operation_queue = [
                    op
                    for idx, op in enumerate(self.redis_increment_operation_queue)
                    if idx not in ops_to_remove
                ]

                if increment_result is not None:
                    return_result = {
                        key["key"]: op
                        for key, op in zip(compressed_queue, increment_result)
                    }
                else:
                    return_result = {}
                return return_result

        except Exception as e:
            verbose_router_logger.error(
                f"Error syncing in-memory cache with Redis: {str(e)}"
            )
            self.redis_increment_operation_queue = []

    def add_to_in_memory_keys_to_update(self, key: str):
        self.in_memory_keys_to_update.add(key)

    def get_key_pattern_to_sync(self) -> Optional[str]:
        """
        Get the key pattern to sync
        """
        return None

    def get_in_memory_keys_to_update(self) -> Set[str]:
        return self.in_memory_keys_to_update

    def get_and_reset_in_memory_keys_to_update(self) -> Set[str]:
        """Atomic get and reset in-memory keys to update"""
        keys = self.in_memory_keys_to_update
        self.in_memory_keys_to_update = set()
        return keys

    def reset_in_memory_keys_to_update(self):
        self.in_memory_keys_to_update = set()

    async def _sync_in_memory_spend_with_redis(self):
        """
        Ensures in-memory cache is updated with latest Redis values for all provider spends.

        Why Do we need this?
        - Optimization to hit sub 100ms latency. Performance was impacted when redis was used for read/write per request
        - Use provider budgets in multi-instance environment, we use Redis to sync spend across all instances

        What this does:
        1. Push all provider spend increments to Redis
        2. Fetch all current provider spend from Redis to update in-memory cache
        """

        try:
            # No need to sync if Redis cache is not initialized
            if self.dual_cache.redis_cache is None:
                return

            # 2. Fetch all current provider spend from Redis to update in-memory cache
            cache_keys = (
                self.get_in_memory_keys_to_update()
            )  # if no pattern OR redis cache does not support scan_iter, use in-memory keys

            cache_keys_list = list(cache_keys)

            # 1. Snapshot in-memory before
            in_memory_before_dict = {}
            in_memory_before = (
                await self.dual_cache.in_memory_cache.async_batch_get_cache(
                    keys=cache_keys_list
                )
            )
            for k, v in zip(cache_keys_list, in_memory_before):
                in_memory_before_dict[k] = float(v or 0)

            # 1. Push all provider spend increments to Redis
            redis_values = await self._push_in_memory_increments_to_redis()
            if redis_values is None:
                return

            # 4. Merge
            for key in cache_keys_list:
                redis_val = float(redis_values.get(key, 0) or 0)
                before = float(in_memory_before_dict.get(key, 0) or 0)
                after = float(
                    await self.dual_cache.in_memory_cache.async_get_cache(key=key) or 0
                )
                delta = after - before
                if after <= redis_val:
                    merged = redis_val + delta
                else:
                    continue
                # elif "rpm" in key:  # redis is behind in-memory cache
                #     # shut down the proxy
                #     print(f"self.redis_increment_operation_queue: {self.redis_increment_operation_queue}")
                #     print(f"Redis_val={redis_val} is behind in-memory cache_val={after} for key: {key}. This should not happen, since we should be updating redis with in-memory cache.")
                #     import os
                #     os._exit(1)
                #     raise Exception(f"Redis is behind in-memory cache for key: {key}. This should not happen, since we should be updating redis with in-memory cache.")
                await self.dual_cache.in_memory_cache.async_set_cache(
                    key=key, value=merged
                )

        except Exception as e:
            verbose_router_logger.exception(
                f"Error syncing in-memory cache with Redis: {str(e)}"
            )

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_block\state_block.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ..common.utils import isStrSpace
from ..ruler import StateBase
from ..token import Token
from ..utils import EnvType

if TYPE_CHECKING:
    from markdown_it.main import MarkdownIt


class StateBlock(StateBase):
    def __init__(
        self, src: str, md: MarkdownIt, env: EnvType, tokens: list[Token]
    ) -> None:
        self.src = src

        # link to parser instance
        self.md = md

        self.env = env

        #
        # Internal state variables
        #

        self.tokens = tokens

        self.bMarks: list[int] = []  # line begin offsets for fast jumps
        self.eMarks: list[int] = []  # line end offsets for fast jumps
        # offsets of the first non-space characters (tabs not expanded)
        self.tShift: list[int] = []
        self.sCount: list[int] = []  # indents for each line (tabs expanded)

        # An amount of virtual spaces (tabs expanded) between beginning
        # of each line (bMarks) and real beginning of that line.
        #
        # It exists only as a hack because blockquotes override bMarks
        # losing information in the process.
        #
        # It's used only when expanding tabs, you can think about it as
        # an initial tab length, e.g. bsCount=21 applied to string `\t123`
        # means first tab should be expanded to 4-21%4 === 3 spaces.
        #
        self.bsCount: list[int] = []

        # block parser variables
        self.blkIndent = 0  # required block content indent (for example, if we are
        # inside a list, it would be positioned after list marker)
        self.line = 0  # line index in src
        self.lineMax = 0  # lines count
        self.tight = False  # loose/tight mode for lists
        self.ddIndent = -1  # indent of the current dd block (-1 if there isn't any)
        self.listIndent = -1  # indent of the current list block (-1 if there isn't any)

        # can be 'blockquote', 'list', 'root', 'paragraph' or 'reference'
        # used in lists to determine if they interrupt a paragraph
        self.parentType = "root"

        self.level = 0

        # renderer
        self.result = ""

        # Create caches
        # Generate markers.
        indent_found = False

        start = pos = indent = offset = 0
        length = len(self.src)

        for pos, character in enumerate(self.src):
            if not indent_found:
                if isStrSpace(character):
                    indent += 1

                    if character == "\t":
                        offset += 4 - offset % 4
                    else:
                        offset += 1
                    continue
                else:
                    indent_found = True

            if character == "\n" or pos == length - 1:
                if character != "\n":
                    pos += 1
                self.bMarks.append(start)
                self.eMarks.append(pos)
                self.tShift.append(indent)
                self.sCount.append(offset)
                self.bsCount.append(0)

                indent_found = False
                indent = 0
                offset = 0
                start = pos + 1

        # Push fake entry to simplify cache bounds checks
        self.bMarks.append(length)
        self.eMarks.append(length)
        self.tShift.append(0)
        self.sCount.append(0)
        self.bsCount.append(0)

        self.lineMax = len(self.bMarks) - 1  # don't count last fake line

        # pre-check if code blocks are enabled, to speed up is_code_block method
        self._code_enabled = "code" in self.md["block"].ruler.get_active_rules()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(line={self.line},level={self.level},tokens={len(self.tokens)})"
        )

    def push(self, ttype: str, tag: str, nesting: Literal[-1, 0, 1]) -> Token:
        """Push new token to "stream"."""
        token = Token(ttype, tag, nesting)
        token.block = True
        if nesting < 0:
            self.level -= 1  # closing tag
        token.level = self.level
        if nesting > 0:
            self.level += 1  # opening tag
        self.tokens.append(token)
        return token

    def isEmpty(self, line: int) -> bool:
        """."""
        return (self.bMarks[line] + self.tShift[line]) >= self.eMarks[line]

    def skipEmptyLines(self, from_pos: int) -> int:
        """."""
        while from_pos < self.lineMax:
            try:
                if (self.bMarks[from_pos] + self.tShift[from_pos]) < self.eMarks[
                    from_pos
                ]:
                    break
            except IndexError:
                pass
            from_pos += 1
        return from_pos

    def skipSpaces(self, pos: int) -> int:
        """Skip spaces from given position."""
        while True:
            try:
                current = self.src[pos]
            except IndexError:
                break
            if not isStrSpace(current):
                break
            pos += 1
        return pos

    def skipSpacesBack(self, pos: int, minimum: int) -> int:
        """Skip spaces from given position in reverse."""
        if pos <= minimum:
            return pos
        while pos > minimum:
            pos -= 1
            if not isStrSpace(self.src[pos]):
                return pos + 1
        return pos

    def skipChars(self, pos: int, code: int) -> int:
        """Skip character code from given position."""
        while True:
            try:
                current = self.srcCharCode[pos]
            except IndexError:
                break
            if current != code:
                break
            pos += 1
        return pos

    def skipCharsStr(self, pos: int, ch: str) -> int:
        """Skip character string from given position."""
        while True:
            try:
                current = self.src[pos]
            except IndexError:
                break
            if current != ch:
                break
            pos += 1
        return pos

    def skipCharsBack(self, pos: int, code: int, minimum: int) -> int:
        """Skip character code reverse from given position - 1."""
        if pos <= minimum:
            return pos
        while pos > minimum:
            pos -= 1
            if code != self.srcCharCode[pos]:
                return pos + 1
        return pos

    def skipCharsStrBack(self, pos: int, ch: str, minimum: int) -> int:
        """Skip character string reverse from given position - 1."""
        if pos <= minimum:
            return pos
        while pos > minimum:
            pos -= 1
            if ch != self.src[pos]:
                return pos + 1
        return pos

    def getLines(self, begin: int, end: int, indent: int, keepLastLF: bool) -> str:
        """Cut lines range from source."""
        line = begin
        if begin >= end:
            return ""

        queue = [""] * (end - begin)

        i = 1
        while line < end:
            lineIndent = 0
            lineStart = first = self.bMarks[line]
            last = (
                self.eMarks[line] + 1
                if line + 1 < end or keepLastLF
                else self.eMarks[line]
            )

            while (first < last) and (lineIndent < indent):
                ch = self.src[first]
                if isStrSpace(ch):
                    if ch == "\t":
                        lineIndent += 4 - (lineIndent + self.bsCount[line]) % 4
                    else:
                        lineIndent += 1
                elif first - lineStart < self.tShift[line]:
                    lineIndent += 1
                else:
                    break
                first += 1

            if lineIndent > indent:
                # partially expanding tabs in code blocks, e.g '\t\tfoobar'
                # with indent=2 becomes '  \tfoobar'
                queue[i - 1] = (" " * (lineIndent - indent)) + self.src[first:last]
            else:
                queue[i - 1] = self.src[first:last]

            line += 1
            i += 1

        return "".join(queue)

    def is_code_block(self, line: int) -> bool:
        """Check if line is a code block,
        i.e. the code block rule is enabled and text is indented by more than 3 spaces.
        """
        return self._code_enabled and (self.sCount[line] - self.blkIndent) >= 4

# === NexusCore/openenv\Lib\site-packages\nltk\sem\lfg.py ===
# Natural Language Toolkit: Lexical Functional Grammar
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from itertools import chain

from nltk.internals import Counter


class FStructure(dict):
    def safeappend(self, key, item):
        """
        Append 'item' to the list at 'key'.  If no list exists for 'key', then
        construct one.
        """
        if key not in self:
            self[key] = []
        self[key].append(item)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key.lower(), value)

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())

    def __contains__(self, key):
        return dict.__contains__(self, key.lower())

    def to_glueformula_list(self, glue_dict):
        depgraph = self.to_depgraph()
        return glue_dict.to_glueformula_list(depgraph)

    def to_depgraph(self, rel=None):
        from nltk.parse.dependencygraph import DependencyGraph

        depgraph = DependencyGraph()
        nodes = depgraph.nodes

        self._to_depgraph(nodes, 0, "ROOT")

        # Add all the dependencies for all the nodes
        for address, node in nodes.items():
            for n2 in (n for n in nodes.values() if n["rel"] != "TOP"):
                if n2["head"] == address:
                    relation = n2["rel"]
                    node["deps"].setdefault(relation, [])
                    node["deps"][relation].append(n2["address"])

        depgraph.root = nodes[1]

        return depgraph

    def _to_depgraph(self, nodes, head, rel):
        index = len(nodes)

        nodes[index].update(
            {
                "address": index,
                "word": self.pred[0],
                "tag": self.pred[1],
                "head": head,
                "rel": rel,
            }
        )

        for feature in sorted(self):
            for item in sorted(self[feature]):
                if isinstance(item, FStructure):
                    item._to_depgraph(nodes, index, feature)
                elif isinstance(item, tuple):
                    new_index = len(nodes)
                    nodes[new_index].update(
                        {
                            "address": new_index,
                            "word": item[0],
                            "tag": item[1],
                            "head": index,
                            "rel": feature,
                        }
                    )
                elif isinstance(item, list):
                    for n in item:
                        n._to_depgraph(nodes, index, feature)
                else:
                    raise Exception(
                        "feature %s is not an FStruct, a list, or a tuple" % feature
                    )

    @staticmethod
    def read_depgraph(depgraph):
        return FStructure._read_depgraph(depgraph.root, depgraph)

    @staticmethod
    def _read_depgraph(node, depgraph, label_counter=None, parent=None):
        if not label_counter:
            label_counter = Counter()

        if node["rel"].lower() in ["spec", "punct"]:
            # the value of a 'spec' entry is a word, not an FStructure
            return (node["word"], node["tag"])

        else:
            fstruct = FStructure()
            fstruct.pred = None
            fstruct.label = FStructure._make_label(label_counter.get())

            fstruct.parent = parent

            word, tag = node["word"], node["tag"]
            if tag[:2] == "VB":
                if tag[2:3] == "D":
                    fstruct.safeappend("tense", ("PAST", "tense"))
                fstruct.pred = (word, tag[:2])

            if not fstruct.pred:
                fstruct.pred = (word, tag)

            children = [
                depgraph.nodes[idx]
                for idx in chain.from_iterable(node["deps"].values())
            ]
            for child in children:
                fstruct.safeappend(
                    child["rel"],
                    FStructure._read_depgraph(child, depgraph, label_counter, fstruct),
                )

            return fstruct

    @staticmethod
    def _make_label(value):
        """
        Pick an alphabetic character as identifier for an entity in the model.

        :param value: where to index into the list of characters
        :type value: int
        """
        letter = [
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "a",
            "b",
            "c",
            "d",
            "e",
        ][value - 1]
        num = int(value) // 26
        if num > 0:
            return letter + str(num)
        else:
            return letter

    def __repr__(self):
        return self.__str__().replace("\n", "")

    def __str__(self):
        return self.pretty_format()

    def pretty_format(self, indent=3):
        try:
            accum = "%s:[" % self.label
        except NameError:
            accum = "["
        try:
            accum += "pred '%s'" % (self.pred[0])
        except NameError:
            pass

        for feature in sorted(self):
            for item in self[feature]:
                if isinstance(item, FStructure):
                    next_indent = indent + len(feature) + 3 + len(self.label)
                    accum += "\n{}{} {}".format(
                        " " * (indent),
                        feature,
                        item.pretty_format(next_indent),
                    )
                elif isinstance(item, tuple):
                    accum += "\n{}{} '{}'".format(" " * (indent), feature, item[0])
                elif isinstance(item, list):
                    accum += "\n{}{} {{{}}}".format(
                        " " * (indent),
                        feature,
                        ("\n%s" % (" " * (indent + len(feature) + 2))).join(item),
                    )
                else:  # ERROR
                    raise Exception(
                        "feature %s is not an FStruct, a list, or a tuple" % feature
                    )
        return accum + "]"


def demo_read_depgraph():
    from nltk.parse.dependencygraph import DependencyGraph

    dg1 = DependencyGraph(
        """\
Esso       NNP     2       SUB
said       VBD     0       ROOT
the        DT      5       NMOD
Whiting    NNP     5       NMOD
field      NN      6       SUB
started    VBD     2       VMOD
production NN      6       OBJ
Tuesday    NNP     6       VMOD
"""
    )
    dg2 = DependencyGraph(
        """\
John    NNP     2       SUB
sees    VBP     0       ROOT
Mary    NNP     2       OBJ
"""
    )
    dg3 = DependencyGraph(
        """\
a       DT      2       SPEC
man     NN      3       SUBJ
walks   VB      0       ROOT
"""
    )
    dg4 = DependencyGraph(
        """\
every   DT      2       SPEC
girl    NN      3       SUBJ
chases  VB      0       ROOT
a       DT      5       SPEC
dog     NN      3       OBJ
"""
    )

    depgraphs = [dg1, dg2, dg3, dg4]
    for dg in depgraphs:
        print(FStructure.read_depgraph(dg))


if __name__ == "__main__":
    demo_read_depgraph()

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\threads\run_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable, Optional
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ...shared.chat_model import ChatModel
from ..assistant_tool_param import AssistantToolParam
from .runs.run_step_include import RunStepInclude
from ...shared_params.metadata import Metadata
from ...shared.reasoning_effort import ReasoningEffort
from .message_content_part_param import MessageContentPartParam
from ..code_interpreter_tool_param import CodeInterpreterToolParam
from ..assistant_tool_choice_option_param import AssistantToolChoiceOptionParam
from ..assistant_response_format_option_param import AssistantResponseFormatOptionParam

__all__ = [
    "RunCreateParamsBase",
    "AdditionalMessage",
    "AdditionalMessageAttachment",
    "AdditionalMessageAttachmentTool",
    "AdditionalMessageAttachmentToolFileSearch",
    "TruncationStrategy",
    "RunCreateParamsNonStreaming",
    "RunCreateParamsStreaming",
]


class RunCreateParamsBase(TypedDict, total=False):
    assistant_id: Required[str]
    """
    The ID of the
    [assistant](https://platform.openai.com/docs/api-reference/assistants) to use to
    execute this run.
    """

    include: List[RunStepInclude]
    """A list of additional fields to include in the response.

    Currently the only supported value is
    `step_details.tool_calls[*].file_search.results[*].content` to fetch the file
    search result content.

    See the
    [file search tool documentation](https://platform.openai.com/docs/assistants/tools/file-search#customizing-file-search-settings)
    for more information.
    """

    additional_instructions: Optional[str]
    """Appends additional instructions at the end of the instructions for the run.

    This is useful for modifying the behavior on a per-run basis without overriding
    other instructions.
    """

    additional_messages: Optional[Iterable[AdditionalMessage]]
    """Adds additional messages to the thread before creating the run."""

    instructions: Optional[str]
    """
    Overrides the
    [instructions](https://platform.openai.com/docs/api-reference/assistants/createAssistant)
    of the assistant. This is useful for modifying the behavior on a per-run basis.
    """

    max_completion_tokens: Optional[int]
    """
    The maximum number of completion tokens that may be used over the course of the
    run. The run will make a best effort to use only the number of completion tokens
    specified, across multiple turns of the run. If the run exceeds the number of
    completion tokens specified, the run will end with status `incomplete`. See
    `incomplete_details` for more info.
    """

    max_prompt_tokens: Optional[int]
    """The maximum number of prompt tokens that may be used over the course of the run.

    The run will make a best effort to use only the number of prompt tokens
    specified, across multiple turns of the run. If the run exceeds the number of
    prompt tokens specified, the run will end with status `incomplete`. See
    `incomplete_details` for more info.
    """

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """

    model: Union[str, ChatModel, None]
    """
    The ID of the [Model](https://platform.openai.com/docs/api-reference/models) to
    be used to execute this run. If a value is provided here, it will override the
    model associated with the assistant. If not, the model associated with the
    assistant will be used.
    """

    parallel_tool_calls: bool
    """
    Whether to enable
    [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
    during tool use.
    """

    reasoning_effort: Optional[ReasoningEffort]
    """**o-series models only**

    Constrains effort on reasoning for
    [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
    supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
    result in faster responses and fewer tokens used on reasoning in a response.
    """

    response_format: Optional[AssistantResponseFormatOptionParam]
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

    temperature: Optional[float]
    """What sampling temperature to use, between 0 and 2.

    Higher values like 0.8 will make the output more random, while lower values like
    0.2 will make it more focused and deterministic.
    """

    tool_choice: Optional[AssistantToolChoiceOptionParam]
    """
    Controls which (if any) tool is called by the model. `none` means the model will
    not call any tools and instead generates a message. `auto` is the default value
    and means the model can pick between generating a message or calling one or more
    tools. `required` means the model must call one or more tools before responding
    to the user. Specifying a particular tool like `{"type": "file_search"}` or
    `{"type": "function", "function": {"name": "my_function"}}` forces the model to
    call that tool.
    """

    tools: Optional[Iterable[AssistantToolParam]]
    """Override the tools the assistant can use for this run.

    This is useful for modifying the behavior on a per-run basis.
    """

    top_p: Optional[float]
    """
    An alternative to sampling with temperature, called nucleus sampling, where the
    model considers the results of the tokens with top_p probability mass. So 0.1
    means only the tokens comprising the top 10% probability mass are considered.

    We generally recommend altering this or temperature but not both.
    """

    truncation_strategy: Optional[TruncationStrategy]
    """Controls for how a thread will be truncated prior to the run.

    Use this to control the intial context window of the run.
    """


class AdditionalMessageAttachmentToolFileSearch(TypedDict, total=False):
    type: Required[Literal["file_search"]]
    """The type of tool being defined: `file_search`"""


AdditionalMessageAttachmentTool: TypeAlias = Union[CodeInterpreterToolParam, AdditionalMessageAttachmentToolFileSearch]


class AdditionalMessageAttachment(TypedDict, total=False):
    file_id: str
    """The ID of the file to attach to the message."""

    tools: Iterable[AdditionalMessageAttachmentTool]
    """The tools to add this file to."""


class AdditionalMessage(TypedDict, total=False):
    content: Required[Union[str, Iterable[MessageContentPartParam]]]
    """The text contents of the message."""

    role: Required[Literal["user", "assistant"]]
    """The role of the entity that is creating the message. Allowed values include:

    - `user`: Indicates the message is sent by an actual user and should be used in
      most cases to represent user-generated messages.
    - `assistant`: Indicates the message is generated by the assistant. Use this
      value to insert messages from the assistant into the conversation.
    """

    attachments: Optional[Iterable[AdditionalMessageAttachment]]
    """A list of files attached to the message, and the tools they should be added to."""

    metadata: Optional[Metadata]
    """Set of 16 key-value pairs that can be attached to an object.

    This can be useful for storing additional information about the object in a
    structured format, and querying for objects via API or the dashboard.

    Keys are strings with a maximum length of 64 characters. Values are strings with
    a maximum length of 512 characters.
    """


class TruncationStrategy(TypedDict, total=False):
    type: Required[Literal["auto", "last_messages"]]
    """The truncation strategy to use for the thread.

    The default is `auto`. If set to `last_messages`, the thread will be truncated
    to the n most recent messages in the thread. When set to `auto`, messages in the
    middle of the thread will be dropped to fit the context length of the model,
    `max_prompt_tokens`.
    """

    last_messages: Optional[int]
    """
    The number of most recent messages from the thread when constructing the context
    for the run.
    """


class RunCreateParamsNonStreaming(RunCreateParamsBase, total=False):
    stream: Optional[Literal[False]]
    """
    If `true`, returns a stream of events that happen during the Run as server-sent
    events, terminating when the Run enters a terminal state with a `data: [DONE]`
    message.
    """


class RunCreateParamsStreaming(RunCreateParamsBase):
    stream: Required[Literal[True]]
    """
    If `true`, returns a stream of events that happen during the Run as server-sent
    events, terminating when the Run enters a terminal state with a `data: [DONE]`
    message.
    """


RunCreateParams = Union[RunCreateParamsNonStreaming, RunCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\starlette\middleware\errors.py ===
from __future__ import annotations

import html
import inspect
import traceback
import typing

from starlette._utils import is_async_callable
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

STYLES = """
p {
    color: #211c1c;
}
.traceback-container {
    border: 1px solid #038BB8;
}
.traceback-title {
    background-color: #038BB8;
    color: lemonchiffon;
    padding: 12px;
    font-size: 20px;
    margin-top: 0px;
}
.frame-line {
    padding-left: 10px;
    font-family: monospace;
}
.frame-filename {
    font-family: monospace;
}
.center-line {
    background-color: #038BB8;
    color: #f9f6e1;
    padding: 5px 0px 5px 5px;
}
.lineno {
    margin-right: 5px;
}
.frame-title {
    font-weight: unset;
    padding: 10px 10px 10px 10px;
    background-color: #E4F4FD;
    margin-right: 10px;
    color: #191f21;
    font-size: 17px;
    border: 1px solid #c7dce8;
}
.collapse-btn {
    float: right;
    padding: 0px 5px 1px 5px;
    border: solid 1px #96aebb;
    cursor: pointer;
}
.collapsed {
  display: none;
}
.source-code {
  font-family: courier;
  font-size: small;
  padding-bottom: 10px;
}
"""

JS = """
<script type="text/javascript">
    function collapse(element){
        const frameId = element.getAttribute("data-frame-id");
        const frame = document.getElementById(frameId);

        if (frame.classList.contains("collapsed")){
            element.innerHTML = "&#8210;";
            frame.classList.remove("collapsed");
        } else {
            element.innerHTML = "+";
            frame.classList.add("collapsed");
        }
    }
</script>
"""

TEMPLATE = """
<html>
    <head>
        <style type='text/css'>
            {styles}
        </style>
        <title>Starlette Debugger</title>
    </head>
    <body>
        <h1>500 Server Error</h1>
        <h2>{error}</h2>
        <div class="traceback-container">
            <p class="traceback-title">Traceback</p>
            <div>{exc_html}</div>
        </div>
        {js}
    </body>
</html>
"""

FRAME_TEMPLATE = """
<div>
    <p class="frame-title">File <span class="frame-filename">{frame_filename}</span>,
    line <i>{frame_lineno}</i>,
    in <b>{frame_name}</b>
    <span class="collapse-btn" data-frame-id="{frame_filename}-{frame_lineno}" onclick="collapse(this)">{collapse_button}</span>
    </p>
    <div id="{frame_filename}-{frame_lineno}" class="source-code {collapsed}">{code_context}</div>
</div>
"""  # noqa: E501

LINE = """
<p><span class="frame-line">
<span class="lineno">{lineno}.</span> {line}</span></p>
"""

CENTER_LINE = """
<p class="center-line"><span class="frame-line center-line">
<span class="lineno">{lineno}.</span> {line}</span></p>
"""


class ServerErrorMiddleware:
    """
    Handles returning 500 responses when a server error occurs.

    If 'debug' is set, then traceback responses will be returned,
    otherwise the designated 'handler' will be called.

    This middleware class should generally be used to wrap *everything*
    else up, so that unhandled exceptions anywhere in the stack
    always result in an appropriate 500 response.
    """

    def __init__(
        self,
        app: ASGIApp,
        handler: typing.Callable[[Request, Exception], typing.Any] | None = None,
        debug: bool = False,
    ) -> None:
        self.app = app
        self.handler = handler
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send

            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            request = Request(scope)
            if self.debug:
                # In debug mode, return traceback responses.
                response = self.debug_response(request, exc)
            elif self.handler is None:
                # Use our default 500 error handler.
                response = self.error_response(request, exc)
            else:
                # Use an installed 500 error handler.
                if is_async_callable(self.handler):
                    response = await self.handler(request, exc)
                else:
                    response = await run_in_threadpool(self.handler, request, exc)

            if not response_started:
                await response(scope, receive, send)

            # We always continue to raise the exception.
            # This allows servers to log the error, or allows test clients
            # to optionally raise the error within the test case.
            raise exc

    def format_line(
        self, index: int, line: str, frame_lineno: int, frame_index: int
    ) -> str:
        values = {
            # HTML escape - line could contain < or >
            "line": html.escape(line).replace(" ", "&nbsp"),
            "lineno": (frame_lineno - frame_index) + index,
        }

        if index != frame_index:
            return LINE.format(**values)
        return CENTER_LINE.format(**values)

    def generate_frame_html(self, frame: inspect.FrameInfo, is_collapsed: bool) -> str:
        code_context = "".join(
            self.format_line(
                index,
                line,
                frame.lineno,
                frame.index,  # type: ignore[arg-type]
            )
            for index, line in enumerate(frame.code_context or [])
        )

        values = {
            # HTML escape - filename could contain < or >, especially if it's a virtual
            # file e.g. <stdin> in the REPL
            "frame_filename": html.escape(frame.filename),
            "frame_lineno": frame.lineno,
            # HTML escape - if you try very hard it's possible to name a function with <
            # or >
            "frame_name": html.escape(frame.function),
            "code_context": code_context,
            "collapsed": "collapsed" if is_collapsed else "",
            "collapse_button": "+" if is_collapsed else "&#8210;",
        }
        return FRAME_TEMPLATE.format(**values)

    def generate_html(self, exc: Exception, limit: int = 7) -> str:
        traceback_obj = traceback.TracebackException.from_exception(
            exc, capture_locals=True
        )

        exc_html = ""
        is_collapsed = False
        exc_traceback = exc.__traceback__
        if exc_traceback is not None:
            frames = inspect.getinnerframes(exc_traceback, limit)
            for frame in reversed(frames):
                exc_html += self.generate_frame_html(frame, is_collapsed)
                is_collapsed = True

        # escape error class and text
        error = (
            f"{html.escape(traceback_obj.exc_type.__name__)}: "
            f"{html.escape(str(traceback_obj))}"
        )

        return TEMPLATE.format(styles=STYLES, js=JS, error=error, exc_html=exc_html)

    def generate_plain_text(self, exc: Exception) -> str:
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    def debug_response(self, request: Request, exc: Exception) -> Response:
        accept = request.headers.get("accept", "")

        if "text/html" in accept:
            content = self.generate_html(exc)
            return HTMLResponse(content, status_code=500)
        content = self.generate_plain_text(exc)
        return PlainTextResponse(content, status_code=500)

    def error_response(self, request: Request, exc: Exception) -> Response:
        return PlainTextResponse("Internal Server Error", status_code=500)

# === NexusCore/openenv\Lib\site-packages\win32comext\internet\inetcon.py ===
INET_E_USE_DEFAULT_PROTOCOLHANDLER = -2146697199  # _HRESULT_TYPEDEF_(0x800C0011L)
INET_E_USE_DEFAULT_SETTING = -2146697198  # _HRESULT_TYPEDEF_(0x800C0012L)
INET_E_DEFAULT_ACTION = INET_E_USE_DEFAULT_PROTOCOLHANDLER
INET_E_QUERYOPTION_UNKNOWN = -2146697197  # _HRESULT_TYPEDEF_(0x800C0013L)
INET_E_REDIRECTING = -2146697196  # _HRESULT_TYPEDEF_(0x800C0014L)

INET_E_INVALID_URL = -2146697214  # _HRESULT_TYPEDEF_(0x800C0002L)
INET_E_NO_SESSION = -2146697213  # _HRESULT_TYPEDEF_(0x800C0003L)
INET_E_CANNOT_CONNECT = -2146697212  # _HRESULT_TYPEDEF_(0x800C0004L)
INET_E_RESOURCE_NOT_FOUND = -2146697211  # _HRESULT_TYPEDEF_(0x800C0005L)
INET_E_OBJECT_NOT_FOUND = -2146697210  # _HRESULT_TYPEDEF_(0x800C0006L)
INET_E_DATA_NOT_AVAILABLE = -2146697209  # _HRESULT_TYPEDEF_(0x800C0007L)
INET_E_DOWNLOAD_FAILURE = -2146697208  # _HRESULT_TYPEDEF_(0x800C0008L)
INET_E_AUTHENTICATION_REQUIRED = -2146697207  # _HRESULT_TYPEDEF_(0x800C0009L)
INET_E_NO_VALID_MEDIA = -2146697206  # _HRESULT_TYPEDEF_(0x800C000AL)
INET_E_CONNECTION_TIMEOUT = -2146697205  # _HRESULT_TYPEDEF_(0x800C000BL)
INET_E_INVALID_REQUEST = -2146697204  # _HRESULT_TYPEDEF_(0x800C000CL)
INET_E_UNKNOWN_PROTOCOL = -2146697203  # _HRESULT_TYPEDEF_(0x800C000DL)
INET_E_SECURITY_PROBLEM = -2146697202  # _HRESULT_TYPEDEF_(0x800C000EL)
INET_E_CANNOT_LOAD_DATA = -2146697201  # _HRESULT_TYPEDEF_(0x800C000FL)
INET_E_CANNOT_INSTANTIATE_OBJECT = -2146697200  # _HRESULT_TYPEDEF_(0x800C0010L)
INET_E_INVALID_CERTIFICATE = -2146697191  # _HRESULT_TYPEDEF_(0x800C0019L)
INET_E_REDIRECT_FAILED = -2146697196  # _HRESULT_TYPEDEF_(0x800C0014L)
INET_E_REDIRECT_TO_DIR = -2146697195  # _HRESULT_TYPEDEF_(0x800C0015L)
INET_E_CANNOT_LOCK_REQUEST = -2146697194  # _HRESULT_TYPEDEF_(0x800C0016L)
INET_E_USE_EXTEND_BINDING = -2146697193  # _HRESULT_TYPEDEF_(0x800C0017L)
INET_E_TERMINATED_BIND = -2146697192  # _HRESULT_TYPEDEF_(0x800C0018L)
INET_E_CODE_DOWNLOAD_DECLINED = -2146696960  # _HRESULT_TYPEDEF_(0x800C0100L)
INET_E_RESULT_DISPATCHED = -2146696704  # _HRESULT_TYPEDEF_(0x800C0200L)
INET_E_CANNOT_REPLACE_SFP_FILE = -2146696448  # _HRESULT_TYPEDEF_(0x800C0300L)
INET_E_CODE_INSTALL_SUPPRESSED = -2146696192  # _HRESULT_TYPEDEF_(0x800C0400L)
INET_E_CODE_INSTALL_BLOCKED_BY_HASH_POLICY = (
    -2146695936
)  # _HRESULT_TYPEDEF_(0x800C0500L)

# Generated by h2py from UrlMon.h
MKSYS_URLMONIKER = 6
URL_MK_LEGACY = 0
URL_MK_UNIFORM = 1
URL_MK_NO_CANONICALIZE = 2
FIEF_FLAG_FORCE_JITUI = 0x1
FIEF_FLAG_PEEK = 0x2
FIEF_FLAG_SKIP_INSTALLED_VERSION_CHECK = 0x4
FMFD_DEFAULT = 0x00000000
FMFD_URLASFILENAME = 0x00000001
FMFD_ENABLEMIMESNIFFING = 0x00000002
FMFD_IGNOREMIMETEXTPLAIN = 0x00000004
URLMON_OPTION_USERAGENT = 0x10000001
URLMON_OPTION_USERAGENT_REFRESH = 0x10000002
URLMON_OPTION_URL_ENCODING = 0x10000004
URLMON_OPTION_USE_BINDSTRINGCREDS = 0x10000008
URLMON_OPTION_USE_BROWSERAPPSDOCUMENTS = 0x10000010
CF_NULL = 0
Uri_CREATE_ALLOW_RELATIVE = 0x00000001
Uri_CREATE_ALLOW_IMPLICIT_WILDCARD_SCHEME = 0x00000002
Uri_CREATE_ALLOW_IMPLICIT_FILE_SCHEME = 0x00000004
Uri_CREATE_NOFRAG = 0x00000008
Uri_CREATE_NO_CANONICALIZE = 0x00000010
Uri_CREATE_CANONICALIZE = 0x00000100
Uri_CREATE_FILE_USE_DOS_PATH = 0x00000020
Uri_CREATE_DECODE_EXTRA_INFO = 0x00000040
Uri_CREATE_NO_DECODE_EXTRA_INFO = 0x00000080
Uri_CREATE_CRACK_UNKNOWN_SCHEMES = 0x00000200
Uri_CREATE_NO_CRACK_UNKNOWN_SCHEMES = 0x00000400
Uri_CREATE_PRE_PROCESS_HTML_URI = 0x00000800
Uri_CREATE_NO_PRE_PROCESS_HTML_URI = 0x00001000
Uri_CREATE_IE_SETTINGS = 0x00002000
Uri_CREATE_NO_IE_SETTINGS = 0x00004000
Uri_CREATE_NO_ENCODE_FORBIDDEN_CHARACTERS = 0x00008000
Uri_DISPLAY_NO_FRAGMENT = 0x00000001
Uri_PUNYCODE_IDN_HOST = 0x00000002
Uri_DISPLAY_IDN_HOST = 0x00000004
Uri_ENCODING_USER_INFO_AND_PATH_IS_PERCENT_ENCODED_UTF8 = 0x00000001
Uri_ENCODING_USER_INFO_AND_PATH_IS_CP = 0x00000002
Uri_ENCODING_HOST_IS_IDN = 0x00000004
Uri_ENCODING_HOST_IS_PERCENT_ENCODED_UTF8 = 0x00000008
Uri_ENCODING_HOST_IS_PERCENT_ENCODED_CP = 0x00000010
Uri_ENCODING_QUERY_AND_FRAGMENT_IS_PERCENT_ENCODED_UTF8 = 0x00000020
Uri_ENCODING_QUERY_AND_FRAGMENT_IS_CP = 0x00000040
Uri_ENCODING_RFC = (
    Uri_ENCODING_USER_INFO_AND_PATH_IS_PERCENT_ENCODED_UTF8
    | Uri_ENCODING_HOST_IS_PERCENT_ENCODED_UTF8
    | Uri_ENCODING_QUERY_AND_FRAGMENT_IS_PERCENT_ENCODED_UTF8
)
UriBuilder_USE_ORIGINAL_FLAGS = 0x00000001
WININETINFO_OPTION_LOCK_HANDLE = 65534
URLOSTRM_USECACHEDCOPY_ONLY = 0x1
URLOSTRM_USECACHEDCOPY = 0x2
URLOSTRM_GETNEWESTVERSION = 0x3
SET_FEATURE_ON_THREAD = 0x00000001
SET_FEATURE_ON_PROCESS = 0x00000002
SET_FEATURE_IN_REGISTRY = 0x00000004
SET_FEATURE_ON_THREAD_LOCALMACHINE = 0x00000008
SET_FEATURE_ON_THREAD_INTRANET = 0x00000010
SET_FEATURE_ON_THREAD_TRUSTED = 0x00000020
SET_FEATURE_ON_THREAD_INTERNET = 0x00000040
SET_FEATURE_ON_THREAD_RESTRICTED = 0x00000080
GET_FEATURE_FROM_THREAD = 0x00000001
GET_FEATURE_FROM_PROCESS = 0x00000002
GET_FEATURE_FROM_REGISTRY = 0x00000004
GET_FEATURE_FROM_THREAD_LOCALMACHINE = 0x00000008
GET_FEATURE_FROM_THREAD_INTRANET = 0x00000010
GET_FEATURE_FROM_THREAD_TRUSTED = 0x00000020
GET_FEATURE_FROM_THREAD_INTERNET = 0x00000040
GET_FEATURE_FROM_THREAD_RESTRICTED = 0x00000080
PROTOCOLFLAG_NO_PICS_CHECK = 0x00000001
MUTZ_NOSAVEDFILECHECK = 0x00000001
MUTZ_ISFILE = 0x00000002
MUTZ_ACCEPT_WILDCARD_SCHEME = 0x00000080
MUTZ_ENFORCERESTRICTED = 0x00000100
MUTZ_RESERVED = 0x00000200
MUTZ_REQUIRESAVEDFILECHECK = 0x00000400
MUTZ_DONT_UNESCAPE = 0x00000800
MUTZ_DONT_USE_CACHE = 0x00001000
MUTZ_FORCE_INTRANET_FLAGS = 0x00002000
MUTZ_IGNORE_ZONE_MAPPINGS = 0x00004000
MAX_SIZE_SECURITY_ID = 512
URLACTION_MIN = 0x00001000
URLACTION_DOWNLOAD_MIN = 0x00001000
URLACTION_DOWNLOAD_SIGNED_ACTIVEX = 0x00001001
URLACTION_DOWNLOAD_UNSIGNED_ACTIVEX = 0x00001004
URLACTION_DOWNLOAD_CURR_MAX = 0x00001004
URLACTION_DOWNLOAD_MAX = 0x000011FF
URLACTION_ACTIVEX_MIN = 0x00001200
URLACTION_ACTIVEX_RUN = 0x00001200
URLPOLICY_ACTIVEX_CHECK_LIST = 0x00010000
URLACTION_ACTIVEX_OVERRIDE_OBJECT_SAFETY = 0x00001201
URLACTION_ACTIVEX_OVERRIDE_DATA_SAFETY = 0x00001202
URLACTION_ACTIVEX_OVERRIDE_SCRIPT_SAFETY = 0x00001203
URLACTION_SCRIPT_OVERRIDE_SAFETY = 0x00001401
URLACTION_ACTIVEX_CONFIRM_NOOBJECTSAFETY = 0x00001204
URLACTION_ACTIVEX_TREATASUNTRUSTED = 0x00001205
URLACTION_ACTIVEX_NO_WEBOC_SCRIPT = 0x00001206
URLACTION_ACTIVEX_OVERRIDE_REPURPOSEDETECTION = 0x00001207
URLACTION_ACTIVEX_OVERRIDE_OPTIN = 0x00001208
URLACTION_ACTIVEX_SCRIPTLET_RUN = 0x00001209
URLACTION_ACTIVEX_DYNSRC_VIDEO_AND_ANIMATION = 0x0000120A
URLACTION_ACTIVEX_CURR_MAX = 0x0000120A
URLACTION_ACTIVEX_MAX = 0x000013FF
URLACTION_SCRIPT_MIN = 0x00001400
URLACTION_SCRIPT_RUN = 0x00001400
URLACTION_SCRIPT_JAVA_USE = 0x00001402
URLACTION_SCRIPT_SAFE_ACTIVEX = 0x00001405
URLACTION_CROSS_DOMAIN_DATA = 0x00001406
URLACTION_SCRIPT_PASTE = 0x00001407
URLACTION_ALLOW_XDOMAIN_SUBFRAME_RESIZE = 0x00001408
URLACTION_SCRIPT_CURR_MAX = 0x00001408
URLACTION_SCRIPT_MAX = 0x000015FF
URLACTION_HTML_MIN = 0x00001600
URLACTION_HTML_SUBMIT_FORMS = 0x00001601
URLACTION_HTML_SUBMIT_FORMS_FROM = 0x00001602
URLACTION_HTML_SUBMIT_FORMS_TO = 0x00001603
URLACTION_HTML_FONT_DOWNLOAD = 0x00001604
URLACTION_HTML_JAVA_RUN = 0x00001605
URLACTION_HTML_USERDATA_SAVE = 0x00001606
URLACTION_HTML_SUBFRAME_NAVIGATE = 0x00001607
URLACTION_HTML_META_REFRESH = 0x00001608
URLACTION_HTML_MIXED_CONTENT = 0x00001609
URLACTION_HTML_INCLUDE_FILE_PATH = 0x0000160A
URLACTION_HTML_MAX = 0x000017FF
URLACTION_SHELL_MIN = 0x00001800
URLACTION_SHELL_INSTALL_DTITEMS = 0x00001800
URLACTION_SHELL_MOVE_OR_COPY = 0x00001802
URLACTION_SHELL_FILE_DOWNLOAD = 0x00001803
URLACTION_SHELL_VERB = 0x00001804
URLACTION_SHELL_WEBVIEW_VERB = 0x00001805
URLACTION_SHELL_SHELLEXECUTE = 0x00001806
URLACTION_SHELL_EXECUTE_HIGHRISK = 0x00001806
URLACTION_SHELL_EXECUTE_MODRISK = 0x00001807
URLACTION_SHELL_EXECUTE_LOWRISK = 0x00001808
URLACTION_SHELL_POPUPMGR = 0x00001809
URLACTION_SHELL_RTF_OBJECTS_LOAD = 0x0000180A
URLACTION_SHELL_ENHANCED_DRAGDROP_SECURITY = 0x0000180B
URLACTION_SHELL_EXTENSIONSECURITY = 0x0000180C
URLACTION_SHELL_SECURE_DRAGSOURCE = 0x0000180D
URLACTION_SHELL_CURR_MAX = 0x0000180D
URLACTION_SHELL_MAX = 0x000019FF
URLACTION_NETWORK_MIN = 0x00001A00
URLACTION_CREDENTIALS_USE = 0x00001A00
URLPOLICY_CREDENTIALS_SILENT_LOGON_OK = 0x00000000
URLPOLICY_CREDENTIALS_MUST_PROMPT_USER = 0x00010000
URLPOLICY_CREDENTIALS_CONDITIONAL_PROMPT = 0x00020000
URLPOLICY_CREDENTIALS_ANONYMOUS_ONLY = 0x00030000
URLACTION_AUTHENTICATE_CLIENT = 0x00001A01
URLPOLICY_AUTHENTICATE_CLEARTEXT_OK = 0x00000000
URLPOLICY_AUTHENTICATE_CHALLENGE_RESPONSE = 0x00010000
URLPOLICY_AUTHENTICATE_MUTUAL_ONLY = 0x00030000
URLACTION_COOKIES = 0x00001A02
URLACTION_COOKIES_SESSION = 0x00001A03
URLACTION_CLIENT_CERT_PROMPT = 0x00001A04
URLACTION_COOKIES_THIRD_PARTY = 0x00001A05
URLACTION_COOKIES_SESSION_THIRD_PARTY = 0x00001A06
URLACTION_COOKIES_ENABLED = 0x00001A10
URLACTION_NETWORK_CURR_MAX = 0x00001A10
URLACTION_NETWORK_MAX = 0x00001BFF
URLACTION_JAVA_MIN = 0x00001C00
URLACTION_JAVA_PERMISSIONS = 0x00001C00
URLPOLICY_JAVA_PROHIBIT = 0x00000000
URLPOLICY_JAVA_HIGH = 0x00010000
URLPOLICY_JAVA_MEDIUM = 0x00020000
URLPOLICY_JAVA_LOW = 0x00030000
URLPOLICY_JAVA_CUSTOM = 0x00800000
URLACTION_JAVA_CURR_MAX = 0x00001C00
URLACTION_JAVA_MAX = 0x00001CFF
URLACTION_INFODELIVERY_MIN = 0x00001D00
URLACTION_INFODELIVERY_NO_ADDING_CHANNELS = 0x00001D00
URLACTION_INFODELIVERY_NO_EDITING_CHANNELS = 0x00001D01
URLACTION_INFODELIVERY_NO_REMOVING_CHANNELS = 0x00001D02
URLACTION_INFODELIVERY_NO_ADDING_SUBSCRIPTIONS = 0x00001D03
URLACTION_INFODELIVERY_NO_EDITING_SUBSCRIPTIONS = 0x00001D04
URLACTION_INFODELIVERY_NO_REMOVING_SUBSCRIPTIONS = 0x00001D05
URLACTION_INFODELIVERY_NO_CHANNEL_LOGGING = 0x00001D06
URLACTION_INFODELIVERY_CURR_MAX = 0x00001D06
URLACTION_INFODELIVERY_MAX = 0x00001DFF
URLACTION_CHANNEL_SOFTDIST_MIN = 0x00001E00
URLACTION_CHANNEL_SOFTDIST_PERMISSIONS = 0x00001E05
URLPOLICY_CHANNEL_SOFTDIST_PROHIBIT = 0x00010000
URLPOLICY_CHANNEL_SOFTDIST_PRECACHE = 0x00020000
URLPOLICY_CHANNEL_SOFTDIST_AUTOINSTALL = 0x00030000
URLACTION_CHANNEL_SOFTDIST_MAX = 0x00001EFF
URLACTION_BEHAVIOR_MIN = 0x00002000
URLACTION_BEHAVIOR_RUN = 0x00002000
URLPOLICY_BEHAVIOR_CHECK_LIST = 0x00010000
URLACTION_FEATURE_MIN = 0x00002100
URLACTION_FEATURE_MIME_SNIFFING = 0x00002100
URLACTION_FEATURE_ZONE_ELEVATION = 0x00002101
URLACTION_FEATURE_WINDOW_RESTRICTIONS = 0x00002102
URLACTION_FEATURE_SCRIPT_STATUS_BAR = 0x00002103
URLACTION_FEATURE_FORCE_ADDR_AND_STATUS = 0x00002104
URLACTION_FEATURE_BLOCK_INPUT_PROMPTS = 0x00002105
URLACTION_AUTOMATIC_DOWNLOAD_UI_MIN = 0x00002200
URLACTION_AUTOMATIC_DOWNLOAD_UI = 0x00002200
URLACTION_AUTOMATIC_ACTIVEX_UI = 0x00002201
URLACTION_ALLOW_RESTRICTEDPROTOCOLS = 0x00002300
URLACTION_ALLOW_APEVALUATION = 0x00002301
URLACTION_WINDOWS_BROWSER_APPLICATIONS = 0x00002400
URLACTION_XPS_DOCUMENTS = 0x00002401
URLACTION_LOOSE_XAML = 0x00002402
URLACTION_LOWRIGHTS = 0x00002500
URLACTION_WINFX_SETUP = 0x00002600
URLPOLICY_ALLOW = 0x00
URLPOLICY_QUERY = 0x01
URLPOLICY_DISALLOW = 0x03
URLPOLICY_NOTIFY_ON_ALLOW = 0x10
URLPOLICY_NOTIFY_ON_DISALLOW = 0x20
URLPOLICY_LOG_ON_ALLOW = 0x40
URLPOLICY_LOG_ON_DISALLOW = 0x80
URLPOLICY_MASK_PERMISSIONS = 0x0F
URLPOLICY_DONTCHECKDLGBOX = 0x100
URLZONE_ESC_FLAG = 0x100
SECURITY_IE_STATE_GREEN = 0x00000000
SECURITY_IE_STATE_RED = 0x00000001
SOFTDIST_FLAG_USAGE_EMAIL = 0x00000001
SOFTDIST_FLAG_USAGE_PRECACHE = 0x00000002
SOFTDIST_FLAG_USAGE_AUTOINSTALL = 0x00000004
SOFTDIST_FLAG_DELETE_SUBSCRIPTION = 0x00000008
SOFTDIST_ADSTATE_NONE = 0x00000000
SOFTDIST_ADSTATE_AVAILABLE = 0x00000001
SOFTDIST_ADSTATE_DOWNLOADED = 0x00000002
SOFTDIST_ADSTATE_INSTALLED = 0x00000003
CONFIRMSAFETYACTION_LOADOBJECT = 0x00000001

# === NexusCore/evaluation\evalplus\tools\mbpp\to_original_fmt.py ===
import ast
import inspect
import json
import multiprocessing
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from traceback import print_exc

from rich.console import Console
from rich.syntax import Syntax
from tqdm import tqdm

from evalplus.data.mbpp import (
    MBPP_PLUS_VERSION,
    get_mbpp,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from evalplus.eval import is_floats
from evalplus.eval._special_oracle import (
    MBPP_OUTPUT_NOT_NONE_TASKS,
    MBPP_OUTPUT_SET_EQ_TASKS,
)
from evalplus.evaluate import get_groundtruth

MBPP_TEST_TEMPLATE = """\
import numpy as np
from math import inf

{aux_fn}

inputs = {inputs}
results = {results}
for i, (inp, exp) in enumerate(zip(inputs, results)):
    assertion({entry_point}(*inp), exp, {atol})
"""

MBPP_CROSSCHECK_TEMPLATE = """\
import numpy as np
from math import inf

{aux_fn}

{ref_func}

inputs = {inputs}
for i, inp in enumerate(inputs):
    assertion({entry_point}(*inp), ref_func(*inp), {atol})
"""

ASSERTION_FN = f"""\
{inspect.getsource(is_floats)}

def assertion(out, exp, atol):
    if atol == 0 and is_floats(exp):
        atol = 1e-6
    if out != exp and atol != 0:
        assert np.allclose(out, exp, rtol=1e-07, atol=atol)
    else:
        assert out == exp, f"out: {{out}}, exp: {{exp}}"
"""


def synthesize_test_code(task_id, entry_point, inputs, results, ref_func, atol):
    # dataset size optimization for large outputs
    if entry_point in ("combinations_colors", "freq_count", "get_coordinates"):
        return task_id, MBPP_CROSSCHECK_TEMPLATE.format(
            aux_fn=ASSERTION_FN,
            inputs=inputs,
            ref_func=ref_func.replace(f" {entry_point}(", " ref_func("),
            entry_point=entry_point,
            atol=atol,
        )

    # default settings
    aux_fn = ASSERTION_FN

    # ================================================ #
    # ============== special oracles ================= #

    if entry_point in MBPP_OUTPUT_SET_EQ_TASKS:
        aux_fn = f"""\
{inspect.getsource(is_floats)}

def assertion(out, exp, atol):
    if atol == 0 and is_floats(exp):
        atol = 1e-6
    out = set(out)
    exp = set(exp)
    if out != exp and atol != 0:
        assert np.allclose(out, exp, rtol=1e-07, atol=atol)
    else:
        assert out == exp, f"out: {{out}}, exp: {{exp}}"
"""
    elif entry_point in MBPP_OUTPUT_NOT_NONE_TASKS:
        aux_fn = f"""\
def assertion(out, exp, atol):
    if isinstance(out, bool):
        exact_match = out == exp
    else:
        exact_match = exp == (out is not None)
"""

    # ============== special oracles ================= #
    # ================================================ #

    test_code = MBPP_TEST_TEMPLATE.format(
        aux_fn=aux_fn,
        inputs=inputs,
        results=results,
        entry_point=entry_point,
        atol=atol,
    )

    return task_id, test_code


def deduplicate(inputs, results):
    assert len(inputs) == len(results)
    unique_input_strs = set([f"{x}" for x in inputs])

    new_inputs, new_results = [], []
    for inp, res in zip(inputs, results):
        inp_str = f"{inp}"
        if inp_str in unique_input_strs:
            new_inputs.append(inp)
            new_results.append(res)
            unique_input_strs.remove(inp_str)

    return new_inputs, new_results


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug-tasks", nargs="+", default=[], type=int)

    args = parser.parse_args()
    console = Console()

    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(int(10e8))

    plus_problems = get_mbpp_plus(mini=False)
    dataset_hash = get_mbpp_plus_hash()

    original_mbpp = get_mbpp()

    compatible_problems = {}
    expected_outputs = get_groundtruth(
        plus_problems, dataset_hash, MBPP_OUTPUT_NOT_NONE_TASKS
    )

    # debugging: monitoring test code size
    id2bytes = {}

    n_workers = max(1, multiprocessing.cpu_count() // 4)
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = []
        for task_id, plus_form in tqdm(plus_problems.items()):
            # expected MBPP task_id is numbers directly
            # i.e., "666" instead of "Mbpp/666"
            # But in EvalPlus the task_id is "Mbpp/666"
            task_id_int = int(task_id.split("/")[-1])
            if args.debug_tasks and task_id_int not in args.debug_tasks:
                continue

            compatible_form = {
                "task_id": task_id_int,
                "code": plus_form["canonical_solution"],
                "prompt": original_mbpp[str(task_id_int)]["prompt"],
                "source_file": original_mbpp[str(task_id_int)]["source_file"],
                "test_imports": original_mbpp[str(task_id_int)]["test_imports"],
                "test_list": original_mbpp[str(task_id_int)]["test_list"],
            }
            compatible_problems[task_id_int] = compatible_form

            inputs = (
                plus_form["base_input"] + plus_form["plus_input"]
                if len(plus_form["plus_input"]) > 0
                else plus_form["base_input"]
            )
            results = (
                expected_outputs[task_id]["base"] + expected_outputs[task_id]["plus"]
            )

            inputs, results = deduplicate(inputs, results)

            assert len(inputs) == len(results)
            atol = plus_form["atol"]

            futures.append(
                executor.submit(
                    synthesize_test_code,
                    task_id_int,
                    plus_form["entry_point"],
                    inputs,
                    results,
                    compatible_form["code"],
                    atol,
                )
            )

        for future in tqdm(as_completed(futures), total=len(plus_problems)):
            task_id, test_code = future.result()
            # syntax check of test_code
            ast.parse(test_code)
            # ground-truth check
            task = plus_problems[f"Mbpp/{task_id}"]
            exec_code = (
                task["prompt"] + "\n" + task["canonical_solution"] + "\n" + test_code
            )

            # run the code in a subprocess
            def test():
                try:
                    exec(exec_code, globals())
                except Exception:
                    print_exc()
                    raise

            p = multiprocessing.Process(target=test)
            p.start()
            p.join(timeout=20)
            assert not p.is_alive(), f"Timeout for Mbpp/{task_id}!"
            p.terminate()
            p.join()
            if p.exitcode != 0:
                console.print(Syntax(exec_code, "python", line_numbers=True))
                raise RuntimeError(f"Error for Mbpp/{task_id}")

            id2bytes[task_id] = len(test_code.encode("utf-8"))
            compatible_problems[task_id]["test"] = test_code

    # print the top-10 largest test code
    print("Top-10 largest test code comes from problems (in megabytes):")
    for task_id, size in sorted(id2bytes.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]:
        print(f"{task_id}:\t{size / 1024 / 1024:.2f}mb")

    if args.debug_tasks:
        for problem in compatible_problems.values():
            print("--- debugging:", problem["task_id"])
            print('"""\n' + problem["prompt"] + '\n"""\n' + problem["code"])
            test_code = problem["test"]
            if len(test_code) <= 1024:
                print(test_code)
            else:
                print(problem["test"][:1024], "...")
                print("...", problem["test"][-1024:])
    else:
        with open(f"MbppPlus-OriginFmt-{MBPP_PLUS_VERSION}.jsonl", "w") as f:
            for problem in compatible_problems.values():
                f.write(json.dumps(problem) + "\n")


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3279.py ===
#
# This file is part of pyasn1-modules.
#
# Copyright (c) 2017, Danielle Madeley <danielle@madeley.id.au>
# License: http://snmplabs.com/pyasn1/license.html
#
# Modified by Russ Housley to add maps for use with opentypes.
#
# Algorithms and Identifiers for Internet X.509 Certificates and CRLs
#
# Derived from RFC 3279:
# https://www.rfc-editor.org/rfc/rfc3279.txt
#
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import univ

from pyasn1_modules import rfc5280


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


md2 = _OID(1, 2, 840, 113549, 2, 2)
md5 = _OID(1, 2, 840, 113549, 2, 5)
id_sha1 = _OID(1, 3, 14, 3, 2, 26)
id_dsa = _OID(1, 2, 840, 10040, 4, 1)


class DSAPublicKey(univ.Integer):
    pass


class Dss_Parms(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('p', univ.Integer()),
        namedtype.NamedType('q', univ.Integer()),
        namedtype.NamedType('g', univ.Integer())
    )


id_dsa_with_sha1 = _OID(1, 2, 840, 10040, 4, 3)


class Dss_Sig_Value(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('r', univ.Integer()),
        namedtype.NamedType('s', univ.Integer())
    )


pkcs_1 = _OID(1, 2, 840, 113549, 1, 1)
rsaEncryption = _OID(pkcs_1, 1)
md2WithRSAEncryption = _OID(pkcs_1, 2)
md5WithRSAEncryption = _OID(pkcs_1, 4)
sha1WithRSAEncryption = _OID(pkcs_1, 5)


class RSAPublicKey(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('modulus', univ.Integer()),
        namedtype.NamedType('publicExponent', univ.Integer())
    )


dhpublicnumber = _OID(1, 2, 840, 10046, 2, 1)


class DHPublicKey(univ.Integer):
    pass


class ValidationParms(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('seed', univ.BitString()),
        namedtype.NamedType('pgenCounter', univ.Integer())
    )


class DomainParameters(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('p', univ.Integer()),
        namedtype.NamedType('g', univ.Integer()),
        namedtype.NamedType('q', univ.Integer()),
        namedtype.OptionalNamedType('j', univ.Integer()),
        namedtype.OptionalNamedType('validationParms', ValidationParms())
    )


id_keyExchangeAlgorithm = _OID(2, 16, 840, 1, 101, 2, 1, 1, 22)


class KEA_Parms_Id(univ.OctetString):
    pass


ansi_X9_62 = _OID(1, 2, 840, 10045)


class FieldID(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('fieldType', univ.ObjectIdentifier()),
        namedtype.NamedType('parameters', univ.Any())
    )


id_ecSigType = _OID(ansi_X9_62, 4)
ecdsa_with_SHA1 = _OID(id_ecSigType, 1)


class ECDSA_Sig_Value(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('r', univ.Integer()),
        namedtype.NamedType('s', univ.Integer())
    )


id_fieldType = _OID(ansi_X9_62, 1)
prime_field = _OID(id_fieldType, 1)


class Prime_p(univ.Integer):
    pass


characteristic_two_field = _OID(id_fieldType, 2)


class Characteristic_two(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('m', univ.Integer()),
        namedtype.NamedType('basis', univ.ObjectIdentifier()),
        namedtype.NamedType('parameters', univ.Any())
    )


id_characteristic_two_basis = _OID(characteristic_two_field, 3)
gnBasis = _OID(id_characteristic_two_basis, 1)
tpBasis = _OID(id_characteristic_two_basis, 2)


class Trinomial(univ.Integer):
    pass


ppBasis = _OID(id_characteristic_two_basis, 3)


class Pentanomial(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('k1', univ.Integer()),
        namedtype.NamedType('k2', univ.Integer()),
        namedtype.NamedType('k3', univ.Integer())
    )


class FieldElement(univ.OctetString):
    pass


class ECPoint(univ.OctetString):
    pass


class Curve(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('a', FieldElement()),
        namedtype.NamedType('b', FieldElement()),
        namedtype.OptionalNamedType('seed', univ.BitString())
    )


class ECPVer(univ.Integer):
    namedValues = namedval.NamedValues(
        ('ecpVer1', 1)
    )


class ECParameters(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('version', ECPVer()),
        namedtype.NamedType('fieldID', FieldID()),
        namedtype.NamedType('curve', Curve()),
        namedtype.NamedType('base', ECPoint()),
        namedtype.NamedType('order', univ.Integer()),
        namedtype.OptionalNamedType('cofactor', univ.Integer())
    )


class EcpkParameters(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('ecParameters', ECParameters()),
        namedtype.NamedType('namedCurve', univ.ObjectIdentifier()),
        namedtype.NamedType('implicitlyCA', univ.Null())
    )


id_publicKeyType = _OID(ansi_X9_62, 2)
id_ecPublicKey = _OID(id_publicKeyType, 1)

ellipticCurve = _OID(ansi_X9_62, 3)

c_TwoCurve = _OID(ellipticCurve, 0)
c2pnb163v1 = _OID(c_TwoCurve, 1)
c2pnb163v2 = _OID(c_TwoCurve, 2)
c2pnb163v3 = _OID(c_TwoCurve, 3)
c2pnb176w1 = _OID(c_TwoCurve, 4)
c2tnb191v1 = _OID(c_TwoCurve, 5)
c2tnb191v2 = _OID(c_TwoCurve, 6)
c2tnb191v3 = _OID(c_TwoCurve, 7)
c2onb191v4 = _OID(c_TwoCurve, 8)
c2onb191v5 = _OID(c_TwoCurve, 9)
c2pnb208w1 = _OID(c_TwoCurve, 10)
c2tnb239v1 = _OID(c_TwoCurve, 11)
c2tnb239v2 = _OID(c_TwoCurve, 12)
c2tnb239v3 = _OID(c_TwoCurve, 13)
c2onb239v4 = _OID(c_TwoCurve, 14)
c2onb239v5 = _OID(c_TwoCurve, 15)
c2pnb272w1 = _OID(c_TwoCurve, 16)
c2pnb304w1 = _OID(c_TwoCurve, 17)
c2tnb359v1 = _OID(c_TwoCurve, 18)
c2pnb368w1 = _OID(c_TwoCurve, 19)
c2tnb431r1 = _OID(c_TwoCurve, 20)

primeCurve = _OID(ellipticCurve, 1)
prime192v1 = _OID(primeCurve, 1)
prime192v2 = _OID(primeCurve, 2)
prime192v3 = _OID(primeCurve, 3)
prime239v1 = _OID(primeCurve, 4)
prime239v2 = _OID(primeCurve, 5)
prime239v3 = _OID(primeCurve, 6)
prime256v1 = _OID(primeCurve, 7)


# Map of Algorithm Identifier OIDs to Parameters added to the
# ones in rfc5280.py.  Do not add OIDs with absent paramaters.

_algorithmIdentifierMapUpdate = {
    md2: univ.Null(""),
    md5: univ.Null(""),
    id_sha1: univ.Null(""),
    id_dsa: Dss_Parms(),
    rsaEncryption: univ.Null(""),
    md2WithRSAEncryption: univ.Null(""),
    md5WithRSAEncryption: univ.Null(""),
    sha1WithRSAEncryption: univ.Null(""),
    dhpublicnumber: DomainParameters(),
    id_keyExchangeAlgorithm: KEA_Parms_Id(),
    id_ecPublicKey: EcpkParameters(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc8018.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# PKCS #5: Password-Based Cryptography Specification, Version 2.1
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc8018.txt
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import univ

from pyasn1_modules import rfc3565
from pyasn1_modules import rfc5280

MAX = float('inf')

def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


# Import from RFC 3565

AES_IV = rfc3565.AES_IV


# Import from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Basic object identifiers

nistAlgorithms = _OID(2, 16, 840, 1, 101, 3, 4)

aes = _OID(nistAlgorithms, 1)

oiw = _OID(1, 3, 14)

rsadsi = _OID(1, 2, 840, 113549)

pkcs = _OID(rsadsi, 1)

digestAlgorithm = _OID(rsadsi, 2)

encryptionAlgorithm = _OID(rsadsi, 3)

pkcs_5 = _OID(pkcs, 5)



# HMAC object identifiers

id_hmacWithSHA1 = _OID(digestAlgorithm, 7)

id_hmacWithSHA224 = _OID(digestAlgorithm, 8)

id_hmacWithSHA256 = _OID(digestAlgorithm, 9)

id_hmacWithSHA384 = _OID(digestAlgorithm, 10)

id_hmacWithSHA512 = _OID(digestAlgorithm, 11)

id_hmacWithSHA512_224 = _OID(digestAlgorithm, 12)

id_hmacWithSHA512_256 = _OID(digestAlgorithm, 13)


# PBES1 object identifiers

pbeWithMD2AndDES_CBC = _OID(pkcs_5, 1)

pbeWithMD2AndRC2_CBC = _OID(pkcs_5, 4)

pbeWithMD5AndDES_CBC = _OID(pkcs_5, 3)

pbeWithMD5AndRC2_CBC = _OID(pkcs_5, 6)

pbeWithSHA1AndDES_CBC = _OID(pkcs_5, 10)

pbeWithSHA1AndRC2_CBC = _OID(pkcs_5, 11)


# Supporting techniques object identifiers

desCBC = _OID(oiw, 3, 2, 7)

des_EDE3_CBC = _OID(encryptionAlgorithm, 7)

rc2CBC = _OID(encryptionAlgorithm, 2)

rc5_CBC_PAD = _OID(encryptionAlgorithm, 9)

aes128_CBC_PAD = _OID(aes, 2)

aes192_CBC_PAD = _OID(aes, 22)

aes256_CBC_PAD = _OID(aes, 42)


# PBES1

class PBEParameter(univ.Sequence):
    pass

PBEParameter.componentType = namedtype.NamedTypes(
    namedtype.NamedType('salt', univ.OctetString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(8, 8))),
    namedtype.NamedType('iterationCount', univ.Integer())
)


# PBES2

id_PBES2 = _OID(pkcs_5, 13)


class PBES2_params(univ.Sequence):
    pass

PBES2_params.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyDerivationFunc', AlgorithmIdentifier()),
    namedtype.NamedType('encryptionScheme', AlgorithmIdentifier())
)


# PBMAC1

id_PBMAC1 = _OID(pkcs_5, 14)


class PBMAC1_params(univ.Sequence):
    pass

PBMAC1_params.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyDerivationFunc', AlgorithmIdentifier()),
    namedtype.NamedType('messageAuthScheme', AlgorithmIdentifier())
)


# PBKDF2

id_PBKDF2 = _OID(pkcs_5, 12)


algid_hmacWithSHA1 = AlgorithmIdentifier()
algid_hmacWithSHA1['algorithm'] = id_hmacWithSHA1
algid_hmacWithSHA1['parameters'] = univ.Null("")


class PBKDF2_params(univ.Sequence):
    pass

PBKDF2_params.componentType = namedtype.NamedTypes(
    namedtype.NamedType('salt', univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('specified', univ.OctetString()),
        namedtype.NamedType('otherSource', AlgorithmIdentifier())
    ))),
    namedtype.NamedType('iterationCount', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, MAX))),
    namedtype.OptionalNamedType('keyLength', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(1, MAX))),
    namedtype.DefaultedNamedType('prf', algid_hmacWithSHA1)
)


# RC2 CBC algorithm parameter

class RC2_CBC_Parameter(univ.Sequence):
    pass

RC2_CBC_Parameter.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('rc2ParameterVersion', univ.Integer()),
    namedtype.NamedType('iv', univ.OctetString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(8, 8)))
)


# RC5 CBC algorithm parameter

class RC5_CBC_Parameters(univ.Sequence):
    pass

RC5_CBC_Parameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('version',
        univ.Integer(namedValues=namedval.NamedValues(('v1_0', 16))).subtype(
            subtypeSpec=constraint.SingleValueConstraint(16))),
    namedtype.NamedType('rounds',
        univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(8, 127))),
    namedtype.NamedType('blockSizeInBits',
        univ.Integer().subtype(subtypeSpec=constraint.SingleValueConstraint(64, 128))),
    namedtype.OptionalNamedType('iv', univ.OctetString())
)


# Initialization Vector for AES: OCTET STRING (SIZE(16))

class AES_IV(univ.OctetString):
    pass

AES_IV.subtypeSpec = constraint.ValueSizeConstraint(16, 16)


# Initialization Vector for DES: OCTET STRING (SIZE(8))

class DES_IV(univ.OctetString):
    pass

DES_IV.subtypeSpec = constraint.ValueSizeConstraint(8, 8)


# Update the Algorithm Identifier map

_algorithmIdentifierMapUpdate = {
    # PBKDF2-PRFs
    id_hmacWithSHA1: univ.Null(),
    id_hmacWithSHA224: univ.Null(),
    id_hmacWithSHA256: univ.Null(),
    id_hmacWithSHA384: univ.Null(),
    id_hmacWithSHA512: univ.Null(),
    id_hmacWithSHA512_224: univ.Null(),
    id_hmacWithSHA512_256: univ.Null(),
    # PBES1Algorithms
    pbeWithMD2AndDES_CBC: PBEParameter(),
    pbeWithMD2AndRC2_CBC: PBEParameter(),
    pbeWithMD5AndDES_CBC: PBEParameter(),
    pbeWithMD5AndRC2_CBC: PBEParameter(),
    pbeWithSHA1AndDES_CBC: PBEParameter(),
    pbeWithSHA1AndRC2_CBC: PBEParameter(),
    # PBES2Algorithms
    id_PBES2: PBES2_params(),
    # PBES2-KDFs
    id_PBKDF2: PBKDF2_params(),
    # PBMAC1Algorithms
    id_PBMAC1: PBMAC1_params(),
    # SupportingAlgorithms
    desCBC: DES_IV(),
    des_EDE3_CBC: DES_IV(),
    rc2CBC: RC2_CBC_Parameter(),
    rc5_CBC_PAD: RC5_CBC_Parameters(),
    aes128_CBC_PAD: AES_IV(),
    aes192_CBC_PAD: AES_IV(),
    aes256_CBC_PAD: AES_IV(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles_xml_rpc.py ===
import sys
import threading
import traceback
import warnings

from _pydev_bundle._pydev_filesystem_encoding import getfilesystemencoding
from _pydev_bundle.pydev_imports import _queue, xmlrpclib
from _pydevd_bundle.pydevd_constants import Null

Queue = _queue.Queue

# This may happen in IronPython (in Python it shouldn't happen as there are
# 'fast' replacements that are used in xmlrpclib.py)
warnings.filterwarnings("ignore", "The xmllib module is obsolete.*", DeprecationWarning)

file_system_encoding = getfilesystemencoding()


# =======================================================================================================================
# _ServerHolder
# =======================================================================================================================
class _ServerHolder:
    """
    Helper so that we don't have to use a global here.
    """

    SERVER = None


# =======================================================================================================================
# set_server
# =======================================================================================================================
def set_server(server):
    _ServerHolder.SERVER = server


# =======================================================================================================================
# ParallelNotification
# =======================================================================================================================
class ParallelNotification(object):
    def __init__(self, method, args):
        self.method = method
        self.args = args

    def to_tuple(self):
        return self.method, self.args


# =======================================================================================================================
# KillServer
# =======================================================================================================================
class KillServer(object):
    pass


# =======================================================================================================================
# ServerFacade
# =======================================================================================================================
class ServerFacade(object):
    def __init__(self, notifications_queue):
        self.notifications_queue = notifications_queue

    def notifyTestsCollected(self, *args):
        self.notifications_queue.put_nowait(ParallelNotification("notifyTestsCollected", args))

    def notifyConnected(self, *args):
        self.notifications_queue.put_nowait(ParallelNotification("notifyConnected", args))

    def notifyTestRunFinished(self, *args):
        self.notifications_queue.put_nowait(ParallelNotification("notifyTestRunFinished", args))

    def notifyStartTest(self, *args):
        self.notifications_queue.put_nowait(ParallelNotification("notifyStartTest", args))

    def notifyTest(self, *args):
        new_args = []
        for arg in args:
            new_args.append(_encode_if_needed(arg))
        args = tuple(new_args)
        self.notifications_queue.put_nowait(ParallelNotification("notifyTest", args))


# =======================================================================================================================
# ServerComm
# =======================================================================================================================
class ServerComm(threading.Thread):
    def __init__(self, notifications_queue, port, daemon=False):
        # If daemon is False, wait for all the notifications to be passed before exiting!
        threading.Thread.__init__(self, daemon=daemon)
        self.finished = False
        self.notifications_queue = notifications_queue

        from _pydev_bundle import pydev_localhost

        # It is necessary to specify an encoding, that matches
        # the encoding of all bytes-strings passed into an
        # XMLRPC call: "All 8-bit strings in the data structure are assumed to use the
        # packet encoding.  Unicode strings are automatically converted,
        # where necessary."
        # Byte strings most likely come from file names.
        encoding = file_system_encoding
        if encoding == "mbcs":
            # Windos symbolic name for the system encoding CP_ACP.
            # We need to convert it into a encoding that is recognized by Java.
            # Unfortunately this is not always possible. You could use
            # GetCPInfoEx and get a name similar to "windows-1251". Then
            # you need a table to translate on a best effort basis. Much to complicated.
            # ISO-8859-1 is good enough.
            encoding = "ISO-8859-1"

        self.server = xmlrpclib.Server("http://%s:%s" % (pydev_localhost.get_localhost(), port), encoding=encoding)

    def run(self):
        while True:
            kill_found = False
            commands = []
            command = self.notifications_queue.get(block=True)
            if isinstance(command, KillServer):
                kill_found = True
            else:
                assert isinstance(command, ParallelNotification)
                commands.append(command.to_tuple())

            try:
                while True:
                    command = self.notifications_queue.get(block=False)  # No block to create a batch.
                    if isinstance(command, KillServer):
                        kill_found = True
                    else:
                        assert isinstance(command, ParallelNotification)
                        commands.append(command.to_tuple())
            except:
                pass  # That's OK, we're getting it until it becomes empty so that we notify multiple at once.

            if commands:
                try:
                    self.server.notifyCommands(commands)
                except:
                    traceback.print_exc()

            if kill_found:
                self.finished = True
                return


# =======================================================================================================================
# initialize_server
# =======================================================================================================================
def initialize_server(port, daemon=False):
    if _ServerHolder.SERVER is None:
        if port is not None:
            notifications_queue = Queue()
            _ServerHolder.SERVER = ServerFacade(notifications_queue)
            _ServerHolder.SERVER_COMM = ServerComm(notifications_queue, port, daemon)
            _ServerHolder.SERVER_COMM.start()
        else:
            # Create a null server, so that we keep the interface even without any connection.
            _ServerHolder.SERVER = Null()
            _ServerHolder.SERVER_COMM = Null()

    try:
        if _ServerHolder.SERVER is not None:
            _ServerHolder.SERVER.notifyConnected()
    except:
        traceback.print_exc()


# =======================================================================================================================
# notifyTest
# =======================================================================================================================
def notifyTestsCollected(tests_count):
    assert tests_count is not None
    try:
        if _ServerHolder.SERVER is not None:
            _ServerHolder.SERVER.notifyTestsCollected(tests_count)
    except:
        traceback.print_exc()


# =======================================================================================================================
# notifyStartTest
# =======================================================================================================================
def notifyStartTest(file, test):
    """
    @param file: the tests file (c:/temp/test.py)
    @param test: the test ran (i.e.: TestCase.test1)
    """
    assert file is not None
    if test is None:
        test = ""  # Could happen if we have an import error importing module.

    try:
        if _ServerHolder.SERVER is not None:
            _ServerHolder.SERVER.notifyStartTest(file, test)
    except:
        traceback.print_exc()


def _encode_if_needed(obj):
    # In the java side we expect strings to be ISO-8859-1 (org.python.pydev.debug.pyunit.PyUnitServer.initializeDispatches().new Dispatch() {...}.getAsStr(Object))
    if isinstance(obj, str):  # Unicode in py3
        return xmlrpclib.Binary(obj.encode("ISO-8859-1", "xmlcharrefreplace"))

    elif isinstance(obj, bytes):
        try:
            return xmlrpclib.Binary(obj.decode(sys.stdin.encoding, "replace").encode("ISO-8859-1", "xmlcharrefreplace"))
        except:
            return xmlrpclib.Binary(obj)  # bytes already

    return obj


# =======================================================================================================================
# notifyTest
# =======================================================================================================================
def notifyTest(cond, captured_output, error_contents, file, test, time):
    """
    @param cond: ok, fail, error
    @param captured_output: output captured from stdout
    @param captured_output: output captured from stderr
    @param file: the tests file (c:/temp/test.py)
    @param test: the test ran (i.e.: TestCase.test1)
    @param time: float with the number of seconds elapsed
    """
    if _ServerHolder.SERVER is None:
        return

    assert cond is not None
    assert captured_output is not None
    assert error_contents is not None
    assert file is not None
    if test is None:
        test = ""  # Could happen if we have an import error importing module.
    assert time is not None
    try:
        captured_output = _encode_if_needed(captured_output)
        error_contents = _encode_if_needed(error_contents)

        _ServerHolder.SERVER.notifyTest(cond, captured_output, error_contents, file, test, time)
    except:
        traceback.print_exc()


# =======================================================================================================================
# notifyTestRunFinished
# =======================================================================================================================
def notifyTestRunFinished(total_time):
    assert total_time is not None
    try:
        if _ServerHolder.SERVER is not None:
            _ServerHolder.SERVER.notifyTestRunFinished(total_time)
    except:
        traceback.print_exc()


# =======================================================================================================================
# force_server_kill
# =======================================================================================================================
def force_server_kill():
    _ServerHolder.SERVER_COMM.notifications_queue.put_nowait(KillServer())

# === NexusCore/openenv\Lib\site-packages\fontTools\designspaceLib\statNames.py ===
"""Compute name information for a given location in user-space coordinates
using STAT data. This can be used to fill-in automatically the names of an
instance:

.. code:: python

    instance = doc.instances[0]
    names = getStatNames(doc, instance.getFullUserLocation(doc))
    print(names.styleNames)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple, Union
import logging

from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisLabelDescriptor,
    DesignSpaceDocument,
    DiscreteAxisDescriptor,
    SimpleLocationDict,
    SourceDescriptor,
)

LOGGER = logging.getLogger(__name__)

RibbiStyleName = Union[
    Literal["regular"],
    Literal["bold"],
    Literal["italic"],
    Literal["bold italic"],
]

BOLD_ITALIC_TO_RIBBI_STYLE = {
    (False, False): "regular",
    (False, True): "italic",
    (True, False): "bold",
    (True, True): "bold italic",
}


@dataclass
class StatNames:
    """Name data generated from the STAT table information."""

    familyNames: Dict[str, str]
    styleNames: Dict[str, str]
    postScriptFontName: Optional[str]
    styleMapFamilyNames: Dict[str, str]
    styleMapStyleName: Optional[RibbiStyleName]


def getStatNames(
    doc: DesignSpaceDocument, userLocation: SimpleLocationDict
) -> StatNames:
    """Compute the family, style, PostScript names of the given ``userLocation``
    using the document's STAT information.

    Also computes localizations.

    If not enough STAT data is available for a given name, either its dict of
    localized names will be empty (family and style names), or the name will be
    None (PostScript name).

    Note: this method does not consider info attached to the instance, like
    family name. The user needs to override all names on an instance that STAT
    information would compute differently than desired.

    .. versionadded:: 5.0
    """
    familyNames: Dict[str, str] = {}
    defaultSource: Optional[SourceDescriptor] = doc.findDefault()
    if defaultSource is None:
        LOGGER.warning("Cannot determine default source to look up family name.")
    elif defaultSource.familyName is None:
        LOGGER.warning(
            "Cannot look up family name, assign the 'familyname' attribute to the default source."
        )
    else:
        familyNames = {
            "en": defaultSource.familyName,
            **defaultSource.localisedFamilyName,
        }

    styleNames: Dict[str, str] = {}
    # If a free-standing label matches the location, use it for name generation.
    label = doc.labelForUserLocation(userLocation)
    if label is not None:
        styleNames = {"en": label.name, **label.labelNames}
    # Otherwise, scour the axis labels for matches.
    else:
        # Gather all languages in which at least one translation is provided
        # Then build names for all these languages, but fallback to English
        # whenever a translation is missing.
        labels = _getAxisLabelsForUserLocation(doc.axes, userLocation)
        if labels:
            languages = set(
                language for label in labels for language in label.labelNames
            )
            languages.add("en")
            for language in languages:
                styleName = " ".join(
                    label.labelNames.get(language, label.defaultName)
                    for label in labels
                    if not label.elidable
                )
                if not styleName and doc.elidedFallbackName is not None:
                    styleName = doc.elidedFallbackName
                styleNames[language] = styleName

    if "en" not in familyNames or "en" not in styleNames:
        # Not enough information to compute PS names of styleMap names
        return StatNames(
            familyNames=familyNames,
            styleNames=styleNames,
            postScriptFontName=None,
            styleMapFamilyNames={},
            styleMapStyleName=None,
        )

    postScriptFontName = f"{familyNames['en']}-{styleNames['en']}".replace(" ", "")

    styleMapStyleName, regularUserLocation = _getRibbiStyle(doc, userLocation)

    styleNamesForStyleMap = styleNames
    if regularUserLocation != userLocation:
        regularStatNames = getStatNames(doc, regularUserLocation)
        styleNamesForStyleMap = regularStatNames.styleNames

    styleMapFamilyNames = {}
    for language in set(familyNames).union(styleNames.keys()):
        familyName = familyNames.get(language, familyNames["en"])
        styleName = styleNamesForStyleMap.get(language, styleNamesForStyleMap["en"])
        styleMapFamilyNames[language] = (familyName + " " + styleName).strip()

    return StatNames(
        familyNames=familyNames,
        styleNames=styleNames,
        postScriptFontName=postScriptFontName,
        styleMapFamilyNames=styleMapFamilyNames,
        styleMapStyleName=styleMapStyleName,
    )


def _getSortedAxisLabels(
    axes: list[Union[AxisDescriptor, DiscreteAxisDescriptor]],
) -> Dict[str, list[AxisLabelDescriptor]]:
    """Returns axis labels sorted by their ordering, with unordered ones appended as
    they are listed."""

    # First, get the axis labels with explicit ordering...
    sortedAxes = sorted(
        (axis for axis in axes if axis.axisOrdering is not None),
        key=lambda a: a.axisOrdering,
    )
    sortedLabels: Dict[str, list[AxisLabelDescriptor]] = {
        axis.name: axis.axisLabels for axis in sortedAxes
    }

    # ... then append the others in the order they appear.
    # NOTE: This relies on Python 3.7+ dict's preserved insertion order.
    for axis in axes:
        if axis.axisOrdering is None:
            sortedLabels[axis.name] = axis.axisLabels

    return sortedLabels


def _getAxisLabelsForUserLocation(
    axes: list[Union[AxisDescriptor, DiscreteAxisDescriptor]],
    userLocation: SimpleLocationDict,
) -> list[AxisLabelDescriptor]:
    labels: list[AxisLabelDescriptor] = []

    allAxisLabels = _getSortedAxisLabels(axes)
    if allAxisLabels.keys() != userLocation.keys():
        LOGGER.warning(
            f"Mismatch between user location '{userLocation.keys()}' and available "
            f"labels for '{allAxisLabels.keys()}'."
        )

    for axisName, axisLabels in allAxisLabels.items():
        userValue = userLocation[axisName]
        label: Optional[AxisLabelDescriptor] = next(
            (
                l
                for l in axisLabels
                if l.userValue == userValue
                or (
                    l.userMinimum is not None
                    and l.userMaximum is not None
                    and l.userMinimum <= userValue <= l.userMaximum
                )
            ),
            None,
        )
        if label is None:
            LOGGER.debug(
                f"Document needs a label for axis '{axisName}', user value '{userValue}'."
            )
        else:
            labels.append(label)

    return labels


def _getRibbiStyle(
    self: DesignSpaceDocument, userLocation: SimpleLocationDict
) -> Tuple[RibbiStyleName, SimpleLocationDict]:
    """Compute the RIBBI style name of the given user location,
    return the location of the matching Regular in the RIBBI group.

    .. versionadded:: 5.0
    """
    regularUserLocation = {}
    axes_by_tag = {axis.tag: axis for axis in self.axes}

    bold: bool = False
    italic: bool = False

    axis = axes_by_tag.get("wght")
    if axis is not None:
        for regular_label in axis.axisLabels:
            if (
                regular_label.linkedUserValue == userLocation[axis.name]
                # In the "recursive" case where both the Regular has
                # linkedUserValue pointing the Bold, and the Bold has
                # linkedUserValue pointing to the Regular, only consider the
                # first case: Regular (e.g. 400) has linkedUserValue pointing to
                # Bold (e.g. 700, higher than Regular)
                and regular_label.userValue < regular_label.linkedUserValue
            ):
                regularUserLocation[axis.name] = regular_label.userValue
                bold = True
                break

    axis = axes_by_tag.get("ital") or axes_by_tag.get("slnt")
    if axis is not None:
        for upright_label in axis.axisLabels:
            if (
                upright_label.linkedUserValue == userLocation[axis.name]
                # In the "recursive" case where both the Upright has
                # linkedUserValue pointing the Italic, and the Italic has
                # linkedUserValue pointing to the Upright, only consider the
                # first case: Upright (e.g. ital=0, slant=0) has
                # linkedUserValue pointing to Italic (e.g ital=1, slant=-12 or
                # slant=12 for backwards italics, in any case higher than
                # Upright in absolute value, hence the abs() below.
                and abs(upright_label.userValue) < abs(upright_label.linkedUserValue)
            ):
                regularUserLocation[axis.name] = upright_label.userValue
                italic = True
                break

    return BOLD_ITALIC_TO_RIBBI_STYLE[bold, italic], {
        **userLocation,
        **regularUserLocation,
    }

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\avar.py ===
from fontTools.varLib import _add_avar, load_designspace
from fontTools.varLib.models import VariationModel
from fontTools.varLib.varStore import VarStoreInstancer
from fontTools.misc.fixedTools import fixedToFloat as fi2fl
from fontTools.misc.cliTools import makeOutputFileName
from itertools import product
import logging

log = logging.getLogger("fontTools.varLib.avar")


def _denormalize(v, axis):
    if v >= 0:
        return axis.defaultValue + v * (axis.maxValue - axis.defaultValue)
    else:
        return axis.defaultValue + v * (axis.defaultValue - axis.minValue)


def _pruneLocations(locations, poles, axisTags):
    # Now we have all the input locations, find which ones are
    # not needed and remove them.

    # Note: This algorithm is heavily tied to how VariationModel
    # is implemented.  It assumes that input was extracted from
    # VariationModel-generated object, like an ItemVariationStore
    # created by fontmake using varLib.models.VariationModel.
    # Some CoPilot blabbering:
    # I *think* I can prove that this algorithm is correct, but
    # I'm not 100% sure.  It's possible that there are edge cases
    # where this algorithm will fail.  I'm not sure how to prove
    # that it's correct, but I'm also not sure how to prove that
    # it's incorrect.  I'm not sure how to write a test case that
    # would prove that it's incorrect.  I'm not sure how to write
    # a test case that would prove that it's correct.

    model = VariationModel(locations, axisTags)
    modelMapping = model.mapping
    modelSupports = model.supports
    pins = {tuple(k.items()): None for k in poles}
    for location in poles:
        i = locations.index(location)
        i = modelMapping[i]
        support = modelSupports[i]
        supportAxes = set(support.keys())
        for axisTag, (minV, _, maxV) in support.items():
            for v in (minV, maxV):
                if v in (-1, 0, 1):
                    continue
                for pin in pins.keys():
                    pinLocation = dict(pin)
                    pinAxes = set(pinLocation.keys())
                    if pinAxes != supportAxes:
                        continue
                    if axisTag not in pinAxes:
                        continue
                    if pinLocation[axisTag] == v:
                        break
                else:
                    # No pin found. Go through the previous masters
                    # and find a suitable pin.  Going backwards is
                    # better because it can find a pin that is close
                    # to the pole in more dimensions, and reducing
                    # the total number of pins needed.
                    for candidateIdx in range(i - 1, -1, -1):
                        candidate = modelSupports[candidateIdx]
                        candidateAxes = set(candidate.keys())
                        if candidateAxes != supportAxes:
                            continue
                        if axisTag not in candidateAxes:
                            continue
                        candidate = {
                            k: defaultV for k, (_, defaultV, _) in candidate.items()
                        }
                        if candidate[axisTag] == v:
                            pins[tuple(candidate.items())] = None
                            break
                    else:
                        assert False, "No pin found"
    return [dict(t) for t in pins.keys()]


def mappings_from_avar(font, denormalize=True):
    fvarAxes = font["fvar"].axes
    axisMap = {a.axisTag: a for a in fvarAxes}
    axisTags = [a.axisTag for a in fvarAxes]
    axisIndexes = {a.axisTag: i for i, a in enumerate(fvarAxes)}
    if "avar" not in font:
        return {}, {}
    avar = font["avar"]
    axisMaps = {
        tag: seg
        for tag, seg in avar.segments.items()
        if seg and seg != {-1: -1, 0: 0, 1: 1}
    }
    mappings = []

    if getattr(avar, "majorVersion", 1) == 2:
        varStore = avar.table.VarStore
        regions = varStore.VarRegionList.Region

        # Find all the input locations; this finds "poles", that are
        # locations of the peaks, and "corners", that are locations
        # of the corners of the regions.  These two sets of locations
        # together constitute inputLocations to consider.

        poles = {(): None}  # Just using it as an ordered set
        inputLocations = set({()})
        for varData in varStore.VarData:
            regionIndices = varData.VarRegionIndex
            for regionIndex in regionIndices:
                peakLocation = []
                corners = []
                region = regions[regionIndex]
                for axisIndex, axis in enumerate(region.VarRegionAxis):
                    if axis.PeakCoord == 0:
                        continue
                    axisTag = axisTags[axisIndex]
                    peakLocation.append((axisTag, axis.PeakCoord))
                    corner = []
                    if axis.StartCoord != 0:
                        corner.append((axisTag, axis.StartCoord))
                    if axis.EndCoord != 0:
                        corner.append((axisTag, axis.EndCoord))
                    corners.append(corner)
                corners = set(product(*corners))
                peakLocation = tuple(peakLocation)
                poles[peakLocation] = None
                inputLocations.add(peakLocation)
                inputLocations.update(corners)

        # Sort them by number of axes, then by axis order
        inputLocations = [
            dict(t)
            for t in sorted(
                inputLocations,
                key=lambda t: (len(t), tuple(axisIndexes[tag] for tag, _ in t)),
            )
        ]
        poles = [dict(t) for t in poles.keys()]
        inputLocations = _pruneLocations(inputLocations, list(poles), axisTags)

        # Find the output locations, at input locations
        varIdxMap = avar.table.VarIdxMap
        instancer = VarStoreInstancer(varStore, fvarAxes)
        for location in inputLocations:
            instancer.setLocation(location)
            outputLocation = {}
            for axisIndex, axisTag in enumerate(axisTags):
                varIdx = axisIndex
                if varIdxMap is not None:
                    varIdx = varIdxMap[varIdx]
                delta = instancer[varIdx]
                if delta != 0:
                    v = location.get(axisTag, 0)
                    v = v + fi2fl(delta, 14)
                    # See https://github.com/fonttools/fonttools/pull/3598#issuecomment-2266082009
                    # v = max(-1, min(1, v))
                    outputLocation[axisTag] = v
            mappings.append((location, outputLocation))

        # Remove base master we added, if it maps to the default location
        assert mappings[0][0] == {}
        if mappings[0][1] == {}:
            mappings.pop(0)

    if denormalize:
        for tag, seg in axisMaps.items():
            if tag not in axisMap:
                raise ValueError(f"Unknown axis tag {tag}")
            denorm = lambda v: _denormalize(v, axisMap[tag])
            axisMaps[tag] = {denorm(k): denorm(v) for k, v in seg.items()}

        for i, (inputLoc, outputLoc) in enumerate(mappings):
            inputLoc = {
                tag: _denormalize(val, axisMap[tag]) for tag, val in inputLoc.items()
            }
            outputLoc = {
                tag: _denormalize(val, axisMap[tag]) for tag, val in outputLoc.items()
            }
            mappings[i] = (inputLoc, outputLoc)

    return axisMaps, mappings


def main(args=None):
    """Add `avar` table from designspace file to variable font."""

    if args is None:
        import sys

        args = sys.argv[1:]

    from fontTools import configLogger
    from fontTools.ttLib import TTFont
    from fontTools.designspaceLib import DesignSpaceDocument
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools varLib.avar",
        description="Add `avar` table from designspace file to variable font.",
    )
    parser.add_argument("font", metavar="varfont.ttf", help="Variable-font file.")
    parser.add_argument(
        "designspace",
        metavar="family.designspace",
        help="Designspace file.",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=str,
        help="Output font file name.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )

    options = parser.parse_args(args)

    configLogger(level=("INFO" if options.verbose else "WARNING"))

    font = TTFont(options.font)
    if not "fvar" in font:
        log.error("Not a variable font.")
        return 1

    if options.designspace is None:
        from pprint import pprint

        segments, mappings = mappings_from_avar(font)
        pprint(segments)
        pprint(mappings)
        print(len(mappings), "mappings")
        return

    axisTags = [a.axisTag for a in font["fvar"].axes]

    ds = load_designspace(options.designspace, require_sources=False)

    if "avar" in font:
        log.warning("avar table already present, overwriting.")
        del font["avar"]

    _add_avar(font, ds.axes, ds.axisMappings, axisTags)

    if options.output_file is None:
        outfile = makeOutputFileName(options.font, overWrite=True, suffix=".avar")
    else:
        outfile = options.output_file
    if outfile:
        log.info("Saving %s", outfile)
        font.save(outfile)


if __name__ == "__main__":
    import sys

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\litellm\llms\anthropic\experimental_pass_through\adapters\handler.py ===
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
    cast,
)

import litellm
from litellm.llms.anthropic.experimental_pass_through.adapters.transformation import (
    AnthropicAdapter,
)
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
)
from litellm.types.utils import ModelResponse

if TYPE_CHECKING:
    pass

########################################################
# init adapter
ANTHROPIC_ADAPTER = AnthropicAdapter()
########################################################


class LiteLLMMessagesToCompletionTransformationHandler:
    @staticmethod
    def _prepare_completion_kwargs(
        *,
        max_tokens: int,
        messages: List[Dict],
        model: str,
        metadata: Optional[Dict] = None,
        stop_sequences: Optional[List[str]] = None,
        stream: Optional[bool] = False,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        thinking: Optional[Dict] = None,
        tool_choice: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        extra_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Prepare kwargs for litellm.completion/acompletion"""
        from litellm.litellm_core_utils.litellm_logging import (
            Logging as LiteLLMLoggingObject,
        )

        request_data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        if metadata:
            request_data["metadata"] = metadata
        if stop_sequences:
            request_data["stop_sequences"] = stop_sequences
        if system:
            request_data["system"] = system
        if temperature is not None:
            request_data["temperature"] = temperature
        if thinking:
            request_data["thinking"] = thinking
        if tool_choice:
            request_data["tool_choice"] = tool_choice
        if tools:
            request_data["tools"] = tools
        if top_k is not None:
            request_data["top_k"] = top_k
        if top_p is not None:
            request_data["top_p"] = top_p

        openai_request = ANTHROPIC_ADAPTER.translate_completion_input_params(
            request_data
        )

        if openai_request is None:
            raise ValueError("Failed to translate request to OpenAI format")

        completion_kwargs: Dict[str, Any] = dict(openai_request)

        if stream:
            completion_kwargs["stream"] = stream

        excluded_keys = {"anthropic_messages"}
        extra_kwargs = extra_kwargs or {}
        for key, value in extra_kwargs.items():
            if (
                key == "litellm_logging_obj"
                and value is not None
                and isinstance(value, LiteLLMLoggingObject)
            ):
                from litellm.types.utils import CallTypes

                setattr(value, "call_type", CallTypes.completion.value)
            if (
                key not in excluded_keys
                and key not in completion_kwargs
                and value is not None
            ):
                completion_kwargs[key] = value

        return completion_kwargs

    @staticmethod
    async def async_anthropic_messages_handler(
        max_tokens: int,
        messages: List[Dict],
        model: str,
        metadata: Optional[Dict] = None,
        stop_sequences: Optional[List[str]] = None,
        stream: Optional[bool] = False,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        thinking: Optional[Dict] = None,
        tool_choice: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        **kwargs,
    ) -> Union[AnthropicMessagesResponse, AsyncIterator]:
        """Handle non-Anthropic models asynchronously using the adapter"""

        completion_kwargs = (
            LiteLLMMessagesToCompletionTransformationHandler._prepare_completion_kwargs(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                metadata=metadata,
                stop_sequences=stop_sequences,
                stream=stream,
                system=system,
                temperature=temperature,
                thinking=thinking,
                tool_choice=tool_choice,
                tools=tools,
                top_k=top_k,
                top_p=top_p,
                extra_kwargs=kwargs,
            )
        )

        try:
            completion_response = await litellm.acompletion(**completion_kwargs)

            if stream:
                transformed_stream = (
                    ANTHROPIC_ADAPTER.translate_completion_output_params_streaming(
                        completion_response
                    )
                )
                if transformed_stream is not None:
                    return transformed_stream
                raise ValueError("Failed to transform streaming response")
            else:
                anthropic_response = (
                    ANTHROPIC_ADAPTER.translate_completion_output_params(
                        cast(ModelResponse, completion_response)
                    )
                )
                if anthropic_response is not None:
                    return anthropic_response
                raise ValueError("Failed to transform response to Anthropic format")
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"Error calling litellm.acompletion for non-Anthropic model: {str(e)}"
            )

    @staticmethod
    def anthropic_messages_handler(
        max_tokens: int,
        messages: List[Dict],
        model: str,
        metadata: Optional[Dict] = None,
        stop_sequences: Optional[List[str]] = None,
        stream: Optional[bool] = False,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        thinking: Optional[Dict] = None,
        tool_choice: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        _is_async: bool = False,
        **kwargs,
    ) -> Union[
        AnthropicMessagesResponse,
        AsyncIterator[Any],
        Coroutine[Any, Any, Union[AnthropicMessagesResponse, AsyncIterator[Any]]],
    ]:
        """Handle non-Anthropic models using the adapter."""
        if _is_async is True:
            return LiteLLMMessagesToCompletionTransformationHandler.async_anthropic_messages_handler(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                metadata=metadata,
                stop_sequences=stop_sequences,
                stream=stream,
                system=system,
                temperature=temperature,
                thinking=thinking,
                tool_choice=tool_choice,
                tools=tools,
                top_k=top_k,
                top_p=top_p,
                **kwargs,
            )

        completion_kwargs = (
            LiteLLMMessagesToCompletionTransformationHandler._prepare_completion_kwargs(
                max_tokens=max_tokens,
                messages=messages,
                model=model,
                metadata=metadata,
                stop_sequences=stop_sequences,
                stream=stream,
                system=system,
                temperature=temperature,
                thinking=thinking,
                tool_choice=tool_choice,
                tools=tools,
                top_k=top_k,
                top_p=top_p,
                extra_kwargs=kwargs,
            )
        )

        try:
            completion_response = litellm.completion(**completion_kwargs)

            if stream:
                transformed_stream = (
                    ANTHROPIC_ADAPTER.translate_completion_output_params_streaming(
                        completion_response
                    )
                )
                if transformed_stream is not None:
                    return transformed_stream
                raise ValueError("Failed to transform streaming response")
            else:
                anthropic_response = (
                    ANTHROPIC_ADAPTER.translate_completion_output_params(
                        cast(ModelResponse, completion_response)
                    )
                )
                if anthropic_response is not None:
                    return anthropic_response
                raise ValueError("Failed to transform response to Anthropic format")
        except Exception as e:  # noqa: BLE001
            raise ValueError(
                f"Error calling litellm.completion for non-Anthropic model: {str(e)}"
            )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\auth\model_checks.py ===
# What is this?
## Common checks for /v1/models and `/model/info`
from typing import Dict, List, Optional, Set

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import SpecialModelNames, UserAPIKeyAuth
from litellm.router import Router
from litellm.types.router import LiteLLM_Params
from litellm.utils import get_valid_models


def _check_wildcard_routing(model: str) -> bool:
    """
    Returns True if a model is a provider wildcard.

    eg:
    - anthropic/*
    - openai/*
    - *
    """
    if "*" in model:
        return True
    return False


def get_provider_models(
    provider: str, litellm_params: Optional[LiteLLM_Params] = None
) -> Optional[List[str]]:
    """
    Returns the list of known models by provider
    """
    if provider == "*":
        return get_valid_models(litellm_params=litellm_params)

    if provider in litellm.models_by_provider:
        provider_models = get_valid_models(
            custom_llm_provider=provider, litellm_params=litellm_params
        )
        return provider_models
    return None


def _get_models_from_access_groups(
    model_access_groups: Dict[str, List[str]],
    all_models: List[str],
    include_model_access_groups: Optional[bool] = False,
) -> List[str]:
    idx_to_remove = []
    new_models = []
    for idx, model in enumerate(all_models):
        if model in model_access_groups:
            if (
                not include_model_access_groups
            ):  # remove access group, unless requested - e.g. when creating a key and trying to see list of models
                idx_to_remove.append(idx)
            new_models.extend(model_access_groups[model])

    for idx in sorted(idx_to_remove, reverse=True):
        all_models.pop(idx)

    all_models.extend(new_models)
    return all_models


def get_key_models(
    user_api_key_dict: UserAPIKeyAuth,
    proxy_model_list: List[str],
    model_access_groups: Dict[str, List[str]],
    include_model_access_groups: Optional[bool] = False,
    only_model_access_groups: Optional[bool] = False,
) -> List[str]:
    """
    Returns:
    - List of model name strings
    - Empty list if no models set
    - If model_access_groups is provided, only return models that are in the access groups
    - If include_model_access_groups is True, it includes the 'keys' of the model_access_groups in the response - {"beta-models": ["gpt-4", "claude-v1"]} -> returns 'beta-models'
    """
    all_models: List[str] = []
    if len(user_api_key_dict.models) > 0:
        all_models = user_api_key_dict.models
        if SpecialModelNames.all_team_models.value in all_models:
            all_models = user_api_key_dict.team_models
        if SpecialModelNames.all_proxy_models.value in all_models:
            all_models = proxy_model_list

    all_models = _get_models_from_access_groups(
        model_access_groups=model_access_groups, all_models=all_models
    )

    verbose_proxy_logger.debug("ALL KEY MODELS - {}".format(len(all_models)))
    return all_models


def get_team_models(
    team_models: List[str],
    proxy_model_list: List[str],
    model_access_groups: Dict[str, List[str]],
    include_model_access_groups: Optional[bool] = False,
) -> List[str]:
    """
    Returns:
    - List of model name strings
    - Empty list if no models set
    - If model_access_groups is provided, only return models that are in the access groups
    """
    all_models_set: Set[str] = set()
    if len(team_models) > 0:
        all_models_set.update(team_models)
        if SpecialModelNames.all_team_models.value in all_models_set:
            all_models_set.update(team_models)
        if SpecialModelNames.all_proxy_models.value in all_models_set:
            all_models_set.update(proxy_model_list)

    all_models = list(all_models_set)

    all_models = _get_models_from_access_groups(
        model_access_groups=model_access_groups,
        all_models=list(all_models_set),
        include_model_access_groups=include_model_access_groups,
    )

    verbose_proxy_logger.debug("ALL TEAM MODELS - {}".format(len(all_models)))
    return all_models


def get_complete_model_list(
    key_models: List[str],
    team_models: List[str],
    proxy_model_list: List[str],
    user_model: Optional[str],
    infer_model_from_keys: Optional[bool],
    return_wildcard_routes: Optional[bool] = False,
    llm_router: Optional[Router] = None,
    model_access_groups: Dict[str, List[str]] = {},
    include_model_access_groups: Optional[bool] = False,
    only_model_access_groups: Optional[bool] = False,
) -> List[str]:
    """Logic for returning complete model list for a given key + team pair"""

    """
    - If key list is empty -> defer to team list
    - If team list is empty -> defer to proxy model list

    If list contains wildcard -> return known provider models
    """

    unique_models: Set[str] = set()
    if key_models:
        unique_models.update(key_models)
    elif team_models:
        unique_models.update(team_models)
    else:
        unique_models.update(proxy_model_list)
        if include_model_access_groups:
            unique_models.update(model_access_groups.keys())

        if user_model:
            unique_models.add(user_model)

        if infer_model_from_keys:
            valid_models = get_valid_models()
            unique_models.update(valid_models)

    if only_model_access_groups:
        model_access_groups_to_return: List[str] = []
        for model in unique_models:
            if model in model_access_groups:
                model_access_groups_to_return.append(model)
        return model_access_groups_to_return

    all_wildcard_models = _get_wildcard_models(
        unique_models=unique_models,
        return_wildcard_routes=return_wildcard_routes,
        llm_router=llm_router,
    )

    complete_model_list = list(unique_models) + all_wildcard_models

    return complete_model_list


def get_known_models_from_wildcard(
    wildcard_model: str, litellm_params: Optional[LiteLLM_Params] = None
) -> List[str]:
    try:
        wildcard_provider_prefix, wildcard_suffix = wildcard_model.split("/", 1)
    except ValueError:  # safely fail
        return []

    if litellm_params is None:  # need litellm params to extract litellm model name
        return []

    try:
        provider = litellm_params.model.split("/", 1)[0]
    except ValueError:
        provider = wildcard_provider_prefix

    # get all known provider models
    wildcard_models = get_provider_models(
        provider=provider, litellm_params=litellm_params
    )
    if wildcard_models is None:
        return []
    if wildcard_suffix != "*":
        model_prefix = wildcard_suffix.replace("*", "")
        filtered_wildcard_models = [
            wc_model
            for wc_model in wildcard_models
            if wc_model.startswith(model_prefix)
        ]
        wildcard_models = filtered_wildcard_models

    suffix_appended_wildcard_models = []
    for model in wildcard_models:
        if not model.startswith(wildcard_provider_prefix):
            model = f"{wildcard_provider_prefix}/{model}"
        suffix_appended_wildcard_models.append(model)
    return suffix_appended_wildcard_models or []


def _get_wildcard_models(
    unique_models: Set[str],
    return_wildcard_routes: Optional[bool] = False,
    llm_router: Optional[Router] = None,
) -> List[str]:
    models_to_remove = set()
    all_wildcard_models = []
    for model in unique_models:
        if _check_wildcard_routing(model=model):
            if (
                return_wildcard_routes
            ):  # will add the wildcard route to the list eg: anthropic/*.
                all_wildcard_models.append(model)

            ## get litellm params from model
            if llm_router is not None:
                model_list = llm_router.get_model_list(model_name=model)
                if model_list is not None:
                    for router_model in model_list:
                        wildcard_models = get_known_models_from_wildcard(
                            wildcard_model=model,
                            litellm_params=LiteLLM_Params(
                                **router_model["litellm_params"]  # type: ignore
                            ),
                        )
                        all_wildcard_models.extend(wildcard_models)
            else:
                # get all known provider models
                wildcard_models = get_known_models_from_wildcard(wildcard_model=model)

                if wildcard_models is not None:
                    models_to_remove.add(model)
                    all_wildcard_models.extend(wildcard_models)

    for model in models_to_remove:
        unique_models.remove(model)

    return all_wildcard_models

# === NexusCore/openenv\Lib\site-packages\nltk\classify\naivebayes.py ===
# Natural Language Toolkit: Naive Bayes Classifiers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A classifier based on the Naive Bayes algorithm.  In order to find the
probability for a label, this algorithm first uses the Bayes rule to
express P(label|features) in terms of P(label) and P(features|label):

|                       P(label) * P(features|label)
|  P(label|features) = ------------------------------
|                              P(features)

The algorithm then makes the 'naive' assumption that all features are
independent, given the label:

|                       P(label) * P(f1|label) * ... * P(fn|label)
|  P(label|features) = --------------------------------------------
|                                         P(features)

Rather than computing P(features) explicitly, the algorithm just
calculates the numerator for each label, and normalizes them so they
sum to one:

|                       P(label) * P(f1|label) * ... * P(fn|label)
|  P(label|features) = --------------------------------------------
|                        SUM[l]( P(l) * P(f1|l) * ... * P(fn|l) )
"""

from collections import defaultdict

from nltk.classify.api import ClassifierI
from nltk.probability import DictionaryProbDist, ELEProbDist, FreqDist, sum_logs

##//////////////////////////////////////////////////////
##  Naive Bayes Classifier
##//////////////////////////////////////////////////////


class NaiveBayesClassifier(ClassifierI):
    """
    A Naive Bayes classifier.  Naive Bayes classifiers are
    paramaterized by two probability distributions:

      - P(label) gives the probability that an input will receive each
        label, given no information about the input's features.

      - P(fname=fval|label) gives the probability that a given feature
        (fname) will receive a given value (fval), given that the
        label (label).

    If the classifier encounters an input with a feature that has
    never been seen with any label, then rather than assigning a
    probability of 0 to all labels, it will ignore that feature.

    The feature value 'None' is reserved for unseen feature values;
    you generally should not use 'None' as a feature value for one of
    your own features.
    """

    def __init__(self, label_probdist, feature_probdist):
        """
        :param label_probdist: P(label), the probability distribution
            over labels.  It is expressed as a ``ProbDistI`` whose
            samples are labels.  I.e., P(label) =
            ``label_probdist.prob(label)``.

        :param feature_probdist: P(fname=fval|label), the probability
            distribution for feature values, given labels.  It is
            expressed as a dictionary whose keys are ``(label, fname)``
            pairs and whose values are ``ProbDistI`` objects over feature
            values.  I.e., P(fname=fval|label) =
            ``feature_probdist[label,fname].prob(fval)``.  If a given
            ``(label,fname)`` is not a key in ``feature_probdist``, then
            it is assumed that the corresponding P(fname=fval|label)
            is 0 for all values of ``fval``.
        """
        self._label_probdist = label_probdist
        self._feature_probdist = feature_probdist
        self._labels = list(label_probdist.samples())

    def labels(self):
        return self._labels

    def classify(self, featureset):
        return self.prob_classify(featureset).max()

    def prob_classify(self, featureset):
        # Discard any feature names that we've never seen before.
        # Otherwise, we'll just assign a probability of 0 to
        # everything.
        featureset = featureset.copy()
        for fname in list(featureset.keys()):
            for label in self._labels:
                if (label, fname) in self._feature_probdist:
                    break
            else:
                # print('Ignoring unseen feature %s' % fname)
                del featureset[fname]

        # Find the log probability of each label, given the features.
        # Start with the log probability of the label itself.
        logprob = {}
        for label in self._labels:
            logprob[label] = self._label_probdist.logprob(label)

        # Then add in the log probability of features given labels.
        for label in self._labels:
            for fname, fval in featureset.items():
                if (label, fname) in self._feature_probdist:
                    feature_probs = self._feature_probdist[label, fname]
                    logprob[label] += feature_probs.logprob(fval)
                else:
                    # nb: This case will never come up if the
                    # classifier was created by
                    # NaiveBayesClassifier.train().
                    logprob[label] += sum_logs([])  # = -INF.

        return DictionaryProbDist(logprob, normalize=True, log=True)

    def show_most_informative_features(self, n=10):
        # Determine the most relevant features, and display them.
        cpdist = self._feature_probdist
        print("Most Informative Features")

        for fname, fval in self.most_informative_features(n):

            def labelprob(l):
                return cpdist[l, fname].prob(fval)

            labels = sorted(
                (l for l in self._labels if fval in cpdist[l, fname].samples()),
                key=lambda element: (-labelprob(element), element),
                reverse=True,
            )
            if len(labels) == 1:
                continue
            l0 = labels[0]
            l1 = labels[-1]
            if cpdist[l0, fname].prob(fval) == 0:
                ratio = "INF"
            else:
                ratio = "%8.1f" % (
                    cpdist[l1, fname].prob(fval) / cpdist[l0, fname].prob(fval)
                )
            print(
                "%24s = %-14r %6s : %-6s = %s : 1.0"
                % (fname, fval, ("%s" % l1)[:6], ("%s" % l0)[:6], ratio)
            )

    def most_informative_features(self, n=100):
        """
        Return a list of the 'most informative' features used by this
        classifier.  For the purpose of this function, the
        informativeness of a feature ``(fname,fval)`` is equal to the
        highest value of P(fname=fval|label), for any label, divided by
        the lowest value of P(fname=fval|label), for any label:

        |  max[ P(fname=fval|label1) / P(fname=fval|label2) ]
        """
        if hasattr(self, "_most_informative_features"):
            return self._most_informative_features[:n]
        else:
            # The set of (fname, fval) pairs used by this classifier.
            features = set()
            # The max & min probability associated w/ each (fname, fval)
            # pair.  Maps (fname,fval) -> float.
            maxprob = defaultdict(float)
            minprob = defaultdict(lambda: 1.0)

            for (label, fname), probdist in self._feature_probdist.items():
                for fval in probdist.samples():
                    feature = (fname, fval)
                    features.add(feature)
                    p = probdist.prob(fval)
                    maxprob[feature] = max(p, maxprob[feature])
                    minprob[feature] = min(p, minprob[feature])
                    if minprob[feature] == 0:
                        features.discard(feature)

            # Convert features to a list, & sort it by how informative
            # features are.
            self._most_informative_features = sorted(
                features,
                key=lambda feature_: (
                    minprob[feature_] / maxprob[feature_],
                    feature_[0],
                    feature_[1] in [None, False, True],
                    str(feature_[1]).lower(),
                ),
            )
        return self._most_informative_features[:n]

    @classmethod
    def train(cls, labeled_featuresets, estimator=ELEProbDist):
        """
        :param labeled_featuresets: A list of classified featuresets,
            i.e., a list of tuples ``(featureset, label)``.
        """
        label_freqdist = FreqDist()
        feature_freqdist = defaultdict(FreqDist)
        feature_values = defaultdict(set)
        fnames = set()

        # Count up how many times each feature value occurred, given
        # the label and featurename.
        for featureset, label in labeled_featuresets:
            label_freqdist[label] += 1
            for fname, fval in featureset.items():
                # Increment freq(fval|label, fname)
                feature_freqdist[label, fname][fval] += 1
                # Record that fname can take the value fval.
                feature_values[fname].add(fval)
                # Keep a list of all feature names.
                fnames.add(fname)

        # If a feature didn't have a value given for an instance, then
        # we assume that it gets the implicit value 'None.'  This loop
        # counts up the number of 'missing' feature values for each
        # (label,fname) pair, and increments the count of the fval
        # 'None' by that amount.
        for label in label_freqdist:
            num_samples = label_freqdist[label]
            for fname in fnames:
                count = feature_freqdist[label, fname].N()
                # Only add a None key when necessary, i.e. if there are
                # any samples with feature 'fname' missing.
                if num_samples - count > 0:
                    feature_freqdist[label, fname][None] += num_samples - count
                    feature_values[fname].add(None)

        # Create the P(label) distribution
        label_probdist = estimator(label_freqdist)

        # Create the P(fval|label, fname) distribution
        feature_probdist = {}
        for (label, fname), freqdist in feature_freqdist.items():
            probdist = estimator(freqdist, bins=len(feature_values[fname]))
            feature_probdist[label, fname] = probdist

        return cls(label_probdist, feature_probdist)


##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////


def demo():
    from nltk.classify.util import names_demo

    classifier = names_demo(NaiveBayesClassifier.train)
    classifier.show_most_informative_features()


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\filters\base.py ===
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, Union

__all__ = ["Filter", "Never", "Always", "Condition", "FilterOrBool"]


class Filter(metaclass=ABCMeta):
    """
    Base class for any filter to activate/deactivate a feature, depending on a
    condition.

    The return value of ``__call__`` will tell if the feature should be active.
    """

    def __init__(self) -> None:
        self._and_cache: dict[Filter, Filter] = {}
        self._or_cache: dict[Filter, Filter] = {}
        self._invert_result: Filter | None = None

    @abstractmethod
    def __call__(self) -> bool:
        """
        The actual call to evaluate the filter.
        """
        return True

    def __and__(self, other: Filter) -> Filter:
        """
        Chaining of filters using the & operator.
        """
        assert isinstance(other, Filter), f"Expecting filter, got {other!r}"

        if isinstance(other, Always):
            return self
        if isinstance(other, Never):
            return other

        if other in self._and_cache:
            return self._and_cache[other]

        result = _AndList.create([self, other])
        self._and_cache[other] = result
        return result

    def __or__(self, other: Filter) -> Filter:
        """
        Chaining of filters using the | operator.
        """
        assert isinstance(other, Filter), f"Expecting filter, got {other!r}"

        if isinstance(other, Always):
            return other
        if isinstance(other, Never):
            return self

        if other in self._or_cache:
            return self._or_cache[other]

        result = _OrList.create([self, other])
        self._or_cache[other] = result
        return result

    def __invert__(self) -> Filter:
        """
        Inverting of filters using the ~ operator.
        """
        if self._invert_result is None:
            self._invert_result = _Invert(self)

        return self._invert_result

    def __bool__(self) -> None:
        """
        By purpose, we don't allow bool(...) operations directly on a filter,
        because the meaning is ambiguous.

        Executing a filter has to be done always by calling it. Providing
        defaults for `None` values should be done through an `is None` check
        instead of for instance ``filter1 or Always()``.
        """
        raise ValueError(
            "The truth value of a Filter is ambiguous. Instead, call it as a function."
        )


def _remove_duplicates(filters: list[Filter]) -> list[Filter]:
    result = []
    for f in filters:
        if f not in result:
            result.append(f)
    return result


class _AndList(Filter):
    """
    Result of &-operation between several filters.
    """

    def __init__(self, filters: list[Filter]) -> None:
        super().__init__()
        self.filters = filters

    @classmethod
    def create(cls, filters: Iterable[Filter]) -> Filter:
        """
        Create a new filter by applying an `&` operator between them.

        If there's only one unique filter in the given iterable, it will return
        that one filter instead of an `_AndList`.
        """
        filters_2: list[Filter] = []

        for f in filters:
            if isinstance(f, _AndList):  # Turn nested _AndLists into one.
                filters_2.extend(f.filters)
            else:
                filters_2.append(f)

        # Remove duplicates. This could speed up execution, and doesn't make a
        # difference for the evaluation.
        filters = _remove_duplicates(filters_2)

        # If only one filter is left, return that without wrapping into an
        # `_AndList`.
        if len(filters) == 1:
            return filters[0]

        return cls(filters)

    def __call__(self) -> bool:
        return all(f() for f in self.filters)

    def __repr__(self) -> str:
        return "&".join(repr(f) for f in self.filters)


class _OrList(Filter):
    """
    Result of |-operation between several filters.
    """

    def __init__(self, filters: list[Filter]) -> None:
        super().__init__()
        self.filters = filters

    @classmethod
    def create(cls, filters: Iterable[Filter]) -> Filter:
        """
        Create a new filter by applying an `|` operator between them.

        If there's only one unique filter in the given iterable, it will return
        that one filter instead of an `_OrList`.
        """
        filters_2: list[Filter] = []

        for f in filters:
            if isinstance(f, _OrList):  # Turn nested _AndLists into one.
                filters_2.extend(f.filters)
            else:
                filters_2.append(f)

        # Remove duplicates. This could speed up execution, and doesn't make a
        # difference for the evaluation.
        filters = _remove_duplicates(filters_2)

        # If only one filter is left, return that without wrapping into an
        # `_AndList`.
        if len(filters) == 1:
            return filters[0]

        return cls(filters)

    def __call__(self) -> bool:
        return any(f() for f in self.filters)

    def __repr__(self) -> str:
        return "|".join(repr(f) for f in self.filters)


class _Invert(Filter):
    """
    Negation of another filter.
    """

    def __init__(self, filter: Filter) -> None:
        super().__init__()
        self.filter = filter

    def __call__(self) -> bool:
        return not self.filter()

    def __repr__(self) -> str:
        return f"~{self.filter!r}"


class Always(Filter):
    """
    Always enable feature.
    """

    def __call__(self) -> bool:
        return True

    def __or__(self, other: Filter) -> Filter:
        return self

    def __and__(self, other: Filter) -> Filter:
        return other

    def __invert__(self) -> Never:
        return Never()


class Never(Filter):
    """
    Never enable feature.
    """

    def __call__(self) -> bool:
        return False

    def __and__(self, other: Filter) -> Filter:
        return self

    def __or__(self, other: Filter) -> Filter:
        return other

    def __invert__(self) -> Always:
        return Always()


class Condition(Filter):
    """
    Turn any callable into a Filter. The callable is supposed to not take any
    arguments.

    This can be used as a decorator::

        @Condition
        def feature_is_active():  # `feature_is_active` becomes a Filter.
            return True

    :param func: Callable which takes no inputs and returns a boolean.
    """

    def __init__(self, func: Callable[[], bool]) -> None:
        super().__init__()
        self.func = func

    def __call__(self) -> bool:
        return self.func()

    def __repr__(self) -> str:
        return f"Condition({self.func!r})"


# Often used as type annotation.
FilterOrBool = Union[Filter, bool]

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\pwa.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PWA (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


@dataclass
class FileHandlerAccept:
    '''
    The following types are the replica of
    https://crsrc.org/c/chrome/browser/web_applications/proto/web_app_os_integration_state.proto;drc=9910d3be894c8f142c977ba1023f30a656bc13fc;l=67
    '''
    #: New name of the mimetype according to
    #: https://www.iana.org/assignments/media-types/media-types.xhtml
    media_type: str

    file_extensions: typing.List[str]

    def to_json(self):
        json = dict()
        json['mediaType'] = self.media_type
        json['fileExtensions'] = [i for i in self.file_extensions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            media_type=str(json['mediaType']),
            file_extensions=[str(i) for i in json['fileExtensions']],
        )


@dataclass
class FileHandler:
    action: str

    accepts: typing.List[FileHandlerAccept]

    display_name: str

    def to_json(self):
        json = dict()
        json['action'] = self.action
        json['accepts'] = [i.to_json() for i in self.accepts]
        json['displayName'] = self.display_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            action=str(json['action']),
            accepts=[FileHandlerAccept.from_json(i) for i in json['accepts']],
            display_name=str(json['displayName']),
        )


class DisplayMode(enum.Enum):
    '''
    If user prefers opening the app in browser or an app window.
    '''
    STANDALONE = "standalone"
    BROWSER = "browser"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def get_os_app_state(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[int, typing.List[FileHandler]]]:
    '''
    Returns the following OS state for the given manifest id.

    :param manifest_id: The id from the webapp's manifest file, commonly it's the url of the site installing the webapp. See https://web.dev/learn/pwa/web-app-manifest.
    :returns: A tuple with the following items:

        0. **badgeCount** - 
        1. **fileHandlers** - 
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.getOsAppState',
        'params': params,
    }
    json = yield cmd_dict
    return (
        int(json['badgeCount']),
        [FileHandler.from_json(i) for i in json['fileHandlers']]
    )


def install(
        manifest_id: str,
        install_url_or_bundle_url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Installs the given manifest identity, optionally using the given install_url
    or IWA bundle location.

    TODO(crbug.com/337872319) Support IWA to meet the following specific
    requirement.
    IWA-specific install description: If the manifest_id is isolated-app://,
    install_url_or_bundle_url is required, and can be either an http(s) URL or
    file:// URL pointing to a signed web bundle (.swbn). The .swbn file's
    signing key must correspond to manifest_id. If Chrome is not in IWA dev
    mode, the installation will fail, regardless of the state of the allowlist.

    :param manifest_id:
    :param install_url_or_bundle_url: *(Optional)* The location of the app or bundle overriding the one derived from the manifestId.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if install_url_or_bundle_url is not None:
        params['installUrlOrBundleUrl'] = install_url_or_bundle_url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.install',
        'params': params,
    }
    json = yield cmd_dict


def uninstall(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls the given manifest_id and closes any opened app windows.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def launch(
        manifest_id: str,
        url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,target.TargetID]:
    '''
    Launches the installed web app, or an url in the same web app instead of the
    default start url if it is provided. Returns a page Target.TargetID which
    can be used to attach to via Target.attachToTarget or similar APIs.

    :param manifest_id:
    :param url: *(Optional)*
    :returns: ID of the tab target created as a result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if url is not None:
        params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launch',
        'params': params,
    }
    json = yield cmd_dict
    return target.TargetID.from_json(json['targetId'])


def launch_files_in_app(
        manifest_id: str,
        files: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[target.TargetID]]:
    '''
    Opens one or more local files from an installed web app identified by its
    manifestId. The web app needs to have file handlers registered to process
    the files. The API returns one or more page Target.TargetIDs which can be
    used to attach to via Target.attachToTarget or similar APIs.
    If some files in the parameters cannot be handled by the web app, they will
    be ignored. If none of the files can be handled, this API returns an error.
    If no files are provided as the parameter, this API also returns an error.

    According to the definition of the file handlers in the manifest file, one
    Target.TargetID may represent a page handling one or more files. The order
    of the returned Target.TargetIDs is not guaranteed.

    TODO(crbug.com/339454034): Check the existences of the input files.

    :param manifest_id:
    :param files:
    :returns: IDs of the tab targets created as the result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    params['files'] = [i for i in files]
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launchFilesInApp',
        'params': params,
    }
    json = yield cmd_dict
    return [target.TargetID.from_json(i) for i in json['targetIds']]


def open_current_page_in_app(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Opens the current page in its web app identified by the manifest id, needs
    to be called on a page target. This function returns immediately without
    waiting for the app to finish loading.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.openCurrentPageInApp',
        'params': params,
    }
    json = yield cmd_dict


def change_app_user_settings(
        manifest_id: str,
        link_capturing: typing.Optional[bool] = None,
        display_mode: typing.Optional[DisplayMode] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes user settings of the web app identified by its manifestId. If the
    app was not installed, this command returns an error. Unset parameters will
    be ignored; unrecognized values will cause an error.

    Unlike the ones defined in the manifest files of the web apps, these
    settings are provided by the browser and controlled by the users, they
    impact the way the browser handling the web apps.

    See the comment of each parameter.

    :param manifest_id:
    :param link_capturing: *(Optional)* If user allows the links clicked on by the user in the app's scope, or extended scope if the manifest has scope extensions and the flags ```DesktopPWAsLinkCapturingWithScopeExtensions```` and ````WebAppEnableScopeExtensions``` are enabled.  Note, the API does not support resetting the linkCapturing to the initial value, uninstalling and installing the web app again will reset it.  TODO(crbug.com/339453269): Setting this value on ChromeOS is not supported yet.
    :param display_mode: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if link_capturing is not None:
        params['linkCapturing'] = link_capturing
    if display_mode is not None:
        params['displayMode'] = display_mode.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.changeAppUserSettings',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\pwa.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PWA (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


@dataclass
class FileHandlerAccept:
    '''
    The following types are the replica of
    https://crsrc.org/c/chrome/browser/web_applications/proto/web_app_os_integration_state.proto;drc=9910d3be894c8f142c977ba1023f30a656bc13fc;l=67
    '''
    #: New name of the mimetype according to
    #: https://www.iana.org/assignments/media-types/media-types.xhtml
    media_type: str

    file_extensions: typing.List[str]

    def to_json(self):
        json = dict()
        json['mediaType'] = self.media_type
        json['fileExtensions'] = [i for i in self.file_extensions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            media_type=str(json['mediaType']),
            file_extensions=[str(i) for i in json['fileExtensions']],
        )


@dataclass
class FileHandler:
    action: str

    accepts: typing.List[FileHandlerAccept]

    display_name: str

    def to_json(self):
        json = dict()
        json['action'] = self.action
        json['accepts'] = [i.to_json() for i in self.accepts]
        json['displayName'] = self.display_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            action=str(json['action']),
            accepts=[FileHandlerAccept.from_json(i) for i in json['accepts']],
            display_name=str(json['displayName']),
        )


class DisplayMode(enum.Enum):
    '''
    If user prefers opening the app in browser or an app window.
    '''
    STANDALONE = "standalone"
    BROWSER = "browser"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def get_os_app_state(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[int, typing.List[FileHandler]]]:
    '''
    Returns the following OS state for the given manifest id.

    :param manifest_id: The id from the webapp's manifest file, commonly it's the url of the site installing the webapp. See https://web.dev/learn/pwa/web-app-manifest.
    :returns: A tuple with the following items:

        0. **badgeCount** - 
        1. **fileHandlers** - 
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.getOsAppState',
        'params': params,
    }
    json = yield cmd_dict
    return (
        int(json['badgeCount']),
        [FileHandler.from_json(i) for i in json['fileHandlers']]
    )


def install(
        manifest_id: str,
        install_url_or_bundle_url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Installs the given manifest identity, optionally using the given install_url
    or IWA bundle location.

    TODO(crbug.com/337872319) Support IWA to meet the following specific
    requirement.
    IWA-specific install description: If the manifest_id is isolated-app://,
    install_url_or_bundle_url is required, and can be either an http(s) URL or
    file:// URL pointing to a signed web bundle (.swbn). The .swbn file's
    signing key must correspond to manifest_id. If Chrome is not in IWA dev
    mode, the installation will fail, regardless of the state of the allowlist.

    :param manifest_id:
    :param install_url_or_bundle_url: *(Optional)* The location of the app or bundle overriding the one derived from the manifestId.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if install_url_or_bundle_url is not None:
        params['installUrlOrBundleUrl'] = install_url_or_bundle_url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.install',
        'params': params,
    }
    json = yield cmd_dict


def uninstall(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls the given manifest_id and closes any opened app windows.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def launch(
        manifest_id: str,
        url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,target.TargetID]:
    '''
    Launches the installed web app, or an url in the same web app instead of the
    default start url if it is provided. Returns a page Target.TargetID which
    can be used to attach to via Target.attachToTarget or similar APIs.

    :param manifest_id:
    :param url: *(Optional)*
    :returns: ID of the tab target created as a result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if url is not None:
        params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launch',
        'params': params,
    }
    json = yield cmd_dict
    return target.TargetID.from_json(json['targetId'])


def launch_files_in_app(
        manifest_id: str,
        files: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[target.TargetID]]:
    '''
    Opens one or more local files from an installed web app identified by its
    manifestId. The web app needs to have file handlers registered to process
    the files. The API returns one or more page Target.TargetIDs which can be
    used to attach to via Target.attachToTarget or similar APIs.
    If some files in the parameters cannot be handled by the web app, they will
    be ignored. If none of the files can be handled, this API returns an error.
    If no files are provided as the parameter, this API also returns an error.

    According to the definition of the file handlers in the manifest file, one
    Target.TargetID may represent a page handling one or more files. The order
    of the returned Target.TargetIDs is not guaranteed.

    TODO(crbug.com/339454034): Check the existences of the input files.

    :param manifest_id:
    :param files:
    :returns: IDs of the tab targets created as the result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    params['files'] = [i for i in files]
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launchFilesInApp',
        'params': params,
    }
    json = yield cmd_dict
    return [target.TargetID.from_json(i) for i in json['targetIds']]


def open_current_page_in_app(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Opens the current page in its web app identified by the manifest id, needs
    to be called on a page target. This function returns immediately without
    waiting for the app to finish loading.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.openCurrentPageInApp',
        'params': params,
    }
    json = yield cmd_dict


def change_app_user_settings(
        manifest_id: str,
        link_capturing: typing.Optional[bool] = None,
        display_mode: typing.Optional[DisplayMode] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes user settings of the web app identified by its manifestId. If the
    app was not installed, this command returns an error. Unset parameters will
    be ignored; unrecognized values will cause an error.

    Unlike the ones defined in the manifest files of the web apps, these
    settings are provided by the browser and controlled by the users, they
    impact the way the browser handling the web apps.

    See the comment of each parameter.

    :param manifest_id:
    :param link_capturing: *(Optional)* If user allows the links clicked on by the user in the app's scope, or extended scope if the manifest has scope extensions and the flags ```DesktopPWAsLinkCapturingWithScopeExtensions```` and ````WebAppEnableScopeExtensions``` are enabled.  Note, the API does not support resetting the linkCapturing to the initial value, uninstalling and installing the web app again will reset it.  TODO(crbug.com/339453269): Setting this value on ChromeOS is not supported yet.
    :param display_mode: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if link_capturing is not None:
        params['linkCapturing'] = link_capturing
    if display_mode is not None:
        params['displayMode'] = display_mode.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.changeAppUserSettings',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\pwa.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: PWA (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import target


@dataclass
class FileHandlerAccept:
    '''
    The following types are the replica of
    https://crsrc.org/c/chrome/browser/web_applications/proto/web_app_os_integration_state.proto;drc=9910d3be894c8f142c977ba1023f30a656bc13fc;l=67
    '''
    #: New name of the mimetype according to
    #: https://www.iana.org/assignments/media-types/media-types.xhtml
    media_type: str

    file_extensions: typing.List[str]

    def to_json(self):
        json = dict()
        json['mediaType'] = self.media_type
        json['fileExtensions'] = [i for i in self.file_extensions]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            media_type=str(json['mediaType']),
            file_extensions=[str(i) for i in json['fileExtensions']],
        )


@dataclass
class FileHandler:
    action: str

    accepts: typing.List[FileHandlerAccept]

    display_name: str

    def to_json(self):
        json = dict()
        json['action'] = self.action
        json['accepts'] = [i.to_json() for i in self.accepts]
        json['displayName'] = self.display_name
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            action=str(json['action']),
            accepts=[FileHandlerAccept.from_json(i) for i in json['accepts']],
            display_name=str(json['displayName']),
        )


class DisplayMode(enum.Enum):
    '''
    If user prefers opening the app in browser or an app window.
    '''
    STANDALONE = "standalone"
    BROWSER = "browser"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def get_os_app_state(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[int, typing.List[FileHandler]]]:
    '''
    Returns the following OS state for the given manifest id.

    :param manifest_id: The id from the webapp's manifest file, commonly it's the url of the site installing the webapp. See https://web.dev/learn/pwa/web-app-manifest.
    :returns: A tuple with the following items:

        0. **badgeCount** - 
        1. **fileHandlers** - 
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.getOsAppState',
        'params': params,
    }
    json = yield cmd_dict
    return (
        int(json['badgeCount']),
        [FileHandler.from_json(i) for i in json['fileHandlers']]
    )


def install(
        manifest_id: str,
        install_url_or_bundle_url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Installs the given manifest identity, optionally using the given install_url
    or IWA bundle location.

    TODO(crbug.com/337872319) Support IWA to meet the following specific
    requirement.
    IWA-specific install description: If the manifest_id is isolated-app://,
    install_url_or_bundle_url is required, and can be either an http(s) URL or
    file:// URL pointing to a signed web bundle (.swbn). The .swbn file's
    signing key must correspond to manifest_id. If Chrome is not in IWA dev
    mode, the installation will fail, regardless of the state of the allowlist.

    :param manifest_id:
    :param install_url_or_bundle_url: *(Optional)* The location of the app or bundle overriding the one derived from the manifestId.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if install_url_or_bundle_url is not None:
        params['installUrlOrBundleUrl'] = install_url_or_bundle_url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.install',
        'params': params,
    }
    json = yield cmd_dict


def uninstall(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Uninstalls the given manifest_id and closes any opened app windows.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.uninstall',
        'params': params,
    }
    json = yield cmd_dict


def launch(
        manifest_id: str,
        url: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,target.TargetID]:
    '''
    Launches the installed web app, or an url in the same web app instead of the
    default start url if it is provided. Returns a page Target.TargetID which
    can be used to attach to via Target.attachToTarget or similar APIs.

    :param manifest_id:
    :param url: *(Optional)*
    :returns: ID of the tab target created as a result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if url is not None:
        params['url'] = url
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launch',
        'params': params,
    }
    json = yield cmd_dict
    return target.TargetID.from_json(json['targetId'])


def launch_files_in_app(
        manifest_id: str,
        files: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[target.TargetID]]:
    '''
    Opens one or more local files from an installed web app identified by its
    manifestId. The web app needs to have file handlers registered to process
    the files. The API returns one or more page Target.TargetIDs which can be
    used to attach to via Target.attachToTarget or similar APIs.
    If some files in the parameters cannot be handled by the web app, they will
    be ignored. If none of the files can be handled, this API returns an error.
    If no files are provided as the parameter, this API also returns an error.

    According to the definition of the file handlers in the manifest file, one
    Target.TargetID may represent a page handling one or more files. The order
    of the returned Target.TargetIDs is not guaranteed.

    TODO(crbug.com/339454034): Check the existences of the input files.

    :param manifest_id:
    :param files:
    :returns: IDs of the tab targets created as the result.
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    params['files'] = [i for i in files]
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.launchFilesInApp',
        'params': params,
    }
    json = yield cmd_dict
    return [target.TargetID.from_json(i) for i in json['targetIds']]


def open_current_page_in_app(
        manifest_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Opens the current page in its web app identified by the manifest id, needs
    to be called on a page target. This function returns immediately without
    waiting for the app to finish loading.

    :param manifest_id:
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.openCurrentPageInApp',
        'params': params,
    }
    json = yield cmd_dict


def change_app_user_settings(
        manifest_id: str,
        link_capturing: typing.Optional[bool] = None,
        display_mode: typing.Optional[DisplayMode] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes user settings of the web app identified by its manifestId. If the
    app was not installed, this command returns an error. Unset parameters will
    be ignored; unrecognized values will cause an error.

    Unlike the ones defined in the manifest files of the web apps, these
    settings are provided by the browser and controlled by the users, they
    impact the way the browser handling the web apps.

    See the comment of each parameter.

    :param manifest_id:
    :param link_capturing: *(Optional)* If user allows the links clicked on by the user in the app's scope, or extended scope if the manifest has scope extensions and the flags ```DesktopPWAsLinkCapturingWithScopeExtensions```` and ````WebAppEnableScopeExtensions``` are enabled.  Note, the API does not support resetting the linkCapturing to the initial value, uninstalling and installing the web app again will reset it.  TODO(crbug.com/339453269): Setting this value on ChromeOS is not supported yet.
    :param display_mode: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['manifestId'] = manifest_id
    if link_capturing is not None:
        params['linkCapturing'] = link_capturing
    if display_mode is not None:
        params['displayMode'] = display_mode.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'PWA.changeAppUserSettings',
        'params': params,
    }
    json = yield cmd_dict

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\wheel\vendored\packaging\_manylinux.py ===
import collections
import contextlib
import functools
import os
import re
import sys
import warnings
from typing import Dict, Generator, Iterator, NamedTuple, Optional, Sequence, Tuple

from ._elffile import EIClass, EIData, ELFFile, EMachine

EF_ARM_ABIMASK = 0xFF000000
EF_ARM_ABI_VER5 = 0x05000000
EF_ARM_ABI_FLOAT_HARD = 0x00000400


# `os.PathLike` not a generic type until Python 3.9, so sticking with `str`
# as the type for `path` until then.
@contextlib.contextmanager
def _parse_elf(path: str) -> Generator[Optional[ELFFile], None, None]:
    try:
        with open(path, "rb") as f:
            yield ELFFile(f)
    except (OSError, TypeError, ValueError):
        yield None


def _is_linux_armhf(executable: str) -> bool:
    # hard-float ABI can be detected from the ELF header of the running
    # process
    # https://static.docs.arm.com/ihi0044/g/aaelf32.pdf
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.Arm
            and f.flags & EF_ARM_ABIMASK == EF_ARM_ABI_VER5
            and f.flags & EF_ARM_ABI_FLOAT_HARD == EF_ARM_ABI_FLOAT_HARD
        )


def _is_linux_i686(executable: str) -> bool:
    with _parse_elf(executable) as f:
        return (
            f is not None
            and f.capacity == EIClass.C32
            and f.encoding == EIData.Lsb
            and f.machine == EMachine.I386
        )


def _have_compatible_abi(executable: str, archs: Sequence[str]) -> bool:
    if "armv7l" in archs:
        return _is_linux_armhf(executable)
    if "i686" in archs:
        return _is_linux_i686(executable)
    allowed_archs = {
        "x86_64",
        "aarch64",
        "ppc64",
        "ppc64le",
        "s390x",
        "loongarch64",
        "riscv64",
    }
    return any(arch in allowed_archs for arch in archs)


# If glibc ever changes its major version, we need to know what the last
# minor version was, so we can build the complete list of all versions.
# For now, guess what the highest minor version might be, assume it will
# be 50 for testing. Once this actually happens, update the dictionary
# with the actual value.
_LAST_GLIBC_MINOR: Dict[int, int] = collections.defaultdict(lambda: 50)


class _GLibCVersion(NamedTuple):
    major: int
    minor: int


def _glibc_version_string_confstr() -> Optional[str]:
    """
    Primary implementation of glibc_version_string using os.confstr.
    """
    # os.confstr is quite a bit faster than ctypes.DLL. It's also less likely
    # to be broken or missing. This strategy is used in the standard library
    # platform module.
    # https://github.com/python/cpython/blob/fcf1d003bf4f0100c/Lib/platform.py#L175-L183
    try:
        # Should be a string like "glibc 2.17".
        version_string: Optional[str] = os.confstr("CS_GNU_LIBC_VERSION")
        assert version_string is not None
        _, version = version_string.rsplit()
    except (AssertionError, AttributeError, OSError, ValueError):
        # os.confstr() or CS_GNU_LIBC_VERSION not available (or a bad value)...
        return None
    return version


def _glibc_version_string_ctypes() -> Optional[str]:
    """
    Fallback implementation of glibc_version_string using ctypes.
    """
    try:
        import ctypes
    except ImportError:
        return None

    # ctypes.CDLL(None) internally calls dlopen(NULL), and as the dlopen
    # manpage says, "If filename is NULL, then the returned handle is for the
    # main program". This way we can let the linker do the work to figure out
    # which libc our process is actually using.
    #
    # We must also handle the special case where the executable is not a
    # dynamically linked executable. This can occur when using musl libc,
    # for example. In this situation, dlopen() will error, leading to an
    # OSError. Interestingly, at least in the case of musl, there is no
    # errno set on the OSError. The single string argument used to construct
    # OSError comes from libc itself and is therefore not portable to
    # hard code here. In any case, failure to call dlopen() means we
    # can proceed, so we bail on our attempt.
    try:
        process_namespace = ctypes.CDLL(None)
    except OSError:
        return None

    try:
        gnu_get_libc_version = process_namespace.gnu_get_libc_version
    except AttributeError:
        # Symbol doesn't exist -> therefore, we are not linked to
        # glibc.
        return None

    # Call gnu_get_libc_version, which returns a string like "2.5"
    gnu_get_libc_version.restype = ctypes.c_char_p
    version_str: str = gnu_get_libc_version()
    # py2 / py3 compatibility:
    if not isinstance(version_str, str):
        version_str = version_str.decode("ascii")

    return version_str


def _glibc_version_string() -> Optional[str]:
    """Returns glibc version string, or None if not using glibc."""
    return _glibc_version_string_confstr() or _glibc_version_string_ctypes()


def _parse_glibc_version(version_str: str) -> Tuple[int, int]:
    """Parse glibc version.

    We use a regexp instead of str.split because we want to discard any
    random junk that might come after the minor version -- this might happen
    in patched/forked versions of glibc (e.g. Linaro's version of glibc
    uses version strings like "2.20-2014.11"). See gh-3588.
    """
    m = re.match(r"(?P<major>[0-9]+)\.(?P<minor>[0-9]+)", version_str)
    if not m:
        warnings.warn(
            f"Expected glibc version with 2 components major.minor,"
            f" got: {version_str}",
            RuntimeWarning,
        )
        return -1, -1
    return int(m.group("major")), int(m.group("minor"))


@functools.lru_cache
def _get_glibc_version() -> Tuple[int, int]:
    version_str = _glibc_version_string()
    if version_str is None:
        return (-1, -1)
    return _parse_glibc_version(version_str)


# From PEP 513, PEP 600
def _is_compatible(arch: str, version: _GLibCVersion) -> bool:
    sys_glibc = _get_glibc_version()
    if sys_glibc < version:
        return False
    # Check for presence of _manylinux module.
    try:
        import _manylinux
    except ImportError:
        return True
    if hasattr(_manylinux, "manylinux_compatible"):
        result = _manylinux.manylinux_compatible(version[0], version[1], arch)
        if result is not None:
            return bool(result)
        return True
    if version == _GLibCVersion(2, 5):
        if hasattr(_manylinux, "manylinux1_compatible"):
            return bool(_manylinux.manylinux1_compatible)
    if version == _GLibCVersion(2, 12):
        if hasattr(_manylinux, "manylinux2010_compatible"):
            return bool(_manylinux.manylinux2010_compatible)
    if version == _GLibCVersion(2, 17):
        if hasattr(_manylinux, "manylinux2014_compatible"):
            return bool(_manylinux.manylinux2014_compatible)
    return True


_LEGACY_MANYLINUX_MAP = {
    # CentOS 7 w/ glibc 2.17 (PEP 599)
    (2, 17): "manylinux2014",
    # CentOS 6 w/ glibc 2.12 (PEP 571)
    (2, 12): "manylinux2010",
    # CentOS 5 w/ glibc 2.5 (PEP 513)
    (2, 5): "manylinux1",
}


def platform_tags(archs: Sequence[str]) -> Iterator[str]:
    """Generate manylinux tags compatible to the current platform.

    :param archs: Sequence of compatible architectures.
        The first one shall be the closest to the actual architecture and be the part of
        platform tag after the ``linux_`` prefix, e.g. ``x86_64``.
        The ``linux_`` prefix is assumed as a prerequisite for the current platform to
        be manylinux-compatible.

    :returns: An iterator of compatible manylinux tags.
    """
    if not _have_compatible_abi(sys.executable, archs):
        return
    # Oldest glibc to be supported regardless of architecture is (2, 17).
    too_old_glibc2 = _GLibCVersion(2, 16)
    if set(archs) & {"x86_64", "i686"}:
        # On x86/i686 also oldest glibc to be supported is (2, 5).
        too_old_glibc2 = _GLibCVersion(2, 4)
    current_glibc = _GLibCVersion(*_get_glibc_version())
    glibc_max_list = [current_glibc]
    # We can assume compatibility across glibc major versions.
    # https://sourceware.org/bugzilla/show_bug.cgi?id=24636
    #
    # Build a list of maximum glibc versions so that we can
    # output the canonical list of all glibc from current_glibc
    # down to too_old_glibc2, including all intermediary versions.
    for glibc_major in range(current_glibc.major - 1, 1, -1):
        glibc_minor = _LAST_GLIBC_MINOR[glibc_major]
        glibc_max_list.append(_GLibCVersion(glibc_major, glibc_minor))
    for arch in archs:
        for glibc_max in glibc_max_list:
            if glibc_max.major == too_old_glibc2.major:
                min_minor = too_old_glibc2.minor
            else:
                # For other glibc major versions oldest supported is (x, 0).
                min_minor = -1
            for glibc_minor in range(glibc_max.minor, min_minor, -1):
                glibc_version = _GLibCVersion(glibc_max.major, glibc_minor)
                tag = "manylinux_{}_{}".format(*glibc_version)
                if _is_compatible(arch, glibc_version):
                    yield f"{tag}_{arch}"
                # Handle the legacy manylinux1, manylinux2010, manylinux2014 tags.
                if glibc_version in _LEGACY_MANYLINUX_MAP:
                    legacy_tag = _LEGACY_MANYLINUX_MAP[glibc_version]
                    if _is_compatible(arch, glibc_version):
                        yield f"{legacy_tag}_{arch}"

# === NexusCore/openenv\Lib\site-packages\aiohappyeyeballs\impl.py ===
"""Base implementation."""

import asyncio
import collections
import contextlib
import functools
import itertools
import socket
from typing import List, Optional, Sequence, Set, Union

from . import _staggered
from .types import AddrInfoType, SocketFactoryType


async def start_connection(
    addr_infos: Sequence[AddrInfoType],
    *,
    local_addr_infos: Optional[Sequence[AddrInfoType]] = None,
    happy_eyeballs_delay: Optional[float] = None,
    interleave: Optional[int] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
    socket_factory: Optional[SocketFactoryType] = None,
) -> socket.socket:
    """
    Connect to a TCP server.

    Create a socket connection to a specified destination.  The
    destination is specified as a list of AddrInfoType tuples as
    returned from getaddrinfo().

    The arguments are, in order:

    * ``family``: the address family, e.g. ``socket.AF_INET`` or
        ``socket.AF_INET6``.
    * ``type``: the socket type, e.g. ``socket.SOCK_STREAM`` or
        ``socket.SOCK_DGRAM``.
    * ``proto``: the protocol, e.g. ``socket.IPPROTO_TCP`` or
        ``socket.IPPROTO_UDP``.
    * ``canonname``: the canonical name of the address, e.g.
        ``"www.python.org"``.
    * ``sockaddr``: the socket address

    This method is a coroutine which will try to establish the connection
    in the background. When successful, the coroutine returns a
    socket.

    The expected use case is to use this method in conjunction with
    loop.create_connection() to establish a connection to a server::

            socket = await start_connection(addr_infos)
            transport, protocol = await loop.create_connection(
                MyProtocol, sock=socket, ...)
    """
    if not (current_loop := loop):
        current_loop = asyncio.get_running_loop()

    single_addr_info = len(addr_infos) == 1

    if happy_eyeballs_delay is not None and interleave is None:
        # If using happy eyeballs, default to interleave addresses by family
        interleave = 1

    if interleave and not single_addr_info:
        addr_infos = _interleave_addrinfos(addr_infos, interleave)

    sock: Optional[socket.socket] = None
    # uvloop can raise RuntimeError instead of OSError
    exceptions: List[List[Union[OSError, RuntimeError]]] = []
    if happy_eyeballs_delay is None or single_addr_info:
        # not using happy eyeballs
        for addrinfo in addr_infos:
            try:
                sock = await _connect_sock(
                    current_loop,
                    exceptions,
                    addrinfo,
                    local_addr_infos,
                    None,
                    socket_factory,
                )
                break
            except (RuntimeError, OSError):
                continue
    else:  # using happy eyeballs
        open_sockets: Set[socket.socket] = set()
        try:
            sock, _, _ = await _staggered.staggered_race(
                (
                    functools.partial(
                        _connect_sock,
                        current_loop,
                        exceptions,
                        addrinfo,
                        local_addr_infos,
                        open_sockets,
                        socket_factory,
                    )
                    for addrinfo in addr_infos
                ),
                happy_eyeballs_delay,
            )
        finally:
            # If we have a winner, staggered_race will
            # cancel the other tasks, however there is a
            # small race window where any of the other tasks
            # can be done before they are cancelled which
            # will leave the socket open. To avoid this problem
            # we pass a set to _connect_sock to keep track of
            # the open sockets and close them here if there
            # are any "runner up" sockets.
            for s in open_sockets:
                if s is not sock:
                    with contextlib.suppress(OSError):
                        s.close()
            open_sockets = None  # type: ignore[assignment]

    if sock is None:
        all_exceptions = [exc for sub in exceptions for exc in sub]
        try:
            first_exception = all_exceptions[0]
            if len(all_exceptions) == 1:
                raise first_exception
            else:
                # If they all have the same str(), raise one.
                model = str(first_exception)
                if all(str(exc) == model for exc in all_exceptions):
                    raise first_exception
                # Raise a combined exception so the user can see all
                # the various error messages.
                msg = "Multiple exceptions: {}".format(
                    ", ".join(str(exc) for exc in all_exceptions)
                )
                # If the errno is the same for all exceptions, raise
                # an OSError with that errno.
                if isinstance(first_exception, OSError):
                    first_errno = first_exception.errno
                    if all(
                        isinstance(exc, OSError) and exc.errno == first_errno
                        for exc in all_exceptions
                    ):
                        raise OSError(first_errno, msg)
                elif isinstance(first_exception, RuntimeError) and all(
                    isinstance(exc, RuntimeError) for exc in all_exceptions
                ):
                    raise RuntimeError(msg)
                # We have a mix of OSError and RuntimeError
                # so we have to pick which one to raise.
                # and we raise OSError for compatibility
                raise OSError(msg)
        finally:
            all_exceptions = None  # type: ignore[assignment]
            exceptions = None  # type: ignore[assignment]

    return sock


async def _connect_sock(
    loop: asyncio.AbstractEventLoop,
    exceptions: List[List[Union[OSError, RuntimeError]]],
    addr_info: AddrInfoType,
    local_addr_infos: Optional[Sequence[AddrInfoType]] = None,
    open_sockets: Optional[Set[socket.socket]] = None,
    socket_factory: Optional[SocketFactoryType] = None,
) -> socket.socket:
    """
    Create, bind and connect one socket.

    If open_sockets is passed, add the socket to the set of open sockets.
    Any failure caught here will remove the socket from the set and close it.

    Callers can use this set to close any sockets that are not the winner
    of all staggered tasks in the result there are runner up sockets aka
    multiple winners.
    """
    my_exceptions: List[Union[OSError, RuntimeError]] = []
    exceptions.append(my_exceptions)
    family, type_, proto, _, address = addr_info
    sock = None
    try:
        if socket_factory is not None:
            sock = socket_factory(addr_info)
        else:
            sock = socket.socket(family=family, type=type_, proto=proto)
        if open_sockets is not None:
            open_sockets.add(sock)
        sock.setblocking(False)
        if local_addr_infos is not None:
            for lfamily, _, _, _, laddr in local_addr_infos:
                # skip local addresses of different family
                if lfamily != family:
                    continue
                try:
                    sock.bind(laddr)
                    break
                except OSError as exc:
                    msg = (
                        f"error while attempting to bind on "
                        f"address {laddr!r}: "
                        f"{(exc.strerror or '').lower()}"
                    )
                    exc = OSError(exc.errno, msg)
                    my_exceptions.append(exc)
            else:  # all bind attempts failed
                if my_exceptions:
                    raise my_exceptions.pop()
                else:
                    raise OSError(f"no matching local address with {family=} found")
        await loop.sock_connect(sock, address)
        return sock
    except (RuntimeError, OSError) as exc:
        my_exceptions.append(exc)
        if sock is not None:
            if open_sockets is not None:
                open_sockets.remove(sock)
            try:
                sock.close()
            except OSError as e:
                my_exceptions.append(e)
                raise
        raise
    except:
        if sock is not None:
            if open_sockets is not None:
                open_sockets.remove(sock)
            try:
                sock.close()
            except OSError as e:
                my_exceptions.append(e)
                raise
        raise
    finally:
        exceptions = my_exceptions = None  # type: ignore[assignment]


def _interleave_addrinfos(
    addrinfos: Sequence[AddrInfoType], first_address_family_count: int = 1
) -> List[AddrInfoType]:
    """Interleave list of addrinfo tuples by family."""
    # Group addresses by family
    addrinfos_by_family: collections.OrderedDict[int, List[AddrInfoType]] = (
        collections.OrderedDict()
    )
    for addr in addrinfos:
        family = addr[0]
        if family not in addrinfos_by_family:
            addrinfos_by_family[family] = []
        addrinfos_by_family[family].append(addr)
    addrinfos_lists = list(addrinfos_by_family.values())

    reordered: List[AddrInfoType] = []
    if first_address_family_count > 1:
        reordered.extend(addrinfos_lists[0][: first_address_family_count - 1])
        del addrinfos_lists[0][: first_address_family_count - 1]
    reordered.extend(
        a
        for a in itertools.chain.from_iterable(itertools.zip_longest(*addrinfos_lists))
        if a is not None
    )
    return reordered

# === NexusCore/openenv\Lib\site-packages\litellm\responses\utils.py ===
import base64
from typing import Any, Dict, Optional, Union, cast, get_type_hints

import litellm
from litellm._logging import verbose_logger
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig
from litellm.types.llms.openai import (
    ResponseAPIUsage,
    ResponsesAPIOptionalRequestParams,
    ResponsesAPIResponse,
)
from litellm.types.responses.main import DecodedResponseId
from litellm.types.utils import SpecialEnums, Usage


class ResponsesAPIRequestUtils:
    """Helper utils for constructing ResponseAPI requests"""

    @staticmethod
    def get_optional_params_responses_api(
        model: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        response_api_optional_params: ResponsesAPIOptionalRequestParams,
    ) -> Dict:
        """
        Get optional parameters for the responses API.

        Args:
            params: Dictionary of all parameters
            model: The model name
            responses_api_provider_config: The provider configuration for responses API

        Returns:
            A dictionary of supported parameters for the responses API
        """
        # Remove None values and internal parameters

        # Get supported parameters for the model
        supported_params = responses_api_provider_config.get_supported_openai_params(
            model
        )

        # Check for unsupported parameters
        unsupported_params = [
            param
            for param in response_api_optional_params
            if param not in supported_params
        ]

        if unsupported_params:
            raise litellm.UnsupportedParamsError(
                model=model,
                message=f"The following parameters are not supported for model {model}: {', '.join(unsupported_params)}",
            )

        # Map parameters to provider-specific format
        mapped_params = responses_api_provider_config.map_openai_params(
            response_api_optional_params=response_api_optional_params,
            model=model,
            drop_params=litellm.drop_params,
        )

        return mapped_params

    @staticmethod
    def get_requested_response_api_optional_param(
        params: Dict[str, Any],
    ) -> ResponsesAPIOptionalRequestParams:
        """
        Filter parameters to only include those defined in ResponsesAPIOptionalRequestParams.

        Args:
            params: Dictionary of parameters to filter

        Returns:
            ResponsesAPIOptionalRequestParams instance with only the valid parameters
        """
        valid_keys = get_type_hints(ResponsesAPIOptionalRequestParams).keys()
        filtered_params = {
            k: v for k, v in params.items() if k in valid_keys and v is not None
        }

        # decode previous_response_id if it's a litellm encoded id
        if "previous_response_id" in filtered_params:
            decoded_previous_response_id = ResponsesAPIRequestUtils.decode_previous_response_id_to_original_previous_response_id(
                filtered_params["previous_response_id"]
            )
            filtered_params["previous_response_id"] = decoded_previous_response_id

        if "metadata" in filtered_params:
            from litellm.utils import add_openai_metadata

            filtered_params["metadata"] = add_openai_metadata(
                filtered_params["metadata"]
            )

        return cast(ResponsesAPIOptionalRequestParams, filtered_params)

    @staticmethod
    def _update_responses_api_response_id_with_model_id(
        responses_api_response: ResponsesAPIResponse,
        custom_llm_provider: Optional[str],
        litellm_metadata: Optional[Dict[str, Any]] = None,
    ) -> ResponsesAPIResponse:
        """
        Update the responses_api_response_id with model_id and custom_llm_provider

        This builds a composite ID containing the custom LLM provider, model ID, and original response ID
        """
        litellm_metadata = litellm_metadata or {}
        model_info: Dict[str, Any] = litellm_metadata.get("model_info", {}) or {}
        model_id = model_info.get("id")
        updated_id = ResponsesAPIRequestUtils._build_responses_api_response_id(
            model_id=model_id,
            custom_llm_provider=custom_llm_provider,
            response_id=responses_api_response.id,
        )

        responses_api_response.id = updated_id
        return responses_api_response

    @staticmethod
    def _build_responses_api_response_id(
        custom_llm_provider: Optional[str],
        model_id: Optional[str],
        response_id: str,
    ) -> str:
        """Build the responses_api_response_id"""
        assembled_id: str = str(
            SpecialEnums.LITELLM_MANAGED_RESPONSE_COMPLETE_STR.value
        ).format(custom_llm_provider, model_id, response_id)
        base64_encoded_id: str = base64.b64encode(assembled_id.encode("utf-8")).decode(
            "utf-8"
        )
        return f"resp_{base64_encoded_id}"

    @staticmethod
    def _decode_responses_api_response_id(
        response_id: str,
    ) -> DecodedResponseId:
        """
        Decode the responses_api_response_id

        Returns:
            DecodedResponseId: Structured tuple with custom_llm_provider, model_id, and response_id
        """
        try:
            # Remove prefix and decode
            cleaned_id = response_id.replace("resp_", "")
            decoded_id = base64.b64decode(cleaned_id.encode("utf-8")).decode("utf-8")

            # Parse components using known prefixes
            if ";" not in decoded_id:
                return DecodedResponseId(
                    custom_llm_provider=None,
                    model_id=None,
                    response_id=response_id,
                )

            parts = decoded_id.split(";")

            # Format: litellm:custom_llm_provider:{};model_id:{};response_id:{}
            custom_llm_provider = None
            model_id = None

            if (
                len(parts) >= 3
            ):  # Full format with custom_llm_provider, model_id, and response_id
                custom_llm_provider_part = parts[0]
                model_id_part = parts[1]
                response_part = parts[2]

                custom_llm_provider = custom_llm_provider_part.replace(
                    "litellm:custom_llm_provider:", ""
                )
                model_id = model_id_part.replace("model_id:", "")
                decoded_response_id = response_part.replace("response_id:", "")
            else:
                decoded_response_id = response_id

            return DecodedResponseId(
                custom_llm_provider=custom_llm_provider,
                model_id=model_id,
                response_id=decoded_response_id,
            )
        except Exception as e:
            verbose_logger.debug(f"Error decoding response_id '{response_id}': {e}")
            return DecodedResponseId(
                custom_llm_provider=None,
                model_id=None,
                response_id=response_id,
            )

    @staticmethod
    def get_model_id_from_response_id(response_id: Optional[str]) -> Optional[str]:
        """Get the model_id from the response_id"""
        if response_id is None:
            return None
        decoded_response_id = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(response_id)
        )
        return decoded_response_id.get("model_id") or None

    @staticmethod
    def decode_previous_response_id_to_original_previous_response_id(
        previous_response_id: str,
    ) -> str:
        """
        Decode the previous_response_id to the original previous_response_id

        Why?
            - LiteLLM encodes the `custom_llm_provider` and `model_id` into the `previous_response_id` this helps with maintaining session consistency when load balancing multiple deployments of the same model.
            - We cannot send the litellm encoded b64 to the upstream llm api, hence we decode it to the original `previous_response_id`

        Args:
            previous_response_id: The previous_response_id to decode

        Returns:
            The original previous_response_id
        """
        decoded_response_id = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                previous_response_id
            )
        )
        return decoded_response_id.get("response_id", previous_response_id)


class ResponseAPILoggingUtils:
    @staticmethod
    def _is_response_api_usage(usage: Union[dict, ResponseAPIUsage]) -> bool:
        """returns True if usage is from OpenAI Response API"""
        if isinstance(usage, ResponseAPIUsage):
            return True
        if "input_tokens" in usage and "output_tokens" in usage:
            return True
        return False

    @staticmethod
    def _transform_response_api_usage_to_chat_usage(
        usage: Optional[Union[dict, ResponseAPIUsage]],
    ) -> Usage:
        """Tranforms the ResponseAPIUsage object to a Usage object"""
        if usage is None:
            return Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )
        response_api_usage: ResponseAPIUsage = (
            ResponseAPIUsage(**usage) if isinstance(usage, dict) else usage
        )
        prompt_tokens: int = response_api_usage.input_tokens or 0
        completion_tokens: int = response_api_usage.output_tokens or 0
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\d.py ===
"""
    pygments.lexers.d
    ~~~~~~~~~~~~~~~~~

    Lexers for D languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.lexer import RegexLexer, include, words, bygroups
from pygments.token import Comment, Keyword, Name, String, Number, \
    Punctuation, Whitespace

__all__ = ['DLexer', 'CrocLexer', 'MiniDLexer']


class DLexer(RegexLexer):
    """
    For D source.
    """
    name = 'D'
    url = 'https://dlang.org/'
    filenames = ['*.d', '*.di']
    aliases = ['d']
    mimetypes = ['text/x-dsrc']
    version_added = '1.2'

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            # (r'\\\n', Text), # line continuations
            # Comments
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
            (r'/\+', Comment.Multiline, 'nested_comment'),
            # Keywords
            (words((
                'abstract', 'alias', 'align', 'asm', 'assert', 'auto', 'body',
                'break', 'case', 'cast', 'catch', 'class', 'const', 'continue',
                'debug', 'default', 'delegate', 'delete', 'deprecated', 'do', 'else',
                'enum', 'export', 'extern', 'finally', 'final', 'foreach_reverse',
                'foreach', 'for', 'function', 'goto', 'if', 'immutable', 'import',
                'interface', 'invariant', 'inout', 'in', 'is', 'lazy', 'mixin',
                'module', 'new', 'nothrow', 'out', 'override', 'package', 'pragma',
                'private', 'protected', 'public', 'pure', 'ref', 'return', 'scope',
                'shared', 'static', 'struct', 'super', 'switch', 'synchronized',
                'template', 'this', 'throw', 'try', 'typeid', 'typeof',
                'union', 'unittest', 'version', 'volatile', 'while', 'with',
                '__gshared', '__traits', '__vector', '__parameters'),
                suffix=r'\b'),
             Keyword),
            (words((
                # Removed in 2.072
                'typedef', ),
                suffix=r'\b'),
             Keyword.Removed),
            (words((
                'bool', 'byte', 'cdouble', 'cent', 'cfloat', 'char', 'creal',
                'dchar', 'double', 'float', 'idouble', 'ifloat', 'int', 'ireal',
                'long', 'real', 'short', 'ubyte', 'ucent', 'uint', 'ulong',
                'ushort', 'void', 'wchar'), suffix=r'\b'),
             Keyword.Type),
            (r'(false|true|null)\b', Keyword.Constant),
            (words((
                '__FILE__', '__FILE_FULL_PATH__', '__MODULE__', '__LINE__', '__FUNCTION__',
                '__PRETTY_FUNCTION__', '__DATE__', '__EOF__', '__TIME__', '__TIMESTAMP__',
                '__VENDOR__', '__VERSION__'), suffix=r'\b'),
             Keyword.Pseudo),
            (r'macro\b', Keyword.Reserved),
            (r'(string|wstring|dstring|size_t|ptrdiff_t)\b', Name.Builtin),
            # FloatLiteral
            # -- HexFloat
            (r'0[xX]([0-9a-fA-F_]*\.[0-9a-fA-F_]+|[0-9a-fA-F_]+)'
             r'[pP][+\-]?[0-9_]+[fFL]?[i]?', Number.Float),
            # -- DecimalFloat
            (r'[0-9_]+(\.[0-9_]+[eE][+\-]?[0-9_]+|'
             r'\.[0-9_]*|[eE][+\-]?[0-9_]+)[fFL]?[i]?', Number.Float),
            (r'\.(0|[1-9][0-9_]*)([eE][+\-]?[0-9_]+)?[fFL]?[i]?', Number.Float),
            # IntegerLiteral
            # -- Binary
            (r'0[Bb][01_]+', Number.Bin),
            # -- Octal
            (r'0[0-7_]+', Number.Oct),
            # -- Hexadecimal
            (r'0[xX][0-9a-fA-F_]+', Number.Hex),
            # -- Decimal
            (r'(0|[1-9][0-9_]*)([LUu]|Lu|LU|uL|UL)?', Number.Integer),
            # CharacterLiteral
            (r"""'(\\['"?\\abfnrtv]|\\x[0-9a-fA-F]{2}|\\[0-7]{1,3}"""
             r"""|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|\\&\w+;|.)'""",
             String.Char),
            # StringLiteral
            # -- WysiwygString
            (r'r"[^"]*"[cwd]?', String),
            # -- AlternateWysiwygString
            (r'`[^`]*`[cwd]?', String),
            # -- DoubleQuotedString
            (r'"(\\\\|\\[^\\]|[^"\\])*"[cwd]?', String),
            # -- EscapeSequence
            (r"\\(['\"?\\abfnrtv]|x[0-9a-fA-F]{2}|[0-7]{1,3}"
             r"|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|&\w+;)",
             String),
            # -- HexString
            (r'x"[0-9a-fA-F_\s]*"[cwd]?', String),
            # -- DelimitedString
            (r'q"\[', String, 'delimited_bracket'),
            (r'q"\(', String, 'delimited_parenthesis'),
            (r'q"<', String, 'delimited_angle'),
            (r'q"\{', String, 'delimited_curly'),
            (r'q"([a-zA-Z_]\w*)\n.*?\n\1"', String),
            (r'q"(.).*?\1"', String),
            # -- TokenString
            (r'q\{', String, 'token_string'),
            # Attributes
            (r'@([a-zA-Z_]\w*)?', Name.Decorator),
            # Tokens
            (r'(~=|\^=|%=|\*=|==|!>=|!<=|!<>=|!<>|!<|!>|!=|>>>=|>>>|>>=|>>|>='
             r'|<>=|<>|<<=|<<|<=|\+\+|\+=|--|-=|\|\||\|=|&&|&=|\.\.\.|\.\.|/=)'
             r'|[/.&|\-+<>!()\[\]{}?,;:$=*%^~]', Punctuation),
            # Identifier
            (r'[a-zA-Z_]\w*', Name),
            # Line
            (r'(#line)(\s)(.*)(\n)', bygroups(Comment.Special, Whitespace,
                Comment.Special, Whitespace)),
        ],
        'nested_comment': [
            (r'[^+/]+', Comment.Multiline),
            (r'/\+', Comment.Multiline, '#push'),
            (r'\+/', Comment.Multiline, '#pop'),
            (r'[+/]', Comment.Multiline),
        ],
        'token_string': [
            (r'\{', Punctuation, 'token_string_nest'),
            (r'\}', String, '#pop'),
            include('root'),
        ],
        'token_string_nest': [
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            include('root'),
        ],
        'delimited_bracket': [
            (r'[^\[\]]+', String),
            (r'\[', String, 'delimited_inside_bracket'),
            (r'\]"', String, '#pop'),
        ],
        'delimited_inside_bracket': [
            (r'[^\[\]]+', String),
            (r'\[', String, '#push'),
            (r'\]', String, '#pop'),
        ],
        'delimited_parenthesis': [
            (r'[^()]+', String),
            (r'\(', String, 'delimited_inside_parenthesis'),
            (r'\)"', String, '#pop'),
        ],
        'delimited_inside_parenthesis': [
            (r'[^()]+', String),
            (r'\(', String, '#push'),
            (r'\)', String, '#pop'),
        ],
        'delimited_angle': [
            (r'[^<>]+', String),
            (r'<', String, 'delimited_inside_angle'),
            (r'>"', String, '#pop'),
        ],
        'delimited_inside_angle': [
            (r'[^<>]+', String),
            (r'<', String, '#push'),
            (r'>', String, '#pop'),
        ],
        'delimited_curly': [
            (r'[^{}]+', String),
            (r'\{', String, 'delimited_inside_curly'),
            (r'\}"', String, '#pop'),
        ],
        'delimited_inside_curly': [
            (r'[^{}]+', String),
            (r'\{', String, '#push'),
            (r'\}', String, '#pop'),
        ],
    }


class CrocLexer(RegexLexer):
    """
    For Croc source.
    """
    name = 'Croc'
    url = 'http://jfbillingsley.com/croc'
    filenames = ['*.croc']
    aliases = ['croc']
    mimetypes = ['text/x-crocsrc']
    version_added = ''

    tokens = {
        'root': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            # Comments
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),
            (r'/\*', Comment.Multiline, 'nestedcomment'),
            # Keywords
            (words((
                'as', 'assert', 'break', 'case', 'catch', 'class', 'continue',
                'default', 'do', 'else', 'finally', 'for', 'foreach', 'function',
                'global', 'namespace', 'if', 'import', 'in', 'is', 'local',
                'module', 'return', 'scope', 'super', 'switch', 'this', 'throw',
                'try', 'vararg', 'while', 'with', 'yield'), suffix=r'\b'),
             Keyword),
            (r'(false|true|null)\b', Keyword.Constant),
            # FloatLiteral
            (r'([0-9][0-9_]*)(?=[.eE])(\.[0-9][0-9_]*)?([eE][+\-]?[0-9_]+)?',
             Number.Float),
            # IntegerLiteral
            # -- Binary
            (r'0[bB][01][01_]*', Number.Bin),
            # -- Hexadecimal
            (r'0[xX][0-9a-fA-F][0-9a-fA-F_]*', Number.Hex),
            # -- Decimal
            (r'([0-9][0-9_]*)(?![.eE])', Number.Integer),
            # CharacterLiteral
            (r"""'(\\['"\\nrt]|\\x[0-9a-fA-F]{2}|\\[0-9]{1,3}"""
             r"""|\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}|.)'""",
             String.Char),
            # StringLiteral
            # -- WysiwygString
            (r'@"(""|[^"])*"', String),
            (r'@`(``|[^`])*`', String),
            (r"@'(''|[^'])*'", String),
            # -- DoubleQuotedString
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            # Tokens
            (r'(~=|\^=|%=|\*=|==|!=|>>>=|>>>|>>=|>>|>=|<=>|\?=|-\>'
             r'|<<=|<<|<=|\+\+|\+=|--|-=|\|\||\|=|&&|&=|\.\.|/=)'
             r'|[-/.&$@|\+<>!()\[\]{}?,;:=*%^~#\\]', Punctuation),
            # Identifier
            (r'[a-zA-Z_]\w*', Name),
        ],
        'nestedcomment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
    }


class MiniDLexer(CrocLexer):
    """
    For MiniD source. MiniD is now known as Croc.
    """
    name = 'MiniD'
    filenames = []  # don't lex .md as MiniD, reserve for Markdown
    aliases = ['minid']
    mimetypes = ['text/x-minidsrc']
    version_added = ''

# === NexusCore/myenv\Lib\site-packages\pip\_internal\resolution\resolvelib\provider.py ===
import collections
import math
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    TypeVar,
    Union,
)

from pip._vendor.resolvelib.providers import AbstractProvider

from .base import Candidate, Constraint, Requirement
from .candidates import REQUIRES_PYTHON_IDENTIFIER
from .factory import Factory

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference
    from pip._vendor.resolvelib.resolvers import RequirementInformation

    PreferenceInformation = RequirementInformation[Requirement, Candidate]

    _ProviderBase = AbstractProvider[Requirement, Candidate, str]
else:
    _ProviderBase = AbstractProvider

# Notes on the relationship between the provider, the factory, and the
# candidate and requirement classes.
#
# The provider is a direct implementation of the resolvelib class. Its role
# is to deliver the API that resolvelib expects.
#
# Rather than work with completely abstract "requirement" and "candidate"
# concepts as resolvelib does, pip has concrete classes implementing these two
# ideas. The API of Requirement and Candidate objects are defined in the base
# classes, but essentially map fairly directly to the equivalent provider
# methods. In particular, `find_matches` and `is_satisfied_by` are
# requirement methods, and `get_dependencies` is a candidate method.
#
# The factory is the interface to pip's internal mechanisms. It is stateless,
# and is created by the resolver and held as a property of the provider. It is
# responsible for creating Requirement and Candidate objects, and provides
# services to those objects (access to pip's finder and preparer).


D = TypeVar("D")
V = TypeVar("V")


def _get_with_identifier(
    mapping: Mapping[str, V],
    identifier: str,
    default: D,
) -> Union[D, V]:
    """Get item from a package name lookup mapping with a resolver identifier.

    This extra logic is needed when the target mapping is keyed by package
    name, which cannot be directly looked up with an identifier (which may
    contain requested extras). Additional logic is added to also look up a value
    by "cleaning up" the extras from the identifier.
    """
    if identifier in mapping:
        return mapping[identifier]
    # HACK: Theoretically we should check whether this identifier is a valid
    # "NAME[EXTRAS]" format, and parse out the name part with packaging or
    # some regular expression. But since pip's resolver only spits out three
    # kinds of identifiers: normalized PEP 503 names, normalized names plus
    # extras, and Requires-Python, we can cheat a bit here.
    name, open_bracket, _ = identifier.partition("[")
    if open_bracket and name in mapping:
        return mapping[name]
    return default


class PipProvider(_ProviderBase):
    """Pip's provider implementation for resolvelib.

    :params constraints: A mapping of constraints specified by the user. Keys
        are canonicalized project names.
    :params ignore_dependencies: Whether the user specified ``--no-deps``.
    :params upgrade_strategy: The user-specified upgrade strategy.
    :params user_requested: A set of canonicalized package names that the user
        supplied for pip to install/upgrade.
    """

    def __init__(
        self,
        factory: Factory,
        constraints: Dict[str, Constraint],
        ignore_dependencies: bool,
        upgrade_strategy: str,
        user_requested: Dict[str, int],
    ) -> None:
        self._factory = factory
        self._constraints = constraints
        self._ignore_dependencies = ignore_dependencies
        self._upgrade_strategy = upgrade_strategy
        self._user_requested = user_requested
        self._known_depths: Dict[str, float] = collections.defaultdict(lambda: math.inf)

    def identify(self, requirement_or_candidate: Union[Requirement, Candidate]) -> str:
        return requirement_or_candidate.name

    def get_preference(
        self,
        identifier: str,
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterable["PreferenceInformation"]],
        backtrack_causes: Sequence["PreferenceInformation"],
    ) -> "Preference":
        """Produce a sort key for given requirement based on preference.

        The lower the return value is, the more preferred this group of
        arguments is.

        Currently pip considers the following in order:

        * Prefer if any of the known requirements is "direct", e.g. points to an
          explicit URL.
        * If equal, prefer if any requirement is "pinned", i.e. contains
          operator ``===`` or ``==``.
        * If equal, calculate an approximate "depth" and resolve requirements
          closer to the user-specified requirements first. If the depth cannot
          by determined (eg: due to no matching parents), it is considered
          infinite.
        * Order user-specified requirements by the order they are specified.
        * If equal, prefers "non-free" requirements, i.e. contains at least one
          operator, such as ``>=`` or ``<``.
        * If equal, order alphabetically for consistency (helps debuggability).
        """
        try:
            next(iter(information[identifier]))
        except StopIteration:
            # There is no information for this identifier, so there's no known
            # candidates.
            has_information = False
        else:
            has_information = True

        if has_information:
            lookups = (r.get_candidate_lookup() for r, _ in information[identifier])
            candidate, ireqs = zip(*lookups)
        else:
            candidate, ireqs = None, ()

        operators = [
            specifier.operator
            for specifier_set in (ireq.specifier for ireq in ireqs if ireq)
            for specifier in specifier_set
        ]

        direct = candidate is not None
        pinned = any(op[:2] == "==" for op in operators)
        unfree = bool(operators)

        try:
            requested_order: Union[int, float] = self._user_requested[identifier]
        except KeyError:
            requested_order = math.inf
            if has_information:
                parent_depths = (
                    self._known_depths[parent.name] if parent is not None else 0.0
                    for _, parent in information[identifier]
                )
                inferred_depth = min(d for d in parent_depths) + 1.0
            else:
                inferred_depth = math.inf
        else:
            inferred_depth = 1.0
        self._known_depths[identifier] = inferred_depth

        requested_order = self._user_requested.get(identifier, math.inf)

        # Requires-Python has only one candidate and the check is basically
        # free, so we always do it first to avoid needless work if it fails.
        requires_python = identifier == REQUIRES_PYTHON_IDENTIFIER

        # Prefer the causes of backtracking on the assumption that the problem
        # resolving the dependency tree is related to the failures that caused
        # the backtracking
        backtrack_cause = self.is_backtrack_cause(identifier, backtrack_causes)

        return (
            not requires_python,
            not direct,
            not pinned,
            not backtrack_cause,
            inferred_depth,
            requested_order,
            not unfree,
            identifier,
        )

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator[Requirement]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
    ) -> Iterable[Candidate]:
        def _eligible_for_upgrade(identifier: str) -> bool:
            """Are upgrades allowed for this project?

            This checks the upgrade strategy, and whether the project was one
            that the user specified in the command line, in order to decide
            whether we should upgrade if there's a newer version available.

            (Note that we don't need access to the `--upgrade` flag, because
            an upgrade strategy of "to-satisfy-only" means that `--upgrade`
            was not specified).
            """
            if self._upgrade_strategy == "eager":
                return True
            elif self._upgrade_strategy == "only-if-needed":
                user_order = _get_with_identifier(
                    self._user_requested,
                    identifier,
                    default=None,
                )
                return user_order is not None
            return False

        constraint = _get_with_identifier(
            self._constraints,
            identifier,
            default=Constraint.empty(),
        )
        return self._factory.find_candidates(
            identifier=identifier,
            requirements=requirements,
            constraint=constraint,
            prefers_installed=(not _eligible_for_upgrade(identifier)),
            incompatibilities=incompatibilities,
            is_satisfied_by=self.is_satisfied_by,
        )

    @lru_cache(maxsize=None)
    def is_satisfied_by(self, requirement: Requirement, candidate: Candidate) -> bool:
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate: Candidate) -> Sequence[Requirement]:
        with_requires = not self._ignore_dependencies
        return [r for r in candidate.iter_dependencies(with_requires) if r is not None]

    @staticmethod
    def is_backtrack_cause(
        identifier: str, backtrack_causes: Sequence["PreferenceInformation"]
    ) -> bool:
        for backtrack_cause in backtrack_causes:
            if identifier == backtrack_cause.requirement.name:
                return True
            if backtrack_cause.parent and identifier == backtrack_cause.parent.name:
                return True
        return False

# === NexusCore/openenv\Lib\site-packages\anyio\to_process.py ===
from __future__ import annotations

import os
import pickle
import subprocess
import sys
from collections import deque
from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from typing import TypeVar, cast

from ._core._eventloop import current_time, get_async_backend, get_cancelled_exc_class
from ._core._exceptions import BrokenWorkerProcess
from ._core._subprocesses import open_process
from ._core._synchronization import CapacityLimiter
from ._core._tasks import CancelScope, fail_after
from .abc import ByteReceiveStream, ByteSendStream, Process
from .lowlevel import RunVar, checkpoint_if_cancelled
from .streams.buffered import BufferedByteReceiveStream

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

WORKER_MAX_IDLE_TIME = 300  # 5 minutes

T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")

_process_pool_workers: RunVar[set[Process]] = RunVar("_process_pool_workers")
_process_pool_idle_workers: RunVar[deque[tuple[Process, float]]] = RunVar(
    "_process_pool_idle_workers"
)
_default_process_limiter: RunVar[CapacityLimiter] = RunVar("_default_process_limiter")


async def run_sync(  # type: ignore[return]
    func: Callable[[Unpack[PosArgsT]], T_Retval],
    *args: Unpack[PosArgsT],
    cancellable: bool = False,
    limiter: CapacityLimiter | None = None,
) -> T_Retval:
    """
    Call the given function with the given arguments in a worker process.

    If the ``cancellable`` option is enabled and the task waiting for its completion is
    cancelled, the worker process running it will be abruptly terminated using SIGKILL
    (or ``terminateProcess()`` on Windows).

    :param func: a callable
    :param args: positional arguments for the callable
    :param cancellable: ``True`` to allow cancellation of the operation while it's
        running
    :param limiter: capacity limiter to use to limit the total amount of processes
        running (if omitted, the default limiter is used)
    :return: an awaitable that yields the return value of the function.

    """

    async def send_raw_command(pickled_cmd: bytes) -> object:
        try:
            await stdin.send(pickled_cmd)
            response = await buffered.receive_until(b"\n", 50)
            status, length = response.split(b" ")
            if status not in (b"RETURN", b"EXCEPTION"):
                raise RuntimeError(
                    f"Worker process returned unexpected response: {response!r}"
                )

            pickled_response = await buffered.receive_exactly(int(length))
        except BaseException as exc:
            workers.discard(process)
            try:
                process.kill()
                with CancelScope(shield=True):
                    await process.aclose()
            except ProcessLookupError:
                pass

            if isinstance(exc, get_cancelled_exc_class()):
                raise
            else:
                raise BrokenWorkerProcess from exc

        retval = pickle.loads(pickled_response)
        if status == b"EXCEPTION":
            assert isinstance(retval, BaseException)
            raise retval
        else:
            return retval

    # First pickle the request before trying to reserve a worker process
    await checkpoint_if_cancelled()
    request = pickle.dumps(("run", func, args), protocol=pickle.HIGHEST_PROTOCOL)

    # If this is the first run in this event loop thread, set up the necessary variables
    try:
        workers = _process_pool_workers.get()
        idle_workers = _process_pool_idle_workers.get()
    except LookupError:
        workers = set()
        idle_workers = deque()
        _process_pool_workers.set(workers)
        _process_pool_idle_workers.set(idle_workers)
        get_async_backend().setup_process_pool_exit_at_shutdown(workers)

    async with limiter or current_default_process_limiter():
        # Pop processes from the pool (starting from the most recently used) until we
        # find one that hasn't exited yet
        process: Process
        while idle_workers:
            process, idle_since = idle_workers.pop()
            if process.returncode is None:
                stdin = cast(ByteSendStream, process.stdin)
                buffered = BufferedByteReceiveStream(
                    cast(ByteReceiveStream, process.stdout)
                )

                # Prune any other workers that have been idle for WORKER_MAX_IDLE_TIME
                # seconds or longer
                now = current_time()
                killed_processes: list[Process] = []
                while idle_workers:
                    if now - idle_workers[0][1] < WORKER_MAX_IDLE_TIME:
                        break

                    process_to_kill, idle_since = idle_workers.popleft()
                    process_to_kill.kill()
                    workers.remove(process_to_kill)
                    killed_processes.append(process_to_kill)

                with CancelScope(shield=True):
                    for killed_process in killed_processes:
                        await killed_process.aclose()

                break

            workers.remove(process)
        else:
            command = [sys.executable, "-u", "-m", __name__]
            process = await open_process(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            try:
                stdin = cast(ByteSendStream, process.stdin)
                buffered = BufferedByteReceiveStream(
                    cast(ByteReceiveStream, process.stdout)
                )
                with fail_after(20):
                    message = await buffered.receive(6)

                if message != b"READY\n":
                    raise BrokenWorkerProcess(
                        f"Worker process returned unexpected response: {message!r}"
                    )

                main_module_path = getattr(sys.modules["__main__"], "__file__", None)
                pickled = pickle.dumps(
                    ("init", sys.path, main_module_path),
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
                await send_raw_command(pickled)
            except (BrokenWorkerProcess, get_cancelled_exc_class()):
                raise
            except BaseException as exc:
                process.kill()
                raise BrokenWorkerProcess(
                    "Error during worker process initialization"
                ) from exc

            workers.add(process)

        with CancelScope(shield=not cancellable):
            try:
                return cast(T_Retval, await send_raw_command(request))
            finally:
                if process in workers:
                    idle_workers.append((process, current_time()))


def current_default_process_limiter() -> CapacityLimiter:
    """
    Return the capacity limiter that is used by default to limit the number of worker
    processes.

    :return: a capacity limiter object

    """
    try:
        return _default_process_limiter.get()
    except LookupError:
        limiter = CapacityLimiter(os.cpu_count() or 2)
        _default_process_limiter.set(limiter)
        return limiter


def process_worker() -> None:
    # Redirect standard streams to os.devnull so that user code won't interfere with the
    # parent-worker communication
    stdin = sys.stdin
    stdout = sys.stdout
    sys.stdin = open(os.devnull)
    sys.stdout = open(os.devnull, "w")

    stdout.buffer.write(b"READY\n")
    while True:
        retval = exception = None
        try:
            command, *args = pickle.load(stdin.buffer)
        except EOFError:
            return
        except BaseException as exc:
            exception = exc
        else:
            if command == "run":
                func, args = args
                try:
                    retval = func(*args)
                except BaseException as exc:
                    exception = exc
            elif command == "init":
                main_module_path: str | None
                sys.path, main_module_path = args
                del sys.modules["__main__"]
                if main_module_path and os.path.isfile(main_module_path):
                    # Load the parent's main module but as __mp_main__ instead of
                    # __main__ (like multiprocessing does) to avoid infinite recursion
                    try:
                        spec = spec_from_file_location("__mp_main__", main_module_path)
                        if spec and spec.loader:
                            main = module_from_spec(spec)
                            spec.loader.exec_module(main)
                            sys.modules["__main__"] = main
                    except BaseException as exc:
                        exception = exc
        try:
            if exception is not None:
                status = b"EXCEPTION"
                pickled = pickle.dumps(exception, pickle.HIGHEST_PROTOCOL)
            else:
                status = b"RETURN"
                pickled = pickle.dumps(retval, pickle.HIGHEST_PROTOCOL)
        except BaseException as exc:
            exception = exc
            status = b"EXCEPTION"
            pickled = pickle.dumps(exc, pickle.HIGHEST_PROTOCOL)

        stdout.buffer.write(b"%s %d\n" % (status, len(pickled)))
        stdout.buffer.write(pickled)

        # Respect SIGTERM
        if isinstance(exception, SystemExit):
            raise exception


if __name__ == "__main__":
    process_worker()

# === NexusCore/openenv\Lib\site-packages\numpy\conftest.py ===
"""
Pytest configuration and fixtures for the Numpy test suite.
"""
import os
import string
import sys
import tempfile
import warnings
from contextlib import contextmanager

import hypothesis
import pytest

import numpy
import numpy as np
from numpy._core._multiarray_tests import get_fpu_mode
from numpy._core.tests._natype import get_stringdtype_dtype, pd_NA
from numpy.testing._private.utils import NOGIL_BUILD

try:
    from scipy_doctest.conftest import dt_config
    HAVE_SCPDT = True
except ModuleNotFoundError:
    HAVE_SCPDT = False


_old_fpu_mode = None
_collect_results = {}

# Use a known and persistent tmpdir for hypothesis' caches, which
# can be automatically cleared by the OS or user.
hypothesis.configuration.set_hypothesis_home_dir(
    os.path.join(tempfile.gettempdir(), ".hypothesis")
)

# We register two custom profiles for Numpy - for details see
# https://hypothesis.readthedocs.io/en/latest/settings.html
# The first is designed for our own CI runs; the latter also
# forces determinism and is designed for use via np.test()
hypothesis.settings.register_profile(
    name="numpy-profile", deadline=None, print_blob=True,
)
hypothesis.settings.register_profile(
    name="np.test() profile",
    deadline=None, print_blob=True, database=None, derandomize=True,
    suppress_health_check=list(hypothesis.HealthCheck),
)
# Note that the default profile is chosen based on the presence
# of pytest.ini, but can be overridden by passing the
# --hypothesis-profile=NAME argument to pytest.
_pytest_ini = os.path.join(os.path.dirname(__file__), "..", "pytest.ini")
hypothesis.settings.load_profile(
    "numpy-profile" if os.path.isfile(_pytest_ini) else "np.test() profile"
)

# The experimentalAPI is used in _umath_tests
os.environ["NUMPY_EXPERIMENTAL_DTYPE_API"] = "1"

def pytest_configure(config):
    config.addinivalue_line("markers",
        "valgrind_error: Tests that are known to error under valgrind.")
    config.addinivalue_line("markers",
        "leaks_references: Tests that are known to leak references.")
    config.addinivalue_line("markers",
        "slow: Tests that are very slow.")
    config.addinivalue_line("markers",
        "slow_pypy: Tests that are very slow on pypy.")


def pytest_addoption(parser):
    parser.addoption("--available-memory", action="store", default=None,
                     help=("Set amount of memory available for running the "
                           "test suite. This can result to tests requiring "
                           "especially large amounts of memory to be skipped. "
                           "Equivalent to setting environment variable "
                           "NPY_AVAILABLE_MEM. Default: determined"
                           "automatically."))


gil_enabled_at_start = True
if NOGIL_BUILD:
    gil_enabled_at_start = sys._is_gil_enabled()


def pytest_sessionstart(session):
    available_mem = session.config.getoption('available_memory')
    if available_mem is not None:
        os.environ['NPY_AVAILABLE_MEM'] = available_mem


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if NOGIL_BUILD and not gil_enabled_at_start and sys._is_gil_enabled():
        tr = terminalreporter
        tr.ensure_newline()
        tr.section("GIL re-enabled", sep="=", red=True, bold=True)
        tr.line("The GIL was re-enabled at runtime during the tests.")
        tr.line("This can happen with no test failures if the RuntimeWarning")
        tr.line("raised by Python when this happens is filtered by a test.")
        tr.line("")
        tr.line("Please ensure all new C modules declare support for running")
        tr.line("without the GIL. Any new tests that intentionally imports ")
        tr.line("code that re-enables the GIL should do so in a subprocess.")
        pytest.exit("GIL re-enabled during tests", returncode=1)

# FIXME when yield tests are gone.
@pytest.hookimpl()
def pytest_itemcollected(item):
    """
    Check FPU precision mode was not changed during test collection.

    The clumsy way we do it here is mainly necessary because numpy
    still uses yield tests, which can execute code at test collection
    time.
    """
    global _old_fpu_mode

    mode = get_fpu_mode()

    if _old_fpu_mode is None:
        _old_fpu_mode = mode
    elif mode != _old_fpu_mode:
        _collect_results[item] = (_old_fpu_mode, mode)
        _old_fpu_mode = mode


@pytest.fixture(scope="function", autouse=True)
def check_fpu_mode(request):
    """
    Check FPU precision mode was not changed during the test.
    """
    old_mode = get_fpu_mode()
    yield
    new_mode = get_fpu_mode()

    if old_mode != new_mode:
        raise AssertionError(f"FPU precision mode changed from {old_mode:#x} to "
                             f"{new_mode:#x} during the test")

    collect_result = _collect_results.get(request.node)
    if collect_result is not None:
        old_mode, new_mode = collect_result
        raise AssertionError(f"FPU precision mode changed from {old_mode:#x} to "
                             f"{new_mode:#x} when collecting the test")


@pytest.fixture(autouse=True)
def add_np(doctest_namespace):
    doctest_namespace['np'] = numpy

@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    monkeypatch.setenv('PYTHONHASHSEED', '0')


if HAVE_SCPDT:

    @contextmanager
    def warnings_errors_and_rng(test=None):
        """Filter out the wall of DeprecationWarnings.
        """
        msgs = ["The numpy.linalg.linalg",
                "The numpy.fft.helper",
                "dep_util",
                "pkg_resources",
                "numpy.core.umath",
                "msvccompiler",
                "Deprecated call",
                "numpy.core",
                "Importing from numpy.matlib",
                "This function is deprecated.",    # random_integers
                "Data type alias 'a'",     # numpy.rec.fromfile
                "Arrays of 2-dimensional vectors",   # matlib.cross
                "`in1d` is deprecated", ]
        msg = "|".join(msgs)

        msgs_r = [
            "invalid value encountered",
            "divide by zero encountered"
        ]
        msg_r = "|".join(msgs_r)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore', category=DeprecationWarning, message=msg
            )
            warnings.filterwarnings(
                'ignore', category=RuntimeWarning, message=msg_r
            )
            yield

    # find and check doctests under this context manager
    dt_config.user_context_mgr = warnings_errors_and_rng

    # numpy specific tweaks from refguide-check
    dt_config.rndm_markers.add('#uninitialized')
    dt_config.rndm_markers.add('# uninitialized')

    # make the checker pick on mismatched dtypes
    dt_config.strict_check = True

    import doctest
    dt_config.optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS

    # recognize the StringDType repr
    dt_config.check_namespace['StringDType'] = numpy.dtypes.StringDType

    # temporary skips
    dt_config.skiplist = {
        'numpy.savez',    # unclosed file
        'numpy.matlib.savez',
        'numpy.__array_namespace_info__',
        'numpy.matlib.__array_namespace_info__',
    }

    # xfail problematic tutorials
    dt_config.pytest_extra_xfail = {
        'how-to-verify-bug.rst': '',
        'c-info.ufunc-tutorial.rst': '',
        'basics.interoperability.rst': 'needs pandas',
        'basics.dispatch.rst': 'errors out in /testing/overrides.py',
        'basics.subclassing.rst': '.. testcode:: admonitions not understood',
        'misc.rst': 'manipulates warnings',
    }

    # ignores are for things fail doctest collection (optionals etc)
    dt_config.pytest_extra_ignore = [
        'numpy/distutils',
        'numpy/_core/cversions.py',
        'numpy/_pyinstaller',
        'numpy/random/_examples',
        'numpy/f2py/_backends/_distutils.py',
    ]


@pytest.fixture
def random_string_list():
    chars = list(string.ascii_letters + string.digits)
    chars = np.array(chars, dtype="U1")
    ret = np.random.choice(chars, size=100 * 10, replace=True)
    return ret.view("U100")


@pytest.fixture(params=[True, False])
def coerce(request):
    return request.param


@pytest.fixture(
    params=["unset", None, pd_NA, np.nan, float("nan"), "__nan__"],
    ids=["unset", "None", "pandas.NA", "np.nan", "float('nan')", "string nan"],
)
def na_object(request):
    return request.param


@pytest.fixture()
def dtype(na_object, coerce):
    return get_stringdtype_dtype(na_object, coerce)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2511.py ===
#
# This file is part of pyasn1-modules software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# X.509 certificate Request Message Format (CRMF) syntax
#
# ASN.1 source from:
# http://tools.ietf.org/html/rfc2511
#
# Sample captures could be obtained with OpenSSL
#
from pyasn1_modules import rfc2315
from pyasn1_modules.rfc2459 import *

MAX = float('inf')

id_pkix = univ.ObjectIdentifier('1.3.6.1.5.5.7')
id_pkip = univ.ObjectIdentifier('1.3.6.1.5.5.7.5')
id_regCtrl = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1')
id_regCtrl_regToken = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.1')
id_regCtrl_authenticator = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.2')
id_regCtrl_pkiPublicationInfo = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.3')
id_regCtrl_pkiArchiveOptions = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.4')
id_regCtrl_oldCertID = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.5')
id_regCtrl_protocolEncrKey = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.1.6')
id_regInfo = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.2')
id_regInfo_utf8Pairs = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.2.1')
id_regInfo_certReq = univ.ObjectIdentifier('1.3.6.1.5.5.7.5.2.2')


# This should be in PKIX Certificate Extensions module

class GeneralName(univ.OctetString):
    pass


# end of PKIX Certificate Extensions module

class UTF8Pairs(char.UTF8String):
    pass


class ProtocolEncrKey(SubjectPublicKeyInfo):
    pass


class CertId(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('issuer', GeneralName()),
        namedtype.NamedType('serialNumber', univ.Integer())
    )


class OldCertId(CertId):
    pass


class KeyGenParameters(univ.OctetString):
    pass


class EncryptedValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('intendedAlg', AlgorithmIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('symmAlg', AlgorithmIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('encSymmKey', univ.BitString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('keyAlg', AlgorithmIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('valueHint', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.NamedType('encValue', univ.BitString())
    )


class EncryptedKey(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('encryptedValue', EncryptedValue()),
        namedtype.NamedType('envelopedData', rfc2315.EnvelopedData().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )


class PKIArchiveOptions(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('encryptedPrivKey', EncryptedKey().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('keyGenParameters', KeyGenParameters().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('archiveRemGenPrivKey',
                            univ.Boolean().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class SinglePubInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('pubMethod', univ.Integer(
            namedValues=namedval.NamedValues(('dontCare', 0), ('x500', 1), ('web', 2), ('ldap', 3)))),
        namedtype.OptionalNamedType('pubLocation', GeneralName())
    )


class PKIPublicationInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('action',
                            univ.Integer(namedValues=namedval.NamedValues(('dontPublish', 0), ('pleasePublish', 1)))),
        namedtype.OptionalNamedType('pubInfos', univ.SequenceOf(componentType=SinglePubInfo()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX)))
    )


class Authenticator(char.UTF8String):
    pass


class RegToken(char.UTF8String):
    pass


class SubsequentMessage(univ.Integer):
    namedValues = namedval.NamedValues(
        ('encrCert', 0),
        ('challengeResp', 1)
    )


class POPOPrivKey(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('thisMessage',
                            univ.BitString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('subsequentMessage', SubsequentMessage().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.NamedType('dhMAC',
                            univ.BitString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class PBMParameter(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('salt', univ.OctetString()),
        namedtype.NamedType('owf', AlgorithmIdentifier()),
        namedtype.NamedType('iterationCount', univ.Integer()),
        namedtype.NamedType('mac', AlgorithmIdentifier())
    )


class PKMACValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algId', AlgorithmIdentifier()),
        namedtype.NamedType('value', univ.BitString())
    )


class POPOSigningKeyInput(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'authInfo', univ.Choice(
                componentType=namedtype.NamedTypes(
                    namedtype.NamedType(
                        'sender', GeneralName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))
                    ),
                    namedtype.NamedType('publicKeyMAC', PKMACValue())
                )
            )
        ),
        namedtype.NamedType('publicKey', SubjectPublicKeyInfo())
    )


class POPOSigningKey(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('poposkInput', POPOSigningKeyInput().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.NamedType('algorithmIdentifier', AlgorithmIdentifier()),
        namedtype.NamedType('signature', univ.BitString())
    )


class ProofOfPossession(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('raVerified',
                            univ.Null().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.NamedType('signature', POPOSigningKey().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.NamedType('keyEncipherment', POPOPrivKey().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.NamedType('keyAgreement', POPOPrivKey().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)))
    )


class Controls(univ.SequenceOf):
    componentType = AttributeTypeAndValue()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class OptionalValidity(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('notBefore',
                                    Time().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('notAfter',
                                    Time().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class CertTemplate(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('version', Version().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('serialNumber', univ.Integer().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('signingAlg', AlgorithmIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('issuer', Name().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('validity', OptionalValidity().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.OptionalNamedType('subject', Name().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
        namedtype.OptionalNamedType('publicKey', SubjectPublicKeyInfo().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6))),
        namedtype.OptionalNamedType('issuerUID', UniqueIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
        namedtype.OptionalNamedType('subjectUID', UniqueIdentifier().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8))),
        namedtype.OptionalNamedType('extensions', Extensions().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)))
    )


class CertRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certReqId', univ.Integer()),
        namedtype.NamedType('certTemplate', CertTemplate()),
        namedtype.OptionalNamedType('controls', Controls())
    )


class CertReq(CertRequest):
    pass


class CertReqMsg(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('certReq', CertRequest()),
        namedtype.OptionalNamedType('pop', ProofOfPossession()),
        namedtype.OptionalNamedType('regInfo', univ.SequenceOf(componentType=AttributeTypeAndValue()).subtype(
            sizeSpec=constraint.ValueSizeConstraint(1, MAX)))
    )


class CertReqMessages(univ.SequenceOf):
    componentType = CertReqMsg()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc4055.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with a very small amount of assistance from
# asn1ate v.0.6.0.
# Modified by Russ Housley to add maps for opentypes.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Additional Algorithms and Identifiers for RSA Cryptography
# for use in Certificates and CRLs
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc4055.txt
#
from pyasn1.type import namedtype
from pyasn1.type import tag
from pyasn1.type import univ

from pyasn1_modules import rfc5280


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))
    return univ.ObjectIdentifier(output)


id_sha1 = _OID(1, 3, 14, 3, 2, 26)

id_sha256 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 1)

id_sha384 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 2)

id_sha512 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 3)

id_sha224 = _OID(2, 16, 840, 1, 101, 3, 4, 2, 4)

rsaEncryption = _OID(1, 2, 840, 113549, 1, 1, 1)

id_mgf1 = _OID(1, 2, 840, 113549, 1, 1, 8)

id_RSAES_OAEP = _OID(1, 2, 840, 113549, 1, 1, 7)

id_pSpecified = _OID(1, 2, 840, 113549, 1, 1, 9)

id_RSASSA_PSS = _OID(1, 2, 840, 113549, 1, 1, 10)

sha256WithRSAEncryption = _OID(1, 2, 840, 113549, 1, 1, 11)

sha384WithRSAEncryption = _OID(1, 2, 840, 113549, 1, 1, 12)

sha512WithRSAEncryption = _OID(1, 2, 840, 113549, 1, 1, 13)

sha224WithRSAEncryption = _OID(1, 2, 840, 113549, 1, 1, 14)

sha1Identifier = rfc5280.AlgorithmIdentifier()
sha1Identifier['algorithm'] = id_sha1
sha1Identifier['parameters'] = univ.Null("")

sha224Identifier = rfc5280.AlgorithmIdentifier()
sha224Identifier['algorithm'] = id_sha224
sha224Identifier['parameters'] = univ.Null("")

sha256Identifier = rfc5280.AlgorithmIdentifier()
sha256Identifier['algorithm'] = id_sha256
sha256Identifier['parameters'] = univ.Null("")

sha384Identifier = rfc5280.AlgorithmIdentifier()
sha384Identifier['algorithm'] = id_sha384
sha384Identifier['parameters'] = univ.Null("")

sha512Identifier = rfc5280.AlgorithmIdentifier()
sha512Identifier['algorithm'] = id_sha512
sha512Identifier['parameters'] = univ.Null("")

mgf1SHA1Identifier = rfc5280.AlgorithmIdentifier()
mgf1SHA1Identifier['algorithm'] = id_mgf1
mgf1SHA1Identifier['parameters'] = sha1Identifier

mgf1SHA224Identifier = rfc5280.AlgorithmIdentifier()
mgf1SHA224Identifier['algorithm'] = id_mgf1
mgf1SHA224Identifier['parameters'] = sha224Identifier

mgf1SHA256Identifier = rfc5280.AlgorithmIdentifier()
mgf1SHA256Identifier['algorithm'] = id_mgf1
mgf1SHA256Identifier['parameters'] = sha256Identifier

mgf1SHA384Identifier = rfc5280.AlgorithmIdentifier()
mgf1SHA384Identifier['algorithm'] = id_mgf1
mgf1SHA384Identifier['parameters'] = sha384Identifier

mgf1SHA512Identifier = rfc5280.AlgorithmIdentifier()
mgf1SHA512Identifier['algorithm'] = id_mgf1
mgf1SHA512Identifier['parameters'] = sha512Identifier

pSpecifiedEmptyIdentifier = rfc5280.AlgorithmIdentifier()
pSpecifiedEmptyIdentifier['algorithm'] = id_pSpecified
pSpecifiedEmptyIdentifier['parameters'] = univ.OctetString(value='')


class RSAPublicKey(univ.Sequence):
    pass

RSAPublicKey.componentType = namedtype.NamedTypes(
    namedtype.NamedType('modulus', univ.Integer()),
    namedtype.NamedType('publicExponent', univ.Integer())
)


class HashAlgorithm(rfc5280.AlgorithmIdentifier):
    pass


class MaskGenAlgorithm(rfc5280.AlgorithmIdentifier):
    pass


class RSAES_OAEP_params(univ.Sequence):
    pass

RSAES_OAEP_params.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('hashFunc', rfc5280.AlgorithmIdentifier().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('maskGenFunc', rfc5280.AlgorithmIdentifier().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.OptionalNamedType('pSourceFunc', rfc5280.AlgorithmIdentifier().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
)

rSAES_OAEP_Default_Params = RSAES_OAEP_params()

rSAES_OAEP_Default_Identifier = rfc5280.AlgorithmIdentifier()
rSAES_OAEP_Default_Identifier['algorithm'] = id_RSAES_OAEP
rSAES_OAEP_Default_Identifier['parameters'] = rSAES_OAEP_Default_Params

rSAES_OAEP_SHA224_Params = RSAES_OAEP_params()
rSAES_OAEP_SHA224_Params['hashFunc'] = sha224Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSAES_OAEP_SHA224_Params['maskGenFunc'] = mgf1SHA224Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSAES_OAEP_SHA224_Identifier = rfc5280.AlgorithmIdentifier()
rSAES_OAEP_SHA224_Identifier['algorithm'] = id_RSAES_OAEP
rSAES_OAEP_SHA224_Identifier['parameters'] = rSAES_OAEP_SHA224_Params

rSAES_OAEP_SHA256_Params = RSAES_OAEP_params()
rSAES_OAEP_SHA256_Params['hashFunc'] = sha256Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSAES_OAEP_SHA256_Params['maskGenFunc'] = mgf1SHA256Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSAES_OAEP_SHA256_Identifier = rfc5280.AlgorithmIdentifier()
rSAES_OAEP_SHA256_Identifier['algorithm'] = id_RSAES_OAEP
rSAES_OAEP_SHA256_Identifier['parameters'] = rSAES_OAEP_SHA256_Params

rSAES_OAEP_SHA384_Params = RSAES_OAEP_params()
rSAES_OAEP_SHA384_Params['hashFunc'] = sha384Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSAES_OAEP_SHA384_Params['maskGenFunc'] = mgf1SHA384Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSAES_OAEP_SHA384_Identifier = rfc5280.AlgorithmIdentifier()
rSAES_OAEP_SHA384_Identifier['algorithm'] = id_RSAES_OAEP
rSAES_OAEP_SHA384_Identifier['parameters'] = rSAES_OAEP_SHA384_Params

rSAES_OAEP_SHA512_Params = RSAES_OAEP_params()
rSAES_OAEP_SHA512_Params['hashFunc'] = sha512Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSAES_OAEP_SHA512_Params['maskGenFunc'] = mgf1SHA512Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSAES_OAEP_SHA512_Identifier = rfc5280.AlgorithmIdentifier()
rSAES_OAEP_SHA512_Identifier['algorithm'] = id_RSAES_OAEP
rSAES_OAEP_SHA512_Identifier['parameters'] = rSAES_OAEP_SHA512_Params


class RSASSA_PSS_params(univ.Sequence):
    pass

RSASSA_PSS_params.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('hashAlgorithm', rfc5280.AlgorithmIdentifier().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('maskGenAlgorithm', rfc5280.AlgorithmIdentifier().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1))),
    namedtype.DefaultedNamedType('saltLength', univ.Integer(value=20).subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.DefaultedNamedType('trailerField', univ.Integer(value=1).subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

rSASSA_PSS_Default_Params = RSASSA_PSS_params()

rSASSA_PSS_Default_Identifier = rfc5280.AlgorithmIdentifier()
rSASSA_PSS_Default_Identifier['algorithm'] = id_RSASSA_PSS
rSASSA_PSS_Default_Identifier['parameters'] = rSASSA_PSS_Default_Params

rSASSA_PSS_SHA224_Params = RSASSA_PSS_params()
rSASSA_PSS_SHA224_Params['hashAlgorithm'] = sha224Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSASSA_PSS_SHA224_Params['maskGenAlgorithm'] = mgf1SHA224Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSASSA_PSS_SHA224_Identifier = rfc5280.AlgorithmIdentifier()
rSASSA_PSS_SHA224_Identifier['algorithm'] = id_RSASSA_PSS
rSASSA_PSS_SHA224_Identifier['parameters'] = rSASSA_PSS_SHA224_Params

rSASSA_PSS_SHA256_Params = RSASSA_PSS_params()
rSASSA_PSS_SHA256_Params['hashAlgorithm'] = sha256Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSASSA_PSS_SHA256_Params['maskGenAlgorithm'] = mgf1SHA256Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSASSA_PSS_SHA256_Identifier = rfc5280.AlgorithmIdentifier()
rSASSA_PSS_SHA256_Identifier['algorithm'] = id_RSASSA_PSS
rSASSA_PSS_SHA256_Identifier['parameters'] = rSASSA_PSS_SHA256_Params

rSASSA_PSS_SHA384_Params = RSASSA_PSS_params()
rSASSA_PSS_SHA384_Params['hashAlgorithm'] = sha384Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSASSA_PSS_SHA384_Params['maskGenAlgorithm'] = mgf1SHA384Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSASSA_PSS_SHA384_Identifier = rfc5280.AlgorithmIdentifier()
rSASSA_PSS_SHA384_Identifier['algorithm'] = id_RSASSA_PSS
rSASSA_PSS_SHA384_Identifier['parameters'] = rSASSA_PSS_SHA384_Params

rSASSA_PSS_SHA512_Params = RSASSA_PSS_params()
rSASSA_PSS_SHA512_Params['hashAlgorithm'] = sha512Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0), cloneValueFlag=True)
rSASSA_PSS_SHA512_Params['maskGenAlgorithm'] = mgf1SHA512Identifier.subtype(
    explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1), cloneValueFlag=True)

rSASSA_PSS_SHA512_Identifier = rfc5280.AlgorithmIdentifier()
rSASSA_PSS_SHA512_Identifier['algorithm'] = id_RSASSA_PSS
rSASSA_PSS_SHA512_Identifier['parameters'] = rSASSA_PSS_SHA512_Params


# Update the Algorithm Identifier map

_algorithmIdentifierMapUpdate = {
    id_sha1: univ.Null(),
    id_sha224: univ.Null(),
    id_sha256: univ.Null(),
    id_sha384: univ.Null(),
    id_sha512: univ.Null(),
    id_mgf1: rfc5280.AlgorithmIdentifier(),
    id_pSpecified: univ.OctetString(),
    id_RSAES_OAEP: RSAES_OAEP_params(),
    id_RSASSA_PSS: RSASSA_PSS_params(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)

# === NexusCore/openenv\Lib\site-packages\fontTools\encodings\MacRoman.py ===
MacRoman = [
    "NUL",
    "Eth",
    "eth",
    "Lslash",
    "lslash",
    "Scaron",
    "scaron",
    "Yacute",
    "yacute",
    "HT",
    "LF",
    "Thorn",
    "thorn",
    "CR",
    "Zcaron",
    "zcaron",
    "DLE",
    "DC1",
    "DC2",
    "DC3",
    "DC4",
    "onehalf",
    "onequarter",
    "onesuperior",
    "threequarters",
    "threesuperior",
    "twosuperior",
    "brokenbar",
    "minus",
    "multiply",
    "RS",
    "US",
    "space",
    "exclam",
    "quotedbl",
    "numbersign",
    "dollar",
    "percent",
    "ampersand",
    "quotesingle",
    "parenleft",
    "parenright",
    "asterisk",
    "plus",
    "comma",
    "hyphen",
    "period",
    "slash",
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "colon",
    "semicolon",
    "less",
    "equal",
    "greater",
    "question",
    "at",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "bracketleft",
    "backslash",
    "bracketright",
    "asciicircum",
    "underscore",
    "grave",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "braceleft",
    "bar",
    "braceright",
    "asciitilde",
    "DEL",
    "Adieresis",
    "Aring",
    "Ccedilla",
    "Eacute",
    "Ntilde",
    "Odieresis",
    "Udieresis",
    "aacute",
    "agrave",
    "acircumflex",
    "adieresis",
    "atilde",
    "aring",
    "ccedilla",
    "eacute",
    "egrave",
    "ecircumflex",
    "edieresis",
    "iacute",
    "igrave",
    "icircumflex",
    "idieresis",
    "ntilde",
    "oacute",
    "ograve",
    "ocircumflex",
    "odieresis",
    "otilde",
    "uacute",
    "ugrave",
    "ucircumflex",
    "udieresis",
    "dagger",
    "degree",
    "cent",
    "sterling",
    "section",
    "bullet",
    "paragraph",
    "germandbls",
    "registered",
    "copyright",
    "trademark",
    "acute",
    "dieresis",
    "notequal",
    "AE",
    "Oslash",
    "infinity",
    "plusminus",
    "lessequal",
    "greaterequal",
    "yen",
    "mu",
    "partialdiff",
    "summation",
    "product",
    "pi",
    "integral",
    "ordfeminine",
    "ordmasculine",
    "Omega",
    "ae",
    "oslash",
    "questiondown",
    "exclamdown",
    "logicalnot",
    "radical",
    "florin",
    "approxequal",
    "Delta",
    "guillemotleft",
    "guillemotright",
    "ellipsis",
    "nbspace",
    "Agrave",
    "Atilde",
    "Otilde",
    "OE",
    "oe",
    "endash",
    "emdash",
    "quotedblleft",
    "quotedblright",
    "quoteleft",
    "quoteright",
    "divide",
    "lozenge",
    "ydieresis",
    "Ydieresis",
    "fraction",
    "currency",
    "guilsinglleft",
    "guilsinglright",
    "fi",
    "fl",
    "daggerdbl",
    "periodcentered",
    "quotesinglbase",
    "quotedblbase",
    "perthousand",
    "Acircumflex",
    "Ecircumflex",
    "Aacute",
    "Edieresis",
    "Egrave",
    "Iacute",
    "Icircumflex",
    "Idieresis",
    "Igrave",
    "Oacute",
    "Ocircumflex",
    "apple",
    "Ograve",
    "Uacute",
    "Ucircumflex",
    "Ugrave",
    "dotlessi",
    "circumflex",
    "tilde",
    "macron",
    "breve",
    "dotaccent",
    "ring",
    "cedilla",
    "hungarumlaut",
    "ogonek",
    "caron",
]

# === NexusCore/openenv\Lib\site-packages\fontTools\encodings\StandardEncoding.py ===
StandardEncoding = [
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    "space",
    "exclam",
    "quotedbl",
    "numbersign",
    "dollar",
    "percent",
    "ampersand",
    "quoteright",
    "parenleft",
    "parenright",
    "asterisk",
    "plus",
    "comma",
    "hyphen",
    "period",
    "slash",
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "colon",
    "semicolon",
    "less",
    "equal",
    "greater",
    "question",
    "at",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "bracketleft",
    "backslash",
    "bracketright",
    "asciicircum",
    "underscore",
    "quoteleft",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "braceleft",
    "bar",
    "braceright",
    "asciitilde",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    "exclamdown",
    "cent",
    "sterling",
    "fraction",
    "yen",
    "florin",
    "section",
    "currency",
    "quotesingle",
    "quotedblleft",
    "guillemotleft",
    "guilsinglleft",
    "guilsinglright",
    "fi",
    "fl",
    ".notdef",
    "endash",
    "dagger",
    "daggerdbl",
    "periodcentered",
    ".notdef",
    "paragraph",
    "bullet",
    "quotesinglbase",
    "quotedblbase",
    "quotedblright",
    "guillemotright",
    "ellipsis",
    "perthousand",
    ".notdef",
    "questiondown",
    ".notdef",
    "grave",
    "acute",
    "circumflex",
    "tilde",
    "macron",
    "breve",
    "dotaccent",
    "dieresis",
    ".notdef",
    "ring",
    "cedilla",
    ".notdef",
    "hungarumlaut",
    "ogonek",
    "caron",
    "emdash",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    "AE",
    ".notdef",
    "ordfeminine",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    "Lslash",
    "Oslash",
    "OE",
    "ordmasculine",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
    "ae",
    ".notdef",
    ".notdef",
    ".notdef",
    "dotlessi",
    ".notdef",
    ".notdef",
    "lslash",
    "oslash",
    "oe",
    "germandbls",
    ".notdef",
    ".notdef",
    ".notdef",
    ".notdef",
]

# === NexusCore/openenv\Lib\site-packages\litellm\caching\in_memory_cache.py ===
"""
In-Memory Cache implementation

Has 4 methods:
    - set_cache
    - get_cache
    - async_set_cache
    - async_get_cache
"""

import json
import sys
import time
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from litellm.types.caching import RedisPipelineIncrementOperation

from pydantic import BaseModel

from litellm.constants import MAX_SIZE_PER_ITEM_IN_MEMORY_CACHE_IN_KB

from .base_cache import BaseCache


class InMemoryCache(BaseCache):
    def __init__(
        self,
        max_size_in_memory: Optional[int] = 200,
        default_ttl: Optional[
            int
        ] = 600,  # default ttl is 10 minutes. At maximum litellm rate limiting logic requires objects to be in memory for 1 minute
        max_size_per_item: Optional[int] = 1024,  # 1MB = 1024KB
    ):
        """
        max_size_in_memory [int]: Maximum number of items in cache. done to prevent memory leaks. Use 200 items as a default
        """
        self.max_size_in_memory = (
            max_size_in_memory or 200
        )  # set an upper bound of 200 items in-memory
        self.default_ttl = default_ttl or 600
        self.max_size_per_item = (
            max_size_per_item or MAX_SIZE_PER_ITEM_IN_MEMORY_CACHE_IN_KB
        )  # 1MB = 1024KB

        # in-memory cache
        self.cache_dict: dict = {}
        self.ttl_dict: dict = {}

    def check_value_size(self, value: Any):
        """
        Check if value size exceeds max_size_per_item (1MB)
        Returns True if value size is acceptable, False otherwise
        """
        try:
            # Fast path for common primitive types that are typically small
            if (
                isinstance(value, (bool, int, float, str))
                and len(str(value))
                < self.max_size_per_item * MAX_SIZE_PER_ITEM_IN_MEMORY_CACHE_IN_KB
            ):  # Conservative estimate
                return True

            # Direct size check for bytes objects
            if isinstance(value, bytes):
                return sys.getsizeof(value) / 1024 <= self.max_size_per_item

            # Handle special types without full conversion when possible
            if hasattr(value, "__sizeof__"):  # Use __sizeof__ if available
                size = value.__sizeof__() / 1024
                return size <= self.max_size_per_item

            # Fallback for complex types
            if isinstance(value, BaseModel) and hasattr(
                value, "model_dump"
            ):  # Pydantic v2
                value = value.model_dump()
            elif hasattr(value, "isoformat"):  # datetime objects
                return True  # datetime strings are always small

            # Only convert to JSON if absolutely necessary
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value, default=str)

            return sys.getsizeof(value) / 1024 <= self.max_size_per_item

        except Exception:
            return False

    def _is_key_expired(self, key: str) -> bool:
        """
        Check if a specific key is expired
        """
        return key in self.ttl_dict and time.time() > self.ttl_dict[key]

    def _remove_key(self, key: str) -> None:
        """
        Remove a key from both cache_dict and ttl_dict
        """
        self.cache_dict.pop(key, None)
        self.ttl_dict.pop(key, None)

    def evict_cache(self):
        """
        Eviction policy:
        - check if any items in ttl_dict are expired -> remove them from ttl_dict and cache_dict


        This guarantees the following:
        - 1. When item ttl not set: At minimumm each item will remain in memory for 5 minutes
        - 2. When ttl is set: the item will remain in memory for at least that amount of time
        - 3. the size of in-memory cache is bounded

        """
        for key in list(self.ttl_dict.keys()):
            if self._is_key_expired(key):
                self._remove_key(key)

                # de-reference the removed item
                # https://www.geeksforgeeks.org/diagnosing-and-fixing-memory-leaks-in-python/
                # One of the most common causes of memory leaks in Python is the retention of objects that are no longer being used.
                # This can occur when an object is referenced by another object, but the reference is never removed.

    def allow_ttl_override(self, key: str) -> bool:
        """
        Check if ttl is set for a key
        """
        ttl_time = self.ttl_dict.get(key)
        if ttl_time is None:  # if ttl is not set, allow override
            return True
        elif float(ttl_time) < time.time():  # if ttl is expired, allow override
            return True
        else:
            return False

    def set_cache(self, key, value, **kwargs):
        if len(self.cache_dict) >= self.max_size_in_memory:
            # only evict when cache is full
            self.evict_cache()
        if not self.check_value_size(value):
            return

        self.cache_dict[key] = value
        if self.allow_ttl_override(key):  # if ttl is not set, set it to default ttl
            if "ttl" in kwargs and kwargs["ttl"] is not None:
                self.ttl_dict[key] = time.time() + float(kwargs["ttl"])
            else:
                self.ttl_dict[key] = time.time() + self.default_ttl

    async def async_set_cache(self, key, value, **kwargs):
        self.set_cache(key=key, value=value, **kwargs)

    async def async_set_cache_pipeline(self, cache_list, ttl=None, **kwargs):
        for cache_key, cache_value in cache_list:
            if ttl is not None:
                self.set_cache(key=cache_key, value=cache_value, ttl=ttl)
            else:
                self.set_cache(key=cache_key, value=cache_value)

    async def async_set_cache_sadd(self, key, value: List, ttl: Optional[float]):
        """
        Add value to set
        """
        # get the value
        init_value = self.get_cache(key=key) or set()
        for val in value:
            init_value.add(val)
        self.set_cache(key, init_value, ttl=ttl)
        return value

    def evict_element_if_expired(self, key: str) -> bool:
        """
        Returns True if the element is expired and removed from the cache

        Returns False if the element is not expired
        """
        if self._is_key_expired(key):
            self._remove_key(key)
            return True
        return False

    def get_cache(self, key, **kwargs):
        if key in self.cache_dict:
            if self.evict_element_if_expired(key):
                return None
            original_cached_response = self.cache_dict[key]
            try:
                cached_response = json.loads(original_cached_response)
            except Exception:
                cached_response = original_cached_response
            return cached_response
        return None

    def batch_get_cache(self, keys: list, **kwargs):
        return_val = []
        for k in keys:
            val = self.get_cache(key=k, **kwargs)
            return_val.append(val)
        return return_val

    def increment_cache(self, key, value: int, **kwargs) -> int:
        # get the value
        init_value = self.get_cache(key=key) or 0
        value = init_value + value
        self.set_cache(key, value, **kwargs)
        return value

    async def async_get_cache(self, key, **kwargs):
        return self.get_cache(key=key, **kwargs)

    async def async_batch_get_cache(self, keys: list, **kwargs):
        return_val = []
        for k in keys:
            val = self.get_cache(key=k, **kwargs)
            return_val.append(val)
        return return_val

    async def async_increment(self, key, value: float, **kwargs) -> float:
        # get the value
        init_value = await self.async_get_cache(key=key) or 0
        value = init_value + value
        await self.async_set_cache(key, value, **kwargs)
        return value

    async def async_increment_pipeline(
        self, increment_list: List["RedisPipelineIncrementOperation"], **kwargs
    ) -> Optional[List[float]]:
        results = []
        for increment in increment_list:
            result = await self.async_increment(
                increment["key"], increment["increment_value"], **kwargs
            )
            results.append(result)
        return results

    def flush_cache(self):
        self.cache_dict.clear()
        self.ttl_dict.clear()

    async def disconnect(self):
        pass

    def delete_cache(self, key):
        self._remove_key(key)

    async def async_get_ttl(self, key: str) -> Optional[int]:
        """
        Get the remaining TTL of a key in in-memory cache
        """
        return self.ttl_dict.get(key, None)

    async def async_get_oldest_n_keys(self, n: int) -> List[str]:
        """
        Get the oldest n keys in the cache
        """
        # sorted ttl dict by ttl
        sorted_ttl_dict = sorted(self.ttl_dict.items(), key=lambda x: x[1])
        return [key for key, _ in sorted_ttl_dict[:n]]

# === NexusCore/openenv\Lib\site-packages\pip\_internal\resolution\resolvelib\provider.py ===
import collections
import math
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    TypeVar,
    Union,
)

from pip._vendor.resolvelib.providers import AbstractProvider

from .base import Candidate, Constraint, Requirement
from .candidates import REQUIRES_PYTHON_IDENTIFIER
from .factory import Factory

if TYPE_CHECKING:
    from pip._vendor.resolvelib.providers import Preference
    from pip._vendor.resolvelib.resolvers import RequirementInformation

    PreferenceInformation = RequirementInformation[Requirement, Candidate]

    _ProviderBase = AbstractProvider[Requirement, Candidate, str]
else:
    _ProviderBase = AbstractProvider

# Notes on the relationship between the provider, the factory, and the
# candidate and requirement classes.
#
# The provider is a direct implementation of the resolvelib class. Its role
# is to deliver the API that resolvelib expects.
#
# Rather than work with completely abstract "requirement" and "candidate"
# concepts as resolvelib does, pip has concrete classes implementing these two
# ideas. The API of Requirement and Candidate objects are defined in the base
# classes, but essentially map fairly directly to the equivalent provider
# methods. In particular, `find_matches` and `is_satisfied_by` are
# requirement methods, and `get_dependencies` is a candidate method.
#
# The factory is the interface to pip's internal mechanisms. It is stateless,
# and is created by the resolver and held as a property of the provider. It is
# responsible for creating Requirement and Candidate objects, and provides
# services to those objects (access to pip's finder and preparer).


D = TypeVar("D")
V = TypeVar("V")


def _get_with_identifier(
    mapping: Mapping[str, V],
    identifier: str,
    default: D,
) -> Union[D, V]:
    """Get item from a package name lookup mapping with a resolver identifier.

    This extra logic is needed when the target mapping is keyed by package
    name, which cannot be directly looked up with an identifier (which may
    contain requested extras). Additional logic is added to also look up a value
    by "cleaning up" the extras from the identifier.
    """
    if identifier in mapping:
        return mapping[identifier]
    # HACK: Theoretically we should check whether this identifier is a valid
    # "NAME[EXTRAS]" format, and parse out the name part with packaging or
    # some regular expression. But since pip's resolver only spits out three
    # kinds of identifiers: normalized PEP 503 names, normalized names plus
    # extras, and Requires-Python, we can cheat a bit here.
    name, open_bracket, _ = identifier.partition("[")
    if open_bracket and name in mapping:
        return mapping[name]
    return default


class PipProvider(_ProviderBase):
    """Pip's provider implementation for resolvelib.

    :params constraints: A mapping of constraints specified by the user. Keys
        are canonicalized project names.
    :params ignore_dependencies: Whether the user specified ``--no-deps``.
    :params upgrade_strategy: The user-specified upgrade strategy.
    :params user_requested: A set of canonicalized package names that the user
        supplied for pip to install/upgrade.
    """

    def __init__(
        self,
        factory: Factory,
        constraints: Dict[str, Constraint],
        ignore_dependencies: bool,
        upgrade_strategy: str,
        user_requested: Dict[str, int],
    ) -> None:
        self._factory = factory
        self._constraints = constraints
        self._ignore_dependencies = ignore_dependencies
        self._upgrade_strategy = upgrade_strategy
        self._user_requested = user_requested
        self._known_depths: Dict[str, float] = collections.defaultdict(lambda: math.inf)

    def identify(self, requirement_or_candidate: Union[Requirement, Candidate]) -> str:
        return requirement_or_candidate.name

    def get_preference(
        self,
        identifier: str,
        resolutions: Mapping[str, Candidate],
        candidates: Mapping[str, Iterator[Candidate]],
        information: Mapping[str, Iterable["PreferenceInformation"]],
        backtrack_causes: Sequence["PreferenceInformation"],
    ) -> "Preference":
        """Produce a sort key for given requirement based on preference.

        The lower the return value is, the more preferred this group of
        arguments is.

        Currently pip considers the following in order:

        * Prefer if any of the known requirements is "direct", e.g. points to an
          explicit URL.
        * If equal, prefer if any requirement is "pinned", i.e. contains
          operator ``===`` or ``==``.
        * If equal, calculate an approximate "depth" and resolve requirements
          closer to the user-specified requirements first. If the depth cannot
          by determined (eg: due to no matching parents), it is considered
          infinite.
        * Order user-specified requirements by the order they are specified.
        * If equal, prefers "non-free" requirements, i.e. contains at least one
          operator, such as ``>=`` or ``<``.
        * If equal, order alphabetically for consistency (helps debuggability).
        """
        try:
            next(iter(information[identifier]))
        except StopIteration:
            # There is no information for this identifier, so there's no known
            # candidates.
            has_information = False
        else:
            has_information = True

        if has_information:
            lookups = (r.get_candidate_lookup() for r, _ in information[identifier])
            candidate, ireqs = zip(*lookups)
        else:
            candidate, ireqs = None, ()

        operators = [
            specifier.operator
            for specifier_set in (ireq.specifier for ireq in ireqs if ireq)
            for specifier in specifier_set
        ]

        direct = candidate is not None
        pinned = any(op[:2] == "==" for op in operators)
        unfree = bool(operators)

        try:
            requested_order: Union[int, float] = self._user_requested[identifier]
        except KeyError:
            requested_order = math.inf
            if has_information:
                parent_depths = (
                    self._known_depths[parent.name] if parent is not None else 0.0
                    for _, parent in information[identifier]
                )
                inferred_depth = min(d for d in parent_depths) + 1.0
            else:
                inferred_depth = math.inf
        else:
            inferred_depth = 1.0
        self._known_depths[identifier] = inferred_depth

        requested_order = self._user_requested.get(identifier, math.inf)

        # Requires-Python has only one candidate and the check is basically
        # free, so we always do it first to avoid needless work if it fails.
        requires_python = identifier == REQUIRES_PYTHON_IDENTIFIER

        # Prefer the causes of backtracking on the assumption that the problem
        # resolving the dependency tree is related to the failures that caused
        # the backtracking
        backtrack_cause = self.is_backtrack_cause(identifier, backtrack_causes)

        return (
            not requires_python,
            not direct,
            not pinned,
            not backtrack_cause,
            inferred_depth,
            requested_order,
            not unfree,
            identifier,
        )

    def find_matches(
        self,
        identifier: str,
        requirements: Mapping[str, Iterator[Requirement]],
        incompatibilities: Mapping[str, Iterator[Candidate]],
    ) -> Iterable[Candidate]:
        def _eligible_for_upgrade(identifier: str) -> bool:
            """Are upgrades allowed for this project?

            This checks the upgrade strategy, and whether the project was one
            that the user specified in the command line, in order to decide
            whether we should upgrade if there's a newer version available.

            (Note that we don't need access to the `--upgrade` flag, because
            an upgrade strategy of "to-satisfy-only" means that `--upgrade`
            was not specified).
            """
            if self._upgrade_strategy == "eager":
                return True
            elif self._upgrade_strategy == "only-if-needed":
                user_order = _get_with_identifier(
                    self._user_requested,
                    identifier,
                    default=None,
                )
                return user_order is not None
            return False

        constraint = _get_with_identifier(
            self._constraints,
            identifier,
            default=Constraint.empty(),
        )
        return self._factory.find_candidates(
            identifier=identifier,
            requirements=requirements,
            constraint=constraint,
            prefers_installed=(not _eligible_for_upgrade(identifier)),
            incompatibilities=incompatibilities,
            is_satisfied_by=self.is_satisfied_by,
        )

    @lru_cache(maxsize=None)
    def is_satisfied_by(self, requirement: Requirement, candidate: Candidate) -> bool:
        return requirement.is_satisfied_by(candidate)

    def get_dependencies(self, candidate: Candidate) -> Sequence[Requirement]:
        with_requires = not self._ignore_dependencies
        return [r for r in candidate.iter_dependencies(with_requires) if r is not None]

    @staticmethod
    def is_backtrack_cause(
        identifier: str, backtrack_causes: Sequence["PreferenceInformation"]
    ) -> bool:
        for backtrack_cause in backtrack_causes:
            if identifier == backtrack_cause.requirement.name:
                return True
            if backtrack_cause.parent and identifier == backtrack_cause.parent.name:
                return True
        return False

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\select.py ===
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

from typing import List

from selenium.common.exceptions import NoSuchElementException, UnexpectedTagNameException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class Select:
    def __init__(self, webelement: WebElement) -> None:
        """Constructor. A check is made that the given element is, indeed, a
        SELECT tag. If it is not, then an UnexpectedTagNameException is thrown.

        :Args:
         - webelement - SELECT element to wrap

        Example:
            from selenium.webdriver.support.ui import Select \n
            Select(driver.find_element(By.TAG_NAME, "select")).select_by_index(2)
        """
        if webelement.tag_name.lower() != "select":
            raise UnexpectedTagNameException(f"Select only works on <select> elements, not on {webelement.tag_name}")
        self._el = webelement
        multi = self._el.get_dom_attribute("multiple")
        self.is_multiple = multi and multi != "false"

    @property
    def options(self) -> List[WebElement]:
        """Returns a list of all options belonging to this select tag."""
        return self._el.find_elements(By.TAG_NAME, "option")

    @property
    def all_selected_options(self) -> List[WebElement]:
        """Returns a list of all selected options belonging to this select
        tag."""
        return [opt for opt in self.options if opt.is_selected()]

    @property
    def first_selected_option(self) -> WebElement:
        """The first selected option in this select tag (or the currently
        selected option in a normal select)"""
        for opt in self.options:
            if opt.is_selected():
                return opt
        raise NoSuchElementException("No options are selected")

    def select_by_value(self, value: str) -> None:
        """Select all options that have a value matching the argument. That is,
        when given "foo" this would select an option like:

        <option value="foo">Bar</option>

        :Args:
         - value - The value to match against

        throws NoSuchElementException If there is no option with specified value in SELECT
        """
        css = f"option[value ={self._escape_string(value)}]"
        opts = self._el.find_elements(By.CSS_SELECTOR, css)
        matched = False
        for opt in opts:
            self._set_selected(opt)
            if not self.is_multiple:
                return
            matched = True
        if not matched:
            raise NoSuchElementException(f"Cannot locate option with value: {value}")

    def select_by_index(self, index: int) -> None:
        """Select the option at the given index. This is done by examining the
        "index" attribute of an element, and not merely by counting.

        :Args:
         - index - The option at this index will be selected

        throws NoSuchElementException If there is no option with specified index in SELECT
        """
        match = str(index)
        for opt in self.options:
            if opt.get_attribute("index") == match:
                self._set_selected(opt)
                return
        raise NoSuchElementException(f"Could not locate element with index {index}")

    def select_by_visible_text(self, text: str) -> None:
        """Select all options that display text matching the argument. That is,
        when given "Bar" this would select an option like:

         <option value="foo">Bar</option>

        :Args:
         - text - The visible text to match against

         throws NoSuchElementException If there is no option with specified text in SELECT
        """
        xpath = f".//option[normalize-space(.) = {self._escape_string(text)}]"
        opts = self._el.find_elements(By.XPATH, xpath)
        matched = False
        for opt in opts:
            if not self._has_css_property_and_visible(opt):
                raise NoSuchElementException(f"Invisible option with text: {text}")
            self._set_selected(opt)
            if not self.is_multiple:
                return
            matched = True

        if len(opts) == 0 and " " in text:
            sub_string_without_space = self._get_longest_token(text)
            if sub_string_without_space == "":
                candidates = self.options
            else:
                xpath = f".//option[contains(.,{self._escape_string(sub_string_without_space)})]"
                candidates = self._el.find_elements(By.XPATH, xpath)
            for candidate in candidates:
                if text == candidate.text:
                    if not self._has_css_property_and_visible(candidate):
                        raise NoSuchElementException(f"Invisible option with text: {text}")
                    self._set_selected(candidate)
                    if not self.is_multiple:
                        return
                    matched = True

        if not matched:
            raise NoSuchElementException(f"Could not locate element with visible text: {text}")

    def deselect_all(self) -> None:
        """Clear all selected entries.

        This is only valid when the SELECT supports multiple selections.
        throws NotImplementedError If the SELECT does not support
        multiple selections
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect all options of a multi-select")
        for opt in self.options:
            self._unset_selected(opt)

    def deselect_by_value(self, value: str) -> None:
        """Deselect all options that have a value matching the argument. That
        is, when given "foo" this would deselect an option like:

         <option value="foo">Bar</option>

        :Args:
         - value - The value to match against

         throws NoSuchElementException If there is no option with specified value in SELECT
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        matched = False
        css = f"option[value = {self._escape_string(value)}]"
        opts = self._el.find_elements(By.CSS_SELECTOR, css)
        for opt in opts:
            self._unset_selected(opt)
            matched = True
        if not matched:
            raise NoSuchElementException(f"Could not locate element with value: {value}")

    def deselect_by_index(self, index: int) -> None:
        """Deselect the option at the given index. This is done by examining
        the "index" attribute of an element, and not merely by counting.

        :Args:
         - index - The option at this index will be deselected

         throws NoSuchElementException If there is no option with specified index in SELECT
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        for opt in self.options:
            if opt.get_attribute("index") == str(index):
                self._unset_selected(opt)
                return
        raise NoSuchElementException(f"Could not locate element with index {index}")

    def deselect_by_visible_text(self, text: str) -> None:
        """Deselect all options that display text matching the argument. That
        is, when given "Bar" this would deselect an option like:

        <option value="foo">Bar</option>

        :Args:
         - text - The visible text to match against
        """
        if not self.is_multiple:
            raise NotImplementedError("You may only deselect options of a multi-select")
        matched = False
        xpath = f".//option[normalize-space(.) = {self._escape_string(text)}]"
        opts = self._el.find_elements(By.XPATH, xpath)
        for opt in opts:
            if not self._has_css_property_and_visible(opt):
                raise NoSuchElementException(f"Invisible option with text: {text}")
            self._unset_selected(opt)
            matched = True
        if not matched:
            raise NoSuchElementException(f"Could not locate element with visible text: {text}")

    def _set_selected(self, option) -> None:
        if not option.is_selected():
            if not option.is_enabled():
                raise NotImplementedError("You may not select a disabled option")
            option.click()

    def _unset_selected(self, option) -> None:
        if option.is_selected():
            option.click()

    def _escape_string(self, value: str) -> str:
        if '"' in value and "'" in value:
            substrings = value.split('"')
            result = ["concat("]
            for substring in substrings:
                result.append(f'"{substring}"')
                result.append(", '\"', ")
            result = result[0:-1]
            if value.endswith('"'):
                result.append(", '\"'")
            return "".join(result) + ")"

        if '"' in value:
            return f"'{value}'"

        return f'"{value}"'

    def _get_longest_token(self, value: str) -> str:
        items = value.split(" ")
        longest = ""
        for item in items:
            if len(item) > len(longest):
                longest = item
        return longest

    def _has_css_property_and_visible(self, option) -> bool:
        css_value_candidates = ["hidden", "none", "0", "0.0"]
        css_property_candidates = ["visibility", "display", "opacity"]

        for property in css_property_candidates:
            css_value = option.value_of_css_property(property)
            if css_value in css_value_candidates:
                return False
        return True