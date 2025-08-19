
# === NexusCore/openenv\Lib\site-packages\IPython\terminal\pt_inputhooks\osx.py ===
"""Inputhook for OS X

Calls NSApp / CoreFoundation APIs via ctypes.
"""

# obj-c boilerplate from appnope, used under BSD 2-clause

import ctypes
import ctypes.util
from threading import Event

objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))  # type: ignore

void_p = ctypes.c_void_p

objc.objc_getClass.restype = void_p
objc.sel_registerName.restype = void_p
objc.objc_msgSend.restype = void_p
objc.objc_msgSend.argtypes = [void_p, void_p]

msg = objc.objc_msgSend

def _utf8(s):
    """ensure utf8 bytes"""
    if not isinstance(s, bytes):
        s = s.encode('utf8')
    return s

def n(name):
    """create a selector name (for ObjC methods)"""
    return objc.sel_registerName(_utf8(name))

def C(classname):
    """get an ObjC Class by name"""
    return objc.objc_getClass(_utf8(classname))

# end obj-c boilerplate from appnope

# CoreFoundation C-API calls we will use:
CoreFoundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))  # type: ignore

CFFileDescriptorCreate = CoreFoundation.CFFileDescriptorCreate
CFFileDescriptorCreate.restype = void_p
CFFileDescriptorCreate.argtypes = [void_p, ctypes.c_int, ctypes.c_bool, void_p, void_p]

CFFileDescriptorGetNativeDescriptor = CoreFoundation.CFFileDescriptorGetNativeDescriptor
CFFileDescriptorGetNativeDescriptor.restype = ctypes.c_int
CFFileDescriptorGetNativeDescriptor.argtypes = [void_p]

CFFileDescriptorEnableCallBacks = CoreFoundation.CFFileDescriptorEnableCallBacks
CFFileDescriptorEnableCallBacks.restype = None
CFFileDescriptorEnableCallBacks.argtypes = [void_p, ctypes.c_ulong]

CFFileDescriptorCreateRunLoopSource = CoreFoundation.CFFileDescriptorCreateRunLoopSource
CFFileDescriptorCreateRunLoopSource.restype = void_p
CFFileDescriptorCreateRunLoopSource.argtypes = [void_p, void_p, void_p]

CFRunLoopGetCurrent = CoreFoundation.CFRunLoopGetCurrent
CFRunLoopGetCurrent.restype = void_p

CFRunLoopAddSource = CoreFoundation.CFRunLoopAddSource
CFRunLoopAddSource.restype = None
CFRunLoopAddSource.argtypes = [void_p, void_p, void_p]

CFRelease = CoreFoundation.CFRelease
CFRelease.restype = None
CFRelease.argtypes = [void_p]

CFFileDescriptorInvalidate = CoreFoundation.CFFileDescriptorInvalidate
CFFileDescriptorInvalidate.restype = None
CFFileDescriptorInvalidate.argtypes = [void_p]

# From CFFileDescriptor.h
kCFFileDescriptorReadCallBack = 1
kCFRunLoopCommonModes = void_p.in_dll(CoreFoundation, 'kCFRunLoopCommonModes')


def _NSApp():
    """Return the global NSApplication instance (NSApp)"""
    objc.objc_msgSend.argtypes = [void_p, void_p]
    return msg(C('NSApplication'), n('sharedApplication'))


def _wake(NSApp):
    """Wake the Application"""
    objc.objc_msgSend.argtypes = [
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
        void_p,
    ]
    event = msg(
        C("NSEvent"),
        n(
            "otherEventWithType:location:modifierFlags:"
            "timestamp:windowNumber:context:subtype:data1:data2:"
        ),
        15,  # Type
        0,  # location
        0,  # flags
        0,  # timestamp
        0,  # window
        None,  # context
        0,  # subtype
        0,  # data1
        0,  # data2
    )
    objc.objc_msgSend.argtypes = [void_p, void_p, void_p, void_p]
    msg(NSApp, n('postEvent:atStart:'), void_p(event), True)


def _input_callback(fdref, flags, info):
    """Callback to fire when there's input to be read"""
    CFFileDescriptorInvalidate(fdref)
    CFRelease(fdref)
    NSApp = _NSApp()
    objc.objc_msgSend.argtypes = [void_p, void_p, void_p]
    msg(NSApp, n('stop:'), NSApp)
    _wake(NSApp)

_c_callback_func_type = ctypes.CFUNCTYPE(None, void_p, void_p, void_p)
_c_input_callback = _c_callback_func_type(_input_callback)


def _stop_on_read(fd):
    """Register callback to stop eventloop when there's data on fd"""
    fdref = CFFileDescriptorCreate(None, fd, False, _c_input_callback, None)
    CFFileDescriptorEnableCallBacks(fdref, kCFFileDescriptorReadCallBack)
    source = CFFileDescriptorCreateRunLoopSource(None, fdref, 0)
    loop = CFRunLoopGetCurrent()
    CFRunLoopAddSource(loop, source, kCFRunLoopCommonModes)
    CFRelease(source)


def inputhook(context):
    """Inputhook for Cocoa (NSApp)"""
    NSApp = _NSApp()
    _stop_on_read(context.fileno())
    objc.objc_msgSend.argtypes = [void_p, void_p]
    msg(NSApp, n('run'))

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\common_utils.py ===
import json
from typing import List, Optional

from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    GenericStreamingChunk,
)


class CohereError(BaseLLMException):
    def __init__(self, status_code, message):
        super().__init__(status_code=status_code, message=message)


def validate_environment(
    headers: dict,
    model: str,
    messages: List[AllMessageValues],
    optional_params: dict,
    api_key: Optional[str] = None,
) -> dict:
    """
    Return headers to use for cohere chat completion request

    Cohere API Ref: https://docs.cohere.com/reference/chat
    Expected headers:
    {
        "Request-Source": "unspecified:litellm",
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "bearer $CO_API_KEY"
    }
    """
    headers.update(
        {
            "Request-Source": "unspecified:litellm",
            "accept": "application/json",
            "content-type": "application/json",
        }
    )
    if api_key:
        headers["Authorization"] = f"bearer {api_key}"
    return headers


class ModelResponseIterator:
    def __init__(
        self, streaming_response, sync_stream: bool, json_mode: Optional[bool] = False
    ):
        self.streaming_response = streaming_response
        self.response_iterator = self.streaming_response
        self.content_blocks: List = []
        self.tool_index = -1
        self.json_mode = json_mode

    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None
            provider_specific_fields = None

            index = int(chunk.get("index", 0))

            if "text" in chunk:
                text = chunk["text"]
            elif "is_finished" in chunk and chunk["is_finished"] is True:
                is_finished = chunk["is_finished"]
                finish_reason = chunk["finish_reason"]

            if "citations" in chunk:
                provider_specific_fields = {"citations": chunk["citations"]}

            returned_chunk = GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=index,
                provider_specific_fields=provider_specific_fields,
            )

            return returned_chunk

        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

    # Sync iterator
    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = self.response_iterator.__next__()
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            return self.convert_str_chunk_to_generic_chunk(chunk=chunk)
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

    def convert_str_chunk_to_generic_chunk(self, chunk: str) -> GenericStreamingChunk:
        """
        Convert a string chunk to a GenericStreamingChunk

        Note: This is used for Cohere pass through streaming logging
        """
        str_line = chunk
        if isinstance(chunk, bytes):  # Handle binary data
            str_line = chunk.decode("utf-8")  # Convert bytes to string
            index = str_line.find("data:")
            if index != -1:
                str_line = str_line[index:]

        data_json = json.loads(str_line)
        return self.chunk_parser(chunk=data_json)

    # Async iterator
    def __aiter__(self):
        self.async_response_iterator = self.streaming_response.__aiter__()
        return self

    async def __anext__(self):
        try:
            chunk = await self.async_response_iterator.__anext__()
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            return self.convert_str_chunk_to_generic_chunk(chunk=chunk)
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

# === NexusCore/openenv\Lib\site-packages\matplotlib\sphinxext\roles.py ===
"""
Custom roles for the Matplotlib documentation.

.. warning::

    These roles are considered semi-public. They are only intended to be used in
    the Matplotlib documentation.

However, it can happen that downstream packages end up pulling these roles into
their documentation, which will result in documentation build errors. The following
describes the exact mechanism and how to fix the errors.

There are two ways, Matplotlib docstrings can end up in downstream documentation.
You have to subclass a Matplotlib class and either use the ``:inherited-members:``
option in your autodoc configuration, or you have to override a method without
specifying a new docstring; the new method will inherit the original docstring and
still render in your autodoc. If the docstring contains one of the custom sphinx
roles, you'll see one of the following error messages:

.. code-block:: none

    Unknown interpreted text role "mpltype".
    Unknown interpreted text role "rc".

To fix this, you can add this module as extension to your sphinx :file:`conf.py`::

    extensions = [
        'matplotlib.sphinxext.roles',
        # Other extensions.
    ]

.. warning::

    Direct use of these roles in other packages is not officially supported. We
    reserve the right to modify or remove these roles without prior notification.
"""

from urllib.parse import urlsplit, urlunsplit

from docutils import nodes

import matplotlib
from matplotlib import rcParamsDefault


class _QueryReference(nodes.Inline, nodes.TextElement):
    """
    Wraps a reference or pending reference to add a query string.

    The query string is generated from the attributes added to this node.

    Also equivalent to a `~docutils.nodes.literal` node.
    """

    def to_query_string(self):
        """Generate query string from node attributes."""
        return '&'.join(f'{name}={value}' for name, value in self.attlist())


def _visit_query_reference_node(self, node):
    """
    Resolve *node* into query strings on its ``reference`` children.

    Then act as if this is a `~docutils.nodes.literal`.
    """
    query = node.to_query_string()
    for refnode in node.findall(nodes.reference):
        uri = urlsplit(refnode['refuri'])._replace(query=query)
        refnode['refuri'] = urlunsplit(uri)

    self.visit_literal(node)


def _depart_query_reference_node(self, node):
    """
    Act as if this is a `~docutils.nodes.literal`.
    """
    self.depart_literal(node)


def _rcparam_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Sphinx role ``:rc:`` to highlight and link ``rcParams`` entries.

    Usage: Give the desired ``rcParams`` key as parameter.

    :code:`:rc:`figure.dpi`` will render as: :rc:`figure.dpi`
    """
    # Generate a pending cross-reference so that Sphinx will ensure this link
    # isn't broken at some point in the future.
    title = f'rcParams["{text}"]'
    target = 'matplotlibrc-sample'
    ref_nodes, messages = inliner.interpreted(title, f'{title} <{target}>',
                                              'ref', lineno)

    qr = _QueryReference(rawtext, highlight=text)
    qr += ref_nodes
    node_list = [qr]

    # The default backend would be printed as "agg", but that's not correct (as
    # the default is actually determined by fallback).
    if text in rcParamsDefault and text != "backend":
        node_list.extend([
            nodes.Text(' (default: '),
            nodes.literal('', repr(rcParamsDefault[text])),
            nodes.Text(')'),
            ])

    return node_list, messages


def _mpltype_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    """
    Sphinx role ``:mpltype:`` for custom matplotlib types.

    In Matplotlib, there are a number of type-like concepts that do not have a
    direct type representation; example: color. This role allows to properly
    highlight them in the docs and link to their definition.

    Currently supported values:

    - :code:`:mpltype:`color`` will render as: :mpltype:`color`

    """
    mpltype = text
    type_to_link_target = {
        'color': 'colors_def',
    }
    if mpltype not in type_to_link_target:
        raise ValueError(f"Unknown mpltype: {mpltype!r}")

    node_list, messages = inliner.interpreted(
        mpltype, f'{mpltype} <{type_to_link_target[mpltype]}>', 'ref', lineno)
    return node_list, messages


def setup(app):
    app.add_role("rc", _rcparam_role)
    app.add_role("mpltype", _mpltype_role)
    app.add_node(
        _QueryReference,
        html=(_visit_query_reference_node, _depart_query_reference_node),
        latex=(_visit_query_reference_node, _depart_query_reference_node),
        text=(_visit_query_reference_node, _depart_query_reference_node),
    )
    return {"version": matplotlib.__version__,
            "parallel_read_safe": True, "parallel_write_safe": True}

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\legality_principle.py ===
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Christopher Hench <chris.l.hench@gmail.com>
#         Alex Estes
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

"""
The Legality Principle is a language agnostic principle maintaining that syllable
onsets and codas (the beginning and ends of syllables not including the vowel)
are only legal if they are found as word onsets or codas in the language. The English
word ''admit'' must then be syllabified as ''ad-mit'' since ''dm'' is not found
word-initially in the English language (Bartlett et al.). This principle was first proposed
in Daniel Kahn's 1976 dissertation, ''Syllable-based generalizations in English phonology''.

Kahn further argues that there is a ''strong tendency to syllabify in such a way that
initial clusters are of maximal length, consistent with the general constraints on
word-initial consonant clusters.'' Consequently, in addition to being legal onsets,
the longest legal onset is preferable---''Onset Maximization''.

The default implementation assumes an English vowel set, but the `vowels` attribute
can be set to IPA or any other alphabet's vowel set for the use-case.
Both a valid set of vowels as well as a text corpus of words in the language
are necessary to determine legal onsets and subsequently syllabify words.

The legality principle with onset maximization is a universal syllabification algorithm,
but that does not mean it performs equally across languages. Bartlett et al. (2009)
is a good benchmark for English accuracy if utilizing IPA (pg. 311).

References:

- Otto Jespersen. 1904. Lehrbuch der Phonetik.
  Leipzig, Teubner. Chapter 13, Silbe, pp. 185-203.
- Theo Vennemann, ''On the Theory of Syllabic Phonology,'' 1972, p. 11.
- Daniel Kahn, ''Syllable-based generalizations in English phonology'', (PhD diss., MIT, 1976).
- Elisabeth Selkirk. 1984. On the major class features and syllable theory.
  In Aronoff & Oehrle (eds.) Language Sound Structure: Studies in Phonology.
  Cambridge, MIT Press. pp. 107-136.
- Jeremy Goslin and Ulrich Frauenfelder. 2001. A comparison of theoretical and human syllabification. Language and Speech, 44:409–436.
- Susan Bartlett, et al. 2009. On the Syllabification of Phonemes.
  In HLT-NAACL. pp. 308-316.
- Christopher Hench. 2017. Resonances in Middle High German: New Methodologies in Prosody. UC Berkeley.
"""

from collections import Counter

from nltk.tokenize.api import TokenizerI


class LegalitySyllableTokenizer(TokenizerI):
    """
    Syllabifies words based on the Legality Principle and Onset Maximization.

        >>> from nltk.tokenize import LegalitySyllableTokenizer
        >>> from nltk import word_tokenize
        >>> from nltk.corpus import words
        >>> text = "This is a wonderful sentence."
        >>> text_words = word_tokenize(text)
        >>> LP = LegalitySyllableTokenizer(words.words())
        >>> [LP.tokenize(word) for word in text_words]
        [['This'], ['is'], ['a'], ['won', 'der', 'ful'], ['sen', 'ten', 'ce'], ['.']]
    """

    def __init__(
        self, tokenized_source_text, vowels="aeiouy", legal_frequency_threshold=0.001
    ):
        """
        :param tokenized_source_text: List of valid tokens in the language
        :type tokenized_source_text: list(str)
        :param vowels: Valid vowels in language or IPA representation
        :type vowels: str
        :param legal_frequency_threshold: Lowest frequency of all onsets to be considered a legal onset
        :type legal_frequency_threshold: float
        """
        self.legal_frequency_threshold = legal_frequency_threshold
        self.vowels = vowels
        self.legal_onsets = self.find_legal_onsets(tokenized_source_text)

    def find_legal_onsets(self, words):
        """
        Gathers all onsets and then return only those above the frequency threshold

        :param words: List of words in a language
        :type words: list(str)
        :return: Set of legal onsets
        :rtype: set(str)
        """
        onsets = [self.onset(word) for word in words]
        legal_onsets = [
            k
            for k, v in Counter(onsets).items()
            if (v / len(onsets)) > self.legal_frequency_threshold
        ]
        return set(legal_onsets)

    def onset(self, word):
        """
        Returns consonant cluster of word, i.e. all characters until the first vowel.

        :param word: Single word or token
        :type word: str
        :return: String of characters of onset
        :rtype: str
        """
        onset = ""
        for c in word.lower():
            if c in self.vowels:
                return onset
            else:
                onset += c
        return onset

    def tokenize(self, token):
        """
        Apply the Legality Principle in combination with
        Onset Maximization to return a list of syllables.

        :param token: Single word or token
        :type token: str
        :return syllable_list: Single word or token broken up into syllables.
        :rtype: list(str)
        """
        syllables = []
        syllable, current_onset = "", ""
        vowel, onset = False, False
        for char in token[::-1]:
            char_lower = char.lower()
            if not vowel:
                syllable += char
                vowel = bool(char_lower in self.vowels)
            else:
                if char_lower + current_onset[::-1] in self.legal_onsets:
                    syllable += char
                    current_onset += char_lower
                    onset = True
                elif char_lower in self.vowels and not onset:
                    syllable += char
                    current_onset += char_lower
                else:
                    syllables.append(syllable)
                    syllable = char
                    current_onset = ""
                    vowel = bool(char_lower in self.vowels)
        syllables.append(syllable)
        syllables_ordered = [syllable[::-1] for syllable in syllables][::-1]
        return syllables_ordered

# === NexusCore/openenv\Lib\site-packages\nltk\twitter\util.py ===
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Authentication utilities to accompany `twitterclient`.
"""

import os
import pprint

from twython import Twython


def credsfromfile(creds_file=None, subdir=None, verbose=False):
    """
    Convenience function for authentication
    """
    return Authenticate().load_creds(
        creds_file=creds_file, subdir=subdir, verbose=verbose
    )


class Authenticate:
    """
    Methods for authenticating with Twitter.
    """

    def __init__(self):
        self.creds_file = "credentials.txt"
        self.creds_fullpath = None

        self.oauth = {}
        try:
            self.twitter_dir = os.environ["TWITTER"]
            self.creds_subdir = self.twitter_dir
        except KeyError:
            self.twitter_dir = None
            self.creds_subdir = None

    def load_creds(self, creds_file=None, subdir=None, verbose=False):
        """
        Read OAuth credentials from a text file.

        File format for OAuth 1::

           app_key=YOUR_APP_KEY
           app_secret=YOUR_APP_SECRET
           oauth_token=OAUTH_TOKEN
           oauth_token_secret=OAUTH_TOKEN_SECRET


        File format for OAuth 2::

           app_key=YOUR_APP_KEY
           app_secret=YOUR_APP_SECRET
           access_token=ACCESS_TOKEN

        :param str file_name: File containing credentials. ``None`` (default) reads
            data from `TWITTER/'credentials.txt'`
        """
        if creds_file is not None:
            self.creds_file = creds_file

        if subdir is None:
            if self.creds_subdir is None:
                msg = (
                    "Supply a value to the 'subdir' parameter or"
                    + " set the TWITTER environment variable."
                )
                raise ValueError(msg)
        else:
            self.creds_subdir = subdir

        self.creds_fullpath = os.path.normpath(
            os.path.join(self.creds_subdir, self.creds_file)
        )

        if not os.path.isfile(self.creds_fullpath):
            raise OSError(f"Cannot find file {self.creds_fullpath}")

        with open(self.creds_fullpath) as infile:
            if verbose:
                print(f"Reading credentials file {self.creds_fullpath}")

            for line in infile:
                if "=" in line:
                    name, value = line.split("=", 1)
                    self.oauth[name.strip()] = value.strip()

        self._validate_creds_file(verbose=verbose)

        return self.oauth

    def _validate_creds_file(self, verbose=False):
        """Check validity of a credentials file."""
        oauth1 = False
        oauth1_keys = ["app_key", "app_secret", "oauth_token", "oauth_token_secret"]
        oauth2 = False
        oauth2_keys = ["app_key", "app_secret", "access_token"]
        if all(k in self.oauth for k in oauth1_keys):
            oauth1 = True
        elif all(k in self.oauth for k in oauth2_keys):
            oauth2 = True

        if not (oauth1 or oauth2):
            msg = f"Missing or incorrect entries in {self.creds_file}\n"
            msg += pprint.pformat(self.oauth)
            raise ValueError(msg)
        elif verbose:
            print(f'Credentials file "{self.creds_file}" looks good')


def add_access_token(creds_file=None):
    """
    For OAuth 2, retrieve an access token for an app and append it to a
    credentials file.
    """
    if creds_file is None:
        path = os.path.dirname(__file__)
        creds_file = os.path.join(path, "credentials2.txt")
    oauth2 = credsfromfile(creds_file=creds_file)
    app_key = oauth2["app_key"]
    app_secret = oauth2["app_secret"]

    twitter = Twython(app_key, app_secret, oauth_version=2)
    access_token = twitter.obtain_access_token()
    tok = f"access_token={access_token}\n"
    with open(creds_file, "a") as infile:
        print(tok, file=infile)


def guess_path(pth):
    """
    If the path is not absolute, guess that it is a subdirectory of the
    user's home directory.

    :param str pth: The pathname of the directory where files of tweets should be written
    """
    if os.path.isabs(pth):
        return pth
    else:
        return os.path.expanduser(os.path.join("~", pth))

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\hashes.py ===
import hashlib
from typing import TYPE_CHECKING, BinaryIO, Dict, Iterable, List, NoReturn, Optional

from pip._internal.exceptions import HashMismatch, HashMissing, InstallationError
from pip._internal.utils.misc import read_chunks

if TYPE_CHECKING:
    from hashlib import _Hash


# The recommended hash algo of the moment. Change this whenever the state of
# the art changes; it won't hurt backward compatibility.
FAVORITE_HASH = "sha256"


# Names of hashlib algorithms allowed by the --hash option and ``pip hash``
# Currently, those are the ones at least as collision-resistant as sha256.
STRONG_HASHES = ["sha256", "sha384", "sha512"]


class Hashes:
    """A wrapper that builds multiple hashes at once and checks them against
    known-good values

    """

    def __init__(self, hashes: Optional[Dict[str, List[str]]] = None) -> None:
        """
        :param hashes: A dict of algorithm names pointing to lists of allowed
            hex digests
        """
        allowed = {}
        if hashes is not None:
            for alg, keys in hashes.items():
                # Make sure values are always sorted (to ease equality checks)
                allowed[alg] = [k.lower() for k in sorted(keys)]
        self._allowed = allowed

    def __and__(self, other: "Hashes") -> "Hashes":
        if not isinstance(other, Hashes):
            return NotImplemented

        # If either of the Hashes object is entirely empty (i.e. no hash
        # specified at all), all hashes from the other object are allowed.
        if not other:
            return self
        if not self:
            return other

        # Otherwise only hashes that present in both objects are allowed.
        new = {}
        for alg, values in other._allowed.items():
            if alg not in self._allowed:
                continue
            new[alg] = [v for v in values if v in self._allowed[alg]]
        return Hashes(new)

    @property
    def digest_count(self) -> int:
        return sum(len(digests) for digests in self._allowed.values())

    def is_hash_allowed(self, hash_name: str, hex_digest: str) -> bool:
        """Return whether the given hex digest is allowed."""
        return hex_digest in self._allowed.get(hash_name, [])

    def check_against_chunks(self, chunks: Iterable[bytes]) -> None:
        """Check good hashes against ones built from iterable of chunks of
        data.

        Raise HashMismatch if none match.

        """
        gots = {}
        for hash_name in self._allowed.keys():
            try:
                gots[hash_name] = hashlib.new(hash_name)
            except (ValueError, TypeError):
                raise InstallationError(f"Unknown hash name: {hash_name}")

        for chunk in chunks:
            for hash in gots.values():
                hash.update(chunk)

        for hash_name, got in gots.items():
            if got.hexdigest() in self._allowed[hash_name]:
                return
        self._raise(gots)

    def _raise(self, gots: Dict[str, "_Hash"]) -> "NoReturn":
        raise HashMismatch(self._allowed, gots)

    def check_against_file(self, file: BinaryIO) -> None:
        """Check good hashes against a file-like object

        Raise HashMismatch if none match.

        """
        return self.check_against_chunks(read_chunks(file))

    def check_against_path(self, path: str) -> None:
        with open(path, "rb") as file:
            return self.check_against_file(file)

    def has_one_of(self, hashes: Dict[str, str]) -> bool:
        """Return whether any of the given hashes are allowed."""
        for hash_name, hex_digest in hashes.items():
            if self.is_hash_allowed(hash_name, hex_digest):
                return True
        return False

    def __bool__(self) -> bool:
        """Return whether I know any known-good hashes."""
        return bool(self._allowed)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hashes):
            return NotImplemented
        return self._allowed == other._allowed

    def __hash__(self) -> int:
        return hash(
            ",".join(
                sorted(
                    ":".join((alg, digest))
                    for alg, digest_list in self._allowed.items()
                    for digest in digest_list
                )
            )
        )


class MissingHashes(Hashes):
    """A workalike for Hashes used when we're missing a hash for a requirement

    It computes the actual hash of the requirement and raises a HashMissing
    exception showing it to the user.

    """

    def __init__(self) -> None:
        """Don't offer the ``hashes`` kwarg."""
        # Pass our favorite hash in to generate a "gotten hash". With the
        # empty list, it will never match, so an error will always raise.
        super().__init__(hashes={FAVORITE_HASH: []})

    def _raise(self, gots: Dict[str, "_Hash"]) -> "NoReturn":
        raise HashMissing(gots[FAVORITE_HASH].hexdigest())

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\__init__.py ===
"""
Command line layout definitions
-------------------------------

The layout of a command line interface is defined by a Container instance.
There are two main groups of classes here. Containers and controls:

- A container can contain other containers or controls, it can have multiple
  children and it decides about the dimensions.
- A control is responsible for rendering the actual content to a screen.
  A control can propose some dimensions, but it's the container who decides
  about the dimensions -- or when the control consumes more space -- which part
  of the control will be visible.


Container classes::

    - Container (Abstract base class)
       |- HSplit (Horizontal split)
       |- VSplit (Vertical split)
       |- FloatContainer (Container which can also contain menus and other floats)
       `- Window (Container which contains one actual control

Control classes::

    - UIControl (Abstract base class)
       |- FormattedTextControl (Renders formatted text, or a simple list of text fragments)
       `- BufferControl (Renders an input buffer.)


Usually, you end up wrapping every control inside a `Window` object, because
that's the only way to render it in a layout.

There are some prepared toolbars which are ready to use::

- SystemToolbar (Shows the 'system' input buffer, for entering system commands.)
- ArgToolbar (Shows the input 'arg', for repetition of input commands.)
- SearchToolbar (Shows the 'search' input buffer, for incremental search.)
- CompletionsToolbar (Shows the completions of the current buffer.)
- ValidationToolbar (Shows validation errors of the current buffer.)

And one prepared menu:

- CompletionsMenu

"""

from __future__ import annotations

from .containers import (
    AnyContainer,
    ColorColumn,
    ConditionalContainer,
    Container,
    DynamicContainer,
    Float,
    FloatContainer,
    HorizontalAlign,
    HSplit,
    ScrollOffsets,
    VerticalAlign,
    VSplit,
    Window,
    WindowAlign,
    WindowRenderInfo,
    is_container,
    to_container,
    to_window,
)
from .controls import (
    BufferControl,
    DummyControl,
    FormattedTextControl,
    SearchBufferControl,
    UIContent,
    UIControl,
)
from .dimension import (
    AnyDimension,
    D,
    Dimension,
    is_dimension,
    max_layout_dimensions,
    sum_layout_dimensions,
    to_dimension,
)
from .layout import InvalidLayoutError, Layout, walk
from .margins import (
    ConditionalMargin,
    Margin,
    NumberedMargin,
    PromptMargin,
    ScrollbarMargin,
)
from .menus import CompletionsMenu, MultiColumnCompletionsMenu
from .scrollable_pane import ScrollablePane

__all__ = [
    # Layout.
    "Layout",
    "InvalidLayoutError",
    "walk",
    # Dimensions.
    "AnyDimension",
    "Dimension",
    "D",
    "sum_layout_dimensions",
    "max_layout_dimensions",
    "to_dimension",
    "is_dimension",
    # Containers.
    "AnyContainer",
    "Container",
    "HorizontalAlign",
    "VerticalAlign",
    "HSplit",
    "VSplit",
    "FloatContainer",
    "Float",
    "WindowAlign",
    "Window",
    "WindowRenderInfo",
    "ConditionalContainer",
    "ScrollOffsets",
    "ColorColumn",
    "to_container",
    "to_window",
    "is_container",
    "DynamicContainer",
    "ScrollablePane",
    # Controls.
    "BufferControl",
    "SearchBufferControl",
    "DummyControl",
    "FormattedTextControl",
    "UIControl",
    "UIContent",
    # Margins.
    "Margin",
    "NumberedMargin",
    "ScrollbarMargin",
    "ConditionalMargin",
    "PromptMargin",
    # Menus.
    "CompletionsMenu",
    "MultiColumnCompletionsMenu",
]

# === NexusCore/openenv\Lib\site-packages\win32com\test\testStreams.py ===
import unittest

import pythoncom
import win32com.server.util
import win32com.test.util


class Persists:
    _public_methods_ = [
        "GetClassID",
        "IsDirty",
        "Load",
        "Save",
        "GetSizeMax",
        "InitNew",
    ]
    _com_interfaces_ = [pythoncom.IID_IPersistStreamInit]

    def __init__(self):
        self.data = b"abcdefg"
        self.dirty = 1

    def GetClassID(self):
        return pythoncom.IID_NULL

    def IsDirty(self):
        return self.dirty

    def Load(self, stream):
        self.data = stream.Read(26)

    def Save(self, stream, clearDirty):
        stream.Write(self.data)
        if clearDirty:
            self.dirty = 0

    def GetSizeMax(self):
        return 1024

    def InitNew(self):
        pass


class Stream:
    _public_methods_ = ["Read", "Write", "Seek"]
    _com_interfaces_ = [pythoncom.IID_IStream]

    def __init__(self, data):
        self.data = data
        self.index = 0

    def Read(self, amount):
        result = self.data[self.index : self.index + amount]
        self.index += amount
        return result

    def Write(self, data):
        self.data = data
        self.index = 0
        return len(data)

    def Seek(self, dist, origin):
        if origin == pythoncom.STREAM_SEEK_SET:
            self.index = dist
        elif origin == pythoncom.STREAM_SEEK_CUR:
            self.index += dist
        elif origin == pythoncom.STREAM_SEEK_END:
            self.index = len(self.data) + dist
        else:
            raise ValueError("Unknown Seek type: " + str(origin))
        if self.index < 0:
            self.index = 0
        else:
            self.index = min(self.index, len(self.data))
        return self.index


class BadStream(Stream):
    """PyGStream::Read could formerly overflow buffer if the python implementation
    returned more data than requested.
    """

    def Read(self, amount):
        return b"x" * (amount + 1)


class StreamTest(win32com.test.util.TestCase):
    def _readWrite(self, data, write_stream, read_stream=None):
        if read_stream is None:
            read_stream = write_stream
        write_stream.Write(data)
        read_stream.Seek(0, pythoncom.STREAM_SEEK_SET)
        got = read_stream.Read(len(data))
        self.assertEqual(data, got)
        read_stream.Seek(1, pythoncom.STREAM_SEEK_SET)
        got = read_stream.Read(len(data) - 2)
        self.assertEqual(data[1:-1], got)

    def testit(self):
        mydata = b"abcdefghijklmnopqrstuvwxyz"

        # First test the objects just as Python objects...
        s = Stream(mydata)
        p = Persists()

        p.Load(s)
        p.Save(s, 0)
        self.assertEqual(s.data, mydata)

        # Wrap the Python objects as COM objects, and make the calls as if
        # they were non-Python COM objects.
        s2 = win32com.server.util.wrap(s, pythoncom.IID_IStream)
        p2 = win32com.server.util.wrap(p, pythoncom.IID_IPersistStreamInit)

        self._readWrite(mydata, s, s)
        self._readWrite(mydata, s, s2)
        self._readWrite(mydata, s2, s)
        self._readWrite(mydata, s2, s2)

        self._readWrite(b"string with\0a NULL", s2, s2)
        # reset the stream
        s.Write(mydata)
        p2.Load(s2)
        p2.Save(s2, 0)
        self.assertEqual(s.data, mydata)

    def testseek(self):
        s = Stream(b"yo")
        s = win32com.server.util.wrap(s, pythoncom.IID_IStream)
        # we used to die passing a value > 32bits
        s.Seek(0x100000000, pythoncom.STREAM_SEEK_SET)

    def testerrors(self):
        # setup a test logger to capture tracebacks etc.
        records, old_log = win32com.test.util.setup_test_logger()
        ## check for buffer overflow in Read method
        badstream = BadStream("Check for buffer overflow")
        badstream2 = win32com.server.util.wrap(badstream, pythoncom.IID_IStream)
        self.assertRaises(pythoncom.com_error, badstream2.Read, 10)
        win32com.test.util.restore_test_logger(old_log)
        # there's 1 error here
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].msg.startswith("pythoncom error"))


if __name__ == "__main__":
    unittest.main()

# === NexusCore/archive\git_manager.py ===
# ==============================================================================
# フォルダ: src
# ファイル名: git_manager.py
# ==============================================================================
import subprocess
from pathlib import Path
import pandas as pd
import git
import difflib

