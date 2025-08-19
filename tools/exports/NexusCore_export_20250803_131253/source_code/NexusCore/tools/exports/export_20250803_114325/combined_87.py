
# === NexusCore/openenv\Lib\site-packages\fontTools\mtiLib\__init__.py ===
# FontDame-to-FontTools for OpenType Layout tables
#
# Source language spec is available at:
# http://monotype.github.io/OpenType_Table_Source/otl_source.html
# https://github.com/Monotype/OpenType_Table_Source/

from fontTools import ttLib
from fontTools.ttLib.tables._c_m_a_p import cmap_classes
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables.otBase import ValueRecord, valueRecordFormatDict
from fontTools.otlLib import builder as otl
from contextlib import contextmanager
from fontTools.ttLib import newTable
from fontTools.feaLib.lookupDebugInfo import LOOKUP_DEBUG_ENV_VAR, LOOKUP_DEBUG_INFO_KEY
from operator import setitem
import os
import logging


class MtiLibError(Exception):
    pass


class ReferenceNotFoundError(MtiLibError):
    pass


class FeatureNotFoundError(ReferenceNotFoundError):
    pass


class LookupNotFoundError(ReferenceNotFoundError):
    pass


log = logging.getLogger("fontTools.mtiLib")


def makeGlyph(s):
    if s[:2] in ["U ", "u "]:
        return ttLib.TTFont._makeGlyphName(int(s[2:], 16))
    elif s[:2] == "# ":
        return "glyph%.5d" % int(s[2:])
    assert s.find(" ") < 0, "Space found in glyph name: %s" % s
    assert s, "Glyph name is empty"
    return s


def makeGlyphs(l):
    return [makeGlyph(g) for g in l]


def mapLookup(sym, mapping):
    # Lookups are addressed by name.  So resolved them using a map if available.
    # Fallback to parsing as lookup index if a map isn't provided.
    if mapping is not None:
        try:
            idx = mapping[sym]
        except KeyError:
            raise LookupNotFoundError(sym)
    else:
        idx = int(sym)
    return idx


def mapFeature(sym, mapping):
    # Features are referenced by index according the spec.  So, if symbol is an
    # integer, use it directly.  Otherwise look up in the map if provided.
    try:
        idx = int(sym)
    except ValueError:
        try:
            idx = mapping[sym]
        except KeyError:
            raise FeatureNotFoundError(sym)
    return idx


def setReference(mapper, mapping, sym, setter, collection, key):
    try:
        mapped = mapper(sym, mapping)
    except ReferenceNotFoundError as e:
        try:
            if mapping is not None:
                mapping.addDeferredMapping(
                    lambda ref: setter(collection, key, ref), sym, e
                )
                return
        except AttributeError:
            pass
        raise
    setter(collection, key, mapped)


class DeferredMapping(dict):
    def __init__(self):
        self._deferredMappings = []

    def addDeferredMapping(self, setter, sym, e):
        log.debug("Adding deferred mapping for symbol '%s' %s", sym, type(e).__name__)
        self._deferredMappings.append((setter, sym, e))

    def applyDeferredMappings(self):
        for setter, sym, e in self._deferredMappings:
            log.debug(
                "Applying deferred mapping for symbol '%s' %s", sym, type(e).__name__
            )
            try:
                mapped = self[sym]
            except KeyError:
                raise e
            setter(mapped)
            log.debug("Set to %s", mapped)
        self._deferredMappings = []


def parseScriptList(lines, featureMap=None):
    self = ot.ScriptList()
    records = []
    with lines.between("script table"):
        for line in lines:
            while len(line) < 4:
                line.append("")
            scriptTag, langSysTag, defaultFeature, features = line
            log.debug("Adding script %s language-system %s", scriptTag, langSysTag)

            langSys = ot.LangSys()
            langSys.LookupOrder = None
            if defaultFeature:
                setReference(
                    mapFeature,
                    featureMap,
                    defaultFeature,
                    setattr,
                    langSys,
                    "ReqFeatureIndex",
                )
            else:
                langSys.ReqFeatureIndex = 0xFFFF
            syms = stripSplitComma(features)
            langSys.FeatureIndex = theList = [3] * len(syms)
            for i, sym in enumerate(syms):
                setReference(mapFeature, featureMap, sym, setitem, theList, i)
            langSys.FeatureCount = len(langSys.FeatureIndex)

            script = [s for s in records if s.ScriptTag == scriptTag]
            if script:
                script = script[0].Script
            else:
                scriptRec = ot.ScriptRecord()
                scriptRec.ScriptTag = scriptTag + " " * (4 - len(scriptTag))
                scriptRec.Script = ot.Script()
                records.append(scriptRec)
                script = scriptRec.Script
                script.DefaultLangSys = None
                script.LangSysRecord = []
                script.LangSysCount = 0

            if langSysTag == "default":
                script.DefaultLangSys = langSys
            else:
                langSysRec = ot.LangSysRecord()
                langSysRec.LangSysTag = langSysTag + " " * (4 - len(langSysTag))
                langSysRec.LangSys = langSys
                script.LangSysRecord.append(langSysRec)
                script.LangSysCount = len(script.LangSysRecord)

    for script in records:
        script.Script.LangSysRecord = sorted(
            script.Script.LangSysRecord, key=lambda rec: rec.LangSysTag
        )
    self.ScriptRecord = sorted(records, key=lambda rec: rec.ScriptTag)
    self.ScriptCount = len(self.ScriptRecord)
    return self


def parseFeatureList(lines, lookupMap=None, featureMap=None):
    self = ot.FeatureList()
    self.FeatureRecord = []
    with lines.between("feature table"):
        for line in lines:
            name, featureTag, lookups = line
            if featureMap is not None:
                assert name not in featureMap, "Duplicate feature name: %s" % name
                featureMap[name] = len(self.FeatureRecord)
            # If feature name is integer, make sure it matches its index.
            try:
                assert int(name) == len(self.FeatureRecord), "%d %d" % (
                    name,
                    len(self.FeatureRecord),
                )
            except ValueError:
                pass
            featureRec = ot.FeatureRecord()
            featureRec.FeatureTag = featureTag
            featureRec.Feature = ot.Feature()
            self.FeatureRecord.append(featureRec)
            feature = featureRec.Feature
            feature.FeatureParams = None
            syms = stripSplitComma(lookups)
            feature.LookupListIndex = theList = [None] * len(syms)
            for i, sym in enumerate(syms):
                setReference(mapLookup, lookupMap, sym, setitem, theList, i)
            feature.LookupCount = len(feature.LookupListIndex)

    self.FeatureCount = len(self.FeatureRecord)
    return self


def parseLookupFlags(lines):
    flags = 0
    filterset = None
    allFlags = [
        "righttoleft",
        "ignorebaseglyphs",
        "ignoreligatures",
        "ignoremarks",
        "markattachmenttype",
        "markfiltertype",
    ]
    while lines.peeks()[0].lower() in allFlags:
        line = next(lines)
        flag = {
            "righttoleft": 0x0001,
            "ignorebaseglyphs": 0x0002,
            "ignoreligatures": 0x0004,
            "ignoremarks": 0x0008,
        }.get(line[0].lower())
        if flag:
            assert line[1].lower() in ["yes", "no"], line[1]
            if line[1].lower() == "yes":
                flags |= flag
            continue
        if line[0].lower() == "markattachmenttype":
            flags |= int(line[1]) << 8
            continue
        if line[0].lower() == "markfiltertype":
            flags |= 0x10
            filterset = int(line[1])
    return flags, filterset


def parseSingleSubst(lines, font, _lookupMap=None):
    mapping = {}
    for line in lines:
        assert len(line) == 2, line
        line = makeGlyphs(line)
        mapping[line[0]] = line[1]
    return otl.buildSingleSubstSubtable(mapping)


def parseMultiple(lines, font, _lookupMap=None):
    mapping = {}
    for line in lines:
        line = makeGlyphs(line)
        mapping[line[0]] = line[1:]
    return otl.buildMultipleSubstSubtable(mapping)


def parseAlternate(lines, font, _lookupMap=None):
    mapping = {}
    for line in lines:
        line = makeGlyphs(line)
        mapping[line[0]] = line[1:]
    return otl.buildAlternateSubstSubtable(mapping)


def parseLigature(lines, font, _lookupMap=None):
    mapping = {}
    for line in lines:
        assert len(line) >= 2, line
        line = makeGlyphs(line)
        mapping[tuple(line[1:])] = line[0]
    return otl.buildLigatureSubstSubtable(mapping)


def parseSinglePos(lines, font, _lookupMap=None):
    values = {}
    for line in lines:
        assert len(line) == 3, line
        w = line[0].title().replace(" ", "")
        assert w in valueRecordFormatDict
        g = makeGlyph(line[1])
        v = int(line[2])
        if g not in values:
            values[g] = ValueRecord()
        assert not hasattr(values[g], w), (g, w)
        setattr(values[g], w, v)
    return otl.buildSinglePosSubtable(values, font.getReverseGlyphMap())


def parsePair(lines, font, _lookupMap=None):
    self = ot.PairPos()
    self.ValueFormat1 = self.ValueFormat2 = 0
    typ = lines.peeks()[0].split()[0].lower()
    if typ in ("left", "right"):
        self.Format = 1
        values = {}
        for line in lines:
            assert len(line) == 4, line
            side = line[0].split()[0].lower()
            assert side in ("left", "right"), side
            what = line[0][len(side) :].title().replace(" ", "")
            mask = valueRecordFormatDict[what][0]
            glyph1, glyph2 = makeGlyphs(line[1:3])
            value = int(line[3])
            if not glyph1 in values:
                values[glyph1] = {}
            if not glyph2 in values[glyph1]:
                values[glyph1][glyph2] = (ValueRecord(), ValueRecord())
            rec2 = values[glyph1][glyph2]
            if side == "left":
                self.ValueFormat1 |= mask
                vr = rec2[0]
            else:
                self.ValueFormat2 |= mask
                vr = rec2[1]
            assert not hasattr(vr, what), (vr, what)
            setattr(vr, what, value)
        self.Coverage = makeCoverage(set(values.keys()), font)
        self.PairSet = []
        for glyph1 in self.Coverage.glyphs:
            values1 = values[glyph1]
            pairset = ot.PairSet()
            records = pairset.PairValueRecord = []
            for glyph2 in sorted(values1.keys(), key=font.getGlyphID):
                values2 = values1[glyph2]
                pair = ot.PairValueRecord()
                pair.SecondGlyph = glyph2
                pair.Value1 = values2[0]
                pair.Value2 = values2[1] if self.ValueFormat2 else None
                records.append(pair)
            pairset.PairValueCount = len(pairset.PairValueRecord)
            self.PairSet.append(pairset)
        self.PairSetCount = len(self.PairSet)
    elif typ.endswith("class"):
        self.Format = 2
        classDefs = [None, None]
        while lines.peeks()[0].endswith("class definition begin"):
            typ = lines.peek()[0][: -len("class definition begin")].lower()
            idx, klass = {
                "first": (0, ot.ClassDef1),
                "second": (1, ot.ClassDef2),
            }[typ]
            assert classDefs[idx] is None
            classDefs[idx] = parseClassDef(lines, font, klass=klass)
        self.ClassDef1, self.ClassDef2 = classDefs
        self.Class1Count, self.Class2Count = (
            1 + max(c.classDefs.values()) for c in classDefs
        )
        self.Class1Record = [ot.Class1Record() for i in range(self.Class1Count)]
        for rec1 in self.Class1Record:
            rec1.Class2Record = [ot.Class2Record() for j in range(self.Class2Count)]
            for rec2 in rec1.Class2Record:
                rec2.Value1 = ValueRecord()
                rec2.Value2 = ValueRecord()
        for line in lines:
            assert len(line) == 4, line
            side = line[0].split()[0].lower()
            assert side in ("left", "right"), side
            what = line[0][len(side) :].title().replace(" ", "")
            mask = valueRecordFormatDict[what][0]
            class1, class2, value = (int(x) for x in line[1:4])
            rec2 = self.Class1Record[class1].Class2Record[class2]
            if side == "left":
                self.ValueFormat1 |= mask
                vr = rec2.Value1
            else:
                self.ValueFormat2 |= mask
                vr = rec2.Value2
            assert not hasattr(vr, what), (vr, what)
            setattr(vr, what, value)
        for rec1 in self.Class1Record:
            for rec2 in rec1.Class2Record:
                rec2.Value1 = ValueRecord(self.ValueFormat1, rec2.Value1)
                rec2.Value2 = (
                    ValueRecord(self.ValueFormat2, rec2.Value2)
                    if self.ValueFormat2
                    else None
                )

        self.Coverage = makeCoverage(set(self.ClassDef1.classDefs.keys()), font)
    else:
        assert 0, typ
    return self


def parseKernset(lines, font, _lookupMap=None):
    typ = lines.peeks()[0].split()[0].lower()
    if typ in ("left", "right"):
        with lines.until(
            ("firstclass definition begin", "secondclass definition begin")
        ):
            return parsePair(lines, font)
    return parsePair(lines, font)


def makeAnchor(data, klass=ot.Anchor):
    assert len(data) <= 2
    anchor = klass()
    anchor.Format = 1
    anchor.XCoordinate, anchor.YCoordinate = intSplitComma(data[0])
    if len(data) > 1 and data[1] != "":
        anchor.Format = 2
        anchor.AnchorPoint = int(data[1])
    return anchor


def parseCursive(lines, font, _lookupMap=None):
    records = {}
    for line in lines:
        assert len(line) in [3, 4], line
        idx, klass = {
            "entry": (0, ot.EntryAnchor),
            "exit": (1, ot.ExitAnchor),
        }[line[0]]
        glyph = makeGlyph(line[1])
        if glyph not in records:
            records[glyph] = [None, None]
        assert records[glyph][idx] is None, (glyph, idx)
        records[glyph][idx] = makeAnchor(line[2:], klass)
    return otl.buildCursivePosSubtable(records, font.getReverseGlyphMap())


def makeMarkRecords(data, coverage, c):
    records = []
    for glyph in coverage.glyphs:
        klass, anchor = data[glyph]
        record = c.MarkRecordClass()
        record.Class = klass
        setattr(record, c.MarkAnchor, anchor)
        records.append(record)
    return records


def makeBaseRecords(data, coverage, c, classCount):
    records = []
    idx = {}
    for glyph in coverage.glyphs:
        idx[glyph] = len(records)
        record = c.BaseRecordClass()
        anchors = [None] * classCount
        setattr(record, c.BaseAnchor, anchors)
        records.append(record)
    for (glyph, klass), anchor in data.items():
        record = records[idx[glyph]]
        anchors = getattr(record, c.BaseAnchor)
        assert anchors[klass] is None, (glyph, klass)
        anchors[klass] = anchor
    return records


def makeLigatureRecords(data, coverage, c, classCount):
    records = [None] * len(coverage.glyphs)
    idx = {g: i for i, g in enumerate(coverage.glyphs)}

    for (glyph, klass, compIdx, compCount), anchor in data.items():
        record = records[idx[glyph]]
        if record is None:
            record = records[idx[glyph]] = ot.LigatureAttach()
            record.ComponentCount = compCount
            record.ComponentRecord = [ot.ComponentRecord() for i in range(compCount)]
            for compRec in record.ComponentRecord:
                compRec.LigatureAnchor = [None] * classCount
        assert record.ComponentCount == compCount, (
            glyph,
            record.ComponentCount,
            compCount,
        )

        anchors = record.ComponentRecord[compIdx - 1].LigatureAnchor
        assert anchors[klass] is None, (glyph, compIdx, klass)
        anchors[klass] = anchor
    return records


def parseMarkToSomething(lines, font, c):
    self = c.Type()
    self.Format = 1
    markData = {}
    baseData = {}
    Data = {
        "mark": (markData, c.MarkAnchorClass),
        "base": (baseData, c.BaseAnchorClass),
        "ligature": (baseData, c.BaseAnchorClass),
    }
    maxKlass = 0
    for line in lines:
        typ = line[0]
        assert typ in ("mark", "base", "ligature")
        glyph = makeGlyph(line[1])
        data, anchorClass = Data[typ]
        extraItems = 2 if typ == "ligature" else 0
        extras = tuple(int(i) for i in line[2 : 2 + extraItems])
        klass = int(line[2 + extraItems])
        anchor = makeAnchor(line[3 + extraItems :], anchorClass)
        if typ == "mark":
            key, value = glyph, (klass, anchor)
        else:
            key, value = ((glyph, klass) + extras), anchor
        assert key not in data, key
        data[key] = value
        maxKlass = max(maxKlass, klass)

    # Mark
    markCoverage = makeCoverage(set(markData.keys()), font, c.MarkCoverageClass)
    markArray = c.MarkArrayClass()
    markRecords = makeMarkRecords(markData, markCoverage, c)
    setattr(markArray, c.MarkRecord, markRecords)
    setattr(markArray, c.MarkCount, len(markRecords))
    setattr(self, c.MarkCoverage, markCoverage)
    setattr(self, c.MarkArray, markArray)
    self.ClassCount = maxKlass + 1

    # Base
    self.classCount = 0 if not baseData else 1 + max(k[1] for k, v in baseData.items())
    baseCoverage = makeCoverage(
        set([k[0] for k in baseData.keys()]), font, c.BaseCoverageClass
    )
    baseArray = c.BaseArrayClass()
    if c.Base == "Ligature":
        baseRecords = makeLigatureRecords(baseData, baseCoverage, c, self.classCount)
    else:
        baseRecords = makeBaseRecords(baseData, baseCoverage, c, self.classCount)
    setattr(baseArray, c.BaseRecord, baseRecords)
    setattr(baseArray, c.BaseCount, len(baseRecords))
    setattr(self, c.BaseCoverage, baseCoverage)
    setattr(self, c.BaseArray, baseArray)

    return self


class MarkHelper(object):
    def __init__(self):
        for Which in ("Mark", "Base"):
            for What in ("Coverage", "Array", "Count", "Record", "Anchor"):
                key = Which + What
                if Which == "Mark" and What in ("Count", "Record", "Anchor"):
                    value = key
                else:
                    value = getattr(self, Which) + What
                if value == "LigatureRecord":
                    value = "LigatureAttach"
                setattr(self, key, value)
                if What != "Count":
                    klass = getattr(ot, value)
                    setattr(self, key + "Class", klass)


class MarkToBaseHelper(MarkHelper):
    Mark = "Mark"
    Base = "Base"
    Type = ot.MarkBasePos


class MarkToMarkHelper(MarkHelper):
    Mark = "Mark1"
    Base = "Mark2"
    Type = ot.MarkMarkPos


class MarkToLigatureHelper(MarkHelper):
    Mark = "Mark"
    Base = "Ligature"
    Type = ot.MarkLigPos


def parseMarkToBase(lines, font, _lookupMap=None):
    return parseMarkToSomething(lines, font, MarkToBaseHelper())


def parseMarkToMark(lines, font, _lookupMap=None):
    return parseMarkToSomething(lines, font, MarkToMarkHelper())


def parseMarkToLigature(lines, font, _lookupMap=None):
    return parseMarkToSomething(lines, font, MarkToLigatureHelper())


def stripSplitComma(line):
    return [s.strip() for s in line.split(",")] if line else []


def intSplitComma(line):
    return [int(i) for i in line.split(",")] if line else []


# Copied from fontTools.subset
class ContextHelper(object):
    def __init__(self, klassName, Format):
        if klassName.endswith("Subst"):
            Typ = "Sub"
            Type = "Subst"
        else:
            Typ = "Pos"
            Type = "Pos"
        if klassName.startswith("Chain"):
            Chain = "Chain"
            InputIdx = 1
            DataLen = 3
        else:
            Chain = ""
            InputIdx = 0
            DataLen = 1
        ChainTyp = Chain + Typ

        self.Typ = Typ
        self.Type = Type
        self.Chain = Chain
        self.ChainTyp = ChainTyp
        self.InputIdx = InputIdx
        self.DataLen = DataLen

        self.LookupRecord = Type + "LookupRecord"

        if Format == 1:
            Coverage = lambda r: r.Coverage
            ChainCoverage = lambda r: r.Coverage
            ContextData = lambda r: (None,)
            ChainContextData = lambda r: (None, None, None)
            SetContextData = None
            SetChainContextData = None
            RuleData = lambda r: (r.Input,)
            ChainRuleData = lambda r: (r.Backtrack, r.Input, r.LookAhead)

            def SetRuleData(r, d):
                (r.Input,) = d
                (r.GlyphCount,) = (len(x) + 1 for x in d)

            def ChainSetRuleData(r, d):
                (r.Backtrack, r.Input, r.LookAhead) = d
                (
                    r.BacktrackGlyphCount,
                    r.InputGlyphCount,
                    r.LookAheadGlyphCount,
                ) = (len(d[0]), len(d[1]) + 1, len(d[2]))

        elif Format == 2:
            Coverage = lambda r: r.Coverage
            ChainCoverage = lambda r: r.Coverage
            ContextData = lambda r: (r.ClassDef,)
            ChainContextData = lambda r: (
                r.BacktrackClassDef,
                r.InputClassDef,
                r.LookAheadClassDef,
            )

            def SetContextData(r, d):
                (r.ClassDef,) = d

            def SetChainContextData(r, d):
                (r.BacktrackClassDef, r.InputClassDef, r.LookAheadClassDef) = d

            RuleData = lambda r: (r.Class,)
            ChainRuleData = lambda r: (r.Backtrack, r.Input, r.LookAhead)

            def SetRuleData(r, d):
                (r.Class,) = d
                (r.GlyphCount,) = (len(x) + 1 for x in d)

            def ChainSetRuleData(r, d):
                (r.Backtrack, r.Input, r.LookAhead) = d
                (
                    r.BacktrackGlyphCount,
                    r.InputGlyphCount,
                    r.LookAheadGlyphCount,
                ) = (len(d[0]), len(d[1]) + 1, len(d[2]))

        elif Format == 3:
            Coverage = lambda r: r.Coverage[0]
            ChainCoverage = lambda r: r.InputCoverage[0]
            ContextData = None
            ChainContextData = None
            SetContextData = None
            SetChainContextData = None
            RuleData = lambda r: r.Coverage
            ChainRuleData = lambda r: (
                r.BacktrackCoverage + r.InputCoverage + r.LookAheadCoverage
            )

            def SetRuleData(r, d):
                (r.Coverage,) = d
                (r.GlyphCount,) = (len(x) for x in d)

            def ChainSetRuleData(r, d):
                (r.BacktrackCoverage, r.InputCoverage, r.LookAheadCoverage) = d
                (
                    r.BacktrackGlyphCount,
                    r.InputGlyphCount,
                    r.LookAheadGlyphCount,
                ) = (len(x) for x in d)

        else:
            assert 0, "unknown format: %s" % Format

        if Chain:
            self.Coverage = ChainCoverage
            self.ContextData = ChainContextData
            self.SetContextData = SetChainContextData
            self.RuleData = ChainRuleData
            self.SetRuleData = ChainSetRuleData
        else:
            self.Coverage = Coverage
            self.ContextData = ContextData
            self.SetContextData = SetContextData
            self.RuleData = RuleData
            self.SetRuleData = SetRuleData

        if Format == 1:
            self.Rule = ChainTyp + "Rule"
            self.RuleCount = ChainTyp + "RuleCount"
            self.RuleSet = ChainTyp + "RuleSet"
            self.RuleSetCount = ChainTyp + "RuleSetCount"
            self.Intersect = lambda glyphs, c, r: [r] if r in glyphs else []
        elif Format == 2:
            self.Rule = ChainTyp + "ClassRule"
            self.RuleCount = ChainTyp + "ClassRuleCount"
            self.RuleSet = ChainTyp + "ClassSet"
            self.RuleSetCount = ChainTyp + "ClassSetCount"
            self.Intersect = lambda glyphs, c, r: (
                c.intersect_class(glyphs, r)
                if c
                else (set(glyphs) if r == 0 else set())
            )

            self.ClassDef = "InputClassDef" if Chain else "ClassDef"
            self.ClassDefIndex = 1 if Chain else 0
            self.Input = "Input" if Chain else "Class"


def parseLookupRecords(items, klassName, lookupMap=None):
    klass = getattr(ot, klassName)
    lst = []
    for item in items:
        rec = klass()
        item = stripSplitComma(item)
        assert len(item) == 2, item
        idx = int(item[0])
        assert idx > 0, idx
        rec.SequenceIndex = idx - 1
        setReference(mapLookup, lookupMap, item[1], setattr, rec, "LookupListIndex")
        lst.append(rec)
    return lst


def makeClassDef(classDefs, font, klass=ot.Coverage):
    if not classDefs:
        return None
    self = klass()
    self.classDefs = dict(classDefs)
    return self


def parseClassDef(lines, font, klass=ot.ClassDef):
    classDefs = {}
    with lines.between("class definition"):
        for line in lines:
            glyph = makeGlyph(line[0])
            assert glyph not in classDefs, glyph
            classDefs[glyph] = int(line[1])
    return makeClassDef(classDefs, font, klass)


def makeCoverage(glyphs, font, klass=ot.Coverage):
    if not glyphs:
        return None
    if isinstance(glyphs, set):
        glyphs = sorted(glyphs)
    coverage = klass()
    coverage.glyphs = sorted(set(glyphs), key=font.getGlyphID)
    return coverage


def parseCoverage(lines, font, klass=ot.Coverage):
    glyphs = []
    with lines.between("coverage definition"):
        for line in lines:
            glyphs.append(makeGlyph(line[0]))
    return makeCoverage(glyphs, font, klass)


def bucketizeRules(self, c, rules, bucketKeys):
    buckets = {}
    for seq, recs in rules:
        buckets.setdefault(seq[c.InputIdx][0], []).append(
            (tuple(s[1 if i == c.InputIdx else 0 :] for i, s in enumerate(seq)), recs)
        )

    rulesets = []
    for firstGlyph in bucketKeys:
        if firstGlyph not in buckets:
            rulesets.append(None)
            continue
        thisRules = []
        for seq, recs in buckets[firstGlyph]:
            rule = getattr(ot, c.Rule)()
            c.SetRuleData(rule, seq)
            setattr(rule, c.Type + "Count", len(recs))
            setattr(rule, c.LookupRecord, recs)
            thisRules.append(rule)

        ruleset = getattr(ot, c.RuleSet)()
        setattr(ruleset, c.Rule, thisRules)
        setattr(ruleset, c.RuleCount, len(thisRules))
        rulesets.append(ruleset)

    setattr(self, c.RuleSet, rulesets)
    setattr(self, c.RuleSetCount, len(rulesets))


def parseContext(lines, font, Type, lookupMap=None):
    self = getattr(ot, Type)()
    typ = lines.peeks()[0].split()[0].lower()
    if typ == "glyph":
        self.Format = 1
        log.debug("Parsing %s format %s", Type, self.Format)
        c = ContextHelper(Type, self.Format)
        rules = []
        for line in lines:
            assert line[0].lower() == "glyph", line[0]
            while len(line) < 1 + c.DataLen:
                line.append("")
            seq = tuple(makeGlyphs(stripSplitComma(i)) for i in line[1 : 1 + c.DataLen])
            recs = parseLookupRecords(line[1 + c.DataLen :], c.LookupRecord, lookupMap)
            rules.append((seq, recs))

        firstGlyphs = set(seq[c.InputIdx][0] for seq, recs in rules)
        self.Coverage = makeCoverage(firstGlyphs, font)
        bucketizeRules(self, c, rules, self.Coverage.glyphs)
    elif typ.endswith("class"):
        self.Format = 2
        log.debug("Parsing %s format %s", Type, self.Format)
        c = ContextHelper(Type, self.Format)
        classDefs = [None] * c.DataLen
        while lines.peeks()[0].endswith("class definition begin"):
            typ = lines.peek()[0][: -len("class definition begin")].lower()
            idx, klass = {
                1: {
                    "": (0, ot.ClassDef),
                },
                3: {
                    "backtrack": (0, ot.BacktrackClassDef),
                    "": (1, ot.InputClassDef),
                    "lookahead": (2, ot.LookAheadClassDef),
                },
            }[c.DataLen][typ]
            assert classDefs[idx] is None, idx
            classDefs[idx] = parseClassDef(lines, font, klass=klass)
        c.SetContextData(self, classDefs)
        rules = []
        for line in lines:
            assert line[0].lower().startswith("class"), line[0]
            while len(line) < 1 + c.DataLen:
                line.append("")
            seq = tuple(intSplitComma(i) for i in line[1 : 1 + c.DataLen])
            recs = parseLookupRecords(line[1 + c.DataLen :], c.LookupRecord, lookupMap)
            rules.append((seq, recs))
        firstClasses = set(seq[c.InputIdx][0] for seq, recs in rules)
        firstGlyphs = set(
            g for g, c in classDefs[c.InputIdx].classDefs.items() if c in firstClasses
        )
        self.Coverage = makeCoverage(firstGlyphs, font)
        bucketizeRules(self, c, rules, range(max(firstClasses) + 1))
    elif typ.endswith("coverage"):
        self.Format = 3
        log.debug("Parsing %s format %s", Type, self.Format)
        c = ContextHelper(Type, self.Format)
        coverages = tuple([] for i in range(c.DataLen))
        while lines.peeks()[0].endswith("coverage definition begin"):
            typ = lines.peek()[0][: -len("coverage definition begin")].lower()
            idx, klass = {
                1: {
                    "": (0, ot.Coverage),
                },
                3: {
                    "backtrack": (0, ot.BacktrackCoverage),
                    "input": (1, ot.InputCoverage),
                    "lookahead": (2, ot.LookAheadCoverage),
                },
            }[c.DataLen][typ]
            coverages[idx].append(parseCoverage(lines, font, klass=klass))
        c.SetRuleData(self, coverages)
        lines = list(lines)
        assert len(lines) == 1
        line = lines[0]
        assert line[0].lower() == "coverage", line[0]
        recs = parseLookupRecords(line[1:], c.LookupRecord, lookupMap)
        setattr(self, c.Type + "Count", len(recs))
        setattr(self, c.LookupRecord, recs)
    else:
        assert 0, typ
    return self


def parseContextSubst(lines, font, lookupMap=None):
    return parseContext(lines, font, "ContextSubst", lookupMap=lookupMap)


def parseContextPos(lines, font, lookupMap=None):
    return parseContext(lines, font, "ContextPos", lookupMap=lookupMap)


def parseChainedSubst(lines, font, lookupMap=None):
    return parseContext(lines, font, "ChainContextSubst", lookupMap=lookupMap)


def parseChainedPos(lines, font, lookupMap=None):
    return parseContext(lines, font, "ChainContextPos", lookupMap=lookupMap)


def parseReverseChainedSubst(lines, font, _lookupMap=None):
    self = ot.ReverseChainSingleSubst()
    self.Format = 1
    coverages = ([], [])
    while lines.peeks()[0].endswith("coverage definition begin"):
        typ = lines.peek()[0][: -len("coverage definition begin")].lower()
        idx, klass = {
            "backtrack": (0, ot.BacktrackCoverage),
            "lookahead": (1, ot.LookAheadCoverage),
        }[typ]
        coverages[idx].append(parseCoverage(lines, font, klass=klass))
    self.BacktrackCoverage = coverages[0]
    self.BacktrackGlyphCount = len(self.BacktrackCoverage)
    self.LookAheadCoverage = coverages[1]
    self.LookAheadGlyphCount = len(self.LookAheadCoverage)
    mapping = {}
    for line in lines:
        assert len(line) == 2, line
        line = makeGlyphs(line)
        mapping[line[0]] = line[1]
    self.Coverage = makeCoverage(set(mapping.keys()), font)
    self.Substitute = [mapping[k] for k in self.Coverage.glyphs]
    self.GlyphCount = len(self.Substitute)
    return self


def parseLookup(lines, tableTag, font, lookupMap=None):
    line = lines.expect("lookup")
    _, name, typ = line
    log.debug("Parsing lookup type %s %s", typ, name)
    lookup = ot.Lookup()
    lookup.LookupFlag, filterset = parseLookupFlags(lines)
    if filterset is not None:
        lookup.MarkFilteringSet = filterset
    lookup.LookupType, parseLookupSubTable = {
        "GSUB": {
            "single": (1, parseSingleSubst),
            "multiple": (2, parseMultiple),
            "alternate": (3, parseAlternate),
            "ligature": (4, parseLigature),
            "context": (5, parseContextSubst),
            "chained": (6, parseChainedSubst),
            "reversechained": (8, parseReverseChainedSubst),
        },
        "GPOS": {
            "single": (1, parseSinglePos),
            "pair": (2, parsePair),
            "kernset": (2, parseKernset),
            "cursive": (3, parseCursive),
            "mark to base": (4, parseMarkToBase),
            "mark to ligature": (5, parseMarkToLigature),
            "mark to mark": (6, parseMarkToMark),
            "context": (7, parseContextPos),
            "chained": (8, parseChainedPos),
        },
    }[tableTag][typ]

    with lines.until("lookup end"):
        subtables = []

        while lines.peek():
            with lines.until(("% subtable", "subtable end")):
                while lines.peek():
                    subtable = parseLookupSubTable(lines, font, lookupMap)
                    assert lookup.LookupType == subtable.LookupType
                    subtables.append(subtable)
            if lines.peeks()[0] in ("% subtable", "subtable end"):
                next(lines)
    lines.expect("lookup end")

    lookup.SubTable = subtables
    lookup.SubTableCount = len(lookup.SubTable)
    if lookup.SubTableCount == 0:
        # Remove this return when following is fixed:
        # https://github.com/fonttools/fonttools/issues/789
        return None
    return lookup


def parseGSUBGPOS(lines, font, tableTag):
    container = ttLib.getTableClass(tableTag)()
    lookupMap = DeferredMapping()
    featureMap = DeferredMapping()
    assert tableTag in ("GSUB", "GPOS")
    log.debug("Parsing %s", tableTag)
    self = getattr(ot, tableTag)()
    self.Version = 0x00010000
    fields = {
        "script table begin": (
            "ScriptList",
            lambda lines: parseScriptList(lines, featureMap),
        ),
        "feature table begin": (
            "FeatureList",
            lambda lines: parseFeatureList(lines, lookupMap, featureMap),
        ),
        "lookup": ("LookupList", None),
    }
    for attr, parser in fields.values():
        setattr(self, attr, None)
    while lines.peek() is not None:
        typ = lines.peek()[0].lower()
        if typ not in fields:
            log.debug("Skipping %s", lines.peek())
            next(lines)
            continue
        attr, parser = fields[typ]
        if typ == "lookup":
            if self.LookupList is None:
                self.LookupList = ot.LookupList()
                self.LookupList.Lookup = []
            _, name, _ = lines.peek()
            lookup = parseLookup(lines, tableTag, font, lookupMap)
            if lookupMap is not None:
                assert name not in lookupMap, "Duplicate lookup name: %s" % name
                lookupMap[name] = len(self.LookupList.Lookup)
            else:
                assert int(name) == len(self.LookupList.Lookup), "%d %d" % (
                    name,
                    len(self.Lookup),
                )
            self.LookupList.Lookup.append(lookup)
        else:
            assert getattr(self, attr) is None, attr
            setattr(self, attr, parser(lines))
    if self.LookupList:
        self.LookupList.LookupCount = len(self.LookupList.Lookup)
    if lookupMap is not None:
        lookupMap.applyDeferredMappings()
        if os.environ.get(LOOKUP_DEBUG_ENV_VAR):
            if "Debg" not in font:
                font["Debg"] = newTable("Debg")
                font["Debg"].data = {}
            debug = (
                font["Debg"]
                .data.setdefault(LOOKUP_DEBUG_INFO_KEY, {})
                .setdefault(tableTag, {})
            )
            for name, lookup in lookupMap.items():
                debug[str(lookup)] = ["", name, ""]

        featureMap.applyDeferredMappings()
    container.table = self
    return container


def parseGSUB(lines, font):
    return parseGSUBGPOS(lines, font, "GSUB")


def parseGPOS(lines, font):
    return parseGSUBGPOS(lines, font, "GPOS")


def parseAttachList(lines, font):
    points = {}
    with lines.between("attachment list"):
        for line in lines:
            glyph = makeGlyph(line[0])
            assert glyph not in points, glyph
            points[glyph] = [int(i) for i in line[1:]]
    return otl.buildAttachList(points, font.getReverseGlyphMap())


def parseCaretList(lines, font):
    carets = {}
    with lines.between("carets"):
        for line in lines:
            glyph = makeGlyph(line[0])
            assert glyph not in carets, glyph
            num = int(line[1])
            thisCarets = [int(i) for i in line[2:]]
            assert num == len(thisCarets), line
            carets[glyph] = thisCarets
    return otl.buildLigCaretList(carets, {}, font.getReverseGlyphMap())


def makeMarkFilteringSets(sets, font):
    self = ot.MarkGlyphSetsDef()
    self.MarkSetTableFormat = 1
    self.MarkSetCount = 1 + max(sets.keys())
    self.Coverage = [None] * self.MarkSetCount
    for k, v in sorted(sets.items()):
        self.Coverage[k] = makeCoverage(set(v), font)
    return self


def parseMarkFilteringSets(lines, font):
    sets = {}
    with lines.between("set definition"):
        for line in lines:
            assert len(line) == 2, line
            glyph = makeGlyph(line[0])
            # TODO accept set names
            st = int(line[1])
            if st not in sets:
                sets[st] = []
            sets[st].append(glyph)
    return makeMarkFilteringSets(sets, font)


def parseGDEF(lines, font):
    container = ttLib.getTableClass("GDEF")()
    log.debug("Parsing GDEF")
    self = ot.GDEF()
    fields = {
        "class definition begin": (
            "GlyphClassDef",
            lambda lines, font: parseClassDef(lines, font, klass=ot.GlyphClassDef),
        ),
        "attachment list begin": ("AttachList", parseAttachList),
        "carets begin": ("LigCaretList", parseCaretList),
        "mark attachment class definition begin": (
            "MarkAttachClassDef",
            lambda lines, font: parseClassDef(lines, font, klass=ot.MarkAttachClassDef),
        ),
        "markfilter set definition begin": ("MarkGlyphSetsDef", parseMarkFilteringSets),
    }
    for attr, parser in fields.values():
        setattr(self, attr, None)
    while lines.peek() is not None:
        typ = lines.peek()[0].lower()
        if typ not in fields:
            log.debug("Skipping %s", typ)
            next(lines)
            continue
        attr, parser = fields[typ]
        assert getattr(self, attr) is None, attr
        setattr(self, attr, parser(lines, font))
    self.Version = 0x00010000 if self.MarkGlyphSetsDef is None else 0x00010002
    container.table = self
    return container


