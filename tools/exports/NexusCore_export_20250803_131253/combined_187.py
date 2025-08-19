
# === NexusCore/tools\exports\export_20250803_114325\combined_205.py ===

# === NexusCore/openenv\Lib\site-packages\jedi\inference\compiled\mixed.py ===
"""
Used only for REPL Completion.
"""

import inspect
from pathlib import Path

from jedi.parser_utils import get_cached_code_lines

from jedi import settings
from jedi.cache import memoize_method
from jedi.inference import compiled
from jedi.file_io import FileIO
from jedi.inference.names import NameWrapper
from jedi.inference.base_value import ValueSet, ValueWrapper, NO_VALUES
from jedi.inference.value import ModuleValue
from jedi.inference.cache import inference_state_function_cache, \
    inference_state_method_cache
from jedi.inference.compiled.access import ALLOWED_GETITEM_TYPES, get_api_type
from jedi.inference.gradual.conversion import to_stub
from jedi.inference.context import CompiledContext, CompiledModuleContext, \
    TreeContextMixin

_sentinel = object()


class MixedObject(ValueWrapper):
    """
    A ``MixedObject`` is used in two ways:

    1. It uses the default logic of ``parser.python.tree`` objects,
    2. except for getattr calls and signatures. The names dicts are generated
       in a fashion like ``CompiledValue``.

    This combined logic makes it possible to provide more powerful REPL
    completion. It allows side effects that are not noticable with the default
    parser structure to still be completable.

    The biggest difference from CompiledValue to MixedObject is that we are
    generally dealing with Python code and not with C code. This will generate
    fewer special cases, because we in Python you don't have the same freedoms
    to modify the runtime.
    """
    def __init__(self, compiled_value, tree_value):
        super().__init__(tree_value)
        self.compiled_value = compiled_value
        self.access_handle = compiled_value.access_handle

    def get_filters(self, *args, **kwargs):
        yield MixedObjectFilter(
            self.inference_state, self.compiled_value, self._wrapped_value)

    def get_signatures(self):
        # Prefer `inspect.signature` over somehow analyzing Python code. It
        # should be very precise, especially for stuff like `partial`.
        return self.compiled_value.get_signatures()

    @inference_state_method_cache(default=NO_VALUES)
    def py__call__(self, arguments):
        # Fallback to the wrapped value if to stub returns no values.
        values = to_stub(self._wrapped_value)
        if not values:
            values = self._wrapped_value
        return values.py__call__(arguments)

    def get_safe_value(self, default=_sentinel):
        if default is _sentinel:
            return self.compiled_value.get_safe_value()
        else:
            return self.compiled_value.get_safe_value(default)

    @property
    def array_type(self):
        return self.compiled_value.array_type

    def get_key_values(self):
        return self.compiled_value.get_key_values()

    def py__simple_getitem__(self, index):
        python_object = self.compiled_value.access_handle.access._obj
        if type(python_object) in ALLOWED_GETITEM_TYPES:
            return self.compiled_value.py__simple_getitem__(index)
        return self._wrapped_value.py__simple_getitem__(index)

    def negate(self):
        return self.compiled_value.negate()

    def _as_context(self):
        if self.parent_context is None:
            return MixedModuleContext(self)
        return MixedContext(self)

    def __repr__(self):
        return '<%s: %s; %s>' % (
            type(self).__name__,
            self.access_handle.get_repr(),
            self._wrapped_value,
        )


class MixedContext(CompiledContext, TreeContextMixin):
    @property
    def compiled_value(self):
        return self._value.compiled_value


class MixedModuleContext(CompiledModuleContext, MixedContext):
    pass


class MixedName(NameWrapper):
    """
    The ``CompiledName._compiled_value`` is our MixedObject.
    """
    def __init__(self, wrapped_name, parent_tree_value):
        super().__init__(wrapped_name)
        self._parent_tree_value = parent_tree_value

    @property
    def start_pos(self):
        values = list(self.infer())
        if not values:
            # This means a start_pos that doesn't exist (compiled objects).
            return 0, 0
        return values[0].name.start_pos

    @memoize_method
    def infer(self):
        compiled_value = self._wrapped_name.infer_compiled_value()
        tree_value = self._parent_tree_value
        if tree_value.is_instance() or tree_value.is_class():
            tree_values = tree_value.py__getattribute__(self.string_name)
            if compiled_value.is_function():
                return ValueSet({MixedObject(compiled_value, v) for v in tree_values})

        module_context = tree_value.get_root_context()
        return _create(self._inference_state, compiled_value, module_context)


class MixedObjectFilter(compiled.CompiledValueFilter):
    def __init__(self, inference_state, compiled_value, tree_value):
        super().__init__(inference_state, compiled_value)
        self._tree_value = tree_value

    def _create_name(self, *args, **kwargs):
        return MixedName(
            super()._create_name(*args, **kwargs),
            self._tree_value,
        )


@inference_state_function_cache()
def _load_module(inference_state, path):
    return inference_state.parse(
        path=path,
        cache=True,
        diff_cache=settings.fast_parser,
        cache_path=settings.cache_directory
    ).get_root_node()


def _get_object_to_check(python_object):
    """Check if inspect.getfile has a chance to find the source."""
    try:
        python_object = inspect.unwrap(python_object)
    except ValueError:
        # Can return a ValueError when it wraps around
        pass

    if (inspect.ismodule(python_object)
            or inspect.isclass(python_object)
            or inspect.ismethod(python_object)
            or inspect.isfunction(python_object)
            or inspect.istraceback(python_object)
            or inspect.isframe(python_object)
            or inspect.iscode(python_object)):
        return python_object

    try:
        return python_object.__class__
    except AttributeError:
        raise TypeError  # Prevents computation of `repr` within inspect.


def _find_syntax_node_name(inference_state, python_object):
    original_object = python_object
    try:
        python_object = _get_object_to_check(python_object)
        path = inspect.getsourcefile(python_object)
    except (OSError, TypeError):
        # The type might not be known (e.g. class_with_dict.__weakref__)
        return None
    path = None if path is None else Path(path)
    try:
        if path is None or not path.exists():
            # The path might not exist or be e.g. <stdin>.
            return None
    except OSError:
        # Might raise an OSError on Windows:
        #
        #     [WinError 123] The filename, directory name, or volume label
        #     syntax is incorrect: '<string>'
        return None

    file_io = FileIO(path)
    module_node = _load_module(inference_state, path)

    if inspect.ismodule(python_object):
        # We don't need to check names for modules, because there's not really
        # a way to write a module in a module in Python (and also __name__ can
        # be something like ``email.utils``).
        code_lines = get_cached_code_lines(inference_state.grammar, path)
        return module_node, module_node, file_io, code_lines

    try:
        name_str = python_object.__name__
    except AttributeError:
        # Stuff like python_function.__code__.
        return None

    if name_str == '<lambda>':
        return None  # It's too hard to find lambdas.

    # Doesn't always work (e.g. os.stat_result)
    names = module_node.get_used_names().get(name_str, [])
    # Only functions and classes are relevant. If a name e.g. points to an
    # import, it's probably a builtin (like collections.deque) and needs to be
    # ignored.
    names = [
        n for n in names
        if n.parent.type in ('funcdef', 'classdef') and n.parent.name == n
    ]
    if not names:
        return None

    try:
        code = python_object.__code__
        # By using the line number of a code object we make the lookup in a
        # file pretty easy. There's still a possibility of people defining
        # stuff like ``a = 3; foo(a); a = 4`` on the same line, but if people
        # do so we just don't care.
        line_nr = code.co_firstlineno
    except AttributeError:
        pass
    else:
        line_names = [name for name in names if name.start_pos[0] == line_nr]
        # There's a chance that the object is not available anymore, because
        # the code has changed in the background.
        if line_names:
            names = line_names

    code_lines = get_cached_code_lines(inference_state.grammar, path)
    # It's really hard to actually get the right definition, here as a last
    # resort we just return the last one. This chance might lead to odd
    # completions at some points but will lead to mostly correct type
    # inference, because people tend to define a public name in a module only
    # once.
    tree_node = names[-1].parent
    if tree_node.type == 'funcdef' and get_api_type(original_object) == 'instance':
        # If an instance is given and we're landing on a function (e.g.
        # partial in 3.5), something is completely wrong and we should not
        # return that.
        return None
    return module_node, tree_node, file_io, code_lines


@inference_state_function_cache()
def _create(inference_state, compiled_value, module_context):
    # TODO accessing this is bad, but it probably doesn't matter that much,
    # because we're working with interpreters only here.
    python_object = compiled_value.access_handle.access._obj
    result = _find_syntax_node_name(inference_state, python_object)
    if result is None:
        # TODO Care about generics from stuff like `[1]` and don't return like this.
        if type(python_object) in (dict, list, tuple):
            return ValueSet({compiled_value})

        tree_values = to_stub(compiled_value)
        if not tree_values:
            return ValueSet({compiled_value})
    else:
        module_node, tree_node, file_io, code_lines = result

        if module_context is None or module_context.tree_node != module_node:
            root_compiled_value = compiled_value.get_root_context().get_value()
            # TODO this __name__ might be wrong.
            name = root_compiled_value.py__name__()
            string_names = tuple(name.split('.'))
            module_value = ModuleValue(
                inference_state, module_node,
                file_io=file_io,
                string_names=string_names,
                code_lines=code_lines,
                is_package=root_compiled_value.is_package(),
            )
            if name is not None:
                inference_state.module_cache.add(string_names, ValueSet([module_value]))
            module_context = module_value.as_context()

        tree_values = ValueSet({module_context.create_value(tree_node)})
        if tree_node.type == 'classdef':
            if not compiled_value.is_class():
                # Is an instance, not a class.
                tree_values = tree_values.execute_with_values()

    return ValueSet(
        MixedObject(compiled_value, tree_value=tree_value)
        for tree_value in tree_values
    )

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\comparative_sents.py ===
# Natural Language Toolkit: Comparative Sentence Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Pierpaolo Pantone <24alsecondo@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
CorpusReader for the Comparative Sentence Dataset.

- Comparative Sentence Dataset information -

Annotated by: Nitin Jindal and Bing Liu, 2006.
              Department of Computer Sicence
              University of Illinois at Chicago

Contact: Nitin Jindal, njindal@cs.uic.edu
         Bing Liu, liub@cs.uic.edu (https://www.cs.uic.edu/~liub)

Distributed with permission.

Related papers:

- Nitin Jindal and Bing Liu. "Identifying Comparative Sentences in Text Documents".
   Proceedings of the ACM SIGIR International Conference on Information Retrieval
   (SIGIR-06), 2006.

- Nitin Jindal and Bing Liu. "Mining Comprative Sentences and Relations".
   Proceedings of Twenty First National Conference on Artificial Intelligence
   (AAAI-2006), 2006.

- Murthy Ganapathibhotla and Bing Liu. "Mining Opinions in Comparative Sentences".
    Proceedings of the 22nd International Conference on Computational Linguistics
    (Coling-2008), Manchester, 18-22 August, 2008.
"""
import re

from nltk.corpus.reader.api import *
from nltk.tokenize import *

# Regular expressions for dataset components
STARS = re.compile(r"^\*+$")
COMPARISON = re.compile(r"<cs-[1234]>")
CLOSE_COMPARISON = re.compile(r"</cs-[1234]>")
GRAD_COMPARISON = re.compile(r"<cs-[123]>")
NON_GRAD_COMPARISON = re.compile(r"<cs-4>")
ENTITIES_FEATS = re.compile(r"(\d)_((?:[\.\w\s/-](?!\d_))+)")
KEYWORD = re.compile(r"\(([^\(]*)\)$")


class Comparison:
    """
    A Comparison represents a comparative sentence and its constituents.
    """

    def __init__(
        self,
        text=None,
        comp_type=None,
        entity_1=None,
        entity_2=None,
        feature=None,
        keyword=None,
    ):
        """
        :param text: a string (optionally tokenized) containing a comparison.
        :param comp_type: an integer defining the type of comparison expressed.
            Values can be: 1 (Non-equal gradable), 2 (Equative), 3 (Superlative),
            4 (Non-gradable).
        :param entity_1: the first entity considered in the comparison relation.
        :param entity_2: the second entity considered in the comparison relation.
        :param feature: the feature considered in the comparison relation.
        :param keyword: the word or phrase which is used for that comparative relation.
        """
        self.text = text
        self.comp_type = comp_type
        self.entity_1 = entity_1
        self.entity_2 = entity_2
        self.feature = feature
        self.keyword = keyword

    def __repr__(self):
        return (
            'Comparison(text="{}", comp_type={}, entity_1="{}", entity_2="{}", '
            'feature="{}", keyword="{}")'
        ).format(
            self.text,
            self.comp_type,
            self.entity_1,
            self.entity_2,
            self.feature,
            self.keyword,
        )


class ComparativeSentencesCorpusReader(CorpusReader):
    """
    Reader for the Comparative Sentence Dataset by Jindal and Liu (2006).

        >>> from nltk.corpus import comparative_sentences
        >>> comparison = comparative_sentences.comparisons()[0]
        >>> comparison.text # doctest: +NORMALIZE_WHITESPACE
        ['its', 'fast-forward', 'and', 'rewind', 'work', 'much', 'more', 'smoothly',
        'and', 'consistently', 'than', 'those', 'of', 'other', 'models', 'i', "'ve",
        'had', '.']
        >>> comparison.entity_2
        'models'
        >>> (comparison.feature, comparison.keyword)
        ('rewind', 'more')
        >>> len(comparative_sentences.comparisons())
        853
    """

    CorpusView = StreamBackedCorpusView

    def __init__(
        self,
        root,
        fileids,
        word_tokenizer=WhitespaceTokenizer(),
        sent_tokenizer=None,
        encoding="utf8",
    ):
        """
        :param root: The root directory for this corpus.
        :param fileids: a list or regexp specifying the fileids in this corpus.
        :param word_tokenizer: tokenizer for breaking sentences or paragraphs
            into words. Default: `WhitespaceTokenizer`
        :param sent_tokenizer: tokenizer for breaking paragraphs into sentences.
        :param encoding: the encoding that should be used to read the corpus.
        """

        CorpusReader.__init__(self, root, fileids, encoding)
        self._word_tokenizer = word_tokenizer
        self._sent_tokenizer = sent_tokenizer
        self._readme = "README.txt"

    def comparisons(self, fileids=None):
        """
        Return all comparisons in the corpus.

        :param fileids: a list or regexp specifying the ids of the files whose
            comparisons have to be returned.
        :return: the given file(s) as a list of Comparison objects.
        :rtype: list(Comparison)
        """
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]
        return concat(
            [
                self.CorpusView(path, self._read_comparison_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def keywords(self, fileids=None):
        """
        Return a set of all keywords used in the corpus.

        :param fileids: a list or regexp specifying the ids of the files whose
            keywords have to be returned.
        :return: the set of keywords and comparative phrases used in the corpus.
        :rtype: set(str)
        """
        all_keywords = concat(
            [
                self.CorpusView(path, self._read_keyword_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

        keywords_set = {keyword.lower() for keyword in all_keywords if keyword}
        return keywords_set

    def keywords_readme(self):
        """
        Return the list of words and constituents considered as clues of a
        comparison (from listOfkeywords.txt).
        """
        keywords = []
        with self.open("listOfkeywords.txt") as fp:
            raw_text = fp.read()
        for line in raw_text.split("\n"):
            if not line or line.startswith("//"):
                continue
            keywords.append(line.strip())
        return keywords

    def sents(self, fileids=None):
        """
        Return all sentences in the corpus.

        :param fileids: a list or regexp specifying the ids of the files whose
            sentences have to be returned.
        :return: all sentences of the corpus as lists of tokens (or as plain
            strings, if no word tokenizer is specified).
        :rtype: list(list(str)) or list(str)
        """
        return concat(
            [
                self.CorpusView(path, self._read_sent_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def words(self, fileids=None):
        """
        Return all words and punctuation symbols in the corpus.

        :param fileids: a list or regexp specifying the ids of the files whose
            words have to be returned.
        :return: the given file(s) as a list of words and punctuation symbols.
        :rtype: list(str)
        """
        return concat(
            [
                self.CorpusView(path, self._read_word_block, encoding=enc)
                for (path, enc, fileid) in self.abspaths(fileids, True, True)
            ]
        )

    def _read_comparison_block(self, stream):
        while True:
            line = stream.readline()
            if not line:
                return []  # end of file.
            comparison_tags = re.findall(COMPARISON, line)
            if comparison_tags:
                grad_comparisons = re.findall(GRAD_COMPARISON, line)
                non_grad_comparisons = re.findall(NON_GRAD_COMPARISON, line)
                # Advance to the next line (it contains the comparative sentence)
                comparison_text = stream.readline().strip()
                if self._word_tokenizer:
                    comparison_text = self._word_tokenizer.tokenize(comparison_text)
                # Skip the next line (it contains closing comparison tags)
                stream.readline()
                # If gradable comparisons are found, create Comparison instances
                # and populate their fields
                comparison_bundle = []
                if grad_comparisons:
                    # Each comparison tag has its own relations on a separate line
                    for comp in grad_comparisons:
                        comp_type = int(re.match(r"<cs-(\d)>", comp).group(1))
                        comparison = Comparison(
                            text=comparison_text, comp_type=comp_type
                        )
                        line = stream.readline()
                        entities_feats = ENTITIES_FEATS.findall(line)
                        if entities_feats:
                            for code, entity_feat in entities_feats:
                                if code == "1":
                                    comparison.entity_1 = entity_feat.strip()
                                elif code == "2":
                                    comparison.entity_2 = entity_feat.strip()
                                elif code == "3":
                                    comparison.feature = entity_feat.strip()
                        keyword = KEYWORD.findall(line)
                        if keyword:
                            comparison.keyword = keyword[0]
                        comparison_bundle.append(comparison)
                # If non-gradable comparisons are found, create a simple Comparison
                # instance for each one
                if non_grad_comparisons:
                    for comp in non_grad_comparisons:
                        # comp_type in this case should always be 4.
                        comp_type = int(re.match(r"<cs-(\d)>", comp).group(1))
                        comparison = Comparison(
                            text=comparison_text, comp_type=comp_type
                        )
                        comparison_bundle.append(comparison)
                # Flatten the list of comparisons before returning them
                # return concat([comparison_bundle])
                return comparison_bundle

    def _read_keyword_block(self, stream):
        keywords = []
        for comparison in self._read_comparison_block(stream):
            keywords.append(comparison.keyword)
        return keywords

    def _read_sent_block(self, stream):
        while True:
            line = stream.readline()
            if re.match(STARS, line):
                while True:
                    line = stream.readline()
                    if re.match(STARS, line):
                        break
                continue
            if (
                not re.findall(COMPARISON, line)
                and not ENTITIES_FEATS.findall(line)
                and not re.findall(CLOSE_COMPARISON, line)
            ):
                if self._sent_tokenizer:
                    return [
                        self._word_tokenizer.tokenize(sent)
                        for sent in self._sent_tokenizer.tokenize(line)
                    ]
                else:
                    return [self._word_tokenizer.tokenize(line)]

    def _read_word_block(self, stream):
        words = []
        for sent in self._read_sent_block(stream):
            words.extend(sent)
        return words

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\_palettes.py ===
from .palette import Palette


# Taken from https://en.wikipedia.org/wiki/ANSI_escape_code (Windows 10 column)
WINDOWS_PALETTE = Palette(
    [
        (12, 12, 12),
        (197, 15, 31),
        (19, 161, 14),
        (193, 156, 0),
        (0, 55, 218),
        (136, 23, 152),
        (58, 150, 221),
        (204, 204, 204),
        (118, 118, 118),
        (231, 72, 86),
        (22, 198, 12),
        (249, 241, 165),
        (59, 120, 255),
        (180, 0, 158),
        (97, 214, 214),
        (242, 242, 242),
    ]
)

# # The standard ansi colors (including bright variants)
STANDARD_PALETTE = Palette(
    [
        (0, 0, 0),
        (170, 0, 0),
        (0, 170, 0),
        (170, 85, 0),
        (0, 0, 170),
        (170, 0, 170),
        (0, 170, 170),
        (170, 170, 170),
        (85, 85, 85),
        (255, 85, 85),
        (85, 255, 85),
        (255, 255, 85),
        (85, 85, 255),
        (255, 85, 255),
        (85, 255, 255),
        (255, 255, 255),
    ]
)


# The 256 color palette
EIGHT_BIT_PALETTE = Palette(
    [
        (0, 0, 0),
        (128, 0, 0),
        (0, 128, 0),
        (128, 128, 0),
        (0, 0, 128),
        (128, 0, 128),
        (0, 128, 128),
        (192, 192, 192),
        (128, 128, 128),
        (255, 0, 0),
        (0, 255, 0),
        (255, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (0, 255, 255),
        (255, 255, 255),
        (0, 0, 0),
        (0, 0, 95),
        (0, 0, 135),
        (0, 0, 175),
        (0, 0, 215),
        (0, 0, 255),
        (0, 95, 0),
        (0, 95, 95),
        (0, 95, 135),
        (0, 95, 175),
        (0, 95, 215),
        (0, 95, 255),
        (0, 135, 0),
        (0, 135, 95),
        (0, 135, 135),
        (0, 135, 175),
        (0, 135, 215),
        (0, 135, 255),
        (0, 175, 0),
        (0, 175, 95),
        (0, 175, 135),
        (0, 175, 175),
        (0, 175, 215),
        (0, 175, 255),
        (0, 215, 0),
        (0, 215, 95),
        (0, 215, 135),
        (0, 215, 175),
        (0, 215, 215),
        (0, 215, 255),
        (0, 255, 0),
        (0, 255, 95),
        (0, 255, 135),
        (0, 255, 175),
        (0, 255, 215),
        (0, 255, 255),
        (95, 0, 0),
        (95, 0, 95),
        (95, 0, 135),
        (95, 0, 175),
        (95, 0, 215),
        (95, 0, 255),
        (95, 95, 0),
        (95, 95, 95),
        (95, 95, 135),
        (95, 95, 175),
        (95, 95, 215),
        (95, 95, 255),
        (95, 135, 0),
        (95, 135, 95),
        (95, 135, 135),
        (95, 135, 175),
        (95, 135, 215),
        (95, 135, 255),
        (95, 175, 0),
        (95, 175, 95),
        (95, 175, 135),
        (95, 175, 175),
        (95, 175, 215),
        (95, 175, 255),
        (95, 215, 0),
        (95, 215, 95),
        (95, 215, 135),
        (95, 215, 175),
        (95, 215, 215),
        (95, 215, 255),
        (95, 255, 0),
        (95, 255, 95),
        (95, 255, 135),
        (95, 255, 175),
        (95, 255, 215),
        (95, 255, 255),
        (135, 0, 0),
        (135, 0, 95),
        (135, 0, 135),
        (135, 0, 175),
        (135, 0, 215),
        (135, 0, 255),
        (135, 95, 0),
        (135, 95, 95),
        (135, 95, 135),
        (135, 95, 175),
        (135, 95, 215),
        (135, 95, 255),
        (135, 135, 0),
        (135, 135, 95),
        (135, 135, 135),
        (135, 135, 175),
        (135, 135, 215),
        (135, 135, 255),
        (135, 175, 0),
        (135, 175, 95),
        (135, 175, 135),
        (135, 175, 175),
        (135, 175, 215),
        (135, 175, 255),
        (135, 215, 0),
        (135, 215, 95),
        (135, 215, 135),
        (135, 215, 175),
        (135, 215, 215),
        (135, 215, 255),
        (135, 255, 0),
        (135, 255, 95),
        (135, 255, 135),
        (135, 255, 175),
        (135, 255, 215),
        (135, 255, 255),
        (175, 0, 0),
        (175, 0, 95),
        (175, 0, 135),
        (175, 0, 175),
        (175, 0, 215),
        (175, 0, 255),
        (175, 95, 0),
        (175, 95, 95),
        (175, 95, 135),
        (175, 95, 175),
        (175, 95, 215),
        (175, 95, 255),
        (175, 135, 0),
        (175, 135, 95),
        (175, 135, 135),
        (175, 135, 175),
        (175, 135, 215),
        (175, 135, 255),
        (175, 175, 0),
        (175, 175, 95),
        (175, 175, 135),
        (175, 175, 175),
        (175, 175, 215),
        (175, 175, 255),
        (175, 215, 0),
        (175, 215, 95),
        (175, 215, 135),
        (175, 215, 175),
        (175, 215, 215),
        (175, 215, 255),
        (175, 255, 0),
        (175, 255, 95),
        (175, 255, 135),
        (175, 255, 175),
        (175, 255, 215),
        (175, 255, 255),
        (215, 0, 0),
        (215, 0, 95),
        (215, 0, 135),
        (215, 0, 175),
        (215, 0, 215),
        (215, 0, 255),
        (215, 95, 0),
        (215, 95, 95),
        (215, 95, 135),
        (215, 95, 175),
        (215, 95, 215),
        (215, 95, 255),
        (215, 135, 0),
        (215, 135, 95),
        (215, 135, 135),
        (215, 135, 175),
        (215, 135, 215),
        (215, 135, 255),
        (215, 175, 0),
        (215, 175, 95),
        (215, 175, 135),
        (215, 175, 175),
        (215, 175, 215),
        (215, 175, 255),
        (215, 215, 0),
        (215, 215, 95),
        (215, 215, 135),
        (215, 215, 175),
        (215, 215, 215),
        (215, 215, 255),
        (215, 255, 0),
        (215, 255, 95),
        (215, 255, 135),
        (215, 255, 175),
        (215, 255, 215),
        (215, 255, 255),
        (255, 0, 0),
        (255, 0, 95),
        (255, 0, 135),
        (255, 0, 175),
        (255, 0, 215),
        (255, 0, 255),
        (255, 95, 0),
        (255, 95, 95),
        (255, 95, 135),
        (255, 95, 175),
        (255, 95, 215),
        (255, 95, 255),
        (255, 135, 0),
        (255, 135, 95),
        (255, 135, 135),
        (255, 135, 175),
        (255, 135, 215),
        (255, 135, 255),
        (255, 175, 0),
        (255, 175, 95),
        (255, 175, 135),
        (255, 175, 175),
        (255, 175, 215),
        (255, 175, 255),
        (255, 215, 0),
        (255, 215, 95),
        (255, 215, 135),
        (255, 215, 175),
        (255, 215, 215),
        (255, 215, 255),
        (255, 255, 0),
        (255, 255, 95),
        (255, 255, 135),
        (255, 255, 175),
        (255, 255, 215),
        (255, 255, 255),
        (8, 8, 8),
        (18, 18, 18),
        (28, 28, 28),
        (38, 38, 38),
        (48, 48, 48),
        (58, 58, 58),
        (68, 68, 68),
        (78, 78, 78),
        (88, 88, 88),
        (98, 98, 98),
        (108, 108, 108),
        (118, 118, 118),
        (128, 128, 128),
        (138, 138, 138),
        (148, 148, 148),
        (158, 158, 158),
        (168, 168, 168),
        (178, 178, 178),
        (188, 188, 188),
        (198, 198, 198),
        (208, 208, 208),
        (218, 218, 218),
        (228, 228, 228),
        (238, 238, 238),
    ]
)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\input\vt100.py ===
from __future__ import annotations

import sys

assert sys.platform != "win32"

import contextlib
import io
import termios
import tty
from asyncio import AbstractEventLoop, get_running_loop
from typing import Callable, ContextManager, Generator, TextIO

from ..key_binding import KeyPress
from .base import Input
from .posix_utils import PosixStdinReader
from .vt100_parser import Vt100Parser

__all__ = [
    "Vt100Input",
    "raw_mode",
    "cooked_mode",
]


class Vt100Input(Input):
    """
    Vt100 input for Posix systems.
    (This uses a posix file descriptor that can be registered in the event loop.)
    """

    # For the error messages. Only display "Input is not a terminal" once per
    # file descriptor.
    _fds_not_a_terminal: set[int] = set()

    def __init__(self, stdin: TextIO) -> None:
        # Test whether the given input object has a file descriptor.
        # (Idle reports stdin to be a TTY, but fileno() is not implemented.)
        try:
            # This should not raise, but can return 0.
            stdin.fileno()
        except io.UnsupportedOperation as e:
            if "idlelib.run" in sys.modules:
                raise io.UnsupportedOperation(
                    "Stdin is not a terminal. Running from Idle is not supported."
                ) from e
            else:
                raise io.UnsupportedOperation("Stdin is not a terminal.") from e

        # Even when we have a file descriptor, it doesn't mean it's a TTY.
        # Normally, this requires a real TTY device, but people instantiate
        # this class often during unit tests as well. They use for instance
        # pexpect to pipe data into an application. For convenience, we print
        # an error message and go on.
        isatty = stdin.isatty()
        fd = stdin.fileno()

        if not isatty and fd not in Vt100Input._fds_not_a_terminal:
            msg = "Warning: Input is not a terminal (fd=%r).\n"
            sys.stderr.write(msg % fd)
            sys.stderr.flush()
            Vt100Input._fds_not_a_terminal.add(fd)

        #
        self.stdin = stdin

        # Create a backup of the fileno(). We want this to work even if the
        # underlying file is closed, so that `typeahead_hash()` keeps working.
        self._fileno = stdin.fileno()

        self._buffer: list[KeyPress] = []  # Buffer to collect the Key objects.
        self.stdin_reader = PosixStdinReader(self._fileno, encoding=stdin.encoding)
        self.vt100_parser = Vt100Parser(
            lambda key_press: self._buffer.append(key_press)
        )

    def attach(self, input_ready_callback: Callable[[], None]) -> ContextManager[None]:
        """
        Return a context manager that makes this input active in the current
        event loop.
        """
        return _attached_input(self, input_ready_callback)

    def detach(self) -> ContextManager[None]:
        """
        Return a context manager that makes sure that this input is not active
        in the current event loop.
        """
        return _detached_input(self)

    def read_keys(self) -> list[KeyPress]:
        "Read list of KeyPress."
        # Read text from stdin.
        data = self.stdin_reader.read()

        # Pass it through our vt100 parser.
        self.vt100_parser.feed(data)

        # Return result.
        result = self._buffer
        self._buffer = []
        return result

    def flush_keys(self) -> list[KeyPress]:
        """
        Flush pending keys and return them.
        (Used for flushing the 'escape' key.)
        """
        # Flush all pending keys. (This is most important to flush the vt100
        # 'Escape' key early when nothing else follows.)
        self.vt100_parser.flush()

        # Return result.
        result = self._buffer
        self._buffer = []
        return result

    @property
    def closed(self) -> bool:
        return self.stdin_reader.closed

    def raw_mode(self) -> ContextManager[None]:
        return raw_mode(self.stdin.fileno())

    def cooked_mode(self) -> ContextManager[None]:
        return cooked_mode(self.stdin.fileno())

    def fileno(self) -> int:
        return self.stdin.fileno()

    def typeahead_hash(self) -> str:
        return f"fd-{self._fileno}"


_current_callbacks: dict[
    tuple[AbstractEventLoop, int], Callable[[], None] | None
] = {}  # (loop, fd) -> current callback


@contextlib.contextmanager
def _attached_input(
    input: Vt100Input, callback: Callable[[], None]
) -> Generator[None, None, None]:
    """
    Context manager that makes this input active in the current event loop.

    :param input: :class:`~prompt_toolkit.input.Input` object.
    :param callback: Called when the input is ready to read.
    """
    loop = get_running_loop()
    fd = input.fileno()
    previous = _current_callbacks.get((loop, fd))

    def callback_wrapper() -> None:
        """Wrapper around the callback that already removes the reader when
        the input is closed. Otherwise, we keep continuously calling this
        callback, until we leave the context manager (which can happen a bit
        later). This fixes issues when piping /dev/null into a prompt_toolkit
        application."""
        if input.closed:
            loop.remove_reader(fd)
        callback()

    try:
        loop.add_reader(fd, callback_wrapper)
    except PermissionError:
        # For `EPollSelector`, adding /dev/null to the event loop will raise
        # `PermissionError` (that doesn't happen for `SelectSelector`
        # apparently). Whenever we get a `PermissionError`, we can raise
        # `EOFError`, because there's not more to be read anyway. `EOFError` is
        # an exception that people expect in
        # `prompt_toolkit.application.Application.run()`.
        # To reproduce, do: `ptpython 0< /dev/null 1< /dev/null`
        raise EOFError

    _current_callbacks[loop, fd] = callback

    try:
        yield
    finally:
        loop.remove_reader(fd)

        if previous:
            loop.add_reader(fd, previous)
            _current_callbacks[loop, fd] = previous
        else:
            del _current_callbacks[loop, fd]


@contextlib.contextmanager
def _detached_input(input: Vt100Input) -> Generator[None, None, None]:
    loop = get_running_loop()
    fd = input.fileno()
    previous = _current_callbacks.get((loop, fd))

    if previous:
        loop.remove_reader(fd)
        _current_callbacks[loop, fd] = None

    try:
        yield
    finally:
        if previous:
            loop.add_reader(fd, previous)
            _current_callbacks[loop, fd] = previous


class raw_mode:
    """
    ::

        with raw_mode(stdin):
            ''' the pseudo-terminal stdin is now used in raw mode '''

    We ignore errors when executing `tcgetattr` fails.
    """

    # There are several reasons for ignoring errors:
    # 1. To avoid the "Inappropriate ioctl for device" crash if somebody would
    #    execute this code (In a Python REPL, for instance):
    #
    #         import os; f = open(os.devnull); os.dup2(f.fileno(), 0)
    #
    #    The result is that the eventloop will stop correctly, because it has
    #    to logic to quit when stdin is closed. However, we should not fail at
    #    this point. See:
    #      https://github.com/jonathanslenders/python-prompt-toolkit/pull/393
    #      https://github.com/jonathanslenders/python-prompt-toolkit/issues/392

    # 2. Related, when stdin is an SSH pipe, and no full terminal was allocated.
    #    See: https://github.com/jonathanslenders/python-prompt-toolkit/pull/165
    def __init__(self, fileno: int) -> None:
        self.fileno = fileno
        self.attrs_before: list[int | list[bytes | int]] | None
        try:
            self.attrs_before = termios.tcgetattr(fileno)
        except termios.error:
            # Ignore attribute errors.
            self.attrs_before = None

    def __enter__(self) -> None:
        # NOTE: On os X systems, using pty.setraw() fails. Therefor we are using this:
        try:
            newattr = termios.tcgetattr(self.fileno)
        except termios.error:
            pass
        else:
            newattr[tty.LFLAG] = self._patch_lflag(newattr[tty.LFLAG])
            newattr[tty.IFLAG] = self._patch_iflag(newattr[tty.IFLAG])

            # VMIN defines the number of characters read at a time in
            # non-canonical mode. It seems to default to 1 on Linux, but on
            # Solaris and derived operating systems it defaults to 4. (This is
            # because the VMIN slot is the same as the VEOF slot, which
            # defaults to ASCII EOT = Ctrl-D = 4.)
            newattr[tty.CC][termios.VMIN] = 1

            termios.tcsetattr(self.fileno, termios.TCSANOW, newattr)

    @classmethod
    def _patch_lflag(cls, attrs: int) -> int:
        return attrs & ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)

    @classmethod
    def _patch_iflag(cls, attrs: int) -> int:
        return attrs & ~(
            # Disable XON/XOFF flow control on output and input.
            # (Don't capture Ctrl-S and Ctrl-Q.)
            # Like executing: "stty -ixon."
            termios.IXON
            | termios.IXOFF
            |
            # Don't translate carriage return into newline on input.
            termios.ICRNL
            | termios.INLCR
            | termios.IGNCR
        )

    def __exit__(self, *a: object) -> None:
        if self.attrs_before is not None:
            try:
                termios.tcsetattr(self.fileno, termios.TCSANOW, self.attrs_before)
            except termios.error:
                pass

            # # Put the terminal in application mode.
            # self._stdout.write('\x1b[?1h')


class cooked_mode(raw_mode):
    """
    The opposite of ``raw_mode``, used when we need cooked mode inside a
    `raw_mode` block.  Used in `Application.run_in_terminal`.::

        with cooked_mode(stdin):
            ''' the pseudo-terminal stdin is now used in cooked mode. '''
    """

    @classmethod
    def _patch_lflag(cls, attrs: int) -> int:
        return attrs | (termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)

    @classmethod
    def _patch_iflag(cls, attrs: int) -> int:
        # Turn the ICRNL flag back on. (Without this, calling `input()` in
        # run_in_terminal doesn't work and displays ^M instead. Ptpython
        # evaluates commands using `run_in_terminal`, so it's important that
        # they translate ^M back into ^J.)
        return attrs | termios.ICRNL

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ul4.py ===
"""
    pygments.lexers.ul4
    ~~~~~~~~~~~~~~~~~~~

    Lexer for the UL4 templating language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, DelegatingLexer, bygroups, words, include
from pygments.token import Comment, Text, Keyword, String, Number, Literal, \
    Name, Other, Operator
from pygments.lexers.web import HtmlLexer, XmlLexer, CssLexer, JavascriptLexer
from pygments.lexers.python import PythonLexer

__all__ = ['UL4Lexer', 'HTMLUL4Lexer', 'XMLUL4Lexer', 'CSSUL4Lexer',
           'JavascriptUL4Lexer', 'PythonUL4Lexer']


class UL4Lexer(RegexLexer):
    """
    Generic lexer for UL4.
    """

    flags = re.MULTILINE | re.DOTALL

    name = 'UL4'
    aliases = ['ul4']
    filenames = ['*.ul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = '2.12'

    tokens = {
        "root": [
            (
                # Template header without name:
                # ``<?ul4?>``
                r"(<\?)(\s*)(ul4)(\s*)(\?>)",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword,
                         Text.Whitespace, Comment.Preproc),
            ),
            (
                # Template header with name (potentially followed by the signature):
                # ``<?ul4 foo(bar=42)?>``
                r"(<\?)(\s*)(ul4)(\s*)([a-zA-Z_][a-zA-Z_0-9]*)?",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword,
                         Text.Whitespace, Name.Function),
                "ul4", # Switch to "expression" mode
            ),
            (
                # Comment:
                # ``<?note?>...<?end note?>``
                r"<\?\s*note\s*\?>",
                Comment,
                "note", # Switch to "note" mode
            ),
            (
                # Comment:
                # ``<?note foobar?>``
                r"<\?\s*note\s.*?\?>",
                Comment,
            ),
            (
                # Template documentation:
                # ``<?doc?>...<?end doc?>``
                r"<\?\s*doc\s*\?>",
                String.Doc,
                "doc",
            ),
            (
                # Template documentation:
                # ``<?doc foobar?>``
                r"<\?\s*doc\s.*?\?>",
                String.Doc,
            ),
            (
                # ``<?ignore?>`` tag for commenting out code:
                # ``<?ignore?>...<?end ignore?>``
                r"<\?\s*ignore\s*\?>",
                Comment,
                "ignore", # Switch to "ignore" mode
            ),
            (
                # ``<?def?>`` tag for defining local templates
                # ``<?def foo(bar=42)?>...<?end def?>``
                r"(<\?)(\s*)(def)(\s*)([a-zA-Z_][a-zA-Z_0-9]*)?",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword,
                         Text.Whitespace, Name.Function),
                "ul4", # Switch to "expression" mode
            ),
            (
                # The rest of the supported tags
                r"(<\?)(\s*)(printx|print|for|if|elif|else|while|code|renderblocks?|render)\b",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword),
                "ul4", # Switch to "expression" mode
            ),
            (
                # ``<?end?>`` tag for ending ``<?def?>``, ``<?for?>``,
                # ``<?if?>``, ``<?while?>``, ``<?renderblock?>`` and
                # ``<?renderblocks?>`` blocks.
                r"(<\?)(\s*)(end)\b",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword),
                "end", # Switch to "end tag" mode
            ),
            (
                # ``<?whitespace?>`` tag for configuring whitespace handlng
                r"(<\?)(\s*)(whitespace)\b",
                bygroups(Comment.Preproc, Text.Whitespace, Keyword),
                "whitespace", # Switch to "whitespace" mode
            ),
            # Plain text
            (r"[^<]+", Other),
            (r"<", Other),
        ],
        # Ignore mode ignores everything upto the matching ``<?end ignore?>`` tag
        "ignore": [
            # Nested ``<?ignore?>`` tag
            (r"<\?\s*ignore\s*\?>", Comment, "#push"),
            # ``<?end ignore?>`` tag
            (r"<\?\s*end\s+ignore\s*\?>", Comment, "#pop"),
            # Everything else
            (r"[^<]+", Comment),
            (r".", Comment),
        ],
        # Note mode ignores everything upto the matching ``<?end note?>`` tag
        "note": [
            # Nested ``<?note?>`` tag
            (r"<\?\s*note\s*\?>", Comment, "#push"),
            # ``<?end note?>`` tag
            (r"<\?\s*end\s+note\s*\?>", Comment, "#pop"),
            # Everything else
            (r"[^<]+", Comment),
            (r".", Comment),
        ],
        # Doc mode ignores everything upto the matching ``<?end doc?>`` tag
        "doc": [
            # Nested ``<?doc?>`` tag
            (r"<\?\s*doc\s*\?>", String.Doc, "#push"),
            # ``<?end doc?>`` tag
            (r"<\?\s*end\s+doc\s*\?>", String.Doc, "#pop"),
            # Everything else
            (r"[^<]+", String.Doc),
            (r".", String.Doc),
        ],
        # UL4 expressions
        "ul4": [
            # End the tag
            (r"\?>", Comment.Preproc, "#pop"),
            # Start triple quoted string constant
            ("'''", String, "string13"),
            ('"""', String, "string23"),
            # Start single quoted string constant
            ("'", String, "string1"),
            ('"', String, "string2"),
            # Floating point number
            (r"\d+\.\d*([eE][+-]?\d+)?", Number.Float),
            (r"\.\d+([eE][+-]?\d+)?", Number.Float),
            (r"\d+[eE][+-]?\d+", Number.Float),
            # Binary integer: ``0b101010``
            (r"0[bB][01]+", Number.Bin),
            # Octal integer: ``0o52``
            (r"0[oO][0-7]+", Number.Oct),
            # Hexadecimal integer: ``0x2a``
            (r"0[xX][0-9a-fA-F]+", Number.Hex),
            # Date or datetime: ``@(2000-02-29)``/``@(2000-02-29T12:34:56.987654)``
            (r"@\(\d\d\d\d-\d\d-\d\d(T(\d\d:\d\d(:\d\d(\.\d{6})?)?)?)?\)", Literal.Date),
            # Color: ``#fff``, ``#fff8f0`` etc.
            (r"#[0-9a-fA-F]{8}", Literal.Color),
            (r"#[0-9a-fA-F]{6}", Literal.Color),
            (r"#[0-9a-fA-F]{3,4}", Literal.Color),
            # Decimal integer: ``42``
            (r"\d+", Number.Integer),
            # Operators
            (r"//|==|!=|>=|<=|<<|>>|\+=|-=|\*=|/=|//=|<<=|>>=|&=|\|=|^=|=|[\[\]{},:*/().~%&|<>^+-]", Operator),
            # Keywords
            (words(("for", "in", "if", "else", "not", "is", "and", "or"), suffix=r"\b"), Keyword),
            # Builtin constants
            (words(("None", "False", "True"), suffix=r"\b"), Keyword.Constant),
            # Variable names
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
            # Whitespace
            (r"\s+", Text.Whitespace),
        ],
        # ``<?end ...?>`` tag for closing the last open block
        "end": [
            (r"\?>", Comment.Preproc, "#pop"),
            (words(("for", "if", "def", "while", "renderblock", "renderblocks"), suffix=r"\b"), Keyword),
            (r"\s+", Text),
        ],
        # Content of the ``<?whitespace ...?>`` tag:
        # ``keep``, ``strip`` or ``smart``
        "whitespace": [
            (r"\?>", Comment.Preproc, "#pop"),
            (words(("keep", "strip", "smart"), suffix=r"\b"), Comment.Preproc),
            (r"\s+", Text.Whitespace),
        ],
        # Inside a string constant
        "stringescapes": [
            (r"""\\[\\'"abtnfr]""", String.Escape),
            (r"\\x[0-9a-fA-F]{2}", String.Escape),
            (r"\\u[0-9a-fA-F]{4}", String.Escape),
            (r"\\U[0-9a-fA-F]{8}", String.Escape),
        ],
        # Inside a triple quoted string started with ``'''``
        "string13": [
            (r"'''", String, "#pop"),
            include("stringescapes"),
            (r"[^\\']+", String),
            (r'.', String),
        ],
        # Inside a triple quoted string started with ``"""``
        "string23": [
            (r'"""', String, "#pop"),
            include("stringescapes"),
            (r'[^\\"]+', String),
            (r'.', String),
        ],
        # Inside a single quoted string started with ``'``
        "string1": [
            (r"'", String, "#pop"),
            include("stringescapes"),
            (r"[^\\']+", String),
            (r'.', String),
        ],
        # Inside a single quoted string started with ``"``
        "string2": [
            (r'"', String, "#pop"),
            include("stringescapes"),
            (r'[^\\"]+', String),
            (r'.', String),
        ],
    }