class GitManager:
    """Gitリポジトリの操作を管理するクラス"""
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"指定されたパス '{self.repo_path}' は有効なGitリポジトリではありません。")

    @staticmethod
    def initialize_repo(repo_path: Path):
        """新しいGitリポジトリを初期化する"""
        git.Repo.init(repo_path)
        # ◀️ ここが修正点！ 初期化後に自分自身のインスタンスを返す
        return GitManager(repo_path)

    def get_current_branch(self):
        """現在のブランチ名を取得する"""
        return self.repo.active_branch.name

    def write_file_and_commit(self, file_path: str, content: str, message: str):
        """ファイルに書き込み、ステージングし、コミットする"""
        full_path = self.repo_path / file_path
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.repo.index.add([file_path])
        self.repo.index.commit(message)

    def read_file(self, file_path: str, commit_hash: str = 'HEAD') -> str:
        """指定されたコミットからファイルの内容を読み込む"""
        try:
            if commit_hash == 'HEAD':
                # HEADの場合、作業ディレクトリの現在のファイルを読み込む
                current_path = self.repo_path / file_path
                if current_path.exists():
                    return current_path.read_text(encoding='utf-8')
                return "" # ファイルが存在しない場合は空文字
            
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except (KeyError, git.exc.GitCommandError):
            return ""

    def get_history(self, limit: int = 20) -> list[dict]:
        """コミット履歴をリストとして取得する"""
        if not self.repo.head.is_valid(): # コミットがまだない場合
            return []
        history = []
        for commit in self.repo.iter_commits(max_count=limit):
            history.append({
                "commit": commit.hexsha,
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
            })
        return history
    
    def get_history_for_ui(self) -> pd.DataFrame:
        """GradioのDataFrame用にコミット履歴を整形する"""
        history = self.get_history()
        if not history:
            return pd.DataFrame(columns=["commit", "author", "date", "message"])
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
        df['message'] = df['message'].str.split('\n').str[0]
        # commit_shortカラムを削除し、commitカラムを7文字に制限
        df['commit'] = df['commit'].str[:7]
        df = df[['commit', 'author', 'date', 'message']]
        return df

    def get_tracked_files(self) -> list[str]:
        """リポジトリで追跡されているファイルの一覧を取得する"""
        if not self.repo.head.is_valid():
            return []
        # 'git ls-files'をGitPython経由で実行
        return self.repo.git.ls_files().splitlines()

    def checkout(self, commit_or_branch: str):
        """指定されたコミットまたはブランチにチェックアウトする"""
        self.repo.git.checkout(commit_or_branch)
        
    # --- write_fileとcommitを分離 ---
    def write_file(self, file_path: str, content: str):
        """ファイルへの書き込みのみを行う"""
        full_path = self.repo_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')

    def commit(self, message: str, add_all: bool = True):
        """変更をコミットする"""
        if add_all:
            self.repo.index.add(self.repo.untracked_files)
            self.repo.index.add([item.a_path for item in self.repo.index.diff(None)])
        self.repo.index.commit(message)
        
    def run_pytest(self, project_path: str) -> str:
        """リポジトリ内でpytestを実行する"""
        try:
            result = subprocess.run(
                ["pytest"], cwd=project_path, capture_output=True,
                text=True, encoding="utf-8", timeout=30
            )
            output = "--- stdout ---\n" + (result.stdout or "（なし）")
            if result.stderr:
                output += "\n\n--- stderr ---\n" + result.stderr
            return output
        except FileNotFoundError:
            return "❌ `pytest` コマンドが見つかりません。インストールされているか確認してください。"
        except Exception as e:
            return f"❌ テスト実行中に予期せぬエラーが発生しました: {e}"

def get_file_diff(old_content: str, new_content: str, filename: str) -> str:
    """2つのテキストの差分をHTML形式で生成する"""
    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True), fromfile=f"a/{filename}", tofile=f"b/{filename}"
    )
    html = '<div class="diff-container">'
    has_changes = False
    for line in diff:
        has_changes = True
        line_escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith('+'):
            html += f'<div class="diff-add">{line_escaped}</div>'
        elif line.startswith('-'):
            html += f'<div class="diff-remove">{line_escaped}</div>'
        elif line.startswith('@@'):
            html += f'<div><strong>{line_escaped}</strong></div>'
        else:
            html += f'<div>{line_escaped}</div>'
    html += '</div>'
    return html if has_changes else "変更はありません。"

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\download.py ===
import logging
import os
from optparse import Values
from typing import List

from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req.req_install import check_legacy_setup_py_options
from pip._internal.utils.misc import ensure_dir, normalize_path, write_output
from pip._internal.utils.temp_dir import TempDirectory

logger = logging.getLogger(__name__)


class DownloadCommand(RequirementCommand):
    """
    Download packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports downloading from "requirements files", which provide
    an easy way to specify a whole environment to be downloaded.
    """

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] <vcs project url> ...
      %prog [options] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.global_options())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.src())
        self.cmd_opts.add_option(cmdoptions.pre())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())

        self.cmd_opts.add_option(
            "-d",
            "--dest",
            "--destination-dir",
            "--destination-directory",
            dest="download_dir",
            metavar="dir",
            default=os.curdir,
            help="Download packages into <dir>.",
        )

        cmdoptions.add_target_python_options(self.cmd_opts)

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        options.ignore_installed = True
        # editable doesn't really make sense for `pip download`, but the bowels
        # of the RequirementSet code require that property.
        options.editables = []

        cmdoptions.check_dist_restriction(options)

        options.download_dir = normalize_path(options.download_dir)
        ensure_dir(options.download_dir)

        session = self.get_default_session(options)

        target_python = make_target_python(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )

        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="download",
            globally_managed=True,
        )

        reqs = self.get_requirements(args, options, finder, session)
        check_legacy_setup_py_options(options, reqs)

        preparer = self.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.download_dir,
            use_user_site=False,
            verbosity=self.verbosity,
        )

        resolver = self.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            ignore_requires_python=options.ignore_requires_python,
            use_pep517=options.use_pep517,
            py_version_info=options.python_version,
        )

        self.trace_basic_info(finder)

        requirement_set = resolver.resolve(reqs, check_supported_wheels=True)

        downloaded: List[str] = []
        for req in requirement_set.requirements.values():
            if req.satisfied_by is None:
                assert req.name is not None
                preparer.save_linked_requirement(req)
                downloaded.append(req.name)

        preparer.prepare_linked_requirements_more(requirement_set.requirements.values())

        if downloaded:
            write_output("Successfully downloaded %s", " ".join(downloaded))

        return SUCCESS

# === NexusCore/myenv\Lib\site-packages\pip\_internal\utils\setuptools_build.py ===
import sys
import textwrap
from typing import List, Optional, Sequence

# Shim to wrap setup.py invocation with setuptools
# Note that __file__ is handled via two {!r} *and* %r, to ensure that paths on
# Windows are correctly handled (it should be "C:\\Users" not "C:\Users").
_SETUPTOOLS_SHIM = textwrap.dedent(
    """
    exec(compile('''
    # This is <pip-setuptools-caller> -- a caller that pip uses to run setup.py
    #
    # - It imports setuptools before invoking setup.py, to enable projects that directly
    #   import from `distutils.core` to work with newer packaging standards.
    # - It provides a clear error message when setuptools is not installed.
    # - It sets `sys.argv[0]` to the underlying `setup.py`, when invoking `setup.py` so
    #   setuptools doesn't think the script is `-c`. This avoids the following warning:
    #     manifest_maker: standard file '-c' not found".
    # - It generates a shim setup.py, for handling setup.cfg-only projects.
    import os, sys, tokenize

    try:
        import setuptools
    except ImportError as error:
        print(
            "ERROR: Can not execute `setup.py` since setuptools is not available in "
            "the build environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    __file__ = %r
    sys.argv[0] = __file__

    if os.path.exists(__file__):
        filename = __file__
        with tokenize.open(__file__) as f:
            setup_py_code = f.read()
    else:
        filename = "<auto-generated setuptools caller>"
        setup_py_code = "from setuptools import setup; setup()"

    exec(compile(setup_py_code, filename, "exec"))
    ''' % ({!r},), "<pip-setuptools-caller>", "exec"))
    """
).rstrip()


def make_setuptools_shim_args(
    setup_py_path: str,
    global_options: Optional[Sequence[str]] = None,
    no_user_config: bool = False,
    unbuffered_output: bool = False,
) -> List[str]:
    """
    Get setuptools command arguments with shim wrapped setup file invocation.

    :param setup_py_path: The path to setup.py to be wrapped.
    :param global_options: Additional global options.
    :param no_user_config: If True, disables personal user configuration.
    :param unbuffered_output: If True, adds the unbuffered switch to the
     argument list.
    """
    args = [sys.executable]
    if unbuffered_output:
        args += ["-u"]
    args += ["-c", _SETUPTOOLS_SHIM.format(setup_py_path)]
    if global_options:
        args += global_options
    if no_user_config:
        args += ["--no-user-cfg"]
    return args


def make_setuptools_bdist_wheel_args(
    setup_py_path: str,
    global_options: Sequence[str],
    build_options: Sequence[str],
    destination_dir: str,
) -> List[str]:
    # NOTE: Eventually, we'd want to also -S to the flags here, when we're
    # isolating. Currently, it breaks Python in virtualenvs, because it
    # relies on site.py to find parts of the standard library outside the
    # virtualenv.
    args = make_setuptools_shim_args(
        setup_py_path, global_options=global_options, unbuffered_output=True
    )
    args += ["bdist_wheel", "-d", destination_dir]
    args += build_options
    return args


def make_setuptools_clean_args(
    setup_py_path: str,
    global_options: Sequence[str],
) -> List[str]:
    args = make_setuptools_shim_args(
        setup_py_path, global_options=global_options, unbuffered_output=True
    )
    args += ["clean", "--all"]
    return args


def make_setuptools_develop_args(
    setup_py_path: str,
    *,
    global_options: Sequence[str],
    no_user_config: bool,
    prefix: Optional[str],
    home: Optional[str],
    use_user_site: bool,
) -> List[str]:
    assert not (use_user_site and prefix)

    args = make_setuptools_shim_args(
        setup_py_path,
        global_options=global_options,
        no_user_config=no_user_config,
    )

    args += ["develop", "--no-deps"]

    if prefix:
        args += ["--prefix", prefix]
    if home is not None:
        args += ["--install-dir", home]

    if use_user_site:
        args += ["--user", "--prefix="]

    return args


def make_setuptools_egg_info_args(
    setup_py_path: str,
    egg_info_dir: Optional[str],
    no_user_config: bool,
) -> List[str]:
    args = make_setuptools_shim_args(setup_py_path, no_user_config=no_user_config)

    args += ["egg_info"]

    if egg_info_dir:
        args += ["--egg-base", egg_info_dir]

    return args

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\cachecontrol\serialize.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
from typing import IO, TYPE_CHECKING, Any, Mapping, cast

from pip._vendor import msgpack
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.urllib3 import HTTPResponse

if TYPE_CHECKING:
    from pip._vendor.requests import PreparedRequest