def parseCmap(lines, font):
    container = ttLib.getTableClass("cmap")()
    log.debug("Parsing cmap")
    tables = []
    while lines.peek() is not None:
        lines.expect("cmap subtable %d" % len(tables))
        platId, encId, fmt, lang = [
            parseCmapId(lines, field)
            for field in ("platformID", "encodingID", "format", "language")
        ]
        table = cmap_classes[fmt](fmt)
        table.platformID = platId
        table.platEncID = encId
        table.language = lang
        table.cmap = {}
        line = next(lines)
        while line[0] != "end subtable":
            table.cmap[int(line[0], 16)] = line[1]
            line = next(lines)
        tables.append(table)
    container.tableVersion = 0
    container.tables = tables
    return container


def parseCmapId(lines, field):
    line = next(lines)
    assert field == line[0]
    return int(line[1])


def parseTable(lines, font, tableTag=None):
    log.debug("Parsing table")
    line = lines.peeks()
    tag = None
    if line[0].split()[0] == "FontDame":
        tag = line[0].split()[1]
    elif " ".join(line[0].split()[:3]) == "Font Chef Table":
        tag = line[0].split()[3]
    if tag is not None:
        next(lines)
        tag = tag.ljust(4)
        if tableTag is None:
            tableTag = tag
        else:
            assert tableTag == tag, (tableTag, tag)

    assert (
        tableTag is not None
    ), "Don't know what table to parse and data doesn't specify"

    return {
        "GSUB": parseGSUB,
        "GPOS": parseGPOS,
        "GDEF": parseGDEF,
        "cmap": parseCmap,
    }[tableTag](lines, font)


class Tokenizer(object):
    def __init__(self, f):
        # TODO BytesIO / StringIO as needed?  also, figure out whether we work on bytes or unicode
        lines = iter(f)
        try:
            self.filename = f.name
        except:
            self.filename = None
        self.lines = iter(lines)
        self.line = ""
        self.lineno = 0
        self.stoppers = []
        self.buffer = None

    def __iter__(self):
        return self

    def _next_line(self):
        self.lineno += 1
        line = self.line = next(self.lines)
        line = [s.strip() for s in line.split("\t")]
        if len(line) == 1 and not line[0]:
            del line[0]
        if line and not line[-1]:
            log.warning("trailing tab found on line %d: %s" % (self.lineno, self.line))
            while line and not line[-1]:
                del line[-1]
        return line

    def _next_nonempty(self):
        while True:
            line = self._next_line()
            # Skip comments and empty lines
            if line and line[0] and (line[0][0] != "%" or line[0] == "% subtable"):
                return line

    def _next_buffered(self):
        if self.buffer:
            ret = self.buffer
            self.buffer = None
            return ret
        else:
            return self._next_nonempty()

    def __next__(self):
        line = self._next_buffered()
        if line[0].lower() in self.stoppers:
            self.buffer = line
            raise StopIteration
        return line

    def next(self):
        return self.__next__()

    def peek(self):
        if not self.buffer:
            try:
                self.buffer = self._next_nonempty()
            except StopIteration:
                return None
        if self.buffer[0].lower() in self.stoppers:
            return None
        return self.buffer

    def peeks(self):
        ret = self.peek()
        return ret if ret is not None else ("",)

    @contextmanager
    def between(self, tag):
        start = tag + " begin"
        end = tag + " end"
        self.expectendswith(start)
        self.stoppers.append(end)
        yield
        del self.stoppers[-1]
        self.expect(tag + " end")

    @contextmanager
    def until(self, tags):
        if type(tags) is not tuple:
            tags = (tags,)
        self.stoppers.extend(tags)
        yield
        del self.stoppers[-len(tags) :]

    def expect(self, s):
        line = next(self)
        tag = line[0].lower()
        assert tag == s, "Expected '%s', got '%s'" % (s, tag)
        return line

    def expectendswith(self, s):
        line = next(self)
        tag = line[0].lower()
        assert tag.endswith(s), "Expected '*%s', got '%s'" % (s, tag)
        return line


def build(f, font, tableTag=None):
    """Convert a Monotype font layout file to an OpenType layout object

    A font object must be passed, but this may be a "dummy" font; it is only
    used for sorting glyph sets when making coverage tables and to hold the
    OpenType layout table while it is being built.

    Args:
            f: A file object.
            font (TTFont): A font object.
            tableTag (string): If provided, asserts that the file contains data for the
                    given OpenType table.

    Returns:
            An object representing the table. (e.g. ``table_G_S_U_B_``)
    """
    lines = Tokenizer(f)
    return parseTable(lines, font, tableTag=tableTag)


def main(args=None, font=None):
    """Convert a FontDame OTL file to TTX XML

    Writes XML output to stdout.

    Args:
            args: Command line arguments (``--font``, ``--table``, input files).
    """
    import sys
    from fontTools import configLogger
    from fontTools.misc.testTools import MockFont

    if args is None:
        args = sys.argv[1:]

    # configure the library logger (for >= WARNING)
    configLogger()
    # comment this out to enable debug messages from mtiLib's logger
    # log.setLevel(logging.DEBUG)

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools mtiLib",
        description=main.__doc__,
    )

    parser.add_argument(
        "--font",
        "-f",
        metavar="FILE",
        dest="font",
        help="Input TTF files (used for glyph classes and sorting coverage tables)",
    )
    parser.add_argument(
        "--table",
        "-t",
        metavar="TABLE",
        dest="tableTag",
        help="Table to fill (sniffed from input file if not provided)",
    )
    parser.add_argument(
        "inputs", metavar="FILE", type=str, nargs="+", help="Input FontDame .txt files"
    )

    args = parser.parse_args(args)

    if font is None:
        if args.font:
            font = ttLib.TTFont(args.font)
        else:
            font = MockFont()

    for f in args.inputs:
        log.debug("Processing %s", f)
        with open(f, "rt", encoding="utf-8-sig") as f:
            table = build(f, font, tableTag=args.tableTag)
        blob = table.compile(font)  # Make sure it compiles
        decompiled = table.__class__()
        decompiled.decompile(blob, font)  # Make sure it decompiles!

        # continue
        from fontTools.misc import xmlWriter

        tag = table.tableTag
        writer = xmlWriter.XMLWriter(sys.stdout)
        writer.begintag(tag)
        writer.newline()
        # table.toXML(writer, font)
        decompiled.toXML(writer, font)
        writer.endtag(tag)
        writer.newline()


if __name__ == "__main__":
    import sys

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Debugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class BreakpointId(str):
    '''
    Breakpoint identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> BreakpointId:
        return cls(json)

    def __repr__(self):
        return 'BreakpointId({})'.format(super().__repr__())


class CallFrameId(str):
    '''
    Call frame identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CallFrameId:
        return cls(json)

    def __repr__(self):
        return 'CallFrameId({})'.format(super().__repr__())


@dataclass
class Location:
    '''
    Location in the source code.
    '''
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
        )


@dataclass
class ScriptPosition:
    '''
    Location in the source code.
    '''
    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class LocationRange:
    '''
    Location range within one script.
    '''
    script_id: runtime.ScriptId

    start: ScriptPosition

    end: ScriptPosition

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['start'] = self.start.to_json()
        json['end'] = self.end.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            start=ScriptPosition.from_json(json['start']),
            end=ScriptPosition.from_json(json['end']),
        )


@dataclass
class CallFrame:
    '''
    JavaScript call frame. Array of call frames form the call stack.
    '''
    #: Call frame identifier. This identifier is only valid while the virtual machine is paused.
    call_frame_id: CallFrameId

    #: Name of the JavaScript function called on this call frame.
    function_name: str

    #: Location in the source code.
    location: Location

    #: JavaScript script name or url.
    #: Deprecated in favor of using the ``location.scriptId`` to resolve the URL via a previously
    #: sent ``Debugger.scriptParsed`` event.
    url: str

    #: Scope chain for this call frame.
    scope_chain: typing.List[Scope]

    #: ``this`` object for this call frame.
    this: runtime.RemoteObject

    #: Location in the source code.
    function_location: typing.Optional[Location] = None

    #: The value being returned, if the function is at return point.
    return_value: typing.Optional[runtime.RemoteObject] = None

    #: Valid only while the VM is paused and indicates whether this frame
    #: can be restarted or not. Note that a ``true`` value here does not
    #: guarantee that Debugger#restartFrame with this CallFrameId will be
    #: successful, but it is very likely.
    can_be_restarted: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['callFrameId'] = self.call_frame_id.to_json()
        json['functionName'] = self.function_name
        json['location'] = self.location.to_json()
        json['url'] = self.url
        json['scopeChain'] = [i.to_json() for i in self.scope_chain]
        json['this'] = self.this.to_json()
        if self.function_location is not None:
            json['functionLocation'] = self.function_location.to_json()
        if self.return_value is not None:
            json['returnValue'] = self.return_value.to_json()
        if self.can_be_restarted is not None:
            json['canBeRestarted'] = self.can_be_restarted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame_id=CallFrameId.from_json(json['callFrameId']),
            function_name=str(json['functionName']),
            location=Location.from_json(json['location']),
            url=str(json['url']),
            scope_chain=[Scope.from_json(i) for i in json['scopeChain']],
            this=runtime.RemoteObject.from_json(json['this']),
            function_location=Location.from_json(json['functionLocation']) if 'functionLocation' in json else None,
            return_value=runtime.RemoteObject.from_json(json['returnValue']) if 'returnValue' in json else None,
            can_be_restarted=bool(json['canBeRestarted']) if 'canBeRestarted' in json else None,
        )


@dataclass
class Scope:
    '''
    Scope description.
    '''
    #: Scope type.
    type_: str

    #: Object representing the scope. For ``global`` and ``with`` scopes it represents the actual
    #: object; for the rest of the scopes, it is artificial transient object enumerating scope
    #: variables as its properties.
    object_: runtime.RemoteObject

    name: typing.Optional[str] = None

    #: Location in the source code where scope starts
    start_location: typing.Optional[Location] = None

    #: Location in the source code where scope ends
    end_location: typing.Optional[Location] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['object'] = self.object_.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.start_location is not None:
            json['startLocation'] = self.start_location.to_json()
        if self.end_location is not None:
            json['endLocation'] = self.end_location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            object_=runtime.RemoteObject.from_json(json['object']),
            name=str(json['name']) if 'name' in json else None,
            start_location=Location.from_json(json['startLocation']) if 'startLocation' in json else None,
            end_location=Location.from_json(json['endLocation']) if 'endLocation' in json else None,
        )


@dataclass
class SearchMatch:
    '''
    Search match for resource.
    '''
    #: Line number in resource content.
    line_number: float

    #: Line with match content.
    line_content: str

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['lineContent'] = self.line_content
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=float(json['lineNumber']),
            line_content=str(json['lineContent']),
        )


@dataclass
class BreakLocation:
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


@dataclass
class WasmDisassemblyChunk:
    #: The next chunk of disassembled lines.
    lines: typing.List[str]

    #: The bytecode offsets describing the start of each line.
    bytecode_offsets: typing.List[int]

    def to_json(self):
        json = dict()
        json['lines'] = [i for i in self.lines]
        json['bytecodeOffsets'] = [i for i in self.bytecode_offsets]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lines=[str(i) for i in json['lines']],
            bytecode_offsets=[int(i) for i in json['bytecodeOffsets']],
        )


class ScriptLanguage(enum.Enum):
    '''
    Enum of possible script languages.
    '''
    JAVA_SCRIPT = "JavaScript"
    WEB_ASSEMBLY = "WebAssembly"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DebugSymbols:
    '''
    Debug symbols available for a wasm script.
    '''
    #: Type of the debug symbols.
    type_: str

    #: URL of the external symbol source.
    external_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.external_url is not None:
            json['externalURL'] = self.external_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            external_url=str(json['externalURL']) if 'externalURL' in json else None,
        )


@dataclass
class ResolvedBreakpoint:
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId

    #: Actual breakpoint location.
    location: Location

    def to_json(self):
        json = dict()
        json['breakpointId'] = self.breakpoint_id.to_json()
        json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location']),
        )


def continue_to_location(
        location: Location,
        target_call_frames: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues execution until specific location is reached.

    :param location: Location to continue to.
    :param target_call_frames: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if target_call_frames is not None:
        params['targetCallFrames'] = target_call_frames
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.continueToLocation',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables debugger for given page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disable',
    }
    json = yield cmd_dict


def enable(
        max_scripts_cache_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.UniqueDebuggerId]:
    '''
    Enables debugger for the given page. Clients should not assume that the debugging has been
    enabled until the result for this command is received.

    :param max_scripts_cache_size: **(EXPERIMENTAL)** *(Optional)* The maximum size in bytes of collected scripts (not referenced by other heap objects) the debugger can hold. Puts no limit if parameter is omitted.
    :returns: Unique identifier of the debugger.
    '''
    params: T_JSON_DICT = dict()
    if max_scripts_cache_size is not None:
        params['maxScriptsCacheSize'] = max_scripts_cache_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.enable',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.UniqueDebuggerId.from_json(json['debuggerId'])


def evaluate_on_call_frame(
        call_frame_id: CallFrameId,
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[runtime.TimeDelta] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[runtime.RemoteObject, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Evaluates expression on a given call frame.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* String object group name to put result into (allows rapid releasing resulting object handles using ```releaseObjectGroup````).
    :param include_command_line_api: *(Optional)* Specifies whether command line API should be available to the evaluated expression, defaults to false.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ````setPauseOnException``` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param throw_on_side_effect: *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :returns: A tuple with the following items:

        0. **result** - Object wrapper for the evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.evaluateOnCallFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        runtime.RemoteObject.from_json(json['result']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_possible_breakpoints(
        start: Location,
        end: typing.Optional[Location] = None,
        restrict_to_function: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[BreakLocation]]:
    '''
    Returns possible locations for breakpoint. scriptId in start and end range locations should be
    the same.

    :param start: Start of range to search possible breakpoint locations in.
    :param end: *(Optional)* End of range to search possible breakpoint locations in (excluding). When not specified, end of scripts is used as end of range.
    :param restrict_to_function: *(Optional)* Only consider locations which are in the same (non-nested) function as start.
    :returns: List of the possible breakpoint locations.
    '''
    params: T_JSON_DICT = dict()
    params['start'] = start.to_json()
    if end is not None:
        params['end'] = end.to_json()
    if restrict_to_function is not None:
        params['restrictToFunction'] = restrict_to_function
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getPossibleBreakpoints',
        'params': params,
    }
    json = yield cmd_dict
    return [BreakLocation.from_json(i) for i in json['locations']]


def get_script_source(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, typing.Optional[str]]]:
    '''
    Returns source for the script with given id.

    :param script_id: Id of the script to get source for.
    :returns: A tuple with the following items:

        0. **scriptSource** - Script source (empty in case of Wasm bytecode).
        1. **bytecode** - *(Optional)* Wasm bytecode.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['scriptSource']),
        str(json['bytecode']) if 'bytecode' in json else None
    )


def disassemble_wasm_module(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, typing.List[int], WasmDisassemblyChunk]]:
    '''


    **EXPERIMENTAL**

    :param script_id: Id of the script to disassemble
    :returns: A tuple with the following items:

        0. **streamId** - *(Optional)* For large modules, return a stream from which additional chunks of disassembly can be read successively.
        1. **totalNumberOfLines** - The total number of lines in the disassembly text.
        2. **functionBodyOffsets** - The offsets of all function bodies, in the format [start1, end1, start2, end2, ...] where all ends are exclusive.
        3. **chunk** - The first chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disassembleWasmModule',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['streamId']) if 'streamId' in json else None,
        int(json['totalNumberOfLines']),
        [int(i) for i in json['functionBodyOffsets']],
        WasmDisassemblyChunk.from_json(json['chunk'])
    )


def next_wasm_disassembly_chunk(
        stream_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,WasmDisassemblyChunk]:
    '''
    Disassemble the next chunk of lines for the module corresponding to the
    stream. If disassembly is complete, this API will invalidate the streamId
    and return an empty chunk. Any subsequent calls for the now invalid stream
    will return errors.

    **EXPERIMENTAL**

    :param stream_id:
    :returns: The next chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['streamId'] = stream_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.nextWasmDisassemblyChunk',
        'params': params,
    }
    json = yield cmd_dict
    return WasmDisassemblyChunk.from_json(json['chunk'])


def get_wasm_bytecode(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    This command is deprecated. Use getScriptSource instead.

    :param script_id: Id of the Wasm script to get source for.
    :returns: Script source.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getWasmBytecode',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['bytecode'])


def get_stack_trace(
        stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.StackTrace]:
    '''
    Returns stack trace with given ``stackTraceId``.

    **EXPERIMENTAL**

    :param stack_trace_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['stackTraceId'] = stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getStackTrace',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.StackTrace.from_json(json['stackTrace'])


def pause() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops on the next JavaScript statement.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pause',
    }
    json = yield cmd_dict


def pause_on_async_call(
        parent_stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param parent_stack_trace_id: Debugger will pause when async call with given stack trace is started.
    '''
    params: T_JSON_DICT = dict()
    params['parentStackTraceId'] = parent_stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pauseOnAsyncCall',
        'params': params,
    }
    json = yield cmd_dict


def remove_breakpoint(
        breakpoint_id: BreakpointId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes JavaScript breakpoint.

    :param breakpoint_id:
    '''
    params: T_JSON_DICT = dict()
    params['breakpointId'] = breakpoint_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.removeBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def restart_frame(
        call_frame_id: CallFrameId,
        mode: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[CallFrame], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId]]]:
    '''
    Restarts particular call frame from the beginning. The old, deprecated
    behavior of ``restartFrame`` is to stay paused and allow further CDP commands
    after a restart was scheduled. This can cause problems with restarting, so
    we now continue execution immediatly after it has been scheduled until we
    reach the beginning of the restarted frame.

    To stay back-wards compatible, ``restartFrame`` now expects a ``mode``
    parameter to be present. If the ``mode`` parameter is missing, ``restartFrame``
    errors out.

    The various return values are deprecated and ``callFrames`` is always empty.
    Use the call frames from the ``Debugger#paused`` events instead, that fires
    once V8 pauses at the beginning of the restarted function.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param mode: **(EXPERIMENTAL)** *(Optional)* The ```mode```` parameter must be present and set to 'StepInto', otherwise ````restartFrame``` will error out.
    :returns: A tuple with the following items:

        0. **callFrames** - New stack trace.
        1. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        2. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    if mode is not None:
        params['mode'] = mode
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.restartFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']],
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None
    )


def resume(
        terminate_on_resume: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resumes JavaScript execution.

    :param terminate_on_resume: *(Optional)* Set to true to terminate execution upon resuming execution. In contrast to Runtime.terminateExecution, this will allows to execute further JavaScript (i.e. via evaluation) until execution of the paused code is actually resumed, at which point termination is triggered. If execution is currently not paused, this parameter has no effect.
    '''
    params: T_JSON_DICT = dict()
    if terminate_on_resume is not None:
        params['terminateOnResume'] = terminate_on_resume
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.resume',
        'params': params,
    }
    json = yield cmd_dict


def search_in_content(
        script_id: runtime.ScriptId,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SearchMatch]]:
    '''
    Searches for given string in script content.

    :param script_id: Id of the script to search in.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.searchInContent',
        'params': params,
    }
    json = yield cmd_dict
    return [SearchMatch.from_json(i) for i in json['result']]


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_execution_contexts(
        unique_ids: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox execution contexts with passed ones. Forces backend to skip
    stepping/pausing in scripts in these execution contexts. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param unique_ids: Array of execution context unique ids for the debugger to ignore.
    '''
    params: T_JSON_DICT = dict()
    params['uniqueIds'] = [i for i in unique_ids]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxExecutionContexts',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_patterns(
        patterns: typing.List[str],
        skip_anonymous: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox patterns with passed ones. Forces backend to skip stepping/pausing in
    scripts with url matching one of the patterns. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param patterns: Array of regexps that will be used to check script url for blackbox state.
    :param skip_anonymous: *(Optional)* If true, also ignore scripts with no source url.
    '''
    params: T_JSON_DICT = dict()
    params['patterns'] = [i for i in patterns]
    if skip_anonymous is not None:
        params['skipAnonymous'] = skip_anonymous
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxPatterns',
        'params': params,
    }
    json = yield cmd_dict


def set_blackboxed_ranges(
        script_id: runtime.ScriptId,
        positions: typing.List[ScriptPosition]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes backend skip steps in the script in blackboxed ranges. VM will try leave blacklisted
    scripts by performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
    Positions array contains positions where blackbox state is changed. First interval isn't
    blackboxed. Array should be sorted.

    **EXPERIMENTAL**

    :param script_id: Id of the script.
    :param positions:
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['positions'] = [i.to_json() for i in positions]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxedRanges',
        'params': params,
    }
    json = yield cmd_dict


def set_breakpoint(
        location: Location,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, Location]]:
    '''
    Sets JavaScript breakpoint at a given location.

    :param location: Location to set breakpoint in.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **actualLocation** - Location this breakpoint resolved into.
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        Location.from_json(json['actualLocation'])
    )


def set_instrumentation_breakpoint(
        instrumentation: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets instrumentation breakpoint.

    :param instrumentation: Instrumentation name.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['instrumentation'] = instrumentation
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoint_by_url(
        line_number: int,
        url: typing.Optional[str] = None,
        url_regex: typing.Optional[str] = None,
        script_hash: typing.Optional[str] = None,
        column_number: typing.Optional[int] = None,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, typing.List[Location]]]:
    '''
    Sets JavaScript breakpoint at given location specified either by URL or URL regex. Once this
    command is issued, all existing parsed scripts will have breakpoints resolved and returned in
    ``locations`` property. Further matching script parsing will result in subsequent
    ``breakpointResolved`` events issued. This logical breakpoint will survive page reloads.

    :param line_number: Line number to set breakpoint at.
    :param url: *(Optional)* URL of the resources to set breakpoint on.
    :param url_regex: *(Optional)* Regex pattern for the URLs of the resources to set breakpoints on. Either ```url```` or ````urlRegex``` must be specified.
    :param script_hash: *(Optional)* Script hash of the resources to set breakpoint on.
    :param column_number: *(Optional)* Offset in the line to set breakpoint at.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **locations** - List of the locations this breakpoint resolved into upon addition.
    '''
    params: T_JSON_DICT = dict()
    params['lineNumber'] = line_number
    if url is not None:
        params['url'] = url
    if url_regex is not None:
        params['urlRegex'] = url_regex
    if script_hash is not None:
        params['scriptHash'] = script_hash
    if column_number is not None:
        params['columnNumber'] = column_number
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointByUrl',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        [Location.from_json(i) for i in json['locations']]
    )


def set_breakpoint_on_function_call(
        object_id: runtime.RemoteObjectId,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets JavaScript breakpoint before each call to the given function.
    If another function was created from the same source as a given one,
    calling it will also trigger the breakpoint.

    **EXPERIMENTAL**

    :param object_id: Function object id.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will stop on the breakpoint if this expression evaluates to true.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointOnFunctionCall',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoints_active(
        active: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates / deactivates all breakpoints on the page.

    :param active: New value for breakpoints active state.
    '''
    params: T_JSON_DICT = dict()
    params['active'] = active
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointsActive',
        'params': params,
    }
    json = yield cmd_dict


def set_pause_on_exceptions(
        state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Defines pause on exceptions state. Can be set to stop on all exceptions, uncaught exceptions,
    or caught exceptions, no exceptions. Initial pause on exceptions state is ``none``.

    :param state: Pause on exceptions mode.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setPauseOnExceptions',
        'params': params,
    }
    json = yield cmd_dict


def set_return_value(
        new_value: runtime.CallArgument
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes return value in top frame. Available only at return break position.

    **EXPERIMENTAL**

    :param new_value: New return value.
    '''
    params: T_JSON_DICT = dict()
    params['newValue'] = new_value.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setReturnValue',
        'params': params,
    }
    json = yield cmd_dict


def set_script_source(
        script_id: runtime.ScriptId,
        script_source: str,
        dry_run: typing.Optional[bool] = None,
        allow_top_frame_editing: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[typing.List[CallFrame]], typing.Optional[bool], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId], str, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Edits JavaScript source live.

    In general, functions that are currently on the stack can not be edited with
    a single exception: If the edited function is the top-most stack frame and
    that is the only activation of that function on the stack. In this case
    the live edit will be successful and a ``Debugger.restartFrame`` for the
    top-most function is automatically triggered.

    :param script_id: Id of the script to edit.
    :param script_source: New content of the script.
    :param dry_run: *(Optional)* If true the change will not actually be applied. Dry run may be used to get result description without actually modifying the code.
    :param allow_top_frame_editing: **(EXPERIMENTAL)** *(Optional)* If true, then ```scriptSource```` is allowed to change the function on top of the stack as long as the top-most stack frame is the only activation of that function.
    :returns: A tuple with the following items:

        0. **callFrames** - *(Optional)* New stack trace in case editing has happened while VM was stopped.
        1. **stackChanged** - *(Optional)* Whether current call stack  was modified after applying the changes.
        2. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        3. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
        4. **status** - Whether the operation was successful or not. Only `` Ok`` denotes a successful live edit while the other enum variants denote why the live edit failed.
        5. **exceptionDetails** - *(Optional)* Exception details if any. Only present when `` status`` is `` CompileError`.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['scriptSource'] = script_source
    if dry_run is not None:
        params['dryRun'] = dry_run
    if allow_top_frame_editing is not None:
        params['allowTopFrameEditing'] = allow_top_frame_editing
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']] if 'callFrames' in json else None,
        bool(json['stackChanged']) if 'stackChanged' in json else None,
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
        str(json['status']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_skip_all_pauses(
        skip: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes page not interrupt on any pauses (breakpoint, exception, dom exception etc).

    :param skip: New value for skip pauses state.
    '''
    params: T_JSON_DICT = dict()
    params['skip'] = skip
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setSkipAllPauses',
        'params': params,
    }
    json = yield cmd_dict


def set_variable_value(
        scope_number: int,
        variable_name: str,
        new_value: runtime.CallArgument,
        call_frame_id: CallFrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes value of variable in a callframe. Object-based scopes are not supported and must be
    mutated manually.

    :param scope_number: 0-based number of scope as was listed in scope chain. Only 'local', 'closure' and 'catch' scope types are allowed. Other scopes could be manipulated manually.
    :param variable_name: Variable name.
    :param new_value: New variable value.
    :param call_frame_id: Id of callframe that holds variable.
    '''
    params: T_JSON_DICT = dict()
    params['scopeNumber'] = scope_number
    params['variableName'] = variable_name
    params['newValue'] = new_value.to_json()
    params['callFrameId'] = call_frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setVariableValue',
        'params': params,
    }
    json = yield cmd_dict


def step_into(
        break_on_async_call: typing.Optional[bool] = None,
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps into the function call.

    :param break_on_async_call: **(EXPERIMENTAL)** *(Optional)* Debugger will pause on the execution of the first async task which was scheduled before next pause.
    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step into.
    '''
    params: T_JSON_DICT = dict()
    if break_on_async_call is not None:
        params['breakOnAsyncCall'] = break_on_async_call
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepInto',
        'params': params,
    }
    json = yield cmd_dict


def step_out() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps out of the function call.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOut',
    }
    json = yield cmd_dict


def step_over(
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps over the statement.

    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step over.
    '''
    params: T_JSON_DICT = dict()
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOver',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Debugger.breakpointResolved')
@dataclass
class BreakpointResolved:
    '''
    Fired when breakpoint is resolved to an actual script and location.
    Deprecated in favor of ``resolvedBreakpoints`` in the ``scriptParsed`` event.
    '''
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId
    #: Actual breakpoint location.
    location: Location

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BreakpointResolved:
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location'])
        )


@event_class('Debugger.paused')
@dataclass
class Paused:
    '''
    Fired when the virtual machine stopped on breakpoint or exception or any other stop criteria.
    '''
    #: Call stack the virtual machine stopped on.
    call_frames: typing.List[CallFrame]
    #: Pause reason.
    reason: str
    #: Object containing break-specific auxiliary properties.
    data: typing.Optional[dict]
    #: Hit breakpoints IDs
    hit_breakpoints: typing.Optional[typing.List[str]]
    #: Async stack trace, if any.
    async_stack_trace: typing.Optional[runtime.StackTrace]
    #: Async stack trace, if any.
    async_stack_trace_id: typing.Optional[runtime.StackTraceId]
    #: Never present, will be removed.
    async_call_stack_trace_id: typing.Optional[runtime.StackTraceId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Paused:
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            reason=str(json['reason']),
            data=dict(json['data']) if 'data' in json else None,
            hit_breakpoints=[str(i) for i in json['hitBreakpoints']] if 'hitBreakpoints' in json else None,
            async_stack_trace=runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
            async_stack_trace_id=runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
            async_call_stack_trace_id=runtime.StackTraceId.from_json(json['asyncCallStackTraceId']) if 'asyncCallStackTraceId' in json else None
        )


@event_class('Debugger.resumed')
@dataclass
class Resumed:
    '''
    Fired when the virtual machine resumed execution.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Resumed:
        return cls(

        )


@event_class('Debugger.scriptFailedToParse')
@dataclass
class ScriptFailedToParse:
    '''
    Fired when virtual machine fails to parse the script.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptFailedToParse:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None
        )


@event_class('Debugger.scriptParsed')
@dataclass
class ScriptParsed:
    '''
    Fired when virtual machine parses script. This event is also fired for all known and uncollected
    scripts upon enabling debugger.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: True, if this script is generated as a result of the live edit operation.
    is_live_edit: typing.Optional[bool]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: If the scriptLanguage is WebAssembly, the source of debug symbols for the module.
    debug_symbols: typing.Optional[typing.List[debugger.DebugSymbols]]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]
    #: The list of set breakpoints in this script if calls to ``setBreakpointByUrl``
    #: matches this script's URL or hash. Clients that use this list can ignore the
    #: ``breakpointResolved`` event. They are equivalent.
    resolved_breakpoints: typing.Optional[typing.List[ResolvedBreakpoint]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptParsed:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            is_live_edit=bool(json['isLiveEdit']) if 'isLiveEdit' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            debug_symbols=[debugger.DebugSymbols.from_json(i) for i in json['debugSymbols']] if 'debugSymbols' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None,
            resolved_breakpoints=[ResolvedBreakpoint.from_json(i) for i in json['resolvedBreakpoints']] if 'resolvedBreakpoints' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Debugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class BreakpointId(str):
    '''
    Breakpoint identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> BreakpointId:
        return cls(json)

    def __repr__(self):
        return 'BreakpointId({})'.format(super().__repr__())


class CallFrameId(str):
    '''
    Call frame identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CallFrameId:
        return cls(json)

    def __repr__(self):
        return 'CallFrameId({})'.format(super().__repr__())


@dataclass
class Location:
    '''
    Location in the source code.
    '''
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
        )


@dataclass
class ScriptPosition:
    '''
    Location in the source code.
    '''
    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class LocationRange:
    '''
    Location range within one script.
    '''
    script_id: runtime.ScriptId

    start: ScriptPosition

    end: ScriptPosition

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['start'] = self.start.to_json()
        json['end'] = self.end.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            start=ScriptPosition.from_json(json['start']),
            end=ScriptPosition.from_json(json['end']),
        )


@dataclass
class CallFrame:
    '''
    JavaScript call frame. Array of call frames form the call stack.
    '''
    #: Call frame identifier. This identifier is only valid while the virtual machine is paused.
    call_frame_id: CallFrameId

    #: Name of the JavaScript function called on this call frame.
    function_name: str

    #: Location in the source code.
    location: Location

    #: JavaScript script name or url.
    #: Deprecated in favor of using the ``location.scriptId`` to resolve the URL via a previously
    #: sent ``Debugger.scriptParsed`` event.
    url: str

    #: Scope chain for this call frame.
    scope_chain: typing.List[Scope]

    #: ``this`` object for this call frame.
    this: runtime.RemoteObject

    #: Location in the source code.
    function_location: typing.Optional[Location] = None

    #: The value being returned, if the function is at return point.
    return_value: typing.Optional[runtime.RemoteObject] = None

    #: Valid only while the VM is paused and indicates whether this frame
    #: can be restarted or not. Note that a ``true`` value here does not
    #: guarantee that Debugger#restartFrame with this CallFrameId will be
    #: successful, but it is very likely.
    can_be_restarted: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['callFrameId'] = self.call_frame_id.to_json()
        json['functionName'] = self.function_name
        json['location'] = self.location.to_json()
        json['url'] = self.url
        json['scopeChain'] = [i.to_json() for i in self.scope_chain]
        json['this'] = self.this.to_json()
        if self.function_location is not None:
            json['functionLocation'] = self.function_location.to_json()
        if self.return_value is not None:
            json['returnValue'] = self.return_value.to_json()
        if self.can_be_restarted is not None:
            json['canBeRestarted'] = self.can_be_restarted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame_id=CallFrameId.from_json(json['callFrameId']),
            function_name=str(json['functionName']),
            location=Location.from_json(json['location']),
            url=str(json['url']),
            scope_chain=[Scope.from_json(i) for i in json['scopeChain']],
            this=runtime.RemoteObject.from_json(json['this']),
            function_location=Location.from_json(json['functionLocation']) if 'functionLocation' in json else None,
            return_value=runtime.RemoteObject.from_json(json['returnValue']) if 'returnValue' in json else None,
            can_be_restarted=bool(json['canBeRestarted']) if 'canBeRestarted' in json else None,
        )


@dataclass
class Scope:
    '''
    Scope description.
    '''
    #: Scope type.
    type_: str

    #: Object representing the scope. For ``global`` and ``with`` scopes it represents the actual
    #: object; for the rest of the scopes, it is artificial transient object enumerating scope
    #: variables as its properties.
    object_: runtime.RemoteObject

    name: typing.Optional[str] = None

    #: Location in the source code where scope starts
    start_location: typing.Optional[Location] = None

    #: Location in the source code where scope ends
    end_location: typing.Optional[Location] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['object'] = self.object_.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.start_location is not None:
            json['startLocation'] = self.start_location.to_json()
        if self.end_location is not None:
            json['endLocation'] = self.end_location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            object_=runtime.RemoteObject.from_json(json['object']),
            name=str(json['name']) if 'name' in json else None,
            start_location=Location.from_json(json['startLocation']) if 'startLocation' in json else None,
            end_location=Location.from_json(json['endLocation']) if 'endLocation' in json else None,
        )


@dataclass
class SearchMatch:
    '''
    Search match for resource.
    '''
    #: Line number in resource content.
    line_number: float

    #: Line with match content.
    line_content: str

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['lineContent'] = self.line_content
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=float(json['lineNumber']),
            line_content=str(json['lineContent']),
        )


@dataclass
class BreakLocation:
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


@dataclass
class WasmDisassemblyChunk:
    #: The next chunk of disassembled lines.
    lines: typing.List[str]

    #: The bytecode offsets describing the start of each line.
    bytecode_offsets: typing.List[int]

    def to_json(self):
        json = dict()
        json['lines'] = [i for i in self.lines]
        json['bytecodeOffsets'] = [i for i in self.bytecode_offsets]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lines=[str(i) for i in json['lines']],
            bytecode_offsets=[int(i) for i in json['bytecodeOffsets']],
        )


class ScriptLanguage(enum.Enum):
    '''
    Enum of possible script languages.
    '''
    JAVA_SCRIPT = "JavaScript"
    WEB_ASSEMBLY = "WebAssembly"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DebugSymbols:
    '''
    Debug symbols available for a wasm script.
    '''
    #: Type of the debug symbols.
    type_: str

    #: URL of the external symbol source.
    external_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.external_url is not None:
            json['externalURL'] = self.external_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            external_url=str(json['externalURL']) if 'externalURL' in json else None,
        )


@dataclass
class ResolvedBreakpoint:
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId

    #: Actual breakpoint location.
    location: Location

    def to_json(self):
        json = dict()
        json['breakpointId'] = self.breakpoint_id.to_json()
        json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location']),
        )


def continue_to_location(
        location: Location,
        target_call_frames: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues execution until specific location is reached.

    :param location: Location to continue to.
    :param target_call_frames: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if target_call_frames is not None:
        params['targetCallFrames'] = target_call_frames
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.continueToLocation',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables debugger for given page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disable',
    }
    json = yield cmd_dict


def enable(
        max_scripts_cache_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.UniqueDebuggerId]:
    '''
    Enables debugger for the given page. Clients should not assume that the debugging has been
    enabled until the result for this command is received.

    :param max_scripts_cache_size: **(EXPERIMENTAL)** *(Optional)* The maximum size in bytes of collected scripts (not referenced by other heap objects) the debugger can hold. Puts no limit if parameter is omitted.
    :returns: Unique identifier of the debugger.
    '''
    params: T_JSON_DICT = dict()
    if max_scripts_cache_size is not None:
        params['maxScriptsCacheSize'] = max_scripts_cache_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.enable',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.UniqueDebuggerId.from_json(json['debuggerId'])


def evaluate_on_call_frame(
        call_frame_id: CallFrameId,
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[runtime.TimeDelta] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[runtime.RemoteObject, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Evaluates expression on a given call frame.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* String object group name to put result into (allows rapid releasing resulting object handles using ```releaseObjectGroup````).
    :param include_command_line_api: *(Optional)* Specifies whether command line API should be available to the evaluated expression, defaults to false.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ````setPauseOnException``` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param throw_on_side_effect: *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :returns: A tuple with the following items:

        0. **result** - Object wrapper for the evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.evaluateOnCallFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        runtime.RemoteObject.from_json(json['result']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_possible_breakpoints(
        start: Location,
        end: typing.Optional[Location] = None,
        restrict_to_function: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[BreakLocation]]:
    '''
    Returns possible locations for breakpoint. scriptId in start and end range locations should be
    the same.

    :param start: Start of range to search possible breakpoint locations in.
    :param end: *(Optional)* End of range to search possible breakpoint locations in (excluding). When not specified, end of scripts is used as end of range.
    :param restrict_to_function: *(Optional)* Only consider locations which are in the same (non-nested) function as start.
    :returns: List of the possible breakpoint locations.
    '''
    params: T_JSON_DICT = dict()
    params['start'] = start.to_json()
    if end is not None:
        params['end'] = end.to_json()
    if restrict_to_function is not None:
        params['restrictToFunction'] = restrict_to_function
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getPossibleBreakpoints',
        'params': params,
    }
    json = yield cmd_dict
    return [BreakLocation.from_json(i) for i in json['locations']]


def get_script_source(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, typing.Optional[str]]]:
    '''
    Returns source for the script with given id.

    :param script_id: Id of the script to get source for.
    :returns: A tuple with the following items:

        0. **scriptSource** - Script source (empty in case of Wasm bytecode).
        1. **bytecode** - *(Optional)* Wasm bytecode.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['scriptSource']),
        str(json['bytecode']) if 'bytecode' in json else None
    )