class HTMLUL4Lexer(DelegatingLexer):
    """
    Lexer for UL4 embedded in HTML.
    """

    name = 'HTML+UL4'
    aliases = ['html+ul4']
    filenames = ['*.htmlul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(HtmlLexer, UL4Lexer, **options)


class XMLUL4Lexer(DelegatingLexer):
    """
    Lexer for UL4 embedded in XML.
    """

    name = 'XML+UL4'
    aliases = ['xml+ul4']
    filenames = ['*.xmlul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(XmlLexer, UL4Lexer, **options)


class CSSUL4Lexer(DelegatingLexer):
    """
    Lexer for UL4 embedded in CSS.
    """

    name = 'CSS+UL4'
    aliases = ['css+ul4']
    filenames = ['*.cssul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(CssLexer, UL4Lexer, **options)


class JavascriptUL4Lexer(DelegatingLexer):
    """
    Lexer for UL4 embedded in Javascript.
    """

    name = 'Javascript+UL4'
    aliases = ['js+ul4']
    filenames = ['*.jsul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(JavascriptLexer, UL4Lexer, **options)


class PythonUL4Lexer(DelegatingLexer):
    """
    Lexer for UL4 embedded in Python.
    """

    name = 'Python+UL4'
    aliases = ['py+ul4']
    filenames = ['*.pyul4']
    url = 'https://python.livinglogic.de/UL4.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(PythonLexer, UL4Lexer, **options)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\cache_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: CacheStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import storage


class CacheId(str):
    '''
    Unique identifier of the Cache object.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CacheId:
        return cls(json)

    def __repr__(self):
        return 'CacheId({})'.format(super().__repr__())


class CachedResponseType(enum.Enum):
    '''
    type of HTTP response cached
    '''
    BASIC = "basic"
    CORS = "cors"
    DEFAULT = "default"
    ERROR = "error"
    OPAQUE_RESPONSE = "opaqueResponse"
    OPAQUE_REDIRECT = "opaqueRedirect"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Request URL.
    request_url: str

    #: Request method.
    request_method: str

    #: Request headers
    request_headers: typing.List[Header]

    #: Number of seconds since epoch.
    response_time: float

    #: HTTP response status code.
    response_status: int

    #: HTTP response status text.
    response_status_text: str

    #: HTTP response type
    response_type: CachedResponseType

    #: Response headers
    response_headers: typing.List[Header]

    def to_json(self):
        json = dict()
        json['requestURL'] = self.request_url
        json['requestMethod'] = self.request_method
        json['requestHeaders'] = [i.to_json() for i in self.request_headers]
        json['responseTime'] = self.response_time
        json['responseStatus'] = self.response_status
        json['responseStatusText'] = self.response_status_text
        json['responseType'] = self.response_type.to_json()
        json['responseHeaders'] = [i.to_json() for i in self.response_headers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_url=str(json['requestURL']),
            request_method=str(json['requestMethod']),
            request_headers=[Header.from_json(i) for i in json['requestHeaders']],
            response_time=float(json['responseTime']),
            response_status=int(json['responseStatus']),
            response_status_text=str(json['responseStatusText']),
            response_type=CachedResponseType.from_json(json['responseType']),
            response_headers=[Header.from_json(i) for i in json['responseHeaders']],
        )


@dataclass
class Cache:
    '''
    Cache identifier.
    '''
    #: An opaque unique id of the cache.
    cache_id: CacheId

    #: Security origin of the cache.
    security_origin: str

    #: Storage key of the cache.
    storage_key: str

    #: The name of the cache.
    cache_name: str

    #: Storage bucket of the cache.
    storage_bucket: typing.Optional[storage.StorageBucket] = None

    def to_json(self):
        json = dict()
        json['cacheId'] = self.cache_id.to_json()
        json['securityOrigin'] = self.security_origin
        json['storageKey'] = self.storage_key
        json['cacheName'] = self.cache_name
        if self.storage_bucket is not None:
            json['storageBucket'] = self.storage_bucket.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cache_id=CacheId.from_json(json['cacheId']),
            security_origin=str(json['securityOrigin']),
            storage_key=str(json['storageKey']),
            cache_name=str(json['cacheName']),
            storage_bucket=storage.StorageBucket.from_json(json['storageBucket']) if 'storageBucket' in json else None,
        )


@dataclass
class Header:
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class CachedResponse:
    '''
    Cached response
    '''
    #: Entry content, base64-encoded.
    body: str

    def to_json(self):
        json = dict()
        json['body'] = self.body
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            body=str(json['body']),
        )


def delete_cache(
        cache_id: CacheId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache.

    :param cache_id: Id of cache for deletion.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteCache',
        'params': params,
    }
    json = yield cmd_dict


def delete_entry(
        cache_id: CacheId,
        request: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache entry.

    :param cache_id: Id of cache where the entry will be deleted.
    :param request: URL spec of the request.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['request'] = request
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteEntry',
        'params': params,
    }
    json = yield cmd_dict


def request_cache_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cache]]:
    '''
    Requests cache names.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Caches for the security origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCacheNames',
        'params': params,
    }
    json = yield cmd_dict
    return [Cache.from_json(i) for i in json['caches']]


def request_cached_response(
        cache_id: CacheId,
        request_url: str,
        request_headers: typing.List[Header]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CachedResponse]:
    '''
    Fetches cache entry.

    :param cache_id: Id of cache that contains the entry.
    :param request_url: URL spec of the request.
    :param request_headers: headers of the request.
    :returns: Response read from the cache.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['requestURL'] = request_url
    params['requestHeaders'] = [i.to_json() for i in request_headers]
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCachedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return CachedResponse.from_json(json['response'])


def request_entries(
        cache_id: CacheId,
        skip_count: typing.Optional[int] = None,
        page_size: typing.Optional[int] = None,
        path_filter: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], float]]:
    '''
    Requests data from cache.

    :param cache_id: ID of cache to get entries from.
    :param skip_count: *(Optional)* Number of records to skip.
    :param page_size: *(Optional)* Number of records to fetch.
    :param path_filter: *(Optional)* If present, only return the entries containing this substring in the path
    :returns: A tuple with the following items:

        0. **cacheDataEntries** - Array of object store data entries.
        1. **returnCount** - Count of returned entries from this storage. If pathFilter is empty, it is the count of all entries from this storage.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    if skip_count is not None:
        params['skipCount'] = skip_count
    if page_size is not None:
        params['pageSize'] = page_size
    if path_filter is not None:
        params['pathFilter'] = path_filter
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestEntries',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['cacheDataEntries']],
        float(json['returnCount'])
    )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\cache_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: CacheStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import storage


class CacheId(str):
    '''
    Unique identifier of the Cache object.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CacheId:
        return cls(json)

    def __repr__(self):
        return 'CacheId({})'.format(super().__repr__())


class CachedResponseType(enum.Enum):
    '''
    type of HTTP response cached
    '''
    BASIC = "basic"
    CORS = "cors"
    DEFAULT = "default"
    ERROR = "error"
    OPAQUE_RESPONSE = "opaqueResponse"
    OPAQUE_REDIRECT = "opaqueRedirect"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Request URL.
    request_url: str

    #: Request method.
    request_method: str

    #: Request headers
    request_headers: typing.List[Header]

    #: Number of seconds since epoch.
    response_time: float

    #: HTTP response status code.
    response_status: int

    #: HTTP response status text.
    response_status_text: str

    #: HTTP response type
    response_type: CachedResponseType

    #: Response headers
    response_headers: typing.List[Header]

    def to_json(self):
        json = dict()
        json['requestURL'] = self.request_url
        json['requestMethod'] = self.request_method
        json['requestHeaders'] = [i.to_json() for i in self.request_headers]
        json['responseTime'] = self.response_time
        json['responseStatus'] = self.response_status
        json['responseStatusText'] = self.response_status_text
        json['responseType'] = self.response_type.to_json()
        json['responseHeaders'] = [i.to_json() for i in self.response_headers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_url=str(json['requestURL']),
            request_method=str(json['requestMethod']),
            request_headers=[Header.from_json(i) for i in json['requestHeaders']],
            response_time=float(json['responseTime']),
            response_status=int(json['responseStatus']),
            response_status_text=str(json['responseStatusText']),
            response_type=CachedResponseType.from_json(json['responseType']),
            response_headers=[Header.from_json(i) for i in json['responseHeaders']],
        )


@dataclass
class Cache:
    '''
    Cache identifier.
    '''
    #: An opaque unique id of the cache.
    cache_id: CacheId

    #: Security origin of the cache.
    security_origin: str

    #: Storage key of the cache.
    storage_key: str

    #: The name of the cache.
    cache_name: str

    #: Storage bucket of the cache.
    storage_bucket: typing.Optional[storage.StorageBucket] = None

    def to_json(self):
        json = dict()
        json['cacheId'] = self.cache_id.to_json()
        json['securityOrigin'] = self.security_origin
        json['storageKey'] = self.storage_key
        json['cacheName'] = self.cache_name
        if self.storage_bucket is not None:
            json['storageBucket'] = self.storage_bucket.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cache_id=CacheId.from_json(json['cacheId']),
            security_origin=str(json['securityOrigin']),
            storage_key=str(json['storageKey']),
            cache_name=str(json['cacheName']),
            storage_bucket=storage.StorageBucket.from_json(json['storageBucket']) if 'storageBucket' in json else None,
        )


@dataclass
class Header:
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class CachedResponse:
    '''
    Cached response
    '''
    #: Entry content, base64-encoded.
    body: str

    def to_json(self):
        json = dict()
        json['body'] = self.body
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            body=str(json['body']),
        )


def delete_cache(
        cache_id: CacheId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache.

    :param cache_id: Id of cache for deletion.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteCache',
        'params': params,
    }
    json = yield cmd_dict


def delete_entry(
        cache_id: CacheId,
        request: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache entry.

    :param cache_id: Id of cache where the entry will be deleted.
    :param request: URL spec of the request.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['request'] = request
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteEntry',
        'params': params,
    }
    json = yield cmd_dict


def request_cache_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cache]]:
    '''
    Requests cache names.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Caches for the security origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCacheNames',
        'params': params,
    }
    json = yield cmd_dict
    return [Cache.from_json(i) for i in json['caches']]


def request_cached_response(
        cache_id: CacheId,
        request_url: str,
        request_headers: typing.List[Header]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CachedResponse]:
    '''
    Fetches cache entry.

    :param cache_id: Id of cache that contains the entry.
    :param request_url: URL spec of the request.
    :param request_headers: headers of the request.
    :returns: Response read from the cache.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['requestURL'] = request_url
    params['requestHeaders'] = [i.to_json() for i in request_headers]
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCachedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return CachedResponse.from_json(json['response'])


def request_entries(
        cache_id: CacheId,
        skip_count: typing.Optional[int] = None,
        page_size: typing.Optional[int] = None,
        path_filter: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], float]]:
    '''
    Requests data from cache.

    :param cache_id: ID of cache to get entries from.
    :param skip_count: *(Optional)* Number of records to skip.
    :param page_size: *(Optional)* Number of records to fetch.
    :param path_filter: *(Optional)* If present, only return the entries containing this substring in the path
    :returns: A tuple with the following items:

        0. **cacheDataEntries** - Array of object store data entries.
        1. **returnCount** - Count of returned entries from this storage. If pathFilter is empty, it is the count of all entries from this storage.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    if skip_count is not None:
        params['skipCount'] = skip_count
    if page_size is not None:
        params['pageSize'] = page_size
    if path_filter is not None:
        params['pathFilter'] = path_filter
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestEntries',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['cacheDataEntries']],
        float(json['returnCount'])
    )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\cache_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: CacheStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import storage


class CacheId(str):
    '''
    Unique identifier of the Cache object.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> CacheId:
        return cls(json)

    def __repr__(self):
        return 'CacheId({})'.format(super().__repr__())


class CachedResponseType(enum.Enum):
    '''
    type of HTTP response cached
    '''
    BASIC = "basic"
    CORS = "cors"
    DEFAULT = "default"
    ERROR = "error"
    OPAQUE_RESPONSE = "opaqueResponse"
    OPAQUE_REDIRECT = "opaqueRedirect"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class DataEntry:
    '''
    Data entry.
    '''
    #: Request URL.
    request_url: str

    #: Request method.
    request_method: str

    #: Request headers
    request_headers: typing.List[Header]

    #: Number of seconds since epoch.
    response_time: float

    #: HTTP response status code.
    response_status: int

    #: HTTP response status text.
    response_status_text: str

    #: HTTP response type
    response_type: CachedResponseType

    #: Response headers
    response_headers: typing.List[Header]

    def to_json(self):
        json = dict()
        json['requestURL'] = self.request_url
        json['requestMethod'] = self.request_method
        json['requestHeaders'] = [i.to_json() for i in self.request_headers]
        json['responseTime'] = self.response_time
        json['responseStatus'] = self.response_status
        json['responseStatusText'] = self.response_status_text
        json['responseType'] = self.response_type.to_json()
        json['responseHeaders'] = [i.to_json() for i in self.response_headers]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            request_url=str(json['requestURL']),
            request_method=str(json['requestMethod']),
            request_headers=[Header.from_json(i) for i in json['requestHeaders']],
            response_time=float(json['responseTime']),
            response_status=int(json['responseStatus']),
            response_status_text=str(json['responseStatusText']),
            response_type=CachedResponseType.from_json(json['responseType']),
            response_headers=[Header.from_json(i) for i in json['responseHeaders']],
        )


@dataclass
class Cache:
    '''
    Cache identifier.
    '''
    #: An opaque unique id of the cache.
    cache_id: CacheId

    #: Security origin of the cache.
    security_origin: str

    #: Storage key of the cache.
    storage_key: str

    #: The name of the cache.
    cache_name: str

    #: Storage bucket of the cache.
    storage_bucket: typing.Optional[storage.StorageBucket] = None

    def to_json(self):
        json = dict()
        json['cacheId'] = self.cache_id.to_json()
        json['securityOrigin'] = self.security_origin
        json['storageKey'] = self.storage_key
        json['cacheName'] = self.cache_name
        if self.storage_bucket is not None:
            json['storageBucket'] = self.storage_bucket.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            cache_id=CacheId.from_json(json['cacheId']),
            security_origin=str(json['securityOrigin']),
            storage_key=str(json['storageKey']),
            cache_name=str(json['cacheName']),
            storage_bucket=storage.StorageBucket.from_json(json['storageBucket']) if 'storageBucket' in json else None,
        )


@dataclass
class Header:
    name: str

    value: str

    def to_json(self):
        json = dict()
        json['name'] = self.name
        json['value'] = self.value
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']),
            value=str(json['value']),
        )


@dataclass
class CachedResponse:
    '''
    Cached response
    '''
    #: Entry content, base64-encoded.
    body: str

    def to_json(self):
        json = dict()
        json['body'] = self.body
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            body=str(json['body']),
        )


def delete_cache(
        cache_id: CacheId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache.

    :param cache_id: Id of cache for deletion.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteCache',
        'params': params,
    }
    json = yield cmd_dict


def delete_entry(
        cache_id: CacheId,
        request: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a cache entry.

    :param cache_id: Id of cache where the entry will be deleted.
    :param request: URL spec of the request.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['request'] = request
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.deleteEntry',
        'params': params,
    }
    json = yield cmd_dict


def request_cache_names(
        security_origin: typing.Optional[str] = None,
        storage_key: typing.Optional[str] = None,
        storage_bucket: typing.Optional[storage.StorageBucket] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Cache]]:
    '''
    Requests cache names.

    :param security_origin: *(Optional)* At least and at most one of securityOrigin, storageKey, storageBucket must be specified. Security origin.
    :param storage_key: *(Optional)* Storage key.
    :param storage_bucket: *(Optional)* Storage bucket. If not specified, it uses the default bucket.
    :returns: Caches for the security origin.
    '''
    params: T_JSON_DICT = dict()
    if security_origin is not None:
        params['securityOrigin'] = security_origin
    if storage_key is not None:
        params['storageKey'] = storage_key
    if storage_bucket is not None:
        params['storageBucket'] = storage_bucket.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCacheNames',
        'params': params,
    }
    json = yield cmd_dict
    return [Cache.from_json(i) for i in json['caches']]


def request_cached_response(
        cache_id: CacheId,
        request_url: str,
        request_headers: typing.List[Header]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,CachedResponse]:
    '''
    Fetches cache entry.

    :param cache_id: Id of cache that contains the entry.
    :param request_url: URL spec of the request.
    :param request_headers: headers of the request.
    :returns: Response read from the cache.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    params['requestURL'] = request_url
    params['requestHeaders'] = [i.to_json() for i in request_headers]
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestCachedResponse',
        'params': params,
    }
    json = yield cmd_dict
    return CachedResponse.from_json(json['response'])


def request_entries(
        cache_id: CacheId,
        skip_count: typing.Optional[int] = None,
        page_size: typing.Optional[int] = None,
        path_filter: typing.Optional[str] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.Tuple[typing.List[DataEntry], float]]:
    '''
    Requests data from cache.

    :param cache_id: ID of cache to get entries from.
    :param skip_count: *(Optional)* Number of records to skip.
    :param page_size: *(Optional)* Number of records to fetch.
    :param path_filter: *(Optional)* If present, only return the entries containing this substring in the path
    :returns: A tuple with the following items:

        0. **cacheDataEntries** - Array of object store data entries.
        1. **returnCount** - Count of returned entries from this storage. If pathFilter is empty, it is the count of all entries from this storage.
    '''
    params: T_JSON_DICT = dict()
    params['cacheId'] = cache_id.to_json()
    if skip_count is not None:
        params['skipCount'] = skip_count
    if page_size is not None:
        params['pageSize'] = page_size
    if path_filter is not None:
        params['pathFilter'] = path_filter
    cmd_dict: T_JSON_DICT = {
        'method': 'CacheStorage.requestEntries',
        'params': params,
    }
    json = yield cmd_dict
    return (
        [DataEntry.from_json(i) for i in json['cacheDataEntries']],
        float(json['returnCount'])
    )

# === NexusCore/openenv\Lib\site-packages\click\exceptions.py ===
from __future__ import annotations

import collections.abc as cabc
import typing as t
from gettext import gettext as _
from gettext import ngettext

from ._compat import get_text_stderr
from .globals import resolve_color_default
from .utils import echo
from .utils import format_filename