class Serializer:
    serde_version = "4"

    def dumps(
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
    ) -> bytes:
        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if body is None:
            # When a body isn't passed in, we'll read the response. We
            # also update the response with a new file handler to be
            # sure it acts as though it was never read.
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)  # type: ignore[assignment]
            response.length_remaining = len(body)

        data = {
            "response": {
                "body": body,  # Empty bytestring if body is stored separately
                "headers": {str(k): str(v) for k, v in response.headers.items()},
                "status": response.status,
                "version": response.version,
                "reason": str(response.reason),
                "decode_content": response.decode_content,
            }
        }

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers["vary"].split(",")
            for header in varied_headers:
                header = str(header).strip()
                header_value = request.headers.get(header, None)
                if header_value is not None:
                    header_value = str(header_value)
                data["vary"][header] = header_value

        return b",".join([f"cc={self.serde_version}".encode(), self.serialize(data)])

    def serialize(self, data: dict[str, Any]) -> bytes:
        return cast(bytes, msgpack.dumps(data, use_bin_type=True))

    def loads(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        # Short circuit if we've been given an empty set of data
        if not data:
            return None

        # Previous versions of this library supported other serialization
        # formats, but these have all been removed.
        if not data.startswith(f"cc={self.serde_version},".encode()):
            return None

        data = data[5:]
        return self._loads_v4(request, data, body_file)

    def prepare_response(
        self,
        request: PreparedRequest,
        cached: Mapping[str, Any],
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        """Verify our vary headers match and construct a real urllib3
        HTTPResponse object.
        """
        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        # This case is also handled in the controller code when creating
        # a cache entry, but is left here for backwards compatibility.
        if "*" in cached.get("vary", {}):
            return None

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return None

        body_raw = cached["response"].pop("body")

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            data=cached["response"]["headers"]
        )
        if headers.get("transfer-encoding", "") == "chunked":
            headers.pop("transfer-encoding")

        cached["response"]["headers"] = headers

        try:
            body: IO[bytes]
            if body_file is None:
                body = io.BytesIO(body_raw)
            else:
                body = body_file
        except TypeError:
            # This can happen if cachecontrol serialized to v1 format (pickle)
            # using Python 2. A Python 2 str(byte string) will be unpickled as
            # a Python 3 str (unicode string), which will cause the above to
            # fail with:
            #
            #     TypeError: 'str' does not support the buffer interface
            body = io.BytesIO(body_raw.encode("utf8"))

        # Discard any `strict` parameter serialized by older version of cachecontrol.
        cached["response"].pop("strict", None)

        return HTTPResponse(body=body, preload_content=False, **cached["response"])

    def _loads_v4(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        try:
            cached = msgpack.loads(data, raw=False)
        except ValueError:
            return None

        return self.prepare_response(request, cached, body_file)

# === NexusCore/openenv\Lib\site-packages\pyasn1\debug.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import logging
import sys

from pyasn1 import __version__
from pyasn1 import error

__all__ = ['Debug', 'setLogger', 'hexdump']

DEBUG_NONE = 0x0000
DEBUG_ENCODER = 0x0001
DEBUG_DECODER = 0x0002
DEBUG_ALL = 0xffff

FLAG_MAP = {
    'none': DEBUG_NONE,
    'encoder': DEBUG_ENCODER,
    'decoder': DEBUG_DECODER,
    'all': DEBUG_ALL
}

LOGGEE_MAP = {}


class Printer(object):
    # noinspection PyShadowingNames
    def __init__(self, logger=None, handler=None, formatter=None):
        if logger is None:
            logger = logging.getLogger('pyasn1')

        logger.setLevel(logging.DEBUG)

        if handler is None:
            handler = logging.StreamHandler()

        if formatter is None:
            formatter = logging.Formatter('%(asctime)s %(name)s: %(message)s')

        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        self.__logger = logger

    def __call__(self, msg):
        self.__logger.debug(msg)

    def __str__(self):
        return '<python logging>'


class Debug(object):
    defaultPrinter = Printer()

    def __init__(self, *flags, **options):
        self._flags = DEBUG_NONE

        if 'loggerName' in options:
            # route our logs to parent logger
            self._printer = Printer(
                logger=logging.getLogger(options['loggerName']),
                handler=logging.NullHandler()
            )

        elif 'printer' in options:
            self._printer = options.get('printer')

        else:
            self._printer = self.defaultPrinter

        self._printer('running pyasn1 %s, debug flags %s' % (__version__, ', '.join(flags)))

        for flag in flags:
            inverse = flag and flag[0] in ('!', '~')
            if inverse:
                flag = flag[1:]
            try:
                if inverse:
                    self._flags &= ~FLAG_MAP[flag]
                else:
                    self._flags |= FLAG_MAP[flag]
            except KeyError:
                raise error.PyAsn1Error('bad debug flag %s' % flag)

            self._printer("debug category '%s' %s" % (flag, inverse and 'disabled' or 'enabled'))

    def __str__(self):
        return 'logger %s, flags %x' % (self._printer, self._flags)

    def __call__(self, msg):
        self._printer(msg)

    def __and__(self, flag):
        return self._flags & flag

    def __rand__(self, flag):
        return flag & self._flags

_LOG = DEBUG_NONE


def setLogger(userLogger):
    global _LOG

    if userLogger:
        _LOG = userLogger
    else:
        _LOG = DEBUG_NONE

    # Update registered logging clients
    for module, (name, flags) in LOGGEE_MAP.items():
        setattr(module, name, _LOG & flags and _LOG or DEBUG_NONE)


def registerLoggee(module, name='LOG', flags=DEBUG_NONE):
    LOGGEE_MAP[sys.modules[module]] = name, flags
    setLogger(_LOG)
    return _LOG


def hexdump(octets):
    return ' '.join(
        ['%s%.2X' % (n % 16 == 0 and ('\n%.5d: ' % n) or '', x)
         for n, x in zip(range(len(octets)), octets)]
    )


class Scope(object):
    def __init__(self):
        self._list = []

    def __str__(self): return '.'.join(self._list)

    def push(self, token):
        self._list.append(token)

    def pop(self):
        return self._list.pop()


scope = Scope()

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3370.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Cryptographic Message Syntax (CMS) Algorithms
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc3370.txt
#

from pyasn1.type import univ

from pyasn1_modules import rfc3279
from pyasn1_modules import rfc5280
from pyasn1_modules import rfc5751
from pyasn1_modules import rfc5753
from pyasn1_modules import rfc5990
from pyasn1_modules import rfc8018


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier


# Imports from RFC 3279

dhpublicnumber = rfc3279.dhpublicnumber

dh_public_number = dhpublicnumber

DHPublicKey = rfc3279.DHPublicKey

DomainParameters = rfc3279.DomainParameters

DHDomainParameters = DomainParameters

Dss_Parms = rfc3279.Dss_Parms

Dss_Sig_Value = rfc3279.Dss_Sig_Value

md5 = rfc3279.md5

md5WithRSAEncryption = rfc3279.md5WithRSAEncryption

RSAPublicKey = rfc3279.RSAPublicKey

rsaEncryption = rfc3279.rsaEncryption

ValidationParms = rfc3279.ValidationParms

id_dsa = rfc3279.id_dsa

id_dsa_with_sha1 = rfc3279.id_dsa_with_sha1

id_sha1 = rfc3279.id_sha1

sha_1 = id_sha1

sha1WithRSAEncryption = rfc3279.sha1WithRSAEncryption


# Imports from RFC 5753

CBCParameter = rfc5753.CBCParameter

CBCParameter = rfc5753.IV

KeyWrapAlgorithm = rfc5753.KeyWrapAlgorithm


# Imports from RFC 5990

id_alg_CMS3DESwrap = rfc5990.id_alg_CMS3DESwrap


# Imports from RFC 8018

des_EDE3_CBC = rfc8018.des_EDE3_CBC

des_ede3_cbc = des_EDE3_CBC

rc2CBC = rfc8018.rc2CBC

rc2_cbc = rc2CBC

RC2_CBC_Parameter = rfc8018.RC2_CBC_Parameter

RC2CBCParameter = RC2_CBC_Parameter

PBKDF2_params = rfc8018.PBKDF2_params

id_PBKDF2 = rfc8018.id_PBKDF2


# The few things that are not already defined elsewhere

hMAC_SHA1 = univ.ObjectIdentifier('1.3.6.1.5.5.8.1.2')


id_alg_ESDH = univ.ObjectIdentifier('1.2.840.113549.1.9.16.3.5')


id_alg_SSDH = univ.ObjectIdentifier('1.2.840.113549.1.9.16.3.10')


id_alg_CMSRC2wrap = univ.ObjectIdentifier('1.2.840.113549.1.9.16.3.7')


class RC2ParameterVersion(univ.Integer):
    pass


class RC2wrapParameter(RC2ParameterVersion):
    pass


class Dss_Pub_Key(univ.Integer):
    pass


# Update the Algorithm Identifier map in rfc5280.py.

_algorithmIdentifierMapUpdate = {
    hMAC_SHA1: univ.Null(""),
    id_alg_CMSRC2wrap: RC2wrapParameter(),
    id_alg_ESDH: KeyWrapAlgorithm(),
    id_alg_SSDH: KeyWrapAlgorithm(),
}

rfc5280.algorithmIdentifierMap.update(_algorithmIdentifierMapUpdate)


# Update the S/MIME Capabilities map in rfc5751.py.

_smimeCapabilityMapUpdate = {
    id_alg_CMSRC2wrap: RC2wrapParameter(),
    id_alg_ESDH: KeyWrapAlgorithm(),
    id_alg_SSDH: KeyWrapAlgorithm(),
}

rfc5751.smimeCapabilityMap.update(_smimeCapabilityMapUpdate)

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\anyio.py ===
from __future__ import annotations

import ssl
import typing

import anyio

from .._exceptions import (
    ConnectError,
    ConnectTimeout,
    ReadError,
    ReadTimeout,
    WriteError,
    WriteTimeout,
    map_exceptions,
)
from .._utils import is_socket_readable
from .base import SOCKET_OPTION, AsyncNetworkBackend, AsyncNetworkStream


class AnyIOStream(AsyncNetworkStream):
    def __init__(self, stream: anyio.abc.ByteStream) -> None:
        self._stream = stream

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        exc_map = {
            TimeoutError: ReadTimeout,
            anyio.BrokenResourceError: ReadError,
            anyio.ClosedResourceError: ReadError,
            anyio.EndOfStream: ReadError,
        }
        with map_exceptions(exc_map):
            with anyio.fail_after(timeout):
                try:
                    return await self._stream.receive(max_bytes=max_bytes)
                except anyio.EndOfStream:  # pragma: nocover
                    return b""

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        if not buffer:
            return

        exc_map = {
            TimeoutError: WriteTimeout,
            anyio.BrokenResourceError: WriteError,
            anyio.ClosedResourceError: WriteError,
        }
        with map_exceptions(exc_map):
            with anyio.fail_after(timeout):
                await self._stream.send(item=buffer)

    async def aclose(self) -> None:
        await self._stream.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> AsyncNetworkStream:
        exc_map = {
            TimeoutError: ConnectTimeout,
            anyio.BrokenResourceError: ConnectError,
            anyio.EndOfStream: ConnectError,
            ssl.SSLError: ConnectError,
        }
        with map_exceptions(exc_map):
            try:
                with anyio.fail_after(timeout):
                    ssl_stream = await anyio.streams.tls.TLSStream.wrap(
                        self._stream,
                        ssl_context=ssl_context,
                        hostname=server_hostname,
                        standard_compatible=False,
                        server_side=False,
                    )
            except Exception as exc:  # pragma: nocover
                await self.aclose()
                raise exc
        return AnyIOStream(ssl_stream)

    def get_extra_info(self, info: str) -> typing.Any:
        if info == "ssl_object":
            return self._stream.extra(anyio.streams.tls.TLSAttribute.ssl_object, None)
        if info == "client_addr":
            return self._stream.extra(anyio.abc.SocketAttribute.local_address, None)
        if info == "server_addr":
            return self._stream.extra(anyio.abc.SocketAttribute.remote_address, None)
        if info == "socket":
            return self._stream.extra(anyio.abc.SocketAttribute.raw_socket, None)
        if info == "is_readable":
            sock = self._stream.extra(anyio.abc.SocketAttribute.raw_socket, None)
            return is_socket_readable(sock)
        return None


class AnyIOBackend(AsyncNetworkBackend):
    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:  # pragma: nocover
        if socket_options is None:
            socket_options = []
        exc_map = {
            TimeoutError: ConnectTimeout,
            OSError: ConnectError,
            anyio.BrokenResourceError: ConnectError,
        }
        with map_exceptions(exc_map):
            with anyio.fail_after(timeout):
                stream: anyio.abc.ByteStream = await anyio.connect_tcp(
                    remote_host=host,
                    remote_port=port,
                    local_host=local_address,
                )
                # By default TCP sockets opened in `asyncio` include TCP_NODELAY.
                for option in socket_options:
                    stream._raw_socket.setsockopt(*option)  # type: ignore[attr-defined] # pragma: no cover
        return AnyIOStream(stream)

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:  # pragma: nocover
        if socket_options is None:
            socket_options = []
        exc_map = {
            TimeoutError: ConnectTimeout,
            OSError: ConnectError,
            anyio.BrokenResourceError: ConnectError,
        }
        with map_exceptions(exc_map):
            with anyio.fail_after(timeout):
                stream: anyio.abc.ByteStream = await anyio.connect_unix(path)
                for option in socket_options:
                    stream._raw_socket.setsockopt(*option)  # type: ignore[attr-defined] # pragma: no cover
        return AnyIOStream(stream)

    async def sleep(self, seconds: float) -> None:
        await anyio.sleep(seconds)  # pragma: nocover

# === NexusCore/openenv\Lib\site-packages\interpreter\core\computer\terminal\languages\java.py ===
import os
import queue
import re
import subprocess
import threading
import time
import traceback
from .subprocess_language import SubprocessLanguage

class Java(SubprocessLanguage):
    file_extension = "java"
    name = "Java"

    def __init__(self):
        super().__init__()
        self.start_cmd = None  # We will handle the start command in the run method

    def preprocess_code(self, code):
        return preprocess_java(code)

    def line_postprocessor(self, line):
        # Clean up output from javac and java
        return line.strip()

    def detect_active_line(self, line):
        if "##active_line" in line:
            return int(line.split("##active_line")[1].split("##")[0])
        return None

    def detect_end_of_execution(self, line):
        return "##end_of_execution##" in line

    def run(self, code):
        try:
            # Extract the class name from the code
            match = re.search(r'class\s+(\w+)', code)
            if not match:
                yield {
                    "type": "console",
                    "format": "output",
                    "content": "Error: No class definition found in the provided code."
                }
                return

            class_name = match.group(1)
            file_name = f"{class_name}.java"

            # Write the Java code to a file, preserving newlines
            with open(file_name, "w", newline='\n') as file:
                file.write(code)

            # Compile the Java code
            compile_process = subprocess.Popen(
                ["javac", file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = compile_process.communicate()

            if compile_process.returncode != 0:
                yield {
                    "type": "console",
                    "format": "output",
                    "content": f"Compilation Error:\n{stderr}"
                }
                return

            # Run the compiled Java code
            run_process = subprocess.Popen(
                ["java", class_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout_thread = threading.Thread(
                target=self.handle_stream_output,
                args=(run_process.stdout, False),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=self.handle_stream_output,
                args=(run_process.stderr, True),
                daemon=True,
            )

            stdout_thread.start()
            stderr_thread.start()

            stdout_thread.join()
            stderr_thread.join()

            run_process.wait()
            self.done.set()

            while True:
                if not self.output_queue.empty():
                    yield self.output_queue.get()
                else:
                    time.sleep(0.1)
                try:
                    output = self.output_queue.get(timeout=0.3)
                    yield output
                except queue.Empty:
                    if self.done.is_set():
                        for _ in range(3):
                            if not self.output_queue.empty():
                                yield self.output_queue.get()
                            time.sleep(0.2)
                        break

        except Exception as e:
            yield {
                "type": "console",
                "format": "output",
                "content": f"{traceback.format_exc()}"
            }
        finally:
            # Clean up the generated Java files
            if os.path.exists(file_name):
                os.remove(file_name)
            class_file = file_name.replace(".java", ".class")
            if os.path.exists(class_file):
                os.remove(class_file)

def preprocess_java(code):
    """
    Add active line markers
    Add end of execution marker
    """
    lines = code.split("\n")
    processed_lines = []

    for i, line in enumerate(lines, 1):
        # Add active line print
        processed_lines.append(f'System.out.println("##active_line{i}##");')
        processed_lines.append(line)

    # Join lines to form the processed code
    code = "\n".join(processed_lines)

    # Add end of execution marker
    code += '\nSystem.out.println("##end_of_execution##");'
    return code

# === NexusCore/openenv\Lib\site-packages\jedi\inference\finder.py ===
"""
Searching for names with given scope and name. This is very central in Jedi and
Python. The name resolution is quite complicated with descripter,
``__getattribute__``, ``__getattr__``, ``global``, etc.

If you want to understand name resolution, please read the first few chapters
in http://blog.ionelmc.ro/2015/02/09/understanding-python-metaclasses/.

Flow checks
+++++++++++

Flow checks are not really mature. There's only a check for ``isinstance``.  It
would check whether a flow has the form of ``if isinstance(a, type_or_tuple)``.
Unfortunately every other thing is being ignored (e.g. a == '' would be easy to
check for -> a is a string). There's big potential in these checks.
"""

from parso.tree import search_ancestor
from parso.python.tree import Name

from jedi import settings
from jedi.inference.arguments import TreeArguments
from jedi.inference.value import iterable
from jedi.inference.base_value import NO_VALUES
from jedi.parser_utils import is_scope


def filter_name(filters, name_or_str):
    """
    Searches names that are defined in a scope (the different
    ``filters``), until a name fits.
    """
    string_name = name_or_str.value if isinstance(name_or_str, Name) else name_or_str
    names = []
    for filter in filters:
        names = filter.get(string_name)
        if names:
            break

    return list(_remove_del_stmt(names))


def _remove_del_stmt(names):
    # Catch del statements and remove them from results.
    for name in names:
        if name.tree_name is not None:
            definition = name.tree_name.get_definition()
            if definition is not None and definition.type == 'del_stmt':
                continue
        yield name


def check_flow_information(value, flow, search_name, pos):
    """ Try to find out the type of a variable just with the information that
    is given by the flows: e.g. It is also responsible for assert checks.::

        if isinstance(k, str):
            k.  # <- completion here

    ensures that `k` is a string.
    """
    if not settings.dynamic_flow_information:
        return None

    result = None
    if is_scope(flow):
        # Check for asserts.
        module_node = flow.get_root_node()
        try:
            names = module_node.get_used_names()[search_name.value]
        except KeyError:
            return None
        names = reversed([
            n for n in names
            if flow.start_pos <= n.start_pos < (pos or flow.end_pos)
        ])

        for name in names:
            ass = search_ancestor(name, 'assert_stmt')
            if ass is not None:
                result = _check_isinstance_type(value, ass.assertion, search_name)
                if result is not None:
                    return result

    if flow.type in ('if_stmt', 'while_stmt'):
        potential_ifs = [c for c in flow.children[1::4] if c != ':']
        for if_test in reversed(potential_ifs):
            if search_name.start_pos > if_test.end_pos:
                return _check_isinstance_type(value, if_test, search_name)
    return result


def _get_isinstance_trailer_arglist(node):
    if node.type in ('power', 'atom_expr') and len(node.children) == 2:
        # This might be removed if we analyze and, etc
        first, trailer = node.children
        if first.type == 'name' and first.value == 'isinstance' \
                and trailer.type == 'trailer' and trailer.children[0] == '(':
            return trailer
    return None


def _check_isinstance_type(value, node, search_name):
    lazy_cls = None
    trailer = _get_isinstance_trailer_arglist(node)
    if trailer is not None and len(trailer.children) == 3:
        arglist = trailer.children[1]
        args = TreeArguments(value.inference_state, value, arglist, trailer)
        param_list = list(args.unpack())
        # Disallow keyword arguments
        if len(param_list) == 2 and len(arglist.children) == 3:
            (key1, _), (key2, lazy_value_cls) = param_list
            if key1 is None and key2 is None:
                call = _get_call_string(search_name)
                is_instance_call = _get_call_string(arglist.children[0])
                # Do a simple get_code comparison of the strings . They should
                # just have the same code, and everything will be all right.
                # There are ways that this is not correct, if some stuff is
                # redefined in between. However here we don't care, because
                # it's a heuristic that works pretty well.
                if call == is_instance_call:
                    lazy_cls = lazy_value_cls
    if lazy_cls is None:
        return None

    value_set = NO_VALUES
    for cls_or_tup in lazy_cls.infer():
        if isinstance(cls_or_tup, iterable.Sequence) and cls_or_tup.array_type == 'tuple':
            for lazy_value in cls_or_tup.py__iter__():
                value_set |= lazy_value.infer().execute_with_values()
        else:
            value_set |= cls_or_tup.execute_with_values()
    return value_set


def _get_call_string(node):
    if node.parent.type == 'atom_expr':
        return _get_call_string(node.parent)

    code = ''
    leaf = node.get_first_leaf()
    end = node.get_last_leaf().end_pos
    while leaf.start_pos < end:
        code += leaf.value
        leaf = leaf.get_next_leaf()
    return code

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\rte.py ===
# Natural Language Toolkit: RTE Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author:  Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Corpus reader for the Recognizing Textual Entailment (RTE) Challenge Corpora.

The files were taken from the RTE1, RTE2 and RTE3 datasets and the files
were regularized.

Filenames are of the form rte*_dev.xml and rte*_test.xml. The latter are the
gold standard annotated files.

Each entailment corpus is a list of 'text'/'hypothesis' pairs. The following
example is taken from RTE3::

 <pair id="1" entailment="YES" task="IE" length="short" >

    <t>The sale was made to pay Yukos' US$ 27.5 billion tax bill,
    Yuganskneftegaz was originally sold for US$ 9.4 billion to a little known
    company Baikalfinansgroup which was later bought by the Russian
    state-owned oil company Rosneft .</t>

   <h>Baikalfinansgroup was sold to Rosneft.</h>
 </pair>

In order to provide globally unique IDs for each pair, a new attribute
``challenge`` has been added to the root element ``entailment-corpus`` of each
file, taking values 1, 2 or 3. The GID is formatted 'm-n', where 'm' is the
challenge number and 'n' is the pair ID.
"""
from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.xmldocs import *


def norm(value_string):
    """
    Normalize the string value in an RTE pair's ``value`` or ``entailment``
    attribute as an integer (1, 0).

    :param value_string: the label used to classify a text/hypothesis pair
    :type value_string: str
    :rtype: int
    """

    valdict = {"TRUE": 1, "FALSE": 0, "YES": 1, "NO": 0}
    return valdict[value_string.upper()]


class RTEPair:
    """
    Container for RTE text-hypothesis pairs.

    The entailment relation is signalled by the ``value`` attribute in RTE1, and by
    ``entailment`` in RTE2 and RTE3. These both get mapped on to the ``entailment``
    attribute of this class.
    """

    def __init__(
        self,
        pair,
        challenge=None,
        id=None,
        text=None,
        hyp=None,
        value=None,
        task=None,
        length=None,
    ):
        """
        :param challenge: version of the RTE challenge (i.e., RTE1, RTE2 or RTE3)
        :param id: identifier for the pair
        :param text: the text component of the pair
        :param hyp: the hypothesis component of the pair
        :param value: classification label for the pair
        :param task: attribute for the particular NLP task that the data was drawn from
        :param length: attribute for the length of the text of the pair
        """
        self.challenge = challenge
        self.id = pair.attrib["id"]
        self.gid = f"{self.challenge}-{self.id}"
        self.text = pair[0].text
        self.hyp = pair[1].text

        if "value" in pair.attrib:
            self.value = norm(pair.attrib["value"])
        elif "entailment" in pair.attrib:
            self.value = norm(pair.attrib["entailment"])
        else:
            self.value = value
        if "task" in pair.attrib:
            self.task = pair.attrib["task"]
        else:
            self.task = task
        if "length" in pair.attrib:
            self.length = pair.attrib["length"]
        else:
            self.length = length

    def __repr__(self):
        if self.challenge:
            return f"<RTEPair: gid={self.challenge}-{self.id}>"
        else:
            return "<RTEPair: id=%s>" % self.id


class RTECorpusReader(XMLCorpusReader):
    """
    Corpus reader for corpora in RTE challenges.

    This is just a wrapper around the XMLCorpusReader. See module docstring above for the expected
    structure of input documents.
    """

    def _read_etree(self, doc):
        """
        Map the XML input into an RTEPair.

        This uses the ``getiterator()`` method from the ElementTree package to
        find all the ``<pair>`` elements.

        :param doc: a parsed XML document
        :rtype: list(RTEPair)
        """
        try:
            challenge = doc.attrib["challenge"]
        except KeyError:
            challenge = None
        pairiter = doc.iter("pair")
        return [RTEPair(pair, challenge=challenge) for pair in pairiter]

    def pairs(self, fileids):
        """
        Build a list of RTEPairs from a RTE corpus.

        :param fileids: a list of RTE corpus fileids
        :type: list
        :rtype: list(RTEPair)
        """
        if isinstance(fileids, str):
            fileids = [fileids]
        return concat([self._read_etree(self.xml(fileid)) for fileid in fileids])

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\download.py ===
import logging
import os
from optparse import Values
from typing import List

from pip._internal.cli import cmdoptions
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.req_command import RequirementCommand, with_cleanup
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.req.req_install import check_legacy_setup_py_options
from pip._internal.utils.misc import ensure_dir, normalize_path, write_output
from pip._internal.utils.temp_dir import TempDirectory

logger = logging.getLogger(__name__)


class DownloadCommand(RequirementCommand):
    """
    Download packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports downloading from "requirements files", which provide
    an easy way to specify a whole environment to be downloaded.
    """

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] <vcs project url> ...
      %prog [options] <local project path> ...
      %prog [options] <archive url/path> ..."""

    def add_options(self) -> None:
        self.cmd_opts.add_option(cmdoptions.constraints())
        self.cmd_opts.add_option(cmdoptions.requirements())
        self.cmd_opts.add_option(cmdoptions.no_deps())
        self.cmd_opts.add_option(cmdoptions.global_options())
        self.cmd_opts.add_option(cmdoptions.no_binary())
        self.cmd_opts.add_option(cmdoptions.only_binary())
        self.cmd_opts.add_option(cmdoptions.prefer_binary())
        self.cmd_opts.add_option(cmdoptions.src())
        self.cmd_opts.add_option(cmdoptions.pre())
        self.cmd_opts.add_option(cmdoptions.require_hashes())
        self.cmd_opts.add_option(cmdoptions.progress_bar())
        self.cmd_opts.add_option(cmdoptions.no_build_isolation())
        self.cmd_opts.add_option(cmdoptions.use_pep517())
        self.cmd_opts.add_option(cmdoptions.no_use_pep517())
        self.cmd_opts.add_option(cmdoptions.check_build_deps())
        self.cmd_opts.add_option(cmdoptions.ignore_requires_python())

        self.cmd_opts.add_option(
            "-d",
            "--dest",
            "--destination-dir",
            "--destination-directory",
            dest="download_dir",
            metavar="dir",
            default=os.curdir,
            help="Download packages into <dir>.",
        )

        cmdoptions.add_target_python_options(self.cmd_opts)

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    @with_cleanup
    def run(self, options: Values, args: List[str]) -> int:
        options.ignore_installed = True
        # editable doesn't really make sense for `pip download`, but the bowels
        # of the RequirementSet code require that property.
        options.editables = []

        cmdoptions.check_dist_restriction(options)

        options.download_dir = normalize_path(options.download_dir)
        ensure_dir(options.download_dir)

        session = self.get_default_session(options)

        target_python = make_target_python(options)
        finder = self._build_package_finder(
            options=options,
            session=session,
            target_python=target_python,
            ignore_requires_python=options.ignore_requires_python,
        )

        build_tracker = self.enter_context(get_build_tracker())

        directory = TempDirectory(
            delete=not options.no_clean,
            kind="download",
            globally_managed=True,
        )

        reqs = self.get_requirements(args, options, finder, session)
        check_legacy_setup_py_options(options, reqs)

        preparer = self.make_requirement_preparer(
            temp_build_dir=directory,
            options=options,
            build_tracker=build_tracker,
            session=session,
            finder=finder,
            download_dir=options.download_dir,
            use_user_site=False,
            verbosity=self.verbosity,
        )

        resolver = self.make_resolver(
            preparer=preparer,
            finder=finder,
            options=options,
            ignore_requires_python=options.ignore_requires_python,
            use_pep517=options.use_pep517,
            py_version_info=options.python_version,
        )

        self.trace_basic_info(finder)

        requirement_set = resolver.resolve(reqs, check_supported_wheels=True)

        downloaded: List[str] = []
        for req in requirement_set.requirements.values():
            if req.satisfied_by is None:
                assert req.name is not None
                preparer.save_linked_requirement(req)
                downloaded.append(req.name)

        preparer.prepare_linked_requirements_more(requirement_set.requirements.values())

        if downloaded:
            write_output("Successfully downloaded %s", " ".join(downloaded))

        return SUCCESS

# === NexusCore/openenv\Lib\site-packages\pip\_internal\utils\setuptools_build.py ===
import sys
import textwrap
from typing import List, Optional, Sequence

# Shim to wrap setup.py invocation with setuptools
# Note that __file__ is handled via two {!r} *and* %r, to ensure that paths on
# Windows are correctly handled (it should be "C:\\Users" not "C:\Users").
_SETUPTOOLS_SHIM = textwrap.dedent(
    """
    exec(compile('''
    # This is <pip-setuptools-caller> -- a caller that pip uses to run setup.py
    #
    # - It imports setuptools before invoking setup.py, to enable projects that directly
    #   import from `distutils.core` to work with newer packaging standards.
    # - It provides a clear error message when setuptools is not installed.
    # - It sets `sys.argv[0]` to the underlying `setup.py`, when invoking `setup.py` so
    #   setuptools doesn't think the script is `-c`. This avoids the following warning:
    #     manifest_maker: standard file '-c' not found".
    # - It generates a shim setup.py, for handling setup.cfg-only projects.
    import os, sys, tokenize

    try:
        import setuptools
    except ImportError as error:
        print(
            "ERROR: Can not execute `setup.py` since setuptools is not available in "
            "the build environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    __file__ = %r
    sys.argv[0] = __file__

    if os.path.exists(__file__):
        filename = __file__
        with tokenize.open(__file__) as f:
            setup_py_code = f.read()
    else:
        filename = "<auto-generated setuptools caller>"
        setup_py_code = "from setuptools import setup; setup()"

    exec(compile(setup_py_code, filename, "exec"))
    ''' % ({!r},), "<pip-setuptools-caller>", "exec"))
    """
).rstrip()


def make_setuptools_shim_args(
    setup_py_path: str,
    global_options: Optional[Sequence[str]] = None,
    no_user_config: bool = False,
    unbuffered_output: bool = False,
) -> List[str]:
    """
    Get setuptools command arguments with shim wrapped setup file invocation.

    :param setup_py_path: The path to setup.py to be wrapped.
    :param global_options: Additional global options.
    :param no_user_config: If True, disables personal user configuration.
    :param unbuffered_output: If True, adds the unbuffered switch to the
     argument list.
    """
    args = [sys.executable]
    if unbuffered_output:
        args += ["-u"]
    args += ["-c", _SETUPTOOLS_SHIM.format(setup_py_path)]
    if global_options:
        args += global_options
    if no_user_config:
        args += ["--no-user-cfg"]
    return args


def make_setuptools_bdist_wheel_args(
    setup_py_path: str,
    global_options: Sequence[str],
    build_options: Sequence[str],
    destination_dir: str,
) -> List[str]:
    # NOTE: Eventually, we'd want to also -S to the flags here, when we're
    # isolating. Currently, it breaks Python in virtualenvs, because it
    # relies on site.py to find parts of the standard library outside the
    # virtualenv.
    args = make_setuptools_shim_args(
        setup_py_path, global_options=global_options, unbuffered_output=True
    )
    args += ["bdist_wheel", "-d", destination_dir]
    args += build_options
    return args


def make_setuptools_clean_args(
    setup_py_path: str,
    global_options: Sequence[str],
) -> List[str]:
    args = make_setuptools_shim_args(
        setup_py_path, global_options=global_options, unbuffered_output=True
    )
    args += ["clean", "--all"]
    return args


def make_setuptools_develop_args(
    setup_py_path: str,
    *,
    global_options: Sequence[str],
    no_user_config: bool,
    prefix: Optional[str],
    home: Optional[str],
    use_user_site: bool,
) -> List[str]:
    assert not (use_user_site and prefix)

    args = make_setuptools_shim_args(
        setup_py_path,
        global_options=global_options,
        no_user_config=no_user_config,
    )

    args += ["develop", "--no-deps"]

    if prefix:
        args += ["--prefix", prefix]
    if home is not None:
        args += ["--install-dir", home]

    if use_user_site:
        args += ["--user", "--prefix="]

    return args


def make_setuptools_egg_info_args(
    setup_py_path: str,
    egg_info_dir: Optional[str],
    no_user_config: bool,
) -> List[str]:
    args = make_setuptools_shim_args(setup_py_path, no_user_config=no_user_config)

    args += ["egg_info"]

    if egg_info_dir:
        args += ["--egg-base", egg_info_dir]

    return args

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\cachecontrol\serialize.py ===
# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import io
from typing import IO, TYPE_CHECKING, Any, Mapping, cast

from pip._vendor import msgpack
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.urllib3 import HTTPResponse

if TYPE_CHECKING:
    from pip._vendor.requests import PreparedRequest


class Serializer:
    serde_version = "4"

    def dumps(
        self,
        request: PreparedRequest,
        response: HTTPResponse,
        body: bytes | None = None,
    ) -> bytes:
        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if body is None:
            # When a body isn't passed in, we'll read the response. We
            # also update the response with a new file handler to be
            # sure it acts as though it was never read.
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)  # type: ignore[assignment]
            response.length_remaining = len(body)

        data = {
            "response": {
                "body": body,  # Empty bytestring if body is stored separately
                "headers": {str(k): str(v) for k, v in response.headers.items()},
                "status": response.status,
                "version": response.version,
                "reason": str(response.reason),
                "decode_content": response.decode_content,
            }
        }

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers["vary"].split(",")
            for header in varied_headers:
                header = str(header).strip()
                header_value = request.headers.get(header, None)
                if header_value is not None:
                    header_value = str(header_value)
                data["vary"][header] = header_value

        return b",".join([f"cc={self.serde_version}".encode(), self.serialize(data)])

    def serialize(self, data: dict[str, Any]) -> bytes:
        return cast(bytes, msgpack.dumps(data, use_bin_type=True))

    def loads(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        # Short circuit if we've been given an empty set of data
        if not data:
            return None

        # Previous versions of this library supported other serialization
        # formats, but these have all been removed.
        if not data.startswith(f"cc={self.serde_version},".encode()):
            return None

        data = data[5:]
        return self._loads_v4(request, data, body_file)

    def prepare_response(
        self,
        request: PreparedRequest,
        cached: Mapping[str, Any],
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        """Verify our vary headers match and construct a real urllib3
        HTTPResponse object.
        """
        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        # This case is also handled in the controller code when creating
        # a cache entry, but is left here for backwards compatibility.
        if "*" in cached.get("vary", {}):
            return None

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return None

        body_raw = cached["response"].pop("body")

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            data=cached["response"]["headers"]
        )
        if headers.get("transfer-encoding", "") == "chunked":
            headers.pop("transfer-encoding")

        cached["response"]["headers"] = headers

        try:
            body: IO[bytes]
            if body_file is None:
                body = io.BytesIO(body_raw)
            else:
                body = body_file
        except TypeError:
            # This can happen if cachecontrol serialized to v1 format (pickle)
            # using Python 2. A Python 2 str(byte string) will be unpickled as
            # a Python 3 str (unicode string), which will cause the above to
            # fail with:
            #
            #     TypeError: 'str' does not support the buffer interface
            body = io.BytesIO(body_raw.encode("utf8"))

        # Discard any `strict` parameter serialized by older version of cachecontrol.
        cached["response"].pop("strict", None)

        return HTTPResponse(body=body, preload_content=False, **cached["response"])

    def _loads_v4(
        self,
        request: PreparedRequest,
        data: bytes,
        body_file: IO[bytes] | None = None,
    ) -> HTTPResponse | None:
        try:
            cached = msgpack.loads(data, raw=False)
        except ValueError:
            return None

        return self.prepare_response(request, cached, body_file)

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\dialogs\list.py ===
import commctrl
import win32api
import win32con
import win32ui
from pywin.mfc import dialog


class ListDialog(dialog.Dialog):
    def __init__(self, title, list):
        dialog.Dialog.__init__(self, self._maketemplate(title))
        self.HookMessage(self.on_size, win32con.WM_SIZE)
        self.HookNotify(self.OnListItemChange, commctrl.LVN_ITEMCHANGED)
        self.HookCommand(self.OnListClick, win32ui.IDC_LIST1)
        self.items = list

    def _maketemplate(self, title):
        style = win32con.WS_DLGFRAME | win32con.WS_SYSMENU | win32con.WS_VISIBLE
        ls = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | commctrl.LVS_ALIGNLEFT
            | commctrl.LVS_REPORT
        )
        bs = win32con.WS_CHILD | win32con.WS_VISIBLE
        return [
            [title, (0, 0, 200, 200), style, None, (8, "MS Sans Serif")],
            ["SysListView32", None, win32ui.IDC_LIST1, (0, 0, 200, 200), ls],
            [128, "OK", win32con.IDOK, (10, 0, 50, 14), bs | win32con.BS_DEFPUSHBUTTON],
            [128, "Cancel", win32con.IDCANCEL, (0, 0, 50, 14), bs],
        ]

    def FillList(self):
        size = self.GetWindowRect()
        width = size[2] - size[0] - (10)
        itemDetails = (commctrl.LVCFMT_LEFT, width, "Item", 0)
        self.itemsControl.InsertColumn(0, itemDetails)
        index = 0
        for item in self.items:
            index = self.itemsControl.InsertItem(index + 1, str(item), 0)

    def OnListClick(self, id, code):
        if code == commctrl.NM_DBLCLK:
            self.EndDialog(win32con.IDOK)
        return 1

    def OnListItemChange(self, std, extra):
        (
            (hwndFrom, idFrom, code),
            (
                itemNotify,
                sub,
                newState,
                oldState,
                change,
                point,
                lparam,
            ),
        ) = (std, extra)
        oldSel = (oldState & commctrl.LVIS_SELECTED) != 0
        newSel = (newState & commctrl.LVIS_SELECTED) != 0
        if oldSel != newSel:
            try:
                self.selecteditem = itemNotify
                self.butOK.EnableWindow(1)
            except win32ui.error:
                self.selecteditem = None

    def OnInitDialog(self):
        rc = dialog.Dialog.OnInitDialog(self)
        self.itemsControl = self.GetDlgItem(win32ui.IDC_LIST1)
        self.butOK = self.GetDlgItem(win32con.IDOK)
        self.butCancel = self.GetDlgItem(win32con.IDCANCEL)

        self.FillList()

        size = self.GetWindowRect()
        self.LayoutControls(size[2] - size[0], size[3] - size[1])
        self.butOK.EnableWindow(0)  # wait for first selection
        return rc

    def LayoutControls(self, w, h):
        self.itemsControl.MoveWindow((0, 0, w, h - 30))
        self.butCancel.MoveWindow((10, h - 24, 60, h - 4))
        self.butOK.MoveWindow((w - 60, h - 24, w - 10, h - 4))

    def on_size(self, params):
        lparam = params[3]
        w = win32api.LOWORD(lparam)
        h = win32api.HIWORD(lparam)
        self.LayoutControls(w, h)


class ListsDialog(ListDialog):
    def __init__(self, title, list, colHeadings=["Item"]):
        ListDialog.__init__(self, title, list)
        self.colHeadings = colHeadings

    def FillList(self):
        index = 0
        size = self.GetWindowRect()
        width = (
            size[2] - size[0] - (10) - win32api.GetSystemMetrics(win32con.SM_CXVSCROLL)
        )
        numCols = len(self.colHeadings)

        for col in self.colHeadings:
            itemDetails = (commctrl.LVCFMT_LEFT, int(width / numCols), col, 0)
            self.itemsControl.InsertColumn(index, itemDetails)
            index += 1
        index = 0
        for items in self.items:
            index = self.itemsControl.InsertItem(index + 1, str(items[0]), 0)
            for itemno in range(1, numCols):
                item = items[itemno]
                self.itemsControl.SetItemText(index, itemno, str(item))


def SelectFromList(title, lst):
    dlg = ListDialog(title, lst)
    if dlg.DoModal() == win32con.IDOK:
        return dlg.selecteditem
    else:
        return None


def SelectFromLists(title, lists, headings):
    dlg = ListsDialog(title, lists, headings)
    if dlg.DoModal() == win32con.IDOK:
        return dlg.selecteditem
    else:
        return None


def test():
    # 	print SelectFromList('Single list',  [1,2,3])
    print(
        SelectFromLists(
            "Multi-List",
            [("1", 1, "a"), ("2", 2, "b"), ("3", 3, "c")],
            ["Col 1", "Col 2"],
        )
    )


if __name__ == "__main__":
    test()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\packaging\licenses\__init__.py ===
#######################################################################################
#
# Adapted from:
#  https://github.com/pypa/hatch/blob/5352e44/backend/src/hatchling/licenses/parse.py
#
# MIT License
#
# Copyright (c) 2017-present Ofek Lev <oss@ofek.dev>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# With additional allowance of arbitrary `LicenseRef-` identifiers, not just
# `LicenseRef-Public-Domain` and `LicenseRef-Proprietary`.
#
#######################################################################################
from __future__ import annotations

import re
from typing import NewType, cast

from pip._vendor.packaging.licenses._spdx import EXCEPTIONS, LICENSES

__all__ = [
    "NormalizedLicenseExpression",
    "InvalidLicenseExpression",
    "canonicalize_license_expression",
]

license_ref_allowed = re.compile("^[A-Za-z0-9.-]*$")

NormalizedLicenseExpression = NewType("NormalizedLicenseExpression", str)


class InvalidLicenseExpression(ValueError):
    """Raised when a license-expression string is invalid

    >>> canonicalize_license_expression("invalid")
    Traceback (most recent call last):
        ...
    packaging.licenses.InvalidLicenseExpression: Invalid license expression: 'invalid'
    """


def canonicalize_license_expression(
    raw_license_expression: str,
) -> NormalizedLicenseExpression:
    if not raw_license_expression:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message)

    # Pad any parentheses so tokenization can be achieved by merely splitting on
    # whitespace.
    license_expression = raw_license_expression.replace("(", " ( ").replace(")", " ) ")
    licenseref_prefix = "LicenseRef-"
    license_refs = {
        ref.lower(): "LicenseRef-" + ref[len(licenseref_prefix) :]
        for ref in license_expression.split()
        if ref.lower().startswith(licenseref_prefix.lower())
    }

    # Normalize to lower case so we can look up licenses/exceptions
    # and so boolean operators are Python-compatible.
    license_expression = license_expression.lower()

    tokens = license_expression.split()

    # Rather than implementing boolean logic, we create an expression that Python can
    # parse. Everything that is not involved with the grammar itself is treated as
    # `False` and the expression should evaluate as such.
    python_tokens = []
    for token in tokens:
        if token not in {"or", "and", "with", "(", ")"}:
            python_tokens.append("False")
        elif token == "with":
            python_tokens.append("or")
        elif token == "(" and python_tokens and python_tokens[-1] not in {"or", "and"}:
            message = f"Invalid license expression: {raw_license_expression!r}"
            raise InvalidLicenseExpression(message)
        else:
            python_tokens.append(token)

    python_expression = " ".join(python_tokens)
    try:
        invalid = eval(python_expression, globals(), locals())
    except Exception:
        invalid = True

    if invalid is not False:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message) from None

    # Take a final pass to check for unknown licenses/exceptions.
    normalized_tokens = []
    for token in tokens:
        if token in {"or", "and", "with", "(", ")"}:
            normalized_tokens.append(token.upper())
            continue

        if normalized_tokens and normalized_tokens[-1] == "WITH":
            if token not in EXCEPTIONS:
                message = f"Unknown license exception: {token!r}"
                raise InvalidLicenseExpression(message)

            normalized_tokens.append(EXCEPTIONS[token]["id"])
        else:
            if token.endswith("+"):
                final_token = token[:-1]
                suffix = "+"
            else:
                final_token = token
                suffix = ""

            if final_token.startswith("licenseref-"):
                if not license_ref_allowed.match(final_token):
                    message = f"Invalid licenseref: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(license_refs[final_token] + suffix)
            else:
                if final_token not in LICENSES:
                    message = f"Unknown license: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(LICENSES[final_token]["id"] + suffix)

    normalized_expression = " ".join(normalized_tokens)

    return cast(
        NormalizedLicenseExpression,
        normalized_expression.replace("( ", "(").replace(" )", ")"),
    )

# === NexusCore/openenv\Lib\site-packages\h11\_writers.py ===
# Code to read HTTP data
#
# Strategy: each writer takes an event + a write-some-bytes function, which is
# calls.
#
# WRITERS is a dict describing how to pick a reader. It maps states to either:
# - a writer
# - or, for body writers, a dict of framin-dependent writer factories

from typing import Any, Callable, Dict, List, Tuple, Type, Union

from ._events import Data, EndOfMessage, Event, InformationalResponse, Request, Response
from ._headers import Headers
from ._state import CLIENT, IDLE, SEND_BODY, SEND_RESPONSE, SERVER
from ._util import LocalProtocolError, Sentinel

__all__ = ["WRITERS"]

Writer = Callable[[bytes], Any]


def write_headers(headers: Headers, write: Writer) -> None:
    # "Since the Host field-value is critical information for handling a
    # request, a user agent SHOULD generate Host as the first header field
    # following the request-line." - RFC 7230
    raw_items = headers._full_items
    for raw_name, name, value in raw_items:
        if name == b"host":
            write(b"%s: %s\r\n" % (raw_name, value))
    for raw_name, name, value in raw_items:
        if name != b"host":
            write(b"%s: %s\r\n" % (raw_name, value))
    write(b"\r\n")


def write_request(request: Request, write: Writer) -> None:
    if request.http_version != b"1.1":
        raise LocalProtocolError("I only send HTTP/1.1")
    write(b"%s %s HTTP/1.1\r\n" % (request.method, request.target))
    write_headers(request.headers, write)


# Shared between InformationalResponse and Response
def write_any_response(
    response: Union[InformationalResponse, Response], write: Writer
) -> None:
    if response.http_version != b"1.1":
        raise LocalProtocolError("I only send HTTP/1.1")
    status_bytes = str(response.status_code).encode("ascii")
    # We don't bother sending ascii status messages like "OK"; they're
    # optional and ignored by the protocol. (But the space after the numeric
    # status code is mandatory.)
    #
    # XX FIXME: could at least make an effort to pull out the status message
    # from stdlib's http.HTTPStatus table. Or maybe just steal their enums
    # (either by import or copy/paste). We already accept them as status codes
    # since they're of type IntEnum < int.
    write(b"HTTP/1.1 %s %s\r\n" % (status_bytes, response.reason))
    write_headers(response.headers, write)


class BodyWriter:
    def __call__(self, event: Event, write: Writer) -> None:
        if type(event) is Data:
            self.send_data(event.data, write)
        elif type(event) is EndOfMessage:
            self.send_eom(event.headers, write)
        else:  # pragma: no cover
            assert False

    def send_data(self, data: bytes, write: Writer) -> None:
        pass

    def send_eom(self, headers: Headers, write: Writer) -> None:
        pass


#
# These are all careful not to do anything to 'data' except call len(data) and
# write(data). This allows us to transparently pass-through funny objects,
# like placeholder objects referring to files on disk that will be sent via
# sendfile(2).
#
class ContentLengthWriter(BodyWriter):
    def __init__(self, length: int) -> None:
        self._length = length

    def send_data(self, data: bytes, write: Writer) -> None:
        self._length -= len(data)
        if self._length < 0:
            raise LocalProtocolError("Too much data for declared Content-Length")
        write(data)

    def send_eom(self, headers: Headers, write: Writer) -> None:
        if self._length != 0:
            raise LocalProtocolError("Too little data for declared Content-Length")
        if headers:
            raise LocalProtocolError("Content-Length and trailers don't mix")


class ChunkedWriter(BodyWriter):
    def send_data(self, data: bytes, write: Writer) -> None:
        # if we encoded 0-length data in the naive way, it would look like an
        # end-of-message.
        if not data:
            return
        write(b"%x\r\n" % len(data))
        write(data)
        write(b"\r\n")

    def send_eom(self, headers: Headers, write: Writer) -> None:
        write(b"0\r\n")
        write_headers(headers, write)


class Http10Writer(BodyWriter):
    def send_data(self, data: bytes, write: Writer) -> None:
        write(data)

    def send_eom(self, headers: Headers, write: Writer) -> None:
        if headers:
            raise LocalProtocolError("can't send trailers to HTTP/1.0 client")
        # no need to close the socket ourselves, that will be taken care of by
        # Connection: close machinery


WritersType = Dict[
    Union[Tuple[Type[Sentinel], Type[Sentinel]], Type[Sentinel]],
    Union[
        Dict[str, Type[BodyWriter]],
        Callable[[Union[InformationalResponse, Response], Writer], None],
        Callable[[Request, Writer], None],
    ],
]

WRITERS: WritersType = {
    (CLIENT, IDLE): write_request,
    (SERVER, IDLE): write_any_response,
    (SERVER, SEND_RESPONSE): write_any_response,
    SEND_BODY: {
        "chunked": ChunkedWriter,
        "content-length": ContentLengthWriter,
        "http/1.0": Http10Writer,
    },
}

# === NexusCore/openenv\Lib\site-packages\PIL\SunImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# Sun image file handling
#
# History:
# 1995-09-10 fl   Created
# 1996-05-28 fl   Fixed 32-bit alignment
# 1998-12-29 fl   Import ImagePalette module
# 2001-12-18 fl   Fixed palette loading (from Jean-Claude Rimbault)
#
# Copyright (c) 1997-2001 by Secret Labs AB
# Copyright (c) 1995-1996 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

from . import Image, ImageFile, ImagePalette
from ._binary import i32be as i32


def _accept(prefix: bytes) -> bool:
    return len(prefix) >= 4 and i32(prefix) == 0x59A66A95


##
# Image plugin for Sun raster files.


class SunImageFile(ImageFile.ImageFile):
    format = "SUN"
    format_description = "Sun Raster File"

    def _open(self) -> None:
        # The Sun Raster file header is 32 bytes in length
        # and has the following format:

        #     typedef struct _SunRaster
        #     {
        #         DWORD MagicNumber;      /* Magic (identification) number */
        #         DWORD Width;            /* Width of image in pixels */
        #         DWORD Height;           /* Height of image in pixels */
        #         DWORD Depth;            /* Number of bits per pixel */
        #         DWORD Length;           /* Size of image data in bytes */
        #         DWORD Type;             /* Type of raster file */
        #         DWORD ColorMapType;     /* Type of color map */
        #         DWORD ColorMapLength;   /* Size of the color map in bytes */
        #     } SUNRASTER;

        assert self.fp is not None

        # HEAD
        s = self.fp.read(32)
        if not _accept(s):
            msg = "not an SUN raster file"
            raise SyntaxError(msg)

        offset = 32

        self._size = i32(s, 4), i32(s, 8)

        depth = i32(s, 12)
        # data_length = i32(s, 16)   # unreliable, ignore.
        file_type = i32(s, 20)
        palette_type = i32(s, 24)  # 0: None, 1: RGB, 2: Raw/arbitrary
        palette_length = i32(s, 28)

        if depth == 1:
            self._mode, rawmode = "1", "1;I"
        elif depth == 4:
            self._mode, rawmode = "L", "L;4"
        elif depth == 8:
            self._mode = rawmode = "L"
        elif depth == 24:
            if file_type == 3:
                self._mode, rawmode = "RGB", "RGB"
            else:
                self._mode, rawmode = "RGB", "BGR"
        elif depth == 32:
            if file_type == 3:
                self._mode, rawmode = "RGB", "RGBX"
            else:
                self._mode, rawmode = "RGB", "BGRX"
        else:
            msg = "Unsupported Mode/Bit Depth"
            raise SyntaxError(msg)

        if palette_length:
            if palette_length > 1024:
                msg = "Unsupported Color Palette Length"
                raise SyntaxError(msg)

            if palette_type != 1:
                msg = "Unsupported Palette Type"
                raise SyntaxError(msg)

            offset = offset + palette_length
            self.palette = ImagePalette.raw("RGB;L", self.fp.read(palette_length))
            if self.mode == "L":
                self._mode = "P"
                rawmode = rawmode.replace("L", "P")

        # 16 bit boundaries on stride
        stride = ((self.size[0] * depth + 15) // 16) * 2

        # file type: Type is the version (or flavor) of the bitmap
        # file. The following values are typically found in the Type
        # field:
        # 0000h Old
        # 0001h Standard
        # 0002h Byte-encoded
        # 0003h RGB format
        # 0004h TIFF format
        # 0005h IFF format
        # FFFFh Experimental

        # Old and standard are the same, except for the length tag.
        # byte-encoded is run-length-encoded
        # RGB looks similar to standard, but RGB byte order
        # TIFF and IFF mean that they were converted from T/IFF
        # Experimental means that it's something else.
        # (https://www.fileformat.info/format/sunraster/egff.htm)

        if file_type in (0, 1, 3, 4, 5):
            self.tile = [
                ImageFile._Tile("raw", (0, 0) + self.size, offset, (rawmode, stride))
            ]
        elif file_type == 2:
            self.tile = [
                ImageFile._Tile("sun_rle", (0, 0) + self.size, offset, rawmode)
            ]
        else:
            msg = "Unsupported Sun Raster file type"
            raise SyntaxError(msg)


#
# registry


Image.register_open(SunImageFile.format, SunImageFile, _accept)

Image.register_extension(SunImageFile.format, ".ras")

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\file_service.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import file as gag_file

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "CreateFileRequest",
        "CreateFileResponse",
        "ListFilesRequest",
        "ListFilesResponse",
        "GetFileRequest",
        "DeleteFileRequest",
    },
)


class CreateFileRequest(proto.Message):
    r"""Request for ``CreateFile``.

    Attributes:
        file (google.ai.generativelanguage_v1beta.types.File):
            Optional. Metadata for the file to create.
    """

    file: gag_file.File = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_file.File,
    )


class CreateFileResponse(proto.Message):
    r"""Response for ``CreateFile``.

    Attributes:
        file (google.ai.generativelanguage_v1beta.types.File):
            Metadata for the created file.
    """

    file: gag_file.File = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_file.File,
    )


class ListFilesRequest(proto.Message):
    r"""Request for ``ListFiles``.

    Attributes:
        page_size (int):
            Optional. Maximum number of ``File``\ s to return per page.
            If unspecified, defaults to 10. Maximum ``page_size`` is
            100.
        page_token (str):
            Optional. A page token from a previous ``ListFiles`` call.
    """

    page_size: int = proto.Field(
        proto.INT32,
        number=1,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=3,
    )


class ListFilesResponse(proto.Message):
    r"""Response for ``ListFiles``.

    Attributes:
        files (MutableSequence[google.ai.generativelanguage_v1beta.types.File]):
            The list of ``File``\ s.
        next_page_token (str):
            A token that can be sent as a ``page_token`` into a
            subsequent ``ListFiles`` call.
    """

    @property
    def raw_page(self):
        return self

    files: MutableSequence[gag_file.File] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=gag_file.File,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class GetFileRequest(proto.Message):
    r"""Request for ``GetFile``.

    Attributes:
        name (str):
            Required. The name of the ``File`` to get. Example:
            ``files/abc-123``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class DeleteFileRequest(proto.Message):
    r"""Request for ``DeleteFile``.

    Attributes:
        name (str):
            Required. The name of the ``File`` to delete. Example:
            ``files/abc-123``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\googleapiclient\discovery_cache\file_cache.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""File based cache for the discovery document.

The cache is stored in a single file so that multiple processes can
share the same cache. It locks the file whenever accessing to the
file. When the cache content is corrupted, it will be initialized with
an empty cache.
"""

from __future__ import division

import datetime
import json
import logging
import os
import tempfile

try:
    from oauth2client.contrib.locked_file import LockedFile
except ImportError:
    # oauth2client < 2.0.0
    try:
        from oauth2client.locked_file import LockedFile
    except ImportError:
        # oauth2client > 4.0.0 or google-auth
        raise ImportError(
            "file_cache is unavailable when using oauth2client >= 4.0.0 or google-auth"
        )

from . import base
from ..discovery_cache import DISCOVERY_DOC_MAX_AGE

LOGGER = logging.getLogger(__name__)

FILENAME = "google-api-python-client-discovery-doc.cache"
EPOCH = datetime.datetime(1970, 1, 1)


def _to_timestamp(date):
    try:
        return (date - EPOCH).total_seconds()
    except AttributeError:
        # The following is the equivalent of total_seconds() in Python2.6.
        # See also: https://docs.python.org/2/library/datetime.html
        delta = date - EPOCH
        return (
            delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6
        ) / 10**6


def _read_or_initialize_cache(f):
    f.file_handle().seek(0)
    try:
        cache = json.load(f.file_handle())
    except Exception:
        # This means it opens the file for the first time, or the cache is
        # corrupted, so initializing the file with an empty dict.
        cache = {}
        f.file_handle().truncate(0)
        f.file_handle().seek(0)
        json.dump(cache, f.file_handle())
    return cache


class Cache(base.Cache):
    """A file based cache for the discovery documents."""

    def __init__(self, max_age):
        """Constructor.

        Args:
          max_age: Cache expiration in seconds.
        """
        self._max_age = max_age
        self._file = os.path.join(tempfile.gettempdir(), FILENAME)
        f = LockedFile(self._file, "a+", "r")
        try:
            f.open_and_lock()
            if f.is_locked():
                _read_or_initialize_cache(f)
            # If we can not obtain the lock, other process or thread must
            # have initialized the file.
        except Exception as e:
            LOGGER.warning(e, exc_info=True)
        finally:
            f.unlock_and_close()

    def get(self, url):
        f = LockedFile(self._file, "r+", "r")
        try:
            f.open_and_lock()
            if f.is_locked():
                cache = _read_or_initialize_cache(f)
                if url in cache:
                    content, t = cache.get(url, (None, 0))
                    if _to_timestamp(datetime.datetime.now()) < t + self._max_age:
                        return content
                return None
            else:
                LOGGER.debug("Could not obtain a lock for the cache file.")
                return None
        except Exception as e:
            LOGGER.warning(e, exc_info=True)
        finally:
            f.unlock_and_close()

    def set(self, url, content):
        f = LockedFile(self._file, "r+", "r")
        try:
            f.open_and_lock()
            if f.is_locked():
                cache = _read_or_initialize_cache(f)
                cache[url] = (content, _to_timestamp(datetime.datetime.now()))
                # Remove stale cache.
                for k, (_, timestamp) in list(cache.items()):
                    if (
                        _to_timestamp(datetime.datetime.now())
                        >= timestamp + self._max_age
                    ):
                        del cache[k]
                f.file_handle().truncate(0)
                f.file_handle().seek(0)
                json.dump(cache, f.file_handle())
            else:
                LOGGER.debug("Could not obtain a lock for the cache file.")
        except Exception as e:
            LOGGER.warning(e, exc_info=True)
        finally:
            f.unlock_and_close()


cache = Cache(max_age=DISCOVERY_DOC_MAX_AGE)

# === NexusCore/openenv\Lib\site-packages\IPython\core\splitinput.py ===
# encoding: utf-8
"""
Simple utility for splitting user input. This is used by both inputsplitter and
prefilter.

