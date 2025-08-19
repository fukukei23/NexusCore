
# === NexusCore/tools\exports\export_20250803_114325\combined_61.py ===

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\otConverters.py ===
from fontTools.misc.fixedTools import (
    fixedToFloat as fi2fl,
    floatToFixed as fl2fi,
    floatToFixedToStr as fl2str,
    strToFixedToFloat as str2fl,
    ensureVersionIsLong as fi2ve,
    versionToFixed as ve2fi,
)
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.misc.roundTools import nearestMultipleShortestRepr, otRound
from fontTools.misc.textTools import bytesjoin, tobytes, tostr, pad, safeEval
from fontTools.misc.lazyTools import LazyList
from fontTools.ttLib import OPTIMIZE_FONT_SPEED, getSearchRange
from .otBase import (
    CountReference,
    FormatSwitchingBaseTable,
    OTTableReader,
    OTTableWriter,
    ValueRecordFactory,
)
from .otTables import (
    lookupTypes,
    VarCompositeGlyph,
    AATStateTable,
    AATState,
    AATAction,
    ContextualMorphAction,
    LigatureMorphAction,
    InsertionMorphAction,
    MorxSubtable,
    ExtendMode as _ExtendMode,
    CompositeMode as _CompositeMode,
    NO_VARIATION_INDEX,
)
from itertools import zip_longest, accumulate
from functools import partial
from types import SimpleNamespace
import re
import struct
from typing import Optional
import logging


log = logging.getLogger(__name__)
istuple = lambda t: isinstance(t, tuple)


def buildConverters(tableSpec, tableNamespace):
    """Given a table spec from otData.py, build a converter object for each
    field of the table. This is called for each table in otData.py, and
    the results are assigned to the corresponding class in otTables.py."""
    converters = []
    convertersByName = {}
    for tp, name, repeat, aux, descr in tableSpec:
        tableName = name
        if name.startswith("ValueFormat"):
            assert tp == "uint16"
            converterClass = ValueFormat
        elif name.endswith("Count") or name in ("StructLength", "MorphType"):
            converterClass = {
                "uint8": ComputedUInt8,
                "uint16": ComputedUShort,
                "uint32": ComputedULong,
            }[tp]
        elif name == "SubTable":
            converterClass = SubTable
        elif name == "ExtSubTable":
            converterClass = ExtSubTable
        elif name == "SubStruct":
            converterClass = SubStruct
        elif name == "FeatureParams":
            converterClass = FeatureParams
        elif name in ("CIDGlyphMapping", "GlyphCIDMapping"):
            converterClass = StructWithLength
        else:
            if not tp in converterMapping and "(" not in tp:
                tableName = tp
                converterClass = Struct
            else:
                converterClass = eval(tp, tableNamespace, converterMapping)

        conv = converterClass(name, repeat, aux, description=descr)

        if conv.tableClass:
            # A "template" such as OffsetTo(AType) knows the table class already
            tableClass = conv.tableClass
        elif tp in ("MortChain", "MortSubtable", "MorxChain"):
            tableClass = tableNamespace.get(tp)
        else:
            tableClass = tableNamespace.get(tableName)

        if not conv.tableClass:
            conv.tableClass = tableClass

        if name in ["SubTable", "ExtSubTable", "SubStruct"]:
            conv.lookupTypes = tableNamespace["lookupTypes"]
            # also create reverse mapping
            for t in conv.lookupTypes.values():
                for cls in t.values():
                    convertersByName[cls.__name__] = Table(name, repeat, aux, cls)
        if name == "FeatureParams":
            conv.featureParamTypes = tableNamespace["featureParamTypes"]
            conv.defaultFeatureParams = tableNamespace["FeatureParams"]
            for cls in conv.featureParamTypes.values():
                convertersByName[cls.__name__] = Table(name, repeat, aux, cls)
        converters.append(conv)
        assert name not in convertersByName, name
        convertersByName[name] = conv
    return converters, convertersByName


class BaseConverter(object):
    """Base class for converter objects. Apart from the constructor, this
    is an abstract class."""

    def __init__(self, name, repeat, aux, tableClass=None, *, description=""):
        self.name = name
        self.repeat = repeat
        self.aux = aux
        if self.aux and not self.repeat:
            self.aux = compile(self.aux, "<string>", "eval")
        self.tableClass = tableClass
        self.isCount = name.endswith("Count") or name in [
            "DesignAxisRecordSize",
            "ValueRecordSize",
        ]
        self.isLookupType = name.endswith("LookupType") or name == "MorphType"
        self.isPropagated = name in [
            "ClassCount",
            "Class2Count",
            "FeatureTag",
            "SettingsCount",
            "VarRegionCount",
            "MappingCount",
            "RegionAxisCount",
            "DesignAxisCount",
            "DesignAxisRecordSize",
            "AxisValueCount",
            "ValueRecordSize",
            "AxisCount",
            "BaseGlyphRecordCount",
            "LayerRecordCount",
            "AxisIndicesList",
        ]
        self.description = description

    def readArray(self, reader, font, tableDict, count):
        """Read an array of values from the reader."""
        lazy = font.lazy and count > 8
        if lazy:
            recordSize = self.getRecordSize(reader)
            if recordSize is NotImplemented:
                lazy = False
        if not lazy:
            l = []
            for i in range(count):
                l.append(self.read(reader, font, tableDict))
            return l
        else:

            def get_read_item():
                reader_copy = reader.copy()
                pos = reader.pos

                def read_item(i):
                    reader_copy.seek(pos + i * recordSize)
                    return self.read(reader_copy, font, {})

                return read_item

            read_item = get_read_item()
            l = LazyList(read_item for i in range(count))
            reader.advance(count * recordSize)

            return l

    def getRecordSize(self, reader):
        if hasattr(self, "staticSize"):
            return self.staticSize
        return NotImplemented

    def read(self, reader, font, tableDict):
        """Read a value from the reader."""
        raise NotImplementedError(self)

    def writeArray(self, writer, font, tableDict, values):
        try:
            for i, value in enumerate(values):
                self.write(writer, font, tableDict, value, i)
        except Exception as e:
            e.args = e.args + (i,)
            raise

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        """Write a value to the writer."""
        raise NotImplementedError(self)

    def xmlRead(self, attrs, content, font):
        """Read a value from XML."""
        raise NotImplementedError(self)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        """Write a value to XML."""
        raise NotImplementedError(self)

    varIndexBasePlusOffsetRE = re.compile(r"VarIndexBase\s*\+\s*(\d+)")

    def getVarIndexOffset(self) -> Optional[int]:
        """If description has `VarIndexBase + {offset}`, return the offset else None."""
        m = self.varIndexBasePlusOffsetRE.search(self.description)
        if not m:
            return None
        return int(m.group(1))


class SimpleValue(BaseConverter):
    @staticmethod
    def toString(value):
        return value

    @staticmethod
    def fromString(value):
        return value

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", self.toString(value))])
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        return self.fromString(attrs["value"])


class OptionalValue(SimpleValue):
    DEFAULT = None

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        if value != self.DEFAULT:
            attrs.append(("value", self.toString(value)))
        xmlWriter.simpletag(name, attrs)
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        if "value" in attrs:
            return self.fromString(attrs["value"])
        return self.DEFAULT


class IntValue(SimpleValue):
    @staticmethod
    def fromString(value):
        return int(value, 0)


