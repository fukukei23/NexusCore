
# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\_n_a_m_e.py ===
# -*- coding: utf-8 -*-
from fontTools.misc import sstruct
from fontTools.misc.textTools import (
    bytechr,
    byteord,
    bytesjoin,
    strjoin,
    tobytes,
    tostr,
    safeEval,
)
from fontTools.misc.encodingTools import getEncoding
from fontTools.ttLib import newTable
from fontTools.ttLib.ttVisitor import TTVisitor
from fontTools import ttLib
import fontTools.ttLib.tables.otTables as otTables
from fontTools.ttLib.tables import C_P_A_L_
from . import DefaultTable
import struct
import logging


log = logging.getLogger(__name__)

nameRecordFormat = """
		>	# big endian
		platformID:	H
		platEncID:	H
		langID:		H
		nameID:		H
		length:		H
		offset:		H
"""

nameRecordSize = sstruct.calcsize(nameRecordFormat)


class table__n_a_m_e(DefaultTable.DefaultTable):
    """Naming table

    The ``name`` table is used to store a variety of strings that can be
    associated with user-facing font information. Records in the ``name``
    table can be tagged with language tags to support multilingual naming
    and can support platform-specific character-encoding variants.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/name
    """

    dependencies = ["ltag"]

    def __init__(self, tag=None):
        super().__init__(tag)
        self.names = []

    def decompile(self, data, ttFont):
        format, n, stringOffset = struct.unpack(b">HHH", data[:6])
        expectedStringOffset = 6 + n * nameRecordSize
        if stringOffset != expectedStringOffset:
            log.error(
                "'name' table stringOffset incorrect. Expected: %s; Actual: %s",
                expectedStringOffset,
                stringOffset,
            )
        stringData = data[stringOffset:]
        data = data[6:]
        self.names = []
        for i in range(n):
            if len(data) < 12:
                log.error("skipping malformed name record #%d", i)
                continue
            name, data = sstruct.unpack2(nameRecordFormat, data, NameRecord())
            name.string = stringData[name.offset : name.offset + name.length]
            if name.offset + name.length > len(stringData):
                log.error("skipping malformed name record #%d", i)
                continue
            assert len(name.string) == name.length
            # if (name.platEncID, name.platformID) in ((0, 0), (1, 3)):
            # 	if len(name.string) % 2:
            # 		print "2-byte string doesn't have even length!"
            # 		print name.__dict__
            del name.offset, name.length
            self.names.append(name)

    def compile(self, ttFont):
        names = self.names
        names.sort()  # sort according to the spec; see NameRecord.__lt__()
        stringData = b""
        format = 0
        n = len(names)
        stringOffset = 6 + n * sstruct.calcsize(nameRecordFormat)
        data = struct.pack(b">HHH", format, n, stringOffset)
        lastoffset = 0
        done = {}  # remember the data so we can reuse the "pointers"
        for name in names:
            string = name.toBytes()
            if string in done:
                name.offset, name.length = done[string]
            else:
                name.offset, name.length = done[string] = len(stringData), len(string)
                stringData = bytesjoin([stringData, string])
            data = data + sstruct.pack(nameRecordFormat, name)
        return data + stringData

    def toXML(self, writer, ttFont):
        for name in self.names:
            name.toXML(writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name != "namerecord":
            return  # ignore unknown tags
        name = NameRecord()
        self.names.append(name)
        name.fromXML(name, attrs, content, ttFont)

    def getName(self, nameID, platformID, platEncID, langID=None):
        for namerecord in self.names:
            if (
                namerecord.nameID == nameID
                and namerecord.platformID == platformID
                and namerecord.platEncID == platEncID
            ):
                if langID is None or namerecord.langID == langID:
                    return namerecord
        return None  # not found

    def getDebugName(self, nameID):
        englishName = someName = None
        for name in self.names:
            if name.nameID != nameID:
                continue
            try:
                unistr = name.toUnicode()
            except UnicodeDecodeError:
                continue

            someName = unistr
            if (name.platformID, name.langID) in ((1, 0), (3, 0x409)):
                englishName = unistr
                break
        if englishName:
            return englishName
        elif someName:
            return someName
        else:
            return None

    def getFirstDebugName(self, nameIDs):
        for nameID in nameIDs:
            name = self.getDebugName(nameID)
            if name is not None:
                return name
        return None

    def getBestFamilyName(self):
        # 21 = WWS Family Name
        # 16 = Typographic Family Name
        # 1 = Family Name
        return self.getFirstDebugName((21, 16, 1))

    def getBestSubFamilyName(self):
        # 22 = WWS SubFamily Name
        # 17 = Typographic SubFamily Name
        # 2 = SubFamily Name
        return self.getFirstDebugName((22, 17, 2))

    def getBestFullName(self):
        # 4 = Full Name
        # 6 = PostScript Name
        for nameIDs in ((21, 22), (16, 17), (1, 2), (4,), (6,)):
            if len(nameIDs) == 2:
                name_fam = self.getDebugName(nameIDs[0])
                name_subfam = self.getDebugName(nameIDs[1])
                if None in [name_fam, name_subfam]:
                    continue  # if any is None, skip
                name = f"{name_fam} {name_subfam}"
                if name_subfam.lower() == "regular":
                    name = f"{name_fam}"
                return name
            else:
                name = self.getDebugName(nameIDs[0])
                if name is not None:
                    return name
        return None

    def setName(self, string, nameID, platformID, platEncID, langID):
        """Set the 'string' for the name record identified by 'nameID', 'platformID',
        'platEncID' and 'langID'. If a record with that nameID doesn't exist, create it
        and append to the name table.

        'string' can be of type `str` (`unicode` in PY2) or `bytes`. In the latter case,
        it is assumed to be already encoded with the correct plaform-specific encoding
        identified by the (platformID, platEncID, langID) triplet. A warning is issued
        to prevent unexpected results.
        """
        if not isinstance(string, str):
            if isinstance(string, bytes):
                log.warning(
                    "name string is bytes, ensure it's correctly encoded: %r", string
                )
            else:
                raise TypeError(
                    "expected unicode or bytes, found %s: %r"
                    % (type(string).__name__, string)
                )
        namerecord = self.getName(nameID, platformID, platEncID, langID)
        if namerecord:
            namerecord.string = string
        else:
            self.names.append(makeName(string, nameID, platformID, platEncID, langID))

    def removeNames(self, nameID=None, platformID=None, platEncID=None, langID=None):
        """Remove any name records identified by the given combination of 'nameID',
        'platformID', 'platEncID' and 'langID'.
        """
        args = {
            argName: argValue
            for argName, argValue in (
                ("nameID", nameID),
                ("platformID", platformID),
                ("platEncID", platEncID),
                ("langID", langID),
            )
            if argValue is not None
        }
        if not args:
            # no arguments, nothing to do
            return
        self.names = [
            rec
            for rec in self.names
            if any(
                argValue != getattr(rec, argName) for argName, argValue in args.items()
            )
        ]

    @staticmethod
    def removeUnusedNames(ttFont):
        """Remove any name records which are not in NameID range 0-255 and not utilized
        within the font itself."""
        visitor = NameRecordVisitor()
        visitor.visit(ttFont)
        toDelete = set()
        for record in ttFont["name"].names:
            # Name IDs 26 to 255, inclusive, are reserved for future standard names.
            # https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
            if record.nameID < 256:
                continue
            if record.nameID not in visitor.seen:
                toDelete.add(record.nameID)

        for nameID in toDelete:
            ttFont["name"].removeNames(nameID)
        return toDelete

    def _findUnusedNameID(self, minNameID=256):
        """Finds an unused name id.

        The nameID is assigned in the range between 'minNameID' and 32767 (inclusive),
        following the last nameID in the name table.
        """
        names = self.names
        nameID = 1 + max([n.nameID for n in names] + [minNameID - 1])
        if nameID > 32767:
            raise ValueError("nameID must be less than 32768")
        return nameID

    def findMultilingualName(
        self, names, windows=True, mac=True, minNameID=0, ttFont=None
    ):
        """Return the name ID of an existing multilingual name that
        matches the 'names' dictionary, or None if not found.

        'names' is a dictionary with the name in multiple languages,
        such as {'en': 'Pale', 'de': 'Blaß', 'de-CH': 'Blass'}.
        The keys can be arbitrary IETF BCP 47 language codes;
        the values are Unicode strings.

        If 'windows' is True, the returned name ID is guaranteed
        exist for all requested languages for platformID=3 and
        platEncID=1.
        If 'mac' is True, the returned name ID is guaranteed to exist
        for all requested languages for platformID=1 and platEncID=0.

        The returned name ID will not be less than the 'minNameID'
        argument.
        """
        # Gather the set of requested
        #   (string, platformID, platEncID, langID)
        # tuples
        reqNameSet = set()
        for lang, name in sorted(names.items()):
            if windows:
                windowsName = _makeWindowsName(name, None, lang)
                if windowsName is not None:
                    reqNameSet.add(
                        (
                            windowsName.string,
                            windowsName.platformID,
                            windowsName.platEncID,
                            windowsName.langID,
                        )
                    )
            if mac:
                macName = _makeMacName(name, None, lang, ttFont)
                if macName is not None:
                    reqNameSet.add(
                        (
                            macName.string,
                            macName.platformID,
                            macName.platEncID,
                            macName.langID,
                        )
                    )

        # Collect matching name IDs
        matchingNames = dict()
        for name in self.names:
            try:
                key = (name.toUnicode(), name.platformID, name.platEncID, name.langID)
            except UnicodeDecodeError:
                continue
            if key in reqNameSet and name.nameID >= minNameID:
                nameSet = matchingNames.setdefault(name.nameID, set())
                nameSet.add(key)

        # Return the first name ID that defines all requested strings
        for nameID, nameSet in sorted(matchingNames.items()):
            if nameSet == reqNameSet:
                return nameID

        return None  # not found

    def addMultilingualName(
        self, names, ttFont=None, nameID=None, windows=True, mac=True, minNameID=0
    ):
        """Add a multilingual name, returning its name ID

        'names' is a dictionary with the name in multiple languages,
        such as {'en': 'Pale', 'de': 'Blaß', 'de-CH': 'Blass'}.
        The keys can be arbitrary IETF BCP 47 language codes;
        the values are Unicode strings.

        'ttFont' is the TTFont to which the names are added, or None.
        If present, the font's 'ltag' table can get populated
        to store exotic language codes, which allows encoding
        names that otherwise cannot get encoded at all.

        'nameID' is the name ID to be used, or None to let the library
        find an existing set of name records that match, or pick an
        unused name ID.

        If 'windows' is True, a platformID=3 name record will be added.
        If 'mac' is True, a platformID=1 name record will be added.

        If the 'nameID' argument is None, the created nameID will not
        be less than the 'minNameID' argument.
        """
        if nameID is None:
            # Reuse nameID if possible
            nameID = self.findMultilingualName(
                names, windows=windows, mac=mac, minNameID=minNameID, ttFont=ttFont
            )
            if nameID is not None:
                return nameID
            nameID = self._findUnusedNameID()
        # TODO: Should minimize BCP 47 language codes.
        # https://github.com/fonttools/fonttools/issues/930
        for lang, name in sorted(names.items()):
            if windows:
                windowsName = _makeWindowsName(name, nameID, lang)
                if windowsName is not None:
                    self.names.append(windowsName)
                else:
                    # We cannot not make a Windows name: make sure we add a
                    # Mac name as a fallback. This can happen for exotic
                    # BCP47 language tags that have no Windows language code.
                    mac = True
            if mac:
                macName = _makeMacName(name, nameID, lang, ttFont)
                if macName is not None:
                    self.names.append(macName)
        return nameID

    def addName(self, string, platforms=((1, 0, 0), (3, 1, 0x409)), minNameID=255):
        """Add a new name record containing 'string' for each (platformID, platEncID,
        langID) tuple specified in the 'platforms' list.

        The nameID is assigned in the range between 'minNameID'+1 and 32767 (inclusive),
        following the last nameID in the name table.
        If no 'platforms' are specified, two English name records are added, one for the
        Macintosh (platformID=0), and one for the Windows platform (3).

        The 'string' must be a Unicode string, so it can be encoded with different,
        platform-specific encodings.

        Return the new nameID.
        """
        assert (
            len(platforms) > 0
        ), "'platforms' must contain at least one (platformID, platEncID, langID) tuple"
        if not isinstance(string, str):
            raise TypeError(
                "expected str, found %s: %r" % (type(string).__name__, string)
            )
        nameID = self._findUnusedNameID(minNameID + 1)
        for platformID, platEncID, langID in platforms:
            self.names.append(makeName(string, nameID, platformID, platEncID, langID))
        return nameID


def makeName(string, nameID, platformID, platEncID, langID):
    name = NameRecord()
    name.string, name.nameID, name.platformID, name.platEncID, name.langID = (
        string,
        nameID,
        platformID,
        platEncID,
        langID,
    )
    return name


def _makeWindowsName(name, nameID, language):
    """Create a NameRecord for the Microsoft Windows platform

    'language' is an arbitrary IETF BCP 47 language identifier such
    as 'en', 'de-CH', 'de-AT-1901', or 'fa-Latn'. If Microsoft Windows
    does not support the desired language, the result will be None.
    Future versions of fonttools might return a NameRecord for the
    OpenType 'name' table format 1, but this is not implemented yet.
    """
    langID = _WINDOWS_LANGUAGE_CODES.get(language.lower())
    if langID is not None:
        return makeName(name, nameID, 3, 1, langID)
    else:
        log.warning(
            "cannot add Windows name in language %s "
            "because fonttools does not yet support "
            "name table format 1" % language
        )
        return None


def _makeMacName(name, nameID, language, font=None):
    """Create a NameRecord for Apple platforms

    'language' is an arbitrary IETF BCP 47 language identifier such
    as 'en', 'de-CH', 'de-AT-1901', or 'fa-Latn'. When possible, we
    create a Macintosh NameRecord that is understood by old applications
    (platform ID 1 and an old-style Macintosh language enum). If this
    is not possible, we create a Unicode NameRecord (platform ID 0)
    whose language points to the font’s 'ltag' table. The latter
    can encode any string in any language, but legacy applications
    might not recognize the format (in which case they will ignore
    those names).

    'font' should be the TTFont for which you want to create a name.
    If 'font' is None, we only return NameRecords for legacy Macintosh;
    in that case, the result will be None for names that need to
    be encoded with an 'ltag' table.

    See the section “The language identifier” in Apple’s specification:
    https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6name.html
    """
    macLang = _MAC_LANGUAGE_CODES.get(language.lower())
    macScript = _MAC_LANGUAGE_TO_SCRIPT.get(macLang)
    if macLang is not None and macScript is not None:
        encoding = getEncoding(1, macScript, macLang, default="ascii")
        # Check if we can actually encode this name. If we can't,
        # for example because we have no support for the legacy
        # encoding, or because the name string contains Unicode
        # characters that the legacy encoding cannot represent,
        # we fall back to encoding the name in Unicode and put
        # the language tag into the ltag table.
        try:
            _ = tobytes(name, encoding, errors="strict")
            return makeName(name, nameID, 1, macScript, macLang)
        except UnicodeEncodeError:
            pass
    if font is not None:
        ltag = font.tables.get("ltag")
        if ltag is None:
            ltag = font["ltag"] = newTable("ltag")
        # 0 = Unicode; 4 = “Unicode 2.0 or later semantics (non-BMP characters allowed)”
        # “The preferred platform-specific code for Unicode would be 3 or 4.”
        # https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6name.html
        return makeName(name, nameID, 0, 4, ltag.addTag(language))
    else:
        log.warning(
            "cannot store language %s into 'ltag' table "
            "without having access to the TTFont object" % language
        )
        return None


class NameRecord(object):
    def getEncoding(self, default="ascii"):
        """Returns the Python encoding name for this name entry based on its platformID,
        platEncID, and langID.  If encoding for these values is not known, by default
        'ascii' is returned.  That can be overriden by passing a value to the default
        argument.
        """
        return getEncoding(self.platformID, self.platEncID, self.langID, default)

    def encodingIsUnicodeCompatible(self):
        return self.getEncoding(None) in ["utf_16_be", "ucs2be", "ascii", "latin1"]

    def __str__(self):
        return self.toStr(errors="backslashreplace")

    def isUnicode(self):
        return self.platformID == 0 or (
            self.platformID == 3 and self.platEncID in [0, 1, 10]
        )

    def toUnicode(self, errors="strict"):
        """
        If self.string is a Unicode string, return it; otherwise try decoding the
        bytes in self.string to a Unicode string using the encoding of this
        entry as returned by self.getEncoding(); Note that  self.getEncoding()
        returns 'ascii' if the encoding is unknown to the library.

        Certain heuristics are performed to recover data from bytes that are
        ill-formed in the chosen encoding, or that otherwise look misencoded
        (mostly around bad UTF-16BE encoded bytes, or bytes that look like UTF-16BE
        but marked otherwise).  If the bytes are ill-formed and the heuristics fail,
        the error is handled according to the errors parameter to this function, which is
        passed to the underlying decode() function; by default it throws a
        UnicodeDecodeError exception.

        Note: The mentioned heuristics mean that roundtripping a font to XML and back
        to binary might recover some misencoded data whereas just loading the font
        and saving it back will not change them.
        """

        def isascii(b):
            return (b >= 0x20 and b <= 0x7E) or b in [0x09, 0x0A, 0x0D]

        encoding = self.getEncoding()
        string = self.string

        if (
            isinstance(string, bytes)
            and encoding == "utf_16_be"
            and len(string) % 2 == 1
        ):
            # Recover badly encoded UTF-16 strings that have an odd number of bytes:
            # - If the last byte is zero, drop it.  Otherwise,
            # - If all the odd bytes are zero and all the even bytes are ASCII,
            #   prepend one zero byte.  Otherwise,
            # - If first byte is zero and all other bytes are ASCII, insert zero
            #   bytes between consecutive ASCII bytes.
            #
            # (Yes, I've seen all of these in the wild... sigh)
            if byteord(string[-1]) == 0:
                string = string[:-1]
            elif all(
                byteord(b) == 0 if i % 2 else isascii(byteord(b))
                for i, b in enumerate(string)
            ):
                string = b"\0" + string
            elif byteord(string[0]) == 0 and all(
                isascii(byteord(b)) for b in string[1:]
            ):
                string = bytesjoin(b"\0" + bytechr(byteord(b)) for b in string[1:])

        string = tostr(string, encoding=encoding, errors=errors)

        # If decoded strings still looks like UTF-16BE, it suggests a double-encoding.
        # Fix it up.
        if all(
            ord(c) == 0 if i % 2 == 0 else isascii(ord(c)) for i, c in enumerate(string)
        ):
            # If string claims to be Mac encoding, but looks like UTF-16BE with ASCII text,
            # narrow it down.
            string = "".join(c for c in string[1::2])

        return string

    def toBytes(self, errors="strict"):
        """If self.string is a bytes object, return it; otherwise try encoding
        the Unicode string in self.string to bytes using the encoding of this
        entry as returned by self.getEncoding(); Note that self.getEncoding()
        returns 'ascii' if the encoding is unknown to the library.

        If the Unicode string cannot be encoded to bytes in the chosen encoding,
        the error is handled according to the errors parameter to this function,
        which is passed to the underlying encode() function; by default it throws a
        UnicodeEncodeError exception.
        """
        return tobytes(self.string, encoding=self.getEncoding(), errors=errors)

    toStr = toUnicode

    def toXML(self, writer, ttFont):
        try:
            unistr = self.toUnicode()
        except UnicodeDecodeError:
            unistr = None
        attrs = [
            ("nameID", self.nameID),
            ("platformID", self.platformID),
            ("platEncID", self.platEncID),
            ("langID", hex(self.langID)),
        ]

        if unistr is None or not self.encodingIsUnicodeCompatible():
            attrs.append(("unicode", unistr is not None))

        writer.begintag("namerecord", attrs)
        writer.newline()
        if unistr is not None:
            writer.write(unistr)
        else:
            writer.write8bit(self.string)
        writer.newline()
        writer.endtag("namerecord")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.nameID = safeEval(attrs["nameID"])
        self.platformID = safeEval(attrs["platformID"])
        self.platEncID = safeEval(attrs["platEncID"])
        self.langID = safeEval(attrs["langID"])
        s = strjoin(content).strip()
        encoding = self.getEncoding()
        if self.encodingIsUnicodeCompatible() or safeEval(
            attrs.get("unicode", "False")
        ):
            self.string = s.encode(encoding)
        else:
            # This is the inverse of write8bit...
            self.string = s.encode("latin1")

    def __lt__(self, other):
        if type(self) != type(other):
            return NotImplemented

        try:
            selfTuple = (
                self.platformID,
                self.platEncID,
                self.langID,
                self.nameID,
            )
            otherTuple = (
                other.platformID,
                other.platEncID,
                other.langID,
                other.nameID,
            )
        except AttributeError:
            # This can only happen for
            # 1) an object that is not a NameRecord, or
            # 2) an unlikely incomplete NameRecord object which has not been
            #    fully populated
            return NotImplemented

        try:
            # Include the actual NameRecord string in the comparison tuples
            selfTuple = selfTuple + (self.toBytes(),)
            otherTuple = otherTuple + (other.toBytes(),)
        except UnicodeEncodeError as e:
            # toBytes caused an encoding error in either of the two, so content
            # to sorting based on IDs only
            log.error("NameRecord sorting failed to encode: %s" % e)

        # Implemented so that list.sort() sorts according to the spec by using
        # the order of the tuple items and their comparison
        return selfTuple < otherTuple

    def __repr__(self):
        return "<NameRecord NameID=%d; PlatformID=%d; LanguageID=%d>" % (
            self.nameID,
            self.platformID,
            self.langID,
        )


# Windows language ID → IETF BCP-47 language tag
#
# While Microsoft indicates a region/country for all its language
# IDs, we follow Unicode practice by omitting “most likely subtags”
# as per Unicode CLDR. For example, English is simply “en” and not
# “en-Latn” because according to Unicode, the default script
# for English is Latin.
#
# http://www.unicode.org/cldr/charts/latest/supplemental/likely_subtags.html
# http://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
_WINDOWS_LANGUAGES = {
    0x0436: "af",
    0x041C: "sq",
    0x0484: "gsw",
    0x045E: "am",
    0x1401: "ar-DZ",
    0x3C01: "ar-BH",
    0x0C01: "ar",
    0x0801: "ar-IQ",
    0x2C01: "ar-JO",
    0x3401: "ar-KW",
    0x3001: "ar-LB",
    0x1001: "ar-LY",
    0x1801: "ary",
    0x2001: "ar-OM",
    0x4001: "ar-QA",
    0x0401: "ar-SA",
    0x2801: "ar-SY",
    0x1C01: "aeb",
    0x3801: "ar-AE",
    0x2401: "ar-YE",
    0x042B: "hy",
    0x044D: "as",
    0x082C: "az-Cyrl",
    0x042C: "az",
    0x046D: "ba",
    0x042D: "eu",
    0x0423: "be",
    0x0845: "bn",
    0x0445: "bn-IN",
    0x201A: "bs-Cyrl",
    0x141A: "bs",
    0x047E: "br",
    0x0402: "bg",
    0x0403: "ca",
    0x0C04: "zh-HK",
    0x1404: "zh-MO",
    0x0804: "zh",
    0x1004: "zh-SG",
    0x0404: "zh-TW",
    0x0483: "co",
    0x041A: "hr",
    0x101A: "hr-BA",
    0x0405: "cs",
    0x0406: "da",
    0x048C: "prs",
    0x0465: "dv",
    0x0813: "nl-BE",
    0x0413: "nl",
    0x0C09: "en-AU",
    0x2809: "en-BZ",
    0x1009: "en-CA",
    0x2409: "en-029",
    0x4009: "en-IN",
    0x1809: "en-IE",
    0x2009: "en-JM",
    0x4409: "en-MY",
    0x1409: "en-NZ",
    0x3409: "en-PH",
    0x4809: "en-SG",
    0x1C09: "en-ZA",
    0x2C09: "en-TT",
    0x0809: "en-GB",
    0x0409: "en",
    0x3009: "en-ZW",
    0x0425: "et",
    0x0438: "fo",
    0x0464: "fil",
    0x040B: "fi",
    0x080C: "fr-BE",
    0x0C0C: "fr-CA",
    0x040C: "fr",
    0x140C: "fr-LU",
    0x180C: "fr-MC",
    0x100C: "fr-CH",
    0x0462: "fy",
    0x0456: "gl",
    0x0437: "ka",
    0x0C07: "de-AT",
    0x0407: "de",
    0x1407: "de-LI",
    0x1007: "de-LU",
    0x0807: "de-CH",
    0x0408: "el",
    0x046F: "kl",
    0x0447: "gu",
    0x0468: "ha",
    0x040D: "he",
    0x0439: "hi",
    0x040E: "hu",
    0x040F: "is",
    0x0470: "ig",
    0x0421: "id",
    0x045D: "iu",
    0x085D: "iu-Latn",
    0x083C: "ga",
    0x0434: "xh",
    0x0435: "zu",
    0x0410: "it",
    0x0810: "it-CH",
    0x0411: "ja",
    0x044B: "kn",
    0x043F: "kk",
    0x0453: "km",
    0x0486: "quc",
    0x0487: "rw",
    0x0441: "sw",
    0x0457: "kok",
    0x0412: "ko",
    0x0440: "ky",
    0x0454: "lo",
    0x0426: "lv",
    0x0427: "lt",
    0x082E: "dsb",
    0x046E: "lb",
    0x042F: "mk",
    0x083E: "ms-BN",
    0x043E: "ms",
    0x044C: "ml",
    0x043A: "mt",
    0x0481: "mi",
    0x047A: "arn",
    0x044E: "mr",
    0x047C: "moh",
    0x0450: "mn",
    0x0850: "mn-CN",
    0x0461: "ne",
    0x0414: "nb",
    0x0814: "nn",
    0x0482: "oc",
    0x0448: "or",
    0x0463: "ps",
    0x0415: "pl",
    0x0416: "pt",
    0x0816: "pt-PT",
    0x0446: "pa",
    0x046B: "qu-BO",
    0x086B: "qu-EC",
    0x0C6B: "qu",
    0x0418: "ro",
    0x0417: "rm",
    0x0419: "ru",
    0x243B: "smn",
    0x103B: "smj-NO",
    0x143B: "smj",
    0x0C3B: "se-FI",
    0x043B: "se",
    0x083B: "se-SE",
    0x203B: "sms",
    0x183B: "sma-NO",
    0x1C3B: "sms",
    0x044F: "sa",
    0x1C1A: "sr-Cyrl-BA",
    0x0C1A: "sr",
    0x181A: "sr-Latn-BA",
    0x081A: "sr-Latn",
    0x046C: "nso",
    0x0432: "tn",
    0x045B: "si",
    0x041B: "sk",
    0x0424: "sl",
    0x2C0A: "es-AR",
    0x400A: "es-BO",
    0x340A: "es-CL",
    0x240A: "es-CO",
    0x140A: "es-CR",
    0x1C0A: "es-DO",
    0x300A: "es-EC",
    0x440A: "es-SV",
    0x100A: "es-GT",
    0x480A: "es-HN",
    0x080A: "es-MX",
    0x4C0A: "es-NI",
    0x180A: "es-PA",
    0x3C0A: "es-PY",
    0x280A: "es-PE",
    0x500A: "es-PR",
    # Microsoft has defined two different language codes for
    # “Spanish with modern sorting” and “Spanish with traditional
    # sorting”. This makes sense for collation APIs, and it would be
    # possible to express this in BCP 47 language tags via Unicode
    # extensions (eg., “es-u-co-trad” is “Spanish with traditional
    # sorting”). However, for storing names in fonts, this distinction
    # does not make sense, so we use “es” in both cases.
    0x0C0A: "es",
    0x040A: "es",
    0x540A: "es-US",
    0x380A: "es-UY",
    0x200A: "es-VE",
    0x081D: "sv-FI",
    0x041D: "sv",
    0x045A: "syr",
    0x0428: "tg",
    0x085F: "tzm",
    0x0449: "ta",
    0x0444: "tt",
    0x044A: "te",
    0x041E: "th",
    0x0451: "bo",
    0x041F: "tr",
    0x0442: "tk",
    0x0480: "ug",
    0x0422: "uk",
    0x042E: "hsb",
    0x0420: "ur",
    0x0843: "uz-Cyrl",
    0x0443: "uz",
    0x042A: "vi",
    0x0452: "cy",
    0x0488: "wo",
    0x0485: "sah",
    0x0478: "ii",
    0x046A: "yo",
}


_MAC_LANGUAGES = {
    0: "en",
    1: "fr",
    2: "de",
    3: "it",
    4: "nl",
    5: "sv",
    6: "es",
    7: "da",
    8: "pt",
    9: "no",
    10: "he",
    11: "ja",
    12: "ar",
    13: "fi",
    14: "el",
    15: "is",
    16: "mt",
    17: "tr",
    18: "hr",
    19: "zh-Hant",
    20: "ur",
    21: "hi",
    22: "th",
    23: "ko",
    24: "lt",
    25: "pl",
    26: "hu",
    27: "es",
    28: "lv",
    29: "se",
    30: "fo",
    31: "fa",
    32: "ru",
    33: "zh",
    34: "nl-BE",
    35: "ga",
    36: "sq",
    37: "ro",
    38: "cz",
    39: "sk",
    40: "sl",
    41: "yi",
    42: "sr",
    43: "mk",
    44: "bg",
    45: "uk",
    46: "be",
    47: "uz",
    48: "kk",
    49: "az-Cyrl",
    50: "az-Arab",
    51: "hy",
    52: "ka",
    53: "mo",
    54: "ky",
    55: "tg",
    56: "tk",
    57: "mn-CN",
    58: "mn",
    59: "ps",
    60: "ks",
    61: "ku",
    62: "sd",
    63: "bo",
    64: "ne",
    65: "sa",
    66: "mr",
    67: "bn",
    68: "as",
    69: "gu",
    70: "pa",
    71: "or",
    72: "ml",
    73: "kn",
    74: "ta",
    75: "te",
    76: "si",
    77: "my",
    78: "km",
    79: "lo",
    80: "vi",
    81: "id",
    82: "tl",
    83: "ms",
    84: "ms-Arab",
    85: "am",
    86: "ti",
    87: "om",
    88: "so",
    89: "sw",
    90: "rw",
    91: "rn",
    92: "ny",
    93: "mg",
    94: "eo",
    128: "cy",
    129: "eu",
    130: "ca",
    131: "la",
    132: "qu",
    133: "gn",
    134: "ay",
    135: "tt",
    136: "ug",
    137: "dz",
    138: "jv",
    139: "su",
    140: "gl",
    141: "af",
    142: "br",
    143: "iu",
    144: "gd",
    145: "gv",
    146: "ga",
    147: "to",
    148: "el-polyton",
    149: "kl",
    150: "az",
    151: "nn",
}


_WINDOWS_LANGUAGE_CODES = {
    lang.lower(): code for code, lang in _WINDOWS_LANGUAGES.items()
}
_MAC_LANGUAGE_CODES = {lang.lower(): code for code, lang in _MAC_LANGUAGES.items()}


# MacOS language ID → MacOS script ID
#
# Note that the script ID is not sufficient to determine what encoding
# to use in TrueType files. For some languages, MacOS used a modification
# of a mainstream script. For example, an Icelandic name would be stored
# with smRoman in the TrueType naming table, but the actual encoding
# is a special Icelandic version of the normal Macintosh Roman encoding.
# As another example, Inuktitut uses an 8-bit encoding for Canadian Aboriginal
# Syllables but MacOS had run out of available script codes, so this was
# done as a (pretty radical) “modification” of Ethiopic.
#
# http://unicode.org/Public/MAPPINGS/VENDORS/APPLE/Readme.txt
_MAC_LANGUAGE_TO_SCRIPT = {
    0: 0,  # langEnglish → smRoman
    1: 0,  # langFrench → smRoman
    2: 0,  # langGerman → smRoman
    3: 0,  # langItalian → smRoman
    4: 0,  # langDutch → smRoman
    5: 0,  # langSwedish → smRoman
    6: 0,  # langSpanish → smRoman
    7: 0,  # langDanish → smRoman
    8: 0,  # langPortuguese → smRoman
    9: 0,  # langNorwegian → smRoman
    10: 5,  # langHebrew → smHebrew
    11: 1,  # langJapanese → smJapanese
    12: 4,  # langArabic → smArabic
    13: 0,  # langFinnish → smRoman
    14: 6,  # langGreek → smGreek
    15: 0,  # langIcelandic → smRoman (modified)
    16: 0,  # langMaltese → smRoman
    17: 0,  # langTurkish → smRoman (modified)
    18: 0,  # langCroatian → smRoman (modified)
    19: 2,  # langTradChinese → smTradChinese
    20: 4,  # langUrdu → smArabic
    21: 9,  # langHindi → smDevanagari
    22: 21,  # langThai → smThai
    23: 3,  # langKorean → smKorean
    24: 29,  # langLithuanian → smCentralEuroRoman
    25: 29,  # langPolish → smCentralEuroRoman
    26: 29,  # langHungarian → smCentralEuroRoman
    27: 29,  # langEstonian → smCentralEuroRoman
    28: 29,  # langLatvian → smCentralEuroRoman
    29: 0,  # langSami → smRoman
    30: 0,  # langFaroese → smRoman (modified)
    31: 4,  # langFarsi → smArabic (modified)
    32: 7,  # langRussian → smCyrillic
    33: 25,  # langSimpChinese → smSimpChinese
    34: 0,  # langFlemish → smRoman
    35: 0,  # langIrishGaelic → smRoman (modified)
    36: 0,  # langAlbanian → smRoman
    37: 0,  # langRomanian → smRoman (modified)
    38: 29,  # langCzech → smCentralEuroRoman
    39: 29,  # langSlovak → smCentralEuroRoman
    40: 0,  # langSlovenian → smRoman (modified)
    41: 5,  # langYiddish → smHebrew
    42: 7,  # langSerbian → smCyrillic
    43: 7,  # langMacedonian → smCyrillic
    44: 7,  # langBulgarian → smCyrillic
    45: 7,  # langUkrainian → smCyrillic (modified)
    46: 7,  # langByelorussian → smCyrillic
    47: 7,  # langUzbek → smCyrillic
    48: 7,  # langKazakh → smCyrillic
    49: 7,  # langAzerbaijani → smCyrillic
    50: 4,  # langAzerbaijanAr → smArabic
    51: 24,  # langArmenian → smArmenian
    52: 23,  # langGeorgian → smGeorgian
    53: 7,  # langMoldavian → smCyrillic
    54: 7,  # langKirghiz → smCyrillic
    55: 7,  # langTajiki → smCyrillic
    56: 7,  # langTurkmen → smCyrillic
    57: 27,  # langMongolian → smMongolian
    58: 7,  # langMongolianCyr → smCyrillic
    59: 4,  # langPashto → smArabic
    60: 4,  # langKurdish → smArabic
    61: 4,  # langKashmiri → smArabic
    62: 4,  # langSindhi → smArabic
    63: 26,  # langTibetan → smTibetan
    64: 9,  # langNepali → smDevanagari
    65: 9,  # langSanskrit → smDevanagari
    66: 9,  # langMarathi → smDevanagari
    67: 13,  # langBengali → smBengali
    68: 13,  # langAssamese → smBengali
    69: 11,  # langGujarati → smGujarati
    70: 10,  # langPunjabi → smGurmukhi
    71: 12,  # langOriya → smOriya
    72: 17,  # langMalayalam → smMalayalam
    73: 16,  # langKannada → smKannada
    74: 14,  # langTamil → smTamil
    75: 15,  # langTelugu → smTelugu
    76: 18,  # langSinhalese → smSinhalese
    77: 19,  # langBurmese → smBurmese
    78: 20,  # langKhmer → smKhmer
    79: 22,  # langLao → smLao
    80: 30,  # langVietnamese → smVietnamese
    81: 0,  # langIndonesian → smRoman
    82: 0,  # langTagalog → smRoman
    83: 0,  # langMalayRoman → smRoman
    84: 4,  # langMalayArabic → smArabic
    85: 28,  # langAmharic → smEthiopic
    86: 28,  # langTigrinya → smEthiopic
    87: 28,  # langOromo → smEthiopic
    88: 0,  # langSomali → smRoman
    89: 0,  # langSwahili → smRoman
    90: 0,  # langKinyarwanda → smRoman
    91: 0,  # langRundi → smRoman
    92: 0,  # langNyanja → smRoman
    93: 0,  # langMalagasy → smRoman
    94: 0,  # langEsperanto → smRoman
    128: 0,  # langWelsh → smRoman (modified)
    129: 0,  # langBasque → smRoman
    130: 0,  # langCatalan → smRoman
    131: 0,  # langLatin → smRoman
    132: 0,  # langQuechua → smRoman
    133: 0,  # langGuarani → smRoman
    134: 0,  # langAymara → smRoman
    135: 7,  # langTatar → smCyrillic
    136: 4,  # langUighur → smArabic
    137: 26,  # langDzongkha → smTibetan
    138: 0,  # langJavaneseRom → smRoman
    139: 0,  # langSundaneseRom → smRoman
    140: 0,  # langGalician → smRoman
    141: 0,  # langAfrikaans → smRoman
    142: 0,  # langBreton → smRoman (modified)
    143: 28,  # langInuktitut → smEthiopic (modified)
    144: 0,  # langScottishGaelic → smRoman (modified)
    145: 0,  # langManxGaelic → smRoman (modified)
    146: 0,  # langIrishGaelicScript → smRoman (modified)
    147: 0,  # langTongan → smRoman
    148: 6,  # langGreekAncient → smRoman
    149: 0,  # langGreenlandic → smRoman
    150: 0,  # langAzerbaijanRoman → smRoman
    151: 0,  # langNynorsk → smRoman
}


class NameRecordVisitor(TTVisitor):
    # Font tables that have NameIDs we need to collect.
    TABLES = ("GSUB", "GPOS", "fvar", "CPAL", "STAT")

    def __init__(self):
        self.seen = set()


@NameRecordVisitor.register_attrs(
    (
        (otTables.FeatureParamsSize, ("SubfamilyNameID",)),
        (otTables.FeatureParamsStylisticSet, ("UINameID",)),
        (otTables.STAT, ("ElidedFallbackNameID",)),
        (otTables.AxisRecord, ("AxisNameID",)),
        (otTables.AxisValue, ("ValueNameID",)),
        (otTables.FeatureName, ("FeatureNameID",)),
        (otTables.Setting, ("SettingNameID",)),
    )
)
def visit(visitor, obj, attr, value):
    visitor.seen.add(value)


@NameRecordVisitor.register(otTables.FeatureParamsCharacterVariants)
def visit(visitor, obj):
    for attr in ("FeatUILabelNameID", "FeatUITooltipTextNameID", "SampleTextNameID"):
        value = getattr(obj, attr)
        visitor.seen.add(value)
    # also include the sequence of UI strings for individual variants, if any
    if obj.FirstParamUILabelNameID == 0 or obj.NumNamedParameters == 0:
        return
    visitor.seen.update(
        range(
            obj.FirstParamUILabelNameID,
            obj.FirstParamUILabelNameID + obj.NumNamedParameters,
        )
    )


@NameRecordVisitor.register(ttLib.getTableClass("fvar"))
def visit(visitor, obj):
    for inst in obj.instances:
        if inst.postscriptNameID != 0xFFFF:
            visitor.seen.add(inst.postscriptNameID)
        visitor.seen.add(inst.subfamilyNameID)

    for axis in obj.axes:
        visitor.seen.add(axis.axisNameID)


@NameRecordVisitor.register(ttLib.getTableClass("CPAL"))
def visit(visitor, obj):
    if obj.version == 1:
        visitor.seen.update(obj.paletteLabels)
        visitor.seen.update(obj.paletteEntryLabels)


@NameRecordVisitor.register(ttLib.TTFont)
def visit(visitor, font, *args, **kwargs):
    if hasattr(visitor, "font"):
        return False

    visitor.font = font
    for tag in visitor.TABLES:
        if tag in font:
            visitor.visit(font[tag], *args, **kwargs)
    del visitor.font
    return False

# === NexusCore/openenv\Lib\site-packages\tornado\auth.py ===
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""This module contains implementations of various third-party
authentication schemes.

All the classes in this file are class mixins designed to be used with
the `tornado.web.RequestHandler` class.  They are used in two ways:

* On a login handler, use methods such as ``authenticate_redirect()``,
  ``authorize_redirect()``, and ``get_authenticated_user()`` to
  establish the user's identity and store authentication tokens to your
  database and/or cookies.
* In non-login handlers, use methods such as ``facebook_request()``
  or ``twitter_request()`` to use the authentication tokens to make
  requests to the respective services.

They all take slightly different arguments due to the fact all these
services implement authentication and authorization slightly differently.
See the individual service classes below for complete documentation.

Example usage for Google OAuth:

.. testsetup::

    import urllib

.. testcode::

    class GoogleOAuth2LoginHandler(tornado.web.RequestHandler,
                                    tornado.auth.GoogleOAuth2Mixin):
        async def get(self):
            # Google requires an exact match for redirect_uri, so it's
            # best to get it from your app configuration instead of from
            # self.request.full_uri().
            redirect_uri = urllib.parse.urljoin(self.application.settings['redirect_base_uri'],
                self.reverse_url('google_oauth'))
            async def get(self):
                if self.get_argument('code', False):
                    access = await self.get_authenticated_user(
                        redirect_uri=redirect_uri,
                        code=self.get_argument('code'))
                    user = await self.oauth2_request(
                        "https://www.googleapis.com/oauth2/v1/userinfo",
                        access_token=access["access_token"])
                    # Save the user and access token. For example:
                    user_cookie = dict(id=user["id"], access_token=access["access_token"])
                    self.set_signed_cookie("user", json.dumps(user_cookie))
                    self.redirect("/")
                else:
                    self.authorize_redirect(
                        redirect_uri=redirect_uri,
                        client_id=self.get_google_oauth_settings()['key'],
                        scope=['profile', 'email'],
                        response_type='code',
                        extra_params={'approval_prompt': 'auto'})

"""

import base64
import binascii
import hashlib
import hmac
import time
import urllib.parse
import uuid
import warnings

from tornado import httpclient
from tornado import escape
from tornado.httputil import url_concat
from tornado.util import unicode_type
from tornado.web import RequestHandler

from typing import List, Any, Dict, cast, Iterable, Union, Optional


class AuthError(Exception):
    pass


class OpenIdMixin:
    """Abstract implementation of OpenID and Attribute Exchange.

    Class attributes:

    * ``_OPENID_ENDPOINT``: the identity provider's URI.
    """

    def authenticate_redirect(
        self,
        callback_uri: Optional[str] = None,
        ax_attrs: List[str] = ["name", "email", "language", "username"],
    ) -> None:
        """Redirects to the authentication URL for this service.

        After authentication, the service will redirect back to the given
        callback URI with additional parameters including ``openid.mode``.

        We request the given attributes for the authenticated user by
        default (name, email, language, and username). If you don't need
        all those attributes for your app, you can request fewer with
        the ax_attrs keyword argument.

        .. versionchanged:: 6.0

            The ``callback`` argument was removed and this method no
            longer returns an awaitable object. It is now an ordinary
            synchronous function.
        """
        handler = cast(RequestHandler, self)
        callback_uri = callback_uri or handler.request.uri
        assert callback_uri is not None
        args = self._openid_args(callback_uri, ax_attrs=ax_attrs)
        endpoint = self._OPENID_ENDPOINT  # type: ignore
        handler.redirect(endpoint + "?" + urllib.parse.urlencode(args))

    async def get_authenticated_user(
        self, http_client: Optional[httpclient.AsyncHTTPClient] = None
    ) -> Dict[str, Any]:
        """Fetches the authenticated user data upon redirect.

        This method should be called by the handler that receives the
        redirect from the `authenticate_redirect()` method (which is
        often the same as the one that calls it; in that case you would
        call `get_authenticated_user` if the ``openid.mode`` parameter
        is present and `authenticate_redirect` if it is not).

        The result of this method will generally be used to set a cookie.

        .. versionchanged:: 6.0

            The ``callback`` argument was removed. Use the returned
            awaitable object instead.
        """
        handler = cast(RequestHandler, self)
        # Verify the OpenID response via direct request to the OP
        args = {
            k: v[-1] for k, v in handler.request.arguments.items()
        }  # type: Dict[str, Union[str, bytes]]
        args["openid.mode"] = "check_authentication"
        url = self._OPENID_ENDPOINT  # type: ignore
        if http_client is None:
            http_client = self.get_auth_http_client()
        resp = await http_client.fetch(
            url, method="POST", body=urllib.parse.urlencode(args)
        )
        return self._on_authentication_verified(resp)

    def _openid_args(
        self,
        callback_uri: str,
        ax_attrs: Iterable[str] = [],
        oauth_scope: Optional[str] = None,
    ) -> Dict[str, str]:
        handler = cast(RequestHandler, self)
        url = urllib.parse.urljoin(handler.request.full_url(), callback_uri)
        args = {
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.return_to": url,
            "openid.realm": urllib.parse.urljoin(url, "/"),
            "openid.mode": "checkid_setup",
        }
        if ax_attrs:
            args.update(
                {
                    "openid.ns.ax": "http://openid.net/srv/ax/1.0",
                    "openid.ax.mode": "fetch_request",
                }
            )
            ax_attrs = set(ax_attrs)
            required = []  # type: List[str]
            if "name" in ax_attrs:
                ax_attrs -= {"name", "firstname", "fullname", "lastname"}
                required += ["firstname", "fullname", "lastname"]
                args.update(
                    {
                        "openid.ax.type.firstname": "http://axschema.org/namePerson/first",
                        "openid.ax.type.fullname": "http://axschema.org/namePerson",
                        "openid.ax.type.lastname": "http://axschema.org/namePerson/last",
                    }
                )
            known_attrs = {
                "email": "http://axschema.org/contact/email",
                "language": "http://axschema.org/pref/language",
                "username": "http://axschema.org/namePerson/friendly",
            }
            for name in ax_attrs:
                args["openid.ax.type." + name] = known_attrs[name]
                required.append(name)
            args["openid.ax.required"] = ",".join(required)
        if oauth_scope:
            args.update(
                {
                    "openid.ns.oauth": "http://specs.openid.net/extensions/oauth/1.0",
                    "openid.oauth.consumer": handler.request.host.split(":")[0],
                    "openid.oauth.scope": oauth_scope,
                }
            )
        return args

    def _on_authentication_verified(
        self, response: httpclient.HTTPResponse
    ) -> Dict[str, Any]:
        handler = cast(RequestHandler, self)
        if b"is_valid:true" not in response.body:
            raise AuthError("Invalid OpenID response: %r" % response.body)

        # Make sure we got back at least an email from attribute exchange
        ax_ns = None
        for key in handler.request.arguments:
            if (
                key.startswith("openid.ns.")
                and handler.get_argument(key) == "http://openid.net/srv/ax/1.0"
            ):
                ax_ns = key[10:]
                break

        def get_ax_arg(uri: str) -> str:
            if not ax_ns:
                return ""
            prefix = "openid." + ax_ns + ".type."
            ax_name = None
            for name in handler.request.arguments.keys():
                if handler.get_argument(name) == uri and name.startswith(prefix):
                    part = name[len(prefix) :]
                    ax_name = "openid." + ax_ns + ".value." + part
                    break
            if not ax_name:
                return ""
            return handler.get_argument(ax_name, "")

        email = get_ax_arg("http://axschema.org/contact/email")
        name = get_ax_arg("http://axschema.org/namePerson")
        first_name = get_ax_arg("http://axschema.org/namePerson/first")
        last_name = get_ax_arg("http://axschema.org/namePerson/last")
        username = get_ax_arg("http://axschema.org/namePerson/friendly")
        locale = get_ax_arg("http://axschema.org/pref/language").lower()
        user = dict()
        name_parts = []
        if first_name:
            user["first_name"] = first_name
            name_parts.append(first_name)
        if last_name:
            user["last_name"] = last_name
            name_parts.append(last_name)
        if name:
            user["name"] = name
        elif name_parts:
            user["name"] = " ".join(name_parts)
        elif email:
            user["name"] = email.split("@")[0]
        if email:
            user["email"] = email
        if locale:
            user["locale"] = locale
        if username:
            user["username"] = username
        claimed_id = handler.get_argument("openid.claimed_id", None)
        if claimed_id:
            user["claimed_id"] = claimed_id
        return user

    def get_auth_http_client(self) -> httpclient.AsyncHTTPClient:
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class OAuthMixin:
    """Abstract implementation of OAuth 1.0 and 1.0a.

    See `TwitterMixin` below for an example implementation.

    Class attributes:

    * ``_OAUTH_AUTHORIZE_URL``: The service's OAuth authorization url.
    * ``_OAUTH_ACCESS_TOKEN_URL``: The service's OAuth access token url.
    * ``_OAUTH_VERSION``: May be either "1.0" or "1.0a".
    * ``_OAUTH_NO_CALLBACKS``: Set this to True if the service requires
      advance registration of callbacks.

    Subclasses must also override the `_oauth_get_user_future` and
    `_oauth_consumer_token` methods.
    """

    async def authorize_redirect(
        self,
        callback_uri: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        http_client: Optional[httpclient.AsyncHTTPClient] = None,
    ) -> None:
        """Redirects the user to obtain OAuth authorization for this service.

        The ``callback_uri`` may be omitted if you have previously
        registered a callback URI with the third-party service. For
        some services, you must use a previously-registered callback
        URI and cannot specify a callback via this method.

        This method sets a cookie called ``_oauth_request_token`` which is
        subsequently used (and cleared) in `get_authenticated_user` for
        security purposes.

        This method is asynchronous and must be called with ``await``
        or ``yield`` (This is different from other ``auth*_redirect``
        methods defined in this module). It calls
        `.RequestHandler.finish` for you so you should not write any
        other response after it returns.

        .. versionchanged:: 3.1
           Now returns a `.Future` and takes an optional callback, for
           compatibility with `.gen.coroutine`.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           awaitable object instead.

        """
        if callback_uri and getattr(self, "_OAUTH_NO_CALLBACKS", False):
            raise Exception("This service does not support oauth_callback")
        if http_client is None:
            http_client = self.get_auth_http_client()
        assert http_client is not None
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            response = await http_client.fetch(
                self._oauth_request_token_url(
                    callback_uri=callback_uri, extra_params=extra_params
                )
            )
        else:
            response = await http_client.fetch(self._oauth_request_token_url())
        url = self._OAUTH_AUTHORIZE_URL  # type: ignore
        self._on_request_token(url, callback_uri, response)

    async def get_authenticated_user(
        self, http_client: Optional[httpclient.AsyncHTTPClient] = None
    ) -> Dict[str, Any]:
        """Gets the OAuth authorized user and access token.

        This method should be called from the handler for your
        OAuth callback URL to complete the registration process. We run the
        callback with the authenticated user dictionary.  This dictionary
        will contain an ``access_key`` which can be used to make authorized
        requests to this service on behalf of the user.  The dictionary will
        also contain other fields such as ``name``, depending on the service
        used.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           awaitable object instead.
        """
        handler = cast(RequestHandler, self)
        request_key = escape.utf8(handler.get_argument("oauth_token"))
        oauth_verifier = handler.get_argument("oauth_verifier", None)
        request_cookie = handler.get_cookie("_oauth_request_token")
        if not request_cookie:
            raise AuthError("Missing OAuth request token cookie")
        handler.clear_cookie("_oauth_request_token")
        cookie_key, cookie_secret = (
            base64.b64decode(escape.utf8(i)) for i in request_cookie.split("|")
        )
        if cookie_key != request_key:
            raise AuthError("Request token does not match cookie")
        token = dict(
            key=cookie_key, secret=cookie_secret
        )  # type: Dict[str, Union[str, bytes]]
        if oauth_verifier:
            token["verifier"] = oauth_verifier
        if http_client is None:
            http_client = self.get_auth_http_client()
        assert http_client is not None
        response = await http_client.fetch(self._oauth_access_token_url(token))
        access_token = _oauth_parse_response(response.body)
        user = await self._oauth_get_user_future(access_token)
        if not user:
            raise AuthError("Error getting user")
        user["access_token"] = access_token
        return user

    def _oauth_request_token_url(
        self,
        callback_uri: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        handler = cast(RequestHandler, self)
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_REQUEST_TOKEN_URL  # type: ignore
        args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            if callback_uri == "oob":
                args["oauth_callback"] = "oob"
            elif callback_uri:
                args["oauth_callback"] = urllib.parse.urljoin(
                    handler.request.full_url(), callback_uri
                )
            if extra_params:
                args.update(extra_params)
            signature = _oauth10a_signature(consumer_token, "GET", url, args)
        else:
            signature = _oauth_signature(consumer_token, "GET", url, args)

        args["oauth_signature"] = signature
        return url + "?" + urllib.parse.urlencode(args)

    def _on_request_token(
        self,
        authorize_url: str,
        callback_uri: Optional[str],
        response: httpclient.HTTPResponse,
    ) -> None:
        handler = cast(RequestHandler, self)
        request_token = _oauth_parse_response(response.body)
        data = (
            base64.b64encode(escape.utf8(request_token["key"]))
            + b"|"
            + base64.b64encode(escape.utf8(request_token["secret"]))
        )
        handler.set_cookie("_oauth_request_token", data)
        args = dict(oauth_token=request_token["key"])
        if callback_uri == "oob":
            handler.finish(authorize_url + "?" + urllib.parse.urlencode(args))
            return
        elif callback_uri:
            args["oauth_callback"] = urllib.parse.urljoin(
                handler.request.full_url(), callback_uri
            )
        handler.redirect(authorize_url + "?" + urllib.parse.urlencode(args))

    def _oauth_access_token_url(self, request_token: Dict[str, Any]) -> str:
        consumer_token = self._oauth_consumer_token()
        url = self._OAUTH_ACCESS_TOKEN_URL  # type: ignore
        args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_token=escape.to_basestring(request_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        if "verifier" in request_token:
            args["oauth_verifier"] = request_token["verifier"]

        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            signature = _oauth10a_signature(
                consumer_token, "GET", url, args, request_token
            )
        else:
            signature = _oauth_signature(
                consumer_token, "GET", url, args, request_token
            )

        args["oauth_signature"] = signature
        return url + "?" + urllib.parse.urlencode(args)

    def _oauth_consumer_token(self) -> Dict[str, Any]:
        """Subclasses must override this to return their OAuth consumer keys.

        The return value should be a `dict` with keys ``key`` and ``secret``.
        """
        raise NotImplementedError()

    async def _oauth_get_user_future(
        self, access_token: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Subclasses must override this to get basic information about the
        user.

        Should be a coroutine whose result is a dictionary
        containing information about the user, which may have been
        retrieved by using ``access_token`` to make a request to the
        service.

        The access token will be added to the returned dictionary to make
        the result of `get_authenticated_user`.

        .. versionchanged:: 5.1

           Subclasses may also define this method with ``async def``.

        .. versionchanged:: 6.0

           A synchronous fallback to ``_oauth_get_user`` was removed.
        """
        raise NotImplementedError()

    def _oauth_request_parameters(
        self,
        url: str,
        access_token: Dict[str, Any],
        parameters: Dict[str, Any] = {},
        method: str = "GET",
    ) -> Dict[str, Any]:
        """Returns the OAuth parameters as a dict for the given request.

        parameters should include all POST arguments and query string arguments
        that will be sent with the request.
        """
        consumer_token = self._oauth_consumer_token()
        base_args = dict(
            oauth_consumer_key=escape.to_basestring(consumer_token["key"]),
            oauth_token=escape.to_basestring(access_token["key"]),
            oauth_signature_method="HMAC-SHA1",
            oauth_timestamp=str(int(time.time())),
            oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
            oauth_version="1.0",
        )
        args = {}
        args.update(base_args)
        args.update(parameters)
        if getattr(self, "_OAUTH_VERSION", "1.0a") == "1.0a":
            signature = _oauth10a_signature(
                consumer_token, method, url, args, access_token
            )
        else:
            signature = _oauth_signature(
                consumer_token, method, url, args, access_token
            )
        base_args["oauth_signature"] = escape.to_basestring(signature)
        return base_args

    def get_auth_http_client(self) -> httpclient.AsyncHTTPClient:
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.
        """
        return httpclient.AsyncHTTPClient()


class OAuth2Mixin:
    """Abstract implementation of OAuth 2.0.

    See `FacebookGraphMixin` or `GoogleOAuth2Mixin` below for example
    implementations.

    Class attributes:

    * ``_OAUTH_AUTHORIZE_URL``: The service's authorization url.
    * ``_OAUTH_ACCESS_TOKEN_URL``:  The service's access token url.
    """

    def authorize_redirect(
        self,
        redirect_uri: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        scope: Optional[List[str]] = None,
        response_type: str = "code",
    ) -> None:
        """Redirects the user to obtain OAuth authorization for this service.

        Some providers require that you register a redirect URL with
        your application instead of passing one via this method. You
        should call this method to log the user in, and then call
        ``get_authenticated_user`` in the handler for your
        redirect URL to complete the authorization process.

        .. versionchanged:: 6.0

           The ``callback`` argument and returned awaitable were removed;
           this is now an ordinary synchronous function.

        .. deprecated:: 6.4
           The ``client_secret`` argument (which has never had any effect)
           is deprecated and will be removed in Tornado 7.0.
        """
        if client_secret is not None:
            warnings.warn("client_secret argument is deprecated", DeprecationWarning)
        handler = cast(RequestHandler, self)
        args = {"response_type": response_type}
        if redirect_uri is not None:
            args["redirect_uri"] = redirect_uri
        if client_id is not None:
            args["client_id"] = client_id
        if extra_params:
            args.update(extra_params)
        if scope:
            args["scope"] = " ".join(scope)
        url = self._OAUTH_AUTHORIZE_URL  # type: ignore
        handler.redirect(url_concat(url, args))

    def _oauth_request_token_url(
        self,
        redirect_uri: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        code: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        url = self._OAUTH_ACCESS_TOKEN_URL  # type: ignore
        args = {}  # type: Dict[str, str]
        if redirect_uri is not None:
            args["redirect_uri"] = redirect_uri
        if code is not None:
            args["code"] = code
        if client_id is not None:
            args["client_id"] = client_id
        if client_secret is not None:
            args["client_secret"] = client_secret
        if extra_params:
            args.update(extra_params)
        return url_concat(url, args)

    async def oauth2_request(
        self,
        url: str,
        access_token: Optional[str] = None,
        post_args: Optional[Dict[str, Any]] = None,
        **args: Any,
    ) -> Any:
        """Fetches the given URL auth an OAuth2 access token.

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        Example usage:

        ..testcode::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.FacebookGraphMixin):
                @tornado.web.authenticated
                async def get(self):
                    new_entry = await self.oauth2_request(
                        "https://graph.facebook.com/me/feed",
                        post_args={"message": "I am posting from my Tornado application!"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        .. versionadded:: 4.3

        .. versionchanged::: 6.0

           The ``callback`` argument was removed. Use the returned awaitable object instead.
        """
        all_args = {}
        if access_token:
            all_args["access_token"] = access_token
            all_args.update(args)

        if all_args:
            url += "?" + urllib.parse.urlencode(all_args)
        http = self.get_auth_http_client()
        if post_args is not None:
            response = await http.fetch(
                url, method="POST", body=urllib.parse.urlencode(post_args)
            )
        else:
            response = await http.fetch(url)
        return escape.json_decode(response.body)

    def get_auth_http_client(self) -> httpclient.AsyncHTTPClient:
        """Returns the `.AsyncHTTPClient` instance to be used for auth requests.

        May be overridden by subclasses to use an HTTP client other than
        the default.

        .. versionadded:: 4.3
        """
        return httpclient.AsyncHTTPClient()


class TwitterMixin(OAuthMixin):
    """Twitter OAuth authentication.

    To authenticate with Twitter, register your application with
    Twitter at http://twitter.com/apps. Then copy your Consumer Key
    and Consumer Secret to the application
    `~tornado.web.Application.settings` ``twitter_consumer_key`` and
    ``twitter_consumer_secret``. Use this mixin on the handler for the
    URL you registered as your application's callback URL.

    When your application is set up, you can use this mixin like this
    to authenticate the user with Twitter and get access to their stream:

    .. testcode::

        class TwitterLoginHandler(tornado.web.RequestHandler,
                                  tornado.auth.TwitterMixin):
            async def get(self):
                if self.get_argument("oauth_token", None):
                    user = await self.get_authenticated_user()
                    # Save the user using e.g. set_signed_cookie()
                else:
                    await self.authorize_redirect()

    The user object returned by `~OAuthMixin.get_authenticated_user`
    includes the attributes ``username``, ``name``, ``access_token``,
    and all of the custom Twitter user attributes described at
    https://dev.twitter.com/docs/api/1.1/get/users/show

    .. deprecated:: 6.3
       This class refers to version 1.1 of the Twitter API, which has been
       deprecated by Twitter. Since Twitter has begun to limit access to its
       API, this class will no longer be updated and will be removed in the
       future.
    """

    _OAUTH_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
    _OAUTH_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
    _OAUTH_AUTHENTICATE_URL = "https://api.twitter.com/oauth/authenticate"
    _OAUTH_NO_CALLBACKS = False
    _TWITTER_BASE_URL = "https://api.twitter.com/1.1"

    async def authenticate_redirect(self, callback_uri: Optional[str] = None) -> None:
        """Just like `~OAuthMixin.authorize_redirect`, but
        auto-redirects if authorized.

        This is generally the right interface to use if you are using
        Twitter for single-sign on.

        .. versionchanged:: 3.1
           Now returns a `.Future` and takes an optional callback, for
           compatibility with `.gen.coroutine`.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           awaitable object instead.
        """
        http = self.get_auth_http_client()
        response = await http.fetch(
            self._oauth_request_token_url(callback_uri=callback_uri)
        )
        self._on_request_token(self._OAUTH_AUTHENTICATE_URL, None, response)

    async def twitter_request(
        self,
        path: str,
        access_token: Dict[str, Any],
        post_args: Optional[Dict[str, Any]] = None,
        **args: Any,
    ) -> Any:
        """Fetches the given API path, e.g., ``statuses/user_timeline/btaylor``

        The path should not include the format or API version number.
        (we automatically use JSON format and API version 1).

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        All the Twitter methods are documented at http://dev.twitter.com/

        Many methods require an OAuth access token which you can
        obtain through `~OAuthMixin.authorize_redirect` and
        `~OAuthMixin.get_authenticated_user`. The user returned through that
        process includes an 'access_token' attribute that can be used
        to make authenticated requests via this method. Example
        usage:

        .. testcode::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.TwitterMixin):
                @tornado.web.authenticated
                async def get(self):
                    new_entry = await self.twitter_request(
                        "/statuses/update",
                        post_args={"status": "Testing Tornado Web Server"},
                        access_token=self.current_user["access_token"])
                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        await self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned
           awaitable object instead.
        """
        if path.startswith("http:") or path.startswith("https:"):
            # Raw urls are useful for e.g. search which doesn't follow the
            # usual pattern: http://search.twitter.com/search.json
            url = path
        else:
            url = self._TWITTER_BASE_URL + path + ".json"
        # Add the OAuth resource request signature if we have credentials
        if access_token:
            all_args = {}
            all_args.update(args)
            all_args.update(post_args or {})
            method = "POST" if post_args is not None else "GET"
            oauth = self._oauth_request_parameters(
                url, access_token, all_args, method=method
            )
            args.update(oauth)
        if args:
            url += "?" + urllib.parse.urlencode(args)
        http = self.get_auth_http_client()
        if post_args is not None:
            response = await http.fetch(
                url, method="POST", body=urllib.parse.urlencode(post_args)
            )
        else:
            response = await http.fetch(url)
        return escape.json_decode(response.body)

    def _oauth_consumer_token(self) -> Dict[str, Any]:
        handler = cast(RequestHandler, self)
        handler.require_setting("twitter_consumer_key", "Twitter OAuth")
        handler.require_setting("twitter_consumer_secret", "Twitter OAuth")
        return dict(
            key=handler.settings["twitter_consumer_key"],
            secret=handler.settings["twitter_consumer_secret"],
        )

    async def _oauth_get_user_future(
        self, access_token: Dict[str, Any]
    ) -> Dict[str, Any]:
        user = await self.twitter_request(
            "/account/verify_credentials", access_token=access_token
        )
        if user:
            user["username"] = user["screen_name"]
        return user


class GoogleOAuth2Mixin(OAuth2Mixin):
    """Google authentication using OAuth2.

    In order to use, register your application with Google and copy the
    relevant parameters to your application settings.

    * Go to the Google Dev Console at http://console.developers.google.com
    * Select a project, or create a new one.
    * Depending on permissions required, you may need to set your app to
      "testing" mode and add your account as a test user, or go through
      a verfication process. You may also need to use the "Enable
      APIs and Services" command to enable specific services.
    * In the sidebar on the left, select Credentials.
    * Click CREATE CREDENTIALS and click OAuth client ID.
    * Under Application type, select Web application.
    * Name OAuth 2.0 client and click Create.
    * Copy the "Client secret" and "Client ID" to the application settings as
      ``{"google_oauth": {"key": CLIENT_ID, "secret": CLIENT_SECRET}}``
    * You must register the ``redirect_uri`` you plan to use with this class
      on the Credentials page.

    .. versionadded:: 3.2
    """

    _OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _OAUTH_ACCESS_TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    _OAUTH_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = "google_oauth"

    def get_google_oauth_settings(self) -> Dict[str, str]:
        """Return the Google OAuth 2.0 credentials that you created with
        [Google Cloud
        Platform](https://console.cloud.google.com/apis/credentials). The dict
        format is::

            {
                "key": "your_client_id", "secret": "your_client_secret"
            }

        If your credentials are stored differently (e.g. in a db) you can
        override this method for custom provision.
        """
        handler = cast(RequestHandler, self)
        return handler.settings[self._OAUTH_SETTINGS_KEY]

    async def get_authenticated_user(
        self,
        redirect_uri: str,
        code: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handles the login for the Google user, returning an access token.

        The result is a dictionary containing an ``access_token`` field
        ([among others](https://developers.google.com/identity/protocols/OAuth2WebServer#handlingtheresponse)).
        Unlike other ``get_authenticated_user`` methods in this package,
        this method does not return any additional information about the user.
        The returned access token can be used with `OAuth2Mixin.oauth2_request`
        to request additional information (perhaps from
        ``https://www.googleapis.com/oauth2/v2/userinfo``)

        Example usage:

        .. testsetup::

            import urllib

        .. testcode::

            class GoogleOAuth2LoginHandler(tornado.web.RequestHandler,
                                           tornado.auth.GoogleOAuth2Mixin):
                async def get(self):
                    # Google requires an exact match for redirect_uri, so it's
                    # best to get it from your app configuration instead of from
                    # self.request.full_uri().
                    redirect_uri = urllib.parse.urljoin(self.application.settings['redirect_base_uri'],
                        self.reverse_url('google_oauth'))
                    async def get(self):
                        if self.get_argument('code', False):
                            access = await self.get_authenticated_user(
                                redirect_uri=redirect_uri,
                                code=self.get_argument('code'))
                            user = await self.oauth2_request(
                                "https://www.googleapis.com/oauth2/v1/userinfo",
                                access_token=access["access_token"])
                            # Save the user and access token. For example:
                            user_cookie = dict(id=user["id"], access_token=access["access_token"])
                            self.set_signed_cookie("user", json.dumps(user_cookie))
                            self.redirect("/")
                        else:
                            self.authorize_redirect(
                                redirect_uri=redirect_uri,
                                client_id=self.get_google_oauth_settings()['key'],
                                scope=['profile', 'email'],
                                response_type='code',
                                extra_params={'approval_prompt': 'auto'})

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned awaitable object instead.
        """  # noqa: E501

        if client_id is None or client_secret is None:
            settings = self.get_google_oauth_settings()
            if client_id is None:
                client_id = settings["key"]
            if client_secret is None:
                client_secret = settings["secret"]
        http = self.get_auth_http_client()
        body = urllib.parse.urlencode(
            {
                "redirect_uri": redirect_uri,
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
            }
        )

        response = await http.fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=body,
        )
        return escape.json_decode(response.body)


class FacebookGraphMixin(OAuth2Mixin):
    """Facebook authentication using the new Graph API and OAuth2."""

    _OAUTH_ACCESS_TOKEN_URL = "https://graph.facebook.com/oauth/access_token?"
    _OAUTH_AUTHORIZE_URL = "https://www.facebook.com/dialog/oauth?"
    _OAUTH_NO_CALLBACKS = False
    _FACEBOOK_BASE_URL = "https://graph.facebook.com"

    async def get_authenticated_user(
        self,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
        code: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Handles the login for the Facebook user, returning a user object.

        Example usage:

        .. testcode::

            class FacebookGraphLoginHandler(tornado.web.RequestHandler,
                                            tornado.auth.FacebookGraphMixin):
              async def get(self):
                redirect_uri = urllib.parse.urljoin(
                    self.application.settings['redirect_base_uri'],
                    self.reverse_url('facebook_oauth'))
                if self.get_argument("code", False):
                    user = await self.get_authenticated_user(
                        redirect_uri=redirect_uri,
                        client_id=self.settings["facebook_api_key"],
                        client_secret=self.settings["facebook_secret"],
                        code=self.get_argument("code"))
                    # Save the user with e.g. set_signed_cookie
                else:
                    self.authorize_redirect(
                        redirect_uri=redirect_uri,
                        client_id=self.settings["facebook_api_key"],
                        extra_params={"scope": "user_posts"})

        This method returns a dictionary which may contain the following fields:

        * ``access_token``, a string which may be passed to `facebook_request`
        * ``session_expires``, an integer encoded as a string representing
          the time until the access token expires in seconds. This field should
          be used like ``int(user['session_expires'])``; in a future version of
          Tornado it will change from a string to an integer.
        * ``id``, ``name``, ``first_name``, ``last_name``, ``locale``, ``picture``,
          ``link``, plus any fields named in the ``extra_fields`` argument. These
          fields are copied from the Facebook graph API
          `user object <https://developers.facebook.com/docs/graph-api/reference/user>`_

        .. versionchanged:: 4.5
           The ``session_expires`` field was updated to support changes made to the
           Facebook API in March 2017.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned awaitable object instead.
        """
        http = self.get_auth_http_client()
        args = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        fields = {"id", "name", "first_name", "last_name", "locale", "picture", "link"}
        if extra_fields:
            fields.update(extra_fields)

        response = await http.fetch(
            self._oauth_request_token_url(**args)  # type: ignore
        )
        args = escape.json_decode(response.body)
        session = {
            "access_token": args.get("access_token"),
            "expires_in": args.get("expires_in"),
        }
        assert session["access_token"] is not None

        user = await self.facebook_request(
            path="/me",
            access_token=session["access_token"],
            appsecret_proof=hmac.new(
                key=client_secret.encode("utf8"),
                msg=session["access_token"].encode("utf8"),
                digestmod=hashlib.sha256,
            ).hexdigest(),
            fields=",".join(fields),
        )

        if user is None:
            return None

        fieldmap = {}
        for field in fields:
            fieldmap[field] = user.get(field)

        # session_expires is converted to str for compatibility with
        # older versions in which the server used url-encoding and
        # this code simply returned the string verbatim.
        # This should change in Tornado 5.0.
        fieldmap.update(
            {
                "access_token": session["access_token"],
                "session_expires": str(session.get("expires_in")),
            }
        )
        return fieldmap

    async def facebook_request(
        self,
        path: str,
        access_token: Optional[str] = None,
        post_args: Optional[Dict[str, Any]] = None,
        **args: Any,
    ) -> Any:
        """Fetches the given relative API path, e.g., "/btaylor/picture"

        If the request is a POST, ``post_args`` should be provided. Query
        string arguments should be given as keyword arguments.

        An introduction to the Facebook Graph API can be found at
        http://developers.facebook.com/docs/api

        Many methods require an OAuth access token which you can
        obtain through `~OAuth2Mixin.authorize_redirect` and
        `get_authenticated_user`. The user returned through that
        process includes an ``access_token`` attribute that can be
        used to make authenticated requests via this method.

        Example usage:

        .. testcode::

            class MainHandler(tornado.web.RequestHandler,
                              tornado.auth.FacebookGraphMixin):
                @tornado.web.authenticated
                async def get(self):
                    new_entry = await self.facebook_request(
                        "/me/feed",
                        post_args={"message": "I am posting from my Tornado application!"},
                        access_token=self.current_user["access_token"])

                    if not new_entry:
                        # Call failed; perhaps missing permission?
                        self.authorize_redirect()
                        return
                    self.finish("Posted a message!")

        The given path is relative to ``self._FACEBOOK_BASE_URL``,
        by default "https://graph.facebook.com".

        This method is a wrapper around `OAuth2Mixin.oauth2_request`;
        the only difference is that this method takes a relative path,
        while ``oauth2_request`` takes a complete url.

        .. versionchanged:: 3.1
           Added the ability to override ``self._FACEBOOK_BASE_URL``.

        .. versionchanged:: 6.0

           The ``callback`` argument was removed. Use the returned awaitable object instead.
        """
        url = self._FACEBOOK_BASE_URL + path
        return await self.oauth2_request(
            url, access_token=access_token, post_args=post_args, **args
        )


def _oauth_signature(
    consumer_token: Dict[str, Any],
    method: str,
    url: str,
    parameters: Dict[str, Any] = {},
    token: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Calculates the HMAC-SHA1 OAuth signature for the given request.

    See http://oauth.net/core/1.0/#signing_process
    """
    parts = urllib.parse.urlparse(url)
    scheme, netloc, path = parts[:3]
    normalized_url = scheme.lower() + "://" + netloc.lower() + path

    base_elems = []
    base_elems.append(method.upper())
    base_elems.append(normalized_url)
    base_elems.append(
        "&".join(f"{k}={_oauth_escape(str(v))}" for k, v in sorted(parameters.items()))
    )
    base_string = "&".join(_oauth_escape(e) for e in base_elems)

    key_elems = [escape.utf8(consumer_token["secret"])]
    key_elems.append(escape.utf8(token["secret"] if token else ""))
    key = b"&".join(key_elems)

    hash = hmac.new(key, escape.utf8(base_string), hashlib.sha1)
    return binascii.b2a_base64(hash.digest())[:-1]


def _oauth10a_signature(
    consumer_token: Dict[str, Any],
    method: str,
    url: str,
    parameters: Dict[str, Any] = {},
    token: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Calculates the HMAC-SHA1 OAuth 1.0a signature for the given request.

    See http://oauth.net/core/1.0a/#signing_process
    """
    parts = urllib.parse.urlparse(url)
    scheme, netloc, path = parts[:3]
    normalized_url = scheme.lower() + "://" + netloc.lower() + path

    base_elems = []
    base_elems.append(method.upper())
    base_elems.append(normalized_url)
    base_elems.append(
        "&".join(f"{k}={_oauth_escape(str(v))}" for k, v in sorted(parameters.items()))
    )

    base_string = "&".join(_oauth_escape(e) for e in base_elems)
    key_elems = [escape.utf8(urllib.parse.quote(consumer_token["secret"], safe="~"))]
    key_elems.append(
        escape.utf8(urllib.parse.quote(token["secret"], safe="~") if token else "")
    )
    key = b"&".join(key_elems)

    hash = hmac.new(key, escape.utf8(base_string), hashlib.sha1)
    return binascii.b2a_base64(hash.digest())[:-1]


def _oauth_escape(val: Union[str, bytes]) -> str:
    if isinstance(val, unicode_type):
        val = val.encode("utf-8")
    return urllib.parse.quote(val, safe="~")


def _oauth_parse_response(body: bytes) -> Dict[str, Any]:
    # I can't find an officially-defined encoding for oauth responses and
    # have never seen anyone use non-ascii.  Leave the response in a byte
    # string for python 2, and use utf8 on python 3.
    body_str = escape.native_str(body)
    p = urllib.parse.parse_qs(body_str, keep_blank_values=False)
    token = dict(key=p["oauth_token"][0], secret=p["oauth_token_secret"][0])

    # Add the extra parameters the Provider included to the token
    special = ("oauth_token", "oauth_token_secret")
    token.update((k, p[k][0]) for k in p if k not in special)
    return token

# === NexusCore/openenv\Lib\site-packages\PIL\ImageDraw.py ===
#
# The Python Imaging Library
# $Id$
#
# drawing interface operations
#
# History:
# 1996-04-13 fl   Created (experimental)
# 1996-08-07 fl   Filled polygons, ellipses.
# 1996-08-13 fl   Added text support
# 1998-06-28 fl   Handle I and F images
# 1998-12-29 fl   Added arc; use arc primitive to draw ellipses
# 1999-01-10 fl   Added shape stuff (experimental)
# 1999-02-06 fl   Added bitmap support
# 1999-02-11 fl   Changed all primitives to take options
# 1999-02-20 fl   Fixed backwards compatibility
# 2000-10-12 fl   Copy on write, when necessary
# 2001-02-18 fl   Use default ink for bitmap/text also in fill mode
# 2002-10-24 fl   Added support for CSS-style color strings
# 2002-12-10 fl   Added experimental support for RGBA-on-RGB drawing
# 2002-12-11 fl   Refactored low-level drawing API (work in progress)
# 2004-08-26 fl   Made Draw() a factory function, added getdraw() support
# 2004-09-04 fl   Added width support to line primitive
# 2004-09-10 fl   Added font mode handling
# 2006-06-19 fl   Added font bearing support (getmask2)
#
# Copyright (c) 1997-2006 by Secret Labs AB
# Copyright (c) 1996-2006 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import math
import struct
from collections.abc import Sequence
from types import ModuleType
from typing import Any, AnyStr, Callable, Union, cast

from . import Image, ImageColor
from ._deprecate import deprecate
from ._typing import Coords

# experimental access to the outline API
Outline: Callable[[], Image.core._Outline] = Image.core.outline

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import ImageDraw2, ImageFont

_Ink = Union[float, tuple[int, ...], str]

"""
A simple 2D drawing interface for PIL images.
<p>
Application code should use the <b>Draw</b> factory, instead of
directly.
"""


class ImageDraw:
    font: (
        ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None
    ) = None

    def __init__(self, im: Image.Image, mode: str | None = None) -> None:
        """
        Create a drawing instance.

        :param im: The image to draw in.
        :param mode: Optional mode to use for color values.  For RGB
           images, this argument can be RGB or RGBA (to blend the
           drawing into the image).  For all other modes, this argument
           must be the same as the image mode.  If omitted, the mode
           defaults to the mode of the image.
        """
        im.load()
        if im.readonly:
            im._copy()  # make it writeable
        blend = 0
        if mode is None:
            mode = im.mode
        if mode != im.mode:
            if mode == "RGBA" and im.mode == "RGB":
                blend = 1
            else:
                msg = "mode mismatch"
                raise ValueError(msg)
        if mode == "P":
            self.palette = im.palette
        else:
            self.palette = None
        self._image = im
        self.im = im.im
        self.draw = Image.core.draw(self.im, blend)
        self.mode = mode
        if mode in ("I", "F"):
            self.ink = self.draw.draw_ink(1)
        else:
            self.ink = self.draw.draw_ink(-1)
        if mode in ("1", "P", "I", "F"):
            # FIXME: fix Fill2 to properly support matte for I+F images
            self.fontmode = "1"
        else:
            self.fontmode = "L"  # aliasing is okay for other modes
        self.fill = False

    def getfont(
        self,
    ) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont:
        """
        Get the current default font.

        To set the default font for this ImageDraw instance::

            from PIL import ImageDraw, ImageFont
            draw.font = ImageFont.truetype("Tests/fonts/FreeMono.ttf")

        To set the default font for all future ImageDraw instances::

            from PIL import ImageDraw, ImageFont
            ImageDraw.ImageDraw.font = ImageFont.truetype("Tests/fonts/FreeMono.ttf")

        If the current default font is ``None``,
        it is initialized with ``ImageFont.load_default()``.

        :returns: An image font."""
        if not self.font:
            # FIXME: should add a font repository
            from . import ImageFont

            self.font = ImageFont.load_default()
        return self.font

    def _getfont(
        self, font_size: float | None
    ) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont:
        if font_size is not None:
            from . import ImageFont

            return ImageFont.load_default(font_size)
        else:
            return self.getfont()

    def _getink(
        self, ink: _Ink | None, fill: _Ink | None = None
    ) -> tuple[int | None, int | None]:
        result_ink = None
        result_fill = None
        if ink is None and fill is None:
            if self.fill:
                result_fill = self.ink
            else:
                result_ink = self.ink
        else:
            if ink is not None:
                if isinstance(ink, str):
                    ink = ImageColor.getcolor(ink, self.mode)
                if self.palette and isinstance(ink, tuple):
                    ink = self.palette.getcolor(ink, self._image)
                result_ink = self.draw.draw_ink(ink)
            if fill is not None:
                if isinstance(fill, str):
                    fill = ImageColor.getcolor(fill, self.mode)
                if self.palette and isinstance(fill, tuple):
                    fill = self.palette.getcolor(fill, self._image)
                result_fill = self.draw.draw_ink(fill)
        return result_ink, result_fill

    def arc(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw an arc."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_arc(xy, start, end, ink, width)

    def bitmap(
        self, xy: Sequence[int], bitmap: Image.Image, fill: _Ink | None = None
    ) -> None:
        """Draw a bitmap."""
        bitmap.load()
        ink, fill = self._getink(fill)
        if ink is None:
            ink = fill
        if ink is not None:
            self.draw.draw_bitmap(xy, bitmap.im, ink)

    def chord(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a chord."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_chord(xy, start, end, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_chord(xy, start, end, ink, 0, width)

    def ellipse(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw an ellipse."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_ellipse(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_ellipse(xy, ink, 0, width)

    def circle(
        self,
        xy: Sequence[float],
        radius: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a circle given center coordinates and a radius."""
        ellipse_xy = (xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius)
        self.ellipse(ellipse_xy, fill, outline, width)

    def line(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        width: int = 0,
        joint: str | None = None,
    ) -> None:
        """Draw a line, or a connected sequence of line segments."""
        ink = self._getink(fill)[0]
        if ink is not None:
            self.draw.draw_lines(xy, ink, width)
            if joint == "curve" and width > 4:
                points: Sequence[Sequence[float]]
                if isinstance(xy[0], (list, tuple)):
                    points = cast(Sequence[Sequence[float]], xy)
                else:
                    points = [
                        cast(Sequence[float], tuple(xy[i : i + 2]))
                        for i in range(0, len(xy), 2)
                    ]
                for i in range(1, len(points) - 1):
                    point = points[i]
                    angles = [
                        math.degrees(math.atan2(end[0] - start[0], start[1] - end[1]))
                        % 360
                        for start, end in (
                            (points[i - 1], point),
                            (point, points[i + 1]),
                        )
                    ]
                    if angles[0] == angles[1]:
                        # This is a straight line, so no joint is required
                        continue

                    def coord_at_angle(
                        coord: Sequence[float], angle: float
                    ) -> tuple[float, ...]:
                        x, y = coord
                        angle -= 90
                        distance = width / 2 - 1
                        return tuple(
                            p + (math.floor(p_d) if p_d > 0 else math.ceil(p_d))
                            for p, p_d in (
                                (x, distance * math.cos(math.radians(angle))),
                                (y, distance * math.sin(math.radians(angle))),
                            )
                        )

                    flipped = (
                        angles[1] > angles[0] and angles[1] - 180 > angles[0]
                    ) or (angles[1] < angles[0] and angles[1] + 180 > angles[0])
                    coords = [
                        (point[0] - width / 2 + 1, point[1] - width / 2 + 1),
                        (point[0] + width / 2 - 1, point[1] + width / 2 - 1),
                    ]
                    if flipped:
                        start, end = (angles[1] + 90, angles[0] + 90)
                    else:
                        start, end = (angles[0] - 90, angles[1] - 90)
                    self.pieslice(coords, start - 90, end - 90, fill)

                    if width > 8:
                        # Cover potential gaps between the line and the joint
                        if flipped:
                            gap_coords = [
                                coord_at_angle(point, angles[0] + 90),
                                point,
                                coord_at_angle(point, angles[1] + 90),
                            ]
                        else:
                            gap_coords = [
                                coord_at_angle(point, angles[0] - 90),
                                point,
                                coord_at_angle(point, angles[1] - 90),
                            ]
                        self.line(gap_coords, fill, width=3)

    def shape(
        self,
        shape: Image.core._Outline,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
    ) -> None:
        """(Experimental) Draw a shape."""
        shape.close()
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_outline(shape, fill_ink, 1)
        if ink is not None and ink != fill_ink:
            self.draw.draw_outline(shape, ink, 0)

    def pieslice(
        self,
        xy: Coords,
        start: float,
        end: float,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a pieslice."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_pieslice(xy, start, end, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_pieslice(xy, start, end, ink, 0, width)

    def point(self, xy: Coords, fill: _Ink | None = None) -> None:
        """Draw one or more individual pixels."""
        ink, fill = self._getink(fill)
        if ink is not None:
            self.draw.draw_points(xy, ink)

    def polygon(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a polygon."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_polygon(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            if width == 1:
                self.draw.draw_polygon(xy, ink, 0, width)
            elif self.im is not None:
                # To avoid expanding the polygon outwards,
                # use the fill as a mask
                mask = Image.new("1", self.im.size)
                mask_ink = self._getink(1)[0]

                fill_im = mask.copy()
                draw = Draw(fill_im)
                draw.draw.draw_polygon(xy, mask_ink, 1)

                ink_im = mask.copy()
                draw = Draw(ink_im)
                width = width * 2 - 1
                draw.draw.draw_polygon(xy, mask_ink, 0, width)

                mask.paste(ink_im, mask=fill_im)

                im = Image.new(self.mode, self.im.size)
                draw = Draw(im)
                draw.draw.draw_polygon(xy, ink, 0, width)
                self.im.paste(im.im, (0, 0) + im.size, mask.im)

    def regular_polygon(
        self,
        bounding_circle: Sequence[Sequence[float] | float],
        n_sides: int,
        rotation: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a regular polygon."""
        xy = _compute_regular_polygon_vertices(bounding_circle, n_sides, rotation)
        self.polygon(xy, fill, outline, width)

    def rectangle(
        self,
        xy: Coords,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None:
        """Draw a rectangle."""
        ink, fill_ink = self._getink(outline, fill)
        if fill_ink is not None:
            self.draw.draw_rectangle(xy, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            self.draw.draw_rectangle(xy, ink, 0, width)

    def rounded_rectangle(
        self,
        xy: Coords,
        radius: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
        *,
        corners: tuple[bool, bool, bool, bool] | None = None,
    ) -> None:
        """Draw a rounded rectangle."""
        if isinstance(xy[0], (list, tuple)):
            (x0, y0), (x1, y1) = cast(Sequence[Sequence[float]], xy)
        else:
            x0, y0, x1, y1 = cast(Sequence[float], xy)
        if x1 < x0:
            msg = "x1 must be greater than or equal to x0"
            raise ValueError(msg)
        if y1 < y0:
            msg = "y1 must be greater than or equal to y0"
            raise ValueError(msg)
        if corners is None:
            corners = (True, True, True, True)

        d = radius * 2

        x0 = round(x0)
        y0 = round(y0)
        x1 = round(x1)
        y1 = round(y1)
        full_x, full_y = False, False
        if all(corners):
            full_x = d >= x1 - x0 - 1
            if full_x:
                # The two left and two right corners are joined
                d = x1 - x0
            full_y = d >= y1 - y0 - 1
            if full_y:
                # The two top and two bottom corners are joined
                d = y1 - y0
            if full_x and full_y:
                # If all corners are joined, that is a circle
                return self.ellipse(xy, fill, outline, width)

        if d == 0 or not any(corners):
            # If the corners have no curve,
            # or there are no corners,
            # that is a rectangle
            return self.rectangle(xy, fill, outline, width)

        r = int(d // 2)
        ink, fill_ink = self._getink(outline, fill)

        def draw_corners(pieslice: bool) -> None:
            parts: tuple[tuple[tuple[float, float, float, float], int, int], ...]
            if full_x:
                # Draw top and bottom halves
                parts = (
                    ((x0, y0, x0 + d, y0 + d), 180, 360),
                    ((x0, y1 - d, x0 + d, y1), 0, 180),
                )
            elif full_y:
                # Draw left and right halves
                parts = (
                    ((x0, y0, x0 + d, y0 + d), 90, 270),
                    ((x1 - d, y0, x1, y0 + d), 270, 90),
                )
            else:
                # Draw four separate corners
                parts = tuple(
                    part
                    for i, part in enumerate(
                        (
                            ((x0, y0, x0 + d, y0 + d), 180, 270),
                            ((x1 - d, y0, x1, y0 + d), 270, 360),
                            ((x1 - d, y1 - d, x1, y1), 0, 90),
                            ((x0, y1 - d, x0 + d, y1), 90, 180),
                        )
                    )
                    if corners[i]
                )
            for part in parts:
                if pieslice:
                    self.draw.draw_pieslice(*(part + (fill_ink, 1)))
                else:
                    self.draw.draw_arc(*(part + (ink, width)))

        if fill_ink is not None:
            draw_corners(True)

            if full_x:
                self.draw.draw_rectangle((x0, y0 + r + 1, x1, y1 - r - 1), fill_ink, 1)
            elif x1 - r - 1 > x0 + r + 1:
                self.draw.draw_rectangle((x0 + r + 1, y0, x1 - r - 1, y1), fill_ink, 1)
            if not full_x and not full_y:
                left = [x0, y0, x0 + r, y1]
                if corners[0]:
                    left[1] += r + 1
                if corners[3]:
                    left[3] -= r + 1
                self.draw.draw_rectangle(left, fill_ink, 1)

                right = [x1 - r, y0, x1, y1]
                if corners[1]:
                    right[1] += r + 1
                if corners[2]:
                    right[3] -= r + 1
                self.draw.draw_rectangle(right, fill_ink, 1)
        if ink is not None and ink != fill_ink and width != 0:
            draw_corners(False)

            if not full_x:
                top = [x0, y0, x1, y0 + width - 1]
                if corners[0]:
                    top[0] += r + 1
                if corners[1]:
                    top[2] -= r + 1
                self.draw.draw_rectangle(top, ink, 1)

                bottom = [x0, y1 - width + 1, x1, y1]
                if corners[3]:
                    bottom[0] += r + 1
                if corners[2]:
                    bottom[2] -= r + 1
                self.draw.draw_rectangle(bottom, ink, 1)
            if not full_y:
                left = [x0, y0, x0 + width - 1, y1]
                if corners[0]:
                    left[1] += r + 1
                if corners[3]:
                    left[3] -= r + 1
                self.draw.draw_rectangle(left, ink, 1)

                right = [x1 - width + 1, y0, x1, y1]
                if corners[1]:
                    right[1] += r + 1
                if corners[2]:
                    right[3] -= r + 1
                self.draw.draw_rectangle(right, ink, 1)

    def _multiline_check(self, text: AnyStr) -> bool:
        split_character = "\n" if isinstance(text, str) else b"\n"

        return split_character in text

    def text(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        fill: _Ink | None = None,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Draw text."""
        if embedded_color and self.mode not in ("RGB", "RGBA"):
            msg = "Embedded color supported only in RGB and RGBA modes"
            raise ValueError(msg)

        if font is None:
            font = self._getfont(kwargs.get("font_size"))

        if self._multiline_check(text):
            return self.multiline_text(
                xy,
                text,
                fill,
                font,
                anchor,
                spacing,
                align,
                direction,
                features,
                language,
                stroke_width,
                stroke_fill,
                embedded_color,
            )

        def getink(fill: _Ink | None) -> int:
            ink, fill_ink = self._getink(fill)
            if ink is None:
                assert fill_ink is not None
                return fill_ink
            return ink

        def draw_text(ink: int, stroke_width: float = 0) -> None:
            mode = self.fontmode
            if stroke_width == 0 and embedded_color:
                mode = "RGBA"
            coord = []
            for i in range(2):
                coord.append(int(xy[i]))
            start = (math.modf(xy[0])[0], math.modf(xy[1])[0])
            try:
                mask, offset = font.getmask2(  # type: ignore[union-attr,misc]
                    text,
                    mode,
                    direction=direction,
                    features=features,
                    language=language,
                    stroke_width=stroke_width,
                    stroke_filled=True,
                    anchor=anchor,
                    ink=ink,
                    start=start,
                    *args,
                    **kwargs,
                )
                coord = [coord[0] + offset[0], coord[1] + offset[1]]
            except AttributeError:
                try:
                    mask = font.getmask(  # type: ignore[misc]
                        text,
                        mode,
                        direction,
                        features,
                        language,
                        stroke_width,
                        anchor,
                        ink,
                        start=start,
                        *args,
                        **kwargs,
                    )
                except TypeError:
                    mask = font.getmask(text)
            if mode == "RGBA":
                # font.getmask2(mode="RGBA") returns color in RGB bands and mask in A
                # extract mask and set text alpha
                color, mask = mask, mask.getband(3)
                ink_alpha = struct.pack("i", ink)[3]
                color.fillband(3, ink_alpha)
                x, y = coord
                if self.im is not None:
                    self.im.paste(
                        color, (x, y, x + mask.size[0], y + mask.size[1]), mask
                    )
            else:
                self.draw.draw_bitmap(coord, mask, ink)

        ink = getink(fill)
        if ink is not None:
            stroke_ink = None
            if stroke_width:
                stroke_ink = getink(stroke_fill) if stroke_fill is not None else ink

            if stroke_ink is not None:
                # Draw stroked text
                draw_text(stroke_ink, stroke_width)

                # Draw normal text
                if ink != stroke_ink:
                    draw_text(ink)
            else:
                # Only draw normal text
                draw_text(ink)

    def _prepare_multiline_text(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ),
        anchor: str | None,
        spacing: float,
        align: str,
        direction: str | None,
        features: list[str] | None,
        language: str | None,
        stroke_width: float,
        embedded_color: bool,
        font_size: float | None,
    ) -> tuple[
        ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont,
        str,
        list[tuple[tuple[float, float], AnyStr]],
    ]:
        if direction == "ttb":
            msg = "ttb direction is unsupported for multiline text"
            raise ValueError(msg)

        if anchor is None:
            anchor = "la"
        elif len(anchor) != 2:
            msg = "anchor must be a 2 character string"
            raise ValueError(msg)
        elif anchor[1] in "tb":
            msg = "anchor not supported for multiline text"
            raise ValueError(msg)

        if font is None:
            font = self._getfont(font_size)

        widths = []
        max_width: float = 0
        lines = text.split("\n" if isinstance(text, str) else b"\n")
        line_spacing = (
            self.textbbox((0, 0), "A", font, stroke_width=stroke_width)[3]
            + stroke_width
            + spacing
        )

        for line in lines:
            line_width = self.textlength(
                line,
                font,
                direction=direction,
                features=features,
                language=language,
                embedded_color=embedded_color,
            )
            widths.append(line_width)
            max_width = max(max_width, line_width)

        top = xy[1]
        if anchor[1] == "m":
            top -= (len(lines) - 1) * line_spacing / 2.0
        elif anchor[1] == "d":
            top -= (len(lines) - 1) * line_spacing

        parts = []
        for idx, line in enumerate(lines):
            left = xy[0]
            width_difference = max_width - widths[idx]

            # first align left by anchor
            if anchor[0] == "m":
                left -= width_difference / 2.0
            elif anchor[0] == "r":
                left -= width_difference

            # then align by align parameter
            if align in ("left", "justify"):
                pass
            elif align == "center":
                left += width_difference / 2.0
            elif align == "right":
                left += width_difference
            else:
                msg = 'align must be "left", "center", "right" or "justify"'
                raise ValueError(msg)

            if align == "justify" and width_difference != 0:
                words = line.split(" " if isinstance(text, str) else b" ")
                word_widths = [
                    self.textlength(
                        word,
                        font,
                        direction=direction,
                        features=features,
                        language=language,
                        embedded_color=embedded_color,
                    )
                    for word in words
                ]
                width_difference = max_width - sum(word_widths)
                for i, word in enumerate(words):
                    parts.append(((left, top), word))
                    left += word_widths[i] + width_difference / (len(words) - 1)
            else:
                parts.append(((left, top), line))

            top += line_spacing

        return font, anchor, parts

    def multiline_text(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        fill: _Ink | None = None,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> None:
        font, anchor, lines = self._prepare_multiline_text(
            xy,
            text,
            font,
            anchor,
            spacing,
            align,
            direction,
            features,
            language,
            stroke_width,
            embedded_color,
            font_size,
        )

        for xy, line in lines:
            self.text(
                xy,
                line,
                fill,
                font,
                anchor,
                direction=direction,
                features=features,
                language=language,
                stroke_width=stroke_width,
                stroke_fill=stroke_fill,
                embedded_color=embedded_color,
            )

    def textlength(
        self,
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> float:
        """Get the length of a given string, in pixels with 1/64 precision."""
        if self._multiline_check(text):
            msg = "can't measure length of multiline text"
            raise ValueError(msg)
        if embedded_color and self.mode not in ("RGB", "RGBA"):
            msg = "Embedded color supported only in RGB and RGBA modes"
            raise ValueError(msg)

        if font is None:
            font = self._getfont(font_size)
        mode = "RGBA" if embedded_color else self.fontmode
        return font.getlength(text, mode, direction, features, language)

    def textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]:
        """Get the bounding box of a given string, in pixels."""
        if embedded_color and self.mode not in ("RGB", "RGBA"):
            msg = "Embedded color supported only in RGB and RGBA modes"
            raise ValueError(msg)

        if font is None:
            font = self._getfont(font_size)

        if self._multiline_check(text):
            return self.multiline_textbbox(
                xy,
                text,
                font,
                anchor,
                spacing,
                align,
                direction,
                features,
                language,
                stroke_width,
                embedded_color,
            )

        mode = "RGBA" if embedded_color else self.fontmode
        bbox = font.getbbox(
            text, mode, direction, features, language, stroke_width, anchor
        )
        return bbox[0] + xy[0], bbox[1] + xy[1], bbox[2] + xy[0], bbox[3] + xy[1]

    def multiline_textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: (
            ImageFont.ImageFont
            | ImageFont.FreeTypeFont
            | ImageFont.TransposedFont
            | None
        ) = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]:
        font, anchor, lines = self._prepare_multiline_text(
            xy,
            text,
            font,
            anchor,
            spacing,
            align,
            direction,
            features,
            language,
            stroke_width,
            embedded_color,
            font_size,
        )

        bbox: tuple[float, float, float, float] | None = None

        for xy, line in lines:
            bbox_line = self.textbbox(
                xy,
                line,
                font,
                anchor,
                direction=direction,
                features=features,
                language=language,
                stroke_width=stroke_width,
                embedded_color=embedded_color,
            )
            if bbox is None:
                bbox = bbox_line
            else:
                bbox = (
                    min(bbox[0], bbox_line[0]),
                    min(bbox[1], bbox_line[1]),
                    max(bbox[2], bbox_line[2]),
                    max(bbox[3], bbox_line[3]),
                )

        if bbox is None:
            return xy[0], xy[1], xy[0], xy[1]
        return bbox


def Draw(im: Image.Image, mode: str | None = None) -> ImageDraw:
    """
    A simple 2D drawing interface for PIL images.

    :param im: The image to draw in.
    :param mode: Optional mode to use for color values.  For RGB
       images, this argument can be RGB or RGBA (to blend the
       drawing into the image).  For all other modes, this argument
       must be the same as the image mode.  If omitted, the mode
       defaults to the mode of the image.
    """
    try:
        return getattr(im, "getdraw")(mode)
    except AttributeError:
        return ImageDraw(im, mode)


def getdraw(
    im: Image.Image | None = None, hints: list[str] | None = None
) -> tuple[ImageDraw2.Draw | None, ModuleType]:
    """
    :param im: The image to draw in.
    :param hints: An optional list of hints. Deprecated.
    :returns: A (drawing context, drawing resource factory) tuple.
    """
    if hints is not None:
        deprecate("'hints' parameter", 12)
    from . import ImageDraw2

    draw = ImageDraw2.Draw(im) if im is not None else None
    return draw, ImageDraw2


def floodfill(
    image: Image.Image,
    xy: tuple[int, int],
    value: float | tuple[int, ...],
    border: float | tuple[int, ...] | None = None,
    thresh: float = 0,
) -> None:
    """
    .. warning:: This method is experimental.

    Fills a bounded region with a given color.

    :param image: Target image.
    :param xy: Seed position (a 2-item coordinate tuple). See
        :ref:`coordinate-system`.
    :param value: Fill color.
    :param border: Optional border value.  If given, the region consists of
        pixels with a color different from the border color.  If not given,
        the region consists of pixels having the same color as the seed
        pixel.
    :param thresh: Optional threshold value which specifies a maximum
        tolerable difference of a pixel value from the 'background' in
        order for it to be replaced. Useful for filling regions of
        non-homogeneous, but similar, colors.
    """
    # based on an implementation by Eric S. Raymond
    # amended by yo1995 @20180806
    pixel = image.load()
    assert pixel is not None
    x, y = xy
    try:
        background = pixel[x, y]
        if _color_diff(value, background) <= thresh:
            return  # seed point already has fill color
        pixel[x, y] = value
    except (ValueError, IndexError):
        return  # seed point outside image
    edge = {(x, y)}
    # use a set to keep record of current and previous edge pixels
    # to reduce memory consumption
    full_edge = set()
    while edge:
        new_edge = set()
        for x, y in edge:  # 4 adjacent method
            for s, t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                # If already processed, or if a coordinate is negative, skip
                if (s, t) in full_edge or s < 0 or t < 0:
                    continue
                try:
                    p = pixel[s, t]
                except (ValueError, IndexError):
                    pass
                else:
                    full_edge.add((s, t))
                    if border is None:
                        fill = _color_diff(p, background) <= thresh
                    else:
                        fill = p not in (value, border)
                    if fill:
                        pixel[s, t] = value
                        new_edge.add((s, t))
        full_edge = edge  # discard pixels processed
        edge = new_edge


def _compute_regular_polygon_vertices(
    bounding_circle: Sequence[Sequence[float] | float], n_sides: int, rotation: float
) -> list[tuple[float, float]]:
    """
    Generate a list of vertices for a 2D regular polygon.

    :param bounding_circle: The bounding circle is a sequence defined
        by a point and radius. The polygon is inscribed in this circle.
        (e.g. ``bounding_circle=(x, y, r)`` or ``((x, y), r)``)
    :param n_sides: Number of sides
        (e.g. ``n_sides=3`` for a triangle, ``6`` for a hexagon)
    :param rotation: Apply an arbitrary rotation to the polygon
        (e.g. ``rotation=90``, applies a 90 degree rotation)
    :return: List of regular polygon vertices
        (e.g. ``[(25, 50), (50, 50), (50, 25), (25, 25)]``)

    How are the vertices computed?
    1. Compute the following variables
        - theta: Angle between the apothem & the nearest polygon vertex
        - side_length: Length of each polygon edge
        - centroid: Center of bounding circle (1st, 2nd elements of bounding_circle)
        - polygon_radius: Polygon radius (last element of bounding_circle)
        - angles: Location of each polygon vertex in polar grid
            (e.g. A square with 0 degree rotation => [225.0, 315.0, 45.0, 135.0])

    2. For each angle in angles, get the polygon vertex at that angle
        The vertex is computed using the equation below.
            X= xcos(φ) + ysin(φ)
            Y= −xsin(φ) + ycos(φ)

        Note:
            φ = angle in degrees
            x = 0
            y = polygon_radius

        The formula above assumes rotation around the origin.
        In our case, we are rotating around the centroid.
        To account for this, we use the formula below
            X = xcos(φ) + ysin(φ) + centroid_x
            Y = −xsin(φ) + ycos(φ) + centroid_y
    """
    # 1. Error Handling
    # 1.1 Check `n_sides` has an appropriate value
    if not isinstance(n_sides, int):
        msg = "n_sides should be an int"  # type: ignore[unreachable]
        raise TypeError(msg)
    if n_sides < 3:
        msg = "n_sides should be an int > 2"
        raise ValueError(msg)

    # 1.2 Check `bounding_circle` has an appropriate value
    if not isinstance(bounding_circle, (list, tuple)):
        msg = "bounding_circle should be a sequence"
        raise TypeError(msg)

    if len(bounding_circle) == 3:
        if not all(isinstance(i, (int, float)) for i in bounding_circle):
            msg = "bounding_circle should only contain numeric data"
            raise ValueError(msg)

        *centroid, polygon_radius = cast(list[float], list(bounding_circle))
    elif len(bounding_circle) == 2 and isinstance(bounding_circle[0], (list, tuple)):
        if not all(
            isinstance(i, (int, float)) for i in bounding_circle[0]
        ) or not isinstance(bounding_circle[1], (int, float)):
            msg = "bounding_circle should only contain numeric data"
            raise ValueError(msg)

        if len(bounding_circle[0]) != 2:
            msg = "bounding_circle centre should contain 2D coordinates (e.g. (x, y))"
            raise ValueError(msg)

        centroid = cast(list[float], list(bounding_circle[0]))
        polygon_radius = cast(float, bounding_circle[1])
    else:
        msg = (
            "bounding_circle should contain 2D coordinates "
            "and a radius (e.g. (x, y, r) or ((x, y), r) )"
        )
        raise ValueError(msg)

    if polygon_radius <= 0:
        msg = "bounding_circle radius should be > 0"
        raise ValueError(msg)

    # 1.3 Check `rotation` has an appropriate value
    if not isinstance(rotation, (int, float)):
        msg = "rotation should be an int or float"  # type: ignore[unreachable]
        raise ValueError(msg)

    # 2. Define Helper Functions
    def _apply_rotation(point: list[float], degrees: float) -> tuple[float, float]:
        return (
            round(
                point[0] * math.cos(math.radians(360 - degrees))
                - point[1] * math.sin(math.radians(360 - degrees))
                + centroid[0],
                2,
            ),
            round(
                point[1] * math.cos(math.radians(360 - degrees))
                + point[0] * math.sin(math.radians(360 - degrees))
                + centroid[1],
                2,
            ),
        )

    def _compute_polygon_vertex(angle: float) -> tuple[float, float]:
        start_point = [polygon_radius, 0]
        return _apply_rotation(start_point, angle)

    def _get_angles(n_sides: int, rotation: float) -> list[float]:
        angles = []
        degrees = 360 / n_sides
        # Start with the bottom left polygon vertex
        current_angle = (270 - 0.5 * degrees) + rotation
        for _ in range(n_sides):
            angles.append(current_angle)
            current_angle += degrees
            if current_angle > 360:
                current_angle -= 360
        return angles

    # 3. Variable Declarations
    angles = _get_angles(n_sides, rotation)

    # 4. Compute Vertices
    return [_compute_polygon_vertex(angle) for angle in angles]


def _color_diff(
    color1: float | tuple[int, ...], color2: float | tuple[int, ...]
) -> float:
    """
    Uses 1-norm distance to calculate difference between two values.
    """
    first = color1 if isinstance(color1, tuple) else (color1,)
    second = color2 if isinstance(color2, tuple) else (color2,)

    return sum(abs(first[i] - second[i]) for i in range(len(second)))

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_transformer.py ===
from __future__ import annotations

import ast
import builtins
import sys
import typing
from ast import (
    AST,
    Add,
    AnnAssign,
    Assign,
    AsyncFunctionDef,
    Attribute,
    AugAssign,
    BinOp,
    BitAnd,
    BitOr,
    BitXor,
    Call,
    ClassDef,
    Constant,
    Dict,
    Div,
    Expr,
    Expression,
    FloorDiv,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    Index,
    List,
    Load,
    LShift,
    MatMult,
    Mod,
    Module,
    Mult,
    Name,
    NamedExpr,
    NodeTransformer,
    NodeVisitor,
    Pass,
    Pow,
    Return,
    RShift,
    Starred,
    Store,
    Sub,
    Subscript,
    Tuple,
    Yield,
    YieldFrom,
    alias,
    copy_location,
    expr,
    fix_missing_locations,
    keyword,
    walk,
)
from collections import defaultdict
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, cast, overload

generator_names = (
    "typing.Generator",
    "collections.abc.Generator",
    "typing.Iterator",
    "collections.abc.Iterator",
    "typing.Iterable",
    "collections.abc.Iterable",
    "typing.AsyncIterator",
    "collections.abc.AsyncIterator",
    "typing.AsyncIterable",
    "collections.abc.AsyncIterable",
    "typing.AsyncGenerator",
    "collections.abc.AsyncGenerator",
)
anytype_names = (
    "typing.Any",
    "typing_extensions.Any",
)
literal_names = (
    "typing.Literal",
    "typing_extensions.Literal",
)
annotated_names = (
    "typing.Annotated",
    "typing_extensions.Annotated",
)
ignore_decorators = (
    "typing.no_type_check",
    "typeguard.typeguard_ignore",
)
aug_assign_functions = {
    Add: "iadd",
    Sub: "isub",
    Mult: "imul",
    MatMult: "imatmul",
    Div: "itruediv",
    FloorDiv: "ifloordiv",
    Mod: "imod",
    Pow: "ipow",
    LShift: "ilshift",
    RShift: "irshift",
    BitAnd: "iand",
    BitXor: "ixor",
    BitOr: "ior",
}


@dataclass
class TransformMemo:
    node: Module | ClassDef | FunctionDef | AsyncFunctionDef | None
    parent: TransformMemo | None
    path: tuple[str, ...]
    joined_path: Constant = field(init=False)
    return_annotation: expr | None = None
    yield_annotation: expr | None = None
    send_annotation: expr | None = None
    is_async: bool = False
    local_names: set[str] = field(init=False, default_factory=set)
    imported_names: dict[str, str] = field(init=False, default_factory=dict)
    ignored_names: set[str] = field(init=False, default_factory=set)
    load_names: defaultdict[str, dict[str, Name]] = field(
        init=False, default_factory=lambda: defaultdict(dict)
    )
    has_yield_expressions: bool = field(init=False, default=False)
    has_return_expressions: bool = field(init=False, default=False)
    memo_var_name: Name | None = field(init=False, default=None)
    should_instrument: bool = field(init=False, default=True)
    variable_annotations: dict[str, expr] = field(init=False, default_factory=dict)
    configuration_overrides: dict[str, Any] = field(init=False, default_factory=dict)
    code_inject_index: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        elements: list[str] = []
        memo = self
        while isinstance(memo.node, (ClassDef, FunctionDef, AsyncFunctionDef)):
            elements.insert(0, memo.node.name)
            if not memo.parent:
                break

            memo = memo.parent
            if isinstance(memo.node, (FunctionDef, AsyncFunctionDef)):
                elements.insert(0, "<locals>")

        self.joined_path = Constant(".".join(elements))

        # Figure out where to insert instrumentation code
        if self.node:
            for index, child in enumerate(self.node.body):
                if isinstance(child, ImportFrom) and child.module == "__future__":
                    # (module only) __future__ imports must come first
                    continue
                elif (
                    isinstance(child, Expr)
                    and isinstance(child.value, Constant)
                    and isinstance(child.value.value, str)
                ):
                    continue  # docstring

                self.code_inject_index = index
                break

    def get_unused_name(self, name: str) -> str:
        memo: TransformMemo | None = self
        while memo is not None:
            if name in memo.local_names:
                memo = self
                name += "_"
            else:
                memo = memo.parent

        self.local_names.add(name)
        return name

    def is_ignored_name(self, expression: expr | Expr | None) -> bool:
        top_expression = (
            expression.value if isinstance(expression, Expr) else expression
        )

        if isinstance(top_expression, Attribute) and isinstance(
            top_expression.value, Name
        ):
            name = top_expression.value.id
        elif isinstance(top_expression, Name):
            name = top_expression.id
        else:
            return False

        memo: TransformMemo | None = self
        while memo is not None:
            if name in memo.ignored_names:
                return True

            memo = memo.parent

        return False

    def get_memo_name(self) -> Name:
        if not self.memo_var_name:
            self.memo_var_name = Name(id="memo", ctx=Load())

        return self.memo_var_name

    def get_import(self, module: str, name: str) -> Name:
        if module in self.load_names and name in self.load_names[module]:
            return self.load_names[module][name]

        qualified_name = f"{module}.{name}"
        if name in self.imported_names and self.imported_names[name] == qualified_name:
            return Name(id=name, ctx=Load())

        alias = self.get_unused_name(name)
        node = self.load_names[module][name] = Name(id=alias, ctx=Load())
        self.imported_names[name] = qualified_name
        return node

    def insert_imports(self, node: Module | FunctionDef | AsyncFunctionDef) -> None:
        """Insert imports needed by injected code."""
        if not self.load_names:
            return

        # Insert imports after any "from __future__ ..." imports and any docstring
        for modulename, names in self.load_names.items():
            aliases = [
                alias(orig_name, new_name.id if orig_name != new_name.id else None)
                for orig_name, new_name in sorted(names.items())
            ]
            node.body.insert(self.code_inject_index, ImportFrom(modulename, aliases, 0))

    def name_matches(self, expression: expr | Expr | None, *names: str) -> bool:
        if expression is None:
            return False

        path: list[str] = []
        top_expression = (
            expression.value if isinstance(expression, Expr) else expression
        )

        if isinstance(top_expression, Subscript):
            top_expression = top_expression.value
        elif isinstance(top_expression, Call):
            top_expression = top_expression.func

        while isinstance(top_expression, Attribute):
            path.insert(0, top_expression.attr)
            top_expression = top_expression.value

        if not isinstance(top_expression, Name):
            return False

        if top_expression.id in self.imported_names:
            translated = self.imported_names[top_expression.id]
        elif hasattr(builtins, top_expression.id):
            translated = "builtins." + top_expression.id
        else:
            translated = top_expression.id

        path.insert(0, translated)
        joined_path = ".".join(path)
        if joined_path in names:
            return True
        elif self.parent:
            return self.parent.name_matches(expression, *names)
        else:
            return False

    def get_config_keywords(self) -> list[keyword]:
        if self.parent and isinstance(self.parent.node, ClassDef):
            overrides = self.parent.configuration_overrides.copy()
        else:
            overrides = {}

        overrides.update(self.configuration_overrides)
        return [keyword(key, value) for key, value in overrides.items()]


class NameCollector(NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Import(self, node: Import) -> None:
        for name in node.names:
            self.names.add(name.asname or name.name)

    def visit_ImportFrom(self, node: ImportFrom) -> None:
        for name in node.names:
            self.names.add(name.asname or name.name)

    def visit_Assign(self, node: Assign) -> None:
        for target in node.targets:
            if isinstance(target, Name):
                self.names.add(target.id)

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        if isinstance(node.target, Name):
            self.names.add(node.target.id)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        pass

    def visit_ClassDef(self, node: ClassDef) -> None:
        pass


class GeneratorDetector(NodeVisitor):
    """Detects if a function node is a generator function."""

    contains_yields: bool = False
    in_root_function: bool = False

    def visit_Yield(self, node: Yield) -> Any:
        self.contains_yields = True

    def visit_YieldFrom(self, node: YieldFrom) -> Any:
        self.contains_yields = True

    def visit_ClassDef(self, node: ClassDef) -> Any:
        pass

    def visit_FunctionDef(self, node: FunctionDef | AsyncFunctionDef) -> Any:
        if not self.in_root_function:
            self.in_root_function = True
            self.generic_visit(node)
            self.in_root_function = False

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)


class AnnotationTransformer(NodeTransformer):
    type_substitutions: ClassVar[dict[str, tuple[str, str]]] = {
        "builtins.dict": ("typing", "Dict"),
        "builtins.list": ("typing", "List"),
        "builtins.tuple": ("typing", "Tuple"),
        "builtins.set": ("typing", "Set"),
        "builtins.frozenset": ("typing", "FrozenSet"),
    }

    def __init__(self, transformer: TypeguardTransformer):
        self.transformer = transformer
        self._memo = transformer._memo
        self._level = 0

    def visit(self, node: AST) -> Any:
        # Don't process Literals
        if isinstance(node, expr) and self._memo.name_matches(node, *literal_names):
            return node

        self._level += 1
        new_node = super().visit(node)
        self._level -= 1

        if isinstance(new_node, Expression) and not hasattr(new_node, "body"):
            return None

        # Return None if this new node matches a variation of typing.Any
        if (
            self._level == 0
            and isinstance(new_node, expr)
            and self._memo.name_matches(new_node, *anytype_names)
        ):
            return None

        return new_node

    def visit_BinOp(self, node: BinOp) -> Any:
        self.generic_visit(node)

        if isinstance(node.op, BitOr):
            # If either branch of the BinOp has been transformed to `None`, it means
            # that a type in the union was ignored, so the entire annotation should e
            # ignored
            if not hasattr(node, "left") or not hasattr(node, "right"):
                return None

            # Return Any if either side is Any
            if self._memo.name_matches(node.left, *anytype_names):
                return node.left
            elif self._memo.name_matches(node.right, *anytype_names):
                return node.right

            if sys.version_info < (3, 10):
                union_name = self.transformer._get_import("typing", "Union")
                return Subscript(
                    value=union_name,
                    slice=Index(
                        Tuple(elts=[node.left, node.right], ctx=Load()), ctx=Load()
                    ),
                    ctx=Load(),
                )

        return node

    def visit_Attribute(self, node: Attribute) -> Any:
        if self._memo.is_ignored_name(node):
            return None

        return node

    def visit_Subscript(self, node: Subscript) -> Any:
        if self._memo.is_ignored_name(node.value):
            return None

        # The subscript of typing(_extensions).Literal can be any arbitrary string, so
        # don't try to evaluate it as code
        if node.slice:
            if isinstance(node.slice, Index):
                # Python 3.8
                slice_value = node.slice.value  # type: ignore[attr-defined]
            else:
                slice_value = node.slice

            if isinstance(slice_value, Tuple):
                if self._memo.name_matches(node.value, *annotated_names):
                    # Only treat the first argument to typing.Annotated as a potential
                    # forward reference
                    items = cast(
                        typing.List[expr],
                        [self.visit(slice_value.elts[0])] + slice_value.elts[1:],
                    )
                else:
                    items = cast(
                        typing.List[expr],
                        [self.visit(item) for item in slice_value.elts],
                    )

                # If this is a Union and any of the items is Any, erase the entire
                # annotation
                if self._memo.name_matches(node.value, "typing.Union") and any(
                    item is None
                    or (
                        isinstance(item, expr)
                        and self._memo.name_matches(item, *anytype_names)
                    )
                    for item in items
                ):
                    return None

                # If all items in the subscript were Any, erase the subscript entirely
                if all(item is None for item in items):
                    return node.value

                for index, item in enumerate(items):
                    if item is None:
                        items[index] = self.transformer._get_import("typing", "Any")

                slice_value.elts = items
            else:
                self.generic_visit(node)

                # If the transformer erased the slice entirely, just return the node
                # value without the subscript (unless it's Optional, in which case erase
                # the node entirely
                if self._memo.name_matches(
                    node.value, "typing.Optional"
                ) and not hasattr(node, "slice"):
                    return None
                if sys.version_info >= (3, 9) and not hasattr(node, "slice"):
                    return node.value
                elif sys.version_info < (3, 9) and not hasattr(node.slice, "value"):
                    return node.value

        return node

    def visit_Name(self, node: Name) -> Any:
        if self._memo.is_ignored_name(node):
            return None

        if sys.version_info < (3, 9):
            for typename, substitute in self.type_substitutions.items():
                if self._memo.name_matches(node, typename):
                    new_node = self.transformer._get_import(*substitute)
                    return copy_location(new_node, node)

        return node

    def visit_Call(self, node: Call) -> Any:
        # Don't recurse into calls
        return node

    def visit_Constant(self, node: Constant) -> Any:
        if isinstance(node.value, str):
            expression = ast.parse(node.value, mode="eval")
            new_node = self.visit(expression)
            if new_node:
                return copy_location(new_node.body, node)
            else:
                return None

        return node


class TypeguardTransformer(NodeTransformer):
    def __init__(
        self, target_path: Sequence[str] | None = None, target_lineno: int | None = None
    ) -> None:
        self._target_path = tuple(target_path) if target_path else None
        self._memo = self._module_memo = TransformMemo(None, None, ())
        self.names_used_in_annotations: set[str] = set()
        self.target_node: FunctionDef | AsyncFunctionDef | None = None
        self.target_lineno = target_lineno

    def generic_visit(self, node: AST) -> AST:
        has_non_empty_body_initially = bool(getattr(node, "body", None))
        initial_type = type(node)

        node = super().generic_visit(node)

        if (
            type(node) is initial_type
            and has_non_empty_body_initially
            and hasattr(node, "body")
            and not node.body
        ):
            # If we have still the same node type after transformation
            # but we've optimised it's body away, we add a `pass` statement.
            node.body = [Pass()]

        return node

    @contextmanager
    def _use_memo(
        self, node: ClassDef | FunctionDef | AsyncFunctionDef
    ) -> Generator[None, Any, None]:
        new_memo = TransformMemo(node, self._memo, self._memo.path + (node.name,))
        old_memo = self._memo
        self._memo = new_memo

        if isinstance(node, (FunctionDef, AsyncFunctionDef)):
            new_memo.should_instrument = (
                self._target_path is None or new_memo.path == self._target_path
            )
            if new_memo.should_instrument:
                # Check if the function is a generator function
                detector = GeneratorDetector()
                detector.visit(node)

                # Extract yield, send and return types where possible from a subscripted
                # annotation like Generator[int, str, bool]
                return_annotation = deepcopy(node.returns)
                if detector.contains_yields and new_memo.name_matches(
                    return_annotation, *generator_names
                ):
                    if isinstance(return_annotation, Subscript):
                        annotation_slice = return_annotation.slice

                        # Python < 3.9
                        if isinstance(annotation_slice, Index):
                            annotation_slice = (
                                annotation_slice.value  # type: ignore[attr-defined]
                            )

                        if isinstance(annotation_slice, Tuple):
                            items = annotation_slice.elts
                        else:
                            items = [annotation_slice]

                        if len(items) > 0:
                            new_memo.yield_annotation = self._convert_annotation(
                                items[0]
                            )

                        if len(items) > 1:
                            new_memo.send_annotation = self._convert_annotation(
                                items[1]
                            )

                        if len(items) > 2:
                            new_memo.return_annotation = self._convert_annotation(
                                items[2]
                            )
                else:
                    new_memo.return_annotation = self._convert_annotation(
                        return_annotation
                    )

        if isinstance(node, AsyncFunctionDef):
            new_memo.is_async = True

        yield
        self._memo = old_memo

    def _get_import(self, module: str, name: str) -> Name:
        memo = self._memo if self._target_path else self._module_memo
        return memo.get_import(module, name)

    @overload
    def _convert_annotation(self, annotation: None) -> None: ...

    @overload
    def _convert_annotation(self, annotation: expr) -> expr: ...

    def _convert_annotation(self, annotation: expr | None) -> expr | None:
        if annotation is None:
            return None

        # Convert PEP 604 unions (x | y) and generic built-in collections where
        # necessary, and undo forward references
        new_annotation = cast(expr, AnnotationTransformer(self).visit(annotation))
        if isinstance(new_annotation, expr):
            new_annotation = ast.copy_location(new_annotation, annotation)

            # Store names used in the annotation
            names = {node.id for node in walk(new_annotation) if isinstance(node, Name)}
            self.names_used_in_annotations.update(names)

        return new_annotation

    def visit_Name(self, node: Name) -> Name:
        self._memo.local_names.add(node.id)
        return node

    def visit_Module(self, node: Module) -> Module:
        self._module_memo = self._memo = TransformMemo(node, None, ())
        self.generic_visit(node)
        self._module_memo.insert_imports(node)

        fix_missing_locations(node)
        return node

    def visit_Import(self, node: Import) -> Import:
        for name in node.names:
            self._memo.local_names.add(name.asname or name.name)
            self._memo.imported_names[name.asname or name.name] = name.name

        return node

    def visit_ImportFrom(self, node: ImportFrom) -> ImportFrom:
        for name in node.names:
            if name.name != "*":
                alias = name.asname or name.name
                self._memo.local_names.add(alias)
                self._memo.imported_names[alias] = f"{node.module}.{name.name}"

        return node

    def visit_ClassDef(self, node: ClassDef) -> ClassDef | None:
        self._memo.local_names.add(node.name)

        # Eliminate top level classes not belonging to the target path
        if (
            self._target_path is not None
            and not self._memo.path
            and node.name != self._target_path[0]
        ):
            return None

        with self._use_memo(node):
            for decorator in node.decorator_list.copy():
                if self._memo.name_matches(decorator, "typeguard.typechecked"):
                    # Remove the decorator to prevent duplicate instrumentation
                    node.decorator_list.remove(decorator)

                    # Store any configuration overrides
                    if isinstance(decorator, Call) and decorator.keywords:
                        self._memo.configuration_overrides.update(
                            {kw.arg: kw.value for kw in decorator.keywords if kw.arg}
                        )

            self.generic_visit(node)
            return node

    def visit_FunctionDef(
        self, node: FunctionDef | AsyncFunctionDef
    ) -> FunctionDef | AsyncFunctionDef | None:
        """
        Injects type checks for function arguments, and for a return of None if the
        function is annotated to return something else than Any or None, and the body
        ends without an explicit "return".

        """
        self._memo.local_names.add(node.name)

        # Eliminate top level functions not belonging to the target path
        if (
            self._target_path is not None
            and not self._memo.path
            and node.name != self._target_path[0]
        ):
            return None

        # Skip instrumentation if we're instrumenting the whole module and the function
        # contains either @no_type_check or @typeguard_ignore
        if self._target_path is None:
            for decorator in node.decorator_list:
                if self._memo.name_matches(decorator, *ignore_decorators):
                    return node

        with self._use_memo(node):
            arg_annotations: dict[str, Any] = {}
            if self._target_path is None or self._memo.path == self._target_path:
                # Find line number we're supposed to match against
                if node.decorator_list:
                    first_lineno = node.decorator_list[0].lineno
                else:
                    first_lineno = node.lineno

                for decorator in node.decorator_list.copy():
                    if self._memo.name_matches(decorator, "typing.overload"):
                        # Remove overloads entirely
                        return None
                    elif self._memo.name_matches(decorator, "typeguard.typechecked"):
                        # Remove the decorator to prevent duplicate instrumentation
                        node.decorator_list.remove(decorator)

                        # Store any configuration overrides
                        if isinstance(decorator, Call) and decorator.keywords:
                            self._memo.configuration_overrides = {
                                kw.arg: kw.value for kw in decorator.keywords if kw.arg
                            }

                if self.target_lineno == first_lineno:
                    assert self.target_node is None
                    self.target_node = node
                    if node.decorator_list:
                        self.target_lineno = node.decorator_list[0].lineno
                    else:
                        self.target_lineno = node.lineno

                all_args = node.args.args + node.args.kwonlyargs + node.args.posonlyargs

                # Ensure that any type shadowed by the positional or keyword-only
                # argument names are ignored in this function
                for arg in all_args:
                    self._memo.ignored_names.add(arg.arg)

                # Ensure that any type shadowed by the variable positional argument name
                # (e.g. "args" in *args) is ignored this function
                if node.args.vararg:
                    self._memo.ignored_names.add(node.args.vararg.arg)

                # Ensure that any type shadowed by the variable keywrod argument name
                # (e.g. "kwargs" in *kwargs) is ignored this function
                if node.args.kwarg:
                    self._memo.ignored_names.add(node.args.kwarg.arg)

                for arg in all_args:
                    annotation = self._convert_annotation(deepcopy(arg.annotation))
                    if annotation:
                        arg_annotations[arg.arg] = annotation

                if node.args.vararg:
                    annotation_ = self._convert_annotation(node.args.vararg.annotation)
                    if annotation_:
                        if sys.version_info >= (3, 9):
                            container = Name("tuple", ctx=Load())
                        else:
                            container = self._get_import("typing", "Tuple")

                        subscript_slice: Tuple | Index = Tuple(
                            [
                                annotation_,
                                Constant(Ellipsis),
                            ],
                            ctx=Load(),
                        )
                        if sys.version_info < (3, 9):
                            subscript_slice = Index(subscript_slice, ctx=Load())

                        arg_annotations[node.args.vararg.arg] = Subscript(
                            container, subscript_slice, ctx=Load()
                        )

                if node.args.kwarg:
                    annotation_ = self._convert_annotation(node.args.kwarg.annotation)
                    if annotation_:
                        if sys.version_info >= (3, 9):
                            container = Name("dict", ctx=Load())
                        else:
                            container = self._get_import("typing", "Dict")

                        subscript_slice = Tuple(
                            [
                                Name("str", ctx=Load()),
                                annotation_,
                            ],
                            ctx=Load(),
                        )
                        if sys.version_info < (3, 9):
                            subscript_slice = Index(subscript_slice, ctx=Load())

                        arg_annotations[node.args.kwarg.arg] = Subscript(
                            container, subscript_slice, ctx=Load()
                        )

                if arg_annotations:
                    self._memo.variable_annotations.update(arg_annotations)

            self.generic_visit(node)

            if arg_annotations:
                annotations_dict = Dict(
                    keys=[Constant(key) for key in arg_annotations.keys()],
                    values=[
                        Tuple([Name(key, ctx=Load()), annotation], ctx=Load())
                        for key, annotation in arg_annotations.items()
                    ],
                )
                func_name = self._get_import(
                    "typeguard._functions", "check_argument_types"
                )
                args = [
                    self._memo.joined_path,
                    annotations_dict,
                    self._memo.get_memo_name(),
                ]
                node.body.insert(
                    self._memo.code_inject_index, Expr(Call(func_name, args, []))
                )

            # Add a checked "return None" to the end if there's no explicit return
            # Skip if the return annotation is None or Any
            if (
                self._memo.return_annotation
                and (not self._memo.is_async or not self._memo.has_yield_expressions)
                and not isinstance(node.body[-1], Return)
                and (
                    not isinstance(self._memo.return_annotation, Constant)
                    or self._memo.return_annotation.value is not None
                )
            ):
                func_name = self._get_import(
                    "typeguard._functions", "check_return_type"
                )
                return_node = Return(
                    Call(
                        func_name,
                        [
                            self._memo.joined_path,
                            Constant(None),
                            self._memo.return_annotation,
                            self._memo.get_memo_name(),
                        ],
                        [],
                    )
                )

                # Replace a placeholder "pass" at the end
                if isinstance(node.body[-1], Pass):
                    copy_location(return_node, node.body[-1])
                    del node.body[-1]

                node.body.append(return_node)

            # Insert code to create the call memo, if it was ever needed for this
            # function
            if self._memo.memo_var_name:
                memo_kwargs: dict[str, Any] = {}
                if self._memo.parent and isinstance(self._memo.parent.node, ClassDef):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, Name)
                            and decorator.id == "staticmethod"
                        ):
                            break
                        elif (
                            isinstance(decorator, Name)
                            and decorator.id == "classmethod"
                        ):
                            memo_kwargs["self_type"] = Name(
                                id=node.args.args[0].arg, ctx=Load()
                            )
                            break
                    else:
                        if node.args.args:
                            if node.name == "__new__":
                                memo_kwargs["self_type"] = Name(
                                    id=node.args.args[0].arg, ctx=Load()
                                )
                            else:
                                memo_kwargs["self_type"] = Attribute(
                                    Name(id=node.args.args[0].arg, ctx=Load()),
                                    "__class__",
                                    ctx=Load(),
                                )

                # Construct the function reference
                # Nested functions get special treatment: the function name is added
                # to free variables (and the closure of the resulting function)
                names: list[str] = [node.name]
                memo = self._memo.parent
                while memo:
                    if isinstance(memo.node, (FunctionDef, AsyncFunctionDef)):
                        # This is a nested function. Use the function name as-is.
                        del names[:-1]
                        break
                    elif not isinstance(memo.node, ClassDef):
                        break

                    names.insert(0, memo.node.name)
                    memo = memo.parent

                config_keywords = self._memo.get_config_keywords()
                if config_keywords:
                    memo_kwargs["config"] = Call(
                        self._get_import("dataclasses", "replace"),
                        [self._get_import("typeguard._config", "global_config")],
                        config_keywords,
                    )

                self._memo.memo_var_name.id = self._memo.get_unused_name("memo")
                memo_store_name = Name(id=self._memo.memo_var_name.id, ctx=Store())
                globals_call = Call(Name(id="globals", ctx=Load()), [], [])
                locals_call = Call(Name(id="locals", ctx=Load()), [], [])
                memo_expr = Call(
                    self._get_import("typeguard", "TypeCheckMemo"),
                    [globals_call, locals_call],
                    [keyword(key, value) for key, value in memo_kwargs.items()],
                )
                node.body.insert(
                    self._memo.code_inject_index,
                    Assign([memo_store_name], memo_expr),
                )

                self._memo.insert_imports(node)

                # Special case the __new__() method to create a local alias from the
                # class name to the first argument (usually "cls")
                if (
                    isinstance(node, FunctionDef)
                    and node.args
                    and self._memo.parent is not None
                    and isinstance(self._memo.parent.node, ClassDef)
                    and node.name == "__new__"
                ):
                    first_args_expr = Name(node.args.args[0].arg, ctx=Load())
                    cls_name = Name(self._memo.parent.node.name, ctx=Store())
                    node.body.insert(
                        self._memo.code_inject_index,
                        Assign([cls_name], first_args_expr),
                    )

                # Rmove any placeholder "pass" at the end
                if isinstance(node.body[-1], Pass):
                    del node.body[-1]

        return node

    def visit_AsyncFunctionDef(
        self, node: AsyncFunctionDef
    ) -> FunctionDef | AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)

    def visit_Return(self, node: Return) -> Return:
        """This injects type checks into "return" statements."""
        self.generic_visit(node)
        if (
            self._memo.return_annotation
            and self._memo.should_instrument
            and not self._memo.is_ignored_name(self._memo.return_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_return_type")
            old_node = node
            retval = old_node.value or Constant(None)
            node = Return(
                Call(
                    func_name,
                    [
                        self._memo.joined_path,
                        retval,
                        self._memo.return_annotation,
                        self._memo.get_memo_name(),
                    ],
                    [],
                )
            )
            copy_location(node, old_node)

        return node

    def visit_Yield(self, node: Yield) -> Yield | Call:
        """
        This injects type checks into "yield" expressions, checking both the yielded
        value and the value sent back to the generator, when appropriate.

        """
        self._memo.has_yield_expressions = True
        self.generic_visit(node)

        if (
            self._memo.yield_annotation
            and self._memo.should_instrument
            and not self._memo.is_ignored_name(self._memo.yield_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_yield_type")
            yieldval = node.value or Constant(None)
            node.value = Call(
                func_name,
                [
                    self._memo.joined_path,
                    yieldval,
                    self._memo.yield_annotation,
                    self._memo.get_memo_name(),
                ],
                [],
            )

        if (
            self._memo.send_annotation
            and self._memo.should_instrument
            and not self._memo.is_ignored_name(self._memo.send_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_send_type")
            old_node = node
            call_node = Call(
                func_name,
                [
                    self._memo.joined_path,
                    old_node,
                    self._memo.send_annotation,
                    self._memo.get_memo_name(),
                ],
                [],
            )
            copy_location(call_node, old_node)
            return call_node

        return node

    def visit_AnnAssign(self, node: AnnAssign) -> Any:
        """
        This injects a type check into a local variable annotation-assignment within a
        function body.

        """
        self.generic_visit(node)

        if (
            isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef))
            and node.annotation
            and isinstance(node.target, Name)
        ):
            self._memo.ignored_names.add(node.target.id)
            annotation = self._convert_annotation(deepcopy(node.annotation))
            if annotation:
                self._memo.variable_annotations[node.target.id] = annotation
                if node.value:
                    func_name = self._get_import(
                        "typeguard._functions", "check_variable_assignment"
                    )
                    node.value = Call(
                        func_name,
                        [
                            node.value,
                            Constant(node.target.id),
                            annotation,
                            self._memo.get_memo_name(),
                        ],
                        [],
                    )

        return node

    def visit_Assign(self, node: Assign) -> Any:
        """
        This injects a type check into a local variable assignment within a function
        body. The variable must have been annotated earlier in the function body.

        """
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)):
            targets: list[dict[Constant, expr | None]] = []
            check_required = False
            for target in node.targets:
                elts: Sequence[expr]
                if isinstance(target, Name):
                    elts = [target]
                elif isinstance(target, Tuple):
                    elts = target.elts
                else:
                    continue

                annotations_: dict[Constant, expr | None] = {}
                for exp in elts:
                    prefix = ""
                    if isinstance(exp, Starred):
                        exp = exp.value
                        prefix = "*"

                    if isinstance(exp, Name):
                        self._memo.ignored_names.add(exp.id)
                        name = prefix + exp.id
                        annotation = self._memo.variable_annotations.get(exp.id)
                        if annotation:
                            annotations_[Constant(name)] = annotation
                            check_required = True
                        else:
                            annotations_[Constant(name)] = None

                targets.append(annotations_)

            if check_required:
                # Replace missing annotations with typing.Any
                for item in targets:
                    for key, expression in item.items():
                        if expression is None:
                            item[key] = self._get_import("typing", "Any")

                if len(targets) == 1 and len(targets[0]) == 1:
                    func_name = self._get_import(
                        "typeguard._functions", "check_variable_assignment"
                    )
                    target_varname = next(iter(targets[0]))
                    node.value = Call(
                        func_name,
                        [
                            node.value,
                            target_varname,
                            targets[0][target_varname],
                            self._memo.get_memo_name(),
                        ],
                        [],
                    )
                elif targets:
                    func_name = self._get_import(
                        "typeguard._functions", "check_multi_variable_assignment"
                    )
                    targets_arg = List(
                        [
                            Dict(keys=list(target), values=list(target.values()))
                            for target in targets
                        ],
                        ctx=Load(),
                    )
                    node.value = Call(
                        func_name,
                        [node.value, targets_arg, self._memo.get_memo_name()],
                        [],
                    )

        return node

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        """This injects a type check into an assignment expression (a := foo())."""
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)) and isinstance(
            node.target, Name
        ):
            self._memo.ignored_names.add(node.target.id)

            # Bail out if no matching annotation is found
            annotation = self._memo.variable_annotations.get(node.target.id)
            if annotation is None:
                return node

            func_name = self._get_import(
                "typeguard._functions", "check_variable_assignment"
            )
            node.value = Call(
                func_name,
                [
                    node.value,
                    Constant(node.target.id),
                    annotation,
                    self._memo.get_memo_name(),
                ],
                [],
            )

        return node

    def visit_AugAssign(self, node: AugAssign) -> Any:
        """
        This injects a type check into an augmented assignment expression (a += 1).

        """
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)) and isinstance(
            node.target, Name
        ):
            # Bail out if no matching annotation is found
            annotation = self._memo.variable_annotations.get(node.target.id)
            if annotation is None:
                return node

            # Bail out if the operator is not found (newer Python version?)
            try:
                operator_func_name = aug_assign_functions[node.op.__class__]
            except KeyError:
                return node

            operator_func = self._get_import("operator", operator_func_name)
            operator_call = Call(
                operator_func, [Name(node.target.id, ctx=Load()), node.value], []
            )
            check_call = Call(
                self._get_import("typeguard._functions", "check_variable_assignment"),
                [
                    operator_call,
                    Constant(node.target.id),
                    annotation,
                    self._memo.get_memo_name(),
                ],
                [],
            )
            return Assign(targets=[node.target], value=check_call)

        return node

    def visit_If(self, node: If) -> Any:
        """
        This blocks names from being collected from a module-level
        "if typing.TYPE_CHECKING:" block, so that they won't be type checked.

        """
        self.generic_visit(node)

        if (
            self._memo is self._module_memo
            and isinstance(node.test, Name)
            and self._memo.name_matches(node.test, "typing.TYPE_CHECKING")
        ):
            collector = NameCollector()
            collector.visit(node)
            self._memo.ignored_names.update(collector.names)

        return node

# === NexusCore/openenv\Lib\site-packages\matplotlib\quiver.py ===
"""
Support for plotting vector fields.

Presently this contains Quiver and Barb. Quiver plots an arrow in the
direction of the vector, with the size of the arrow related to the
magnitude of the vector.

Barbs are like quiver in that they point along a vector, but
the magnitude of the vector is given schematically by the presence of barbs
or flags on the barb.

This will also become a home for things such as standard
deviation ellipses, which can and will be derived very easily from
the Quiver code.
"""

import math

import numpy as np
from numpy import ma

from matplotlib import _api, cbook, _docstring
import matplotlib.artist as martist
import matplotlib.collections as mcollections
from matplotlib.patches import CirclePolygon
import matplotlib.text as mtext
import matplotlib.transforms as transforms


_quiver_doc = """
Plot a 2D field of arrows.

Call signature::

  quiver([X, Y], U, V, [C], /, **kwargs)

*X*, *Y* define the arrow locations, *U*, *V* define the arrow directions, and
*C* optionally sets the color. The arguments *X*, *Y*, *U*, *V*, *C* are
positional-only.

**Arrow length**

The default settings auto-scales the length of the arrows to a reasonable size.
To change this behavior see the *scale* and *scale_units* parameters.

**Arrow shape**

The arrow shape is determined by *width*, *headwidth*, *headlength* and
*headaxislength*. See the notes below.

**Arrow styling**

Each arrow is internally represented by a filled polygon with a default edge
linewidth of 0. As a result, an arrow is rather a filled area, not a line with
a head, and `.PolyCollection` properties like *linewidth*, *edgecolor*,
*facecolor*, etc. act accordingly.


Parameters
----------
X, Y : 1D or 2D array-like, optional
    The x and y coordinates of the arrow locations.

    If not given, they will be generated as a uniform integer meshgrid based
    on the dimensions of *U* and *V*.

    If *X* and *Y* are 1D but *U*, *V* are 2D, *X*, *Y* are expanded to 2D
    using ``X, Y = np.meshgrid(X, Y)``. In this case ``len(X)`` and ``len(Y)``
    must match the column and row dimensions of *U* and *V*.

U, V : 1D or 2D array-like
    The x and y direction components of the arrow vectors. The interpretation
    of these components (in data or in screen space) depends on *angles*.

    *U* and *V* must have the same number of elements, matching the number of
    arrow locations in *X*, *Y*. *U* and *V* may be masked. Locations masked
    in any of *U*, *V*, and *C* will not be drawn.

C : 1D or 2D array-like, optional
    Numeric data that defines the arrow colors by colormapping via *norm* and
    *cmap*.

    This does not support explicit colors. If you want to set colors directly,
    use *color* instead.  The size of *C* must match the number of arrow
    locations.

angles : {'uv', 'xy'} or array-like, default: 'uv'
    Method for determining the angle of the arrows.

    - 'uv':  Arrow directions are based on
      :ref:`display coordinates <coordinate-systems>`; i.e. a 45° angle will
      always show up as diagonal on the screen, irrespective of figure or Axes
      aspect ratio or Axes data ranges. This is useful when the arrows represent
      a quantity whose direction is not tied to the x and y data coordinates.

      If *U* == *V* the orientation of the arrow on the plot is 45 degrees
      counter-clockwise from the horizontal axis (positive to the right).

    - 'xy': Arrow direction in data coordinates, i.e. the arrows point from
      (x, y) to (x+u, y+v). This is ideal for vector fields or gradient plots
      where the arrows should directly represent movements or gradients in the
      x and y directions.

    - Arbitrary angles may be specified explicitly as an array of values
      in degrees, counter-clockwise from the horizontal axis.

      In this case *U*, *V* is only used to determine the length of the
      arrows.

      For example, ``angles=[30, 60, 90]`` will orient the arrows at 30, 60, and 90
      degrees respectively, regardless of the *U* and *V* components.

    Note: inverting a data axis will correspondingly invert the
    arrows only with ``angles='xy'``.

pivot : {'tail', 'mid', 'middle', 'tip'}, default: 'tail'
    The part of the arrow that is anchored to the *X*, *Y* grid. The arrow
    rotates about this point.

    'mid' is a synonym for 'middle'.

scale : float, optional
    Scales the length of the arrow inversely.

    Number of data values represented by one unit of arrow length on the plot.
    For example, if the data represents velocity in meters per second (m/s), the
    scale parameter determines how many meters per second correspond to one unit of
    arrow length relative to the width of the plot.
    Smaller scale parameter makes the arrow longer.

    By default, an autoscaling algorithm is used to scale the arrow length to a
    reasonable size, which is based on the average vector length and the number of
    vectors.

    The arrow length unit is given by the *scale_units* parameter.

scale_units : {'width', 'height', 'dots', 'inches', 'x', 'y', 'xy'}, default: 'width'

    The physical image unit, which is used for rendering the scaled arrow data *U*, *V*.

    The rendered arrow length is given by

        length in x direction = $\\frac{u}{\\mathrm{scale}} \\mathrm{scale_unit}$

        length in y direction = $\\frac{v}{\\mathrm{scale}} \\mathrm{scale_unit}$

    For example, ``(u, v) = (0.5, 0)`` with ``scale=10, scale_unit="width"`` results
    in a horizontal arrow with a length of *0.5 / 10 * "width"*, i.e. 0.05 times the
    Axes width.

    Supported values are:

    - 'width' or 'height': The arrow length is scaled relative to the width or height
       of the Axes.
       For example, ``scale_units='width', scale=1.0``, will result in an arrow length
       of width of the Axes.

    - 'dots': The arrow length of the arrows is in measured in display dots (pixels).

    - 'inches': Arrow lengths are scaled based on the DPI (dots per inch) of the figure.
       This ensures that the arrows have a consistent physical size on the figure,
       in inches, regardless of data values or plot scaling.
       For example, ``(u, v) = (1, 0)`` with ``scale_units='inches', scale=2`` results
       in a 0.5 inch-long arrow.

    - 'x' or 'y': The arrow length is scaled relative to the x or y axis units.
       For example, ``(u, v) = (0, 1)`` with ``scale_units='x', scale=1`` results
       in a vertical arrow with the length of 1 x-axis unit.

    - 'xy': Arrow length will be same as 'x' or 'y' units.
       This is useful for creating vectors in the x-y plane where u and v have
       the same units as x and y. To plot vectors in the x-y plane with u and v having
       the same units as x and y, use ``angles='xy', scale_units='xy', scale=1``.

    Note: Setting *scale_units* without setting scale does not have any effect because
    the scale units only differ by a constant factor and that is rescaled through
    autoscaling.

units : {'width', 'height', 'dots', 'inches', 'x', 'y', 'xy'}, default: 'width'
    Affects the arrow size (except for the length). In particular, the shaft
    *width* is measured in multiples of this unit.

    Supported values are:

    - 'width', 'height': The width or height of the Axes.
    - 'dots', 'inches': Pixels or inches based on the figure dpi.
    - 'x', 'y', 'xy': *X*, *Y* or :math:`\\sqrt{X^2 + Y^2}` in data units.

    The following table summarizes how these values affect the visible arrow
    size under zooming and figure size changes:

    =================  =================   ==================
    units              zoom                figure size change
    =================  =================   ==================
    'x', 'y', 'xy'     arrow size scales   —
    'width', 'height'  —                   arrow size scales
    'dots', 'inches'   —                   —
    =================  =================   ==================

width : float, optional
    Shaft width in arrow units. All head parameters are relative to *width*.

    The default depends on choice of *units* above, and number of vectors;
    a typical starting value is about 0.005 times the width of the plot.

headwidth : float, default: 3
    Head width as multiple of shaft *width*. See the notes below.

headlength : float, default: 5
    Head length as multiple of shaft *width*. See the notes below.

headaxislength : float, default: 4.5
    Head length at shaft intersection as multiple of shaft *width*.
    See the notes below.

minshaft : float, default: 1
    Length below which arrow scales, in units of head length. Do not
    set this to less than 1, or small arrows will look terrible!

minlength : float, default: 1
    Minimum length as a multiple of shaft width; if an arrow length
    is less than this, plot a dot (hexagon) of this diameter instead.

color : :mpltype:`color` or list :mpltype:`color`, optional
    Explicit color(s) for the arrows. If *C* has been set, *color* has no
    effect.

    This is a synonym for the `.PolyCollection` *facecolor* parameter.

Other Parameters
----------------
data : indexable object, optional
    DATA_PARAMETER_PLACEHOLDER

**kwargs : `~matplotlib.collections.PolyCollection` properties, optional
    All other keyword arguments are passed on to `.PolyCollection`:

    %(PolyCollection:kwdoc)s

Returns
-------
`~matplotlib.quiver.Quiver`

See Also
--------
.Axes.quiverkey : Add a key to a quiver plot.

Notes
-----

**Arrow shape**

The arrow is drawn as a polygon using the nodes as shown below. The values
*headwidth*, *headlength*, and *headaxislength* are in units of *width*.

.. image:: /_static/quiver_sizes.svg
   :width: 500px

The defaults give a slightly swept-back arrow. Here are some guidelines how to
get other head shapes:

- To make the head a triangle, make *headaxislength* the same as *headlength*.
- To make the arrow more pointed, reduce *headwidth* or increase *headlength*
  and *headaxislength*.
- To make the head smaller relative to the shaft, scale down all the head
  parameters proportionally.
- To remove the head completely, set all *head* parameters to 0.
- To get a diamond-shaped head, make *headaxislength* larger than *headlength*.
- Warning: For *headaxislength* < (*headlength* / *headwidth*), the "headaxis"
  nodes (i.e. the ones connecting the head with the shaft) will protrude out
  of the head in forward direction so that the arrow head looks broken.
""" % _docstring.interpd.params

_docstring.interpd.register(quiver_doc=_quiver_doc)


class QuiverKey(martist.Artist):
    """Labelled arrow for use as a quiver plot scale key."""
    halign = {'N': 'center', 'S': 'center', 'E': 'left', 'W': 'right'}
    valign = {'N': 'bottom', 'S': 'top', 'E': 'center', 'W': 'center'}
    pivot = {'N': 'middle', 'S': 'middle', 'E': 'tip', 'W': 'tail'}

    def __init__(self, Q, X, Y, U, label,
                 *, angle=0, coordinates='axes', color=None, labelsep=0.1,
                 labelpos='N', labelcolor=None, fontproperties=None,
                 zorder=None, **kwargs):
        """
        Add a key to a quiver plot.

        The positioning of the key depends on *X*, *Y*, *coordinates*, and
        *labelpos*.  If *labelpos* is 'N' or 'S', *X*, *Y* give the position of
        the middle of the key arrow.  If *labelpos* is 'E', *X*, *Y* positions
        the head, and if *labelpos* is 'W', *X*, *Y* positions the tail; in
        either of these two cases, *X*, *Y* is somewhere in the middle of the
        arrow+label key object.

        Parameters
        ----------
        Q : `~matplotlib.quiver.Quiver`
            A `.Quiver` object as returned by a call to `~.Axes.quiver()`.
        X, Y : float
            The location of the key.
        U : float
            The length of the key.
        label : str
            The key label (e.g., length and units of the key).
        angle : float, default: 0
            The angle of the key arrow, in degrees anti-clockwise from the
            horizontal axis.
        coordinates : {'axes', 'figure', 'data', 'inches'}, default: 'axes'
            Coordinate system and units for *X*, *Y*: 'axes' and 'figure' are
            normalized coordinate systems with (0, 0) in the lower left and
            (1, 1) in the upper right; 'data' are the axes data coordinates
            (used for the locations of the vectors in the quiver plot itself);
            'inches' is position in the figure in inches, with (0, 0) at the
            lower left corner.
        color : :mpltype:`color`
            Overrides face and edge colors from *Q*.
        labelpos : {'N', 'S', 'E', 'W'}
            Position the label above, below, to the right, to the left of the
            arrow, respectively.
        labelsep : float, default: 0.1
            Distance in inches between the arrow and the label.
        labelcolor : :mpltype:`color`, default: :rc:`text.color`
            Label color.
        fontproperties : dict, optional
            A dictionary with keyword arguments accepted by the
            `~matplotlib.font_manager.FontProperties` initializer:
            *family*, *style*, *variant*, *size*, *weight*.
        zorder : float
            The zorder of the key. The default is 0.1 above *Q*.
        **kwargs
            Any additional keyword arguments are used to override vector
            properties taken from *Q*.
        """
        super().__init__()
        self.Q = Q
        self.X = X
        self.Y = Y
        self.U = U
        self.angle = angle
        self.coord = coordinates
        self.color = color
        self.label = label
        self._labelsep_inches = labelsep

        self.labelpos = labelpos
        self.labelcolor = labelcolor
        self.fontproperties = fontproperties or dict()
        self.kw = kwargs
        self.text = mtext.Text(
            text=label,
            horizontalalignment=self.halign[self.labelpos],
            verticalalignment=self.valign[self.labelpos],
            fontproperties=self.fontproperties)
        if self.labelcolor is not None:
            self.text.set_color(self.labelcolor)
        self._dpi_at_last_init = None
        self.zorder = zorder if zorder is not None else Q.zorder + 0.1

    @property
    def labelsep(self):
        return self._labelsep_inches * self.Q.axes.get_figure(root=True).dpi

    def _init(self):
        if True:  # self._dpi_at_last_init != self.axes.get_figure().dpi
            if self.Q._dpi_at_last_init != self.Q.axes.get_figure(root=True).dpi:
                self.Q._init()
            self._set_transform()
            with cbook._setattr_cm(self.Q, pivot=self.pivot[self.labelpos],
                                   # Hack: save and restore the Umask
                                   Umask=ma.nomask):
                u = self.U * np.cos(np.radians(self.angle))
                v = self.U * np.sin(np.radians(self.angle))
                self.verts = self.Q._make_verts([[0., 0.]],
                                                np.array([u]), np.array([v]), 'uv')
            kwargs = self.Q.polykw
            kwargs.update(self.kw)
            self.vector = mcollections.PolyCollection(
                self.verts,
                offsets=[(self.X, self.Y)],
                offset_transform=self.get_transform(),
                **kwargs)
            if self.color is not None:
                self.vector.set_color(self.color)
            self.vector.set_transform(self.Q.get_transform())
            self.vector.set_figure(self.get_figure())
            self._dpi_at_last_init = self.Q.axes.get_figure(root=True).dpi

    def _text_shift(self):
        return {
            "N": (0, +self.labelsep),
            "S": (0, -self.labelsep),
            "E": (+self.labelsep, 0),
            "W": (-self.labelsep, 0),
        }[self.labelpos]

    @martist.allow_rasterization
    def draw(self, renderer):
        self._init()
        self.vector.draw(renderer)
        pos = self.get_transform().transform((self.X, self.Y))
        self.text.set_position(pos + self._text_shift())
        self.text.draw(renderer)
        self.stale = False

    def _set_transform(self):
        fig = self.Q.axes.get_figure(root=False)
        self.set_transform(_api.check_getitem({
            "data": self.Q.axes.transData,
            "axes": self.Q.axes.transAxes,
            "figure": fig.transFigure,
            "inches": fig.dpi_scale_trans,
        }, coordinates=self.coord))

    def set_figure(self, fig):
        super().set_figure(fig)
        self.text.set_figure(fig)

    def contains(self, mouseevent):
        if self._different_canvas(mouseevent):
            return False, {}
        # Maybe the dictionary should allow one to
        # distinguish between a text hit and a vector hit.
        if (self.text.contains(mouseevent)[0] or
                self.vector.contains(mouseevent)[0]):
            return True, {}
        return False, {}


def _parse_args(*args, caller_name='function'):
    """
    Helper function to parse positional parameters for colored vector plots.

    This is currently used for Quiver and Barbs.

    Parameters
    ----------
    *args : list
        list of 2-5 arguments. Depending on their number they are parsed to::

            U, V
            U, V, C
            X, Y, U, V
            X, Y, U, V, C

    caller_name : str
        Name of the calling method (used in error messages).
    """
    X = Y = C = None

    nargs = len(args)
    if nargs == 2:
        # The use of atleast_1d allows for handling scalar arguments while also
        # keeping masked arrays
        U, V = np.atleast_1d(*args)
    elif nargs == 3:
        U, V, C = np.atleast_1d(*args)
    elif nargs == 4:
        X, Y, U, V = np.atleast_1d(*args)
    elif nargs == 5:
        X, Y, U, V, C = np.atleast_1d(*args)
    else:
        raise _api.nargs_error(caller_name, takes="from 2 to 5", given=nargs)

    nr, nc = (1, U.shape[0]) if U.ndim == 1 else U.shape

    if X is not None:
        X = X.ravel()
        Y = Y.ravel()
        if len(X) == nc and len(Y) == nr:
            X, Y = (a.ravel() for a in np.meshgrid(X, Y))
        elif len(X) != len(Y):
            raise ValueError('X and Y must be the same size, but '
                             f'X.size is {X.size} and Y.size is {Y.size}.')
    else:
        indexgrid = np.meshgrid(np.arange(nc), np.arange(nr))
        X, Y = (np.ravel(a) for a in indexgrid)
    # Size validation for U, V, C is left to the set_UVC method.
    return X, Y, U, V, C


def _check_consistent_shapes(*arrays):
    all_shapes = {a.shape for a in arrays}
    if len(all_shapes) != 1:
        raise ValueError('The shapes of the passed in arrays do not match')


class Quiver(mcollections.PolyCollection):
    """
    Specialized PolyCollection for arrows.

    The only API method is set_UVC(), which can be used
    to change the size, orientation, and color of the
    arrows; their locations are fixed when the class is
    instantiated.  Possibly this method will be useful
    in animations.

    Much of the work in this class is done in the draw()
    method so that as much information as possible is available
    about the plot.  In subsequent draw() calls, recalculation
    is limited to things that might have changed, so there
    should be no performance penalty from putting the calculations
    in the draw() method.
    """

    _PIVOT_VALS = ('tail', 'middle', 'tip')

    @_docstring.Substitution(_quiver_doc)
    def __init__(self, ax, *args,
                 scale=None, headwidth=3, headlength=5, headaxislength=4.5,
                 minshaft=1, minlength=1, units='width', scale_units=None,
                 angles='uv', width=None, color='k', pivot='tail', **kwargs):
        """
        The constructor takes one required argument, an Axes
        instance, followed by the args and kwargs described
        by the following pyplot interface documentation:
        %s
        """
        self._axes = ax  # The attr actually set by the Artist.axes property.
        X, Y, U, V, C = _parse_args(*args, caller_name='quiver')
        self.X = X
        self.Y = Y
        self.XY = np.column_stack((X, Y))
        self.N = len(X)
        self.scale = scale
        self.headwidth = headwidth
        self.headlength = float(headlength)
        self.headaxislength = headaxislength
        self.minshaft = minshaft
        self.minlength = minlength
        self.units = units
        self.scale_units = scale_units
        self.angles = angles
        self.width = width

        if pivot.lower() == 'mid':
            pivot = 'middle'
        self.pivot = pivot.lower()
        _api.check_in_list(self._PIVOT_VALS, pivot=self.pivot)

        self.transform = kwargs.pop('transform', ax.transData)
        kwargs.setdefault('facecolors', color)
        kwargs.setdefault('linewidths', (0,))
        super().__init__([], offsets=self.XY, offset_transform=self.transform,
                         closed=False, **kwargs)
        self.polykw = kwargs
        self.set_UVC(U, V, C)
        self._dpi_at_last_init = None

    def _init(self):
        """
        Initialization delayed until first draw;
        allow time for axes setup.
        """
        # It seems that there are not enough event notifications
        # available to have this work on an as-needed basis at present.
        if True:  # self._dpi_at_last_init != self.axes.figure.dpi
            trans = self._set_transform()
            self.span = trans.inverted().transform_bbox(self.axes.bbox).width
            if self.width is None:
                sn = np.clip(math.sqrt(self.N), 8, 25)
                self.width = 0.06 * self.span / sn

            # _make_verts sets self.scale if not already specified
            if (self._dpi_at_last_init != self.axes.get_figure(root=True).dpi
                    and self.scale is None):
                self._make_verts(self.XY, self.U, self.V, self.angles)

            self._dpi_at_last_init = self.axes.get_figure(root=True).dpi

    def get_datalim(self, transData):
        trans = self.get_transform()
        offset_trf = self.get_offset_transform()
        full_transform = (trans - transData) + (offset_trf - transData)
        XY = full_transform.transform(self.XY)
        bbox = transforms.Bbox.null()
        bbox.update_from_data_xy(XY, ignore=True)
        return bbox

    @martist.allow_rasterization
    def draw(self, renderer):
        self._init()
        verts = self._make_verts(self.XY, self.U, self.V, self.angles)
        self.set_verts(verts, closed=False)
        super().draw(renderer)
        self.stale = False

    def set_UVC(self, U, V, C=None):
        # We need to ensure we have a copy, not a reference
        # to an array that might change before draw().
        U = ma.masked_invalid(U, copy=True).ravel()
        V = ma.masked_invalid(V, copy=True).ravel()
        if C is not None:
            C = ma.masked_invalid(C, copy=True).ravel()
        for name, var in zip(('U', 'V', 'C'), (U, V, C)):
            if not (var is None or var.size == self.N or var.size == 1):
                raise ValueError(f'Argument {name} has a size {var.size}'
                                 f' which does not match {self.N},'
                                 ' the number of arrow positions')

        mask = ma.mask_or(U.mask, V.mask, copy=False, shrink=True)
        if C is not None:
            mask = ma.mask_or(mask, C.mask, copy=False, shrink=True)
            if mask is ma.nomask:
                C = C.filled()
            else:
                C = ma.array(C, mask=mask, copy=False)
        self.U = U.filled(1)
        self.V = V.filled(1)
        self.Umask = mask
        if C is not None:
            self.set_array(C)
        self.stale = True

    def _dots_per_unit(self, units):
        """Return a scale factor for converting from units to pixels."""
        bb = self.axes.bbox
        vl = self.axes.viewLim
        return _api.check_getitem({
            'x': bb.width / vl.width,
            'y': bb.height / vl.height,
            'xy': np.hypot(*bb.size) / np.hypot(*vl.size),
            'width': bb.width,
            'height': bb.height,
            'dots': 1.,
            'inches': self.axes.get_figure(root=True).dpi,
        }, units=units)

    def _set_transform(self):
        """
        Set the PolyCollection transform to go
        from arrow width units to pixels.
        """
        dx = self._dots_per_unit(self.units)
        self._trans_scale = dx  # pixels per arrow width unit
        trans = transforms.Affine2D().scale(dx)
        self.set_transform(trans)
        return trans

    # Calculate angles and lengths for segment between (x, y), (x+u, y+v)
    def _angles_lengths(self, XY, U, V, eps=1):
        xy = self.axes.transData.transform(XY)
        uv = np.column_stack((U, V))
        xyp = self.axes.transData.transform(XY + eps * uv)
        dxy = xyp - xy
        angles = np.arctan2(dxy[:, 1], dxy[:, 0])
        lengths = np.hypot(*dxy.T) / eps
        return angles, lengths

    # XY is stacked [X, Y].
    # See quiver() doc for meaning of X, Y, U, V, angles.
    def _make_verts(self, XY, U, V, angles):
        uv = (U + V * 1j)
        str_angles = angles if isinstance(angles, str) else ''
        if str_angles == 'xy' and self.scale_units == 'xy':
            # Here eps is 1 so that if we get U, V by diffing
            # the X, Y arrays, the vectors will connect the
            # points, regardless of the axis scaling (including log).
            angles, lengths = self._angles_lengths(XY, U, V, eps=1)
        elif str_angles == 'xy' or self.scale_units == 'xy':
            # Calculate eps based on the extents of the plot
            # so that we don't end up with roundoff error from
            # adding a small number to a large.
            eps = np.abs(self.axes.dataLim.extents).max() * 0.001
            angles, lengths = self._angles_lengths(XY, U, V, eps=eps)

        if str_angles and self.scale_units == 'xy':
            a = lengths
        else:
            a = np.abs(uv)

        if self.scale is None:
            sn = max(10, math.sqrt(self.N))
            if self.Umask is not ma.nomask:
                amean = a[~self.Umask].mean()
            else:
                amean = a.mean()
            # crude auto-scaling
            # scale is typical arrow length as a multiple of the arrow width
            scale = 1.8 * amean * sn / self.span

        if self.scale_units is None:
            if self.scale is None:
                self.scale = scale
            widthu_per_lenu = 1.0
        else:
            if self.scale_units == 'xy':
                dx = 1
            else:
                dx = self._dots_per_unit(self.scale_units)
            widthu_per_lenu = dx / self._trans_scale
            if self.scale is None:
                self.scale = scale * widthu_per_lenu
        length = a * (widthu_per_lenu / (self.scale * self.width))
        X, Y = self._h_arrows(length)
        if str_angles == 'xy':
            theta = angles
        elif str_angles == 'uv':
            theta = np.angle(uv)
        else:
            theta = ma.masked_invalid(np.deg2rad(angles)).filled(0)
        theta = theta.reshape((-1, 1))  # for broadcasting
        xy = (X + Y * 1j) * np.exp(1j * theta) * self.width
        XY = np.stack((xy.real, xy.imag), axis=2)
        if self.Umask is not ma.nomask:
            XY = ma.array(XY)
            XY[self.Umask] = ma.masked
            # This might be handled more efficiently with nans, given
            # that nans will end up in the paths anyway.

        return XY

    def _h_arrows(self, length):
        """Length is in arrow width units."""
        # It might be possible to streamline the code
        # and speed it up a bit by using complex (x, y)
        # instead of separate arrays; but any gain would be slight.
        minsh = self.minshaft * self.headlength
        N = len(length)
        length = length.reshape(N, 1)
        # This number is chosen based on when pixel values overflow in Agg
        # causing rendering errors
        # length = np.minimum(length, 2 ** 16)
        np.clip(length, 0, 2 ** 16, out=length)
        # x, y: normal horizontal arrow
        x = np.array([0, -self.headaxislength,
                      -self.headlength, 0],
                     np.float64)
        x = x + np.array([0, 1, 1, 1]) * length
        y = 0.5 * np.array([1, 1, self.headwidth, 0], np.float64)
        y = np.repeat(y[np.newaxis, :], N, axis=0)
        # x0, y0: arrow without shaft, for short vectors
        x0 = np.array([0, minsh - self.headaxislength,
                       minsh - self.headlength, minsh], np.float64)
        y0 = 0.5 * np.array([1, 1, self.headwidth, 0], np.float64)
        ii = [0, 1, 2, 3, 2, 1, 0, 0]
        X = x[:, ii]
        Y = y[:, ii]
        Y[:, 3:-1] *= -1
        X0 = x0[ii]
        Y0 = y0[ii]
        Y0[3:-1] *= -1
        shrink = length / minsh if minsh != 0. else 0.
        X0 = shrink * X0[np.newaxis, :]
        Y0 = shrink * Y0[np.newaxis, :]
        short = np.repeat(length < minsh, 8, axis=1)
        # Now select X0, Y0 if short, otherwise X, Y
        np.copyto(X, X0, where=short)
        np.copyto(Y, Y0, where=short)
        if self.pivot == 'middle':
            X -= 0.5 * X[:, 3, np.newaxis]
        elif self.pivot == 'tip':
            # numpy bug? using -= does not work here unless we multiply by a
            # float first, as with 'mid'.
            X = X - X[:, 3, np.newaxis]
        elif self.pivot != 'tail':
            _api.check_in_list(["middle", "tip", "tail"], pivot=self.pivot)

        tooshort = length < self.minlength
        if tooshort.any():
            # Use a heptagonal dot:
            th = np.arange(0, 8, 1, np.float64) * (np.pi / 3.0)
            x1 = np.cos(th) * self.minlength * 0.5
            y1 = np.sin(th) * self.minlength * 0.5
            X1 = np.repeat(x1[np.newaxis, :], N, axis=0)
            Y1 = np.repeat(y1[np.newaxis, :], N, axis=0)
            tooshort = np.repeat(tooshort, 8, 1)
            np.copyto(X, X1, where=tooshort)
            np.copyto(Y, Y1, where=tooshort)
        # Mask handling is deferred to the caller, _make_verts.
        return X, Y


_barbs_doc = r"""
Plot a 2D field of wind barbs.

Call signature::

  barbs([X, Y], U, V, [C], /, **kwargs)

Where *X*, *Y* define the barb locations, *U*, *V* define the barb
directions, and *C* optionally sets the color.

The arguments *X*, *Y*, *U*, *V*, *C* are positional-only and may be
1D or 2D. *U*, *V*, *C* may be masked arrays, but masked *X*, *Y*
are not supported at present.

Barbs are traditionally used in meteorology as a way to plot the speed
and direction of wind observations, but can technically be used to
plot any two dimensional vector quantity.  As opposed to arrows, which
give vector magnitude by the length of the arrow, the barbs give more
quantitative information about the vector magnitude by putting slanted
lines or a triangle for various increments in magnitude, as show
schematically below::

  :                   /\    \
  :                  /  \    \
  :                 /    \    \    \
  :                /      \    \    \
  :               ------------------------------

The largest increment is given by a triangle (or "flag"). After those
come full lines (barbs). The smallest increment is a half line.  There
is only, of course, ever at most 1 half line.  If the magnitude is
small and only needs a single half-line and no full lines or
triangles, the half-line is offset from the end of the barb so that it
can be easily distinguished from barbs with a single full line.  The
magnitude for the barb shown above would nominally be 65, using the
standard increments of 50, 10, and 5.

See also https://en.wikipedia.org/wiki/Wind_barb.

Parameters
----------
X, Y : 1D or 2D array-like, optional
    The x and y coordinates of the barb locations. See *pivot* for how the
    barbs are drawn to the x, y positions.

    If not given, they will be generated as a uniform integer meshgrid based
    on the dimensions of *U* and *V*.

    If *X* and *Y* are 1D but *U*, *V* are 2D, *X*, *Y* are expanded to 2D
    using ``X, Y = np.meshgrid(X, Y)``. In this case ``len(X)`` and ``len(Y)``
    must match the column and row dimensions of *U* and *V*.

U, V : 1D or 2D array-like
    The x and y components of the barb shaft.

C : 1D or 2D array-like, optional
    Numeric data that defines the barb colors by colormapping via *norm* and
    *cmap*.

    This does not support explicit colors. If you want to set colors directly,
    use *barbcolor* instead.

length : float, default: 7
    Length of the barb in points; the other parts of the barb
    are scaled against this.

pivot : {'tip', 'middle'} or float, default: 'tip'
    The part of the arrow that is anchored to the *X*, *Y* grid. The barb
    rotates about this point. This can also be a number, which shifts the
    start of the barb that many points away from grid point.

barbcolor : :mpltype:`color` or color sequence
    The color of all parts of the barb except for the flags.  This parameter
    is analogous to the *edgecolor* parameter for polygons, which can be used
    instead. However this parameter will override facecolor.

flagcolor : :mpltype:`color` or color sequence
    The color of any flags on the barb.  This parameter is analogous to the
    *facecolor* parameter for polygons, which can be used instead. However,
    this parameter will override facecolor.  If this is not set (and *C* has
    not either) then *flagcolor* will be set to match *barbcolor* so that the
    barb has a uniform color. If *C* has been set, *flagcolor* has no effect.

sizes : dict, optional
    A dictionary of coefficients specifying the ratio of a given
    feature to the length of the barb. Only those values one wishes to
    override need to be included.  These features include:

    - 'spacing' - space between features (flags, full/half barbs)
    - 'height' - height (distance from shaft to top) of a flag or full barb
    - 'width' - width of a flag, twice the width of a full barb
    - 'emptybarb' - radius of the circle used for low magnitudes

fill_empty : bool, default: False
    Whether the empty barbs (circles) that are drawn should be filled with
    the flag color.  If they are not filled, the center is transparent.

rounding : bool, default: True
    Whether the vector magnitude should be rounded when allocating barb
    components.  If True, the magnitude is rounded to the nearest multiple
    of the half-barb increment.  If False, the magnitude is simply truncated
    to the next lowest multiple.

barb_increments : dict, optional
    A dictionary of increments specifying values to associate with
    different parts of the barb. Only those values one wishes to
    override need to be included.

    - 'half' - half barbs (Default is 5)
    - 'full' - full barbs (Default is 10)
    - 'flag' - flags (default is 50)

flip_barb : bool or array-like of bool, default: False
    Whether the lines and flags should point opposite to normal.
    Normal behavior is for the barbs and lines to point right (comes from wind
    barbs having these features point towards low pressure in the Northern
    Hemisphere).

    A single value is applied to all barbs. Individual barbs can be flipped by
    passing a bool array of the same size as *U* and *V*.

Returns
-------
barbs : `~matplotlib.quiver.Barbs`

Other Parameters
----------------
data : indexable object, optional
    DATA_PARAMETER_PLACEHOLDER

**kwargs
    The barbs can further be customized using `.PolyCollection` keyword
    arguments:

    %(PolyCollection:kwdoc)s
""" % _docstring.interpd.params

_docstring.interpd.register(barbs_doc=_barbs_doc)


class Barbs(mcollections.PolyCollection):
    """
    Specialized PolyCollection for barbs.

    The only API method is :meth:`set_UVC`, which can be used to
    change the size, orientation, and color of the arrows.  Locations
    are changed using the :meth:`set_offsets` collection method.
    Possibly this method will be useful in animations.

    There is one internal function :meth:`_find_tails` which finds
    exactly what should be put on the barb given the vector magnitude.
    From there :meth:`_make_barbs` is used to find the vertices of the
    polygon to represent the barb based on this information.
    """

    # This may be an abuse of polygons here to render what is essentially maybe
    # 1 triangle and a series of lines.  It works fine as far as I can tell
    # however.

    @_docstring.interpd
    def __init__(self, ax, *args,
                 pivot='tip', length=7, barbcolor=None, flagcolor=None,
                 sizes=None, fill_empty=False, barb_increments=None,
                 rounding=True, flip_barb=False, **kwargs):
        """
        The constructor takes one required argument, an Axes
        instance, followed by the args and kwargs described
        by the following pyplot interface documentation:
        %(barbs_doc)s
        """
        self.sizes = sizes or dict()
        self.fill_empty = fill_empty
        self.barb_increments = barb_increments or dict()
        self.rounding = rounding
        self.flip = np.atleast_1d(flip_barb)
        transform = kwargs.pop('transform', ax.transData)
        self._pivot = pivot
        self._length = length

        # Flagcolor and barbcolor provide convenience parameters for
        # setting the facecolor and edgecolor, respectively, of the barb
        # polygon.  We also work here to make the flag the same color as the
        # rest of the barb by default

        if None in (barbcolor, flagcolor):
            kwargs['edgecolors'] = 'face'
            if flagcolor:
                kwargs['facecolors'] = flagcolor
            elif barbcolor:
                kwargs['facecolors'] = barbcolor
            else:
                # Set to facecolor passed in or default to black
                kwargs.setdefault('facecolors', 'k')
        else:
            kwargs['edgecolors'] = barbcolor
            kwargs['facecolors'] = flagcolor

        # Explicitly set a line width if we're not given one, otherwise
        # polygons are not outlined and we get no barbs
        if 'linewidth' not in kwargs and 'lw' not in kwargs:
            kwargs['linewidth'] = 1

        # Parse out the data arrays from the various configurations supported
        x, y, u, v, c = _parse_args(*args, caller_name='barbs')
        self.x = x
        self.y = y
        xy = np.column_stack((x, y))

        # Make a collection
        barb_size = self._length ** 2 / 4  # Empirically determined
        super().__init__(
            [], (barb_size,), offsets=xy, offset_transform=transform, **kwargs)
        self.set_transform(transforms.IdentityTransform())

        self.set_UVC(u, v, c)

    def _find_tails(self, mag, rounding=True, half=5, full=10, flag=50):
        """
        Find how many of each of the tail pieces is necessary.

        Parameters
        ----------
        mag : `~numpy.ndarray`
            Vector magnitudes; must be non-negative (and an actual ndarray).
        rounding : bool, default: True
            Whether to round or to truncate to the nearest half-barb.
        half, full, flag : float, defaults: 5, 10, 50
            Increments for a half-barb, a barb, and a flag.

        Returns
        -------
        n_flags, n_barbs : int array
            For each entry in *mag*, the number of flags and barbs.
        half_flag : bool array
            For each entry in *mag*, whether a half-barb is needed.
        empty_flag : bool array
            For each entry in *mag*, whether nothing is drawn.
        """
        # If rounding, round to the nearest multiple of half, the smallest
        # increment
        if rounding:
            mag = half * np.around(mag / half)
        n_flags, mag = divmod(mag, flag)
        n_barb, mag = divmod(mag, full)
        half_flag = mag >= half
        empty_flag = ~(half_flag | (n_flags > 0) | (n_barb > 0))
        return n_flags.astype(int), n_barb.astype(int), half_flag, empty_flag

    def _make_barbs(self, u, v, nflags, nbarbs, half_barb, empty_flag, length,
                    pivot, sizes, fill_empty, flip):
        """
        Create the wind barbs.

        Parameters
        ----------
        u, v
            Components of the vector in the x and y directions, respectively.

        nflags, nbarbs, half_barb, empty_flag
            Respectively, the number of flags, number of barbs, flag for
            half a barb, and flag for empty barb, ostensibly obtained from
            :meth:`_find_tails`.

        length
            The length of the barb staff in points.

        pivot : {"tip", "middle"} or number
            The point on the barb around which the entire barb should be
            rotated.  If a number, the start of the barb is shifted by that
            many points from the origin.

        sizes : dict
            Coefficients specifying the ratio of a given feature to the length
            of the barb. These features include:

            - *spacing*: space between features (flags, full/half barbs).
            - *height*: distance from shaft of top of a flag or full barb.
            - *width*: width of a flag, twice the width of a full barb.
            - *emptybarb*: radius of the circle used for low magnitudes.

        fill_empty : bool
            Whether the circle representing an empty barb should be filled or
            not (this changes the drawing of the polygon).

        flip : list of bool
            Whether the features should be flipped to the other side of the
            barb (useful for winds in the southern hemisphere).

        Returns
        -------
        list of arrays of vertices
            Polygon vertices for each of the wind barbs.  These polygons have
            been rotated to properly align with the vector direction.
        """

        # These control the spacing and size of barb elements relative to the
        # length of the shaft
        spacing = length * sizes.get('spacing', 0.125)
        full_height = length * sizes.get('height', 0.4)
        full_width = length * sizes.get('width', 0.25)
        empty_rad = length * sizes.get('emptybarb', 0.15)

        # Controls y point where to pivot the barb.
        pivot_points = dict(tip=0.0, middle=-length / 2.)

        endx = 0.0
        try:
            endy = float(pivot)
        except ValueError:
            endy = pivot_points[pivot.lower()]

        # Get the appropriate angle for the vector components.  The offset is
        # due to the way the barb is initially drawn, going down the y-axis.
        # This makes sense in a meteorological mode of thinking since there 0
        # degrees corresponds to north (the y-axis traditionally)
        angles = -(ma.arctan2(v, u) + np.pi / 2)

        # Used for low magnitude.  We just get the vertices, so if we make it
        # out here, it can be reused.  The center set here should put the
        # center of the circle at the location(offset), rather than at the
        # same point as the barb pivot; this seems more sensible.
        circ = CirclePolygon((0, 0), radius=empty_rad).get_verts()
        if fill_empty:
            empty_barb = circ
        else:
            # If we don't want the empty one filled, we make a degenerate
            # polygon that wraps back over itself
            empty_barb = np.concatenate((circ, circ[::-1]))

        barb_list = []
        for index, angle in np.ndenumerate(angles):
            # If the vector magnitude is too weak to draw anything, plot an
            # empty circle instead
            if empty_flag[index]:
                # We can skip the transform since the circle has no preferred
                # orientation
                barb_list.append(empty_barb)
                continue

            poly_verts = [(endx, endy)]
            offset = length

            # Handle if this barb should be flipped
            barb_height = -full_height if flip[index] else full_height

            # Add vertices for each flag
            for i in range(nflags[index]):
                # The spacing that works for the barbs is a little to much for
                # the flags, but this only occurs when we have more than 1
                # flag.
                if offset != length:
                    offset += spacing / 2.
                poly_verts.extend(
                    [[endx, endy + offset],
                     [endx + barb_height, endy - full_width / 2 + offset],
                     [endx, endy - full_width + offset]])

                offset -= full_width + spacing

            # Add vertices for each barb.  These really are lines, but works
            # great adding 3 vertices that basically pull the polygon out and
            # back down the line
            for i in range(nbarbs[index]):
                poly_verts.extend(
                    [(endx, endy + offset),
                     (endx + barb_height, endy + offset + full_width / 2),
                     (endx, endy + offset)])

                offset -= spacing

            # Add the vertices for half a barb, if needed
            if half_barb[index]:
                # If the half barb is the first on the staff, traditionally it
                # is offset from the end to make it easy to distinguish from a
                # barb with a full one
                if offset == length:
                    poly_verts.append((endx, endy + offset))
                    offset -= 1.5 * spacing
                poly_verts.extend(
                    [(endx, endy + offset),
                     (endx + barb_height / 2, endy + offset + full_width / 4),
                     (endx, endy + offset)])

            # Rotate the barb according the angle. Making the barb first and
            # then rotating it made the math for drawing the barb really easy.
            # Also, the transform framework makes doing the rotation simple.
            poly_verts = transforms.Affine2D().rotate(-angle).transform(
                poly_verts)
            barb_list.append(poly_verts)

        return barb_list

    def set_UVC(self, U, V, C=None):
        # We need to ensure we have a copy, not a reference to an array that
        # might change before draw().
        self.u = ma.masked_invalid(U, copy=True).ravel()
        self.v = ma.masked_invalid(V, copy=True).ravel()

        # Flip needs to have the same number of entries as everything else.
        # Use broadcast_to to avoid a bloated array of identical values.
        # (can't rely on actual broadcasting)
        if len(self.flip) == 1:
            flip = np.broadcast_to(self.flip, self.u.shape)
        else:
            flip = self.flip

        if C is not None:
            c = ma.masked_invalid(C, copy=True).ravel()
            x, y, u, v, c, flip = cbook.delete_masked_points(
                self.x.ravel(), self.y.ravel(), self.u, self.v, c,
                flip.ravel())
            _check_consistent_shapes(x, y, u, v, c, flip)
        else:
            x, y, u, v, flip = cbook.delete_masked_points(
                self.x.ravel(), self.y.ravel(), self.u, self.v, flip.ravel())
            _check_consistent_shapes(x, y, u, v, flip)

        magnitude = np.hypot(u, v)
        flags, barbs, halves, empty = self._find_tails(
            magnitude, self.rounding, **self.barb_increments)

        # Get the vertices for each of the barbs

        plot_barbs = self._make_barbs(u, v, flags, barbs, halves, empty,
                                      self._length, self._pivot, self.sizes,
                                      self.fill_empty, flip)
        self.set_verts(plot_barbs)

        # Set the color array
        if C is not None:
            self.set_array(c)

        # Update the offsets in case the masked data changed
        xy = np.column_stack((x, y))
        self._offsets = xy
        self.stale = True

    def set_offsets(self, xy):
        """
        Set the offsets for the barb polygons.  This saves the offsets passed
        in and masks them as appropriate for the existing U/V data.

        Parameters
        ----------
        xy : sequence of pairs of floats
        """
        self.x = xy[:, 0]
        self.y = xy[:, 1]
        x, y, u, v = cbook.delete_masked_points(
            self.x.ravel(), self.y.ravel(), self.u, self.v)
        _check_consistent_shapes(x, y, u, v)
        xy = np.column_stack((x, y))
        super().set_offsets(xy)
        self.stale = True

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\system.py ===
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
System settings.

@group Instrumentation:
    System
"""

from __future__ import with_statement

__revision__ = "$Id$"

__all__ = ["System"]

from winappdbg import win32
from winappdbg.registry import Registry
from winappdbg.textio import HexInput, HexDump
from winappdbg.util import Regenerator, PathOperations, MemoryAddresses, DebugRegister, classproperty
from winappdbg.process import _ProcessContainer
from winappdbg.window import Window

import sys
import os
import ctypes
import warnings

from os import path, getenv

# ==============================================================================


class System(_ProcessContainer):
    """
    Interface to a batch of processes, plus some system wide settings.
    Contains a snapshot of processes.

    @group Platform settings:
        arch, bits, os, wow64, pageSize

    @group Instrumentation:
        find_window, get_window_at, get_foreground_window,
        get_desktop_window, get_shell_window

    @group Debugging:
        load_dbghelp, fix_symbol_store_path,
        request_debug_privileges, drop_debug_privileges

    @group Postmortem debugging:
        get_postmortem_debugger, set_postmortem_debugger,
        get_postmortem_exclusion_list, add_to_postmortem_exclusion_list,
        remove_from_postmortem_exclusion_list

    @group System services:
        get_services, get_active_services,
        start_service, stop_service,
        pause_service, resume_service,
        get_service_display_name, get_service_from_display_name

    @group Permissions and privileges:
        request_privileges, drop_privileges, adjust_privileges, is_admin

    @group Miscellaneous global settings:
        set_kill_on_exit_mode, read_msr, write_msr, enable_step_on_branch_mode,
        get_last_branch_location

    @type arch: str
    @cvar arch: Name of the processor architecture we're running on.
        For more details see L{win32.version._get_arch}.

    @type bits: int
    @cvar bits: Size of the machine word in bits for the current architecture.
        For more details see L{win32.version._get_bits}.

    @type os: str
    @cvar os: Name of the Windows version we're runing on.
        For more details see L{win32.version._get_os}.

    @type wow64: bool
    @cvar wow64: C{True} if the debugger is a 32 bits process running in a 64
        bits version of Windows, C{False} otherwise.

    @type pageSize: int
    @cvar pageSize: Page size in bytes. Defaults to 0x1000 but it's
        automatically updated on runtime when importing the module.

    @type registry: L{Registry}
    @cvar registry: Windows Registry for this machine.
    """

    arch = win32.arch
    bits = win32.bits
    os = win32.os
    wow64 = win32.wow64

    @classproperty
    def pageSize(cls):
        pageSize = MemoryAddresses.pageSize
        cls.pageSize = pageSize
        return pageSize

    registry = Registry()

    # ------------------------------------------------------------------------------

    @staticmethod
    def find_window(className=None, windowName=None):
        """
        Find the first top-level window in the current desktop to match the
        given class name and/or window name. If neither are provided any
        top-level window will match.

        @see: L{get_window_at}

        @type  className: str
        @param className: (Optional) Class name of the window to find.
            If C{None} or not used any class name will match the search.

        @type  windowName: str
        @param windowName: (Optional) Caption text of the window to find.
            If C{None} or not used any caption text will match the search.

        @rtype:  L{Window} or None
        @return: A window that matches the request. There may be more matching
            windows, but this method only returns one. If no matching window
            is found, the return value is C{None}.

        @raise WindowsError: An error occured while processing this request.
        """
        # I'd love to reverse the order of the parameters
        # but that might create some confusion. :(
        hWnd = win32.FindWindow(className, windowName)
        if hWnd:
            return Window(hWnd)

    @staticmethod
    def get_window_at(x, y):
        """
        Get the window located at the given coordinates in the desktop.
        If no such window exists an exception is raised.

        @see: L{find_window}

        @type  x: int
        @param x: Horizontal coordinate.
        @type  y: int
        @param y: Vertical coordinate.

        @rtype:  L{Window}
        @return: Window at the requested position. If no such window
            exists a C{WindowsError} exception is raised.

        @raise WindowsError: An error occured while processing this request.
        """
        return Window(win32.WindowFromPoint((x, y)))

    @staticmethod
    def get_foreground_window():
        """
        @rtype:  L{Window}
        @return: Returns the foreground window.
        @raise WindowsError: An error occured while processing this request.
        """
        return Window(win32.GetForegroundWindow())

    @staticmethod
    def get_desktop_window():
        """
        @rtype:  L{Window}
        @return: Returns the desktop window.
        @raise WindowsError: An error occured while processing this request.
        """
        return Window(win32.GetDesktopWindow())

    @staticmethod
    def get_shell_window():
        """
        @rtype:  L{Window}
        @return: Returns the shell window.
        @raise WindowsError: An error occured while processing this request.
        """
        return Window(win32.GetShellWindow())

    # ------------------------------------------------------------------------------

    @classmethod
    def request_debug_privileges(cls, bIgnoreExceptions=False):
        """
        Requests debug privileges.

        This may be needed to debug processes running as SYSTEM
        (such as services) since Windows XP.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when requesting debug privileges.

        @rtype:  bool
        @return: C{True} on success, C{False} on failure.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """
        try:
            cls.request_privileges(win32.SE_DEBUG_NAME)
            return True
        except Exception:
            if not bIgnoreExceptions:
                raise
        return False

    @classmethod
    def drop_debug_privileges(cls, bIgnoreExceptions=False):
        """
        Drops debug privileges.

        This may be needed to avoid being detected
        by certain anti-debug tricks.

        @type  bIgnoreExceptions: bool
        @param bIgnoreExceptions: C{True} to ignore any exceptions that may be
            raised when dropping debug privileges.

        @rtype:  bool
        @return: C{True} on success, C{False} on failure.

        @raise WindowsError: Raises an exception on error, unless
            C{bIgnoreExceptions} is C{True}.
        """
        try:
            cls.drop_privileges(win32.SE_DEBUG_NAME)
            return True
        except Exception:
            if not bIgnoreExceptions:
                raise
        return False

    @classmethod
    def request_privileges(cls, *privileges):
        """
        Requests privileges.

        @type  privileges: int...
        @param privileges: Privileges to request.

        @raise WindowsError: Raises an exception on error.
        """
        cls.adjust_privileges(True, privileges)

    @classmethod
    def drop_privileges(cls, *privileges):
        """
        Drops privileges.

        @type  privileges: int...
        @param privileges: Privileges to drop.

        @raise WindowsError: Raises an exception on error.
        """
        cls.adjust_privileges(False, privileges)

    @staticmethod
    def adjust_privileges(state, privileges):
        """
        Requests or drops privileges.

        @type  state: bool
        @param state: C{True} to request, C{False} to drop.

        @type  privileges: list(int)
        @param privileges: Privileges to request or drop.

        @raise WindowsError: Raises an exception on error.
        """
        with win32.OpenProcessToken(win32.GetCurrentProcess(), win32.TOKEN_ADJUST_PRIVILEGES) as hToken:
            NewState = ((priv, state) for priv in privileges)
            win32.AdjustTokenPrivileges(hToken, NewState)

    @staticmethod
    def is_admin():
        """
        @rtype:  bool
        @return: C{True} if the current user as Administrator privileges,
            C{False} otherwise. Since Windows Vista and above this means if
            the current process is running with UAC elevation or not.
        """
        return win32.IsUserAnAdmin()

    # ------------------------------------------------------------------------------

    __binary_types = {
        win32.VFT_APP: "application",
        win32.VFT_DLL: "dynamic link library",
        win32.VFT_STATIC_LIB: "static link library",
        win32.VFT_FONT: "font",
        win32.VFT_DRV: "driver",
        win32.VFT_VXD: "legacy driver",
    }

    __driver_types = {
        win32.VFT2_DRV_COMM: "communications driver",
        win32.VFT2_DRV_DISPLAY: "display driver",
        win32.VFT2_DRV_INSTALLABLE: "installable driver",
        win32.VFT2_DRV_KEYBOARD: "keyboard driver",
        win32.VFT2_DRV_LANGUAGE: "language driver",
        win32.VFT2_DRV_MOUSE: "mouse driver",
        win32.VFT2_DRV_NETWORK: "network driver",
        win32.VFT2_DRV_PRINTER: "printer driver",
        win32.VFT2_DRV_SOUND: "sound driver",
        win32.VFT2_DRV_SYSTEM: "system driver",
        win32.VFT2_DRV_VERSIONED_PRINTER: "versioned printer driver",
    }

    __font_types = {
        win32.VFT2_FONT_RASTER: "raster font",
        win32.VFT2_FONT_TRUETYPE: "TrueType font",
        win32.VFT2_FONT_VECTOR: "vector font",
    }

    __months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )

    __days_of_the_week = (
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    )

    @classmethod
    def get_file_version_info(cls, filename):
        """
        Get the program version from an executable file, if available.

        @type  filename: str
        @param filename: Pathname to the executable file to query.

        @rtype: tuple(str, str, bool, bool, str, str)
        @return: Tuple with version information extracted from the executable
            file metadata, containing the following:
             - File version number (C{"major.minor"}).
             - Product version number (C{"major.minor"}).
             - C{True} for debug builds, C{False} for production builds.
             - C{True} for legacy OS builds (DOS, OS/2, Win16),
               C{False} for modern OS builds.
             - Binary file type.
               May be one of the following values:
                - "application"
                - "dynamic link library"
                - "static link library"
                - "font"
                - "raster font"
                - "TrueType font"
                - "vector font"
                - "driver"
                - "communications driver"
                - "display driver"
                - "installable driver"
                - "keyboard driver"
                - "language driver"
                - "legacy driver"
                - "mouse driver"
                - "network driver"
                - "printer driver"
                - "sound driver"
                - "system driver"
                - "versioned printer driver"
             - Binary creation timestamp.
            Any of the fields may be C{None} if not available.

        @raise WindowsError: Raises an exception on error.
        """

        # Get the file version info structure.
        pBlock = win32.GetFileVersionInfo(filename)
        pBuffer, dwLen = win32.VerQueryValue(pBlock, "\\")
        if dwLen != ctypes.sizeof(win32.VS_FIXEDFILEINFO):
            raise ctypes.WinError(win32.ERROR_BAD_LENGTH)
        pVersionInfo = ctypes.cast(pBuffer, ctypes.POINTER(win32.VS_FIXEDFILEINFO))
        VersionInfo = pVersionInfo.contents
        if VersionInfo.dwSignature != 0xFEEF04BD:
            raise ctypes.WinError(win32.ERROR_BAD_ARGUMENTS)

        # File and product versions.
        FileVersion = "%d.%d" % (VersionInfo.dwFileVersionMS, VersionInfo.dwFileVersionLS)
        ProductVersion = "%d.%d" % (VersionInfo.dwProductVersionMS, VersionInfo.dwProductVersionLS)

        # Debug build?
        if VersionInfo.dwFileFlagsMask & win32.VS_FF_DEBUG:
            DebugBuild = (VersionInfo.dwFileFlags & win32.VS_FF_DEBUG) != 0
        else:
            DebugBuild = None

        # Legacy OS build?
        LegacyBuild = VersionInfo.dwFileOS != win32.VOS_NT_WINDOWS32

        # File type.
        FileType = cls.__binary_types.get(VersionInfo.dwFileType)
        if VersionInfo.dwFileType == win32.VFT_DRV:
            FileType = cls.__driver_types.get(VersionInfo.dwFileSubtype)
        elif VersionInfo.dwFileType == win32.VFT_FONT:
            FileType = cls.__font_types.get(VersionInfo.dwFileSubtype)

        # Timestamp, ex: "Monday, July 7, 2013 (12:20:50.126)".
        # FIXME: how do we know the time zone?
        FileDate = (VersionInfo.dwFileDateMS << 32) + VersionInfo.dwFileDateLS
        if FileDate:
            CreationTime = win32.FileTimeToSystemTime(FileDate)
            CreationTimestamp = "%s, %s %d, %d (%d:%d:%d.%d)" % (
                cls.__days_of_the_week[CreationTime.wDayOfWeek],
                cls.__months[CreationTime.wMonth],
                CreationTime.wDay,
                CreationTime.wYear,
                CreationTime.wHour,
                CreationTime.wMinute,
                CreationTime.wSecond,
                CreationTime.wMilliseconds,
            )
        else:
            CreationTimestamp = None

        # Return the file version info.
        return (
            FileVersion,
            ProductVersion,
            DebugBuild,
            LegacyBuild,
            FileType,
            CreationTimestamp,
        )

    # ------------------------------------------------------------------------------

    # Locations for dbghelp.dll.
    #  Unfortunately, Microsoft started bundling WinDbg with the
    #  platform SDK, so the install directories may vary across
    #  versions and platforms.
    __dbghelp_locations = {
        # Intel 64 bits.
        win32.ARCH_AMD64: set(
            [
                # WinDbg bundled with the SDK, version 8.0.
                path.join(getenv("ProgramFiles", "C:\\Program Files"), "Windows Kits", "8.0", "Debuggers", "x64", "dbghelp.dll"),
                path.join(
                    getenv("ProgramW6432", getenv("ProgramFiles", "C:\\Program Files")),
                    "Windows Kits",
                    "8.0",
                    "Debuggers",
                    "x64",
                    "dbghelp.dll",
                ),
                # Old standalone versions of WinDbg.
                path.join(getenv("ProgramFiles", "C:\\Program Files"), "Debugging Tools for Windows (x64)", "dbghelp.dll"),
            ]
        ),
        # Intel 32 bits.
        win32.ARCH_I386: set(
            [
                # WinDbg bundled with the SDK, version 8.0.
                path.join(getenv("ProgramFiles", "C:\\Program Files"), "Windows Kits", "8.0", "Debuggers", "x86", "dbghelp.dll"),
                path.join(
                    getenv("ProgramW6432", getenv("ProgramFiles", "C:\\Program Files")),
                    "Windows Kits",
                    "8.0",
                    "Debuggers",
                    "x86",
                    "dbghelp.dll",
                ),
                # Old standalone versions of WinDbg.
                path.join(getenv("ProgramFiles", "C:\\Program Files"), "Debugging Tools for Windows (x86)", "dbghelp.dll"),
                # Version shipped with Windows.
                path.join(getenv("ProgramFiles", "C:\\Program Files"), "Debugging Tools for Windows (x86)", "dbghelp.dll"),
            ]
        ),
    }

    @classmethod
    def load_dbghelp(cls, pathname=None):
        """
        Load the specified version of the C{dbghelp.dll} library.

        This library is shipped with the Debugging Tools for Windows, and it's
        required to load debug symbols.

        Normally you don't need to call this method, as WinAppDbg already tries
        to load the latest version automatically - but it may come in handy if
        the Debugging Tools are installed in a non standard folder.

        Example::
            from winappdbg import Debug

            def simple_debugger( argv ):

                # Instance a Debug object, passing it the event handler callback
                debug = Debug( my_event_handler )
                try:

                    # Load a specific dbghelp.dll file
                    debug.system.load_dbghelp("C:\\Some folder\\dbghelp.dll")

                    # Start a new process for debugging
                    debug.execv( argv )

                    # Wait for the debugee to finish
                    debug.loop()

                # Stop the debugger
                finally:
                    debug.stop()

        @see: U{http://msdn.microsoft.com/en-us/library/ms679294(VS.85).aspx}

        @type  pathname: str
        @param pathname:
            (Optional) Full pathname to the C{dbghelp.dll} library.
            If not provided this method will try to autodetect it.

        @rtype:  ctypes.WinDLL
        @return: Loaded instance of C{dbghelp.dll}.

        @raise NotImplementedError: This feature was not implemented for the
            current architecture.

        @raise WindowsError: An error occured while processing this request.
        """

        # If an explicit pathname was not given, search for the library.
        if not pathname:
            # Under WOW64 we'll treat AMD64 as I386.
            arch = win32.arch
            if arch == win32.ARCH_AMD64 and win32.bits == 32:
                arch = win32.ARCH_I386

            # Check if the architecture is supported.
            if not arch in cls.__dbghelp_locations:
                msg = "Architecture %s is not currently supported."
                raise NotImplementedError(msg % arch)

            # Grab all versions of the library we can find.
            found = []
            for pathname in cls.__dbghelp_locations[arch]:
                if path.isfile(pathname):
                    try:
                        f_ver, p_ver = cls.get_file_version_info(pathname)[:2]
                    except WindowsError:
                        msg = "Failed to parse file version metadata for: %s"
                        warnings.warn(msg % pathname)
                    if not f_ver:
                        f_ver = p_ver
                    elif p_ver and p_ver > f_ver:
                        f_ver = p_ver
                    found.append((f_ver, pathname))

            # If we found any, use the newest version.
            if found:
                found.sort()
                pathname = found.pop()[1]

            # If we didn't find any, trust the default DLL search algorithm.
            else:
                pathname = "dbghelp.dll"

        # Load the library.
        dbghelp = ctypes.windll.LoadLibrary(pathname)

        # Set it globally as the library to be used.
        ctypes.windll.dbghelp = dbghelp

        # Return the library.
        return dbghelp

    @staticmethod
    def fix_symbol_store_path(symbol_store_path=None, remote=True, force=False):
        """
        Fix the symbol store path. Equivalent to the C{.symfix} command in
        Microsoft WinDbg.

        If the symbol store path environment variable hasn't been set, this
        method will provide a default one.

        @type  symbol_store_path: str or None
        @param symbol_store_path: (Optional) Symbol store path to set.

        @type  remote: bool
        @param remote: (Optional) Defines the symbol store path to set when the
            C{symbol_store_path} is C{None}.

            If C{True} the default symbol store path is set to the Microsoft
            symbol server. Debug symbols will be downloaded through HTTP.
            This gives the best results but is also quite slow.

            If C{False} the default symbol store path is set to the local
            cache only. This prevents debug symbols from being downloaded and
            is faster, but unless you've installed the debug symbols on this
            machine or downloaded them in a previous debugging session, some
            symbols may be missing.

            If the C{symbol_store_path} argument is not C{None}, this argument
            is ignored entirely.

        @type  force: bool
        @param force: (Optional) If C{True} the new symbol store path is set
            always. If C{False} the new symbol store path is only set if
            missing.

            This allows you to call this method preventively to ensure the
            symbol server is always set up correctly when running your script,
            but without messing up whatever configuration the user has.

            Example::
                from winappdbg import Debug, System

                def simple_debugger( argv ):

                    # Instance a Debug object
                    debug = Debug( MyEventHandler() )
                    try:

                        # Make sure the remote symbol store is set
                        System.fix_symbol_store_path(remote = True,
                                                      force = False)

                        # Start a new process for debugging
                        debug.execv( argv )

                        # Wait for the debugee to finish
                        debug.loop()

                    # Stop the debugger
                    finally:
                        debug.stop()

        @rtype:  str or None
        @return: The previously set symbol store path if any,
            otherwise returns C{None}.
        """
        try:
            if symbol_store_path is None:
                local_path = "C:\\SYMBOLS"
                if not path.isdir(local_path):
                    local_path = "C:\\Windows\\Symbols"
                    if not path.isdir(local_path):
                        local_path = path.abspath(".")
                if remote:
                    symbol_store_path = "cache*;SRV*" + local_path + "*" "http://msdl.microsoft.com/download/symbols"
                else:
                    symbol_store_path = "cache*;SRV*" + local_path
            previous = os.environ.get("_NT_SYMBOL_PATH", None)
            if not previous or force:
                os.environ["_NT_SYMBOL_PATH"] = symbol_store_path
            return previous
        except Exception:
            e = sys.exc_info()[1]
            warnings.warn("Cannot fix symbol path, reason: %s" % str(e), RuntimeWarning)

    # ------------------------------------------------------------------------------

    @staticmethod
    def set_kill_on_exit_mode(bKillOnExit=False):
        """
        Defines the behavior of the debugged processes when the debugging
        thread dies. This method only affects the calling thread.

        Works on the following platforms:

         - Microsoft Windows XP and above.
         - Wine (Windows Emulator).

        Fails on the following platforms:

         - Microsoft Windows 2000 and below.
         - ReactOS.

        @type  bKillOnExit: bool
        @param bKillOnExit: C{True} to automatically kill processes when the
            debugger thread dies. C{False} to automatically detach from
            processes when the debugger thread dies.

        @rtype:  bool
        @return: C{True} on success, C{False} on error.

        @note:
            This call will fail if a debug port was not created. That is, if
            the debugger isn't attached to at least one process. For more info
            see: U{http://msdn.microsoft.com/en-us/library/ms679307.aspx}
        """
        try:
            # won't work before calling CreateProcess or DebugActiveProcess
            win32.DebugSetProcessKillOnExit(bKillOnExit)
        except (AttributeError, WindowsError):
            return False
        return True

    @staticmethod
    def read_msr(address):
        """
        Read the contents of the specified MSR (Machine Specific Register).

        @type  address: int
        @param address: MSR to read.

        @rtype:  int
        @return: Value of the specified MSR.

        @raise WindowsError:
            Raises an exception on error.

        @raise NotImplementedError:
            Current architecture is not C{i386} or C{amd64}.

        @warning:
            It could potentially brick your machine.
            It works on my machine, but your mileage may vary.
        """
        if win32.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
            raise NotImplementedError("MSR reading is only supported on i386 or amd64 processors.")
        msr = win32.SYSDBG_MSR()
        msr.Address = address
        msr.Data = 0
        win32.NtSystemDebugControl(win32.SysDbgReadMsr, InputBuffer=msr, OutputBuffer=msr)
        return msr.Data

    @staticmethod
    def write_msr(address, value):
        """
        Set the contents of the specified MSR (Machine Specific Register).

        @type  address: int
        @param address: MSR to write.

        @type  value: int
        @param value: Contents to write on the MSR.

        @raise WindowsError:
            Raises an exception on error.

        @raise NotImplementedError:
            Current architecture is not C{i386} or C{amd64}.

        @warning:
            It could potentially brick your machine.
            It works on my machine, but your mileage may vary.
        """
        if win32.arch not in (win32.ARCH_I386, win32.ARCH_AMD64):
            raise NotImplementedError("MSR writing is only supported on i386 or amd64 processors.")
        msr = win32.SYSDBG_MSR()
        msr.Address = address
        msr.Data = value
        win32.NtSystemDebugControl(win32.SysDbgWriteMsr, InputBuffer=msr)

    @classmethod
    def enable_step_on_branch_mode(cls):
        """
        When tracing, call this on every single step event
        for step on branch mode.

        @raise WindowsError:
            Raises C{ERROR_DEBUGGER_INACTIVE} if the debugger is not attached
            to least one process.

        @raise NotImplementedError:
            Current architecture is not C{i386} or C{amd64}.

        @warning:
            This method uses the processor's machine specific registers (MSR).
            It could potentially brick your machine.
            It works on my machine, but your mileage may vary.

        @note:
            It doesn't seem to work in VMWare or VirtualBox machines.
            Maybe it fails in other virtualization/emulation environments,
            no extensive testing was made so far.
        """
        cls.write_msr(DebugRegister.DebugCtlMSR, DebugRegister.BranchTrapFlag | DebugRegister.LastBranchRecord)

    @classmethod
    def get_last_branch_location(cls):
        """
        Returns the source and destination addresses of the last taken branch.

        @rtype: tuple( int, int )
        @return: Source and destination addresses of the last taken branch.

        @raise WindowsError:
            Raises an exception on error.

        @raise NotImplementedError:
            Current architecture is not C{i386} or C{amd64}.

        @warning:
            This method uses the processor's machine specific registers (MSR).
            It could potentially brick your machine.
            It works on my machine, but your mileage may vary.

        @note:
            It doesn't seem to work in VMWare or VirtualBox machines.
            Maybe it fails in other virtualization/emulation environments,
            no extensive testing was made so far.
        """
        LastBranchFromIP = cls.read_msr(DebugRegister.LastBranchFromIP)
        LastBranchToIP = cls.read_msr(DebugRegister.LastBranchToIP)
        return (LastBranchFromIP, LastBranchToIP)

    # ------------------------------------------------------------------------------

    @classmethod
    def get_postmortem_debugger(cls, bits=None):
        """
        Returns the postmortem debugging settings from the Registry.

        @see: L{set_postmortem_debugger}

        @type  bits: int
        @param bits: Set to C{32} for the 32 bits debugger, or C{64} for the
            64 bits debugger. Set to {None} for the default (L{System.bits}.

        @rtype:  tuple( str, bool, int )
        @return: A tuple containing the command line string to the postmortem
            debugger, a boolean specifying if user interaction is allowed
            before attaching, and an integer specifying a user defined hotkey.
            Any member of the tuple may be C{None}.
            See L{set_postmortem_debugger} for more details.

        @raise WindowsError:
            Raises an exception on error.
        """
        if bits is None:
            bits = cls.bits
        elif bits not in (32, 64):
            raise NotImplementedError("Unknown architecture (%r bits)" % bits)

        if bits == 32 and cls.bits == 64:
            keyname = "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug"
        else:
            keyname = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug"

        key = cls.registry[keyname]

        debugger = key.get("Debugger")
        auto = key.get("Auto")
        hotkey = key.get("UserDebuggerHotkey")

        if auto is not None:
            auto = bool(auto)

        return (debugger, auto, hotkey)

    @classmethod
    def get_postmortem_exclusion_list(cls, bits=None):
        """
        Returns the exclusion list for the postmortem debugger.

        @see: L{get_postmortem_debugger}

        @type  bits: int
        @param bits: Set to C{32} for the 32 bits debugger, or C{64} for the
            64 bits debugger. Set to {None} for the default (L{System.bits}).

        @rtype:  list( str )
        @return: List of excluded application filenames.

        @raise WindowsError:
            Raises an exception on error.
        """
        if bits is None:
            bits = cls.bits
        elif bits not in (32, 64):
            raise NotImplementedError("Unknown architecture (%r bits)" % bits)

        if bits == 32 and cls.bits == 64:
            keyname = "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"
        else:
            keyname = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"

        try:
            key = cls.registry[keyname]
        except KeyError:
            return []

        return [name for (name, enabled) in key.items() if enabled]

    @classmethod
    def set_postmortem_debugger(cls, cmdline, auto=None, hotkey=None, bits=None):
        """
        Sets the postmortem debugging settings in the Registry.

        @warning: This method requires administrative rights.

        @see: L{get_postmortem_debugger}

        @type  cmdline: str
        @param cmdline: Command line to the new postmortem debugger.
            When the debugger is invoked, the first "%ld" is replaced with the
            process ID and the second "%ld" is replaced with the event handle.
            Don't forget to enclose the program filename in double quotes if
            the path contains spaces.

        @type  auto: bool
        @param auto: Set to C{True} if no user interaction is allowed, C{False}
            to prompt a confirmation dialog before attaching.
            Use C{None} to leave this value unchanged.

        @type  hotkey: int
        @param hotkey: Virtual key scan code for the user defined hotkey.
            Use C{0} to disable the hotkey.
            Use C{None} to leave this value unchanged.

        @type  bits: int
        @param bits: Set to C{32} for the 32 bits debugger, or C{64} for the
            64 bits debugger. Set to {None} for the default (L{System.bits}).

        @rtype:  tuple( str, bool, int )
        @return: Previously defined command line and auto flag.

        @raise WindowsError:
            Raises an exception on error.
        """
        if bits is None:
            bits = cls.bits
        elif bits not in (32, 64):
            raise NotImplementedError("Unknown architecture (%r bits)" % bits)

        if bits == 32 and cls.bits == 64:
            keyname = "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug"
        else:
            keyname = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug"

        key = cls.registry[keyname]

        if cmdline is not None:
            key["Debugger"] = cmdline
        if auto is not None:
            key["Auto"] = int(bool(auto))
        if hotkey is not None:
            key["UserDebuggerHotkey"] = int(hotkey)

    @classmethod
    def add_to_postmortem_exclusion_list(cls, pathname, bits=None):
        """
        Adds the given filename to the exclusion list for postmortem debugging.

        @warning: This method requires administrative rights.

        @see: L{get_postmortem_exclusion_list}

        @type  pathname: str
        @param pathname:
            Application pathname to exclude from postmortem debugging.

        @type  bits: int
        @param bits: Set to C{32} for the 32 bits debugger, or C{64} for the
            64 bits debugger. Set to {None} for the default (L{System.bits}).

        @raise WindowsError:
            Raises an exception on error.
        """
        if bits is None:
            bits = cls.bits
        elif bits not in (32, 64):
            raise NotImplementedError("Unknown architecture (%r bits)" % bits)

        if bits == 32 and cls.bits == 64:
            keyname = "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"
        else:
            keyname = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"

        try:
            key = cls.registry[keyname]
        except KeyError:
            key = cls.registry.create(keyname)

        key[pathname] = 1

    @classmethod
    def remove_from_postmortem_exclusion_list(cls, pathname, bits=None):
        """
        Removes the given filename to the exclusion list for postmortem
        debugging from the Registry.

        @warning: This method requires administrative rights.

        @warning: Don't ever delete entries you haven't created yourself!
            Some entries are set by default for your version of Windows.
            Deleting them might deadlock your system under some circumstances.

            For more details see:
            U{http://msdn.microsoft.com/en-us/library/bb204634(v=vs.85).aspx}

        @see: L{get_postmortem_exclusion_list}

        @type  pathname: str
        @param pathname: Application pathname to remove from the postmortem
            debugging exclusion list.

        @type  bits: int
        @param bits: Set to C{32} for the 32 bits debugger, or C{64} for the
            64 bits debugger. Set to {None} for the default (L{System.bits}).

        @raise WindowsError:
            Raises an exception on error.
        """
        if bits is None:
            bits = cls.bits
        elif bits not in (32, 64):
            raise NotImplementedError("Unknown architecture (%r bits)" % bits)

        if bits == 32 and cls.bits == 64:
            keyname = "HKLM\\SOFTWARE\\Wow6432Node\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"
        else:
            keyname = "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\AeDebug\\AutoExclusionList"

        try:
            key = cls.registry[keyname]
        except KeyError:
            return

        try:
            del key[pathname]
        except KeyError:
            return

    # ------------------------------------------------------------------------------

    @staticmethod
    def get_services():
        """
        Retrieve a list of all system services.

        @see: L{get_active_services},
            L{start_service}, L{stop_service},
            L{pause_service}, L{resume_service}

        @rtype:  list( L{win32.ServiceStatusProcessEntry} )
        @return: List of service status descriptors.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_ENUMERATE_SERVICE) as hSCManager:
            try:
                return win32.EnumServicesStatusEx(hSCManager)
            except AttributeError:
                return win32.EnumServicesStatus(hSCManager)

    @staticmethod
    def get_active_services():
        """
        Retrieve a list of all active system services.

        @see: L{get_services},
            L{start_service}, L{stop_service},
            L{pause_service}, L{resume_service}

        @rtype:  list( L{win32.ServiceStatusProcessEntry} )
        @return: List of service status descriptors.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_ENUMERATE_SERVICE) as hSCManager:
            return [
                entry
                for entry in win32.EnumServicesStatusEx(hSCManager, dwServiceType=win32.SERVICE_WIN32, dwServiceState=win32.SERVICE_ACTIVE)
                if entry.ProcessId
            ]

    @staticmethod
    def get_service(name):
        """
        Get the service descriptor for the given service name.

        @see: L{start_service}, L{stop_service},
            L{pause_service}, L{resume_service}

        @type  name: str
        @param name: Service unique name. You can get this value from the
            C{ServiceName} member of the service descriptors returned by
            L{get_services} or L{get_active_services}.

        @rtype:  L{win32.ServiceStatusProcess}
        @return: Service status descriptor.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_ENUMERATE_SERVICE) as hSCManager:
            with win32.OpenService(hSCManager, name, dwDesiredAccess=win32.SERVICE_QUERY_STATUS) as hService:
                try:
                    return win32.QueryServiceStatusEx(hService)
                except AttributeError:
                    return win32.QueryServiceStatus(hService)

    @staticmethod
    def get_service_display_name(name):
        """
        Get the service display name for the given service name.

        @see: L{get_service}

        @type  name: str
        @param name: Service unique name. You can get this value from the
            C{ServiceName} member of the service descriptors returned by
            L{get_services} or L{get_active_services}.

        @rtype:  str
        @return: Service display name.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_ENUMERATE_SERVICE) as hSCManager:
            return win32.GetServiceDisplayName(hSCManager, name)

    @staticmethod
    def get_service_from_display_name(displayName):
        """
        Get the service unique name given its display name.

        @see: L{get_service}

        @type  displayName: str
        @param displayName: Service display name. You can get this value from
            the C{DisplayName} member of the service descriptors returned by
            L{get_services} or L{get_active_services}.

        @rtype:  str
        @return: Service unique name.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_ENUMERATE_SERVICE) as hSCManager:
            return win32.GetServiceKeyName(hSCManager, displayName)

    @staticmethod
    def start_service(name, argv=None):
        """
        Start the service given by name.

        @warn: This method requires UAC elevation in Windows Vista and above.

        @see: L{stop_service}, L{pause_service}, L{resume_service}

        @type  name: str
        @param name: Service unique name. You can get this value from the
            C{ServiceName} member of the service descriptors returned by
            L{get_services} or L{get_active_services}.
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_CONNECT) as hSCManager:
            with win32.OpenService(hSCManager, name, dwDesiredAccess=win32.SERVICE_START) as hService:
                win32.StartService(hService)

    @staticmethod
    def stop_service(name):
        """
        Stop the service given by name.

        @warn: This method requires UAC elevation in Windows Vista and above.

        @see: L{get_services}, L{get_active_services},
            L{start_service}, L{pause_service}, L{resume_service}
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_CONNECT) as hSCManager:
            with win32.OpenService(hSCManager, name, dwDesiredAccess=win32.SERVICE_STOP) as hService:
                win32.ControlService(hService, win32.SERVICE_CONTROL_STOP)

    @staticmethod
    def pause_service(name):
        """
        Pause the service given by name.

        @warn: This method requires UAC elevation in Windows Vista and above.

        @note: Not all services support this.

        @see: L{get_services}, L{get_active_services},
            L{start_service}, L{stop_service}, L{resume_service}
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_CONNECT) as hSCManager:
            with win32.OpenService(hSCManager, name, dwDesiredAccess=win32.SERVICE_PAUSE_CONTINUE) as hService:
                win32.ControlService(hService, win32.SERVICE_CONTROL_PAUSE)

    @staticmethod
    def resume_service(name):
        """
        Resume the service given by name.

        @warn: This method requires UAC elevation in Windows Vista and above.

        @note: Not all services support this.

        @see: L{get_services}, L{get_active_services},
            L{start_service}, L{stop_service}, L{pause_service}
        """
        with win32.OpenSCManager(dwDesiredAccess=win32.SC_MANAGER_CONNECT) as hSCManager:
            with win32.OpenService(hSCManager, name, dwDesiredAccess=win32.SERVICE_PAUSE_CONTINUE) as hService:
                win32.ControlService(hService, win32.SERVICE_CONTROL_CONTINUE)

    # TODO: create_service, delete_service

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_numpy_pickle.py ===
"""Test the numpy pickler as a replacement of the standard pickler."""

import bz2
import copy
import gzip
import io
import mmap
import os
import pickle
import random
import re
import socket
import sys
import warnings
import zlib
from contextlib import closing
from pathlib import Path

try:
    import lzma
except ImportError:
    lzma = None

import pytest

# numpy_pickle is not a drop-in replacement of pickle, as it takes
# filenames instead of open files as arguments.
from joblib import numpy_pickle, register_compressor
from joblib.compressor import (
    _COMPRESSORS,
    _LZ4_PREFIX,
    LZ4_NOT_INSTALLED_ERROR,
    BinaryZlibFile,
    CompressorWrapper,
)
from joblib.numpy_pickle_utils import (
    _IO_BUFFER_SIZE,
    _detect_compressor,
    _ensure_native_byte_order,
    _is_numpy_array_byte_order_mismatch,
)
from joblib.test import data
from joblib.test.common import (
    memory_used,
    np,
    with_lz4,
    with_memory_profiler,
    with_numpy,
    without_lz4,
)
from joblib.testing import parametrize, raises, warns

###############################################################################
# Define a list of standard types.
# Borrowed from dill, initial author: Micheal McKerns:
# http://dev.danse.us/trac/pathos/browser/dill/dill_test2.py

typelist = []

# testing types
_none = None
typelist.append(_none)
_type = type
typelist.append(_type)
_bool = bool(1)
typelist.append(_bool)
_int = int(1)
typelist.append(_int)
_float = float(1)
typelist.append(_float)
_complex = complex(1)
typelist.append(_complex)
_string = str(1)
typelist.append(_string)
_tuple = ()
typelist.append(_tuple)
_list = []
typelist.append(_list)
_dict = {}
typelist.append(_dict)
_builtin = len
typelist.append(_builtin)


def _function(x):
    yield x


class _class:
    def _method(self):
        pass


class _newclass(object):
    def _method(self):
        pass


typelist.append(_function)
typelist.append(_class)
typelist.append(_newclass)  # <type 'type'>
_instance = _class()
typelist.append(_instance)
_object = _newclass()
typelist.append(_object)  # <type 'class'>


###############################################################################
# Tests


@parametrize("compress", [0, 1])
@parametrize("member", typelist)
def test_standard_types(tmpdir, compress, member):
    # Test pickling and saving with standard types.
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump(member, filename, compress=compress)
    _member = numpy_pickle.load(filename)
    # We compare the pickled instance to the reloaded one only if it
    # can be compared to a copied one
    if member == copy.deepcopy(member):
        assert member == _member


def test_value_error():
    # Test inverting the input arguments to dump
    with raises(ValueError):
        numpy_pickle.dump("foo", dict())


@parametrize("wrong_compress", [-1, 10, dict()])
def test_compress_level_error(wrong_compress):
    # Verify that passing an invalid compress argument raises an error.
    exception_msg = 'Non valid compress level given: "{0}"'.format(wrong_compress)
    with raises(ValueError) as excinfo:
        numpy_pickle.dump("dummy", "foo", compress=wrong_compress)
    excinfo.match(exception_msg)


@with_numpy
@parametrize("compress", [False, True, 0, 3, "zlib"])
def test_numpy_persistence(tmpdir, compress):
    filename = tmpdir.join("test.pkl").strpath
    rnd = np.random.RandomState(0)
    a = rnd.random_sample((10, 2))
    # We use 'a.T' to have a non C-contiguous array.
    for index, obj in enumerate(((a,), (a.T,), (a, a), [a, a, a])):
        filenames = numpy_pickle.dump(obj, filename, compress=compress)

        # All is cached in one file
        assert len(filenames) == 1
        # Check that only one file was created
        assert filenames[0] == filename
        # Check that this file does exist
        assert os.path.exists(filenames[0])

        # Unpickle the object
        obj_ = numpy_pickle.load(filename)
        # Check that the items are indeed arrays
        for item in obj_:
            assert isinstance(item, np.ndarray)
        # And finally, check that all the values are equal.
        np.testing.assert_array_equal(np.array(obj), np.array(obj_))

    # Now test with an array subclass
    obj = np.memmap(filename + "mmap", mode="w+", shape=4, dtype=np.float64)
    filenames = numpy_pickle.dump(obj, filename, compress=compress)
    # All is cached in one file
    assert len(filenames) == 1

    obj_ = numpy_pickle.load(filename)
    if type(obj) is not np.memmap and hasattr(obj, "__array_prepare__"):
        # We don't reconstruct memmaps
        assert isinstance(obj_, type(obj))

    np.testing.assert_array_equal(obj_, obj)

    # Test with an object containing multiple numpy arrays
    obj = ComplexTestObject()
    filenames = numpy_pickle.dump(obj, filename, compress=compress)
    # All is cached in one file
    assert len(filenames) == 1

    obj_loaded = numpy_pickle.load(filename)
    assert isinstance(obj_loaded, type(obj))
    np.testing.assert_array_equal(obj_loaded.array_float, obj.array_float)
    np.testing.assert_array_equal(obj_loaded.array_int, obj.array_int)
    np.testing.assert_array_equal(obj_loaded.array_obj, obj.array_obj)


@with_numpy
def test_numpy_persistence_bufferred_array_compression(tmpdir):
    big_array = np.ones((_IO_BUFFER_SIZE + 100), dtype=np.uint8)
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump(big_array, filename, compress=True)
    arr_reloaded = numpy_pickle.load(filename)

    np.testing.assert_array_equal(big_array, arr_reloaded)


@with_numpy
def test_memmap_persistence(tmpdir):
    rnd = np.random.RandomState(0)
    a = rnd.random_sample(10)
    filename = tmpdir.join("test1.pkl").strpath
    numpy_pickle.dump(a, filename)
    b = numpy_pickle.load(filename, mmap_mode="r")

    assert isinstance(b, np.memmap)

    # Test with an object containing multiple numpy arrays
    filename = tmpdir.join("test2.pkl").strpath
    obj = ComplexTestObject()
    numpy_pickle.dump(obj, filename)
    obj_loaded = numpy_pickle.load(filename, mmap_mode="r")
    assert isinstance(obj_loaded, type(obj))
    assert isinstance(obj_loaded.array_float, np.memmap)
    assert not obj_loaded.array_float.flags.writeable
    assert isinstance(obj_loaded.array_int, np.memmap)
    assert not obj_loaded.array_int.flags.writeable
    # Memory map not allowed for numpy object arrays
    assert not isinstance(obj_loaded.array_obj, np.memmap)
    np.testing.assert_array_equal(obj_loaded.array_float, obj.array_float)
    np.testing.assert_array_equal(obj_loaded.array_int, obj.array_int)
    np.testing.assert_array_equal(obj_loaded.array_obj, obj.array_obj)

    # Test we can write in memmapped arrays
    obj_loaded = numpy_pickle.load(filename, mmap_mode="r+")
    assert obj_loaded.array_float.flags.writeable
    obj_loaded.array_float[0:10] = 10.0
    assert obj_loaded.array_int.flags.writeable
    obj_loaded.array_int[0:10] = 10

    obj_reloaded = numpy_pickle.load(filename, mmap_mode="r")
    np.testing.assert_array_equal(obj_reloaded.array_float, obj_loaded.array_float)
    np.testing.assert_array_equal(obj_reloaded.array_int, obj_loaded.array_int)

    # Test w+ mode is caught and the mode has switched to r+
    numpy_pickle.load(filename, mmap_mode="w+")
    assert obj_loaded.array_int.flags.writeable
    assert obj_loaded.array_int.mode == "r+"
    assert obj_loaded.array_float.flags.writeable
    assert obj_loaded.array_float.mode == "r+"


@with_numpy
def test_memmap_persistence_mixed_dtypes(tmpdir):
    # loading datastructures that have sub-arrays with dtype=object
    # should not prevent memmapping on fixed size dtype sub-arrays.
    rnd = np.random.RandomState(0)
    a = rnd.random_sample(10)
    b = np.array([1, "b"], dtype=object)
    construct = (a, b)
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump(construct, filename)
    a_clone, b_clone = numpy_pickle.load(filename, mmap_mode="r")

    # the floating point array has been memory mapped
    assert isinstance(a_clone, np.memmap)

    # the object-dtype array has been loaded in memory
    assert not isinstance(b_clone, np.memmap)


@with_numpy
def test_masked_array_persistence(tmpdir):
    # The special-case picker fails, because saving masked_array
    # not implemented, but it just delegates to the standard pickler.
    rnd = np.random.RandomState(0)
    a = rnd.random_sample(10)
    a = np.ma.masked_greater(a, 0.5)
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump(a, filename)
    b = numpy_pickle.load(filename, mmap_mode="r")
    assert isinstance(b, np.ma.masked_array)


@with_numpy
def test_compress_mmap_mode_warning(tmpdir):
    # Test the warning in case of compress + mmap_mode
    rnd = np.random.RandomState(0)
    obj = rnd.random_sample(10)
    this_filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump(obj, this_filename, compress=1)
    with warns(UserWarning) as warninfo:
        reloaded_obj = numpy_pickle.load(this_filename, mmap_mode="r+")
    debug_msg = "\n".join([str(w) for w in warninfo])
    warninfo = [w.message for w in warninfo]
    assert not isinstance(reloaded_obj, np.memmap)
    np.testing.assert_array_equal(obj, reloaded_obj)
    assert len(warninfo) == 1, debug_msg
    assert (
        str(warninfo[0]) == 'mmap_mode "r+" is not compatible with compressed '
        f'file {this_filename}. "r+" flag will be ignored.'
    )


@with_numpy
@with_memory_profiler
@parametrize("compress", [True, False])
def test_memory_usage(tmpdir, compress):
    # Verify memory stays within expected bounds.
    filename = tmpdir.join("test.pkl").strpath
    small_array = np.ones((10, 10))
    big_array = np.ones(shape=100 * int(1e6), dtype=np.uint8)

    for obj in (small_array, big_array):
        size = obj.nbytes / 1e6
        obj_filename = filename + str(np.random.randint(0, 1000))
        mem_used = memory_used(numpy_pickle.dump, obj, obj_filename, compress=compress)

        # The memory used to dump the object shouldn't exceed the buffer
        # size used to write array chunks (16MB).
        write_buf_size = _IO_BUFFER_SIZE + 16 * 1024**2 / 1e6
        assert mem_used <= write_buf_size

        mem_used = memory_used(numpy_pickle.load, obj_filename)
        # memory used should be less than array size + buffer size used to
        # read the array chunk by chunk.
        read_buf_size = 32 + _IO_BUFFER_SIZE  # MiB
        assert mem_used < size + read_buf_size


@with_numpy
def test_compressed_pickle_dump_and_load(tmpdir):
    expected_list = [
        np.arange(5, dtype=np.dtype("<i8")),
        np.arange(5, dtype=np.dtype(">i8")),
        np.arange(5, dtype=np.dtype("<f8")),
        np.arange(5, dtype=np.dtype(">f8")),
        np.array([1, "abc", {"a": 1, "b": 2}], dtype="O"),
        np.arange(256, dtype=np.uint8).tobytes(),
        "C'est l'\xe9t\xe9 !",
    ]

    fname = tmpdir.join("temp.pkl.gz").strpath

    dumped_filenames = numpy_pickle.dump(expected_list, fname, compress=1)
    assert len(dumped_filenames) == 1
    result_list = numpy_pickle.load(fname)
    for result, expected in zip(result_list, expected_list):
        if isinstance(expected, np.ndarray):
            expected = _ensure_native_byte_order(expected)
            assert result.dtype == expected.dtype
            np.testing.assert_equal(result, expected)
        else:
            assert result == expected


@with_numpy
def test_memmap_load(tmpdir):
    little_endian_dtype = np.dtype("<i8")
    big_endian_dtype = np.dtype(">i8")
    all_dtypes = (little_endian_dtype, big_endian_dtype)

    le_array = np.arange(5, dtype=little_endian_dtype)
    be_array = np.arange(5, dtype=big_endian_dtype)

    fname = tmpdir.join("temp.pkl").strpath

    numpy_pickle.dump([le_array, be_array], fname)

    le_array_native_load, be_array_native_load = numpy_pickle.load(
        fname, ensure_native_byte_order=True
    )

    assert le_array_native_load.dtype == be_array_native_load.dtype
    assert le_array_native_load.dtype in all_dtypes

    le_array_nonnative_load, be_array_nonnative_load = numpy_pickle.load(
        fname, ensure_native_byte_order=False
    )

    assert le_array_nonnative_load.dtype == le_array.dtype
    assert be_array_nonnative_load.dtype == be_array.dtype


def test_invalid_parameters_raise():
    expected_msg = (
        "Native byte ordering can only be enforced if 'mmap_mode' parameter "
        "is set to None, but got 'mmap_mode=r+' instead."
    )

    with raises(ValueError, match=re.escape(expected_msg)):
        numpy_pickle.load(
            "/path/to/some/dump.pkl", ensure_native_byte_order=True, mmap_mode="r+"
        )


def _check_pickle(filename, expected_list, mmap_mode=None):
    """Helper function to test joblib pickle content.

    Note: currently only pickles containing an iterable are supported
    by this function.
    """
    version_match = re.match(r".+py(\d)(\d).+", filename)
    py_version_used_for_writing = int(version_match.group(1))

    py_version_to_default_pickle_protocol = {2: 2, 3: 3}
    pickle_reading_protocol = py_version_to_default_pickle_protocol.get(3, 4)
    pickle_writing_protocol = py_version_to_default_pickle_protocol.get(
        py_version_used_for_writing, 4
    )
    if pickle_reading_protocol >= pickle_writing_protocol:
        try:
            with warnings.catch_warnings(record=True) as warninfo:
                warnings.simplefilter("always")
                result_list = numpy_pickle.load(filename, mmap_mode=mmap_mode)
            filename_base = os.path.basename(filename)
            expected_nb_deprecation_warnings = (
                1 if ("_0.9" in filename_base or "_0.8.4" in filename_base) else 0
            )

            expected_nb_user_warnings = (
                3
                if (re.search("_0.1.+.pkl$", filename_base) and mmap_mode is not None)
                else 0
            )
            expected_nb_warnings = (
                expected_nb_deprecation_warnings + expected_nb_user_warnings
            )
            assert len(warninfo) == expected_nb_warnings, (
                "Did not get the expected number of warnings. Expected "
                f"{expected_nb_warnings} but got warnings: "
                f"{[w.message for w in warninfo]}"
            )

            deprecation_warnings = [
                w for w in warninfo if issubclass(w.category, DeprecationWarning)
            ]
            user_warnings = [w for w in warninfo if issubclass(w.category, UserWarning)]
            for w in deprecation_warnings:
                assert (
                    str(w.message)
                    == "The file '{0}' has been generated with a joblib "
                    "version less than 0.10. Please regenerate this "
                    "pickle file.".format(filename)
                )

            for w in user_warnings:
                escaped_filename = re.escape(filename)
                assert re.search(
                    f"memmapped.+{escaped_filename}.+segmentation fault", str(w.message)
                )

            for result, expected in zip(result_list, expected_list):
                if isinstance(expected, np.ndarray):
                    expected = _ensure_native_byte_order(expected)
                    assert result.dtype == expected.dtype
                    np.testing.assert_equal(result, expected)
                else:
                    assert result == expected
        except Exception as exc:
            # When trying to read with python 3 a pickle generated
            # with python 2 we expect a user-friendly error
            if py_version_used_for_writing == 2:
                assert isinstance(exc, ValueError)
                message = (
                    "You may be trying to read with "
                    "python 3 a joblib pickle generated with python 2."
                )
                assert message in str(exc)
            elif filename.endswith(".lz4") and with_lz4.args[0]:
                assert isinstance(exc, ValueError)
                assert LZ4_NOT_INSTALLED_ERROR in str(exc)
            else:
                raise
    else:
        # Pickle protocol used for writing is too high. We expect a
        # "unsupported pickle protocol" error message
        try:
            numpy_pickle.load(filename)
            raise AssertionError(
                "Numpy pickle loading should have raised a ValueError exception"
            )
        except ValueError as e:
            message = "unsupported pickle protocol: {0}".format(pickle_writing_protocol)
            assert message in str(e.args)


@with_numpy
def test_joblib_pickle_across_python_versions():
    # We need to be specific about dtypes in particular endianness
    # because the pickles can be generated on one architecture and
    # the tests run on another one. See
    # https://github.com/joblib/joblib/issues/279.
    expected_list = [
        np.arange(5, dtype=np.dtype("<i8")),
        np.arange(5, dtype=np.dtype("<f8")),
        np.array([1, "abc", {"a": 1, "b": 2}], dtype="O"),
        np.arange(256, dtype=np.uint8).tobytes(),
        # np.matrix is a subclass of np.ndarray, here we want
        # to verify this type of object is correctly unpickled
        # among versions.
        np.matrix([0, 1, 2], dtype=np.dtype("<i8")),
        "C'est l'\xe9t\xe9 !",
    ]

    # Testing all the compressed and non compressed
    # pickles in joblib/test/data. These pickles were generated by
    # the joblib/test/data/create_numpy_pickle.py script for the
    # relevant python, joblib and numpy versions.
    test_data_dir = os.path.dirname(os.path.abspath(data.__file__))

    pickle_extensions = (".pkl", ".gz", ".gzip", ".bz2", "lz4")
    if lzma is not None:
        pickle_extensions += (".xz", ".lzma")
    pickle_filenames = [
        os.path.join(test_data_dir, fn)
        for fn in os.listdir(test_data_dir)
        if any(fn.endswith(ext) for ext in pickle_extensions)
    ]

    for fname in pickle_filenames:
        _check_pickle(fname, expected_list)


@with_numpy
def test_joblib_pickle_across_python_versions_with_mmap():
    expected_list = [
        np.arange(5, dtype=np.dtype("<i8")),
        np.arange(5, dtype=np.dtype("<f8")),
        np.array([1, "abc", {"a": 1, "b": 2}], dtype="O"),
        np.arange(256, dtype=np.uint8).tobytes(),
        # np.matrix is a subclass of np.ndarray, here we want
        # to verify this type of object is correctly unpickled
        # among versions.
        np.matrix([0, 1, 2], dtype=np.dtype("<i8")),
        "C'est l'\xe9t\xe9 !",
    ]

    test_data_dir = os.path.dirname(os.path.abspath(data.__file__))

    pickle_filenames = [
        os.path.join(test_data_dir, fn)
        for fn in os.listdir(test_data_dir)
        if fn.endswith(".pkl")
    ]
    for fname in pickle_filenames:
        _check_pickle(fname, expected_list, mmap_mode="r")


@with_numpy
def test_numpy_array_byte_order_mismatch_detection():
    # List of numpy arrays with big endian byteorder.
    be_arrays = [
        np.array([(1, 2.0), (3, 4.0)], dtype=[("", ">i8"), ("", ">f8")]),
        np.arange(3, dtype=np.dtype(">i8")),
        np.arange(3, dtype=np.dtype(">f8")),
    ]

    # Verify the byteorder mismatch is correctly detected.
    for array in be_arrays:
        if sys.byteorder == "big":
            assert not _is_numpy_array_byte_order_mismatch(array)
        else:
            assert _is_numpy_array_byte_order_mismatch(array)
        converted = _ensure_native_byte_order(array)
        if converted.dtype.fields:
            for f in converted.dtype.fields.values():
                f[0].byteorder == "="
        else:
            assert converted.dtype.byteorder == "="

    # List of numpy arrays with little endian byteorder.
    le_arrays = [
        np.array([(1, 2.0), (3, 4.0)], dtype=[("", "<i8"), ("", "<f8")]),
        np.arange(3, dtype=np.dtype("<i8")),
        np.arange(3, dtype=np.dtype("<f8")),
    ]

    # Verify the byteorder mismatch is correctly detected.
    for array in le_arrays:
        if sys.byteorder == "little":
            assert not _is_numpy_array_byte_order_mismatch(array)
        else:
            assert _is_numpy_array_byte_order_mismatch(array)
        converted = _ensure_native_byte_order(array)
        if converted.dtype.fields:
            for f in converted.dtype.fields.values():
                f[0].byteorder == "="
        else:
            assert converted.dtype.byteorder == "="


@parametrize("compress_tuple", [("zlib", 3), ("gzip", 3)])
def test_compress_tuple_argument(tmpdir, compress_tuple):
    # Verify the tuple is correctly taken into account.
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump("dummy", filename, compress=compress_tuple)
    # Verify the file contains the right magic number
    with open(filename, "rb") as f:
        assert _detect_compressor(f) == compress_tuple[0]


@parametrize(
    "compress_tuple,message",
    [
        (
            ("zlib", 3, "extra"),  # wrong compress tuple
            "Compress argument tuple should contain exactly 2 elements",
        ),
        (
            ("wrong", 3),  # wrong compress method
            'Non valid compression method given: "{}"'.format("wrong"),
        ),
        (
            ("zlib", "wrong"),  # wrong compress level
            'Non valid compress level given: "{}"'.format("wrong"),
        ),
    ],
)
def test_compress_tuple_argument_exception(tmpdir, compress_tuple, message):
    filename = tmpdir.join("test.pkl").strpath
    # Verify setting a wrong compress tuple raises a ValueError.
    with raises(ValueError) as excinfo:
        numpy_pickle.dump("dummy", filename, compress=compress_tuple)
    excinfo.match(message)


@parametrize("compress_string", ["zlib", "gzip"])
def test_compress_string_argument(tmpdir, compress_string):
    # Verify the string is correctly taken into account.
    filename = tmpdir.join("test.pkl").strpath
    numpy_pickle.dump("dummy", filename, compress=compress_string)
    # Verify the file contains the right magic number
    with open(filename, "rb") as f:
        assert _detect_compressor(f) == compress_string


@with_numpy
@parametrize("compress", [1, 3, 6])
@parametrize("cmethod", _COMPRESSORS)
def test_joblib_compression_formats(tmpdir, compress, cmethod):
    filename = tmpdir.join("test.pkl").strpath
    objects = (
        np.ones(shape=(100, 100), dtype="f8"),
        range(10),
        {"a": 1, 2: "b"},
        [],
        (),
        {},
        0,
        1.0,
    )

    if cmethod in ("lzma", "xz") and lzma is None:
        pytest.skip("lzma is support not available")

    elif cmethod == "lz4" and with_lz4.args[0]:
        # Skip the test if lz4 is not installed. We here use the with_lz4
        # skipif fixture whose argument is True when lz4 is not installed
        pytest.skip("lz4 is not installed.")

    dump_filename = filename + "." + cmethod
    for obj in objects:
        numpy_pickle.dump(obj, dump_filename, compress=(cmethod, compress))
        # Verify the file contains the right magic number
        with open(dump_filename, "rb") as f:
            assert _detect_compressor(f) == cmethod
        # Verify the reloaded object is correct
        obj_reloaded = numpy_pickle.load(dump_filename)
        assert isinstance(obj_reloaded, type(obj))
        if isinstance(obj, np.ndarray):
            np.testing.assert_array_equal(obj_reloaded, obj)
        else:
            assert obj_reloaded == obj


def _gzip_file_decompress(source_filename, target_filename):
    """Decompress a gzip file."""
    with closing(gzip.GzipFile(source_filename, "rb")) as fo:
        buf = fo.read()

    with open(target_filename, "wb") as fo:
        fo.write(buf)


def _zlib_file_decompress(source_filename, target_filename):
    """Decompress a zlib file."""
    with open(source_filename, "rb") as fo:
        buf = zlib.decompress(fo.read())

    with open(target_filename, "wb") as fo:
        fo.write(buf)


@parametrize(
    "extension,decompress",
    [(".z", _zlib_file_decompress), (".gz", _gzip_file_decompress)],
)
def test_load_externally_decompressed_files(tmpdir, extension, decompress):
    # Test that BinaryZlibFile generates valid gzip and zlib compressed files.
    obj = "a string to persist"
    filename_raw = tmpdir.join("test.pkl").strpath

    filename_compressed = filename_raw + extension
    # Use automatic extension detection to compress with the right method.
    numpy_pickle.dump(obj, filename_compressed)

    # Decompress with the corresponding method
    decompress(filename_compressed, filename_raw)

    # Test that the uncompressed pickle can be loaded and
    # that the result is correct.
    obj_reloaded = numpy_pickle.load(filename_raw)
    assert obj == obj_reloaded


@parametrize(
    "extension,cmethod",
    # valid compressor extensions
    [
        (".z", "zlib"),
        (".gz", "gzip"),
        (".bz2", "bz2"),
        (".lzma", "lzma"),
        (".xz", "xz"),
        # invalid compressor extensions
        (".pkl", "not-compressed"),
        ("", "not-compressed"),
    ],
)
def test_compression_using_file_extension(tmpdir, extension, cmethod):
    if cmethod in ("lzma", "xz") and lzma is None:
        pytest.skip("lzma is missing")
    # test that compression method corresponds to the given filename extension.
    filename = tmpdir.join("test.pkl").strpath
    obj = "object to dump"

    dump_fname = filename + extension
    numpy_pickle.dump(obj, dump_fname)
    # Verify the file contains the right magic number
    with open(dump_fname, "rb") as f:
        assert _detect_compressor(f) == cmethod
    # Verify the reloaded object is correct
    obj_reloaded = numpy_pickle.load(dump_fname)
    assert isinstance(obj_reloaded, type(obj))
    assert obj_reloaded == obj


@with_numpy
def test_file_handle_persistence(tmpdir):
    objs = [np.random.random((10, 10)), "some data"]
    fobjs = [bz2.BZ2File, gzip.GzipFile]
    if lzma is not None:
        fobjs += [lzma.LZMAFile]
    filename = tmpdir.join("test.pkl").strpath

    for obj in objs:
        for fobj in fobjs:
            with fobj(filename, "wb") as f:
                numpy_pickle.dump(obj, f)

            # using the same decompressor prevents from internally
            # decompress again.
            with fobj(filename, "rb") as f:
                obj_reloaded = numpy_pickle.load(f)

            # when needed, the correct decompressor should be used when
            # passing a raw file handle.
            with open(filename, "rb") as f:
                obj_reloaded_2 = numpy_pickle.load(f)

            if isinstance(obj, np.ndarray):
                np.testing.assert_array_equal(obj_reloaded, obj)
                np.testing.assert_array_equal(obj_reloaded_2, obj)
            else:
                assert obj_reloaded == obj
                assert obj_reloaded_2 == obj


@with_numpy
def test_in_memory_persistence():
    objs = [np.random.random((10, 10)), "some data"]
    for obj in objs:
        f = io.BytesIO()
        numpy_pickle.dump(obj, f)
        obj_reloaded = numpy_pickle.load(f)
        if isinstance(obj, np.ndarray):
            np.testing.assert_array_equal(obj_reloaded, obj)
        else:
            assert obj_reloaded == obj


@with_numpy
def test_file_handle_persistence_mmap(tmpdir):
    obj = np.random.random((10, 10))
    filename = tmpdir.join("test.pkl").strpath

    with open(filename, "wb") as f:
        numpy_pickle.dump(obj, f)

    with open(filename, "rb") as f:
        obj_reloaded = numpy_pickle.load(f, mmap_mode="r+")

    np.testing.assert_array_equal(obj_reloaded, obj)


@with_numpy
def test_file_handle_persistence_compressed_mmap(tmpdir):
    obj = np.random.random((10, 10))
    filename = tmpdir.join("test.pkl").strpath

    with open(filename, "wb") as f:
        numpy_pickle.dump(obj, f, compress=("gzip", 3))

    with closing(gzip.GzipFile(filename, "rb")) as f:
        with warns(UserWarning) as warninfo:
            numpy_pickle.load(f, mmap_mode="r+")
        assert len(warninfo) == 1
        assert (
            str(warninfo[0].message)
            == '"%(fileobj)r" is not a raw file, mmap_mode "%(mmap_mode)s" '
            "flag will be ignored." % {"fileobj": f, "mmap_mode": "r+"}
        )


@with_numpy
def test_file_handle_persistence_in_memory_mmap():
    obj = np.random.random((10, 10))
    buf = io.BytesIO()

    numpy_pickle.dump(obj, buf)

    with warns(UserWarning) as warninfo:
        numpy_pickle.load(buf, mmap_mode="r+")
    assert len(warninfo) == 1
    assert (
        str(warninfo[0].message)
        == "In memory persistence is not compatible with mmap_mode "
        '"%(mmap_mode)s" flag passed. mmap_mode option will be '
        "ignored." % {"mmap_mode": "r+"}
    )


@parametrize(
    "data",
    [
        b"a little data as bytes.",
        # More bytes
        10000 * "{}".format(random.randint(0, 1000) * 1000).encode("latin-1"),
    ],
    ids=["a little data as bytes.", "a large data as bytes."],
)
@parametrize("compress_level", [1, 3, 9])
def test_binary_zlibfile(tmpdir, data, compress_level):
    filename = tmpdir.join("test.pkl").strpath
    # Regular cases
    with open(filename, "wb") as f:
        with BinaryZlibFile(f, "wb", compresslevel=compress_level) as fz:
            assert fz.writable()
            fz.write(data)
            assert fz.fileno() == f.fileno()
            with raises(io.UnsupportedOperation):
                fz._check_can_read()

            with raises(io.UnsupportedOperation):
                fz._check_can_seek()
        assert fz.closed
        with raises(ValueError):
            fz._check_not_closed()

    with open(filename, "rb") as f:
        with BinaryZlibFile(f) as fz:
            assert fz.readable()
            assert fz.seekable()
            assert fz.fileno() == f.fileno()
            assert fz.read() == data
            with raises(io.UnsupportedOperation):
                fz._check_can_write()
            assert fz.seekable()
            fz.seek(0)
            assert fz.tell() == 0
        assert fz.closed

    # Test with a filename as input
    with BinaryZlibFile(filename, "wb", compresslevel=compress_level) as fz:
        assert fz.writable()
        fz.write(data)

    with BinaryZlibFile(filename, "rb") as fz:
        assert fz.read() == data
        assert fz.seekable()

    # Test without context manager
    fz = BinaryZlibFile(filename, "wb", compresslevel=compress_level)
    assert fz.writable()
    fz.write(data)
    fz.close()

    fz = BinaryZlibFile(filename, "rb")
    assert fz.read() == data
    fz.close()


@parametrize("bad_value", [-1, 10, 15, "a", (), {}])
def test_binary_zlibfile_bad_compression_levels(tmpdir, bad_value):
    filename = tmpdir.join("test.pkl").strpath
    with raises(ValueError) as excinfo:
        BinaryZlibFile(filename, "wb", compresslevel=bad_value)
    pattern = re.escape(
        "'compresslevel' must be an integer between 1 and 9. "
        "You provided 'compresslevel={}'".format(bad_value)
    )
    excinfo.match(pattern)


@parametrize("bad_mode", ["a", "x", "r", "w", 1, 2])
def test_binary_zlibfile_invalid_modes(tmpdir, bad_mode):
    filename = tmpdir.join("test.pkl").strpath
    with raises(ValueError) as excinfo:
        BinaryZlibFile(filename, bad_mode)
    excinfo.match("Invalid mode")


@parametrize("bad_file", [1, (), {}])
def test_binary_zlibfile_invalid_filename_type(bad_file):
    with raises(TypeError) as excinfo:
        BinaryZlibFile(bad_file, "rb")
    excinfo.match("filename must be a str or bytes object, or a file")


###############################################################################
# Test dumping array subclasses
if np is not None:

    class SubArray(np.ndarray):
        def __reduce__(self):
            return _load_sub_array, (np.asarray(self),)

    def _load_sub_array(arr):
        d = SubArray(arr.shape)
        d[:] = arr
        return d

    class ComplexTestObject:
        """A complex object containing numpy arrays as attributes."""

        def __init__(self):
            self.array_float = np.arange(100, dtype="float64")
            self.array_int = np.ones(100, dtype="int32")
            self.array_obj = np.array(["a", 10, 20.0], dtype="object")


@with_numpy
def test_numpy_subclass(tmpdir):
    filename = tmpdir.join("test.pkl").strpath
    a = SubArray((10,))
    numpy_pickle.dump(a, filename)
    c = numpy_pickle.load(filename)
    assert isinstance(c, SubArray)
    np.testing.assert_array_equal(c, a)


def test_pathlib(tmpdir):
    filename = tmpdir.join("test.pkl").strpath
    value = 123
    numpy_pickle.dump(value, Path(filename))
    assert numpy_pickle.load(filename) == value
    numpy_pickle.dump(value, filename)
    assert numpy_pickle.load(Path(filename)) == value


@with_numpy
def test_non_contiguous_array_pickling(tmpdir):
    filename = tmpdir.join("test.pkl").strpath

    for array in [  # Array that triggers a contiguousness issue with nditer,
        # see https://github.com/joblib/joblib/pull/352 and see
        # https://github.com/joblib/joblib/pull/353
        np.asfortranarray([[1, 2], [3, 4]])[1:],
        # Non contiguous array with works fine with nditer
        np.ones((10, 50, 20), order="F")[:, :1, :],
    ]:
        assert not array.flags.c_contiguous
        assert not array.flags.f_contiguous
        numpy_pickle.dump(array, filename)
        array_reloaded = numpy_pickle.load(filename)
        np.testing.assert_array_equal(array_reloaded, array)


@with_numpy
def test_pickle_highest_protocol(tmpdir):
    # ensure persistence of a numpy array is valid even when using
    # the pickle HIGHEST_PROTOCOL.
    # see https://github.com/joblib/joblib/issues/362

    filename = tmpdir.join("test.pkl").strpath
    test_array = np.zeros(10)

    numpy_pickle.dump(test_array, filename, protocol=pickle.HIGHEST_PROTOCOL)
    array_reloaded = numpy_pickle.load(filename)

    np.testing.assert_array_equal(array_reloaded, test_array)


@with_numpy
def test_pickle_in_socket():
    # test that joblib can pickle in sockets
    test_array = np.arange(10)
    _ADDR = ("localhost", 12345)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(_ADDR)
    listener.listen(1)

    with socket.create_connection(_ADDR) as client:
        server, client_addr = listener.accept()

        with server.makefile("wb") as sf:
            numpy_pickle.dump(test_array, sf)

        with client.makefile("rb") as cf:
            array_reloaded = numpy_pickle.load(cf)

        np.testing.assert_array_equal(array_reloaded, test_array)

        # Check that a byte-aligned numpy array written in a file can be send
        # over a socket and then read on the other side
        bytes_to_send = io.BytesIO()
        numpy_pickle.dump(test_array, bytes_to_send)
        server.send(bytes_to_send.getvalue())

        with client.makefile("rb") as cf:
            array_reloaded = numpy_pickle.load(cf)

        np.testing.assert_array_equal(array_reloaded, test_array)


@with_numpy
def test_load_memmap_with_big_offset(tmpdir):
    # Test that numpy memmap offset is set correctly if greater than
    # mmap.ALLOCATIONGRANULARITY, see
    # https://github.com/joblib/joblib/issues/451 and
    # https://github.com/numpy/numpy/pull/8443 for more details.
    fname = tmpdir.join("test.mmap").strpath
    size = mmap.ALLOCATIONGRANULARITY
    obj = [np.zeros(size, dtype="uint8"), np.ones(size, dtype="uint8")]
    numpy_pickle.dump(obj, fname)
    memmaps = numpy_pickle.load(fname, mmap_mode="r")
    assert isinstance(memmaps[1], np.memmap)
    assert memmaps[1].offset > size
    np.testing.assert_array_equal(obj, memmaps)


def test_register_compressor(tmpdir):
    # Check that registering compressor file works.
    compressor_name = "test-name"
    compressor_prefix = "test-prefix"

    class BinaryCompressorTestFile(io.BufferedIOBase):
        pass

    class BinaryCompressorTestWrapper(CompressorWrapper):
        def __init__(self):
            CompressorWrapper.__init__(
                self, obj=BinaryCompressorTestFile, prefix=compressor_prefix
            )

    register_compressor(compressor_name, BinaryCompressorTestWrapper())

    assert _COMPRESSORS[compressor_name].fileobj_factory == BinaryCompressorTestFile
    assert _COMPRESSORS[compressor_name].prefix == compressor_prefix

    # Remove this dummy compressor file from extra compressors because other
    # tests might fail because of this
    _COMPRESSORS.pop(compressor_name)


@parametrize("invalid_name", [1, (), {}])
def test_register_compressor_invalid_name(invalid_name):
    # Test that registering an invalid compressor name is not allowed.
    with raises(ValueError) as excinfo:
        register_compressor(invalid_name, None)
    excinfo.match("Compressor name should be a string")


def test_register_compressor_invalid_fileobj():
    # Test that registering an invalid file object is not allowed.

    class InvalidFileObject:
        pass

    class InvalidFileObjectWrapper(CompressorWrapper):
        def __init__(self):
            CompressorWrapper.__init__(self, obj=InvalidFileObject, prefix=b"prefix")

    with raises(ValueError) as excinfo:
        register_compressor("invalid", InvalidFileObjectWrapper())

    excinfo.match(
        "Compressor 'fileobj_factory' attribute should implement "
        "the file object interface"
    )


class AnotherZlibCompressorWrapper(CompressorWrapper):
    def __init__(self):
        CompressorWrapper.__init__(self, obj=BinaryZlibFile, prefix=b"prefix")


class StandardLibGzipCompressorWrapper(CompressorWrapper):
    def __init__(self):
        CompressorWrapper.__init__(self, obj=gzip.GzipFile, prefix=b"prefix")


def test_register_compressor_already_registered():
    # Test registration of existing compressor files.
    compressor_name = "test-name"

    # register a test compressor
    register_compressor(compressor_name, AnotherZlibCompressorWrapper())

    with raises(ValueError) as excinfo:
        register_compressor(compressor_name, StandardLibGzipCompressorWrapper())
    excinfo.match("Compressor '{}' already registered.".format(compressor_name))

    register_compressor(compressor_name, StandardLibGzipCompressorWrapper(), force=True)

    assert compressor_name in _COMPRESSORS
    assert _COMPRESSORS[compressor_name].fileobj_factory == gzip.GzipFile

    # Remove this dummy compressor file from extra compressors because other
    # tests might fail because of this
    _COMPRESSORS.pop(compressor_name)


@with_lz4
def test_lz4_compression(tmpdir):
    # Check that lz4 can be used when dependency is available.
    import lz4.frame

    compressor = "lz4"
    assert compressor in _COMPRESSORS
    assert _COMPRESSORS[compressor].fileobj_factory == lz4.frame.LZ4FrameFile

    fname = tmpdir.join("test.pkl").strpath
    data = "test data"
    numpy_pickle.dump(data, fname, compress=compressor)

    with open(fname, "rb") as f:
        assert f.read(len(_LZ4_PREFIX)) == _LZ4_PREFIX
    assert numpy_pickle.load(fname) == data

    # Test that LZ4 is applied based on file extension
    numpy_pickle.dump(data, fname + ".lz4")
    with open(fname, "rb") as f:
        assert f.read(len(_LZ4_PREFIX)) == _LZ4_PREFIX
    assert numpy_pickle.load(fname) == data


@without_lz4
def test_lz4_compression_without_lz4(tmpdir):
    # Check that lz4 cannot be used when dependency is not available.
    fname = tmpdir.join("test.nolz4").strpath
    data = "test data"
    msg = LZ4_NOT_INSTALLED_ERROR
    with raises(ValueError) as excinfo:
        numpy_pickle.dump(data, fname, compress="lz4")
    excinfo.match(msg)

    with raises(ValueError) as excinfo:
        numpy_pickle.dump(data, fname + ".lz4")
    excinfo.match(msg)


protocols = [pickle.DEFAULT_PROTOCOL]
if pickle.HIGHEST_PROTOCOL != pickle.DEFAULT_PROTOCOL:
    protocols.append(pickle.HIGHEST_PROTOCOL)


@with_numpy
@parametrize("protocol", protocols)
def test_memmap_alignment_padding(tmpdir, protocol):
    # Test that memmaped arrays returned by numpy.load are correctly aligned
    fname = tmpdir.join("test.mmap").strpath

    a = np.random.randn(2)
    numpy_pickle.dump(a, fname, protocol=protocol)
    memmap = numpy_pickle.load(fname, mmap_mode="r")
    assert isinstance(memmap, np.memmap)
    np.testing.assert_array_equal(a, memmap)
    assert memmap.ctypes.data % numpy_pickle.NUMPY_ARRAY_ALIGNMENT_BYTES == 0
    assert memmap.flags.aligned

    array_list = [
        np.random.randn(2),
        np.random.randn(2),
        np.random.randn(2),
        np.random.randn(2),
    ]

    # On Windows OSError 22 if reusing the same path for memmap ...
    fname = tmpdir.join("test1.mmap").strpath
    numpy_pickle.dump(array_list, fname, protocol=protocol)
    l_reloaded = numpy_pickle.load(fname, mmap_mode="r")

    for idx, memmap in enumerate(l_reloaded):
        assert isinstance(memmap, np.memmap)
        np.testing.assert_array_equal(array_list[idx], memmap)
        assert memmap.ctypes.data % numpy_pickle.NUMPY_ARRAY_ALIGNMENT_BYTES == 0
        assert memmap.flags.aligned

    array_dict = {
        "a0": np.arange(2, dtype=np.uint8),
        "a1": np.arange(3, dtype=np.uint8),
        "a2": np.arange(5, dtype=np.uint8),
        "a3": np.arange(7, dtype=np.uint8),
        "a4": np.arange(11, dtype=np.uint8),
        "a5": np.arange(13, dtype=np.uint8),
        "a6": np.arange(17, dtype=np.uint8),
        "a7": np.arange(19, dtype=np.uint8),
        "a8": np.arange(23, dtype=np.uint8),
    }

    # On Windows OSError 22 if reusing the same path for memmap ...
    fname = tmpdir.join("test2.mmap").strpath
    numpy_pickle.dump(array_dict, fname, protocol=protocol)
    d_reloaded = numpy_pickle.load(fname, mmap_mode="r")

    for key, memmap in d_reloaded.items():
        assert isinstance(memmap, np.memmap)
        np.testing.assert_array_equal(array_dict[key], memmap)
        assert memmap.ctypes.data % numpy_pickle.NUMPY_ARRAY_ALIGNMENT_BYTES == 0
        assert memmap.flags.aligned

# === NexusCore/openenv\Lib\site-packages\IPython\core\history.py ===
"""History related magics and functionality"""

from __future__ import annotations

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


import atexit
import datetime
import re


import threading
from pathlib import Path

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from decorator import decorator
from traitlets import (
    Any,
    Bool,
    Dict,
    Instance,
    Integer,
    List,
    TraitError,
    Unicode,
    Union,
    default,
    observe,
)
from traitlets.config.configurable import LoggingConfigurable

from IPython.paths import locate_profile
from IPython.utils.decorators import undoc
from typing import Iterable, Tuple, Optional, TYPE_CHECKING
import typing
from warnings import warn
from weakref import ref, WeakSet

if TYPE_CHECKING:
    from IPython.core.interactiveshell import InteractiveShell
    from IPython.config.Configuration import Configuration

try:
    from sqlite3 import DatabaseError, OperationalError
    import sqlite3

    sqlite3.register_converter(
        "timestamp", lambda val: datetime.datetime.fromisoformat(val.decode())
    )

    sqlite3_found = True
except ModuleNotFoundError:
    sqlite3_found = False

    class DatabaseError(Exception):  # type: ignore [no-redef]
        pass

    class OperationalError(Exception):  # type: ignore [no-redef]
        pass


InOrInOut = typing.Union[str, tuple[str, Optional[str]]]

# -----------------------------------------------------------------------------
# Classes and functions
# -----------------------------------------------------------------------------


@undoc
class DummyDB:
    """Dummy DB that will act as a black hole for history.

    Only used in the absence of sqlite"""

    def execute(*args: typing.Any, **kwargs: typing.Any) -> list:
        return []

    def commit(self, *args, **kwargs):  # type: ignore [no-untyped-def]
        pass

    def __enter__(self, *args, **kwargs):  # type: ignore [no-untyped-def]
        pass

    def __exit__(self, *args, **kwargs):  # type: ignore [no-untyped-def]
        pass


@decorator
def only_when_enabled(f, self, *a, **kw):  # type: ignore [no-untyped-def]
    """Decorator: return an empty list in the absence of sqlite."""
    if not self.enabled:
        return []
    else:
        return f(self, *a, **kw)


# use 16kB as threshold for whether a corrupt history db should be saved
# that should be at least 100 entries or so
_SAVE_DB_SIZE = 16384


@decorator
def catch_corrupt_db(f, self, *a, **kw):  # type: ignore [no-untyped-def]
    """A decorator which wraps HistoryAccessor method calls to catch errors from
    a corrupt SQLite database, move the old database out of the way, and create
    a new one.

    We avoid clobbering larger databases because this may be triggered due to filesystem issues,
    not just a corrupt file.
    """
    try:
        return f(self, *a, **kw)
    except (DatabaseError, OperationalError) as e:
        self._corrupt_db_counter += 1
        self.log.error("Failed to open SQLite history %s (%s).", self.hist_file, e)
        if self.hist_file != ":memory:":
            if self._corrupt_db_counter > self._corrupt_db_limit:
                self.hist_file = ":memory:"
                self.log.error(
                    "Failed to load history too many times, history will not be saved."
                )
            elif self.hist_file.is_file():
                # move the file out of the way
                base = str(self.hist_file.parent / self.hist_file.stem)
                ext = self.hist_file.suffix
                size = self.hist_file.stat().st_size
                if size >= _SAVE_DB_SIZE:
                    # if there's significant content, avoid clobbering
                    now = (
                        datetime.datetime.now(datetime.timezone.utc)
                        .isoformat()
                        .replace(":", ".")
                    )
                    newpath = base + "-corrupt-" + now + ext
                    # don't clobber previous corrupt backups
                    for i in range(100):
                        if not Path(newpath).exists():
                            break
                        else:
                            newpath = base + "-corrupt-" + now + ("-%i" % i) + ext
                else:
                    # not much content, possibly empty; don't worry about clobbering
                    # maybe we should just delete it?
                    newpath = base + "-corrupt" + ext
                self.hist_file.rename(newpath)
                self.log.error(
                    "History file was moved to %s and a new file created.", newpath
                )
            self.init_db()
            return []
        else:
            # Failed with :memory:, something serious is wrong
            raise


class HistoryAccessorBase(LoggingConfigurable):
    """An abstract class for History Accessors"""

    def get_tail(
        self,
        n: int = 10,
        raw: bool = True,
        output: bool = False,
        include_latest: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        raise NotImplementedError

    def search(
        self,
        pattern: str = "*",
        raw: bool = True,
        search_raw: bool = True,
        output: bool = False,
        n: Optional[int] = None,
        unique: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        raise NotImplementedError

    def get_range(
        self,
        session: int,
        start: int = 1,
        stop: Optional[int] = None,
        raw: bool = True,
        output: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        raise NotImplementedError

    def get_range_by_str(
        self, rangestr: str, raw: bool = True, output: bool = False
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        raise NotImplementedError


class HistoryAccessor(HistoryAccessorBase):
    """Access the history database without adding to it.

    This is intended for use by standalone history tools. IPython shells use
    HistoryManager, below, which is a subclass of this."""

    # counter for init_db retries, so we don't keep trying over and over
    _corrupt_db_counter = 0
    # after two failures, fallback on :memory:
    _corrupt_db_limit = 2

    # String holding the path to the history file
    hist_file = Union(
        [Instance(Path), Unicode()],
        help="""Path to file to use for SQLite history database.

        By default, IPython will put the history database in the IPython
        profile directory.  If you would rather share one history among
        profiles, you can set this value in each, so that they are consistent.

        Due to an issue with fcntl, SQLite is known to misbehave on some NFS
        mounts.  If you see IPython hanging, try setting this to something on a
        local disk, e.g::

            ipython --HistoryManager.hist_file=/tmp/ipython_hist.sqlite

        you can also use the specific value `:memory:` (including the colon
        at both end but not the back ticks), to avoid creating an history file.

        """,
    ).tag(config=True)

    enabled = Bool(
        sqlite3_found,
        help="""enable the SQLite history

        set enabled=False to disable the SQLite history,
        in which case there will be no stored history, no SQLite connection,
        and no background saving thread.  This may be necessary in some
        threaded environments where IPython is embedded.
        """,
    ).tag(config=True)

    connection_options = Dict(
        help="""Options for configuring the SQLite connection

        These options are passed as keyword args to sqlite3.connect
        when establishing database connections.
        """
    ).tag(config=True)

    @default("connection_options")
    def _default_connection_options(self) -> dict[str, bool]:
        return dict(check_same_thread=False)

    # The SQLite database
    db = Any()

    @observe("db")
    @only_when_enabled
    def _db_changed(self, change):  # type: ignore [no-untyped-def]
        """validate the db, since it can be an Instance of two different types"""
        new = change["new"]
        connection_types = (DummyDB, sqlite3.Connection)
        if not isinstance(new, connection_types):
            msg = "%s.db must be sqlite3 Connection or DummyDB, not %r" % (
                self.__class__.__name__,
                new,
            )
            raise TraitError(msg)

    def __init__(
        self, profile: str = "default", hist_file: str = "", **traits: typing.Any
    ) -> None:
        """Create a new history accessor.

        Parameters
        ----------
        profile : str
            The name of the profile from which to open history.
        hist_file : str
            Path to an SQLite history database stored by IPython. If specified,
            hist_file overrides profile.
        config : :class:`~traitlets.config.loader.Config`
            Config object. hist_file can also be set through this.
        """
        super(HistoryAccessor, self).__init__(**traits)
        # defer setting hist_file from kwarg until after init,
        # otherwise the default kwarg value would clobber any value
        # set by config
        if hist_file:
            self.hist_file = hist_file

        try:
            self.hist_file
        except TraitError:
            # No one has set the hist_file, yet.
            self.hist_file = self._get_hist_file_name(profile)

        self.init_db()

    def _get_hist_file_name(self, profile: str = "default") -> Path:
        """Find the history file for the given profile name.

        This is overridden by the HistoryManager subclass, to use the shell's
        active profile.

        Parameters
        ----------
        profile : str
            The name of a profile which has a history file.
        """
        return Path(locate_profile(profile)) / "history.sqlite"

    @catch_corrupt_db
    def init_db(self) -> None:
        """Connect to the database, and create tables if necessary."""
        if not self.enabled:
            self.db = DummyDB()
            return

        # use detect_types so that timestamps return datetime objects
        kwargs = dict(detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        kwargs.update(self.connection_options)
        self.db = sqlite3.connect(str(self.hist_file), **kwargs)  # type: ignore [call-overload]
        with self.db:
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS sessions (session integer
                            primary key autoincrement, start timestamp,
                            end timestamp, num_cmds integer, remark text)"""
            )
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS history
                    (session integer, line integer, source text, source_raw text,
                    PRIMARY KEY (session, line))"""
            )
            # Output history is optional, but ensure the table's there so it can be
            # enabled later.
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS output_history
                            (session integer, line integer, output text,
                            PRIMARY KEY (session, line))"""
            )
        # success! reset corrupt db count
        self._corrupt_db_counter = 0

    def writeout_cache(self) -> None:
        """Overridden by HistoryManager to dump the cache before certain
        database lookups."""
        pass

    ## -------------------------------
    ## Methods for retrieving history:
    ## -------------------------------
    def _run_sql(
        self,
        sql: str,
        params: tuple,
        raw: bool = True,
        output: bool = False,
        latest: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Prepares and runs an SQL query for the history database.

        Parameters
        ----------
        sql : str
            Any filtering expressions to go after SELECT ... FROM ...
        params : tuple
            Parameters passed to the SQL query (to replace "?")
        raw, output : bool
            See :meth:`get_range`
        latest : bool
            Select rows with max (session, line)

        Returns
        -------
        Tuples as :meth:`get_range`
        """
        toget = "source_raw" if raw else "source"
        sqlfrom = "history"
        if output:
            sqlfrom = "history LEFT JOIN output_history USING (session, line)"
            toget = "history.%s, output_history.output" % toget
        if latest:
            toget += ", MAX(session * 128 * 1024 + line)"
        this_querry = "SELECT session, line, %s FROM %s " % (toget, sqlfrom) + sql
        cur = self.db.execute(this_querry, params)
        if latest:
            cur = (row[:-1] for row in cur)
        if output:  # Regroup into 3-tuples, and parse JSON
            return ((ses, lin, (inp, out)) for ses, lin, inp, out in cur)
        return cur

    @only_when_enabled
    @catch_corrupt_db
    def get_session_info(
        self, session: int
    ) -> tuple[int, datetime.datetime, Optional[datetime.datetime], Optional[int], str]:
        """Get info about a session.

        Parameters
        ----------
        session : int
            Session number to retrieve.

        Returns
        -------
        session_id : int
            Session ID number
        start : datetime
            Timestamp for the start of the session.
        end : datetime
            Timestamp for the end of the session, or None if IPython crashed.
        num_cmds : int
            Number of commands run, or None if IPython crashed.
        remark : str
            A manually set description.
        """
        query = "SELECT * from sessions where session == ?"
        return self.db.execute(query, (session,)).fetchone()

    @catch_corrupt_db
    def get_last_session_id(self) -> Optional[int]:
        """Get the last session ID currently in the database.

        Within IPython, this should be the same as the value stored in
        :attr:`HistoryManager.session_number`.
        """
        for record in self.get_tail(n=1, include_latest=True):
            return record[0]
        return None

    @catch_corrupt_db
    def get_tail(
        self,
        n: int = 10,
        raw: bool = True,
        output: bool = False,
        include_latest: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Get the last n lines from the history database.

        Parameters
        ----------
        n : int
            The number of lines to get
        raw, output : bool
            See :meth:`get_range`
        include_latest : bool
            If False (default), n+1 lines are fetched, and the latest one
            is discarded. This is intended to be used where the function
            is called by a user command, which it should not return.

        Returns
        -------
        Tuples as :meth:`get_range`
        """
        self.writeout_cache()
        if not include_latest:
            n += 1
        cur = self._run_sql(
            "ORDER BY session DESC, line DESC LIMIT ?", (n,), raw=raw, output=output
        )
        if not include_latest:
            return reversed(list(cur)[1:])
        return reversed(list(cur))

    @catch_corrupt_db
    def search(
        self,
        pattern: str = "*",
        raw: bool = True,
        search_raw: bool = True,
        output: bool = False,
        n: Optional[int] = None,
        unique: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Search the database using unix glob-style matching (wildcards
        * and ?).

        Parameters
        ----------
        pattern : str
            The wildcarded pattern to match when searching
        search_raw : bool
            If True, search the raw input, otherwise, the parsed input
        raw, output : bool
            See :meth:`get_range`
        n : None or int
            If an integer is given, it defines the limit of
            returned entries.
        unique : bool
            When it is true, return only unique entries.

        Returns
        -------
        Tuples as :meth:`get_range`
        """
        tosearch = "source_raw" if search_raw else "source"
        if output:
            tosearch = "history." + tosearch
        self.writeout_cache()
        sqlform = "WHERE %s GLOB ?" % tosearch
        params: tuple[typing.Any, ...] = (pattern,)
        if unique:
            sqlform += " GROUP BY {0}".format(tosearch)
        if n is not None:
            sqlform += " ORDER BY session DESC, line DESC LIMIT ?"
            params += (n,)
        elif unique:
            sqlform += " ORDER BY session, line"
        cur = self._run_sql(sqlform, params, raw=raw, output=output, latest=unique)
        if n is not None:
            return reversed(list(cur))
        return cur

    @catch_corrupt_db
    def get_range(
        self,
        session: int,
        start: int = 1,
        stop: Optional[int] = None,
        raw: bool = True,
        output: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Retrieve input by session.

        Parameters
        ----------
        session : int
            Session number to retrieve.
        start : int
            First line to retrieve.
        stop : int
            End of line range (excluded from output itself). If None, retrieve
            to the end of the session.
        raw : bool
            If True, return untranslated input
        output : bool
            If True, attempt to include output. This will be 'real' Python
            objects for the current session, or text reprs from previous
            sessions if db_log_output was enabled at the time. Where no output
            is found, None is used.

        Returns
        -------
        entries
            An iterator over the desired lines. Each line is a 3-tuple, either
            (session, line, input) if output is False, or
            (session, line, (input, output)) if output is True.
        """
        params: tuple[typing.Any, ...]
        if stop:
            lineclause = "line >= ? AND line < ?"
            params = (session, start, stop)
        else:
            lineclause = "line>=?"
            params = (session, start)

        return self._run_sql(
            "WHERE session==? AND %s" % lineclause, params, raw=raw, output=output
        )

    def get_range_by_str(
        self, rangestr: str, raw: bool = True, output: bool = False
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Get lines of history from a string of ranges, as used by magic
        commands %hist, %save, %macro, etc.

        Parameters
        ----------
        rangestr : str
            A string specifying ranges, e.g. "5 ~2/1-4". If empty string is used,
            this will return everything from current session's history.

            See the documentation of :func:`%history` for the full details.

        raw, output : bool
            As :meth:`get_range`

        Returns
        -------
        Tuples as :meth:`get_range`
        """
        for sess, s, e in extract_hist_ranges(rangestr):
            yield from self.get_range(sess, s, e, raw=raw, output=output)


@dataclass
class HistoryOutput:
    output_type: typing.Literal[
        "out_stream", "err_stream", "display_data", "execute_result"
    ]
    bundle: typing.Dict[str, str]


class HistoryManager(HistoryAccessor):
    """A class to organize all history-related functionality in one place."""

    # Public interface

    # An instance of the IPython shell we are attached to
    shell = Instance(
        "IPython.core.interactiveshell.InteractiveShellABC", allow_none=False
    )
    # Lists to hold processed and raw history. These start with a blank entry
    # so that we can index them starting from 1
    input_hist_parsed = List([""])
    input_hist_raw = List([""])
    # A list of directories visited during session
    dir_hist: List = List()

    @default("dir_hist")
    def _dir_hist_default(self) -> list[Path]:
        try:
            return [Path.cwd()]
        except OSError:
            return []

    # A dict of output history, keyed with ints from the shell's
    # execution count.
    output_hist = Dict()
    # The text/plain repr of outputs.
    output_hist_reprs: typing.Dict[int, str] = Dict()  # type: ignore [assignment]
    # Maps execution_count to MIME bundles
    outputs: typing.Dict[int, typing.List[HistoryOutput]] = defaultdict(list)
    # Maps execution_count to exception tracebacks
    exceptions: typing.Dict[int, typing.Dict[str, Any]] = Dict()  # type: ignore [assignment]

    # The number of the current session in the history database
    session_number: int = Integer()  # type: ignore [assignment]

    db_log_output = Bool(
        False, help="Should the history database include output? (default: no)"
    ).tag(config=True)
    db_cache_size = Integer(
        0,
        help="Write to database every x commands (higher values save disk access & power).\n"
        "Values of 1 or less effectively disable caching.",
    ).tag(config=True)
    # The input and output caches
    db_input_cache: List[tuple[int, str, str]] = List()
    db_output_cache: List[tuple[int, str]] = List()

    # History saving in separate thread
    save_thread = Instance("IPython.core.history.HistorySavingThread", allow_none=True)

    @property
    def save_flag(self) -> threading.Event | None:
        if self.save_thread is not None:
            return self.save_thread.save_flag
        return None

    # Private interface
    # Variables used to store the three last inputs from the user.  On each new
    # history update, we populate the user's namespace with these, shifted as
    # necessary.
    _i00 = Unicode("")
    _i = Unicode("")
    _ii = Unicode("")
    _iii = Unicode("")

    # A regex matching all forms of the exit command, so that we don't store
    # them in the history (it's annoying to rewind the first entry and land on
    # an exit call).
    _exit_re = re.compile(r"(exit|quit)(\s*\(.*\))?$")

    _instances: WeakSet[HistoryManager] = WeakSet()
    _max_inst: int | float = float("inf")

    def __init__(
        self,
        shell: InteractiveShell,
        config: Optional[Configuration] = None,
        **traits: typing.Any,
    ):
        """Create a new history manager associated with a shell instance."""
        super().__init__(shell=shell, config=config, **traits)
        self.db_input_cache_lock = threading.Lock()
        self.db_output_cache_lock = threading.Lock()

        try:
            self.new_session()
        except OperationalError:
            self.log.error(
                "Failed to create history session in %s. History will not be saved.",
                self.hist_file,
                exc_info=True,
            )
            self.hist_file = ":memory:"

        if self.enabled and self.hist_file != ":memory:":
            self.save_thread = HistorySavingThread(self)
            try:
                self.save_thread.start()
            except RuntimeError:
                self.log.error(
                    "Failed to start history saving thread. History will not be saved.",
                    exc_info=True,
                )
                self.hist_file = ":memory:"
        self._instances.add(self)
        assert len(HistoryManager._instances) <= HistoryManager._max_inst, (
            len(HistoryManager._instances),
            HistoryManager._max_inst,
        )

    def __del__(self) -> None:
        if self.save_thread is not None:
            self.save_thread.stop()

    def _get_hist_file_name(self, profile: Optional[str] = None) -> Path:
        """Get default history file name based on the Shell's profile.

        The profile parameter is ignored, but must exist for compatibility with
        the parent class."""
        profile_dir = self.shell.profile_dir.location
        return Path(profile_dir) / "history.sqlite"

    @only_when_enabled
    def new_session(self, conn: Optional[sqlite3.Connection] = None) -> None:
        """Get a new session number."""
        if conn is None:
            conn = self.db

        with conn:
            cur = conn.execute(
                """INSERT INTO sessions VALUES (NULL, ?, NULL,
                            NULL, '') """,
                (datetime.datetime.now().isoformat(" "),),
            )
            assert isinstance(cur.lastrowid, int)
            self.session_number = cur.lastrowid

    def end_session(self) -> None:
        """Close the database session, filling in the end time and line count."""
        self.writeout_cache()
        with self.db:
            self.db.execute(
                """UPDATE sessions SET end=?, num_cmds=? WHERE
                            session==?""",
                (
                    datetime.datetime.now(datetime.timezone.utc).isoformat(" "),
                    len(self.input_hist_parsed) - 1,
                    self.session_number,
                ),
            )
        self.session_number = 0

    def name_session(self, name: str) -> None:
        """Give the current session a name in the history database."""
        warn(
            "name_session is deprecated in IPython 9.0 and will be removed in future versions",
            DeprecationWarning,
            stacklevel=2,
        )
        with self.db:
            self.db.execute(
                "UPDATE sessions SET remark=? WHERE session==?",
                (name, self.session_number),
            )

    def reset(self, new_session: bool = True) -> None:
        """Clear the session history, releasing all object references, and
        optionally open a new session."""
        self.output_hist.clear()
        self.outputs.clear()
        self.exceptions.clear()

        # The directory history can't be completely empty
        self.dir_hist[:] = [Path.cwd()]

        if new_session:
            if self.session_number:
                self.end_session()
            self.input_hist_parsed[:] = [""]
            self.input_hist_raw[:] = [""]
            self.new_session()

    # ------------------------------
    # Methods for retrieving history
    # ------------------------------
    def get_session_info(
        self, session: int = 0
    ) -> tuple[int, datetime.datetime, Optional[datetime.datetime], Optional[int], str]:
        """Get info about a session.

        Parameters
        ----------
        session : int
            Session number to retrieve. The current session is 0, and negative
            numbers count back from current session, so -1 is the previous session.

        Returns
        -------
        session_id : int
            Session ID number
        start : datetime
            Timestamp for the start of the session.
        end : datetime
            Timestamp for the end of the session, or None if IPython crashed.
        num_cmds : int
            Number of commands run, or None if IPython crashed.
        remark : str
            A manually set description.
        """
        if session <= 0:
            session += self.session_number

        return super(HistoryManager, self).get_session_info(session=session)

    @catch_corrupt_db
    def get_tail(
        self,
        n: int = 10,
        raw: bool = True,
        output: bool = False,
        include_latest: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Get the last n lines from the history database.

        Most recent entry last.

        Completion will be reordered so that that the last ones are when
        possible from current session.

        Parameters
        ----------
        n : int
            The number of lines to get
        raw, output : bool
            See :meth:`get_range`
        include_latest : bool
            If False (default), n+1 lines are fetched, and the latest one
            is discarded. This is intended to be used where the function
            is called by a user command, which it should not return.

        Returns
        -------
        Tuples as :meth:`get_range`
        """
        self.writeout_cache()
        if not include_latest:
            n += 1
        # cursor/line/entry
        this_cur = list(
            self._run_sql(
                "WHERE session == ? ORDER BY line DESC LIMIT ?  ",
                (self.session_number, n),
                raw=raw,
                output=output,
            )
        )
        other_cur = list(
            self._run_sql(
                "WHERE session != ? ORDER BY session DESC, line DESC LIMIT ?",
                (self.session_number, n),
                raw=raw,
                output=output,
            )
        )

        everything: list[tuple[int, int, InOrInOut]] = this_cur + other_cur

        everything = everything[:n]

        if not include_latest:
            return list(everything)[:0:-1]
        return list(everything)[::-1]

    def _get_range_session(
        self,
        start: int = 1,
        stop: Optional[int] = None,
        raw: bool = True,
        output: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Get input and output history from the current session. Called by
        get_range, and takes similar parameters."""
        input_hist = self.input_hist_raw if raw else self.input_hist_parsed

        n = len(input_hist)
        if start < 0:
            start += n
        if not stop or (stop > n):
            stop = n
        elif stop < 0:
            stop += n
        line: InOrInOut
        for i in range(start, stop):
            if output:
                line = (input_hist[i], self.output_hist_reprs.get(i))
            else:
                line = input_hist[i]
            yield (0, i, line)

    def get_range(
        self,
        session: int = 0,
        start: int = 1,
        stop: Optional[int] = None,
        raw: bool = True,
        output: bool = False,
    ) -> Iterable[tuple[int, int, InOrInOut]]:
        """Retrieve input by session.

        Parameters
        ----------
        session : int
            Session number to retrieve. The current session is 0, and negative
            numbers count back from current session, so -1 is previous session.
        start : int
            First line to retrieve.
        stop : int
            End of line range (excluded from output itself). If None, retrieve
            to the end of the session.
        raw : bool
            If True, return untranslated input
        output : bool
            If True, attempt to include output. This will be 'real' Python
            objects for the current session, or text reprs from previous
            sessions if db_log_output was enabled at the time. Where no output
            is found, None is used.

        Returns
        -------
        entries
            An iterator over the desired lines. Each line is a 3-tuple, either
            (session, line, input) if output is False, or
            (session, line, (input, output)) if output is True.
        """
        if session <= 0:
            session += self.session_number
        if session == self.session_number:  # Current session
            return self._get_range_session(start, stop, raw, output)
        return super(HistoryManager, self).get_range(session, start, stop, raw, output)

    ## ----------------------------
    ## Methods for storing history:
    ## ----------------------------
    def store_inputs(
        self, line_num: int, source: str, source_raw: Optional[str] = None
    ) -> None:
        """Store source and raw input in history and create input cache
        variables ``_i*``.

        Parameters
        ----------
        line_num : int
            The prompt number of this input.
        source : str
            Python input.
        source_raw : str, optional
            If given, this is the raw input without any IPython transformations
            applied to it.  If not given, ``source`` is used.
        """
        if source_raw is None:
            source_raw = source
        source = source.rstrip("\n")
        source_raw = source_raw.rstrip("\n")

        # do not store exit/quit commands
        if self._exit_re.match(source_raw.strip()):
            return

        self.input_hist_parsed.append(source)
        self.input_hist_raw.append(source_raw)

        with self.db_input_cache_lock:
            self.db_input_cache.append((line_num, source, source_raw))
            # Trigger to flush cache and write to DB.
            if len(self.db_input_cache) >= self.db_cache_size:
                if self.save_flag:
                    self.save_flag.set()

        # update the auto _i variables
        self._iii = self._ii
        self._ii = self._i
        self._i = self._i00
        self._i00 = source_raw

        # hackish access to user namespace to create _i1,_i2... dynamically
        new_i = "_i%s" % line_num
        to_main = {"_i": self._i, "_ii": self._ii, "_iii": self._iii, new_i: self._i00}

        if self.shell is not None:
            self.shell.push(to_main, interactive=False)

    def store_output(self, line_num: int) -> None:
        """If database output logging is enabled, this saves all the
        outputs from the indicated prompt number to the database. It's
        called by run_cell after code has been executed.

        Parameters
        ----------
        line_num : int
            The line number from which to save outputs
        """
        if (not self.db_log_output) or (line_num not in self.output_hist_reprs):
            return
        lnum: int = line_num
        output = self.output_hist_reprs[line_num]

        with self.db_output_cache_lock:
            self.db_output_cache.append((line_num, output))
        if self.db_cache_size <= 1 and self.save_flag is not None:
            self.save_flag.set()

    def _writeout_input_cache(self, conn: sqlite3.Connection) -> None:
        with conn:
            for line in self.db_input_cache:
                conn.execute(
                    "INSERT INTO history VALUES (?, ?, ?, ?)",
                    (self.session_number,) + line,
                )

    def _writeout_output_cache(self, conn: sqlite3.Connection) -> None:
        with conn:
            for line in self.db_output_cache:
                conn.execute(
                    "INSERT INTO output_history VALUES (?, ?, ?)",
                    (self.session_number,) + line,
                )

    @only_when_enabled
    def writeout_cache(self, conn: Optional[sqlite3.Connection] = None) -> None:
        """Write any entries in the cache to the database."""
        if conn is None:
            conn = self.db

        with self.db_input_cache_lock:
            try:
                self._writeout_input_cache(conn)
            except sqlite3.IntegrityError:
                self.new_session(conn)
                print(
                    "ERROR! Session/line number was not unique in",
                    "database. History logging moved to new session",
                    self.session_number,
                )
                try:
                    # Try writing to the new session. If this fails, don't
                    # recurse
                    self._writeout_input_cache(conn)
                except sqlite3.IntegrityError:
                    pass
            finally:
                self.db_input_cache = []

        with self.db_output_cache_lock:
            try:
                self._writeout_output_cache(conn)
            except sqlite3.IntegrityError:
                print(
                    "!! Session/line number for output was not unique",
                    "in database. Output will not be stored.",
                )
            finally:
                self.db_output_cache = []


from typing import Callable, Iterator
from weakref import ReferenceType


@contextmanager
def hold(ref: ReferenceType[HistoryManager]) -> Iterator[ReferenceType[HistoryManager]]:
    """
    Context manger that hold a reference to a weak ref to make sure it
    is not GC'd during it's context.
    """
    r = ref()
    yield ref
    del r


class HistorySavingThread(threading.Thread):
    """This thread takes care of writing history to the database, so that
    the UI isn't held up while that happens.

    It waits for the HistoryManager's save_flag to be set, then writes out
    the history cache. The main thread is responsible for setting the flag when
    the cache size reaches a defined threshold."""

    save_flag: threading.Event
    daemon: bool = True
    _stop_now: bool = False
    enabled: bool = True
    history_manager: ref[HistoryManager]
    _stopped = False

    def __init__(self, history_manager: HistoryManager) -> None:
        super(HistorySavingThread, self).__init__(name="IPythonHistorySavingThread")
        self.history_manager = ref(history_manager)
        self.enabled = history_manager.enabled
        self.save_flag = threading.Event()

    @only_when_enabled
    def run(self) -> None:
        atexit.register(self.stop)
        # We need a separate db connection per thread:
        try:
            hm: ReferenceType[HistoryManager]
            with hold(self.history_manager) as hm:
                if hm() is not None:
                    self.db = sqlite3.connect(
                        str(hm().hist_file),  # type: ignore [union-attr]
                        **hm().connection_options,  # type: ignore [union-attr]
                    )
            while True:
                self.save_flag.wait()
                with hold(self.history_manager) as hm:
                    if hm() is None:
                        self._stop_now = True
                    if self._stop_now:
                        self.db.close()
                        return
                    self.save_flag.clear()
                    if hm() is not None:
                        hm().writeout_cache(self.db)  # type: ignore [union-attr]

        except Exception as e:
            print(
                (
                    "The history saving thread hit an unexpected error (%s)."
                    "History will not be written to the database."
                )
                % repr(e)
            )
        finally:
            atexit.unregister(self.stop)

    def stop(self) -> None:
        """This can be called from the main thread to safely stop this thread.

        Note that it does not attempt to write out remaining history before
        exiting. That should be done by calling the HistoryManager's
        end_session method."""
        if self._stopped:
            return
        self._stop_now = True

        self.save_flag.set()
        self._stopped = True
        if self != threading.current_thread():
            self.join()

    def __del__(self) -> None:
        self.stop()


# To match, e.g. ~5/8-~2/3
range_re = re.compile(
    r"""
((?P<startsess>~?\d+)/)?
(?P<start>\d+)?
((?P<sep>[\-:])
 ((?P<endsess>~?\d+)/)?
 (?P<end>\d+))?
$""",
    re.VERBOSE,
)


def extract_hist_ranges(ranges_str: str) -> Iterable[tuple[int, int, Optional[int]]]:
    """Turn a string of history ranges into 3-tuples of (session, start, stop).

    Empty string results in a `[(0, 1, None)]`, i.e. "everything from current
    session".

    Examples
    --------
    >>> list(extract_hist_ranges("~8/5-~7/4 2"))
    [(-8, 5, None), (-7, 1, 5), (0, 2, 3)]
    """
    if ranges_str == "":
        yield (0, 1, None)  # Everything from current session
        return

    for range_str in ranges_str.split():
        rmatch = range_re.match(range_str)
        if not rmatch:
            continue
        start = rmatch.group("start")
        if start:
            start = int(start)
            end = rmatch.group("end")
            # If no end specified, get (a, a + 1)
            end = int(end) if end else start + 1
        else:  # start not specified
            if not rmatch.group("startsess"):  # no startsess
                continue
            start = 1
            end = None  # provide the entire session hist

        if rmatch.group("sep") == "-":  # 1-3 == 1:4 --> [1, 2, 3]
            assert end is not None
            end += 1
        startsess = rmatch.group("startsess") or "0"
        endsess = rmatch.group("endsess") or startsess
        startsess = int(startsess.replace("~", "-"))
        endsess = int(endsess.replace("~", "-"))
        assert endsess >= startsess, "start session must be earlier than end session"

        if endsess == startsess:
            yield (startsess, start, end)
            continue
        # Multiple sessions in one range:
        yield (startsess, start, None)
        for sess in range(startsess + 1, endsess):
            yield (sess, 1, None)
        yield (endsess, 1, end)


def _format_lineno(session: int, line: int) -> str:
    """Helper function to format line numbers properly."""
    if session == 0:
        return str(line)
    return "%s#%s" % (session, line)

# === NexusCore/openenv\Lib\site-packages\IPython\core\oinspect.py ===
"""Tools for inspecting Python objects.

Uses syntax highlighting for presenting the various information elements.

Similar in spirit to the inspect module, but all calls take a name argument to
reference the name under which an object is being read.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

__all__ = ["Inspector"]

# stdlib modules
from dataclasses import dataclass
from inspect import signature
from textwrap import dedent
import ast
import html
import inspect
import io as stdlib_io
import linecache
import os
import types
import warnings
from pygments.token import Token


from typing import (
    cast,
    Any,
    Optional,
    Dict,
    Union,
    List,
    TypedDict,
    TypeAlias,
    Tuple,
)

import traitlets
from traitlets.config import Configurable

# IPython's own
from IPython.core import page
from IPython.lib.pretty import pretty
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils import PyColorize, openpy
from IPython.utils.dir2 import safe_hasattr
from IPython.utils.path import compress_user
from IPython.utils.text import indent
from IPython.utils.wildcard import list_namespace, typestr2type
from IPython.utils.decorators import undoc

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

HOOK_NAME = "__custom_documentations__"


UnformattedBundle: TypeAlias = Dict[str, List[Tuple[str, str]]]  # List of (title, body)
Bundle: TypeAlias = Dict[str, str]


@dataclass
class OInfo:
    ismagic: bool
    isalias: bool
    found: bool
    namespace: Optional[str]
    parent: Any
    obj: Any

    def get(self, field):
        """Get a field from the object for backward compatibility with before 8.12

        see https://github.com/h5py/h5py/issues/2253
        """
        # We need to deprecate this at some point, but the warning will show in completion.
        # Let's comment this for now and uncomment end of 2023 ish
        # Jan 2025: decomenting for IPython 9.0
        warnings.warn(
            f"OInfo dataclass with fields access since IPython 8.12 please use OInfo.{field} instead."
            "OInfo used to be a dict but a dataclass provide static fields verification with mypy."
            "This warning and backward compatibility `get()` method were added in 8.13.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(self, field)


def pylight(code):
    return highlight(code, PythonLexer(), HtmlFormatter(noclasses=True))

# builtin docstrings to ignore
_func_call_docstring = types.FunctionType.__call__.__doc__
_object_init_docstring = object.__init__.__doc__
_builtin_type_docstrings = {
    inspect.getdoc(t) for t in (types.ModuleType, types.MethodType,
                                types.FunctionType, property)
}

_builtin_func_type = type(all)
_builtin_meth_type = type(str.upper)  # Bound methods have the same type as builtin functions
#****************************************************************************
# Builtin color schemes


#****************************************************************************
# Auxiliary functions and objects


class InfoDict(TypedDict):
    type_name: Optional[str]
    base_class: Optional[str]
    string_form: Optional[str]
    namespace: Optional[str]
    length: Optional[str]
    file: Optional[str]
    definition: Optional[str]
    docstring: Optional[str]
    source: Optional[str]
    init_definition: Optional[str]
    class_docstring: Optional[str]
    init_docstring: Optional[str]
    call_def: Optional[str]
    call_docstring: Optional[str]
    subclasses: Optional[str]
    # These won't be printed but will be used to determine how to
    # format the object
    ismagic: bool
    isalias: bool
    isclass: bool
    found: bool
    name: str


_info_fields = list(InfoDict.__annotations__.keys())


def __getattr__(name):
    if name == "info_fields":
        warnings.warn(
            "IPython.core.oinspect's `info_fields` is considered for deprecation and may be removed in the Future. ",
            DeprecationWarning,
            stacklevel=2,
        )
        return _info_fields

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


@dataclass
class InspectorHookData:
    """Data passed to the mime hook"""

    obj: Any
    info: Optional[OInfo]
    info_dict: InfoDict
    detail_level: int
    omit_sections: list[str]


@undoc
def object_info(
    *,
    name: str,
    found: bool,
    isclass: bool = False,
    isalias: bool = False,
    ismagic: bool = False,
    **kw,
) -> InfoDict:
    """Make an object info dict with all fields present."""
    infodict = dict(kw)
    infodict.update({k: None for k in _info_fields if k not in infodict})
    infodict["name"] = name  # type: ignore
    infodict["found"] = found  # type: ignore
    infodict["isclass"] = isclass  # type: ignore
    infodict["isalias"] = isalias  # type: ignore
    infodict["ismagic"] = ismagic  # type: ignore

    return InfoDict(**infodict)  # type:ignore


def get_encoding(obj):
    """Get encoding for python source file defining obj

    Returns None if obj is not defined in a sourcefile.
    """
    ofile = find_file(obj)
    # run contents of file through pager starting at line where the object
    # is defined, as long as the file isn't binary and is actually on the
    # filesystem.
    if ofile is None:
        return None
    elif ofile.endswith(('.so', '.dll', '.pyd')):
        return None
    elif not os.path.isfile(ofile):
        return None
    else:
        # Print only text files, not extension binaries.  Note that
        # getsourcelines returns lineno with 1-offset and page() uses
        # 0-offset, so we must adjust.
        with stdlib_io.open(ofile, 'rb') as buffer:   # Tweaked to use io.open for Python 2
            encoding, _lines = openpy.detect_encoding(buffer.readline)
        return encoding


def getdoc(obj) -> Union[str, None]:
    """Stable wrapper around inspect.getdoc.

    This can't crash because of attribute problems.

    It also attempts to call a getdoc() method on the given object.  This
    allows objects which provide their docstrings via non-standard mechanisms
    (like Pyro proxies) to still be inspected by ipython's ? system.
    """
    # Allow objects to offer customized documentation via a getdoc method:
    try:
        ds = obj.getdoc()
    except Exception:
        pass
    else:
        if isinstance(ds, str):
            return inspect.cleandoc(ds)
    docstr = inspect.getdoc(obj)
    return docstr


def getsource(obj, oname='') -> Union[str,None]:
    """Wrapper around inspect.getsource.

    This can be modified by other projects to provide customized source
    extraction.

    Parameters
    ----------
    obj : object
        an object whose source code we will attempt to extract
    oname : str
        (optional) a name under which the object is known

    Returns
    -------
    src : unicode or None

    """

    if isinstance(obj, property):
        sources = []
        for attrname in ['fget', 'fset', 'fdel']:
            fn = getattr(obj, attrname)
            if fn is not None:
                oname_prefix = ('%s.' % oname) if oname else ''
                sources.append(''.join(('# ', oname_prefix, attrname)))
                if inspect.isfunction(fn):
                    _src = getsource(fn)
                    if _src:
                        # assert _src is not None, "please mypy"
                        sources.append(dedent(_src))
                else:
                    # Default str/repr only prints function name,
                    # pretty.pretty prints module name too.
                    sources.append(
                        '%s%s = %s\n' % (oname_prefix, attrname, pretty(fn))
                    )
        if sources:
            return '\n'.join(sources)
        else:
            return None

    else:
        # Get source for non-property objects.

        obj = _get_wrapped(obj)

        try:
            src = inspect.getsource(obj)
        except TypeError:
            # The object itself provided no meaningful source, try looking for
            # its class definition instead.
            try:
                src = inspect.getsource(obj.__class__)
            except (OSError, TypeError):
                return None
        except OSError:
            return None

        return src


def is_simple_callable(obj):
    """True if obj is a function ()"""
    return (inspect.isfunction(obj) or inspect.ismethod(obj) or \
            isinstance(obj, _builtin_func_type) or isinstance(obj, _builtin_meth_type))

def _get_wrapped(obj):
    """Get the original object if wrapped in one or more @decorators

    Some objects automatically construct similar objects on any unrecognised
    attribute access (e.g. unittest.mock.call). To protect against infinite loops,
    this will arbitrarily cut off after 100 levels of obj.__wrapped__
    attribute access. --TK, Jan 2016
    """
    orig_obj = obj
    i = 0
    while safe_hasattr(obj, '__wrapped__'):
        obj = obj.__wrapped__
        i += 1
        if i > 100:
            # __wrapped__ is probably a lie, so return the thing we started with
            return orig_obj
    return obj

def find_file(obj) -> Optional[str]:
    """Find the absolute path to the file where an object was defined.

    This is essentially a robust wrapper around `inspect.getabsfile`.

    Returns None if no file can be found.

    Parameters
    ----------
    obj : any Python object

    Returns
    -------
    fname : str
        The absolute path to the file where the object was defined.
    """
    obj = _get_wrapped(obj)

    fname: Optional[str] = None
    try:
        fname = inspect.getabsfile(obj)
    except TypeError:
        # For an instance, the file that matters is where its class was
        # declared.
        try:
            fname = inspect.getabsfile(obj.__class__)
        except (OSError, TypeError):
            # Can happen for builtins
            pass
    except OSError:
        pass

    return fname


def find_source_lines(obj):
    """Find the line number in a file where an object was defined.

    This is essentially a robust wrapper around `inspect.getsourcelines`.

    Returns None if no file can be found.

    Parameters
    ----------
    obj : any Python object

    Returns
    -------
    lineno : int
        The line number where the object definition starts.
    """
    obj = _get_wrapped(obj)

    try:
        lineno = inspect.getsourcelines(obj)[1]
    except TypeError:
        # For instances, try the class object like getsource() does
        try:
            lineno = inspect.getsourcelines(obj.__class__)[1]
        except (OSError, TypeError):
            return None
    except OSError:
        return None

    return lineno


_sentinel = object()


class Inspector(Configurable):

    mime_hooks = traitlets.Dict(
        config=True,
        help="dictionary of mime to callable to add information into help mimebundle dict",
    ).tag(config=True)

    _theme_name: str

    def __init__(
        self,
        *,
        theme_name: str,
        str_detail_level=0,
        parent=None,
        config=None,
    ):
        if theme_name in ["Linux", "LightBG", "Neutral", "NoColor"]:
            warnings.warn(
                f"Theme names and color schemes are lowercase in IPython 9.0 use {theme_name.lower()} instead",
                DeprecationWarning,
                stacklevel=2,
            )
            theme_name = theme_name.lower()
        self._theme_name = theme_name
        super(Inspector, self).__init__(parent=parent, config=config)
        self.parser = PyColorize.Parser(out="str", theme_name=theme_name)
        self.str_detail_level = str_detail_level
        self.set_theme_name(theme_name)

    def format(self, *args, **kwargs):
        return self.parser.format(*args, **kwargs)

    def _getdef(self,obj,oname='') -> Union[str,None]:
        """Return the call signature for any callable object.

        If any exception is generated, None is returned instead and the
        exception is suppressed."""
        if not callable(obj):
            return None
        try:
            return _render_signature(signature(obj), oname)
        except:
            return None

    def __head(self, h: str) -> str:
        """Return a header string with proper colors."""
        return PyColorize.theme_table[self._theme_name].format([(Token.Header, h)])

    def set_theme_name(self, name: str):
        assert name == name.lower()
        assert name in PyColorize.theme_table.keys()
        self._theme_name = name
        self.parser.theme_name = name

    def set_active_scheme(self, scheme: str):
        warnings.warn(
            "set_active_scheme is deprecated and replaced by set_theme_name as of IPython 9.0",
            DeprecationWarning,
            stacklevel=2,
        )
        assert scheme == scheme.lower()
        if scheme is not None and self._theme_name != scheme:
            self._theme_name = scheme
            self.parser.theme_name = scheme

    def noinfo(self, msg, oname):
        """Generic message when no information is found."""
        print('No %s found' % msg, end=' ')
        if oname:
            print('for %s' % oname)
        else:
            print()

    def pdef(self, obj, oname=''):
        """Print the call signature for any callable object.

        If the object is a class, print the constructor information."""

        if not callable(obj):
            print('Object is not callable.')
            return

        header = ''

        if inspect.isclass(obj):
            header = self.__head('Class constructor information:\n')


        output = self._getdef(obj,oname)
        if output is None:
            self.noinfo('definition header',oname)
        else:
            print(header,self.format(output), end=' ')

    # In Python 3, all classes are new-style, so they all have __init__.
    @skip_doctest
    def pdoc(self, obj, oname='', formatter=None):
        """Print the docstring for any object.

        Optional:
        -formatter: a function to run the docstring through for specially
        formatted docstrings.

        Examples
        --------
        In [1]: class NoInit:
           ...:     pass

        In [2]: class NoDoc:
           ...:     def __init__(self):
           ...:         pass

        In [3]: %pdoc NoDoc
        No documentation found for NoDoc

        In [4]: %pdoc NoInit
        No documentation found for NoInit

        In [5]: obj = NoInit()

        In [6]: %pdoc obj
        No documentation found for obj

        In [5]: obj2 = NoDoc()

        In [6]: %pdoc obj2
        No documentation found for obj2
        """

        lines = []
        ds = getdoc(obj)
        if formatter:
            ds = formatter(ds).get('plain/text', ds)
        if ds:
            lines.append(self.__head("Class docstring:"))
            lines.append(indent(ds))
        if inspect.isclass(obj) and hasattr(obj, '__init__'):
            init_ds = getdoc(obj.__init__)
            if init_ds is not None:
                lines.append(self.__head("Init docstring:"))
                lines.append(indent(init_ds))
        elif hasattr(obj,'__call__'):
            call_ds = getdoc(obj.__call__)
            if call_ds:
                lines.append(self.__head("Call docstring:"))
                lines.append(indent(call_ds))

        if not lines:
            self.noinfo('documentation',oname)
        else:
            page.page('\n'.join(lines))

    def psource(self, obj, oname=''):
        """Print the source code for an object."""

        # Flush the source cache because inspect can return out-of-date source
        linecache.checkcache()
        try:
            src = getsource(obj, oname=oname)
        except Exception:
            src = None

        if src is None:
            self.noinfo('source', oname)
        else:
            page.page(self.format(src))

    def pfile(self, obj, oname=''):
        """Show the whole file where an object was defined."""

        lineno = find_source_lines(obj)
        if lineno is None:
            self.noinfo('file', oname)
            return

        ofile = find_file(obj)
        # run contents of file through pager starting at line where the object
        # is defined, as long as the file isn't binary and is actually on the
        # filesystem.
        if ofile is None:
            print("Could not find file for object")
        elif ofile.endswith((".so", ".dll", ".pyd")):
            print("File %r is binary, not printing." % ofile)
        elif not os.path.isfile(ofile):
            print('File %r does not exist, not printing.' % ofile)
        else:
            # Print only text files, not extension binaries.  Note that
            # getsourcelines returns lineno with 1-offset and page() uses
            # 0-offset, so we must adjust.
            page.page(self.format(openpy.read_py_file(ofile, skip_encoding_cookie=False)), lineno - 1)


    def _mime_format(self, text:str, formatter=None) -> dict:
        """Return a mime bundle representation of the input text.

        - if `formatter` is None, the returned mime bundle has
           a ``text/plain`` field, with the input text.
           a ``text/html`` field with a ``<pre>`` tag containing the input text.

        - if ``formatter`` is not None, it must be a callable transforming the
          input text into a mime bundle. Default values for ``text/plain`` and
          ``text/html`` representations are the ones described above.

        Note:

        Formatters returning strings are supported but this behavior is deprecated.

        """
        defaults = {
            "text/plain": text,
            "text/html": f"<pre>{html.escape(text)}</pre>",
        }

        if formatter is None:
            return defaults
        else:
            formatted = formatter(text)

            if not isinstance(formatted, dict):
                # Handle the deprecated behavior of a formatter returning
                # a string instead of a mime bundle.
                return {"text/plain": formatted, "text/html": f"<pre>{formatted}</pre>"}

            else:
                return dict(defaults, **formatted)

    def format_mime(self, bundle: UnformattedBundle) -> Bundle:
        """Format a mimebundle being created by _make_info_unformatted into a real mimebundle"""
        # Format text/plain mimetype
        assert isinstance(bundle["text/plain"], list)
        for item in bundle["text/plain"]:
            assert isinstance(item, tuple)

        new_b: Bundle = {}
        lines = []
        _len = max(len(h) for h, _ in bundle["text/plain"])

        for head, body in bundle["text/plain"]:
            body = body.strip("\n")
            delim = "\n" if "\n" in body else " "
            lines.append(
                f"{self.__head(head+':')}{(_len - len(head))*' '}{delim}{body}"
            )

        new_b["text/plain"] = "\n".join(lines)

        if "text/html" in bundle:
            assert isinstance(bundle["text/html"], list)
            for item in bundle["text/html"]:
                assert isinstance(item, tuple)
            # Format the text/html mimetype
            if isinstance(bundle["text/html"], (list, tuple)):
                # bundle['text/html'] is a list of (head, formatted body) pairs
                new_b["text/html"] = "\n".join(
                    f"<h1>{head}</h1>\n{body}" for (head, body) in bundle["text/html"]
                )

        for k in bundle.keys():
            if k in ("text/html", "text/plain"):
                continue
            else:
                new_b[k] = bundle[k]  # type:ignore
        return new_b

    def _append_info_field(
        self,
        bundle: UnformattedBundle,
        title: str,
        key: str,
        info,
        omit_sections: List[str],
        formatter,
    ):
        """Append an info value to the unformatted mimebundle being constructed by _make_info_unformatted"""
        if title in omit_sections or key in omit_sections:
            return
        field = info[key]
        if field is not None:
            formatted_field = self._mime_format(field, formatter)
            bundle["text/plain"].append((title, formatted_field["text/plain"]))
            bundle["text/html"].append((title, formatted_field["text/html"]))

    def _make_info_unformatted(
        self, obj, info, formatter, detail_level, omit_sections
    ) -> UnformattedBundle:
        """Assemble the mimebundle as unformatted lists of information"""
        bundle: UnformattedBundle = {
            "text/plain": [],
            "text/html": [],
        }

        # A convenience function to simplify calls below
        def append_field(
            bundle: UnformattedBundle, title: str, key: str, formatter=None
        ):
            self._append_info_field(
                bundle,
                title=title,
                key=key,
                info=info,
                omit_sections=omit_sections,
                formatter=formatter,
            )

        def code_formatter(text) -> Bundle:
            return {
                'text/plain': self.format(text),
                'text/html': pylight(text)
            }

        if info["isalias"]:
            append_field(bundle, "Repr", "string_form")

        elif info['ismagic']:
            if detail_level > 0:
                append_field(bundle, "Source", "source", code_formatter)
            else:
                append_field(bundle, "Docstring", "docstring", formatter)
            append_field(bundle, "File", "file")

        elif info['isclass'] or is_simple_callable(obj):
            # Functions, methods, classes
            append_field(bundle, "Signature", "definition", code_formatter)
            append_field(bundle, "Init signature", "init_definition", code_formatter)
            append_field(bundle, "Docstring", "docstring", formatter)
            if detail_level > 0 and info["source"]:
                append_field(bundle, "Source", "source", code_formatter)
            else:
                append_field(bundle, "Init docstring", "init_docstring", formatter)

            append_field(bundle, "File", "file")
            append_field(bundle, "Type", "type_name")
            append_field(bundle, "Subclasses", "subclasses")

        else:
            # General Python objects
            append_field(bundle, "Signature", "definition", code_formatter)
            append_field(bundle, "Call signature", "call_def", code_formatter)
            append_field(bundle, "Type", "type_name")
            append_field(bundle, "String form", "string_form")

            # Namespace
            if info["namespace"] != "Interactive":
                append_field(bundle, "Namespace", "namespace")

            append_field(bundle, "Length", "length")
            append_field(bundle, "File", "file")

            # Source or docstring, depending on detail level and whether
            # source found.
            if detail_level > 0 and info["source"]:
                append_field(bundle, "Source", "source", code_formatter)
            else:
                append_field(bundle, "Docstring", "docstring", formatter)

            append_field(bundle, "Class docstring", "class_docstring", formatter)
            append_field(bundle, "Init docstring", "init_docstring", formatter)
            append_field(bundle, "Call docstring", "call_docstring", formatter)
        return bundle


    def _get_info(
        self,
        obj: Any,
        oname: str = "",
        formatter=None,
        info: Optional[OInfo] = None,
        detail_level: int = 0,
        omit_sections: Union[List[str], Tuple[()]] = (),
    ) -> Bundle:
        """Retrieve an info dict and format it.

        Parameters
        ----------
        obj : any
            Object to inspect and return info from
        oname : str (default: ''):
            Name of the variable pointing to `obj`.
        formatter : callable
        info
            already computed information
        detail_level : integer
            Granularity of detail level, if set to 1, give more information.
        omit_sections : list[str]
            Titles or keys to omit from output (can be set, tuple, etc., anything supporting `in`)
        """

        info_dict = self.info(obj, oname=oname, info=info, detail_level=detail_level)
        omit_sections = list(omit_sections)

        bundle = self._make_info_unformatted(
            obj,
            info_dict,
            formatter,
            detail_level=detail_level,
            omit_sections=omit_sections,
        )
        if self.mime_hooks:
            hook_data = InspectorHookData(
                obj=obj,
                info=info,
                info_dict=info_dict,
                detail_level=detail_level,
                omit_sections=omit_sections,
            )
            for key, hook in self.mime_hooks.items():  # type:ignore
                required_parameters = [
                    parameter
                    for parameter in inspect.signature(hook).parameters.values()
                    if parameter.default != inspect.Parameter.default
                ]
                if len(required_parameters) == 1:
                    res = hook(hook_data)
                else:
                    warnings.warn(
                        "MIME hook format changed in IPython 8.22; hooks should now accept"
                        " a single parameter (InspectorHookData); support for hooks requiring"
                        " two-parameters (obj and info) will be removed in a future version",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    res = hook(obj, info)
                if res is not None:
                    bundle[key] = res
        return self.format_mime(bundle)

    def pinfo(
        self,
        obj,
        oname="",
        formatter=None,
        info: Optional[OInfo] = None,
        detail_level=0,
        enable_html_pager=True,
        omit_sections=(),
    ):
        """Show detailed information about an object.

        Optional arguments:

        - oname: name of the variable pointing to the object.

        - formatter: callable (optional)
              A special formatter for docstrings.

              The formatter is a callable that takes a string as an input
              and returns either a formatted string or a mime type bundle
              in the form of a dictionary.

              Although the support of custom formatter returning a string
              instead of a mime type bundle is deprecated.

        - info: a structure with some information fields which may have been
          precomputed already.

        - detail_level: if set to 1, more information is given.

        - omit_sections: set of section keys and titles to omit
        """
        assert info is not None
        info_b: Bundle = self._get_info(
            obj, oname, formatter, info, detail_level, omit_sections=omit_sections
        )
        if not enable_html_pager:
            del info_b["text/html"]
        page.page(info_b)

    def info(self, obj, oname="", info=None, detail_level=0) -> InfoDict:
        """Compute a dict with detailed information about an object.

        Parameters
        ----------
        obj : any
            An object to find information about
        oname : str (default: '')
            Name of the variable pointing to `obj`.
        info : (default: None)
            A struct (dict like with attr access) with some information fields
            which may have been precomputed already.
        detail_level : int (default:0)
            If set to 1, more information is given.

        Returns
        -------
        An object info dict with known fields from `info_fields` (see `InfoDict`).
        """

        if info is None:
            ismagic = False
            isalias = False
            ospace = ''
        else:
            ismagic = info.ismagic
            isalias = info.isalias
            ospace = info.namespace

        # Get docstring, special-casing aliases:
        att_name = oname.split(".")[-1]
        parents_docs = None
        prelude = ""
        if info and info.parent is not None and hasattr(info.parent, HOOK_NAME):
            parents_docs_dict = getattr(info.parent, HOOK_NAME)
            parents_docs = parents_docs_dict.get(att_name, None)
        out: InfoDict = cast(
            InfoDict,
            {
                **{field: None for field in _info_fields},
                **{
                    "name": oname,
                    "found": True,
                    "isalias": isalias,
                    "ismagic": ismagic,
                    "subclasses": None,
                },
            },
        )

        if parents_docs:
            ds = parents_docs
        elif isalias:
            if not callable(obj):
                try:
                    ds = "Alias to the system command:\n  %s" % obj[1]
                except:
                    ds = "Alias: " + str(obj)
            else:
                ds = "Alias to " + str(obj)
                if obj.__doc__:
                    ds += "\nDocstring:\n" + obj.__doc__
        else:
            ds_or_None = getdoc(obj)
            if ds_or_None is None:
                ds = '<no docstring>'
            else:
                ds = ds_or_None

        ds = prelude + ds

        # store output in a dict, we initialize it here and fill it as we go

        string_max = 200 # max size of strings to show (snipped if longer)
        shalf = int((string_max - 5) / 2)

        if ismagic:
            out['type_name'] = 'Magic function'
        elif isalias:
            out['type_name'] = 'System alias'
        else:
            out['type_name'] = type(obj).__name__

        try:
            bclass = obj.__class__
            out['base_class'] = str(bclass)
        except:
            pass

        # String form, but snip if too long in ? form (full in ??)
        if detail_level >= self.str_detail_level:
            try:
                ostr = str(obj)
                if not detail_level and len(ostr) > string_max:
                    ostr = ostr[:shalf] + ' <...> ' + ostr[-shalf:]
                    # TODO: `'string_form'.expandtabs()` seems wrong, but
                    # it was (nearly) like this since the first commit ever.
                    ostr = ("\n" + " " * len("string_form".expandtabs())).join(
                        q.strip() for q in ostr.split("\n")
                    )
                out["string_form"] = ostr
            except:
                pass

        if ospace:
            out['namespace'] = ospace

        # Length (for strings and lists)
        try:
            out['length'] = str(len(obj))
        except Exception:
            pass

        # Filename where object was defined
        binary_file = False
        fname = find_file(obj)
        if fname is None:
            # if anything goes wrong, we don't want to show source, so it's as
            # if the file was binary
            binary_file = True
        else:
            if fname.endswith(('.so', '.dll', '.pyd')):
                binary_file = True
            elif fname.endswith('<string>'):
                fname = 'Dynamically generated function. No source code available.'
            out['file'] = compress_user(fname)

        # Original source code for a callable, class or property.
        if detail_level:
            # Flush the source cache because inspect can return out-of-date
            # source
            linecache.checkcache()
            try:
                if isinstance(obj, property) or not binary_file:
                    src = getsource(obj, oname)
                    if src is not None:
                        src = src.rstrip()
                    out['source'] = src

            except Exception:
                pass

        # Add docstring only if no source is to be shown (avoid repetitions).
        if ds and not self._source_contains_docstring(out.get('source'), ds):
            out['docstring'] = ds

        # Constructor docstring for classes
        if inspect.isclass(obj):
            out['isclass'] = True

            # get the init signature:
            try:
                init_def = self._getdef(obj, oname)
            except AttributeError:
                init_def = None

            # get the __init__ docstring
            try:
                obj_init = obj.__init__
            except AttributeError:
                init_ds = None
            else:
                if init_def is None:
                    # Get signature from init if top-level sig failed.
                    # Can happen for built-in types (list, etc.).
                    try:
                        init_def = self._getdef(obj_init, oname)
                    except AttributeError:
                        pass
                init_ds = getdoc(obj_init)
                # Skip Python's auto-generated docstrings
                if init_ds == _object_init_docstring:
                    init_ds = None

            if init_def:
                out['init_definition'] = init_def

            if init_ds:
                out['init_docstring'] = init_ds

            names = [sub.__name__ for sub in type.__subclasses__(obj)]
            if len(names) < 10:
                all_names = ', '.join(names)
            else:
                all_names = ', '.join(names[:10]+['...'])
            out['subclasses'] = all_names
        # and class docstring for instances:
        else:
            # reconstruct the function definition and print it:
            defln = self._getdef(obj, oname)
            if defln:
                out['definition'] = defln

            # First, check whether the instance docstring is identical to the
            # class one, and print it separately if they don't coincide.  In
            # most cases they will, but it's nice to print all the info for
            # objects which use instance-customized docstrings.
            if ds:
                try:
                    cls = getattr(obj,'__class__')
                except:
                    class_ds = None
                else:
                    class_ds = getdoc(cls)
                # Skip Python's auto-generated docstrings
                if class_ds in _builtin_type_docstrings:
                    class_ds = None
                if class_ds and ds != class_ds:
                    out['class_docstring'] = class_ds

            # Next, try to show constructor docstrings
            try:
                init_ds = getdoc(obj.__init__)
                # Skip Python's auto-generated docstrings
                if init_ds == _object_init_docstring:
                    init_ds = None
            except AttributeError:
                init_ds = None
            if init_ds:
                out['init_docstring'] = init_ds

            # Call form docstring for callable instances
            if safe_hasattr(obj, '__call__') and not is_simple_callable(obj):
                call_def = self._getdef(obj.__call__, oname)
                if call_def and (call_def != out.get('definition')):
                    # it may never be the case that call def and definition differ,
                    # but don't include the same signature twice
                    out['call_def'] = call_def
                call_ds = getdoc(obj.__call__)
                # Skip Python's auto-generated docstrings
                if call_ds == _func_call_docstring:
                    call_ds = None
                if call_ds:
                    out['call_docstring'] = call_ds

        return out

    @staticmethod
    def _source_contains_docstring(src, doc):
        """
        Check whether the source *src* contains the docstring *doc*.

        This is is helper function to skip displaying the docstring if the
        source already contains it, avoiding repetition of information.
        """
        try:
            (def_node,) = ast.parse(dedent(src)).body
            return ast.get_docstring(def_node) == doc  # type: ignore[arg-type]
        except Exception:
            # The source can become invalid or even non-existent (because it
            # is re-fetched from the source file) so the above code fail in
            # arbitrary ways.
            return False

    def psearch(self,pattern,ns_table,ns_search=[],
                ignore_case=False,show_all=False, *, list_types=False):
        """Search namespaces with wildcards for objects.

        Arguments:

        - pattern: string containing shell-like wildcards to use in namespace
          searches and optionally a type specification to narrow the search to
          objects of that type.

        - ns_table: dict of name->namespaces for search.

        Optional arguments:

          - ns_search: list of namespace names to include in search.

          - ignore_case(False): make the search case-insensitive.

          - show_all(False): show all names, including those starting with
            underscores.

          - list_types(False): list all available object types for object matching.
        """
        # print('ps pattern:<%r>' % pattern)  # dbg

        # defaults
        type_pattern = 'all'
        filter = ''

        # list all object types
        if list_types:
            page.page('\n'.join(sorted(typestr2type)))
            return

        cmds = pattern.split()
        len_cmds  =  len(cmds)
        if len_cmds == 1:
            # Only filter pattern given
            filter = cmds[0]
        elif len_cmds == 2:
            # Both filter and type specified
            filter,type_pattern = cmds
        else:
            raise ValueError('invalid argument string for psearch: <%s>' %
                             pattern)

        # filter search namespaces
        for name in ns_search:
            if name not in ns_table:
                raise ValueError('invalid namespace <%s>. Valid names: %s' %
                                 (name,ns_table.keys()))

        # print('type_pattern:',type_pattern)  # dbg
        search_result, namespaces_seen = set(), set()
        for ns_name in ns_search:
            ns = ns_table[ns_name]
            # Normally, locals and globals are the same, so we just check one.
            if id(ns) in namespaces_seen:
                continue
            namespaces_seen.add(id(ns))
            tmp_res = list_namespace(ns, type_pattern, filter,
                                    ignore_case=ignore_case, show_all=show_all)
            search_result.update(tmp_res)

        page.page('\n'.join(sorted(search_result)))


def _render_signature(obj_signature, obj_name) -> str:
    """
    This was mostly taken from inspect.Signature.__str__.
    Look there for the comments.
    The only change is to add linebreaks when this gets too long.
    """
    result = []
    pos_only = False
    kw_only = True
    for param in obj_signature.parameters.values():
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            pos_only = True
        elif pos_only:
            result.append('/')
            pos_only = False

        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            kw_only = False
        elif param.kind == inspect.Parameter.KEYWORD_ONLY and kw_only:
            result.append('*')
            kw_only = False

        result.append(str(param))

    if pos_only:
        result.append('/')

    # add up name, parameters, braces (2), and commas
    if len(obj_name) + sum(len(r) + 2 for r in result) > 75:
        # This doesn’t fit behind “Signature: ” in an inspect window.
        rendered = '{}(\n{})'.format(obj_name, ''.join(
            '    {},\n'.format(r) for r in result)
        )
    else:
        rendered = '{}({})'.format(obj_name, ', '.join(result))

    if obj_signature.return_annotation is not inspect._empty:
        anno = inspect.formatannotation(obj_signature.return_annotation)
        rendered += ' -> {}'.format(anno)

    return rendered