Authors:

* Brian Granger
* Fernando Perez
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

import re
import sys

from IPython.utils import py3compat
from IPython.utils.encoding import get_stream_enc
from IPython.core.oinspect import OInfo

#-----------------------------------------------------------------------------
# Main function
#-----------------------------------------------------------------------------

# RegExp for splitting line contents into pre-char//first word-method//rest.
# For clarity, each group in on one line.

# WARNING: update the regexp if the escapes in interactiveshell are changed, as
# they are hardwired in.

# Although it's not solely driven by the regex, note that:
# ,;/% only trigger if they are the first character on the line
# ! and !! trigger if they are first char(s) *or* follow an indent
# ? triggers as first or last char.

line_split = re.compile(r"""
             ^(\s*)               # any leading space
             ([,;/%]|!!?|\?\??)?  # escape character or characters
             \s*(%{0,2}[\w\.\*]*)     # function/method, possibly with leading %
                                  # to correctly treat things like '?%magic'
             (.*?$|$)             # rest of line
             """, re.VERBOSE)


def split_user_input(line, pattern=None):
    """Split user input into initial whitespace, escape character, function part
    and the rest.
    """
    # We need to ensure that the rest of this routine deals only with unicode
    encoding = get_stream_enc(sys.stdin, 'utf-8')
    line = py3compat.cast_unicode(line, encoding)

    if pattern is None:
        pattern = line_split
    match = pattern.match(line)
    if not match:
        # print("match failed for line '%s'" % line)
        try:
            ifun, the_rest = line.split(None,1)
        except ValueError:
            # print("split failed for line '%s'" % line)
            ifun, the_rest = line, u''
        pre = re.match(r'^(\s*)(.*)',line).groups()[0]
        esc = ""
    else:
        pre, esc, ifun, the_rest = match.groups()

    # print('line:<%s>' % line)  # dbg
    # print('pre <%s> ifun <%s> rest <%s>' % (pre,ifun.strip(),the_rest))  # dbg
    return pre, esc or "", ifun.strip(), the_rest


class LineInfo:
    """A single line of input and associated info.

    Includes the following as properties:

    line
      The original, raw line

    continue_prompt
      Is this line a continuation in a sequence of multiline input?

    pre
      Any leading whitespace.

    esc
      The escape character(s) in pre or the empty string if there isn't one.
      Note that '!!' and '??' are possible values for esc. Otherwise it will
      always be a single character.

    ifun
      The 'function part', which is basically the maximal initial sequence
      of valid python identifiers and the '.' character. This is what is
      checked for alias and magic transformations, used for auto-calling,
      etc. In contrast to Python identifiers, it may start with "%" and contain
      "*".

    the_rest
      Everything else on the line.

    raw_the_rest
      the_rest without whitespace stripped.
    """
    def __init__(self, line, continue_prompt=False):
        self.line            = line
        self.continue_prompt = continue_prompt
        self.pre, self.esc, self.ifun, self.raw_the_rest = split_user_input(line)
        self.the_rest = self.raw_the_rest.lstrip()

        self.pre_char       = self.pre.strip()
        if self.pre_char:
            self.pre_whitespace = '' # No whitespace allowed before esc chars
        else:
            self.pre_whitespace = self.pre

    def ofind(self, ip) -> OInfo:
        """Do a full, attribute-walking lookup of the ifun in the various
        namespaces for the given IPython InteractiveShell instance.

        Return a dict with keys: {found, obj, ospace, ismagic}

        Note: can cause state changes because of calling getattr, but should
        only be run if autocall is on and if the line hasn't matched any
        other, less dangerous handlers.

        Does cache the results of the call, so can be called multiple times
        without worrying about *further* damaging state.
        """
        return ip._ofind(self.ifun)

    def __str__(self):
        return "LineInfo [%s|%s|%s|%s]" %(self.pre, self.esc, self.ifun, self.the_rest)

    def __repr__(self):
        return "<" + str(self) + ">"

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\__init__.py ===
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com> (minor additions)
# Contributors: matthewmc, clouds56
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
NLTK Tokenizer Package

Tokenizers divide strings into lists of substrings.  For example,
tokenizers can be used to find the words and punctuation in a string:

    >>> from nltk.tokenize import word_tokenize
    >>> s = '''Good muffins cost $3.88\nin New York.  Please buy me
    ... two of them.\n\nThanks.'''
    >>> word_tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.',
    'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']

This particular tokenizer requires the Punkt sentence tokenization
models to be installed. NLTK also provides a simpler,
regular-expression based tokenizer, which splits text on whitespace
and punctuation:

    >>> from nltk.tokenize import wordpunct_tokenize
    >>> wordpunct_tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$', '3', '.', '88', 'in', 'New', 'York', '.',
    'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']

We can also operate at the level of sentences, using the sentence
tokenizer directly as follows:

    >>> from nltk.tokenize import sent_tokenize, word_tokenize
    >>> sent_tokenize(s)
    ['Good muffins cost $3.88\nin New York.', 'Please buy me\ntwo of them.', 'Thanks.']
    >>> [word_tokenize(t) for t in sent_tokenize(s)] # doctest: +NORMALIZE_WHITESPACE
    [['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.'],
    ['Please', 'buy', 'me', 'two', 'of', 'them', '.'], ['Thanks', '.']]

Caution: when tokenizing a Unicode string, make sure you are not
using an encoded version of the string (it may be necessary to
decode it first, e.g. with ``s.decode("utf8")``.

NLTK tokenizers can produce token-spans, represented as tuples of integers
having the same semantics as string slices, to support efficient comparison
of tokenizers.  (These methods are implemented as generators.)

    >>> from nltk.tokenize import WhitespaceTokenizer
    >>> list(WhitespaceTokenizer().span_tokenize(s)) # doctest: +NORMALIZE_WHITESPACE
    [(0, 4), (5, 12), (13, 17), (18, 23), (24, 26), (27, 30), (31, 36), (38, 44),
    (45, 48), (49, 51), (52, 55), (56, 58), (59, 64), (66, 73)]

There are numerous ways to tokenize text.  If you need more control over
tokenization, see the other methods provided in this package.

For further information, please see Chapter 3 of the NLTK book.
"""

import functools
import re

from nltk.data import load
from nltk.tokenize.casual import TweetTokenizer, casual_tokenize
from nltk.tokenize.destructive import NLTKWordTokenizer
from nltk.tokenize.legality_principle import LegalitySyllableTokenizer
from nltk.tokenize.mwe import MWETokenizer
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktTokenizer
from nltk.tokenize.regexp import (
    BlanklineTokenizer,
    RegexpTokenizer,
    WhitespaceTokenizer,
    WordPunctTokenizer,
    blankline_tokenize,
    regexp_tokenize,
    wordpunct_tokenize,
)
from nltk.tokenize.repp import ReppTokenizer
from nltk.tokenize.sexpr import SExprTokenizer, sexpr_tokenize
from nltk.tokenize.simple import (
    LineTokenizer,
    SpaceTokenizer,
    TabTokenizer,
    line_tokenize,
)
from nltk.tokenize.sonority_sequencing import SyllableTokenizer
from nltk.tokenize.stanford_segmenter import StanfordSegmenter
from nltk.tokenize.texttiling import TextTilingTokenizer
from nltk.tokenize.toktok import ToktokTokenizer
from nltk.tokenize.treebank import TreebankWordDetokenizer, TreebankWordTokenizer
from nltk.tokenize.util import regexp_span_tokenize, string_span_tokenize


@functools.lru_cache
def _get_punkt_tokenizer(language="english"):
    """
    A constructor for the PunktTokenizer that utilizes
    a lru cache for performance.

    :param language: the model name in the Punkt corpus
    :type language: str
    """
    return PunktTokenizer(language)


# Standard sentence tokenizer.
def sent_tokenize(text, language="english"):
    """
    Return a sentence-tokenized copy of *text*,
    using NLTK's recommended sentence tokenizer
    (currently :class:`.PunktSentenceTokenizer`
    for the specified language).

    :param text: text to split into sentences
    :param language: the model name in the Punkt corpus
    """
    tokenizer = _get_punkt_tokenizer(language)
    return tokenizer.tokenize(text)


# Standard word tokenizer.
_treebank_word_tokenizer = NLTKWordTokenizer()


def word_tokenize(text, language="english", preserve_line=False):
    """
    Return a tokenized copy of *text*,
    using NLTK's recommended word tokenizer
    (currently an improved :class:`.TreebankWordTokenizer`
    along with :class:`.PunktSentenceTokenizer`
    for the specified language).

    :param text: text to split into words
    :type text: str
    :param language: the model name in the Punkt corpus
    :type language: str
    :param preserve_line: A flag to decide whether to sentence tokenize the text or not.
    :type preserve_line: bool
    """
    sentences = [text] if preserve_line else sent_tokenize(text, language)
    return [
        token for sent in sentences for token in _treebank_word_tokenizer.tokenize(sent)
    ]

# === NexusCore/openenv\Lib\site-packages\nltk\twitter\api.py ===
# Natural Language Toolkit: Twitter API
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides an interface for TweetHandlers, and support for timezone
handling.
"""

import time as _time
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta, timezone, tzinfo


class LocalTimezoneOffsetWithUTC(tzinfo):
    """
    This is not intended to be a general purpose class for dealing with the
    local timezone. In particular:

    * it assumes that the date passed has been created using
      `datetime(..., tzinfo=Local)`, where `Local` is an instance of
      the object `LocalTimezoneOffsetWithUTC`;
    * for such an object, it returns the offset with UTC, used for date comparisons.

    Reference: https://docs.python.org/3/library/datetime.html
    """

    STDOFFSET = timedelta(seconds=-_time.timezone)

    if _time.daylight:
        DSTOFFSET = timedelta(seconds=-_time.altzone)
    else:
        DSTOFFSET = STDOFFSET

    def utcoffset(self, dt):
        """
        Access the relevant time offset.
        """
        return self.DSTOFFSET


LOCAL = LocalTimezoneOffsetWithUTC()


class BasicTweetHandler(metaclass=ABCMeta):
    """
    Minimal implementation of `TweetHandler`.

    Counts the number of Tweets and decides when the client should stop
    fetching them.
    """

    def __init__(self, limit=20):
        self.limit = limit
        self.counter = 0

        """
        A flag to indicate to the client whether to stop fetching data given
        some condition (e.g., reaching a date limit).
        """
        self.do_stop = False

        """
        Stores the id of the last fetched Tweet to handle pagination.
        """
        self.max_id = None

    def do_continue(self):
        """
        Returns `False` if the client should stop fetching Tweets.
        """
        return self.counter < self.limit and not self.do_stop


class TweetHandlerI(BasicTweetHandler):
    """
    Interface class whose subclasses should implement a handle method that
    Twitter clients can delegate to.
    """

    def __init__(self, limit=20, upper_date_limit=None, lower_date_limit=None):
        """
        :param int limit: The number of data items to process in the current\
        round of processing.

        :param tuple upper_date_limit: The date at which to stop collecting\
        new data. This should be entered as a tuple which can serve as the\
        argument to `datetime.datetime`.\
        E.g. `date_limit=(2015, 4, 1, 12, 40)` for 12:30 pm on April 1 2015.

        :param tuple lower_date_limit: The date at which to stop collecting\
        new data. See `upper_data_limit` for formatting.
        """
        BasicTweetHandler.__init__(self, limit)

        self.upper_date_limit = None
        self.lower_date_limit = None
        if upper_date_limit:
            self.upper_date_limit = datetime(*upper_date_limit, tzinfo=LOCAL)
        if lower_date_limit:
            self.lower_date_limit = datetime(*lower_date_limit, tzinfo=LOCAL)

        self.startingup = True

    @abstractmethod
    def handle(self, data):
        """
        Deal appropriately with data returned by the Twitter API
        """

    @abstractmethod
    def on_finish(self):
        """
        Actions when the tweet limit has been reached
        """

    def check_date_limit(self, data, verbose=False):
        """
        Validate date limits.
        """
        if self.upper_date_limit or self.lower_date_limit:
            date_fmt = "%a %b %d %H:%M:%S +0000 %Y"
            tweet_date = datetime.strptime(data["created_at"], date_fmt).replace(
                tzinfo=timezone.utc
            )
            if (self.upper_date_limit and tweet_date > self.upper_date_limit) or (
                self.lower_date_limit and tweet_date < self.lower_date_limit
            ):
                if self.upper_date_limit:
                    message = "earlier"
                    date_limit = self.upper_date_limit
                else:
                    message = "later"
                    date_limit = self.lower_date_limit
                if verbose:
                    print(
                        "Date limit {} is {} than date of current tweet {}".format(
                            date_limit, message, tweet_date
                        )
                    )
                self.do_stop = True

# === NexusCore/openenv\Lib\site-packages\packaging\licenses\__init__.py ===
#######################################################################################
#
# Adapted from:
#  https://github.com/pypa/hatch/blob/5352e44/backend/src/hatchling/licenses/parse.py
#
# MIT License
#
# Copyright (c) 2017-present Ofek Lev <oss@ofek.dev>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# With additional allowance of arbitrary `LicenseRef-` identifiers, not just
# `LicenseRef-Public-Domain` and `LicenseRef-Proprietary`.
#
#######################################################################################
from __future__ import annotations

import re
from typing import NewType, cast

from packaging.licenses._spdx import EXCEPTIONS, LICENSES

__all__ = [
    "InvalidLicenseExpression",
    "NormalizedLicenseExpression",
    "canonicalize_license_expression",
]

license_ref_allowed = re.compile("^[A-Za-z0-9.-]*$")

NormalizedLicenseExpression = NewType("NormalizedLicenseExpression", str)


class InvalidLicenseExpression(ValueError):
    """Raised when a license-expression string is invalid

    >>> canonicalize_license_expression("invalid")
    Traceback (most recent call last):
        ...
    packaging.licenses.InvalidLicenseExpression: Invalid license expression: 'invalid'
    """


def canonicalize_license_expression(
    raw_license_expression: str,
) -> NormalizedLicenseExpression:
    if not raw_license_expression:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message)

    # Pad any parentheses so tokenization can be achieved by merely splitting on
    # whitespace.
    license_expression = raw_license_expression.replace("(", " ( ").replace(")", " ) ")
    licenseref_prefix = "LicenseRef-"
    license_refs = {
        ref.lower(): "LicenseRef-" + ref[len(licenseref_prefix) :]
        for ref in license_expression.split()
        if ref.lower().startswith(licenseref_prefix.lower())
    }

    # Normalize to lower case so we can look up licenses/exceptions
    # and so boolean operators are Python-compatible.
    license_expression = license_expression.lower()

    tokens = license_expression.split()

    # Rather than implementing boolean logic, we create an expression that Python can
    # parse. Everything that is not involved with the grammar itself is treated as
    # `False` and the expression should evaluate as such.
    python_tokens = []
    for token in tokens:
        if token not in {"or", "and", "with", "(", ")"}:
            python_tokens.append("False")
        elif token == "with":
            python_tokens.append("or")
        elif token == "(" and python_tokens and python_tokens[-1] not in {"or", "and"}:
            message = f"Invalid license expression: {raw_license_expression!r}"
            raise InvalidLicenseExpression(message)
        else:
            python_tokens.append(token)

    python_expression = " ".join(python_tokens)
    try:
        invalid = eval(python_expression, globals(), locals())
    except Exception:
        invalid = True

    if invalid is not False:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message) from None

    # Take a final pass to check for unknown licenses/exceptions.
    normalized_tokens = []
    for token in tokens:
        if token in {"or", "and", "with", "(", ")"}:
            normalized_tokens.append(token.upper())
            continue

        if normalized_tokens and normalized_tokens[-1] == "WITH":
            if token not in EXCEPTIONS:
                message = f"Unknown license exception: {token!r}"
                raise InvalidLicenseExpression(message)

            normalized_tokens.append(EXCEPTIONS[token]["id"])
        else:
            if token.endswith("+"):
                final_token = token[:-1]
                suffix = "+"
            else:
                final_token = token
                suffix = ""

            if final_token.startswith("licenseref-"):
                if not license_ref_allowed.match(final_token):
                    message = f"Invalid licenseref: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(license_refs[final_token] + suffix)
            else:
                if final_token not in LICENSES:
                    message = f"Unknown license: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(LICENSES[final_token]["id"] + suffix)

    normalized_expression = " ".join(normalized_tokens)

    return cast(
        NormalizedLicenseExpression,
        normalized_expression.replace("( ", "(").replace(" )", ")"),
    )

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\packaging\licenses\__init__.py ===
#######################################################################################
#
# Adapted from:
#  https://github.com/pypa/hatch/blob/5352e44/backend/src/hatchling/licenses/parse.py
#
# MIT License
#
# Copyright (c) 2017-present Ofek Lev <oss@ofek.dev>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# With additional allowance of arbitrary `LicenseRef-` identifiers, not just
# `LicenseRef-Public-Domain` and `LicenseRef-Proprietary`.
#
#######################################################################################
from __future__ import annotations

import re
from typing import NewType, cast

from pip._vendor.packaging.licenses._spdx import EXCEPTIONS, LICENSES

__all__ = [
    "NormalizedLicenseExpression",
    "InvalidLicenseExpression",
    "canonicalize_license_expression",
]

license_ref_allowed = re.compile("^[A-Za-z0-9.-]*$")

NormalizedLicenseExpression = NewType("NormalizedLicenseExpression", str)


class InvalidLicenseExpression(ValueError):
    """Raised when a license-expression string is invalid

    >>> canonicalize_license_expression("invalid")
    Traceback (most recent call last):
        ...
    packaging.licenses.InvalidLicenseExpression: Invalid license expression: 'invalid'
    """


def canonicalize_license_expression(
    raw_license_expression: str,
) -> NormalizedLicenseExpression:
    if not raw_license_expression:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message)

    # Pad any parentheses so tokenization can be achieved by merely splitting on
    # whitespace.
    license_expression = raw_license_expression.replace("(", " ( ").replace(")", " ) ")
    licenseref_prefix = "LicenseRef-"
    license_refs = {
        ref.lower(): "LicenseRef-" + ref[len(licenseref_prefix) :]
        for ref in license_expression.split()
        if ref.lower().startswith(licenseref_prefix.lower())
    }

    # Normalize to lower case so we can look up licenses/exceptions
    # and so boolean operators are Python-compatible.
    license_expression = license_expression.lower()

    tokens = license_expression.split()

    # Rather than implementing boolean logic, we create an expression that Python can
    # parse. Everything that is not involved with the grammar itself is treated as
    # `False` and the expression should evaluate as such.
    python_tokens = []
    for token in tokens:
        if token not in {"or", "and", "with", "(", ")"}:
            python_tokens.append("False")
        elif token == "with":
            python_tokens.append("or")
        elif token == "(" and python_tokens and python_tokens[-1] not in {"or", "and"}:
            message = f"Invalid license expression: {raw_license_expression!r}"
            raise InvalidLicenseExpression(message)
        else:
            python_tokens.append(token)

    python_expression = " ".join(python_tokens)
    try:
        invalid = eval(python_expression, globals(), locals())
    except Exception:
        invalid = True

    if invalid is not False:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message) from None

    # Take a final pass to check for unknown licenses/exceptions.
    normalized_tokens = []
    for token in tokens:
        if token in {"or", "and", "with", "(", ")"}:
            normalized_tokens.append(token.upper())
            continue

        if normalized_tokens and normalized_tokens[-1] == "WITH":
            if token not in EXCEPTIONS:
                message = f"Unknown license exception: {token!r}"
                raise InvalidLicenseExpression(message)

            normalized_tokens.append(EXCEPTIONS[token]["id"])
        else:
            if token.endswith("+"):
                final_token = token[:-1]
                suffix = "+"
            else:
                final_token = token
                suffix = ""

            if final_token.startswith("licenseref-"):
                if not license_ref_allowed.match(final_token):
                    message = f"Invalid licenseref: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(license_refs[final_token] + suffix)
            else:
                if final_token not in LICENSES:
                    message = f"Unknown license: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(LICENSES[final_token]["id"] + suffix)

    normalized_expression = " ".join(normalized_tokens)

    return cast(
        NormalizedLicenseExpression,
        normalized_expression.replace("( ", "(").replace(" )", ")"),
    )

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\formatted_text\html.py ===
from __future__ import annotations

import xml.dom.minidom as minidom
from string import Formatter
from typing import Any

from .base import FormattedText, StyleAndTextTuples

__all__ = ["HTML"]


class HTML:
    """
    HTML formatted text.
    Take something HTML-like, for use as a formatted string.

    ::

        # Turn something into red.
        HTML('<style fg="ansired" bg="#00ff44">...</style>')

        # Italic, bold, underline and strike.
        HTML('<i>...</i>')
        HTML('<b>...</b>')
        HTML('<u>...</u>')
        HTML('<s>...</s>')

    All HTML elements become available as a "class" in the style sheet.
    E.g. ``<username>...</username>`` can be styled, by setting a style for
    ``username``.
    """

    def __init__(self, value: str) -> None:
        self.value = value
        document = minidom.parseString(f"<html-root>{value}</html-root>")

        result: StyleAndTextTuples = []
        name_stack: list[str] = []
        fg_stack: list[str] = []
        bg_stack: list[str] = []

        def get_current_style() -> str:
            "Build style string for current node."
            parts = []
            if name_stack:
                parts.append("class:" + ",".join(name_stack))

            if fg_stack:
                parts.append("fg:" + fg_stack[-1])
            if bg_stack:
                parts.append("bg:" + bg_stack[-1])
            return " ".join(parts)

        def process_node(node: Any) -> None:
            "Process node recursively."
            for child in node.childNodes:
                if child.nodeType == child.TEXT_NODE:
                    result.append((get_current_style(), child.data))
                else:
                    add_to_name_stack = child.nodeName not in (
                        "#document",
                        "html-root",
                        "style",
                    )
                    fg = bg = ""

                    for k, v in child.attributes.items():
                        if k == "fg":
                            fg = v
                        if k == "bg":
                            bg = v
                        if k == "color":
                            fg = v  # Alias for 'fg'.

                    # Check for spaces in attributes. This would result in
                    # invalid style strings otherwise.
                    if " " in fg:
                        raise ValueError('"fg" attribute contains a space.')
                    if " " in bg:
                        raise ValueError('"bg" attribute contains a space.')

                    if add_to_name_stack:
                        name_stack.append(child.nodeName)
                    if fg:
                        fg_stack.append(fg)
                    if bg:
                        bg_stack.append(bg)

                    process_node(child)

                    if add_to_name_stack:
                        name_stack.pop()
                    if fg:
                        fg_stack.pop()
                    if bg:
                        bg_stack.pop()

        process_node(document)

        self.formatted_text = FormattedText(result)

    def __repr__(self) -> str:
        return f"HTML({self.value!r})"

    def __pt_formatted_text__(self) -> StyleAndTextTuples:
        return self.formatted_text

    def format(self, *args: object, **kwargs: object) -> HTML:
        """
        Like `str.format`, but make sure that the arguments are properly
        escaped.
        """
        return HTML(FORMATTER.vformat(self.value, args, kwargs))

    def __mod__(self, value: object) -> HTML:
        """
        HTML('<b>%s</b>') % value
        """
        if not isinstance(value, tuple):
            value = (value,)

        value = tuple(html_escape(i) for i in value)
        return HTML(self.value % value)


class HTMLFormatter(Formatter):
    def format_field(self, value: object, format_spec: str) -> str:
        return html_escape(format(value, format_spec))


def html_escape(text: object) -> str:
    # The string interpolation functions also take integers and other types.
    # Convert to string first.
    if not isinstance(text, str):
        text = f"{text}"

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


