
# === NexusCore/tools\exports\export_20250803_114325\combined_167.py ===

# === NexusCore/openenv\Lib\site-packages\fontTools\merge\layout.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod, Roozbeh Pournader

from fontTools import ttLib
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from fontTools.ttLib.tables import otTables
from fontTools.merge.base import add_method, mergeObjects
from fontTools.merge.util import *
import logging


log = logging.getLogger("fontTools.merge")


def mergeLookupLists(lst):
    # TODO Do smarter merge.
    return sumLists(lst)


def mergeFeatures(lst):
    assert lst
    self = otTables.Feature()
    self.FeatureParams = None
    self.LookupListIndex = mergeLookupLists(
        [l.LookupListIndex for l in lst if l.LookupListIndex]
    )
    self.LookupCount = len(self.LookupListIndex)
    return self


def mergeFeatureLists(lst):
    d = {}
    for l in lst:
        for f in l:
            tag = f.FeatureTag
            if tag not in d:
                d[tag] = []
            d[tag].append(f.Feature)
    ret = []
    for tag in sorted(d.keys()):
        rec = otTables.FeatureRecord()
        rec.FeatureTag = tag
        rec.Feature = mergeFeatures(d[tag])
        ret.append(rec)
    return ret


def mergeLangSyses(lst):
    assert lst

    # TODO Support merging ReqFeatureIndex
    assert all(l.ReqFeatureIndex == 0xFFFF for l in lst)

    self = otTables.LangSys()
    self.LookupOrder = None
    self.ReqFeatureIndex = 0xFFFF
    self.FeatureIndex = mergeFeatureLists(
        [l.FeatureIndex for l in lst if l.FeatureIndex]
    )
    self.FeatureCount = len(self.FeatureIndex)
    return self


def mergeScripts(lst):
    assert lst

    if len(lst) == 1:
        return lst[0]
    langSyses = {}
    for sr in lst:
        for lsr in sr.LangSysRecord:
            if lsr.LangSysTag not in langSyses:
                langSyses[lsr.LangSysTag] = []
            langSyses[lsr.LangSysTag].append(lsr.LangSys)
    lsrecords = []
    for tag, langSys_list in sorted(langSyses.items()):
        lsr = otTables.LangSysRecord()
        lsr.LangSys = mergeLangSyses(langSys_list)
        lsr.LangSysTag = tag
        lsrecords.append(lsr)

    self = otTables.Script()
    self.LangSysRecord = lsrecords
    self.LangSysCount = len(lsrecords)
    dfltLangSyses = [s.DefaultLangSys for s in lst if s.DefaultLangSys]
    if dfltLangSyses:
        self.DefaultLangSys = mergeLangSyses(dfltLangSyses)
    else:
        self.DefaultLangSys = None
    return self


def mergeScriptRecords(lst):
    d = {}
    for l in lst:
        for s in l:
            tag = s.ScriptTag
            if tag not in d:
                d[tag] = []
            d[tag].append(s.Script)
    ret = []
    for tag in sorted(d.keys()):
        rec = otTables.ScriptRecord()
        rec.ScriptTag = tag
        rec.Script = mergeScripts(d[tag])
        ret.append(rec)
    return ret


otTables.ScriptList.mergeMap = {
    "ScriptCount": lambda lst: None,  # TODO
    "ScriptRecord": mergeScriptRecords,
}
otTables.BaseScriptList.mergeMap = {
    "BaseScriptCount": lambda lst: None,  # TODO
    # TODO: Merge duplicate entries
    "BaseScriptRecord": lambda lst: sorted(
        sumLists(lst), key=lambda s: s.BaseScriptTag
    ),
}

otTables.FeatureList.mergeMap = {
    "FeatureCount": sum,
    "FeatureRecord": lambda lst: sorted(sumLists(lst), key=lambda s: s.FeatureTag),
}

otTables.LookupList.mergeMap = {
    "LookupCount": sum,
    "Lookup": sumLists,
}

otTables.Coverage.mergeMap = {
    "Format": min,
    "glyphs": sumLists,
}

otTables.ClassDef.mergeMap = {
    "Format": min,
    "classDefs": sumDicts,
}

otTables.LigCaretList.mergeMap = {
    "Coverage": mergeObjects,
    "LigGlyphCount": sum,
    "LigGlyph": sumLists,
}

otTables.AttachList.mergeMap = {
    "Coverage": mergeObjects,
    "GlyphCount": sum,
    "AttachPoint": sumLists,
}

# XXX Renumber MarkFilterSets of lookups
otTables.MarkGlyphSetsDef.mergeMap = {
    "MarkSetTableFormat": equal,
    "MarkSetCount": sum,
    "Coverage": sumLists,
}

otTables.Axis.mergeMap = {
    "*": mergeObjects,
}

# XXX Fix BASE table merging
otTables.BaseTagList.mergeMap = {
    "BaseTagCount": sum,
    "BaselineTag": sumLists,
}

otTables.GDEF.mergeMap = otTables.GSUB.mergeMap = otTables.GPOS.mergeMap = (
    otTables.BASE.mergeMap
) = otTables.JSTF.mergeMap = otTables.MATH.mergeMap = {
    "*": mergeObjects,
    "Version": max,
}

ttLib.getTableClass("GDEF").mergeMap = ttLib.getTableClass("GSUB").mergeMap = (
    ttLib.getTableClass("GPOS").mergeMap
) = ttLib.getTableClass("BASE").mergeMap = ttLib.getTableClass(
    "JSTF"
).mergeMap = ttLib.getTableClass(
    "MATH"
).mergeMap = {
    "tableTag": onlyExisting(equal),  # XXX clean me up
    "table": mergeObjects,
}


@add_method(ttLib.getTableClass("GSUB"))
def merge(self, m, tables):
    assert len(tables) == len(m.duplicateGlyphsPerFont)
    for i, (table, dups) in enumerate(zip(tables, m.duplicateGlyphsPerFont)):
        if not dups:
            continue
        if table is None or table is NotImplemented:
            log.warning(
                "Have non-identical duplicates to resolve for '%s' but no GSUB. Are duplicates intended?: %s",
                m.fonts[i]._merger__name,
                dups,
            )
            continue

        synthFeature = None
        synthLookup = None
        for script in table.table.ScriptList.ScriptRecord:
            if script.ScriptTag == "DFLT":
                continue  # XXX
            for langsys in [script.Script.DefaultLangSys] + [
                l.LangSys for l in script.Script.LangSysRecord
            ]:
                if langsys is None:
                    continue  # XXX Create!
                feature = [v for v in langsys.FeatureIndex if v.FeatureTag == "locl"]
                assert len(feature) <= 1
                if feature:
                    feature = feature[0]
                else:
                    if not synthFeature:
                        synthFeature = otTables.FeatureRecord()
                        synthFeature.FeatureTag = "locl"
                        f = synthFeature.Feature = otTables.Feature()
                        f.FeatureParams = None
                        f.LookupCount = 0
                        f.LookupListIndex = []
                        table.table.FeatureList.FeatureRecord.append(synthFeature)
                        table.table.FeatureList.FeatureCount += 1
                    feature = synthFeature
                    langsys.FeatureIndex.append(feature)
                    langsys.FeatureIndex.sort(key=lambda v: v.FeatureTag)

                if not synthLookup:
                    subtable = otTables.SingleSubst()
                    subtable.mapping = dups
                    synthLookup = otTables.Lookup()
                    synthLookup.LookupFlag = 0
                    synthLookup.LookupType = 1
                    synthLookup.SubTableCount = 1
                    synthLookup.SubTable = [subtable]
                    if table.table.LookupList is None:
                        # mtiLib uses None as default value for LookupList,
                        # while feaLib points to an empty array with count 0
                        # TODO: make them do the same
                        table.table.LookupList = otTables.LookupList()
                        table.table.LookupList.Lookup = []
                        table.table.LookupList.LookupCount = 0
                    table.table.LookupList.Lookup.append(synthLookup)
                    table.table.LookupList.LookupCount += 1

                if feature.Feature.LookupListIndex[:1] != [synthLookup]:
                    feature.Feature.LookupListIndex[:0] = [synthLookup]
                    feature.Feature.LookupCount += 1

    DefaultTable.merge(self, m, tables)
    return self


@add_method(
    otTables.SingleSubst,
    otTables.MultipleSubst,
    otTables.AlternateSubst,
    otTables.LigatureSubst,
    otTables.ReverseChainSingleSubst,
    otTables.SinglePos,
    otTables.PairPos,
    otTables.CursivePos,
    otTables.MarkBasePos,
    otTables.MarkLigPos,
    otTables.MarkMarkPos,
)
def mapLookups(self, lookupMap):
    pass


# Copied and trimmed down from subset.py
@add_method(
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def __merge_classify_context(self):
    class ContextHelper(object):
        def __init__(self, klass, Format):
            if klass.__name__.endswith("Subst"):
                Typ = "Sub"
                Type = "Subst"
            else:
                Typ = "Pos"
                Type = "Pos"
            if klass.__name__.startswith("Chain"):
                Chain = "Chain"
            else:
                Chain = ""
            ChainTyp = Chain + Typ

            self.Typ = Typ
            self.Type = Type
            self.Chain = Chain
            self.ChainTyp = ChainTyp

            self.LookupRecord = Type + "LookupRecord"

            if Format == 1:
                self.Rule = ChainTyp + "Rule"
                self.RuleSet = ChainTyp + "RuleSet"
            elif Format == 2:
                self.Rule = ChainTyp + "ClassRule"
                self.RuleSet = ChainTyp + "ClassSet"

    if self.Format not in [1, 2, 3]:
        return None  # Don't shoot the messenger; let it go
    if not hasattr(self.__class__, "_merge__ContextHelpers"):
        self.__class__._merge__ContextHelpers = {}
    if self.Format not in self.__class__._merge__ContextHelpers:
        helper = ContextHelper(self.__class__, self.Format)
        self.__class__._merge__ContextHelpers[self.Format] = helper
    return self.__class__._merge__ContextHelpers[self.Format]


@add_method(
    otTables.ContextSubst,
    otTables.ChainContextSubst,
    otTables.ContextPos,
    otTables.ChainContextPos,
)
def mapLookups(self, lookupMap):
    c = self.__merge_classify_context()

    if self.Format in [1, 2]:
        for rs in getattr(self, c.RuleSet):
            if not rs:
                continue
            for r in getattr(rs, c.Rule):
                if not r:
                    continue
                for ll in getattr(r, c.LookupRecord):
                    if not ll:
                        continue
                    ll.LookupListIndex = lookupMap[ll.LookupListIndex]
    elif self.Format == 3:
        for ll in getattr(self, c.LookupRecord):
            if not ll:
                continue
            ll.LookupListIndex = lookupMap[ll.LookupListIndex]
    else:
        assert 0, "unknown format: %s" % self.Format


@add_method(otTables.ExtensionSubst, otTables.ExtensionPos)
def mapLookups(self, lookupMap):
    if self.Format == 1:
        self.ExtSubTable.mapLookups(lookupMap)
    else:
        assert 0, "unknown format: %s" % self.Format


@add_method(otTables.Lookup)
def mapLookups(self, lookupMap):
    for st in self.SubTable:
        if not st:
            continue
        st.mapLookups(lookupMap)


@add_method(otTables.LookupList)
def mapLookups(self, lookupMap):
    for l in self.Lookup:
        if not l:
            continue
        l.mapLookups(lookupMap)


@add_method(otTables.Lookup)
def mapMarkFilteringSets(self, markFilteringSetMap):
    if self.LookupFlag & 0x0010:
        self.MarkFilteringSet = markFilteringSetMap[self.MarkFilteringSet]


@add_method(otTables.LookupList)
def mapMarkFilteringSets(self, markFilteringSetMap):
    for l in self.Lookup:
        if not l:
            continue
        l.mapMarkFilteringSets(markFilteringSetMap)


@add_method(otTables.Feature)
def mapLookups(self, lookupMap):
    self.LookupListIndex = [lookupMap[i] for i in self.LookupListIndex]


@add_method(otTables.FeatureList)
def mapLookups(self, lookupMap):
    for f in self.FeatureRecord:
        if not f or not f.Feature:
            continue
        f.Feature.mapLookups(lookupMap)


@add_method(otTables.DefaultLangSys, otTables.LangSys)
def mapFeatures(self, featureMap):
    self.FeatureIndex = [featureMap[i] for i in self.FeatureIndex]
    if self.ReqFeatureIndex != 65535:
        self.ReqFeatureIndex = featureMap[self.ReqFeatureIndex]


@add_method(otTables.Script)
def mapFeatures(self, featureMap):
    if self.DefaultLangSys:
        self.DefaultLangSys.mapFeatures(featureMap)
    for l in self.LangSysRecord:
        if not l or not l.LangSys:
            continue
        l.LangSys.mapFeatures(featureMap)


@add_method(otTables.ScriptList)
def mapFeatures(self, featureMap):
    for s in self.ScriptRecord:
        if not s or not s.Script:
            continue
        s.Script.mapFeatures(featureMap)


def layoutPreMerge(font):
    # Map indices to references

    GDEF = font.get("GDEF")
    GSUB = font.get("GSUB")
    GPOS = font.get("GPOS")

    for t in [GSUB, GPOS]:
        if not t:
            continue

        if t.table.LookupList:
            lookupMap = {i: v for i, v in enumerate(t.table.LookupList.Lookup)}
            t.table.LookupList.mapLookups(lookupMap)
            t.table.FeatureList.mapLookups(lookupMap)

            if (
                GDEF
                and GDEF.table.Version >= 0x00010002
                and GDEF.table.MarkGlyphSetsDef
            ):
                markFilteringSetMap = {
                    i: v for i, v in enumerate(GDEF.table.MarkGlyphSetsDef.Coverage)
                }
                t.table.LookupList.mapMarkFilteringSets(markFilteringSetMap)

        if t.table.FeatureList and t.table.ScriptList:
            featureMap = {i: v for i, v in enumerate(t.table.FeatureList.FeatureRecord)}
            t.table.ScriptList.mapFeatures(featureMap)

    # TODO FeatureParams nameIDs


def layoutPostMerge(font):
    # Map references back to indices

    GDEF = font.get("GDEF")
    GSUB = font.get("GSUB")
    GPOS = font.get("GPOS")

    for t in [GSUB, GPOS]:
        if not t:
            continue

        if t.table.FeatureList and t.table.ScriptList:
            # Collect unregistered (new) features.
            featureMap = GregariousIdentityDict(t.table.FeatureList.FeatureRecord)
            t.table.ScriptList.mapFeatures(featureMap)

            # Record used features.
            featureMap = AttendanceRecordingIdentityDict(
                t.table.FeatureList.FeatureRecord
            )
            t.table.ScriptList.mapFeatures(featureMap)
            usedIndices = featureMap.s

            # Remove unused features
            t.table.FeatureList.FeatureRecord = [
                f
                for i, f in enumerate(t.table.FeatureList.FeatureRecord)
                if i in usedIndices
            ]

            # Map back to indices.
            featureMap = NonhashableDict(t.table.FeatureList.FeatureRecord)
            t.table.ScriptList.mapFeatures(featureMap)

            t.table.FeatureList.FeatureCount = len(t.table.FeatureList.FeatureRecord)

        if t.table.LookupList:
            # Collect unregistered (new) lookups.
            lookupMap = GregariousIdentityDict(t.table.LookupList.Lookup)
            t.table.FeatureList.mapLookups(lookupMap)
            t.table.LookupList.mapLookups(lookupMap)

            # Record used lookups.
            lookupMap = AttendanceRecordingIdentityDict(t.table.LookupList.Lookup)
            t.table.FeatureList.mapLookups(lookupMap)
            t.table.LookupList.mapLookups(lookupMap)
            usedIndices = lookupMap.s

            # Remove unused lookups
            t.table.LookupList.Lookup = [
                l for i, l in enumerate(t.table.LookupList.Lookup) if i in usedIndices
            ]

            # Map back to indices.
            lookupMap = NonhashableDict(t.table.LookupList.Lookup)
            t.table.FeatureList.mapLookups(lookupMap)
            t.table.LookupList.mapLookups(lookupMap)

            t.table.LookupList.LookupCount = len(t.table.LookupList.Lookup)

            if GDEF and GDEF.table.Version >= 0x00010002:
                markFilteringSetMap = NonhashableDict(
                    GDEF.table.MarkGlyphSetsDef.Coverage
                )
                t.table.LookupList.mapMarkFilteringSets(markFilteringSetMap)

    # TODO FeatureParams nameIDs

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\key_binding\key_processor.py ===
"""
An :class:`~.KeyProcessor` receives callbacks for the keystrokes parsed from
the input in the :class:`~prompt_toolkit.inputstream.InputStream` instance.

The `KeyProcessor` will according to the implemented keybindings call the
correct callbacks when new key presses are feed through `feed`.
"""

from __future__ import annotations

import weakref
from asyncio import Task, sleep
from collections import deque
from typing import TYPE_CHECKING, Any, Generator

from prompt_toolkit.application.current import get_app
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters.app import vi_navigation_mode
from prompt_toolkit.keys import Keys
from prompt_toolkit.utils import Event

from .key_bindings import Binding, KeyBindingsBase

if TYPE_CHECKING:
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer


__all__ = [
    "KeyProcessor",
    "KeyPress",
    "KeyPressEvent",
]


class KeyPress:
    """
    :param key: A `Keys` instance or text (one character).
    :param data: The received string on stdin. (Often vt100 escape codes.)
    """

    def __init__(self, key: Keys | str, data: str | None = None) -> None:
        assert isinstance(key, Keys) or len(key) == 1

        if data is None:
            if isinstance(key, Keys):
                data = key.value
            else:
                data = key  # 'key' is a one character string.

        self.key = key
        self.data = data

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(key={self.key!r}, data={self.data!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeyPress):
            return False
        return self.key == other.key and self.data == other.data


"""
Helper object to indicate flush operation in the KeyProcessor.
NOTE: the implementation is very similar to the VT100 parser.
"""
_Flush = KeyPress("?", data="_Flush")


class KeyProcessor:
    """
    Statemachine that receives :class:`KeyPress` instances and according to the
    key bindings in the given :class:`KeyBindings`, calls the matching handlers.

    ::

        p = KeyProcessor(key_bindings)

        # Send keys into the processor.
        p.feed(KeyPress(Keys.ControlX, '\x18'))
        p.feed(KeyPress(Keys.ControlC, '\x03')

        # Process all the keys in the queue.
        p.process_keys()

        # Now the ControlX-ControlC callback will be called if this sequence is
        # registered in the key bindings.

    :param key_bindings: `KeyBindingsBase` instance.
    """

    def __init__(self, key_bindings: KeyBindingsBase) -> None:
        self._bindings = key_bindings

        self.before_key_press = Event(self)
        self.after_key_press = Event(self)

        self._flush_wait_task: Task[None] | None = None

        self.reset()

    def reset(self) -> None:
        self._previous_key_sequence: list[KeyPress] = []
        self._previous_handler: Binding | None = None

        # The queue of keys not yet send to our _process generator/state machine.
        self.input_queue: deque[KeyPress] = deque()

        # The key buffer that is matched in the generator state machine.
        # (This is at at most the amount of keys that make up for one key binding.)
        self.key_buffer: list[KeyPress] = []

        #: Readline argument (for repetition of commands.)
        #: https://www.gnu.org/software/bash/manual/html_node/Readline-Arguments.html
        self.arg: str | None = None

        # Start the processor coroutine.
        self._process_coroutine = self._process()
        self._process_coroutine.send(None)  # type: ignore

    def _get_matches(self, key_presses: list[KeyPress]) -> list[Binding]:
        """
        For a list of :class:`KeyPress` instances. Give the matching handlers
        that would handle this.
        """
        keys = tuple(k.key for k in key_presses)

        # Try match, with mode flag
        return [b for b in self._bindings.get_bindings_for_keys(keys) if b.filter()]

    def _is_prefix_of_longer_match(self, key_presses: list[KeyPress]) -> bool:
        """
        For a list of :class:`KeyPress` instances. Return True if there is any
        handler that is bound to a suffix of this keys.
        """
        keys = tuple(k.key for k in key_presses)

        # Get the filters for all the key bindings that have a longer match.
        # Note that we transform it into a `set`, because we don't care about
        # the actual bindings and executing it more than once doesn't make
        # sense. (Many key bindings share the same filter.)
        filters = {
            b.filter for b in self._bindings.get_bindings_starting_with_keys(keys)
        }

        # When any key binding is active, return True.
        return any(f() for f in filters)

    def _process(self) -> Generator[None, KeyPress, None]:
        """
        Coroutine implementing the key match algorithm. Key strokes are sent
        into this generator, and it calls the appropriate handlers.
        """
        buffer = self.key_buffer
        retry = False

        while True:
            flush = False

            if retry:
                retry = False
            else:
                key = yield
                if key is _Flush:
                    flush = True
                else:
                    buffer.append(key)

            # If we have some key presses, check for matches.
            if buffer:
                matches = self._get_matches(buffer)

                if flush:
                    is_prefix_of_longer_match = False
                else:
                    is_prefix_of_longer_match = self._is_prefix_of_longer_match(buffer)

                # When eager matches were found, give priority to them and also
                # ignore all the longer matches.
                eager_matches = [m for m in matches if m.eager()]

                if eager_matches:
                    matches = eager_matches
                    is_prefix_of_longer_match = False

                # Exact matches found, call handler.
                if not is_prefix_of_longer_match and matches:
                    self._call_handler(matches[-1], key_sequence=buffer[:])
                    del buffer[:]  # Keep reference.

                # No match found.
                elif not is_prefix_of_longer_match and not matches:
                    retry = True
                    found = False

                    # Loop over the input, try longest match first and shift.
                    for i in range(len(buffer), 0, -1):
                        matches = self._get_matches(buffer[:i])
                        if matches:
                            self._call_handler(matches[-1], key_sequence=buffer[:i])
                            del buffer[:i]
                            found = True
                            break

                    if not found:
                        del buffer[:1]

    def feed(self, key_press: KeyPress, first: bool = False) -> None:
        """
        Add a new :class:`KeyPress` to the input queue.
        (Don't forget to call `process_keys` in order to process the queue.)

        :param first: If true, insert before everything else.
        """
        if first:
            self.input_queue.appendleft(key_press)
        else:
            self.input_queue.append(key_press)

    def feed_multiple(self, key_presses: list[KeyPress], first: bool = False) -> None:
        """
        :param first: If true, insert before everything else.
        """
        if first:
            self.input_queue.extendleft(reversed(key_presses))
        else:
            self.input_queue.extend(key_presses)

    def process_keys(self) -> None:
        """
        Process all the keys in the `input_queue`.
        (To be called after `feed`.)

        Note: because of the `feed`/`process_keys` separation, it is
              possible to call `feed` from inside a key binding.
              This function keeps looping until the queue is empty.
        """
        app = get_app()

        def not_empty() -> bool:
            # When the application result is set, stop processing keys.  (E.g.
            # if ENTER was received, followed by a few additional key strokes,
            # leave the other keys in the queue.)
            if app.is_done:
                # But if there are still CPRResponse keys in the queue, these
                # need to be processed.
                return any(k for k in self.input_queue if k.key == Keys.CPRResponse)
            else:
                return bool(self.input_queue)

        def get_next() -> KeyPress:
            if app.is_done:
                # Only process CPR responses. Everything else is typeahead.
                cpr = [k for k in self.input_queue if k.key == Keys.CPRResponse][0]
                self.input_queue.remove(cpr)
                return cpr
            else:
                return self.input_queue.popleft()

        is_flush = False

        while not_empty():
            # Process next key.
            key_press = get_next()

            is_flush = key_press is _Flush
            is_cpr = key_press.key == Keys.CPRResponse

            if not is_flush and not is_cpr:
                self.before_key_press.fire()

            try:
                self._process_coroutine.send(key_press)
            except Exception:
                # If for some reason something goes wrong in the parser, (maybe
                # an exception was raised) restart the processor for next time.
                self.reset()
                self.empty_queue()
                raise

            if not is_flush and not is_cpr:
                self.after_key_press.fire()

        # Skip timeout if the last key was flush.
        if not is_flush:
            self._start_timeout()

    def empty_queue(self) -> list[KeyPress]:
        """
        Empty the input queue. Return the unprocessed input.
        """
        key_presses = list(self.input_queue)
        self.input_queue.clear()

        # Filter out CPRs. We don't want to return these.
        key_presses = [k for k in key_presses if k.key != Keys.CPRResponse]
        return key_presses

    def _call_handler(self, handler: Binding, key_sequence: list[KeyPress]) -> None:
        app = get_app()
        was_recording_emacs = app.emacs_state.is_recording
        was_recording_vi = bool(app.vi_state.recording_register)
        was_temporary_navigation_mode = app.vi_state.temporary_navigation_mode
        arg = self.arg
        self.arg = None

        event = KeyPressEvent(
            weakref.ref(self),
            arg=arg,
            key_sequence=key_sequence,
            previous_key_sequence=self._previous_key_sequence,
            is_repeat=(handler == self._previous_handler),
        )

        # Save the state of the current buffer.
        if handler.save_before(event):
            event.app.current_buffer.save_to_undo_stack()

        # Call handler.
        from prompt_toolkit.buffer import EditReadOnlyBuffer

        try:
            handler.call(event)
            self._fix_vi_cursor_position(event)

        except EditReadOnlyBuffer:
            # When a key binding does an attempt to change a buffer which is
            # read-only, we can ignore that. We sound a bell and go on.
            app.output.bell()

        if was_temporary_navigation_mode:
            self._leave_vi_temp_navigation_mode(event)

        self._previous_key_sequence = key_sequence
        self._previous_handler = handler

        # Record the key sequence in our macro. (Only if we're in macro mode
        # before and after executing the key.)
        if handler.record_in_macro():
            if app.emacs_state.is_recording and was_recording_emacs:
                recording = app.emacs_state.current_recording
                if recording is not None:  # Should always be true, given that
                    # `was_recording_emacs` is set.
                    recording.extend(key_sequence)

            if app.vi_state.recording_register and was_recording_vi:
                for k in key_sequence:
                    app.vi_state.current_recording += k.data

    def _fix_vi_cursor_position(self, event: KeyPressEvent) -> None:
        """
        After every command, make sure that if we are in Vi navigation mode, we
        never put the cursor after the last character of a line. (Unless it's
        an empty line.)
        """
        app = event.app
        buff = app.current_buffer
        preferred_column = buff.preferred_column

        if (
            vi_navigation_mode()
            and buff.document.is_cursor_at_the_end_of_line
            and len(buff.document.current_line) > 0
        ):
            buff.cursor_position -= 1

            # Set the preferred_column for arrow up/down again.
            # (This was cleared after changing the cursor position.)
            buff.preferred_column = preferred_column

    def _leave_vi_temp_navigation_mode(self, event: KeyPressEvent) -> None:
        """
        If we're in Vi temporary navigation (normal) mode, return to
        insert/replace mode after executing one action.
        """
        app = event.app

        if app.editing_mode == EditingMode.VI:
            # Not waiting for a text object and no argument has been given.
            if app.vi_state.operator_func is None and self.arg is None:
                app.vi_state.temporary_navigation_mode = False

    def _start_timeout(self) -> None:
        """
        Start auto flush timeout. Similar to Vim's `timeoutlen` option.

        Start a background coroutine with a timer. When this timeout expires
        and no key was pressed in the meantime, we flush all data in the queue
        and call the appropriate key binding handlers.
        """
        app = get_app()
        timeout = app.timeoutlen

        if timeout is None:
            return

        async def wait() -> None:
            "Wait for timeout."
            # This sleep can be cancelled. In that case we don't flush.
            await sleep(timeout)

            if len(self.key_buffer) > 0:
                # (No keys pressed in the meantime.)
                flush_keys()

        def flush_keys() -> None:
            "Flush keys."
            self.feed(_Flush)
            self.process_keys()

        # Automatically flush keys.
        if self._flush_wait_task:
            self._flush_wait_task.cancel()
        self._flush_wait_task = app.create_background_task(wait())

    def send_sigint(self) -> None:
        """
        Send SIGINT. Immediately call the SIGINT key handler.
        """
        self.feed(KeyPress(key=Keys.SIGINT), first=True)
        self.process_keys()


class KeyPressEvent:
    """
    Key press event, delivered to key bindings.

    :param key_processor_ref: Weak reference to the `KeyProcessor`.
    :param arg: Repetition argument.
    :param key_sequence: List of `KeyPress` instances.
    :param previouskey_sequence: Previous list of `KeyPress` instances.
    :param is_repeat: True when the previous event was delivered to the same handler.
    """

    def __init__(
        self,
        key_processor_ref: weakref.ReferenceType[KeyProcessor],
        arg: str | None,
        key_sequence: list[KeyPress],
        previous_key_sequence: list[KeyPress],
        is_repeat: bool,
    ) -> None:
        self._key_processor_ref = key_processor_ref
        self.key_sequence = key_sequence
        self.previous_key_sequence = previous_key_sequence

        #: True when the previous key sequence was handled by the same handler.
        self.is_repeat = is_repeat

        self._arg = arg
        self._app = get_app()

    def __repr__(self) -> str:
        return f"KeyPressEvent(arg={self.arg!r}, key_sequence={self.key_sequence!r}, is_repeat={self.is_repeat!r})"

    @property
    def data(self) -> str:
        return self.key_sequence[-1].data

    @property
    def key_processor(self) -> KeyProcessor:
        processor = self._key_processor_ref()
        if processor is None:
            raise Exception("KeyProcessor was lost. This should not happen.")
        return processor

    @property
    def app(self) -> Application[Any]:
        """
        The current `Application` object.
        """
        return self._app

    @property
    def current_buffer(self) -> Buffer:
        """
        The current buffer.
        """
        return self.app.current_buffer

    @property
    def arg(self) -> int:
        """
        Repetition argument.
        """
        if self._arg == "-":
            return -1

        result = int(self._arg or 1)

        # Don't exceed a million.
        if int(result) >= 1000000:
            result = 1

        return result

    @property
    def arg_present(self) -> bool:
        """
        True if repetition argument was explicitly provided.
        """
        return self._arg is not None

    def append_to_arg_count(self, data: str) -> None:
        """
        Add digit to the input argument.

        :param data: the typed digit as string
        """
        assert data in "-0123456789"
        current = self._arg

        if data == "-":
            assert current is None or current == "-"
            result = data
        elif current is None:
            result = data
        else:
            result = f"{current}{data}"

        self.key_processor.arg = result

    @property
    def cli(self) -> Application[Any]:
        "For backward-compatibility."
        return self.app

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\erlang.py ===
"""
    pygments.lexers.erlang
    ~~~~~~~~~~~~~~~~~~~~~~

    Lexers for Erlang.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, bygroups, words, do_insertions, \
    include, default, line_re
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Whitespace

__all__ = ['ErlangLexer', 'ErlangShellLexer', 'ElixirConsoleLexer',
           'ElixirLexer']


class ErlangLexer(RegexLexer):
    """
    For the Erlang functional programming language.
    """

    name = 'Erlang'
    url = 'https://www.erlang.org/'
    aliases = ['erlang']
    filenames = ['*.erl', '*.hrl', '*.es', '*.escript']
    mimetypes = ['text/x-erlang']
    version_added = '0.9'

    keywords = (
        'after', 'begin', 'case', 'catch', 'cond', 'end', 'fun', 'if',
        'let', 'of', 'query', 'receive', 'try', 'when',
    )

    builtins = (  # See erlang(3) man page
        'abs', 'append_element', 'apply', 'atom_to_list', 'binary_to_list',
        'bitstring_to_list', 'binary_to_term', 'bit_size', 'bump_reductions',
        'byte_size', 'cancel_timer', 'check_process_code', 'delete_module',
        'demonitor', 'disconnect_node', 'display', 'element', 'erase', 'exit',
        'float', 'float_to_list', 'fun_info', 'fun_to_list',
        'function_exported', 'garbage_collect', 'get', 'get_keys',
        'group_leader', 'hash', 'hd', 'integer_to_list', 'iolist_to_binary',
        'iolist_size', 'is_atom', 'is_binary', 'is_bitstring', 'is_boolean',
        'is_builtin', 'is_float', 'is_function', 'is_integer', 'is_list',
        'is_number', 'is_pid', 'is_port', 'is_process_alive', 'is_record',
        'is_reference', 'is_tuple', 'length', 'link', 'list_to_atom',
        'list_to_binary', 'list_to_bitstring', 'list_to_existing_atom',
        'list_to_float', 'list_to_integer', 'list_to_pid', 'list_to_tuple',
        'load_module', 'localtime_to_universaltime', 'make_tuple', 'md5',
        'md5_final', 'md5_update', 'memory', 'module_loaded', 'monitor',
        'monitor_node', 'node', 'nodes', 'open_port', 'phash', 'phash2',
        'pid_to_list', 'port_close', 'port_command', 'port_connect',
        'port_control', 'port_call', 'port_info', 'port_to_list',
        'process_display', 'process_flag', 'process_info', 'purge_module',
        'put', 'read_timer', 'ref_to_list', 'register', 'resume_process',
        'round', 'send', 'send_after', 'send_nosuspend', 'set_cookie',
        'setelement', 'size', 'spawn', 'spawn_link', 'spawn_monitor',
        'spawn_opt', 'split_binary', 'start_timer', 'statistics',
        'suspend_process', 'system_flag', 'system_info', 'system_monitor',
        'system_profile', 'term_to_binary', 'tl', 'trace', 'trace_delivered',
        'trace_info', 'trace_pattern', 'trunc', 'tuple_size', 'tuple_to_list',
        'universaltime_to_localtime', 'unlink', 'unregister', 'whereis'
    )

    operators = r'(\+\+?|--?|\*|/|<|>|/=|=:=|=/=|=<|>=|==?|<-|!|\?)'
    word_operators = (
        'and', 'andalso', 'band', 'bnot', 'bor', 'bsl', 'bsr', 'bxor',
        'div', 'not', 'or', 'orelse', 'rem', 'xor'
    )

    atom_re = r"(?:[a-z]\w*|'[^\n']*[^\\]')"

    variable_re = r'(?:[A-Z_]\w*)'

    esc_char_re = r'[bdefnrstv\'"\\]'
    esc_octal_re = r'[0-7][0-7]?[0-7]?'
    esc_hex_re = r'(?:x[0-9a-fA-F]{2}|x\{[0-9a-fA-F]+\})'
    esc_ctrl_re = r'\^[a-zA-Z]'
    escape_re = r'(?:\\(?:'+esc_char_re+r'|'+esc_octal_re+r'|'+esc_hex_re+r'|'+esc_ctrl_re+r'))'

    macro_re = r'(?:'+variable_re+r'|'+atom_re+r')'

    base_re = r'(?:[2-9]|[12][0-9]|3[0-6])'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(%.*)(\n)', bygroups(Comment, Whitespace)),
            (words(keywords, suffix=r'\b'), Keyword),
            (words(builtins, suffix=r'\b'), Name.Builtin),
            (words(word_operators, suffix=r'\b'), Operator.Word),
            (r'^-', Punctuation, 'directive'),
            (operators, Operator),
            (r'"', String, 'string'),
            (r'<<', Name.Label),
            (r'>>', Name.Label),
            ('(' + atom_re + ')(:)', bygroups(Name.Namespace, Punctuation)),
            ('(?:^|(?<=:))(' + atom_re + r')(\s*)(\()',
             bygroups(Name.Function, Whitespace, Punctuation)),
            (r'[+-]?' + base_re + r'#[0-9a-zA-Z]+', Number.Integer),
            (r'[+-]?\d+', Number.Integer),
            (r'[+-]?\d+.\d+', Number.Float),
            (r'[]\[:_@\".{}()|;,]', Punctuation),
            (variable_re, Name.Variable),
            (atom_re, Name),
            (r'\?'+macro_re, Name.Constant),
            (r'\$(?:'+escape_re+r'|\\[ %]|[^\\])', String.Char),
            (r'#'+atom_re+r'(:?\.'+atom_re+r')?', Name.Label),

            # Erlang script shebang
            (r'\A#!.+\n', Comment.Hashbang),

            # EEP 43: Maps
            # http://www.erlang.org/eeps/eep-0043.html
            (r'#\{', Punctuation, 'map_key'),
        ],
        'string': [
            (escape_re, String.Escape),
            (r'"', String, '#pop'),
            (r'~[0-9.*]*[~#+BPWXb-ginpswx]', String.Interpol),
            (r'[^"\\~]+', String),
            (r'~', String),
        ],
        'directive': [
            (r'(define)(\s*)(\()('+macro_re+r')',
             bygroups(Name.Entity, Whitespace, Punctuation, Name.Constant), '#pop'),
            (r'(record)(\s*)(\()('+macro_re+r')',
             bygroups(Name.Entity, Whitespace, Punctuation, Name.Label), '#pop'),
            (atom_re, Name.Entity, '#pop'),
        ],
        'map_key': [
            include('root'),
            (r'=>', Punctuation, 'map_val'),
            (r':=', Punctuation, 'map_val'),
            (r'\}', Punctuation, '#pop'),
        ],
        'map_val': [
            include('root'),
            (r',', Punctuation, '#pop'),
            (r'(?=\})', Punctuation, '#pop'),
        ],
    }


class ErlangShellLexer(Lexer):
    """
    Shell sessions in erl (for Erlang code).
    """
    name = 'Erlang erl session'
    aliases = ['erl']
    filenames = ['*.erl-sh']
    mimetypes = ['text/x-erl-shellsession']
    url = 'https://www.erlang.org/'
    version_added = '1.1'

    _prompt_re = re.compile(r'(?:\([\w@_.]+\))?\d+>(?=\s|\Z)')

    def get_tokens_unprocessed(self, text):
        erlexer = ErlangLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            m = self._prompt_re.match(line)
            if m is not None:
                end = m.end()
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:end])]))
                curcode += line[end:]
            else:
                if curcode:
                    yield from do_insertions(insertions,
                                             erlexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                if line.startswith('*'):
                    yield match.start(), Generic.Traceback, line
                else:
                    yield match.start(), Generic.Output, line
        if curcode:
            yield from do_insertions(insertions,
                                     erlexer.get_tokens_unprocessed(curcode))


def gen_elixir_string_rules(name, symbol, token):
    states = {}
    states['string_' + name] = [
        (rf'[^#{symbol}\\]+', token),
        include('escapes'),
        (r'\\.', token),
        (rf'({symbol})', bygroups(token), "#pop"),
        include('interpol')
    ]
    return states


def gen_elixir_sigstr_rules(term, term_class, token, interpol=True):
    if interpol:
        return [
            (rf'[^#{term_class}\\]+', token),
            include('escapes'),
            (r'\\.', token),
            (rf'{term}[a-zA-Z]*', token, '#pop'),
            include('interpol')
        ]
    else:
        return [
            (rf'[^{term_class}\\]+', token),
            (r'\\.', token),
            (rf'{term}[a-zA-Z]*', token, '#pop'),
        ]


class ElixirLexer(RegexLexer):
    """
    For the Elixir language.
    """

    name = 'Elixir'
    url = 'https://elixir-lang.org'
    aliases = ['elixir', 'ex', 'exs']
    filenames = ['*.ex', '*.eex', '*.exs', '*.leex']
    mimetypes = ['text/x-elixir']
    version_added = '1.5'

    KEYWORD = ('fn', 'do', 'end', 'after', 'else', 'rescue', 'catch')
    KEYWORD_OPERATOR = ('not', 'and', 'or', 'when', 'in')
    BUILTIN = (
        'case', 'cond', 'for', 'if', 'unless', 'try', 'receive', 'raise',
        'quote', 'unquote', 'unquote_splicing', 'throw', 'super',
    )
    BUILTIN_DECLARATION = (
        'def', 'defp', 'defmodule', 'defprotocol', 'defmacro', 'defmacrop',
        'defdelegate', 'defexception', 'defstruct', 'defimpl', 'defcallback',
    )

    BUILTIN_NAMESPACE = ('import', 'require', 'use', 'alias')
    CONSTANT = ('nil', 'true', 'false')

    PSEUDO_VAR = ('_', '__MODULE__', '__DIR__', '__ENV__', '__CALLER__')

    OPERATORS3 = (
        '<<<', '>>>', '|||', '&&&', '^^^', '~~~', '===', '!==',
        '~>>', '<~>', '|~>', '<|>',
    )
    OPERATORS2 = (
        '==', '!=', '<=', '>=', '&&', '||', '<>', '++', '--', '|>', '=~',
        '->', '<-', '|', '.', '=', '~>', '<~',
    )
    OPERATORS1 = ('<', '>', '+', '-', '*', '/', '!', '^', '&')

    PUNCTUATION = (
        '\\\\', '<<', '>>', '=>', '(', ')', ':', ';', ',', '[', ']',
    )

    def get_tokens_unprocessed(self, text):
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name:
                if value in self.KEYWORD:
                    yield index, Keyword, value
                elif value in self.KEYWORD_OPERATOR:
                    yield index, Operator.Word, value
                elif value in self.BUILTIN:
                    yield index, Keyword, value
                elif value in self.BUILTIN_DECLARATION:
                    yield index, Keyword.Declaration, value
                elif value in self.BUILTIN_NAMESPACE:
                    yield index, Keyword.Namespace, value
                elif value in self.CONSTANT:
                    yield index, Name.Constant, value
                elif value in self.PSEUDO_VAR:
                    yield index, Name.Builtin.Pseudo, value
                else:
                    yield index, token, value
            else:
                yield index, token, value

    def gen_elixir_sigil_rules():
        # all valid sigil terminators (excluding heredocs)
        terminators = [
            (r'\{', r'\}', '}',   'cb'),
            (r'\[', r'\]', r'\]', 'sb'),
            (r'\(', r'\)', ')',   'pa'),
            ('<',   '>',   '>',   'ab'),
            ('/',   '/',   '/',   'slas'),
            (r'\|', r'\|', '|',   'pipe'),
            ('"',   '"',   '"',   'quot'),
            ("'",   "'",   "'",   'apos'),
        ]

        # heredocs have slightly different rules
        triquotes = [(r'"""', 'triquot'), (r"'''", 'triapos')]

        token = String.Other
        states = {'sigils': []}

        for term, name in triquotes:
            states['sigils'] += [
                (rf'(~[a-z])({term})', bygroups(token, String.Heredoc),
                    (name + '-end', name + '-intp')),
                (rf'(~[A-Z])({term})', bygroups(token, String.Heredoc),
                    (name + '-end', name + '-no-intp')),
            ]

            states[name + '-end'] = [
                (r'[a-zA-Z]+', token, '#pop'),
                default('#pop'),
            ]
            states[name + '-intp'] = [
                (r'^(\s*)(' + term + ')', bygroups(Whitespace, String.Heredoc), '#pop'),
                include('heredoc_interpol'),
            ]
            states[name + '-no-intp'] = [
                (r'^(\s*)(' + term +')', bygroups(Whitespace, String.Heredoc), '#pop'),
                include('heredoc_no_interpol'),
            ]

        for lterm, rterm, rterm_class, name in terminators:
            states['sigils'] += [
                (r'~[a-z]' + lterm, token, name + '-intp'),
                (r'~[A-Z]' + lterm, token, name + '-no-intp'),
            ]
            states[name + '-intp'] = \
                gen_elixir_sigstr_rules(rterm, rterm_class, token)
            states[name + '-no-intp'] = \
                gen_elixir_sigstr_rules(rterm, rterm_class, token, interpol=False)

        return states

    op3_re = "|".join(re.escape(s) for s in OPERATORS3)
    op2_re = "|".join(re.escape(s) for s in OPERATORS2)
    op1_re = "|".join(re.escape(s) for s in OPERATORS1)
    ops_re = rf'(?:{op3_re}|{op2_re}|{op1_re})'
    punctuation_re = "|".join(re.escape(s) for s in PUNCTUATION)
    alnum = r'\w'
    name_re = rf'(?:\.\.\.|[a-z_]{alnum}*[!?]?)'
    modname_re = rf'[A-Z]{alnum}*(?:\.[A-Z]{alnum}*)*'
    complex_name_re = rf'(?:{name_re}|{modname_re}|{ops_re})'
    special_atom_re = r'(?:\.\.\.|<<>>|%\{\}|%|\{\})'

    long_hex_char_re = r'(\\x\{)([\da-fA-F]+)(\})'
    hex_char_re = r'(\\x[\da-fA-F]{1,2})'
    escape_char_re = r'(\\[abdefnrstv])'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'#.*$', Comment.Single),

            # Various kinds of characters
            (r'(\?)' + long_hex_char_re,
                bygroups(String.Char,
                         String.Escape, Number.Hex, String.Escape)),
            (r'(\?)' + hex_char_re,
                bygroups(String.Char, String.Escape)),
            (r'(\?)' + escape_char_re,
                bygroups(String.Char, String.Escape)),
            (r'\?\\?.', String.Char),

            # '::' has to go before atoms
            (r':::', String.Symbol),
            (r'::', Operator),

            # atoms
            (r':' + special_atom_re, String.Symbol),
            (r':' + complex_name_re, String.Symbol),
            (r':"', String.Symbol, 'string_double_atom'),
            (r":'", String.Symbol, 'string_single_atom'),

            # [keywords: ...]
            (rf'({special_atom_re}|{complex_name_re})(:)(?=\s|\n)',
                bygroups(String.Symbol, Punctuation)),

            # @attributes
            (r'@' + name_re, Name.Attribute),

            # identifiers
            (name_re, Name),
            (rf'(%?)({modname_re})', bygroups(Punctuation, Name.Class)),

            # operators and punctuation
            (op3_re, Operator),
            (op2_re, Operator),
            (punctuation_re, Punctuation),
            (r'&\d', Name.Entity),   # anon func arguments
            (op1_re, Operator),

            # numbers
            (r'0b[01]+', Number.Bin),
            (r'0o[0-7]+', Number.Oct),
            (r'0x[\da-fA-F]+', Number.Hex),
            (r'\d(_?\d)*\.\d(_?\d)*([eE][-+]?\d(_?\d)*)?', Number.Float),
            (r'\d(_?\d)*', Number.Integer),

            # strings and heredocs
            (r'(""")(\s*)', bygroups(String.Heredoc, Whitespace),
                'heredoc_double'),
            (r"(''')(\s*)$", bygroups(String.Heredoc, Whitespace),
                'heredoc_single'),
            (r'"', String.Double, 'string_double'),
            (r"'", String.Single, 'string_single'),

            include('sigils'),

            (r'%\{', Punctuation, 'map_key'),
            (r'\{', Punctuation, 'tuple'),
        ],
        'heredoc_double': [
            (r'^(\s*)(""")', bygroups(Whitespace, String.Heredoc), '#pop'),
            include('heredoc_interpol'),
        ],
        'heredoc_single': [
            (r"^\s*'''", String.Heredoc, '#pop'),
            include('heredoc_interpol'),
        ],
        'heredoc_interpol': [
            (r'[^#\\\n]+', String.Heredoc),
            include('escapes'),
            (r'\\.', String.Heredoc),
            (r'\n+', String.Heredoc),
            include('interpol'),
        ],
        'heredoc_no_interpol': [
            (r'[^\\\n]+', String.Heredoc),
            (r'\\.', String.Heredoc),
            (r'\n+', Whitespace),
        ],
        'escapes': [
            (long_hex_char_re,
                bygroups(String.Escape, Number.Hex, String.Escape)),
            (hex_char_re, String.Escape),
            (escape_char_re, String.Escape),
        ],
        'interpol': [
            (r'#\{', String.Interpol, 'interpol_string'),
        ],
        'interpol_string': [
            (r'\}', String.Interpol, "#pop"),
            include('root')
        ],
        'map_key': [
            include('root'),
            (r':', Punctuation, 'map_val'),
            (r'=>', Punctuation, 'map_val'),
            (r'\}', Punctuation, '#pop'),
        ],
        'map_val': [
            include('root'),
            (r',', Punctuation, '#pop'),
            (r'(?=\})', Punctuation, '#pop'),
        ],
        'tuple': [
            include('root'),
            (r'\}', Punctuation, '#pop'),
        ],
    }
    tokens.update(gen_elixir_string_rules('double', '"', String.Double))
    tokens.update(gen_elixir_string_rules('single', "'", String.Single))
    tokens.update(gen_elixir_string_rules('double_atom', '"', String.Symbol))
    tokens.update(gen_elixir_string_rules('single_atom', "'", String.Symbol))
    tokens.update(gen_elixir_sigil_rules())


