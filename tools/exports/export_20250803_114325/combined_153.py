
# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\verbnet.py ===
# Natural Language Toolkit: Verbnet Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An NLTK interface to the VerbNet verb lexicon

For details about VerbNet see:
https://verbs.colorado.edu/~mpalmer/projects/verbnet.html
"""

import re
import textwrap
from collections import defaultdict

from nltk.corpus.reader.xmldocs import XMLCorpusReader


class VerbnetCorpusReader(XMLCorpusReader):
    """
    An NLTK interface to the VerbNet verb lexicon.

    From the VerbNet site: "VerbNet (VN) (Kipper-Schuler 2006) is the largest
    on-line verb lexicon currently available for English. It is a hierarchical
    domain-independent, broad-coverage verb lexicon with mappings to other
    lexical resources such as WordNet (Miller, 1990; Fellbaum, 1998), XTAG
    (XTAG Research Group, 2001), and FrameNet (Baker et al., 1998)."

    For details about VerbNet see:
    https://verbs.colorado.edu/~mpalmer/projects/verbnet.html
    """

    # No unicode encoding param, since the data files are all XML.
    def __init__(self, root, fileids, wrap_etree=False):
        XMLCorpusReader.__init__(self, root, fileids, wrap_etree)

        self._lemma_to_class = defaultdict(list)
        """A dictionary mapping from verb lemma strings to lists of
        VerbNet class identifiers."""

        self._wordnet_to_class = defaultdict(list)
        """A dictionary mapping from wordnet identifier strings to
        lists of VerbNet class identifiers."""

        self._class_to_fileid = {}
        """A dictionary mapping from class identifiers to
        corresponding file identifiers.  The keys of this dictionary
        provide a complete list of all classes and subclasses."""

        self._shortid_to_longid = {}

        # Initialize the dictionaries.  Use the quick (regexp-based)
        # method instead of the slow (xml-based) method, because it
        # runs 2-30 times faster.
        self._quick_index()

    _LONGID_RE = re.compile(r"([^\-\.]*)-([\d+.\-]+)$")
    """Regular expression that matches (and decomposes) longids"""

    _SHORTID_RE = re.compile(r"[\d+.\-]+$")
    """Regular expression that matches shortids"""

    _INDEX_RE = re.compile(
        r'<MEMBER name="\??([^"]+)" wn="([^"]*)"[^>]+>|' r'<VNSUBCLASS ID="([^"]+)"/?>'
    )
    """Regular expression used by ``_index()`` to quickly scan the corpus
       for basic information."""

    def lemmas(self, vnclass=None):
        """
        Return a list of all verb lemmas that appear in any class, or
        in the ``classid`` if specified.
        """
        if vnclass is None:
            return sorted(self._lemma_to_class.keys())
        else:
            # [xx] should this include subclass members?
            if isinstance(vnclass, str):
                vnclass = self.vnclass(vnclass)
            return [member.get("name") for member in vnclass.findall("MEMBERS/MEMBER")]

    def wordnetids(self, vnclass=None):
        """
        Return a list of all wordnet identifiers that appear in any
        class, or in ``classid`` if specified.
        """
        if vnclass is None:
            return sorted(self._wordnet_to_class.keys())
        else:
            # [xx] should this include subclass members?
            if isinstance(vnclass, str):
                vnclass = self.vnclass(vnclass)
            return sum(
                (
                    member.get("wn", "").split()
                    for member in vnclass.findall("MEMBERS/MEMBER")
                ),
                [],
            )

    def classids(self, lemma=None, wordnetid=None, fileid=None, classid=None):
        """
        Return a list of the VerbNet class identifiers.  If a file
        identifier is specified, then return only the VerbNet class
        identifiers for classes (and subclasses) defined by that file.
        If a lemma is specified, then return only VerbNet class
        identifiers for classes that contain that lemma as a member.
        If a wordnetid is specified, then return only identifiers for
        classes that contain that wordnetid as a member.  If a classid
        is specified, then return only identifiers for subclasses of
        the specified VerbNet class.
        If nothing is specified, return all classids within VerbNet
        """
        if fileid is not None:
            return [c for (c, f) in self._class_to_fileid.items() if f == fileid]
        elif lemma is not None:
            return self._lemma_to_class[lemma]
        elif wordnetid is not None:
            return self._wordnet_to_class[wordnetid]
        elif classid is not None:
            xmltree = self.vnclass(classid)
            return [
                subclass.get("ID")
                for subclass in xmltree.findall("SUBCLASSES/VNSUBCLASS")
            ]
        else:
            return sorted(self._class_to_fileid.keys())

    def vnclass(self, fileid_or_classid):
        """Returns VerbNet class ElementTree

        Return an ElementTree containing the xml for the specified
        VerbNet class.

        :param fileid_or_classid: An identifier specifying which class
            should be returned.  Can be a file identifier (such as
            ``'put-9.1.xml'``), or a VerbNet class identifier (such as
            ``'put-9.1'``) or a short VerbNet class identifier (such as
            ``'9.1'``).
        """
        # File identifier: just return the xml.
        if fileid_or_classid in self._fileids:
            return self.xml(fileid_or_classid)

        # Class identifier: get the xml, and find the right elt.
        classid = self.longid(fileid_or_classid)
        if classid in self._class_to_fileid:
            fileid = self._class_to_fileid[self.longid(classid)]
            tree = self.xml(fileid)
            if classid == tree.get("ID"):
                return tree
            else:
                for subclass in tree.findall(".//VNSUBCLASS"):
                    if classid == subclass.get("ID"):
                        return subclass
                else:
                    assert False  # we saw it during _index()!

        else:
            raise ValueError(f"Unknown identifier {fileid_or_classid}")

    def fileids(self, vnclass_ids=None):
        """
        Return a list of fileids that make up this corpus.  If
        ``vnclass_ids`` is specified, then return the fileids that make
        up the specified VerbNet class(es).
        """
        if vnclass_ids is None:
            return self._fileids
        elif isinstance(vnclass_ids, str):
            return [self._class_to_fileid[self.longid(vnclass_ids)]]
        else:
            return [
                self._class_to_fileid[self.longid(vnclass_id)]
                for vnclass_id in vnclass_ids
            ]

    def frames(self, vnclass):
        """Given a VerbNet class, this method returns VerbNet frames

        The members returned are:
        1) Example
        2) Description
        3) Syntax
        4) Semantics

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        :return: frames - a list of frame dictionaries
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)
        frames = []
        vnframes = vnclass.findall("FRAMES/FRAME")
        for vnframe in vnframes:
            frames.append(
                {
                    "example": self._get_example_within_frame(vnframe),
                    "description": self._get_description_within_frame(vnframe),
                    "syntax": self._get_syntactic_list_within_frame(vnframe),
                    "semantics": self._get_semantics_within_frame(vnframe),
                }
            )
        return frames

    def subclasses(self, vnclass):
        """Returns subclass ids, if any exist

        Given a VerbNet class, this method returns subclass ids (if they exist)
        in a list of strings.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        :return: list of subclasses
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        subclasses = [
            subclass.get("ID") for subclass in vnclass.findall("SUBCLASSES/VNSUBCLASS")
        ]
        return subclasses

    def themroles(self, vnclass):
        """Returns thematic roles participating in a VerbNet class

        Members returned as part of roles are-
        1) Type
        2) Modifiers

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        :return: themroles: A list of thematic roles in the VerbNet class
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        themroles = []
        for trole in vnclass.findall("THEMROLES/THEMROLE"):
            themroles.append(
                {
                    "type": trole.get("type"),
                    "modifiers": [
                        {"value": restr.get("Value"), "type": restr.get("type")}
                        for restr in trole.findall("SELRESTRS/SELRESTR")
                    ],
                }
            )
        return themroles

    ######################################################################
    # { Index Initialization
    ######################################################################

    def _index(self):
        """
        Initialize the indexes ``_lemma_to_class``,
        ``_wordnet_to_class``, and ``_class_to_fileid`` by scanning
        through the corpus fileids.  This is fast if ElementTree
        uses the C implementation (<0.1 secs), but quite slow (>10 secs)
        if only the python implementation is available.
        """
        for fileid in self._fileids:
            self._index_helper(self.xml(fileid), fileid)

    def _index_helper(self, xmltree, fileid):
        """Helper for ``_index()``"""
        vnclass = xmltree.get("ID")
        self._class_to_fileid[vnclass] = fileid
        self._shortid_to_longid[self.shortid(vnclass)] = vnclass
        for member in xmltree.findall("MEMBERS/MEMBER"):
            self._lemma_to_class[member.get("name")].append(vnclass)
            for wn in member.get("wn", "").split():
                self._wordnet_to_class[wn].append(vnclass)
        for subclass in xmltree.findall("SUBCLASSES/VNSUBCLASS"):
            self._index_helper(subclass, fileid)

    def _quick_index(self):
        """
        Initialize the indexes ``_lemma_to_class``,
        ``_wordnet_to_class``, and ``_class_to_fileid`` by scanning
        through the corpus fileids.  This doesn't do proper xml parsing,
        but is good enough to find everything in the standard VerbNet
        corpus -- and it runs about 30 times faster than xml parsing
        (with the python ElementTree; only 2-3 times faster
        if ElementTree uses the C implementation).
        """
        # nb: if we got rid of wordnet_to_class, this would run 2-3
        # times faster.
        for fileid in self._fileids:
            vnclass = fileid[:-4]  # strip the '.xml'
            self._class_to_fileid[vnclass] = fileid
            self._shortid_to_longid[self.shortid(vnclass)] = vnclass
            with self.open(fileid) as fp:
                for m in self._INDEX_RE.finditer(fp.read()):
                    groups = m.groups()
                    if groups[0] is not None:
                        self._lemma_to_class[groups[0]].append(vnclass)
                        for wn in groups[1].split():
                            self._wordnet_to_class[wn].append(vnclass)
                    elif groups[2] is not None:
                        self._class_to_fileid[groups[2]] = fileid
                        vnclass = groups[2]  # for <MEMBER> elts.
                        self._shortid_to_longid[self.shortid(vnclass)] = vnclass
                    else:
                        assert False, "unexpected match condition"

    ######################################################################
    # { Identifier conversion
    ######################################################################

    def longid(self, shortid):
        """Returns longid of a VerbNet class

        Given a short VerbNet class identifier (eg '37.10'), map it
        to a long id (eg 'confess-37.10').  If ``shortid`` is already a
        long id, then return it as-is"""
        if self._LONGID_RE.match(shortid):
            return shortid  # it's already a longid.
        elif not self._SHORTID_RE.match(shortid):
            raise ValueError("vnclass identifier %r not found" % shortid)
        try:
            return self._shortid_to_longid[shortid]
        except KeyError as e:
            raise ValueError("vnclass identifier %r not found" % shortid) from e

    def shortid(self, longid):
        """Returns shortid of a VerbNet class

        Given a long VerbNet class identifier (eg 'confess-37.10'),
        map it to a short id (eg '37.10').  If ``longid`` is already a
        short id, then return it as-is."""
        if self._SHORTID_RE.match(longid):
            return longid  # it's already a shortid.
        m = self._LONGID_RE.match(longid)
        if m:
            return m.group(2)
        else:
            raise ValueError("vnclass identifier %r not found" % longid)

    ######################################################################
    # { Frame access utility functions
    ######################################################################

    def _get_semantics_within_frame(self, vnframe):
        """Returns semantics within a single frame

        A utility function to retrieve semantics within a frame in VerbNet
        Members of the semantics dictionary:
        1) Predicate value
        2) Arguments

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        :return: semantics: semantics dictionary
        """
        semantics_within_single_frame = []
        for pred in vnframe.findall("SEMANTICS/PRED"):
            arguments = [
                {"type": arg.get("type"), "value": arg.get("value")}
                for arg in pred.findall("ARGS/ARG")
            ]
            semantics_within_single_frame.append(
                {
                    "predicate_value": pred.get("value"),
                    "arguments": arguments,
                    "negated": pred.get("bool") == "!",
                }
            )
        return semantics_within_single_frame

    def _get_example_within_frame(self, vnframe):
        """Returns example within a frame

        A utility function to retrieve an example within a frame in VerbNet.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        :return: example_text: The example sentence for this particular frame
        """
        example_element = vnframe.find("EXAMPLES/EXAMPLE")
        if example_element is not None:
            example_text = example_element.text
        else:
            example_text = ""
        return example_text

    def _get_description_within_frame(self, vnframe):
        """Returns member description within frame

        A utility function to retrieve a description of participating members
        within a frame in VerbNet.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        :return: description: a description dictionary with members - primary and secondary
        """
        description_element = vnframe.find("DESCRIPTION")
        return {
            "primary": description_element.attrib["primary"],
            "secondary": description_element.get("secondary", ""),
        }

    def _get_syntactic_list_within_frame(self, vnframe):
        """Returns semantics within a frame

        A utility function to retrieve semantics within a frame in VerbNet.
        Members of the syntactic dictionary:
        1) POS Tag
        2) Modifiers

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        :return: syntax_within_single_frame
        """
        syntax_within_single_frame = []
        for elt in vnframe.find("SYNTAX"):
            pos_tag = elt.tag
            modifiers = dict()
            modifiers["value"] = elt.get("value") if "value" in elt.attrib else ""
            modifiers["selrestrs"] = [
                {"value": restr.get("Value"), "type": restr.get("type")}
                for restr in elt.findall("SELRESTRS/SELRESTR")
            ]
            modifiers["synrestrs"] = [
                {"value": restr.get("Value"), "type": restr.get("type")}
                for restr in elt.findall("SYNRESTRS/SYNRESTR")
            ]
            syntax_within_single_frame.append(
                {"pos_tag": pos_tag, "modifiers": modifiers}
            )
        return syntax_within_single_frame

    ######################################################################
    # { Pretty Printing
    ######################################################################

    def pprint(self, vnclass):
        """Returns pretty printed version of a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet class.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        s = vnclass.get("ID") + "\n"
        s += self.pprint_subclasses(vnclass, indent="  ") + "\n"
        s += self.pprint_members(vnclass, indent="  ") + "\n"
        s += "  Thematic roles:\n"
        s += self.pprint_themroles(vnclass, indent="    ") + "\n"
        s += "  Frames:\n"
        s += self.pprint_frames(vnclass, indent="    ")
        return s

    def pprint_subclasses(self, vnclass, indent=""):
        """Returns pretty printed version of subclasses of VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet class's subclasses.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        subclasses = self.subclasses(vnclass)
        if not subclasses:
            subclasses = ["(none)"]
        s = "Subclasses: " + " ".join(subclasses)
        return textwrap.fill(
            s, 70, initial_indent=indent, subsequent_indent=indent + "  "
        )

    def pprint_members(self, vnclass, indent=""):
        """Returns pretty printed version of members in a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet class's member verbs.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        members = self.lemmas(vnclass)
        if not members:
            members = ["(none)"]
        s = "Members: " + " ".join(members)
        return textwrap.fill(
            s, 70, initial_indent=indent, subsequent_indent=indent + "  "
        )

    def pprint_themroles(self, vnclass, indent=""):
        """Returns pretty printed version of thematic roles in a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet class's thematic roles.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)

        pieces = []
        for themrole in self.themroles(vnclass):
            piece = indent + "* " + themrole.get("type")
            modifiers = [
                modifier["value"] + modifier["type"]
                for modifier in themrole["modifiers"]
            ]
            if modifiers:
                piece += "[{}]".format(" ".join(modifiers))
            pieces.append(piece)
        return "\n".join(pieces)

    def pprint_frames(self, vnclass, indent=""):
        """Returns pretty version of all frames in a VerbNet class

        Return a string containing a pretty-printed representation of
        the list of frames within the VerbNet class.

        :param vnclass: A VerbNet class identifier; or an ElementTree
            containing the xml contents of a VerbNet class.
        """
        if isinstance(vnclass, str):
            vnclass = self.vnclass(vnclass)
        pieces = []
        for vnframe in self.frames(vnclass):
            pieces.append(self._pprint_single_frame(vnframe, indent))
        return "\n".join(pieces)

    def _pprint_single_frame(self, vnframe, indent=""):
        """Returns pretty printed version of a single frame in a VerbNet class

        Returns a string containing a pretty-printed representation of
        the given frame.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        """
        frame_string = self._pprint_description_within_frame(vnframe, indent) + "\n"
        frame_string += self._pprint_example_within_frame(vnframe, indent + " ") + "\n"
        frame_string += (
            self._pprint_syntax_within_frame(vnframe, indent + "  Syntax: ") + "\n"
        )
        frame_string += indent + "  Semantics:\n"
        frame_string += self._pprint_semantics_within_frame(vnframe, indent + "    ")
        return frame_string

    def _pprint_example_within_frame(self, vnframe, indent=""):
        """Returns pretty printed version of example within frame in a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet frame example.

        :param vnframe: An ElementTree containing the xml contents of
            a Verbnet frame.
        """
        if vnframe["example"]:
            return indent + " Example: " + vnframe["example"]

    def _pprint_description_within_frame(self, vnframe, indent=""):
        """Returns pretty printed version of a VerbNet frame description

        Return a string containing a pretty-printed representation of
        the given VerbNet frame description.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        """
        description = indent + vnframe["description"]["primary"]
        if vnframe["description"]["secondary"]:
            description += " ({})".format(vnframe["description"]["secondary"])
        return description

    def _pprint_syntax_within_frame(self, vnframe, indent=""):
        """Returns pretty printed version of syntax within a frame in a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet frame syntax.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        """
        pieces = []
        for element in vnframe["syntax"]:
            piece = element["pos_tag"]
            modifier_list = []
            if "value" in element["modifiers"] and element["modifiers"]["value"]:
                modifier_list.append(element["modifiers"]["value"])
            modifier_list += [
                "{}{}".format(restr["value"], restr["type"])
                for restr in (
                    element["modifiers"]["selrestrs"]
                    + element["modifiers"]["synrestrs"]
                )
            ]
            if modifier_list:
                piece += "[{}]".format(" ".join(modifier_list))
            pieces.append(piece)

        return indent + " ".join(pieces)

    def _pprint_semantics_within_frame(self, vnframe, indent=""):
        """Returns a pretty printed version of semantics within frame in a VerbNet class

        Return a string containing a pretty-printed representation of
        the given VerbNet frame semantics.

        :param vnframe: An ElementTree containing the xml contents of
            a VerbNet frame.
        """
        pieces = []
        for predicate in vnframe["semantics"]:
            arguments = [argument["value"] for argument in predicate["arguments"]]
            pieces.append(
                f"{'¬' if predicate['negated'] else ''}{predicate['predicate_value']}({', '.join(arguments)})"
            )
        return "\n".join(f"{indent}* {piece}" for piece in pieces)

# === NexusCore/openenv\Lib\site-packages\wget.py ===
#!/usr/bin/env python
"""
Download utility as an easy way to get file from the net
 
  python -m wget <URL>
  python wget.py <URL>

Downloads: http://pypi.python.org/pypi/wget/
Development: http://bitbucket.org/techtonik/python-wget/

wget.py is not option compatible with Unix wget utility,
to make command line interface intuitive for new people.

Public domain by anatoly techtonik <techtonik@gmail.com>
Also available under the terms of MIT license
Copyright (c) 2010-2015 anatoly techtonik
"""

__version__ = "3.2"


import sys, shutil, os
import tempfile
import math

PY3K = sys.version_info >= (3, 0)
if PY3K:
  import urllib.request as ulib
  import urllib.parse as urlparse
else:
  import urllib as ulib
  import urlparse


# --- workarounds for Python misbehavior ---

# enable passing unicode arguments from command line in Python 2.x
# https://stackoverflow.com/questions/846850/read-unicode-characters
def win32_utf8_argv():
    """Uses shell32.GetCommandLineArgvW to get sys.argv as a list of Unicode
    strings.

    Versions 2.x of Python don't support Unicode in sys.argv on
    Windows, with the underlying Windows API instead replacing multi-byte
    characters with '?'.
    """

    from ctypes import POINTER, byref, cdll, c_int, windll
    from ctypes.wintypes import LPCWSTR, LPWSTR

    GetCommandLineW = cdll.kernel32.GetCommandLineW
    GetCommandLineW.argtypes = []
    GetCommandLineW.restype = LPCWSTR

    CommandLineToArgvW = windll.shell32.CommandLineToArgvW
    CommandLineToArgvW.argtypes = [LPCWSTR, POINTER(c_int)]
    CommandLineToArgvW.restype = POINTER(LPWSTR)

    cmd = GetCommandLineW()
    argc = c_int(0)
    argv = CommandLineToArgvW(cmd, byref(argc))
    argnum = argc.value
    sysnum = len(sys.argv)
    result = []
    if argnum > 0:
        # Remove Python executable and commands if present
        start = argnum - sysnum
        for i in range(start, argnum):
            result.append(argv[i].encode('utf-8'))
    return result


# enable unicode output to windows console
# https://stackoverflow.com/questions/878972/windows-cmd-encoding-change-causes-python-crash
def win32_unicode_console():
    import codecs
    from ctypes import WINFUNCTYPE, windll, POINTER, byref, c_int
    from ctypes.wintypes import BOOL, HANDLE, DWORD, LPWSTR, LPCWSTR, LPVOID

    original_stderr = sys.stderr

    # Output exceptions in this code to original_stderr, so that we can at least see them
    def _complain(message):
        original_stderr.write(message if isinstance(message, str) else repr(message))
        original_stderr.write('\n')

    codecs.register(lambda name: codecs.lookup('utf-8') if name == 'cp65001' else None)

    try:
        GetStdHandle = WINFUNCTYPE(HANDLE, DWORD)(("GetStdHandle", windll.kernel32))
        STD_OUTPUT_HANDLE = DWORD(-11)
        STD_ERROR_HANDLE = DWORD(-12)
        GetFileType = WINFUNCTYPE(DWORD, DWORD)(("GetFileType", windll.kernel32))
        FILE_TYPE_CHAR = 0x0002
        FILE_TYPE_REMOTE = 0x8000
        GetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, POINTER(DWORD))(("GetConsoleMode", windll.kernel32))
        INVALID_HANDLE_VALUE = DWORD(-1).value

        def not_a_console(handle):
            if handle == INVALID_HANDLE_VALUE or handle is None:
                return True
            return ((GetFileType(handle) & ~FILE_TYPE_REMOTE) != FILE_TYPE_CHAR
                    or GetConsoleMode(handle, byref(DWORD())) == 0)

        old_stdout_fileno = None
        old_stderr_fileno = None
        if hasattr(sys.stdout, 'fileno'):
            old_stdout_fileno = sys.stdout.fileno()
        if hasattr(sys.stderr, 'fileno'):
            old_stderr_fileno = sys.stderr.fileno()

        STDOUT_FILENO = 1
        STDERR_FILENO = 2
        real_stdout = (old_stdout_fileno == STDOUT_FILENO)
        real_stderr = (old_stderr_fileno == STDERR_FILENO)

        if real_stdout:
            hStdout = GetStdHandle(STD_OUTPUT_HANDLE)
            if not_a_console(hStdout):
                real_stdout = False

        if real_stderr:
            hStderr = GetStdHandle(STD_ERROR_HANDLE)
            if not_a_console(hStderr):
                real_stderr = False

        if real_stdout or real_stderr:
            WriteConsoleW = WINFUNCTYPE(BOOL, HANDLE, LPWSTR, DWORD, POINTER(DWORD), LPVOID)(("WriteConsoleW", windll.kernel32))

            class UnicodeOutput:
                def __init__(self, hConsole, stream, fileno, name):
                    self._hConsole = hConsole
                    self._stream = stream
                    self._fileno = fileno
                    self.closed = False
                    self.softspace = False
                    self.mode = 'w'
                    self.encoding = 'utf-8'
                    self.name = name
                    self.flush()

                def isatty(self):
                    return False

                def close(self):
                    # don't really close the handle, that would only cause problems
                    self.closed = True

                def fileno(self):
                    return self._fileno

                def flush(self):
                    if self._hConsole is None:
                        try:
                            self._stream.flush()
                        except Exception as e:
                            _complain("%s.flush: %r from %r" % (self.name, e, self._stream))
                            raise

                def write(self, text):
                    try:
                        if self._hConsole is None:
                            if not PY3K and isinstance(text, unicode):
                                text = text.encode('utf-8')
                            elif PY3K and isinstance(text, str):
                                text = text.encode('utf-8')
                            self._stream.write(text)
                        else:
                            if not PY3K and not isinstance(text, unicode):
                                text = str(text).decode('utf-8')
                            elif PY3K and not isinstance(text, str):
                                text = text.decode('utf-8')
                            remaining = len(text)
                            while remaining:
                                n = DWORD(0)
                                # There is a shorter-than-documented limitation on the
                                # length of the string passed to WriteConsoleW (see
                                # <http://tahoe-lafs.org/trac/tahoe-lafs/ticket/1232>.
                                retval = WriteConsoleW(self._hConsole, text, min(remaining, 10000), byref(n), None)
                                if retval == 0 or n.value == 0:
                                    raise IOError("WriteConsoleW returned %r, n.value = %r" % (retval, n.value))
                                remaining -= n.value
                                if not remaining:
                                    break
                                text = text[n.value:]
                    except Exception as e:
                        _complain("%s.write: %r" % (self.name, e))
                        raise

                def writelines(self, lines):
                    try:
                        for line in lines:
                            self.write(line)
                    except Exception as e:
                        _complain("%s.writelines: %r" % (self.name, e))
                        raise

            if real_stdout:
                sys.stdout = UnicodeOutput(hStdout, None, STDOUT_FILENO, '<Unicode console stdout>')
            else:
                sys.stdout = UnicodeOutput(None, sys.stdout, old_stdout_fileno, '<Unicode redirected stdout>')

            if real_stderr:
                sys.stderr = UnicodeOutput(hStderr, None, STDERR_FILENO, '<Unicode console stderr>')
            else:
                sys.stderr = UnicodeOutput(None, sys.stderr, old_stderr_fileno, '<Unicode redirected stderr>')
    except Exception as e:
        _complain("exception %r while fixing up sys.stdout and sys.stderr" % (e,))


# --- helpers ---

def to_unicode(filename):
    """:return: filename decoded from utf-8 to unicode"""
    #
    if PY3K:
        # [ ] test this on Python 3 + (Windows, Linux)
        # [ ] port filename_from_headers once this works
        # [ ] add test to repository / Travis
        return filename
    else:
        if isinstance(filename, unicode): 
            return filename
        else:
            return unicode(filename, 'utf-8')

def filename_from_url(url):
    """:return: detected filename as unicode or None"""
    # [ ] test urlparse behavior with unicode url
    fname = os.path.basename(urlparse.urlparse(url).path)
    if len(fname.strip(" \n\t.")) == 0:
        return None
    return to_unicode(fname)

def filename_from_headers(headers):
    """Detect filename from Content-Disposition headers if present.
    http://greenbytes.de/tech/tc2231/

    :param: headers as dict, list or string
    :return: filename from content-disposition header or None
    """
    if type(headers) == str:
        headers = headers.splitlines()
    if type(headers) == list:
        headers = dict([x.split(':', 1) for x in headers])
    cdisp = headers.get("Content-Disposition")
    if not cdisp:
        return None
    cdtype = cdisp.split(';')
    if len(cdtype) == 1:
        return None
    if cdtype[0].strip().lower() not in ('inline', 'attachment'):
        return None
    # several filename params is illegal, but just in case
    fnames = [x for x in cdtype[1:] if x.strip().startswith('filename=')]
    if len(fnames) > 1:
        return None
    name = fnames[0].split('=')[1].strip(' \t"')
    name = os.path.basename(name)
    if not name:
        return None
    return name

def filename_fix_existing(filename):
    """Expands name portion of filename with numeric ' (x)' suffix to
    return filename that doesn't exist already.
    """
    dirname = u'.'
    name, ext = filename.rsplit('.', 1)
    names = [x for x in os.listdir(dirname) if x.startswith(name)]
    names = [x.rsplit('.', 1)[0] for x in names]
    suffixes = [x.replace(name, '') for x in names]
    # filter suffixes that match ' (x)' pattern
    suffixes = [x[2:-1] for x in suffixes
                   if x.startswith(' (') and x.endswith(')')]
    indexes  = [int(x) for x in suffixes
                   if set(x) <= set('0123456789')]
    idx = 1
    if indexes:
        idx += sorted(indexes)[-1]
    return '%s (%d).%s' % (name, idx, ext)


# --- terminal/console output helpers ---

def get_console_width():
    """Return width of available window area. Autodetection works for
       Windows and POSIX platforms. Returns 80 for others

       Code from http://bitbucket.org/techtonik/python-pager
    """

    if os.name == 'nt':
        STD_INPUT_HANDLE  = -10
        STD_OUTPUT_HANDLE = -11
        STD_ERROR_HANDLE  = -12

        # get console handle
        from ctypes import windll, Structure, byref
        try:
            from ctypes.wintypes import SHORT, WORD, DWORD
        except ImportError:
            # workaround for missing types in Python 2.5
            from ctypes import (
                c_short as SHORT, c_ushort as WORD, c_ulong as DWORD)
        console_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

        # CONSOLE_SCREEN_BUFFER_INFO Structure
        class COORD(Structure):
            _fields_ = [("X", SHORT), ("Y", SHORT)]

        class SMALL_RECT(Structure):
            _fields_ = [("Left", SHORT), ("Top", SHORT),
                        ("Right", SHORT), ("Bottom", SHORT)]

        class CONSOLE_SCREEN_BUFFER_INFO(Structure):
            _fields_ = [("dwSize", COORD),
                        ("dwCursorPosition", COORD),
                        ("wAttributes", WORD),
                        ("srWindow", SMALL_RECT),
                        ("dwMaximumWindowSize", DWORD)]

        sbi = CONSOLE_SCREEN_BUFFER_INFO()
        ret = windll.kernel32.GetConsoleScreenBufferInfo(
            console_handle, byref(sbi))
        if ret == 0:
            return 0
        return sbi.srWindow.Right+1

    elif os.name == 'posix':
        from fcntl import ioctl
        from termios import TIOCGWINSZ
        from array import array

        winsize = array("H", [0] * 4)
        try:
            ioctl(sys.stdout.fileno(), TIOCGWINSZ, winsize)
        except IOError:
            pass
        return (winsize[1], winsize[0])[0]

    return 80


def bar_thermometer(current, total, width=80):
    """Return thermometer style progress bar string. `total` argument
    can not be zero. The minimum size of bar returned is 3. Example:

        [..........            ]

    Control and trailing symbols (\r and spaces) are not included.
    See `bar_adaptive` for more information.
    """
    # number of dots on thermometer scale
    avail_dots = width-2
    shaded_dots = int(math.floor(float(current) / total * avail_dots))
    return '[' + '.'*shaded_dots + ' '*(avail_dots-shaded_dots) + ']'

def bar_adaptive(current, total, width=80):
    """Return progress bar string for given values in one of three
    styles depending on available width:

        [..  ] downloaded / total
        downloaded / total
        [.. ]

    if total value is unknown or <= 0, show bytes counter using two
    adaptive styles:

        %s / unknown
        %s

    if there is not enough space on the screen, do not display anything

    returned string doesn't include control characters like \r used to
    place cursor at the beginning of the line to erase previous content.

    this function leaves one free character at the end of string to
    avoid automatic linefeed on Windows.
    """

    # process special case when total size is unknown and return immediately
    if not total or total < 0:
        msg = "%s / unknown" % current
        if len(msg) < width:    # leaves one character to avoid linefeed
            return msg
        if len("%s" % current) < width:
            return "%s" % current

    # --- adaptive layout algorithm ---
    #
    # [x] describe the format of the progress bar
    # [x] describe min width for each data field
    # [x] set priorities for each element
    # [x] select elements to be shown
    #   [x] choose top priority element min_width < avail_width
    #   [x] lessen avail_width by value if min_width
    #   [x] exclude element from priority list and repeat
    
    #  10% [.. ]  10/100
    # pppp bbbbb sssssss

    min_width = {
      'percent': 4,  # 100%
      'bar': 3,      # [.]
      'size': len("%s" % total)*2 + 3, # 'xxxx / yyyy'
    }
    priority = ['percent', 'bar', 'size']

    # select elements to show
    selected = []
    avail = width
    for field in priority:
      if min_width[field] < avail:
        selected.append(field)
        avail -= min_width[field]+1   # +1 is for separator or for reserved space at
                                      # the end of line to avoid linefeed on Windows
    # render
    output = ''
    for field in selected:

      if field == 'percent':
        # fixed size width for percentage
        output += ('%s%%' % (100 * current // total)).rjust(min_width['percent'])
      elif field == 'bar':  # [. ]
        # bar takes its min width + all available space
        output += bar_thermometer(current, total, min_width['bar']+avail)
      elif field == 'size':
        # size field has a constant width (min == max)
        output += ("%s / %s" % (current, total)).rjust(min_width['size'])

      selected = selected[1:]
      if selected:
        output += ' '  # add field separator

    return output

# --/ console helpers


__current_size = 0  # global state variable, which exists solely as a
                    # workaround against Python 3.3.0 regression
                    # http://bugs.python.org/issue16409
                    # fixed in Python 3.3.1
def callback_progress(blocks, block_size, total_size, bar_function):
    """callback function for urlretrieve that is called when connection is
    created and when once for each block

    draws adaptive progress bar in terminal/console

    use sys.stdout.write() instead of "print,", because it allows one more
    symbol at the line end without linefeed on Windows

    :param blocks: number of blocks transferred so far
    :param block_size: in bytes
    :param total_size: in bytes, can be -1 if server doesn't return it
    :param bar_function: another callback function to visualize progress
    """
    global __current_size
 
    width = min(100, get_console_width())

    if sys.version_info[:3] == (3, 3, 0):  # regression workaround
        if blocks == 0:  # first call
            __current_size = 0
        else:
            __current_size += block_size
        current_size = __current_size
    else:
        current_size = min(blocks*block_size, total_size)
    progress = bar_function(current_size, total_size, width)
    if progress:
        sys.stdout.write("\r" + progress)


def detect_filename(url=None, out=None, headers=None, default="download.wget"):
    """Return filename for saving file. If no filename is detected from output
    argument, url or headers, return default (download.wget)
    """
    names = dict(out='', url='', headers='')
    if out:
        names["out"] = out or ''
    if url:
        names["url"] = filename_from_url(url) or ''
    if headers:
        names["headers"] = filename_from_headers(headers) or ''
    return names["out"] or names["headers"] or names["url"] or default

def download(url, out=None, bar=bar_adaptive):
    """High level function, which downloads URL into tmp file in current
    directory and then renames it to filename autodetected from either URL
    or HTTP headers.

    :param bar: function to track download progress (visualize etc.)
    :param out: output filename or directory
    :return:    filename where URL is downloaded to
    """
    # detect of out is a directory
    outdir = None
    if out and os.path.isdir(out):
        outdir = out
        out = None

    # get filename for temp file in current directory
    prefix = detect_filename(url, out)
    (fd, tmpfile) = tempfile.mkstemp(".tmp", prefix=prefix, dir=".")
    os.close(fd)
    os.unlink(tmpfile)

    # set progress monitoring callback
    def callback_charged(blocks, block_size, total_size):
        # 'closure' to set bar drawing function in callback
        callback_progress(blocks, block_size, total_size, bar_function=bar)
    if bar:
        callback = callback_charged
    else:
        callback = None

    if PY3K:
        # Python 3 can not quote URL as needed
        binurl = list(urlparse.urlsplit(url))
        binurl[2] = urlparse.quote(binurl[2])
        binurl = urlparse.urlunsplit(binurl)
    else:
        binurl = url
    (tmpfile, headers) = ulib.urlretrieve(binurl, tmpfile, callback)
    filename = detect_filename(url, out, headers)
    if outdir:
        filename = outdir + "/" + filename

    # add numeric ' (x)' suffix if filename already exists
    if os.path.exists(filename):
        filename = filename_fix_existing(filename)
    shutil.move(tmpfile, filename)

    #print headers
    return filename


usage = """\
usage: wget.py [options] URL

options:
  -o --output FILE|DIR   output filename or directory
  -h --help
  --version
"""

if __name__ == "__main__":
    if len(sys.argv) < 2 or "-h" in sys.argv or "--help" in sys.argv:
        sys.exit(usage)
    if "--version" in sys.argv:
        sys.exit("wget.py " + __version__)

    # patch Python 2.x to read unicode from command line
    if not PY3K and sys.platform == "win32":
        sys.argv = win32_utf8_argv()
    # patch Python to write unicode characters to console
    if sys.platform == "win32":
        win32_unicode_console()

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-o", "--output", dest="output")
    (options, args) = parser.parse_args()

    url = sys.argv[1]
    filename = download(args[0], out=options.output)

    print("")
    print("Saved under %s" % filename)

r"""
features that require more tuits for urlretrieve API
http://www.python.org/doc/2.6/library/urllib.html#urllib.urlretrieve

[x] autodetect filename from URL
[x] autodetect filename from headers - Content-Disposition
    http://greenbytes.de/tech/tc2231/
[ ] make HEAD request to detect temp filename from Content-Disposition
[ ] process HTTP status codes (i.e. 404 error)
    http://ftp.de.debian.org/debian/pool/iso-codes_3.24.2.orig.tar.bz2
[ ] catch KeyboardInterrupt
[ ] optionally preserve incomplete file
[x] create temp file in current directory
[ ] resume download (broken connection)
[ ] resume download (incomplete file)
[x] show progress indicator
    http://mail.python.org/pipermail/tutor/2005-May/038797.html
[x] do not overwrite downloaded file
 [x] rename file automatically if exists
[x] optionally specify path for downloaded file

[ ] options plan
 [x] -h, --help, --version (CHAOS speccy)
[ ] clpbar progress bar style
_ 30.0Mb at  3.0 Mbps  eta:   0:00:20   30% [=====         ]
[ ] test "bar \r" print with \r at the end of line on Windows
[ ] process Python 2.x urllib.ContentTooShortError exception gracefully
    (ideally retry and continue download)

    (tmpfile, headers) = urllib.urlretrieve(url, tmpfile, callback_progress)
  File "C:\Python27\lib\urllib.py", line 93, in urlretrieve
    return _urlopener.retrieve(url, filename, reporthook, data)
  File "C:\Python27\lib\urllib.py", line 283, in retrieve
    "of %i bytes" % (read, size), result)
urllib.ContentTooShortError: retrieval incomplete: got only 15239952 out of 24807571 bytes

[ ] find out if urlretrieve may return unicode headers
[ ] write files with unicode characters
    https://bitbucket.org/techtonik/python-wget/issues/7/filename-issue
  [x] Python 2, Windows
  [x] Python 3, Windows
  [ ] Linux
[ ] add automatic tests
  [ ] specify unicode URL from command line
  [ ] specify unicode output file from command line
  [ ] test suite for unsafe filenames from url and from headers

[ ] security checks
  [ ] filename_from_url
  [ ] filename_from_headers
  [ ] MITM redirect from https URL
  [ ] https certificate check
  [ ] size+hash check helpers
    [ ] fail if size is known and mismatch
    [ ] fail if hash mismatch
"""

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc6402.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Modified by Russ Housley to add a maps for CMC Control Attributes
#   and CMC Content Types for use with opentypes.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Certificate Management over CMS (CMC) Updates
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc6402.txt
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc4211
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5652

MAX = float('inf')


def _buildOid(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


# Since CMS Attributes and CMC Controls both use 'attrType', one map is used 
cmcControlAttributesMap = rfc5652.cmsAttributesMap


class ChangeSubjectName(univ.Sequence):
    pass


ChangeSubjectName.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('subject', rfc5280.Name()),
    namedtype.OptionalNamedType('subjectAlt', rfc5280.GeneralNames())
)


class AttributeValue(univ.Any):
    pass


class CMCStatus(univ.Integer):
    pass


CMCStatus.namedValues = namedval.NamedValues(
    ('success', 0),
    ('failed', 2),
    ('pending', 3),
    ('noSupport', 4),
    ('confirmRequired', 5),
    ('popRequired', 6),
    ('partial', 7)
)


class PendInfo(univ.Sequence):
    pass


PendInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pendToken', univ.OctetString()),
    namedtype.NamedType('pendTime', useful.GeneralizedTime())
)

bodyIdMax = univ.Integer(4294967295)


class BodyPartID(univ.Integer):
    pass


BodyPartID.subtypeSpec = constraint.ValueRangeConstraint(0, bodyIdMax)


class BodyPartPath(univ.SequenceOf):
    pass


BodyPartPath.componentType = BodyPartID()
BodyPartPath.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class BodyPartReference(univ.Choice):
    pass


BodyPartReference.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('bodyPartPath', BodyPartPath())
)