FORMATTER = HTMLFormatter()

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\urbi.py ===
"""
    pygments.lexers.urbi
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for UrbiScript language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import ExtendedRegexLexer, words
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation

__all__ = ['UrbiscriptLexer']


class UrbiscriptLexer(ExtendedRegexLexer):
    """
    For UrbiScript source code.
    """

    name = 'UrbiScript'
    aliases = ['urbiscript']
    filenames = ['*.u']
    mimetypes = ['application/x-urbiscript']
    url = 'https://github.com/urbiforge/urbi'
    version_added = '1.5'

    flags = re.DOTALL

    # TODO
    # - handle Experimental and deprecated tags with specific tokens
    # - handle Angles and Durations with specific tokens

    def blob_callback(lexer, match, ctx):
        text_before_blob = match.group(1)
        blob_start = match.group(2)
        blob_size_str = match.group(3)
        blob_size = int(blob_size_str)
        yield match.start(), String, text_before_blob
        ctx.pos += len(text_before_blob)

        # if blob size doesn't match blob format (example : "\B(2)(aaa)")
        # yield blob as a string
        if ctx.text[match.end() + blob_size] != ")":
            result = "\\B(" + blob_size_str + ")("
            yield match.start(), String, result
            ctx.pos += len(result)
            return

        # if blob is well formatted, yield as Escape
        blob_text = blob_start + ctx.text[match.end():match.end()+blob_size] + ")"
        yield match.start(), String.Escape, blob_text
        ctx.pos = match.end() + blob_size + 1  # +1 is the ending ")"

    tokens = {
        'root': [
            (r'\s+', Text),
            # comments
            (r'//.*?\n', Comment),
            (r'/\*', Comment.Multiline, 'comment'),
            (r'(every|for|loop|while)(?:;|&|\||,)', Keyword),
            (words((
                'assert', 'at', 'break', 'case', 'catch', 'closure', 'compl',
                'continue', 'default', 'else', 'enum', 'every', 'external',
                'finally', 'for', 'freezeif', 'if', 'new', 'onleave', 'return',
                'stopif', 'switch', 'this', 'throw', 'timeout', 'try',
                'waituntil', 'whenever', 'while'), suffix=r'\b'),
             Keyword),
            (words((
                'asm', 'auto', 'bool', 'char', 'const_cast', 'delete', 'double',
                'dynamic_cast', 'explicit', 'export', 'extern', 'float', 'friend',
                'goto', 'inline', 'int', 'long', 'mutable', 'namespace', 'register',
                'reinterpret_cast', 'short', 'signed', 'sizeof', 'static_cast',
                'struct', 'template', 'typedef', 'typeid', 'typename', 'union',
                'unsigned', 'using', 'virtual', 'volatile', 'wchar_t'), suffix=r'\b'),
             Keyword.Reserved),
            # deprecated keywords, use a meaningful token when available
            (r'(emit|foreach|internal|loopn|static)\b', Keyword),
            # ignored keywords, use a meaningful token when available
            (r'(private|protected|public)\b', Keyword),
            (r'(var|do|const|function|class)\b', Keyword.Declaration),
            (r'(true|false|nil|void)\b', Keyword.Constant),
            (words((
                'Barrier', 'Binary', 'Boolean', 'CallMessage', 'Channel', 'Code',
                'Comparable', 'Container', 'Control', 'Date', 'Dictionary', 'Directory',
                'Duration', 'Enumeration', 'Event', 'Exception', 'Executable', 'File',
                'Finalizable', 'Float', 'FormatInfo', 'Formatter', 'Global', 'Group',
                'Hash', 'InputStream', 'IoService', 'Job', 'Kernel', 'Lazy', 'List',
                'Loadable', 'Lobby', 'Location', 'Logger', 'Math', 'Mutex', 'nil',
                'Object', 'Orderable', 'OutputStream', 'Pair', 'Path', 'Pattern',
                'Position', 'Primitive', 'Process', 'Profile', 'PseudoLazy', 'PubSub',
                'RangeIterable', 'Regexp', 'Semaphore', 'Server', 'Singleton', 'Socket',
                'StackFrame', 'Stream', 'String', 'System', 'Tag', 'Timeout',
                'Traceable', 'TrajectoryGenerator', 'Triplet', 'Tuple', 'UObject',
                'UValue', 'UVar'), suffix=r'\b'),
             Name.Builtin),
            (r'(?:this)\b', Name.Builtin.Pseudo),
            # don't match single | and &
            (r'(?:[-=+*%/<>~^:]+|\.&?|\|\||&&)', Operator),
            (r'(?:and_eq|and|bitand|bitor|in|not|not_eq|or_eq|or|xor_eq|xor)\b',
             Operator.Word),
            (r'[{}\[\]()]+', Punctuation),
            (r'(?:;|\||,|&|\?|!)+', Punctuation),
            (r'[$a-zA-Z_]\w*', Name.Other),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            # Float, Integer, Angle and Duration
            (r'(?:[0-9]+(?:(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)?'
             r'((?:rad|deg|grad)|(?:ms|s|min|h|d))?)\b', Number.Float),
            # handle binary blob in strings
            (r'"', String.Double, "string.double"),
            (r"'", String.Single, "string.single"),
        ],
        'string.double': [
            (r'((?:\\\\|\\"|[^"])*?)(\\B\((\d+)\)\()', blob_callback),
            (r'(\\\\|\\[^\\]|[^"\\])*?"', String.Double, '#pop'),
        ],
        'string.single': [
            (r"((?:\\\\|\\'|[^'])*?)(\\B\((\d+)\)\()", blob_callback),
            (r"(\\\\|\\[^\\]|[^'\\])*?'", String.Single, '#pop'),
        ],
        # from http://pygments.org/docs/lexerdevelopment/#changing-states
        'comment': [
            (r'[^*/]', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ]
    }

    def analyse_text(text):
        """This is fairly similar to C and others, but freezeif and
        waituntil are unique keywords."""
        result = 0

        if 'freezeif' in text:
            result += 0.05

        if 'waituntil' in text:
            result += 0.05

        return result

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\Demos\dlgtest.py ===
# A Demo of Pythonwin's Dialog and Property Page support.

###################
#
# First demo - use the built-in to Pythonwin "Tab Stop" dialog, but
# customise it heavily.
#
# ID's for the tabstop dialog - out test.
#
import win32con
import win32ui
from pywin.mfc import dialog
from win32con import IDCANCEL
from win32ui import IDC_EDIT_TABS, IDC_PROMPT_TABS, IDD_SET_TABSTOPS


class TestDialog(dialog.Dialog):
    def __init__(self, modal=1):
        dialog.Dialog.__init__(self, IDD_SET_TABSTOPS)
        self.counter = 0
        if modal:
            self.DoModal()
        else:
            self.CreateWindow()

    def OnInitDialog(self):
        # Set the caption of the dialog itself.
        self.SetWindowText("Used to be Tab Stops!")
        # Get a child control, remember it, and change its text.
        self.edit = self.GetDlgItem(IDC_EDIT_TABS)  # the text box.
        self.edit.SetWindowText("Test")
        # Hook a Windows message for the dialog.
        self.edit.HookMessage(self.KillFocus, win32con.WM_KILLFOCUS)
        # Get the prompt control, and change its next.
        prompt = self.GetDlgItem(IDC_PROMPT_TABS)  # the prompt box.
        prompt.SetWindowText("Prompt")
        # And the same for the button..
        cancel = self.GetDlgItem(IDCANCEL)  # the cancel button
        cancel.SetWindowText("&Kill me")

        # And just for demonstration purposes, we hook the notify message for the dialog.
        # This allows us to be notified when the Edit Control text changes.
        self.HookCommand(self.OnNotify, IDC_EDIT_TABS)

    def OnNotify(self, controlid, code):
        if code == win32con.EN_CHANGE:
            print("Edit text changed!")
        return 1  # I handled this, so no need to call defaults!

    # kill focus for the edit box.
    # Simply increment the value in the text box.
    def KillFocus(self, msg):
        self.counter += 1
        if self.edit is not None:
            self.edit.SetWindowText(str(self.counter))

    # Called when the dialog box is terminating...
    def OnDestroy(self, msg):
        del self.edit
        del self.counter


# A very simply Property Sheet.
# We only make a new class for demonstration purposes.
class TestSheet(dialog.PropertySheet):
    def __init__(self, title):
        dialog.PropertySheet.__init__(self, title)
        self.HookMessage(self.OnActivate, win32con.WM_ACTIVATE)

    def OnActivate(self, msg):
        pass


# A very simply Property Page, which will be "owned" by the above
# Property Sheet.
# We create a new class, just so we can hook a control notification.
class TestPage(dialog.PropertyPage):
    def OnInitDialog(self):
        # We use the HookNotify function to allow Python to respond to
        # Windows WM_NOTIFY messages.
        # In this case, we are interested in BN_CLICKED messages.
        self.HookNotify(self.OnNotify, win32con.BN_CLICKED)

    def OnNotify(self, std, extra):
        print("OnNotify", std, extra)


# Some code that actually uses these objects.
def demo(modal=0):
    TestDialog(modal)

    # property sheet/page demo
    ps = win32ui.CreatePropertySheet("Property Sheet/Page Demo")
    # Create a completely standard PropertyPage.
    page1 = win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO1)
    # Create our custom property page.
    page2 = TestPage(win32ui.IDD_PROPDEMO2)
    ps.AddPage(page1)
    ps.AddPage(page2)
    if modal:
        ps.DoModal()
    else:
        style = (
            win32con.WS_SYSMENU
            | win32con.WS_POPUP
            | win32con.WS_CAPTION
            | win32con.DS_MODALFRAME
            | win32con.WS_VISIBLE
        )
        styleex = win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_PALETTEWINDOW
        ps.CreateWindow(win32ui.GetMainFrame(), style, styleex)


def test(modal=1):
    # 	dlg=dialog.Dialog(1010)
    # 	dlg.CreateWindow()
    # 	dlg.EndDialog(0)
    # 	del dlg
    # 	return
    # property sheet/page demo
    ps = TestSheet("Property Sheet/Page Demo")
    page1 = win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO1)
    page2 = win32ui.CreatePropertyPage(win32ui.IDD_PROPDEMO2)
    ps.AddPage(page1)
    ps.AddPage(page2)
    del page1
    del page2
    if modal:
        ps.DoModal()
    else:
        ps.CreateWindow(win32ui.GetMainFrame())
    return ps


def d():
    dlg = win32ui.CreateDialog(win32ui.IDD_DEBUGGER)
    dlg.datalist.append((win32ui.IDC_DBG_RADIOSTACK, "radio"))
    print("data list is ", dlg.datalist)
    dlg.data["radio"] = 1
    dlg.DoModal()
    print(dlg.data["radio"])


if __name__ == "__main__":
    demo(1)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\packaging\licenses\__init__.py ===
#######################################################################################
#
# Adapted from:
#  https://github.com/pypa/hatch/blob/5352e44/backend/src/hatchling/licenses/parse.py
#
# MIT License
#
# Copyright (c) 2017-present Ofek Lev <oss@ofek.dev>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#
# With additional allowance of arbitrary `LicenseRef-` identifiers, not just
# `LicenseRef-Public-Domain` and `LicenseRef-Proprietary`.
#
#######################################################################################
from __future__ import annotations

import re
from typing import NewType, cast

from packaging.licenses._spdx import EXCEPTIONS, LICENSES

__all__ = [
    "NormalizedLicenseExpression",
    "InvalidLicenseExpression",
    "canonicalize_license_expression",
]

license_ref_allowed = re.compile("^[A-Za-z0-9.-]*$")

NormalizedLicenseExpression = NewType("NormalizedLicenseExpression", str)


class InvalidLicenseExpression(ValueError):
    """Raised when a license-expression string is invalid

    >>> canonicalize_license_expression("invalid")
    Traceback (most recent call last):
        ...
    packaging.licenses.InvalidLicenseExpression: Invalid license expression: 'invalid'
    """


def canonicalize_license_expression(
    raw_license_expression: str,
) -> NormalizedLicenseExpression:
    if not raw_license_expression:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message)

    # Pad any parentheses so tokenization can be achieved by merely splitting on
    # whitespace.
    license_expression = raw_license_expression.replace("(", " ( ").replace(")", " ) ")
    licenseref_prefix = "LicenseRef-"
    license_refs = {
        ref.lower(): "LicenseRef-" + ref[len(licenseref_prefix) :]
        for ref in license_expression.split()
        if ref.lower().startswith(licenseref_prefix.lower())
    }

    # Normalize to lower case so we can look up licenses/exceptions
    # and so boolean operators are Python-compatible.
    license_expression = license_expression.lower()

    tokens = license_expression.split()

    # Rather than implementing boolean logic, we create an expression that Python can
    # parse. Everything that is not involved with the grammar itself is treated as
    # `False` and the expression should evaluate as such.
    python_tokens = []
    for token in tokens:
        if token not in {"or", "and", "with", "(", ")"}:
            python_tokens.append("False")
        elif token == "with":
            python_tokens.append("or")
        elif token == "(" and python_tokens and python_tokens[-1] not in {"or", "and"}:
            message = f"Invalid license expression: {raw_license_expression!r}"
            raise InvalidLicenseExpression(message)
        else:
            python_tokens.append(token)

    python_expression = " ".join(python_tokens)
    try:
        invalid = eval(python_expression, globals(), locals())
    except Exception:
        invalid = True

    if invalid is not False:
        message = f"Invalid license expression: {raw_license_expression!r}"
        raise InvalidLicenseExpression(message) from None

    # Take a final pass to check for unknown licenses/exceptions.
    normalized_tokens = []
    for token in tokens:
        if token in {"or", "and", "with", "(", ")"}:
            normalized_tokens.append(token.upper())
            continue

        if normalized_tokens and normalized_tokens[-1] == "WITH":
            if token not in EXCEPTIONS:
                message = f"Unknown license exception: {token!r}"
                raise InvalidLicenseExpression(message)

            normalized_tokens.append(EXCEPTIONS[token]["id"])
        else:
            if token.endswith("+"):
                final_token = token[:-1]
                suffix = "+"
            else:
                final_token = token
                suffix = ""

            if final_token.startswith("licenseref-"):
                if not license_ref_allowed.match(final_token):
                    message = f"Invalid licenseref: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(license_refs[final_token] + suffix)
            else:
                if final_token not in LICENSES:
                    message = f"Unknown license: {final_token!r}"
                    raise InvalidLicenseExpression(message)
                normalized_tokens.append(LICENSES[final_token]["id"] + suffix)

    normalized_expression = " ".join(normalized_tokens)

    return cast(
        NormalizedLicenseExpression,
        normalized_expression.replace("( ", "(").replace(" )", ")"),
    )

# === NexusCore/openenv\Lib\site-packages\win32comext\axscript\server\axsite.py ===
import pythoncom
import winerror
from win32com.axscript import axscript
from win32com.server import util
from win32com.server.exception import COMException


class AXEngine:
    def __init__(self, site, engine):
        self.eScript = self.eParse = self.eSafety = None
        if isinstance(engine, str):
            engine = pythoncom.CoCreateInstance(
                engine, None, pythoncom.CLSCTX_SERVER, pythoncom.IID_IUnknown
            )

        self.eScript = engine.QueryInterface(axscript.IID_IActiveScript)
        self.eParse = engine.QueryInterface(axscript.IID_IActiveScriptParse)
        self.eSafety = engine.QueryInterface(axscript.IID_IObjectSafety)

        self.eScript.SetScriptSite(site)
        self.eParse.InitNew()

    def __del__(self):
        self.Close()

    def GetScriptDispatch(self, name=None):
        return self.eScript.GetScriptDispatch(name)

    def AddNamedItem(self, item, flags):
        return self.eScript.AddNamedItem(item, flags)

    # Some helpers.
    def AddCode(self, code, flags=0):
        self.eParse.ParseScriptText(code, None, None, None, 0, 0, flags)

    def EvalCode(self, code):
        return self.eParse.ParseScriptText(
            code, None, None, None, 0, 0, axscript.SCRIPTTEXT_ISEXPRESSION
        )

    def Start(self):
        # Should maybe check state?
        # Do I need to transition through?
        self.eScript.SetScriptState(axscript.SCRIPTSTATE_STARTED)

    #    self.eScript.SetScriptState(axscript.SCRIPTSTATE_CONNECTED)

    def Close(self):
        if self.eScript:
            self.eScript.Close()
        self.eScript = self.eParse = self.eSafety = None

    def SetScriptState(self, state):
        self.eScript.SetScriptState(state)


IActiveScriptSite_methods = [
    "GetLCID",
    "GetItemInfo",
    "GetDocVersionString",
    "OnScriptTerminate",
    "OnStateChange",
    "OnScriptError",
    "OnEnterScript",
    "OnLeaveScript",
]


class AXSite:
    """An Active Scripting site.  A Site can have exactly one engine."""

    _public_methods_ = IActiveScriptSite_methods
    _com_interfaces_ = [axscript.IID_IActiveScriptSite]

    def __init__(self, objModel={}, engine=None, lcid=0):
        self.lcid = lcid
        self.objModel = {}
        for name, object in objModel.items():
            # Gregs code did str.lower this - I think that is callers job if he wants!
            self.objModel[name] = object

        self.engine = None
        if engine:
            self._AddEngine(engine)

    def AddEngine(self, engine):
        """Adds a new engine to the site.
        engine can be a string, or a fully wrapped engine object.
        """
        if isinstance(engine, str):
            newEngine = AXEngine(util.wrap(self), engine)
        else:
            newEngine = engine
        self.engine = newEngine
        flags = (
            axscript.SCRIPTITEM_ISVISIBLE
            | axscript.SCRIPTITEM_NOCODE
            | axscript.SCRIPTITEM_GLOBALMEMBERS
            | axscript.SCRIPTITEM_ISPERSISTENT
        )
        for name in self.objModel:
            newEngine.AddNamedItem(name, flags)
            newEngine.SetScriptState(axscript.SCRIPTSTATE_INITIALIZED)
        return newEngine

    # B/W compat
    _AddEngine = AddEngine

    def _Close(self):
        self.engine.Close()
        self.objModel = {}

    def GetLCID(self):
        return self.lcid

    def GetItemInfo(self, name, returnMask):
        if name not in self.objModel:
            raise COMException(
                scode=winerror.TYPE_E_ELEMENTNOTFOUND, desc="item not found"
            )

        ### for now, we don't have any type information

        if returnMask & axscript.SCRIPTINFO_IUNKNOWN:
            return (self.objModel[name], None)

        return (None, None)

    def GetDocVersionString(self):
        return "Python AXHost version 1.0"

    def OnScriptTerminate(self, result, excepInfo):
        pass

    def OnStateChange(self, state):
        pass

    def OnScriptError(self, errorInterface):
        return winerror.S_FALSE

    def OnEnterScript(self):
        pass

    def OnLeaveScript(self):
        pass

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\platformdirs\macos.py ===
"""macOS."""

from __future__ import annotations

import os.path
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from pathlib import Path


class MacOS(PlatformDirsABC):
    """
    Platform directories for the macOS operating system.

    Follows the guidance from
    `Apple documentation <https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/MacOSXDirectories/MacOSXDirectories.html>`_.
    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`,
    `version <platformdirs.api.PlatformDirsABC.version>`,
    `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``~/Library/Application Support/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Application Support"))  # noqa: PTH111

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directory shared by users, e.g. ``/Library/Application Support/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/share/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/share/$appname/$version:/Library/Application Support/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/share")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Application Support"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g. ``~/Library/Caches/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches"))  # noqa: PTH111

    @property
    def site_cache_dir(self) -> str:
        """
        :return: cache directory shared by users, e.g. ``/Library/Caches/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/var/cache/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/var/cache/$appname/$version:/Library/Caches/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/var/cache")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Caches"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, e.g. ``~/Library/Logs/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Logs"))  # noqa: PTH111

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return os.path.expanduser("~/Documents")  # noqa: PTH111

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return os.path.expanduser("~/Downloads")  # noqa: PTH111

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return os.path.expanduser("~/Pictures")  # noqa: PTH111

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Movies``"""
        return os.path.expanduser("~/Movies")  # noqa: PTH111

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return os.path.expanduser("~/Music")  # noqa: PTH111

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return os.path.expanduser("~/Desktop")  # noqa: PTH111

    @property
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user, e.g. ``~/Library/Caches/TemporaryItems/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches/TemporaryItems"))  # noqa: PTH111

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


__all__ = [
    "MacOS",
]

# === NexusCore/openenv\Lib\site-packages\IPython\__init__.py ===
# PYTHON_ARGCOMPLETE_OK
"""
IPython: tools for interactive and parallel computing in Python.

https://ipython.org
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2008-2011, IPython Development Team.
#  Copyright (c) 2001-2007, Fernando Perez <fernando.perez@colorado.edu>
#  Copyright (c) 2001, Janko Hauser <jhauser@zscout.de>
#  Copyright (c) 2001, Nathaniel Gray <n8gray@caltech.edu>
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys
import warnings

#-----------------------------------------------------------------------------
# Setup everything
#-----------------------------------------------------------------------------

# Don't forget to also update setup.py when this changes!
if sys.version_info < (3, 11):
    raise ImportError(
        """
IPython 8.31+ supports Python 3.11 and above, following SPEC0
IPython 8.19+ supports Python 3.10 and above, following SPEC0.
IPython 8.13+ supports Python 3.9 and above, following NEP 29.
IPython 8.0-8.12 supports Python 3.8 and above, following NEP 29.
When using Python 2.7, please install IPython 5.x LTS Long Term Support version.
Python 3.3 and 3.4 were supported up to IPython 6.x.
Python 3.5 was supported with IPython 7.0 to 7.9.
Python 3.6 was supported with IPython up to 7.16.
Python 3.7 was still supported with the 7.x branch.

See IPython `README.rst` file for more information:

    https://github.com/ipython/ipython/blob/main/README.rst

"""
    )

#-----------------------------------------------------------------------------
# Setup the top level names
#-----------------------------------------------------------------------------

from .core.getipython import get_ipython
from .core import release
from .core.application import Application
from .terminal.embed import embed

from .core.interactiveshell import InteractiveShell
from .utils.sysinfo import sys_info
from .utils.frame import extract_module_locals

__all__ = ["start_ipython", "embed", "embed_kernel"]

# Release data
__author__ = '%s <%s>' % (release.author, release.author_email)
__license__  = release.license
__version__  = release.version
version_info = release.version_info
# list of CVEs that should have been patched in this release.
# this is informational and should not be relied upon.
__patched_cves__ = {"CVE-2022-21699", "CVE-2023-24816"}


def embed_kernel(module=None, local_ns=None, **kwargs):
    """Embed and start an IPython kernel in a given scope.

    If you don't want the kernel to initialize the namespace
    from the scope of the surrounding function,
    and/or you want to load full IPython configuration,
    you probably want `IPython.start_kernel()` instead.

    This is a deprecated alias for `ipykernel.embed.embed_kernel()`,
    to be removed in the future.
    You should import directly from `ipykernel.embed`; this wrapper
    fails anyway if you don't have `ipykernel` package installed.

    Parameters
    ----------
    module : types.ModuleType, optional
        The module to load into IPython globals (default: caller)
    local_ns : dict, optional
        The namespace to load into IPython user namespace (default: caller)
    **kwargs : various, optional
        Further keyword args are relayed to the IPKernelApp constructor,
        such as `config`, a traitlets :class:`Config` object (see :ref:`configure_start_ipython`),
        allowing configuration of the kernel.  Will only have an effect
        on the first embed_kernel call for a given process.
    """

    warnings.warn(
        "import embed_kernel from ipykernel.embed directly (since 2013)."
        " Importing from IPython will be removed in the future",
        DeprecationWarning,
        stacklevel=2,
    )

    (caller_module, caller_locals) = extract_module_locals(1)
    if module is None:
        module = caller_module
    if local_ns is None:
        local_ns = dict(**caller_locals)
    
    # Only import .zmq when we really need it
    from ipykernel.embed import embed_kernel as real_embed_kernel
    real_embed_kernel(module=module, local_ns=local_ns, **kwargs)

def start_ipython(argv=None, **kwargs):
    """Launch a normal IPython instance (as opposed to embedded)

    `IPython.embed()` puts a shell in a particular calling scope,
    such as a function or method for debugging purposes,
    which is often not desirable.

    `start_ipython()` does full, regular IPython initialization,
    including loading startup files, configuration, etc.
    much of which is skipped by `embed()`.

    This is a public API method, and will survive implementation changes.

    Parameters
    ----------
    argv : list or None, optional
        If unspecified or None, IPython will parse command-line options from sys.argv.
        To prevent any command-line parsing, pass an empty list: `argv=[]`.
    user_ns : dict, optional
        specify this dictionary to initialize the IPython user namespace with particular values.
    **kwargs : various, optional
        Any other kwargs will be passed to the Application constructor,
        such as `config`, a traitlets :class:`Config` object (see :ref:`configure_start_ipython`),
        allowing configuration of the instance (see :ref:`terminal_options`).
    """
    from IPython.terminal.ipapp import launch_new_instance
    return launch_new_instance(argv=argv, **kwargs)

# === NexusCore/openenv\Lib\site-packages\platformdirs\macos.py ===
"""macOS."""

from __future__ import annotations

import os.path
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from pathlib import Path


class MacOS(PlatformDirsABC):
    """
    Platform directories for the macOS operating system.

    Follows the guidance from
    `Apple documentation <https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/MacOSXDirectories/MacOSXDirectories.html>`_.
    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`,
    `version <platformdirs.api.PlatformDirsABC.version>`,
    `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``~/Library/Application Support/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Application Support"))  # noqa: PTH111

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directory shared by users, e.g. ``/Library/Application Support/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/share/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/share/$appname/$version:/Library/Application Support/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/share")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Application Support"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g. ``~/Library/Caches/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches"))  # noqa: PTH111

    @property
    def site_cache_dir(self) -> str:
        """
        :return: cache directory shared by users, e.g. ``/Library/Caches/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/var/cache/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/var/cache/$appname/$version:/Library/Caches/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/var/cache")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Caches"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, e.g. ``~/Library/Logs/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Logs"))  # noqa: PTH111

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return os.path.expanduser("~/Documents")  # noqa: PTH111

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return os.path.expanduser("~/Downloads")  # noqa: PTH111

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return os.path.expanduser("~/Pictures")  # noqa: PTH111

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Movies``"""
        return os.path.expanduser("~/Movies")  # noqa: PTH111

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return os.path.expanduser("~/Music")  # noqa: PTH111

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return os.path.expanduser("~/Desktop")  # noqa: PTH111

    @property
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user, e.g. ``~/Library/Caches/TemporaryItems/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches/TemporaryItems"))  # noqa: PTH111

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


__all__ = [
    "MacOS",
]

# === NexusCore/openenv\Lib\site-packages\pydantic_core\__init__.py ===
from __future__ import annotations

import sys as _sys
from typing import Any as _Any

from ._pydantic_core import (
    ArgsKwargs,
    MultiHostUrl,
    PydanticCustomError,
    PydanticKnownError,
    PydanticOmit,
    PydanticSerializationError,
    PydanticSerializationUnexpectedValue,
    PydanticUndefined,
    PydanticUndefinedType,
    PydanticUseDefault,
    SchemaError,
    SchemaSerializer,
    SchemaValidator,
    Some,
    TzInfo,
    Url,
    ValidationError,
    __version__,
    from_json,
    to_json,
    to_jsonable_python,
    validate_core_schema,
)
from .core_schema import CoreConfig, CoreSchema, CoreSchemaType, ErrorType

if _sys.version_info < (3, 11):
    from typing_extensions import NotRequired as _NotRequired
else:
    from typing import NotRequired as _NotRequired

if _sys.version_info < (3, 12):
    from typing_extensions import TypedDict as _TypedDict
else:
    from typing import TypedDict as _TypedDict

__all__ = [
    '__version__',
    'CoreConfig',
    'CoreSchema',
    'CoreSchemaType',
    'SchemaValidator',
    'SchemaSerializer',
    'Some',
    'Url',
    'MultiHostUrl',
    'ArgsKwargs',
    'PydanticUndefined',
    'PydanticUndefinedType',
    'SchemaError',
    'ErrorDetails',
    'InitErrorDetails',
    'ValidationError',
    'PydanticCustomError',
    'PydanticKnownError',
    'PydanticOmit',
    'PydanticUseDefault',
    'PydanticSerializationError',
    'PydanticSerializationUnexpectedValue',
    'TzInfo',
    'to_json',
    'from_json',
    'to_jsonable_python',
    'validate_core_schema',
]


class ErrorDetails(_TypedDict):
    type: str
    """
    The type of error that occurred, this is an identifier designed for
    programmatic use that will change rarely or never.

    `type` is unique for each error message, and can hence be used as an identifier to build custom error messages.
    """
    loc: tuple[int | str, ...]
    """Tuple of strings and ints identifying where in the schema the error occurred."""
    msg: str
    """A human readable error message."""
    input: _Any
    """The input data at this `loc` that caused the error."""
    ctx: _NotRequired[dict[str, _Any]]
    """
    Values which are required to render the error message, and could hence be useful in rendering custom error messages.
    Also useful for passing custom error data forward.
    """
    url: _NotRequired[str]
    """
    The documentation URL giving information about the error. No URL is available if
    a [`PydanticCustomError`][pydantic_core.PydanticCustomError] is used.
    """


class InitErrorDetails(_TypedDict):
    type: str | PydanticCustomError
    """The type of error that occurred, this should be a "slug" identifier that changes rarely or never."""
    loc: _NotRequired[tuple[int | str, ...]]
    """Tuple of strings and ints identifying where in the schema the error occurred."""
    input: _Any
    """The input data at this `loc` that caused the error."""
    ctx: _NotRequired[dict[str, _Any]]
    """
    Values which are required to render the error message, and could hence be useful in rendering custom error messages.
    Also useful for passing custom error data forward.
    """


class ErrorTypeInfo(_TypedDict):
    """
    Gives information about errors.
    """

    type: ErrorType
    """The type of error that occurred, this should a "slug" identifier that changes rarely or never."""
    message_template_python: str
    """String template to render a human readable error message from using context, when the input is Python."""
    example_message_python: str
    """Example of a human readable error message, when the input is Python."""
    message_template_json: _NotRequired[str]
    """String template to render a human readable error message from using context, when the input is JSON data."""
    example_message_json: _NotRequired[str]
    """Example of a human readable error message, when the input is JSON data."""
    example_context: dict[str, _Any] | None
    """Example of context values."""


class MultiHostHost(_TypedDict):
    """
    A host part of a multi-host URL.
    """

    username: str | None
    """The username part of this host, or `None`."""
    password: str | None
    """The password part of this host, or `None`."""
    host: str | None
    """The host part of this host, or `None`."""
    port: int | None
    """The port part of this host, or `None`."""

# === NexusCore/openenv\Lib\site-packages\trio\_windows_pipes.py ===
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from . import _core
from ._abc import ReceiveStream, SendStream
from ._core._windows_cffi import _handle, kernel32, raise_winerror
from ._util import ConflictDetector, final

assert sys.platform == "win32" or not TYPE_CHECKING

# XX TODO: don't just make this up based on nothing.
DEFAULT_RECEIVE_SIZE = 65536


# See the comments on _unix_pipes._FdHolder for discussion of why we set the
# handle to -1 when it's closed.
class _HandleHolder:
    def __init__(self, handle: int) -> None:
        self.handle = -1
        if not isinstance(handle, int):
            raise TypeError("handle must be an int")
        self.handle = handle
        _core.register_with_iocp(self.handle)

    @property
    def closed(self) -> bool:
        return self.handle == -1

    def close(self) -> None:
        if self.closed:
            return
        handle = self.handle
        self.handle = -1
        if not kernel32.CloseHandle(_handle(handle)):
            raise_winerror()

    def __del__(self) -> None:
        self.close()


@final
class PipeSendStream(SendStream):
    """Represents a send stream over a Windows named pipe that has been
    opened in OVERLAPPED mode.
    """

    def __init__(self, handle: int) -> None:
        self._handle_holder = _HandleHolder(handle)
        self._conflict_detector = ConflictDetector(
            "another task is currently using this pipe",
        )

    async def send_all(self, data: bytes) -> None:
        with self._conflict_detector:
            if self._handle_holder.closed:
                raise _core.ClosedResourceError("this pipe is already closed")

            if not data:
                await _core.checkpoint()
                return

            try:
                written = await _core.write_overlapped(self._handle_holder.handle, data)
            except BrokenPipeError as ex:
                raise _core.BrokenResourceError from ex
            # By my reading of MSDN, this assert is guaranteed to pass so long
            # as the pipe isn't in nonblocking mode, but... let's just
            # double-check.
            assert written == len(data)

    async def wait_send_all_might_not_block(self) -> None:
        with self._conflict_detector:
            if self._handle_holder.closed:
                raise _core.ClosedResourceError("This pipe is already closed")

            # not implemented yet, and probably not needed
            await _core.checkpoint()

    def close(self) -> None:
        self._handle_holder.close()

    async def aclose(self) -> None:
        self.close()
        await _core.checkpoint()


@final
class PipeReceiveStream(ReceiveStream):
    """Represents a receive stream over an os.pipe object."""

    def __init__(self, handle: int) -> None:
        self._handle_holder = _HandleHolder(handle)
        self._conflict_detector = ConflictDetector(
            "another task is currently using this pipe",
        )

    async def receive_some(self, max_bytes: int | None = None) -> bytes:
        with self._conflict_detector:
            if self._handle_holder.closed:
                raise _core.ClosedResourceError("this pipe is already closed")

            if max_bytes is None:
                max_bytes = DEFAULT_RECEIVE_SIZE
            else:
                if not isinstance(max_bytes, int):
                    raise TypeError("max_bytes must be integer >= 1")
                if max_bytes < 1:
                    raise ValueError("max_bytes must be integer >= 1")

            buffer = bytearray(max_bytes)
            try:
                size = await _core.readinto_overlapped(
                    self._handle_holder.handle,
                    buffer,
                )
            except BrokenPipeError:
                if self._handle_holder.closed:
                    raise _core.ClosedResourceError(
                        "another task closed this pipe",
                    ) from None

                # Windows raises BrokenPipeError on one end of a pipe
                # whenever the other end closes, regardless of direction.
                # Convert this to the Unix behavior of returning EOF to the
                # reader when the writer closes.
                #
                # And since we're not raising an exception, we have to
                # checkpoint. But readinto_overlapped did raise an exception,
                # so it might not have checkpointed for us. So we have to
                # checkpoint manually.
                await _core.checkpoint()
                return b""
            else:
                del buffer[size:]
                return buffer

    def close(self) -> None:
        self._handle_holder.close()

    async def aclose(self) -> None:
        self.close()
        await _core.checkpoint()

# === NexusCore/openenv\Lib\site-packages\google\api_core\client_logging.py ===
import logging
import json
import os

from typing import List, Optional

_LOGGING_INITIALIZED = False
_BASE_LOGGER_NAME = "google"

# Fields to be included in the StructuredLogFormatter.
#
# TODO(https://github.com/googleapis/python-api-core/issues/761): Update this list to support additional logging fields.
_recognized_logging_fields = [
    "httpRequest",
    "rpcName",
    "serviceName",
    "credentialsType",
    "credentialsInfo",
    "universeDomain",
    "request",
    "response",
    "metadata",
    "retryAttempt",
    "httpResponse",
]  # Additional fields to be Logged.


def logger_configured(logger) -> bool:
    """Determines whether `logger` has non-default configuration

    Args:
      logger: The logger to check.

    Returns:
      bool: Whether the logger has any non-default configuration.
    """
    return (
        logger.handlers != [] or logger.level != logging.NOTSET or not logger.propagate
    )


def initialize_logging():
    """Initializes "google" loggers, partly based on the environment variable

    Initializes the "google" logger and any loggers (at the "google"
    level or lower) specified by the environment variable
    GOOGLE_SDK_PYTHON_LOGGING_SCOPE, as long as none of these loggers
    were previously configured. If any such loggers (including the
    "google" logger) are initialized, they are set to NOT propagate
    log events up to their parent loggers.

    This initialization is executed only once, and hence the
    environment variable is only processed the first time this
    function is called.
    """
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return
    scopes = os.getenv("GOOGLE_SDK_PYTHON_LOGGING_SCOPE", "")
    setup_logging(scopes)
    _LOGGING_INITIALIZED = True


def parse_logging_scopes(scopes: Optional[str] = None) -> List[str]:
    """Returns a list of logger names.

    Splits the single string of comma-separated logger names into a list of individual logger name strings.

    Args:
      scopes: The name of a single logger. (In the future, this will be a comma-separated list of multiple loggers.)

    Returns:
      A list of all the logger names in scopes.
    """
    if not scopes:
        return []
    # TODO(https://github.com/googleapis/python-api-core/issues/759): check if the namespace is a valid namespace.
    # TODO(b/380481951): Support logging multiple scopes.
    # TODO(b/380483756): Raise or log a warning for an invalid scope.
    namespaces = [scopes]
    return namespaces


def configure_defaults(logger):
    """Configures `logger` to emit structured info to stdout."""
    if not logger_configured(logger):
        console_handler = logging.StreamHandler()
        logger.setLevel("DEBUG")
        logger.propagate = False
        formatter = StructuredLogFormatter()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def setup_logging(scopes: str = ""):
    """Sets up logging for the specified `scopes`.

    If the loggers specified in `scopes` have not been previously
    configured, this will configure them to emit structured log
    entries to stdout, and to not propagate their log events to their
    parent loggers. Additionally, if the "google" logger (whether it
    was specified in `scopes` or not) was not previously configured,
    it will also configure it to not propagate log events to the root
    logger.

    Args:
      scopes: The name of a single logger. (In the future, this will be a comma-separated list of multiple loggers.)

    """

    # only returns valid logger scopes (namespaces)
    # this list has at most one element.
    logger_names = parse_logging_scopes(scopes)

    for namespace in logger_names:
        # This will either create a module level logger or get the reference of the base logger instantiated above.
        logger = logging.getLogger(namespace)

        # Configure default settings.
        configure_defaults(logger)

    # disable log propagation at base logger level to the root logger only if a base logger is not already configured via code changes.
    base_logger = logging.getLogger(_BASE_LOGGER_NAME)
    if not logger_configured(base_logger):
        base_logger.propagate = False