class ElixirConsoleLexer(Lexer):
    """
    For Elixir interactive console (iex) output like:

    .. sourcecode:: iex

        iex> [head | tail] = [1,2,3]
        [1,2,3]
        iex> head
        1
        iex> tail
        [2,3]
        iex> [head | tail]
        [1,2,3]
        iex> length [head | tail]
        3
    """

    name = 'Elixir iex session'
    aliases = ['iex']
    mimetypes = ['text/x-elixir-shellsession']
    url = 'https://elixir-lang.org'
    version_added = '1.5'

    _prompt_re = re.compile(r'(iex|\.{3})((?:\([\w@_.]+\))?\d+|\(\d+\))?> ')

    def get_tokens_unprocessed(self, text):
        exlexer = ElixirLexer(**self.options)

        curcode = ''
        in_error = False
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            if line.startswith('** '):
                in_error = True
                insertions.append((len(curcode),
                                   [(0, Generic.Error, line[:-1])]))
                curcode += line[-1:]
            else:
                m = self._prompt_re.match(line)
                if m is not None:
                    in_error = False
                    end = m.end()
                    insertions.append((len(curcode),
                                       [(0, Generic.Prompt, line[:end])]))
                    curcode += line[end:]
                else:
                    if curcode:
                        yield from do_insertions(
                            insertions, exlexer.get_tokens_unprocessed(curcode))
                        curcode = ''
                        insertions = []
                    token = Generic.Error if in_error else Generic.Output
                    yield match.start(), token, line
        if curcode:
            yield from do_insertions(
                insertions, exlexer.get_tokens_unprocessed(curcode))

# === NexusCore/openenv\Lib\site-packages\setuptools\config\_apply_pyprojecttoml.py ===
"""Translation layer between pyproject config and setuptools distribution and
metadata objects.

The distribution and metadata objects are modeled after (an old version of)
core metadata, therefore configs in the format specified for ``pyproject.toml``
need to be processed before being applied.

**PRIVATE MODULE**: API reserved for setuptools internal usage only.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from email.headerregistry import Address
from functools import partial, reduce
from inspect import cleandoc
from itertools import chain
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

from .. import _static
from .._path import StrPath
from ..errors import InvalidConfigError, RemovedConfigError
from ..extension import Extension
from ..warnings import SetuptoolsDeprecationWarning, SetuptoolsWarning

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from setuptools._importlib import metadata
    from setuptools.dist import Distribution

    from distutils.dist import _OptionsList  # Comes from typeshed


EMPTY: Mapping = MappingProxyType({})  # Immutable dict-like
_ProjectReadmeValue: TypeAlias = Union[str, dict[str, str]]
_Correspondence: TypeAlias = Callable[["Distribution", Any, Union[StrPath, None]], None]
_T = TypeVar("_T")

_logger = logging.getLogger(__name__)


def apply(dist: Distribution, config: dict, filename: StrPath) -> Distribution:
    """Apply configuration dict read with :func:`read_configuration`"""

    if not config:
        return dist  # short-circuit unrelated pyproject.toml file

    root_dir = os.path.dirname(filename) or "."

    _apply_project_table(dist, config, root_dir)
    _apply_tool_table(dist, config, filename)

    current_directory = os.getcwd()
    os.chdir(root_dir)
    try:
        dist._finalize_requires()
        dist._finalize_license_expression()
        dist._finalize_license_files()
    finally:
        os.chdir(current_directory)

    return dist


def _apply_project_table(dist: Distribution, config: dict, root_dir: StrPath):
    orig_config = config.get("project", {})
    if not orig_config:
        return  # short-circuit

    project_table = {k: _static.attempt_conversion(v) for k, v in orig_config.items()}
    _handle_missing_dynamic(dist, project_table)
    _unify_entry_points(project_table)

    for field, value in project_table.items():
        norm_key = json_compatible_key(field)
        corresp = PYPROJECT_CORRESPONDENCE.get(norm_key, norm_key)
        if callable(corresp):
            corresp(dist, value, root_dir)
        else:
            _set_config(dist, corresp, value)


def _apply_tool_table(dist: Distribution, config: dict, filename: StrPath):
    tool_table = config.get("tool", {}).get("setuptools", {})
    if not tool_table:
        return  # short-circuit

    if "license-files" in tool_table:
        if "license-files" in config.get("project", {}):
            # https://github.com/pypa/setuptools/pull/4837#discussion_r2004983349
            raise InvalidConfigError(
                "'project.license-files' is defined already. "
                "Remove 'tool.setuptools.license-files'."
            )

        pypa_guides = "guides/writing-pyproject-toml/#license-files"
        SetuptoolsDeprecationWarning.emit(
            "'tool.setuptools.license-files' is deprecated in favor of "
            "'project.license-files' (available on setuptools>=77.0.0).",
            see_url=f"https://packaging.python.org/en/latest/{pypa_guides}",
            due_date=(2026, 2, 18),  # Warning introduced on 2025-02-18
        )

    for field, value in tool_table.items():
        norm_key = json_compatible_key(field)

        if norm_key in TOOL_TABLE_REMOVALS:
            suggestion = cleandoc(TOOL_TABLE_REMOVALS[norm_key])
            msg = f"""
            The parameter `tool.setuptools.{field}` was long deprecated
            and has been removed from `pyproject.toml`.
            """
            raise RemovedConfigError("\n".join([cleandoc(msg), suggestion]))

        norm_key = TOOL_TABLE_RENAMES.get(norm_key, norm_key)
        corresp = TOOL_TABLE_CORRESPONDENCE.get(norm_key, norm_key)
        if callable(corresp):
            corresp(dist, value)
        else:
            _set_config(dist, corresp, value)

    _copy_command_options(config, dist, filename)


def _handle_missing_dynamic(dist: Distribution, project_table: dict):
    """Be temporarily forgiving with ``dynamic`` fields not listed in ``dynamic``"""
    dynamic = set(project_table.get("dynamic", []))
    for field, getter in _PREVIOUSLY_DEFINED.items():
        if not (field in project_table or field in dynamic):
            value = getter(dist)
            if value:
                _MissingDynamic.emit(field=field, value=value)
                project_table[field] = _RESET_PREVIOUSLY_DEFINED.get(field)


def json_compatible_key(key: str) -> str:
    """As defined in :pep:`566#json-compatible-metadata`"""
    return key.lower().replace("-", "_")


def _set_config(dist: Distribution, field: str, value: Any):
    val = _PREPROCESS.get(field, _noop)(dist, value)
    setter = getattr(dist.metadata, f"set_{field}", None)
    if setter:
        setter(val)
    elif hasattr(dist.metadata, field) or field in SETUPTOOLS_PATCHES:
        setattr(dist.metadata, field, val)
    else:
        setattr(dist, field, val)


_CONTENT_TYPES = {
    ".md": "text/markdown",
    ".rst": "text/x-rst",
    ".txt": "text/plain",
}


def _guess_content_type(file: str) -> str | None:
    _, ext = os.path.splitext(file.lower())
    if not ext:
        return None

    if ext in _CONTENT_TYPES:
        return _static.Str(_CONTENT_TYPES[ext])

    valid = ", ".join(f"{k} ({v})" for k, v in _CONTENT_TYPES.items())
    msg = f"only the following file extensions are recognized: {valid}."
    raise ValueError(f"Undefined content type for {file}, {msg}")


def _long_description(
    dist: Distribution, val: _ProjectReadmeValue, root_dir: StrPath | None
):
    from setuptools.config import expand

    file: str | tuple[()]
    if isinstance(val, str):
        file = val
        text = expand.read_files(file, root_dir)
        ctype = _guess_content_type(file)
    else:
        file = val.get("file") or ()
        text = val.get("text") or expand.read_files(file, root_dir)
        ctype = val["content-type"]

    # XXX: Is it completely safe to assume static?
    _set_config(dist, "long_description", _static.Str(text))

    if ctype:
        _set_config(dist, "long_description_content_type", _static.Str(ctype))

    if file:
        dist._referenced_files.add(file)


def _license(dist: Distribution, val: str | dict, root_dir: StrPath | None):
    from setuptools.config import expand

    if isinstance(val, str):
        if getattr(dist.metadata, "license", None):
            SetuptoolsWarning.emit("`license` overwritten by `pyproject.toml`")
            dist.metadata.license = None
        _set_config(dist, "license_expression", _static.Str(val))
    else:
        pypa_guides = "guides/writing-pyproject-toml/#license"
        SetuptoolsDeprecationWarning.emit(
            "`project.license` as a TOML table is deprecated",
            "Please use a simple string containing a SPDX expression for "
            "`project.license`. You can also use `project.license-files`. "
            "(Both options available on setuptools>=77.0.0).",
            see_url=f"https://packaging.python.org/en/latest/{pypa_guides}",
            due_date=(2026, 2, 18),  # Introduced on 2025-02-18
        )
        if "file" in val:
            # XXX: Is it completely safe to assume static?
            value = expand.read_files([val["file"]], root_dir)
            _set_config(dist, "license", _static.Str(value))
            dist._referenced_files.add(val["file"])
        else:
            _set_config(dist, "license", _static.Str(val["text"]))


def _people(dist: Distribution, val: list[dict], _root_dir: StrPath | None, kind: str):
    field = []
    email_field = []
    for person in val:
        if "name" not in person:
            email_field.append(person["email"])
        elif "email" not in person:
            field.append(person["name"])
        else:
            addr = Address(display_name=person["name"], addr_spec=person["email"])
            email_field.append(str(addr))

    if field:
        _set_config(dist, kind, _static.Str(", ".join(field)))
    if email_field:
        _set_config(dist, f"{kind}_email", _static.Str(", ".join(email_field)))


def _project_urls(dist: Distribution, val: dict, _root_dir: StrPath | None):
    _set_config(dist, "project_urls", val)


def _python_requires(dist: Distribution, val: str, _root_dir: StrPath | None):
    _set_config(dist, "python_requires", _static.SpecifierSet(val))


def _dependencies(dist: Distribution, val: list, _root_dir: StrPath | None):
    if getattr(dist, "install_requires", []):
        msg = "`install_requires` overwritten in `pyproject.toml` (dependencies)"
        SetuptoolsWarning.emit(msg)
    dist.install_requires = val


def _optional_dependencies(dist: Distribution, val: dict, _root_dir: StrPath | None):
    if getattr(dist, "extras_require", None):
        msg = "`extras_require` overwritten in `pyproject.toml` (optional-dependencies)"
        SetuptoolsWarning.emit(msg)
    dist.extras_require = val


def _ext_modules(dist: Distribution, val: list[dict]) -> list[Extension]:
    existing = dist.ext_modules or []
    args = ({k.replace("-", "_"): v for k, v in x.items()} for x in val)
    new = [Extension(**kw) for kw in args]
    return [*existing, *new]


def _noop(_dist: Distribution, val: _T) -> _T:
    return val


def _identity(val: _T) -> _T:
    return val


def _unify_entry_points(project_table: dict):
    project = project_table
    given = project.pop("entry-points", project.pop("entry_points", {}))
    entry_points = dict(given)  # Avoid problems with static
    renaming = {"scripts": "console_scripts", "gui_scripts": "gui_scripts"}
    for key, value in list(project.items()):  # eager to allow modifications
        norm_key = json_compatible_key(key)
        if norm_key in renaming:
            # Don't skip even if value is empty (reason: reset missing `dynamic`)
            entry_points[renaming[norm_key]] = project.pop(key)

    if entry_points:
        project["entry-points"] = {
            name: [f"{k} = {v}" for k, v in group.items()]
            for name, group in entry_points.items()
            if group  # now we can skip empty groups
        }
        # Sometimes this will set `project["entry-points"] = {}`, and that is
        # intentional (for resetting configurations that are missing `dynamic`).


def _copy_command_options(pyproject: dict, dist: Distribution, filename: StrPath):
    tool_table = pyproject.get("tool", {})
    cmdclass = tool_table.get("setuptools", {}).get("cmdclass", {})
    valid_options = _valid_command_options(cmdclass)

    cmd_opts = dist.command_options
    for cmd, config in pyproject.get("tool", {}).get("distutils", {}).items():
        cmd = json_compatible_key(cmd)
        valid = valid_options.get(cmd, set())
        cmd_opts.setdefault(cmd, {})
        for key, value in config.items():
            key = json_compatible_key(key)
            cmd_opts[cmd][key] = (str(filename), value)
            if key not in valid:
                # To avoid removing options that are specified dynamically we
                # just log a warn...
                _logger.warning(f"Command option {cmd}.{key} is not defined")


def _valid_command_options(cmdclass: Mapping = EMPTY) -> dict[str, set[str]]:
    from setuptools.dist import Distribution

    from .._importlib import metadata

    valid_options = {"global": _normalise_cmd_options(Distribution.global_options)}

    unloaded_entry_points = metadata.entry_points(group='distutils.commands')
    loaded_entry_points = (_load_ep(ep) for ep in unloaded_entry_points)
    entry_points = (ep for ep in loaded_entry_points if ep)
    for cmd, cmd_class in chain(entry_points, cmdclass.items()):
        opts = valid_options.get(cmd, set())
        opts = opts | _normalise_cmd_options(getattr(cmd_class, "user_options", []))
        valid_options[cmd] = opts

    return valid_options


def _load_ep(ep: metadata.EntryPoint) -> tuple[str, type] | None:
    if ep.value.startswith("wheel.bdist_wheel"):
        # Ignore deprecated entrypoint from wheel and avoid warning pypa/wheel#631
        # TODO: remove check when `bdist_wheel` has been fully removed from pypa/wheel
        return None

    # Ignore all the errors
    try:
        return (ep.name, ep.load())
    except Exception as ex:
        msg = f"{ex.__class__.__name__} while trying to load entry-point {ep.name}"
        _logger.warning(f"{msg}: {ex}")
        return None


def _normalise_cmd_option_key(name: str) -> str:
    return json_compatible_key(name).strip("_=")


def _normalise_cmd_options(desc: _OptionsList) -> set[str]:
    return {_normalise_cmd_option_key(fancy_option[0]) for fancy_option in desc}


def _get_previous_entrypoints(dist: Distribution) -> dict[str, list]:
    ignore = ("console_scripts", "gui_scripts")
    value = getattr(dist, "entry_points", None) or {}
    return {k: v for k, v in value.items() if k not in ignore}


def _get_previous_scripts(dist: Distribution) -> list | None:
    value = getattr(dist, "entry_points", None) or {}
    return value.get("console_scripts")


def _get_previous_gui_scripts(dist: Distribution) -> list | None:
    value = getattr(dist, "entry_points", None) or {}
    return value.get("gui_scripts")


def _set_static_list_metadata(attr: str, dist: Distribution, val: list) -> None:
    """Apply distutils metadata validation but preserve "static" behaviour"""
    meta = dist.metadata
    setter, getter = getattr(meta, f"set_{attr}"), getattr(meta, f"get_{attr}")
    setter(val)
    setattr(meta, attr, _static.List(getter()))


def _attrgetter(attr):
    """
    Similar to ``operator.attrgetter`` but returns None if ``attr`` is not found
    >>> from types import SimpleNamespace
    >>> obj = SimpleNamespace(a=42, b=SimpleNamespace(c=13))
    >>> _attrgetter("a")(obj)
    42
    >>> _attrgetter("b.c")(obj)
    13
    >>> _attrgetter("d")(obj) is None
    True
    """
    return partial(reduce, lambda acc, x: getattr(acc, x, None), attr.split("."))


def _some_attrgetter(*items):
    """
    Return the first "truth-y" attribute or None
    >>> from types import SimpleNamespace
    >>> obj = SimpleNamespace(a=42, b=SimpleNamespace(c=13))
    >>> _some_attrgetter("d", "a", "b.c")(obj)
    42
    >>> _some_attrgetter("d", "e", "b.c", "a")(obj)
    13
    >>> _some_attrgetter("d", "e", "f")(obj) is None
    True
    """

    def _acessor(obj):
        values = (_attrgetter(i)(obj) for i in items)
        return next((i for i in values if i is not None), None)

    return _acessor


PYPROJECT_CORRESPONDENCE: dict[str, _Correspondence] = {
    "readme": _long_description,
    "license": _license,
    "authors": partial(_people, kind="author"),
    "maintainers": partial(_people, kind="maintainer"),
    "urls": _project_urls,
    "dependencies": _dependencies,
    "optional_dependencies": _optional_dependencies,
    "requires_python": _python_requires,
}

TOOL_TABLE_RENAMES = {"script_files": "scripts"}
TOOL_TABLE_REMOVALS = {
    "namespace_packages": """
        Please migrate to implicit native namespaces instead.
        See https://packaging.python.org/en/latest/guides/packaging-namespace-packages/.
        """,
}
TOOL_TABLE_CORRESPONDENCE = {
    # Fields with corresponding core metadata need to be marked as static:
    "obsoletes": partial(_set_static_list_metadata, "obsoletes"),
    "provides": partial(_set_static_list_metadata, "provides"),
    "platforms": partial(_set_static_list_metadata, "platforms"),
}

SETUPTOOLS_PATCHES = {
    "long_description_content_type",
    "project_urls",
    "provides_extras",
    "license_file",
    "license_files",
    "license_expression",
}

_PREPROCESS = {
    "ext_modules": _ext_modules,
}

_PREVIOUSLY_DEFINED = {
    "name": _attrgetter("metadata.name"),
    "version": _attrgetter("metadata.version"),
    "description": _attrgetter("metadata.description"),
    "readme": _attrgetter("metadata.long_description"),
    "requires-python": _some_attrgetter("python_requires", "metadata.python_requires"),
    "license": _some_attrgetter("metadata.license_expression", "metadata.license"),
    # XXX: `license-file` is currently not considered in the context of `dynamic`.
    #      See TestPresetField.test_license_files_exempt_from_dynamic
    "authors": _some_attrgetter("metadata.author", "metadata.author_email"),
    "maintainers": _some_attrgetter("metadata.maintainer", "metadata.maintainer_email"),
    "keywords": _attrgetter("metadata.keywords"),
    "classifiers": _attrgetter("metadata.classifiers"),
    "urls": _attrgetter("metadata.project_urls"),
    "entry-points": _get_previous_entrypoints,
    "scripts": _get_previous_scripts,
    "gui-scripts": _get_previous_gui_scripts,
    "dependencies": _attrgetter("install_requires"),
    "optional-dependencies": _attrgetter("extras_require"),
}


_RESET_PREVIOUSLY_DEFINED: dict = {
    # Fix improper setting: given in `setup.py`, but not listed in `dynamic`
    # Use "immutable" data structures to avoid in-place modification.
    # dict: pyproject name => value to which reset
    "license": "",
    # XXX: `license-file` is currently not considered in the context of `dynamic`.
    #      See TestPresetField.test_license_files_exempt_from_dynamic
    "authors": _static.EMPTY_LIST,
    "maintainers": _static.EMPTY_LIST,
    "keywords": _static.EMPTY_LIST,
    "classifiers": _static.EMPTY_LIST,
    "urls": _static.EMPTY_DICT,
    "entry-points": _static.EMPTY_DICT,
    "scripts": _static.EMPTY_DICT,
    "gui-scripts": _static.EMPTY_DICT,
    "dependencies": _static.EMPTY_LIST,
    "optional-dependencies": _static.EMPTY_DICT,
}


class _MissingDynamic(SetuptoolsWarning):
    _SUMMARY = "`{field}` defined outside of `pyproject.toml` is ignored."

    _DETAILS = """
    The following seems to be defined outside of `pyproject.toml`:

    `{field} = {value!r}`

    According to the spec (see the link below), however, setuptools CANNOT
    consider this value unless `{field}` is listed as `dynamic`.

    https://packaging.python.org/en/latest/specifications/pyproject-toml/#declaring-project-metadata-the-project-table

    To prevent this problem, you can list `{field}` under `dynamic` or alternatively
    remove the `[project]` table from your file and rely entirely on other means of
    configuration.
    """
    # TODO: Consider removing this check in the future?
    #       There is a trade-off here between improving "debug-ability" and the cost
    #       of running/testing/maintaining these unnecessary checks...

    @classmethod
    def details(cls, field: str, value: Any) -> str:
        return cls._DETAILS.format(field=field, value=value)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\indexed_db.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: IndexedDB (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime
from . import storage


@dataclass
class DatabaseWithObjectStores:
    '''
    Database with an array of object stores.
    '''
    #: Database name.
    name: str

    #: Database version (type is not 'integer', as the standard
    #: requires the version number to be 'unsigned long long')
    version: float

    #: Object stores in this database.
    object_stores: typing.List[ObjectStore]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['version'] = self.version
        json['objectStores'] = [i.to_json() for i in self.object_stores]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            version=float(json['version']),
            object_stores=[ObjectStore.from_json(i) for i in json['objectStores']],
        )


@dataclass
class ObjectStore:
    '''
    Object store.
    '''
    #: Object store name.
    name: str

    #: Object store key path.
    key_path: KeyPath

    #: If true, object store has auto increment flag set.
    auto_increment: bool

    #: Indexes in this object store.
    indexes: typing.List[ObjectStoreIndex]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['autoIncrement'] = self.auto_increment
        json['indexes'] = [i.to_json() for i in self.indexes]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            auto_increment=bool(json['autoIncrement']),
            indexes=[ObjectStoreIndex.from_json(i) for i in json['indexes']],
        )


@dataclass
class ObjectStoreIndex:
    '''
    Object store index.
    '''
    #: Index name.
    name: str

    #: Index key path.
    key_path: KeyPath

    #: If true, index is unique.
    unique: bool

    #: If true, index allows multiple entries for a key.
    multi_entry: bool

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['unique'] = self.unique
        json['multiEntry'] = self.multi_entry
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            unique=bool(json['unique']),
            multi_entry=bool(json['multiEntry']),
        )


@dataclass
class Key:
    '''
    Key.
    '''
    #: Key type.
    type_: str

    #: Number value.
    number: typing.Optional[float] = None

    #: String value.
    string: typing.Optional[str] = None

    #: Date value.
    date: typing.Optional[float] = None

    #: Array value.
    array: typing.Optional[typing.List[Key]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.number is not None:
            json['number'] = self.number
        if self.string is not None:
            json['string'] = self.string
        if self.date is not None:
            json['date'] = self.date
        if self.array is not None:
            json['array'] = [i.to_json() for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            number=float(json['number']) if 'number' in json else None,
            string=str(json['string']) if 'string' in json else None,
            date=float(json['date']) if 'date' in json else None,
            array=[Key.from_json(i) for i in json['array']] if 'array' in json else None,
        )


@dataclass
class KeyRange:
    '''
    Key range.
    '''
    #: If true lower bound is open.
    lower_open: bool

    #: If true upper bound is open.
    upper_open: bool

    #: Lower bound.
    lower: typing.Optional[Key] = None

    #: Upper bound.
    upper: typing.Optional[Key] = None

    def to_json(self):
        json = dict()
        json['lowerOpen'] = self.lower_open
        json['upperOpen'] = self.upper_open
        if self.lower is not None:
            json['lower'] = self.lower.to_json()
        if self.upper is not None:
            json['upper'] = self.upper.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lower_open=bool(json['lowerOpen']),
            upper_open=bool(json['upperOpen']),
            lower=Key.from_json(json['lower']) if 'lower' in json else None,
            upper=Key.from_json(json['upper']) if 'upper' in json else None,
        )


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Key object.
    key: runtime.RemoteObject

    #: Primary key object.
    primary_key: runtime.RemoteObject

    #: Value object.
    value: runtime.RemoteObject

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['primaryKey'] = self.primary_key.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=runtime.RemoteObject.from_json(json['key']),
            primary_key=runtime.RemoteObject.from_json(json['primaryKey']),
            value=runtime.RemoteObject.from_json(json['value']),
        )


@dataclass
class KeyPath:
    '''
    Key path.
    '''
    #: Key path type.
    type_: str

    #: String value.
    string: typing.Optional[str] = None

    #: Array value.
    array: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.string is not None:
            json['string'] = self.string
        if self.array is not None:
            json['array'] = [i for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            string=str(json['string']) if 'string' in json else None,
            array=[str(i) for i in json['array']] if 'array' in json else None,
        )


def clear_object_store(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries from an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.clearObjectStore',
        'params': params,
    }
    json = yield cmd_dict


def delete_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a database.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteDatabase',
        'params': params,
    }
    json = yield cmd_dict


def delete_object_store_entries(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        key_range: KeyRange = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Delete a range of entries from an object store

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name:
    :param object_store_name:
    :param key_range: Range of entry keys to delete
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteObjectStoreEntries',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.enable',
    }
    json = yield cmd_dict


def request_data(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        index_name: str = None,
        skip_count: int = None,
        page_size: int = None,
        key_range: typing.Optional[KeyRange] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], bool]]:
    '''
    Requests data from object store or index.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :param index_name: Index name, empty string for object store data requests.
    :param skip_count: Number of records to skip.
    :param page_size: Number of records to fetch.
    :param key_range: *(Optional)* Key range.
    :returns: A tuple with the following items:

        0. **objectStoreDataEntries** - Array of object store data entries.
        1. **hasMore** - If true, there are more entries to fetch in the given range.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['indexName'] = index_name
    params['skipCount'] = skip_count
    params['pageSize'] = page_size
    if key_range is not None:
        params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestData',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['objectStoreDataEntries']],
        bool(json['hasMore'])
    )


def get_metadata(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float]]:
    '''
    Gets metadata of an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :returns: A tuple with the following items:

        0. **entriesCount** - the entries count
        1. **keyGeneratorValue** - the current value of key generator, to become the next inserted key into the object store. Valid if objectStore.autoIncrement is true.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.getMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['entriesCount']),
        float(json['keyGeneratorValue'])
    )


def request_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,DatabaseWithObjectStores]:
    '''
    Requests database with given name in given frame.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :returns: Database with an array of object stores.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabase',
        'params': params,
    }
    json = yield cmd_dict
    return DatabaseWithObjectStores.from_json(json['databaseWithObjectStores'])


def request_database_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Requests database names for given security origin.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Database names for origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabaseNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['databaseNames']]

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\indexed_db.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: IndexedDB (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime
from . import storage


@dataclass
class DatabaseWithObjectStores:
    '''
    Database with an array of object stores.
    '''
    #: Database name.
    name: str

    #: Database version (type is not 'integer', as the standard
    #: requires the version number to be 'unsigned long long')
    version: float

    #: Object stores in this database.
    object_stores: typing.List[ObjectStore]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['version'] = self.version
        json['objectStores'] = [i.to_json() for i in self.object_stores]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            version=float(json['version']),
            object_stores=[ObjectStore.from_json(i) for i in json['objectStores']],
        )


@dataclass
class ObjectStore:
    '''
    Object store.
    '''
    #: Object store name.
    name: str

    #: Object store key path.
    key_path: KeyPath

    #: If true, object store has auto increment flag set.
    auto_increment: bool

    #: Indexes in this object store.
    indexes: typing.List[ObjectStoreIndex]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['autoIncrement'] = self.auto_increment
        json['indexes'] = [i.to_json() for i in self.indexes]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            auto_increment=bool(json['autoIncrement']),
            indexes=[ObjectStoreIndex.from_json(i) for i in json['indexes']],
        )


@dataclass
class ObjectStoreIndex:
    '''
    Object store index.
    '''
    #: Index name.
    name: str

    #: Index key path.
    key_path: KeyPath

    #: If true, index is unique.
    unique: bool

    #: If true, index allows multiple entries for a key.
    multi_entry: bool

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['unique'] = self.unique
        json['multiEntry'] = self.multi_entry
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            unique=bool(json['unique']),
            multi_entry=bool(json['multiEntry']),
        )


@dataclass
class Key:
    '''
    Key.
    '''
    #: Key type.
    type_: str

    #: Number value.
    number: typing.Optional[float] = None

    #: String value.
    string: typing.Optional[str] = None

    #: Date value.
    date: typing.Optional[float] = None

    #: Array value.
    array: typing.Optional[typing.List[Key]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.number is not None:
            json['number'] = self.number
        if self.string is not None:
            json['string'] = self.string
        if self.date is not None:
            json['date'] = self.date
        if self.array is not None:
            json['array'] = [i.to_json() for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            number=float(json['number']) if 'number' in json else None,
            string=str(json['string']) if 'string' in json else None,
            date=float(json['date']) if 'date' in json else None,
            array=[Key.from_json(i) for i in json['array']] if 'array' in json else None,
        )


@dataclass
class KeyRange:
    '''
    Key range.
    '''
    #: If true lower bound is open.
    lower_open: bool

    #: If true upper bound is open.
    upper_open: bool

    #: Lower bound.
    lower: typing.Optional[Key] = None

    #: Upper bound.
    upper: typing.Optional[Key] = None

    def to_json(self):
        json = dict()
        json['lowerOpen'] = self.lower_open
        json['upperOpen'] = self.upper_open
        if self.lower is not None:
            json['lower'] = self.lower.to_json()
        if self.upper is not None:
            json['upper'] = self.upper.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lower_open=bool(json['lowerOpen']),
            upper_open=bool(json['upperOpen']),
            lower=Key.from_json(json['lower']) if 'lower' in json else None,
            upper=Key.from_json(json['upper']) if 'upper' in json else None,
        )


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Key object.
    key: runtime.RemoteObject

    #: Primary key object.
    primary_key: runtime.RemoteObject

    #: Value object.
    value: runtime.RemoteObject

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['primaryKey'] = self.primary_key.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=runtime.RemoteObject.from_json(json['key']),
            primary_key=runtime.RemoteObject.from_json(json['primaryKey']),
            value=runtime.RemoteObject.from_json(json['value']),
        )


@dataclass
class KeyPath:
    '''
    Key path.
    '''
    #: Key path type.
    type_: str

    #: String value.
    string: typing.Optional[str] = None

    #: Array value.
    array: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.string is not None:
            json['string'] = self.string
        if self.array is not None:
            json['array'] = [i for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            string=str(json['string']) if 'string' in json else None,
            array=[str(i) for i in json['array']] if 'array' in json else None,
        )


def clear_object_store(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries from an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.clearObjectStore',
        'params': params,
    }
    json = yield cmd_dict


def delete_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a database.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteDatabase',
        'params': params,
    }
    json = yield cmd_dict


def delete_object_store_entries(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        key_range: KeyRange = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Delete a range of entries from an object store

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name:
    :param object_store_name:
    :param key_range: Range of entry keys to delete
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteObjectStoreEntries',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.enable',
    }
    json = yield cmd_dict


def request_data(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        index_name: str = None,
        skip_count: int = None,
        page_size: int = None,
        key_range: typing.Optional[KeyRange] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], bool]]:
    '''
    Requests data from object store or index.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :param index_name: Index name, empty string for object store data requests.
    :param skip_count: Number of records to skip.
    :param page_size: Number of records to fetch.
    :param key_range: *(Optional)* Key range.
    :returns: A tuple with the following items:

        0. **objectStoreDataEntries** - Array of object store data entries.
        1. **hasMore** - If true, there are more entries to fetch in the given range.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['indexName'] = index_name
    params['skipCount'] = skip_count
    params['pageSize'] = page_size
    if key_range is not None:
        params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestData',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['objectStoreDataEntries']],
        bool(json['hasMore'])
    )


def get_metadata(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float]]:
    '''
    Gets metadata of an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :returns: A tuple with the following items:

        0. **entriesCount** - the entries count
        1. **keyGeneratorValue** - the current value of key generator, to become the next inserted key into the object store. Valid if objectStore.autoIncrement is true.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.getMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['entriesCount']),
        float(json['keyGeneratorValue'])
    )


def request_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,DatabaseWithObjectStores]:
    '''
    Requests database with given name in given frame.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :returns: Database with an array of object stores.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabase',
        'params': params,
    }
    json = yield cmd_dict
    return DatabaseWithObjectStores.from_json(json['databaseWithObjectStores'])


def request_database_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Requests database names for given security origin.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Database names for origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabaseNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['databaseNames']]

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\indexed_db.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: IndexedDB (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import runtime
from . import storage


@dataclass
class DatabaseWithObjectStores:
    '''
    Database with an array of object stores.
    '''
    #: Database name.
    name: str

    #: Database version (type is not 'integer', as the standard
    #: requires the version number to be 'unsigned long long')
    version: float

    #: Object stores in this database.
    object_stores: typing.List[ObjectStore]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['version'] = self.version
        json['objectStores'] = [i.to_json() for i in self.object_stores]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            version=float(json['version']),
            object_stores=[ObjectStore.from_json(i) for i in json['objectStores']],
        )


@dataclass
class ObjectStore:
    '''
    Object store.
    '''
    #: Object store name.
    name: str

    #: Object store key path.
    key_path: KeyPath

    #: If true, object store has auto increment flag set.
    auto_increment: bool

    #: Indexes in this object store.
    indexes: typing.List[ObjectStoreIndex]

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['autoIncrement'] = self.auto_increment
        json['indexes'] = [i.to_json() for i in self.indexes]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            auto_increment=bool(json['autoIncrement']),
            indexes=[ObjectStoreIndex.from_json(i) for i in json['indexes']],
        )


@dataclass
class ObjectStoreIndex:
    '''
    Object store index.
    '''
    #: Index name.
    name: str

    #: Index key path.
    key_path: KeyPath

    #: If true, index is unique.
    unique: bool

    #: If true, index allows multiple entries for a key.
    multi_entry: bool

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['keyPath'] = self.key_path.to_json()
        json['unique'] = self.unique
        json['multiEntry'] = self.multi_entry
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            key_path=KeyPath.from_json(json['keyPath']),
            unique=bool(json['unique']),
            multi_entry=bool(json['multiEntry']),
        )


@dataclass
class Key:
    '''
    Key.
    '''
    #: Key type.
    type_: str

    #: Number value.
    number: typing.Optional[float] = None

    #: String value.
    string: typing.Optional[str] = None

    #: Date value.
    date: typing.Optional[float] = None

    #: Array value.
    array: typing.Optional[typing.List[Key]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.number is not None:
            json['number'] = self.number
        if self.string is not None:
            json['string'] = self.string
        if self.date is not None:
            json['date'] = self.date
        if self.array is not None:
            json['array'] = [i.to_json() for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            number=float(json['number']) if 'number' in json else None,
            string=str(json['string']) if 'string' in json else None,
            date=float(json['date']) if 'date' in json else None,
            array=[Key.from_json(i) for i in json['array']] if 'array' in json else None,
        )


@dataclass
class KeyRange:
    '''
    Key range.
    '''
    #: If true lower bound is open.
    lower_open: bool

    #: If true upper bound is open.
    upper_open: bool

    #: Lower bound.
    lower: typing.Optional[Key] = None

    #: Upper bound.
    upper: typing.Optional[Key] = None

    def to_json(self):
        json = dict()
        json['lowerOpen'] = self.lower_open
        json['upperOpen'] = self.upper_open
        if self.lower is not None:
            json['lower'] = self.lower.to_json()
        if self.upper is not None:
            json['upper'] = self.upper.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            lower_open=bool(json['lowerOpen']),
            upper_open=bool(json['upperOpen']),
            lower=Key.from_json(json['lower']) if 'lower' in json else None,
            upper=Key.from_json(json['upper']) if 'upper' in json else None,
        )


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Key object.
    key: runtime.RemoteObject

    #: Primary key object.
    primary_key: runtime.RemoteObject

    #: Value object.
    value: runtime.RemoteObject

    def to_json(self):
        json = dict()
        json['key'] = self.key.to_json()
        json['primaryKey'] = self.primary_key.to_json()
        json['value'] = self.value.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=runtime.RemoteObject.from_json(json['key']),
            primary_key=runtime.RemoteObject.from_json(json['primaryKey']),
            value=runtime.RemoteObject.from_json(json['value']),
        )


@dataclass
class KeyPath:
    '''
    Key path.
    '''
    #: Key path type.
    type_: str

    #: String value.
    string: typing.Optional[str] = None

    #: Array value.
    array: typing.Optional[typing.List[str]] = None

    def to_json(self):
        json = dict()
        json['type'] = self.type_
        if self.string is not None:
            json['string'] = self.string
        if self.array is not None:
            json['array'] = [i for i in self.array]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            type_=str(json['type']),
            string=str(json['string']) if 'string' in json else None,
            array=[str(i) for i in json['array']] if 'array' in json else None,
        )


def clear_object_store(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Clears all entries from an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.clearObjectStore',
        'params': params,
    }
    json = yield cmd_dict


def delete_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a database.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteDatabase',
        'params': params,
    }
    json = yield cmd_dict


def delete_object_store_entries(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        key_range: KeyRange = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Delete a range of entries from an object store

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name:
    :param object_store_name:
    :param key_range: Range of entry keys to delete
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.deleteObjectStoreEntries',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables events from backend.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.enable',
    }
    json = yield cmd_dict


def request_data(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None,
        index_name: str = None,
        skip_count: int = None,
        page_size: int = None,
        key_range: typing.Optional[KeyRange] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], bool]]:
    '''
    Requests data from object store or index.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :param index_name: Index name, empty string for object store data requests.
    :param skip_count: Number of records to skip.
    :param page_size: Number of records to fetch.
    :param key_range: *(Optional)* Key range.
    :returns: A tuple with the following items:

        0. **objectStoreDataEntries** - Array of object store data entries.
        1. **hasMore** - If true, there are more entries to fetch in the given range.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    params['indexName'] = index_name
    params['skipCount'] = skip_count
    params['pageSize'] = page_size
    if key_range is not None:
        params['keyRange'] = key_range.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestData',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['objectStoreDataEntries']],
        bool(json['hasMore'])
    )


def get_metadata(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None,
        object_store_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[float, float]]:
    '''
    Gets metadata of an object store.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :param object_store_name: Object store name.
    :returns: A tuple with the following items:

        0. **entriesCount** - the entries count
        1. **keyGeneratorValue** - the current value of key generator, to become the next inserted key into the object store. Valid if objectStore.autoIncrement is true.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    params['objectStoreName'] = object_store_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.getMetadata',
        'params': params,
    }
    json = yield cmd_dict
    return (
        float(json['entriesCount']),
        float(json['keyGeneratorValue'])
    )


def request_database(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None,
        database_name: str = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,DatabaseWithObjectStores]:
    '''
    Requests database with given name in given frame.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :param database_name: Database name.
    :returns: Database with an array of object stores.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    params['databaseName'] = database_name
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabase',
        'params': params,
    }
    json = yield cmd_dict
    return DatabaseWithObjectStores.from_json(json['databaseWithObjectStores'])


def request_database_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[str]]:
    '''
    Requests database names for given security origin.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, or storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Database names for origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'IndexedDB.requestDatabaseNames',
        'params': params,
    }
    json = yield cmd_dict
    return [str(i) for i in json['databaseNames']]

# === NexusCore/openenv\Lib\site-packages\nltk\toolbox.py ===
# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating
Toolbox databases and settings files.
"""