if t.TYPE_CHECKING:
    from .core import Command
    from .core import Context
    from .core import Parameter


def _join_param_hints(param_hint: cabc.Sequence[str] | str | None) -> str | None:
    if param_hint is not None and not isinstance(param_hint, str):
        return " / ".join(repr(x) for x in param_hint)

    return param_hint


class ClickException(Exception):
    """An exception that Click can handle and show to the user."""

    #: The exit code for this exception.
    exit_code = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        # The context will be removed by the time we print the message, so cache
        # the color settings here to be used later on (in `show`)
        self.show_color: bool | None = resolve_color_default()
        self.message = message

    def format_message(self) -> str:
        return self.message

    def __str__(self) -> str:
        return self.message

    def show(self, file: t.IO[t.Any] | None = None) -> None:
        if file is None:
            file = get_text_stderr()

        echo(
            _("Error: {message}").format(message=self.format_message()),
            file=file,
            color=self.show_color,
        )


class UsageError(ClickException):
    """An internal exception that signals a usage error.  This typically
    aborts any further handling.

    :param message: the error message to display.
    :param ctx: optionally the context that caused this error.  Click will
                fill in the context automatically in some situations.
    """

    exit_code = 2

    def __init__(self, message: str, ctx: Context | None = None) -> None:
        super().__init__(message)
        self.ctx = ctx
        self.cmd: Command | None = self.ctx.command if self.ctx else None

    def show(self, file: t.IO[t.Any] | None = None) -> None:
        if file is None:
            file = get_text_stderr()
        color = None
        hint = ""
        if (
            self.ctx is not None
            and self.ctx.command.get_help_option(self.ctx) is not None
        ):
            hint = _("Try '{command} {option}' for help.").format(
                command=self.ctx.command_path, option=self.ctx.help_option_names[0]
            )
            hint = f"{hint}\n"
        if self.ctx is not None:
            color = self.ctx.color
            echo(f"{self.ctx.get_usage()}\n{hint}", file=file, color=color)
        echo(
            _("Error: {message}").format(message=self.format_message()),
            file=file,
            color=color,
        )


class BadParameter(UsageError):
    """An exception that formats out a standardized error message for a
    bad parameter.  This is useful when thrown from a callback or type as
    Click will attach contextual information to it (for instance, which
    parameter it is).

    .. versionadded:: 2.0

    :param param: the parameter object that caused this error.  This can
                  be left out, and Click will attach this info itself
                  if possible.
    :param param_hint: a string that shows up as parameter name.  This
                       can be used as alternative to `param` in cases
                       where custom validation should happen.  If it is
                       a string it's used as such, if it's a list then
                       each item is quoted and separated.
    """

    def __init__(
        self,
        message: str,
        ctx: Context | None = None,
        param: Parameter | None = None,
        param_hint: str | None = None,
    ) -> None:
        super().__init__(message, ctx)
        self.param = param
        self.param_hint = param_hint

    def format_message(self) -> str:
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)  # type: ignore
        else:
            return _("Invalid value: {message}").format(message=self.message)

        return _("Invalid value for {param_hint}: {message}").format(
            param_hint=_join_param_hints(param_hint), message=self.message
        )


class MissingParameter(BadParameter):
    """Raised if click required an option or argument but it was not
    provided when invoking the script.

    .. versionadded:: 4.0

    :param param_type: a string that indicates the type of the parameter.
                       The default is to inherit the parameter type from
                       the given `param`.  Valid values are ``'parameter'``,
                       ``'option'`` or ``'argument'``.
    """

    def __init__(
        self,
        message: str | None = None,
        ctx: Context | None = None,
        param: Parameter | None = None,
        param_hint: str | None = None,
        param_type: str | None = None,
    ) -> None:
        super().__init__(message or "", ctx, param, param_hint)
        self.param_type = param_type

    def format_message(self) -> str:
        if self.param_hint is not None:
            param_hint: str | None = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)  # type: ignore
        else:
            param_hint = None

        param_hint = _join_param_hints(param_hint)
        param_hint = f" {param_hint}" if param_hint else ""

        param_type = self.param_type
        if param_type is None and self.param is not None:
            param_type = self.param.param_type_name

        msg = self.message
        if self.param is not None:
            msg_extra = self.param.type.get_missing_message(
                param=self.param, ctx=self.ctx
            )
            if msg_extra:
                if msg:
                    msg += f". {msg_extra}"
                else:
                    msg = msg_extra

        msg = f" {msg}" if msg else ""

        # Translate param_type for known types.
        if param_type == "argument":
            missing = _("Missing argument")
        elif param_type == "option":
            missing = _("Missing option")
        elif param_type == "parameter":
            missing = _("Missing parameter")
        else:
            missing = _("Missing {param_type}").format(param_type=param_type)

        return f"{missing}{param_hint}.{msg}"

    def __str__(self) -> str:
        if not self.message:
            param_name = self.param.name if self.param else None
            return _("Missing parameter: {param_name}").format(param_name=param_name)
        else:
            return self.message


class NoSuchOption(UsageError):
    """Raised if click attempted to handle an option that does not
    exist.

    .. versionadded:: 4.0
    """

    def __init__(
        self,
        option_name: str,
        message: str | None = None,
        possibilities: cabc.Sequence[str] | None = None,
        ctx: Context | None = None,
    ) -> None:
        if message is None:
            message = _("No such option: {name}").format(name=option_name)

        super().__init__(message, ctx)
        self.option_name = option_name
        self.possibilities = possibilities

    def format_message(self) -> str:
        if not self.possibilities:
            return self.message

        possibility_str = ", ".join(sorted(self.possibilities))
        suggest = ngettext(
            "Did you mean {possibility}?",
            "(Possible options: {possibilities})",
            len(self.possibilities),
        ).format(possibility=possibility_str, possibilities=possibility_str)
        return f"{self.message} {suggest}"


class BadOptionUsage(UsageError):
    """Raised if an option is generally supplied but the use of the option
    was incorrect.  This is for instance raised if the number of arguments
    for an option is not correct.

    .. versionadded:: 4.0

    :param option_name: the name of the option being used incorrectly.
    """

    def __init__(
        self, option_name: str, message: str, ctx: Context | None = None
    ) -> None:
        super().__init__(message, ctx)
        self.option_name = option_name


class BadArgumentUsage(UsageError):
    """Raised if an argument is generally supplied but the use of the argument
    was incorrect.  This is for instance raised if the number of values
    for an argument is not correct.

    .. versionadded:: 6.0
    """


class NoArgsIsHelpError(UsageError):
    def __init__(self, ctx: Context) -> None:
        self.ctx: Context
        super().__init__(ctx.get_help(), ctx=ctx)

    def show(self, file: t.IO[t.Any] | None = None) -> None:
        echo(self.format_message(), file=file, err=True, color=self.ctx.color)


class FileError(ClickException):
    """Raised if a file cannot be opened."""

    def __init__(self, filename: str, hint: str | None = None) -> None:
        if hint is None:
            hint = _("unknown error")

        super().__init__(hint)
        self.ui_filename: str = format_filename(filename)
        self.filename = filename

    def format_message(self) -> str:
        return _("Could not open file {filename!r}: {message}").format(
            filename=self.ui_filename, message=self.message
        )


class Abort(RuntimeError):
    """An internal signalling exception that signals Click to abort."""


class Exit(RuntimeError):
    """An exception that indicates that the application should exit with some
    status code.

    :param code: the status code to exit with.
    """

    __slots__ = ("exit_code",)

    def __init__(self, code: int = 0) -> None:
        self.exit_code: int = code

# === NexusCore/openenv\Lib\site-packages\pydantic\_migration.py ===
import sys
from typing import Any, Callable

from .version import version_short

MOVED_IN_V2 = {
    'pydantic.utils:version_info': 'pydantic.version:version_info',
    'pydantic.error_wrappers:ValidationError': 'pydantic:ValidationError',
    'pydantic.utils:to_camel': 'pydantic.alias_generators:to_pascal',
    'pydantic.utils:to_lower_camel': 'pydantic.alias_generators:to_camel',
    'pydantic:PyObject': 'pydantic.types:ImportString',
    'pydantic.types:PyObject': 'pydantic.types:ImportString',
    'pydantic.generics:GenericModel': 'pydantic.BaseModel',
}

DEPRECATED_MOVED_IN_V2 = {
    'pydantic.tools:schema_of': 'pydantic.deprecated.tools:schema_of',
    'pydantic.tools:parse_obj_as': 'pydantic.deprecated.tools:parse_obj_as',
    'pydantic.tools:schema_json_of': 'pydantic.deprecated.tools:schema_json_of',
    'pydantic.json:pydantic_encoder': 'pydantic.deprecated.json:pydantic_encoder',
    'pydantic:validate_arguments': 'pydantic.deprecated.decorator:validate_arguments',
    'pydantic.json:custom_pydantic_encoder': 'pydantic.deprecated.json:custom_pydantic_encoder',
    'pydantic.json:timedelta_isoformat': 'pydantic.deprecated.json:timedelta_isoformat',
    'pydantic.decorator:validate_arguments': 'pydantic.deprecated.decorator:validate_arguments',
    'pydantic.class_validators:validator': 'pydantic.deprecated.class_validators:validator',
    'pydantic.class_validators:root_validator': 'pydantic.deprecated.class_validators:root_validator',
    'pydantic.config:BaseConfig': 'pydantic.deprecated.config:BaseConfig',
    'pydantic.config:Extra': 'pydantic.deprecated.config:Extra',
}

REDIRECT_TO_V1 = {
    f'pydantic.utils:{obj}': f'pydantic.v1.utils:{obj}'
    for obj in (
        'deep_update',
        'GetterDict',
        'lenient_issubclass',
        'lenient_isinstance',
        'is_valid_field',
        'update_not_none',
        'import_string',
        'Representation',
        'ROOT_KEY',
        'smart_deepcopy',
        'sequence_like',
    )
}


REMOVED_IN_V2 = {
    'pydantic:ConstrainedBytes',
    'pydantic:ConstrainedDate',
    'pydantic:ConstrainedDecimal',
    'pydantic:ConstrainedFloat',
    'pydantic:ConstrainedFrozenSet',
    'pydantic:ConstrainedInt',
    'pydantic:ConstrainedList',
    'pydantic:ConstrainedSet',
    'pydantic:ConstrainedStr',
    'pydantic:JsonWrapper',
    'pydantic:NoneBytes',
    'pydantic:NoneStr',
    'pydantic:NoneStrBytes',
    'pydantic:Protocol',
    'pydantic:Required',
    'pydantic:StrBytes',
    'pydantic:compiled',
    'pydantic.config:get_config',
    'pydantic.config:inherit_config',
    'pydantic.config:prepare_config',
    'pydantic:create_model_from_namedtuple',
    'pydantic:create_model_from_typeddict',
    'pydantic.dataclasses:create_pydantic_model_from_dataclass',
    'pydantic.dataclasses:make_dataclass_validator',
    'pydantic.dataclasses:set_validation',
    'pydantic.datetime_parse:parse_date',
    'pydantic.datetime_parse:parse_time',
    'pydantic.datetime_parse:parse_datetime',
    'pydantic.datetime_parse:parse_duration',
    'pydantic.error_wrappers:ErrorWrapper',
    'pydantic.errors:AnyStrMaxLengthError',
    'pydantic.errors:AnyStrMinLengthError',
    'pydantic.errors:ArbitraryTypeError',
    'pydantic.errors:BoolError',
    'pydantic.errors:BytesError',
    'pydantic.errors:CallableError',
    'pydantic.errors:ClassError',
    'pydantic.errors:ColorError',
    'pydantic.errors:ConfigError',
    'pydantic.errors:DataclassTypeError',
    'pydantic.errors:DateError',
    'pydantic.errors:DateNotInTheFutureError',
    'pydantic.errors:DateNotInThePastError',
    'pydantic.errors:DateTimeError',
    'pydantic.errors:DecimalError',
    'pydantic.errors:DecimalIsNotFiniteError',
    'pydantic.errors:DecimalMaxDigitsError',
    'pydantic.errors:DecimalMaxPlacesError',
    'pydantic.errors:DecimalWholeDigitsError',
    'pydantic.errors:DictError',
    'pydantic.errors:DurationError',
    'pydantic.errors:EmailError',
    'pydantic.errors:EnumError',
    'pydantic.errors:EnumMemberError',
    'pydantic.errors:ExtraError',
    'pydantic.errors:FloatError',
    'pydantic.errors:FrozenSetError',
    'pydantic.errors:FrozenSetMaxLengthError',
    'pydantic.errors:FrozenSetMinLengthError',
    'pydantic.errors:HashableError',
    'pydantic.errors:IPv4AddressError',
    'pydantic.errors:IPv4InterfaceError',
    'pydantic.errors:IPv4NetworkError',
    'pydantic.errors:IPv6AddressError',
    'pydantic.errors:IPv6InterfaceError',
    'pydantic.errors:IPv6NetworkError',
    'pydantic.errors:IPvAnyAddressError',
    'pydantic.errors:IPvAnyInterfaceError',
    'pydantic.errors:IPvAnyNetworkError',
    'pydantic.errors:IntEnumError',
    'pydantic.errors:IntegerError',
    'pydantic.errors:InvalidByteSize',
    'pydantic.errors:InvalidByteSizeUnit',
    'pydantic.errors:InvalidDiscriminator',
    'pydantic.errors:InvalidLengthForBrand',
    'pydantic.errors:JsonError',
    'pydantic.errors:JsonTypeError',
    'pydantic.errors:ListError',
    'pydantic.errors:ListMaxLengthError',
    'pydantic.errors:ListMinLengthError',
    'pydantic.errors:ListUniqueItemsError',
    'pydantic.errors:LuhnValidationError',
    'pydantic.errors:MissingDiscriminator',
    'pydantic.errors:MissingError',
    'pydantic.errors:NoneIsAllowedError',
    'pydantic.errors:NoneIsNotAllowedError',
    'pydantic.errors:NotDigitError',
    'pydantic.errors:NotNoneError',
    'pydantic.errors:NumberNotGeError',
    'pydantic.errors:NumberNotGtError',
    'pydantic.errors:NumberNotLeError',
    'pydantic.errors:NumberNotLtError',
    'pydantic.errors:NumberNotMultipleError',
    'pydantic.errors:PathError',
    'pydantic.errors:PathNotADirectoryError',
    'pydantic.errors:PathNotAFileError',
    'pydantic.errors:PathNotExistsError',
    'pydantic.errors:PatternError',
    'pydantic.errors:PyObjectError',
    'pydantic.errors:PydanticTypeError',
    'pydantic.errors:PydanticValueError',
    'pydantic.errors:SequenceError',
    'pydantic.errors:SetError',
    'pydantic.errors:SetMaxLengthError',
    'pydantic.errors:SetMinLengthError',
    'pydantic.errors:StrError',
    'pydantic.errors:StrRegexError',
    'pydantic.errors:StrictBoolError',
    'pydantic.errors:SubclassError',
    'pydantic.errors:TimeError',
    'pydantic.errors:TupleError',
    'pydantic.errors:TupleLengthError',
    'pydantic.errors:UUIDError',
    'pydantic.errors:UUIDVersionError',
    'pydantic.errors:UrlError',
    'pydantic.errors:UrlExtraError',
    'pydantic.errors:UrlHostError',
    'pydantic.errors:UrlHostTldError',
    'pydantic.errors:UrlPortError',
    'pydantic.errors:UrlSchemeError',
    'pydantic.errors:UrlSchemePermittedError',
    'pydantic.errors:UrlUserInfoError',
    'pydantic.errors:WrongConstantError',
    'pydantic.main:validate_model',
    'pydantic.networks:stricturl',
    'pydantic:parse_file_as',
    'pydantic:parse_raw_as',
    'pydantic:stricturl',
    'pydantic.tools:parse_file_as',
    'pydantic.tools:parse_raw_as',
    'pydantic.types:ConstrainedBytes',
    'pydantic.types:ConstrainedDate',
    'pydantic.types:ConstrainedDecimal',
    'pydantic.types:ConstrainedFloat',
    'pydantic.types:ConstrainedFrozenSet',
    'pydantic.types:ConstrainedInt',
    'pydantic.types:ConstrainedList',
    'pydantic.types:ConstrainedSet',
    'pydantic.types:ConstrainedStr',
    'pydantic.types:JsonWrapper',
    'pydantic.types:NoneBytes',
    'pydantic.types:NoneStr',
    'pydantic.types:NoneStrBytes',
    'pydantic.types:StrBytes',
    'pydantic.typing:evaluate_forwardref',
    'pydantic.typing:AbstractSetIntStr',
    'pydantic.typing:AnyCallable',
    'pydantic.typing:AnyClassMethod',
    'pydantic.typing:CallableGenerator',
    'pydantic.typing:DictAny',
    'pydantic.typing:DictIntStrAny',
    'pydantic.typing:DictStrAny',
    'pydantic.typing:IntStr',
    'pydantic.typing:ListStr',
    'pydantic.typing:MappingIntStrAny',
    'pydantic.typing:NoArgAnyCallable',
    'pydantic.typing:NoneType',
    'pydantic.typing:ReprArgs',
    'pydantic.typing:SetStr',
    'pydantic.typing:StrPath',
    'pydantic.typing:TupleGenerator',
    'pydantic.typing:WithArgsTypes',
    'pydantic.typing:all_literal_values',
    'pydantic.typing:display_as_type',
    'pydantic.typing:get_all_type_hints',
    'pydantic.typing:get_args',
    'pydantic.typing:get_origin',
    'pydantic.typing:get_sub_types',
    'pydantic.typing:is_callable_type',
    'pydantic.typing:is_classvar',
    'pydantic.typing:is_finalvar',
    'pydantic.typing:is_literal_type',
    'pydantic.typing:is_namedtuple',
    'pydantic.typing:is_new_type',
    'pydantic.typing:is_none_type',
    'pydantic.typing:is_typeddict',
    'pydantic.typing:is_typeddict_special',
    'pydantic.typing:is_union',
    'pydantic.typing:new_type_supertype',
    'pydantic.typing:resolve_annotations',
    'pydantic.typing:typing_base',
    'pydantic.typing:update_field_forward_refs',
    'pydantic.typing:update_model_forward_refs',
    'pydantic.utils:ClassAttribute',
    'pydantic.utils:DUNDER_ATTRIBUTES',
    'pydantic.utils:PyObjectStr',
    'pydantic.utils:ValueItems',
    'pydantic.utils:almost_equal_floats',
    'pydantic.utils:get_discriminator_alias_and_values',
    'pydantic.utils:get_model',
    'pydantic.utils:get_unique_discriminator_alias',
    'pydantic.utils:in_ipython',
    'pydantic.utils:is_valid_identifier',
    'pydantic.utils:path_type',
    'pydantic.utils:validate_field_name',
    'pydantic:validate_model',
}


def getattr_migration(module: str) -> Callable[[str], Any]:
    """Implement PEP 562 for objects that were either moved or removed on the migration
    to V2.

    Args:
        module: The module name.

    Returns:
        A callable that will raise an error if the object is not found.
    """
    # This avoids circular import with errors.py.
    from .errors import PydanticImportError

    def wrapper(name: str) -> object:
        """Raise an error if the object is not found, or warn if it was moved.

        In case it was moved, it still returns the object.

        Args:
            name: The object name.

        Returns:
            The object.
        """
        if name == '__path__':
            raise AttributeError(f'module {module!r} has no attribute {name!r}')

        import warnings

        from ._internal._validators import import_string

        import_path = f'{module}:{name}'
        if import_path in MOVED_IN_V2.keys():
            new_location = MOVED_IN_V2[import_path]
            warnings.warn(f'`{import_path}` has been moved to `{new_location}`.')
            return import_string(MOVED_IN_V2[import_path])
        if import_path in DEPRECATED_MOVED_IN_V2:
            # skip the warning here because a deprecation warning will be raised elsewhere
            return import_string(DEPRECATED_MOVED_IN_V2[import_path])
        if import_path in REDIRECT_TO_V1:
            new_location = REDIRECT_TO_V1[import_path]
            warnings.warn(
                f'`{import_path}` has been removed. We are importing from `{new_location}` instead.'
                'See the migration guide for more details: https://docs.pydantic.dev/latest/migration/'
            )
            return import_string(REDIRECT_TO_V1[import_path])
        if import_path == 'pydantic:BaseSettings':
            raise PydanticImportError(
                '`BaseSettings` has been moved to the `pydantic-settings` package. '
                f'See https://docs.pydantic.dev/{version_short()}/migration/#basesettings-has-moved-to-pydantic-settings '
                'for more details.'
            )
        if import_path in REMOVED_IN_V2:
            raise PydanticImportError(f'`{import_path}` has been removed in V2.')
        globals: dict[str, Any] = sys.modules[module].__dict__
        if name in globals:
            return globals[name]
        raise AttributeError(f'module {module!r} has no attribute {name!r}')

    return wrapper

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_runfiles\pydev_runfiles_pytest2.py ===
import base64
import os
import pickle
import sys
import time
import zlib
from pathlib import Path

import pytest
from pydevd_file_utils import canonical_normalized_path

from _pydev_runfiles import pydev_runfiles_xml_rpc

# =========================================================================
# Load filters with tests we should skip
# =========================================================================
py_test_accept_filter = None


def _load_filters():
    global py_test_accept_filter
    if py_test_accept_filter is None:
        py_test_accept_filter = os.environ.get("PYDEV_PYTEST_SKIP")
        if py_test_accept_filter:
            py_test_accept_filter = pickle.loads(zlib.decompress(base64.b64decode(py_test_accept_filter)))

            # Newer versions of pytest resolve symlinks, so, we
            # may need to filter with a resolved path too.
            new_dct = {}
            for filename, value in py_test_accept_filter.items():
                new_dct[canonical_normalized_path(str(Path(filename).resolve()))] = value

            py_test_accept_filter.update(new_dct)

        else:
            py_test_accept_filter = {}


def is_in_xdist_node():
    main_pid = os.environ.get("PYDEV_MAIN_PID")
    if main_pid and main_pid != str(os.getpid()):
        return True
    return False


connected = False


def connect_to_server_for_communication_to_xml_rpc_on_xdist():
    global connected
    if connected:
        return
    connected = True
    if is_in_xdist_node():
        port = os.environ.get("PYDEV_PYTEST_SERVER")
        if port == "None":
            pass
        elif not port:
            sys.stderr.write("Error: no PYDEV_PYTEST_SERVER environment variable defined.\n")
        else:
            pydev_runfiles_xml_rpc.initialize_server(int(port), daemon=True)


PY2 = sys.version_info[0] <= 2
PY3 = not PY2


class State:
    start_time = time.time()
    buf_err = None
    buf_out = None


def start_redirect():
    if State.buf_out is not None:
        return
    from _pydevd_bundle import pydevd_io

    State.buf_err = pydevd_io.start_redirect(keep_original_redirection=True, std="stderr")
    State.buf_out = pydevd_io.start_redirect(keep_original_redirection=True, std="stdout")


def get_curr_output():
    buf_out = State.buf_out
    buf_err = State.buf_err
    return buf_out.getvalue() if buf_out is not None else "", buf_err.getvalue() if buf_err is not None else ""


def pytest_unconfigure():
    if is_in_xdist_node():
        return
    # Only report that it finished when on the main node (we don't want to report
    # the finish on each separate node).
    pydev_runfiles_xml_rpc.notifyTestRunFinished("Finished in: %.2f secs." % (time.time() - State.start_time,))


def pytest_collection_modifyitems(session, config, items):
    # A note: in xdist, this is not called on the main process, only in the
    # secondary nodes, so, we'll actually make the filter and report it multiple
    # times.
    connect_to_server_for_communication_to_xml_rpc_on_xdist()

    _load_filters()
    if not py_test_accept_filter:
        pydev_runfiles_xml_rpc.notifyTestsCollected(len(items))
        return  # Keep on going (nothing to filter)

    new_items = []
    for item in items:
        f = canonical_normalized_path(str(item.parent.fspath))
        name = item.name

        if f not in py_test_accept_filter:
            # print('Skip file: %s' % (f,))
            continue  # Skip the file

        i = name.find("[")
        name_without_parametrize = None
        if i > 0:
            name_without_parametrize = name[:i]

        accept_tests = py_test_accept_filter[f]

        if item.cls is not None:
            class_name = item.cls.__name__
        else:
            class_name = None
        for test in accept_tests:
            if test == name:
                # Direct match of the test (just go on with the default
                # loading)
                new_items.append(item)
                break

            if name_without_parametrize is not None and test == name_without_parametrize:
                # This happens when parameterizing pytest tests on older versions
                # of pytest where the test name doesn't include the fixture name
                # in it.
                new_items.append(item)
                break

            if class_name is not None:
                if test == class_name + "." + name:
                    new_items.append(item)
                    break

                if name_without_parametrize is not None and test == class_name + "." + name_without_parametrize:
                    new_items.append(item)
                    break

                if class_name == test:
                    new_items.append(item)
                    break
        else:
            pass
            # print('Skip test: %s.%s. Accept: %s' % (class_name, name, accept_tests))

    # Modify the original list
    items[:] = new_items
    pydev_runfiles_xml_rpc.notifyTestsCollected(len(items))


try:
    """
    pytest > 5.4 uses own version of TerminalWriter based on py.io.TerminalWriter
    and assumes there is a specific method TerminalWriter._write_source
    so try load pytest version first or fallback to default one
    """
    from _pytest._io import TerminalWriter
except ImportError:
    from py.io import TerminalWriter


def _get_error_contents_from_report(report):
    if report.longrepr is not None:
        try:
            tw = TerminalWriter(stringio=True)
            stringio = tw.stringio
        except TypeError:
            import io

            stringio = io.StringIO()
            tw = TerminalWriter(file=stringio)
        tw.hasmarkup = False
        report.toterminal(tw)
        exc = stringio.getvalue()
        s = exc.strip()
        if s:
            return s

    return ""


def pytest_collectreport(report):
    error_contents = _get_error_contents_from_report(report)
    if error_contents:
        report_test("fail", "<collect errors>", "<collect errors>", "", error_contents, 0.0)


def append_strings(s1, s2):
    if s1.__class__ == s2.__class__:
        return s1 + s2

    # Prefer str
    if isinstance(s1, bytes):
        s1 = s1.decode("utf-8", "replace")

    if isinstance(s2, bytes):
        s2 = s2.decode("utf-8", "replace")

    return s1 + s2


def pytest_runtest_logreport(report):
    if is_in_xdist_node():
        # When running with xdist, we don't want the report to be called from the node, only
        # from the main process.
        return
    report_duration = report.duration
    report_when = report.when
    report_outcome = report.outcome

    if hasattr(report, "wasxfail"):
        if report_outcome != "skipped":
            report_outcome = "passed"

    if report_outcome == "passed":
        # passed on setup/teardown: no need to report if in setup or teardown
        # (only on the actual test if it passed).
        if report_when in ("setup", "teardown"):
            return

        status = "ok"

    elif report_outcome == "skipped":
        status = "skip"

    else:
        # It has only passed, skipped and failed (no error), so, let's consider
        # error if not on call.
        if report_when in ("setup", "teardown"):
            status = "error"

        else:
            # any error in the call (not in setup or teardown) is considered a
            # regular failure.
            status = "fail"

    # This will work if pytest is not capturing it, if it is, nothing will
    # come from here...
    captured_output, error_contents = getattr(report, "pydev_captured_output", ""), getattr(report, "pydev_error_contents", "")
    for type_section, value in report.sections:
        if value:
            if type_section in ("err", "stderr", "Captured stderr call"):
                error_contents = append_strings(error_contents, value)
            else:
                captured_output = append_strings(error_contents, value)

    filename = getattr(report, "pydev_fspath_strpath", "<unable to get>")
    test = report.location[2]

    if report_outcome != "skipped":
        # On skipped, we'll have a traceback for the skip, which is not what we
        # want.
        exc = _get_error_contents_from_report(report)
        if exc:
            if error_contents:
                error_contents = append_strings(error_contents, "----------------------------- Exceptions -----------------------------\n")
            error_contents = append_strings(error_contents, exc)

    report_test(status, filename, test, captured_output, error_contents, report_duration)


def report_test(status, filename, test, captured_output, error_contents, duration):
    """
    @param filename: 'D:\\src\\mod1\\hello.py'
    @param test: 'TestCase.testMet1'
    @param status: fail, error, ok
    """
    time_str = "%.2f" % (duration,)
    pydev_runfiles_xml_rpc.notifyTest(status, captured_output, error_contents, filename, test, time_str)


if not hasattr(pytest, "hookimpl"):
    raise AssertionError("Please upgrade pytest (the current version of pytest: %s is unsupported)" % (pytest.__version__,))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    report.pydev_fspath_strpath = item.fspath.strpath
    report.pydev_captured_output, report.pydev_error_contents = get_curr_output()


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    """
    Note: with xdist will be on a secondary process.
    """
    # We have our own redirection: if xdist does its redirection, we'll have
    # nothing in our contents (which is OK), but if it does, we'll get nothing
    # from pytest but will get our own here.
    start_redirect()
    filename = item.fspath.strpath
    test = item.location[2]

    pydev_runfiles_xml_rpc.notifyStartTest(filename, test)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\discuss_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport


class DiscussServiceGrpcTransport(DiscussServiceTransport):
    """gRPC backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
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
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
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
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
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

        if isinstance(channel, grpc.Channel):
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

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    ~.GenerateMessageResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    ~.CountMessageTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("DiscussServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\discuss_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta3.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport


class DiscussServiceGrpcTransport(DiscussServiceTransport):
    """gRPC backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
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
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
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
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
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

        if isinstance(channel, grpc.Channel):
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

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    ~.GenerateMessageResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    ~.CountMessageTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta3.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("DiscussServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_functions.py ===
from __future__ import annotations

import sys
import warnings
from typing import Any, Callable, NoReturn, TypeVar, Union, overload

from . import _suppression
from ._checkers import BINARY_MAGIC_METHODS, check_type_internal
from ._config import (
    CollectionCheckStrategy,
    ForwardRefPolicy,
    TypeCheckConfiguration,
)
from ._exceptions import TypeCheckError, TypeCheckWarning
from ._memo import TypeCheckMemo
from ._utils import get_stacklevel, qualified_name

if sys.version_info >= (3, 11):
    from typing import Literal, Never, TypeAlias
else:
    from typing_extensions import Literal, Never, TypeAlias

T = TypeVar("T")
TypeCheckFailCallback: TypeAlias = Callable[[TypeCheckError, TypeCheckMemo], Any]


@overload
def check_type(
    value: object,
    expected_type: type[T],
    *,
    forward_ref_policy: ForwardRefPolicy = ...,
    typecheck_fail_callback: TypeCheckFailCallback | None = ...,
    collection_check_strategy: CollectionCheckStrategy = ...,
) -> T: ...


@overload
def check_type(
    value: object,
    expected_type: Any,
    *,
    forward_ref_policy: ForwardRefPolicy = ...,
    typecheck_fail_callback: TypeCheckFailCallback | None = ...,
    collection_check_strategy: CollectionCheckStrategy = ...,
) -> Any: ...


def check_type(
    value: object,
    expected_type: Any,
    *,
    forward_ref_policy: ForwardRefPolicy = TypeCheckConfiguration().forward_ref_policy,
    typecheck_fail_callback: TypeCheckFailCallback | None = (
        TypeCheckConfiguration().typecheck_fail_callback
    ),
    collection_check_strategy: CollectionCheckStrategy = (
        TypeCheckConfiguration().collection_check_strategy
    ),
) -> Any:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or
    :func:`issubclass` so a number of type specific checks are required. This function
    knows which checker to call for which type.

    This function wraps :func:`~.check_type_internal` in the following ways:

    * Respects type checking suppression (:func:`~.suppress_type_checks`)
    * Forms a :class:`~.TypeCheckMemo` from the current stack frame
    * Calls the configured type check fail callback if the check fails

    Note that this function is independent of the globally shared configuration in
    :data:`typeguard.config`. This means that usage within libraries is safe from being
    affected configuration changes made by other libraries or by the integrating
    application. Instead, configuration options have the same default values as their
    corresponding fields in :class:`TypeCheckConfiguration`.

    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance, or a tuple of such things
    :param forward_ref_policy: see :attr:`TypeCheckConfiguration.forward_ref_policy`
    :param typecheck_fail_callback:
        see :attr`TypeCheckConfiguration.typecheck_fail_callback`
    :param collection_check_strategy:
        see :attr:`TypeCheckConfiguration.collection_check_strategy`
    :return: ``value``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    if type(expected_type) is tuple:
        expected_type = Union[expected_type]

    config = TypeCheckConfiguration(
        forward_ref_policy=forward_ref_policy,
        typecheck_fail_callback=typecheck_fail_callback,
        collection_check_strategy=collection_check_strategy,
    )

    if _suppression.type_checks_suppressed or expected_type is Any:
        return value

    frame = sys._getframe(1)
    memo = TypeCheckMemo(frame.f_globals, frame.f_locals, config=config)
    try:
        check_type_internal(value, expected_type, memo)
    except TypeCheckError as exc:
        exc.append_path_element(qualified_name(value, add_class_prefix=True))
        if config.typecheck_fail_callback:
            config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_argument_types(
    func_name: str,
    arguments: dict[str, tuple[Any, Any]],
    memo: TypeCheckMemo,
) -> Literal[True]:
    if _suppression.type_checks_suppressed:
        return True

    for argname, (value, annotation) in arguments.items():
        if annotation is NoReturn or annotation is Never:
            exc = TypeCheckError(
                f"{func_name}() was declared never to be called but it was"
            )
            if memo.config.typecheck_fail_callback:
                memo.config.typecheck_fail_callback(exc, memo)
            else:
                raise exc

        try:
            check_type_internal(value, annotation, memo)
        except TypeCheckError as exc:
            qualname = qualified_name(value, add_class_prefix=True)
            exc.append_path_element(f'argument "{argname}" ({qualname})')
            if memo.config.typecheck_fail_callback:
                memo.config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return True


def check_return_type(
    func_name: str,
    retval: T,
    annotation: Any,
    memo: TypeCheckMemo,
) -> T:
    if _suppression.type_checks_suppressed:
        return retval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(f"{func_name}() was declared never to return but it did")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(retval, annotation, memo)
    except TypeCheckError as exc:
        # Allow NotImplemented if this is a binary magic method (__eq__() et al)
        if retval is NotImplemented and annotation is bool:
            # This does (and cannot) not check if it's actually a method
            func_name = func_name.rsplit(".", 1)[-1]
            if func_name in BINARY_MAGIC_METHODS:
                return retval

        qualname = qualified_name(retval, add_class_prefix=True)
        exc.append_path_element(f"the return value ({qualname})")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return retval


def check_send_type(
    func_name: str,
    sendval: T,
    annotation: Any,
    memo: TypeCheckMemo,
) -> T:
    if _suppression.type_checks_suppressed:
        return sendval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(
            f"{func_name}() was declared never to be sent a value to but it was"
        )
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(sendval, annotation, memo)
    except TypeCheckError as exc:
        qualname = qualified_name(sendval, add_class_prefix=True)
        exc.append_path_element(f"the value sent to generator ({qualname})")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return sendval


def check_yield_type(
    func_name: str,
    yieldval: T,
    annotation: Any,
    memo: TypeCheckMemo,
) -> T:
    if _suppression.type_checks_suppressed:
        return yieldval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(f"{func_name}() was declared never to yield but it did")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(yieldval, annotation, memo)
    except TypeCheckError as exc:
        qualname = qualified_name(yieldval, add_class_prefix=True)
        exc.append_path_element(f"the yielded value ({qualname})")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return yieldval


def check_variable_assignment(
    value: object, varname: str, annotation: Any, memo: TypeCheckMemo
) -> Any:
    if _suppression.type_checks_suppressed:
        return value

    try:
        check_type_internal(value, annotation, memo)
    except TypeCheckError as exc:
        qualname = qualified_name(value, add_class_prefix=True)
        exc.append_path_element(f"value assigned to {varname} ({qualname})")
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_multi_variable_assignment(
    value: Any, targets: list[dict[str, Any]], memo: TypeCheckMemo
) -> Any:
    if max(len(target) for target in targets) == 1:
        iterated_values = [value]
    else:
        iterated_values = list(value)

    if not _suppression.type_checks_suppressed:
        for expected_types in targets:
            value_index = 0
            for ann_index, (varname, expected_type) in enumerate(
                expected_types.items()
            ):
                if varname.startswith("*"):
                    varname = varname[1:]
                    keys_left = len(expected_types) - 1 - ann_index
                    next_value_index = len(iterated_values) - keys_left
                    obj: object = iterated_values[value_index:next_value_index]
                    value_index = next_value_index
                else:
                    obj = iterated_values[value_index]
                    value_index += 1

                try:
                    check_type_internal(obj, expected_type, memo)
                except TypeCheckError as exc:
                    qualname = qualified_name(obj, add_class_prefix=True)
                    exc.append_path_element(f"value assigned to {varname} ({qualname})")
                    if memo.config.typecheck_fail_callback:
                        memo.config.typecheck_fail_callback(exc, memo)
                    else:
                        raise

    return iterated_values[0] if len(iterated_values) == 1 else iterated_values


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> None:
    """
    Emit a warning on a type mismatch.

    This is intended to be used as an error handler in
    :attr:`TypeCheckConfiguration.typecheck_fail_callback`.

    """
    warnings.warn(TypeCheckWarning(str(exc)), stacklevel=get_stacklevel())

# === NexusCore/evaluation\evalplus\evalplus\perf\sampling.py ===
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from traceback import format_exc
from typing import Any, List, Optional, Tuple

from pympler.asizeof import asizeof
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from termcolor import colored

from evalplus.data import get_human_eval_plus, get_mbpp_plus
from evalplus.data.mbpp import mbpp_serialize_inputs
from evalplus.eval.utils import TimeoutException, reliability_guard, time_limit
from evalplus.perf.config import CURATION_TIMEOUT_PER_TEST_SECOND, MEMORY_LIMIT_GB
from evalplus.sanitize import syntax_check


# this is more of a hack... rather than a "verified" implementation
def insert_contract(entry_point: str, code: str, contract: str):
    # why is this so complicated? because the contract might be mis-indented...
    def get_first_indent_size(source, body_char_start_idx):
        assert source.strip()
        indent_size = 0
        while source[body_char_start_idx - indent_size - 1] == " ":
            indent_size += 1
        return indent_size

    code = code.replace("\t", " " * 4)
    contract = contract.replace("\t", " " * 4)

    lines = [line for line in code.split("\n") if line.strip()]
    fn_def_line = [line for line in lines if line.startswith(f"def {entry_point}")][0]
    def_line_idx = lines.index(fn_def_line)
    body_start_idx = code.index(code.split(fn_def_line)[1].lstrip())

    source_indent: int = get_first_indent_size(code, body_start_idx)
    contract_indent: int = get_first_indent_size(
        contract, len(contract) - len(contract.lstrip())
    )
    return "\n".join(
        lines[: def_line_idx + 1]
        + [
            " " * max(0, source_indent - contract_indent) + cline
            for cline in contract.split("\n")
            if cline
        ]
        + [
            " " * max(0, contract_indent - source_indent) + sline
            for sline in lines[def_line_idx + 1 :]
            if sline
        ]
    )


def post_process(text: str) -> Optional[str]:
    """Post-process the LLM generated text to make it valid."""
    if "\n```" not in text:
        return None

    # split ```python3 or ```python
    text = re.split(r"\n```python3?\n", text)[1]
    text = text.split("\n```")[0].strip()

    # perform syntax check
    if not syntax_check(text):
        print(colored("⚠️ Syntax check failed for the code below:", "red"))
        print(text[:256], "..." if len(text) > 256 else "")
        return None

    return text


# returns:
# 1. generated and validated (by the contract) inputs
# 2. whether the generator stops in a well-defined manner
#    -- if False, we might want to try another generator
def sample_one_input(
    ref_code_with_contract: str,
    entry_point: str,
    generator_code: str,
    timeout_second: float = CURATION_TIMEOUT_PER_TEST_SECOND + 1,
) -> Tuple[List[Any], bool]:
    # These system calls are needed when cleaning up tempdir.
    import os
    import shutil

    rmtree = shutil.rmtree
    rmdir = os.rmdir
    chdir = os.chdir
    # Disable functionalities that can make destructive changes to the test.
    # :imit memory usages.
    maximum_memory_bytes = MEMORY_LIMIT_GB * 1024 * 1024 * 1024
    reliability_guard(maximum_memory_bytes=maximum_memory_bytes)
    exec_globals = {}

    # eval the func def with contract
    exec(ref_code_with_contract, exec_globals)
    fn = exec_globals[entry_point]

    # eval the generator
    generator_code = "from typing import *\n" + generator_code
    try:
        exec(generator_code, exec_globals)
        generator = exec_globals["perf_input_gen"]
    except Exception:
        print(colored(f"⚠️ [GEN EVAL] Exception ~ {entry_point}:", "red"))
        print(colored(format_exc(), "red"))
        return [], False

    well_defined_exit = True
    return_inputs = []

    for fac in range(1, 27):
        scale = 2**fac
        print(f"[INPUT GEN] scale=2**{fac}")
        try:
            with time_limit(timeout_second):
                test_input = generator(scale)
            if not isinstance(test_input, tuple):
                test_input = (test_input,)
            # integers should stay in the range of 64-bit
            if any(
                isinstance(arg, int) and not (-(2**63) <= arg < 2**63)
                for arg in test_input
            ):
                print(colored(f"[INPUT GEN] Int overflow against 64bit", "yellow"))
                break
            # hack list integer
            if isinstance(test_input[0], list) and any(
                not (-(2**63) <= v < 2**63)
                for v in test_input[0]
                if isinstance(v, int)
            ):
                print(colored(f"[INPUT GEN] Int overflow against 64bit", "yellow"))
                break
            # stop here if the input is of 64M.
            INPUT_LIMIT_MB = 64
            if asizeof(test_input) > 1024 * 1024 * INPUT_LIMIT_MB:
                print(colored(f"[INPUT GEN] Size > {INPUT_LIMIT_MB}MB", "yellow"))
                break
        except TimeoutException:
            print(colored(f"[INPUT GEN] TimeoutException at scale=2**{fac}", "yellow"))
            break
        except MemoryError:
            print(colored(f"[INPUT GEN] MemoryError at scale=2**{fac}", "yellow"))
            break
        except Exception:
            print(colored(f"⚠️ [INPUT GEN] Exception at scale=2**{fac}", "red"))
            print(colored(format_exc(), "red"))
            well_defined_exit = False
            break

        try:
            with time_limit(timeout_second):
                # deepcopy in case fn modifies the input
                fn(*deepcopy(test_input))
            return_inputs = [test_input]  # only keep on input
        except TimeoutException:
            print(colored(f"[Testing] Timeout at scale=2**{fac}", "yellow"))
            break
        except MemoryError:
            print(colored(f"[Testing] MemoryError at scale=2**{fac}", "yellow"))
            break
        except Exception:
            print(colored(f"⚠️ [Testing] Exception ~ {entry_point}", "red"))
            print(colored(format_exc(), "red"))
            well_defined_exit = False
            break

    # Needed for cleaning up.
    shutil.rmtree = rmtree
    os.rmdir = rmdir
    os.chdir = chdir

    return return_inputs, well_defined_exit


def main(input: str, output: str):
    """In the synthesizer file, each line includes a set of input generators for a task.
    The goal of this script is to use these generators to sample inputs for each task.
    The generated inputs are expected to be valid.
    """
    assert output.endswith(".jsonl"), "output must be a .jsonl file"

    id2task = {}
    for task_id, item in get_human_eval_plus().items():
        id2task[task_id] = item

    for task_id, item in get_mbpp_plus().items():
        id2task[task_id] = item

    # loading the synthesizers
    with open(input, "r") as f:
        synthesizers = [json.loads(l) for l in f]

    n_total = 0
    n_parsed = 0
    n_dedup = 0

    for item in synthesizers:
        item["synthesizers"] = [post_process(s) for s in item["synthesizers"]]
        n_total += len(item["synthesizers"])
        item["synthesizers"] = [s for s in item["synthesizers"] if s is not None]
        n_parsed += len(item["synthesizers"])

        dedup_set = set()
        for s in item["synthesizers"]:
            dedup_set.add(
                "\n".join(
                    [l for l in s.splitlines() if l.strip() and not l.startswith("#")]
                )
            )
        item["synthesizers"] = list(dedup_set)
        n_dedup += len(item["synthesizers"])

    print(
        colored(
            f"#Total {n_total} with {n_parsed} parsed => {100 * (1 - n_parsed / n_total) :.1f}% syntax err",
            "green",
        )
    )

    print(
        colored(
            f"#Parsed {n_parsed} with {n_dedup} dedup => {100 * (1 - n_dedup / n_parsed) :.1f}% duplicate",
            "green",
        )
    )

    # resume mode check finished tasks
    finished_tasks = set()
    if os.path.isfile(output):
        with open(output, "r") as f:
            for l in f:
                item = json.loads(l)
                finished_tasks.add(item["task_id"])

    print("Resumed finished tasks:", finished_tasks)
    with open(output, "ab+") as f:
        with Progress(
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
        ) as p:
            for item in p.track(synthesizers):
                task_id = item["task_id"]
                entry_point = id2task[task_id]["entry_point"]
                if task_id in finished_tasks:
                    p.console.print(f"{task_id}: {entry_point} ~ Resumed")
                    continue

                ref_code_with_contract = insert_contract(
                    entry_point, item["ref_code"], id2task[task_id]["contract"]
                )
                p.console.print(f"{task_id}: PE input generation...")
                p.console.print(Syntax(ref_code_with_contract.strip(), "python"))

                results = []
                for i, generator_code in enumerate(item["synthesizers"]):
                    p.console.print(
                        f"Using generator {i+1}/{len(item['synthesizers'])}:"
                    )
                    p.console.print(Syntax(generator_code, "python"))
                    args = (
                        ref_code_with_contract,
                        entry_point,
                        generator_code,
                    )
                    with ProcessPoolExecutor(max_workers=1) as executor:
                        tmp_results, status = executor.submit(
                            sample_one_input, *args
                        ).result()

                    results.extend(tmp_results)

                    # if the func returns in a well-defined manner, we can stop here.
                    if status:
                        break

                p.console.print("Serializing and storing results...")

                if "Mbpp/" in task_id:
                    results = mbpp_serialize_inputs(task_id, results)

                to_write = {"task_id": item["task_id"], "inputs": results}
                to_write = (json.dumps(to_write) + "\n").encode("utf-8")

                # task_id => list of inputs
                f.write(to_write)
                f.flush()


if __name__ == "__main__":
    import fire

    fire.Fire(main)

# === NexusCore/openenv\Lib\site-packages\google_auth_httplib2.py ===
# Copyright 2016 Google Inc.
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

"""Transport adapter for httplib2."""

from __future__ import absolute_import

import http.client
import logging

from google.auth import exceptions
from google.auth import transport
import httplib2


_LOGGER = logging.getLogger(__name__)
# Properties present in file-like streams / buffers.
_STREAM_PROPERTIES = ("read", "seek", "tell")


class _Response(transport.Response):
    """httplib2 transport response adapter.

    Args:
        response (httplib2.Response): The raw httplib2 response.
        data (bytes): The response body.
    """

    def __init__(self, response, data):
        self._response = response
        self._data = data

    @property
    def status(self):
        """int: The HTTP status code."""
        return self._response.status

    @property
    def headers(self):
        """Mapping[str, str]: The HTTP response headers."""
        return dict(self._response)

    @property
    def data(self):
        """bytes: The response body."""
        return self._data


class Request(transport.Request):
    """httplib2 request adapter.

    This class is used internally for making requests using various transports
    in a consistent way. If you use :class:`AuthorizedHttp` you do not need
    to construct or use this class directly.

    This class can be useful if you want to manually refresh a
    :class:`~google.auth.credentials.Credentials` instance::

        import google_auth_httplib2
        import httplib2

        http = httplib2.Http()
        request = google_auth_httplib2.Request(http)

        credentials.refresh(request)

    Args:
        http (httplib2.Http): The underlying http object to use to make
            requests.

    .. automethod:: __call__
    """

    def __init__(self, http):
        self.http = http

    def __call__(
        self, url, method="GET", body=None, headers=None, timeout=None, **kwargs
    ):
        """Make an HTTP request using httplib2.

        Args:
            url (str): The URI to be requested.
            method (str): The HTTP method to use for the request. Defaults
                to 'GET'.
            body (bytes): The payload / body in HTTP request.
            headers (Mapping[str, str]): Request headers.
            timeout (Optional[int]): The number of seconds to wait for a
                response from the server. This is ignored by httplib2 and will
                issue a warning.
            kwargs: Additional arguments passed throught to the underlying
                :meth:`httplib2.Http.request` method.

        Returns:
            google.auth.transport.Response: The HTTP response.

        Raises:
            google.auth.exceptions.TransportError: If any exception occurred.
        """
        if timeout is not None:
            _LOGGER.warning(
                "httplib2 transport does not support per-request timeout. "
                "Set the timeout when constructing the httplib2.Http instance."
            )

        try:
            _LOGGER.debug("Making request: %s %s", method, url)
            response, data = self.http.request(
                url, method=method, body=body, headers=headers, **kwargs
            )
            return _Response(response, data)
        # httplib2 should catch the lower http error, this is a bug and
        # needs to be fixed there.  Catch the error for the meanwhile.
        except (httplib2.HttpLib2Error, http.client.HTTPException) as exc:
            raise exceptions.TransportError(exc)


def _make_default_http():
    """Returns a default httplib2.Http instance."""
    return httplib2.Http()


class AuthorizedHttp(object):
    """A httplib2 HTTP class with credentials.

    This class is used to perform requests to API endpoints that require
    authorization::

        from google.auth.transport._httplib2 import AuthorizedHttp

        authed_http = AuthorizedHttp(credentials)

        response = authed_http.request(
            'https://www.googleapis.com/storage/v1/b')

    This class implements :meth:`request` in the same way as
    :class:`httplib2.Http` and can usually be used just like any other
    instance of :class:``httplib2.Http`.

    The underlying :meth:`request` implementation handles adding the
    credentials' headers to the request and refreshing credentials as needed.
    """

    def __init__(
        self,
        credentials,
        http=None,
        refresh_status_codes=transport.DEFAULT_REFRESH_STATUS_CODES,
        max_refresh_attempts=transport.DEFAULT_MAX_REFRESH_ATTEMPTS,
    ):
        """
        Args:
            credentials (google.auth.credentials.Credentials): The credentials
                to add to the request.
            http (httplib2.Http): The underlying HTTP object to
                use to make requests. If not specified, a
                :class:`httplib2.Http` instance will be constructed.
            refresh_status_codes (Sequence[int]): Which HTTP status codes
                indicate that credentials should be refreshed and the request
                should be retried.
            max_refresh_attempts (int): The maximum number of times to attempt
                to refresh the credentials and retry the request.
        """

        if http is None:
            http = _make_default_http()

        self.http = http
        self.credentials = credentials
        self._refresh_status_codes = refresh_status_codes
        self._max_refresh_attempts = max_refresh_attempts
        # Request instance used by internal methods (for example,
        # credentials.refresh).
        self._request = Request(self.http)

    def close(self):
        """Calls httplib2's Http.close"""
        self.http.close()

    def request(
        self,
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type=None,
        **kwargs
    ):
        """Implementation of httplib2's Http.request."""

        _credential_refresh_attempt = kwargs.pop("_credential_refresh_attempt", 0)

        # Make a copy of the headers. They will be modified by the credentials
        # and we want to pass the original headers if we recurse.
        request_headers = headers.copy() if headers is not None else {}

        self.credentials.before_request(self._request, method, uri, request_headers)

        # Check if the body is a file-like stream, and if so, save the body
        # stream position so that it can be restored in case of refresh.
        body_stream_position = None
        if all(getattr(body, stream_prop, None) for stream_prop in _STREAM_PROPERTIES):
            body_stream_position = body.tell()

        # Make the request.
        response, content = self.http.request(
            uri,
            method,
            body=body,
            headers=request_headers,
            redirections=redirections,
            connection_type=connection_type,
            **kwargs
        )

        # If the response indicated that the credentials needed to be
        # refreshed, then refresh the credentials and re-attempt the
        # request.
        # A stored token may expire between the time it is retrieved and
        # the time the request is made, so we may need to try twice.
        if (
            response.status in self._refresh_status_codes
            and _credential_refresh_attempt < self._max_refresh_attempts
        ):

            _LOGGER.info(
                "Refreshing credentials due to a %s response. Attempt %s/%s.",
                response.status,
                _credential_refresh_attempt + 1,
                self._max_refresh_attempts,
            )

            self.credentials.refresh(self._request)

            # Restore the body's stream position if needed.
            if body_stream_position is not None:
                body.seek(body_stream_position)

            # Recurse. Pass in the original headers, not our modified set.
            return self.request(
                uri,
                method,
                body=body,
                headers=headers,
                redirections=redirections,
                connection_type=connection_type,
                _credential_refresh_attempt=_credential_refresh_attempt + 1,
                **kwargs
            )

        return response, content

    def add_certificate(self, key, cert, domain, password=None):
        """Proxy to httplib2.Http.add_certificate."""
        self.http.add_certificate(key, cert, domain, password=password)

    @property
    def connections(self):
        """Proxy to httplib2.Http.connections."""
        return self.http.connections

    @connections.setter
    def connections(self, value):
        """Proxy to httplib2.Http.connections."""
        self.http.connections = value

    @property
    def follow_redirects(self):
        """Proxy to httplib2.Http.follow_redirects."""
        return self.http.follow_redirects

    @follow_redirects.setter
    def follow_redirects(self, value):
        """Proxy to httplib2.Http.follow_redirects."""
        self.http.follow_redirects = value

    @property
    def timeout(self):
        """Proxy to httplib2.Http.timeout."""
        return self.http.timeout

    @timeout.setter
    def timeout(self, value):
        """Proxy to httplib2.Http.timeout."""
        self.http.timeout = value

    @property
    def redirect_codes(self):
        """Proxy to httplib2.Http.redirect_codes."""
        return self.http.redirect_codes

    @redirect_codes.setter
    def redirect_codes(self, value):
        """Proxy to httplib2.Http.redirect_codes."""
        self.http.redirect_codes = value

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta2\services\discuss_service\transports\grpc.py ===
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
from typing import Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import gapic_v1, grpc_helpers
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
import grpc  # type: ignore

from google.ai.generativelanguage_v1beta2.types import discuss_service

from .base import DEFAULT_CLIENT_INFO, DiscussServiceTransport


class DiscussServiceGrpcTransport(DiscussServiceTransport):
    """gRPC backend transport for DiscussService.

    An API for using Generative Language Models (GLMs) in dialog
    applications.
    Also known as large language models (LLMs), this API provides
    models that are trained for multi-turn dialog.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _stubs: Dict[str, Callable]

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]] = None,
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
            scopes (Optional(Sequence[str])): A list of scopes. This argument is
                ignored if a ``channel`` instance is provided.
            channel (Optional[Union[grpc.Channel, Callable[..., grpc.Channel]]]):
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
          google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
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

        if isinstance(channel, grpc.Channel):
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

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> grpc.Channel:
        """Create and return a gRPC channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            grpc.Channel: A gRPC channel object.

        Raises:
            google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """

        return grpc_helpers.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    @property
    def grpc_channel(self) -> grpc.Channel:
        """Return the channel designed to connect to this service."""
        return self._grpc_channel

    @property
    def generate_message(
        self,
    ) -> Callable[
        [discuss_service.GenerateMessageRequest],
        discuss_service.GenerateMessageResponse,
    ]:
        r"""Return a callable for the generate message method over gRPC.

        Generates a response from the model given an input
        ``MessagePrompt``.

        Returns:
            Callable[[~.GenerateMessageRequest],
                    ~.GenerateMessageResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_message" not in self._stubs:
            self._stubs["generate_message"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.DiscussService/GenerateMessage",
                request_serializer=discuss_service.GenerateMessageRequest.serialize,
                response_deserializer=discuss_service.GenerateMessageResponse.deserialize,
            )
        return self._stubs["generate_message"]

    @property
    def count_message_tokens(
        self,
    ) -> Callable[
        [discuss_service.CountMessageTokensRequest],
        discuss_service.CountMessageTokensResponse,
    ]:
        r"""Return a callable for the count message tokens method over gRPC.

        Runs a model's tokenizer on a string and returns the
        token count.

        Returns:
            Callable[[~.CountMessageTokensRequest],
                    ~.CountMessageTokensResponse]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_message_tokens" not in self._stubs:
            self._stubs["count_message_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta2.DiscussService/CountMessageTokens",
                request_serializer=discuss_service.CountMessageTokensRequest.serialize,
                response_deserializer=discuss_service.CountMessageTokensResponse.deserialize,
            )
        return self._stubs["count_message_tokens"]

    def close(self):
        self.grpc_channel.close()

    @property
    def kind(self) -> str:
        return "grpc"


__all__ = ("DiscussServiceGrpcTransport",)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\utils\tqdm.py ===
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
"""Utility helpers to handle progress bars in `huggingface_hub`.

Example:
    1. Use `huggingface_hub.utils.tqdm` as you would use `tqdm.tqdm` or `tqdm.auto.tqdm`.
    2. To disable progress bars, either use `disable_progress_bars()` helper or set the
       environment variable `HF_HUB_DISABLE_PROGRESS_BARS` to 1.
    3. To re-enable progress bars, use `enable_progress_bars()`.
    4. To check whether progress bars are disabled, use `are_progress_bars_disabled()`.

NOTE: Environment variable `HF_HUB_DISABLE_PROGRESS_BARS` has the priority.

Example:
    ```py
    >>> from huggingface_hub.utils import are_progress_bars_disabled, disable_progress_bars, enable_progress_bars, tqdm

    # Disable progress bars globally
    >>> disable_progress_bars()

    # Use as normal `tqdm`
    >>> for _ in tqdm(range(5)):
    ...    pass

    # Still not showing progress bars, as `disable=False` is overwritten to `True`.
    >>> for _ in tqdm(range(5), disable=False):
    ...    pass

    >>> are_progress_bars_disabled()
    True

    # Re-enable progress bars globally
    >>> enable_progress_bars()

    # Progress bar will be shown !
    >>> for _ in tqdm(range(5)):
    ...   pass
    100%|███████████████████████████████████████| 5/5 [00:00<00:00, 117817.53it/s]
    ```

Group-based control:
    ```python
    # Disable progress bars for a specific group
    >>> disable_progress_bars("peft.foo")

    # Check state of different groups
    >>> assert not are_progress_bars_disabled("peft"))
    >>> assert not are_progress_bars_disabled("peft.something")
    >>> assert are_progress_bars_disabled("peft.foo"))
    >>> assert are_progress_bars_disabled("peft.foo.bar"))

    # Enable progress bars for a subgroup
    >>> enable_progress_bars("peft.foo.bar")

    # Check if enabling a subgroup affects the parent group
    >>> assert are_progress_bars_disabled("peft.foo"))
    >>> assert not are_progress_bars_disabled("peft.foo.bar"))

    # No progress bar for `name="peft.foo"`
    >>> for _ in tqdm(range(5), name="peft.foo"):
    ...     pass

    # Progress bar will be shown for `name="peft.foo.bar"`
    >>> for _ in tqdm(range(5), name="peft.foo.bar"):
    ...     pass
    100%|███████████████████████████████████████| 5/5 [00:00<00:00, 117817.53it/s]

    ```
"""

import io
import logging
import os
import warnings
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import ContextManager, Dict, Iterator, Optional, Union

from tqdm.auto import tqdm as old_tqdm

from ..constants import HF_HUB_DISABLE_PROGRESS_BARS


# The `HF_HUB_DISABLE_PROGRESS_BARS` environment variable can be True, False, or not set (None),
# allowing for control over progress bar visibility. When set, this variable takes precedence
# over programmatic settings, dictating whether progress bars should be shown or hidden globally.
# Essentially, the environment variable's setting overrides any code-based configurations.
#
# If `HF_HUB_DISABLE_PROGRESS_BARS` is not defined (None), it implies that users can manage
# progress bar visibility through code. By default, progress bars are turned on.


progress_bar_states: Dict[str, bool] = {}


def disable_progress_bars(name: Optional[str] = None) -> None:
    """
    Disable progress bars either globally or for a specified group.

    This function updates the state of progress bars based on a group name.
    If no group name is provided, all progress bars are disabled. The operation
    respects the `HF_HUB_DISABLE_PROGRESS_BARS` environment variable's setting.

    Args:
        name (`str`, *optional*):
            The name of the group for which to disable the progress bars. If None,
            progress bars are disabled globally.

    Raises:
        Warning: If the environment variable precludes changes.
    """
    if HF_HUB_DISABLE_PROGRESS_BARS is False:
        warnings.warn(
            "Cannot disable progress bars: environment variable `HF_HUB_DISABLE_PROGRESS_BARS=0` is set and has priority."
        )
        return

    if name is None:
        progress_bar_states.clear()
        progress_bar_states["_global"] = False
    else:
        keys_to_remove = [key for key in progress_bar_states if key.startswith(f"{name}.")]
        for key in keys_to_remove:
            del progress_bar_states[key]
        progress_bar_states[name] = False


def enable_progress_bars(name: Optional[str] = None) -> None:
    """
    Enable progress bars either globally or for a specified group.

    This function sets the progress bars to enabled for the specified group or globally
    if no group is specified. The operation is subject to the `HF_HUB_DISABLE_PROGRESS_BARS`
    environment setting.

    Args:
        name (`str`, *optional*):
            The name of the group for which to enable the progress bars. If None,
            progress bars are enabled globally.

    Raises:
        Warning: If the environment variable precludes changes.
    """
    if HF_HUB_DISABLE_PROGRESS_BARS is True:
        warnings.warn(
            "Cannot enable progress bars: environment variable `HF_HUB_DISABLE_PROGRESS_BARS=1` is set and has priority."
        )
        return

    if name is None:
        progress_bar_states.clear()
        progress_bar_states["_global"] = True
    else:
        keys_to_remove = [key for key in progress_bar_states if key.startswith(f"{name}.")]
        for key in keys_to_remove:
            del progress_bar_states[key]
        progress_bar_states[name] = True


def are_progress_bars_disabled(name: Optional[str] = None) -> bool:
    """
    Check if progress bars are disabled globally or for a specific group.

    This function returns whether progress bars are disabled for a given group or globally.
    It checks the `HF_HUB_DISABLE_PROGRESS_BARS` environment variable first, then the programmatic
    settings.

    Args:
        name (`str`, *optional*):
            The group name to check; if None, checks the global setting.

    Returns:
        `bool`: True if progress bars are disabled, False otherwise.
    """
    if HF_HUB_DISABLE_PROGRESS_BARS is True:
        return True

    if name is None:
        return not progress_bar_states.get("_global", True)

    while name:
        if name in progress_bar_states:
            return not progress_bar_states[name]
        name = ".".join(name.split(".")[:-1])

    return not progress_bar_states.get("_global", True)


def is_tqdm_disabled(log_level: int) -> Optional[bool]:
    """
    Determine if tqdm progress bars should be disabled based on logging level and environment settings.

    see https://github.com/huggingface/huggingface_hub/pull/2000 and https://github.com/huggingface/huggingface_hub/pull/2698.
    """
    if log_level == logging.NOTSET:
        return True
    if os.getenv("TQDM_POSITION") == "-1":
        return False
    return None


class tqdm(old_tqdm):
    """
    Class to override `disable` argument in case progress bars are globally disabled.

    Taken from https://github.com/tqdm/tqdm/issues/619#issuecomment-619639324.
    """

    def __init__(self, *args, **kwargs):
        name = kwargs.pop("name", None)  # do not pass `name` to `tqdm`
        if are_progress_bars_disabled(name):
            kwargs["disable"] = True
        super().__init__(*args, **kwargs)

    def __delattr__(self, attr: str) -> None:
        """Fix for https://github.com/huggingface/huggingface_hub/issues/1603"""
        try:
            super().__delattr__(attr)
        except AttributeError:
            if attr != "_lock":
                raise


@contextmanager
def tqdm_stream_file(path: Union[Path, str]) -> Iterator[io.BufferedReader]:
    """
    Open a file as binary and wrap the `read` method to display a progress bar when it's streamed.

    First implemented in `transformers` in 2019 but removed when switched to git-lfs. Used in `huggingface_hub` to show
    progress bar when uploading an LFS file to the Hub. See github.com/huggingface/transformers/pull/2078#discussion_r354739608
    for implementation details.

    Note: currently implementation handles only files stored on disk as it is the most common use case. Could be
          extended to stream any `BinaryIO` object but we might have to debug some corner cases.

    Example:
    ```py
    >>> with tqdm_stream_file("config.json") as f:
    >>>     requests.put(url, data=f)
    config.json: 100%|█████████████████████████| 8.19k/8.19k [00:02<00:00, 3.72kB/s]
    ```
    """
    if isinstance(path, str):
        path = Path(path)

    with path.open("rb") as f:
        total_size = path.stat().st_size
        pbar = tqdm(
            unit="B",
            unit_scale=True,
            total=total_size,
            initial=0,
            desc=path.name,
        )

        f_read = f.read

        def _inner_read(size: Optional[int] = -1) -> bytes:
            data = f_read(size)
            pbar.update(len(data))
            return data

        f.read = _inner_read  # type: ignore

        yield f

        pbar.close()


def _get_progress_bar_context(
    *,
    desc: str,
    log_level: int,
    total: Optional[int] = None,
    initial: int = 0,
    unit: str = "B",
    unit_scale: bool = True,
    name: Optional[str] = None,
    _tqdm_bar: Optional[tqdm] = None,
) -> ContextManager[tqdm]:
    if _tqdm_bar is not None:
        return nullcontext(_tqdm_bar)
        # ^ `contextlib.nullcontext` mimics a context manager that does nothing
        #   Makes it easier to use the same code path for both cases but in the later
        #   case, the progress bar is not closed when exiting the context manager.

    return tqdm(
        unit=unit,
        unit_scale=unit_scale,
        total=total,
        initial=initial,
        desc=desc,
        disable=is_tqdm_disabled(log_level=log_level),
        name=name,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\deprecated_providers\aleph_alpha.py ===
import json
import time
import types
from typing import Callable, Optional

import httpx  # type: ignore

import litellm
from litellm.utils import Choices, Message, ModelResponse, Usage


class AlephAlphaError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(
            method="POST", url="https://api.aleph-alpha.com/complete"
        )
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


class AlephAlphaConfig:
    """
    Reference: https://docs.aleph-alpha.com/api/complete/

    The `AlephAlphaConfig` class represents the configuration for the Aleph Alpha API. Here are the properties:

    - `maximum_tokens` (integer, required): The maximum number of tokens to be generated by the completion. The sum of input tokens and maximum tokens may not exceed 2048.

    - `minimum_tokens` (integer, optional; default value: 0): Generate at least this number of tokens before an end-of-text token is generated.

    - `echo` (boolean, optional; default value: false): Whether to echo the prompt in the completion.

    - `temperature` (number, nullable; default value: 0): Adjusts how creatively the model generates outputs. Use combinations of temperature, top_k, and top_p sensibly.

    - `top_k` (integer, nullable; default value: 0): Introduces randomness into token generation by considering the top k most likely options.

    - `top_p` (number, nullable; default value: 0): Adds randomness by considering the smallest set of tokens whose cumulative probability exceeds top_p.

    - `presence_penalty`, `frequency_penalty`, `sequence_penalty` (number, nullable; default value: 0): Various penalties that can reduce repetition.

    - `sequence_penalty_min_length` (integer; default value: 2): Minimum number of tokens to be considered as a sequence.

    - `repetition_penalties_include_prompt`, `repetition_penalties_include_completion`, `use_multiplicative_presence_penalty`,`use_multiplicative_frequency_penalty`,`use_multiplicative_sequence_penalty` (boolean, nullable; default value: false): Various settings that adjust how the repetition penalties are applied.

    - `penalty_bias` (string, nullable): Text used in addition to the penalized tokens for repetition penalties.

    - `penalty_exceptions` (string[], nullable): Strings that may be generated without penalty.

    - `penalty_exceptions_include_stop_sequences` (boolean, nullable; default value: true): Include all stop_sequences in penalty_exceptions.

    - `best_of` (integer, nullable; default value: 1): The number of completions will be generated on the server side.

    - `n` (integer, nullable; default value: 1): The number of completions to return.

    - `logit_bias` (object, nullable): Adjust the logit scores before sampling.

    - `log_probs` (integer, nullable): Number of top log probabilities for each token generated.

    - `stop_sequences` (string[], nullable): List of strings that will stop generation if they're generated.

    - `tokens` (boolean, nullable; default value: false): Flag indicating whether individual tokens of the completion should be returned or not.

    - `raw_completion` (boolean; default value: false): if True, the raw completion of the model will be returned.

    - `disable_optimizations` (boolean, nullable; default value: false): Disables any applied optimizations to both your prompt and completion.

    - `completion_bias_inclusion`, `completion_bias_exclusion` (string[], default value: []): Set of strings to bias the generation of tokens.

    - `completion_bias_inclusion_first_token_only`, `completion_bias_exclusion_first_token_only` (boolean; default value: false): Consider only the first token for the completion_bias_inclusion/exclusion.

    - `contextual_control_threshold` (number, nullable): Control over how similar tokens are controlled.

    - `control_log_additive` (boolean; default value: true): Method of applying control to attention scores.
    """

    maximum_tokens: Optional[
        int
    ] = litellm.max_tokens  # aleph alpha requires max tokens
    minimum_tokens: Optional[int] = None
    echo: Optional[bool] = None
    temperature: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[int] = None
    presence_penalty: Optional[int] = None
    frequency_penalty: Optional[int] = None
    sequence_penalty: Optional[int] = None
    sequence_penalty_min_length: Optional[int] = None
    repetition_penalties_include_prompt: Optional[bool] = None
    repetition_penalties_include_completion: Optional[bool] = None
    use_multiplicative_presence_penalty: Optional[bool] = None
    use_multiplicative_frequency_penalty: Optional[bool] = None
    use_multiplicative_sequence_penalty: Optional[bool] = None
    penalty_bias: Optional[str] = None
    penalty_exceptions_include_stop_sequences: Optional[bool] = None
    best_of: Optional[int] = None
    n: Optional[int] = None
    logit_bias: Optional[dict] = None
    log_probs: Optional[int] = None
    stop_sequences: Optional[list] = None
    tokens: Optional[bool] = None
    raw_completion: Optional[bool] = None
    disable_optimizations: Optional[bool] = None
    completion_bias_inclusion: Optional[list] = None
    completion_bias_exclusion: Optional[list] = None
    completion_bias_inclusion_first_token_only: Optional[bool] = None
    completion_bias_exclusion_first_token_only: Optional[bool] = None
    contextual_control_threshold: Optional[int] = None
    control_log_additive: Optional[bool] = None

    def __init__(
        self,
        maximum_tokens: Optional[int] = None,
        minimum_tokens: Optional[int] = None,
        echo: Optional[bool] = None,
        temperature: Optional[int] = None,
        top_k: Optional[int] = None,
        top_p: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        sequence_penalty: Optional[int] = None,
        sequence_penalty_min_length: Optional[int] = None,
        repetition_penalties_include_prompt: Optional[bool] = None,
        repetition_penalties_include_completion: Optional[bool] = None,
        use_multiplicative_presence_penalty: Optional[bool] = None,
        use_multiplicative_frequency_penalty: Optional[bool] = None,
        use_multiplicative_sequence_penalty: Optional[bool] = None,
        penalty_bias: Optional[str] = None,
        penalty_exceptions_include_stop_sequences: Optional[bool] = None,
        best_of: Optional[int] = None,
        n: Optional[int] = None,
        logit_bias: Optional[dict] = None,
        log_probs: Optional[int] = None,
        stop_sequences: Optional[list] = None,
        tokens: Optional[bool] = None,
        raw_completion: Optional[bool] = None,
        disable_optimizations: Optional[bool] = None,
        completion_bias_inclusion: Optional[list] = None,
        completion_bias_exclusion: Optional[list] = None,
        completion_bias_inclusion_first_token_only: Optional[bool] = None,
        completion_bias_exclusion_first_token_only: Optional[bool] = None,
        contextual_control_threshold: Optional[int] = None,
        control_log_additive: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                ),
            )
            and v is not None
        }


def validate_environment(api_key):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def completion(
    model: str,
    messages: list,
    api_base: str,
    model_response: ModelResponse,
    print_verbose: Callable,
    encoding,
    api_key,
    logging_obj,
    optional_params: dict,
    litellm_params=None,
    logger_fn=None,
    default_max_tokens_to_sample=None,
):
    headers = validate_environment(api_key)

    ## Load Config
    config = litellm.AlephAlphaConfig.get_config()
    for k, v in config.items():
        if (
            k not in optional_params
        ):  # completion(top_k=3) > aleph_alpha_config(top_k=3) <- allows for dynamic variables to be passed in
            optional_params[k] = v

    completion_url = api_base
    model = model
    prompt = ""
    if "control" in model:  # follow the ###Instruction / ###Response format
        for idx, message in enumerate(messages):
            if "role" in message:
                if (
                    idx == 0
                ):  # set first message as instruction (required), let later user messages be input
                    prompt += f"###Instruction: {message['content']}"
                else:
                    if message["role"] == "system":
                        prompt += f"###Instruction: {message['content']}"
                    elif message["role"] == "user":
                        prompt += f"###Input: {message['content']}"
                    else:
                        prompt += f"###Response: {message['content']}"
            else:
                prompt += f"{message['content']}"
    else:
        prompt = " ".join(message["content"] for message in messages)
    data = {
        "model": model,
        "prompt": prompt,
        **optional_params,
    }

    ## LOGGING
    logging_obj.pre_call(
        input=prompt,
        api_key=api_key,
        additional_args={"complete_input_dict": data},
    )
    ## COMPLETION CALL
    response = litellm.module_level_client.post(
        completion_url,
        headers=headers,
        data=json.dumps(data),
        stream=optional_params["stream"] if "stream" in optional_params else False,
    )
    if "stream" in optional_params and optional_params["stream"] is True:
        return response.iter_lines()
    else:
        ## LOGGING
        logging_obj.post_call(
            input=prompt,
            api_key=api_key,
            original_response=response.text,
            additional_args={"complete_input_dict": data},
        )
        print_verbose(f"raw model_response: {response.text}")
        ## RESPONSE OBJECT
        completion_response = response.json()
        if "error" in completion_response:
            raise AlephAlphaError(
                message=completion_response["error"],
                status_code=response.status_code,
            )
        else:
            try:
                choices_list = []
                for idx, item in enumerate(completion_response["completions"]):
                    if len(item["completion"]) > 0:
                        message_obj = Message(content=item["completion"])
                    else:
                        message_obj = Message(content=None)
                    choice_obj = Choices(
                        finish_reason=item["finish_reason"],
                        index=idx + 1,
                        message=message_obj,
                    )
                    choices_list.append(choice_obj)
                model_response.choices = choices_list  # type: ignore
            except Exception:
                raise AlephAlphaError(
                    message=json.dumps(completion_response),
                    status_code=response.status_code,
                )

        ## CALCULATING USAGE - baseten charges on time, not tokens - have some mapping of cost here.
        prompt_tokens = len(encoding.encode(prompt))
        completion_tokens = len(
            encoding.encode(
                model_response["choices"][0]["message"]["content"],
                disallowed_special=(),
            )
        )

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response


def embedding():
    # logic for parsing in - calling - parsing out model embedding calls
    pass

# === NexusCore/openenv\Lib\site-packages\litellm\llms\replicate\chat\handler.py ===
import asyncio
import json
import time
from typing import Callable, List, Union

import litellm
from litellm.constants import REPLICATE_POLLING_DELAY_SECONDS
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.types.llms.openai import AllMessageValues
from litellm.utils import CustomStreamWrapper, ModelResponse

from ..common_utils import ReplicateError
from .transformation import ReplicateConfig

replicate_config = ReplicateConfig()


# Function to handle prediction response (streaming)
def handle_prediction_response_streaming(
    prediction_url, api_token, print_verbose, headers: dict, http_client: HTTPHandler
):
    previous_output = ""
    output_string = ""

    status = ""
    while True and (status not in ["succeeded", "failed", "canceled"]):
        time.sleep(
            REPLICATE_POLLING_DELAY_SECONDS
        )  # prevent being rate limited by replicate
        print_verbose(f"replicate: polling endpoint: {prediction_url}")
        response = http_client.get(prediction_url, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            status = response_data["status"]
            if "output" in response_data:
                try:
                    output_string = "".join(response_data["output"])
                except Exception:
                    raise ReplicateError(
                        status_code=422,
                        message="Unable to parse response. Got={}".format(
                            response_data["output"]
                        ),
                        headers=response.headers,
                    )
                new_output = output_string[len(previous_output) :]
                print_verbose(f"New chunk: {new_output}")
                yield {"output": new_output, "status": status}
                previous_output = output_string
            status = response_data["status"]
            if status == "failed":
                replicate_error = response_data.get("error", "")
                raise ReplicateError(
                    status_code=400,
                    message=f"Error: {replicate_error}",
                    headers=response.headers,
                )
        else:
            # this can fail temporarily but it does not mean the replicate request failed, replicate request fails when status=="failed"
            print_verbose(
                f"Replicate: Failed to fetch prediction status and output.{response.status_code}{response.text}"
            )


# Function to handle prediction response (streaming)
async def async_handle_prediction_response_streaming(
    prediction_url,
    api_token,
    print_verbose,
    headers: dict,
    http_client: AsyncHTTPHandler,
):
    previous_output = ""
    output_string = ""

    status = ""
    while True and (status not in ["succeeded", "failed", "canceled"]):
        await asyncio.sleep(
            REPLICATE_POLLING_DELAY_SECONDS
        )  # prevent being rate limited by replicate
        print_verbose(f"replicate: polling endpoint: {prediction_url}")
        response = await http_client.get(prediction_url, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            status = response_data["status"]
            if "output" in response_data:
                try:
                    output_string = "".join(response_data["output"])
                except Exception:
                    raise ReplicateError(
                        status_code=422,
                        message="Unable to parse response. Got={}".format(
                            response_data["output"]
                        ),
                        headers=response.headers,
                    )
                new_output = output_string[len(previous_output) :]
                print_verbose(f"New chunk: {new_output}")
                yield {"output": new_output, "status": status}
                previous_output = output_string
            status = response_data["status"]
            if status == "failed":
                replicate_error = response_data.get("error", "")
                raise ReplicateError(
                    status_code=400,
                    message=f"Error: {replicate_error}",
                    headers=response.headers,
                )
        else:
            # this can fail temporarily but it does not mean the replicate request failed, replicate request fails when status=="failed"
            print_verbose(
                f"Replicate: Failed to fetch prediction status and output.{response.status_code}{response.text}"
            )


# Main function for prediction completion
def completion(
    model: str,
    messages: list,
    api_base: str,
    model_response: ModelResponse,
    print_verbose: Callable,
    optional_params: dict,
    litellm_params: dict,
    logging_obj,
    api_key,
    encoding,
    custom_prompt_dict={},
    logger_fn=None,
    acompletion=None,
    headers={},
) -> Union[ModelResponse, CustomStreamWrapper]:
    headers = replicate_config.validate_environment(
        api_key=api_key,
        headers=headers,
        model=model,
        messages=messages,
        optional_params=optional_params,
        litellm_params=litellm_params,
    )
    # Start a prediction and get the prediction URL
    version_id = replicate_config.model_to_version_id(model)
    input_data = replicate_config.transform_request(
        model=model,
        messages=messages,
        optional_params=optional_params,
        litellm_params=litellm_params,
        headers=headers,
    )

    if acompletion is not None and acompletion is True:
        return async_completion(
            model_response=model_response,
            model=model,
            encoding=encoding,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            version_id=version_id,
            input_data=input_data,
            api_key=api_key,
            api_base=api_base,
            logging_obj=logging_obj,
            print_verbose=print_verbose,
            headers=headers,
        )  # type: ignore
    ## COMPLETION CALL
    model_response.created = int(
        time.time()
    )  # for pricing this must remain right before calling api

    prediction_url = replicate_config.get_complete_url(
        api_base=api_base,
        api_key=api_key,
        model=model,
        optional_params=optional_params,
        litellm_params=litellm_params,
    )

    ## COMPLETION CALL
    httpx_client = _get_httpx_client(
        params={"timeout": 600.0},
    )
    response = httpx_client.post(
        url=prediction_url,
        headers=headers,
        data=json.dumps(input_data),
    )

    prediction_url = replicate_config.get_prediction_url(response)

    # Handle the prediction response (streaming or non-streaming)
    if "stream" in optional_params and optional_params["stream"] is True:
        print_verbose("streaming request")
        _response = handle_prediction_response_streaming(
            prediction_url,
            api_key,
            print_verbose,
            headers=headers,
            http_client=httpx_client,
        )
        return CustomStreamWrapper(_response, model, logging_obj=logging_obj, custom_llm_provider="replicate")  # type: ignore
    else:
        for retry in range(litellm.DEFAULT_REPLICATE_POLLING_RETRIES):
            time.sleep(
                litellm.DEFAULT_REPLICATE_POLLING_DELAY_SECONDS + 2 * retry
            )  # wait to allow response to be generated by replicate - else partial output is generated with status=="processing"
            response = httpx_client.get(url=prediction_url, headers=headers)
            if (
                response.status_code == 200
                and response.json().get("status") == "processing"
            ):
                continue
            return litellm.ReplicateConfig().transform_response(
                model=model,
                raw_response=response,
                model_response=model_response,
                logging_obj=logging_obj,
                api_key=api_key,
                request_data=input_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=encoding,
            )

    raise ReplicateError(
        status_code=500,
        message="No response received from Replicate API after max retries",
        headers=None,
    )


async def async_completion(
    model_response: ModelResponse,
    model: str,
    messages: List[AllMessageValues],
    encoding,
    optional_params: dict,
    litellm_params: dict,
    version_id,
    input_data,
    api_key,
    api_base,
    logging_obj,
    print_verbose,
    headers: dict,
) -> Union[ModelResponse, CustomStreamWrapper]:
    prediction_url = replicate_config.get_complete_url(
        api_base=api_base,
        api_key=api_key,
        model=model,
        optional_params=optional_params,
        litellm_params=litellm_params,
    )
    async_handler = get_async_httpx_client(
        llm_provider=litellm.LlmProviders.REPLICATE,
        params={"timeout": 600.0},
    )
    response = await async_handler.post(
        url=prediction_url, headers=headers, data=json.dumps(input_data)
    )
    prediction_url = replicate_config.get_prediction_url(response)

    if "stream" in optional_params and optional_params["stream"] is True:
        _response = async_handle_prediction_response_streaming(
            prediction_url,
            api_key,
            print_verbose,
            headers=headers,
            http_client=async_handler,
        )
        return CustomStreamWrapper(_response, model, logging_obj=logging_obj, custom_llm_provider="replicate")  # type: ignore

    for retry in range(litellm.DEFAULT_REPLICATE_POLLING_RETRIES):
        await asyncio.sleep(
            litellm.DEFAULT_REPLICATE_POLLING_DELAY_SECONDS + 2 * retry
        )  # wait to allow response to be generated by replicate - else partial output is generated with status=="processing"
        response = await async_handler.get(url=prediction_url, headers=headers)
        if (
            response.status_code == 200
            and response.json().get("status") == "processing"
        ):
            continue
        return litellm.ReplicateConfig().transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=input_data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
        )
    # Add a fallback return if no response is received after max retries
    raise ReplicateError(
        status_code=500,
        message="No response received from Replicate API after max retries",
        headers=None,
    )

# === NexusCore/openenv\Lib\site-packages\matplotlib\tri\_trirefine.py ===
"""
Mesh refinement for triangular grids.
"""

import numpy as np

from matplotlib import _api
from matplotlib.tri._triangulation import Triangulation
import matplotlib.tri._triinterpolate


class TriRefiner:
    """
    Abstract base class for classes implementing mesh refinement.

    A TriRefiner encapsulates a Triangulation object and provides tools for
    mesh refinement and interpolation.

    Derived classes must implement:

    - ``refine_triangulation(return_tri_index=False, **kwargs)`` , where
      the optional keyword arguments *kwargs* are defined in each
      TriRefiner concrete implementation, and which returns:

      - a refined triangulation,
      - optionally (depending on *return_tri_index*), for each
        point of the refined triangulation: the index of
        the initial triangulation triangle to which it belongs.

    - ``refine_field(z, triinterpolator=None, **kwargs)``, where:

      - *z* array of field values (to refine) defined at the base
        triangulation nodes,
      - *triinterpolator* is an optional `~matplotlib.tri.TriInterpolator`,
      - the other optional keyword arguments *kwargs* are defined in
        each TriRefiner concrete implementation;

      and which returns (as a tuple) a refined triangular mesh and the
      interpolated values of the field at the refined triangulation nodes.
    """

    def __init__(self, triangulation):
        _api.check_isinstance(Triangulation, triangulation=triangulation)
        self._triangulation = triangulation


class UniformTriRefiner(TriRefiner):
    """
    Uniform mesh refinement by recursive subdivisions.

    Parameters
    ----------
    triangulation : `~matplotlib.tri.Triangulation`
        The encapsulated triangulation (to be refined)
    """
#    See Also
#    --------
#    :class:`~matplotlib.tri.CubicTriInterpolator` and
#    :class:`~matplotlib.tri.TriAnalyzer`.
#    """
    def __init__(self, triangulation):
        super().__init__(triangulation)

    def refine_triangulation(self, return_tri_index=False, subdiv=3):
        """
        Compute a uniformly refined triangulation *refi_triangulation* of
        the encapsulated :attr:`triangulation`.

        This function refines the encapsulated triangulation by splitting each
        father triangle into 4 child sub-triangles built on the edges midside
        nodes, recursing *subdiv* times.  In the end, each triangle is hence
        divided into ``4**subdiv`` child triangles.

        Parameters
        ----------
        return_tri_index : bool, default: False
            Whether an index table indicating the father triangle index of each
            point is returned.
        subdiv : int, default: 3
            Recursion level for the subdivision.
            Each triangle is divided into ``4**subdiv`` child triangles;
            hence, the default results in 64 refined subtriangles for each
            triangle of the initial triangulation.

        Returns
        -------
        refi_triangulation : `~matplotlib.tri.Triangulation`
            The refined triangulation.
        found_index : int array
            Index of the initial triangulation containing triangle, for each
            point of *refi_triangulation*.
            Returned only if *return_tri_index* is set to True.
        """
        refi_triangulation = self._triangulation
        ntri = refi_triangulation.triangles.shape[0]

        # Computes the triangulation ancestors numbers in the reference
        # triangulation.
        ancestors = np.arange(ntri, dtype=np.int32)
        for _ in range(subdiv):
            refi_triangulation, ancestors = self._refine_triangulation_once(
                refi_triangulation, ancestors)
        refi_npts = refi_triangulation.x.shape[0]
        refi_triangles = refi_triangulation.triangles

        # Now we compute found_index table if needed
        if return_tri_index:
            # We have to initialize found_index with -1 because some nodes
            # may very well belong to no triangle at all, e.g., in case of
            # Delaunay Triangulation with DuplicatePointWarning.
            found_index = np.full(refi_npts, -1, dtype=np.int32)
            tri_mask = self._triangulation.mask
            if tri_mask is None:
                found_index[refi_triangles] = np.repeat(ancestors,
                                                        3).reshape(-1, 3)
            else:
                # There is a subtlety here: we want to avoid whenever possible
                # that refined points container is a masked triangle (which
                # would result in artifacts in plots).
                # So we impose the numbering from masked ancestors first,
                # then overwrite it with unmasked ancestor numbers.
                ancestor_mask = tri_mask[ancestors]
                found_index[refi_triangles[ancestor_mask, :]
                            ] = np.repeat(ancestors[ancestor_mask],
                                          3).reshape(-1, 3)
                found_index[refi_triangles[~ancestor_mask, :]
                            ] = np.repeat(ancestors[~ancestor_mask],
                                          3).reshape(-1, 3)
            return refi_triangulation, found_index
        else:
            return refi_triangulation

    def refine_field(self, z, triinterpolator=None, subdiv=3):
        """
        Refine a field defined on the encapsulated triangulation.

        Parameters
        ----------
        z : (npoints,) array-like
            Values of the field to refine, defined at the nodes of the
            encapsulated triangulation. (``n_points`` is the number of points
            in the initial triangulation)
        triinterpolator : `~matplotlib.tri.TriInterpolator`, optional
            Interpolator used for field interpolation. If not specified,
            a `~matplotlib.tri.CubicTriInterpolator` will be used.
        subdiv : int, default: 3
            Recursion level for the subdivision.
            Each triangle is divided into ``4**subdiv`` child triangles.

        Returns
        -------
        refi_tri : `~matplotlib.tri.Triangulation`
             The returned refined triangulation.
        refi_z : 1D array of length: *refi_tri* node count.
             The returned interpolated field (at *refi_tri* nodes).
        """
        if triinterpolator is None:
            interp = matplotlib.tri.CubicTriInterpolator(
                self._triangulation, z)
        else:
            _api.check_isinstance(matplotlib.tri.TriInterpolator,
                                  triinterpolator=triinterpolator)
            interp = triinterpolator

        refi_tri, found_index = self.refine_triangulation(
            subdiv=subdiv, return_tri_index=True)
        refi_z = interp._interpolate_multikeys(
            refi_tri.x, refi_tri.y, tri_index=found_index)[0]
        return refi_tri, refi_z

    @staticmethod
    def _refine_triangulation_once(triangulation, ancestors=None):
        """
        Refine a `.Triangulation` by splitting each triangle into 4
        child-masked_triangles built on the edges midside nodes.

        Masked triangles, if present, are also split, but their children
        returned masked.

        If *ancestors* is not provided, returns only a new triangulation:
        child_triangulation.

        If the array-like key table *ancestor* is given, it shall be of shape
        (ntri,) where ntri is the number of *triangulation* masked_triangles.
        In this case, the function returns
        (child_triangulation, child_ancestors)
        child_ancestors is defined so that the 4 child masked_triangles share
        the same index as their father: child_ancestors.shape = (4 * ntri,).
        """

        x = triangulation.x
        y = triangulation.y

        #    According to tri.triangulation doc:
        #         neighbors[i, j] is the triangle that is the neighbor
        #         to the edge from point index masked_triangles[i, j] to point
        #         index masked_triangles[i, (j+1)%3].
        neighbors = triangulation.neighbors
        triangles = triangulation.triangles
        npts = np.shape(x)[0]
        ntri = np.shape(triangles)[0]
        if ancestors is not None:
            ancestors = np.asarray(ancestors)
            if np.shape(ancestors) != (ntri,):
                raise ValueError(
                    "Incompatible shapes provide for "
                    "triangulation.masked_triangles and ancestors: "
                    f"{np.shape(triangles)} and {np.shape(ancestors)}")

        # Initiating tables refi_x and refi_y of the refined triangulation
        # points
        # hint: each apex is shared by 2 masked_triangles except the borders.
        borders = np.sum(neighbors == -1)
        added_pts = (3*ntri + borders) // 2
        refi_npts = npts + added_pts
        refi_x = np.zeros(refi_npts)
        refi_y = np.zeros(refi_npts)

        # First part of refi_x, refi_y is just the initial points
        refi_x[:npts] = x
        refi_y[:npts] = y

        # Second part contains the edge midside nodes.
        # Each edge belongs to 1 triangle (if border edge) or is shared by 2
        # masked_triangles (interior edge).
        # We first build 2 * ntri arrays of edge starting nodes (edge_elems,
        # edge_apexes); we then extract only the masters to avoid overlaps.
        # The so-called 'master' is the triangle with biggest index
        # The 'slave' is the triangle with lower index
        # (can be -1 if border edge)
        # For slave and master we will identify the apex pointing to the edge
        # start
        edge_elems = np.tile(np.arange(ntri, dtype=np.int32), 3)
        edge_apexes = np.repeat(np.arange(3, dtype=np.int32), ntri)
        edge_neighbors = neighbors[edge_elems, edge_apexes]
        mask_masters = (edge_elems > edge_neighbors)

        # Identifying the "masters" and adding to refi_x, refi_y vec
        masters = edge_elems[mask_masters]
        apex_masters = edge_apexes[mask_masters]
        x_add = (x[triangles[masters, apex_masters]] +
                 x[triangles[masters, (apex_masters+1) % 3]]) * 0.5
        y_add = (y[triangles[masters, apex_masters]] +
                 y[triangles[masters, (apex_masters+1) % 3]]) * 0.5
        refi_x[npts:] = x_add
        refi_y[npts:] = y_add

        # Building the new masked_triangles; each old masked_triangles hosts
        # 4 new masked_triangles
        # there are 6 pts to identify per 'old' triangle, 3 new_pt_corner and
        # 3 new_pt_midside
        new_pt_corner = triangles

        # What is the index in refi_x, refi_y of point at middle of apex iapex
        #  of elem ielem ?
        # If ielem is the apex master: simple count, given the way refi_x was
        #  built.
        # If ielem is the apex slave: yet we do not know; but we will soon
        # using the neighbors table.
        new_pt_midside = np.empty([ntri, 3], dtype=np.int32)
        cum_sum = npts
        for imid in range(3):
            mask_st_loc = (imid == apex_masters)
            n_masters_loc = np.sum(mask_st_loc)
            elem_masters_loc = masters[mask_st_loc]
            new_pt_midside[:, imid][elem_masters_loc] = np.arange(
                n_masters_loc, dtype=np.int32) + cum_sum
            cum_sum += n_masters_loc

        # Now dealing with slave elems.
        # for each slave element we identify the master and then the inode
        # once slave_masters is identified, slave_masters_apex is such that:
        # neighbors[slaves_masters, slave_masters_apex] == slaves
        mask_slaves = np.logical_not(mask_masters)
        slaves = edge_elems[mask_slaves]
        slaves_masters = edge_neighbors[mask_slaves]
        diff_table = np.abs(neighbors[slaves_masters, :] -
                            np.outer(slaves, np.ones(3, dtype=np.int32)))
        slave_masters_apex = np.argmin(diff_table, axis=1)
        slaves_apex = edge_apexes[mask_slaves]
        new_pt_midside[slaves, slaves_apex] = new_pt_midside[
            slaves_masters, slave_masters_apex]

        # Builds the 4 child masked_triangles
        child_triangles = np.empty([ntri*4, 3], dtype=np.int32)
        child_triangles[0::4, :] = np.vstack([
            new_pt_corner[:, 0], new_pt_midside[:, 0],
            new_pt_midside[:, 2]]).T
        child_triangles[1::4, :] = np.vstack([
            new_pt_corner[:, 1], new_pt_midside[:, 1],
            new_pt_midside[:, 0]]).T
        child_triangles[2::4, :] = np.vstack([
            new_pt_corner[:, 2], new_pt_midside[:, 2],
            new_pt_midside[:, 1]]).T
        child_triangles[3::4, :] = np.vstack([
            new_pt_midside[:, 0], new_pt_midside[:, 1],
            new_pt_midside[:, 2]]).T
        child_triangulation = Triangulation(refi_x, refi_y, child_triangles)

        # Builds the child mask
        if triangulation.mask is not None:
            child_triangulation.set_mask(np.repeat(triangulation.mask, 4))

        if ancestors is None:
            return child_triangulation
        else:
            return child_triangulation, np.repeat(ancestors, 4)

# === NexusCore/openenv\Lib\site-packages\nltk\sem\util.py ===
# Natural Language Toolkit: Semantic Interpretation
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Utility functions for batch-processing sentences: parsing and
extraction of the semantic representation of the root node of the the
syntax tree, followed by evaluation of the semantic representation in
a first-order model.
"""

import codecs

from nltk.sem import evaluate

##############################################################
## Utility functions for connecting parse output to semantics
##############################################################


def parse_sents(inputs, grammar, trace=0):
    """
    Convert input sentences into syntactic trees.

    :param inputs: sentences to be parsed
    :type inputs: list(str)
    :param grammar: ``FeatureGrammar`` or name of feature-based grammar
    :type grammar: nltk.grammar.FeatureGrammar
    :rtype: list(nltk.tree.Tree) or dict(list(str)): list(Tree)
    :return: a mapping from input sentences to a list of ``Tree`` instances.
    """
    # put imports here to avoid circult dependencies
    from nltk.grammar import FeatureGrammar
    from nltk.parse import FeatureChartParser, load_parser

    if isinstance(grammar, FeatureGrammar):
        cp = FeatureChartParser(grammar)
    else:
        cp = load_parser(grammar, trace=trace)
    parses = []
    for sent in inputs:
        tokens = sent.split()  # use a tokenizer?
        syntrees = list(cp.parse(tokens))
        parses.append(syntrees)
    return parses


def root_semrep(syntree, semkey="SEM"):
    """
    Find the semantic representation at the root of a tree.

    :param syntree: a parse ``Tree``
    :param semkey: the feature label to use for the root semantics in the tree
    :return: the semantic representation at the root of a ``Tree``
    :rtype: sem.Expression
    """
    from nltk.grammar import FeatStructNonterminal

    node = syntree.label()
    assert isinstance(node, FeatStructNonterminal)
    try:
        return node[semkey]
    except KeyError:
        print(node, end=" ")
        print("has no specification for the feature %s" % semkey)
    raise


def interpret_sents(inputs, grammar, semkey="SEM", trace=0):
    """
    Add the semantic representation to each syntactic parse tree
    of each input sentence.

    :param inputs: a list of sentences
    :type inputs: list(str)
    :param grammar: ``FeatureGrammar`` or name of feature-based grammar
    :type grammar: nltk.grammar.FeatureGrammar
    :return: a mapping from sentences to lists of pairs (parse-tree, semantic-representations)
    :rtype: list(list(tuple(nltk.tree.Tree, nltk.sem.logic.ConstantExpression)))
    """
    return [
        [(syn, root_semrep(syn, semkey)) for syn in syntrees]
        for syntrees in parse_sents(inputs, grammar, trace=trace)
    ]


def evaluate_sents(inputs, grammar, model, assignment, trace=0):
    """
    Add the truth-in-a-model value to each semantic representation
    for each syntactic parse of each input sentences.

    :param inputs: a list of sentences
    :type inputs: list(str)
    :param grammar: ``FeatureGrammar`` or name of feature-based grammar
    :type grammar: nltk.grammar.FeatureGrammar
    :return: a mapping from sentences to lists of triples (parse-tree, semantic-representations, evaluation-in-model)
    :rtype: list(list(tuple(nltk.tree.Tree, nltk.sem.logic.ConstantExpression, bool or dict(str): bool)))
    """
    return [
        [
            (syn, sem, model.evaluate("%s" % sem, assignment, trace=trace))
            for (syn, sem) in interpretations
        ]
        for interpretations in interpret_sents(inputs, grammar)
    ]


def demo_model0():
    global m0, g0
    # Initialize a valuation of non-logical constants."""
    v = [
        ("john", "b1"),
        ("mary", "g1"),
        ("suzie", "g2"),
        ("fido", "d1"),
        ("tess", "d2"),
        ("noosa", "n"),
        ("girl", {"g1", "g2"}),
        ("boy", {"b1", "b2"}),
        ("dog", {"d1", "d2"}),
        ("bark", {"d1", "d2"}),
        ("walk", {"b1", "g2", "d1"}),
        ("chase", {("b1", "g1"), ("b2", "g1"), ("g1", "d1"), ("g2", "d2")}),
        (
            "see",
            {("b1", "g1"), ("b2", "d2"), ("g1", "b1"), ("d2", "b1"), ("g2", "n")},
        ),
        ("in", {("b1", "n"), ("b2", "n"), ("d2", "n")}),
        ("with", {("b1", "g1"), ("g1", "b1"), ("d1", "b1"), ("b1", "d1")}),
    ]
    # Read in the data from ``v``
    val = evaluate.Valuation(v)
    # Bind ``dom`` to the ``domain`` property of ``val``
    dom = val.domain
    # Initialize a model with parameters ``dom`` and ``val``.
    m0 = evaluate.Model(dom, val)
    # Initialize a variable assignment with parameter ``dom``
    g0 = evaluate.Assignment(dom)


def read_sents(filename, encoding="utf8"):
    with codecs.open(filename, "r", encoding) as fp:
        sents = [l.rstrip() for l in fp]

    # get rid of blank lines
    sents = [l for l in sents if len(l) > 0]
    sents = [l for l in sents if not l[0] == "#"]
    return sents


def demo_legacy_grammar():
    """
    Check that interpret_sents() is compatible with legacy grammars that use
    a lowercase 'sem' feature.

    Define 'test.fcfg' to be the following

    """
    from nltk.grammar import FeatureGrammar

    g = FeatureGrammar.fromstring(
        """
    % start S
    S[sem=<hello>] -> 'hello'
    """
    )
    print("Reading grammar: %s" % g)
    print("*" * 20)
    for reading in interpret_sents(["hello"], g, semkey="sem"):
        syn, sem = reading[0]
        print()
        print("output: ", sem)


def demo():
    import sys
    from optparse import OptionParser

    description = """
    Parse and evaluate some sentences.
    """

    opts = OptionParser(description=description)

    opts.set_defaults(
        evaluate=True,
        beta=True,
        syntrace=0,
        semtrace=0,
        demo="default",
        grammar="",
        sentences="",
    )

    opts.add_option(
        "-d",
        "--demo",
        dest="demo",
        help="choose demo D; omit this for the default demo, or specify 'chat80'",
        metavar="D",
    )
    opts.add_option(
        "-g", "--gram", dest="grammar", help="read in grammar G", metavar="G"
    )
    opts.add_option(
        "-m",
        "--model",
        dest="model",
        help="import model M (omit '.py' suffix)",
        metavar="M",
    )
    opts.add_option(
        "-s",
        "--sentences",
        dest="sentences",
        help="read in a file of test sentences S",
        metavar="S",
    )
    opts.add_option(
        "-e",
        "--no-eval",
        action="store_false",
        dest="evaluate",
        help="just do a syntactic analysis",
    )
    opts.add_option(
        "-b",
        "--no-beta-reduction",
        action="store_false",
        dest="beta",
        help="don't carry out beta-reduction",
    )
    opts.add_option(
        "-t",
        "--syntrace",
        action="count",
        dest="syntrace",
        help="set syntactic tracing on; requires '-e' option",
    )
    opts.add_option(
        "-T",
        "--semtrace",
        action="count",
        dest="semtrace",
        help="set semantic tracing on",
    )

    (options, args) = opts.parse_args()

    SPACER = "-" * 30

    demo_model0()

    sents = [
        "Fido sees a boy with Mary",
        "John sees Mary",
        "every girl chases a dog",
        "every boy chases a girl",
        "John walks with a girl in Noosa",
        "who walks",
    ]

    gramfile = "grammars/sample_grammars/sem2.fcfg"

    if options.sentences:
        sentsfile = options.sentences
    if options.grammar:
        gramfile = options.grammar
    if options.model:
        exec("import %s as model" % options.model)

    if sents is None:
        sents = read_sents(sentsfile)

    # Set model and assignment
    model = m0
    g = g0

    if options.evaluate:
        evaluations = evaluate_sents(sents, gramfile, model, g, trace=options.semtrace)
    else:
        semreps = interpret_sents(sents, gramfile, trace=options.syntrace)

    for i, sent in enumerate(sents):
        n = 1
        print("\nSentence: %s" % sent)
        print(SPACER)
        if options.evaluate:
            for syntree, semrep, value in evaluations[i]:
                if isinstance(value, dict):
                    value = set(value.keys())
                print("%d:  %s" % (n, semrep))
                print(value)
                n += 1
        else:
            for syntree, semrep in semreps[i]:
                print("%d:  %s" % (n, semrep))
                n += 1


if __name__ == "__main__":
    demo()
    demo_legacy_grammar()

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\proxy.py ===
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
"""The Proxy implementation."""


class ProxyTypeFactory:
    """Factory for proxy types."""

    @staticmethod
    def make(ff_value, string):
        return {"ff_value": ff_value, "string": string}


class ProxyType:
    """Set of possible types of proxy.

    Each proxy type has 2 properties:    'ff_value' is value of Firefox
    profile preference,    'string' is id of proxy type.
    """

    DIRECT = ProxyTypeFactory.make(0, "DIRECT")  # Direct connection, no proxy (default on Windows).
    MANUAL = ProxyTypeFactory.make(1, "MANUAL")  # Manual proxy settings (e.g., for httpProxy).
    PAC = ProxyTypeFactory.make(2, "PAC")  # Proxy autoconfiguration from URL.
    RESERVED_1 = ProxyTypeFactory.make(3, "RESERVED1")  # Never used.
    AUTODETECT = ProxyTypeFactory.make(4, "AUTODETECT")  # Proxy autodetection (presumably with WPAD).
    SYSTEM = ProxyTypeFactory.make(5, "SYSTEM")  # Use system settings (default on Linux).
    UNSPECIFIED = ProxyTypeFactory.make(6, "UNSPECIFIED")  # Not initialized (for internal use).

    @classmethod
    def load(cls, value):
        if isinstance(value, dict) and "string" in value:
            value = value["string"]
        value = str(value).upper()
        for attr in dir(cls):
            attr_value = getattr(cls, attr)
            if isinstance(attr_value, dict) and "string" in attr_value and attr_value["string"] == value:
                return attr_value
        raise Exception(f"No proxy type is found for {value}")


class _ProxyTypeDescriptor:
    def __init__(self, name, p_type):
        self.name = name
        self.p_type = p_type

    def __get__(self, obj, cls):
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if self.name == "autodetect" and not isinstance(value, bool):
            raise ValueError("Autodetect proxy value needs to be a boolean")
        getattr(obj, "_verify_proxy_type_compatibility")(self.p_type)
        setattr(obj, "proxyType", self.p_type)
        setattr(obj, self.name, value)


class Proxy:
    """Proxy contains information about proxy type and necessary proxy
    settings."""

    proxyType = ProxyType.UNSPECIFIED
    autodetect = False
    ftpProxy = ""
    httpProxy = ""
    noProxy = ""
    proxyAutoconfigUrl = ""
    sslProxy = ""
    socksProxy = ""
    socksUsername = ""
    socksPassword = ""
    socksVersion = None

    # create descriptor type objects
    auto_detect = _ProxyTypeDescriptor("autodetect", ProxyType.AUTODETECT)
    """Gets and Sets `auto_detect`

    Usage:
    ------
    - Get
        - `self.auto_detect`
    - Set
        - `self.auto_detect` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    ftp_proxy = _ProxyTypeDescriptor("ftpProxy", ProxyType.MANUAL)
    """Gets and Sets `ftp_proxy`

    Usage:
    ------
    - Get
        - `self.ftp_proxy`
    - Set
        - `self.ftp_proxy` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    http_proxy = _ProxyTypeDescriptor("httpProxy", ProxyType.MANUAL)
    """Gets and Sets `http_proxy`

    Usage:
    ------
    - Get
        - `self.http_proxy`
    - Set
        - `self.http_proxy` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    no_proxy = _ProxyTypeDescriptor("noProxy", ProxyType.MANUAL)
    """Gets and Sets `no_proxy`

    Usage:
    ------
    - Get
        - `self.no_proxy`
    - Set
        - `self.no_proxy` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    proxy_autoconfig_url = _ProxyTypeDescriptor("proxyAutoconfigUrl", ProxyType.PAC)
    """Gets and Sets `proxy_autoconfig_url`

    Usage:
    ------
    - Get
        - `self.proxy_autoconfig_url`
    - Set
        - `self.proxy_autoconfig_url` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    ssl_proxy = _ProxyTypeDescriptor("sslProxy", ProxyType.MANUAL)
    """Gets and Sets `ssl_proxy`

    Usage:
    ------
    - Get
        - `self.ssl_proxy`
    - Set
        - `self.ssl_proxy` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    socks_proxy = _ProxyTypeDescriptor("socksProxy", ProxyType.MANUAL)
    """Gets and Sets `socks_proxy`

    Usage:
    ------
    - Get
        - `self.sock_proxy`
    - Set
        - `self.socks_proxy` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    socks_username = _ProxyTypeDescriptor("socksUsername", ProxyType.MANUAL)
    """Gets and Sets `socks_password`

    Usage:
    ------
    - Get
        - `self.socks_password`
    - Set
        - `self.socks_password` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    socks_password = _ProxyTypeDescriptor("socksPassword", ProxyType.MANUAL)
    """Gets and Sets `socks_password`

    Usage:
    ------
    - Get
        - `self.socks_password`
    - Set
        - `self.socks_password` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    socks_version = _ProxyTypeDescriptor("socksVersion", ProxyType.MANUAL)
    """Gets and Sets `socks_version`

    Usage:
    ------
    - Get
        - `self.socks_version`
    - Set
        - `self.socks_version` = `value`

    Parameters:
    -----------
    `value`: `str`
    """

    def __init__(self, raw=None):
        """Creates a new Proxy.

        :Args:
         - raw: raw proxy data. If None, default class values are used.
        """
        if raw:
            if "proxyType" in raw and raw["proxyType"]:
                self.proxy_type = ProxyType.load(raw["proxyType"])
            if "ftpProxy" in raw and raw["ftpProxy"]:
                self.ftp_proxy = raw["ftpProxy"]
            if "httpProxy" in raw and raw["httpProxy"]:
                self.http_proxy = raw["httpProxy"]
            if "noProxy" in raw and raw["noProxy"]:
                self.no_proxy = raw["noProxy"]
            if "proxyAutoconfigUrl" in raw and raw["proxyAutoconfigUrl"]:
                self.proxy_autoconfig_url = raw["proxyAutoconfigUrl"]
            if "sslProxy" in raw and raw["sslProxy"]:
                self.sslProxy = raw["sslProxy"]
            if "autodetect" in raw and raw["autodetect"]:
                self.auto_detect = raw["autodetect"]
            if "socksProxy" in raw and raw["socksProxy"]:
                self.socks_proxy = raw["socksProxy"]
            if "socksUsername" in raw and raw["socksUsername"]:
                self.socks_username = raw["socksUsername"]
            if "socksPassword" in raw and raw["socksPassword"]:
                self.socks_password = raw["socksPassword"]
            if "socksVersion" in raw and raw["socksVersion"]:
                self.socks_version = raw["socksVersion"]

    @property
    def proxy_type(self):
        """Returns proxy type as `ProxyType`."""
        return self.proxyType

    @proxy_type.setter
    def proxy_type(self, value) -> None:
        """Sets proxy type.

        :Args:
         - value: The proxy type.
        """
        self._verify_proxy_type_compatibility(value)
        self.proxyType = value

    def _verify_proxy_type_compatibility(self, compatible_proxy):
        if self.proxyType not in (ProxyType.UNSPECIFIED, compatible_proxy):
            raise ValueError(
                f"Specified proxy type ({compatible_proxy}) not compatible with current setting ({self.proxyType})"
            )

    def to_capabilities(self):
        proxy_caps = {"proxyType": self.proxyType["string"].lower()}
        proxies = [
            "autodetect",
            "ftpProxy",
            "httpProxy",
            "proxyAutoconfigUrl",
            "sslProxy",
            "noProxy",
            "socksProxy",
            "socksUsername",
            "socksPassword",
            "socksVersion",
        ]
        for proxy in proxies:
            attr_value = getattr(self, proxy)
            if attr_value:
                proxy_caps[proxy] = attr_value
        return proxy_caps

# === NexusCore/openenv\Lib\site-packages\cffi\verifier.py ===
#
# DEPRECATED: implementation for ffi.verify()
#
import sys, os, binascii, shutil, io
from . import __version_verifier_modules__
from . import ffiplatform
from .error import VerificationError

if sys.version_info >= (3, 3):
    import importlib.machinery
    def _extension_suffixes():
        return importlib.machinery.EXTENSION_SUFFIXES[:]
else:
    import imp
    def _extension_suffixes():
        return [suffix for suffix, _, type in imp.get_suffixes()
                if type == imp.C_EXTENSION]


if sys.version_info >= (3,):
    NativeIO = io.StringIO
else:
    class NativeIO(io.BytesIO):
        def write(self, s):
            if isinstance(s, unicode):
                s = s.encode('ascii')
            super(NativeIO, self).write(s)


class Verifier(object):

    def __init__(self, ffi, preamble, tmpdir=None, modulename=None,
                 ext_package=None, tag='', force_generic_engine=False,
                 source_extension='.c', flags=None, relative_to=None, **kwds):
        if ffi._parser._uses_new_feature:
            raise VerificationError(
                "feature not supported with ffi.verify(), but only "
                "with ffi.set_source(): %s" % (ffi._parser._uses_new_feature,))
        self.ffi = ffi
        self.preamble = preamble
        if not modulename:
            flattened_kwds = ffiplatform.flatten(kwds)
        vengine_class = _locate_engine_class(ffi, force_generic_engine)
        self._vengine = vengine_class(self)
        self._vengine.patch_extension_kwds(kwds)
        self.flags = flags
        self.kwds = self.make_relative_to(kwds, relative_to)
        #
        if modulename:
            if tag:
                raise TypeError("can't specify both 'modulename' and 'tag'")
        else:
            key = '\x00'.join(['%d.%d' % sys.version_info[:2],
                               __version_verifier_modules__,
                               preamble, flattened_kwds] +
                              ffi._cdefsources)
            if sys.version_info >= (3,):
                key = key.encode('utf-8')
            k1 = hex(binascii.crc32(key[0::2]) & 0xffffffff)
            k1 = k1.lstrip('0x').rstrip('L')
            k2 = hex(binascii.crc32(key[1::2]) & 0xffffffff)
            k2 = k2.lstrip('0').rstrip('L')
            modulename = '_cffi_%s_%s%s%s' % (tag, self._vengine._class_key,
                                              k1, k2)
        suffix = _get_so_suffixes()[0]
        self.tmpdir = tmpdir or _caller_dir_pycache()
        self.sourcefilename = os.path.join(self.tmpdir, modulename + source_extension)
        self.modulefilename = os.path.join(self.tmpdir, modulename + suffix)
        self.ext_package = ext_package
        self._has_source = False
        self._has_module = False

    def write_source(self, file=None):
        """Write the C source code.  It is produced in 'self.sourcefilename',
        which can be tweaked beforehand."""
        with self.ffi._lock:
            if self._has_source and file is None:
                raise VerificationError(
                    "source code already written")
            self._write_source(file)

    def compile_module(self):
        """Write the C source code (if not done already) and compile it.
        This produces a dynamic link library in 'self.modulefilename'."""
        with self.ffi._lock:
            if self._has_module:
                raise VerificationError("module already compiled")
            if not self._has_source:
                self._write_source()
            self._compile_module()

    def load_library(self):
        """Get a C module from this Verifier instance.
        Returns an instance of a FFILibrary class that behaves like the
        objects returned by ffi.dlopen(), but that delegates all
        operations to the C module.  If necessary, the C code is written
        and compiled first.
        """
        with self.ffi._lock:
            if not self._has_module:
                self._locate_module()
                if not self._has_module:
                    if not self._has_source:
                        self._write_source()
                    self._compile_module()
            return self._load_library()

    def get_module_name(self):
        basename = os.path.basename(self.modulefilename)
        # kill both the .so extension and the other .'s, as introduced
        # by Python 3: 'basename.cpython-33m.so'
        basename = basename.split('.', 1)[0]
        # and the _d added in Python 2 debug builds --- but try to be
        # conservative and not kill a legitimate _d
        if basename.endswith('_d') and hasattr(sys, 'gettotalrefcount'):
            basename = basename[:-2]
        return basename

    def get_extension(self):
        if not self._has_source:
            with self.ffi._lock:
                if not self._has_source:
                    self._write_source()
        sourcename = ffiplatform.maybe_relative_path(self.sourcefilename)
        modname = self.get_module_name()
        return ffiplatform.get_extension(sourcename, modname, **self.kwds)

    def generates_python_module(self):
        return self._vengine._gen_python_module

    def make_relative_to(self, kwds, relative_to):
        if relative_to and os.path.dirname(relative_to):
            dirname = os.path.dirname(relative_to)
            kwds = kwds.copy()
            for key in ffiplatform.LIST_OF_FILE_NAMES:
                if key in kwds:
                    lst = kwds[key]
                    if not isinstance(lst, (list, tuple)):
                        raise TypeError("keyword '%s' should be a list or tuple"
                                        % (key,))
                    lst = [os.path.join(dirname, fn) for fn in lst]
                    kwds[key] = lst
        return kwds

    # ----------

    def _locate_module(self):
        if not os.path.isfile(self.modulefilename):
            if self.ext_package:
                try:
                    pkg = __import__(self.ext_package, None, None, ['__doc__'])
                except ImportError:
                    return      # cannot import the package itself, give up
                    # (e.g. it might be called differently before installation)
                path = pkg.__path__
            else:
                path = None
            filename = self._vengine.find_module(self.get_module_name(), path,
                                                 _get_so_suffixes())
            if filename is None:
                return
            self.modulefilename = filename
        self._vengine.collect_types()
        self._has_module = True

    def _write_source_to(self, file):
        self._vengine._f = file
        try:
            self._vengine.write_source_to_f()
        finally:
            del self._vengine._f

    def _write_source(self, file=None):
        if file is not None:
            self._write_source_to(file)
        else:
            # Write our source file to an in memory file.
            f = NativeIO()
            self._write_source_to(f)
            source_data = f.getvalue()

            # Determine if this matches the current file
            if os.path.exists(self.sourcefilename):
                with open(self.sourcefilename, "r") as fp:
                    needs_written = not (fp.read() == source_data)
            else:
                needs_written = True

            # Actually write the file out if it doesn't match
            if needs_written:
                _ensure_dir(self.sourcefilename)
                with open(self.sourcefilename, "w") as fp:
                    fp.write(source_data)

            # Set this flag
            self._has_source = True

    def _compile_module(self):
        # compile this C source
        tmpdir = os.path.dirname(self.sourcefilename)
        outputfilename = ffiplatform.compile(tmpdir, self.get_extension())
        try:
            same = ffiplatform.samefile(outputfilename, self.modulefilename)
        except OSError:
            same = False
        if not same:
            _ensure_dir(self.modulefilename)
            shutil.move(outputfilename, self.modulefilename)
        self._has_module = True

    def _load_library(self):
        assert self._has_module
        if self.flags is not None:
            return self._vengine.load_library(self.flags)
        else:
            return self._vengine.load_library()

# ____________________________________________________________

_FORCE_GENERIC_ENGINE = False      # for tests

def _locate_engine_class(ffi, force_generic_engine):
    if _FORCE_GENERIC_ENGINE:
        force_generic_engine = True
    if not force_generic_engine:
        if '__pypy__' in sys.builtin_module_names:
            force_generic_engine = True
        else:
            try:
                import _cffi_backend
            except ImportError:
                _cffi_backend = '?'
            if ffi._backend is not _cffi_backend:
                force_generic_engine = True
    if force_generic_engine:
        from . import vengine_gen
        return vengine_gen.VGenericEngine
    else:
        from . import vengine_cpy
        return vengine_cpy.VCPythonEngine

# ____________________________________________________________

_TMPDIR = None

def _caller_dir_pycache():
    if _TMPDIR:
        return _TMPDIR
    result = os.environ.get('CFFI_TMPDIR')
    if result:
        return result
    filename = sys._getframe(2).f_code.co_filename
    return os.path.abspath(os.path.join(os.path.dirname(filename),
                           '__pycache__'))

def set_tmpdir(dirname):
    """Set the temporary directory to use instead of __pycache__."""
    global _TMPDIR
    _TMPDIR = dirname

def cleanup_tmpdir(tmpdir=None, keep_so=False):
    """Clean up the temporary directory by removing all files in it
    called `_cffi_*.{c,so}` as well as the `build` subdirectory."""
    tmpdir = tmpdir or _caller_dir_pycache()
    try:
        filelist = os.listdir(tmpdir)
    except OSError:
        return
    if keep_so:
        suffix = '.c'   # only remove .c files
    else:
        suffix = _get_so_suffixes()[0].lower()
    for fn in filelist:
        if fn.lower().startswith('_cffi_') and (
                fn.lower().endswith(suffix) or fn.lower().endswith('.c')):
            try:
                os.unlink(os.path.join(tmpdir, fn))
            except OSError:
                pass
    clean_dir = [os.path.join(tmpdir, 'build')]
    for dir in clean_dir:
        try:
            for fn in os.listdir(dir):
                fn = os.path.join(dir, fn)
                if os.path.isdir(fn):
                    clean_dir.append(fn)
                else:
                    os.unlink(fn)
        except OSError:
            pass

def _get_so_suffixes():
    suffixes = _extension_suffixes()
    if not suffixes:
        # bah, no C_EXTENSION available.  Occurs on pypy without cpyext
        if sys.platform == 'win32':
            suffixes = [".pyd"]
        else:
            suffixes = [".so"]

    return suffixes

def _ensure_dir(filename):
    dirname = os.path.dirname(filename)
    if dirname and not os.path.isdir(dirname):
        os.makedirs(dirname)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\history.py ===
"""
Implementations for the history of a `Buffer`.

NOTE: There is no `DynamicHistory`:
      This doesn't work well, because the `Buffer` needs to be able to attach
      an event handler to the event when a history entry is loaded. This
      loading can be done asynchronously and making the history swappable would
      probably break this.
"""

from __future__ import annotations

import datetime
import os
import threading
from abc import ABCMeta, abstractmethod
from asyncio import get_running_loop
from typing import AsyncGenerator, Iterable, Sequence, Union

__all__ = [
    "History",
    "ThreadedHistory",
    "DummyHistory",
    "FileHistory",
    "InMemoryHistory",
]


class History(metaclass=ABCMeta):
    """
    Base ``History`` class.

    This also includes abstract methods for loading/storing history.
    """

    def __init__(self) -> None:
        # In memory storage for strings.
        self._loaded = False

        # History that's loaded already, in reverse order. Latest, most recent
        # item first.
        self._loaded_strings: list[str] = []

    #
    # Methods expected by `Buffer`.
    #

    async def load(self) -> AsyncGenerator[str, None]:
        """
        Load the history and yield all the entries in reverse order (latest,
        most recent history entry first).

        This method can be called multiple times from the `Buffer` to
        repopulate the history when prompting for a new input. So we are
        responsible here for both caching, and making sure that strings that
        were were appended to the history will be incorporated next time this
        method is called.
        """
        if not self._loaded:
            self._loaded_strings = list(self.load_history_strings())
            self._loaded = True

        for item in self._loaded_strings:
            yield item

    def get_strings(self) -> list[str]:
        """
        Get the strings from the history that are loaded so far.
        (In order. Oldest item first.)
        """
        return self._loaded_strings[::-1]

    def append_string(self, string: str) -> None:
        "Add string to the history."
        self._loaded_strings.insert(0, string)
        self.store_string(string)

    #
    # Implementation for specific backends.
    #

    @abstractmethod
    def load_history_strings(self) -> Iterable[str]:
        """
        This should be a generator that yields `str` instances.

        It should yield the most recent items first, because they are the most
        important. (The history can already be used, even when it's only
        partially loaded.)
        """
        while False:
            yield

    @abstractmethod
    def store_string(self, string: str) -> None:
        """
        Store the string in persistent storage.
        """


class ThreadedHistory(History):
    """
    Wrapper around `History` implementations that run the `load()` generator in
    a thread.

    Use this to increase the start-up time of prompt_toolkit applications.
    History entries are available as soon as they are loaded. We don't have to
    wait for everything to be loaded.
    """

    def __init__(self, history: History) -> None:
        super().__init__()

        self.history = history

        self._load_thread: threading.Thread | None = None

        # Lock for accessing/manipulating `_loaded_strings` and `_loaded`
        # together in a consistent state.
        self._lock = threading.Lock()

        # Events created by each `load()` call. Used to wait for new history
        # entries from the loader thread.
        self._string_load_events: list[threading.Event] = []

    async def load(self) -> AsyncGenerator[str, None]:
        """
        Like `History.load(), but call `self.load_history_strings()` in a
        background thread.
        """
        # Start the load thread, if this is called for the first time.
        if not self._load_thread:
            self._load_thread = threading.Thread(
                target=self._in_load_thread,
                daemon=True,
            )
            self._load_thread.start()

        # Consume the `_loaded_strings` list, using asyncio.
        loop = get_running_loop()

        # Create threading Event so that we can wait for new items.
        event = threading.Event()
        event.set()
        self._string_load_events.append(event)

        items_yielded = 0

        try:
            while True:
                # Wait for new items to be available.
                # (Use a timeout, because the executor thread is not a daemon
                # thread. The "slow-history.py" example would otherwise hang if
                # Control-C is pressed before the history is fully loaded,
                # because there's still this non-daemon executor thread waiting
                # for this event.)
                got_timeout = await loop.run_in_executor(
                    None, lambda: event.wait(timeout=0.5)
                )
                if not got_timeout:
                    continue

                # Read new items (in lock).
                def in_executor() -> tuple[list[str], bool]:
                    with self._lock:
                        new_items = self._loaded_strings[items_yielded:]
                        done = self._loaded
                        event.clear()
                    return new_items, done

                new_items, done = await loop.run_in_executor(None, in_executor)

                items_yielded += len(new_items)

                for item in new_items:
                    yield item

                if done:
                    break
        finally:
            self._string_load_events.remove(event)

    def _in_load_thread(self) -> None:
        try:
            # Start with an empty list. In case `append_string()` was called
            # before `load()` happened. Then `.store_string()` will have
            # written these entries back to disk and we will reload it.
            self._loaded_strings = []

            for item in self.history.load_history_strings():
                with self._lock:
                    self._loaded_strings.append(item)

                for event in self._string_load_events:
                    event.set()
        finally:
            with self._lock:
                self._loaded = True
            for event in self._string_load_events:
                event.set()

    def append_string(self, string: str) -> None:
        with self._lock:
            self._loaded_strings.insert(0, string)
        self.store_string(string)

    # All of the following are proxied to `self.history`.

    def load_history_strings(self) -> Iterable[str]:
        return self.history.load_history_strings()

    def store_string(self, string: str) -> None:
        self.history.store_string(string)

    def __repr__(self) -> str:
        return f"ThreadedHistory({self.history!r})"


class InMemoryHistory(History):
    """
    :class:`.History` class that keeps a list of all strings in memory.

    In order to prepopulate the history, it's possible to call either
    `append_string` for all items or pass a list of strings to `__init__` here.
    """

    def __init__(self, history_strings: Sequence[str] | None = None) -> None:
        super().__init__()
        # Emulating disk storage.
        if history_strings is None:
            self._storage = []
        else:
            self._storage = list(history_strings)

    def load_history_strings(self) -> Iterable[str]:
        yield from self._storage[::-1]

    def store_string(self, string: str) -> None:
        self._storage.append(string)


class DummyHistory(History):
    """
    :class:`.History` object that doesn't remember anything.
    """

    def load_history_strings(self) -> Iterable[str]:
        return []

    def store_string(self, string: str) -> None:
        pass

    def append_string(self, string: str) -> None:
        # Don't remember this.
        pass


_StrOrBytesPath = Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]


class FileHistory(History):
    """
    :class:`.History` class that stores all strings in a file.
    """

    def __init__(self, filename: _StrOrBytesPath) -> None:
        self.filename = filename
        super().__init__()

    def load_history_strings(self) -> Iterable[str]:
        strings: list[str] = []
        lines: list[str] = []

        def add() -> None:
            if lines:
                # Join and drop trailing newline.
                string = "".join(lines)[:-1]

                strings.append(string)

        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                for line_bytes in f:
                    line = line_bytes.decode("utf-8", errors="replace")

                    if line.startswith("+"):
                        lines.append(line[1:])
                    else:
                        add()
                        lines = []

                add()

        # Reverse the order, because newest items have to go first.
        return reversed(strings)

    def store_string(self, string: str) -> None:
        # Save to file.
        with open(self.filename, "ab") as f:

            def write(t: str) -> None:
                f.write(t.encode("utf-8"))

            write(f"\n# {datetime.datetime.now()}\n")
            for line in string.split("\n"):
                write(f"+{line}\n")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\dynamic_rate_limiter.py ===
# What is this?
## Allocates dynamic tpm/rpm quota for a project based on current traffic
## Tracks num active projects per minute

import asyncio
import os
from typing import List, Literal, Optional, Tuple, Union

from fastapi import HTTPException

import litellm
from litellm import ModelResponse, Router
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import UserAPIKeyAuth
from litellm.types.router import ModelGroupInfo
from litellm.utils import get_utc_datetime


class DynamicRateLimiterCache:
    """
    Thin wrapper on DualCache for this file.

    Track number of active projects calling a model.
    """

    def __init__(self, cache: DualCache) -> None:
        self.cache = cache
        self.ttl = 60  # 1 min ttl

    async def async_get_cache(self, model: str) -> Optional[int]:
        dt = get_utc_datetime()
        current_minute = dt.strftime("%H-%M")
        key_name = "{}:{}".format(current_minute, model)
        _response = await self.cache.async_get_cache(key=key_name)
        response: Optional[int] = None
        if _response is not None:
            response = len(_response)
        return response

    async def async_set_cache_sadd(self, model: str, value: List):
        """
        Add value to set.

        Parameters:
        - model: str, the name of the model group
        - value: str, the team id

        Returns:
        - None

        Raises:
        - Exception, if unable to connect to cache client (if redis caching enabled)
        """
        try:
            dt = get_utc_datetime()
            current_minute = dt.strftime("%H-%M")

            key_name = "{}:{}".format(current_minute, model)
            await self.cache.async_set_cache_sadd(
                key=key_name, value=value, ttl=self.ttl
            )
        except Exception as e:
            verbose_proxy_logger.exception(
                "litellm.proxy.hooks.dynamic_rate_limiter.py::async_set_cache_sadd(): Exception occured - {}".format(
                    str(e)
                )
            )
            raise e


class _PROXY_DynamicRateLimitHandler(CustomLogger):
    # Class variables or attributes
    def __init__(self, internal_usage_cache: DualCache):
        self.internal_usage_cache = DynamicRateLimiterCache(cache=internal_usage_cache)

    def update_variables(self, llm_router: Router):
        self.llm_router = llm_router

    async def check_available_usage(
        self, model: str, priority: Optional[str] = None
    ) -> Tuple[
        Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]
    ]:
        """
        For a given model, get its available tpm

        Params:
        - model: str, the name of the model in the router model_list
        - priority: Optional[str], the priority for the request.

        Returns
        - Tuple[available_tpm, available_tpm, model_tpm, model_rpm, active_projects]
            - available_tpm: int or null - always 0 or positive.
            - available_tpm: int or null - always 0 or positive.
            - remaining_model_tpm: int or null. If available tpm is int, then this will be too.
            - remaining_model_rpm: int or null. If available rpm is int, then this will be too.
            - active_projects: int or null
        """
        try:
            weight: float = 1
            if (
                litellm.priority_reservation is None
                or priority not in litellm.priority_reservation
            ):
                verbose_proxy_logger.error(
                    "Priority Reservation not set. priority={}, but litellm.priority_reservation is {}.".format(
                        priority, litellm.priority_reservation
                    )
                )
            elif priority is not None and litellm.priority_reservation is not None:
                if os.getenv("LITELLM_LICENSE", None) is None:
                    verbose_proxy_logger.error(
                        "PREMIUM FEATURE: Reserving tpm/rpm by priority is a premium feature. Please add a 'LITELLM_LICENSE' to your .env to enable this.\nGet a license: https://docs.litellm.ai/docs/proxy/enterprise."
                    )
                else:
                    weight = litellm.priority_reservation[priority]

            active_projects = await self.internal_usage_cache.async_get_cache(
                model=model
            )
            (
                current_model_tpm,
                current_model_rpm,
            ) = await self.llm_router.get_model_group_usage(model_group=model)
            model_group_info: Optional[
                ModelGroupInfo
            ] = self.llm_router.get_model_group_info(model_group=model)
            total_model_tpm: Optional[int] = None
            total_model_rpm: Optional[int] = None
            if model_group_info is not None:
                if model_group_info.tpm is not None:
                    total_model_tpm = model_group_info.tpm
                if model_group_info.rpm is not None:
                    total_model_rpm = model_group_info.rpm

            remaining_model_tpm: Optional[int] = None
            if total_model_tpm is not None and current_model_tpm is not None:
                remaining_model_tpm = total_model_tpm - current_model_tpm
            elif total_model_tpm is not None:
                remaining_model_tpm = total_model_tpm

            remaining_model_rpm: Optional[int] = None
            if total_model_rpm is not None and current_model_rpm is not None:
                remaining_model_rpm = total_model_rpm - current_model_rpm
            elif total_model_rpm is not None:
                remaining_model_rpm = total_model_rpm

            available_tpm: Optional[int] = None

            if remaining_model_tpm is not None:
                if active_projects is not None:
                    available_tpm = int(remaining_model_tpm * weight / active_projects)
                else:
                    available_tpm = int(remaining_model_tpm * weight)

            if available_tpm is not None and available_tpm < 0:
                available_tpm = 0

            available_rpm: Optional[int] = None

            if remaining_model_rpm is not None:
                if active_projects is not None:
                    available_rpm = int(remaining_model_rpm * weight / active_projects)
                else:
                    available_rpm = int(remaining_model_rpm * weight)

            if available_rpm is not None and available_rpm < 0:
                available_rpm = 0
            return (
                available_tpm,
                available_rpm,
                remaining_model_tpm,
                remaining_model_rpm,
                active_projects,
            )
        except Exception as e:
            verbose_proxy_logger.exception(
                "litellm.proxy.hooks.dynamic_rate_limiter.py::check_available_usage: Exception occurred - {}".format(
                    str(e)
                )
            )
            return None, None, None, None, None

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
            "pass_through_endpoint",
            "rerank",
        ],
    ) -> Optional[
        Union[Exception, str, dict]
    ]:  # raise exception if invalid, return a str for the user to receive - if rejected, or return a modified dictionary for passing into litellm
        """
        - For a model group
        - Check if tpm/rpm available
        - Raise RateLimitError if no tpm/rpm available
        """
        if "model" in data:
            key_priority: Optional[str] = user_api_key_dict.metadata.get(
                "priority", None
            )
            (
                available_tpm,
                available_rpm,
                model_tpm,
                model_rpm,
                active_projects,
            ) = await self.check_available_usage(
                model=data["model"], priority=key_priority
            )
            ### CHECK TPM ###
            if available_tpm is not None and available_tpm == 0:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Key={} over available TPM={}. Model TPM={}, Active keys={}".format(
                            user_api_key_dict.api_key,
                            available_tpm,
                            model_tpm,
                            active_projects,
                        )
                    },
                )
            ### CHECK RPM ###
            elif available_rpm is not None and available_rpm == 0:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Key={} over available RPM={}. Model RPM={}, Active keys={}".format(
                            user_api_key_dict.api_key,
                            available_rpm,
                            model_rpm,
                            active_projects,
                        )
                    },
                )
            elif available_rpm is not None or available_tpm is not None:
                ## UPDATE CACHE WITH ACTIVE PROJECT
                asyncio.create_task(
                    self.internal_usage_cache.async_set_cache_sadd(  # this is a set
                        model=data["model"],  # type: ignore
                        value=[user_api_key_dict.token or "default_key"],
                    )
                )
        return None

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: UserAPIKeyAuth, response
    ):
        try:
            if isinstance(response, ModelResponse):
                model_info = self.llm_router.get_model_info(
                    id=response._hidden_params["model_id"]
                )
                assert (
                    model_info is not None
                ), "Model info for model with id={} is None".format(
                    response._hidden_params["model_id"]
                )
                key_priority: Optional[str] = user_api_key_dict.metadata.get(
                    "priority", None
                )
                (
                    available_tpm,
                    available_rpm,
                    model_tpm,
                    model_rpm,
                    active_projects,
                ) = await self.check_available_usage(
                    model=model_info["model_name"], priority=key_priority
                )
                response._hidden_params[
                    "additional_headers"
                ] = {  # Add additional response headers - easier debugging
                    "x-litellm-model_group": model_info["model_name"],
                    "x-ratelimit-remaining-litellm-project-tokens": available_tpm,
                    "x-ratelimit-remaining-litellm-project-requests": available_rpm,
                    "x-ratelimit-remaining-model-tokens": model_tpm,
                    "x-ratelimit-remaining-model-requests": model_rpm,
                    "x-ratelimit-current-active-projects": active_projects,
                }

                return response
            return await super().async_post_call_success_hook(
                data=data,
                user_api_key_dict=user_api_key_dict,
                response=response,
            )
        except Exception as e:
            verbose_proxy_logger.exception(
                "litellm.proxy.hooks.dynamic_rate_limiter.py::async_post_call_success_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            return response

# === NexusCore/openenv\Lib\site-packages\nltk\twitter\twitter_demo.py ===
# Natural Language Toolkit: Twitter client
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Lorenzo Rubio <lrnzcig@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Examples to demo the :py:mod:`twitterclient` code.

These demo functions should all run, with the following caveats:

* You must have obtained API keys from Twitter, and installed them according to
  the instructions in the `twitter HOWTO <https://www.nltk.org/howto/twitter.html>`_.

* If you are on a slow network, some of the calls to the Twitter API may
  timeout.

* If you are being rate limited while searching, you will receive a 420
  error response.

* Your terminal window / console must be able to display UTF-8 encoded characters.

For documentation about the Twitter APIs, see `The Streaming APIs Overview
<https://dev.twitter.com/streaming/overview>`_ and `The REST APIs Overview
<https://dev.twitter.com/rest/public>`_.

For error codes see Twitter's
`Error Codes and Responses <https://dev.twitter.com/overview/api/response-codes>`
"""

import datetime
import json
from functools import wraps
from io import StringIO

from nltk.twitter import (
    Query,
    Streamer,
    TweetViewer,
    TweetWriter,
    Twitter,
    credsfromfile,
)

SPACER = "###################################"


def verbose(func):
    """Decorator for demo functions"""

    @wraps(func)
    def with_formatting(*args, **kwargs):
        print()
        print(SPACER)
        print("Using %s" % (func.__name__))
        print(SPACER)
        return func(*args, **kwargs)

    return with_formatting


def yesterday():
    """
    Get yesterday's datetime as a 5-tuple.
    """
    date = datetime.datetime.now()
    date -= datetime.timedelta(days=1)
    date_tuple = date.timetuple()[:6]
    return date_tuple


def setup():
    """
    Initialize global variables for the demos.
    """
    global USERIDS, FIELDS

    USERIDS = ["759251", "612473", "15108702", "6017542", "2673523800"]
    # UserIDs corresponding to\
    #           @CNN,    @BBCNews, @ReutersLive, @BreakingNews, @AJELive
    FIELDS = ["id_str"]


@verbose
def twitterclass_demo():
    """
    Use the simplified :class:`Twitter` class to write some tweets to a file.
    """
    tw = Twitter()
    print("Track from the public stream\n")
    tw.tweets(keywords="love, hate", limit=10)  # public stream
    print(SPACER)
    print("Search past Tweets\n")
    tw = Twitter()
    tw.tweets(keywords="love, hate", stream=False, limit=10)  # search past tweets
    print(SPACER)
    print(
        "Follow two accounts in the public stream"
        + " -- be prepared to wait a few minutes\n"
    )
    tw = Twitter()
    tw.tweets(follow=["759251", "6017542"], stream=True, limit=5)  # public stream


@verbose
def sampletoscreen_demo(limit=20):
    """
    Sample from the Streaming API and send output to terminal.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.sample()


@verbose
def tracktoscreen_demo(track="taylor swift", limit=10):
    """
    Track keywords from the public Streaming API and send output to terminal.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.filter(track=track)


@verbose
def search_demo(keywords="nltk"):
    """
    Use the REST API to search for past tweets containing a given keyword.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    for tweet in client.search_tweets(keywords=keywords, limit=10):
        print(tweet["text"])


@verbose
def tweets_by_user_demo(user="NLTK_org", count=200):
    """
    Use the REST API to search for past tweets by a given user.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    client.register(TweetWriter())
    client.user_tweets(user, count)


@verbose
def lookup_by_userid_demo():
    """
    Use the REST API to convert a userID to a screen name.
    """
    oauth = credsfromfile()
    client = Query(**oauth)
    user_info = client.user_info_from_id(USERIDS)
    for info in user_info:
        name = info["screen_name"]
        followers = info["followers_count"]
        following = info["friends_count"]
        print(f"{name}, followers: {followers}, following: {following}")


@verbose
def followtoscreen_demo(limit=10):
    """
    Using the Streaming API, select just the tweets from a specified list of
    userIDs.

    This is will only give results in a reasonable time if the users in
    question produce a high volume of tweets, and may even so show some delay.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetViewer(limit=limit))
    client.statuses.filter(follow=USERIDS)


@verbose
def streamtofile_demo(limit=20):
    """
    Write 20 tweets sampled from the public Streaming API to a file.
    """
    oauth = credsfromfile()
    client = Streamer(**oauth)
    client.register(TweetWriter(limit=limit, repeat=False))
    client.statuses.sample()


@verbose
def limit_by_time_demo(keywords="nltk"):
    """
    Query the REST API for Tweets about NLTK since yesterday and send
    the output to terminal.

    This example makes the assumption that there are sufficient Tweets since
    yesterday for the date to be an effective cut-off.
    """
    date = yesterday()
    dt_date = datetime.datetime(*date)
    oauth = credsfromfile()
    client = Query(**oauth)
    client.register(TweetViewer(limit=100, lower_date_limit=date))

    print(f"Cutoff date: {dt_date}\n")

    for tweet in client.search_tweets(keywords=keywords):
        print("{} ".format(tweet["created_at"]), end="")
        client.handler.handle(tweet)


@verbose
def corpusreader_demo():
    """
    Use `TwitterCorpusReader` tp read a file of tweets, and print out

    * some full tweets in JSON format;
    * some raw strings from the tweets (i.e., the value of the `text` field); and
    * the result of tokenising the raw strings.

    """
    from nltk.corpus import twitter_samples as tweets

    print()
    print("Complete tweet documents")
    print(SPACER)
    for tweet in tweets.docs("tweets.20150430-223406.json")[:1]:
        print(json.dumps(tweet, indent=1, sort_keys=True))

    print()
    print("Raw tweet strings:")
    print(SPACER)
    for text in tweets.strings("tweets.20150430-223406.json")[:15]:
        print(text)

    print()
    print("Tokenized tweet strings:")
    print(SPACER)
    for toks in tweets.tokenized("tweets.20150430-223406.json")[:15]:
        print(toks)


@verbose
def expand_tweetids_demo():
    """
    Given a file object containing a list of Tweet IDs, fetch the
    corresponding full Tweets, if available.

    """
    ids_f = StringIO(
        """\
        588665495492124672
        588665495487909888
        588665495508766721
        588665495513006080
        588665495517200384
        588665495487811584
        588665495525588992
        588665495487844352
        588665495492014081
        588665495512948737"""
    )
    oauth = credsfromfile()
    client = Query(**oauth)
    hydrated = client.expand_tweetids(ids_f)

    for tweet in hydrated:
        id_str = tweet["id_str"]
        print(f"id: {id_str}")
        text = tweet["text"]
        if text.startswith("@null"):
            text = "[Tweet not available]"
        print(text + "\n")


ALL = [
    twitterclass_demo,
    sampletoscreen_demo,
    tracktoscreen_demo,
    search_demo,
    tweets_by_user_demo,
    lookup_by_userid_demo,
    followtoscreen_demo,
    streamtofile_demo,
    limit_by_time_demo,
    corpusreader_demo,
    expand_tweetids_demo,
]

"""
Select demo functions to run. E.g. replace the following line with "DEMOS =
ALL[8:]" to execute only the final three demos.
"""
DEMOS = ALL[:]

if __name__ == "__main__":
    setup()

    for demo in DEMOS:
        demo()

    print("\n" + SPACER)
    print("All demos completed")
    print(SPACER)

# === NexusCore/openenv\Lib\site-packages\openai\resources\models.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import httpx

from .. import _legacy_response
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ..pagination import SyncPage, AsyncPage
from ..types.model import Model
from .._base_client import (
    AsyncPaginator,
    make_request_options,
)
from ..types.model_deleted import ModelDeleted

__all__ = ["Models", "AsyncModels"]


class Models(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ModelsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ModelsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ModelsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ModelsWithStreamingResponse(self)

    def retrieve(
        self,
        model: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Model:
        """
        Retrieves a model instance, providing basic information about the model such as
        the owner and permissioning.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not model:
            raise ValueError(f"Expected a non-empty value for `model` but received {model!r}")
        return self._get(
            f"/models/{model}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Model,
        )

    def list(
        self,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncPage[Model]:
        """
        Lists the currently available models, and provides basic information about each
        one such as the owner and availability.
        """
        return self._get_api_list(
            "/models",
            page=SyncPage[Model],
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=Model,
        )

    def delete(
        self,
        model: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ModelDeleted:
        """Delete a fine-tuned model.

        You must have the Owner role in your organization to
        delete a model.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not model:
            raise ValueError(f"Expected a non-empty value for `model` but received {model!r}")
        return self._delete(
            f"/models/{model}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ModelDeleted,
        )


class AsyncModels(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncModelsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncModelsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncModelsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncModelsWithStreamingResponse(self)

    async def retrieve(
        self,
        model: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Model:
        """
        Retrieves a model instance, providing basic information about the model such as
        the owner and permissioning.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not model:
            raise ValueError(f"Expected a non-empty value for `model` but received {model!r}")
        return await self._get(
            f"/models/{model}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Model,
        )

    def list(
        self,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Model, AsyncPage[Model]]:
        """
        Lists the currently available models, and provides basic information about each
        one such as the owner and availability.
        """
        return self._get_api_list(
            "/models",
            page=AsyncPage[Model],
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            model=Model,
        )

    async def delete(
        self,
        model: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ModelDeleted:
        """Delete a fine-tuned model.

        You must have the Owner role in your organization to
        delete a model.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not model:
            raise ValueError(f"Expected a non-empty value for `model` but received {model!r}")
        return await self._delete(
            f"/models/{model}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ModelDeleted,
        )


class ModelsWithRawResponse:
    def __init__(self, models: Models) -> None:
        self._models = models

        self.retrieve = _legacy_response.to_raw_response_wrapper(
            models.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            models.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            models.delete,
        )


class AsyncModelsWithRawResponse:
    def __init__(self, models: AsyncModels) -> None:
        self._models = models

        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            models.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            models.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            models.delete,
        )


class ModelsWithStreamingResponse:
    def __init__(self, models: Models) -> None:
        self._models = models

        self.retrieve = to_streamed_response_wrapper(
            models.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            models.list,
        )
        self.delete = to_streamed_response_wrapper(
            models.delete,
        )


class AsyncModelsWithStreamingResponse:
    def __init__(self, models: AsyncModels) -> None:
        self._models = models

        self.retrieve = async_to_streamed_response_wrapper(
            models.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            models.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            models.delete,
        )

# === NexusCore/openenv\Lib\site-packages\playwright\_impl\_browser_type.py ===
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
import pathlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Pattern, Sequence, Union, cast

from playwright._impl._api_structures import (
    ClientCertificate,
    Geolocation,
    HttpCredentials,
    ProxySettings,
    ViewportSize,
)
from playwright._impl._browser import Browser, prepare_browser_context_params
from playwright._impl._browser_context import BrowserContext
from playwright._impl._connection import (
    ChannelOwner,
    Connection,
    from_channel,
    from_nullable_channel,
)
from playwright._impl._errors import Error
from playwright._impl._helper import (
    ColorScheme,
    Contrast,
    Env,
    ForcedColors,
    HarContentPolicy,
    HarMode,
    ReducedMotion,
    ServiceWorkersPolicy,
    locals_to_params,
)
from playwright._impl._json_pipe import JsonPipeTransport
from playwright._impl._network import serialize_headers
from playwright._impl._waiter import throw_on_timeout

if TYPE_CHECKING:
    from playwright._impl._playwright import Playwright


class BrowserType(ChannelOwner):
    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)
        self._playwright: "Playwright"

    def __repr__(self) -> str:
        return f"<BrowserType name={self.name} executable_path={self.executable_path}>"

    @property
    def name(self) -> str:
        return self._initializer["name"]

    @property
    def executable_path(self) -> str:
        return self._initializer["executablePath"]

    async def launch(
        self,
        executablePath: Union[str, Path] = None,
        channel: str = None,
        args: Sequence[str] = None,
        ignoreDefaultArgs: Union[bool, Sequence[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, float, bool]] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        normalize_launch_params(params)
        browser = cast(
            Browser, from_channel(await self._channel.send("launch", params))
        )
        self._did_launch_browser(browser)
        return browser

    async def launch_persistent_context(
        self,
        userDataDir: Union[str, Path],
        channel: str = None,
        executablePath: Union[str, Path] = None,
        args: Sequence[str] = None,
        ignoreDefaultArgs: Union[bool, Sequence[str]] = None,
        handleSIGINT: bool = None,
        handleSIGTERM: bool = None,
        handleSIGHUP: bool = None,
        timeout: float = None,
        env: Env = None,
        headless: bool = None,
        devtools: bool = None,
        proxy: ProxySettings = None,
        downloadsPath: Union[str, Path] = None,
        slowMo: float = None,
        viewport: ViewportSize = None,
        screen: ViewportSize = None,
        noViewport: bool = None,
        ignoreHTTPSErrors: bool = None,
        javaScriptEnabled: bool = None,
        bypassCSP: bool = None,
        userAgent: str = None,
        locale: str = None,
        timezoneId: str = None,
        geolocation: Geolocation = None,
        permissions: Sequence[str] = None,
        extraHTTPHeaders: Dict[str, str] = None,
        offline: bool = None,
        httpCredentials: HttpCredentials = None,
        deviceScaleFactor: float = None,
        isMobile: bool = None,
        hasTouch: bool = None,
        colorScheme: ColorScheme = None,
        reducedMotion: ReducedMotion = None,
        forcedColors: ForcedColors = None,
        contrast: Contrast = None,
        acceptDownloads: bool = None,
        tracesDir: Union[pathlib.Path, str] = None,
        chromiumSandbox: bool = None,
        firefoxUserPrefs: Dict[str, Union[str, float, bool]] = None,
        recordHarPath: Union[Path, str] = None,
        recordHarOmitContent: bool = None,
        recordVideoDir: Union[Path, str] = None,
        recordVideoSize: ViewportSize = None,
        baseURL: str = None,
        strictSelectors: bool = None,
        serviceWorkers: ServiceWorkersPolicy = None,
        recordHarUrlFilter: Union[Pattern[str], str] = None,
        recordHarMode: HarMode = None,
        recordHarContent: HarContentPolicy = None,
        clientCertificates: List[ClientCertificate] = None,
    ) -> BrowserContext:
        userDataDir = self._user_data_dir(userDataDir)
        params = locals_to_params(locals())
        await prepare_browser_context_params(params)
        normalize_launch_params(params)
        context = cast(
            BrowserContext,
            from_channel(await self._channel.send("launchPersistentContext", params)),
        )
        self._did_create_context(context, params, params)
        return context

    def _user_data_dir(self, userDataDir: Optional[Union[str, Path]]) -> str:
        if not userDataDir:
            return ""
        if not Path(userDataDir).is_absolute():
            # Can be dropped once we drop Python 3.9 support (10/2025):
            # https://github.com/python/cpython/issues/82852
            if sys.platform == "win32" and sys.version_info[:2] < (3, 10):
                return pathlib.Path.cwd() / userDataDir
            return str(Path(userDataDir).resolve())
        return str(Path(userDataDir))

    async def connect_over_cdp(
        self,
        endpointURL: str,
        timeout: float = None,
        slowMo: float = None,
        headers: Dict[str, str] = None,
    ) -> Browser:
        params = locals_to_params(locals())
        if params.get("headers"):
            params["headers"] = serialize_headers(params["headers"])
        response = await self._channel.send_return_as_dict("connectOverCDP", params)
        browser = cast(Browser, from_channel(response["browser"]))
        self._did_launch_browser(browser)

        default_context = cast(
            Optional[BrowserContext],
            from_nullable_channel(response.get("defaultContext")),
        )
        if default_context:
            self._did_create_context(default_context, {}, {})
        return browser

    async def connect(
        self,
        wsEndpoint: str,
        timeout: float = None,
        slowMo: float = None,
        headers: Dict[str, str] = None,
        exposeNetwork: str = None,
    ) -> Browser:
        if timeout is None:
            timeout = 30000
        if slowMo is None:
            slowMo = 0

        headers = {**(headers if headers else {}), "x-playwright-browser": self.name}
        local_utils = self._connection.local_utils
        pipe_channel = (
            await local_utils._channel.send_return_as_dict(
                "connect",
                {
                    "wsEndpoint": wsEndpoint,
                    "headers": headers,
                    "slowMo": slowMo,
                    "timeout": timeout,
                    "exposeNetwork": exposeNetwork,
                },
            )
        )["pipe"]
        transport = JsonPipeTransport(self._connection._loop, pipe_channel)

        connection = Connection(
            self._connection._dispatcher_fiber,
            self._connection._object_factory,
            transport,
            self._connection._loop,
            local_utils=self._connection.local_utils,
        )
        connection.mark_as_remote()

        browser = None

        def handle_transport_close(reason: Optional[str]) -> None:
            if browser:
                for context in browser.contexts:
                    for page in context.pages:
                        page._on_close()
                    context._on_close()
                browser._on_close()
            connection.cleanup(reason)
            # TODO: Backport https://github.com/microsoft/playwright/commit/d8d5289e8692c9b1265d23ee66988d1ac5122f33
            # Give a chance to any API call promises to reject upon page/context closure.
            # This happens naturally when we receive page.onClose and browser.onClose from the server
            # in separate tasks. However, upon pipe closure we used to dispatch them all synchronously
            # here and promises did not have a chance to reject.
            # The order of rejects vs closure is a part of the API contract and our test runner
            # relies on it to attribute rejections to the right test.

        transport.once("close", handle_transport_close)

        connection._is_sync = self._connection._is_sync
        connection._loop.create_task(connection.run())
        playwright_future = connection.playwright_future

        timeout_future = throw_on_timeout(timeout, Error("Connection timed out"))
        done, pending = await asyncio.wait(
            {transport.on_error_future, playwright_future, timeout_future},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not playwright_future.done():
            playwright_future.cancel()
        if not timeout_future.done():
            timeout_future.cancel()
        playwright: "Playwright" = next(iter(done)).result()
        playwright._set_selectors(self._playwright.selectors)
        self._connection._child_ws_connections.append(connection)
        pre_launched_browser = playwright._initializer.get("preLaunchedBrowser")
        assert pre_launched_browser
        browser = cast(Browser, from_channel(pre_launched_browser))
        self._did_launch_browser(browser)
        browser._should_close_connection_on_close = True

        return browser

    def _did_create_context(
        self, context: BrowserContext, context_options: Dict, browser_options: Dict
    ) -> None:
        context._set_options(context_options, browser_options)

    def _did_launch_browser(self, browser: Browser) -> None:
        browser._browser_type = self


def normalize_launch_params(params: Dict) -> None:
    if "env" in params:
        params["env"] = [
            {"name": name, "value": str(value)}
            for [name, value] in params["env"].items()
        ]
    if "ignoreDefaultArgs" in params:
        if params["ignoreDefaultArgs"] is True:
            params["ignoreAllDefaultArgs"] = True
            del params["ignoreDefaultArgs"]
    if "executablePath" in params:
        params["executablePath"] = str(Path(params["executablePath"]))
    if "downloadsPath" in params:
        params["downloadsPath"] = str(Path(params["downloadsPath"]))
    if "tracesDir" in params:
        params["tracesDir"] = str(Path(params["tracesDir"]))

# === NexusCore/openenv\Lib\site-packages\anthropic\types\message_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from .tool_param import ToolParam
from .model_param import ModelParam
from .message_param import MessageParam
from .metadata_param import MetadataParam
from .text_block_param import TextBlockParam
from .tool_choice_param import ToolChoiceParam
from .tool_choice_any_param import ToolChoiceAnyParam
from .tool_choice_auto_param import ToolChoiceAutoParam
from .tool_choice_tool_param import ToolChoiceToolParam

__all__ = [
    "MessageCreateParamsBase",
    "Metadata",
    "ToolChoice",
    "ToolChoiceToolChoiceAuto",
    "ToolChoiceToolChoiceAny",
    "ToolChoiceToolChoiceTool",
    "MessageCreateParamsNonStreaming",
    "MessageCreateParamsStreaming",
]


class MessageCreateParamsBase(TypedDict, total=False):
    max_tokens: Required[int]
    """The maximum number of tokens to generate before stopping.

    Note that our models may stop _before_ reaching this maximum. This parameter
    only specifies the absolute maximum number of tokens to generate.

    Different models have different maximum values for this parameter. See
    [models](https://docs.anthropic.com/en/docs/models-overview) for details.
    """

    messages: Required[Iterable[MessageParam]]
    """Input messages.

    Our models are trained to operate on alternating `user` and `assistant`
    conversational turns. When creating a new `Message`, you specify the prior
    conversational turns with the `messages` parameter, and the model then generates
    the next `Message` in the conversation. Consecutive `user` or `assistant` turns
    in your request will be combined into a single turn.

    Each input message must be an object with a `role` and `content`. You can
    specify a single `user`-role message, or you can include multiple `user` and
    `assistant` messages.

    If the final message uses the `assistant` role, the response content will
    continue immediately from the content in that message. This can be used to
    constrain part of the model's response.

    Example with a single `user` message:

    ```json
    [{ "role": "user", "content": "Hello, Claude" }]
    ```

    Example with multiple conversational turns:

    ```json
    [
      { "role": "user", "content": "Hello there." },
      { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
      { "role": "user", "content": "Can you explain LLMs in plain English?" }
    ]
    ```

    Example with a partially-filled response from Claude:

    ```json
    [
      {
        "role": "user",
        "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
      },
      { "role": "assistant", "content": "The best answer is (" }
    ]
    ```

    Each input message `content` may be either a single `string` or an array of
    content blocks, where each block has a specific `type`. Using a `string` for
    `content` is shorthand for an array of one content block of type `"text"`. The
    following input messages are equivalent:

    ```json
    { "role": "user", "content": "Hello, Claude" }
    ```

    ```json
    { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
    ```

    Starting with Claude 3 models, you can also send image content blocks:

    ```json
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "/9j/4AAQSkZJRg..."
          }
        },
        { "type": "text", "text": "What is in this image?" }
      ]
    }
    ```

    We currently support the `base64` source type for images, and the `image/jpeg`,
    `image/png`, `image/gif`, and `image/webp` media types.

    See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
    more input examples.

    Note that if you want to include a
    [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
    the top-level `system` parameter — there is no `"system"` role for input
    messages in the Messages API.
    """

    model: Required[ModelParam]
    """
    The model that will complete your prompt.\n\nSee
    [models](https://docs.anthropic.com/en/docs/models-overview) for additional
    details and options.
    """

    metadata: MetadataParam
    """An object describing metadata about the request."""

    stop_sequences: List[str]
    """Custom text sequences that will cause the model to stop generating.

    Our models will normally stop when they have naturally completed their turn,
    which will result in a response `stop_reason` of `"end_turn"`.

    If you want the model to stop generating when it encounters custom strings of
    text, you can use the `stop_sequences` parameter. If the model encounters one of
    the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
    and the response `stop_sequence` value will contain the matched stop sequence.
    """

    system: Union[str, Iterable[TextBlockParam]]
    """System prompt.

    A system prompt is a way of providing context and instructions to Claude, such
    as specifying a particular goal or role. See our
    [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
    """

    temperature: float
    """Amount of randomness injected into the response.

    Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
    for analytical / multiple choice, and closer to `1.0` for creative and
    generative tasks.

    Note that even with `temperature` of `0.0`, the results will not be fully
    deterministic.
    """

    tool_choice: ToolChoiceParam
    """How the model should use the provided tools.

    The model can use a specific tool, any available tool, or decide by itself.
    """

    tools: Iterable[ToolParam]
    """Definitions of tools that the model may use.

    If you include `tools` in your API request, the model may return `tool_use`
    content blocks that represent the model's use of those tools. You can then run
    those tools using the tool input generated by the model and then optionally
    return results back to the model using `tool_result` content blocks.

    Each tool definition includes:

    - `name`: Name of the tool.
    - `description`: Optional, but strongly-recommended description of the tool.
    - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
      shape that the model will produce in `tool_use` output content blocks.

    For example, if you defined `tools` as:

    ```json
    [
      {
        "name": "get_stock_price",
        "description": "Get the current stock price for a given ticker symbol.",
        "input_schema": {
          "type": "object",
          "properties": {
            "ticker": {
              "type": "string",
              "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
            }
          },
          "required": ["ticker"]
        }
      }
    ]
    ```

    And then asked the model "What's the S&P 500 at today?", the model might produce
    `tool_use` content blocks in the response like this:

    ```json
    [
      {
        "type": "tool_use",
        "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "name": "get_stock_price",
        "input": { "ticker": "^GSPC" }
      }
    ]
    ```

    You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
    input, and return the following back to the model in a subsequent `user`
    message:

    ```json
    [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "content": "259.75 USD"
      }
    ]
    ```

    Tools can be used for workflows that include running client-side tools and
    functions, or more generally whenever you want the model to produce a particular
    JSON structure of output.

    See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
    """

    top_k: int
    """Only sample from the top K options for each subsequent token.

    Used to remove "long tail" low probability responses.
    [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """

    top_p: float
    """Use nucleus sampling.

    In nucleus sampling, we compute the cumulative distribution over all the options
    for each subsequent token in decreasing probability order and cut it off once it
    reaches a particular probability specified by `top_p`. You should either alter
    `temperature` or `top_p`, but not both.

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """


Metadata: TypeAlias = MetadataParam
"""This is deprecated, `MetadataParam` should be used instead"""

ToolChoice: TypeAlias = ToolChoiceParam
"""This is deprecated, `ToolChoiceParam` should be used instead"""

ToolChoiceToolChoiceAuto: TypeAlias = ToolChoiceAutoParam
"""This is deprecated, `ToolChoiceAutoParam` should be used instead"""

ToolChoiceToolChoiceAny: TypeAlias = ToolChoiceAnyParam
"""This is deprecated, `ToolChoiceAnyParam` should be used instead"""

ToolChoiceToolChoiceTool: TypeAlias = ToolChoiceToolParam
"""This is deprecated, `ToolChoiceToolParam` should be used instead"""


class MessageCreateParamsNonStreaming(MessageCreateParamsBase, total=False):
    stream: Literal[False]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


class MessageCreateParamsStreaming(MessageCreateParamsBase):
    stream: Required[Literal[True]]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


MessageCreateParams = Union[MessageCreateParamsNonStreaming, MessageCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\anthropic\types\beta\prompt_caching\message_create_params.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, Required, TypeAlias, TypedDict

from ...model_param import ModelParam
from ...metadata_param import MetadataParam
from ...tool_choice_param import ToolChoiceParam
from ...tool_choice_any_param import ToolChoiceAnyParam
from ...tool_choice_auto_param import ToolChoiceAutoParam
from ...tool_choice_tool_param import ToolChoiceToolParam
from .prompt_caching_beta_tool_param import PromptCachingBetaToolParam
from .prompt_caching_beta_message_param import PromptCachingBetaMessageParam
from .prompt_caching_beta_text_block_param import PromptCachingBetaTextBlockParam

__all__ = [
    "MessageCreateParamsBase",
    "Metadata",
    "ToolChoice",
    "ToolChoiceToolChoiceAuto",
    "ToolChoiceToolChoiceAny",
    "ToolChoiceToolChoiceTool",
    "MessageCreateParamsNonStreaming",
    "MessageCreateParamsStreaming",
]


class MessageCreateParamsBase(TypedDict, total=False):
    max_tokens: Required[int]
    """The maximum number of tokens to generate before stopping.

    Note that our models may stop _before_ reaching this maximum. This parameter
    only specifies the absolute maximum number of tokens to generate.

    Different models have different maximum values for this parameter. See
    [models](https://docs.anthropic.com/en/docs/models-overview) for details.
    """

    messages: Required[Iterable[PromptCachingBetaMessageParam]]
    """Input messages.

    Our models are trained to operate on alternating `user` and `assistant`
    conversational turns. When creating a new `Message`, you specify the prior
    conversational turns with the `messages` parameter, and the model then generates
    the next `Message` in the conversation. Consecutive `user` or `assistant` turns
    in your request will be combined into a single turn.

    Each input message must be an object with a `role` and `content`. You can
    specify a single `user`-role message, or you can include multiple `user` and
    `assistant` messages.

    If the final message uses the `assistant` role, the response content will
    continue immediately from the content in that message. This can be used to
    constrain part of the model's response.

    Example with a single `user` message:

    ```json
    [{ "role": "user", "content": "Hello, Claude" }]
    ```

    Example with multiple conversational turns:

    ```json
    [
      { "role": "user", "content": "Hello there." },
      { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
      { "role": "user", "content": "Can you explain LLMs in plain English?" }
    ]
    ```

    Example with a partially-filled response from Claude:

    ```json
    [
      {
        "role": "user",
        "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
      },
      { "role": "assistant", "content": "The best answer is (" }
    ]
    ```

    Each input message `content` may be either a single `string` or an array of
    content blocks, where each block has a specific `type`. Using a `string` for
    `content` is shorthand for an array of one content block of type `"text"`. The
    following input messages are equivalent:

    ```json
    { "role": "user", "content": "Hello, Claude" }
    ```

    ```json
    { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
    ```

    Starting with Claude 3 models, you can also send image content blocks:

    ```json
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": "/9j/4AAQSkZJRg..."
          }
        },
        { "type": "text", "text": "What is in this image?" }
      ]
    }
    ```

    We currently support the `base64` source type for images, and the `image/jpeg`,
    `image/png`, `image/gif`, and `image/webp` media types.

    See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
    more input examples.

    Note that if you want to include a
    [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
    the top-level `system` parameter — there is no `"system"` role for input
    messages in the Messages API.
    """

    model: Required[ModelParam]
    """
    The model that will complete your prompt.\n\nSee
    [models](https://docs.anthropic.com/en/docs/models-overview) for additional
    details and options.
    """

    metadata: MetadataParam
    """An object describing metadata about the request."""

    stop_sequences: List[str]
    """Custom text sequences that will cause the model to stop generating.

    Our models will normally stop when they have naturally completed their turn,
    which will result in a response `stop_reason` of `"end_turn"`.

    If you want the model to stop generating when it encounters custom strings of
    text, you can use the `stop_sequences` parameter. If the model encounters one of
    the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
    and the response `stop_sequence` value will contain the matched stop sequence.
    """

    system: Union[str, Iterable[PromptCachingBetaTextBlockParam]]
    """System prompt.

    A system prompt is a way of providing context and instructions to Claude, such
    as specifying a particular goal or role. See our
    [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
    """

    temperature: float
    """Amount of randomness injected into the response.

    Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
    for analytical / multiple choice, and closer to `1.0` for creative and
    generative tasks.

    Note that even with `temperature` of `0.0`, the results will not be fully
    deterministic.
    """

    tool_choice: ToolChoiceParam
    """How the model should use the provided tools.

    The model can use a specific tool, any available tool, or decide by itself.
    """

    tools: Iterable[PromptCachingBetaToolParam]
    """Definitions of tools that the model may use.

    If you include `tools` in your API request, the model may return `tool_use`
    content blocks that represent the model's use of those tools. You can then run
    those tools using the tool input generated by the model and then optionally
    return results back to the model using `tool_result` content blocks.

    Each tool definition includes:

    - `name`: Name of the tool.
    - `description`: Optional, but strongly-recommended description of the tool.
    - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
      shape that the model will produce in `tool_use` output content blocks.

    For example, if you defined `tools` as:

    ```json
    [
      {
        "name": "get_stock_price",
        "description": "Get the current stock price for a given ticker symbol.",
        "input_schema": {
          "type": "object",
          "properties": {
            "ticker": {
              "type": "string",
              "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
            }
          },
          "required": ["ticker"]
        }
      }
    ]
    ```

    And then asked the model "What's the S&P 500 at today?", the model might produce
    `tool_use` content blocks in the response like this:

    ```json
    [
      {
        "type": "tool_use",
        "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "name": "get_stock_price",
        "input": { "ticker": "^GSPC" }
      }
    ]
    ```

    You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
    input, and return the following back to the model in a subsequent `user`
    message:

    ```json
    [
      {
        "type": "tool_result",
        "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
        "content": "259.75 USD"
      }
    ]
    ```

    Tools can be used for workflows that include running client-side tools and
    functions, or more generally whenever you want the model to produce a particular
    JSON structure of output.

    See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
    """

    top_k: int
    """Only sample from the top K options for each subsequent token.

    Used to remove "long tail" low probability responses.
    [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """

    top_p: float
    """Use nucleus sampling.

    In nucleus sampling, we compute the cumulative distribution over all the options
    for each subsequent token in decreasing probability order and cut it off once it
    reaches a particular probability specified by `top_p`. You should either alter
    `temperature` or `top_p`, but not both.

    Recommended for advanced use cases only. You usually only need to use
    `temperature`.
    """


Metadata: TypeAlias = MetadataParam
"""This is deprecated, `MetadataParam` should be used instead"""

ToolChoice: TypeAlias = ToolChoiceParam
"""This is deprecated, `ToolChoiceParam` should be used instead"""

ToolChoiceToolChoiceAuto: TypeAlias = ToolChoiceAutoParam
"""This is deprecated, `ToolChoiceAutoParam` should be used instead"""

ToolChoiceToolChoiceAny: TypeAlias = ToolChoiceAnyParam
"""This is deprecated, `ToolChoiceAnyParam` should be used instead"""

ToolChoiceToolChoiceTool: TypeAlias = ToolChoiceToolParam
"""This is deprecated, `ToolChoiceToolParam` should be used instead"""


class MessageCreateParamsNonStreaming(MessageCreateParamsBase, total=False):
    stream: Literal[False]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


class MessageCreateParamsStreaming(MessageCreateParamsBase):
    stream: Required[Literal[True]]
    """Whether to incrementally stream the response using server-sent events.

    See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
    details.
    """


MessageCreateParams = Union[MessageCreateParamsNonStreaming, MessageCreateParamsStreaming]

# === NexusCore/openenv\Lib\site-packages\fontTools\cffLib\CFFToCFF2.py ===
"""CFF to CFF2 converter."""

from fontTools.ttLib import TTFont, newTable
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.misc.psCharStrings import T2WidthExtractor
from fontTools.cffLib import (
    TopDictIndex,
    FDArrayIndex,
    FontDict,
    buildOrder,
    topDictOperators,
    privateDictOperators,
    topDictOperators2,
    privateDictOperators2,
)
from io import BytesIO
import logging

__all__ = ["convertCFFToCFF2", "main"]


log = logging.getLogger("fontTools.cffLib")


class _NominalWidthUsedError(Exception):
    def __add__(self, other):
        raise self

    def __radd__(self, other):
        raise self


def _convertCFFToCFF2(cff, otFont):
    """Converts this object from CFF format to CFF2 format. This conversion
    is done 'in-place'. The conversion cannot be reversed.

    This assumes a decompiled CFF table. (i.e. that the object has been
    filled via :meth:`decompile` and e.g. not loaded from XML.)"""

    # Clean up T2CharStrings

    topDict = cff.topDictIndex[0]
    fdArray = topDict.FDArray if hasattr(topDict, "FDArray") else None
    charStrings = topDict.CharStrings
    globalSubrs = cff.GlobalSubrs
    localSubrs = (
        [getattr(fd.Private, "Subrs", []) for fd in fdArray]
        if fdArray
        else (
            [topDict.Private.Subrs]
            if hasattr(topDict, "Private") and hasattr(topDict.Private, "Subrs")
            else []
        )
    )

    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        cs.decompile()

    # Clean up subroutines first
    for subrs in [globalSubrs] + localSubrs:
        for subr in subrs:
            program = subr.program
            i = j = len(program)
            try:
                i = program.index("return")
            except ValueError:
                pass
            try:
                j = program.index("endchar")
            except ValueError:
                pass
            program[min(i, j) :] = []

    # Clean up glyph charstrings
    removeUnusedSubrs = False
    nominalWidthXError = _NominalWidthUsedError()
    for glyphName in charStrings.keys():
        cs, fdIndex = charStrings.getItemAndSelector(glyphName)
        program = cs.program

        thisLocalSubrs = (
            localSubrs[fdIndex]
            if fdIndex is not None
            else (
                getattr(topDict.Private, "Subrs", [])
                if hasattr(topDict, "Private")
                else []
            )
        )

        # Intentionally use custom type for nominalWidthX, such that any
        # CharString that has an explicit width encoded will throw back to us.
        extractor = T2WidthExtractor(
            thisLocalSubrs,
            globalSubrs,
            nominalWidthXError,
            0,
        )
        try:
            extractor.execute(cs)
        except _NominalWidthUsedError:
            # Program has explicit width. We want to drop it, but can't
            # just pop the first number since it may be a subroutine call.
            # Instead, when seeing that, we embed the subroutine and recurse.
            # If this ever happened, we later prune unused subroutines.
            while len(program) >= 2 and program[1] in ["callsubr", "callgsubr"]:
                removeUnusedSubrs = True
                subrNumber = program.pop(0)
                assert isinstance(subrNumber, int), subrNumber
                op = program.pop(0)
                bias = extractor.localBias if op == "callsubr" else extractor.globalBias
                subrNumber += bias
                subrSet = thisLocalSubrs if op == "callsubr" else globalSubrs
                subrProgram = subrSet[subrNumber].program
                program[:0] = subrProgram
            # Now pop the actual width
            assert len(program) >= 1, program
            program.pop(0)

        if program and program[-1] == "endchar":
            program.pop()

    if removeUnusedSubrs:
        cff.remove_unused_subroutines()

    # Upconvert TopDict

    cff.major = 2
    cff2GetGlyphOrder = cff.otFont.getGlyphOrder
    topDictData = TopDictIndex(None, cff2GetGlyphOrder)
    for item in cff.topDictIndex:
        # Iterate over, such that all are decompiled
        topDictData.append(item)
    cff.topDictIndex = topDictData
    topDict = topDictData[0]
    if hasattr(topDict, "Private"):
        privateDict = topDict.Private
    else:
        privateDict = None
    opOrder = buildOrder(topDictOperators2)
    topDict.order = opOrder
    topDict.cff2GetGlyphOrder = cff2GetGlyphOrder

    if not hasattr(topDict, "FDArray"):
        fdArray = topDict.FDArray = FDArrayIndex()
        fdArray.strings = None
        fdArray.GlobalSubrs = topDict.GlobalSubrs
        topDict.GlobalSubrs.fdArray = fdArray
        charStrings = topDict.CharStrings
        if charStrings.charStringsAreIndexed:
            charStrings.charStringsIndex.fdArray = fdArray
        else:
            charStrings.fdArray = fdArray
        fontDict = FontDict()
        fontDict.setCFF2(True)
        fdArray.append(fontDict)
        fontDict.Private = privateDict
        privateOpOrder = buildOrder(privateDictOperators2)
        if privateDict is not None:
            for entry in privateDictOperators:
                key = entry[1]
                if key not in privateOpOrder:
                    if key in privateDict.rawDict:
                        # print "Removing private dict", key
                        del privateDict.rawDict[key]
                    if hasattr(privateDict, key):
                        delattr(privateDict, key)
                        # print "Removing privateDict attr", key
    else:
        # clean up the PrivateDicts in the fdArray
        fdArray = topDict.FDArray
        privateOpOrder = buildOrder(privateDictOperators2)
        for fontDict in fdArray:
            fontDict.setCFF2(True)
            for key in list(fontDict.rawDict.keys()):
                if key not in fontDict.order:
                    del fontDict.rawDict[key]
                    if hasattr(fontDict, key):
                        delattr(fontDict, key)

            privateDict = fontDict.Private
            for entry in privateDictOperators:
                key = entry[1]
                if key not in privateOpOrder:
                    if key in list(privateDict.rawDict.keys()):
                        # print "Removing private dict", key
                        del privateDict.rawDict[key]
                    if hasattr(privateDict, key):
                        delattr(privateDict, key)
                        # print "Removing privateDict attr", key

    # Now delete up the deprecated topDict operators from CFF 1.0
    for entry in topDictOperators:
        key = entry[1]
        # We seem to need to keep the charset operator for now,
        # or we fail to compile with some fonts, like AdditionFont.otf.
        # I don't know which kind of CFF font those are. But keeping
        # charset seems to work. It will be removed when we save and
        # read the font again.
        #
        # AdditionFont.otf has <Encoding name="StandardEncoding"/>.
        if key == "charset":
            continue
        if key not in opOrder:
            if key in topDict.rawDict:
                del topDict.rawDict[key]
            if hasattr(topDict, key):
                delattr(topDict, key)

    # TODO(behdad): What does the following comment even mean? Both CFF and CFF2
    # use the same T2Charstring class. I *think* what it means is that the CharStrings
    # were loaded for CFF1, and we need to reload them for CFF2 to set varstore, etc
    # on them. At least that's what I understand. It's probably safe to remove this
    # and just set vstore where needed.
    #
    # See comment above about charset as well.

    # At this point, the Subrs and Charstrings are all still T2Charstring class
    # easiest to fix this by compiling, then decompiling again
    file = BytesIO()
    cff.compile(file, otFont, isCFF2=True)
    file.seek(0)
    cff.decompile(file, otFont, isCFF2=True)


def convertCFFToCFF2(font):
    cff = font["CFF "].cff
    del font["CFF "]
    _convertCFFToCFF2(cff, font)
    table = font["CFF2"] = newTable("CFF2")
    table.cff = cff


def main(args=None):
    """Convert CFF OTF font to CFF2 OTF font"""
    if args is None:
        import sys

        args = sys.argv[1:]

    import argparse

    parser = argparse.ArgumentParser(
        "fonttools cffLib.CFFToCFF2",
        description="Upgrade a CFF font to CFF2.",
    )
    parser.add_argument(
        "input", metavar="INPUT.ttf", help="Input OTF file with CFF table."
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT.ttf",
        default=None,
        help="Output instance OTF file (default: INPUT-CFF2.ttf).",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalc_timestamp",
        action="store_false",
        help="Don't set the output font's timestamp to the current time.",
    )
    loggingGroup = parser.add_mutually_exclusive_group(required=False)
    loggingGroup.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    loggingGroup.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    options = parser.parse_args(args)

    from fontTools import configLogger

    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    import os

    infile = options.input
    if not os.path.isfile(infile):
        parser.error("No such file '{}'".format(infile))

    outfile = (
        makeOutputFileName(infile, overWrite=True, suffix="-CFF2")
        if not options.output
        else options.output
    )

    font = TTFont(infile, recalcTimestamp=options.recalc_timestamp, recalcBBoxes=False)

    convertCFFToCFF2(font)

    log.info(
        "Saving %s",
        outfile,
    )
    font.save(outfile)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\C_P_A_L_.py ===
# Copyright 2013 Google, Inc. All Rights Reserved.
#
# Google Author(s): Behdad Esfahbod

from fontTools.misc.textTools import bytesjoin, safeEval
from . import DefaultTable
import array
from collections import namedtuple
import struct
import sys


class table_C_P_A_L_(DefaultTable.DefaultTable):
    """Color Palette table

    The ``CPAL`` table contains a set of one or more color palettes. The color
    records in each palette can be referenced by the ``COLR`` table to specify
    the colors used in a color glyph.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/cpal
    """

    NO_NAME_ID = 0xFFFF
    DEFAULT_PALETTE_TYPE = 0

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.palettes = []
        self.paletteTypes = []
        self.paletteLabels = []
        self.paletteEntryLabels = []

    def decompile(self, data, ttFont):
        (
            self.version,
            self.numPaletteEntries,
            numPalettes,
            numColorRecords,
            goffsetFirstColorRecord,
        ) = struct.unpack(">HHHHL", data[:12])
        assert (
            self.version <= 1
        ), "Version of CPAL table is higher than I know how to handle"
        self.palettes = []
        pos = 12
        for i in range(numPalettes):
            startIndex = struct.unpack(">H", data[pos : pos + 2])[0]
            assert startIndex + self.numPaletteEntries <= numColorRecords
            pos += 2
            palette = []
            ppos = goffsetFirstColorRecord + startIndex * 4
            for j in range(self.numPaletteEntries):
                palette.append(Color(*struct.unpack(">BBBB", data[ppos : ppos + 4])))
                ppos += 4
            self.palettes.append(palette)
        if self.version == 0:
            offsetToPaletteTypeArray = 0
            offsetToPaletteLabelArray = 0
            offsetToPaletteEntryLabelArray = 0
        else:
            pos = 12 + numPalettes * 2
            (
                offsetToPaletteTypeArray,
                offsetToPaletteLabelArray,
                offsetToPaletteEntryLabelArray,
            ) = struct.unpack(">LLL", data[pos : pos + 12])
        self.paletteTypes = self._decompileUInt32Array(
            data,
            offsetToPaletteTypeArray,
            numPalettes,
            default=self.DEFAULT_PALETTE_TYPE,
        )
        self.paletteLabels = self._decompileUInt16Array(
            data, offsetToPaletteLabelArray, numPalettes, default=self.NO_NAME_ID
        )
        self.paletteEntryLabels = self._decompileUInt16Array(
            data,
            offsetToPaletteEntryLabelArray,
            self.numPaletteEntries,
            default=self.NO_NAME_ID,
        )

    def _decompileUInt16Array(self, data, offset, numElements, default=0):
        if offset == 0:
            return [default] * numElements
        result = array.array("H", data[offset : offset + 2 * numElements])
        if sys.byteorder != "big":
            result.byteswap()
        assert len(result) == numElements, result
        return result.tolist()

    def _decompileUInt32Array(self, data, offset, numElements, default=0):
        if offset == 0:
            return [default] * numElements
        result = array.array("I", data[offset : offset + 4 * numElements])
        if sys.byteorder != "big":
            result.byteswap()
        assert len(result) == numElements, result
        return result.tolist()

    def compile(self, ttFont):
        colorRecordIndices, colorRecords = self._compileColorRecords()
        paletteTypes = self._compilePaletteTypes()
        paletteLabels = self._compilePaletteLabels()
        paletteEntryLabels = self._compilePaletteEntryLabels()
        numColorRecords = len(colorRecords) // 4
        offsetToFirstColorRecord = 12 + len(colorRecordIndices)
        if self.version >= 1:
            offsetToFirstColorRecord += 12
        header = struct.pack(
            ">HHHHL",
            self.version,
            self.numPaletteEntries,
            len(self.palettes),
            numColorRecords,
            offsetToFirstColorRecord,
        )
        if self.version == 0:
            dataList = [header, colorRecordIndices, colorRecords]
        else:
            pos = offsetToFirstColorRecord + len(colorRecords)
            if len(paletteTypes) == 0:
                offsetToPaletteTypeArray = 0
            else:
                offsetToPaletteTypeArray = pos
                pos += len(paletteTypes)
            if len(paletteLabels) == 0:
                offsetToPaletteLabelArray = 0
            else:
                offsetToPaletteLabelArray = pos
                pos += len(paletteLabels)
            if len(paletteEntryLabels) == 0:
                offsetToPaletteEntryLabelArray = 0
            else:
                offsetToPaletteEntryLabelArray = pos
                pos += len(paletteLabels)
            header1 = struct.pack(
                ">LLL",
                offsetToPaletteTypeArray,
                offsetToPaletteLabelArray,
                offsetToPaletteEntryLabelArray,
            )
            dataList = [
                header,
                colorRecordIndices,
                header1,
                colorRecords,
                paletteTypes,
                paletteLabels,
                paletteEntryLabels,
            ]
        return bytesjoin(dataList)

    def _compilePalette(self, palette):
        assert len(palette) == self.numPaletteEntries
        pack = lambda c: struct.pack(">BBBB", c.blue, c.green, c.red, c.alpha)
        return bytesjoin([pack(color) for color in palette])

    def _compileColorRecords(self):
        colorRecords, colorRecordIndices, pool = [], [], {}
        for palette in self.palettes:
            packedPalette = self._compilePalette(palette)
            if packedPalette in pool:
                index = pool[packedPalette]
            else:
                index = len(colorRecords)
                colorRecords.append(packedPalette)
                pool[packedPalette] = index
            colorRecordIndices.append(struct.pack(">H", index * self.numPaletteEntries))
        return bytesjoin(colorRecordIndices), bytesjoin(colorRecords)

    def _compilePaletteTypes(self):
        if self.version == 0 or not any(self.paletteTypes):
            return b""
        assert len(self.paletteTypes) == len(self.palettes)
        result = bytesjoin([struct.pack(">I", ptype) for ptype in self.paletteTypes])
        assert len(result) == 4 * len(self.palettes)
        return result

    def _compilePaletteLabels(self):
        if self.version == 0 or all(l == self.NO_NAME_ID for l in self.paletteLabels):
            return b""
        assert len(self.paletteLabels) == len(self.palettes)
        result = bytesjoin([struct.pack(">H", label) for label in self.paletteLabels])
        assert len(result) == 2 * len(self.palettes)
        return result

    def _compilePaletteEntryLabels(self):
        if self.version == 0 or all(
            l == self.NO_NAME_ID for l in self.paletteEntryLabels
        ):
            return b""
        assert len(self.paletteEntryLabels) == self.numPaletteEntries
        result = bytesjoin(
            [struct.pack(">H", label) for label in self.paletteEntryLabels]
        )
        assert len(result) == 2 * self.numPaletteEntries
        return result

    def toXML(self, writer, ttFont):
        numPalettes = len(self.palettes)
        paletteLabels = {i: nameID for (i, nameID) in enumerate(self.paletteLabels)}
        paletteTypes = {i: typ for (i, typ) in enumerate(self.paletteTypes)}
        writer.simpletag("version", value=self.version)
        writer.newline()
        writer.simpletag("numPaletteEntries", value=self.numPaletteEntries)
        writer.newline()
        for index, palette in enumerate(self.palettes):
            attrs = {"index": index}
            paletteType = paletteTypes.get(index, self.DEFAULT_PALETTE_TYPE)
            paletteLabel = paletteLabels.get(index, self.NO_NAME_ID)
            if self.version > 0 and paletteLabel != self.NO_NAME_ID:
                attrs["label"] = paletteLabel
            if self.version > 0 and paletteType != self.DEFAULT_PALETTE_TYPE:
                attrs["type"] = paletteType
            writer.begintag("palette", **attrs)
            writer.newline()
            if (
                self.version > 0
                and paletteLabel != self.NO_NAME_ID
                and ttFont
                and "name" in ttFont
            ):
                name = ttFont["name"].getDebugName(paletteLabel)
                if name is not None:
                    writer.comment(name)
                    writer.newline()
            assert len(palette) == self.numPaletteEntries
            for cindex, color in enumerate(palette):
                color.toXML(writer, ttFont, cindex)
            writer.endtag("palette")
            writer.newline()
        if self.version > 0 and not all(
            l == self.NO_NAME_ID for l in self.paletteEntryLabels
        ):
            writer.begintag("paletteEntryLabels")
            writer.newline()
            for index, label in enumerate(self.paletteEntryLabels):
                if label != self.NO_NAME_ID:
                    writer.simpletag("label", index=index, value=label)
                    if self.version > 0 and label and ttFont and "name" in ttFont:
                        name = ttFont["name"].getDebugName(label)
                        if name is not None:
                            writer.comment(name)
                    writer.newline()
            writer.endtag("paletteEntryLabels")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "palette":
            self.paletteLabels.append(int(attrs.get("label", self.NO_NAME_ID)))
            self.paletteTypes.append(int(attrs.get("type", self.DEFAULT_PALETTE_TYPE)))
            palette = []
            for element in content:
                if isinstance(element, str):
                    continue
                attrs = element[1]
                color = Color.fromHex(attrs["value"])
                palette.append(color)
            self.palettes.append(palette)
        elif name == "paletteEntryLabels":
            colorLabels = {}
            for element in content:
                if isinstance(element, str):
                    continue
                elementName, elementAttr, _ = element
                if elementName == "label":
                    labelIndex = safeEval(elementAttr["index"])
                    nameID = safeEval(elementAttr["value"])
                    colorLabels[labelIndex] = nameID
            self.paletteEntryLabels = [
                colorLabels.get(i, self.NO_NAME_ID)
                for i in range(self.numPaletteEntries)
            ]
        elif "value" in attrs:
            value = safeEval(attrs["value"])
            setattr(self, name, value)
            if name == "numPaletteEntries":
                self.paletteEntryLabels = [self.NO_NAME_ID] * self.numPaletteEntries


class Color(namedtuple("Color", "blue green red alpha")):
    def hex(self):
        return "#%02X%02X%02X%02X" % (self.red, self.green, self.blue, self.alpha)

    def __repr__(self):
        return self.hex()

    def toXML(self, writer, ttFont, index=None):
        writer.simpletag("color", value=self.hex(), index=index)
        writer.newline()

    @classmethod
    def fromHex(cls, value):
        if value[0] == "#":
            value = value[1:]
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
        alpha = int(value[6:8], 16) if len(value) >= 8 else 0xFF
        return cls(red=red, green=green, blue=blue, alpha=alpha)

    @classmethod
    def fromRGBA(cls, red, green, blue, alpha):
        return cls(red=red, green=green, blue=blue, alpha=alpha)