# TODO(https://github.com/googleapis/python-api-core/issues/763): Expand documentation.
class StructuredLogFormatter(logging.Formatter):
    # TODO(https://github.com/googleapis/python-api-core/issues/761): ensure that additional fields such as
    # function name, file name, and line no. appear in a log output.
    def format(self, record: logging.LogRecord):
        log_obj = {
            "timestamp": self.formatTime(record),
            "severity": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        for field_name in _recognized_logging_fields:
            value = getattr(record, field_name, None)
            if value is not None:
                log_obj[field_name] = value
        return json.dumps(log_obj)

# === NexusCore/openenv\Lib\site-packages\google\auth\aio\transport\__init__.py ===
# Copyright 2024 Google LLC
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

"""Transport - Asynchronous HTTP client library support.

:mod:`google.auth.aio` is designed to work with various asynchronous client libraries such
as aiohttp. In order to work across these libraries with different
interfaces some abstraction is needed.

This module provides two interfaces that are implemented by transport adapters
to support HTTP libraries. :class:`Request` defines the interface expected by
:mod:`google.auth` to make asynchronous requests. :class:`Response` defines the interface
for the return value of :class:`Request`.
"""

import abc
from typing import AsyncGenerator, Mapping, Optional

import google.auth.transport


_DEFAULT_TIMEOUT_SECONDS = 180

DEFAULT_RETRYABLE_STATUS_CODES = google.auth.transport.DEFAULT_RETRYABLE_STATUS_CODES
"""Sequence[int]:  HTTP status codes indicating a request can be retried.
"""


DEFAULT_MAX_RETRY_ATTEMPTS = 3
"""int: How many times to retry a request."""


class Response(metaclass=abc.ABCMeta):
    """Asynchronous HTTP Response Interface."""

    @property
    @abc.abstractmethod
    def status_code(self) -> int:
        """
        The HTTP response status code.

        Returns:
            int: The HTTP response status code.

        """
        raise NotImplementedError("status_code must be implemented.")

    @property
    @abc.abstractmethod
    def headers(self) -> Mapping[str, str]:
        """The HTTP response headers.

        Returns:
            Mapping[str, str]: The HTTP response headers.
        """
        raise NotImplementedError("headers must be implemented.")

    @abc.abstractmethod
    async def content(self, chunk_size: int) -> AsyncGenerator[bytes, None]:
        """The raw response content.

        Args:
            chunk_size (int): The size of each chunk.

        Yields:
            AsyncGenerator[bytes, None]: An asynchronous generator yielding
            response chunks as bytes.
        """
        raise NotImplementedError("content must be implemented.")

    @abc.abstractmethod
    async def read(self) -> bytes:
        """Read the entire response content as bytes.

        Returns:
            bytes: The entire response content.
        """
        raise NotImplementedError("read must be implemented.")

    @abc.abstractmethod
    async def close(self):
        """Close the response after it is fully consumed to resource."""
        raise NotImplementedError("close must be implemented.")


class Request(metaclass=abc.ABCMeta):
    """Interface for a callable that makes HTTP requests.

    Specific transport implementations should provide an implementation of
    this that adapts their specific request / response API.

    .. automethod:: __call__
    """

    @abc.abstractmethod
    async def __call__(
        self,
        url: str,
        method: str,
        body: Optional[bytes],
        headers: Optional[Mapping[str, str]],
        timeout: float,
        **kwargs
    ) -> Response:
        """Make an HTTP request.

        Args:
            url (str): The URI to be requested.
            method (str): The HTTP method to use for the request. Defaults
                to 'GET'.
            body (Optional[bytes]): The payload / body in HTTP request.
            headers (Mapping[str, str]): Request headers.
            timeout (float): The number of seconds to wait for a
                response from the server. If not specified or if None, the
                transport-specific default timeout will be used.
            kwargs: Additional arguments passed on to the transport's
                request method.

        Returns:
            google.auth.aio.transport.Response: The HTTP response.

        Raises:
            google.auth.exceptions.TransportError: If any exception occurred.
        """
        # pylint: disable=redundant-returns-doc, missing-raises-doc
        # (pylint doesn't play well with abstract docstrings.)
        raise NotImplementedError("__call__ must be implemented.")

    async def close(self) -> None:
        """
        Close the underlying session.
        """
        raise NotImplementedError("close must be implemented.")

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\_subprocess.py ===
# coding=utf-8
# Copyright 2021 The HuggingFace Inc. team. All rights reserved.
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
# limitations under the License
"""Contains utilities to easily handle subprocesses in `huggingface_hub`."""

import os
import subprocess
import sys
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import IO, Generator, List, Optional, Tuple, Union

from .logging import get_logger


logger = get_logger(__name__)


@contextmanager
def capture_output() -> Generator[StringIO, None, None]:
    """Capture output that is printed to terminal.

    Taken from https://stackoverflow.com/a/34738440

    Example:
    ```py
    >>> with capture_output() as output:
    ...     print("hello world")
    >>> assert output.getvalue() == "hello world\n"
    ```
    """
    output = StringIO()
    previous_output = sys.stdout
    sys.stdout = output
    try:
        yield output
    finally:
        sys.stdout = previous_output


def run_subprocess(
    command: Union[str, List[str]],
    folder: Optional[Union[str, Path]] = None,
    check=True,
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    Method to run subprocesses. Calling this will capture the `stderr` and `stdout`,
    please call `subprocess.run` manually in case you would like for them not to
    be captured.

    Args:
        command (`str` or `List[str]`):
            The command to execute as a string or list of strings.
        folder (`str`, *optional*):
            The folder in which to run the command. Defaults to current working
            directory (from `os.getcwd()`).
        check (`bool`, *optional*, defaults to `True`):
            Setting `check` to `True` will raise a `subprocess.CalledProcessError`
            when the subprocess has a non-zero exit code.
        kwargs (`Dict[str]`):
            Keyword arguments to be passed to the `subprocess.run` underlying command.

    Returns:
        `subprocess.CompletedProcess`: The completed process.
    """
    if isinstance(command, str):
        command = command.split()

    if isinstance(folder, Path):
        folder = str(folder)

    return subprocess.run(
        command,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        check=check,
        encoding="utf-8",
        errors="replace",  # if not utf-8, replace char by �
        cwd=folder or os.getcwd(),
        **kwargs,
    )


@contextmanager
def run_interactive_subprocess(
    command: Union[str, List[str]],
    folder: Optional[Union[str, Path]] = None,
    **kwargs,
) -> Generator[Tuple[IO[str], IO[str]], None, None]:
    """Run a subprocess in an interactive mode in a context manager.

    Args:
        command (`str` or `List[str]`):
            The command to execute as a string or list of strings.
        folder (`str`, *optional*):
            The folder in which to run the command. Defaults to current working
            directory (from `os.getcwd()`).
        kwargs (`Dict[str]`):
            Keyword arguments to be passed to the `subprocess.run` underlying command.

    Returns:
        `Tuple[IO[str], IO[str]]`: A tuple with `stdin` and `stdout` to interact
        with the process (input and output are utf-8 encoded).

    Example:
    ```python
    with _interactive_subprocess("git credential-store get") as (stdin, stdout):
        # Write to stdin
        stdin.write("url=hf.co\nusername=obama\n".encode("utf-8"))
        stdin.flush()

        # Read from stdout
        output = stdout.read().decode("utf-8")
    ```
    """
    if isinstance(command, str):
        command = command.split()

    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",  # if not utf-8, replace char by �
        cwd=folder or os.getcwd(),
        **kwargs,
    ) as process:
        assert process.stdin is not None, "subprocess is opened as subprocess.PIPE"
        assert process.stdout is not None, "subprocess is opened as subprocess.PIPE"
        yield process.stdin, process.stdout

# === NexusCore/openenv\Lib\site-packages\IPython\core\magics\auto.py ===
"""Implementation of magic functions that control various automatic behaviors.
"""
#-----------------------------------------------------------------------------
#  Copyright (c) 2012 The IPython Development Team.
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Our own packages
from IPython.core.magic import Bunch, Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from logging import error

#-----------------------------------------------------------------------------
# Magic implementation classes
#-----------------------------------------------------------------------------

@magics_class
class AutoMagics(Magics):
    """Magics that control various autoX behaviors."""

    def __init__(self, shell):
        super(AutoMagics, self).__init__(shell)
        # namespace for holding state we may need
        self._magic_state = Bunch()

    @line_magic
    def automagic(self, parameter_s=''):
        """Make magic functions callable without having to type the initial %.

        Without arguments toggles on/off (when off, you must call it as
        %automagic, of course).  With arguments it sets the value, and you can
        use any of (case insensitive):

         - on, 1, True: to activate

         - off, 0, False: to deactivate.

        Note that magic functions have lowest priority, so if there's a
        variable whose name collides with that of a magic fn, automagic won't
        work for that function (you get the variable instead). However, if you
        delete the variable (del var), the previously shadowed magic function
        becomes visible to automagic again."""

        arg = parameter_s.lower()
        mman = self.shell.magics_manager
        if arg in ('on', '1', 'true'):
            val = True
        elif arg in ('off', '0', 'false'):
            val = False
        else:
            val = not mman.auto_magic
        mman.auto_magic = val
        print('\n' + self.shell.magics_manager.auto_status())

    @skip_doctest
    @line_magic
    def autocall(self, parameter_s=''):
        """Make functions callable without having to type parentheses.

        Usage:

           %autocall [mode]

        The mode can be one of: 0->Off, 1->Smart, 2->Full.  If not given, the
        value is toggled on and off (remembering the previous state).

        In more detail, these values mean:

        0 -> fully disabled

        1 -> active, but do not apply if there are no arguments on the line.

        In this mode, you get::

          In [1]: callable
          Out[1]: <built-in function callable>

          In [2]: callable 'hello'
          ------> callable('hello')
          Out[2]: False

        2 -> Active always.  Even if no arguments are present, the callable
        object is called::

          In [2]: float
          ------> float()
          Out[2]: 0.0

        Note that even with autocall off, you can still use '/' at the start of
        a line to treat the first argument on the command line as a function
        and add parentheses to it::

          In [8]: /str 43
          ------> str(43)
          Out[8]: '43'

        # all-random (note for auto-testing)
        """

        valid_modes = {
            0: "Off",
            1: "Smart",
            2: "Full",
        }

        def errorMessage() -> str:
            error = "Valid modes: "
            for k, v in valid_modes.items():
                error += str(k) + "->" + v + ", "
            error = error[:-2]  # remove tailing `, ` after last element
            return error

        if parameter_s:
            if parameter_s not in map(str, valid_modes.keys()):
                error(errorMessage())
                return
            arg = int(parameter_s)
        else:
            arg = 'toggle'

        if arg not in (*list(valid_modes.keys()), "toggle"):
            error(errorMessage())
            return

        if arg in (valid_modes.keys()):
            self.shell.autocall = arg
        else: # toggle
            if self.shell.autocall:
                self._magic_state.autocall_save = self.shell.autocall
                self.shell.autocall = 0
            else:
                try:
                    self.shell.autocall = self._magic_state.autocall_save
                except AttributeError:
                    self.shell.autocall = self._magic_state.autocall_save = 1

        print("Automatic calling is:", list(valid_modes.values())[self.shell.autocall])

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\platformdirs\macos.py ===
"""macOS."""

from __future__ import annotations

import os.path
import sys
from typing import TYPE_CHECKING

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from pathlib import Path


class MacOS(PlatformDirsABC):
    """
    Platform directories for the macOS operating system.

    Follows the guidance from
    `Apple documentation <https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemProgrammingGuide/MacOSXDirectories/MacOSXDirectories.html>`_.
    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`,
    `version <platformdirs.api.PlatformDirsABC.version>`,
    `ensure_exists <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        """:return: data directory tied to the user, e.g. ``~/Library/Application Support/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Application Support"))  # noqa: PTH111

    @property
    def site_data_dir(self) -> str:
        """
        :return: data directory shared by users, e.g. ``/Library/Application Support/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/share/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/share/$appname/$version:/Library/Application Support/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/share")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Application Support"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_data_path(self) -> Path:
        """:return: data path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_data_dir)

    @property
    def user_config_dir(self) -> str:
        """:return: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:return: config directory shared by the users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        """:return: cache directory tied to the user, e.g. ``~/Library/Caches/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches"))  # noqa: PTH111

    @property
    def site_cache_dir(self) -> str:
        """
        :return: cache directory shared by users, e.g. ``/Library/Caches/$appname/$version``.
          If we're using a Python binary managed by `Homebrew <https://brew.sh>`_, the directory
          will be under the Homebrew prefix, e.g. ``/opt/homebrew/var/cache/$appname/$version``.
          If `multipath <platformdirs.api.PlatformDirsABC.multipath>` is enabled, and we're in Homebrew,
          the response is a multi-path string separated by ":", e.g.
          ``/opt/homebrew/var/cache/$appname/$version:/Library/Caches/$appname/$version``
        """
        is_homebrew = sys.prefix.startswith("/opt/homebrew")
        path_list = [self._append_app_name_and_version("/opt/homebrew/var/cache")] if is_homebrew else []
        path_list.append(self._append_app_name_and_version("/Library/Caches"))
        if self.multipath:
            return os.pathsep.join(path_list)
        return path_list[0]

    @property
    def site_cache_path(self) -> Path:
        """:return: cache path shared by users. Only return the first item, even if ``multipath`` is set to ``True``"""
        return self._first_item_as_path_if_multipath(self.site_cache_dir)

    @property
    def user_state_dir(self) -> str:
        """:return: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def user_log_dir(self) -> str:
        """:return: log directory tied to the user, e.g. ``~/Library/Logs/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Logs"))  # noqa: PTH111

    @property
    def user_documents_dir(self) -> str:
        """:return: documents directory tied to the user, e.g. ``~/Documents``"""
        return os.path.expanduser("~/Documents")  # noqa: PTH111

    @property
    def user_downloads_dir(self) -> str:
        """:return: downloads directory tied to the user, e.g. ``~/Downloads``"""
        return os.path.expanduser("~/Downloads")  # noqa: PTH111

    @property
    def user_pictures_dir(self) -> str:
        """:return: pictures directory tied to the user, e.g. ``~/Pictures``"""
        return os.path.expanduser("~/Pictures")  # noqa: PTH111

    @property
    def user_videos_dir(self) -> str:
        """:return: videos directory tied to the user, e.g. ``~/Movies``"""
        return os.path.expanduser("~/Movies")  # noqa: PTH111

    @property
    def user_music_dir(self) -> str:
        """:return: music directory tied to the user, e.g. ``~/Music``"""
        return os.path.expanduser("~/Music")  # noqa: PTH111

    @property
    def user_desktop_dir(self) -> str:
        """:return: desktop directory tied to the user, e.g. ``~/Desktop``"""
        return os.path.expanduser("~/Desktop")  # noqa: PTH111

    @property
    def user_runtime_dir(self) -> str:
        """:return: runtime directory tied to the user, e.g. ``~/Library/Caches/TemporaryItems/$appname/$version``"""
        return self._append_app_name_and_version(os.path.expanduser("~/Library/Caches/TemporaryItems"))  # noqa: PTH111

    @property
    def site_runtime_dir(self) -> str:
        """:return: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


__all__ = [
    "MacOS",
]

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ada.py ===
"""
    pygments.lexers.ada
    ~~~~~~~~~~~~~~~~~~~

    Lexers for Ada family languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words, using, this, \
    default
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation
from pygments.lexers._ada_builtins import KEYWORD_LIST, BUILTIN_LIST

__all__ = ['AdaLexer']


class AdaLexer(RegexLexer):
    """
    For Ada source code.
    """

    name = 'Ada'
    aliases = ['ada', 'ada95', 'ada2005']
    filenames = ['*.adb', '*.ads', '*.ada']
    mimetypes = ['text/x-ada']
    url = 'https://www.adaic.org'
    version_added = '1.3'

    flags = re.MULTILINE | re.IGNORECASE

    tokens = {
        'root': [
            (r'[^\S\n]+', Text),
            (r'--.*?\n', Comment.Single),
            (r'[^\S\n]+', Text),
            (r'function|procedure|entry', Keyword.Declaration, 'subprogram'),
            (r'(subtype|type)(\s+)(\w+)',
             bygroups(Keyword.Declaration, Text, Keyword.Type), 'type_def'),
            (r'task|protected', Keyword.Declaration),
            (r'(subtype)(\s+)', bygroups(Keyword.Declaration, Text)),
            (r'(end)(\s+)', bygroups(Keyword.Reserved, Text), 'end'),
            (r'(pragma)(\s+)(\w+)', bygroups(Keyword.Reserved, Text,
                                             Comment.Preproc)),
            (r'(true|false|null)\b', Keyword.Constant),
            # builtin types
            (words(BUILTIN_LIST, suffix=r'\b'), Keyword.Type),
            (r'(and(\s+then)?|in|mod|not|or(\s+else)|rem)\b', Operator.Word),
            (r'generic|private', Keyword.Declaration),
            (r'package', Keyword.Declaration, 'package'),
            (r'array\b', Keyword.Reserved, 'array_def'),
            (r'(with|use)(\s+)', bygroups(Keyword.Namespace, Text), 'import'),
            (r'(\w+)(\s*)(:)(\s*)(constant)',
             bygroups(Name.Constant, Text, Punctuation, Text,
                      Keyword.Reserved)),
            (r'<<\w+>>', Name.Label),
            (r'(\w+)(\s*)(:)(\s*)(declare|begin|loop|for|while)',
             bygroups(Name.Label, Text, Punctuation, Text, Keyword.Reserved)),
            # keywords
            (words(KEYWORD_LIST, prefix=r'\b', suffix=r'\b'),
             Keyword.Reserved),
            (r'"[^"]*"', String),
            include('attribute'),
            include('numbers'),
            (r"'[^']'", String.Character),
            (r'(\w+)(\s*|[(,])', bygroups(Name, using(this))),
            (r"(<>|=>|:=|@|[\[\]]|[()|:;,.'])", Punctuation),
            (r'[*<>+=/&-]', Operator),
            (r'\n+', Text),
        ],
        'numbers': [
            (r'[0-9_]+#[0-9a-f_\.]+#', Number.Hex),
            (r'[0-9_]+\.[0-9_]*', Number.Float),
            (r'[0-9_]+', Number.Integer),
        ],
        'attribute': [
            (r"(')(\w+)", bygroups(Punctuation, Name.Attribute)),
        ],
        'subprogram': [
            (r'\(', Punctuation, ('#pop', 'formal_part')),
            (r';', Punctuation, '#pop'),
            (r'is\b', Keyword.Reserved, '#pop'),
            (r'"[^"]+"|\w+', Name.Function),
            include('root'),
        ],
        'end': [
            ('(if|case|record|loop|select)', Keyword.Reserved),
            (r'"[^"]+"|[\w.]+', Name.Function),
            (r'\s+', Text),
            (';', Punctuation, '#pop'),
        ],
        'type_def': [
            (r';', Punctuation, '#pop'),
            (r'\(', Punctuation, 'formal_part'),
            (r'\[', Punctuation, 'formal_part'),
            (r'with|and|use', Keyword.Reserved),
            (r'array\b', Keyword.Reserved, ('#pop', 'array_def')),
            (r'record\b', Keyword.Reserved, ('record_def')),
            (r'(null record)(;)', bygroups(Keyword.Reserved, Punctuation), '#pop'),
            include('root'),
        ],
        'array_def': [
            (r';', Punctuation, '#pop'),
            (r'(\w+)(\s+)(range)', bygroups(Keyword.Type, Text, Keyword.Reserved)),
            include('root'),
        ],
        'record_def': [
            (r'end record', Keyword.Reserved, '#pop'),
            include('root'),
        ],
        'import': [
            # TODO: use Name.Namespace if appropriate.  This needs
            # work to disinguish imports from aspects.
            (r'[\w.]+', Name, '#pop'),
            default('#pop'),
        ],
        'formal_part': [
            (r'\)', Punctuation, '#pop'),
            (r'\]', Punctuation, '#pop'),
            (r'\w+', Name.Variable),
            (r',|:[^=]', Punctuation),
            (r'(in|not|null|out|access)\b', Keyword.Reserved),
            include('root'),
        ],
        'package': [
            ('body', Keyword.Declaration),
            (r'is\s+new|renames', Keyword.Reserved),
            ('is', Keyword.Reserved, '#pop'),
            (';', Punctuation, '#pop'),
            (r'\(', Punctuation, 'package_instantiation'),
            (r'([\w.]+)', Name.Class),
            include('root'),
        ],
        'package_instantiation': [
            (r'("[^"]+"|\w+)(\s+)(=>)', bygroups(Name.Variable, Text, Punctuation)),
            (r'[\w.\'"]', Text),
            (r'\)', Punctuation, '#pop'),
            include('root'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ecl.py ===
"""
    pygments.lexers.ecl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for the ECL language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, words
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Whitespace

__all__ = ['ECLLexer']


class ECLLexer(RegexLexer):
    """
    Lexer for the declarative big-data ECL language.
    """

    name = 'ECL'
    url = 'https://hpccsystems.com/training/documentation/ecl-language-reference/html'
    aliases = ['ecl']
    filenames = ['*.ecl']
    mimetypes = ['application/x-ecl']
    version_added = '1.5'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            include('whitespace'),
            include('statements'),
        ],
        'whitespace': [
            (r'\s+', Whitespace),
            (r'\/\/.*', Comment.Single),
            (r'/(\\\n)?\*(.|\n)*?\*(\\\n)?/', Comment.Multiline),
        ],
        'statements': [
            include('types'),
            include('keywords'),
            include('functions'),
            include('hash'),
            (r'"', String, 'string'),
            (r'\'', String, 'string'),
            (r'(\d+\.\d*|\.\d+|\d+)e[+-]?\d+[lu]*', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+f)f?', Number.Float),
            (r'0x[0-9a-f]+[lu]*', Number.Hex),
            (r'0[0-7]+[lu]*', Number.Oct),
            (r'\d+[lu]*', Number.Integer),
            (r'[~!%^&*+=|?:<>/-]+', Operator),
            (r'[{}()\[\],.;]', Punctuation),
            (r'[a-z_]\w*', Name),
        ],
        'hash': [
            (r'^#.*$', Comment.Preproc),
        ],
        'types': [
            (r'(RECORD|END)\D', Keyword.Declaration),
            (r'((?:ASCII|BIG_ENDIAN|BOOLEAN|DATA|DECIMAL|EBCDIC|INTEGER|PATTERN|'
             r'QSTRING|REAL|RECORD|RULE|SET OF|STRING|TOKEN|UDECIMAL|UNICODE|'
             r'UNSIGNED|VARSTRING|VARUNICODE)\d*)(\s+)',
             bygroups(Keyword.Type, Whitespace)),
        ],
        'keywords': [
            (words((
                'APPLY', 'ASSERT', 'BUILD', 'BUILDINDEX', 'EVALUATE', 'FAIL',
                'KEYDIFF', 'KEYPATCH', 'LOADXML', 'NOTHOR', 'NOTIFY', 'OUTPUT',
                'PARALLEL', 'SEQUENTIAL', 'SOAPCALL', 'CHECKPOINT', 'DEPRECATED',
                'FAILCODE', 'FAILMESSAGE', 'FAILURE', 'GLOBAL', 'INDEPENDENT',
                'ONWARNING', 'PERSIST', 'PRIORITY', 'RECOVERY', 'STORED', 'SUCCESS',
                'WAIT', 'WHEN'), suffix=r'\b'),
             Keyword.Reserved),
            # These are classed differently, check later
            (words((
                'ALL', 'AND', 'ANY', 'AS', 'ATMOST', 'BEFORE', 'BEGINC++', 'BEST',
                'BETWEEN', 'CASE', 'CONST', 'COUNTER', 'CSV', 'DESCEND', 'ENCRYPT',
                'ENDC++', 'ENDMACRO', 'EXCEPT', 'EXCLUSIVE', 'EXPIRE', 'EXPORT',
                'EXTEND', 'FALSE', 'FEW', 'FIRST', 'FLAT', 'FULL', 'FUNCTION',
                'GROUP', 'HEADER', 'HEADING', 'HOLE', 'IFBLOCK', 'IMPORT', 'IN',
                'JOINED', 'KEEP', 'KEYED', 'LAST', 'LEFT', 'LIMIT', 'LOAD', 'LOCAL',
                'LOCALE', 'LOOKUP', 'MACRO', 'MANY', 'MAXCOUNT', 'MAXLENGTH',
                'MIN SKEW', 'MODULE', 'INTERFACE', 'NAMED', 'NOCASE', 'NOROOT',
                'NOSCAN', 'NOSORT', 'NOT', 'OF', 'ONLY', 'OPT', 'OR', 'OUTER',
                'OVERWRITE', 'PACKED', 'PARTITION', 'PENALTY', 'PHYSICALLENGTH',
                'PIPE', 'QUOTE', 'RELATIONSHIP', 'REPEAT', 'RETURN', 'RIGHT',
                'SCAN', 'SELF', 'SEPARATOR', 'SERVICE', 'SHARED', 'SKEW', 'SKIP',
                'SQL', 'STORE', 'TERMINATOR', 'THOR', 'THRESHOLD', 'TOKEN',
                'TRANSFORM', 'TRIM', 'TRUE', 'TYPE', 'UNICODEORDER', 'UNSORTED',
                'VALIDATE', 'VIRTUAL', 'WHOLE', 'WILD', 'WITHIN', 'XML', 'XPATH',
                '__COMPRESSED__'), suffix=r'\b'),
             Keyword.Reserved),
        ],
        'functions': [
            (words((
                'ABS', 'ACOS', 'ALLNODES', 'ASCII', 'ASIN', 'ASSTRING', 'ATAN',
                'ATAN2', 'AVE', 'CASE', 'CHOOSE', 'CHOOSEN', 'CHOOSESETS',
                'CLUSTERSIZE', 'COMBINE', 'CORRELATION', 'COS', 'COSH', 'COUNT',
                'COVARIANCE', 'CRON', 'DATASET', 'DEDUP', 'DEFINE', 'DENORMALIZE',
                'DISTRIBUTE', 'DISTRIBUTED', 'DISTRIBUTION', 'EBCDIC', 'ENTH',
                'ERROR', 'EVALUATE', 'EVENT', 'EVENTEXTRA', 'EVENTNAME', 'EXISTS',
                'EXP', 'FAILCODE', 'FAILMESSAGE', 'FETCH', 'FROMUNICODE',
                'GETISVALID', 'GLOBAL', 'GRAPH', 'GROUP', 'HASH', 'HASH32',
                'HASH64', 'HASHCRC', 'HASHMD5', 'HAVING', 'IF', 'INDEX',
                'INTFORMAT', 'ISVALID', 'ITERATE', 'JOIN', 'KEYUNICODE', 'LENGTH',
                'LIBRARY', 'LIMIT', 'LN', 'LOCAL', 'LOG', 'LOOP', 'MAP', 'MATCHED',
                'MATCHLENGTH', 'MATCHPOSITION', 'MATCHTEXT', 'MATCHUNICODE', 'MAX',
                'MERGE', 'MERGEJOIN', 'MIN', 'NOLOCAL', 'NONEMPTY', 'NORMALIZE',
                'PARSE', 'PIPE', 'POWER', 'PRELOAD', 'PROCESS', 'PROJECT', 'PULL',
                'RANDOM', 'RANGE', 'RANK', 'RANKED', 'REALFORMAT', 'RECORDOF',
                'REGEXFIND', 'REGEXREPLACE', 'REGROUP', 'REJECTED', 'ROLLUP',
                'ROUND', 'ROUNDUP', 'ROW', 'ROWDIFF', 'SAMPLE', 'SET', 'SIN',
                'SINH', 'SIZEOF', 'SOAPCALL', 'SORT', 'SORTED', 'SQRT', 'STEPPED',
                'STORED', 'SUM', 'TABLE', 'TAN', 'TANH', 'THISNODE', 'TOPN',
                'TOUNICODE', 'TRANSFER', 'TRIM', 'TRUNCATE', 'TYPEOF', 'UNGROUP',
                'UNICODEORDER', 'VARIANCE', 'WHICH', 'WORKUNIT', 'XMLDECODE',
                'XMLENCODE', 'XMLTEXT', 'XMLUNICODE'), suffix=r'\b'),
             Name.Function),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\'', String, '#pop'),
            (r'[^"\']+', String),
        ],
    }

    def analyse_text(text):
        """This is very difficult to guess relative to other business languages.
        -> in conjunction with BEGIN/END seems relatively rare though."""
        result = 0

        if '->' in text:
            result += 0.01
        if 'BEGIN' in text:
            result += 0.01
        if 'END' in text:
            result += 0.01

        return result

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\nix.py ===
"""
    pygments.lexers.nix
    ~~~~~~~~~~~~~~~~~~~

    Lexers for the NixOS Nix language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Literal

__all__ = ['NixLexer']


class NixLexer(RegexLexer):
    """
    For the Nix language.
    """

    name = 'Nix'
    url = 'http://nixos.org/nix/'
    aliases = ['nixos', 'nix']
    filenames = ['*.nix']
    mimetypes = ['text/x-nix']
    version_added = '2.0'

    keywords = ['rec', 'with', 'let', 'in', 'inherit', 'assert', 'if',
                'else', 'then', '...']
    builtins = ['import', 'abort', 'baseNameOf', 'dirOf', 'isNull', 'builtins',
                'map', 'removeAttrs', 'throw', 'toString', 'derivation']
    operators = ['++', '+', '?', '.', '!', '//', '==', '/',
                 '!=', '&&', '||', '->', '=', '<', '>', '*', '-']

    punctuations = ["(", ")", "[", "]", ";", "{", "}", ":", ",", "@"]

    tokens = {
        'root': [
            # comments starting with #
            (r'#.*$', Comment.Single),

            # multiline comments
            (r'/\*', Comment.Multiline, 'comment'),

            # whitespace
            (r'\s+', Text),

            # keywords
            ('({})'.format('|'.join(re.escape(entry) + '\\b' for entry in keywords)), Keyword),

            # highlight the builtins
            ('({})'.format('|'.join(re.escape(entry) + '\\b' for entry in builtins)),
             Name.Builtin),

            (r'\b(true|false|null)\b', Name.Constant),

            # floats
            (r'-?(\d+\.\d*|\.\d+)([eE][-+]?\d+)?', Number.Float),

            # integers
            (r'-?[0-9]+', Number.Integer),

            # paths
            (r'[\w.+-]*(\/[\w.+-]+)+', Literal),
            (r'~(\/[\w.+-]+)+', Literal),
            (r'\<[\w.+-]+(\/[\w.+-]+)*\>', Literal),

            # operators
            ('({})'.format('|'.join(re.escape(entry) for entry in operators)),
             Operator),

            # word operators
            (r'\b(or|and)\b', Operator.Word),

            (r'\{', Punctuation, 'block'),

            # punctuations
            ('({})'.format('|'.join(re.escape(entry) for entry in punctuations)), Punctuation),

            # strings
            (r'"', String.Double, 'doublequote'),
            (r"''", String.Multiline, 'multiline'),

            # urls
            (r'[a-zA-Z][a-zA-Z0-9\+\-\.]*\:[\w%/?:@&=+$,\\.!~*\'-]+', Literal),

            # names of variables
            (r'[\w-]+(?=\s*=)', String.Symbol),
            (r'[a-zA-Z_][\w\'-]*', Text),

            (r"\$\{", String.Interpol, 'antiquote'),
        ],
        'comment': [
            (r'[^/*]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
        'multiline': [
            (r"''(\$|'|\\n|\\r|\\t|\\)", String.Escape),
            (r"''", String.Multiline, '#pop'),
            (r'\$\{', String.Interpol, 'antiquote'),
            (r"[^'\$]+", String.Multiline),
            (r"\$[^\{']", String.Multiline),
            (r"'[^']", String.Multiline),
            (r"\$(?=')", String.Multiline),
        ],
        'doublequote': [
            (r'\\(\\|"|\$|n)', String.Escape),
            (r'"', String.Double, '#pop'),
            (r'\$\{', String.Interpol, 'antiquote'),
            (r'[^"\\\$]+', String.Double),
            (r'\$[^\{"]', String.Double),
            (r'\$(?=")', String.Double),
            (r'\\', String.Double),
        ],
        'antiquote': [
            (r"\}", String.Interpol, '#pop'),
            # TODO: we should probably escape also here ''${ \${
            (r"\$\{", String.Interpol, '#push'),
            include('root'),
        ],
        'block': [
            (r"\}", Punctuation, '#pop'),
            include('root'),
        ],
    }

    def analyse_text(text):
        rv = 0.0
        # TODO: let/in
        if re.search(r'import.+?<[^>]+>', text):
            rv += 0.4
        if re.search(r'mkDerivation\s+(\(|\{|rec)', text):
            rv += 0.4
        if re.search(r'=\s+mkIf\s+', text):
            rv += 0.4
        if re.search(r'\{[a-zA-Z,\s]+\}:', text):
            rv += 0.1
        return rv

# === NexusCore/openenv\Lib\site-packages\pygments\styles\solarized.py ===
"""
    pygments.styles.solarized
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Solarized by Camil Staps

    A Pygments style for the Solarized themes (licensed under MIT).
    See: https://github.com/altercation/solarized

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.style import Style
from pygments.token import Comment, Error, Generic, Keyword, Name, Number, \
    Operator, String, Token


__all__ = ['SolarizedLightStyle', 'SolarizedDarkStyle']


def make_style(colors):
    return {
        Token:               colors['base0'],

        Comment:             'italic ' + colors['base01'],
        Comment.Hashbang:    colors['base01'],
        Comment.Multiline:   colors['base01'],
        Comment.Preproc:     'noitalic ' + colors['magenta'],
        Comment.PreprocFile: 'noitalic ' + colors['base01'],

        Keyword:             colors['green'],
        Keyword.Constant:    colors['cyan'],
        Keyword.Declaration: colors['cyan'],
        Keyword.Namespace:   colors['orange'],
        Keyword.Type:        colors['yellow'],

        Operator:            colors['base01'],
        Operator.Word:       colors['green'],

        Name.Builtin:        colors['blue'],
        Name.Builtin.Pseudo: colors['blue'],
        Name.Class:          colors['blue'],
        Name.Constant:       colors['blue'],
        Name.Decorator:      colors['blue'],
        Name.Entity:         colors['blue'],
        Name.Exception:      colors['blue'],
        Name.Function:       colors['blue'],
        Name.Function.Magic: colors['blue'],
        Name.Label:          colors['blue'],
        Name.Namespace:      colors['blue'],
        Name.Tag:            colors['blue'],
        Name.Variable:       colors['blue'],
        Name.Variable.Global:colors['blue'],
        Name.Variable.Magic: colors['blue'],

        String:              colors['cyan'],
        String.Doc:          colors['base01'],
        String.Regex:        colors['orange'],

        Number:              colors['cyan'],

        Generic:             colors['base0'],
        Generic.Deleted:     colors['red'],
        Generic.Emph:        'italic',
        Generic.Error:       colors['red'],
        Generic.Heading:     'bold',
        Generic.Subheading:  'underline',
        Generic.Inserted:    colors['green'],
        Generic.Output:      colors['base0'],
        Generic.Prompt:      'bold ' + colors['blue'],
        Generic.Strong:      'bold',
        Generic.EmphStrong:  'bold italic',
        Generic.Traceback:   colors['blue'],

        Error:               'bg:' + colors['red'],
    }


DARK_COLORS = {
    'base03':  '#002b36',
    'base02':  '#073642',
    'base01':  '#586e75',
    'base00':  '#657b83',
    'base0':   '#839496',
    'base1':   '#93a1a1',
    'base2':   '#eee8d5',
    'base3':   '#fdf6e3',
    'yellow':  '#b58900',
    'orange':  '#cb4b16',
    'red':     '#dc322f',
    'magenta': '#d33682',
    'violet':  '#6c71c4',
    'blue':    '#268bd2',
    'cyan':    '#2aa198',
    'green':   '#859900',
}

LIGHT_COLORS = {
    'base3':   '#002b36',
    'base2':   '#073642',
    'base1':   '#586e75',
    'base0':   '#657b83',
    'base00':  '#839496',
    'base01':  '#93a1a1',
    'base02':  '#eee8d5',
    'base03':  '#fdf6e3',
    'yellow':  '#b58900',
    'orange':  '#cb4b16',
    'red':     '#dc322f',
    'magenta': '#d33682',
    'violet':  '#6c71c4',
    'blue':    '#268bd2',
    'cyan':    '#2aa198',
    'green':   '#859900',
}


class SolarizedDarkStyle(Style):
    """
    The solarized style, dark.
    """

    name = 'solarized-dark'
    
    styles = make_style(DARK_COLORS)
    background_color = DARK_COLORS['base03']
    highlight_color = DARK_COLORS['base02']
    line_number_color = DARK_COLORS['base01']
    line_number_background_color = DARK_COLORS['base02']


class SolarizedLightStyle(SolarizedDarkStyle):
    """
    The solarized style, light.
    """

    name = 'solarized-light'
    
    styles = make_style(LIGHT_COLORS)
    background_color = LIGHT_COLORS['base03']
    highlight_color = LIGHT_COLORS['base02']
    line_number_color = LIGHT_COLORS['base01']
    line_number_background_color = LIGHT_COLORS['base02']

# === NexusCore/openenv\Lib\site-packages\win32\test\test_win32crypt.py ===
# Test module for win32crypt

import contextlib
import unittest
from collections.abc import Iterator
from typing import Any

import win32crypt
from pywin32_testutil import find_test_fixture, testmain
from win32cryptcon import (
    CERT_QUERY_CONTENT_CERT,
    CERT_QUERY_CONTENT_FLAG_CERT,
    CERT_QUERY_FORMAT_BASE64_ENCODED,
    CERT_QUERY_FORMAT_BINARY,
    CERT_QUERY_FORMAT_FLAG_ALL,
    CERT_QUERY_OBJECT_BLOB,
    CERT_QUERY_OBJECT_FILE,
    CERT_STORE_ADD_REPLACE_EXISTING,
    CERT_STORE_PROV_SYSTEM,
    CERT_SYSTEM_STORE_CURRENT_USER,
    CERT_SYSTEM_STORE_LOCAL_MACHINE,
)


class Crypt(unittest.TestCase):
    def testSimple(self):
        data = b"My test data"
        entropy = None
        desc = "My description"
        flags = 0
        ps = None
        blob = win32crypt.CryptProtectData(data, desc, entropy, None, ps, flags)
        got_desc, got_data = win32crypt.CryptUnprotectData(
            blob, entropy, None, ps, flags
        )
        self.assertEqual(data, got_data)
        self.assertEqual(desc, got_desc)

    def testEntropy(self):
        data = b"My test data"
        entropy = b"My test entropy"
        desc = "My description"
        flags = 0
        ps = None
        blob = win32crypt.CryptProtectData(data, desc, entropy, None, ps, flags)
        got_desc, got_data = win32crypt.CryptUnprotectData(
            blob, entropy, None, ps, flags
        )
        self.assertEqual(data, got_data)
        self.assertEqual(desc, got_desc)