import codecs
import re
from io import StringIO
from xml.etree.ElementTree import Element, ElementTree, SubElement, TreeBuilder

from nltk.data import PathPointer, find


class StandardFormat:
    """
    Class for reading and processing standard format marker files and strings.
    """

    def __init__(self, filename=None, encoding=None):
        self._encoding = encoding
        if filename is not None:
            self.open(filename)

    def open(self, sfm_file):
        """
        Open a standard format marker file for sequential reading.

        :param sfm_file: name of the standard format marker input file
        :type sfm_file: str
        """
        if isinstance(sfm_file, PathPointer):
            self._file = sfm_file.open(self._encoding)
        else:
            self._file = codecs.open(sfm_file, "r", self._encoding)

    def open_string(self, s):
        """
        Open a standard format marker string for sequential reading.

        :param s: string to parse as a standard format marker input file
        :type s: str
        """
        self._file = StringIO(s)

    def raw_fields(self):
        """
        Return an iterator that returns the next field in a (marker, value)
        tuple. Linebreaks and trailing white space are preserved except
        for the final newline in each field.

        :rtype: iter(tuple(str, str))
        """
        join_string = "\n"
        line_regexp = r"^%s(?:\\(\S+)\s*)?(.*)$"
        # discard a BOM in the first line
        first_line_pat = re.compile(line_regexp % "(?:\xef\xbb\xbf)?")
        line_pat = re.compile(line_regexp % "")
        # need to get first line outside the loop for correct handling
        # of the first marker if it spans multiple lines
        file_iter = iter(self._file)
        # PEP 479, prevent RuntimeError when StopIteration is raised inside generator
        try:
            line = next(file_iter)
        except StopIteration:
            # no more data is available, terminate the generator
            return
        mobj = re.match(first_line_pat, line)
        mkr, line_value = mobj.groups()
        value_lines = [line_value]
        self.line_num = 0
        for line in file_iter:
            self.line_num += 1
            mobj = re.match(line_pat, line)
            line_mkr, line_value = mobj.groups()
            if line_mkr:
                yield (mkr, join_string.join(value_lines))
                mkr = line_mkr
                value_lines = [line_value]
            else:
                value_lines.append(line_value)
        self.line_num += 1
        yield (mkr, join_string.join(value_lines))

    def fields(
        self,
        strip=True,
        unwrap=True,
        encoding=None,
        errors="strict",
        unicode_fields=None,
    ):
        """
        Return an iterator that returns the next field in a ``(marker, value)``
        tuple, where ``marker`` and ``value`` are unicode strings if an ``encoding``
        was specified in the ``fields()`` method. Otherwise they are non-unicode strings.

        :param strip: strip trailing whitespace from the last line of each field
        :type strip: bool
        :param unwrap: Convert newlines in a field to spaces.
        :type unwrap: bool
        :param encoding: Name of an encoding to use. If it is specified then
            the ``fields()`` method returns unicode strings rather than non
            unicode strings.
        :type encoding: str or None
        :param errors: Error handling scheme for codec. Same as the ``decode()``
            builtin string method.
        :type errors: str
        :param unicode_fields: Set of marker names whose values are UTF-8 encoded.
            Ignored if encoding is None. If the whole file is UTF-8 encoded set
            ``encoding='utf8'`` and leave ``unicode_fields`` with its default
            value of None.
        :type unicode_fields: sequence
        :rtype: iter(tuple(str, str))
        """
        if encoding is None and unicode_fields is not None:
            raise ValueError("unicode_fields is set but not encoding.")
        unwrap_pat = re.compile(r"\n+")
        for mkr, val in self.raw_fields():
            if unwrap:
                val = unwrap_pat.sub(" ", val)
            if strip:
                val = val.rstrip()
            yield (mkr, val)

    def close(self):
        """Close a previously opened standard format marker file or string."""
        self._file.close()
        try:
            del self.line_num
        except AttributeError:
            pass