def disassemble_wasm_module(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, typing.List[int], WasmDisassemblyChunk]]:
    '''


    **EXPERIMENTAL**

    :param script_id: Id of the script to disassemble
    :returns: A tuple with the following items:

        0. **streamId** - *(Optional)* For large modules, return a stream from which additional chunks of disassembly can be read successively.
        1. **totalNumberOfLines** - The total number of lines in the disassembly text.
        2. **functionBodyOffsets** - The offsets of all function bodies, in the format [start1, end1, start2, end2, ...] where all ends are exclusive.
        3. **chunk** - The first chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disassembleWasmModule',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['streamId']) if 'streamId' in json else None,
        int(json['totalNumberOfLines']),
        [int(i) for i in json['functionBodyOffsets']],
        WasmDisassemblyChunk.from_json(json['chunk'])
    )


def next_wasm_disassembly_chunk(
        stream_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,WasmDisassemblyChunk]:
    '''
    Disassemble the next chunk of lines for the module corresponding to the
    stream. If disassembly is complete, this API will invalidate the streamId
    and return an empty chunk. Any subsequent calls for the now invalid stream
    will return errors.

    **EXPERIMENTAL**

    :param stream_id:
    :returns: The next chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['streamId'] = stream_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.nextWasmDisassemblyChunk',
        'params': params,
    }
    json = yield cmd_dict
    return WasmDisassemblyChunk.from_json(json['chunk'])


def get_wasm_bytecode(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    This command is deprecated. Use getScriptSource instead.

    :param script_id: Id of the Wasm script to get source for.
    :returns: Script source.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getWasmBytecode',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['bytecode'])


def get_stack_trace(
        stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.StackTrace]:
    '''
    Returns stack trace with given ``stackTraceId``.

    **EXPERIMENTAL**

    :param stack_trace_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['stackTraceId'] = stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getStackTrace',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.StackTrace.from_json(json['stackTrace'])


def pause() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops on the next JavaScript statement.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pause',
    }
    json = yield cmd_dict


def pause_on_async_call(
        parent_stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param parent_stack_trace_id: Debugger will pause when async call with given stack trace is started.
    '''
    params: T_JSON_DICT = dict()
    params['parentStackTraceId'] = parent_stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pauseOnAsyncCall',
        'params': params,
    }
    json = yield cmd_dict


def remove_breakpoint(
        breakpoint_id: BreakpointId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes JavaScript breakpoint.

    :param breakpoint_id:
    '''
    params: T_JSON_DICT = dict()
    params['breakpointId'] = breakpoint_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.removeBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def restart_frame(
        call_frame_id: CallFrameId,
        mode: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[CallFrame], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId]]]:
    '''
    Restarts particular call frame from the beginning. The old, deprecated
    behavior of ``restartFrame`` is to stay paused and allow further CDP commands
    after a restart was scheduled. This can cause problems with restarting, so
    we now continue execution immediatly after it has been scheduled until we
    reach the beginning of the restarted frame.

    To stay back-wards compatible, ``restartFrame`` now expects a ``mode``
    parameter to be present. If the ``mode`` parameter is missing, ``restartFrame``
    errors out.

    The various return values are deprecated and ``callFrames`` is always empty.
    Use the call frames from the ``Debugger#paused`` events instead, that fires
    once V8 pauses at the beginning of the restarted function.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param mode: **(EXPERIMENTAL)** *(Optional)* The ```mode```` parameter must be present and set to 'StepInto', otherwise ````restartFrame``` will error out.
    :returns: A tuple with the following items:

        0. **callFrames** - New stack trace.
        1. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        2. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    if mode is not None:
        params['mode'] = mode
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.restartFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']],
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None
    )


def resume(
        terminate_on_resume: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resumes JavaScript execution.

    :param terminate_on_resume: *(Optional)* Set to true to terminate execution upon resuming execution. In contrast to Runtime.terminateExecution, this will allows to execute further JavaScript (i.e. via evaluation) until execution of the paused code is actually resumed, at which point termination is triggered. If execution is currently not paused, this parameter has no effect.
    '''
    params: T_JSON_DICT = dict()
    if terminate_on_resume is not None:
        params['terminateOnResume'] = terminate_on_resume
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.resume',
        'params': params,
    }
    json = yield cmd_dict


def search_in_content(
        script_id: runtime.ScriptId,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SearchMatch]]:
    '''
    Searches for given string in script content.

    :param script_id: Id of the script to search in.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.searchInContent',
        'params': params,
    }
    json = yield cmd_dict
    return [SearchMatch.from_json(i) for i in json['result']]


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_execution_contexts(
        unique_ids: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox execution contexts with passed ones. Forces backend to skip
    stepping/pausing in scripts in these execution contexts. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param unique_ids: Array of execution context unique ids for the debugger to ignore.
    '''
    params: T_JSON_DICT = dict()
    params['uniqueIds'] = [i for i in unique_ids]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxExecutionContexts',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_patterns(
        patterns: typing.List[str],
        skip_anonymous: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox patterns with passed ones. Forces backend to skip stepping/pausing in
    scripts with url matching one of the patterns. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param patterns: Array of regexps that will be used to check script url for blackbox state.
    :param skip_anonymous: *(Optional)* If true, also ignore scripts with no source url.
    '''
    params: T_JSON_DICT = dict()
    params['patterns'] = [i for i in patterns]
    if skip_anonymous is not None:
        params['skipAnonymous'] = skip_anonymous
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxPatterns',
        'params': params,
    }
    json = yield cmd_dict


def set_blackboxed_ranges(
        script_id: runtime.ScriptId,
        positions: typing.List[ScriptPosition]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes backend skip steps in the script in blackboxed ranges. VM will try leave blacklisted
    scripts by performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
    Positions array contains positions where blackbox state is changed. First interval isn't
    blackboxed. Array should be sorted.

    **EXPERIMENTAL**

    :param script_id: Id of the script.
    :param positions:
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['positions'] = [i.to_json() for i in positions]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxedRanges',
        'params': params,
    }
    json = yield cmd_dict


def set_breakpoint(
        location: Location,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, Location]]:
    '''
    Sets JavaScript breakpoint at a given location.

    :param location: Location to set breakpoint in.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **actualLocation** - Location this breakpoint resolved into.
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        Location.from_json(json['actualLocation'])
    )


def set_instrumentation_breakpoint(
        instrumentation: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets instrumentation breakpoint.

    :param instrumentation: Instrumentation name.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['instrumentation'] = instrumentation
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoint_by_url(
        line_number: int,
        url: typing.Optional[str] = None,
        url_regex: typing.Optional[str] = None,
        script_hash: typing.Optional[str] = None,
        column_number: typing.Optional[int] = None,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, typing.List[Location]]]:
    '''
    Sets JavaScript breakpoint at given location specified either by URL or URL regex. Once this
    command is issued, all existing parsed scripts will have breakpoints resolved and returned in
    ``locations`` property. Further matching script parsing will result in subsequent
    ``breakpointResolved`` events issued. This logical breakpoint will survive page reloads.

    :param line_number: Line number to set breakpoint at.
    :param url: *(Optional)* URL of the resources to set breakpoint on.
    :param url_regex: *(Optional)* Regex pattern for the URLs of the resources to set breakpoints on. Either ```url```` or ````urlRegex``` must be specified.
    :param script_hash: *(Optional)* Script hash of the resources to set breakpoint on.
    :param column_number: *(Optional)* Offset in the line to set breakpoint at.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **locations** - List of the locations this breakpoint resolved into upon addition.
    '''
    params: T_JSON_DICT = dict()
    params['lineNumber'] = line_number
    if url is not None:
        params['url'] = url
    if url_regex is not None:
        params['urlRegex'] = url_regex
    if script_hash is not None:
        params['scriptHash'] = script_hash
    if column_number is not None:
        params['columnNumber'] = column_number
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointByUrl',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        [Location.from_json(i) for i in json['locations']]
    )


def set_breakpoint_on_function_call(
        object_id: runtime.RemoteObjectId,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets JavaScript breakpoint before each call to the given function.
    If another function was created from the same source as a given one,
    calling it will also trigger the breakpoint.

    **EXPERIMENTAL**

    :param object_id: Function object id.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will stop on the breakpoint if this expression evaluates to true.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointOnFunctionCall',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoints_active(
        active: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates / deactivates all breakpoints on the page.

    :param active: New value for breakpoints active state.
    '''
    params: T_JSON_DICT = dict()
    params['active'] = active
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointsActive',
        'params': params,
    }
    json = yield cmd_dict


def set_pause_on_exceptions(
        state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Defines pause on exceptions state. Can be set to stop on all exceptions, uncaught exceptions,
    or caught exceptions, no exceptions. Initial pause on exceptions state is ``none``.

    :param state: Pause on exceptions mode.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setPauseOnExceptions',
        'params': params,
    }
    json = yield cmd_dict


def set_return_value(
        new_value: runtime.CallArgument
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes return value in top frame. Available only at return break position.

    **EXPERIMENTAL**

    :param new_value: New return value.
    '''
    params: T_JSON_DICT = dict()
    params['newValue'] = new_value.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setReturnValue',
        'params': params,
    }
    json = yield cmd_dict


def set_script_source(
        script_id: runtime.ScriptId,
        script_source: str,
        dry_run: typing.Optional[bool] = None,
        allow_top_frame_editing: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[typing.List[CallFrame]], typing.Optional[bool], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId], str, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Edits JavaScript source live.

    In general, functions that are currently on the stack can not be edited with
    a single exception: If the edited function is the top-most stack frame and
    that is the only activation of that function on the stack. In this case
    the live edit will be successful and a ``Debugger.restartFrame`` for the
    top-most function is automatically triggered.

    :param script_id: Id of the script to edit.
    :param script_source: New content of the script.
    :param dry_run: *(Optional)* If true the change will not actually be applied. Dry run may be used to get result description without actually modifying the code.
    :param allow_top_frame_editing: **(EXPERIMENTAL)** *(Optional)* If true, then ```scriptSource```` is allowed to change the function on top of the stack as long as the top-most stack frame is the only activation of that function.
    :returns: A tuple with the following items:

        0. **callFrames** - *(Optional)* New stack trace in case editing has happened while VM was stopped.
        1. **stackChanged** - *(Optional)* Whether current call stack  was modified after applying the changes.
        2. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        3. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
        4. **status** - Whether the operation was successful or not. Only `` Ok`` denotes a successful live edit while the other enum variants denote why the live edit failed.
        5. **exceptionDetails** - *(Optional)* Exception details if any. Only present when `` status`` is `` CompileError`.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['scriptSource'] = script_source
    if dry_run is not None:
        params['dryRun'] = dry_run
    if allow_top_frame_editing is not None:
        params['allowTopFrameEditing'] = allow_top_frame_editing
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']] if 'callFrames' in json else None,
        bool(json['stackChanged']) if 'stackChanged' in json else None,
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
        str(json['status']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_skip_all_pauses(
        skip: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes page not interrupt on any pauses (breakpoint, exception, dom exception etc).

    :param skip: New value for skip pauses state.
    '''
    params: T_JSON_DICT = dict()
    params['skip'] = skip
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setSkipAllPauses',
        'params': params,
    }
    json = yield cmd_dict


def set_variable_value(
        scope_number: int,
        variable_name: str,
        new_value: runtime.CallArgument,
        call_frame_id: CallFrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes value of variable in a callframe. Object-based scopes are not supported and must be
    mutated manually.

    :param scope_number: 0-based number of scope as was listed in scope chain. Only 'local', 'closure' and 'catch' scope types are allowed. Other scopes could be manipulated manually.
    :param variable_name: Variable name.
    :param new_value: New variable value.
    :param call_frame_id: Id of callframe that holds variable.
    '''
    params: T_JSON_DICT = dict()
    params['scopeNumber'] = scope_number
    params['variableName'] = variable_name
    params['newValue'] = new_value.to_json()
    params['callFrameId'] = call_frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setVariableValue',
        'params': params,
    }
    json = yield cmd_dict


def step_into(
        break_on_async_call: typing.Optional[bool] = None,
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps into the function call.

    :param break_on_async_call: **(EXPERIMENTAL)** *(Optional)* Debugger will pause on the execution of the first async task which was scheduled before next pause.
    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step into.
    '''
    params: T_JSON_DICT = dict()
    if break_on_async_call is not None:
        params['breakOnAsyncCall'] = break_on_async_call
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepInto',
        'params': params,
    }
    json = yield cmd_dict


def step_out() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps out of the function call.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOut',
    }
    json = yield cmd_dict


def step_over(
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps over the statement.

    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step over.
    '''
    params: T_JSON_DICT = dict()
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOver',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Debugger.breakpointResolved')
@dataclass
class BreakpointResolved:
    '''
    Fired when breakpoint is resolved to an actual script and location.
    Deprecated in favor of ``resolvedBreakpoints`` in the ``scriptParsed`` event.
    '''
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId
    #: Actual breakpoint location.
    location: Location

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BreakpointResolved:
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location'])
        )


@event_class('Debugger.paused')
@dataclass
class Paused:
    '''
    Fired when the virtual machine stopped on breakpoint or exception or any other stop criteria.
    '''
    #: Call stack the virtual machine stopped on.
    call_frames: typing.List[CallFrame]
    #: Pause reason.
    reason: str
    #: Object containing break-specific auxiliary properties.
    data: typing.Optional[dict]
    #: Hit breakpoints IDs
    hit_breakpoints: typing.Optional[typing.List[str]]
    #: Async stack trace, if any.
    async_stack_trace: typing.Optional[runtime.StackTrace]
    #: Async stack trace, if any.
    async_stack_trace_id: typing.Optional[runtime.StackTraceId]
    #: Never present, will be removed.
    async_call_stack_trace_id: typing.Optional[runtime.StackTraceId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Paused:
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            reason=str(json['reason']),
            data=dict(json['data']) if 'data' in json else None,
            hit_breakpoints=[str(i) for i in json['hitBreakpoints']] if 'hitBreakpoints' in json else None,
            async_stack_trace=runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
            async_stack_trace_id=runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
            async_call_stack_trace_id=runtime.StackTraceId.from_json(json['asyncCallStackTraceId']) if 'asyncCallStackTraceId' in json else None
        )


@event_class('Debugger.resumed')
@dataclass
class Resumed:
    '''
    Fired when the virtual machine resumed execution.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Resumed:
        return cls(

        )


@event_class('Debugger.scriptFailedToParse')
@dataclass
class ScriptFailedToParse:
    '''
    Fired when virtual machine fails to parse the script.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptFailedToParse:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None
        )


@event_class('Debugger.scriptParsed')
@dataclass
class ScriptParsed:
    '''
    Fired when virtual machine parses script. This event is also fired for all known and uncollected
    scripts upon enabling debugger.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: True, if this script is generated as a result of the live edit operation.
    is_live_edit: typing.Optional[bool]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: If the scriptLanguage is WebAssembly, the source of debug symbols for the module.
    debug_symbols: typing.Optional[typing.List[debugger.DebugSymbols]]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]
    #: The list of set breakpoints in this script if calls to ``setBreakpointByUrl``
    #: matches this script's URL or hash. Clients that use this list can ignore the
    #: ``breakpointResolved`` event. They are equivalent.
    resolved_breakpoints: typing.Optional[typing.List[ResolvedBreakpoint]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptParsed:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            is_live_edit=bool(json['isLiveEdit']) if 'isLiveEdit' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            debug_symbols=[debugger.DebugSymbols.from_json(i) for i in json['debugSymbols']] if 'debugSymbols' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None,
            resolved_breakpoints=[ResolvedBreakpoint.from_json(i) for i in json['resolvedBreakpoints']] if 'resolvedBreakpoints' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\debugger.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Debugger
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime


class BreakpointId(str):
    '''
    Breakpoint identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> BreakpointId:
        return cls(json)

    def __repr__(self):
        return 'BreakpointId({})'.format(super().__repr__())


class CallFrameId(str):
    '''
    Call frame identifier.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CallFrameId:
        return cls(json)

    def __repr__(self):
        return 'CallFrameId({})'.format(super().__repr__())


@dataclass
class Location:
    '''
    Location in the source code.
    '''
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
        )


@dataclass
class ScriptPosition:
    '''
    Location in the source code.
    '''
    line_number: int

    column_number: int

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['columnNumber'] = self.column_number
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']),
        )


@dataclass
class LocationRange:
    '''
    Location range within one script.
    '''
    script_id: runtime.ScriptId

    start: ScriptPosition

    end: ScriptPosition

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['start'] = self.start.to_json()
        json['end'] = self.end.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            start=ScriptPosition.from_json(json['start']),
            end=ScriptPosition.from_json(json['end']),
        )


@dataclass
class CallFrame:
    '''
    JavaScript call frame. Array of call frames form the call stack.
    '''
    #: Call frame identifier. This identifier is only valid while the virtual machine is paused.
    call_frame_id: CallFrameId

    #: Name of the JavaScript function called on this call frame.
    function_name: str

    #: Location in the source code.
    location: Location

    #: JavaScript script name or url.
    #: Deprecated in favor of using the ``location.scriptId`` to resolve the URL via a previously
    #: sent ``Debugger.scriptParsed`` event.
    url: str

    #: Scope chain for this call frame.
    scope_chain: typing.List[Scope]

    #: ``this`` object for this call frame.
    this: runtime.RemoteObject

    #: Location in the source code.
    function_location: typing.Optional[Location] = None

    #: The value being returned, if the function is at return point.
    return_value: typing.Optional[runtime.RemoteObject] = None

    #: Valid only while the VM is paused and indicates whether this frame
    #: can be restarted or not. Note that a ``true`` value here does not
    #: guarantee that Debugger#restartFrame with this CallFrameId will be
    #: successful, but it is very likely.
    can_be_restarted: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        json['callFrameId'] = self.call_frame_id.to_json()
        json['functionName'] = self.function_name
        json['location'] = self.location.to_json()
        json['url'] = self.url
        json['scopeChain'] = [i.to_json() for i in self.scope_chain]
        json['this'] = self.this.to_json()
        if self.function_location is not None:
            json['functionLocation'] = self.function_location.to_json()
        if self.return_value is not None:
            json['returnValue'] = self.return_value.to_json()
        if self.can_be_restarted is not None:
            json['canBeRestarted'] = self.can_be_restarted
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            call_frame_id=CallFrameId.from_json(json['callFrameId']),
            function_name=str(json['functionName']),
            location=Location.from_json(json['location']),
            url=str(json['url']),
            scope_chain=[Scope.from_json(i) for i in json['scopeChain']],
            this=runtime.RemoteObject.from_json(json['this']),
            function_location=Location.from_json(json['functionLocation']) if 'functionLocation' in json else None,
            return_value=runtime.RemoteObject.from_json(json['returnValue']) if 'returnValue' in json else None,
            can_be_restarted=bool(json['canBeRestarted']) if 'canBeRestarted' in json else None,
        )


@dataclass
class Scope:
    '''
    Scope description.
    '''
    #: Scope type.
    type_: str

    #: Object representing the scope. For ``global`` and ``with`` scopes it represents the actual
    #: object; for the rest of the scopes, it is artificial transient object enumerating scope
    #: variables as its properties.
    object_: runtime.RemoteObject

    name: typing.Optional[str] = None

    #: Location in the source code where scope starts
    start_location: typing.Optional[Location] = None

    #: Location in the source code where scope ends
    end_location: typing.Optional[Location] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        json['object'] = self.object_.to_json()
        if self.name is not None:
            json['name'] = self.name
        if self.start_location is not None:
            json['startLocation'] = self.start_location.to_json()
        if self.end_location is not None:
            json['endLocation'] = self.end_location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            object_=runtime.RemoteObject.from_json(json['object']),
            name=str(json['name']) if 'name' in json else None,
            start_location=Location.from_json(json['startLocation']) if 'startLocation' in json else None,
            end_location=Location.from_json(json['endLocation']) if 'endLocation' in json else None,
        )


@dataclass
class SearchMatch:
    '''
    Search match for resource.
    '''
    #: Line number in resource content.
    line_number: float

    #: Line with match content.
    line_content: str

    def to_json(self):
        json = dict()
        json['lineNumber'] = self.line_number
        json['lineContent'] = self.line_content
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            line_number=float(json['lineNumber']),
            line_content=str(json['lineContent']),
        )


@dataclass
class BreakLocation:
    #: Script identifier as reported in the ``Debugger.scriptParsed``.
    script_id: runtime.ScriptId

    #: Line number in the script (0-based).
    line_number: int

    #: Column number in the script (0-based).
    column_number: typing.Optional[int] = None

    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['scriptId'] = self.script_id.to_json()
        json['lineNumber'] = self.line_number
        if self.column_number is not None:
            json['columnNumber'] = self.column_number
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            line_number=int(json['lineNumber']),
            column_number=int(json['columnNumber']) if 'columnNumber' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


@dataclass
class WasmDisassemblyChunk:
    #: The next chunk of disassembled lines.
    lines: typing.List[str]

    #: The bytecode offsets describing the start of each line.
    bytecode_offsets: typing.List[int]

    def to_json(self):
        json = dict()
        json['lines'] = [i for i in self.lines]
        json['bytecodeOffsets'] = [i for i in self.bytecode_offsets]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lines=[str(i) for i in json['lines']],
            bytecode_offsets=[int(i) for i in json['bytecodeOffsets']],
        )


class ScriptLanguage(enum.Enum):
    '''
    Enum of possible script languages.
    '''
    JAVA_SCRIPT = "JavaScript"
    WEB_ASSEMBLY = "WebAssembly"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DebugSymbols:
    '''
    Debug symbols available for a wasm script.
    '''
    #: Type of the debug symbols.
    type_: str

    #: URL of the external symbol source.
    external_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.external_url is not None:
            json['externalURL'] = self.external_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            external_url=str(json['externalURL']) if 'externalURL' in json else None,
        )


@dataclass
class ResolvedBreakpoint:
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId

    #: Actual breakpoint location.
    location: Location

    def to_json(self):
        json = dict()
        json['breakpointId'] = self.breakpoint_id.to_json()
        json['location'] = self.location.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location']),
        )


def continue_to_location(
        location: Location,
        target_call_frames: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Continues execution until specific location is reached.

    :param location: Location to continue to.
    :param target_call_frames: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if target_call_frames is not None:
        params['targetCallFrames'] = target_call_frames
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.continueToLocation',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables debugger for given page.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disable',
    }
    json = yield cmd_dict


def enable(
        max_scripts_cache_size: typing.Optional[float] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.UniqueDebuggerId]:
    '''
    Enables debugger for the given page. Clients should not assume that the debugging has been
    enabled until the result for this command is received.

    :param max_scripts_cache_size: **(EXPERIMENTAL)** *(Optional)* The maximum size in bytes of collected scripts (not referenced by other heap objects) the debugger can hold. Puts no limit if parameter is omitted.
    :returns: Unique identifier of the debugger.
    '''
    params: T_JSON_DICT = dict()
    if max_scripts_cache_size is not None:
        params['maxScriptsCacheSize'] = max_scripts_cache_size
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.enable',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.UniqueDebuggerId.from_json(json['debuggerId'])


def evaluate_on_call_frame(
        call_frame_id: CallFrameId,
        expression: str,
        object_group: typing.Optional[str] = None,
        include_command_line_api: typing.Optional[bool] = None,
        silent: typing.Optional[bool] = None,
        return_by_value: typing.Optional[bool] = None,
        generate_preview: typing.Optional[bool] = None,
        throw_on_side_effect: typing.Optional[bool] = None,
        timeout: typing.Optional[runtime.TimeDelta] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[runtime.RemoteObject, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Evaluates expression on a given call frame.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param expression: Expression to evaluate.
    :param object_group: *(Optional)* String object group name to put result into (allows rapid releasing resulting object handles using ```releaseObjectGroup````).
    :param include_command_line_api: *(Optional)* Specifies whether command line API should be available to the evaluated expression, defaults to false.
    :param silent: *(Optional)* In silent mode exceptions thrown during evaluation are not reported and do not pause execution. Overrides ````setPauseOnException``` state.
    :param return_by_value: *(Optional)* Whether the result is expected to be a JSON object that should be sent by value.
    :param generate_preview: **(EXPERIMENTAL)** *(Optional)* Whether preview should be generated for the result.
    :param throw_on_side_effect: *(Optional)* Whether to throw an exception if side effect cannot be ruled out during evaluation.
    :param timeout: **(EXPERIMENTAL)** *(Optional)* Terminate execution after timing out (number of milliseconds).
    :returns: A tuple with the following items:

        0. **result** - Object wrapper for the evaluation result.
        1. **exceptionDetails** - *(Optional)* Exception details.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    params['expression'] = expression
    if object_group is not None:
        params['objectGroup'] = object_group
    if include_command_line_api is not None:
        params['includeCommandLineAPI'] = include_command_line_api
    if silent is not None:
        params['silent'] = silent
    if return_by_value is not None:
        params['returnByValue'] = return_by_value
    if generate_preview is not None:
        params['generatePreview'] = generate_preview
    if throw_on_side_effect is not None:
        params['throwOnSideEffect'] = throw_on_side_effect
    if timeout is not None:
        params['timeout'] = timeout.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.evaluateOnCallFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        runtime.RemoteObject.from_json(json['result']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def get_possible_breakpoints(
        start: Location,
        end: typing.Optional[Location] = None,
        restrict_to_function: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[BreakLocation]]:
    '''
    Returns possible locations for breakpoint. scriptId in start and end range locations should be
    the same.

    :param start: Start of range to search possible breakpoint locations in.
    :param end: *(Optional)* End of range to search possible breakpoint locations in (excluding). When not specified, end of scripts is used as end of range.
    :param restrict_to_function: *(Optional)* Only consider locations which are in the same (non-nested) function as start.
    :returns: List of the possible breakpoint locations.
    '''
    params: T_JSON_DICT = dict()
    params['start'] = start.to_json()
    if end is not None:
        params['end'] = end.to_json()
    if restrict_to_function is not None:
        params['restrictToFunction'] = restrict_to_function
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getPossibleBreakpoints',
        'params': params,
    }
    json = yield cmd_dict
    return [BreakLocation.from_json(i) for i in json['locations']]


def get_script_source(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[str, typing.Optional[str]]]:
    '''
    Returns source for the script with given id.

    :param script_id: Id of the script to get source for.
    :returns: A tuple with the following items:

        0. **scriptSource** - Script source (empty in case of Wasm bytecode).
        1. **bytecode** - *(Optional)* Wasm bytecode.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['scriptSource']),
        str(json['bytecode']) if 'bytecode' in json else None
    )


def disassemble_wasm_module(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[str], int, typing.List[int], WasmDisassemblyChunk]]:
    '''


    **EXPERIMENTAL**

    :param script_id: Id of the script to disassemble
    :returns: A tuple with the following items:

        0. **streamId** - *(Optional)* For large modules, return a stream from which additional chunks of disassembly can be read successively.
        1. **totalNumberOfLines** - The total number of lines in the disassembly text.
        2. **functionBodyOffsets** - The offsets of all function bodies, in the format [start1, end1, start2, end2, ...] where all ends are exclusive.
        3. **chunk** - The first chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.disassembleWasmModule',
        'params': params,
    }
    json = yield cmd_dict
    return (
        str(json['streamId']) if 'streamId' in json else None,
        int(json['totalNumberOfLines']),
        [int(i) for i in json['functionBodyOffsets']],
        WasmDisassemblyChunk.from_json(json['chunk'])
    )


def next_wasm_disassembly_chunk(
        stream_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,WasmDisassemblyChunk]:
    '''
    Disassemble the next chunk of lines for the module corresponding to the
    stream. If disassembly is complete, this API will invalidate the streamId
    and return an empty chunk. Any subsequent calls for the now invalid stream
    will return errors.

    **EXPERIMENTAL**

    :param stream_id:
    :returns: The next chunk of disassembly.
    '''
    params: T_JSON_DICT = dict()
    params['streamId'] = stream_id
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.nextWasmDisassemblyChunk',
        'params': params,
    }
    json = yield cmd_dict
    return WasmDisassemblyChunk.from_json(json['chunk'])


def get_wasm_bytecode(
        script_id: runtime.ScriptId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    This command is deprecated. Use getScriptSource instead.

    :param script_id: Id of the Wasm script to get source for.
    :returns: Script source.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getWasmBytecode',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['bytecode'])


def get_stack_trace(
        stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,runtime.StackTrace]:
    '''
    Returns stack trace with given ``stackTraceId``.

    **EXPERIMENTAL**

    :param stack_trace_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['stackTraceId'] = stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.getStackTrace',
        'params': params,
    }
    json = yield cmd_dict
    return runtime.StackTrace.from_json(json['stackTrace'])


def pause() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Stops on the next JavaScript statement.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pause',
    }
    json = yield cmd_dict


def pause_on_async_call(
        parent_stack_trace_id: runtime.StackTraceId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''


    **EXPERIMENTAL**

    :param parent_stack_trace_id: Debugger will pause when async call with given stack trace is started.
    '''
    params: T_JSON_DICT = dict()
    params['parentStackTraceId'] = parent_stack_trace_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.pauseOnAsyncCall',
        'params': params,
    }
    json = yield cmd_dict


def remove_breakpoint(
        breakpoint_id: BreakpointId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes JavaScript breakpoint.

    :param breakpoint_id:
    '''
    params: T_JSON_DICT = dict()
    params['breakpointId'] = breakpoint_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.removeBreakpoint',
        'params': params,
    }
    json = yield cmd_dict


def restart_frame(
        call_frame_id: CallFrameId,
        mode: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[CallFrame], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId]]]:
    '''
    Restarts particular call frame from the beginning. The old, deprecated
    behavior of ``restartFrame`` is to stay paused and allow further CDP commands
    after a restart was scheduled. This can cause problems with restarting, so
    we now continue execution immediatly after it has been scheduled until we
    reach the beginning of the restarted frame.

    To stay back-wards compatible, ``restartFrame`` now expects a ``mode``
    parameter to be present. If the ``mode`` parameter is missing, ``restartFrame``
    errors out.

    The various return values are deprecated and ``callFrames`` is always empty.
    Use the call frames from the ``Debugger#paused`` events instead, that fires
    once V8 pauses at the beginning of the restarted function.

    :param call_frame_id: Call frame identifier to evaluate on.
    :param mode: **(EXPERIMENTAL)** *(Optional)* The ```mode```` parameter must be present and set to 'StepInto', otherwise ````restartFrame``` will error out.
    :returns: A tuple with the following items:

        0. **callFrames** - New stack trace.
        1. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        2. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
    '''
    params: T_JSON_DICT = dict()
    params['callFrameId'] = call_frame_id.to_json()
    if mode is not None:
        params['mode'] = mode
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.restartFrame',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']],
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None
    )


def resume(
        terminate_on_resume: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resumes JavaScript execution.

    :param terminate_on_resume: *(Optional)* Set to true to terminate execution upon resuming execution. In contrast to Runtime.terminateExecution, this will allows to execute further JavaScript (i.e. via evaluation) until execution of the paused code is actually resumed, at which point termination is triggered. If execution is currently not paused, this parameter has no effect.
    '''
    params: T_JSON_DICT = dict()
    if terminate_on_resume is not None:
        params['terminateOnResume'] = terminate_on_resume
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.resume',
        'params': params,
    }
    json = yield cmd_dict


def search_in_content(
        script_id: runtime.ScriptId,
        query: str,
        case_sensitive: typing.Optional[bool] = None,
        is_regex: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[SearchMatch]]:
    '''
    Searches for given string in script content.

    :param script_id: Id of the script to search in.
    :param query: String to search for.
    :param case_sensitive: *(Optional)* If true, search is case sensitive.
    :param is_regex: *(Optional)* If true, treats string parameter as regex.
    :returns: List of search matches.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['query'] = query
    if case_sensitive is not None:
        params['caseSensitive'] = case_sensitive
    if is_regex is not None:
        params['isRegex'] = is_regex
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.searchInContent',
        'params': params,
    }
    json = yield cmd_dict
    return [SearchMatch.from_json(i) for i in json['result']]


def set_async_call_stack_depth(
        max_depth: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables or disables async call stacks tracking.

    :param max_depth: Maximum depth of async call stacks. Setting to ```0``` will effectively disable collecting async call stacks (default).
    '''
    params: T_JSON_DICT = dict()
    params['maxDepth'] = max_depth
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setAsyncCallStackDepth',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_execution_contexts(
        unique_ids: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox execution contexts with passed ones. Forces backend to skip
    stepping/pausing in scripts in these execution contexts. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param unique_ids: Array of execution context unique ids for the debugger to ignore.
    '''
    params: T_JSON_DICT = dict()
    params['uniqueIds'] = [i for i in unique_ids]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxExecutionContexts',
        'params': params,
    }
    json = yield cmd_dict


def set_blackbox_patterns(
        patterns: typing.List[str],
        skip_anonymous: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Replace previous blackbox patterns with passed ones. Forces backend to skip stepping/pausing in
    scripts with url matching one of the patterns. VM will try to leave blackboxed script by
    performing 'step in' several times, finally resorting to 'step out' if unsuccessful.

    **EXPERIMENTAL**

    :param patterns: Array of regexps that will be used to check script url for blackbox state.
    :param skip_anonymous: *(Optional)* If true, also ignore scripts with no source url.
    '''
    params: T_JSON_DICT = dict()
    params['patterns'] = [i for i in patterns]
    if skip_anonymous is not None:
        params['skipAnonymous'] = skip_anonymous
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxPatterns',
        'params': params,
    }
    json = yield cmd_dict


def set_blackboxed_ranges(
        script_id: runtime.ScriptId,
        positions: typing.List[ScriptPosition]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes backend skip steps in the script in blackboxed ranges. VM will try leave blacklisted
    scripts by performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
    Positions array contains positions where blackbox state is changed. First interval isn't
    blackboxed. Array should be sorted.

    **EXPERIMENTAL**

    :param script_id: Id of the script.
    :param positions:
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['positions'] = [i.to_json() for i in positions]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBlackboxedRanges',
        'params': params,
    }
    json = yield cmd_dict


def set_breakpoint(
        location: Location,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, Location]]:
    '''
    Sets JavaScript breakpoint at a given location.

    :param location: Location to set breakpoint in.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **actualLocation** - Location this breakpoint resolved into.
    '''
    params: T_JSON_DICT = dict()
    params['location'] = location.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        Location.from_json(json['actualLocation'])
    )


def set_instrumentation_breakpoint(
        instrumentation: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets instrumentation breakpoint.

    :param instrumentation: Instrumentation name.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['instrumentation'] = instrumentation
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setInstrumentationBreakpoint',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoint_by_url(
        line_number: int,
        url: typing.Optional[str] = None,
        url_regex: typing.Optional[str] = None,
        script_hash: typing.Optional[str] = None,
        column_number: typing.Optional[int] = None,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[BreakpointId, typing.List[Location]]]:
    '''
    Sets JavaScript breakpoint at given location specified either by URL or URL regex. Once this
    command is issued, all existing parsed scripts will have breakpoints resolved and returned in
    ``locations`` property. Further matching script parsing will result in subsequent
    ``breakpointResolved`` events issued. This logical breakpoint will survive page reloads.

    :param line_number: Line number to set breakpoint at.
    :param url: *(Optional)* URL of the resources to set breakpoint on.
    :param url_regex: *(Optional)* Regex pattern for the URLs of the resources to set breakpoints on. Either ```url```` or ````urlRegex``` must be specified.
    :param script_hash: *(Optional)* Script hash of the resources to set breakpoint on.
    :param column_number: *(Optional)* Offset in the line to set breakpoint at.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will only stop on the breakpoint if this expression evaluates to true.
    :returns: A tuple with the following items:

        0. **breakpointId** - Id of the created breakpoint for further reference.
        1. **locations** - List of the locations this breakpoint resolved into upon addition.
    '''
    params: T_JSON_DICT = dict()
    params['lineNumber'] = line_number
    if url is not None:
        params['url'] = url
    if url_regex is not None:
        params['urlRegex'] = url_regex
    if script_hash is not None:
        params['scriptHash'] = script_hash
    if column_number is not None:
        params['columnNumber'] = column_number
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointByUrl',
        'params': params,
    }
    json = yield cmd_dict
    return (
        BreakpointId.from_json(json['breakpointId']),
        [Location.from_json(i) for i in json['locations']]
    )


def set_breakpoint_on_function_call(
        object_id: runtime.RemoteObjectId,
        condition: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,BreakpointId]:
    '''
    Sets JavaScript breakpoint before each call to the given function.
    If another function was created from the same source as a given one,
    calling it will also trigger the breakpoint.

    **EXPERIMENTAL**

    :param object_id: Function object id.
    :param condition: *(Optional)* Expression to use as a breakpoint condition. When specified, debugger will stop on the breakpoint if this expression evaluates to true.
    :returns: Id of the created breakpoint for further reference.
    '''
    params: T_JSON_DICT = dict()
    params['objectId'] = object_id.to_json()
    if condition is not None:
        params['condition'] = condition
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointOnFunctionCall',
        'params': params,
    }
    json = yield cmd_dict
    return BreakpointId.from_json(json['breakpointId'])