class CMCFailInfo(univ.Integer):
    pass


CMCFailInfo.namedValues = namedval.NamedValues(
    ('badAlg', 0),
    ('badMessageCheck', 1),
    ('badRequest', 2),
    ('badTime', 3),
    ('badCertId', 4),
    ('unsupportedExt', 5),
    ('mustArchiveKeys', 6),
    ('badIdentity', 7),
    ('popRequired', 8),
    ('popFailed', 9),
    ('noKeyReuse', 10),
    ('internalCAError', 11),
    ('tryLater', 12),
    ('authDataFail', 13)
)


class CMCStatusInfoV2(univ.Sequence):
    pass


CMCStatusInfoV2.componentType = namedtype.NamedTypes(
    namedtype.NamedType('cMCStatus', CMCStatus()),
    namedtype.NamedType('bodyList', univ.SequenceOf(componentType=BodyPartReference())),
    namedtype.OptionalNamedType('statusString', char.UTF8String()),
    namedtype.OptionalNamedType(
        'otherInfo', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('failInfo', CMCFailInfo()),
                namedtype.NamedType('pendInfo', PendInfo()),
                namedtype.NamedType(
                    'extendedFailInfo', univ.Sequence(
                    componentType=namedtype.NamedTypes(
                        namedtype.NamedType('failInfoOID', univ.ObjectIdentifier()),
                        namedtype.NamedType('failInfoValue', AttributeValue()))
                    )
                )
            )
        )
    )
)


class GetCRL(univ.Sequence):
    pass


GetCRL.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerName', rfc5280.Name()),
    namedtype.OptionalNamedType('cRLName', rfc5280.GeneralName()),
    namedtype.OptionalNamedType('time', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('reasons', rfc5280.ReasonFlags())
)

id_pkix = _buildOid(1, 3, 6, 1, 5, 5, 7)

id_cmc = _buildOid(id_pkix, 7)

id_cmc_batchResponses = _buildOid(id_cmc, 29)

id_cmc_popLinkWitness = _buildOid(id_cmc, 23)


class PopLinkWitnessV2(univ.Sequence):
    pass


PopLinkWitnessV2.componentType = namedtype.NamedTypes(
    namedtype.NamedType('keyGenAlgorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('macAlgorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('witness', univ.OctetString())
)

id_cmc_popLinkWitnessV2 = _buildOid(id_cmc, 33)

id_cmc_identityProofV2 = _buildOid(id_cmc, 34)

id_cmc_revokeRequest = _buildOid(id_cmc, 17)

id_cmc_recipientNonce = _buildOid(id_cmc, 7)


class ControlsProcessed(univ.Sequence):
    pass


ControlsProcessed.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyList', univ.SequenceOf(componentType=BodyPartReference()))
)


class CertificationRequest(univ.Sequence):
    pass


CertificationRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType(
        'certificationRequestInfo', univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('version', univ.Integer()),
                namedtype.NamedType('subject', rfc5280.Name()),
                namedtype.NamedType(
                    'subjectPublicKeyInfo', univ.Sequence(
                        componentType=namedtype.NamedTypes(
                            namedtype.NamedType('algorithm', rfc5280.AlgorithmIdentifier()),
                            namedtype.NamedType('subjectPublicKey', univ.BitString())
                        )
                    )
                ),
                namedtype.NamedType(
                    'attributes', univ.SetOf(
                        componentType=rfc5652.Attribute()).subtype(
                        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))
                )
            )
        )
    ),
    namedtype.NamedType('signatureAlgorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class TaggedCertificationRequest(univ.Sequence):
    pass


TaggedCertificationRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('certificationRequest', CertificationRequest())
)


class TaggedRequest(univ.Choice):
    pass


TaggedRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tcr', TaggedCertificationRequest().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('crm',
                        rfc4211.CertReqMsg().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('orm', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('bodyPartID', BodyPartID()),
        namedtype.NamedType('requestMessageType', univ.ObjectIdentifier()),
        namedtype.NamedType('requestMessageValue', univ.Any())
    ))
                        .subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)))
)

id_cmc_popLinkRandom = _buildOid(id_cmc, 22)

id_cmc_statusInfo = _buildOid(id_cmc, 1)

id_cmc_trustedAnchors = _buildOid(id_cmc, 26)

id_cmc_transactionId = _buildOid(id_cmc, 5)

id_cmc_encryptedPOP = _buildOid(id_cmc, 9)


class PublishTrustAnchors(univ.Sequence):
    pass


PublishTrustAnchors.componentType = namedtype.NamedTypes(
    namedtype.NamedType('seqNumber', univ.Integer()),
    namedtype.NamedType('hashAlgorithm', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('anchorHashes', univ.SequenceOf(componentType=univ.OctetString()))
)


class RevokeRequest(univ.Sequence):
    pass


RevokeRequest.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerName', rfc5280.Name()),
    namedtype.NamedType('serialNumber', univ.Integer()),
    namedtype.NamedType('reason', rfc5280.CRLReason()),
    namedtype.OptionalNamedType('invalidityDate', useful.GeneralizedTime()),
    namedtype.OptionalNamedType('passphrase', univ.OctetString()),
    namedtype.OptionalNamedType('comment', char.UTF8String())
)

id_cmc_senderNonce = _buildOid(id_cmc, 6)

id_cmc_authData = _buildOid(id_cmc, 27)


class TaggedContentInfo(univ.Sequence):
    pass


TaggedContentInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('contentInfo', rfc5652.ContentInfo())
)


class IdentifyProofV2(univ.Sequence):
    pass


IdentifyProofV2.componentType = namedtype.NamedTypes(
    namedtype.NamedType('proofAlgID', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('macAlgId', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('witness', univ.OctetString())
)


class CMCPublicationInfo(univ.Sequence):
    pass


CMCPublicationInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('hashAlg', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('certHashes', univ.SequenceOf(componentType=univ.OctetString())),
    namedtype.NamedType('pubInfo', rfc4211.PKIPublicationInfo())
)

id_kp_cmcCA = _buildOid(rfc5280.id_kp, 27)

id_cmc_confirmCertAcceptance = _buildOid(id_cmc, 24)

id_cmc_raIdentityWitness = _buildOid(id_cmc, 35)

id_ExtensionReq = _buildOid(1, 2, 840, 113549, 1, 9, 14)

id_cct = _buildOid(id_pkix, 12)

id_cct_PKIData = _buildOid(id_cct, 2)

id_kp_cmcRA = _buildOid(rfc5280.id_kp, 28)


class CMCStatusInfo(univ.Sequence):
    pass


CMCStatusInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('cMCStatus', CMCStatus()),
    namedtype.NamedType('bodyList', univ.SequenceOf(componentType=BodyPartID())),
    namedtype.OptionalNamedType('statusString', char.UTF8String()),
    namedtype.OptionalNamedType(
        'otherInfo', univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('failInfo', CMCFailInfo()),
                namedtype.NamedType('pendInfo', PendInfo())
            )
        )
    )
)


class DecryptedPOP(univ.Sequence):
    pass


DecryptedPOP.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('thePOPAlgID', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('thePOP', univ.OctetString())
)

id_cmc_addExtensions = _buildOid(id_cmc, 8)

id_cmc_modCertTemplate = _buildOid(id_cmc, 31)


class TaggedAttribute(univ.Sequence):
    pass


TaggedAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('attrType', univ.ObjectIdentifier()),
    namedtype.NamedType('attrValues', univ.SetOf(componentType=AttributeValue()),
        openType=opentype.OpenType('attrType', cmcControlAttributesMap)
    )
)


class OtherMsg(univ.Sequence):
    pass


OtherMsg.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartID', BodyPartID()),
    namedtype.NamedType('otherMsgType', univ.ObjectIdentifier()),
    namedtype.NamedType('otherMsgValue', univ.Any())
)


class PKIData(univ.Sequence):
    pass


PKIData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('controlSequence', univ.SequenceOf(componentType=TaggedAttribute())),
    namedtype.NamedType('reqSequence', univ.SequenceOf(componentType=TaggedRequest())),
    namedtype.NamedType('cmsSequence', univ.SequenceOf(componentType=TaggedContentInfo())),
    namedtype.NamedType('otherMsgSequence', univ.SequenceOf(componentType=OtherMsg()))
)


class BodyPartList(univ.SequenceOf):
    pass


BodyPartList.componentType = BodyPartID()
BodyPartList.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_cmc_responseBody = _buildOid(id_cmc, 37)


class AuthPublish(BodyPartID):
    pass


class CMCUnsignedData(univ.Sequence):
    pass


CMCUnsignedData.componentType = namedtype.NamedTypes(
    namedtype.NamedType('bodyPartPath', BodyPartPath()),
    namedtype.NamedType('identifier', univ.ObjectIdentifier()),
    namedtype.NamedType('content', univ.Any())
)


class CMCCertId(rfc5652.IssuerAndSerialNumber):
    pass


class PKIResponse(univ.Sequence):
    pass


PKIResponse.componentType = namedtype.NamedTypes(
    namedtype.NamedType('controlSequence', univ.SequenceOf(componentType=TaggedAttribute())),
    namedtype.NamedType('cmsSequence', univ.SequenceOf(componentType=TaggedContentInfo())),
    namedtype.NamedType('otherMsgSequence', univ.SequenceOf(componentType=OtherMsg()))
)


class ResponseBody(PKIResponse):
    pass


id_cmc_statusInfoV2 = _buildOid(id_cmc, 25)

id_cmc_lraPOPWitness = _buildOid(id_cmc, 11)


class ModCertTemplate(univ.Sequence):
    pass


ModCertTemplate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pkiDataReference', BodyPartPath()),
    namedtype.NamedType('certReferences', BodyPartList()),
    namedtype.DefaultedNamedType('replace', univ.Boolean().subtype(value=1)),
    namedtype.NamedType('certTemplate', rfc4211.CertTemplate())
)

id_cmc_regInfo = _buildOid(id_cmc, 18)

id_cmc_identityProof = _buildOid(id_cmc, 3)


class ExtensionReq(univ.SequenceOf):
    pass


ExtensionReq.componentType = rfc5280.Extension()
ExtensionReq.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_kp_cmcArchive = _buildOid(rfc5280.id_kp, 28)

id_cmc_publishCert = _buildOid(id_cmc, 30)

id_cmc_dataReturn = _buildOid(id_cmc, 4)


class LraPopWitness(univ.Sequence):
    pass


LraPopWitness.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pkiDataBodyid', BodyPartID()),
    namedtype.NamedType('bodyIds', univ.SequenceOf(componentType=BodyPartID()))
)

id_aa = _buildOid(1, 2, 840, 113549, 1, 9, 16, 2)

id_aa_cmc_unsignedData = _buildOid(id_aa, 34)

id_cmc_getCert = _buildOid(id_cmc, 15)

id_cmc_batchRequests = _buildOid(id_cmc, 28)

id_cmc_decryptedPOP = _buildOid(id_cmc, 10)

id_cmc_responseInfo = _buildOid(id_cmc, 19)

id_cmc_changeSubjectName = _buildOid(id_cmc, 36)


class GetCert(univ.Sequence):
    pass


GetCert.componentType = namedtype.NamedTypes(
    namedtype.NamedType('issuerName', rfc5280.GeneralName()),
    namedtype.NamedType('serialNumber', univ.Integer())
)

id_cmc_identification = _buildOid(id_cmc, 2)

id_cmc_queryPending = _buildOid(id_cmc, 21)


class AddExtensions(univ.Sequence):
    pass


AddExtensions.componentType = namedtype.NamedTypes(
    namedtype.NamedType('pkiDataReference', BodyPartID()),
    namedtype.NamedType('certReferences', univ.SequenceOf(componentType=BodyPartID())),
    namedtype.NamedType('extensions', univ.SequenceOf(componentType=rfc5280.Extension()))
)


class EncryptedPOP(univ.Sequence):
    pass