class ToolboxData(StandardFormat):
    def parse(self, grammar=None, **kwargs):
        if grammar:
            return self._chunk_parse(grammar=grammar, **kwargs)
        else:
            return self._record_parse(**kwargs)

    def _record_parse(self, key=None, **kwargs):
        r"""
        Returns an element tree structure corresponding to a toolbox data file with
        all markers at the same level.

        Thus the following Toolbox database::
            \_sh v3.0  400  Rotokas Dictionary
            \_DateStampHasFourDigitYear

            \lx kaa
            \ps V.A
            \ge gag
            \gp nek i pas

            \lx kaa
            \ps V.B
            \ge strangle
            \gp pasim nek

        after parsing will end up with the same structure (ignoring the extra
        whitespace) as the following XML fragment after being parsed by
        ElementTree::
            <toolbox_data>
                <header>
                    <_sh>v3.0  400  Rotokas Dictionary</_sh>
                    <_DateStampHasFourDigitYear/>
                </header>

                <record>
                    <lx>kaa</lx>
                    <ps>V.A</ps>
                    <ge>gag</ge>
                    <gp>nek i pas</gp>
                </record>

                <record>
                    <lx>kaa</lx>
                    <ps>V.B</ps>
                    <ge>strangle</ge>
                    <gp>pasim nek</gp>
                </record>
            </toolbox_data>

        :param key: Name of key marker at the start of each record. If set to
            None (the default value) the first marker that doesn't begin with
            an underscore is assumed to be the key.
        :type key: str
        :param kwargs: Keyword arguments passed to ``StandardFormat.fields()``
        :type kwargs: dict
        :rtype: ElementTree._ElementInterface
        :return: contents of toolbox data divided into header and records
        """
        builder = TreeBuilder()
        builder.start("toolbox_data", {})
        builder.start("header", {})
        in_records = False
        for mkr, value in self.fields(**kwargs):
            if key is None and not in_records and mkr[0] != "_":
                key = mkr
            if mkr == key:
                if in_records:
                    builder.end("record")
                else:
                    builder.end("header")
                    in_records = True
                builder.start("record", {})
            builder.start(mkr, {})
            builder.data(value)
            builder.end(mkr)
        if in_records:
            builder.end("record")
        else:
            builder.end("header")
        builder.end("toolbox_data")
        return builder.close()

    def _tree2etree(self, parent):
        from nltk.tree import Tree

        root = Element(parent.label())
        for child in parent:
            if isinstance(child, Tree):
                root.append(self._tree2etree(child))
            else:
                text, tag = child
                e = SubElement(root, tag)
                e.text = text
        return root

    def _chunk_parse(self, grammar=None, root_label="record", trace=0, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file
        parsed according to the chunk grammar.

        :type grammar: str
        :param grammar: Contains the chunking rules used to parse the
            database.  See ``chunk.RegExp`` for documentation.
        :type root_label: str
        :param root_label: The node value that should be used for the
            top node of the chunk structure.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.
        :type kwargs: dict
        :param kwargs: Keyword arguments passed to ``toolbox.StandardFormat.fields()``
        :rtype: ElementTree._ElementInterface
        """
        from nltk import chunk
        from nltk.tree import Tree

        cp = chunk.RegexpParser(grammar, root_label=root_label, trace=trace)
        db = self.parse(**kwargs)
        tb_etree = Element("toolbox_data")
        header = db.find("header")
        tb_etree.append(header)
        for record in db.findall("record"):
            parsed = cp.parse([(elem.text, elem.tag) for elem in record])
            tb_etree.append(self._tree2etree(parsed))
        return tb_etree


_is_value = re.compile(r"\S")


def to_sfm_string(tree, encoding=None, errors="strict", unicode_fields=None):
    """
    Return a string with a standard format representation of the toolbox
    data in tree (tree can be a toolbox database or a single record).

    :param tree: flat representation of toolbox data (whole database or single record)
    :type tree: ElementTree._ElementInterface
    :param encoding: Name of an encoding to use.
    :type encoding: str
    :param errors: Error handling scheme for codec. Same as the ``encode()``
        builtin string method.
    :type errors: str
    :param unicode_fields:
    :type unicode_fields: dict(str) or set(str)
    :rtype: str
    """
    if tree.tag == "record":
        root = Element("toolbox_data")
        root.append(tree)
        tree = root

    if tree.tag != "toolbox_data":
        raise ValueError("not a toolbox_data element structure")
    if encoding is None and unicode_fields is not None:
        raise ValueError(
            "if encoding is not specified then neither should unicode_fields"
        )
    l = []
    for rec in tree:
        l.append("\n")
        for field in rec:
            mkr = field.tag
            value = field.text
            if encoding is not None:
                if unicode_fields is not None and mkr in unicode_fields:
                    cur_encoding = "utf8"
                else:
                    cur_encoding = encoding
                if re.search(_is_value, value):
                    l.append((f"\\{mkr} {value}\n").encode(cur_encoding, errors))
                else:
                    l.append((f"\\{mkr}{value}\n").encode(cur_encoding, errors))
            else:
                if re.search(_is_value, value):
                    l.append(f"\\{mkr} {value}\n")
                else:
                    l.append(f"\\{mkr}{value}\n")
    return "".join(l[1:])


class ToolboxSettings(StandardFormat):
    """This class is the base class for settings files."""

    def __init__(self):
        super().__init__()

    def parse(self, encoding=None, errors="strict", **kwargs):
        """
        Return the contents of toolbox settings file with a nested structure.

        :param encoding: encoding used by settings file
        :type encoding: str
        :param errors: Error handling scheme for codec. Same as ``decode()`` builtin method.
        :type errors: str
        :param kwargs: Keyword arguments passed to ``StandardFormat.fields()``
        :type kwargs: dict
        :rtype: ElementTree._ElementInterface
        """
        builder = TreeBuilder()
        for mkr, value in self.fields(encoding=encoding, errors=errors, **kwargs):
            # Check whether the first char of the field marker
            # indicates a block start (+) or end (-)
            block = mkr[0]
            if block in ("+", "-"):
                mkr = mkr[1:]
            else:
                block = None
            # Build tree on the basis of block char
            if block == "+":
                builder.start(mkr, {})
                builder.data(value)
            elif block == "-":
                builder.end(mkr)
            else:
                builder.start(mkr, {})
                builder.data(value)
                builder.end(mkr)
        return builder.close()


def to_settings_string(tree, encoding=None, errors="strict", unicode_fields=None):
    # write XML to file
    l = list()
    _to_settings_string(
        tree.getroot(),
        l,
        encoding=encoding,
        errors=errors,
        unicode_fields=unicode_fields,
    )
    return "".join(l)


def _to_settings_string(node, l, **kwargs):
    # write XML to file
    tag = node.tag
    text = node.text
    if len(node) == 0:
        if text:
            l.append(f"\\{tag} {text}\n")
        else:
            l.append("\\%s\n" % tag)
    else:
        if text:
            l.append(f"\\+{tag} {text}\n")
        else:
            l.append("\\+%s\n" % tag)
        for n in node:
            _to_settings_string(n, l, **kwargs)
        l.append("\\-%s\n" % tag)
    return


def remove_blanks(elem):
    """
    Remove all elements and subelements with no text and no child elements.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    """
    out = list()
    for child in elem:
        remove_blanks(child)
        if child.text or len(child) > 0:
            out.append(child)
    elem[:] = out


def add_default_fields(elem, default_fields):
    """
    Add blank elements and subelements specified in default_fields.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param default_fields: fields to add to each type of element and subelement
    :type default_fields: dict(tuple)
    """
    for field in default_fields.get(elem.tag, []):
        if elem.find(field) is None:
            SubElement(elem, field)
    for child in elem:
        add_default_fields(child, default_fields)


def sort_fields(elem, field_orders):
    """
    Sort the elements and subelements in order specified in field_orders.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param field_orders: order of fields for each type of element and subelement
    :type field_orders: dict(tuple)
    """
    order_dicts = dict()
    for field, order in field_orders.items():
        order_dicts[field] = order_key = dict()
        for i, subfield in enumerate(order):
            order_key[subfield] = i
    _sort_fields(elem, order_dicts)


def _sort_fields(elem, orders_dicts):
    """sort the children of elem"""
    try:
        order = orders_dicts[elem.tag]
    except KeyError:
        pass
    else:
        tmp = sorted(
            ((order.get(child.tag, 1e9), i), child) for i, child in enumerate(elem)
        )
        elem[:] = [child for key, child in tmp]
    for child in elem:
        if len(child):
            _sort_fields(child, orders_dicts)


def add_blank_lines(tree, blanks_before, blanks_between):
    """
    Add blank lines before all elements and subelements specified in blank_before.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param blank_before: elements and subelements to add blank lines before
    :type blank_before: dict(tuple)
    """
    try:
        before = blanks_before[tree.tag]
        between = blanks_between[tree.tag]
    except KeyError:
        for elem in tree:
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
    else:
        last_elem = None
        for elem in tree:
            tag = elem.tag
            if last_elem is not None and last_elem.tag != tag:
                if tag in before and last_elem is not None:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            else:
                if tag in between:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
            last_elem = elem


def demo():
    from itertools import islice

    #    zip_path = find('corpora/toolbox.zip')
    #    lexicon = ToolboxData(ZipFilePathPointer(zip_path, 'toolbox/rotokas.dic')).parse()
    file_path = find("corpora/toolbox/rotokas.dic")
    lexicon = ToolboxData(file_path).parse()
    print("first field in fourth record:")
    print(lexicon[3][0].tag)
    print(lexicon[3][0].text)

    print("\nfields in sequential order:")
    for field in islice(lexicon.find("record"), 10):
        print(field.tag, field.text)

    print("\nlx fields:")
    for field in islice(lexicon.findall("record/lx"), 10):
        print(field.text)

    settings = ToolboxSettings()
    file_path = find("corpora/toolbox/MDF/MDF_AltH.typ")
    settings.open(file_path)
    #    settings.open(ZipFilePathPointer(zip_path, entry='toolbox/MDF/MDF_AltH.typ'))
    tree = settings.parse(unwrap=False, encoding="cp1252")
    print(tree.find("expset/expMDF/rtfPageSetup/paperSize").text)
    settings_tree = ElementTree(tree)
    print(to_settings_string(settings_tree).encode("utf8"))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\urllib3\util\ssl_.py ===
from __future__ import annotations

import hashlib
import hmac
import os
import socket
import sys
import typing
import warnings
from binascii import unhexlify

from ..exceptions import ProxySchemeUnsupported, SSLError
from .url import _BRACELESS_IPV6_ADDRZ_RE, _IPV4_RE

SSLContext = None
SSLTransport = None
HAS_NEVER_CHECK_COMMON_NAME = False
IS_PYOPENSSL = False
ALPN_PROTOCOLS = ["http/1.1"]

_TYPE_VERSION_INFO = tuple[int, int, int, str, int]

# Maps the length of a digest to a possible hash function producing this digest
HASHFUNC_MAP = {
    length: getattr(hashlib, algorithm, None)
    for length, algorithm in ((32, "md5"), (40, "sha1"), (64, "sha256"))
}


def _is_bpo_43522_fixed(
    implementation_name: str,
    version_info: _TYPE_VERSION_INFO,
    pypy_version_info: _TYPE_VERSION_INFO | None,
) -> bool:
    """Return True for CPython 3.9.3+ or 3.10+ and PyPy 7.3.8+ where
    setting SSLContext.hostname_checks_common_name to False works.

    Outside of CPython and PyPy we don't know which implementations work
    or not so we conservatively use our hostname matching as we know that works
    on all implementations.

    https://github.com/urllib3/urllib3/issues/2192#issuecomment-821832963
    https://foss.heptapod.net/pypy/pypy/-/issues/3539
    """
    if implementation_name == "pypy":
        # https://foss.heptapod.net/pypy/pypy/-/issues/3129
        return pypy_version_info >= (7, 3, 8)  # type: ignore[operator]
    elif implementation_name == "cpython":
        major_minor = version_info[:2]
        micro = version_info[2]
        return (major_minor == (3, 9) and micro >= 3) or major_minor >= (3, 10)
    else:  # Defensive:
        return False


def _is_has_never_check_common_name_reliable(
    openssl_version: str,
    openssl_version_number: int,
    implementation_name: str,
    version_info: _TYPE_VERSION_INFO,
    pypy_version_info: _TYPE_VERSION_INFO | None,
) -> bool:
    # As of May 2023, all released versions of LibreSSL fail to reject certificates with
    # only common names, see https://github.com/urllib3/urllib3/pull/3024
    is_openssl = openssl_version.startswith("OpenSSL ")
    # Before fixing OpenSSL issue #14579, the SSL_new() API was not copying hostflags
    # like X509_CHECK_FLAG_NEVER_CHECK_SUBJECT, which tripped up CPython.
    # https://github.com/openssl/openssl/issues/14579
    # This was released in OpenSSL 1.1.1l+ (>=0x101010cf)
    is_openssl_issue_14579_fixed = openssl_version_number >= 0x101010CF

    return is_openssl and (
        is_openssl_issue_14579_fixed
        or _is_bpo_43522_fixed(implementation_name, version_info, pypy_version_info)
    )


if typing.TYPE_CHECKING:
    from ssl import VerifyMode
    from typing import TypedDict

    from .ssltransport import SSLTransport as SSLTransportType

    class _TYPE_PEER_CERT_RET_DICT(TypedDict, total=False):
        subjectAltName: tuple[tuple[str, str], ...]
        subject: tuple[tuple[tuple[str, str], ...], ...]
        serialNumber: str


# Mapping from 'ssl.PROTOCOL_TLSX' to 'TLSVersion.X'
_SSL_VERSION_TO_TLS_VERSION: dict[int, int] = {}

try:  # Do we have ssl at all?
    import ssl
    from ssl import (  # type: ignore[assignment]
        CERT_REQUIRED,
        HAS_NEVER_CHECK_COMMON_NAME,
        OP_NO_COMPRESSION,
        OP_NO_TICKET,
        OPENSSL_VERSION,
        OPENSSL_VERSION_NUMBER,
        PROTOCOL_TLS,
        PROTOCOL_TLS_CLIENT,
        VERIFY_X509_STRICT,
        OP_NO_SSLv2,
        OP_NO_SSLv3,
        SSLContext,
        TLSVersion,
    )

    PROTOCOL_SSLv23 = PROTOCOL_TLS

    # Needed for Python 3.9 which does not define this
    VERIFY_X509_PARTIAL_CHAIN = getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0x80000)

    # Setting SSLContext.hostname_checks_common_name = False didn't work before CPython
    # 3.9.3, and 3.10 (but OK on PyPy) or OpenSSL 1.1.1l+
    if HAS_NEVER_CHECK_COMMON_NAME and not _is_has_never_check_common_name_reliable(
        OPENSSL_VERSION,
        OPENSSL_VERSION_NUMBER,
        sys.implementation.name,
        sys.version_info,
        sys.pypy_version_info if sys.implementation.name == "pypy" else None,  # type: ignore[attr-defined]
    ):  # Defensive: for Python < 3.9.3
        HAS_NEVER_CHECK_COMMON_NAME = False

    # Need to be careful here in case old TLS versions get
    # removed in future 'ssl' module implementations.
    for attr in ("TLSv1", "TLSv1_1", "TLSv1_2"):
        try:
            _SSL_VERSION_TO_TLS_VERSION[getattr(ssl, f"PROTOCOL_{attr}")] = getattr(
                TLSVersion, attr
            )
        except AttributeError:  # Defensive:
            continue

    from .ssltransport import SSLTransport  # type: ignore[assignment]
except ImportError:
    OP_NO_COMPRESSION = 0x20000  # type: ignore[assignment]
    OP_NO_TICKET = 0x4000  # type: ignore[assignment]
    OP_NO_SSLv2 = 0x1000000  # type: ignore[assignment]
    OP_NO_SSLv3 = 0x2000000  # type: ignore[assignment]
    PROTOCOL_SSLv23 = PROTOCOL_TLS = 2  # type: ignore[assignment]
    PROTOCOL_TLS_CLIENT = 16  # type: ignore[assignment]
    VERIFY_X509_PARTIAL_CHAIN = 0x80000
    VERIFY_X509_STRICT = 0x20  # type: ignore[assignment]


_TYPE_PEER_CERT_RET = typing.Union["_TYPE_PEER_CERT_RET_DICT", bytes, None]


def assert_fingerprint(cert: bytes | None, fingerprint: str) -> None:
    """
    Checks if given fingerprint matches the supplied certificate.

    :param cert:
        Certificate as bytes object.
    :param fingerprint:
        Fingerprint as string of hexdigits, can be interspersed by colons.
    """

    if cert is None:
        raise SSLError("No certificate for the peer.")

    fingerprint = fingerprint.replace(":", "").lower()
    digest_length = len(fingerprint)
    if digest_length not in HASHFUNC_MAP:
        raise SSLError(f"Fingerprint of invalid length: {fingerprint}")
    hashfunc = HASHFUNC_MAP.get(digest_length)
    if hashfunc is None:
        raise SSLError(
            f"Hash function implementation unavailable for fingerprint length: {digest_length}"
        )

    # We need encode() here for py32; works on py2 and p33.
    fingerprint_bytes = unhexlify(fingerprint.encode())

    cert_digest = hashfunc(cert).digest()

    if not hmac.compare_digest(cert_digest, fingerprint_bytes):
        raise SSLError(
            f'Fingerprints did not match. Expected "{fingerprint}", got "{cert_digest.hex()}"'
        )


def resolve_cert_reqs(candidate: None | int | str) -> VerifyMode:
    """
    Resolves the argument to a numeric constant, which can be passed to
    the wrap_socket function/method from the ssl module.
    Defaults to :data:`ssl.CERT_REQUIRED`.
    If given a string it is assumed to be the name of the constant in the
    :mod:`ssl` module or its abbreviation.
    (So you can specify `REQUIRED` instead of `CERT_REQUIRED`.
    If it's neither `None` nor a string we assume it is already the numeric
    constant which can directly be passed to wrap_socket.
    """
    if candidate is None:
        return CERT_REQUIRED

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "CERT_" + candidate)
        return res  # type: ignore[no-any-return]

    return candidate  # type: ignore[return-value]


def resolve_ssl_version(candidate: None | int | str) -> int:
    """
    like resolve_cert_reqs
    """
    if candidate is None:
        return PROTOCOL_TLS

    if isinstance(candidate, str):
        res = getattr(ssl, candidate, None)
        if res is None:
            res = getattr(ssl, "PROTOCOL_" + candidate)
        return typing.cast(int, res)

    return candidate


def create_urllib3_context(
    ssl_version: int | None = None,
    cert_reqs: int | None = None,
    options: int | None = None,
    ciphers: str | None = None,
    ssl_minimum_version: int | None = None,
    ssl_maximum_version: int | None = None,
    verify_flags: int | None = None,
) -> ssl.SSLContext:
    """Creates and configures an :class:`ssl.SSLContext` instance for use with urllib3.

    :param ssl_version:
        The desired protocol version to use. This will default to
        PROTOCOL_SSLv23 which will negotiate the highest protocol that both
        the server and your installation of OpenSSL support.

        This parameter is deprecated instead use 'ssl_minimum_version'.
    :param ssl_minimum_version:
        The minimum version of TLS to be used. Use the 'ssl.TLSVersion' enum for specifying the value.
    :param ssl_maximum_version:
        The maximum version of TLS to be used. Use the 'ssl.TLSVersion' enum for specifying the value.
        Not recommended to set to anything other than 'ssl.TLSVersion.MAXIMUM_SUPPORTED' which is the
        default value.
    :param cert_reqs:
        Whether to require the certificate verification. This defaults to
        ``ssl.CERT_REQUIRED``.
    :param options:
        Specific OpenSSL options. These default to ``ssl.OP_NO_SSLv2``,
        ``ssl.OP_NO_SSLv3``, ``ssl.OP_NO_COMPRESSION``, and ``ssl.OP_NO_TICKET``.
    :param ciphers:
        Which cipher suites to allow the server to select. Defaults to either system configured
        ciphers if OpenSSL 1.1.1+, otherwise uses a secure default set of ciphers.
    :param verify_flags:
        The flags for certificate verification operations. These default to
        ``ssl.VERIFY_X509_PARTIAL_CHAIN`` and ``ssl.VERIFY_X509_STRICT`` for Python 3.13+.
    :returns:
        Constructed SSLContext object with specified options
    :rtype: SSLContext
    """
    if SSLContext is None:
        raise TypeError("Can't create an SSLContext object without an ssl module")

    # This means 'ssl_version' was specified as an exact value.
    if ssl_version not in (None, PROTOCOL_TLS, PROTOCOL_TLS_CLIENT):
        # Disallow setting 'ssl_version' and 'ssl_minimum|maximum_version'
        # to avoid conflicts.
        if ssl_minimum_version is not None or ssl_maximum_version is not None:
            raise ValueError(
                "Can't specify both 'ssl_version' and either "
                "'ssl_minimum_version' or 'ssl_maximum_version'"
            )

        # 'ssl_version' is deprecated and will be removed in the future.
        else:
            # Use 'ssl_minimum_version' and 'ssl_maximum_version' instead.
            ssl_minimum_version = _SSL_VERSION_TO_TLS_VERSION.get(
                ssl_version, TLSVersion.MINIMUM_SUPPORTED
            )
            ssl_maximum_version = _SSL_VERSION_TO_TLS_VERSION.get(
                ssl_version, TLSVersion.MAXIMUM_SUPPORTED
            )

            # This warning message is pushing users to use 'ssl_minimum_version'
            # instead of both min/max. Best practice is to only set the minimum version and
            # keep the maximum version to be it's default value: 'TLSVersion.MAXIMUM_SUPPORTED'
            warnings.warn(
                "'ssl_version' option is deprecated and will be "
                "removed in urllib3 v2.1.0. Instead use 'ssl_minimum_version'",
                category=DeprecationWarning,
                stacklevel=2,
            )

    # PROTOCOL_TLS is deprecated in Python 3.10 so we always use PROTOCOL_TLS_CLIENT
    context = SSLContext(PROTOCOL_TLS_CLIENT)

    if ssl_minimum_version is not None:
        context.minimum_version = ssl_minimum_version
    else:  # Python <3.10 defaults to 'MINIMUM_SUPPORTED' so explicitly set TLSv1.2 here
        context.minimum_version = TLSVersion.TLSv1_2

    if ssl_maximum_version is not None:
        context.maximum_version = ssl_maximum_version

    # Unless we're given ciphers defer to either system ciphers in
    # the case of OpenSSL 1.1.1+ or use our own secure default ciphers.
    if ciphers:
        context.set_ciphers(ciphers)

    # Setting the default here, as we may have no ssl module on import
    cert_reqs = ssl.CERT_REQUIRED if cert_reqs is None else cert_reqs

    if options is None:
        options = 0
        # SSLv2 is easily broken and is considered harmful and dangerous
        options |= OP_NO_SSLv2
        # SSLv3 has several problems and is now dangerous
        options |= OP_NO_SSLv3
        # Disable compression to prevent CRIME attacks for OpenSSL 1.0+
        # (issue #309)
        options |= OP_NO_COMPRESSION
        # TLSv1.2 only. Unless set explicitly, do not request tickets.
        # This may save some bandwidth on wire, and although the ticket is encrypted,
        # there is a risk associated with it being on wire,
        # if the server is not rotating its ticketing keys properly.
        options |= OP_NO_TICKET

    context.options |= options

    if verify_flags is None:
        verify_flags = 0
        # In Python 3.13+ ssl.create_default_context() sets VERIFY_X509_PARTIAL_CHAIN
        # and VERIFY_X509_STRICT so we do the same
        if sys.version_info >= (3, 13):
            verify_flags |= VERIFY_X509_PARTIAL_CHAIN
            verify_flags |= VERIFY_X509_STRICT

    context.verify_flags |= verify_flags

    # Enable post-handshake authentication for TLS 1.3, see GH #1634. PHA is
    # necessary for conditional client cert authentication with TLS 1.3.
    # The attribute is None for OpenSSL <= 1.1.0 or does not exist when using
    # an SSLContext created by pyOpenSSL.
    if getattr(context, "post_handshake_auth", None) is not None:
        context.post_handshake_auth = True

    # The order of the below lines setting verify_mode and check_hostname
    # matter due to safe-guards SSLContext has to prevent an SSLContext with
    # check_hostname=True, verify_mode=NONE/OPTIONAL.
    # We always set 'check_hostname=False' for pyOpenSSL so we rely on our own
    # 'ssl.match_hostname()' implementation.
    if cert_reqs == ssl.CERT_REQUIRED and not IS_PYOPENSSL:
        context.verify_mode = cert_reqs
        context.check_hostname = True
    else:
        context.check_hostname = False
        context.verify_mode = cert_reqs

    try:
        context.hostname_checks_common_name = False
    except AttributeError:  # Defensive: for CPython < 3.9.3; for PyPy < 7.3.8
        pass

    sslkeylogfile = os.environ.get("SSLKEYLOGFILE")
    if sslkeylogfile:
        context.keylog_filename = sslkeylogfile

    return context


@typing.overload
def ssl_wrap_socket(
    sock: socket.socket,
    keyfile: str | None = ...,
    certfile: str | None = ...,
    cert_reqs: int | None = ...,
    ca_certs: str | None = ...,
    server_hostname: str | None = ...,
    ssl_version: int | None = ...,
    ciphers: str | None = ...,
    ssl_context: ssl.SSLContext | None = ...,
    ca_cert_dir: str | None = ...,
    key_password: str | None = ...,
    ca_cert_data: None | str | bytes = ...,
    tls_in_tls: typing.Literal[False] = ...,
) -> ssl.SSLSocket: ...


@typing.overload
def ssl_wrap_socket(
    sock: socket.socket,
    keyfile: str | None = ...,
    certfile: str | None = ...,
    cert_reqs: int | None = ...,
    ca_certs: str | None = ...,
    server_hostname: str | None = ...,
    ssl_version: int | None = ...,
    ciphers: str | None = ...,
    ssl_context: ssl.SSLContext | None = ...,
    ca_cert_dir: str | None = ...,
    key_password: str | None = ...,
    ca_cert_data: None | str | bytes = ...,
    tls_in_tls: bool = ...,
) -> ssl.SSLSocket | SSLTransportType: ...


def ssl_wrap_socket(
    sock: socket.socket,
    keyfile: str | None = None,
    certfile: str | None = None,
    cert_reqs: int | None = None,
    ca_certs: str | None = None,
    server_hostname: str | None = None,
    ssl_version: int | None = None,
    ciphers: str | None = None,
    ssl_context: ssl.SSLContext | None = None,
    ca_cert_dir: str | None = None,
    key_password: str | None = None,
    ca_cert_data: None | str | bytes = None,
    tls_in_tls: bool = False,
) -> ssl.SSLSocket | SSLTransportType:
    """
    All arguments except for server_hostname, ssl_context, tls_in_tls, ca_cert_data and
    ca_cert_dir have the same meaning as they do when using
    :func:`ssl.create_default_context`, :meth:`ssl.SSLContext.load_cert_chain`,
    :meth:`ssl.SSLContext.set_ciphers` and :meth:`ssl.SSLContext.wrap_socket`.

    :param server_hostname:
        When SNI is supported, the expected hostname of the certificate
    :param ssl_context:
        A pre-made :class:`SSLContext` object. If none is provided, one will
        be created using :func:`create_urllib3_context`.
    :param ciphers:
        A string of ciphers we wish the client to support.
    :param ca_cert_dir:
        A directory containing CA certificates in multiple separate files, as
        supported by OpenSSL's -CApath flag or the capath argument to
        SSLContext.load_verify_locations().
    :param key_password:
        Optional password if the keyfile is encrypted.
    :param ca_cert_data:
        Optional string containing CA certificates in PEM format suitable for
        passing as the cadata parameter to SSLContext.load_verify_locations()
    :param tls_in_tls:
        Use SSLTransport to wrap the existing socket.
    """
    context = ssl_context
    if context is None:
        # Note: This branch of code and all the variables in it are only used in tests.
        # We should consider deprecating and removing this code.
        context = create_urllib3_context(ssl_version, cert_reqs, ciphers=ciphers)

    if ca_certs or ca_cert_dir or ca_cert_data:
        try:
            context.load_verify_locations(ca_certs, ca_cert_dir, ca_cert_data)
        except OSError as e:
            raise SSLError(e) from e

    elif ssl_context is None and hasattr(context, "load_default_certs"):
        # try to load OS default certs; works well on Windows.
        context.load_default_certs()

    # Attempt to detect if we get the goofy behavior of the
    # keyfile being encrypted and OpenSSL asking for the
    # passphrase via the terminal and instead error out.
    if keyfile and key_password is None and _is_key_file_encrypted(keyfile):
        raise SSLError("Client private key is encrypted, password is required")

    if certfile:
        if key_password is None:
            context.load_cert_chain(certfile, keyfile)
        else:
            context.load_cert_chain(certfile, keyfile, key_password)

    context.set_alpn_protocols(ALPN_PROTOCOLS)

    ssl_sock = _ssl_wrap_socket_impl(sock, context, tls_in_tls, server_hostname)
    return ssl_sock


def is_ipaddress(hostname: str | bytes) -> bool:
    """Detects whether the hostname given is an IPv4 or IPv6 address.
    Also detects IPv6 addresses with Zone IDs.

    :param str hostname: Hostname to examine.
    :return: True if the hostname is an IP address, False otherwise.
    """
    if isinstance(hostname, bytes):
        # IDN A-label bytes are ASCII compatible.
        hostname = hostname.decode("ascii")
    return bool(_IPV4_RE.match(hostname) or _BRACELESS_IPV6_ADDRZ_RE.match(hostname))


def _is_key_file_encrypted(key_file: str) -> bool:
    """Detects if a key file is encrypted or not."""
    with open(key_file) as f:
        for line in f:
            # Look for Proc-Type: 4,ENCRYPTED
            if "ENCRYPTED" in line:
                return True

    return False


def _ssl_wrap_socket_impl(
    sock: socket.socket,
    ssl_context: ssl.SSLContext,
    tls_in_tls: bool,
    server_hostname: str | None = None,
) -> ssl.SSLSocket | SSLTransportType:
    if tls_in_tls:
        if not SSLTransport:
            # Import error, ssl is not available.
            raise ProxySchemeUnsupported(
                "TLS in TLS requires support for the 'ssl' module"
            )

        SSLTransport._validate_ssl_context_for_tls_in_tls(ssl_context)
        return SSLTransport(sock, ssl_context, server_hostname)

    return ssl_context.wrap_socket(sock, server_hostname=server_hostname)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\network\session.py ===
"""PipSession and supporting code, containing all pip-specific
network request configuration and behavior.
"""

import email.utils
import functools
import io
import ipaddress
import json
import logging
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import urllib.parse
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pip._vendor import requests, urllib3
from pip._vendor.cachecontrol import CacheControlAdapter as _BaseCacheControlAdapter
from pip._vendor.requests.adapters import DEFAULT_POOLBLOCK, BaseAdapter
from pip._vendor.requests.adapters import HTTPAdapter as _BaseHTTPAdapter
from pip._vendor.requests.models import PreparedRequest, Response
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.urllib3.connectionpool import ConnectionPool
from pip._vendor.urllib3.exceptions import InsecureRequestWarning

from pip import __version__
from pip._internal.metadata import get_default_environment
from pip._internal.models.link import Link
from pip._internal.network.auth import MultiDomainBasicAuth
from pip._internal.network.cache import SafeFileCache

# Import ssl from compat so the initial import occurs in only one place.
from pip._internal.utils.compat import has_tls
from pip._internal.utils.glibc import libc_ver
from pip._internal.utils.misc import build_url_from_netloc, parse_netloc
from pip._internal.utils.urls import url_to_path

if TYPE_CHECKING:
    from ssl import SSLContext

    from pip._vendor.urllib3.poolmanager import PoolManager


logger = logging.getLogger(__name__)

SecureOrigin = Tuple[str, str, Optional[Union[int, str]]]


# Ignore warning raised when using --trusted-host.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


SECURE_ORIGINS: List[SecureOrigin] = [
    # protocol, hostname, port
    # Taken from Chrome's list of secure origins (See: http://bit.ly/1qrySKC)
    ("https", "*", "*"),
    ("*", "localhost", "*"),
    ("*", "127.0.0.0/8", "*"),
    ("*", "::1/128", "*"),
    ("file", "*", None),
    # ssh is always secure.
    ("ssh", "*", "*"),
]


# These are environment variables present when running under various
# CI systems.  For each variable, some CI systems that use the variable
# are indicated.  The collection was chosen so that for each of a number
# of popular systems, at least one of the environment variables is used.
# This list is used to provide some indication of and lower bound for
# CI traffic to PyPI.  Thus, it is okay if the list is not comprehensive.
# For more background, see: https://github.com/pypa/pip/issues/5499
CI_ENVIRONMENT_VARIABLES = (
    # Azure Pipelines
    "BUILD_BUILDID",
    # Jenkins
    "BUILD_ID",
    # AppVeyor, CircleCI, Codeship, Gitlab CI, Shippable, Travis CI
    "CI",
    # Explicit environment variable.
    "PIP_IS_CI",
)


def looks_like_ci() -> bool:
    """
    Return whether it looks like pip is running under CI.
    """
    # We don't use the method of checking for a tty (e.g. using isatty())
    # because some CI systems mimic a tty (e.g. Travis CI).  Thus that
    # method doesn't provide definitive information in either direction.
    return any(name in os.environ for name in CI_ENVIRONMENT_VARIABLES)


@functools.lru_cache(maxsize=1)
def user_agent() -> str:
    """
    Return a string representing the user agent.
    """
    data: Dict[str, Any] = {
        "installer": {"name": "pip", "version": __version__},
        "python": platform.python_version(),
        "implementation": {
            "name": platform.python_implementation(),
        },
    }

    if data["implementation"]["name"] == "CPython":
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == "PyPy":
        pypy_version_info = sys.pypy_version_info  # type: ignore
        if pypy_version_info.releaselevel == "final":
            pypy_version_info = pypy_version_info[:3]
        data["implementation"]["version"] = ".".join(
            [str(x) for x in pypy_version_info]
        )
    elif data["implementation"]["name"] == "Jython":
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == "IronPython":
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()

    if sys.platform.startswith("linux"):
        from pip._vendor import distro

        linux_distribution = distro.name(), distro.version(), distro.codename()
        distro_infos: Dict[str, Any] = dict(
            filter(
                lambda x: x[1],
                zip(["name", "version", "id"], linux_distribution),
            )
        )
        libc = dict(
            filter(
                lambda x: x[1],
                zip(["lib", "version"], libc_ver()),
            )
        )
        if libc:
            distro_infos["libc"] = libc
        if distro_infos:
            data["distro"] = distro_infos

    if sys.platform.startswith("darwin") and platform.mac_ver()[0]:
        data["distro"] = {"name": "macOS", "version": platform.mac_ver()[0]}

    if platform.system():
        data.setdefault("system", {})["name"] = platform.system()

    if platform.release():
        data.setdefault("system", {})["release"] = platform.release()

    if platform.machine():
        data["cpu"] = platform.machine()

    if has_tls():
        import _ssl as ssl

        data["openssl_version"] = ssl.OPENSSL_VERSION

    setuptools_dist = get_default_environment().get_distribution("setuptools")
    if setuptools_dist is not None:
        data["setuptools_version"] = str(setuptools_dist.version)

    if shutil.which("rustc") is not None:
        # If for any reason `rustc --version` fails, silently ignore it
        try:
            rustc_output = subprocess.check_output(
                ["rustc", "--version"], stderr=subprocess.STDOUT, timeout=0.5
            )
        except Exception:
            pass
        else:
            if rustc_output.startswith(b"rustc "):
                # The format of `rustc --version` is:
                # `b'rustc 1.52.1 (9bc8c42bb 2021-05-09)\n'`
                # We extract just the middle (1.52.1) part
                data["rustc_version"] = rustc_output.split(b" ")[1].decode()

    # Use None rather than False so as not to give the impression that
    # pip knows it is not being run under CI.  Rather, it is a null or
    # inconclusive result.  Also, we include some value rather than no
    # value to make it easier to know that the check has been run.
    data["ci"] = True if looks_like_ci() else None

    user_data = os.environ.get("PIP_USER_AGENT_USER_DATA")
    if user_data is not None:
        data["user_data"] = user_data

    return "{data[installer][name]}/{data[installer][version]} {json}".format(
        data=data,
        json=json.dumps(data, separators=(",", ":"), sort_keys=True),
    )


class LocalFSAdapter(BaseAdapter):
    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: Optional[Union[float, Tuple[float, float]]] = None,
        verify: Union[bool, str] = True,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> Response:
        pathname = url_to_path(request.url)

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = os.stat(pathname)
        except OSError as exc:
            # format the exception raised as a io.BytesIO object,
            # to return a better error message:
            resp.status_code = 404
            resp.reason = type(exc).__name__
            resp.raw = io.BytesIO(f"{resp.reason}: {exc}".encode())
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(pathname)[0] or "text/plain"
            resp.headers = CaseInsensitiveDict(
                {
                    "Content-Type": content_type,
                    "Content-Length": stats.st_size,
                    "Last-Modified": modified,
                }
            )

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close

        return resp

    def close(self) -> None:
        pass


class _SSLContextAdapterMixin:
    """Mixin to add the ``ssl_context`` constructor argument to HTTP adapters.

    The additional argument is forwarded directly to the pool manager. This allows us
    to dynamically decide what SSL store to use at runtime, which is used to implement
    the optional ``truststore`` backend.
    """

    def __init__(
        self,
        *,
        ssl_context: Optional["SSLContext"] = None,
        **kwargs: Any,
    ) -> None:
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        **pool_kwargs: Any,
    ) -> "PoolManager":
        if self._ssl_context is not None:
            pool_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().init_poolmanager(  # type: ignore[misc]
            connections=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


class HTTPAdapter(_SSLContextAdapterMixin, _BaseHTTPAdapter):
    pass


class CacheControlAdapter(_SSLContextAdapterMixin, _BaseCacheControlAdapter):
    pass


class InsecureHTTPAdapter(HTTPAdapter):
    def cert_verify(
        self,
        conn: ConnectionPool,
        url: str,
        verify: Union[bool, str],
        cert: Optional[Union[str, Tuple[str, str]]],
    ) -> None:
        super().cert_verify(conn=conn, url=url, verify=False, cert=cert)


class InsecureCacheControlAdapter(CacheControlAdapter):
    def cert_verify(
        self,
        conn: ConnectionPool,
        url: str,
        verify: Union[bool, str],
        cert: Optional[Union[str, Tuple[str, str]]],
    ) -> None:
        super().cert_verify(conn=conn, url=url, verify=False, cert=cert)


class PipSession(requests.Session):
    timeout: Optional[int] = None

    def __init__(
        self,
        *args: Any,
        retries: int = 0,
        cache: Optional[str] = None,
        trusted_hosts: Sequence[str] = (),
        index_urls: Optional[List[str]] = None,
        ssl_context: Optional["SSLContext"] = None,
        **kwargs: Any,
    ) -> None:
        """
        :param trusted_hosts: Domains not to emit warnings for when not using
            HTTPS.
        """
        super().__init__(*args, **kwargs)

        # Namespace the attribute with "pip_" just in case to prevent
        # possible conflicts with the base class.
        self.pip_trusted_origins: List[Tuple[str, Optional[int]]] = []
        self.pip_proxy = None

        # Attach our User Agent to the request
        self.headers["User-Agent"] = user_agent()

        # Attach our Authentication handler to the session
        self.auth = MultiDomainBasicAuth(index_urls=index_urls)

        # Create our urllib3.Retry instance which will allow us to customize
        # how we handle retries.
        retries = urllib3.Retry(
            # Set the total number of retries that a particular request can
            # have.
            total=retries,
            # A 503 error from PyPI typically means that the Fastly -> Origin
            # connection got interrupted in some way. A 503 error in general
            # is typically considered a transient error so we'll go ahead and
            # retry it.
            # A 500 may indicate transient error in Amazon S3
            # A 502 may be a transient error from a CDN like CloudFlare or CloudFront
            # A 520 or 527 - may indicate transient error in CloudFlare
            status_forcelist=[500, 502, 503, 520, 527],
            # Add a small amount of back off between failed requests in
            # order to prevent hammering the service.
            backoff_factor=0.25,
        )  # type: ignore

        # Our Insecure HTTPAdapter disables HTTPS validation. It does not
        # support caching so we'll use it for all http:// URLs.
        # If caching is disabled, we will also use it for
        # https:// hosts that we've marked as ignoring
        # TLS errors for (trusted-hosts).
        insecure_adapter = InsecureHTTPAdapter(max_retries=retries)

        # We want to _only_ cache responses on securely fetched origins or when
        # the host is specified as trusted. We do this because
        # we can't validate the response of an insecurely/untrusted fetched
        # origin, and we don't want someone to be able to poison the cache and
        # require manual eviction from the cache to fix it.
        if cache:
            secure_adapter = CacheControlAdapter(
                cache=SafeFileCache(cache),
                max_retries=retries,
                ssl_context=ssl_context,
            )
            self._trusted_host_adapter = InsecureCacheControlAdapter(
                cache=SafeFileCache(cache),
                max_retries=retries,
            )
        else:
            secure_adapter = HTTPAdapter(max_retries=retries, ssl_context=ssl_context)
            self._trusted_host_adapter = insecure_adapter

        self.mount("https://", secure_adapter)
        self.mount("http://", insecure_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        for host in trusted_hosts:
            self.add_trusted_host(host, suppress_logging=True)

    def update_index_urls(self, new_index_urls: List[str]) -> None:
        """
        :param new_index_urls: New index urls to update the authentication
            handler with.
        """
        self.auth.index_urls = new_index_urls

    def add_trusted_host(
        self, host: str, source: Optional[str] = None, suppress_logging: bool = False
    ) -> None:
        """
        :param host: It is okay to provide a host that has previously been
            added.
        :param source: An optional source string, for logging where the host
            string came from.
        """
        if not suppress_logging:
            msg = f"adding trusted host: {host!r}"
            if source is not None:
                msg += f" (from {source})"
            logger.info(msg)

        parsed_host, parsed_port = parse_netloc(host)
        if parsed_host is None:
            raise ValueError(f"Trusted host URL must include a host part: {host!r}")
        if (parsed_host, parsed_port) not in self.pip_trusted_origins:
            self.pip_trusted_origins.append((parsed_host, parsed_port))

        self.mount(
            build_url_from_netloc(host, scheme="http") + "/", self._trusted_host_adapter
        )
        self.mount(build_url_from_netloc(host) + "/", self._trusted_host_adapter)
        if not parsed_port:
            self.mount(
                build_url_from_netloc(host, scheme="http") + ":",
                self._trusted_host_adapter,
            )
            # Mount wildcard ports for the same host.
            self.mount(build_url_from_netloc(host) + ":", self._trusted_host_adapter)

    def iter_secure_origins(self) -> Generator[SecureOrigin, None, None]:
        yield from SECURE_ORIGINS
        for host, port in self.pip_trusted_origins:
            yield ("*", host, "*" if port is None else port)

    def is_secure_origin(self, location: Link) -> bool:
        # Determine if this url used a secure transport mechanism
        parsed = urllib.parse.urlparse(str(location))
        origin_protocol, origin_host, origin_port = (
            parsed.scheme,
            parsed.hostname,
            parsed.port,
        )

        # The protocol to use to see if the protocol matches.
        # Don't count the repository type as part of the protocol: in
        # cases such as "git+ssh", only use "ssh". (I.e., Only verify against
        # the last scheme.)
        origin_protocol = origin_protocol.rsplit("+", 1)[-1]

        # Determine if our origin is a secure origin by looking through our
        # hardcoded list of secure origins, as well as any additional ones
        # configured on this PackageFinder instance.
        for secure_origin in self.iter_secure_origins():
            secure_protocol, secure_host, secure_port = secure_origin
            if origin_protocol != secure_protocol and secure_protocol != "*":
                continue

            try:
                addr = ipaddress.ip_address(origin_host or "")
                network = ipaddress.ip_network(secure_host)
            except ValueError:
                # We don't have both a valid address or a valid network, so
                # we'll check this origin against hostnames.
                if (
                    origin_host
                    and origin_host.lower() != secure_host.lower()
                    and secure_host != "*"
                ):
                    continue
            else:
                # We have a valid address and network, so see if the address
                # is contained within the network.
                if addr not in network:
                    continue

            # Check to see if the port matches.
            if (
                origin_port != secure_port
                and secure_port != "*"
                and secure_port is not None
            ):
                continue

            # If we've gotten here, then this origin matches the current
            # secure origin and we should return True
            return True

        # If we've gotten to this point, then the origin isn't secure and we
        # will not accept it as a valid location to search. We will however
        # log a warning that we are ignoring it.
        logger.warning(
            "The repository located at %s is not a trusted or secure host and "
            "is being ignored. If this repository is available via HTTPS we "
            "recommend you use HTTPS instead, otherwise you may silence "
            "this warning and allow it anyway with '--trusted-host %s'.",
            origin_host,
            origin_host,
        )

        return False

    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:
        # Allow setting a default timeout on a session
        kwargs.setdefault("timeout", self.timeout)
        # Allow setting a default proxies on a session
        kwargs.setdefault("proxies", self.proxies)

        # Dispatch the actual request
        return super().request(method, url, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\pip\_internal\network\session.py ===
"""PipSession and supporting code, containing all pip-specific
network request configuration and behavior.
"""

import email.utils
import functools
import io
import ipaddress
import json
import logging
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import urllib.parse
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pip._vendor import requests, urllib3
from pip._vendor.cachecontrol import CacheControlAdapter as _BaseCacheControlAdapter
from pip._vendor.requests.adapters import DEFAULT_POOLBLOCK, BaseAdapter
from pip._vendor.requests.adapters import HTTPAdapter as _BaseHTTPAdapter
from pip._vendor.requests.models import PreparedRequest, Response
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.urllib3.connectionpool import ConnectionPool
from pip._vendor.urllib3.exceptions import InsecureRequestWarning

from pip import __version__
from pip._internal.metadata import get_default_environment
from pip._internal.models.link import Link
from pip._internal.network.auth import MultiDomainBasicAuth
from pip._internal.network.cache import SafeFileCache

# Import ssl from compat so the initial import occurs in only one place.
from pip._internal.utils.compat import has_tls
from pip._internal.utils.glibc import libc_ver
from pip._internal.utils.misc import build_url_from_netloc, parse_netloc
from pip._internal.utils.urls import url_to_path

if TYPE_CHECKING:
    from ssl import SSLContext

    from pip._vendor.urllib3.poolmanager import PoolManager


logger = logging.getLogger(__name__)

SecureOrigin = Tuple[str, str, Optional[Union[int, str]]]


# Ignore warning raised when using --trusted-host.
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


SECURE_ORIGINS: List[SecureOrigin] = [
    # protocol, hostname, port
    # Taken from Chrome's list of secure origins (See: http://bit.ly/1qrySKC)
    ("https", "*", "*"),
    ("*", "localhost", "*"),
    ("*", "127.0.0.0/8", "*"),
    ("*", "::1/128", "*"),
    ("file", "*", None),
    # ssh is always secure.
    ("ssh", "*", "*"),
]


# These are environment variables present when running under various
# CI systems.  For each variable, some CI systems that use the variable
# are indicated.  The collection was chosen so that for each of a number
# of popular systems, at least one of the environment variables is used.
# This list is used to provide some indication of and lower bound for
# CI traffic to PyPI.  Thus, it is okay if the list is not comprehensive.
# For more background, see: https://github.com/pypa/pip/issues/5499
CI_ENVIRONMENT_VARIABLES = (
    # Azure Pipelines
    "BUILD_BUILDID",
    # Jenkins
    "BUILD_ID",
    # AppVeyor, CircleCI, Codeship, Gitlab CI, Shippable, Travis CI
    "CI",
    # Explicit environment variable.
    "PIP_IS_CI",
)


def looks_like_ci() -> bool:
    """
    Return whether it looks like pip is running under CI.
    """
    # We don't use the method of checking for a tty (e.g. using isatty())
    # because some CI systems mimic a tty (e.g. Travis CI).  Thus that
    # method doesn't provide definitive information in either direction.
    return any(name in os.environ for name in CI_ENVIRONMENT_VARIABLES)


@functools.lru_cache(maxsize=1)
def user_agent() -> str:
    """
    Return a string representing the user agent.
    """
    data: Dict[str, Any] = {
        "installer": {"name": "pip", "version": __version__},
        "python": platform.python_version(),
        "implementation": {
            "name": platform.python_implementation(),
        },
    }

    if data["implementation"]["name"] == "CPython":
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == "PyPy":
        pypy_version_info = sys.pypy_version_info  # type: ignore
        if pypy_version_info.releaselevel == "final":
            pypy_version_info = pypy_version_info[:3]
        data["implementation"]["version"] = ".".join(
            [str(x) for x in pypy_version_info]
        )
    elif data["implementation"]["name"] == "Jython":
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == "IronPython":
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()

    if sys.platform.startswith("linux"):
        from pip._vendor import distro

        linux_distribution = distro.name(), distro.version(), distro.codename()
        distro_infos: Dict[str, Any] = dict(
            filter(
                lambda x: x[1],
                zip(["name", "version", "id"], linux_distribution),
            )
        )
        libc = dict(
            filter(
                lambda x: x[1],
                zip(["lib", "version"], libc_ver()),
            )
        )
        if libc:
            distro_infos["libc"] = libc
        if distro_infos:
            data["distro"] = distro_infos

    if sys.platform.startswith("darwin") and platform.mac_ver()[0]:
        data["distro"] = {"name": "macOS", "version": platform.mac_ver()[0]}

    if platform.system():
        data.setdefault("system", {})["name"] = platform.system()

    if platform.release():
        data.setdefault("system", {})["release"] = platform.release()

    if platform.machine():
        data["cpu"] = platform.machine()

    if has_tls():
        import _ssl as ssl

        data["openssl_version"] = ssl.OPENSSL_VERSION

    setuptools_dist = get_default_environment().get_distribution("setuptools")
    if setuptools_dist is not None:
        data["setuptools_version"] = str(setuptools_dist.version)

    if shutil.which("rustc") is not None:
        # If for any reason `rustc --version` fails, silently ignore it
        try:
            rustc_output = subprocess.check_output(
                ["rustc", "--version"], stderr=subprocess.STDOUT, timeout=0.5
            )
        except Exception:
            pass
        else:
            if rustc_output.startswith(b"rustc "):
                # The format of `rustc --version` is:
                # `b'rustc 1.52.1 (9bc8c42bb 2021-05-09)\n'`
                # We extract just the middle (1.52.1) part
                data["rustc_version"] = rustc_output.split(b" ")[1].decode()

    # Use None rather than False so as not to give the impression that
    # pip knows it is not being run under CI.  Rather, it is a null or
    # inconclusive result.  Also, we include some value rather than no
    # value to make it easier to know that the check has been run.
    data["ci"] = True if looks_like_ci() else None

    user_data = os.environ.get("PIP_USER_AGENT_USER_DATA")
    if user_data is not None:
        data["user_data"] = user_data

    return "{data[installer][name]}/{data[installer][version]} {json}".format(
        data=data,
        json=json.dumps(data, separators=(",", ":"), sort_keys=True),
    )


class LocalFSAdapter(BaseAdapter):
    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: Optional[Union[float, Tuple[float, float]]] = None,
        verify: Union[bool, str] = True,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        proxies: Optional[Mapping[str, str]] = None,
    ) -> Response:
        pathname = url_to_path(request.url)

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = os.stat(pathname)
        except OSError as exc:
            # format the exception raised as a io.BytesIO object,
            # to return a better error message:
            resp.status_code = 404
            resp.reason = type(exc).__name__
            resp.raw = io.BytesIO(f"{resp.reason}: {exc}".encode())
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(pathname)[0] or "text/plain"
            resp.headers = CaseInsensitiveDict(
                {
                    "Content-Type": content_type,
                    "Content-Length": stats.st_size,
                    "Last-Modified": modified,
                }
            )

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close

        return resp

    def close(self) -> None:
        pass


class _SSLContextAdapterMixin:
    """Mixin to add the ``ssl_context`` constructor argument to HTTP adapters.

    The additional argument is forwarded directly to the pool manager. This allows us
    to dynamically decide what SSL store to use at runtime, which is used to implement
    the optional ``truststore`` backend.
    """

    def __init__(
        self,
        *,
        ssl_context: Optional["SSLContext"] = None,
        **kwargs: Any,
    ) -> None:
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = DEFAULT_POOLBLOCK,
        **pool_kwargs: Any,
    ) -> "PoolManager":
        if self._ssl_context is not None:
            pool_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().init_poolmanager(  # type: ignore[misc]
            connections=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )


class HTTPAdapter(_SSLContextAdapterMixin, _BaseHTTPAdapter):
    pass


class CacheControlAdapter(_SSLContextAdapterMixin, _BaseCacheControlAdapter):
    pass


class InsecureHTTPAdapter(HTTPAdapter):
    def cert_verify(
        self,
        conn: ConnectionPool,
        url: str,
        verify: Union[bool, str],
        cert: Optional[Union[str, Tuple[str, str]]],
    ) -> None:
        super().cert_verify(conn=conn, url=url, verify=False, cert=cert)


class InsecureCacheControlAdapter(CacheControlAdapter):
    def cert_verify(
        self,
        conn: ConnectionPool,
        url: str,
        verify: Union[bool, str],
        cert: Optional[Union[str, Tuple[str, str]]],
    ) -> None:
        super().cert_verify(conn=conn, url=url, verify=False, cert=cert)


class PipSession(requests.Session):
    timeout: Optional[int] = None

    def __init__(
        self,
        *args: Any,
        retries: int = 0,
        cache: Optional[str] = None,
        trusted_hosts: Sequence[str] = (),
        index_urls: Optional[List[str]] = None,
        ssl_context: Optional["SSLContext"] = None,
        **kwargs: Any,
    ) -> None:
        """
        :param trusted_hosts: Domains not to emit warnings for when not using
            HTTPS.
        """
        super().__init__(*args, **kwargs)

        # Namespace the attribute with "pip_" just in case to prevent
        # possible conflicts with the base class.
        self.pip_trusted_origins: List[Tuple[str, Optional[int]]] = []
        self.pip_proxy = None

        # Attach our User Agent to the request
        self.headers["User-Agent"] = user_agent()

        # Attach our Authentication handler to the session
        self.auth = MultiDomainBasicAuth(index_urls=index_urls)

        # Create our urllib3.Retry instance which will allow us to customize
        # how we handle retries.
        retries = urllib3.Retry(
            # Set the total number of retries that a particular request can
            # have.
            total=retries,
            # A 503 error from PyPI typically means that the Fastly -> Origin
            # connection got interrupted in some way. A 503 error in general
            # is typically considered a transient error so we'll go ahead and
            # retry it.
            # A 500 may indicate transient error in Amazon S3
            # A 502 may be a transient error from a CDN like CloudFlare or CloudFront
            # A 520 or 527 - may indicate transient error in CloudFlare
            status_forcelist=[500, 502, 503, 520, 527],
            # Add a small amount of back off between failed requests in
            # order to prevent hammering the service.
            backoff_factor=0.25,
        )  # type: ignore

        # Our Insecure HTTPAdapter disables HTTPS validation. It does not
        # support caching so we'll use it for all http:// URLs.
        # If caching is disabled, we will also use it for
        # https:// hosts that we've marked as ignoring
        # TLS errors for (trusted-hosts).
        insecure_adapter = InsecureHTTPAdapter(max_retries=retries)

        # We want to _only_ cache responses on securely fetched origins or when
        # the host is specified as trusted. We do this because
        # we can't validate the response of an insecurely/untrusted fetched
        # origin, and we don't want someone to be able to poison the cache and
        # require manual eviction from the cache to fix it.
        if cache:
            secure_adapter = CacheControlAdapter(
                cache=SafeFileCache(cache),
                max_retries=retries,
                ssl_context=ssl_context,
            )
            self._trusted_host_adapter = InsecureCacheControlAdapter(
                cache=SafeFileCache(cache),
                max_retries=retries,
            )
        else:
            secure_adapter = HTTPAdapter(max_retries=retries, ssl_context=ssl_context)
            self._trusted_host_adapter = insecure_adapter

        self.mount("https://", secure_adapter)
        self.mount("http://", insecure_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        for host in trusted_hosts:
            self.add_trusted_host(host, suppress_logging=True)

    def update_index_urls(self, new_index_urls: List[str]) -> None:
        """
        :param new_index_urls: New index urls to update the authentication
            handler with.
        """
        self.auth.index_urls = new_index_urls

    def add_trusted_host(
        self, host: str, source: Optional[str] = None, suppress_logging: bool = False
    ) -> None:
        """
        :param host: It is okay to provide a host that has previously been
            added.
        :param source: An optional source string, for logging where the host
            string came from.
        """
        if not suppress_logging:
            msg = f"adding trusted host: {host!r}"
            if source is not None:
                msg += f" (from {source})"
            logger.info(msg)

        parsed_host, parsed_port = parse_netloc(host)
        if parsed_host is None:
            raise ValueError(f"Trusted host URL must include a host part: {host!r}")
        if (parsed_host, parsed_port) not in self.pip_trusted_origins:
            self.pip_trusted_origins.append((parsed_host, parsed_port))

        self.mount(
            build_url_from_netloc(host, scheme="http") + "/", self._trusted_host_adapter
        )
        self.mount(build_url_from_netloc(host) + "/", self._trusted_host_adapter)
        if not parsed_port:
            self.mount(
                build_url_from_netloc(host, scheme="http") + ":",
                self._trusted_host_adapter,
            )
            # Mount wildcard ports for the same host.
            self.mount(build_url_from_netloc(host) + ":", self._trusted_host_adapter)

    def iter_secure_origins(self) -> Generator[SecureOrigin, None, None]:
        yield from SECURE_ORIGINS
        for host, port in self.pip_trusted_origins:
            yield ("*", host, "*" if port is None else port)

    def is_secure_origin(self, location: Link) -> bool:
        # Determine if this url used a secure transport mechanism
        parsed = urllib.parse.urlparse(str(location))
        origin_protocol, origin_host, origin_port = (
            parsed.scheme,
            parsed.hostname,
            parsed.port,
        )

        # The protocol to use to see if the protocol matches.
        # Don't count the repository type as part of the protocol: in
        # cases such as "git+ssh", only use "ssh". (I.e., Only verify against
        # the last scheme.)
        origin_protocol = origin_protocol.rsplit("+", 1)[-1]

        # Determine if our origin is a secure origin by looking through our
        # hardcoded list of secure origins, as well as any additional ones
        # configured on this PackageFinder instance.
        for secure_origin in self.iter_secure_origins():
            secure_protocol, secure_host, secure_port = secure_origin
            if origin_protocol != secure_protocol and secure_protocol != "*":
                continue

            try:
                addr = ipaddress.ip_address(origin_host or "")
                network = ipaddress.ip_network(secure_host)
            except ValueError:
                # We don't have both a valid address or a valid network, so
                # we'll check this origin against hostnames.
                if (
                    origin_host
                    and origin_host.lower() != secure_host.lower()
                    and secure_host != "*"
                ):
                    continue
            else:
                # We have a valid address and network, so see if the address
                # is contained within the network.
                if addr not in network:
                    continue

            # Check to see if the port matches.
            if (
                origin_port != secure_port
                and secure_port != "*"
                and secure_port is not None
            ):
                continue

            # If we've gotten here, then this origin matches the current
            # secure origin and we should return True
            return True

        # If we've gotten to this point, then the origin isn't secure and we
        # will not accept it as a valid location to search. We will however
        # log a warning that we are ignoring it.
        logger.warning(
            "The repository located at %s is not a trusted or secure host and "
            "is being ignored. If this repository is available via HTTPS we "
            "recommend you use HTTPS instead, otherwise you may silence "
            "this warning and allow it anyway with '--trusted-host %s'.",
            origin_host,
            origin_host,
        )

        return False

    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:
        # Allow setting a default timeout on a session
        kwargs.setdefault("timeout", self.timeout)
        # Allow setting a default proxies on a session
        kwargs.setdefault("proxies", self.proxies)

        # Dispatch the actual request
        return super().request(method, url, *args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_helper.py ===
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
import math
import os
import re
import time
import traceback
from pathlib import Path
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    TypedDict,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urljoin, urlparse

from playwright._impl._api_structures import NameValue
from playwright._impl._errors import (
    Error,
    TargetClosedError,
    TimeoutError,
    is_target_closed_error,
    rewrite_error,
)
from playwright._impl._glob import glob_to_regex_pattern
from playwright._impl._greenlets import RouteGreenlet
from playwright._impl._str_utils import escape_regex_flags

if TYPE_CHECKING:  # pragma: no cover
    from playwright._impl._api_structures import HeadersArray
    from playwright._impl._network import Request, Response, Route, WebSocketRoute

URLMatch = Union[str, Pattern[str], Callable[[str], bool]]
URLMatchRequest = Union[str, Pattern[str], Callable[["Request"], bool]]
URLMatchResponse = Union[str, Pattern[str], Callable[["Response"], bool]]
RouteHandlerCallback = Union[
    Callable[["Route"], Any], Callable[["Route", "Request"], Any]
]
WebSocketRouteHandlerCallback = Callable[["WebSocketRoute"], Any]

ColorScheme = Literal["dark", "light", "no-preference", "null"]
ForcedColors = Literal["active", "none", "null"]
Contrast = Literal["more", "no-preference", "null"]
ReducedMotion = Literal["no-preference", "null", "reduce"]
DocumentLoadState = Literal["commit", "domcontentloaded", "load", "networkidle"]
KeyboardModifier = Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]
MouseButton = Literal["left", "middle", "right"]
ServiceWorkersPolicy = Literal["allow", "block"]
HarMode = Literal["full", "minimal"]
HarContentPolicy = Literal["attach", "embed", "omit"]
RouteFromHarNotFoundPolicy = Literal["abort", "fallback"]


class ErrorPayload(TypedDict, total=False):
    message: str
    name: str
    stack: str
    value: Optional[Any]


class HarRecordingMetadata(TypedDict, total=False):
    path: str
    content: Optional[HarContentPolicy]


def prepare_record_har_options(params: Dict) -> Dict[str, Any]:
    out_params: Dict[str, Any] = {"path": str(params["recordHarPath"])}
    if "recordHarUrlFilter" in params:
        opt = params["recordHarUrlFilter"]
        if isinstance(opt, str):
            out_params["urlGlob"] = opt
        if isinstance(opt, Pattern):
            out_params["urlRegexSource"] = opt.pattern
            out_params["urlRegexFlags"] = escape_regex_flags(opt)
        del params["recordHarUrlFilter"]
    if "recordHarMode" in params:
        out_params["mode"] = params["recordHarMode"]
        del params["recordHarMode"]

    new_content_api = None
    old_content_api = None
    if "recordHarContent" in params:
        new_content_api = params["recordHarContent"]
        del params["recordHarContent"]
    if "recordHarOmitContent" in params:
        old_content_api = params["recordHarOmitContent"]
        del params["recordHarOmitContent"]
    content = new_content_api or ("omit" if old_content_api else None)
    if content:
        out_params["content"] = content

    return out_params


class ParsedMessageParams(TypedDict):
    type: str
    guid: str
    initializer: Dict


class ParsedMessagePayload(TypedDict, total=False):
    id: int
    guid: str
    method: str
    params: ParsedMessageParams
    result: Any
    error: ErrorPayload


class Document(TypedDict):
    request: Optional[Any]


class FrameNavigatedEvent(TypedDict):
    url: str
    name: str
    newDocument: Optional[Document]
    error: Optional[str]


Env = Dict[str, Union[str, float, bool]]


def url_matches(
    base_url: Optional[str],
    url_string: str,
    match: Optional[URLMatch],
    websocket_url: bool = None,
) -> bool:
    if not match:
        return True
    if isinstance(match, str):
        match = re.compile(
            resolve_glob_to_regex_pattern(base_url, match, websocket_url)
        )
    if isinstance(match, Pattern):
        return bool(match.search(url_string))
    return match(url_string)


def resolve_glob_to_regex_pattern(
    base_url: Optional[str], glob: str, websocket_url: bool = None
) -> str:
    if websocket_url:
        base_url = to_websocket_base_url(base_url)
    glob = resolve_glob_base(base_url, glob)
    return glob_to_regex_pattern(glob)


def to_websocket_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is not None and re.match(r"^https?://", base_url):
        base_url = re.sub(r"^http", "ws", base_url)
    return base_url


def resolve_glob_base(base_url: Optional[str], match: str) -> str:
    if match[0] == "*":
        return match

    token_map: Dict[str, str] = {}

    def map_token(original: str, replacement: str) -> str:
        if len(original) == 0:
            return ""
        token_map[replacement] = original
        return replacement

    # Escaped `\\?` behaves the same as `?` in our glob patterns.
    match = match.replace(r"\\?", "?")
    # Glob symbols may be escaped in the URL and some of them such as ? affect resolution,
    # so we replace them with safe components first.
    processed_parts = []
    for index, token in enumerate(match.split("/")):
        if token in (".", "..", ""):
            processed_parts.append(token)
            continue
        # Handle special case of http*://, note that the new schema has to be
        # a web schema so that slashes are properly inserted after domain.
        if index == 0 and token.endswith(":"):
            # Using a simple replacement for the scheme part
            processed_parts.append(map_token(token, "http:"))
            continue
        question_index = token.find("?")
        if question_index == -1:
            processed_parts.append(map_token(token, f"$_{index}_$"))
        else:
            new_prefix = map_token(token[:question_index], f"$_{index}_$")
            new_suffix = map_token(token[question_index:], f"?$_{index}_$")
            processed_parts.append(new_prefix + new_suffix)

    relative_path = "/".join(processed_parts)
    resolved_url = urljoin(base_url if base_url is not None else "", relative_path)

    for replacement, original in token_map.items():
        resolved_url = resolved_url.replace(replacement, original, 1)

    return ensure_trailing_slash(resolved_url)


# In Node.js, new URL('http://localhost') returns 'http://localhost/'.
# To ensure the same url matching behavior, do the same.
def ensure_trailing_slash(url: str) -> str:
    split = url.split("://", maxsplit=1)
    if len(split) == 2:
        # URL parser doesn't like strange/unknown schemes, so we replace it for parsing, then put it back
        parsable_url = "http://" + split[1]
    else:
        # Given current rules, this should never happen _and_ still be a valid matcher. We require the protocol to be part of the match,
        # so either the user is using a glob that starts with "*" (and none of this code is running), or the user actually has `something://` in `match`
        parsable_url = url
    parsed = urlparse(parsable_url, allow_fragments=True)
    if len(split) == 2:
        # Replace the scheme that we removed earlier
        parsed = parsed._replace(scheme=split[0])
    if parsed.path == "":
        parsed = parsed._replace(path="/")
        url = parsed.geturl()

    return url


class HarLookupResult(TypedDict, total=False):
    action: Literal["error", "redirect", "fulfill", "noentry"]
    message: Optional[str]
    redirectURL: Optional[str]
    status: Optional[int]
    headers: Optional["HeadersArray"]
    body: Optional[str]


class TimeoutSettings:
    def __init__(self, parent: Optional["TimeoutSettings"]) -> None:
        self._parent = parent
        self._default_timeout: Optional[float] = None
        self._default_navigation_timeout: Optional[float] = None

    def set_default_timeout(self, timeout: Optional[float]) -> None:
        self._default_timeout = timeout

    def timeout(self, timeout: float = None) -> float:
        if timeout is not None:
            return timeout
        if self._default_timeout is not None:
            return self._default_timeout
        if self._parent:
            return self._parent.timeout()
        return 30000

    def set_default_navigation_timeout(
        self, navigation_timeout: Optional[float]
    ) -> None:
        self._default_navigation_timeout = navigation_timeout

    def default_navigation_timeout(self) -> Optional[float]:
        return self._default_navigation_timeout

    def default_timeout(self) -> Optional[float]:
        return self._default_timeout

    def navigation_timeout(self) -> float:
        if self._default_navigation_timeout is not None:
            return self._default_navigation_timeout
        if self._parent:
            return self._parent.navigation_timeout()
        return 30000


def serialize_error(ex: Exception, tb: Optional[TracebackType]) -> ErrorPayload:
    return ErrorPayload(
        message=str(ex), name="Error", stack="".join(traceback.format_tb(tb))
    )


def parse_error(error: ErrorPayload, log: Optional[str] = None) -> Error:
    base_error_class = Error
    if error.get("name") == "TimeoutError":
        base_error_class = TimeoutError
    if error.get("name") == "TargetClosedError":
        base_error_class = TargetClosedError
    if not log:
        log = ""
    exc = base_error_class(patch_error_message(error["message"]) + log)
    exc._name = error["name"]
    exc._stack = error["stack"]
    return exc


def patch_error_message(message: str) -> str:
    match = re.match(r"(\w+)(: expected .*)", message)
    if match:
        message = to_snake_case(match.group(1)) + match.group(2)
    message = message.replace(
        "Pass { acceptDownloads: true }", "Pass 'accept_downloads=True'"
    )
    return message


def locals_to_params(args: Dict) -> Dict:
    copy = {}
    for key in args:
        if key == "self":
            continue
        if args[key] is not None:
            copy[key] = (
                args[key]
                if not isinstance(args[key], Dict)
                else locals_to_params(args[key])
            )
    return copy


def monotonic_time() -> int:
    return math.floor(time.monotonic() * 1000)


class RouteHandlerInvocation:
    complete: "asyncio.Future"
    route: "Route"

    def __init__(self, complete: "asyncio.Future", route: "Route") -> None:
        self.complete = complete
        self.route = route


class RouteHandler:
    def __init__(
        self,
        base_url: Optional[str],
        url: URLMatch,
        handler: RouteHandlerCallback,
        is_sync: bool,
        times: Optional[int] = None,
    ):
        self._base_url = base_url
        self.url = url
        self.handler = handler
        self._times = times if times else math.inf
        self._handled_count = 0
        self._is_sync = is_sync
        self._ignore_exception = False
        self._active_invocations: Set[RouteHandlerInvocation] = set()

    def matches(self, request_url: str) -> bool:
        return url_matches(self._base_url, request_url, self.url)

    async def handle(self, route: "Route") -> bool:
        handler_invocation = RouteHandlerInvocation(
            asyncio.get_running_loop().create_future(), route
        )
        self._active_invocations.add(handler_invocation)
        try:
            return await self._handle_internal(route)
        except Exception as e:
            # If the handler was stopped (without waiting for completion), we ignore all exceptions.
            if self._ignore_exception:
                return False
            if is_target_closed_error(e):
                # We are failing in the handler because the target has closed.
                # Give user a hint!
                optional_async_prefix = "await " if not self._is_sync else ""
                raise rewrite_error(
                    e,
                    f"\"{str(e)}\" while running route callback.\nConsider awaiting `{optional_async_prefix}page.unroute_all(behavior='ignoreErrors')`\nbefore the end of the test to ignore remaining routes in flight.",
                )
            raise e
        finally:
            handler_invocation.complete.set_result(None)
            self._active_invocations.remove(handler_invocation)

    async def _handle_internal(self, route: "Route") -> bool:
        handled_future = route._start_handling()

        self._handled_count += 1
        if self._is_sync:
            handler_finished_future = route._loop.create_future()

            def _handler() -> None:
                try:
                    self.handler(route, route.request)  # type: ignore
                    handler_finished_future.set_result(None)
                except Exception as e:
                    handler_finished_future.set_exception(e)

            # As with event handlers, each route handler is a potentially blocking context
            # so it needs a fiber.
            g = RouteGreenlet(_handler)
            g.switch()
            await handler_finished_future
        else:
            coro_or_future = self.handler(route, route.request)  # type: ignore
            if coro_or_future:
                # separate task so that we get a proper stack trace for exceptions / tracing api_name extraction
                await asyncio.ensure_future(coro_or_future)
        return await handled_future

    async def stop(self, behavior: Literal["ignoreErrors", "wait"]) -> None:
        # When a handler is manually unrouted or its page/context is closed we either
        # - wait for the current handler invocations to finish
        # - or do not wait, if the user opted out of it, but swallow all exceptions
        #   that happen after the unroute/close.
        if behavior == "ignoreErrors":
            self._ignore_exception = True
        else:
            tasks = []
            for activation in self._active_invocations:
                if not activation.route._did_throw:
                    tasks.append(activation.complete)
            await asyncio.gather(*tasks)

    @property
    def will_expire(self) -> bool:
        return self._handled_count + 1 >= self._times

    @staticmethod
    def prepare_interception_patterns(
        handlers: List["RouteHandler"],
    ) -> List[Dict[str, str]]:
        patterns = []
        all = False
        for handler in handlers:
            if isinstance(handler.url, str):
                patterns.append({"glob": handler.url})
            elif isinstance(handler.url, re.Pattern):
                patterns.append(
                    {
                        "regexSource": handler.url.pattern,
                        "regexFlags": escape_regex_flags(handler.url),
                    }
                )
            else:
                all = True
        if all:
            return [{"glob": "**/*"}]
        return patterns


to_snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def to_snake_case(name: str) -> str:
    return to_snake_case_regex.sub(r"_\1", name).lower()


def make_dirs_for_file(path: Union[Path, str]) -> None:
    if not os.path.isabs(path):
        path = Path.cwd() / path
    os.makedirs(os.path.dirname(path), exist_ok=True)


async def async_writefile(file: Union[str, Path], data: Union[str, bytes]) -> None:
    def inner() -> None:
        with open(file, "w" if isinstance(data, str) else "wb") as fh:
            fh.write(data)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, inner)


async def async_readfile(file: Union[str, Path]) -> bytes:
    def inner() -> bytes:
        with open(file, "rb") as fh:
            return fh.read()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, inner)


T = TypeVar("T")


def to_impl(obj: T) -> T:
    if hasattr(obj, "_impl_obj"):
        return cast(Any, obj)._impl_obj
    return obj


def object_to_array(obj: Optional[Dict]) -> Optional[List[NameValue]]:
    if not obj:
        return None
    result = []
    for key, value in obj.items():
        result.append(NameValue(name=key, value=str(value)))
    return result


def is_file_payload(value: Optional[Any]) -> bool:
    return (
        isinstance(value, dict)
        and "name" in value
        and "mimeType" in value
        and "buffer" in value
    )


TEXTUAL_MIME_TYPE = re.compile(
    r"^(text\/.*?|application\/(json|(x-)?javascript|xml.*?|ecmascript|graphql|x-www-form-urlencoded)|image\/svg(\+xml)?|application\/.*?(\+json|\+xml))(;\s*charset=.*)?$"
)


def is_textual_mime_type(mime_type: str) -> bool:
    return bool(TEXTUAL_MIME_TYPE.match(mime_type))

# === NexusCore/openenv\Lib\site-packages\aiohttp\cookiejar.py ===
import asyncio
import calendar
import contextlib
import datetime
import heapq
import itertools
import os  # noqa
import pathlib
import pickle
import re
import time
import warnings
from collections import defaultdict
from collections.abc import Mapping
from http.cookies import BaseCookie, Morsel, SimpleCookie
from typing import (
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from yarl import URL

from ._cookie_helpers import preserve_morsel_with_coded_value
from .abc import AbstractCookieJar, ClearCookiePredicate
from .helpers import is_ip_address
from .typedefs import LooseCookies, PathLike, StrOrURL

__all__ = ("CookieJar", "DummyCookieJar")


CookieItem = Union[str, "Morsel[str]"]

# We cache these string methods here as their use is in performance critical code.
_FORMAT_PATH = "{}/{}".format
_FORMAT_DOMAIN_REVERSED = "{1}.{0}".format

# The minimum number of scheduled cookie expirations before we start cleaning up
# the expiration heap. This is a performance optimization to avoid cleaning up the
# heap too often when there are only a few scheduled expirations.
_MIN_SCHEDULED_COOKIE_EXPIRATION = 100
_SIMPLE_COOKIE = SimpleCookie()


class CookieJar(AbstractCookieJar):
    """Implements cookie storage adhering to RFC 6265."""

    DATE_TOKENS_RE = re.compile(
        r"[\x09\x20-\x2F\x3B-\x40\x5B-\x60\x7B-\x7E]*"
        r"(?P<token>[\x00-\x08\x0A-\x1F\d:a-zA-Z\x7F-\xFF]+)"
    )

    DATE_HMS_TIME_RE = re.compile(r"(\d{1,2}):(\d{1,2}):(\d{1,2})")

    DATE_DAY_OF_MONTH_RE = re.compile(r"(\d{1,2})")

    DATE_MONTH_RE = re.compile(
        "(jan)|(feb)|(mar)|(apr)|(may)|(jun)|(jul)|(aug)|(sep)|(oct)|(nov)|(dec)",
        re.I,
    )

    DATE_YEAR_RE = re.compile(r"(\d{2,4})")

    # calendar.timegm() fails for timestamps after datetime.datetime.max
    # Minus one as a loss of precision occurs when timestamp() is called.
    MAX_TIME = (
        int(datetime.datetime.max.replace(tzinfo=datetime.timezone.utc).timestamp()) - 1
    )
    try:
        calendar.timegm(time.gmtime(MAX_TIME))
    except (OSError, ValueError):
        # Hit the maximum representable time on Windows
        # https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/localtime-localtime32-localtime64
        # Throws ValueError on PyPy 3.9, OSError elsewhere
        MAX_TIME = calendar.timegm((3000, 12, 31, 23, 59, 59, -1, -1, -1))
    except OverflowError:
        # #4515: datetime.max may not be representable on 32-bit platforms
        MAX_TIME = 2**31 - 1
    # Avoid minuses in the future, 3x faster
    SUB_MAX_TIME = MAX_TIME - 1

    def __init__(
        self,
        *,
        unsafe: bool = False,
        quote_cookie: bool = True,
        treat_as_secure_origin: Union[StrOrURL, List[StrOrURL], None] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__(loop=loop)
        self._cookies: DefaultDict[Tuple[str, str], SimpleCookie] = defaultdict(
            SimpleCookie
        )
        self._morsel_cache: DefaultDict[Tuple[str, str], Dict[str, Morsel[str]]] = (
            defaultdict(dict)
        )
        self._host_only_cookies: Set[Tuple[str, str]] = set()
        self._unsafe = unsafe
        self._quote_cookie = quote_cookie
        if treat_as_secure_origin is None:
            treat_as_secure_origin = []
        elif isinstance(treat_as_secure_origin, URL):
            treat_as_secure_origin = [treat_as_secure_origin.origin()]
        elif isinstance(treat_as_secure_origin, str):
            treat_as_secure_origin = [URL(treat_as_secure_origin).origin()]
        else:
            treat_as_secure_origin = [
                URL(url).origin() if isinstance(url, str) else url.origin()
                for url in treat_as_secure_origin
            ]
        self._treat_as_secure_origin = treat_as_secure_origin
        self._expire_heap: List[Tuple[float, Tuple[str, str, str]]] = []
        self._expirations: Dict[Tuple[str, str, str], float] = {}

    @property
    def quote_cookie(self) -> bool:
        return self._quote_cookie

    def save(self, file_path: PathLike) -> None:
        file_path = pathlib.Path(file_path)
        with file_path.open(mode="wb") as f:
            pickle.dump(self._cookies, f, pickle.HIGHEST_PROTOCOL)

    def load(self, file_path: PathLike) -> None:
        file_path = pathlib.Path(file_path)
        with file_path.open(mode="rb") as f:
            self._cookies = pickle.load(f)

    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        if predicate is None:
            self._expire_heap.clear()
            self._cookies.clear()
            self._morsel_cache.clear()
            self._host_only_cookies.clear()
            self._expirations.clear()
            return

        now = time.time()
        to_del = [
            key
            for (domain, path), cookie in self._cookies.items()
            for name, morsel in cookie.items()
            if (
                (key := (domain, path, name)) in self._expirations
                and self._expirations[key] <= now
            )
            or predicate(morsel)
        ]
        if to_del:
            self._delete_cookies(to_del)

    def clear_domain(self, domain: str) -> None:
        self.clear(lambda x: self._is_domain_match(domain, x["domain"]))

    def __iter__(self) -> "Iterator[Morsel[str]]":
        self._do_expiration()
        for val in self._cookies.values():
            yield from val.values()

    def __len__(self) -> int:
        """Return number of cookies.

        This function does not iterate self to avoid unnecessary expiration
        checks.
        """
        return sum(len(cookie.values()) for cookie in self._cookies.values())

    def _do_expiration(self) -> None:
        """Remove expired cookies."""
        if not (expire_heap_len := len(self._expire_heap)):
            return

        # If the expiration heap grows larger than the number expirations
        # times two, we clean it up to avoid keeping expired entries in
        # the heap and consuming memory. We guard this with a minimum
        # threshold to avoid cleaning up the heap too often when there are
        # only a few scheduled expirations.
        if (
            expire_heap_len > _MIN_SCHEDULED_COOKIE_EXPIRATION
            and expire_heap_len > len(self._expirations) * 2
        ):
            # Remove any expired entries from the expiration heap
            # that do not match the expiration time in the expirations
            # as it means the cookie has been re-added to the heap
            # with a different expiration time.
            self._expire_heap = [
                entry
                for entry in self._expire_heap
                if self._expirations.get(entry[1]) == entry[0]
            ]
            heapq.heapify(self._expire_heap)

        now = time.time()
        to_del: List[Tuple[str, str, str]] = []
        # Find any expired cookies and add them to the to-delete list
        while self._expire_heap:
            when, cookie_key = self._expire_heap[0]
            if when > now:
                break
            heapq.heappop(self._expire_heap)
            # Check if the cookie hasn't been re-added to the heap
            # with a different expiration time as it will be removed
            # later when it reaches the top of the heap and its
            # expiration time is met.
            if self._expirations.get(cookie_key) == when:
                to_del.append(cookie_key)

        if to_del:
            self._delete_cookies(to_del)

    def _delete_cookies(self, to_del: List[Tuple[str, str, str]]) -> None:
        for domain, path, name in to_del:
            self._host_only_cookies.discard((domain, name))
            self._cookies[(domain, path)].pop(name, None)
            self._morsel_cache[(domain, path)].pop(name, None)
            self._expirations.pop((domain, path, name), None)

    def _expire_cookie(self, when: float, domain: str, path: str, name: str) -> None:
        cookie_key = (domain, path, name)
        if self._expirations.get(cookie_key) == when:
            # Avoid adding duplicates to the heap
            return
        heapq.heappush(self._expire_heap, (when, cookie_key))
        self._expirations[cookie_key] = when

    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        """Update cookies."""
        hostname = response_url.raw_host

        if not self._unsafe and is_ip_address(hostname):
            # Don't accept cookies from IPs
            return

        if isinstance(cookies, Mapping):
            cookies = cookies.items()

        for name, cookie in cookies:
            if not isinstance(cookie, Morsel):
                tmp = SimpleCookie()
                tmp[name] = cookie  # type: ignore[assignment]
                cookie = tmp[name]

            domain = cookie["domain"]

            # ignore domains with trailing dots
            if domain and domain[-1] == ".":
                domain = ""
                del cookie["domain"]

            if not domain and hostname is not None:
                # Set the cookie's domain to the response hostname
                # and set its host-only-flag
                self._host_only_cookies.add((hostname, name))
                domain = cookie["domain"] = hostname

            if domain and domain[0] == ".":
                # Remove leading dot
                domain = domain[1:]
                cookie["domain"] = domain

            if hostname and not self._is_domain_match(domain, hostname):
                # Setting cookies for different domains is not allowed
                continue

            path = cookie["path"]
            if not path or path[0] != "/":
                # Set the cookie's path to the response path
                path = response_url.path
                if not path.startswith("/"):
                    path = "/"
                else:
                    # Cut everything from the last slash to the end
                    path = "/" + path[1 : path.rfind("/")]
                cookie["path"] = path
            path = path.rstrip("/")

            if max_age := cookie["max-age"]:
                try:
                    delta_seconds = int(max_age)
                    max_age_expiration = min(time.time() + delta_seconds, self.MAX_TIME)
                    self._expire_cookie(max_age_expiration, domain, path, name)
                except ValueError:
                    cookie["max-age"] = ""

            elif expires := cookie["expires"]:
                if expire_time := self._parse_date(expires):
                    self._expire_cookie(expire_time, domain, path, name)
                else:
                    cookie["expires"] = ""

            key = (domain, path)
            if self._cookies[key].get(name) != cookie:
                # Don't blow away the cache if the same
                # cookie gets set again
                self._cookies[key][name] = cookie
                self._morsel_cache[key].pop(name, None)

        self._do_expiration()

    def filter_cookies(self, request_url: URL = URL()) -> "BaseCookie[str]":
        """Returns this jar's cookies filtered by their attributes."""
        # We always use BaseCookie now since all
        # cookies set on on filtered are fully constructed
        # Morsels, not just names and values.
        filtered: BaseCookie[str] = BaseCookie()
        if not self._cookies:
            # Skip do_expiration() if there are no cookies.
            return filtered
        self._do_expiration()
        if not self._cookies:
            # Skip rest of function if no non-expired cookies.
            return filtered
        if type(request_url) is not URL:
            warnings.warn(
                "filter_cookies expects yarl.URL instances only,"
                f"and will stop working in 4.x, got {type(request_url)}",
                DeprecationWarning,
                stacklevel=2,
            )
            request_url = URL(request_url)
        hostname = request_url.raw_host or ""

        is_not_secure = request_url.scheme not in ("https", "wss")
        if is_not_secure and self._treat_as_secure_origin:
            request_origin = URL()
            with contextlib.suppress(ValueError):
                request_origin = request_url.origin()
            is_not_secure = request_origin not in self._treat_as_secure_origin

        # Send shared cookie
        key = ("", "")
        for c in self._cookies[key].values():
            # Check cache first
            if c.key in self._morsel_cache[key]:
                filtered[c.key] = self._morsel_cache[key][c.key]
                continue

            # Build and cache the morsel
            mrsl_val = self._build_morsel(c)
            self._morsel_cache[key][c.key] = mrsl_val
            filtered[c.key] = mrsl_val

        if is_ip_address(hostname):
            if not self._unsafe:
                return filtered
            domains: Iterable[str] = (hostname,)
        else:
            # Get all the subdomains that might match a cookie (e.g. "foo.bar.com", "bar.com", "com")
            domains = itertools.accumulate(
                reversed(hostname.split(".")), _FORMAT_DOMAIN_REVERSED
            )

        # Get all the path prefixes that might match a cookie (e.g. "", "/foo", "/foo/bar")
        paths = itertools.accumulate(request_url.path.split("/"), _FORMAT_PATH)
        # Create every combination of (domain, path) pairs.
        pairs = itertools.product(domains, paths)

        path_len = len(request_url.path)
        # Point 2: https://www.rfc-editor.org/rfc/rfc6265.html#section-5.4
        for p in pairs:
            if p not in self._cookies:
                continue
            for name, cookie in self._cookies[p].items():
                domain = cookie["domain"]

                if (domain, name) in self._host_only_cookies and domain != hostname:
                    continue

                # Skip edge case when the cookie has a trailing slash but request doesn't.
                if len(cookie["path"]) > path_len:
                    continue

                if is_not_secure and cookie["secure"]:
                    continue

                # We already built the Morsel so reuse it here
                if name in self._morsel_cache[p]:
                    filtered[name] = self._morsel_cache[p][name]
                    continue

                # Build and cache the morsel
                mrsl_val = self._build_morsel(cookie)
                self._morsel_cache[p][name] = mrsl_val
                filtered[name] = mrsl_val

        return filtered

    def _build_morsel(self, cookie: Morsel[str]) -> Morsel[str]:
        """Build a morsel for sending, respecting quote_cookie setting."""
        if self._quote_cookie and cookie.coded_value and cookie.coded_value[0] == '"':
            return preserve_morsel_with_coded_value(cookie)
        morsel: Morsel[str] = Morsel()
        if self._quote_cookie:
            value, coded_value = _SIMPLE_COOKIE.value_encode(cookie.value)
        else:
            coded_value = value = cookie.value
        # We use __setstate__ instead of the public set() API because it allows us to
        # bypass validation and set already validated state. This is more stable than
        # setting protected attributes directly and unlikely to change since it would
        # break pickling.
        morsel.__setstate__({"key": cookie.key, "value": value, "coded_value": coded_value})  # type: ignore[attr-defined]
        return morsel

    @staticmethod
    def _is_domain_match(domain: str, hostname: str) -> bool:
        """Implements domain matching adhering to RFC 6265."""
        if hostname == domain:
            return True

        if not hostname.endswith(domain):
            return False

        non_matching = hostname[: -len(domain)]

        if not non_matching.endswith("."):
            return False

        return not is_ip_address(hostname)

    @classmethod
    def _parse_date(cls, date_str: str) -> Optional[int]:
        """Implements date string parsing adhering to RFC 6265."""
        if not date_str:
            return None

        found_time = False
        found_day = False
        found_month = False
        found_year = False

        hour = minute = second = 0
        day = 0
        month = 0
        year = 0

        for token_match in cls.DATE_TOKENS_RE.finditer(date_str):

            token = token_match.group("token")

            if not found_time:
                time_match = cls.DATE_HMS_TIME_RE.match(token)
                if time_match:
                    found_time = True
                    hour, minute, second = (int(s) for s in time_match.groups())
                    continue

            if not found_day:
                day_match = cls.DATE_DAY_OF_MONTH_RE.match(token)
                if day_match:
                    found_day = True
                    day = int(day_match.group())
                    continue

            if not found_month:
                month_match = cls.DATE_MONTH_RE.match(token)
                if month_match:
                    found_month = True
                    assert month_match.lastindex is not None
                    month = month_match.lastindex
                    continue

            if not found_year:
                year_match = cls.DATE_YEAR_RE.match(token)
                if year_match:
                    found_year = True
                    year = int(year_match.group())

        if 70 <= year <= 99:
            year += 1900
        elif 0 <= year <= 69:
            year += 2000

        if False in (found_day, found_month, found_year, found_time):
            return None

        if not 1 <= day <= 31:
            return None

        if year < 1601 or hour > 23 or minute > 59 or second > 59:
            return None

        return calendar.timegm((year, month, day, hour, minute, second, -1, -1, -1))


class DummyCookieJar(AbstractCookieJar):
    """Implements a dummy cookie storage.

    It can be used with the ClientSession when no cookie processing is needed.

    """

    def __init__(self, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(loop=loop)

    def __iter__(self) -> "Iterator[Morsel[str]]":
        while False:
            yield None

    def __len__(self) -> int:
        return 0

    @property
    def quote_cookie(self) -> bool:
        return True

    def clear(self, predicate: Optional[ClearCookiePredicate] = None) -> None:
        pass

    def clear_domain(self, domain: str) -> None:
        pass

    def update_cookies(self, cookies: LooseCookies, response_url: URL = URL()) -> None:
        pass

    def filter_cookies(self, request_url: URL) -> "BaseCookie[str]":
        return SimpleCookie()

# === NexusCore/openenv\Lib\site-packages\google\auth\credentials.py ===
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


"""Interfaces for credentials."""

import abc
from enum import Enum
import os

from google.auth import _helpers, environment_vars
from google.auth import exceptions
from google.auth import metrics
from google.auth._credentials_base import _BaseCredentials
from google.auth._refresh_worker import RefreshThreadManager

DEFAULT_UNIVERSE_DOMAIN = "googleapis.com"


class Credentials(_BaseCredentials):
    """Base class for all credentials.

    All credentials have a :attr:`token` that is used for authentication and
    may also optionally set an :attr:`expiry` to indicate when the token will
    no longer be valid.

    Most credentials will be :attr:`invalid` until :meth:`refresh` is called.
    Credentials can do this automatically before the first HTTP request in
    :meth:`before_request`.

    Although the token and expiration will change as the credentials are
    :meth:`refreshed <refresh>` and used, credentials should be considered
    immutable. Various credentials will accept configuration such as private
    keys, scopes, and other options. These options are not changeable after
    construction. Some classes will provide mechanisms to copy the credentials
    with modifications such as :meth:`ScopedCredentials.with_scopes`.
    """

    def __init__(self):
        super(Credentials, self).__init__()

        self.expiry = None
        """Optional[datetime]: When the token expires and is no longer valid.
        If this is None, the token is assumed to never expire."""
        self._quota_project_id = None
        """Optional[str]: Project to use for quota and billing purposes."""
        self._trust_boundary = None
        """Optional[dict]: Cache of a trust boundary response which has a list
        of allowed regions and an encoded string representation of credentials
        trust boundary."""
        self._universe_domain = DEFAULT_UNIVERSE_DOMAIN
        """Optional[str]: The universe domain value, default is googleapis.com
        """

        self._use_non_blocking_refresh = False
        self._refresh_worker = RefreshThreadManager()

    @property
    def expired(self):
        """Checks if the credentials are expired.

        Note that credentials can be invalid but not expired because
        Credentials with :attr:`expiry` set to None is considered to never
        expire.

        .. deprecated:: v2.24.0
          Prefer checking :attr:`token_state` instead.
        """
        if not self.expiry:
            return False
        # Remove some threshold from expiry to err on the side of reporting
        # expiration early so that we avoid the 401-refresh-retry loop.
        skewed_expiry = self.expiry - _helpers.REFRESH_THRESHOLD
        return _helpers.utcnow() >= skewed_expiry

    @property
    def valid(self):
        """Checks the validity of the credentials.

        This is True if the credentials have a :attr:`token` and the token
        is not :attr:`expired`.

        .. deprecated:: v2.24.0
          Prefer checking :attr:`token_state` instead.
        """
        return self.token is not None and not self.expired

    @property
    def token_state(self):
        """
        See `:obj:`TokenState`
        """
        if self.token is None:
            return TokenState.INVALID

        # Credentials that can't expire are always treated as fresh.
        if self.expiry is None:
            return TokenState.FRESH

        expired = _helpers.utcnow() >= self.expiry
        if expired:
            return TokenState.INVALID

        is_stale = _helpers.utcnow() >= (self.expiry - _helpers.REFRESH_THRESHOLD)
        if is_stale:
            return TokenState.STALE

        return TokenState.FRESH

    @property
    def quota_project_id(self):
        """Project to use for quota and billing purposes."""
        return self._quota_project_id

    @property
    def universe_domain(self):
        """The universe domain value."""
        return self._universe_domain

    def get_cred_info(self):
        """The credential information JSON.

        The credential information will be added to auth related error messages
        by client library.

        Returns:
            Mapping[str, str]: The credential information JSON.
        """
        return None

    @abc.abstractmethod
    def refresh(self, request):
        """Refreshes the access token.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If the credentials could
                not be refreshed.
        """
        # pylint: disable=missing-raises-doc
        # (pylint doesn't recognize that this is abstract)
        raise NotImplementedError("Refresh must be implemented")

    def _metric_header_for_usage(self):
        """The x-goog-api-client header for token usage metric.

        This header will be added to the API service requests in before_request
        method. For example, "cred-type/sa-jwt" means service account self
        signed jwt access token is used in the API service request
        authorization header. Children credentials classes need to override
        this method to provide the header value, if the token usage metric is
        needed.

        Returns:
            str: The x-goog-api-client header value.
        """
        return None

    def apply(self, headers, token=None):
        """Apply the token to the authentication header.

        Args:
            headers (Mapping): The HTTP request headers.
            token (Optional[str]): If specified, overrides the current access
                token.
        """
        self._apply(headers, token=token)
        """Trust boundary value will be a cached value from global lookup.

        The response of trust boundary will be a list of regions and a hex
        encoded representation.

        An example of global lookup response:
        {
          "locations": [
            "us-central1", "us-east1", "europe-west1", "asia-east1"
          ]
          "encoded_locations": "0xA30"
        }
        """
        if self._trust_boundary is not None:
            headers["x-allowed-locations"] = self._trust_boundary["encoded_locations"]
        if self.quota_project_id:
            headers["x-goog-user-project"] = self.quota_project_id

    def _blocking_refresh(self, request):
        if not self.valid:
            self.refresh(request)

    def _non_blocking_refresh(self, request):
        use_blocking_refresh_fallback = False

        if self.token_state == TokenState.STALE:
            use_blocking_refresh_fallback = not self._refresh_worker.start_refresh(
                self, request
            )

        if self.token_state == TokenState.INVALID or use_blocking_refresh_fallback:
            self.refresh(request)
            # If the blocking refresh succeeds then we can clear the error info
            # on the background refresh worker, and perform refreshes in a
            # background thread.
            self._refresh_worker.clear_error()

    def before_request(self, request, method, url, headers):
        """Performs credential-specific before request logic.

        Refreshes the credentials if necessary, then calls :meth:`apply` to
        apply the token to the authentication header.

        Args:
            request (google.auth.transport.Request): The object used to make
                HTTP requests.
            method (str): The request's HTTP method or the RPC method being
                invoked.
            url (str): The request's URI or the RPC service's URI.
            headers (Mapping): The request's headers.
        """
        # pylint: disable=unused-argument
        # (Subclasses may use these arguments to ascertain information about
        # the http request.)
        if self._use_non_blocking_refresh:
            self._non_blocking_refresh(request)
        else:
            self._blocking_refresh(request)

        metrics.add_metric_header(headers, self._metric_header_for_usage())
        self.apply(headers)

    def with_non_blocking_refresh(self):
        self._use_non_blocking_refresh = True


class CredentialsWithQuotaProject(Credentials):
    """Abstract base for credentials supporting ``with_quota_project`` factory"""

    def with_quota_project(self, quota_project_id):
        """Returns a copy of these credentials with a modified quota project.

        Args:
            quota_project_id (str): The project to use for quota and
                billing purposes

        Returns:
            google.auth.credentials.Credentials: A new credentials instance.
        """
        raise NotImplementedError("This credential does not support quota project.")

    def with_quota_project_from_environment(self):
        quota_from_env = os.environ.get(environment_vars.GOOGLE_CLOUD_QUOTA_PROJECT)
        if quota_from_env:
            return self.with_quota_project(quota_from_env)
        return self


class CredentialsWithTokenUri(Credentials):
    """Abstract base for credentials supporting ``with_token_uri`` factory"""

    def with_token_uri(self, token_uri):
        """Returns a copy of these credentials with a modified token uri.

        Args:
            token_uri (str): The uri to use for fetching/exchanging tokens

        Returns:
            google.auth.credentials.Credentials: A new credentials instance.
        """
        raise NotImplementedError("This credential does not use token uri.")


class CredentialsWithUniverseDomain(Credentials):
    """Abstract base for credentials supporting ``with_universe_domain`` factory"""

    def with_universe_domain(self, universe_domain):
        """Returns a copy of these credentials with a modified universe domain.

        Args:
            universe_domain (str): The universe domain to use

        Returns:
            google.auth.credentials.Credentials: A new credentials instance.
        """
        raise NotImplementedError(
            "This credential does not support with_universe_domain."
        )


class AnonymousCredentials(Credentials):
    """Credentials that do not provide any authentication information.

    These are useful in the case of services that support anonymous access or
    local service emulators that do not use credentials.
    """

    @property
    def expired(self):
        """Returns `False`, anonymous credentials never expire."""
        return False

    @property
    def valid(self):
        """Returns `True`, anonymous credentials are always valid."""
        return True

    def refresh(self, request):
        """Raises :class:``InvalidOperation``, anonymous credentials cannot be
        refreshed."""
        raise exceptions.InvalidOperation("Anonymous credentials cannot be refreshed.")

    def apply(self, headers, token=None):
        """Anonymous credentials do nothing to the request.

        The optional ``token`` argument is not supported.

        Raises:
            google.auth.exceptions.InvalidValue: If a token was specified.
        """
        if token is not None:
            raise exceptions.InvalidValue("Anonymous credentials don't support tokens.")

    def before_request(self, request, method, url, headers):
        """Anonymous credentials do nothing to the request."""


class ReadOnlyScoped(metaclass=abc.ABCMeta):
    """Interface for credentials whose scopes can be queried.

    OAuth 2.0-based credentials allow limiting access using scopes as described
    in `RFC6749 Section 3.3`_.
    If a credential class implements this interface then the credentials either
    use scopes in their implementation.

    Some credentials require scopes in order to obtain a token. You can check
    if scoping is necessary with :attr:`requires_scopes`::

        if credentials.requires_scopes:
            # Scoping is required.
            credentials = credentials.with_scopes(scopes=['one', 'two'])

    Credentials that require scopes must either be constructed with scopes::

        credentials = SomeScopedCredentials(scopes=['one', 'two'])

    Or must copy an existing instance using :meth:`with_scopes`::

        scoped_credentials = credentials.with_scopes(scopes=['one', 'two'])

    Some credentials have scopes but do not allow or require scopes to be set,
    these credentials can be used as-is.

    .. _RFC6749 Section 3.3: https://tools.ietf.org/html/rfc6749#section-3.3
    """

    def __init__(self):
        super(ReadOnlyScoped, self).__init__()
        self._scopes = None
        self._default_scopes = None

    @property
    def scopes(self):
        """Sequence[str]: the credentials' current set of scopes."""
        return self._scopes

    @property
    def default_scopes(self):
        """Sequence[str]: the credentials' current set of default scopes."""
        return self._default_scopes

    @abc.abstractproperty
    def requires_scopes(self):
        """True if these credentials require scopes to obtain an access token.
        """
        return False

    def has_scopes(self, scopes):
        """Checks if the credentials have the given scopes.

        .. warning: This method is not guaranteed to be accurate if the
            credentials are :attr:`~Credentials.invalid`.

        Args:
            scopes (Sequence[str]): The list of scopes to check.

        Returns:
            bool: True if the credentials have the given scopes.
        """
        credential_scopes = (
            self._scopes if self._scopes is not None else self._default_scopes
        )
        return set(scopes).issubset(set(credential_scopes or []))


class Scoped(ReadOnlyScoped):
    """Interface for credentials whose scopes can be replaced while copying.

    OAuth 2.0-based credentials allow limiting access using scopes as described
    in `RFC6749 Section 3.3`_.
    If a credential class implements this interface then the credentials either
    use scopes in their implementation.

    Some credentials require scopes in order to obtain a token. You can check
    if scoping is necessary with :attr:`requires_scopes`::

        if credentials.requires_scopes:
            # Scoping is required.
            credentials = credentials.create_scoped(['one', 'two'])

    Credentials that require scopes must either be constructed with scopes::

        credentials = SomeScopedCredentials(scopes=['one', 'two'])

    Or must copy an existing instance using :meth:`with_scopes`::

        scoped_credentials = credentials.with_scopes(scopes=['one', 'two'])

    Some credentials have scopes but do not allow or require scopes to be set,
    these credentials can be used as-is.

    .. _RFC6749 Section 3.3: https://tools.ietf.org/html/rfc6749#section-3.3
    """

    @abc.abstractmethod
    def with_scopes(self, scopes, default_scopes=None):
        """Create a copy of these credentials with the specified scopes.

        Args:
            scopes (Sequence[str]): The list of scopes to attach to the
                current credentials.

        Raises:
            NotImplementedError: If the credentials' scopes can not be changed.
                This can be avoided by checking :attr:`requires_scopes` before
                calling this method.
        """
        raise NotImplementedError("This class does not require scoping.")


def with_scopes_if_required(credentials, scopes, default_scopes=None):
    """Creates a copy of the credentials with scopes if scoping is required.

    This helper function is useful when you do not know (or care to know) the
    specific type of credentials you are using (such as when you use
    :func:`google.auth.default`). This function will call
    :meth:`Scoped.with_scopes` if the credentials are scoped credentials and if
    the credentials require scoping. Otherwise, it will return the credentials
    as-is.

    Args:
        credentials (google.auth.credentials.Credentials): The credentials to
            scope if necessary.
        scopes (Sequence[str]): The list of scopes to use.
        default_scopes (Sequence[str]): Default scopes passed by a
            Google client library. Use 'scopes' for user-defined scopes.

    Returns:
        google.auth.credentials.Credentials: Either a new set of scoped
            credentials, or the passed in credentials instance if no scoping
            was required.
    """
    if isinstance(credentials, Scoped) and credentials.requires_scopes:
        return credentials.with_scopes(scopes, default_scopes=default_scopes)
    else:
        return credentials


class Signing(metaclass=abc.ABCMeta):
    """Interface for credentials that can cryptographically sign messages."""

    @abc.abstractmethod
    def sign_bytes(self, message):
        """Signs the given message.

        Args:
            message (bytes): The message to sign.

        Returns:
            bytes: The message's cryptographic signature.
        """
        # pylint: disable=missing-raises-doc,redundant-returns-doc
        # (pylint doesn't recognize that this is abstract)
        raise NotImplementedError("Sign bytes must be implemented.")

    @abc.abstractproperty
    def signer_email(self):
        """Optional[str]: An email address that identifies the signer."""
        # pylint: disable=missing-raises-doc
        # (pylint doesn't recognize that this is abstract)
        raise NotImplementedError("Signer email must be implemented.")

    @abc.abstractproperty
    def signer(self):
        """google.auth.crypt.Signer: The signer used to sign bytes."""
        # pylint: disable=missing-raises-doc
        # (pylint doesn't recognize that this is abstract)
        raise NotImplementedError("Signer must be implemented.")


class TokenState(Enum):
    """
    Tracks the state of a token.
    FRESH: The token is valid. It is not expired or close to expired, or the token has no expiry.
    STALE: The token is close to expired, and should be refreshed. The token can be used normally.
    INVALID: The token is expired or invalid. The token cannot be used for a normal operation.
    """

    FRESH = 1
    STALE = 2
    INVALID = 3

# === NexusCore/openenv\Lib\site-packages\IPython\utils\PyColorize.py ===
import keyword
import os
import sys
import token
import tokenize
import warnings
from io import StringIO
from typing import TypeAlias

import pygments
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.style import Style
from pygments.styles import get_style_by_name
from pygments.token import Token, _TokenType
from functools import cache

from typing import TypedDict


TokenStream: TypeAlias = list[tuple[_TokenType, str]]


__all__ = ["Parser", "Theme"]


class Symbols(TypedDict):
    top_line: str
    arrow_body: str
    arrow_head: str


_default_symbols: Symbols = {
    "top_line": "-",
    "arrow_body": "-",
    "arrow_head": ">",
}


class Theme:
    name: str
    base: str | None
    extra_style: dict[_TokenType, str]
    symbols: Symbols

    def __init__(self, name, base, extra_style, *, symbols={}):
        self.name = name
        self.base = base
        self.extra_style = extra_style
        self.symbols = {**_default_symbols, **symbols}
        self._formatter = Terminal256Formatter(style=self.as_pygments_style())

    @cache
    def as_pygments_style(self):
        if self.base is not None:
            base_styles = get_style_by_name(self.base).styles
        else:
            base_styles = {}

        class MyStyle(Style):
            styles = {**base_styles, **self.extra_style}

        return MyStyle

    def format(self, stream: TokenStream) -> str:

        return pygments.format(stream, self._formatter)

    def make_arrow(self, width: int):
        """generate the leading arrow in front of traceback or debugger"""
        if width >= 2:
            return (
                self.symbols["arrow_body"] * (width - 2)
                + self.symbols["arrow_head"]
                + " "
            )
        elif width == 1:
            return self.symbols["arrow_head"]
        return ""


generate_tokens = tokenize.generate_tokens


#############################################################################
### Python Source Parser (does Highlighting)
#############################################################################

_KEYWORD = token.NT_OFFSET + 1
_TEXT = token.NT_OFFSET + 2

# ****************************************************************************

_pygment_token_mapping: dict[int, _TokenType] = {
    token.NUMBER: Token.Literal.Number,
    token.OP: Token.Operator,
    token.STRING: Token.Literal.String,
    token.COMMENT: Token.Comment,
    token.NAME: Token.Name,
    token.ERRORTOKEN: Token.Error,
    _KEYWORD: Token.Keyword,
    _TEXT: Token.Text,
}

# technically BW is not nocolor, we should have a no-style, style
nocolors_theme = Theme("nocolor", None, {})


linux_theme = Theme(
    "linux",
    "monokai",
    {
        Token.Header: "ansibrightred",
        Token.LinenoEm: "ansibrightgreen",
        Token.Lineno: "ansigreen",
        Token.ValEm: "ansibrightblue",
        Token.VName: "ansicyan",
        Token.Caret: "",
        Token.Filename: "ansibrightgreen",
        Token.ExcName: "ansibrightred",
        Token.Topline: "ansibrightred",
        Token.FilenameEm: "ansigreen",
        Token.Normal: "",
        Token.NormalEm: "ansibrightcyan",
        Token.Line: "ansiyellow",
        Token.TB.Name: "ansimagenta",
        Token.TB.NameEm: "ansibrightmagenta",
        Token.Breakpoint: "",
        Token.Breakpoint.Enabled: "ansibrightred",
        Token.Breakpoint.Disabled: "ansired",
        Token.Prompt: "ansibrightgreen",
        Token.PromptNum: "ansigreen bold",
        Token.OutPrompt: "ansibrightred",
        Token.OutPromptNum: "ansired bold",
    },
)

neutral_pygments_equiv = {
    Token.Header: "ansired",
    Token.LinenoEm: "ansigreen",
    Token.Lineno: "ansibrightgreen",
    Token.ValEm: "ansiblue",
    Token.VName: "ansicyan",
    Token.Caret: "",
    Token.Filename: "ansibrightgreen",
    Token.FilenameEm: "ansigreen",
    Token.ExcName: "ansired",
    Token.Topline: "ansired",
    Token.Normal: "",
    Token.NormalEm: "ansicyan",
    Token.Line: "ansired",
    Token.TB.Name: "ansibrightmagenta",
    Token.TB.NameEm: "ansimagenta",
    Token.Breakpoint: "",
    Token.Breakpoint.Enabled: "ansibrightred",
    Token.Breakpoint.Disabled: "ansired",
    ## specific override of pygments defaults for visibility
    Token.Number: "ansigreen",
    Token.Operator: "noinherit",
    Token.String: "ansiyellow",
    Token.Name.Function: "ansiblue",
    Token.Name.Class: "bold ansiblue",
    Token.Name.Namespace: "bold ansiblue",
    Token.Name.Variable.Magic: "ansiblue",
    Token.Prompt: "ansigreen",
    Token.OutPrompt: "ansired",
}


neutral_pygments_nt = {
    **neutral_pygments_equiv,
    Token.PromptNum: "ansigreen bold",
    Token.OutPromptNum: "ansired bold",
}
neutral_pygments_posix = {
    **neutral_pygments_equiv,
    Token.PromptNum: "ansibrightgreen bold",
    Token.OutPromptNum: "ansibrightred bold",
}


neutral_nt = Theme("neutral:nt", "default", neutral_pygments_nt)
neutral_posix = Theme("neutral:posix", "default", neutral_pygments_posix)


# Hack: the 'neutral' colours are not very visible on a dark background on
# Windows. Since Windows command prompts have a dark background by default, and
# relatively few users are likely to alter that, we will use the 'Linux' colours,
# designed for a dark background, as the default on Windows. Changing it here
# avoids affecting the prompt colours rendered by prompt_toolkit, where the
# neutral defaults do work OK.
if os.name == "nt":
    neutral_theme = neutral_nt
else:
    neutral_theme = neutral_posix


lightbg_theme = Theme(
    "lightbg",
    "pastie",
    {
        Token.Header: "ansired",
        Token.LinenoEm: "ansigreen",
        Token.Lineno: "ansibrightgreen",
        Token.ValEm: "ansiblue",
        Token.VName: "ansicyan",
        Token.Caret: "",
        Token.Filename: "ansigreen",
        Token.FilenameEm: "ansibrightgreen",
        Token.ExcName: "ansired",
        Token.Topline: "ansired",
        Token.Normal: "",
        Token.NormalEm: "ansicyan",
        Token.Line: "ansired",
        Token.TB.Name: "ansibrightmagenta",
        Token.TB.NameEm: "ansimagenta",
        Token.Breakpoint: "",
        Token.Breakpoint.Enabled: "ansibrightred",
        Token.Breakpoint.Disabled: "ansired",
        Token.Prompt: "ansibrightblue",
        Token.PromptNum: "ansiblue bold",
        Token.OutPrompt: "ansibrightred",
        Token.OutPromptNum: "ansired bold",
    },
)

PRIDE_RED = "#E40303"
PRIDE_ORANGE = "#FF8C00"
PRIDE_YELLOW = "#FFED00"
PRIDE_GREEN = "#008026"
PRIDE_INDIGO = "#004CFF"
PRIDE_VIOLET = "#732982"
pride_theme = Theme(
    "pride",
    "pastie",
    {
        Token.Header: PRIDE_INDIGO,
        Token.LinenoEm: f"{PRIDE_GREEN} italic",
        Token.Lineno: f"{PRIDE_GREEN} bold",
        Token.ValEm: f"{PRIDE_INDIGO} italic",
        Token.VName: "ansicyan",
        Token.Caret: "",
        Token.Filename: f"{PRIDE_YELLOW}",
        Token.FilenameEm: f"bg:{PRIDE_VIOLET}",
        Token.ExcName: f"{PRIDE_ORANGE}",
        Token.Topline: f"{PRIDE_RED}",
        Token.Normal: "",
        Token.NormalEm: "bold",
        Token.Line: "ansired",
        Token.TB.Name: "ansibrightmagenta",
        Token.TB.NameEm: "ansimagenta",
        Token.Breakpoint: "",
        Token.Breakpoint.Enabled: "ansibrightred",
        Token.Breakpoint.Disabled: "ansired",
        Token.Prompt: "ansibrightblue",
        Token.Prompt.Continuation.L1: f"ansiwhite bg:{PRIDE_RED}",
        Token.Prompt.Continuation.L2: f"ansiwhite bg:{PRIDE_ORANGE}",
        Token.Prompt.Continuation.L3: f"ansiblack bg:{PRIDE_YELLOW}",
        Token.Prompt.Continuation.L4: f"ansiwhite bg:{PRIDE_GREEN}",
        Token.Prompt.Continuation.L5: f"ansiwhite bg:{PRIDE_INDIGO}",
        Token.Prompt.Continuation.L6: f"ansiwhite bg:{PRIDE_VIOLET}",
        Token.PromptNum: "ansiblue bold",
        Token.OutPrompt: "ansibrightred",
        Token.OutPromptNum: "ansired bold",
    },
    symbols={"arrow_body": "\u2500", "arrow_head": "\u25b6", "top_line": "\u2500"},
)


C1 = "#D52D00"
C2 = "#EF7627"
C3 = "#FF9A56"
White = "#FFFFFF"
C5 = "#D162A4"
C6 = "#B55690"
C7 = "#A30262"

pl = {
    # Token.Whitespace: "#bbbbbb",
    Token.Comment: "#888888",
    Token.String: C5,
    Token.String.Escape: C1,
    Token.Keyword: f"italic {C2}",
    Token.Name.Class: C2,
    Token.Name.Exception: C1,
    Token.Name.Builtin: C3,
    Token.Name.Variable: C6,
    Token.Name.Constant: C7,
    Token.Name.Decorator: C2,
    Token.Number: C7,
    Token.Generic.Deleted: f"bg:{C1} #000000",
    Token.Generic.Emph: "italic",
    Token.Generic.Strong: "bold",
    Token.Generic.EmphStrong: "bold italic",
}

pridel_theme = Theme(
    "pride:l",
    None,
    {
        Token.Header: C3,
        Token.LinenoEm: C3,
        Token.Lineno: C2,
        Token.ValEm: C2,
        Token.VName: C2,
        Token.Caret: "",
        Token.Filename: C2,
        Token.FilenameEm: C3,
        Token.ExcName: C1,
        Token.Topline: C1,
        Token.Normal: "",
        Token.NormalEm: "bold",
        Token.Line: C2,
        Token.TB.Name: C6,
        Token.TB.NameEm: C7,
        Token.Breakpoint: "",
        Token.Breakpoint.Enabled: C1,
        Token.Breakpoint.Disabled: C7,
        Token.Prompt: C1,
        Token.PromptNum: C2,
        Token.Prompt.Continuation: C7,
        Token.Prompt.Continuation.L1: C2,
        Token.Prompt.Continuation.L2: C3,
        Token.Prompt.Continuation.L3: White,
        Token.Prompt.Continuation.L4: C5,
        Token.Prompt.Continuation.L5: C6,
        Token.Prompt.Continuation.L6: C7,
        Token.OutPrompt: C6,
        Token.OutPromptNum: C5,
        **pl,
    },
    symbols={"arrow_body": "\u2500", "arrow_head": "\u25b6", "top_line": "\u2500"},
)

theme_table: dict[str, Theme] = {
    "nocolor": nocolors_theme,
    "linux": linux_theme,
    "neutral": neutral_theme,
    "neutral:nt": neutral_nt,
    "neutral:posix": neutral_posix,
    "lightbg": lightbg_theme,
    "pride": pride_theme,
    "pride:l": pridel_theme,
}


class Parser:
    """Format colored Python source."""

    _theme_name: str

    def __init__(self, out=sys.stdout, *, theme_name: str = None):
        """Create a parser with a specified color table and output channel.

        Call format() to process code.
        """

        assert theme_name is not None

        self.out = out
        self.pos = None
        self.lines = None
        self.raw = None
        if theme_name is not None:
            if theme_name in ["Linux", "LightBG", "Neutral", "NoColor"]:
                warnings.warn(
                    f"Theme names and color schemes are lowercase in IPython 9.0 use {theme_name.lower()} instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
                theme_name = theme_name.lower()
        if not theme_name:
            self.theme_name = "nocolor"
        else:
            self.theme_name = theme_name

    @property
    def theme_name(self):
        return self._theme_name

    @theme_name.setter
    def theme_name(self, value):
        assert value == value.lower()
        self._theme_name = value

    @property
    def style(self):
        assert False
        return self._theme_name

    @style.setter
    def set(self, val):
        assert False
        assert val == val.lower()
        self._theme_name = val

    def format(self, raw, out=None):
        return self.format2(raw, out)[0]

    def format2(self, raw, out=None):
        """Parse and send the colored source.

        If out is not specified, the defaults (given to constructor) are used.

        out should be a file-type object. Optionally, out can be given as the
        string 'str' and the parser will automatically return the output in a
        string."""

        string_output = 0
        if out == "str" or self.out == "str" or isinstance(self.out, StringIO):
            # XXX - I don't really like this state handling logic, but at this
            # point I don't want to make major changes, so adding the
            # isinstance() check is the simplest I can do to ensure correct
            # behavior.
            out_old = self.out
            self.out = StringIO()
            string_output = 1
        elif out is not None:
            self.out = out
        else:
            raise ValueError(
                '`out` or `self.out` should be file-like or the value `"str"`'
            )

        # Fast return of the unmodified input for nocolor scheme
        # TODO:
        if self.theme_name == "nocolor":
            error = False
            self.out.write(raw)
            if string_output:
                return raw, error
            return None, error

        # local shorthands

        # Remove trailing whitespace and normalize tabs
        self.raw = raw.expandtabs().rstrip()

        # store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0
        raw_find = self.raw.find
        lines_append = self.lines.append
        while True:
            pos = raw_find("\n", pos) + 1
            if not pos:
                break
            lines_append(pos)
        lines_append(len(self.raw))

        # parse the source and write it
        self.pos = 0
        text = StringIO(self.raw)

        error = False
        try:
            for atoken in generate_tokens(text.readline):
                self(*atoken)
        except tokenize.TokenError as ex:
            msg = ex.args[0]
            line = ex.args[1][0]
            self.out.write(
                theme_table[self.theme_name].format(
                    [
                        (Token, "\n\n"),
                        (
                            Token.Error,
                            f"*** ERROR: {msg}{self.raw[self.lines[line] :]}",
                        ),
                        (Token, "\n"),
                    ]
                )
            )
            error = True
        self.out.write(
            theme_table[self.theme_name].format(
                [
                    (Token, "\n"),
                ]
            )
        )

        if string_output:
            output = self.out.getvalue()
            self.out = out_old
            return (output, error)
        return (None, error)

    def _inner_call_(self, toktype, toktext, start_pos):
        """like call but write to a temporary buffer"""
        srow, scol = start_pos

        # calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)

        # send the original whitespace, if needed
        if newpos > oldpos:
            acc = self.raw[oldpos:newpos]
        else:
            acc = ""

        # skip indenting tokens
        if toktype in [token.INDENT, token.DEDENT]:
            self.pos = newpos
            return acc

        # map token type to a color group
        if token.LPAR <= toktype <= token.OP:
            toktype = token.OP
        elif toktype == token.NAME and keyword.iskeyword(toktext):
            toktype = _KEYWORD
        pyg_tok_type = _pygment_token_mapping.get(toktype, Token.Text)

        # send text, pygments should take care of splitting on newline and resending
        # the correct self.colors after the new line, which is necessary for pagers
        acc += theme_table[self.theme_name].format([(pyg_tok_type, toktext)])
        return acc

    def __call__(self, toktype, toktext, start_pos, end_pos, line):
        """Token handler, with syntax highlighting."""
        self.out.write(self._inner_call_(toktype, toktext, start_pos))

# === NexusCore/openenv\Lib\site-packages\jedi\api\helpers.py ===
"""
Helpers for the API
"""
import re
from collections import namedtuple
from textwrap import dedent
from itertools import chain
from functools import wraps
from inspect import Parameter

from parso.python.parser import Parser
from parso.python import tree

from jedi.inference.base_value import NO_VALUES
from jedi.inference.syntax_tree import infer_atom
from jedi.inference.helpers import infer_call_of_leaf
from jedi.inference.compiled import get_string_value_set
from jedi.cache import signature_time_cache, memoize_method
from jedi.parser_utils import get_parent_scope


CompletionParts = namedtuple('CompletionParts', ['path', 'has_dot', 'name'])


def _start_match(string, like_name):
    return string.startswith(like_name)


def _fuzzy_match(string, like_name):
    if len(like_name) <= 1:
        return like_name in string
    pos = string.find(like_name[0])
    if pos >= 0:
        return _fuzzy_match(string[pos + 1:], like_name[1:])
    return False


def match(string, like_name, fuzzy=False):
    if fuzzy:
        return _fuzzy_match(string, like_name)
    else:
        return _start_match(string, like_name)


def sorted_definitions(defs):
    # Note: `or ''` below is required because `module_path` could be
    return sorted(defs, key=lambda x: (str(x.module_path or ''),
                                       x.line or 0,
                                       x.column or 0,
                                       x.name))


def get_on_completion_name(module_node, lines, position):
    leaf = module_node.get_leaf_for_position(position)
    if leaf is None or leaf.type in ('string', 'error_leaf'):
        # Completions inside strings are a bit special, we need to parse the
        # string. The same is true for comments and error_leafs.
        line = lines[position[0] - 1]
        # The first step of completions is to get the name
        return re.search(r'(?!\d)\w+$|$', line[:position[1]]).group(0)
    elif leaf.type not in ('name', 'keyword'):
        return ''

    return leaf.value[:position[1] - leaf.start_pos[1]]


def _get_code(code_lines, start_pos, end_pos):
    # Get relevant lines.
    lines = code_lines[start_pos[0] - 1:end_pos[0]]
    # Remove the parts at the end of the line.
    lines[-1] = lines[-1][:end_pos[1]]
    # Remove first line indentation.
    lines[0] = lines[0][start_pos[1]:]
    return ''.join(lines)


class OnErrorLeaf(Exception):
    @property
    def error_leaf(self):
        return self.args[0]


def _get_code_for_stack(code_lines, leaf, position):
    # It might happen that we're on whitespace or on a comment. This means
    # that we would not get the right leaf.
    if leaf.start_pos >= position:
        # If we're not on a comment simply get the previous leaf and proceed.
        leaf = leaf.get_previous_leaf()
        if leaf is None:
            return ''  # At the beginning of the file.

    is_after_newline = leaf.type == 'newline'
    while leaf.type == 'newline':
        leaf = leaf.get_previous_leaf()
        if leaf is None:
            return ''

    if leaf.type == 'error_leaf' or leaf.type == 'string':
        if leaf.start_pos[0] < position[0]:
            # On a different line, we just begin anew.
            return ''

        # Error leafs cannot be parsed, completion in strings is also
        # impossible.
        raise OnErrorLeaf(leaf)
    else:
        user_stmt = leaf
        while True:
            if user_stmt.parent.type in ('file_input', 'suite', 'simple_stmt'):
                break
            user_stmt = user_stmt.parent

        if is_after_newline:
            if user_stmt.start_pos[1] > position[1]:
                # This means that it's actually a dedent and that means that we
                # start without value (part of a suite).
                return ''

        # This is basically getting the relevant lines.
        return _get_code(code_lines, user_stmt.get_start_pos_of_prefix(), position)


def get_stack_at_position(grammar, code_lines, leaf, pos):
    """
    Returns the possible node names (e.g. import_from, xor_test or yield_stmt).
    """
    class EndMarkerReached(Exception):
        pass

    def tokenize_without_endmarker(code):
        # TODO This is for now not an official parso API that exists purely
        #   for Jedi.
        tokens = grammar._tokenize(code)
        for token in tokens:
            if token.string == safeword:
                raise EndMarkerReached()
            elif token.prefix.endswith(safeword):
                # This happens with comments.
                raise EndMarkerReached()
            elif token.string.endswith(safeword):
                yield token  # Probably an f-string literal that was not finished.
                raise EndMarkerReached()
            else:
                yield token

    # The code might be indedented, just remove it.
    code = dedent(_get_code_for_stack(code_lines, leaf, pos))
    # We use a word to tell Jedi when we have reached the start of the
    # completion.
    # Use Z as a prefix because it's not part of a number suffix.
    safeword = 'ZZZ_USER_WANTS_TO_COMPLETE_HERE_WITH_JEDI'
    code = code + ' ' + safeword

    p = Parser(grammar._pgen_grammar, error_recovery=True)
    try:
        p.parse(tokens=tokenize_without_endmarker(code))
    except EndMarkerReached:
        return p.stack
    raise SystemError(
        "This really shouldn't happen. There's a bug in Jedi:\n%s"
        % list(tokenize_without_endmarker(code))
    )


def infer(inference_state, context, leaf):
    if leaf.type == 'name':
        return inference_state.infer(context, leaf)

    parent = leaf.parent
    definitions = NO_VALUES
    if parent.type == 'atom':
        # e.g. `(a + b)`
        definitions = context.infer_node(leaf.parent)
    elif parent.type == 'trailer':
        # e.g. `a()`
        definitions = infer_call_of_leaf(context, leaf)
    elif isinstance(leaf, tree.Literal):
        # e.g. `"foo"` or `1.0`
        return infer_atom(context, leaf)
    elif leaf.type in ('fstring_string', 'fstring_start', 'fstring_end'):
        return get_string_value_set(inference_state)
    return definitions


def filter_follow_imports(names, follow_builtin_imports=False):
    for name in names:
        if name.is_import():
            new_names = list(filter_follow_imports(
                name.goto(),
                follow_builtin_imports=follow_builtin_imports,
            ))
            found_builtin = False
            if follow_builtin_imports:
                for new_name in new_names:
                    if new_name.start_pos is None:
                        found_builtin = True

            if found_builtin:
                yield name
            else:
                yield from new_names
        else:
            yield name


class CallDetails:
    def __init__(self, bracket_leaf, children, position):
        self.bracket_leaf = bracket_leaf
        self._children = children
        self._position = position

    @property
    def index(self):
        return _get_index_and_key(self._children, self._position)[0]

    @property
    def keyword_name_str(self):
        return _get_index_and_key(self._children, self._position)[1]

    @memoize_method
    def _list_arguments(self):
        return list(_iter_arguments(self._children, self._position))

    def calculate_index(self, param_names):
        positional_count = 0
        used_names = set()
        star_count = -1
        args = self._list_arguments()
        if not args:
            if param_names:
                return 0
            else:
                return None

        is_kwarg = False
        for i, (star_count, key_start, had_equal) in enumerate(args):
            is_kwarg |= had_equal | (star_count == 2)
            if star_count:
                pass  # For now do nothing, we don't know what's in there here.
            else:
                if i + 1 != len(args):  # Not last
                    if had_equal:
                        used_names.add(key_start)
                    else:
                        positional_count += 1

        for i, param_name in enumerate(param_names):
            kind = param_name.get_kind()

            if not is_kwarg:
                if kind == Parameter.VAR_POSITIONAL:
                    return i
                if kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                    if i == positional_count:
                        return i

            if key_start is not None and not star_count == 1 or star_count == 2:
                if param_name.string_name not in used_names \
                        and (kind == Parameter.KEYWORD_ONLY
                             or kind == Parameter.POSITIONAL_OR_KEYWORD
                             and positional_count <= i):
                    if star_count:
                        return i
                    if had_equal:
                        if param_name.string_name == key_start:
                            return i
                    else:
                        if param_name.string_name.startswith(key_start):
                            return i

                if kind == Parameter.VAR_KEYWORD:
                    return i
        return None

    def iter_used_keyword_arguments(self):
        for star_count, key_start, had_equal in list(self._list_arguments()):
            if had_equal and key_start:
                yield key_start

    def count_positional_arguments(self):
        count = 0
        for star_count, key_start, had_equal in self._list_arguments()[:-1]:
            if star_count or key_start:
                break
            count += 1
        return count


def _iter_arguments(nodes, position):
    def remove_after_pos(name):
        if name.type != 'name':
            return None
        return name.value[:position[1] - name.start_pos[1]]

    # Returns Generator[Tuple[star_count, Optional[key_start: str], had_equal]]
    nodes_before = [c for c in nodes if c.start_pos < position]
    if nodes_before[-1].type == 'arglist':
        yield from _iter_arguments(nodes_before[-1].children, position)
        return

    previous_node_yielded = False
    stars_seen = 0
    for i, node in enumerate(nodes_before):
        if node.type == 'argument':
            previous_node_yielded = True
            first = node.children[0]
            second = node.children[1]
            if second == '=':
                if second.start_pos < position and first.type == 'name':
                    yield 0, first.value, True
                else:
                    yield 0, remove_after_pos(first), False
            elif first in ('*', '**'):
                yield len(first.value), remove_after_pos(second), False
            else:
                # Must be a Comprehension
                first_leaf = node.get_first_leaf()
                if first_leaf.type == 'name' and first_leaf.start_pos >= position:
                    yield 0, remove_after_pos(first_leaf), False
                else:
                    yield 0, None, False
            stars_seen = 0
        elif node.type == 'testlist_star_expr':
            for n in node.children[::2]:
                if n.type == 'star_expr':
                    stars_seen = 1
                    n = n.children[1]
                yield stars_seen, remove_after_pos(n), False
                stars_seen = 0
            # The count of children is even if there's a comma at the end.
            previous_node_yielded = bool(len(node.children) % 2)
        elif isinstance(node, tree.PythonLeaf) and node.value == ',':
            if not previous_node_yielded:
                yield stars_seen, '', False
                stars_seen = 0
            previous_node_yielded = False
        elif isinstance(node, tree.PythonLeaf) and node.value in ('*', '**'):
            stars_seen = len(node.value)
        elif node == '=' and nodes_before[-1]:
            previous_node_yielded = True
            before = nodes_before[i - 1]
            if before.type == 'name':
                yield 0, before.value, True
            else:
                yield 0, None, False
            # Just ignore the star that is probably a syntax error.
            stars_seen = 0

    if not previous_node_yielded:
        if nodes_before[-1].type == 'name':
            yield stars_seen, remove_after_pos(nodes_before[-1]), False
        else:
            yield stars_seen, '', False


def _get_index_and_key(nodes, position):
    """
    Returns the amount of commas and the keyword argument string.
    """
    nodes_before = [c for c in nodes if c.start_pos < position]
    if nodes_before[-1].type == 'arglist':
        return _get_index_and_key(nodes_before[-1].children, position)

    key_str = None

    last = nodes_before[-1]
    if last.type == 'argument' and last.children[1] == '=' \
            and last.children[1].end_pos <= position:
        # Checked if the argument
        key_str = last.children[0].value
    elif last == '=':
        key_str = nodes_before[-2].value

    return nodes_before.count(','), key_str


def _get_signature_details_from_error_node(node, additional_children, position):
    for index, element in reversed(list(enumerate(node.children))):
        # `index > 0` means that it's a trailer and not an atom.
        if element == '(' and element.end_pos <= position and index > 0:
            # It's an error node, we don't want to match too much, just
            # until the parentheses is enough.
            children = node.children[index:]
            name = element.get_previous_leaf()
            if name is None:
                continue
            if name.type == 'name' or name.parent.type in ('trailer', 'atom'):
                return CallDetails(element, children + additional_children, position)


def get_signature_details(module, position):
    leaf = module.get_leaf_for_position(position, include_prefixes=True)
    # It's easier to deal with the previous token than the next one in this
    # case.
    if leaf.start_pos >= position:
        # Whitespace / comments after the leaf count towards the previous leaf.
        leaf = leaf.get_previous_leaf()
        if leaf is None:
            return None

    # Now that we know where we are in the syntax tree, we start to look at
    # parents for possible function definitions.
    node = leaf.parent
    while node is not None:
        if node.type in ('funcdef', 'classdef', 'decorated', 'async_stmt'):
            # Don't show signatures if there's stuff before it that just
            # makes it feel strange to have a signature.
            return None

        additional_children = []
        for n in reversed(node.children):
            if n.start_pos < position:
                if n.type == 'error_node':
                    result = _get_signature_details_from_error_node(
                        n, additional_children, position
                    )
                    if result is not None:
                        return result

                    additional_children[0:0] = n.children
                    continue
                additional_children.insert(0, n)

        # Find a valid trailer
        if node.type == 'trailer' and node.children[0] == '(' \
                or node.type == 'decorator' and node.children[2] == '(':
            # Additionally we have to check that an ending parenthesis isn't
            # interpreted wrong. There are two cases:
            # 1. Cursor before paren -> The current signature is good
            # 2. Cursor after paren -> We need to skip the current signature
            if not (leaf is node.children[-1] and position >= leaf.end_pos):
                leaf = node.get_previous_leaf()
                if leaf is None:
                    return None
                return CallDetails(
                    node.children[0] if node.type == 'trailer' else node.children[2],
                    node.children,
                    position
                )

        node = node.parent

    return None


@signature_time_cache("call_signatures_validity")
def cache_signatures(inference_state, context, bracket_leaf, code_lines, user_pos):
    """This function calculates the cache key."""
    line_index = user_pos[0] - 1

    before_cursor = code_lines[line_index][:user_pos[1]]
    other_lines = code_lines[bracket_leaf.start_pos[0]:line_index]
    whole = ''.join(other_lines + [before_cursor])
    before_bracket = re.match(r'.*\(', whole, re.DOTALL)

    module_path = context.get_root_context().py__file__()
    if module_path is None:
        yield None  # Don't cache!
    else:
        yield (module_path, before_bracket, bracket_leaf.start_pos)
    yield infer(
        inference_state,
        context,
        bracket_leaf.get_previous_leaf(),
    )


def validate_line_column(func):
    @wraps(func)
    def wrapper(self, line=None, column=None, *args, **kwargs):
        line = max(len(self._code_lines), 1) if line is None else line
        if not (0 < line <= len(self._code_lines)):
            raise ValueError('`line` parameter is not in a valid range.')

        line_string = self._code_lines[line - 1]
        line_len = len(line_string)
        if line_string.endswith('\r\n'):
            line_len -= 2
        elif line_string.endswith('\n'):
            line_len -= 1

        column = line_len if column is None else column
        if not (0 <= column <= line_len):
            raise ValueError('`column` parameter (%d) is not in a valid range '
                             '(0-%d) for line %d (%r).' % (
                                 column, line_len, line, line_string))
        return func(self, line, column, *args, **kwargs)
    return wrapper


def get_module_names(module, all_scopes, definitions=True, references=False):
    """
    Returns a dictionary with name parts as keys and their call paths as
    values.
    """
    def def_ref_filter(name):
        is_def = name.is_definition()
        return definitions and is_def or references and not is_def

    names = list(chain.from_iterable(module.get_used_names().values()))
    if not all_scopes:
        # We have to filter all the names that don't have the module as a
        # parent_scope. There's None as a parent, because nodes in the module
        # node have the parent module and not suite as all the others.
        # Therefore it's important to catch that case.

        def is_module_scope_name(name):
            parent_scope = get_parent_scope(name)
            # async functions have an extra wrapper. Strip it.
            if parent_scope and parent_scope.type == 'async_stmt':
                parent_scope = parent_scope.parent
            return parent_scope in (module, None)

        names = [n for n in names if is_module_scope_name(n)]
    return filter(def_ref_filter, names)


def split_search_string(name):
    type, _, dotted_names = name.rpartition(' ')
    if type == 'def':
        type = 'function'
    return type, dotted_names.split('.')

# === NexusCore/openenv\Lib\site-packages\trio\_core\_tests\test_io.py ===
from __future__ import annotations

import random
import select
import socket as stdlib_socket
import sys
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TYPE_CHECKING, TypeVar

import pytest

import trio

from ... import _core
from ...testing import assert_checkpoints, wait_all_tasks_blocked

# Cross-platform tests for IO handling

if TYPE_CHECKING:
    from collections.abc import Generator

    from typing_extensions import ParamSpec

    ArgsT = ParamSpec("ArgsT")


def fill_socket(sock: stdlib_socket.socket) -> None:
    try:
        while True:
            sock.send(b"x" * 65536)
    except BlockingIOError:
        pass


def drain_socket(sock: stdlib_socket.socket) -> None:
    try:
        while True:
            sock.recv(65536)
    except BlockingIOError:
        pass


WaitSocket = Callable[[stdlib_socket.socket], Awaitable[object]]
SocketPair = tuple[stdlib_socket.socket, stdlib_socket.socket]
RetT = TypeVar("RetT")


@pytest.fixture
def socketpair() -> Generator[SocketPair, None, None]:
    pair = stdlib_socket.socketpair()
    for sock in pair:
        sock.setblocking(False)
    yield pair
    for sock in pair:
        sock.close()


def also_using_fileno(
    fn: Callable[[stdlib_socket.socket | int], RetT],
) -> list[Callable[[stdlib_socket.socket], RetT]]:
    def fileno_wrapper(fileobj: stdlib_socket.socket) -> RetT:
        return fn(fileobj.fileno())

    name = f"<{fn.__name__} on fileno>"
    fileno_wrapper.__name__ = fileno_wrapper.__qualname__ = name
    return [fn, fileno_wrapper]


# Decorators that feed in different settings for wait_readable / wait_writable
# / notify_closing.
# Note that if you use all three decorators on the same test, it will run all
# N**3 *combinations*
read_socket_test = pytest.mark.parametrize(
    "wait_readable",
    also_using_fileno(trio.lowlevel.wait_readable),
    ids=lambda fn: fn.__name__,
)
write_socket_test = pytest.mark.parametrize(
    "wait_writable",
    also_using_fileno(trio.lowlevel.wait_writable),
    ids=lambda fn: fn.__name__,
)
notify_closing_test = pytest.mark.parametrize(
    "notify_closing",
    also_using_fileno(trio.lowlevel.notify_closing),
    ids=lambda fn: fn.__name__,
)


# XX These tests are all a bit dicey because they can't distinguish between
# wait_on_{read,writ}able blocking the way it should, versus blocking
# momentarily and then immediately resuming.
@read_socket_test
@write_socket_test
async def test_wait_basic(
    socketpair: SocketPair,
    wait_readable: WaitSocket,
    wait_writable: WaitSocket,
) -> None:
    a, b = socketpair

    # They start out writable()
    with assert_checkpoints():
        await wait_writable(a)

    # But readable() blocks until data arrives
    record = []

    async def block_on_read() -> None:
        try:
            with assert_checkpoints():
                await wait_readable(a)
        except _core.Cancelled:
            record.append("cancelled")
        else:
            record.append("readable")
            assert a.recv(10) == b"x"

    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_read)
        await wait_all_tasks_blocked()
        assert record == []
        b.send(b"x")

    fill_socket(a)

    # Now writable will block, but readable won't
    with assert_checkpoints():
        await wait_readable(b)
    record = []

    async def block_on_write() -> None:
        try:
            with assert_checkpoints():
                await wait_writable(a)
        except _core.Cancelled:
            record.append("cancelled")
        else:
            record.append("writable")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_write)
        await wait_all_tasks_blocked()
        assert record == []
        drain_socket(b)

    # check cancellation
    record = []
    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_read)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    assert record == ["cancelled"]

    fill_socket(a)
    record = []
    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_write)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    assert record == ["cancelled"]