def set_breakpoints_active(
        active: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates / deactivates all breakpoints on the page.

    :param active: New value for breakpoints active state.
    '''
    params: T_JSON_DICT = dict()
    params['active'] = active
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setBreakpointsActive',
        'params': params,
    }
    json = yield cmd_dict


def set_pause_on_exceptions(
        state: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Defines pause on exceptions state. Can be set to stop on all exceptions, uncaught exceptions,
    or caught exceptions, no exceptions. Initial pause on exceptions state is ``none``.

    :param state: Pause on exceptions mode.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setPauseOnExceptions',
        'params': params,
    }
    json = yield cmd_dict


def set_return_value(
        new_value: runtime.CallArgument
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes return value in top frame. Available only at return break position.

    **EXPERIMENTAL**

    :param new_value: New return value.
    '''
    params: T_JSON_DICT = dict()
    params['newValue'] = new_value.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setReturnValue',
        'params': params,
    }
    json = yield cmd_dict


def set_script_source(
        script_id: runtime.ScriptId,
        script_source: str,
        dry_run: typing.Optional[bool] = None,
        allow_top_frame_editing: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.Optional[typing.List[CallFrame]], typing.Optional[bool], typing.Optional[runtime.StackTrace], typing.Optional[runtime.StackTraceId], str, typing.Optional[runtime.ExceptionDetails]]]:
    '''
    Edits JavaScript source live.

    In general, functions that are currently on the stack can not be edited with
    a single exception: If the edited function is the top-most stack frame and
    that is the only activation of that function on the stack. In this case
    the live edit will be successful and a ``Debugger.restartFrame`` for the
    top-most function is automatically triggered.

    :param script_id: Id of the script to edit.
    :param script_source: New content of the script.
    :param dry_run: *(Optional)* If true the change will not actually be applied. Dry run may be used to get result description without actually modifying the code.
    :param allow_top_frame_editing: **(EXPERIMENTAL)** *(Optional)* If true, then ```scriptSource```` is allowed to change the function on top of the stack as long as the top-most stack frame is the only activation of that function.
    :returns: A tuple with the following items:

        0. **callFrames** - *(Optional)* New stack trace in case editing has happened while VM was stopped.
        1. **stackChanged** - *(Optional)* Whether current call stack  was modified after applying the changes.
        2. **asyncStackTrace** - *(Optional)* Async stack trace, if any.
        3. **asyncStackTraceId** - *(Optional)* Async stack trace, if any.
        4. **status** - Whether the operation was successful or not. Only `` Ok`` denotes a successful live edit while the other enum variants denote why the live edit failed.
        5. **exceptionDetails** - *(Optional)* Exception details if any. Only present when `` status`` is `` CompileError`.
    '''
    params: T_JSON_DICT = dict()
    params['scriptId'] = script_id.to_json()
    params['scriptSource'] = script_source
    if dry_run is not None:
        params['dryRun'] = dry_run
    if allow_top_frame_editing is not None:
        params['allowTopFrameEditing'] = allow_top_frame_editing
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setScriptSource',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [CallFrame.from_json(i) for i in json['callFrames']] if 'callFrames' in json else None,
        bool(json['stackChanged']) if 'stackChanged' in json else None,
        runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
        runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
        str(json['status']),
        runtime.ExceptionDetails.from_json(json['exceptionDetails']) if 'exceptionDetails' in json else None
    )


def set_skip_all_pauses(
        skip: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Makes page not interrupt on any pauses (breakpoint, exception, dom exception etc).

    :param skip: New value for skip pauses state.
    '''
    params: T_JSON_DICT = dict()
    params['skip'] = skip
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setSkipAllPauses',
        'params': params,
    }
    json = yield cmd_dict


def set_variable_value(
        scope_number: int,
        variable_name: str,
        new_value: runtime.CallArgument,
        call_frame_id: CallFrameId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Changes value of variable in a callframe. Object-based scopes are not supported and must be
    mutated manually.

    :param scope_number: 0-based number of scope as was listed in scope chain. Only 'local', 'closure' and 'catch' scope types are allowed. Other scopes could be manipulated manually.
    :param variable_name: Variable name.
    :param new_value: New variable value.
    :param call_frame_id: Id of callframe that holds variable.
    '''
    params: T_JSON_DICT = dict()
    params['scopeNumber'] = scope_number
    params['variableName'] = variable_name
    params['newValue'] = new_value.to_json()
    params['callFrameId'] = call_frame_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.setVariableValue',
        'params': params,
    }
    json = yield cmd_dict