EncryptedPOP.componentType = namedtype.NamedTypes(
    namedtype.NamedType('request', TaggedRequest()),
    namedtype.NamedType('cms', rfc5652.ContentInfo()),
    namedtype.NamedType('thePOPAlgID', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('witnessAlgID', rfc5280.AlgorithmIdentifier()),
    namedtype.NamedType('witness', univ.OctetString())
)

id_cmc_getCRL = _buildOid(id_cmc, 16)

id_cct_PKIResponse = _buildOid(id_cct, 3)

id_cmc_controlProcessed = _buildOid(id_cmc, 32)


class NoSignatureValue(univ.OctetString):
    pass


id_ad_cmc = _buildOid(rfc5280.id_ad, 12)

id_alg_noSignature = _buildOid(id_pkix, 6, 2)


# Map of CMC Control OIDs to CMC Control Attributes

_cmcControlAttributesMapUpdate = {
    id_cmc_statusInfo: CMCStatusInfo(),
    id_cmc_statusInfoV2: CMCStatusInfoV2(),
    id_cmc_identification: char.UTF8String(),
    id_cmc_identityProof: univ.OctetString(),
    id_cmc_identityProofV2: IdentifyProofV2(),
    id_cmc_dataReturn: univ.OctetString(),
    id_cmc_transactionId: univ.Integer(),
    id_cmc_senderNonce: univ.OctetString(),
    id_cmc_recipientNonce: univ.OctetString(),
    id_cmc_addExtensions: AddExtensions(),
    id_cmc_encryptedPOP: EncryptedPOP(),
    id_cmc_decryptedPOP: DecryptedPOP(),
    id_cmc_lraPOPWitness: LraPopWitness(),
    id_cmc_getCert: GetCert(),
    id_cmc_getCRL: GetCRL(),
    id_cmc_revokeRequest: RevokeRequest(),
    id_cmc_regInfo: univ.OctetString(),
    id_cmc_responseInfo: univ.OctetString(),
    id_cmc_queryPending: univ.OctetString(),
    id_cmc_popLinkRandom: univ.OctetString(),
    id_cmc_popLinkWitness: univ.OctetString(),
    id_cmc_popLinkWitnessV2: PopLinkWitnessV2(),
    id_cmc_confirmCertAcceptance: CMCCertId(),
    id_cmc_trustedAnchors: PublishTrustAnchors(),
    id_cmc_authData: AuthPublish(),
    id_cmc_batchRequests: BodyPartList(),
    id_cmc_batchResponses: BodyPartList(),
    id_cmc_publishCert: CMCPublicationInfo(),
    id_cmc_modCertTemplate: ModCertTemplate(),
    id_cmc_controlProcessed: ControlsProcessed(),
    id_ExtensionReq: ExtensionReq(),
}

cmcControlAttributesMap.update(_cmcControlAttributesMapUpdate)


# Map of CMC Content Type OIDs to CMC Content Types are added to
# the ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_cct_PKIData: PKIData(),
    id_cct_PKIResponse: PKIResponse(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)


# === NexusCore/openenv\Lib\site-packages\google\auth\external_account.py ===
# Copyright 2020 Google LLC
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

"""External Account Credentials.

This module provides credentials that exchange workload identity pool external
credentials for Google access tokens. This facilitates accessing Google Cloud
Platform resources from on-prem and non-Google Cloud platforms (e.g. AWS,
Microsoft Azure, OIDC identity providers), using native credentials retrieved
from the current environment without the need to copy, save and manage
long-lived service account credentials.

Specifically, this is intended to use access tokens acquired using the GCP STS
token exchange endpoint following the `OAuth 2.0 Token Exchange`_ spec.

.. _OAuth 2.0 Token Exchange: https://tools.ietf.org/html/rfc8693
"""

import abc
import copy
from dataclasses import dataclass
import datetime
import functools
import io
import json
import re

from google.auth import _helpers
from google.auth import credentials
from google.auth import exceptions
from google.auth import impersonated_credentials
from google.auth import metrics
from google.oauth2 import sts
from google.oauth2 import utils

# External account JSON type identifier.
_EXTERNAL_ACCOUNT_JSON_TYPE = "external_account"
# The token exchange grant_type used for exchanging credentials.
_STS_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:token-exchange"
# The token exchange requested_token_type. This is always an access_token.
_STS_REQUESTED_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
# Cloud resource manager URL used to retrieve project information.
_CLOUD_RESOURCE_MANAGER = "https://cloudresourcemanager.googleapis.com/v1/projects/"
# Default Google sts token url.
_DEFAULT_TOKEN_URL = "https://sts.{universe_domain}/v1/token"


@dataclass
class SupplierContext:
    """A context class that contains information about the requested third party credential that is passed
        to AWS security credential and subject token suppliers.

        Attributes:
            subject_token_type (str): The requested subject token type based on the Oauth2.0 token exchange spec.
                Expected values include::

                    “urn:ietf:params:oauth:token-type:jwt”
                    “urn:ietf:params:oauth:token-type:id-token”
                    “urn:ietf:params:oauth:token-type:saml2”
                    “urn:ietf:params:aws:token-type:aws4_request”

            audience (str): The requested audience for the subject token.
    """

    subject_token_type: str
    audience: str


class Credentials(
    credentials.Scoped,
    credentials.CredentialsWithQuotaProject,
    credentials.CredentialsWithTokenUri,
    metaclass=abc.ABCMeta,
):
    """Base class for all external account credentials.

    This is used to instantiate Credentials for exchanging external account
    credentials for Google access token and authorizing requests to Google APIs.
    The base class implements the common logic for exchanging external account
    credentials for Google access tokens.
    """

    def __init__(
        self,
        audience,
        subject_token_type,
        token_url,
        credential_source,
        service_account_impersonation_url=None,
        service_account_impersonation_options=None,
        client_id=None,
        client_secret=None,
        token_info_url=None,
        quota_project_id=None,
        scopes=None,
        default_scopes=None,
        workforce_pool_user_project=None,
        universe_domain=credentials.DEFAULT_UNIVERSE_DOMAIN,
        trust_boundary=None,
    ):
        """Instantiates an external account credentials object.

        Args:
            audience (str): The STS audience field.
            subject_token_type (str): The subject token type based on the Oauth2.0 token exchange spec.
                Expected values include::

                    “urn:ietf:params:oauth:token-type:jwt”
                    “urn:ietf:params:oauth:token-type:id-token”
                    “urn:ietf:params:oauth:token-type:saml2”
                    “urn:ietf:params:aws:token-type:aws4_request”

            token_url (str): The STS endpoint URL.
            credential_source (Mapping): The credential source dictionary.
            service_account_impersonation_url (Optional[str]): The optional service account
                impersonation generateAccessToken URL.
            client_id (Optional[str]): The optional client ID.
            client_secret (Optional[str]): The optional client secret.
            token_info_url (str): The optional STS endpoint URL for token introspection.
            quota_project_id (Optional[str]): The optional quota project ID.
            scopes (Optional[Sequence[str]]): Optional scopes to request during the
                authorization grant.
            default_scopes (Optional[Sequence[str]]): Default scopes passed by a
                Google client library. Use 'scopes' for user-defined scopes.
            workforce_pool_user_project (Optona[str]): The optional workforce pool user
                project number when the credential corresponds to a workforce pool and not
                a workload identity pool. The underlying principal must still have
                serviceusage.services.use IAM permission to use the project for
                billing/quota.
            universe_domain (str): The universe domain. The default universe
                domain is googleapis.com.
            trust_boundary (str): String representation of trust boundary meta.
        Raises:
            google.auth.exceptions.RefreshError: If the generateAccessToken
                endpoint returned an error.
        """
        super(Credentials, self).__init__()
        self._audience = audience
        self._subject_token_type = subject_token_type
        self._universe_domain = universe_domain
        self._token_url = token_url
        if self._token_url == _DEFAULT_TOKEN_URL:
            self._token_url = self._token_url.replace(
                "{universe_domain}", self._universe_domain
            )
        self._token_info_url = token_info_url
        self._credential_source = credential_source
        self._service_account_impersonation_url = service_account_impersonation_url
        self._service_account_impersonation_options = (
            service_account_impersonation_options or {}
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._quota_project_id = quota_project_id
        self._scopes = scopes
        self._default_scopes = default_scopes
        self._workforce_pool_user_project = workforce_pool_user_project
        self._trust_boundary = {
            "locations": [],
            "encoded_locations": "0x0",
        }  # expose a placeholder trust boundary value.

        if self._client_id:
            self._client_auth = utils.ClientAuthentication(
                utils.ClientAuthType.basic, self._client_id, self._client_secret
            )
        else:
            self._client_auth = None
        self._sts_client = sts.Client(self._token_url, self._client_auth)

        self._metrics_options = self._create_default_metrics_options()

        self._impersonated_credentials = None
        self._project_id = None
        self._supplier_context = SupplierContext(
            self._subject_token_type, self._audience
        )
        self._cred_file_path = None

        if not self.is_workforce_pool and self._workforce_pool_user_project:
            # Workload identity pools do not support workforce pool user projects.
            raise exceptions.InvalidValue(
                "workforce_pool_user_project should not be set for non-workforce pool "
                "credentials"
            )

    @property
    def info(self):
        """Generates the dictionary representation of the current credentials.

        Returns:
            Mapping: The dictionary representation of the credentials. This is the
                reverse of "from_info" defined on the subclasses of this class. It is
                useful for serializing the current credentials so it can deserialized
                later.
        """
        config_info = self._constructor_args()
        config_info.update(
            type=_EXTERNAL_ACCOUNT_JSON_TYPE,
            service_account_impersonation=config_info.pop(
                "service_account_impersonation_options", None
            ),
        )
        config_info.pop("scopes", None)
        config_info.pop("default_scopes", None)
        return {key: value for key, value in config_info.items() if value is not None}

    def _constructor_args(self):
        args = {
            "audience": self._audience,
            "subject_token_type": self._subject_token_type,
            "token_url": self._token_url,
            "token_info_url": self._token_info_url,
            "service_account_impersonation_url": self._service_account_impersonation_url,
            "service_account_impersonation_options": copy.deepcopy(
                self._service_account_impersonation_options
            )
            or None,
            "credential_source": copy.deepcopy(self._credential_source),
            "quota_project_id": self._quota_project_id,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "workforce_pool_user_project": self._workforce_pool_user_project,
            "scopes": self._scopes,
            "default_scopes": self._default_scopes,
            "universe_domain": self._universe_domain,
        }
        if not self.is_workforce_pool:
            args.pop("workforce_pool_user_project")
        return args

    @property
    def service_account_email(self):
        """Returns the service account email if service account impersonation is used.

        Returns:
            Optional[str]: The service account email if impersonation is used. Otherwise
                None is returned.
        """
        if self._service_account_impersonation_url:
            # Parse email from URL. The formal looks as follows:
            # https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/name@project-id.iam.gserviceaccount.com:generateAccessToken
            url = self._service_account_impersonation_url
            start_index = url.rfind("/")
            end_index = url.find(":generateAccessToken")
            if start_index != -1 and end_index != -1 and start_index < end_index:
                start_index = start_index + 1
                return url[start_index:end_index]
        return None

    @property
    def is_user(self):
        """Returns whether the credentials represent a user (True) or workload (False).
        Workloads behave similarly to service accounts. Currently workloads will use
        service account impersonation but will eventually not require impersonation.
        As a result, this property is more reliable than the service account email
        property in determining if the credentials represent a user or workload.

        Returns:
            bool: True if the credentials represent a user. False if they represent a
                workload.
        """
        # If service account impersonation is used, the credentials will always represent a
        # service account.
        if self._service_account_impersonation_url:
            return False
        return self.is_workforce_pool

    @property
    def is_workforce_pool(self):
        """Returns whether the credentials represent a workforce pool (True) or
        workload (False) based on the credentials' audience.

        This will also return True for impersonated workforce pool credentials.

        Returns:
            bool: True if the credentials represent a workforce pool. False if they
                represent a workload.
        """
        # Workforce pools representing users have the following audience format:
        # //iam.googleapis.com/locations/$location/workforcePools/$poolId/providers/$providerId
        p = re.compile(r"//iam\.googleapis\.com/locations/[^/]+/workforcePools/")
        return p.match(self._audience or "") is not None

    @property
    def requires_scopes(self):
        """Checks if the credentials requires scopes.

        Returns:
            bool: True if there are no scopes set otherwise False.
        """
        return not self._scopes and not self._default_scopes

    @property
    def project_number(self):
        """Optional[str]: The project number corresponding to the workload identity pool."""

        # STS audience pattern:
        # //iam.googleapis.com/projects/$PROJECT_NUMBER/locations/...
        components = self._audience.split("/")
        try:
            project_index = components.index("projects")
            if project_index + 1 < len(components):
                return components[project_index + 1] or None
        except ValueError:
            return None

    @property
    def token_info_url(self):
        """Optional[str]: The STS token introspection endpoint."""

        return self._token_info_url

    @_helpers.copy_docstring(credentials.Credentials)
    def get_cred_info(self):
        if self._cred_file_path:
            cred_info_json = {
                "credential_source": self._cred_file_path,
                "credential_type": "external account credentials",
            }
            if self.service_account_email:
                cred_info_json["principal"] = self.service_account_email
            return cred_info_json
        return None

    @_helpers.copy_docstring(credentials.Scoped)
    def with_scopes(self, scopes, default_scopes=None):
        kwargs = self._constructor_args()
        kwargs.update(scopes=scopes, default_scopes=default_scopes)
        scoped = self.__class__(**kwargs)
        scoped._cred_file_path = self._cred_file_path
        scoped._metrics_options = self._metrics_options
        return scoped

    @abc.abstractmethod
    def retrieve_subject_token(self, request):
        """Retrieves the subject token using the credential_source object.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
        Returns:
            str: The retrieved subject token.
        """
        # pylint: disable=missing-raises-doc
        # (pylint doesn't recognize that this is abstract)
        raise NotImplementedError("retrieve_subject_token must be implemented")

    def get_project_id(self, request):
        """Retrieves the project ID corresponding to the workload identity or workforce pool.
        For workforce pool credentials, it returns the project ID corresponding to
        the workforce_pool_user_project.

        When not determinable, None is returned.

        This is introduced to support the current pattern of using the Auth library:

            credentials, project_id = google.auth.default()

        The resource may not have permission (resourcemanager.projects.get) to
        call this API or the required scopes may not be selected:
        https://cloud.google.com/resource-manager/reference/rest/v1/projects/get#authorization-scopes

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
        Returns:
            Optional[str]: The project ID corresponding to the workload identity pool
                or workforce pool if determinable.
        """
        if self._project_id:
            # If already retrieved, return the cached project ID value.
            return self._project_id
        scopes = self._scopes if self._scopes is not None else self._default_scopes
        # Scopes are required in order to retrieve a valid access token.
        project_number = self.project_number or self._workforce_pool_user_project
        if project_number and scopes:
            headers = {}
            url = _CLOUD_RESOURCE_MANAGER + project_number
            self.before_request(request, "GET", url, headers)
            response = request(url=url, method="GET", headers=headers)

            response_body = (
                response.data.decode("utf-8")
                if hasattr(response.data, "decode")
                else response.data
            )
            response_data = json.loads(response_body)

            if response.status == 200:
                # Cache result as this field is immutable.
                self._project_id = response_data.get("projectId")
                return self._project_id

        return None

    @_helpers.copy_docstring(credentials.Credentials)
    def refresh(self, request):
        scopes = self._scopes if self._scopes is not None else self._default_scopes

        # Inject client certificate into request.
        if self._mtls_required():
            request = functools.partial(
                request, cert=self._get_mtls_cert_and_key_paths()
            )

        if self._should_initialize_impersonated_credentials():
            self._impersonated_credentials = self._initialize_impersonated_credentials()

        if self._impersonated_credentials:
            self._impersonated_credentials.refresh(request)
            self.token = self._impersonated_credentials.token
            self.expiry = self._impersonated_credentials.expiry
        else:
            now = _helpers.utcnow()
            additional_options = None
            # Do not pass workforce_pool_user_project when client authentication
            # is used. The client ID is sufficient for determining the user project.
            if self._workforce_pool_user_project and not self._client_id:
                additional_options = {"userProject": self._workforce_pool_user_project}
            additional_headers = {
                metrics.API_CLIENT_HEADER: metrics.byoid_metrics_header(
                    self._metrics_options
                )
            }
            response_data = self._sts_client.exchange_token(
                request=request,
                grant_type=_STS_GRANT_TYPE,
                subject_token=self.retrieve_subject_token(request),
                subject_token_type=self._subject_token_type,
                audience=self._audience,
                scopes=scopes,
                requested_token_type=_STS_REQUESTED_TOKEN_TYPE,
                additional_options=additional_options,
                additional_headers=additional_headers,
            )
            self.token = response_data.get("access_token")
            expires_in = response_data.get("expires_in")
            # Some services do not respect the OAUTH2.0 RFC and send expires_in as a
            # JSON String.
            if isinstance(expires_in, str):
                expires_in = int(expires_in)

            lifetime = datetime.timedelta(seconds=expires_in)

            self.expiry = now + lifetime

    def _make_copy(self):
        kwargs = self._constructor_args()
        new_cred = self.__class__(**kwargs)
        new_cred._cred_file_path = self._cred_file_path
        new_cred._metrics_options = self._metrics_options
        return new_cred

    @_helpers.copy_docstring(credentials.CredentialsWithQuotaProject)
    def with_quota_project(self, quota_project_id):
        # Return copy of instance with the provided quota project ID.
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

    def _should_initialize_impersonated_credentials(self):
        return (
            self._service_account_impersonation_url is not None
            and self._impersonated_credentials is None
        )

    def _initialize_impersonated_credentials(self):
        """Generates an impersonated credentials.

        For more details, see `projects.serviceAccounts.generateAccessToken`_.

        .. _projects.serviceAccounts.generateAccessToken: https://cloud.google.com/iam/docs/reference/credentials/rest/v1/projects.serviceAccounts/generateAccessToken

        Returns:
            impersonated_credentials.Credential: The impersonated credentials
                object.

        Raises:
            google.auth.exceptions.RefreshError: If the generateAccessToken
                endpoint returned an error.
        """
        # Return copy of instance with no service account impersonation.
        kwargs = self._constructor_args()
        kwargs.update(
            service_account_impersonation_url=None,
            service_account_impersonation_options={},
        )
        source_credentials = self.__class__(**kwargs)
        source_credentials._metrics_options = self._metrics_options

        # Determine target_principal.
        target_principal = self.service_account_email
        if not target_principal:
            raise exceptions.RefreshError(
                "Unable to determine target principal from service account impersonation URL."
            )

        scopes = self._scopes if self._scopes is not None else self._default_scopes
        # Initialize and return impersonated credentials.
        return impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=scopes,
            quota_project_id=self._quota_project_id,
            iam_endpoint_override=self._service_account_impersonation_url,
            lifetime=self._service_account_impersonation_options.get(
                "token_lifetime_seconds"
            ),
        )

    def _create_default_metrics_options(self):
        metrics_options = {}
        if self._service_account_impersonation_url:
            metrics_options["sa-impersonation"] = "true"
        else:
            metrics_options["sa-impersonation"] = "false"
        if self._service_account_impersonation_options.get("token_lifetime_seconds"):
            metrics_options["config-lifetime"] = "true"
        else:
            metrics_options["config-lifetime"] = "false"

        return metrics_options

    def _mtls_required(self):
        """Returns a boolean representing whether the current credential is configured
        for mTLS and should add a certificate to the outgoing calls to the sts and service
        account impersonation endpoint.

        Returns:
            bool: True if the credential is configured for mTLS, False if it is not.
        """
        return False

    def _get_mtls_cert_and_key_paths(self):
        """Gets the file locations for a certificate and private key file
        to be used for configuring mTLS for the sts and service account
        impersonation calls. Currently only expected to return a value when using
        X509 workload identity federation.

        Returns:
            Tuple[str, str]: The cert and key file locations as strings in a tuple.

        Raises:
            NotImplementedError: When the current credential is not configured for
                mTLS.
        """
        raise NotImplementedError(
            "_get_mtls_cert_and_key_location must be implemented."
        )

    @classmethod
    def from_info(cls, info, **kwargs):
        """Creates a Credentials instance from parsed external account info.

        Args:
            info (Mapping[str, str]): The external account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.identity_pool.Credentials: The constructed
                credentials.

        Raises:
            InvalidValue: For invalid parameters.
        """
        return cls(
            audience=info.get("audience"),
            subject_token_type=info.get("subject_token_type"),
            token_url=info.get("token_url"),
            token_info_url=info.get("token_info_url"),
            service_account_impersonation_url=info.get(
                "service_account_impersonation_url"
            ),
            service_account_impersonation_options=info.get(
                "service_account_impersonation"
            )
            or {},
            client_id=info.get("client_id"),
            client_secret=info.get("client_secret"),
            credential_source=info.get("credential_source"),
            quota_project_id=info.get("quota_project_id"),
            workforce_pool_user_project=info.get("workforce_pool_user_project"),
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
            google.auth.identity_pool.Credentials: The constructed
                credentials.
        """
        with io.open(filename, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
            return cls.from_info(data, **kwargs)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\file_service\transports\rest.py ===
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

import dataclasses
import json  # type: ignore
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, path_template, rest_helpers, rest_streaming
from google.api_core import exceptions as core_exceptions
from google.api_core import retry as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.auth.transport.requests import AuthorizedSession  # type: ignore
from google.protobuf import json_format
import grpc  # type: ignore
from requests import __version__ as requests_version

try:
    OptionalRetry = Union[retries.Retry, gapic_v1.method._MethodDefault, None]
except AttributeError:  # pragma: NO COVER
    OptionalRetry = Union[retries.Retry, object, None]  # type: ignore


from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta.types import file, file_service

from .base import DEFAULT_CLIENT_INFO as BASE_DEFAULT_CLIENT_INFO
from .base import FileServiceTransport

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=BASE_DEFAULT_CLIENT_INFO.gapic_version,
    grpc_version=None,
    rest_version=requests_version,
)


class FileServiceRestInterceptor:
    """Interceptor for FileService.

    Interceptors are used to manipulate requests, request metadata, and responses
    in arbitrary ways.
    Example use cases include:
    * Logging
    * Verifying requests according to service or custom semantics
    * Stripping extraneous information from responses

    These use cases and more can be enabled by injecting an
    instance of a custom subclass when constructing the FileServiceRestTransport.

    .. code-block:: python
        class MyCustomFileServiceInterceptor(FileServiceRestInterceptor):
            def pre_create_file(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_create_file(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_delete_file(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def pre_get_file(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_get_file(self, response):
                logging.log(f"Received response: {response}")
                return response

            def pre_list_files(self, request, metadata):
                logging.log(f"Received request: {request}")
                return request, metadata

            def post_list_files(self, response):
                logging.log(f"Received response: {response}")
                return response

        transport = FileServiceRestTransport(interceptor=MyCustomFileServiceInterceptor())
        client = FileServiceClient(transport=transport)


    """

    def pre_create_file(
        self,
        request: file_service.CreateFileRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[file_service.CreateFileRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for create_file

        Override in a subclass to manipulate the request or metadata
        before they are sent to the FileService server.
        """
        return request, metadata

    def post_create_file(
        self, response: file_service.CreateFileResponse
    ) -> file_service.CreateFileResponse:
        """Post-rpc interceptor for create_file

        Override in a subclass to manipulate the response
        after it is returned by the FileService server but before
        it is returned to user code.
        """
        return response

    def pre_delete_file(
        self,
        request: file_service.DeleteFileRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[file_service.DeleteFileRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for delete_file

        Override in a subclass to manipulate the request or metadata
        before they are sent to the FileService server.
        """
        return request, metadata

    def pre_get_file(
        self, request: file_service.GetFileRequest, metadata: Sequence[Tuple[str, str]]
    ) -> Tuple[file_service.GetFileRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for get_file

        Override in a subclass to manipulate the request or metadata
        before they are sent to the FileService server.
        """
        return request, metadata

    def post_get_file(self, response: file.File) -> file.File:
        """Post-rpc interceptor for get_file

        Override in a subclass to manipulate the response
        after it is returned by the FileService server but before
        it is returned to user code.
        """
        return response

    def pre_list_files(
        self,
        request: file_service.ListFilesRequest,
        metadata: Sequence[Tuple[str, str]],
    ) -> Tuple[file_service.ListFilesRequest, Sequence[Tuple[str, str]]]:
        """Pre-rpc interceptor for list_files

        Override in a subclass to manipulate the request or metadata
        before they are sent to the FileService server.
        """
        return request, metadata

    def post_list_files(
        self, response: file_service.ListFilesResponse
    ) -> file_service.ListFilesResponse:
        """Post-rpc interceptor for list_files

        Override in a subclass to manipulate the response
        after it is returned by the FileService server but before
        it is returned to user code.
        """
        return response


@dataclasses.dataclass
class FileServiceRestStub:
    _session: AuthorizedSession
    _host: str
    _interceptor: FileServiceRestInterceptor


class FileServiceRestTransport(FileServiceTransport):
    """REST backend transport for FileService.

    An API for uploading and managing files.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends JSON representations of protocol buffers over HTTP/1.1

    """

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        url_scheme: str = "https",
        interceptor: Optional[FileServiceRestInterceptor] = None,
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

            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if ``channel`` is provided.
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if ``channel`` is provided.
            client_cert_source_for_mtls (Callable[[], Tuple[bytes, bytes]]): Client
                certificate to configure mutual TLS HTTP channel. It is ignored
                if ``channel`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you are developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
            url_scheme: the protocol scheme for the API endpoint.  Normally
                "https", but for testing or local servers,
                "http" can be specified.
        """
        # Run the base constructor
        # TODO(yon-mg): resolve other ctor params i.e. scopes, quota, etc.
        # TODO: When custom host (api_endpoint) is set, `scopes` must *also* be set on the
        # credentials object
        maybe_url_match = re.match("^(?P<scheme>http(?:s)?://)?(?P<host>.*)$", host)
        if maybe_url_match is None:
            raise ValueError(
                f"Unexpected hostname structure: {host}"
            )  # pragma: NO COVER

        url_match_items = maybe_url_match.groupdict()

        host = f"{url_scheme}://{host}" if not url_match_items["scheme"] else host

        super().__init__(
            host=host,
            credentials=credentials,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )
        self._session = AuthorizedSession(
            self._credentials, default_host=self.DEFAULT_HOST
        )
        if client_cert_source_for_mtls:
            self._session.configure_mtls_channel(client_cert_source_for_mtls)
        self._interceptor = interceptor or FileServiceRestInterceptor()
        self._prep_wrapped_messages(client_info)

    class _CreateFile(FileServiceRestStub):
        def __hash__(self):
            return hash("CreateFile")

        def __call__(
            self,
            request: file_service.CreateFileRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> file_service.CreateFileResponse:
            r"""Call the create file method over HTTP.

            Args:
                request (~.file_service.CreateFileRequest):
                    The request object. Request for ``CreateFile``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.file_service.CreateFileResponse:
                    Response for ``CreateFile``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "post",
                    "uri": "/v1beta/files",
                    "body": "*",
                },
            ]
            request, metadata = self._interceptor.pre_create_file(request, metadata)
            pb_request = file_service.CreateFileRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            # Jsonify the request body

            body = json_format.MessageToJson(
                transcoded_request["body"], use_integers_for_enums=True
            )
            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
                data=body,
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = file_service.CreateFileResponse()
            pb_resp = file_service.CreateFileResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_create_file(resp)
            return resp

    class _DeleteFile(FileServiceRestStub):
        def __hash__(self):
            return hash("DeleteFile")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: file_service.DeleteFileRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ):
            r"""Call the delete file method over HTTP.

            Args:
                request (~.file_service.DeleteFileRequest):
                    The request object. Request for ``DeleteFile``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "delete",
                    "uri": "/v1beta/{name=files/*}",
                },
            ]
            request, metadata = self._interceptor.pre_delete_file(request, metadata)
            pb_request = file_service.DeleteFileRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

    class _GetFile(FileServiceRestStub):
        def __hash__(self):
            return hash("GetFile")

        __REQUIRED_FIELDS_DEFAULT_VALUES: Dict[str, Any] = {}

        @classmethod
        def _get_unset_required_fields(cls, message_dict):
            return {
                k: v
                for k, v in cls.__REQUIRED_FIELDS_DEFAULT_VALUES.items()
                if k not in message_dict
            }

        def __call__(
            self,
            request: file_service.GetFileRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> file.File:
            r"""Call the get file method over HTTP.

            Args:
                request (~.file_service.GetFileRequest):
                    The request object. Request for ``GetFile``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.file.File:
                    A file uploaded to the API.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/{name=files/*}",
                },
            ]
            request, metadata = self._interceptor.pre_get_file(request, metadata)
            pb_request = file_service.GetFileRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )
            query_params.update(self._get_unset_required_fields(query_params))

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = file.File()
            pb_resp = file.File.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_get_file(resp)
            return resp

    class _ListFiles(FileServiceRestStub):
        def __hash__(self):
            return hash("ListFiles")

        def __call__(
            self,
            request: file_service.ListFilesRequest,
            *,
            retry: OptionalRetry = gapic_v1.method.DEFAULT,
            timeout: Optional[float] = None,
            metadata: Sequence[Tuple[str, str]] = (),
        ) -> file_service.ListFilesResponse:
            r"""Call the list files method over HTTP.

            Args:
                request (~.file_service.ListFilesRequest):
                    The request object. Request for ``ListFiles``.
                retry (google.api_core.retry.Retry): Designation of what errors, if any,
                    should be retried.
                timeout (float): The timeout for this request.
                metadata (Sequence[Tuple[str, str]]): Strings which should be
                    sent along with the request as metadata.

            Returns:
                ~.file_service.ListFilesResponse:
                    Response for ``ListFiles``.
            """

            http_options: List[Dict[str, str]] = [
                {
                    "method": "get",
                    "uri": "/v1beta/files",
                },
            ]
            request, metadata = self._interceptor.pre_list_files(request, metadata)
            pb_request = file_service.ListFilesRequest.pb(request)
            transcoded_request = path_template.transcode(http_options, pb_request)

            uri = transcoded_request["uri"]
            method = transcoded_request["method"]

            # Jsonify the query params
            query_params = json.loads(
                json_format.MessageToJson(
                    transcoded_request["query_params"],
                    use_integers_for_enums=True,
                )
            )

            query_params["$alt"] = "json;enum-encoding=int"

            # Send the request
            headers = dict(metadata)
            headers["Content-Type"] = "application/json"
            response = getattr(self._session, method)(
                "{host}{uri}".format(host=self._host, uri=uri),
                timeout=timeout,
                headers=headers,
                params=rest_helpers.flatten_query_params(query_params, strict=True),
            )

            # In case of error, raise the appropriate core_exceptions.GoogleAPICallError exception
            # subclass.
            if response.status_code >= 400:
                raise core_exceptions.from_http_response(response)

            # Return the response
            resp = file_service.ListFilesResponse()
            pb_resp = file_service.ListFilesResponse.pb(resp)

            json_format.Parse(response.content, pb_resp, ignore_unknown_fields=True)
            resp = self._interceptor.post_list_files(resp)
            return resp

    @property
    def create_file(
        self,
    ) -> Callable[[file_service.CreateFileRequest], file_service.CreateFileResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._CreateFile(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def delete_file(
        self,
    ) -> Callable[[file_service.DeleteFileRequest], empty_pb2.Empty]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._DeleteFile(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def get_file(self) -> Callable[[file_service.GetFileRequest], file.File]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._GetFile(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def list_files(
        self,
    ) -> Callable[[file_service.ListFilesRequest], file_service.ListFilesResponse]:
        # The return type is fine, but mypy isn't sophisticated enough to determine what's going on here.
        # In C++ this would require a dynamic_cast
        return self._ListFiles(self._session, self._host, self._interceptor)  # type: ignore

    @property
    def kind(self) -> str:
        return "rest"

    def close(self):
        self._session.close()


__all__ = ("FileServiceRestTransport",)

# === NexusCore/openenv\Lib\site-packages\nltk\tag\brill_trainer.py ===
# Natural Language Toolkit: Transformation-based learning
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Marcus Uneson <marcus.uneson@gmail.com>
#   based on previous (nltk2) version by
#   Christopher Maloof, Edward Loper, Steven Bird
# URL: <https://www.nltk.org/>
# For license information, see  LICENSE.TXT

import bisect
import textwrap
from collections import defaultdict

from nltk.tag import BrillTagger, untag

######################################################################
#  Brill Tagger Trainer
######################################################################


class BrillTaggerTrainer:
    """
    A trainer for tbl taggers.
    """

    def __init__(
        self, initial_tagger, templates, trace=0, deterministic=None, ruleformat="str"
    ):
        """
        Construct a Brill tagger from a baseline tagger and a
        set of templates

        :param initial_tagger: the baseline tagger
        :type initial_tagger: Tagger
        :param templates: templates to be used in training
        :type templates: list of Templates
        :param trace: verbosity level
        :type trace: int
        :param deterministic: if True, adjudicate ties deterministically
        :type deterministic: bool
        :param ruleformat: format of reported Rules
        :type ruleformat: str
        :return: An untrained BrillTagger
        :rtype: BrillTagger
        """

        if deterministic is None:
            deterministic = trace > 0
        self._initial_tagger = initial_tagger
        self._templates = templates
        self._trace = trace
        self._deterministic = deterministic
        self._ruleformat = ruleformat

        self._tag_positions = None
        """Mapping from tags to lists of positions that use that tag."""

        self._rules_by_position = None
        """Mapping from positions to the set of rules that are known
           to occur at that position.  Position is (sentnum, wordnum).
           Initially, this will only contain positions where each rule
           applies in a helpful way; but when we examine a rule, we'll
           extend this list to also include positions where each rule
           applies in a harmful or neutral way."""

        self._positions_by_rule = None
        """Mapping from rule to position to effect, specifying the
           effect that each rule has on the overall score, at each
           position.  Position is (sentnum, wordnum); and effect is
           -1, 0, or 1.  As with _rules_by_position, this mapping starts
           out only containing rules with positive effects; but when
           we examine a rule, we'll extend this mapping to include
           the positions where the rule is harmful or neutral."""

        self._rules_by_score = None
        """Mapping from scores to the set of rules whose effect on the
           overall score is upper bounded by that score.  Invariant:
           rulesByScore[s] will contain r iff the sum of
           _positions_by_rule[r] is s."""

        self._rule_scores = None
        """Mapping from rules to upper bounds on their effects on the
           overall score.  This is the inverse mapping to _rules_by_score.
           Invariant: ruleScores[r] = sum(_positions_by_rule[r])"""

        self._first_unknown_position = None
        """Mapping from rules to the first position where we're unsure
           if the rule applies.  This records the next position we
           need to check to see if the rule messed anything up."""

    # Training

    def train(self, train_sents, max_rules=200, min_score=2, min_acc=None):
        r"""
        Trains the Brill tagger on the corpus *train_sents*,
        producing at most *max_rules* transformations, each of which
        reduces the net number of errors in the corpus by at least
        *min_score*, and each of which has accuracy not lower than
        *min_acc*.

        >>> # Relevant imports
        >>> from nltk.tbl.template import Template
        >>> from nltk.tag.brill import Pos, Word
        >>> from nltk.tag import untag, RegexpTagger, BrillTaggerTrainer

        >>> # Load some data
        >>> from nltk.corpus import treebank
        >>> training_data = treebank.tagged_sents()[:100]
        >>> baseline_data = treebank.tagged_sents()[100:200]
        >>> gold_data = treebank.tagged_sents()[200:300]
        >>> testing_data = [untag(s) for s in gold_data]

        >>> backoff = RegexpTagger([
        ... (r'^-?[0-9]+(\.[0-9]+)?$', 'CD'),  # cardinal numbers
        ... (r'(The|the|A|a|An|an)$', 'AT'),   # articles
        ... (r'.*able$', 'JJ'),                # adjectives
        ... (r'.*ness$', 'NN'),                # nouns formed from adjectives
        ... (r'.*ly$', 'RB'),                  # adverbs
        ... (r'.*s$', 'NNS'),                  # plural nouns
        ... (r'.*ing$', 'VBG'),                # gerunds
        ... (r'.*ed$', 'VBD'),                 # past tense verbs
        ... (r'.*', 'NN')                      # nouns (default)
        ... ])

        >>> baseline = backoff #see NOTE1
        >>> baseline.accuracy(gold_data) #doctest: +ELLIPSIS
        0.243...

        >>> # Set up templates
        >>> Template._cleartemplates() #clear any templates created in earlier tests
        >>> templates = [Template(Pos([-1])), Template(Pos([-1]), Word([0]))]

        >>> # Construct a BrillTaggerTrainer
        >>> tt = BrillTaggerTrainer(baseline, templates, trace=3)

        >>> tagger1 = tt.train(training_data, max_rules=10)
        TBL train (fast) (seqs: 100; tokens: 2417; tpls: 2; min score: 2; min acc: None)
        Finding initial useful rules...
            Found 847 useful rules.
        <BLANKLINE>
                   B      |
           S   F   r   O  |        Score = Fixed - Broken
           c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
           o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
           r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
           e   d   n   r  |  e
        ------------------+-------------------------------------------------------
         132 132   0   0  | AT->DT if Pos:NN@[-1]
          85  85   0   0  | NN->, if Pos:NN@[-1] & Word:,@[0]
          69  69   0   0  | NN->. if Pos:NN@[-1] & Word:.@[0]
          51  51   0   0  | NN->IN if Pos:NN@[-1] & Word:of@[0]
          47  63  16 162  | NN->IN if Pos:NNS@[-1]
          33  33   0   0  | NN->TO if Pos:NN@[-1] & Word:to@[0]
          26  26   0   0  | IN->. if Pos:NNS@[-1] & Word:.@[0]
          24  24   0   0  | IN->, if Pos:NNS@[-1] & Word:,@[0]
          22  27   5  24  | NN->-NONE- if Pos:VBD@[-1]
          17  17   0   0  | NN->CC if Pos:NN@[-1] & Word:and@[0]

        >>> tagger1.rules()[1:3]
        (Rule('001', 'NN', ',', [(Pos([-1]),'NN'), (Word([0]),',')]), Rule('001', 'NN', '.', [(Pos([-1]),'NN'), (Word([0]),'.')]))

        >>> train_stats = tagger1.train_stats()
        >>> [train_stats[stat] for stat in ['initialerrors', 'finalerrors', 'rulescores']]
        [1776, 1270, [132, 85, 69, 51, 47, 33, 26, 24, 22, 17]]

        >>> tagger1.print_template_statistics(printunused=False)
        TEMPLATE STATISTICS (TRAIN)  2 templates, 10 rules)
        TRAIN (   2417 tokens) initial  1776 0.2652 final:  1270 0.4746
        #ID | Score (train) |  #Rules     | Template
        --------------------------------------------
        001 |   305   0.603 |   7   0.700 | Template(Pos([-1]),Word([0]))
        000 |   201   0.397 |   3   0.300 | Template(Pos([-1]))
        <BLANKLINE>
        <BLANKLINE>

        >>> round(tagger1.accuracy(gold_data),5)
        0.43834

        >>> tagged, test_stats = tagger1.batch_tag_incremental(testing_data, gold_data)

        >>> tagged[33][12:] == [('foreign', 'IN'), ('debt', 'NN'), ('of', 'IN'), ('$', 'NN'), ('64', 'CD'),
        ... ('billion', 'NN'), ('*U*', 'NN'), ('--', 'NN'), ('the', 'DT'), ('third-highest', 'NN'), ('in', 'NN'),
        ... ('the', 'DT'), ('developing', 'VBG'), ('world', 'NN'), ('.', '.')]
        True

        >>> [test_stats[stat] for stat in ['initialerrors', 'finalerrors', 'rulescores']]
        [1859, 1380, [100, 85, 67, 58, 27, 36, 27, 16, 31, 32]]

        >>> # A high-accuracy tagger
        >>> tagger2 = tt.train(training_data, max_rules=10, min_acc=0.99)
        TBL train (fast) (seqs: 100; tokens: 2417; tpls: 2; min score: 2; min acc: 0.99)
        Finding initial useful rules...
            Found 847 useful rules.
        <BLANKLINE>
                   B      |
           S   F   r   O  |        Score = Fixed - Broken
           c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
           o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
           r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
           e   d   n   r  |  e
        ------------------+-------------------------------------------------------
         132 132   0   0  | AT->DT if Pos:NN@[-1]
          85  85   0   0  | NN->, if Pos:NN@[-1] & Word:,@[0]
          69  69   0   0  | NN->. if Pos:NN@[-1] & Word:.@[0]
          51  51   0   0  | NN->IN if Pos:NN@[-1] & Word:of@[0]
          36  36   0   0  | NN->TO if Pos:NN@[-1] & Word:to@[0]
          26  26   0   0  | NN->. if Pos:NNS@[-1] & Word:.@[0]
          24  24   0   0  | NN->, if Pos:NNS@[-1] & Word:,@[0]
          19  19   0   6  | NN->VB if Pos:TO@[-1]
          18  18   0   0  | CD->-NONE- if Pos:NN@[-1] & Word:0@[0]
          18  18   0   0  | NN->CC if Pos:NN@[-1] & Word:and@[0]

        >>> round(tagger2.accuracy(gold_data), 8)
        0.43996744

        >>> tagger2.rules()[2:4]
        (Rule('001', 'NN', '.', [(Pos([-1]),'NN'), (Word([0]),'.')]), Rule('001', 'NN', 'IN', [(Pos([-1]),'NN'), (Word([0]),'of')]))

        # NOTE1: (!!FIXME) A far better baseline uses nltk.tag.UnigramTagger,
        # with a RegexpTagger only as backoff. For instance,
        # >>> baseline = UnigramTagger(baseline_data, backoff=backoff)
        # However, as of Nov 2013, nltk.tag.UnigramTagger does not yield consistent results
        # between python versions. The simplistic backoff above is a workaround to make doctests
        # get consistent input.

        :param train_sents: training data
        :type train_sents: list(list(tuple))
        :param max_rules: output at most max_rules rules
        :type max_rules: int
        :param min_score: stop training when no rules better than min_score can be found
        :type min_score: int
        :param min_acc: discard any rule with lower accuracy than min_acc
        :type min_acc: float or None
        :return: the learned tagger
        :rtype: BrillTagger
        """
        # FIXME: several tests are a bit too dependent on tracing format
        # FIXME: tests in trainer.fast and trainer.brillorig are exact duplicates

        # Basic idea: Keep track of the rules that apply at each position.
        # And keep track of the positions to which each rule applies.

        # Create a new copy of the training corpus, and run the
        # initial tagger on it.  We will progressively update this
        # test corpus to look more like the training corpus.
        test_sents = [
            list(self._initial_tagger.tag(untag(sent))) for sent in train_sents
        ]

        # Collect some statistics on the training process
        trainstats = {}
        trainstats["min_acc"] = min_acc
        trainstats["min_score"] = min_score
        trainstats["tokencount"] = sum(len(t) for t in test_sents)
        trainstats["sequencecount"] = len(test_sents)
        trainstats["templatecount"] = len(self._templates)
        trainstats["rulescores"] = []
        trainstats["initialerrors"] = sum(
            tag[1] != truth[1]
            for paired in zip(test_sents, train_sents)
            for (tag, truth) in zip(*paired)
        )
        trainstats["initialacc"] = (
            1 - trainstats["initialerrors"] / trainstats["tokencount"]
        )
        if self._trace > 0:
            print(
                "TBL train (fast) (seqs: {sequencecount}; tokens: {tokencount}; "
                "tpls: {templatecount}; min score: {min_score}; min acc: {min_acc})".format(
                    **trainstats
                )
            )

        # Initialize our mappings.  This will find any errors made
        # by the initial tagger, and use those to generate repair
        # rules, which are added to the rule mappings.
        if self._trace:
            print("Finding initial useful rules...")
        self._init_mappings(test_sents, train_sents)
        if self._trace:
            print(f"    Found {len(self._rule_scores)} useful rules.")

        # Let the user know what we're up to.
        if self._trace > 2:
            self._trace_header()
        elif self._trace == 1:
            print("Selecting rules...")

        # Repeatedly select the best rule, and add it to `rules`.
        rules = []
        try:
            while len(rules) < max_rules:
                # Find the best rule, and add it to our rule list.
                rule = self._best_rule(train_sents, test_sents, min_score, min_acc)
                if rule:
                    rules.append(rule)
                    score = self._rule_scores[rule]
                    trainstats["rulescores"].append(score)
                else:
                    break  # No more good rules left!

                # Report the rule that we found.
                if self._trace > 1:
                    self._trace_rule(rule)

                # Apply the new rule at the relevant sites
                self._apply_rule(rule, test_sents)

                # Update _tag_positions[rule.original_tag] and
                # _tag_positions[rule.replacement_tag] for the affected
                # positions (i.e., self._positions_by_rule[rule]).
                self._update_tag_positions(rule)

                # Update rules that were affected by the change.
                self._update_rules(rule, train_sents, test_sents)

        # The user can cancel training manually:
        except KeyboardInterrupt:
            print(f"Training stopped manually -- {len(rules)} rules found")

        # Discard our tag position mapping & rule mappings.
        self._clean()
        trainstats["finalerrors"] = trainstats["initialerrors"] - sum(
            trainstats["rulescores"]
        )
        trainstats["finalacc"] = (
            1 - trainstats["finalerrors"] / trainstats["tokencount"]
        )
        # Create and return a tagger from the rules we found.
        return BrillTagger(self._initial_tagger, rules, trainstats)

    def _init_mappings(self, test_sents, train_sents):
        """
        Initialize the tag position mapping & the rule related
        mappings.  For each error in test_sents, find new rules that
        would correct them, and add them to the rule mappings.
        """
        self._tag_positions = defaultdict(list)
        self._rules_by_position = defaultdict(set)
        self._positions_by_rule = defaultdict(dict)
        self._rules_by_score = defaultdict(set)
        self._rule_scores = defaultdict(int)
        self._first_unknown_position = defaultdict(int)
        # Scan through the corpus, initializing the tag_positions
        # mapping and all the rule-related mappings.
        for sentnum, sent in enumerate(test_sents):
            for wordnum, (word, tag) in enumerate(sent):
                # Initialize tag_positions
                self._tag_positions[tag].append((sentnum, wordnum))

                # If it's an error token, update the rule-related mappings.
                correct_tag = train_sents[sentnum][wordnum][1]
                if tag != correct_tag:
                    for rule in self._find_rules(sent, wordnum, correct_tag):
                        self._update_rule_applies(rule, sentnum, wordnum, train_sents)

    def _clean(self):
        self._tag_positions = None
        self._rules_by_position = None
        self._positions_by_rule = None
        self._rules_by_score = None
        self._rule_scores = None
        self._first_unknown_position = None

    def _find_rules(self, sent, wordnum, new_tag):
        """
        Use the templates to find rules that apply at index *wordnum*
        in the sentence *sent* and generate the tag *new_tag*.
        """
        for template in self._templates:
            yield from template.applicable_rules(sent, wordnum, new_tag)

    def _update_rule_applies(self, rule, sentnum, wordnum, train_sents):
        """
        Update the rule data tables to reflect the fact that
        *rule* applies at the position *(sentnum, wordnum)*.
        """
        pos = sentnum, wordnum

        # If the rule is already known to apply here, ignore.
        # (This only happens if the position's tag hasn't changed.)
        if pos in self._positions_by_rule[rule]:
            return

        # Update self._positions_by_rule.
        correct_tag = train_sents[sentnum][wordnum][1]
        if rule.replacement_tag == correct_tag:
            self._positions_by_rule[rule][pos] = 1
        elif rule.original_tag == correct_tag:
            self._positions_by_rule[rule][pos] = -1
        else:  # was wrong, remains wrong
            self._positions_by_rule[rule][pos] = 0

        # Update _rules_by_position
        self._rules_by_position[pos].add(rule)

        # Update _rule_scores.
        old_score = self._rule_scores[rule]
        self._rule_scores[rule] += self._positions_by_rule[rule][pos]

        # Update _rules_by_score.
        self._rules_by_score[old_score].discard(rule)
        self._rules_by_score[self._rule_scores[rule]].add(rule)

    def _update_rule_not_applies(self, rule, sentnum, wordnum):
        """
        Update the rule data tables to reflect the fact that *rule*
        does not apply at the position *(sentnum, wordnum)*.
        """
        pos = sentnum, wordnum

        # Update _rule_scores.
        old_score = self._rule_scores[rule]
        self._rule_scores[rule] -= self._positions_by_rule[rule][pos]

        # Update _rules_by_score.
        self._rules_by_score[old_score].discard(rule)
        self._rules_by_score[self._rule_scores[rule]].add(rule)

        # Update _positions_by_rule
        del self._positions_by_rule[rule][pos]
        self._rules_by_position[pos].remove(rule)

        # Optional addition: if the rule now applies nowhere, delete
        # all its dictionary entries.

    def _best_rule(self, train_sents, test_sents, min_score, min_acc):
        """
        Find the next best rule.  This is done by repeatedly taking a
        rule with the highest score and stepping through the corpus to
        see where it applies.  When it makes an error (decreasing its
        score) it's bumped down, and we try a new rule with the
        highest score.  When we find a rule which has the highest
        score *and* which has been tested against the entire corpus, we
        can conclude that it's the next best rule.
        """
        for max_score in sorted(self._rules_by_score.keys(), reverse=True):
            if len(self._rules_by_score) == 0:
                return None
            if max_score < min_score or max_score <= 0:
                return None
            best_rules = list(self._rules_by_score[max_score])
            if self._deterministic:
                best_rules.sort(key=repr)
            for rule in best_rules:
                positions = self._tag_positions[rule.original_tag]

                unk = self._first_unknown_position.get(rule, (0, -1))
                start = bisect.bisect_left(positions, unk)

                for i in range(start, len(positions)):
                    sentnum, wordnum = positions[i]
                    if rule.applies(test_sents[sentnum], wordnum):
                        self._update_rule_applies(rule, sentnum, wordnum, train_sents)
                        if self._rule_scores[rule] < max_score:
                            self._first_unknown_position[rule] = (sentnum, wordnum + 1)
                            break  # The update demoted the rule.

                if self._rule_scores[rule] == max_score:
                    self._first_unknown_position[rule] = (len(train_sents) + 1, 0)
                    # optimization: if no min_acc threshold given, don't bother computing accuracy
                    if min_acc is None:
                        return rule
                    else:
                        changes = self._positions_by_rule[rule].values()
                        num_fixed = len([c for c in changes if c == 1])
                        num_broken = len([c for c in changes if c == -1])
                        # acc here is fixed/(fixed+broken); could also be
                        # fixed/(fixed+broken+other) == num_fixed/len(changes)
                        acc = num_fixed / (num_fixed + num_broken)
                        if acc >= min_acc:
                            return rule
                        # else: rule too inaccurate, discard and try next

            # We demoted (or skipped due to < min_acc, if that was given)
            # all the rules with score==max_score.

            assert min_acc is not None or not self._rules_by_score[max_score]
            if not self._rules_by_score[max_score]:
                del self._rules_by_score[max_score]

    def _apply_rule(self, rule, test_sents):
        """
        Update *test_sents* by applying *rule* everywhere where its
        conditions are met.
        """
        update_positions = set(self._positions_by_rule[rule])
        new_tag = rule.replacement_tag

        if self._trace > 3:
            self._trace_apply(len(update_positions))

        # Update test_sents.
        for sentnum, wordnum in update_positions:
            text = test_sents[sentnum][wordnum][0]
            test_sents[sentnum][wordnum] = (text, new_tag)

    def _update_tag_positions(self, rule):
        """
        Update _tag_positions to reflect the changes to tags that are
        made by *rule*.
        """
        # Update the tag index.
        for pos in self._positions_by_rule[rule]:
            # Delete the old tag.
            old_tag_positions = self._tag_positions[rule.original_tag]
            old_index = bisect.bisect_left(old_tag_positions, pos)
            del old_tag_positions[old_index]
            # Insert the new tag.
            new_tag_positions = self._tag_positions[rule.replacement_tag]
            bisect.insort_left(new_tag_positions, pos)

    def _update_rules(self, rule, train_sents, test_sents):
        """
        Check if we should add or remove any rules from consideration,
        given the changes made by *rule*.
        """
        # Collect a list of all positions that might be affected.
        neighbors = set()
        for sentnum, wordnum in self._positions_by_rule[rule]:
            for template in self._templates:
                n = template.get_neighborhood(test_sents[sentnum], wordnum)
                neighbors.update([(sentnum, i) for i in n])

        # Update the rules at each position.
        num_obsolete = num_new = num_unseen = 0
        for sentnum, wordnum in neighbors:
            test_sent = test_sents[sentnum]
            correct_tag = train_sents[sentnum][wordnum][1]

            # Check if the change causes any rule at this position to
            # stop matching; if so, then update our rule mappings
            # accordingly.
            old_rules = set(self._rules_by_position[sentnum, wordnum])
            for old_rule in old_rules:
                if not old_rule.applies(test_sent, wordnum):
                    num_obsolete += 1
                    self._update_rule_not_applies(old_rule, sentnum, wordnum)

            # Check if the change causes our templates to propose any
            # new rules for this position.
            for template in self._templates:
                for new_rule in template.applicable_rules(
                    test_sent, wordnum, correct_tag
                ):
                    if new_rule not in old_rules:
                        num_new += 1
                        if new_rule not in self._rule_scores:
                            num_unseen += 1
                        old_rules.add(new_rule)
                        self._update_rule_applies(
                            new_rule, sentnum, wordnum, train_sents
                        )

            # We may have caused other rules to match here, that are
            # not proposed by our templates -- in particular, rules
            # that are harmful or neutral.  We therefore need to
            # update any rule whose first_unknown_position is past
            # this rule.
            for new_rule, pos in self._first_unknown_position.items():
                if pos > (sentnum, wordnum):
                    if new_rule not in old_rules:
                        num_new += 1
                        if new_rule.applies(test_sent, wordnum):
                            self._update_rule_applies(
                                new_rule, sentnum, wordnum, train_sents
                            )

        if self._trace > 3:
            self._trace_update_rules(num_obsolete, num_new, num_unseen)

    # Tracing

    def _trace_header(self):
        print(
            """
           B      |
   S   F   r   O  |        Score = Fixed - Broken
   c   i   o   t  |  R     Fixed = num tags changed incorrect -> correct
   o   x   k   h  |  u     Broken = num tags changed correct -> incorrect
   r   e   e   e  |  l     Other = num tags changed incorrect -> incorrect
   e   d   n   r  |  e
------------------+-------------------------------------------------------
        """.rstrip()
        )

    def _trace_rule(self, rule):
        assert self._rule_scores[rule] == sum(self._positions_by_rule[rule].values())

        changes = self._positions_by_rule[rule].values()
        num_fixed = len([c for c in changes if c == 1])
        num_broken = len([c for c in changes if c == -1])
        num_other = len([c for c in changes if c == 0])
        score = self._rule_scores[rule]

        rulestr = rule.format(self._ruleformat)
        if self._trace > 2:
            print(
                "{:4d}{:4d}{:4d}{:4d}  |".format(
                    score, num_fixed, num_broken, num_other
                ),
                end=" ",
            )
            print(
                textwrap.fill(
                    rulestr,
                    initial_indent=" " * 20,
                    width=79,
                    subsequent_indent=" " * 18 + "|   ",
                ).strip()
            )
        else:
            print(rulestr)

    def _trace_apply(self, num_updates):
        prefix = " " * 18 + "|"
        print(prefix)
        print(prefix, f"Applying rule to {num_updates} positions.")

    def _trace_update_rules(self, num_obsolete, num_new, num_unseen):
        prefix = " " * 18 + "|"
        print(prefix, "Updated rule tables:")
        print(prefix, (f"  - {num_obsolete} rule applications removed"))
        print(
            prefix,
            (f"  - {num_new} rule applications added ({num_unseen} novel)"),
        )
        print(prefix)

# === NexusCore/openenv\Lib\site-packages\click\utils.py ===
from __future__ import annotations

import collections.abc as cabc
import os
import re
import sys
import typing as t
from functools import update_wrapper
from types import ModuleType
from types import TracebackType

from ._compat import _default_text_stderr
from ._compat import _default_text_stdout
from ._compat import _find_binary_writer
from ._compat import auto_wrap_for_ansi
from ._compat import binary_streams
from ._compat import open_stream
from ._compat import should_strip_ansi
from ._compat import strip_ansi
from ._compat import text_streams
from ._compat import WIN
from .globals import resolve_color_default

if t.TYPE_CHECKING:
    import typing_extensions as te

    P = te.ParamSpec("P")

R = t.TypeVar("R")


def _posixify(name: str) -> str:
    return "-".join(name.split()).lower()


def safecall(func: t.Callable[P, R]) -> t.Callable[P, R | None]:
    """Wraps a function so that it swallows exceptions."""

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return func(*args, **kwargs)
        except Exception:
            pass
        return None

    return update_wrapper(wrapper, func)


def make_str(value: t.Any) -> str:
    """Converts a value into a valid string."""
    if isinstance(value, bytes):
        try:
            return value.decode(sys.getfilesystemencoding())
        except UnicodeError:
            return value.decode("utf-8", "replace")
    return str(value)


def make_default_short_help(help: str, max_length: int = 45) -> str:
    """Returns a condensed version of help string."""
    # Consider only the first paragraph.
    paragraph_end = help.find("\n\n")

    if paragraph_end != -1:
        help = help[:paragraph_end]

    # Collapse newlines, tabs, and spaces.
    words = help.split()

    if not words:
        return ""

    # The first paragraph started with a "no rewrap" marker, ignore it.
    if words[0] == "\b":
        words = words[1:]

    total_length = 0
    last_index = len(words) - 1

    for i, word in enumerate(words):
        total_length += len(word) + (i > 0)

        if total_length > max_length:  # too long, truncate
            break

        if word[-1] == ".":  # sentence end, truncate without "..."
            return " ".join(words[: i + 1])

        if total_length == max_length and i != last_index:
            break  # not at sentence end, truncate with "..."
    else:
        return " ".join(words)  # no truncation needed

    # Account for the length of the suffix.
    total_length += len("...")

    # remove words until the length is short enough
    while i > 0:
        total_length -= len(words[i]) + (i > 0)

        if total_length <= max_length:
            break

        i -= 1

    return " ".join(words[:i]) + "..."


class LazyFile:
    """A lazy file works like a regular file but it does not fully open
    the file but it does perform some basic checks early to see if the
    filename parameter does make sense.  This is useful for safely opening
    files for writing.
    """

    def __init__(
        self,
        filename: str | os.PathLike[str],
        mode: str = "r",
        encoding: str | None = None,
        errors: str | None = "strict",
        atomic: bool = False,
    ):
        self.name: str = os.fspath(filename)
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.atomic = atomic
        self._f: t.IO[t.Any] | None
        self.should_close: bool

        if self.name == "-":
            self._f, self.should_close = open_stream(filename, mode, encoding, errors)
        else:
            if "r" in mode:
                # Open and close the file in case we're opening it for
                # reading so that we can catch at least some errors in
                # some cases early.
                open(filename, mode).close()
            self._f = None
            self.should_close = True

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self.open(), name)

    def __repr__(self) -> str:
        if self._f is not None:
            return repr(self._f)
        return f"<unopened file '{format_filename(self.name)}' {self.mode}>"

    def open(self) -> t.IO[t.Any]:
        """Opens the file if it's not yet open.  This call might fail with
        a :exc:`FileError`.  Not handling this error will produce an error
        that Click shows.
        """
        if self._f is not None:
            return self._f
        try:
            rv, self.should_close = open_stream(
                self.name, self.mode, self.encoding, self.errors, atomic=self.atomic
            )
        except OSError as e:
            from .exceptions import FileError

            raise FileError(self.name, hint=e.strerror) from e
        self._f = rv
        return rv

    def close(self) -> None:
        """Closes the underlying file, no matter what."""
        if self._f is not None:
            self._f.close()

    def close_intelligently(self) -> None:
        """This function only closes the file if it was opened by the lazy
        file wrapper.  For instance this will never close stdin.
        """
        if self.should_close:
            self.close()

    def __enter__(self) -> LazyFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close_intelligently()

    def __iter__(self) -> cabc.Iterator[t.AnyStr]:
        self.open()
        return iter(self._f)  # type: ignore


class KeepOpenFile:
    def __init__(self, file: t.IO[t.Any]) -> None:
        self._file: t.IO[t.Any] = file

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._file, name)

    def __enter__(self) -> KeepOpenFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass

    def __repr__(self) -> str:
        return repr(self._file)

    def __iter__(self) -> cabc.Iterator[t.AnyStr]:
        return iter(self._file)


def echo(
    message: t.Any | None = None,
    file: t.IO[t.Any] | None = None,
    nl: bool = True,
    err: bool = False,
    color: bool | None = None,
) -> None:
    """Print a message and newline to stdout or a file. This should be
    used instead of :func:`print` because it provides better support
    for different data, files, and environments.

    Compared to :func:`print`, this does the following:

    -   Ensures that the output encoding is not misconfigured on Linux.
    -   Supports Unicode in the Windows console.
    -   Supports writing to binary outputs, and supports writing bytes
        to text outputs.
    -   Supports colors and styles on Windows.
    -   Removes ANSI color and style codes if the output does not look
        like an interactive terminal.
    -   Always flushes the output.

    :param message: The string or bytes to output. Other objects are
        converted to strings.
    :param file: The file to write to. Defaults to ``stdout``.
    :param err: Write to ``stderr`` instead of ``stdout``.
    :param nl: Print a newline after the message. Enabled by default.
    :param color: Force showing or hiding colors and other styles. By
        default Click will remove color if the output does not look like
        an interactive terminal.

    .. versionchanged:: 6.0
        Support Unicode output on the Windows console. Click does not
        modify ``sys.stdout``, so ``sys.stdout.write()`` and ``print()``
        will still not support Unicode.

    .. versionchanged:: 4.0
        Added the ``color`` parameter.

    .. versionadded:: 3.0
        Added the ``err`` parameter.

    .. versionchanged:: 2.0
        Support colors on Windows if colorama is installed.
    """
    if file is None:
        if err:
            file = _default_text_stderr()
        else:
            file = _default_text_stdout()

        # There are no standard streams attached to write to. For example,
        # pythonw on Windows.
        if file is None:
            return

    # Convert non bytes/text into the native string type.
    if message is not None and not isinstance(message, (str, bytes, bytearray)):
        out: str | bytes | None = str(message)
    else:
        out = message

    if nl:
        out = out or ""
        if isinstance(out, str):
            out += "\n"
        else:
            out += b"\n"

    if not out:
        file.flush()
        return

    # If there is a message and the value looks like bytes, we manually
    # need to find the binary stream and write the message in there.
    # This is done separately so that most stream types will work as you
    # would expect. Eg: you can write to StringIO for other cases.
    if isinstance(out, (bytes, bytearray)):
        binary_file = _find_binary_writer(file)

        if binary_file is not None:
            file.flush()
            binary_file.write(out)
            binary_file.flush()
            return

    # ANSI style code support. For no message or bytes, nothing happens.
    # When outputting to a file instead of a terminal, strip codes.
    else:
        color = resolve_color_default(color)

        if should_strip_ansi(file, color):
            out = strip_ansi(out)
        elif WIN:
            if auto_wrap_for_ansi is not None:
                file = auto_wrap_for_ansi(file, color)  # type: ignore
            elif not color:
                out = strip_ansi(out)

    file.write(out)  # type: ignore
    file.flush()


def get_binary_stream(name: t.Literal["stdin", "stdout", "stderr"]) -> t.BinaryIO:
    """Returns a system stream for byte processing.

    :param name: the name of the stream to open.  Valid names are ``'stdin'``,
                 ``'stdout'`` and ``'stderr'``
    """
    opener = binary_streams.get(name)
    if opener is None:
        raise TypeError(f"Unknown standard stream '{name}'")
    return opener()


def get_text_stream(
    name: t.Literal["stdin", "stdout", "stderr"],
    encoding: str | None = None,
    errors: str | None = "strict",
) -> t.TextIO:
    """Returns a system stream for text processing.  This usually returns
    a wrapped stream around a binary stream returned from
    :func:`get_binary_stream` but it also can take shortcuts for already
    correctly configured streams.

    :param name: the name of the stream to open.  Valid names are ``'stdin'``,
                 ``'stdout'`` and ``'stderr'``
    :param encoding: overrides the detected default encoding.
    :param errors: overrides the default error mode.
    """
    opener = text_streams.get(name)
    if opener is None:
        raise TypeError(f"Unknown standard stream '{name}'")
    return opener(encoding, errors)


def open_file(
    filename: str | os.PathLike[str],
    mode: str = "r",
    encoding: str | None = None,
    errors: str | None = "strict",
    lazy: bool = False,
    atomic: bool = False,
) -> t.IO[t.Any]:
    """Open a file, with extra behavior to handle ``'-'`` to indicate
    a standard stream, lazy open on write, and atomic write. Similar to
    the behavior of the :class:`~click.File` param type.

    If ``'-'`` is given to open ``stdout`` or ``stdin``, the stream is
    wrapped so that using it in a context manager will not close it.
    This makes it possible to use the function without accidentally
    closing a standard stream:

    .. code-block:: python

        with open_file(filename) as f:
            ...

    :param filename: The name or Path of the file to open, or ``'-'`` for
        ``stdin``/``stdout``.
    :param mode: The mode in which to open the file.
    :param encoding: The encoding to decode or encode a file opened in
        text mode.
    :param errors: The error handling mode.
    :param lazy: Wait to open the file until it is accessed. For read
        mode, the file is temporarily opened to raise access errors
        early, then closed until it is read again.
    :param atomic: Write to a temporary file and replace the given file
        on close.

    .. versionadded:: 3.0
    """
    if lazy:
        return t.cast(
            "t.IO[t.Any]", LazyFile(filename, mode, encoding, errors, atomic=atomic)
        )

    f, should_close = open_stream(filename, mode, encoding, errors, atomic=atomic)

    if not should_close:
        f = t.cast("t.IO[t.Any]", KeepOpenFile(f))

    return f


def format_filename(
    filename: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    shorten: bool = False,
) -> str:
    """Format a filename as a string for display. Ensures the filename can be
    displayed by replacing any invalid bytes or surrogate escapes in the name
    with the replacement character ``�``.

    Invalid bytes or surrogate escapes will raise an error when written to a
    stream with ``errors="strict"``. This will typically happen with ``stdout``
    when the locale is something like ``en_GB.UTF-8``.

    Many scenarios *are* safe to write surrogates though, due to PEP 538 and
    PEP 540, including:

    -   Writing to ``stderr``, which uses ``errors="backslashreplace"``.
    -   The system has ``LANG=C.UTF-8``, ``C``, or ``POSIX``. Python opens
        stdout and stderr with ``errors="surrogateescape"``.
    -   None of ``LANG/LC_*`` are set. Python assumes ``LANG=C.UTF-8``.
    -   Python is started in UTF-8 mode  with  ``PYTHONUTF8=1`` or ``-X utf8``.
        Python opens stdout and stderr with ``errors="surrogateescape"``.

    :param filename: formats a filename for UI display.  This will also convert
                     the filename into unicode without failing.
    :param shorten: this optionally shortens the filename to strip of the
                    path that leads up to it.
    """
    if shorten:
        filename = os.path.basename(filename)
    else:
        filename = os.fspath(filename)

    if isinstance(filename, bytes):
        filename = filename.decode(sys.getfilesystemencoding(), "replace")
    else:
        filename = filename.encode("utf-8", "surrogateescape").decode(
            "utf-8", "replace"
        )

    return filename


def get_app_dir(app_name: str, roaming: bool = True, force_posix: bool = False) -> str:
    r"""Returns the config folder for the application.  The default behavior
    is to return whatever is most appropriate for the operating system.

    To give you an idea, for an app called ``"Foo Bar"``, something like
    the following folders could be returned:

    Mac OS X:
      ``~/Library/Application Support/Foo Bar``
    Mac OS X (POSIX):
      ``~/.foo-bar``
    Unix:
      ``~/.config/foo-bar``
    Unix (POSIX):
      ``~/.foo-bar``
    Windows (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Windows (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``

    .. versionadded:: 2.0

    :param app_name: the application name.  This should be properly capitalized
                     and can contain whitespace.
    :param roaming: controls if the folder should be roaming or not on Windows.
                    Has no effect otherwise.
    :param force_posix: if this is set to `True` then on any POSIX system the
                        folder will be stored in the home folder with a leading
                        dot instead of the XDG config home or darwin's
                        application support folder.
    """
    if WIN:
        key = "APPDATA" if roaming else "LOCALAPPDATA"
        folder = os.environ.get(key)
        if folder is None:
            folder = os.path.expanduser("~")
        return os.path.join(folder, app_name)
    if force_posix:
        return os.path.join(os.path.expanduser(f"~/.{_posixify(app_name)}"))
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"), app_name
        )
    return os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        _posixify(app_name),
    )


class PacifyFlushWrapper:
    """This wrapper is used to catch and suppress BrokenPipeErrors resulting
    from ``.flush()`` being called on broken pipe during the shutdown/final-GC
    of the Python interpreter. Notably ``.flush()`` is always called on
    ``sys.stdout`` and ``sys.stderr``. So as to have minimal impact on any
    other cleanup code, and the case where the underlying file is not a broken
    pipe, all calls and attributes are proxied.
    """

    def __init__(self, wrapped: t.IO[t.Any]) -> None:
        self.wrapped = wrapped

    def flush(self) -> None:
        try:
            self.wrapped.flush()
        except OSError as e:
            import errno

            if e.errno != errno.EPIPE:
                raise

    def __getattr__(self, attr: str) -> t.Any:
        return getattr(self.wrapped, attr)


def _detect_program_name(
    path: str | None = None, _main: ModuleType | None = None
) -> str:
    """Determine the command used to run the program, for use in help
    text. If a file or entry point was executed, the file name is
    returned. If ``python -m`` was used to execute a module or package,
    ``python -m name`` is returned.

    This doesn't try to be too precise, the goal is to give a concise
    name for help text. Files are only shown as their name without the
    path. ``python`` is only shown for modules, and the full path to
    ``sys.executable`` is not shown.

    :param path: The Python file being executed. Python puts this in
        ``sys.argv[0]``, which is used by default.
    :param _main: The ``__main__`` module. This should only be passed
        during internal testing.

    .. versionadded:: 8.0
        Based on command args detection in the Werkzeug reloader.

    :meta private:
    """
    if _main is None:
        _main = sys.modules["__main__"]

    if not path:
        path = sys.argv[0]

    # The value of __package__ indicates how Python was called. It may
    # not exist if a setuptools script is installed as an egg. It may be
    # set incorrectly for entry points created with pip on Windows.
    # It is set to "" inside a Shiv or PEX zipapp.
    if getattr(_main, "__package__", None) in {None, ""} or (
        os.name == "nt"
        and _main.__package__ == ""
        and not os.path.exists(path)
        and os.path.exists(f"{path}.exe")
    ):
        # Executed a file, like "python app.py".
        return os.path.basename(path)

    # Executed a module, like "python -m example".
    # Rewritten by Python from "-m script" to "/path/to/script.py".
    # Need to look at main module to determine how it was executed.
    py_module = t.cast(str, _main.__package__)
    name = os.path.splitext(os.path.basename(path))[0]

    # A submodule like "example.cli".
    if name != "__main__":
        py_module = f"{py_module}.{name}"

    return f"python -m {py_module.lstrip('.')}"


def _expand_args(
    args: cabc.Iterable[str],
    *,
    user: bool = True,
    env: bool = True,
    glob_recursive: bool = True,
) -> list[str]:
    """Simulate Unix shell expansion with Python functions.

    See :func:`glob.glob`, :func:`os.path.expanduser`, and
    :func:`os.path.expandvars`.

    This is intended for use on Windows, where the shell does not do any
    expansion. It may not exactly match what a Unix shell would do.

    :param args: List of command line arguments to expand.
    :param user: Expand user home directory.
    :param env: Expand environment variables.
    :param glob_recursive: ``**`` matches directories recursively.

    .. versionchanged:: 8.1
        Invalid glob patterns are treated as empty expansions rather
        than raising an error.

    .. versionadded:: 8.0

    :meta private:
    """
    from glob import glob

    out = []

    for arg in args:
        if user:
            arg = os.path.expanduser(arg)

        if env:
            arg = os.path.expandvars(arg)

        try:
            matches = glob(arg, recursive=glob_recursive)
        except re.error:
            matches = []

        if not matches:
            out.append(arg)
        else:
            out.extend(matches)

    return out

# === NexusCore/openenv\Lib\site-packages\grpc\aio\_channel.py ===
# Copyright 2019 gRPC authors.
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
"""Invocation-side implementation of gRPC Asyncio Python."""

import asyncio
import sys
from typing import Any, Iterable, List, Optional, Sequence

import grpc
from grpc import _common
from grpc import _compression
from grpc import _grpcio_metadata
from grpc._cython import cygrpc

from . import _base_call
from . import _base_channel
from ._call import StreamStreamCall
from ._call import StreamUnaryCall
from ._call import UnaryStreamCall
from ._call import UnaryUnaryCall
from ._interceptor import ClientInterceptor
from ._interceptor import InterceptedStreamStreamCall
from ._interceptor import InterceptedStreamUnaryCall
from ._interceptor import InterceptedUnaryStreamCall
from ._interceptor import InterceptedUnaryUnaryCall
from ._interceptor import StreamStreamClientInterceptor
from ._interceptor import StreamUnaryClientInterceptor
from ._interceptor import UnaryStreamClientInterceptor
from ._interceptor import UnaryUnaryClientInterceptor
from ._metadata import Metadata
from ._typing import ChannelArgumentType
from ._typing import DeserializingFunction
from ._typing import MetadataType
from ._typing import RequestIterableType
from ._typing import RequestType
from ._typing import ResponseType
from ._typing import SerializingFunction
from ._utils import _timeout_to_deadline

_USER_AGENT = "grpc-python-asyncio/{}".format(_grpcio_metadata.__version__)

if sys.version_info[1] < 7:

    def _all_tasks() -> Iterable[asyncio.Task]:
        return asyncio.Task.all_tasks()  # pylint: disable=no-member

else:

    def _all_tasks() -> Iterable[asyncio.Task]:
        return asyncio.all_tasks()


def _augment_channel_arguments(
    base_options: ChannelArgumentType, compression: Optional[grpc.Compression]
):
    compression_channel_argument = _compression.create_channel_option(
        compression
    )
    user_agent_channel_argument = (
        (
            cygrpc.ChannelArgKey.primary_user_agent_string,
            _USER_AGENT,
        ),
    )
    return (
        tuple(base_options)
        + compression_channel_argument
        + user_agent_channel_argument
    )


class _BaseMultiCallable:
    """Base class of all multi callable objects.

    Handles the initialization logic and stores common attributes.
    """

    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel
    _method: bytes
    _request_serializer: SerializingFunction
    _response_deserializer: DeserializingFunction
    _interceptors: Optional[Sequence[ClientInterceptor]]
    _references: List[Any]
    _loop: asyncio.AbstractEventLoop

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        channel: cygrpc.AioChannel,
        method: bytes,
        request_serializer: SerializingFunction,
        response_deserializer: DeserializingFunction,
        interceptors: Optional[Sequence[ClientInterceptor]],
        references: List[Any],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._loop = loop
        self._channel = channel
        self._method = method
        self._request_serializer = request_serializer
        self._response_deserializer = response_deserializer
        self._interceptors = interceptors
        self._references = references

    @staticmethod
    def _init_metadata(
        metadata: Optional[MetadataType] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> Metadata:
        """Based on the provided values for <metadata> or <compression> initialise the final
        metadata, as it should be used for the current call.
        """
        metadata = metadata or Metadata()
        if not isinstance(metadata, Metadata) and isinstance(metadata, tuple):
            metadata = Metadata.from_tuple(metadata)
        if compression:
            metadata = Metadata(
                *_compression.augment_metadata(metadata, compression)
            )
        return metadata


class UnaryUnaryMultiCallable(
    _BaseMultiCallable, _base_channel.UnaryUnaryMultiCallable
):
    def __call__(
        self,
        request: RequestType,
        *,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.UnaryUnaryCall[RequestType, ResponseType]:
        metadata = self._init_metadata(metadata, compression)
        if not self._interceptors:
            call = UnaryUnaryCall(
                request,
                _timeout_to_deadline(timeout),
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )
        else:
            call = InterceptedUnaryUnaryCall(
                self._interceptors,
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )

        return call


class UnaryStreamMultiCallable(
    _BaseMultiCallable, _base_channel.UnaryStreamMultiCallable
):
    def __call__(
        self,
        request: RequestType,
        *,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.UnaryStreamCall[RequestType, ResponseType]:
        metadata = self._init_metadata(metadata, compression)

        if not self._interceptors:
            call = UnaryStreamCall(
                request,
                _timeout_to_deadline(timeout),
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )
        else:
            call = InterceptedUnaryStreamCall(
                self._interceptors,
                request,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )

        return call


class StreamUnaryMultiCallable(
    _BaseMultiCallable, _base_channel.StreamUnaryMultiCallable
):
    def __call__(
        self,
        request_iterator: Optional[RequestIterableType] = None,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.StreamUnaryCall:
        metadata = self._init_metadata(metadata, compression)

        if not self._interceptors:
            call = StreamUnaryCall(
                request_iterator,
                _timeout_to_deadline(timeout),
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )
        else:
            call = InterceptedStreamUnaryCall(
                self._interceptors,
                request_iterator,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )

        return call


class StreamStreamMultiCallable(
    _BaseMultiCallable, _base_channel.StreamStreamMultiCallable
):
    def __call__(
        self,
        request_iterator: Optional[RequestIterableType] = None,
        timeout: Optional[float] = None,
        metadata: Optional[MetadataType] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None,
    ) -> _base_call.StreamStreamCall:
        metadata = self._init_metadata(metadata, compression)

        if not self._interceptors:
            call = StreamStreamCall(
                request_iterator,
                _timeout_to_deadline(timeout),
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )
        else:
            call = InterceptedStreamStreamCall(
                self._interceptors,
                request_iterator,
                timeout,
                metadata,
                credentials,
                wait_for_ready,
                self._channel,
                self._method,
                self._request_serializer,
                self._response_deserializer,
                self._loop,
            )

        return call


class Channel(_base_channel.Channel):
    _loop: asyncio.AbstractEventLoop
    _channel: cygrpc.AioChannel
    _unary_unary_interceptors: List[UnaryUnaryClientInterceptor]
    _unary_stream_interceptors: List[UnaryStreamClientInterceptor]
    _stream_unary_interceptors: List[StreamUnaryClientInterceptor]
    _stream_stream_interceptors: List[StreamStreamClientInterceptor]

    def __init__(
        self,
        target: str,
        options: ChannelArgumentType,
        credentials: Optional[grpc.ChannelCredentials],
        compression: Optional[grpc.Compression],
        interceptors: Optional[Sequence[ClientInterceptor]],
    ):
        """Constructor.

        Args:
          target: The target to which to connect.
          options: Configuration options for the channel.
          credentials: A cygrpc.ChannelCredentials or None.
          compression: An optional value indicating the compression method to be
            used over the lifetime of the channel.
          interceptors: An optional list of interceptors that would be used for
            intercepting any RPC executed with that channel.
        """
        self._unary_unary_interceptors = []
        self._unary_stream_interceptors = []
        self._stream_unary_interceptors = []
        self._stream_stream_interceptors = []

        if interceptors is not None:
            for interceptor in interceptors:
                if isinstance(interceptor, UnaryUnaryClientInterceptor):
                    self._unary_unary_interceptors.append(interceptor)
                elif isinstance(interceptor, UnaryStreamClientInterceptor):
                    self._unary_stream_interceptors.append(interceptor)
                elif isinstance(interceptor, StreamUnaryClientInterceptor):
                    self._stream_unary_interceptors.append(interceptor)
                elif isinstance(interceptor, StreamStreamClientInterceptor):
                    self._stream_stream_interceptors.append(interceptor)
                else:
                    raise ValueError(
                        "Interceptor {} must be ".format(interceptor)
                        + "{} or ".format(UnaryUnaryClientInterceptor.__name__)
                        + "{} or ".format(UnaryStreamClientInterceptor.__name__)
                        + "{} or ".format(StreamUnaryClientInterceptor.__name__)
                        + "{}. ".format(StreamStreamClientInterceptor.__name__)
                    )

        self._loop = cygrpc.get_working_loop()
        self._channel = cygrpc.AioChannel(
            _common.encode(target),
            _augment_channel_arguments(options, compression),
            credentials,
            self._loop,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close(None)

    async def _close(self, grace):  # pylint: disable=too-many-branches
        if self._channel.closed():
            return

        # No new calls will be accepted by the Cython channel.
        self._channel.closing()

        # Iterate through running tasks
        tasks = _all_tasks()
        calls = []
        call_tasks = []
        for task in tasks:
            try:
                stack = task.get_stack(limit=1)
            except AttributeError as attribute_error:
                # NOTE(lidiz) tl;dr: If the Task is created with a CPython
                # object, it will trigger AttributeError.
                #
                # In the global finalizer, the event loop schedules
                # a CPython PyAsyncGenAThrow object.
                # https://github.com/python/cpython/blob/00e45877e33d32bb61aa13a2033e3bba370bda4d/Lib/asyncio/base_events.py#L484
                #
                # However, the PyAsyncGenAThrow object is written in C and
                # failed to include the normal Python frame objects. Hence,
                # this exception is a false negative, and it is safe to ignore
                # the failure. It is fixed by https://github.com/python/cpython/pull/18669,
                # but not available until 3.9 or 3.8.3. So, we have to keep it
                # for a while.
                # TODO(lidiz) drop this hack after 3.8 deprecation
                if "frame" in str(attribute_error):
                    continue
                else:
                    raise

            # If the Task is created by a C-extension, the stack will be empty.
            if not stack:
                continue

            # Locate ones created by `aio.Call`.
            frame = stack[0]
            candidate = frame.f_locals.get("self")
            # Explicitly check for a non-null candidate instead of the more pythonic 'if candidate:'
            # because doing 'if candidate:' assumes that the coroutine implements '__bool__' which
            # might not always be the case.
            if candidate is not None:
                if isinstance(candidate, _base_call.Call):
                    if hasattr(candidate, "_channel"):
                        # For intercepted Call object
                        if candidate._channel is not self._channel:
                            continue
                    elif hasattr(candidate, "_cython_call"):
                        # For normal Call object
                        if candidate._cython_call._channel is not self._channel:
                            continue
                    else:
                        # Unidentified Call object
                        raise cygrpc.InternalError(
                            f"Unrecognized call object: {candidate}"
                        )

                    calls.append(candidate)
                    call_tasks.append(task)

        # If needed, try to wait for them to finish.
        # Call objects are not always awaitables.
        if grace and call_tasks:
            await asyncio.wait(call_tasks, timeout=grace)

        # Time to cancel existing calls.
        for call in calls:
            call.cancel()

        # Destroy the channel
        self._channel.close()

    async def close(self, grace: Optional[float] = None):
        await self._close(grace)

    def __del__(self):
        if hasattr(self, "_channel"):
            if not self._channel.closed():
                self._channel.close()

    def get_state(
        self, try_to_connect: bool = False
    ) -> grpc.ChannelConnectivity:
        result = self._channel.check_connectivity_state(try_to_connect)
        return _common.CYGRPC_CONNECTIVITY_STATE_TO_CHANNEL_CONNECTIVITY[result]

    async def wait_for_state_change(
        self,
        last_observed_state: grpc.ChannelConnectivity,
    ) -> None:
        assert await self._channel.watch_connectivity_state(
            last_observed_state.value[0], None
        )

    async def channel_ready(self) -> None:
        state = self.get_state(try_to_connect=True)
        while state != grpc.ChannelConnectivity.READY:
            await self.wait_for_state_change(state)
            state = self.get_state(try_to_connect=True)

    # TODO(xuanwn): Implement this method after we have
    # observability for Asyncio.
    def _get_registered_call_handle(self, method: str) -> int:
        pass

    # TODO(xuanwn): Implement _registered_method after we have
    # observability for Asyncio.
    # pylint: disable=arguments-differ,unused-argument
    def unary_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> UnaryUnaryMultiCallable:
        return UnaryUnaryMultiCallable(
            self._channel,
            _common.encode(method),
            request_serializer,
            response_deserializer,
            self._unary_unary_interceptors,
            [self],
            self._loop,
        )

    # TODO(xuanwn): Implement _registered_method after we have
    # observability for Asyncio.
    # pylint: disable=arguments-differ,unused-argument
    def unary_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> UnaryStreamMultiCallable:
        return UnaryStreamMultiCallable(
            self._channel,
            _common.encode(method),
            request_serializer,
            response_deserializer,
            self._unary_stream_interceptors,
            [self],
            self._loop,
        )

    # TODO(xuanwn): Implement _registered_method after we have
    # observability for Asyncio.
    # pylint: disable=arguments-differ,unused-argument
    def stream_unary(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> StreamUnaryMultiCallable:
        return StreamUnaryMultiCallable(
            self._channel,
            _common.encode(method),
            request_serializer,
            response_deserializer,
            self._stream_unary_interceptors,
            [self],
            self._loop,
        )

    # TODO(xuanwn): Implement _registered_method after we have
    # observability for Asyncio.
    # pylint: disable=arguments-differ,unused-argument
    def stream_stream(
        self,
        method: str,
        request_serializer: Optional[SerializingFunction] = None,
        response_deserializer: Optional[DeserializingFunction] = None,
        _registered_method: Optional[bool] = False,
    ) -> StreamStreamMultiCallable:
        return StreamStreamMultiCallable(
            self._channel,
            _common.encode(method),
            request_serializer,
            response_deserializer,
            self._stream_stream_interceptors,
            [self],
            self._loop,
        )


def insecure_channel(
    target: str,
    options: Optional[ChannelArgumentType] = None,
    compression: Optional[grpc.Compression] = None,
    interceptors: Optional[Sequence[ClientInterceptor]] = None,
):
    """Creates an insecure asynchronous Channel to a server.

    Args:
      target: The server address
      options: An optional list of key-value pairs (:term:`channel_arguments`
        in gRPC Core runtime) to configure the channel.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel.
      interceptors: An optional sequence of interceptors that will be executed for
        any call executed with this channel.

    Returns:
      A Channel.
    """
    return Channel(
        target,
        () if options is None else options,
        None,
        compression,
        interceptors,
    )


def secure_channel(
    target: str,
    credentials: grpc.ChannelCredentials,
    options: Optional[ChannelArgumentType] = None,
    compression: Optional[grpc.Compression] = None,
    interceptors: Optional[Sequence[ClientInterceptor]] = None,
):
    """Creates a secure asynchronous Channel to a server.

    Args:
      target: The server address.
      credentials: A ChannelCredentials instance.
      options: An optional list of key-value pairs (:term:`channel_arguments`
        in gRPC Core runtime) to configure the channel.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel.
      interceptors: An optional sequence of interceptors that will be executed for
        any call executed with this channel.

    Returns:
      An aio.Channel.
    """
    return Channel(
        target,
        () if options is None else options,
        credentials._credentials,
        compression,
        interceptors,
    )

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\backend_gtk4.py ===
import functools
import io
import os

import matplotlib as mpl
from matplotlib import _api, backend_tools, cbook
from matplotlib.backend_bases import (
    ToolContainerBase, MouseButton,
    KeyEvent, LocationEvent, MouseEvent, ResizeEvent, CloseEvent)

try:
    import gi
except ImportError as err:
    raise ImportError("The GTK4 backends require PyGObject") from err

try:
    # :raises ValueError: If module/version is already loaded, already
    # required, or unavailable.
    gi.require_version("Gtk", "4.0")
except ValueError as e:
    # in this case we want to re-raise as ImportError so the
    # auto-backend selection logic correctly skips.
    raise ImportError(e) from e

from gi.repository import Gio, GLib, Gtk, Gdk, GdkPixbuf
from . import _backend_gtk
from ._backend_gtk import (  # noqa: F401 # pylint: disable=W0611
    _BackendGTK, _FigureCanvasGTK, _FigureManagerGTK, _NavigationToolbar2GTK,
    TimerGTK as TimerGTK4,
)

_GOBJECT_GE_3_47 = gi.version_info >= (3, 47, 0)


class FigureCanvasGTK4(_FigureCanvasGTK, Gtk.DrawingArea):
    required_interactive_framework = "gtk4"
    supports_blit = False
    manager_class = _api.classproperty(lambda cls: FigureManagerGTK4)

    def __init__(self, figure=None):
        super().__init__(figure=figure)

        self.set_hexpand(True)
        self.set_vexpand(True)

        self._idle_draw_id = 0
        self._rubberband_rect = None

        self.set_draw_func(self._draw_func)
        self.connect('resize', self.resize_event)
        self.connect('notify::scale-factor', self._update_device_pixel_ratio)

        click = Gtk.GestureClick()
        click.set_button(0)  # All buttons.
        click.connect('pressed', self.button_press_event)
        click.connect('released', self.button_release_event)
        self.add_controller(click)

        key = Gtk.EventControllerKey()
        key.connect('key-pressed', self.key_press_event)
        key.connect('key-released', self.key_release_event)
        self.add_controller(key)

        motion = Gtk.EventControllerMotion()
        motion.connect('motion', self.motion_notify_event)
        motion.connect('enter', self.enter_notify_event)
        motion.connect('leave', self.leave_notify_event)
        self.add_controller(motion)

        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect('scroll', self.scroll_event)
        self.add_controller(scroll)

        self.set_focusable(True)

        css = Gtk.CssProvider()
        style = '.matplotlib-canvas { background-color: white; }'
        if Gtk.check_version(4, 9, 3) is None:
            css.load_from_data(style, -1)
        else:
            css.load_from_data(style.encode('utf-8'))
        style_ctx = self.get_style_context()
        style_ctx.add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        style_ctx.add_class("matplotlib-canvas")

    def destroy(self):
        CloseEvent("close_event", self)._process()

    def set_cursor(self, cursor):
        # docstring inherited
        self.set_cursor_from_name(_backend_gtk.mpl_to_gtk_cursor_name(cursor))

    def _mpl_coords(self, xy=None):
        """
        Convert the *xy* position of a GTK event, or of the current cursor
        position if *xy* is None, to Matplotlib coordinates.

        GTK use logical pixels, but the figure is scaled to physical pixels for
        rendering.  Transform to physical pixels so that all of the down-stream
        transforms work as expected.

        Also, the origin is different and needs to be corrected.
        """
        if xy is None:
            surface = self.get_native().get_surface()
            is_over, x, y, mask = surface.get_device_position(
                self.get_display().get_default_seat().get_pointer())
        else:
            x, y = xy
        x = x * self.device_pixel_ratio
        # flip y so y=0 is bottom of canvas
        y = self.figure.bbox.height - y * self.device_pixel_ratio
        return x, y

    def scroll_event(self, controller, dx, dy):
        MouseEvent(
            "scroll_event", self, *self._mpl_coords(), step=dy,
            modifiers=self._mpl_modifiers(controller),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()
        return True

    def button_press_event(self, controller, n_press, x, y):
        MouseEvent(
            "button_press_event", self, *self._mpl_coords((x, y)),
            controller.get_current_button(),
            modifiers=self._mpl_modifiers(controller),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()
        self.grab_focus()

    def button_release_event(self, controller, n_press, x, y):
        MouseEvent(
            "button_release_event", self, *self._mpl_coords((x, y)),
            controller.get_current_button(),
            modifiers=self._mpl_modifiers(controller),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()

    def key_press_event(self, controller, keyval, keycode, state):
        KeyEvent(
            "key_press_event", self, self._get_key(keyval, keycode, state),
            *self._mpl_coords(),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()
        return True

    def key_release_event(self, controller, keyval, keycode, state):
        KeyEvent(
            "key_release_event", self, self._get_key(keyval, keycode, state),
            *self._mpl_coords(),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()
        return True

    def motion_notify_event(self, controller, x, y):
        MouseEvent(
            "motion_notify_event", self, *self._mpl_coords((x, y)),
            buttons=self._mpl_buttons(controller),
            modifiers=self._mpl_modifiers(controller),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()

    def enter_notify_event(self, controller, x, y):
        LocationEvent(
            "figure_enter_event", self, *self._mpl_coords((x, y)),
            modifiers=self._mpl_modifiers(),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()

    def leave_notify_event(self, controller):
        LocationEvent(
            "figure_leave_event", self, *self._mpl_coords(),
            modifiers=self._mpl_modifiers(),
            guiEvent=controller.get_current_event() if _GOBJECT_GE_3_47 else None,
        )._process()

    def resize_event(self, area, width, height):
        self._update_device_pixel_ratio()
        dpi = self.figure.dpi
        winch = width * self.device_pixel_ratio / dpi
        hinch = height * self.device_pixel_ratio / dpi
        self.figure.set_size_inches(winch, hinch, forward=False)
        ResizeEvent("resize_event", self)._process()
        self.draw_idle()

    def _mpl_buttons(self, controller):
        # NOTE: This spews "Broken accounting of active state" warnings on
        # right click on macOS.
        surface = self.get_native().get_surface()
        is_over, x, y, event_state = surface.get_device_position(
            self.get_display().get_default_seat().get_pointer())
        # NOTE: alternatively we could use
        #   event_state = controller.get_current_event_state()
        # but for button_press/button_release this would report the state
        # *prior* to the event rather than after it; the above reports the
        # state *after* it.
        mod_table = [
            (MouseButton.LEFT, Gdk.ModifierType.BUTTON1_MASK),
            (MouseButton.MIDDLE, Gdk.ModifierType.BUTTON2_MASK),
            (MouseButton.RIGHT, Gdk.ModifierType.BUTTON3_MASK),
            (MouseButton.BACK, Gdk.ModifierType.BUTTON4_MASK),
            (MouseButton.FORWARD, Gdk.ModifierType.BUTTON5_MASK),
        ]
        return {name for name, mask in mod_table if event_state & mask}

    def _mpl_modifiers(self, controller=None):
        if controller is None:
            surface = self.get_native().get_surface()
            is_over, x, y, event_state = surface.get_device_position(
                self.get_display().get_default_seat().get_pointer())
        else:
            event_state = controller.get_current_event_state()
        mod_table = [
            ("ctrl", Gdk.ModifierType.CONTROL_MASK),
            ("alt", Gdk.ModifierType.ALT_MASK),
            ("shift", Gdk.ModifierType.SHIFT_MASK),
            ("super", Gdk.ModifierType.SUPER_MASK),
        ]
        return [name for name, mask in mod_table if event_state & mask]

    def _get_key(self, keyval, keycode, state):
        unikey = chr(Gdk.keyval_to_unicode(keyval))
        key = cbook._unikey_or_keysym_to_mplkey(
            unikey,
            Gdk.keyval_name(keyval))
        modifiers = [
            ("ctrl", Gdk.ModifierType.CONTROL_MASK, "control"),
            ("alt", Gdk.ModifierType.ALT_MASK, "alt"),
            ("shift", Gdk.ModifierType.SHIFT_MASK, "shift"),
            ("super", Gdk.ModifierType.SUPER_MASK, "super"),
        ]
        mods = [
            mod for mod, mask, mod_key in modifiers
            if (mod_key != key and state & mask
                and not (mod == "shift" and unikey.isprintable()))]
        return "+".join([*mods, key])

    def _update_device_pixel_ratio(self, *args, **kwargs):
        # We need to be careful in cases with mixed resolution displays if
        # device_pixel_ratio changes.
        if self._set_device_pixel_ratio(self.get_scale_factor()):
            self.draw()

    def _draw_rubberband(self, rect):
        self._rubberband_rect = rect
        # TODO: Only update the rubberband area.
        self.queue_draw()

    def _draw_func(self, drawing_area, ctx, width, height):
        self.on_draw_event(self, ctx)
        self._post_draw(self, ctx)

    def _post_draw(self, widget, ctx):
        if self._rubberband_rect is None:
            return

        lw = 1
        dash = 3
        x0, y0, w, h = (dim / self.device_pixel_ratio
                        for dim in self._rubberband_rect)
        x1 = x0 + w
        y1 = y0 + h

        # Draw the lines from x0, y0 towards x1, y1 so that the
        # dashes don't "jump" when moving the zoom box.
        ctx.move_to(x0, y0)
        ctx.line_to(x0, y1)
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y0)
        ctx.move_to(x0, y1)
        ctx.line_to(x1, y1)
        ctx.move_to(x1, y0)
        ctx.line_to(x1, y1)

        ctx.set_antialias(1)
        ctx.set_line_width(lw)
        ctx.set_dash((dash, dash), 0)
        ctx.set_source_rgb(0, 0, 0)
        ctx.stroke_preserve()

        ctx.set_dash((dash, dash), dash)
        ctx.set_source_rgb(1, 1, 1)
        ctx.stroke()

    def on_draw_event(self, widget, ctx):
        # to be overwritten by GTK4Agg or GTK4Cairo
        pass

    def draw(self):
        # docstring inherited
        if self.is_drawable():
            self.queue_draw()

    def draw_idle(self):
        # docstring inherited
        if self._idle_draw_id != 0:
            return
        def idle_draw(*args):
            try:
                self.draw()
            finally:
                self._idle_draw_id = 0
            return False
        self._idle_draw_id = GLib.idle_add(idle_draw)

    def flush_events(self):
        # docstring inherited
        context = GLib.MainContext.default()
        while context.pending():
            context.iteration(True)


class NavigationToolbar2GTK4(_NavigationToolbar2GTK, Gtk.Box):
    def __init__(self, canvas):
        Gtk.Box.__init__(self)

        self.add_css_class('toolbar')

        self._gtk_ids = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self.append(Gtk.Separator())
                continue
            image = Gtk.Image.new_from_gicon(
                Gio.Icon.new_for_string(
                    str(cbook._get_data_path('images',
                                             f'{image_file}-symbolic.svg'))))
            self._gtk_ids[text] = button = (
                Gtk.ToggleButton() if callback in ['zoom', 'pan'] else
                Gtk.Button())
            button.set_child(image)
            button.add_css_class('flat')
            button.add_css_class('image-button')
            # Save the handler id, so that we can block it as needed.
            button._signal_handler = button.connect(
                'clicked', getattr(self, callback))
            button.set_tooltip_text(tooltip_text)
            self.append(button)

        # This filler item ensures the toolbar is always at least two text
        # lines high. Otherwise the canvas gets redrawn as the mouse hovers
        # over images because those use two-line messages which resize the
        # toolbar.
        label = Gtk.Label()
        label.set_markup(
            '<small>\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}</small>')
        label.set_hexpand(True)  # Push real message to the right.
        self.append(label)

        self.message = Gtk.Label()
        self.message.set_justify(Gtk.Justification.RIGHT)
        self.append(self.message)

        _NavigationToolbar2GTK.__init__(self, canvas)

    def save_figure(self, *args):
        dialog = Gtk.FileChooserNative(
            title='Save the figure',
            transient_for=self.canvas.get_root(),
            action=Gtk.FileChooserAction.SAVE,
            modal=True)
        self._save_dialog = dialog  # Must keep a reference.

        ff = Gtk.FileFilter()
        ff.set_name('All files')
        ff.add_pattern('*')
        dialog.add_filter(ff)
        dialog.set_filter(ff)

        formats = []
        default_format = None
        for i, (name, fmts) in enumerate(
                self.canvas.get_supported_filetypes_grouped().items()):
            ff = Gtk.FileFilter()
            ff.set_name(name)
            for fmt in fmts:
                ff.add_pattern(f'*.{fmt}')
            dialog.add_filter(ff)
            formats.append(name)
            if self.canvas.get_default_filetype() in fmts:
                default_format = i
        # Setting the choice doesn't always work, so make sure the default
        # format is first.
        formats = [formats[default_format], *formats[:default_format],
                   *formats[default_format+1:]]
        dialog.add_choice('format', 'File format', formats, formats)
        dialog.set_choice('format', formats[0])

        dialog.set_current_folder(Gio.File.new_for_path(
            os.path.expanduser(mpl.rcParams['savefig.directory'])))
        dialog.set_current_name(self.canvas.get_default_filename())

        @functools.partial(dialog.connect, 'response')
        def on_response(dialog, response):
            file = dialog.get_file()
            fmt = dialog.get_choice('format')
            fmt = self.canvas.get_supported_filetypes_grouped()[fmt][0]
            dialog.destroy()
            self._save_dialog = None
            if response != Gtk.ResponseType.ACCEPT:
                return
            # Save dir for next time, unless empty str (which means use cwd).
            if mpl.rcParams['savefig.directory']:
                parent = file.get_parent()
                mpl.rcParams['savefig.directory'] = parent.get_path()
            try:
                self.canvas.figure.savefig(file.get_path(), format=fmt)
            except Exception as e:
                msg = Gtk.MessageDialog(
                    transient_for=self.canvas.get_root(),
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK, modal=True,
                    text=str(e))
                msg.show()

        dialog.show()
        return self.UNKNOWN_SAVED_STATUS


class ToolbarGTK4(ToolContainerBase, Gtk.Box):
    _icon_extension = '-symbolic.svg'

    def __init__(self, toolmanager):
        ToolContainerBase.__init__(self, toolmanager)
        Gtk.Box.__init__(self)
        self.set_property('orientation', Gtk.Orientation.HORIZONTAL)

        # Tool items are created later, but must appear before the message.
        self._tool_box = Gtk.Box()
        self.append(self._tool_box)
        self._groups = {}
        self._toolitems = {}

        # This filler item ensures the toolbar is always at least two text
        # lines high. Otherwise the canvas gets redrawn as the mouse hovers
        # over images because those use two-line messages which resize the
        # toolbar.
        label = Gtk.Label()
        label.set_markup(
            '<small>\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}</small>')
        label.set_hexpand(True)  # Push real message to the right.
        self.append(label)

        self._message = Gtk.Label()
        self._message.set_justify(Gtk.Justification.RIGHT)
        self.append(self._message)

    def add_toolitem(self, name, group, position, image_file, description,
                     toggle):
        if toggle:
            button = Gtk.ToggleButton()
        else:
            button = Gtk.Button()
        button.set_label(name)
        button.add_css_class('flat')

        if image_file is not None:
            image = Gtk.Image.new_from_gicon(
                Gio.Icon.new_for_string(image_file))
            button.set_child(image)
            button.add_css_class('image-button')

        if position is None:
            position = -1

        self._add_button(button, group, position)
        signal = button.connect('clicked', self._call_tool, name)
        button.set_tooltip_text(description)
        self._toolitems.setdefault(name, [])
        self._toolitems[name].append((button, signal))

    def _find_child_at_position(self, group, position):
        children = [None]
        child = self._groups[group].get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()
        return children[position]

    def _add_button(self, button, group, position):
        if group not in self._groups:
            if self._groups:
                self._add_separator()
            group_box = Gtk.Box()
            self._tool_box.append(group_box)
            self._groups[group] = group_box
        self._groups[group].insert_child_after(
            button, self._find_child_at_position(group, position))

    def _call_tool(self, btn, name):
        self.trigger_tool(name)

    def toggle_toolitem(self, name, toggled):
        if name not in self._toolitems:
            return
        for toolitem, signal in self._toolitems[name]:
            toolitem.handler_block(signal)
            toolitem.set_active(toggled)
            toolitem.handler_unblock(signal)

    def remove_toolitem(self, name):
        for toolitem, _signal in self._toolitems.pop(name, []):
            for group in self._groups:
                if toolitem in self._groups[group]:
                    self._groups[group].remove(toolitem)

    def _add_separator(self):
        sep = Gtk.Separator()
        sep.set_property("orientation", Gtk.Orientation.VERTICAL)
        self._tool_box.append(sep)

    def set_message(self, s):
        self._message.set_label(s)


@backend_tools._register_tool_class(FigureCanvasGTK4)
class SaveFigureGTK4(backend_tools.SaveFigureBase):
    def trigger(self, *args, **kwargs):
        NavigationToolbar2GTK4.save_figure(
            self._make_classic_style_pseudo_toolbar())


@backend_tools._register_tool_class(FigureCanvasGTK4)
class HelpGTK4(backend_tools.ToolHelpBase):
    def _normalize_shortcut(self, key):
        """
        Convert Matplotlib key presses to GTK+ accelerator identifiers.

        Related to `FigureCanvasGTK4._get_key`.
        """
        special = {
            'backspace': 'BackSpace',
            'pagedown': 'Page_Down',
            'pageup': 'Page_Up',
            'scroll_lock': 'Scroll_Lock',
        }

        parts = key.split('+')
        mods = ['<' + mod + '>' for mod in parts[:-1]]
        key = parts[-1]

        if key in special:
            key = special[key]
        elif len(key) > 1:
            key = key.capitalize()
        elif key.isupper():
            mods += ['<shift>']

        return ''.join(mods) + key

    def _is_valid_shortcut(self, key):
        """
        Check for a valid shortcut to be displayed.

        - GTK will never send 'cmd+' (see `FigureCanvasGTK4._get_key`).
        - The shortcut window only shows keyboard shortcuts, not mouse buttons.
        """
        return 'cmd+' not in key and not key.startswith('MouseButton.')

    def trigger(self, *args):
        section = Gtk.ShortcutsSection()

        for name, tool in sorted(self.toolmanager.tools.items()):
            if not tool.description:
                continue

            # Putting everything in a separate group allows GTK to
            # automatically split them into separate columns/pages, which is
            # useful because we have lots of shortcuts, some with many keys
            # that are very wide.
            group = Gtk.ShortcutsGroup()
            section.append(group)
            # A hack to remove the title since we have no group naming.
            child = group.get_first_child()
            while child is not None:
                child.set_visible(False)
                child = child.get_next_sibling()

            shortcut = Gtk.ShortcutsShortcut(
                accelerator=' '.join(
                    self._normalize_shortcut(key)
                    for key in self.toolmanager.get_tool_keymap(name)
                    if self._is_valid_shortcut(key)),
                title=tool.name,
                subtitle=tool.description)
            group.append(shortcut)

        window = Gtk.ShortcutsWindow(
            title='Help',
            modal=True,
            transient_for=self._figure.canvas.get_root())
        window.set_child(section)

        window.show()


@backend_tools._register_tool_class(FigureCanvasGTK4)
class ToolCopyToClipboardGTK4(backend_tools.ToolCopyToClipboardBase):
    def trigger(self, *args, **kwargs):
        with io.BytesIO() as f:
            self.canvas.print_rgba(f)
            w, h = self.canvas.get_width_height()
            pb = GdkPixbuf.Pixbuf.new_from_data(f.getbuffer(),
                                                GdkPixbuf.Colorspace.RGB, True,
                                                8, w, h, w*4)
        clipboard = self.canvas.get_clipboard()
        clipboard.set(pb)


backend_tools._register_tool_class(
    FigureCanvasGTK4, _backend_gtk.ConfigureSubplotsGTK)
backend_tools._register_tool_class(
    FigureCanvasGTK4, _backend_gtk.RubberbandGTK)
Toolbar = ToolbarGTK4


class FigureManagerGTK4(_FigureManagerGTK):
    _toolbar2_class = NavigationToolbar2GTK4
    _toolmanager_toolbar_class = ToolbarGTK4


@_BackendGTK.export
class _BackendGTK4(_BackendGTK):
    FigureCanvas = FigureCanvasGTK4
    FigureManager = FigureManagerGTK4

# === NexusCore/openenv\Lib\site-packages\nltk\tree\prettyprinter.py ===
# Natural Language Toolkit: ASCII visualization of NLTK trees
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Andreas van Cranenburgh <A.W.vanCranenburgh@uva.nl>
#         Peter Ljunglöf <peter.ljunglof@gu.se>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Pretty-printing of discontinuous trees.
Adapted from the disco-dop project, by Andreas van Cranenburgh.
https://github.com/andreasvc/disco-dop

Interesting reference (not used for this code):
T. Eschbach et al., Orth. Hypergraph Drawing, Journal of
Graph Algorithms and Applications, 10(2) 141--157 (2006)149.
https://jgaa.info/accepted/2006/EschbachGuentherBecker2006.10.2.pdf
"""

import re

try:
    from html import escape
except ImportError:
    from cgi import escape

from collections import defaultdict
from operator import itemgetter

from nltk.tree.tree import Tree
from nltk.util import OrderedDict

ANSICOLOR = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
}


class TreePrettyPrinter:
    """
    Pretty-print a tree in text format, either as ASCII or Unicode.
    The tree can be a normal tree, or discontinuous.

    ``TreePrettyPrinter(tree, sentence=None, highlight=())``
    creates an object from which different visualizations can be created.

    :param tree: a Tree object.
    :param sentence: a list of words (strings). If `sentence` is given,
        `tree` must contain integers as leaves, which are taken as indices
        in `sentence`. Using this you can display a discontinuous tree.
    :param highlight: Optionally, a sequence of Tree objects in `tree` which
        should be highlighted. Has the effect of only applying colors to nodes
        in this sequence (nodes should be given as Tree objects, terminals as
        indices).

    >>> from nltk.tree import Tree
    >>> tree = Tree.fromstring('(S (NP Mary) (VP walks))')
    >>> print(TreePrettyPrinter(tree).text())
    ... # doctest: +NORMALIZE_WHITESPACE
          S
      ____|____
     NP        VP
     |         |
    Mary     walks
    """

    def __init__(self, tree, sentence=None, highlight=()):
        if sentence is None:
            leaves = tree.leaves()
            if (
                leaves
                and all(len(a) > 0 for a in tree.subtrees())
                and all(isinstance(a, int) for a in leaves)
            ):
                sentence = [str(a) for a in leaves]
            else:
                # this deals with empty nodes (frontier non-terminals)
                # and multiple/mixed terminals under non-terminals.
                tree = tree.copy(True)
                sentence = []
                for a in tree.subtrees():
                    if len(a) == 0:
                        a.append(len(sentence))
                        sentence.append(None)
                    elif any(not isinstance(b, Tree) for b in a):
                        for n, b in enumerate(a):
                            if not isinstance(b, Tree):
                                a[n] = len(sentence)
                                if type(b) == tuple:
                                    b = "/".join(b)
                                sentence.append("%s" % b)
        self.nodes, self.coords, self.edges, self.highlight = self.nodecoords(
            tree, sentence, highlight
        )

    def __str__(self):
        return self.text()

    def __repr__(self):
        return "<TreePrettyPrinter with %d nodes>" % len(self.nodes)

    @staticmethod
    def nodecoords(tree, sentence, highlight):
        """
        Produce coordinates of nodes on a grid.

        Objective:

        - Produce coordinates for a non-overlapping placement of nodes and
            horizontal lines.
        - Order edges so that crossing edges cross a minimal number of previous
            horizontal lines (never vertical lines).

        Approach:

        - bottom up level order traversal (start at terminals)
        - at each level, identify nodes which cannot be on the same row
        - identify nodes which cannot be in the same column
        - place nodes into a grid at (row, column)
        - order child-parent edges with crossing edges last

        Coordinates are (row, column); the origin (0, 0) is at the top left;
        the root node is on row 0. Coordinates do not consider the size of a
        node (which depends on font, &c), so the width of a column of the grid
        should be automatically determined by the element with the greatest
        width in that column. Alternatively, the integer coordinates could be
        converted to coordinates in which the distances between adjacent nodes
        are non-uniform.

        Produces tuple (nodes, coords, edges, highlighted) where:

        - nodes[id]: Tree object for the node with this integer id
        - coords[id]: (n, m) coordinate where to draw node with id in the grid
        - edges[id]: parent id of node with this id (ordered dictionary)
        - highlighted: set of ids that should be highlighted
        """

        def findcell(m, matrix, startoflevel, children):
            """
            Find vacant row, column index for node ``m``.
            Iterate over current rows for this level (try lowest first)
            and look for cell between first and last child of this node,
            add new row to level if no free row available.
            """
            candidates = [a for _, a in children[m]]
            minidx, maxidx = min(candidates), max(candidates)
            leaves = tree[m].leaves()
            center = scale * sum(leaves) // len(leaves)  # center of gravity
            if minidx < maxidx and not minidx < center < maxidx:
                center = sum(candidates) // len(candidates)
            if max(candidates) - min(candidates) > 2 * scale:
                center -= center % scale  # round to unscaled coordinate
                if minidx < maxidx and not minidx < center < maxidx:
                    center += scale
            if ids[m] == 0:
                startoflevel = len(matrix)
            for rowidx in range(startoflevel, len(matrix) + 1):
                if rowidx == len(matrix):  # need to add a new row
                    matrix.append(
                        [
                            vertline if a not in (corner, None) else None
                            for a in matrix[-1]
                        ]
                    )
                row = matrix[rowidx]
                if len(children[m]) == 1:  # place unaries directly above child
                    return rowidx, next(iter(children[m]))[1]
                elif all(
                    a is None or a == vertline
                    for a in row[min(candidates) : max(candidates) + 1]
                ):
                    # find free column
                    for n in range(scale):
                        i = j = center + n
                        while j > minidx or i < maxidx:
                            if i < maxidx and (
                                matrix[rowidx][i] is None or i in candidates
                            ):
                                return rowidx, i
                            elif j > minidx and (
                                matrix[rowidx][j] is None or j in candidates
                            ):
                                return rowidx, j
                            i += scale
                            j -= scale
            raise ValueError(
                "could not find a free cell for:\n%s\n%s"
                "min=%d; max=%d" % (tree[m], minidx, maxidx, dumpmatrix())
            )

        def dumpmatrix():
            """Dump matrix contents for debugging purposes."""
            return "\n".join(
                "%2d: %s" % (n, " ".join(("%2r" % i)[:2] for i in row))
                for n, row in enumerate(matrix)
            )

        leaves = tree.leaves()
        if not all(isinstance(n, int) for n in leaves):
            raise ValueError("All leaves must be integer indices.")
        if len(leaves) != len(set(leaves)):
            raise ValueError("Indices must occur at most once.")
        if not all(0 <= n < len(sentence) for n in leaves):
            raise ValueError(
                "All leaves must be in the interval 0..n "
                "with n=len(sentence)\ntokens: %d indices: "
                "%r\nsentence: %s" % (len(sentence), tree.leaves(), sentence)
            )
        vertline, corner = -1, -2  # constants
        tree = tree.copy(True)
        for a in tree.subtrees():
            a.sort(key=lambda n: min(n.leaves()) if isinstance(n, Tree) else n)
        scale = 2
        crossed = set()
        # internal nodes and lexical nodes (no frontiers)
        positions = tree.treepositions()
        maxdepth = max(map(len, positions)) + 1
        childcols = defaultdict(set)
        matrix = [[None] * (len(sentence) * scale)]
        nodes = {}
        ids = {a: n for n, a in enumerate(positions)}
        highlighted_nodes = {
            n for a, n in ids.items() if not highlight or tree[a] in highlight
        }
        levels = {n: [] for n in range(maxdepth - 1)}
        terminals = []
        for a in positions:
            node = tree[a]
            if isinstance(node, Tree):
                levels[maxdepth - node.height()].append(a)
            else:
                terminals.append(a)

        for n in levels:
            levels[n].sort(key=lambda n: max(tree[n].leaves()) - min(tree[n].leaves()))
        terminals.sort()
        positions = set(positions)

        for m in terminals:
            i = int(tree[m]) * scale
            assert matrix[0][i] is None, (matrix[0][i], m, i)
            matrix[0][i] = ids[m]
            nodes[ids[m]] = sentence[tree[m]]
            if nodes[ids[m]] is None:
                nodes[ids[m]] = "..."
                highlighted_nodes.discard(ids[m])
            positions.remove(m)
            childcols[m[:-1]].add((0, i))

        # add other nodes centered on their children,
        # if the center is already taken, back off
        # to the left and right alternately, until an empty cell is found.
        for n in sorted(levels, reverse=True):
            nodesatdepth = levels[n]
            startoflevel = len(matrix)
            matrix.append(
                [vertline if a not in (corner, None) else None for a in matrix[-1]]
            )
            for m in nodesatdepth:  # [::-1]:
                if n < maxdepth - 1 and childcols[m]:
                    _, pivot = min(childcols[m], key=itemgetter(1))
                    if {
                        a[:-1]
                        for row in matrix[:-1]
                        for a in row[:pivot]
                        if isinstance(a, tuple)
                    } & {
                        a[:-1]
                        for row in matrix[:-1]
                        for a in row[pivot:]
                        if isinstance(a, tuple)
                    }:
                        crossed.add(m)

                rowidx, i = findcell(m, matrix, startoflevel, childcols)
                positions.remove(m)

                # block positions where children of this node branch out
                for _, x in childcols[m]:
                    matrix[rowidx][x] = corner
                # assert m == () or matrix[rowidx][i] in (None, corner), (
                #         matrix[rowidx][i], m, str(tree), ' '.join(sentence))
                # node itself
                matrix[rowidx][i] = ids[m]
                nodes[ids[m]] = tree[m]
                # add column to the set of children for its parent
                if len(m) > 0:
                    childcols[m[:-1]].add((rowidx, i))
        assert len(positions) == 0

        # remove unused columns, right to left
        for m in range(scale * len(sentence) - 1, -1, -1):
            if not any(isinstance(row[m], (Tree, int)) for row in matrix):
                for row in matrix:
                    del row[m]

        # remove unused rows, reverse
        matrix = [
            row
            for row in reversed(matrix)
            if not all(a is None or a == vertline for a in row)
        ]

        # collect coordinates of nodes
        coords = {}
        for n, _ in enumerate(matrix):
            for m, i in enumerate(matrix[n]):
                if isinstance(i, int) and i >= 0:
                    coords[i] = n, m

        # move crossed edges last
        positions = sorted(
            (a for level in levels.values() for a in level),
            key=lambda a: a[:-1] in crossed,
        )

        # collect edges from node to node
        edges = OrderedDict()
        for i in reversed(positions):
            for j, _ in enumerate(tree[i]):
                edges[ids[i + (j,)]] = ids[i]

        return nodes, coords, edges, highlighted_nodes

    def text(
        self,
        nodedist=1,
        unicodelines=False,
        html=False,
        ansi=False,
        nodecolor="blue",
        leafcolor="red",
        funccolor="green",
        abbreviate=None,
        maxwidth=16,
    ):
        """
        :return: ASCII art for a discontinuous tree.

        :param unicodelines: whether to use Unicode line drawing characters
            instead of plain (7-bit) ASCII.
        :param html: whether to wrap output in html code (default plain text).
        :param ansi: whether to produce colors with ANSI escape sequences
            (only effective when html==False).
        :param leafcolor, nodecolor: specify colors of leaves and phrasal
            nodes; effective when either html or ansi is True.
        :param abbreviate: if True, abbreviate labels longer than 5 characters.
            If integer, abbreviate labels longer than `abbr` characters.
        :param maxwidth: maximum number of characters before a label starts to
            wrap; pass None to disable.
        """
        if abbreviate == True:
            abbreviate = 5
        if unicodelines:
            horzline = "\u2500"
            leftcorner = "\u250c"
            rightcorner = "\u2510"
            vertline = " \u2502 "
            tee = horzline + "\u252C" + horzline
            bottom = horzline + "\u2534" + horzline
            cross = horzline + "\u253c" + horzline
            ellipsis = "\u2026"
        else:
            horzline = "_"
            leftcorner = rightcorner = " "
            vertline = " | "
            tee = 3 * horzline
            cross = bottom = "_|_"
            ellipsis = "."

        def crosscell(cur, x=vertline):
            """Overwrite center of this cell with a vertical branch."""
            splitl = len(cur) - len(cur) // 2 - len(x) // 2 - 1
            lst = list(cur)
            lst[splitl : splitl + len(x)] = list(x)
            return "".join(lst)

        result = []
        matrix = defaultdict(dict)
        maxnodewith = defaultdict(lambda: 3)
        maxnodeheight = defaultdict(lambda: 1)
        maxcol = 0
        minchildcol = {}
        maxchildcol = {}
        childcols = defaultdict(set)
        labels = {}
        wrapre = re.compile(
            "(.{%d,%d}\\b\\W*|.{%d})" % (maxwidth - 4, maxwidth, maxwidth)
        )
        # collect labels and coordinates
        for a in self.nodes:
            row, column = self.coords[a]
            matrix[row][column] = a
            maxcol = max(maxcol, column)
            label = (
                self.nodes[a].label()
                if isinstance(self.nodes[a], Tree)
                else self.nodes[a]
            )
            if abbreviate and len(label) > abbreviate:
                label = label[:abbreviate] + ellipsis
            if maxwidth and len(label) > maxwidth:
                label = wrapre.sub(r"\1\n", label).strip()
            label = label.split("\n")
            maxnodeheight[row] = max(maxnodeheight[row], len(label))
            maxnodewith[column] = max(maxnodewith[column], max(map(len, label)))
            labels[a] = label
            if a not in self.edges:
                continue  # e.g., root
            parent = self.edges[a]
            childcols[parent].add((row, column))
            minchildcol[parent] = min(minchildcol.get(parent, column), column)
            maxchildcol[parent] = max(maxchildcol.get(parent, column), column)
        # bottom up level order traversal
        for row in sorted(matrix, reverse=True):
            noderows = [
                ["".center(maxnodewith[col]) for col in range(maxcol + 1)]
                for _ in range(maxnodeheight[row])
            ]
            branchrow = ["".center(maxnodewith[col]) for col in range(maxcol + 1)]
            for col in matrix[row]:
                n = matrix[row][col]
                node = self.nodes[n]
                text = labels[n]
                if isinstance(node, Tree):
                    # draw horizontal branch towards children for this node
                    if n in minchildcol and minchildcol[n] < maxchildcol[n]:
                        i, j = minchildcol[n], maxchildcol[n]
                        a, b = (maxnodewith[i] + 1) // 2 - 1, maxnodewith[j] // 2
                        branchrow[i] = ((" " * a) + leftcorner).ljust(
                            maxnodewith[i], horzline
                        )
                        branchrow[j] = (rightcorner + (" " * b)).rjust(
                            maxnodewith[j], horzline
                        )
                        for i in range(minchildcol[n] + 1, maxchildcol[n]):
                            if i == col and any(a == i for _, a in childcols[n]):
                                line = cross
                            elif i == col:
                                line = bottom
                            elif any(a == i for _, a in childcols[n]):
                                line = tee
                            else:
                                line = horzline
                            branchrow[i] = line.center(maxnodewith[i], horzline)
                    else:  # if n and n in minchildcol:
                        branchrow[col] = crosscell(branchrow[col])
                text = [a.center(maxnodewith[col]) for a in text]
                color = nodecolor if isinstance(node, Tree) else leafcolor
                if isinstance(node, Tree) and node.label().startswith("-"):
                    color = funccolor
                if html:
                    text = [escape(a, quote=False) for a in text]
                    if n in self.highlight:
                        text = [f"<font color={color}>{a}</font>" for a in text]
                elif ansi and n in self.highlight:
                    text = ["\x1b[%d;1m%s\x1b[0m" % (ANSICOLOR[color], a) for a in text]
                for x in range(maxnodeheight[row]):
                    # draw vertical lines in partially filled multiline node
                    # labels, but only if it's not a frontier node.
                    noderows[x][col] = (
                        text[x]
                        if x < len(text)
                        else (vertline if childcols[n] else " ").center(
                            maxnodewith[col], " "
                        )
                    )
            # for each column, if there is a node below us which has a parent
            # above us, draw a vertical branch in that column.
            if row != max(matrix):
                for n, (childrow, col) in self.coords.items():
                    if n > 0 and self.coords[self.edges[n]][0] < row < childrow:
                        branchrow[col] = crosscell(branchrow[col])
                        if col not in matrix[row]:
                            for noderow in noderows:
                                noderow[col] = crosscell(noderow[col])
                branchrow = [
                    a + ((a[-1] if a[-1] != " " else b[0]) * nodedist)
                    for a, b in zip(branchrow, branchrow[1:] + [" "])
                ]
                result.append("".join(branchrow))
            result.extend(
                (" " * nodedist).join(noderow) for noderow in reversed(noderows)
            )
        return "\n".join(reversed(result)) + "\n"

    def svg(self, nodecolor="blue", leafcolor="red", funccolor="green"):
        """
        :return: SVG representation of a tree.
        """
        fontsize = 12
        hscale = 40
        vscale = 25
        hstart = vstart = 20
        width = max(col for _, col in self.coords.values())
        height = max(row for row, _ in self.coords.values())
        result = [
            '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
            'width="%dem" height="%dem" viewBox="%d %d %d %d">'
            % (
                width * 3,
                height * 2.5,
                -hstart,
                -vstart,
                width * hscale + 3 * hstart,
                height * vscale + 3 * vstart,
            )
        ]

        children = defaultdict(set)
        for n in self.nodes:
            if n:
                children[self.edges[n]].add(n)

        # horizontal branches from nodes to children
        for node in self.nodes:
            if not children[node]:
                continue
            y, x = self.coords[node]
            x *= hscale
            y *= vscale
            x += hstart
            y += vstart + fontsize // 2
            childx = [self.coords[c][1] for c in children[node]]
            xmin = hstart + hscale * min(childx)
            xmax = hstart + hscale * max(childx)
            result.append(
                '\t<polyline style="stroke:black; stroke-width:1; fill:none;" '
                'points="%g,%g %g,%g" />' % (xmin, y, xmax, y)
            )
            result.append(
                '\t<polyline style="stroke:black; stroke-width:1; fill:none;" '
                'points="%g,%g %g,%g" />' % (x, y, x, y - fontsize // 3)
            )

        # vertical branches from children to parents
        for child, parent in self.edges.items():
            y, _ = self.coords[parent]
            y *= vscale
            y += vstart + fontsize // 2
            childy, childx = self.coords[child]
            childx *= hscale
            childy *= vscale
            childx += hstart
            childy += vstart - fontsize
            result += [
                '\t<polyline style="stroke:white; stroke-width:10; fill:none;"'
                ' points="%g,%g %g,%g" />' % (childx, childy, childx, y + 5),
                '\t<polyline style="stroke:black; stroke-width:1; fill:none;"'
                ' points="%g,%g %g,%g" />' % (childx, childy, childx, y),
            ]

        # write nodes with coordinates
        for n, (row, column) in self.coords.items():
            node = self.nodes[n]
            x = column * hscale + hstart
            y = row * vscale + vstart
            if n in self.highlight:
                color = nodecolor if isinstance(node, Tree) else leafcolor
                if isinstance(node, Tree) and node.label().startswith("-"):
                    color = funccolor
            else:
                color = "black"
            result += [
                '\t<text style="text-anchor: middle; fill: %s; '
                'font-size: %dpx;" x="%g" y="%g">%s</text>'
                % (
                    color,
                    fontsize,
                    x,
                    y,
                    escape(
                        node.label() if isinstance(node, Tree) else node, quote=False
                    ),
                )
            ]

        result += ["</svg>"]
        return "\n".join(result)


def test():
    """Do some tree drawing tests."""

    def print_tree(n, tree, sentence=None, ansi=True, **xargs):
        print()
        print('{}: "{}"'.format(n, " ".join(sentence or tree.leaves())))
        print(tree)
        print()
        drawtree = TreePrettyPrinter(tree, sentence)
        try:
            print(drawtree.text(unicodelines=ansi, ansi=ansi, **xargs))
        except (UnicodeDecodeError, UnicodeEncodeError):
            print(drawtree.text(unicodelines=False, ansi=False, **xargs))

    from nltk.corpus import treebank

    for n in [0, 1440, 1591, 2771, 2170]:
        tree = treebank.parsed_sents()[n]
        print_tree(n, tree, nodedist=2, maxwidth=8)
    print()
    print("ASCII version:")
    print(TreePrettyPrinter(tree).text(nodedist=2))

    tree = Tree.fromstring(
        "(top (punct 8) (smain (noun 0) (verb 1) (inf (verb 5) (inf (verb 6) "
        "(conj (inf (pp (prep 2) (np (det 3) (noun 4))) (verb 7)) (inf (verb 9)) "
        "(vg 10) (inf (verb 11)))))) (punct 12))",
        read_leaf=int,
    )
    sentence = (
        "Ze had met haar moeder kunnen gaan winkelen ,"
        " zwemmen of terrassen .".split()
    )
    print_tree("Discontinuous tree", tree, sentence, nodedist=2)


__all__ = ["TreePrettyPrinter"]

if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\platformdirs\__init__.py ===
"""
Utilities for determining application-specific dirs.

See <https://github.com/platformdirs/platformdirs> for details and usage.

"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC
from .version import __version__
from .version import __version_tuple__ as __version_info__

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal


def _set_platform_dir_class() -> type[PlatformDirsABC]:
    if sys.platform == "win32":
        from platformdirs.windows import Windows as Result  # noqa: PLC0415
    elif sys.platform == "darwin":
        from platformdirs.macos import MacOS as Result  # noqa: PLC0415
    else:
        from platformdirs.unix import Unix as Result  # noqa: PLC0415

    if os.getenv("ANDROID_DATA") == "/data" and os.getenv("ANDROID_ROOT") == "/system":
        if os.getenv("SHELL") or os.getenv("PREFIX"):
            return Result

        from platformdirs.android import _android_folder  # noqa: PLC0415

        if _android_folder() is not None:
            from platformdirs.android import Android  # noqa: PLC0415

            return Android  # return to avoid redefinition of a result

    return Result


PlatformDirs = _set_platform_dir_class()  #: Currently active platform
AppDirs = PlatformDirs  #: Backwards compatibility with appdirs


def user_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_dir


def site_data_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_dir


def user_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_dir


def site_config_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config directory shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_dir


def user_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_dir


def site_cache_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_dir


def user_state_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_dir


def user_log_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_dir


def user_documents_dir() -> str:
    """:returns: documents directory tied to the user"""
    return PlatformDirs().user_documents_dir


def user_downloads_dir() -> str:
    """:returns: downloads directory tied to the user"""
    return PlatformDirs().user_downloads_dir


def user_pictures_dir() -> str:
    """:returns: pictures directory tied to the user"""
    return PlatformDirs().user_pictures_dir


def user_videos_dir() -> str:
    """:returns: videos directory tied to the user"""
    return PlatformDirs().user_videos_dir


def user_music_dir() -> str:
    """:returns: music directory tied to the user"""
    return PlatformDirs().user_music_dir


def user_desktop_dir() -> str:
    """:returns: desktop directory tied to the user"""
    return PlatformDirs().user_desktop_dir


def user_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_dir


def site_runtime_dir(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> str:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime directory shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_dir


def user_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_data_path


def site_data_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `multipath <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: data path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_data_path


def user_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_config_path


def site_config_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    multipath: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param multipath: See `roaming <platformdirs.api.PlatformDirsABC.multipath>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: config path shared by the users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        multipath=multipath,
        ensure_exists=ensure_exists,
    ).site_config_path


def site_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache directory tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_cache_path


def user_cache_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: cache path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_cache_path


def user_state_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    roaming: bool = False,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param roaming: See `roaming <platformdirs.api.PlatformDirsABC.roaming>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: state path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        roaming=roaming,
        ensure_exists=ensure_exists,
    ).user_state_path


def user_log_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `roaming <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: log path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_log_path


def user_documents_path() -> Path:
    """:returns: documents a path tied to the user"""
    return PlatformDirs().user_documents_path


def user_downloads_path() -> Path:
    """:returns: downloads path tied to the user"""
    return PlatformDirs().user_downloads_path


def user_pictures_path() -> Path:
    """:returns: pictures path tied to the user"""
    return PlatformDirs().user_pictures_path


def user_videos_path() -> Path:
    """:returns: videos path tied to the user"""
    return PlatformDirs().user_videos_path


def user_music_path() -> Path:
    """:returns: music path tied to the user"""
    return PlatformDirs().user_music_path


def user_desktop_path() -> Path:
    """:returns: desktop path tied to the user"""
    return PlatformDirs().user_desktop_path


def user_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path tied to the user
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).user_runtime_path


def site_runtime_path(
    appname: str | None = None,
    appauthor: str | None | Literal[False] = None,
    version: str | None = None,
    opinion: bool = True,  # noqa: FBT001, FBT002
    ensure_exists: bool = False,  # noqa: FBT001, FBT002
) -> Path:
    """
    :param appname: See `appname <platformdirs.api.PlatformDirsABC.appname>`.
    :param appauthor: See `appauthor <platformdirs.api.PlatformDirsABC.appauthor>`.
    :param version: See `version <platformdirs.api.PlatformDirsABC.version>`.
    :param opinion: See `opinion <platformdirs.api.PlatformDirsABC.opinion>`.
    :param ensure_exists: See `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.
    :returns: runtime path shared by users
    """
    return PlatformDirs(
        appname=appname,
        appauthor=appauthor,
        version=version,
        opinion=opinion,
        ensure_exists=ensure_exists,
    ).site_runtime_path


__all__ = [
    "AppDirs",
    "PlatformDirs",
    "PlatformDirsABC",
    "__version__",
    "__version_info__",
    "site_cache_dir",
    "site_cache_path",
    "site_config_dir",
    "site_config_path",
    "site_data_dir",
    "site_data_path",
    "site_runtime_dir",
    "site_runtime_path",
    "user_cache_dir",
    "user_cache_path",
    "user_config_dir",
    "user_config_path",
    "user_data_dir",
    "user_data_path",
    "user_desktop_dir",
    "user_desktop_path",
    "user_documents_dir",
    "user_documents_path",
    "user_downloads_dir",
    "user_downloads_path",
    "user_log_dir",
    "user_log_path",
    "user_music_dir",
    "user_music_path",
    "user_pictures_dir",
    "user_pictures_path",
    "user_runtime_dir",
    "user_runtime_path",
    "user_state_dir",
    "user_state_path",
    "user_videos_dir",
    "user_videos_path",
]

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_channel.py ===
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Union

import pytest

import trio
from trio import EndOfChannel, as_safe_channel, open_memory_channel

from ..testing import Matcher, RaisesGroup, assert_checkpoints, wait_all_tasks_blocked

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def test_channel() -> None:
    with pytest.raises(TypeError):
        open_memory_channel(1.0)
    with pytest.raises(ValueError, match=r"^max_buffer_size must be >= 0$"):
        open_memory_channel(-1)

    s, r = open_memory_channel[Union[int, str, None]](2)
    repr(s)  # smoke test
    repr(r)  # smoke test

    s.send_nowait(1)
    with assert_checkpoints():
        await s.send(2)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)

    with assert_checkpoints():
        assert await r.receive() == 1
    assert r.receive_nowait() == 2
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()

    s.send_nowait("last")
    await s.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await s.send("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.clone()
    await s.aclose()

    assert r.receive_nowait() == "last"
    with pytest.raises(EndOfChannel):
        await r.receive()
    await r.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    await r.aclose()


async def test_553(autojump_clock: trio.abc.Clock) -> None:
    s, r = open_memory_channel[str](1)
    with trio.move_on_after(10) as timeout_scope:
        await r.receive()
    assert timeout_scope.cancelled_caught
    await s.send("Test for PR #553")


async def test_channel_multiple_producers() -> None:
    async def producer(send_channel: trio.MemorySendChannel[int], i: int) -> None:
        # We close our handle when we're done with it
        async with send_channel:
            for j in range(3 * i, 3 * (i + 1)):
                await send_channel.send(j)

    send_channel, receive_channel = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        # We hand out clones to all the new producers, and then close the
        # original.
        async with send_channel:
            for i in range(10):
                nursery.start_soon(producer, send_channel.clone(), i)

        got = [value async for value in receive_channel]

        got.sort()
        assert got == list(range(30))


async def test_channel_multiple_consumers() -> None:
    successful_receivers = set()
    received = []

    async def consumer(receive_channel: trio.MemoryReceiveChannel[int], i: int) -> None:
        async for value in receive_channel:
            successful_receivers.add(i)
            received.append(value)

    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel[int](1)
        async with send_channel:
            for i in range(5):
                nursery.start_soon(consumer, receive_channel, i)
            await wait_all_tasks_blocked()
            for i in range(10):
                await send_channel.send(i)

    assert successful_receivers == set(range(5))
    assert len(received) == 10
    assert set(received) == set(range(10))


async def test_close_basics() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        await s.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        await r.aclose()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[int]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    _s2, r2 = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r2)
        await wait_all_tasks_blocked()
        await r2.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r2.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r2.receive()


async def test_close_sync() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        s.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[None]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()


async def test_receive_channel_clone_and_close() -> None:
    s, r = open_memory_channel[None](10)

    r2 = r.clone()
    r3 = r.clone()

    s.send_nowait(None)
    await r.aclose()
    with r2:
        pass

    with pytest.raises(trio.ClosedResourceError):
        r.clone()

    with pytest.raises(trio.ClosedResourceError):
        r2.clone()

    # Can still send, r3 is still open
    s.send_nowait(None)

    await r3.aclose()

    # But now the receiver is really closed
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)


async def test_close_multiple_send_handles() -> None:
    # With multiple send handles, closing one handle only wakes senders on
    # that handle, but others can continue just fine
    s1, r = open_memory_channel[str](0)
    s2 = s1.clone()

    async def send_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await s1.send("nope")

    async def send_will_succeed() -> None:
        await s2.send("ok")

    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_will_close)
        nursery.start_soon(send_will_succeed)
        await wait_all_tasks_blocked()
        await s1.aclose()
        assert await r.receive() == "ok"


async def test_close_multiple_receive_handles() -> None:
    # With multiple receive handles, closing one handle only wakes receivers on
    # that handle, but others can continue just fine
    s, r1 = open_memory_channel[str](0)
    r2 = r1.clone()

    async def receive_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r1.receive()

    async def receive_will_succeed() -> None:
        assert await r2.receive() == "ok"

    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_will_close)
        nursery.start_soon(receive_will_succeed)
        await wait_all_tasks_blocked()
        await r1.aclose()
        await s.send("ok")


async def test_inf_capacity() -> None:
    send, receive = open_memory_channel[int](float("inf"))

    # It's accepted, and we can send all day without blocking
    with send:
        for i in range(10):
            send.send_nowait(i)

    got = [i async for i in receive]
    assert got == list(range(10))


async def test_statistics() -> None:
    s, r = open_memory_channel[None](2)

    assert s.statistics() == r.statistics()
    stats = s.statistics()
    assert stats.current_buffer_used == 0
    assert stats.max_buffer_size == 2
    assert stats.open_send_channels == 1
    assert stats.open_receive_channels == 1
    assert stats.tasks_waiting_send == 0
    assert stats.tasks_waiting_receive == 0

    s.send_nowait(None)
    assert s.statistics().current_buffer_used == 1

    s2 = s.clone()
    assert s.statistics().open_send_channels == 2
    await s.aclose()
    assert s2.statistics().open_send_channels == 1

    r2 = r.clone()
    assert s2.statistics().open_receive_channels == 2
    await r2.aclose()
    assert s2.statistics().open_receive_channels == 1

    async with trio.open_nursery() as nursery:
        s2.send_nowait(None)  # fill up the buffer
        assert s.statistics().current_buffer_used == 2
        nursery.start_soon(s2.send, None)
        nursery.start_soon(s2.send, None)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_send == 2
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_send == 0

    # empty out the buffer again
    try:
        while True:
            r.receive_nowait()
    except trio.WouldBlock:
        pass

    async with trio.open_nursery() as nursery:
        nursery.start_soon(r.receive)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_receive == 1
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_receive == 0


async def test_channel_fairness() -> None:
    # We can remove an item we just sent, and send an item back in after, if
    # no-one else is waiting.
    s, r = open_memory_channel[Union[int, None]](1)
    s.send_nowait(1)
    assert r.receive_nowait() == 1
    s.send_nowait(2)
    assert r.receive_nowait() == 2

    # But if someone else is waiting to receive, then they "own" the item we
    # send, so we can't receive it (even though we run first):

    result: int | None = None

    async def do_receive(r: trio.MemoryReceiveChannel[int | None]) -> None:
        nonlocal result
        result = await r.receive()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_receive, r)
        await wait_all_tasks_blocked()
        s.send_nowait(2)
        with pytest.raises(trio.WouldBlock):
            r.receive_nowait()
    assert result == 2

    # And the analogous situation for send: if we free up a space, we can't
    # immediately send something in it if someone is already waiting to do
    # that
    s, r = open_memory_channel[Union[int, None]](1)
    s.send_nowait(1)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(s.send, 2)
        await wait_all_tasks_blocked()
        assert r.receive_nowait() == 1
        with pytest.raises(trio.WouldBlock):
            s.send_nowait(3)
        assert (await r.receive()) == 2


async def test_unbuffered() -> None:
    s, r = open_memory_channel[int](0)
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(1)

    async def do_send(s: trio.MemorySendChannel[int], v: int) -> None:
        with assert_checkpoints():
            await s.send(v)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_send, s, 1)
        with assert_checkpoints():
            assert await r.receive() == 1
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()


async def test_as_safe_channel_exhaust() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1

    async with agen() as recv_chan:
        async for x in recv_chan:
            assert x == 1


async def test_as_safe_channel_broken_resource() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        yield 2

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1

        # close the receiving channel
        await recv_chan.aclose()

        # trying to get the next element errors
        with pytest.raises(trio.ClosedResourceError):
            await recv_chan.__anext__()

        # but we don't get an error on exit of the cm


async def test_as_safe_channel_cancelled() -> None:
    with trio.CancelScope() as cs:

        @as_safe_channel
        async def agen() -> AsyncGenerator[None]:  # pragma: no cover
            raise AssertionError(
                "cancel before consumption means generator should not be iterated"
            )
            yield  # indicate that we're an iterator

        async with agen():
            cs.cancel()


async def test_as_safe_channel_no_race() -> None:
    # this previously led to a race condition due to
    # https://github.com/python-trio/trio/issues/1559
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise ValueError("oae")

    with pytest.raises(ValueError, match=r"^oae$"):
        async with agen() as recv_chan:
            async for x in recv_chan:
                assert x == 1


async def test_as_safe_channel_buffer_size_too_small(
    autojump_clock: trio.testing.MockClock,
) -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError(
            "buffer size 0 means we shouldn't be asked for another value"
        )  # pragma: no cover

    with trio.move_on_after(5):
        async with agen() as recv_chan:
            async for x in recv_chan:  # pragma: no branch
                assert x == 1
                await trio.sleep_forever()


async def test_as_safe_channel_no_interleave() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError  # pragma: no cover

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1
        await trio.lowlevel.checkpoint()


async def test_as_safe_channel_genexit_finally() -> None:
    @as_safe_channel
    async def agen(events: list[str]) -> AsyncGenerator[int]:
        try:
            yield 1
        except BaseException as e:
            events.append(repr(e))
            raise
        finally:
            events.append("finally")
            raise ValueError("agen")

    events: list[str] = []
    with RaisesGroup(
        RaisesGroup(
            Matcher(ValueError, match="^agen$"),
            Matcher(TypeError, match="^iterator$"),
        ),
        match=r"^Encountered exception during cleanup of generator object, as well as exception in the contextmanager body - unable to unwrap.$",
    ):
        async with agen(events) as recv_chan:
            async for i in recv_chan:  # pragma: no branch
                assert i == 1
                raise TypeError("iterator")

    assert events == ["GeneratorExit()", "finally"]


async def test_as_safe_channel_nested_loop() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        for i in range(2):
            yield i

    ii = 0
    async with agen() as recv_chan1:
        async for i in recv_chan1:
            async with agen() as recv_chan:
                jj = 0
                async for j in recv_chan:
                    assert (i, j) == (ii, jj)
                    jj += 1
            ii += 1


async def test_as_safe_channel_doesnt_leak_cancellation() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        with trio.CancelScope() as cscope:
            cscope.cancel()
            yield

    with pytest.raises(AssertionError):
        async with agen() as recv_chan:
            async for _ in recv_chan:
                pass
        raise AssertionError("should be reachable")


async def test_as_safe_channel_dont_unwrap_user_exceptiongroup() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        raise NotImplementedError("not entered")
        yield  # pragma: no cover

    with RaisesGroup(Matcher(ValueError, match="bar"), match="foo"):
        async with agen() as _:
            raise ExceptionGroup("foo", [ValueError("bar")])


async def test_as_safe_channel_multiple_receiver() -> None:
    event = trio.Event()

    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        await event.wait()
        yield 0
        yield 1

    async def handle_value(
        recv_chan: trio.abc.ReceiveChannel[int],
        value: int,
        task_status: trio.TaskStatus,
    ) -> None:
        task_status.started()
        assert await recv_chan.receive() == value

    async with agen() as recv_chan:
        async with trio.open_nursery() as nursery:
            await nursery.start(handle_value, recv_chan, 0)
            await nursery.start(handle_value, recv_chan, 1)
            event.set()


async def test_as_safe_channel_multi_cancel() -> None:
    @as_safe_channel
    async def agen(events: list[str]) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            # this will give a warning of ASYNC120, although it's not technically a
            # problem of swallowing existing exceptions
            try:
                await trio.lowlevel.checkpoint()
            except trio.Cancelled:
                events.append("agen cancel")
                raise

    events: list[str] = []
    with trio.CancelScope() as cs:
        with pytest.raises(trio.Cancelled):
            async with agen(events) as recv_chan:
                async for _ in recv_chan:  # pragma: no branch
                    cs.cancel()
                    try:
                        await trio.lowlevel.checkpoint()
                    except trio.Cancelled:
                        events.append("body cancel")
                        raise
    assert events == ["body cancel", "agen cancel"]

# === NexusCore/openenv\Lib\site-packages\jedi\inference\compiled\value.py ===
"""
Imitate the parser representation.
"""
import re
from functools import partial
from inspect import Parameter
from pathlib import Path
from typing import Optional

from jedi import debug
from jedi.inference.utils import to_list
from jedi.cache import memoize_method
from jedi.inference.filters import AbstractFilter
from jedi.inference.names import AbstractNameDefinition, ValueNameMixin, \
    ParamNameInterface
from jedi.inference.base_value import Value, ValueSet, NO_VALUES
from jedi.inference.lazy_value import LazyKnownValue
from jedi.inference.compiled.access import _sentinel
from jedi.inference.cache import inference_state_function_cache
from jedi.inference.helpers import reraise_getitem_errors
from jedi.inference.signature import BuiltinSignature
from jedi.inference.context import CompiledContext, CompiledModuleContext


class CheckAttribute:
    """Raises :exc:`AttributeError` if the attribute X is not available."""
    def __init__(self, check_name=None):
        # Remove the py in front of e.g. py__call__.
        self.check_name = check_name

    def __call__(self, func):
        self.func = func
        if self.check_name is None:
            self.check_name = func.__name__[2:]
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self

        # This might raise an AttributeError. That's wanted.
        instance.access_handle.getattr_paths(self.check_name)
        return partial(self.func, instance)


class CompiledValue(Value):
    def __init__(self, inference_state, access_handle, parent_context=None):
        super().__init__(inference_state, parent_context)
        self.access_handle = access_handle

    def py__call__(self, arguments):
        return_annotation = self.access_handle.get_return_annotation()
        if return_annotation is not None:
            return create_from_access_path(
                self.inference_state,
                return_annotation
            ).execute_annotation()

        try:
            self.access_handle.getattr_paths('__call__')
        except AttributeError:
            return super().py__call__(arguments)
        else:
            if self.access_handle.is_class():
                from jedi.inference.value import CompiledInstance
                return ValueSet([
                    CompiledInstance(self.inference_state, self.parent_context, self, arguments)
                ])
            else:
                return ValueSet(self._execute_function(arguments))

    @CheckAttribute()
    def py__class__(self):
        return create_from_access_path(self.inference_state, self.access_handle.py__class__())

    @CheckAttribute()
    def py__mro__(self):
        return (self,) + tuple(
            create_from_access_path(self.inference_state, access)
            for access in self.access_handle.py__mro__accesses()
        )

    @CheckAttribute()
    def py__bases__(self):
        return tuple(
            create_from_access_path(self.inference_state, access)
            for access in self.access_handle.py__bases__()
        )

    def get_qualified_names(self):
        return self.access_handle.get_qualified_names()

    def py__bool__(self):
        return self.access_handle.py__bool__()

    def is_class(self):
        return self.access_handle.is_class()

    def is_function(self):
        return self.access_handle.is_function()

    def is_module(self):
        return self.access_handle.is_module()

    def is_compiled(self):
        return True

    def is_stub(self):
        return False

    def is_instance(self):
        return self.access_handle.is_instance()

    def py__doc__(self):
        return self.access_handle.py__doc__()

    @to_list
    def get_param_names(self):
        try:
            signature_params = self.access_handle.get_signature_params()
        except ValueError:  # Has no signature
            params_str, ret = self._parse_function_doc()
            if not params_str:
                tokens = []
            else:
                tokens = params_str.split(',')
            if self.access_handle.ismethoddescriptor():
                tokens.insert(0, 'self')
            for p in tokens:
                name, _, default = p.strip().partition('=')
                yield UnresolvableParamName(self, name, default)
        else:
            for signature_param in signature_params:
                yield SignatureParamName(self, signature_param)

    def get_signatures(self):
        _, return_string = self._parse_function_doc()
        return [BuiltinSignature(self, return_string)]

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.access_handle.get_repr())

    @memoize_method
    def _parse_function_doc(self):
        doc = self.py__doc__()
        if doc is None:
            return '', ''

        return _parse_function_doc(doc)

    @property
    def api_type(self):
        return self.access_handle.get_api_type()

    def get_filters(self, is_instance=False, origin_scope=None):
        yield self._ensure_one_filter(is_instance)

    @memoize_method
    def _ensure_one_filter(self, is_instance):
        return CompiledValueFilter(self.inference_state, self, is_instance)

    def py__simple_getitem__(self, index):
        with reraise_getitem_errors(IndexError, KeyError, TypeError):
            try:
                access = self.access_handle.py__simple_getitem__(
                    index,
                    safe=not self.inference_state.allow_unsafe_executions
                )
            except AttributeError:
                return super().py__simple_getitem__(index)
        if access is None:
            return super().py__simple_getitem__(index)

        return ValueSet([create_from_access_path(self.inference_state, access)])

    def py__getitem__(self, index_value_set, contextualized_node):
        all_access_paths = self.access_handle.py__getitem__all_values()
        if all_access_paths is None:
            # This means basically that no __getitem__ has been defined on this
            # object.
            return super().py__getitem__(index_value_set, contextualized_node)
        return ValueSet(
            create_from_access_path(self.inference_state, access)
            for access in all_access_paths
        )

    def py__iter__(self, contextualized_node=None):
        if not self.access_handle.has_iter():
            yield from super().py__iter__(contextualized_node)

        access_path_list = self.access_handle.py__iter__list()
        if access_path_list is None:
            # There is no __iter__ method on this object.
            return

        for access in access_path_list:
            yield LazyKnownValue(create_from_access_path(self.inference_state, access))

    def py__name__(self):
        return self.access_handle.py__name__()

    @property
    def name(self):
        name = self.py__name__()
        if name is None:
            name = self.access_handle.get_repr()
        return CompiledValueName(self, name)

    def _execute_function(self, params):
        from jedi.inference import docstrings
        from jedi.inference.compiled import builtin_from_name
        if self.api_type != 'function':
            return

        for name in self._parse_function_doc()[1].split():
            try:
                # TODO wtf is this? this is exactly the same as the thing
                # below. It uses getattr as well.
                self.inference_state.builtins_module.access_handle.getattr_paths(name)
            except AttributeError:
                continue
            else:
                bltn_obj = builtin_from_name(self.inference_state, name)
                yield from self.inference_state.execute(bltn_obj, params)
        yield from docstrings.infer_return_types(self)

    def get_safe_value(self, default=_sentinel):
        try:
            return self.access_handle.get_safe_value()
        except ValueError:
            if default == _sentinel:
                raise
            return default

    def execute_operation(self, other, operator):
        try:
            return ValueSet([create_from_access_path(
                self.inference_state,
                self.access_handle.execute_operation(other.access_handle, operator)
            )])
        except TypeError:
            return NO_VALUES

    def execute_annotation(self):
        if self.access_handle.get_repr() == 'None':
            # None as an annotation doesn't need to be executed.
            return ValueSet([self])

        name, args = self.access_handle.get_annotation_name_and_args()
        arguments = [
            ValueSet([create_from_access_path(self.inference_state, path)])
            for path in args
        ]
        if name == 'Union':
            return ValueSet.from_sets(arg.execute_annotation() for arg in arguments)
        elif name:
            # While with_generics only exists on very specific objects, we
            # should probably be fine, because we control all the typing
            # objects.
            return ValueSet([
                v.with_generics(arguments)
                for v in self.inference_state.typing_module.py__getattribute__(name)
            ]).execute_annotation()
        return super().execute_annotation()

    def negate(self):
        return create_from_access_path(self.inference_state, self.access_handle.negate())

    def get_metaclasses(self):
        return NO_VALUES

    def _as_context(self):
        return CompiledContext(self)

    @property
    def array_type(self):
        return self.access_handle.get_array_type()

    def get_key_values(self):
        return [
            create_from_access_path(self.inference_state, k)
            for k in self.access_handle.get_key_paths()
        ]

    def get_type_hint(self, add_class_info=True):
        if self.access_handle.get_repr() in ('None', "<class 'NoneType'>"):
            return 'None'
        return None


class CompiledModule(CompiledValue):
    file_io = None  # For modules

    def _as_context(self):
        return CompiledModuleContext(self)

    def py__path__(self):
        return self.access_handle.py__path__()

    def is_package(self):
        return self.py__path__() is not None

    @property
    def string_names(self):
        # For modules
        name = self.py__name__()
        if name is None:
            return ()
        return tuple(name.split('.'))

    def py__file__(self) -> Optional[Path]:
        return self.access_handle.py__file__()  # type: ignore[no-any-return]


class CompiledName(AbstractNameDefinition):
    def __init__(self, inference_state, parent_value, name, is_descriptor):
        self._inference_state = inference_state
        self.parent_context = parent_value.as_context()
        self._parent_value = parent_value
        self.string_name = name
        self.is_descriptor = is_descriptor

    def py__doc__(self):
        return self.infer_compiled_value().py__doc__()

    def _get_qualified_names(self):
        parent_qualified_names = self.parent_context.get_qualified_names()
        if parent_qualified_names is None:
            return None
        return parent_qualified_names + (self.string_name,)

    def get_defining_qualified_value(self):
        context = self.parent_context
        if context.is_module() or context.is_class():
            return self.parent_context.get_value()  # Might be None

        return None

    def __repr__(self):
        try:
            name = self.parent_context.name  # __name__ is not defined all the time
        except AttributeError:
            name = None
        return '<%s: (%s).%s>' % (self.__class__.__name__, name, self.string_name)

    @property
    def api_type(self):
        if self.is_descriptor:
            # In case of properties we want to avoid executions as much as
            # possible. Since the api_type can be wrong for other reasons
            # anyway, we just return instance here.
            return "instance"
        return self.infer_compiled_value().api_type

    def infer(self):
        return ValueSet([self.infer_compiled_value()])

    @memoize_method
    def infer_compiled_value(self):
        return create_from_name(self._inference_state, self._parent_value, self.string_name)


class SignatureParamName(ParamNameInterface, AbstractNameDefinition):
    def __init__(self, compiled_value, signature_param):
        self.parent_context = compiled_value.parent_context
        self._signature_param = signature_param

    @property
    def string_name(self):
        return self._signature_param.name

    def to_string(self):
        s = self._kind_string() + self.string_name
        if self._signature_param.has_annotation:
            s += ': ' + self._signature_param.annotation_string
        if self._signature_param.has_default:
            s += '=' + self._signature_param.default_string
        return s

    def get_kind(self):
        return getattr(Parameter, self._signature_param.kind_name)

    def infer(self):
        p = self._signature_param
        inference_state = self.parent_context.inference_state
        values = NO_VALUES
        if p.has_default:
            values = ValueSet([create_from_access_path(inference_state, p.default)])
        if p.has_annotation:
            annotation = create_from_access_path(inference_state, p.annotation)
            values |= annotation.execute_with_values()
        return values


class UnresolvableParamName(ParamNameInterface, AbstractNameDefinition):
    def __init__(self, compiled_value, name, default):
        self.parent_context = compiled_value.parent_context
        self.string_name = name
        self._default = default

    def get_kind(self):
        return Parameter.POSITIONAL_ONLY

    def to_string(self):
        string = self.string_name
        if self._default:
            string += '=' + self._default
        return string

    def infer(self):
        return NO_VALUES


class CompiledValueName(ValueNameMixin, AbstractNameDefinition):
    def __init__(self, value, name):
        self.string_name = name
        self._value = value
        self.parent_context = value.parent_context


class EmptyCompiledName(AbstractNameDefinition):
    """
    Accessing some names will raise an exception. To avoid not having any
    completions, just give Jedi the option to return this object. It infers to
    nothing.
    """
    def __init__(self, inference_state, name):
        self.parent_context = inference_state.builtins_module
        self.string_name = name

    def infer(self):
        return NO_VALUES


class CompiledValueFilter(AbstractFilter):
    def __init__(self, inference_state, compiled_value, is_instance=False):
        self._inference_state = inference_state
        self.compiled_value = compiled_value
        self.is_instance = is_instance

    def get(self, name):
        access_handle = self.compiled_value.access_handle
        safe = not self._inference_state.allow_unsafe_executions
        return self._get(
            name,
            lambda name: access_handle.is_allowed_getattr(name, safe=safe),
            lambda name: name in access_handle.dir(),
            check_has_attribute=True
        )

    def _get(self, name, allowed_getattr_callback, in_dir_callback, check_has_attribute=False):
        """
        To remove quite a few access calls we introduced the callback here.
        """
        has_attribute, is_descriptor, property_return_annotation = allowed_getattr_callback(
            name,
        )
        if property_return_annotation is not None:
            values = create_from_access_path(
                self._inference_state,
                property_return_annotation
            ).execute_annotation()
            if values:
                return [CompiledValueName(v, name) for v in values]

        if check_has_attribute and not has_attribute:
            return []

        if (is_descriptor or not has_attribute) \
                and not self._inference_state.allow_unsafe_executions:
            return [self._get_cached_name(name, is_empty=True)]

        if self.is_instance and not in_dir_callback(name):
            return []
        return [self._get_cached_name(name, is_descriptor=is_descriptor)]

    @memoize_method
    def _get_cached_name(self, name, is_empty=False, *, is_descriptor=False):
        if is_empty:
            return EmptyCompiledName(self._inference_state, name)
        else:
            return self._create_name(name, is_descriptor=is_descriptor)

    def values(self):
        from jedi.inference.compiled import builtin_from_name
        names = []
        needs_type_completions, dir_infos = self.compiled_value.access_handle.get_dir_infos()
        # We could use `safe=False` here as well, especially as a parameter to
        # get_dir_infos. But this would lead to a lot of property executions
        # that are probably not wanted. The drawback for this is that we
        # have a different name for `get` and `values`. For `get` we always
        # execute.
        for name in dir_infos:
            names += self._get(
                name,
                lambda name: dir_infos[name],
                lambda name: name in dir_infos,
            )

        # ``dir`` doesn't include the type names.
        if not self.is_instance and needs_type_completions:
            for filter in builtin_from_name(self._inference_state, 'type').get_filters():
                names += filter.values()
        return names

    def _create_name(self, name, is_descriptor):
        return CompiledName(
            self._inference_state,
            self.compiled_value,
            name,
            is_descriptor,
        )

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.compiled_value)


docstr_defaults = {
    'floating point number': 'float',
    'character': 'str',
    'integer': 'int',
    'dictionary': 'dict',
    'string': 'str',
}


def _parse_function_doc(doc):
    """
    Takes a function and returns the params and return value as a tuple.
    This is nothing more than a docstring parser.

    TODO docstrings like utime(path, (atime, mtime)) and a(b [, b]) -> None
    TODO docstrings like 'tuple of integers'
    """
    # parse round parentheses: def func(a, (b,c))
    try:
        count = 0
        start = doc.index('(')
        for i, s in enumerate(doc[start:]):
            if s == '(':
                count += 1
            elif s == ')':
                count -= 1
            if count == 0:
                end = start + i
                break
        param_str = doc[start + 1:end]
    except (ValueError, UnboundLocalError):
        # ValueError for doc.index
        # UnboundLocalError for undefined end in last line
        debug.dbg('no brackets found - no param')
        end = 0
        param_str = ''
    else:
        # remove square brackets, that show an optional param ( = None)
        def change_options(m):
            args = m.group(1).split(',')
            for i, a in enumerate(args):
                if a and '=' not in a:
                    args[i] += '=None'
            return ','.join(args)

        while True:
            param_str, changes = re.subn(r' ?\[([^\[\]]+)\]',
                                         change_options, param_str)
            if changes == 0:
                break
    param_str = param_str.replace('-', '_')  # see: isinstance.__doc__

    # parse return value
    r = re.search('-[>-]* ', doc[end:end + 7])
    if r is None:
        ret = ''
    else:
        index = end + r.end()
        # get result type, which can contain newlines
        pattern = re.compile(r'(,\n|[^\n-])+')
        ret_str = pattern.match(doc, index).group(0).strip()
        # New object -> object()
        ret_str = re.sub(r'[nN]ew (.*)', r'\1()', ret_str)

        ret = docstr_defaults.get(ret_str, ret_str)

    return param_str, ret


def create_from_name(inference_state, compiled_value, name):
    access_paths = compiled_value.access_handle.getattr_paths(name, default=None)

    value = None
    for access_path in access_paths:
        value = create_cached_compiled_value(
            inference_state,
            access_path,
            parent_context=None if value is None else value.as_context(),
        )
    return value


def _normalize_create_args(func):
    """The cache doesn't care about keyword vs. normal args."""
    def wrapper(inference_state, obj, parent_context=None):
        return func(inference_state, obj, parent_context)
    return wrapper


def create_from_access_path(inference_state, access_path):
    value = None
    for name, access in access_path.accesses:
        value = create_cached_compiled_value(
            inference_state,
            access,
            parent_context=None if value is None else value.as_context()
        )
    return value


@_normalize_create_args
@inference_state_function_cache()
def create_cached_compiled_value(inference_state, access_handle, parent_context):
    assert not isinstance(parent_context, CompiledValue)
    if parent_context is None:
        cls = CompiledModule
    else:
        cls = CompiledValue
    return cls(inference_state, access_handle, parent_context)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_upload_large_folder.py ===
# coding=utf-8
# Copyright 2024-present, the HuggingFace Inc. team.
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
import enum
import logging
import os
import queue
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, List, Optional, Tuple, Union
from urllib.parse import quote

from . import constants
from ._commit_api import CommitOperationAdd, UploadInfo, _fetch_upload_modes
from ._local_folder import LocalUploadFileMetadata, LocalUploadFilePaths, get_local_upload_paths, read_upload_metadata
from .constants import DEFAULT_REVISION, REPO_TYPES
from .utils import DEFAULT_IGNORE_PATTERNS, filter_repo_objects, tqdm
from .utils._cache_manager import _format_size
from .utils.sha import sha_fileobj


if TYPE_CHECKING:
    from .hf_api import HfApi

logger = logging.getLogger(__name__)

WAITING_TIME_IF_NO_TASKS = 10  # seconds
MAX_NB_FILES_FETCH_UPLOAD_MODE = 100
COMMIT_SIZE_SCALE: List[int] = [20, 50, 75, 100, 125, 200, 250, 400, 600, 1000]


def upload_large_folder_internal(
    api: "HfApi",
    repo_id: str,
    folder_path: Union[str, Path],
    *,
    repo_type: str,  # Repo type is required!
    revision: Optional[str] = None,
    private: Optional[bool] = None,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    num_workers: Optional[int] = None,
    print_report: bool = True,
    print_report_every: int = 60,
):
    """Upload a large folder to the Hub in the most resilient way possible.

    See [`HfApi.upload_large_folder`] for the full documentation.
    """
    # 1. Check args and setup
    if repo_type is None:
        raise ValueError(
            "For large uploads, `repo_type` is explicitly required. Please set it to `model`, `dataset` or `space`."
            " If you are using the CLI, pass it as `--repo-type=model`."
        )
    if repo_type not in REPO_TYPES:
        raise ValueError(f"Invalid repo type, must be one of {REPO_TYPES}")
    if revision is None:
        revision = DEFAULT_REVISION

    folder_path = Path(folder_path).expanduser().resolve()
    if not folder_path.is_dir():
        raise ValueError(f"Provided path: '{folder_path}' is not a directory")

    if ignore_patterns is None:
        ignore_patterns = []
    elif isinstance(ignore_patterns, str):
        ignore_patterns = [ignore_patterns]
    ignore_patterns += DEFAULT_IGNORE_PATTERNS

    if num_workers is None:
        nb_cores = os.cpu_count() or 1
        num_workers = max(nb_cores - 2, 2)  # Use all but 2 cores, or at least 2 cores

    # 2. Create repo if missing
    repo_url = api.create_repo(repo_id=repo_id, repo_type=repo_type, private=private, exist_ok=True)
    logger.info(f"Repo created: {repo_url}")
    repo_id = repo_url.repo_id

    # 3. List files to upload
    filtered_paths_list = filter_repo_objects(
        (path.relative_to(folder_path).as_posix() for path in folder_path.glob("**/*") if path.is_file()),
        allow_patterns=allow_patterns,
        ignore_patterns=ignore_patterns,
    )
    paths_list = [get_local_upload_paths(folder_path, relpath) for relpath in filtered_paths_list]
    logger.info(f"Found {len(paths_list)} candidate files to upload")

    # Read metadata for each file
    items = [
        (paths, read_upload_metadata(folder_path, paths.path_in_repo))
        for paths in tqdm(paths_list, desc="Recovering from metadata files")
    ]

    # 4. Start workers
    status = LargeUploadStatus(items)
    threads = [
        threading.Thread(
            target=_worker_job,
            kwargs={
                "status": status,
                "api": api,
                "repo_id": repo_id,
                "repo_type": repo_type,
                "revision": revision,
            },
        )
        for _ in range(num_workers)
    ]

    for thread in threads:
        thread.start()

    # 5. Print regular reports
    if print_report:
        print("\n\n" + status.current_report())
    last_report_ts = time.time()
    while True:
        time.sleep(1)
        if time.time() - last_report_ts >= print_report_every:
            if print_report:
                _print_overwrite(status.current_report())
            last_report_ts = time.time()
        if status.is_done():
            logging.info("Is done: exiting main loop")
            break

    for thread in threads:
        thread.join()

    logger.info(status.current_report())
    logging.info("Upload is complete!")


####################
# Logic to manage workers and synchronize tasks
####################


class WorkerJob(enum.Enum):
    SHA256 = enum.auto()
    GET_UPLOAD_MODE = enum.auto()
    PREUPLOAD_LFS = enum.auto()
    COMMIT = enum.auto()
    WAIT = enum.auto()  # if no tasks are available but we don't want to exit


JOB_ITEM_T = Tuple[LocalUploadFilePaths, LocalUploadFileMetadata]


class LargeUploadStatus:
    """Contains information, queues and tasks for a large upload process."""

    def __init__(self, items: List[JOB_ITEM_T]):
        self.items = items
        self.queue_sha256: "queue.Queue[JOB_ITEM_T]" = queue.Queue()
        self.queue_get_upload_mode: "queue.Queue[JOB_ITEM_T]" = queue.Queue()
        self.queue_preupload_lfs: "queue.Queue[JOB_ITEM_T]" = queue.Queue()
        self.queue_commit: "queue.Queue[JOB_ITEM_T]" = queue.Queue()
        self.lock = Lock()

        self.nb_workers_sha256: int = 0
        self.nb_workers_get_upload_mode: int = 0
        self.nb_workers_preupload_lfs: int = 0
        self.nb_workers_commit: int = 0
        self.nb_workers_waiting: int = 0
        self.last_commit_attempt: Optional[float] = None

        self._started_at = datetime.now()
        self._chunk_idx: int = 1
        self._chunk_lock: Lock = Lock()

        # Setup queues
        for item in self.items:
            paths, metadata = item
            if metadata.sha256 is None:
                self.queue_sha256.put(item)
            elif metadata.upload_mode is None:
                self.queue_get_upload_mode.put(item)
            elif metadata.upload_mode == "lfs" and not metadata.is_uploaded:
                self.queue_preupload_lfs.put(item)
            elif not metadata.is_committed:
                self.queue_commit.put(item)
            else:
                logger.debug(f"Skipping file {paths.path_in_repo} (already uploaded and committed)")

    def target_chunk(self) -> int:
        with self._chunk_lock:
            return COMMIT_SIZE_SCALE[self._chunk_idx]

    def update_chunk(self, success: bool, nb_items: int, duration: float) -> None:
        with self._chunk_lock:
            if not success:
                logger.warning(f"Failed to commit {nb_items} files at once. Will retry with less files in next batch.")
                self._chunk_idx -= 1
            elif nb_items >= COMMIT_SIZE_SCALE[self._chunk_idx] and duration < 40:
                logger.info(f"Successfully committed {nb_items} at once. Increasing the limit for next batch.")
                self._chunk_idx += 1

            self._chunk_idx = max(0, min(self._chunk_idx, len(COMMIT_SIZE_SCALE) - 1))

    def current_report(self) -> str:
        """Generate a report of the current status of the large upload."""
        nb_hashed = 0
        size_hashed = 0
        nb_preuploaded = 0
        nb_lfs = 0
        nb_lfs_unsure = 0
        size_preuploaded = 0
        nb_committed = 0
        size_committed = 0
        total_size = 0
        ignored_files = 0
        total_files = 0

        with self.lock:
            for _, metadata in self.items:
                if metadata.should_ignore:
                    ignored_files += 1
                    continue
                total_size += metadata.size
                total_files += 1
                if metadata.sha256 is not None:
                    nb_hashed += 1
                    size_hashed += metadata.size
                if metadata.upload_mode == "lfs":
                    nb_lfs += 1
                if metadata.upload_mode is None:
                    nb_lfs_unsure += 1
                if metadata.is_uploaded:
                    nb_preuploaded += 1
                    size_preuploaded += metadata.size
                if metadata.is_committed:
                    nb_committed += 1
                    size_committed += metadata.size
            total_size_str = _format_size(total_size)

            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            elapsed = now - self._started_at
            elapsed_str = str(elapsed).split(".")[0]  # remove milliseconds

            message = "\n" + "-" * 10
            message += f" {now_str} ({elapsed_str}) "
            message += "-" * 10 + "\n"

            message += "Files:   "
            message += f"hashed {nb_hashed}/{total_files} ({_format_size(size_hashed)}/{total_size_str}) | "
            message += f"pre-uploaded: {nb_preuploaded}/{nb_lfs} ({_format_size(size_preuploaded)}/{total_size_str})"
            if nb_lfs_unsure > 0:
                message += f" (+{nb_lfs_unsure} unsure)"
            message += f" | committed: {nb_committed}/{total_files} ({_format_size(size_committed)}/{total_size_str})"
            message += f" | ignored: {ignored_files}\n"

            message += "Workers: "
            message += f"hashing: {self.nb_workers_sha256} | "
            message += f"get upload mode: {self.nb_workers_get_upload_mode} | "
            message += f"pre-uploading: {self.nb_workers_preupload_lfs} | "
            message += f"committing: {self.nb_workers_commit} | "
            message += f"waiting: {self.nb_workers_waiting}\n"
            message += "-" * 51

            return message

    def is_done(self) -> bool:
        with self.lock:
            return all(metadata.is_committed or metadata.should_ignore for _, metadata in self.items)


def _worker_job(
    status: LargeUploadStatus,
    api: "HfApi",
    repo_id: str,
    repo_type: str,
    revision: str,
):
    """
    Main process for a worker. The worker will perform tasks based on the priority list until all files are uploaded
    and committed. If no tasks are available, the worker will wait for 10 seconds before checking again.

    If a task fails for any reason, the item(s) are put back in the queue for another worker to pick up.

    Read `upload_large_folder` docstring for more information on how tasks are prioritized.
    """
    while True:
        next_job: Optional[Tuple[WorkerJob, List[JOB_ITEM_T]]] = None

        # Determine next task
        next_job = _determine_next_job(status)
        if next_job is None:
            return
        job, items = next_job

        # Perform task
        if job == WorkerJob.SHA256:
            item = items[0]  # single item
            try:
                _compute_sha256(item)
                status.queue_get_upload_mode.put(item)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Failed to compute sha256: {e}")
                traceback.format_exc()
                status.queue_sha256.put(item)

            with status.lock:
                status.nb_workers_sha256 -= 1

        elif job == WorkerJob.GET_UPLOAD_MODE:
            try:
                _get_upload_mode(items, api=api, repo_id=repo_id, repo_type=repo_type, revision=revision)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Failed to get upload mode: {e}")
                traceback.format_exc()

            # Items are either:
            # - dropped (if should_ignore)
            # - put in LFS queue (if LFS)
            # - put in commit queue (if regular)
            # - or put back (if error occurred).
            for item in items:
                _, metadata = item
                if metadata.should_ignore:
                    continue
                if metadata.upload_mode == "lfs":
                    status.queue_preupload_lfs.put(item)
                elif metadata.upload_mode == "regular":
                    status.queue_commit.put(item)
                else:
                    status.queue_get_upload_mode.put(item)

            with status.lock:
                status.nb_workers_get_upload_mode -= 1

        elif job == WorkerJob.PREUPLOAD_LFS:
            item = items[0]  # single item
            try:
                _preupload_lfs(item, api=api, repo_id=repo_id, repo_type=repo_type, revision=revision)
                status.queue_commit.put(item)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Failed to preupload LFS: {e}")
                traceback.format_exc()
                status.queue_preupload_lfs.put(item)

            with status.lock:
                status.nb_workers_preupload_lfs -= 1

        elif job == WorkerJob.COMMIT:
            start_ts = time.time()
            success = True
            try:
                _commit(items, api=api, repo_id=repo_id, repo_type=repo_type, revision=revision)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Failed to commit: {e}")
                traceback.format_exc()
                for item in items:
                    status.queue_commit.put(item)
                success = False
            duration = time.time() - start_ts
            status.update_chunk(success, len(items), duration)
            with status.lock:
                status.last_commit_attempt = time.time()
                status.nb_workers_commit -= 1

        elif job == WorkerJob.WAIT:
            time.sleep(WAITING_TIME_IF_NO_TASKS)
            with status.lock:
                status.nb_workers_waiting -= 1


def _determine_next_job(status: LargeUploadStatus) -> Optional[Tuple[WorkerJob, List[JOB_ITEM_T]]]:
    with status.lock:
        # 1. Commit if more than 5 minutes since last commit attempt (and at least 1 file)
        if (
            status.nb_workers_commit == 0
            and status.queue_commit.qsize() > 0
            and status.last_commit_attempt is not None
            and time.time() - status.last_commit_attempt > 5 * 60
        ):
            status.nb_workers_commit += 1
            logger.debug("Job: commit (more than 5 minutes since last commit attempt)")
            return (WorkerJob.COMMIT, _get_n(status.queue_commit, status.target_chunk()))

        # 2. Commit if at least 100 files are ready to commit
        elif status.nb_workers_commit == 0 and status.queue_commit.qsize() >= 150:
            status.nb_workers_commit += 1
            logger.debug("Job: commit (>100 files ready)")
            return (WorkerJob.COMMIT, _get_n(status.queue_commit, status.target_chunk()))

        # 3. Get upload mode if at least 100 files
        elif status.queue_get_upload_mode.qsize() >= MAX_NB_FILES_FETCH_UPLOAD_MODE:
            status.nb_workers_get_upload_mode += 1
            logger.debug(f"Job: get upload mode (>{MAX_NB_FILES_FETCH_UPLOAD_MODE} files ready)")
            return (WorkerJob.GET_UPLOAD_MODE, _get_n(status.queue_get_upload_mode, MAX_NB_FILES_FETCH_UPLOAD_MODE))

        # 4. Preupload LFS file if at least 1 file and no worker is preuploading LFS
        elif status.queue_preupload_lfs.qsize() > 0 and status.nb_workers_preupload_lfs == 0:
            status.nb_workers_preupload_lfs += 1
            logger.debug("Job: preupload LFS (no other worker preuploading LFS)")
            return (WorkerJob.PREUPLOAD_LFS, _get_one(status.queue_preupload_lfs))

        # 5. Compute sha256 if at least 1 file and no worker is computing sha256
        elif status.queue_sha256.qsize() > 0 and status.nb_workers_sha256 == 0:
            status.nb_workers_sha256 += 1
            logger.debug("Job: sha256 (no other worker computing sha256)")
            return (WorkerJob.SHA256, _get_one(status.queue_sha256))

        # 6. Get upload mode if at least 1 file and no worker is getting upload mode
        elif status.queue_get_upload_mode.qsize() > 0 and status.nb_workers_get_upload_mode == 0:
            status.nb_workers_get_upload_mode += 1
            logger.debug("Job: get upload mode (no other worker getting upload mode)")
            return (WorkerJob.GET_UPLOAD_MODE, _get_n(status.queue_get_upload_mode, MAX_NB_FILES_FETCH_UPLOAD_MODE))

        # 7. Preupload LFS file if at least 1 file
        #    Skip if hf_transfer is enabled and there is already a worker preuploading LFS
        elif status.queue_preupload_lfs.qsize() > 0 and (
            status.nb_workers_preupload_lfs == 0 or not constants.HF_HUB_ENABLE_HF_TRANSFER
        ):
            status.nb_workers_preupload_lfs += 1
            logger.debug("Job: preupload LFS")
            return (WorkerJob.PREUPLOAD_LFS, _get_one(status.queue_preupload_lfs))

        # 8. Compute sha256 if at least 1 file
        elif status.queue_sha256.qsize() > 0:
            status.nb_workers_sha256 += 1
            logger.debug("Job: sha256")
            return (WorkerJob.SHA256, _get_one(status.queue_sha256))

        # 9. Get upload mode if at least 1 file
        elif status.queue_get_upload_mode.qsize() > 0:
            status.nb_workers_get_upload_mode += 1
            logger.debug("Job: get upload mode")
            return (WorkerJob.GET_UPLOAD_MODE, _get_n(status.queue_get_upload_mode, MAX_NB_FILES_FETCH_UPLOAD_MODE))

        # 10. Commit if at least 1 file and 1 min since last commit attempt
        elif (
            status.nb_workers_commit == 0
            and status.queue_commit.qsize() > 0
            and status.last_commit_attempt is not None
            and time.time() - status.last_commit_attempt > 1 * 60
        ):
            status.nb_workers_commit += 1
            logger.debug("Job: commit (1 min since last commit attempt)")
            return (WorkerJob.COMMIT, _get_n(status.queue_commit, status.target_chunk()))

        # 11. Commit if at least 1 file all other queues are empty and all workers are waiting
        #     e.g. when it's the last commit
        elif (
            status.nb_workers_commit == 0
            and status.queue_commit.qsize() > 0
            and status.queue_sha256.qsize() == 0
            and status.queue_get_upload_mode.qsize() == 0
            and status.queue_preupload_lfs.qsize() == 0
            and status.nb_workers_sha256 == 0
            and status.nb_workers_get_upload_mode == 0
            and status.nb_workers_preupload_lfs == 0
        ):
            status.nb_workers_commit += 1
            logger.debug("Job: commit")
            return (WorkerJob.COMMIT, _get_n(status.queue_commit, status.target_chunk()))

        # 12. If all queues are empty, exit
        elif all(metadata.is_committed or metadata.should_ignore for _, metadata in status.items):
            logger.info("All files have been processed! Exiting worker.")
            return None

        # 13. If no task is available, wait
        else:
            status.nb_workers_waiting += 1
            logger.debug(f"No task available, waiting... ({WAITING_TIME_IF_NO_TASKS}s)")
            return (WorkerJob.WAIT, [])


####################
# Atomic jobs (sha256, get_upload_mode, preupload_lfs, commit)
####################


def _compute_sha256(item: JOB_ITEM_T) -> None:
    """Compute sha256 of a file and save it in metadata."""
    paths, metadata = item
    if metadata.sha256 is None:
        with paths.file_path.open("rb") as f:
            metadata.sha256 = sha_fileobj(f).hex()
    metadata.save(paths)


def _get_upload_mode(items: List[JOB_ITEM_T], api: "HfApi", repo_id: str, repo_type: str, revision: str) -> None:
    """Get upload mode for each file and update metadata.

    Also receive info if the file should be ignored.
    """
    additions = [_build_hacky_operation(item) for item in items]
    _fetch_upload_modes(
        additions=additions,
        repo_type=repo_type,
        repo_id=repo_id,
        headers=api._build_hf_headers(),
        revision=quote(revision, safe=""),
        endpoint=api.endpoint,
    )
    for item, addition in zip(items, additions):
        paths, metadata = item
        metadata.upload_mode = addition._upload_mode
        metadata.should_ignore = addition._should_ignore
        metadata.remote_oid = addition._remote_oid
        metadata.save(paths)


def _preupload_lfs(item: JOB_ITEM_T, api: "HfApi", repo_id: str, repo_type: str, revision: str) -> None:
    """Preupload LFS file and update metadata."""
    paths, metadata = item
    addition = _build_hacky_operation(item)
    api.preupload_lfs_files(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        additions=[addition],
    )

    metadata.is_uploaded = True
    metadata.save(paths)


def _commit(items: List[JOB_ITEM_T], api: "HfApi", repo_id: str, repo_type: str, revision: str) -> None:
    """Commit files to the repo."""
    additions = [_build_hacky_operation(item) for item in items]
    api.create_commit(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        operations=additions,
        commit_message="Add files using upload-large-folder tool",
    )
    for paths, metadata in items:
        metadata.is_committed = True
        metadata.save(paths)


####################
# Hacks with CommitOperationAdd to bypass checks/sha256 calculation
####################


class HackyCommitOperationAdd(CommitOperationAdd):
    def __post_init__(self) -> None:
        if isinstance(self.path_or_fileobj, Path):
            self.path_or_fileobj = str(self.path_or_fileobj)


def _build_hacky_operation(item: JOB_ITEM_T) -> HackyCommitOperationAdd:
    paths, metadata = item
    operation = HackyCommitOperationAdd(path_in_repo=paths.path_in_repo, path_or_fileobj=paths.file_path)
    with paths.file_path.open("rb") as file:
        sample = file.peek(512)[:512]
    if metadata.sha256 is None:
        raise ValueError("sha256 must have been computed by now!")
    operation.upload_info = UploadInfo(sha256=bytes.fromhex(metadata.sha256), size=metadata.size, sample=sample)
    operation._upload_mode = metadata.upload_mode  # type: ignore[assignment]
    operation._should_ignore = metadata.should_ignore
    operation._remote_oid = metadata.remote_oid
    return operation


####################
# Misc helpers
####################


def _get_one(queue: "queue.Queue[JOB_ITEM_T]") -> List[JOB_ITEM_T]:
    return [queue.get()]


def _get_n(queue: "queue.Queue[JOB_ITEM_T]", n: int) -> List[JOB_ITEM_T]:
    return [queue.get() for _ in range(min(queue.qsize(), n))]


def _print_overwrite(report: str) -> None:
    """Print a report, overwriting the previous lines.

    Since tqdm in using `sys.stderr` to (re-)write progress bars, we need to use `sys.stdout`
    to print the report.

    Note: works well only if no other process is writing to `sys.stdout`!
    """
    report += "\n"
    # Get terminal width
    terminal_width = shutil.get_terminal_size().columns

    # Count number of lines that should be cleared
    nb_lines = sum(len(line) // terminal_width + 1 for line in report.splitlines())

    # Clear previous lines based on the number of lines in the report
    for _ in range(nb_lines):
        sys.stdout.write("\r\033[K")  # Clear line
        sys.stdout.write("\033[F")  # Move cursor up one line

    # Print the new report, filling remaining space with whitespace
    sys.stdout.write(report)
    sys.stdout.write(" " * (terminal_width - len(report.splitlines()[-1])))
    sys.stdout.flush()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\business.py ===
"""
    pygments.lexers.business
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for "business-oriented" languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, words, bygroups
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error, Whitespace

from pygments.lexers._openedge_builtins import OPENEDGEKEYWORDS

__all__ = ['CobolLexer', 'CobolFreeformatLexer', 'ABAPLexer', 'OpenEdgeLexer',
           'GoodDataCLLexer', 'MaqlLexer']


class CobolLexer(RegexLexer):
    """
    Lexer for OpenCOBOL code.
    """
    name = 'COBOL'
    aliases = ['cobol']
    filenames = ['*.cob', '*.COB', '*.cpy', '*.CPY']
    mimetypes = ['text/x-cobol']
    url = 'https://en.wikipedia.org/wiki/COBOL'
    version_added = '1.6'

    flags = re.IGNORECASE | re.MULTILINE

    # Data Types: by PICTURE and USAGE
    # Operators: **, *, +, -, /, <, >, <=, >=, =, <>
    # Logical (?): NOT, AND, OR

    # Reserved words:
    # http://opencobol.add1tocobol.com/#reserved-words
    # Intrinsics:
    # http://opencobol.add1tocobol.com/#does-opencobol-implement-any-intrinsic-functions

    tokens = {
        'root': [
            include('comment'),
            include('strings'),
            include('core'),
            include('nums'),
            (r'[a-z0-9]([\w\-]*[a-z0-9]+)?', Name.Variable),
            # (r'[\s]+', Text),
            (r'[ \t]+', Whitespace),
        ],
        'comment': [
            (r'(^.{6}[*/].*\n|^.{6}|\*>.*\n)', Comment),
        ],
        'core': [
            # Figurative constants
            (r'(^|(?<=[^\w\-]))(ALL\s+)?'
             r'((ZEROES)|(HIGH-VALUE|LOW-VALUE|QUOTE|SPACE|ZERO)(S)?)'
             r'\s*($|(?=[^\w\-]))',
             Name.Constant),

            # Reserved words STATEMENTS and other bolds
            (words((
                'ACCEPT', 'ADD', 'ALLOCATE', 'CALL', 'CANCEL', 'CLOSE', 'COMPUTE',
                'CONFIGURATION', 'CONTINUE', 'DATA', 'DELETE', 'DISPLAY', 'DIVIDE',
                'DIVISION', 'ELSE', 'END', 'END-ACCEPT',
                'END-ADD', 'END-CALL', 'END-COMPUTE', 'END-DELETE', 'END-DISPLAY',
                'END-DIVIDE', 'END-EVALUATE', 'END-IF', 'END-MULTIPLY', 'END-OF-PAGE',
                'END-PERFORM', 'END-READ', 'END-RETURN', 'END-REWRITE', 'END-SEARCH',
                'END-START', 'END-STRING', 'END-SUBTRACT', 'END-UNSTRING', 'END-WRITE',
                'ENVIRONMENT', 'EVALUATE', 'EXIT', 'FD', 'FILE', 'FILE-CONTROL', 'FOREVER',
                'FREE', 'GENERATE', 'GO', 'GOBACK', 'IDENTIFICATION', 'IF', 'INITIALIZE',
                'INITIATE', 'INPUT-OUTPUT', 'INSPECT', 'INVOKE', 'I-O-CONTROL', 'LINKAGE',
                'LOCAL-STORAGE', 'MERGE', 'MOVE', 'MULTIPLY', 'OPEN', 'PERFORM',
                'PROCEDURE', 'PROGRAM-ID', 'RAISE', 'READ', 'RELEASE', 'RESUME',
                'RETURN', 'REWRITE', 'SCREEN', 'SD', 'SEARCH', 'SECTION', 'SET',
                'SORT', 'START', 'STOP', 'STRING', 'SUBTRACT', 'SUPPRESS',
                'TERMINATE', 'THEN', 'UNLOCK', 'UNSTRING', 'USE', 'VALIDATE',
                'WORKING-STORAGE', 'WRITE'), prefix=r'(^|(?<=[^\w\-]))',
                suffix=r'\s*($|(?=[^\w\-]))'),
             Keyword.Reserved),

            # Reserved words
            (words((
                'ACCESS', 'ADDRESS', 'ADVANCING', 'AFTER', 'ALL',
                'ALPHABET', 'ALPHABETIC', 'ALPHABETIC-LOWER', 'ALPHABETIC-UPPER',
                'ALPHANUMERIC', 'ALPHANUMERIC-EDITED', 'ALSO', 'ALTER', 'ALTERNATE'
                'ANY', 'ARE', 'AREA', 'AREAS', 'ARGUMENT-NUMBER', 'ARGUMENT-VALUE', 'AS',
                'ASCENDING', 'ASSIGN', 'AT', 'AUTO', 'AUTO-SKIP', 'AUTOMATIC',
                'AUTOTERMINATE', 'BACKGROUND-COLOR', 'BASED', 'BEEP', 'BEFORE', 'BELL',
                'BLANK', 'BLINK', 'BLOCK', 'BOTTOM', 'BY', 'BYTE-LENGTH', 'CHAINING',
                'CHARACTER', 'CHARACTERS', 'CLASS', 'CODE', 'CODE-SET', 'COL',
                'COLLATING', 'COLS', 'COLUMN', 'COLUMNS', 'COMMA', 'COMMAND-LINE',
                'COMMIT', 'COMMON', 'CONSTANT', 'CONTAINS', 'CONTENT', 'CONTROL',
                'CONTROLS', 'CONVERTING', 'COPY', 'CORR', 'CORRESPONDING', 'COUNT', 'CRT',
                'CURRENCY', 'CURSOR', 'CYCLE', 'DATE', 'DAY', 'DAY-OF-WEEK', 'DE',
                'DEBUGGING', 'DECIMAL-POINT', 'DECLARATIVES', 'DEFAULT', 'DELIMITED',
                'DELIMITER', 'DEPENDING', 'DESCENDING', 'DETAIL', 'DISK',
                'DOWN', 'DUPLICATES', 'DYNAMIC', 'EBCDIC',
                'ENTRY', 'ENVIRONMENT-NAME', 'ENVIRONMENT-VALUE', 'EOL', 'EOP',
                'EOS', 'ERASE', 'ERROR', 'ESCAPE', 'EXCEPTION',
                'EXCLUSIVE', 'EXTEND', 'EXTERNAL', 'FILE-ID', 'FILLER', 'FINAL',
                'FIRST', 'FIXED', 'FLOAT-LONG', 'FLOAT-SHORT',
                'FOOTING', 'FOR', 'FOREGROUND-COLOR', 'FORMAT', 'FROM', 'FULL',
                'FUNCTION', 'FUNCTION-ID', 'GIVING', 'GLOBAL', 'GROUP',
                'HEADING', 'HIGHLIGHT', 'I-O', 'ID',
                'IGNORE', 'IGNORING', 'IN', 'INDEX', 'INDEXED', 'INDICATE',
                'INITIAL', 'INITIALIZED', 'INPUT', 'INTO', 'INTRINSIC', 'INVALID',
                'IS', 'JUST', 'JUSTIFIED', 'KEY', 'LABEL',
                'LAST', 'LEADING', 'LEFT', 'LENGTH', 'LIMIT', 'LIMITS', 'LINAGE',
                'LINAGE-COUNTER', 'LINE', 'LINES', 'LOCALE', 'LOCK',
                'LOWLIGHT', 'MANUAL', 'MEMORY', 'MINUS', 'MODE', 'MULTIPLE',
                'NATIONAL', 'NATIONAL-EDITED', 'NATIVE', 'NEGATIVE', 'NEXT', 'NO',
                'NULL', 'NULLS', 'NUMBER', 'NUMBERS', 'NUMERIC', 'NUMERIC-EDITED',
                'OBJECT-COMPUTER', 'OCCURS', 'OF', 'OFF', 'OMITTED', 'ON', 'ONLY',
                'OPTIONAL', 'ORDER', 'ORGANIZATION', 'OTHER', 'OUTPUT', 'OVERFLOW',
                'OVERLINE', 'PACKED-DECIMAL', 'PADDING', 'PAGE', 'PARAGRAPH',
                'PLUS', 'POINTER', 'POSITION', 'POSITIVE', 'PRESENT', 'PREVIOUS',
                'PRINTER', 'PRINTING', 'PROCEDURE-POINTER', 'PROCEDURES',
                'PROCEED', 'PROGRAM', 'PROGRAM-POINTER', 'PROMPT', 'QUOTE',
                'QUOTES', 'RANDOM', 'RD', 'RECORD', 'RECORDING', 'RECORDS', 'RECURSIVE',
                'REDEFINES', 'REEL', 'REFERENCE', 'RELATIVE', 'REMAINDER', 'REMOVAL',
                'RENAMES', 'REPLACING', 'REPORT', 'REPORTING', 'REPORTS', 'REPOSITORY',
                'REQUIRED', 'RESERVE', 'RETURNING', 'REVERSE-VIDEO', 'REWIND',
                'RIGHT', 'ROLLBACK', 'ROUNDED', 'RUN', 'SAME', 'SCROLL',
                'SECURE', 'SEGMENT-LIMIT', 'SELECT', 'SENTENCE', 'SEPARATE',
                'SEQUENCE', 'SEQUENTIAL', 'SHARING', 'SIGN', 'SIGNED', 'SIGNED-INT',
                'SIGNED-LONG', 'SIGNED-SHORT', 'SIZE', 'SORT-MERGE', 'SOURCE',
                'SOURCE-COMPUTER', 'SPECIAL-NAMES', 'STANDARD',
                'STANDARD-1', 'STANDARD-2', 'STATUS', 'SUBKEY', 'SUM',
                'SYMBOLIC', 'SYNC', 'SYNCHRONIZED', 'TALLYING', 'TAPE',
                'TEST', 'THROUGH', 'THRU', 'TIME', 'TIMES', 'TO', 'TOP', 'TRAILING',
                'TRANSFORM', 'TYPE', 'UNDERLINE', 'UNIT', 'UNSIGNED',
                'UNSIGNED-INT', 'UNSIGNED-LONG', 'UNSIGNED-SHORT', 'UNTIL', 'UP',
                'UPDATE', 'UPON', 'USAGE', 'USING', 'VALUE', 'VALUES', 'VARYING',
                'WAIT', 'WHEN', 'WITH', 'WORDS', 'YYYYDDD', 'YYYYMMDD'),
                prefix=r'(^|(?<=[^\w\-]))', suffix=r'\s*($|(?=[^\w\-]))'),
             Keyword.Pseudo),

            # inactive reserved words
            (words((
                'ACTIVE-CLASS', 'ALIGNED', 'ANYCASE', 'ARITHMETIC', 'ATTRIBUTE',
                'B-AND', 'B-NOT', 'B-OR', 'B-XOR', 'BIT', 'BOOLEAN', 'CD', 'CENTER',
                'CF', 'CH', 'CHAIN', 'CLASS-ID', 'CLASSIFICATION', 'COMMUNICATION',
                'CONDITION', 'DATA-POINTER', 'DESTINATION', 'DISABLE', 'EC', 'EGI',
                'EMI', 'ENABLE', 'END-RECEIVE', 'ENTRY-CONVENTION', 'EO', 'ESI',
                'EXCEPTION-OBJECT', 'EXPANDS', 'FACTORY', 'FLOAT-BINARY-16',
                'FLOAT-BINARY-34', 'FLOAT-BINARY-7', 'FLOAT-DECIMAL-16',
                'FLOAT-DECIMAL-34', 'FLOAT-EXTENDED', 'FORMAT', 'FUNCTION-POINTER',
                'GET', 'GROUP-USAGE', 'IMPLEMENTS', 'INFINITY', 'INHERITS',
                'INTERFACE', 'INTERFACE-ID', 'INVOKE', 'LC_ALL', 'LC_COLLATE',
                'LC_CTYPE', 'LC_MESSAGES', 'LC_MONETARY', 'LC_NUMERIC', 'LC_TIME',
                'LINE-COUNTER', 'MESSAGE', 'METHOD', 'METHOD-ID', 'NESTED', 'NONE',
                'NORMAL', 'OBJECT', 'OBJECT-REFERENCE', 'OPTIONS', 'OVERRIDE',
                'PAGE-COUNTER', 'PF', 'PH', 'PROPERTY', 'PROTOTYPE', 'PURGE',
                'QUEUE', 'RAISE', 'RAISING', 'RECEIVE', 'RELATION', 'REPLACE',
                'REPRESENTS-NOT-A-NUMBER', 'RESET', 'RESUME', 'RETRY', 'RF', 'RH',
                'SECONDS', 'SEGMENT', 'SELF', 'SEND', 'SOURCES', 'STATEMENT',
                'STEP', 'STRONG', 'SUB-QUEUE-1', 'SUB-QUEUE-2', 'SUB-QUEUE-3',
                'SUPER', 'SYMBOL', 'SYSTEM-DEFAULT', 'TABLE', 'TERMINAL', 'TEXT',
                'TYPEDEF', 'UCS-4', 'UNIVERSAL', 'USER-DEFAULT', 'UTF-16', 'UTF-8',
                'VAL-STATUS', 'VALID', 'VALIDATE', 'VALIDATE-STATUS'),
                   prefix=r'(^|(?<=[^\w\-]))', suffix=r'\s*($|(?=[^\w\-]))'),
             Error),

            # Data Types
            (r'(^|(?<=[^\w\-]))'
             r'(PIC\s+.+?(?=(\s|\.\s))|PICTURE\s+.+?(?=(\s|\.\s))|'
             r'(COMPUTATIONAL)(-[1-5X])?|(COMP)(-[1-5X])?|'
             r'BINARY-C-LONG|'
             r'BINARY-CHAR|BINARY-DOUBLE|BINARY-LONG|BINARY-SHORT|'
             r'BINARY)\s*($|(?=[^\w\-]))', Keyword.Type),

            # Operators
            (r'(\*\*|\*|\+|-|/|<=|>=|<|>|==|/=|=)', Operator),

            # (r'(::)', Keyword.Declaration),

            (r'([(),;:&%.])', Punctuation),

            # Intrinsics
            (r'(^|(?<=[^\w\-]))(ABS|ACOS|ANNUITY|ASIN|ATAN|BYTE-LENGTH|'
             r'CHAR|COMBINED-DATETIME|CONCATENATE|COS|CURRENT-DATE|'
             r'DATE-OF-INTEGER|DATE-TO-YYYYMMDD|DAY-OF-INTEGER|DAY-TO-YYYYDDD|'
             r'EXCEPTION-(?:FILE|LOCATION|STATEMENT|STATUS)|EXP10|EXP|E|'
             r'FACTORIAL|FRACTION-PART|INTEGER-OF-(?:DATE|DAY|PART)|INTEGER|'
             r'LENGTH|LOCALE-(?:DATE|TIME(?:-FROM-SECONDS)?)|LOG(?:10)?|'
             r'LOWER-CASE|MAX|MEAN|MEDIAN|MIDRANGE|MIN|MOD|NUMVAL(?:-C)?|'
             r'ORD(?:-MAX|-MIN)?|PI|PRESENT-VALUE|RANDOM|RANGE|REM|REVERSE|'
             r'SECONDS-FROM-FORMATTED-TIME|SECONDS-PAST-MIDNIGHT|SIGN|SIN|SQRT|'
             r'STANDARD-DEVIATION|STORED-CHAR-LENGTH|SUBSTITUTE(?:-CASE)?|'
             r'SUM|TAN|TEST-DATE-YYYYMMDD|TEST-DAY-YYYYDDD|TRIM|'
             r'UPPER-CASE|VARIANCE|WHEN-COMPILED|YEAR-TO-YYYY)\s*'
             r'($|(?=[^\w\-]))', Name.Function),

            # Booleans
            (r'(^|(?<=[^\w\-]))(true|false)\s*($|(?=[^\w\-]))', Name.Builtin),
            # Comparing Operators
            (r'(^|(?<=[^\w\-]))(equal|equals|ne|lt|le|gt|ge|'
             r'greater|less|than|not|and|or)\s*($|(?=[^\w\-]))', Operator.Word),
        ],

        # \"[^\"\n]*\"|\'[^\'\n]*\'
        'strings': [
            # apparently strings can be delimited by EOL if they are continued
            # in the next line
            (r'"[^"\n]*("|\n)', String.Double),
            (r"'[^'\n]*('|\n)", String.Single),
        ],

        'nums': [
            (r'\d+(\s*|\.$|$)', Number.Integer),
            (r'[+-]?\d*\.\d+(E[-+]?\d+)?', Number.Float),
            (r'[+-]?\d+\.\d*(E[-+]?\d+)?', Number.Float),
        ],
    }


class CobolFreeformatLexer(CobolLexer):
    """
    Lexer for Free format OpenCOBOL code.
    """
    name = 'COBOLFree'
    aliases = ['cobolfree']
    filenames = ['*.cbl', '*.CBL']
    mimetypes = []
    url = 'https://opencobol.add1tocobol.com'
    version_added = '1.6'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'comment': [
            (r'(\*>.*\n|^\w*\*.*$)', Comment),
        ],
    }


class ABAPLexer(RegexLexer):
    """
    Lexer for ABAP, SAP's integrated language.
    """
    name = 'ABAP'
    aliases = ['abap']
    filenames = ['*.abap', '*.ABAP']
    mimetypes = ['text/x-abap']
    url = 'https://community.sap.com/topics/abap'
    version_added = '1.1'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'common': [
            (r'\s+', Whitespace),
            (r'^\*.*$', Comment.Single),
            (r'\".*?\n', Comment.Single),
            (r'##\w+', Comment.Special),
        ],
        'variable-names': [
            (r'<\S+>', Name.Variable),
            (r'\w[\w~]*(?:(\[\])|->\*)?', Name.Variable),
        ],
        'root': [
            include('common'),
            # function calls
            (r'CALL\s+(?:BADI|CUSTOMER-FUNCTION|FUNCTION)',
             Keyword),
            (r'(CALL\s+(?:DIALOG|SCREEN|SUBSCREEN|SELECTION-SCREEN|'
             r'TRANSACTION|TRANSFORMATION))\b',
             Keyword),
            (r'(FORM|PERFORM)(\s+)(\w+)',
             bygroups(Keyword, Whitespace, Name.Function)),
            (r'(PERFORM)(\s+)(\()(\w+)(\))',
             bygroups(Keyword, Whitespace, Punctuation, Name.Variable, Punctuation)),
            (r'(MODULE)(\s+)(\S+)(\s+)(INPUT|OUTPUT)',
             bygroups(Keyword, Whitespace, Name.Function, Whitespace, Keyword)),

            # method implementation
            (r'(METHOD)(\s+)([\w~]+)',
             bygroups(Keyword, Whitespace, Name.Function)),
            # method calls
            (r'(\s+)([\w\-]+)([=\-]>)([\w\-~]+)',
             bygroups(Whitespace, Name.Variable, Operator, Name.Function)),
            # call methodnames returning style
            (r'(?<=(=|-)>)([\w\-~]+)(?=\()', Name.Function),

            # text elements
            (r'(TEXT)(-)(\d{3})',
             bygroups(Keyword, Punctuation, Number.Integer)),
            (r'(TEXT)(-)(\w{3})',
             bygroups(Keyword, Punctuation, Name.Variable)),

            # keywords with dashes in them.
            # these need to be first, because for instance the -ID part
            # of MESSAGE-ID wouldn't get highlighted if MESSAGE was
            # first in the list of keywords.
            (r'(ADD-CORRESPONDING|AUTHORITY-CHECK|'
             r'CLASS-DATA|CLASS-EVENTS|CLASS-METHODS|CLASS-POOL|'
             r'DELETE-ADJACENT|DIVIDE-CORRESPONDING|'
             r'EDITOR-CALL|ENHANCEMENT-POINT|ENHANCEMENT-SECTION|EXIT-COMMAND|'
             r'FIELD-GROUPS|FIELD-SYMBOLS|FIELD-SYMBOL|FUNCTION-POOL|'
             r'INTERFACE-POOL|INVERTED-DATE|'
             r'LOAD-OF-PROGRAM|LOG-POINT|'
             r'MESSAGE-ID|MOVE-CORRESPONDING|MULTIPLY-CORRESPONDING|'
             r'NEW-LINE|NEW-PAGE|NEW-SECTION|NO-EXTENSION|'
             r'OUTPUT-LENGTH|PRINT-CONTROL|'
             r'SELECT-OPTIONS|START-OF-SELECTION|SUBTRACT-CORRESPONDING|'
             r'SYNTAX-CHECK|SYSTEM-EXCEPTIONS|'
             r'TYPE-POOL|TYPE-POOLS|NO-DISPLAY'
             r')\b', Keyword),

            # keyword kombinations
            (r'(?<![-\>])(CREATE\s+(PUBLIC|PRIVATE|DATA|OBJECT)|'
             r'(PUBLIC|PRIVATE|PROTECTED)\s+SECTION|'
             r'(TYPE|LIKE)\s+((LINE\s+OF|REF\s+TO|'
             r'(SORTED|STANDARD|HASHED)\s+TABLE\s+OF))?|'
             r'FROM\s+(DATABASE|MEMORY)|CALL\s+METHOD|'
             r'(GROUP|ORDER) BY|HAVING|SEPARATED BY|'
             r'GET\s+(BADI|BIT|CURSOR|DATASET|LOCALE|PARAMETER|'
             r'PF-STATUS|(PROPERTY|REFERENCE)\s+OF|'
             r'RUN\s+TIME|TIME\s+(STAMP)?)?|'
             r'SET\s+(BIT|BLANK\s+LINES|COUNTRY|CURSOR|DATASET|EXTENDED\s+CHECK|'
             r'HANDLER|HOLD\s+DATA|LANGUAGE|LEFT\s+SCROLL-BOUNDARY|'
             r'LOCALE|MARGIN|PARAMETER|PF-STATUS|PROPERTY\s+OF|'
             r'RUN\s+TIME\s+(ANALYZER|CLOCK\s+RESOLUTION)|SCREEN|'
             r'TITLEBAR|UPADTE\s+TASK\s+LOCAL|USER-COMMAND)|'
             r'CONVERT\s+((INVERTED-)?DATE|TIME|TIME\s+STAMP|TEXT)|'
             r'(CLOSE|OPEN)\s+(DATASET|CURSOR)|'
             r'(TO|FROM)\s+(DATA BUFFER|INTERNAL TABLE|MEMORY ID|'
             r'DATABASE|SHARED\s+(MEMORY|BUFFER))|'
             r'DESCRIBE\s+(DISTANCE\s+BETWEEN|FIELD|LIST|TABLE)|'
             r'FREE\s(MEMORY|OBJECT)?|'
             r'PROCESS\s+(BEFORE\s+OUTPUT|AFTER\s+INPUT|'
             r'ON\s+(VALUE-REQUEST|HELP-REQUEST))|'
             r'AT\s+(LINE-SELECTION|USER-COMMAND|END\s+OF|NEW)|'
             r'AT\s+SELECTION-SCREEN(\s+(ON(\s+(BLOCK|(HELP|VALUE)-REQUEST\s+FOR|'
             r'END\s+OF|RADIOBUTTON\s+GROUP))?|OUTPUT))?|'
             r'SELECTION-SCREEN:?\s+((BEGIN|END)\s+OF\s+((TABBED\s+)?BLOCK|LINE|'
             r'SCREEN)|COMMENT|FUNCTION\s+KEY|'
             r'INCLUDE\s+BLOCKS|POSITION|PUSHBUTTON|'
             r'SKIP|ULINE)|'
             r'LEAVE\s+(LIST-PROCESSING|PROGRAM|SCREEN|'
             r'TO LIST-PROCESSING|TO TRANSACTION)'
             r'(ENDING|STARTING)\s+AT|'
             r'FORMAT\s+(COLOR|INTENSIFIED|INVERSE|HOTSPOT|INPUT|FRAMES|RESET)|'
             r'AS\s+(CHECKBOX|SUBSCREEN|WINDOW)|'
             r'WITH\s+(((NON-)?UNIQUE)?\s+KEY|FRAME)|'
             r'(BEGIN|END)\s+OF|'
             r'DELETE(\s+ADJACENT\s+DUPLICATES\sFROM)?|'
             r'COMPARING(\s+ALL\s+FIELDS)?|'
             r'(INSERT|APPEND)(\s+INITIAL\s+LINE\s+(IN)?TO|\s+LINES\s+OF)?|'
             r'IN\s+((BYTE|CHARACTER)\s+MODE|PROGRAM)|'
             r'END-OF-(DEFINITION|PAGE|SELECTION)|'
             r'WITH\s+FRAME(\s+TITLE)|'
             r'(REPLACE|FIND)\s+((FIRST|ALL)\s+OCCURRENCES?\s+OF\s+)?(SUBSTRING|REGEX)?|'
             r'MATCH\s+(LENGTH|COUNT|LINE|OFFSET)|'
             r'(RESPECTING|IGNORING)\s+CASE|'
             r'IN\s+UPDATE\s+TASK|'
             r'(SOURCE|RESULT)\s+(XML)?|'
             r'REFERENCE\s+INTO|'

             # simple kombinations
             r'AND\s+(MARK|RETURN)|CLIENT\s+SPECIFIED|CORRESPONDING\s+FIELDS\s+OF|'
             r'IF\s+FOUND|FOR\s+EVENT|INHERITING\s+FROM|LEAVE\s+TO\s+SCREEN|'
             r'LOOP\s+AT\s+(SCREEN)?|LOWER\s+CASE|MATCHCODE\s+OBJECT|MODIF\s+ID|'
             r'MODIFY\s+SCREEN|NESTING\s+LEVEL|NO\s+INTERVALS|OF\s+STRUCTURE|'
             r'RADIOBUTTON\s+GROUP|RANGE\s+OF|REF\s+TO|SUPPRESS DIALOG|'
             r'TABLE\s+OF|UPPER\s+CASE|TRANSPORTING\s+NO\s+FIELDS|'
             r'VALUE\s+CHECK|VISIBLE\s+LENGTH|HEADER\s+LINE|COMMON\s+PART)\b', Keyword),

            # single word keywords.
            (r'(^|(?<=(\s|\.)))(ABBREVIATED|ABSTRACT|ADD|ALIASES|ALIGN|ALPHA|'
             r'ASSERT|AS|ASSIGN(ING)?|AT(\s+FIRST)?|'
             r'BACK|BLOCK|BREAK-POINT|'
             r'CASE|CAST|CATCH|CHANGING|CHECK|CLASS|CLEAR|COLLECT|COLOR|COMMIT|COND|CONV|'
             r'CREATE|COMMUNICATION|COMPONENTS?|COMPUTE|CONCATENATE|CONDENSE|'
             r'CONSTANTS|CONTEXTS|CONTINUE|CONTROLS|COUNTRY|CURRENCY|'
             r'DATA|DATE|DECIMALS|DEFAULT|DEFINE|DEFINITION|DEFERRED|DEMAND|'
             r'DETAIL|DIRECTORY|DIVIDE|DO|DUMMY|'
             r'ELSE(IF)?|ENDAT|ENDCASE|ENDCATCH|ENDCLASS|ENDDO|ENDFORM|ENDFUNCTION|'
             r'ENDIF|ENDINTERFACE|ENDLOOP|ENDMETHOD|ENDMODULE|ENDSELECT|ENDTRY|ENDWHILE|'
             r'ENHANCEMENT|EVENTS|EXACT|EXCEPTIONS?|EXIT|EXPONENT|EXPORT|EXPORTING|EXTRACT|'
             r'FETCH|FIELDS?|FOR|FORM|FORMAT|FREE|FROM|FUNCTION|'
             r'HIDE|'
             r'ID|IF|IMPORT|IMPLEMENTATION|IMPORTING|IN|INCLUDE|INCLUDING|'
             r'INDEX|INFOTYPES|INITIALIZATION|INTERFACE|INTERFACES|INTO|'
             r'LANGUAGE|LEAVE|LENGTH|LINES|LOAD|LOCAL|'
             r'JOIN|'
             r'KEY|'
             r'NEW|NEXT|'
             r'MAXIMUM|MESSAGE|METHOD[S]?|MINIMUM|MODULE|MODIFIER|MODIFY|MOVE|MULTIPLY|'
             r'NODES|NUMBER|'
             r'OBLIGATORY|OBJECT|OF|OFF|ON|OTHERS|OVERLAY|'
             r'PACK|PAD|PARAMETERS|PERCENTAGE|POSITION|PROGRAM|PROVIDE|PUBLIC|PUT|PF\d\d|'
             r'RAISE|RAISING|RANGES?|READ|RECEIVE|REDEFINITION|REFRESH|REJECT|REPORT|RESERVE|'
             r'REF|RESUME|RETRY|RETURN|RETURNING|RIGHT|ROLLBACK|REPLACE|'
             r'SCROLL|SEARCH|SELECT|SHIFT|SIGN|SINGLE|SIZE|SKIP|SORT|SPLIT|STATICS|STOP|'
             r'STYLE|SUBMATCHES|SUBMIT|SUBTRACT|SUM(?!\()|SUMMARY|SUMMING|SUPPLY|SWITCH|'
             r'TABLE|TABLES|TIMESTAMP|TIMES?|TIMEZONE|TITLE|\??TO|'
             r'TOP-OF-PAGE|TRANSFER|TRANSLATE|TRY|TYPES|'
             r'ULINE|UNDER|UNPACK|UPDATE|USING|'
             r'VALUE|VALUES|VIA|VARYING|VARY|'
             r'WAIT|WHEN|WHERE|WIDTH|WHILE|WITH|WINDOW|WRITE|XSD|ZERO)\b', Keyword),

            # builtins
            (r'(abs|acos|asin|atan|'
             r'boolc|boolx|bit_set|'
             r'char_off|charlen|ceil|cmax|cmin|condense|contains|'
             r'contains_any_of|contains_any_not_of|concat_lines_of|cos|cosh|'
             r'count|count_any_of|count_any_not_of|'
             r'dbmaxlen|distance|'
             r'escape|exp|'
             r'find|find_end|find_any_of|find_any_not_of|floor|frac|from_mixed|'
             r'insert|'
             r'lines|log|log10|'
             r'match|matches|'
             r'nmax|nmin|numofchar|'
             r'repeat|replace|rescale|reverse|round|'
             r'segment|shift_left|shift_right|sign|sin|sinh|sqrt|strlen|'
             r'substring|substring_after|substring_from|substring_before|substring_to|'
             r'tan|tanh|to_upper|to_lower|to_mixed|translate|trunc|'
             r'xstrlen)(\()\b', bygroups(Name.Builtin, Punctuation)),

            (r'&[0-9]', Name),
            (r'[0-9]+', Number.Integer),

            # operators which look like variable names before
            # parsing variable names.
            (r'(?<=(\s|.))(AND|OR|EQ|NE|GT|LT|GE|LE|CO|CN|CA|NA|CS|NOT|NS|CP|NP|'
             r'BYTE-CO|BYTE-CN|BYTE-CA|BYTE-NA|BYTE-CS|BYTE-NS|'
             r'IS\s+(NOT\s+)?(INITIAL|ASSIGNED|REQUESTED|BOUND))\b', Operator.Word),

            include('variable-names'),

            # standard operators after variable names,
            # because < and > are part of field symbols.
            (r'[?*<>=\-+&]', Operator),
            (r"'(''|[^'])*'", String.Single),
            (r"`([^`])*`", String.Single),
            (r"([|}])([^{}|]*?)([|{])",
             bygroups(Punctuation, String.Single, Punctuation)),
            (r'[/;:()\[\],.]', Punctuation),
            (r'(!)(\w+)', bygroups(Operator, Name)),
        ],
    }


class OpenEdgeLexer(RegexLexer):
    """
    Lexer for OpenEdge ABL (formerly Progress) source code.
    """
    name = 'OpenEdge ABL'
    aliases = ['openedge', 'abl', 'progress']
    filenames = ['*.p', '*.cls']
    mimetypes = ['text/x-openedge', 'application/x-openedge']
    url = 'https://www.progress.com/openedge/features/abl'
    version_added = '1.5'

    types = (r'(?i)(^|(?<=[^\w\-]))(CHARACTER|CHAR|CHARA|CHARAC|CHARACT|CHARACTE|'
             r'COM-HANDLE|DATE|DATETIME|DATETIME-TZ|'
             r'DECIMAL|DEC|DECI|DECIM|DECIMA|HANDLE|'
             r'INT64|INTEGER|INT|INTE|INTEG|INTEGE|'
             r'LOGICAL|LONGCHAR|MEMPTR|RAW|RECID|ROWID)\s*($|(?=[^\w\-]))')

    keywords = words(OPENEDGEKEYWORDS,
                     prefix=r'(?i)(^|(?<=[^\w\-]))',
                     suffix=r'\s*($|(?=[^\w\-]))')

    tokens = {
        'root': [
            (r'/\*', Comment.Multiline, 'comment'),
            (r'\{', Comment.Preproc, 'preprocessor'),
            (r'\s*&.*', Comment.Preproc),
            (r'0[xX][0-9a-fA-F]+[LlUu]*', Number.Hex),
            (r'(?i)(DEFINE|DEF|DEFI|DEFIN)\b', Keyword.Declaration),
            (types, Keyword.Type),
            (keywords, Name.Builtin),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'[0-9]+', Number.Integer),
            (r'\s+', Whitespace),
            (r'[+*/=-]', Operator),
            (r'[.:()]', Punctuation),
            (r'.', Name.Variable),  # Lazy catch-all
        ],
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'preprocessor': [
            (r'[^{}]', Comment.Preproc),
            (r'\{', Comment.Preproc, '#push'),
            (r'\}', Comment.Preproc, '#pop'),
        ],
    }

    def analyse_text(text):
        """Try to identify OpenEdge ABL based on a few common constructs."""
        result = 0

        if 'END.' in text:
            result += 0.05

        if 'END PROCEDURE.' in text:
            result += 0.05

        if 'ELSE DO:' in text:
            result += 0.05

        return result


class GoodDataCLLexer(RegexLexer):
    """
    Lexer for GoodData-CL script files.
    """

    name = 'GoodData-CL'
    aliases = ['gooddata-cl']
    filenames = ['*.gdc']
    mimetypes = ['text/x-gooddata-cl']
    url = 'https://github.com/gooddata/GoodData-CL'
    version_added = '1.4'

    flags = re.IGNORECASE

    # Syntax:
    # https://github.com/gooddata/GoodData-CL/raw/master/cli/src/main/resources/com/gooddata/processor/COMMANDS.txt
    tokens = {
        'root': [
            # Comments
            (r'#.*', Comment.Single),
            # Function call
            (r'[a-z]\w*', Name.Function),
            # Argument list
            (r'\(', Punctuation, 'args-list'),
            # Punctuation
            (r';', Punctuation),
            # Space is not significant
            (r'\s+', Text)
        ],
        'args-list': [
            (r'\)', Punctuation, '#pop'),
            (r',', Punctuation),
            (r'[a-z]\w*', Name.Variable),
            (r'=', Operator),
            (r'"', String, 'string-literal'),
            (r'[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]{1,3})?', Number),
            # Space is not significant
            (r'\s', Whitespace)
        ],
        'string-literal': [
            (r'\\[tnrfbae"\\]', String.Escape),
            (r'"', String, '#pop'),
            (r'[^\\"]+', String)
        ]
    }


class MaqlLexer(RegexLexer):
    """
    Lexer for GoodData MAQL scripts.
    """

    name = 'MAQL'
    aliases = ['maql']
    filenames = ['*.maql']
    mimetypes = ['text/x-gooddata-maql', 'application/x-gooddata-maql']
    url = 'https://help.gooddata.com/doc/enterprise/en/dashboards-and-insights/maql-analytical-query-language'
    version_added = '1.4'

    flags = re.IGNORECASE
    tokens = {
        'root': [
            # IDENTITY
            (r'IDENTIFIER\b', Name.Builtin),
            # IDENTIFIER
            (r'\{[^}]+\}', Name.Variable),
            # NUMBER
            (r'[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]{1,3})?', Number),
            # STRING
            (r'"', String, 'string-literal'),
            #  RELATION
            (r'\<\>|\!\=', Operator),
            (r'\=|\>\=|\>|\<\=|\<', Operator),
            # :=
            (r'\:\=', Operator),
            # OBJECT
            (r'\[[^]]+\]', Name.Variable.Class),
            # keywords
            (words((
                'DIMENSION', 'DIMENSIONS', 'BOTTOM', 'METRIC', 'COUNT', 'OTHER',
                'FACT', 'WITH', 'TOP', 'OR', 'ATTRIBUTE', 'CREATE', 'PARENT',
                'FALSE', 'ROW', 'ROWS', 'FROM', 'ALL', 'AS', 'PF', 'COLUMN',
                'COLUMNS', 'DEFINE', 'REPORT', 'LIMIT', 'TABLE', 'LIKE', 'AND',
                'BY', 'BETWEEN', 'EXCEPT', 'SELECT', 'MATCH', 'WHERE', 'TRUE',
                'FOR', 'IN', 'WITHOUT', 'FILTER', 'ALIAS', 'WHEN', 'NOT', 'ON',
                'KEYS', 'KEY', 'FULLSET', 'PRIMARY', 'LABELS', 'LABEL',
                'VISUAL', 'TITLE', 'DESCRIPTION', 'FOLDER', 'ALTER', 'DROP',
                'ADD', 'DATASET', 'DATATYPE', 'INT', 'BIGINT', 'DOUBLE', 'DATE',
                'VARCHAR', 'DECIMAL', 'SYNCHRONIZE', 'TYPE', 'DEFAULT', 'ORDER',
                'ASC', 'DESC', 'HYPERLINK', 'INCLUDE', 'TEMPLATE', 'MODIFY'),
                suffix=r'\b'),
             Keyword),
            # FUNCNAME
            (r'[a-z]\w*\b', Name.Function),
            # Comments
            (r'#.*', Comment.Single),
            # Punctuation
            (r'[,;()]', Punctuation),
            # Space is not significant
            (r'\s+', Whitespace)
        ],
        'string-literal': [
            (r'\\[tnrfbae"\\]', String.Escape),
            (r'"', String, '#pop'),
            (r'[^\\"]+', String)
        ],
    }

# === NexusCore/openenv\Lib\site-packages\jupyter_client\multikernelmanager.py ===
"""A kernel manager for multiple kernels"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import json
import os
import socket
import typing as t
import uuid
from functools import wraps
from pathlib import Path

import zmq
from traitlets import Any, Bool, Dict, DottedObjectName, Instance, Unicode, default, observe
from traitlets.config.configurable import LoggingConfigurable
from traitlets.utils.importstring import import_item

from .connect import KernelConnectionInfo
from .kernelspec import NATIVE_KERNEL_NAME, KernelSpecManager
from .manager import KernelManager
from .utils import ensure_async, run_sync, utcnow


class DuplicateKernelError(Exception):
    pass


def kernel_method(f: t.Callable) -> t.Callable:
    """decorator for proxying MKM.method(kernel_id) to individual KMs by ID"""

    @wraps(f)
    def wrapped(
        self: t.Any, kernel_id: str, *args: t.Any, **kwargs: t.Any
    ) -> t.Callable | t.Awaitable:
        # get the kernel
        km = self.get_kernel(kernel_id)
        method = getattr(km, f.__name__)
        # call the kernel's method
        r = method(*args, **kwargs)
        # last thing, call anything defined in the actual class method
        # such as logging messages
        f(self, kernel_id, *args, **kwargs)
        # return the method result
        return r

    return wrapped


class MultiKernelManager(LoggingConfigurable):
    """A class for managing multiple kernels."""

    default_kernel_name = Unicode(
        NATIVE_KERNEL_NAME, help="The name of the default kernel to start"
    ).tag(config=True)

    kernel_spec_manager = Instance(KernelSpecManager, allow_none=True)

    kernel_manager_class = DottedObjectName(
        "jupyter_client.ioloop.IOLoopKernelManager",
        help="""The kernel manager class.  This is configurable to allow
        subclassing of the KernelManager for customized behavior.
        """,
    ).tag(config=True)

    @observe("kernel_manager_class")
    def _kernel_manager_class_changed(self, change: t.Any) -> None:
        self.kernel_manager_factory = self._create_kernel_manager_factory()

    kernel_manager_factory = Any(help="this is kernel_manager_class after import")

    @default("kernel_manager_factory")
    def _kernel_manager_factory_default(self) -> t.Callable:
        return self._create_kernel_manager_factory()

    def _create_kernel_manager_factory(self) -> t.Callable:
        kernel_manager_ctor = import_item(self.kernel_manager_class)

        def create_kernel_manager(*args: t.Any, **kwargs: t.Any) -> KernelManager:
            if self.shared_context:
                if self.context.closed:
                    # recreate context if closed
                    self.context = self._context_default()
                kwargs.setdefault("context", self.context)
            km = kernel_manager_ctor(*args, **kwargs)
            return km

        return create_kernel_manager

    shared_context = Bool(
        True,
        help="Share a single zmq.Context to talk to all my kernels",
    ).tag(config=True)

    context = Instance("zmq.Context")

    _created_context = Bool(False)

    _pending_kernels = Dict()

    @property
    def _starting_kernels(self) -> dict:
        """A shim for backwards compatibility."""
        return self._pending_kernels

    @default("context")
    def _context_default(self) -> zmq.Context:
        self._created_context = True
        return zmq.Context()

    connection_dir = Unicode("")
    external_connection_dir = Unicode(None, allow_none=True)

    _kernels = Dict()

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)
        self.kernel_id_to_connection_file: dict[str, Path] = {}

    def __del__(self) -> None:
        """Handle garbage collection.  Destroy context if applicable."""
        if self._created_context and self.context and not self.context.closed:
            if self.log:
                self.log.debug("Destroying zmq context for %s", self)
            self.context.destroy()
        try:
            super_del = super().__del__  # type:ignore[misc]
        except AttributeError:
            pass
        else:
            super_del()

    def list_kernel_ids(self) -> list[str]:
        """Return a list of the kernel ids of the active kernels."""
        if self.external_connection_dir is not None:
            external_connection_dir = Path(self.external_connection_dir)
            if external_connection_dir.is_dir():
                connection_files = [p for p in external_connection_dir.iterdir() if p.is_file()]

                # remove kernels (whose connection file has disappeared) from our list
                k = list(self.kernel_id_to_connection_file.keys())
                v = list(self.kernel_id_to_connection_file.values())
                for connection_file in list(self.kernel_id_to_connection_file.values()):
                    if connection_file not in connection_files:
                        kernel_id = k[v.index(connection_file)]
                        del self.kernel_id_to_connection_file[kernel_id]
                        del self._kernels[kernel_id]

                # add kernels (whose connection file appeared) to our list
                for connection_file in connection_files:
                    if connection_file in self.kernel_id_to_connection_file.values():
                        continue
                    try:
                        connection_info: KernelConnectionInfo = json.loads(
                            connection_file.read_text()
                        )
                    except Exception:  # noqa: S112
                        continue
                    self.log.debug("Loading connection file %s", connection_file)
                    if not ("kernel_name" in connection_info and "key" in connection_info):
                        continue
                    # it looks like a connection file
                    kernel_id = self.new_kernel_id()
                    self.kernel_id_to_connection_file[kernel_id] = connection_file
                    km = self.kernel_manager_factory(
                        parent=self,
                        log=self.log,
                        owns_kernel=False,
                    )
                    km.load_connection_info(connection_info)
                    km.last_activity = utcnow()
                    km.execution_state = "idle"
                    km.connections = 1
                    km.kernel_id = kernel_id
                    km.kernel_name = connection_info["kernel_name"]
                    km.ready.set_result(None)

                    self._kernels[kernel_id] = km

        # Create a copy so we can iterate over kernels in operations
        # that delete keys.
        return list(self._kernels.keys())

    def __len__(self) -> int:
        """Return the number of running kernels."""
        return len(self.list_kernel_ids())

    def __contains__(self, kernel_id: str) -> bool:
        return kernel_id in self._kernels

    def pre_start_kernel(
        self, kernel_name: str | None, kwargs: t.Any
    ) -> tuple[KernelManager, str, str]:
        # kwargs should be mutable, passing it as a dict argument.
        kernel_id = kwargs.pop("kernel_id", self.new_kernel_id(**kwargs))
        if kernel_id in self:
            raise DuplicateKernelError("Kernel already exists: %s" % kernel_id)

        if kernel_name is None:
            kernel_name = self.default_kernel_name
        # kernel_manager_factory is the constructor for the KernelManager
        # subclass we are using. It can be configured as any Configurable,
        # including things like its transport and ip.
        constructor_kwargs = {}
        if self.kernel_spec_manager:
            constructor_kwargs["kernel_spec_manager"] = self.kernel_spec_manager
        km = self.kernel_manager_factory(
            connection_file=os.path.join(self.connection_dir, "kernel-%s.json" % kernel_id),
            parent=self,
            log=self.log,
            kernel_name=kernel_name,
            **constructor_kwargs,
        )
        return km, kernel_name, kernel_id

    def update_env(self, *, kernel_id: str, env: t.Dict[str, str]) -> None:
        """
        Allow to update the environment of the given kernel.

        Forward the update env request to the corresponding kernel.

        .. version-added: 8.5
        """
        if kernel_id in self:
            self._kernels[kernel_id].update_env(env=env)

    async def _add_kernel_when_ready(
        self, kernel_id: str, km: KernelManager, kernel_awaitable: t.Awaitable
    ) -> None:
        try:
            await kernel_awaitable
            self._kernels[kernel_id] = km
            self._pending_kernels.pop(kernel_id, None)
        except Exception as e:
            self.log.exception(e)

    async def _remove_kernel_when_ready(
        self, kernel_id: str, kernel_awaitable: t.Awaitable
    ) -> None:
        try:
            await kernel_awaitable
            self.remove_kernel(kernel_id)
            self._pending_kernels.pop(kernel_id, None)
        except Exception as e:
            self.log.exception(e)

    def _using_pending_kernels(self) -> bool:
        """Returns a boolean; a clearer method for determining if
        this multikernelmanager is using pending kernels or not
        """
        return getattr(self, "use_pending_kernels", False)

    async def _async_start_kernel(self, *, kernel_name: str | None = None, **kwargs: t.Any) -> str:
        """Start a new kernel.

        The caller can pick a kernel_id by passing one in as a keyword arg,
        otherwise one will be generated using new_kernel_id().

        The kernel ID for the newly started kernel is returned.
        """
        km, kernel_name, kernel_id = self.pre_start_kernel(kernel_name, kwargs)
        if not isinstance(km, KernelManager):
            self.log.warning(  # type:ignore[unreachable]
                "Kernel manager class ({km_class}) is not an instance of 'KernelManager'!".format(
                    km_class=self.kernel_manager_class.__class__
                )
            )
        kwargs["kernel_id"] = kernel_id  # Make kernel_id available to manager and provisioner

        starter = ensure_async(km.start_kernel(**kwargs))
        task = asyncio.create_task(self._add_kernel_when_ready(kernel_id, km, starter))
        self._pending_kernels[kernel_id] = task
        # Handling a Pending Kernel
        if self._using_pending_kernels():
            # If using pending kernels, do not block
            # on the kernel start.
            self._kernels[kernel_id] = km
        else:
            await task
            # raise an exception if one occurred during kernel startup.
            if km.ready.exception():
                raise km.ready.exception()  # type: ignore[misc]

        return kernel_id

    start_kernel = run_sync(_async_start_kernel)

    async def _async_shutdown_kernel(
        self,
        kernel_id: str,
        now: bool | None = False,
        restart: bool | None = False,
    ) -> None:
        """Shutdown a kernel by its kernel uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to shutdown.
        now : bool
            Should the kernel be shutdown forcibly using a signal.
        restart : bool
            Will the kernel be restarted?
        """
        self.log.info("Kernel shutdown: %s", kernel_id)
        # If the kernel is still starting, wait for it to be ready.
        if kernel_id in self._pending_kernels:
            task = self._pending_kernels[kernel_id]
            try:
                await task
                km = self.get_kernel(kernel_id)
                await t.cast(asyncio.Future, km.ready)
            except asyncio.CancelledError:
                pass
            except Exception:
                self.remove_kernel(kernel_id)
                return
        km = self.get_kernel(kernel_id)
        # If a pending kernel raised an exception, remove it.
        if not km.ready.cancelled() and km.ready.exception():
            self.remove_kernel(kernel_id)
            return
        stopper = ensure_async(km.shutdown_kernel(now, restart))
        fut = asyncio.ensure_future(self._remove_kernel_when_ready(kernel_id, stopper))
        self._pending_kernels[kernel_id] = fut
        # Await the kernel if not using pending kernels.
        if not self._using_pending_kernels():
            await fut
            # raise an exception if one occurred during kernel shutdown.
            if km.ready.exception():
                raise km.ready.exception()  # type: ignore[misc]

    shutdown_kernel = run_sync(_async_shutdown_kernel)

    @kernel_method
    def request_shutdown(self, kernel_id: str, restart: bool | None = False) -> None:
        """Ask a kernel to shut down by its kernel uuid"""

    @kernel_method
    def finish_shutdown(
        self,
        kernel_id: str,
        waittime: float | None = None,
        pollinterval: float | None = 0.1,
    ) -> None:
        """Wait for a kernel to finish shutting down, and kill it if it doesn't"""
        self.log.info("Kernel shutdown: %s", kernel_id)

    @kernel_method
    def cleanup_resources(self, kernel_id: str, restart: bool = False) -> None:
        """Clean up a kernel's resources"""

    def remove_kernel(self, kernel_id: str) -> KernelManager:
        """remove a kernel from our mapping.

        Mainly so that a kernel can be removed if it is already dead,
        without having to call shutdown_kernel.

        The kernel object is returned, or `None` if not found.
        """
        return self._kernels.pop(kernel_id, None)

    async def _async_shutdown_all(self, now: bool = False) -> None:
        """Shutdown all kernels."""
        kids = self.list_kernel_ids()
        kids += list(self._pending_kernels)
        kms = list(self._kernels.values())
        futs = [self._async_shutdown_kernel(kid, now=now) for kid in set(kids)]
        await asyncio.gather(*futs)
        # If using pending kernels, the kernels will not have been fully shut down.
        if self._using_pending_kernels():
            for km in kms:
                try:
                    await km.ready
                except asyncio.CancelledError:
                    self._pending_kernels[km.kernel_id].cancel()
                except Exception:
                    # Will have been logged in _add_kernel_when_ready
                    pass

    shutdown_all = run_sync(_async_shutdown_all)

    def interrupt_kernel(self, kernel_id: str) -> None:
        """Interrupt (SIGINT) the kernel by its uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to interrupt.
        """
        kernel = self.get_kernel(kernel_id)
        if not kernel.ready.done():
            msg = "Kernel is in a pending state. Cannot interrupt."
            raise RuntimeError(msg)
        out = kernel.interrupt_kernel()
        self.log.info("Kernel interrupted: %s", kernel_id)
        return out

    @kernel_method
    def signal_kernel(self, kernel_id: str, signum: int) -> None:
        """Sends a signal to the kernel by its uuid.

        Note that since only SIGTERM is supported on Windows, this function
        is only useful on Unix systems.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to signal.
        signum : int
            Signal number to send kernel.
        """
        self.log.info("Signaled Kernel %s with %s", kernel_id, signum)

    async def _async_restart_kernel(self, kernel_id: str, now: bool = False) -> None:
        """Restart a kernel by its uuid, keeping the same ports.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel to interrupt.
        now : bool, optional
            If True, the kernel is forcefully restarted *immediately*, without
            having a chance to do any cleanup action.  Otherwise the kernel is
            given 1s to clean up before a forceful restart is issued.

            In all cases the kernel is restarted, the only difference is whether
            it is given a chance to perform a clean shutdown or not.
        """
        kernel = self.get_kernel(kernel_id)
        if self._using_pending_kernels() and not kernel.ready.done():
            msg = "Kernel is in a pending state. Cannot restart."
            raise RuntimeError(msg)
        await ensure_async(kernel.restart_kernel(now=now))
        self.log.info("Kernel restarted: %s", kernel_id)

    restart_kernel = run_sync(_async_restart_kernel)

    @kernel_method
    def is_alive(self, kernel_id: str) -> bool:  # type:ignore[empty-body]
        """Is the kernel alive.

        This calls KernelManager.is_alive() which calls Popen.poll on the
        actual kernel subprocess.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel.
        """

    def _check_kernel_id(self, kernel_id: str) -> None:
        """check that a kernel id is valid"""
        if kernel_id not in self:
            raise KeyError("Kernel with id not found: %s" % kernel_id)

    def get_kernel(self, kernel_id: str) -> KernelManager:
        """Get the single KernelManager object for a kernel by its uuid.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel.
        """
        self._check_kernel_id(kernel_id)
        return self._kernels[kernel_id]

    @kernel_method
    def add_restart_callback(
        self, kernel_id: str, callback: t.Callable, event: str = "restart"
    ) -> None:
        """add a callback for the KernelRestarter"""

    @kernel_method
    def remove_restart_callback(
        self, kernel_id: str, callback: t.Callable, event: str = "restart"
    ) -> None:
        """remove a callback for the KernelRestarter"""

    @kernel_method
    def get_connection_info(self, kernel_id: str) -> dict[str, t.Any]:  # type:ignore[empty-body]
        """Return a dictionary of connection data for a kernel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel.

        Returns
        =======
        connection_dict : dict
            A dict of the information needed to connect to a kernel.
            This includes the ip address and the integer port
            numbers of the different channels (stdin_port, iopub_port,
            shell_port, hb_port).
        """

    @kernel_method
    def connect_iopub(  # type:ignore[empty-body]
        self, kernel_id: str, identity: bytes | None = None
    ) -> socket.socket:
        """Return a zmq Socket connected to the iopub channel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel
        identity : bytes (optional)
            The zmq identity of the socket

        Returns
        =======
        stream : zmq Socket or ZMQStream
        """

    @kernel_method
    def connect_shell(  # type:ignore[empty-body]
        self, kernel_id: str, identity: bytes | None = None
    ) -> socket.socket:
        """Return a zmq Socket connected to the shell channel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel
        identity : bytes (optional)
            The zmq identity of the socket

        Returns
        =======
        stream : zmq Socket or ZMQStream
        """

    @kernel_method
    def connect_control(  # type:ignore[empty-body]
        self, kernel_id: str, identity: bytes | None = None
    ) -> socket.socket:
        """Return a zmq Socket connected to the control channel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel
        identity : bytes (optional)
            The zmq identity of the socket

        Returns
        =======
        stream : zmq Socket or ZMQStream
        """

    @kernel_method
    def connect_stdin(  # type:ignore[empty-body]
        self, kernel_id: str, identity: bytes | None = None
    ) -> socket.socket:
        """Return a zmq Socket connected to the stdin channel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel
        identity : bytes (optional)
            The zmq identity of the socket

        Returns
        =======
        stream : zmq Socket or ZMQStream
        """

    @kernel_method
    def connect_hb(  # type:ignore[empty-body]
        self, kernel_id: str, identity: bytes | None = None
    ) -> socket.socket:
        """Return a zmq Socket connected to the hb channel.

        Parameters
        ==========
        kernel_id : uuid
            The id of the kernel
        identity : bytes (optional)
            The zmq identity of the socket

        Returns
        =======
        stream : zmq Socket or ZMQStream
        """

    def new_kernel_id(self, **kwargs: t.Any) -> str:
        """
        Returns the id to associate with the kernel for this request. Subclasses may override
        this method to substitute other sources of kernel ids.
        :param kwargs:
        :return: string-ized version 4 uuid
        """
        return str(uuid.uuid4())


class AsyncMultiKernelManager(MultiKernelManager):
    kernel_manager_class = DottedObjectName(
        "jupyter_client.ioloop.AsyncIOLoopKernelManager",
        config=True,
        help="""The kernel manager class.  This is configurable to allow
        subclassing of the AsyncKernelManager for customized behavior.
        """,
    )

    use_pending_kernels = Bool(
        False,
        help="""Whether to make kernels available before the process has started.  The
        kernel has a `.ready` future which can be awaited before connecting""",
    ).tag(config=True)

    context = Instance("zmq.asyncio.Context")

    @default("context")
    def _context_default(self) -> zmq.asyncio.Context:
        self._created_context = True
        return zmq.asyncio.Context()

    start_kernel: t.Callable[..., t.Awaitable] = MultiKernelManager._async_start_kernel  # type:ignore[assignment]
    restart_kernel: t.Callable[..., t.Awaitable] = MultiKernelManager._async_restart_kernel  # type:ignore[assignment]
    shutdown_kernel: t.Callable[..., t.Awaitable] = MultiKernelManager._async_shutdown_kernel  # type:ignore[assignment]
    shutdown_all: t.Callable[..., t.Awaitable] = MultiKernelManager._async_shutdown_all  # type:ignore[assignment]