# via https://github.com/mhammond/pywin32/issues/1859
_LOCAL_MACHINE = "LocalMachine"
_CURRENT_USER = "CurrentUser"


@contextlib.contextmanager
def open_windows_certstore(store_name: str, store_location: str) -> Iterator[Any]:
    """Open a windows certificate store

    :param store_name: store name
    :param store_location: store location
    :return: handle to cert store
    """
    handle = None
    try:
        handle = win32crypt.CertOpenStore(
            CERT_STORE_PROV_SYSTEM,
            0,
            None,
            (
                CERT_SYSTEM_STORE_LOCAL_MACHINE
                if store_location == _LOCAL_MACHINE
                else CERT_SYSTEM_STORE_CURRENT_USER
            ),
            store_name,
        )
        yield handle
    finally:
        if handle is not None:
            handle.CertCloseStore()


class TestCerts(unittest.TestCase):
    def readCertFile(self, file_name):
        with open(find_test_fixture(file_name), "rb") as f:
            buf = bytearray(f.read())
            return win32crypt.CryptQueryObject(
                CERT_QUERY_OBJECT_BLOB,
                buf,
                CERT_QUERY_CONTENT_FLAG_CERT,
                CERT_QUERY_FORMAT_FLAG_ALL,
                0,
            )

    def testReadCertFiles(self):
        # readCertFile has Python read the file and load it as a blob.
        # win32crypt can read the file directly - let's check that works too
        # (ideally we'd compare the 2 approaches etc, but the objects don't support
        # equality checks etc, so this will do for now.)
        # No need to do this for different filenames!
        filename = "win32crypt_testcert_base64.cer"
        cert = win32crypt.CryptQueryObject(
            CERT_QUERY_OBJECT_FILE,
            find_test_fixture(filename),
            CERT_QUERY_CONTENT_FLAG_CERT,
            CERT_QUERY_FORMAT_FLAG_ALL,
            0,
        )
        self.assertEqual(cert["FormatType"], CERT_QUERY_FORMAT_BASE64_ENCODED)
        self.assertEqual(cert["ContentType"], CERT_QUERY_CONTENT_CERT)

    def checkCertFile(self, filename, expected_format):
        cert = self.readCertFile(filename)
        self.assertEqual(cert["FormatType"], expected_format)
        self.assertEqual(cert["ContentType"], CERT_QUERY_CONTENT_CERT)

        with open_windows_certstore(_CURRENT_USER, "Temp") as store:
            context = store.CertAddCertificateContextToStore(
                cert["Context"], CERT_STORE_ADD_REPLACE_EXISTING
            )
            # Getting 2 certs here - main thing is we get 1!
            self.assertTrue(len(store.CertEnumCertificatesInStore()))
            self.assertFalse(len(store.CertEnumCTLsInStore()))
            context.CertFreeCertificateContext()
            try:
                context.CertFreeCertificateContext()
            except ValueError:
                pass
            else:
                raise AssertionError("should not be able to close the context twice")

    def testCertBase64(self):
        self.checkCertFile(
            "win32crypt_testcert_base64.cer", CERT_QUERY_FORMAT_BASE64_ENCODED
        )

    def testCertBinary(self):
        self.checkCertFile("win32crypt_testcert_bin.cer", CERT_QUERY_FORMAT_BINARY)


if __name__ == "__main__":
    testmain()

# === NexusCore/openenv\Lib\site-packages\pyee\trio.py ===
# -*- coding: utf-8 -*-

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    cast,
    Dict,
    Optional,
    Tuple,
    Type,
)

import trio

from pyee.base import EventEmitter, PyeeError

Self = Any

__all__ = ["TrioEventEmitter"]


Nursery = trio.Nursery