def step_into(
        break_on_async_call: typing.Optional[bool] = None,
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps into the function call.

    :param break_on_async_call: **(EXPERIMENTAL)** *(Optional)* Debugger will pause on the execution of the first async task which was scheduled before next pause.
    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step into.
    '''
    params: T_JSON_DICT = dict()
    if break_on_async_call is not None:
        params['breakOnAsyncCall'] = break_on_async_call
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepInto',
        'params': params,
    }
    json = yield cmd_dict


def step_out() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps out of the function call.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOut',
    }
    json = yield cmd_dict


def step_over(
        skip_list: typing.Optional[typing.List[LocationRange]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Steps over the statement.

    :param skip_list: **(EXPERIMENTAL)** *(Optional)* The skipList specifies location ranges that should be skipped on step over.
    '''
    params: T_JSON_DICT = dict()
    if skip_list is not None:
        params['skipList'] = [i.to_json() for i in skip_list]
    cmd_dict: T_JSON_DICT = {
        'method': 'Debugger.stepOver',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Debugger.breakpointResolved')
@dataclass
class BreakpointResolved:
    '''
    Fired when breakpoint is resolved to an actual script and location.
    Deprecated in favor of ``resolvedBreakpoints`` in the ``scriptParsed`` event.
    '''
    #: Breakpoint unique identifier.
    breakpoint_id: BreakpointId
    #: Actual breakpoint location.
    location: Location

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> BreakpointResolved:
        return cls(
            breakpoint_id=BreakpointId.from_json(json['breakpointId']),
            location=Location.from_json(json['location'])
        )


@event_class('Debugger.paused')
@dataclass
class Paused:
    '''
    Fired when the virtual machine stopped on breakpoint or exception or any other stop criteria.
    '''
    #: Call stack the virtual machine stopped on.
    call_frames: typing.List[CallFrame]
    #: Pause reason.
    reason: str
    #: Object containing break-specific auxiliary properties.
    data: typing.Optional[dict]
    #: Hit breakpoints IDs
    hit_breakpoints: typing.Optional[typing.List[str]]
    #: Async stack trace, if any.
    async_stack_trace: typing.Optional[runtime.StackTrace]
    #: Async stack trace, if any.
    async_stack_trace_id: typing.Optional[runtime.StackTraceId]
    #: Never present, will be removed.
    async_call_stack_trace_id: typing.Optional[runtime.StackTraceId]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Paused:
        return cls(
            call_frames=[CallFrame.from_json(i) for i in json['callFrames']],
            reason=str(json['reason']),
            data=dict(json['data']) if 'data' in json else None,
            hit_breakpoints=[str(i) for i in json['hitBreakpoints']] if 'hitBreakpoints' in json else None,
            async_stack_trace=runtime.StackTrace.from_json(json['asyncStackTrace']) if 'asyncStackTrace' in json else None,
            async_stack_trace_id=runtime.StackTraceId.from_json(json['asyncStackTraceId']) if 'asyncStackTraceId' in json else None,
            async_call_stack_trace_id=runtime.StackTraceId.from_json(json['asyncCallStackTraceId']) if 'asyncCallStackTraceId' in json else None
        )


@event_class('Debugger.resumed')
@dataclass
class Resumed:
    '''
    Fired when the virtual machine resumed execution.
    '''


    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> Resumed:
        return cls(

        )


@event_class('Debugger.scriptFailedToParse')
@dataclass
class ScriptFailedToParse:
    '''
    Fired when virtual machine fails to parse the script.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section. For JavaScript the ``debugId`` magic comment.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptFailedToParse:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None
        )


@event_class('Debugger.scriptParsed')
@dataclass
class ScriptParsed:
    '''
    Fired when virtual machine parses script. This event is also fired for all known and uncollected
    scripts upon enabling debugger.
    '''
    #: Identifier of the script parsed.
    script_id: runtime.ScriptId
    #: URL or name of the script parsed (if any).
    url: str
    #: Line offset of the script within the resource with given URL (for script tags).
    start_line: int
    #: Column offset of the script within the resource with given URL.
    start_column: int
    #: Last line of the script.
    end_line: int
    #: Length of the last line of the script.
    end_column: int
    #: Specifies script creation context.
    execution_context_id: runtime.ExecutionContextId
    #: Content hash of the script, SHA-256.
    hash_: str
    #: For Wasm modules, the content of the ``build_id`` custom section. For JavaScript the ``debugId`` magic comment.
    build_id: str
    #: Embedder-specific auxiliary data likely matching {isDefault: boolean, type: 'default'``'isolated'``'worker', frameId: string}
    execution_context_aux_data: typing.Optional[dict]
    #: True, if this script is generated as a result of the live edit operation.
    is_live_edit: typing.Optional[bool]
    #: URL of source map associated with script (if any).
    source_map_url: typing.Optional[str]
    #: True, if this script has sourceURL.
    has_source_url: typing.Optional[bool]
    #: True, if this script is ES6 module.
    is_module: typing.Optional[bool]
    #: This script length.
    length: typing.Optional[int]
    #: JavaScript top stack frame of where the script parsed event was triggered if available.
    stack_trace: typing.Optional[runtime.StackTrace]
    #: If the scriptLanguage is WebAssembly, the code section offset in the module.
    code_offset: typing.Optional[int]
    #: The language of the script.
    script_language: typing.Optional[debugger.ScriptLanguage]
    #: If the scriptLanguage is WebAssembly, the source of debug symbols for the module.
    debug_symbols: typing.Optional[typing.List[debugger.DebugSymbols]]
    #: The name the embedder supplied for this script.
    embedder_name: typing.Optional[str]
    #: The list of set breakpoints in this script if calls to ``setBreakpointByUrl``
    #: matches this script's URL or hash. Clients that use this list can ignore the
    #: ``breakpointResolved`` event. They are equivalent.
    resolved_breakpoints: typing.Optional[typing.List[ResolvedBreakpoint]]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ScriptParsed:
        return cls(
            script_id=runtime.ScriptId.from_json(json['scriptId']),
            url=str(json['url']),
            start_line=int(json['startLine']),
            start_column=int(json['startColumn']),
            end_line=int(json['endLine']),
            end_column=int(json['endColumn']),
            execution_context_id=runtime.ExecutionContextId.from_json(json['executionContextId']),
            hash_=str(json['hash']),
            build_id=str(json['buildId']),
            execution_context_aux_data=dict(json['executionContextAuxData']) if 'executionContextAuxData' in json else None,
            is_live_edit=bool(json['isLiveEdit']) if 'isLiveEdit' in json else None,
            source_map_url=str(json['sourceMapURL']) if 'sourceMapURL' in json else None,
            has_source_url=bool(json['hasSourceURL']) if 'hasSourceURL' in json else None,
            is_module=bool(json['isModule']) if 'isModule' in json else None,
            length=int(json['length']) if 'length' in json else None,
            stack_trace=runtime.StackTrace.from_json(json['stackTrace']) if 'stackTrace' in json else None,
            code_offset=int(json['codeOffset']) if 'codeOffset' in json else None,
            script_language=debugger.ScriptLanguage.from_json(json['scriptLanguage']) if 'scriptLanguage' in json else None,
            debug_symbols=[debugger.DebugSymbols.from_json(i) for i in json['debugSymbols']] if 'debugSymbols' in json else None,
            embedder_name=str(json['embedderName']) if 'embedderName' in json else None,
            resolved_breakpoints=[ResolvedBreakpoint.from_json(i) for i in json['resolvedBreakpoints']] if 'resolvedBreakpoints' in json else None
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\compilers\C\base.py ===
"""distutils.ccompiler

Contains Compiler, an abstract base class that defines the interface
for the Distutils compiler abstraction model."""

from __future__ import annotations

import os
import pathlib
import re
import sys
import warnings
from collections.abc import Callable, Iterable, MutableSequence, Sequence
from typing import (
    TYPE_CHECKING,
    ClassVar,
    Literal,
    TypeVar,
    Union,
    overload,
)

from more_itertools import always_iterable

from ..._log import log
from ..._modified import newer_group
from ...dir_util import mkpath
from ...errors import (
    DistutilsModuleError,
    DistutilsPlatformError,
)
from ...file_util import move_file
from ...spawn import spawn
from ...util import execute, is_mingw, split_quoted
from .errors import (
    CompileError,
    LinkError,
    UnknownFileType,
)

if TYPE_CHECKING:
    from typing_extensions import TypeAlias, TypeVarTuple, Unpack

    _Ts = TypeVarTuple("_Ts")

_Macro: TypeAlias = Union[tuple[str], tuple[str, Union[str, None]]]
_StrPathT = TypeVar("_StrPathT", bound="str | os.PathLike[str]")
_BytesPathT = TypeVar("_BytesPathT", bound="bytes | os.PathLike[bytes]")


class Compiler:
    """Abstract base class to define the interface that must be implemented
    by real compiler classes.  Also has some utility methods used by
    several compiler classes.

    The basic idea behind a compiler abstraction class is that each
    instance can be used for all the compile/link steps in building a
    single project.  Thus, attributes common to all of those compile and
    link steps -- include directories, macros to define, libraries to link
    against, etc. -- are attributes of the compiler instance.  To allow for
    variability in how individual files are treated, most of those
    attributes may be varied on a per-compilation or per-link basis.
    """

    # 'compiler_type' is a class attribute that identifies this class.  It
    # keeps code that wants to know what kind of compiler it's dealing with
    # from having to import all possible compiler classes just to do an
    # 'isinstance'.  In concrete CCompiler subclasses, 'compiler_type'
    # should really, really be one of the keys of the 'compiler_class'
    # dictionary (see below -- used by the 'new_compiler()' factory
    # function) -- authors of new compiler interface classes are
    # responsible for updating 'compiler_class'!
    compiler_type: ClassVar[str] = None  # type: ignore[assignment]

    # XXX things not handled by this compiler abstraction model:
    #   * client can't provide additional options for a compiler,
    #     e.g. warning, optimization, debugging flags.  Perhaps this
    #     should be the domain of concrete compiler abstraction classes
    #     (UnixCCompiler, MSVCCompiler, etc.) -- or perhaps the base
    #     class should have methods for the common ones.
    #   * can't completely override the include or library searchg
    #     path, ie. no "cc -I -Idir1 -Idir2" or "cc -L -Ldir1 -Ldir2".
    #     I'm not sure how widely supported this is even by Unix
    #     compilers, much less on other platforms.  And I'm even less
    #     sure how useful it is; maybe for cross-compiling, but
    #     support for that is a ways off.  (And anyways, cross
    #     compilers probably have a dedicated binary with the
    #     right paths compiled in.  I hope.)
    #   * can't do really freaky things with the library list/library
    #     dirs, e.g. "-Ldir1 -lfoo -Ldir2 -lfoo" to link against
    #     different versions of libfoo.a in different locations.  I
    #     think this is useless without the ability to null out the
    #     library search path anyways.

    executables: ClassVar[dict]

    # Subclasses that rely on the standard filename generation methods
    # implemented below should override these; see the comment near
    # those methods ('object_filenames()' et. al.) for details:
    src_extensions: ClassVar[list[str] | None] = None
    obj_extension: ClassVar[str | None] = None
    static_lib_extension: ClassVar[str | None] = None
    shared_lib_extension: ClassVar[str | None] = None
    static_lib_format: ClassVar[str | None] = None  # format string
    shared_lib_format: ClassVar[str | None] = None  # prob. same as static_lib_format
    exe_extension: ClassVar[str | None] = None

    # Default language settings. language_map is used to detect a source
    # file or Extension target language, checking source filenames.
    # language_order is used to detect the language precedence, when deciding
    # what language to use when mixing source types. For example, if some
    # extension has two files with ".c" extension, and one with ".cpp", it
    # is still linked as c++.
    language_map: ClassVar[dict[str, str]] = {
        ".c": "c",
        ".cc": "c++",
        ".cpp": "c++",
        ".cxx": "c++",
        ".m": "objc",
    }
    language_order: ClassVar[list[str]] = ["c++", "objc", "c"]

    include_dirs: list[str] = []
    """
    include dirs specific to this compiler class
    """

    library_dirs: list[str] = []
    """
    library dirs specific to this compiler class
    """

    def __init__(
        self, verbose: bool = False, dry_run: bool = False, force: bool = False
    ) -> None:
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose

        # 'output_dir': a common output directory for object, library,
        # shared object, and shared library files
        self.output_dir: str | None = None

        # 'macros': a list of macro definitions (or undefinitions).  A
        # macro definition is a 2-tuple (name, value), where the value is
        # either a string or None (no explicit value).  A macro
        # undefinition is a 1-tuple (name,).
        self.macros: list[_Macro] = []

        # 'include_dirs': a list of directories to search for include files
        self.include_dirs = []

        # 'libraries': a list of libraries to include in any link
        # (library names, not filenames: eg. "foo" not "libfoo.a")
        self.libraries: list[str] = []

        # 'library_dirs': a list of directories to search for libraries
        self.library_dirs = []

        # 'runtime_library_dirs': a list of directories to search for
        # shared libraries/objects at runtime
        self.runtime_library_dirs: list[str] = []

        # 'objects': a list of object files (or similar, such as explicitly
        # named library files) to include on any link
        self.objects: list[str] = []

        for key in self.executables.keys():
            self.set_executable(key, self.executables[key])

    def set_executables(self, **kwargs: str) -> None:
        """Define the executables (and options for them) that will be run
        to perform the various stages of compilation.  The exact set of
        executables that may be specified here depends on the compiler
        class (via the 'executables' class attribute), but most will have:
          compiler      the C/C++ compiler
          linker_so     linker used to create shared objects and libraries
          linker_exe    linker used to create binary executables
          archiver      static library creator

        On platforms with a command-line (Unix, DOS/Windows), each of these
        is a string that will be split into executable name and (optional)
        list of arguments.  (Splitting the string is done similarly to how
        Unix shells operate: words are delimited by spaces, but quotes and
        backslashes can override this.  See
        'distutils.util.split_quoted()'.)
        """

        # Note that some CCompiler implementation classes will define class
        # attributes 'cpp', 'cc', etc. with hard-coded executable names;
        # this is appropriate when a compiler class is for exactly one
        # compiler/OS combination (eg. MSVCCompiler).  Other compiler
        # classes (UnixCCompiler, in particular) are driven by information
        # discovered at run-time, since there are many different ways to do
        # basically the same things with Unix C compilers.

        for key in kwargs:
            if key not in self.executables:
                raise ValueError(
                    f"unknown executable '{key}' for class {self.__class__.__name__}"
                )
            self.set_executable(key, kwargs[key])

    def set_executable(self, key, value):
        if isinstance(value, str):
            setattr(self, key, split_quoted(value))
        else:
            setattr(self, key, value)

    def _find_macro(self, name):
        i = 0
        for defn in self.macros:
            if defn[0] == name:
                return i
            i += 1
        return None

    def _check_macro_definitions(self, definitions):
        """Ensure that every element of 'definitions' is valid."""
        for defn in definitions:
            self._check_macro_definition(*defn)

    def _check_macro_definition(self, defn):
        """
        Raise a TypeError if defn is not valid.

        A valid definition is either a (name, value) 2-tuple or a (name,) tuple.
        """
        if not isinstance(defn, tuple) or not self._is_valid_macro(*defn):
            raise TypeError(
                f"invalid macro definition '{defn}': "
                "must be tuple (string,), (string, string), or (string, None)"
            )

    @staticmethod
    def _is_valid_macro(name, value=None):
        """
        A valid macro is a ``name : str`` and a ``value : str | None``.

        >>> Compiler._is_valid_macro('foo', None)
        True
        """
        return isinstance(name, str) and isinstance(value, (str, type(None)))

    # -- Bookkeeping methods -------------------------------------------

    def define_macro(self, name: str, value: str | None = None) -> None:
        """Define a preprocessor macro for all compilations driven by this
        compiler object.  The optional parameter 'value' should be a
        string; if it is not supplied, then the macro will be defined
        without an explicit value and the exact outcome depends on the
        compiler used (XXX true? does ANSI say anything about this?)
        """
        # Delete from the list of macro definitions/undefinitions if
        # already there (so that this one will take precedence).
        i = self._find_macro(name)
        if i is not None:
            del self.macros[i]

        self.macros.append((name, value))

    def undefine_macro(self, name: str) -> None:
        """Undefine a preprocessor macro for all compilations driven by
        this compiler object.  If the same macro is defined by
        'define_macro()' and undefined by 'undefine_macro()' the last call
        takes precedence (including multiple redefinitions or
        undefinitions).  If the macro is redefined/undefined on a
        per-compilation basis (ie. in the call to 'compile()'), then that
        takes precedence.
        """
        # Delete from the list of macro definitions/undefinitions if
        # already there (so that this one will take precedence).
        i = self._find_macro(name)
        if i is not None:
            del self.macros[i]

        undefn = (name,)
        self.macros.append(undefn)

    def add_include_dir(self, dir: str) -> None:
        """Add 'dir' to the list of directories that will be searched for
        header files.  The compiler is instructed to search directories in
        the order in which they are supplied by successive calls to
        'add_include_dir()'.
        """
        self.include_dirs.append(dir)

    def set_include_dirs(self, dirs: list[str]) -> None:
        """Set the list of directories that will be searched to 'dirs' (a
        list of strings).  Overrides any preceding calls to
        'add_include_dir()'; subsequence calls to 'add_include_dir()' add
        to the list passed to 'set_include_dirs()'.  This does not affect
        any list of standard include directories that the compiler may
        search by default.
        """
        self.include_dirs = dirs[:]

    def add_library(self, libname: str) -> None:
        """Add 'libname' to the list of libraries that will be included in
        all links driven by this compiler object.  Note that 'libname'
        should *not* be the name of a file containing a library, but the
        name of the library itself: the actual filename will be inferred by
        the linker, the compiler, or the compiler class (depending on the
        platform).

        The linker will be instructed to link against libraries in the
        order they were supplied to 'add_library()' and/or
        'set_libraries()'.  It is perfectly valid to duplicate library
        names; the linker will be instructed to link against libraries as
        many times as they are mentioned.
        """
        self.libraries.append(libname)

    def set_libraries(self, libnames: list[str]) -> None:
        """Set the list of libraries to be included in all links driven by
        this compiler object to 'libnames' (a list of strings).  This does
        not affect any standard system libraries that the linker may
        include by default.
        """
        self.libraries = libnames[:]

    def add_library_dir(self, dir: str) -> None:
        """Add 'dir' to the list of directories that will be searched for
        libraries specified to 'add_library()' and 'set_libraries()'.  The
        linker will be instructed to search for libraries in the order they
        are supplied to 'add_library_dir()' and/or 'set_library_dirs()'.
        """
        self.library_dirs.append(dir)

    def set_library_dirs(self, dirs: list[str]) -> None:
        """Set the list of library search directories to 'dirs' (a list of
        strings).  This does not affect any standard library search path
        that the linker may search by default.
        """
        self.library_dirs = dirs[:]

    def add_runtime_library_dir(self, dir: str) -> None:
        """Add 'dir' to the list of directories that will be searched for
        shared libraries at runtime.
        """
        self.runtime_library_dirs.append(dir)

    def set_runtime_library_dirs(self, dirs: list[str]) -> None:
        """Set the list of directories to search for shared libraries at
        runtime to 'dirs' (a list of strings).  This does not affect any
        standard search path that the runtime linker may search by
        default.
        """
        self.runtime_library_dirs = dirs[:]

    def add_link_object(self, object: str) -> None:
        """Add 'object' to the list of object files (or analogues, such as
        explicitly named library files or the output of "resource
        compilers") to be included in every link driven by this compiler
        object.
        """
        self.objects.append(object)

    def set_link_objects(self, objects: list[str]) -> None:
        """Set the list of object files (or analogues) to be included in
        every link to 'objects'.  This does not affect any standard object
        files that the linker may include by default (such as system
        libraries).
        """
        self.objects = objects[:]

    # -- Private utility methods --------------------------------------
    # (here for the convenience of subclasses)

    # Helper method to prep compiler in subclass compile() methods

    def _setup_compile(
        self,
        outdir: str | None,
        macros: list[_Macro] | None,
        incdirs: list[str] | tuple[str, ...] | None,
        sources,
        depends,
        extra,
    ):
        """Process arguments and decide which source files to compile."""
        outdir, macros, incdirs = self._fix_compile_args(outdir, macros, incdirs)

        if extra is None:
            extra = []

        # Get the list of expected output (object) files
        objects = self.object_filenames(sources, strip_dir=False, output_dir=outdir)
        assert len(objects) == len(sources)

        pp_opts = gen_preprocess_options(macros, incdirs)

        build = {}
        for i in range(len(sources)):
            src = sources[i]
            obj = objects[i]
            ext = os.path.splitext(src)[1]
            self.mkpath(os.path.dirname(obj))
            build[obj] = (src, ext)

        return macros, objects, extra, pp_opts, build

    def _get_cc_args(self, pp_opts, debug, before):
        # works for unixccompiler, cygwinccompiler
        cc_args = pp_opts + ['-c']
        if debug:
            cc_args[:0] = ['-g']
        if before:
            cc_args[:0] = before
        return cc_args

    def _fix_compile_args(
        self,
        output_dir: str | None,
        macros: list[_Macro] | None,
        include_dirs: list[str] | tuple[str, ...] | None,
    ) -> tuple[str, list[_Macro], list[str]]:
        """Typecheck and fix-up some of the arguments to the 'compile()'
        method, and return fixed-up values.  Specifically: if 'output_dir'
        is None, replaces it with 'self.output_dir'; ensures that 'macros'
        is a list, and augments it with 'self.macros'; ensures that
        'include_dirs' is a list, and augments it with 'self.include_dirs'.
        Guarantees that the returned values are of the correct type,
        i.e. for 'output_dir' either string or None, and for 'macros' and
        'include_dirs' either list or None.
        """
        if output_dir is None:
            output_dir = self.output_dir
        elif not isinstance(output_dir, str):
            raise TypeError("'output_dir' must be a string or None")

        if macros is None:
            macros = list(self.macros)
        elif isinstance(macros, list):
            macros = macros + (self.macros or [])
        else:
            raise TypeError("'macros' (if supplied) must be a list of tuples")

        if include_dirs is None:
            include_dirs = list(self.include_dirs)
        elif isinstance(include_dirs, (list, tuple)):
            include_dirs = list(include_dirs) + (self.include_dirs or [])
        else:
            raise TypeError("'include_dirs' (if supplied) must be a list of strings")

        # add include dirs for class
        include_dirs += self.__class__.include_dirs

        return output_dir, macros, include_dirs

    def _prep_compile(self, sources, output_dir, depends=None):
        """Decide which source files must be recompiled.

        Determine the list of object files corresponding to 'sources',
        and figure out which ones really need to be recompiled.
        Return a list of all object files and a dictionary telling
        which source files can be skipped.
        """
        # Get the list of expected output (object) files
        objects = self.object_filenames(sources, output_dir=output_dir)
        assert len(objects) == len(sources)

        # Return an empty dict for the "which source files can be skipped"
        # return value to preserve API compatibility.
        return objects, {}

    def _fix_object_args(
        self, objects: list[str] | tuple[str, ...], output_dir: str | None
    ) -> tuple[list[str], str]:
        """Typecheck and fix up some arguments supplied to various methods.
        Specifically: ensure that 'objects' is a list; if output_dir is
        None, replace with self.output_dir.  Return fixed versions of
        'objects' and 'output_dir'.
        """
        if not isinstance(objects, (list, tuple)):
            raise TypeError("'objects' must be a list or tuple of strings")
        objects = list(objects)

        if output_dir is None:
            output_dir = self.output_dir
        elif not isinstance(output_dir, str):
            raise TypeError("'output_dir' must be a string or None")

        return (objects, output_dir)

    def _fix_lib_args(
        self,
        libraries: list[str] | tuple[str, ...] | None,
        library_dirs: list[str] | tuple[str, ...] | None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None,
    ) -> tuple[list[str], list[str], list[str]]:
        """Typecheck and fix up some of the arguments supplied to the
        'link_*' methods.  Specifically: ensure that all arguments are
        lists, and augment them with their permanent versions
        (eg. 'self.libraries' augments 'libraries').  Return a tuple with
        fixed versions of all arguments.
        """
        if libraries is None:
            libraries = list(self.libraries)
        elif isinstance(libraries, (list, tuple)):
            libraries = list(libraries) + (self.libraries or [])
        else:
            raise TypeError("'libraries' (if supplied) must be a list of strings")

        if library_dirs is None:
            library_dirs = list(self.library_dirs)
        elif isinstance(library_dirs, (list, tuple)):
            library_dirs = list(library_dirs) + (self.library_dirs or [])
        else:
            raise TypeError("'library_dirs' (if supplied) must be a list of strings")

        # add library dirs for class
        library_dirs += self.__class__.library_dirs

        if runtime_library_dirs is None:
            runtime_library_dirs = list(self.runtime_library_dirs)
        elif isinstance(runtime_library_dirs, (list, tuple)):
            runtime_library_dirs = list(runtime_library_dirs) + (
                self.runtime_library_dirs or []
            )
        else:
            raise TypeError(
                "'runtime_library_dirs' (if supplied) must be a list of strings"
            )

        return (libraries, library_dirs, runtime_library_dirs)

    def _need_link(self, objects, output_file):
        """Return true if we need to relink the files listed in 'objects'
        to recreate 'output_file'.
        """
        if self.force:
            return True
        else:
            if self.dry_run:
                newer = newer_group(objects, output_file, missing='newer')
            else:
                newer = newer_group(objects, output_file)
            return newer

    def detect_language(self, sources: str | list[str]) -> str | None:
        """Detect the language of a given file, or list of files. Uses
        language_map, and language_order to do the job.
        """
        if not isinstance(sources, list):
            sources = [sources]
        lang = None
        index = len(self.language_order)
        for source in sources:
            base, ext = os.path.splitext(source)
            extlang = self.language_map.get(ext)
            try:
                extindex = self.language_order.index(extlang)
                if extindex < index:
                    lang = extlang
                    index = extindex
            except ValueError:
                pass
        return lang

    # -- Worker methods ------------------------------------------------
    # (must be implemented by subclasses)

    def preprocess(
        self,
        source: str | os.PathLike[str],
        output_file: str | os.PathLike[str] | None = None,
        macros: list[_Macro] | None = None,
        include_dirs: list[str] | tuple[str, ...] | None = None,
        extra_preargs: list[str] | None = None,
        extra_postargs: Iterable[str] | None = None,
    ):
        """Preprocess a single C/C++ source file, named in 'source'.
        Output will be written to file named 'output_file', or stdout if
        'output_file' not supplied.  'macros' is a list of macro
        definitions as for 'compile()', which will augment the macros set
        with 'define_macro()' and 'undefine_macro()'.  'include_dirs' is a
        list of directory names that will be added to the default list.

        Raises PreprocessError on failure.
        """
        pass

    def compile(
        self,
        sources: Sequence[str | os.PathLike[str]],
        output_dir: str | None = None,
        macros: list[_Macro] | None = None,
        include_dirs: list[str] | tuple[str, ...] | None = None,
        debug: bool = False,
        extra_preargs: list[str] | None = None,
        extra_postargs: list[str] | None = None,
        depends: list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        """Compile one or more source files.

        'sources' must be a list of filenames, most likely C/C++
        files, but in reality anything that can be handled by a
        particular compiler and compiler class (eg. MSVCCompiler can
        handle resource files in 'sources').  Return a list of object
        filenames, one per source filename in 'sources'.  Depending on
        the implementation, not all source files will necessarily be
        compiled, but all corresponding object filenames will be
        returned.

        If 'output_dir' is given, object files will be put under it, while
        retaining their original path component.  That is, "foo/bar.c"
        normally compiles to "foo/bar.o" (for a Unix implementation); if
        'output_dir' is "build", then it would compile to
        "build/foo/bar.o".

        'macros', if given, must be a list of macro definitions.  A macro
        definition is either a (name, value) 2-tuple or a (name,) 1-tuple.
        The former defines a macro; if the value is None, the macro is
        defined without an explicit value.  The 1-tuple case undefines a
        macro.  Later definitions/redefinitions/ undefinitions take
        precedence.

        'include_dirs', if given, must be a list of strings, the
        directories to add to the default include file search path for this
        compilation only.

        'debug' is a boolean; if true, the compiler will be instructed to
        output debug symbols in (or alongside) the object file(s).

        'extra_preargs' and 'extra_postargs' are implementation- dependent.
        On platforms that have the notion of a command-line (e.g. Unix,
        DOS/Windows), they are most likely lists of strings: extra
        command-line arguments to prepend/append to the compiler command
        line.  On other platforms, consult the implementation class
        documentation.  In any event, they are intended as an escape hatch
        for those occasions when the abstract compiler framework doesn't
        cut the mustard.

        'depends', if given, is a list of filenames that all targets
        depend on.  If a source file is older than any file in
        depends, then the source file will be recompiled.  This
        supports dependency tracking, but only at a coarse
        granularity.

        Raises CompileError on failure.
        """
        # A concrete compiler class can either override this method
        # entirely or implement _compile().
        macros, objects, extra_postargs, pp_opts, build = self._setup_compile(
            output_dir, macros, include_dirs, sources, depends, extra_postargs
        )
        cc_args = self._get_cc_args(pp_opts, debug, extra_preargs)

        for obj in objects:
            try:
                src, ext = build[obj]
            except KeyError:
                continue
            self._compile(obj, src, ext, cc_args, extra_postargs, pp_opts)

        # Return *all* object filenames, not just the ones we just built.
        return objects

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        """Compile 'src' to product 'obj'."""
        # A concrete compiler class that does not override compile()
        # should implement _compile().
        pass

    def create_static_lib(
        self,
        objects: list[str] | tuple[str, ...],
        output_libname: str,
        output_dir: str | None = None,
        debug: bool = False,
        target_lang: str | None = None,
    ) -> None:
        """Link a bunch of stuff together to create a static library file.
        The "bunch of stuff" consists of the list of object files supplied
        as 'objects', the extra object files supplied to
        'add_link_object()' and/or 'set_link_objects()', the libraries
        supplied to 'add_library()' and/or 'set_libraries()', and the
        libraries supplied as 'libraries' (if any).

        'output_libname' should be a library name, not a filename; the
        filename will be inferred from the library name.  'output_dir' is
        the directory where the library file will be put.

        'debug' is a boolean; if true, debugging information will be
        included in the library (note that on most platforms, it is the
        compile step where this matters: the 'debug' flag is included here
        just for consistency).

        'target_lang' is the target language for which the given objects
        are being compiled. This allows specific linkage time treatment of
        certain languages.

        Raises LibError on failure.
        """
        pass

    # values for target_desc parameter in link()
    SHARED_OBJECT = "shared_object"
    SHARED_LIBRARY = "shared_library"
    EXECUTABLE = "executable"

    def link(
        self,
        target_desc: str,
        objects: list[str] | tuple[str, ...],
        output_filename: str,
        output_dir: str | None = None,
        libraries: list[str] | tuple[str, ...] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None = None,
        export_symbols: Iterable[str] | None = None,
        debug: bool = False,
        extra_preargs: list[str] | None = None,
        extra_postargs: list[str] | None = None,
        build_temp: str | os.PathLike[str] | None = None,
        target_lang: str | None = None,
    ):
        """Link a bunch of stuff together to create an executable or
        shared library file.

        The "bunch of stuff" consists of the list of object files supplied
        as 'objects'.  'output_filename' should be a filename.  If
        'output_dir' is supplied, 'output_filename' is relative to it
        (i.e. 'output_filename' can provide directory components if
        needed).

        'libraries' is a list of libraries to link against.  These are
        library names, not filenames, since they're translated into
        filenames in a platform-specific way (eg. "foo" becomes "libfoo.a"
        on Unix and "foo.lib" on DOS/Windows).  However, they can include a
        directory component, which means the linker will look in that
        specific directory rather than searching all the normal locations.

        'library_dirs', if supplied, should be a list of directories to
        search for libraries that were specified as bare library names
        (ie. no directory component).  These are on top of the system
        default and those supplied to 'add_library_dir()' and/or
        'set_library_dirs()'.  'runtime_library_dirs' is a list of
        directories that will be embedded into the shared library and used
        to search for other shared libraries that *it* depends on at
        run-time.  (This may only be relevant on Unix.)

        'export_symbols' is a list of symbols that the shared library will
        export.  (This appears to be relevant only on Windows.)

        'debug' is as for 'compile()' and 'create_static_lib()', with the
        slight distinction that it actually matters on most platforms (as
        opposed to 'create_static_lib()', which includes a 'debug' flag
        mostly for form's sake).

        'extra_preargs' and 'extra_postargs' are as for 'compile()' (except
        of course that they supply command-line arguments for the
        particular linker being used).

        'target_lang' is the target language for which the given objects
        are being compiled. This allows specific linkage time treatment of
        certain languages.

        Raises LinkError on failure.
        """
        raise NotImplementedError

    # Old 'link_*()' methods, rewritten to use the new 'link()' method.

    def link_shared_lib(
        self,
        objects: list[str] | tuple[str, ...],
        output_libname: str,
        output_dir: str | None = None,
        libraries: list[str] | tuple[str, ...] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None = None,
        export_symbols: Iterable[str] | None = None,
        debug: bool = False,
        extra_preargs: list[str] | None = None,
        extra_postargs: list[str] | None = None,
        build_temp: str | os.PathLike[str] | None = None,
        target_lang: str | None = None,
    ):
        self.link(
            Compiler.SHARED_LIBRARY,
            objects,
            self.library_filename(output_libname, lib_type='shared'),
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

    def link_shared_object(
        self,
        objects: list[str] | tuple[str, ...],
        output_filename: str,
        output_dir: str | None = None,
        libraries: list[str] | tuple[str, ...] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None = None,
        export_symbols: Iterable[str] | None = None,
        debug: bool = False,
        extra_preargs: list[str] | None = None,
        extra_postargs: list[str] | None = None,
        build_temp: str | os.PathLike[str] | None = None,
        target_lang: str | None = None,
    ):
        self.link(
            Compiler.SHARED_OBJECT,
            objects,
            output_filename,
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

    def link_executable(
        self,
        objects: list[str] | tuple[str, ...],
        output_progname: str,
        output_dir: str | None = None,
        libraries: list[str] | tuple[str, ...] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None = None,
        debug: bool = False,
        extra_preargs: list[str] | None = None,
        extra_postargs: list[str] | None = None,
        target_lang: str | None = None,
    ):
        self.link(
            Compiler.EXECUTABLE,
            objects,
            self.executable_filename(output_progname),
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            None,
            debug,
            extra_preargs,
            extra_postargs,
            None,
            target_lang,
        )

    # -- Miscellaneous methods -----------------------------------------
    # These are all used by the 'gen_lib_options() function; there is
    # no appropriate default implementation so subclasses should
    # implement all of these.

    def library_dir_option(self, dir: str) -> str:
        """Return the compiler option to add 'dir' to the list of
        directories searched for libraries.
        """
        raise NotImplementedError

    def runtime_library_dir_option(self, dir: str) -> str:
        """Return the compiler option to add 'dir' to the list of
        directories searched for runtime libraries.
        """
        raise NotImplementedError

    def library_option(self, lib: str) -> str:
        """Return the compiler option to add 'lib' to the list of libraries
        linked into the shared library or executable.
        """
        raise NotImplementedError

    def has_function(  # noqa: C901
        self,
        funcname: str,
        includes: Iterable[str] | None = None,
        include_dirs: list[str] | tuple[str, ...] | None = None,
        libraries: list[str] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        """Return a boolean indicating whether funcname is provided as
        a symbol on the current platform.  The optional arguments can
        be used to augment the compilation environment.

        The libraries argument is a list of flags to be passed to the
        linker to make additional symbol definitions available for
        linking.

        The includes and include_dirs arguments are deprecated.
        Usually, supplying include files with function declarations
        will cause function detection to fail even in cases where the
        symbol is available for linking.

        """
        # this can't be included at module scope because it tries to
        # import math which might not be available at that point - maybe
        # the necessary logic should just be inlined?
        import tempfile

        if includes is None:
            includes = []
        else:
            warnings.warn("includes is deprecated", DeprecationWarning)
        if include_dirs is None:
            include_dirs = []
        else:
            warnings.warn("include_dirs is deprecated", DeprecationWarning)
        if libraries is None:
            libraries = []
        if library_dirs is None:
            library_dirs = []
        fd, fname = tempfile.mkstemp(".c", funcname, text=True)
        with os.fdopen(fd, "w", encoding='utf-8') as f:
            for incl in includes:
                f.write(f"""#include "{incl}"\n""")
            if not includes:
                # Use "char func(void);" as the prototype to follow
                # what autoconf does.  This prototype does not match
                # any well-known function the compiler might recognize
                # as a builtin, so this ends up as a true link test.
                # Without a fake prototype, the test would need to
                # know the exact argument types, and the has_function
                # interface does not provide that level of information.
                f.write(
                    f"""\
#ifdef __cplusplus
extern "C"
#endif
char {funcname}(void);
"""
                )
            f.write(
                f"""\
int main (int argc, char **argv) {{
    {funcname}();
    return 0;
}}
"""
            )

        try:
            objects = self.compile([fname], include_dirs=include_dirs)
        except CompileError:
            return False
        finally:
            os.remove(fname)

        try:
            self.link_executable(
                objects, "a.out", libraries=libraries, library_dirs=library_dirs
            )
        except (LinkError, TypeError):
            return False
        else:
            os.remove(
                self.executable_filename("a.out", output_dir=self.output_dir or '')
            )
        finally:
            for fn in objects:
                os.remove(fn)
        return True

    def find_library_file(
        self, dirs: Iterable[str], lib: str, debug: bool = False
    ) -> str | None:
        """Search the specified list of directories for a static or shared
        library file 'lib' and return the full path to that file.  If
        'debug' true, look for a debugging version (if that makes sense on
        the current platform).  Return None if 'lib' wasn't found in any of
        the specified directories.
        """
        raise NotImplementedError

    # -- Filename generation methods -----------------------------------

    # The default implementation of the filename generating methods are
    # prejudiced towards the Unix/DOS/Windows view of the world:
    #   * object files are named by replacing the source file extension
    #     (eg. .c/.cpp -> .o/.obj)
    #   * library files (shared or static) are named by plugging the
    #     library name and extension into a format string, eg.
    #     "lib%s.%s" % (lib_name, ".a") for Unix static libraries
    #   * executables are named by appending an extension (possibly
    #     empty) to the program name: eg. progname + ".exe" for
    #     Windows
    #
    # To reduce redundant code, these methods expect to find
    # several attributes in the current object (presumably defined
    # as class attributes):
    #   * src_extensions -
    #     list of C/C++ source file extensions, eg. ['.c', '.cpp']
    #   * obj_extension -
    #     object file extension, eg. '.o' or '.obj'
    #   * static_lib_extension -
    #     extension for static library files, eg. '.a' or '.lib'
    #   * shared_lib_extension -
    #     extension for shared library/object files, eg. '.so', '.dll'
    #   * static_lib_format -
    #     format string for generating static library filenames,
    #     eg. 'lib%s.%s' or '%s.%s'
    #   * shared_lib_format
    #     format string for generating shared library filenames
    #     (probably same as static_lib_format, since the extension
    #     is one of the intended parameters to the format string)
    #   * exe_extension -
    #     extension for executable files, eg. '' or '.exe'

    def object_filenames(
        self,
        source_filenames: Iterable[str | os.PathLike[str]],
        strip_dir: bool = False,
        output_dir: str | os.PathLike[str] | None = '',
    ) -> list[str]:
        if output_dir is None:
            output_dir = ''
        return list(
            self._make_out_path(output_dir, strip_dir, src_name)
            for src_name in source_filenames
        )

    @property
    def out_extensions(self):
        return dict.fromkeys(self.src_extensions, self.obj_extension)

    def _make_out_path(self, output_dir, strip_dir, src_name):
        return self._make_out_path_exts(
            output_dir, strip_dir, src_name, self.out_extensions
        )

    @classmethod
    def _make_out_path_exts(cls, output_dir, strip_dir, src_name, extensions):
        r"""
        >>> exts = {'.c': '.o'}
        >>> Compiler._make_out_path_exts('.', False, '/foo/bar.c', exts).replace('\\', '/')
        './foo/bar.o'
        >>> Compiler._make_out_path_exts('.', True, '/foo/bar.c', exts).replace('\\', '/')
        './bar.o'
        """
        src = pathlib.PurePath(src_name)
        # Ensure base is relative to honor output_dir (python/cpython#37775).
        base = cls._make_relative(src)
        try:
            new_ext = extensions[src.suffix]
        except LookupError:
            raise UnknownFileType(f"unknown file type '{src.suffix}' (from '{src}')")
        if strip_dir:
            base = pathlib.PurePath(base.name)
        return os.path.join(output_dir, base.with_suffix(new_ext))

    @staticmethod
    def _make_relative(base: pathlib.Path):
        return base.relative_to(base.anchor)

    @overload
    def shared_object_filename(
        self,
        basename: str,
        strip_dir: Literal[False] = False,
        output_dir: str | os.PathLike[str] = "",
    ) -> str: ...
    @overload
    def shared_object_filename(
        self,
        basename: str | os.PathLike[str],
        strip_dir: Literal[True],
        output_dir: str | os.PathLike[str] = "",
    ) -> str: ...
    def shared_object_filename(
        self,
        basename: str | os.PathLike[str],
        strip_dir: bool = False,
        output_dir: str | os.PathLike[str] = '',
    ) -> str:
        assert output_dir is not None
        if strip_dir:
            basename = os.path.basename(basename)
        return os.path.join(output_dir, basename + self.shared_lib_extension)

    @overload
    def executable_filename(
        self,
        basename: str,
        strip_dir: Literal[False] = False,
        output_dir: str | os.PathLike[str] = "",
    ) -> str: ...
    @overload
    def executable_filename(
        self,
        basename: str | os.PathLike[str],
        strip_dir: Literal[True],
        output_dir: str | os.PathLike[str] = "",
    ) -> str: ...
    def executable_filename(
        self,
        basename: str | os.PathLike[str],
        strip_dir: bool = False,
        output_dir: str | os.PathLike[str] = '',
    ) -> str:
        assert output_dir is not None
        if strip_dir:
            basename = os.path.basename(basename)
        return os.path.join(output_dir, basename + (self.exe_extension or ''))

    def library_filename(
        self,
        libname: str,
        lib_type: str = "static",
        strip_dir: bool = False,
        output_dir: str | os.PathLike[str] = "",  # or 'shared'
    ):
        assert output_dir is not None
        expected = '"static", "shared", "dylib", "xcode_stub"'
        if lib_type not in eval(expected):
            raise ValueError(f"'lib_type' must be {expected}")
        fmt = getattr(self, lib_type + "_lib_format")
        ext = getattr(self, lib_type + "_lib_extension")

        dir, base = os.path.split(libname)
        filename = fmt % (base, ext)
        if strip_dir:
            dir = ''

        return os.path.join(output_dir, dir, filename)

    # -- Utility methods -----------------------------------------------

    def announce(self, msg: object, level: int = 1) -> None:
        log.debug(msg)

    def debug_print(self, msg: object) -> None:
        from distutils.debug import DEBUG

        if DEBUG:
            print(msg)

    def warn(self, msg: object) -> None:
        sys.stderr.write(f"warning: {msg}\n")

    def execute(
        self,
        func: Callable[[Unpack[_Ts]], object],
        args: tuple[Unpack[_Ts]],
        msg: object = None,
        level: int = 1,
    ) -> None:
        execute(func, args, msg, self.dry_run)

    def spawn(
        self, cmd: MutableSequence[bytes | str | os.PathLike[str]], **kwargs
    ) -> None:
        spawn(cmd, dry_run=self.dry_run, **kwargs)

    @overload
    def move_file(
        self, src: str | os.PathLike[str], dst: _StrPathT
    ) -> _StrPathT | str: ...
    @overload
    def move_file(
        self, src: bytes | os.PathLike[bytes], dst: _BytesPathT
    ) -> _BytesPathT | bytes: ...
    def move_file(
        self,
        src: str | os.PathLike[str] | bytes | os.PathLike[bytes],
        dst: str | os.PathLike[str] | bytes | os.PathLike[bytes],
    ) -> str | os.PathLike[str] | bytes | os.PathLike[bytes]:
        return move_file(src, dst, dry_run=self.dry_run)

    def mkpath(self, name, mode=0o777):
        mkpath(name, mode, dry_run=self.dry_run)


# Map a sys.platform/os.name ('posix', 'nt') to the default compiler
# type for that platform. Keys are interpreted as re match
# patterns. Order is important; platform mappings are preferred over
# OS names.
_default_compilers = (
    # Platform string mappings
    # on a cygwin built python we can use gcc like an ordinary UNIXish
    # compiler
    ('cygwin.*', 'unix'),
    ('zos', 'zos'),
    # OS name mappings
    ('posix', 'unix'),
    ('nt', 'msvc'),
)


def get_default_compiler(osname: str | None = None, platform: str | None = None) -> str:
    """Determine the default compiler to use for the given platform.

    osname should be one of the standard Python OS names (i.e. the
    ones returned by os.name) and platform the common value
    returned by sys.platform for the platform in question.

    The default values are os.name and sys.platform in case the
    parameters are not given.
    """
    if osname is None:
        osname = os.name
    if platform is None:
        platform = sys.platform
    # Mingw is a special case where sys.platform is 'win32' but we
    # want to use the 'mingw32' compiler, so check it first
    if is_mingw():
        return 'mingw32'
    for pattern, compiler in _default_compilers:
        if (
            re.match(pattern, platform) is not None
            or re.match(pattern, osname) is not None
        ):
            return compiler
    # Default to Unix compiler
    return 'unix'


# Map compiler types to (module_name, class_name) pairs -- ie. where to
# find the code that implements an interface to this compiler.  (The module
# is assumed to be in the 'distutils' package.)
compiler_class = {
    'unix': ('unixccompiler', 'UnixCCompiler', "standard UNIX-style compiler"),
    'msvc': ('_msvccompiler', 'MSVCCompiler', "Microsoft Visual C++"),
    'cygwin': (
        'cygwinccompiler',
        'CygwinCCompiler',
        "Cygwin port of GNU C Compiler for Win32",
    ),
    'mingw32': (
        'cygwinccompiler',
        'Mingw32CCompiler',
        "Mingw32 port of GNU C Compiler for Win32",
    ),
    'bcpp': ('bcppcompiler', 'BCPPCompiler', "Borland C++ Compiler"),
    'zos': ('zosccompiler', 'zOSCCompiler', 'IBM XL C/C++ Compilers'),
}


def show_compilers() -> None:
    """Print list of available compilers (used by the "--help-compiler"
    options to "build", "build_ext", "build_clib").
    """
    # XXX this "knows" that the compiler option it's describing is
    # "--compiler", which just happens to be the case for the three
    # commands that use it.
    from distutils.fancy_getopt import FancyGetopt

    compilers = sorted(
        ("compiler=" + compiler, None, compiler_class[compiler][2])
        for compiler in compiler_class.keys()
    )
    pretty_printer = FancyGetopt(compilers)
    pretty_printer.print_help("List of available compilers:")


def new_compiler(
    plat: str | None = None,
    compiler: str | None = None,
    verbose: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> Compiler:
    """Generate an instance of some CCompiler subclass for the supplied
    platform/compiler combination.  'plat' defaults to 'os.name'
    (eg. 'posix', 'nt'), and 'compiler' defaults to the default compiler
    for that platform.  Currently only 'posix' and 'nt' are supported, and
    the default compilers are "traditional Unix interface" (UnixCCompiler
    class) and Visual C++ (MSVCCompiler class).  Note that it's perfectly
    possible to ask for a Unix compiler object under Windows, and a
    Microsoft compiler object under Unix -- if you supply a value for
    'compiler', 'plat' is ignored.
    """
    if plat is None:
        plat = os.name

    try:
        if compiler is None:
            compiler = get_default_compiler(plat)

        (module_name, class_name, long_description) = compiler_class[compiler]
    except KeyError:
        msg = f"don't know how to compile C/C++ code on platform '{plat}'"
        if compiler is not None:
            msg = msg + f" with '{compiler}' compiler"
        raise DistutilsPlatformError(msg)

    try:
        module_name = "distutils." + module_name
        __import__(module_name)
        module = sys.modules[module_name]
        klass = vars(module)[class_name]
    except ImportError:
        raise DistutilsModuleError(
            f"can't compile C/C++ code: unable to load module '{module_name}'"
        )
    except KeyError:
        raise DistutilsModuleError(
            f"can't compile C/C++ code: unable to find class '{class_name}' "
            f"in module '{module_name}'"
        )

    # XXX The None is necessary to preserve backwards compatibility
    # with classes that expect verbose to be the first positional
    # argument.
    return klass(None, dry_run, force)


def gen_preprocess_options(
    macros: Iterable[_Macro], include_dirs: Iterable[str]
) -> list[str]:
    """Generate C pre-processor options (-D, -U, -I) as used by at least
    two types of compilers: the typical Unix compiler and Visual C++.
    'macros' is the usual thing, a list of 1- or 2-tuples, where (name,)
    means undefine (-U) macro 'name', and (name,value) means define (-D)
    macro 'name' to 'value'.  'include_dirs' is just a list of directory
    names to be added to the header file search path (-I).  Returns a list
    of command-line options suitable for either Unix compilers or Visual
    C++.
    """
    # XXX it would be nice (mainly aesthetic, and so we don't generate
    # stupid-looking command lines) to go over 'macros' and eliminate
    # redundant definitions/undefinitions (ie. ensure that only the
    # latest mention of a particular macro winds up on the command
    # line).  I don't think it's essential, though, since most (all?)
    # Unix C compilers only pay attention to the latest -D or -U
    # mention of a macro on their command line.  Similar situation for
    # 'include_dirs'.  I'm punting on both for now.  Anyways, weeding out
    # redundancies like this should probably be the province of
    # CCompiler, since the data structures used are inherited from it
    # and therefore common to all CCompiler classes.
    pp_opts = []
    for macro in macros:
        if not (isinstance(macro, tuple) and 1 <= len(macro) <= 2):
            raise TypeError(
                f"bad macro definition '{macro}': "
                "each element of 'macros' list must be a 1- or 2-tuple"
            )

        if len(macro) == 1:  # undefine this macro
            pp_opts.append(f"-U{macro[0]}")
        elif len(macro) == 2:
            if macro[1] is None:  # define with no explicit value
                pp_opts.append(f"-D{macro[0]}")
            else:
                # XXX *don't* need to be clever about quoting the
                # macro value here, because we're going to avoid the
                # shell at all costs when we spawn the command!
                pp_opts.append("-D{}={}".format(*macro))

    pp_opts.extend(f"-I{dir}" for dir in include_dirs)
    return pp_opts


def gen_lib_options(
    compiler: Compiler,
    library_dirs: Iterable[str],
    runtime_library_dirs: Iterable[str],
    libraries: Iterable[str],
) -> list[str]:
    """Generate linker options for searching library directories and
    linking with specific libraries.  'libraries' and 'library_dirs' are,
    respectively, lists of library names (not filenames!) and search
    directories.  Returns a list of command-line options suitable for use
    with some compiler (depending on the two format strings passed in).
    """
    lib_opts = [compiler.library_dir_option(dir) for dir in library_dirs]

    for dir in runtime_library_dirs:
        lib_opts.extend(always_iterable(compiler.runtime_library_dir_option(dir)))

    # XXX it's important that we *not* remove redundant library mentions!
    # sometimes you really do have to say "-lfoo -lbar -lfoo" in order to
    # resolve all symbols.  I just hope we never have to say "-lfoo obj.o
    # -lbar" to get things to work -- that's certainly a possibility, but a
    # pretty nasty way to arrange your C code.

    for lib in libraries:
        (lib_dir, lib_name) = os.path.split(lib)
        if lib_dir:
            lib_file = compiler.find_library_file([lib_dir], lib_name)
            if lib_file:
                lib_opts.append(lib_file)
            else:
                compiler.warn(
                    f"no library file corresponding to '{lib}' found (skipping)"
                )
        else:
            lib_opts.append(compiler.library_option(lib))
    return lib_opts

# === NexusCore/openenv\Lib\site-packages\litellm\cost_calculator.py ===
# What is this?
## File for 'response_cost' calculation in Logging
import time
from functools import lru_cache
from typing import Any, List, Literal, Optional, Tuple, Union, cast

from pydantic import BaseModel

import litellm
import litellm._logging
from litellm import verbose_logger
from litellm.constants import (
    DEFAULT_MAX_LRU_CACHE_SIZE,
    DEFAULT_REPLICATE_GPU_PRICE_PER_SECOND,
)
from litellm.litellm_core_utils.llm_cost_calc.tool_call_cost_tracking import (
    StandardBuiltInToolCostTracking,
)
from litellm.litellm_core_utils.llm_cost_calc.utils import (
    CostCalculatorUtils,
    _generic_cost_per_character,
    generic_cost_per_token,
    select_cost_metric_for_model,
)
from litellm.llms.anthropic.cost_calculation import (
    cost_per_token as anthropic_cost_per_token,
)
from litellm.llms.azure.cost_calculation import (
    cost_per_token as azure_openai_cost_per_token,
)
from litellm.llms.bedrock.image.cost_calculator import (
    cost_calculator as bedrock_image_cost_calculator,
)
from litellm.llms.databricks.cost_calculator import (
    cost_per_token as databricks_cost_per_token,
)
from litellm.llms.deepseek.cost_calculator import (
    cost_per_token as deepseek_cost_per_token,
)
from litellm.llms.fireworks_ai.cost_calculator import (
    cost_per_token as fireworks_ai_cost_per_token,
)
from litellm.llms.gemini.cost_calculator import cost_per_token as gemini_cost_per_token
from litellm.llms.openai.cost_calculation import (
    cost_per_second as openai_cost_per_second,
)
from litellm.llms.openai.cost_calculation import cost_per_token as openai_cost_per_token
from litellm.llms.together_ai.cost_calculator import get_model_params_and_category
from litellm.llms.vertex_ai.cost_calculator import (
    cost_per_character as google_cost_per_character,
)
from litellm.llms.vertex_ai.cost_calculator import (
    cost_per_token as google_cost_per_token,
)
from litellm.llms.vertex_ai.cost_calculator import cost_router as google_cost_router
from litellm.llms.vertex_ai.image_generation.cost_calculator import (
    cost_calculator as vertex_ai_image_cost_calculator,
)
from litellm.responses.utils import ResponseAPILoggingUtils
from litellm.types.llms.openai import (
    HttpxBinaryResponseContent,
    ImageGenerationRequestQuality,
    OpenAIModerationResponse,
    OpenAIRealtimeStreamList,
    OpenAIRealtimeStreamResponseBaseObject,
    OpenAIRealtimeStreamSessionEvents,
    ResponseAPIUsage,
    ResponsesAPIResponse,
)
from litellm.types.rerank import RerankBilledUnits, RerankResponse
from litellm.types.utils import (
    CallTypesLiteral,
    LiteLLMRealtimeStreamLoggingObject,
    LlmProviders,
    LlmProvidersSet,
    ModelInfo,
    StandardBuiltInToolsParams,
    Usage,
)
from litellm.utils import (
    CallTypes,
    CostPerToken,
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    ProviderConfigManager,
    TextCompletionResponse,
    TranscriptionResponse,
    _cached_get_model_info_helper,
    token_counter,
)


def _cost_per_token_custom_pricing_helper(
    prompt_tokens: float = 0,
    completion_tokens: float = 0,
    response_time_ms: Optional[float] = 0.0,
    ### CUSTOM PRICING ###
    custom_cost_per_token: Optional[CostPerToken] = None,
    custom_cost_per_second: Optional[float] = None,
) -> Optional[Tuple[float, float]]:
    """Internal helper function for calculating cost, if custom pricing given"""
    if custom_cost_per_token is None and custom_cost_per_second is None:
        return None

    if custom_cost_per_token is not None:
        input_cost = custom_cost_per_token["input_cost_per_token"] * prompt_tokens
        output_cost = custom_cost_per_token["output_cost_per_token"] * completion_tokens
        return input_cost, output_cost
    elif custom_cost_per_second is not None:
        output_cost = custom_cost_per_second * response_time_ms / 1000  # type: ignore
        return 0, output_cost

    return None


def cost_per_token(  # noqa: PLR0915
    model: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    response_time_ms: Optional[float] = 0.0,
    custom_llm_provider: Optional[str] = None,
    region_name=None,
    ### CHARACTER PRICING ###
    prompt_characters: Optional[int] = None,
    completion_characters: Optional[int] = None,
    ### PROMPT CACHING PRICING ### - used for anthropic
    cache_creation_input_tokens: Optional[int] = 0,
    cache_read_input_tokens: Optional[int] = 0,
    ### CUSTOM PRICING ###
    custom_cost_per_token: Optional[CostPerToken] = None,
    custom_cost_per_second: Optional[float] = None,
    ### NUMBER OF QUERIES ###
    number_of_queries: Optional[int] = None,
    ### USAGE OBJECT ###
    usage_object: Optional[Usage] = None,  # just read the usage object if provided
    ### BILLED UNITS ###
    rerank_billed_units: Optional[RerankBilledUnits] = None,
    ### CALL TYPE ###
    call_type: CallTypesLiteral = "completion",
    audio_transcription_file_duration: float = 0.0,  # for audio transcription calls - the file time in seconds
) -> Tuple[float, float]:  # type: ignore
    """
    Calculates the cost per token for a given model, prompt tokens, and completion tokens.

    Parameters:
        model (str): The name of the model to use. Default is ""
        prompt_tokens (int): The number of tokens in the prompt.
        completion_tokens (int): The number of tokens in the completion.
        response_time (float): The amount of time, in milliseconds, it took the call to complete.
        prompt_characters (float): The number of characters in the prompt. Used for vertex ai cost calculation.
        completion_characters (float): The number of characters in the completion response. Used for vertex ai cost calculation.
        custom_llm_provider (str): The llm provider to whom the call was made (see init.py for full list)
        custom_cost_per_token: Optional[CostPerToken]: the cost per input + output token for the llm api call.
        custom_cost_per_second: Optional[float]: the cost per second for the llm api call.
        call_type: Optional[str]: the call type

    Returns:
        tuple: A tuple containing the cost in USD dollars for prompt tokens and completion tokens, respectively.
    """
    if model is None:
        raise Exception("Invalid arg. Model cannot be none.")

    ## RECONSTRUCT USAGE BLOCK ##
    if usage_object is not None:
        usage_block = usage_object
    else:
        usage_block = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        )

    ## CUSTOM PRICING ##
    response_cost = _cost_per_token_custom_pricing_helper(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        response_time_ms=response_time_ms,
        custom_cost_per_second=custom_cost_per_second,
        custom_cost_per_token=custom_cost_per_token,
    )

    if response_cost is not None:
        return response_cost[0], response_cost[1]

    # given
    prompt_tokens_cost_usd_dollar: float = 0
    completion_tokens_cost_usd_dollar: float = 0
    model_cost_ref = litellm.model_cost
    model_with_provider = model
    if custom_llm_provider is not None:
        model_with_provider = custom_llm_provider + "/" + model
        if region_name is not None:
            model_with_provider_and_region = (
                f"{custom_llm_provider}/{region_name}/{model}"
            )
            if (
                model_with_provider_and_region in model_cost_ref
            ):  # use region based pricing, if it's available
                model_with_provider = model_with_provider_and_region
    else:
        _, custom_llm_provider, _, _ = litellm.get_llm_provider(model=model)
    model_without_prefix = model
    model_parts = model.split("/", 1)
    if len(model_parts) > 1:
        model_without_prefix = model_parts[1]
    else:
        model_without_prefix = model
    """
    Code block that formats model to lookup in litellm.model_cost
    Option1. model = "bedrock/ap-northeast-1/anthropic.claude-instant-v1". This is the most accurate since it is region based. Should always be option 1
    Option2. model = "openai/gpt-4"       - model = provider/model
    Option3. model = "anthropic.claude-3" - model = model
    """
    if (
        model_with_provider in model_cost_ref
    ):  # Option 2. use model with provider, model = "openai/gpt-4"
        model = model_with_provider
    elif model in model_cost_ref:  # Option 1. use model passed, model="gpt-4"
        model = model
    elif (
        model_without_prefix in model_cost_ref
    ):  # Option 3. if user passed model="bedrock/anthropic.claude-3", use model="anthropic.claude-3"
        model = model_without_prefix

    # see this https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models
    if call_type == "speech" or call_type == "aspeech":
        speech_model_info = litellm.get_model_info(
            model=model_without_prefix, custom_llm_provider=custom_llm_provider
        )
        cost_metric = select_cost_metric_for_model(speech_model_info)
        prompt_cost: float = 0.0
        completion_cost: float = 0.0
        if cost_metric == "cost_per_character":
            if prompt_characters is None:
                raise ValueError(
                    "prompt_characters must be provided for tts calls. prompt_characters={}, model={}, custom_llm_provider={}, call_type={}".format(
                        prompt_characters,
                        model,
                        custom_llm_provider,
                        call_type,
                    )
                )
            _prompt_cost, _completion_cost = _generic_cost_per_character(
                model=model_without_prefix,
                custom_llm_provider=custom_llm_provider,
                prompt_characters=prompt_characters,
                completion_characters=0,
                custom_prompt_cost=None,
                custom_completion_cost=0,
            )
            if _prompt_cost is None or _completion_cost is None:
                raise ValueError(
                    "cost for tts call is None. prompt_cost={}, completion_cost={}, model={}, custom_llm_provider={}, prompt_characters={}, completion_characters={}".format(
                        _prompt_cost,
                        _completion_cost,
                        model_without_prefix,
                        custom_llm_provider,
                        prompt_characters,
                        completion_characters,
                    )
                )
            prompt_cost = _prompt_cost
            completion_cost = _completion_cost
        elif cost_metric == "cost_per_token":
            prompt_cost, completion_cost = generic_cost_per_token(
                model=model_without_prefix,
                usage=usage_block,
                custom_llm_provider=custom_llm_provider,
            )

        return prompt_cost, completion_cost
    elif call_type == "arerank" or call_type == "rerank":
        return rerank_cost(
            model=model,
            custom_llm_provider=custom_llm_provider,
            billed_units=rerank_billed_units,
        )
    elif (
        call_type == "aretrieve_batch"
        or call_type == "retrieve_batch"
        or call_type == CallTypes.aretrieve_batch
        or call_type == CallTypes.retrieve_batch
    ):
        return batch_cost_calculator(
            usage=usage_block, model=model, custom_llm_provider=custom_llm_provider
        )
    elif call_type == "atranscription" or call_type == "transcription":
        return openai_cost_per_second(
            model=model,
            custom_llm_provider=custom_llm_provider,
            duration=audio_transcription_file_duration,
        )
    elif custom_llm_provider == "vertex_ai":
        cost_router = google_cost_router(
            model=model_without_prefix,
            custom_llm_provider=custom_llm_provider,
            call_type=call_type,
        )
        if cost_router == "cost_per_character":
            return google_cost_per_character(
                model=model_without_prefix,
                custom_llm_provider=custom_llm_provider,
                prompt_characters=prompt_characters,
                completion_characters=completion_characters,
                usage=usage_block,
            )
        elif cost_router == "cost_per_token":
            return google_cost_per_token(
                model=model_without_prefix,
                custom_llm_provider=custom_llm_provider,
                usage=usage_block,
            )
    elif custom_llm_provider == "anthropic":
        return anthropic_cost_per_token(model=model, usage=usage_block)
    elif custom_llm_provider == "openai":
        return openai_cost_per_token(model=model, usage=usage_block)
    elif custom_llm_provider == "databricks":
        return databricks_cost_per_token(model=model, usage=usage_block)
    elif custom_llm_provider == "fireworks_ai":
        return fireworks_ai_cost_per_token(model=model, usage=usage_block)
    elif custom_llm_provider == "azure":
        return azure_openai_cost_per_token(
            model=model, usage=usage_block, response_time_ms=response_time_ms
        )
    elif custom_llm_provider == "gemini":
        return gemini_cost_per_token(model=model, usage=usage_block)
    elif custom_llm_provider == "deepseek":
        return deepseek_cost_per_token(model=model, usage=usage_block)
    else:
        model_info = _cached_get_model_info_helper(
            model=model, custom_llm_provider=custom_llm_provider
        )

        if model_info["input_cost_per_token"] > 0:
            ## COST PER TOKEN ##
            prompt_tokens_cost_usd_dollar = (
                model_info["input_cost_per_token"] * prompt_tokens
            )
        elif (
            model_info.get("input_cost_per_second", None) is not None
            and response_time_ms is not None
        ):
            verbose_logger.debug(
                "For model=%s - input_cost_per_second: %s; response time: %s",
                model,
                model_info.get("input_cost_per_second", None),
                response_time_ms,
            )
            ## COST PER SECOND ##
            prompt_tokens_cost_usd_dollar = (
                model_info["input_cost_per_second"] * response_time_ms / 1000  # type: ignore
            )

        if model_info["output_cost_per_token"] > 0:
            completion_tokens_cost_usd_dollar = (
                model_info["output_cost_per_token"] * completion_tokens
            )
        elif (
            model_info.get("output_cost_per_second", None) is not None
            and response_time_ms is not None
        ):
            verbose_logger.debug(
                "For model=%s - output_cost_per_second: %s; response time: %s",
                model,
                model_info.get("output_cost_per_second", None),
                response_time_ms,
            )
            ## COST PER SECOND ##
            completion_tokens_cost_usd_dollar = (
                model_info["output_cost_per_second"] * response_time_ms / 1000  # type: ignore
            )

        verbose_logger.debug(
            "Returned custom cost for model=%s - prompt_tokens_cost_usd_dollar: %s, completion_tokens_cost_usd_dollar: %s",
            model,
            prompt_tokens_cost_usd_dollar,
            completion_tokens_cost_usd_dollar,
        )
        return prompt_tokens_cost_usd_dollar, completion_tokens_cost_usd_dollar


def get_replicate_completion_pricing(completion_response: dict, total_time=0.0):
    # see https://replicate.com/pricing
    # for all litellm currently supported LLMs, almost all requests go to a100_80gb
    a100_80gb_price_per_second_public = DEFAULT_REPLICATE_GPU_PRICE_PER_SECOND  # assume all calls sent to A100 80GB for now
    if total_time == 0.0:  # total time is in ms
        start_time = completion_response.get("created", time.time())
        end_time = getattr(completion_response, "ended", time.time())
        total_time = end_time - start_time

    return a100_80gb_price_per_second_public * total_time / 1000


def has_hidden_params(obj: Any) -> bool:
    return hasattr(obj, "_hidden_params")


def _get_provider_for_cost_calc(
    model: Optional[str],
    custom_llm_provider: Optional[str] = None,
) -> Optional[str]:
    if custom_llm_provider is not None:
        return custom_llm_provider
    if model is None:
        return None
    try:
        _, custom_llm_provider, _, _ = litellm.get_llm_provider(model=model)
    except Exception as e:
        verbose_logger.debug(
            f"litellm.cost_calculator.py::_get_provider_for_cost_calc() - Error inferring custom_llm_provider - {str(e)}"
        )
        return None

    return custom_llm_provider


def _select_model_name_for_cost_calc(
    model: Optional[str],
    completion_response: Optional[Any],
    base_model: Optional[str] = None,
    custom_pricing: Optional[bool] = None,
    custom_llm_provider: Optional[str] = None,
    router_model_id: Optional[str] = None,
) -> Optional[str]:
    """
    1. If custom pricing is true, return received model name
    2. If base_model is set (e.g. for azure models), return that
    3. If completion response has model set return that
    4. Check if model is passed in return that
    """

    return_model: Optional[str] = None
    region_name: Optional[str] = None
    custom_llm_provider = _get_provider_for_cost_calc(
        model=model, custom_llm_provider=custom_llm_provider
    )

    completion_response_model: Optional[str] = None
    if completion_response is not None:
        if isinstance(completion_response, BaseModel):
            completion_response_model = getattr(completion_response, "model", None)
        elif isinstance(completion_response, dict):
            completion_response_model = completion_response.get("model", None)
    hidden_params: Optional[dict] = getattr(completion_response, "_hidden_params", None)

    if custom_pricing is True:
        if router_model_id is not None and router_model_id in litellm.model_cost:
            return_model = router_model_id
        else:
            return_model = model

    if base_model is not None:
        return_model = base_model

    if completion_response_model is None and hidden_params is not None:
        if (
            hidden_params.get("model", None) is not None
            and len(hidden_params["model"]) > 0
        ):
            return_model = hidden_params.get("model", model)
    if hidden_params is not None and hidden_params.get("region_name", None) is not None:
        region_name = hidden_params.get("region_name", None)

    if return_model is None and completion_response_model is not None:
        return_model = completion_response_model

    if return_model is None and model is not None:
        return_model = model

    if (
        return_model is not None
        and custom_llm_provider is not None
        and not _model_contains_known_llm_provider(return_model)
    ):  # add provider prefix if not already present, to match model_cost
        if region_name is not None:
            return_model = f"{custom_llm_provider}/{region_name}/{return_model}"
        else:
            return_model = f"{custom_llm_provider}/{return_model}"

    return return_model


@lru_cache(maxsize=DEFAULT_MAX_LRU_CACHE_SIZE)
def _model_contains_known_llm_provider(model: str) -> bool:
    """
    Check if the model contains a known llm provider
    """
    _provider_prefix = model.split("/")[0]
    return _provider_prefix in LlmProvidersSet


def _get_usage_object(
    completion_response: Any,
) -> Optional[Usage]:
    usage_obj = cast(
        Union[Usage, ResponseAPIUsage, dict, BaseModel],
        (
            completion_response.get("usage")
            if isinstance(completion_response, dict)
            else getattr(completion_response, "get", lambda x: None)("usage")
        ),
    )

    if usage_obj is None:
        return None
    if isinstance(usage_obj, Usage):
        return usage_obj
    elif (
        usage_obj is not None
        and (isinstance(usage_obj, dict) or isinstance(usage_obj, ResponseAPIUsage))
        and ResponseAPILoggingUtils._is_response_api_usage(usage_obj)
    ):
        return ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
            usage_obj
        )
    elif isinstance(usage_obj, dict):
        return Usage(**usage_obj)
    elif isinstance(usage_obj, BaseModel):
        return Usage(**usage_obj.model_dump())
    else:
        verbose_logger.debug(
            f"Unknown usage object type: {type(usage_obj)}, usage_obj: {usage_obj}"
        )
        return None


def _is_known_usage_objects(usage_obj):
    """Returns True if the usage obj is a known Usage type"""
    return isinstance(usage_obj, litellm.Usage) or isinstance(
        usage_obj, ResponseAPIUsage
    )


def _infer_call_type(
    call_type: Optional[CallTypesLiteral], completion_response: Any
) -> Optional[CallTypesLiteral]:
    if call_type is not None:
        return call_type

    if completion_response is None:
        return None

    if isinstance(completion_response, ModelResponse):
        return "completion"
    elif isinstance(completion_response, EmbeddingResponse):
        return "embedding"
    elif isinstance(completion_response, TranscriptionResponse):
        return "transcription"
    elif isinstance(completion_response, HttpxBinaryResponseContent):
        return "speech"
    elif isinstance(completion_response, RerankResponse):
        return "rerank"
    elif isinstance(completion_response, ImageResponse):
        return "image_generation"
    elif isinstance(completion_response, TextCompletionResponse):
        return "text_completion"

    return call_type


def completion_cost(  # noqa: PLR0915
    completion_response=None,
    model: Optional[str] = None,
    prompt="",
    messages: List = [],
    completion="",
    total_time: Optional[float] = 0.0,  # used for replicate, sagemaker
    call_type: Optional[CallTypesLiteral] = None,
    ### REGION ###
    custom_llm_provider=None,
    region_name=None,  # used for bedrock pricing
    ### IMAGE GEN ###
    size: Optional[str] = None,
    quality: Optional[str] = None,
    n: Optional[int] = None,  # number of images
    ### CUSTOM PRICING ###
    custom_cost_per_token: Optional[CostPerToken] = None,
    custom_cost_per_second: Optional[float] = None,
    optional_params: Optional[dict] = None,
    custom_pricing: Optional[bool] = None,
    base_model: Optional[str] = None,
    standard_built_in_tools_params: Optional[StandardBuiltInToolsParams] = None,
    litellm_model_name: Optional[str] = None,
    router_model_id: Optional[str] = None,
) -> float:
    """
    Calculate the cost of a given completion call fot GPT-3.5-turbo, llama2, any litellm supported llm.

    Parameters:
        completion_response (litellm.ModelResponses): [Required] The response received from a LiteLLM completion request.

        [OPTIONAL PARAMS]
        model (str): Optional. The name of the language model used in the completion calls
        prompt (str): Optional. The input prompt passed to the llm
        completion (str): Optional. The output completion text from the llm
        total_time (float, int): Optional. (Only used for Replicate LLMs) The total time used for the request in seconds
        custom_cost_per_token: Optional[CostPerToken]: the cost per input + output token for the llm api call.
        custom_cost_per_second: Optional[float]: the cost per second for the llm api call.

    Returns:
        float: The cost in USD dollars for the completion based on the provided parameters.

    Exceptions:
        Raises exception if model not in the litellm model cost map. Register model, via custom pricing or PR - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json


    Note:
        - If completion_response is provided, the function extracts token information and the model name from it.
        - If completion_response is not provided, the function calculates token counts based on the model and input text.
        - The cost is calculated based on the model, prompt tokens, and completion tokens.
        - For certain models containing "togethercomputer" in the name, prices are based on the model size.
        - For un-mapped Replicate models, the cost is calculated based on the total time used for the request.
    """
    try:
        call_type = _infer_call_type(call_type, completion_response) or "completion"

        if (
            (call_type == "aimage_generation" or call_type == "image_generation")
            and model is not None
            and isinstance(model, str)
            and len(model) == 0
            and custom_llm_provider == "azure"
        ):
            model = "dall-e-2"  # for dall-e-2, azure expects an empty model name
        # Handle Inputs to completion_cost
        prompt_tokens = 0
        prompt_characters: Optional[int] = None
        completion_tokens = 0
        completion_characters: Optional[int] = None
        cache_creation_input_tokens: Optional[int] = None
        cache_read_input_tokens: Optional[int] = None
        audio_transcription_file_duration: float = 0.0
        cost_per_token_usage_object: Optional[Usage] = _get_usage_object(
            completion_response=completion_response
        )
        rerank_billed_units: Optional[RerankBilledUnits] = None

        selected_model = _select_model_name_for_cost_calc(
            model=model,
            completion_response=completion_response,
            custom_llm_provider=custom_llm_provider,
            custom_pricing=custom_pricing,
            base_model=base_model,
            router_model_id=router_model_id,
        )

        potential_model_names = [selected_model]
        if model is not None:
            potential_model_names.append(model)
        for idx, model in enumerate(potential_model_names):
            try:
                verbose_logger.info(
                    f"selected model name for cost calculation: {model}"
                )

                if completion_response is not None and (
                    isinstance(completion_response, BaseModel)
                    or isinstance(completion_response, dict)
                ):  # tts returns a custom class
                    if isinstance(completion_response, dict):
                        usage_obj: Optional[
                            Union[dict, Usage]
                        ] = completion_response.get("usage", {})
                    else:
                        usage_obj = getattr(completion_response, "usage", {})
                    if isinstance(usage_obj, BaseModel) and not _is_known_usage_objects(
                        usage_obj=usage_obj
                    ):
                        setattr(
                            completion_response,
                            "usage",
                            litellm.Usage(**usage_obj.model_dump()),
                        )
                    if usage_obj is None:
                        _usage = {}
                    elif isinstance(usage_obj, BaseModel):
                        _usage = usage_obj.model_dump()
                    else:
                        _usage = usage_obj

                    if ResponseAPILoggingUtils._is_response_api_usage(_usage):
                        _usage = ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
                            _usage
                        ).model_dump()

                    # get input/output tokens from completion_response
                    prompt_tokens = _usage.get("prompt_tokens", 0)
                    completion_tokens = _usage.get("completion_tokens", 0)
                    cache_creation_input_tokens = _usage.get(
                        "cache_creation_input_tokens", 0
                    )
                    cache_read_input_tokens = _usage.get("cache_read_input_tokens", 0)
                    if (
                        "prompt_tokens_details" in _usage
                        and _usage["prompt_tokens_details"] != {}
                        and _usage["prompt_tokens_details"]
                    ):
                        prompt_tokens_details = _usage.get("prompt_tokens_details", {})
                        cache_read_input_tokens = prompt_tokens_details.get(
                            "cached_tokens", 0
                        )

                    total_time = getattr(completion_response, "_response_ms", 0)

                    hidden_params = getattr(completion_response, "_hidden_params", None)
                    if hidden_params is not None:
                        custom_llm_provider = hidden_params.get(
                            "custom_llm_provider", custom_llm_provider or None
                        )
                        region_name = hidden_params.get("region_name", region_name)
                        size = hidden_params.get("optional_params", {}).get(
                            "size", "1024-x-1024"
                        )  # openai default
                        quality = hidden_params.get("optional_params", {}).get(
                            "quality", "standard"
                        )  # openai default
                        n = hidden_params.get("optional_params", {}).get(
                            "n", 1
                        )  # openai default
                else:
                    if model is None:
                        raise ValueError(
                            f"Model is None and does not exist in passed completion_response. Passed completion_response={completion_response}, model={model}"
                        )
                    if len(messages) > 0:
                        prompt_tokens = token_counter(model=model, messages=messages)
                    elif len(prompt) > 0:
                        prompt_tokens = token_counter(model=model, text=prompt)
                    completion_tokens = token_counter(model=model, text=completion)

                if model is None:
                    raise ValueError(
                        f"Model is None and does not exist in passed completion_response. Passed completion_response={completion_response}, model={model}"
                    )
                if custom_llm_provider is None:
                    try:
                        model, custom_llm_provider, _, _ = litellm.get_llm_provider(
                            model=model
                        )  # strip the llm provider from the model name -> for image gen cost calculation
                    except Exception as e:
                        verbose_logger.debug(
                            "litellm.cost_calculator.py::completion_cost() - Error inferring custom_llm_provider - {}".format(
                                str(e)
                            )
                        )
                if CostCalculatorUtils._call_type_has_image_response(call_type):
                    ### IMAGE GENERATION COST CALCULATION ###
                    if custom_llm_provider == "vertex_ai":
                        if isinstance(completion_response, ImageResponse):
                            return vertex_ai_image_cost_calculator(
                                model=model,
                                image_response=completion_response,
                            )
                    elif custom_llm_provider == "bedrock":
                        if isinstance(completion_response, ImageResponse):
                            return bedrock_image_cost_calculator(
                                model=model,
                                size=size,
                                image_response=completion_response,
                                optional_params=optional_params,
                            )
                        raise TypeError(
                            "completion_response must be of type ImageResponse for bedrock image cost calculation"
                        )
                    else:
                        return default_image_cost_calculator(
                            model=model,
                            quality=quality,
                            custom_llm_provider=custom_llm_provider,
                            n=n,
                            size=size,
                            optional_params=optional_params,
                        )
                elif (
                    call_type == CallTypes.speech.value
                    or call_type == CallTypes.aspeech.value
                ):
                    prompt_characters = litellm.utils._count_characters(text=prompt)
                elif (
                    call_type == CallTypes.atranscription.value
                    or call_type == CallTypes.transcription.value
                ):
                    audio_transcription_file_duration = getattr(
                        completion_response, "duration", 0.0
                    )
                elif (
                    call_type == CallTypes.rerank.value
                    or call_type == CallTypes.arerank.value
                ):
                    if completion_response is not None and isinstance(
                        completion_response, RerankResponse
                    ):
                        meta_obj = completion_response.meta
                        if meta_obj is not None:
                            billed_units = meta_obj.get("billed_units", {}) or {}
                        else:
                            billed_units = {}

                        rerank_billed_units = RerankBilledUnits(
                            search_units=billed_units.get("search_units"),
                            total_tokens=billed_units.get("total_tokens"),
                        )

                        search_units = (
                            billed_units.get("search_units") or 1
                        )  # cohere charges per request by default.
                        completion_tokens = search_units
                elif call_type == CallTypes.arealtime.value and isinstance(
                    completion_response, LiteLLMRealtimeStreamLoggingObject
                ):
                    if (
                        cost_per_token_usage_object is None
                        or custom_llm_provider is None
                    ):
                        raise ValueError(
                            "usage object and custom_llm_provider must be provided for realtime stream cost calculation. Got cost_per_token_usage_object={}, custom_llm_provider={}".format(
                                cost_per_token_usage_object,
                                custom_llm_provider,
                            )
                        )
                    return handle_realtime_stream_cost_calculation(
                        results=completion_response.results,
                        combined_usage_object=cost_per_token_usage_object,
                        custom_llm_provider=custom_llm_provider,
                        litellm_model_name=model,
                    )
                # Calculate cost based on prompt_tokens, completion_tokens
                if (
                    "togethercomputer" in model
                    or "together_ai" in model
                    or custom_llm_provider == "together_ai"
                ):
                    # together ai prices based on size of llm
                    # get_model_params_and_category takes a model name and returns the category of LLM size it is in model_prices_and_context_window.json

                    model = get_model_params_and_category(
                        model, call_type=CallTypes(call_type)
                    )

                # replicate llms are calculate based on time for request running
                # see https://replicate.com/pricing
                elif (
                    model in litellm.replicate_models or "replicate" in model
                ) and model not in litellm.model_cost:
                    # for unmapped replicate model, default to replicate's time tracking logic
                    return get_replicate_completion_pricing(completion_response, total_time)  # type: ignore

                if model is None:
                    raise ValueError(
                        f"Model is None and does not exist in passed completion_response. Passed completion_response={completion_response}, model={model}"
                    )

                if (
                    custom_llm_provider is not None
                    and custom_llm_provider == "vertex_ai"
                ):
                    # Calculate the prompt characters + response characters
                    if len(messages) > 0:
                        prompt_string = litellm.utils.get_formatted_prompt(
                            data={"messages": messages}, call_type="completion"
                        )

                        prompt_characters = litellm.utils._count_characters(
                            text=prompt_string
                        )
                    if completion_response is not None and isinstance(
                        completion_response, ModelResponse
                    ):
                        completion_string = litellm.utils.get_response_string(
                            response_obj=completion_response
                        )
                        completion_characters = litellm.utils._count_characters(
                            text=completion_string
                        )

                (
                    prompt_tokens_cost_usd_dollar,
                    completion_tokens_cost_usd_dollar,
                ) = cost_per_token(
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    custom_llm_provider=custom_llm_provider,
                    response_time_ms=total_time,
                    region_name=region_name,
                    custom_cost_per_second=custom_cost_per_second,
                    custom_cost_per_token=custom_cost_per_token,
                    prompt_characters=prompt_characters,
                    completion_characters=completion_characters,
                    cache_creation_input_tokens=cache_creation_input_tokens,
                    cache_read_input_tokens=cache_read_input_tokens,
                    usage_object=cost_per_token_usage_object,
                    call_type=cast(CallTypesLiteral, call_type),
                    audio_transcription_file_duration=audio_transcription_file_duration,
                    rerank_billed_units=rerank_billed_units,
                )
                _final_cost = (
                    prompt_tokens_cost_usd_dollar + completion_tokens_cost_usd_dollar
                )
                _final_cost += (
                    StandardBuiltInToolCostTracking.get_cost_for_built_in_tools(
                        model=model,
                        response_object=completion_response,
                        usage=cost_per_token_usage_object,
                        standard_built_in_tools_params=standard_built_in_tools_params,
                        custom_llm_provider=custom_llm_provider,
                    )
                )
                return _final_cost
            except Exception as e:
                verbose_logger.debug(
                    "litellm.cost_calculator.py::completion_cost() - Error calculating cost for model={} - {}".format(
                        model, str(e)
                    )
                )
                if idx == len(potential_model_names) - 1:
                    raise e
        raise Exception(
            "Unable to calculat cost for received potential model names - {}".format(
                potential_model_names
            )
        )
    except Exception as e:
        raise e


def get_response_cost_from_hidden_params(
    hidden_params: Union[dict, BaseModel],
) -> Optional[float]:
    if isinstance(hidden_params, BaseModel):
        _hidden_params_dict = hidden_params.model_dump()
    else:
        _hidden_params_dict = hidden_params

    additional_headers = _hidden_params_dict.get("additional_headers", {})
    if (
        additional_headers
        and "llm_provider-x-litellm-response-cost" in additional_headers
    ):
        response_cost = additional_headers["llm_provider-x-litellm-response-cost"]
        if response_cost is None:
            return None
        return float(additional_headers["llm_provider-x-litellm-response-cost"])
    return None


def response_cost_calculator(
    response_object: Union[
        ModelResponse,
        EmbeddingResponse,
        ImageResponse,
        TranscriptionResponse,
        TextCompletionResponse,
        HttpxBinaryResponseContent,
        RerankResponse,
        ResponsesAPIResponse,
        LiteLLMRealtimeStreamLoggingObject,
        OpenAIModerationResponse,
    ],
    model: str,
    custom_llm_provider: Optional[str],
    call_type: Literal[
        "embedding",
        "aembedding",
        "completion",
        "acompletion",
        "atext_completion",
        "text_completion",
        "image_generation",
        "aimage_generation",
        "moderation",
        "amoderation",
        "atranscription",
        "transcription",
        "aspeech",
        "speech",
        "rerank",
        "arerank",
    ],
    optional_params: dict,
    cache_hit: Optional[bool] = None,
    base_model: Optional[str] = None,
    custom_pricing: Optional[bool] = None,
    prompt: str = "",
    standard_built_in_tools_params: Optional[StandardBuiltInToolsParams] = None,
    litellm_model_name: Optional[str] = None,
    router_model_id: Optional[str] = None,
) -> float:
    """
    Returns
    - float or None: cost of response
    """
    try:
        response_cost: float = 0.0
        if cache_hit is not None and cache_hit is True:
            response_cost = 0.0
        else:
            if isinstance(response_object, BaseModel):
                response_object._hidden_params["optional_params"] = optional_params

                if hasattr(response_object, "_hidden_params"):
                    provider_response_cost = get_response_cost_from_hidden_params(
                        response_object._hidden_params
                    )
                    if provider_response_cost is not None:
                        return provider_response_cost

            response_cost = completion_cost(
                completion_response=response_object,
                model=model,
                call_type=call_type,
                custom_llm_provider=custom_llm_provider,
                optional_params=optional_params,
                custom_pricing=custom_pricing,
                base_model=base_model,
                prompt=prompt,
                standard_built_in_tools_params=standard_built_in_tools_params,
                litellm_model_name=litellm_model_name,
                router_model_id=router_model_id,
            )
        return response_cost
    except Exception as e:
        raise e


def rerank_cost(
    model: str,
    custom_llm_provider: Optional[str],
    billed_units: Optional[RerankBilledUnits] = None,
) -> Tuple[float, float]:
    """
    Returns
    - float or None: cost of response OR none if error.
    """
    _, custom_llm_provider, _, _ = litellm.get_llm_provider(
        model=model, custom_llm_provider=custom_llm_provider
    )

    try:
        config = ProviderConfigManager.get_provider_rerank_config(
            model=model,
            api_base=None,
            present_version_params=[],
            provider=LlmProviders(custom_llm_provider),
        )

        try:
            model_info: Optional[ModelInfo] = litellm.get_model_info(
                model=model, custom_llm_provider=custom_llm_provider
            )
        except Exception:
            model_info = None

        return config.calculate_rerank_cost(
            model=model,
            custom_llm_provider=custom_llm_provider,
            billed_units=billed_units,
            model_info=model_info,
        )
    except Exception as e:
        raise e


def transcription_cost(
    model: str, custom_llm_provider: Optional[str], duration: float
) -> Tuple[float, float]:
    return openai_cost_per_second(
        model=model, custom_llm_provider=custom_llm_provider, duration=duration
    )


def default_image_cost_calculator(
    model: str,
    custom_llm_provider: Optional[str] = None,
    quality: Optional[str] = None,
    n: Optional[int] = 1,  # Default to 1 image
    size: Optional[str] = "1024-x-1024",  # OpenAI default
    optional_params: Optional[dict] = None,
) -> float:
    """
    Default image cost calculator for image generation

    Args:
        model (str): Model name
        image_response (ImageResponse): Response from image generation
        quality (Optional[str]): Image quality setting
        n (Optional[int]): Number of images generated
        size (Optional[str]): Image size (e.g. "1024x1024" or "1024-x-1024")

    Returns:
        float: Cost in USD for the image generation

    Raises:
        Exception: If model pricing not found in cost map
    """
    # Standardize size format to use "-x-"
    size_str: str = size or "1024-x-1024"
    size_str = (
        size_str.replace("x", "-x-")
        if "x" in size_str and "-x-" not in size_str
        else size_str
    )

    # Parse dimensions
    height, width = map(int, size_str.split("-x-"))

    # Build model names for cost lookup
    base_model_name = f"{size_str}/{model}"
    model_name_without_custom_llm_provider: Optional[str] = None
    if custom_llm_provider and model.startswith(f"{custom_llm_provider}/"):
        model_name_without_custom_llm_provider = model.replace(
            f"{custom_llm_provider}/", ""
        )
        base_model_name = (
            f"{custom_llm_provider}/{size_str}/{model_name_without_custom_llm_provider}"
        )
    model_name_with_quality = (
        f"{quality}/{base_model_name}" if quality else base_model_name
    )

    # gpt-image-1 models use low, medium, high quality. If user did not specify quality, use medium fot gpt-image-1 model family
    model_name_with_v2_quality = (
        f"{ImageGenerationRequestQuality.MEDIUM.value}/{base_model_name}"
    )

    verbose_logger.debug(
        f"Looking up cost for models: {model_name_with_quality}, {base_model_name}"
    )

    model_without_provider = f"{size_str}/{model.split('/')[-1]}"
    model_with_quality_without_provider = (
        f"{quality}/{model_without_provider}" if quality else model_without_provider
    )

    # Try model with quality first, fall back to base model name
    cost_info: Optional[dict] = None
    models_to_check: List[Optional[str]] = [
        model_name_with_quality,
        base_model_name,
        model_name_with_v2_quality,
        model_with_quality_without_provider,
        model_without_provider,
        model,
        model_name_without_custom_llm_provider,
    ]
    for _model in models_to_check:
        if _model is not None and _model in litellm.model_cost:
            cost_info = litellm.model_cost[_model]
            break
    if cost_info is None:
        raise Exception(
            f"Model not found in cost map. Tried checking {models_to_check}"
        )

    return cost_info["input_cost_per_pixel"] * height * width * n


def batch_cost_calculator(
    usage: Usage,
    model: str,
    custom_llm_provider: Optional[str] = None,
) -> Tuple[float, float]:
    """
    Calculate the cost of a batch job
    """

    _, custom_llm_provider, _, _ = litellm.get_llm_provider(
        model=model, custom_llm_provider=custom_llm_provider
    )

    verbose_logger.info(
        "Calculating batch cost per token. model=%s, custom_llm_provider=%s",
        model,
        custom_llm_provider,
    )

    try:
        model_info: Optional[ModelInfo] = litellm.get_model_info(
            model=model, custom_llm_provider=custom_llm_provider
        )
    except Exception:
        model_info = None

    if not model_info:
        return 0.0, 0.0

    input_cost_per_token_batches = model_info.get("input_cost_per_token_batches")
    input_cost_per_token = model_info.get("input_cost_per_token")
    output_cost_per_token_batches = model_info.get("output_cost_per_token_batches")
    output_cost_per_token = model_info.get("output_cost_per_token")
    total_prompt_cost = 0.0
    total_completion_cost = 0.0
    if input_cost_per_token_batches:
        total_prompt_cost = usage.prompt_tokens * input_cost_per_token_batches
    elif input_cost_per_token:
        total_prompt_cost = (
            usage.prompt_tokens * (input_cost_per_token) / 2
        )  # batch cost is usually half of the regular token cost
    if output_cost_per_token_batches:
        total_completion_cost = usage.completion_tokens * output_cost_per_token_batches
    elif output_cost_per_token:
        total_completion_cost = (
            usage.completion_tokens * (output_cost_per_token) / 2
        )  # batch cost is usually half of the regular token cost

    return total_prompt_cost, total_completion_cost


class BaseTokenUsageProcessor:
    @staticmethod
    def combine_usage_objects(usage_objects: List[Usage]) -> Usage:
        """
        Combine multiple Usage objects into a single Usage object, checking model keys for nested values.
        """
        from litellm.types.utils import (
            CompletionTokensDetails,
            PromptTokensDetailsWrapper,
            Usage,
        )

        combined = Usage()

        # Sum basic token counts
        for usage in usage_objects:
            # Handle direct attributes by checking what exists in the model
            for attr in dir(usage):
                if not attr.startswith("_") and not callable(getattr(usage, attr)):
                    current_val = getattr(combined, attr, 0)
                    new_val = getattr(usage, attr, 0)
                    if (
                        new_val is not None
                        and isinstance(new_val, (int, float))
                        and isinstance(current_val, (int, float))
                    ):
                        setattr(combined, attr, current_val + new_val)
            # Handle nested prompt_tokens_details
            if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
                if (
                    not hasattr(combined, "prompt_tokens_details")
                    or not combined.prompt_tokens_details
                ):
                    combined.prompt_tokens_details = PromptTokensDetailsWrapper()

                # Check what keys exist in the model's prompt_tokens_details
                for attr in usage.prompt_tokens_details.model_fields:
                    if (
                        hasattr(usage.prompt_tokens_details, attr)
                        and not attr.startswith("_")
                        and not callable(getattr(usage.prompt_tokens_details, attr))
                    ):
                        current_val = (
                            getattr(combined.prompt_tokens_details, attr, 0) or 0
                        )
                        new_val = getattr(usage.prompt_tokens_details, attr, 0) or 0
                        if new_val is not None and isinstance(new_val, (int, float)):
                            setattr(
                                combined.prompt_tokens_details,
                                attr,
                                current_val + new_val,
                            )

            # Handle nested completion_tokens_details
            if (
                hasattr(usage, "completion_tokens_details")
                and usage.completion_tokens_details
            ):
                if (
                    not hasattr(combined, "completion_tokens_details")
                    or not combined.completion_tokens_details
                ):
                    combined.completion_tokens_details = CompletionTokensDetails()

                # Check what keys exist in the model's completion_tokens_details
                for attr in dir(usage.completion_tokens_details):
                    if not attr.startswith("_") and not callable(
                        getattr(usage.completion_tokens_details, attr)
                    ):
                        current_val = getattr(
                            combined.completion_tokens_details, attr, 0
                        )
                        new_val = getattr(usage.completion_tokens_details, attr, 0)
                        if new_val is not None:
                            setattr(
                                combined.completion_tokens_details,
                                attr,
                                current_val + new_val,
                            )

        return combined


class RealtimeAPITokenUsageProcessor(BaseTokenUsageProcessor):
    @staticmethod
    def collect_usage_from_realtime_stream_results(
        results: OpenAIRealtimeStreamList,
    ) -> List[Usage]:
        """
        Collect usage from realtime stream results
        """
        response_done_events: List[OpenAIRealtimeStreamResponseBaseObject] = cast(
            List[OpenAIRealtimeStreamResponseBaseObject],
            [result for result in results if result["type"] == "response.done"],
        )
        usage_objects: List[Usage] = []
        for result in response_done_events:
            usage_object = (
                ResponseAPILoggingUtils._transform_response_api_usage_to_chat_usage(
                    result["response"].get("usage", {})
                )
            )
            usage_objects.append(usage_object)
        return usage_objects

    @staticmethod
    def collect_and_combine_usage_from_realtime_stream_results(
        results: OpenAIRealtimeStreamList,
    ) -> Usage:
        """
        Collect and combine usage from realtime stream results
        """
        collected_usage_objects = (
            RealtimeAPITokenUsageProcessor.collect_usage_from_realtime_stream_results(
                results
            )
        )
        combined_usage_object = RealtimeAPITokenUsageProcessor.combine_usage_objects(
            collected_usage_objects
        )
        return combined_usage_object

    @staticmethod
    def create_logging_realtime_object(
        usage: Usage, results: OpenAIRealtimeStreamList
    ) -> LiteLLMRealtimeStreamLoggingObject:
        return LiteLLMRealtimeStreamLoggingObject(
            usage=usage,
            results=results,
        )


def handle_realtime_stream_cost_calculation(
    results: OpenAIRealtimeStreamList,
    combined_usage_object: Usage,
    custom_llm_provider: str,
    litellm_model_name: str,
) -> float:
    """
    Handles the cost calculation for realtime stream responses.

    Pick the 'response.done' events. Calculate total cost across all 'response.done' events.

    Args:
        results: A list of OpenAIRealtimeStreamBaseObject objects
    """
    received_model = None
    potential_model_names = []
    for result in results:
        if result["type"] == "session.created":
            received_model = cast(OpenAIRealtimeStreamSessionEvents, result)[
                "session"
            ].get("model", None)
            potential_model_names.append(received_model)

    potential_model_names.append(litellm_model_name)
    input_cost_per_token = 0.0
    output_cost_per_token = 0.0

    for model_name in potential_model_names:
        try:
            if model_name is None:
                continue
            _input_cost_per_token, _output_cost_per_token = generic_cost_per_token(
                model=model_name,
                usage=combined_usage_object,
                custom_llm_provider=custom_llm_provider,
            )
        except Exception:
            continue
        input_cost_per_token += _input_cost_per_token
        output_cost_per_token += _output_cost_per_token
        break  # exit if we find a valid model
    total_cost = input_cost_per_token + output_cost_per_token

    return total_cost

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\dist.py ===
"""distutils.dist

Provides the Distribution class, which represents the module distribution
being built/installed/distributed.
"""

from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import re
import sys
import warnings
from collections.abc import Iterable, MutableMapping
from email import message_from_file
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    TypeVar,
    Union,
    overload,
)

from packaging.utils import canonicalize_name, canonicalize_version

from ._log import log
from .debug import DEBUG
from .errors import (
    DistutilsArgError,
    DistutilsClassError,
    DistutilsModuleError,
    DistutilsOptionError,
)
from .fancy_getopt import FancyGetopt, translate_longopt
from .util import check_environ, rfc822_escape, strtobool

if TYPE_CHECKING:
    from _typeshed import SupportsWrite
    from typing_extensions import TypeAlias

    # type-only import because of mutual dependence between these modules
    from .cmd import Command

_CommandT = TypeVar("_CommandT", bound="Command")
_OptionsList: TypeAlias = list[
    Union[tuple[str, Union[str, None], str, int], tuple[str, Union[str, None], str]]
]


# Regex to define acceptable Distutils command names.  This is not *quite*
# the same as a Python NAME -- I don't allow leading underscores.  The fact
# that they're very similar is no coincidence; the default naming scheme is
# to look for a Python module named after the command.
command_re = re.compile(r'^[a-zA-Z]([a-zA-Z0-9_]*)$')


def _ensure_list(value: str | Iterable[str], fieldname) -> str | list[str]:
    if isinstance(value, str):
        # a string containing comma separated values is okay.  It will
        # be converted to a list by Distribution.finalize_options().
        pass
    elif not isinstance(value, list):
        # passing a tuple or an iterator perhaps, warn and convert
        typename = type(value).__name__
        msg = "Warning: '{fieldname}' should be a list, got type '{typename}'"
        msg = msg.format(**locals())
        log.warning(msg)
        value = list(value)
    return value


class Distribution:
    """The core of the Distutils.  Most of the work hiding behind 'setup'
    is really done within a Distribution instance, which farms the work out
    to the Distutils commands specified on the command line.

    Setup scripts will almost never instantiate Distribution directly,
    unless the 'setup()' function is totally inadequate to their needs.
    However, it is conceivable that a setup script might wish to subclass
    Distribution for some specialized purpose, and then pass the subclass
    to 'setup()' as the 'distclass' keyword argument.  If so, it is
    necessary to respect the expectations that 'setup' has of Distribution.
    See the code for 'setup()', in core.py, for details.
    """

    # 'global_options' describes the command-line options that may be
    # supplied to the setup script prior to any actual commands.
    # Eg. "./setup.py -n" or "./setup.py --quiet" both take advantage of
    # these global options.  This list should be kept to a bare minimum,
    # since every global option is also valid as a command option -- and we
    # don't want to pollute the commands with too many options that they
    # have minimal control over.
    # The fourth entry for verbose means that it can be repeated.
    global_options: ClassVar[_OptionsList] = [
        ('verbose', 'v', "run verbosely (default)", 1),
        ('quiet', 'q', "run quietly (turns verbosity off)"),
        ('dry-run', 'n', "don't actually do anything"),
        ('help', 'h', "show detailed help message"),
        ('no-user-cfg', None, 'ignore pydistutils.cfg in your home directory'),
    ]

    # 'common_usage' is a short (2-3 line) string describing the common
    # usage of the setup script.
    common_usage: ClassVar[str] = """\
Common commands: (see '--help-commands' for more)

  setup.py build      will build the package underneath 'build/'
  setup.py install    will install the package
"""

    # options that are not propagated to the commands
    display_options: ClassVar[_OptionsList] = [
        ('help-commands', None, "list all available commands"),
        ('name', None, "print package name"),
        ('version', 'V', "print package version"),
        ('fullname', None, "print <package name>-<version>"),
        ('author', None, "print the author's name"),
        ('author-email', None, "print the author's email address"),
        ('maintainer', None, "print the maintainer's name"),
        ('maintainer-email', None, "print the maintainer's email address"),
        ('contact', None, "print the maintainer's name if known, else the author's"),
        (
            'contact-email',
            None,
            "print the maintainer's email address if known, else the author's",
        ),
        ('url', None, "print the URL for this package"),
        ('license', None, "print the license of the package"),
        ('licence', None, "alias for --license"),
        ('description', None, "print the package description"),
        ('long-description', None, "print the long package description"),
        ('platforms', None, "print the list of platforms"),
        ('classifiers', None, "print the list of classifiers"),
        ('keywords', None, "print the list of keywords"),
        ('provides', None, "print the list of packages/modules provided"),
        ('requires', None, "print the list of packages/modules required"),
        ('obsoletes', None, "print the list of packages/modules made obsolete"),
    ]
    display_option_names: ClassVar[list[str]] = [
        translate_longopt(x[0]) for x in display_options
    ]

    # negative options are options that exclude other options
    negative_opt: ClassVar[dict[str, str]] = {'quiet': 'verbose'}

    # -- Creation/initialization methods -------------------------------

    # Can't Unpack a TypedDict with optional properties, so using Any instead
    def __init__(self, attrs: MutableMapping[str, Any] | None = None) -> None:  # noqa: C901
        """Construct a new Distribution instance: initialize all the
        attributes of a Distribution, and then use 'attrs' (a dictionary
        mapping attribute names to values) to assign some of those
        attributes their "real" values.  (Any attributes not mentioned in
        'attrs' will be assigned to some null value: 0, None, an empty list
        or dictionary, etc.)  Most importantly, initialize the
        'command_obj' attribute to the empty dictionary; this will be
        filled in with real command objects by 'parse_command_line()'.
        """

        # Default values for our command-line options
        self.verbose = True
        self.dry_run = False
        self.help = False
        for attr in self.display_option_names:
            setattr(self, attr, False)

        # Store the distribution meta-data (name, version, author, and so
        # forth) in a separate object -- we're getting to have enough
        # information here (and enough command-line options) that it's
        # worth it.  Also delegate 'get_XXX()' methods to the 'metadata'
        # object in a sneaky and underhanded (but efficient!) way.
        self.metadata = DistributionMetadata()
        for basename in self.metadata._METHOD_BASENAMES:
            method_name = "get_" + basename
            setattr(self, method_name, getattr(self.metadata, method_name))

        # 'cmdclass' maps command names to class objects, so we
        # can 1) quickly figure out which class to instantiate when
        # we need to create a new command object, and 2) have a way
        # for the setup script to override command classes
        self.cmdclass: dict[str, type[Command]] = {}

        # 'command_packages' is a list of packages in which commands
        # are searched for.  The factory for command 'foo' is expected
        # to be named 'foo' in the module 'foo' in one of the packages
        # named here.  This list is searched from the left; an error
        # is raised if no named package provides the command being
        # searched for.  (Always access using get_command_packages().)
        self.command_packages: str | list[str] | None = None

        # 'script_name' and 'script_args' are usually set to sys.argv[0]
        # and sys.argv[1:], but they can be overridden when the caller is
        # not necessarily a setup script run from the command-line.
        self.script_name: str | os.PathLike[str] | None = None
        self.script_args: list[str] | None = None

        # 'command_options' is where we store command options between
        # parsing them (from config files, the command-line, etc.) and when
        # they are actually needed -- ie. when the command in question is
        # instantiated.  It is a dictionary of dictionaries of 2-tuples:
        #   command_options = { command_name : { option : (source, value) } }
        self.command_options: dict[str, dict[str, tuple[str, str]]] = {}

        # 'dist_files' is the list of (command, pyversion, file) that
        # have been created by any dist commands run so far. This is
        # filled regardless of whether the run is dry or not. pyversion
        # gives sysconfig.get_python_version() if the dist file is
        # specific to a Python version, 'any' if it is good for all
        # Python versions on the target platform, and '' for a source
        # file. pyversion should not be used to specify minimum or
        # maximum required Python versions; use the metainfo for that
        # instead.
        self.dist_files: list[tuple[str, str, str]] = []

        # These options are really the business of various commands, rather
        # than of the Distribution itself.  We provide aliases for them in
        # Distribution as a convenience to the developer.
        self.packages = None
        self.package_data: dict[str, list[str]] = {}
        self.package_dir = None
        self.py_modules = None
        self.libraries = None
        self.headers = None
        self.ext_modules = None
        self.ext_package = None
        self.include_dirs = None
        self.extra_path = None
        self.scripts = None
        self.data_files = None
        self.password = ''

        # And now initialize bookkeeping stuff that can't be supplied by
        # the caller at all.  'command_obj' maps command names to
        # Command instances -- that's how we enforce that every command
        # class is a singleton.
        self.command_obj: dict[str, Command] = {}

        # 'have_run' maps command names to boolean values; it keeps track
        # of whether we have actually run a particular command, to make it
        # cheap to "run" a command whenever we think we might need to -- if
        # it's already been done, no need for expensive filesystem
        # operations, we just check the 'have_run' dictionary and carry on.
        # It's only safe to query 'have_run' for a command class that has
        # been instantiated -- a false value will be inserted when the
        # command object is created, and replaced with a true value when
        # the command is successfully run.  Thus it's probably best to use
        # '.get()' rather than a straight lookup.
        self.have_run: dict[str, bool] = {}

        # Now we'll use the attrs dictionary (ultimately, keyword args from
        # the setup script) to possibly override any or all of these
        # distribution options.

        if attrs:
            # Pull out the set of command options and work on them
            # specifically.  Note that this order guarantees that aliased
            # command options will override any supplied redundantly
            # through the general options dictionary.
            options = attrs.get('options')
            if options is not None:
                del attrs['options']
                for command, cmd_options in options.items():
                    opt_dict = self.get_option_dict(command)
                    for opt, val in cmd_options.items():
                        opt_dict[opt] = ("setup script", val)

            if 'licence' in attrs:
                attrs['license'] = attrs['licence']
                del attrs['licence']
                msg = "'licence' distribution option is deprecated; use 'license'"
                warnings.warn(msg)

            # Now work on the rest of the attributes.  Any attribute that's
            # not already defined is invalid!
            for key, val in attrs.items():
                if hasattr(self.metadata, "set_" + key):
                    getattr(self.metadata, "set_" + key)(val)
                elif hasattr(self.metadata, key):
                    setattr(self.metadata, key, val)
                elif hasattr(self, key):
                    setattr(self, key, val)
                else:
                    msg = f"Unknown distribution option: {key!r}"
                    warnings.warn(msg)

        # no-user-cfg is handled before other command line args
        # because other args override the config files, and this
        # one is needed before we can load the config files.
        # If attrs['script_args'] wasn't passed, assume false.
        #
        # This also make sure we just look at the global options
        self.want_user_cfg = True

        if self.script_args is not None:
            # Coerce any possible iterable from attrs into a list
            self.script_args = list(self.script_args)
            for arg in self.script_args:
                if not arg.startswith('-'):
                    break
                if arg == '--no-user-cfg':
                    self.want_user_cfg = False
                    break

        self.finalize_options()

    def get_option_dict(self, command):
        """Get the option dictionary for a given command.  If that
        command's option dictionary hasn't been created yet, then create it
        and return the new dictionary; otherwise, return the existing
        option dictionary.
        """
        dict = self.command_options.get(command)
        if dict is None:
            dict = self.command_options[command] = {}
        return dict

    def dump_option_dicts(self, header=None, commands=None, indent: str = "") -> None:
        from pprint import pformat

        if commands is None:  # dump all command option dicts
            commands = sorted(self.command_options.keys())

        if header is not None:
            self.announce(indent + header)
            indent = indent + "  "

        if not commands:
            self.announce(indent + "no commands known yet")
            return

        for cmd_name in commands:
            opt_dict = self.command_options.get(cmd_name)
            if opt_dict is None:
                self.announce(indent + f"no option dict for '{cmd_name}' command")
            else:
                self.announce(indent + f"option dict for '{cmd_name}' command:")
                out = pformat(opt_dict)
                for line in out.split('\n'):
                    self.announce(indent + "  " + line)

    # -- Config file finding/parsing methods ---------------------------

    def find_config_files(self):
        """Find as many configuration files as should be processed for this
        platform, and return a list of filenames in the order in which they
        should be parsed.  The filenames returned are guaranteed to exist
        (modulo nasty race conditions).

        There are multiple possible config files:
        - distutils.cfg in the Distutils installation directory (i.e.
          where the top-level Distutils __inst__.py file lives)
        - a file in the user's home directory named .pydistutils.cfg
          on Unix and pydistutils.cfg on Windows/Mac; may be disabled
          with the ``--no-user-cfg`` option
        - setup.cfg in the current directory
        - a file named by an environment variable
        """
        check_environ()
        files = [str(path) for path in self._gen_paths() if os.path.isfile(path)]

        if DEBUG:
            self.announce("using config files: {}".format(', '.join(files)))

        return files

    def _gen_paths(self):
        # The system-wide Distutils config file
        sys_dir = pathlib.Path(sys.modules['distutils'].__file__).parent
        yield sys_dir / "distutils.cfg"

        # The per-user config file
        prefix = '.' * (os.name == 'posix')
        filename = prefix + 'pydistutils.cfg'
        if self.want_user_cfg:
            with contextlib.suppress(RuntimeError):
                yield pathlib.Path('~').expanduser() / filename

        # All platforms support local setup.cfg
        yield pathlib.Path('setup.cfg')

        # Additional config indicated in the environment
        with contextlib.suppress(TypeError):
            yield pathlib.Path(os.getenv("DIST_EXTRA_CONFIG"))

    def parse_config_files(self, filenames=None):  # noqa: C901
        from configparser import ConfigParser

        # Ignore install directory options if we have a venv
        if sys.prefix != sys.base_prefix:
            ignore_options = [
                'install-base',
                'install-platbase',
                'install-lib',
                'install-platlib',
                'install-purelib',
                'install-headers',
                'install-scripts',
                'install-data',
                'prefix',
                'exec-prefix',
                'home',
                'user',
                'root',
            ]
        else:
            ignore_options = []

        ignore_options = frozenset(ignore_options)

        if filenames is None:
            filenames = self.find_config_files()

        if DEBUG:
            self.announce("Distribution.parse_config_files():")

        parser = ConfigParser()
        for filename in filenames:
            if DEBUG:
                self.announce(f"  reading {filename}")
            parser.read(filename, encoding='utf-8')
            for section in parser.sections():
                options = parser.options(section)
                opt_dict = self.get_option_dict(section)

                for opt in options:
                    if opt != '__name__' and opt not in ignore_options:
                        val = parser.get(section, opt)
                        opt = opt.replace('-', '_')
                        opt_dict[opt] = (filename, val)

            # Make the ConfigParser forget everything (so we retain
            # the original filenames that options come from)
            parser.__init__()

        # If there was a "global" section in the config file, use it
        # to set Distribution options.

        if 'global' in self.command_options:
            for opt, (_src, val) in self.command_options['global'].items():
                alias = self.negative_opt.get(opt)
                try:
                    if alias:
                        setattr(self, alias, not strtobool(val))
                    elif opt in ('verbose', 'dry_run'):  # ugh!
                        setattr(self, opt, strtobool(val))
                    else:
                        setattr(self, opt, val)
                except ValueError as msg:
                    raise DistutilsOptionError(msg)

    # -- Command-line parsing methods ----------------------------------

    def parse_command_line(self):
        """Parse the setup script's command line, taken from the
        'script_args' instance attribute (which defaults to 'sys.argv[1:]'
        -- see 'setup()' in core.py).  This list is first processed for
        "global options" -- options that set attributes of the Distribution
        instance.  Then, it is alternately scanned for Distutils commands
        and options for that command.  Each new command terminates the
        options for the previous command.  The allowed options for a
        command are determined by the 'user_options' attribute of the
        command class -- thus, we have to be able to load command classes
        in order to parse the command line.  Any error in that 'options'
        attribute raises DistutilsGetoptError; any error on the
        command-line raises DistutilsArgError.  If no Distutils commands
        were found on the command line, raises DistutilsArgError.  Return
        true if command-line was successfully parsed and we should carry
        on with executing commands; false if no errors but we shouldn't
        execute commands (currently, this only happens if user asks for
        help).
        """
        #
        # We now have enough information to show the Macintosh dialog
        # that allows the user to interactively specify the "command line".
        #
        toplevel_options = self._get_toplevel_options()

        # We have to parse the command line a bit at a time -- global
        # options, then the first command, then its options, and so on --
        # because each command will be handled by a different class, and
        # the options that are valid for a particular class aren't known
        # until we have loaded the command class, which doesn't happen
        # until we know what the command is.

        self.commands = []
        parser = FancyGetopt(toplevel_options + self.display_options)
        parser.set_negative_aliases(self.negative_opt)
        parser.set_aliases({'licence': 'license'})
        args = parser.getopt(args=self.script_args, object=self)
        option_order = parser.get_option_order()
        logging.getLogger().setLevel(logging.WARN - 10 * self.verbose)

        # for display options we return immediately
        if self.handle_display_options(option_order):
            return
        while args:
            args = self._parse_command_opts(parser, args)
            if args is None:  # user asked for help (and got it)
                return

        # Handle the cases of --help as a "global" option, ie.
        # "setup.py --help" and "setup.py --help command ...".  For the
        # former, we show global options (--verbose, --dry-run, etc.)
        # and display-only options (--name, --version, etc.); for the
        # latter, we omit the display-only options and show help for
        # each command listed on the command line.
        if self.help:
            self._show_help(
                parser, display_options=len(self.commands) == 0, commands=self.commands
            )
            return

        # Oops, no commands found -- an end-user error
        if not self.commands:
            raise DistutilsArgError("no commands supplied")

        # All is well: return true
        return True

    def _get_toplevel_options(self):
        """Return the non-display options recognized at the top level.

        This includes options that are recognized *only* at the top
        level as well as options recognized for commands.
        """
        return self.global_options + [
            (
                "command-packages=",
                None,
                "list of packages that provide distutils commands",
            ),
        ]

    def _parse_command_opts(self, parser, args):  # noqa: C901
        """Parse the command-line options for a single command.
        'parser' must be a FancyGetopt instance; 'args' must be the list
        of arguments, starting with the current command (whose options
        we are about to parse).  Returns a new version of 'args' with
        the next command at the front of the list; will be the empty
        list if there are no more commands on the command line.  Returns
        None if the user asked for help on this command.
        """
        # late import because of mutual dependence between these modules
        from distutils.cmd import Command

        # Pull the current command from the head of the command line
        command = args[0]
        if not command_re.match(command):
            raise SystemExit(f"invalid command name '{command}'")
        self.commands.append(command)

        # Dig up the command class that implements this command, so we
        # 1) know that it's a valid command, and 2) know which options
        # it takes.
        try:
            cmd_class = self.get_command_class(command)
        except DistutilsModuleError as msg:
            raise DistutilsArgError(msg)

        # Require that the command class be derived from Command -- want
        # to be sure that the basic "command" interface is implemented.
        if not issubclass(cmd_class, Command):
            raise DistutilsClassError(
                f"command class {cmd_class} must subclass Command"
            )

        # Also make sure that the command object provides a list of its
        # known options.
        if not (
            hasattr(cmd_class, 'user_options')
            and isinstance(cmd_class.user_options, list)
        ):
            msg = (
                "command class %s must provide "
                "'user_options' attribute (a list of tuples)"
            )
            raise DistutilsClassError(msg % cmd_class)

        # If the command class has a list of negative alias options,
        # merge it in with the global negative aliases.
        negative_opt = self.negative_opt
        if hasattr(cmd_class, 'negative_opt'):
            negative_opt = negative_opt.copy()
            negative_opt.update(cmd_class.negative_opt)

        # Check for help_options in command class.  They have a different
        # format (tuple of four) so we need to preprocess them here.
        if hasattr(cmd_class, 'help_options') and isinstance(
            cmd_class.help_options, list
        ):
            help_options = fix_help_options(cmd_class.help_options)
        else:
            help_options = []

        # All commands support the global options too, just by adding
        # in 'global_options'.
        parser.set_option_table(
            self.global_options + cmd_class.user_options + help_options
        )
        parser.set_negative_aliases(negative_opt)
        (args, opts) = parser.getopt(args[1:])
        if hasattr(opts, 'help') and opts.help:
            self._show_help(parser, display_options=False, commands=[cmd_class])
            return

        if hasattr(cmd_class, 'help_options') and isinstance(
            cmd_class.help_options, list
        ):
            help_option_found = 0
            for help_option, _short, _desc, func in cmd_class.help_options:
                if hasattr(opts, parser.get_attr_name(help_option)):
                    help_option_found = 1
                    if callable(func):
                        func()
                    else:
                        raise DistutilsClassError(
                            f"invalid help function {func!r} for help option '{help_option}': "
                            "must be a callable object (function, etc.)"
                        )

            if help_option_found:
                return

        # Put the options from the command-line into their official
        # holding pen, the 'command_options' dictionary.
        opt_dict = self.get_option_dict(command)
        for name, value in vars(opts).items():
            opt_dict[name] = ("command line", value)

        return args

    def finalize_options(self) -> None:
        """Set final values for all the options on the Distribution
        instance, analogous to the .finalize_options() method of Command
        objects.
        """
        for attr in ('keywords', 'platforms'):
            value = getattr(self.metadata, attr)
            if value is None:
                continue
            if isinstance(value, str):
                value = [elm.strip() for elm in value.split(',')]
                setattr(self.metadata, attr, value)

    def _show_help(
        self, parser, global_options=True, display_options=True, commands: Iterable = ()
    ):
        """Show help for the setup script command-line in the form of
        several lists of command-line options.  'parser' should be a
        FancyGetopt instance; do not expect it to be returned in the
        same state, as its option table will be reset to make it
        generate the correct help text.

        If 'global_options' is true, lists the global options:
        --verbose, --dry-run, etc.  If 'display_options' is true, lists
        the "display-only" options: --name, --version, etc.  Finally,
        lists per-command help for every command name or command class
        in 'commands'.
        """
        # late import because of mutual dependence between these modules
        from distutils.cmd import Command
        from distutils.core import gen_usage

        if global_options:
            if display_options:
                options = self._get_toplevel_options()
            else:
                options = self.global_options
            parser.set_option_table(options)
            parser.print_help(self.common_usage + "\nGlobal options:")
            print()

        if display_options:
            parser.set_option_table(self.display_options)
            parser.print_help(
                "Information display options (just display information, ignore any commands)"
            )
            print()

        for command in commands:
            if isinstance(command, type) and issubclass(command, Command):
                klass = command
            else:
                klass = self.get_command_class(command)
            if hasattr(klass, 'help_options') and isinstance(klass.help_options, list):
                parser.set_option_table(
                    klass.user_options + fix_help_options(klass.help_options)
                )
            else:
                parser.set_option_table(klass.user_options)
            parser.print_help(f"Options for '{klass.__name__}' command:")
            print()

        print(gen_usage(self.script_name))

    def handle_display_options(self, option_order):
        """If there were any non-global "display-only" options
        (--help-commands or the metadata display options) on the command
        line, display the requested info and return true; else return
        false.
        """
        from distutils.core import gen_usage

        # User just wants a list of commands -- we'll print it out and stop
        # processing now (ie. if they ran "setup --help-commands foo bar",
        # we ignore "foo bar").
        if self.help_commands:
            self.print_commands()
            print()
            print(gen_usage(self.script_name))
            return 1

        # If user supplied any of the "display metadata" options, then
        # display that metadata in the order in which the user supplied the
        # metadata options.
        any_display_options = 0
        is_display_option = set()
        for option in self.display_options:
            is_display_option.add(option[0])

        for opt, val in option_order:
            if val and opt in is_display_option:
                opt = translate_longopt(opt)
                value = getattr(self.metadata, "get_" + opt)()
                if opt in ('keywords', 'platforms'):
                    print(','.join(value))
                elif opt in ('classifiers', 'provides', 'requires', 'obsoletes'):
                    print('\n'.join(value))
                else:
                    print(value)
                any_display_options = 1

        return any_display_options

    def print_command_list(self, commands, header, max_length) -> None:
        """Print a subset of the list of all commands -- used by
        'print_commands()'.
        """
        print(header + ":")

        for cmd in commands:
            klass = self.cmdclass.get(cmd)
            if not klass:
                klass = self.get_command_class(cmd)
            try:
                description = klass.description
            except AttributeError:
                description = "(no description available)"

            print(f"  {cmd:<{max_length}}  {description}")

    def print_commands(self) -> None:
        """Print out a help message listing all available commands with a
        description of each.  The list is divided into "standard commands"
        (listed in distutils.command.__all__) and "extra commands"
        (mentioned in self.cmdclass, but not a standard command).  The
        descriptions come from the command class attribute
        'description'.
        """
        import distutils.command

        std_commands = distutils.command.__all__
        is_std = set(std_commands)

        extra_commands = [cmd for cmd in self.cmdclass.keys() if cmd not in is_std]

        max_length = 0
        for cmd in std_commands + extra_commands:
            if len(cmd) > max_length:
                max_length = len(cmd)

        self.print_command_list(std_commands, "Standard commands", max_length)
        if extra_commands:
            print()
            self.print_command_list(extra_commands, "Extra commands", max_length)

    def get_command_list(self):
        """Get a list of (command, description) tuples.
        The list is divided into "standard commands" (listed in
        distutils.command.__all__) and "extra commands" (mentioned in
        self.cmdclass, but not a standard command).  The descriptions come
        from the command class attribute 'description'.
        """
        # Currently this is only used on Mac OS, for the Mac-only GUI
        # Distutils interface (by Jack Jansen)
        import distutils.command

        std_commands = distutils.command.__all__
        is_std = set(std_commands)

        extra_commands = [cmd for cmd in self.cmdclass.keys() if cmd not in is_std]

        rv = []
        for cmd in std_commands + extra_commands:
            klass = self.cmdclass.get(cmd)
            if not klass:
                klass = self.get_command_class(cmd)
            try:
                description = klass.description
            except AttributeError:
                description = "(no description available)"
            rv.append((cmd, description))
        return rv

    # -- Command class/object methods ----------------------------------

    def get_command_packages(self):
        """Return a list of packages from which commands are loaded."""
        pkgs = self.command_packages
        if not isinstance(pkgs, list):
            if pkgs is None:
                pkgs = ''
            pkgs = [pkg.strip() for pkg in pkgs.split(',') if pkg != '']
            if "distutils.command" not in pkgs:
                pkgs.insert(0, "distutils.command")
            self.command_packages = pkgs
        return pkgs

    def get_command_class(self, command: str) -> type[Command]:
        """Return the class that implements the Distutils command named by
        'command'.  First we check the 'cmdclass' dictionary; if the
        command is mentioned there, we fetch the class object from the
        dictionary and return it.  Otherwise we load the command module
        ("distutils.command." + command) and fetch the command class from
        the module.  The loaded class is also stored in 'cmdclass'
        to speed future calls to 'get_command_class()'.

        Raises DistutilsModuleError if the expected module could not be
        found, or if that module does not define the expected class.
        """
        klass = self.cmdclass.get(command)
        if klass:
            return klass

        for pkgname in self.get_command_packages():
            module_name = f"{pkgname}.{command}"
            klass_name = command

            try:
                __import__(module_name)
                module = sys.modules[module_name]
            except ImportError:
                continue

            try:
                klass = getattr(module, klass_name)
            except AttributeError:
                raise DistutilsModuleError(
                    f"invalid command '{command}' (no class '{klass_name}' in module '{module_name}')"
                )

            self.cmdclass[command] = klass
            return klass

        raise DistutilsModuleError(f"invalid command '{command}'")

    @overload
    def get_command_obj(
        self, command: str, create: Literal[True] = True
    ) -> Command: ...
    @overload
    def get_command_obj(
        self, command: str, create: Literal[False]
    ) -> Command | None: ...
    def get_command_obj(self, command: str, create: bool = True) -> Command | None:
        """Return the command object for 'command'.  Normally this object
        is cached on a previous call to 'get_command_obj()'; if no command
        object for 'command' is in the cache, then we either create and
        return it (if 'create' is true) or return None.
        """
        cmd_obj = self.command_obj.get(command)
        if not cmd_obj and create:
            if DEBUG:
                self.announce(
                    "Distribution.get_command_obj(): "
                    f"creating '{command}' command object"
                )

            klass = self.get_command_class(command)
            cmd_obj = self.command_obj[command] = klass(self)
            self.have_run[command] = False

            # Set any options that were supplied in config files
            # or on the command line.  (NB. support for error
            # reporting is lame here: any errors aren't reported
            # until 'finalize_options()' is called, which means
            # we won't report the source of the error.)
            options = self.command_options.get(command)
            if options:
                self._set_command_options(cmd_obj, options)

        return cmd_obj

    def _set_command_options(self, command_obj, option_dict=None):  # noqa: C901
        """Set the options for 'command_obj' from 'option_dict'.  Basically
        this means copying elements of a dictionary ('option_dict') to
        attributes of an instance ('command').

        'command_obj' must be a Command instance.  If 'option_dict' is not
        supplied, uses the standard option dictionary for this command
        (from 'self.command_options').
        """
        command_name = command_obj.get_command_name()
        if option_dict is None:
            option_dict = self.get_option_dict(command_name)

        if DEBUG:
            self.announce(f"  setting options for '{command_name}' command:")
        for option, (source, value) in option_dict.items():
            if DEBUG:
                self.announce(f"    {option} = {value} (from {source})")
            try:
                bool_opts = [translate_longopt(o) for o in command_obj.boolean_options]
            except AttributeError:
                bool_opts = []
            try:
                neg_opt = command_obj.negative_opt
            except AttributeError:
                neg_opt = {}

            try:
                is_string = isinstance(value, str)
                if option in neg_opt and is_string:
                    setattr(command_obj, neg_opt[option], not strtobool(value))
                elif option in bool_opts and is_string:
                    setattr(command_obj, option, strtobool(value))
                elif hasattr(command_obj, option):
                    setattr(command_obj, option, value)
                else:
                    raise DistutilsOptionError(
                        f"error in {source}: command '{command_name}' has no such option '{option}'"
                    )
            except ValueError as msg:
                raise DistutilsOptionError(msg)

    @overload
    def reinitialize_command(
        self, command: str, reinit_subcommands: bool = False
    ) -> Command: ...
    @overload
    def reinitialize_command(
        self, command: _CommandT, reinit_subcommands: bool = False
    ) -> _CommandT: ...
    def reinitialize_command(
        self, command: str | Command, reinit_subcommands=False
    ) -> Command:
        """Reinitializes a command to the state it was in when first
        returned by 'get_command_obj()': ie., initialized but not yet
        finalized.  This provides the opportunity to sneak option
        values in programmatically, overriding or supplementing
        user-supplied values from the config files and command line.
        You'll have to re-finalize the command object (by calling
        'finalize_options()' or 'ensure_finalized()') before using it for
        real.

        'command' should be a command name (string) or command object.  If
        'reinit_subcommands' is true, also reinitializes the command's
        sub-commands, as declared by the 'sub_commands' class attribute (if
        it has one).  See the "install" command for an example.  Only
        reinitializes the sub-commands that actually matter, ie. those
        whose test predicates return true.

        Returns the reinitialized command object.
        """
        from distutils.cmd import Command

        if not isinstance(command, Command):
            command_name = command
            command = self.get_command_obj(command_name)
        else:
            command_name = command.get_command_name()

        if not command.finalized:
            return command
        command.initialize_options()
        command.finalized = False
        self.have_run[command_name] = False
        self._set_command_options(command)

        if reinit_subcommands:
            for sub in command.get_sub_commands():
                self.reinitialize_command(sub, reinit_subcommands)

        return command

    # -- Methods that operate on the Distribution ----------------------

    def announce(self, msg, level: int = logging.INFO) -> None:
        log.log(level, msg)

    def run_commands(self) -> None:
        """Run each command that was seen on the setup script command line.
        Uses the list of commands found and cache of command objects
        created by 'get_command_obj()'.
        """
        for cmd in self.commands:
            self.run_command(cmd)

    # -- Methods that operate on its Commands --------------------------

    def run_command(self, command: str) -> None:
        """Do whatever it takes to run a command (including nothing at all,
        if the command has already been run).  Specifically: if we have
        already created and run the command named by 'command', return
        silently without doing anything.  If the command named by 'command'
        doesn't even have a command object yet, create one.  Then invoke
        'run()' on that command object (or an existing one).
        """
        # Already been here, done that? then return silently.
        if self.have_run.get(command):
            return

        log.info("running %s", command)
        cmd_obj = self.get_command_obj(command)
        cmd_obj.ensure_finalized()
        cmd_obj.run()
        self.have_run[command] = True

    # -- Distribution query methods ------------------------------------

    def has_pure_modules(self) -> bool:
        return len(self.packages or self.py_modules or []) > 0

    def has_ext_modules(self) -> bool:
        return self.ext_modules and len(self.ext_modules) > 0

    def has_c_libraries(self) -> bool:
        return self.libraries and len(self.libraries) > 0

    def has_modules(self) -> bool:
        return self.has_pure_modules() or self.has_ext_modules()

    def has_headers(self) -> bool:
        return self.headers and len(self.headers) > 0

    def has_scripts(self) -> bool:
        return self.scripts and len(self.scripts) > 0

    def has_data_files(self) -> bool:
        return self.data_files and len(self.data_files) > 0

    def is_pure(self) -> bool:
        return (
            self.has_pure_modules()
            and not self.has_ext_modules()
            and not self.has_c_libraries()
        )

    # -- Metadata query methods ----------------------------------------

    # If you're looking for 'get_name()', 'get_version()', and so forth,
    # they are defined in a sneaky way: the constructor binds self.get_XXX
    # to self.metadata.get_XXX.  The actual code is in the
    # DistributionMetadata class, below.
    if TYPE_CHECKING:
        # Unfortunately this means we need to specify them manually or not expose statically
        def _(self) -> None:
            self.get_name = self.metadata.get_name
            self.get_version = self.metadata.get_version
            self.get_fullname = self.metadata.get_fullname
            self.get_author = self.metadata.get_author
            self.get_author_email = self.metadata.get_author_email
            self.get_maintainer = self.metadata.get_maintainer
            self.get_maintainer_email = self.metadata.get_maintainer_email
            self.get_contact = self.metadata.get_contact
            self.get_contact_email = self.metadata.get_contact_email
            self.get_url = self.metadata.get_url
            self.get_license = self.metadata.get_license
            self.get_licence = self.metadata.get_licence
            self.get_description = self.metadata.get_description
            self.get_long_description = self.metadata.get_long_description
            self.get_keywords = self.metadata.get_keywords
            self.get_platforms = self.metadata.get_platforms
            self.get_classifiers = self.metadata.get_classifiers
            self.get_download_url = self.metadata.get_download_url
            self.get_requires = self.metadata.get_requires
            self.get_provides = self.metadata.get_provides
            self.get_obsoletes = self.metadata.get_obsoletes

        # Default attributes generated in __init__ from self.display_option_names
        help_commands: bool
        name: str | Literal[False]
        version: str | Literal[False]
        fullname: str | Literal[False]
        author: str | Literal[False]
        author_email: str | Literal[False]
        maintainer: str | Literal[False]
        maintainer_email: str | Literal[False]
        contact: str | Literal[False]
        contact_email: str | Literal[False]
        url: str | Literal[False]
        license: str | Literal[False]
        licence: str | Literal[False]
        description: str | Literal[False]
        long_description: str | Literal[False]
        platforms: str | list[str] | Literal[False]
        classifiers: str | list[str] | Literal[False]
        keywords: str | list[str] | Literal[False]
        provides: list[str] | Literal[False]
        requires: list[str] | Literal[False]
        obsoletes: list[str] | Literal[False]


class DistributionMetadata:
    """Dummy class to hold the distribution meta-data: name, version,
    author, and so forth.
    """

    _METHOD_BASENAMES = (
        "name",
        "version",
        "author",
        "author_email",
        "maintainer",
        "maintainer_email",
        "url",
        "license",
        "description",
        "long_description",
        "keywords",
        "platforms",
        "fullname",
        "contact",
        "contact_email",
        "classifiers",
        "download_url",
        # PEP 314
        "provides",
        "requires",
        "obsoletes",
    )

    def __init__(
        self, path: str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None
    ) -> None:
        if path is not None:
            self.read_pkg_file(open(path))
        else:
            self.name: str | None = None
            self.version: str | None = None
            self.author: str | None = None
            self.author_email: str | None = None
            self.maintainer: str | None = None
            self.maintainer_email: str | None = None
            self.url: str | None = None
            self.license: str | None = None
            self.description: str | None = None
            self.long_description: str | None = None
            self.keywords: str | list[str] | None = None
            self.platforms: str | list[str] | None = None
            self.classifiers: str | list[str] | None = None
            self.download_url: str | None = None
            # PEP 314
            self.provides: str | list[str] | None = None
            self.requires: str | list[str] | None = None
            self.obsoletes: str | list[str] | None = None

    def read_pkg_file(self, file: IO[str]) -> None:
        """Reads the metadata values from a file object."""
        msg = message_from_file(file)

        def _read_field(name: str) -> str | None:
            value = msg[name]
            if value and value != "UNKNOWN":
                return value
            return None

        def _read_list(name):
            values = msg.get_all(name, None)
            if values == []:
                return None
            return values

        metadata_version = msg['metadata-version']
        self.name = _read_field('name')
        self.version = _read_field('version')
        self.description = _read_field('summary')
        # we are filling author only.
        self.author = _read_field('author')
        self.maintainer = None
        self.author_email = _read_field('author-email')
        self.maintainer_email = None
        self.url = _read_field('home-page')
        self.license = _read_field('license')

        if 'download-url' in msg:
            self.download_url = _read_field('download-url')
        else:
            self.download_url = None

        self.long_description = _read_field('description')
        self.description = _read_field('summary')

        if 'keywords' in msg:
            self.keywords = _read_field('keywords').split(',')

        self.platforms = _read_list('platform')
        self.classifiers = _read_list('classifier')

        # PEP 314 - these fields only exist in 1.1
        if metadata_version == '1.1':
            self.requires = _read_list('requires')
            self.provides = _read_list('provides')
            self.obsoletes = _read_list('obsoletes')
        else:
            self.requires = None
            self.provides = None
            self.obsoletes = None

    def write_pkg_info(self, base_dir: str | os.PathLike[str]) -> None:
        """Write the PKG-INFO file into the release tree."""
        with open(
            os.path.join(base_dir, 'PKG-INFO'), 'w', encoding='UTF-8'
        ) as pkg_info:
            self.write_pkg_file(pkg_info)

    def write_pkg_file(self, file: SupportsWrite[str]) -> None:
        """Write the PKG-INFO format data to a file object."""
        version = '1.0'
        if (
            self.provides
            or self.requires
            or self.obsoletes
            or self.classifiers
            or self.download_url
        ):
            version = '1.1'

        # required fields
        file.write(f'Metadata-Version: {version}\n')
        file.write(f'Name: {self.get_name()}\n')
        file.write(f'Version: {self.get_version()}\n')

        def maybe_write(header, val):
            if val:
                file.write(f"{header}: {val}\n")

        # optional fields
        maybe_write("Summary", self.get_description())
        maybe_write("Home-page", self.get_url())
        maybe_write("Author", self.get_contact())
        maybe_write("Author-email", self.get_contact_email())
        maybe_write("License", self.get_license())
        maybe_write("Download-URL", self.download_url)
        maybe_write("Description", rfc822_escape(self.get_long_description() or ""))
        maybe_write("Keywords", ",".join(self.get_keywords()))

        self._write_list(file, 'Platform', self.get_platforms())
        self._write_list(file, 'Classifier', self.get_classifiers())

        # PEP 314
        self._write_list(file, 'Requires', self.get_requires())
        self._write_list(file, 'Provides', self.get_provides())
        self._write_list(file, 'Obsoletes', self.get_obsoletes())

    def _write_list(self, file, name, values):
        values = values or []
        for value in values:
            file.write(f'{name}: {value}\n')

    # -- Metadata query methods ----------------------------------------

    def get_name(self) -> str:
        return self.name or "UNKNOWN"

    def get_version(self) -> str:
        return self.version or "0.0.0"

    def get_fullname(self) -> str:
        return self._fullname(self.get_name(), self.get_version())

    @staticmethod
    def _fullname(name: str, version: str) -> str:
        """
        >>> DistributionMetadata._fullname('setup.tools', '1.0-2')
        'setup_tools-1.0.post2'
        >>> DistributionMetadata._fullname('setup-tools', '1.2post2')
        'setup_tools-1.2.post2'
        >>> DistributionMetadata._fullname('setup-tools', '1.0-r2')
        'setup_tools-1.0.post2'
        >>> DistributionMetadata._fullname('setup.tools', '1.0.post')
        'setup_tools-1.0.post0'
        >>> DistributionMetadata._fullname('setup.tools', '1.0+ubuntu-1')
        'setup_tools-1.0+ubuntu.1'
        """
        return "{}-{}".format(
            canonicalize_name(name).replace('-', '_'),
            canonicalize_version(version, strip_trailing_zero=False),
        )

    def get_author(self) -> str | None:
        return self.author

    def get_author_email(self) -> str | None:
        return self.author_email

    def get_maintainer(self) -> str | None:
        return self.maintainer

    def get_maintainer_email(self) -> str | None:
        return self.maintainer_email

    def get_contact(self) -> str | None:
        return self.maintainer or self.author

    def get_contact_email(self) -> str | None:
        return self.maintainer_email or self.author_email

    def get_url(self) -> str | None:
        return self.url

    def get_license(self) -> str | None:
        return self.license

    get_licence = get_license

    def get_description(self) -> str | None:
        return self.description

    def get_long_description(self) -> str | None:
        return self.long_description

    def get_keywords(self) -> str | list[str]:
        return self.keywords or []

    def set_keywords(self, value: str | Iterable[str]) -> None:
        self.keywords = _ensure_list(value, 'keywords')

    def get_platforms(self) -> str | list[str] | None:
        return self.platforms

    def set_platforms(self, value: str | Iterable[str]) -> None:
        self.platforms = _ensure_list(value, 'platforms')

    def get_classifiers(self) -> str | list[str]:
        return self.classifiers or []

    def set_classifiers(self, value: str | Iterable[str]) -> None:
        self.classifiers = _ensure_list(value, 'classifiers')

    def get_download_url(self) -> str | None:
        return self.download_url

    # PEP 314
    def get_requires(self) -> str | list[str]:
        return self.requires or []

    def set_requires(self, value: Iterable[str]) -> None:
        import distutils.versionpredicate

        for v in value:
            distutils.versionpredicate.VersionPredicate(v)
        self.requires = list(value)

    def get_provides(self) -> str | list[str]:
        return self.provides or []

    def set_provides(self, value: Iterable[str]) -> None:
        value = [v.strip() for v in value]
        for v in value:
            import distutils.versionpredicate

            distutils.versionpredicate.split_provision(v)
        self.provides = value

    def get_obsoletes(self) -> str | list[str]:
        return self.obsoletes or []

    def set_obsoletes(self, value: Iterable[str]) -> None:
        import distutils.versionpredicate

        for v in value:
            distutils.versionpredicate.VersionPredicate(v)
        self.obsoletes = list(value)


def fix_help_options(options):
    """Convert a 4-tuple 'help_options' list as found in various command
    classes to the 3-tuple form required by FancyGetopt.
    """
    return [opt[0:3] for opt in options]

# === NexusCore/openenv\Lib\site-packages\trio\_dtls.py ===
# Implementation of DTLS 1.2, using pyopenssl
# https://datatracker.ietf.org/doc/html/rfc6347
#
# OpenSSL's APIs for DTLS are extremely awkward and limited, which forces us to jump
# through a *lot* of hoops and implement important chunks of the protocol ourselves.
# Hopefully they fix this before implementing DTLS 1.3, because it's a very different
# protocol, and it's probably impossible to pull tricks like we do here.

from __future__ import annotations

import contextlib
import enum
import errno
import hmac
import os
import struct
import warnings
import weakref
from itertools import count
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
    Union,
)
from weakref import ReferenceType, WeakValueDictionary

import attrs

import trio

from ._util import NoPublicConstructor, final

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Iterator
    from types import TracebackType

    # See DTLSEndpoint.__init__ for why this is imported here
    from OpenSSL import SSL  # noqa: TC004
    from typing_extensions import Self, TypeAlias, TypeVarTuple, Unpack

    from trio._socket import AddressFormat
    from trio.socket import SocketType

    PosArgsT = TypeVarTuple("PosArgsT")

MAX_UDP_PACKET_SIZE = 65527


def packet_header_overhead(sock: SocketType) -> int:
    if sock.family == trio.socket.AF_INET:
        return 28
    else:
        return 48


def worst_case_mtu(sock: SocketType) -> int:
    if sock.family == trio.socket.AF_INET:
        return 576 - packet_header_overhead(sock)
    else:
        return 1280 - packet_header_overhead(sock)  # TODO: test this line


def best_guess_mtu(sock: SocketType) -> int:
    return 1500 - packet_header_overhead(sock)


# There are a bunch of different RFCs that define these codes, so for a
# comprehensive collection look here:
# https://www.iana.org/assignments/tls-parameters/tls-parameters.xhtml
class ContentType(enum.IntEnum):
    change_cipher_spec = 20
    alert = 21
    handshake = 22
    application_data = 23
    heartbeat = 24


class HandshakeType(enum.IntEnum):
    hello_request = 0
    client_hello = 1
    server_hello = 2
    hello_verify_request = 3
    new_session_ticket = 4
    end_of_early_data = 4
    encrypted_extensions = 8
    certificate = 11
    server_key_exchange = 12
    certificate_request = 13
    server_hello_done = 14
    certificate_verify = 15
    client_key_exchange = 16
    finished = 20
    certificate_url = 21
    certificate_status = 22
    supplemental_data = 23
    key_update = 24
    compressed_certificate = 25
    ekt_key = 26
    message_hash = 254


class ProtocolVersion:
    DTLS10 = bytes([254, 255])
    DTLS12 = bytes([254, 253])


EPOCH_MASK = 0xFFFF << (6 * 8)


# Conventions:
# - All functions that handle network data end in _untrusted.
# - All functions end in _untrusted MUST make sure that bad data from the
#   network cannot *only* cause BadPacket to be raised. No IndexError or
#   struct.error or whatever.
class BadPacket(Exception):
    pass


# This checks that the DTLS 'epoch' field is 0, which is true iff we're in the
# initial handshake. It doesn't check the ContentType, because not all
# handshake messages have ContentType==handshake -- for example,
# ChangeCipherSpec is used during the handshake but has its own ContentType.
#
# Cannot fail.
def part_of_handshake_untrusted(packet: bytes) -> bool:
    # If the packet is too short, then slicing will successfully return a
    # short string, which will necessarily fail to match.
    return packet[3:5] == b"\x00\x00"


# Cannot fail
def is_client_hello_untrusted(packet: bytes) -> bool:
    try:
        return (
            packet[0] == ContentType.handshake
            and packet[13] == HandshakeType.client_hello
        )
    except IndexError:
        # Invalid DTLS record
        return False


# DTLS records are:
# - 1 byte content type
# - 2 bytes version
# - 8 bytes epoch+seqno
#    Technically this is 2 bytes epoch then 6 bytes seqno, but we treat it as
#    a single 8-byte integer, where epoch changes are represented as jumping
#    forward by 2**(6*8).
# - 2 bytes payload length (unsigned big-endian)
# - payload
RECORD_HEADER = struct.Struct("!B2sQH")


def to_hex(data: bytes) -> str:  # pragma: no cover
    return data.hex()


@attrs.frozen
class Record:
    content_type: int
    version: bytes = attrs.field(repr=to_hex)
    epoch_seqno: int
    payload: bytes = attrs.field(repr=to_hex)


def records_untrusted(packet: bytes) -> Iterator[Record]:
    i = 0
    while i < len(packet):
        try:
            ct, version, epoch_seqno, payload_len = RECORD_HEADER.unpack_from(packet, i)
        # Marked as no-cover because at time of writing, this code is unreachable
        # (records_untrusted only gets called on packets that are either trusted or that
        # have passed is_client_hello_untrusted, which filters out short packets)
        except struct.error as exc:  # pragma: no cover
            raise BadPacket("invalid record header") from exc
        i += RECORD_HEADER.size
        payload = packet[i : i + payload_len]
        if len(payload) != payload_len:
            raise BadPacket("short record")
        i += payload_len
        yield Record(ct, version, epoch_seqno, payload)


def encode_record(record: Record) -> bytes:
    header = RECORD_HEADER.pack(
        record.content_type,
        record.version,
        record.epoch_seqno,
        len(record.payload),
    )
    return header + record.payload


# Handshake messages are:
# - 1 byte message type
# - 3 bytes total message length
# - 2 bytes message sequence number
# - 3 bytes fragment offset
# - 3 bytes fragment length
HANDSHAKE_MESSAGE_HEADER = struct.Struct("!B3sH3s3s")


@attrs.frozen
class HandshakeFragment:
    msg_type: int
    msg_len: int
    msg_seq: int
    frag_offset: int
    frag_len: int
    frag: bytes = attrs.field(repr=to_hex)


def decode_handshake_fragment_untrusted(payload: bytes) -> HandshakeFragment:
    # Raises BadPacket if decoding fails
    try:
        (
            msg_type,
            msg_len_bytes,
            msg_seq,
            frag_offset_bytes,
            frag_len_bytes,
        ) = HANDSHAKE_MESSAGE_HEADER.unpack_from(payload)
    except struct.error as exc:  # TODO: test this line
        raise BadPacket("bad handshake message header") from exc
    # 'struct' doesn't have built-in support for 24-bit integers, so we
    # have to do it by hand. These can't fail.
    msg_len = int.from_bytes(msg_len_bytes, "big")
    frag_offset = int.from_bytes(frag_offset_bytes, "big")
    frag_len = int.from_bytes(frag_len_bytes, "big")
    frag = payload[HANDSHAKE_MESSAGE_HEADER.size :]
    if len(frag) != frag_len:
        raise BadPacket("handshake fragment length doesn't match record length")
    return HandshakeFragment(
        msg_type,
        msg_len,
        msg_seq,
        frag_offset,
        frag_len,
        frag,
    )


def encode_handshake_fragment(hsf: HandshakeFragment) -> bytes:
    hs_header = HANDSHAKE_MESSAGE_HEADER.pack(
        hsf.msg_type,
        hsf.msg_len.to_bytes(3, "big"),
        hsf.msg_seq,
        hsf.frag_offset.to_bytes(3, "big"),
        hsf.frag_len.to_bytes(3, "big"),
    )
    return hs_header + hsf.frag


def decode_client_hello_untrusted(packet: bytes) -> tuple[int, bytes, bytes]:
    # Raises BadPacket if parsing fails
    # Returns (record epoch_seqno, cookie from the packet, data that should be
    # hashed into cookie)
    try:
        # ClientHello has to be the first record in the packet
        record = next(records_untrusted(packet))
        # no-cover because at time of writing, this is unreachable:
        # decode_client_hello_untrusted is only called on packets that have passed
        # is_client_hello_untrusted, which confirms the content type.
        if record.content_type != ContentType.handshake:  # pragma: no cover
            raise BadPacket("not a handshake record")
        fragment = decode_handshake_fragment_untrusted(record.payload)
        if fragment.msg_type != HandshakeType.client_hello:
            raise BadPacket("not a ClientHello")
        # ClientHello can't be fragmented, because reassembly requires holding
        # per-connection state, and we refuse to allocate per-connection state
        # until after we get a valid ClientHello.
        if fragment.frag_offset != 0:
            raise BadPacket("fragmented ClientHello")
        if fragment.frag_len != fragment.msg_len:
            raise BadPacket("fragmented ClientHello")

        # As per RFC 6347:
        #
        #   When responding to a HelloVerifyRequest, the client MUST use the
        #   same parameter values (version, random, session_id, cipher_suites,
        #   compression_method) as it did in the original ClientHello.  The
        #   server SHOULD use those values to generate its cookie and verify that
        #   they are correct upon cookie receipt.
        #
        # However, the record-layer framing can and will change (e.g. the
        # second ClientHello will have a new record-layer sequence number). So
        # we need to pull out the handshake message alone, discarding the
        # record-layer stuff, and then we're going to hash all of it *except*
        # the cookie.

        body = fragment.frag
        # ClientHello is:
        #
        # - 2 bytes client_version
        # - 32 bytes random
        # - 1 byte session_id length
        # - session_id
        # - 1 byte cookie length
        # - cookie
        # - everything else
        #
        # So to find the cookie, so we need to figure out how long the
        # session_id is and skip past it.
        session_id_len = body[2 + 32]
        cookie_len_offset = 2 + 32 + 1 + session_id_len
        cookie_len = body[cookie_len_offset]

        cookie_start = cookie_len_offset + 1
        cookie_end = cookie_start + cookie_len

        before_cookie = body[:cookie_len_offset]
        cookie = body[cookie_start:cookie_end]
        after_cookie = body[cookie_end:]

        if len(cookie) != cookie_len:
            raise BadPacket("short cookie")
        return (record.epoch_seqno, cookie, before_cookie + after_cookie)

    except (struct.error, IndexError) as exc:
        raise BadPacket("bad ClientHello") from exc


@attrs.frozen
class HandshakeMessage:
    record_version: bytes = attrs.field(repr=to_hex)
    msg_type: HandshakeType
    msg_seq: int
    body: bytearray = attrs.field(repr=to_hex)


# ChangeCipherSpec is part of the handshake, but it's not a "handshake
# message" and can't be fragmented the same way. Sigh.
@attrs.frozen
class PseudoHandshakeMessage:
    record_version: bytes = attrs.field(repr=to_hex)
    content_type: int
    payload: bytes = attrs.field(repr=to_hex)


# The final record in a handshake is Finished, which is encrypted, can't be fragmented
# (at least by us), and keeps its record number (because it's in a new epoch). So we
# just pass it through unchanged. (Fortunately, the payload is only a single hash value,
# so the largest it will ever be is 64 bytes for a 512-bit hash. Which is small enough
# that it never requires fragmenting to fit into a UDP packet.
@attrs.frozen
class OpaqueHandshakeMessage:
    record: Record


_AnyHandshakeMessage: TypeAlias = Union[
    HandshakeMessage,
    PseudoHandshakeMessage,
    OpaqueHandshakeMessage,
]


# This takes a raw outgoing handshake volley that openssl generated, and
# reconstructs the handshake messages inside it, so that we can repack them
# into records while retransmitting. So the data ought to be well-behaved --
# it's not coming from the network.
def decode_volley_trusted(
    volley: bytes,
) -> list[_AnyHandshakeMessage]:
    messages: list[_AnyHandshakeMessage] = []
    messages_by_seq = {}
    for record in records_untrusted(volley):
        # ChangeCipherSpec isn't a handshake message, so it can't be fragmented.
        # Handshake messages with epoch > 0 are encrypted, so we can't fragment them
        # either. Fortunately, ChangeCipherSpec has a 1 byte payload, and the only
        # encrypted handshake message is Finished, whose payload is a single hash value
        # -- so 32 bytes for SHA-256, 64 for SHA-512, etc. Neither is going to be so
        # large that it has to be fragmented to fit into a single packet.
        if record.epoch_seqno & EPOCH_MASK:
            messages.append(OpaqueHandshakeMessage(record))
        elif record.content_type in (ContentType.change_cipher_spec, ContentType.alert):
            messages.append(
                PseudoHandshakeMessage(
                    record.version,
                    record.content_type,
                    record.payload,
                ),
            )
        else:
            assert record.content_type == ContentType.handshake
            fragment = decode_handshake_fragment_untrusted(record.payload)
            msg_type = HandshakeType(fragment.msg_type)
            if fragment.msg_seq not in messages_by_seq:
                msg = HandshakeMessage(
                    record.version,
                    msg_type,
                    fragment.msg_seq,
                    bytearray(fragment.msg_len),
                )
                messages.append(msg)
                messages_by_seq[fragment.msg_seq] = msg
            else:
                msg = messages_by_seq[fragment.msg_seq]
            assert msg.msg_type == fragment.msg_type
            assert msg.msg_seq == fragment.msg_seq
            assert len(msg.body) == fragment.msg_len

            msg.body[
                fragment.frag_offset : fragment.frag_offset + fragment.frag_len
            ] = fragment.frag

    return messages


class RecordEncoder:
    def __init__(self) -> None:
        self._record_seq = count()

    def set_first_record_number(self, n: int) -> None:
        self._record_seq = count(n)

    def encode_volley(
        self,
        messages: Iterable[_AnyHandshakeMessage],
        mtu: int,
    ) -> list[bytearray]:
        packets = []
        packet = bytearray()
        for message in messages:
            if isinstance(message, OpaqueHandshakeMessage):
                encoded = encode_record(message.record)
                if mtu - len(packet) - len(encoded) <= 0:  # TODO: test this line
                    packets.append(packet)
                    packet = bytearray()
                packet += encoded
                assert len(packet) <= mtu
            elif isinstance(message, PseudoHandshakeMessage):
                space = mtu - len(packet) - RECORD_HEADER.size - len(message.payload)
                if space <= 0:  # TODO: test this line
                    packets.append(packet)
                    packet = bytearray()
                packet += RECORD_HEADER.pack(
                    message.content_type,
                    message.record_version,
                    next(self._record_seq),
                    len(message.payload),
                )
                packet += message.payload
                assert len(packet) <= mtu
            else:
                msg_len_bytes = len(message.body).to_bytes(3, "big")
                frag_offset = 0
                frags_encoded = 0
                # If message.body is empty, then we still want to encode it in one
                # fragment, not zero.
                while frag_offset < len(message.body) or not frags_encoded:
                    space = (
                        mtu
                        - len(packet)
                        - RECORD_HEADER.size
                        - HANDSHAKE_MESSAGE_HEADER.size
                    )
                    if space <= 0:
                        packets.append(packet)
                        packet = bytearray()
                        continue
                    frag = message.body[frag_offset : frag_offset + space]
                    frag_offset_bytes = frag_offset.to_bytes(3, "big")
                    frag_len_bytes = len(frag).to_bytes(3, "big")
                    frag_offset += len(frag)

                    packet += RECORD_HEADER.pack(
                        ContentType.handshake,
                        message.record_version,
                        next(self._record_seq),
                        HANDSHAKE_MESSAGE_HEADER.size + len(frag),
                    )

                    packet += HANDSHAKE_MESSAGE_HEADER.pack(
                        message.msg_type,
                        msg_len_bytes,
                        message.msg_seq,
                        frag_offset_bytes,
                        frag_len_bytes,
                    )

                    packet += frag

                    frags_encoded += 1
                    assert len(packet) <= mtu

        if packet:
            packets.append(packet)

        return packets


# This bit requires implementing a bona fide cryptographic protocol, so even though it's
# a simple one let's take a moment to discuss the design.
#
# Our goal is to force new incoming handshakes that claim to be coming from a
# given ip:port to prove that they can also receive packets sent to that
# ip:port. (There's nothing in UDP to stop someone from forging the return
# address, and it's often used for stuff like DoS reflection attacks, where
# an attacker tries to trick us into sending data at some innocent victim.)
# For more details, see:
#
#    https://datatracker.ietf.org/doc/html/rfc6347#section-4.2.1
#
# To do this, when we receive an initial ClientHello, we calculate a magic
# cookie, and send it back as a HelloVerifyRequest. Then the client sends us a
# second ClientHello, this time with the magic cookie included, and after we
# check that this cookie is valid we go ahead and start the handshake proper.
#
# So the magic cookie needs the following properties:
# - No-one can forge it without knowing our secret key
# - It ensures that the ip, port, and ClientHello contents from the response
#   match those in the challenge
# - It expires after a short-ish period (so that if an attacker manages to steal one, it
#   won't be useful for long)
# - It doesn't require storing any peer-specific state on our side
#
# To do that, we take the ip/port/ClientHello data and compute an HMAC of them, using a
# secret key we generate on startup. We also include:
#
# - The current time (using Trio's clock), rounded to the nearest 30 seconds
# - A random salt
#
# Then the cookie is the salt and the HMAC digest concatenated together.
#
# When verifying a cookie, we use the salt + new ip/port/ClientHello data to recompute
# the HMAC digest, for both the current time and the current time minus 30 seconds, and
# if either of them match, we consider the cookie good.
#
# Including the rounded-off time like this means that each cookie is good for at least
# 30 seconds, and possibly as much as 60 seconds.
#
# The salt is probably not necessary -- I'm pretty sure that all it does is make it hard
# for an attacker to figure out when our clock ticks over a 30 second boundary. Which is
# probably pretty harmless? But it's easier to add the salt than to convince myself that
# it's *completely* harmless, so, salt it is.

COOKIE_REFRESH_INTERVAL = 30  # seconds
KEY_BYTES = 32
COOKIE_HASH = "sha256"
SALT_BYTES = 8
# 32 bytes was the maximum cookie length in DTLS 1.0. DTLS 1.2 raised it to 255. I doubt
# there are any DTLS 1.0 implementations still in the wild, but really 32 bytes is
# plenty, and it also gets rid of a confusing warning in Wireshark output.
#
# We truncate the cookie to 32 bytes, of which 8 bytes is salt, so that leaves 24 bytes
# of truncated HMAC = 192 bit security, which is still massive overkill. (TCP uses 32
# *bits* for this.) HMAC truncation is explicitly noted as safe in RFC 2104:
#   https://datatracker.ietf.org/doc/html/rfc2104#section-5
COOKIE_LENGTH = 32


def _current_cookie_tick() -> int:
    return int(trio.current_time() / COOKIE_REFRESH_INTERVAL)


# Simple deterministic and invertible serializer -- i.e., a useful tool for converting
# structured data into something we can cryptographically sign.
def _signable(*fields: bytes) -> bytes:
    out: list[bytes] = []
    for field in fields:
        out.extend((struct.pack("!Q", len(field)), field))
    return b"".join(out)


def _make_cookie(
    key: bytes,
    salt: bytes,
    tick: int,
    address: AddressFormat,
    client_hello_bits: bytes,
) -> bytes:
    assert len(salt) == SALT_BYTES
    assert len(key) == KEY_BYTES

    signable_data = _signable(
        salt,
        struct.pack("!Q", tick),
        # address is a mix of strings and ints, and variable length, so pack
        # it into a single nested field
        _signable(*(str(part).encode() for part in address)),
        client_hello_bits,
    )

    return (salt + hmac.digest(key, signable_data, COOKIE_HASH))[:COOKIE_LENGTH]


def valid_cookie(
    key: bytes,
    cookie: bytes,
    address: AddressFormat,
    client_hello_bits: bytes,
) -> bool:
    if len(cookie) > SALT_BYTES:
        salt = cookie[:SALT_BYTES]

        tick = _current_cookie_tick()

        cur_cookie = _make_cookie(key, salt, tick, address, client_hello_bits)
        old_cookie = _make_cookie(
            key,
            salt,
            max(tick - 1, 0),
            address,
            client_hello_bits,
        )

        # I doubt using a short-circuiting 'or' here would leak any meaningful
        # information, but why risk it when '|' is just as easy.
        return hmac.compare_digest(cookie, cur_cookie) | hmac.compare_digest(
            cookie,
            old_cookie,
        )
    else:
        return False


def challenge_for(
    key: bytes,
    address: AddressFormat,
    epoch_seqno: int,
    client_hello_bits: bytes,
) -> bytes:
    salt = os.urandom(SALT_BYTES)
    tick = _current_cookie_tick()
    cookie = _make_cookie(key, salt, tick, address, client_hello_bits)

    # HelloVerifyRequest body is:
    # - 2 bytes version
    # - length-prefixed cookie
    #
    # The DTLS 1.2 spec says that for this message specifically we should use
    # the DTLS 1.0 version.
    #
    # (It also says the opposite of that, but that part is a mistake:
    #    https://www.rfc-editor.org/errata/eid4103
    # ).
    #
    # And I guess we use this for both the message-level and record-level
    # ProtocolVersions, since we haven't negotiated anything else yet?
    body = ProtocolVersion.DTLS10 + bytes([len(cookie)]) + cookie

    # RFC says have to copy the client's record number
    # Errata says it should be handshake message number
    # Openssl copies back record sequence number, and always sets message seq
    # number 0. So I guess we'll follow openssl.
    hs = HandshakeFragment(
        msg_type=HandshakeType.hello_verify_request,
        msg_len=len(body),
        msg_seq=0,
        frag_offset=0,
        frag_len=len(body),
        frag=body,
    )
    payload = encode_handshake_fragment(hs)

    packet = encode_record(
        Record(ContentType.handshake, ProtocolVersion.DTLS10, epoch_seqno, payload),
    )
    return packet


_T = TypeVar("_T")


class _Queue(Generic[_T]):
    def __init__(self, incoming_packets_buffer: int | float) -> None:  # noqa: PYI041
        self.s, self.r = trio.open_memory_channel[_T](incoming_packets_buffer)


def _read_loop(read_fn: Callable[[int], bytes]) -> bytes:
    chunks = []
    while True:
        try:
            chunk = read_fn(2**14)  # max TLS record size
        except SSL.WantReadError:
            break
        chunks.append(chunk)
    return b"".join(chunks)


async def handle_client_hello_untrusted(
    endpoint: DTLSEndpoint,
    address: AddressFormat,
    packet: bytes,
) -> None:
    # it's trivial to write a simple function that directly calls this to
    # get code coverage, but it should maybe:
    # 1. be removed
    # 2. be asserted
    # 3. Write a complicated test case where this happens "organically"
    if endpoint._listening_context is None:  # pragma: no cover
        return

    try:
        epoch_seqno, cookie, bits = decode_client_hello_untrusted(packet)
    except BadPacket:
        return

    if endpoint._listening_key is None:
        endpoint._listening_key = os.urandom(KEY_BYTES)

    if not valid_cookie(endpoint._listening_key, cookie, address, bits):
        challenge_packet = challenge_for(
            endpoint._listening_key,
            address,
            epoch_seqno,
            bits,
        )
        try:
            async with endpoint._send_lock:
                await endpoint.socket.sendto(challenge_packet, address)
        except (OSError, trio.ClosedResourceError):
            pass
    else:
        # We got a real, valid ClientHello!
        stream = DTLSChannel._create(endpoint, address, endpoint._listening_context)
        # Our HelloRetryRequest had some sequence number. We need our future sequence
        # numbers to be larger than it, so our peer knows that our future records aren't
        # stale/duplicates. But, we don't know what this sequence number was. What we do
        # know is:
        # - the HelloRetryRequest seqno was copied it from the initial ClientHello
        # - the new ClientHello has a higher seqno than the initial ClientHello
        # So, if we copy the new ClientHello's seqno into our first real handshake
        # record and increment from there, that should work.
        stream._record_encoder.set_first_record_number(epoch_seqno)
        # Process the ClientHello
        try:
            stream._ssl.bio_write(packet)
            stream._ssl.DTLSv1_listen()
        except SSL.Error:  # pragma: no cover
            # ...OpenSSL didn't like it, so I guess we didn't have a valid ClientHello
            # after all.
            return

        # Check if we have an existing association
        old_stream = endpoint._streams.get(address)
        if old_stream is not None:
            if old_stream._client_hello == (cookie, bits):
                # ...This was just a duplicate of the last ClientHello, so never mind.
                return
            else:
                # Ok, this *really is* a new handshake; the old stream should go away.
                old_stream._set_replaced()
        stream._client_hello = (cookie, bits)
        endpoint._streams[address] = stream
        endpoint._incoming_connections_q.s.send_nowait(stream)


async def dtls_receive_loop(
    endpoint_ref: ReferenceType[DTLSEndpoint],
    sock: SocketType,
) -> None:
    try:
        while True:
            try:
                packet, address = await sock.recvfrom(MAX_UDP_PACKET_SIZE)
            except OSError as exc:
                if exc.errno == errno.ECONNRESET:
                    # Windows only: "On a UDP-datagram socket [ECONNRESET]
                    # indicates a previous send operation resulted in an ICMP Port
                    # Unreachable message" -- https://docs.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recvfrom
                    #
                    # This is totally useless -- there's nothing we can do with this
                    # information. So we just ignore it and retry the recv.
                    continue
                else:
                    raise
            endpoint = endpoint_ref()
            try:
                if endpoint is None:
                    return
                if is_client_hello_untrusted(packet):
                    await handle_client_hello_untrusted(endpoint, address, packet)
                elif address in endpoint._streams:
                    stream = endpoint._streams[address]
                    if stream._did_handshake and part_of_handshake_untrusted(packet):
                        # The peer just sent us more handshake messages, that aren't a
                        # ClientHello, and we thought the handshake was done. Some of
                        # the packets that we sent to finish the handshake must have
                        # gotten lost. So re-send them. We do this directly here instead
                        # of just putting it into the queue and letting the receiver do
                        # it, because there's no guarantee that anyone is reading from
                        # the queue, because we think the handshake is done!
                        await stream._resend_final_volley()
                    else:
                        try:
                            # mypy for some reason cannot determine type of _q
                            stream._q.s.send_nowait(packet)  # type:ignore[has-type]
                        except trio.WouldBlock:
                            stream._packets_dropped_in_trio += 1
                else:
                    # Drop packet
                    pass
            finally:
                del endpoint
    except trio.ClosedResourceError:
        # socket was closed
        return
    except OSError as exc:
        if exc.errno in (errno.EBADF, errno.ENOTSOCK):
            # socket was closed
            return
        else:  # pragma: no cover
            # ??? shouldn't happen
            raise


@attrs.frozen
class DTLSChannelStatistics:
    """Currently this has only one attribute:

    - ``incoming_packets_dropped_in_trio`` (``int``): Gives a count of the number of
      incoming packets from this peer that Trio successfully received from the
      network, but then got dropped because the internal channel buffer was full. If
      this is non-zero, then you might want to call ``receive`` more often, or use a
      larger ``incoming_packets_buffer``, or just not worry about it because your
      UDP-based protocol should be able to handle the occasional lost packet, right?

    """

    incoming_packets_dropped_in_trio: int


@final
class DTLSChannel(trio.abc.Channel[bytes], metaclass=NoPublicConstructor):
    """A DTLS connection.

    This class has no public constructor – you get instances by calling
    `DTLSEndpoint.serve` or `~DTLSEndpoint.connect`.

    .. attribute:: endpoint

       The `DTLSEndpoint` that this connection is using.

    .. attribute:: peer_address

       The IP/port of the remote peer that this connection is associated with.

    """

    def __init__(
        self,
        endpoint: DTLSEndpoint,
        peer_address: AddressFormat,
        ctx: SSL.Context,
    ) -> None:
        self.endpoint = endpoint
        self.peer_address = peer_address
        self._packets_dropped_in_trio = 0
        self._client_hello = None
        self._did_handshake = False
        # These are mandatory for all DTLS connections. OP_NO_QUERY_MTU is required to
        # stop openssl from trying to query the memory BIO's MTU and then breaking, and
        # OP_NO_RENEGOTIATION disables renegotiation, which is too complex for us to
        # support and isn't useful anyway -- especially for DTLS where it's equivalent
        # to just performing a new handshake.
        ctx.set_options(
            SSL.OP_NO_QUERY_MTU | SSL.OP_NO_RENEGOTIATION,  # type: ignore[attr-defined]
        )
        self._ssl = SSL.Connection(ctx)
        self._handshake_mtu = 0
        # This calls self._ssl.set_ciphertext_mtu, which is important, because if you
        # don't call it then openssl doesn't work.
        self.set_ciphertext_mtu(best_guess_mtu(self.endpoint.socket))
        self._replaced = False
        self._closed = False
        self._q = _Queue[bytes](endpoint.incoming_packets_buffer)
        self._handshake_lock = trio.Lock()
        self._record_encoder: RecordEncoder = RecordEncoder()

        self._final_volley: list[_AnyHandshakeMessage] = []

    def _set_replaced(self) -> None:
        self._replaced = True
        # Any packets we already received could maybe possibly still be processed, but
        # there are no more coming. So we close this on the sender side.
        self._q.s.close()

    def _check_replaced(self) -> None:
        if self._replaced:
            raise trio.BrokenResourceError(
                "peer tore down this connection to start a new one",
            )

    # XX on systems where we can (maybe just Linux?) take advantage of the kernel's PMTU
    # estimate

    # XX should we send close-notify when closing? It seems particularly pointless for
    # DTLS where packets are all independent and can be lost anyway. We do at least need
    # to handle receiving it properly though, which might be easier if we send it...

    def close(self) -> None:
        """Close this connection.

        `DTLSChannel`\\s don't actually own any OS-level resources – the
        socket is owned by the `DTLSEndpoint`, not the individual connections. So
        you don't really *have* to call this. But it will interrupt any other tasks
        calling `receive` with a `ClosedResourceError`, and cause future attempts to use
        this connection to fail.

        You can also use this object as a synchronous or asynchronous context manager.

        """
        if self._closed:
            return
        self._closed = True
        if self.endpoint._streams.get(self.peer_address) is self:
            del self.endpoint._streams[self.peer_address]
        # Will wake any tasks waiting on self._q.get with a
        # ClosedResourceError
        self._q.r.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self.close()

    async def aclose(self) -> None:
        """Close this connection, but asynchronously.

        This is included to satisfy the `trio.abc.Channel` contract. It's
        identical to `close`, but async.

        """
        self.close()
        await trio.lowlevel.checkpoint()

    async def _send_volley(self, volley_messages: list[_AnyHandshakeMessage]) -> None:
        packets = self._record_encoder.encode_volley(
            volley_messages,
            self._handshake_mtu,
        )
        for packet in packets:
            async with self.endpoint._send_lock:
                await self.endpoint.socket.sendto(packet, self.peer_address)

    async def _resend_final_volley(self) -> None:
        await self._send_volley(self._final_volley)

    async def do_handshake(self, *, initial_retransmit_timeout: float = 1.0) -> None:
        """Perform the handshake.

        Calling this is optional – if you don't, then it will be automatically called
        the first time you call `send` or `receive`. But calling it explicitly can be
        useful in case you want to control the retransmit timeout, use a cancel scope to
        place an overall timeout on the handshake, or catch errors from the handshake
        specifically.

        It's safe to call this multiple times, or call it simultaneously from multiple
        tasks – the first call will perform the handshake, and the rest will be no-ops.

        Args:

          initial_retransmit_timeout (float): Since UDP is an unreliable protocol, it's
            possible that some of the packets we send during the handshake will get
            lost. To handle this, DTLS uses a timer to automatically retransmit
            handshake packets that don't receive a response. This lets you set the
            timeout we use to detect packet loss. Ideally, it should be set to ~1.5
            times the round-trip time to your peer, but 1 second is a reasonable
            default. There's `some useful guidance here
            <https://tlswg.org/dtls13-spec/draft-ietf-tls-dtls13.html#name-timer-values>`__.

            This is the *initial* timeout, because if packets keep being lost then Trio
            will automatically back off to longer values, to avoid overloading the
            network.

        """
        async with self._handshake_lock:
            if self._did_handshake:
                return

            timeout = initial_retransmit_timeout
            volley_messages: list[_AnyHandshakeMessage] = []
            volley_failed_sends = 0

            def read_volley() -> list[_AnyHandshakeMessage]:
                volley_bytes = _read_loop(self._ssl.bio_read)
                new_volley_messages = decode_volley_trusted(volley_bytes)
                if (
                    new_volley_messages
                    and volley_messages
                    and isinstance(new_volley_messages[0], HandshakeMessage)
                    and isinstance(volley_messages[0], HandshakeMessage)
                    and new_volley_messages[0].msg_seq == volley_messages[0].msg_seq
                ):
                    # openssl decided to retransmit; discard because we handle
                    # retransmits ourselves
                    return []
                else:
                    return new_volley_messages

            # If we're a client, we send the initial volley. If we're a server, then
            # the initial ClientHello has already been inserted into self._ssl's
            # read BIO. So either way, we start by generating a new volley.
            with contextlib.suppress(SSL.WantReadError):
                self._ssl.do_handshake()
            volley_messages = read_volley()
            # If we don't have messages to send in our initial volley, then something
            # has gone very wrong. (I'm not sure this can actually happen without an
            # error from OpenSSL, but we check just in case.)
            if not volley_messages:  # pragma: no cover
                raise SSL.Error("something wrong with peer's ClientHello")

            while True:
                # -- at this point, we need to either send or re-send a volley --
                assert volley_messages
                self._check_replaced()
                await self._send_volley(volley_messages)
                # -- then this is where we wait for a reply --
                self.endpoint._ensure_receive_loop()
                with trio.move_on_after(timeout) as cscope:
                    async for packet in self._q.r:
                        self._ssl.bio_write(packet)
                        try:
                            self._ssl.do_handshake()
                        # We ignore generic SSL.Error here, because you can get those
                        # from random invalid packets
                        except (SSL.WantReadError, SSL.Error):
                            pass
                        else:
                            # No exception -> the handshake is done, and we can
                            # switch into data transfer mode.
                            self._did_handshake = True
                            # Might be empty, but that's ok -- we'll just send no
                            # packets.
                            self._final_volley = read_volley()
                            await self._send_volley(self._final_volley)
                            return
                        maybe_volley = read_volley()
                        if maybe_volley:
                            if (
                                isinstance(maybe_volley[0], PseudoHandshakeMessage)
                                and maybe_volley[0].content_type == ContentType.alert
                            ):  # TODO: test this line
                                # we're sending an alert (e.g. due to a corrupted
                                # packet). We want to send it once, but don't save it to
                                # retransmit -- keep the last volley as the current
                                # volley.
                                await self._send_volley(maybe_volley)
                            else:
                                # We managed to get all of the peer's volley and
                                # generate a new one ourselves! break out of the 'for'
                                # loop and restart the timer.
                                volley_messages = maybe_volley
                                # "Implementations SHOULD retain the current timer value
                                # until a transmission without loss occurs, at which
                                # time the value may be reset to the initial value."
                                if volley_failed_sends == 0:
                                    timeout = initial_retransmit_timeout
                                volley_failed_sends = 0
                                break
                    else:
                        assert self._replaced
                        self._check_replaced()
                if cscope.cancelled_caught:
                    # Timeout expired. Double timeout for backoff, with a limit of 60
                    # seconds (this matches what openssl does, and also the
                    # recommendation in draft-ietf-tls-dtls13).
                    timeout = min(2 * timeout, 60.0)
                    volley_failed_sends += 1
                    if volley_failed_sends == 2:
                        # We tried sending this twice and they both failed. Maybe our
                        # PMTU estimate is wrong? Let's try dropping it to the minimum
                        # and hope that helps.
                        self._handshake_mtu = min(
                            self._handshake_mtu,
                            worst_case_mtu(self.endpoint.socket),
                        )

    async def send(self, data: bytes) -> None:
        """Send a packet of data, securely."""

        if self._closed:
            raise trio.ClosedResourceError
        if not data:
            raise ValueError("openssl doesn't support sending empty DTLS packets")
        if not self._did_handshake:
            await self.do_handshake()
        self._check_replaced()
        self._ssl.write(data)
        async with self.endpoint._send_lock:
            await self.endpoint.socket.sendto(
                _read_loop(self._ssl.bio_read),
                self.peer_address,
            )

    async def receive(self) -> bytes:
        """Fetch the next packet of data from this connection's peer, waiting if
        necessary.

        This is safe to call from multiple tasks simultaneously, in case you have some
        reason to do that. And more importantly, it's cancellation-safe, meaning that
        cancelling a call to `receive` will never cause a packet to be lost or corrupt
        the underlying connection.

        """
        if not self._did_handshake:
            await self.do_handshake()
        # If the packet isn't really valid, then openssl can decode it to the empty
        # string (e.g. b/c it's a late-arriving handshake packet, or a duplicate copy of
        # a data packet). Skip over these instead of returning them.
        while True:
            try:
                packet = await self._q.r.receive()
            except trio.EndOfChannel:
                assert self._replaced
                self._check_replaced()
            self._ssl.bio_write(packet)
            cleartext = _read_loop(self._ssl.read)
            if cleartext:
                return cleartext

    def set_ciphertext_mtu(self, new_mtu: int) -> None:
        """Tells Trio the `largest amount of data that can be sent in a single packet to
        this peer <https://en.wikipedia.org/wiki/Maximum_transmission_unit>`__.

        Trio doesn't actually enforce this limit – if you pass a huge packet to `send`,
        then we'll dutifully encrypt it and attempt to send it. But calling this method
        does have two useful effects:

        - If called before the handshake is performed, then Trio will automatically
          fragment handshake messages to fit within the given MTU. It also might
          fragment them even smaller, if it detects signs of packet loss, so setting
          this should never be necessary to make a successful connection. But, the
          packet loss detection only happens after multiple timeouts have expired, so if
          you have reason to believe that a smaller MTU is required, then you can set
          this to skip those timeouts and establish the connection more quickly.

        - It changes the value returned from `get_cleartext_mtu`. So if you have some
          kind of estimate of the network-level MTU, then you can use this to figure out
          how much overhead DTLS will need for hashes/padding/etc., and how much space
          you have left for your application data.

        The MTU here is measuring the largest UDP *payload* you think can be sent, the
        amount of encrypted data that can be handed to the operating system in a single
        call to `send`. It should *not* include IP/UDP headers. Note that OS estimates
        of the MTU often are link-layer MTUs, so you have to subtract off 28 bytes on
        IPv4 and 48 bytes on IPv6 to get the ciphertext MTU.

        By default, Trio assumes an MTU of 1472 bytes on IPv4, and 1452 bytes on IPv6,
        which correspond to the common Ethernet MTU of 1500 bytes after accounting for
        IP/UDP overhead.

        """
        self._handshake_mtu = new_mtu
        self._ssl.set_ciphertext_mtu(new_mtu)

    def get_cleartext_mtu(self) -> int:
        """Returns the largest number of bytes that you can pass in a single call to
        `send` while still fitting within the network-level MTU.

        See `set_ciphertext_mtu` for more details.

        """
        if not self._did_handshake:
            raise trio.NeedHandshakeError
        return self._ssl.get_cleartext_mtu()  # type: ignore[no-any-return]

    def statistics(self) -> DTLSChannelStatistics:
        """Returns a `DTLSChannelStatistics` object with statistics about this connection."""
        return DTLSChannelStatistics(self._packets_dropped_in_trio)


@final
class DTLSEndpoint:
    """A DTLS endpoint.

    A single UDP socket can handle arbitrarily many DTLS connections simultaneously,
    acting as a client or server as needed. A `DTLSEndpoint` object holds a UDP socket
    and manages these connections, which are represented as `DTLSChannel` objects.

    Args:
      socket: (trio.socket.SocketType): A ``SOCK_DGRAM`` socket. If you want to accept
        incoming connections in server mode, then you should probably bind the socket to
        some known port.
      incoming_packets_buffer (int): Each `DTLSChannel` using this socket has its own
        buffer that holds incoming packets until you call `~DTLSChannel.receive` to read
        them. This lets you adjust the size of this buffer. `~DTLSChannel.statistics`
        lets you check if the buffer has overflowed.

    .. attribute:: socket
                   incoming_packets_buffer

       Both constructor arguments are also exposed as attributes, in case you need to
       access them later.

    """

    def __init__(
        self,
        socket: SocketType,
        *,
        incoming_packets_buffer: int = 10,
    ) -> None:
        # We do this lazily on first construction, so only people who actually use DTLS
        # have to install PyOpenSSL.
        global SSL
        from OpenSSL import SSL

        # for __del__, in case the next line raises
        self._initialized: bool = False
        if socket.type != trio.socket.SOCK_DGRAM:
            raise ValueError("DTLS requires a SOCK_DGRAM socket")
        self._initialized = True
        self.socket: SocketType = socket

        self.incoming_packets_buffer = incoming_packets_buffer
        self._token = trio.lowlevel.current_trio_token()
        # We don't need to track handshaking vs non-handshake connections
        # separately. We only keep one connection per remote address; as soon
        # as a peer provides a valid cookie, we can immediately tear down the
        # old connection.
        # {remote address: DTLSChannel}
        self._streams: WeakValueDictionary[AddressFormat, DTLSChannel] = (
            WeakValueDictionary()
        )
        self._listening_context: SSL.Context | None = None
        self._listening_key: bytes | None = None
        self._incoming_connections_q = _Queue[DTLSChannel](float("inf"))
        self._send_lock = trio.Lock()
        self._closed = False
        self._receive_loop_spawned = False

    def _ensure_receive_loop(self) -> None:
        # We have to spawn this lazily, because on Windows it will immediately error out
        # if the socket isn't already bound -- which for clients might not happen until
        # after we send our first packet.
        if not self._receive_loop_spawned:
            trio.lowlevel.spawn_system_task(
                dtls_receive_loop,
                weakref.ref(self),
                self.socket,
            )
            self._receive_loop_spawned = True

    def __del__(self) -> None:
        # Do nothing if this object was never fully constructed
        if not self._initialized:
            return
        # Close the socket in Trio context (if our Trio context still exists), so that
        # the background task gets notified about the closure and can exit.
        if not self._closed:
            with contextlib.suppress(RuntimeError):
                self._token.run_sync_soon(self.close)
            # Do this last, because it might raise an exception
            warnings.warn(
                f"unclosed DTLS endpoint {self!r}",
                ResourceWarning,
                source=self,
                stacklevel=1,
            )

    def close(self) -> None:
        """Close this socket, and all associated DTLS connections.

        This object can also be used as a context manager.

        """
        self._closed = True
        self.socket.close()
        for stream in list(self._streams.values()):
            stream.close()
        self._incoming_connections_q.s.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self.close()

    def _check_closed(self) -> None:
        if self._closed:
            raise trio.ClosedResourceError

    async def serve(
        self,
        ssl_context: SSL.Context,
        async_fn: Callable[[DTLSChannel, Unpack[PosArgsT]], Awaitable[object]],
        *args: Unpack[PosArgsT],
        task_status: trio.TaskStatus[None] = trio.TASK_STATUS_IGNORED,
    ) -> None:
        """Listen for incoming connections, and spawn a handler for each using an
        internal nursery.

        Similar to `~trio.serve_tcp`, this function never returns until cancelled, or
        the `DTLSEndpoint` is closed and all handlers have exited.

        Usage commonly looks like::

            async def handler(dtls_channel):
                ...

            async with trio.open_nursery() as nursery:
                await nursery.start(dtls_endpoint.serve, ssl_context, handler)
                # ... do other things here ...

        The ``dtls_channel`` passed into the handler function has already performed the
        "cookie exchange" part of the DTLS handshake, so the peer address is
        trustworthy. But the actual cryptographic handshake doesn't happen until you
        start using it, giving you a chance for any last minute configuration, and the
        option to catch and handle handshake errors.

        Args:
          ssl_context (OpenSSL.SSL.Context): The PyOpenSSL context object to use for
            incoming connections.
          async_fn: The handler function that will be invoked for each incoming
            connection.
          *args: Additional arguments to pass to the handler function.

        """
        self._check_closed()
        if self._listening_context is not None:
            raise trio.BusyResourceError("another task is already listening")
        try:
            self.socket.getsockname()
        except OSError:  # TODO: test this line
            raise RuntimeError(
                "DTLS socket must be bound before it can serve",
            ) from None
        self._ensure_receive_loop()
        # We do cookie verification ourselves, so tell OpenSSL not to worry about it.
        # (See also _inject_client_hello_untrusted.)
        ssl_context.set_cookie_verify_callback(lambda *_: True)
        try:
            self._listening_context = ssl_context
            task_status.started()

            async def handler_wrapper(stream: DTLSChannel) -> None:
                with stream:
                    await async_fn(stream, *args)

            async with trio.open_nursery() as nursery:
                async for stream in self._incoming_connections_q.r:  # pragma: no branch
                    nursery.start_soon(handler_wrapper, stream)
        finally:
            self._listening_context = None

    def connect(
        self,
        address: tuple[str, int],
        ssl_context: SSL.Context,
    ) -> DTLSChannel:
        """Initiate an outgoing DTLS connection.

        Notice that this is a synchronous method. That's because it doesn't actually
        initiate any I/O – it just sets up a `DTLSChannel` object. The actual handshake
        doesn't occur until you start using the `DTLSChannel`. This gives you a chance
        to do further configuration first, like setting MTU etc.

        Args:
          address: The address to connect to. Usually a (host, port) tuple, like
            ``("127.0.0.1", 12345)``.
          ssl_context (OpenSSL.SSL.Context): The PyOpenSSL context object to use for
            this connection.

        Returns:
          DTLSChannel

        """
        # it would be nice if we could detect when 'address' is our own endpoint (a
        # loopback connection), because that can't work
        # but I don't see how to do it reliably
        self._check_closed()
        channel = DTLSChannel._create(self, address, ssl_context)
        channel._ssl.set_connect_state()
        old_channel = self._streams.get(address)
        if old_channel is not None:
            old_channel._set_replaced()
        self._streams[address] = channel
        return channel