class Long(IntValue):
    staticSize = 4

    def read(self, reader, font, tableDict):
        return reader.readLong()

    def readArray(self, reader, font, tableDict, count):
        return reader.readLongArray(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeLong(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeLongArray(values)


class ULong(IntValue):
    staticSize = 4

    def read(self, reader, font, tableDict):
        return reader.readULong()

    def readArray(self, reader, font, tableDict, count):
        return reader.readULongArray(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeULong(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeULongArray(values)


class Flags32(ULong):
    @staticmethod
    def toString(value):
        return "0x%08X" % value


class VarIndex(OptionalValue, ULong):
    DEFAULT = NO_VARIATION_INDEX


class Short(IntValue):
    staticSize = 2

    def read(self, reader, font, tableDict):
        return reader.readShort()

    def readArray(self, reader, font, tableDict, count):
        return reader.readShortArray(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeShort(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeShortArray(values)


class UShort(IntValue):
    staticSize = 2

    def read(self, reader, font, tableDict):
        return reader.readUShort()

    def readArray(self, reader, font, tableDict, count):
        return reader.readUShortArray(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeUShort(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeUShortArray(values)


class Int8(IntValue):
    staticSize = 1

    def read(self, reader, font, tableDict):
        return reader.readInt8()

    def readArray(self, reader, font, tableDict, count):
        return reader.readInt8Array(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeInt8(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeInt8Array(values)


class UInt8(IntValue):
    staticSize = 1

    def read(self, reader, font, tableDict):
        return reader.readUInt8()

    def readArray(self, reader, font, tableDict, count):
        return reader.readUInt8Array(count)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeUInt8(value)

    def writeArray(self, writer, font, tableDict, values):
        writer.writeUInt8Array(values)


class UInt24(IntValue):
    staticSize = 3

    def read(self, reader, font, tableDict):
        return reader.readUInt24()

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeUInt24(value)


class ComputedInt(IntValue):
    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        if value is not None:
            xmlWriter.comment("%s=%s" % (name, value))
            xmlWriter.newline()


class ComputedUInt8(ComputedInt, UInt8):
    pass


class ComputedUShort(ComputedInt, UShort):
    pass


class ComputedULong(ComputedInt, ULong):
    pass


class Tag(SimpleValue):
    staticSize = 4

    def read(self, reader, font, tableDict):
        return reader.readTag()

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeTag(value)


class GlyphID(SimpleValue):
    staticSize = 2
    typecode = "H"

    def readArray(self, reader, font, tableDict, count):
        return font.getGlyphNameMany(
            reader.readArray(self.typecode, self.staticSize, count)
        )

    def read(self, reader, font, tableDict):
        return font.getGlyphName(reader.readValue(self.typecode, self.staticSize))

    def writeArray(self, writer, font, tableDict, values):
        writer.writeArray(self.typecode, font.getGlyphIDMany(values))

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeValue(self.typecode, font.getGlyphID(value))


class GlyphID32(GlyphID):
    staticSize = 4
    typecode = "L"


class NameID(UShort):
    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        if font and value:
            nameTable = font.get("name")
            if nameTable:
                name = nameTable.getDebugName(value)
                xmlWriter.write("  ")
                if name:
                    xmlWriter.comment(name)
                else:
                    xmlWriter.comment("missing from name table")
                    log.warning("name id %d missing from name table" % value)
        xmlWriter.newline()


class STATFlags(UShort):
    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        flags = []
        if value & 0x01:
            flags.append("OlderSiblingFontAttribute")
        if value & 0x02:
            flags.append("ElidableAxisValueName")
        if flags:
            xmlWriter.write("  ")
            xmlWriter.comment(" ".join(flags))
        xmlWriter.newline()


class FloatValue(SimpleValue):
    @staticmethod
    def fromString(value):
        return float(value)


class DeciPoints(FloatValue):
    staticSize = 2

    def read(self, reader, font, tableDict):
        return reader.readUShort() / 10

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.writeUShort(round(value * 10))


class BaseFixedValue(FloatValue):
    staticSize = NotImplemented
    precisionBits = NotImplemented
    readerMethod = NotImplemented
    writerMethod = NotImplemented

    def read(self, reader, font, tableDict):
        return self.fromInt(getattr(reader, self.readerMethod)())

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        getattr(writer, self.writerMethod)(self.toInt(value))

    @classmethod
    def fromInt(cls, value):
        return fi2fl(value, cls.precisionBits)

    @classmethod
    def toInt(cls, value):
        return fl2fi(value, cls.precisionBits)

    @classmethod
    def fromString(cls, value):
        return str2fl(value, cls.precisionBits)

    @classmethod
    def toString(cls, value):
        return fl2str(value, cls.precisionBits)


class Fixed(BaseFixedValue):
    staticSize = 4
    precisionBits = 16
    readerMethod = "readLong"
    writerMethod = "writeLong"


class F2Dot14(BaseFixedValue):
    staticSize = 2
    precisionBits = 14
    readerMethod = "readShort"
    writerMethod = "writeShort"


class Angle(F2Dot14):
    # angles are specified in degrees, and encoded as F2Dot14 fractions of half
    # circle: e.g. 1.0 => 180, -0.5 => -90, -2.0 => -360, etc.
    bias = 0.0
    factor = 1.0 / (1 << 14) * 180  # 0.010986328125

    @classmethod
    def fromInt(cls, value):
        return (super().fromInt(value) + cls.bias) * 180

    @classmethod
    def toInt(cls, value):
        return super().toInt((value / 180) - cls.bias)

    @classmethod
    def fromString(cls, value):
        # quantize to nearest multiples of minimum fixed-precision angle
        return otRound(float(value) / cls.factor) * cls.factor

    @classmethod
    def toString(cls, value):
        return nearestMultipleShortestRepr(value, cls.factor)


class BiasedAngle(Angle):
    # A bias of 1.0 is used in the representation of start and end angles
    # of COLRv1 PaintSweepGradients to allow for encoding +360deg
    bias = 1.0


class Version(SimpleValue):
    staticSize = 4

    def read(self, reader, font, tableDict):
        value = reader.readLong()
        return value

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        value = fi2ve(value)
        writer.writeLong(value)

    @staticmethod
    def fromString(value):
        return ve2fi(value)

    @staticmethod
    def toString(value):
        return "0x%08x" % value

    @staticmethod
    def fromFloat(v):
        return fl2fi(v, 16)


class Char64(SimpleValue):
    """An ASCII string with up to 64 characters.

    Unused character positions are filled with 0x00 bytes.
    Used in Apple AAT fonts in the `gcid` table.
    """

    staticSize = 64

    def read(self, reader, font, tableDict):
        data = reader.readData(self.staticSize)
        zeroPos = data.find(b"\0")
        if zeroPos >= 0:
            data = data[:zeroPos]
        s = tostr(data, encoding="ascii", errors="replace")
        if s != tostr(data, encoding="ascii", errors="ignore"):
            log.warning('replaced non-ASCII characters in "%s"' % s)
        return s

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        data = tobytes(value, encoding="ascii", errors="replace")
        if data != tobytes(value, encoding="ascii", errors="ignore"):
            log.warning('replacing non-ASCII characters in "%s"' % value)
        if len(data) > self.staticSize:
            log.warning(
                'truncating overlong "%s" to %d bytes' % (value, self.staticSize)
            )
        data = (data + b"\0" * self.staticSize)[: self.staticSize]
        writer.writeData(data)


class Struct(BaseConverter):
    def getRecordSize(self, reader):
        return self.tableClass and self.tableClass.getRecordSize(reader)

    def read(self, reader, font, tableDict):
        table = self.tableClass()
        table.decompile(reader, font)
        return table

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        value.compile(writer, font)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        if value is None:
            if attrs:
                # If there are attributes (probably index), then
                # don't drop this even if it's NULL.  It will mess
                # up the array indices of the containing element.
                xmlWriter.simpletag(name, attrs + [("empty", 1)])
                xmlWriter.newline()
            else:
                pass  # NULL table, ignore
        else:
            value.toXML(xmlWriter, font, attrs, name=name)

    def xmlRead(self, attrs, content, font):
        if "empty" in attrs and safeEval(attrs["empty"]):
            return None
        table = self.tableClass()
        Format = attrs.get("Format")
        if Format is not None:
            table.Format = int(Format)

        noPostRead = not hasattr(table, "postRead")
        if noPostRead:
            # TODO Cache table.hasPropagated.
            cleanPropagation = False
            for conv in table.getConverters():
                if conv.isPropagated:
                    cleanPropagation = True
                    if not hasattr(font, "_propagator"):
                        font._propagator = {}
                    propagator = font._propagator
                    assert conv.name not in propagator, (conv.name, propagator)
                    setattr(table, conv.name, None)
                    propagator[conv.name] = CountReference(table.__dict__, conv.name)

        for element in content:
            if isinstance(element, tuple):
                name, attrs, content = element
                table.fromXML(name, attrs, content, font)
            else:
                pass

        table.populateDefaults(propagator=getattr(font, "_propagator", None))

        if noPostRead:
            if cleanPropagation:
                for conv in table.getConverters():
                    if conv.isPropagated:
                        propagator = font._propagator
                        del propagator[conv.name]
                        if not propagator:
                            del font._propagator

        return table

    def __repr__(self):
        return "Struct of " + repr(self.tableClass)


class StructWithLength(Struct):
    def read(self, reader, font, tableDict):
        pos = reader.pos
        table = self.tableClass()
        table.decompile(reader, font)
        reader.seek(pos + table.StructLength)
        return table

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        for convIndex, conv in enumerate(value.getConverters()):
            if conv.name == "StructLength":
                break
        lengthIndex = len(writer.items) + convIndex
        if isinstance(value, FormatSwitchingBaseTable):
            lengthIndex += 1  # implicit Format field
        deadbeef = {1: 0xDE, 2: 0xDEAD, 4: 0xDEADBEEF}[conv.staticSize]

        before = writer.getDataLength()
        value.StructLength = deadbeef
        value.compile(writer, font)
        length = writer.getDataLength() - before
        lengthWriter = writer.getSubWriter()
        conv.write(lengthWriter, font, tableDict, length)
        assert writer.items[lengthIndex] == b"\xde\xad\xbe\xef"[: conv.staticSize]
        writer.items[lengthIndex] = lengthWriter.getAllData()


class Table(Struct):
    staticSize = 2

    def readOffset(self, reader):
        return reader.readUShort()

    def writeNullOffset(self, writer):
        writer.writeUShort(0)

    def read(self, reader, font, tableDict):
        offset = self.readOffset(reader)
        if offset == 0:
            return None
        table = self.tableClass()
        reader = reader.getSubReader(offset)
        if font.lazy:
            table.reader = reader
            table.font = font
        else:
            table.decompile(reader, font)
        return table

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        if value is None:
            self.writeNullOffset(writer)
        else:
            subWriter = writer.getSubWriter()
            subWriter.name = self.name
            if repeatIndex is not None:
                subWriter.repeatIndex = repeatIndex
            writer.writeSubTable(subWriter, offsetSize=self.staticSize)
            value.compile(subWriter, font)


class LTable(Table):
    staticSize = 4

    def readOffset(self, reader):
        return reader.readULong()

    def writeNullOffset(self, writer):
        writer.writeULong(0)


# Table pointed to by a 24-bit, 3-byte long offset
class Table24(Table):
    staticSize = 3

    def readOffset(self, reader):
        return reader.readUInt24()

    def writeNullOffset(self, writer):
        writer.writeUInt24(0)


# TODO Clean / merge the SubTable and SubStruct


class SubStruct(Struct):
    def getConverter(self, tableType, lookupType):
        tableClass = self.lookupTypes[tableType][lookupType]
        return self.__class__(self.name, self.repeat, self.aux, tableClass)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        super(SubStruct, self).xmlWrite(xmlWriter, font, value, None, attrs)


class SubTable(Table):
    def getConverter(self, tableType, lookupType):
        tableClass = self.lookupTypes[tableType][lookupType]
        return self.__class__(self.name, self.repeat, self.aux, tableClass)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        super(SubTable, self).xmlWrite(xmlWriter, font, value, None, attrs)


class ExtSubTable(LTable, SubTable):
    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer.Extension = True  # actually, mere presence of the field flags it as an Ext Subtable writer.
        Table.write(self, writer, font, tableDict, value, repeatIndex)


class FeatureParams(Table):
    def getConverter(self, featureTag):
        tableClass = self.featureParamTypes.get(featureTag, self.defaultFeatureParams)
        return self.__class__(self.name, self.repeat, self.aux, tableClass)


class ValueFormat(IntValue):
    staticSize = 2

    def __init__(self, name, repeat, aux, tableClass=None, *, description=""):
        BaseConverter.__init__(
            self, name, repeat, aux, tableClass, description=description
        )
        self.which = "ValueFormat" + ("2" if name[-1] == "2" else "1")

    def read(self, reader, font, tableDict):
        format = reader.readUShort()
        reader[self.which] = ValueRecordFactory(format)
        return format

    def write(self, writer, font, tableDict, format, repeatIndex=None):
        writer.writeUShort(format)
        writer[self.which] = ValueRecordFactory(format)


class ValueRecord(ValueFormat):
    def getRecordSize(self, reader):
        return 2 * len(reader[self.which])

    def read(self, reader, font, tableDict):
        return reader[self.which].readValueRecord(reader, font)

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        writer[self.which].writeValueRecord(writer, font, value)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        if value is None:
            pass  # NULL table, ignore
        else:
            value.toXML(xmlWriter, font, self.name, attrs)

    def xmlRead(self, attrs, content, font):
        from .otBase import ValueRecord

        value = ValueRecord()
        value.fromXML(None, attrs, content, font)
        return value


class AATLookup(BaseConverter):
    BIN_SEARCH_HEADER_SIZE = 10

    def __init__(self, name, repeat, aux, tableClass, *, description=""):
        BaseConverter.__init__(
            self, name, repeat, aux, tableClass, description=description
        )
        if issubclass(self.tableClass, SimpleValue):
            self.converter = self.tableClass(name="Value", repeat=None, aux=None)
        else:
            self.converter = Table(
                name="Value", repeat=None, aux=None, tableClass=self.tableClass
            )

    def read(self, reader, font, tableDict):
        format = reader.readUShort()
        if format == 0:
            return self.readFormat0(reader, font)
        elif format == 2:
            return self.readFormat2(reader, font)
        elif format == 4:
            return self.readFormat4(reader, font)
        elif format == 6:
            return self.readFormat6(reader, font)
        elif format == 8:
            return self.readFormat8(reader, font)
        else:
            assert False, "unsupported lookup format: %d" % format

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        values = list(
            sorted([(font.getGlyphID(glyph), val) for glyph, val in value.items()])
        )
        # TODO: Also implement format 4.
        formats = list(
            sorted(
                filter(
                    None,
                    [
                        self.buildFormat0(writer, font, values),
                        self.buildFormat2(writer, font, values),
                        self.buildFormat6(writer, font, values),
                        self.buildFormat8(writer, font, values),
                    ],
                )
            )
        )
        # We use the format ID as secondary sort key to make the output
        # deterministic when multiple formats have same encoded size.
        dataSize, lookupFormat, writeMethod = formats[0]
        pos = writer.getDataLength()
        writeMethod()
        actualSize = writer.getDataLength() - pos
        assert (
            actualSize == dataSize
        ), "AATLookup format %d claimed to write %d bytes, but wrote %d" % (
            lookupFormat,
            dataSize,
            actualSize,
        )

    @staticmethod
    def writeBinSearchHeader(writer, numUnits, unitSize):
        writer.writeUShort(unitSize)
        writer.writeUShort(numUnits)
        searchRange, entrySelector, rangeShift = getSearchRange(
            n=numUnits, itemSize=unitSize
        )
        writer.writeUShort(searchRange)
        writer.writeUShort(entrySelector)
        writer.writeUShort(rangeShift)

    def buildFormat0(self, writer, font, values):
        numGlyphs = len(font.getGlyphOrder())
        if len(values) != numGlyphs:
            return None
        valueSize = self.converter.staticSize
        return (
            2 + numGlyphs * valueSize,
            0,
            lambda: self.writeFormat0(writer, font, values),
        )

    def writeFormat0(self, writer, font, values):
        writer.writeUShort(0)
        for glyphID_, value in values:
            self.converter.write(
                writer, font, tableDict=None, value=value, repeatIndex=None
            )

    def buildFormat2(self, writer, font, values):
        segStart, segValue = values[0]
        segEnd = segStart
        segments = []
        for glyphID, curValue in values[1:]:
            if glyphID != segEnd + 1 or curValue != segValue:
                segments.append((segStart, segEnd, segValue))
                segStart = segEnd = glyphID
                segValue = curValue
            else:
                segEnd = glyphID
        segments.append((segStart, segEnd, segValue))
        valueSize = self.converter.staticSize
        numUnits, unitSize = len(segments) + 1, valueSize + 4
        return (
            2 + self.BIN_SEARCH_HEADER_SIZE + numUnits * unitSize,
            2,
            lambda: self.writeFormat2(writer, font, segments),
        )

    def writeFormat2(self, writer, font, segments):
        writer.writeUShort(2)
        valueSize = self.converter.staticSize
        numUnits, unitSize = len(segments), valueSize + 4
        self.writeBinSearchHeader(writer, numUnits, unitSize)
        for firstGlyph, lastGlyph, value in segments:
            writer.writeUShort(lastGlyph)
            writer.writeUShort(firstGlyph)
            self.converter.write(
                writer, font, tableDict=None, value=value, repeatIndex=None
            )
        writer.writeUShort(0xFFFF)
        writer.writeUShort(0xFFFF)
        writer.writeData(b"\x00" * valueSize)

    def buildFormat6(self, writer, font, values):
        valueSize = self.converter.staticSize
        numUnits, unitSize = len(values), valueSize + 2
        return (
            2 + self.BIN_SEARCH_HEADER_SIZE + (numUnits + 1) * unitSize,
            6,
            lambda: self.writeFormat6(writer, font, values),
        )

    def writeFormat6(self, writer, font, values):
        writer.writeUShort(6)
        valueSize = self.converter.staticSize
        numUnits, unitSize = len(values), valueSize + 2
        self.writeBinSearchHeader(writer, numUnits, unitSize)
        for glyphID, value in values:
            writer.writeUShort(glyphID)
            self.converter.write(
                writer, font, tableDict=None, value=value, repeatIndex=None
            )
        writer.writeUShort(0xFFFF)
        writer.writeData(b"\x00" * valueSize)

    def buildFormat8(self, writer, font, values):
        minGlyphID, maxGlyphID = values[0][0], values[-1][0]
        if len(values) != maxGlyphID - minGlyphID + 1:
            return None
        valueSize = self.converter.staticSize
        return (
            6 + len(values) * valueSize,
            8,
            lambda: self.writeFormat8(writer, font, values),
        )

    def writeFormat8(self, writer, font, values):
        firstGlyphID = values[0][0]
        writer.writeUShort(8)
        writer.writeUShort(firstGlyphID)
        writer.writeUShort(len(values))
        for _, value in values:
            self.converter.write(
                writer, font, tableDict=None, value=value, repeatIndex=None
            )

    def readFormat0(self, reader, font):
        numGlyphs = len(font.getGlyphOrder())
        data = self.converter.readArray(reader, font, tableDict=None, count=numGlyphs)
        return {font.getGlyphName(k): value for k, value in enumerate(data)}

    def readFormat2(self, reader, font):
        mapping = {}
        pos = reader.pos - 2  # start of table is at UShort for format
        unitSize, numUnits = reader.readUShort(), reader.readUShort()
        assert unitSize >= 4 + self.converter.staticSize, unitSize
        for i in range(numUnits):
            reader.seek(pos + i * unitSize + 12)
            last = reader.readUShort()
            first = reader.readUShort()
            value = self.converter.read(reader, font, tableDict=None)
            if last != 0xFFFF:
                for k in range(first, last + 1):
                    mapping[font.getGlyphName(k)] = value
        return mapping

    def readFormat4(self, reader, font):
        mapping = {}
        pos = reader.pos - 2  # start of table is at UShort for format
        unitSize = reader.readUShort()
        assert unitSize >= 6, unitSize
        for i in range(reader.readUShort()):
            reader.seek(pos + i * unitSize + 12)
            last = reader.readUShort()
            first = reader.readUShort()
            offset = reader.readUShort()
            if last != 0xFFFF:
                dataReader = reader.getSubReader(0)  # relative to current position
                dataReader.seek(pos + offset)  # relative to start of table
                data = self.converter.readArray(
                    dataReader, font, tableDict=None, count=last - first + 1
                )
                for k, v in enumerate(data):
                    mapping[font.getGlyphName(first + k)] = v
        return mapping

    def readFormat6(self, reader, font):
        mapping = {}
        pos = reader.pos - 2  # start of table is at UShort for format
        unitSize = reader.readUShort()
        assert unitSize >= 2 + self.converter.staticSize, unitSize
        for i in range(reader.readUShort()):
            reader.seek(pos + i * unitSize + 12)
            glyphID = reader.readUShort()
            value = self.converter.read(reader, font, tableDict=None)
            if glyphID != 0xFFFF:
                mapping[font.getGlyphName(glyphID)] = value
        return mapping

    def readFormat8(self, reader, font):
        first = reader.readUShort()
        count = reader.readUShort()
        data = self.converter.readArray(reader, font, tableDict=None, count=count)
        return {font.getGlyphName(first + k): value for (k, value) in enumerate(data)}

    def xmlRead(self, attrs, content, font):
        value = {}
        for element in content:
            if isinstance(element, tuple):
                name, a, eltContent = element
                if name == "Lookup":
                    value[a["glyph"]] = self.converter.xmlRead(a, eltContent, font)
        return value

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.begintag(name, attrs)
        xmlWriter.newline()
        for glyph, value in sorted(value.items()):
            self.converter.xmlWrite(
                xmlWriter, font, value=value, name="Lookup", attrs=[("glyph", glyph)]
            )
        xmlWriter.endtag(name)
        xmlWriter.newline()


# The AAT 'ankr' table has an unusual structure: An offset to an AATLookup
# followed by an offset to a glyph data table. Other than usual, the
# offsets in the AATLookup are not relative to the beginning of
# the beginning of the 'ankr' table, but relative to the glyph data table.
# So, to find the anchor data for a glyph, one needs to add the offset
# to the data table to the offset found in the AATLookup, and then use
# the sum of these two offsets to find the actual data.
class AATLookupWithDataOffset(BaseConverter):
    def read(self, reader, font, tableDict):
        lookupOffset = reader.readULong()
        dataOffset = reader.readULong()
        lookupReader = reader.getSubReader(lookupOffset)
        lookup = AATLookup("DataOffsets", None, None, UShort)
        offsets = lookup.read(lookupReader, font, tableDict)
        result = {}
        for glyph, offset in offsets.items():
            dataReader = reader.getSubReader(offset + dataOffset)
            item = self.tableClass()
            item.decompile(dataReader, font)
            result[glyph] = item
        return result

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        # We do not work with OTTableWriter sub-writers because
        # the offsets in our AATLookup are relative to our data
        # table, for which we need to provide an offset value itself.
        # It might have been possible to somehow make a kludge for
        # performing this indirect offset computation directly inside
        # OTTableWriter. But this would have made the internal logic
        # of OTTableWriter even more complex than it already is,
        # so we decided to roll our own offset computation for the
        # contents of the AATLookup and associated data table.
        offsetByGlyph, offsetByData, dataLen = {}, {}, 0
        compiledData = []
        for glyph in sorted(value, key=font.getGlyphID):
            subWriter = OTTableWriter()
            value[glyph].compile(subWriter, font)
            data = subWriter.getAllData()
            offset = offsetByData.get(data, None)
            if offset == None:
                offset = dataLen
                dataLen = dataLen + len(data)
                offsetByData[data] = offset
                compiledData.append(data)
            offsetByGlyph[glyph] = offset
        # For calculating the offsets to our AATLookup and data table,
        # we can use the regular OTTableWriter infrastructure.
        lookupWriter = writer.getSubWriter()
        lookup = AATLookup("DataOffsets", None, None, UShort)
        lookup.write(lookupWriter, font, tableDict, offsetByGlyph, None)

        dataWriter = writer.getSubWriter()
        writer.writeSubTable(lookupWriter, offsetSize=4)
        writer.writeSubTable(dataWriter, offsetSize=4)
        for d in compiledData:
            dataWriter.writeData(d)

    def xmlRead(self, attrs, content, font):
        lookup = AATLookup("DataOffsets", None, None, self.tableClass)
        return lookup.xmlRead(attrs, content, font)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        lookup = AATLookup("DataOffsets", None, None, self.tableClass)
        lookup.xmlWrite(xmlWriter, font, value, name, attrs)


class MorxSubtableConverter(BaseConverter):
    _PROCESSING_ORDERS = {
        # bits 30 and 28 of morx.CoverageFlags; see morx spec
        (False, False): "LayoutOrder",
        (True, False): "ReversedLayoutOrder",
        (False, True): "LogicalOrder",
        (True, True): "ReversedLogicalOrder",
    }

    _PROCESSING_ORDERS_REVERSED = {val: key for key, val in _PROCESSING_ORDERS.items()}

    def __init__(self, name, repeat, aux, tableClass=None, *, description=""):
        BaseConverter.__init__(
            self, name, repeat, aux, tableClass, description=description
        )

    def _setTextDirectionFromCoverageFlags(self, flags, subtable):
        if (flags & 0x20) != 0:
            subtable.TextDirection = "Any"
        elif (flags & 0x80) != 0:
            subtable.TextDirection = "Vertical"
        else:
            subtable.TextDirection = "Horizontal"

    def read(self, reader, font, tableDict):
        pos = reader.pos
        m = MorxSubtable()
        m.StructLength = reader.readULong()
        flags = reader.readUInt8()
        orderKey = ((flags & 0x40) != 0, (flags & 0x10) != 0)
        m.ProcessingOrder = self._PROCESSING_ORDERS[orderKey]
        self._setTextDirectionFromCoverageFlags(flags, m)
        m.Reserved = reader.readUShort()
        m.Reserved |= (flags & 0xF) << 16
        m.MorphType = reader.readUInt8()
        m.SubFeatureFlags = reader.readULong()
        tableClass = lookupTypes["morx"].get(m.MorphType)
        if tableClass is None:
            assert False, "unsupported 'morx' lookup type %s" % m.MorphType
        # To decode AAT ligatures, we need to know the subtable size.
        # The easiest way to pass this along is to create a new reader
        # that works on just the subtable as its data.
        headerLength = reader.pos - pos
        data = reader.data[reader.pos : reader.pos + m.StructLength - headerLength]
        assert len(data) == m.StructLength - headerLength
        subReader = OTTableReader(data=data, tableTag=reader.tableTag)
        m.SubStruct = tableClass()
        m.SubStruct.decompile(subReader, font)
        reader.seek(pos + m.StructLength)
        return m

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.begintag(name, attrs)
        xmlWriter.newline()
        xmlWriter.comment("StructLength=%d" % value.StructLength)
        xmlWriter.newline()
        xmlWriter.simpletag("TextDirection", value=value.TextDirection)
        xmlWriter.newline()
        xmlWriter.simpletag("ProcessingOrder", value=value.ProcessingOrder)
        xmlWriter.newline()
        if value.Reserved != 0:
            xmlWriter.simpletag("Reserved", value="0x%04x" % value.Reserved)
            xmlWriter.newline()
        xmlWriter.comment("MorphType=%d" % value.MorphType)
        xmlWriter.newline()
        xmlWriter.simpletag("SubFeatureFlags", value="0x%08x" % value.SubFeatureFlags)
        xmlWriter.newline()
        value.SubStruct.toXML(xmlWriter, font)
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        m = MorxSubtable()
        covFlags = 0
        m.Reserved = 0
        for eltName, eltAttrs, eltContent in filter(istuple, content):
            if eltName == "CoverageFlags":
                # Only in XML from old versions of fonttools.
                covFlags = safeEval(eltAttrs["value"])
                orderKey = ((covFlags & 0x40) != 0, (covFlags & 0x10) != 0)
                m.ProcessingOrder = self._PROCESSING_ORDERS[orderKey]
                self._setTextDirectionFromCoverageFlags(covFlags, m)
            elif eltName == "ProcessingOrder":
                m.ProcessingOrder = eltAttrs["value"]
                assert m.ProcessingOrder in self._PROCESSING_ORDERS_REVERSED, (
                    "unknown ProcessingOrder: %s" % m.ProcessingOrder
                )
            elif eltName == "TextDirection":
                m.TextDirection = eltAttrs["value"]
                assert m.TextDirection in {"Horizontal", "Vertical", "Any"}, (
                    "unknown TextDirection %s" % m.TextDirection
                )
            elif eltName == "Reserved":
                m.Reserved = safeEval(eltAttrs["value"])
            elif eltName == "SubFeatureFlags":
                m.SubFeatureFlags = safeEval(eltAttrs["value"])
            elif eltName.endswith("Morph"):
                m.fromXML(eltName, eltAttrs, eltContent, font)
            else:
                assert False, eltName
        m.Reserved = (covFlags & 0xF) << 16 | m.Reserved
        return m

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        covFlags = (value.Reserved & 0x000F0000) >> 16
        reverseOrder, logicalOrder = self._PROCESSING_ORDERS_REVERSED[
            value.ProcessingOrder
        ]
        covFlags |= 0x80 if value.TextDirection == "Vertical" else 0
        covFlags |= 0x40 if reverseOrder else 0
        covFlags |= 0x20 if value.TextDirection == "Any" else 0
        covFlags |= 0x10 if logicalOrder else 0
        value.CoverageFlags = covFlags
        lengthIndex = len(writer.items)
        before = writer.getDataLength()
        value.StructLength = 0xDEADBEEF
        # The high nibble of value.Reserved is actuallly encoded
        # into coverageFlags, so we need to clear it here.
        origReserved = value.Reserved  # including high nibble
        value.Reserved = value.Reserved & 0xFFFF  # without high nibble
        value.compile(writer, font)
        value.Reserved = origReserved  # restore original value
        assert writer.items[lengthIndex] == b"\xde\xad\xbe\xef"
        length = writer.getDataLength() - before
        writer.items[lengthIndex] = struct.pack(">L", length)


# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6Tables.html#ExtendedStateHeader
# TODO: Untangle the implementation of the various lookup-specific formats.
class STXHeader(BaseConverter):
    def __init__(self, name, repeat, aux, tableClass, *, description=""):
        BaseConverter.__init__(
            self, name, repeat, aux, tableClass, description=description
        )
        assert issubclass(self.tableClass, AATAction)
        self.classLookup = AATLookup("GlyphClasses", None, None, UShort)
        if issubclass(self.tableClass, ContextualMorphAction):
            self.perGlyphLookup = AATLookup("PerGlyphLookup", None, None, GlyphID)
        else:
            self.perGlyphLookup = None

    def read(self, reader, font, tableDict):
        table = AATStateTable()
        pos = reader.pos
        classTableReader = reader.getSubReader(0)
        stateArrayReader = reader.getSubReader(0)
        entryTableReader = reader.getSubReader(0)
        actionReader = None
        ligaturesReader = None
        table.GlyphClassCount = reader.readULong()
        classTableReader.seek(pos + reader.readULong())
        stateArrayReader.seek(pos + reader.readULong())
        entryTableReader.seek(pos + reader.readULong())
        if self.perGlyphLookup is not None:
            perGlyphTableReader = reader.getSubReader(0)
            perGlyphTableReader.seek(pos + reader.readULong())
        if issubclass(self.tableClass, LigatureMorphAction):
            actionReader = reader.getSubReader(0)
            actionReader.seek(pos + reader.readULong())
            ligComponentReader = reader.getSubReader(0)
            ligComponentReader.seek(pos + reader.readULong())
            ligaturesReader = reader.getSubReader(0)
            ligaturesReader.seek(pos + reader.readULong())
            numLigComponents = (ligaturesReader.pos - ligComponentReader.pos) // 2
            assert numLigComponents >= 0
            table.LigComponents = ligComponentReader.readUShortArray(numLigComponents)
            table.Ligatures = self._readLigatures(ligaturesReader, font)
        elif issubclass(self.tableClass, InsertionMorphAction):
            actionReader = reader.getSubReader(0)
            actionReader.seek(pos + reader.readULong())
        table.GlyphClasses = self.classLookup.read(classTableReader, font, tableDict)
        numStates = int(
            (entryTableReader.pos - stateArrayReader.pos) / (table.GlyphClassCount * 2)
        )
        for stateIndex in range(numStates):
            state = AATState()
            table.States.append(state)
            for glyphClass in range(table.GlyphClassCount):
                entryIndex = stateArrayReader.readUShort()
                state.Transitions[glyphClass] = self._readTransition(
                    entryTableReader, entryIndex, font, actionReader
                )
        if self.perGlyphLookup is not None:
            table.PerGlyphLookups = self._readPerGlyphLookups(
                table, perGlyphTableReader, font
            )
        return table

    def _readTransition(self, reader, entryIndex, font, actionReader):
        transition = self.tableClass()
        entryReader = reader.getSubReader(
            reader.pos + entryIndex * transition.staticSize
        )
        transition.decompile(entryReader, font, actionReader)
        return transition

    def _readLigatures(self, reader, font):
        limit = len(reader.data)
        numLigatureGlyphs = (limit - reader.pos) // 2
        return font.getGlyphNameMany(reader.readUShortArray(numLigatureGlyphs))

    def _countPerGlyphLookups(self, table):
        # Somewhat annoyingly, the morx table does not encode
        # the size of the per-glyph table. So we need to find
        # the maximum value that MorphActions use as index
        # into this table.
        numLookups = 0
        for state in table.States:
            for t in state.Transitions.values():
                if isinstance(t, ContextualMorphAction):
                    if t.MarkIndex != 0xFFFF:
                        numLookups = max(numLookups, t.MarkIndex + 1)
                    if t.CurrentIndex != 0xFFFF:
                        numLookups = max(numLookups, t.CurrentIndex + 1)
        return numLookups

    def _readPerGlyphLookups(self, table, reader, font):
        pos = reader.pos
        lookups = []
        for _ in range(self._countPerGlyphLookups(table)):
            lookupReader = reader.getSubReader(0)
            lookupReader.seek(pos + reader.readULong())
            lookups.append(self.perGlyphLookup.read(lookupReader, font, {}))
        return lookups

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        glyphClassWriter = OTTableWriter()
        self.classLookup.write(
            glyphClassWriter, font, tableDict, value.GlyphClasses, repeatIndex=None
        )
        glyphClassData = pad(glyphClassWriter.getAllData(), 2)
        glyphClassCount = max(value.GlyphClasses.values()) + 1
        glyphClassTableOffset = 16  # size of STXHeader
        if self.perGlyphLookup is not None:
            glyphClassTableOffset += 4

        glyphClassTableOffset += self.tableClass.actionHeaderSize
        actionData, actionIndex = self.tableClass.compileActions(font, value.States)
        stateArrayData, entryTableData = self._compileStates(
            font, value.States, glyphClassCount, actionIndex
        )
        stateArrayOffset = glyphClassTableOffset + len(glyphClassData)
        entryTableOffset = stateArrayOffset + len(stateArrayData)
        perGlyphOffset = entryTableOffset + len(entryTableData)
        perGlyphData = pad(self._compilePerGlyphLookups(value, font), 4)
        if actionData is not None:
            actionOffset = entryTableOffset + len(entryTableData)
        else:
            actionOffset = None

        ligaturesOffset, ligComponentsOffset = None, None
        ligComponentsData = self._compileLigComponents(value, font)
        ligaturesData = self._compileLigatures(value, font)
        if ligComponentsData is not None:
            assert len(perGlyphData) == 0
            ligComponentsOffset = actionOffset + len(actionData)
            ligaturesOffset = ligComponentsOffset + len(ligComponentsData)

        writer.writeULong(glyphClassCount)
        writer.writeULong(glyphClassTableOffset)
        writer.writeULong(stateArrayOffset)
        writer.writeULong(entryTableOffset)
        if self.perGlyphLookup is not None:
            writer.writeULong(perGlyphOffset)
        if actionOffset is not None:
            writer.writeULong(actionOffset)
        if ligComponentsOffset is not None:
            writer.writeULong(ligComponentsOffset)
            writer.writeULong(ligaturesOffset)
        writer.writeData(glyphClassData)
        writer.writeData(stateArrayData)
        writer.writeData(entryTableData)
        writer.writeData(perGlyphData)
        if actionData is not None:
            writer.writeData(actionData)
        if ligComponentsData is not None:
            writer.writeData(ligComponentsData)
        if ligaturesData is not None:
            writer.writeData(ligaturesData)

    def _compileStates(self, font, states, glyphClassCount, actionIndex):
        stateArrayWriter = OTTableWriter()
        entries, entryIDs = [], {}
        for state in states:
            for glyphClass in range(glyphClassCount):
                transition = state.Transitions[glyphClass]
                entryWriter = OTTableWriter()
                transition.compile(entryWriter, font, actionIndex)
                entryData = entryWriter.getAllData()
                assert (
                    len(entryData) == transition.staticSize
                ), "%s has staticSize %d, " "but actually wrote %d bytes" % (
                    repr(transition),
                    transition.staticSize,
                    len(entryData),
                )
                entryIndex = entryIDs.get(entryData)
                if entryIndex is None:
                    entryIndex = len(entries)
                    entryIDs[entryData] = entryIndex
                    entries.append(entryData)
                stateArrayWriter.writeUShort(entryIndex)
        stateArrayData = pad(stateArrayWriter.getAllData(), 4)
        entryTableData = pad(bytesjoin(entries), 4)
        return stateArrayData, entryTableData

    def _compilePerGlyphLookups(self, table, font):
        if self.perGlyphLookup is None:
            return b""
        numLookups = self._countPerGlyphLookups(table)
        assert len(table.PerGlyphLookups) == numLookups, (
            "len(AATStateTable.PerGlyphLookups) is %d, "
            "but the actions inside the table refer to %d"
            % (len(table.PerGlyphLookups), numLookups)
        )
        writer = OTTableWriter()
        for lookup in table.PerGlyphLookups:
            lookupWriter = writer.getSubWriter()
            self.perGlyphLookup.write(lookupWriter, font, {}, lookup, None)
            writer.writeSubTable(lookupWriter, offsetSize=4)
        return writer.getAllData()

    def _compileLigComponents(self, table, font):
        if not hasattr(table, "LigComponents"):
            return None
        writer = OTTableWriter()
        for component in table.LigComponents:
            writer.writeUShort(component)
        return writer.getAllData()

    def _compileLigatures(self, table, font):
        if not hasattr(table, "Ligatures"):
            return None
        writer = OTTableWriter()
        for glyphName in table.Ligatures:
            writer.writeUShort(font.getGlyphID(glyphName))
        return writer.getAllData()

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.begintag(name, attrs)
        xmlWriter.newline()
        xmlWriter.comment("GlyphClassCount=%s" % value.GlyphClassCount)
        xmlWriter.newline()
        for g, klass in sorted(value.GlyphClasses.items()):
            xmlWriter.simpletag("GlyphClass", glyph=g, value=klass)
            xmlWriter.newline()
        for stateIndex, state in enumerate(value.States):
            xmlWriter.begintag("State", index=stateIndex)
            xmlWriter.newline()
            for glyphClass, trans in sorted(state.Transitions.items()):
                trans.toXML(
                    xmlWriter,
                    font=font,
                    attrs={"onGlyphClass": glyphClass},
                    name="Transition",
                )
            xmlWriter.endtag("State")
            xmlWriter.newline()
        for i, lookup in enumerate(value.PerGlyphLookups):
            xmlWriter.begintag("PerGlyphLookup", index=i)
            xmlWriter.newline()
            for glyph, val in sorted(lookup.items()):
                xmlWriter.simpletag("Lookup", glyph=glyph, value=val)
                xmlWriter.newline()
            xmlWriter.endtag("PerGlyphLookup")
            xmlWriter.newline()
        if hasattr(value, "LigComponents"):
            xmlWriter.begintag("LigComponents")
            xmlWriter.newline()
            for i, val in enumerate(getattr(value, "LigComponents")):
                xmlWriter.simpletag("LigComponent", index=i, value=val)
                xmlWriter.newline()
            xmlWriter.endtag("LigComponents")
            xmlWriter.newline()
        self._xmlWriteLigatures(xmlWriter, font, value, name, attrs)
        xmlWriter.endtag(name)
        xmlWriter.newline()

    def _xmlWriteLigatures(self, xmlWriter, font, value, name, attrs):
        if not hasattr(value, "Ligatures"):
            return
        xmlWriter.begintag("Ligatures")
        xmlWriter.newline()
        for i, g in enumerate(getattr(value, "Ligatures")):
            xmlWriter.simpletag("Ligature", index=i, glyph=g)
            xmlWriter.newline()
        xmlWriter.endtag("Ligatures")
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        table = AATStateTable()
        for eltName, eltAttrs, eltContent in filter(istuple, content):
            if eltName == "GlyphClass":
                glyph = eltAttrs["glyph"]
                value = eltAttrs["value"]
                table.GlyphClasses[glyph] = safeEval(value)
            elif eltName == "State":
                state = self._xmlReadState(eltAttrs, eltContent, font)
                table.States.append(state)
            elif eltName == "PerGlyphLookup":
                lookup = self.perGlyphLookup.xmlRead(eltAttrs, eltContent, font)
                table.PerGlyphLookups.append(lookup)
            elif eltName == "LigComponents":
                table.LigComponents = self._xmlReadLigComponents(
                    eltAttrs, eltContent, font
                )
            elif eltName == "Ligatures":
                table.Ligatures = self._xmlReadLigatures(eltAttrs, eltContent, font)
        table.GlyphClassCount = max(table.GlyphClasses.values()) + 1
        return table

    def _xmlReadState(self, attrs, content, font):
        state = AATState()
        for eltName, eltAttrs, eltContent in filter(istuple, content):
            if eltName == "Transition":
                glyphClass = safeEval(eltAttrs["onGlyphClass"])
                transition = self.tableClass()
                transition.fromXML(eltName, eltAttrs, eltContent, font)
                state.Transitions[glyphClass] = transition
        return state

    def _xmlReadLigComponents(self, attrs, content, font):
        ligComponents = []
        for eltName, eltAttrs, _eltContent in filter(istuple, content):
            if eltName == "LigComponent":
                ligComponents.append(safeEval(eltAttrs["value"]))
        return ligComponents

    def _xmlReadLigatures(self, attrs, content, font):
        ligs = []
        for eltName, eltAttrs, _eltContent in filter(istuple, content):
            if eltName == "Ligature":
                ligs.append(eltAttrs["glyph"])
        return ligs


class CIDGlyphMap(BaseConverter):
    def read(self, reader, font, tableDict):
        numCIDs = reader.readUShort()
        result = {}
        for cid, glyphID in enumerate(reader.readUShortArray(numCIDs)):
            if glyphID != 0xFFFF:
                result[cid] = font.getGlyphName(glyphID)
        return result

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        items = {cid: font.getGlyphID(glyph) for cid, glyph in value.items()}
        count = max(items) + 1 if items else 0
        writer.writeUShort(count)
        for cid in range(count):
            writer.writeUShort(items.get(cid, 0xFFFF))

    def xmlRead(self, attrs, content, font):
        result = {}
        for eName, eAttrs, _eContent in filter(istuple, content):
            if eName == "CID":
                result[safeEval(eAttrs["cid"])] = eAttrs["glyph"].strip()
        return result

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.begintag(name, attrs)
        xmlWriter.newline()
        for cid, glyph in sorted(value.items()):
            if glyph is not None and glyph != 0xFFFF:
                xmlWriter.simpletag("CID", cid=cid, glyph=glyph)
                xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()


class GlyphCIDMap(BaseConverter):
    def read(self, reader, font, tableDict):
        glyphOrder = font.getGlyphOrder()
        count = reader.readUShort()
        cids = reader.readUShortArray(count)
        if count > len(glyphOrder):
            log.warning(
                "GlyphCIDMap has %d elements, "
                "but the font has only %d glyphs; "
                "ignoring the rest" % (count, len(glyphOrder))
            )
        result = {}
        for glyphID in range(min(len(cids), len(glyphOrder))):
            cid = cids[glyphID]
            if cid != 0xFFFF:
                result[glyphOrder[glyphID]] = cid
        return result

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        items = {
            font.getGlyphID(g): cid
            for g, cid in value.items()
            if cid is not None and cid != 0xFFFF
        }
        count = max(items) + 1 if items else 0
        writer.writeUShort(count)
        for glyphID in range(count):
            writer.writeUShort(items.get(glyphID, 0xFFFF))

    def xmlRead(self, attrs, content, font):
        result = {}
        for eName, eAttrs, _eContent in filter(istuple, content):
            if eName == "CID":
                result[eAttrs["glyph"]] = safeEval(eAttrs["value"])
        return result

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.begintag(name, attrs)
        xmlWriter.newline()
        for glyph, cid in sorted(value.items()):
            if cid is not None and cid != 0xFFFF:
                xmlWriter.simpletag("CID", glyph=glyph, value=cid)
                xmlWriter.newline()
        xmlWriter.endtag(name)
        xmlWriter.newline()


class DeltaValue(BaseConverter):
    def read(self, reader, font, tableDict):
        StartSize = tableDict["StartSize"]
        EndSize = tableDict["EndSize"]
        DeltaFormat = tableDict["DeltaFormat"]
        assert DeltaFormat in (1, 2, 3), "illegal DeltaFormat"
        nItems = EndSize - StartSize + 1
        nBits = 1 << DeltaFormat
        minusOffset = 1 << nBits
        mask = (1 << nBits) - 1
        signMask = 1 << (nBits - 1)

        DeltaValue = []
        tmp, shift = 0, 0
        for i in range(nItems):
            if shift == 0:
                tmp, shift = reader.readUShort(), 16
            shift = shift - nBits
            value = (tmp >> shift) & mask
            if value & signMask:
                value = value - minusOffset
            DeltaValue.append(value)
        return DeltaValue

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        StartSize = tableDict["StartSize"]
        EndSize = tableDict["EndSize"]
        DeltaFormat = tableDict["DeltaFormat"]
        DeltaValue = value
        assert DeltaFormat in (1, 2, 3), "illegal DeltaFormat"
        nItems = EndSize - StartSize + 1
        nBits = 1 << DeltaFormat
        assert len(DeltaValue) == nItems
        mask = (1 << nBits) - 1

        tmp, shift = 0, 16
        for value in DeltaValue:
            shift = shift - nBits
            tmp = tmp | ((value & mask) << shift)
            if shift == 0:
                writer.writeUShort(tmp)
                tmp, shift = 0, 16
        if shift != 16:
            writer.writeUShort(tmp)

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        return safeEval(attrs["value"])


class VarIdxMapValue(BaseConverter):
    def read(self, reader, font, tableDict):
        fmt = tableDict["EntryFormat"]
        nItems = tableDict["MappingCount"]

        innerBits = 1 + (fmt & 0x000F)
        innerMask = (1 << innerBits) - 1
        outerMask = 0xFFFFFFFF - innerMask
        outerShift = 16 - innerBits

        entrySize = 1 + ((fmt & 0x0030) >> 4)
        readArray = {
            1: reader.readUInt8Array,
            2: reader.readUShortArray,
            3: reader.readUInt24Array,
            4: reader.readULongArray,
        }[entrySize]

        return [
            (((raw & outerMask) << outerShift) | (raw & innerMask))
            for raw in readArray(nItems)
        ]

    def write(self, writer, font, tableDict, value, repeatIndex=None):
        fmt = tableDict["EntryFormat"]
        mapping = value
        writer["MappingCount"].setValue(len(mapping))

        innerBits = 1 + (fmt & 0x000F)
        innerMask = (1 << innerBits) - 1
        outerShift = 16 - innerBits

        entrySize = 1 + ((fmt & 0x0030) >> 4)
        writeArray = {
            1: writer.writeUInt8Array,
            2: writer.writeUShortArray,
            3: writer.writeUInt24Array,
            4: writer.writeULongArray,
        }[entrySize]

        writeArray(
            [
                (((idx & 0xFFFF0000) >> outerShift) | (idx & innerMask))
                for idx in mapping
            ]
        )


class VarDataValue(BaseConverter):
    def read(self, reader, font, tableDict):
        values = []

        regionCount = tableDict["VarRegionCount"]
        wordCount = tableDict["NumShorts"]

        # https://github.com/fonttools/fonttools/issues/2279
        longWords = bool(wordCount & 0x8000)
        wordCount = wordCount & 0x7FFF

        if longWords:
            readBigArray, readSmallArray = reader.readLongArray, reader.readShortArray
        else:
            readBigArray, readSmallArray = reader.readShortArray, reader.readInt8Array

        n1, n2 = min(regionCount, wordCount), max(regionCount, wordCount)
        values.extend(readBigArray(n1))
        values.extend(readSmallArray(n2 - n1))
        if n2 > regionCount:  # Padding
            del values[regionCount:]

        return values

    def write(self, writer, font, tableDict, values, repeatIndex=None):
        regionCount = tableDict["VarRegionCount"]
        wordCount = tableDict["NumShorts"]

        # https://github.com/fonttools/fonttools/issues/2279
        longWords = bool(wordCount & 0x8000)
        wordCount = wordCount & 0x7FFF

        (writeBigArray, writeSmallArray) = {
            False: (writer.writeShortArray, writer.writeInt8Array),
            True: (writer.writeLongArray, writer.writeShortArray),
        }[longWords]

        n1, n2 = min(regionCount, wordCount), max(regionCount, wordCount)
        writeBigArray(values[:n1])
        writeSmallArray(values[n1:regionCount])
        if n2 > regionCount:  # Padding
            writer.writeSmallArray([0] * (n2 - regionCount))

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        xmlWriter.newline()

    def xmlRead(self, attrs, content, font):
        return safeEval(attrs["value"])


class TupleValues:
    def read(self, data, font):
        return TupleVariation.decompileDeltas_(None, data)[0]

    def write(self, writer, font, tableDict, values, repeatIndex=None):
        optimizeSpeed = font.cfg[OPTIMIZE_FONT_SPEED]
        return bytes(
            TupleVariation.compileDeltaValues_(values, optimizeSize=not optimizeSpeed)
        )

    def xmlRead(self, attrs, content, font):
        return safeEval(attrs["value"])

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        xmlWriter.newline()


class CFF2Index(BaseConverter):
    def __init__(
        self,
        name,
        repeat,
        aux,
        tableClass=None,
        *,
        itemClass=None,
        itemConverterClass=None,
        description="",
    ):
        BaseConverter.__init__(
            self, name, repeat, aux, tableClass, description=description
        )
        self._itemClass = itemClass
        self._converter = (
            itemConverterClass() if itemConverterClass is not None else None
        )

    def read(self, reader, font, tableDict):
        count = reader.readULong()
        if count == 0:
            return []
        offSize = reader.readUInt8()

        def getReadArray(reader, offSize):
            return {
                1: reader.readUInt8Array,
                2: reader.readUShortArray,
                3: reader.readUInt24Array,
                4: reader.readULongArray,
            }[offSize]

        readArray = getReadArray(reader, offSize)

        lazy = font.lazy is not False and count > 8
        if not lazy:
            offsets = readArray(count + 1)
            items = []
            lastOffset = offsets.pop(0)
            reader.readData(lastOffset - 1)  # In case first offset is not 1

            for offset in offsets:
                assert lastOffset <= offset
                item = reader.readData(offset - lastOffset)

                if self._itemClass is not None:
                    obj = self._itemClass()
                    obj.decompile(item, font, reader.localState)
                    item = obj
                elif self._converter is not None:
                    item = self._converter.read(item, font)

                items.append(item)
                lastOffset = offset
            return items
        else:

            def get_read_item():
                reader_copy = reader.copy()
                offset_pos = reader.pos
                data_pos = offset_pos + (count + 1) * offSize - 1
                readArray = getReadArray(reader_copy, offSize)

                def read_item(i):
                    reader_copy.seek(offset_pos + i * offSize)
                    offsets = readArray(2)
                    reader_copy.seek(data_pos + offsets[0])
                    item = reader_copy.readData(offsets[1] - offsets[0])

                    if self._itemClass is not None:
                        obj = self._itemClass()
                        obj.decompile(item, font, reader_copy.localState)
                        item = obj
                    elif self._converter is not None:
                        item = self._converter.read(item, font)
                    return item

                return read_item

            read_item = get_read_item()
            l = LazyList([read_item] * count)

            # TODO: Advance reader

            return l

    def write(self, writer, font, tableDict, values, repeatIndex=None):
        items = values

        writer.writeULong(len(items))
        if not len(items):
            return

        if self._itemClass is not None:
            items = [item.compile(font) for item in items]
        elif self._converter is not None:
            items = [
                self._converter.write(writer, font, tableDict, item, i)
                for i, item in enumerate(items)
            ]

        offsets = [len(item) for item in items]
        offsets = list(accumulate(offsets, initial=1))

        lastOffset = offsets[-1]
        offSize = (
            1
            if lastOffset < 0x100
            else 2 if lastOffset < 0x10000 else 3 if lastOffset < 0x1000000 else 4
        )
        writer.writeUInt8(offSize)

        writeArray = {
            1: writer.writeUInt8Array,
            2: writer.writeUShortArray,
            3: writer.writeUInt24Array,
            4: writer.writeULongArray,
        }[offSize]

        writeArray(offsets)
        for item in items:
            writer.writeData(item)

    def xmlRead(self, attrs, content, font):
        if self._itemClass is not None:
            obj = self._itemClass()
            obj.fromXML(None, attrs, content, font)
            return obj
        elif self._converter is not None:
            return self._converter.xmlRead(attrs, content, font)
        else:
            raise NotImplementedError()

    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        if self._itemClass is not None:
            for i, item in enumerate(value):
                item.toXML(xmlWriter, font, [("index", i)], name)
        elif self._converter is not None:
            for i, item in enumerate(value):
                self._converter.xmlWrite(
                    xmlWriter, font, item, name, attrs + [("index", i)]
                )
        else:
            raise NotImplementedError()


class LookupFlag(UShort):
    def xmlWrite(self, xmlWriter, font, value, name, attrs):
        xmlWriter.simpletag(name, attrs + [("value", value)])
        flags = []
        if value & 0x01:
            flags.append("rightToLeft")
        if value & 0x02:
            flags.append("ignoreBaseGlyphs")
        if value & 0x04:
            flags.append("ignoreLigatures")
        if value & 0x08:
            flags.append("ignoreMarks")
        if value & 0x10:
            flags.append("useMarkFilteringSet")
        if value & 0xFF00:
            flags.append("markAttachmentType[%i]" % (value >> 8))
        if flags:
            xmlWriter.comment(" ".join(flags))
        xmlWriter.newline()


class _UInt8Enum(UInt8):
    enumClass = NotImplemented

    def read(self, reader, font, tableDict):
        return self.enumClass(super().read(reader, font, tableDict))

    @classmethod
    def fromString(cls, value):
        return getattr(cls.enumClass, value.upper())

    @classmethod
    def toString(cls, value):
        return cls.enumClass(value).name.lower()


class ExtendMode(_UInt8Enum):
    enumClass = _ExtendMode


class CompositeMode(_UInt8Enum):
    enumClass = _CompositeMode


converterMapping = {
    # type		class
    "int8": Int8,
    "int16": Short,
    "int32": Long,
    "uint8": UInt8,
    "uint16": UShort,
    "uint24": UInt24,
    "uint32": ULong,
    "char64": Char64,
    "Flags32": Flags32,
    "VarIndex": VarIndex,
    "Version": Version,
    "Tag": Tag,
    "GlyphID": GlyphID,
    "GlyphID32": GlyphID32,
    "NameID": NameID,
    "DeciPoints": DeciPoints,
    "Fixed": Fixed,
    "F2Dot14": F2Dot14,
    "Angle": Angle,
    "BiasedAngle": BiasedAngle,
    "struct": Struct,
    "Offset": Table,
    "LOffset": LTable,
    "Offset24": Table24,
    "ValueRecord": ValueRecord,
    "DeltaValue": DeltaValue,
    "VarIdxMapValue": VarIdxMapValue,
    "VarDataValue": VarDataValue,
    "LookupFlag": LookupFlag,
    "ExtendMode": ExtendMode,
    "CompositeMode": CompositeMode,
    "STATFlags": STATFlags,
    "TupleList": partial(CFF2Index, itemConverterClass=TupleValues),
    "VarCompositeGlyphList": partial(CFF2Index, itemClass=VarCompositeGlyph),
    # AAT
    "CIDGlyphMap": CIDGlyphMap,
    "GlyphCIDMap": GlyphCIDMap,
    "MortChain": StructWithLength,
    "MortSubtable": StructWithLength,
    "MorxChain": StructWithLength,
    "MorxSubtable": MorxSubtableConverter,
    # "Template" types
    "AATLookup": lambda C: partial(AATLookup, tableClass=C),
    "AATLookupWithDataOffset": lambda C: partial(AATLookupWithDataOffset, tableClass=C),
    "STXHeader": lambda C: partial(STXHeader, tableClass=C),
    "OffsetTo": lambda C: partial(Table, tableClass=C),
    "LOffsetTo": lambda C: partial(LTable, tableClass=C),
    "LOffset24To": lambda C: partial(Table24, tableClass=C),
}

# === NexusCore/openenv\Lib\site-packages\nltk\sem\logic.py ===
# Natural Language Toolkit: Logic
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A version of first order predicate logic, built on
top of the typed lambda calculus.
"""

import operator
import re
from collections import defaultdict
from functools import reduce, total_ordering

from nltk.internals import Counter
from nltk.util import Trie

APP = "APP"

_counter = Counter()


class Tokens:
    LAMBDA = "\\"
    LAMBDA_LIST = ["\\"]

    # Quantifiers
    EXISTS = "exists"
    EXISTS_LIST = ["some", "exists", "exist"]
    ALL = "all"
    ALL_LIST = ["all", "forall"]
    IOTA = "iota"
    IOTA_LIST = ["iota"]

    # Punctuation
    DOT = "."
    OPEN = "("
    CLOSE = ")"
    COMMA = ","

    # Operations
    NOT = "-"
    NOT_LIST = ["not", "-", "!"]
    AND = "&"
    AND_LIST = ["and", "&", "^"]
    OR = "|"
    OR_LIST = ["or", "|"]
    IMP = "->"
    IMP_LIST = ["implies", "->", "=>"]
    IFF = "<->"
    IFF_LIST = ["iff", "<->", "<=>"]
    EQ = "="
    EQ_LIST = ["=", "=="]
    NEQ = "!="
    NEQ_LIST = ["!="]

    # Collections of tokens
    BINOPS = AND_LIST + OR_LIST + IMP_LIST + IFF_LIST
    QUANTS = EXISTS_LIST + ALL_LIST + IOTA_LIST
    PUNCT = [DOT, OPEN, CLOSE, COMMA]

    TOKENS = BINOPS + EQ_LIST + NEQ_LIST + QUANTS + LAMBDA_LIST + PUNCT + NOT_LIST

    # Special
    SYMBOLS = [x for x in TOKENS if re.match(r"^[-\\.(),!&^|>=<]*$", x)]


def boolean_ops():
    """
    Boolean operators
    """
    names = ["negation", "conjunction", "disjunction", "implication", "equivalence"]
    for pair in zip(names, [Tokens.NOT, Tokens.AND, Tokens.OR, Tokens.IMP, Tokens.IFF]):
        print("%-15s\t%s" % pair)


def equality_preds():
    """
    Equality predicates
    """
    names = ["equality", "inequality"]
    for pair in zip(names, [Tokens.EQ, Tokens.NEQ]):
        print("%-15s\t%s" % pair)


def binding_ops():
    """
    Binding operators
    """
    names = ["existential", "universal", "lambda"]
    for pair in zip(names, [Tokens.EXISTS, Tokens.ALL, Tokens.LAMBDA, Tokens.IOTA]):
        print("%-15s\t%s" % pair)


class LogicParser:
    """A lambda calculus expression parser."""

    def __init__(self, type_check=False):
        """
        :param type_check: should type checking be performed
            to their types?
        :type type_check: bool
        """
        assert isinstance(type_check, bool)

        self._currentIndex = 0
        self._buffer = []
        self.type_check = type_check

        """A list of tuples of quote characters.  The 4-tuple is comprised
        of the start character, the end character, the escape character, and
        a boolean indicating whether the quotes should be included in the
        result. Quotes are used to signify that a token should be treated as
        atomic, ignoring any special characters within the token.  The escape
        character allows the quote end character to be used within the quote.
        If True, the boolean indicates that the final token should contain the
        quote and escape characters.
        This method exists to be overridden"""
        self.quote_chars = []

        self.operator_precedence = dict(
            [(x, 1) for x in Tokens.LAMBDA_LIST]
            + [(x, 2) for x in Tokens.NOT_LIST]
            + [(APP, 3)]
            + [(x, 4) for x in Tokens.EQ_LIST + Tokens.NEQ_LIST]
            + [(x, 5) for x in Tokens.QUANTS]
            + [(x, 6) for x in Tokens.AND_LIST]
            + [(x, 7) for x in Tokens.OR_LIST]
            + [(x, 8) for x in Tokens.IMP_LIST]
            + [(x, 9) for x in Tokens.IFF_LIST]
            + [(None, 10)]
        )
        self.right_associated_operations = [APP]

    def parse(self, data, signature=None):
        """
        Parse the expression.

        :param data: str for the input to be parsed
        :param signature: ``dict<str, str>`` that maps variable names to type
            strings
        :returns: a parsed Expression
        """
        data = data.rstrip()

        self._currentIndex = 0
        self._buffer, mapping = self.process(data)

        try:
            result = self.process_next_expression(None)
            if self.inRange(0):
                raise UnexpectedTokenException(self._currentIndex + 1, self.token(0))
        except LogicalExpressionException as e:
            msg = "{}\n{}\n{}^".format(e, data, " " * mapping[e.index - 1])
            raise LogicalExpressionException(None, msg) from e

        if self.type_check:
            result.typecheck(signature)

        return result

    def process(self, data):
        """Split the data into tokens"""
        out = []
        mapping = {}
        tokenTrie = Trie(self.get_all_symbols())
        token = ""
        data_idx = 0
        token_start_idx = data_idx
        while data_idx < len(data):
            cur_data_idx = data_idx
            quoted_token, data_idx = self.process_quoted_token(data_idx, data)
            if quoted_token:
                if not token:
                    token_start_idx = cur_data_idx
                token += quoted_token
                continue

            st = tokenTrie
            c = data[data_idx]
            symbol = ""
            while c in st:
                symbol += c
                st = st[c]
                if len(data) - data_idx > len(symbol):
                    c = data[data_idx + len(symbol)]
                else:
                    break
            if Trie.LEAF in st:
                # token is a complete symbol
                if token:
                    mapping[len(out)] = token_start_idx
                    out.append(token)
                    token = ""
                mapping[len(out)] = data_idx
                out.append(symbol)
                data_idx += len(symbol)
            else:
                if data[data_idx] in " \t\n":  # any whitespace
                    if token:
                        mapping[len(out)] = token_start_idx
                        out.append(token)
                        token = ""
                else:
                    if not token:
                        token_start_idx = data_idx
                    token += data[data_idx]
                data_idx += 1
        if token:
            mapping[len(out)] = token_start_idx
            out.append(token)
        mapping[len(out)] = len(data)
        mapping[len(out) + 1] = len(data) + 1
        return out, mapping

    def process_quoted_token(self, data_idx, data):
        token = ""
        c = data[data_idx]
        i = data_idx
        for start, end, escape, incl_quotes in self.quote_chars:
            if c == start:
                if incl_quotes:
                    token += c
                i += 1
                while data[i] != end:
                    if data[i] == escape:
                        if incl_quotes:
                            token += data[i]
                        i += 1
                        if len(data) == i:  # if there are no more chars
                            raise LogicalExpressionException(
                                None,
                                "End of input reached.  "
                                "Escape character [%s] found at end." % escape,
                            )
                        token += data[i]
                    else:
                        token += data[i]
                    i += 1
                    if len(data) == i:
                        raise LogicalExpressionException(
                            None, "End of input reached.  " "Expected: [%s]" % end
                        )
                if incl_quotes:
                    token += data[i]
                i += 1
                if not token:
                    raise LogicalExpressionException(None, "Empty quoted token found")
                break
        return token, i

    def get_all_symbols(self):
        """This method exists to be overridden"""
        return Tokens.SYMBOLS

    def inRange(self, location):
        """Return TRUE if the given location is within the buffer"""
        return self._currentIndex + location < len(self._buffer)

    def token(self, location=None):
        """Get the next waiting token.  If a location is given, then
        return the token at currentIndex+location without advancing
        currentIndex; setting it gives lookahead/lookback capability."""
        try:
            if location is None:
                tok = self._buffer[self._currentIndex]
                self._currentIndex += 1
            else:
                tok = self._buffer[self._currentIndex + location]
            return tok
        except IndexError as e:
            raise ExpectedMoreTokensException(self._currentIndex + 1) from e

    def isvariable(self, tok):
        return tok not in Tokens.TOKENS

    def process_next_expression(self, context):
        """Parse the next complete expression from the stream and return it."""
        try:
            tok = self.token()
        except ExpectedMoreTokensException as e:
            raise ExpectedMoreTokensException(
                self._currentIndex + 1, message="Expression expected."
            ) from e

        accum = self.handle(tok, context)

        if not accum:
            raise UnexpectedTokenException(
                self._currentIndex, tok, message="Expression expected."
            )

        return self.attempt_adjuncts(accum, context)

    def handle(self, tok, context):
        """This method is intended to be overridden for logics that
        use different operators or expressions"""
        if self.isvariable(tok):
            return self.handle_variable(tok, context)

        elif tok in Tokens.NOT_LIST:
            return self.handle_negation(tok, context)

        elif tok in Tokens.LAMBDA_LIST:
            return self.handle_lambda(tok, context)

        elif tok in Tokens.QUANTS:
            return self.handle_quant(tok, context)

        elif tok == Tokens.OPEN:
            return self.handle_open(tok, context)

    def attempt_adjuncts(self, expression, context):
        cur_idx = None
        while cur_idx != self._currentIndex:  # while adjuncts are added
            cur_idx = self._currentIndex
            expression = self.attempt_EqualityExpression(expression, context)
            expression = self.attempt_ApplicationExpression(expression, context)
            expression = self.attempt_BooleanExpression(expression, context)
        return expression

    def handle_negation(self, tok, context):
        return self.make_NegatedExpression(self.process_next_expression(Tokens.NOT))

    def make_NegatedExpression(self, expression):
        return NegatedExpression(expression)

    def handle_variable(self, tok, context):
        # It's either: 1) a predicate expression: sees(x,y)
        #             2) an application expression: P(x)
        #             3) a solo variable: john OR x
        accum = self.make_VariableExpression(tok)
        if self.inRange(0) and self.token(0) == Tokens.OPEN:
            # The predicate has arguments
            if not isinstance(accum, FunctionVariableExpression) and not isinstance(
                accum, ConstantExpression
            ):
                raise LogicalExpressionException(
                    self._currentIndex,
                    "'%s' is an illegal predicate name.  "
                    "Individual variables may not be used as "
                    "predicates." % tok,
                )
            self.token()  # swallow the Open Paren

            # curry the arguments
            accum = self.make_ApplicationExpression(
                accum, self.process_next_expression(APP)
            )
            while self.inRange(0) and self.token(0) == Tokens.COMMA:
                self.token()  # swallow the comma
                accum = self.make_ApplicationExpression(
                    accum, self.process_next_expression(APP)
                )
            self.assertNextToken(Tokens.CLOSE)
        return accum

    def get_next_token_variable(self, description):
        try:
            tok = self.token()
        except ExpectedMoreTokensException as e:
            raise ExpectedMoreTokensException(e.index, "Variable expected.") from e
        if isinstance(self.make_VariableExpression(tok), ConstantExpression):
            raise LogicalExpressionException(
                self._currentIndex,
                "'%s' is an illegal variable name.  "
                "Constants may not be %s." % (tok, description),
            )
        return Variable(tok)

    def handle_lambda(self, tok, context):
        # Expression is a lambda expression
        if not self.inRange(0):
            raise ExpectedMoreTokensException(
                self._currentIndex + 2,
                message="Variable and Expression expected following lambda operator.",
            )
        vars = [self.get_next_token_variable("abstracted")]
        while True:
            if not self.inRange(0) or (
                self.token(0) == Tokens.DOT and not self.inRange(1)
            ):
                raise ExpectedMoreTokensException(
                    self._currentIndex + 2, message="Expression expected."
                )
            if not self.isvariable(self.token(0)):
                break
            # Support expressions like: \x y.M == \x.\y.M
            vars.append(self.get_next_token_variable("abstracted"))
        if self.inRange(0) and self.token(0) == Tokens.DOT:
            self.token()  # swallow the dot

        accum = self.process_next_expression(tok)
        while vars:
            accum = self.make_LambdaExpression(vars.pop(), accum)
        return accum

    def handle_quant(self, tok, context):
        # Expression is a quantified expression: some x.M
        factory = self.get_QuantifiedExpression_factory(tok)

        if not self.inRange(0):
            raise ExpectedMoreTokensException(
                self._currentIndex + 2,
                message="Variable and Expression expected following quantifier '%s'."
                % tok,
            )
        vars = [self.get_next_token_variable("quantified")]
        while True:
            if not self.inRange(0) or (
                self.token(0) == Tokens.DOT and not self.inRange(1)
            ):
                raise ExpectedMoreTokensException(
                    self._currentIndex + 2, message="Expression expected."
                )
            if not self.isvariable(self.token(0)):
                break
            # Support expressions like: some x y.M == some x.some y.M
            vars.append(self.get_next_token_variable("quantified"))
        if self.inRange(0) and self.token(0) == Tokens.DOT:
            self.token()  # swallow the dot

        accum = self.process_next_expression(tok)
        while vars:
            accum = self.make_QuanifiedExpression(factory, vars.pop(), accum)
        return accum

    def get_QuantifiedExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different quantifiers"""
        if tok in Tokens.EXISTS_LIST:
            return ExistsExpression
        elif tok in Tokens.ALL_LIST:
            return AllExpression
        elif tok in Tokens.IOTA_LIST:
            return IotaExpression
        else:
            self.assertToken(tok, Tokens.QUANTS)

    def make_QuanifiedExpression(self, factory, variable, term):
        return factory(variable, term)

    def handle_open(self, tok, context):
        # Expression is in parens
        accum = self.process_next_expression(None)
        self.assertNextToken(Tokens.CLOSE)
        return accum

    def attempt_EqualityExpression(self, expression, context):
        """Attempt to make an equality expression.  If the next token is an
        equality operator, then an EqualityExpression will be returned.
        Otherwise, the parameter will be returned."""
        if self.inRange(0):
            tok = self.token(0)
            if tok in Tokens.EQ_LIST + Tokens.NEQ_LIST and self.has_priority(
                tok, context
            ):
                self.token()  # swallow the "=" or "!="
                expression = self.make_EqualityExpression(
                    expression, self.process_next_expression(tok)
                )
                if tok in Tokens.NEQ_LIST:
                    expression = self.make_NegatedExpression(expression)
        return expression

    def make_EqualityExpression(self, first, second):
        """This method serves as a hook for other logic parsers that
        have different equality expression classes"""
        return EqualityExpression(first, second)

    def attempt_BooleanExpression(self, expression, context):
        """Attempt to make a boolean expression.  If the next token is a boolean
        operator, then a BooleanExpression will be returned.  Otherwise, the
        parameter will be returned."""
        while self.inRange(0):
            tok = self.token(0)
            factory = self.get_BooleanExpression_factory(tok)
            if factory and self.has_priority(tok, context):
                self.token()  # swallow the operator
                expression = self.make_BooleanExpression(
                    factory, expression, self.process_next_expression(tok)
                )
            else:
                break
        return expression

    def get_BooleanExpression_factory(self, tok):
        """This method serves as a hook for other logic parsers that
        have different boolean operators"""
        if tok in Tokens.AND_LIST:
            return AndExpression
        elif tok in Tokens.OR_LIST:
            return OrExpression
        elif tok in Tokens.IMP_LIST:
            return ImpExpression
        elif tok in Tokens.IFF_LIST:
            return IffExpression
        else:
            return None

    def make_BooleanExpression(self, factory, first, second):
        return factory(first, second)

    def attempt_ApplicationExpression(self, expression, context):
        """Attempt to make an application expression.  The next tokens are
        a list of arguments in parens, then the argument expression is a
        function being applied to the arguments.  Otherwise, return the
        argument expression."""
        if self.has_priority(APP, context):
            if self.inRange(0) and self.token(0) == Tokens.OPEN:
                if (
                    not isinstance(expression, LambdaExpression)
                    and not isinstance(expression, ApplicationExpression)
                    and not isinstance(expression, FunctionVariableExpression)
                    and not isinstance(expression, ConstantExpression)
                ):
                    raise LogicalExpressionException(
                        self._currentIndex,
                        ("The function '%s" % expression)
                        + "' is not a Lambda Expression, an "
                        "Application Expression, or a "
                        "functional predicate, so it may "
                        "not take arguments.",
                    )
                self.token()  # swallow then open paren
                # curry the arguments
                accum = self.make_ApplicationExpression(
                    expression, self.process_next_expression(APP)
                )
                while self.inRange(0) and self.token(0) == Tokens.COMMA:
                    self.token()  # swallow the comma
                    accum = self.make_ApplicationExpression(
                        accum, self.process_next_expression(APP)
                    )
                self.assertNextToken(Tokens.CLOSE)
                return accum
        return expression

    def make_ApplicationExpression(self, function, argument):
        return ApplicationExpression(function, argument)

    def make_VariableExpression(self, name):
        return VariableExpression(Variable(name))

    def make_LambdaExpression(self, variable, term):
        return LambdaExpression(variable, term)

    def has_priority(self, operation, context):
        return self.operator_precedence[operation] < self.operator_precedence[
            context
        ] or (
            operation in self.right_associated_operations
            and self.operator_precedence[operation] == self.operator_precedence[context]
        )

    def assertNextToken(self, expected):
        try:
            tok = self.token()
        except ExpectedMoreTokensException as e:
            raise ExpectedMoreTokensException(
                e.index, message="Expected token '%s'." % expected
            ) from e

        if isinstance(expected, list):
            if tok not in expected:
                raise UnexpectedTokenException(self._currentIndex, tok, expected)
        else:
            if tok != expected:
                raise UnexpectedTokenException(self._currentIndex, tok, expected)

    def assertToken(self, tok, expected):
        if isinstance(expected, list):
            if tok not in expected:
                raise UnexpectedTokenException(self._currentIndex, tok, expected)
        else:
            if tok != expected:
                raise UnexpectedTokenException(self._currentIndex, tok, expected)

    def __repr__(self):
        if self.inRange(0):
            msg = "Next token: " + self.token(0)
        else:
            msg = "No more tokens"
        return "<" + self.__class__.__name__ + ": " + msg + ">"


def read_logic(s, logic_parser=None, encoding=None):
    """
    Convert a file of First Order Formulas into a list of {Expression}s.

    :param s: the contents of the file
    :type s: str
    :param logic_parser: The parser to be used to parse the logical expression
    :type logic_parser: LogicParser
    :param encoding: the encoding of the input string, if it is binary
    :type encoding: str
    :return: a list of parsed formulas.
    :rtype: list(Expression)
    """
    if encoding is not None:
        s = s.decode(encoding)
    if logic_parser is None:
        logic_parser = LogicParser()

    statements = []
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith("#") or line == "":
            continue
        try:
            statements.append(logic_parser.parse(line))
        except LogicalExpressionException as e:
            raise ValueError(f"Unable to parse line {linenum}: {line}") from e
    return statements


@total_ordering
class Variable:
    def __init__(self, name):
        """
        :param name: the name of the variable
        """
        assert isinstance(name, str), "%s is not a string" % name
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Variable) and self.name == other.name

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Variable):
            raise TypeError
        return self.name < other.name

    def substitute_bindings(self, bindings):
        return bindings.get(self, self)

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "Variable('%s')" % self.name


def unique_variable(pattern=None, ignore=None):
    """
    Return a new, unique variable.

    :param pattern: ``Variable`` that is being replaced.  The new variable must
        be the same type.
    :param term: a set of ``Variable`` objects that should not be returned from
        this function.
    :rtype: Variable
    """
    if pattern is not None:
        if is_indvar(pattern.name):
            prefix = "z"
        elif is_funcvar(pattern.name):
            prefix = "F"
        elif is_eventvar(pattern.name):
            prefix = "e0"
        else:
            assert False, "Cannot generate a unique constant"
    else:
        prefix = "z"

    v = Variable(f"{prefix}{_counter.get()}")
    while ignore is not None and v in ignore:
        v = Variable(f"{prefix}{_counter.get()}")
    return v


def skolem_function(univ_scope=None):
    """
    Return a skolem function over the variables in univ_scope
    param univ_scope
    """
    skolem = VariableExpression(Variable("F%s" % _counter.get()))
    if univ_scope:
        for v in list(univ_scope):
            skolem = skolem(VariableExpression(v))
    return skolem


class Type:
    def __repr__(self):
        return "%s" % self

    def __hash__(self):
        return hash("%s" % self)

    @classmethod
    def fromstring(cls, s):
        return read_type(s)


class ComplexType(Type):
    def __init__(self, first, second):
        assert isinstance(first, Type), "%s is not a Type" % first
        assert isinstance(second, Type), "%s is not a Type" % second
        self.first = first
        self.second = second

    def __eq__(self, other):
        return (
            isinstance(other, ComplexType)
            and self.first == other.first
            and self.second == other.second
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = Type.__hash__

    def matches(self, other):
        if isinstance(other, ComplexType):
            return self.first.matches(other.first) and self.second.matches(other.second)
        else:
            return self == ANY_TYPE

    def resolve(self, other):
        if other == ANY_TYPE:
            return self
        elif isinstance(other, ComplexType):
            f = self.first.resolve(other.first)
            s = self.second.resolve(other.second)
            if f and s:
                return ComplexType(f, s)
            else:
                return None
        elif self == ANY_TYPE:
            return other
        else:
            return None

    def __str__(self):
        if self == ANY_TYPE:
            return "%s" % ANY_TYPE
        else:
            return f"<{self.first},{self.second}>"

    def str(self):
        if self == ANY_TYPE:
            return ANY_TYPE.str()
        else:
            return f"({self.first.str()} -> {self.second.str()})"


class BasicType(Type):
    def __eq__(self, other):
        return isinstance(other, BasicType) and ("%s" % self) == ("%s" % other)

    def __ne__(self, other):
        return not self == other

    __hash__ = Type.__hash__

    def matches(self, other):
        return other == ANY_TYPE or self == other

    def resolve(self, other):
        if self.matches(other):
            return self
        else:
            return None


class EntityType(BasicType):
    def __str__(self):
        return "e"

    def str(self):
        return "IND"


class TruthValueType(BasicType):
    def __str__(self):
        return "t"

    def str(self):
        return "BOOL"


class EventType(BasicType):
    def __str__(self):
        return "v"

    def str(self):
        return "EVENT"


class AnyType(BasicType, ComplexType):
    def __init__(self):
        pass

    @property
    def first(self):
        return self

    @property
    def second(self):
        return self

    def __eq__(self, other):
        return isinstance(other, AnyType) or other.__eq__(self)

    def __ne__(self, other):
        return not self == other

    __hash__ = Type.__hash__

    def matches(self, other):
        return True

    def resolve(self, other):
        return other

    def __str__(self):
        return "?"

    def str(self):
        return "ANY"


TRUTH_TYPE = TruthValueType()
ENTITY_TYPE = EntityType()
EVENT_TYPE = EventType()
ANY_TYPE = AnyType()


def read_type(type_string):
    assert isinstance(type_string, str)
    type_string = type_string.replace(" ", "")  # remove spaces

    if type_string[0] == "<":
        assert type_string[-1] == ">"
        paren_count = 0
        for i, char in enumerate(type_string):
            if char == "<":
                paren_count += 1
            elif char == ">":
                paren_count -= 1
                assert paren_count > 0
            elif char == ",":
                if paren_count == 1:
                    break
        return ComplexType(
            read_type(type_string[1:i]), read_type(type_string[i + 1 : -1])
        )
    elif type_string[0] == "%s" % ENTITY_TYPE:
        return ENTITY_TYPE
    elif type_string[0] == "%s" % TRUTH_TYPE:
        return TRUTH_TYPE
    elif type_string[0] == "%s" % ANY_TYPE:
        return ANY_TYPE
    else:
        raise LogicalExpressionException(
            None, "Unexpected character: '%s'." % type_string[0]
        )


class TypeException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class InconsistentTypeHierarchyException(TypeException):
    def __init__(self, variable, expression=None):
        if expression:
            msg = (
                "The variable '%s' was found in multiple places with different"
                " types in '%s'." % (variable, expression)
            )
        else:
            msg = (
                "The variable '%s' was found in multiple places with different"
                " types." % (variable)
            )
        super().__init__(msg)


class TypeResolutionException(TypeException):
    def __init__(self, expression, other_type):
        super().__init__(
            "The type of '%s', '%s', cannot be resolved with type '%s'"
            % (expression, expression.type, other_type)
        )


class IllegalTypeException(TypeException):
    def __init__(self, expression, other_type, allowed_type):
        super().__init__(
            "Cannot set type of %s '%s' to '%s'; must match type '%s'."
            % (expression.__class__.__name__, expression, other_type, allowed_type)
        )


def typecheck(expressions, signature=None):
    """
    Ensure correct typing across a collection of ``Expression`` objects.
    :param expressions: a collection of expressions
    :param signature: dict that maps variable names to types (or string
    representations of types)
    """
    # typecheck and create master signature
    for expression in expressions:
        signature = expression.typecheck(signature)
    # apply master signature to all expressions
    for expression in expressions[:-1]:
        expression.typecheck(signature)
    return signature


class SubstituteBindingsI:
    """
    An interface for classes that can perform substitutions for
    variables.
    """

    def substitute_bindings(self, bindings):
        """
        :return: The object that is obtained by replacing
            each variable bound by ``bindings`` with its values.
            Aliases are already resolved. (maybe?)
        :rtype: (any)
        """
        raise NotImplementedError()

    def variables(self):
        """
        :return: A list of all variables in this object.
        """
        raise NotImplementedError()


class Expression(SubstituteBindingsI):
    """This is the base abstract object for all logical expressions"""

    _logic_parser = LogicParser()
    _type_checking_logic_parser = LogicParser(type_check=True)

    @classmethod
    def fromstring(cls, s, type_check=False, signature=None):
        if type_check:
            return cls._type_checking_logic_parser.parse(s, signature)
        else:
            return cls._logic_parser.parse(s, signature)

    def __call__(self, other, *additional):
        accum = self.applyto(other)
        for a in additional:
            accum = accum(a)
        return accum

    def applyto(self, other):
        assert isinstance(other, Expression), "%s is not an Expression" % other
        return ApplicationExpression(self, other)

    def __neg__(self):
        return NegatedExpression(self)

    def negate(self):
        """If this is a negated expression, remove the negation.
        Otherwise add a negation."""
        return -self

    def __and__(self, other):
        if not isinstance(other, Expression):
            raise TypeError("%s is not an Expression" % other)
        return AndExpression(self, other)

    def __or__(self, other):
        if not isinstance(other, Expression):
            raise TypeError("%s is not an Expression" % other)
        return OrExpression(self, other)

    def __gt__(self, other):
        if not isinstance(other, Expression):
            raise TypeError("%s is not an Expression" % other)
        return ImpExpression(self, other)

    def __lt__(self, other):
        if not isinstance(other, Expression):
            raise TypeError("%s is not an Expression" % other)
        return IffExpression(self, other)

    def __eq__(self, other):
        return NotImplemented

    def __ne__(self, other):
        return not self == other

    def equiv(self, other, prover=None):
        """
        Check for logical equivalence.
        Pass the expression (self <-> other) to the theorem prover.
        If the prover says it is valid, then the self and other are equal.

        :param other: an ``Expression`` to check equality against
        :param prover: a ``nltk.inference.api.Prover``
        """
        assert isinstance(other, Expression), "%s is not an Expression" % other

        if prover is None:
            from nltk.inference import Prover9

            prover = Prover9()
        bicond = IffExpression(self.simplify(), other.simplify())
        return prover.prove(bicond)

    def __hash__(self):
        return hash(repr(self))

    def substitute_bindings(self, bindings):
        expr = self
        for var in expr.variables():
            if var in bindings:
                val = bindings[var]
                if isinstance(val, Variable):
                    val = self.make_VariableExpression(val)
                elif not isinstance(val, Expression):
                    raise ValueError(
                        "Can not substitute a non-expression "
                        "value into an expression: %r" % (val,)
                    )
                # Substitute bindings in the target value.
                val = val.substitute_bindings(bindings)
                # Replace var w/ the target value.
                expr = expr.replace(var, val)
        return expr.simplify()

    def typecheck(self, signature=None):
        """
        Infer and check types.  Raise exceptions if necessary.

        :param signature: dict that maps variable names to types (or string
            representations of types)
        :return: the signature, plus any additional type mappings
        """
        sig = defaultdict(list)
        if signature:
            for key in signature:
                val = signature[key]
                varEx = VariableExpression(Variable(key))
                if isinstance(val, Type):
                    varEx.type = val
                else:
                    varEx.type = read_type(val)
                sig[key].append(varEx)

        self._set_type(signature=sig)

        return {key: sig[key][0].type for key in sig}

    def findtype(self, variable):
        """
        Find the type of the given variable as it is used in this expression.
        For example, finding the type of "P" in "P(x) & Q(x,y)" yields "<e,t>"

        :param variable: Variable
        """
        raise NotImplementedError()

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """
        Set the type of this expression to be the given type.  Raise type
        exceptions where applicable.

        :param other_type: Type
        :param signature: dict(str -> list(AbstractVariableExpression))
        """
        raise NotImplementedError()

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """
        Replace every instance of 'variable' with 'expression'
        :param variable: ``Variable`` The variable to replace
        :param expression: ``Expression`` The expression with which to replace it
        :param replace_bound: bool Should bound variables be replaced?
        :param alpha_convert: bool Alpha convert automatically to avoid name clashes?
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), (
            "%s is not an Expression" % expression
        )

        return self.visit_structured(
            lambda e: e.replace(variable, expression, replace_bound, alpha_convert),
            self.__class__,
        )

    def normalize(self, newvars=None):
        """Rename auto-generated unique variables"""

        def get_indiv_vars(e):
            if isinstance(e, IndividualVariableExpression):
                return {e}
            elif isinstance(e, AbstractVariableExpression):
                return set()
            else:
                return e.visit(
                    get_indiv_vars, lambda parts: reduce(operator.or_, parts, set())
                )

        result = self
        for i, e in enumerate(sorted(get_indiv_vars(self), key=lambda e: e.variable)):
            if isinstance(e, EventVariableExpression):
                newVar = e.__class__(Variable("e0%s" % (i + 1)))
            elif isinstance(e, IndividualVariableExpression):
                newVar = e.__class__(Variable("z%s" % (i + 1)))
            else:
                newVar = e
            result = result.replace(e.variable, newVar, True)
        return result

    def visit(self, function, combinator):
        """
        Recursively visit subexpressions.  Apply 'function' to each
        subexpression and pass the result of each function application
        to the 'combinator' for aggregation:

            return combinator(map(function, self.subexpressions))

        Bound variables are neither applied upon by the function nor given to
        the combinator.
        :param function: ``Function<Expression,T>`` to call on each subexpression
        :param combinator: ``Function<list<T>,R>`` to combine the results of the
        function calls
        :return: result of combination ``R``
        """
        raise NotImplementedError()

    def visit_structured(self, function, combinator):
        """
        Recursively visit subexpressions.  Apply 'function' to each
        subexpression and pass the result of each function application
        to the 'combinator' for aggregation.  The combinator must have
        the same signature as the constructor.  The function is not
        applied to bound variables, but they are passed to the
        combinator.
        :param function: ``Function`` to call on each subexpression
        :param combinator: ``Function`` with the same signature as the
        constructor, to combine the results of the function calls
        :return: result of combination
        """
        return self.visit(function, lambda parts: combinator(*parts))

    def __repr__(self):
        return f"<{self.__class__.__name__} {self}>"

    def __str__(self):
        return self.str()

    def variables(self):
        """
        Return a set of all the variables for binding substitution.
        The variables returned include all free (non-bound) individual
        variables and any variable starting with '?' or '@'.
        :return: set of ``Variable`` objects
        """
        return self.free() | {
            p for p in self.predicates() | self.constants() if re.match("^[?@]", p.name)
        }

    def free(self):
        """
        Return a set of all the free (non-bound) variables.  This includes
        both individual and predicate variables, but not constants.
        :return: set of ``Variable`` objects
        """
        return self.visit(
            lambda e: e.free(), lambda parts: reduce(operator.or_, parts, set())
        )

    def constants(self):
        """
        Return a set of individual constants (non-predicates).
        :return: set of ``Variable`` objects
        """
        return self.visit(
            lambda e: e.constants(), lambda parts: reduce(operator.or_, parts, set())
        )

    def predicates(self):
        """
        Return a set of predicates (constants, not variables).
        :return: set of ``Variable`` objects
        """
        return self.visit(
            lambda e: e.predicates(), lambda parts: reduce(operator.or_, parts, set())
        )

    def simplify(self):
        """
        :return: beta-converted version of this expression
        """
        return self.visit_structured(lambda e: e.simplify(), self.__class__)

    def make_VariableExpression(self, variable):
        return VariableExpression(variable)


class ApplicationExpression(Expression):
    r"""
    This class is used to represent two related types of logical expressions.

    The first is a Predicate Expression, such as "P(x,y)".  A predicate
    expression is comprised of a ``FunctionVariableExpression`` or
    ``ConstantExpression`` as the predicate and a list of Expressions as the
    arguments.

    The second is a an application of one expression to another, such as
    "(\x.dog(x))(fido)".

    The reason Predicate Expressions are treated as Application Expressions is
    that the Variable Expression predicate of the expression may be replaced
    with another Expression, such as a LambdaExpression, which would mean that
    the Predicate should be thought of as being applied to the arguments.

    The logical expression reader will always curry arguments in a application expression.
    So, "\x y.see(x,y)(john,mary)" will be represented internally as
    "((\x y.(see(x))(y))(john))(mary)".  This simplifies the internals since
    there will always be exactly one argument in an application.

    The str() method will usually print the curried forms of application
    expressions.  The one exception is when the the application expression is
    really a predicate expression (ie, underlying function is an
    ``AbstractVariableExpression``).  This means that the example from above
    will be returned as "(\x y.see(x,y)(john))(mary)".
    """

    def __init__(self, function, argument):
        """
        :param function: ``Expression``, for the function expression
        :param argument: ``Expression``, for the argument
        """
        assert isinstance(function, Expression), "%s is not an Expression" % function
        assert isinstance(argument, Expression), "%s is not an Expression" % argument
        self.function = function
        self.argument = argument

    def simplify(self):
        function = self.function.simplify()
        argument = self.argument.simplify()
        if isinstance(function, LambdaExpression):
            return function.term.replace(function.variable, argument).simplify()
        else:
            return self.__class__(function, argument)

    @property
    def type(self):
        if isinstance(self.function.type, ComplexType):
            return self.function.type.second
        else:
            return ANY_TYPE

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        self.argument._set_type(ANY_TYPE, signature)
        try:
            self.function._set_type(
                ComplexType(self.argument.type, other_type), signature
            )
        except TypeResolutionException as e:
            raise TypeException(
                "The function '%s' is of type '%s' and cannot be applied "
                "to '%s' of type '%s'.  Its argument must match type '%s'."
                % (
                    self.function,
                    self.function.type,
                    self.argument,
                    self.argument.type,
                    self.function.type.first,
                )
            ) from e

    def findtype(self, variable):
        """:see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        if self.is_atom():
            function, args = self.uncurry()
        else:
            # It's not a predicate expression ("P(x,y)"), so leave args curried
            function = self.function
            args = [self.argument]

        found = [arg.findtype(variable) for arg in [function] + args]

        unique = []
        for f in found:
            if f != ANY_TYPE:
                if unique:
                    for u in unique:
                        if f.matches(u):
                            break
                else:
                    unique.append(f)

        if len(unique) == 1:
            return list(unique)[0]
        else:
            return ANY_TYPE

    def constants(self):
        """:see: Expression.constants()"""
        if isinstance(self.function, AbstractVariableExpression):
            function_constants = set()
        else:
            function_constants = self.function.constants()
        return function_constants | self.argument.constants()

    def predicates(self):
        """:see: Expression.predicates()"""
        if isinstance(self.function, ConstantExpression):
            function_preds = {self.function.variable}
        else:
            function_preds = self.function.predicates()
        return function_preds | self.argument.predicates()

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        return combinator([function(self.function), function(self.argument)])

    def __eq__(self, other):
        return (
            isinstance(other, ApplicationExpression)
            and self.function == other.function
            and self.argument == other.argument
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__

    def __str__(self):
        # uncurry the arguments and find the base function
        if self.is_atom():
            function, args = self.uncurry()
            arg_str = ",".join("%s" % arg for arg in args)
        else:
            # Leave arguments curried
            function = self.function
            arg_str = "%s" % self.argument

        function_str = "%s" % function
        parenthesize_function = False
        if isinstance(function, LambdaExpression):
            if isinstance(function.term, ApplicationExpression):
                if not isinstance(function.term.function, AbstractVariableExpression):
                    parenthesize_function = True
            elif not isinstance(function.term, BooleanExpression):
                parenthesize_function = True
        elif isinstance(function, ApplicationExpression):
            parenthesize_function = True

        if parenthesize_function:
            function_str = Tokens.OPEN + function_str + Tokens.CLOSE

        return function_str + Tokens.OPEN + arg_str + Tokens.CLOSE

    def uncurry(self):
        """
        Uncurry this application expression

        return: A tuple (base-function, arg-list)
        """
        function = self.function
        args = [self.argument]
        while isinstance(function, ApplicationExpression):
            # (\x.\y.sees(x,y)(john))(mary)
            args.insert(0, function.argument)
            function = function.function
        return (function, args)

    @property
    def pred(self):
        """
        Return uncurried base-function.
        If this is an atom, then the result will be a variable expression.
        Otherwise, it will be a lambda expression.
        """
        return self.uncurry()[0]

    @property
    def args(self):
        """
        Return uncurried arg-list
        """
        return self.uncurry()[1]

    def is_atom(self):
        """
        Is this expression an atom (as opposed to a lambda expression applied
        to a term)?
        """
        return isinstance(self.pred, AbstractVariableExpression)


@total_ordering
class AbstractVariableExpression(Expression):
    """This class represents a variable to be used as a predicate or entity"""

    def __init__(self, variable):
        """
        :param variable: ``Variable``, for the variable
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        self.variable = variable

    def simplify(self):
        return self

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """:see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not an Variable" % variable
        assert isinstance(expression, Expression), (
            "%s is not an Expression" % expression
        )
        if self.variable == variable:
            return expression
        else:
            return self

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        resolution = other_type
        for varEx in signature[self.variable.name]:
            resolution = varEx.type.resolve(resolution)
            if not resolution:
                raise InconsistentTypeHierarchyException(self)

        signature[self.variable.name].append(self)
        for varEx in signature[self.variable.name]:
            varEx.type = resolution

    def findtype(self, variable):
        """:see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        if self.variable == variable:
            return self.type
        else:
            return ANY_TYPE

    def predicates(self):
        """:see: Expression.predicates()"""
        return set()

    def __eq__(self, other):
        """Allow equality between instances of ``AbstractVariableExpression``
        subtypes."""
        return (
            isinstance(other, AbstractVariableExpression)
            and self.variable == other.variable
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, AbstractVariableExpression):
            raise TypeError
        return self.variable < other.variable

    __hash__ = Expression.__hash__

    def __str__(self):
        return "%s" % self.variable


class IndividualVariableExpression(AbstractVariableExpression):
    """This class represents variables that take the form of a single lowercase
    character (other than 'e') followed by zero or more digits."""

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if not other_type.matches(ENTITY_TYPE):
            raise IllegalTypeException(self, other_type, ENTITY_TYPE)

        signature[self.variable.name].append(self)

    def _get_type(self):
        return ENTITY_TYPE

    type = property(_get_type, _set_type)

    def free(self):
        """:see: Expression.free()"""
        return {self.variable}

    def constants(self):
        """:see: Expression.constants()"""
        return set()


class FunctionVariableExpression(AbstractVariableExpression):
    """This class represents variables that take the form of a single uppercase
    character followed by zero or more digits."""

    type = ANY_TYPE

    def free(self):
        """:see: Expression.free()"""
        return {self.variable}

    def constants(self):
        """:see: Expression.constants()"""
        return set()


class EventVariableExpression(IndividualVariableExpression):
    """This class represents variables that take the form of a single lowercase
    'e' character followed by zero or more digits."""

    type = EVENT_TYPE


class ConstantExpression(AbstractVariableExpression):
    """This class represents variables that do not take the form of a single
    character followed by zero or more digits."""

    type = ENTITY_TYPE

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if other_type == ANY_TYPE:
            # entity type by default, for individuals
            resolution = ENTITY_TYPE
        else:
            resolution = other_type
            if self.type != ENTITY_TYPE:
                resolution = resolution.resolve(self.type)

        for varEx in signature[self.variable.name]:
            resolution = varEx.type.resolve(resolution)
            if not resolution:
                raise InconsistentTypeHierarchyException(self)

        signature[self.variable.name].append(self)
        for varEx in signature[self.variable.name]:
            varEx.type = resolution

    def free(self):
        """:see: Expression.free()"""
        return set()

    def constants(self):
        """:see: Expression.constants()"""
        return {self.variable}


def VariableExpression(variable):
    """
    This is a factory method that instantiates and returns a subtype of
    ``AbstractVariableExpression`` appropriate for the given variable.
    """
    assert isinstance(variable, Variable), "%s is not a Variable" % variable
    if is_indvar(variable.name):
        return IndividualVariableExpression(variable)
    elif is_funcvar(variable.name):
        return FunctionVariableExpression(variable)
    elif is_eventvar(variable.name):
        return EventVariableExpression(variable)
    else:
        return ConstantExpression(variable)


class VariableBinderExpression(Expression):
    """This an abstract class for any Expression that binds a variable in an
    Expression.  This includes LambdaExpressions and Quantified Expressions"""

    def __init__(self, variable, term):
        """
        :param variable: ``Variable``, for the variable
        :param term: ``Expression``, for the term
        """
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(term, Expression), "%s is not an Expression" % term
        self.variable = variable
        self.term = term

    def replace(self, variable, expression, replace_bound=False, alpha_convert=True):
        """:see: Expression.replace()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        assert isinstance(expression, Expression), (
            "%s is not an Expression" % expression
        )
        # if the bound variable is the thing being replaced
        if self.variable == variable:
            if replace_bound:
                assert isinstance(expression, AbstractVariableExpression), (
                    "%s is not a AbstractVariableExpression" % expression
                )
                return self.__class__(
                    expression.variable,
                    self.term.replace(variable, expression, True, alpha_convert),
                )
            else:
                return self
        else:
            # if the bound variable appears in the expression, then it must
            # be alpha converted to avoid a conflict
            if alpha_convert and self.variable in expression.free():
                self = self.alpha_convert(unique_variable(pattern=self.variable))

            # replace in the term
            return self.__class__(
                self.variable,
                self.term.replace(variable, expression, replace_bound, alpha_convert),
            )

    def alpha_convert(self, newvar):
        """Rename all occurrences of the variable introduced by this variable
        binder in the expression to ``newvar``.
        :param newvar: ``Variable``, for the new variable
        """
        assert isinstance(newvar, Variable), "%s is not a Variable" % newvar
        return self.__class__(
            newvar, self.term.replace(self.variable, VariableExpression(newvar), True)
        )

    def free(self):
        """:see: Expression.free()"""
        return self.term.free() - {self.variable}

    def findtype(self, variable):
        """:see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        if variable == self.variable:
            return ANY_TYPE
        else:
            return self.term.findtype(variable)

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        return combinator([function(self.term)])

    def visit_structured(self, function, combinator):
        """:see: Expression.visit_structured()"""
        return combinator(self.variable, function(self.term))

    def __eq__(self, other):
        r"""Defines equality modulo alphabetic variance.  If we are comparing
        \x.M  and \y.N, then check equality of M and N[x/y]."""
        if isinstance(self, other.__class__) or isinstance(other, self.__class__):
            if self.variable == other.variable:
                return self.term == other.term
            else:
                # Comparing \x.M  and \y.N.  Relabel y in N with x and continue.
                varex = VariableExpression(self.variable)
                return self.term == other.term.replace(other.variable, varex)
        else:
            return False

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__


class LambdaExpression(VariableBinderExpression):
    @property
    def type(self):
        return ComplexType(self.term.findtype(self.variable), self.term.type)

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        self.term._set_type(other_type.second, signature)
        if not self.type.resolve(other_type):
            raise TypeResolutionException(self, other_type)

    def __str__(self):
        variables = [self.variable]
        term = self.term
        while term.__class__ == self.__class__:
            variables.append(term.variable)
            term = term.term
        return (
            Tokens.LAMBDA
            + " ".join("%s" % v for v in variables)
            + Tokens.DOT
            + "%s" % term
        )


class QuantifiedExpression(VariableBinderExpression):
    @property
    def type(self):
        return TRUTH_TYPE

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.term._set_type(TRUTH_TYPE, signature)

    def __str__(self):
        variables = [self.variable]
        term = self.term
        while term.__class__ == self.__class__:
            variables.append(term.variable)
            term = term.term
        return (
            self.getQuantifier()
            + " "
            + " ".join("%s" % v for v in variables)
            + Tokens.DOT
            + "%s" % term
        )


class ExistsExpression(QuantifiedExpression):
    def getQuantifier(self):
        return Tokens.EXISTS


class AllExpression(QuantifiedExpression):
    def getQuantifier(self):
        return Tokens.ALL


class IotaExpression(QuantifiedExpression):
    def getQuantifier(self):
        return Tokens.IOTA


class NegatedExpression(Expression):
    def __init__(self, term):
        assert isinstance(term, Expression), "%s is not an Expression" % term
        self.term = term

    @property
    def type(self):
        return TRUTH_TYPE

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.term._set_type(TRUTH_TYPE, signature)

    def findtype(self, variable):
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        return self.term.findtype(variable)

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        return combinator([function(self.term)])

    def negate(self):
        """:see: Expression.negate()"""
        return self.term

    def __eq__(self, other):
        return isinstance(other, NegatedExpression) and self.term == other.term

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__

    def __str__(self):
        return Tokens.NOT + "%s" % self.term


class BinaryExpression(Expression):
    def __init__(self, first, second):
        assert isinstance(first, Expression), "%s is not an Expression" % first
        assert isinstance(second, Expression), "%s is not an Expression" % second
        self.first = first
        self.second = second

    @property
    def type(self):
        return TRUTH_TYPE

    def findtype(self, variable):
        """:see Expression.findtype()"""
        assert isinstance(variable, Variable), "%s is not a Variable" % variable
        f = self.first.findtype(variable)
        s = self.second.findtype(variable)
        if f == s or s == ANY_TYPE:
            return f
        elif f == ANY_TYPE:
            return s
        else:
            return ANY_TYPE

    def visit(self, function, combinator):
        """:see: Expression.visit()"""
        return combinator([function(self.first), function(self.second)])

    def __eq__(self, other):
        return (
            (isinstance(self, other.__class__) or isinstance(other, self.__class__))
            and self.first == other.first
            and self.second == other.second
        )

    def __ne__(self, other):
        return not self == other

    __hash__ = Expression.__hash__

    def __str__(self):
        first = self._str_subex(self.first)
        second = self._str_subex(self.second)
        return Tokens.OPEN + first + " " + self.getOp() + " " + second + Tokens.CLOSE

    def _str_subex(self, subex):
        return "%s" % subex


class BooleanExpression(BinaryExpression):
    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.first._set_type(TRUTH_TYPE, signature)
        self.second._set_type(TRUTH_TYPE, signature)


class AndExpression(BooleanExpression):
    """This class represents conjunctions"""

    def getOp(self):
        return Tokens.AND

    def _str_subex(self, subex):
        s = "%s" % subex
        if isinstance(subex, AndExpression):
            return s[1:-1]
        return s


class OrExpression(BooleanExpression):
    """This class represents disjunctions"""

    def getOp(self):
        return Tokens.OR

    def _str_subex(self, subex):
        s = "%s" % subex
        if isinstance(subex, OrExpression):
            return s[1:-1]
        return s


class ImpExpression(BooleanExpression):
    """This class represents implications"""

    def getOp(self):
        return Tokens.IMP


class IffExpression(BooleanExpression):
    """This class represents biconditionals"""

    def getOp(self):
        return Tokens.IFF


class EqualityExpression(BinaryExpression):
    """This class represents equality expressions like "(x = y)"."""

    def _set_type(self, other_type=ANY_TYPE, signature=None):
        """:see Expression._set_type()"""
        assert isinstance(other_type, Type)

        if signature is None:
            signature = defaultdict(list)

        if not other_type.matches(TRUTH_TYPE):
            raise IllegalTypeException(self, other_type, TRUTH_TYPE)
        self.first._set_type(ENTITY_TYPE, signature)
        self.second._set_type(ENTITY_TYPE, signature)

    def getOp(self):
        return Tokens.EQ


### Utilities


class LogicalExpressionException(Exception):
    def __init__(self, index, message):
        self.index = index
        Exception.__init__(self, message)


class UnexpectedTokenException(LogicalExpressionException):
    def __init__(self, index, unexpected=None, expected=None, message=None):
        if unexpected and expected:
            msg = "Unexpected token: '%s'.  " "Expected token '%s'." % (
                unexpected,
                expected,
            )
        elif unexpected:
            msg = "Unexpected token: '%s'." % unexpected
            if message:
                msg += "  " + message
        else:
            msg = "Expected token '%s'." % expected
        LogicalExpressionException.__init__(self, index, msg)


class ExpectedMoreTokensException(LogicalExpressionException):
    def __init__(self, index, message=None):
        if not message:
            message = "More tokens expected."
        LogicalExpressionException.__init__(
            self, index, "End of input found.  " + message
        )


def is_indvar(expr):
    """
    An individual variable must be a single lowercase character other than 'e',
    followed by zero or more digits.

    :param expr: str
    :return: bool True if expr is of the correct form
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r"^[a-df-z]\d*$", expr) is not None


def is_funcvar(expr):
    """
    A function variable must be a single uppercase character followed by
    zero or more digits.

    :param expr: str
    :return: bool True if expr is of the correct form
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r"^[A-Z]\d*$", expr) is not None


def is_eventvar(expr):
    """
    An event variable must be a single lowercase 'e' character followed by
    zero or more digits.

    :param expr: str
    :return: bool True if expr is of the correct form
    """
    assert isinstance(expr, str), "%s is not a string" % expr
    return re.match(r"^e\d*$", expr) is not None


def demo():
    lexpr = Expression.fromstring
    print("=" * 20 + "Test reader" + "=" * 20)
    print(lexpr(r"john"))
    print(lexpr(r"man(x)"))
    print(lexpr(r"-man(x)"))
    print(lexpr(r"(man(x) & tall(x) & walks(x))"))
    print(lexpr(r"exists x.(man(x) & tall(x) & walks(x))"))
    print(lexpr(r"\x.man(x)"))
    print(lexpr(r"\x.man(x)(john)"))
    print(lexpr(r"\x y.sees(x,y)"))
    print(lexpr(r"\x y.sees(x,y)(a,b)"))
    print(lexpr(r"(\x.exists y.walks(x,y))(x)"))
    print(lexpr(r"exists x.x = y"))
    print(lexpr(r"exists x.(x = y)"))
    print(lexpr("P(x) & x=y & P(y)"))
    print(lexpr(r"\P Q.exists x.(P(x) & Q(x))"))
    print(lexpr(r"man(x) <-> tall(x)"))

    print("=" * 20 + "Test simplify" + "=" * 20)
    print(lexpr(r"\x.\y.sees(x,y)(john)(mary)").simplify())
    print(lexpr(r"\x.\y.sees(x,y)(john, mary)").simplify())
    print(lexpr(r"all x.(man(x) & (\x.exists y.walks(x,y))(x))").simplify())
    print(lexpr(r"(\P.\Q.exists x.(P(x) & Q(x)))(\x.dog(x))(\x.bark(x))").simplify())

    print("=" * 20 + "Test alpha conversion and binder expression equality" + "=" * 20)
    e1 = lexpr("exists x.P(x)")
    print(e1)
    e2 = e1.alpha_convert(Variable("z"))
    print(e2)
    print(e1 == e2)


def demo_errors():
    print("=" * 20 + "Test reader errors" + "=" * 20)
    demoException("(P(x) & Q(x)")
    demoException("((P(x) &) & Q(x))")
    demoException("P(x) -> ")
    demoException("P(x")
    demoException("P(x,")
    demoException("P(x,)")
    demoException("exists")
    demoException("exists x.")
    demoException("\\")
    demoException("\\ x y.")
    demoException("P(x)Q(x)")
    demoException("(P(x)Q(x)")
    demoException("exists x -> y")


def demoException(s):
    try:
        Expression.fromstring(s)
    except LogicalExpressionException as e:
        print(f"{e.__class__.__name__}: {e}")


def printtype(ex):
    print(f"{ex.str()} : {ex.type}")


if __name__ == "__main__":
    demo()
#    demo_errors()

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\gemini\vertex_and_google_ai_studio_gemini.py ===
# What is this?
## httpx client for vertex ai calls
## Initial implementation - covers gemini + image gen calls
import json
import time
import uuid
from copy import deepcopy
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import httpx  # type: ignore

import litellm
import litellm.litellm_core_utils
import litellm.litellm_core_utils.litellm_logging
from litellm import verbose_logger
from litellm.constants import (
    DEFAULT_REASONING_EFFORT_DISABLE_THINKING_BUDGET,
    DEFAULT_REASONING_EFFORT_HIGH_THINKING_BUDGET,
    DEFAULT_REASONING_EFFORT_LOW_THINKING_BUDGET,
    DEFAULT_REASONING_EFFORT_MEDIUM_THINKING_BUDGET,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.llms.anthropic import AnthropicThinkingParam
from litellm.types.llms.gemini import BidiGenerateContentServerMessage
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionResponseMessage,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolParamFunctionChunk,
    OpenAIChatCompletionFinishReason,
)
from litellm.types.llms.vertex_ai import (
    VERTEX_CREDENTIALS_TYPES,
    Candidates,
    ContentType,
    FunctionCallingConfig,
    FunctionDeclaration,
    GeminiThinkingConfig,
    GenerateContentResponseBody,
    HttpxPartType,
    LogprobsResult,
    ToolConfig,
    Tools,
    UsageMetadata,
)
from litellm.types.utils import (
    ChatCompletionAudioResponse,
    ChatCompletionTokenLogprob,
    ChoiceLogprobs,
    CompletionTokensDetailsWrapper,
    PromptTokensDetailsWrapper,
    TopLogprob,
    Usage,
)
from litellm.utils import (
    CustomStreamWrapper,
    ModelResponse,
    is_base64_encoded,
    supports_reasoning,
)

from ....utils import _remove_additional_properties, _remove_strict_from_schema
from ..common_utils import VertexAIError, _build_vertex_schema
from ..vertex_llm_base import VertexBase
from .transformation import (
    _gemini_convert_messages_with_history,
    async_transform_request_body,
    sync_transform_request_body,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
    from litellm.types.utils import ModelResponseStream

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


class VertexAIBaseConfig:
    def get_mapped_special_auth_params(self) -> dict:
        """
        Common auth params across bedrock/vertex_ai/azure/watsonx
        """
        return {"project": "vertex_project", "region_name": "vertex_location"}

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        mapped_params = self.get_mapped_special_auth_params()

        for param, value in non_default_params.items():
            if param in mapped_params:
                optional_params[mapped_params[param]] = value
        return optional_params

    def get_eu_regions(self) -> List[str]:
        """
        Source: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#available-regions
        """
        return [
            "europe-central2",
            "europe-north1",
            "europe-southwest1",
            "europe-west1",
            "europe-west2",
            "europe-west3",
            "europe-west4",
            "europe-west6",
            "europe-west8",
            "europe-west9",
        ]

    def get_us_regions(self) -> List[str]:
        """
        Source: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#available-regions
        """
        return [
            "us-central1",
            "us-east1",
            "us-east4",
            "us-east5",
            "us-south1",
            "us-west1",
            "us-west4",
            "us-west5",
        ]


class VertexGeminiConfig(VertexAIBaseConfig, BaseConfig):
    """
    Reference: https://cloud.google.com/vertex-ai/docs/generative-ai/chat/test-chat-prompts
    Reference: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference

    The class `VertexAIConfig` provides configuration for the VertexAI's API interface. Below are the parameters:

    - `temperature` (float): This controls the degree of randomness in token selection.

    - `max_output_tokens` (integer): This sets the limitation for the maximum amount of token in the text output. In this case, the default value is 256.

    - `top_p` (float): The tokens are selected from the most probable to the least probable until the sum of their probabilities equals the `top_p` value. Default is 0.95.

    - `top_k` (integer): The value of `top_k` determines how many of the most probable tokens are considered in the selection. For example, a `top_k` of 1 means the selected token is the most probable among all tokens. The default value is 40.

    - `response_mime_type` (str): The MIME type of the response. The default value is 'text/plain'.

    - `candidate_count` (int): Number of generated responses to return.

    - `stop_sequences` (List[str]): The set of character sequences (up to 5) that will stop output generation. If specified, the API will stop at the first appearance of a stop sequence. The stop sequence will not be included as part of the response.

    - `frequency_penalty` (float): This parameter is used to penalize the model from repeating the same output. The default value is 0.0.

    - `presence_penalty` (float): This parameter is used to penalize the model from generating the same output as the input. The default value is 0.0.

    - `seed` (int): The seed value is used to help generate the same output for the same input. The default value is None.

    Note: Please make sure to modify the default parameters as required for your use case.
    """

    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    response_mime_type: Optional[str] = None
    candidate_count: Optional[int] = None
    stop_sequences: Optional[list] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    seed: Optional[int] = None

    def __init__(
        self,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        response_mime_type: Optional[str] = None,
        candidate_count: Optional[int] = None,
        stop_sequences: Optional[list] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str) -> List[str]:
        supported_params = [
            "temperature",
            "top_p",
            "max_tokens",
            "max_completion_tokens",
            "stream",
            "tools",
            "functions",
            "tool_choice",
            "response_format",
            "n",
            "stop",
            "frequency_penalty",
            "presence_penalty",
            "extra_headers",
            "seed",
            "logprobs",
            "top_logprobs",
            "modalities",
            "parallel_tool_calls",
            "web_search_options",
        ]
        if supports_reasoning(model):
            supported_params.append("reasoning_effort")
            supported_params.append("thinking")
        return supported_params

    def map_tool_choice_values(
        self, model: str, tool_choice: Union[str, dict]
    ) -> Optional[ToolConfig]:
        if tool_choice == "none":
            return ToolConfig(functionCallingConfig=FunctionCallingConfig(mode="NONE"))
        elif tool_choice == "required":
            return ToolConfig(functionCallingConfig=FunctionCallingConfig(mode="ANY"))
        elif tool_choice == "auto":
            return ToolConfig(functionCallingConfig=FunctionCallingConfig(mode="AUTO"))
        elif isinstance(tool_choice, dict):
            # only supported for anthropic + mistral models - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html
            name = tool_choice.get("function", {}).get("name", "")
            return ToolConfig(
                functionCallingConfig=FunctionCallingConfig(
                    mode="ANY", allowed_function_names=[name]
                )
            )
        else:
            raise litellm.utils.UnsupportedParamsError(
                message="VertexAI doesn't support tool_choice={}. Supported tool_choice values=['auto', 'required', json object]. To drop it from the call, set `litellm.drop_params = True.".format(
                    tool_choice
                ),
                status_code=400,
            )

    def _map_web_search_options(self, value: dict) -> Tools:
        """
        Base Case: empty dict

        Google doesn't support user_location or search_context_size params
        """
        return Tools(googleSearch={})

    def _map_function(self, value: List[dict]) -> List[Tools]:  # noqa: PLR0915
        gtool_func_declarations = []
        googleSearch: Optional[dict] = None
        googleSearchRetrieval: Optional[dict] = None
        enterpriseWebSearch: Optional[dict] = None
        urlContext: Optional[dict] = None
        code_execution: Optional[dict] = None
        # remove 'additionalProperties' from tools
        value = _remove_additional_properties(value)
        # remove 'strict' from tools
        value = _remove_strict_from_schema(value)

        def get_tool_value(tool: dict, tool_name: str) -> Optional[dict]:
            """
            Helper function to get tool value handling both camelCase and underscore_case variants

            Args:
                tool (dict): The tool dictionary
                tool_name (str): The base tool name (e.g. "codeExecution")

            Returns:
                Optional[dict]: The tool value if found, None otherwise
            """
            # Convert camelCase to underscore_case
            underscore_name = "".join(
                ["_" + c.lower() if c.isupper() else c for c in tool_name]
            ).lstrip("_")
            # Try both camelCase and underscore_case variants

            if tool.get(tool_name) is not None:
                return tool.get(tool_name)
            elif tool.get(underscore_name) is not None:
                return tool.get(underscore_name)
            else:
                return None

        for tool in value:
            openai_function_object: Optional[ChatCompletionToolParamFunctionChunk] = (
                None
            )
            if "function" in tool:  # tools list
                _openai_function_object = ChatCompletionToolParamFunctionChunk(  # type: ignore
                    **tool["function"]
                )

                if (
                    "parameters" in _openai_function_object
                    and _openai_function_object["parameters"] is not None
                    and isinstance(_openai_function_object["parameters"], dict)
                ):  # OPENAI accepts JSON Schema, Google accepts OpenAPI schema.
                    _openai_function_object["parameters"] = _build_vertex_schema(
                        _openai_function_object["parameters"]
                    )

                openai_function_object = _openai_function_object

            elif "name" in tool:  # functions list
                openai_function_object = ChatCompletionToolParamFunctionChunk(**tool)  # type: ignore

            tool_name = list(tool.keys())[0] if len(tool.keys()) == 1 else None
            if tool_name and (
                tool_name == "codeExecution" or tool_name == "code_execution"
            ):  # code_execution maintained for backwards compatibility
                code_execution = get_tool_value(tool, "codeExecution")
            elif tool_name and tool_name == "googleSearch":
                googleSearch = get_tool_value(tool, "googleSearch")
            elif tool_name and tool_name == "googleSearchRetrieval":
                googleSearchRetrieval = get_tool_value(tool, "googleSearchRetrieval")
            elif tool_name and tool_name == "enterpriseWebSearch":
                enterpriseWebSearch = get_tool_value(tool, "enterpriseWebSearch")
            elif tool_name and tool_name == "urlContext":
                urlContext = get_tool_value(tool, "urlContext")
            elif openai_function_object is not None:
                gtool_func_declaration = FunctionDeclaration(
                    name=openai_function_object["name"],
                )
                _description = openai_function_object.get("description", None)
                _parameters = openai_function_object.get("parameters", None)
                if isinstance(_parameters, str) and len(_parameters) == 0:
                    _parameters = {
                        "type": "object",
                    }
                if _description is not None:
                    gtool_func_declaration["description"] = _description
                if _parameters is not None:
                    gtool_func_declaration["parameters"] = _parameters
                gtool_func_declarations.append(gtool_func_declaration)
            else:
                # assume it's a provider-specific param
                verbose_logger.warning(
                    "Invalid tool={}. Use `litellm.set_verbose` or `litellm --detailed_debug` to see raw request."
                )

        _tools = Tools(
            function_declarations=gtool_func_declarations,
        )
        if googleSearch is not None:
            _tools["googleSearch"] = googleSearch
        if googleSearchRetrieval is not None:
            _tools["googleSearchRetrieval"] = googleSearchRetrieval
        if enterpriseWebSearch is not None:
            _tools["enterpriseWebSearch"] = enterpriseWebSearch
        if code_execution is not None:
            _tools["code_execution"] = code_execution
        if urlContext is not None:
            _tools["url_context"] = urlContext
        return [_tools]

    def _map_response_schema(self, value: dict) -> dict:
        old_schema = deepcopy(value)
        if isinstance(old_schema, list):
            for item in old_schema:
                if isinstance(item, dict):
                    item = _build_vertex_schema(
                        parameters=item, add_property_ordering=True
                    )

        elif isinstance(old_schema, dict):
            old_schema = _build_vertex_schema(
                parameters=old_schema, add_property_ordering=True
            )
        return old_schema

    def apply_response_schema_transformation(self, value: dict, optional_params: dict):
        new_value = deepcopy(value)
        # remove 'additionalProperties' from json schema
        new_value = _remove_additional_properties(new_value)
        # remove 'strict' from json schema
        new_value = _remove_strict_from_schema(new_value)
        if new_value["type"] == "json_object":
            optional_params["response_mime_type"] = "application/json"
        elif new_value["type"] == "text":
            optional_params["response_mime_type"] = "text/plain"
        if "response_schema" in new_value:
            optional_params["response_mime_type"] = "application/json"
            optional_params["response_schema"] = new_value["response_schema"]
        elif new_value["type"] == "json_schema":  # type: ignore
            if "json_schema" in new_value and "schema" in new_value["json_schema"]:  # type: ignore
                optional_params["response_mime_type"] = "application/json"
                optional_params["response_schema"] = new_value["json_schema"]["schema"]  # type: ignore

        if "response_schema" in optional_params and isinstance(
            optional_params["response_schema"], dict
        ):
            optional_params["response_schema"] = self._map_response_schema(
                value=optional_params["response_schema"]
            )

    @staticmethod
    def _map_reasoning_effort_to_thinking_budget(
        reasoning_effort: str,
    ) -> GeminiThinkingConfig:
        if reasoning_effort == "low":
            return {
                "thinkingBudget": DEFAULT_REASONING_EFFORT_LOW_THINKING_BUDGET,
                "includeThoughts": True,
            }
        elif reasoning_effort == "medium":
            return {
                "thinkingBudget": DEFAULT_REASONING_EFFORT_MEDIUM_THINKING_BUDGET,
                "includeThoughts": True,
            }
        elif reasoning_effort == "high":
            return {
                "thinkingBudget": DEFAULT_REASONING_EFFORT_HIGH_THINKING_BUDGET,
                "includeThoughts": True,
            }
        elif reasoning_effort == "disable":
            return {
                "thinkingBudget": DEFAULT_REASONING_EFFORT_DISABLE_THINKING_BUDGET,
                "includeThoughts": False,
            }
        else:
            raise ValueError(f"Invalid reasoning effort: {reasoning_effort}")

    @staticmethod
    def _is_thinking_budget_zero(thinking_budget: Optional[int]) -> bool:
        return thinking_budget is not None and thinking_budget == 0

    @staticmethod
    def _map_thinking_param(
        thinking_param: AnthropicThinkingParam,
    ) -> GeminiThinkingConfig:
        thinking_enabled = thinking_param.get("type") == "enabled"
        thinking_budget = thinking_param.get("budget_tokens")

        params: GeminiThinkingConfig = {}
        if thinking_enabled and not VertexGeminiConfig._is_thinking_budget_zero(
            thinking_budget
        ):
            params["includeThoughts"] = True
        if thinking_budget is not None and isinstance(thinking_budget, int):
            params["thinkingBudget"] = thinking_budget

        return params

    def map_response_modalities(self, value: list) -> list:
        response_modalities = []
        for modality in value:
            if modality == "text":
                response_modalities.append("TEXT")
            elif modality == "image":
                response_modalities.append("IMAGE")
            elif modality == "audio":
                response_modalities.append("AUDIO")
            else:
                response_modalities.append("MODALITY_UNSPECIFIED")
        return response_modalities

    def validate_parallel_tool_calls(self, value: bool, non_default_params: dict):
        tools = non_default_params.get("tools", non_default_params.get("functions"))
        num_function_declarations = len(tools) if isinstance(tools, list) else 0
        if num_function_declarations > 1:
            raise litellm.utils.UnsupportedParamsError(
                message=(
                    "`parallel_tool_calls=False` is not supported by Gemini when multiple tools are "
                    "provided. Specify a single tool, or set "
                    "`parallel_tool_calls=True`. If you want to drop this param, set `litellm.drop_params = True` or pass in `(.., drop_params=True)` in the requst - https://docs.litellm.ai/docs/completion/drop_params"
                ),
                status_code=400,
            )

    def _map_audio_params(self, value: dict) -> dict:
        """
        Expected input:
        {
            "voice": "alloy",
            "format": "mp3",
        }

        Expected output:
        speechConfig = {
            voiceConfig: {
                prebuiltVoiceConfig: {
                    voiceName: "alloy",
                }
            }
        }
        """
        from litellm.types.llms.vertex_ai import (
            PrebuiltVoiceConfig,
            SpeechConfig,
            VoiceConfig,
        )

        # Validate audio format - Gemini TTS only supports pcm16
        audio_format = value.get("format")
        if audio_format is not None and audio_format != "pcm16":
            raise ValueError(
                f"Unsupported audio format for Gemini TTS models: {audio_format}. "
                f"Gemini TTS models only support 'pcm16' format as they return audio data in L16 PCM format. "
                f"Please set audio format to 'pcm16'."
            )

        # Map OpenAI audio parameter to Gemini speech config
        speech_config: SpeechConfig = {}

        if "voice" in value:
            prebuilt_voice_config: PrebuiltVoiceConfig = {"voiceName": value["voice"]}
            voice_config: VoiceConfig = {"prebuiltVoiceConfig": prebuilt_voice_config}
            speech_config["voiceConfig"] = voice_config

        return cast(dict, speech_config)

    def map_openai_params(  # noqa: PLR0915
        self,
        non_default_params: Dict,
        optional_params: Dict,
        model: str,
        drop_params: bool,
    ) -> Dict:
        for param, value in non_default_params.items():
            if param == "temperature":
                optional_params["temperature"] = value
            elif param == "top_p":
                optional_params["top_p"] = value
            elif (
                param == "stream" and value is True
            ):  # sending stream = False, can cause it to get passed unchecked and raise issues
                optional_params["stream"] = value
            elif param == "n":
                optional_params["candidate_count"] = value
            elif param == "audio" and isinstance(value, dict):
                optional_params["speechConfig"] = self._map_audio_params(value)
            elif param == "stop":
                if isinstance(value, str):
                    optional_params["stop_sequences"] = [value]
                elif isinstance(value, list):
                    optional_params["stop_sequences"] = value
            elif param == "max_tokens" or param == "max_completion_tokens":
                optional_params["max_output_tokens"] = value
            elif param == "response_format" and isinstance(value, dict):  # type: ignore
                self.apply_response_schema_transformation(
                    value=value, optional_params=optional_params
                )
            elif param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            elif param == "presence_penalty":
                optional_params["presence_penalty"] = value
            elif param == "logprobs":
                optional_params["responseLogprobs"] = value
            elif param == "top_logprobs":
                optional_params["logprobs"] = value
            elif (
                (param == "tools" or param == "functions")
                and isinstance(value, list)
                and value
            ):
                optional_params = self._add_tools_to_optional_params(
                    optional_params, self._map_function(value=value)
                )
            elif param == "tool_choice" and (
                isinstance(value, str) or isinstance(value, dict)
            ):
                _tool_choice_value = self.map_tool_choice_values(
                    model=model, tool_choice=value  # type: ignore
                )
                if _tool_choice_value is not None:
                    optional_params["tool_choice"] = _tool_choice_value
            elif param == "parallel_tool_calls":
                if value is False and not (
                    drop_params or litellm.drop_params
                ):  # if drop params is True, then we should just ignore this
                    self.validate_parallel_tool_calls(value, non_default_params)
                else:
                    optional_params["parallel_tool_calls"] = value
            elif param == "seed":
                optional_params["seed"] = value
            elif param == "reasoning_effort" and isinstance(value, str):
                optional_params["thinkingConfig"] = (
                    VertexGeminiConfig._map_reasoning_effort_to_thinking_budget(value)
                )
            elif param == "thinking":
                optional_params["thinkingConfig"] = (
                    VertexGeminiConfig._map_thinking_param(
                        cast(AnthropicThinkingParam, value)
                    )
                )
            elif param == "modalities" and isinstance(value, list):
                response_modalities = self.map_response_modalities(value)
                optional_params["responseModalities"] = response_modalities
            elif param == "web_search_options" and value and isinstance(value, dict):
                _tools = self._map_web_search_options(value)
                optional_params = self._add_tools_to_optional_params(
                    optional_params, [_tools]
                )
        if litellm.vertex_ai_safety_settings is not None:
            optional_params["safety_settings"] = litellm.vertex_ai_safety_settings

        # if audio param is set, ensure responseModalities is set to AUDIO
        audio_param = optional_params.get("speechConfig")
        if audio_param is not None:
            if "responseModalities" not in optional_params:
                optional_params["responseModalities"] = ["AUDIO"]
            elif "AUDIO" not in optional_params["responseModalities"]:
                optional_params["responseModalities"].append("AUDIO")

        return optional_params

    def get_mapped_special_auth_params(self) -> dict:
        """
        Common auth params across bedrock/vertex_ai/azure/watsonx
        """
        return {"project": "vertex_project", "region_name": "vertex_location"}

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        mapped_params = self.get_mapped_special_auth_params()

        for param, value in non_default_params.items():
            if param in mapped_params:
                optional_params[mapped_params[param]] = value
        return optional_params

    def get_eu_regions(self) -> List[str]:
        """
        Source: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#available-regions
        """
        return [
            "europe-central2",
            "europe-north1",
            "europe-southwest1",
            "europe-west1",
            "europe-west2",
            "europe-west3",
            "europe-west4",
            "europe-west6",
            "europe-west8",
            "europe-west9",
        ]

    @staticmethod
    def get_model_for_vertex_ai_url(model: str) -> str:
        """
        Returns the model name to use in the request to Vertex AI

        Handles 2 cases:
        1. User passed `model="vertex_ai/gemini/ft-uuid"`, we need to return `ft-uuid` for the request to Vertex AI
        2. User passed `model="vertex_ai/gemini-2.0-flash-001"`, we need to return `gemini-2.0-flash-001` for the request to Vertex AI

        Args:
            model (str): The model name to use in the request to Vertex AI

        Returns:
            str: The model name to use in the request to Vertex AI
        """
        if VertexGeminiConfig._is_model_gemini_spec_model(model):
            return VertexGeminiConfig._get_model_name_from_gemini_spec_model(model)
        return model

    @staticmethod
    def _is_model_gemini_spec_model(model: Optional[str]) -> bool:
        """
        Returns true if user is trying to call custom model in `/gemini` request/response format
        """
        if model is None:
            return False
        if "gemini/" in model:
            return True
        return False

    @staticmethod
    def _get_model_name_from_gemini_spec_model(model: str) -> str:
        """
        Returns the model name if model="vertex_ai/gemini/<unique_id>"

        Example:
        - model = "gemini/1234567890"
        - returns "1234567890"
        """
        if "gemini/" in model:
            return model.split("/")[-1]
        return model

    def get_flagged_finish_reasons(self) -> Dict[str, str]:
        """
        Return Dictionary of finish reasons which indicate response was flagged

        and what it means
        """
        return {
            "SAFETY": "The token generation was stopped as the response was flagged for safety reasons. NOTE: When streaming the Candidate.content will be empty if content filters blocked the output.",
            "RECITATION": "The token generation was stopped as the response was flagged for unauthorized citations.",
            "BLOCKLIST": "The token generation was stopped as the response was flagged for the terms which are included from the terminology blocklist.",
            "PROHIBITED_CONTENT": "The token generation was stopped as the response was flagged for the prohibited contents.",
            "SPII": "The token generation was stopped as the response was flagged for Sensitive Personally Identifiable Information (SPII) contents.",
            "IMAGE_SAFETY": "The token generation was stopped as the response was flagged for image safety reasons.",
        }

    @staticmethod
    def get_finish_reason_mapping() -> Dict[str, OpenAIChatCompletionFinishReason]:
        """
        Return Dictionary of finish reasons which indicate response was flagged

        and what it means
        """
        return {
            "FINISH_REASON_UNSPECIFIED": "stop",  # openai doesn't have a way of representing this
            "STOP": "stop",
            "MAX_TOKENS": "length",
            "SAFETY": "content_filter",
            "RECITATION": "content_filter",
            "LANGUAGE": "content_filter",
            "OTHER": "content_filter",
            "BLOCKLIST": "content_filter",
            "PROHIBITED_CONTENT": "content_filter",
            "SPII": "content_filter",
            "MALFORMED_FUNCTION_CALL": "stop",  # openai doesn't have a way of representing this
            "IMAGE_SAFETY": "content_filter",
        }

    def translate_exception_str(self, exception_string: str):
        if (
            "GenerateContentRequest.tools[0].function_declarations[0].parameters.properties: should be non-empty for OBJECT type"
            in exception_string
        ):
            return "'properties' field in tools[0]['function']['parameters'] cannot be empty if 'type' == 'object'. Received error from provider - {}".format(
                exception_string
            )
        return exception_string

    def get_assistant_content_message(
        self, parts: List[HttpxPartType]
    ) -> Tuple[Optional[str], Optional[str]]:
        content_str: Optional[str] = None
        reasoning_content_str: Optional[str] = None

        for part in parts:
            _content_str = ""
            if "text" in part:
                text_content = part["text"]
                # Check if text content is audio data URI - if so, exclude from text content
                if text_content.startswith("data:audio") and ";base64," in text_content:
                    try:
                        if is_base64_encoded(text_content):
                            media_type, _ = text_content.split("data:")[1].split(
                                ";base64,"
                            )
                            if media_type.startswith("audio/"):
                                continue
                    except (ValueError, IndexError):
                        # If parsing fails, treat as regular text
                        pass
                _content_str += text_content
            elif "inlineData" in part:
                mime_type = part["inlineData"]["mimeType"]
                data = part["inlineData"]["data"]
                # Check if inline data is audio - if so, exclude from text content
                if mime_type.startswith("audio/"):
                    continue
                _content_str += "data:{};base64,{}".format(mime_type, data)

            if len(_content_str) > 0:
                if part.get("thought") is True:
                    if reasoning_content_str is None:
                        reasoning_content_str = ""
                    reasoning_content_str += _content_str
                else:
                    if content_str is None:
                        content_str = ""
                    content_str += _content_str

        return content_str, reasoning_content_str

    def _extract_audio_response_from_parts(
        self, parts: List[HttpxPartType]
    ) -> Optional[ChatCompletionAudioResponse]:
        """Extract audio response from parts if present"""
        for part in parts:
            if "text" in part:
                text_content = part["text"]
                # Check if text content contains audio data URI
                if text_content.startswith("data:audio") and ";base64," in text_content:
                    try:
                        if is_base64_encoded(text_content):
                            media_type, audio_data = text_content.split("data:")[
                                1
                            ].split(";base64,")

                            if media_type.startswith("audio/"):
                                expires_at = int(time.time()) + (24 * 60 * 60)
                                transcript = ""  # Gemini doesn't provide transcript

                                return ChatCompletionAudioResponse(
                                    data=audio_data,
                                    expires_at=expires_at,
                                    transcript=transcript,
                                )
                    except (ValueError, IndexError):
                        pass

            elif "inlineData" in part:
                mime_type = part["inlineData"]["mimeType"]
                data = part["inlineData"]["data"]

                if mime_type.startswith("audio/"):
                    expires_at = int(time.time()) + (24 * 60 * 60)
                    transcript = ""  # Gemini doesn't provide transcript

                    return ChatCompletionAudioResponse(
                        data=data, expires_at=expires_at, transcript=transcript
                    )

        return None

    @staticmethod
    def _transform_parts(
        parts: List[HttpxPartType],
        is_function_call: Optional[bool],
    ) -> Tuple[
        Optional[ChatCompletionToolCallFunctionChunk],
        Optional[List[ChatCompletionToolCallChunk]],
    ]:
        function: Optional[ChatCompletionToolCallFunctionChunk] = None
        _tools: List[ChatCompletionToolCallChunk] = []
        # in a single chunk, each tool call appears as a separate part
        # they need to be separate indexes as they are separate tool calls
        funcCallIndex = 0
        for part in parts:
            if "functionCall" in part:
                _function_chunk = ChatCompletionToolCallFunctionChunk(
                    name=part["functionCall"]["name"],
                    arguments=json.dumps(part["functionCall"]["args"]),
                )
                if is_function_call is True:
                    function = _function_chunk
                else:
                    _tool_response_chunk = ChatCompletionToolCallChunk(
                        id=f"call_{str(uuid.uuid4())}",
                        type="function",
                        function=_function_chunk,
                        index=funcCallIndex,
                    )
                    _tools.append(_tool_response_chunk)
                funcCallIndex += 1
        if len(_tools) == 0:
            tools: Optional[List[ChatCompletionToolCallChunk]] = None
        else:
            tools = _tools
        return function, tools

    @staticmethod
    def _transform_logprobs(
        logprobs_result: Optional[LogprobsResult],
    ) -> Optional[ChoiceLogprobs]:
        if logprobs_result is None:
            return None
        if "chosenCandidates" not in logprobs_result:
            return None
        logprobs_list: List[ChatCompletionTokenLogprob] = []
        for index, candidate in enumerate(logprobs_result["chosenCandidates"]):
            top_logprobs: List[TopLogprob] = []
            if "topCandidates" in logprobs_result and index < len(
                logprobs_result["topCandidates"]
            ):
                top_candidates_for_index = logprobs_result["topCandidates"][index][
                    "candidates"
                ]

                for options in top_candidates_for_index:
                    top_logprobs.append(
                        TopLogprob(
                            token=options["token"], logprob=options["logProbability"]
                        )
                    )
            logprobs_list.append(
                ChatCompletionTokenLogprob(
                    token=candidate["token"],
                    logprob=candidate["logProbability"],
                    top_logprobs=top_logprobs,
                )
            )
        return ChoiceLogprobs(content=logprobs_list)

    def _handle_blocked_response(
        self,
        model_response: ModelResponse,
        completion_response: GenerateContentResponseBody,
    ) -> ModelResponse:
        # If set, the prompt was blocked and no candidates are returned. Rephrase your prompt
        model_response.choices[0].finish_reason = "content_filter"

        chat_completion_message: ChatCompletionResponseMessage = {
            "role": "assistant",
            "content": None,
        }

        choice = litellm.Choices(
            finish_reason="content_filter",
            index=0,
            message=chat_completion_message,  # type: ignore
            logprobs=None,
            enhancements=None,
        )

        model_response.choices = [choice]

        ## GET USAGE ##
        usage = Usage(
            prompt_tokens=completion_response["usageMetadata"].get(
                "promptTokenCount", 0
            ),
            completion_tokens=completion_response["usageMetadata"].get(
                "candidatesTokenCount", 0
            ),
            total_tokens=completion_response["usageMetadata"].get("totalTokenCount", 0),
        )

        setattr(model_response, "usage", usage)

        return model_response

    def _handle_content_policy_violation(
        self,
        model_response: ModelResponse,
        completion_response: GenerateContentResponseBody,
    ) -> ModelResponse:
        ## CONTENT POLICY VIOLATION ERROR
        model_response.choices[0].finish_reason = "content_filter"

        _chat_completion_message = {
            "role": "assistant",
            "content": None,
        }

        choice = litellm.Choices(
            finish_reason="content_filter",
            index=0,
            message=_chat_completion_message,
            logprobs=None,
            enhancements=None,
        )

        model_response.choices = [choice]

        ## GET USAGE ##
        usage = Usage(
            prompt_tokens=completion_response["usageMetadata"].get(
                "promptTokenCount", 0
            ),
            completion_tokens=completion_response["usageMetadata"].get(
                "candidatesTokenCount", 0
            ),
            total_tokens=completion_response["usageMetadata"].get("totalTokenCount", 0),
        )

        setattr(model_response, "usage", usage)

        return model_response

    @staticmethod
    def is_candidate_token_count_inclusive(usage_metadata: UsageMetadata) -> bool:
        """
        Check if the candidate token count is inclusive of the thinking token count

        if prompttokencount + candidatesTokenCount == totalTokenCount, then the candidate token count is inclusive of the thinking token count

        else the candidate token count is exclusive of the thinking token count

        Addresses - https://github.com/BerriAI/litellm/pull/10141#discussion_r2052272035
        """
        if usage_metadata.get("promptTokenCount", 0) + usage_metadata.get(
            "candidatesTokenCount", 0
        ) == usage_metadata.get("totalTokenCount", 0):
            return True
        else:
            return False

    @staticmethod
    def _calculate_usage(
        completion_response: Union[
            GenerateContentResponseBody, BidiGenerateContentServerMessage
        ],
    ) -> Usage:
        if (
            completion_response is not None
            and "usageMetadata" not in completion_response
        ):
            raise ValueError(
                f"usageMetadata not found in completion_response. Got={completion_response}"
            )
        cached_tokens: Optional[int] = None
        audio_tokens: Optional[int] = None
        text_tokens: Optional[int] = None
        prompt_tokens_details: Optional[PromptTokensDetailsWrapper] = None
        reasoning_tokens: Optional[int] = None
        response_tokens: Optional[int] = None
        response_tokens_details: Optional[CompletionTokensDetailsWrapper] = None
        usage_metadata = completion_response["usageMetadata"]
        if "cachedContentTokenCount" in usage_metadata:
            cached_tokens = usage_metadata["cachedContentTokenCount"]

        ## GEMINI LIVE API ONLY PARAMS ##
        if "responseTokenCount" in usage_metadata:
            response_tokens = usage_metadata["responseTokenCount"]
        if "responseTokensDetails" in usage_metadata:
            response_tokens_details = CompletionTokensDetailsWrapper()
            for detail in usage_metadata["responseTokensDetails"]:
                if detail["modality"] == "TEXT":
                    response_tokens_details.text_tokens = detail.get("tokenCount", 0)
                elif detail["modality"] == "AUDIO":
                    response_tokens_details.audio_tokens = detail.get("tokenCount", 0)
        #########################################################

        if "promptTokensDetails" in usage_metadata:
            for detail in usage_metadata["promptTokensDetails"]:
                if detail["modality"] == "AUDIO":
                    audio_tokens = detail.get("tokenCount", 0)
                elif detail["modality"] == "TEXT":
                    text_tokens = detail.get("tokenCount", 0)
        if "thoughtsTokenCount" in usage_metadata:
            reasoning_tokens = usage_metadata["thoughtsTokenCount"]
        prompt_tokens_details = PromptTokensDetailsWrapper(
            cached_tokens=cached_tokens,
            audio_tokens=audio_tokens,
            text_tokens=text_tokens,
        )

        completion_tokens = response_tokens or completion_response["usageMetadata"].get(
            "candidatesTokenCount", 0
        )
        if (
            not VertexGeminiConfig.is_candidate_token_count_inclusive(usage_metadata)
            and reasoning_tokens
        ):
            completion_tokens = reasoning_tokens + completion_tokens
        ## GET USAGE ##
        usage = Usage(
            prompt_tokens=usage_metadata.get("promptTokenCount", 0),
            completion_tokens=completion_tokens,
            total_tokens=usage_metadata.get("totalTokenCount", 0),
            prompt_tokens_details=prompt_tokens_details,
            reasoning_tokens=reasoning_tokens,
            completion_tokens_details=response_tokens_details,
        )

        return usage

    @staticmethod
    def _check_finish_reason(
        chat_completion_message: Optional[ChatCompletionResponseMessage],
        finish_reason: Optional[str],
    ) -> OpenAIChatCompletionFinishReason:
        mapped_finish_reason = VertexGeminiConfig.get_finish_reason_mapping()
        if chat_completion_message and chat_completion_message.get("function_call"):
            return "function_call"
        elif chat_completion_message and chat_completion_message.get("tool_calls"):
            return "tool_calls"
        elif (
            finish_reason and finish_reason in mapped_finish_reason.keys()
        ):  # vertex ai
            return mapped_finish_reason[finish_reason]
        else:
            return "stop"

    @staticmethod
    def _calculate_web_search_requests(grounding_metadata: List[dict]) -> Optional[int]:
        web_search_requests: Optional[int] = None

        if (
            grounding_metadata
            and isinstance(grounding_metadata, list)
            and len(grounding_metadata) > 0
        ):
            for grounding_metadata_item in grounding_metadata:
                web_search_queries = grounding_metadata_item.get("webSearchQueries")
                if web_search_queries and web_search_requests:
                    web_search_requests += len(web_search_queries)
                elif web_search_queries:
                    web_search_requests = len(grounding_metadata)
        return web_search_requests

    @staticmethod
    def _process_candidates(
        _candidates: List[Candidates],
        model_response: Union[ModelResponse, "ModelResponseStream"],
        standard_optional_params: dict,
    ) -> Tuple[List[dict], List[dict], List, List]:
        """
        Helper method to process candidates and extract metadata

        Returns:
            grounding_metadata: List[dict]
            url_context_metadata: List[dict]
            safety_ratings: List
            citation_metadata: List
        """
        from litellm.litellm_core_utils.prompt_templates.common_utils import (
            is_function_call,
        )
        from litellm.types.utils import ModelResponseStream

        grounding_metadata: List[dict] = []
        url_context_metadata: List[dict] = []
        safety_ratings: List = []
        citation_metadata: List = []
        chat_completion_message: ChatCompletionResponseMessage = {"role": "assistant"}
        chat_completion_logprobs: Optional[ChoiceLogprobs] = None
        tools: Optional[List[ChatCompletionToolCallChunk]] = []
        functions: Optional[ChatCompletionToolCallFunctionChunk] = None

        for idx, candidate in enumerate(_candidates):
            if "content" not in candidate:
                continue

            if "groundingMetadata" in candidate:
                if isinstance(candidate["groundingMetadata"], list):
                    grounding_metadata.extend(candidate["groundingMetadata"])  # type: ignore
                else:
                    grounding_metadata.append(candidate["groundingMetadata"])  # type: ignore

            if "safetyRatings" in candidate:
                safety_ratings.append(candidate["safetyRatings"])

            if "citationMetadata" in candidate:
                citation_metadata.append(candidate["citationMetadata"])

            if "urlContextMetadata" in candidate:
                # Add URL context metadata to grounding metadata
                url_context_metadata.append(cast(dict, candidate["urlContextMetadata"]))

            if "parts" in candidate["content"]:
                (
                    content,
                    reasoning_content,
                ) = VertexGeminiConfig().get_assistant_content_message(
                    parts=candidate["content"]["parts"]
                )

                audio_response = (
                    VertexGeminiConfig()._extract_audio_response_from_parts(
                        parts=candidate["content"]["parts"]
                    )
                )

                if audio_response is not None:
                    cast(Dict[str, Any], chat_completion_message)[
                        "audio"
                    ] = audio_response
                    chat_completion_message["content"] = None  # OpenAI spec
                elif content is not None:
                    chat_completion_message["content"] = content

                if reasoning_content is not None:
                    chat_completion_message["reasoning_content"] = reasoning_content

                functions, tools = VertexGeminiConfig._transform_parts(
                    parts=candidate["content"]["parts"],
                    is_function_call=is_function_call(standard_optional_params),
                )

            if "logprobsResult" in candidate:
                chat_completion_logprobs = VertexGeminiConfig._transform_logprobs(
                    logprobs_result=candidate["logprobsResult"]
                )

            if tools:
                chat_completion_message["tool_calls"] = tools

            if functions is not None:
                chat_completion_message["function_call"] = functions

            if isinstance(model_response, ModelResponseStream):
                from litellm.types.utils import Delta, StreamingChoices

                # create a streaming choice object
                choice = StreamingChoices(
                    finish_reason=VertexGeminiConfig._check_finish_reason(
                        chat_completion_message, candidate.get("finishReason")
                    ),
                    index=candidate.get("index", idx),
                    delta=Delta(
                        content=chat_completion_message.get("content"),
                        reasoning_content=chat_completion_message.get(
                            "reasoning_content"
                        ),
                        tool_calls=tools,
                        function_call=functions,
                    ),
                    logprobs=chat_completion_logprobs,
                    enhancements=None,
                )
                model_response.choices.append(choice)
            elif isinstance(model_response, ModelResponse):
                choice = litellm.Choices(
                    finish_reason=VertexGeminiConfig._check_finish_reason(
                        chat_completion_message, candidate.get("finishReason")
                    ),
                    index=candidate.get("index", idx),
                    message=chat_completion_message,  # type: ignore
                    logprobs=chat_completion_logprobs,
                    enhancements=None,
                )
                model_response.choices.append(choice)

        return (
            grounding_metadata,
            url_context_metadata,
            safety_ratings,
            citation_metadata,
        )

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = GenerateContentResponseBody(**raw_response.json())  # type: ignore
        except Exception as e:
            raise VertexAIError(
                message="Received={}, Error converting to valid response block={}. File an issue if litellm error - https://github.com/BerriAI/litellm/issues".format(
                    raw_response.text, str(e)
                ),
                status_code=422,
                headers=raw_response.headers,
            )

        ## GET MODEL ##
        model_response.model = model

        ## CHECK IF RESPONSE FLAGGED
        if (
            "promptFeedback" in completion_response
            and "blockReason" in completion_response["promptFeedback"]
        ):
            return self._handle_blocked_response(
                model_response=model_response,
                completion_response=completion_response,
            )

        _candidates = completion_response.get("candidates")
        if _candidates and len(_candidates) > 0:
            content_policy_violations = (
                VertexGeminiConfig().get_flagged_finish_reasons()
            )
            if (
                "finishReason" in _candidates[0]
                and _candidates[0]["finishReason"] in content_policy_violations.keys()
            ):
                return self._handle_content_policy_violation(
                    model_response=model_response,
                    completion_response=completion_response,
                )

        model_response.choices = []
        response_id = completion_response.get("responseId")
        if response_id:
            model_response.id = response_id
        url_context_metadata: List[dict] = []
        try:
            grounding_metadata: List[dict] = []
            safety_ratings: List[dict] = []
            citation_metadata: List[dict] = []
            if _candidates:
                (
                    grounding_metadata,
                    url_context_metadata,
                    safety_ratings,
                    citation_metadata,
                ) = VertexGeminiConfig._process_candidates(
                    _candidates, model_response, logging_obj.optional_params
                )

            usage = VertexGeminiConfig._calculate_usage(
                completion_response=completion_response
            )
            setattr(model_response, "usage", usage)

            ## ADD METADATA TO RESPONSE ##

            setattr(model_response, "vertex_ai_grounding_metadata", grounding_metadata)
            model_response._hidden_params["vertex_ai_grounding_metadata"] = (
                grounding_metadata
            )

            setattr(
                model_response, "vertex_ai_url_context_metadata", url_context_metadata
            )

            model_response._hidden_params["vertex_ai_url_context_metadata"] = (
                url_context_metadata
            )

            setattr(model_response, "vertex_ai_safety_results", safety_ratings)
            model_response._hidden_params["vertex_ai_safety_results"] = (
                safety_ratings  # older approach - maintaining to prevent regressions
            )

            ## ADD CITATION METADATA ##
            setattr(model_response, "vertex_ai_citation_metadata", citation_metadata)
            model_response._hidden_params["vertex_ai_citation_metadata"] = (
                citation_metadata  # older approach - maintaining to prevent regressions
            )

        except Exception as e:
            raise VertexAIError(
                message="Received={}, Error converting to valid response block={}. File an issue if litellm error - https://github.com/BerriAI/litellm/issues".format(
                    completion_response, str(e)
                ),
                status_code=422,
                headers=raw_response.headers,
            )

        return model_response

    def _transform_messages(
        self, messages: List[AllMessageValues]
    ) -> List[ContentType]:
        return _gemini_convert_messages_with_history(messages=messages)

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[Dict, httpx.Headers]
    ) -> BaseLLMException:
        return VertexAIError(
            message=error_message, status_code=status_code, headers=headers
        )

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        headers: Dict,
    ) -> Dict:
        raise NotImplementedError(
            "Vertex AI has a custom implementation of transform_request. Needs sync + async."
        )

    def validate_environment(
        self,
        headers: Optional[Dict],
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Dict:
        default_headers = {
            "Content-Type": "application/json",
        }
        if api_key is not None:
            default_headers["Authorization"] = f"Bearer {api_key}"
        if headers is not None:
            default_headers.update(headers)

        return default_headers


async def make_call(
    client: Optional[AsyncHTTPHandler],
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
):
    if client is None:
        client = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.VERTEX_AI,
        )

    try:
        response = await client.post(api_base, headers=headers, data=data, stream=True)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        exception_string = str(await e.response.aread())
        raise VertexAIError(
            status_code=e.response.status_code,
            message=VertexGeminiConfig().translate_exception_str(exception_string),
            headers=e.response.headers,
        )
    if response.status_code != 200 and response.status_code != 201:
        raise VertexAIError(
            status_code=response.status_code,
            message=response.text,
            headers=response.headers,
        )

    completion_stream = ModelResponseIterator(
        streaming_response=response.aiter_lines(),
        sync_stream=False,
        logging_obj=logging_obj,
    )
    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response="first stream response received",
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


def make_sync_call(
    client: Optional[HTTPHandler],  # module-level client
    gemini_client: Optional[HTTPHandler],  # if passed by user
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
):
    if gemini_client is not None:
        client = gemini_client
    if client is None:
        client = HTTPHandler()  # Create a new client if none provided

    response = client.post(api_base, headers=headers, data=data, stream=True)

    if response.status_code != 200 and response.status_code != 201:
        raise VertexAIError(
            status_code=response.status_code,
            message=str(response.read()),
            headers=response.headers,
        )

    completion_stream = ModelResponseIterator(
        streaming_response=response.iter_lines(),
        sync_stream=True,
        logging_obj=logging_obj,
    )

    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response="first stream response received",
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


class VertexLLM(VertexBase):
    def __init__(self) -> None:
        super().__init__()

    async def async_streaming(
        self,
        model: str,
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        data: dict,
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj,
        stream,
        optional_params: dict,
        litellm_params: dict,
        logger_fn=None,
        api_base: Optional[str] = None,
        client: Optional[AsyncHTTPHandler] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES] = None,
        gemini_api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> CustomStreamWrapper:
        request_body = await async_transform_request_body(**data)  # type: ignore

        should_use_v1beta1_features = self.is_using_v1beta1_features(
            optional_params=optional_params
        )

        _auth_header, vertex_project = await self._ensure_access_token_async(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )

        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=gemini_api_key,
            auth_header=_auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=stream,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=should_use_v1beta1_features,
        )

        headers = VertexGeminiConfig().validate_environment(
            api_key=auth_header,
            headers=extra_headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": request_body,
                "api_base": api_base,
                "headers": headers,
            },
        )

        request_body_str = json.dumps(request_body)
        streaming_response = CustomStreamWrapper(
            completion_stream=None,
            make_call=partial(
                make_call,
                client=client,
                api_base=api_base,
                headers=headers,
                data=request_body_str,
                model=model,
                messages=messages,
                logging_obj=logging_obj,
            ),
            model=model,
            custom_llm_provider="vertex_ai_beta",
            logging_obj=logging_obj,
        )
        return streaming_response

    async def async_completion(
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        data: dict,
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
        timeout: Optional[Union[float, httpx.Timeout]],
        encoding,
        logging_obj,
        stream,
        optional_params: dict,
        litellm_params: dict,
        logger_fn=None,
        api_base: Optional[str] = None,
        client: Optional[AsyncHTTPHandler] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES] = None,
        gemini_api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        should_use_v1beta1_features = self.is_using_v1beta1_features(
            optional_params=optional_params
        )

        _auth_header, vertex_project = await self._ensure_access_token_async(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )

        auth_header, api_base = self._get_token_and_url(
            model=model,
            gemini_api_key=gemini_api_key,
            auth_header=_auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=stream,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=should_use_v1beta1_features,
        )

        headers = VertexGeminiConfig().validate_environment(
            api_key=auth_header,
            headers=extra_headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        request_body = await async_transform_request_body(**data)  # type: ignore
        _async_client_params = {}
        if timeout:
            _async_client_params["timeout"] = timeout
        if client is None or not isinstance(client, AsyncHTTPHandler):
            client = get_async_httpx_client(
                params=_async_client_params, llm_provider=litellm.LlmProviders.VERTEX_AI
            )
        else:
            client = client  # type: ignore
        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": request_body,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await client.post(
                api_base, headers=headers, json=cast(dict, request_body)
            )  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(
                status_code=error_code,
                message=err.response.text,
                headers=err.response.headers,
            )
        except httpx.TimeoutException:
            raise VertexAIError(
                status_code=408,
                message="Timeout error occurred.",
                headers=None,
            )

        return VertexGeminiConfig().transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key="",
            request_data=cast(dict, request_body),
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
        )

    def completion(
        self,
        model: str,
        messages: list,
        model_response: ModelResponse,
        print_verbose: Callable,
        custom_llm_provider: Literal[
            "vertex_ai", "vertex_ai_beta", "gemini"
        ],  # if it's vertex_ai or gemini (google ai studio)
        encoding,
        logging_obj,
        optional_params: dict,
        acompletion: bool,
        timeout: Optional[Union[float, httpx.Timeout]],
        vertex_project: Optional[str],
        vertex_location: Optional[str],
        vertex_credentials: Optional[VERTEX_CREDENTIALS_TYPES],
        gemini_api_key: Optional[str],
        litellm_params: dict,
        logger_fn=None,
        extra_headers: Optional[dict] = None,
        client: Optional[Union[AsyncHTTPHandler, HTTPHandler]] = None,
        api_base: Optional[str] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        stream: Optional[bool] = optional_params.pop("stream", None)  # type: ignore

        transform_request_params = {
            "gemini_api_key": gemini_api_key,
            "messages": messages,
            "api_base": api_base,
            "model": model,
            "client": client,
            "timeout": timeout,
            "extra_headers": extra_headers,
            "optional_params": optional_params,
            "logging_obj": logging_obj,
            "custom_llm_provider": custom_llm_provider,
            "litellm_params": litellm_params,
        }

        ### ROUTING (ASYNC, STREAMING, SYNC)
        if acompletion:
            ### ASYNC STREAMING
            if stream is True:
                return self.async_streaming(
                    model=model,
                    messages=messages,
                    api_base=api_base,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=stream,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    timeout=timeout,
                    client=client,  # type: ignore
                    data=transform_request_params,
                    vertex_project=vertex_project,
                    vertex_location=vertex_location,
                    vertex_credentials=vertex_credentials,
                    gemini_api_key=gemini_api_key,
                    custom_llm_provider=custom_llm_provider,
                    extra_headers=extra_headers,
                )
            ### ASYNC COMPLETION
            return self.async_completion(
                model=model,
                messages=messages,
                data=transform_request_params,  # type: ignore
                api_base=api_base,
                model_response=model_response,
                print_verbose=print_verbose,
                encoding=encoding,
                logging_obj=logging_obj,
                optional_params=optional_params,
                stream=stream,
                litellm_params=litellm_params,
                logger_fn=logger_fn,
                timeout=timeout,
                client=client,  # type: ignore
                vertex_project=vertex_project,
                vertex_location=vertex_location,
                vertex_credentials=vertex_credentials,
                gemini_api_key=gemini_api_key,
                custom_llm_provider=custom_llm_provider,
                extra_headers=extra_headers,
            )

        should_use_v1beta1_features = self.is_using_v1beta1_features(
            optional_params=optional_params
        )

        _auth_header, vertex_project = self._ensure_access_token(
            credentials=vertex_credentials,
            project_id=vertex_project,
            custom_llm_provider=custom_llm_provider,
        )

        auth_header, url = self._get_token_and_url(
            model=model,
            gemini_api_key=gemini_api_key,
            auth_header=_auth_header,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            vertex_credentials=vertex_credentials,
            stream=stream,
            custom_llm_provider=custom_llm_provider,
            api_base=api_base,
            should_use_v1beta1_features=should_use_v1beta1_features,
        )
        headers = VertexGeminiConfig().validate_environment(
            api_key=auth_header,
            headers=extra_headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        ## TRANSFORMATION ##
        data = sync_transform_request_body(**transform_request_params)

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": url,
                "headers": headers,
            },
        )

        ## SYNC STREAMING CALL ##
        if stream is True:
            request_data_str = json.dumps(data)
            streaming_response = CustomStreamWrapper(
                completion_stream=None,
                make_call=partial(
                    make_sync_call,
                    gemini_client=(
                        client
                        if client is not None and isinstance(client, HTTPHandler)
                        else None
                    ),
                    api_base=url,
                    data=request_data_str,
                    model=model,
                    messages=messages,
                    logging_obj=logging_obj,
                    headers=headers,
                ),
                model=model,
                custom_llm_provider="vertex_ai_beta",
                logging_obj=logging_obj,
            )

            return streaming_response
        ## COMPLETION CALL ##

        if client is None or isinstance(client, AsyncHTTPHandler):
            _params = {}
            if timeout is not None:
                if isinstance(timeout, float) or isinstance(timeout, int):
                    timeout = httpx.Timeout(timeout)
                _params["timeout"] = timeout
            client = HTTPHandler(**_params)  # type: ignore
        else:
            client = client

        try:
            response = client.post(url=url, headers=headers, json=data)  # type: ignore
            response.raise_for_status()
        except httpx.HTTPStatusError as err:
            error_code = err.response.status_code
            raise VertexAIError(
                status_code=error_code,
                message=err.response.text,
                headers=err.response.headers,
            )
        except httpx.TimeoutException:
            raise VertexAIError(
                status_code=408,
                message="Timeout error occurred.",
                headers=None,
            )

        return VertexGeminiConfig().transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            optional_params=optional_params,
            litellm_params=litellm_params,
            api_key="",
            request_data=data,  # type: ignore
            messages=messages,
            encoding=encoding,
        )


class ModelResponseIterator:
    def __init__(
        self, streaming_response, sync_stream: bool, logging_obj: LoggingClass
    ):
        from litellm.litellm_core_utils.prompt_templates.common_utils import (
            check_is_function_call,
        )

        self.streaming_response = streaming_response
        self.chunk_type: Literal["valid_json", "accumulated_json"] = "valid_json"
        self.accumulated_json = ""
        self.sent_first_chunk = False
        self.logging_obj = logging_obj
        self.is_function_call = check_is_function_call(logging_obj)

    def chunk_parser(self, chunk: dict) -> Optional["ModelResponseStream"]:
        try:
            verbose_logger.debug(f"RAW GEMINI CHUNK: {chunk}")
            from litellm.types.utils import ModelResponseStream

            processed_chunk = GenerateContentResponseBody(**chunk)  # type: ignore
            response_id = processed_chunk.get("responseId")
            model_response = ModelResponseStream(choices=[], id=response_id)
            usage: Optional[Usage] = None
            _candidates: Optional[List[Candidates]] = processed_chunk.get("candidates")
            grounding_metadata: List[dict] = []
            url_context_metadata: List[dict] = []
            safety_ratings: List[dict] = []
            citation_metadata: List[dict] = []
            if _candidates:
                (
                    grounding_metadata,
                    url_context_metadata,
                    safety_ratings,
                    citation_metadata,
                ) = VertexGeminiConfig._process_candidates(
                    _candidates, model_response, self.logging_obj.optional_params
                )
                setattr(model_response, "vertex_ai_grounding_metadata", grounding_metadata)  # type: ignore
                setattr(model_response, "vertex_ai_url_context_metadata", url_context_metadata)  # type: ignore
                setattr(model_response, "vertex_ai_safety_ratings", safety_ratings)  # type: ignore
                setattr(model_response, "vertex_ai_citation_metadata", citation_metadata)  # type: ignore

            if "usageMetadata" in processed_chunk:
                usage = VertexGeminiConfig._calculate_usage(
                    completion_response=processed_chunk,
                )

                web_search_requests = VertexGeminiConfig._calculate_web_search_requests(
                    grounding_metadata
                )
                if web_search_requests is not None:
                    cast(
                        PromptTokensDetailsWrapper, usage.prompt_tokens_details
                    ).web_search_requests = web_search_requests

            setattr(model_response, "usage", usage)  # type: ignore

            model_response._hidden_params["is_finished"] = False
            return model_response

        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

    # Sync iterator
    def __iter__(self):
        self.response_iterator = self.streaming_response
        return self

    def handle_valid_json_chunk(self, chunk: str) -> Optional["ModelResponseStream"]:
        chunk = chunk.strip()
        try:
            json_chunk = json.loads(chunk)

        except json.JSONDecodeError as e:
            if (
                self.sent_first_chunk is False
            ):  # only check for accumulated json, on first chunk, else raise error. Prevent real errors from being masked.
                self.chunk_type = "accumulated_json"
                return self.handle_accumulated_json_chunk(chunk=chunk)
            raise e

        if self.sent_first_chunk is False:
            self.sent_first_chunk = True

        return self.chunk_parser(chunk=json_chunk)

    def handle_accumulated_json_chunk(
        self, chunk: str
    ) -> Optional["ModelResponseStream"]:
        chunk = litellm.CustomStreamWrapper._strip_sse_data_from_chunk(chunk) or ""
        message = chunk.replace("\n\n", "")

        # Accumulate JSON data
        self.accumulated_json += message

        # Try to parse the accumulated JSON
        try:
            _data = json.loads(self.accumulated_json)
            self.accumulated_json = ""  # reset after successful parsing
            return self.chunk_parser(chunk=_data)
        except json.JSONDecodeError:
            # If it's not valid JSON yet, continue to the next event
            return None

    def _common_chunk_parsing_logic(
        self, chunk: str
    ) -> Optional["ModelResponseStream"]:
        try:
            chunk = litellm.CustomStreamWrapper._strip_sse_data_from_chunk(chunk) or ""
            if len(chunk) > 0:
                """
                Check if initial chunk valid json
                - if partial json -> enter accumulated json logic
                - if valid - continue
                """
                if self.chunk_type == "valid_json":
                    return self.handle_valid_json_chunk(chunk=chunk)
                elif self.chunk_type == "accumulated_json":
                    return self.handle_accumulated_json_chunk(chunk=chunk)

            return None
        except Exception:
            raise

    def __next__(self):
        try:
            chunk = self.response_iterator.__next__()
        except StopIteration:
            if self.chunk_type == "accumulated_json" and self.accumulated_json:
                return self.handle_accumulated_json_chunk(chunk="")
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            return self._common_chunk_parsing_logic(chunk=chunk)
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

    # Async iterator
    def __aiter__(self):
        self.async_response_iterator = self.streaming_response.__aiter__()
        return self

    async def __anext__(self):
        try:
            chunk = await self.async_response_iterator.__anext__()
        except StopAsyncIteration:
            if self.chunk_type == "accumulated_json" and self.accumulated_json:
                return self.handle_accumulated_json_chunk(chunk="")
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            return self._common_chunk_parsing_logic(chunk=chunk)
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

# === NexusCore/src\sandbox_logs\repair_20250713_142257_original.py ===
def multiply(a, b): return a * b

# === NexusCore/src\sandbox_logs\repair_20250713_142312_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、対応するpytest形式のユニットテストを生成することができません。

# === NexusCore/src\sandbox_logs\repair_20250713_142329_original.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、対応するpytest形式のユニットテストを生成することができません。

# === NexusCore/src\sandbox_logs\repair_20250713_173707_original.py ===
def multiply(a, b): return a * b

# === NexusCore/src\sandbox_logs\repair_20250713_213549_fixed.py ===
# Sorry, but the test target Python code is not provided, so we cannot generate a specific pytest style unit test. However, we will show a general format below.

# === NexusCore/openenv\Lib\site-packages\matplotlib\text.py ===
"""
Classes for including text in a figure.
"""

import functools
import logging
import math
from numbers import Real
import weakref

import numpy as np

import matplotlib as mpl
from . import _api, artist, cbook, _docstring
from .artist import Artist
from .font_manager import FontProperties
from .patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from .textpath import TextPath, TextToPath  # noqa # Logically located here
from .transforms import (
    Affine2D, Bbox, BboxBase, BboxTransformTo, IdentityTransform, Transform)


_log = logging.getLogger(__name__)


def _get_textbox(text, renderer):
    """
    Calculate the bounding box of the text.

    The bbox position takes text rotation into account, but the width and
    height are those of the unrotated box (unlike `.Text.get_window_extent`).
    """
    # TODO : This function may move into the Text class as a method. As a
    # matter of fact, the information from the _get_textbox function
    # should be available during the Text._get_layout() call, which is
    # called within the _get_textbox. So, it would better to move this
    # function as a method with some refactoring of _get_layout method.

    projected_xs = []
    projected_ys = []

    theta = np.deg2rad(text.get_rotation())
    tr = Affine2D().rotate(-theta)

    _, parts, d = text._get_layout(renderer)

    for t, wh, x, y in parts:
        w, h = wh

        xt1, yt1 = tr.transform((x, y))
        yt1 -= d
        xt2, yt2 = xt1 + w, yt1 + h

        projected_xs.extend([xt1, xt2])
        projected_ys.extend([yt1, yt2])

    xt_box, yt_box = min(projected_xs), min(projected_ys)
    w_box, h_box = max(projected_xs) - xt_box, max(projected_ys) - yt_box

    x_box, y_box = Affine2D().rotate(theta).transform((xt_box, yt_box))

    return x_box, y_box, w_box, h_box


def _get_text_metrics_with_cache(renderer, text, fontprop, ismath, dpi):
    """Call ``renderer.get_text_width_height_descent``, caching the results."""
    # Cached based on a copy of fontprop so that later in-place mutations of
    # the passed-in argument do not mess up the cache.
    return _get_text_metrics_with_cache_impl(
        weakref.ref(renderer), text, fontprop.copy(), ismath, dpi)


@functools.lru_cache(4096)
def _get_text_metrics_with_cache_impl(
        renderer_ref, text, fontprop, ismath, dpi):
    # dpi is unused, but participates in cache invalidation (via the renderer).
    return renderer_ref().get_text_width_height_descent(text, fontprop, ismath)


@_docstring.interpd
@_api.define_aliases({
    "color": ["c"],
    "fontproperties": ["font", "font_properties"],
    "fontfamily": ["family"],
    "fontname": ["name"],
    "fontsize": ["size"],
    "fontstretch": ["stretch"],
    "fontstyle": ["style"],
    "fontvariant": ["variant"],
    "fontweight": ["weight"],
    "horizontalalignment": ["ha"],
    "verticalalignment": ["va"],
    "multialignment": ["ma"],
})
class Text(Artist):
    """Handle storing and drawing of text in window or data coordinates."""

    zorder = 3
    _charsize_cache = dict()

    def __repr__(self):
        return f"Text({self._x}, {self._y}, {self._text!r})"

    def __init__(self,
                 x=0, y=0, text='', *,
                 color=None,           # defaults to rc params
                 verticalalignment='baseline',
                 horizontalalignment='left',
                 multialignment=None,
                 fontproperties=None,  # defaults to FontProperties()
                 rotation=None,
                 linespacing=None,
                 rotation_mode=None,
                 usetex=None,          # defaults to rcParams['text.usetex']
                 wrap=False,
                 transform_rotates_text=False,
                 parse_math=None,    # defaults to rcParams['text.parse_math']
                 antialiased=None,  # defaults to rcParams['text.antialiased']
                 **kwargs
                 ):
        """
        Create a `.Text` instance at *x*, *y* with string *text*.

        The text is aligned relative to the anchor point (*x*, *y*) according
        to ``horizontalalignment`` (default: 'left') and ``verticalalignment``
        (default: 'baseline'). See also
        :doc:`/gallery/text_labels_and_annotations/text_alignment`.

        While Text accepts the 'label' keyword argument, by default it is not
        added to the handles of a legend.

        Valid keyword arguments are:

        %(Text:kwdoc)s
        """
        super().__init__()
        self._x, self._y = x, y
        self._text = ''
        self._reset_visual_defaults(
            text=text,
            color=color,
            fontproperties=fontproperties,
            usetex=usetex,
            parse_math=parse_math,
            wrap=wrap,
            verticalalignment=verticalalignment,
            horizontalalignment=horizontalalignment,
            multialignment=multialignment,
            rotation=rotation,
            transform_rotates_text=transform_rotates_text,
            linespacing=linespacing,
            rotation_mode=rotation_mode,
            antialiased=antialiased
        )
        self.update(kwargs)

    def _reset_visual_defaults(
        self,
        text='',
        color=None,
        fontproperties=None,
        usetex=None,
        parse_math=None,
        wrap=False,
        verticalalignment='baseline',
        horizontalalignment='left',
        multialignment=None,
        rotation=None,
        transform_rotates_text=False,
        linespacing=None,
        rotation_mode=None,
        antialiased=None
    ):
        self.set_text(text)
        self.set_color(mpl._val_or_rc(color, "text.color"))
        self.set_fontproperties(fontproperties)
        self.set_usetex(usetex)
        self.set_parse_math(mpl._val_or_rc(parse_math, 'text.parse_math'))
        self.set_wrap(wrap)
        self.set_verticalalignment(verticalalignment)
        self.set_horizontalalignment(horizontalalignment)
        self._multialignment = multialignment
        self.set_rotation(rotation)
        self._transform_rotates_text = transform_rotates_text
        self._bbox_patch = None  # a FancyBboxPatch instance
        self._renderer = None
        if linespacing is None:
            linespacing = 1.2  # Maybe use rcParam later.
        self.set_linespacing(linespacing)
        self.set_rotation_mode(rotation_mode)
        self.set_antialiased(antialiased if antialiased is not None else
                             mpl.rcParams['text.antialiased'])

    def update(self, kwargs):
        # docstring inherited
        ret = []
        kwargs = cbook.normalize_kwargs(kwargs, Text)
        sentinel = object()  # bbox can be None, so use another sentinel.
        # Update fontproperties first, as it has lowest priority.
        fontproperties = kwargs.pop("fontproperties", sentinel)
        if fontproperties is not sentinel:
            ret.append(self.set_fontproperties(fontproperties))
        # Update bbox last, as it depends on font properties.
        bbox = kwargs.pop("bbox", sentinel)
        ret.extend(super().update(kwargs))
        if bbox is not sentinel:
            ret.append(self.set_bbox(bbox))
        return ret

    def __getstate__(self):
        d = super().__getstate__()
        # remove the cached _renderer (if it exists)
        d['_renderer'] = None
        return d

    def contains(self, mouseevent):
        """
        Return whether the mouse event occurred inside the axis-aligned
        bounding-box of the text.
        """
        if (self._different_canvas(mouseevent) or not self.get_visible()
                or self._renderer is None):
            return False, {}
        # Explicitly use Text.get_window_extent(self) and not
        # self.get_window_extent() so that Annotation.contains does not
        # accidentally cover the entire annotation bounding box.
        bbox = Text.get_window_extent(self)
        inside = (bbox.x0 <= mouseevent.x <= bbox.x1
                  and bbox.y0 <= mouseevent.y <= bbox.y1)
        cattr = {}
        # if the text has a surrounding patch, also check containment for it,
        # and merge the results with the results for the text.
        if self._bbox_patch:
            patch_inside, patch_cattr = self._bbox_patch.contains(mouseevent)
            inside = inside or patch_inside
            cattr["bbox_patch"] = patch_cattr
        return inside, cattr

    def _get_xy_display(self):
        """
        Get the (possibly unit converted) transformed x, y in display coords.
        """
        x, y = self.get_unitless_position()
        return self.get_transform().transform((x, y))

    def _get_multialignment(self):
        if self._multialignment is not None:
            return self._multialignment
        else:
            return self._horizontalalignment

    def _char_index_at(self, x):
        """
        Calculate the index closest to the coordinate x in display space.

        The position of text[index] is assumed to be the sum of the widths
        of all preceding characters text[:index].

        This works only on single line texts.
        """
        if not self._text:
            return 0

        text = self._text

        fontproperties = str(self._fontproperties)
        if fontproperties not in Text._charsize_cache:
            Text._charsize_cache[fontproperties] = dict()

        charsize_cache = Text._charsize_cache[fontproperties]
        for char in set(text):
            if char not in charsize_cache:
                self.set_text(char)
                bb = self.get_window_extent()
                charsize_cache[char] = bb.x1 - bb.x0

        self.set_text(text)
        bb = self.get_window_extent()

        size_accum = np.cumsum([0] + [charsize_cache[x] for x in text])
        std_x = x - bb.x0
        return (np.abs(size_accum - std_x)).argmin()

    def get_rotation(self):
        """Return the text angle in degrees between 0 and 360."""
        if self.get_transform_rotates_text():
            return self.get_transform().transform_angles(
                [self._rotation], [self.get_unitless_position()]).item(0)
        else:
            return self._rotation

    def get_transform_rotates_text(self):
        """
        Return whether rotations of the transform affect the text direction.
        """
        return self._transform_rotates_text

    def set_rotation_mode(self, m):
        """
        Set text rotation mode.

        Parameters
        ----------
        m : {None, 'default', 'anchor'}
            If ``"default"``, the text will be first rotated, then aligned according
            to their horizontal and vertical alignments.  If ``"anchor"``, then
            alignment occurs before rotation. Passing ``None`` will set the rotation
            mode to ``"default"``.
        """
        if m is None:
            m = "default"
        else:
            _api.check_in_list(("anchor", "default"), rotation_mode=m)
        self._rotation_mode = m
        self.stale = True

    def get_rotation_mode(self):
        """Return the text rotation mode."""
        return self._rotation_mode

    def set_antialiased(self, antialiased):
        """
        Set whether to use antialiased rendering.

        Parameters
        ----------
        antialiased : bool

        Notes
        -----
        Antialiasing will be determined by :rc:`text.antialiased`
        and the parameter *antialiased* will have no effect if the text contains
        math expressions.
        """
        self._antialiased = antialiased
        self.stale = True

    def get_antialiased(self):
        """Return whether antialiased rendering is used."""
        return self._antialiased

    def update_from(self, other):
        # docstring inherited
        super().update_from(other)
        self._color = other._color
        self._multialignment = other._multialignment
        self._verticalalignment = other._verticalalignment
        self._horizontalalignment = other._horizontalalignment
        self._fontproperties = other._fontproperties.copy()
        self._usetex = other._usetex
        self._rotation = other._rotation
        self._transform_rotates_text = other._transform_rotates_text
        self._picker = other._picker
        self._linespacing = other._linespacing
        self._antialiased = other._antialiased
        self.stale = True

    def _get_layout(self, renderer):
        """
        Return the extent (bbox) of the text together with
        multiple-alignment information. Note that it returns an extent
        of a rotated text when necessary.
        """
        thisx, thisy = 0.0, 0.0
        lines = self._get_wrapped_text().split("\n")  # Ensures lines is not empty.

        ws = []
        hs = []
        xs = []
        ys = []

        # Full vertical extent of font, including ascenders and descenders:
        _, lp_h, lp_d = _get_text_metrics_with_cache(
            renderer, "lp", self._fontproperties,
            ismath="TeX" if self.get_usetex() else False,
            dpi=self.get_figure(root=True).dpi)
        min_dy = (lp_h - lp_d) * self._linespacing

        for i, line in enumerate(lines):
            clean_line, ismath = self._preprocess_math(line)
            if clean_line:
                w, h, d = _get_text_metrics_with_cache(
                    renderer, clean_line, self._fontproperties,
                    ismath=ismath, dpi=self.get_figure(root=True).dpi)
            else:
                w = h = d = 0

            # For multiline text, increase the line spacing when the text
            # net-height (excluding baseline) is larger than that of a "l"
            # (e.g., use of superscripts), which seems what TeX does.
            h = max(h, lp_h)
            d = max(d, lp_d)

            ws.append(w)
            hs.append(h)

            # Metrics of the last line that are needed later:
            baseline = (h - d) - thisy

            if i == 0:
                # position at baseline
                thisy = -(h - d)
            else:
                # put baseline a good distance from bottom of previous line
                thisy -= max(min_dy, (h - d) * self._linespacing)

            xs.append(thisx)  # == 0.
            ys.append(thisy)

            thisy -= d

        # Metrics of the last line that are needed later:
        descent = d

        # Bounding box definition:
        width = max(ws)
        xmin = 0
        xmax = width
        ymax = 0
        ymin = ys[-1] - descent  # baseline of last line minus its descent

        # get the rotation matrix
        M = Affine2D().rotate_deg(self.get_rotation())

        # now offset the individual text lines within the box
        malign = self._get_multialignment()
        if malign == 'left':
            offset_layout = [(x, y) for x, y in zip(xs, ys)]
        elif malign == 'center':
            offset_layout = [(x + width / 2 - w / 2, y)
                             for x, y, w in zip(xs, ys, ws)]
        elif malign == 'right':
            offset_layout = [(x + width - w, y)
                             for x, y, w in zip(xs, ys, ws)]

        # the corners of the unrotated bounding box
        corners_horiz = np.array(
            [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)])

        # now rotate the bbox
        corners_rotated = M.transform(corners_horiz)
        # compute the bounds of the rotated box
        xmin = corners_rotated[:, 0].min()
        xmax = corners_rotated[:, 0].max()
        ymin = corners_rotated[:, 1].min()
        ymax = corners_rotated[:, 1].max()
        width = xmax - xmin
        height = ymax - ymin

        # Now move the box to the target position offset the display
        # bbox by alignment
        halign = self._horizontalalignment
        valign = self._verticalalignment

        rotation_mode = self.get_rotation_mode()
        if rotation_mode != "anchor":
            # compute the text location in display coords and the offsets
            # necessary to align the bbox with that location
            if halign == 'center':
                offsetx = (xmin + xmax) / 2
            elif halign == 'right':
                offsetx = xmax
            else:
                offsetx = xmin

            if valign == 'center':
                offsety = (ymin + ymax) / 2
            elif valign == 'top':
                offsety = ymax
            elif valign == 'baseline':
                offsety = ymin + descent
            elif valign == 'center_baseline':
                offsety = ymin + height - baseline / 2.0
            else:
                offsety = ymin
        else:
            xmin1, ymin1 = corners_horiz[0]
            xmax1, ymax1 = corners_horiz[2]

            if halign == 'center':
                offsetx = (xmin1 + xmax1) / 2.0
            elif halign == 'right':
                offsetx = xmax1
            else:
                offsetx = xmin1

            if valign == 'center':
                offsety = (ymin1 + ymax1) / 2.0
            elif valign == 'top':
                offsety = ymax1
            elif valign == 'baseline':
                offsety = ymax1 - baseline
            elif valign == 'center_baseline':
                offsety = ymax1 - baseline / 2.0
            else:
                offsety = ymin1

            offsetx, offsety = M.transform((offsetx, offsety))

        xmin -= offsetx
        ymin -= offsety

        bbox = Bbox.from_bounds(xmin, ymin, width, height)

        # now rotate the positions around the first (x, y) position
        xys = M.transform(offset_layout) - (offsetx, offsety)

        return bbox, list(zip(lines, zip(ws, hs), *xys.T)), descent

    def set_bbox(self, rectprops):
        """
        Draw a bounding box around self.

        Parameters
        ----------
        rectprops : dict with properties for `.patches.FancyBboxPatch`
             The default boxstyle is 'square'. The mutation
             scale of the `.patches.FancyBboxPatch` is set to the fontsize.

        Examples
        --------
        ::

            t.set_bbox(dict(facecolor='red', alpha=0.5))
        """

        if rectprops is not None:
            props = rectprops.copy()
            boxstyle = props.pop("boxstyle", None)
            pad = props.pop("pad", None)
            if boxstyle is None:
                boxstyle = "square"
                if pad is None:
                    pad = 4  # points
                pad /= self.get_size()  # to fraction of font size
            else:
                if pad is None:
                    pad = 0.3
            # boxstyle could be a callable or a string
            if isinstance(boxstyle, str) and "pad" not in boxstyle:
                boxstyle += ",pad=%0.2f" % pad
            self._bbox_patch = FancyBboxPatch(
                (0, 0), 1, 1,
                boxstyle=boxstyle, transform=IdentityTransform(), **props)
        else:
            self._bbox_patch = None

        self._update_clip_properties()

    def get_bbox_patch(self):
        """
        Return the bbox Patch, or None if the `.patches.FancyBboxPatch`
        is not made.
        """
        return self._bbox_patch

    def update_bbox_position_size(self, renderer):
        """
        Update the location and the size of the bbox.

        This method should be used when the position and size of the bbox needs
        to be updated before actually drawing the bbox.
        """
        if self._bbox_patch:
            # don't use self.get_unitless_position here, which refers to text
            # position in Text:
            posx = float(self.convert_xunits(self._x))
            posy = float(self.convert_yunits(self._y))
            posx, posy = self.get_transform().transform((posx, posy))

            x_box, y_box, w_box, h_box = _get_textbox(self, renderer)
            self._bbox_patch.set_bounds(0., 0., w_box, h_box)
            self._bbox_patch.set_transform(
                Affine2D()
                .rotate_deg(self.get_rotation())
                .translate(posx + x_box, posy + y_box))
            fontsize_in_pixel = renderer.points_to_pixels(self.get_size())
            self._bbox_patch.set_mutation_scale(fontsize_in_pixel)

    def _update_clip_properties(self):
        if self._bbox_patch:
            clipprops = dict(clip_box=self.clipbox,
                             clip_path=self._clippath,
                             clip_on=self._clipon)
            self._bbox_patch.update(clipprops)

    def set_clip_box(self, clipbox):
        # docstring inherited.
        super().set_clip_box(clipbox)
        self._update_clip_properties()

    def set_clip_path(self, path, transform=None):
        # docstring inherited.
        super().set_clip_path(path, transform)
        self._update_clip_properties()

    def set_clip_on(self, b):
        # docstring inherited.
        super().set_clip_on(b)
        self._update_clip_properties()

    def get_wrap(self):
        """Return whether the text can be wrapped."""
        return self._wrap

    def set_wrap(self, wrap):
        """
        Set whether the text can be wrapped.

        Wrapping makes sure the text is confined to the (sub)figure box. It
        does not take into account any other artists.

        Parameters
        ----------
        wrap : bool

        Notes
        -----
        Wrapping does not work together with
        ``savefig(..., bbox_inches='tight')`` (which is also used internally
        by ``%matplotlib inline`` in IPython/Jupyter). The 'tight' setting
        rescales the canvas to accommodate all content and happens before
        wrapping.
        """
        self._wrap = wrap

    def _get_wrap_line_width(self):
        """
        Return the maximum line width for wrapping text based on the current
        orientation.
        """
        x0, y0 = self.get_transform().transform(self.get_position())
        figure_box = self.get_figure().get_window_extent()

        # Calculate available width based on text alignment
        alignment = self.get_horizontalalignment()
        self.set_rotation_mode('anchor')
        rotation = self.get_rotation()

        left = self._get_dist_to_box(rotation, x0, y0, figure_box)
        right = self._get_dist_to_box(
            (180 + rotation) % 360, x0, y0, figure_box)

        if alignment == 'left':
            line_width = left
        elif alignment == 'right':
            line_width = right
        else:
            line_width = 2 * min(left, right)

        return line_width

    def _get_dist_to_box(self, rotation, x0, y0, figure_box):
        """
        Return the distance from the given points to the boundaries of a
        rotated box, in pixels.
        """
        if rotation > 270:
            quad = rotation - 270
            h1 = (y0 - figure_box.y0) / math.cos(math.radians(quad))
            h2 = (figure_box.x1 - x0) / math.cos(math.radians(90 - quad))
        elif rotation > 180:
            quad = rotation - 180
            h1 = (x0 - figure_box.x0) / math.cos(math.radians(quad))
            h2 = (y0 - figure_box.y0) / math.cos(math.radians(90 - quad))
        elif rotation > 90:
            quad = rotation - 90
            h1 = (figure_box.y1 - y0) / math.cos(math.radians(quad))
            h2 = (x0 - figure_box.x0) / math.cos(math.radians(90 - quad))
        else:
            h1 = (figure_box.x1 - x0) / math.cos(math.radians(rotation))
            h2 = (figure_box.y1 - y0) / math.cos(math.radians(90 - rotation))

        return min(h1, h2)

    def _get_rendered_text_width(self, text):
        """
        Return the width of a given text string, in pixels.
        """

        w, h, d = _get_text_metrics_with_cache(
            self._renderer, text, self.get_fontproperties(),
            cbook.is_math_text(text),
            self.get_figure(root=True).dpi)
        return math.ceil(w)

    def _get_wrapped_text(self):
        """
        Return a copy of the text string with new lines added so that the text
        is wrapped relative to the parent figure (if `get_wrap` is True).
        """
        if not self.get_wrap():
            return self.get_text()

        # Not fit to handle breaking up latex syntax correctly, so
        # ignore latex for now.
        if self.get_usetex():
            return self.get_text()

        # Build the line incrementally, for a more accurate measure of length
        line_width = self._get_wrap_line_width()
        wrapped_lines = []

        # New lines in the user's text force a split
        unwrapped_lines = self.get_text().split('\n')

        # Now wrap each individual unwrapped line
        for unwrapped_line in unwrapped_lines:

            sub_words = unwrapped_line.split(' ')
            # Remove items from sub_words as we go, so stop when empty
            while len(sub_words) > 0:
                if len(sub_words) == 1:
                    # Only one word, so just add it to the end
                    wrapped_lines.append(sub_words.pop(0))
                    continue

                for i in range(2, len(sub_words) + 1):
                    # Get width of all words up to and including here
                    line = ' '.join(sub_words[:i])
                    current_width = self._get_rendered_text_width(line)

                    # If all these words are too wide, append all not including
                    # last word
                    if current_width > line_width:
                        wrapped_lines.append(' '.join(sub_words[:i - 1]))
                        sub_words = sub_words[i - 1:]
                        break

                    # Otherwise if all words fit in the width, append them all
                    elif i == len(sub_words):
                        wrapped_lines.append(' '.join(sub_words[:i]))
                        sub_words = []
                        break

        return '\n'.join(wrapped_lines)

    @artist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited

        if renderer is not None:
            self._renderer = renderer
        if not self.get_visible():
            return
        if self.get_text() == '':
            return

        renderer.open_group('text', self.get_gid())

        with self._cm_set(text=self._get_wrapped_text()):
            bbox, info, descent = self._get_layout(renderer)
            trans = self.get_transform()

            # don't use self.get_position here, which refers to text
            # position in Text:
            x, y = self._x, self._y
            if np.ma.is_masked(x):
                x = np.nan
            if np.ma.is_masked(y):
                y = np.nan
            posx = float(self.convert_xunits(x))
            posy = float(self.convert_yunits(y))
            posx, posy = trans.transform((posx, posy))
            if np.isnan(posx) or np.isnan(posy):
                return  # don't throw a warning here
            if not np.isfinite(posx) or not np.isfinite(posy):
                _log.warning("posx and posy should be finite values")
                return
            canvasw, canvash = renderer.get_canvas_width_height()

            # Update the location and size of the bbox
            # (`.patches.FancyBboxPatch`), and draw it.
            if self._bbox_patch:
                self.update_bbox_position_size(renderer)
                self._bbox_patch.draw(renderer)

            gc = renderer.new_gc()
            gc.set_foreground(self.get_color())
            gc.set_alpha(self.get_alpha())
            gc.set_url(self._url)
            gc.set_antialiased(self._antialiased)
            self._set_gc_clip(gc)

            angle = self.get_rotation()

            for line, wh, x, y in info:

                mtext = self if len(info) == 1 else None
                x = x + posx
                y = y + posy
                if renderer.flipy():
                    y = canvash - y
                clean_line, ismath = self._preprocess_math(line)

                if self.get_path_effects():
                    from matplotlib.patheffects import PathEffectRenderer
                    textrenderer = PathEffectRenderer(
                        self.get_path_effects(), renderer)
                else:
                    textrenderer = renderer

                if self.get_usetex():
                    textrenderer.draw_tex(gc, x, y, clean_line,
                                          self._fontproperties, angle,
                                          mtext=mtext)
                else:
                    textrenderer.draw_text(gc, x, y, clean_line,
                                           self._fontproperties, angle,
                                           ismath=ismath, mtext=mtext)

        gc.restore()
        renderer.close_group('text')
        self.stale = False

    def get_color(self):
        """Return the color of the text."""
        return self._color

    def get_fontproperties(self):
        """Return the `.font_manager.FontProperties`."""
        return self._fontproperties

    def get_fontfamily(self):
        """
        Return the list of font families used for font lookup.

        See Also
        --------
        .font_manager.FontProperties.get_family
        """
        return self._fontproperties.get_family()

    def get_fontname(self):
        """
        Return the font name as a string.

        See Also
        --------
        .font_manager.FontProperties.get_name
        """
        return self._fontproperties.get_name()

    def get_fontstyle(self):
        """
        Return the font style as a string.

        See Also
        --------
        .font_manager.FontProperties.get_style
        """
        return self._fontproperties.get_style()

    def get_fontsize(self):
        """
        Return the font size as an integer.

        See Also
        --------
        .font_manager.FontProperties.get_size_in_points
        """
        return self._fontproperties.get_size_in_points()

    def get_fontvariant(self):
        """
        Return the font variant as a string.

        See Also
        --------
        .font_manager.FontProperties.get_variant
        """
        return self._fontproperties.get_variant()

    def get_fontweight(self):
        """
        Return the font weight as a string or a number.

        See Also
        --------
        .font_manager.FontProperties.get_weight
        """
        return self._fontproperties.get_weight()

    def get_stretch(self):
        """
        Return the font stretch as a string or a number.

        See Also
        --------
        .font_manager.FontProperties.get_stretch
        """
        return self._fontproperties.get_stretch()

    def get_horizontalalignment(self):
        """
        Return the horizontal alignment as a string.  Will be one of
        'left', 'center' or 'right'.
        """
        return self._horizontalalignment

    def get_unitless_position(self):
        """Return the (x, y) unitless position of the text."""
        # This will get the position with all unit information stripped away.
        # This is here for convenience since it is done in several locations.
        x = float(self.convert_xunits(self._x))
        y = float(self.convert_yunits(self._y))
        return x, y

    def get_position(self):
        """Return the (x, y) position of the text."""
        # This should return the same data (possible unitized) as was
        # specified with 'set_x' and 'set_y'.
        return self._x, self._y

    def get_text(self):
        """Return the text string."""
        return self._text

    def get_verticalalignment(self):
        """
        Return the vertical alignment as a string.  Will be one of
        'top', 'center', 'bottom', 'baseline' or 'center_baseline'.
        """
        return self._verticalalignment

    def get_window_extent(self, renderer=None, dpi=None):
        """
        Return the `.Bbox` bounding the text, in display units.

        In addition to being used internally, this is useful for specifying
        clickable regions in a png file on a web page.

        Parameters
        ----------
        renderer : Renderer, optional
            A renderer is needed to compute the bounding box.  If the artist
            has already been drawn, the renderer is cached; thus, it is only
            necessary to pass this argument when calling `get_window_extent`
            before the first draw.  In practice, it is usually easier to
            trigger a draw first, e.g. by calling
            `~.Figure.draw_without_rendering` or ``plt.show()``.

        dpi : float, optional
            The dpi value for computing the bbox, defaults to
            ``self.get_figure(root=True).dpi`` (*not* the renderer dpi); should be set
            e.g. if to match regions with a figure saved with a custom dpi value.
        """
        if not self.get_visible():
            return Bbox.unit()

        fig = self.get_figure(root=True)
        if dpi is None:
            dpi = fig.dpi
        if self.get_text() == '':
            with cbook._setattr_cm(fig, dpi=dpi):
                tx, ty = self._get_xy_display()
                return Bbox.from_bounds(tx, ty, 0, 0)

        if renderer is not None:
            self._renderer = renderer
        if self._renderer is None:
            self._renderer = fig._get_renderer()
        if self._renderer is None:
            raise RuntimeError(
                "Cannot get window extent of text w/o renderer. You likely "
                "want to call 'figure.draw_without_rendering()' first.")

        with cbook._setattr_cm(fig, dpi=dpi):
            bbox, info, descent = self._get_layout(self._renderer)
            x, y = self.get_unitless_position()
            x, y = self.get_transform().transform((x, y))
            bbox = bbox.translated(x, y)
            return bbox

    def set_backgroundcolor(self, color):
        """
        Set the background color of the text by updating the bbox.

        Parameters
        ----------
        color : :mpltype:`color`

        See Also
        --------
        .set_bbox : To change the position of the bounding box
        """
        if self._bbox_patch is None:
            self.set_bbox(dict(facecolor=color, edgecolor=color))
        else:
            self._bbox_patch.update(dict(facecolor=color))

        self._update_clip_properties()
        self.stale = True

    def set_color(self, color):
        """
        Set the foreground color of the text

        Parameters
        ----------
        color : :mpltype:`color`
        """
        # "auto" is only supported by axisartist, but we can just let it error
        # out at draw time for simplicity.
        if not cbook._str_equal(color, "auto"):
            mpl.colors._check_color_like(color=color)
        self._color = color
        self.stale = True

    def set_horizontalalignment(self, align):
        """
        Set the horizontal alignment relative to the anchor point.

        See also :doc:`/gallery/text_labels_and_annotations/text_alignment`.

        Parameters
        ----------
        align : {'left', 'center', 'right'}
        """
        _api.check_in_list(['center', 'right', 'left'], align=align)
        self._horizontalalignment = align
        self.stale = True

    def set_multialignment(self, align):
        """
        Set the text alignment for multiline texts.

        The layout of the bounding box of all the lines is determined by the
        horizontalalignment and verticalalignment properties. This property
        controls the alignment of the text lines within that box.

        Parameters
        ----------
        align : {'left', 'right', 'center'}
        """
        _api.check_in_list(['center', 'right', 'left'], align=align)
        self._multialignment = align
        self.stale = True

    def set_linespacing(self, spacing):
        """
        Set the line spacing as a multiple of the font size.

        The default line spacing is 1.2.

        Parameters
        ----------
        spacing : float (multiple of font size)
        """
        _api.check_isinstance(Real, spacing=spacing)
        self._linespacing = spacing
        self.stale = True

    def set_fontfamily(self, fontname):
        """
        Set the font family.  Can be either a single string, or a list of
        strings in decreasing priority.  Each string may be either a real font
        name or a generic font class name.  If the latter, the specific font
        names will be looked up in the corresponding rcParams.

        If a `Text` instance is constructed with ``fontfamily=None``, then the
        font is set to :rc:`font.family`, and the
        same is done when `set_fontfamily()` is called on an existing
        `Text` instance.

        Parameters
        ----------
        fontname : {FONTNAME, 'serif', 'sans-serif', 'cursive', 'fantasy', \
'monospace'}

        See Also
        --------
        .font_manager.FontProperties.set_family
        """
        self._fontproperties.set_family(fontname)
        self.stale = True

    def set_fontvariant(self, variant):
        """
        Set the font variant.

        Parameters
        ----------
        variant : {'normal', 'small-caps'}

        See Also
        --------
        .font_manager.FontProperties.set_variant
        """
        self._fontproperties.set_variant(variant)
        self.stale = True

    def set_fontstyle(self, fontstyle):
        """
        Set the font style.

        Parameters
        ----------
        fontstyle : {'normal', 'italic', 'oblique'}

        See Also
        --------
        .font_manager.FontProperties.set_style
        """
        self._fontproperties.set_style(fontstyle)
        self.stale = True

    def set_fontsize(self, fontsize):
        """
        Set the font size.

        Parameters
        ----------
        fontsize : float or {'xx-small', 'x-small', 'small', 'medium', \
'large', 'x-large', 'xx-large'}
            If a float, the fontsize in points. The string values denote sizes
            relative to the default font size.

        See Also
        --------
        .font_manager.FontProperties.set_size
        """
        self._fontproperties.set_size(fontsize)
        self.stale = True

    def get_math_fontfamily(self):
        """
        Return the font family name for math text rendered by Matplotlib.

        The default value is :rc:`mathtext.fontset`.

        See Also
        --------
        set_math_fontfamily
        """
        return self._fontproperties.get_math_fontfamily()

    def set_math_fontfamily(self, fontfamily):
        """
        Set the font family for math text rendered by Matplotlib.

        This does only affect Matplotlib's own math renderer. It has no effect
        when rendering with TeX (``usetex=True``).

        Parameters
        ----------
        fontfamily : str
            The name of the font family.

            Available font families are defined in the
            :ref:`default matplotlibrc file
            <customizing-with-matplotlibrc-files>`.

        See Also
        --------
        get_math_fontfamily
        """
        self._fontproperties.set_math_fontfamily(fontfamily)

    def set_fontweight(self, weight):
        """
        Set the font weight.

        Parameters
        ----------
        weight : {a numeric value in range 0-1000, 'ultralight', 'light', \
'normal', 'regular', 'book', 'medium', 'roman', 'semibold', 'demibold', \
'demi', 'bold', 'heavy', 'extra bold', 'black'}

        See Also
        --------
        .font_manager.FontProperties.set_weight
        """
        self._fontproperties.set_weight(weight)
        self.stale = True

    def set_fontstretch(self, stretch):
        """
        Set the font stretch (horizontal condensation or expansion).

        Parameters
        ----------
        stretch : {a numeric value in range 0-1000, 'ultra-condensed', \
'extra-condensed', 'condensed', 'semi-condensed', 'normal', 'semi-expanded', \
'expanded', 'extra-expanded', 'ultra-expanded'}

        See Also
        --------
        .font_manager.FontProperties.set_stretch
        """
        self._fontproperties.set_stretch(stretch)
        self.stale = True

    def set_position(self, xy):
        """
        Set the (*x*, *y*) position of the text.

        Parameters
        ----------
        xy : (float, float)
        """
        self.set_x(xy[0])
        self.set_y(xy[1])

    def set_x(self, x):
        """
        Set the *x* position of the text.

        Parameters
        ----------
        x : float
        """
        self._x = x
        self.stale = True

    def set_y(self, y):
        """
        Set the *y* position of the text.

        Parameters
        ----------
        y : float
        """
        self._y = y
        self.stale = True

    def set_rotation(self, s):
        """
        Set the rotation of the text.

        Parameters
        ----------
        s : float or {'vertical', 'horizontal'}
            The rotation angle in degrees in mathematically positive direction
            (counterclockwise). 'horizontal' equals 0, 'vertical' equals 90.
        """
        if isinstance(s, Real):
            self._rotation = float(s) % 360
        elif cbook._str_equal(s, 'horizontal') or s is None:
            self._rotation = 0.
        elif cbook._str_equal(s, 'vertical'):
            self._rotation = 90.
        else:
            raise ValueError("rotation must be 'vertical', 'horizontal' or "
                             f"a number, not {s}")
        self.stale = True

    def set_transform_rotates_text(self, t):
        """
        Whether rotations of the transform affect the text direction.

        Parameters
        ----------
        t : bool
        """
        self._transform_rotates_text = t
        self.stale = True

    def set_verticalalignment(self, align):
        """
        Set the vertical alignment relative to the anchor point.

        See also :doc:`/gallery/text_labels_and_annotations/text_alignment`.

        Parameters
        ----------
        align : {'baseline', 'bottom', 'center', 'center_baseline', 'top'}
        """
        _api.check_in_list(
            ['top', 'bottom', 'center', 'baseline', 'center_baseline'],
            align=align)
        self._verticalalignment = align
        self.stale = True

    def set_text(self, s):
        r"""
        Set the text string *s*.

        It may contain newlines (``\n``) or math in LaTeX syntax.

        Parameters
        ----------
        s : object
            Any object gets converted to its `str` representation, except for
            ``None`` which is converted to an empty string.
        """
        s = '' if s is None else str(s)
        if s != self._text:
            self._text = s
            self.stale = True

    def _preprocess_math(self, s):
        """
        Return the string *s* after mathtext preprocessing, and the kind of
        mathtext support needed.

        - If *self* is configured to use TeX, return *s* unchanged except that
          a single space gets escaped, and the flag "TeX".
        - Otherwise, if *s* is mathtext (has an even number of unescaped dollar
          signs) and ``parse_math`` is not set to False, return *s* and the
          flag True.
        - Otherwise, return *s* with dollar signs unescaped, and the flag
          False.
        """
        if self.get_usetex():
            if s == " ":
                s = r"\ "
            return s, "TeX"
        elif not self.get_parse_math():
            return s, False
        elif cbook.is_math_text(s):
            return s, True
        else:
            return s.replace(r"\$", "$"), False

    def set_fontproperties(self, fp):
        """
        Set the font properties that control the text.

        Parameters
        ----------
        fp : `.font_manager.FontProperties` or `str` or `pathlib.Path`
            If a `str`, it is interpreted as a fontconfig pattern parsed by
            `.FontProperties`.  If a `pathlib.Path`, it is interpreted as the
            absolute path to a font file.
        """
        self._fontproperties = FontProperties._from_any(fp).copy()
        self.stale = True

    @_docstring.kwarg_doc("bool, default: :rc:`text.usetex`")
    def set_usetex(self, usetex):
        """
        Parameters
        ----------
        usetex : bool or None
            Whether to render using TeX, ``None`` means to use
            :rc:`text.usetex`.
        """
        if usetex is None:
            self._usetex = mpl.rcParams['text.usetex']
        else:
            self._usetex = bool(usetex)
        self.stale = True

    def get_usetex(self):
        """Return whether this `Text` object uses TeX for rendering."""
        return self._usetex

    def set_parse_math(self, parse_math):
        """
        Override switch to disable any mathtext parsing for this `Text`.

        Parameters
        ----------
        parse_math : bool
            If False, this `Text` will never use mathtext.  If True, mathtext
            will be used if there is an even number of unescaped dollar signs.
        """
        self._parse_math = bool(parse_math)

    def get_parse_math(self):
        """Return whether mathtext parsing is considered for this `Text`."""
        return self._parse_math

    def set_fontname(self, fontname):
        """
        Alias for `set_fontfamily`.

        One-way alias only: the getter differs.

        Parameters
        ----------
        fontname : {FONTNAME, 'serif', 'sans-serif', 'cursive', 'fantasy', \
'monospace'}

        See Also
        --------
        .font_manager.FontProperties.set_family

        """
        self.set_fontfamily(fontname)


class OffsetFrom:
    """Callable helper class for working with `Annotation`."""

    def __init__(self, artist, ref_coord, unit="points"):
        """
        Parameters
        ----------
        artist : `~matplotlib.artist.Artist` or `.BboxBase` or `.Transform`
            The object to compute the offset from.

        ref_coord : (float, float)
            If *artist* is an `.Artist` or `.BboxBase`, this values is
            the location to of the offset origin in fractions of the
            *artist* bounding box.

            If *artist* is a transform, the offset origin is the
            transform applied to this value.

        unit : {'points, 'pixels'}, default: 'points'
            The screen units to use (pixels or points) for the offset input.
        """
        self._artist = artist
        x, y = ref_coord  # Make copy when ref_coord is an array (and check the shape).
        self._ref_coord = x, y
        self.set_unit(unit)

    def set_unit(self, unit):
        """
        Set the unit for input to the transform used by ``__call__``.

        Parameters
        ----------
        unit : {'points', 'pixels'}
        """
        _api.check_in_list(["points", "pixels"], unit=unit)
        self._unit = unit

    def get_unit(self):
        """Return the unit for input to the transform used by ``__call__``."""
        return self._unit

    def __call__(self, renderer):
        """
        Return the offset transform.

        Parameters
        ----------
        renderer : `RendererBase`
            The renderer to use to compute the offset

        Returns
        -------
        `Transform`
            Maps (x, y) in pixel or point units to screen units
            relative to the given artist.
        """
        if isinstance(self._artist, Artist):
            bbox = self._artist.get_window_extent(renderer)
            xf, yf = self._ref_coord
            x = bbox.x0 + bbox.width * xf
            y = bbox.y0 + bbox.height * yf
        elif isinstance(self._artist, BboxBase):
            bbox = self._artist
            xf, yf = self._ref_coord
            x = bbox.x0 + bbox.width * xf
            y = bbox.y0 + bbox.height * yf
        elif isinstance(self._artist, Transform):
            x, y = self._artist.transform(self._ref_coord)
        else:
            _api.check_isinstance((Artist, BboxBase, Transform), artist=self._artist)
        scale = 1 if self._unit == "pixels" else renderer.points_to_pixels(1)
        return Affine2D().scale(scale).translate(x, y)


class _AnnotationBase:
    def __init__(self,
                 xy,
                 xycoords='data',
                 annotation_clip=None):

        x, y = xy  # Make copy when xy is an array (and check the shape).
        self.xy = x, y
        self.xycoords = xycoords
        self.set_annotation_clip(annotation_clip)

        self._draggable = None

    def _get_xy(self, renderer, xy, coords):
        x, y = xy
        xcoord, ycoord = coords if isinstance(coords, tuple) else (coords, coords)
        if xcoord == 'data':
            x = float(self.convert_xunits(x))
        if ycoord == 'data':
            y = float(self.convert_yunits(y))
        return self._get_xy_transform(renderer, coords).transform((x, y))

    def _get_xy_transform(self, renderer, coords):

        if isinstance(coords, tuple):
            xcoord, ycoord = coords
            from matplotlib.transforms import blended_transform_factory
            tr1 = self._get_xy_transform(renderer, xcoord)
            tr2 = self._get_xy_transform(renderer, ycoord)
            return blended_transform_factory(tr1, tr2)
        elif callable(coords):
            tr = coords(renderer)
            if isinstance(tr, BboxBase):
                return BboxTransformTo(tr)
            elif isinstance(tr, Transform):
                return tr
            else:
                raise TypeError(
                    f"xycoords callable must return a BboxBase or Transform, not a "
                    f"{type(tr).__name__}")
        elif isinstance(coords, Artist):
            bbox = coords.get_window_extent(renderer)
            return BboxTransformTo(bbox)
        elif isinstance(coords, BboxBase):
            return BboxTransformTo(coords)
        elif isinstance(coords, Transform):
            return coords
        elif not isinstance(coords, str):
            raise TypeError(
                f"'xycoords' must be an instance of str, tuple[str, str], Artist, "
                f"Transform, or Callable, not a {type(coords).__name__}")

        if coords == 'data':
            return self.axes.transData
        elif coords == 'polar':
            from matplotlib.projections import PolarAxes
            tr = PolarAxes.PolarTransform(apply_theta_transforms=False)
            trans = tr + self.axes.transData
            return trans

        try:
            bbox_name, unit = coords.split()
        except ValueError:  # i.e. len(coords.split()) != 2.
            raise ValueError(f"{coords!r} is not a valid coordinate") from None

        bbox0, xy0 = None, None

        # if unit is offset-like
        if bbox_name == "figure":
            bbox0 = self.get_figure(root=False).figbbox
        elif bbox_name == "subfigure":
            bbox0 = self.get_figure(root=False).bbox
        elif bbox_name == "axes":
            bbox0 = self.axes.bbox

        # reference x, y in display coordinate
        if bbox0 is not None:
            xy0 = bbox0.p0
        elif bbox_name == "offset":
            xy0 = self._get_position_xy(renderer)
        else:
            raise ValueError(f"{coords!r} is not a valid coordinate")

        if unit == "points":
            tr = Affine2D().scale(
                self.get_figure(root=True).dpi / 72)  # dpi/72 dots per point
        elif unit == "pixels":
            tr = Affine2D()
        elif unit == "fontsize":
            tr = Affine2D().scale(
                self.get_size() * self.get_figure(root=True).dpi / 72)
        elif unit == "fraction":
            tr = Affine2D().scale(*bbox0.size)
        else:
            raise ValueError(f"{unit!r} is not a recognized unit")

        return tr.translate(*xy0)

    def set_annotation_clip(self, b):
        """
        Set the annotation's clipping behavior.

        Parameters
        ----------
        b : bool or None
            - True: The annotation will be clipped when ``self.xy`` is
              outside the Axes.
            - False: The annotation will always be drawn.
            - None: The annotation will be clipped when ``self.xy`` is
              outside the Axes and ``self.xycoords == "data"``.
        """
        self._annotation_clip = b

    def get_annotation_clip(self):
        """
        Return the annotation's clipping behavior.

        See `set_annotation_clip` for the meaning of return values.
        """
        return self._annotation_clip

    def _get_position_xy(self, renderer):
        """Return the pixel position of the annotated point."""
        return self._get_xy(renderer, self.xy, self.xycoords)

    def _check_xy(self, renderer=None):
        """Check whether the annotation at *xy_pixel* should be drawn."""
        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()
        b = self.get_annotation_clip()
        if b or (b is None and self.xycoords == "data"):
            # check if self.xy is inside the Axes.
            xy_pixel = self._get_position_xy(renderer)
            return self.axes.contains_point(xy_pixel)
        return True

    def draggable(self, state=None, use_blit=False):
        """
        Set whether the annotation is draggable with the mouse.

        Parameters
        ----------
        state : bool or None
            - True or False: set the draggability.
            - None: toggle the draggability.
        use_blit : bool, default: False
            Use blitting for faster image composition. For details see
            :ref:`func-animation`.

        Returns
        -------
        DraggableAnnotation or None
            If the annotation is draggable, the corresponding
            `.DraggableAnnotation` helper is returned.
        """
        from matplotlib.offsetbox import DraggableAnnotation
        is_draggable = self._draggable is not None

        # if state is None we'll toggle
        if state is None:
            state = not is_draggable

        if state:
            if self._draggable is None:
                self._draggable = DraggableAnnotation(self, use_blit)
        else:
            if self._draggable is not None:
                self._draggable.disconnect()
            self._draggable = None

        return self._draggable


class Annotation(Text, _AnnotationBase):
    """
    An `.Annotation` is a `.Text` that can refer to a specific position *xy*.
    Optionally an arrow pointing from the text to *xy* can be drawn.

    Attributes
    ----------
    xy
        The annotated position.
    xycoords
        The coordinate system for *xy*.
    arrow_patch
        A `.FancyArrowPatch` to point from *xytext* to *xy*.
    """

    def __str__(self):
        return f"Annotation({self.xy[0]:g}, {self.xy[1]:g}, {self._text!r})"

    def __init__(self, text, xy,
                 xytext=None,
                 xycoords='data',
                 textcoords=None,
                 arrowprops=None,
                 annotation_clip=None,
                 **kwargs):
        """
        Annotate the point *xy* with text *text*.

        In the simplest form, the text is placed at *xy*.

        Optionally, the text can be displayed in another position *xytext*.
        An arrow pointing from the text to the annotated point *xy* can then
        be added by defining *arrowprops*.

        Parameters
        ----------
        text : str
            The text of the annotation.

        xy : (float, float)
            The point *(x, y)* to annotate. The coordinate system is determined
            by *xycoords*.

        xytext : (float, float), default: *xy*
            The position *(x, y)* to place the text at. The coordinate system
            is determined by *textcoords*.

        xycoords : single or two-tuple of str or `.Artist` or `.Transform` or \
callable, default: 'data'

            The coordinate system that *xy* is given in. The following types
            of values are supported:

            - One of the following strings:

              ==================== ============================================
              Value                Description
              ==================== ============================================
              'figure points'      Points from the lower left of the figure
              'figure pixels'      Pixels from the lower left of the figure
              'figure fraction'    Fraction of figure from lower left
              'subfigure points'   Points from the lower left of the subfigure
              'subfigure pixels'   Pixels from the lower left of the subfigure
              'subfigure fraction' Fraction of subfigure from lower left
              'axes points'        Points from lower left corner of the Axes
              'axes pixels'        Pixels from lower left corner of the Axes
              'axes fraction'      Fraction of Axes from lower left
              'data'               Use the coordinate system of the object
                                   being annotated (default)
              'polar'              *(theta, r)* if not native 'data'
                                   coordinates
              ==================== ============================================

              Note that 'subfigure pixels' and 'figure pixels' are the same
              for the parent figure, so users who want code that is usable in
              a subfigure can use 'subfigure pixels'.

            - An `.Artist`: *xy* is interpreted as a fraction of the artist's
              `~matplotlib.transforms.Bbox`. E.g. *(0, 0)* would be the lower
              left corner of the bounding box and *(0.5, 1)* would be the
              center top of the bounding box.

            - A `.Transform` to transform *xy* to screen coordinates.

            - A function with one of the following signatures::

                def transform(renderer) -> Bbox
                def transform(renderer) -> Transform

              where *renderer* is a `.RendererBase` subclass.

              The result of the function is interpreted like the `.Artist` and
              `.Transform` cases above.

            - A tuple *(xcoords, ycoords)* specifying separate coordinate
              systems for *x* and *y*. *xcoords* and *ycoords* must each be
              of one of the above described types.

            See :ref:`plotting-guide-annotation` for more details.

        textcoords : single or two-tuple of str or `.Artist` or `.Transform` \
or callable, default: value of *xycoords*
            The coordinate system that *xytext* is given in.

            All *xycoords* values are valid as well as the following strings:

            =================   =================================================
            Value               Description
            =================   =================================================
            'offset points'     Offset, in points, from the *xy* value
            'offset pixels'     Offset, in pixels, from the *xy* value
            'offset fontsize'   Offset, relative to fontsize, from the *xy* value
            =================   =================================================

        arrowprops : dict, optional
            The properties used to draw a `.FancyArrowPatch` arrow between the
            positions *xy* and *xytext*.  Defaults to None, i.e. no arrow is
            drawn.

            For historical reasons there are two different ways to specify
            arrows, "simple" and "fancy":

            **Simple arrow:**

            If *arrowprops* does not contain the key 'arrowstyle' the
            allowed keys are:

            ==========  =================================================
            Key         Description
            ==========  =================================================
            width       The width of the arrow in points
            headwidth   The width of the base of the arrow head in points
            headlength  The length of the arrow head in points
            shrink      Fraction of total length to shrink from both ends
            ?           Any `.FancyArrowPatch` property
            ==========  =================================================

            The arrow is attached to the edge of the text box, the exact
            position (corners or centers) depending on where it's pointing to.

            **Fancy arrow:**

            This is used if 'arrowstyle' is provided in the *arrowprops*.

            Valid keys are the following `.FancyArrowPatch` parameters:

            ===============  ===================================
            Key              Description
            ===============  ===================================
            arrowstyle       The arrow style
            connectionstyle  The connection style
            relpos           See below; default is (0.5, 0.5)
            patchA           Default is bounding box of the text
            patchB           Default is None
            shrinkA          In points. Default is 2 points
            shrinkB          In points. Default is 2 points
            mutation_scale   Default is text size (in points)
            mutation_aspect  Default is 1
            ?                Any `.FancyArrowPatch` property
            ===============  ===================================

            The exact starting point position of the arrow is defined by
            *relpos*. It's a tuple of relative coordinates of the text box,
            where (0, 0) is the lower left corner and (1, 1) is the upper
            right corner. Values <0 and >1 are supported and specify points
            outside the text box. By default (0.5, 0.5), so the starting point
            is centered in the text box.

        annotation_clip : bool or None, default: None
            Whether to clip (i.e. not draw) the annotation when the annotation
            point *xy* is outside the Axes area.

            - If *True*, the annotation will be clipped when *xy* is outside
              the Axes.
            - If *False*, the annotation will always be drawn.
            - If *None*, the annotation will be clipped when *xy* is outside
              the Axes and *xycoords* is 'data'.

        **kwargs
            Additional kwargs are passed to `.Text`.

        Returns
        -------
        `.Annotation`

        See Also
        --------
        :ref:`annotations`

        """
        _AnnotationBase.__init__(self,
                                 xy,
                                 xycoords=xycoords,
                                 annotation_clip=annotation_clip)
        # warn about wonky input data
        if (xytext is None and
                textcoords is not None and
                textcoords != xycoords):
            _api.warn_external("You have used the `textcoords` kwarg, but "
                               "not the `xytext` kwarg.  This can lead to "
                               "surprising results.")

        # clean up textcoords and assign default
        if textcoords is None:
            textcoords = self.xycoords
        self._textcoords = textcoords

        # cleanup xytext defaults
        if xytext is None:
            xytext = self.xy
        x, y = xytext

        self.arrowprops = arrowprops
        if arrowprops is not None:
            arrowprops = arrowprops.copy()
            if "arrowstyle" in arrowprops:
                self._arrow_relpos = arrowprops.pop("relpos", (0.5, 0.5))
            else:
                # modified YAArrow API to be used with FancyArrowPatch
                for key in ['width', 'headwidth', 'headlength', 'shrink']:
                    arrowprops.pop(key, None)
            self.arrow_patch = FancyArrowPatch((0, 0), (1, 1), **arrowprops)
        else:
            self.arrow_patch = None

        # Must come last, as some kwargs may be propagated to arrow_patch.
        Text.__init__(self, x, y, text, **kwargs)

    def contains(self, mouseevent):
        if self._different_canvas(mouseevent):
            return False, {}
        contains, tinfo = Text.contains(self, mouseevent)
        if self.arrow_patch is not None:
            in_patch, _ = self.arrow_patch.contains(mouseevent)
            contains = contains or in_patch
        return contains, tinfo

    @property
    def xycoords(self):
        return self._xycoords

    @xycoords.setter
    def xycoords(self, xycoords):
        def is_offset(s):
            return isinstance(s, str) and s.startswith("offset")

        if (isinstance(xycoords, tuple) and any(map(is_offset, xycoords))
                or is_offset(xycoords)):
            raise ValueError("xycoords cannot be an offset coordinate")
        self._xycoords = xycoords

    @property
    def xyann(self):
        """
        The text position.

        See also *xytext* in `.Annotation`.
        """
        return self.get_position()

    @xyann.setter
    def xyann(self, xytext):
        self.set_position(xytext)

    def get_anncoords(self):
        """
        Return the coordinate system to use for `.Annotation.xyann`.

        See also *xycoords* in `.Annotation`.
        """
        return self._textcoords

    def set_anncoords(self, coords):
        """
        Set the coordinate system to use for `.Annotation.xyann`.

        See also *xycoords* in `.Annotation`.
        """
        self._textcoords = coords

    anncoords = property(get_anncoords, set_anncoords, doc="""
        The coordinate system to use for `.Annotation.xyann`.""")

    def set_figure(self, fig):
        # docstring inherited
        if self.arrow_patch is not None:
            self.arrow_patch.set_figure(fig)
        Artist.set_figure(self, fig)

    def update_positions(self, renderer):
        """
        Update the pixel positions of the annotation text and the arrow patch.
        """
        # generate transformation
        self.set_transform(self._get_xy_transform(renderer, self.anncoords))

        arrowprops = self.arrowprops
        if arrowprops is None:
            return

        bbox = Text.get_window_extent(self, renderer)

        arrow_end = x1, y1 = self._get_position_xy(renderer)  # Annotated pos.

        ms = arrowprops.get("mutation_scale", self.get_size())
        self.arrow_patch.set_mutation_scale(ms)

        if "arrowstyle" not in arrowprops:
            # Approximately simulate the YAArrow.
            shrink = arrowprops.get('shrink', 0.0)
            width = arrowprops.get('width', 4)
            headwidth = arrowprops.get('headwidth', 12)
            headlength = arrowprops.get('headlength', 12)

            # NB: ms is in pts
            stylekw = dict(head_length=headlength / ms,
                           head_width=headwidth / ms,
                           tail_width=width / ms)

            self.arrow_patch.set_arrowstyle('simple', **stylekw)

            # using YAArrow style:
            # pick the corner of the text bbox closest to annotated point.
            xpos = [(bbox.x0, 0), ((bbox.x0 + bbox.x1) / 2, 0.5), (bbox.x1, 1)]
            ypos = [(bbox.y0, 0), ((bbox.y0 + bbox.y1) / 2, 0.5), (bbox.y1, 1)]
            x, relposx = min(xpos, key=lambda v: abs(v[0] - x1))
            y, relposy = min(ypos, key=lambda v: abs(v[0] - y1))
            self._arrow_relpos = (relposx, relposy)
            r = np.hypot(y - y1, x - x1)
            shrink_pts = shrink * r / renderer.points_to_pixels(1)
            self.arrow_patch.shrinkA = self.arrow_patch.shrinkB = shrink_pts

        # adjust the starting point of the arrow relative to the textbox.
        # TODO : Rotation needs to be accounted.
        arrow_begin = bbox.p0 + bbox.size * self._arrow_relpos
        # The arrow is drawn from arrow_begin to arrow_end.  It will be first
        # clipped by patchA and patchB.  Then it will be shrunk by shrinkA and
        # shrinkB (in points).  If patchA is not set, self.bbox_patch is used.
        self.arrow_patch.set_positions(arrow_begin, arrow_end)

        if "patchA" in arrowprops:
            patchA = arrowprops["patchA"]
        elif self._bbox_patch:
            patchA = self._bbox_patch
        elif self.get_text() == "":
            patchA = None
        else:
            pad = renderer.points_to_pixels(4)
            patchA = Rectangle(
                xy=(bbox.x0 - pad / 2, bbox.y0 - pad / 2),
                width=bbox.width + pad, height=bbox.height + pad,
                transform=IdentityTransform(), clip_on=False)
        self.arrow_patch.set_patchA(patchA)

    @artist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if renderer is not None:
            self._renderer = renderer
        if not self.get_visible() or not self._check_xy(renderer):
            return
        # Update text positions before `Text.draw` would, so that the
        # FancyArrowPatch is correctly positioned.
        self.update_positions(renderer)
        self.update_bbox_position_size(renderer)
        if self.arrow_patch is not None:  # FancyArrowPatch
            if (self.arrow_patch.get_figure(root=False) is None and
                    (fig := self.get_figure(root=False)) is not None):
                self.arrow_patch.set_figure(fig)
            self.arrow_patch.draw(renderer)
        # Draw text, including FancyBboxPatch, after FancyArrowPatch.
        # Otherwise, a wedge arrowstyle can land partly on top of the Bbox.
        Text.draw(self, renderer)

    def get_window_extent(self, renderer=None):
        # docstring inherited
        # This block is the same as in Text.get_window_extent, but we need to
        # set the renderer before calling update_positions().
        if not self.get_visible() or not self._check_xy(renderer):
            return Bbox.unit()
        if renderer is not None:
            self._renderer = renderer
        if self._renderer is None:
            self._renderer = self.get_figure(root=True)._get_renderer()
        if self._renderer is None:
            raise RuntimeError('Cannot get window extent without renderer')

        self.update_positions(self._renderer)

        text_bbox = Text.get_window_extent(self)
        bboxes = [text_bbox]

        if self.arrow_patch is not None:
            bboxes.append(self.arrow_patch.get_window_extent())

        return Bbox.union(bboxes)

    def get_tightbbox(self, renderer=None):
        # docstring inherited
        if not self._check_xy(renderer):
            return Bbox.null()
        return super().get_tightbbox(renderer)


_docstring.interpd.register(Annotation=Annotation.__init__.__doc__)

# === NexusCore/openenv\Lib\site-packages\zmq\backend\cython\_zmq.py ===
# cython: language_level = 3str
# cython: freethreading_compatible = True
"""Cython backend for pyzmq"""

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

try:
    import cython

    if not cython.compiled:
        raise ImportError()
except ImportError:
    from pathlib import Path

    zmq_root = Path(__file__).parents[3]
    msg = f"""
    Attempting to import zmq Cython backend, which has not been compiled.

    This probably means you are importing zmq from its source tree.
    if this is what you want, make sure to do an in-place build first:

        pip install -e '{zmq_root}'

    If it is not, then '{zmq_root}' is probably on your sys.path,
    when it shouldn't be. Is that your current working directory?

    If neither of those is true and this file is actually installed,
    something seems to have gone wrong with the install!
    Please report at https://github.com/zeromq/pyzmq/issues
    """
    raise ImportError(msg)

import warnings
from threading import Event
from time import monotonic
from weakref import ref

import cython as C
from cython import (
    NULL,
    Py_ssize_t,
    address,
    bint,
    cast,
    cclass,
    cfunc,
    char,
    declare,
    inline,
    nogil,
    p_char,
    p_void,
    pointer,
    size_t,
    sizeof,
)
from cython.cimports.cpython.buffer import (
    Py_buffer,
    PyBUF_ANY_CONTIGUOUS,
    PyBUF_WRITABLE,
    PyBuffer_Release,
    PyObject_GetBuffer,
)
from cython.cimports.cpython.bytes import (
    PyBytes_AsString,
    PyBytes_FromStringAndSize,
    PyBytes_Size,
)
from cython.cimports.cpython.exc import PyErr_CheckSignals
from cython.cimports.libc.errno import EAGAIN, EINTR, ENAMETOOLONG, ENOENT, ENOTSOCK
from cython.cimports.libc.stdint import uint32_t
from cython.cimports.libc.stdio import fprintf
from cython.cimports.libc.stdio import stderr as cstderr
from cython.cimports.libc.stdlib import free, malloc
from cython.cimports.libc.string import memcpy
from cython.cimports.zmq.backend.cython._externs import (
    get_ipc_path_max_len,
    getpid,
    mutex_allocate,
    mutex_lock,
    mutex_t,
    mutex_unlock,
)
from cython.cimports.zmq.backend.cython.libzmq import (
    ZMQ_ENOTSOCK,
    ZMQ_ETERM,
    ZMQ_EVENT_ALL,
    ZMQ_FD,
    ZMQ_IDENTITY,
    ZMQ_IO_THREADS,
    ZMQ_LINGER,
    ZMQ_POLLIN,
    ZMQ_POLLOUT,
    ZMQ_RCVMORE,
    ZMQ_ROUTER,
    ZMQ_SNDMORE,
    ZMQ_THREAD_SAFE,
    ZMQ_TYPE,
    _zmq_version,
    fd_t,
    int64_t,
    zmq_bind,
    zmq_close,
    zmq_connect,
    zmq_ctx_destroy,
    zmq_ctx_get,
    zmq_ctx_new,
    zmq_ctx_set,
    zmq_curve_keypair,
    zmq_curve_public,
    zmq_disconnect,
    zmq_free_fn,
    zmq_getsockopt,
    zmq_has,
    zmq_join,
    zmq_leave,
    zmq_msg_close,
    zmq_msg_copy,
    zmq_msg_data,
    zmq_msg_get,
    zmq_msg_gets,
    zmq_msg_group,
    zmq_msg_init,
    zmq_msg_init_data,
    zmq_msg_init_size,
    zmq_msg_recv,
    zmq_msg_routing_id,
    zmq_msg_send,
    zmq_msg_set,
    zmq_msg_set_group,
    zmq_msg_set_routing_id,
    zmq_msg_size,
    zmq_msg_t,
    zmq_poller_add,
    zmq_poller_destroy,
    zmq_poller_fd,
    zmq_poller_new,
    zmq_pollitem_t,
    zmq_proxy,
    zmq_proxy_steerable,
    zmq_recv,
    zmq_setsockopt,
    zmq_socket,
    zmq_socket_monitor,
    zmq_strerror,
    zmq_unbind,
)
from cython.cimports.zmq.backend.cython.libzmq import zmq_errno as _zmq_errno
from cython.cimports.zmq.backend.cython.libzmq import zmq_poll as zmq_poll_c

import zmq
from zmq.constants import SocketOption, _OptType
from zmq.error import (
    Again,
    ContextTerminated,
    InterruptedSystemCall,
    ZMQError,
    _check_version,
)

IPC_PATH_MAX_LEN: int = get_ipc_path_max_len()


@cfunc
@inline
@C.exceptval(-1)
def _check_rc(rc: C.int, error_without_errno: bint = False) -> C.int:
    """internal utility for checking zmq return condition

    and raising the appropriate Exception class
    """
    errno: C.int = _zmq_errno()
    PyErr_CheckSignals()
    if errno == 0 and not error_without_errno:
        return 0
    if rc == -1:  # if rc < -1, it's a bug in libzmq. Should we warn?
        if errno == EINTR:
            raise InterruptedSystemCall(errno)
        elif errno == EAGAIN:
            raise Again(errno)
        elif errno == ZMQ_ETERM:
            raise ContextTerminated(errno)
        else:
            raise ZMQError(errno)
    return 0


# message Frame class

_zhint = C.struct(
    sock=p_void,
    mutex=pointer(mutex_t),
    id=size_t,
)


@cfunc
@nogil
def free_python_msg(data: p_void, vhint: p_void) -> C.int:
    """A pure-C function for DECREF'ing Python-owned message data.

    Sends a message on a PUSH socket

    The hint is a `zhint` struct with two values:

    sock (void *): pointer to the Garbage Collector's PUSH socket
    id (size_t): the id to be used to construct a zmq_msg_t that should be sent on a PUSH socket,
       signaling the Garbage Collector to remove its reference to the object.

    When the Garbage Collector's PULL socket receives the message,
    it deletes its reference to the object,
    allowing Python to free the memory.
    """
    msg = declare(zmq_msg_t)
    msg_ptr: pointer(zmq_msg_t) = address(msg)
    hint: pointer(_zhint) = cast(pointer(_zhint), vhint)
    rc: C.int

    if hint != NULL:
        zmq_msg_init_size(msg_ptr, sizeof(size_t))
        memcpy(zmq_msg_data(msg_ptr), address(hint.id), sizeof(size_t))
        rc = mutex_lock(hint.mutex)
        if rc != 0:
            fprintf(cstderr, "pyzmq-gc mutex lock failed rc=%d\n", rc)
        rc = zmq_msg_send(msg_ptr, hint.sock, 0)
        if rc < 0:
            # gc socket could have been closed, e.g. during process teardown.
            # If so, ignore the failure because there's nothing to do.
            if _zmq_errno() != ZMQ_ENOTSOCK:
                fprintf(
                    cstderr, "pyzmq-gc send failed: %s\n", zmq_strerror(_zmq_errno())
                )
        rc = mutex_unlock(hint.mutex)
        if rc != 0:
            fprintf(cstderr, "pyzmq-gc mutex unlock failed rc=%d\n", rc)

        zmq_msg_close(msg_ptr)
        free(hint)
        return 0


@cfunc
@inline
def _copy_zmq_msg_bytes(zmq_msg: pointer(zmq_msg_t)) -> bytes:
    """Copy the data from a zmq_msg_t"""
    data_c: p_char = NULL
    data_len_c: Py_ssize_t
    data_c = cast(p_char, zmq_msg_data(zmq_msg))
    data_len_c = zmq_msg_size(zmq_msg)
    return PyBytes_FromStringAndSize(data_c, data_len_c)


@cfunc
@inline
def _asbuffer(obj, data_c: pointer(p_void), writable: bint = False) -> size_t:
    """Get a C buffer from a memoryview"""
    pybuf = declare(Py_buffer)
    flags: C.int = PyBUF_ANY_CONTIGUOUS
    if writable:
        flags |= PyBUF_WRITABLE
    rc: C.int = PyObject_GetBuffer(obj, address(pybuf), flags)
    if rc < 0:
        raise ValueError("Couldn't create buffer")
    data_c[0] = pybuf.buf
    data_size: size_t = pybuf.len
    PyBuffer_Release(address(pybuf))
    return data_size


_gc = None


@cclass
class Frame:
    def __init__(
        self, data=None, track=False, copy=None, copy_threshold=None, **kwargs
    ):
        rc: C.int
        data_c: p_char = NULL
        data_len_c: Py_ssize_t = 0
        hint: pointer(_zhint)
        if copy_threshold is None:
            copy_threshold = zmq.COPY_THRESHOLD

        c_copy_threshold: C.size_t = 0
        if copy_threshold is not None:
            c_copy_threshold = copy_threshold

        zmq_msg_ptr: pointer(zmq_msg_t) = address(self.zmq_msg)
        # init more as False
        self.more = False

        # Save the data object in case the user wants the the data as a str.
        self._data = data
        self._failed_init = True  # bool switch for dealloc
        self._buffer = None  # buffer view of data
        self._bytes = None  # bytes copy of data

        self.tracker_event = None
        self.tracker = None
        # self.tracker should start finished
        # except in the case where we are sharing memory with libzmq
        if track:
            self.tracker = zmq._FINISHED_TRACKER

        if isinstance(data, str):
            raise TypeError("Str objects not allowed. Only: bytes, buffer interfaces.")

        if data is None:
            rc = zmq_msg_init(zmq_msg_ptr)
            _check_rc(rc)
            self._failed_init = False
            return

        data_len_c = _asbuffer(data, cast(pointer(p_void), address(data_c)))

        # copy unspecified, apply copy_threshold
        c_copy: bint = True
        if copy is None:
            if c_copy_threshold and data_len_c < c_copy_threshold:
                c_copy = True
            else:
                c_copy = False
        else:
            c_copy = copy

        if c_copy:
            # copy message data instead of sharing memory
            rc = zmq_msg_init_size(zmq_msg_ptr, data_len_c)
            _check_rc(rc)
            memcpy(zmq_msg_data(zmq_msg_ptr), data_c, data_len_c)
            self._failed_init = False
            return

        # Getting here means that we are doing a true zero-copy Frame,
        # where libzmq and Python are sharing memory.
        # Hook up garbage collection with MessageTracker and zmq_free_fn

        # Event and MessageTracker for monitoring when zmq is done with data:
        if track:
            evt = Event()
            self.tracker_event = evt
            self.tracker = zmq.MessageTracker(evt)
        # create the hint for zmq_free_fn
        # two pointers: the gc context and a message to be sent to the gc PULL socket
        # allows libzmq to signal to Python when it is done with Python-owned memory.
        global _gc
        if _gc is None:
            from zmq.utils.garbage import gc as _gc

        hint: pointer(_zhint) = cast(pointer(_zhint), malloc(sizeof(_zhint)))
        hint.id = _gc.store(data, self.tracker_event)
        if not _gc._push_mutex:
            hint.mutex = mutex_allocate()
            _gc._push_mutex = cast(size_t, hint.mutex)
        else:
            hint.mutex = cast(pointer(mutex_t), cast(size_t, _gc._push_mutex))
        hint.sock = cast(p_void, cast(size_t, _gc._push_socket.underlying))

        rc = zmq_msg_init_data(
            zmq_msg_ptr,
            cast(p_void, data_c),
            data_len_c,
            cast(pointer(zmq_free_fn), free_python_msg),
            cast(p_void, hint),
        )
        if rc != 0:
            free(hint)
            _check_rc(rc)
        self._failed_init = False

    def __dealloc__(self):
        if self._failed_init:
            return
        # decrease the 0MQ ref-count of zmq_msg
        with nogil:
            rc: C.int = zmq_msg_close(address(self.zmq_msg))
        _check_rc(rc)

    def __copy__(self):
        return self.fast_copy()

    def fast_copy(self) -> Frame:
        new_msg: Frame = Frame()
        # This does not copy the contents, but just increases the ref-count
        # of the zmq_msg by one.
        zmq_msg_copy(address(new_msg.zmq_msg), address(self.zmq_msg))
        # Copy the ref to data so the copy won't create a copy when str is
        # called.
        if self._data is not None:
            new_msg._data = self._data
        if self._buffer is not None:
            new_msg._buffer = self._buffer
        if self._bytes is not None:
            new_msg._bytes = self._bytes

        # Frame copies share the tracker and tracker_event
        new_msg.tracker_event = self.tracker_event
        new_msg.tracker = self.tracker

        return new_msg

    # buffer interface code adapted from petsc4py by Lisandro Dalcin, a BSD project

    def __getbuffer__(self, buffer: pointer(Py_buffer), flags: C.int):  # noqa: F821
        # new-style (memoryview) buffer interface
        buffer.buf = zmq_msg_data(address(self.zmq_msg))
        buffer.len = zmq_msg_size(address(self.zmq_msg))

        buffer.obj = self
        buffer.readonly = 0
        buffer.format = "B"
        buffer.ndim = 1
        buffer.shape = address(buffer.len)
        buffer.strides = NULL
        buffer.suboffsets = NULL
        buffer.itemsize = 1
        buffer.internal = NULL

    def __len__(self) -> size_t:
        """Return the length of the message in bytes."""
        sz: size_t = zmq_msg_size(address(self.zmq_msg))
        return sz

    @property
    def buffer(self):
        """A memoryview of the message contents."""
        _buffer = self._buffer and self._buffer()
        if _buffer is not None:
            return _buffer
        _buffer = memoryview(self)
        self._buffer = ref(_buffer)
        return _buffer

    @property
    def bytes(self):
        """The message content as a Python bytes object.

        The first time this property is accessed, a copy of the message
        contents is made. From then on that same copy of the message is
        returned.
        """
        if self._bytes is None:
            self._bytes = _copy_zmq_msg_bytes(address(self.zmq_msg))
        return self._bytes

    def get(self, option):
        """
        Get a Frame option or property.

        See the 0MQ API documentation for zmq_msg_get and zmq_msg_gets
        for details on specific options.

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0

        .. versionchanged:: 14.3
            add support for zmq_msg_gets (requires libzmq-4.1)
            All message properties are strings.

        .. versionchanged:: 17.0
            Added support for `routing_id` and `group`.
            Only available if draft API is enabled
            with libzmq >= 4.2.
        """
        rc: C.int = 0
        property_c: p_char = NULL

        # zmq_msg_get
        if isinstance(option, int):
            rc = zmq_msg_get(address(self.zmq_msg), option)
            _check_rc(rc)
            return rc

        if option == 'routing_id':
            routing_id: uint32_t = zmq_msg_routing_id(address(self.zmq_msg))
            if routing_id == 0:
                _check_rc(-1)
            return routing_id
        elif option == 'group':
            buf = zmq_msg_group(address(self.zmq_msg))
            if buf == NULL:
                _check_rc(-1)
            return buf.decode('utf8')

        # zmq_msg_gets
        _check_version((4, 1), "get string properties")
        if isinstance(option, str):
            option = option.encode('utf8')

        if not isinstance(option, bytes):
            raise TypeError(f"expected str, got: {option!r}")

        property_c = option

        result: p_char = cast(p_char, zmq_msg_gets(address(self.zmq_msg), property_c))
        if result == NULL:
            _check_rc(-1)
        return result.decode('utf8')

    def set(self, option, value):
        """Set a Frame option.

        See the 0MQ API documentation for zmq_msg_set
        for details on specific options.

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0
        .. versionchanged:: 17.0
            Added support for `routing_id` and `group`.
            Only available if draft API is enabled
            with libzmq >= 4.2.
        """
        rc: C.int

        if option == 'routing_id':
            routing_id: uint32_t = value
            rc = zmq_msg_set_routing_id(address(self.zmq_msg), routing_id)
            _check_rc(rc)
            return
        elif option == 'group':
            if isinstance(value, str):
                value = value.encode('utf8')
            rc = zmq_msg_set_group(address(self.zmq_msg), value)
            _check_rc(rc)
            return

        rc = zmq_msg_set(address(self.zmq_msg), option, value)
        _check_rc(rc)


@cclass
class Context:
    """
    Manage the lifecycle of a 0MQ context.

    Parameters
    ----------
    io_threads : int
        The number of IO threads.
    """

    def __init__(self, io_threads: C.int = 1, shadow: size_t = 0):
        self.handle = NULL
        self._pid = 0
        self._shadow = False

        if shadow:
            self.handle = cast(p_void, shadow)
            self._shadow = True
        else:
            self._shadow = False
            self.handle = zmq_ctx_new()

        if self.handle == NULL:
            raise ZMQError()

        rc: C.int = 0
        if not self._shadow:
            rc = zmq_ctx_set(self.handle, ZMQ_IO_THREADS, io_threads)
            _check_rc(rc)

        self.closed = False
        self._pid = getpid()

    @property
    def underlying(self):
        """The address of the underlying libzmq context"""
        return cast(size_t, self.handle)

    @cfunc
    @inline
    def _term(self) -> C.int:
        rc: C.int = 0
        if self.handle != NULL and not self.closed and getpid() == self._pid:
            with nogil:
                rc = zmq_ctx_destroy(self.handle)
        self.handle = NULL
        return rc

    def term(self):
        """
        Close or terminate the context.

        This can be called to close the context by hand. If this is not called,
        the context will automatically be closed when it is garbage collected.
        """
        rc: C.int = self._term()
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            # ignore interrupted term
            # see PEP 475 notes about close & EINTR for why
            pass

        self.closed = True

    def set(self, option: C.int, optval):
        """
        Set a context option.

        See the 0MQ API documentation for zmq_ctx_set
        for details on specific options.

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0

        Parameters
        ----------
        option : int
            The option to set.  Available values will depend on your
            version of libzmq.  Examples include::

                zmq.IO_THREADS, zmq.MAX_SOCKETS

        optval : int
            The value of the option to set.
        """
        optval_int_c: C.int
        rc: C.int

        if self.closed:
            raise RuntimeError("Context has been destroyed")

        if not isinstance(optval, int):
            raise TypeError(f'expected int, got: {optval!r}')
        optval_int_c = optval
        rc = zmq_ctx_set(self.handle, option, optval_int_c)
        _check_rc(rc)

    def get(self, option: C.int):
        """
        Get the value of a context option.

        See the 0MQ API documentation for zmq_ctx_get
        for details on specific options.

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0

        Parameters
        ----------
        option : int
            The option to get.  Available values will depend on your
            version of libzmq.  Examples include::

                zmq.IO_THREADS, zmq.MAX_SOCKETS

        Returns
        -------
        optval : int
            The value of the option as an integer.
        """
        rc: C.int

        if self.closed:
            raise RuntimeError("Context has been destroyed")

        rc = zmq_ctx_get(self.handle, option)
        _check_rc(rc, error_without_errno=False)
        return rc


@cfunc
@inline
def _c_addr(addr) -> p_char:
    if isinstance(addr, str):
        addr = addr.encode('utf-8')
    try:
        c_addr: p_char = addr
    except TypeError:
        raise TypeError(f"Expected addr to be str, got addr={addr!r}")
    return c_addr


@cclass
class Socket:
    """
    A 0MQ socket.

    These objects will generally be constructed via the socket() method of a Context object.

    Note: 0MQ Sockets are *not* threadsafe. **DO NOT** share them across threads.

    Parameters
    ----------
    context : Context
        The 0MQ Context this Socket belongs to.
    socket_type : int
        The socket type, which can be any of the 0MQ socket types:
        REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, XPUB, XSUB.

    See Also
    --------
    .Context.socket : method for creating a socket bound to a Context.
    """

    def __init__(
        self,
        context=None,
        socket_type: C.int = -1,
        shadow: size_t = 0,
        copy_threshold=None,
    ):
        # pre-init
        self.handle = NULL
        self._draft_poller = NULL
        self._pid = 0
        self._shadow = False
        self.context = None

        if copy_threshold is None:
            copy_threshold = zmq.COPY_THRESHOLD
        self.copy_threshold = copy_threshold

        self.handle = NULL
        self.context = context
        if shadow:
            self._shadow = True
            self.handle = cast(p_void, shadow)
        else:
            if context is None:
                raise TypeError("context must be specified")
            if socket_type < 0:
                raise TypeError("socket_type must be specified")
            self._shadow = False
            self.handle = zmq_socket(self.context.handle, socket_type)
        if self.handle == NULL:
            raise ZMQError()
        self._closed = False
        self._pid = getpid()

    @property
    def underlying(self):
        """The address of the underlying libzmq socket"""
        return cast(size_t, self.handle)

    @property
    def closed(self):
        """Whether the socket is closed"""
        return _check_closed_deep(self)

    def close(self, linger: int | None = None):
        """
        Close the socket.

        If linger is specified, LINGER sockopt will be set prior to closing.

        This can be called to close the socket by hand. If this is not
        called, the socket will automatically be closed when it is
        garbage collected.
        """
        rc: C.int = 0
        linger_c: C.int
        setlinger: bint = False

        if linger is not None:
            linger_c = linger
            setlinger = True

        if self.handle != NULL and not self._closed and getpid() == self._pid:
            if setlinger:
                zmq_setsockopt(self.handle, ZMQ_LINGER, address(linger_c), sizeof(int))

            # teardown draft poller
            if self._draft_poller != NULL:
                zmq_poller_destroy(address(self._draft_poller))
                self._draft_poller = NULL

            rc = zmq_close(self.handle)
            if rc < 0 and _zmq_errno() != ENOTSOCK:
                # ignore ENOTSOCK (closed by Context)
                _check_rc(rc)
            self._closed = True
            self.handle = NULL

    def set(self, option: C.int, optval):
        """
        Set socket options.

        See the 0MQ API documentation for details on specific options.

        Parameters
        ----------
        option : int
            The option to set.  Available values will depend on your
            version of libzmq.  Examples include::

                zmq.SUBSCRIBE, UNSUBSCRIBE, IDENTITY, HWM, LINGER, FD

        optval : int or bytes
            The value of the option to set.

        Notes
        -----
        .. warning::

            All options other than zmq.SUBSCRIBE, zmq.UNSUBSCRIBE and
            zmq.LINGER only take effect for subsequent socket bind/connects.
        """
        optval_int64_c: int64_t
        optval_int_c: C.int
        optval_c: p_char
        sz: Py_ssize_t

        _check_closed(self)
        if isinstance(optval, str):
            raise TypeError("unicode not allowed, use setsockopt_string")

        try:
            sopt = SocketOption(option)
        except ValueError:
            # unrecognized option,
            # assume from the future,
            # let EINVAL raise
            opt_type = _OptType.int
        else:
            opt_type = sopt._opt_type

        if opt_type == _OptType.bytes:
            if not isinstance(optval, bytes):
                raise TypeError(f'expected bytes, got: {optval!r}')
            optval_c = PyBytes_AsString(optval)
            sz = PyBytes_Size(optval)
            _setsockopt(self.handle, option, optval_c, sz)
        elif opt_type == _OptType.int64:
            if not isinstance(optval, int):
                raise TypeError(f'expected int, got: {optval!r}')
            optval_int64_c = optval
            _setsockopt(self.handle, option, address(optval_int64_c), sizeof(int64_t))
        else:
            # default is to assume int, which is what most new sockopts will be
            # this lets pyzmq work with newer libzmq which may add constants
            # pyzmq has not yet added, rather than artificially raising. Invalid
            # sockopts will still raise just the same, but it will be libzmq doing
            # the raising.
            if not isinstance(optval, int):
                raise TypeError(f'expected int, got: {optval!r}')
            optval_int_c = optval
            _setsockopt(self.handle, option, address(optval_int_c), sizeof(int))

    def get(self, option: C.int):
        """
        Get the value of a socket option.

        See the 0MQ API documentation for details on specific options.

        .. versionchanged:: 27
            Added experimental support for ZMQ_FD for draft sockets via `zmq_poller_fd`.
            Requires libzmq >=4.3.2 built with draft support.

        Parameters
        ----------
        option : int
            The option to get.  Available values will depend on your
            version of libzmq.  Examples include::

                zmq.IDENTITY, HWM, LINGER, FD, EVENTS

        Returns
        -------
        optval : int or bytes
            The value of the option as a bytestring or int.
        """
        optval_int64_c = declare(int64_t)
        optval_int_c = declare(C.int)
        optval_fd_c = declare(fd_t)
        identity_str_c = declare(char[255])
        sz: size_t

        _check_closed(self)

        try:
            sopt = SocketOption(option)
        except ValueError:
            # unrecognized option,
            # assume from the future,
            # let EINVAL raise
            opt_type = _OptType.int
        else:
            opt_type = sopt._opt_type

        if opt_type == _OptType.bytes:
            sz = 255
            _getsockopt(self.handle, option, cast(p_void, identity_str_c), address(sz))
            # strip null-terminated strings *except* identity
            if (
                option != ZMQ_IDENTITY
                and sz > 0
                and (cast(p_char, identity_str_c))[sz - 1] == b'\0'
            ):
                sz -= 1
            result = PyBytes_FromStringAndSize(cast(p_char, identity_str_c), sz)
        elif opt_type == _OptType.int64:
            sz = sizeof(int64_t)
            _getsockopt(
                self.handle, option, cast(p_void, address(optval_int64_c)), address(sz)
            )
            result = optval_int64_c
        elif option == ZMQ_FD and self._draft_poller != NULL:
            # draft sockets use FD of a draft zmq_poller as proxy
            rc = zmq_poller_fd(self._draft_poller, address(optval_fd_c))
            _check_rc(rc)
            result = optval_fd_c
        elif opt_type == _OptType.fd:
            sz = sizeof(fd_t)
            try:
                _getsockopt(
                    self.handle, option, cast(p_void, address(optval_fd_c)), address(sz)
                )
            except ZMQError as e:
                # threadsafe sockets don't support ZMQ_FD (yet!)
                # fallback on zmq_poller_fd as proxy with the same behavior
                # until libzmq fixes this.
                # if upstream fixes it, this branch will never be taken
                if (
                    option == ZMQ_FD
                    and e.errno == zmq.Errno.EINVAL
                    and self.get(ZMQ_THREAD_SAFE)
                ):
                    _check_version(
                        (4, 3, 2), "draft socket FD support via zmq_poller_fd"
                    )
                    if not zmq.has('draft'):
                        raise RuntimeError("libzmq must be built with draft support")
                    warnings.warn(zmq.error.DraftFDWarning(), stacklevel=2)

                    # create a poller and retrieve its fd
                    self._draft_poller = zmq_poller_new()
                    if self._draft_poller == NULL:
                        # failed (why?), raise original error
                        raise
                    # register self with poller
                    rc = zmq_poller_add(
                        self._draft_poller, self.handle, NULL, ZMQ_POLLIN | ZMQ_POLLOUT
                    )
                    _check_rc(rc)
                    # use poller fd as proxy for ours
                    rc = zmq_poller_fd(self._draft_poller, address(optval_fd_c))
                    _check_rc(rc)
                else:
                    raise
            result = optval_fd_c
        else:
            # default is to assume int, which is what most new sockopts will be
            # this lets pyzmq work with newer libzmq which may add constants
            # pyzmq has not yet added, rather than artificially raising. Invalid
            # sockopts will still raise just the same, but it will be libzmq doing
            # the raising.
            sz = sizeof(int)
            _getsockopt(
                self.handle, option, cast(p_void, address(optval_int_c)), address(sz)
            )
            result = optval_int_c

        return result

    def bind(self, addr: str | bytes):
        """
        Bind the socket to an address.

        This causes the socket to listen on a network port. Sockets on the
        other side of this connection will use ``Socket.connect(addr)`` to
        connect to this socket.

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported include
            tcp, udp, pgm, epgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.
        """
        c_addr: p_char = _c_addr(addr)
        _check_closed(self)
        rc: C.int = zmq_bind(self.handle, c_addr)
        if rc != 0:
            _errno: C.int = _zmq_errno()
            _ipc_max: C.int = get_ipc_path_max_len()
            if _ipc_max and _errno == ENAMETOOLONG:
                path = addr.split('://', 1)[-1]
                msg = (
                    f'ipc path "{path}" is longer than {_ipc_max} '
                    'characters (sizeof(sockaddr_un.sun_path)). '
                    'zmq.IPC_PATH_MAX_LEN constant can be used '
                    'to check addr length (if it is defined).'
                )
                raise ZMQError(msg=msg)
            elif _errno == ENOENT:
                path = addr.split('://', 1)[-1]
                msg = f'No such file or directory for ipc path "{path}".'
                raise ZMQError(msg=msg)
        while True:
            try:
                _check_rc(rc)
            except InterruptedSystemCall:
                rc = zmq_bind(self.handle, c_addr)
                continue
            else:
                break

    def connect(self, addr: str | bytes) -> None:
        """
        Connect to a remote 0MQ socket.

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported are
            tcp, udp, pgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.
        """
        rc: C.int
        c_addr: p_char = _c_addr(addr)
        _check_closed(self)

        while True:
            try:
                rc = zmq_connect(self.handle, c_addr)
                _check_rc(rc)
            except InterruptedSystemCall:
                # retry syscall
                continue
            else:
                break

    def unbind(self, addr: str | bytes):
        """
        Unbind from an address (undoes a call to bind).

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported are
            tcp, udp, pgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.
        """
        c_addr: p_char = _c_addr(addr)
        _check_closed(self)
        rc: C.int = zmq_unbind(self.handle, c_addr)
        if rc != 0:
            raise ZMQError()

    def disconnect(self, addr: str | bytes):
        """
        Disconnect from a remote 0MQ socket (undoes a call to connect).

        .. versionadded:: libzmq-3.2
        .. versionadded:: 13.0

        Parameters
        ----------
        addr : str
            The address string. This has the form 'protocol://interface:port',
            for example 'tcp://127.0.0.1:5555'. Protocols supported are
            tcp, udp, pgm, inproc and ipc. If the address is unicode, it is
            encoded to utf-8 first.
        """
        c_addr: p_char = _c_addr(addr)
        _check_closed(self)

        rc: C.int = zmq_disconnect(self.handle, c_addr)
        if rc != 0:
            raise ZMQError()

    def monitor(self, addr: str | bytes | None, events: C.int = ZMQ_EVENT_ALL):
        """
        Start publishing socket events on inproc.
        See libzmq docs for zmq_monitor for details.

        While this function is available from libzmq 3.2,
        pyzmq cannot parse monitor messages from libzmq prior to 4.0.

        .. versionadded: libzmq-3.2
        .. versionadded: 14.0

        Parameters
        ----------
        addr : str | None
            The inproc url used for monitoring. Passing None as
            the addr will cause an existing socket monitor to be
            deregistered.
        events : int
            default: zmq.EVENT_ALL
            The zmq event bitmask for which events will be sent to the monitor.
        """
        c_addr: p_char = NULL
        if addr is not None:
            c_addr = _c_addr(addr)
        _check_closed(self)

        _check_rc(zmq_socket_monitor(self.handle, c_addr, events))

    def join(self, group: str | bytes):
        """
        Join a RADIO-DISH group

        Only for DISH sockets.

        libzmq and pyzmq must have been built with ZMQ_BUILD_DRAFT_API

        .. versionadded:: 17
        """
        _check_version((4, 2), "RADIO-DISH")
        if not zmq.has('draft'):
            raise RuntimeError("libzmq must be built with draft support")
        if isinstance(group, str):
            group = group.encode('utf8')
        c_group: bytes = group
        rc: C.int = zmq_join(self.handle, c_group)
        _check_rc(rc)

    def leave(self, group):
        """
        Leave a RADIO-DISH group

        Only for DISH sockets.

        libzmq and pyzmq must have been built with ZMQ_BUILD_DRAFT_API

        .. versionadded:: 17
        """
        _check_version((4, 2), "RADIO-DISH")
        if not zmq.has('draft'):
            raise RuntimeError("libzmq must be built with draft support")
        rc: C.int = zmq_leave(self.handle, group)
        _check_rc(rc)

    def send(self, data, flags=0, copy: bint = True, track: bint = False):
        """
        Send a single zmq message frame on this socket.

        This queues the message to be sent by the IO thread at a later time.

        With flags=NOBLOCK, this raises :class:`ZMQError` if the queue is full;
        otherwise, this waits until space is available.
        See :class:`Poller` for more general non-blocking I/O.

        Parameters
        ----------
        data : bytes, Frame, memoryview
            The content of the message. This can be any object that provides
            the Python buffer API (`memoryview(data)` can be called).
        flags : int
            0, NOBLOCK, SNDMORE, or NOBLOCK|SNDMORE.
        copy : bool
            Should the message be sent in a copying or non-copying manner.
        track : bool
            Should the message be tracked for notification that ZMQ has
            finished with it? (ignored if copy=True)

        Returns
        -------
        None : if `copy` or not track
            None if message was sent, raises an exception otherwise.
        MessageTracker : if track and not copy
            a MessageTracker object, whose `done` property will
            be False until the send is completed.

        Raises
        ------
        TypeError
            If a unicode object is passed
        ValueError
            If `track=True`, but an untracked Frame is passed.
        ZMQError
            for any of the reasons zmq_msg_send might fail (including
            if NOBLOCK is set and the outgoing queue is full).

        """
        _check_closed(self)

        if isinstance(data, str):
            raise TypeError("unicode not allowed, use send_string")

        if copy and not isinstance(data, Frame):
            return _send_copy(self.handle, data, flags)
        else:
            if isinstance(data, Frame):
                if track and not data.tracker:
                    raise ValueError('Not a tracked message')
                msg = data
            else:
                if self.copy_threshold:
                    buf = memoryview(data)
                    nbytes: size_t = buf.nbytes
                    copy_threshold: size_t = self.copy_threshold
                    # always copy messages smaller than copy_threshold
                    if nbytes < copy_threshold:
                        _send_copy(self.handle, buf, flags)
                        return zmq._FINISHED_TRACKER
                msg = Frame(data, track=track, copy_threshold=self.copy_threshold)
            return _send_frame(self.handle, msg, flags)

    def recv(self, flags=0, copy: bint = True, track: bint = False):
        """
        Receive a message.

        With flags=NOBLOCK, this raises :class:`ZMQError` if no messages have
        arrived; otherwise, this waits until a message arrives.
        See :class:`Poller` for more general non-blocking I/O.

        Parameters
        ----------
        flags : int
            0 or NOBLOCK.
        copy : bool
            Should the message be received in a copying or non-copying manner?
            If False a Frame object is returned, if True a string copy of
            message is returned.
        track : bool
            Should the message be tracked for notification that ZMQ has
            finished with it? (ignored if copy=True)

        Returns
        -------
        msg : bytes or Frame
            The received message frame.  If `copy` is False, then it will be a Frame,
            otherwise it will be bytes.

        Raises
        ------
        ZMQError
            for any of the reasons zmq_msg_recv might fail (including if
            NOBLOCK is set and no new messages have arrived).
        """
        _check_closed(self)

        if copy:
            return _recv_copy(self.handle, flags)
        else:
            frame = _recv_frame(self.handle, flags, track)
            more: bint = False
            sz: size_t = sizeof(bint)
            _getsockopt(
                self.handle, ZMQ_RCVMORE, cast(p_void, address(more)), address(sz)
            )
            frame.more = more
            return frame

    def recv_into(self, buffer, /, *, nbytes=0, flags=0) -> C.int:
        """
        Receive up to nbytes bytes from the socket,
        storing the data into a buffer rather than allocating a new Frame.

        The next message frame can be discarded by receiving into an empty buffer::

            sock.recv_into(bytearray())

        .. versionadded:: 26.4

        Parameters
        ----------
        buffer : memoryview
            Any object providing the buffer interface (i.e. `memoryview(buffer)` works),
            where the memoryview is contiguous and writable.
        nbytes: int, default=0
            The maximum number of bytes to receive.
            If nbytes is not specified (or 0), receive up to the size available in the given buffer.
            If the next frame is larger than this, the frame will be truncated and message content discarded.
        flags: int, default=0
            See `socket.recv`

        Returns
        -------
        bytes_received: int
            Returns the number of bytes received.
            This is always the size of the received frame.
            If the returned `bytes_received` is larger than `nbytes` (or size of `buffer` if `nbytes=0`),
            the message has been truncated and the rest of the frame discarded.
            Truncated data cannot be recovered.

        Raises
        ------
        ZMQError
            for any of the reasons `zmq_recv` might fail.
        BufferError
            for invalid buffers, such as readonly or not contiguous.
        """
        c_flags: C.int = flags
        _check_closed(self)
        c_nbytes: size_t = nbytes
        if c_nbytes < 0:
            raise ValueError(f"{nbytes=} must be non-negative")
        view = memoryview(buffer)
        c_data = declare(pointer(C.void))
        view_bytes: C.size_t = _asbuffer(view, address(c_data), True)
        if nbytes == 0:
            c_nbytes = view_bytes
        elif c_nbytes > view_bytes:
            raise ValueError(f"{nbytes=} too big for memoryview of {view_bytes}B")

        # call zmq_recv, with retries
        while True:
            with nogil:
                rc: C.int = zmq_recv(self.handle, c_data, c_nbytes, c_flags)
            try:
                _check_rc(rc)
            except InterruptedSystemCall:
                continue
            else:
                return rc


# inline socket methods


@inline
@cfunc
def _check_closed(s: Socket):
    """raise ENOTSUP if socket is closed

    Does not do a deep check
    """
    if s._closed:
        raise ZMQError(ENOTSOCK)


@inline
@cfunc
def _check_closed_deep(s: Socket) -> bint:
    """thorough check of whether the socket has been closed,
    even if by another entity (e.g. ctx.destroy).

    Only used by the `closed` property.

    returns True if closed, False otherwise
    """
    rc: C.int
    errno: C.int
    stype = declare(C.int)
    sz: size_t = sizeof(int)

    if s._closed:
        return True
    else:
        rc = zmq_getsockopt(
            s.handle, ZMQ_TYPE, cast(p_void, address(stype)), address(sz)
        )
        if rc < 0:
            errno = _zmq_errno()
            if errno == ENOTSOCK:
                s._closed = True
                return True
            elif errno == ZMQ_ETERM:
                # don't raise ETERM when checking if we're closed
                return False
        else:
            _check_rc(rc)
    return False


@cfunc
@inline
def _recv_frame(handle: p_void, flags: C.int = 0, track: bint = False) -> Frame:
    """Receive a message in a non-copying manner and return a Frame."""
    rc: C.int
    msg = zmq.Frame(track=track)
    cmsg: Frame = msg

    while True:
        with nogil:
            rc = zmq_msg_recv(address(cmsg.zmq_msg), handle, flags)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break
    return msg


@cfunc
@inline
def _recv_copy(handle: p_void, flags: C.int = 0):
    """Receive a message and return a copy"""
    zmq_msg = declare(zmq_msg_t)
    zmq_msg_p: pointer(zmq_msg_t) = address(zmq_msg)
    rc: C.int = zmq_msg_init(zmq_msg_p)
    _check_rc(rc)
    while True:
        with nogil:
            rc = zmq_msg_recv(zmq_msg_p, handle, flags)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        except Exception:
            zmq_msg_close(zmq_msg_p)  # ensure msg is closed on failure
            raise
        else:
            break

    msg_bytes = _copy_zmq_msg_bytes(zmq_msg_p)
    zmq_msg_close(zmq_msg_p)
    return msg_bytes


@cfunc
@inline
def _send_frame(handle: p_void, msg: Frame, flags: C.int = 0):
    """Send a Frame on this socket in a non-copy manner."""
    rc: C.int
    msg_copy: Frame

    # Always copy so the original message isn't garbage collected.
    # This doesn't do a real copy, just a reference.
    msg_copy = msg.fast_copy()

    while True:
        with nogil:
            rc = zmq_msg_send(address(msg_copy.zmq_msg), handle, flags)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break

    return msg.tracker


@cfunc
@inline
def _send_copy(handle: p_void, buf, flags: C.int = 0):
    """Send a message on this socket by copying its content."""
    rc: C.int
    msg = declare(zmq_msg_t)
    c_bytes = declare(p_void)

    # copy to c array:
    c_bytes_len = _asbuffer(buf, address(c_bytes))

    # Copy the msg before sending. This avoids any complications with
    # the GIL, etc.
    # If zmq_msg_init_* fails we must not call zmq_msg_close (Bus Error)
    rc = zmq_msg_init_size(address(msg), c_bytes_len)
    _check_rc(rc)

    while True:
        with nogil:
            memcpy(zmq_msg_data(address(msg)), c_bytes, zmq_msg_size(address(msg)))
            rc = zmq_msg_send(address(msg), handle, flags)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        except Exception:
            zmq_msg_close(address(msg))  # close the unused msg
            raise  # raise original exception
        else:
            rc = zmq_msg_close(address(msg))
            _check_rc(rc)
            break


@cfunc
@inline
def _getsockopt(handle: p_void, option: C.int, optval: p_void, sz: pointer(size_t)):
    """getsockopt, retrying interrupted calls

    checks rc, raising ZMQError on failure.
    """
    rc: C.int = 0
    while True:
        rc = zmq_getsockopt(handle, option, optval, sz)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break


@cfunc
@inline
def _setsockopt(handle: p_void, option: C.int, optval: p_void, sz: size_t):
    """setsockopt, retrying interrupted calls

    checks rc, raising ZMQError on failure.
    """
    rc: C.int = 0
    while True:
        rc = zmq_setsockopt(handle, option, optval, sz)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break


# General utility functions


def zmq_errno() -> C.int:
    """Return the integer errno of the most recent zmq error."""
    return _zmq_errno()


def strerror(errno: C.int) -> str:
    """
    Return the error string given the error number.
    """
    str_e: bytes = zmq_strerror(errno)
    return str_e.decode("utf8", "replace")


def zmq_version_info() -> tuple[int, int, int]:
    """Return the version of ZeroMQ itself as a 3-tuple of ints."""
    major: C.int = 0
    minor: C.int = 0
    patch: C.int = 0
    _zmq_version(address(major), address(minor), address(patch))
    return (major, minor, patch)


def has(capability: str) -> bool:
    """Check for zmq capability by name (e.g. 'ipc', 'curve')

    .. versionadded:: libzmq-4.1
    .. versionadded:: 14.1
    """
    _check_version((4, 1), 'zmq.has')
    ccap: bytes = capability.encode('utf8')
    return bool(zmq_has(ccap))


def curve_keypair() -> tuple[bytes, bytes]:
    """generate a Z85 key pair for use with zmq.CURVE security

    Requires libzmq (≥ 4.0) to have been built with CURVE support.

    .. versionadded:: libzmq-4.0
    .. versionadded:: 14.0

    Returns
    -------
    public: bytes
        The public key as 40 byte z85-encoded bytestring.
    private: bytes
        The private key as 40 byte z85-encoded bytestring.
    """
    rc: C.int
    public_key = declare(char[64])
    secret_key = declare(char[64])
    _check_version((4, 0), "curve_keypair")
    # see huge comment in libzmq/src/random.cpp
    # about threadsafety of random initialization
    rc = zmq_curve_keypair(public_key, secret_key)
    _check_rc(rc)
    return public_key, secret_key


def curve_public(secret_key) -> bytes:
    """Compute the public key corresponding to a secret key for use
    with zmq.CURVE security

    Requires libzmq (≥ 4.2) to have been built with CURVE support.

    Parameters
    ----------
    private
        The private key as a 40 byte z85-encoded bytestring

    Returns
    -------
    bytes
        The public key as a 40 byte z85-encoded bytestring
    """
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf8')
    if not len(secret_key) == 40:
        raise ValueError('secret key must be a 40 byte z85 encoded string')

    rc: C.int
    public_key = declare(char[64])
    c_secret_key: pointer(char) = secret_key
    _check_version((4, 2), "curve_public")
    # see huge comment in libzmq/src/random.cpp
    # about threadsafety of random initialization
    rc = zmq_curve_public(public_key, c_secret_key)
    _check_rc(rc)
    return public_key[:40]


# polling
def zmq_poll(sockets, timeout: C.int = -1):
    """zmq_poll(sockets, timeout=-1)

    Poll a set of 0MQ sockets, native file descs. or sockets.

    Parameters
    ----------
    sockets : list of tuples of (socket, flags)
        Each element of this list is a two-tuple containing a socket
        and a flags. The socket may be a 0MQ socket or any object with
        a ``fileno()`` method. The flags can be zmq.POLLIN (for detecting
        for incoming messages), zmq.POLLOUT (for detecting that send is OK)
        or zmq.POLLIN|zmq.POLLOUT for detecting both.
    timeout : int
        The number of milliseconds to poll for. Negative means no timeout.
    """
    rc: C.int
    i: C.int
    fileno: fd_t
    events: C.int
    pollitems: pointer(zmq_pollitem_t) = NULL
    nsockets: C.int = len(sockets)

    if nsockets == 0:
        return []

    pollitems = cast(pointer(zmq_pollitem_t), malloc(nsockets * sizeof(zmq_pollitem_t)))
    if pollitems == NULL:
        raise MemoryError("Could not allocate poll items")

    for i in range(nsockets):
        s, events = sockets[i]
        if isinstance(s, Socket):
            pollitems[i].socket = cast(Socket, s).handle
            pollitems[i].fd = 0
            pollitems[i].events = events
            pollitems[i].revents = 0
        elif isinstance(s, int):
            fileno = s
            pollitems[i].socket = NULL
            pollitems[i].fd = fileno
            pollitems[i].events = events
            pollitems[i].revents = 0
        elif hasattr(s, 'fileno'):
            try:
                fileno = int(s.fileno())
            except Exception:
                free(pollitems)
                raise ValueError('fileno() must return a valid integer fd')
            else:
                pollitems[i].socket = NULL
                pollitems[i].fd = fileno
                pollitems[i].events = events
                pollitems[i].revents = 0
        else:
            free(pollitems)
            raise TypeError(
                "Socket must be a 0MQ socket, an integer fd or have "
                f"a fileno() method: {s!r}"
            )

    ms_passed: C.int = 0
    tic: C.int
    try:
        while True:
            start: C.int = monotonic()
            with nogil:
                rc = zmq_poll_c(pollitems, nsockets, timeout)
            try:
                _check_rc(rc)
            except InterruptedSystemCall:
                if timeout > 0:
                    tic = monotonic()
                    ms_passed = int(1000 * (tic - start))
                    if ms_passed < 0:
                        # don't allow negative ms_passed,
                        # which can happen on old Python versions without time.monotonic.
                        warnings.warn(
                            f"Negative elapsed time for interrupted poll: {ms_passed}."
                            "  Did the clock change?",
                            RuntimeWarning,
                        )
                        # treat this case the same as no time passing,
                        # since it should be rare and not happen twice in a row.
                        ms_passed = 0
                    timeout = max(0, timeout - ms_passed)
                continue
            else:
                break
    except Exception:
        free(pollitems)
        raise

    results = []
    for i in range(nsockets):
        revents = pollitems[i].revents
        # for compatibility with select.poll:
        # - only return sockets with non-zero status
        # - return the fd for plain sockets
        if revents > 0:
            if pollitems[i].socket != NULL:
                s = sockets[i][0]
            else:
                s = pollitems[i].fd
            results.append((s, revents))

    free(pollitems)
    return results


def proxy(frontend: Socket, backend: Socket, capture: Socket = None):
    """
    Start a zeromq proxy (replacement for device).

    .. versionadded:: libzmq-3.2
    .. versionadded:: 13.0

    Parameters
    ----------
    frontend : Socket
        The Socket instance for the incoming traffic.
    backend : Socket
        The Socket instance for the outbound traffic.
    capture : Socket (optional)
        The Socket instance for capturing traffic.
    """
    rc: C.int = 0
    capture_handle: p_void
    if isinstance(capture, Socket):
        capture_handle = capture.handle
    else:
        capture_handle = NULL
    while True:
        with nogil:
            rc = zmq_proxy(frontend.handle, backend.handle, capture_handle)
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break
    return rc


def proxy_steerable(
    frontend: Socket,
    backend: Socket,
    capture: Socket = None,
    control: Socket = None,
):
    """
    Start a zeromq proxy with control flow.

    .. versionadded:: libzmq-4.1
    .. versionadded:: 18.0

    Parameters
    ----------
    frontend : Socket
        The Socket instance for the incoming traffic.
    backend : Socket
        The Socket instance for the outbound traffic.
    capture : Socket (optional)
        The Socket instance for capturing traffic.
    control : Socket (optional)
        The Socket instance for control flow.
    """
    rc: C.int = 0
    capture_handle: p_void
    if isinstance(capture, Socket):
        capture_handle = capture.handle
    else:
        capture_handle = NULL
    if isinstance(control, Socket):
        control_handle = control.handle
    else:
        control_handle = NULL
    while True:
        with nogil:
            rc = zmq_proxy_steerable(
                frontend.handle, backend.handle, capture_handle, control_handle
            )
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break
    return rc


# monitored queue - like proxy (predates libzmq proxy)
# but supports ROUTER-ROUTER devices
@cfunc
@inline
@nogil
def _mq_relay(
    in_socket: p_void,
    out_socket: p_void,
    side_socket: p_void,
    msg: zmq_msg_t,
    side_msg: zmq_msg_t,
    id_msg: zmq_msg_t,
    swap_ids: bint,
) -> C.int:
    rc: C.int
    flags: C.int
    flagsz = declare(size_t)
    more = declare(int)
    flagsz = sizeof(int)

    if swap_ids:  # both router, must send second identity first
        # recv two ids into msg, id_msg
        rc = zmq_msg_recv(address(msg), in_socket, 0)
        if rc < 0:
            return rc

        rc = zmq_msg_recv(address(id_msg), in_socket, 0)
        if rc < 0:
            return rc

        # send second id (id_msg) first
        # !!!! always send a copy before the original !!!!
        rc = zmq_msg_copy(address(side_msg), address(id_msg))
        if rc < 0:
            return rc
        rc = zmq_msg_send(address(side_msg), out_socket, ZMQ_SNDMORE)
        if rc < 0:
            return rc
        rc = zmq_msg_send(address(id_msg), side_socket, ZMQ_SNDMORE)
        if rc < 0:
            return rc
        # send first id (msg) second
        rc = zmq_msg_copy(address(side_msg), address(msg))
        if rc < 0:
            return rc
        rc = zmq_msg_send(address(side_msg), out_socket, ZMQ_SNDMORE)
        if rc < 0:
            return rc
        rc = zmq_msg_send(address(msg), side_socket, ZMQ_SNDMORE)
        if rc < 0:
            return rc
    while True:
        rc = zmq_msg_recv(address(msg), in_socket, 0)
        if rc < 0:
            return rc
        # assert (rc == 0)
        rc = zmq_getsockopt(in_socket, ZMQ_RCVMORE, address(more), address(flagsz))
        if rc < 0:
            return rc
        flags = 0
        if more:
            flags |= ZMQ_SNDMORE

        rc = zmq_msg_copy(address(side_msg), address(msg))
        if rc < 0:
            return rc
        if flags:
            rc = zmq_msg_send(address(side_msg), out_socket, flags)
            if rc < 0:
                return rc
            # only SNDMORE for side-socket
            rc = zmq_msg_send(address(msg), side_socket, ZMQ_SNDMORE)
            if rc < 0:
                return rc
        else:
            rc = zmq_msg_send(address(side_msg), out_socket, 0)
            if rc < 0:
                return rc
            rc = zmq_msg_send(address(msg), side_socket, 0)
            if rc < 0:
                return rc
            break
    return rc


@cfunc
@inline
@nogil
def _mq_inline(
    in_socket: p_void,
    out_socket: p_void,
    side_socket: p_void,
    in_msg_ptr: pointer(zmq_msg_t),
    out_msg_ptr: pointer(zmq_msg_t),
    swap_ids: bint,
) -> C.int:
    """
    inner C function for monitored_queue
    """

    msg: zmq_msg_t = declare(zmq_msg_t)
    rc: C.int = zmq_msg_init(address(msg))
    id_msg = declare(zmq_msg_t)
    rc = zmq_msg_init(address(id_msg))
    if rc < 0:
        return rc
    side_msg = declare(zmq_msg_t)
    rc = zmq_msg_init(address(side_msg))
    if rc < 0:
        return rc

    items = declare(zmq_pollitem_t[2])
    items[0].socket = in_socket
    items[0].events = ZMQ_POLLIN
    items[0].fd = items[0].revents = 0
    items[1].socket = out_socket
    items[1].events = ZMQ_POLLIN
    items[1].fd = items[1].revents = 0

    while True:
        # wait for the next message to process
        rc = zmq_poll_c(address(items[0]), 2, -1)
        if rc < 0:
            return rc
        if items[0].revents & ZMQ_POLLIN:
            # send in_prefix to side socket
            rc = zmq_msg_copy(address(side_msg), in_msg_ptr)
            if rc < 0:
                return rc
            rc = zmq_msg_send(address(side_msg), side_socket, ZMQ_SNDMORE)
            if rc < 0:
                return rc
            # relay the rest of the message
            rc = _mq_relay(
                in_socket, out_socket, side_socket, msg, side_msg, id_msg, swap_ids
            )
            if rc < 0:
                return rc
        if items[1].revents & ZMQ_POLLIN:
            # send out_prefix to side socket
            rc = zmq_msg_copy(address(side_msg), out_msg_ptr)
            if rc < 0:
                return rc
            rc = zmq_msg_send(address(side_msg), side_socket, ZMQ_SNDMORE)
            if rc < 0:
                return rc
            # relay the rest of the message
            rc = _mq_relay(
                out_socket, in_socket, side_socket, msg, side_msg, id_msg, swap_ids
            )
            if rc < 0:
                return rc
    return rc


def monitored_queue(
    in_socket: Socket,
    out_socket: Socket,
    mon_socket: Socket,
    in_prefix: bytes = b'in',
    out_prefix: bytes = b'out',
):
    """
    Start a monitored queue device.

    A monitored queue is very similar to the zmq.proxy device (monitored queue came first).

    Differences from zmq.proxy:

    - monitored_queue supports both in and out being ROUTER sockets
      (via swapping IDENTITY prefixes).
    - monitor messages are prefixed, making in and out messages distinguishable.

    Parameters
    ----------
    in_socket : zmq.Socket
        One of the sockets to the Queue. Its messages will be prefixed with
        'in'.
    out_socket : zmq.Socket
        One of the sockets to the Queue. Its messages will be prefixed with
        'out'. The only difference between in/out socket is this prefix.
    mon_socket : zmq.Socket
        This socket sends out every message received by each of the others
        with an in/out prefix specifying which one it was.
    in_prefix : str
        Prefix added to broadcast messages from in_socket.
    out_prefix : str
        Prefix added to broadcast messages from out_socket.
    """
    ins: p_void = in_socket.handle
    outs: p_void = out_socket.handle
    mons: p_void = mon_socket.handle
    in_msg = declare(zmq_msg_t)
    out_msg = declare(zmq_msg_t)
    swap_ids: bint
    msg_c: p_void = NULL
    msg_c_len = declare(Py_ssize_t)
    rc: C.int

    # force swap_ids if both ROUTERs
    swap_ids = in_socket.type == ZMQ_ROUTER and out_socket.type == ZMQ_ROUTER

    # build zmq_msg objects from str prefixes
    msg_c_len = _asbuffer(in_prefix, address(msg_c))
    rc = zmq_msg_init_size(address(in_msg), msg_c_len)
    _check_rc(rc)

    memcpy(zmq_msg_data(address(in_msg)), msg_c, zmq_msg_size(address(in_msg)))

    msg_c_len = _asbuffer(out_prefix, address(msg_c))

    rc = zmq_msg_init_size(address(out_msg), msg_c_len)
    _check_rc(rc)

    while True:
        with nogil:
            memcpy(
                zmq_msg_data(address(out_msg)), msg_c, zmq_msg_size(address(out_msg))
            )
            rc = _mq_inline(
                ins, outs, mons, address(in_msg), address(out_msg), swap_ids
            )
        try:
            _check_rc(rc)
        except InterruptedSystemCall:
            continue
        else:
            break
    return rc


__all__ = [
    'IPC_PATH_MAX_LEN',
    'Context',
    'Socket',
    'Frame',
    'has',
    'curve_keypair',
    'curve_public',
    'zmq_version_info',
    'zmq_errno',
    'zmq_poll',
    'strerror',
    'proxy',
    'proxy_steerable',
]