@read_socket_test
async def test_double_read(socketpair: SocketPair, wait_readable: WaitSocket) -> None:
    a, _b = socketpair

    # You can't have two tasks trying to read from a socket at the same time
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_readable, a)
        await wait_all_tasks_blocked()
        with pytest.raises(_core.BusyResourceError):
            await wait_readable(a)
        nursery.cancel_scope.cancel()


@write_socket_test
async def test_double_write(socketpair: SocketPair, wait_writable: WaitSocket) -> None:
    a, _b = socketpair

    # You can't have two tasks trying to write to a socket at the same time
    fill_socket(a)
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_writable, a)
        await wait_all_tasks_blocked()
        with pytest.raises(_core.BusyResourceError):
            await wait_writable(a)
        nursery.cancel_scope.cancel()


@read_socket_test
@write_socket_test
@notify_closing_test
async def test_interrupted_by_close(
    socketpair: SocketPair,
    wait_readable: WaitSocket,
    wait_writable: WaitSocket,
    notify_closing: Callable[[stdlib_socket.socket], object],
) -> None:
    a, _b = socketpair

    async def reader() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await wait_readable(a)

    async def writer() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await wait_writable(a)

    fill_socket(a)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(reader)
        nursery.start_soon(writer)
        await wait_all_tasks_blocked()
        notify_closing(a)


@read_socket_test
@write_socket_test
async def test_socket_simultaneous_read_write(
    socketpair: SocketPair,
    wait_readable: WaitSocket,
    wait_writable: WaitSocket,
) -> None:
    record: list[str] = []

    async def r_task(sock: stdlib_socket.socket) -> None:
        await wait_readable(sock)
        record.append("r_task")

    async def w_task(sock: stdlib_socket.socket) -> None:
        await wait_writable(sock)
        record.append("w_task")

    a, b = socketpair
    fill_socket(a)
    async with _core.open_nursery() as nursery:
        nursery.start_soon(r_task, a)
        nursery.start_soon(w_task, a)
        await wait_all_tasks_blocked()
        assert record == []
        b.send(b"x")
        await wait_all_tasks_blocked()
        assert record == ["r_task"]
        drain_socket(b)
        await wait_all_tasks_blocked()
        assert record == ["r_task", "w_task"]


@read_socket_test
@write_socket_test
async def test_socket_actual_streaming(
    socketpair: SocketPair,
    wait_readable: WaitSocket,
    wait_writable: WaitSocket,
) -> None:
    a, b = socketpair

    # Use a small send buffer on one of the sockets to increase the chance of
    # getting partial writes
    a.setsockopt(stdlib_socket.SOL_SOCKET, stdlib_socket.SO_SNDBUF, 10000)

    N = 1000000  # 1 megabyte
    MAX_CHUNK = 65536

    results: dict[str, int] = {}

    async def sender(sock: stdlib_socket.socket, seed: int, key: str) -> None:
        r = random.Random(seed)
        sent = 0
        while sent < N:
            print("sent", sent)
            chunk = bytearray(r.randrange(MAX_CHUNK))
            while chunk:
                with assert_checkpoints():
                    await wait_writable(sock)
                this_chunk_size = sock.send(chunk)
                sent += this_chunk_size
                del chunk[:this_chunk_size]
        sock.shutdown(stdlib_socket.SHUT_WR)
        results[key] = sent

    async def receiver(sock: stdlib_socket.socket, key: str) -> None:
        received = 0
        while True:
            print("received", received)
            with assert_checkpoints():
                await wait_readable(sock)
            this_chunk_size = len(sock.recv(MAX_CHUNK))
            if not this_chunk_size:
                break
            received += this_chunk_size
        results[key] = received

    async with _core.open_nursery() as nursery:
        nursery.start_soon(sender, a, 0, "send_a")
        nursery.start_soon(sender, b, 1, "send_b")
        nursery.start_soon(receiver, a, "recv_a")
        nursery.start_soon(receiver, b, "recv_b")

    assert results["send_a"] == results["recv_b"]
    assert results["send_b"] == results["recv_a"]


async def test_notify_closing_on_invalid_object() -> None:
    # It should either be a no-op (generally on Unix, where we don't know
    # which fds are valid), or an OSError (on Windows, where we currently only
    # support sockets, so we have to do some validation to figure out whether
    # it's a socket or a regular handle).
    got_oserror = False
    got_no_error = False
    try:
        trio.lowlevel.notify_closing(-1)
    except OSError:
        got_oserror = True
    else:
        got_no_error = True
    assert got_oserror or got_no_error


async def test_wait_on_invalid_object() -> None:
    # We definitely want to raise an error everywhere if you pass in an
    # invalid fd to wait_*
    for wait in [trio.lowlevel.wait_readable, trio.lowlevel.wait_writable]:
        with stdlib_socket.socket() as s:
            fileno = s.fileno()
        # We just closed the socket and don't do anything else in between, so
        # we can be confident that the fileno hasn't be reassigned.
        with pytest.raises(
            OSError,
            match=r"^\[\w+ \d+] (Bad file descriptor|An operation was attempted on something that is not a socket)$",
        ):
            await wait(fileno)


async def test_io_manager_statistics() -> None:
    def check(*, expected_readers: int, expected_writers: int) -> None:
        statistics = _core.current_statistics()
        print(statistics)
        iostats = statistics.io_statistics
        if iostats.backend == "epoll" or iostats.backend == "windows":
            assert iostats.tasks_waiting_read == expected_readers
            assert iostats.tasks_waiting_write == expected_writers
        else:
            assert iostats.backend == "kqueue"
            assert iostats.monitors == 0
            assert iostats.tasks_waiting == expected_readers + expected_writers

    a1, b1 = stdlib_socket.socketpair()
    a2, b2 = stdlib_socket.socketpair()
    a3, b3 = stdlib_socket.socketpair()
    for sock in [a1, b1, a2, b2, a3, b3]:
        sock.setblocking(False)
    with a1, b1, a2, b2, a3, b3:
        # let the call_soon_task settle down
        await wait_all_tasks_blocked()

        # 1 for call_soon_task
        check(expected_readers=1, expected_writers=0)

        # We want:
        # - one socket with a writer blocked
        # - two sockets with a reader blocked
        # - a socket with both blocked
        fill_socket(a1)
        fill_socket(a3)
        async with _core.open_nursery() as nursery:
            nursery.start_soon(_core.wait_writable, a1)
            nursery.start_soon(_core.wait_readable, a2)
            nursery.start_soon(_core.wait_readable, b2)
            nursery.start_soon(_core.wait_writable, a3)
            nursery.start_soon(_core.wait_readable, a3)

            await wait_all_tasks_blocked()

            # +1 for call_soon_task
            check(expected_readers=3 + 1, expected_writers=2)

            nursery.cancel_scope.cancel()

        # 1 for call_soon_task
        check(expected_readers=1, expected_writers=0)


@pytest.mark.filterwarnings("ignore:.*UnboundedQueue:trio.TrioDeprecationWarning")
async def test_io_manager_kqueue_monitors_statistics() -> None:
    def check(
        *,
        expected_monitors: int,
        expected_readers: int,
        expected_writers: int,
    ) -> None:
        statistics = _core.current_statistics()
        print(statistics)
        iostats = statistics.io_statistics
        assert iostats.backend == "kqueue"
        assert iostats.monitors == expected_monitors
        assert iostats.tasks_waiting == expected_readers + expected_writers

    a1, b1 = stdlib_socket.socketpair()
    for sock in [a1, b1]:
        sock.setblocking(False)

    with a1, b1:
        # let the call_soon_task settle down
        await wait_all_tasks_blocked()

        if sys.platform != "win32" and sys.platform != "linux":
            # 1 for call_soon_task
            check(expected_monitors=0, expected_readers=1, expected_writers=0)

            with _core.monitor_kevent(a1.fileno(), select.KQ_FILTER_READ):
                with (
                    pytest.raises(_core.BusyResourceError),
                    _core.monitor_kevent(a1.fileno(), select.KQ_FILTER_READ),
                ):
                    pass  # pragma: no cover
                check(expected_monitors=1, expected_readers=1, expected_writers=0)

            check(expected_monitors=0, expected_readers=1, expected_writers=0)