class TrioEventEmitter(EventEmitter):
    """An event emitter class which can run trio tasks in a trio nursery.

    By default, this class will lazily create both a nursery manager (the
    object returned from `trio.open_nursery()` and a nursery (the object
    yielded by using the nursery manager as an async context manager). It is
    also possible to supply an existing nursery manager via the `manager`
    argument, or an existing nursery via the `nursery` argument.

    Instances of TrioEventEmitter are themselves async context managers, so
    that they may manage the lifecycle of the underlying trio nursery. For
    example, typical usage of this library may look something like this::

    ```py
    async with TrioEventEmitter() as ee:
        # Underlying nursery is instantiated and ready to go
        @ee.on('data')
        async def handler(data):
            print(data)

        ee.emit('event')

    # Underlying nursery and manager have been cleaned up
    ```

    Unlike the case with the EventEmitter, all exceptions raised by event
    handlers are automatically emitted on the `error` event. This is
    important for trio coroutines specifically but is also handled for
    synchronous functions for consistency.

    For trio coroutine event handlers, calling emit is non-blocking. In other
    words, you should not attempt to await emit; the coroutine is scheduled
    in a fire-and-forget fashion.
    """

    def __init__(
        self: Self,
        nursery: Optional[Nursery] = None,
        manager: Optional["AbstractAsyncContextManager[trio.Nursery]"] = None,
    ):
        super(TrioEventEmitter, self).__init__()
        self._nursery: Optional[Nursery] = None
        self._manager: Optional["AbstractAsyncContextManager[trio.Nursery]"] = None
        if nursery:
            if manager:
                raise PyeeError(
                    "You may either pass a nursery or a nursery manager " "but not both"
                )
            self._nursery = nursery
        elif manager:
            self._manager = manager
        else:
            self._manager = trio.open_nursery()

    def _async_runner(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Callable[[], Awaitable[None]]:
        async def runner() -> None:
            try:
                await f(*args, **kwargs)
            except Exception as exc:
                self.emit("error", exc)

        return runner

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        if not self._nursery:
            raise PyeeError("Uninitialized trio nursery")
        self._nursery.start_soon(self._async_runner(f, args, kwargs))

    @asynccontextmanager
    async def context(
        self: Self,
    ) -> AsyncGenerator["TrioEventEmitter", None]:
        """Returns an async contextmanager which manages the underlying
        nursery to the EventEmitter. The `TrioEventEmitter`'s
        async context management methods are implemented using this
        function, but it may also be used directly for clarity.
        """
        if self._nursery is not None:
            yield self
        elif self._manager is not None:
            async with self._manager as nursery:
                self._nursery = nursery
                yield self
        else:
            raise PyeeError("Uninitialized nursery or nursery manager")

    async def __aenter__(self: Self) -> "TrioEventEmitter":
        self._context: Optional[AbstractAsyncContextManager["TrioEventEmitter"]] = (
            self.context()
        )
        return await cast(Any, self._context).__aenter__()

    async def __aexit__(
        self: Self,
        type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        if self._context is None:
            raise PyeeError("Attempting to exit uninitialized context")
        rv = await self._context.__aexit__(type, value, traceback)
        self._context = None
        self._nursery = None
        self._manager = None
        return rv

# === NexusCore/openenv\Lib\site-packages\smmap\buf.py ===
"""Module with a simple buffer implementation using the memory manager"""
import sys

__all__ = ["SlidingWindowMapBuffer"]


class SlidingWindowMapBuffer:

    """A buffer like object which allows direct byte-wise object and slicing into
    memory of a mapped file. The mapping is controlled by the provided cursor.

    The buffer is relative, that is if you map an offset, index 0 will map to the
    first byte at the offset you used during initialization or begin_access

    **Note:** Although this type effectively hides the fact that there are mapped windows
    underneath, it can unfortunately not be used in any non-pure python method which
    needs a buffer or string"""
    __slots__ = (
        '_c',           # our cursor
        '_size',        # our supposed size
    )

    def __init__(self, cursor=None, offset=0, size=sys.maxsize, flags=0):
        """Initialize the instance to operate on the given cursor.
        :param cursor: if not None, the associated cursor to the file you want to access
            If None, you have call begin_access before using the buffer and provide a cursor
        :param offset: absolute offset in bytes
        :param size: the total size of the mapping. Defaults to the maximum possible size
            From that point on, the __len__ of the buffer will be the given size or the file size.
            If the size is larger than the mappable area, you can only access the actually available
            area, although the length of the buffer is reported to be your given size.
            Hence it is in your own interest to provide a proper size !
        :param flags: Additional flags to be passed to os.open
        :raise ValueError: if the buffer could not achieve a valid state"""
        self._c = cursor
        if cursor and not self.begin_access(cursor, offset, size, flags):
            raise ValueError("Failed to allocate the buffer - probably the given offset is out of bounds")
        # END handle offset

    def __del__(self):
        self.end_access()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_access()

    def __len__(self):
        return self._size

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__getslice__(i.start or 0, i.stop or self._size)
        c = self._c
        assert c.is_valid()
        if i < 0:
            i = self._size + i
        if not c.includes_ofs(i):
            c.use_region(i, 1)
        # END handle region usage
        return c.buffer()[i - c.ofs_begin()]

    def __getslice__(self, i, j):
        c = self._c
        # fast path, slice fully included - safes a concatenate operation and
        # should be the default
        assert c.is_valid()
        if i < 0:
            i = self._size + i
        if j == sys.maxsize:
            j = self._size
        if j < 0:
            j = self._size + j
        if (c.ofs_begin() <= i) and (j < c.ofs_end()):
            b = c.ofs_begin()
            return c.buffer()[i - b:j - b]
        else:
            l = j - i                 # total length
            ofs = i
            # It's fastest to keep tokens and join later, especially in py3, which was 7 times slower
            # in the previous iteration of this code
            md = list()
            while l:
                c.use_region(ofs, l)
                assert c.is_valid()
                d = c.buffer()[:l]
                ofs += len(d)
                l -= len(d)
                # Make sure we don't keep references, as c.use_region() might attempt to free resources, but
                # can't unless we use pure bytes
                if hasattr(d, 'tobytes'):
                    d = d.tobytes()
                md.append(d)
            # END while there are bytes to read
            return b''.join(md)
        # END fast or slow path
    #{ Interface

    def begin_access(self, cursor=None, offset=0, size=sys.maxsize, flags=0):
        """Call this before the first use of this instance. The method was already
        called by the constructor in case sufficient information was provided.

        For more information no the parameters, see the __init__ method
        :param path: if cursor is None the existing one will be used.
        :return: True if the buffer can be used"""
        if cursor:
            self._c = cursor
        # END update our cursor

        # reuse existing cursors if possible
        if self._c is not None and self._c.is_associated():
            res = self._c.use_region(offset, size, flags).is_valid()
            if res:
                # if given size is too large or default, we computer a proper size
                # If its smaller, we assume the combination between offset and size
                # as chosen by the user is correct and use it !
                # If not, the user is in trouble.
                if size > self._c.file_size():
                    size = self._c.file_size() - offset
                # END handle size
                self._size = size
            # END set size
            return res
        # END use our cursor
        return False

    def end_access(self):
        """Call this method once you are done using the instance. It is automatically
        called on destruction, and should be called just in time to allow system
        resources to be freed.

        Once you called end_access, you must call begin access before reusing this instance!"""
        self._size = 0
        if self._c is not None:
            self._c.unuse_region()
        # END unuse region

    def cursor(self):
        """:return: the currently set cursor which provides access to the data"""
        return self._c

    #}END interface

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\_debug_adapter\pydevd_base_schema.py ===
from _pydevd_bundle._debug_adapter.pydevd_schema_log import debug_exception
import json
import itertools
from functools import partial


class BaseSchema(object):
    @staticmethod
    def initialize_ids_translation():
        BaseSchema._dap_id_to_obj_id = {0: 0, None: None}
        BaseSchema._obj_id_to_dap_id = {0: 0, None: None}
        BaseSchema._next_dap_id = partial(next, itertools.count(1))

    def to_json(self):
        return json.dumps(self.to_dict())

    @staticmethod
    def _translate_id_to_dap(obj_id):
        if obj_id == "*":
            return "*"
        # Note: we don't invalidate ids, so, if some object starts using the same id
        # of another object, the same id will be used.
        dap_id = BaseSchema._obj_id_to_dap_id.get(obj_id)
        if dap_id is None:
            dap_id = BaseSchema._obj_id_to_dap_id[obj_id] = BaseSchema._next_dap_id()
            BaseSchema._dap_id_to_obj_id[dap_id] = obj_id
        return dap_id

    @staticmethod
    def _translate_id_from_dap(dap_id):
        if dap_id == "*":
            return "*"
        try:
            return BaseSchema._dap_id_to_obj_id[dap_id]
        except:
            raise KeyError("Wrong ID sent from the client: %s" % (dap_id,))

    @staticmethod
    def update_dict_ids_to_dap(dct):
        return dct

    @staticmethod
    def update_dict_ids_from_dap(dct):
        return dct


BaseSchema.initialize_ids_translation()

_requests_to_types = {}
_responses_to_types = {}
_event_to_types = {}
_all_messages = {}


def register(cls):
    _all_messages[cls.__name__] = cls
    return cls


def register_request(command):
    def do_register(cls):
        _requests_to_types[command] = cls
        return cls

    return do_register


def register_response(command):
    def do_register(cls):
        _responses_to_types[command] = cls
        return cls

    return do_register


def register_event(event):
    def do_register(cls):
        _event_to_types[event] = cls
        return cls

    return do_register


def from_dict(dct, update_ids_from_dap=False):
    msg_type = dct.get("type")
    if msg_type is None:
        raise ValueError("Unable to make sense of message: %s" % (dct,))

    if msg_type == "request":
        to_type = _requests_to_types
        use = dct["command"]

    elif msg_type == "response":
        to_type = _responses_to_types
        use = dct["command"]

    else:
        to_type = _event_to_types
        use = dct["event"]

    cls = to_type.get(use)
    if cls is None:
        raise ValueError("Unable to create message from dict: %s. %s not in %s" % (dct, use, sorted(to_type.keys())))
    try:
        return cls(update_ids_from_dap=update_ids_from_dap, **dct)
    except:
        msg = "Error creating %s from %s" % (cls, dct)
        debug_exception(msg)
        raise


def from_json(json_msg, update_ids_from_dap=False, on_dict_loaded=lambda dct: None):
    if isinstance(json_msg, bytes):
        json_msg = json_msg.decode("utf-8")

    as_dict = json.loads(json_msg)
    on_dict_loaded(as_dict)
    try:
        return from_dict(as_dict, update_ids_from_dap=update_ids_from_dap)
    except:
        if as_dict.get("type") == "response" and not as_dict.get("success"):
            # Error messages may not have required body (return as a generic Response).
            Response = _all_messages["Response"]
            return Response(**as_dict)
        else:
            raise


def get_response_class(request):
    if request.__class__ == dict:
        return _responses_to_types[request["command"]]
    return _responses_to_types[request.command]


def build_response(request, kwargs=None):
    if kwargs is None:
        kwargs = {"success": True}
    else:
        if "success" not in kwargs:
            kwargs["success"] = True
    response_class = _responses_to_types[request.command]
    kwargs.setdefault("seq", -1)  # To be overwritten before sending
    return response_class(command=request.command, request_seq=request.seq, **kwargs)

# === NexusCore/openenv\Lib\site-packages\fontTools\colorLib\geometry.py ===
"""Helpers for manipulating 2D points and vectors in COLR table."""

from math import copysign, cos, hypot, isclose, pi
from fontTools.misc.roundTools import otRound


def _vector_between(origin, target):
    return (target[0] - origin[0], target[1] - origin[1])


def _round_point(pt):
    return (otRound(pt[0]), otRound(pt[1]))


def _unit_vector(vec):
    length = hypot(*vec)
    if length == 0:
        return None
    return (vec[0] / length, vec[1] / length)


_CIRCLE_INSIDE_TOLERANCE = 1e-4


# The unit vector's X and Y components are respectively
#   U = (cos(α), sin(α))
# where α is the angle between the unit vector and the positive x axis.
_UNIT_VECTOR_THRESHOLD = cos(3 / 8 * pi)  # == sin(1/8 * pi) == 0.38268343236508984


def _rounding_offset(direction):
    # Return 2-tuple of -/+ 1.0 or 0.0 approximately based on the direction vector.
    # We divide the unit circle in 8 equal slices oriented towards the cardinal
    # (N, E, S, W) and intermediate (NE, SE, SW, NW) directions. To each slice we
    # map one of the possible cases: -1, 0, +1 for either X and Y coordinate.
    # E.g. Return (+1.0, -1.0) if unit vector is oriented towards SE, or
    # (-1.0, 0.0) if it's pointing West, etc.
    uv = _unit_vector(direction)
    if not uv:
        return (0, 0)

    result = []
    for uv_component in uv:
        if -_UNIT_VECTOR_THRESHOLD <= uv_component < _UNIT_VECTOR_THRESHOLD:
            # unit vector component near 0: direction almost orthogonal to the
            # direction of the current axis, thus keep coordinate unchanged
            result.append(0)
        else:
            # nudge coord by +/- 1.0 in direction of unit vector
            result.append(copysign(1.0, uv_component))
    return tuple(result)


class Circle:
    def __init__(self, centre, radius):
        self.centre = centre
        self.radius = radius

    def __repr__(self):
        return f"Circle(centre={self.centre}, radius={self.radius})"

    def round(self):
        return Circle(_round_point(self.centre), otRound(self.radius))

    def inside(self, outer_circle, tolerance=_CIRCLE_INSIDE_TOLERANCE):
        dist = self.radius + hypot(*_vector_between(self.centre, outer_circle.centre))
        return (
            isclose(outer_circle.radius, dist, rel_tol=_CIRCLE_INSIDE_TOLERANCE)
            or outer_circle.radius > dist
        )

    def concentric(self, other):
        return self.centre == other.centre

    def move(self, dx, dy):
        self.centre = (self.centre[0] + dx, self.centre[1] + dy)


def round_start_circle_stable_containment(c0, r0, c1, r1):
    """Round start circle so that it stays inside/outside end circle after rounding.

    The rounding of circle coordinates to integers may cause an abrupt change
    if the start circle c0 is so close to the end circle c1's perimiter that
    it ends up falling outside (or inside) as a result of the rounding.
    To keep the gradient unchanged, we nudge it in the right direction.

    See:
    https://github.com/googlefonts/colr-gradients-spec/issues/204
    https://github.com/googlefonts/picosvg/issues/158
    """
    start, end = Circle(c0, r0), Circle(c1, r1)

    inside_before_round = start.inside(end)

    round_start = start.round()
    round_end = end.round()
    inside_after_round = round_start.inside(round_end)

    if inside_before_round == inside_after_round:
        return round_start
    elif inside_after_round:
        # start was outside before rounding: we need to push start away from end
        direction = _vector_between(round_end.centre, round_start.centre)
        radius_delta = +1.0
    else:
        # start was inside before rounding: we need to push start towards end
        direction = _vector_between(round_start.centre, round_end.centre)
        radius_delta = -1.0
    dx, dy = _rounding_offset(direction)

    # At most 2 iterations ought to be enough to converge. Before the loop, we
    # know the start circle didn't keep containment after normal rounding; thus
    # we continue adjusting by -/+ 1.0 until containment is restored.
    # Normal rounding can at most move each coordinates -/+0.5; in the worst case
    # both the start and end circle's centres and radii will be rounded in opposite
    # directions, e.g. when they move along a 45 degree diagonal:
    #   c0 = (1.5, 1.5) ===> (2.0, 2.0)
    #   r0 = 0.5 ===> 1.0
    #   c1 = (0.499, 0.499) ===> (0.0, 0.0)
    #   r1 = 2.499 ===> 2.0
    # In this example, the relative distance between the circles, calculated
    # as r1 - (r0 + distance(c0, c1)) is initially 0.57437 (c0 is inside c1), and
    # -1.82842 after rounding (c0 is now outside c1). Nudging c0 by -1.0 on both
    # x and y axes moves it towards c1 by hypot(-1.0, -1.0) = 1.41421. Two of these
    # moves cover twice that distance, which is enough to restore containment.
    max_attempts = 2
    for _ in range(max_attempts):
        if round_start.concentric(round_end):
            # can't move c0 towards c1 (they are the same), so we change the radius
            round_start.radius += radius_delta
            assert round_start.radius >= 0
        else:
            round_start.move(dx, dy)
        if inside_before_round == round_start.inside(round_end):
            break
    else:  # likely a bug
        raise AssertionError(
            f"Rounding circle {start} "
            f"{'inside' if inside_before_round else 'outside'} "
            f"{end} failed after {max_attempts} attempts!"
        )

    return round_start

# === NexusCore/openenv\Lib\site-packages\fontTools\merge\util.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod, Roozbeh Pournader

from fontTools.misc.timeTools import timestampNow
from fontTools.ttLib.tables.DefaultTable import DefaultTable
from functools import reduce
import operator
import logging


log = logging.getLogger("fontTools.merge")


# General utility functions for merging values from different fonts


def equal(lst):
    lst = list(lst)
    t = iter(lst)
    first = next(t)
    assert all(item == first for item in t), "Expected all items to be equal: %s" % lst
    return first


def first(lst):
    return next(iter(lst))


def recalculate(lst):
    return NotImplemented


def current_time(lst):
    return timestampNow()


def bitwise_and(lst):
    return reduce(operator.and_, lst)


def bitwise_or(lst):
    return reduce(operator.or_, lst)


def avg_int(lst):
    lst = list(lst)
    return sum(lst) // len(lst)


def onlyExisting(func):
    """Returns a filter func that when called with a list,
    only calls func on the non-NotImplemented items of the list,
    and only so if there's at least one item remaining.
    Otherwise returns NotImplemented."""

    def wrapper(lst):
        items = [item for item in lst if item is not NotImplemented]
        return func(items) if items else NotImplemented

    return wrapper


def sumLists(lst):
    l = []
    for item in lst:
        l.extend(item)
    return l


def sumDicts(lst):
    d = {}
    for item in lst:
        d.update(item)
    return d


def mergeBits(bitmap):
    def wrapper(lst):
        lst = list(lst)
        returnValue = 0
        for bitNumber in range(bitmap["size"]):
            try:
                mergeLogic = bitmap[bitNumber]
            except KeyError:
                try:
                    mergeLogic = bitmap["*"]
                except KeyError:
                    raise Exception("Don't know how to merge bit %s" % bitNumber)
            shiftedBit = 1 << bitNumber
            mergedValue = mergeLogic(bool(item & shiftedBit) for item in lst)
            returnValue |= mergedValue << bitNumber
        return returnValue

    return wrapper


class AttendanceRecordingIdentityDict(object):
    """A dictionary-like object that records indices of items actually accessed
    from a list."""

    def __init__(self, lst):
        self.l = lst
        self.d = {id(v): i for i, v in enumerate(lst)}
        self.s = set()

    def __getitem__(self, v):
        self.s.add(self.d[id(v)])
        return v


class GregariousIdentityDict(object):
    """A dictionary-like object that welcomes guests without reservations and
    adds them to the end of the guest list."""

    def __init__(self, lst):
        self.l = lst
        self.s = set(id(v) for v in lst)

    def __getitem__(self, v):
        if id(v) not in self.s:
            self.s.add(id(v))
            self.l.append(v)
        return v


class NonhashableDict(object):
    """A dictionary-like object mapping objects to values."""

    def __init__(self, keys, values=None):
        if values is None:
            self.d = {id(v): i for i, v in enumerate(keys)}
        else:
            self.d = {id(k): v for k, v in zip(keys, values)}

    def __getitem__(self, k):
        return self.d[id(k)]

    def __setitem__(self, k, v):
        self.d[id(k)] = v

    def __delitem__(self, k):
        del self.d[id(k)]

# === NexusCore/openenv\Lib\site-packages\google\auth\aio\credentials.py ===
# Copyright 2024 Google LLC
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


"""Interfaces for asynchronous credentials."""


from google.auth import _helpers
from google.auth import exceptions
from google.auth._credentials_base import _BaseCredentials


class Credentials(_BaseCredentials):
    """Base class for all asynchronous credentials.

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

    async def apply(self, headers, token=None):
        """Apply the token to the authentication header.

        Args:
            headers (Mapping): The HTTP request headers.
            token (Optional[str]): If specified, overrides the current access
                token.
        """
        self._apply(headers, token=token)

    async def refresh(self, request):
        """Refreshes the access token.

        Args:
            request (google.auth.aio.transport.Request): The object used to make
                HTTP requests.

        Raises:
            google.auth.exceptions.RefreshError: If the credentials could
                not be refreshed.
        """
        raise NotImplementedError("Refresh must be implemented")

    async def before_request(self, request, method, url, headers):
        """Performs credential-specific before request logic.

        Refreshes the credentials if necessary, then calls :meth:`apply` to
        apply the token to the authentication header.

        Args:
            request (google.auth.aio.transport.Request): The object used to make
                HTTP requests.
            method (str): The request's HTTP method or the RPC method being
                invoked.
            url (str): The request's URI or the RPC service's URI.
            headers (Mapping): The request's headers.
        """
        await self.apply(headers)


class StaticCredentials(Credentials):
    """Asynchronous Credentials representing an immutable access token.

    The credentials are considered immutable except the tokens which can be
    configured in the constructor ::

        credentials = StaticCredentials(token="token123")

    StaticCredentials does not support :meth `refresh` and assumes that the configured
    token is valid and not expired. StaticCredentials will never attempt to
    refresh the token.
    """

    def __init__(self, token):
        """
        Args:
            token (str): The access token.
        """
        super(StaticCredentials, self).__init__()
        self.token = token

    @_helpers.copy_docstring(Credentials)
    async def refresh(self, request):
        raise exceptions.InvalidOperation("Static credentials cannot be refreshed.")

    # Note: before_request should never try to refresh access tokens.
    # StaticCredentials intentionally does not support it.
    @_helpers.copy_docstring(Credentials)
    async def before_request(self, request, method, url, headers):
        await self.apply(headers)


class AnonymousCredentials(Credentials):
    """Asynchronous Credentials that do not provide any authentication information.

    These are useful in the case of services that support anonymous access or
    local service emulators that do not use credentials.
    """

    async def refresh(self, request):
        """Raises :class:``InvalidOperation``, anonymous credentials cannot be
        refreshed."""
        raise exceptions.InvalidOperation("Anonymous credentials cannot be refreshed.")

    async def apply(self, headers, token=None):
        """Anonymous credentials do nothing to the request.

        The optional ``token`` argument is not supported.

        Raises:
            google.auth.exceptions.InvalidValue: If a token was specified.
        """
        if token is not None:
            raise exceptions.InvalidValue("Anonymous credentials don't support tokens.")

    async def before_request(self, request, method, url, headers):
        """Anonymous credentials do nothing to the request."""
        pass

# === NexusCore/openenv\Lib\site-packages\google\generativeai\types\file_types.py ===
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
from __future__ import annotations

import datetime
from typing import Any, Union
from typing_extensions import TypedDict

from google.rpc.status_pb2 import Status
from google.generativeai.client import get_default_file_client

from google.generativeai import protos

import pprint


class File:
    def __init__(self, proto: protos.File | File | dict):
        if isinstance(proto, File):
            proto = proto.to_proto()
        self._proto = protos.File(proto)

    def to_proto(self) -> protos.File:
        return self._proto

    def to_dict(self) -> dict[str, Any]:
        return type(self._proto).to_dict(self._proto, use_integers_for_enums=False)

    def __str__(self):
        def sort_key(pair):
            name, value = pair
            if name == "name":
                return ""
            elif "time" in name:
                return "zz_" + name
            else:
                return name

        dict_format = dict(sorted(self.to_dict().items(), key=sort_key))
        dict_format = pprint.pformat(dict_format, sort_dicts=False)
        dict_format = "{\n " + dict_format[1:]
        dict_format = "\n   ".join(dict_format.splitlines())
        return dict_format.join(["genai.File(", ")"])

    __repr__ = __str__

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def display_name(self) -> str:
        return self._proto.display_name

    @property
    def mime_type(self) -> str:
        return self._proto.mime_type

    @property
    def size_bytes(self) -> int:
        return self._proto.size_bytes

    @property
    def create_time(self) -> datetime.datetime:
        return self._proto.create_time

    @property
    def update_time(self) -> datetime.datetime:
        return self._proto.update_time

    @property
    def expiration_time(self) -> datetime.datetime:
        return self._proto.expiration_time

    @property
    def sha256_hash(self) -> bytes:
        return self._proto.sha256_hash

    @property
    def uri(self) -> str:
        return self._proto.uri

    @property
    def state(self) -> protos.File.State:
        return self._proto.state

    @property
    def video_metadata(self) -> protos.VideoMetadata:
        return self._proto.video_metadata

    @property
    def error(self) -> Status:
        return self._proto.error

    def delete(self):
        client = get_default_file_client()
        client.delete_file(name=self.name)


class FileDataDict(TypedDict):
    mime_type: str
    file_uri: str


FileDataType = Union[FileDataDict, protos.FileData, protos.File, File]


def to_file_data(file_data: FileDataType):
    if isinstance(file_data, dict):
        if "file_uri" in file_data:
            file_data = protos.FileData(file_data)
        else:
            file_data = protos.File(file_data)

    if isinstance(file_data, File):
        file_data = file_data.to_proto()

    if isinstance(file_data, protos.File):
        file_data = protos.FileData(
            mime_type=file_data.mime_type,
            file_uri=file_data.uri,
        )

    if isinstance(file_data, protos.FileData):
        return file_data
    else:
        raise TypeError(
            f"Invalid input type. Failed to convert input to `FileData`.\n"
            f"Received an object of type: {type(file_data)}.\n"
            f"Object Value: {file_data}"
        )

# === NexusCore/openenv\Lib\site-packages\httpcore\_backends\mock.py ===
from __future__ import annotations

import ssl
import typing

from .._exceptions import ReadError
from .base import (
    SOCKET_OPTION,
    AsyncNetworkBackend,
    AsyncNetworkStream,
    NetworkBackend,
    NetworkStream,
)


class MockSSLObject:
    def __init__(self, http2: bool):
        self._http2 = http2

    def selected_alpn_protocol(self) -> str:
        return "h2" if self._http2 else "http/1.1"


class MockStream(NetworkStream):
    def __init__(self, buffer: list[bytes], http2: bool = False) -> None:
        self._buffer = buffer
        self._http2 = http2
        self._closed = False

    def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self._closed:
            raise ReadError("Connection closed")
        if not self._buffer:
            return b""
        return self._buffer.pop(0)

    def write(self, buffer: bytes, timeout: float | None = None) -> None:
        pass

    def close(self) -> None:
        self._closed = True

    def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> NetworkStream:
        return self

    def get_extra_info(self, info: str) -> typing.Any:
        return MockSSLObject(http2=self._http2) if info == "ssl_object" else None

    def __repr__(self) -> str:
        return "<httpcore.MockStream>"


class MockBackend(NetworkBackend):
    def __init__(self, buffer: list[bytes], http2: bool = False) -> None:
        self._buffer = buffer
        self._http2 = http2

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:
        return MockStream(list(self._buffer), http2=self._http2)

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:
        return MockStream(list(self._buffer), http2=self._http2)

    def sleep(self, seconds: float) -> None:
        pass


class AsyncMockStream(AsyncNetworkStream):
    def __init__(self, buffer: list[bytes], http2: bool = False) -> None:
        self._buffer = buffer
        self._http2 = http2
        self._closed = False

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        if self._closed:
            raise ReadError("Connection closed")
        if not self._buffer:
            return b""
        return self._buffer.pop(0)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        pass

    async def aclose(self) -> None:
        self._closed = True

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> AsyncNetworkStream:
        return self

    def get_extra_info(self, info: str) -> typing.Any:
        return MockSSLObject(http2=self._http2) if info == "ssl_object" else None

    def __repr__(self) -> str:
        return "<httpcore.AsyncMockStream>"


class AsyncMockBackend(AsyncNetworkBackend):
    def __init__(self, buffer: list[bytes], http2: bool = False) -> None:
        self._buffer = buffer
        self._http2 = http2

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:
        return AsyncMockStream(list(self._buffer), http2=self._http2)

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: typing.Iterable[SOCKET_OPTION] | None = None,
    ) -> AsyncNetworkStream:
        return AsyncMockStream(list(self._buffer), http2=self._http2)

    async def sleep(self, seconds: float) -> None:
        pass

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\tag_based_routing.py ===
"""
Use this to route requests between Teams

- If tags in request is a subset of tags in deployment, return deployment
- if deployments are set with default tags, return all default deployment
- If no default_deployments are set, return all deployments
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from litellm._logging import verbose_logger
from litellm.types.router import RouterErrors

if TYPE_CHECKING:
    from litellm.router import Router as _Router

    LitellmRouter = _Router
else:
    LitellmRouter = Any


def is_valid_deployment_tag(
    deployment_tags: List[str], request_tags: List[str]
) -> bool:
    """
    Check if a tag is valid
    """

    if any(tag in deployment_tags for tag in request_tags):
        verbose_logger.debug(
            "adding deployment with tags: %s, request tags: %s",
            deployment_tags,
            request_tags,
        )
        return True
    return False


async def get_deployments_for_tag(
    llm_router_instance: LitellmRouter,
    model: str,  # used to raise the correct error
    healthy_deployments: Union[List[Any], Dict[Any, Any]],
    request_kwargs: Optional[Dict[Any, Any]] = None,
):
    """
    Returns a list of deployments that match the requested model and tags in the request.

    Executes tag based filtering based on the tags in request metadata and the tags on the deployments
    """
    if llm_router_instance.enable_tag_filtering is not True:
        return healthy_deployments

    if request_kwargs is None:
        verbose_logger.debug(
            "get_deployments_for_tag: request_kwargs is None returning healthy_deployments: %s",
            healthy_deployments,
        )
        return healthy_deployments

    if healthy_deployments is None:
        verbose_logger.debug(
            "get_deployments_for_tag: healthy_deployments is None returning healthy_deployments"
        )
        return healthy_deployments

    verbose_logger.debug("request metadata: %s", request_kwargs.get("metadata"))
    if "metadata" in request_kwargs:
        metadata = request_kwargs["metadata"]
        request_tags = metadata.get("tags")

        new_healthy_deployments = []
        default_deployments = []
        if request_tags:
            verbose_logger.debug(
                "get_deployments_for_tag routing: router_keys: %s", request_tags
            )
            # example this can be router_keys=["free", "custom"]
            # get all deployments that have a superset of these router keys
            for deployment in healthy_deployments:
                deployment_litellm_params = deployment.get("litellm_params")
                deployment_tags = deployment_litellm_params.get("tags")

                verbose_logger.debug(
                    "deployment: %s,  deployment_router_keys: %s",
                    deployment,
                    deployment_tags,
                )

                if deployment_tags is None:
                    continue

                if is_valid_deployment_tag(deployment_tags, request_tags):
                    new_healthy_deployments.append(deployment)

                if "default" in deployment_tags:
                    default_deployments.append(deployment)

            if len(new_healthy_deployments) == 0 and len(default_deployments) == 0:
                raise ValueError(
                    f"{RouterErrors.no_deployments_with_tag_routing.value}. Passed model={model} and tags={request_tags}"
                )

            return new_healthy_deployments if len(new_healthy_deployments) > 0 else default_deployments

    # for Untagged requests use default deployments if set
    _default_deployments_with_tags = []
    for deployment in healthy_deployments:
        if "default" in deployment.get("litellm_params", {}).get("tags", []):
            _default_deployments_with_tags.append(deployment)

    if len(_default_deployments_with_tags) > 0:
        return _default_deployments_with_tags

    # if no default deployment is found, return healthy_deployments
    verbose_logger.debug(
        "no tier found in metadata, returning healthy_deployments: %s",
        healthy_deployments,
    )
    return healthy_deployments


def _get_tags_from_request_kwargs(
    request_kwargs: Optional[Dict[Any, Any]] = None
) -> List[str]:
    """
    Helper to get tags from request kwargs

    Args:
        request_kwargs: The request kwargs to get tags from

    Returns:
        List[str]: The tags from the request kwargs
    """
    if request_kwargs is None:
        return []
    if "metadata" in request_kwargs:
        metadata = request_kwargs["metadata"]
        return metadata.get("tags", [])
    elif "litellm_params" in request_kwargs:
        litellm_params = request_kwargs["litellm_params"]
        _metadata = litellm_params.get("metadata", {})
        return _metadata.get("tags", [])
    return []

# === NexusCore/openenv\Lib\site-packages\litellm\secret_managers\aws_secret_manager.py ===
"""
This is a file for the AWS Secret Manager Integration

Relevant issue: https://github.com/BerriAI/litellm/issues/1883

Requires:
* `os.environ["AWS_REGION_NAME"], 
* `pip install boto3>=1.28.57`
"""

import ast
import base64
import os
import re
from typing import Any, Dict, Optional

import litellm
from litellm.proxy._types import KeyManagementSystem


def validate_environment():
    if "AWS_REGION_NAME" not in os.environ:
        raise ValueError("Missing required environment variable - AWS_REGION_NAME")


def load_aws_kms(use_aws_kms: Optional[bool]):
    if use_aws_kms is None or use_aws_kms is False:
        return
    try:
        import boto3

        validate_environment()

        # Create a Secrets Manager client
        kms_client = boto3.client("kms", region_name=os.getenv("AWS_REGION_NAME"))

        litellm.secret_manager_client = kms_client
        litellm._key_management_system = KeyManagementSystem.AWS_KMS

    except Exception as e:
        raise e


class AWSKeyManagementService_V2:
    """
    V2 Clean Class for decrypting keys from AWS KeyManagementService
    """

    def __init__(self) -> None:
        self.validate_environment()
        self.kms_client = self.load_aws_kms(use_aws_kms=True)

    def validate_environment(
        self,
    ):
        if "AWS_REGION_NAME" not in os.environ:
            raise ValueError("Missing required environment variable - AWS_REGION_NAME")

        ## CHECK IF LICENSE IN ENV ## - premium feature
        is_litellm_license_in_env: bool = False

        if os.getenv("LITELLM_LICENSE", None) is not None:
            is_litellm_license_in_env = True
        elif os.getenv("LITELLM_SECRET_AWS_KMS_LITELLM_LICENSE", None) is not None:
            is_litellm_license_in_env = True
        if is_litellm_license_in_env is False:
            raise ValueError(
                "AWSKeyManagementService V2 is an Enterprise Feature. Please add a valid LITELLM_LICENSE to your envionment."
            )

    def load_aws_kms(self, use_aws_kms: Optional[bool]):
        if use_aws_kms is None or use_aws_kms is False:
            return
        try:
            import boto3

            validate_environment()

            # Create a Secrets Manager client
            kms_client = boto3.client("kms", region_name=os.getenv("AWS_REGION_NAME"))

            return kms_client
        except Exception as e:
            raise e

    def decrypt_value(self, secret_name: str) -> Any:
        if self.kms_client is None:
            raise ValueError("kms_client is None")
        encrypted_value = os.getenv(secret_name, None)
        if encrypted_value is None:
            raise Exception(
                "AWS KMS - Encrypted Value of Key={} is None".format(secret_name)
            )
        if isinstance(encrypted_value, str) and encrypted_value.startswith("aws_kms/"):
            encrypted_value = encrypted_value.replace("aws_kms/", "")

        # Decode the base64 encoded ciphertext
        ciphertext_blob = base64.b64decode(encrypted_value)

        # Set up the parameters for the decrypt call
        params = {"CiphertextBlob": ciphertext_blob}
        # Perform the decryption
        response = self.kms_client.decrypt(**params)

        # Extract and decode the plaintext
        plaintext = response["Plaintext"]
        secret = plaintext.decode("utf-8")
        if isinstance(secret, str):
            secret = secret.strip()
        try:
            secret_value_as_bool = ast.literal_eval(secret)
            if isinstance(secret_value_as_bool, bool):
                return secret_value_as_bool
        except Exception:
            pass

        return secret


"""
- look for all values in the env with `aws_kms/<hashed_key>` 
- decrypt keys 
- rewrite env var with decrypted key (). Note: this environment variable will only be available to the current process and any child processes spawned from it. Once the Python script ends, the environment variable will not persist.
"""


def decrypt_env_var() -> Dict[str, Any]:
    # setup client class
    aws_kms = AWSKeyManagementService_V2()
    # iterate through env - for `aws_kms/`
    new_values = {}
    for k, v in os.environ.items():
        if (
            k is not None
            and isinstance(k, str)
            and k.lower().startswith("litellm_secret_aws_kms")
        ) or (v is not None and isinstance(v, str) and v.startswith("aws_kms/")):
            decrypted_value = aws_kms.decrypt_value(secret_name=k)
            # reset env var
            k = re.sub("litellm_secret_aws_kms_", "", k, flags=re.IGNORECASE)
            new_values[k] = decrypted_value

    return new_values

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\embed\v1_transformation.py ===
"""
Legacy /v1/embedding transformation logic for Bedrock Cohere. 
"""

from typing import Any, List, Optional, Union

import httpx

from litellm import COHERE_DEFAULT_EMBEDDING_INPUT_TYPE
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.types.llms.bedrock import (
    CohereEmbeddingRequest,
    CohereEmbeddingRequestWithModel,
)
from litellm.types.utils import EmbeddingResponse, PromptTokensDetailsWrapper, Usage
from litellm.utils import is_base64_encoded


class CohereEmbeddingConfig:
    """
    Reference: https://docs.cohere.com/v2/reference/embed
    """

    def __init__(self) -> None:
        pass

    def get_supported_openai_params(self) -> List[str]:
        return ["encoding_format"]

    def map_openai_params(
        self, non_default_params: dict, optional_params: dict
    ) -> dict:
        for k, v in non_default_params.items():
            if k == "encoding_format":
                optional_params["embedding_types"] = v
        return optional_params

    def _is_v3_model(self, model: str) -> bool:
        return "3" in model

    def _transform_request(
        self, model: str, input: List[str], inference_params: dict
    ) -> CohereEmbeddingRequestWithModel:
        is_encoded = False
        for input_str in input:
            is_encoded = is_base64_encoded(input_str)

        if is_encoded:  # check if string is b64 encoded image or not
            transformed_request = CohereEmbeddingRequestWithModel(
                model=model,
                images=input,
                input_type="image",
            )
        else:
            transformed_request = CohereEmbeddingRequestWithModel(
                model=model,
                texts=input,
                input_type=COHERE_DEFAULT_EMBEDDING_INPUT_TYPE,
            )

        for k, v in inference_params.items():
            transformed_request[k] = v  # type: ignore

        return transformed_request

    def _calculate_usage(self, input: List[str], encoding: Any, meta: dict) -> Usage:
        input_tokens = 0

        text_tokens: Optional[int] = meta.get("billed_units", {}).get("input_tokens")

        image_tokens: Optional[int] = meta.get("billed_units", {}).get("images")

        prompt_tokens_details: Optional[PromptTokensDetailsWrapper] = None
        if image_tokens is None and text_tokens is None:
            for text in input:
                input_tokens += len(encoding.encode(text))
        else:
            prompt_tokens_details = PromptTokensDetailsWrapper(
                image_tokens=image_tokens,
                text_tokens=text_tokens,
            )
            if image_tokens:
                input_tokens += image_tokens
            if text_tokens:
                input_tokens += text_tokens

        return Usage(
            prompt_tokens=input_tokens,
            completion_tokens=0,
            total_tokens=input_tokens,
            prompt_tokens_details=prompt_tokens_details,
        )

    def _transform_response(
        self,
        response: httpx.Response,
        api_key: Optional[str],
        logging_obj: LiteLLMLoggingObj,
        data: Union[dict, CohereEmbeddingRequest],
        model_response: EmbeddingResponse,
        model: str,
        encoding: Any,
        input: list,
    ) -> EmbeddingResponse:
        response_json = response.json()
        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=response_json,
        )
        """
            response 
            {
                'object': "list",
                'data': [
                
                ]
                'model', 
                'usage'
            }
        """
        embeddings = response_json["embeddings"]
        output_data = []
        for idx, embedding in enumerate(embeddings):
            output_data.append(
                {"object": "embedding", "index": idx, "embedding": embedding}
            )
        model_response.object = "list"
        model_response.data = output_data
        model_response.model = model
        input_tokens = 0
        for text in input:
            input_tokens += len(encoding.encode(text))

        setattr(
            model_response,
            "usage",
            self._calculate_usage(input, encoding, response_json.get("meta", {})),
        )

        return model_response

# === NexusCore/openenv\Lib\site-packages\litellm\llms\jina_ai\rerank\transformation.py ===
"""
Transformation logic from Cohere's /v1/rerank format to Jina AI's  `/v1/rerank` format. 

Why separate file? Make it easy to see how transformation works

Docs - https://jina.ai/reranker
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from httpx import URL, Response

from litellm.llms.base_llm.chat.transformation import LiteLLMLoggingObj
from litellm.llms.base_llm.rerank.transformation import BaseRerankConfig
from litellm.types.rerank import (
    OptionalRerankParams,
    RerankBilledUnits,
    RerankResponse,
    RerankResponseMeta,
    RerankTokens,
)
from litellm.types.utils import ModelInfo


class JinaAIRerankConfig(BaseRerankConfig):
    def get_supported_cohere_rerank_params(self, model: str) -> list:
        return [
            "query",
            "top_n",
            "documents",
            "return_documents",
        ]

    def map_cohere_rerank_params(
        self,
        non_default_params: dict,
        model: str,
        drop_params: bool,
        query: str,
        documents: List[Union[str, Dict[str, Any]]],
        custom_llm_provider: Optional[str] = None,
        top_n: Optional[int] = None,
        rank_fields: Optional[List[str]] = None,
        return_documents: Optional[bool] = True,
        max_chunks_per_doc: Optional[int] = None,
        max_tokens_per_doc: Optional[int] = None,
    ) -> OptionalRerankParams:
        optional_params = {}
        supported_params = self.get_supported_cohere_rerank_params(model)
        for k, v in non_default_params.items():
            if k in supported_params:
                optional_params[k] = v
        return OptionalRerankParams(
            **optional_params,
        )

    def get_complete_url(self, api_base: Optional[str], model: str) -> str:
        base_path = "/v1/rerank"

        if api_base is None:
            return "https://api.jina.ai/v1/rerank"
        base = URL(api_base)
        # Reconstruct URL with cleaned path
        cleaned_base = str(base.copy_with(path=base_path))

        return cleaned_base

    def transform_rerank_request(
        self, model: str, optional_rerank_params: OptionalRerankParams, headers: Dict
    ) -> Dict:
        return {"model": model, **optional_rerank_params}

    def transform_rerank_response(
        self,
        model: str,
        raw_response: Response,
        model_response: RerankResponse,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str] = None,
        request_data: Dict = {},
        optional_params: Dict = {},
        litellm_params: Dict = {},
    ) -> RerankResponse:
        if raw_response.status_code != 200:
            raise Exception(raw_response.text)

        logging_obj.post_call(original_response=raw_response.text)

        _json_response = raw_response.json()

        _billed_units = RerankBilledUnits(**_json_response.get("usage", {}))
        _tokens = RerankTokens(**_json_response.get("usage", {}))
        rerank_meta = RerankResponseMeta(billed_units=_billed_units, tokens=_tokens)

        _results: Optional[List[dict]] = _json_response.get("results")

        if _results is None:
            raise ValueError(f"No results found in the response={_json_response}")

        return RerankResponse(
            id=_json_response.get("id") or str(uuid.uuid4()),
            results=_results,  # type: ignore
            meta=rerank_meta,
        )  # Return response

    def validate_environment(
        self, headers: Dict, model: str, api_key: Optional[str] = None
    ) -> Dict:
        if api_key is None:
            raise ValueError(
                "api_key is required. Set via `api_key` parameter or `JINA_API_KEY` environment variable."
            )
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        }

    def calculate_rerank_cost(
        self,
        model: str,
        custom_llm_provider: Optional[str] = None,
        billed_units: Optional[RerankBilledUnits] = None,
        model_info: Optional[ModelInfo] = None,
    ) -> Tuple[float, float]:
        """
        Jina AI reranker is priced at $0.000000018 per token.
        """
        if (
            model_info is None
            or "input_cost_per_token" not in model_info
            or model_info["input_cost_per_token"] is None
            or billed_units is None
        ):
            return 0.0, 0.0

        total_tokens = billed_units.get("total_tokens")
        if total_tokens is None:
            return 0.0, 0.0

        input_cost = model_info["input_cost_per_token"] * total_tokens
        return input_cost, 0.0

# === NexusCore/openenv\Lib\site-packages\nltk\classify\scikitlearn.py ===
# Natural Language Toolkit: Interface to scikit-learn classifiers
#
# Author: Lars Buitinck <L.J.Buitinck@uva.nl>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
scikit-learn (https://scikit-learn.org) is a machine learning library for
Python. It supports many classification algorithms, including SVMs,
Naive Bayes, logistic regression (MaxEnt) and decision trees.

This package implements a wrapper around scikit-learn classifiers. To use this
wrapper, construct a scikit-learn estimator object, then use that to construct
a SklearnClassifier. E.g., to wrap a linear SVM with default settings:

>>> from sklearn.svm import LinearSVC
>>> from nltk.classify.scikitlearn import SklearnClassifier
>>> classif = SklearnClassifier(LinearSVC())

A scikit-learn classifier may include preprocessing steps when it's wrapped
in a Pipeline object. The following constructs and wraps a Naive Bayes text
classifier with tf-idf weighting and chi-square feature selection to get the
best 1000 features:

>>> from sklearn.feature_extraction.text import TfidfTransformer
>>> from sklearn.feature_selection import SelectKBest, chi2
>>> from sklearn.naive_bayes import MultinomialNB
>>> from sklearn.pipeline import Pipeline
>>> pipeline = Pipeline([('tfidf', TfidfTransformer()),
...                      ('chi2', SelectKBest(chi2, k=1000)),
...                      ('nb', MultinomialNB())])
>>> classif = SklearnClassifier(pipeline)
"""

from nltk.classify.api import ClassifierI
from nltk.probability import DictionaryProbDist

try:
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import LabelEncoder
except ImportError:
    pass

__all__ = ["SklearnClassifier"]


class SklearnClassifier(ClassifierI):
    """Wrapper for scikit-learn classifiers."""

    def __init__(self, estimator, dtype=float, sparse=True):
        """
        :param estimator: scikit-learn classifier object.

        :param dtype: data type used when building feature array.
            scikit-learn estimators work exclusively on numeric data. The
            default value should be fine for almost all situations.

        :param sparse: Whether to use sparse matrices internally.
            The estimator must support these; not all scikit-learn classifiers
            do (see their respective documentation and look for "sparse
            matrix"). The default value is True, since most NLP problems
            involve sparse feature sets. Setting this to False may take a
            great amount of memory.
        :type sparse: boolean.
        """
        self._clf = estimator
        self._encoder = LabelEncoder()
        self._vectorizer = DictVectorizer(dtype=dtype, sparse=sparse)

    def __repr__(self):
        return "<SklearnClassifier(%r)>" % self._clf

    def classify_many(self, featuresets):
        """Classify a batch of samples.

        :param featuresets: An iterable over featuresets, each a dict mapping
            strings to either numbers, booleans or strings.
        :return: The predicted class label for each input sample.
        :rtype: list
        """
        X = self._vectorizer.transform(featuresets)
        classes = self._encoder.classes_
        return [classes[i] for i in self._clf.predict(X)]

    def prob_classify_many(self, featuresets):
        """Compute per-class probabilities for a batch of samples.

        :param featuresets: An iterable over featuresets, each a dict mapping
            strings to either numbers, booleans or strings.
        :rtype: list of ``ProbDistI``
        """
        X = self._vectorizer.transform(featuresets)
        y_proba_list = self._clf.predict_proba(X)
        return [self._make_probdist(y_proba) for y_proba in y_proba_list]

    def labels(self):
        """The class labels used by this classifier.

        :rtype: list
        """
        return list(self._encoder.classes_)

    def train(self, labeled_featuresets):
        """
        Train (fit) the scikit-learn estimator.

        :param labeled_featuresets: A list of ``(featureset, label)``
            where each ``featureset`` is a dict mapping strings to either
            numbers, booleans or strings.
        """

        X, y = list(zip(*labeled_featuresets))
        X = self._vectorizer.fit_transform(X)
        y = self._encoder.fit_transform(y)
        self._clf.fit(X, y)

        return self

    def _make_probdist(self, y_proba):
        classes = self._encoder.classes_
        return DictionaryProbDist({classes[i]: p for i, p in enumerate(y_proba)})


if __name__ == "__main__":
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import BernoulliNB

    from nltk.classify.util import names_demo, names_demo_features

    # Bernoulli Naive Bayes is designed for binary classification. We set the
    # binarize option to False since we know we're passing boolean features.
    print("scikit-learn Naive Bayes:")
    names_demo(
        SklearnClassifier(BernoulliNB(binarize=False)).train,
        features=names_demo_features,
    )

    # The C parameter on logistic regression (MaxEnt) controls regularization.
    # The higher it's set, the less regularized the classifier is.
    print("\n\nscikit-learn logistic regression:")
    names_demo(
        SklearnClassifier(LogisticRegression(C=1000)).train,
        features=names_demo_features,
    )

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\common_rules.py ===
"""
Build common block mechanism for f2py2e.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
"""
from . import __version__

f2py_version = __version__.version

from . import capi_maps, func2subr
from .auxfuncs import getuseblocks, hasbody, hascommon, hasnote, isintent_hide, outmess
from .crackfortran import rmbadname


def findcommonblocks(block, top=1):
    ret = []
    if hascommon(block):
        for key, value in block['common'].items():
            vars_ = {v: block['vars'][v] for v in value}
            ret.append((key, value, vars_))
    elif hasbody(block):
        for b in block['body']:
            ret = ret + findcommonblocks(b, 0)
    if top:
        tret = []
        names = []
        for t in ret:
            if t[0] not in names:
                names.append(t[0])
                tret.append(t)
        return tret
    return ret


def buildhooks(m):
    ret = {'commonhooks': [], 'initcommonhooks': [],
           'docs': ['"COMMON blocks:\\n"']}
    fwrap = ['']

    def fadd(line, s=fwrap):
        s[0] = f'{s[0]}\n      {line}'
    chooks = ['']

    def cadd(line, s=chooks):
        s[0] = f'{s[0]}\n{line}'
    ihooks = ['']

    def iadd(line, s=ihooks):
        s[0] = f'{s[0]}\n{line}'
    doc = ['']

    def dadd(line, s=doc):
        s[0] = f'{s[0]}\n{line}'
    for (name, vnames, vars) in findcommonblocks(m):
        lower_name = name.lower()
        hnames, inames = [], []
        for n in vnames:
            if isintent_hide(vars[n]):
                hnames.append(n)
            else:
                inames.append(n)
        if hnames:
            outmess('\t\tConstructing COMMON block support for "%s"...\n\t\t  %s\n\t\t  Hidden: %s\n' % (
                name, ','.join(inames), ','.join(hnames)))
        else:
            outmess('\t\tConstructing COMMON block support for "%s"...\n\t\t  %s\n' % (
                name, ','.join(inames)))
        fadd(f'subroutine f2pyinit{name}(setupfunc)')
        for usename in getuseblocks(m):
            fadd(f'use {usename}')
        fadd('external setupfunc')
        for n in vnames:
            fadd(func2subr.var2fixfortran(vars, n))
        if name == '_BLNK_':
            fadd(f"common {','.join(vnames)}")
        else:
            fadd(f"common /{name}/ {','.join(vnames)}")
        fadd(f"call setupfunc({','.join(inames)})")
        fadd('end\n')
        cadd('static FortranDataDef f2py_%s_def[] = {' % (name))
        idims = []
        for n in inames:
            ct = capi_maps.getctype(vars[n])
            elsize = capi_maps.get_elsize(vars[n])
            at = capi_maps.c2capi_map[ct]
            dm = capi_maps.getarrdims(n, vars[n])
            if dm['dims']:
                idims.append(f"({dm['dims']})")
            else:
                idims.append('')
            dms = dm['dims'].strip()
            if not dms:
                dms = '-1'
            cadd('\t{\"%s\",%s,{{%s}},%s, %s},'
                 % (n, dm['rank'], dms, at, elsize))
        cadd('\t{NULL}\n};')
        inames1 = rmbadname(inames)
        inames1_tps = ','.join(['char *' + s for s in inames1])
        cadd('static void f2py_setup_%s(%s) {' % (name, inames1_tps))
        cadd('\tint i_f2py=0;')
        for n in inames1:
            cadd(f'\tf2py_{name}_def[i_f2py++].data = {n};')
        cadd('}')
        if '_' in lower_name:
            F_FUNC = 'F_FUNC_US'
        else:
            F_FUNC = 'F_FUNC'
        cadd('extern void %s(f2pyinit%s,F2PYINIT%s)(void(*)(%s));'
             % (F_FUNC, lower_name, name.upper(),
                ','.join(['char*'] * len(inames1))))
        cadd('static void f2py_init_%s(void) {' % name)
        cadd('\t%s(f2pyinit%s,F2PYINIT%s)(f2py_setup_%s);'
             % (F_FUNC, lower_name, name.upper(), name))
        cadd('}\n')
        iadd(f'\ttmp = PyFortranObject_New(f2py_{name}_def,f2py_init_{name});')
        iadd('\tif (tmp == NULL) return NULL;')
        iadd(f'\tif (F2PyDict_SetItemString(d, "{name}", tmp) == -1) return NULL;')
        iadd('\tPy_DECREF(tmp);')
        tname = name.replace('_', '\\_')
        dadd('\\subsection{Common block \\texttt{%s}}\n' % (tname))
        dadd('\\begin{description}')
        for n in inames:
            dadd('\\item[]{{}\\verb@%s@{}}' %
                 (capi_maps.getarrdocsign(n, vars[n])))
            if hasnote(vars[n]):
                note = vars[n]['note']
                if isinstance(note, list):
                    note = '\n'.join(note)
                dadd(f'--- {note}')
        dadd('\\end{description}')
        ret['docs'].append(
            f"\"\t/{name}/ {','.join(map(lambda v, d: v + d, inames, idims))}\\n\"")
    ret['commonhooks'] = chooks
    ret['initcommonhooks'] = ihooks
    ret['latexdoc'] = doc[0]
    if len(ret['docs']) <= 1:
        ret['docs'] = ''
    return ret, fwrap[0]

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\output\plain_text.py ===
from __future__ import annotations

from typing import TextIO

from prompt_toolkit.cursor_shapes import CursorShape
from prompt_toolkit.data_structures import Size
from prompt_toolkit.styles import Attrs

from .base import Output
from .color_depth import ColorDepth
from .flush_stdout import flush_stdout

__all__ = ["PlainTextOutput"]


class PlainTextOutput(Output):
    """
    Output that won't include any ANSI escape sequences.

    Useful when stdout is not a terminal. Maybe stdout is redirected to a file.
    In this case, if `print_formatted_text` is used, for instance, we don't
    want to include formatting.

    (The code is mostly identical to `Vt100_Output`, but without the
    formatting.)
    """

    def __init__(self, stdout: TextIO) -> None:
        assert all(hasattr(stdout, a) for a in ("write", "flush"))

        self.stdout: TextIO = stdout
        self._buffer: list[str] = []

    def fileno(self) -> int:
        "There is no sensible default for fileno()."
        return self.stdout.fileno()

    def encoding(self) -> str:
        return "utf-8"

    def write(self, data: str) -> None:
        self._buffer.append(data)

    def write_raw(self, data: str) -> None:
        self._buffer.append(data)

    def set_title(self, title: str) -> None:
        pass

    def clear_title(self) -> None:
        pass

    def flush(self) -> None:
        if not self._buffer:
            return

        data = "".join(self._buffer)
        self._buffer = []
        flush_stdout(self.stdout, data)

    def erase_screen(self) -> None:
        pass

    def enter_alternate_screen(self) -> None:
        pass

    def quit_alternate_screen(self) -> None:
        pass

    def enable_mouse_support(self) -> None:
        pass

    def disable_mouse_support(self) -> None:
        pass

    def erase_end_of_line(self) -> None:
        pass

    def erase_down(self) -> None:
        pass

    def reset_attributes(self) -> None:
        pass

    def set_attributes(self, attrs: Attrs, color_depth: ColorDepth) -> None:
        pass

    def disable_autowrap(self) -> None:
        pass

    def enable_autowrap(self) -> None:
        pass

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        pass

    def cursor_up(self, amount: int) -> None:
        pass

    def cursor_down(self, amount: int) -> None:
        self._buffer.append("\n")

    def cursor_forward(self, amount: int) -> None:
        self._buffer.append(" " * amount)

    def cursor_backward(self, amount: int) -> None:
        pass

    def hide_cursor(self) -> None:
        pass

    def show_cursor(self) -> None:
        pass

    def set_cursor_shape(self, cursor_shape: CursorShape) -> None:
        pass

    def reset_cursor_shape(self) -> None:
        pass

    def ask_for_cpr(self) -> None:
        pass

    def bell(self) -> None:
        pass

    def enable_bracketed_paste(self) -> None:
        pass

    def disable_bracketed_paste(self) -> None:
        pass

    def scroll_buffer_to_prompt(self) -> None:
        pass

    def get_size(self) -> Size:
        return Size(rows=40, columns=80)

    def get_rows_below_cursor_position(self) -> int:
        return 8

    def get_default_color_depth(self) -> ColorDepth:
        return ColorDepth.DEPTH_1_BIT

# === NexusCore/openenv\Lib\site-packages\proto\marshal\rules\struct.py ===
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections.abc

from google.protobuf import struct_pb2

from proto.marshal.collections import maps
from proto.marshal.collections import repeated


class ValueRule:
    """A rule to marshal between google.protobuf.Value and Python values."""

    def __init__(self, *, marshal):
        self._marshal = marshal

    def to_python(self, value, *, absent: bool = None):
        """Coerce the given value to the appropriate Python type.

        Note that both NullValue and absent fields return None.
        In order to disambiguate between these two options,
        use containment check,
        E.g.
        "value" in foo
        which is True for NullValue and False for an absent value.
        """
        kind = value.WhichOneof("kind")
        if kind == "null_value" or absent:
            return None
        if kind == "bool_value":
            return bool(value.bool_value)
        if kind == "number_value":
            return float(value.number_value)
        if kind == "string_value":
            return str(value.string_value)
        if kind == "struct_value":
            return self._marshal.to_python(
                struct_pb2.Struct,
                value.struct_value,
                absent=False,
            )
        if kind == "list_value":
            return self._marshal.to_python(
                struct_pb2.ListValue,
                value.list_value,
                absent=False,
            )
        # If more variants are ever added, we want to fail loudly
        # instead of tacitly returning None.
        raise ValueError("Unexpected kind: %s" % kind)  # pragma: NO COVER

    def to_proto(self, value) -> struct_pb2.Value:
        """Return a protobuf Value object representing this value."""
        if isinstance(value, struct_pb2.Value):
            return value
        if value is None:
            return struct_pb2.Value(null_value=0)
        if isinstance(value, bool):
            return struct_pb2.Value(bool_value=value)
        if isinstance(value, (int, float)):
            return struct_pb2.Value(number_value=float(value))
        if isinstance(value, str):
            return struct_pb2.Value(string_value=value)
        if isinstance(value, collections.abc.Sequence):
            return struct_pb2.Value(
                list_value=self._marshal.to_proto(struct_pb2.ListValue, value),
            )
        if isinstance(value, collections.abc.Mapping):
            return struct_pb2.Value(
                struct_value=self._marshal.to_proto(struct_pb2.Struct, value),
            )
        raise ValueError("Unable to coerce value: %r" % value)


class ListValueRule:
    """A rule translating google.protobuf.ListValue and list-like objects."""

    def __init__(self, *, marshal):
        self._marshal = marshal

    def to_python(self, value, *, absent: bool = None):
        """Coerce the given value to a Python sequence."""
        return (
            None
            if absent
            else repeated.RepeatedComposite(value.values, marshal=self._marshal)
        )

    def to_proto(self, value) -> struct_pb2.ListValue:
        # We got a proto, or else something we sent originally.
        # Preserve the instance we have.
        if isinstance(value, struct_pb2.ListValue):
            return value
        if isinstance(value, repeated.RepeatedComposite):
            return struct_pb2.ListValue(values=[v for v in value.pb])

        # We got a list (or something list-like); convert it.
        return struct_pb2.ListValue(
            values=[self._marshal.to_proto(struct_pb2.Value, v) for v in value]
        )


class StructRule:
    """A rule translating google.protobuf.Struct and dict-like objects."""

    def __init__(self, *, marshal):
        self._marshal = marshal

    def to_python(self, value, *, absent: bool = None):
        """Coerce the given value to a Python mapping."""
        return (
            None if absent else maps.MapComposite(value.fields, marshal=self._marshal)
        )

    def to_proto(self, value) -> struct_pb2.Struct:
        # We got a proto, or else something we sent originally.
        # Preserve the instance we have.
        if isinstance(value, struct_pb2.Struct):
            return value
        if isinstance(value, maps.MapComposite):
            return struct_pb2.Struct(
                fields={k: v for k, v in value.pb.items()},
            )

        # We got a dict (or something dict-like); convert it.
        answer = struct_pb2.Struct(
            fields={
                k: self._marshal.to_proto(struct_pb2.Value, v) for k, v in value.items()
            }
        )
        return answer

# === NexusCore/openenv\Lib\site-packages\pygments\styles\tango.py ===
"""
    pygments.styles.tango
    ~~~~~~~~~~~~~~~~~~~~~

    The Crunchy default Style inspired from the color palette from
    the Tango Icon Theme Guidelines.

    http://tango.freedesktop.org/Tango_Icon_Theme_Guidelines

    Butter:     #fce94f     #edd400     #c4a000
    Orange:     #fcaf3e     #f57900     #ce5c00
    Chocolate:  #e9b96e     #c17d11     #8f5902
    Chameleon:  #8ae234     #73d216     #4e9a06
    Sky Blue:   #729fcf     #3465a4     #204a87
    Plum:       #ad7fa8     #75507b     #5c35cc
    Scarlet Red:#ef2929     #cc0000     #a40000
    Aluminium:  #eeeeec     #d3d7cf     #babdb6
                #888a85     #555753     #2e3436

    Not all of the above colors are used; other colors added:
        very light grey: #f8f8f8  (for background)

    This style can be used as a template as it includes all the known
    Token types, unlike most (if not all) of the styles included in the
    Pygments distribution.

    However, since Crunchy is intended to be used by beginners, we have strived
    to create a style that gloss over subtle distinctions between different
    categories.

    Taking Python for example, comments (Comment.*) and docstrings (String.Doc)
    have been chosen to have the same style.  Similarly, keywords (Keyword.*),
    and Operator.Word (and, or, in) have been assigned the same style.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


__all__ = ['TangoStyle']


class TangoStyle(Style):
    """
    The Crunchy default Style inspired from the color palette from
    the Tango Icon Theme Guidelines.
    """

    name = 'tango'
    
    background_color = "#f8f8f8"

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "#f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Multiline:         "italic #8f5902", # class: 'cm'
        Comment.Preproc:           "italic #8f5902", # class: 'cp'
        Comment.Single:            "italic #8f5902", # class: 'c1'
        Comment.Special:           "italic #8f5902", # class: 'cs'

        Keyword:                   "bold #204a87",   # class: 'k'
        Keyword.Constant:          "bold #204a87",   # class: 'kc'
        Keyword.Declaration:       "bold #204a87",   # class: 'kd'
        Keyword.Namespace:         "bold #204a87",   # class: 'kn'
        Keyword.Pseudo:            "bold #204a87",   # class: 'kp'
        Keyword.Reserved:          "bold #204a87",   # class: 'kr'
        Keyword.Type:              "bold #204a87",   # class: 'kt'

        Operator:                  "bold #ce5c00",   # class: 'o'
        Operator.Word:             "bold #204a87",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#204a87",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "bold #5c35cc",   # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #204a87",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        # since the tango light blue does not show up well in text, we choose
        # a pure blue instead.
        Number:                    "bold #0000cf",   # class: 'm'
        Number.Float:              "bold #0000cf",   # class: 'mf'
        Number.Hex:                "bold #0000cf",   # class: 'mh'
        Number.Integer:            "bold #0000cf",   # class: 'mi'
        Number.Integer.Long:       "bold #0000cf",   # class: 'il'
        Number.Oct:                "bold #0000cf",   # class: 'mo'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "italic #000000", # class: 'go'
        Generic.Prompt:            "#8f5902",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.EmphStrong:        "bold italic #000000",  # class: 'ges'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }