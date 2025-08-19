
# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\framenet.py ===
# Natural Language Toolkit: Framenet Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Chuck Wooters <wooters@icsi.berkeley.edu>,
#          Nathan Schneider <nathan.schneider@georgetown.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
Corpus reader for the FrameNet 1.7 lexicon and corpus.
"""

import itertools
import os
import re
import sys
import textwrap
import types
from collections import OrderedDict, defaultdict
from itertools import zip_longest
from operator import itemgetter
from pprint import pprint

from nltk.corpus.reader import XMLCorpusReader, XMLCorpusView
from nltk.util import LazyConcatenation, LazyIteratorList, LazyMap

__docformat__ = "epytext en"


def mimic_wrap(lines, wrap_at=65, **kwargs):
    """
    Wrap the first of 'lines' with textwrap and the remaining lines at exactly the same
    positions as the first.
    """
    l0 = textwrap.fill(lines[0], wrap_at, drop_whitespace=False).split("\n")
    yield l0

    def _(line):
        il0 = 0
        while line and il0 < len(l0) - 1:
            yield line[: len(l0[il0])]
            line = line[len(l0[il0]) :]
            il0 += 1
        if line:  # Remaining stuff on this line past the end of the mimicked line.
            # So just textwrap this line.
            yield from textwrap.fill(line, wrap_at, drop_whitespace=False).split("\n")

    for l in lines[1:]:
        yield list(_(l))


def _pretty_longstring(defstr, prefix="", wrap_at=65):
    """
    Helper function for pretty-printing a long string.

    :param defstr: The string to be printed.
    :type defstr: str
    :return: A nicely formatted string representation of the long string.
    :rtype: str
    """
    return "\n".join(
        [prefix + line for line in textwrap.fill(defstr, wrap_at).split("\n")]
    )


def _pretty_any(obj):
    """
    Helper function for pretty-printing any AttrDict object.

    :param obj: The obj to be printed.
    :type obj: AttrDict
    :return: A nicely formatted string representation of the AttrDict object.
    :rtype: str
    """

    outstr = ""
    for k in obj:
        if isinstance(obj[k], str) and len(obj[k]) > 65:
            outstr += f"[{k}]\n"
            outstr += "{}".format(_pretty_longstring(obj[k], prefix="  "))
            outstr += "\n"
        else:
            outstr += f"[{k}] {obj[k]}\n"

    return outstr


def _pretty_semtype(st):
    """
    Helper function for pretty-printing a semantic type.

    :param st: The semantic type to be printed.
    :type st: AttrDict
    :return: A nicely formatted string representation of the semantic type.
    :rtype: str
    """

    semkeys = st.keys()
    if len(semkeys) == 1:
        return "<None>"

    outstr = ""
    outstr += "semantic type ({0.ID}): {0.name}\n".format(st)
    if "abbrev" in semkeys:
        outstr += f"[abbrev] {st.abbrev}\n"
    if "definition" in semkeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(st.definition, "  ")
    outstr += f"[rootType] {st.rootType.name}({st.rootType.ID})\n"
    if st.superType is None:
        outstr += "[superType] <None>\n"
    else:
        outstr += f"[superType] {st.superType.name}({st.superType.ID})\n"
    outstr += f"[subTypes] {len(st.subTypes)} subtypes\n"
    outstr += (
        "  "
        + ", ".join(f"{x.name}({x.ID})" for x in st.subTypes)
        + "\n" * (len(st.subTypes) > 0)
    )
    return outstr


def _pretty_frame_relation_type(freltyp):
    """
    Helper function for pretty-printing a frame relation type.

    :param freltyp: The frame relation type to be printed.
    :type freltyp: AttrDict
    :return: A nicely formatted string representation of the frame relation type.
    :rtype: str
    """
    outstr = "<frame relation type ({0.ID}): {0.superFrameName} -- {0.name} -> {0.subFrameName}>".format(
        freltyp
    )
    return outstr


def _pretty_frame_relation(frel):
    """
    Helper function for pretty-printing a frame relation.

    :param frel: The frame relation to be printed.
    :type frel: AttrDict
    :return: A nicely formatted string representation of the frame relation.
    :rtype: str
    """
    outstr = "<{0.type.superFrameName}={0.superFrameName} -- {0.type.name} -> {0.type.subFrameName}={0.subFrameName}>".format(
        frel
    )
    return outstr


def _pretty_fe_relation(ferel):
    """
    Helper function for pretty-printing an FE relation.

    :param ferel: The FE relation to be printed.
    :type ferel: AttrDict
    :return: A nicely formatted string representation of the FE relation.
    :rtype: str
    """
    outstr = "<{0.type.superFrameName}={0.frameRelation.superFrameName}.{0.superFEName} -- {0.type.name} -> {0.type.subFrameName}={0.frameRelation.subFrameName}.{0.subFEName}>".format(
        ferel
    )
    return outstr


def _pretty_lu(lu):
    """
    Helper function for pretty-printing a lexical unit.

    :param lu: The lu to be printed.
    :type lu: AttrDict
    :return: A nicely formatted string representation of the lexical unit.
    :rtype: str
    """

    lukeys = lu.keys()
    outstr = ""
    outstr += "lexical unit ({0.ID}): {0.name}\n\n".format(lu)
    if "definition" in lukeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(lu.definition, "  ")
    if "frame" in lukeys:
        outstr += f"\n[frame] {lu.frame.name}({lu.frame.ID})\n"
    if "incorporatedFE" in lukeys:
        outstr += f"\n[incorporatedFE] {lu.incorporatedFE}\n"
    if "POS" in lukeys:
        outstr += f"\n[POS] {lu.POS}\n"
    if "status" in lukeys:
        outstr += f"\n[status] {lu.status}\n"
    if "totalAnnotated" in lukeys:
        outstr += f"\n[totalAnnotated] {lu.totalAnnotated} annotated examples\n"
    if "lexemes" in lukeys:
        outstr += "\n[lexemes] {}\n".format(
            " ".join(f"{lex.name}/{lex.POS}" for lex in lu.lexemes)
        )
    if "semTypes" in lukeys:
        outstr += f"\n[semTypes] {len(lu.semTypes)} semantic types\n"
        outstr += (
            "  " * (len(lu.semTypes) > 0)
            + ", ".join(f"{x.name}({x.ID})" for x in lu.semTypes)
            + "\n" * (len(lu.semTypes) > 0)
        )
    if "URL" in lukeys:
        outstr += f"\n[URL] {lu.URL}\n"
    if "subCorpus" in lukeys:
        subc = [x.name for x in lu.subCorpus]
        outstr += f"\n[subCorpus] {len(lu.subCorpus)} subcorpora\n"
        for line in textwrap.fill(", ".join(sorted(subc)), 60).split("\n"):
            outstr += f"  {line}\n"
    if "exemplars" in lukeys:
        outstr += "\n[exemplars] {} sentences across all subcorpora\n".format(
            len(lu.exemplars)
        )

    return outstr


def _pretty_exemplars(exemplars, lu):
    """
    Helper function for pretty-printing a list of exemplar sentences for a lexical unit.

    :param sent: The list of exemplar sentences to be printed.
    :type sent: list(AttrDict)
    :return: An index of the text of the exemplar sentences.
    :rtype: str
    """

    outstr = ""
    outstr += "exemplar sentences for {0.name} in {0.frame.name}:\n\n".format(lu)
    for i, sent in enumerate(exemplars):
        outstr += f"[{i}] {sent.text}\n"
    outstr += "\n"
    return outstr


def _pretty_fulltext_sentences(sents):
    """
    Helper function for pretty-printing a list of annotated sentences for a full-text document.

    :param sent: The list of sentences to be printed.
    :type sent: list(AttrDict)
    :return: An index of the text of the sentences.
    :rtype: str
    """

    outstr = ""
    outstr += "full-text document ({0.ID}) {0.name}:\n\n".format(sents)
    outstr += "[corpid] {0.corpid}\n[corpname] {0.corpname}\n[description] {0.description}\n[URL] {0.URL}\n\n".format(
        sents
    )
    outstr += f"[sentence]\n"
    for i, sent in enumerate(sents.sentence):
        outstr += f"[{i}] {sent.text}\n"
    outstr += "\n"
    return outstr


def _pretty_fulltext_sentence(sent):
    """
    Helper function for pretty-printing an annotated sentence from a full-text document.

    :param sent: The sentence to be printed.
    :type sent: list(AttrDict)
    :return: The text of the sentence with annotation set indices on frame targets.
    :rtype: str
    """

    outstr = ""
    outstr += "full-text sentence ({0.ID}) in {1}:\n\n".format(
        sent, sent.doc.get("name", sent.doc.description)
    )
    outstr += f"\n[POS] {len(sent.POS)} tags\n"
    outstr += f"\n[POS_tagset] {sent.POS_tagset}\n\n"
    outstr += "[text] + [annotationSet]\n\n"
    outstr += sent._ascii()  # -> _annotation_ascii()
    outstr += "\n"
    return outstr


def _pretty_pos(aset):
    """
    Helper function for pretty-printing a sentence with its POS tags.

    :param aset: The POS annotation set of the sentence to be printed.
    :type sent: list(AttrDict)
    :return: The text of the sentence and its POS tags.
    :rtype: str
    """

    outstr = ""
    outstr += "POS annotation set ({0.ID}) {0.POS_tagset} in sentence {0.sent.ID}:\n\n".format(
        aset
    )

    # list the target spans and their associated aset index
    overt = sorted(aset.POS)

    sent = aset.sent
    s0 = sent.text
    s1 = ""
    s2 = ""
    i = 0
    adjust = 0
    for j, k, lbl in overt:
        assert j >= i, ("Overlapping targets?", (j, k, lbl))
        s1 += " " * (j - i) + "-" * (k - j)
        if len(lbl) > (k - j):
            # add space in the sentence to make room for the annotation index
            amt = len(lbl) - (k - j)
            s0 = (
                s0[: k + adjust] + "~" * amt + s0[k + adjust :]
            )  # '~' to prevent line wrapping
            s1 = s1[: k + adjust] + " " * amt + s1[k + adjust :]
            adjust += amt
        s2 += " " * (j - i) + lbl.ljust(k - j)
        i = k

    long_lines = [s0, s1, s2]

    outstr += "\n\n".join(
        map("\n".join, zip_longest(*mimic_wrap(long_lines), fillvalue=" "))
    ).replace("~", " ")
    outstr += "\n"
    return outstr


def _pretty_annotation(sent, aset_level=False):
    """
    Helper function for pretty-printing an exemplar sentence for a lexical unit.

    :param sent: An annotation set or exemplar sentence to be printed.
    :param aset_level: If True, 'sent' is actually an annotation set within a sentence.
    :type sent: AttrDict
    :return: A nicely formatted string representation of the exemplar sentence
    with its target, frame, and FE annotations.
    :rtype: str
    """

    sentkeys = sent.keys()
    outstr = "annotation set" if aset_level else "exemplar sentence"
    outstr += f" ({sent.ID}):\n"
    if aset_level:  # TODO: any UNANN exemplars?
        outstr += f"\n[status] {sent.status}\n"
    for k in ("corpID", "docID", "paragNo", "sentNo", "aPos"):
        if k in sentkeys:
            outstr += f"[{k}] {sent[k]}\n"
    outstr += (
        "\n[LU] ({0.ID}) {0.name} in {0.frame.name}\n".format(sent.LU)
        if sent.LU
        else "\n[LU] Not found!"
    )
    outstr += "\n[frame] ({0.ID}) {0.name}\n".format(
        sent.frame
    )  # redundant with above, but .frame is convenient
    if not aset_level:
        outstr += "\n[annotationSet] {} annotation sets\n".format(
            len(sent.annotationSet)
        )
        outstr += f"\n[POS] {len(sent.POS)} tags\n"
        outstr += f"\n[POS_tagset] {sent.POS_tagset}\n"
    outstr += "\n[GF] {} relation{}\n".format(
        len(sent.GF), "s" if len(sent.GF) != 1 else ""
    )
    outstr += "\n[PT] {} phrase{}\n".format(
        len(sent.PT), "s" if len(sent.PT) != 1 else ""
    )
    """
    Special Layers
    --------------

    The 'NER' layer contains, for some of the data, named entity labels.

    The 'WSL' (word status layer) contains, for some of the data,
    spans which should not in principle be considered targets (NT).

    The 'Other' layer records relative clause constructions (Rel=relativizer, Ant=antecedent),
    pleonastic 'it' (Null), and existential 'there' (Exist).
    On occasion they are duplicated by accident (e.g., annotationSet 1467275 in lu6700.xml).

    The 'Sent' layer appears to contain labels that the annotator has flagged the
    sentence with for their convenience: values include
    'sense1', 'sense2', 'sense3', etc.;
    'Blend', 'Canonical', 'Idiom', 'Metaphor', 'Special-Sent',
    'keepS', 'deleteS', 'reexamine'
    (sometimes they are duplicated for no apparent reason).

    The POS-specific layers may contain the following kinds of spans:
    Asp (aspectual particle), Non-Asp (non-aspectual particle),
    Cop (copula), Supp (support), Ctrlr (controller),
    Gov (governor), X. Gov and X always cooccur.

    >>> from nltk.corpus import framenet as fn
    >>> def f(luRE, lyr, ignore=set()):
    ...   for i,ex in enumerate(fn.exemplars(luRE)):
    ...     if lyr in ex and ex[lyr] and set(zip(*ex[lyr])[2]) - ignore:
    ...       print(i,ex[lyr])

    - Verb: Asp, Non-Asp
    - Noun: Cop, Supp, Ctrlr, Gov, X
    - Adj: Cop, Supp, Ctrlr, Gov, X
    - Prep: Cop, Supp, Ctrlr
    - Adv: Ctrlr
    - Scon: (none)
    - Art: (none)
    """
    for lyr in ("NER", "WSL", "Other", "Sent"):
        if lyr in sent and sent[lyr]:
            outstr += "\n[{}] {} entr{}\n".format(
                lyr, len(sent[lyr]), "ies" if len(sent[lyr]) != 1 else "y"
            )
    outstr += "\n[text] + [Target] + [FE]"
    # POS-specific layers: syntactically important words that are neither the target
    # nor the FEs. Include these along with the first FE layer but with '^' underlining.
    for lyr in ("Verb", "Noun", "Adj", "Adv", "Prep", "Scon", "Art"):
        if lyr in sent and sent[lyr]:
            outstr += f" + [{lyr}]"
    if "FE2" in sentkeys:
        outstr += " + [FE2]"
        if "FE3" in sentkeys:
            outstr += " + [FE3]"
    outstr += "\n\n"
    outstr += sent._ascii()  # -> _annotation_ascii()
    outstr += "\n"

    return outstr


def _annotation_ascii(sent):
    """
    Given a sentence or FE annotation set, construct the width-limited string showing
    an ASCII visualization of the sentence's annotations, calling either
    _annotation_ascii_frames() or _annotation_ascii_FEs() as appropriate.
    This will be attached as a method to appropriate AttrDict instances
    and called in the full pretty-printing of the instance.
    """
    if sent._type == "fulltext_sentence" or (
        "annotationSet" in sent and len(sent.annotationSet) > 2
    ):
        # a full-text sentence OR sentence with multiple targets.
        # (multiple targets = >2 annotation sets, because the first annotation set is POS.)
        return _annotation_ascii_frames(sent)
    else:  # an FE annotation set, or an LU sentence with 1 target
        return _annotation_ascii_FEs(sent)


def _annotation_ascii_frames(sent):
    """
    ASCII string rendering of the sentence along with its targets and frame names.
    Called for all full-text sentences, as well as the few LU sentences with multiple
    targets (e.g., fn.lu(6412).exemplars[82] has two want.v targets).
    Line-wrapped to limit the display width.
    """
    # list the target spans and their associated aset index
    overt = []
    for a, aset in enumerate(sent.annotationSet[1:]):
        for j, k in aset.Target:
            indexS = f"[{a + 1}]"
            if aset.status == "UNANN" or aset.LU.status == "Problem":
                indexS += " "
                if aset.status == "UNANN":
                    indexS += "!"  # warning indicator that there is a frame annotation but no FE annotation
                if aset.LU.status == "Problem":
                    indexS += "?"  # warning indicator that there is a missing LU definition (because the LU has Problem status)
            overt.append((j, k, aset.LU.frame.name, indexS))
    overt = sorted(overt)

    duplicates = set()
    for o, (j, k, fname, asetIndex) in enumerate(overt):
        if o > 0 and j <= overt[o - 1][1]:
            # multiple annotation sets on the same target
            # (e.g. due to a coordination construction or multiple annotators)
            if (
                overt[o - 1][:2] == (j, k) and overt[o - 1][2] == fname
            ):  # same target, same frame
                # splice indices together
                combinedIndex = (
                    overt[o - 1][3] + asetIndex
                )  # e.g., '[1][2]', '[1]! [2]'
                combinedIndex = combinedIndex.replace(" !", "! ").replace(" ?", "? ")
                overt[o - 1] = overt[o - 1][:3] + (combinedIndex,)
                duplicates.add(o)
            else:  # different frames, same or overlapping targets
                s = sent.text
                for j, k, fname, asetIndex in overt:
                    s += "\n" + asetIndex + " " + sent.text[j:k] + " :: " + fname
                s += "\n(Unable to display sentence with targets marked inline due to overlap)"
                return s
    for o in reversed(sorted(duplicates)):
        del overt[o]

    s0 = sent.text
    s1 = ""
    s11 = ""
    s2 = ""
    i = 0
    adjust = 0
    fAbbrevs = OrderedDict()
    for j, k, fname, asetIndex in overt:
        if not j >= i:
            assert j >= i, (
                "Overlapping targets?"
                + (
                    " UNANN"
                    if any(aset.status == "UNANN" for aset in sent.annotationSet[1:])
                    else ""
                ),
                (j, k, asetIndex),
            )
        s1 += " " * (j - i) + "*" * (k - j)
        short = fname[: k - j]
        if (k - j) < len(fname):
            r = 0
            while short in fAbbrevs:
                if fAbbrevs[short] == fname:
                    break
                r += 1
                short = fname[: k - j - 1] + str(r)
            else:  # short not in fAbbrevs
                fAbbrevs[short] = fname
        s11 += " " * (j - i) + short.ljust(k - j)
        if len(asetIndex) > (k - j):
            # add space in the sentence to make room for the annotation index
            amt = len(asetIndex) - (k - j)
            s0 = (
                s0[: k + adjust] + "~" * amt + s0[k + adjust :]
            )  # '~' to prevent line wrapping
            s1 = s1[: k + adjust] + " " * amt + s1[k + adjust :]
            s11 = s11[: k + adjust] + " " * amt + s11[k + adjust :]
            adjust += amt
        s2 += " " * (j - i) + asetIndex.ljust(k - j)
        i = k

    long_lines = [s0, s1, s11, s2]

    outstr = "\n\n".join(
        map("\n".join, zip_longest(*mimic_wrap(long_lines), fillvalue=" "))
    ).replace("~", " ")
    outstr += "\n"
    if fAbbrevs:
        outstr += " (" + ", ".join("=".join(pair) for pair in fAbbrevs.items()) + ")"
        assert len(fAbbrevs) == len(dict(fAbbrevs)), "Abbreviation clash"

    return outstr


def _annotation_ascii_FE_layer(overt, ni, feAbbrevs):
    """Helper for _annotation_ascii_FEs()."""
    s1 = ""
    s2 = ""
    i = 0
    for j, k, fename in overt:
        s1 += " " * (j - i) + ("^" if fename.islower() else "-") * (k - j)
        short = fename[: k - j]
        if len(fename) > len(short):
            r = 0
            while short in feAbbrevs:
                if feAbbrevs[short] == fename:
                    break
                r += 1
                short = fename[: k - j - 1] + str(r)
            else:  # short not in feAbbrevs
                feAbbrevs[short] = fename
        s2 += " " * (j - i) + short.ljust(k - j)
        i = k

    sNI = ""
    if ni:
        sNI += " [" + ", ".join(":".join(x) for x in sorted(ni.items())) + "]"
    return [s1, s2, sNI]


def _annotation_ascii_FEs(sent):
    """
    ASCII string rendering of the sentence along with a single target and its FEs.
    Secondary and tertiary FE layers are included if present.
    'sent' can be an FE annotation set or an LU sentence with a single target.
    Line-wrapped to limit the display width.
    """
    feAbbrevs = OrderedDict()
    posspec = []  # POS-specific layer spans (e.g., Supp[ort], Cop[ula])
    posspec_separate = False
    for lyr in ("Verb", "Noun", "Adj", "Adv", "Prep", "Scon", "Art"):
        if lyr in sent and sent[lyr]:
            for a, b, lbl in sent[lyr]:
                if (
                    lbl == "X"
                ):  # skip this, which covers an entire phrase typically containing the target and all its FEs
                    # (but do display the Gov)
                    continue
                if any(1 for x, y, felbl in sent.FE[0] if x <= a < y or a <= x < b):
                    # overlap between one of the POS-specific layers and first FE layer
                    posspec_separate = (
                        True  # show POS-specific layers on a separate line
                    )
                posspec.append(
                    (a, b, lbl.lower().replace("-", ""))
                )  # lowercase Cop=>cop, Non-Asp=>nonasp, etc. to distinguish from FE names
    if posspec_separate:
        POSSPEC = _annotation_ascii_FE_layer(posspec, {}, feAbbrevs)
    FE1 = _annotation_ascii_FE_layer(
        sorted(sent.FE[0] + (posspec if not posspec_separate else [])),
        sent.FE[1],
        feAbbrevs,
    )
    FE2 = FE3 = None
    if "FE2" in sent:
        FE2 = _annotation_ascii_FE_layer(sent.FE2[0], sent.FE2[1], feAbbrevs)
        if "FE3" in sent:
            FE3 = _annotation_ascii_FE_layer(sent.FE3[0], sent.FE3[1], feAbbrevs)

    for i, j in sent.Target:
        FE1span, FE1name, FE1exp = FE1
        if len(FE1span) < j:
            FE1span += " " * (j - len(FE1span))
        if len(FE1name) < j:
            FE1name += " " * (j - len(FE1name))
            FE1[1] = FE1name
        FE1[0] = (
            FE1span[:i] + FE1span[i:j].replace(" ", "*").replace("-", "=") + FE1span[j:]
        )
    long_lines = [sent.text]
    if posspec_separate:
        long_lines.extend(POSSPEC[:2])
    long_lines.extend([FE1[0], FE1[1] + FE1[2]])  # lines with no length limit
    if FE2:
        long_lines.extend([FE2[0], FE2[1] + FE2[2]])
        if FE3:
            long_lines.extend([FE3[0], FE3[1] + FE3[2]])
    long_lines.append("")
    outstr = "\n".join(
        map("\n".join, zip_longest(*mimic_wrap(long_lines), fillvalue=" "))
    )
    if feAbbrevs:
        outstr += "(" + ", ".join("=".join(pair) for pair in feAbbrevs.items()) + ")"
        assert len(feAbbrevs) == len(dict(feAbbrevs)), "Abbreviation clash"
    outstr += "\n"

    return outstr


def _pretty_fe(fe):
    """
    Helper function for pretty-printing a frame element.

    :param fe: The frame element to be printed.
    :type fe: AttrDict
    :return: A nicely formatted string representation of the frame element.
    :rtype: str
    """
    fekeys = fe.keys()
    outstr = ""
    outstr += "frame element ({0.ID}): {0.name}\n    of {1.name}({1.ID})\n".format(
        fe, fe.frame
    )
    if "definition" in fekeys:
        outstr += "[definition]\n"
        outstr += _pretty_longstring(fe.definition, "  ")
    if "abbrev" in fekeys:
        outstr += f"[abbrev] {fe.abbrev}\n"
    if "coreType" in fekeys:
        outstr += f"[coreType] {fe.coreType}\n"
    if "requiresFE" in fekeys:
        outstr += "[requiresFE] "
        if fe.requiresFE is None:
            outstr += "<None>\n"
        else:
            outstr += f"{fe.requiresFE.name}({fe.requiresFE.ID})\n"
    if "excludesFE" in fekeys:
        outstr += "[excludesFE] "
        if fe.excludesFE is None:
            outstr += "<None>\n"
        else:
            outstr += f"{fe.excludesFE.name}({fe.excludesFE.ID})\n"
    if "semType" in fekeys:
        outstr += "[semType] "
        if fe.semType is None:
            outstr += "<None>\n"
        else:
            outstr += "\n  " + f"{fe.semType.name}({fe.semType.ID})" + "\n"

    return outstr


def _pretty_frame(frame):
    """
    Helper function for pretty-printing a frame.

    :param frame: The frame to be printed.
    :type frame: AttrDict
    :return: A nicely formatted string representation of the frame.
    :rtype: str
    """

    outstr = ""
    outstr += "frame ({0.ID}): {0.name}\n\n".format(frame)
    outstr += f"[URL] {frame.URL}\n\n"
    outstr += "[definition]\n"
    outstr += _pretty_longstring(frame.definition, "  ") + "\n"

    outstr += f"[semTypes] {len(frame.semTypes)} semantic types\n"
    outstr += (
        "  " * (len(frame.semTypes) > 0)
        + ", ".join(f"{x.name}({x.ID})" for x in frame.semTypes)
        + "\n" * (len(frame.semTypes) > 0)
    )

    outstr += "\n[frameRelations] {} frame relations\n".format(
        len(frame.frameRelations)
    )
    outstr += "  " + "\n  ".join(repr(frel) for frel in frame.frameRelations) + "\n"

    outstr += f"\n[lexUnit] {len(frame.lexUnit)} lexical units\n"
    lustrs = []
    for luName, lu in sorted(frame.lexUnit.items()):
        tmpstr = f"{luName} ({lu.ID})"
        lustrs.append(tmpstr)
    outstr += "{}\n".format(_pretty_longstring(", ".join(lustrs), prefix="  "))

    outstr += f"\n[FE] {len(frame.FE)} frame elements\n"
    fes = {}
    for feName, fe in sorted(frame.FE.items()):
        try:
            fes[fe.coreType].append(f"{feName} ({fe.ID})")
        except KeyError:
            fes[fe.coreType] = []
            fes[fe.coreType].append(f"{feName} ({fe.ID})")
    for ct in sorted(
        fes.keys(),
        key=lambda ct2: [
            "Core",
            "Core-Unexpressed",
            "Peripheral",
            "Extra-Thematic",
        ].index(ct2),
    ):
        outstr += "{:>16}: {}\n".format(ct, ", ".join(sorted(fes[ct])))

    outstr += "\n[FEcoreSets] {} frame element core sets\n".format(
        len(frame.FEcoreSets)
    )
    outstr += (
        "  "
        + "\n  ".join(
            ", ".join([x.name for x in coreSet]) for coreSet in frame.FEcoreSets
        )
        + "\n"
    )

    return outstr


class FramenetError(Exception):
    """An exception class for framenet-related errors."""


class AttrDict(dict):
    """A class that wraps a dict and allows accessing the keys of the
    dict as if they were attributes. Taken from here:
    https://stackoverflow.com/a/14620633/8879

    >>> foo = {'a':1, 'b':2, 'c':3}
    >>> bar = AttrDict(foo)
    >>> pprint(dict(bar))
    {'a': 1, 'b': 2, 'c': 3}
    >>> bar.b
    2
    >>> bar.d = 4
    >>> pprint(dict(bar))
    {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.__dict__ = self

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        if name == "_short_repr":
            return self._short_repr
        return self[name]

    def __getitem__(self, name):
        v = super().__getitem__(name)
        if isinstance(v, Future):
            return v._data()
        return v

    def _short_repr(self):
        if "_type" in self:
            if self["_type"].endswith("relation"):
                return self.__repr__()
            try:
                return "<{} ID={} name={}>".format(
                    self["_type"], self["ID"], self["name"]
                )
            except KeyError:
                try:  # no ID--e.g., for _type=lusubcorpus
                    return "<{} name={}>".format(self["_type"], self["name"])
                except KeyError:  # no name--e.g., for _type=lusentence
                    return "<{} ID={}>".format(self["_type"], self["ID"])
        else:
            return self.__repr__()

    def _str(self):
        outstr = ""

        if "_type" not in self:
            outstr = _pretty_any(self)
        elif self["_type"] == "frame":
            outstr = _pretty_frame(self)
        elif self["_type"] == "fe":
            outstr = _pretty_fe(self)
        elif self["_type"] == "lu":
            outstr = _pretty_lu(self)
        elif self["_type"] == "luexemplars":  # list of ALL exemplars for LU
            outstr = _pretty_exemplars(self, self[0].LU)
        elif (
            self["_type"] == "fulltext_annotation"
        ):  # list of all sentences for full-text doc
            outstr = _pretty_fulltext_sentences(self)
        elif self["_type"] == "lusentence":
            outstr = _pretty_annotation(self)
        elif self["_type"] == "fulltext_sentence":
            outstr = _pretty_fulltext_sentence(self)
        elif self["_type"] in ("luannotationset", "fulltext_annotationset"):
            outstr = _pretty_annotation(self, aset_level=True)
        elif self["_type"] == "posannotationset":
            outstr = _pretty_pos(self)
        elif self["_type"] == "semtype":
            outstr = _pretty_semtype(self)
        elif self["_type"] == "framerelationtype":
            outstr = _pretty_frame_relation_type(self)
        elif self["_type"] == "framerelation":
            outstr = _pretty_frame_relation(self)
        elif self["_type"] == "ferelation":
            outstr = _pretty_fe_relation(self)
        else:
            outstr = _pretty_any(self)

        # ensure result is unicode string prior to applying the
        #  decorator (because non-ASCII characters
        # could in principle occur in the data and would trigger an encoding error when
        # passed as arguments to str.format()).
        # assert isinstance(outstr, unicode) # not in Python 3.2
        return outstr

    def __str__(self):
        return self._str()

    def __repr__(self):
        return self.__str__()


class SpecialList(list):
    """
    A list subclass which adds a '_type' attribute for special printing
    (similar to an AttrDict, though this is NOT an AttrDict subclass).
    """

    def __init__(self, typ, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = typ

    def _str(self):
        outstr = ""

        assert self._type
        if len(self) == 0:
            outstr = "[]"
        elif self._type == "luexemplars":  # list of ALL exemplars for LU
            outstr = _pretty_exemplars(self, self[0].LU)
        else:
            assert False, self._type
        return outstr

    def __str__(self):
        return self._str()

    def __repr__(self):
        return self.__str__()


class Future:
    """
    Wraps and acts as a proxy for a value to be loaded lazily (on demand).
    Adapted from https://gist.github.com/sergey-miryanov/2935416
    """

    def __init__(self, loader, *args, **kwargs):
        """
        :param loader: when called with no arguments, returns the value to be stored
        :type loader: callable
        """
        super().__init__(*args, **kwargs)
        self._loader = loader
        self._d = None

    def _data(self):
        if callable(self._loader):
            self._d = self._loader()
            self._loader = None  # the data is now cached
        return self._d

    def __nonzero__(self):
        return bool(self._data())

    def __len__(self):
        return len(self._data())

    def __setitem__(self, key, value):
        return self._data().__setitem__(key, value)

    def __getitem__(self, key):
        return self._data().__getitem__(key)

    def __getattr__(self, key):
        return self._data().__getattr__(key)

    def __str__(self):
        return self._data().__str__()

    def __repr__(self):
        return self._data().__repr__()


class PrettyDict(AttrDict):
    """
    Displays an abbreviated repr of values where possible.
    Inherits from AttrDict, so a callable value will
    be lazily converted to an actual value.
    """

    def __init__(self, *args, **kwargs):
        _BREAK_LINES = kwargs.pop("breakLines", False)
        super().__init__(*args, **kwargs)
        dict.__setattr__(self, "_BREAK_LINES", _BREAK_LINES)

    def __repr__(self):
        parts = []
        for k, v in sorted(self.items()):
            kv = repr(k) + ": "
            try:
                kv += v._short_repr()
            except AttributeError:
                kv += repr(v)
            parts.append(kv)
        return "{" + (",\n " if self._BREAK_LINES else ", ").join(parts) + "}"


class PrettyList(list):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """

    # from nltk.util
    def __init__(self, *args, **kwargs):
        self._MAX_REPR_SIZE = kwargs.pop("maxReprSize", 60)
        self._BREAK_LINES = kwargs.pop("breakLines", False)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5

        for elt in self:
            pieces.append(
                elt._short_repr()
            )  # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if self._MAX_REPR_SIZE and length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % str(",\n " if self._BREAK_LINES else ", ").join(
                    pieces[:-1]
                )
        return "[%s]" % str(",\n " if self._BREAK_LINES else ", ").join(pieces)


class PrettyLazyMap(LazyMap):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """

    # from nltk.util
    _MAX_REPR_SIZE = 60

    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(
                elt._short_repr()
            )  # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % ", ".join(pieces[:-1])
        return "[%s]" % ", ".join(pieces)


class PrettyLazyIteratorList(LazyIteratorList):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """

    # from nltk.util
    _MAX_REPR_SIZE = 60

    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(
                elt._short_repr()
            )  # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % ", ".join(pieces[:-1])
        return "[%s]" % ", ".join(pieces)


class PrettyLazyConcatenation(LazyConcatenation):
    """
    Displays an abbreviated repr of only the first several elements, not the whole list.
    """

    # from nltk.util
    _MAX_REPR_SIZE = 60

    def __repr__(self):
        """
        Return a string representation for this corpus view that is
        similar to a list's representation; but if it would be more
        than 60 characters long, it is truncated.
        """
        pieces = []
        length = 5
        for elt in self:
            pieces.append(
                elt._short_repr()
            )  # key difference from inherited version: call to _short_repr()
            length += len(pieces[-1]) + 2
            if length > self._MAX_REPR_SIZE and len(pieces) > 2:
                return "[%s, ...]" % ", ".join(pieces[:-1])
        return "[%s]" % ", ".join(pieces)

    def __add__(self, other):
        """Return a list concatenating self with other."""
        return PrettyLazyIteratorList(itertools.chain(self, other))

    def __radd__(self, other):
        """Return a list concatenating other with self."""
        return PrettyLazyIteratorList(itertools.chain(other, self))


class FramenetCorpusReader(XMLCorpusReader):
    """A corpus reader for the Framenet Corpus.

    >>> from nltk.corpus import framenet as fn
    >>> fn.lu(3238).frame.lexUnit['glint.v'] is fn.lu(3238)
    True
    >>> fn.frame_by_name('Replacing') is fn.lus('replace.v')[0].frame
    True
    >>> fn.lus('prejudice.n')[0].frame.frameRelations == fn.frame_relations('Partiality')
    True
    """

    _bad_statuses = ["Problem"]
    """
    When loading LUs for a frame, those whose status is in this list will be ignored.
    Due to caching, if user code modifies this, it should do so before loading any data.
    'Problem' should always be listed for FrameNet 1.5, as these LUs are not included
    in the XML index.
    """

    _warnings = False

    def warnings(self, v):
        """Enable or disable warnings of data integrity issues as they are encountered.
        If v is truthy, warnings will be enabled.

        (This is a function rather than just an attribute/property to ensure that if
        enabling warnings is the first action taken, the corpus reader is instantiated first.)
        """
        self._warnings = v

    def __init__(self, root, fileids):
        XMLCorpusReader.__init__(self, root, fileids)

        # framenet corpus sub dirs
        # sub dir containing the xml files for frames
        self._frame_dir = "frame"
        # sub dir containing the xml files for lexical units
        self._lu_dir = "lu"
        # sub dir containing the xml files for fulltext annotation files
        self._fulltext_dir = "fulltext"

        # location of latest development version of FrameNet
        self._fnweb_url = "https://framenet2.icsi.berkeley.edu/fnReports/data"

        # Indexes used for faster look-ups
        self._frame_idx = None
        self._cached_frames = {}  # name -> ID
        self._lu_idx = None
        self._fulltext_idx = None
        self._semtypes = None
        self._freltyp_idx = None  # frame relation types (Inheritance, Using, etc.)
        self._frel_idx = None  # frame-to-frame relation instances
        self._ferel_idx = None  # FE-to-FE relation instances
        self._frel_f_idx = None  # frame-to-frame relations associated with each frame

        self._readme = "README.txt"

    def help(self, attrname=None):
        """Display help information summarizing the main methods."""

        if attrname is not None:
            return help(self.__getattribute__(attrname))

        # No need to mention frame_by_name() or frame_by_id(),
        # as it's easier to just call frame().
        # Also not mentioning lu_basic().

        msg = """
Citation: Nathan Schneider and Chuck Wooters (2017),
"The NLTK FrameNet API: Designing for Discoverability with a Rich Linguistic Resource".
Proceedings of EMNLP: System Demonstrations. https://arxiv.org/abs/1703.07438

Use the following methods to access data in FrameNet.
Provide a method name to `help()` for more information.

FRAMES
======

frame() to look up a frame by its exact name or ID
frames() to get frames matching a name pattern
frames_by_lemma() to get frames containing an LU matching a name pattern
frame_ids_and_names() to get a mapping from frame IDs to names

FRAME ELEMENTS
==============

fes() to get frame elements (a.k.a. roles) matching a name pattern, optionally constrained
  by a frame name pattern

LEXICAL UNITS
=============

lu() to look up an LU by its ID
lus() to get lexical units matching a name pattern, optionally constrained by frame
lu_ids_and_names() to get a mapping from LU IDs to names

RELATIONS
=========

frame_relation_types() to get the different kinds of frame-to-frame relations
  (Inheritance, Subframe, Using, etc.).
frame_relations() to get the relation instances, optionally constrained by
  frame(s) or relation type
fe_relations() to get the frame element pairs belonging to a frame-to-frame relation

SEMANTIC TYPES
==============

semtypes() to get the different kinds of semantic types that can be applied to
  FEs, LUs, and entire frames
semtype() to look up a particular semtype by name, ID, or abbreviation
semtype_inherits() to check whether two semantic types have a subtype-supertype
  relationship in the semtype hierarchy
propagate_semtypes() to apply inference rules that distribute semtypes over relations
  between FEs

ANNOTATIONS
===========

annotations() to get annotation sets, in which a token in a sentence is annotated
  with a lexical unit in a frame, along with its frame elements and their syntactic properties;
  can be constrained by LU name pattern and limited to lexicographic exemplars or full-text.
  Sentences of full-text annotation can have multiple annotation sets.
sents() to get annotated sentences illustrating one or more lexical units
exemplars() to get sentences of lexicographic annotation, most of which have
  just 1 annotation set; can be constrained by LU name pattern, frame, and overt FE(s)
doc() to look up a document of full-text annotation by its ID
docs() to get documents of full-text annotation that match a name pattern
docs_metadata() to get metadata about all full-text documents without loading them
ft_sents() to iterate over sentences of full-text annotation

UTILITIES
=========

buildindexes() loads metadata about all frames, LUs, etc. into memory to avoid
  delay when one is accessed for the first time. It does not load annotations.
readme() gives the text of the FrameNet README file
warnings(True) to display corpus consistency warnings when loading data
        """
        print(msg)

    def _buildframeindex(self):
        # The total number of Frames in Framenet is fairly small (~1200) so
        # this index should not be very large
        if not self._frel_idx:
            self._buildrelationindex()  # always load frame relations before frames,
            # otherwise weird ordering effects might result in incomplete information
        self._frame_idx = {}
        with XMLCorpusView(
            self.abspath("frameIndex.xml"), "frameIndex/frame", self._handle_elt
        ) as view:
            for f in view:
                self._frame_idx[f["ID"]] = f

    def _buildcorpusindex(self):
        # The total number of fulltext annotated documents in Framenet
        # is fairly small (~90) so this index should not be very large
        self._fulltext_idx = {}
        with XMLCorpusView(
            self.abspath("fulltextIndex.xml"),
            "fulltextIndex/corpus",
            self._handle_fulltextindex_elt,
        ) as view:
            for doclist in view:
                for doc in doclist:
                    self._fulltext_idx[doc.ID] = doc

    def _buildluindex(self):
        # The number of LUs in Framenet is about 13,000 so this index
        # should not be very large
        self._lu_idx = {}
        with XMLCorpusView(
            self.abspath("luIndex.xml"), "luIndex/lu", self._handle_elt
        ) as view:
            for lu in view:
                self._lu_idx[lu["ID"]] = (
                    lu  # populate with LU index entries. if any of these
                )
                # are looked up they will be replaced by full LU objects.

    def _buildrelationindex(self):
        # print('building relation index...', file=sys.stderr)
        self._freltyp_idx = {}
        self._frel_idx = {}
        self._frel_f_idx = defaultdict(set)
        self._ferel_idx = {}

        with XMLCorpusView(
            self.abspath("frRelation.xml"),
            "frameRelations/frameRelationType",
            self._handle_framerelationtype_elt,
        ) as view:
            for freltyp in view:
                self._freltyp_idx[freltyp.ID] = freltyp
                for frel in freltyp.frameRelations:
                    supF = frel.superFrame = frel[freltyp.superFrameName] = Future(
                        (lambda fID: lambda: self.frame_by_id(fID))(frel.supID)
                    )
                    subF = frel.subFrame = frel[freltyp.subFrameName] = Future(
                        (lambda fID: lambda: self.frame_by_id(fID))(frel.subID)
                    )
                    self._frel_idx[frel.ID] = frel
                    self._frel_f_idx[frel.supID].add(frel.ID)
                    self._frel_f_idx[frel.subID].add(frel.ID)
                    for ferel in frel.feRelations:
                        ferel.superFrame = supF
                        ferel.subFrame = subF
                        ferel.superFE = Future(
                            (lambda fer: lambda: fer.superFrame.FE[fer.superFEName])(
                                ferel
                            )
                        )
                        ferel.subFE = Future(
                            (lambda fer: lambda: fer.subFrame.FE[fer.subFEName])(ferel)
                        )
                        self._ferel_idx[ferel.ID] = ferel
        # print('...done building relation index', file=sys.stderr)

    def _warn(self, *message, **kwargs):
        if self._warnings:
            kwargs.setdefault("file", sys.stderr)
            print(*message, **kwargs)

    def buildindexes(self):
        """
        Build the internal indexes to make look-ups faster.
        """
        # Frames
        self._buildframeindex()
        # LUs
        self._buildluindex()
        # Fulltext annotation corpora index
        self._buildcorpusindex()
        # frame and FE relations
        self._buildrelationindex()

    def doc(self, fn_docid):
        """
        Returns the annotated document whose id number is
        ``fn_docid``. This id number can be obtained by calling the
        Documents() function.

        The dict that is returned from this function will contain the
        following keys:

        - '_type'      : 'fulltextannotation'
        - 'sentence'   : a list of sentences in the document
           - Each item in the list is a dict containing the following keys:
              - 'ID'    : the ID number of the sentence
              - '_type' : 'sentence'
              - 'text'  : the text of the sentence
              - 'paragNo' : the paragraph number
              - 'sentNo'  : the sentence number
              - 'docID'   : the document ID number
              - 'corpID'  : the corpus ID number
              - 'aPos'    : the annotation position
              - 'annotationSet' : a list of annotation layers for the sentence
                 - Each item in the list is a dict containing the following keys:
                    - 'ID'       : the ID number of the annotation set
                    - '_type'    : 'annotationset'
                    - 'status'   : either 'MANUAL' or 'UNANN'
                    - 'luName'   : (only if status is 'MANUAL')
                    - 'luID'     : (only if status is 'MANUAL')
                    - 'frameID'  : (only if status is 'MANUAL')
                    - 'frameName': (only if status is 'MANUAL')
                    - 'layer' : a list of labels for the layer
                       - Each item in the layer is a dict containing the following keys:
                          - '_type': 'layer'
                          - 'rank'
                          - 'name'
                          - 'label' : a list of labels in the layer
                             - Each item is a dict containing the following keys:
                                - 'start'
                                - 'end'
                                - 'name'
                                - 'feID' (optional)

        :param fn_docid: The Framenet id number of the document
        :type fn_docid: int
        :return: Information about the annotated document
        :rtype: dict
        """
        try:
            xmlfname = self._fulltext_idx[fn_docid].filename
        except TypeError:  # happens when self._fulltext_idx == None
            # build the index
            self._buildcorpusindex()
            xmlfname = self._fulltext_idx[fn_docid].filename
        except KeyError as e:  # probably means that fn_docid was not in the index
            raise FramenetError(f"Unknown document id: {fn_docid}") from e

        # construct the path name for the xml file containing the document info
        locpath = os.path.join(f"{self._root}", self._fulltext_dir, xmlfname)

        # Grab the top-level xml element containing the fulltext annotation
        with XMLCorpusView(locpath, "fullTextAnnotation") as view:
            elt = view[0]
        info = self._handle_fulltextannotation_elt(elt)
        # add metadata
        for k, v in self._fulltext_idx[fn_docid].items():
            info[k] = v
        return info

    def frame_by_id(self, fn_fid, ignorekeys=[]):
        """
        Get the details for the specified Frame using the frame's id
        number.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame_by_id(256)
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition # doctest: +NORMALIZE_WHITESPACE
        "This frame includes words that name medical specialties and is closely related to the
        Medical_professionals frame.  The FE Type characterizing a sub-are in a Specialty may also be
        expressed. 'Ralph practices paediatric oncology.'"

        :param fn_fid: The Framenet id number of the frame
        :type fn_fid: int
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict

        Also see the ``frame()`` function for details about what is
        contained in the dict that is returned.
        """

        # get the name of the frame with this id number
        try:
            fentry = self._frame_idx[fn_fid]
            if "_type" in fentry:
                return fentry  # full frame object is cached
            name = fentry["name"]
        except TypeError:
            self._buildframeindex()
            name = self._frame_idx[fn_fid]["name"]
        except KeyError as e:
            raise FramenetError(f"Unknown frame id: {fn_fid}") from e

        return self.frame_by_name(name, ignorekeys, check_cache=False)

    def frame_by_name(self, fn_fname, ignorekeys=[], check_cache=True):
        """
        Get the details for the specified Frame using the frame's name.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame_by_name('Medical_specialties')
        >>> f.ID
        256
        >>> f.name
        'Medical_specialties'
        >>> f.definition # doctest: +NORMALIZE_WHITESPACE
         "This frame includes words that name medical specialties and is closely related to the
          Medical_professionals frame.  The FE Type characterizing a sub-are in a Specialty may also be
          expressed. 'Ralph practices paediatric oncology.'"

        :param fn_fname: The name of the frame
        :type fn_fname: str
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict

        Also see the ``frame()`` function for details about what is
        contained in the dict that is returned.
        """

        if check_cache and fn_fname in self._cached_frames:
            return self._frame_idx[self._cached_frames[fn_fname]]
        elif not self._frame_idx:
            self._buildframeindex()

        # construct the path name for the xml file containing the Frame info
        locpath = os.path.join(f"{self._root}", self._frame_dir, fn_fname + ".xml")
        # print(locpath, file=sys.stderr)
        # Grab the xml for the frame
        try:
            with XMLCorpusView(locpath, "frame") as view:
                elt = view[0]
        except OSError as e:
            raise FramenetError(f"Unknown frame: {fn_fname}") from e

        fentry = self._handle_frame_elt(elt, ignorekeys)
        assert fentry

        fentry.URL = self._fnweb_url + "/" + self._frame_dir + "/" + fn_fname + ".xml"

        # INFERENCE RULE: propagate lexical semtypes from the frame to all its LUs
        for st in fentry.semTypes:
            if st.rootType.name == "Lexical_type":
                for lu in fentry.lexUnit.values():
                    if not any(
                        x is st for x in lu.semTypes
                    ):  # identity containment check
                        lu.semTypes.append(st)

        self._frame_idx[fentry.ID] = fentry
        self._cached_frames[fentry.name] = fentry.ID
        """
        # now set up callables to resolve the LU pointers lazily.
        # (could also do this here--caching avoids infinite recursion.)
        for luName,luinfo in fentry.lexUnit.items():
            fentry.lexUnit[luName] = (lambda luID: Future(lambda: self.lu(luID)))(luinfo.ID)
        """
        return fentry

    def frame(self, fn_fid_or_fname, ignorekeys=[]):
        """
        Get the details for the specified Frame using the frame's name
        or id number.

        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> f = fn.frame(256)
        >>> f.name
        'Medical_specialties'
        >>> f = fn.frame('Medical_specialties')
        >>> f.ID
        256
        >>> # ensure non-ASCII character in definition doesn't trigger an encoding error:
        >>> fn.frame('Imposing_obligation') # doctest: +ELLIPSIS
        frame (1494): Imposing_obligation...


        The dict that is returned from this function will contain the
        following information about the Frame:

        - 'name'       : the name of the Frame (e.g. 'Birth', 'Apply_heat', etc.)
        - 'definition' : textual definition of the Frame
        - 'ID'         : the internal ID number of the Frame
        - 'semTypes'   : a list of semantic types for this frame
           - Each item in the list is a dict containing the following keys:
              - 'name' : can be used with the semtype() function
              - 'ID'   : can be used with the semtype() function

        - 'lexUnit'    : a dict containing all of the LUs for this frame.
                         The keys in this dict are the names of the LUs and
                         the value for each key is itself a dict containing
                         info about the LU (see the lu() function for more info.)

        - 'FE' : a dict containing the Frame Elements that are part of this frame
                 The keys in this dict are the names of the FEs (e.g. 'Body_system')
                 and the values are dicts containing the following keys

              - 'definition' : The definition of the FE
              - 'name'       : The name of the FE e.g. 'Body_system'
              - 'ID'         : The id number
              - '_type'      : 'fe'
              - 'abbrev'     : Abbreviation e.g. 'bod'
              - 'coreType'   : one of "Core", "Peripheral", or "Extra-Thematic"
              - 'semType'    : if not None, a dict with the following two keys:
                 - 'name' : name of the semantic type. can be used with
                            the semtype() function
                 - 'ID'   : id number of the semantic type. can be used with
                            the semtype() function
              - 'requiresFE' : if not None, a dict with the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame
              - 'excludesFE' : if not None, a dict with the following two keys:
                 - 'name' : the name of another FE in this frame
                 - 'ID'   : the id of the other FE in this frame

        - 'frameRelation'      : a list of objects describing frame relations
        - 'FEcoreSets'  : a list of Frame Element core sets for this frame
           - Each item in the list is a list of FE objects

        :param fn_fid_or_fname: The Framenet name or id number of the frame
        :type fn_fid_or_fname: int or str
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: Information about a frame
        :rtype: dict
        """

        # get the frame info by name or id number
        if isinstance(fn_fid_or_fname, str):
            f = self.frame_by_name(fn_fid_or_fname, ignorekeys)
        else:
            f = self.frame_by_id(fn_fid_or_fname, ignorekeys)

        return f

    def frames_by_lemma(self, pat):
        """
        Returns a list of all frames that contain LUs in which the
        ``name`` attribute of the LU matches the given regular expression
        ``pat``. Note that LU names are composed of "lemma.POS", where
        the "lemma" part can be made up of either a single lexeme
        (e.g. 'run') or multiple lexemes (e.g. 'a little').

        Note: if you are going to be doing a lot of this type of
        searching, you'd want to build an index that maps from lemmas to
        frames because each time frames_by_lemma() is called, it has to
        search through ALL of the frame XML files in the db.

        >>> from nltk.corpus import framenet as fn
        >>> from nltk.corpus.reader.framenet import PrettyList
        >>> PrettyList(sorted(fn.frames_by_lemma(r'(?i)a little'), key=itemgetter('ID'))) # doctest: +ELLIPSIS
        [<frame ID=189 name=Quanti...>, <frame ID=2001 name=Degree>]

        :return: A list of frame objects.
        :rtype: list(AttrDict)
        """
        return PrettyList(
            f
            for f in self.frames()
            if any(re.search(pat, luName) for luName in f.lexUnit)
        )

    def lu_basic(self, fn_luid):
        """
        Returns basic information about the LU whose id is
        ``fn_luid``. This is basically just a wrapper around the
        ``lu()`` function with "subCorpus" info excluded.

        >>> from nltk.corpus import framenet as fn
        >>> lu = PrettyDict(fn.lu_basic(256), breakLines=True)
        >>> # ellipses account for differences between FN 1.5 and 1.7
        >>> lu # doctest: +ELLIPSIS
        {'ID': 256,
         'POS': 'V',
         'URL': 'https://framenet2.icsi.berkeley.edu/fnReports/data/lu/lu256.xml',
         '_type': 'lu',
         'cBy': ...,
         'cDate': '02/08/2001 01:27:50 PST Thu',
         'definition': 'COD: be aware of beforehand; predict.',
         'definitionMarkup': 'COD: be aware of beforehand; predict.',
         'frame': <frame ID=26 name=Expectation>,
         'lemmaID': 15082,
         'lexemes': [{'POS': 'V', 'breakBefore': 'false', 'headword': 'false', 'name': 'foresee', 'order': 1}],
         'name': 'foresee.v',
         'semTypes': [],
         'sentenceCount': {'annotated': ..., 'total': ...},
         'status': 'FN1_Sent'}

        :param fn_luid: The id number of the desired LU
        :type fn_luid: int
        :return: Basic information about the lexical unit
        :rtype: dict
        """
        return self.lu(fn_luid, ignorekeys=["subCorpus", "exemplars"])

    def lu(self, fn_luid, ignorekeys=[], luName=None, frameID=None, frameName=None):
        """
        Access a lexical unit by its ID. luName, frameID, and frameName are used
        only in the event that the LU does not have a file in the database
        (which is the case for LUs with "Problem" status); in this case,
        a placeholder LU is created which just contains its name, ID, and frame.


        Usage examples:

        >>> from nltk.corpus import framenet as fn
        >>> fn.lu(256).name
        'foresee.v'
        >>> fn.lu(256).definition
        'COD: be aware of beforehand; predict.'
        >>> fn.lu(256).frame.name
        'Expectation'
        >>> list(map(PrettyDict, fn.lu(256).lexemes))
        [{'POS': 'V', 'breakBefore': 'false', 'headword': 'false', 'name': 'foresee', 'order': 1}]

        >>> fn.lu(227).exemplars[23] # doctest: +NORMALIZE_WHITESPACE
        exemplar sentence (352962):
        [sentNo] 0
        [aPos] 59699508
        <BLANKLINE>
        [LU] (227) guess.v in Coming_to_believe
        <BLANKLINE>
        [frame] (23) Coming_to_believe
        <BLANKLINE>
        [annotationSet] 2 annotation sets
        <BLANKLINE>
        [POS] 18 tags
        <BLANKLINE>
        [POS_tagset] BNC
        <BLANKLINE>
        [GF] 3 relations
        <BLANKLINE>
        [PT] 3 phrases
        <BLANKLINE>
        [Other] 1 entry
        <BLANKLINE>
        [text] + [Target] + [FE]
        <BLANKLINE>
        When he was inside the house , Culley noticed the characteristic
                                                      ------------------
                                                      Content
        <BLANKLINE>
        he would n't have guessed at .
        --                ******* --
        Co                        C1 [Evidence:INI]
         (Co=Cognizer, C1=Content)
        <BLANKLINE>
        <BLANKLINE>

        The dict that is returned from this function will contain most of the
        following information about the LU. Note that some LUs do not contain
        all of these pieces of information - particularly 'totalAnnotated' and
        'incorporatedFE' may be missing in some LUs:

        - 'name'       : the name of the LU (e.g. 'merger.n')
        - 'definition' : textual definition of the LU
        - 'ID'         : the internal ID number of the LU
        - '_type'      : 'lu'
        - 'status'     : e.g. 'Created'
        - 'frame'      : Frame that this LU belongs to
        - 'POS'        : the part of speech of this LU (e.g. 'N')
        - 'totalAnnotated' : total number of examples annotated with this LU
        - 'incorporatedFE' : FE that incorporates this LU (e.g. 'Ailment')
        - 'sentenceCount'  : a dict with the following two keys:
                 - 'annotated': number of sentences annotated with this LU
                 - 'total'    : total number of sentences with this LU

        - 'lexemes'  : a list of dicts describing the lemma of this LU.
           Each dict in the list contains these keys:

           - 'POS'     : part of speech e.g. 'N'
           - 'name'    : either single-lexeme e.g. 'merger' or
                         multi-lexeme e.g. 'a little'
           - 'order': the order of the lexeme in the lemma (starting from 1)
           - 'headword': a boolean ('true' or 'false')
           - 'breakBefore': Can this lexeme be separated from the previous lexeme?
                Consider: "take over.v" as in::

                         Germany took over the Netherlands in 2 days.
                         Germany took the Netherlands over in 2 days.

                In this case, 'breakBefore' would be "true" for the lexeme
                "over". Contrast this with "take after.v" as in::

                         Mary takes after her grandmother.
                        *Mary takes her grandmother after.

                In this case, 'breakBefore' would be "false" for the lexeme "after"

        - 'lemmaID'    : Can be used to connect lemmas in different LUs
        - 'semTypes'   : a list of semantic type objects for this LU
        - 'subCorpus'  : a list of subcorpora
           - Each item in the list is a dict containing the following keys:
              - 'name' :
              - 'sentence' : a list of sentences in the subcorpus
                 - each item in the list is a dict with the following keys:
                    - 'ID':
                    - 'sentNo':
                    - 'text': the text of the sentence
                    - 'aPos':
                    - 'annotationSet': a list of annotation sets
                       - each item in the list is a dict with the following keys:
                          - 'ID':
                          - 'status':
                          - 'layer': a list of layers
                             - each layer is a dict containing the following keys:
                                - 'name': layer name (e.g. 'BNC')
                                - 'rank':
                                - 'label': a list of labels for the layer
                                   - each label is a dict containing the following keys:
                                      - 'start': start pos of label in sentence 'text' (0-based)
                                      - 'end': end pos of label in sentence 'text' (0-based)
                                      - 'name': name of label (e.g. 'NN1')

        Under the hood, this implementation looks up the lexical unit information
        in the *frame* definition file. That file does not contain
        corpus annotations, so the LU files will be accessed on demand if those are
        needed. In principle, valence patterns could be loaded here too,
        though these are not currently supported.

        :param fn_luid: The id number of the lexical unit
        :type fn_luid: int
        :param ignorekeys: The keys to ignore. These keys will not be
            included in the output. (optional)
        :type ignorekeys: list(str)
        :return: All information about the lexical unit
        :rtype: dict
        """
        # look for this LU in cache
        if not self._lu_idx:
            self._buildluindex()
        OOV = object()
        luinfo = self._lu_idx.get(fn_luid, OOV)
        if luinfo is OOV:
            # LU not in the index. We create a placeholder by falling back to
            # luName, frameID, and frameName. However, this will not be listed
            # among the LUs for its frame.
            self._warn(
                "LU ID not found: {} ({}) in {} ({})".format(
                    luName, fn_luid, frameName, frameID
                )
            )
            luinfo = AttrDict(
                {
                    "_type": "lu",
                    "ID": fn_luid,
                    "name": luName,
                    "frameID": frameID,
                    "status": "Problem",
                }
            )
            f = self.frame_by_id(luinfo.frameID)
            assert f.name == frameName, (f.name, frameName)
            luinfo["frame"] = f
            self._lu_idx[fn_luid] = luinfo
        elif "_type" not in luinfo:
            # we only have an index entry for the LU. loading the frame will replace this.
            f = self.frame_by_id(luinfo.frameID)
            luinfo = self._lu_idx[fn_luid]
        if ignorekeys:
            return AttrDict({k: v for k, v in luinfo.items() if k not in ignorekeys})

        return luinfo

    def _lu_file(self, lu, ignorekeys=[]):
        """
        Augment the LU information that was loaded from the frame file
        with additional information from the LU file.
        """
        fn_luid = lu.ID

        fname = f"lu{fn_luid}.xml"
        locpath = os.path.join(f"{self._root}", self._lu_dir, fname)
        # print(locpath, file=sys.stderr)
        if not self._lu_idx:
            self._buildluindex()

        try:
            with XMLCorpusView(locpath, "lexUnit") as view:
                elt = view[0]
        except OSError as e:
            raise FramenetError(f"Unknown LU id: {fn_luid}") from e

        lu2 = self._handle_lexunit_elt(elt, ignorekeys)
        lu.URL = self._fnweb_url + "/" + self._lu_dir + "/" + fname
        lu.subCorpus = lu2.subCorpus
        lu.exemplars = SpecialList(
            "luexemplars", [sent for subc in lu.subCorpus for sent in subc.sentence]
        )
        for sent in lu.exemplars:
            sent["LU"] = lu
            sent["frame"] = lu.frame
            for aset in sent.annotationSet:
                aset["LU"] = lu
                aset["frame"] = lu.frame

        return lu

    def _loadsemtypes(self):
        """Create the semantic types index."""
        self._semtypes = AttrDict()
        with XMLCorpusView(
            self.abspath("semTypes.xml"),
            "semTypes/semType",
            self._handle_semtype_elt,
        ) as view:
            for st in view:
                n = st["name"]
                a = st["abbrev"]
                i = st["ID"]
                # Both name and abbrev should be able to retrieve the
                # ID. The ID will retrieve the semantic type dict itself.
                self._semtypes[n] = i
                self._semtypes[a] = i
                self._semtypes[i] = st
        # now that all individual semtype XML is loaded, we can link them together
        roots = []
        for st in self.semtypes():
            if st.superType:
                st.superType = self.semtype(st.superType.supID)
                st.superType.subTypes.append(st)
            else:
                if st not in roots:
                    roots.append(st)
                st.rootType = st
        queue = list(roots)
        assert queue
        while queue:
            st = queue.pop(0)
            for child in st.subTypes:
                child.rootType = st.rootType
                queue.append(child)
        # self.propagate_semtypes()  # apply inferencing over FE relations

    def propagate_semtypes(self):
        """
        Apply inference rules to distribute semtypes over relations between FEs.
        For FrameNet 1.5, this results in 1011 semtypes being propagated.
        (Not done by default because it requires loading all frame files,
        which takes several seconds. If this needed to be fast, it could be rewritten
        to traverse the neighboring relations on demand for each FE semtype.)

        >>> from nltk.corpus import framenet as fn
        >>> x = sum(1 for f in fn.frames() for fe in f.FE.values() if fe.semType)
        >>> fn.propagate_semtypes()
        >>> y = sum(1 for f in fn.frames() for fe in f.FE.values() if fe.semType)
        >>> y-x > 1000
        True
        """
        if not self._semtypes:
            self._loadsemtypes()
        if not self._ferel_idx:
            self._buildrelationindex()
        changed = True
        i = 0
        nPropagations = 0
        while changed:
            # make a pass and see if anything needs to be propagated
            i += 1
            changed = False
            for ferel in self.fe_relations():
                superST = ferel.superFE.semType
                subST = ferel.subFE.semType
                try:
                    if superST and superST is not subST:
                        # propagate downward
                        assert subST is None or self.semtype_inherits(subST, superST), (
                            superST.name,
                            ferel,
                            subST.name,
                        )
                        if subST is None:
                            ferel.subFE.semType = subST = superST
                            changed = True
                            nPropagations += 1
                    if (
                        ferel.type.name in ["Perspective_on", "Subframe", "Precedes"]
                        and subST
                        and subST is not superST
                    ):
                        # propagate upward
                        assert superST is None, (superST.name, ferel, subST.name)
                        ferel.superFE.semType = superST = subST
                        changed = True
                        nPropagations += 1
                except AssertionError as ex:
                    # bug in the data! ignore
                    # print(ex, file=sys.stderr)
                    continue
            # print(i, nPropagations, file=sys.stderr)

    def semtype(self, key):
        """
        >>> from nltk.corpus import framenet as fn
        >>> fn.semtype(233).name
        'Temperature'
        >>> fn.semtype(233).abbrev
        'Temp'
        >>> fn.semtype('Temperature').ID
        233

        :param key: The name, abbreviation, or id number of the semantic type
        :type key: string or int
        :return: Information about a semantic type
        :rtype: dict
        """
        if isinstance(key, int):
            stid = key
        else:
            try:
                stid = self._semtypes[key]
            except TypeError:
                self._loadsemtypes()
                stid = self._semtypes[key]

        try:
            st = self._semtypes[stid]
        except TypeError:
            self._loadsemtypes()
            st = self._semtypes[stid]

        return st

    def semtype_inherits(self, st, superST):
        if not isinstance(st, dict):
            st = self.semtype(st)
        if not isinstance(superST, dict):
            superST = self.semtype(superST)
        par = st.superType
        while par:
            if par is superST:
                return True
            par = par.superType
        return False

    def frames(self, name=None):
        """
        Obtain details for a specific frame.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.frames()) in (1019, 1221)    # FN 1.5 and 1.7, resp.
        True
        >>> x = PrettyList(fn.frames(r'(?i)crim'), maxReprSize=0, breakLines=True)
        >>> x.sort(key=itemgetter('ID'))
        >>> x
        [<frame ID=200 name=Criminal_process>,
         <frame ID=500 name=Criminal_investigation>,
         <frame ID=692 name=Crime_scenario>,
         <frame ID=700 name=Committing_crime>]

        A brief intro to Frames (excerpted from "FrameNet II: Extended
        Theory and Practice" by Ruppenhofer et. al., 2010):

        A Frame is a script-like conceptual structure that describes a
        particular type of situation, object, or event along with the
        participants and props that are needed for that Frame. For
        example, the "Apply_heat" frame describes a common situation
        involving a Cook, some Food, and a Heating_Instrument, and is
        evoked by words such as bake, blanch, boil, broil, brown,
        simmer, steam, etc.

        We call the roles of a Frame "frame elements" (FEs) and the
        frame-evoking words are called "lexical units" (LUs).

        FrameNet includes relations between Frames. Several types of
        relations are defined, of which the most important are:

           - Inheritance: An IS-A relation. The child frame is a subtype
             of the parent frame, and each FE in the parent is bound to
             a corresponding FE in the child. An example is the
             "Revenge" frame which inherits from the
             "Rewards_and_punishments" frame.

           - Using: The child frame presupposes the parent frame as
             background, e.g the "Speed" frame "uses" (or presupposes)
             the "Motion" frame; however, not all parent FEs need to be
             bound to child FEs.

           - Subframe: The child frame is a subevent of a complex event
             represented by the parent, e.g. the "Criminal_process" frame
             has subframes of "Arrest", "Arraignment", "Trial", and
             "Sentencing".

           - Perspective_on: The child frame provides a particular
             perspective on an un-perspectivized parent frame. A pair of
             examples consists of the "Hiring" and "Get_a_job" frames,
             which perspectivize the "Employment_start" frame from the
             Employer's and the Employee's point of view, respectively.

        :param name: A regular expression pattern used to match against
            Frame names. If 'name' is None, then a list of all
            Framenet Frames will be returned.
        :type name: str
        :return: A list of matching Frames (or all Frames).
        :rtype: list(AttrDict)
        """
        try:
            fIDs = list(self._frame_idx.keys())
        except AttributeError:
            self._buildframeindex()
            fIDs = list(self._frame_idx.keys())

        if name is not None:
            return PrettyList(
                self.frame(fID) for fID, finfo in self.frame_ids_and_names(name).items()
            )
        else:
            return PrettyLazyMap(self.frame, fIDs)

    def frame_ids_and_names(self, name=None):
        """
        Uses the frame index, which is much faster than looking up each frame definition
        if only the names and IDs are needed.
        """
        if not self._frame_idx:
            self._buildframeindex()
        return {
            fID: finfo.name
            for fID, finfo in self._frame_idx.items()
            if name is None or re.search(name, finfo.name) is not None
        }

    def fes(self, name=None, frame=None):
        """
        Lists frame element objects. If 'name' is provided, this is treated as
        a case-insensitive regular expression to filter by frame name.
        (Case-insensitivity is because casing of frame element names is not always
        consistent across frames.) Specify 'frame' to filter by a frame name pattern,
        ID, or object.

        >>> from nltk.corpus import framenet as fn
        >>> fn.fes('Noise_maker')
        [<fe ID=6043 name=Noise_maker>]
        >>> sorted([(fe.frame.name,fe.name) for fe in fn.fes('sound')]) # doctest: +NORMALIZE_WHITESPACE
        [('Cause_to_make_noise', 'Sound_maker'), ('Make_noise', 'Sound'),
         ('Make_noise', 'Sound_source'), ('Sound_movement', 'Location_of_sound_source'),
         ('Sound_movement', 'Sound'), ('Sound_movement', 'Sound_source'),
         ('Sounds', 'Component_sound'), ('Sounds', 'Location_of_sound_source'),
         ('Sounds', 'Sound_source'), ('Vocalizations', 'Location_of_sound_source'),
         ('Vocalizations', 'Sound_source')]
        >>> sorted([(fe.frame.name,fe.name) for fe in fn.fes('sound',r'(?i)make_noise')]) # doctest: +NORMALIZE_WHITESPACE
        [('Cause_to_make_noise', 'Sound_maker'),
         ('Make_noise', 'Sound'),
         ('Make_noise', 'Sound_source')]
        >>> sorted(set(fe.name for fe in fn.fes('^sound')))
        ['Sound', 'Sound_maker', 'Sound_source']
        >>> len(fn.fes('^sound$'))
        2

        :param name: A regular expression pattern used to match against
            frame element names. If 'name' is None, then a list of all
            frame elements will be returned.
        :type name: str
        :return: A list of matching frame elements
        :rtype: list(AttrDict)
        """
        # what frames are we searching in?
        if frame is not None:
            if isinstance(frame, int):
                frames = [self.frame(frame)]
            elif isinstance(frame, str):
                frames = self.frames(frame)
            else:
                frames = [frame]
        else:
            frames = self.frames()

        return PrettyList(
            fe
            for f in frames
            for fename, fe in f.FE.items()
            if name is None or re.search(name, fename, re.I)
        )

    def lus(self, name=None, frame=None):
        """
        Obtain details for lexical units.
        Optionally restrict by lexical unit name pattern, and/or to a certain frame
        or frames whose name matches a pattern.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.lus()) in (11829, 13572) # FN 1.5 and 1.7, resp.
        True
        >>> PrettyList(sorted(fn.lus(r'(?i)a little'), key=itemgetter('ID')), maxReprSize=0, breakLines=True)
        [<lu ID=14733 name=a little.n>,
         <lu ID=14743 name=a little.adv>,
         <lu ID=14744 name=a little bit.adv>]
        >>> PrettyList(sorted(fn.lus(r'interest', r'(?i)stimulus'), key=itemgetter('ID')))
        [<lu ID=14894 name=interested.a>, <lu ID=14920 name=interesting.a>]

        A brief intro to Lexical Units (excerpted from "FrameNet II:
        Extended Theory and Practice" by Ruppenhofer et. al., 2010):

        A lexical unit (LU) is a pairing of a word with a meaning. For
        example, the "Apply_heat" Frame describes a common situation
        involving a Cook, some Food, and a Heating Instrument, and is
        _evoked_ by words such as bake, blanch, boil, broil, brown,
        simmer, steam, etc. These frame-evoking words are the LUs in the
        Apply_heat frame. Each sense of a polysemous word is a different
        LU.

        We have used the word "word" in talking about LUs. The reality
        is actually rather complex. When we say that the word "bake" is
        polysemous, we mean that the lemma "bake.v" (which has the
        word-forms "bake", "bakes", "baked", and "baking") is linked to
        three different frames:

           - Apply_heat: "Michelle baked the potatoes for 45 minutes."

           - Cooking_creation: "Michelle baked her mother a cake for her birthday."

           - Absorb_heat: "The potatoes have to bake for more than 30 minutes."

        These constitute three different LUs, with different
        definitions.

        Multiword expressions such as "given name" and hyphenated words
        like "shut-eye" can also be LUs. Idiomatic phrases such as
        "middle of nowhere" and "give the slip (to)" are also defined as
        LUs in the appropriate frames ("Isolated_places" and "Evading",
        respectively), and their internal structure is not analyzed.

        Framenet provides multiple annotated examples of each sense of a
        word (i.e. each LU).  Moreover, the set of examples
        (approximately 20 per LU) illustrates all of the combinatorial
        possibilities of the lexical unit.

        Each LU is linked to a Frame, and hence to the other words which
        evoke that Frame. This makes the FrameNet database similar to a
        thesaurus, grouping together semantically similar words.

        In the simplest case, frame-evoking words are verbs such as
        "fried" in:

           "Matilde fried the catfish in a heavy iron skillet."

        Sometimes event nouns may evoke a Frame. For example,
        "reduction" evokes "Cause_change_of_scalar_position" in:

           "...the reduction of debt levels to $665 million from $2.6 billion."

        Adjectives may also evoke a Frame. For example, "asleep" may
        evoke the "Sleep" frame as in:

           "They were asleep for hours."

        Many common nouns, such as artifacts like "hat" or "tower",
        typically serve as dependents rather than clearly evoking their
        own frames.

        :param name: A regular expression pattern used to search the LU
            names. Note that LU names take the form of a dotted
            string (e.g. "run.v" or "a little.adv") in which a
            lemma precedes the "." and a POS follows the
            dot. The lemma may be composed of a single lexeme
            (e.g. "run") or of multiple lexemes (e.g. "a
            little"). If 'name' is not given, then all LUs will
            be returned.

            The valid POSes are:

                   v    - verb
                   n    - noun
                   a    - adjective
                   adv  - adverb
                   prep - preposition
                   num  - numbers
                   intj - interjection
                   art  - article
                   c    - conjunction
                   scon - subordinating conjunction

        :type name: str
        :type frame: str or int or frame
        :return: A list of selected (or all) lexical units
        :rtype: list of LU objects (dicts). See the lu() function for info
          about the specifics of LU objects.

        """
        if not self._lu_idx:
            self._buildluindex()

        if name is not None:  # match LUs, then restrict by frame
            result = PrettyList(
                self.lu(luID) for luID, luName in self.lu_ids_and_names(name).items()
            )
            if frame is not None:
                if isinstance(frame, int):
                    frameIDs = {frame}
                elif isinstance(frame, str):
                    frameIDs = {f.ID for f in self.frames(frame)}
                else:
                    frameIDs = {frame.ID}
                result = PrettyList(lu for lu in result if lu.frame.ID in frameIDs)
        elif frame is not None:  # all LUs in matching frames
            if isinstance(frame, int):
                frames = [self.frame(frame)]
            elif isinstance(frame, str):
                frames = self.frames(frame)
            else:
                frames = [frame]
            result = PrettyLazyIteratorList(
                iter(LazyConcatenation(list(f.lexUnit.values()) for f in frames))
            )
        else:  # all LUs
            luIDs = [
                luID
                for luID, lu in self._lu_idx.items()
                if lu.status not in self._bad_statuses
            ]
            result = PrettyLazyMap(self.lu, luIDs)
        return result

    def lu_ids_and_names(self, name=None):
        """
        Uses the LU index, which is much faster than looking up each LU definition
        if only the names and IDs are needed.
        """
        if not self._lu_idx:
            self._buildluindex()
        return {
            luID: luinfo.name
            for luID, luinfo in self._lu_idx.items()
            if luinfo.status not in self._bad_statuses
            and (name is None or re.search(name, luinfo.name) is not None)
        }

    def docs_metadata(self, name=None):
        """
        Return an index of the annotated documents in Framenet.

        Details for a specific annotated document can be obtained using this
        class's doc() function and pass it the value of the 'ID' field.

        >>> from nltk.corpus import framenet as fn
        >>> len(fn.docs()) in (78, 107) # FN 1.5 and 1.7, resp.
        True
        >>> set([x.corpname for x in fn.docs_metadata()])>=set(['ANC', 'KBEval', \
                    'LUCorpus-v0.3', 'Miscellaneous', 'NTI', 'PropBank'])
        True

        :param name: A regular expression pattern used to search the
            file name of each annotated document. The document's
            file name contains the name of the corpus that the
            document is from, followed by two underscores "__"
            followed by the document name. So, for example, the
            file name "LUCorpus-v0.3__20000410_nyt-NEW.xml" is
            from the corpus named "LUCorpus-v0.3" and the
            document name is "20000410_nyt-NEW.xml".
        :type name: str
        :return: A list of selected (or all) annotated documents
        :rtype: list of dicts, where each dict object contains the following
                keys:

                - 'name'
                - 'ID'
                - 'corpid'
                - 'corpname'
                - 'description'
                - 'filename'
        """
        try:
            ftlist = PrettyList(self._fulltext_idx.values())
        except AttributeError:
            self._buildcorpusindex()
            ftlist = PrettyList(self._fulltext_idx.values())

        if name is None:
            return ftlist
        else:
            return PrettyList(
                x for x in ftlist if re.search(name, x["filename"]) is not None
            )

    def docs(self, name=None):
        """
        Return a list of the annotated full-text documents in FrameNet,
        optionally filtered by a regex to be matched against the document name.
        """
        return PrettyLazyMap((lambda x: self.doc(x.ID)), self.docs_metadata(name))

    def sents(self, exemplars=True, full_text=True):
        """
        Annotated sentences matching the specified criteria.
        """
        if exemplars:
            if full_text:
                return self.exemplars() + self.ft_sents()
            else:
                return self.exemplars()
        elif full_text:
            return self.ft_sents()

    def annotations(self, luNamePattern=None, exemplars=True, full_text=True):
        """
        Frame annotation sets matching the specified criteria.
        """

        if exemplars:
            epart = PrettyLazyIteratorList(
                sent.frameAnnotation for sent in self.exemplars(luNamePattern)
            )
        else:
            epart = []

        if full_text:
            if luNamePattern is not None:
                matchedLUIDs = set(self.lu_ids_and_names(luNamePattern).keys())
            ftpart = PrettyLazyIteratorList(
                aset
                for sent in self.ft_sents()
                for aset in sent.annotationSet[1:]
                if luNamePattern is None or aset.get("luID", "CXN_ASET") in matchedLUIDs
            )
        else:
            ftpart = []

        if exemplars:
            if full_text:
                return epart + ftpart
            else:
                return epart
        elif full_text:
            return ftpart

    def exemplars(self, luNamePattern=None, frame=None, fe=None, fe2=None):
        """
        Lexicographic exemplar sentences, optionally filtered by LU name and/or 1-2 FEs that
        are realized overtly. 'frame' may be a name pattern, frame ID, or frame instance.
        'fe' may be a name pattern or FE instance; if specified, 'fe2' may also
        be specified to retrieve sentences with both overt FEs (in either order).
        """
        if fe is None and fe2 is not None:
            raise FramenetError("exemplars(..., fe=None, fe2=<value>) is not allowed")
        elif fe is not None and fe2 is not None:
            if not isinstance(fe2, str):
                if isinstance(fe, str):
                    # fe2 is specific to a particular frame. swap fe and fe2 so fe is always used to determine the frame.
                    fe, fe2 = fe2, fe
                elif fe.frame is not fe2.frame:  # ensure frames match
                    raise FramenetError(
                        "exemplars() call with inconsistent `fe` and `fe2` specification (frames must match)"
                    )
        if frame is None and fe is not None and not isinstance(fe, str):
            frame = fe.frame

        # narrow down to frames matching criteria

        lusByFrame = defaultdict(
            list
        )  # frame name -> matching LUs, if luNamePattern is specified
        if frame is not None or luNamePattern is not None:
            if frame is None or isinstance(frame, str):
                if luNamePattern is not None:
                    frames = set()
                    for lu in self.lus(luNamePattern, frame=frame):
                        frames.add(lu.frame.ID)
                        lusByFrame[lu.frame.name].append(lu)
                    frames = LazyMap(self.frame, list(frames))
                else:
                    frames = self.frames(frame)
            else:
                if isinstance(frame, int):
                    frames = [self.frame(frame)]
                else:  # frame object
                    frames = [frame]

                if luNamePattern is not None:
                    lusByFrame = {frame.name: self.lus(luNamePattern, frame=frame)}

            if fe is not None:  # narrow to frames that define this FE
                if isinstance(fe, str):
                    frames = PrettyLazyIteratorList(
                        f
                        for f in frames
                        if fe in f.FE
                        or any(re.search(fe, ffe, re.I) for ffe in f.FE.keys())
                    )
                else:
                    if fe.frame not in frames:
                        raise FramenetError(
                            "exemplars() call with inconsistent `frame` and `fe` specification"
                        )
                    frames = [fe.frame]

                if fe2 is not None:  # narrow to frames that ALSO define this FE
                    if isinstance(fe2, str):
                        frames = PrettyLazyIteratorList(
                            f
                            for f in frames
                            if fe2 in f.FE
                            or any(re.search(fe2, ffe, re.I) for ffe in f.FE.keys())
                        )
                    # else we already narrowed it to a single frame
        else:  # frame, luNamePattern are None. fe, fe2 are None or strings
            if fe is not None:
                frames = {ffe.frame.ID for ffe in self.fes(fe)}
                if fe2 is not None:
                    frames2 = {ffe.frame.ID for ffe in self.fes(fe2)}
                    frames = frames & frames2
                frames = LazyMap(self.frame, list(frames))
            else:
                frames = self.frames()

        # we've narrowed down 'frames'
        # now get exemplars for relevant LUs in those frames

        def _matching_exs():
            for f in frames:
                fes = fes2 = None  # FEs of interest
                if fe is not None:
                    fes = (
                        {ffe for ffe in f.FE.keys() if re.search(fe, ffe, re.I)}
                        if isinstance(fe, str)
                        else {fe.name}
                    )
                    if fe2 is not None:
                        fes2 = (
                            {ffe for ffe in f.FE.keys() if re.search(fe2, ffe, re.I)}
                            if isinstance(fe2, str)
                            else {fe2.name}
                        )

                for lu in (
                    lusByFrame[f.name]
                    if luNamePattern is not None
                    else f.lexUnit.values()
                ):
                    for ex in lu.exemplars:
                        if (fes is None or self._exemplar_of_fes(ex, fes)) and (
                            fes2 is None or self._exemplar_of_fes(ex, fes2)
                        ):
                            yield ex

        return PrettyLazyIteratorList(_matching_exs())

    def _exemplar_of_fes(self, ex, fes=None):
        """
        Given an exemplar sentence and a set of FE names, return the subset of FE names
        that are realized overtly in the sentence on the FE, FE2, or FE3 layer.

        If 'fes' is None, returns all overt FE names.
        """
        overtNames = set(list(zip(*ex.FE[0]))[2]) if ex.FE[0] else set()
        if "FE2" in ex:
            overtNames |= set(list(zip(*ex.FE2[0]))[2]) if ex.FE2[0] else set()
            if "FE3" in ex:
                overtNames |= set(list(zip(*ex.FE3[0]))[2]) if ex.FE3[0] else set()
        return overtNames & fes if fes is not None else overtNames

    def ft_sents(self, docNamePattern=None):
        """
        Full-text annotation sentences, optionally filtered by document name.
        """
        return PrettyLazyIteratorList(
            sent for d in self.docs(docNamePattern) for sent in d.sentence
        )

    def frame_relation_types(self):
        """
        Obtain a list of frame relation types.

        >>> from nltk.corpus import framenet as fn
        >>> frts = sorted(fn.frame_relation_types(), key=itemgetter('ID'))
        >>> isinstance(frts, list)
        True
        >>> len(frts) in (9, 10)    # FN 1.5 and 1.7, resp.
        True
        >>> PrettyDict(frts[0], breakLines=True)
        {'ID': 1,
         '_type': 'framerelationtype',
         'frameRelations': [<Parent=Event -- Inheritance -> Child=Change_of_consistency>, <Parent=Event -- Inheritance -> Child=Rotting>, ...],
         'name': 'Inheritance',
         'subFrameName': 'Child',
         'superFrameName': 'Parent'}

        :return: A list of all of the frame relation types in framenet
        :rtype: list(dict)
        """
        if not self._freltyp_idx:
            self._buildrelationindex()
        return self._freltyp_idx.values()

    def frame_relations(self, frame=None, frame2=None, type=None):
        """
        :param frame: (optional) frame object, name, or ID; only relations involving
            this frame will be returned
        :param frame2: (optional; 'frame' must be a different frame) only show relations
            between the two specified frames, in either direction
        :param type: (optional) frame relation type (name or object); show only relations
            of this type
        :type frame: int or str or AttrDict
        :return: A list of all of the frame relations in framenet
        :rtype: list(dict)

        >>> from nltk.corpus import framenet as fn
        >>> frels = fn.frame_relations()
        >>> isinstance(frels, list)
        True
        >>> len(frels) in (1676, 2070)  # FN 1.5 and 1.7, resp.
        True
        >>> PrettyList(fn.frame_relations('Cooking_creation'), maxReprSize=0, breakLines=True)
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>,
         <Parent=Apply_heat -- Using -> Child=Cooking_creation>,
         <MainEntry=Apply_heat -- See_also -> ReferringEntry=Cooking_creation>]
        >>> PrettyList(fn.frame_relations(274), breakLines=True)
        [<Parent=Avoiding -- Inheritance -> Child=Dodging>,
         <Parent=Avoiding -- Inheritance -> Child=Evading>, ...]
        >>> PrettyList(fn.frame_relations(fn.frame('Cooking_creation')), breakLines=True)
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>,
         <Parent=Apply_heat -- Using -> Child=Cooking_creation>, ...]
        >>> PrettyList(fn.frame_relations('Cooking_creation', type='Inheritance'))
        [<Parent=Intentionally_create -- Inheritance -> Child=Cooking_creation>]
        >>> PrettyList(fn.frame_relations('Cooking_creation', 'Apply_heat'), breakLines=True) # doctest: +NORMALIZE_WHITESPACE
        [<Parent=Apply_heat -- Using -> Child=Cooking_creation>,
        <MainEntry=Apply_heat -- See_also -> ReferringEntry=Cooking_creation>]
        """
        relation_type = type

        if not self._frel_idx:
            self._buildrelationindex()

        rels = None

        if relation_type is not None:
            if not isinstance(relation_type, dict):
                type = [rt for rt in self.frame_relation_types() if rt.name == type][0]
                assert isinstance(type, dict)

        # lookup by 'frame'
        if frame is not None:
            if isinstance(frame, dict) and "frameRelations" in frame:
                rels = PrettyList(frame.frameRelations)
            else:
                if not isinstance(frame, int):
                    if isinstance(frame, dict):
                        frame = frame.ID
                    else:
                        frame = self.frame_by_name(frame).ID
                rels = [self._frel_idx[frelID] for frelID in self._frel_f_idx[frame]]

            # filter by 'type'
            if type is not None:
                rels = [rel for rel in rels if rel.type is type]
        elif type is not None:
            # lookup by 'type'
            rels = type.frameRelations
        else:
            rels = self._frel_idx.values()

        # filter by 'frame2'
        if frame2 is not None:
            if frame is None:
                raise FramenetError(
                    "frame_relations(frame=None, frame2=<value>) is not allowed"
                )
            if not isinstance(frame2, int):
                if isinstance(frame2, dict):
                    frame2 = frame2.ID
                else:
                    frame2 = self.frame_by_name(frame2).ID
            if frame == frame2:
                raise FramenetError(
                    "The two frame arguments to frame_relations() must be different frames"
                )
            rels = [
                rel
                for rel in rels
                if rel.superFrame.ID == frame2 or rel.subFrame.ID == frame2
            ]

        return PrettyList(
            sorted(
                rels,
                key=lambda frel: (frel.type.ID, frel.superFrameName, frel.subFrameName),
            )
        )

    def fe_relations(self):
        """
        Obtain a list of frame element relations.

        >>> from nltk.corpus import framenet as fn
        >>> ferels = fn.fe_relations()
        >>> isinstance(ferels, list)
        True
        >>> len(ferels) in (10020, 12393)   # FN 1.5 and 1.7, resp.
        True
        >>> PrettyDict(ferels[0], breakLines=True) # doctest: +NORMALIZE_WHITESPACE
        {'ID': 14642,
        '_type': 'ferelation',
        'frameRelation': <Parent=Abounding_with -- Inheritance -> Child=Lively_place>,
        'subFE': <fe ID=11370 name=Degree>,
        'subFEName': 'Degree',
        'subFrame': <frame ID=1904 name=Lively_place>,
        'subID': 11370,
        'supID': 2271,
        'superFE': <fe ID=2271 name=Degree>,
        'superFEName': 'Degree',
        'superFrame': <frame ID=262 name=Abounding_with>,
        'type': <framerelationtype ID=1 name=Inheritance>}

        :return: A list of all of the frame element relations in framenet
        :rtype: list(dict)
        """
        if not self._ferel_idx:
            self._buildrelationindex()
        return PrettyList(
            sorted(
                self._ferel_idx.values(),
                key=lambda ferel: (
                    ferel.type.ID,
                    ferel.frameRelation.superFrameName,
                    ferel.superFEName,
                    ferel.frameRelation.subFrameName,
                    ferel.subFEName,
                ),
            )
        )

    def semtypes(self):
        """
        Obtain a list of semantic types.

        >>> from nltk.corpus import framenet as fn
        >>> stypes = fn.semtypes()
        >>> len(stypes) in (73, 109) # FN 1.5 and 1.7, resp.
        True
        >>> sorted(stypes[0].keys())
        ['ID', '_type', 'abbrev', 'definition', 'definitionMarkup', 'name', 'rootType', 'subTypes', 'superType']

        :return: A list of all of the semantic types in framenet
        :rtype: list(dict)
        """
        if not self._semtypes:
            self._loadsemtypes()
        return PrettyList(
            self._semtypes[i] for i in self._semtypes if isinstance(i, int)
        )

    def _load_xml_attributes(self, d, elt):
        """
        Extracts a subset of the attributes from the given element and
        returns them in a dictionary.

        :param d: A dictionary in which to store the attributes.
        :type d: dict
        :param elt: An ElementTree Element
        :type elt: Element
        :return: Returns the input dict ``d`` possibly including attributes from ``elt``
        :rtype: dict
        """

        d = type(d)(d)

        try:
            attr_dict = elt.attrib
        except AttributeError:
            return d

        if attr_dict is None:
            return d

        # Ignore these attributes when loading attributes from an xml node
        ignore_attrs = [  #'cBy', 'cDate', 'mDate', # <-- annotation metadata that could be of interest
            "xsi",
            "schemaLocation",
            "xmlns",
            "bgColor",
            "fgColor",
        ]

        for attr in attr_dict:
            if any(attr.endswith(x) for x in ignore_attrs):
                continue

            val = attr_dict[attr]
            if val.isdigit():
                d[attr] = int(val)
            else:
                d[attr] = val

        return d

    def _strip_tags(self, data):
        """
        Gets rid of all tags and newline characters from the given input

        :return: A cleaned-up version of the input string
        :rtype: str
        """

        try:
            r"""
            # Look for boundary issues in markup. (Sometimes FEs are pluralized in definitions.)
            m = re.search(r'\w[<][^/]|[<][/][^>]+[>](s\w|[a-rt-z0-9])', data)
            if m:
                print('Markup boundary:', data[max(0,m.start(0)-10):m.end(0)+10].replace('\n',' '), file=sys.stderr)
            """

            data = data.replace("<t>", "")
            data = data.replace("</t>", "")
            data = re.sub('<fex name="[^"]+">', "", data)
            data = data.replace("</fex>", "")
            data = data.replace("<fen>", "")
            data = data.replace("</fen>", "")
            data = data.replace("<m>", "")
            data = data.replace("</m>", "")
            data = data.replace("<ment>", "")
            data = data.replace("</ment>", "")
            data = data.replace("<ex>", "'")
            data = data.replace("</ex>", "'")
            data = data.replace("<gov>", "")
            data = data.replace("</gov>", "")
            data = data.replace("<x>", "")
            data = data.replace("</x>", "")

            # Get rid of <def-root> and </def-root> tags
            data = data.replace("<def-root>", "")
            data = data.replace("</def-root>", "")

            data = data.replace("\n", " ")
        except AttributeError:
            pass

        return data

    def _handle_elt(self, elt, tagspec=None):
        """Extracts and returns the attributes of the given element"""
        return self._load_xml_attributes(AttrDict(), elt)

    def _handle_fulltextindex_elt(self, elt, tagspec=None):
        """
        Extracts corpus/document info from the fulltextIndex.xml file.

        Note that this function "flattens" the information contained
        in each of the "corpus" elements, so that each "document"
        element will contain attributes for the corpus and
        corpusid. Also, each of the "document" items will contain a
        new attribute called "filename" that is the base file name of
        the xml file for the document in the "fulltext" subdir of the
        Framenet corpus.
        """
        ftinfo = self._load_xml_attributes(AttrDict(), elt)
        corpname = ftinfo.name
        corpid = ftinfo.ID
        retlist = []
        for sub in elt:
            if sub.tag.endswith("document"):
                doc = self._load_xml_attributes(AttrDict(), sub)
                if "name" in doc:
                    docname = doc.name
                else:
                    docname = doc.description
                doc.filename = f"{corpname}__{docname}.xml"
                doc.URL = (
                    self._fnweb_url + "/" + self._fulltext_dir + "/" + doc.filename
                )
                doc.corpname = corpname
                doc.corpid = corpid
                retlist.append(doc)

        return retlist

    def _handle_frame_elt(self, elt, ignorekeys=[]):
        """Load the info for a Frame from a frame xml file"""
        frinfo = self._load_xml_attributes(AttrDict(), elt)

        frinfo["_type"] = "frame"
        frinfo["definition"] = ""
        frinfo["definitionMarkup"] = ""
        frinfo["FE"] = PrettyDict()
        frinfo["FEcoreSets"] = []
        frinfo["lexUnit"] = PrettyDict()
        frinfo["semTypes"] = []
        for k in ignorekeys:
            if k in frinfo:
                del frinfo[k]

        for sub in elt:
            if sub.tag.endswith("definition") and "definition" not in ignorekeys:
                frinfo["definitionMarkup"] = sub.text
                frinfo["definition"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("FE") and "FE" not in ignorekeys:
                feinfo = self._handle_fe_elt(sub)
                frinfo["FE"][feinfo.name] = feinfo
                feinfo["frame"] = frinfo  # backpointer
            elif sub.tag.endswith("FEcoreSet") and "FEcoreSet" not in ignorekeys:
                coreset = self._handle_fecoreset_elt(sub)
                # assumes all FEs have been loaded before coresets
                frinfo["FEcoreSets"].append(
                    PrettyList(frinfo["FE"][fe.name] for fe in coreset)
                )
            elif sub.tag.endswith("lexUnit") and "lexUnit" not in ignorekeys:
                luentry = self._handle_framelexunit_elt(sub)
                if luentry["status"] in self._bad_statuses:
                    # problematic LU entry; ignore it
                    continue
                luentry["frame"] = frinfo
                luentry["URL"] = (
                    self._fnweb_url
                    + "/"
                    + self._lu_dir
                    + "/"
                    + "lu{}.xml".format(luentry["ID"])
                )
                luentry["subCorpus"] = Future(
                    (lambda lu: lambda: self._lu_file(lu).subCorpus)(luentry)
                )
                luentry["exemplars"] = Future(
                    (lambda lu: lambda: self._lu_file(lu).exemplars)(luentry)
                )
                frinfo["lexUnit"][luentry.name] = luentry
                if not self._lu_idx:
                    self._buildluindex()
                self._lu_idx[luentry.ID] = luentry
            elif sub.tag.endswith("semType") and "semTypes" not in ignorekeys:
                semtypeinfo = self._load_xml_attributes(AttrDict(), sub)
                frinfo["semTypes"].append(self.semtype(semtypeinfo.ID))

        frinfo["frameRelations"] = self.frame_relations(frame=frinfo)

        # resolve 'requires' and 'excludes' links between FEs of this frame
        for fe in frinfo.FE.values():
            if fe.requiresFE:
                name, ID = fe.requiresFE.name, fe.requiresFE.ID
                fe.requiresFE = frinfo.FE[name]
                assert fe.requiresFE.ID == ID
            if fe.excludesFE:
                name, ID = fe.excludesFE.name, fe.excludesFE.ID
                fe.excludesFE = frinfo.FE[name]
                assert fe.excludesFE.ID == ID

        return frinfo

    def _handle_fecoreset_elt(self, elt):
        """Load fe coreset info from xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        tmp = []
        for sub in elt:
            tmp.append(self._load_xml_attributes(AttrDict(), sub))

        return tmp

    def _handle_framerelationtype_elt(self, elt, *args):
        """Load frame-relation element and its child fe-relation elements from frRelation.xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info["_type"] = "framerelationtype"
        info["frameRelations"] = PrettyList()

        for sub in elt:
            if sub.tag.endswith("frameRelation"):
                frel = self._handle_framerelation_elt(sub)
                frel["type"] = info  # backpointer
                for ferel in frel.feRelations:
                    ferel["type"] = info
                info["frameRelations"].append(frel)

        return info

    def _handle_framerelation_elt(self, elt):
        """Load frame-relation element and its child fe-relation elements from frRelation.xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        assert info["superFrameName"] != info["subFrameName"], (elt, info)
        info["_type"] = "framerelation"
        info["feRelations"] = PrettyList()

        for sub in elt:
            if sub.tag.endswith("FERelation"):
                ferel = self._handle_elt(sub)
                ferel["_type"] = "ferelation"
                ferel["frameRelation"] = info  # backpointer
                info["feRelations"].append(ferel)

        return info

    def _handle_fulltextannotation_elt(self, elt):
        """Load full annotation info for a document from its xml
        file. The main element (fullTextAnnotation) contains a 'header'
        element (which we ignore here) and a bunch of 'sentence'
        elements."""
        info = AttrDict()
        info["_type"] = "fulltext_annotation"
        info["sentence"] = []

        for sub in elt:
            if sub.tag.endswith("header"):
                continue  # not used
            elif sub.tag.endswith("sentence"):
                s = self._handle_fulltext_sentence_elt(sub)
                s.doc = info
                info["sentence"].append(s)

        return info

    def _handle_fulltext_sentence_elt(self, elt):
        """Load information from the given 'sentence' element. Each
        'sentence' element contains a "text" and "annotationSet" sub
        elements."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info["_type"] = "fulltext_sentence"
        info["annotationSet"] = []
        info["targets"] = []
        target_spans = set()
        info["_ascii"] = types.MethodType(
            _annotation_ascii, info
        )  # attach a method for this instance
        info["text"] = ""

        for sub in elt:
            if sub.tag.endswith("text"):
                info["text"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("annotationSet"):
                a = self._handle_fulltextannotationset_elt(
                    sub, is_pos=(len(info["annotationSet"]) == 0)
                )
                if "cxnID" in a:  # ignoring construction annotations for now
                    continue
                a.sent = info
                a.text = info.text
                info["annotationSet"].append(a)
                if "Target" in a:
                    for tspan in a.Target:
                        if tspan in target_spans:
                            self._warn(
                                'Duplicate target span "{}"'.format(
                                    info.text[slice(*tspan)]
                                ),
                                tspan,
                                "in sentence",
                                info["ID"],
                                info.text,
                            )
                            # this can happen in cases like "chemical and biological weapons"
                            # being annotated as "chemical weapons" and "biological weapons"
                        else:
                            target_spans.add(tspan)
                    info["targets"].append((a.Target, a.luName, a.frameName))

        assert info["annotationSet"][0].status == "UNANN"
        info["POS"] = info["annotationSet"][0].POS
        info["POS_tagset"] = info["annotationSet"][0].POS_tagset
        return info

    def _handle_fulltextannotationset_elt(self, elt, is_pos=False):
        """Load information from the given 'annotationSet' element. Each
        'annotationSet' contains several "layer" elements."""

        info = self._handle_luannotationset_elt(elt, is_pos=is_pos)
        if not is_pos:
            info["_type"] = "fulltext_annotationset"
            if "cxnID" not in info:  # ignoring construction annotations for now
                info["LU"] = self.lu(
                    info.luID,
                    luName=info.luName,
                    frameID=info.frameID,
                    frameName=info.frameName,
                )
                info["frame"] = info.LU.frame
        return info

    def _handle_fulltextlayer_elt(self, elt):
        """Load information from the given 'layer' element. Each
        'layer' contains several "label" elements."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info["_type"] = "layer"
        info["label"] = []

        for sub in elt:
            if sub.tag.endswith("label"):
                l = self._load_xml_attributes(AttrDict(), sub)
                info["label"].append(l)

        return info

    def _handle_framelexunit_elt(self, elt):
        """Load the lexical unit info from an xml element in a frame's xml file."""
        luinfo = AttrDict()
        luinfo["_type"] = "lu"
        luinfo = self._load_xml_attributes(luinfo, elt)
        luinfo["definition"] = ""
        luinfo["definitionMarkup"] = ""
        luinfo["sentenceCount"] = PrettyDict()
        luinfo["lexemes"] = PrettyList()  # multiword LUs have multiple lexemes
        luinfo["semTypes"] = PrettyList()  # an LU can have multiple semtypes

        for sub in elt:
            if sub.tag.endswith("definition"):
                luinfo["definitionMarkup"] = sub.text
                luinfo["definition"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("sentenceCount"):
                luinfo["sentenceCount"] = self._load_xml_attributes(PrettyDict(), sub)
            elif sub.tag.endswith("lexeme"):
                lexemeinfo = self._load_xml_attributes(PrettyDict(), sub)
                if not isinstance(lexemeinfo.name, str):
                    # some lexeme names are ints by default: e.g.,
                    # thousand.num has lexeme with name="1000"
                    lexemeinfo.name = str(lexemeinfo.name)
                luinfo["lexemes"].append(lexemeinfo)
            elif sub.tag.endswith("semType"):
                semtypeinfo = self._load_xml_attributes(PrettyDict(), sub)
                luinfo["semTypes"].append(self.semtype(semtypeinfo.ID))

        # sort lexemes by 'order' attribute
        # otherwise, e.g., 'write down.v' may have lexemes in wrong order
        luinfo["lexemes"].sort(key=lambda x: x.order)

        return luinfo

    def _handle_lexunit_elt(self, elt, ignorekeys):
        """
        Load full info for a lexical unit from its xml file.
        This should only be called when accessing corpus annotations
        (which are not included in frame files).
        """
        luinfo = self._load_xml_attributes(AttrDict(), elt)
        luinfo["_type"] = "lu"
        luinfo["definition"] = ""
        luinfo["definitionMarkup"] = ""
        luinfo["subCorpus"] = PrettyList()
        luinfo["lexemes"] = PrettyList()  # multiword LUs have multiple lexemes
        luinfo["semTypes"] = PrettyList()  # an LU can have multiple semtypes
        for k in ignorekeys:
            if k in luinfo:
                del luinfo[k]

        for sub in elt:
            if sub.tag.endswith("header"):
                continue  # not used
            elif sub.tag.endswith("valences"):
                continue  # not used
            elif sub.tag.endswith("definition") and "definition" not in ignorekeys:
                luinfo["definitionMarkup"] = sub.text
                luinfo["definition"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("subCorpus") and "subCorpus" not in ignorekeys:
                sc = self._handle_lusubcorpus_elt(sub)
                if sc is not None:
                    luinfo["subCorpus"].append(sc)
            elif sub.tag.endswith("lexeme") and "lexeme" not in ignorekeys:
                luinfo["lexemes"].append(self._load_xml_attributes(PrettyDict(), sub))
            elif sub.tag.endswith("semType") and "semType" not in ignorekeys:
                semtypeinfo = self._load_xml_attributes(AttrDict(), sub)
                luinfo["semTypes"].append(self.semtype(semtypeinfo.ID))

        return luinfo

    def _handle_lusubcorpus_elt(self, elt):
        """Load a subcorpus of a lexical unit from the given xml."""
        sc = AttrDict()
        try:
            sc["name"] = elt.get("name")
        except AttributeError:
            return None
        sc["_type"] = "lusubcorpus"
        sc["sentence"] = []

        for sub in elt:
            if sub.tag.endswith("sentence"):
                s = self._handle_lusentence_elt(sub)
                if s is not None:
                    sc["sentence"].append(s)

        return sc

    def _handle_lusentence_elt(self, elt):
        """Load a sentence from a subcorpus of an LU from xml."""
        info = self._load_xml_attributes(AttrDict(), elt)
        info["_type"] = "lusentence"
        info["annotationSet"] = []
        info["_ascii"] = types.MethodType(
            _annotation_ascii, info
        )  # attach a method for this instance
        for sub in elt:
            if sub.tag.endswith("text"):
                info["text"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("annotationSet"):
                annset = self._handle_luannotationset_elt(
                    sub, is_pos=(len(info["annotationSet"]) == 0)
                )
                if annset is not None:
                    assert annset.status == "UNANN" or "FE" in annset, annset
                    if annset.status != "UNANN":
                        info["frameAnnotation"] = annset
                    # copy layer info up to current level
                    for k in (
                        "Target",
                        "FE",
                        "FE2",
                        "FE3",
                        "GF",
                        "PT",
                        "POS",
                        "POS_tagset",
                        "Other",
                        "Sent",
                        "Verb",
                        "Noun",
                        "Adj",
                        "Adv",
                        "Prep",
                        "Scon",
                        "Art",
                    ):
                        if k in annset:
                            info[k] = annset[k]
                    info["annotationSet"].append(annset)
                    annset["sent"] = info
                    annset["text"] = info.text
        return info

    def _handle_luannotationset_elt(self, elt, is_pos=False):
        """Load an annotation set from a sentence in an subcorpus of an LU"""
        info = self._load_xml_attributes(AttrDict(), elt)
        info["_type"] = "posannotationset" if is_pos else "luannotationset"
        info["layer"] = []
        info["_ascii"] = types.MethodType(
            _annotation_ascii, info
        )  # attach a method for this instance

        if "cxnID" in info:  # ignoring construction annotations for now.
            return info

        for sub in elt:
            if sub.tag.endswith("layer"):
                l = self._handle_lulayer_elt(sub)
                if l is not None:
                    overt = []
                    ni = {}  # null instantiations

                    info["layer"].append(l)
                    for lbl in l.label:
                        if "start" in lbl:
                            thespan = (lbl.start, lbl.end + 1, lbl.name)
                            if l.name not in (
                                "Sent",
                                "Other",
                            ):  # 'Sent' and 'Other' layers sometimes contain accidental duplicate spans
                                assert thespan not in overt, (info.ID, l.name, thespan)
                            overt.append(thespan)
                        else:  # null instantiation
                            if lbl.name in ni:
                                self._warn(
                                    "FE with multiple NI entries:",
                                    lbl.name,
                                    ni[lbl.name],
                                    lbl.itype,
                                )
                            else:
                                ni[lbl.name] = lbl.itype
                    overt = sorted(overt)

                    if l.name == "Target":
                        if not overt:
                            self._warn(
                                "Skipping empty Target layer in annotation set ID={}".format(
                                    info.ID
                                )
                            )
                            continue
                        assert all(lblname == "Target" for i, j, lblname in overt)
                        if "Target" in info:
                            self._warn(
                                "Annotation set {} has multiple Target layers".format(
                                    info.ID
                                )
                            )
                        else:
                            info["Target"] = [(i, j) for (i, j, _) in overt]
                    elif l.name == "FE":
                        if l.rank == 1:
                            assert "FE" not in info
                            info["FE"] = (overt, ni)
                            # assert False,info
                        else:
                            # sometimes there are 3 FE layers! e.g. Change_position_on_a_scale.fall.v
                            assert 2 <= l.rank <= 3, l.rank
                            k = "FE" + str(l.rank)
                            assert k not in info
                            info[k] = (overt, ni)
                    elif l.name in ("GF", "PT"):
                        assert l.rank == 1
                        info[l.name] = overt
                    elif l.name in ("BNC", "PENN"):
                        assert l.rank == 1
                        info["POS"] = overt
                        info["POS_tagset"] = l.name
                    else:
                        if is_pos:
                            if l.name not in ("NER", "WSL"):
                                self._warn(
                                    "Unexpected layer in sentence annotationset:",
                                    l.name,
                                )
                        else:
                            if l.name not in (
                                "Sent",
                                "Verb",
                                "Noun",
                                "Adj",
                                "Adv",
                                "Prep",
                                "Scon",
                                "Art",
                                "Other",
                            ):
                                self._warn(
                                    "Unexpected layer in frame annotationset:", l.name
                                )
                        info[l.name] = overt
        if not is_pos and "cxnID" not in info:
            if "Target" not in info:
                self._warn(f"Missing target in annotation set ID={info.ID}")
            assert "FE" in info
            if "FE3" in info:
                assert "FE2" in info

        return info

    def _handle_lulayer_elt(self, elt):
        """Load a layer from an annotation set"""
        layer = self._load_xml_attributes(AttrDict(), elt)
        layer["_type"] = "lulayer"
        layer["label"] = []

        for sub in elt:
            if sub.tag.endswith("label"):
                l = self._load_xml_attributes(AttrDict(), sub)
                if l is not None:
                    layer["label"].append(l)
        return layer

    def _handle_fe_elt(self, elt):
        feinfo = self._load_xml_attributes(AttrDict(), elt)
        feinfo["_type"] = "fe"
        feinfo["definition"] = ""
        feinfo["definitionMarkup"] = ""
        feinfo["semType"] = None
        feinfo["requiresFE"] = None
        feinfo["excludesFE"] = None
        for sub in elt:
            if sub.tag.endswith("definition"):
                feinfo["definitionMarkup"] = sub.text
                feinfo["definition"] = self._strip_tags(sub.text)
            elif sub.tag.endswith("semType"):
                stinfo = self._load_xml_attributes(AttrDict(), sub)
                feinfo["semType"] = self.semtype(stinfo.ID)
            elif sub.tag.endswith("requiresFE"):
                feinfo["requiresFE"] = self._load_xml_attributes(AttrDict(), sub)
            elif sub.tag.endswith("excludesFE"):
                feinfo["excludesFE"] = self._load_xml_attributes(AttrDict(), sub)

        return feinfo

    def _handle_semtype_elt(self, elt, tagspec=None):
        semt = self._load_xml_attributes(AttrDict(), elt)
        semt["_type"] = "semtype"
        semt["superType"] = None
        semt["subTypes"] = PrettyList()
        for sub in elt:
            if sub.text is not None:
                semt["definitionMarkup"] = sub.text
                semt["definition"] = self._strip_tags(sub.text)
            else:
                supertypeinfo = self._load_xml_attributes(AttrDict(), sub)
                semt["superType"] = supertypeinfo
                # the supertype may not have been loaded yet

        return semt


#
# Demo
#
def demo():
    from nltk.corpus import framenet as fn

    #
    # It is not necessary to explicitly build the indexes by calling
    # buildindexes(). We do this here just for demo purposes. If the
    # indexes are not built explicitly, they will be built as needed.
    #
    print("Building the indexes...")
    fn.buildindexes()

    #
    # Get some statistics about the corpus
    #
    print("Number of Frames:", len(fn.frames()))
    print("Number of Lexical Units:", len(fn.lus()))
    print("Number of annotated documents:", len(fn.docs()))
    print()

    #
    # Frames
    #
    print(
        'getting frames whose name matches the (case insensitive) regex: "(?i)medical"'
    )
    medframes = fn.frames(r"(?i)medical")
    print(f'Found {len(medframes)} Frames whose name matches "(?i)medical":')
    print([(f.name, f.ID) for f in medframes])

    #
    # store the first frame in the list of frames
    #
    tmp_id = medframes[0].ID
    m_frame = fn.frame(tmp_id)  # reads all info for the frame

    #
    # get the frame relations
    #
    print(
        '\nNumber of frame relations for the "{}" ({}) frame:'.format(
            m_frame.name, m_frame.ID
        ),
        len(m_frame.frameRelations),
    )
    for fr in m_frame.frameRelations:
        print("   ", fr)

    #
    # get the names of the Frame Elements
    #
    print(
        f'\nNumber of Frame Elements in the "{m_frame.name}" frame:',
        len(m_frame.FE),
    )
    print("   ", [x for x in m_frame.FE])

    #
    # get the names of the "Core" Frame Elements
    #
    print(f'\nThe "core" Frame Elements in the "{m_frame.name}" frame:')
    print("   ", [x.name for x in m_frame.FE.values() if x.coreType == "Core"])

    #
    # get all of the Lexical Units that are incorporated in the
    # 'Ailment' FE of the 'Medical_conditions' frame (id=239)
    #
    print('\nAll Lexical Units that are incorporated in the "Ailment" FE:')
    m_frame = fn.frame(239)
    ailment_lus = [
        x
        for x in m_frame.lexUnit.values()
        if "incorporatedFE" in x and x.incorporatedFE == "Ailment"
    ]
    print("   ", [x.name for x in ailment_lus])

    #
    # get all of the Lexical Units for the frame
    #
    print(
        f'\nNumber of Lexical Units in the "{m_frame.name}" frame:',
        len(m_frame.lexUnit),
    )
    print("  ", [x.name for x in m_frame.lexUnit.values()][:5], "...")

    #
    # get basic info on the second LU in the frame
    #
    tmp_id = m_frame.lexUnit["ailment.n"].ID  # grab the id of the specified LU
    luinfo = fn.lu_basic(tmp_id)  # get basic info on the LU
    print(f"\nInformation on the LU: {luinfo.name}")
    pprint(luinfo)

    #
    # Get a list of all of the corpora used for fulltext annotation
    #
    print("\nNames of all of the corpora used for fulltext annotation:")
    allcorpora = {x.corpname for x in fn.docs_metadata()}
    pprint(list(allcorpora))

    #
    # Get the names of the annotated documents in the first corpus
    #
    firstcorp = list(allcorpora)[0]
    firstcorp_docs = fn.docs(firstcorp)
    print(f'\nNames of the annotated documents in the "{firstcorp}" corpus:')
    pprint([x.filename for x in firstcorp_docs])

    #
    # Search for frames containing LUs whose name attribute matches a
    # regexp pattern.
    #
    # Note: if you were going to be doing a lot of this type of
    #       searching, you'd want to build an index that maps from
    #       lemmas to frames because each time frames_by_lemma() is
    #       called, it has to search through ALL of the frame XML files
    #       in the db.
    print(
        '\nSearching for all Frames that have a lemma that matches the regexp: "^run.v$":'
    )
    pprint(fn.frames_by_lemma(r"^run.v$"))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\tornado\test\web_test.py ===
from tornado.concurrent import Future
from tornado import gen
from tornado.escape import (
    json_decode,
    utf8,
    to_unicode,
    recursive_unicode,
    native_str,
    to_basestring,
)
from tornado.httpclient import HTTPClientError
from tornado.httputil import format_timestamp
from tornado.iostream import IOStream
from tornado import locale
from tornado.locks import Event
from tornado.log import app_log, gen_log
from tornado.simple_httpclient import SimpleAsyncHTTPClient
from tornado.template import DictLoader
from tornado.testing import AsyncHTTPTestCase, AsyncTestCase, ExpectLog, gen_test
from tornado.test.util import ignore_deprecation
from tornado.util import ObjectDict, unicode_type
from tornado.web import (
    Application,
    RequestHandler,
    StaticFileHandler,
    RedirectHandler as WebRedirectHandler,
    HTTPError,
    MissingArgumentError,
    ErrorHandler,
    authenticated,
    url,
    _create_signature_v1,
    create_signed_value,
    decode_signed_value,
    get_signature_key_version,
    UIModule,
    Finish,
    stream_request_body,
    removeslash,
    addslash,
    GZipContentEncoding,
)

import binascii
import contextlib
import copy
import datetime
import email.utils
import gzip
from io import BytesIO
import itertools
import logging
import os
import re
import socket
import typing  # noqa: F401
import unittest
import urllib.parse


def relpath(*a):
    return os.path.join(os.path.dirname(__file__), *a)


class WebTestCase(AsyncHTTPTestCase):
    """Base class for web tests that also supports WSGI mode.

    Override get_handlers and get_app_kwargs instead of get_app.
    This class is deprecated since WSGI mode is no longer supported.
    """

    def get_app(self):
        self.app = Application(self.get_handlers(), **self.get_app_kwargs())
        return self.app

    def get_handlers(self):
        raise NotImplementedError()

    def get_app_kwargs(self):
        return {}


class SimpleHandlerTestCase(WebTestCase):
    """Simplified base class for tests that work with a single handler class.

    To use, define a nested class named ``Handler``.
    """

    Handler = None

    def get_handlers(self):
        return [("/", self.Handler)]


class HelloHandler(RequestHandler):
    def get(self):
        self.write("hello")


class CookieTestRequestHandler(RequestHandler):
    # stub out enough methods to make the signed_cookie functions work
    def __init__(self, cookie_secret="0123456789", key_version=None):
        # don't call super.__init__
        self._cookies = {}  # type: typing.Dict[str, bytes]
        if key_version is None:
            self.application = ObjectDict(  # type: ignore
                settings=dict(cookie_secret=cookie_secret)
            )
        else:
            self.application = ObjectDict(  # type: ignore
                settings=dict(cookie_secret=cookie_secret, key_version=key_version)
            )

    def get_cookie(self, name):
        return self._cookies.get(name)

    def set_cookie(self, name, value, expires_days=None):
        self._cookies[name] = value


# See SignedValueTest below for more.
class SecureCookieV1Test(unittest.TestCase):
    def test_round_trip(self):
        handler = CookieTestRequestHandler()
        handler.set_signed_cookie("foo", b"bar", version=1)
        self.assertEqual(handler.get_signed_cookie("foo", min_version=1), b"bar")

    def test_cookie_tampering_future_timestamp(self):
        handler = CookieTestRequestHandler()
        # this string base64-encodes to '12345678'
        handler.set_signed_cookie("foo", binascii.a2b_hex(b"d76df8e7aefc"), version=1)
        cookie = handler._cookies["foo"]
        match = re.match(rb"12345678\|([0-9]+)\|([0-9a-f]+)", cookie)
        self.assertIsNotNone(match)
        assert match is not None  # for mypy
        timestamp = match.group(1)
        sig = match.group(2)
        self.assertEqual(
            _create_signature_v1(
                handler.application.settings["cookie_secret"],
                "foo",
                "12345678",
                timestamp,
            ),
            sig,
        )
        # shifting digits from payload to timestamp doesn't alter signature
        # (this is not desirable behavior, just confirming that that's how it
        # works)
        self.assertEqual(
            _create_signature_v1(
                handler.application.settings["cookie_secret"],
                "foo",
                "1234",
                b"5678" + timestamp,
            ),
            sig,
        )
        # tamper with the cookie
        handler._cookies["foo"] = utf8(
            f"1234|5678{to_basestring(timestamp)}|{to_basestring(sig)}"
        )
        # it gets rejected
        with ExpectLog(gen_log, "Cookie timestamp in future"):
            self.assertIsNone(handler.get_signed_cookie("foo", min_version=1))

    def test_arbitrary_bytes(self):
        # Secure cookies accept arbitrary data (which is base64 encoded).
        # Note that normal cookies accept only a subset of ascii.
        handler = CookieTestRequestHandler()
        handler.set_signed_cookie("foo", b"\xe9", version=1)
        self.assertEqual(handler.get_signed_cookie("foo", min_version=1), b"\xe9")


# See SignedValueTest below for more.
class SecureCookieV2Test(unittest.TestCase):
    KEY_VERSIONS = {0: "ajklasdf0ojaisdf", 1: "aslkjasaolwkjsdf"}

    def test_round_trip(self):
        handler = CookieTestRequestHandler()
        handler.set_signed_cookie("foo", b"bar", version=2)
        self.assertEqual(handler.get_signed_cookie("foo", min_version=2), b"bar")

    def test_key_version_roundtrip(self):
        handler = CookieTestRequestHandler(
            cookie_secret=self.KEY_VERSIONS, key_version=0
        )
        handler.set_signed_cookie("foo", b"bar")
        self.assertEqual(handler.get_signed_cookie("foo"), b"bar")

    def test_key_version_roundtrip_differing_version(self):
        handler = CookieTestRequestHandler(
            cookie_secret=self.KEY_VERSIONS, key_version=1
        )
        handler.set_signed_cookie("foo", b"bar")
        self.assertEqual(handler.get_signed_cookie("foo"), b"bar")

    def test_key_version_increment_version(self):
        handler = CookieTestRequestHandler(
            cookie_secret=self.KEY_VERSIONS, key_version=0
        )
        handler.set_signed_cookie("foo", b"bar")
        new_handler = CookieTestRequestHandler(
            cookie_secret=self.KEY_VERSIONS, key_version=1
        )
        new_handler._cookies = handler._cookies
        self.assertEqual(new_handler.get_signed_cookie("foo"), b"bar")

    def test_key_version_invalidate_version(self):
        handler = CookieTestRequestHandler(
            cookie_secret=self.KEY_VERSIONS, key_version=0
        )
        handler.set_signed_cookie("foo", b"bar")
        new_key_versions = self.KEY_VERSIONS.copy()
        new_key_versions.pop(0)
        new_handler = CookieTestRequestHandler(
            cookie_secret=new_key_versions, key_version=1
        )
        new_handler._cookies = handler._cookies
        self.assertEqual(new_handler.get_signed_cookie("foo"), None)


class FinalReturnTest(WebTestCase):
    final_return = None  # type: Future

    def get_handlers(self):
        test = self

        class FinishHandler(RequestHandler):
            @gen.coroutine
            def get(self):
                test.final_return = self.finish()
                yield test.final_return

            @gen.coroutine
            def post(self):
                self.write("hello,")
                yield self.flush()
                test.final_return = self.finish("world")
                yield test.final_return

        class RenderHandler(RequestHandler):
            def create_template_loader(self, path):
                return DictLoader({"foo.html": "hi"})

            @gen.coroutine
            def get(self):
                test.final_return = self.render("foo.html")

        return [("/finish", FinishHandler), ("/render", RenderHandler)]

    def get_app_kwargs(self):
        return dict(template_path="FinalReturnTest")

    def test_finish_method_return_future(self):
        response = self.fetch(self.get_url("/finish"))
        self.assertEqual(response.code, 200)
        self.assertIsInstance(self.final_return, Future)
        self.assertTrue(self.final_return.done())

        response = self.fetch(self.get_url("/finish"), method="POST", body=b"")
        self.assertEqual(response.code, 200)
        self.assertIsInstance(self.final_return, Future)
        self.assertTrue(self.final_return.done())

    def test_render_method_return_future(self):
        response = self.fetch(self.get_url("/render"))
        self.assertEqual(response.code, 200)
        self.assertIsInstance(self.final_return, Future)


class CookieTest(WebTestCase):
    def get_handlers(self):
        class SetCookieHandler(RequestHandler):
            def get(self):
                # Try setting cookies with different argument types
                # to ensure that everything gets encoded correctly
                self.set_cookie("str", "asdf")
                self.set_cookie("unicode", "qwer")
                self.set_cookie("bytes", b"zxcv")

        class GetCookieHandler(RequestHandler):
            def get(self):
                cookie = self.get_cookie("foo", "default")
                assert cookie is not None
                self.write(cookie)

        class SetCookieDomainHandler(RequestHandler):
            def get(self):
                # unicode domain and path arguments shouldn't break things
                # either (see bug #285)
                self.set_cookie("unicode_args", "blah", domain="foo.com", path="/foo")

        class SetCookieSpecialCharHandler(RequestHandler):
            def get(self):
                self.set_cookie("equals", "a=b")
                self.set_cookie("semicolon", "a;b")
                self.set_cookie("quote", 'a"b')

        class SetCookieOverwriteHandler(RequestHandler):
            def get(self):
                self.set_cookie("a", "b", domain="example.com")
                self.set_cookie("c", "d", domain="example.com")
                # A second call with the same name clobbers the first.
                # Attributes from the first call are not carried over.
                self.set_cookie("a", "e")

        class SetCookieMaxAgeHandler(RequestHandler):
            def get(self):
                self.set_cookie("foo", "bar", max_age=10)

        class SetCookieExpiresDaysHandler(RequestHandler):
            def get(self):
                self.set_cookie("foo", "bar", expires_days=10)

        class SetCookieFalsyFlags(RequestHandler):
            def get(self):
                self.set_cookie("a", "1", secure=True)
                self.set_cookie("b", "1", secure=False)
                self.set_cookie("c", "1", httponly=True)
                self.set_cookie("d", "1", httponly=False)

        class SetCookieDeprecatedArgs(RequestHandler):
            def get(self):
                # Mixed case is supported, but deprecated
                self.set_cookie("a", "b", HttpOnly=True, pATH="/foo")

        return [
            ("/set", SetCookieHandler),
            ("/get", GetCookieHandler),
            ("/set_domain", SetCookieDomainHandler),
            ("/special_char", SetCookieSpecialCharHandler),
            ("/set_overwrite", SetCookieOverwriteHandler),
            ("/set_max_age", SetCookieMaxAgeHandler),
            ("/set_expires_days", SetCookieExpiresDaysHandler),
            ("/set_falsy_flags", SetCookieFalsyFlags),
            ("/set_deprecated", SetCookieDeprecatedArgs),
        ]

    def test_set_cookie(self):
        response = self.fetch("/set")
        self.assertEqual(
            sorted(response.headers.get_list("Set-Cookie")),
            ["bytes=zxcv; Path=/", "str=asdf; Path=/", "unicode=qwer; Path=/"],
        )

    def test_get_cookie(self):
        response = self.fetch("/get", headers={"Cookie": "foo=bar"})
        self.assertEqual(response.body, b"bar")

        response = self.fetch("/get", headers={"Cookie": 'foo="bar"'})
        self.assertEqual(response.body, b"bar")

        response = self.fetch("/get", headers={"Cookie": "/=exception;"})
        self.assertEqual(response.body, b"default")

    def test_set_cookie_domain(self):
        response = self.fetch("/set_domain")
        self.assertEqual(
            response.headers.get_list("Set-Cookie"),
            ["unicode_args=blah; Domain=foo.com; Path=/foo"],
        )

    def test_cookie_special_char(self):
        response = self.fetch("/special_char")
        headers = sorted(response.headers.get_list("Set-Cookie"))
        self.assertEqual(len(headers), 3)
        self.assertEqual(headers[0], 'equals="a=b"; Path=/')
        self.assertEqual(headers[1], 'quote="a\\"b"; Path=/')
        # Semicolons are octal-escaped
        self.assertIn(
            headers[2],
            ('semicolon="a;b"; Path=/', 'semicolon="a\\073b"; Path=/'),
            headers[2],
        )

        data = [
            ("foo=a=b", "a=b"),
            ('foo="a=b"', "a=b"),
            ('foo="a;b"', '"a'),  # even quoted, ";" is a delimiter
            ("foo=a\\073b", "a\\073b"),  # escapes only decoded in quotes
            ('foo="a\\073b"', "a;b"),
            ('foo="a\\"b"', 'a"b'),
        ]
        for header, expected in data:
            logging.debug("trying %r", header)
            response = self.fetch("/get", headers={"Cookie": header})
            self.assertEqual(response.body, utf8(expected))

    def test_set_cookie_overwrite(self):
        response = self.fetch("/set_overwrite")
        headers = response.headers.get_list("Set-Cookie")
        self.assertEqual(
            sorted(headers), ["a=e; Path=/", "c=d; Domain=example.com; Path=/"]
        )

    def test_set_cookie_max_age(self):
        response = self.fetch("/set_max_age")
        headers = response.headers.get_list("Set-Cookie")
        self.assertEqual(sorted(headers), ["foo=bar; Max-Age=10; Path=/"])

    def test_set_cookie_expires_days(self):
        response = self.fetch("/set_expires_days")
        header = response.headers.get("Set-Cookie")
        self.assertIsNotNone(header)
        assert header is not None  # for mypy
        match = re.match("foo=bar; expires=(?P<expires>.+); Path=/", header)
        self.assertIsNotNone(match)
        assert match is not None  # for mypy

        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=10
        )
        header_expires = email.utils.parsedate_to_datetime(match.groupdict()["expires"])
        self.assertLess(abs((expires - header_expires).total_seconds()), 10)

    def test_set_cookie_false_flags(self):
        response = self.fetch("/set_falsy_flags")
        headers = sorted(response.headers.get_list("Set-Cookie"))
        self.assertEqual(headers[0], "a=1; Path=/; Secure")
        self.assertEqual(headers[1], "b=1; Path=/")
        self.assertEqual(headers[2], "c=1; HttpOnly; Path=/")
        self.assertEqual(headers[3], "d=1; Path=/")

    def test_set_cookie_deprecated(self):
        with ignore_deprecation():
            response = self.fetch("/set_deprecated")
        header = response.headers.get("Set-Cookie")
        self.assertEqual(header, "a=b; HttpOnly; Path=/foo")


class AuthRedirectRequestHandler(RequestHandler):
    def initialize(self, login_url):
        self.login_url = login_url

    def get_login_url(self):
        return self.login_url

    @authenticated
    def get(self):
        # we'll never actually get here because the test doesn't follow redirects
        self.send_error(500)


class AuthRedirectTest(WebTestCase):
    def get_handlers(self):
        return [
            ("/relative", AuthRedirectRequestHandler, dict(login_url="/login")),
            (
                "/absolute",
                AuthRedirectRequestHandler,
                dict(login_url="http://example.com/login"),
            ),
        ]

    def test_relative_auth_redirect(self):
        response = self.fetch(self.get_url("/relative"), follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers["Location"], "/login?next=%2Frelative")

    def test_absolute_auth_redirect(self):
        response = self.fetch(self.get_url("/absolute"), follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(
            re.match(
                r"http://example.com/login\?next=http%3A%2F%2F127.0.0.1%3A[0-9]+%2Fabsolute",
                response.headers["Location"],
            ),
            response.headers["Location"],
        )


class ConnectionCloseHandler(RequestHandler):
    def initialize(self, test):
        self.test = test

    @gen.coroutine
    def get(self):
        self.test.on_handler_waiting()
        yield self.test.cleanup_event.wait()

    def on_connection_close(self):
        self.test.on_connection_close()


class ConnectionCloseTest(WebTestCase):
    def get_handlers(self):
        self.cleanup_event = Event()
        return [("/", ConnectionCloseHandler, dict(test=self))]

    def test_connection_close(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        s.connect(("127.0.0.1", self.get_http_port()))
        self.stream = IOStream(s)
        self.stream.write(b"GET / HTTP/1.0\r\n\r\n")
        self.wait()
        # Let the hanging coroutine clean up after itself
        self.cleanup_event.set()
        self.io_loop.run_sync(lambda: gen.sleep(0))

    def on_handler_waiting(self):
        logging.debug("handler waiting")
        self.stream.close()

    def on_connection_close(self):
        logging.debug("connection closed")
        self.stop()


class EchoHandler(RequestHandler):
    def get(self, *path_args):
        # Type checks: web.py interfaces convert argument values to
        # unicode strings (by default, but see also decode_argument).
        # In httpserver.py (i.e. self.request.arguments), they're left
        # as bytes.  Keys are always native strings.
        for key in self.request.arguments:
            if type(key) is not str:
                raise Exception("incorrect type for key: %r" % type(key))
            for bvalue in self.request.arguments[key]:
                if type(bvalue) is not bytes:
                    raise Exception("incorrect type for value: %r" % type(bvalue))
            for svalue in self.get_arguments(key):
                if type(svalue) is not unicode_type:
                    raise Exception("incorrect type for value: %r" % type(svalue))
        for arg in path_args:
            if type(arg) is not unicode_type:
                raise Exception("incorrect type for path arg: %r" % type(arg))
        self.write(
            dict(
                path=self.request.path,
                path_args=path_args,
                args=recursive_unicode(self.request.arguments),
            )
        )


class RequestEncodingTest(WebTestCase):
    def get_handlers(self):
        return [("/group/(.*)", EchoHandler), ("/slashes/([^/]*)/([^/]*)", EchoHandler)]

    def fetch_json(self, path):
        return json_decode(self.fetch(path).body)

    def test_group_question_mark(self):
        # Ensure that url-encoded question marks are handled properly
        self.assertEqual(
            self.fetch_json("/group/%3F"),
            dict(path="/group/%3F", path_args=["?"], args={}),
        )
        self.assertEqual(
            self.fetch_json("/group/%3F?%3F=%3F"),
            dict(path="/group/%3F", path_args=["?"], args={"?": ["?"]}),
        )

    def test_group_encoding(self):
        # Path components and query arguments should be decoded the same way
        self.assertEqual(
            self.fetch_json("/group/%C3%A9?arg=%C3%A9"),
            {
                "path": "/group/%C3%A9",
                "path_args": ["\u00e9"],
                "args": {"arg": ["\u00e9"]},
            },
        )

    def test_slashes(self):
        # Slashes may be escaped to appear as a single "directory" in the path,
        # but they are then unescaped when passed to the get() method.
        self.assertEqual(
            self.fetch_json("/slashes/foo/bar"),
            dict(path="/slashes/foo/bar", path_args=["foo", "bar"], args={}),
        )
        self.assertEqual(
            self.fetch_json("/slashes/a%2Fb/c%2Fd"),
            dict(path="/slashes/a%2Fb/c%2Fd", path_args=["a/b", "c/d"], args={}),
        )

    def test_error(self):
        # Percent signs (encoded as %25) should not mess up printf-style
        # messages in logs
        with ExpectLog(gen_log, ".*Invalid unicode"):
            self.fetch("/group/?arg=%25%e9")


class TypeCheckHandler(RequestHandler):
    def prepare(self):
        self.errors = {}  # type: typing.Dict[str, str]

        self.check_type("status", self.get_status(), int)

        # get_argument is an exception from the general rule of using
        # type str for non-body data mainly for historical reasons.
        self.check_type("argument", self.get_argument("foo"), unicode_type)
        self.check_type("cookie_key", list(self.cookies.keys())[0], str)
        self.check_type("cookie_value", list(self.cookies.values())[0].value, str)

        # Secure cookies return bytes because they can contain arbitrary
        # data, but regular cookies are native strings.
        if list(self.cookies.keys()) != ["asdf"]:
            raise Exception(
                "unexpected values for cookie keys: %r" % self.cookies.keys()
            )
        self.check_type("get_signed_cookie", self.get_signed_cookie("asdf"), bytes)
        self.check_type("get_cookie", self.get_cookie("asdf"), str)

        self.check_type("xsrf_token", self.xsrf_token, bytes)
        self.check_type("xsrf_form_html", self.xsrf_form_html(), str)

        self.check_type("reverse_url", self.reverse_url("typecheck", "foo"), str)

        self.check_type("request_summary", self._request_summary(), str)

    def get(self, path_component):
        # path_component uses type unicode instead of str for consistency
        # with get_argument()
        self.check_type("path_component", path_component, unicode_type)
        self.write(self.errors)

    def post(self, path_component):
        self.check_type("path_component", path_component, unicode_type)
        self.write(self.errors)

    def check_type(self, name, obj, expected_type):
        actual_type = type(obj)
        if expected_type != actual_type:
            self.errors[name] = f"expected {expected_type}, got {actual_type}"


class DecodeArgHandler(RequestHandler):
    def decode_argument(self, value, name=None):
        if type(value) is not bytes:
            raise Exception("unexpected type for value: %r" % type(value))
        # use self.request.arguments directly to avoid recursion
        if "encoding" in self.request.arguments:
            return value.decode(to_unicode(self.request.arguments["encoding"][0]))
        else:
            return value

    def get(self, arg):
        def describe(s):
            if type(s) is bytes:
                return ["bytes", native_str(binascii.b2a_hex(s))]
            elif type(s) is unicode_type:
                return ["unicode", s]
            raise Exception("unknown type")

        self.write({"path": describe(arg), "query": describe(self.get_argument("foo"))})


class LinkifyHandler(RequestHandler):
    def get(self):
        self.render("linkify.html", message="http://example.com")


class UIModuleResourceHandler(RequestHandler):
    def get(self):
        self.render("page.html", entries=[1, 2])


class OptionalPathHandler(RequestHandler):
    def get(self, path):
        self.write({"path": path})


class MultiHeaderHandler(RequestHandler):
    def get(self):
        self.set_header("x-overwrite", "1")
        self.set_header("X-Overwrite", 2)
        self.add_header("x-multi", 3)
        self.add_header("X-Multi", "4")


class RedirectHandler(RequestHandler):
    def get(self):
        if self.get_argument("permanent", None) is not None:
            self.redirect("/", permanent=bool(int(self.get_argument("permanent"))))
        elif self.get_argument("status", None) is not None:
            self.redirect("/", status=int(self.get_argument("status")))
        else:
            raise Exception("didn't get permanent or status arguments")


class EmptyFlushCallbackHandler(RequestHandler):
    @gen.coroutine
    def get(self):
        # Ensure that the flush callback is run whether or not there
        # was any output.  The gen.Task and direct yield forms are
        # equivalent.
        yield self.flush()  # "empty" flush, but writes headers
        yield self.flush()  # empty flush
        self.write("o")
        yield self.flush()  # flushes the "o"
        yield self.flush()  # empty flush
        self.finish("k")


class HeaderInjectionHandler(RequestHandler):
    def get(self):
        try:
            self.set_header("X-Foo", "foo\r\nX-Bar: baz")
            raise Exception("Didn't get expected exception")
        except ValueError as e:
            if "Unsafe header value" in str(e):
                self.finish(b"ok")
            else:
                raise


class SetHeaderHandler(RequestHandler):
    def get(self):
        # tests the validity of web.RequestHandler._VALID_HEADER_CHARS
        illegal_chars = [chr(o) for o in range(0, 0x20)]
        illegal_chars.append(chr(0x7F))
        illegal_chars.remove("\t")
        for char in illegal_chars:
            try:
                self.set_header("X-Foo", "foo" + char + "bar")
                raise Exception("Didn't get expected exception")
            except ValueError as e:
                if "Unsafe header value" not in str(e):
                    raise

        # an empty header value is valid as well
        self.set_header("X-Foo", "")

        self.finish(b"ok")


class GetArgumentHandler(RequestHandler):
    def prepare(self):
        if self.get_argument("source", None) == "query":
            method = self.get_query_argument
        elif self.get_argument("source", None) == "body":
            method = self.get_body_argument
        else:
            method = self.get_argument  # type: ignore
        self.finish(method("foo", "default"))


class GetArgumentsHandler(RequestHandler):
    def prepare(self):
        self.finish(
            dict(
                default=self.get_arguments("foo"),
                query=self.get_query_arguments("foo"),
                body=self.get_body_arguments("foo"),
            )
        )


# This test was shared with wsgi_test.py; now the name is meaningless.
class WSGISafeWebTest(WebTestCase):
    COOKIE_SECRET = "WebTest.COOKIE_SECRET"

    def get_app_kwargs(self):
        loader = DictLoader(
            {
                "linkify.html": "{% module linkify(message) %}",
                "page.html": """\
<html><head></head><body>
{% for e in entries %}
{% module Template("entry.html", entry=e) %}
{% end %}
</body></html>""",
                "entry.html": """\
{{ set_resources(embedded_css=".entry { margin-bottom: 1em; }",
                 embedded_javascript="js_embed()",
                 css_files=["/base.css", "/foo.css"],
                 javascript_files="/common.js",
                 html_head="<meta>",
                 html_body='<script src="/analytics.js"/>') }}
<div class="entry">...</div>""",
            }
        )
        return dict(
            template_loader=loader,
            autoescape="xhtml_escape",
            cookie_secret=self.COOKIE_SECRET,
        )

    def tearDown(self):
        super().tearDown()
        RequestHandler._template_loaders.clear()

    def get_handlers(self):
        urls = [
            url("/typecheck/(.*)", TypeCheckHandler, name="typecheck"),
            url("/decode_arg/(.*)", DecodeArgHandler, name="decode_arg"),
            url("/decode_arg_kw/(?P<arg>.*)", DecodeArgHandler),
            url("/linkify", LinkifyHandler),
            url("/uimodule_resources", UIModuleResourceHandler),
            url("/optional_path/(.+)?", OptionalPathHandler),
            url("/multi_header", MultiHeaderHandler),
            url("/redirect", RedirectHandler),
            url(
                "/web_redirect_permanent",
                WebRedirectHandler,
                {"url": "/web_redirect_newpath"},
            ),
            url(
                "/web_redirect",
                WebRedirectHandler,
                {"url": "/web_redirect_newpath", "permanent": False},
            ),
            url(
                "//web_redirect_double_slash",
                WebRedirectHandler,
                {"url": "/web_redirect_newpath"},
            ),
            url("/header_injection", HeaderInjectionHandler),
            url("/get_argument", GetArgumentHandler),
            url("/get_arguments", GetArgumentsHandler),
            url("/set_header", SetHeaderHandler),
        ]
        return urls

    def fetch_json(self, *args, **kwargs):
        response = self.fetch(*args, **kwargs)
        response.rethrow()
        return json_decode(response.body)

    def test_types(self):
        cookie_value = to_unicode(
            create_signed_value(self.COOKIE_SECRET, "asdf", "qwer")
        )
        response = self.fetch(
            "/typecheck/asdf?foo=bar", headers={"Cookie": "asdf=" + cookie_value}
        )
        data = json_decode(response.body)
        self.assertEqual(data, {})

        response = self.fetch(
            "/typecheck/asdf?foo=bar",
            method="POST",
            headers={"Cookie": "asdf=" + cookie_value},
            body="foo=bar",
        )

    def test_decode_argument(self):
        # These urls all decode to the same thing
        urls = [
            "/decode_arg/%C3%A9?foo=%C3%A9&encoding=utf-8",
            "/decode_arg/%E9?foo=%E9&encoding=latin1",
            "/decode_arg_kw/%E9?foo=%E9&encoding=latin1",
        ]
        for req_url in urls:
            response = self.fetch(req_url)
            response.rethrow()
            data = json_decode(response.body)
            self.assertEqual(
                data,
                {"path": ["unicode", "\u00e9"], "query": ["unicode", "\u00e9"]},
            )

        response = self.fetch("/decode_arg/%C3%A9?foo=%C3%A9")
        response.rethrow()
        data = json_decode(response.body)
        self.assertEqual(data, {"path": ["bytes", "c3a9"], "query": ["bytes", "c3a9"]})

    def test_decode_argument_invalid_unicode(self):
        # test that invalid unicode in URLs causes 400, not 500
        with ExpectLog(gen_log, ".*Invalid unicode.*"):
            response = self.fetch("/typecheck/invalid%FF")
            self.assertEqual(response.code, 400)
            response = self.fetch("/typecheck/invalid?foo=%FF")
            self.assertEqual(response.code, 400)

    def test_decode_argument_plus(self):
        # These urls are all equivalent.
        urls = [
            "/decode_arg/1%20%2B%201?foo=1%20%2B%201&encoding=utf-8",
            "/decode_arg/1%20+%201?foo=1+%2B+1&encoding=utf-8",
        ]
        for req_url in urls:
            response = self.fetch(req_url)
            response.rethrow()
            data = json_decode(response.body)
            self.assertEqual(
                data,
                {"path": ["unicode", "1 + 1"], "query": ["unicode", "1 + 1"]},
            )

    def test_reverse_url(self):
        self.assertEqual(self.app.reverse_url("decode_arg", "foo"), "/decode_arg/foo")
        self.assertEqual(self.app.reverse_url("decode_arg", 42), "/decode_arg/42")
        self.assertEqual(self.app.reverse_url("decode_arg", b"\xe9"), "/decode_arg/%E9")
        self.assertEqual(
            self.app.reverse_url("decode_arg", "\u00e9"), "/decode_arg/%C3%A9"
        )
        self.assertEqual(
            self.app.reverse_url("decode_arg", "1 + 1"), "/decode_arg/1%20%2B%201"
        )

    def test_uimodule_unescaped(self):
        response = self.fetch("/linkify")
        self.assertEqual(
            response.body, b'<a href="http://example.com">http://example.com</a>'
        )

    def test_uimodule_resources(self):
        response = self.fetch("/uimodule_resources")
        self.assertEqual(
            response.body,
            b"""\
<html><head><link href="/base.css" type="text/css" rel="stylesheet"/><link href="/foo.css" type="text/css" rel="stylesheet"/>
<style type="text/css">
.entry { margin-bottom: 1em; }
</style>
<meta>
</head><body>


<div class="entry">...</div>


<div class="entry">...</div>

<script src="/common.js" type="text/javascript"></script>
<script type="text/javascript">
//<![CDATA[
js_embed()
//]]>
</script>
<script src="/analytics.js"/>
</body></html>""",  # noqa: E501
        )

    def test_optional_path(self):
        self.assertEqual(self.fetch_json("/optional_path/foo"), {"path": "foo"})
        self.assertEqual(self.fetch_json("/optional_path/"), {"path": None})

    def test_multi_header(self):
        response = self.fetch("/multi_header")
        self.assertEqual(response.headers["x-overwrite"], "2")
        self.assertEqual(response.headers.get_list("x-multi"), ["3", "4"])

    def test_redirect(self):
        response = self.fetch("/redirect?permanent=1", follow_redirects=False)
        self.assertEqual(response.code, 301)
        response = self.fetch("/redirect?permanent=0", follow_redirects=False)
        self.assertEqual(response.code, 302)
        response = self.fetch("/redirect?status=307", follow_redirects=False)
        self.assertEqual(response.code, 307)

    def test_web_redirect(self):
        response = self.fetch("/web_redirect_permanent", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/web_redirect_newpath")
        response = self.fetch("/web_redirect", follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers["Location"], "/web_redirect_newpath")

    def test_web_redirect_double_slash(self):
        response = self.fetch("//web_redirect_double_slash", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/web_redirect_newpath")

    def test_header_injection(self):
        response = self.fetch("/header_injection")
        self.assertEqual(response.body, b"ok")

    def test_set_header(self):
        response = self.fetch("/set_header")
        self.assertEqual(response.body, b"ok")

    def test_get_argument(self):
        response = self.fetch("/get_argument?foo=bar")
        self.assertEqual(response.body, b"bar")
        response = self.fetch("/get_argument?foo=")
        self.assertEqual(response.body, b"")
        response = self.fetch("/get_argument")
        self.assertEqual(response.body, b"default")

        # Test merging of query and body arguments.
        # In singular form, body arguments take precedence over query arguments.
        body = urllib.parse.urlencode(dict(foo="hello"))
        response = self.fetch("/get_argument?foo=bar", method="POST", body=body)
        self.assertEqual(response.body, b"hello")
        # In plural methods they are merged.
        response = self.fetch("/get_arguments?foo=bar", method="POST", body=body)
        self.assertEqual(
            json_decode(response.body),
            dict(default=["bar", "hello"], query=["bar"], body=["hello"]),
        )

    def test_get_query_arguments(self):
        # send as a post so we can ensure the separation between query
        # string and body arguments.
        body = urllib.parse.urlencode(dict(foo="hello"))
        response = self.fetch(
            "/get_argument?source=query&foo=bar", method="POST", body=body
        )
        self.assertEqual(response.body, b"bar")
        response = self.fetch(
            "/get_argument?source=query&foo=", method="POST", body=body
        )
        self.assertEqual(response.body, b"")
        response = self.fetch("/get_argument?source=query", method="POST", body=body)
        self.assertEqual(response.body, b"default")

    def test_get_body_arguments(self):
        body = urllib.parse.urlencode(dict(foo="bar"))
        response = self.fetch(
            "/get_argument?source=body&foo=hello", method="POST", body=body
        )
        self.assertEqual(response.body, b"bar")

        body = urllib.parse.urlencode(dict(foo=""))
        response = self.fetch(
            "/get_argument?source=body&foo=hello", method="POST", body=body
        )
        self.assertEqual(response.body, b"")

        body = urllib.parse.urlencode(dict())
        response = self.fetch(
            "/get_argument?source=body&foo=hello", method="POST", body=body
        )
        self.assertEqual(response.body, b"default")

    def test_no_gzip(self):
        response = self.fetch("/get_argument")
        self.assertNotIn("Accept-Encoding", response.headers.get("Vary", ""))
        self.assertNotIn("gzip", response.headers.get("Content-Encoding", ""))


class NonWSGIWebTests(WebTestCase):
    def get_handlers(self):
        return [("/empty_flush", EmptyFlushCallbackHandler)]

    def test_empty_flush(self):
        response = self.fetch("/empty_flush")
        self.assertEqual(response.body, b"ok")


class ErrorResponseTest(WebTestCase):
    def get_handlers(self):
        class DefaultHandler(RequestHandler):
            def get(self):
                if self.get_argument("status", None):
                    raise HTTPError(int(self.get_argument("status")))
                1 / 0

        class WriteErrorHandler(RequestHandler):
            def get(self):
                if self.get_argument("status", None):
                    self.send_error(int(self.get_argument("status")))
                else:
                    1 / 0

            def write_error(self, status_code, **kwargs):
                self.set_header("Content-Type", "text/plain")
                if "exc_info" in kwargs:
                    self.write("Exception: %s" % kwargs["exc_info"][0].__name__)
                else:
                    self.write("Status: %d" % status_code)

        class FailedWriteErrorHandler(RequestHandler):
            def get(self):
                1 / 0

            def write_error(self, status_code, **kwargs):
                raise Exception("exception in write_error")

        return [
            url("/default", DefaultHandler),
            url("/write_error", WriteErrorHandler),
            url("/failed_write_error", FailedWriteErrorHandler),
        ]

    def test_default(self):
        with ExpectLog(app_log, "Uncaught exception"):
            response = self.fetch("/default")
            self.assertEqual(response.code, 500)
            self.assertIn(b"500: Internal Server Error", response.body)

            response = self.fetch("/default?status=503")
            self.assertEqual(response.code, 503)
            self.assertIn(b"503: Service Unavailable", response.body)

            response = self.fetch("/default?status=435")
            self.assertEqual(response.code, 435)
            self.assertIn(b"435: Unknown", response.body)

    def test_write_error(self):
        with ExpectLog(app_log, "Uncaught exception"):
            response = self.fetch("/write_error")
            self.assertEqual(response.code, 500)
            self.assertEqual(b"Exception: ZeroDivisionError", response.body)

            response = self.fetch("/write_error?status=503")
            self.assertEqual(response.code, 503)
            self.assertEqual(b"Status: 503", response.body)

    def test_failed_write_error(self):
        with ExpectLog(app_log, "Uncaught exception"):
            response = self.fetch("/failed_write_error")
            self.assertEqual(response.code, 500)
            self.assertEqual(b"", response.body)


class StaticFileTest(WebTestCase):
    # The expected SHA-512 hash of robots.txt, used in tests that call
    # StaticFileHandler.get_version
    robots_txt_hash = (
        b"63a36e950e134b5217e33c763e88840c10a07d80e6057d92b9ac97508de7fb1f"
        b"a6f0e9b7531e169657165ea764e8963399cb6d921ffe6078425aaafe54c04563"
    )
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    def get_handlers(self):
        class StaticUrlHandler(RequestHandler):
            def get(self, path):
                with_v = int(self.get_argument("include_version", "1"))
                self.write(self.static_url(path, include_version=with_v))

        class AbsoluteStaticUrlHandler(StaticUrlHandler):
            include_host = True

        class OverrideStaticUrlHandler(RequestHandler):
            def get(self, path):
                do_include = bool(self.get_argument("include_host"))
                self.include_host = not do_include

                regular_url = self.static_url(path)
                override_url = self.static_url(path, include_host=do_include)
                if override_url == regular_url:
                    return self.write(str(False))

                protocol = self.request.protocol + "://"
                protocol_length = len(protocol)
                check_regular = regular_url.find(protocol, 0, protocol_length)
                check_override = override_url.find(protocol, 0, protocol_length)

                if do_include:
                    result = check_override == 0 and check_regular == -1
                else:
                    result = check_override == -1 and check_regular == 0
                self.write(str(result))

        return [
            ("/static_url/(.*)", StaticUrlHandler),
            ("/abs_static_url/(.*)", AbsoluteStaticUrlHandler),
            ("/override_static_url/(.*)", OverrideStaticUrlHandler),
            ("/root_static/(.*)", StaticFileHandler, dict(path="/")),
        ]

    def get_app_kwargs(self):
        return dict(static_path=relpath("static"))

    def test_static_files(self):
        response = self.fetch("/robots.txt")
        self.assertIn(b"Disallow: /", response.body)

        response = self.fetch("/static/robots.txt")
        self.assertIn(b"Disallow: /", response.body)
        self.assertEqual(response.headers.get("Content-Type"), "text/plain")

    def test_static_files_cacheable(self):
        # Test that the version parameter triggers cache-control headers. This
        # test is pretty weak but it gives us coverage of the code path which
        # was important for detecting the deprecation of datetime.utcnow.
        response = self.fetch("/robots.txt?v=12345")
        self.assertIn(b"Disallow: /", response.body)
        self.assertIn("Cache-Control", response.headers)
        self.assertIn("Expires", response.headers)

    def test_static_compressed_files(self):
        response = self.fetch("/static/sample.xml.gz")
        self.assertEqual(response.headers.get("Content-Type"), "application/gzip")
        response = self.fetch("/static/sample.xml.bz2")
        self.assertEqual(
            response.headers.get("Content-Type"), "application/octet-stream"
        )
        # make sure the uncompressed file still has the correct type
        response = self.fetch("/static/sample.xml")
        self.assertIn(
            response.headers.get("Content-Type"), {"text/xml", "application/xml"}
        )

    def test_static_url(self):
        response = self.fetch("/static_url/robots.txt")
        self.assertEqual(response.body, b"/static/robots.txt?v=" + self.robots_txt_hash)

    def test_absolute_static_url(self):
        response = self.fetch("/abs_static_url/robots.txt")
        self.assertEqual(
            response.body,
            (utf8(self.get_url("/")) + b"static/robots.txt?v=" + self.robots_txt_hash),
        )

    def test_relative_version_exclusion(self):
        response = self.fetch("/static_url/robots.txt?include_version=0")
        self.assertEqual(response.body, b"/static/robots.txt")

    def test_absolute_version_exclusion(self):
        response = self.fetch("/abs_static_url/robots.txt?include_version=0")
        self.assertEqual(response.body, utf8(self.get_url("/") + "static/robots.txt"))

    def test_include_host_override(self):
        self._trigger_include_host_check(False)
        self._trigger_include_host_check(True)

    def _trigger_include_host_check(self, include_host):
        path = "/override_static_url/robots.txt?include_host=%s"
        response = self.fetch(path % int(include_host))
        self.assertEqual(response.body, utf8(str(True)))

    def get_and_head(self, *args, **kwargs):
        """Performs a GET and HEAD request and returns the GET response.

        Fails if any ``Content-*`` headers returned by the two requests
        differ.
        """
        head_response = self.fetch(*args, method="HEAD", **kwargs)
        get_response = self.fetch(*args, method="GET", **kwargs)
        content_headers = set()
        for h in itertools.chain(head_response.headers, get_response.headers):
            if h.startswith("Content-"):
                content_headers.add(h)
        for h in content_headers:
            self.assertEqual(
                head_response.headers.get(h),
                get_response.headers.get(h),
                "%s differs between GET (%s) and HEAD (%s)"
                % (h, head_response.headers.get(h), get_response.headers.get(h)),
            )
        return get_response

    def test_static_304_if_modified_since(self):
        response1 = self.get_and_head("/static/robots.txt")
        response2 = self.get_and_head(
            "/static/robots.txt",
            headers={"If-Modified-Since": response1.headers["Last-Modified"]},
        )
        self.assertEqual(response2.code, 304)
        self.assertNotIn("Content-Length", response2.headers)

    def test_static_304_if_none_match(self):
        response1 = self.get_and_head("/static/robots.txt")
        response2 = self.get_and_head(
            "/static/robots.txt", headers={"If-None-Match": response1.headers["Etag"]}
        )
        self.assertEqual(response2.code, 304)

    def test_static_304_etag_modified_bug(self):
        response1 = self.get_and_head("/static/robots.txt")
        response2 = self.get_and_head(
            "/static/robots.txt",
            headers={
                "If-None-Match": '"MISMATCH"',
                "If-Modified-Since": response1.headers["Last-Modified"],
            },
        )
        self.assertEqual(response2.code, 200)

    def test_static_304_if_modified_since_invalid(self):
        response = self.get_and_head(
            "/static/robots.txt",
            headers={"If-Modified-Since": "!nv@l!d"},
        )
        self.assertEqual(response.code, 200)

    def test_static_if_modified_since_pre_epoch(self):
        # On windows, the functions that work with time_t do not accept
        # negative values, and at least one client (processing.js) seems
        # to use if-modified-since 1/1/1960 as a cache-busting technique.
        response = self.get_and_head(
            "/static/robots.txt",
            headers={"If-Modified-Since": "Fri, 01 Jan 1960 00:00:00 GMT"},
        )
        self.assertEqual(response.code, 200)

    def test_static_if_modified_since_time_zone(self):
        # Instead of the value from Last-Modified, make requests with times
        # chosen just before and after the known modification time
        # of the file to ensure that the right time zone is being used
        # when parsing If-Modified-Since.
        stat = os.stat(relpath("static/robots.txt"))

        response = self.get_and_head(
            "/static/robots.txt",
            headers={"If-Modified-Since": format_timestamp(stat.st_mtime - 1)},
        )
        self.assertEqual(response.code, 200)
        response = self.get_and_head(
            "/static/robots.txt",
            headers={"If-Modified-Since": format_timestamp(stat.st_mtime + 1)},
        )
        self.assertEqual(response.code, 304)

    def test_static_etag(self):
        response = self.get_and_head("/static/robots.txt")
        self.assertEqual(
            utf8(response.headers.get("Etag")), b'"' + self.robots_txt_hash + b'"'
        )

    def test_static_with_range(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=0-9"}
        )
        self.assertEqual(response.code, 206)
        self.assertEqual(response.body, b"User-agent")
        self.assertEqual(
            utf8(response.headers.get("Etag")), b'"' + self.robots_txt_hash + b'"'
        )
        self.assertEqual(response.headers.get("Content-Length"), "10")
        self.assertEqual(response.headers.get("Content-Range"), "bytes 0-9/26")

    def test_static_with_range_full_file(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=0-"}
        )
        # Note: Chrome refuses to play audio if it gets an HTTP 206 in response
        # to ``Range: bytes=0-`` :(
        self.assertEqual(response.code, 200)
        robots_file_path = os.path.join(self.static_dir, "robots.txt")
        with open(robots_file_path, encoding="utf-8") as f:
            self.assertEqual(response.body, utf8(f.read()))
        self.assertEqual(response.headers.get("Content-Length"), "26")
        self.assertIsNone(response.headers.get("Content-Range"))

    def test_static_with_range_full_past_end(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=0-10000000"}
        )
        self.assertEqual(response.code, 200)
        robots_file_path = os.path.join(self.static_dir, "robots.txt")
        with open(robots_file_path, encoding="utf-8") as f:
            self.assertEqual(response.body, utf8(f.read()))
        self.assertEqual(response.headers.get("Content-Length"), "26")
        self.assertIsNone(response.headers.get("Content-Range"))

    def test_static_with_range_partial_past_end(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=1-10000000"}
        )
        self.assertEqual(response.code, 206)
        robots_file_path = os.path.join(self.static_dir, "robots.txt")
        with open(robots_file_path, encoding="utf-8") as f:
            self.assertEqual(response.body, utf8(f.read()[1:]))
        self.assertEqual(response.headers.get("Content-Length"), "25")
        self.assertEqual(response.headers.get("Content-Range"), "bytes 1-25/26")

    def test_static_with_range_end_edge(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=22-"}
        )
        self.assertEqual(response.body, b": /\n")
        self.assertEqual(response.headers.get("Content-Length"), "4")
        self.assertEqual(response.headers.get("Content-Range"), "bytes 22-25/26")

    def test_static_with_range_neg_end(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=-4"}
        )
        self.assertEqual(response.body, b": /\n")
        self.assertEqual(response.headers.get("Content-Length"), "4")
        self.assertEqual(response.headers.get("Content-Range"), "bytes 22-25/26")

    def test_static_with_range_neg_past_start(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=-1000000"}
        )
        self.assertEqual(response.code, 200)
        robots_file_path = os.path.join(self.static_dir, "robots.txt")
        with open(robots_file_path, encoding="utf-8") as f:
            self.assertEqual(response.body, utf8(f.read()))
        self.assertEqual(response.headers.get("Content-Length"), "26")
        self.assertIsNone(response.headers.get("Content-Range"))

    def test_static_invalid_range(self):
        response = self.get_and_head("/static/robots.txt", headers={"Range": "asdf"})
        self.assertEqual(response.code, 200)

    def test_static_unsatisfiable_range_zero_suffix(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=-0"}
        )
        self.assertEqual(response.headers.get("Content-Range"), "bytes */26")
        self.assertEqual(response.code, 416)

    def test_static_unsatisfiable_range_invalid_start(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=26"}
        )
        self.assertEqual(response.code, 416)
        self.assertEqual(response.headers.get("Content-Range"), "bytes */26")

    def test_static_unsatisfiable_range_end_less_than_start(self):
        response = self.get_and_head(
            "/static/robots.txt", headers={"Range": "bytes=10-3"}
        )
        self.assertEqual(response.code, 416)
        self.assertEqual(response.headers.get("Content-Range"), "bytes */26")

    def test_static_head(self):
        response = self.fetch("/static/robots.txt", method="HEAD")
        self.assertEqual(response.code, 200)
        # No body was returned, but we did get the right content length.
        self.assertEqual(response.body, b"")
        self.assertEqual(response.headers["Content-Length"], "26")
        self.assertEqual(
            utf8(response.headers["Etag"]), b'"' + self.robots_txt_hash + b'"'
        )

    def test_static_head_range(self):
        response = self.fetch(
            "/static/robots.txt", method="HEAD", headers={"Range": "bytes=1-4"}
        )
        self.assertEqual(response.code, 206)
        self.assertEqual(response.body, b"")
        self.assertEqual(response.headers["Content-Length"], "4")
        self.assertEqual(
            utf8(response.headers["Etag"]), b'"' + self.robots_txt_hash + b'"'
        )

    def test_static_range_if_none_match(self):
        response = self.get_and_head(
            "/static/robots.txt",
            headers={
                "Range": "bytes=1-4",
                "If-None-Match": b'"' + self.robots_txt_hash + b'"',
            },
        )
        self.assertEqual(response.code, 304)
        self.assertEqual(response.body, b"")
        self.assertNotIn("Content-Length", response.headers)
        self.assertEqual(
            utf8(response.headers["Etag"]), b'"' + self.robots_txt_hash + b'"'
        )

    def test_static_404(self):
        response = self.get_and_head("/static/blarg")
        self.assertEqual(response.code, 404)

    def test_path_traversal_protection(self):
        # curl_httpclient processes ".." on the client side, so we
        # must test this with simple_httpclient.
        self.http_client.close()
        self.http_client = SimpleAsyncHTTPClient()
        with ExpectLog(gen_log, ".*not in root static directory"):
            response = self.get_and_head("/static/../static_foo.txt")
        # Attempted path traversal should result in 403, not 200
        # (which means the check failed and the file was served)
        # or 404 (which means that the file didn't exist and
        # is probably a packaging error).
        self.assertEqual(response.code, 403)

    @unittest.skipIf(os.name != "posix", "non-posix OS")
    def test_root_static_path(self):
        # Sometimes people set the StaticFileHandler's path to '/'
        # to disable Tornado's path validation (in conjunction with
        # their own validation in get_absolute_path). Make sure
        # that the stricter validation in 4.2.1 doesn't break them.
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static/robots.txt"
        )
        response = self.get_and_head("/root_static" + urllib.parse.quote(path))
        self.assertEqual(response.code, 200)


class StaticDefaultFilenameTest(WebTestCase):
    def get_app_kwargs(self):
        return dict(
            static_path=relpath("static"),
            static_handler_args=dict(default_filename="index.html"),
        )

    def get_handlers(self):
        return []

    def test_static_default_filename(self):
        response = self.fetch("/static/dir/", follow_redirects=False)
        self.assertEqual(response.code, 200)
        self.assertEqual(b"this is the index\n", response.body)

    def test_static_default_redirect(self):
        response = self.fetch("/static/dir", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertTrue(response.headers["Location"].endswith("/static/dir/"))


class StaticDefaultFilenameRootTest(WebTestCase):
    def get_app_kwargs(self):
        return dict(
            static_path=os.path.abspath(relpath("static")),
            static_handler_args=dict(default_filename="index.html"),
            static_url_prefix="/",
        )

    def get_handlers(self):
        return []

    def get_http_client(self):
        # simple_httpclient only: curl doesn't let you send a request starting
        # with two slashes.
        return SimpleAsyncHTTPClient()

    def test_no_open_redirect(self):
        # This test verifies that the open redirect that affected some configurations
        # prior to Tornado 6.3.2 is no longer possible. The vulnerability required
        # a static_url_prefix of "/" and a default_filename (any value) to be set.
        # The absolute* server-side path to the static directory must also be known.
        #
        # * Almost absolute: On windows, the drive letter is stripped from the path.
        test_dir = os.path.dirname(__file__)
        drive, tail = os.path.splitdrive(test_dir)
        if os.name == "posix":
            self.assertEqual(tail, test_dir)
        else:
            test_dir = tail
        with ExpectLog(gen_log, ".*cannot redirect path with two initial slashes"):
            response = self.fetch(
                f"//evil.com/../{test_dir}/static/dir",
                follow_redirects=False,
            )
        self.assertEqual(response.code, 403)


class StaticFileWithPathTest(WebTestCase):
    def get_app_kwargs(self):
        return dict(
            static_path=relpath("static"),
            static_handler_args=dict(default_filename="index.html"),
        )

    def get_handlers(self):
        return [("/foo/(.*)", StaticFileHandler, {"path": relpath("templates/")})]

    def test_serve(self):
        response = self.fetch("/foo/utf8.html")
        self.assertEqual(response.body, b"H\xc3\xa9llo\n")


class CustomStaticFileTest(WebTestCase):
    def get_handlers(self):
        class MyStaticFileHandler(StaticFileHandler):
            @classmethod
            def make_static_url(cls, settings, path):
                version_hash = cls.get_version(settings, path)
                extension_index = path.rindex(".")
                before_version = path[:extension_index]
                after_version = path[(extension_index + 1) :]
                return "/static/{}.{}.{}".format(
                    before_version,
                    version_hash,
                    after_version,
                )

            def parse_url_path(self, url_path):
                extension_index = url_path.rindex(".")
                version_index = url_path.rindex(".", 0, extension_index)
                return f"{url_path[:version_index]}{url_path[extension_index:]}"

            @classmethod
            def get_absolute_path(cls, settings, path):
                return "CustomStaticFileTest:" + path

            def validate_absolute_path(self, root, absolute_path):
                return absolute_path

            @classmethod
            def get_content(self, path, start=None, end=None):
                assert start is None and end is None
                if path == "CustomStaticFileTest:foo.txt":
                    return b"bar"
                raise Exception("unexpected path %r" % path)

            def get_content_size(self):
                if self.absolute_path == "CustomStaticFileTest:foo.txt":
                    return 3
                raise Exception("unexpected path %r" % self.absolute_path)

            def get_modified_time(self):
                return None

            @classmethod
            def get_version(cls, settings, path):
                return "42"

        class StaticUrlHandler(RequestHandler):
            def get(self, path):
                self.write(self.static_url(path))

        self.static_handler_class = MyStaticFileHandler

        return [("/static_url/(.*)", StaticUrlHandler)]

    def get_app_kwargs(self):
        return dict(static_path="dummy", static_handler_class=self.static_handler_class)

    def test_serve(self):
        response = self.fetch("/static/foo.42.txt")
        self.assertEqual(response.body, b"bar")

    def test_static_url(self):
        with ExpectLog(gen_log, "Could not open static file", required=False):
            response = self.fetch("/static_url/foo.txt")
            self.assertEqual(response.body, b"/static/foo.42.txt")


class HostMatchingTest(WebTestCase):
    class Handler(RequestHandler):
        def initialize(self, reply):
            self.reply = reply

        def get(self):
            self.write(self.reply)

    def get_handlers(self):
        return [("/foo", HostMatchingTest.Handler, {"reply": "wildcard"})]

    def test_host_matching(self):
        self.app.add_handlers(
            "www.example.com", [("/foo", HostMatchingTest.Handler, {"reply": "[0]"})]
        )
        self.app.add_handlers(
            r"www\.example\.com", [("/bar", HostMatchingTest.Handler, {"reply": "[1]"})]
        )
        self.app.add_handlers(
            "www.example.com", [("/baz", HostMatchingTest.Handler, {"reply": "[2]"})]
        )
        self.app.add_handlers(
            "www.e.*e.com", [("/baz", HostMatchingTest.Handler, {"reply": "[3]"})]
        )

        response = self.fetch("/foo")
        self.assertEqual(response.body, b"wildcard")
        response = self.fetch("/bar")
        self.assertEqual(response.code, 404)
        response = self.fetch("/baz")
        self.assertEqual(response.code, 404)

        response = self.fetch("/foo", headers={"Host": "www.example.com"})
        self.assertEqual(response.body, b"[0]")
        response = self.fetch("/bar", headers={"Host": "www.example.com"})
        self.assertEqual(response.body, b"[1]")
        response = self.fetch("/baz", headers={"Host": "www.example.com"})
        self.assertEqual(response.body, b"[2]")
        response = self.fetch("/baz", headers={"Host": "www.exe.com"})
        self.assertEqual(response.body, b"[3]")


class DefaultHostMatchingTest(WebTestCase):
    def get_handlers(self):
        return []

    def get_app_kwargs(self):
        return {"default_host": "www.example.com"}

    def test_default_host_matching(self):
        self.app.add_handlers(
            "www.example.com", [("/foo", HostMatchingTest.Handler, {"reply": "[0]"})]
        )
        self.app.add_handlers(
            r"www\.example\.com", [("/bar", HostMatchingTest.Handler, {"reply": "[1]"})]
        )
        self.app.add_handlers(
            "www.test.com", [("/baz", HostMatchingTest.Handler, {"reply": "[2]"})]
        )

        response = self.fetch("/foo")
        self.assertEqual(response.body, b"[0]")
        response = self.fetch("/bar")
        self.assertEqual(response.body, b"[1]")
        response = self.fetch("/baz")
        self.assertEqual(response.code, 404)

        response = self.fetch("/foo", headers={"X-Real-Ip": "127.0.0.1"})
        self.assertEqual(response.code, 404)

        self.app.default_host = "www.test.com"

        response = self.fetch("/baz")
        self.assertEqual(response.body, b"[2]")


class NamedURLSpecGroupsTest(WebTestCase):
    def get_handlers(self):
        class EchoHandler(RequestHandler):
            def get(self, path):
                self.write(path)

        return [
            ("/str/(?P<path>.*)", EchoHandler),
            ("/unicode/(?P<path>.*)", EchoHandler),
        ]

    def test_named_urlspec_groups(self):
        response = self.fetch("/str/foo")
        self.assertEqual(response.body, b"foo")

        response = self.fetch("/unicode/bar")
        self.assertEqual(response.body, b"bar")


class ClearHeaderTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.set_header("h1", "foo")
            self.set_header("h2", "bar")
            self.clear_header("h1")
            self.clear_header("nonexistent")

    def test_clear_header(self):
        response = self.fetch("/")
        self.assertNotIn("h1", response.headers)
        self.assertEqual(response.headers["h2"], "bar")


class Header204Test(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.set_status(204)
            self.finish()

    def test_204_headers(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 204)
        self.assertNotIn("Content-Length", response.headers)
        self.assertNotIn("Transfer-Encoding", response.headers)


class Header304Test(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.set_header("Content-Language", "en_US")
            self.write("hello")

    def test_304_headers(self):
        response1 = self.fetch("/")
        self.assertEqual(response1.headers["Content-Length"], "5")
        self.assertEqual(response1.headers["Content-Language"], "en_US")

        response2 = self.fetch(
            "/", headers={"If-None-Match": response1.headers["Etag"]}
        )
        self.assertEqual(response2.code, 304)
        self.assertNotIn("Content-Length", response2.headers)
        self.assertNotIn("Content-Language", response2.headers)
        # Not an entity header, but should not be added to 304s by chunking
        self.assertNotIn("Transfer-Encoding", response2.headers)


class StatusReasonTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            reason = self.request.arguments.get("reason", [])
            self.set_status(
                int(self.get_argument("code")),
                reason=to_unicode(reason[0]) if reason else None,
            )

    def get_http_client(self):
        # simple_httpclient only: curl doesn't expose the reason string
        return SimpleAsyncHTTPClient()

    def test_status(self):
        response = self.fetch("/?code=304")
        self.assertEqual(response.code, 304)
        self.assertEqual(response.reason, "Not Modified")
        response = self.fetch("/?code=304&reason=Foo")
        self.assertEqual(response.code, 304)
        self.assertEqual(response.reason, "Foo")
        response = self.fetch("/?code=682&reason=Bar")
        self.assertEqual(response.code, 682)
        self.assertEqual(response.reason, "Bar")
        response = self.fetch("/?code=682")
        self.assertEqual(response.code, 682)
        self.assertEqual(response.reason, "Unknown")


class DateHeaderTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.write("hello")

    def test_date_header(self):
        response = self.fetch("/")
        header_date = email.utils.parsedate_to_datetime(response.headers["Date"])
        self.assertLess(
            header_date - datetime.datetime.now(datetime.timezone.utc),
            datetime.timedelta(seconds=2),
        )


class RaiseWithReasonTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            raise HTTPError(682, reason="Foo")

    def get_http_client(self):
        # simple_httpclient only: curl doesn't expose the reason string
        return SimpleAsyncHTTPClient()

    def test_raise_with_reason(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 682)
        self.assertEqual(response.reason, "Foo")
        self.assertIn(b"682: Foo", response.body)

    def test_httperror_str(self):
        self.assertEqual(str(HTTPError(682, reason="Foo")), "HTTP 682: Foo")

    def test_httperror_str_from_httputil(self):
        self.assertEqual(str(HTTPError(682)), "HTTP 682: Unknown")


class ErrorHandlerXSRFTest(WebTestCase):
    def get_handlers(self):
        # note that if the handlers list is empty we get the default_host
        # redirect fallback instead of a 404, so test with both an
        # explicitly defined error handler and an implicit 404.
        return [("/error", ErrorHandler, dict(status_code=417))]

    def get_app_kwargs(self):
        return dict(xsrf_cookies=True)

    def test_error_xsrf(self):
        response = self.fetch("/error", method="POST", body="")
        self.assertEqual(response.code, 417)

    def test_404_xsrf(self):
        response = self.fetch("/404", method="POST", body="")
        self.assertEqual(response.code, 404)


class GzipTestCase(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            for v in self.get_arguments("vary"):
                self.add_header("Vary", v)
            # Must write at least MIN_LENGTH bytes to activate compression.
            self.write("hello world" + ("!" * GZipContentEncoding.MIN_LENGTH))

    def get_app_kwargs(self):
        return dict(
            gzip=True, static_path=os.path.join(os.path.dirname(__file__), "static")
        )

    def assert_compressed(self, response):
        # simple_httpclient renames the content-encoding header;
        # curl_httpclient doesn't.
        self.assertEqual(
            response.headers.get(
                "Content-Encoding", response.headers.get("X-Consumed-Content-Encoding")
            ),
            "gzip",
        )

    def test_gzip(self):
        response = self.fetch("/")
        self.assert_compressed(response)
        self.assertEqual(response.headers["Vary"], "Accept-Encoding")

    def test_gzip_static(self):
        # The streaming responses in StaticFileHandler have subtle
        # interactions with the gzip output so test this case separately.
        response = self.fetch("/robots.txt")
        self.assert_compressed(response)
        self.assertEqual(response.headers["Vary"], "Accept-Encoding")

    def test_gzip_not_requested(self):
        response = self.fetch("/", use_gzip=False)
        self.assertNotIn("Content-Encoding", response.headers)
        self.assertEqual(response.headers["Vary"], "Accept-Encoding")

    def test_vary_already_present(self):
        response = self.fetch("/?vary=Accept-Language")
        self.assert_compressed(response)
        self.assertEqual(
            [s.strip() for s in response.headers["Vary"].split(",")],
            ["Accept-Language", "Accept-Encoding"],
        )

    def test_vary_already_present_multiple(self):
        # Regression test for https://github.com/tornadoweb/tornado/issues/1670
        response = self.fetch("/?vary=Accept-Language&vary=Cookie")
        self.assert_compressed(response)
        self.assertEqual(
            [s.strip() for s in response.headers["Vary"].split(",")],
            ["Accept-Language", "Cookie", "Accept-Encoding"],
        )


class PathArgsInPrepareTest(WebTestCase):
    class Handler(RequestHandler):
        def prepare(self):
            self.write(dict(args=self.path_args, kwargs=self.path_kwargs))

        def get(self, path):
            assert path == "foo"
            self.finish()

    def get_handlers(self):
        return [("/pos/(.*)", self.Handler), ("/kw/(?P<path>.*)", self.Handler)]

    def test_pos(self):
        response = self.fetch("/pos/foo")
        response.rethrow()
        data = json_decode(response.body)
        self.assertEqual(data, {"args": ["foo"], "kwargs": {}})

    def test_kw(self):
        response = self.fetch("/kw/foo")
        response.rethrow()
        data = json_decode(response.body)
        self.assertEqual(data, {"args": [], "kwargs": {"path": "foo"}})


class ClearAllCookiesTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.clear_all_cookies()
            self.write("ok")

    def test_clear_all_cookies(self):
        response = self.fetch("/", headers={"Cookie": "foo=bar; baz=xyzzy"})
        set_cookies = sorted(response.headers.get_list("Set-Cookie"))
        # Python 3.5 sends 'baz="";'; older versions use 'baz=;'
        self.assertTrue(set_cookies[0].startswith('baz="";'))
        self.assertTrue(set_cookies[1].startswith('foo="";'))


class PermissionError(Exception):
    pass


class ExceptionHandlerTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            exc = self.get_argument("exc")
            if exc == "http":
                raise HTTPError(410, "no longer here")
            elif exc == "zero":
                1 / 0
            elif exc == "permission":
                raise PermissionError("not allowed")

        def write_error(self, status_code, **kwargs):
            if "exc_info" in kwargs:
                typ, value, tb = kwargs["exc_info"]
                if isinstance(value, PermissionError):
                    self.set_status(403)
                    self.write("PermissionError")
                    return
            RequestHandler.write_error(self, status_code, **kwargs)

        def log_exception(self, typ, value, tb):
            if isinstance(value, PermissionError):
                app_log.warning("custom logging for PermissionError: %s", value.args[0])
            else:
                RequestHandler.log_exception(self, typ, value, tb)

    def test_http_error(self):
        # HTTPErrors are logged as warnings with no stack trace.
        # TODO: extend ExpectLog to test this more precisely
        with ExpectLog(gen_log, ".*no longer here"):
            response = self.fetch("/?exc=http")
            self.assertEqual(response.code, 410)

    def test_unknown_error(self):
        # Unknown errors are logged as errors with a stack trace.
        with ExpectLog(app_log, "Uncaught exception"):
            response = self.fetch("/?exc=zero")
            self.assertEqual(response.code, 500)

    def test_known_error(self):
        # log_exception can override logging behavior, and write_error
        # can override the response.
        with ExpectLog(app_log, "custom logging for PermissionError: not allowed"):
            response = self.fetch("/?exc=permission")
            self.assertEqual(response.code, 403)


class BuggyLoggingTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            1 / 0

        def log_exception(self, typ, value, tb):
            1 / 0

    def test_buggy_log_exception(self):
        # Something gets logged even though the application's
        # logger is broken.
        with ExpectLog(app_log, ".*"):
            self.fetch("/")


class UIMethodUIModuleTest(SimpleHandlerTestCase):
    """Test that UI methods and modules are created correctly and
    associated with the handler.
    """

    class Handler(RequestHandler):
        def get(self):
            self.render("foo.html")

        def value(self):
            return self.get_argument("value")

    def get_app_kwargs(self):
        def my_ui_method(handler, x):
            return f"In my_ui_method({x}) with handler value {handler.value()}."

        class MyModule(UIModule):
            def render(self, x):
                return "In MyModule({}) with handler value {}.".format(
                    x,
                    typing.cast(UIMethodUIModuleTest.Handler, self.handler).value(),
                )

        loader = DictLoader(
            {"foo.html": "{{ my_ui_method(42) }} {% module MyModule(123) %}"}
        )
        return dict(
            template_loader=loader,
            ui_methods={"my_ui_method": my_ui_method},
            ui_modules={"MyModule": MyModule},
        )

    def tearDown(self):
        super().tearDown()
        # TODO: fix template loader caching so this isn't necessary.
        RequestHandler._template_loaders.clear()

    def test_ui_method(self):
        response = self.fetch("/?value=asdf")
        self.assertEqual(
            response.body,
            b"In my_ui_method(42) with handler value asdf. "
            b"In MyModule(123) with handler value asdf.",
        )


class GetArgumentErrorTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            try:
                self.get_argument("foo")
                self.write({})
            except MissingArgumentError as e:
                self.write({"arg_name": e.arg_name, "log_message": e.log_message})

    def test_catch_error(self):
        response = self.fetch("/")
        self.assertEqual(
            json_decode(response.body),
            {"arg_name": "foo", "log_message": "Missing argument foo"},
        )


class SetLazyPropertiesTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def prepare(self):
            self.current_user = "Ben"
            self.locale = locale.get("en_US")

        def get_user_locale(self):
            raise NotImplementedError()

        def get_current_user(self):
            raise NotImplementedError()

        def get(self):
            self.write(f"Hello {self.current_user} ({self.locale.code})")

    def test_set_properties(self):
        # Ensure that current_user can be assigned to normally for apps
        # that want to forgo the lazy get_current_user property
        response = self.fetch("/")
        self.assertEqual(response.body, b"Hello Ben (en_US)")


class GetCurrentUserTest(WebTestCase):
    def get_app_kwargs(self):
        class WithoutUserModule(UIModule):
            def render(self):
                return ""

        class WithUserModule(UIModule):
            def render(self):
                return str(self.current_user)

        loader = DictLoader(
            {
                "without_user.html": "",
                "with_user.html": "{{ current_user }}",
                "without_user_module.html": "{% module WithoutUserModule() %}",
                "with_user_module.html": "{% module WithUserModule() %}",
            }
        )
        return dict(
            template_loader=loader,
            ui_modules={
                "WithUserModule": WithUserModule,
                "WithoutUserModule": WithoutUserModule,
            },
        )

    def tearDown(self):
        super().tearDown()
        RequestHandler._template_loaders.clear()

    def get_handlers(self):
        class CurrentUserHandler(RequestHandler):
            def prepare(self):
                self.has_loaded_current_user = False

            def get_current_user(self):
                self.has_loaded_current_user = True
                return ""

        class WithoutUserHandler(CurrentUserHandler):
            def get(self):
                self.render_string("without_user.html")
                self.finish(str(self.has_loaded_current_user))

        class WithUserHandler(CurrentUserHandler):
            def get(self):
                self.render_string("with_user.html")
                self.finish(str(self.has_loaded_current_user))

        class CurrentUserModuleHandler(CurrentUserHandler):
            def get_template_namespace(self):
                # If RequestHandler.get_template_namespace is called, then
                # get_current_user is evaluated. Until #820 is fixed, this
                # is a small hack to circumvent the issue.
                return self.ui

        class WithoutUserModuleHandler(CurrentUserModuleHandler):
            def get(self):
                self.render_string("without_user_module.html")
                self.finish(str(self.has_loaded_current_user))

        class WithUserModuleHandler(CurrentUserModuleHandler):
            def get(self):
                self.render_string("with_user_module.html")
                self.finish(str(self.has_loaded_current_user))

        return [
            ("/without_user", WithoutUserHandler),
            ("/with_user", WithUserHandler),
            ("/without_user_module", WithoutUserModuleHandler),
            ("/with_user_module", WithUserModuleHandler),
        ]

    @unittest.skip("needs fix")
    def test_get_current_user_is_lazy(self):
        # TODO: Make this test pass. See #820.
        response = self.fetch("/without_user")
        self.assertEqual(response.body, b"False")

    def test_get_current_user_works(self):
        response = self.fetch("/with_user")
        self.assertEqual(response.body, b"True")

    def test_get_current_user_from_ui_module_is_lazy(self):
        response = self.fetch("/without_user_module")
        self.assertEqual(response.body, b"False")

    def test_get_current_user_from_ui_module_works(self):
        response = self.fetch("/with_user_module")
        self.assertEqual(response.body, b"True")


class UnimplementedHTTPMethodsTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        pass

    def test_unimplemented_standard_methods(self):
        for method in ["HEAD", "GET", "DELETE", "OPTIONS"]:
            response = self.fetch("/", method=method)
            self.assertEqual(response.code, 405)
        for method in ["POST", "PUT"]:
            response = self.fetch("/", method=method, body=b"")
            self.assertEqual(response.code, 405)


class UnimplementedNonStandardMethodsTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def other(self):
            # Even though this method exists, it won't get called automatically
            # because it is not in SUPPORTED_METHODS.
            self.write("other")

    def test_unimplemented_patch(self):
        # PATCH is recently standardized; Tornado supports it by default
        # but wsgiref.validate doesn't like it.
        response = self.fetch("/", method="PATCH", body=b"")
        self.assertEqual(response.code, 405)

    def test_unimplemented_other(self):
        response = self.fetch("/", method="OTHER", allow_nonstandard_methods=True)
        self.assertEqual(response.code, 405)


class AllHTTPMethodsTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def method(self):
            assert self.request.method is not None
            self.write(self.request.method)

        get = delete = options = post = put = method  # type: ignore

    def test_standard_methods(self):
        response = self.fetch("/", method="HEAD")
        self.assertEqual(response.body, b"")
        for method in ["GET", "DELETE", "OPTIONS"]:
            response = self.fetch("/", method=method)
            self.assertEqual(response.body, utf8(method))
        for method in ["POST", "PUT"]:
            response = self.fetch("/", method=method, body=b"")
            self.assertEqual(response.body, utf8(method))


class PatchMethodTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        SUPPORTED_METHODS = RequestHandler.SUPPORTED_METHODS + (  # type: ignore
            "OTHER",
        )

        def patch(self):
            self.write("patch")

        def other(self):
            self.write("other")

    def test_patch(self):
        response = self.fetch("/", method="PATCH", body=b"")
        self.assertEqual(response.body, b"patch")

    def test_other(self):
        response = self.fetch("/", method="OTHER", allow_nonstandard_methods=True)
        self.assertEqual(response.body, b"other")


class FinishInPrepareTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def prepare(self):
            self.finish("done")

        def get(self):
            # It's difficult to assert for certain that a method did not
            # or will not be called in an asynchronous context, but this
            # will be logged noisily if it is reached.
            raise Exception("should not reach this method")

    def test_finish_in_prepare(self):
        response = self.fetch("/")
        self.assertEqual(response.body, b"done")


class Default404Test(WebTestCase):
    def get_handlers(self):
        # If there are no handlers at all a default redirect handler gets added.
        return [("/foo", RequestHandler)]

    def test_404(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(
            response.body,
            b"<html><title>404: Not Found</title>"
            b"<body>404: Not Found</body></html>",
        )


class Custom404Test(WebTestCase):
    def get_handlers(self):
        return [("/foo", RequestHandler)]

    def get_app_kwargs(self):
        class Custom404Handler(RequestHandler):
            def get(self):
                self.set_status(404)
                self.write("custom 404 response")

        return dict(default_handler_class=Custom404Handler)

    def test_404(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.body, b"custom 404 response")


class DefaultHandlerArgumentsTest(WebTestCase):
    def get_handlers(self):
        return [("/foo", RequestHandler)]

    def get_app_kwargs(self):
        return dict(
            default_handler_class=ErrorHandler,
            default_handler_args=dict(status_code=403),
        )

    def test_403(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 403)


class HandlerByNameTest(WebTestCase):
    def get_handlers(self):
        # All three are equivalent.
        return [
            ("/hello1", HelloHandler),
            ("/hello2", "tornado.test.web_test.HelloHandler"),
            url("/hello3", "tornado.test.web_test.HelloHandler"),
        ]

    def test_handler_by_name(self):
        resp = self.fetch("/hello1")
        self.assertEqual(resp.body, b"hello")
        resp = self.fetch("/hello2")
        self.assertEqual(resp.body, b"hello")
        resp = self.fetch("/hello3")
        self.assertEqual(resp.body, b"hello")


class StreamingRequestBodyTest(WebTestCase):
    def get_handlers(self):
        @stream_request_body
        class StreamingBodyHandler(RequestHandler):
            def initialize(self, test):
                self.test = test

            def prepare(self):
                self.test.prepared.set_result(None)

            def data_received(self, data):
                self.test.data.set_result(data)

            def get(self):
                self.test.finished.set_result(None)
                self.write({})

        @stream_request_body
        class EarlyReturnHandler(RequestHandler):
            def prepare(self):
                # If we finish the response in prepare, it won't continue to
                # the (non-existent) data_received.
                raise HTTPError(401)

        @stream_request_body
        class CloseDetectionHandler(RequestHandler):
            def initialize(self, test):
                self.test = test

            def on_connection_close(self):
                super().on_connection_close()
                self.test.close_future.set_result(None)

        return [
            ("/stream_body", StreamingBodyHandler, dict(test=self)),
            ("/early_return", EarlyReturnHandler),
            ("/close_detection", CloseDetectionHandler, dict(test=self)),
        ]

    def connect(self, url, connection_close):
        # Use a raw connection so we can control the sending of data.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        s.connect(("127.0.0.1", self.get_http_port()))
        stream = IOStream(s)
        stream.write(b"GET " + url + b" HTTP/1.1\r\nHost: 127.0.0.1\r\n")
        if connection_close:
            stream.write(b"Connection: close\r\n")
        stream.write(b"Transfer-Encoding: chunked\r\n\r\n")
        return stream

    @gen_test
    def test_streaming_body(self):
        self.prepared = Future()  # type: Future[None]
        self.data = Future()  # type: Future[bytes]
        self.finished = Future()  # type: Future[None]

        stream = self.connect(b"/stream_body", connection_close=True)
        yield self.prepared
        stream.write(b"4\r\nasdf\r\n")
        # Ensure the first chunk is received before we send the second.
        data = yield self.data
        self.assertEqual(data, b"asdf")
        self.data = Future()
        stream.write(b"4\r\nqwer\r\n")
        data = yield self.data
        self.assertEqual(data, b"qwer")
        stream.write(b"0\r\n\r\n")
        yield self.finished
        data = yield stream.read_until_close()
        # This would ideally use an HTTP1Connection to read the response.
        self.assertTrue(data.endswith(b"{}"))
        stream.close()

    @gen_test
    def test_early_return(self):
        stream = self.connect(b"/early_return", connection_close=False)
        data = yield stream.read_until_close()
        self.assertTrue(data.startswith(b"HTTP/1.1 401"))

    @gen_test
    def test_early_return_with_data(self):
        stream = self.connect(b"/early_return", connection_close=False)
        stream.write(b"4\r\nasdf\r\n")
        data = yield stream.read_until_close()
        self.assertTrue(data.startswith(b"HTTP/1.1 401"))

    @gen_test
    def test_close_during_upload(self):
        self.close_future = Future()  # type: Future[None]
        stream = self.connect(b"/close_detection", connection_close=False)
        stream.close()
        yield self.close_future


# Each method in this handler returns a yieldable object and yields to the
# IOLoop so the future is not immediately ready.  Ensure that the
# yieldables are respected and no method is called before the previous
# one has completed.
@stream_request_body
class BaseFlowControlHandler(RequestHandler):
    def initialize(self, test):
        self.test = test
        self.method = None
        self.methods = []  # type: typing.List[str]

    @contextlib.contextmanager
    def in_method(self, method):
        if self.method is not None:
            self.test.fail(f"entered method {method} while in {self.method}")
        self.method = method
        self.methods.append(method)
        try:
            yield
        finally:
            self.method = None

    @gen.coroutine
    def prepare(self):
        # Note that asynchronous prepare() does not block data_received,
        # so we don't use in_method here.
        self.methods.append("prepare")
        yield gen.moment

    @gen.coroutine
    def post(self):
        with self.in_method("post"):
            yield gen.moment
        self.write(dict(methods=self.methods))


class BaseStreamingRequestFlowControlTest:
    def get_httpserver_options(self):
        # Use a small chunk size so flow control is relevant even though
        # all the data arrives at once.
        return dict(chunk_size=10, decompress_request=True)

    def get_http_client(self):
        # simple_httpclient only: curl doesn't support body_producer.
        return SimpleAsyncHTTPClient()

    # Test all the slightly different code paths for fixed, chunked, etc bodies.
    def test_flow_control_fixed_body(self: typing.Any):
        response = self.fetch("/", body="abcdefghijklmnopqrstuvwxyz", method="POST")
        response.rethrow()
        self.assertEqual(
            json_decode(response.body),
            dict(
                methods=[
                    "prepare",
                    "data_received",
                    "data_received",
                    "data_received",
                    "post",
                ]
            ),
        )

    def test_flow_control_chunked_body(self: typing.Any):
        chunks = [b"abcd", b"efgh", b"ijkl"]

        @gen.coroutine
        def body_producer(write):
            for i in chunks:
                yield write(i)

        response = self.fetch("/", body_producer=body_producer, method="POST")
        response.rethrow()
        self.assertEqual(
            json_decode(response.body),
            dict(
                methods=[
                    "prepare",
                    "data_received",
                    "data_received",
                    "data_received",
                    "post",
                ]
            ),
        )

    def test_flow_control_compressed_body(self: typing.Any):
        bytesio = BytesIO()
        gzip_file = gzip.GzipFile(mode="w", fileobj=bytesio)
        gzip_file.write(b"abcdefghijklmnopqrstuvwxyz")
        gzip_file.close()
        compressed_body = bytesio.getvalue()
        response = self.fetch(
            "/",
            body=compressed_body,
            method="POST",
            headers={"Content-Encoding": "gzip"},
        )
        response.rethrow()
        self.assertEqual(
            json_decode(response.body),
            dict(
                methods=[
                    "prepare",
                    "data_received",
                    "data_received",
                    "data_received",
                    "post",
                ]
            ),
        )


class DecoratedStreamingRequestFlowControlTest(
    BaseStreamingRequestFlowControlTest, WebTestCase
):
    def get_handlers(self):
        class DecoratedFlowControlHandler(BaseFlowControlHandler):
            @gen.coroutine
            def data_received(self, data):
                with self.in_method("data_received"):
                    yield gen.moment

        return [("/", DecoratedFlowControlHandler, dict(test=self))]


class NativeStreamingRequestFlowControlTest(
    BaseStreamingRequestFlowControlTest, WebTestCase
):
    def get_handlers(self):
        class NativeFlowControlHandler(BaseFlowControlHandler):
            async def data_received(self, data):
                with self.in_method("data_received"):
                    import asyncio

                    await asyncio.sleep(0)

        return [("/", NativeFlowControlHandler, dict(test=self))]


class IncorrectContentLengthTest(SimpleHandlerTestCase):
    def get_handlers(self):
        test = self
        self.server_error = None

        # Manually set a content-length that doesn't match the actual content.
        class TooHigh(RequestHandler):
            def get(self):
                self.set_header("Content-Length", "42")
                try:
                    self.finish("ok")
                except Exception as e:
                    test.server_error = e
                    raise

        class TooLow(RequestHandler):
            def get(self):
                self.set_header("Content-Length", "2")
                try:
                    self.finish("hello")
                except Exception as e:
                    test.server_error = e
                    raise

        return [("/high", TooHigh), ("/low", TooLow)]

    def test_content_length_too_high(self):
        # When the content-length is too high, the connection is simply
        # closed without completing the response.  An error is logged on
        # the server.
        with ExpectLog(app_log, "(Uncaught exception|Exception in callback)"):
            with ExpectLog(
                gen_log,
                "(Cannot send error response after headers written"
                "|Failed to flush partial response)",
            ):
                with self.assertRaises(HTTPClientError):
                    self.fetch("/high", raise_error=True)
        self.assertEqual(
            str(self.server_error), "Tried to write 40 bytes less than Content-Length"
        )

    def test_content_length_too_low(self):
        # When the content-length is too low, the connection is closed
        # without writing the last chunk, so the client never sees the request
        # complete (which would be a framing error).
        with ExpectLog(app_log, "(Uncaught exception|Exception in callback)"):
            with ExpectLog(
                gen_log,
                "(Cannot send error response after headers written"
                "|Failed to flush partial response)",
            ):
                with self.assertRaises(HTTPClientError):
                    self.fetch("/low", raise_error=True)
        self.assertEqual(
            str(self.server_error), "Tried to write more data than Content-Length"
        )


class ClientCloseTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            if self.request.version.startswith("HTTP/1"):
                # Simulate a connection closed by the client during
                # request processing.  The client will see an error, but the
                # server should respond gracefully (without logging errors
                # because we were unable to write out as many bytes as
                # Content-Length said we would)
                self.request.connection.stream.close()  # type: ignore
                self.write("hello")
            else:
                # TODO: add a HTTP2-compatible version of this test.
                self.write("requires HTTP/1.x")

    def test_client_close(self):
        with self.assertRaises((HTTPClientError, unittest.SkipTest)):  # type: ignore
            response = self.fetch("/", raise_error=True)
            if response.body == b"requires HTTP/1.x":
                self.skipTest("requires HTTP/1.x")
            self.assertEqual(response.code, 599)


class SignedValueTest(unittest.TestCase):
    SECRET = "It's a secret to everybody"
    SECRET_DICT = {0: "asdfbasdf", 1: "12312312", 2: "2342342"}

    def past(self):
        return self.present() - 86400 * 32

    def present(self):
        return 1300000000

    def test_known_values(self):
        signed_v1 = create_signed_value(
            SignedValueTest.SECRET, "key", "value", version=1, clock=self.present
        )
        self.assertEqual(
            signed_v1, b"dmFsdWU=|1300000000|31c934969f53e48164c50768b40cbd7e2daaaa4f"
        )

        signed_v2 = create_signed_value(
            SignedValueTest.SECRET, "key", "value", version=2, clock=self.present
        )
        self.assertEqual(
            signed_v2,
            b"2|1:0|10:1300000000|3:key|8:dmFsdWU=|"
            b"3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e152",
        )

        signed_default = create_signed_value(
            SignedValueTest.SECRET, "key", "value", clock=self.present
        )
        self.assertEqual(signed_default, signed_v2)

        decoded_v1 = decode_signed_value(
            SignedValueTest.SECRET, "key", signed_v1, min_version=1, clock=self.present
        )
        self.assertEqual(decoded_v1, b"value")

        decoded_v2 = decode_signed_value(
            SignedValueTest.SECRET, "key", signed_v2, min_version=2, clock=self.present
        )
        self.assertEqual(decoded_v2, b"value")

    def test_name_swap(self):
        signed1 = create_signed_value(
            SignedValueTest.SECRET, "key1", "value", clock=self.present
        )
        signed2 = create_signed_value(
            SignedValueTest.SECRET, "key2", "value", clock=self.present
        )
        # Try decoding each string with the other's "name"
        decoded1 = decode_signed_value(
            SignedValueTest.SECRET, "key2", signed1, clock=self.present
        )
        self.assertIsNone(decoded1)
        decoded2 = decode_signed_value(
            SignedValueTest.SECRET, "key1", signed2, clock=self.present
        )
        self.assertIsNone(decoded2)

    def test_expired(self):
        signed = create_signed_value(
            SignedValueTest.SECRET, "key1", "value", clock=self.past
        )
        decoded_past = decode_signed_value(
            SignedValueTest.SECRET, "key1", signed, clock=self.past
        )
        self.assertEqual(decoded_past, b"value")
        decoded_present = decode_signed_value(
            SignedValueTest.SECRET, "key1", signed, clock=self.present
        )
        self.assertIsNone(decoded_present)

    def test_payload_tampering(self):
        # These cookies are variants of the one in test_known_values.
        sig = "3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e152"

        def validate(prefix):
            return b"value" == decode_signed_value(
                SignedValueTest.SECRET, "key", prefix + sig, clock=self.present
            )

        self.assertTrue(validate("2|1:0|10:1300000000|3:key|8:dmFsdWU=|"))
        # Change key version
        self.assertFalse(validate("2|1:1|10:1300000000|3:key|8:dmFsdWU=|"))
        # length mismatch (field too short)
        self.assertFalse(validate("2|1:0|10:130000000|3:key|8:dmFsdWU=|"))
        # length mismatch (field too long)
        self.assertFalse(validate("2|1:0|10:1300000000|3:keey|8:dmFsdWU=|"))

    def test_signature_tampering(self):
        prefix = "2|1:0|10:1300000000|3:key|8:dmFsdWU=|"

        def validate(sig):
            return b"value" == decode_signed_value(
                SignedValueTest.SECRET, "key", prefix + sig, clock=self.present
            )

        self.assertTrue(
            validate("3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e152")
        )
        # All zeros
        self.assertFalse(validate("0" * 32))
        # Change one character
        self.assertFalse(
            validate("4d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e152")
        )
        # Change another character
        self.assertFalse(
            validate("3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e153")
        )
        # Truncate
        self.assertFalse(
            validate("3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e15")
        )
        # Lengthen
        self.assertFalse(
            validate(
                "3d4e60b996ff9c5d5788e333a0cba6f238a22c6c0f94788870e1a9ecd482e1538"
            )
        )

    def test_non_ascii(self):
        value = b"\xe9"
        signed = create_signed_value(
            SignedValueTest.SECRET, "key", value, clock=self.present
        )
        decoded = decode_signed_value(
            SignedValueTest.SECRET, "key", signed, clock=self.present
        )
        self.assertEqual(value, decoded)

    def test_key_versioning_read_write_default_key(self):
        value = b"\xe9"
        signed = create_signed_value(
            SignedValueTest.SECRET_DICT, "key", value, clock=self.present, key_version=0
        )
        decoded = decode_signed_value(
            SignedValueTest.SECRET_DICT, "key", signed, clock=self.present
        )
        self.assertEqual(value, decoded)

    def test_key_versioning_read_write_non_default_key(self):
        value = b"\xe9"
        signed = create_signed_value(
            SignedValueTest.SECRET_DICT, "key", value, clock=self.present, key_version=1
        )
        decoded = decode_signed_value(
            SignedValueTest.SECRET_DICT, "key", signed, clock=self.present
        )
        self.assertEqual(value, decoded)

    def test_key_versioning_invalid_key(self):
        value = b"\xe9"
        signed = create_signed_value(
            SignedValueTest.SECRET_DICT, "key", value, clock=self.present, key_version=0
        )
        newkeys = SignedValueTest.SECRET_DICT.copy()
        newkeys.pop(0)
        decoded = decode_signed_value(newkeys, "key", signed, clock=self.present)
        self.assertIsNone(decoded)

    def test_key_version_retrieval(self):
        value = b"\xe9"
        signed = create_signed_value(
            SignedValueTest.SECRET_DICT, "key", value, clock=self.present, key_version=1
        )
        key_version = get_signature_key_version(signed)
        self.assertEqual(1, key_version)


class XSRFTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            version = int(self.get_argument("version", "2"))
            # This would be a bad idea in a real app, but in this test
            # it's fine.
            self.settings["xsrf_cookie_version"] = version
            self.write(self.xsrf_token)

        def post(self):
            self.write("ok")

    def get_app_kwargs(self):
        return dict(xsrf_cookies=True)

    def setUp(self):
        super().setUp()
        self.xsrf_token = self.get_token()

    def get_token(self, old_token=None, version=None):
        if old_token is not None:
            headers = self.cookie_headers(old_token)
        else:
            headers = None
        response = self.fetch(
            "/" if version is None else ("/?version=%d" % version), headers=headers
        )
        response.rethrow()
        return native_str(response.body)

    def cookie_headers(self, token=None):
        if token is None:
            token = self.xsrf_token
        return {"Cookie": "_xsrf=" + token}

    def test_xsrf_fail_no_token(self):
        with ExpectLog(gen_log, ".*'_xsrf' argument missing"):
            response = self.fetch("/", method="POST", body=b"")
        self.assertEqual(response.code, 403)

    def test_xsrf_fail_body_no_cookie(self):
        with ExpectLog(gen_log, ".*XSRF cookie does not match POST"):
            response = self.fetch(
                "/",
                method="POST",
                body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            )
        self.assertEqual(response.code, 403)

    def test_xsrf_fail_argument_invalid_format(self):
        with ExpectLog(gen_log, ".*'_xsrf' argument has invalid format"):
            response = self.fetch(
                "/",
                method="POST",
                headers=self.cookie_headers(),
                body=urllib.parse.urlencode(dict(_xsrf="3|")),
            )
        self.assertEqual(response.code, 403)

    def test_xsrf_fail_cookie_invalid_format(self):
        with ExpectLog(gen_log, ".*XSRF cookie does not match POST"):
            response = self.fetch(
                "/",
                method="POST",
                headers=self.cookie_headers(token="3|"),
                body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            )
        self.assertEqual(response.code, 403)

    def test_xsrf_fail_cookie_no_body(self):
        with ExpectLog(gen_log, ".*'_xsrf' argument missing"):
            response = self.fetch(
                "/", method="POST", body=b"", headers=self.cookie_headers()
            )
        self.assertEqual(response.code, 403)

    def test_xsrf_success_short_token(self):
        response = self.fetch(
            "/",
            method="POST",
            body=urllib.parse.urlencode(dict(_xsrf="deadbeef")),
            headers=self.cookie_headers(token="deadbeef"),
        )
        self.assertEqual(response.code, 200)

    def test_xsrf_success_non_hex_token(self):
        response = self.fetch(
            "/",
            method="POST",
            body=urllib.parse.urlencode(dict(_xsrf="xoxo")),
            headers=self.cookie_headers(token="xoxo"),
        )
        self.assertEqual(response.code, 200)

    def test_xsrf_success_post_body(self):
        response = self.fetch(
            "/",
            method="POST",
            body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            headers=self.cookie_headers(),
        )
        self.assertEqual(response.code, 200)

    def test_xsrf_success_query_string(self):
        response = self.fetch(
            "/?" + urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            method="POST",
            body=b"",
            headers=self.cookie_headers(),
        )
        self.assertEqual(response.code, 200)

    def test_xsrf_success_header(self):
        response = self.fetch(
            "/",
            method="POST",
            body=b"",
            headers=dict(
                {"X-Xsrftoken": self.xsrf_token},  # type: ignore
                **self.cookie_headers(),
            ),
        )
        self.assertEqual(response.code, 200)

    def test_distinct_tokens(self):
        # Every request gets a distinct token.
        NUM_TOKENS = 10
        tokens = set()
        for i in range(NUM_TOKENS):
            tokens.add(self.get_token())
        self.assertEqual(len(tokens), NUM_TOKENS)

    def test_cross_user(self):
        token2 = self.get_token()
        # Each token can be used to authenticate its own request.
        for token in (self.xsrf_token, token2):
            response = self.fetch(
                "/",
                method="POST",
                body=urllib.parse.urlencode(dict(_xsrf=token)),
                headers=self.cookie_headers(token),
            )
            self.assertEqual(response.code, 200)
        # Sending one in the cookie and the other in the body is not allowed.
        for cookie_token, body_token in (
            (self.xsrf_token, token2),
            (token2, self.xsrf_token),
        ):
            with ExpectLog(gen_log, ".*XSRF cookie does not match POST"):
                response = self.fetch(
                    "/",
                    method="POST",
                    body=urllib.parse.urlencode(dict(_xsrf=body_token)),
                    headers=self.cookie_headers(cookie_token),
                )
            self.assertEqual(response.code, 403)

    def test_refresh_token(self):
        token = self.xsrf_token
        tokens_seen = {token}
        # A user's token is stable over time.  Refreshing the page in one tab
        # might update the cookie while an older tab still has the old cookie
        # in its DOM.  Simulate this scenario by passing a constant token
        # in the body and re-querying for the token.
        for i in range(5):
            token = self.get_token(token)
            # Tokens are encoded uniquely each time
            tokens_seen.add(token)
            response = self.fetch(
                "/",
                method="POST",
                body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
                headers=self.cookie_headers(token),
            )
            self.assertEqual(response.code, 200)
        self.assertEqual(len(tokens_seen), 6)

    def test_versioning(self):
        # Version 1 still produces distinct tokens per request.
        self.assertNotEqual(self.get_token(version=1), self.get_token(version=1))

        # Refreshed v1 tokens are all identical.
        v1_token = self.get_token(version=1)
        for i in range(5):
            self.assertEqual(self.get_token(v1_token, version=1), v1_token)

        # Upgrade to a v2 version of the same token
        v2_token = self.get_token(v1_token)
        self.assertNotEqual(v1_token, v2_token)
        # Each v1 token can map to many v2 tokens.
        self.assertNotEqual(v2_token, self.get_token(v1_token))

        # The tokens are cross-compatible.
        for cookie_token, body_token in ((v1_token, v2_token), (v2_token, v1_token)):
            response = self.fetch(
                "/",
                method="POST",
                body=urllib.parse.urlencode(dict(_xsrf=body_token)),
                headers=self.cookie_headers(cookie_token),
            )
            self.assertEqual(response.code, 200)


# A subset of the previous test with a different cookie name
class XSRFCookieNameTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.write(self.xsrf_token)

        def post(self):
            self.write("ok")

    def get_app_kwargs(self):
        return dict(
            xsrf_cookies=True,
            xsrf_cookie_name="__Host-xsrf",
            xsrf_cookie_kwargs={"secure": True},
        )

    def setUp(self):
        super().setUp()
        self.xsrf_token = self.get_token()

    def get_token(self, old_token=None):
        if old_token is not None:
            headers = self.cookie_headers(old_token)
        else:
            headers = None
        response = self.fetch("/", headers=headers)
        response.rethrow()
        return native_str(response.body)

    def cookie_headers(self, token=None):
        if token is None:
            token = self.xsrf_token
        return {"Cookie": "__Host-xsrf=" + token}

    def test_xsrf_fail_no_token(self):
        with ExpectLog(gen_log, ".*'_xsrf' argument missing"):
            response = self.fetch("/", method="POST", body=b"")
        self.assertEqual(response.code, 403)

    def test_xsrf_fail_body_no_cookie(self):
        with ExpectLog(gen_log, ".*XSRF cookie does not match POST"):
            response = self.fetch(
                "/",
                method="POST",
                body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            )
        self.assertEqual(response.code, 403)

    def test_xsrf_success_post_body(self):
        response = self.fetch(
            "/",
            method="POST",
            # Note that renaming the cookie doesn't rename the POST param
            body=urllib.parse.urlencode(dict(_xsrf=self.xsrf_token)),
            headers=self.cookie_headers(),
        )
        self.assertEqual(response.code, 200)


class XSRFCookieKwargsTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.write(self.xsrf_token)

    def get_app_kwargs(self):
        return dict(
            xsrf_cookies=True, xsrf_cookie_kwargs=dict(httponly=True, expires_days=2)
        )

    def test_xsrf_httponly(self):
        response = self.fetch("/")
        self.assertIn("httponly;", response.headers["Set-Cookie"].lower())
        self.assertIn("expires=", response.headers["Set-Cookie"].lower())
        header = response.headers.get("Set-Cookie")
        assert header is not None
        match = re.match(".*; expires=(?P<expires>.+);.*", header)
        assert match is not None

        expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=2
        )
        header_expires = email.utils.parsedate_to_datetime(match.groupdict()["expires"])
        if header_expires.tzinfo is None:
            header_expires = header_expires.replace(tzinfo=datetime.timezone.utc)
        self.assertTrue(abs((expires - header_expires).total_seconds()) < 10)


class FinishExceptionTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            self.set_status(401)
            self.set_header("WWW-Authenticate", 'Basic realm="something"')
            if self.get_argument("finish_value", ""):
                raise Finish("authentication required")
            else:
                self.write("authentication required")
                raise Finish()

    def test_finish_exception(self):
        for u in ["/", "/?finish_value=1"]:
            response = self.fetch(u)
            self.assertEqual(response.code, 401)
            self.assertEqual(
                'Basic realm="something"', response.headers.get("WWW-Authenticate")
            )
            self.assertEqual(b"authentication required", response.body)


class DecoratorTest(WebTestCase):
    def get_handlers(self):
        class RemoveSlashHandler(RequestHandler):
            @removeslash
            def get(self):
                pass

        class AddSlashHandler(RequestHandler):
            @addslash
            def get(self):
                pass

        return [("/removeslash/", RemoveSlashHandler), ("/addslash", AddSlashHandler)]

    def test_removeslash(self):
        response = self.fetch("/removeslash/", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/removeslash")

        response = self.fetch("/removeslash/?foo=bar", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/removeslash?foo=bar")

    def test_addslash(self):
        response = self.fetch("/addslash", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/addslash/")

        response = self.fetch("/addslash?foo=bar", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/addslash/?foo=bar")


class CacheTest(WebTestCase):
    def get_handlers(self):
        class EtagHandler(RequestHandler):
            def get(self, computed_etag):
                self.write(computed_etag)

            def compute_etag(self):
                return self._write_buffer[0]

        return [("/etag/(.*)", EtagHandler)]

    def test_wildcard_etag(self):
        computed_etag = '"xyzzy"'
        etags = "*"
        self._test_etag(computed_etag, etags, 304)

    def test_strong_etag_match(self):
        computed_etag = '"xyzzy"'
        etags = '"xyzzy"'
        self._test_etag(computed_etag, etags, 304)

    def test_multiple_strong_etag_match(self):
        computed_etag = '"xyzzy1"'
        etags = '"xyzzy1", "xyzzy2"'
        self._test_etag(computed_etag, etags, 304)

    def test_strong_etag_not_match(self):
        computed_etag = '"xyzzy"'
        etags = '"xyzzy1"'
        self._test_etag(computed_etag, etags, 200)

    def test_multiple_strong_etag_not_match(self):
        computed_etag = '"xyzzy"'
        etags = '"xyzzy1", "xyzzy2"'
        self._test_etag(computed_etag, etags, 200)

    def test_weak_etag_match(self):
        computed_etag = '"xyzzy1"'
        etags = 'W/"xyzzy1"'
        self._test_etag(computed_etag, etags, 304)

    def test_multiple_weak_etag_match(self):
        computed_etag = '"xyzzy2"'
        etags = 'W/"xyzzy1", W/"xyzzy2"'
        self._test_etag(computed_etag, etags, 304)

    def test_weak_etag_not_match(self):
        computed_etag = '"xyzzy2"'
        etags = 'W/"xyzzy1"'
        self._test_etag(computed_etag, etags, 200)

    def test_multiple_weak_etag_not_match(self):
        computed_etag = '"xyzzy3"'
        etags = 'W/"xyzzy1", W/"xyzzy2"'
        self._test_etag(computed_etag, etags, 200)

    def _test_etag(self, computed_etag, etags, status_code):
        response = self.fetch(
            "/etag/" + computed_etag, headers={"If-None-Match": etags}
        )
        self.assertEqual(response.code, status_code)


class RequestSummaryTest(SimpleHandlerTestCase):
    class Handler(RequestHandler):
        def get(self):
            # remote_ip is optional, although it's set by
            # both HTTPServer and WSGIAdapter.
            # Clobber it to make sure it doesn't break logging.
            self.request.remote_ip = None
            self.finish(self._request_summary())

    def test_missing_remote_ip(self):
        resp = self.fetch("/")
        self.assertEqual(resp.body, b"GET / (None)")


class HTTPErrorTest(unittest.TestCase):
    def test_copy(self):
        e = HTTPError(403, reason="Go away")
        e2 = copy.copy(e)
        self.assertIsNot(e, e2)
        self.assertEqual(e.status_code, e2.status_code)
        self.assertEqual(e.reason, e2.reason)


class ApplicationTest(AsyncTestCase):
    def test_listen(self):
        app = Application([])
        server = app.listen(0, address="127.0.0.1")
        server.stop()


class URLSpecReverseTest(unittest.TestCase):
    def test_reverse(self):
        self.assertEqual("/favicon.ico", url(r"/favicon\.ico", None).reverse())
        self.assertEqual("/favicon.ico", url(r"^/favicon\.ico$", None).reverse())

    def test_non_reversible(self):
        # URLSpecs are non-reversible if they include non-constant
        # regex features outside capturing groups. Currently, this is
        # only strictly enforced for backslash-escaped character
        # classes.
        paths = [r"^/api/v\d+/foo/(\w+)$"]
        for path in paths:
            # A URLSpec can still be created even if it cannot be reversed.
            url_spec = url(path, None)
            try:
                result = url_spec.reverse()
                self.fail(
                    "did not get expected exception when reversing %s. "
                    "result: %s" % (path, result)
                )
            except ValueError:
                pass

    def test_reverse_arguments(self):
        self.assertEqual(
            "/api/v1/foo/bar", url(r"^/api/v1/foo/(\w+)$", None).reverse("bar")
        )
        self.assertEqual(
            "/api.v1/foo/5/icon.png",
            url(r"/api\.v1/foo/([0-9]+)/icon\.png", None).reverse(5),
        )


class RedirectHandlerTest(WebTestCase):
    def get_handlers(self):
        return [
            ("/src", WebRedirectHandler, {"url": "/dst"}),
            ("/src2", WebRedirectHandler, {"url": "/dst2?foo=bar"}),
            (r"/(.*?)/(.*?)/(.*)", WebRedirectHandler, {"url": "/{1}/{0}/{2}"}),
        ]

    def test_basic_redirect(self):
        response = self.fetch("/src", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/dst")

    def test_redirect_with_argument(self):
        response = self.fetch("/src?foo=bar", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/dst?foo=bar")

    def test_redirect_with_appending_argument(self):
        response = self.fetch("/src2?foo2=bar2", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/dst2?foo=bar&foo2=bar2")

    def test_redirect_pattern(self):
        response = self.fetch("/a/b/c", follow_redirects=False)
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], "/b/a/c")


class AcceptLanguageTest(WebTestCase):
    """Test evaluation of Accept-Language header"""

    def get_handlers(self):
        locale.load_gettext_translations(
            os.path.join(os.path.dirname(__file__), "gettext_translations"),
            "tornado_test",
        )

        class AcceptLanguageHandler(RequestHandler):
            def get(self):
                self.set_header(
                    "Content-Language", self.get_browser_locale().code.replace("_", "-")
                )
                self.finish(b"")

        return [
            ("/", AcceptLanguageHandler),
        ]

    def test_accept_language(self):
        response = self.fetch("/", headers={"Accept-Language": "fr-FR;q=0.9"})
        self.assertEqual(response.headers["Content-Language"], "fr-FR")

        response = self.fetch("/", headers={"Accept-Language": "fr-FR; q=0.9"})
        self.assertEqual(response.headers["Content-Language"], "fr-FR")

    def test_accept_language_ignore(self):
        response = self.fetch("/", headers={"Accept-Language": "fr-FR;q=0"})
        self.assertEqual(response.headers["Content-Language"], "en-US")

    def test_accept_language_invalid(self):
        response = self.fetch("/", headers={"Accept-Language": "fr-FR;q=-1"})
        self.assertEqual(response.headers["Content-Language"], "en-US")

# === NexusCore/openenv\Lib\site-packages\fontTools\designspaceLib\__init__.py ===
"""
    designSpaceDocument

    - Read and write designspace files
"""

from __future__ import annotations

import collections
import copy
import itertools
import math
import os
import posixpath
from io import BytesIO, StringIO
from textwrap import indent
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Union, cast

from fontTools.misc import etree as ET
from fontTools.misc import plistlib
from fontTools.misc.loggingTools import LogMixin
from fontTools.misc.textTools import tobytes, tostr


__all__ = [
    "AxisDescriptor",
    "AxisLabelDescriptor",
    "AxisMappingDescriptor",
    "BaseDocReader",
    "BaseDocWriter",
    "DesignSpaceDocument",
    "DesignSpaceDocumentError",
    "DiscreteAxisDescriptor",
    "InstanceDescriptor",
    "LocationLabelDescriptor",
    "RangeAxisSubsetDescriptor",
    "RuleDescriptor",
    "SourceDescriptor",
    "ValueAxisSubsetDescriptor",
    "VariableFontDescriptor",
]

# ElementTree allows to find namespace-prefixed elements, but not attributes
# so we have to do it ourselves for 'xml:lang'
XML_NS = "{http://www.w3.org/XML/1998/namespace}"
XML_LANG = XML_NS + "lang"


def posix(path):
    """Normalize paths using forward slash to work also on Windows."""
    new_path = posixpath.join(*path.split(os.path.sep))
    if path.startswith("/"):
        # The above transformation loses absolute paths
        new_path = "/" + new_path
    elif path.startswith(r"\\"):
        # The above transformation loses leading slashes of UNC path mounts
        new_path = "//" + new_path
    return new_path


def posixpath_property(private_name):
    """Generate a propery that holds a path always using forward slashes."""

    def getter(self):
        # Normal getter
        return getattr(self, private_name)

    def setter(self, value):
        # The setter rewrites paths using forward slashes
        if value is not None:
            value = posix(value)
        setattr(self, private_name, value)

    return property(getter, setter)


class DesignSpaceDocumentError(Exception):
    def __init__(self, msg, obj=None):
        self.msg = msg
        self.obj = obj

    def __str__(self):
        return str(self.msg) + (": %r" % self.obj if self.obj is not None else "")


class AsDictMixin(object):
    def asdict(self):
        d = {}
        for attr, value in self.__dict__.items():
            if attr.startswith("_"):
                continue
            if hasattr(value, "asdict"):
                value = value.asdict()
            elif isinstance(value, list):
                value = [v.asdict() if hasattr(v, "asdict") else v for v in value]
            d[attr] = value
        return d


class SimpleDescriptor(AsDictMixin):
    """Containers for a bunch of attributes"""

    # XXX this is ugly. The 'print' is inappropriate here, and instead of
    # assert, it should simply return True/False
    def compare(self, other):
        # test if this object contains the same data as the other
        for attr in self._attrs:
            try:
                assert getattr(self, attr) == getattr(other, attr)
            except AssertionError:
                print(
                    "failed attribute",
                    attr,
                    getattr(self, attr),
                    "!=",
                    getattr(other, attr),
                )

    def __repr__(self):
        attrs = [f"{a}={repr(getattr(self, a))}," for a in self._attrs]
        attrs = indent("\n".join(attrs), "    ")
        return f"{self.__class__.__name__}(\n{attrs}\n)"


class SourceDescriptor(SimpleDescriptor):
    """Simple container for data related to the source

    .. code:: python

        doc = DesignSpaceDocument()
        s1 = SourceDescriptor()
        s1.path = masterPath1
        s1.name = "master.ufo1"
        s1.font = defcon.Font("master.ufo1")
        s1.location = dict(weight=0)
        s1.familyName = "MasterFamilyName"
        s1.styleName = "MasterStyleNameOne"
        s1.localisedFamilyName = dict(fr="Caractère")
        s1.mutedGlyphNames.append("A")
        s1.mutedGlyphNames.append("Z")
        doc.addSource(s1)

    """

    flavor = "source"
    _attrs = [
        "filename",
        "path",
        "name",
        "layerName",
        "location",
        "copyLib",
        "copyGroups",
        "copyFeatures",
        "muteKerning",
        "muteInfo",
        "mutedGlyphNames",
        "familyName",
        "styleName",
        "localisedFamilyName",
    ]

    filename = posixpath_property("_filename")
    path = posixpath_property("_path")

    def __init__(
        self,
        *,
        filename=None,
        path=None,
        font=None,
        name=None,
        location=None,
        designLocation=None,
        layerName=None,
        familyName=None,
        styleName=None,
        localisedFamilyName=None,
        copyLib=False,
        copyInfo=False,
        copyGroups=False,
        copyFeatures=False,
        muteKerning=False,
        muteInfo=False,
        mutedGlyphNames=None,
    ):
        self.filename = filename
        """string. A relative path to the source file, **as it is in the document**.

        MutatorMath + VarLib.
        """
        self.path = path
        """The absolute path, calculated from filename."""

        self.font = font
        """Any Python object. Optional. Points to a representation of this
        source font that is loaded in memory, as a Python object (e.g. a
        ``defcon.Font`` or a ``fontTools.ttFont.TTFont``).

        The default document reader will not fill-in this attribute, and the
        default writer will not use this attribute. It is up to the user of
        ``designspaceLib`` to either load the resource identified by
        ``filename`` and store it in this field, or write the contents of
        this field to the disk and make ```filename`` point to that.
        """

        self.name = name
        """string. Optional. Unique identifier name for this source.

        MutatorMath + varLib.
        """

        self.designLocation = (
            designLocation if designLocation is not None else location or {}
        )
        """dict. Axis values for this source, in design space coordinates.

        MutatorMath + varLib.

        This may be only part of the full design location.
        See :meth:`getFullDesignLocation()`

        .. versionadded:: 5.0
        """

        self.layerName = layerName
        """string. The name of the layer in the source to look for
        outline data. Default ``None`` which means ``foreground``.
        """
        self.familyName = familyName
        """string. Family name of this source. Though this data
        can be extracted from the font, it can be efficient to have it right
        here.

        varLib.
        """
        self.styleName = styleName
        """string. Style name of this source. Though this data
        can be extracted from the font, it can be efficient to have it right
        here.

        varLib.
        """
        self.localisedFamilyName = localisedFamilyName or {}
        """dict. A dictionary of localised family name strings, keyed by
        language code.

        If present, will be used to build localized names for all instances.

        .. versionadded:: 5.0
        """

        self.copyLib = copyLib
        """bool. Indicates if the contents of the font.lib need to
        be copied to the instances.

        MutatorMath.

        .. deprecated:: 5.0
        """
        self.copyInfo = copyInfo
        """bool. Indicates if the non-interpolating font.info needs
        to be copied to the instances.

        MutatorMath.

        .. deprecated:: 5.0
        """
        self.copyGroups = copyGroups
        """bool. Indicates if the groups need to be copied to the
        instances.

        MutatorMath.

        .. deprecated:: 5.0
        """
        self.copyFeatures = copyFeatures
        """bool. Indicates if the feature text needs to be
        copied to the instances.

        MutatorMath.

        .. deprecated:: 5.0
        """
        self.muteKerning = muteKerning
        """bool. Indicates if the kerning data from this source
        needs to be muted (i.e. not be part of the calculations).

        MutatorMath only.
        """
        self.muteInfo = muteInfo
        """bool. Indicated if the interpolating font.info data for
        this source needs to be muted.

        MutatorMath only.
        """
        self.mutedGlyphNames = mutedGlyphNames or []
        """list. Glyphnames that need to be muted in the
        instances.

        MutatorMath only.
        """

    @property
    def location(self):
        """dict. Axis values for this source, in design space coordinates.

        MutatorMath + varLib.

        .. deprecated:: 5.0
           Use the more explicit alias for this property :attr:`designLocation`.
        """
        return self.designLocation

    @location.setter
    def location(self, location: Optional[SimpleLocationDict]):
        self.designLocation = location or {}

    def setFamilyName(self, familyName, languageCode="en"):
        """Setter for :attr:`localisedFamilyName`

        .. versionadded:: 5.0
        """
        self.localisedFamilyName[languageCode] = tostr(familyName)

    def getFamilyName(self, languageCode="en"):
        """Getter for :attr:`localisedFamilyName`

        .. versionadded:: 5.0
        """
        return self.localisedFamilyName.get(languageCode)

    def getFullDesignLocation(self, doc: "DesignSpaceDocument") -> SimpleLocationDict:
        """Get the complete design location of this source, from its
        :attr:`designLocation` and the document's axis defaults.

        .. versionadded:: 5.0
        """
        result: SimpleLocationDict = {}
        for axis in doc.axes:
            if axis.name in self.designLocation:
                result[axis.name] = self.designLocation[axis.name]
            else:
                result[axis.name] = axis.map_forward(axis.default)
        return result


class RuleDescriptor(SimpleDescriptor):
    """Represents the rule descriptor element: a set of glyph substitutions to
    trigger conditionally in some parts of the designspace.

    .. code:: python

        r1 = RuleDescriptor()
        r1.name = "unique.rule.name"
        r1.conditionSets.append([dict(name="weight", minimum=-10, maximum=10), dict(...)])
        r1.conditionSets.append([dict(...), dict(...)])
        r1.subs.append(("a", "a.alt"))

    .. code:: xml

        <!-- optional: list of substitution rules -->
        <rules>
            <rule name="vertical.bars">
                <conditionset>
                    <condition minimum="250.000000" maximum="750.000000" name="weight"/>
                    <condition minimum="100" name="width"/>
                    <condition minimum="10" maximum="40" name="optical"/>
                </conditionset>
                <sub name="cent" with="cent.alt"/>
                <sub name="dollar" with="dollar.alt"/>
            </rule>
        </rules>
    """

    _attrs = ["name", "conditionSets", "subs"]  # what do we need here

    def __init__(self, *, name=None, conditionSets=None, subs=None):
        self.name = name
        """string. Unique name for this rule. Can be used to reference this rule data."""
        # list of lists of dict(name='aaaa', minimum=0, maximum=1000)
        self.conditionSets = conditionSets or []
        """a list of conditionsets.

        -  Each conditionset is a list of conditions.
        -  Each condition is a dict with ``name``, ``minimum`` and ``maximum`` keys.
        """
        # list of substitutions stored as tuples of glyphnames ("a", "a.alt")
        self.subs = subs or []
        """list of substitutions.

        -  Each substitution is stored as tuples of glyphnames, e.g. ("a", "a.alt").
        -  Note: By default, rules are applied first, before other text
           shaping/OpenType layout, as they are part of the
           `Required Variation Alternates OpenType feature <https://docs.microsoft.com/en-us/typography/opentype/spec/features_pt#-tag-rvrn>`_.
           See ref:`rules-element` § Attributes.
        """


def evaluateRule(rule, location):
    """Return True if any of the rule's conditionsets matches the given location."""
    return any(evaluateConditions(c, location) for c in rule.conditionSets)


def evaluateConditions(conditions, location):
    """Return True if all the conditions matches the given location.

    - If a condition has no minimum, check for < maximum.
    - If a condition has no maximum, check for > minimum.
    """
    for cd in conditions:
        value = location[cd["name"]]
        if cd.get("minimum") is None:
            if value > cd["maximum"]:
                return False
        elif cd.get("maximum") is None:
            if cd["minimum"] > value:
                return False
        elif not cd["minimum"] <= value <= cd["maximum"]:
            return False
    return True


def processRules(rules, location, glyphNames):
    """Apply these rules at this location to these glyphnames.

    Return a new list of glyphNames with substitutions applied.

    - rule order matters
    """
    newNames = []
    for rule in rules:
        if evaluateRule(rule, location):
            for name in glyphNames:
                swap = False
                for a, b in rule.subs:
                    if name == a:
                        swap = True
                        break
                if swap:
                    newNames.append(b)
                else:
                    newNames.append(name)
            glyphNames = newNames
            newNames = []
    return glyphNames


AnisotropicLocationDict = Dict[str, Union[float, Tuple[float, float]]]
SimpleLocationDict = Dict[str, float]


class AxisMappingDescriptor(SimpleDescriptor):
    """Represents the axis mapping element: mapping an input location
    to an output location in the designspace.

    .. code:: python

        m1 = AxisMappingDescriptor()
        m1.inputLocation = {"weight": 900, "width": 150}
        m1.outputLocation = {"weight": 870}

    .. code:: xml

        <mappings>
            <mapping>
                <input>
                    <dimension name="weight" xvalue="900"/>
                    <dimension name="width" xvalue="150"/>
                </input>
                <output>
                    <dimension name="weight" xvalue="870"/>
                </output>
            </mapping>
        </mappings>
    """

    _attrs = ["inputLocation", "outputLocation"]

    def __init__(
        self,
        *,
        inputLocation=None,
        outputLocation=None,
        description=None,
        groupDescription=None,
    ):
        self.inputLocation: SimpleLocationDict = inputLocation or {}
        """dict. Axis values for the input of the mapping, in design space coordinates.

        varLib.

        .. versionadded:: 5.1
        """
        self.outputLocation: SimpleLocationDict = outputLocation or {}
        """dict. Axis values for the output of the mapping, in design space coordinates.

        varLib.

        .. versionadded:: 5.1
        """
        self.description = description
        """string. A description of the mapping.

        varLib.

        .. versionadded:: 5.2
        """
        self.groupDescription = groupDescription
        """string. A description of the group of mappings.

        varLib.

        .. versionadded:: 5.2
        """


class InstanceDescriptor(SimpleDescriptor):
    """Simple container for data related to the instance


    .. code:: python

        i2 = InstanceDescriptor()
        i2.path = instancePath2
        i2.familyName = "InstanceFamilyName"
        i2.styleName = "InstanceStyleName"
        i2.name = "instance.ufo2"
        # anisotropic location
        i2.designLocation = dict(weight=500, width=(400,300))
        i2.postScriptFontName = "InstancePostscriptName"
        i2.styleMapFamilyName = "InstanceStyleMapFamilyName"
        i2.styleMapStyleName = "InstanceStyleMapStyleName"
        i2.lib['com.coolDesignspaceApp.specimenText'] = 'Hamburgerwhatever'
        doc.addInstance(i2)
    """

    flavor = "instance"
    _defaultLanguageCode = "en"
    _attrs = [
        "filename",
        "path",
        "name",
        "locationLabel",
        "designLocation",
        "userLocation",
        "familyName",
        "styleName",
        "postScriptFontName",
        "styleMapFamilyName",
        "styleMapStyleName",
        "localisedFamilyName",
        "localisedStyleName",
        "localisedStyleMapFamilyName",
        "localisedStyleMapStyleName",
        "glyphs",
        "kerning",
        "info",
        "lib",
    ]

    filename = posixpath_property("_filename")
    path = posixpath_property("_path")

    def __init__(
        self,
        *,
        filename=None,
        path=None,
        font=None,
        name=None,
        location=None,
        locationLabel=None,
        designLocation=None,
        userLocation=None,
        familyName=None,
        styleName=None,
        postScriptFontName=None,
        styleMapFamilyName=None,
        styleMapStyleName=None,
        localisedFamilyName=None,
        localisedStyleName=None,
        localisedStyleMapFamilyName=None,
        localisedStyleMapStyleName=None,
        glyphs=None,
        kerning=True,
        info=True,
        lib=None,
    ):
        self.filename = filename
        """string. Relative path to the instance file, **as it is
        in the document**. The file may or may not exist.

        MutatorMath + VarLib.
        """
        self.path = path
        """string. Absolute path to the instance file, calculated from
        the document path and the string in the filename attr. The file may
        or may not exist.

        MutatorMath.
        """
        self.font = font
        """Same as :attr:`SourceDescriptor.font`

        .. seealso:: :attr:`SourceDescriptor.font`
        """
        self.name = name
        """string. Unique identifier name of the instance, used to
        identify it if it needs to be referenced from elsewhere in the
        document.
        """
        self.locationLabel = locationLabel
        """Name of a :class:`LocationLabelDescriptor`. If
        provided, the instance should have the same location as the
        LocationLabel.

        .. seealso::
           :meth:`getFullDesignLocation`
           :meth:`getFullUserLocation`

        .. versionadded:: 5.0
        """
        self.designLocation: AnisotropicLocationDict = (
            designLocation if designLocation is not None else (location or {})
        )
        """dict. Axis values for this instance, in design space coordinates.

        MutatorMath + varLib.

        .. seealso:: This may be only part of the full location. See:
           :meth:`getFullDesignLocation`
           :meth:`getFullUserLocation`

        .. versionadded:: 5.0
        """
        self.userLocation: SimpleLocationDict = userLocation or {}
        """dict. Axis values for this instance, in user space coordinates.

        MutatorMath + varLib.

        .. seealso:: This may be only part of the full location. See:
           :meth:`getFullDesignLocation`
           :meth:`getFullUserLocation`

        .. versionadded:: 5.0
        """
        self.familyName = familyName
        """string. Family name of this instance.

        MutatorMath + varLib.
        """
        self.styleName = styleName
        """string. Style name of this instance.

        MutatorMath + varLib.
        """
        self.postScriptFontName = postScriptFontName
        """string. Postscript fontname for this instance.

        MutatorMath + varLib.
        """
        self.styleMapFamilyName = styleMapFamilyName
        """string. StyleMap familyname for this instance.

        MutatorMath + varLib.
        """
        self.styleMapStyleName = styleMapStyleName
        """string. StyleMap stylename for this instance.

        MutatorMath + varLib.
        """
        self.localisedFamilyName = localisedFamilyName or {}
        """dict. A dictionary of localised family name
        strings, keyed by language code.
        """
        self.localisedStyleName = localisedStyleName or {}
        """dict. A dictionary of localised stylename
        strings, keyed by language code.
        """
        self.localisedStyleMapFamilyName = localisedStyleMapFamilyName or {}
        """A dictionary of localised style map
        familyname strings, keyed by language code.
        """
        self.localisedStyleMapStyleName = localisedStyleMapStyleName or {}
        """A dictionary of localised style map
        stylename strings, keyed by language code.
        """
        self.glyphs = glyphs or {}
        """dict for special master definitions for glyphs. If glyphs
        need special masters (to record the results of executed rules for
        example).

        MutatorMath.

        .. deprecated:: 5.0
            Use rules or sparse sources instead.
        """
        self.kerning = kerning
        """ bool. Indicates if this instance needs its kerning
        calculated.

        MutatorMath.

        .. deprecated:: 5.0
        """
        self.info = info
        """bool. Indicated if this instance needs the interpolating
        font.info calculated.

        .. deprecated:: 5.0
        """

        self.lib = lib or {}
        """Custom data associated with this instance."""

    @property
    def location(self):
        """dict. Axis values for this instance.

        MutatorMath + varLib.

        .. deprecated:: 5.0
           Use the more explicit alias for this property :attr:`designLocation`.
        """
        return self.designLocation

    @location.setter
    def location(self, location: Optional[AnisotropicLocationDict]):
        self.designLocation = location or {}

    def setStyleName(self, styleName, languageCode="en"):
        """These methods give easier access to the localised names."""
        self.localisedStyleName[languageCode] = tostr(styleName)

    def getStyleName(self, languageCode="en"):
        return self.localisedStyleName.get(languageCode)

    def setFamilyName(self, familyName, languageCode="en"):
        self.localisedFamilyName[languageCode] = tostr(familyName)

    def getFamilyName(self, languageCode="en"):
        return self.localisedFamilyName.get(languageCode)

    def setStyleMapStyleName(self, styleMapStyleName, languageCode="en"):
        self.localisedStyleMapStyleName[languageCode] = tostr(styleMapStyleName)

    def getStyleMapStyleName(self, languageCode="en"):
        return self.localisedStyleMapStyleName.get(languageCode)

    def setStyleMapFamilyName(self, styleMapFamilyName, languageCode="en"):
        self.localisedStyleMapFamilyName[languageCode] = tostr(styleMapFamilyName)

    def getStyleMapFamilyName(self, languageCode="en"):
        return self.localisedStyleMapFamilyName.get(languageCode)

    def clearLocation(self, axisName: Optional[str] = None):
        """Clear all location-related fields. Ensures that
        :attr:``designLocation`` and :attr:``userLocation`` are dictionaries
        (possibly empty if clearing everything).

        In order to update the location of this instance wholesale, a user
        should first clear all the fields, then change the field(s) for which
        they have data.

        .. code:: python

            instance.clearLocation()
            instance.designLocation = {'Weight': (34, 36.5), 'Width': 100}
            instance.userLocation = {'Opsz': 16}

        In order to update a single axis location, the user should only clear
        that axis, then edit the values:

        .. code:: python

            instance.clearLocation('Weight')
            instance.designLocation['Weight'] = (34, 36.5)

        Args:
          axisName: if provided, only clear the location for that axis.

        .. versionadded:: 5.0
        """
        self.locationLabel = None
        if axisName is None:
            self.designLocation = {}
            self.userLocation = {}
        else:
            if self.designLocation is None:
                self.designLocation = {}
            if axisName in self.designLocation:
                del self.designLocation[axisName]
            if self.userLocation is None:
                self.userLocation = {}
            if axisName in self.userLocation:
                del self.userLocation[axisName]

    def getLocationLabelDescriptor(
        self, doc: "DesignSpaceDocument"
    ) -> Optional[LocationLabelDescriptor]:
        """Get the :class:`LocationLabelDescriptor` instance that matches
        this instances's :attr:`locationLabel`.

        Raises if the named label can't be found.

        .. versionadded:: 5.0
        """
        if self.locationLabel is None:
            return None
        label = doc.getLocationLabel(self.locationLabel)
        if label is None:
            raise DesignSpaceDocumentError(
                "InstanceDescriptor.getLocationLabelDescriptor(): "
                f"unknown location label `{self.locationLabel}` in instance `{self.name}`."
            )
        return label

    def getFullDesignLocation(
        self, doc: "DesignSpaceDocument"
    ) -> AnisotropicLocationDict:
        """Get the complete design location of this instance, by combining data
        from the various location fields, default axis values and mappings, and
        top-level location labels.

        The source of truth for this instance's location is determined for each
        axis independently by taking the first not-None field in this list:

        - ``locationLabel``: the location along this axis is the same as the
          matching STAT format 4 label. No anisotropy.
        - ``designLocation[axisName]``: the explicit design location along this
          axis, possibly anisotropic.
        - ``userLocation[axisName]``: the explicit user location along this
          axis. No anisotropy.
        - ``axis.default``: default axis value. No anisotropy.

        .. versionadded:: 5.0
        """
        label = self.getLocationLabelDescriptor(doc)
        if label is not None:
            return doc.map_forward(label.userLocation)  # type: ignore
        result: AnisotropicLocationDict = {}
        for axis in doc.axes:
            if axis.name in self.designLocation:
                result[axis.name] = self.designLocation[axis.name]
            elif axis.name in self.userLocation:
                result[axis.name] = axis.map_forward(self.userLocation[axis.name])
            else:
                result[axis.name] = axis.map_forward(axis.default)
        return result

    def getFullUserLocation(self, doc: "DesignSpaceDocument") -> SimpleLocationDict:
        """Get the complete user location for this instance.

        .. seealso:: :meth:`getFullDesignLocation`

        .. versionadded:: 5.0
        """
        return doc.map_backward(self.getFullDesignLocation(doc))


def tagForAxisName(name):
    # try to find or make a tag name for this axis name
    names = {
        "weight": ("wght", dict(en="Weight")),
        "width": ("wdth", dict(en="Width")),
        "optical": ("opsz", dict(en="Optical Size")),
        "slant": ("slnt", dict(en="Slant")),
        "italic": ("ital", dict(en="Italic")),
    }
    if name.lower() in names:
        return names[name.lower()]
    if len(name) < 4:
        tag = name + "*" * (4 - len(name))
    else:
        tag = name[:4]
    return tag, dict(en=name)


class AbstractAxisDescriptor(SimpleDescriptor):
    flavor = "axis"

    def __init__(
        self,
        *,
        tag=None,
        name=None,
        labelNames=None,
        hidden=False,
        map=None,
        axisOrdering=None,
        axisLabels=None,
    ):
        # opentype tag for this axis
        self.tag = tag
        """string. Four letter tag for this axis. Some might be
        registered at the `OpenType
        specification <https://www.microsoft.com/typography/otspec/fvar.htm#VAT>`__.
        Privately-defined axis tags must begin with an uppercase letter and
        use only uppercase letters or digits.
        """
        # name of the axis used in locations
        self.name = name
        """string. Name of the axis as it is used in the location dicts.

        MutatorMath + varLib.
        """
        # names for UI purposes, if this is not a standard axis,
        self.labelNames = labelNames or {}
        """dict. When defining a non-registered axis, it will be
        necessary to define user-facing readable names for the axis. Keyed by
        xml:lang code. Values are required to be ``unicode`` strings, even if
        they only contain ASCII characters.
        """
        self.hidden = hidden
        """bool. Whether this axis should be hidden in user interfaces.
        """
        self.map = map or []
        """list of input / output values that can describe a warp of user space
        to design space coordinates. If no map values are present, it is assumed
        user space is the same as design space, as in [(minimum, minimum),
        (maximum, maximum)].

        varLib.
        """
        self.axisOrdering = axisOrdering
        """STAT table field ``axisOrdering``.

        See: `OTSpec STAT Axis Record <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-records>`_

        .. versionadded:: 5.0
        """
        self.axisLabels: List[AxisLabelDescriptor] = axisLabels or []
        """STAT table entries for Axis Value Tables format 1, 2, 3.

        See: `OTSpec STAT Axis Value Tables <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-value-tables>`_

        .. versionadded:: 5.0
        """


class AxisDescriptor(AbstractAxisDescriptor):
    """Simple container for the axis data.

    Add more localisations?

    .. code:: python

        a1 = AxisDescriptor()
        a1.minimum = 1
        a1.maximum = 1000
        a1.default = 400
        a1.name = "weight"
        a1.tag = "wght"
        a1.labelNames['fa-IR'] = "قطر"
        a1.labelNames['en'] = "Wéíght"
        a1.map = [(1.0, 10.0), (400.0, 66.0), (1000.0, 990.0)]
        a1.axisOrdering = 1
        a1.axisLabels = [
            AxisLabelDescriptor(name="Regular", userValue=400, elidable=True)
        ]
        doc.addAxis(a1)
    """

    _attrs = [
        "tag",
        "name",
        "maximum",
        "minimum",
        "default",
        "map",
        "axisOrdering",
        "axisLabels",
    ]

    def __init__(
        self,
        *,
        tag=None,
        name=None,
        labelNames=None,
        minimum=None,
        default=None,
        maximum=None,
        hidden=False,
        map=None,
        axisOrdering=None,
        axisLabels=None,
    ):
        super().__init__(
            tag=tag,
            name=name,
            labelNames=labelNames,
            hidden=hidden,
            map=map,
            axisOrdering=axisOrdering,
            axisLabels=axisLabels,
        )
        self.minimum = minimum
        """number. The minimum value for this axis in user space.

        MutatorMath + varLib.
        """
        self.maximum = maximum
        """number. The maximum value for this axis in user space.

        MutatorMath + varLib.
        """
        self.default = default
        """number. The default value for this axis, i.e. when a new location is
        created, this is the value this axis will get in user space.

        MutatorMath + varLib.
        """

    def serialize(self):
        # output to a dict, used in testing
        return dict(
            tag=self.tag,
            name=self.name,
            labelNames=self.labelNames,
            maximum=self.maximum,
            minimum=self.minimum,
            default=self.default,
            hidden=self.hidden,
            map=self.map,
            axisOrdering=self.axisOrdering,
            axisLabels=self.axisLabels,
        )

    def map_forward(self, v):
        """Maps value from axis mapping's input (user) to output (design)."""
        from fontTools.varLib.models import piecewiseLinearMap

        if not self.map:
            return v
        return piecewiseLinearMap(v, {k: v for k, v in self.map})

    def map_backward(self, v):
        """Maps value from axis mapping's output (design) to input (user)."""
        from fontTools.varLib.models import piecewiseLinearMap

        if isinstance(v, tuple):
            v = v[0]
        if not self.map:
            return v
        return piecewiseLinearMap(v, {v: k for k, v in self.map})


class DiscreteAxisDescriptor(AbstractAxisDescriptor):
    """Container for discrete axis data.

    Use this for axes that do not interpolate. The main difference from a
    continuous axis is that a continuous axis has a ``minimum`` and ``maximum``,
    while a discrete axis has a list of ``values``.

    Example: an Italic axis with 2 stops, Roman and Italic, that are not
    compatible. The axis still allows to bind together the full font family,
    which is useful for the STAT table, however it can't become a variation
    axis in a VF.

    .. code:: python

        a2 = DiscreteAxisDescriptor()
        a2.values = [0, 1]
        a2.default = 0
        a2.name = "Italic"
        a2.tag = "ITAL"
        a2.labelNames['fr'] = "Italique"
        a2.map = [(0, 0), (1, -11)]
        a2.axisOrdering = 2
        a2.axisLabels = [
            AxisLabelDescriptor(name="Roman", userValue=0, elidable=True)
        ]
        doc.addAxis(a2)

    .. versionadded:: 5.0
    """

    flavor = "axis"
    _attrs = ("tag", "name", "values", "default", "map", "axisOrdering", "axisLabels")

    def __init__(
        self,
        *,
        tag=None,
        name=None,
        labelNames=None,
        values=None,
        default=None,
        hidden=False,
        map=None,
        axisOrdering=None,
        axisLabels=None,
    ):
        super().__init__(
            tag=tag,
            name=name,
            labelNames=labelNames,
            hidden=hidden,
            map=map,
            axisOrdering=axisOrdering,
            axisLabels=axisLabels,
        )
        self.default: float = default
        """The default value for this axis, i.e. when a new location is
        created, this is the value this axis will get in user space.

        However, this default value is less important than in continuous axes:

        -  it doesn't define the "neutral" version of outlines from which
           deltas would apply, as this axis does not interpolate.
        -  it doesn't provide the reference glyph set for the designspace, as
           fonts at each value can have different glyph sets.
        """
        self.values: List[float] = values or []
        """List of possible values for this axis. Contrary to continuous axes,
        only the values in this list can be taken by the axis, nothing in-between.
        """

    def map_forward(self, value):
        """Maps value from axis mapping's input to output.

        Returns value unchanged if no mapping entry is found.

        Note: for discrete axes, each value must have its mapping entry, if
        you intend that value to be mapped.
        """
        return next((v for k, v in self.map if k == value), value)

    def map_backward(self, value):
        """Maps value from axis mapping's output to input.

        Returns value unchanged if no mapping entry is found.

        Note: for discrete axes, each value must have its mapping entry, if
        you intend that value to be mapped.
        """
        if isinstance(value, tuple):
            value = value[0]
        return next((k for k, v in self.map if v == value), value)


class AxisLabelDescriptor(SimpleDescriptor):
    """Container for axis label data.

    Analogue of OpenType's STAT data for a single axis (formats 1, 2 and 3).
    All values are user values.
    See: `OTSpec STAT Axis value table, format 1, 2, 3 <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-value-table-format-1>`_

    The STAT format of the Axis value depends on which field are filled-in,
    see :meth:`getFormat`

    .. versionadded:: 5.0
    """

    flavor = "label"
    _attrs = (
        "userMinimum",
        "userValue",
        "userMaximum",
        "name",
        "elidable",
        "olderSibling",
        "linkedUserValue",
        "labelNames",
    )

    def __init__(
        self,
        *,
        name,
        userValue,
        userMinimum=None,
        userMaximum=None,
        elidable=False,
        olderSibling=False,
        linkedUserValue=None,
        labelNames=None,
    ):
        self.userMinimum: Optional[float] = userMinimum
        """STAT field ``rangeMinValue`` (format 2)."""
        self.userValue: float = userValue
        """STAT field ``value`` (format 1, 3) or ``nominalValue`` (format 2)."""
        self.userMaximum: Optional[float] = userMaximum
        """STAT field ``rangeMaxValue`` (format 2)."""
        self.name: str = name
        """Label for this axis location, STAT field ``valueNameID``."""
        self.elidable: bool = elidable
        """STAT flag ``ELIDABLE_AXIS_VALUE_NAME``.

        See: `OTSpec STAT Flags <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#flags>`_
        """
        self.olderSibling: bool = olderSibling
        """STAT flag ``OLDER_SIBLING_FONT_ATTRIBUTE``.

        See: `OTSpec STAT Flags <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#flags>`_
        """
        self.linkedUserValue: Optional[float] = linkedUserValue
        """STAT field ``linkedValue`` (format 3)."""
        self.labelNames: MutableMapping[str, str] = labelNames or {}
        """User-facing translations of this location's label. Keyed by
        ``xml:lang`` code.
        """

    def getFormat(self) -> int:
        """Determine which format of STAT Axis value to use to encode this label.

        ===========  =========  ===========  ===========  ===============
        STAT Format  userValue  userMinimum  userMaximum  linkedUserValue
        ===========  =========  ===========  ===========  ===============
        1            ✅          ❌            ❌            ❌
        2            ✅          ✅            ✅            ❌
        3            ✅          ❌            ❌            ✅
        ===========  =========  ===========  ===========  ===============
        """
        if self.linkedUserValue is not None:
            return 3
        if self.userMinimum is not None or self.userMaximum is not None:
            return 2
        return 1

    @property
    def defaultName(self) -> str:
        """Return the English name from :attr:`labelNames` or the :attr:`name`."""
        return self.labelNames.get("en") or self.name


class LocationLabelDescriptor(SimpleDescriptor):
    """Container for location label data.

    Analogue of OpenType's STAT data for a free-floating location (format 4).
    All values are user values.

    See: `OTSpec STAT Axis value table, format 4 <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#axis-value-table-format-4>`_

    .. versionadded:: 5.0
    """

    flavor = "label"
    _attrs = ("name", "elidable", "olderSibling", "userLocation", "labelNames")

    def __init__(
        self,
        *,
        name,
        userLocation,
        elidable=False,
        olderSibling=False,
        labelNames=None,
    ):
        self.name: str = name
        """Label for this named location, STAT field ``valueNameID``."""
        self.userLocation: SimpleLocationDict = userLocation or {}
        """Location in user coordinates along each axis.

        If an axis is not mentioned, it is assumed to be at its default location.

        .. seealso:: This may be only part of the full location. See:
           :meth:`getFullUserLocation`
        """
        self.elidable: bool = elidable
        """STAT flag ``ELIDABLE_AXIS_VALUE_NAME``.

        See: `OTSpec STAT Flags <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#flags>`_
        """
        self.olderSibling: bool = olderSibling
        """STAT flag ``OLDER_SIBLING_FONT_ATTRIBUTE``.

        See: `OTSpec STAT Flags <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#flags>`_
        """
        self.labelNames: Dict[str, str] = labelNames or {}
        """User-facing translations of this location's label. Keyed by
        xml:lang code.
        """

    @property
    def defaultName(self) -> str:
        """Return the English name from :attr:`labelNames` or the :attr:`name`."""
        return self.labelNames.get("en") or self.name

    def getFullUserLocation(self, doc: "DesignSpaceDocument") -> SimpleLocationDict:
        """Get the complete user location of this label, by combining data
        from the explicit user location and default axis values.

        .. versionadded:: 5.0
        """
        return {
            axis.name: self.userLocation.get(axis.name, axis.default)
            for axis in doc.axes
        }


class VariableFontDescriptor(SimpleDescriptor):
    """Container for variable fonts, sub-spaces of the Designspace.

    Use-cases:

    - From a single DesignSpace with discrete axes, define 1 variable font
      per value on the discrete axes. Before version 5, you would have needed
      1 DesignSpace per such variable font, and a lot of data duplication.
    - From a big variable font with many axes, define subsets of that variable
      font that only include some axes and freeze other axes at a given location.

    .. versionadded:: 5.0
    """

    flavor = "variable-font"
    _attrs = ("filename", "axisSubsets", "lib")

    filename = posixpath_property("_filename")

    def __init__(self, *, name, filename=None, axisSubsets=None, lib=None):
        self.name: str = name
        """string, required. Name of this variable to identify it during the
        build process and from other parts of the document, and also as a
        filename in case the filename property is empty.

        VarLib.
        """
        self.filename: str = filename
        """string, optional. Relative path to the variable font file, **as it is
        in the document**. The file may or may not exist.

        If not specified, the :attr:`name` will be used as a basename for the file.
        """
        self.axisSubsets: List[
            Union[RangeAxisSubsetDescriptor, ValueAxisSubsetDescriptor]
        ] = (axisSubsets or [])
        """Axis subsets to include in this variable font.

        If an axis is not mentioned, assume that we only want the default
        location of that axis (same as a :class:`ValueAxisSubsetDescriptor`).
        """
        self.lib: MutableMapping[str, Any] = lib or {}
        """Custom data associated with this variable font."""


class RangeAxisSubsetDescriptor(SimpleDescriptor):
    """Subset of a continuous axis to include in a variable font.

    .. versionadded:: 5.0
    """

    flavor = "axis-subset"
    _attrs = ("name", "userMinimum", "userDefault", "userMaximum")

    def __init__(
        self, *, name, userMinimum=-math.inf, userDefault=None, userMaximum=math.inf
    ):
        self.name: str = name
        """Name of the :class:`AxisDescriptor` to subset."""
        self.userMinimum: float = userMinimum
        """New minimum value of the axis in the target variable font.
        If not specified, assume the same minimum value as the full axis.
        (default = ``-math.inf``)
        """
        self.userDefault: Optional[float] = userDefault
        """New default value of the axis in the target variable font.
        If not specified, assume the same default value as the full axis.
        (default = ``None``)
        """
        self.userMaximum: float = userMaximum
        """New maximum value of the axis in the target variable font.
        If not specified, assume the same maximum value as the full axis.
        (default = ``math.inf``)
        """


class ValueAxisSubsetDescriptor(SimpleDescriptor):
    """Single value of a discrete or continuous axis to use in a variable font.

    .. versionadded:: 5.0
    """

    flavor = "axis-subset"
    _attrs = ("name", "userValue")

    def __init__(self, *, name, userValue):
        self.name: str = name
        """Name of the :class:`AxisDescriptor` or :class:`DiscreteAxisDescriptor`
        to "snapshot" or "freeze".
        """
        self.userValue: float = userValue
        """Value in user coordinates at which to freeze the given axis."""


class BaseDocWriter(object):
    _whiteSpace = "    "
    axisDescriptorClass = AxisDescriptor
    discreteAxisDescriptorClass = DiscreteAxisDescriptor
    axisLabelDescriptorClass = AxisLabelDescriptor
    axisMappingDescriptorClass = AxisMappingDescriptor
    locationLabelDescriptorClass = LocationLabelDescriptor
    ruleDescriptorClass = RuleDescriptor
    sourceDescriptorClass = SourceDescriptor
    variableFontDescriptorClass = VariableFontDescriptor
    valueAxisSubsetDescriptorClass = ValueAxisSubsetDescriptor
    rangeAxisSubsetDescriptorClass = RangeAxisSubsetDescriptor
    instanceDescriptorClass = InstanceDescriptor

    @classmethod
    def getAxisDecriptor(cls):
        return cls.axisDescriptorClass()

    @classmethod
    def getAxisMappingDescriptor(cls):
        return cls.axisMappingDescriptorClass()

    @classmethod
    def getSourceDescriptor(cls):
        return cls.sourceDescriptorClass()

    @classmethod
    def getInstanceDescriptor(cls):
        return cls.instanceDescriptorClass()

    @classmethod
    def getRuleDescriptor(cls):
        return cls.ruleDescriptorClass()

    def __init__(self, documentPath, documentObject: DesignSpaceDocument):
        self.path = documentPath
        self.documentObject = documentObject
        self.effectiveFormatTuple = self._getEffectiveFormatTuple()
        self.root = ET.Element("designspace")

    def write(self, pretty=True, encoding="UTF-8", xml_declaration=True):
        self.root.attrib["format"] = ".".join(str(i) for i in self.effectiveFormatTuple)

        if (
            self.documentObject.axes
            or self.documentObject.axisMappings
            or self.documentObject.elidedFallbackName is not None
        ):
            axesElement = ET.Element("axes")
            if self.documentObject.elidedFallbackName is not None:
                axesElement.attrib["elidedfallbackname"] = (
                    self.documentObject.elidedFallbackName
                )
            self.root.append(axesElement)
        for axisObject in self.documentObject.axes:
            self._addAxis(axisObject)

        if self.documentObject.axisMappings:
            mappingsElement = None
            lastGroup = object()
            for mappingObject in self.documentObject.axisMappings:
                if getattr(mappingObject, "groupDescription", None) != lastGroup:
                    if mappingsElement is not None:
                        self.root.findall(".axes")[0].append(mappingsElement)
                    lastGroup = getattr(mappingObject, "groupDescription", None)
                    mappingsElement = ET.Element("mappings")
                    if lastGroup is not None:
                        mappingsElement.attrib["description"] = lastGroup
                self._addAxisMapping(mappingsElement, mappingObject)
            if mappingsElement is not None:
                self.root.findall(".axes")[0].append(mappingsElement)

        if self.documentObject.locationLabels:
            labelsElement = ET.Element("labels")
            for labelObject in self.documentObject.locationLabels:
                self._addLocationLabel(labelsElement, labelObject)
            self.root.append(labelsElement)

        if self.documentObject.rules:
            if getattr(self.documentObject, "rulesProcessingLast", False):
                attributes = {"processing": "last"}
            else:
                attributes = {}
            self.root.append(ET.Element("rules", attributes))
        for ruleObject in self.documentObject.rules:
            self._addRule(ruleObject)

        if self.documentObject.sources:
            self.root.append(ET.Element("sources"))
        for sourceObject in self.documentObject.sources:
            self._addSource(sourceObject)

        if self.documentObject.variableFonts:
            variableFontsElement = ET.Element("variable-fonts")
            for variableFont in self.documentObject.variableFonts:
                self._addVariableFont(variableFontsElement, variableFont)
            self.root.append(variableFontsElement)

        if self.documentObject.instances:
            self.root.append(ET.Element("instances"))
        for instanceObject in self.documentObject.instances:
            self._addInstance(instanceObject)

        if self.documentObject.lib:
            self._addLib(self.root, self.documentObject.lib, 2)

        tree = ET.ElementTree(self.root)
        tree.write(
            self.path,
            encoding=encoding,
            method="xml",
            xml_declaration=xml_declaration,
            pretty_print=pretty,
        )

    def _getEffectiveFormatTuple(self):
        """Try to use the version specified in the document, or a sufficiently
        recent version to be able to encode what the document contains.
        """
        minVersion = self.documentObject.formatTuple
        if (
            any(
                hasattr(axis, "values")
                or axis.axisOrdering is not None
                or axis.axisLabels
                for axis in self.documentObject.axes
            )
            or self.documentObject.locationLabels
            or any(source.localisedFamilyName for source in self.documentObject.sources)
            or self.documentObject.variableFonts
            or any(
                instance.locationLabel or instance.userLocation
                for instance in self.documentObject.instances
            )
        ):
            if minVersion < (5, 0):
                minVersion = (5, 0)
        if self.documentObject.axisMappings:
            if minVersion < (5, 1):
                minVersion = (5, 1)
        return minVersion

    def _makeLocationElement(self, locationObject, name=None):
        """Convert Location dict to a locationElement."""
        locElement = ET.Element("location")
        if name is not None:
            locElement.attrib["name"] = name
        validatedLocation = self.documentObject.newDefaultLocation()
        for axisName, axisValue in locationObject.items():
            if axisName in validatedLocation:
                # only accept values we know
                validatedLocation[axisName] = axisValue
        for dimensionName, dimensionValue in validatedLocation.items():
            dimElement = ET.Element("dimension")
            dimElement.attrib["name"] = dimensionName
            if type(dimensionValue) == tuple:
                dimElement.attrib["xvalue"] = self.intOrFloat(dimensionValue[0])
                dimElement.attrib["yvalue"] = self.intOrFloat(dimensionValue[1])
            else:
                dimElement.attrib["xvalue"] = self.intOrFloat(dimensionValue)
            locElement.append(dimElement)
        return locElement, validatedLocation

    def intOrFloat(self, num):
        if int(num) == num:
            return "%d" % num
        return ("%f" % num).rstrip("0").rstrip(".")

    def _addRule(self, ruleObject):
        # if none of the conditions have minimum or maximum values, do not add the rule.
        ruleElement = ET.Element("rule")
        if ruleObject.name is not None:
            ruleElement.attrib["name"] = ruleObject.name
        for conditions in ruleObject.conditionSets:
            conditionsetElement = ET.Element("conditionset")
            for cond in conditions:
                if cond.get("minimum") is None and cond.get("maximum") is None:
                    # neither is defined, don't add this condition
                    continue
                conditionElement = ET.Element("condition")
                conditionElement.attrib["name"] = cond.get("name")
                if cond.get("minimum") is not None:
                    conditionElement.attrib["minimum"] = self.intOrFloat(
                        cond.get("minimum")
                    )
                if cond.get("maximum") is not None:
                    conditionElement.attrib["maximum"] = self.intOrFloat(
                        cond.get("maximum")
                    )
                conditionsetElement.append(conditionElement)
            if len(conditionsetElement):
                ruleElement.append(conditionsetElement)
        for sub in ruleObject.subs:
            subElement = ET.Element("sub")
            subElement.attrib["name"] = sub[0]
            subElement.attrib["with"] = sub[1]
            ruleElement.append(subElement)
        if len(ruleElement):
            self.root.findall(".rules")[0].append(ruleElement)

    def _addAxis(self, axisObject):
        axisElement = ET.Element("axis")
        axisElement.attrib["tag"] = axisObject.tag
        axisElement.attrib["name"] = axisObject.name
        self._addLabelNames(axisElement, axisObject.labelNames)
        if axisObject.map:
            for inputValue, outputValue in axisObject.map:
                mapElement = ET.Element("map")
                mapElement.attrib["input"] = self.intOrFloat(inputValue)
                mapElement.attrib["output"] = self.intOrFloat(outputValue)
                axisElement.append(mapElement)
        if axisObject.axisOrdering is not None or axisObject.axisLabels:
            labelsElement = ET.Element("labels")
            if axisObject.axisOrdering is not None:
                labelsElement.attrib["ordering"] = str(axisObject.axisOrdering)
            for label in axisObject.axisLabels:
                self._addAxisLabel(labelsElement, label)
            axisElement.append(labelsElement)
        if hasattr(axisObject, "minimum"):
            axisElement.attrib["minimum"] = self.intOrFloat(axisObject.minimum)
            axisElement.attrib["maximum"] = self.intOrFloat(axisObject.maximum)
        elif hasattr(axisObject, "values"):
            axisElement.attrib["values"] = " ".join(
                self.intOrFloat(v) for v in axisObject.values
            )
        axisElement.attrib["default"] = self.intOrFloat(axisObject.default)
        if axisObject.hidden:
            axisElement.attrib["hidden"] = "1"
        self.root.findall(".axes")[0].append(axisElement)

    def _addAxisMapping(self, mappingsElement, mappingObject):
        mappingElement = ET.Element("mapping")
        if getattr(mappingObject, "description", None) is not None:
            mappingElement.attrib["description"] = mappingObject.description
        for what in ("inputLocation", "outputLocation"):
            whatObject = getattr(mappingObject, what, None)
            if whatObject is None:
                continue
            whatElement = ET.Element(what[:-8])
            mappingElement.append(whatElement)

            for name, value in whatObject.items():
                dimensionElement = ET.Element("dimension")
                dimensionElement.attrib["name"] = name
                dimensionElement.attrib["xvalue"] = self.intOrFloat(value)
                whatElement.append(dimensionElement)

        mappingsElement.append(mappingElement)

    def _addAxisLabel(
        self, axisElement: ET.Element, label: AxisLabelDescriptor
    ) -> None:
        labelElement = ET.Element("label")
        labelElement.attrib["uservalue"] = self.intOrFloat(label.userValue)
        if label.userMinimum is not None:
            labelElement.attrib["userminimum"] = self.intOrFloat(label.userMinimum)
        if label.userMaximum is not None:
            labelElement.attrib["usermaximum"] = self.intOrFloat(label.userMaximum)
        labelElement.attrib["name"] = label.name
        if label.elidable:
            labelElement.attrib["elidable"] = "true"
        if label.olderSibling:
            labelElement.attrib["oldersibling"] = "true"
        if label.linkedUserValue is not None:
            labelElement.attrib["linkeduservalue"] = self.intOrFloat(
                label.linkedUserValue
            )
        self._addLabelNames(labelElement, label.labelNames)
        axisElement.append(labelElement)

    def _addLabelNames(self, parentElement, labelNames):
        for languageCode, labelName in sorted(labelNames.items()):
            languageElement = ET.Element("labelname")
            languageElement.attrib[XML_LANG] = languageCode
            languageElement.text = labelName
            parentElement.append(languageElement)

    def _addLocationLabel(
        self, parentElement: ET.Element, label: LocationLabelDescriptor
    ) -> None:
        labelElement = ET.Element("label")
        labelElement.attrib["name"] = label.name
        if label.elidable:
            labelElement.attrib["elidable"] = "true"
        if label.olderSibling:
            labelElement.attrib["oldersibling"] = "true"
        self._addLabelNames(labelElement, label.labelNames)
        self._addLocationElement(labelElement, userLocation=label.userLocation)
        parentElement.append(labelElement)

    def _addLocationElement(
        self,
        parentElement,
        *,
        designLocation: AnisotropicLocationDict = None,
        userLocation: SimpleLocationDict = None,
    ):
        locElement = ET.Element("location")
        for axis in self.documentObject.axes:
            if designLocation is not None and axis.name in designLocation:
                dimElement = ET.Element("dimension")
                dimElement.attrib["name"] = axis.name
                value = designLocation[axis.name]
                if isinstance(value, tuple):
                    dimElement.attrib["xvalue"] = self.intOrFloat(value[0])
                    dimElement.attrib["yvalue"] = self.intOrFloat(value[1])
                else:
                    dimElement.attrib["xvalue"] = self.intOrFloat(value)
                locElement.append(dimElement)
            elif userLocation is not None and axis.name in userLocation:
                dimElement = ET.Element("dimension")
                dimElement.attrib["name"] = axis.name
                value = userLocation[axis.name]
                dimElement.attrib["uservalue"] = self.intOrFloat(value)
                locElement.append(dimElement)
        if len(locElement) > 0:
            parentElement.append(locElement)

    def _addInstance(self, instanceObject):
        instanceElement = ET.Element("instance")
        if instanceObject.name is not None:
            instanceElement.attrib["name"] = instanceObject.name
        if instanceObject.locationLabel is not None:
            instanceElement.attrib["location"] = instanceObject.locationLabel
        if instanceObject.familyName is not None:
            instanceElement.attrib["familyname"] = instanceObject.familyName
        if instanceObject.styleName is not None:
            instanceElement.attrib["stylename"] = instanceObject.styleName
        # add localisations
        if instanceObject.localisedStyleName:
            languageCodes = list(instanceObject.localisedStyleName.keys())
            languageCodes.sort()
            for code in languageCodes:
                if code == "en":
                    continue  # already stored in the element attribute
                localisedStyleNameElement = ET.Element("stylename")
                localisedStyleNameElement.attrib[XML_LANG] = code
                localisedStyleNameElement.text = instanceObject.getStyleName(code)
                instanceElement.append(localisedStyleNameElement)
        if instanceObject.localisedFamilyName:
            languageCodes = list(instanceObject.localisedFamilyName.keys())
            languageCodes.sort()
            for code in languageCodes:
                if code == "en":
                    continue  # already stored in the element attribute
                localisedFamilyNameElement = ET.Element("familyname")
                localisedFamilyNameElement.attrib[XML_LANG] = code
                localisedFamilyNameElement.text = instanceObject.getFamilyName(code)
                instanceElement.append(localisedFamilyNameElement)
        if instanceObject.localisedStyleMapStyleName:
            languageCodes = list(instanceObject.localisedStyleMapStyleName.keys())
            languageCodes.sort()
            for code in languageCodes:
                if code == "en":
                    continue
                localisedStyleMapStyleNameElement = ET.Element("stylemapstylename")
                localisedStyleMapStyleNameElement.attrib[XML_LANG] = code
                localisedStyleMapStyleNameElement.text = (
                    instanceObject.getStyleMapStyleName(code)
                )
                instanceElement.append(localisedStyleMapStyleNameElement)
        if instanceObject.localisedStyleMapFamilyName:
            languageCodes = list(instanceObject.localisedStyleMapFamilyName.keys())
            languageCodes.sort()
            for code in languageCodes:
                if code == "en":
                    continue
                localisedStyleMapFamilyNameElement = ET.Element("stylemapfamilyname")
                localisedStyleMapFamilyNameElement.attrib[XML_LANG] = code
                localisedStyleMapFamilyNameElement.text = (
                    instanceObject.getStyleMapFamilyName(code)
                )
                instanceElement.append(localisedStyleMapFamilyNameElement)

        if self.effectiveFormatTuple >= (5, 0):
            if instanceObject.locationLabel is None:
                self._addLocationElement(
                    instanceElement,
                    designLocation=instanceObject.designLocation,
                    userLocation=instanceObject.userLocation,
                )
        else:
            # Pre-version 5.0 code was validating and filling in the location
            # dict while writing it out, as preserved below.
            if instanceObject.location is not None:
                locationElement, instanceObject.location = self._makeLocationElement(
                    instanceObject.location
                )
                instanceElement.append(locationElement)
        if instanceObject.filename is not None:
            instanceElement.attrib["filename"] = instanceObject.filename
        if instanceObject.postScriptFontName is not None:
            instanceElement.attrib["postscriptfontname"] = (
                instanceObject.postScriptFontName
            )
        if instanceObject.styleMapFamilyName is not None:
            instanceElement.attrib["stylemapfamilyname"] = (
                instanceObject.styleMapFamilyName
            )
        if instanceObject.styleMapStyleName is not None:
            instanceElement.attrib["stylemapstylename"] = (
                instanceObject.styleMapStyleName
            )
        if self.effectiveFormatTuple < (5, 0):
            # Deprecated members as of version 5.0
            if instanceObject.glyphs:
                if instanceElement.findall(".glyphs") == []:
                    glyphsElement = ET.Element("glyphs")
                    instanceElement.append(glyphsElement)
                glyphsElement = instanceElement.findall(".glyphs")[0]
                for glyphName, data in sorted(instanceObject.glyphs.items()):
                    glyphElement = self._writeGlyphElement(
                        instanceElement, instanceObject, glyphName, data
                    )
                    glyphsElement.append(glyphElement)
            if instanceObject.kerning:
                kerningElement = ET.Element("kerning")
                instanceElement.append(kerningElement)
            if instanceObject.info:
                infoElement = ET.Element("info")
                instanceElement.append(infoElement)
        self._addLib(instanceElement, instanceObject.lib, 4)
        self.root.findall(".instances")[0].append(instanceElement)

    def _addSource(self, sourceObject):
        sourceElement = ET.Element("source")
        if sourceObject.filename is not None:
            sourceElement.attrib["filename"] = sourceObject.filename
        if sourceObject.name is not None:
            if sourceObject.name.find("temp_master") != 0:
                # do not save temporary source names
                sourceElement.attrib["name"] = sourceObject.name
        if sourceObject.familyName is not None:
            sourceElement.attrib["familyname"] = sourceObject.familyName
        if sourceObject.styleName is not None:
            sourceElement.attrib["stylename"] = sourceObject.styleName
        if sourceObject.layerName is not None:
            sourceElement.attrib["layer"] = sourceObject.layerName
        if sourceObject.localisedFamilyName:
            languageCodes = list(sourceObject.localisedFamilyName.keys())
            languageCodes.sort()
            for code in languageCodes:
                if code == "en":
                    continue  # already stored in the element attribute
                localisedFamilyNameElement = ET.Element("familyname")
                localisedFamilyNameElement.attrib[XML_LANG] = code
                localisedFamilyNameElement.text = sourceObject.getFamilyName(code)
                sourceElement.append(localisedFamilyNameElement)
        if sourceObject.copyLib:
            libElement = ET.Element("lib")
            libElement.attrib["copy"] = "1"
            sourceElement.append(libElement)
        if sourceObject.copyGroups:
            groupsElement = ET.Element("groups")
            groupsElement.attrib["copy"] = "1"
            sourceElement.append(groupsElement)
        if sourceObject.copyFeatures:
            featuresElement = ET.Element("features")
            featuresElement.attrib["copy"] = "1"
            sourceElement.append(featuresElement)
        if sourceObject.copyInfo or sourceObject.muteInfo:
            infoElement = ET.Element("info")
            if sourceObject.copyInfo:
                infoElement.attrib["copy"] = "1"
            if sourceObject.muteInfo:
                infoElement.attrib["mute"] = "1"
            sourceElement.append(infoElement)
        if sourceObject.muteKerning:
            kerningElement = ET.Element("kerning")
            kerningElement.attrib["mute"] = "1"
            sourceElement.append(kerningElement)
        if sourceObject.mutedGlyphNames:
            for name in sourceObject.mutedGlyphNames:
                glyphElement = ET.Element("glyph")
                glyphElement.attrib["name"] = name
                glyphElement.attrib["mute"] = "1"
                sourceElement.append(glyphElement)
        if self.effectiveFormatTuple >= (5, 0):
            self._addLocationElement(
                sourceElement, designLocation=sourceObject.location
            )
        else:
            # Pre-version 5.0 code was validating and filling in the location
            # dict while writing it out, as preserved below.
            locationElement, sourceObject.location = self._makeLocationElement(
                sourceObject.location
            )
            sourceElement.append(locationElement)
        self.root.findall(".sources")[0].append(sourceElement)

    def _addVariableFont(
        self, parentElement: ET.Element, vf: VariableFontDescriptor
    ) -> None:
        vfElement = ET.Element("variable-font")
        vfElement.attrib["name"] = vf.name
        if vf.filename is not None:
            vfElement.attrib["filename"] = vf.filename
        if vf.axisSubsets:
            subsetsElement = ET.Element("axis-subsets")
            for subset in vf.axisSubsets:
                subsetElement = ET.Element("axis-subset")
                subsetElement.attrib["name"] = subset.name
                # Mypy doesn't support narrowing union types via hasattr()
                # https://mypy.readthedocs.io/en/stable/type_narrowing.html
                # TODO(Python 3.10): use TypeGuard
                if hasattr(subset, "userMinimum"):
                    subset = cast(RangeAxisSubsetDescriptor, subset)
                    if subset.userMinimum != -math.inf:
                        subsetElement.attrib["userminimum"] = self.intOrFloat(
                            subset.userMinimum
                        )
                    if subset.userMaximum != math.inf:
                        subsetElement.attrib["usermaximum"] = self.intOrFloat(
                            subset.userMaximum
                        )
                    if subset.userDefault is not None:
                        subsetElement.attrib["userdefault"] = self.intOrFloat(
                            subset.userDefault
                        )
                elif hasattr(subset, "userValue"):
                    subset = cast(ValueAxisSubsetDescriptor, subset)
                    subsetElement.attrib["uservalue"] = self.intOrFloat(
                        subset.userValue
                    )
                subsetsElement.append(subsetElement)
            vfElement.append(subsetsElement)
        self._addLib(vfElement, vf.lib, 4)
        parentElement.append(vfElement)

    def _addLib(self, parentElement: ET.Element, data: Any, indent_level: int) -> None:
        if not data:
            return
        libElement = ET.Element("lib")
        libElement.append(plistlib.totree(data, indent_level=indent_level))
        parentElement.append(libElement)

    def _writeGlyphElement(self, instanceElement, instanceObject, glyphName, data):
        glyphElement = ET.Element("glyph")
        if data.get("mute"):
            glyphElement.attrib["mute"] = "1"
        if data.get("unicodes") is not None:
            glyphElement.attrib["unicode"] = " ".join(
                [hex(u) for u in data.get("unicodes")]
            )
        if data.get("instanceLocation") is not None:
            locationElement, data["instanceLocation"] = self._makeLocationElement(
                data.get("instanceLocation")
            )
            glyphElement.append(locationElement)
        if glyphName is not None:
            glyphElement.attrib["name"] = glyphName
        if data.get("note") is not None:
            noteElement = ET.Element("note")
            noteElement.text = data.get("note")
            glyphElement.append(noteElement)
        if data.get("masters") is not None:
            mastersElement = ET.Element("masters")
            for m in data.get("masters"):
                masterElement = ET.Element("master")
                if m.get("glyphName") is not None:
                    masterElement.attrib["glyphname"] = m.get("glyphName")
                if m.get("font") is not None:
                    masterElement.attrib["source"] = m.get("font")
                if m.get("location") is not None:
                    locationElement, m["location"] = self._makeLocationElement(
                        m.get("location")
                    )
                    masterElement.append(locationElement)
                mastersElement.append(masterElement)
            glyphElement.append(mastersElement)
        return glyphElement


class BaseDocReader(LogMixin):
    axisDescriptorClass = AxisDescriptor
    discreteAxisDescriptorClass = DiscreteAxisDescriptor
    axisLabelDescriptorClass = AxisLabelDescriptor
    axisMappingDescriptorClass = AxisMappingDescriptor
    locationLabelDescriptorClass = LocationLabelDescriptor
    ruleDescriptorClass = RuleDescriptor
    sourceDescriptorClass = SourceDescriptor
    variableFontsDescriptorClass = VariableFontDescriptor
    valueAxisSubsetDescriptorClass = ValueAxisSubsetDescriptor
    rangeAxisSubsetDescriptorClass = RangeAxisSubsetDescriptor
    instanceDescriptorClass = InstanceDescriptor

    def __init__(self, documentPath, documentObject):
        self.path = documentPath
        self.documentObject = documentObject
        tree = ET.parse(self.path)
        self.root = tree.getroot()
        self.documentObject.formatVersion = self.root.attrib.get("format", "3.0")
        self._axes = []
        self.rules = []
        self.sources = []
        self.instances = []
        self.axisDefaults = {}
        self._strictAxisNames = True

    @classmethod
    def fromstring(cls, string, documentObject):
        f = BytesIO(tobytes(string, encoding="utf-8"))
        self = cls(f, documentObject)
        self.path = None
        return self

    def read(self):
        self.readAxes()
        self.readLabels()
        self.readRules()
        self.readVariableFonts()
        self.readSources()
        self.readInstances()
        self.readLib()

    def readRules(self):
        # we also need to read any conditions that are outside of a condition set.
        rules = []
        rulesElement = self.root.find(".rules")
        if rulesElement is not None:
            processingValue = rulesElement.attrib.get("processing", "first")
            if processingValue not in {"first", "last"}:
                raise DesignSpaceDocumentError(
                    "<rules> processing attribute value is not valid: %r, "
                    "expected 'first' or 'last'" % processingValue
                )
            self.documentObject.rulesProcessingLast = processingValue == "last"
        for ruleElement in self.root.findall(".rules/rule"):
            ruleObject = self.ruleDescriptorClass()
            ruleName = ruleObject.name = ruleElement.attrib.get("name")
            # read any stray conditions outside a condition set
            externalConditions = self._readConditionElements(
                ruleElement,
                ruleName,
            )
            if externalConditions:
                ruleObject.conditionSets.append(externalConditions)
                self.log.info(
                    "Found stray rule conditions outside a conditionset. "
                    "Wrapped them in a new conditionset."
                )
            # read the conditionsets
            for conditionSetElement in ruleElement.findall(".conditionset"):
                conditionSet = self._readConditionElements(
                    conditionSetElement,
                    ruleName,
                )
                if conditionSet is not None:
                    ruleObject.conditionSets.append(conditionSet)
            for subElement in ruleElement.findall(".sub"):
                a = subElement.attrib["name"]
                b = subElement.attrib["with"]
                ruleObject.subs.append((a, b))
            rules.append(ruleObject)
        self.documentObject.rules = rules

    def _readConditionElements(self, parentElement, ruleName=None):
        cds = []
        for conditionElement in parentElement.findall(".condition"):
            cd = {}
            cdMin = conditionElement.attrib.get("minimum")
            if cdMin is not None:
                cd["minimum"] = float(cdMin)
            else:
                # will allow these to be None, assume axis.minimum
                cd["minimum"] = None
            cdMax = conditionElement.attrib.get("maximum")
            if cdMax is not None:
                cd["maximum"] = float(cdMax)
            else:
                # will allow these to be None, assume axis.maximum
                cd["maximum"] = None
            cd["name"] = conditionElement.attrib.get("name")
            # # test for things
            if cd.get("minimum") is None and cd.get("maximum") is None:
                raise DesignSpaceDocumentError(
                    "condition missing required minimum or maximum in rule"
                    + (" '%s'" % ruleName if ruleName is not None else "")
                )
            cds.append(cd)
        return cds

    def readAxes(self):
        # read the axes elements, including the warp map.
        axesElement = self.root.find(".axes")
        if axesElement is not None and "elidedfallbackname" in axesElement.attrib:
            self.documentObject.elidedFallbackName = axesElement.attrib[
                "elidedfallbackname"
            ]
        axisElements = self.root.findall(".axes/axis")
        if not axisElements:
            return
        for axisElement in axisElements:
            if (
                self.documentObject.formatTuple >= (5, 0)
                and "values" in axisElement.attrib
            ):
                axisObject = self.discreteAxisDescriptorClass()
                axisObject.values = [
                    float(s) for s in axisElement.attrib["values"].split(" ")
                ]
            else:
                axisObject = self.axisDescriptorClass()
                axisObject.minimum = float(axisElement.attrib.get("minimum"))
                axisObject.maximum = float(axisElement.attrib.get("maximum"))
            axisObject.default = float(axisElement.attrib.get("default"))
            axisObject.name = axisElement.attrib.get("name")
            if axisElement.attrib.get("hidden", False):
                axisObject.hidden = True
            axisObject.tag = axisElement.attrib.get("tag")
            for mapElement in axisElement.findall("map"):
                a = float(mapElement.attrib["input"])
                b = float(mapElement.attrib["output"])
                axisObject.map.append((a, b))
            for labelNameElement in axisElement.findall("labelname"):
                # Note: elementtree reads the "xml:lang" attribute name as
                # '{http://www.w3.org/XML/1998/namespace}lang'
                for key, lang in labelNameElement.items():
                    if key == XML_LANG:
                        axisObject.labelNames[lang] = tostr(labelNameElement.text)
            labelElement = axisElement.find(".labels")
            if labelElement is not None:
                if "ordering" in labelElement.attrib:
                    axisObject.axisOrdering = int(labelElement.attrib["ordering"])
                for label in labelElement.findall(".label"):
                    axisObject.axisLabels.append(self.readAxisLabel(label))
            self.documentObject.axes.append(axisObject)
            self.axisDefaults[axisObject.name] = axisObject.default

        self.documentObject.axisMappings = []
        for mappingsElement in self.root.findall(".axes/mappings"):
            groupDescription = mappingsElement.attrib.get("description")
            for mappingElement in mappingsElement.findall("mapping"):
                description = mappingElement.attrib.get("description")
                inputElement = mappingElement.find("input")
                outputElement = mappingElement.find("output")
                inputLoc = {}
                outputLoc = {}
                for dimElement in inputElement.findall(".dimension"):
                    name = dimElement.attrib["name"]
                    value = float(dimElement.attrib["xvalue"])
                    inputLoc[name] = value
                for dimElement in outputElement.findall(".dimension"):
                    name = dimElement.attrib["name"]
                    value = float(dimElement.attrib["xvalue"])
                    outputLoc[name] = value
                axisMappingObject = self.axisMappingDescriptorClass(
                    inputLocation=inputLoc,
                    outputLocation=outputLoc,
                    description=description,
                    groupDescription=groupDescription,
                )
                self.documentObject.axisMappings.append(axisMappingObject)

    def readAxisLabel(self, element: ET.Element):
        xml_attrs = {
            "userminimum",
            "uservalue",
            "usermaximum",
            "name",
            "elidable",
            "oldersibling",
            "linkeduservalue",
        }
        unknown_attrs = set(element.attrib) - xml_attrs
        if unknown_attrs:
            raise DesignSpaceDocumentError(
                f"label element contains unknown attributes: {', '.join(unknown_attrs)}"
            )

        name = element.get("name")
        if name is None:
            raise DesignSpaceDocumentError("label element must have a name attribute.")
        valueStr = element.get("uservalue")
        if valueStr is None:
            raise DesignSpaceDocumentError(
                "label element must have a uservalue attribute."
            )
        value = float(valueStr)
        minimumStr = element.get("userminimum")
        minimum = float(minimumStr) if minimumStr is not None else None
        maximumStr = element.get("usermaximum")
        maximum = float(maximumStr) if maximumStr is not None else None
        linkedValueStr = element.get("linkeduservalue")
        linkedValue = float(linkedValueStr) if linkedValueStr is not None else None
        elidable = True if element.get("elidable") == "true" else False
        olderSibling = True if element.get("oldersibling") == "true" else False
        labelNames = {
            lang: label_name.text or ""
            for label_name in element.findall("labelname")
            for attr, lang in label_name.items()
            if attr == XML_LANG
            # Note: elementtree reads the "xml:lang" attribute name as
            # '{http://www.w3.org/XML/1998/namespace}lang'
        }
        return self.axisLabelDescriptorClass(
            name=name,
            userValue=value,
            userMinimum=minimum,
            userMaximum=maximum,
            elidable=elidable,
            olderSibling=olderSibling,
            linkedUserValue=linkedValue,
            labelNames=labelNames,
        )

    def readLabels(self):
        if self.documentObject.formatTuple < (5, 0):
            return

        xml_attrs = {"name", "elidable", "oldersibling"}
        for labelElement in self.root.findall(".labels/label"):
            unknown_attrs = set(labelElement.attrib) - xml_attrs
            if unknown_attrs:
                raise DesignSpaceDocumentError(
                    f"Label element contains unknown attributes: {', '.join(unknown_attrs)}"
                )

            name = labelElement.get("name")
            if name is None:
                raise DesignSpaceDocumentError(
                    "label element must have a name attribute."
                )
            designLocation, userLocation = self.locationFromElement(labelElement)
            if designLocation:
                raise DesignSpaceDocumentError(
                    f'<label> element "{name}" must only have user locations (using uservalue="").'
                )
            elidable = True if labelElement.get("elidable") == "true" else False
            olderSibling = True if labelElement.get("oldersibling") == "true" else False
            labelNames = {
                lang: label_name.text or ""
                for label_name in labelElement.findall("labelname")
                for attr, lang in label_name.items()
                if attr == XML_LANG
                # Note: elementtree reads the "xml:lang" attribute name as
                # '{http://www.w3.org/XML/1998/namespace}lang'
            }
            locationLabel = self.locationLabelDescriptorClass(
                name=name,
                userLocation=userLocation,
                elidable=elidable,
                olderSibling=olderSibling,
                labelNames=labelNames,
            )
            self.documentObject.locationLabels.append(locationLabel)

    def readVariableFonts(self):
        if self.documentObject.formatTuple < (5, 0):
            return

        xml_attrs = {"name", "filename"}
        for variableFontElement in self.root.findall(".variable-fonts/variable-font"):
            unknown_attrs = set(variableFontElement.attrib) - xml_attrs
            if unknown_attrs:
                raise DesignSpaceDocumentError(
                    f"variable-font element contains unknown attributes: {', '.join(unknown_attrs)}"
                )

            name = variableFontElement.get("name")
            if name is None:
                raise DesignSpaceDocumentError(
                    "variable-font element must have a name attribute."
                )

            filename = variableFontElement.get("filename")

            axisSubsetsElement = variableFontElement.find(".axis-subsets")
            if axisSubsetsElement is None:
                raise DesignSpaceDocumentError(
                    "variable-font element must contain an axis-subsets element."
                )
            axisSubsets = []
            for axisSubset in axisSubsetsElement.iterfind(".axis-subset"):
                axisSubsets.append(self.readAxisSubset(axisSubset))

            lib = None
            libElement = variableFontElement.find(".lib")
            if libElement is not None:
                lib = plistlib.fromtree(libElement[0])

            variableFont = self.variableFontsDescriptorClass(
                name=name,
                filename=filename,
                axisSubsets=axisSubsets,
                lib=lib,
            )
            self.documentObject.variableFonts.append(variableFont)

    def readAxisSubset(self, element: ET.Element):
        if "uservalue" in element.attrib:
            xml_attrs = {"name", "uservalue"}
            unknown_attrs = set(element.attrib) - xml_attrs
            if unknown_attrs:
                raise DesignSpaceDocumentError(
                    f"axis-subset element contains unknown attributes: {', '.join(unknown_attrs)}"
                )

            name = element.get("name")
            if name is None:
                raise DesignSpaceDocumentError(
                    "axis-subset element must have a name attribute."
                )
            userValueStr = element.get("uservalue")
            if userValueStr is None:
                raise DesignSpaceDocumentError(
                    "The axis-subset element for a discrete subset must have a uservalue attribute."
                )
            userValue = float(userValueStr)

            return self.valueAxisSubsetDescriptorClass(name=name, userValue=userValue)
        else:
            xml_attrs = {"name", "userminimum", "userdefault", "usermaximum"}
            unknown_attrs = set(element.attrib) - xml_attrs
            if unknown_attrs:
                raise DesignSpaceDocumentError(
                    f"axis-subset element contains unknown attributes: {', '.join(unknown_attrs)}"
                )

            name = element.get("name")
            if name is None:
                raise DesignSpaceDocumentError(
                    "axis-subset element must have a name attribute."
                )

            userMinimum = element.get("userminimum")
            userDefault = element.get("userdefault")
            userMaximum = element.get("usermaximum")
            if (
                userMinimum is not None
                and userDefault is not None
                and userMaximum is not None
            ):
                return self.rangeAxisSubsetDescriptorClass(
                    name=name,
                    userMinimum=float(userMinimum),
                    userDefault=float(userDefault),
                    userMaximum=float(userMaximum),
                )
            if all(v is None for v in (userMinimum, userDefault, userMaximum)):
                return self.rangeAxisSubsetDescriptorClass(name=name)

            raise DesignSpaceDocumentError(
                "axis-subset element must have min/max/default values or none at all."
            )

    def readSources(self):
        for sourceCount, sourceElement in enumerate(
            self.root.findall(".sources/source")
        ):
            filename = sourceElement.attrib.get("filename")
            if filename is not None and self.path is not None:
                sourcePath = os.path.abspath(
                    os.path.join(os.path.dirname(self.path), filename)
                )
            else:
                sourcePath = None
            sourceName = sourceElement.attrib.get("name")
            if sourceName is None:
                # add a temporary source name
                sourceName = "temp_master.%d" % (sourceCount)
            sourceObject = self.sourceDescriptorClass()
            sourceObject.path = sourcePath  # absolute path to the ufo source
            sourceObject.filename = filename  # path as it is stored in the document
            sourceObject.name = sourceName
            familyName = sourceElement.attrib.get("familyname")
            if familyName is not None:
                sourceObject.familyName = familyName
            styleName = sourceElement.attrib.get("stylename")
            if styleName is not None:
                sourceObject.styleName = styleName
            for familyNameElement in sourceElement.findall("familyname"):
                for key, lang in familyNameElement.items():
                    if key == XML_LANG:
                        familyName = familyNameElement.text
                        sourceObject.setFamilyName(familyName, lang)
            designLocation, userLocation = self.locationFromElement(sourceElement)
            if userLocation:
                raise DesignSpaceDocumentError(
                    f'<source> element "{sourceName}" must only have design locations (using xvalue="").'
                )
            sourceObject.location = designLocation
            layerName = sourceElement.attrib.get("layer")
            if layerName is not None:
                sourceObject.layerName = layerName
            for libElement in sourceElement.findall(".lib"):
                if libElement.attrib.get("copy") == "1":
                    sourceObject.copyLib = True
            for groupsElement in sourceElement.findall(".groups"):
                if groupsElement.attrib.get("copy") == "1":
                    sourceObject.copyGroups = True
            for infoElement in sourceElement.findall(".info"):
                if infoElement.attrib.get("copy") == "1":
                    sourceObject.copyInfo = True
                if infoElement.attrib.get("mute") == "1":
                    sourceObject.muteInfo = True
            for featuresElement in sourceElement.findall(".features"):
                if featuresElement.attrib.get("copy") == "1":
                    sourceObject.copyFeatures = True
            for glyphElement in sourceElement.findall(".glyph"):
                glyphName = glyphElement.attrib.get("name")
                if glyphName is None:
                    continue
                if glyphElement.attrib.get("mute") == "1":
                    sourceObject.mutedGlyphNames.append(glyphName)
            for kerningElement in sourceElement.findall(".kerning"):
                if kerningElement.attrib.get("mute") == "1":
                    sourceObject.muteKerning = True
            self.documentObject.sources.append(sourceObject)

    def locationFromElement(self, element):
        """Read a nested ``<location>`` element inside the given ``element``.

        .. versionchanged:: 5.0
           Return a tuple of (designLocation, userLocation)
        """
        elementLocation = (None, None)
        for locationElement in element.findall(".location"):
            elementLocation = self.readLocationElement(locationElement)
            break
        return elementLocation

    def readLocationElement(self, locationElement):
        """Read a ``<location>`` element.

        .. versionchanged:: 5.0
           Return a tuple of (designLocation, userLocation)
        """
        if self._strictAxisNames and not self.documentObject.axes:
            raise DesignSpaceDocumentError("No axes defined")
        userLoc = {}
        designLoc = {}
        for dimensionElement in locationElement.findall(".dimension"):
            dimName = dimensionElement.attrib.get("name")
            if self._strictAxisNames and dimName not in self.axisDefaults:
                # In case the document contains no axis definitions,
                self.log.warning('Location with undefined axis: "%s".', dimName)
                continue
            userValue = xValue = yValue = None
            try:
                userValue = dimensionElement.attrib.get("uservalue")
                if userValue is not None:
                    userValue = float(userValue)
            except ValueError:
                self.log.warning(
                    "ValueError in readLocation userValue %3.3f", userValue
                )
            try:
                xValue = dimensionElement.attrib.get("xvalue")
                if xValue is not None:
                    xValue = float(xValue)
            except ValueError:
                self.log.warning("ValueError in readLocation xValue %3.3f", xValue)
            try:
                yValue = dimensionElement.attrib.get("yvalue")
                if yValue is not None:
                    yValue = float(yValue)
            except ValueError:
                self.log.warning("ValueError in readLocation yValue %3.3f", yValue)
            if userValue is None == xValue is None:
                raise DesignSpaceDocumentError(
                    f'Exactly one of uservalue="" or xvalue="" must be provided for location dimension "{dimName}"'
                )
            if yValue is not None:
                if xValue is None:
                    raise DesignSpaceDocumentError(
                        f'Missing xvalue="" for the location dimension "{dimName}"" with yvalue="{yValue}"'
                    )
                designLoc[dimName] = (xValue, yValue)
            elif xValue is not None:
                designLoc[dimName] = xValue
            else:
                userLoc[dimName] = userValue
        return designLoc, userLoc

    def readInstances(self, makeGlyphs=True, makeKerning=True, makeInfo=True):
        instanceElements = self.root.findall(".instances/instance")
        for instanceElement in instanceElements:
            self._readSingleInstanceElement(
                instanceElement,
                makeGlyphs=makeGlyphs,
                makeKerning=makeKerning,
                makeInfo=makeInfo,
            )

    def _readSingleInstanceElement(
        self, instanceElement, makeGlyphs=True, makeKerning=True, makeInfo=True
    ):
        filename = instanceElement.attrib.get("filename")
        if filename is not None and self.documentObject.path is not None:
            instancePath = os.path.join(
                os.path.dirname(self.documentObject.path), filename
            )
        else:
            instancePath = None
        instanceObject = self.instanceDescriptorClass()
        instanceObject.path = instancePath  # absolute path to the instance
        instanceObject.filename = filename  # path as it is stored in the document
        name = instanceElement.attrib.get("name")
        if name is not None:
            instanceObject.name = name
        familyname = instanceElement.attrib.get("familyname")
        if familyname is not None:
            instanceObject.familyName = familyname
        stylename = instanceElement.attrib.get("stylename")
        if stylename is not None:
            instanceObject.styleName = stylename
        postScriptFontName = instanceElement.attrib.get("postscriptfontname")
        if postScriptFontName is not None:
            instanceObject.postScriptFontName = postScriptFontName
        styleMapFamilyName = instanceElement.attrib.get("stylemapfamilyname")
        if styleMapFamilyName is not None:
            instanceObject.styleMapFamilyName = styleMapFamilyName
        styleMapStyleName = instanceElement.attrib.get("stylemapstylename")
        if styleMapStyleName is not None:
            instanceObject.styleMapStyleName = styleMapStyleName
        # read localised names
        for styleNameElement in instanceElement.findall("stylename"):
            for key, lang in styleNameElement.items():
                if key == XML_LANG:
                    styleName = styleNameElement.text
                    instanceObject.setStyleName(styleName, lang)
        for familyNameElement in instanceElement.findall("familyname"):
            for key, lang in familyNameElement.items():
                if key == XML_LANG:
                    familyName = familyNameElement.text
                    instanceObject.setFamilyName(familyName, lang)
        for styleMapStyleNameElement in instanceElement.findall("stylemapstylename"):
            for key, lang in styleMapStyleNameElement.items():
                if key == XML_LANG:
                    styleMapStyleName = styleMapStyleNameElement.text
                    instanceObject.setStyleMapStyleName(styleMapStyleName, lang)
        for styleMapFamilyNameElement in instanceElement.findall("stylemapfamilyname"):
            for key, lang in styleMapFamilyNameElement.items():
                if key == XML_LANG:
                    styleMapFamilyName = styleMapFamilyNameElement.text
                    instanceObject.setStyleMapFamilyName(styleMapFamilyName, lang)
        designLocation, userLocation = self.locationFromElement(instanceElement)
        locationLabel = instanceElement.attrib.get("location")
        if (designLocation or userLocation) and locationLabel is not None:
            raise DesignSpaceDocumentError(
                'instance element must have at most one of the location="..." attribute or the nested location element'
            )
        instanceObject.locationLabel = locationLabel
        instanceObject.userLocation = userLocation or {}
        instanceObject.designLocation = designLocation or {}
        for glyphElement in instanceElement.findall(".glyphs/glyph"):
            self.readGlyphElement(glyphElement, instanceObject)
        for infoElement in instanceElement.findall("info"):
            self.readInfoElement(infoElement, instanceObject)
        for libElement in instanceElement.findall("lib"):
            self.readLibElement(libElement, instanceObject)
        self.documentObject.instances.append(instanceObject)

    def readLibElement(self, libElement, instanceObject):
        """Read the lib element for the given instance."""
        instanceObject.lib = plistlib.fromtree(libElement[0])

    def readInfoElement(self, infoElement, instanceObject):
        """Read the info element."""
        instanceObject.info = True

    def readGlyphElement(self, glyphElement, instanceObject):
        """
        Read the glyph element, which could look like either one of these:

        .. code-block:: xml

            <glyph name="b" unicode="0x62"/>

            <glyph name="b"/>

            <glyph name="b">
                <master location="location-token-bbb" source="master-token-aaa2"/>
                <master glyphname="b.alt1" location="location-token-ccc" source="master-token-aaa3"/>
                <note>
                    This is an instance from an anisotropic interpolation.
                </note>
            </glyph>
        """
        glyphData = {}
        glyphName = glyphElement.attrib.get("name")
        if glyphName is None:
            raise DesignSpaceDocumentError("Glyph object without name attribute")
        mute = glyphElement.attrib.get("mute")
        if mute == "1":
            glyphData["mute"] = True
        # unicode
        unicodes = glyphElement.attrib.get("unicode")
        if unicodes is not None:
            try:
                unicodes = [int(u, 16) for u in unicodes.split(" ")]
                glyphData["unicodes"] = unicodes
            except ValueError:
                raise DesignSpaceDocumentError(
                    "unicode values %s are not integers" % unicodes
                )

        for noteElement in glyphElement.findall(".note"):
            glyphData["note"] = noteElement.text
            break
        designLocation, userLocation = self.locationFromElement(glyphElement)
        if userLocation:
            raise DesignSpaceDocumentError(
                f'<glyph> element "{glyphName}" must only have design locations (using xvalue="").'
            )
        if designLocation is not None:
            glyphData["instanceLocation"] = designLocation
        glyphSources = None
        for masterElement in glyphElement.findall(".masters/master"):
            fontSourceName = masterElement.attrib.get("source")
            designLocation, userLocation = self.locationFromElement(masterElement)
            if userLocation:
                raise DesignSpaceDocumentError(
                    f'<master> element "{fontSourceName}" must only have design locations (using xvalue="").'
                )
            masterGlyphName = masterElement.attrib.get("glyphname")
            if masterGlyphName is None:
                # if we don't read a glyphname, use the one we have
                masterGlyphName = glyphName
            d = dict(
                font=fontSourceName, location=designLocation, glyphName=masterGlyphName
            )
            if glyphSources is None:
                glyphSources = []
            glyphSources.append(d)
        if glyphSources is not None:
            glyphData["masters"] = glyphSources
        instanceObject.glyphs[glyphName] = glyphData

    def readLib(self):
        """Read the lib element for the whole document."""
        for libElement in self.root.findall(".lib"):
            self.documentObject.lib = plistlib.fromtree(libElement[0])


class DesignSpaceDocument(LogMixin, AsDictMixin):
    """The DesignSpaceDocument object can read and write ``.designspace`` data.
    It imports the axes, sources, variable fonts and instances to very basic
    **descriptor** objects that store the data in attributes. Data is added to
    the document by creating such descriptor objects, filling them with data
    and then adding them to the document. This makes it easy to integrate this
    object in different contexts.

    The **DesignSpaceDocument** object can be subclassed to work with
    different objects, as long as they have the same attributes. Reader and
    Writer objects can be subclassed as well.

    **Note:** Python attribute names are usually camelCased, the
    corresponding `XML <document-xml-structure>`_ attributes are usually
    all lowercase.

    .. code:: python

        from fontTools.designspaceLib import DesignSpaceDocument
        doc = DesignSpaceDocument.fromfile("some/path/to/my.designspace")
        doc.formatVersion
        doc.elidedFallbackName
        doc.axes
        doc.axisMappings
        doc.locationLabels
        doc.rules
        doc.rulesProcessingLast
        doc.sources
        doc.variableFonts
        doc.instances
        doc.lib

    """

    def __init__(self, readerClass=None, writerClass=None):
        self.path = None
        """String, optional. When the document is read from the disk, this is
        the full path that was given to :meth:`read` or :meth:`fromfile`.
        """
        self.filename = None
        """String, optional. When the document is read from the disk, this is
        its original file name, i.e. the last part of its path.

        When the document is produced by a Python script and still only exists
        in memory, the producing script can write here an indication of a
        possible "good" filename, in case one wants to save the file somewhere.
        """

        self.formatVersion: Optional[str] = None
        """Format version for this document, as a string. E.g. "4.0" """

        self.elidedFallbackName: Optional[str] = None
        """STAT Style Attributes Header field ``elidedFallbackNameID``.

        See: `OTSpec STAT Style Attributes Header <https://docs.microsoft.com/en-us/typography/opentype/spec/stat#style-attributes-header>`_

        .. versionadded:: 5.0
        """

        self.axes: List[Union[AxisDescriptor, DiscreteAxisDescriptor]] = []
        """List of this document's axes."""

        self.axisMappings: List[AxisMappingDescriptor] = []
        """List of this document's axis mappings."""

        self.locationLabels: List[LocationLabelDescriptor] = []
        """List of this document's STAT format 4 labels.

        .. versionadded:: 5.0"""
        self.rules: List[RuleDescriptor] = []
        """List of this document's rules."""
        self.rulesProcessingLast: bool = False
        """This flag indicates whether the substitution rules should be applied
        before or after other glyph substitution features.

        - False: before
        - True: after.

        Default is False. For new projects, you probably want True. See
        the following issues for more information:
        `fontTools#1371 <https://github.com/fonttools/fonttools/issues/1371#issuecomment-590214572>`__
        `fontTools#2050 <https://github.com/fonttools/fonttools/issues/2050#issuecomment-678691020>`__

        If you want to use a different feature altogether, e.g. ``calt``,
        use the lib key ``com.github.fonttools.varLib.featureVarsFeatureTag``

        .. code:: xml

            <lib>
                <dict>
                    <key>com.github.fonttools.varLib.featureVarsFeatureTag</key>
                    <string>calt</string>
                </dict>
            </lib>
        """
        self.sources: List[SourceDescriptor] = []
        """List of this document's sources."""
        self.variableFonts: List[VariableFontDescriptor] = []
        """List of this document's variable fonts.

        .. versionadded:: 5.0"""
        self.instances: List[InstanceDescriptor] = []
        """List of this document's instances."""
        self.lib: Dict = {}
        """User defined, custom data associated with the whole document.

        Use reverse-DNS notation to identify your own data.
        Respect the data stored by others.
        """

        self.default: Optional[str] = None
        """Name of the default master.

        This attribute is updated by the :meth:`findDefault`
        """

        if readerClass is not None:
            self.readerClass = readerClass
        else:
            self.readerClass = BaseDocReader
        if writerClass is not None:
            self.writerClass = writerClass
        else:
            self.writerClass = BaseDocWriter

    @classmethod
    def fromfile(cls, path, readerClass=None, writerClass=None):
        """Read a designspace file from ``path`` and return a new instance of
        :class:.
        """
        self = cls(readerClass=readerClass, writerClass=writerClass)
        self.read(path)
        return self

    @classmethod
    def fromstring(cls, string, readerClass=None, writerClass=None):
        self = cls(readerClass=readerClass, writerClass=writerClass)
        reader = self.readerClass.fromstring(string, self)
        reader.read()
        if self.sources:
            self.findDefault()
        return self

    def tostring(self, encoding=None):
        """Returns the designspace as a string. Default encoding ``utf-8``."""
        if encoding is str or (encoding is not None and encoding.lower() == "unicode"):
            f = StringIO()
            xml_declaration = False
        elif encoding is None or encoding == "utf-8":
            f = BytesIO()
            encoding = "UTF-8"
            xml_declaration = True
        else:
            raise ValueError("unsupported encoding: '%s'" % encoding)
        writer = self.writerClass(f, self)
        writer.write(encoding=encoding, xml_declaration=xml_declaration)
        return f.getvalue()

    def read(self, path):
        """Read a designspace file from ``path`` and populates the fields of
        ``self`` with the data.
        """
        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()
        self.path = path
        self.filename = os.path.basename(path)
        reader = self.readerClass(path, self)
        reader.read()
        if self.sources:
            self.findDefault()

    def write(self, path):
        """Write this designspace to ``path``."""
        if hasattr(path, "__fspath__"):  # support os.PathLike objects
            path = path.__fspath__()
        self.path = path
        self.filename = os.path.basename(path)
        self.updatePaths()
        writer = self.writerClass(path, self)
        writer.write()

    def _posixRelativePath(self, otherPath):
        relative = os.path.relpath(otherPath, os.path.dirname(self.path))
        return posix(relative)

    def updatePaths(self):
        """
        Right before we save we need to identify and respond to the following situations:
        In each descriptor, we have to do the right thing for the filename attribute.

        ::

            case 1.
            descriptor.filename == None
            descriptor.path == None

            -- action:
            write as is, descriptors will not have a filename attr.
            useless, but no reason to interfere.


            case 2.
            descriptor.filename == "../something"
            descriptor.path == None

            -- action:
            write as is. The filename attr should not be touched.


            case 3.
            descriptor.filename == None
            descriptor.path == "~/absolute/path/there"

            -- action:
            calculate the relative path for filename.
            We're not overwriting some other value for filename, it should be fine


            case 4.
            descriptor.filename == '../somewhere'
            descriptor.path == "~/absolute/path/there"

            -- action:
            there is a conflict between the given filename, and the path.
            So we know where the file is relative to the document.
            Can't guess why they're different, we just choose for path to be correct and update filename.
        """
        assert self.path is not None
        for descriptor in self.sources + self.instances:
            if descriptor.path is not None:
                # case 3 and 4: filename gets updated and relativized
                descriptor.filename = self._posixRelativePath(descriptor.path)

    def addSource(self, sourceDescriptor: SourceDescriptor):
        """Add the given ``sourceDescriptor`` to ``doc.sources``."""
        self.sources.append(sourceDescriptor)

    def addSourceDescriptor(self, **kwargs):
        """Instantiate a new :class:`SourceDescriptor` using the given
        ``kwargs`` and add it to ``doc.sources``.
        """
        source = self.writerClass.sourceDescriptorClass(**kwargs)
        self.addSource(source)
        return source

    def addInstance(self, instanceDescriptor: InstanceDescriptor):
        """Add the given ``instanceDescriptor`` to :attr:`instances`."""
        self.instances.append(instanceDescriptor)

    def addInstanceDescriptor(self, **kwargs):
        """Instantiate a new :class:`InstanceDescriptor` using the given
        ``kwargs`` and add it to :attr:`instances`.
        """
        instance = self.writerClass.instanceDescriptorClass(**kwargs)
        self.addInstance(instance)
        return instance

    def addAxis(self, axisDescriptor: Union[AxisDescriptor, DiscreteAxisDescriptor]):
        """Add the given ``axisDescriptor`` to :attr:`axes`."""
        self.axes.append(axisDescriptor)

    def addAxisDescriptor(self, **kwargs):
        """Instantiate a new :class:`AxisDescriptor` using the given
        ``kwargs`` and add it to :attr:`axes`.

        The axis will be and instance of :class:`DiscreteAxisDescriptor` if
        the ``kwargs`` provide a ``value``, or a :class:`AxisDescriptor` otherwise.
        """
        if "values" in kwargs:
            axis = self.writerClass.discreteAxisDescriptorClass(**kwargs)
        else:
            axis = self.writerClass.axisDescriptorClass(**kwargs)
        self.addAxis(axis)
        return axis

    def addAxisMapping(self, axisMappingDescriptor: AxisMappingDescriptor):
        """Add the given ``axisMappingDescriptor`` to :attr:`axisMappings`."""
        self.axisMappings.append(axisMappingDescriptor)

    def addAxisMappingDescriptor(self, **kwargs):
        """Instantiate a new :class:`AxisMappingDescriptor` using the given
        ``kwargs`` and add it to :attr:`rules`.
        """
        axisMapping = self.writerClass.axisMappingDescriptorClass(**kwargs)
        self.addAxisMapping(axisMapping)
        return axisMapping

    def addRule(self, ruleDescriptor: RuleDescriptor):
        """Add the given ``ruleDescriptor`` to :attr:`rules`."""
        self.rules.append(ruleDescriptor)

    def addRuleDescriptor(self, **kwargs):
        """Instantiate a new :class:`RuleDescriptor` using the given
        ``kwargs`` and add it to :attr:`rules`.
        """
        rule = self.writerClass.ruleDescriptorClass(**kwargs)
        self.addRule(rule)
        return rule

    def addVariableFont(self, variableFontDescriptor: VariableFontDescriptor):
        """Add the given ``variableFontDescriptor`` to :attr:`variableFonts`.

        .. versionadded:: 5.0
        """
        self.variableFonts.append(variableFontDescriptor)

    def addVariableFontDescriptor(self, **kwargs):
        """Instantiate a new :class:`VariableFontDescriptor` using the given
        ``kwargs`` and add it to :attr:`variableFonts`.

        .. versionadded:: 5.0
        """
        variableFont = self.writerClass.variableFontDescriptorClass(**kwargs)
        self.addVariableFont(variableFont)
        return variableFont

    def addLocationLabel(self, locationLabelDescriptor: LocationLabelDescriptor):
        """Add the given ``locationLabelDescriptor`` to :attr:`locationLabels`.

        .. versionadded:: 5.0
        """
        self.locationLabels.append(locationLabelDescriptor)

    def addLocationLabelDescriptor(self, **kwargs):
        """Instantiate a new :class:`LocationLabelDescriptor` using the given
        ``kwargs`` and add it to :attr:`locationLabels`.

        .. versionadded:: 5.0
        """
        locationLabel = self.writerClass.locationLabelDescriptorClass(**kwargs)
        self.addLocationLabel(locationLabel)
        return locationLabel

    def newDefaultLocation(self):
        """Return a dict with the default location in design space coordinates."""
        # Without OrderedDict, output XML would be non-deterministic.
        # https://github.com/LettError/designSpaceDocument/issues/10
        loc = collections.OrderedDict()
        for axisDescriptor in self.axes:
            loc[axisDescriptor.name] = axisDescriptor.map_forward(
                axisDescriptor.default
            )
        return loc

    def labelForUserLocation(
        self, userLocation: SimpleLocationDict
    ) -> Optional[LocationLabelDescriptor]:
        """Return the :class:`LocationLabel` that matches the given
        ``userLocation``, or ``None`` if no such label exists.

        .. versionadded:: 5.0
        """
        return next(
            (
                label
                for label in self.locationLabels
                if label.userLocation == userLocation
            ),
            None,
        )

    def updateFilenameFromPath(self, masters=True, instances=True, force=False):
        """Set a descriptor filename attr from the path and this document path.

        If the filename attribute is not None: skip it.
        """
        if masters:
            for descriptor in self.sources:
                if descriptor.filename is not None and not force:
                    continue
                if self.path is not None:
                    descriptor.filename = self._posixRelativePath(descriptor.path)
        if instances:
            for descriptor in self.instances:
                if descriptor.filename is not None and not force:
                    continue
                if self.path is not None:
                    descriptor.filename = self._posixRelativePath(descriptor.path)

    def newAxisDescriptor(self):
        """Ask the writer class to make us a new axisDescriptor."""
        return self.writerClass.getAxisDecriptor()

    def newSourceDescriptor(self):
        """Ask the writer class to make us a new sourceDescriptor."""
        return self.writerClass.getSourceDescriptor()

    def newInstanceDescriptor(self):
        """Ask the writer class to make us a new instanceDescriptor."""
        return self.writerClass.getInstanceDescriptor()

    def getAxisOrder(self):
        """Return a list of axis names, in the same order as defined in the document."""
        names = []
        for axisDescriptor in self.axes:
            names.append(axisDescriptor.name)
        return names

    def getAxis(self, name: str) -> AxisDescriptor | DiscreteAxisDescriptor | None:
        """Return the axis with the given ``name``, or ``None`` if no such axis exists."""
        return next((axis for axis in self.axes if axis.name == name), None)

    def getAxisByTag(self, tag: str) -> AxisDescriptor | DiscreteAxisDescriptor | None:
        """Return the axis with the given ``tag``, or ``None`` if no such axis exists."""
        return next((axis for axis in self.axes if axis.tag == tag), None)

    def getLocationLabel(self, name: str) -> Optional[LocationLabelDescriptor]:
        """Return the top-level location label with the given ``name``, or
        ``None`` if no such label exists.

        .. versionadded:: 5.0
        """
        for label in self.locationLabels:
            if label.name == name:
                return label
        return None

    def map_forward(self, userLocation: SimpleLocationDict) -> SimpleLocationDict:
        """Map a user location to a design location.

        Assume that missing coordinates are at the default location for that axis.

        Note: the output won't be anisotropic, only the xvalue is set.

        .. versionadded:: 5.0
        """
        return {
            axis.name: axis.map_forward(userLocation.get(axis.name, axis.default))
            for axis in self.axes
        }

    def map_backward(
        self, designLocation: AnisotropicLocationDict
    ) -> SimpleLocationDict:
        """Map a design location to a user location.

        Assume that missing coordinates are at the default location for that axis.

        When the input has anisotropic locations, only the xvalue is used.

        .. versionadded:: 5.0
        """
        return {
            axis.name: (
                axis.map_backward(designLocation[axis.name])
                if axis.name in designLocation
                else axis.default
            )
            for axis in self.axes
        }

    def findDefault(self):
        """Set and return SourceDescriptor at the default location or None.

        The default location is the set of all `default` values in user space
        of all axes.

        This function updates the document's :attr:`default` value.

        .. versionchanged:: 5.0
           Allow the default source to not specify some of the axis values, and
           they are assumed to be the default.
           See :meth:`SourceDescriptor.getFullDesignLocation()`
        """
        self.default = None

        # Convert the default location from user space to design space before comparing
        # it against the SourceDescriptor locations (always in design space).
        defaultDesignLocation = self.newDefaultLocation()

        for sourceDescriptor in self.sources:
            if sourceDescriptor.getFullDesignLocation(self) == defaultDesignLocation:
                self.default = sourceDescriptor
                return sourceDescriptor

        return None

    def normalizeLocation(self, location):
        """Return a dict with normalized axis values."""
        from fontTools.varLib.models import normalizeValue

        new = {}
        for axis in self.axes:
            if axis.name not in location:
                # skipping this dimension it seems
                continue
            value = location[axis.name]
            # 'anisotropic' location, take first coord only
            if isinstance(value, tuple):
                value = value[0]
            triple = [
                axis.map_forward(v) for v in (axis.minimum, axis.default, axis.maximum)
            ]
            new[axis.name] = normalizeValue(value, triple)
        return new

    def normalize(self):
        """
        Normalise the geometry of this designspace:

        - scale all the locations of all masters and instances to the -1 - 0 - 1 value.
        - we need the axis data to do the scaling, so we do those last.
        """
        # masters
        for item in self.sources:
            item.location = self.normalizeLocation(item.location)
        # instances
        for item in self.instances:
            # glyph masters for this instance
            for _, glyphData in item.glyphs.items():
                glyphData["instanceLocation"] = self.normalizeLocation(
                    glyphData["instanceLocation"]
                )
                for glyphMaster in glyphData["masters"]:
                    glyphMaster["location"] = self.normalizeLocation(
                        glyphMaster["location"]
                    )
            item.location = self.normalizeLocation(item.location)
        # the axes
        for axis in self.axes:
            # scale the map first
            newMap = []
            for inputValue, outputValue in axis.map:
                newOutputValue = self.normalizeLocation({axis.name: outputValue}).get(
                    axis.name
                )
                newMap.append((inputValue, newOutputValue))
            if newMap:
                axis.map = newMap
            # finally the axis values
            minimum = self.normalizeLocation({axis.name: axis.minimum}).get(axis.name)
            maximum = self.normalizeLocation({axis.name: axis.maximum}).get(axis.name)
            default = self.normalizeLocation({axis.name: axis.default}).get(axis.name)
            # and set them in the axis.minimum
            axis.minimum = minimum
            axis.maximum = maximum
            axis.default = default
        # now the rules
        for rule in self.rules:
            newConditionSets = []
            for conditions in rule.conditionSets:
                newConditions = []
                for cond in conditions:
                    if cond.get("minimum") is not None:
                        minimum = self.normalizeLocation(
                            {cond["name"]: cond["minimum"]}
                        ).get(cond["name"])
                    else:
                        minimum = None
                    if cond.get("maximum") is not None:
                        maximum = self.normalizeLocation(
                            {cond["name"]: cond["maximum"]}
                        ).get(cond["name"])
                    else:
                        maximum = None
                    newConditions.append(
                        dict(name=cond["name"], minimum=minimum, maximum=maximum)
                    )
                newConditionSets.append(newConditions)
            rule.conditionSets = newConditionSets

    def loadSourceFonts(self, opener, **kwargs):
        """Ensure SourceDescriptor.font attributes are loaded, and return list of fonts.

        Takes a callable which initializes a new font object (e.g. TTFont, or
        defcon.Font, etc.) from the SourceDescriptor.path, and sets the
        SourceDescriptor.font attribute.
        If the font attribute is already not None, it is not loaded again.
        Fonts with the same path are only loaded once and shared among SourceDescriptors.

        For example, to load UFO sources using defcon:

            designspace = DesignSpaceDocument.fromfile("path/to/my.designspace")
            designspace.loadSourceFonts(defcon.Font)

        Or to load masters as FontTools binary fonts, including extra options:

            designspace.loadSourceFonts(ttLib.TTFont, recalcBBoxes=False)

        Args:
            opener (Callable): takes one required positional argument, the source.path,
                and an optional list of keyword arguments, and returns a new font object
                loaded from the path.
            **kwargs: extra options passed on to the opener function.

        Returns:
            List of font objects in the order they appear in the sources list.
        """
        # we load fonts with the same source.path only once
        loaded = {}
        fonts = []
        for source in self.sources:
            if source.font is not None:  # font already loaded
                fonts.append(source.font)
                continue
            if source.path in loaded:
                source.font = loaded[source.path]
            else:
                if source.path is None:
                    raise DesignSpaceDocumentError(
                        "Designspace source '%s' has no 'path' attribute"
                        % (source.name or "<Unknown>")
                    )
                source.font = opener(source.path, **kwargs)
                loaded[source.path] = source.font
            fonts.append(source.font)
        return fonts

    @property
    def formatTuple(self):
        """Return the formatVersion as a tuple of (major, minor).

        .. versionadded:: 5.0
        """
        if self.formatVersion is None:
            return (5, 0)
        numbers = (int(i) for i in self.formatVersion.split("."))
        major = next(numbers)
        minor = next(numbers, 0)
        return (major, minor)

    def getVariableFonts(self) -> List[VariableFontDescriptor]:
        """Return all variable fonts defined in this document, or implicit
        variable fonts that can be built from the document's continuous axes.

        In the case of Designspace documents before version 5, the whole
        document was implicitly describing a variable font that covers the
        whole space.

        In version 5 and above documents, there can be as many variable fonts
        as there are locations on discrete axes.

        .. seealso:: :func:`splitInterpolable`

        .. versionadded:: 5.0
        """
        if self.variableFonts:
            return self.variableFonts

        variableFonts = []
        discreteAxes = []
        rangeAxisSubsets: List[
            Union[RangeAxisSubsetDescriptor, ValueAxisSubsetDescriptor]
        ] = []
        for axis in self.axes:
            if hasattr(axis, "values"):
                # Mypy doesn't support narrowing union types via hasattr()
                # TODO(Python 3.10): use TypeGuard
                # https://mypy.readthedocs.io/en/stable/type_narrowing.html
                axis = cast(DiscreteAxisDescriptor, axis)
                discreteAxes.append(axis)  # type: ignore
            else:
                rangeAxisSubsets.append(RangeAxisSubsetDescriptor(name=axis.name))
        valueCombinations = itertools.product(*[axis.values for axis in discreteAxes])
        for values in valueCombinations:
            basename = None
            if self.filename is not None:
                basename = os.path.splitext(self.filename)[0] + "-VF"
            if self.path is not None:
                basename = os.path.splitext(os.path.basename(self.path))[0] + "-VF"
            if basename is None:
                basename = "VF"
            axisNames = "".join(
                [f"-{axis.tag}{value}" for axis, value in zip(discreteAxes, values)]
            )
            variableFonts.append(
                VariableFontDescriptor(
                    name=f"{basename}{axisNames}",
                    axisSubsets=rangeAxisSubsets
                    + [
                        ValueAxisSubsetDescriptor(name=axis.name, userValue=value)
                        for axis, value in zip(discreteAxes, values)
                    ],
                )
            )
        return variableFonts

    def deepcopyExceptFonts(self):
        """Allow deep-copying a DesignSpace document without deep-copying
        attached UFO fonts or TTFont objects. The :attr:`font` attribute
        is shared by reference between the original and the copy.

        .. versionadded:: 5.0
        """
        fonts = [source.font for source in self.sources]
        try:
            for source in self.sources:
                source.font = None
            res = copy.deepcopy(self)
            for source, font in zip(res.sources, fonts):
                source.font = font
            return res
        finally:
            for source, font in zip(self.sources, fonts):
                source.font = font


def main(args=None):
    """Roundtrip .designspace file through the DesignSpaceDocument class"""

    if args is None:
        import sys

        args = sys.argv[1:]

    from argparse import ArgumentParser

    parser = ArgumentParser(prog="designspaceLib", description=main.__doc__)
    parser.add_argument("input")
    parser.add_argument("output")

    options = parser.parse_args(args)

    ds = DesignSpaceDocument.fromfile(options.input)
    ds.write(options.output)