async def test_can_survive_unnotified_close() -> None:
    # An "unnotified" close is when the user closes an fd/socket/handle
    # directly, without calling notify_closing first. This should never happen
    # -- users should call notify_closing before closing things. But, just in
    # case they don't, we would still like to avoid exploding.
    #
    # Acceptable behaviors:
    # - wait_* never return, but can be cancelled cleanly
    # - wait_* exit cleanly
    # - wait_* raise an OSError
    #
    # Not acceptable:
    # - getting stuck in an uncancellable state
    # - TrioInternalError blowing up the whole run
    #
    # This test exercises some tricky "unnotified close" scenarios, to make
    # sure we get the "acceptable" behaviors.

    async def allow_OSError(
        async_func: Callable[ArgsT, Awaitable[object]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
    ) -> None:
        with suppress(OSError):
            await async_func(*args, **kwargs)

    with stdlib_socket.socket() as s:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, s)
            await wait_all_tasks_blocked()
            s.close()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    # We hit different paths on Windows depending on whether we close the last
    # handle to the object (which produces a LOCAL_CLOSE notification and
    # wakes up wait_readable), or only close one of the handles (which leaves
    # wait_readable pending until cancelled).
    with stdlib_socket.socket() as s, s.dup() as s2:  # noqa: F841
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, s)
            await wait_all_tasks_blocked()
            s.close()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    # A more elaborate case, with two tasks waiting. On windows and epoll,
    # the two tasks get muxed together onto a single underlying wait
    # operation. So when they're cancelled, there's a brief moment where one
    # of the tasks is cancelled but the other isn't, so we try to re-issue the
    # underlying wait operation. But here, the handle we were going to use to
    # do that has been pulled out from under our feet... so test that we can
    # survive this.
    a, b = stdlib_socket.socketpair()
    with a, b, a.dup() as a2:
        a.setblocking(False)
        b.setblocking(False)
        fill_socket(a)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, a)
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_writable, a)
            await wait_all_tasks_blocked()
            a.close()
            nursery.cancel_scope.cancel()

    # A similar case, but now the single-task-wakeup happens due to I/O
    # arriving, not a cancellation, so the operation gets re-issued from
    # handle_io context rather than abort context.
    a, b = stdlib_socket.socketpair()
    with a, b, a.dup() as a2:
        print(f"a={a.fileno()}, b={b.fileno()}, a2={a2.fileno()}")
        a.setblocking(False)
        b.setblocking(False)
        fill_socket(a)
        e = trio.Event()

        # We want to wait for the kernel to process the wakeup on 'a', if any.
        # But depending on the platform, we might not get a wakeup on 'a'. So
        # we put one task to sleep waiting on 'a', and we put a second task to
        # sleep waiting on 'a2', with the idea that the 'a2' notification will
        # definitely arrive, and when it does then we can assume that whatever
        # notification was going to arrive for 'a' has also arrived.
        async def wait_readable_a2_then_set() -> None:
            await trio.lowlevel.wait_readable(a2)
            e.set()

        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, a)
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_writable, a)
            nursery.start_soon(wait_readable_a2_then_set)
            await wait_all_tasks_blocked()
            a.close()
            b.send(b"x")
            # Make sure that the wakeup has been received and everything has
            # settled before cancelling the wait_writable.
            await e.wait()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

# === NexusCore/openenv\Lib\site-packages\jsonschema\_format.py ===
from __future__ import annotations

from contextlib import suppress
from datetime import date, datetime
from uuid import UUID
import ipaddress
import re
import typing
import warnings

from jsonschema.exceptions import FormatError

_FormatCheckCallable = typing.Callable[[object], bool]
#: A format checker callable.
_F = typing.TypeVar("_F", bound=_FormatCheckCallable)
_RaisesType = typing.Union[type[Exception], tuple[type[Exception], ...]]

_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$", re.ASCII)


class FormatChecker:
    """
    A ``format`` property checker.

    JSON Schema does not mandate that the ``format`` property actually do any
    validation. If validation is desired however, instances of this class can
    be hooked into validators to enable format validation.

    `FormatChecker` objects always return ``True`` when asked about
    formats that they do not know how to validate.

    To add a check for a custom format use the `FormatChecker.checks`
    decorator.

    Arguments:

        formats:

            The known formats to validate. This argument can be used to
            limit which formats will be used during validation.

    """

    checkers: dict[
        str,
        tuple[_FormatCheckCallable, _RaisesType],
    ] = {}  # noqa: RUF012

    def __init__(self, formats: typing.Iterable[str] | None = None):
        if formats is None:
            formats = self.checkers.keys()
        self.checkers = {k: self.checkers[k] for k in formats}

    def __repr__(self):
        return f"<FormatChecker checkers={sorted(self.checkers)}>"

    def checks(
        self, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        """
        Register a decorated function as validating a new format.

        Arguments:

            format:

                The format that the decorated function will check.

            raises:

                The exception(s) raised by the decorated function when an
                invalid instance is found.

                The exception object will be accessible as the
                `jsonschema.exceptions.ValidationError.cause` attribute of the
                resulting validation error.

        """

        def _checks(func: _F) -> _F:
            self.checkers[format] = (func, raises)
            return func

        return _checks

    @classmethod
    def cls_checks(
        cls, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        warnings.warn(
            (
                "FormatChecker.cls_checks is deprecated. Call "
                "FormatChecker.checks on a specific FormatChecker instance "
                "instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        return cls._cls_checks(format=format, raises=raises)

    @classmethod
    def _cls_checks(
        cls, format: str, raises: _RaisesType = (),
    ) -> typing.Callable[[_F], _F]:
        def _checks(func: _F) -> _F:
            cls.checkers[format] = (func, raises)
            return func

        return _checks

    def check(self, instance: object, format: str) -> None:
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format:

                The format that instance should conform to

        Raises:

            FormatError:

                if the instance does not conform to ``format``

        """
        if format not in self.checkers:
            return

        func, raises = self.checkers[format]
        result, cause = None, None
        try:
            result = func(instance)
        except raises as e:
            cause = e
        if not result:
            raise FormatError(f"{instance!r} is not a {format!r}", cause=cause)

    def conforms(self, instance: object, format: str) -> bool:
        """
        Check whether the instance conforms to the given format.

        Arguments:

            instance (*any primitive type*, i.e. str, number, bool):

                The instance to check

            format:

                The format that instance should conform to

        Returns:

            bool: whether it conformed

        """
        try:
            self.check(instance, format)
        except FormatError:
            return False
        else:
            return True


draft3_format_checker = FormatChecker()
draft4_format_checker = FormatChecker()
draft6_format_checker = FormatChecker()
draft7_format_checker = FormatChecker()
draft201909_format_checker = FormatChecker()
draft202012_format_checker = FormatChecker()

_draft_checkers: dict[str, FormatChecker] = dict(
    draft3=draft3_format_checker,
    draft4=draft4_format_checker,
    draft6=draft6_format_checker,
    draft7=draft7_format_checker,
    draft201909=draft201909_format_checker,
    draft202012=draft202012_format_checker,
)


def _checks_drafts(
    name=None,
    draft3=None,
    draft4=None,
    draft6=None,
    draft7=None,
    draft201909=None,
    draft202012=None,
    raises=(),
) -> typing.Callable[[_F], _F]:
    draft3 = draft3 or name
    draft4 = draft4 or name
    draft6 = draft6 or name
    draft7 = draft7 or name
    draft201909 = draft201909 or name
    draft202012 = draft202012 or name

    def wrap(func: _F) -> _F:
        if draft3:
            func = _draft_checkers["draft3"].checks(draft3, raises)(func)
        if draft4:
            func = _draft_checkers["draft4"].checks(draft4, raises)(func)
        if draft6:
            func = _draft_checkers["draft6"].checks(draft6, raises)(func)
        if draft7:
            func = _draft_checkers["draft7"].checks(draft7, raises)(func)
        if draft201909:
            func = _draft_checkers["draft201909"].checks(draft201909, raises)(
                func,
            )
        if draft202012:
            func = _draft_checkers["draft202012"].checks(draft202012, raises)(
                func,
            )

        # Oy. This is bad global state, but relied upon for now, until
        # deprecation. See #519 and test_format_checkers_come_with_defaults
        FormatChecker._cls_checks(
            draft202012 or draft201909 or draft7 or draft6 or draft4 or draft3,
            raises,
        )(func)
        return func

    return wrap


@_checks_drafts(name="idn-email")
@_checks_drafts(name="email")
def is_email(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return "@" in instance


@_checks_drafts(
    draft3="ip-address",
    draft4="ipv4",
    draft6="ipv4",
    draft7="ipv4",
    draft201909="ipv4",
    draft202012="ipv4",
    raises=ipaddress.AddressValueError,
)
def is_ipv4(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(ipaddress.IPv4Address(instance))


@_checks_drafts(name="ipv6", raises=ipaddress.AddressValueError)
def is_ipv6(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    address = ipaddress.IPv6Address(instance)
    return not getattr(address, "scope_id", "")


with suppress(ImportError):
    from fqdn import FQDN

    @_checks_drafts(
        draft3="host-name",
        draft4="hostname",
        draft6="hostname",
        draft7="hostname",
        draft201909="hostname",
        draft202012="hostname",
        # fqdn.FQDN("") raises a ValueError due to a bug
        # however, it's not clear when or if that will be fixed, so catch it
        # here for now
        raises=ValueError,
    )
    def is_host_name(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return FQDN(instance, min_labels=1).is_valid


with suppress(ImportError):
    # The built-in `idna` codec only implements RFC 3890, so we go elsewhere.
    import idna

    @_checks_drafts(
        draft7="idn-hostname",
        draft201909="idn-hostname",
        draft202012="idn-hostname",
        raises=(idna.IDNAError, UnicodeError),
    )
    def is_idn_host_name(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        idna.encode(instance)
        return True


try:
    import rfc3987
except ImportError:
    with suppress(ImportError):
        from rfc3986_validator import validate_rfc3986

        @_checks_drafts(name="uri")
        def is_uri(instance: object) -> bool:
            if not isinstance(instance, str):
                return True
            return validate_rfc3986(instance, rule="URI")

        @_checks_drafts(
            draft6="uri-reference",
            draft7="uri-reference",
            draft201909="uri-reference",
            draft202012="uri-reference",
            raises=ValueError,
        )
        def is_uri_reference(instance: object) -> bool:
            if not isinstance(instance, str):
                return True
            return validate_rfc3986(instance, rule="URI_reference")

else:

    @_checks_drafts(
        draft7="iri",
        draft201909="iri",
        draft202012="iri",
        raises=ValueError,
    )
    def is_iri(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule="IRI")

    @_checks_drafts(
        draft7="iri-reference",
        draft201909="iri-reference",
        draft202012="iri-reference",
        raises=ValueError,
    )
    def is_iri_reference(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule="IRI_reference")

    @_checks_drafts(name="uri", raises=ValueError)
    def is_uri(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule="URI")

    @_checks_drafts(
        draft6="uri-reference",
        draft7="uri-reference",
        draft201909="uri-reference",
        draft202012="uri-reference",
        raises=ValueError,
    )
    def is_uri_reference(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return rfc3987.parse(instance, rule="URI_reference")


with suppress(ImportError):
    from rfc3339_validator import validate_rfc3339

    @_checks_drafts(name="date-time")
    def is_datetime(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return validate_rfc3339(instance.upper())

    @_checks_drafts(
        draft7="time",
        draft201909="time",
        draft202012="time",
    )
    def is_time(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return is_datetime("1970-01-01T" + instance)


@_checks_drafts(name="regex", raises=re.error)
def is_regex(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(re.compile(instance))


@_checks_drafts(
    draft3="date",
    draft7="date",
    draft201909="date",
    draft202012="date",
    raises=ValueError,
)
def is_date(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(_RE_DATE.fullmatch(instance) and date.fromisoformat(instance))


@_checks_drafts(draft3="time", raises=ValueError)
def is_draft3_time(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    return bool(datetime.strptime(instance, "%H:%M:%S"))  # noqa: DTZ007


with suppress(ImportError):
    import webcolors

    @_checks_drafts(draft3="color", raises=(ValueError, TypeError))
    def is_css21_color(instance: object) -> bool:
        if isinstance(instance, str):
            try:
                webcolors.name_to_hex(instance)
            except ValueError:
                webcolors.normalize_hex(instance.lower())
        return True


with suppress(ImportError):
    import jsonpointer

    @_checks_drafts(
        draft6="json-pointer",
        draft7="json-pointer",
        draft201909="json-pointer",
        draft202012="json-pointer",
        raises=jsonpointer.JsonPointerException,
    )
    def is_json_pointer(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return bool(jsonpointer.JsonPointer(instance))

    # TODO: I don't want to maintain this, so it
    #       needs to go either into jsonpointer (pending
    #       https://github.com/stefankoegl/python-json-pointer/issues/34) or
    #       into a new external library.
    @_checks_drafts(
        draft7="relative-json-pointer",
        draft201909="relative-json-pointer",
        draft202012="relative-json-pointer",
        raises=jsonpointer.JsonPointerException,
    )
    def is_relative_json_pointer(instance: object) -> bool:
        # Definition taken from:
        # https://tools.ietf.org/html/draft-handrews-relative-json-pointer-01#section-3
        if not isinstance(instance, str):
            return True
        if not instance:
            return False

        non_negative_integer, rest = [], ""
        for i, character in enumerate(instance):
            if character.isdigit():
                # digits with a leading "0" are not allowed
                if i > 0 and int(instance[i - 1]) == 0:
                    return False

                non_negative_integer.append(character)
                continue

            if not non_negative_integer:
                return False

            rest = instance[i:]
            break
        return (rest == "#") or bool(jsonpointer.JsonPointer(rest))


with suppress(ImportError):
    import uri_template

    @_checks_drafts(
        draft6="uri-template",
        draft7="uri-template",
        draft201909="uri-template",
        draft202012="uri-template",
    )
    def is_uri_template(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        return uri_template.validate(instance)


with suppress(ImportError):
    import isoduration

    @_checks_drafts(
        draft201909="duration",
        draft202012="duration",
        raises=isoduration.DurationParsingException,
    )
    def is_duration(instance: object) -> bool:
        if not isinstance(instance, str):
            return True
        isoduration.parse_duration(instance)
        # FIXME: See bolsote/isoduration#25 and bolsote/isoduration#21
        return instance.endswith(tuple("DMYWHMS"))


@_checks_drafts(
    draft201909="uuid",
    draft202012="uuid",
    raises=ValueError,
)
def is_uuid(instance: object) -> bool:
    if not isinstance(instance, str):
        return True
    UUID(instance)
    return all(instance[position] == "-" for position in (8, 13, 18, 23))

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\generative_service\transports\grpc_asyncio.py ===
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
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import generative_service

from .base import DEFAULT_CLIENT_INFO, GenerativeServiceTransport
from .grpc import GenerativeServiceGrpcTransport


class GenerativeServiceGrpcAsyncIOTransport(GenerativeServiceTransport):
    """gRPC AsyncIO backend transport for GenerativeService.

    API for using Large Models that generate multimodal content
    and have additional capabilities beyond text generation.

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
    def generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        Awaitable[generative_service.GenerateContentResponse],
    ]:
        r"""Return a callable for the generate content method over gRPC.

        Generates a response from the model given an input
        ``GenerateContentRequest``.

        Input capabilities differ between models, including tuned
        models. See the `model
        guide <https://ai.google.dev/models/gemini>`__ and `tuning
        guide <https://ai.google.dev/docs/model_tuning_guidance>`__ for
        details.

        Returns:
            Callable[[~.GenerateContentRequest],
                    Awaitable[~.GenerateContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_content" not in self._stubs:
            self._stubs["generate_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/GenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["generate_content"]

    @property
    def generate_answer(
        self,
    ) -> Callable[
        [generative_service.GenerateAnswerRequest],
        Awaitable[generative_service.GenerateAnswerResponse],
    ]:
        r"""Return a callable for the generate answer method over gRPC.

        Generates a grounded answer from the model given an input
        ``GenerateAnswerRequest``.

        Returns:
            Callable[[~.GenerateAnswerRequest],
                    Awaitable[~.GenerateAnswerResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_answer" not in self._stubs:
            self._stubs["generate_answer"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/GenerateAnswer",
                request_serializer=generative_service.GenerateAnswerRequest.serialize,
                response_deserializer=generative_service.GenerateAnswerResponse.deserialize,
            )
        return self._stubs["generate_answer"]

    @property
    def stream_generate_content(
        self,
    ) -> Callable[
        [generative_service.GenerateContentRequest],
        Awaitable[generative_service.GenerateContentResponse],
    ]:
        r"""Return a callable for the stream generate content method over gRPC.

        Generates a streamed response from the model given an input
        ``GenerateContentRequest``.

        Returns:
            Callable[[~.GenerateContentRequest],
                    Awaitable[~.GenerateContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "stream_generate_content" not in self._stubs:
            self._stubs["stream_generate_content"] = self.grpc_channel.unary_stream(
                "/google.ai.generativelanguage.v1beta.GenerativeService/StreamGenerateContent",
                request_serializer=generative_service.GenerateContentRequest.serialize,
                response_deserializer=generative_service.GenerateContentResponse.deserialize,
            )
        return self._stubs["stream_generate_content"]

    @property
    def embed_content(
        self,
    ) -> Callable[
        [generative_service.EmbedContentRequest],
        Awaitable[generative_service.EmbedContentResponse],
    ]:
        r"""Return a callable for the embed content method over gRPC.

        Generates an embedding from the model given an input
        ``Content``.

        Returns:
            Callable[[~.EmbedContentRequest],
                    Awaitable[~.EmbedContentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_content" not in self._stubs:
            self._stubs["embed_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/EmbedContent",
                request_serializer=generative_service.EmbedContentRequest.serialize,
                response_deserializer=generative_service.EmbedContentResponse.deserialize,
            )
        return self._stubs["embed_content"]

    @property
    def batch_embed_contents(
        self,
    ) -> Callable[
        [generative_service.BatchEmbedContentsRequest],
        Awaitable[generative_service.BatchEmbedContentsResponse],
    ]:
        r"""Return a callable for the batch embed contents method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedContentsRequest],
                    Awaitable[~.BatchEmbedContentsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_contents" not in self._stubs:
            self._stubs["batch_embed_contents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/BatchEmbedContents",
                request_serializer=generative_service.BatchEmbedContentsRequest.serialize,
                response_deserializer=generative_service.BatchEmbedContentsResponse.deserialize,
            )
        return self._stubs["batch_embed_contents"]

    @property
    def count_tokens(
        self,
    ) -> Callable[
        [generative_service.CountTokensRequest],
        Awaitable[generative_service.CountTokensResponse],
    ]:
        r"""Return a callable for the count tokens method over gRPC.

        Runs a model's tokenizer on input content and returns
        the token count.

        Returns:
            Callable[[~.CountTokensRequest],
                    Awaitable[~.CountTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_tokens" not in self._stubs:
            self._stubs["count_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.GenerativeService/CountTokens",
                request_serializer=generative_service.CountTokensRequest.serialize,
                response_deserializer=generative_service.CountTokensResponse.deserialize,
            )
        return self._stubs["count_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_content: gapic_v1.method_async.wrap_method(
                self.generate_content,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=600.0,
                ),
                default_timeout=600.0,
                client_info=client_info,
            ),
            self.generate_answer: gapic_v1.method_async.wrap_method(
                self.generate_answer,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.stream_generate_content: gapic_v1.method_async.wrap_method(
                self.stream_generate_content,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=600.0,
                ),
                default_timeout=600.0,
                client_info=client_info,
            ),
            self.embed_content: gapic_v1.method_async.wrap_method(
                self.embed_content,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_embed_contents: gapic_v1.method_async.wrap_method(
                self.batch_embed_contents,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.count_tokens: gapic_v1.method_async.wrap_method(
                self.count_tokens,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("GenerativeServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\command\sdist.py ===
"""distutils.command.sdist

Implements the Distutils 'sdist' command (create a source distribution)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from distutils import archive_util, dir_util, file_util
from distutils._log import log
from glob import glob
from itertools import filterfalse
from typing import ClassVar

from ..core import Command
from ..errors import DistutilsOptionError, DistutilsTemplateError
from ..filelist import FileList
from ..text_file import TextFile
from ..util import convert_path


def show_formats():
    """Print all possible values for the 'formats' option (used by
    the "--help-formats" command-line option).
    """
    from ..archive_util import ARCHIVE_FORMATS
    from ..fancy_getopt import FancyGetopt

    formats = sorted(
        ("formats=" + format, None, ARCHIVE_FORMATS[format][2])
        for format in ARCHIVE_FORMATS.keys()
    )
    FancyGetopt(formats).print_help("List of available source distribution formats:")


class sdist(Command):
    description = "create a source distribution (tarball, zip file, etc.)"

    def checking_metadata(self) -> bool:
        """Callable used for the check sub-command.

        Placed here so user_options can view it"""
        return self.metadata_check

    user_options = [
        ('template=', 't', "name of manifest template file [default: MANIFEST.in]"),
        ('manifest=', 'm', "name of manifest file [default: MANIFEST]"),
        (
            'use-defaults',
            None,
            "include the default file set in the manifest "
            "[default; disable with --no-defaults]",
        ),
        ('no-defaults', None, "don't include the default file set"),
        (
            'prune',
            None,
            "specifically exclude files/directories that should not be "
            "distributed (build tree, RCS/CVS dirs, etc.) "
            "[default; disable with --no-prune]",
        ),
        ('no-prune', None, "don't automatically exclude anything"),
        (
            'manifest-only',
            'o',
            "just regenerate the manifest and then stop (implies --force-manifest)",
        ),
        (
            'force-manifest',
            'f',
            "forcibly regenerate the manifest and carry on as usual. "
            "Deprecated: now the manifest is always regenerated.",
        ),
        ('formats=', None, "formats for source distribution (comma-separated list)"),
        (
            'keep-temp',
            'k',
            "keep the distribution tree around after creating " + "archive file(s)",
        ),
        (
            'dist-dir=',
            'd',
            "directory to put the source distribution archive(s) in [default: dist]",
        ),
        (
            'metadata-check',
            None,
            "Ensure that all required elements of meta-data "
            "are supplied. Warn if any missing. [default]",
        ),
        (
            'owner=',
            'u',
            "Owner name used when creating a tar file [default: current user]",
        ),
        (
            'group=',
            'g',
            "Group name used when creating a tar file [default: current group]",
        ),
    ]

    boolean_options: ClassVar[list[str]] = [
        'use-defaults',
        'prune',
        'manifest-only',
        'force-manifest',
        'keep-temp',
        'metadata-check',
    ]

    help_options: ClassVar[list[tuple[str, str | None, str, Callable[[], object]]]] = [
        ('help-formats', None, "list available distribution formats", show_formats),
    ]

    negative_opt: ClassVar[dict[str, str]] = {
        'no-defaults': 'use-defaults',
        'no-prune': 'prune',
    }

    sub_commands = [('check', checking_metadata)]

    READMES: ClassVar[tuple[str, ...]] = ('README', 'README.txt', 'README.rst')

    def initialize_options(self):
        # 'template' and 'manifest' are, respectively, the names of
        # the manifest template and manifest file.
        self.template = None
        self.manifest = None

        # 'use_defaults': if true, we will include the default file set
        # in the manifest
        self.use_defaults = True
        self.prune = True

        self.manifest_only = False
        self.force_manifest = False

        self.formats = ['gztar']
        self.keep_temp = False
        self.dist_dir = None

        self.archive_files = None
        self.metadata_check = True
        self.owner = None
        self.group = None

    def finalize_options(self) -> None:
        if self.manifest is None:
            self.manifest = "MANIFEST"
        if self.template is None:
            self.template = "MANIFEST.in"

        self.ensure_string_list('formats')

        bad_format = archive_util.check_archive_formats(self.formats)
        if bad_format:
            raise DistutilsOptionError(f"unknown archive format '{bad_format}'")

        if self.dist_dir is None:
            self.dist_dir = "dist"

    def run(self) -> None:
        # 'filelist' contains the list of files that will make up the
        # manifest
        self.filelist = FileList()

        # Run sub commands
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

        # Do whatever it takes to get the list of files to process
        # (process the manifest template, read an existing manifest,
        # whatever).  File list is accumulated in 'self.filelist'.
        self.get_file_list()

        # If user just wanted us to regenerate the manifest, stop now.
        if self.manifest_only:
            return

        # Otherwise, go ahead and create the source distribution tarball,
        # or zipfile, or whatever.
        self.make_distribution()

    def get_file_list(self) -> None:
        """Figure out the list of files to include in the source
        distribution, and put it in 'self.filelist'.  This might involve
        reading the manifest template (and writing the manifest), or just
        reading the manifest, or just using the default file set -- it all
        depends on the user's options.
        """
        # new behavior when using a template:
        # the file list is recalculated every time because
        # even if MANIFEST.in or setup.py are not changed
        # the user might have added some files in the tree that
        # need to be included.
        #
        #  This makes --force the default and only behavior with templates.
        template_exists = os.path.isfile(self.template)
        if not template_exists and self._manifest_is_not_generated():
            self.read_manifest()
            self.filelist.sort()
            self.filelist.remove_duplicates()
            return

        if not template_exists:
            self.warn(
                ("manifest template '%s' does not exist " + "(using default file list)")
                % self.template
            )
        self.filelist.findall()

        if self.use_defaults:
            self.add_defaults()

        if template_exists:
            self.read_template()

        if self.prune:
            self.prune_file_list()

        self.filelist.sort()
        self.filelist.remove_duplicates()
        self.write_manifest()

    def add_defaults(self) -> None:
        """Add all the default files to self.filelist:
          - README or README.txt
          - setup.py
          - tests/test*.py and test/test*.py
          - all pure Python modules mentioned in setup script
          - all files pointed by package_data (build_py)
          - all files defined in data_files.
          - all files defined as scripts.
          - all C sources listed as part of extensions or C libraries
            in the setup script (doesn't catch C headers!)
        Warns if (README or README.txt) or setup.py are missing; everything
        else is optional.
        """
        self._add_defaults_standards()
        self._add_defaults_optional()
        self._add_defaults_python()
        self._add_defaults_data_files()
        self._add_defaults_ext()
        self._add_defaults_c_libs()
        self._add_defaults_scripts()

    @staticmethod
    def _cs_path_exists(fspath):
        """
        Case-sensitive path existence check

        >>> sdist._cs_path_exists(__file__)
        True
        >>> sdist._cs_path_exists(__file__.upper())
        False
        """
        if not os.path.exists(fspath):
            return False
        # make absolute so we always have a directory
        abspath = os.path.abspath(fspath)
        directory, filename = os.path.split(abspath)
        return filename in os.listdir(directory)

    def _add_defaults_standards(self):
        standards = [self.READMES, self.distribution.script_name]
        for fn in standards:
            if isinstance(fn, tuple):
                alts = fn
                got_it = False
                for fn in alts:
                    if self._cs_path_exists(fn):
                        got_it = True
                        self.filelist.append(fn)
                        break

                if not got_it:
                    self.warn(
                        "standard file not found: should have one of " + ', '.join(alts)
                    )
            else:
                if self._cs_path_exists(fn):
                    self.filelist.append(fn)
                else:
                    self.warn(f"standard file '{fn}' not found")

    def _add_defaults_optional(self):
        optional = ['tests/test*.py', 'test/test*.py', 'setup.cfg']
        for pattern in optional:
            files = filter(os.path.isfile, glob(pattern))
            self.filelist.extend(files)

    def _add_defaults_python(self):
        # build_py is used to get:
        #  - python modules
        #  - files defined in package_data
        build_py = self.get_finalized_command('build_py')

        # getting python files
        if self.distribution.has_pure_modules():
            self.filelist.extend(build_py.get_source_files())

        # getting package_data files
        # (computed in build_py.data_files by build_py.finalize_options)
        for _pkg, src_dir, _build_dir, filenames in build_py.data_files:
            for filename in filenames:
                self.filelist.append(os.path.join(src_dir, filename))

    def _add_defaults_data_files(self):
        # getting distribution.data_files
        if self.distribution.has_data_files():
            for item in self.distribution.data_files:
                if isinstance(item, str):
                    # plain file
                    item = convert_path(item)
                    if os.path.isfile(item):
                        self.filelist.append(item)
                else:
                    # a (dirname, filenames) tuple
                    dirname, filenames = item
                    for f in filenames:
                        f = convert_path(f)
                        if os.path.isfile(f):
                            self.filelist.append(f)

    def _add_defaults_ext(self):
        if self.distribution.has_ext_modules():
            build_ext = self.get_finalized_command('build_ext')
            self.filelist.extend(build_ext.get_source_files())

    def _add_defaults_c_libs(self):
        if self.distribution.has_c_libraries():
            build_clib = self.get_finalized_command('build_clib')
            self.filelist.extend(build_clib.get_source_files())

    def _add_defaults_scripts(self):
        if self.distribution.has_scripts():
            build_scripts = self.get_finalized_command('build_scripts')
            self.filelist.extend(build_scripts.get_source_files())

    def read_template(self) -> None:
        """Read and parse manifest template file named by self.template.

        (usually "MANIFEST.in") The parsing and processing is done by
        'self.filelist', which updates itself accordingly.
        """
        log.info("reading manifest template '%s'", self.template)
        template = TextFile(
            self.template,
            strip_comments=True,
            skip_blanks=True,
            join_lines=True,
            lstrip_ws=True,
            rstrip_ws=True,
            collapse_join=True,
        )

        try:
            while True:
                line = template.readline()
                if line is None:  # end of file
                    break

                try:
                    self.filelist.process_template_line(line)
                # the call above can raise a DistutilsTemplateError for
                # malformed lines, or a ValueError from the lower-level
                # convert_path function
                except (DistutilsTemplateError, ValueError) as msg:
                    self.warn(
                        f"{template.filename}, line {int(template.current_line)}: {msg}"
                    )
        finally:
            template.close()

    def prune_file_list(self) -> None:
        """Prune off branches that might slip into the file list as created
        by 'read_template()', but really don't belong there:
          * the build tree (typically "build")
          * the release tree itself (only an issue if we ran "sdist"
            previously with --keep-temp, or it aborted)
          * any RCS, CVS, .svn, .hg, .git, .bzr, _darcs directories
        """
        build = self.get_finalized_command('build')
        base_dir = self.distribution.get_fullname()

        self.filelist.exclude_pattern(None, prefix=os.fspath(build.build_base))
        self.filelist.exclude_pattern(None, prefix=base_dir)

        if sys.platform == 'win32':
            seps = r'/|\\'
        else:
            seps = '/'

        vcs_dirs = ['RCS', 'CVS', r'\.svn', r'\.hg', r'\.git', r'\.bzr', '_darcs']
        vcs_ptrn = r'(^|{})({})({}).*'.format(seps, '|'.join(vcs_dirs), seps)
        self.filelist.exclude_pattern(vcs_ptrn, is_regex=True)

    def write_manifest(self) -> None:
        """Write the file list in 'self.filelist' (presumably as filled in
        by 'add_defaults()' and 'read_template()') to the manifest file
        named by 'self.manifest'.
        """
        if self._manifest_is_not_generated():
            log.info(
                f"not writing to manually maintained manifest file '{self.manifest}'"
            )
            return

        content = self.filelist.files[:]
        content.insert(0, '# file GENERATED by distutils, do NOT edit')
        self.execute(
            file_util.write_file,
            (self.manifest, content),
            f"writing manifest file '{self.manifest}'",
        )

    def _manifest_is_not_generated(self):
        # check for special comment used in 3.1.3 and higher
        if not os.path.isfile(self.manifest):
            return False

        with open(self.manifest, encoding='utf-8') as fp:
            first_line = next(fp)
        return first_line != '# file GENERATED by distutils, do NOT edit\n'

    def read_manifest(self) -> None:
        """Read the manifest file (named by 'self.manifest') and use it to
        fill in 'self.filelist', the list of files to include in the source
        distribution.
        """
        log.info("reading manifest file '%s'", self.manifest)
        with open(self.manifest, encoding='utf-8') as lines:
            self.filelist.extend(
                # ignore comments and blank lines
                filter(None, filterfalse(is_comment, map(str.strip, lines)))
            )

    def make_release_tree(self, base_dir, files) -> None:
        """Create the directory tree that will become the source
        distribution archive.  All directories implied by the filenames in
        'files' are created under 'base_dir', and then we hard link or copy
        (if hard linking is unavailable) those files into place.
        Essentially, this duplicates the developer's source tree, but in a
        directory named after the distribution, containing only the files
        to be distributed.
        """
        # Create all the directories under 'base_dir' necessary to
        # put 'files' there; the 'mkpath()' is just so we don't die
        # if the manifest happens to be empty.
        self.mkpath(base_dir)
        dir_util.create_tree(base_dir, files, dry_run=self.dry_run)

        # And walk over the list of files, either making a hard link (if
        # os.link exists) to each one that doesn't already exist in its
        # corresponding location under 'base_dir', or copying each file
        # that's out-of-date in 'base_dir'.  (Usually, all files will be
        # out-of-date, because by default we blow away 'base_dir' when
        # we're done making the distribution archives.)

        if hasattr(os, 'link'):  # can make hard links on this system
            link = 'hard'
            msg = f"making hard links in {base_dir}..."
        else:  # nope, have to copy
            link = None
            msg = f"copying files to {base_dir}..."

        if not files:
            log.warning("no files to distribute -- empty manifest?")
        else:
            log.info(msg)
        for file in files:
            if not os.path.isfile(file):
                log.warning("'%s' not a regular file -- skipping", file)
            else:
                dest = os.path.join(base_dir, file)
                self.copy_file(file, dest, link=link)

        self.distribution.metadata.write_pkg_info(base_dir)

    def make_distribution(self) -> None:
        """Create the source distribution(s).  First, we create the release
        tree with 'make_release_tree()'; then, we create all required
        archive files (according to 'self.formats') from the release tree.
        Finally, we clean up by blowing away the release tree (unless
        'self.keep_temp' is true).  The list of archive files created is
        stored so it can be retrieved later by 'get_archive_files()'.
        """
        # Don't warn about missing meta-data here -- should be (and is!)
        # done elsewhere.
        base_dir = self.distribution.get_fullname()
        base_name = os.path.join(self.dist_dir, base_dir)

        self.make_release_tree(base_dir, self.filelist.files)
        archive_files = []  # remember names of files we create
        # tar archive must be created last to avoid overwrite and remove
        if 'tar' in self.formats:
            self.formats.append(self.formats.pop(self.formats.index('tar')))

        for fmt in self.formats:
            file = self.make_archive(
                base_name, fmt, base_dir=base_dir, owner=self.owner, group=self.group
            )
            archive_files.append(file)
            self.distribution.dist_files.append(('sdist', '', file))

        self.archive_files = archive_files

        if not self.keep_temp:
            dir_util.remove_tree(base_dir, dry_run=self.dry_run)

    def get_archive_files(self):
        """Return the list of archive files created when the command
        was run, or None if the command hasn't run yet.
        """
        return self.archive_files


def is_comment(line: str) -> bool:
    return line.startswith('#')